# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SupplierDropshipInfo(models.Model):
    """Extension des informations fournisseur avec données dropshipping"""
    _name = 'supplier.dropship.info'
    _description = 'Informations Dropshipping Fournisseur'
    _order = 'sequence, id'

    # === RELATIONS ===
    product_tmpl_id = fields.Many2one('product.template', string='Produit', 
                                       required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Variante produit')
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', required=True,
                                  domain=[('supplier_rank', '>', 0)])
    company_id = fields.Many2one('res.company', string='Société',
                                  default=lambda self: self.env.company)
    
    # === IDENTIFICATION ===
    sequence = fields.Integer(string='Priorité', default=10,
                              help="Plus bas = plus prioritaire")
    supplier_product_ref = fields.Char(string='Référence fournisseur')
    supplier_product_name = fields.Char(string='Nom chez fournisseur')
    barcode = fields.Char(string='Code-barres fournisseur')
    
    # === TARIFICATION ===
    currency_id = fields.Many2one('res.currency', string='Devise',
                                   default=lambda self: self.env.company.currency_id)
    price = fields.Monetary(string='Prix d\'achat HT', required=True, currency_field='currency_id')
    min_qty = fields.Float(string='Quantité minimum', default=1.0)
    
    # Frais additionnels
    shipping_cost = fields.Monetary(string='Frais de port', currency_field='currency_id',
                                    help="Frais de livraison standard")
    handling_fee = fields.Monetary(string='Frais de manutention', currency_field='currency_id')
    dropship_fee = fields.Monetary(string='Frais dropshipping', currency_field='currency_id',
                                   help="Surcoût pour livraison directe client")
    urgent_surcharge = fields.Monetary(string='Surcoût urgence', currency_field='currency_id')
    
    # Prix calculé total
    total_cost = fields.Monetary(string='Coût total', compute='_compute_total_cost',
                                  store=True, currency_field='currency_id')
    
    # === DÉLAIS ===
    delay = fields.Integer(string='Délai (jours)', default=3,
                           help="Délai de livraison en jours ouvrés")
    delay_min = fields.Integer(string='Délai min (jours)')
    delay_max = fields.Integer(string='Délai max (jours)')
    
    # === CAPACITÉS ===
    is_dropship_capable = fields.Boolean(string='Dropshipping', default=True,
                                          help="Le fournisseur peut livrer directement au client")
    is_priority = fields.Boolean(string='Fournisseur prioritaire', default=False)
    is_active = fields.Boolean(string='Actif', default=True)
    
    # Stock fournisseur (si connu)
    supplier_stock = fields.Float(string='Stock fournisseur')
    stock_updated = fields.Datetime(string='Mise à jour stock')
    
    # === PERFORMANCE ===
    reliability_score = fields.Float(string='Score fiabilité (%)', default=100.0,
                                      help="Score basé sur l'historique (0-100)")
    total_orders = fields.Integer(string='Commandes totales', compute='_compute_stats', store=True)
    on_time_deliveries = fields.Integer(string='Livraisons à temps', compute='_compute_stats', store=True)
    avg_delay_variance = fields.Float(string='Écart délai moyen (jours)', compute='_compute_stats', store=True)
    
    # === ZONES & RESTRICTIONS ===
    country_ids = fields.Many2many('res.country', string='Pays desservis',
                                    help="Laisser vide pour tous les pays")
    excluded_country_ids = fields.Many2many('res.country', 'supplier_dropship_excluded_country_rel',
                                            string='Pays exclus')
    
    # === COMMUNICATION ===
    order_method = fields.Selection([
        ('email', 'Email'),
        ('api', 'API / EDI'),
        ('portal', 'Portail fournisseur'),
        ('manual', 'Manuel'),
    ], string='Méthode de commande', default='email')
    
    order_email = fields.Char(string='Email commandes')
    api_endpoint = fields.Char(string='URL API')
    portal_url = fields.Char(string='URL Portail')
    
    # === NOTES ===
    notes = fields.Text(string='Notes internes')
    packaging_instructions = fields.Text(string='Instructions emballage')
    
    # === CHAMPS CALCULÉS ===
    margin_estimate = fields.Float(string='Marge estimée (%)', compute='_compute_margin_estimate', store=True)

    @api.depends('supplier_id', 'product_tmpl_id', 'supplier_product_ref')
    def _compute_display_name(self):
        for record in self:
            parts = [record.supplier_id.name or '']
            if record.supplier_product_ref:
                parts.append(f"[{record.supplier_product_ref}]")
            record.display_name = ' '.join(parts) or 'Nouveau'

    @api.depends('price', 'shipping_cost', 'handling_fee', 'dropship_fee')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = (
                record.price + 
                record.shipping_cost + 
                record.handling_fee + 
                record.dropship_fee
            )

    @api.depends('total_cost', 'product_tmpl_id.list_price')
    def _compute_margin_estimate(self):
        for record in self:
            if record.product_tmpl_id.list_price and record.total_cost:
                sale_price = record.product_tmpl_id.list_price
                margin = ((sale_price - record.total_cost) / sale_price) * 100
                record.margin_estimate = round(margin, 2)
            else:
                record.margin_estimate = 0.0

    def _compute_stats(self):
        """Calcule les statistiques de performance du fournisseur"""
        for record in self:
            # Rechercher les commandes fournisseur liées
            purchases = self.env['purchase.order.line'].search([
                ('partner_id', '=', record.supplier_id.id),
                ('product_id.product_tmpl_id', '=', record.product_tmpl_id.id),
                ('order_id.state', 'in', ['purchase', 'done'])
            ])
            
            record.total_orders = len(purchases)
            
            # Calculer les livraisons à temps
            on_time = 0
            delay_variances = []
            for po_line in purchases:
                if po_line.order_id.effective_date and po_line.order_id.date_planned:
                    planned = po_line.order_id.date_planned.date()
                    effective = po_line.order_id.effective_date.date()
                    variance = (effective - planned).days
                    delay_variances.append(variance)
                    if variance <= 0:
                        on_time += 1
            
            record.on_time_deliveries = on_time
            record.avg_delay_variance = sum(delay_variances) / len(delay_variances) if delay_variances else 0.0

    def update_reliability_score(self):
        """Met à jour le score de fiabilité basé sur l'historique"""
        for record in self:
            if record.total_orders > 0:
                # Base: % de livraisons à temps
                on_time_rate = (record.on_time_deliveries / record.total_orders) * 100
                
                # Ajustement selon l'écart de délai moyen
                if record.avg_delay_variance <= 0:
                    delay_bonus = 5
                elif record.avg_delay_variance <= 2:
                    delay_bonus = 0
                else:
                    delay_bonus = -min(record.avg_delay_variance * 2, 20)
                
                record.reliability_score = min(100, max(0, on_time_rate + delay_bonus))

    def can_deliver_to(self, country_id):
        """Vérifie si le fournisseur peut livrer dans un pays donné"""
        self.ensure_one()
        
        # Vérifier les exclusions
        if country_id in self.excluded_country_ids.ids:
            return False
        
        # Si des pays spécifiques sont définis, vérifier l'inclusion
        if self.country_ids:
            return country_id in self.country_ids.ids
        
        # Sinon, tous les pays sont acceptés
        return True

    def calculate_total_cost(self, quantity=1, urgent=False, destination_country_id=None):
        """Calcule le coût total pour une quantité donnée"""
        self.ensure_one()
        
        base_cost = self.price * quantity
        shipping = self.shipping_cost
        handling = self.handling_fee
        dropship = self.dropship_fee
        
        # Surcoût urgence
        urgent_fee = self.urgent_surcharge if urgent else 0
        
        total = base_cost + shipping + handling + dropship + urgent_fee
        
        return {
            'base_cost': base_cost,
            'shipping_cost': shipping,
            'handling_fee': handling,
            'dropship_fee': dropship,
            'urgent_fee': urgent_fee,
            'total_cost': total,
            'unit_cost': total / quantity if quantity else 0,
        }
