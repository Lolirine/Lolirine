# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # === DROPSHIPPING ===
    is_dropship_order = fields.Boolean(
        string='Commande dropshipping',
        compute='_compute_is_dropship', store=True,
    )
    dropship_status = fields.Selection([
        ('pending', 'En attente'),
        ('to_process', 'À traiter'),
        ('po_created', 'BC fournisseur créé'),
        ('po_sent', 'BC envoyé'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('issue', 'Problème'),
    ], string='Statut dropship', default='pending', tracking=True)

    # Relations
    dropship_purchase_ids = fields.One2many(
        'purchase.order', 'dropship_sale_id', string='BC Fournisseur',
    )
    dropship_purchase_count = fields.Integer(compute='_compute_dropship_purchase_count')

    # Marges
    dropship_estimated_margin = fields.Monetary(
        string='Marge estimée', compute='_compute_dropship_margins',
        currency_field='currency_id',
    )
    dropship_margin_percent = fields.Float(
        string='Marge (%)', compute='_compute_dropship_margins',
    )
    dropship_total_supplier_cost = fields.Monetary(
        string='Coût fournisseur', compute='_compute_dropship_margins',
        currency_field='currency_id',
    )
    
    # Flag pour identifier les commandes payées en ligne
    dropship_needs_processing = fields.Boolean(
        string='À traiter', compute='_compute_needs_processing', store=True,
    )

    @api.depends('order_line.product_id.is_dropship_product')
    def _compute_is_dropship(self):
        for order in self:
            order.is_dropship_order = any(
                line.product_id.product_tmpl_id.is_dropship_product
                for line in order.order_line if line.product_id
            )

    @api.depends('state', 'is_dropship_order', 'dropship_status', 'dropship_purchase_ids')
    def _compute_needs_processing(self):
        for order in self:
            order.dropship_needs_processing = (
                order.is_dropship_order
                and order.state == 'sale'
                and order.dropship_status in ('pending', 'to_process')
                and not order.dropship_purchase_ids
            )

    def _compute_dropship_purchase_count(self):
        for order in self:
            order.dropship_purchase_count = len(order.dropship_purchase_ids)

    @api.depends('order_line.price_subtotal', 'amount_untaxed')
    def _compute_dropship_margins(self):
        for order in self:
            if not order.is_dropship_order:
                order.dropship_total_supplier_cost = 0
                order.dropship_estimated_margin = 0
                order.dropship_margin_percent = 0
                continue

            total_cost = 0
            for line in order.order_line:
                if not line.product_id or line.display_type:
                    continue
                product = line.product_id.product_tmpl_id
                # Chercher la meilleure info dropship
                info = self.env['supplier.dropship.info'].search([
                    ('product_tmpl_id', '=', product.id),
                    ('is_active', '=', True),
                ], order='is_priority desc, negotiated_price asc', limit=1)
                if info:
                    total_cost += info.negotiated_price * line.product_uom_qty
                else:
                    # Sans info, on considère marge = 0
                    total_cost += line.price_unit * line.product_uom_qty

            order.dropship_total_supplier_cost = total_cost
            if order.amount_untaxed > 0:
                margin = order.amount_untaxed - total_cost
                order.dropship_estimated_margin = margin
                order.dropship_margin_percent = (margin / order.amount_untaxed) * 100
            else:
                order.dropship_estimated_margin = 0
                order.dropship_margin_percent = 0

    def action_confirm(self):
        """Override pour mettre le statut dropship à 'to_process' après confirmation"""
        res = super().action_confirm()
        for order in self:
            if order.is_dropship_order and order.dropship_status == 'pending':
                order.dropship_status = 'to_process'
                order.message_post(
                    body=_(
                        "🛒 Commande confirmée. Dropshipping : veuillez créer le bon "
                        "de commande fournisseur via le bouton 'Créer BC Dropship'."
                    )
                )
        return res

    def action_open_create_dropship_po_wizard(self):
        """Ouvrir le wizard de création de BC fournisseur"""
        self.ensure_one()
        if not self.is_dropship_order:
            raise UserError(_("Cette commande ne contient pas de produits dropshipping."))

        return {
            'name': _('Créer BC Fournisseur Dropship'),
            'type': 'ir.actions.act_window',
            'res_model': 'create.dropship.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'sale.order',
                'default_sale_order_id': self.id,
            },
        }

    def action_view_dropship_purchases(self):
        """Voir les BC fournisseur liés"""
        self.ensure_one()
        if len(self.dropship_purchase_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id': self.dropship_purchase_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('BC Fournisseur'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.dropship_purchase_ids.ids)],
            'target': 'current',
        }

    def action_mark_shipped(self):
        """Marquer comme expédiée"""
        for order in self:
            order.dropship_status = 'shipped'
            order.message_post(body=_("📦 Commande marquée comme expédiée par le fournisseur."))

    def action_mark_delivered(self):
        """Marquer comme livrée"""
        for order in self:
            order.dropship_status = 'delivered'
            order.message_post(body=_("✅ Commande livrée au client."))

    def action_mark_issue(self):
        """Signaler un problème"""
        for order in self:
            order.dropship_status = 'issue'
            order.message_post(body=_("⚠️ Problème signalé sur cette commande dropshipping."))
