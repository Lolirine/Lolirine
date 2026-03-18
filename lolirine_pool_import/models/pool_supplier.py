from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PoolSupplier(models.Model):
    _name = 'pool.supplier'
    _description = 'Fournisseur Piscine'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    # Type de fournisseur (ajouté pour compatibilité)
    supplier_type = fields.Selection([
        ('manufacturer', 'Fabricant'),
        ('distributor', 'Distributeur'),
        ('wholesaler', 'Grossiste'),
    ], string='Type de fournisseur', default='distributor')
    
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
    
    # Remises par catégorie
    discount_ids = fields.One2many(
        'pool.supplier.discount', 'supplier_id',
        string='Grille de remises'
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
    
    def get_discount_for_category(self, category_code=None, category_name=None):
        """
        Trouve la remise applicable pour une catégorie de produit.
        
        Args:
            category_code: Code alphanumérique Fluidra (ex: FI01F, NK01N, M)
            category_name: Nom de la catégorie pour recherche par mots-clés
        
        Returns:
            tuple: (discount_percent, discount_record) ou (0, None) si pas de remise
        """
        self.ensure_one()
        
        if not self.discount_ids:
            return (0, None)
        
        # 1. Recherche par code exact
        if category_code:
            discount = self.discount_ids.filtered(
                lambda d: d.code and d.code.upper() == category_code.upper()
            )
            if discount:
                return (discount[0].discount_percent, discount[0])
        
        # 2. Recherche par préfixe de code (ex: "NK" pour NK01N, NK02N...)
        if category_code:
            for discount in self.discount_ids.sorted(key=lambda d: len(d.code or ''), reverse=True):
                if discount.code and category_code.upper().startswith(discount.code.upper()):
                    return (discount.discount_percent, discount)
        
        # 3. Recherche par mots-clés dans le nom de catégorie
        if category_name:
            cat_lower = category_name.lower()
            for discount in self.discount_ids:
                if discount.keywords:
                    keywords = [k.strip().lower() for k in discount.keywords.split(',')]
                    for keyword in keywords:
                        if keyword and keyword in cat_lower:
                            return (discount.discount_percent, discount)
        
        # 4. Remise par défaut du fournisseur (code "M" pour Magasin généralement)
        default_discount = self.discount_ids.filtered(lambda d: d.is_default)
        if default_discount:
            return (default_discount[0].discount_percent, default_discount[0])
        
        return (0, None)
    
    def calculate_net_purchase_price(self, catalog_price, category_code=None, category_name=None):
        """
        Calcule le prix d'achat NET après application de la remise fournisseur.
        
        Args:
            catalog_price: Prix catalogue (brut)
            category_code: Code alphanumérique de la catégorie
            category_name: Nom de la catégorie
        
        Returns:
            float: Prix d'achat net après remise
        """
        self.ensure_one()
        
        discount_percent, discount_record = self.get_discount_for_category(category_code, category_name)
        
        if discount_percent > 0:
            net_price = catalog_price * (1 - discount_percent / 100)
            _logger.info(f"Prix catalogue: {catalog_price}€ - Remise {discount_percent}% = Prix net: {net_price:.2f}€")
            return round(net_price, 2)
        
        return catalog_price
    
    def calculate_selling_price(self, purchase_price, margin=None, category_code=None, category_name=None):
        """
        Calcule le prix de vente avec marge et arrondi psychologique.
        
        Args:
            purchase_price: Prix d'achat (peut être brut catalogue ou net)
            margin: Marge à appliquer (utilise default_margin si None)
            category_code: Code pour trouver une marge spécifique
            category_name: Nom catégorie pour marge spécifique
        
        Returns:
            float: Prix de vente calculé
        """
        self.ensure_one()
        
        # Chercher une marge spécifique pour la catégorie
        if category_code or category_name:
            _, discount_record = self.get_discount_for_category(category_code, category_name)
            if discount_record and discount_record.selling_margin:
                margin = discount_record.selling_margin
        
        margin = margin or self.default_margin
        raw_price = purchase_price * (1 + margin / 100)
        
        if self.price_rounding == '0.99':
            return max(round(raw_price) - 0.01, purchase_price * 1.1)
        elif self.price_rounding == '0.95':
            return max(round(raw_price) - 0.05, purchase_price * 1.1)
        else:
            return round(raw_price, 2)
    
    def calculate_prices(self, catalog_price, category_code=None, category_name=None, custom_margin=None):
        """
        Calcule tous les prix en une fois: achat net + vente.
        
        Args:
            catalog_price: Prix catalogue brut
            category_code: Code alphanumérique
            category_name: Nom de catégorie
            custom_margin: Marge personnalisée (optionnel)
        
        Returns:
            dict: {
                'catalog_price': prix catalogue original,
                'discount_percent': remise appliquée,
                'purchase_price': prix d'achat net,
                'margin_percent': marge de vente,
                'selling_price': prix de vente
            }
        """
        self.ensure_one()
        
        discount_percent, discount_record = self.get_discount_for_category(category_code, category_name)
        purchase_price = catalog_price * (1 - discount_percent / 100)
        
        margin = custom_margin or (discount_record.selling_margin if discount_record and discount_record.selling_margin else self.default_margin)
        selling_price = self.calculate_selling_price(purchase_price, margin)
        
        return {
            'catalog_price': catalog_price,
            'discount_percent': discount_percent,
            'purchase_price': round(purchase_price, 2),
            'margin_percent': margin,
            'selling_price': selling_price,
        }


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


class PoolSupplierDiscount(models.Model):
    _name = 'pool.supplier.discount'
    _description = 'Remise Fournisseur par Catégorie'
    _order = 'sequence, code'
    
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    
    # Identification
    code = fields.Char(string='Code Alphanumérique', help='Code catégorie fournisseur (ex: FI01F, NK01N, M)')
    name = fields.Char(string='Description', required=True)
    keywords = fields.Char(string='Mots-clés', help='Mots-clés séparés par virgules pour détection automatique')
    
    # Remises
    discount_percent = fields.Float(string='Remise (%)', required=True, help='Remise sur prix catalogue')
    discount_percent_2 = fields.Float(string='Remise 2 (%)', default=0, help='Remise complémentaire si applicable')
    
    # Marge de vente suggérée
    selling_margin = fields.Float(string='Marge vente (%)', help='Marge de vente suggérée pour cette catégorie')
    
    # Flags
    is_default = fields.Boolean(string='Remise par défaut', default=False)
    active = fields.Boolean(default=True)
    
    # Champs calculés pour affichage
    final_discount = fields.Float(compute='_compute_final_discount', string='Remise totale (%)')
    
    @api.depends('discount_percent', 'discount_percent_2')
    def _compute_final_discount(self):
        for rec in self:
            # Remise cumulée: (1 - (1-r1) * (1-r2)) * 100
            if rec.discount_percent_2:
                rec.final_discount = (1 - (1 - rec.discount_percent/100) * (1 - rec.discount_percent_2/100)) * 100
            else:
                rec.final_discount = rec.discount_percent
