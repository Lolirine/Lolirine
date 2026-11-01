# -*- coding: utf-8 -*-
"""Matériaux bâtiment : prix des fournisseurs (Carlier Bois, Gobert Matériaux…).

- Fournisseur de matériaux : remise obtenue (20 % chez Carlier), adresse de
  recherche du site, lecteur de prix.
- Matériau : fournisseur, référence et page du produit chez lui, prix public TTC.
  Coût = prix public HT − remise ; prix de vente = prix public HT.
- Lecture du prix public sur la page du produit (Carlier : pro.carlier.be),
  contrôle mensuel des écarts : rien n'est appliqué sans action de l'utilisateur.
- Visionneuse : le site du fournisseur dans Odoo, import d'un article par sa
  référence ou l'adresse de sa page, ajout direct au devis ou à l'ouvrage.
"""
import base64
import html
import logging
import re
from urllib.parse import quote_plus, unquote_plus, urljoin

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TVA = 1.21
LECTEURS = [('carlier', 'Carlier (pro.carlier.be)'), ('aucun', 'Aucun : prix saisi à la main')]
ENTETES = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/126.0 Safari/537.36 Odoo-Lolirine',
    'Accept-Language': 'fr-BE,fr;q=0.9',
}
# unité de vente du fournisseur -> unité Odoo
UNITES = {
    'M2': 'uom.product_uom_square_meter',
    'ML': 'uom.product_uom_meter',
    'M': 'uom.product_uom_meter',
    'M3': 'uom.product_uom_cubic_meter',
    'PCE': 'uom.product_uom_unit',
    'PC': 'uom.product_uom_unit',
    'U': 'uom.product_uom_unit',
    'KG': 'uom.product_uom_kgm',
    'L': 'uom.product_uom_litre',
}


def nombre_fr(texte):
    """'1 234,56' -> 1234.56"""
    return float(re.sub(r'[^\d,]', '', texte).replace(',', '.'))


def lire_page_carlier(page):
    """Extrait d'une page produit pro.carlier.be : nom, référence, prix TTC, unité, image."""
    res = {}
    m = re.search(r'<meta property="og:title" content="([^"]+)"', page)
    if m:
        res['nom'] = html.unescape(m.group(1)).strip()
    m = re.search(r'R[ée]f\s*:\s*([\w\-./]+)\s*<', page) or re.search(r'R&eacute;f\s*:\s*([\w\-./]+)', page)
    if m:
        res['ref'] = m.group(1).strip()
    m = re.search(r'priceByUVte[^>]*>\s*<span>\s*([\d . ]+,\d{2})\s*(?:€|&euro;)\s*TTC\s*/\s*([A-Za-z0-9²]+)', page)
    if m:
        res['prix_ttc'] = nombre_fr(m.group(1))
        res['unite'] = m.group(2).upper().replace('²', '2')
    else:
        m = re.search(r'class="price"[^>]*>\s*<span>\s*([\d . ]+,\d{2})\s*(?:€|&euro;)\s*TTC', page)
        if m:
            res['prix_ttc'] = nombre_fr(m.group(1))
    m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    if m and 'logo' not in m.group(1):
        res['image_url'] = m.group(1)
    m = re.search(r'<meta property="og:url" content="([^"]+)"', page)
    if m:
        res['url'] = m.group(1)
    return res


class ResPartnerFournisseurBat(models.Model):
    _inherit = 'res.partner'

    bat_fournisseur_materiaux = fields.Boolean(
        "Fournisseur de matériaux bâtiment",
        help="Proposé comme fournisseur des matériaux bâtiment (prix public, remise, site).")
    bat_remise_materiaux = fields.Float(
        "Remise sur les matériaux (%)", digits=(5, 2),
        help="Remise obtenue sur le prix public : coût = prix public HT − remise.")
    bat_site_url = fields.Char("Site du fournisseur", help="Page d'accueil du catalogue en ligne.")
    bat_url_recherche = fields.Char(
        "Adresse de recherche",
        help="Adresse de recherche du site, {} étant remplacé par le texte cherché "
             "(ex. https://pro.carlier.be/recherche?term={}).")
    bat_lecteur_prix = fields.Selection(LECTEURS, string="Lecture des prix", default='aucun')

    def _bat_url_recherche(self, texte):
        self.ensure_one()
        if not self.bat_url_recherche:
            return self.bat_site_url or ''
        return self.bat_url_recherche.replace('{}', quote_plus(texte or ''))

    # ── Lecture d'une page produit ───────────────────────────────────
    def _bat_telecharger(self, url):
        try:
            rep = requests.get(url, headers=ENTETES, timeout=20)
            rep.raise_for_status()
        except requests.RequestException as e:
            raise UserError(_("Le site du fournisseur ne répond pas (%s) : %s") % (url, e))
        return rep.text

    def _bat_lire_produit(self, url):
        """Infos d'une page produit du fournisseur (dict vide si pas de lecteur)."""
        self.ensure_one()
        if self.bat_lecteur_prix != 'carlier' or not url:
            return {}
        infos = lire_page_carlier(self._bat_telecharger(url))
        infos.setdefault('url', url)
        if '/produit/' not in (infos.get('url') or '') or not infos.get('nom'):
            return {}      # page de recherche, de rubrique… : pas une fiche produit
        return infos

    def _bat_trouver_par_ref(self, ref):
        """Carlier : recherche de la référence, puis lecture des pages trouvées jusqu'à la bonne."""
        self.ensure_one()
        if self.bat_lecteur_prix != 'carlier':
            return {}
        page = self._bat_telecharger(self._bat_url_recherche(ref))
        liens = []
        m = re.search(r'R[ée]f\s*:\s*%s\s*<' % re.escape(ref), page)
        if m:
            avant = re.findall(r'href="([^"]*/produit/[^"]+)"', page[:m.start()])
            if avant:
                liens.append(urljoin(self.bat_site_url or 'https://pro.carlier.be/', html.unescape(avant[-1])))
        for lien in re.findall(r'href="([^"]*/produit/[^"]+)"', page):
            lien = urljoin(self.bat_site_url or 'https://pro.carlier.be/', html.unescape(lien))
            if lien not in liens:
                liens.append(lien)
        for lien in liens[:12]:
            infos = self._bat_lire_produit(lien)
            if (infos.get('ref') or '').upper() == ref.upper():
                return infos
        return {}


class ProductTemplateFournisseurBat(models.Model):
    _inherit = 'product.template'

    bat_est_materiau = fields.Boolean(compute='_compute_bat_est_materiau')
    bat_fournisseur_id = fields.Many2one(
        'res.partner', "Fournisseur (matériaux)", domain=[('bat_fournisseur_materiaux', '=', True)])
    bat_ref_fournisseur = fields.Char("Référence fournisseur")
    bat_url_fournisseur = fields.Char("Page chez le fournisseur")
    bat_unite_fournisseur = fields.Char("Unité de vente fournisseur", help="Ex. M2, PCE, ML.")
    bat_prix_public_ttc = fields.Float("Prix public TTC", digits='Product Price',
                                       help="Prix public affiché par le fournisseur, TVA 21 % comprise.")
    bat_prix_public_ht = fields.Float("Prix public HT", digits='Product Price',
                                      compute='_compute_bat_prix', store=True)
    bat_remise = fields.Float("Remise (%)", related='bat_fournisseur_id.bat_remise_materiaux')
    bat_cout_remise = fields.Float("Coût après remise", digits='Product Price',
                                   compute='_compute_bat_prix', store=True)
    bat_prix_releve_le = fields.Date("Prix relevé le")
    bat_prix_lu_ttc = fields.Float("Dernier prix lu TTC", digits='Product Price',
                                   help="Prix public lu lors du dernier contrôle sur le site du fournisseur.")
    bat_prix_lu_le = fields.Date("Contrôlé le")
    bat_prix_a_jour = fields.Selection(
        [('ok', 'À jour'), ('change', 'Prix fournisseur changé'), ('applique', 'À appliquer')],
        string="État du prix", compute='_compute_bat_prix_a_jour', store=True)

    @api.depends('categ_id', 'bat_fournisseur_id', 'type')
    def _compute_bat_est_materiau(self):
        categ = self.env.ref('lolirine_batiment.categ_batiment', raise_if_not_found=False)
        for t in self:
            t.bat_est_materiau = t.type != 'service' and (bool(t.bat_fournisseur_id) or bool(
                categ and t.categ_id and t.categ_id.parent_path and
                t.categ_id.parent_path.startswith(categ.parent_path or '-')))

    @api.depends('bat_prix_public_ttc', 'bat_fournisseur_id.bat_remise_materiaux')
    def _compute_bat_prix(self):
        for t in self:
            ht = round(t.bat_prix_public_ttc / TVA, 2) if t.bat_prix_public_ttc else 0.0
            t.bat_prix_public_ht = ht
            t.bat_cout_remise = round(ht * (1 - (t.bat_fournisseur_id.bat_remise_materiaux or 0.0) / 100.0), 2)

    @api.depends('bat_prix_public_ttc', 'bat_prix_lu_ttc', 'bat_prix_public_ht', 'list_price', 'standard_price')
    def _compute_bat_prix_a_jour(self):
        for t in self:
            if not t.bat_prix_public_ttc:
                t.bat_prix_a_jour = False
            elif t.bat_prix_lu_ttc and abs(t.bat_prix_lu_ttc - t.bat_prix_public_ttc) > 0.005:
                t.bat_prix_a_jour = 'change'
            elif abs(t.list_price - t.bat_prix_public_ht) > 0.005 or abs(t.standard_price - t.bat_cout_remise) > 0.005:
                t.bat_prix_a_jour = 'applique'
            else:
                t.bat_prix_a_jour = 'ok'

    # ── Actions de la fiche ──────────────────────────────────────────
    def action_bat_voir_fournisseur(self):
        self.ensure_one()
        return self.env['product.template']._bat_action_visionneuse(produit=self)

    def action_bat_lire_prix(self):
        """Lit le prix public sur la page du produit chez le fournisseur (sans l'appliquer)."""
        lus, erreurs = 0, []
        for t in self:
            f = t.bat_fournisseur_id
            if not f or f.bat_lecteur_prix == 'aucun':
                continue
            try:
                infos = f._bat_lire_produit(t.bat_url_fournisseur) if t.bat_url_fournisseur \
                    else f._bat_trouver_par_ref(t.bat_ref_fournisseur or '')
            except UserError as e:
                erreurs.append("%s : %s" % (t.display_name, e.args[0]))
                continue
            if not infos.get('prix_ttc'):
                erreurs.append(_("%s : prix introuvable sur la page.") % t.display_name)
                continue
            vals = {'bat_prix_lu_ttc': infos['prix_ttc'], 'bat_prix_lu_le': fields.Date.today()}
            if not t.bat_url_fournisseur and infos.get('url'):
                vals['bat_url_fournisseur'] = infos['url']
            if not t.bat_unite_fournisseur and infos.get('unite'):
                vals['bat_unite_fournisseur'] = infos['unite']
            if not t.bat_prix_public_ttc:
                vals['bat_prix_public_ttc'] = infos['prix_ttc']
            t.write(vals)
            lus += 1
        if len(self) == 1 and erreurs:
            raise UserError(erreurs[0])
        return self._bat_notification(
            _("Prix lus : %s") % lus + (("\n" + "\n".join(erreurs[:5])) if erreurs else ''),
            'warning' if erreurs else 'success')

    def action_bat_appliquer_prix(self):
        """Prix lu -> prix public ; coût = public HT − remise ; vente = public HT ; ligne fournisseur."""
        for t in self:
            if t.bat_prix_lu_ttc:
                t.bat_prix_public_ttc = t.bat_prix_lu_ttc
            if not t.bat_prix_public_ttc:
                continue
            t.write({
                'standard_price': t.bat_cout_remise,
                'list_price': t.bat_prix_public_ht,
                'bat_prix_releve_le': t.bat_prix_lu_le or fields.Date.today(),
            })
            t._bat_ligne_fournisseur()
        return self._bat_notification(_("Prix appliqués sur %s article(s).") % len(self), 'success')

    def _bat_ligne_fournisseur(self):
        """Ligne fournisseur : prix public HT, remise, référence (bons de commande au bon prix)."""
        for t in self.filtered('bat_fournisseur_id'):
            info = t.seller_ids.filtered(lambda s: s.partner_id == t.bat_fournisseur_id)[:1]
            vals = {
                'partner_id': t.bat_fournisseur_id.id,
                'product_code': t.bat_ref_fournisseur or False,
                'price': t.bat_prix_public_ht,
                'discount': t.bat_fournisseur_id.bat_remise_materiaux or 0.0,
                'product_tmpl_id': t.id,
            }
            if info:
                info.write(vals)
            else:
                self.env['product.supplierinfo'].create(vals)

    def _bat_notification(self, message, genre):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': message, 'type': genre, 'sticky': genre != 'success'}}

    @api.model
    def _cron_bat_controle_prix(self):
        """Contrôle mensuel : relit les prix publics, signale les changements (rien n'est appliqué)."""
        produits = self.search([('bat_fournisseur_id.bat_lecteur_prix', '=', 'carlier'),
                                '|', ('bat_url_fournisseur', '!=', False), ('bat_ref_fournisseur', '!=', False)])
        for t in produits:
            try:
                t.action_bat_lire_prix()
                self.env.cr.commit()
            except Exception as e:  # un article en erreur ne bloque pas les autres
                self.env.cr.rollback()
                _logger.warning("Contrôle du prix fournisseur %s : %s", t.display_name, e)
        changes = produits.filtered(lambda t: t.bat_prix_a_jour == 'change')
        if changes:
            admin = self.env.ref('base.user_admin', raise_if_not_found=False)
            for t in changes:
                t.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=(admin or self.env.user).id,
                    summary=_("Prix fournisseur changé : %.2f → %.2f TTC") % (t.bat_prix_public_ttc, t.bat_prix_lu_ttc))
            _logger.info("Prix fournisseur changés : %s", len(changes))

    # ── Visionneuse des sites fournisseurs ───────────────────────────
    @api.model
    def _bat_action_visionneuse(self, produit=None, res_model=None, res_id=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'lolirine_bat_fournisseurs',
            'name': _("Fournisseurs de matériaux"),
            'params': {'produit_id': produit.id if produit else False,
                       'res_model': res_model, 'res_id': res_id},
            'target': 'current',
        }

    @api.model
    def bat_visionneuse_donnees(self, produit_id=False, res_model=False, res_id=False):
        fournisseurs = self.env['res.partner'].search([('bat_fournisseur_materiaux', '=', True)], order='name')
        res = {
            'fournisseurs': [{
                'id': f.id, 'nom': f.name, 'remise': f.bat_remise_materiaux,
                'site': f.bat_site_url or '', 'recherche': f.bat_url_recherche or '',
                'lecteur': f.bat_lecteur_prix,
            } for f in fournisseurs],
            'cible': False, 'produit': False, 'materiaux': self._bat_materiaux_liste(),
        }
        if produit_id:
            t = self.browse(produit_id)
            res['produit'] = t._bat_infos()
        if res_model in ('sale.order', 'lolirine.pool.prestation') and res_id:
            rec = self.env[res_model].browse(res_id)
            res['cible'] = {'model': res_model, 'id': rec.id, 'nom': rec.display_name,
                            'lignes': self._bat_lignes_cible(rec)}
        return res

    @api.model
    def _bat_materiaux_liste(self):
        categ = self.env.ref('lolirine_batiment.categ_batiment', raise_if_not_found=False)
        if not categ:
            return []
        return [t._bat_infos() for t in self.search(
            [('categ_id', 'child_of', categ.id), ('type', '!=', 'service')], order='name')]

    def _bat_infos(self):
        self.ensure_one()
        return {
            'id': self.id, 'nom': self.name, 'code': self.default_code or '',
            'fournisseur': self.bat_fournisseur_id.name or '', 'fournisseur_id': self.bat_fournisseur_id.id,
            'ref': self.bat_ref_fournisseur or '', 'url': self.bat_url_fournisseur or '',
            'unite': self.uom_id.name or '', 'unite_f': self.bat_unite_fournisseur or '',
            'public_ttc': self.bat_prix_public_ttc, 'public_ht': self.bat_prix_public_ht,
            'cout': self.standard_price, 'vente': self.list_price,
            'majoration': self.pool_majoration_defaut or '0', 'etat': self.bat_prix_a_jour or '',
        }

    @api.model
    def _bat_lignes_cible(self, rec):
        if rec._name == 'sale.order':
            return [{'nom': l.name.split('\n')[0], 'qte': l.product_uom_qty, 'prix': l.price_unit,
                     'unite': l.product_uom_id.name or ''}
                    for l in rec.order_line if not l.display_type and l.product_id.type != 'service']
        return [{'nom': f.product_id.display_name or f.name, 'qte': f.quantite, 'prix': f.prix_unitaire,
                 'unite': f.product_id.uom_id.name or ''} for f in rec.fourniture_ids]

    @api.model
    def bat_importer_article(self, fournisseur_id, texte):
        """Crée ou met à jour un matériau depuis l'adresse de sa page ou sa référence chez le fournisseur."""
        f = self.env['res.partner'].browse(fournisseur_id).exists()
        texte = (texte or '').strip()
        if not f or not texte:
            raise UserError(_("Choisis le fournisseur et colle la référence ou l'adresse de la page du produit."))
        if f.bat_lecteur_prix != 'carlier':
            raise UserError(_("Pas de lecture automatique pour %s : crée l'article à la main "
                              "(référence, page et prix public sur la fiche).") % f.name)
        if texte.startswith('http') and '/produit/' not in texte:
            terme = re.search(r'[?&]term=([^&#]+)', texte)
            if not terme:
                raise UserError(_("Ce lien n'est pas celui d'un produit. Sur le site, fais un clic droit sur le produit "
                                  "(sa photo ou son nom) > Copier l'adresse du lien, ou colle sa référence (Réf : …)."))
            texte = unquote_plus(terme.group(1)).strip()
        infos = f._bat_lire_produit(texte) if texte.startswith('http') else f._bat_trouver_par_ref(texte)
        if not infos.get('prix_ttc') or not infos.get('ref'):
            raise UserError(_("Produit introuvable chez %s pour « %s ». Colle l'adresse de la page du produit "
                              "(clic droit sur le produit > Copier l'adresse du lien).") % (f.name, texte))
        t = self.search([('bat_fournisseur_id', '=', f.id), ('bat_ref_fournisseur', '=', infos['ref'])], limit=1)
        nouveau = not t
        if nouveau:
            categ = self.env.ref('lolirine_batiment.categ_batiment')
            vals = {
                'name': infos.get('nom') or infos['ref'], 'type': 'consu', 'categ_id': categ.id,
                'sale_ok': True, 'purchase_ok': True, 'is_published': False,
                'default_code': 'BAT-%s-%s' % ((f.name or 'F')[:3].upper(), infos['ref']),
                'bat_fournisseur_id': f.id, 'bat_ref_fournisseur': infos['ref'],
            }
            uom = self.env.ref(UNITES.get(infos.get('unite') or '', ''), raise_if_not_found=False) \
                if infos.get('unite') in UNITES else None
            if uom:
                vals['uom_id'] = uom.id
                if 'uom_po_id' in self._fields:
                    vals['uom_po_id'] = uom.id
            t = self.create(vals)
            if infos.get('image_url'):
                try:
                    img = requests.get(infos['image_url'], headers=ENTETES, timeout=20)
                    if img.ok and img.headers.get('content-type', '').startswith('image'):
                        t.image_1920 = base64.b64encode(img.content)
                except requests.RequestException:
                    pass
        t.write({
            'bat_url_fournisseur': infos.get('url') or t.bat_url_fournisseur,
            'bat_unite_fournisseur': infos.get('unite') or t.bat_unite_fournisseur,
            'bat_prix_lu_ttc': infos['prix_ttc'], 'bat_prix_lu_le': fields.Date.today(),
        })
        if nouveau:
            t.action_bat_appliquer_prix()
        res = t._bat_infos()
        res['nouveau'] = nouveau
        res['avertissement'] = '' if nouveau or not infos.get('unite') or not t.bat_unite_fournisseur \
            or infos['unite'] == t.bat_unite_fournisseur else _("Unité différente chez le fournisseur : %s") % infos['unite']
        return res

    @api.model
    def bat_ajouter(self, res_model, res_id, produit_id, qte):
        """Ajoute le matériau au devis (ligne) ou à l'ouvrage (fourniture)."""
        t = self.browse(produit_id)
        qte = float(qte or 1.0)
        if res_model == 'sale.order':
            so = self.env['sale.order'].browse(res_id)
            if so.state not in ('draft', 'sent'):
                raise UserError(_("Le devis %s n'est plus modifiable.") % so.name)
            self.env['sale.order.line'].create({
                'order_id': so.id, 'product_id': t.product_variant_id.id, 'product_uom_qty': qte,
                'price_unit': t.list_price})
            rec = so
        elif res_model == 'lolirine.pool.prestation':
            rec = self.env['lolirine.pool.prestation'].browse(res_id)
            rec.write({'fourniture_ids': [(0, 0, {
                'product_id': t.product_variant_id.id, 'name': t.name, 'quantite': qte,
                'prix_unitaire': t.list_price, 'cout_unitaire': t.standard_price})]})
        else:
            raise UserError(_("Ouvre la visionneuse depuis un devis ou un ouvrage pour y ajouter un article."))
        return self._bat_lignes_cible(rec)


class SaleOrderFournisseurBat(models.Model):
    _inherit = 'sale.order'

    def action_bat_fournisseurs(self):
        self.ensure_one()
        return self.env['product.template']._bat_action_visionneuse(res_model='sale.order', res_id=self.id)


class PoolPrestationFournisseurBat(models.Model):
    _inherit = 'lolirine.pool.prestation'

    def action_bat_fournisseurs(self):
        self.ensure_one()
        return self.env['product.template']._bat_action_visionneuse(
            res_model='lolirine.pool.prestation', res_id=self.id)
