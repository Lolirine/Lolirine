import base64
import json
import csv
import io
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PoolImportWizard(models.TransientModel):
    _name = 'pool.import.wizard'
    _description = "Assistant d'import Fluidra"

    supplier_id = fields.Many2one(
        'pool.supplier', string='Fournisseur',
        required=True,
        default=lambda self: self.env['pool.supplier'].search([('code', '=', 'fluidra')], limit=1)
    )
    
    source_type = fields.Selection([
        ('json', 'JSON (Export complet de l\'extracteur)'),
        ('csv_products', 'CSV Produits simples'),
        ('csv_templates', 'CSV Templates avec variantes'),
    ], string="Type d'import", required=True, default='json')
    
    import_file = fields.Binary(string='Fichier', required=True)
    import_filename = fields.Char(string='Nom du fichier')
    
    # Options
    update_existing = fields.Boolean(
        string='Mettre à jour les produits existants',
        default=True,
        help="Si coché, les produits avec la même référence fournisseur seront mis à jour"
    )
    recalculate_prices = fields.Boolean(
        string='Recalculer les prix de vente',
        default=False,
        help="Recalcule les prix selon la marge du fournisseur"
    )
    import_templates = fields.Boolean(
        string='Importer les templates avec variantes',
        default=True,
        help="Crée les product.template avec attributs et variantes"
    )
    
    # Prévisualisation
    preview_line_ids = fields.One2many(
        'pool.import.wizard.line', 'wizard_id',
        string='Aperçu'
    )
    preview_count = fields.Integer(string='Produits à importer', compute='_compute_preview_count')
    preview_templates_count = fields.Integer(string='Templates à créer', compute='_compute_preview_count')
    
    @api.depends('preview_line_ids')
    def _compute_preview_count(self):
        for wizard in self:
            wizard.preview_count = len(wizard.preview_line_ids.filtered(lambda l: not l.is_template))
            wizard.preview_templates_count = len(wizard.preview_line_ids.filtered(lambda l: l.is_template))
    
    @api.onchange('import_file', 'source_type')
    def _onchange_import_file(self):
        """Génère l'aperçu lors du changement de fichier"""
        self.preview_line_ids = [(5, 0, 0)]
        
        if not self.import_file:
            return
        
        try:
            content = base64.b64decode(self.import_file)
            
            if self.source_type == 'json':
                self._preview_json(content)
            elif self.source_type == 'csv_products':
                self._preview_csv_products(content)
            elif self.source_type == 'csv_templates':
                self._preview_csv_templates(content)
                
        except Exception as e:
            raise UserError(_("Erreur lors de la lecture du fichier: %s") % str(e))
    
    def _preview_json(self, content):
        """Prévisualise un fichier JSON"""
        data = json.loads(content.decode('utf-8'))
        lines = []
        
        # Produits simples
        for product in data.get('products', [])[:50]:  # Limiter à 50 pour l'aperçu
            existing = self.env['product.template'].search([
                ('x_pool_supplier_ref', '=', product.get('ref'))
            ], limit=1)
            
            lines.append((0, 0, {
                'supplier_ref': product.get('ref'),
                'name': product.get('name'),
                'brand': product.get('brand'),
                'category': product.get('category'),
                'purchase_price': product.get('purchasePrice', 0),
                'selling_price': product.get('sellingPrice', 0),
                'is_template': product.get('isVariant', False),
                'existing_product_id': existing.id if existing else False,
                'action': 'update' if existing else 'create',
            }))
        
        # Templates
        for template in data.get('productTemplates', [])[:20]:
            lines.append((0, 0, {
                'supplier_ref': template.get('id'),
                'name': template.get('name'),
                'brand': template.get('brand'),
                'category': template.get('category'),
                'is_template': True,
                'variants_count': len(template.get('variants', [])),
                'attributes_info': ', '.join([a.get('name', '') for a in template.get('attributes', [])]),
                'action': 'create',
            }))
        
        self.preview_line_ids = lines
    
    def _preview_csv_products(self, content):
        """Prévisualise un fichier CSV de produits"""
        # Détecter l'encodage et le délimiteur
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text), delimiter=';')
        
        lines = []
        for i, row in enumerate(reader):
            if i >= 50:
                break
            
            ref = row.get('x_supplier_ref') or row.get('default_code', '').replace('POOL-', '')
            existing = self.env['product.template'].search([
                ('x_pool_supplier_ref', '=', ref)
            ], limit=1)
            
            lines.append((0, 0, {
                'supplier_ref': ref,
                'name': row.get('name', ''),
                'brand': row.get('x_brand', ''),
                'purchase_price': float(row.get('standard_price', 0) or 0),
                'selling_price': float(row.get('list_price', 0) or 0),
                'existing_product_id': existing.id if existing else False,
                'action': 'update' if existing else 'create',
            }))
        
        self.preview_line_ids = lines
    
    def _preview_csv_templates(self, content):
        """Prévisualise un fichier CSV de templates"""
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text), delimiter=';')
        
        lines = []
        current_template = None
        
        for row in reader:
            template_id = row.get('id', '').replace('__export__.product_template_', '')
            if template_id and template_id != current_template:
                current_template = template_id
                lines.append((0, 0, {
                    'supplier_ref': template_id,
                    'name': row.get('name', ''),
                    'is_template': True,
                    'attributes_info': row.get('attribute_line_ids/attribute_id/id', '').replace('__export__.product_attribute_', ''),
                    'action': 'create',
                }))
        
        self.preview_line_ids = lines
    
    def action_preview(self):
        """Rafraîchit l'aperçu"""
        self._onchange_import_file()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pool.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_import(self):
        """Lance l'import"""
        self.ensure_one()
        
        if not self.import_file:
            raise UserError(_("Veuillez sélectionner un fichier"))
        
        # Créer le log d'import
        log = self.env['pool.import.log'].create({
            'supplier_id': self.supplier_id.id,
            'source_type': self.source_type,
            'import_file': self.import_file,
            'import_filename': self.import_filename,
            'state': 'processing',
            'start_date': fields.Datetime.now(),
        })
        
        try:
            content = base64.b64decode(self.import_file)
            
            if self.source_type == 'json':
                result = self._import_json(content, log)
            elif self.source_type == 'csv_products':
                result = self._import_csv_products(content, log)
            elif self.source_type == 'csv_templates':
                result = self._import_csv_templates(content, log)
            
            log.write({
                'state': 'done',
                'end_date': fields.Datetime.now(),
                **result,
            })
            
            # Mettre à jour la date du dernier import du fournisseur
            self.supplier_id.last_import_date = fields.Datetime.now()
            
        except Exception as e:
            log.write({
                'state': 'error',
                'end_date': fields.Datetime.now(),
                'error_message': str(e),
            })
            raise UserError(_("Erreur lors de l'import: %s") % str(e))
        
        # Retourner l'action pour voir le log
        return {
            'type': 'ir.actions.act_window',
            'name': _("Résultat de l'import"),
            'res_model': 'pool.import.log',
            'res_id': log.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _import_json(self, content, log):
        """Importe un fichier JSON complet"""
        data = json.loads(content.decode('utf-8'))
        
        products_created = 0
        products_updated = 0
        products_skipped = 0
        templates_created = 0
        variants_created = 0
        errors = 0
        log_lines = []
        
        ProductTemplate = self.env['product.template']
        
        # Import des produits simples (non variantes)
        for product_data in data.get('products', []):
            if product_data.get('isVariant'):
                continue  # Les variantes seront gérées avec les templates
            
            try:
                ref = product_data.get('ref')
                existing = ProductTemplate.search([
                    ('x_pool_supplier_ref', '=', ref)
                ], limit=1)
                
                if existing and self.update_existing:
                    # Mise à jour
                    vals = self._prepare_product_vals(product_data)
                    existing.write(vals)
                    products_updated += 1
                    action = 'update'
                    product = existing
                elif existing:
                    products_skipped += 1
                    action = 'skip'
                    product = existing
                else:
                    # Création
                    product = ProductTemplate.create_from_fluidra_import(
                        product_data, self.supplier_id
                    )
                    products_created += 1
                    action = 'create'
                
                log_lines.append((0, 0, {
                    'supplier_ref': ref,
                    'product_name': product_data.get('name'),
                    'product_id': product.id,
                    'action': action,
                    'raw_data': json.dumps(product_data),
                }))
                
            except Exception as e:
                errors += 1
                log_lines.append((0, 0, {
                    'supplier_ref': product_data.get('ref'),
                    'product_name': product_data.get('name'),
                    'action': 'error',
                    'message': str(e),
                    'raw_data': json.dumps(product_data),
                }))
        
        # Import des templates avec variantes
        if self.import_templates:
            for template_data in data.get('productTemplates', []):
                try:
                    template = ProductTemplate.create_template_with_variants(
                        template_data, self.supplier_id
                    )
                    templates_created += 1
                    variants_created += len(template.product_variant_ids)
                    
                    log_lines.append((0, 0, {
                        'supplier_ref': template_data.get('id'),
                        'product_name': template_data.get('name'),
                        'product_id': template.id,
                        'action': 'create',
                        'message': f"Template avec {len(template.product_variant_ids)} variantes",
                    }))
                    
                except Exception as e:
                    errors += 1
                    log_lines.append((0, 0, {
                        'supplier_ref': template_data.get('id'),
                        'product_name': template_data.get('name'),
                        'action': 'error',
                        'message': str(e),
                    }))
        
        log.log_line_ids = log_lines
        
        return {
            'total_lines': len(data.get('products', [])) + len(data.get('productTemplates', [])),
            'products_created': products_created,
            'products_updated': products_updated,
            'products_skipped': products_skipped,
            'templates_created': templates_created,
            'variants_created': variants_created,
            'errors_count': errors,
        }
    
    def _import_csv_products(self, content, log):
        """Importe un fichier CSV de produits simples"""
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text), delimiter=';')
        
        products_created = 0
        products_updated = 0
        products_skipped = 0
        errors = 0
        log_lines = []
        total = 0
        
        ProductTemplate = self.env['product.template']
        
        for row in reader:
            total += 1
            try:
                ref = row.get('x_supplier_ref') or row.get('default_code', '').replace('POOL-', '')
                
                existing = ProductTemplate.search([
                    ('x_pool_supplier_ref', '=', ref)
                ], limit=1)
                
                vals = {
                    'name': row.get('name'),
                    'default_code': row.get('default_code') or f"POOL-{ref}",
                    'x_pool_supplier_id': self.supplier_id.id,
                    'x_pool_supplier_ref': ref,
                    'x_pool_brand': row.get('x_brand'),
                    'x_description_fr': row.get('description_sale'),
                    'x_description_nl': row.get('description_sale_nl'),
                    'description_sale': row.get('description_sale'),
                    'standard_price': float(row.get('standard_price', 0) or 0),
                    'list_price': float(row.get('list_price', 0) or 0),
                    'type': 'product',
                    'sale_ok': row.get('sale_ok', 'True').lower() == 'true',
                    'purchase_ok': row.get('purchase_ok', 'True').lower() == 'true',
                    'x_pool_import_date': fields.Datetime.now(),
                    'x_pool_import_source': 'CSV Import',
                }
                
                # Recalculer le prix si demandé
                if self.recalculate_prices and vals['standard_price']:
                    vals['list_price'] = self.supplier_id.calculate_selling_price(vals['standard_price'])
                
                if existing and self.update_existing:
                    existing.write(vals)
                    products_updated += 1
                    action = 'update'
                    product = existing
                elif existing:
                    products_skipped += 1
                    action = 'skip'
                    product = existing
                else:
                    product = ProductTemplate.create(vals)
                    products_created += 1
                    action = 'create'
                
                log_lines.append((0, 0, {
                    'supplier_ref': ref,
                    'product_name': row.get('name'),
                    'product_id': product.id,
                    'action': action,
                }))
                
            except Exception as e:
                errors += 1
                log_lines.append((0, 0, {
                    'supplier_ref': row.get('x_supplier_ref', ''),
                    'product_name': row.get('name', ''),
                    'action': 'error',
                    'message': str(e),
                }))
        
        log.log_line_ids = log_lines
        
        return {
            'total_lines': total,
            'products_created': products_created,
            'products_updated': products_updated,
            'products_skipped': products_skipped,
            'errors_count': errors,
        }
    
    def _import_csv_templates(self, content, log):
        """Importe des fichiers CSV de templates"""
        # Cette méthode nécessiterait 3 fichiers CSV (attributs, valeurs, templates)
        # Pour simplifier, on retourne un message d'information
        raise UserError(_(
            "L'import CSV de templates nécessite l'import séquentiel de 3 fichiers:\n"
            "1. Attributs (product.attribute)\n"
            "2. Valeurs d'attributs (product.attribute.value)\n"
            "3. Templates (product.template)\n\n"
            "Utilisez plutôt l'import JSON pour une gestion automatique des templates."
        ))
    
    def _prepare_product_vals(self, product_data):
        """Prépare les valeurs pour la mise à jour d'un produit"""
        vals = {
            'name': product_data.get('name'),
            'x_pool_brand': product_data.get('brand'),
            'x_pool_category': product_data.get('category'),
            'x_pool_subcategory': product_data.get('subCategory'),
            'x_description_fr': product_data.get('descriptionFr'),
            'x_description_nl': product_data.get('descriptionNl'),
            'description_sale': product_data.get('descriptionFr'),
            'standard_price': product_data.get('purchasePrice', 0),
        }
        
        if self.recalculate_prices:
            vals['list_price'] = self.supplier_id.calculate_selling_price(vals['standard_price'])
        else:
            vals['list_price'] = product_data.get('sellingPrice', 0)
        
        # Attributs techniques
        attributes = product_data.get('attributes', {})
        if attributes.get('power_kw'):
            vals['x_power_kw'] = attributes['power_kw']
        if attributes.get('voltage'):
            vals['x_voltage'] = attributes['voltage']
        if attributes.get('flow'):
            vals['x_flow_rate'] = attributes['flow']
        
        return vals


class PoolImportWizardLine(models.TransientModel):
    _name = 'pool.import.wizard.line'
    _description = "Ligne d'aperçu import"

    wizard_id = fields.Many2one('pool.import.wizard', string='Wizard', required=True, ondelete='cascade')
    
    supplier_ref = fields.Char(string='Réf.')
    name = fields.Char(string='Nom')
    brand = fields.Char(string='Marque')
    category = fields.Char(string='Catégorie')
    purchase_price = fields.Float(string='Prix Achat')
    selling_price = fields.Float(string='Prix Vente')
    
    is_template = fields.Boolean(string='Template')
    variants_count = fields.Integer(string='Variantes')
    attributes_info = fields.Char(string='Attributs')
    
    existing_product_id = fields.Many2one('product.template', string='Produit existant')
    action = fields.Selection([
        ('create', 'Créer'),
        ('update', 'Mettre à jour'),
        ('skip', 'Ignorer'),
    ], string='Action')
