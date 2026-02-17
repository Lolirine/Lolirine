# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # === DROPSHIPPING ===
    is_dropship_product = fields.Boolean(string='Produit dropshipping', default=False,
                                          help="Ce produit est géré en dropshipping")
    dropship_supplier_ids = fields.One2many('supplier.dropship.info', 'product_tmpl_id',
                                             string='Fournisseurs dropshipping')
    dropship_supplier_count = fields.Integer(compute='_compute_dropship_supplier_count',
                                              string='Nb fournisseurs', store=True)
    
    # Fournisseur préféré
    preferred_dropship_supplier_id = fields.Many2one('supplier.dropship.info',
                                                      string='Fournisseur préféré',
                                                      domain="[('product_tmpl_id', '=', id)]")
    
    # Statistiques
    best_margin_supplier_id = fields.Many2one('supplier.dropship.info', 
                                               compute='_compute_best_suppliers',
                                               string='Meilleure marge')
    fastest_supplier_id = fields.Many2one('supplier.dropship.info',
                                           compute='_compute_best_suppliers',
                                           string='Plus rapide')
    best_overall_supplier_id = fields.Many2one('supplier.dropship.info',
                                                compute='_compute_best_suppliers',
                                                string='Meilleur global')
    
    # Marge
    avg_margin = fields.Float(string='Marge moyenne (%)', compute='_compute_margins')
    best_margin = fields.Float(string='Meilleure marge (%)', compute='_compute_margins')
    worst_margin = fields.Float(string='Pire marge (%)', compute='_compute_margins')

    @api.depends('dropship_supplier_ids', 'dropship_supplier_ids.is_active')
    def _compute_dropship_supplier_count(self):
        for product in self:
            product.dropship_supplier_count = len(product.dropship_supplier_ids.filtered('is_active'))

    @api.depends('dropship_supplier_ids.margin_estimate', 'dropship_supplier_ids.delay',
                 'dropship_supplier_ids.reliability_score', 'dropship_supplier_ids.is_active')
    def _compute_best_suppliers(self):
        for product in self:
            active_suppliers = product.dropship_supplier_ids.filtered('is_active')
            
            if not active_suppliers:
                product.best_margin_supplier_id = False
                product.fastest_supplier_id = False
                product.best_overall_supplier_id = False
                continue
            
            # Meilleure marge
            best_margin = max(active_suppliers, key=lambda s: s.margin_estimate, default=False)
            product.best_margin_supplier_id = best_margin.id if best_margin else False
            
            # Plus rapide
            fastest = min(active_suppliers, key=lambda s: s.delay, default=False)
            product.fastest_supplier_id = fastest.id if fastest else False
            
            # Meilleur global (score pondéré)
            def calculate_score(supplier):
                margin_score = supplier.margin_estimate * 0.4
                delay_score = (30 - min(supplier.delay, 30)) / 30 * 100 * 0.25  # Inverse du délai
                reliability_score = supplier.reliability_score * 0.2
                priority_score = 15 if supplier.is_priority else 0
                return margin_score + delay_score + reliability_score + priority_score
            
            best_overall = max(active_suppliers, key=calculate_score, default=False)
            product.best_overall_supplier_id = best_overall.id if best_overall else False

    @api.depends('dropship_supplier_ids.margin_estimate', 'dropship_supplier_ids.is_active')
    def _compute_margins(self):
        for product in self:
            active_suppliers = product.dropship_supplier_ids.filtered('is_active')
            margins = [s.margin_estimate for s in active_suppliers if s.margin_estimate]
            
            if margins:
                product.avg_margin = sum(margins) / len(margins)
                product.best_margin = max(margins)
                product.worst_margin = min(margins)
            else:
                product.avg_margin = 0.0
                product.best_margin = 0.0
                product.worst_margin = 0.0

    def get_best_supplier(self, quantity=1, destination_country_id=None, urgent=False):
        """
        Sélectionne le meilleur fournisseur selon la configuration
        
        Returns: dict avec supplier_info, costs, margin, score, reasons
        """
        self.ensure_one()
        
        config = self.env['dropship.config'].get_config()
        active_suppliers = self.dropship_supplier_ids.filtered(
            lambda s: s.is_active and s.is_dropship_capable
        )
        
        if not active_suppliers:
            return {
                'success': False,
                'error': 'Aucun fournisseur dropshipping actif pour ce produit',
                'supplier_info': False,
            }
        
        # Filtrer par pays si spécifié
        if destination_country_id:
            active_suppliers = active_suppliers.filtered(
                lambda s: s.can_deliver_to(destination_country_id)
            )
            if not active_suppliers:
                return {
                    'success': False,
                    'error': 'Aucun fournisseur ne livre dans ce pays',
                    'supplier_info': False,
                }
        
        # Calculer le score pour chaque fournisseur
        candidates = []
        sale_price = self.list_price * quantity
        
        for supplier in active_suppliers:
            costs = supplier.calculate_total_cost(quantity, urgent, destination_country_id)
            
            # Calculer la marge
            if sale_price > 0:
                margin = ((sale_price - costs['total_cost']) / sale_price) * 100
            else:
                margin = 0
            
            # Vérifier la marge minimum
            if margin < config.min_margin_percent:
                continue
            
            # Calculer le score pondéré
            # Normaliser les valeurs sur 100
            margin_normalized = min(margin, 50) * 2  # Cap à 50% = 100 points
            delay_normalized = max(0, 100 - supplier.delay * 5)  # 0 jours = 100, 20 jours = 0
            reliability_normalized = supplier.reliability_score
            shipping_normalized = max(0, 100 - costs['shipping_cost'] * 2)  # Inverse des frais
            
            score = (
                margin_normalized * (config.weight_margin / 100) +
                delay_normalized * (config.weight_delay / 100) +
                reliability_normalized * (config.weight_reliability / 100) +
                shipping_normalized * (config.weight_shipping / 100)
            )
            
            # Bonus
            if supplier.delay < 3:
                score += config.bonus_fast_delivery
            if supplier.is_priority:
                score += config.bonus_priority_supplier
            
            # Malus
            if supplier.reliability_score < 70:
                score -= config.malus_low_reliability
            
            candidates.append({
                'supplier_info': supplier,
                'costs': costs,
                'margin': margin,
                'score': score,
                'reasons': self._build_selection_reasons(supplier, margin, score, config),
            })
        
        if not candidates:
            return {
                'success': False,
                'error': f'Aucun fournisseur avec marge >= {config.min_margin_percent}%',
                'supplier_info': False,
            }
        
        # Trier par score décroissant
        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]
        
        return {
            'success': True,
            'supplier_info': best['supplier_info'],
            'costs': best['costs'],
            'margin': best['margin'],
            'score': best['score'],
            'reasons': best['reasons'],
            'alternatives': candidates[1:5],  # 4 alternatives max
        }

    def _build_selection_reasons(self, supplier, margin, score, config):
        """Construit les raisons de la sélection"""
        reasons = []
        
        if config.selection_priority == 'margin':
            reasons.append(f"Marge: {margin:.1f}%")
        
        reasons.append(f"Délai: {supplier.delay} jours")
        reasons.append(f"Fiabilité: {supplier.reliability_score:.0f}%")
        
        if supplier.is_priority:
            reasons.append("Fournisseur prioritaire")
        
        reasons.append(f"Score global: {score:.1f}")
        
        return reasons

    def action_view_dropship_suppliers(self):
        """Action pour voir/gérer les fournisseurs dropshipping"""
        self.ensure_one()
        return {
            'name': f'Fournisseurs - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.dropship.info',
            'view_mode': 'list,form',
            'domain': [('product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_tmpl_id': self.id,
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_best_supplier(self, quantity=1, destination_country_id=None, urgent=False):
        """Délègue au template"""
        return self.product_tmpl_id.get_best_supplier(quantity, destination_country_id, urgent)
