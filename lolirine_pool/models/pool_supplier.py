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
    ], string='Méthode d\'import', default='csv', required=True)
    
    # URLs et connexion
    website_url = fields.Char(string='Site web')
    catalog_url = fields.Char(string='URL catalogue en ligne')
    api_endpoint = fields.Char(string='Endpoint API')
    api_key = fields.Char(string='Clé API')
    api_secret = fields.Char(string='Secret API')
    
    # Authentification
    login = fields.Char(string='Identifiant')
    password = fields.Char(string='Mot de passe')
    
    # Mapping des champs
    field_mapping_ids = fields.One2many(
        'pool.supplier.field.mapping',
        'supplier_id',
        string='Mapping des champs'
    )
    
    # Configuration prix
    price_field = fields.Selection([
        ('cost', 'Prix d\'achat'),
        ('list', 'Prix de vente'),
        ('both', 'Les deux'),
    ], string='Type de prix importé', default='cost')
    
    margin_type = fields.Selection([
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
        ('formula', 'Formule personnalisée'),
    ], string='Type de marge', default='percentage')
    
    default_margin = fields.Float(
        string='Marge par défaut (%)',
        default=30.0,
        help="Marge appliquée par défaut pour calculer le prix de vente"
    )
    
    margin_formula = fields.Char(
        string='Formule de marge',
        help="Formule Python. Variables: cost, qty. Ex: cost * 1.3 + 5"
    )
    
    # Catégorie par défaut
    default_category_id = fields.Many2one(
        'product.category',
        string='Catégorie par défaut'
    )
    
    # Statistiques
    product_count = fields.Integer(
        string='Produits',
        compute='_compute_product_count'
    )
    last_import_date = fields.Datetime(
        string='Dernier import',
        readonly=True
    )
    import_count = fields.Integer(
        string='Nombre d\'imports',
        compute='_compute_import_count'
    )
    
    # Notes
    notes = fields.Html(string='Notes et instructions')
    
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Le code fournisseur doit être unique !'),
    ]
    
    @api.depends('partner_id')
    def _compute_product_count(self):
        for supplier in self:
            if supplier.partner_id:
                supplier.product_count = self.env['product.supplierinfo'].search_count([
                    ('partner_id', '=', supplier.partner_id.id)
                ])
            else:
                supplier.product_count = self.env['pool.product.import'].search_count([
                    ('supplier_id', '=', supplier.id),
                    ('product_id', '!=', False)
                ])
    
    @api.depends()
    def _compute_import_count(self):
        ImportLog = self.env['pool.import.log']
        for supplier in self:
            supplier.import_count = ImportLog.search_count([
                ('supplier_id', '=', supplier.id)
            ])
    
    def action_view_products(self):
        """Voir les produits de ce fournisseur"""
        self.ensure_one()
        if self.partner_id:
            supplierinfo = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.partner_id.id)
            ])
            product_ids = supplierinfo.mapped('product_tmpl_id').ids
        else:
            imports = self.env['pool.product.import'].search([
                ('supplier_id', '=', self.id),
                ('product_id', '!=', False)
            ])
            product_ids = imports.mapped('product_id.product_tmpl_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Produits {self.name}',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', product_ids)],
            'context': {'default_pool_supplier_id': self.id}
        }
    
    def action_open_import_wizard(self):
        """Ouvrir l'assistant d'import"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Import {self.name}',
            'res_model': 'pool.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_supplier_id': self.id,
                'default_import_method': self.import_method,
            }
        }
    
    def action_test_connection(self):
        """Tester la connexion API"""
        self.ensure_one()
        if self.import_method != 'api':
            raise UserError(_("Ce fournisseur n'utilise pas d'API."))
        
        # Implémentation spécifique selon le type de fournisseur
        if self.supplier_type == 'fluidra':
            return self._test_fluidra_connection()
        elif self.supplier_type == 'scp':
            return self._test_scp_connection()
        else:
            raise UserError(_("Test de connexion non implémenté pour ce fournisseur."))
    
    def _test_fluidra_connection(self):
        """Test connexion Fluidra"""
        # À implémenter selon l'API Fluidra
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test de connexion'),
                'message': _('Connexion Fluidra à implémenter.'),
                'type': 'warning',
            }
        }
    
    def _test_scp_connection(self):
        """Test connexion SCP"""
        # À implémenter selon l'API SCP
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test de connexion'),
                'message': _('Connexion SCP à implémenter.'),
                'type': 'warning',
            }
        }
    
    def calculate_sale_price(self, cost_price):
        """Calculer le prix de vente selon la configuration"""
        self.ensure_one()
        if not cost_price:
            return 0.0
        
        if self.margin_type == 'percentage':
            return cost_price * (1 + self.default_margin / 100)
        elif self.margin_type == 'fixed':
            return cost_price + self.default_margin
        elif self.margin_type == 'formula' and self.margin_formula:
            try:
                # Exécution sécurisée de la formule
                local_vars = {'cost': cost_price, 'qty': 1}
                return eval(self.margin_formula, {"__builtins__": {}}, local_vars)
            except Exception as e:
                _logger.warning(f"Erreur formule marge: {e}")
                return cost_price * 1.3  # Fallback 30%
        
        return cost_price * 1.3  # Default 30%


class PoolSupplierFieldMapping(models.Model):
    """Mapping des champs pour l'import"""
    _name = 'pool.supplier.field.mapping'
    _description = 'Mapping champs fournisseur'
    _order = 'sequence'
    
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
        help="Nom du champ dans le fichier/API du fournisseur"
    )
    
    target_field = fields.Selection([
        ('default_code', 'Référence interne'),
        ('name', 'Nom du produit'),
        ('description', 'Description'),
        ('description_sale', 'Description de vente'),
        ('list_price', 'Prix de vente'),
        ('standard_price', 'Prix d\'achat'),
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
