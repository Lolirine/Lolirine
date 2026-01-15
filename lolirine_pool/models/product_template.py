# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    """Extension des produits pour les fonctionnalités piscine"""
    _inherit = 'product.template'

    is_pool_product = fields.Boolean(
        string='Produit piscine',
        default=False,
        help="Cochez si ce produit fait partie du catalogue piscine"
    )
    
    # Marque
    pool_brand_id = fields.Many2one(
        'pool.brand',
        string='Marque',
        tracking=True
    )
    
    # Catégorie piscine
    pool_category_id = fields.Many2one(
        'pool.product.category',
        string='Catégorie piscine'
    )
    
    # Caractéristiques techniques
    pool_volume = fields.Float(
        string='Volume bassin max (m³)',
        help="Volume maximum du bassin pour lequel ce produit est adapté"
    )
    pool_flow_rate = fields.Float(
        string='Débit (m³/h)',
        help="Débit de filtration ou de circulation"
    )
    pool_power = fields.Float(
        string='Puissance (W)',
        help="Puissance électrique"
    )
    pool_warranty = fields.Integer(
        string='Garantie (mois)',
        help="Durée de garantie en mois"
    )
    
    # Compatibilité
    pool_compatibility = fields.Text(
        string='Compatibilité',
        help="Indications de compatibilité avec d'autres produits ou types de piscine"
    )
    
    # Fournisseur piscine principal
    main_pool_supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur piscine principal',
        compute='_compute_main_pool_supplier',
        store=True
    )
    
    # Stock fournisseur
    supplier_stock_available = fields.Boolean(
        string='Dispo fournisseur',
        compute='_compute_supplier_stock'
    )
    supplier_lead_time = fields.Integer(
        string='Délai fournisseur (jours)',
        compute='_compute_supplier_stock'
    )
    
    @api.depends('seller_ids', 'seller_ids.partner_id')
    def _compute_main_pool_supplier(self):
        for product in self:
            supplier = False
            for seller in product.seller_ids:
                pool_supplier = self.env['pool.supplier'].search([
                    ('partner_id', '=', seller.partner_id.id)
                ], limit=1)
                if pool_supplier:
                    supplier = pool_supplier
                    break
            product.main_pool_supplier_id = supplier
    
    @api.depends('seller_ids')
    def _compute_supplier_stock(self):
        for product in self:
            # Valeurs par défaut
            product.supplier_stock_available = False
            product.supplier_lead_time = 0
            
            # Chercher le premier fournisseur avec info
            for seller in product.seller_ids:
                if hasattr(seller, 'supplier_stock') and seller.supplier_stock > 0:
                    product.supplier_stock_available = True
                if seller.delay:
                    product.supplier_lead_time = seller.delay
                    break
    
    @api.onchange('pool_category_id')
    def _onchange_pool_category(self):
        """Synchroniser avec la catégorie produit Odoo"""
        if self.pool_category_id and self.pool_category_id.product_category_id:
            self.categ_id = self.pool_category_id.product_category_id


class ProductProduct(models.Model):
    """Extension des variantes de produits"""
    _inherit = 'product.product'
    
    # Champs spécifiques aux variantes si nécessaire
    pool_variant_code = fields.Char(string='Code variante piscine')


class ProductSupplierinfo(models.Model):
    """Extension des infos fournisseur"""
    _inherit = 'product.supplierinfo'
    
    pool_supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur piscine',
        compute='_compute_pool_supplier',
        store=True
    )
    
    # Stock fournisseur
    supplier_stock = fields.Float(string='Stock fournisseur')
    supplier_stock_date = fields.Date(string='Date MAJ stock')
    
    # Délai et dropship
    is_dropship = fields.Boolean(string='Dropship', default=False)
    
    @api.depends('partner_id')
    def _compute_pool_supplier(self):
        for info in self:
            if info.partner_id:
                supplier = self.env['pool.supplier'].search([
                    ('partner_id', '=', info.partner_id.id)
                ], limit=1)
                info.pool_supplier_id = supplier
            else:
                info.pool_supplier_id = False
