from odoo import models, fields, api


class PoolSupplier(models.Model):
    _name = 'pool.supplier'
    _description = 'Fournisseur Piscine'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    # Informations fournisseur
    partner_id = fields.Many2one('res.partner', string='Partenaire')
    website = fields.Char(string='Site Web')
    catalog_url = fields.Char(string='URL Catalogue')
    
    # Configuration des marges
    default_margin = fields.Float(string='Marge par défaut (%)', default=35.0)
    min_margin = fields.Float(string='Marge minimum (%)', default=20.0)
    price_rounding = fields.Selection([
        ('0.99', 'XX.99'),
        ('0.95', 'XX.95'),
        ('0', 'Arrondi normal'),
    ], string='Prix psychologique', default='0.99')
    
    # Marques associées
    brand_ids = fields.One2many('pool.supplier.brand', 'supplier_id', string='Marques')
    
    # Mapping catégories
    category_mapping_ids = fields.One2many(
        'pool.supplier.category.mapping', 'supplier_id', 
        string='Mapping Catégories'
    )
    
    # Statistiques
    product_count = fields.Integer(compute='_compute_product_count', string='Produits')
    last_import_date = fields.Datetime(string='Dernier import')
    
    @api.depends('code')
    def _compute_product_count(self):
        for supplier in self:
            supplier.product_count = self.env['product.template'].search_count([
                ('x_pool_supplier_id', '=', supplier.id)
            ])
    
    def action_view_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Produits {self.name}',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('x_pool_supplier_id', '=', self.id)],
            'context': {'default_x_pool_supplier_id': self.id},
        }
    
    def calculate_selling_price(self, purchase_price, margin=None):
        """Calcule le prix de vente avec marge et arrondi psychologique"""
        self.ensure_one()
        margin = margin or self.default_margin
        raw_price = purchase_price * (1 + margin / 100)
        
        if self.price_rounding == '0.99':
            return max(round(raw_price) - 0.01, purchase_price * 1.1)
        elif self.price_rounding == '0.95':
            return max(round(raw_price) - 0.05, purchase_price * 1.1)
        else:
            return round(raw_price, 2)


class PoolSupplierBrand(models.Model):
    _name = 'pool.supplier.brand'
    _description = 'Marque Fournisseur Piscine'

    name = fields.Char(string='Nom', required=True)
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur', required=True, ondelete='cascade')
    logo = fields.Binary(string='Logo')
    active = fields.Boolean(default=True)


class PoolSupplierCategoryMapping(models.Model):
    _name = 'pool.supplier.category.mapping'
    _description = 'Mapping Catégorie Fournisseur'

    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur', required=True, ondelete='cascade')
    supplier_category = fields.Char(string='Catégorie Fournisseur', required=True)
    supplier_prefix = fields.Char(string='Préfixe Catalogue')
    odoo_category_id = fields.Many2one('product.category', string='Catégorie Odoo', required=True)
