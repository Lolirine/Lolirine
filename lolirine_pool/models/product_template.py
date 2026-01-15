# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    """Extension product.template pour les produits piscine"""
    _inherit = 'product.template'

    # Identification piscine
    is_pool_product = fields.Boolean(
        string='Produit piscine',
        default=False,
        help="Cocher si ce produit fait partie du catalogue piscine"
    )
    
    pool_supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur piscine'
    )
    
    pool_category_id = fields.Many2one(
        'pool.product.category',
        string='Catégorie piscine'
    )
    
    pool_brand_id = fields.Many2one(
        'pool.brand',
        string='Marque'
    )
    pool_brand = fields.Char(
        string='Marque (texte)',
        help="Marque importée en texte libre"
    )
    
    # Références fournisseurs
    supplier_ref = fields.Char(
        string='Réf. fournisseur principale',
        help="Référence chez le fournisseur principal"
    )
    
    # Attributs techniques
    pool_attribute_value_ids = fields.One2many(
        'pool.product.attribute.value',
        'product_tmpl_id',
        string='Caractéristiques techniques'
    )
    
    # Spécifications techniques rapides (champs directs)
    pool_power = fields.Float(string='Puissance (W)')
    pool_flow_rate = fields.Float(string='Débit (m³/h)')
    pool_pressure = fields.Float(string='Pression max (bar)')
    pool_volume_min = fields.Float(string='Volume piscine min (m³)')
    pool_volume_max = fields.Float(string='Volume piscine max (m³)')
    pool_warranty_years = fields.Integer(string='Garantie (années)')
    
    # Compatibilité
    pool_compatibility = fields.Text(
        string='Compatibilité',
        help="Informations de compatibilité avec d'autres équipements"
    )
    
    # Documents
    pool_datasheet_url = fields.Char(string='Fiche technique (URL)')
    pool_manual_url = fields.Char(string='Manuel (URL)')
    
    # Dropshipping
    is_dropship = fields.Boolean(
        string='Dropshipping',
        default=False,
        help="Produit livré directement par le fournisseur"
    )
    dropship_delay = fields.Integer(
        string='Délai dropship (jours)',
        default=5
    )
    
    # Stock fournisseur
    supplier_stock_qty = fields.Float(
        string='Stock fournisseur',
        help="Quantité en stock chez le fournisseur (info)"
    )
    supplier_stock_date = fields.Date(
        string='MAJ stock fournisseur'
    )
    
    @api.onchange('pool_supplier_id')
    def _onchange_pool_supplier(self):
        """Pré-remplir certains champs selon le fournisseur"""
        if self.pool_supplier_id:
            self.is_pool_product = True
            if self.pool_supplier_id.default_category_id and not self.categ_id:
                self.categ_id = self.pool_supplier_id.default_category_id
    
    @api.onchange('pool_brand')
    def _onchange_pool_brand_text(self):
        """Essayer de lier à une marque existante"""
        if self.pool_brand and not self.pool_brand_id:
            brand = self.env['pool.brand'].search([
                ('name', '=ilike', self.pool_brand)
            ], limit=1)
            if brand:
                self.pool_brand_id = brand


class ProductProduct(models.Model):
    """Extension product.product"""
    _inherit = 'product.product'
    
    # Héritage des champs du template suffit généralement
    # Ajouter ici des champs spécifiques aux variantes si nécessaire


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
    
    # Délai
    is_dropship = fields.Boolean(string='Dropship')
    
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
