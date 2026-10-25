# -*- coding: utf-8 -*-
"""Pool Store — automatismes de nuit et de fond.

1. Prix Fluidra : chaque nuit, le prix catalogue public de webshop.sibo.nl est
   relu pour chaque fiche Fluidra. Un changement met à jour le prix fournisseur
   (la remise négociée est gardée) et le prix d'achat de la fiche. Les prix de
   vente ne sont JAMAIS modifiés : les fiches vendues à perte (ou sous la marge
   minimale) sont seulement signalées à OdooBot.
2. Factures fournisseurs (Peppol, e-mail, saisie) : chaque facture brouillon
   SCP / Fluidra est rapprochée de son bon dropship (référence P000xx, sinon
   références articles), ligne par ligne. Les lignes rapprochées reçoivent le
   compte analytique de la commande ; le journal passe en « Achats Piscines ».
"""
import json
import logging
import re
import time

import requests
from markupsafe import Markup

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

SIBO_GRAPHQL = 'https://webshop.sibo.nl/graphql'
MARGE_MINI = 0.10  # sous 10 % de marge brute, la fiche est signalée
RE_BON = re.compile(r'\bP\d{5}\b')


def _eur(m):
    return ('%.2f €' % (m or 0.0)).replace('.', ',')


def _odoobot(env, corps, utilisateur_id=2):
    user = env['res.users'].sudo().browse(utilisateur_id).exists()
    if not user:
        return
    try:
        canal = env['discuss.channel'].with_user(env.ref('base.user_root')) \
            .sudo()._get_or_create_chat([user.partner_id.id])
        canal.sudo().message_post(body=corps, author_id=env.ref('base.partner_root').id,
                                  message_type='comment', subtype_xmlid='mail.mt_comment')
    except Exception:  # noqa: BLE001
        _logger.exception("Message OdooBot non posté")


class SupplierDropshipInfo(models.Model):
    _inherit = 'supplier.dropship.info'

    @api.model
    def _pool_prix_sibo(self, refs, budget=300):
        """{REF: prix catalogue} depuis le GraphQL public de Sibo (Fluidra Benelux)."""
        prix, debut = {}, time.time()
        for k in range(0, len(refs), 50):
            if time.time() - debut > budget:
                _logger.warning("Prix Sibo : budget de temps dépassé, %d/%d références lues", k, len(refs))
                break
            lot = refs[k:k + 50]
            q = '{products(filter:{sku:{in:%s}},pageSize:100){items{sku price_range{minimum_price{regular_price{value}}}}}}' \
                % json.dumps(lot)
            try:
                r = requests.get(SIBO_GRAPHQL, params={'query': q}, timeout=30,
                                 headers={'User-Agent': 'Lolirine Pool Store'})
                for it in ((r.json().get('data') or {}).get('products') or {}).get('items') or []:
                    v = it['price_range']['minimum_price']['regular_price']['value']
                    if v:
                        prix[it['sku'].strip().upper()] = float(v)
            except Exception as e:  # noqa: BLE001
                _logger.warning("Prix Sibo : lot %d en erreur : %s", k, e)
        return prix

    @api.model
    def _cron_pool_sync_prix_fluidra(self, appliquer=True, utilisateur_id=2):
        """Relit les prix catalogue Fluidra ; renvoie le résumé (texte) pour contrôle."""
        fluidra = self.env['res.partner'].sudo().with_context(active_test=False) \
            .search([('name', '=', 'Fluidra Benelux')], limit=1)
        if not fluidra:
            return "Fournisseur « Fluidra Benelux » introuvable", [], [], []
        infos = self.sudo().search([('supplier_id', '=', fluidra.id), ('is_active', '=', True)])
        refs = sorted({(i.supplier_product_ref or '').strip().upper() for i in infos
                       if (i.supplier_product_ref or '').strip()})
        catalogue = self._pool_prix_sibo(refs)
        if not catalogue:
            return "Aucun prix obtenu de Sibo (site injoignable ?) — rien n'a changé", [], [], []
        hausses, baisses = [], []
        for i in infos:
            c = catalogue.get((i.supplier_product_ref or '').strip().upper())
            # seules les fiches déjà au prix catalogue + remise sont suivies
            if not c or not i.discount_percent or abs(c - i.price) < 0.005:
                continue
            ancien_net = i.price * (1 - i.discount_percent / 100.0)
            nouveau_net = c * (1 - i.discount_percent / 100.0)
            (hausses if c > i.price else baisses).append((i, i.price, c, ancien_net, nouveau_net))
            if appliquer:
                i.price = c
                t = i.product_tmpl_id
                if abs((t.standard_price or 0) - ancien_net) < 0.02:  # coût aligné sur l'ancien net
                    t.standard_price = round(nouveau_net, 2)
        # fiches vendues sous le coût (ou sous la marge minimale)
        alertes = []
        for i in infos:
            t = i.product_tmpl_id
            if not t.sale_ok or not t.is_published or not t.list_price:
                continue
            net = i.price * (1 - (i.discount_percent or 0) / 100.0)
            if net and t.list_price < net * (1 + MARGE_MINI):
                alertes.append((t, t.list_price, net))
        resume = _("%(n)d prix catalogue relus : %(h)d hausse(s), %(b)d baisse(s) ; %(a)d fiche(s) sous %(m)d %% de marge",
                   n=len(catalogue), h=len(hausses), b=len(baisses), a=len(alertes), m=int(MARGE_MINI * 100))
        if appliquer and (hausses or baisses or alertes):
            base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            def lien(t):
                return Markup('<a href="%s/odoo/action-product.product_template_action/%d">%s</a>') % (
                    base, t.id, t.name)
            corps = Markup('<p>💶 <strong>Prix Fluidra (Sibo)</strong> — %s</p>') % resume
            if hausses:
                corps += Markup('<p><strong>Hausses</strong> (votre prix de vente n\'a pas changé) :</p><ul>%s</ul>') % \
                    Markup('').join(Markup('<li>%s : catalogue %s → %s, achat %s → %s</li>') % (
                        lien(i.product_tmpl_id), _eur(a), _eur(c), _eur(an), _eur(nn))
                        for i, a, c, an, nn in hausses[:25])
            if baisses:
                corps += Markup('<p><strong>Baisses</strong> :</p><ul>%s</ul>') % \
                    Markup('').join(Markup('<li>%s : catalogue %s → %s</li>') % (lien(i.product_tmpl_id), _eur(a), _eur(c))
                                    for i, a, c, _an, _nn in baisses[:15])
            if alertes:
                corps += Markup('<p><strong>⚠ Vendues à perte ou presque</strong> (vente HT ≤ achat + %d %%) :</p><ul>%s</ul>') % (
                    int(MARGE_MINI * 100),
                    Markup('').join(Markup('<li>%s : vente %s HT, achat %s</li>') % (lien(t), _eur(v), _eur(n))
                                    for t, v, n in sorted(alertes, key=lambda x: x[1] - x[2])[:25]))
            _odoobot(self.env, corps, utilisateur_id)
        _logger.info("Prix Fluidra : %s", resume)
        return resume, hausses, baisses, alertes


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _pool_textes(self):
        """Textes de la facture où chercher la référence de notre bon."""
        self.ensure_one()
        textes = [self.ref or '', self.payment_reference or '', self.invoice_origin or '',
                  self.narration or ''] + self.invoice_line_ids.mapped('name')
        for pj in self.env['ir.attachment'].sudo().search([('res_model', '=', 'account.move'),
                                                           ('res_id', '=', self.id)]):
            if pj.mimetype and 'xml' in pj.mimetype and pj.raw:
                try:
                    textes.append(pj.raw.decode('utf-8', 'ignore'))
                except Exception:  # noqa: BLE001
                    pass
        return '\n'.join(t for t in textes if t)

    def _pool_rapprocher_bc(self):
        """Rapproche une facture fournisseur brouillon de ses bons dropship.
        Renvoie un texte décrivant le résultat (ou False si rien à faire)."""
        self.ensure_one()
        if self.move_type != 'in_invoice' or self.state != 'draft':
            return False
        lignes = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        if not lignes or lignes.filtered('purchase_line_id'):
            return False
        PO = self.env['purchase.order'].sudo()
        fournisseur = self.partner_id.commercial_partner_id
        ouverts = PO.search([('is_dropship_order', '=', True), ('state', '!=', 'cancel'),
                             ('partner_id', 'child_of', fournisseur.id)])
        if not ouverts:
            return False
        refs = set(RE_BON.findall(self._pool_textes()))
        bons = ouverts.filtered(lambda p: p.name in refs)
        comment = _('référence %s') % ', '.join(sorted(bons.mapped('name'))) if bons else ''
        lignes_bc = (bons or ouverts.filtered(lambda p: p.invoice_status != 'invoiced')).mapped('order_line') \
            .filtered(lambda pl: not pl.display_type)
        # rapprochement ligne à ligne : réf. fournisseur ou code article dans la ligne facturée
        lien = {}
        for l in lignes:
            texte = ((l.name or '') + ' ' + (l.product_id.default_code or '')).upper()
            candidates = lignes_bc.filtered(
                lambda pl: pl.id not in lien.values() and (
                    (pl.supplier_product_ref and re.search(r'\b%s\b' % re.escape(pl.supplier_product_ref.upper()), texte))
                    or (l.product_id and pl.product_id == l.product_id)))
            if len(candidates.mapped('order_id')) == 1:
                lien[l.id] = candidates[0].id
        if not lien and bons and len(lignes_bc) == 1 and len(lignes) == 1:
            lien[lignes.id] = lignes_bc.id  # une ligne de chaque côté
        if not lien:
            return False
        if not bons:
            bons = self.env['purchase.order.line'].browse(list(lien.values())).mapped('order_id')
            comment = _('articles %s') % ', '.join(bons.mapped('name'))
        # compte analytique de la commande (une seule commande client)
        ventes = bons.mapped('dropship_sale_id')
        compte = ventes._pool_compte_analytique() if len(ventes) == 1 else False
        for l in lignes:
            vals = {}
            if l.id in lien:
                pl = self.env['purchase.order.line'].browse(lien[l.id])
                vals['purchase_line_id'] = pl.id
                if pl.analytic_distribution:
                    vals['analytic_distribution'] = pl.analytic_distribution
            elif compte:  # port, frais de gestion… : imputés à la même commande
                vals['analytic_distribution'] = {str(compte.id): 100}
            if vals:
                l.write(vals)
        maj = {'invoice_origin': ', '.join(bons.mapped('name'))}
        journal = self.env['account.journal'].sudo().search([
            ('code', '=', 'PISC'), ('type', '=', 'purchase'), ('company_id', '=', self.company_id.id)], limit=1)
        if journal and self.journal_id != journal and (not self.name or self.name == '/'):
            maj['journal_id'] = journal.id
        self.write(maj)
        texte = _("Rapprochée de %(bons)s (%(comment)s) : %(n)d ligne(s) sur %(t)d.",
                  bons=', '.join(bons.mapped('name')), comment=comment, n=len(lien), t=len(lignes))
        self.message_post(body=texte)
        for po in bons:
            po.invalidate_recordset()
            po.message_post(body=_("🧾 Facture fournisseur reçue et rapprochée (brouillon) — %s") % (self.ref or self.display_name))
        return texte

    def action_pool_rapprocher_bc(self):
        resultats = [m._pool_rapprocher_bc() or _("%s : aucun bon dropship trouvé") % (m.ref or m.display_name)
                     for m in self]
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Rapprochement'), 'message': '\n'.join(resultats), 'sticky': False,
                       'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'}},
        }

    @api.model
    def _cron_pool_rapprocher_factures(self, utilisateur_id=2):
        fournisseurs = self.env['purchase.order'].sudo().search([('is_dropship_order', '=', True)]) \
            .mapped('partner_id.commercial_partner_id')
        if not fournisseurs:
            return
        depuis = fields.Datetime.subtract(fields.Datetime.now(), days=60)
        factures = self.sudo().search([
            ('move_type', '=', 'in_invoice'), ('state', '=', 'draft'), ('create_date', '>=', depuis),
            ('commercial_partner_id', 'in', fournisseurs.ids)])
        faites = []
        for m in factures:
            try:
                with self.env.cr.savepoint():
                    texte = m._pool_rapprocher_bc()
                if texte:
                    faites.append((m, texte))
            except Exception:  # noqa: BLE001
                _logger.exception("Rapprochement de la facture %s impossible", m.id)
        if faites:
            base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            corps = Markup('<p>🧾 <strong>%s</strong></p><ul>%s</ul>') % (
                _('%d facture(s) fournisseur rapprochée(s) — à vérifier et valider') % len(faites),
                Markup('').join(Markup('<li><a href="%s/odoo/action-account.action_move_in_invoice_type/%d">%s %s</a> — %s%s</li>') % (
                    base, m.id, m.partner_id.name, m.ref or '', t,
                    Markup(' <strong>⚠ écart</strong>') if m.pool_ecart_bc else '') for m, t in faites))
            _odoobot(self.env, corps, utilisateur_id)
