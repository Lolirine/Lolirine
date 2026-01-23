# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import json
import csv
import io
import requests
import logging

_logger = logging.getLogger(__name__)


class PoolCatalog(models.Model):
    _name = 'pool.catalog'
    _description = 'Catalogue Piscine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Nom', required=True, tracking=True)
    supplier_id = fields.Many2one('pool.supplier', string='Fournisseur', required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('loaded', 'Chargé'),
        ('validated', 'Validé'),
        ('imported', 'Importé'),
    ], string='État', default='draft', tracking=True)
    
    # Fichier source
    source_file = fields.Binary(string='Fichier source')
    source_filename = fields.Char(string='Nom du fichier')
    source_type = fields.Selection([
        ('json', 'JSON (Export extracteur)'),
        ('csv', 'CSV'),
    ], string='Type de source', default='json')
    
    # Éléments du catalogue
    item_ids = fields.One2many('pool.catalog.item', 'catalog_id', string='Éléments')
    
    # Statistiques
    item_count = fields.Integer(string='Nb éléments', compute='_compute_counts', store=True)
    item_to_import_count = fields.Integer(string='À importer', compute='_compute_counts', store=True)
    item_imported_count = fields.Integer(string='Importés', compute='_compute_counts', store=True)
    item_skipped_count = fields.Integer(string='Ignorés', compute='_compute_counts', store=True)
    
    # Options d'import
    update_existing = fields.Boolean(string='Mettre à jour existants', default=True)
    recalculate_prices = fields.Boolean(string='Recalculer les prix', default=False)
    
    # Dates
    load_date = fields.Datetime(string='Date de chargement')
    import_date = fields.Datetime(string='Date d\'import')
    
    notes = fields.Html(string='Notes')
    
    @api.depends('item_ids', 'item_ids.state')
    def _compute_counts(self):
        for catalog in self:
            items = catalog.item_ids
            catalog.item_count = len(items)
            catalog.item_to_import_count = len(items.filtered(lambda i: i.state == 'to_import'))
            catalog.item_imported_count = len(items.filtered(lambda i: i.state == 'imported'))
            catalog.item_skipped_count = len(items.filtered(lambda i: i.state == 'skipped'))
    
    @api.onchange('source_file')
    def _onchange_source_file(self):
        """Détecte automatiquement le type de fichier"""
        if self.source_filename:
            if self.source_filename.endswith('.json'):
                self.source_type = 'json'
            elif self.source_filename.endswith('.csv'):
                self.source_type = 'csv'
    
    def action_load_file(self):
        """Charge le fichier et crée les éléments du catalogue"""
        self.ensure_one()
        
        if not self.source_file:
            raise UserError(_("Veuillez sélectionner un fichier"))
        
        # Supprimer les anciens éléments
        self.item_ids.unlink()
        
        content = base64.b64decode(self.source_file)
        
        if self.source_type == 'json':
            self._load_json(content)
        else:
            self._load_csv(content)
        
        self.write({
            'state': 'loaded',
            'load_date': fields.Datetime.now(),
        })
        
        return True
    
    def _load_json(self, content):
        """Charge un fichier JSON"""
        data = json.loads(content.decode('utf-8'))
        items_vals = []
        
        # Charger les produits simples
        for product in data.get('products', []):
            existing = self.env['product.template'].search([
                ('x_pool_supplier_ref', '=', product.get('ref'))
            ], limit=1)
            
            items_vals.append({
                'catalog_id': self.id,
                'supplier_ref': product.get('ref'),
                'name': product.get('name'),
                'brand': product.get('brand'),
                'category': product.get('category'),
                'subcategory': product.get('subCategory'),
                'purchase_price': product.get('purchasePrice', 0),
                'selling_price': product.get('sellingPrice', 0),
                'description_fr': product.get('descriptionFr'),
                'description_nl': product.get('descriptionNl'),
                'image_url': product.get('imageUrl'),
                'is_template': False,
                'existing_product_id': existing.id if existing else False,
                'state': 'exists' if existing else 'to_import',
                'raw_data': json.dumps(product),
            })
        
        # Charger les templates
        for template in data.get('productTemplates', []):
            items_vals.append({
                'catalog_id': self.id,
                'supplier_ref': template.get('id'),
                'name': template.get('name'),
                'brand': template.get('brand'),
                'category': template.get('category'),
                'is_template': True,
                'variants_count': len(template.get('variants', [])),
                'attributes_info': ', '.join([a.get('name', '') for a in template.get('attributes', [])]),
                'state': 'to_import',
                'raw_data': json.dumps(template),
            })
        
        self.env['pool.catalog.item'].create(items_vals)
    
    def _load_csv(self, content):
        """Charge un fichier CSV"""
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text), delimiter=';')
        items_vals = []
        
        for row in reader:
            ref = row.get('ref') or row.get('x_supplier_ref') or row.get('default_code', '').replace('POOL-', '')
            existing = self.env['product.template'].search([
                ('x_pool_supplier_ref', '=', ref)
            ], limit=1)
            
            items_vals.append({
                'catalog_id': self.id,
                'supplier_ref': ref,
                'name': row.get('name'),
                'brand': row.get('brand') or row.get('x_brand'),
                'category': row.get('category'),
                'purchase_price': float(row.get('standard_price', 0) or row.get('purchasePrice', 0) or 0),
                'selling_price': float(row.get('list_price', 0) or row.get('sellingPrice', 0) or 0),
                'existing_product_id': existing.id if existing else False,
                'state': 'exists' if existing else 'to_import',
                'raw_data': json.dumps(row),
            })
        
        self.env['pool.catalog.item'].create(items_vals)
    
    def action_validate(self):
        """Valide le catalogue pour l'import"""
        self.ensure_one()
        self.state = 'validated'
    
    def action_import(self):
        """Importe les éléments sélectionnés"""
        self.ensure_one()
        
        items_to_import = self.item_ids.filtered(lambda i: i.state == 'to_import' and i.selected)
        if not items_to_import:
            items_to_import = self.item_ids.filtered(lambda i: i.state == 'to_import')
        
        if not items_to_import:
            raise UserError(_("Aucun élément à importer"))
        
        imported = 0
        updated = 0
        errors = 0
        
        for item in items_to_import:
            try:
                if item.is_template:
                    item._import_as_template()
                else:
                    item._import_as_product()
                imported += 1
            except Exception as e:
                item.write({
                    'state': 'error',
                    'error_message': str(e),
                })
                errors += 1
        
        self.write({
            'state': 'imported',
            'import_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': _('%d produits importés, %d erreurs') % (imported, errors),
                'type': 'success' if errors == 0 else 'warning',
                'sticky': False,
            }
        }
    
    def action_select_all(self):
        """Sélectionne tous les éléments à importer"""
        self.item_ids.filtered(lambda i: i.state == 'to_import').write({'selected': True})
    
    def action_deselect_all(self):
        """Désélectionne tous les éléments"""
        self.item_ids.write({'selected': False})
    
    @api.model
    def extract_product_from_image(self, image_base64):
        """
        Extrait les informations produit d'une image via Claude API
        
        :param image_base64: Image encodée en base64
        :return: dict avec success, data ou error
        """
        # Récupérer la clé API depuis les paramètres système
        api_key = self.env['ir.config_parameter'].sudo().get_param('pool.claude_api_key')
        
        if not api_key:
            # Mode démo sans API - extraction basique
            _logger.warning("Claude API key not configured, using demo mode")
            return {
                'success': True,
                'data': {
                    'reference': '',
                    'name': 'Produit extrait (configurez la clé API Claude)',
                    'brand': '',
                    'category': '',
                    'purchase_price': 0,
                    'selling_price': 0,
                    'description_fr': 'Pour activer l\'extraction IA, configurez le paramètre système pool.claude_api_key',
                },
                'demo_mode': True,
            }
        
        try:
            # Appel à l'API Claude
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            }
            
            prompt = """Analyse cette image d'un catalogue de produits de piscine et extrait les informations suivantes au format JSON:
{
    "reference": "la référence/code produit",
    "name": "le nom complet du produit",
    "brand": "la marque",
    "category": "la catégorie (ex: Filtration, Pompes, Robots, etc.)",
    "purchase_price": 0,
    "selling_price": "le prix si visible (nombre uniquement)",
    "description_fr": "description du produit en français"
}

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire."""
            
            payload = {
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 1024,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'image/png',
                                    'data': image_base64,
                                },
                            },
                            {
                                'type': 'text',
                                'text': prompt,
                            },
                        ],
                    },
                ],
            }
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=payload,
                timeout=30,
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('content', [{}])[0].get('text', '{}')
                
                # Parser le JSON de la réponse
                try:
                    # Nettoyer la réponse si elle contient des backticks
                    content = content.strip()
                    if content.startswith('```'):
                        content = content.split('```')[1]
                        if content.startswith('json'):
                            content = content[4:]
                    content = content.strip()
                    
                    data = json.loads(content)
                    return {
                        'success': True,
                        'data': data,
                    }
                except json.JSONDecodeError as e:
                    _logger.error(f"JSON parse error: {e}, content: {content}")
                    return {
                        'success': False,
                        'error': f"Erreur de parsing JSON: {str(e)}",
                    }
            else:
                _logger.error(f"Claude API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur API ({response.status_code}): {response.text[:200]}",
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': "Timeout - L'API n'a pas répondu à temps",
            }
        except Exception as e:
            _logger.error(f"OCR extraction error: {e}")
            return {
                'success': False,
                'error': str(e),
            }


class PoolCatalogItem(models.Model):
    _name = 'pool.catalog.item'
    _description = 'Élément de catalogue'
    _order = 'category, name'

    catalog_id = fields.Many2one('pool.catalog', string='Catalogue', required=True, ondelete='cascade')
    supplier_id = fields.Many2one(related='catalog_id.supplier_id', store=True)
    
    # Données produit
    supplier_ref = fields.Char(string='Réf. Fournisseur', index=True)
    name = fields.Char(string='Nom')
    brand = fields.Char(string='Marque')
    category = fields.Char(string='Catégorie')
    subcategory = fields.Char(string='Sous-catégorie')
    
    purchase_price = fields.Float(string='Prix achat')
    selling_price = fields.Float(string='Prix vente')
    margin = fields.Float(string='Marge %', compute='_compute_margin')
    
    description_fr = fields.Text(string='Description FR')
    description_nl = fields.Text(string='Description NL')
    image_url = fields.Char(string='URL Image')
    
    # Template info
    is_template = fields.Boolean(string='Est un template')
    variants_count = fields.Integer(string='Nb variantes')
    attributes_info = fields.Char(string='Attributs')
    
    # État
    state = fields.Selection([
        ('to_import', 'À importer'),
        ('exists', 'Existe déjà'),
        ('imported', 'Importé'),
        ('skipped', 'Ignoré'),
        ('error', 'Erreur'),
    ], string='État', default='to_import')
    
    selected = fields.Boolean(string='Sélectionné', default=True)
    
    # Lien produit Odoo
    existing_product_id = fields.Many2one('product.template', string='Produit existant')
    created_product_id = fields.Many2one('product.template', string='Produit créé')
    
    # Données brutes et erreurs
    raw_data = fields.Text(string='Données brutes')
    error_message = fields.Text(string='Message d\'erreur')
    
    @api.depends('purchase_price', 'selling_price')
    def _compute_margin(self):
        for item in self:
            if item.selling_price > 0:
                item.margin = ((item.selling_price - item.purchase_price) / item.selling_price) * 100
            else:
                item.margin = 0
    
    def action_skip(self):
        """Marque l'élément comme ignoré"""
        self.write({'state': 'skipped', 'selected': False})
    
    def action_reset(self):
        """Remet l'élément en état 'à importer'"""
        self.write({'state': 'to_import', 'selected': True, 'error_message': False})
    
    def _import_as_product(self):
        """Importe l'élément comme produit simple"""
        self.ensure_one()
        
        supplier = self.catalog_id.supplier_id
        
        vals = {
            'name': self.name,
            'default_code': f"POOL-{self.supplier_ref}",
            'x_pool_supplier_id': supplier.id,
            'x_pool_supplier_ref': self.supplier_ref,
            'x_pool_brand': self.brand,
            'x_pool_category': self.category,
            'x_pool_subcategory': self.subcategory,
            'x_description_fr': self.description_fr,
            'x_description_nl': self.description_nl,
            'description_sale': self.description_fr,
            'standard_price': self.purchase_price,
            'list_price': self.selling_price,
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
            'x_pool_import_date': fields.Datetime.now(),
            'x_pool_import_source': f'Catalogue {self.catalog_id.name}',
        }
        
        # Recalculer le prix si demandé
        if self.catalog_id.recalculate_prices and self.purchase_price:
            vals['list_price'] = supplier.calculate_selling_price(self.purchase_price)
        
        # Mise à jour ou création
        if self.existing_product_id and self.catalog_id.update_existing:
            self.existing_product_id.write(vals)
            self.write({
                'state': 'imported',
                'created_product_id': self.existing_product_id.id,
            })
        else:
            product = self.env['product.template'].create(vals)
            self.write({
                'state': 'imported',
                'created_product_id': product.id,
            })
    
    def _import_as_template(self):
        """Importe l'élément comme template avec variantes"""
        self.ensure_one()
        
        if not self.raw_data:
            raise UserError(_("Données brutes manquantes pour le template"))
        
        template_data = json.loads(self.raw_data)
        product = self.env['product.template'].create_template_with_variants(
            template_data, self.catalog_id.supplier_id
        )
        
        self.write({
            'state': 'imported',
            'created_product_id': product.id,
        })
    
    def action_view_product(self):
        """Ouvre le produit lié"""
        self.ensure_one()
        product = self.created_product_id or self.existing_product_id
        if product:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'res_id': product.id,
                'view_mode': 'form',
            }
