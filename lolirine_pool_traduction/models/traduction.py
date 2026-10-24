"""Traduction automatique des fiches produits du Pool Store (site 6).

Fonctionnement
--------------
* Toutes les 30 min, si le paramètre « lolirine_pool_traduction.actif » vaut
  True et qu'aucun lot n'est en cours, ``_cron_soumettre`` prépare les fiches
  suivantes (au plus « lot_max ») et les envoie à l'API Claude en traitement
  par lots (Message Batches : moitié prix, résultat en général sous l'heure).
* Toutes les 10 min, ``_cron_recuperer`` interroge les lots envoyés ; quand un
  lot est terminé, les traductions sont posées sur les fiches.

Ce qui est écrit, par fiche
---------------------------
* nom, description courte : néerlandais et anglais, seulement si la langue
  n'est pas encore traduite (une traduction faite à la main n'est jamais
  remplacée) ;
* textes HTML (description e-commerce, description du site, caractéristiques
  techniques) : traduction phrase par phrase via les « termes » d'Odoo ; une
  traduction dont les balises HTML ne correspondent pas à l'original est
  ignorée ;
* titre Google : rédigé en français, néerlandais et anglais s'il est vide ;
* description Google : réécrite dans les trois langues si elle est vide ou
  générée automatiquement (« … – Lolirine Pool Store. ») ; une description
  rédigée à la main garde son français et reçoit seulement sa traduction.

Une mémoire de traduction évite de payer deux fois un texte identique
(fréquent pour les déclinaisons d'une même gamme).
"""
import hashlib
import json
import logging
import re
import time

import requests
from lxml import etree

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

P = 'lolirine_pool_traduction.'
SITE = 6
URL_LOTS = 'https://api.anthropic.com/v1/messages/batches'
CHAMPS_HTML = ['description_ecommerce', 'website_description', 'x_specs_techniques']
LANGUES = {'nl': 'nl_NL', 'en': 'en_GB'}
META_AUTO = re.compile(r'Lolirine Pool Store\.\s*$')

CONSIGNES = """Tu es traducteur et rédacteur web pour Lolirine Pool Store (lolirinepoolstore.be), \
boutique belge de matériel de piscine, spa et wellness. Tu reçois une fiche produit en français, en JSON.

Ta mission :
1. Traduire en néerlandais de Belgique (vouvoiement « u ») et en anglais britannique : le nom, la \
description courte et chaque élément de la liste « termes ».
2. Rédiger le titre Google (meta title) en français, néerlandais et anglais : 60 caractères maximum, \
espaces compris. Commence par le type de produit (le nom seul peut être une simple taille, ex. \
« 110 mm » : sers-toi de la catégorie et de la description pour dire ce que c'est), puis la marque \
et le modèle ou la taille utiles. Termine par « | Lolirine » si la place le permet.
3. Description Google (meta description) :
   - si « rediger_meta » vaut true : rédige-la en français, néerlandais et anglais, 140 à 155 \
caractères, concrète (ce que c'est, l'avantage principal, la compatibilité utile), sans prix, \
terminée par une courte mention de livraison en Belgique ;
   - si « rediger_meta » vaut false : NE réécris PAS le français ; traduis seulement \
« meta_description_actuelle » en néerlandais et en anglais.

Règles :
- Termes métier : pompe à chaleur = warmtepomp / heat pump ; filtre à sable = zandfilter / sand \
filter ; électrolyseur = zoutelektrolyse / salt chlorinator ; bâche (à bulles) = (bubbel)zeil / \
(bubble) cover ; bâche à barres = stangenafdekking / bar cover ; volet = rolluik / slatted cover ; \
bonde de fond = bodemafvoer / main drain ; buse de refoulement = inlaatmondstuk / return inlet ; \
prise balai = stofzuigeraansluiting / vacuum point ; pièces à sceller = inbouwonderdelen / built-in \
parts ; hivernage = overwintering / winterising ; robot = zwembadrobot / pool robot ; \
HT = excl. btw / excl. VAT ; TVAC/TTC = incl. btw / incl. VAT.
- Ne traduis jamais : marques, noms de gammes et de modèles, références, codes, nombres, unités, \
dimensions, normes.
- Dans « termes », chaque élément peut contenir des balises HTML : garde exactement les mêmes \
balises, dans le même ordre, avec les mêmes attributs ; ne traduis que le texte. Garde les entités \
HTML (&amp; etc.). N'ajoute ni ne retire d'information.
- Les listes « termes » traduites ont exactement le même nombre d'éléments, dans le même ordre.

Réponds UNIQUEMENT par un objet JSON valide, sans texte autour, de la forme :
{"fr": {"meta_title": "...", "meta_description": "..."},
 "nl": {"nom": "...", "description_courte": "...", "meta_title": "...", "meta_description": "...", "termes": ["..."]},
 "en": {"nom": "...", "description_courte": "...", "meta_title": "...", "meta_description": "...", "termes": ["..."]}}
Mets "" pour un champ absent de l'entrée (ex. pas de description courte). Si « rediger_meta » vaut \
false, mets "" pour fr.meta_description."""


def _empreinte(texte):
    return hashlib.sha1(texte.encode('utf-8')).hexdigest()


def _balises(fragment):
    """Suite (balise, attributs) d'un fragment HTML, pour vérifier une traduction."""
    try:
        racine = etree.fromstring('<div>%s</div>' % fragment)
    except etree.XMLSyntaxError:
        try:
            racine = etree.fromstring('<div>%s</div>' % fragment, etree.HTMLParser())
        except Exception:  # noqa: BLE001
            return None
    return [(el.tag, tuple(sorted(el.attrib.items()))) for el in racine.iter()
            if isinstance(el.tag, str) and el.tag not in ('html', 'body')]


def _sans_balises(texte):
    return re.sub(r'<[^>]+>', ' ', texte or '').strip()


class LolirineTradMemoire(models.Model):
    _name = 'lolirine.trad.memoire'
    _description = 'Mémoire de traduction des fiches'

    empreinte = fields.Char(required=True, index=True)
    source = fields.Text(required=True)
    nl = fields.Text()
    en = fields.Text()

    @api.model
    def chercher(self, textes):
        """{texte: (nl, en)} pour les textes déjà traduits."""
        if not textes:
            return {}
        par_emp = {_empreinte(t): t for t in textes}
        trouves = self.search([('empreinte', 'in', list(par_emp))])
        return {par_emp[m.empreinte]: (m.nl, m.en) for m in trouves if m.nl and m.en}

    @api.model
    def retenir(self, paires):
        """paires : {texte: (nl, en)}"""
        connus = set(self.search([('empreinte', 'in', [_empreinte(t) for t in paires])]).mapped('empreinte'))
        self.create([{'empreinte': _empreinte(t), 'source': t, 'nl': nl, 'en': en}
                     for t, (nl, en) in paires.items() if nl and en and _empreinte(t) not in connus])


class LolirineTradFiche(models.Model):
    _name = 'lolirine.trad.fiche'
    _description = 'Traduction automatique : suivi par fiche'
    _order = 'write_date desc'

    product_tmpl_id = fields.Many2one('product.template', 'Fiche', required=True, index=True, ondelete='cascade')
    lot_id = fields.Many2one('lolirine.trad.lot', 'Lot', index=True, ondelete='set null')
    state = fields.Selection([('envoye', 'Envoyée'), ('fait', 'Traduite'), ('erreur', 'Erreur')],
                             'État', default='envoye', index=True)
    essais = fields.Integer(default=0)
    erreur = fields.Text()
    meta_title_fr = fields.Char('Titre Google (FR)')
    meta_title_nl = fields.Char('Titre Google (NL)')
    meta_description_fr = fields.Text('Description Google (FR)')
    termes = fields.Integer('Textes HTML traduits')
    termes_envoyes = fields.Text('Textes envoyés (JSON)')


class LolirineTradLot(models.Model):
    _name = 'lolirine.trad.lot'
    _description = 'Traduction automatique : lot envoyé à Claude'
    _order = 'id desc'

    name = fields.Char('Lot Anthropic', readonly=True)
    state = fields.Selection([('en_cours', 'En cours'), ('termine', 'Terminé'), ('erreur', 'Erreur')],
                             'État', default='en_cours', index=True)
    nb_fiches = fields.Integer('Fiches')
    nb_ok = fields.Integer('Traduites')
    nb_erreurs = fields.Integer('Erreurs')
    tokens_entree = fields.Integer('Tokens en entrée')
    tokens_sortie = fields.Integer('Tokens en sortie')
    fiche_ids = fields.One2many('lolirine.trad.fiche', 'lot_id', 'Fiches')
    note = fields.Text()

    # ── paramètres ────────────────────────────────────────────────────────
    @api.model
    def _param(self, cle, defaut=''):
        return self.env['ir.config_parameter'].sudo().get_param(P + cle, defaut)

    @api.model
    def _entetes(self):
        cle = self.env['ir.config_parameter'].sudo().get_param('lolirine_ai_chat.api_key')
        if not cle:
            raise ValueError("Clé API Claude absente (paramètre lolirine_ai_chat.api_key)")
        return {'x-api-key': cle, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'}

    # ── sélection des fiches ──────────────────────────────────────────────
    @api.model
    def _fiches_a_traiter(self, limite):
        Tmpl = self.env['product.template'].sudo().with_context(active_test=True)
        deja = self.env['lolirine.trad.fiche'].sudo().search(
            ['|', ('state', 'in', ('envoye', 'fait')), ('essais', '>=', 3)]).mapped('product_tmpl_id').ids
        dom = [('website_id', 'in', [False, SITE]), ('is_published', '=', True), ('sale_ok', '=', True)]
        if deja:
            dom.append(('id', 'not in', deja))
        ids_test = [int(x) for x in re.findall(r'\d+', self._param('fiches_test', ''))]
        if ids_test:
            dom.append(('id', 'in', ids_test))
        return Tmpl.search(dom, limit=limite, order='id')

    @api.model
    def _termes_manquants(self, tmpl):
        """{champ: [termes source]} pour les termes HTML non traduits en nl ou en."""
        res = {}
        for champ in CHAMPS_HTML:
            if champ not in tmpl._fields or not tmpl[champ]:
                continue
            lst, _ctx = tmpl.get_field_translations(champ, langs=list(LANGUES.values()))
            manque = []
            for t in lst:
                src = t['source']
                if not re.search(r'[A-Za-zÀ-ÿ]{2}', _sans_balises(src)):
                    continue
                if (not t['value'] or t['value'] == src) and src not in manque:
                    manque.append(src)
            if manque:
                res[champ] = manque
        return res

    @api.model
    def _charge(self, tmpl):
        """Contenu JSON envoyé à Claude pour une fiche, + termes déjà connus."""
        fr = tmpl.with_context(lang='fr_BE')
        nl = tmpl.with_context(lang='nl_NL')
        termes = self._termes_manquants(fr)
        tous = list(dict.fromkeys(t for lst in termes.values() for t in lst))
        connus = self.env['lolirine.trad.memoire'].sudo().chercher(tous)
        a_traduire = [t for t in tous if t not in connus]
        categ = fr.public_categ_ids.filtered(lambda c: c.website_id.id in (False, SITE))[:1]
        marque = ''
        if 'pool_brand_id' in fr._fields and fr.pool_brand_id:
            marque = fr.pool_brand_id.name
        elif 'x_pool_brand' in fr._fields and fr.x_pool_brand:
            marque = fr.x_pool_brand if isinstance(fr.x_pool_brand, str) else fr.x_pool_brand.display_name
        meta = fr.website_meta_description or ''
        charge = {
            'nom': fr.name if nl.name == fr.name or not nl.name else '',
            'description_courte': (fr.description_sale or '')
            if (fr.description_sale and nl.description_sale == fr.description_sale) else '',
            'categorie': categ.display_name if categ else '',
            'marque': marque,
            'reference': fr.default_code or '',
            'description_produit': _sans_balises(fr.description_ecommerce or '')[:1500],
            'rediger_meta': not meta or bool(META_AUTO.search(meta)),
            'meta_description_actuelle': meta if meta and not META_AUTO.search(meta) else '',
            'termes': a_traduire,
        }
        return charge, connus

    # ── envoi ─────────────────────────────────────────────────────────────
    @api.model
    def _cron_soumettre(self):
        if self._param('actif') != 'True':
            return
        if self.search_count([('state', '=', 'en_cours')]):
            return
        limite = int(self._param('lot_max', '20') or 20)
        modele = self._param('modele') or self._param_ia('model') or 'claude-sonnet-5-5'
        fiches = self._fiches_a_traiter(limite)
        if not fiches:
            _logger.info("Traduction des fiches : plus rien à traduire")
            return
        requetes, suivis = [], []
        Fiche = self.env['lolirine.trad.fiche'].sudo()
        for tmpl in fiches:
            try:
                charge, _connus = self._charge(tmpl)
            except Exception as e:  # noqa: BLE001
                _logger.exception("Traduction : fiche %s non préparée", tmpl.id)
                suivi = Fiche.search([('product_tmpl_id', '=', tmpl.id)], limit=1) or Fiche.create(
                    {'product_tmpl_id': tmpl.id})
                suivi.write({'state': 'erreur', 'essais': suivi.essais + 1, 'erreur': str(e)[:500]})
                continue
            requetes.append({
                'custom_id': 'tmpl-%d' % tmpl.id,
                'params': {
                    'model': modele,
                    'max_tokens': 16000,
                    'system': [{'type': 'text', 'text': CONSIGNES, 'cache_control': {'type': 'ephemeral'}}],
                    'messages': [{'role': 'user', 'content': json.dumps(charge, ensure_ascii=False)}],
                },
            })
            suivis.append((tmpl.id, charge['termes']))
        if not requetes:
            return
        rep = requests.post(URL_LOTS, headers=self._entetes(), json={'requests': requetes}, timeout=120)
        if rep.status_code >= 300:
            _logger.error("Traduction : envoi du lot refusé (%s) %s", rep.status_code, rep.text[:500])
            return
        lot = self.create({'name': rep.json().get('id'), 'nb_fiches': len(suivis)})
        for tid, termes in suivis:
            suivi = Fiche.search([('product_tmpl_id', '=', tid)], limit=1)
            vals = {'lot_id': lot.id, 'state': 'envoye', 'erreur': False,
                    'termes_envoyes': json.dumps(termes, ensure_ascii=False)}
            if suivi:
                suivi.write(dict(vals, essais=suivi.essais + 1))
            else:
                Fiche.create(dict(vals, product_tmpl_id=tid, essais=1))
        _logger.info("Traduction : lot %s envoyé (%d fiches)", lot.name, len(suivis))

    @api.model
    def _param_ia(self, cle):
        return self.env['ir.config_parameter'].sudo().get_param('lolirine_ai_chat.' + cle, '')

    # ── récupération ──────────────────────────────────────────────────────
    @api.model
    def _cron_recuperer(self):
        for lot in self.search([('state', '=', 'en_cours')]):
            try:
                lot._recuperer()
            except Exception as e:  # noqa: BLE001
                _logger.exception("Traduction : lot %s non récupéré", lot.name)
                lot.note = str(e)[:1000]

    def _recuperer(self):
        self.ensure_one()
        entetes = self._entetes()
        rep = requests.get('%s/%s' % (URL_LOTS, self.name), headers=entetes, timeout=60)
        rep.raise_for_status()
        info = rep.json()
        if info.get('processing_status') != 'ended':
            return
        res = requests.get(info['results_url'], headers=entetes, timeout=300)
        res.raise_for_status()
        Fiche = self.env['lolirine.trad.fiche'].sudo()
        ok = ko = t_in = t_out = 0
        debut = time.time()
        for ligne in res.text.splitlines():
            if not ligne.strip():
                continue
            if time.time() - debut > 600:
                # au-delà de 10 min, on s'arrête : le passage suivant reprend où on en est
                _logger.info("Traduction : lot %s appliqué en partie, suite au prochain passage", self.name)
                return
            r = json.loads(ligne)
            tid = int(r['custom_id'].split('-')[1])
            suivi = Fiche.search([('product_tmpl_id', '=', tid)], limit=1)
            if suivi.lot_id == self and suivi.state in ('fait', 'erreur'):
                ok += suivi.state == 'fait'
                ko += suivi.state == 'erreur'
                continue
            resultat = r.get('result') or {}
            if resultat.get('type') != 'succeeded':
                ko += 1
                suivi.write({'state': 'erreur', 'erreur': json.dumps(resultat)[:1000]})
                continue
            message = resultat['message']
            usage = message.get('usage') or {}
            t_in += (usage.get('input_tokens') or 0) + (usage.get('cache_read_input_tokens') or 0) \
                + (usage.get('cache_creation_input_tokens') or 0)
            t_out += usage.get('output_tokens') or 0
            texte = ''.join(b.get('text', '') for b in message.get('content', []) if b.get('type') == 'text')
            try:
                donnees = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', texte.strip()))
                n_termes = self._appliquer(self.env['product.template'].sudo().browse(tid), donnees, suivi)
                suivi.write({'state': 'fait', 'erreur': False, 'termes': n_termes})
                ok += 1
            except Exception as e:  # noqa: BLE001
                _logger.exception("Traduction : fiche %s non appliquée", tid)
                self.env.cr.rollback()
                self.env.invalidate_all()
                suivi = Fiche.search([('product_tmpl_id', '=', tid)], limit=1)
                suivi.write({'state': 'erreur', 'erreur': ('%s\n%s' % (e, texte[:800]))[:1500]})
                ko += 1
            self.env.cr.commit()
        self.write({'state': 'termine', 'nb_ok': ok, 'nb_erreurs': ko,
                    'tokens_entree': t_in, 'tokens_sortie': t_out})
        self.env.cr.commit()
        _logger.info("Traduction : lot %s terminé — %d fiches traduites, %d erreurs", self.name, ok, ko)

    # ── écriture sur la fiche ─────────────────────────────────────────────
    @api.model
    def _appliquer(self, tmpl, d, suivi):
        if not tmpl.exists():
            return 0
        fr = tmpl.with_context(lang='fr_BE')
        nl_rec = tmpl.with_context(lang='nl_NL')
        en_rec = tmpl.with_context(lang='en_GB')
        d_fr, d_nl, d_en = d.get('fr') or {}, d.get('nl') or {}, d.get('en') or {}

        # 1. termes HTML : réponse de Claude + mémoire
        charge_termes = self._termes_manquants(fr)
        tous = list(dict.fromkeys(t for lst in charge_termes.values() for t in lst))
        memoire = self.env['lolirine.trad.memoire'].sudo()
        connus = memoire.chercher(tous)
        # textes envoyés à Claude pour cette fiche, dans l'ordre (mémorisés à l'envoi)
        envoyes = json.loads(suivi.termes_envoyes or '[]')
        nl_t, en_t = d_nl.get('termes') or [], d_en.get('termes') or []
        nouveaux = {}
        if len(nl_t) == len(envoyes) == len(en_t):
            for src, tnl, ten in zip(envoyes, nl_t, en_t):
                ref = _balises(src)
                if ref is not None and _balises(tnl) == ref and _balises(ten) == ref:
                    nouveaux[src] = (tnl, ten)
        elif envoyes:
            _logger.warning("Traduction fiche %s : %d termes attendus, %d/%d reçus",
                            tmpl.id, len(envoyes), len(nl_t), len(en_t))
        memoire.retenir(nouveaux)
        dispo = dict(connus, **nouveaux)
        n_termes = 0
        for champ, termes in charge_termes.items():
            lst, _ctx = fr.get_field_translations(champ, langs=list(LANGUES.values()))
            actuel = {(t['lang'], t['source']): t['value'] for t in lst}
            maj = {'nl_NL': {}, 'en_GB': {}}
            for src in termes:
                if src not in dispo:
                    continue
                for i, lang in enumerate(('nl_NL', 'en_GB')):
                    v = actuel.get((lang, src))
                    if not v or v == src:
                        maj[lang][src] = dispo[src][i]
            maj = {k: v for k, v in maj.items() if v}
            if maj:
                fr.update_field_translations(champ, maj)
                n_termes += len(maj.get('nl_NL', {}))

        # 2. nom et description courte (jamais par-dessus une traduction existante)
        for champ, cle in (('name', 'nom'), ('description_sale', 'description_courte')):
            src = fr[champ]
            if not src:
                continue
            maj = {}
            if d_nl.get(cle) and (not nl_rec[champ] or nl_rec[champ] == src):
                maj['nl_NL'] = d_nl[cle].strip()
            if d_en.get(cle) and (not en_rec[champ] or en_rec[champ] == src):
                maj['en_GB'] = d_en[cle].strip()
            if maj:
                fr.update_field_translations(champ, maj)

        # 3. titre Google : seulement s'il est vide
        if not fr.website_meta_title and d_fr.get('meta_title'):
            t_fr = d_fr['meta_title'].strip()
            fr.update_field_translations('website_meta_title', {
                'en_US': t_fr, 'fr_BE': t_fr,
                'nl_NL': (d_nl.get('meta_title') or t_fr).strip(),
                'en_GB': (d_en.get('meta_title') or t_fr).strip(),
            })

        # 4. description Google
        meta = fr.website_meta_description or ''
        if (not meta or META_AUTO.search(meta)) and d_fr.get('meta_description'):
            m_fr = d_fr['meta_description'].strip()
            fr.update_field_translations('website_meta_description', {
                'en_US': m_fr, 'fr_BE': m_fr,
                'nl_NL': (d_nl.get('meta_description') or m_fr).strip(),
                'en_GB': (d_en.get('meta_description') or m_fr).strip(),
            })
        elif meta:
            maj = {}
            if d_nl.get('meta_description') and nl_rec.website_meta_description in (False, '', meta):
                maj['nl_NL'] = d_nl['meta_description'].strip()
            if d_en.get('meta_description') and en_rec.website_meta_description in (False, '', meta):
                maj['en_GB'] = d_en['meta_description'].strip()
            if maj:
                fr.update_field_translations('website_meta_description', maj)

        suivi.write({
            'meta_title_fr': (d_fr.get('meta_title') or '')[:255],
            'meta_title_nl': (d_nl.get('meta_title') or '')[:255],
            'meta_description_fr': d_fr.get('meta_description') or '',
        })
        return n_termes
