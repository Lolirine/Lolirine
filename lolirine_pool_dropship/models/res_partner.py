# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # === CAPACITÉS DROPSHIPPING ===
    is_dropship_supplier = fields.Boolean(string='Fournisseur dropshipping',
                                           help="Ce fournisseur peut livrer directement aux clients")
    dropship_certified = fields.Boolean(string='Certifié dropshipping',
                                         help="Fournisseur validé pour le dropshipping")
    
    # === CONDITIONS GÉNÉRALES ===
    dropship_min_order = fields.Monetary(string='Commande minimum dropship',
                                          currency_field='currency_id')
    dropship_free_shipping_threshold = fields.Monetary(string='Franco de port',
                                                        currency_field='currency_id')
    dropship_standard_delay = fields.Integer(string='Délai standard (jours)', default=5)
    
    # === SLA ===
    sla_delivery_target = fields.Integer(string='SLA Livraison (jours)', default=5,
                                          help="Délai maximum de livraison garanti")
    sla_response_time = fields.Integer(string='SLA Réponse (heures)', default=24)
    sla_return_processing = fields.Integer(string='SLA Retours (jours)', default=14)
    
    # === ZONES DESSERVIES ===
    dropship_country_ids = fields.Many2many('res.country', 'partner_dropship_country_rel',
                                             string='Pays desservis')
    dropship_excluded_zones = fields.Text(string='Zones exclues',
                                          help="Codes postaux ou régions non desservis")
    
    # === COMMUNICATION ===
    dropship_order_email = fields.Char(string='Email commandes dropship')
    dropship_api_enabled = fields.Boolean(string='API activée')
    dropship_api_key = fields.Char(string='Clé API')
    dropship_api_endpoint = fields.Char(string='URL API')
    dropship_portal_url = fields.Char(string='URL Portail')
    
    # === PRÉFÉRENCES ===
    dropship_packing_neutral = fields.Boolean(string='Emballage neutre', default=True)
    dropship_include_invoice = fields.Boolean(string='Inclure facture', default=False)
    dropship_special_instructions = fields.Text(string='Instructions spéciales')
    
    # === PERFORMANCE ===
    dropship_reliability_score = fields.Float(string='Score fiabilité global (%)',
                                               compute='_compute_dropship_stats')
    dropship_total_orders = fields.Integer(string='Total commandes dropship',
                                            compute='_compute_dropship_stats')
    dropship_avg_delay = fields.Float(string='Délai moyen (jours)',
                                       compute='_compute_dropship_stats')
    dropship_on_time_rate = fields.Float(string='Taux ponctualité (%)',
                                          compute='_compute_dropship_stats')
    
    # === STATISTIQUES PRODUITS ===
    dropship_product_count = fields.Integer(string='Produits dropship',
                                             compute='_compute_dropship_product_count')

    @api.depends('supplier_rank')
    def _compute_dropship_stats(self):
        """Calcule les statistiques dropshipping du fournisseur"""
        for partner in self:
            if partner.supplier_rank <= 0:
                partner.dropship_reliability_score = 0
                partner.dropship_total_orders = 0
                partner.dropship_avg_delay = 0
                partner.dropship_on_time_rate = 0
                continue
            
            # Récupérer les commandes dropshipping
            dropship_orders = self.env['purchase.order'].search([
                ('partner_id', '=', partner.id),
                ('is_dropship_order', '=', True),
                ('state', 'in', ['purchase', 'done'])
            ])
            
            partner.dropship_total_orders = len(dropship_orders)
            
            if not dropship_orders:
                partner.dropship_reliability_score = 100
                partner.dropship_avg_delay = 0
                partner.dropship_on_time_rate = 100
                continue
            
            # Calculer les délais et ponctualité
            delays = []
            on_time_count = 0
            
            for order in dropship_orders:
                if order.effective_date and order.date_planned:
                    actual_delay = (order.effective_date.date() - order.date_order.date()).days
                    delays.append(actual_delay)
                    
                    expected_delay = (order.date_planned.date() - order.date_order.date()).days
                    if actual_delay <= expected_delay:
                        on_time_count += 1
            
            if delays:
                partner.dropship_avg_delay = sum(delays) / len(delays)
                partner.dropship_on_time_rate = (on_time_count / len(delays)) * 100
            else:
                partner.dropship_avg_delay = 0
                partner.dropship_on_time_rate = 100
            
            # Score de fiabilité
            partner.dropship_reliability_score = min(100, partner.dropship_on_time_rate + 5)

    def _compute_dropship_product_count(self):
        for partner in self:
            count = self.env['supplier.dropship.info'].search_count([
                ('supplier_id', '=', partner.id),
                ('is_active', '=', True)
            ])
            partner.dropship_product_count = count

    def action_view_dropship_products(self):
        """Voir les produits dropshipping de ce fournisseur"""
        self.ensure_one()
        return {
            'name': f'Produits dropship - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.dropship.info',
            'view_mode': 'list,form',
            'domain': [('supplier_id', '=', self.id)],
            'context': {
                'default_supplier_id': self.id,
            },
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
                ('is_dropship_order', '=', True)
            ],
        }
