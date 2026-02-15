# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_dropship_order = fields.Boolean(string='BC Dropshipping', default=False, tracking=True)
    dropship_sale_id = fields.Many2one(
        'sale.order', string='Commande client dropship',
        copy=False, index=True,
    )
    dropship_sent_to_supplier = fields.Boolean(
        string='Envoyé au fournisseur', default=False, tracking=True,
    )
    dropship_sent_date = fields.Datetime(string='Date envoi fournisseur')

    def action_mark_sent_to_supplier(self):
        """Marquer le BC comme envoyé au fournisseur"""
        for po in self:
            po.dropship_sent_to_supplier = True
            po.dropship_sent_date = fields.Datetime.now()
            po.message_post(body=_("📧 BC marqué comme envoyé au fournisseur."))
            
            # Mettre à jour le statut de la commande client
            if po.dropship_sale_id:
                po.dropship_sale_id.dropship_status = 'po_sent'
                po.dropship_sale_id.message_post(
                    body=_(
                        "📧 BC %(po_name)s envoyé au fournisseur %(supplier)s.",
                        po_name=po.name, supplier=po.partner_id.name,
                    )
                )

    def action_view_dropship_sale(self):
        """Ouvrir la commande client liée"""
        self.ensure_one()
        if self.dropship_sale_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.dropship_sale_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def button_confirm(self):
        """Override pour tracker la confirmation des BC dropship"""
        res = super().button_confirm()
        for po in self:
            if po.is_dropship_order and po.dropship_sale_id:
                po.dropship_sale_id.message_post(
                    body=_(
                        "✅ BC %(po_name)s confirmé (fournisseur: %(supplier)s, montant: %(amount)s€).",
                        po_name=po.name,
                        supplier=po.partner_id.name,
                        amount=po.amount_untaxed,
                    )
                )
        return res
