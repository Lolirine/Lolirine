from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

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
            'list_price': data.get('sellingPrice', 0),
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
