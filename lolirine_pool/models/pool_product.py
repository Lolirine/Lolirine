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
    
    # Lien avec catégorie Odoo
    product_category_id = fields.Many2one(
        'product.category',
        string='Catégorie produit Odoo'
    )
    
    # Icône et description
    icon = fields.Char(string='Icône (Font Awesome)', default='fa-tint')
    description = fields.Text(string='Description', translate=True)
    image = fields.Binary(string='Image')
    
    # Configuration
    default_margin = fields.Float(
        string='Marge par défaut (%)',
        help="Surcharge la marge du fournisseur pour cette catégorie"
    )
    
    product_count = fields.Integer(
        string='Produits',
        compute='_compute_product_count'
    )
    
    def _compute_product_count(self):
        for cat in self:
            if cat.product_category_id:
                cat.product_count = self.env['product.template'].search_count([
                    ('categ_id', 'child_of', cat.product_category_id.id)
                ])
            else:
                cat.product_count = 0


class PoolBrand(models.Model):
    """Marques de produits piscine"""
    _name = 'pool.brand'
    _description = 'Marque piscine'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)
    
    logo = fields.Binary(string='Logo')
    website = fields.Char(string='Site web')
    description = fields.Html(string='Description')
    
    # Fournisseurs liés
    supplier_ids = fields.Many2many(
        'pool.supplier',
        string='Fournisseurs'
    )
    
    product_count = fields.Integer(
        string='Produits',
        compute='_compute_product_count'
    )
    
    def _compute_product_count(self):
        for brand in self:
            brand.product_count = self.env['product.template'].search_count([
                ('pool_brand_id', '=', brand.id)
            ])


class PoolProductAttribute(models.Model):
    """Attributs techniques spécifiques piscine"""
    _name = 'pool.product.attribute'
    _description = 'Attribut technique piscine'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    code = fields.Char(string='Code technique')
    sequence = fields.Integer(default=10)
    
    attribute_type = fields.Selection([
        ('char', 'Texte'),
        ('integer', 'Nombre entier'),
        ('float', 'Nombre décimal'),
        ('boolean', 'Oui/Non'),
        ('selection', 'Liste de choix'),
    ], string='Type', default='char', required=True)
    
    # Pour type selection
    selection_values = fields.Text(
        string='Valeurs possibles',
        help="Une valeur par ligne"
    )
    
    unit = fields.Char(string='Unité', help="Ex: m³/h, W, bar, °C")
    
    # Catégories concernées
    category_ids = fields.Many2many(
        'pool.product.category',
        string='Catégories concernées'
    )
    
    # Affichage
    show_on_website = fields.Boolean(
        string='Afficher sur le site',
        default=True
    )
    show_in_filter = fields.Boolean(
        string='Utilisable comme filtre',
        default=False
    )


class PoolProductAttributeValue(models.Model):
    """Valeurs des attributs techniques pour un produit"""
    _name = 'pool.product.attribute.value'
    _description = 'Valeur attribut technique piscine'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Produit',
        required=True,
        ondelete='cascade'
    )
    attribute_id = fields.Many2one(
        'pool.product.attribute',
        string='Attribut',
        required=True,
        ondelete='cascade'
    )
    
    # Valeurs selon le type
    value_char = fields.Char(string='Valeur texte')
    value_integer = fields.Integer(string='Valeur entière')
    value_float = fields.Float(string='Valeur décimale')
    value_boolean = fields.Boolean(string='Valeur booléenne')
    value_selection = fields.Char(string='Valeur sélection')
    
    # Valeur affichée
    display_value = fields.Char(
        string='Valeur affichée',
        compute='_compute_display_value'
    )
    
    @api.depends('attribute_id', 'value_char', 'value_integer', 'value_float', 
                 'value_boolean', 'value_selection')
    def _compute_display_value(self):
        for val in self:
            attr_type = val.attribute_id.attribute_type
            unit = val.attribute_id.unit or ''
            
            if attr_type == 'char':
                val.display_value = val.value_char or ''
            elif attr_type == 'integer':
                val.display_value = f"{val.value_integer} {unit}".strip()
            elif attr_type == 'float':
                val.display_value = f"{val.value_float} {unit}".strip()
            elif attr_type == 'boolean':
                val.display_value = _('Oui') if val.value_boolean else _('Non')
            elif attr_type == 'selection':
                val.display_value = val.value_selection or ''
            else:
                val.display_value = ''
