# -*- coding: utf-8 -*-
import base64
import csv
import io
import logging
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PoolImportLog(models.Model):
    """Journal des imports de produits"""
    _name = 'pool.import.log'
    _description = "Log d'import piscine"
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Référence',
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur',
        required=True,
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('processing', 'En cours'),
        ('done', 'Terminé'),
        ('error', 'Erreur'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', tracking=True)
    
    import_method = fields.Selection([
        ('csv', 'Import CSV/Excel'),
        ('api', 'API REST'),
        ('ocr', 'OCR (catalogue PDF)'),
        ('scraping', 'Web Scraping'),
        ('manual', 'Saisie manuelle'),
    ], string="Méthode d'import")
    
    # Fichier importé
    file_data = fields.Binary(string='Fichier')
    file_name = fields.Char(string='Nom du fichier')
    
    # Options d'import
    update_existing = fields.Boolean(
        string='Mettre à jour les produits existants',
        default=True
    )
    create_category = fields.Boolean(
        string='Créer les catégories manquantes',
        default=True
    )
    import_images = fields.Boolean(
        string='Importer les images',
        default=True
    )
    
    # Statistiques
    total_lines = fields.Integer(string='Total lignes', readonly=True)
    imported_count = fields.Integer(string='Importés', readonly=True)
    updated_count = fields.Integer(string='Mis à jour', readonly=True)
    error_count = fields.Integer(string='Erreurs', readonly=True)
    skipped_count = fields.Integer(string='Ignorés', readonly=True)
    
    # Lignes d'import
    line_ids = fields.One2many(
        'pool.import.line',
        'import_log_id',
        string='Lignes'
    )
    
    # Notes et erreurs
    notes = fields.Text(string='Notes')
    error_message = fields.Text(string='Message erreur')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pool.import.log') or _('Nouveau')
        return super().create(vals_list)
    
    def action_process(self):
        """Lancer le traitement de l'import"""
        self.ensure_one()
        
        if not self.file_data and self.import_method == 'csv':
            raise UserError(_("Veuillez charger un fichier à importer."))
        
        self.state = 'processing'
        
        try:
            if self.import_method == 'csv':
                self._process_csv()
            elif self.import_method == 'api':
                self._process_api()
            else:
                raise UserError(_("Méthode d'import non supportée."))
            
            self.state = 'done'
            self.supplier_id.last_import_date = fields.Datetime.now()
            self.supplier_id.last_import_count = self.imported_count + self.updated_count
            
        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.exception("Erreur lors de l'import")
            raise
    
    def _process_csv(self):
        """Traiter un fichier CSV"""
        self.ensure_one()
        
        # Décoder le fichier
        file_content = base64.b64decode(self.file_data)
        encoding = self.supplier_id.csv_encoding or 'utf-8'
        delimiter = self.supplier_id.csv_delimiter or ';'
        
        try:
            text_content = file_content.decode(encoding)
        except UnicodeDecodeError:
            text_content = file_content.decode('latin-1')
        
        # Parser le CSV
        reader = csv.DictReader(
            io.StringIO(text_content),
            delimiter=delimiter
        )
        
        # Récupérer le mapping
        field_mapping = {
            m.source_field: m for m in self.supplier_id.field_mapping_ids
        }
        
        lines_data = []
        for i, row in enumerate(reader):
            if i < (self.supplier_id.csv_skip_lines or 0):
                continue
            
            line_vals = self._prepare_import_line(row, field_mapping)
            if line_vals:
                lines_data.append((0, 0, line_vals))
        
        self.total_lines = len(lines_data)
        self.line_ids = lines_data
        
        # Traiter les lignes
        self._import_lines()
    
    def _prepare_import_line(self, row, field_mapping):
        """Préparer une ligne d'import à partir d'une ligne CSV"""
        vals = {
            'import_log_id': self.id,
            'raw_data': str(row),
            'state': 'pending',
        }
        
        for source_field, value in row.items():
            if source_field in field_mapping:
                mapping = field_mapping[source_field]
                target = mapping.target_field
                transformed_value = mapping.apply_transformation(value)
                
                if target == 'default_code':
                    vals['product_ref'] = transformed_value
                elif target == 'name':
                    vals['product_name'] = transformed_value
                elif target == 'description':
                    vals['description'] = transformed_value
                elif target == 'standard_price':
                    vals['cost_price'] = transformed_value if isinstance(transformed_value, (int, float)) else 0.0
                elif target == 'list_price':
                    vals['sale_price'] = transformed_value if isinstance(transformed_value, (int, float)) else 0.0
                elif target == 'barcode':
                    vals['barcode'] = transformed_value
                elif target == 'categ_id':
                    vals['category_name'] = transformed_value
                elif target == 'supplier_code':
                    vals['supplier_code'] = transformed_value
                elif target == 'image_url':
                    vals['image_url'] = transformed_value
                elif target == 'brand':
                    vals['brand_name'] = transformed_value
        
        # Vérifier qu'on a au moins une référence ou un nom
        if not vals.get('product_ref') and not vals.get('product_name'):
            return None
        
        return vals
    
    def _import_lines(self):
        """Importer les lignes préparées"""
        imported = 0
        updated = 0
        errors = 0
        skipped = 0
        
        for line in self.line_ids:
            try:
                result = line.action_import()
                if result == 'created':
                    imported += 1
                elif result == 'updated':
                    updated += 1
                elif result == 'skipped':
                    skipped += 1
            except Exception as e:
                errors += 1
                line.state = 'error'
                line.error_message = str(e)
                _logger.warning(f"Erreur import ligne {line.id}: {e}")
        
        self.imported_count = imported
        self.updated_count = updated
        self.error_count = errors
        self.skipped_count = skipped
    
    def _process_api(self):
        """Traiter un import via API"""
        raise UserError(_("L'import API n'est pas encore implémenté."))
    
    def action_cancel(self):
        """Annuler l'import"""
        self.state = 'cancelled'
    
    def action_reset(self):
        """Remettre en brouillon"""
        self.state = 'draft'
        self.line_ids.unlink()
        self.imported_count = 0
        self.updated_count = 0
        self.error_count = 0
        self.skipped_count = 0


class PoolImportLine(models.Model):
    """Ligne d'import de produit"""
    _name = 'pool.import.line'
    _description = "Ligne d'import piscine"
    _order = 'id'

    import_log_id = fields.Many2one(
        'pool.import.log',
        string='Log import',
        required=True,
        ondelete='cascade'
    )
    supplier_id = fields.Many2one(
        related='import_log_id.supplier_id',
        store=True
    )
    
    state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Importé'),
        ('updated', 'Mis à jour'),
        ('skipped', 'Ignoré'),
        ('error', 'Erreur'),
    ], string='État', default='pending')
    
    # Données brutes
    raw_data = fields.Text(string='Données brutes')
    
    # Données parsées
    product_ref = fields.Char(string='Référence')
    product_name = fields.Char(string='Nom')
    description = fields.Text(string='Description')
    cost_price = fields.Float(string="Prix d'achat")
    sale_price = fields.Float(string='Prix de vente')
    barcode = fields.Char(string='Code-barres')
    category_name = fields.Char(string='Catégorie')
    brand_name = fields.Char(string='Marque')
    supplier_code = fields.Char(string='Réf. fournisseur')
    image_url = fields.Char(string='URL image')
    
    # Résultat
    product_id = fields.Many2one('product.template', string='Produit créé/mis à jour')
    error_message = fields.Text(string='Message erreur')
    
    def action_import(self):
        """Importer cette ligne comme produit"""
        self.ensure_one()
        
        Product = self.env['product.template']
        
        # Chercher un produit existant
        existing = None
        if self.product_ref:
            existing = Product.search([('default_code', '=', self.product_ref)], limit=1)
        if not existing and self.barcode:
            existing = Product.search([('barcode', '=', self.barcode)], limit=1)
        
        # Préparer les valeurs
        vals = self._prepare_product_vals()
        
        if existing:
            if self.import_log_id.update_existing:
                existing.write(vals)
                self.product_id = existing
                self.state = 'updated'
                return 'updated'
            else:
                self.state = 'skipped'
                return 'skipped'
        else:
            product = Product.create(vals)
            self.product_id = product
            self.state = 'done'
            
            # Ajouter info fournisseur
            if self.supplier_id.partner_id:
                self.env['product.supplierinfo'].create({
                    'product_tmpl_id': product.id,
                    'partner_id': self.supplier_id.partner_id.id,
                    'product_code': self.supplier_code or self.product_ref,
                    'price': self.cost_price,
                })
            
            # Importer l'image si demandé
            if self.import_log_id.import_images and self.image_url:
                self._import_image(product)
            
            return 'created'
    
    def _prepare_product_vals(self):
        """Préparer les valeurs pour créer/mettre à jour un produit"""
        vals = {
            'name': self.product_name or self.product_ref,
            'default_code': self.product_ref,
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': True,
            'is_pool_product': True,
        }
        
        if self.description:
            vals['description_sale'] = self.description
        
        if self.barcode:
            vals['barcode'] = self.barcode
        
        # Prix de vente
        if self.sale_price:
            vals['list_price'] = self.sale_price
        elif self.cost_price:
            # Calculer avec la marge du fournisseur
            vals['list_price'] = self.supplier_id.calculate_sale_price(self.cost_price)
        
        # Prix d'achat
        if self.cost_price:
            vals['standard_price'] = self.cost_price
        
        # Catégorie
        category = self._find_or_create_category()
        if category:
            vals['categ_id'] = category.id
        elif self.supplier_id.default_category_id:
            vals['categ_id'] = self.supplier_id.default_category_id.id
        
        # Marque
        if self.brand_name:
            brand = self._find_or_create_brand()
            if brand:
                vals['pool_brand_id'] = brand.id
        
        return vals
    
    def _find_or_create_category(self):
        """Trouver ou créer une catégorie"""
        if not self.category_name:
            return False
        
        Category = self.env['product.category']
        
        # Recherche exacte
        category = Category.search([('name', '=ilike', self.category_name)], limit=1)
        if category:
            return category
        
        # Créer si autorisé
        if self.import_log_id.create_category:
            parent = self.env.ref('lolirine_pool.product_category_pool', raise_if_not_found=False)
            category = Category.create({
                'name': self.category_name,
                'parent_id': parent.id if parent else False,
            })
            return category
        
        return False
    
    def _find_or_create_brand(self):
        """Trouver ou créer une marque"""
        if not self.brand_name:
            return False
        
        Brand = self.env['pool.brand']
        brand = Brand.search([('name', '=ilike', self.brand_name)], limit=1)
        
        if not brand:
            brand = Brand.create({'name': self.brand_name})
        
        return brand
    
    def _import_image(self, product):
        """Importer l'image du produit depuis l'URL"""
        if not self.image_url:
            return
        
        try:
            import requests
            response = requests.get(self.image_url, timeout=10)
            if response.status_code == 200:
                image_data = base64.b64encode(response.content)
                product.image_1920 = image_data
        except Exception as e:
            _logger.warning(f"Erreur import image {self.image_url}: {e}")
