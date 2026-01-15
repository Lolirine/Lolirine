# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PoolProductCategory(models.Model):
    """Catégories spécifiques produits piscine"""
    _name = 'pool.product.category'
    _description = 'Catégorie produit piscine'
    _order = 'sequence, name'
    _parent_store = True

    name = fields.Char(string='Nom', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    parent_id = fields.Many2one(
        'pool.product.category',
        string='Catégorie parente',
        ondelete='cascade'
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        'pool.product.category',
        'parent_id',
        string='Sous-catégories'
    )
    
    # Lien avec la catégorie produit Odoo
    product_category_id = fields.Many2one(
        'product.category',
        string='Catégorie produit Odoo'
    )
    
    # Affichage
    icon = fields.Char(string='Icône Font Awesome', default='fa-cube')
    color = fields.Char(string='Couleur', default='#0077B6')
    image = fields.Binary(string='Image')
    description = fields.Text(string='Description', translate=True)
    
    # Compteurs
    product_count = fields.Integer(
        string='Nombre de produits',
        compute='_compute_product_count'
    )
    
    def _compute_product_count(self):
        for cat in self:
            if cat.product_category_id:
                cat.product_count = self.env['product.template'].search_count([
                    ('categ_id', 'child_of', cat.product_category_id.id),
                    ('is_pool_product', '=', True)
                ])
            else:
                cat.product_count = 0


class PoolBrand(models.Model):
    """Marques de produits piscine"""
    _name = 'pool.brand'
    _description = 'Marque piscine'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    # Image et description
    logo = fields.Binary(string='Logo')
    description = fields.Html(string='Description')
    website_url = fields.Char(string='Site web officiel')
    
    # Fournisseur principal
    main_supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur principal'
    )
    
    # Produits
    product_ids = fields.One2many(
        'product.template',
        'pool_brand_id',
        string='Produits'
    )
    product_count = fields.Integer(
        string='Nombre de produits',
        compute='_compute_product_count'
    )
    
    def _compute_product_count(self):
        for brand in self:
            brand.product_count = len(brand.product_ids)
    
    def action_view_products(self):
        """Voir les produits de cette marque"""
        self.ensure_one()
        return {
            'name': _('Produits %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('pool_brand_id', '=', self.id)],
            'context': {'default_pool_brand_id': self.id},
        }


class PoolAttribute(models.Model):
    """Attributs spécifiques piscine (volume, débit, etc.)"""
    _name = 'pool.attribute'
    _description = 'Attribut piscine'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    code = fields.Char(string='Code technique')
    sequence = fields.Integer(default=10)
    
    attribute_type = fields.Selection([
        ('char', 'Texte'),
        ('float', 'Nombre décimal'),
        ('integer', 'Nombre entier'),
        ('selection', 'Liste de choix'),
        ('boolean', 'Oui/Non'),
    ], string='Type', default='char', required=True)
    
    unit = fields.Char(string='Unité', help="Ex: m³/h, W, m², etc.")
    
    # Pour les attributs de type selection
    value_ids = fields.One2many(
        'pool.attribute.value',
        'attribute_id',
        string='Valeurs possibles'
    )
    
    # Catégories où cet attribut est pertinent
    category_ids = fields.Many2many(
        'pool.product.category',
        string='Catégories concernées'
    )


class PoolAttributeValue(models.Model):
    """Valeurs possibles pour les attributs de type sélection"""
    _name = 'pool.attribute.value'
    _description = 'Valeur attribut piscine'
    _order = 'sequence, name'

    attribute_id = fields.Many2one(
        'pool.attribute',
        string='Attribut',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Valeur', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
