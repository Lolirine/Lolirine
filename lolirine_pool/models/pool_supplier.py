# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PoolSupplier(models.Model):
    """Fournisseurs de matériel piscine avec configuration d'import"""
    _name = 'pool.supplier'
    _description = 'Fournisseur Piscine'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nom du fournisseur',
        required=True,
        tracking=True
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="Code unique pour identifier le fournisseur (ex: FLUIDRA, SCP, AFP)"
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    # Partenaire Odoo lié
    partner_id = fields.Many2one(
        'res.partner',
        string='Fournisseur (Contact)',
        help="Partenaire Odoo associé pour les achats"
    )
    
    # Configuration
    supplier_type = fields.Selection([
        ('fluidra', 'Fluidra'),
        ('scp', 'SCP Bénélux'),
        ('allforpools', 'Allforpools'),
        ('mypiscine', 'MyPiscine.com'),
        ('generic', 'Autre fournisseur'),
    ], string='Type de fournisseur', default='generic', required=True)
    
    import_method = fields.Selection([
        ('csv', 'Import CSV/Excel'),
        ('api', 'API REST'),
        ('ocr', 'OCR (catalogue PDF)'),
        ('scraping', 'Web Scraping'),
        ('manual', 'Saisie manuelle'),
    ], string="Méthode d'import", default='csv', required=True)
    
    # URLs et connexion
    website_url = fields.Char(string='Site web')
    catalog_url = fields.Char(string='URL catalogue en ligne')
    api_endpoint = fields.Char(string='Endpoint API')
    api_key = fields.Char(string='Clé API')
    api_secret = fields.Char(string='Secret API')
    
    # Configuration CSV
    csv_delimiter = fields.Char(string='Délimiteur CSV', default=';')
    csv_encoding = fields.Selection([
        ('utf-8', 'UTF-8'),
        ('latin-1', 'Latin-1 (ISO-8859-1)'),
        ('cp1252', 'Windows-1252'),
    ], string='Encodage', default='utf-8')
    csv_skip_lines = fields.Integer(string='Lignes à ignorer', default=0)
    
    # Configuration prix et marge
    price_field = fields.Selection([
        ('cost', 'Prix d\'achat HT'),
        ('list_price', 'Prix public conseillé'),
        ('discount_price', 'Prix remisé'),
    ], string='Champ prix source', default='cost')
    
    margin_type = fields.Selection([
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
        ('formula', 'Formule personnalisée'),
    ], string='Type de marge', default='percentage')
    
    default_margin = fields.Float(string='Marge par défaut (%)', default=30.0)
    fixed_margin = fields.Float(string='Marge fixe (€)')
    margin_formula = fields.Text(
        string='Formule de marge',
        help="Formule Python. Variables: cost, category. Ex: cost * 1.3 if cost < 100 else cost * 1.25"
    )
    
    # Catégorie par défaut
    default_category_id = fields.Many2one(
        'product.category',
        string='Catégorie par défaut'
    )
    
    # Statistiques
    product_count = fields.Integer(
        string='Nombre de produits',
        compute='_compute_product_count'
    )
    last_import_date = fields.Datetime(string='Dernier import')
    last_import_count = fields.Integer(string='Produits importés')
    
    # Notes
    notes = fields.Html(string='Notes et instructions')
    
    # Mapping des champs
    field_mapping_ids = fields.One2many(
        'pool.supplier.field.mapping',
        'supplier_id',
        string='Mapping des champs'
    )
    
    # Import logs
    import_log_ids = fields.One2many(
        'pool.import.log',
        'supplier_id',
        string='Historique des imports'
    )
    
    _code_unique = models.Constraint(
        'unique(code)',
        "Le code fournisseur doit être unique !",
    )
    
    @api.depends('partner_id')
    def _compute_product_count(self):
        for supplier in self:
            if supplier.partner_id:
                supplier.product_count = self.env['product.supplierinfo'].search_count([
                    ('partner_id', '=', supplier.partner_id.id)
                ])
            else:
                supplier.product_count = 0
    
    def action_view_products(self):
        """Voir les produits de ce fournisseur"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Aucun partenaire associé à ce fournisseur."))
        
        supplierinfos = self.env['product.supplierinfo'].search([
            ('partner_id', '=', self.partner_id.id)
        ])
        product_ids = supplierinfos.mapped('product_tmpl_id').ids
        
        return {
            'name': _('Produits %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', product_ids)],
            'context': {'default_seller_ids': [(0, 0, {'partner_id': self.partner_id.id})]},
        }
    
    def action_import_products(self):
        """Ouvrir l'assistant d'import"""
        self.ensure_one()
        return {
            'name': _('Importer des produits - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'pool.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_supplier_id': self.id,
                'default_import_method': self.import_method,
            },
        }
    
    def action_view_import_logs(self):
        """Voir l'historique des imports"""
        self.ensure_one()
        return {
            'name': _('Imports - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'pool.import.log',
            'view_mode': 'list,form',
            'domain': [('supplier_id', '=', self.id)],
            'context': {'default_supplier_id': self.id},
        }
    
    def calculate_sale_price(self, cost_price, category=None):
        """Calculer le prix de vente à partir du prix d'achat"""
        self.ensure_one()
        
        if self.margin_type == 'percentage':
            margin_multiplier = 1 + (self.default_margin / 100)
            return cost_price * margin_multiplier
        
        elif self.margin_type == 'fixed':
            return cost_price + self.fixed_margin
        
        elif self.margin_type == 'formula' and self.margin_formula:
            try:
                # Contexte sécurisé pour eval
                local_vars = {
                    'cost': cost_price,
                    'category': category.name if category else '',
                }
                return eval(self.margin_formula, {"__builtins__": {}}, local_vars)
            except Exception as e:
                _logger.warning(f"Erreur formule marge: {e}")
                return cost_price * 1.3
        
        return cost_price * 1.3  # Marge par défaut 30%


class PoolSupplierFieldMapping(models.Model):
    """Mapping des champs CSV/API vers les champs Odoo"""
    _name = 'pool.supplier.field.mapping'
    _description = 'Mapping des champs fournisseur'
    _order = 'sequence, id'

    supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    
    source_field = fields.Char(
        string='Champ source',
        required=True,
        help="Nom de la colonne dans le fichier CSV ou clé dans l'API"
    )
    
    target_field = fields.Selection([
        ('default_code', 'Référence interne'),
        ('name', 'Nom du produit'),
        ('description', 'Description'),
        ('description_sale', 'Description vente'),
        ('list_price', 'Prix de vente'),
        ('standard_price', "Prix d'achat"),
        ('barcode', 'Code-barres (EAN)'),
        ('weight', 'Poids'),
        ('volume', 'Volume'),
        ('categ_id', 'Catégorie'),
        ('supplier_code', 'Réf. fournisseur'),
        ('image_url', 'URL image'),
        ('brand', 'Marque'),
        ('ignore', 'Ignorer ce champ'),
    ], string='Champ cible Odoo', required=True)
    
    transformation = fields.Selection([
        ('none', 'Aucune'),
        ('uppercase', 'MAJUSCULES'),
        ('lowercase', 'minuscules'),
        ('capitalize', 'Première lettre maj'),
        ('strip', 'Supprimer espaces'),
        ('number', 'Convertir en nombre'),
        ('boolean', 'Convertir en booléen'),
        ('custom', 'Transformation custom'),
    ], string='Transformation', default='none')
    
    custom_code = fields.Text(
        string='Code de transformation',
        help="Code Python. Variable 'value' contient la valeur. Ex: value.replace(',', '.')"
    )
    
    default_value = fields.Char(
        string='Valeur par défaut',
        help="Valeur utilisée si le champ source est vide"
    )
    
    def apply_transformation(self, value):
        """Appliquer la transformation sur une valeur"""
        if not value and self.default_value:
            return self.default_value
        
        if not value:
            return value
        
        value = str(value)
        
        if self.transformation == 'uppercase':
            return value.upper()
        elif self.transformation == 'lowercase':
            return value.lower()
        elif self.transformation == 'capitalize':
            return value.capitalize()
        elif self.transformation == 'strip':
            return value.strip()
        elif self.transformation == 'number':
            try:
                # Gérer les formats européens (virgule décimale)
                clean_value = value.replace(' ', '').replace(',', '.')
                return float(clean_value)
            except ValueError:
                return 0.0
        elif self.transformation == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'oui', 'x')
        elif self.transformation == 'custom' and self.custom_code:
            try:
                local_vars = {'value': value}
                exec(self.custom_code, {"__builtins__": {}}, local_vars)
                return local_vars.get('result', value)
            except Exception:
                return value
        
        return value
