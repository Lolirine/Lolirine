# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_dropship_supplier = fields.Boolean(string='Fournisseur dropship', default=False)
    dropship_info_ids = fields.One2many(
        'supplier.dropship.info', 'supplier_id', string='Produits dropship',
    )
    dropship_product_count = fields.Integer(
        string='Produits dropship', compute='_compute_dropship_stats',
    )
    dropship_order_count = fields.Integer(
        string='Commandes dropship', compute='_compute_dropship_stats',
    )
    dropship_default_discount = fields.Float(
        string='Réduction par défaut (%)',
        help="Réduction par défaut pour les nouveaux produits de ce fournisseur",
    )
    dropship_default_delay = fields.Integer(
        string='Délai par défaut (jours)', default=5,
    )
    dropship_order_email = fields.Char(
        string='Email commandes dropship',
        help="Email spécifique pour les commandes dropship (si différent de l'email principal)",
    )
    dropship_notes = fields.Text(string='Notes dropship')

    def _compute_dropship_stats(self):
        for partner in self:
            partner.dropship_product_count = len(partner.dropship_info_ids.filtered('is_active'))
            partner.dropship_order_count = self.env['purchase.order'].search_count([
                ('partner_id', '=', partner.id),
                ('is_dropship_order', '=', True),
            ])

    def action_view_dropship_products(self):
        """Voir les produits dropship de ce fournisseur"""
        self.ensure_one()
        return {
            'name': f'Produits dropship - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.dropship.info',
            'view_mode': 'list,form',
            'domain': [('supplier_id', '=', self.id)],
            'context': {'default_supplier_id': self.id},
        }

    def action_view_dropship_orders(self):
        """Voir les commandes dropshipping de ce fournisseur"""
        self.ensure_one()
        return {
            'name': f'Commandes dropship - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('is_dropship_order', '=', True),
            ],
        }
