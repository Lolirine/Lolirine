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
    _description = 'Log d\'import piscine'
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
    ], string='Méthode d\'import')
    
    # Fichier importé
    import_file = fields.Binary(string='Fichier importé')
    import_filename = fields.Char(string='Nom du fichier')
    
    # Statistiques
    total_lines = fields.Integer(string='Lignes totales', readonly=True)
    created_count = fields.Integer(string='Produits créés', readonly=True)
    updated_count = fields.Integer(string='Produits mis à jour', readonly=True)
    error_count = fields.Integer(string='Erreurs', readonly=True)
    skipped_count = fields.Integer(string='Ignorés', readonly=True)
    
    # Dates
    start_date = fields.Datetime(string='Début', readonly=True)
    end_date = fields.Datetime(string='Fin', readonly=True)
    duration = fields.Float(
        string='Durée (sec)',
        compute='_compute_duration',
        store=True
    )
    
    # Lignes d'import
    line_ids = fields.One2many(
        'pool.product.import',
        'import_log_id',
        string='Lignes importées'
    )
    
    # Log détaillé
    log_text = fields.Text(string='Journal détaillé')
    error_log = fields.Text(string='Erreurs détaillées')
    
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
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pool.import.log') or _('Nouveau')
        return super().create(vals_list)
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for log in self:
            if log.start_date and log.end_date:
                delta = log.end_date - log.start_date
                log.duration = delta.total_seconds()
            else:
                log.duration = 0
    
    def action_view_products(self):
        """Voir les produits importés"""
        self.ensure_one()
        product_ids = self.line_ids.filtered(
            lambda l: l.product_id
        ).mapped('product_id.product_tmpl_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Produits importés - {self.name}',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', product_ids)],
        }
    
    def action_view_errors(self):
        """Voir les lignes en erreur"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Erreurs - {self.name}',
            'res_model': 'pool.product.import',
            'view_mode': 'tree,form',
            'domain': [('import_log_id', '=', self.id), ('state', '=', 'error')],
        }
    
    def action_cancel(self):
        """Annuler l'import"""
        self.write({'state': 'cancelled'})
    
    def action_retry(self):
        """Réessayer les lignes en erreur"""
        self.ensure_one()
        error_lines = self.line_ids.filtered(lambda l: l.state == 'error')
        if not error_lines:
            raise UserError(_("Aucune ligne en erreur à réessayer."))
        
        for line in error_lines:
            line.action_process()
        
        self._update_counts()
    
    def _update_counts(self):
        """Mettre à jour les compteurs"""
        for log in self:
            log.created_count = len(log.line_ids.filtered(lambda l: l.state == 'created'))
            log.updated_count = len(log.line_ids.filtered(lambda l: l.state == 'updated'))
            log.error_count = len(log.line_ids.filtered(lambda l: l.state == 'error'))
            log.skipped_count = len(log.line_ids.filtered(lambda l: l.state == 'skipped'))
    
    def _add_log(self, message, level='info'):
        """Ajouter une entrée au journal"""
        self.ensure_one()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level.upper()}] {message}\n"
        
        if level == 'error':
            self.error_log = (self.error_log or '') + log_entry
        
        self.log_text = (self.log_text or '') + log_entry


class PoolProductImport(models.Model):
    """Ligne d'import de produit"""
    _name = 'pool.product.import'
    _description = 'Import produit piscine'
    _order = 'create_date desc'

    import_log_id = fields.Many2one(
        'pool.import.log',
        string='Import',
        ondelete='cascade'
    )
    supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur',
        required=True
    )
    
    state = fields.Selection([
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('created', 'Créé'),
        ('updated', 'Mis à jour'),
        ('skipped', 'Ignoré'),
        ('error', 'Erreur'),
    ], string='État', default='pending')
    
    # Données brutes
    raw_data = fields.Text(string='Données brutes (JSON)')
    
    # Données parsées
    supplier_code = fields.Char(string='Réf. fournisseur')
    product_name = fields.Char(string='Nom produit')
    product_description = fields.Text(string='Description')
    ean_code = fields.Char(string='Code EAN')
    cost_price = fields.Float(string='Prix d\'achat')
    sale_price = fields.Float(string='Prix de vente')
    category_name = fields.Char(string='Catégorie')
    brand = fields.Char(string='Marque')
    image_url = fields.Char(string='URL image')
    weight = fields.Float(string='Poids (kg)')
    
    # Produit Odoo créé/lié
    product_id = fields.Many2one(
        'product.product',
        string='Produit Odoo'
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Modèle produit',
        related='product_id.product_tmpl_id',
        store=True
    )
    
    # Erreur
    error_message = fields.Text(string='Message d\'erreur')
    
    def action_process(self):
        """Traiter cette ligne d'import"""
        self.ensure_one()
        self.state = 'processing'
        
        try:
            # Rechercher produit existant
            product = self._find_existing_product()
            
            if product:
                if self.import_log_id.update_existing:
                    self._update_product(product)
                    self.product_id = product.id
                    self.state = 'updated'
                else:
                    self.state = 'skipped'
            else:
                product = self._create_product()
                self.product_id = product.id
                self.state = 'created'
            
            self.error_message = False
            
        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.exception(f"Erreur import produit: {self.supplier_code}")
    
    def _find_existing_product(self):
        """Rechercher un produit existant"""
        Product = self.env['product.product']
        
        # Recherche par EAN
        if self.ean_code:
            product = Product.search([('barcode', '=', self.ean_code)], limit=1)
            if product:
                return product
        
        # Recherche par référence fournisseur
        if self.supplier_code and self.supplier_id.partner_id:
            supplierinfo = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.supplier_id.partner_id.id),
                ('product_code', '=', self.supplier_code)
            ], limit=1)
            if supplierinfo and supplierinfo.product_id:
                return supplierinfo.product_id
        
        # Recherche par nom exact
        if self.product_name:
            product = Product.search([('name', '=ilike', self.product_name)], limit=1)
            if product:
                return product
        
        return False
    
    def _create_product(self):
        """Créer le produit dans Odoo"""
        self.ensure_one()
        
        # Déterminer la catégorie
        category = self._get_or_create_category()
        
        # Calculer le prix de vente
        sale_price = self.sale_price
        if not sale_price and self.cost_price:
            sale_price = self.supplier_id.calculate_sale_price(self.cost_price)
        
        # Préparer les valeurs
        vals = {
            'name': self.product_name or f"Produit {self.supplier_code}",
            'default_code': self._generate_internal_ref(),
            'type': 'product',
            'categ_id': category.id if category else self.supplier_id.default_category_id.id,
            'list_price': sale_price or 0.0,
            'standard_price': self.cost_price or 0.0,
            'description_sale': self.product_description,
            'weight': self.weight or 0.0,
            'sale_ok': True,
            'purchase_ok': True,
            'pool_supplier_id': self.supplier_id.id,
            'pool_brand': self.brand,
        }
        
        if self.ean_code:
            vals['barcode'] = self.ean_code
        
        # Créer le produit
        product = self.env['product.product'].create(vals)
        
        # Ajouter les infos fournisseur
        if self.supplier_id.partner_id:
            self.env['product.supplierinfo'].create({
                'product_tmpl_id': product.product_tmpl_id.id,
                'partner_id': self.supplier_id.partner_id.id,
                'product_code': self.supplier_code,
                'price': self.cost_price or 0.0,
            })
        
        # Importer l'image si disponible
        if self.image_url and self.import_log_id.import_images:
            self._import_image(product)
        
        return product
    
    def _update_product(self, product):
        """Mettre à jour un produit existant"""
        vals = {}
        
        if self.product_name and product.name != self.product_name:
            vals['name'] = self.product_name
        
        if self.cost_price:
            vals['standard_price'] = self.cost_price
            # Recalculer le prix de vente
            vals['list_price'] = self.sale_price or self.supplier_id.calculate_sale_price(self.cost_price)
        
        if self.product_description:
            vals['description_sale'] = self.product_description
        
        if self.weight:
            vals['weight'] = self.weight
        
        if self.ean_code and not product.barcode:
            vals['barcode'] = self.ean_code
        
        if vals:
            product.write(vals)
        
        # Mettre à jour supplierinfo
        if self.supplier_id.partner_id and self.cost_price:
            supplierinfo = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('partner_id', '=', self.supplier_id.partner_id.id)
            ], limit=1)
            
            if supplierinfo:
                supplierinfo.write({
                    'price': self.cost_price,
                    'product_code': self.supplier_code,
                })
            else:
                self.env['product.supplierinfo'].create({
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'partner_id': self.supplier_id.partner_id.id,
                    'product_code': self.supplier_code,
                    'price': self.cost_price,
                })
    
    def _get_or_create_category(self):
        """Obtenir ou créer la catégorie"""
        if not self.category_name:
            return False
        
        Category = self.env['product.category']
        
        # Recherche exacte
        category = Category.search([('name', '=ilike', self.category_name)], limit=1)
        if category:
            return category
        
        # Créer si autorisé
        if self.import_log_id.create_category:
            # Catégorie parente = catégorie piscine par défaut
            parent = self.env.ref('lolirine_pool.product_category_pool', raise_if_not_found=False)
            category = Category.create({
                'name': self.category_name,
                'parent_id': parent.id if parent else False,
            })
            return category
        
        return False
    
    def _generate_internal_ref(self):
        """Générer une référence interne unique"""
        prefix = self.supplier_id.code or 'POOL'
        suffix = self.supplier_code or str(self.id)
        return f"{prefix}-{suffix}"
    
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
