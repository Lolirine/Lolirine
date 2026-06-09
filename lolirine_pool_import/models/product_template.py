from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Lien vers les extractions
    x_pool_extraction_count = fields.Integer(
        string="Extractions",
        compute='_compute_extraction_count',
    )
    
    @api.depends_context('uid')
    def _compute_extraction_count(self):
        """Compte les extractions liées via pool.catalog.extraction.product"""
        ExtractionProduct = self.env['pool.catalog.extraction.product']
        for product in self:
            product.x_pool_extraction_count = ExtractionProduct.search_count([
                ('product_id', '=', product.id)
            ])
    
    def action_view_extractions(self):
        """Ouvre les extractions liées à ce produit"""
        self.ensure_one()
        extraction_products = self.env['pool.catalog.extraction.product'].search([
            ('product_id', '=', self.id)
        ])
        extraction_ids = extraction_products.mapped('extraction_id').ids
        
        if len(extraction_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pool.catalog.extraction',
                'res_id': extraction_ids[0],
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': f'Extractions - {self.name}',
            'res_model': 'pool.catalog.extraction',
            'view_mode': 'list,form',
            'domain': [('id', 'in', extraction_ids)],
            'target': 'current',
        }
    
    def action_open_in_extractor(self):
        """Ouvre le produit dans l'Extracteur IA pour re-cadrer les images.
        Si une extraction existe déjà, l'ouvre. Sinon, en crée une nouvelle."""
        self.ensure_one()
        
        # Chercher une extraction existante
        extraction_product = self.env['pool.catalog.extraction.product'].search([
            ('product_id', '=', self.id)
        ], limit=1, order='create_date desc')
        
        if extraction_product and extraction_product.extraction_id:
            extraction = extraction_product.extraction_id
            _logger.info(f"Re-ouverture extraction {extraction.id} pour produit {self.name}")
        else:
            # Créer une nouvelle extraction depuis l'image du produit
            extraction = self._create_extraction_from_product()
            if not extraction:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Pas d\'image',
                        'message': f'Le produit "{self.name}" n\'a pas d\'image pour créer une extraction.',
                        'type': 'warning',
                    }
                }
        
        # Ouvrir dans l'extracteur IA (client action)
        return {
            'type': 'ir.actions.client',
            'tag': 'pool_catalog_extractor',
            'params': {
                'extraction_id': extraction.id,
            },
        }
    
    def action_view_extraction_form(self):
        """Ouvre l'extraction liée en vue formulaire pour utiliser ImageCropSelector"""
        self.ensure_one()
        
        extraction_product = self.env['pool.catalog.extraction.product'].search([
            ('product_id', '=', self.id)
        ], limit=1, order='create_date desc')
        
        if extraction_product and extraction_product.extraction_id:
            extraction = extraction_product.extraction_id
        else:
            extraction = self._create_extraction_from_product()
            if not extraction:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Pas d\'image',
                        'message': f'Le produit "{self.name}" n\'a pas d\'image.',
                        'type': 'warning',
                    }
                }
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pool.catalog.extraction',
            'res_id': extraction.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_extraction_from_product(self):
        """Crée une extraction depuis un produit existant pour re-traitement d'images"""
        self.ensure_one()
        
        if not self.image_1920:
            return False
        
        supplier = self.x_pool_supplier_id or False
        
        extraction = self.env['pool.catalog.extraction'].create({
            'image': self.image_1920,
            'image_filename': f'{self.default_code or self.name}.png',
            'supplier_id': supplier.id if supplier else False,
            'state': 'extracted',
            'extraction_type': 'single',
            'notes': f'Re-extraction depuis produit existant: {self.name} (ID: {self.id})',
        })
        
        # Créer le produit d'extraction lié
        self.env['pool.catalog.extraction.product'].create({
            'extraction_id': extraction.id,
            'name': self.name,
            'reference': self.default_code or '',
            'brand': self.x_pool_brand or '',
            'category': self.x_pool_category or '',
            'purchase_price': self.standard_price,
            'selling_price': self.list_price,
            'description_fr': self.x_description_fr or self.description_sale or '',
            'state': 'imported',
            'product_id': self.id,
            'product_image': self.image_1920,
        })
        
        _logger.info(f"Extraction {extraction.id} créée depuis produit {self.name} (ID: {self.id})")
        return extraction
    
    def action_batch_create_reextraction(self):
        """Action serveur : crée des extractions pour les produits sélectionnés"""
        created = 0
        skipped_no_image = 0
        skipped_has_extraction = 0
        
        for product in self:
            # Vérifier s'il a déjà une extraction
            existing = self.env['pool.catalog.extraction.product'].search_count([
                ('product_id', '=', product.id)
            ])
            if existing:
                skipped_has_extraction += 1
                continue
            
            extraction = product._create_extraction_from_product()
            if extraction:
                created += 1
            else:
                skipped_no_image += 1
        
        msg_parts = []
        if created:
            msg_parts.append(f'{created} extraction(s) créée(s)')
        if skipped_has_extraction:
            msg_parts.append(f'{skipped_has_extraction} déjà avec extraction')
        if skipped_no_image:
            msg_parts.append(f'{skipped_no_image} sans image')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Re-extraction en lot',
                'message': ' | '.join(msg_parts) if msg_parts else 'Aucun produit traité',
                'type': 'success' if created else 'warning',
                'sticky': False,
            }
        }

    @api.model
    def action_sync_website_products(self):
        """Synchronise les produits du site web piscine dans le module.
        Trouve les produits publiés sur le pool store et les tague si nécessaire."""
        Website = self.env['website'].sudo()
        
        # Trouver le website pool store
        pool_website = Website.search([
            '|', '|', '|',
            ('name', 'ilike', 'pool store'),
            ('name', 'ilike', 'poolstore'),
            ('name', 'ilike', 'pool'),
            ('domain', 'ilike', 'poolstore'),
        ], limit=1)
        
        if not pool_website:
            pool_website = Website.search([
                ('name', 'ilike', 'lolirine'),
            ], limit=1)
        
        if not pool_website:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Website non trouvé',
                    'message': 'Impossible de trouver le site web Pool Store.',
                    'type': 'warning',
                }
            }
        
        # Trouver les produits publiés sur ce website sans x_pool_import_source
        domain = [
            ('website_id', '=', pool_website.id),
            ('is_published', '=', True),
            ('x_pool_import_source', '=', False),
        ]
        
        products_to_tag = self.search(domain)
        tagged = 0
        
        for product in products_to_tag:
            vals = {
                'x_pool_import_source': f'Website sync - {pool_website.name}',
            }
            if not product.x_pool_import_date:
                vals['x_pool_import_date'] = fields.Datetime.now()
            product.write(vals)
            tagged += 1
        
        # Compter le total
        total = self.search_count([
            '|',
            ('x_pool_supplier_id', '!=', False),
            ('x_pool_import_source', '!=', False),
        ])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Synchronisation terminée',
                'message': f'{tagged} nouveau(x) produit(s) tagué(s) depuis {pool_website.name}. Total: {total} produits piscine.',
                'type': 'success',
                'sticky': False,
            }
        }

    # Champs spécifiques piscine
    x_pool_supplier_id = fields.Many2one(
        'pool.supplier', string='Fournisseur Piscine',
        tracking=True
    )
    x_pool_supplier_ref = fields.Char(
        string='Réf. Fournisseur',
        tracking=True,
        index=True
    )
    x_pool_brand = fields.Char(string='Marque', tracking=True)
    x_pool_category = fields.Char(string='Catégorie Catalogue')
    x_pool_subcategory = fields.Char(string='Sous-catégorie Catalogue')
    
    # Descriptions multilingues
    x_description_fr = fields.Text(string='Description FR')
    x_description_nl = fields.Text(string='Description NL')
    
    # Import metadata
    x_pool_import_date = fields.Datetime(string="Date d'import")
    x_pool_import_source = fields.Char(string="Source d'import")
    x_pool_original_data = fields.Text(string='Données originales (JSON)')
    
    # Spécifications techniques extraites
    x_power_kw = fields.Float(string='Puissance (kW)')
    x_power_cv = fields.Char(string='Puissance (CV)')
    x_voltage = fields.Integer(string='Tension (V)')
    x_flow_rate = fields.Float(string='Débit (m³/h)')
    x_diameter_mm = fields.Integer(string='Diamètre (mm)')
    x_filter_area = fields.Float(string='Surface filtrante (m²)')
    x_cop = fields.Float(string='COP')
    x_noise_level = fields.Float(string='Niveau sonore (dB)')
    
    # Calculs de rentabilité
    x_purchase_margin = fields.Float(
        string='Marge (%)',
        compute='_compute_margin',
        store=True
    )
    x_profit_amount = fields.Monetary(
        string='Profit',
        compute='_compute_margin',
        store=True,
        currency_field='currency_id'
    )
    
    @api.depends('list_price', 'standard_price')
    def _compute_margin(self):
        for product in self:
            if product.list_price and product.list_price > 0:
                product.x_purchase_margin = ((product.list_price - product.standard_price) / product.list_price) * 100
                product.x_profit_amount = product.list_price - product.standard_price
            else:
                product.x_purchase_margin = 0
                product.x_profit_amount = 0
    
    @api.model
    def create_from_fluidra_import(self, data, supplier):
        """Crée un produit depuis les données d'import Fluidra"""
        # Recherche ou création de la catégorie
        category = self._get_or_create_category(data.get('category'), supplier)
        
        vals = {
            'name': data.get('name'),
            'default_code': f"POOL-{data.get('ref')}",
            'x_pool_supplier_id': supplier.id,
            'x_pool_supplier_ref': data.get('ref'),
            'x_pool_brand': data.get('brand'),
            'x_pool_category': data.get('category'),
            'x_pool_subcategory': data.get('subCategory'),
            'x_description_fr': data.get('descriptionFr'),
            'x_description_nl': data.get('descriptionNl'),
            'description_sale': data.get('descriptionFr'),
            'standard_price': data.get('purchasePrice', 0),
            'list_price': data.get('sellingPrice') or (
                round(supplier.calculate_sale_price(data.get('purchasePrice', 0)), 2)
                if supplier and data.get('purchasePrice') else 0),
            'is_pool_product': True,
            'categ_id': category.id if category else False,
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
            'x_pool_import_date': fields.Datetime.now(),
            'x_pool_import_source': 'Fluidra Extractor',
        }
        
        # Ajout des attributs techniques
        attributes = data.get('attributes', {})
        if attributes.get('power_kw'):
            vals['x_power_kw'] = attributes['power_kw']
        if attributes.get('power_cv'):
            vals['x_power_cv'] = attributes['power_cv']
        if attributes.get('voltage'):
            vals['x_voltage'] = attributes['voltage']
        if attributes.get('flow'):
            vals['x_flow_rate'] = attributes['flow']
        if attributes.get('diameter'):
            vals['x_diameter_mm'] = attributes['diameter']
        if attributes.get('filter_area'):
            vals['x_filter_area'] = attributes['filter_area']
        if attributes.get('cop'):
            vals['x_cop'] = attributes['cop']
        if attributes.get('noise'):
            vals['x_noise_level'] = attributes['noise']
        
        return self.create(vals)
    
    def _get_or_create_category(self, category_name, supplier):
        """Récupère ou crée la catégorie produit"""
        if not category_name:
            return False
        
        # Chercher dans le mapping du fournisseur
        mapping = self.env['pool.supplier.category.mapping'].search([
            ('supplier_id', '=', supplier.id),
            ('supplier_category', '=', category_name)
        ], limit=1)
        
        if mapping:
            return mapping.odoo_category_id
        
        # Chercher ou créer la catégorie
        category = self.env['product.category'].search([
            ('name', '=', category_name)
        ], limit=1)
        
        if not category:
            parent = self.env.ref('lolirine_pool_import.product_category_pool', raise_if_not_found=False)
            category = self.env['product.category'].create({
                'name': category_name,
                'parent_id': parent.id if parent else False,
            })
        
        return category
    
    @api.model
    def create_template_with_variants(self, template_data, supplier):
        """Crée un product.template avec ses variantes depuis l'import"""
        # Créer ou récupérer les attributs
        attribute_lines = []
        for attr_data in template_data.get('attributes', []):
            attribute = self._get_or_create_attribute(attr_data)
            value_ids = []
            
            for value in attr_data.get('values', []):
                attr_value = self._get_or_create_attribute_value(attribute, str(value))
                value_ids.append(attr_value.id)
            
            attribute_lines.append((0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, value_ids)],
            }))
        
        # Créer le template
        category = self._get_or_create_category(template_data.get('category'), supplier)
        base_variant = template_data.get('variants', [{}])[0]
        
        template_vals = {
            'name': template_data.get('name'),
            'default_code': f"POOL-TPL-{template_data.get('id')}",
            'x_pool_supplier_id': supplier.id,
            'x_pool_brand': template_data.get('brand'),
            'x_pool_category': template_data.get('category'),
            'x_pool_subcategory': template_data.get('subCategory'),
            'categ_id': category.id if category else False,
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
            'standard_price': base_variant.get('purchasePrice', 0),
            'list_price': base_variant.get('sellingPrice', 0),
            'attribute_line_ids': attribute_lines,
            'x_pool_import_date': fields.Datetime.now(),
            'x_pool_import_source': 'Fluidra Extractor - Template',
        }
        
        template = self.create(template_vals)
        
        # Mettre à jour les prix des variantes
        for variant_data in template_data.get('variants', []):
            self._update_variant_prices(template, variant_data)
        
        return template
    
    def _get_or_create_attribute(self, attr_data):
        """Récupère ou crée un attribut de produit"""
        Attribute = self.env['product.attribute']
        
        attribute = Attribute.search([
            ('name', '=', attr_data.get('name'))
        ], limit=1)
        
        if not attribute:
            attribute = Attribute.create({
                'name': attr_data.get('name'),
                'display_type': 'radio',
                'create_variant': 'always',
            })
        
        return attribute
    
    def _get_or_create_attribute_value(self, attribute, value_name):
        """Récupère ou crée une valeur d'attribut"""
        AttributeValue = self.env['product.attribute.value']
        
        attr_value = AttributeValue.search([
            ('attribute_id', '=', attribute.id),
            ('name', '=', value_name)
        ], limit=1)
        
        if not attr_value:
            attr_value = AttributeValue.create({
                'attribute_id': attribute.id,
                'name': value_name,
            })
        
        return attr_value
    
    def _update_variant_prices(self, template, variant_data):
        """Met à jour les prix d'une variante spécifique"""
        # Trouver la variante correspondante par ses attributs
        attr_values = variant_data.get('attributeValues', {})
        
        for variant in template.product_variant_ids:
            # Vérifier si cette variante correspond aux valeurs d'attributs
            match = True
            for attr_key, attr_value in attr_values.items():
                variant_value = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.name.lower().replace(' ', '_').startswith(attr_key)
                )
                if variant_value and str(attr_value) not in variant_value.mapped('name'):
                    match = False
                    break
            
            if match:
                variant.write({
                    'default_code': f"POOL-{variant_data.get('ref')}",
                    'standard_price': variant_data.get('purchasePrice', 0),
                    # Note: list_price est géré au niveau template + extra_price
                })
                break
