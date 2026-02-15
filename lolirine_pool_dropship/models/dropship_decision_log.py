# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DropshipDecisionLog(models.Model):
    _name = 'dropship.decision.log'
    _description = 'Journal des décisions dropshipping'
    _order = 'create_date desc'

    sale_order_id = fields.Many2one('sale.order', string='Commande', required=True, ondelete='cascade')
    sale_line_id = fields.Many2one('sale.order.line', string='Ligne de commande')
    product_id = fields.Many2one('product.product', string='Produit')
    selected_supplier_id = fields.Many2one('res.partner', string='Fournisseur sélectionné')
    purchase_order_id = fields.Many2one('purchase.order', string='BC Fournisseur')
    decision_type = fields.Selection([
        ('auto', 'Automatique'),
        ('manual', 'Manuelle'),
    ], string='Type de décision', default='manual')
    reason = fields.Text(string='Raison')
    catalog_price = fields.Float(string='Prix catalogue')
    negotiated_price = fields.Float(string='Prix négocié')
    margin_percent = fields.Float(string='Marge %')
    user_id = fields.Many2one(
        'res.users', string='Décideur',
        default=lambda self: self.env.user,
    )

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_supplier(self):
        self.ensure_one()
        if self.selected_supplier_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': self.selected_supplier_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
