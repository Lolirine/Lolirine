# -*- coding: utf-8 -*-
"""Demandes de prix aux fournisseurs à partir d'un devis bâtiment.

Le devis donne la liste des matériaux (quantités cumulées par article). Un
assistant permet de la relire et de la corriger, de choisir les fournisseurs,
puis crée une demande de prix (bon de commande au stade « demande ») par
fournisseur. Chaque demande s'envoie avec un e-mail « demande de prix avec
remise » modifiable avant l'envoi ; les prix reçus se notent sur la demande,
qui devient la commande au fournisseur retenu.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrderDemandeBat(models.Model):
    _inherit = 'purchase.order'

    bat_devis_id = fields.Many2one('sale.order', "Devis bâtiment", index=True, copy=False,
                                   help="Devis client pour lequel ces matériaux sont demandés.")
    bat_livraison = fields.Selection(
        [('chantier', 'Livraison sur chantier'), ('depot', 'Livraison au dépôt (Boninne)'),
         ('enlevement', 'Enlèvement au magasin')], string="Livraison souhaitée")
    bat_message = fields.Text("Précisions pour le fournisseur")
    bat_date_souhaitee = fields.Date("Livraison souhaitée le")

    def action_rfq_send(self):
        action = super().action_rfq_send()
        modele = self.env.ref('lolirine_batiment.mail_template_demande_prix_batiment', raise_if_not_found=False)
        if (len(self) == 1 and self.bat_devis_id and modele and self.state in ('draft', 'sent')
                and isinstance(action, dict) and isinstance(action.get('context'), dict)):
            action['context']['default_template_id'] = modele.id
        return action


class SaleOrderDemandeBat(models.Model):
    _inherit = 'sale.order'

    bat_demande_prix_ids = fields.One2many('purchase.order', 'bat_devis_id', "Demandes de prix")
    bat_demande_prix_count = fields.Integer(compute='_compute_bat_demande_prix_count')

    @api.depends('bat_demande_prix_ids')
    def _compute_bat_demande_prix_count(self):
        for o in self:
            o.bat_demande_prix_count = len(o.bat_demande_prix_ids)

    def action_bat_demande_prix(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Demande de prix aux fournisseurs"),
            'res_model': 'lolirine.bat.demande.prix.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_bat_voir_demandes_prix(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_rfq')
        action['domain'] = [('bat_devis_id', '=', self.id)]
        action['context'] = {'default_bat_devis_id': self.id, 'create': False}
        if len(self.bat_demande_prix_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.bat_demande_prix_ids.id
        return action


class DemandePrixWizard(models.TransientModel):
    _name = 'lolirine.bat.demande.prix.wizard'
    _description = "Demande de prix aux fournisseurs (devis bâtiment)"

    order_id = fields.Many2one('sale.order', "Devis", required=True, readonly=True)
    fournisseur_ids = fields.Many2many(
        'res.partner', string="Fournisseurs", required=True,
        domain=[('bat_fournisseur_materiaux', '=', True)],
        default=lambda self: self.env['res.partner'].search([('bat_fournisseur_materiaux', '=', True)]))
    date_souhaitee = fields.Date("Livraison souhaitée le")
    bat_livraison = fields.Selection(
        [('chantier', 'Livraison sur chantier'), ('depot', 'Livraison au dépôt (Boninne)'),
         ('enlevement', 'Enlèvement au magasin')], string="Livraison", default='depot', required=True)
    message = fields.Text("Précisions pour le fournisseur")
    ligne_ids = fields.One2many('lolirine.bat.demande.prix.ligne', 'wizard_id', "Matériaux")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        so = self.env['sale.order'].browse(res.get('order_id') or self.env.context.get('default_order_id'))
        if so and 'ligne_ids' in fields_list:
            cumul = {}
            for l in so.order_line.sorted(lambda x: (x.sequence, x.id)):
                if l.display_type or not l.product_id or l.product_id.type == 'service' or not l.product_uom_qty:
                    continue
                cle = (l.product_id.id, l.product_uom_id.id)
                if cle in cumul:
                    cumul[cle]['quantite'] += l.product_uom_qty
                else:
                    cumul[cle] = {'product_id': l.product_id.id, 'quantite': l.product_uom_qty,
                                  'uom_id': l.product_uom_id.id, 'retenir': True}
            res['ligne_ids'] = [(0, 0, v) for v in cumul.values()]
            if so.commitment_date and 'date_souhaitee' in fields_list:
                res['date_souhaitee'] = so.commitment_date.date()
        return res

    def action_creer(self):
        self.ensure_one()
        lignes = self.ligne_ids.filtered(lambda l: l.retenir and l.product_id and l.quantite > 0)
        if not lignes:
            raise UserError(_("Aucun matériau retenu pour la demande de prix."))
        if not self.fournisseur_ids:
            raise UserError(_("Choisis au moins un fournisseur."))
        so = self.order_id
        PO = self.env['purchase.order']
        date = fields.Datetime.to_datetime(self.date_souhaitee) if self.date_souhaitee else False
        demandes = PO
        for f in self.fournisseur_ids:
            vals = {
                'partner_id': f.id, 'origin': so.name, 'bat_devis_id': so.id,
                'bat_livraison': self.bat_livraison, 'bat_message': self.message or False,
                'bat_date_souhaitee': self.date_souhaitee,
                'order_line': [],
            }
            if date:
                vals['date_planned'] = date
            for l in lignes:
                ligne = {'product_id': l.product_id.id, 'product_qty': l.quantite}
                if l.uom_id:
                    ligne['product_uom_id'] = l.uom_id.id
                if date:
                    ligne['date_planned'] = date
                vals['order_line'].append((0, 0, ligne))
            po = PO.create(vals)
            for pl in po.order_line:
                code = pl.product_id.seller_ids.filtered(
                    lambda x: x.partner_id == f.commercial_partner_id)[:1].product_code
                if not code:      # pas de référence chez ce fournisseur : nom seul, sans notre code interne
                    pl.name = pl.product_id.name
            demandes |= po
        so.message_post(body=_("Demande de prix préparée pour %s : %s.") % (
            ", ".join(self.fournisseur_ids.mapped('name')), ", ".join(demandes.mapped('name'))))
        if len(demandes) == 1:
            return demandes.with_context(send_rfq=True).action_rfq_send()
        return so.action_bat_voir_demandes_prix()


class DemandePrixLigne(models.TransientModel):
    _name = 'lolirine.bat.demande.prix.ligne'
    _description = "Matériau de la demande de prix"

    wizard_id = fields.Many2one('lolirine.bat.demande.prix.wizard', required=True, ondelete='cascade')
    retenir = fields.Boolean("Demander", default=True)
    product_id = fields.Many2one('product.product', "Article", required=True,
                                 domain=[('purchase_ok', '=', True)])
    quantite = fields.Float("Quantité", digits='Product Unit', default=1.0)
    uom_id = fields.Many2one('uom.uom', "Unité")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
