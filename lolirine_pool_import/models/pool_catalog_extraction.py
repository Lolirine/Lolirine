# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import json
import requests
import logging
import re

_logger = logging.getLogger(__name__)


class PoolCatalogExtraction(models.Model):
    """
    Modèle pour stocker les captures d'écran du catalogue et leurs données extraites.
    Permet de conserver un historique des extractions et de naviguer entre les produits.
    """
    _name = 'pool.catalog.extraction'
    _description = 'Extraction de catalogue'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Nom', 
        compute='_compute_name', 
        store=True
    )
    
    # Image source
    image = fields.Binary(
        string='Capture d\'écran',
        required=True,
        attachment=True
    )
    image_filename = fields.Char(string='Nom du fichier')
    
    # Fournisseur
    supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur',
        tracking=True
    )
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('extracted', 'Extrait'),
        ('imported', 'Importé'),
        ('error', 'Erreur'),
    ], string='État', default='draft', tracking=True)
    
    # Type d'extraction détecté
    extraction_type = fields.Selection([
        ('single', 'Produit unique'),
        ('variants', 'Produit avec variantes'),
        ('multiple', 'Plusieurs produits'),
    ], string='Type d\'extraction', default='single')
    
    # Données extraites (JSON brut)
    raw_extraction_data = fields.Text(string='Données brutes (JSON)')
    
    # Produits extraits (relation One2many)
    extracted_product_ids = fields.One2many(
        'pool.catalog.extraction.product',
        'extraction_id',
        string='Produits extraits'
    )
    
    # Index du produit courant pour la navigation
    current_product_index = fields.Integer(
        string='Produit courant',
        default=0
    )
    
    # Statistiques
    product_count = fields.Integer(
        string='Nombre de produits',
        compute='_compute_counts',
        store=True
    )
    imported_count = fields.Integer(
        string='Produits importés',
        compute='_compute_counts',
        store=True
    )
    
    # Erreur éventuelle
    error_message = fields.Text(string='Message d\'erreur')
    
    # Notes
    notes = fields.Text(string='Notes')
    
    @api.depends('supplier_id', 'create_date')
    def _compute_name(self):
        for rec in self:
            supplier_name = rec.supplier_id.name if rec.supplier_id else 'Sans fournisseur'
            date_str = rec.create_date.strftime('%d/%m/%Y %H:%M') if rec.create_date else ''
            rec.name = f"Extraction {supplier_name} - {date_str}"
    
    @api.depends('extracted_product_ids', 'extracted_product_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.product_count = len(rec.extracted_product_ids)
            rec.imported_count = len(rec.extracted_product_ids.filtered(lambda p: p.state == 'imported'))
    
    def action_extract(self):
        """Lance l'extraction OCR sur l'image"""
        self.ensure_one()
        
        if not self.image:
            raise UserError(_("Veuillez d'abord télécharger une image"))
        
        # Appel à l'extraction
        result = self._extract_from_image(self.image)
        
        if result.get('success'):
            self._process_extraction_result(result.get('data', {}))
            self.state = 'extracted'
        else:
            self.write({
                'state': 'error',
                'error_message': result.get('error', 'Erreur inconnue'),
            })
        
        return True
    
    def _extract_from_image(self, image_base64):
        """
        Extrait les informations produit d'une image via Claude API.
        Gère les produits simples, les variantes et les spécifications techniques.
        """
        # Récupérer la clé API
        api_key = self.env['ir.config_parameter'].sudo().get_param('pool.claude_api_key')
        
        if not api_key:
            _logger.warning("Claude API key not configured")
            return {
                'success': False,
                'error': "Clé API Claude non configurée. Allez dans Configuration > Paramètres > Pool Import.",
            }
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            }
            
            # Prompt amélioré pour extraire les variantes et spécifications
            prompt = """Analyse cette image d'un catalogue de produits de piscine.

IMPORTANT: Détecte s'il s'agit d'un produit unique, d'un produit avec variantes (comme un tableau avec différentes capacités/tailles/prix), ou de plusieurs produits distincts.

Extrais les informations au format JSON suivant:

{
    "extraction_type": "single" | "variants" | "multiple",
    "base_product": {
        "name": "nom du produit principal",
        "brand": "marque",
        "category": "catégorie (Pompes à chaleur, Filtration, Robots, Pompes, Éclairage, etc.)",
        "description_fr": "description détaillée en français"
    },
    "specifications": {
        "power_kw": null,
        "power_cv": null,
        "voltage": null,
        "flow_rate_m3h": null,
        "diameter_mm": null,
        "filter_area_m2": null,
        "cop": null,
        "noise_level_db": null,
        "capacity": null,
        "dimensions": null,
        "weight_kg": null,
        "warranty_years": null
    },
    "products": [
        {
            "type_code": "code type/modèle (ex: ASRC120)",
            "reference": "référence fournisseur (ex: SC941)",
            "variant_name": "nom de la variante si applicable",
            "capacity": "capacité si applicable (ex: 12 kW)",
            "purchase_price": 0,
            "selling_price": 0,
            "specifications": {
                "power_kw": null
            }
        }
    ]
}

Notes:
- Pour un tableau de variantes, crée un objet dans "products" pour chaque ligne
- Les prix doivent être des nombres (pas de symboles € ou espaces)
- "extraction_type" = "variants" si tu vois un tableau avec le même produit en différentes tailles/capacités
- Les spécifications peuvent être au niveau du produit de base ET/OU de chaque variante
- Si tu ne trouves pas une information, utilise null

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire ni backticks."""

            # Décoder si nécessaire
            if isinstance(image_base64, bytes):
                image_data = image_base64.decode('utf-8')
            else:
                image_data = image_base64
            
            payload = {
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 2048,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'image/png',
                                    'data': image_data,
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
                timeout=60,
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('content', [{}])[0].get('text', '{}')
                
                # Nettoyer et parser le JSON
                content = content.strip()
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:]
                content = content.strip()
                
                try:
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
    
    def _process_extraction_result(self, data):
        """Traite le résultat de l'extraction et crée les enregistrements"""
        self.ensure_one()
        
        # Sauvegarder les données brutes
        self.raw_extraction_data = json.dumps(data, indent=2, ensure_ascii=False)
        
        # Déterminer le type d'extraction
        extraction_type = data.get('extraction_type', 'single')
        self.extraction_type = extraction_type
        
        # Supprimer les anciens produits extraits
        self.extracted_product_ids.unlink()
        
        # Informations de base du produit
        base_product = data.get('base_product', {})
        base_specs = data.get('specifications', {})
        
        # Créer les produits extraits
        products_data = data.get('products', [])
        
        if not products_data:
            # Si pas de produits dans la liste, créer un produit simple
            products_data = [{
                'reference': base_product.get('reference', ''),
                'type_code': '',
                'variant_name': '',
                'selling_price': 0,
                'purchase_price': 0,
                'specifications': base_specs,
            }]
        
        for idx, prod in enumerate(products_data):
            # Fusionner les spécifications
            prod_specs = {**base_specs, **(prod.get('specifications', {}) or {})}
            
            # Construire le nom complet
            full_name = base_product.get('name', '')
            if prod.get('variant_name'):
                full_name = f"{full_name} - {prod.get('variant_name')}"
            elif prod.get('capacity'):
                full_name = f"{full_name} - {prod.get('capacity')}"
            elif prod.get('type_code'):
                full_name = f"{full_name} ({prod.get('type_code')})"
            
            self.env['pool.catalog.extraction.product'].create({
                'extraction_id': self.id,
                'sequence': idx,
                'name': full_name.strip() or f"Produit {idx + 1}",
                'type_code': prod.get('type_code', ''),
                'reference': prod.get('reference', ''),
                'brand': base_product.get('brand', ''),
                'category': base_product.get('category', ''),
                'variant_name': prod.get('variant_name', ''),
                'capacity': prod.get('capacity', ''),
                'description_fr': base_product.get('description_fr', ''),
                'purchase_price': self._parse_price(prod.get('purchase_price')),
                'selling_price': self._parse_price(prod.get('selling_price')),
                # Spécifications techniques
                'power_kw': prod_specs.get('power_kw'),
                'power_cv': prod_specs.get('power_cv'),
                'voltage': prod_specs.get('voltage'),
                'flow_rate': prod_specs.get('flow_rate_m3h'),
                'diameter_mm': prod_specs.get('diameter_mm'),
                'filter_area': prod_specs.get('filter_area_m2'),
                'cop': prod_specs.get('cop'),
                'noise_level': prod_specs.get('noise_level_db'),
                'capacity_spec': prod_specs.get('capacity'),
                'dimensions': prod_specs.get('dimensions'),
                'weight': prod_specs.get('weight_kg'),
                'warranty_years': prod_specs.get('warranty_years'),
            })
        
        # Reset l'index courant
        self.current_product_index = 0
    
    def _parse_price(self, value):
        """Parse un prix en float, gère différents formats"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Nettoyer le string
            cleaned = re.sub(r'[^\d.,]', '', value)
            cleaned = cleaned.replace(',', '.')
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        return 0.0
    
    def action_previous_product(self):
        """Navigue vers le produit précédent"""
        self.ensure_one()
        if self.current_product_index > 0:
            self.current_product_index -= 1
    
    def action_next_product(self):
        """Navigue vers le produit suivant"""
        self.ensure_one()
        if self.current_product_index < len(self.extracted_product_ids) - 1:
            self.current_product_index += 1
    
    def action_import_current(self):
        """Importe le produit courant dans Odoo"""
        self.ensure_one()
        
        if not self.extracted_product_ids:
            raise UserError(_("Aucun produit à importer"))
        
        # Trouver le produit courant
        current_product = self.extracted_product_ids.filtered(
            lambda p: p.sequence == self.current_product_index
        )
        
        if not current_product:
            current_product = self.extracted_product_ids[0]
        
        return current_product.action_import_to_odoo()
    
    def action_import_all(self):
        """Importe tous les produits extraits"""
        self.ensure_one()
        
        products_to_import = self.extracted_product_ids.filtered(
            lambda p: p.state == 'draft'
        )
        
        if not products_to_import:
            raise UserError(_("Aucun produit à importer"))
        
        imported = 0
        errors = []
        
        for product in products_to_import:
            try:
                product.action_import_to_odoo()
                imported += 1
            except Exception as e:
                errors.append(f"{product.name}: {str(e)}")
        
        # Mettre à jour l'état
        if not self.extracted_product_ids.filtered(lambda p: p.state == 'draft'):
            self.state = 'imported'
        
        # Notification
        message = f"{imported} produit(s) importé(s)"
        if errors:
            message += f"\n{len(errors)} erreur(s):\n" + "\n".join(errors[:5])
            msg_type = 'warning'
        else:
            msg_type = 'success'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': message,
                'type': msg_type,
                'sticky': bool(errors),
            }
        }
    
    def action_re_extract(self):
        """Relance l'extraction"""
        self.ensure_one()
        self.error_message = False
        return self.action_extract()
    
    @api.model
    def create_from_upload(self, image_base64, supplier_id=None, auto_extract=True):
        """
        Crée une extraction depuis une image uploadée.
        Utilisé par le composant JavaScript.
        
        :return: ID de l'extraction créée (int)
        """
        vals = {
            'image': image_base64,
            'supplier_id': supplier_id,
        }
        
        extraction = self.create(vals)
        
        if auto_extract:
            extraction.action_extract()
        
        # Retourner l'ID (pas le recordset) pour le JavaScript
        return extraction.id


class PoolCatalogExtractionProduct(models.Model):
    """
    Produit extrait d'une capture d'écran.
    Peut représenter un produit simple ou une variante.
    """
    _name = 'pool.catalog.extraction.product'
    _description = 'Produit extrait'
    _order = 'extraction_id, sequence'

    extraction_id = fields.Many2one(
        'pool.catalog.extraction',
        string='Extraction',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Séquence', default=10)
    
    # Informations produit
    name = fields.Char(string='Nom', required=True)
    type_code = fields.Char(string='Code Type', help="Ex: ASRC120, ASRC150")
    reference = fields.Char(string='Référence', help="Référence fournisseur")
    brand = fields.Char(string='Marque')
    category = fields.Char(string='Catégorie')
    variant_name = fields.Char(string='Nom variante')
    capacity = fields.Char(string='Capacité', help="Ex: 12 kW, 15 m³/h")
    
    description_fr = fields.Text(string='Description FR')
    description_nl = fields.Text(string='Description NL')
    
    # Prix
    purchase_price = fields.Float(string='Prix d\'achat HT')
    selling_price = fields.Float(string='Prix de vente HT')
    margin = fields.Float(string='Marge %', compute='_compute_margin')
    
    # Spécifications techniques
    power_kw = fields.Float(string='Puissance (kW)')
    power_cv = fields.Char(string='Puissance (CV)')
    voltage = fields.Integer(string='Tension (V)')
    flow_rate = fields.Float(string='Débit (m³/h)')
    diameter_mm = fields.Integer(string='Diamètre (mm)')
    filter_area = fields.Float(string='Surface filtrante (m²)')
    cop = fields.Float(string='COP')
    noise_level = fields.Float(string='Niveau sonore (dB)')
    capacity_spec = fields.Char(string='Capacité (spec)')
    dimensions = fields.Char(string='Dimensions')
    weight = fields.Float(string='Poids (kg)')
    warranty_years = fields.Integer(string='Garantie (années)')
    
    # État
    state = fields.Selection([
        ('draft', 'À importer'),
        ('imported', 'Importé'),
        ('skipped', 'Ignoré'),
        ('error', 'Erreur'),
    ], string='État', default='draft')
    
    # Lien avec le produit Odoo créé
    product_id = fields.Many2one(
        'product.template',
        string='Produit Odoo',
        ondelete='set null'
    )
    existing_product_id = fields.Many2one(
        'product.template',
        string='Produit existant',
        compute='_compute_existing_product'
    )
    
    error_message = fields.Text(string='Erreur')
    
    @api.depends('purchase_price', 'selling_price')
    def _compute_margin(self):
        for rec in self:
            if rec.selling_price > 0:
                rec.margin = ((rec.selling_price - rec.purchase_price) / rec.selling_price) * 100
            else:
                rec.margin = 0
    
    @api.depends('reference', 'type_code')
    def _compute_existing_product(self):
        for rec in self:
            existing = False
            if rec.reference:
                existing = self.env['product.template'].search([
                    ('x_pool_supplier_ref', '=', rec.reference)
                ], limit=1)
            if not existing and rec.type_code:
                existing = self.env['product.template'].search([
                    '|',
                    ('x_pool_supplier_ref', '=', rec.type_code),
                    ('default_code', 'ilike', rec.type_code),
                ], limit=1)
            rec.existing_product_id = existing.id if existing else False
    
    def action_import_to_odoo(self):
        """Importe ce produit dans Odoo"""
        self.ensure_one()
        
        _logger.info(f"=== Début import produit OCR ID={self.id}, nom={self.name} ===")
        
        supplier = self.extraction_id.supplier_id
        ProductTemplate = self.env['product.template']
        
        # Préparer les valeurs de base (champs standard Odoo uniquement)
        ref_code = self.reference or self.type_code or str(self.id)
        
        vals = {
            'name': self.name or 'Produit sans nom',
            'default_code': f"POOL-{ref_code}",
            'description_sale': self.description_fr or '',
            'standard_price': float(self.purchase_price or 0),
            'list_price': float(self.selling_price or 0),
            'sale_ok': True,
            'purchase_ok': True,
        }
        
        _logger.info(f"Valeurs de base: {vals}")
        
        # Déterminer le bon champ pour le type de produit (varie selon version Odoo)
        if 'detailed_type' in ProductTemplate._fields:
            vals['detailed_type'] = 'product'
            _logger.info("Utilisation de detailed_type=product")
        elif 'type' in ProductTemplate._fields:
            vals['type'] = 'product'
            _logger.info("Utilisation de type=product")
        
        # Ajouter les champs personnalisés UN PAR UN s'ils existent
        custom_fields_mapping = [
            ('x_pool_supplier_ref', ref_code),
            ('x_pool_brand', self.brand or ''),
            ('x_pool_category', self.category or ''),
            ('x_description_fr', self.description_fr or ''),
            ('x_description_nl', self.description_nl or ''),
            ('x_pool_import_source', f'Extraction OCR {self.extraction_id.id}'),
        ]
        
        for field_name, field_value in custom_fields_mapping:
            if field_name in ProductTemplate._fields:
                vals[field_name] = field_value
                _logger.debug(f"Ajout champ {field_name}={field_value}")
        
        # Champs numériques personnalisés
        numeric_fields = [
            ('x_power_kw', self.power_kw),
            ('x_flow_rate', self.flow_rate),
            ('x_filter_area', self.filter_area),
            ('x_cop', self.cop),
            ('x_noise_level', self.noise_level),
        ]
        
        for field_name, field_value in numeric_fields:
            if field_name in ProductTemplate._fields and field_value:
                vals[field_name] = float(field_value)
        
        # Champs entiers personnalisés
        int_fields = [
            ('x_voltage', self.voltage),
            ('x_diameter_mm', self.diameter_mm),
        ]
        
        for field_name, field_value in int_fields:
            if field_name in ProductTemplate._fields and field_value:
                vals[field_name] = int(field_value)
        
        # Date d'import
        if 'x_pool_import_date' in ProductTemplate._fields:
            vals['x_pool_import_date'] = fields.Datetime.now()
        
        # Fournisseur
        if supplier and 'x_pool_supplier_id' in ProductTemplate._fields:
            vals['x_pool_supplier_id'] = supplier.id
            _logger.info(f"Fournisseur: {supplier.name}")
        
        # Catégorie
        if self.category:
            category = self.env['product.category'].search([
                ('name', 'ilike', self.category)
            ], limit=1)
            if category:
                vals['categ_id'] = category.id
                _logger.info(f"Catégorie trouvée: {category.name}")
        
        _logger.info(f"Valeurs finales pour création: {list(vals.keys())}")
        
        try:
            if self.existing_product_id:
                _logger.info(f"Mise à jour produit existant ID={self.existing_product_id.id}")
                self.existing_product_id.write(vals)
                product = self.existing_product_id
            else:
                _logger.info("Création nouveau produit...")
                product = ProductTemplate.create(vals)
                _logger.info(f"Produit créé avec ID={product.id}")
            
            self.write({
                'state': 'imported',
                'product_id': product.id,
                'error_message': False,
            })
            
            _logger.info(f"=== Import réussi pour {product.name} (ID={product.id}) ===")
            return True
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"=== ERREUR import produit: {error_msg} ===")
            _logger.exception("Traceback complet:")
            self.write({
                'state': 'error',
                'error_message': error_msg,
            })
            # Ne pas lever d'exception pour éviter l'erreur serveur côté client
            return False
    
    def action_skip(self):
        """Marque le produit comme ignoré"""
        self.write({'state': 'skipped'})
    
    def action_reset(self):
        """Remet le produit à l'état draft"""
        self.write({
            'state': 'draft',
            'error_message': False,
        })
    
    def action_view_product(self):
        """Ouvre le produit Odoo lié"""
        self.ensure_one()
        product = self.product_id or self.existing_product_id
        if product:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'res_id': product.id,
                'view_mode': 'form',
                'target': 'current',
            }
