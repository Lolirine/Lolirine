# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DropshipDecisionLog(models.Model):
    """Journal des décisions de sélection fournisseur"""
    _name = 'dropship.decision.log'
    _description = 'Journal Décisions Dropshipping'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # === RELATIONS ===
    sale_order_id = fields.Many2one('sale.order', string='Commande client',
                                     ondelete='cascade', required=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Ligne commande',
                                    ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Produit', required=True)
    
    # === FOURNISSEUR SÉLECTIONNÉ ===
    selected_supplier_id = fields.Many2one('res.partner', string='Fournisseur sélectionné')
    supplier_info_id = fields.Many2one('supplier.dropship.info', string='Info fournisseur')
    
    # === DÉCISION ===
    decision_type = fields.Selection([
        ('auto', 'Automatique'),
        ('manual', 'Manuelle'),
        ('override', 'Modification manuelle'),
    ], string='Type de décision', required=True, default='auto')
    
    decision_date = fields.Datetime(string='Date décision', default=fields.Datetime.now)
    decision_user_id = fields.Many2one('res.users', string='Utilisateur',
                                        default=lambda self: self.env.user)
    
    # === DONNÉES FINANCIÈRES ===
    currency_id = fields.Many2one('res.currency', string='Devise',
                                   default=lambda self: self.env.company.currency_id)
    sale_price = fields.Monetary(string='Prix de vente', currency_field='currency_id')
    supplier_cost = fields.Monetary(string='Coût fournisseur', currency_field='currency_id')
    margin_amount = fields.Monetary(string='Marge (€)', currency_field='currency_id')
    margin_percent = fields.Float(string='Marge (%)')
    
    # === SCORING ===
    score = fields.Float(string='Score global')
    reasons = fields.Text(string='Raisons de la sélection')
    
    # === ALTERNATIVES ===
    alternatives_count = fields.Integer(string='Nb alternatives')
    alternative_suppliers = fields.Text(string='Fournisseurs alternatifs')
    
    # === CONTEXTE ===
    quantity = fields.Float(string='Quantité')
    destination_country_id = fields.Many2one('res.country', string='Pays destination')
    was_urgent = fields.Boolean(string='Commande urgente')
    
    # === RÈGLES APPLIQUÉES ===
    config_snapshot = fields.Text(string='Configuration utilisée')
    rules_applied = fields.Text(string='Règles appliquées')
    
    # === CHAMPS CALCULÉS ===
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('sale_order_id', 'product_id', 'decision_date')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.sale_order_id.name} - {record.product_id.name} ({record.decision_date.strftime('%d/%m/%Y %H:%M') if record.decision_date else ''})"

    @api.model_create_multi
    def create(self, vals_list):
        """Capture automatiquement le contexte lors de la création"""
        for vals in vals_list:
            # Capturer la configuration actuelle
            if not vals.get('config_snapshot'):
                config = self.env['dropship.config'].get_config()
                vals['config_snapshot'] = (
                    f"Critère principal: {config.selection_priority}\n"
                    f"Marge min: {config.min_margin_percent}%\n"
                    f"Pondérations: Marge {config.weight_margin}%, "
                    f"Délai {config.weight_delay}%, "
                    f"Fiabilité {config.weight_reliability}%, "
                    f"Frais {config.weight_shipping}%"
                )
            
            # Capturer le pays de destination
            if vals.get('sale_order_id') and not vals.get('destination_country_id'):
                sale_order = self.env['sale.order'].browse(vals['sale_order_id'])
                if sale_order.partner_shipping_id.country_id:
                    vals['destination_country_id'] = sale_order.partner_shipping_id.country_id.id
        
        return super().create(vals_list)

    def action_view_sale_order(self):
        """Voir la commande client"""
        self.ensure_one()
        return {
            'name': 'Commande client',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }

    def action_view_supplier(self):
        """Voir le fournisseur"""
        self.ensure_one()
        return {
            'name': 'Fournisseur',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.selected_supplier_id.id,
        }
