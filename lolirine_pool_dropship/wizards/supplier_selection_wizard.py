# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SupplierSelectionWizard(models.TransientModel):
    """Wizard pour la sélection manuelle du fournisseur"""
    _name = 'supplier.selection.wizard'
    _description = 'Sélection manuelle fournisseur'

    sale_order_id = fields.Many2one('sale.order', string='Commande client', required=True)
    line_ids = fields.One2many('supplier.selection.wizard.line', 'wizard_id', 
                                string='Lignes à configurer')
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        if self._context.get('default_sale_order_id'):
            sale_order = self.env['sale.order'].browse(self._context['default_sale_order_id'])
            
            lines = []
            for line in sale_order.order_line:
                if line.product_id and line.product_id.product_tmpl_id.is_dropship_product:
                    # Récupérer les fournisseurs disponibles
                    suppliers = line.product_id.product_tmpl_id.dropship_supplier_ids.filtered('is_active')
                    
                    line_vals = {
                        'sale_line_id': line.id,
                        'product_id': line.product_id.id,
                        'quantity': line.product_uom_qty,
                        'sale_price': line.price_subtotal,
                        'current_supplier_id': line.dropship_supplier_id.id if line.dropship_supplier_id else False,
                        'available_supplier_ids': [(6, 0, suppliers.mapped('supplier_id').ids)],
                    }
                    
                    # Si un fournisseur est déjà sélectionné, utiliser ses données
                    if line.dropship_supplier_info_id:
                        info = line.dropship_supplier_info_id
                        line_vals.update({
                            'selected_supplier_info_id': info.id,
                            'selected_supplier_id': info.supplier_id.id,
                            'supplier_cost': line.dropship_supplier_cost,
                            'calculated_margin': line.dropship_margin,
                        })
                    
                    lines.append((0, 0, line_vals))
            
            res['line_ids'] = lines
        
        return res

    def action_confirm(self):
        """Confirme la sélection des fournisseurs"""
        self.ensure_one()
        
        for line in self.line_ids:
            if not line.selected_supplier_info_id:
                raise UserError(_(
                    "Veuillez sélectionner un fournisseur pour le produit: %s"
                ) % line.product_id.name)
            
            # Mettre à jour la ligne de commande
            supplier_info = line.selected_supplier_info_id
            costs = supplier_info.calculate_total_cost(line.quantity)
            
            # Calculer la marge
            if line.sale_price > 0:
                margin = ((line.sale_price - costs['total_cost']) / line.sale_price) * 100
            else:
                margin = 0
            
            line.sale_line_id.write({
                'dropship_supplier_info_id': supplier_info.id,
                'dropship_supplier_id': supplier_info.supplier_id.id,
                'dropship_supplier_cost': costs['total_cost'],
                'dropship_margin': margin,
                'dropship_alert': '',
            })
            
            # Logger la décision manuelle
            self.env['dropship.decision.log'].create({
                'sale_order_id': self.sale_order_id.id,
                'sale_line_id': line.sale_line_id.id,
                'product_id': line.product_id.id,
                'selected_supplier_id': supplier_info.supplier_id.id,
                'supplier_info_id': supplier_info.id,
                'decision_type': 'manual',
                'sale_price': line.sale_price,
                'supplier_cost': costs['total_cost'],
                'margin_amount': line.sale_price - costs['total_cost'],
                'margin_percent': margin,
                'quantity': line.quantity,
                'reasons': f"Sélection manuelle par {self.env.user.name}",
            })
        
        # Mettre à jour le statut
        self.sale_order_id.dropship_status = 'supplier_selected'
        
        return {'type': 'ir.actions.act_window_close'}


class SupplierSelectionWizardLine(models.TransientModel):
    """Ligne du wizard de sélection fournisseur"""
    _name = 'supplier.selection.wizard.line'
    _description = 'Ligne sélection fournisseur'

    wizard_id = fields.Many2one('supplier.selection.wizard', string='Wizard', ondelete='cascade')
    sale_line_id = fields.Many2one('sale.order.line', string='Ligne commande')
    product_id = fields.Many2one('product.product', string='Produit')
    quantity = fields.Float(string='Quantité')
    sale_price = fields.Monetary(string='Prix de vente', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Fournisseur actuel
    current_supplier_id = fields.Many2one('res.partner', string='Fournisseur actuel')
    
    # Sélection
    available_supplier_ids = fields.Many2many('res.partner', string='Fournisseurs disponibles')
    selected_supplier_id = fields.Many2one('res.partner', string='Fournisseur sélectionné',
                                            domain="[('id', 'in', available_supplier_ids)]")
    selected_supplier_info_id = fields.Many2one('supplier.dropship.info', string='Info fournisseur',
                                                 compute='_compute_supplier_info', store=True)
    
    # Données calculées
    supplier_cost = fields.Monetary(string='Coût fournisseur', compute='_compute_costs',
                                     currency_field='currency_id')
    calculated_margin = fields.Float(string='Marge (%)', compute='_compute_costs')
    supplier_delay = fields.Integer(string='Délai (jours)', compute='_compute_costs')

    @api.depends('selected_supplier_id', 'product_id')
    def _compute_supplier_info(self):
        for line in self:
            if line.selected_supplier_id and line.product_id:
                info = self.env['supplier.dropship.info'].search([
                    ('supplier_id', '=', line.selected_supplier_id.id),
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                    ('is_active', '=', True),
                ], limit=1)
                line.selected_supplier_info_id = info.id if info else False
            else:
                line.selected_supplier_info_id = False

    @api.depends('selected_supplier_info_id', 'quantity', 'sale_price')
    def _compute_costs(self):
        for line in self:
            if line.selected_supplier_info_id:
                info = line.selected_supplier_info_id
                costs = info.calculate_total_cost(line.quantity)
                line.supplier_cost = costs['total_cost']
                line.supplier_delay = info.delay
                
                if line.sale_price > 0:
                    line.calculated_margin = ((line.sale_price - costs['total_cost']) / line.sale_price) * 100
                else:
                    line.calculated_margin = 0
            else:
                line.supplier_cost = 0
                line.calculated_margin = 0
                line.supplier_delay = 0
