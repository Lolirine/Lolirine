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
            
            # Prompt complet pour extraire tous types de produits piscine
            prompt = """Analyse cette image d'un catalogue de produits de piscine.

IMPORTANT: Détecte s'il s'agit d'un produit unique, d'un produit avec variantes (tableau avec différentes tailles/capacités/prix), ou de plusieurs produits distincts.

EXTRACTION DES PRIX - TRÈS IMPORTANT:
- Les prix sont souvent dans une colonne nommée "EURO", "PRIX", "€", "PVP", "TARIF" ou similaire
- Pour chaque ligne d'un tableau, extrais le prix correspondant
- Le prix doit être un NOMBRE sans symbole € (ex: 0.34, 12.25, 690)
- Si le prix est formaté avec virgule européenne (ex: "€0,34"), convertis en point décimal (0.34)
- Si plusieurs colonnes de prix existent (HT/TTC), prends le prix HT
- Ne laisse JAMAIS purchase_price à 0 si un prix est visible dans le tableau !

TABLEAUX DE VARIANTES (Raccords PVC, accessoires, etc.):
- Souvent organisés en colonnes: DIMENSION | RÉF. | PN | EURO
- Chaque ligne du tableau = une variante avec son propre prix
- La dimension (32mm, 40mm, 50mm, 63mm, 75mm, 110mm...) va dans "capacity" ou "variant_name"
- La référence (AA808, AA809...) va dans "reference"
- Le prix de la colonne EURO va dans "purchase_price"

Extrais les informations au format JSON suivant:

{
    "extraction_type": "single" | "variants" | "multiple",
    "base_product": {
        "name": "nom du produit principal (sans la capacité/variante)",
        "brand": "marque",
        "category": "catégorie détectée (voir liste ci-dessous)",
        "subcategory": "sous-catégorie si applicable",
        "description_fr": "description détaillée en français basée sur le texte visible"
    },
    "specifications": {
        "power_kw": null,
        "power_cv": null,
        "power_watts": null,
        "voltage": null,
        "amperage": null,
        "frequency_hz": null,
        "flow_rate_m3h": null,
        "head_pressure_m": null,
        "diameter_mm": null,
        "diameter_connection_mm": null,
        "filter_area_m2": null,
        "filter_capacity_kg": null,
        "cop": null,
        "eer": null,
        "noise_level_db": null,
        "capacity": null,
        "dimensions": null,
        "dimensions_lxwxh": null,
        "weight_kg": null,
        "warranty_years": null,
        "ip_rating": null,
        "cable_length_m": null,
        "cycle_time_hours": null,
        "coverage_m2": null,
        "lumens": null,
        "color_temperature_k": null,
        "lifespan_hours": null,
        "pressure_bar": null,
        "pressure_pn": null,
        "suction_flow_m3h": null,
        "autonomy_hours": null,
        "battery_voltage": null,
        "cleaning_width_cm": null,
        "pool_shape": null,
        "pool_surface": null,
        "production_clh_gh": null,
        "salt_concentration_gl": null,
        "ph_range": null,
        "orp_mv": null,
        "uv_dose": null,
        "ozone_production_gh": null,
        "material": null,
        "color": null,
        "steps_count": null,
        "max_load_kg": null,
        "thickness_mm": null,
        "trap_volume_l": null
    },
    "informative_attributes": {
        "refrigerant_gas": "gaz réfrigérant (R290, R32, R410A, etc.)",
        "power_supply": "alimentation électrique (230V/1Ph/50Hz, 380V/3Ph, etc.)",
        "pool_volume_min": "volume piscine minimum conseillé en m³",
        "pool_volume_max": "volume piscine maximum conseillé en m³",
        "pool_type": "type de piscine (enterrée, hors-sol, semi-enterrée, tous types)",
        "pool_liner_compatible": "compatible liner (oui/non)",
        "pool_bottom_type": "type de fond (plat, pente douce, pente composée, tous)",
        "operating_temp_min": "température fonctionnement min en °C",
        "operating_temp_max": "température fonctionnement max en °C",
        "water_temp_min": "température eau min en °C",
        "water_temp_max": "température eau max en °C",
        "water_connection": "diamètre connexion eau (50mm, 63mm)",
        "energy_class": "classe énergétique (A, A+, A++, A+++)",
        "product_type": "technologie (Inverter, Full Inverter, On/Off, etc.)",
        "installation_type": "installation (Intérieur, Extérieur, Les deux)",
        "wifi_compatible": true/false,
        "bluetooth_compatible": true/false,
        "app_control": "nom de l'application mobile si mentionné",
        "remote_control": true/false,
        "programmable": true/false,
        "automatic_cleaning": true/false,
        "wall_climbing": true/false,
        "waterline_cleaning": true/false,
        "filter_type": "type de filtre (sable, verre, cartouche, diatomée, poche)",
        "filter_media": "média filtrant (sable, verre, zeolite, AFM)",
        "fineness_microns": "finesse filtration en microns",
        "backwash_auto": true/false,
        "uv_treatment": true/false,
        "led_indicator": true/false,
        "safety_certified": "certifications (CE, TUV, NF, etc.)",
        "country_of_origin": "pays d'origine",
        "heating_capacity_min": "capacité chauffage min en kW",
        "heating_capacity_max": "capacité chauffage max en kW",
        "cooling_capacity": "capacité refroidissement en kW",
        "reversible": true/false,
        "defrost_auto": true/false,
        "anti_corrosion": "traitement anti-corrosion",
        "exchanger_material": "matériau échangeur (titane, inox, etc.)",
        "housing_material": "matériau coque/boîtier",
        "color_options": "couleurs disponibles",
        "rgb_led": true/false,
        "color_modes": "modes couleur (fixe, cycle, télécommande)",
        "transformer_included": true/false,
        "mounting_type": "type de montage (encastré, saillie, sur paroi, etc.)"
    },
    "product_image": {
        "detected": true/false,
        "position": "position de l'image (coin inférieur gauche, centre, etc.)",
        "description": "description courte de l'image du produit"
    },
    "products": [
        {
            "type_code": "code type/modèle",
            "reference": "référence fournisseur (ex: AA808, AA809)",
            "variant_name": "nom de la variante si applicable",
            "capacity": "capacité/dimension si applicable (ex: 32mm, 40mm, 50mm)",
            "purchase_price": 0.34,
            "selling_price": 0,
            "specifications": {
                "power_kw": null,
                "flow_rate_m3h": null,
                "cop": null,
                "noise_level_db": null,
                "pool_volume_min": null,
                "pool_volume_max": null,
                "cable_length_m": null,
                "cycle_time_hours": null,
                "coverage_m2": null,
                "diameter_mm": null,
                "pressure_pn": null
            }
        }
    ]
}

CATÉGORIES DE PRODUITS (utiliser ces valeurs exactes):
- Pompes à chaleur
- Pompes de filtration
- Pompes de nage à contre-courant
- Pompes doseuses
- Filtres à sable
- Filtres à cartouche
- Filtres à diatomée
- Robots électriques
- Robots hydrauliques
- Robots à pression
- Nettoyage manuel
- Électrolyseurs au sel
- Régulateurs pH
- Régulateurs chlore
- Traitement UV
- Traitement ozone
- Produits chimiques
- Projecteurs LED
- Spots encastrés
- Éclairage flottant
- Ampoules de remplacement
- Transformateurs éclairage
- Boîtes de connexion
- Enjoliveurs projecteurs
- Réchauffeurs électriques
- Échangeurs thermiques
- Couvertures à barres
- Bâches à bulles
- Volets roulants
- Couvertures automatiques
- Échelles inox
- Échelles amovibles
- Plongeoirs
- Skimmers
- Buses de refoulement
- Bondes de fond
- Prises balai
- Traverses de paroi
- Liners
- Liner armé
- Liner étang
- Accrochage liner
- Feutre géotextile
- Membranes PVC
- Alarmes immersion
- Alarmes périmétrique
- Barrières de sécurité
- Douches solaires
- Douches inox
- Pédiluves
- Spas gonflables
- Spas encastrables
- Accessoires spa
- Accessoires piscine
- Blocs polystyrène
- Margelles et dalles
- Système de débordement
- Outils construction
- Tuyauterie PVC
- Raccords PVC
- Manchons PVC
- Coudes PVC
- Tés PVC
- Réductions PVC
- Vannes
- Clapets et voyants
- Colles PVC
- Raccords union
- Coffrets électriques
- Tableaux de commande
- Préfiltres

Notes:
- Pour un tableau de variantes, crée un objet dans "products" pour chaque ligne
- OBLIGATOIRE: Les prix doivent être des nombres décimaux (0.34 pas "€0,34")
- Convertis les virgules européennes en points décimaux (1,49 → 1.49)
- Si tu ne trouves pas une information, utilise null
- Adapte les spécifications extraites au type de produit détecté
- Pour les raccords PVC: extrais TOUTES les lignes du tableau avec dimension, référence et prix
- Pour les robots: privilégie cable_length, cycle_time, coverage, wall_climbing
- Pour les filtres: privilégie filter_area, filter_capacity, fineness_microns
- Pour l'éclairage: privilégie lumens, color_temperature, ip_rating, rgb_led
- Pour les PAC: privilégie cop, refrigerant_gas, heating_capacity
- Pour les liners: privilégie thickness_mm, dimensions, color
- Pour la tuyauterie: privilégie diameter_mm, pressure_bar, material
- Pour les pièces à sceller: privilégie diameter_mm, flow_rate, material

EXEMPLE pour un tableau de raccords PVC:
Si tu vois un tableau avec colonnes DIMENSION|RÉF.|PN|EURO:
32mm | AA808 | 10 | €0,34
40mm | AA809 | 10 | €0,69
50mm | AA810 | 10 | €0,88

Tu dois créer 3 entrées dans "products" avec purchase_price: 0.34, 0.69, 0.88 respectivement.

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire ni backticks."""

            # Décoder si nécessaire
            if isinstance(image_base64, bytes):
                image_data = image_base64.decode('utf-8')
            else:
                image_data = image_base64
            
            payload = {
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 8192,
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
                content = self._clean_json_response(content)
                
                try:
                    data = json.loads(content)
                    return {
                        'success': True,
                        'data': data,
                    }
                except json.JSONDecodeError as e:
                    _logger.error(f"JSON parse error: {e}, content: {content[:500]}")
                    # Tentative de réparation du JSON
                    try:
                        repaired_content = self._repair_json(content)
                        data = json.loads(repaired_content)
                        return {
                            'success': True,
                            'data': data,
                        }
                    except:
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
            
            # Ajouter sous-catégorie
            if base_product.get('subcategory'):
                vals['subcategory'] = base_product.get('subcategory')
            
            # Ajouter les spécifications Float (peuvent être 0.0 si null)
            float_specs = [
                # Spécifications générales
                ('power_kw', 'power_kw'),
                ('power_watts', 'power_watts'),
                ('amperage', 'amperage'),
                ('flow_rate', 'flow_rate_m3h'),
                ('filter_area', 'filter_area_m2'),
                ('cop', 'cop'),
                ('eer', 'eer'),
                ('noise_level', 'noise_level_db'),
                ('weight', 'weight_kg'),
                ('heating_capacity_min', 'heating_capacity_min'),
                ('heating_capacity_max', 'heating_capacity_max'),
                ('cooling_capacity', 'cooling_capacity'),
                # Spécifications hydrauliques
                ('head_pressure_m', 'head_pressure_m'),
                ('suction_flow_m3h', 'suction_flow_m3h'),
                ('pressure_bar', 'pressure_bar'),
                ('trap_volume_l', 'trap_volume_l'),
                # Filtration
                ('filter_capacity_kg', 'filter_capacity_kg'),
                # Robots
                ('cable_length_m', 'cable_length_m'),
                ('cycle_time_hours', 'cycle_time_hours'),
                ('coverage_m2', 'coverage_m2'),
                ('autonomy_hours', 'autonomy_hours'),
                ('battery_voltage', 'battery_voltage'),
                # Traitement eau
                ('production_clh_gh', 'production_clh_gh'),
                ('salt_concentration_gl', 'salt_concentration_gl'),
                ('uv_dose', 'uv_dose'),
                ('ozone_production_gh', 'ozone_production_gh'),
                # Accessoires
                ('thickness_mm', 'thickness_mm'),
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
                # Électriques
                ('voltage', 'voltage'),
                ('frequency_hz', 'frequency_hz'),
                # Dimensions
                ('diameter_mm', 'diameter_mm'),
                ('diameter_connection_mm', 'diameter_connection_mm'),
                ('cleaning_width_cm', 'cleaning_width_cm'),
                # Filtration
                ('fineness_microns', 'fineness_microns'),
                # Volume/Température
                ('pool_volume_min', 'pool_volume_min'),
                ('pool_volume_max', 'pool_volume_max'),
                ('operating_temp_min', 'operating_temp_min'),
                ('operating_temp_max', 'operating_temp_max'),
                ('water_temp_min', 'water_temp_min'),
                ('water_temp_max', 'water_temp_max'),
                # Éclairage
                ('lumens', 'lumens'),
                ('color_temperature_k', 'color_temperature_k'),
                ('lifespan_hours', 'lifespan_hours'),
                # Traitement eau
                ('orp_mv', 'orp_mv'),
                # Accessoires
                ('steps_count', 'steps_count'),
                ('max_load_kg', 'max_load_kg'),
                ('warranty_years', 'warranty_years'),
            ]
            for field_name, spec_key in int_specs:
                value = prod_specs.get(spec_key)
                if value is not None:
                    try:
                        vals[field_name] = int(value)
                    except (ValueError, TypeError):
                        vals[field_name] = 0
            
            # Ajouter les spécifications Char
            char_specs = [
                ('power_cv', 'power_cv'),
                ('capacity_spec', 'capacity'),
                ('dimensions', 'dimensions'),
                ('dimensions', 'dimensions_lxwxh'),  # alternative
                ('ip_rating', 'ip_rating'),
                ('filter_type', 'filter_type'),
                ('filter_media', 'filter_media'),
                ('pool_bottom_type', 'pool_bottom_type'),
                ('pool_shape', 'pool_shape'),
                ('pool_surface', 'pool_surface'),
                ('ph_range', 'ph_range'),
                ('color_modes', 'color_modes'),
                ('mounting_type', 'mounting_type'),
                ('exchanger_material', 'exchanger_material'),
                ('material', 'material'),
                ('housing_material', 'housing_material'),
                ('color', 'color'),
                ('color_options', 'color_options'),
                ('anti_corrosion', 'anti_corrosion'),
            ]
            for field_name, spec_key in char_specs:
                value = prod_specs.get(spec_key)
                if value and str(value).strip():
                    vals[field_name] = str(value).strip()
            
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
        
        # =============================================
        # ATTRIBUTS STRING
        # =============================================
        str_attrs = [
            'refrigerant_gas', 'power_supply', 'water_connection',
            'energy_class', 'product_type', 'installation_type',
            # Nouveaux
            'filter_type', 'filter_media', 'pool_bottom_type', 'pool_shape',
            'pool_surface', 'ph_range', 'color_modes', 'mounting_type',
            'exchanger_material', 'material', 'housing_material', 'color',
            'color_options', 'anti_corrosion', 'app_control', 'safety_certified',
            'country_of_origin', 'pool_type', 'ip_rating',
        ]
        for attr in str_attrs:
            if info_attrs.get(attr):
                vals[attr] = str(info_attrs.get(attr))
        
        # =============================================
        # ATTRIBUTS ENTIERS
        # =============================================
        int_attrs = [
            'pool_volume_min', 'pool_volume_max',
            'operating_temp_min', 'operating_temp_max',
            # Nouveaux
            'water_temp_min', 'water_temp_max',
            'lumens', 'color_temperature_k', 'lifespan_hours',
            'fineness_microns', 'orp_mv', 'steps_count', 'max_load_kg',
        ]
        for attr in int_attrs:
            if info_attrs.get(attr) is not None:
                try:
                    vals[attr] = int(info_attrs.get(attr))
                except (ValueError, TypeError):
                    pass
        
        # =============================================
        # ATTRIBUTS FLOAT
        # =============================================
        float_attrs = [
            'heating_capacity_min', 'heating_capacity_max', 'cooling_capacity',
            # Nouveaux
            'cable_length_m', 'cycle_time_hours', 'coverage_m2', 'autonomy_hours',
            'production_clh_gh', 'salt_concentration_gl', 'uv_dose', 'ozone_production_gh',
        ]
        for attr in float_attrs:
            if info_attrs.get(attr) is not None:
                try:
                    vals[attr] = float(info_attrs.get(attr))
                except (ValueError, TypeError):
                    pass
        
        # =============================================
        # ATTRIBUTS BOOLÉENS
        # =============================================
        bool_attrs = [
            'wifi_compatible', 'bluetooth_compatible', 'remote_control',
            'programmable', 'automatic_cleaning', 'led_indicator',
            'wall_climbing', 'waterline_cleaning', 'backwash_auto',
            'uv_treatment', 'rgb_led', 'transformer_included',
            'reversible', 'defrost_auto', 'pool_liner_compatible',
        ]
        for attr in bool_attrs:
            if info_attrs.get(attr) is not None:
                vals[attr] = bool(info_attrs.get(attr))
        
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
    
    def _clean_json_response(self, content):
        """Nettoie la réponse JSON de l'API"""
        if not content:
            return '{}'
        
        content = content.strip()
        
        # Supprimer les backticks markdown
        if content.startswith('```'):
            lines = content.split('\n')
            # Trouver le début du JSON
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('```'):
                    start_idx = i + 1
                    break
            # Trouver la fin
            end_idx = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == '```':
                    end_idx = i
                    break
            content = '\n'.join(lines[start_idx:end_idx])
        
        # Supprimer le préfixe "json" si présent
        content = content.strip()
        if content.lower().startswith('json'):
            content = content[4:].strip()
        
        # Supprimer tout texte avant le premier { ou [
        first_brace = content.find('{')
        first_bracket = content.find('[')
        
        if first_brace == -1 and first_bracket == -1:
            return '{}'
        
        if first_brace == -1:
            start = first_bracket
        elif first_bracket == -1:
            start = first_brace
        else:
            start = min(first_brace, first_bracket)
        
        content = content[start:]
        
        # Supprimer tout texte après le dernier } ou ]
        last_brace = content.rfind('}')
        last_bracket = content.rfind(']')
        
        if last_brace == -1 and last_bracket == -1:
            return '{}'
        
        end = max(last_brace, last_bracket)
        content = content[:end + 1]
        
        return content
    
    def _repair_json(self, content):
        """Tente de réparer un JSON mal formé"""
        import re
        
        if not content:
            return '{}'
        
        # Compter les accolades et crochets
        open_braces = content.count('{')
        close_braces = content.count('}')
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        
        # Ajouter les accolades/crochets manquants
        content = content + ('}' * (open_braces - close_braces))
        content = content + (']' * (open_brackets - close_brackets))
        
        # Réparer les chaînes non terminées
        # Trouver les guillemets non fermés
        in_string = False
        escaped = False
        last_quote_pos = -1
        result = []
        
        for i, char in enumerate(content):
            if escaped:
                escaped = False
                result.append(char)
                continue
            
            if char == '\\':
                escaped = True
                result.append(char)
                continue
            
            if char == '"':
                if in_string:
                    in_string = False
                else:
                    in_string = True
                    last_quote_pos = len(result)
            
            result.append(char)
        
        # Si on est encore dans une chaîne, la fermer
        if in_string:
            # Trouver la fin logique de la chaîne (avant , ou } ou ])
            result_str = ''.join(result)
            # Fermer la chaîne à la position actuelle
            result.append('"')
        
        repaired = ''.join(result)
        
        # Supprimer les virgules trailing avant } ou ]
        repaired = re.sub(r',\s*}', '}', repaired)
        repaired = re.sub(r',\s*]', ']', repaired)
        
        # Ajouter des virgules manquantes entre éléments
        repaired = re.sub(r'"\s*"', '", "', repaired)
        repaired = re.sub(r'}\s*{', '}, {', repaired)
        repaired = re.sub(r']\s*\[', '], [', repaired)
        
        return repaired
    
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
        
        # =============================================
        # CHAMPS SPÉCIFICATIONS TECHNIQUES (variantes)
        # =============================================
        
        # Utiliser les specs du premier produit (base_product)
        # Champs numériques personnalisés (Float)
        numeric_fields = [
            ('x_power_kw', base_product.power_kw),
            ('x_flow_rate', base_product.flow_rate),
            ('x_filter_area', base_product.filter_area),
            ('x_cop', base_product.cop),
            ('x_noise_level', base_product.noise_level),
            ('x_weight', base_product.weight if hasattr(base_product, 'weight') else None),
            ('x_heating_capacity_min', base_product.heating_capacity_min if hasattr(base_product, 'heating_capacity_min') else None),
            ('x_heating_capacity_max', base_product.heating_capacity_max if hasattr(base_product, 'heating_capacity_max') else None),
            ('x_cooling_capacity', base_product.cooling_capacity if hasattr(base_product, 'cooling_capacity') else None),
        ]
        
        for field_name, field_value in numeric_fields:
            if field_name in ProductTemplate._fields and field_value is not None:
                vals[field_name] = float(field_value)
                _logger.info(f"Spec variante numérique: {field_name}={field_value}")
        
        # Champs entiers personnalisés (Integer)
        int_fields = [
            ('x_voltage', base_product.voltage),
            ('x_diameter_mm', base_product.diameter_mm),
            ('x_warranty_years', base_product.warranty_years if hasattr(base_product, 'warranty_years') else None),
            ('x_pool_volume_min', base_product.pool_volume_min if hasattr(base_product, 'pool_volume_min') else None),
            ('x_pool_volume_max', base_product.pool_volume_max if hasattr(base_product, 'pool_volume_max') else None),
            ('x_operating_temp_min', base_product.operating_temp_min if hasattr(base_product, 'operating_temp_min') else None),
            ('x_operating_temp_max', base_product.operating_temp_max if hasattr(base_product, 'operating_temp_max') else None),
        ]
        
        for field_name, field_value in int_fields:
            if field_name in ProductTemplate._fields and field_value is not None:
                vals[field_name] = int(field_value)
                _logger.info(f"Spec variante entier: {field_name}={field_value}")
        
        # Champs texte personnalisés (Char)
        char_fields = [
            ('x_power_cv', base_product.power_cv if hasattr(base_product, 'power_cv') else None),
            ('x_dimensions', base_product.dimensions if hasattr(base_product, 'dimensions') else None),
            ('x_refrigerant_gas', base_product.refrigerant_gas if hasattr(base_product, 'refrigerant_gas') else None),
            ('x_power_supply', base_product.power_supply if hasattr(base_product, 'power_supply') else None),
            ('x_water_connection', base_product.water_connection if hasattr(base_product, 'water_connection') else None),
            ('x_energy_class', base_product.energy_class if hasattr(base_product, 'energy_class') else None),
            ('x_product_type', base_product.product_type if hasattr(base_product, 'product_type') else None),
            ('x_installation_type', base_product.installation_type if hasattr(base_product, 'installation_type') else None),
        ]
        
        for field_name, field_value in char_fields:
            if field_name in ProductTemplate._fields and field_value:
                vals[field_name] = str(field_value)
                _logger.info(f"Spec variante texte: {field_name}={field_value}")
        
        # Champ booléen WiFi
        if 'x_wifi_compatible' in ProductTemplate._fields and hasattr(base_product, 'wifi_compatible'):
            vals['x_wifi_compatible'] = base_product.wifi_compatible
        
        # =============================================
        
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
    
    # Prix catalogue (extraits du PDF/image)
    purchase_price = fields.Float(string='Prix catalogue HT', help="Prix du catalogue fournisseur (avant remise)")
    selling_price = fields.Float(string='Prix de vente HT')
    
    # Prix calculés avec remise fournisseur
    discount_percent = fields.Float(string='Remise fournisseur (%)', compute='_compute_prices_with_discount', store=False)
    purchase_price_net = fields.Float(string='Prix achat NET', compute='_compute_prices_with_discount', store=False, help="Prix d'achat après remise fournisseur")
    selling_price_calculated = fields.Float(string='Prix vente suggéré', compute='_compute_prices_with_discount', store=False, help="Prix de vente calculé avec marge")
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
    
    # =============================================
    # NOUVEAUX CHAMPS - TOUS TYPES DE PRODUITS
    # =============================================
    
    # Sous-catégorie
    subcategory = fields.Char(string='Sous-catégorie')
    
    # Spécifications électriques étendues
    power_watts = fields.Float(string='Puissance (W)')
    amperage = fields.Float(string='Intensité (A)')
    frequency_hz = fields.Integer(string='Fréquence (Hz)')
    battery_voltage = fields.Float(string='Tension batterie (V)')
    
    # Spécifications hydrauliques
    head_pressure_m = fields.Float(string='Hauteur manométrique (m)')
    diameter_connection_mm = fields.Integer(string='Diamètre raccordement (mm)')
    suction_flow_m3h = fields.Float(string='Débit aspiration (m³/h)')
    pressure_bar = fields.Float(string='Pression (bar)')
    trap_volume_l = fields.Float(string='Volume préfiltre (L)')
    
    # Spécifications filtration
    filter_capacity_kg = fields.Float(string='Charge filtre (kg)')
    fineness_microns = fields.Integer(string='Finesse filtration (µm)')
    filter_type = fields.Char(string='Type de filtre', help="sable, verre, cartouche, diatomée")
    filter_media = fields.Char(string='Média filtrant', help="sable, verre, zeolite, AFM")
    backwash_auto = fields.Boolean(string='Contre-lavage auto', default=False)
    
    # Spécifications robots
    cable_length_m = fields.Float(string='Longueur câble (m)')
    cycle_time_hours = fields.Float(string='Durée cycle (h)')
    coverage_m2 = fields.Float(string='Surface couverte (m²)')
    cleaning_width_cm = fields.Integer(string='Largeur nettoyage (cm)')
    autonomy_hours = fields.Float(string='Autonomie (h)')
    wall_climbing = fields.Boolean(string='Monte aux parois', default=False)
    waterline_cleaning = fields.Boolean(string='Nettoyage ligne d\'eau', default=False)
    pool_bottom_type = fields.Char(string='Type de fond', help="plat, pente douce, pente composée")
    pool_shape = fields.Char(string='Forme piscine', help="rectangulaire, libre, toutes formes")
    pool_surface = fields.Char(string='Revêtement compatible', help="liner, carrelage, béton, coque")
    
    # Spécifications traitement eau
    production_clh_gh = fields.Float(string='Production chlore (g/h)')
    salt_concentration_gl = fields.Float(string='Concentration sel (g/L)')
    ph_range = fields.Char(string='Plage pH')
    orp_mv = fields.Integer(string='ORP (mV)')
    uv_dose = fields.Float(string='Dose UV (mJ/cm²)')
    ozone_production_gh = fields.Float(string='Production ozone (g/h)')
    uv_treatment = fields.Boolean(string='Traitement UV', default=False)
    
    # Spécifications éclairage
    lumens = fields.Integer(string='Flux lumineux (lm)')
    color_temperature_k = fields.Integer(string='Température couleur (K)')
    lifespan_hours = fields.Integer(string='Durée de vie (h)')
    ip_rating = fields.Char(string='Indice IP', help="Ex: IP68")
    rgb_led = fields.Boolean(string='LED RGB', default=False)
    color_modes = fields.Char(string='Modes couleur')
    transformer_included = fields.Boolean(string='Transfo inclus', default=False)
    mounting_type = fields.Char(string='Type montage', help="encastré, saillie, etc.")
    
    # Spécifications pompes à chaleur (étendues)
    eer = fields.Float(string='EER')
    reversible = fields.Boolean(string='Réversible', default=False)
    defrost_auto = fields.Boolean(string='Dégivrage auto', default=False)
    exchanger_material = fields.Char(string='Matériau échangeur', help="titane, inox")
    water_temp_min = fields.Integer(string='Temp. eau min (°C)')
    water_temp_max = fields.Integer(string='Temp. eau max (°C)')
    
    # Spécifications sécurité/accessoires
    material = fields.Char(string='Matériau')
    housing_material = fields.Char(string='Matériau boîtier')
    color = fields.Char(string='Couleur')
    color_options = fields.Char(string='Couleurs disponibles')
    steps_count = fields.Integer(string='Nombre marches')
    max_load_kg = fields.Integer(string='Charge max (kg)')
    thickness_mm = fields.Float(string='Épaisseur (mm)')
    anti_corrosion = fields.Char(string='Traitement anti-corrosion')
    
    # Spécifications connectivité
    bluetooth_compatible = fields.Boolean(string='Compatible Bluetooth', default=False)
    app_control = fields.Char(string='Application mobile')
    remote_control = fields.Boolean(string='Télécommande', default=False)
    programmable = fields.Boolean(string='Programmable', default=False)
    automatic_cleaning = fields.Boolean(string='Nettoyage automatique', default=False)
    led_indicator = fields.Boolean(string='Voyant LED', default=False)
    
    # Certifications et origine
    safety_certified = fields.Char(string='Certifications', help="CE, TUV, NF")
    country_of_origin = fields.Char(string='Pays d\'origine')
    
    # Compatibilité piscine
    pool_type = fields.Char(string='Type piscine', help="enterrée, hors-sol, tous types")
    pool_liner_compatible = fields.Boolean(string='Compatible liner', default=True)
    
    # =============================================
    
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
    
    # Option dropshipping
    is_dropship_product = fields.Boolean(
        string='Produit dropshipping',
        default=True,
        help="Créer automatiquement les informations fournisseur dropshipping"
    )
    
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
    
    @api.depends('purchase_price', 'category', 'extraction_id.supplier_id')
    def _compute_prices_with_discount(self):
        """Calcule les prix nets en appliquant la remise fournisseur."""
        for rec in self:
            supplier = rec.extraction_id.supplier_id if rec.extraction_id else False
            catalog_price = rec.purchase_price or 0
            
            if supplier and supplier.discount_ids and catalog_price > 0:
                # Utiliser la méthode du fournisseur pour calculer les prix
                price_info = supplier.calculate_prices(
                    catalog_price=catalog_price,
                    category_name=rec.category,
                )
                rec.discount_percent = price_info['discount_percent']
                rec.purchase_price_net = price_info['purchase_price']
                rec.selling_price_calculated = price_info['selling_price']
            else:
                # Pas de grille de remise, prix = catalogue
                rec.discount_percent = 0
                rec.purchase_price_net = catalog_price
                rec.selling_price_calculated = catalog_price * 1.35 if catalog_price > 0 else 0
    
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
        """Importe ce produit dans Odoo avec calcul automatique des prix (remise + marge)"""
        self.ensure_one()
        
        _logger.info(f"=== Début import produit OCR ID={self.id}, nom={self.name} ===")
        
        supplier = self.extraction_id.supplier_id
        ProductTemplate = self.env['product.template']
        
        # Préparer les valeurs de base (champs standard Odoo uniquement)
        ref_code = self.reference or self.type_code or str(self.id)
        
        _logger.info(f"Prix extraits (catalogue) - Achat: {self.purchase_price}, Vente: {self.selling_price}")
        
        # =============================================
        # CALCUL DES PRIX AVEC REMISE FOURNISSEUR
        # =============================================
        
        catalog_price = float(self.purchase_price or 0)
        selling_price = float(self.selling_price or 0)
        
        # Appliquer la remise fournisseur si disponible
        if supplier and supplier.discount_ids and catalog_price > 0:
            price_info = supplier.calculate_prices(
                catalog_price=catalog_price,
                category_name=self.category,
            )
            
            purchase_price_net = price_info['purchase_price']
            calculated_selling_price = price_info['selling_price']
            discount_percent = price_info['discount_percent']
            margin_percent = price_info['margin_percent']
            
            _logger.info(f"💰 Prix catalogue: {catalog_price}€")
            _logger.info(f"📉 Remise fournisseur: {discount_percent}%")
            _logger.info(f"💵 Prix d'achat NET: {purchase_price_net}€")
            _logger.info(f"📈 Marge appliquée: {margin_percent}%")
            _logger.info(f"🏷️ Prix de vente calculé: {calculated_selling_price}€")
            
            # Utiliser le prix de vente extrait si défini, sinon calculer
            if selling_price > 0:
                final_selling_price = selling_price
                _logger.info(f"→ Prix de vente extrait utilisé: {final_selling_price}€")
            else:
                final_selling_price = calculated_selling_price
                _logger.info(f"→ Prix de vente calculé utilisé: {final_selling_price}€")
        else:
            # Pas de grille de remise, utiliser les prix extraits tels quels
            purchase_price_net = catalog_price
            final_selling_price = selling_price if selling_price > 0 else catalog_price * 1.35
            _logger.info(f"Pas de grille de remise, prix utilisés tels quels")
        
        # =============================================
        
        vals = {
            'name': self.name or 'Produit sans nom',
            'default_code': f"POOL-{ref_code}",
            'description_sale': self.description_fr or '',
            'standard_price': purchase_price_net,
            'list_price': final_selling_price,
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
        
        # =============================================
        # CHAMPS SPÉCIFICATIONS TECHNIQUES (onglet Piscine)
        # =============================================
        
        # Champs numériques personnalisés (Float)
        numeric_fields = [
            ('x_power_kw', self.power_kw),
            ('x_flow_rate', self.flow_rate),
            ('x_filter_area', self.filter_area),
            ('x_cop', self.cop),
            ('x_noise_level', self.noise_level),
            ('x_weight', self.weight if hasattr(self, 'weight') else None),
            ('x_heating_capacity_min', self.heating_capacity_min if hasattr(self, 'heating_capacity_min') else None),
            ('x_heating_capacity_max', self.heating_capacity_max if hasattr(self, 'heating_capacity_max') else None),
            ('x_cooling_capacity', self.cooling_capacity if hasattr(self, 'cooling_capacity') else None),
        ]
        
        for field_name, field_value in numeric_fields:
            if field_name in ProductTemplate._fields and field_value is not None:
                vals[field_name] = float(field_value)
                _logger.info(f"Spec numérique: {field_name}={field_value}")
        
        # Champs entiers personnalisés (Integer)
        int_fields = [
            ('x_voltage', self.voltage),
            ('x_diameter_mm', self.diameter_mm),
            ('x_warranty_years', self.warranty_years if hasattr(self, 'warranty_years') else None),
            ('x_pool_volume_min', self.pool_volume_min if hasattr(self, 'pool_volume_min') else None),
            ('x_pool_volume_max', self.pool_volume_max if hasattr(self, 'pool_volume_max') else None),
            ('x_operating_temp_min', self.operating_temp_min if hasattr(self, 'operating_temp_min') else None),
            ('x_operating_temp_max', self.operating_temp_max if hasattr(self, 'operating_temp_max') else None),
        ]
        
        for field_name, field_value in int_fields:
            if field_name in ProductTemplate._fields and field_value is not None:
                vals[field_name] = int(field_value)
                _logger.info(f"Spec entier: {field_name}={field_value}")
        
        # Champs texte personnalisés (Char)
        char_fields = [
            ('x_power_cv', self.power_cv if hasattr(self, 'power_cv') else None),
            ('x_dimensions', self.dimensions if hasattr(self, 'dimensions') else None),
            ('x_refrigerant_gas', self.refrigerant_gas if hasattr(self, 'refrigerant_gas') else None),
            ('x_power_supply', self.power_supply if hasattr(self, 'power_supply') else None),
            ('x_water_connection', self.water_connection if hasattr(self, 'water_connection') else None),
            ('x_energy_class', self.energy_class if hasattr(self, 'energy_class') else None),
            ('x_product_type', self.product_type if hasattr(self, 'product_type') else None),
            ('x_installation_type', self.installation_type if hasattr(self, 'installation_type') else None),
        ]
        
        for field_name, field_value in char_fields:
            if field_name in ProductTemplate._fields and field_value:
                vals[field_name] = str(field_value)
                _logger.info(f"Spec texte: {field_name}={field_value}")
        
        # Champ booléen WiFi
        if 'x_wifi_compatible' in ProductTemplate._fields and hasattr(self, 'wifi_compatible'):
            vals['x_wifi_compatible'] = self.wifi_compatible
        
        # =============================================
        
        # Date d'import
        if 'x_pool_import_date' in ProductTemplate._fields:
            vals['x_pool_import_date'] = fields.Datetime.now()
        
        # Fournisseur
        if supplier and 'x_pool_supplier_id' in ProductTemplate._fields:
            vals['x_pool_supplier_id'] = supplier.id
            _logger.info(f"Fournisseur: {supplier.name}")
        
        # Catégorie
        if self.category:
            _logger.info(f"Recherche catégorie: {self.category}")
            category = self.env['product.category'].search([
                ('name', 'ilike', self.category)
            ], limit=1)
            
            if not category:
                # Créer la catégorie si elle n'existe pas
                _logger.info(f"Catégorie non trouvée, création de: {self.category}")
                # Chercher une catégorie parente "Piscine" ou "All"
                parent_category = self.env['product.category'].search([
                    '|',
                    ('name', 'ilike', 'piscine'),
                    ('name', '=', 'All'),
                ], limit=1)
                
                try:
                    category = self.env['product.category'].create({
                        'name': self.category,
                        'parent_id': parent_category.id if parent_category else False,
                    })
                    _logger.info(f"Catégorie créée: {category.name} (ID: {category.id})")
                except Exception as e:
                    _logger.warning(f"Impossible de créer la catégorie: {e}")
            
            if category:
                vals['categ_id'] = category.id
                _logger.info(f"Catégorie assignée: {category.name} (ID: {category.id})")
        
        # NOTE: La catégorie e-commerce (public_categ_ids) est déjà assignée plus haut via _get_public_category_ids()
        
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
            
            # Créer les infos dropshipping (toujours essayer, le champ est True par défaut)
            _logger.info(f"=== Tentative création dropship info ===")
            _logger.info(f"is_dropship_product = {self.is_dropship_product}")
            try:
                dropship_result = self._create_dropship_info(product)
                if dropship_result:
                    _logger.info(f"Dropship info créée avec succès: {dropship_result}")
                else:
                    _logger.warning(f"Dropship info non créée (résultat: {dropship_result})")
            except Exception as dropship_error:
                _logger.error(f"Erreur lors de _create_dropship_info: {dropship_error}")
            
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
    
    def _create_dropship_info(self, product):
        """Crée les informations dropshipping pour un produit importé"""
        self.ensure_one()
        _logger.info(f"=== _create_dropship_info pour produit {product.id} ({product.name}) ===")
        
        supplier = self.extraction_id.supplier_id
        _logger.info(f"Fournisseur pool.supplier: {supplier}")
        
        if not supplier:
            _logger.warning("Pas de fournisseur défini dans l'extraction, impossible de créer les infos dropship")
            return False
        
        _logger.info(f"Fournisseur: {supplier.name} (ID: {supplier.id})")
        
        # Récupérer le partenaire lié au fournisseur pool
        partner = supplier.partner_id
        _logger.info(f"Partner existant: {partner}")
        
        if not partner:
            # Créer automatiquement un partenaire si nécessaire
            _logger.info(f"Création d'un nouveau partenaire pour {supplier.name}")
            try:
                partner = self.env['res.partner'].create({
                    'name': supplier.name,
                    'is_company': True,
                    'supplier_rank': 1,
                })
                # Ajouter les champs dropship si ils existent
                if 'is_dropship_supplier' in self.env['res.partner']._fields:
                    partner.is_dropship_supplier = True
                if 'dropship_certified' in self.env['res.partner']._fields:
                    partner.dropship_certified = True
                    
                supplier.partner_id = partner
                _logger.info(f"Partenaire créé: {partner.name} (ID: {partner.id})")
            except Exception as e:
                _logger.error(f"Erreur création partenaire: {e}")
                return False
        else:
            _logger.info(f"Partenaire existant: {partner.name} (ID: {partner.id})")
            # S'assurer que le partenaire est marqué comme fournisseur dropship
            try:
                if 'is_dropship_supplier' in self.env['res.partner']._fields:
                    if not partner.is_dropship_supplier:
                        partner.write({
                            'is_dropship_supplier': True,
                            'supplier_rank': max(partner.supplier_rank, 1),
                        })
                        _logger.info("Partenaire marqué comme fournisseur dropship")
            except Exception as e:
                _logger.warning(f"Impossible de marquer le partenaire comme dropship: {e}")
        
        # Vérifier si le modèle supplier.dropship.info existe
        if 'supplier.dropship.info' not in self.env:
            _logger.error("Le modèle supplier.dropship.info n'existe pas ! Le module lolirine_pool_dropship est-il installé ?")
            return False
        
        # Vérifier si une entrée dropship existe déjà
        DropshipInfo = self.env['supplier.dropship.info']
        existing = DropshipInfo.search([
            ('supplier_id', '=', partner.id),
            ('product_tmpl_id', '=', product.id),
        ], limit=1)
        _logger.info(f"Entrée dropship existante: {existing}")
        
        # Préparer les valeurs
        ref_code = self.reference or self.type_code or str(self.id)
        
        dropship_vals = {
            'supplier_id': partner.id,
            'product_tmpl_id': product.id,
            'supplier_product_ref': ref_code,
            'supplier_product_name': product.name,
            'price': float(self.purchase_price or 0),
            'currency_id': self.env.company.currency_id.id,
            'delay': 5,
            'shipping_cost': 0.0,
            'is_dropship_capable': True,
            'is_active': True,
            'min_order_qty': 1,
            'notes': f"Import auto OCR {fields.Datetime.now().strftime('%d/%m/%Y')}",
        }
        _logger.info(f"Valeurs dropship: {dropship_vals}")
        
        try:
            if existing:
                existing.write(dropship_vals)
                result = existing
                _logger.info(f"Info dropship MISE À JOUR: ID={result.id}")
            else:
                result = DropshipInfo.create(dropship_vals)
                _logger.info(f"Info dropship CRÉÉE: ID={result.id}")
            
            # Marquer le produit comme produit dropshipping
            if 'is_dropship_product' in product._fields:
                if not product.is_dropship_product:
                    product.is_dropship_product = True
                    _logger.info("Produit marqué is_dropship_product=True")
            
            return result
            
        except Exception as e:
            _logger.error(f"ERREUR création info dropship: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            return False
    
    def _get_pool_category(self):
        """
        Retourne la catégorie product.public.category correspondant à la catégorie extraite.
        Utilise un mapping pour convertir les catégories du catalogue vers les catégories piscine.
        
        Catégories e-commerce disponibles:
        01. ROBOTS DE PISCINE
        02. CONSTRUCTION
        03. ÉCLAIRAGE
        04. POMPES
        05. FILTRATION
        06. CHAUFFAGE
        07. TECHNIQUE DE MESURE ET DE CONTRÔLE / PRODUITS CHIMIQUES
        08. TECHNIQUE DE TRAITEMENT DE L'EAU
        09. COUVERTURES
        10. MAINTENANCE ET ACCESSOIRES
        11. MATÉRIAUX DE CONNEXION
        12. IRRIGATION
        """
        self.ensure_one()
        
        if not self.category:
            return False
        
        # Mapping catégorie extraite → product.public.category (catégories e-commerce)
        # IMPORTANT: L'ordre compte ! Les termes plus spécifiques doivent être en premier
        # Format: (terme_recherché, nom_catégorie_ecommerce)
        category_mapping = [
            # ============================================
            # 01. ROBOTS DE PISCINE
            # ============================================
            ('robot', 'ROBOTS DE PISCINE'),
            ('nettoyeur automatique', 'ROBOTS DE PISCINE'),
            ('aspirateur piscine', 'ROBOTS DE PISCINE'),
            ('cleaner', 'ROBOTS DE PISCINE'),
            ('polaris', 'ROBOTS DE PISCINE'),
            ('zodiac mx', 'ROBOTS DE PISCINE'),
            ('dolphin', 'ROBOTS DE PISCINE'),
            
            # ============================================
            # 02. CONSTRUCTION
            # ============================================
            ('liner', 'CONSTRUCTION'),
            ('construction', 'CONSTRUCTION'),
            ('rénovation', 'CONSTRUCTION'),
            ('membrane', 'CONSTRUCTION'),
            ('pièce à sceller', 'CONSTRUCTION'),
            ('skimmer', 'CONSTRUCTION'),
            ('bonde de fond', 'CONSTRUCTION'),
            ('refoulement', 'CONSTRUCTION'),
            ('margelle', 'CONSTRUCTION'),
            ('escalier piscine', 'CONSTRUCTION'),
            ('étanchéité', 'CONSTRUCTION'),
            
            # ============================================
            # 03. ÉCLAIRAGE
            # ============================================
            ('éclairage', 'ÉCLAIRAGE'),
            ('eclairage', 'ÉCLAIRAGE'),
            ('projecteur', 'ÉCLAIRAGE'),
            ('spot', 'ÉCLAIRAGE'),
            ('led piscine', 'ÉCLAIRAGE'),
            ('lampe piscine', 'ÉCLAIRAGE'),
            ('ampoule piscine', 'ÉCLAIRAGE'),
            ('luminaire', 'ÉCLAIRAGE'),
            ('transformateur', 'ÉCLAIRAGE'),
            
            # ============================================
            # 04. POMPES (spécifiques avant générique)
            # ============================================
            ('pompe de circulation', 'POMPES'),
            ('pompe de filtration', 'POMPES'),
            ('pompe à vitesse variable', 'POMPES'),
            ('pompe auto-amorçante', 'POMPES'),
            ('surpresseur', 'POMPES'),
            ('pompe doseuse', 'POMPES'),
            
            # ============================================
            # 05. FILTRATION
            # ============================================
            ('préfiltre', 'FILTRATION'),
            ('pré-filtre', 'FILTRATION'),
            ('multicyclone', 'FILTRATION'),
            ('hydrospin', 'FILTRATION'),
            ('filtre à sable', 'FILTRATION'),
            ('filtre à cartouche', 'FILTRATION'),
            ('filtre à diatomées', 'FILTRATION'),
            ('filtration', 'FILTRATION'),
            ('média filtrant', 'FILTRATION'),
            ('verre filtrant', 'FILTRATION'),
            ('cartouche filtrante', 'FILTRATION'),
            ('filtre', 'FILTRATION'),
            ('vanne multivoies', 'FILTRATION'),
            ('crépine', 'FILTRATION'),
            ('manomètre', 'FILTRATION'),
            
            # ============================================
            # 06. CHAUFFAGE
            # ============================================
            ('pompe à chaleur', 'CHAUFFAGE'),
            ('pompes à chaleur', 'CHAUFFAGE'),
            ('pac piscine', 'CHAUFFAGE'),
            ('heat pump', 'CHAUFFAGE'),
            ('réchauffeur', 'CHAUFFAGE'),
            ('échangeur thermique', 'CHAUFFAGE'),
            ('échangeur de chaleur', 'CHAUFFAGE'),
            ('chauffage solaire', 'CHAUFFAGE'),
            ('capteur solaire', 'CHAUFFAGE'),
            ('chauffage', 'CHAUFFAGE'),
            
            # ============================================
            # 07. TECHNIQUE DE MESURE ET DE CONTRÔLE / PRODUITS CHIMIQUES
            # ============================================
            ('testeur', 'TECHNIQUE DE MESURE'),
            ('analyse', 'TECHNIQUE DE MESURE'),
            ('photomètre', 'TECHNIQUE DE MESURE'),
            ('bandelette', 'TECHNIQUE DE MESURE'),
            ('ph-mètre', 'TECHNIQUE DE MESURE'),
            ('sonde', 'TECHNIQUE DE MESURE'),
            ('régulateur', 'TECHNIQUE DE MESURE'),
            ('contrôleur', 'TECHNIQUE DE MESURE'),
            ('coffret électrique', 'TECHNIQUE DE MESURE'),
            ('chlore', 'TECHNIQUE DE MESURE'),
            ('brome', 'TECHNIQUE DE MESURE'),
            ('algicide', 'TECHNIQUE DE MESURE'),
            ('floculant', 'TECHNIQUE DE MESURE'),
            ('ph+', 'TECHNIQUE DE MESURE'),
            ('ph-', 'TECHNIQUE DE MESURE'),
            ('produit chimique', 'TECHNIQUE DE MESURE'),
            ('chimie', 'TECHNIQUE DE MESURE'),
            ('désinfectant', 'TECHNIQUE DE MESURE'),
            
            # ============================================
            # 08. TECHNIQUE DE TRAITEMENT DE L'EAU
            # ============================================
            ('électrolyseur', 'TRAITEMENT DE L\'EAU'),
            ('électrolyse', 'TRAITEMENT DE L\'EAU'),
            ('cellule électrolyse', 'TRAITEMENT DE L\'EAU'),
            ('sel piscine', 'TRAITEMENT DE L\'EAU'),
            ('uv piscine', 'TRAITEMENT DE L\'EAU'),
            ('stérilisateur', 'TRAITEMENT DE L\'EAU'),
            ('ozonateur', 'TRAITEMENT DE L\'EAU'),
            ('ozone', 'TRAITEMENT DE L\'EAU'),
            ('ioniseur', 'TRAITEMENT DE L\'EAU'),
            ('traitement', 'TRAITEMENT DE L\'EAU'),
            
            # ============================================
            # 09. COUVERTURES
            # ============================================
            ('couverture', 'COUVERTURES'),
            ('bâche', 'COUVERTURES'),
            ('volet', 'COUVERTURES'),
            ('volet roulant', 'COUVERTURES'),
            ('abri piscine', 'COUVERTURES'),
            ('cover', 'COUVERTURES'),
            ('enrouleur', 'COUVERTURES'),
            ('bâche à bulles', 'COUVERTURES'),
            ('bâche hiver', 'COUVERTURES'),
            
            # ============================================
            # 10. MAINTENANCE ET ACCESSOIRES
            # ============================================
            ('épuisette', 'MAINTENANCE ET ACCESSOIRES'),
            ('brosse', 'MAINTENANCE ET ACCESSOIRES'),
            ('balai', 'MAINTENANCE ET ACCESSOIRES'),
            ('manche téléscopique', 'MAINTENANCE ET ACCESSOIRES'),
            ('perche', 'MAINTENANCE ET ACCESSOIRES'),
            ('tuyau flottant', 'MAINTENANCE ET ACCESSOIRES'),
            ('aspirateur manuel', 'MAINTENANCE ET ACCESSOIRES'),
            ('thermomètre', 'MAINTENANCE ET ACCESSOIRES'),
            ('échelle', 'MAINTENANCE ET ACCESSOIRES'),
            ('plongeoir', 'MAINTENANCE ET ACCESSOIRES'),
            ('accessoire', 'MAINTENANCE ET ACCESSOIRES'),
            ('maintenance', 'MAINTENANCE ET ACCESSOIRES'),
            ('entretien', 'MAINTENANCE ET ACCESSOIRES'),
            ('hivernage', 'MAINTENANCE ET ACCESSOIRES'),
            ('douche', 'MAINTENANCE ET ACCESSOIRES'),
            ('alarme piscine', 'MAINTENANCE ET ACCESSOIRES'),
            ('sécurité piscine', 'MAINTENANCE ET ACCESSOIRES'),
            
            # ============================================
            # 11. MATÉRIAUX DE CONNEXION
            # ============================================
            ('pvc pression', 'MATÉRIAUX DE CONNEXION'),
            ('raccord', 'MATÉRIAUX DE CONNEXION'),
            ('coude', 'MATÉRIAUX DE CONNEXION'),
            ('té pvc', 'MATÉRIAUX DE CONNEXION'),
            ('manchon', 'MATÉRIAUX DE CONNEXION'),
            ('réduction', 'MATÉRIAUX DE CONNEXION'),
            ('union', 'MATÉRIAUX DE CONNEXION'),
            ('vanne', 'MATÉRIAUX DE CONNEXION'),
            ('clapet', 'MATÉRIAUX DE CONNEXION'),
            ('tuyau pvc', 'MATÉRIAUX DE CONNEXION'),
            ('tube pvc', 'MATÉRIAUX DE CONNEXION'),
            ('colle pvc', 'MATÉRIAUX DE CONNEXION'),
            ('joint', 'MATÉRIAUX DE CONNEXION'),
            ('flexible', 'MATÉRIAUX DE CONNEXION'),
            ('connexion', 'MATÉRIAUX DE CONNEXION'),
            ('plomberie', 'MATÉRIAUX DE CONNEXION'),
            
            # ============================================
            # 12. IRRIGATION
            # ============================================
            ('irrigation', 'IRRIGATION'),
            ('arrosage', 'IRRIGATION'),
            ('goutte à goutte', 'IRRIGATION'),
            ('asperseur', 'IRRIGATION'),
            ('programmateur arrosage', 'IRRIGATION'),
            ('pompe arrosage', 'IRRIGATION'),
            
            # ============================================
            # POMPES (en dernier pour éviter faux positifs avec PAC)
            # ============================================
            ('pompe', 'POMPES'),
            ('pump', 'POMPES'),
        ]
        
        cat_extraite = self.category.lower() if self.category else ''
        
        # Aussi vérifier le nom du produit pour plus de contexte
        product_name = (self.name or '').lower()
        combined_text = f"{cat_extraite} {product_name}"
        
        pool_cat_name = None
        
        # Chercher une correspondance (ordre de priorité respecté)
        for key, value in category_mapping:
            if key in combined_text:
                pool_cat_name = value
                break
        
        if pool_cat_name:
            # Utiliser product.public.category (catégories e-commerce) avec sudo() pour éviter ACL
            # Recherche flexible avec ilike pour gérer les numéros de préfixe (01., 02., etc.)
            pool_cat = self.env['product.public.category'].sudo().search([('name', 'ilike', pool_cat_name)], limit=1)
            if pool_cat:
                _logger.info(f"Catégorie '{self.category}' mappée vers '{pool_cat.name}'")
                return pool_cat
            _logger.warning(f"Catégorie e-commerce '{pool_cat_name}' non trouvée dans product.public.category")
        else:
            _logger.info(f"Pas de mapping pour la catégorie extraite: {self.category}")
        
        return False
    
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
        Crée un HTML structuré avec description + spécifications techniques adaptées à la catégorie.
        """
        self.ensure_one()
        
        html_parts = []
        
        # Description principale
        if self.description_fr:
            html_parts.append(f'<div class="product-description">')
            html_parts.append(f'<p>{self.description_fr}</p>')
            html_parts.append('</div>')
        
        # Collecter toutes les spécifications disponibles
        specs = []
        
        # =============================================
        # SPÉCIFICATIONS GÉNÉRALES (tous produits)
        # =============================================
        if self.power_kw:
            specs.append(('Puissance', f'{self.power_kw} kW'))
        if hasattr(self, 'power_watts') and self.power_watts:
            specs.append(('Puissance', f'{self.power_watts} W'))
        if self.voltage:
            specs.append(('Tension', f'{self.voltage} V'))
        if hasattr(self, 'amperage') and self.amperage:
            specs.append(('Intensité', f'{self.amperage} A'))
        if self.dimensions:
            specs.append(('Dimensions', self.dimensions))
        if hasattr(self, 'weight') and self.weight:
            specs.append(('Poids', f'{self.weight} kg'))
        if hasattr(self, 'warranty_years') and self.warranty_years:
            specs.append(('Garantie', f'{self.warranty_years} ans'))
        
        # =============================================
        # POMPES À CHALEUR
        # =============================================
        if self.cop:
            specs.append(('COP', str(self.cop)))
        if hasattr(self, 'eer') and self.eer:
            specs.append(('EER', str(self.eer)))
        if self.noise_level:
            specs.append(('Niveau sonore', f'{self.noise_level} dB(A)'))
        if self.refrigerant_gas:
            specs.append(('Gaz réfrigérant', self.refrigerant_gas))
        if self.heating_capacity_min or self.heating_capacity_max:
            heat_str = f"{self.heating_capacity_min or '?'} - {self.heating_capacity_max or '?'} kW"
            specs.append(('Capacité chauffage', heat_str))
        if hasattr(self, 'cooling_capacity') and self.cooling_capacity:
            specs.append(('Capacité refroidissement', f'{self.cooling_capacity} kW'))
        if hasattr(self, 'reversible') and self.reversible:
            specs.append(('Réversible', 'Oui'))
        if hasattr(self, 'defrost_auto') and self.defrost_auto:
            specs.append(('Dégivrage auto', 'Oui'))
        if hasattr(self, 'exchanger_material') and self.exchanger_material:
            specs.append(('Échangeur', self.exchanger_material))
        
        # =============================================
        # POMPES DE FILTRATION
        # =============================================
        if self.flow_rate:
            specs.append(('Débit', f'{self.flow_rate} m³/h'))
        if hasattr(self, 'head_pressure_m') and self.head_pressure_m:
            specs.append(('Hauteur manométrique', f'{self.head_pressure_m} m'))
        if hasattr(self, 'suction_flow_m3h') and self.suction_flow_m3h:
            specs.append(('Débit aspiration', f'{self.suction_flow_m3h} m³/h'))
        if hasattr(self, 'trap_volume_l') and self.trap_volume_l:
            specs.append(('Volume préfiltre', f'{self.trap_volume_l} L'))
        
        # =============================================
        # FILTRES
        # =============================================
        if self.filter_area:
            specs.append(('Surface filtrante', f'{self.filter_area} m²'))
        if hasattr(self, 'filter_capacity_kg') and self.filter_capacity_kg:
            specs.append(('Charge de sable', f'{self.filter_capacity_kg} kg'))
        if hasattr(self, 'fineness_microns') and self.fineness_microns:
            specs.append(('Finesse filtration', f'{self.fineness_microns} µm'))
        if hasattr(self, 'filter_type') and self.filter_type:
            specs.append(('Type de filtre', self.filter_type))
        if hasattr(self, 'filter_media') and self.filter_media:
            specs.append(('Média filtrant', self.filter_media))
        if hasattr(self, 'pressure_bar') and self.pressure_bar:
            specs.append(('Pression max', f'{self.pressure_bar} bar'))
        if hasattr(self, 'backwash_auto') and self.backwash_auto:
            specs.append(('Contre-lavage auto', 'Oui'))
        
        # =============================================
        # ROBOTS NETTOYEURS
        # =============================================
        if hasattr(self, 'cable_length_m') and self.cable_length_m:
            specs.append(('Longueur câble', f'{self.cable_length_m} m'))
        if hasattr(self, 'cycle_time_hours') and self.cycle_time_hours:
            specs.append(('Durée cycle', f'{self.cycle_time_hours} h'))
        if hasattr(self, 'coverage_m2') and self.coverage_m2:
            specs.append(('Surface couverte', f'{self.coverage_m2} m²'))
        if hasattr(self, 'cleaning_width_cm') and self.cleaning_width_cm:
            specs.append(('Largeur nettoyage', f'{self.cleaning_width_cm} cm'))
        if hasattr(self, 'autonomy_hours') and self.autonomy_hours:
            specs.append(('Autonomie', f'{self.autonomy_hours} h'))
        if hasattr(self, 'wall_climbing') and self.wall_climbing:
            specs.append(('Monte aux parois', 'Oui'))
        if hasattr(self, 'waterline_cleaning') and self.waterline_cleaning:
            specs.append(('Ligne d\'eau', 'Oui'))
        if hasattr(self, 'pool_bottom_type') and self.pool_bottom_type:
            specs.append(('Type de fond', self.pool_bottom_type))
        if hasattr(self, 'pool_surface') and self.pool_surface:
            specs.append(('Revêtements compatibles', self.pool_surface))
        
        # =============================================
        # TRAITEMENT DE L'EAU
        # =============================================
        if hasattr(self, 'production_clh_gh') and self.production_clh_gh:
            specs.append(('Production chlore', f'{self.production_clh_gh} g/h'))
        if hasattr(self, 'salt_concentration_gl') and self.salt_concentration_gl:
            specs.append(('Concentration sel', f'{self.salt_concentration_gl} g/L'))
        if hasattr(self, 'ph_range') and self.ph_range:
            specs.append(('Plage pH', self.ph_range))
        if hasattr(self, 'orp_mv') and self.orp_mv:
            specs.append(('ORP', f'{self.orp_mv} mV'))
        if hasattr(self, 'uv_dose') and self.uv_dose:
            specs.append(('Dose UV', f'{self.uv_dose} mJ/cm²'))
        if hasattr(self, 'ozone_production_gh') and self.ozone_production_gh:
            specs.append(('Production ozone', f'{self.ozone_production_gh} g/h'))
        if hasattr(self, 'uv_treatment') and self.uv_treatment:
            specs.append(('Traitement UV', 'Oui'))
        
        # =============================================
        # ÉCLAIRAGE
        # =============================================
        if hasattr(self, 'lumens') and self.lumens:
            specs.append(('Flux lumineux', f'{self.lumens} lm'))
        if hasattr(self, 'color_temperature_k') and self.color_temperature_k:
            specs.append(('Température couleur', f'{self.color_temperature_k} K'))
        if hasattr(self, 'lifespan_hours') and self.lifespan_hours:
            specs.append(('Durée de vie', f'{self.lifespan_hours} h'))
        if hasattr(self, 'ip_rating') and self.ip_rating:
            specs.append(('Indice IP', self.ip_rating))
        if hasattr(self, 'rgb_led') and self.rgb_led:
            specs.append(('LED RGB', 'Oui'))
        if hasattr(self, 'color_modes') and self.color_modes:
            specs.append(('Modes couleur', self.color_modes))
        if hasattr(self, 'transformer_included') and self.transformer_included:
            specs.append(('Transformateur', 'Inclus'))
        if hasattr(self, 'mounting_type') and self.mounting_type:
            specs.append(('Type de montage', self.mounting_type))
        
        # =============================================
        # ACCESSOIRES (ÉCHELLES, PLONGEOIRS, etc.)
        # =============================================
        if hasattr(self, 'material') and self.material:
            specs.append(('Matériau', self.material))
        if hasattr(self, 'steps_count') and self.steps_count:
            specs.append(('Nombre de marches', str(self.steps_count)))
        if hasattr(self, 'max_load_kg') and self.max_load_kg:
            specs.append(('Charge max', f'{self.max_load_kg} kg'))
        if hasattr(self, 'thickness_mm') and self.thickness_mm:
            specs.append(('Épaisseur', f'{self.thickness_mm} mm'))
        if hasattr(self, 'color') and self.color:
            specs.append(('Couleur', self.color))
        
        # =============================================
        # CONNECTIVITÉ & COMPATIBILITÉ
        # =============================================
        if self.wifi_compatible:
            specs.append(('WiFi', 'Compatible'))
        if hasattr(self, 'bluetooth_compatible') and self.bluetooth_compatible:
            specs.append(('Bluetooth', 'Compatible'))
        if hasattr(self, 'app_control') and self.app_control:
            specs.append(('Application', self.app_control))
        if hasattr(self, 'remote_control') and self.remote_control:
            specs.append(('Télécommande', 'Incluse'))
        if hasattr(self, 'programmable') and self.programmable:
            specs.append(('Programmable', 'Oui'))
        
        # =============================================
        # PISCINE COMPATIBLE
        # =============================================
        if self.pool_volume_min or self.pool_volume_max:
            vol_str = f"{self.pool_volume_min or '?'} - {self.pool_volume_max or '?'} m³"
            specs.append(('Volume piscine', vol_str))
        if hasattr(self, 'pool_type') and self.pool_type:
            specs.append(('Type piscine', self.pool_type))
        if self.operating_temp_min is not None or self.operating_temp_max is not None:
            temp_str = f"{self.operating_temp_min or '?'}°C à {self.operating_temp_max or '?'}°C"
            specs.append(('Température fonctionnement', temp_str))
        if self.power_supply:
            specs.append(('Alimentation', self.power_supply))
        if self.water_connection:
            specs.append(('Connexion eau', self.water_connection))
        if self.energy_class:
            specs.append(('Classe énergétique', self.energy_class))
        if self.product_type:
            specs.append(('Technologie', self.product_type))
        if self.installation_type:
            specs.append(('Installation', self.installation_type))
        
        # Certifications
        if hasattr(self, 'safety_certified') and self.safety_certified:
            specs.append(('Certifications', self.safety_certified))
        
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
        Trouve ou crée les catégories e-commerce publiques correspondant à la catégorie détectée.
        
        Stratégie:
        1. Identifier la catégorie PRINCIPALE parmi les 12 existantes
        2. Si pertinent, créer une SOUS-CATÉGORIE plus spécifique
        3. Retourner l'ID de la sous-catégorie (ou de la principale si pas de sous-cat)
        
        Catégories principales existantes:
        01. ROBOTS DE PISCINE
        02. CONSTRUCTION
        03. ÉCLAIRAGE
        04. POMPES
        05. FILTRATION
        06. CHAUFFAGE
        07. TECHNIQUE DE MESURE ET DE CONTRÔLE / PRODUITS CHIMIQUES
        08. TECHNIQUE DE TRAITEMENT DE L'EAU
        09. COUVERTURES
        10. MAINTENANCE ET ACCESSOIRES
        11. MATÉRIAUX DE CONNEXION
        12. IRRIGATION
        """
        if not category_name:
            return []
        
        PublicCategory = self.env['product.public.category'].sudo()
        
        # Normaliser et combiner catégorie + nom produit pour meilleure détection
        cat_lower = category_name.lower() if category_name else ''
        product_name = (self.name or '').lower()
        combined_text = f"{cat_lower} {product_name}"
        
        # Mapping: (mot-clé, catégorie_principale, sous_catégorie_à_créer)
        # Si sous_catégorie est None, on utilise uniquement la catégorie principale
        category_mapping = [
            # ============================================
            # 01. ROBOTS DE PISCINE
            # ============================================
            ('robot électrique', 'ROBOTS DE PISCINE', 'Robots électriques'),
            ('robot hydraulique', 'ROBOTS DE PISCINE', 'Robots hydrauliques'),
            ('robot à pression', 'ROBOTS DE PISCINE', 'Robots à pression'),
            ('robot', 'ROBOTS DE PISCINE', None),
            ('nettoyeur automatique', 'ROBOTS DE PISCINE', None),
            ('aspirateur piscine', 'ROBOTS DE PISCINE', 'Aspirateurs'),
            ('cleaner', 'ROBOTS DE PISCINE', None),
            ('dolphin', 'ROBOTS DE PISCINE', 'Robots électriques'),
            ('polaris', 'ROBOTS DE PISCINE', 'Robots à pression'),
            ('zodiac', 'ROBOTS DE PISCINE', None),
            
            # ============================================
            # 02. CONSTRUCTION
            # ============================================
            ('liner', 'CONSTRUCTION', 'Liners'),
            ('membrane', 'CONSTRUCTION', 'Membranes & Étanchéité'),
            ('skimmer', 'CONSTRUCTION', 'Pièces à sceller'),
            ('bonde de fond', 'CONSTRUCTION', 'Pièces à sceller'),
            ('refoulement', 'CONSTRUCTION', 'Pièces à sceller'),
            ('buse', 'CONSTRUCTION', 'Pièces à sceller'),
            ('prise balai', 'CONSTRUCTION', 'Pièces à sceller'),
            ('pièce à sceller', 'CONSTRUCTION', 'Pièces à sceller'),
            ('margelle', 'CONSTRUCTION', 'Margelles & Dalles'),
            ('dalle', 'CONSTRUCTION', 'Margelles & Dalles'),
            ('escalier piscine', 'CONSTRUCTION', 'Escaliers'),
            ('bloc polystyrène', 'CONSTRUCTION', 'Blocs & Structure'),
            ('coffrage', 'CONSTRUCTION', 'Blocs & Structure'),
            ('construction', 'CONSTRUCTION', None),
            ('rénovation', 'CONSTRUCTION', None),
            ('étanchéité', 'CONSTRUCTION', 'Membranes & Étanchéité'),
            
            # ============================================
            # 03. ÉCLAIRAGE
            # ============================================
            ('projecteur led', 'ÉCLAIRAGE', 'Projecteurs LED'),
            ('projecteur', 'ÉCLAIRAGE', 'Projecteurs'),
            ('spot', 'ÉCLAIRAGE', 'Spots encastrés'),
            ('ampoule', 'ÉCLAIRAGE', 'Ampoules & Pièces'),
            ('transformateur', 'ÉCLAIRAGE', 'Transformateurs'),
            ('niche', 'ÉCLAIRAGE', 'Niches & Supports'),
            ('éclairage', 'ÉCLAIRAGE', None),
            ('eclairage', 'ÉCLAIRAGE', None),
            ('led piscine', 'ÉCLAIRAGE', 'Projecteurs LED'),
            ('luminaire', 'ÉCLAIRAGE', None),
            
            # ============================================
            # 04. POMPES
            # ============================================
            ('pompe de filtration', 'POMPES', 'Pompes de filtration'),
            ('pompe filtration', 'POMPES', 'Pompes de filtration'),
            ('pompe de circulation', 'POMPES', 'Pompes de circulation'),
            ('pompe à vitesse variable', 'POMPES', 'Pompes à vitesse variable'),
            ('pompe variable', 'POMPES', 'Pompes à vitesse variable'),
            ('pompe auto-amorçante', 'POMPES', 'Pompes auto-amorçantes'),
            ('surpresseur', 'POMPES', 'Surpresseurs'),
            ('pompe doseuse', 'POMPES', 'Pompes doseuses'),
            ('nage contre courant', 'POMPES', 'Nage contre-courant'),
            ('contre-courant', 'POMPES', 'Nage contre-courant'),
            
            # ============================================
            # 05. FILTRATION
            # ============================================
            ('préfiltre', 'FILTRATION', 'Préfiltres'),
            ('pré-filtre', 'FILTRATION', 'Préfiltres'),
            ('multicyclone', 'FILTRATION', 'Préfiltres'),
            ('hydrospin', 'FILTRATION', 'Préfiltres'),
            ('filtre à sable', 'FILTRATION', 'Filtres à sable'),
            ('filtre sable', 'FILTRATION', 'Filtres à sable'),
            ('filtre à cartouche', 'FILTRATION', 'Filtres à cartouche'),
            ('filtre cartouche', 'FILTRATION', 'Filtres à cartouche'),
            ('filtre à diatomées', 'FILTRATION', 'Filtres à diatomées'),
            ('filtre diatomée', 'FILTRATION', 'Filtres à diatomées'),
            ('verre filtrant', 'FILTRATION', 'Média filtrant'),
            ('média filtrant', 'FILTRATION', 'Média filtrant'),
            ('zéolite', 'FILTRATION', 'Média filtrant'),
            ('sable filtration', 'FILTRATION', 'Média filtrant'),
            ('cartouche filtrante', 'FILTRATION', 'Cartouches filtrantes'),
            ('vanne multivoies', 'FILTRATION', 'Vannes & Accessoires'),
            ('vanne 6 voies', 'FILTRATION', 'Vannes & Accessoires'),
            ('crépine', 'FILTRATION', 'Pièces détachées filtration'),
            ('manomètre', 'FILTRATION', 'Pièces détachées filtration'),
            ('filtration', 'FILTRATION', None),
            ('filtre', 'FILTRATION', None),
            
            # ============================================
            # 06. CHAUFFAGE
            # ============================================
            ('pompe à chaleur', 'CHAUFFAGE', 'Pompes à chaleur'),
            ('pompes à chaleur', 'CHAUFFAGE', 'Pompes à chaleur'),
            ('pac', 'CHAUFFAGE', 'Pompes à chaleur'),
            ('heat pump', 'CHAUFFAGE', 'Pompes à chaleur'),
            ('réchauffeur électrique', 'CHAUFFAGE', 'Réchauffeurs électriques'),
            ('réchauffeur', 'CHAUFFAGE', 'Réchauffeurs électriques'),
            ('échangeur thermique', 'CHAUFFAGE', 'Échangeurs thermiques'),
            ('échangeur', 'CHAUFFAGE', 'Échangeurs thermiques'),
            ('chauffage solaire', 'CHAUFFAGE', 'Chauffage solaire'),
            ('capteur solaire', 'CHAUFFAGE', 'Chauffage solaire'),
            ('chauffage', 'CHAUFFAGE', None),
            
            # ============================================
            # 07. TECHNIQUE DE MESURE ET DE CONTRÔLE / PRODUITS CHIMIQUES
            # ============================================
            ('testeur', 'TECHNIQUE DE MESURE', 'Analyse & Test'),
            ('photomètre', 'TECHNIQUE DE MESURE', 'Analyse & Test'),
            ('bandelette', 'TECHNIQUE DE MESURE', 'Analyse & Test'),
            ('trousse analyse', 'TECHNIQUE DE MESURE', 'Analyse & Test'),
            ('analyse', 'TECHNIQUE DE MESURE', 'Analyse & Test'),
            ('ph-mètre', 'TECHNIQUE DE MESURE', 'Sondes & Capteurs'),
            ('sonde', 'TECHNIQUE DE MESURE', 'Sondes & Capteurs'),
            ('capteur', 'TECHNIQUE DE MESURE', 'Sondes & Capteurs'),
            ('régulateur', 'TECHNIQUE DE MESURE', 'Régulateurs automatiques'),
            ('contrôleur', 'TECHNIQUE DE MESURE', 'Régulateurs automatiques'),
            ('domotique', 'TECHNIQUE DE MESURE', 'Domotique piscine'),
            ('coffret électrique', 'TECHNIQUE DE MESURE', 'Coffrets électriques'),
            ('chlore', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            ('brome', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            ('algicide', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            ('floculant', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            ('ph+', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            ('ph-', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            ('produit chimique', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            ('chimie', 'TECHNIQUE DE MESURE', 'Produits chimiques'),
            
            # ============================================
            # 08. TECHNIQUE DE TRAITEMENT DE L'EAU
            # ============================================
            ('électrolyseur', 'TRAITEMENT DE L\'EAU', 'Électrolyseurs au sel'),
            ('électrolyse', 'TRAITEMENT DE L\'EAU', 'Électrolyseurs au sel'),
            ('cellule', 'TRAITEMENT DE L\'EAU', 'Cellules & Pièces'),
            ('sel piscine', 'TRAITEMENT DE L\'EAU', 'Électrolyseurs au sel'),
            ('uv piscine', 'TRAITEMENT DE L\'EAU', 'Traitement UV'),
            ('stérilisateur', 'TRAITEMENT DE L\'EAU', 'Traitement UV'),
            ('ozonateur', 'TRAITEMENT DE L\'EAU', 'Traitement ozone'),
            ('ozone', 'TRAITEMENT DE L\'EAU', 'Traitement ozone'),
            ('ioniseur', 'TRAITEMENT DE L\'EAU', 'Ioniseurs'),
            ('traitement', 'TRAITEMENT DE L\'EAU', None),
            
            # ============================================
            # 09. COUVERTURES
            # ============================================
            ('volet roulant', 'COUVERTURES', 'Volets roulants'),
            ('volet', 'COUVERTURES', 'Volets roulants'),
            ('bâche à bulles', 'COUVERTURES', 'Bâches à bulles'),
            ('bâche été', 'COUVERTURES', 'Bâches à bulles'),
            ('bâche hiver', 'COUVERTURES', 'Bâches hivernage'),
            ('bâche à barres', 'COUVERTURES', 'Couvertures à barres'),
            ('couverture à barres', 'COUVERTURES', 'Couvertures à barres'),
            ('enrouleur', 'COUVERTURES', 'Enrouleurs'),
            ('abri piscine', 'COUVERTURES', 'Abris'),
            ('couverture', 'COUVERTURES', None),
            ('bâche', 'COUVERTURES', None),
            ('cover', 'COUVERTURES', None),
            
            # ============================================
            # 10. MAINTENANCE ET ACCESSOIRES
            # ============================================
            ('épuisette', 'MAINTENANCE ET ACCESSOIRES', 'Nettoyage manuel'),
            ('brosse', 'MAINTENANCE ET ACCESSOIRES', 'Nettoyage manuel'),
            ('balai', 'MAINTENANCE ET ACCESSOIRES', 'Nettoyage manuel'),
            ('manche téléscopique', 'MAINTENANCE ET ACCESSOIRES', 'Nettoyage manuel'),
            ('perche', 'MAINTENANCE ET ACCESSOIRES', 'Nettoyage manuel'),
            ('aspirateur manuel', 'MAINTENANCE ET ACCESSOIRES', 'Nettoyage manuel'),
            ('échelle', 'MAINTENANCE ET ACCESSOIRES', 'Échelles & Plongeoirs'),
            ('plongeoir', 'MAINTENANCE ET ACCESSOIRES', 'Échelles & Plongeoirs'),
            ('main courante', 'MAINTENANCE ET ACCESSOIRES', 'Échelles & Plongeoirs'),
            ('thermomètre', 'MAINTENANCE ET ACCESSOIRES', 'Accessoires divers'),
            ('douche', 'MAINTENANCE ET ACCESSOIRES', 'Douches & Pédiluves'),
            ('lave-pieds', 'MAINTENANCE ET ACCESSOIRES', 'Douches & Pédiluves'),
            ('pédiluve', 'MAINTENANCE ET ACCESSOIRES', 'Douches & Pédiluves'),
            ('alarme', 'MAINTENANCE ET ACCESSOIRES', 'Sécurité piscine'),
            ('barrière', 'MAINTENANCE ET ACCESSOIRES', 'Sécurité piscine'),
            ('sécurité', 'MAINTENANCE ET ACCESSOIRES', 'Sécurité piscine'),
            ('hivernage', 'MAINTENANCE ET ACCESSOIRES', 'Hivernage'),
            ('gizzmo', 'MAINTENANCE ET ACCESSOIRES', 'Hivernage'),
            ('flotteur', 'MAINTENANCE ET ACCESSOIRES', 'Hivernage'),
            ('jeux', 'MAINTENANCE ET ACCESSOIRES', 'Jeux & Loisirs'),
            ('bouée', 'MAINTENANCE ET ACCESSOIRES', 'Jeux & Loisirs'),
            ('matelas', 'MAINTENANCE ET ACCESSOIRES', 'Jeux & Loisirs'),
            ('accessoire', 'MAINTENANCE ET ACCESSOIRES', None),
            ('maintenance', 'MAINTENANCE ET ACCESSOIRES', None),
            ('entretien', 'MAINTENANCE ET ACCESSOIRES', None),
            
            # ============================================
            # 11. MATÉRIAUX DE CONNEXION
            # ============================================
            ('tuyau pvc', 'MATÉRIAUX DE CONNEXION', 'Tuyauterie PVC'),
            ('tube pvc', 'MATÉRIAUX DE CONNEXION', 'Tuyauterie PVC'),
            ('pvc pression', 'MATÉRIAUX DE CONNEXION', 'Tuyauterie PVC'),
            ('raccord', 'MATÉRIAUX DE CONNEXION', 'Raccords'),
            ('coude', 'MATÉRIAUX DE CONNEXION', 'Raccords'),
            ('manchon', 'MATÉRIAUX DE CONNEXION', 'Raccords'),
            ('réduction', 'MATÉRIAUX DE CONNEXION', 'Raccords'),
            ('union', 'MATÉRIAUX DE CONNEXION', 'Raccords'),
            ('té pvc', 'MATÉRIAUX DE CONNEXION', 'Raccords'),
            ('vanne', 'MATÉRIAUX DE CONNEXION', 'Vannes'),
            ('clapet', 'MATÉRIAUX DE CONNEXION', 'Vannes'),
            ('colle pvc', 'MATÉRIAUX DE CONNEXION', 'Colles & Joints'),
            ('joint', 'MATÉRIAUX DE CONNEXION', 'Colles & Joints'),
            ('flexible', 'MATÉRIAUX DE CONNEXION', 'Flexibles'),
            ('connexion', 'MATÉRIAUX DE CONNEXION', None),
            ('plomberie', 'MATÉRIAUX DE CONNEXION', None),
            
            # ============================================
            # 12. IRRIGATION
            # ============================================
            ('arrosage', 'IRRIGATION', 'Arrosage'),
            ('goutte à goutte', 'IRRIGATION', 'Goutte à goutte'),
            ('asperseur', 'IRRIGATION', 'Asperseurs'),
            ('programmateur arrosage', 'IRRIGATION', 'Programmateurs'),
            ('irrigation', 'IRRIGATION', None),
            
            # ============================================
            # POMPES (en dernier pour éviter faux positifs avec PAC)
            # ============================================
            ('pompe', 'POMPES', None),
            ('pump', 'POMPES', None),
        ]
        
        main_category_name = None
        sub_category_name = None
        
        # Chercher une correspondance
        for keyword, main_cat, sub_cat in category_mapping:
            if keyword in combined_text:
                main_category_name = main_cat
                sub_category_name = sub_cat
                break
        
        # Si pas de match, utiliser MAINTENANCE ET ACCESSOIRES par défaut
        if not main_category_name:
            main_category_name = 'MAINTENANCE ET ACCESSOIRES'
            _logger.info(f"Pas de mapping pour '{category_name}', utilisation de la catégorie par défaut")
        
        # 1. Trouver la catégorie PRINCIPALE (doit exister)
        main_category = PublicCategory.search([('name', 'ilike', main_category_name)], limit=1)
        
        if not main_category:
            _logger.warning(f"Catégorie principale '{main_category_name}' non trouvée !")
            return []
        
        _logger.info(f"Catégorie principale trouvée: '{main_category.name}' (ID: {main_category.id})")
        
        # 2. Si on a une sous-catégorie à créer/trouver
        if sub_category_name:
            # Chercher si la sous-catégorie existe déjà
            sub_category = PublicCategory.search([
                ('name', '=', sub_category_name),
                ('parent_id', '=', main_category.id)
            ], limit=1)
            
            if not sub_category:
                # Créer la sous-catégorie
                try:
                    sub_category = PublicCategory.create({
                        'name': sub_category_name,
                        'parent_id': main_category.id,
                    })
                    _logger.info(f"✅ Sous-catégorie créée: '{sub_category_name}' sous '{main_category.name}' (ID: {sub_category.id})")
                except Exception as e:
                    _logger.warning(f"Impossible de créer la sous-catégorie '{sub_category_name}': {e}")
                    # Fallback: utiliser la catégorie principale
                    return [main_category.id]
            else:
                _logger.info(f"Sous-catégorie existante: '{sub_category.name}' (ID: {sub_category.id})")
            
            return [sub_category.id]
        
        # Pas de sous-catégorie, retourner la catégorie principale
        return [main_category.id]
    
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
