# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Champ pour identifier les produits piscine
    is_pool_product = fields.Boolean(
        string='Produit Piscine',
        default=False,
        help="Cochez pour afficher ce produit uniquement sur le site Lolirine Pool Store"
    )
    
    # Champ pour la catégorie piscine principale
    pool_category_id = fields.Many2one(
        'pool.website.category',
        string='Catégorie Piscine',
        help="Catégorie pour l'affichage sur le site Pool Store"
    )
    
    @api.model
    def _search_get_detail(self, website, order, options):
        """Override pour filtrer les produits par site web"""
        result = super()._search_get_detail(website, order, options)
        
        # Vérifier si on est sur le site Pool
        if website.id == self.env.ref('lolirine_pool_website.website_pool', raise_if_not_found=False).id if self.env.ref('lolirine_pool_website.website_pool', raise_if_not_found=False) else False:
            # Sur le site Pool, afficher uniquement les produits piscine
            if 'base_domain' in result:
                result['base_domain'].append([('is_pool_product', '=', True)])
        else:
            # Sur les autres sites, exclure les produits piscine
            if 'base_domain' in result:
                result['base_domain'].append([('is_pool_product', '=', False)])
        
        return result


class PoolWebsiteCategory(models.Model):
    """Catégories spécifiques pour le site Pool Store"""
    _name = 'pool.website.category'
    _description = 'Catégorie Site Piscine'
    _order = 'sequence, name'
    
    name = fields.Char(string='Nom', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    parent_id = fields.Many2one('pool.website.category', string='Catégorie parente')
    child_ids = fields.One2many('pool.website.category', 'parent_id', string='Sous-catégories')
    
    description = fields.Text(string='Description', translate=True)
    image = fields.Binary(string='Image', attachment=True)
    
    icon = fields.Char(string='Icône Font Awesome', default='fa-tint', 
                       help="Classe Font Awesome (ex: fa-tint, fa-cog, fa-sun-o)")
    
    product_ids = fields.One2many('product.template', 'pool_category_id', string='Produits')
    product_count = fields.Integer(string='Nombre de produits', compute='_compute_product_count')
    
    website_published = fields.Boolean(string='Publié sur le site', default=True)
    
    # Couleur pour l'affichage
    color = fields.Char(string='Couleur', default='#0ea5e9', 
                        help="Couleur hexadécimale pour l'affichage")
    
    @api.depends('product_ids')
    def _compute_product_count(self):
        for cat in self:
            cat.product_count = len(cat.product_ids.filtered(lambda p: p.is_published))
    
    def action_view_products(self):
        """Ouvre la liste des produits de cette catégorie"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Produits - {self.name}',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('pool_category_id', '=', self.id)],
            'context': {'default_pool_category_id': self.id, 'default_is_pool_product': True},
        }
