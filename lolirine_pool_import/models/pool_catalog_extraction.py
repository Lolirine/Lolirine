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
    
    # Attributs informatifs du produit de base
    refrigerant_gas = fields.Char(string='Gaz réfrigérant')
    power_supply = fields.Char(string='Alimentation')
    pool_volume_range = fields.Char(string='Volume piscine conseillé')
    operating_temp_range = fields.Char(string='Température fonctionnement')
    water_connection = fields.Char(string='Connexion eau')
    energy_class = fields.Char(string='Classe énergétique')
    product_type_tech = fields.Char(string='Type technologie')
    installation_type = fields.Char(string='Type installation')
    wifi_compatible = fields.Boolean(string='Compatible WiFi', default=False)
    
    # Image produit extraite
    extracted_product_image = fields.Binary(string='Image produit extraite', attachment=True)
    product_image_detected = fields.Boolean(string='Image détectée', default=False)
    product_image_position = fields.Char(string='Position image')
    
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
            
            # Prompt amélioré pour extraire les variantes, spécifications et attributs informatifs
            prompt = """Analyse cette image d'un catalogue de produits de piscine.

IMPORTANT: Détecte s'il s'agit d'un produit unique, d'un produit avec variantes (comme un tableau avec différentes capacités/tailles/prix), ou de plusieurs produits distincts.

Extrais les informations au format JSON suivant:

{
    "extraction_type": "single" | "variants" | "multiple",
    "base_product": {
        "name": "nom du produit principal (sans la capacité/variante)",
        "brand": "marque",
        "category": "catégorie (Pompes à chaleur, Filtration, Robots, Pompes, Éclairage, Traitement eau, etc.)",
        "description_fr": "description détaillée en français basée sur le texte visible"
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
    "informative_attributes": {
        "refrigerant_gas": "gaz réfrigérant si mentionné (R290, R32, R410A, etc.)",
        "power_supply": "alimentation électrique (ex: 230V/1Ph/50Hz, 380V/3Ph)",
        "pool_volume_min": "volume piscine minimum conseillé en m³ (nombre uniquement)",
        "pool_volume_max": "volume piscine maximum conseillé en m³ (nombre uniquement)",
        "operating_temp_min": "température fonctionnement minimum en °C (nombre uniquement)",
        "operating_temp_max": "température fonctionnement maximum en °C (nombre uniquement)",
        "water_connection": "diamètre connexion eau (ex: 50mm, 63mm)",
        "energy_class": "classe énergétique si mentionnée (A, A+, A++, etc.)",
        "product_type": "type de technologie (Inverter, Full Inverter, On/Off, Turbo, etc.)",
        "installation_type": "type d'installation (Intérieur, Extérieur, Les deux)",
        "wifi_compatible": true/false si mentionné,
        "heating_capacity_min": "capacité chauffage min en kW",
        "heating_capacity_max": "capacité chauffage max en kW",
        "cooling_capacity": "capacité refroidissement en kW si applicable"
    },
    "product_image": {
        "detected": true/false,
        "position": "description de la position de l'image produit (ex: 'coin inférieur gauche', 'centre gauche')",
        "description": "description courte de l'image du produit visible"
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
                "power_kw": null,
                "cop": null,
                "noise_level_db": null,
                "pool_volume_min": null,
                "pool_volume_max": null
            }
        }
    ]
}

Notes:
- Pour un tableau de variantes, crée un objet dans "products" pour chaque ligne du tableau
- Les prix doivent être des nombres (pas de symboles € ou espaces)
- "extraction_type" = "variants" si tu vois un tableau avec le même produit en différentes tailles/capacités
- Les spécifications peuvent être au niveau du produit de base ET/OU de chaque variante
- Si tu ne trouves pas une information, utilise null
- Pour "informative_attributes", extrait toutes les caractéristiques techniques générales du produit
- Pour "product_image", indique si tu vois une image/photo du produit et où elle se trouve

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
        info_attrs = data.get('informative_attributes', {})
        product_image_info = data.get('product_image', {})
        
        # Stocker les attributs informatifs au niveau de l'extraction
        self._process_informative_attributes(info_attrs)
        
        # Stocker les informations sur l'image produit
        if product_image_info.get('detected'):
            self.product_image_detected = True
            self.product_image_position = product_image_info.get('position', '')
            _logger.info(f"Image produit détectée: {product_image_info.get('description', '')}")
        
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
            
            # Préparer les valeurs en gérant les null/None
            vals = {
                'extraction_id': self.id,
                'sequence': idx,
                'name': full_name.strip() or f"Produit {idx + 1}",
                'type_code': prod.get('type_code') or '',
                'reference': prod.get('reference') or '',
                'brand': base_product.get('brand') or '',
                'category': base_product.get('category') or '',
                'variant_name': prod.get('variant_name') or '',
                'capacity': prod.get('capacity') or '',
                'description_fr': base_product.get('description_fr') or '',
                'purchase_price': self._parse_price(prod.get('purchase_price')),
                'selling_price': self._parse_price(prod.get('selling_price')),
            }
            
            # Ajouter les spécifications Float (peuvent être 0.0 si null)
            float_specs = [
                ('power_kw', 'power_kw'),
                ('flow_rate', 'flow_rate_m3h'),
                ('filter_area', 'filter_area_m2'),
                ('cop', 'cop'),
                ('noise_level', 'noise_level_db'),
                ('weight', 'weight_kg'),
                ('heating_capacity_min', 'heating_capacity_min'),
                ('heating_capacity_max', 'heating_capacity_max'),
                ('cooling_capacity', 'cooling_capacity'),
            ]
            for field_name, spec_key in float_specs:
                value = prod_specs.get(spec_key)
                if value is not None:
                    try:
                        vals[field_name] = float(value)
                    except (ValueError, TypeError):
                        vals[field_name] = 0.0
            
            # Ajouter les spécifications Integer (peuvent être 0 si null)
            int_specs = [
                ('voltage', 'voltage'),
                ('diameter_mm', 'diameter_mm'),
                ('warranty_years', 'warranty_years'),
                ('pool_volume_min', 'pool_volume_min'),
                ('pool_volume_max', 'pool_volume_max'),
                ('operating_temp_min', 'operating_temp_min'),
                ('operating_temp_max', 'operating_temp_max'),
            ]
            for field_name, spec_key in int_specs:
                value = prod_specs.get(spec_key)
                if value is not None:
                    try:
                        vals[field_name] = int(value)
                    except (ValueError, TypeError):
                        vals[field_name] = 0
            
            # Ajouter les spécifications Char
            if prod_specs.get('power_cv'):
                vals['power_cv'] = str(prod_specs.get('power_cv'))
            if prod_specs.get('capacity'):
                vals['capacity_spec'] = str(prod_specs.get('capacity'))
            if prod_specs.get('dimensions'):
                vals['dimensions'] = str(prod_specs.get('dimensions'))
            
            # Ajouter les attributs informatifs au produit
            vals.update(self._get_product_informative_attrs(info_attrs))
            
            _logger.info(f"Création produit extrait {idx}: {vals.get('name')}")
            self.env['pool.catalog.extraction.product'].create(vals)
        
        # Reset l'index courant
        self.current_product_index = 0
        
        # Lancer l'extraction d'image si détectée
        if self.product_image_detected:
            self._extract_product_image()
    
    def _process_informative_attributes(self, info_attrs):
        """Stocke les attributs informatifs au niveau de l'extraction"""
        if not info_attrs:
            return
        
        # Gaz réfrigérant
        if info_attrs.get('refrigerant_gas'):
            self.refrigerant_gas = info_attrs.get('refrigerant_gas')
        
        # Alimentation
        if info_attrs.get('power_supply'):
            self.power_supply = info_attrs.get('power_supply')
        
        # Volume piscine
        vol_min = info_attrs.get('pool_volume_min')
        vol_max = info_attrs.get('pool_volume_max')
        if vol_min or vol_max:
            self.pool_volume_range = f"{vol_min or '?'} - {vol_max or '?'} m³"
        
        # Température fonctionnement
        temp_min = info_attrs.get('operating_temp_min')
        temp_max = info_attrs.get('operating_temp_max')
        if temp_min is not None or temp_max is not None:
            self.operating_temp_range = f"{temp_min or '?'}°C à {temp_max or '?'}°C"
        
        # Autres attributs
        if info_attrs.get('water_connection'):
            self.water_connection = info_attrs.get('water_connection')
        if info_attrs.get('energy_class'):
            self.energy_class = info_attrs.get('energy_class')
        if info_attrs.get('product_type'):
            self.product_type_tech = info_attrs.get('product_type')
        if info_attrs.get('installation_type'):
            self.installation_type = info_attrs.get('installation_type')
        if info_attrs.get('wifi_compatible'):
            self.wifi_compatible = bool(info_attrs.get('wifi_compatible'))
    
    def _get_product_informative_attrs(self, info_attrs):
        """Retourne les attributs informatifs pour un produit extrait"""
        if not info_attrs:
            return {}
        
        vals = {}
        
        # Copier les attributs string directement
        str_attrs = [
            'refrigerant_gas', 'power_supply', 'water_connection',
            'energy_class', 'product_type', 'installation_type'
        ]
        for attr in str_attrs:
            if info_attrs.get(attr):
                vals[attr] = str(info_attrs.get(attr))
        
        # Attributs entiers
        int_attrs = [
            'pool_volume_min', 'pool_volume_max',
            'operating_temp_min', 'operating_temp_max'
        ]
        for attr in int_attrs:
            if info_attrs.get(attr) is not None:
                try:
                    vals[attr] = int(info_attrs.get(attr))
                except (ValueError, TypeError):
                    pass
        
        # Attributs float
        float_attrs = [
            'heating_capacity_min', 'heating_capacity_max', 'cooling_capacity'
        ]
        for attr in float_attrs:
            if info_attrs.get(attr) is not None:
                try:
                    vals[attr] = float(info_attrs.get(attr))
                except (ValueError, TypeError):
                    pass
        
        # WiFi
        if info_attrs.get('wifi_compatible') is not None:
            vals['wifi_compatible'] = bool(info_attrs.get('wifi_compatible'))
        
        return vals
    
    def _extract_product_image(self):
        """Extrait l'image du produit depuis la capture d'écran du catalogue"""
        self.ensure_one()
        
        if not self.image or not self.product_image_detected:
            return
        
        _logger.info("Tentative d'extraction de l'image produit...")
        
        # Récupérer la clé API
        api_key = self.env['ir.config_parameter'].sudo().get_param('pool.claude_api_key')
        if not api_key:
            _logger.warning("Clé API Claude non configurée pour extraction d'image")
            return
        
        try:
            # Décoder l'image source
            if isinstance(self.image, bytes):
                image_data = self.image.decode('utf-8')
            else:
                image_data = self.image
            
            # Demander à Claude d'identifier précisément la zone de l'image produit
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            }
            
            prompt = """Analyse cette image de catalogue. Une image du produit est visible.

Je veux extraire uniquement l'image/photo du produit (pas le texte, pas les tableaux).

Décris précisément les coordonnées de la zone contenant l'image du produit:
- Position approximative en pourcentage depuis le coin supérieur gauche
- Largeur et hauteur approximatives en pourcentage de l'image totale

Réponds au format JSON:
{
    "product_image_zone": {
        "x_percent": 0-100,
        "y_percent": 0-100,
        "width_percent": 0-100,
        "height_percent": 0-100
    },
    "description": "description de l'image du produit"
}

Réponds UNIQUEMENT avec le JSON."""

            payload = {
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 500,
                'messages': [{
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
                        {'type': 'text', 'text': prompt},
                    ],
                }],
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
                content = content.strip()
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:]
                content = content.strip()
                
                zone_data = json.loads(content)
                zone = zone_data.get('product_image_zone', {})
                
                if zone:
                    # Extraire la zone de l'image avec PIL
                    self._crop_product_image(zone)
                    _logger.info(f"Image produit extraite: {zone_data.get('description', '')}")
            else:
                _logger.error(f"Erreur API Claude pour extraction image: {response.status_code}")
                
        except Exception as e:
            _logger.error(f"Erreur lors de l'extraction d'image: {str(e)}")
    
    def _crop_product_image(self, zone):
        """Découpe l'image du produit depuis le catalogue"""
        try:
            from PIL import Image
            import io
            
            # Décoder l'image source
            image_bytes = base64.b64decode(self.image)
            img = Image.open(io.BytesIO(image_bytes))
            
            # Calculer les coordonnées de découpe
            width, height = img.size
            x = int(width * zone.get('x_percent', 0) / 100)
            y = int(height * zone.get('y_percent', 0) / 100)
            w = int(width * zone.get('width_percent', 30) / 100)
            h = int(height * zone.get('height_percent', 30) / 100)
            
            # Découper
            cropped = img.crop((x, y, x + w, y + h))
            
            # Sauvegarder en PNG
            output = io.BytesIO()
            cropped.save(output, format='PNG')
            output.seek(0)
            
            # Stocker l'image extraite
            self.extracted_product_image = base64.b64encode(output.getvalue())
            _logger.info(f"Image produit découpée: {w}x{h}px")
            
        except ImportError:
            _logger.warning("PIL non disponible pour découpe d'image")
        except Exception as e:
            _logger.error(f"Erreur découpe image: {str(e)}")
    
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
        
        # Si c'est une extraction de type "variants", créer un seul produit avec variantes
        if self.extraction_type == 'variants' and len(products_to_import) > 1:
            return self._import_as_single_product_with_variants(products_to_import)
        
        # Sinon, import individuel classique
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
    
    def _import_as_single_product_with_variants(self, products_to_import):
        """
        Importe plusieurs produits extraits comme UN SEUL product.template avec variantes.
        Utilisé quand extraction_type == 'variants'.
        """
        self.ensure_one()
        _logger.info(f"=== Import avec variantes: {len(products_to_import)} variantes ===")
        
        ProductTemplate = self.env['product.template']
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        
        # Déterminer l'attribut principal (Capacité, Taille, etc.)
        # On essaie de détecter automatiquement
        attribute_name = self._detect_variant_attribute(products_to_import)
        _logger.info(f"Attribut détecté: {attribute_name}")
        
        # Créer ou récupérer l'attribut
        attribute = ProductAttribute.search([('name', '=', attribute_name)], limit=1)
        if not attribute:
            attribute = ProductAttribute.create({
                'name': attribute_name,
                'display_type': 'radio',
                'create_variant': 'always',
            })
            _logger.info(f"Attribut créé: {attribute.name} (ID: {attribute.id})")
        
        # Préparer les valeurs d'attribut et collecter les données de chaque variante
        attribute_values = []
        variant_data = {}  # {value_name: product_data}
        
        for prod in products_to_import:
            # Déterminer le nom de la valeur d'attribut
            value_name = prod.capacity or prod.variant_name or prod.type_code or f"Variante {prod.sequence + 1}"
            
            # Créer ou récupérer la valeur d'attribut
            attr_value = ProductAttributeValue.search([
                ('attribute_id', '=', attribute.id),
                ('name', '=', value_name)
            ], limit=1)
            
            if not attr_value:
                attr_value = ProductAttributeValue.create({
                    'attribute_id': attribute.id,
                    'name': value_name,
                })
                _logger.info(f"Valeur d'attribut créée: {attr_value.name}")
            
            attribute_values.append(attr_value.id)
            variant_data[value_name] = {
                'extracted_product': prod,
                'attribute_value_id': attr_value.id,
                'purchase_price': prod.purchase_price or 0,
                'selling_price': prod.selling_price or 0,
                'reference': prod.reference or prod.type_code,
            }
        
        # Récupérer le nom de base depuis les données d'extraction brutes
        base_name = None
        base_product = products_to_import[0]
        
        # Essayer d'abord depuis raw_extraction_data
        if self.raw_extraction_data:
            try:
                raw_data = json.loads(self.raw_extraction_data)
                base_name = raw_data.get('base_product', {}).get('name', '')
                _logger.info(f"Nom de base depuis raw_data: {base_name}")
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Si pas de nom de base, nettoyer le nom du premier produit
        if not base_name:
            base_name = base_product.name
            # Enlever la partie variante du nom si présente
            for suffix in [base_product.capacity, base_product.variant_name, base_product.type_code]:
                if suffix and suffix in base_name:
                    patterns_to_remove = [
                        f" - {suffix}",
                        f" ({suffix})",
                        f"- {suffix}",
                        f"({suffix})",
                        f" {suffix}",
                    ]
                    for pattern in patterns_to_remove:
                        if pattern in base_name:
                            base_name = base_name.replace(pattern, "")
            base_name = ' '.join(base_name.split()).strip()
        
        _logger.info(f"Nom du template final: {base_name}")
        
        # Préparer les valeurs du template
        ref_code = base_product.reference or base_product.type_code or str(self.id)
        
        vals = {
            'name': base_name or 'Produit avec variantes',
            'default_code': f"POOL-{ref_code}",
            'description_sale': base_product.description_fr or '',
            'sale_ok': True,
            'purchase_ok': True,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute_values)],
            })],
        }
        
        # Ajouter la description pour le site web e-commerce
        if 'website_description' in ProductTemplate._fields and base_product.description_fr:
            description_html = base_product._format_website_description()
            vals['website_description'] = description_html
            _logger.info("Description website ajoutée (variantes)")
        
        # Marquer comme produit piscine (pour le multi-site)
        if 'is_pool_product' in ProductTemplate._fields:
            vals['is_pool_product'] = True
        
        # =============================================
        # PUBLICATION E-COMMERCE - VARIANTES
        # =============================================
        
        # Publier le produit sur le site e-commerce
        if 'is_published' in ProductTemplate._fields:
            vals['is_published'] = True
            _logger.info("Produit (variantes) marqué comme publié")
        
        # Assigner au website Pool Store
        pool_website = base_product._get_pool_store_website()
        if pool_website and 'website_id' in ProductTemplate._fields:
            vals['website_id'] = pool_website.id
            _logger.info(f"Produit (variantes) assigné au website: {pool_website.name}")
        
        # Assigner aux catégories e-commerce publiques
        public_categ_ids = base_product._get_public_category_ids(base_product.category)
        if public_categ_ids and 'public_categ_ids' in ProductTemplate._fields:
            vals['public_categ_ids'] = [(6, 0, public_categ_ids)]
            _logger.info(f"Catégories e-commerce (variantes): {public_categ_ids}")
        
        # =============================================
        
        # Déterminer le type de produit
        product_type = 'consu'
        if 'detailed_type' in ProductTemplate._fields:
            field_def = ProductTemplate._fields['detailed_type']
            if hasattr(field_def, 'selection'):
                selection = field_def.selection
                if callable(selection):
                    try:
                        selection = selection(ProductTemplate)
                    except:
                        selection = []
                valid_types = [s[0] for s in selection] if selection else []
                if 'product' in valid_types:
                    product_type = 'product'
            vals['detailed_type'] = product_type
        elif 'type' in ProductTemplate._fields:
            vals['type'] = product_type
        
        # Ajouter les champs personnalisés
        custom_fields = [
            ('x_pool_supplier_ref', ref_code),
            ('x_pool_brand', base_product.brand or ''),
            ('x_pool_category', base_product.category or ''),
            ('x_description_fr', base_product.description_fr or ''),
            ('x_pool_import_source', f'Extraction OCR {self.id} (variantes)'),
        ]
        
        for field_name, field_value in custom_fields:
            if field_name in ProductTemplate._fields:
                vals[field_name] = field_value
        
        # Fournisseur
        if self.supplier_id and 'x_pool_supplier_id' in ProductTemplate._fields:
            vals['x_pool_supplier_id'] = self.supplier_id.id
        
        # Catégorie
        if base_product.category:
            category = self.env['product.category'].search([
                ('name', 'ilike', base_product.category)
            ], limit=1)
            if category:
                vals['categ_id'] = category.id
        
        try:
            # Créer le template
            _logger.info(f"Création du template avec variantes...")
            template = ProductTemplate.create(vals)
            _logger.info(f"Template créé: {template.name} (ID: {template.id})")
            
            # Ajouter les attributs informatifs (depuis le premier produit)
            if products_to_import:
                products_to_import[0]._add_informative_attributes(template)
            
            # Ajouter l'image produit extraite
            if products_to_import:
                products_to_import[0]._add_product_image(template)
            
            # Mettre à jour les prix de chaque variante
            for variant in template.product_variant_ids:
                # Trouver la valeur d'attribut de cette variante
                ptav = variant.product_template_attribute_value_ids
                if ptav:
                    value_name = ptav[0].product_attribute_value_id.name
                    if value_name in variant_data:
                        data = variant_data[value_name]
                        variant.write({
                            'default_code': f"POOL-{data['reference']}" if data['reference'] else variant.default_code,
                            'standard_price': data['purchase_price'],
                            'lst_price': data['selling_price'],
                        })
                        _logger.info(f"Variante mise à jour: {variant.display_name}, prix: {data['selling_price']}")
                        
                        # Marquer le produit extrait comme importé
                        data['extracted_product'].write({
                            'state': 'imported',
                            'product_id': template.id,
                            'error_message': False,
                        })
            
            # Mettre à jour l'état de l'extraction
            self.state = 'imported'
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'res_id': template.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        except Exception as e:
            _logger.error(f"Erreur création variantes: {str(e)}")
            _logger.exception("Traceback:")
            for prod in products_to_import:
                prod.write({
                    'state': 'error',
                    'error_message': str(e),
                })
            raise UserError(_("Erreur lors de la création des variantes: %s") % str(e))
    
    def _detect_variant_attribute(self, products):
        """
        Détecte le nom de l'attribut principal pour les variantes.
        Analyse les produits extraits pour déterminer le type de variation.
        """
        # Analyser les données pour détecter le type de variation
        capacities = [p.capacity for p in products if p.capacity]
        variant_names = [p.variant_name for p in products if p.variant_name]
        
        # Si on a des capacités avec "kW", c'est probablement une puissance
        if capacities:
            if any('kw' in c.lower() for c in capacities):
                return "Puissance"
            if any('m³' in c.lower() or 'm3' in c.lower() for c in capacities):
                return "Débit"
            if any('mm' in c.lower() for c in capacities):
                return "Diamètre"
            if any('m²' in c.lower() or 'm2' in c.lower() for c in capacities):
                return "Surface"
            return "Capacité"
        
        if variant_names:
            return "Modèle"
        
        return "Variante"
    
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
        _logger.info("=== create_from_upload appelé ===")
        _logger.info(f"supplier_id reçu: {supplier_id}, type: {type(supplier_id)}")
        
        vals = {
            'image': image_base64,
        }
        
        # Gérer supplier_id qui peut être None, False, 0, ou un ID valide
        if supplier_id and isinstance(supplier_id, int) and supplier_id > 0:
            vals['supplier_id'] = supplier_id
        
        try:
            extraction = self.create(vals)
            _logger.info(f"Extraction créée avec ID: {extraction.id}")
            
            if auto_extract:
                _logger.info("Lancement auto_extract...")
                extraction.action_extract()
                _logger.info(f"Extraction terminée, état: {extraction.state}")
            
            return extraction.id
            
        except Exception as e:
            _logger.error(f"Erreur dans create_from_upload: {str(e)}")
            _logger.exception("Traceback:")
            raise


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
    
    # Attributs informatifs (non-variants, affichés sur site web)
    refrigerant_gas = fields.Char(string='Gaz réfrigérant', help="Ex: R290, R32, R410A")
    power_supply = fields.Char(string='Alimentation', help="Ex: 230V/1Ph/50Hz")
    pool_volume_min = fields.Integer(string='Volume piscine min (m³)')
    pool_volume_max = fields.Integer(string='Volume piscine max (m³)')
    operating_temp_min = fields.Integer(string='Temp. fonct. min (°C)')
    operating_temp_max = fields.Integer(string='Temp. fonct. max (°C)')
    water_connection = fields.Char(string='Connexion eau', help="Ex: 50mm, 63mm")
    energy_class = fields.Char(string='Classe énergétique', help="Ex: A, A+, A++")
    product_type = fields.Char(string='Type de produit', help="Ex: Inverter, Full Inverter")
    installation_type = fields.Char(string='Installation', help="Ex: Intérieur, Extérieur")
    wifi_compatible = fields.Boolean(string='Compatible WiFi', default=False)
    heating_capacity_min = fields.Float(string='Capacité chauffage min (kW)')
    heating_capacity_max = fields.Float(string='Capacité chauffage max (kW)')
    cooling_capacity = fields.Float(string='Capacité refroidissement (kW)')
    
    # Image produit extraite
    product_image = fields.Binary(string='Image produit', attachment=True)
    product_image_filename = fields.Char(string='Nom fichier image')
    
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
        
        # Ajouter la description pour le site web e-commerce
        if 'website_description' in ProductTemplate._fields and self.description_fr:
            # Formater la description en HTML pour le site web
            description_html = self._format_website_description()
            vals['website_description'] = description_html
            _logger.info("Description website ajoutée")
        
        # Marquer comme produit piscine (pour le multi-site)
        if 'is_pool_product' in ProductTemplate._fields:
            vals['is_pool_product'] = True
        
        # =============================================
        # PUBLICATION E-COMMERCE - NOUVEAU
        # =============================================
        
        # Publier le produit sur le site e-commerce
        if 'is_published' in ProductTemplate._fields:
            vals['is_published'] = True
            _logger.info("Produit marqué comme publié (is_published=True)")
        
        # Assigner au website Pool Store
        pool_website = self._get_pool_store_website()
        if pool_website and 'website_id' in ProductTemplate._fields:
            vals['website_id'] = pool_website.id
            _logger.info(f"Produit assigné au website: {pool_website.name} (ID: {pool_website.id})")
        
        # Assigner aux catégories e-commerce publiques
        public_categ_ids = self._get_public_category_ids(self.category)
        if public_categ_ids and 'public_categ_ids' in ProductTemplate._fields:
            vals['public_categ_ids'] = [(6, 0, public_categ_ids)]
            _logger.info(f"Catégories e-commerce assignées: {public_categ_ids}")
        
        # =============================================
        
        _logger.info(f"Valeurs de base: {vals}")
        
        # Déterminer le bon type de produit
        # 'product' (stockable) nécessite le module stock, sinon utiliser 'consu' (consommable)
        product_type = 'consu'  # Valeur par défaut sûre
        
        if 'detailed_type' in ProductTemplate._fields:
            # Vérifier si 'product' est disponible (module stock installé)
            field_def = ProductTemplate._fields['detailed_type']
            if hasattr(field_def, 'selection'):
                selection = field_def.selection
                if callable(selection):
                    try:
                        selection = selection(ProductTemplate)
                    except:
                        selection = []
                valid_types = [s[0] for s in selection] if selection else []
                if 'product' in valid_types:
                    product_type = 'product'
                    _logger.info("Module stock détecté, utilisation de detailed_type=product")
                else:
                    _logger.info(f"Types disponibles: {valid_types}, utilisation de detailed_type=consu")
            vals['detailed_type'] = product_type
        elif 'type' in ProductTemplate._fields:
            # Odoo < 15
            vals['type'] = product_type
            _logger.info(f"Utilisation de type={product_type}")
        
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
        
        # Ajouter les attributs si le produit a une capacité ou variante
        # (seulement pour les nouveaux produits, pas les mises à jour)
        if not self.existing_product_id and (self.capacity or self.variant_name):
            attribute_line = self._create_product_attribute()
            if attribute_line:
                vals['attribute_line_ids'] = [attribute_line]
                _logger.info(f"Attribut ajouté au produit")
        
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
            
            # Ajouter les attributs informatifs (non-variants)
            self._add_informative_attributes(product)
            
            # Ajouter l'image produit extraite
            self._add_product_image(product)
            
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
    
    def _add_informative_attributes(self, product):
        """Ajoute les attributs informatifs (non-variants) au produit"""
        self.ensure_one()
        
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        
        # Liste des attributs informatifs à créer
        informative_attrs = []
        
        # =============================================
        # SPÉCIFICATIONS TECHNIQUES
        # =============================================
        
        # Puissance kW
        if self.power_kw:
            informative_attrs.append(('Puissance', f"{self.power_kw} kW"))
        
        # Débit
        if self.flow_rate:
            informative_attrs.append(('Débit', f"{self.flow_rate} m³/h"))
        
        # Surface filtrante
        if self.filter_area:
            informative_attrs.append(('Surface filtrante', f"{self.filter_area} m²"))
        
        # Tension
        if self.voltage:
            informative_attrs.append(('Tension', f"{self.voltage} V"))
        
        # Diamètre
        if self.diameter_mm:
            informative_attrs.append(('Diamètre', f"{self.diameter_mm} mm"))
        
        # COP
        if self.cop:
            informative_attrs.append(('COP', str(self.cop)))
        
        # Niveau sonore
        if self.noise_level:
            informative_attrs.append(('Niveau sonore', f"{self.noise_level} dB(A)"))
        
        # =============================================
        # ATTRIBUTS INFORMATIFS ADDITIONNELS
        # =============================================
        
        # Gaz réfrigérant
        if self.refrigerant_gas:
            informative_attrs.append(('Gaz réfrigérant', self.refrigerant_gas))
        
        # Alimentation
        if self.power_supply:
            informative_attrs.append(('Alimentation', self.power_supply))
        
        # Volume piscine
        if self.pool_volume_min or self.pool_volume_max:
            vol_str = f"{self.pool_volume_min or '?'} - {self.pool_volume_max or '?'} m³"
            informative_attrs.append(('Volume piscine conseillé', vol_str))
        
        # Température fonctionnement
        if self.operating_temp_min is not None or self.operating_temp_max is not None:
            temp_str = f"{self.operating_temp_min or '?'}°C à {self.operating_temp_max or '?'}°C"
            informative_attrs.append(('Température fonctionnement', temp_str))
        
        # Connexion eau
        if self.water_connection:
            informative_attrs.append(('Connexion eau', self.water_connection))
        
        # Classe énergétique
        if self.energy_class:
            informative_attrs.append(('Classe énergétique', self.energy_class))
        
        # Type de produit
        if self.product_type:
            informative_attrs.append(('Technologie', self.product_type))
        
        # Installation
        if self.installation_type:
            informative_attrs.append(('Installation', self.installation_type))
        
        # WiFi
        if self.wifi_compatible:
            informative_attrs.append(('Connectivité', 'WiFi'))
        
        # Créer les attributs sur le produit
        for attr_name, attr_value in informative_attrs:
            try:
                # Chercher ou créer l'attribut
                attribute = ProductAttribute.search([('name', '=', attr_name)], limit=1)
                if not attribute:
                    attribute = ProductAttribute.create({
                        'name': attr_name,
                        'display_type': 'radio',
                        'create_variant': 'no_variant',  # Important: pas de variante
                    })
                    _logger.info(f"Attribut informatif créé: {attr_name}")
                
                # Chercher ou créer la valeur
                attr_val = ProductAttributeValue.search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=', attr_value)
                ], limit=1)
                
                if not attr_val:
                    attr_val = ProductAttributeValue.create({
                        'attribute_id': attribute.id,
                        'name': attr_value,
                    })
                
                # Vérifier si l'attribut est déjà sur le produit
                existing_line = product.attribute_line_ids.filtered(
                    lambda l: l.attribute_id.id == attribute.id
                )
                
                if not existing_line:
                    # Ajouter l'attribut au produit
                    product.write({
                        'attribute_line_ids': [(0, 0, {
                            'attribute_id': attribute.id,
                            'value_ids': [(6, 0, [attr_val.id])],
                        })]
                    })
                    _logger.info(f"Attribut ajouté au produit: {attr_name} = {attr_value}")
                
            except Exception as e:
                _logger.warning(f"Impossible d'ajouter l'attribut {attr_name}: {str(e)}")
    
    def _add_product_image(self, product):
        """Ajoute l'image produit extraite au produit Odoo"""
        self.ensure_one()
        
        # Essayer d'abord l'image extraite du produit
        image_data = self.product_image
        
        # Sinon, utiliser l'image extraite de l'extraction parent
        if not image_data and self.extraction_id.extracted_product_image:
            image_data = self.extraction_id.extracted_product_image
        
        if not image_data:
            return
        
        try:
            # Ajouter comme image principale si pas d'image
            if not product.image_1920:
                product.image_1920 = image_data
                _logger.info(f"Image principale ajoutée au produit {product.id}")
            else:
                # Ajouter comme image supplémentaire
                self.env['product.image'].create({
                    'product_tmpl_id': product.id,
                    'name': f"Image catalogue - {self.name}",
                    'image_1920': image_data,
                })
                _logger.info(f"Image supplémentaire ajoutée au produit {product.id}")
                
        except Exception as e:
            _logger.warning(f"Impossible d'ajouter l'image: {str(e)}")
    
    def _create_product_attribute(self):
        """
        Crée un attribut et une valeur pour ce produit.
        Retourne un tuple pour attribute_line_ids ou None.
        """
        self.ensure_one()
        
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        
        # Déterminer le nom de l'attribut et la valeur
        value_name = self.capacity or self.variant_name
        if not value_name:
            return None
        
        # Déterminer le type d'attribut
        attribute_name = "Capacité"  # Par défaut
        value_lower = value_name.lower()
        
        if 'kw' in value_lower or 'watt' in value_lower:
            attribute_name = "Puissance"
        elif 'm³' in value_lower or 'm3' in value_lower or 'l/h' in value_lower:
            attribute_name = "Débit"
        elif 'mm' in value_lower and 'diamètre' not in self.name.lower():
            attribute_name = "Diamètre"
        elif 'm²' in value_lower or 'm2' in value_lower:
            attribute_name = "Surface"
        elif self.variant_name and not self.capacity:
            attribute_name = "Modèle"
        
        _logger.info(f"Création attribut: {attribute_name} = {value_name}")
        
        # Créer ou récupérer l'attribut
        attribute = ProductAttribute.search([('name', '=', attribute_name)], limit=1)
        if not attribute:
            attribute = ProductAttribute.create({
                'name': attribute_name,
                'display_type': 'radio',
                'create_variant': 'always',
            })
            _logger.info(f"Attribut créé: {attribute.name} (ID: {attribute.id})")
        
        # Créer ou récupérer la valeur d'attribut
        attr_value = ProductAttributeValue.search([
            ('attribute_id', '=', attribute.id),
            ('name', '=', value_name)
        ], limit=1)
        
        if not attr_value:
            attr_value = ProductAttributeValue.create({
                'attribute_id': attribute.id,
                'name': value_name,
            })
            _logger.info(f"Valeur d'attribut créée: {attr_value.name}")
        
        # Retourner le tuple pour attribute_line_ids
        return (0, 0, {
            'attribute_id': attribute.id,
            'value_ids': [(6, 0, [attr_value.id])],
        })
    
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
    
    # ==================== Image Search Methods ====================
    
    def action_search_images(self):
        """
        Recherche des images du produit via Google Custom Search API.
        Appelé depuis le frontend JavaScript.
        Retourne une liste d'URLs d'images.
        """
        self.ensure_one()
        
        # Récupérer les clés API
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('pool.google_api_key')
        search_engine_id = ICP.get_param('pool.google_search_engine_id')
        
        if not api_key or not search_engine_id:
            return {
                'success': False,
                'error': "API Google non configurée. Allez dans Configuration > Paramètres > Piscine.",
            }
        
        # Construire la requête de recherche
        search_query = self._build_image_search_query()
        _logger.info(f"Recherche d'images Google: {search_query}")
        
        try:
            # Appeler l'API Google Custom Search
            import urllib.parse
            
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': search_query,
                'searchType': 'image',
                'num': 10,  # Nombre d'images à retourner (max 10 par requête)
                'imgSize': 'large',  # Préférer les grandes images
                'safe': 'active',
            }
            
            url = f"https://www.googleapis.com/customsearch/v1?{urllib.parse.urlencode(params)}"
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                images = []
                for item in items:
                    images.append({
                        'url': item.get('link', ''),
                        'thumbnail': item.get('image', {}).get('thumbnailLink', ''),
                        'title': item.get('title', ''),
                        'source': item.get('displayLink', ''),
                        'width': item.get('image', {}).get('width', 0),
                        'height': item.get('image', {}).get('height', 0),
                    })
                
                _logger.info(f"Google Images: {len(images)} résultats trouvés")
                
                return {
                    'success': True,
                    'images': images,
                    'query': search_query,
                }
            
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': "Quota API Google dépassé (100/jour) ou clé invalide.",
                }
            else:
                _logger.error(f"Erreur API Google: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur API Google: {response.status_code}",
                }
                
        except Exception as e:
            _logger.error(f"Erreur recherche images: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _build_image_search_query(self):
        """Construit la requête de recherche optimisée pour trouver des images produit"""
        self.ensure_one()
        
        parts = []
        
        # Marque en premier (important pour la pertinence)
        if self.brand:
            parts.append(self.brand)
        
        # Nom du produit (nettoyer les infos redondantes)
        name = self.name or ''
        # Retirer la marque si déjà présente dans le nom
        if self.brand and self.brand.lower() in name.lower():
            name = name.lower().replace(self.brand.lower(), '').strip()
        # Retirer la capacité si présente
        if self.capacity and self.capacity in name:
            name = name.replace(self.capacity, '').strip()
        
        if name:
            parts.append(name)
        
        # Ajouter la catégorie pour contexte
        if self.category:
            # Simplifier certaines catégories
            cat_lower = self.category.lower()
            if 'pompe' in cat_lower and 'chaleur' in cat_lower:
                parts.append('pompe chaleur piscine')
            elif 'robot' in cat_lower:
                parts.append('robot piscine')
            elif 'filtr' in cat_lower:
                parts.append('filtre piscine')
            else:
                parts.append(self.category)
        else:
            parts.append('piscine')  # Contexte par défaut
        
        return ' '.join(parts)
    
    def action_import_images_from_urls(self, image_urls):
        """
        Importe une liste d'images depuis leurs URLs et les ajoute au produit.
        
        Args:
            image_urls: Liste de dictionnaires {'url': '...', 'title': '...'}
        
        Returns:
            dict avec success et message
        """
        self.ensure_one()
        
        # Déterminer le produit cible
        product = self.product_id or self.existing_product_id
        
        if not product:
            return {
                'success': False,
                'error': "Aucun produit Odoo lié. Importez d'abord le produit.",
            }
        
        imported_count = 0
        errors = []
        
        for img_data in image_urls:
            url = img_data.get('url', '')
            title = img_data.get('title', f'Image {imported_count + 1}')
            
            if not url:
                continue
            
            try:
                # Télécharger l'image
                response = requests.get(url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; OdooBot/1.0)'
                })
                
                if response.status_code == 200:
                    # Vérifier que c'est bien une image
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' not in content_type:
                        errors.append(f"URL non image: {url[:50]}...")
                        continue
                    
                    # Encoder en base64
                    image_base64 = base64.b64encode(response.content)
                    
                    # Ajouter comme image secondaire
                    if not product.image_1920:
                        # Première image = image principale
                        product.image_1920 = image_base64
                        _logger.info(f"Image principale ajoutée depuis {url[:50]}")
                    else:
                        # Images suivantes = images secondaires
                        self.env['product.image'].create({
                            'product_tmpl_id': product.id,
                            'name': title[:100],
                            'image_1920': image_base64,
                        })
                        _logger.info(f"Image secondaire ajoutée: {title[:50]}")
                    
                    imported_count += 1
                else:
                    errors.append(f"Erreur {response.status_code}: {url[:50]}...")
                    
            except requests.exceptions.Timeout:
                errors.append(f"Timeout: {url[:50]}...")
            except Exception as e:
                errors.append(f"Erreur: {str(e)[:50]}")
        
        return {
            'success': imported_count > 0,
            'imported': imported_count,
            'errors': errors,
            'message': f"{imported_count} image(s) importée(s)" + (f", {len(errors)} erreur(s)" if errors else ""),
        }
    
    @api.model
    def search_images_for_product(self, product_id):
        """
        Méthode appelable depuis JavaScript pour rechercher des images.
        """
        product = self.browse(product_id)
        if product.exists():
            return product.action_search_images()
        return {'success': False, 'error': 'Produit non trouvé'}
    
    @api.model
    def import_images_for_product(self, product_id, image_urls):
        """
        Méthode appelable depuis JavaScript pour importer des images.
        
        Args:
            product_id: ID du pool.catalog.extraction.product
            image_urls: Liste de {'url': '...', 'title': '...'}
        """
        product = self.browse(product_id)
        if product.exists():
            return product.action_import_images_from_urls(image_urls)
        return {'success': False, 'error': 'Produit non trouvé'}
    
    def _get_pool_store_website(self):
        """
        Récupère le website Pool Store.
        Recherche par nom contenant 'pool' ou par domaine.
        """
        Website = self.env['website'].sudo()
        
        # Chercher par nom
        pool_website = Website.search([
            '|', '|', '|',
            ('name', 'ilike', 'pool store'),
            ('name', 'ilike', 'poolstore'),
            ('name', 'ilike', 'pool'),
            ('domain', 'ilike', 'poolstore'),
        ], limit=1)
        
        if pool_website:
            return pool_website
        
        # Si pas trouvé, chercher un website avec "lolirine" et "pool" dans le nom
        pool_website = Website.search([
            ('name', 'ilike', 'lolirine'),
            ('name', 'ilike', 'pool'),
        ], limit=1)
        
        if pool_website:
            return pool_website
        
        _logger.warning("Website Pool Store non trouvé - produit non assigné à un website spécifique")
        return False
    
    def _format_website_description(self):
        """
        Formate la description pour le site web e-commerce.
        Crée un HTML structuré avec description + spécifications techniques.
        """
        self.ensure_one()
        
        html_parts = []
        
        # Description principale
        if self.description_fr:
            html_parts.append(f'<div class="product-description">')
            html_parts.append(f'<p>{self.description_fr}</p>')
            html_parts.append('</div>')
        
        # Tableau des spécifications techniques
        specs = []
        
        if self.power_kw:
            specs.append(('Puissance', f'{self.power_kw} kW'))
        if self.flow_rate:
            specs.append(('Débit', f'{self.flow_rate} m³/h'))
        if self.filter_area:
            specs.append(('Surface filtrante', f'{self.filter_area} m²'))
        if self.voltage:
            specs.append(('Tension', f'{self.voltage} V'))
        if self.diameter_mm:
            specs.append(('Diamètre', f'{self.diameter_mm} mm'))
        if self.cop:
            specs.append(('COP', str(self.cop)))
        if self.noise_level:
            specs.append(('Niveau sonore', f'{self.noise_level} dB(A)'))
        if self.refrigerant_gas:
            specs.append(('Gaz réfrigérant', self.refrigerant_gas))
        if self.power_supply:
            specs.append(('Alimentation', self.power_supply))
        if self.pool_volume_min or self.pool_volume_max:
            vol_str = f"{self.pool_volume_min or '?'} - {self.pool_volume_max or '?'} m³"
            specs.append(('Volume piscine', vol_str))
        if self.operating_temp_min is not None or self.operating_temp_max is not None:
            temp_str = f"{self.operating_temp_min or '?'}°C à {self.operating_temp_max or '?'}°C"
            specs.append(('Température fonctionnement', temp_str))
        if self.water_connection:
            specs.append(('Connexion eau', self.water_connection))
        if self.energy_class:
            specs.append(('Classe énergétique', self.energy_class))
        if self.product_type:
            specs.append(('Technologie', self.product_type))
        if self.installation_type:
            specs.append(('Installation', self.installation_type))
        if self.wifi_compatible:
            specs.append(('Connectivité', 'WiFi'))
        
        # Créer le tableau si on a des specs
        if specs:
            html_parts.append('<div class="product-specifications mt-4">')
            html_parts.append('<h4>Caractéristiques techniques</h4>')
            html_parts.append('<table class="table table-sm table-striped">')
            html_parts.append('<tbody>')
            for label, value in specs:
                html_parts.append(f'<tr><td><strong>{label}</strong></td><td>{value}</td></tr>')
            html_parts.append('</tbody>')
            html_parts.append('</table>')
            html_parts.append('</div>')
        
        # Marque si disponible
        if self.brand:
            html_parts.append(f'<p class="text-muted mt-3"><small>Marque : {self.brand}</small></p>')
        
        return '\n'.join(html_parts) if html_parts else self.description_fr or ''
    
    def _get_public_category_ids(self, category_name):
        """
        Trouve les catégories e-commerce publiques correspondant à la catégorie détectée.
        Retourne une liste d'IDs de product.public.category.
        """
        if not category_name:
            return []
        
        PublicCategory = self.env['product.public.category'].sudo()
        category_ids = []
        
        # Mapping des catégories OCR vers catégories e-commerce
        category_mapping = {
            'pompe à chaleur': ['Chauffage & PAC', 'Pompes à chaleur', 'Chauffage'],
            'pompes à chaleur': ['Chauffage & PAC', 'Pompes à chaleur', 'Chauffage'],
            'pac': ['Chauffage & PAC', 'Pompes à chaleur'],
            'pompe': ['Pompes', 'Équipements'],
            'filtration': ['Filtres & Média filtrant', 'Filtration'],
            'filtre': ['Filtres & Média filtrant', 'Filtration'],
            'robot': ['Robots automatiques', 'Nettoyage & Robots'],
            'nettoyage': ['Nettoyage & Robots', 'Accessoires nettoyage'],
            'éclairage': ['Éclairage LED', 'Éclairage'],
            'led': ['Éclairage LED'],
            'traitement': ['Traitement de l\'eau', 'Produits traitement'],
            'chlore': ['Chlore & Brome', 'Traitement de l\'eau'],
            'sel': ['Électrolyse au sel'],
            'spa': ['Spas & Jacuzzis', 'Espace Wellness'],
            'jacuzzi': ['Spas & Jacuzzis', 'Espace Wellness'],
            'wellness': ['Espace Wellness'],
            'bâche': ['Bâches & Couvertures'],
            'couverture': ['Bâches & Couvertures'],
            'liner': ['Liners & Revêtements'],
            'échelle': ['Échelles & Plongeoirs'],
            'skimmer': ['Skimmers & Buses'],
        }
        
        # Normaliser le nom de la catégorie
        cat_lower = category_name.lower()
        
        # Chercher dans le mapping
        search_terms = []
        for key, values in category_mapping.items():
            if key in cat_lower:
                search_terms.extend(values)
        
        # Ajouter le nom original comme terme de recherche
        if not search_terms:
            search_terms = [category_name]
        
        # Chercher les catégories publiques
        for term in search_terms:
            public_cat = PublicCategory.search([
                ('name', 'ilike', term)
            ], limit=1)
            if public_cat and public_cat.id not in category_ids:
                category_ids.append(public_cat.id)
                _logger.info(f"Catégorie e-commerce trouvée: {public_cat.name} (ID: {public_cat.id})")
        
        # Si aucune catégorie trouvée, chercher une catégorie parente "Piscine" ou générale
        if not category_ids:
            fallback_cat = PublicCategory.search([
                '|', '|',
                ('name', 'ilike', 'piscine'),
                ('name', 'ilike', 'équipement'),
                ('name', 'ilike', 'pool'),
            ], limit=1)
            if fallback_cat:
                category_ids.append(fallback_cat.id)
                _logger.info(f"Catégorie e-commerce fallback: {fallback_cat.name}")
        
        return category_ids
    
    @api.model
    def search_images_custom_query(self, product_id, query):
        """
        Recherche d'images avec une requête personnalisée.
        
        Args:
            product_id: ID du pool.catalog.extraction.product (pour contexte)
            query: Requête de recherche personnalisée
        """
        # Récupérer les clés API
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('pool.google_api_key')
        search_engine_id = ICP.get_param('pool.google_search_engine_id')
        
        if not api_key or not search_engine_id:
            return {
                'success': False,
                'error': "API Google non configurée.",
            }
        
        if not query:
            return {
                'success': False,
                'error': "Requête vide.",
            }
        
        _logger.info(f"Recherche d'images Google (custom): {query}")
        
        try:
            import urllib.parse
            
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': query,
                'searchType': 'image',
                'num': 10,
                'imgSize': 'large',
                'safe': 'active',
            }
            
            url = f"https://www.googleapis.com/customsearch/v1?{urllib.parse.urlencode(params)}"
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                images = []
                for item in items:
                    images.append({
                        'url': item.get('link', ''),
                        'thumbnail': item.get('image', {}).get('thumbnailLink', ''),
                        'title': item.get('title', ''),
                        'source': item.get('displayLink', ''),
                        'width': item.get('image', {}).get('width', 0),
                        'height': item.get('image', {}).get('height', 0),
                    })
                
                return {
                    'success': True,
                    'images': images,
                    'query': query,
                }
            
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': "Quota API Google dépassé ou clé invalide.",
                }
            else:
                return {
                    'success': False,
                    'error': f"Erreur API Google: {response.status_code}",
                }
                
        except Exception as e:
            _logger.error(f"Erreur recherche images: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
