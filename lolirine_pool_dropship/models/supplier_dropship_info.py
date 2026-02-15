# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SupplierDropshipInfo(models.Model):
    _name = 'supplier.dropship.info'
    _description = 'Information fournisseur dropshipping'
    _order = 'is_priority desc, sequence, id'
    _rec_name = 'display_name'

    # === RELATIONS ===
    product_tmpl_id = fields.Many2one(
        'product.template', string='Produit', required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one('product.product', string='Variante produit')
    supplier_id = fields.Many2one(
        'res.partner', string='Fournisseur', required=True,
        domain=[('is_dropship_supplier', '=', True)], index=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company,
    )
    sequence = fields.Integer(string='Priorité', default=10)

    # === RÉFÉRENCES ===
    supplier_product_ref = fields.Char(string='Référence fournisseur')
    supplier_product_name = fields.Char(string='Nom chez fournisseur')
    barcode = fields.Char(string='Code-barres fournisseur')

    # === TARIFICATION ===
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id,
    )
    price = fields.Monetary(
        string='Prix catalogue fournisseur HT', required=True,
        currency_field='currency_id',
        help="Prix catalogue du fournisseur (= prix de vente client HTVA)",
    )
    discount_percent = fields.Float(
        string='Réduction négociée (%)', default=0.0,
        help="Pourcentage de réduction obtenu auprès du fournisseur (ex: 35%, 40%, 52.5%)",
    )
    negotiated_price = fields.Monetary(
        string="Prix d'achat négocié HT",
        compute='_compute_negotiated_price', store=True,
        currency_field='currency_id',
        help="Prix réel d'achat après réduction = Prix catalogue × (1 - réduction%)",
    )
    min_qty = fields.Float(string='Quantité minimum', default=1.0)

    # === FRAIS ADDITIONNELS ===
    shipping_cost = fields.Monetary(
        string='Frais de port', currency_field='currency_id',
        help="Frais de livraison standard",
    )
    handling_fee = fields.Monetary(
        string='Frais de manutention', currency_field='currency_id',
    )
    dropship_fee = fields.Monetary(
        string='Frais dropshipping', currency_field='currency_id',
    )
    urgent_surcharge = fields.Monetary(
        string='Surcoût urgence', currency_field='currency_id',
    )
    total_cost = fields.Monetary(
        string='Coût total', compute='_compute_total_cost',
        store=True, currency_field='currency_id',
    )

    # === DÉLAIS ===
    delay = fields.Integer(string='Délai (jours)', default=5)
    delay_min = fields.Integer(string='Délai min (jours)')
    delay_max = fields.Integer(string='Délai max (jours)')

    # === STATUT ===
    is_dropship_capable = fields.Boolean(string='Dropshipping', default=True)
    is_priority = fields.Boolean(string='Fournisseur prioritaire', default=False)
    is_active = fields.Boolean(string='Actif', default=True)

    # === STOCK FOURNISSEUR ===
    supplier_stock = fields.Integer(string='Stock fournisseur')
    stock_updated = fields.Datetime(string='Mise à jour stock')

    # === FIABILITÉ ===
    reliability_score = fields.Float(string='Score fiabilité (%)', default=100.0)
    total_orders = fields.Integer(string='Commandes totales')
    on_time_deliveries = fields.Integer(string='Livraisons à temps')
    avg_delay_variance = fields.Float(string='Écart délai moyen (jours)')

    # === ZONES DE LIVRAISON ===
    country_ids = fields.Many2many(
        'res.country', 'dropship_info_country_rel',
        'info_id', 'country_id', string='Pays desservis',
    )
    excluded_country_ids = fields.Many2many(
        'res.country', 'dropship_info_excluded_country_rel',
        'info_id', 'country_id', string='Pays exclus',
    )

    # === COMMANDE ===
    order_method = fields.Selection([
        ('email', 'Email'),
        ('api', 'API'),
        ('portal', 'Portail fournisseur'),
        ('phone', 'Téléphone'),
        ('manual', 'Manuel'),
    ], string='Méthode de commande', default='email')
    order_email = fields.Char(string='Email commandes')
    api_endpoint = fields.Char(string='URL API')
    portal_url = fields.Char(string='URL Portail')

    # === NOTES ===
    notes = fields.Text(string='Notes internes')
    packaging_instructions = fields.Text(string='Instructions emballage')

    # === MARGE ===
    margin_estimate = fields.Float(
        string='Marge estimée (%)',
        compute='_compute_margin_estimate', store=True,
    )

    @api.depends('price', 'discount_percent')
    def _compute_negotiated_price(self):
        for record in self:
            if record.discount_percent:
                record.negotiated_price = record.price * (1 - record.discount_percent / 100)
            else:
                record.negotiated_price = record.price

    @api.depends('negotiated_price', 'shipping_cost', 'handling_fee', 'dropship_fee')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = (
                record.negotiated_price
                + record.shipping_cost
                + record.handling_fee
                + record.dropship_fee
            )

    @api.depends('price', 'negotiated_price')
    def _compute_margin_estimate(self):
        for record in self:
            if record.price > 0 and record.negotiated_price:
                record.margin_estimate = (
                    (record.price - record.negotiated_price) / record.price * 100
                )
            else:
                record.margin_estimate = 0

    def calculate_total_cost(self, quantity=1, urgent=False, destination_country_id=None):
        """Calcule le coût total pour une quantité donnée (avec prix négocié)"""
        self.ensure_one()

        base_cost = self.negotiated_price * quantity
        shipping = self.shipping_cost
        handling = self.handling_fee
        dropship = self.dropship_fee
        urgent_fee = self.urgent_surcharge if urgent else 0

        total = base_cost + shipping + handling + dropship + urgent_fee

        return {
            'base_cost': base_cost,
            'unit_price': self.negotiated_price,
            'catalog_price': self.price,
            'discount_percent': self.discount_percent,
            'shipping_cost': shipping,
            'handling_fee': handling,
            'dropship_fee': dropship,
            'urgent_fee': urgent_fee,
            'total_cost': total,
            'unit_cost': total / quantity if quantity else 0,
        }
