# -*- coding: utf-8 -*-
"""Procès-verbal de réception de fin de chantier, signé par le client sur place (téléphone / tablette)."""
import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .pool_parc import CATEGORIES_EQUIPEMENT, deviner_categorie

_logger = logging.getLogger(__name__)

ARTICLES_GENERIQUES = ('FOURN-', 'ELEC-')


class PoolPv(models.Model):
    _name = 'lolirine.pool.pv'
    _description = "Procès-verbal de réception (chantier piscine)"
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char("Référence", compute='_compute_name', store=True)
    order_id = fields.Many2one('sale.order', string="Chantier (commande)", required=True, ondelete='cascade',
                               index=True)
    partner_id = fields.Many2one(related='order_id.partner_id', store=True, string="Client")
    company_id = fields.Many2one(related='order_id.company_id', store=True)
    adresse_chantier = fields.Char("Adresse du chantier")
    date = fields.Date("Date de réception", required=True, default=fields.Date.context_today)
    technicien = fields.Char("Technicien")
    avec_reserves = fields.Boolean("Réception avec réserves")
    reserves = fields.Text("Réserves", help="Points à reprendre, avec le délai convenu.")
    travaux = fields.Text("Travaux réalisés")
    ligne_ids = fields.One2many('lolirine.pool.pv.ligne', 'pv_id', string="Équipements posés")
    avancement_100 = fields.Boolean("Main-d'œuvre terminée (avancement à 100 %)", default=True,
                                    help="Passe les lignes de main-d'œuvre à 100 % : le solde devient facturable.")
    signature = fields.Binary("Signature du client", attachment=True, copy=False)
    signe_par = fields.Char("Nom du signataire", copy=False)
    signe_le = fields.Datetime("Signé le", copy=False, readonly=True)
    state = fields.Selection([('draft', 'À signer'), ('signe', 'Signé')], default='draft', tracking=True,
                             string="État")
    attachment_id = fields.Many2one('ir.attachment', string="PDF signé", copy=False, readonly=True)

    @api.depends('order_id.name')
    def _compute_name(self):
        for pv in self:
            pv.name = "PV %s" % (pv.order_id.name or '')

    @api.model
    def _lignes_depuis_commande(self, order):
        lignes = []
        for l in order.order_line.sorted(lambda x: (x.sequence, x.id)):
            if l.display_type or not l.product_id or not l.product_uom_qty or l._pool_ligne_mo():
                continue
            code = (l.product_id.default_code or '').upper()
            if code.startswith(ARTICLES_GENERIQUES) or l.is_downpayment:
                continue
            titre = (l.name or l.product_id.name).split('\n')[0]
            if titre.startswith('[') and '] ' in titre:
                titre = titre.split('] ', 1)[1]
            lignes.append((0, 0, {
                'product_id': l.product_id.id,
                'name': titre,
                'quantite': l.product_uom_qty,
                'categorie': deviner_categorie(titre),
                'a_enregistrer': l.price_unit >= 100,
            }))
        return lignes

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['sale.order'].browse(vals.get('order_id'))
            if order and not vals.get('ligne_ids'):
                vals['ligne_ids'] = self._lignes_depuis_commande(order)
            if order:
                vals.setdefault('adresse_chantier', order.pool_adresse_chantier or order.partner_shipping_id.contact_address)
                vals.setdefault('technicien', order.pool_technicien or self.env.user.name)
                mo = order.order_line.filtered(lambda x: x._pool_ligne_mo() and x.name)
                vals.setdefault('travaux', "\n".join(x.name for x in mo) or False)
        return super().create(vals_list)

    def action_signer(self):
        for pv in self:
            if pv.state == 'signe':
                continue
            if not pv.signature:
                raise UserError(_("Faites signer le client dans le cadre « Signature du client » avant de valider."))
            if not pv.signe_par:
                pv.signe_par = pv.partner_id.name
            pv.write({'state': 'signe', 'signe_le': fields.Datetime.now()})
            order = pv.order_id
            # Parc installé
            Equipement = self.env['lolirine.pool.equipement']
            for ligne in pv.ligne_ids.filtered('a_enregistrer'):
                p = ligne.product_id
                Equipement.create({
                    'name': ligne.name,
                    'partner_id': order.partner_id.id,
                    'adresse_chantier': pv.adresse_chantier,
                    'categorie': ligne.categorie,
                    'product_id': p.id,
                    'marque': p.pool_brand_id.display_name if 'pool_brand_id' in p._fields and p.pool_brand_id else False,
                    'modele': p.default_code,
                    'numero_serie': ligne.numero_serie,
                    'date_pose': pv.date,
                    'garantie_mois': ligne.garantie_mois,
                    'order_id': order.id,
                    'pv_id': pv.id,
                })
            if pv.adresse_chantier and not order.partner_id.pool_adresse_piscine:
                order.partner_id.pool_adresse_piscine = pv.adresse_chantier
            # Avancement de la main-d'œuvre
            if pv.avancement_100:
                for l in order.order_line.filtered(lambda x: x._pool_ligne_mo() and x.qty_delivered_method == 'manual'):
                    l.qty_delivered = l.product_uom_qty
            # PDF signé : chatter du chantier + dossier documents du projet
            try:
                pdf, _type = self.env['ir.actions.report']._render_qweb_pdf('lolirine_pool_sale.action_report_pool_pv', pv.ids)
                att = self.env['ir.attachment'].create({
                    'name': "%s.pdf" % pv.name.replace('/', '_'),
                    'datas': base64.b64encode(pdf),
                    'mimetype': 'application/pdf',
                    'res_model': 'sale.order',
                    'res_id': order.id,
                })
                pv.attachment_id = att
                order.message_post(body=_("Procès-verbal de réception signé par %s%s.")
                                   % (pv.signe_par, _(" (avec réserves)") if pv.avec_reserves else ""),
                                   attachment_ids=att.ids)
                order._pool_classer_documents(att)
            except Exception as e:  # le PV signé reste valable même si le PDF échoue
                _logger.warning("PDF du PV %s non généré : %s", pv.name, e)
                order.message_post(body=_("Procès-verbal de réception signé par %s (PDF non généré : %s).")
                                   % (pv.signe_par, e))
        return True

    def action_imprimer(self):
        return self.env.ref('lolirine_pool_sale.action_report_pool_pv').report_action(self)


class PoolPvLigne(models.Model):
    _name = 'lolirine.pool.pv.ligne'
    _description = "Équipement posé (procès-verbal de réception)"
    _order = 'pv_id, id'

    pv_id = fields.Many2one('lolirine.pool.pv', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Article")
    name = fields.Char("Équipement", required=True)
    quantite = fields.Float("Qté", digits=(10, 2), default=1.0)
    categorie = fields.Selection(CATEGORIES_EQUIPEMENT, string="Catégorie", default='autre')
    numero_serie = fields.Char("N° de série")
    garantie_mois = fields.Integer("Garantie (mois)", default=24)
    a_enregistrer = fields.Boolean("Au parc", default=True,
                                   help="Enregistré dans le parc installé du client (garantie, SAV, entretien).")
