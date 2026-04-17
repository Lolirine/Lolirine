# -*- coding: utf-8 -*-
"""
pool_catalog_image_wizards.py
=============================
Wizards pour la gestion des images : réassignation et push vers production.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class PoolCatalogImageReassignWizard(models.TransientModel):
    _name = 'pool.catalog.image.reassign.wizard'
    _description = 'Assistant réassignation image-produit'
    
    image_id = fields.Many2one(
        'pool.catalog.pdf.image',
        string='Image',
        required=True,
        readonly=True
    )
    current_product_id = fields.Many2one(
        'pool.catalog.pdf.product',
        string='Produit actuel',
        related='image_id.matched_product_id',
        readonly=True
    )
    new_product_id = fields.Many2one(
        'pool.catalog.pdf.product',
        string='Nouveau produit',
        required=True,
        domain="[('pdf_import_id', '=', pdf_import_id)]"
    )
    pdf_import_id = fields.Many2one(
        'pool.catalog.pdf.import',
        related='image_id.pdf_import_id',
        readonly=True
    )
    confidence_score = fields.Float(
        string='Score de confiance',
        default=1.0,
        digits=(3, 3),
        help="Confiance de cette association manuelle (1.0 = certaine)"
    )
    notes = fields.Text(string='Notes sur la réassignation')
    
    def action_reassign(self):
        """Effectue la réassignation."""
        self.ensure_one()
        
        # Mettre à jour l'image
        self.image_id.write({
            'matched_product_id': self.new_product_id.id,
            'confidence_score': self.confidence_score,
            'notes': self.notes
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Image réassignée à {self.new_product_id.name}",
                'type': 'success'
            }
        }


class PoolCatalogImagePushWizard(models.TransientModel):
    _name = 'pool.catalog.image.push.wizard'
    _description = 'Assistant push images vers production'
    
    pdf_import_id = fields.Many2one(
        'pool.catalog.pdf.import',
        string='Import PDF',
        required=True,
        readonly=True
    )
    
    # Statistiques
    total_products = fields.Integer(
        string='Produits totaux',
        compute='_compute_stats'
    )
    products_with_images = fields.Integer(
        string='Produits avec images',
        compute='_compute_stats'
    )
    primary_images_count = fields.Integer(
        string='Images principales',
        compute='_compute_stats'
    )
    secondary_images_count = fields.Integer(
        string='Images secondaires',
        compute='_compute_stats'
    )
    
    # Options
    create_missing_products = fields.Boolean(
        string='Créer produits manquants',
        default=True,
        help="Créer les product.template pour les produits qui n'existent pas encore"
    )
    overwrite_existing_images = fields.Boolean(
        string='Remplacer images existantes',
        default=False,
        help="Remplacer les images des produits qui en ont déjà"
    )
    category_id = fields.Many2one(
        'product.category',
        string='Catégorie par défaut',
        help="Catégorie pour les nouveaux produits créés"
    )
    website_id = fields.Many2one(
        'website',
        string='Site web',
        default=lambda self: self._default_website_id(),
        help="Site web pour la publication des produits"
    )
    
    # Résultats
    result_created_products = fields.Integer(string='Produits créés', readonly=True)
    result_updated_products = fields.Integer(string='Produits mis à jour', readonly=True)
    result_errors = fields.Text(string='Erreurs', readonly=True)
    
    def _default_website_id(self):
        """Site web par défaut (Pool Store = ID 6)."""
        return self.env['website'].search([('id', '=', 6)], limit=1)
    
    @api.depends('pdf_import_id')
    def _compute_stats(self):
        for wizard in self:
            if not wizard.pdf_import_id:
                wizard.total_products = 0
                wizard.products_with_images = 0
                wizard.primary_images_count = 0
                wizard.secondary_images_count = 0
                continue
            
            products = wizard.pdf_import_id.extracted_product_ids
            images = wizard.pdf_import_id.extracted_image_ids
            
            wizard.total_products = len(products)
            wizard.products_with_images = len(products.filtered('image_ids'))
            wizard.primary_images_count = len(images.filtered(lambda i: i.role == 'primary'))
            wizard.secondary_images_count = len(images.filtered(lambda i: i.role == 'secondary'))
    
    def action_push_to_production(self):
        """Lance le push vers les product.template."""
        self.ensure_one()
        
        if not self.primary_images_count and not self.secondary_images_count:
            raise UserError("Aucune image assignée (principale ou secondaire) à pousser.")
        
        created_count = 0
        updated_count = 0
        errors = []
        
        try:
            # Récupérer les produits avec images assignées
            products_with_images = self.pdf_import_id.extracted_product_ids.filtered('image_ids')
            
            for product in products_with_images:
                try:
                    # Récupérer les images du produit
                    primary_image = product.image_ids.filtered(lambda i: i.role == 'primary')
                    secondary_images = product.image_ids.filtered(lambda i: i.role == 'secondary')
                    
                    if not primary_image and not secondary_images:
                        continue  # Pas d'images assignées pour ce produit
                    
                    # Chercher le product.template existant
                    existing_product = self._find_existing_product_template(product)
                    
                    if existing_product:
                        # Mise à jour produit existant
                        if self.overwrite_existing_images or not existing_product.image_1920:
                            self._update_product_images(existing_product, primary_image, secondary_images)
                            updated_count += 1
                    else:
                        # Création nouveau produit
                        if self.create_missing_products:
                            new_product = self._create_product_template(product, primary_image, secondary_images)
                            if new_product:
                                created_count += 1
                        else:
                            errors.append(f"Produit non trouvé : {product.name} (création désactivée)")
                
                except Exception as e:
                    error_msg = f"Erreur produit {product.name}: {str(e)}"
                    errors.append(error_msg)
                    _logger.error(error_msg)
                    continue
            
            # Mettre à jour les résultats
            self.write({
                'result_created_products': created_count,
                'result_updated_products': updated_count,
                'result_errors': '\n'.join(errors) if errors else False
            })
            
            # Notification
            if created_count or updated_count:
                message = f"Push terminé : {created_count} créés, {updated_count} mis à jour"
                if errors:
                    message += f", {len(errors)} erreurs"
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Push vers production',
                        'message': message,
                        'type': 'success' if not errors else 'warning',
                        'sticky': True,
                    }
                }
            else:
                raise UserError("Aucun produit n'a pu être créé ou mis à jour. Vérifiez les paramètres.")
                
        except Exception as e:
            error_msg = f"Erreur générale push: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)
    
    def _find_existing_product_template(self, catalog_product):
        """
        Cherche un product.template existant correspondant au produit catalogue.
        """
        ProductTemplate = self.env['product.template'].sudo()
        
        # Recherche par référence fournisseur
        if catalog_product.supplier_ref:
            # Chercher dans default_code
            existing = ProductTemplate.search([
                ('default_code', '=', catalog_product.supplier_ref.strip()),
                ('website_id', 'in', [False, self.website_id.id])
            ], limit=1)
            if existing:
                return existing
            
            # Chercher dans les codes barre
            existing = ProductTemplate.search([
                ('barcode', '=', catalog_product.supplier_ref.strip()),
                ('website_id', 'in', [False, self.website_id.id])
            ], limit=1)
            if existing:
                return existing
        
        # Recherche par nom (fuzzy match)
        if catalog_product.name:
            name_clean = catalog_product.name.strip()
            existing = ProductTemplate.search([
                ('name', 'ilike', name_clean),
                ('website_id', 'in', [False, self.website_id.id])
            ], limit=1)
            if existing:
                return existing
        
        return None
    
    def _create_product_template(self, catalog_product, primary_image, secondary_images):
        """
        Crée un nouveau product.template depuis un produit catalogue.
        """
        try:
            # Données de base
            product_vals = {
                'name': catalog_product.name or f"Produit {catalog_product.supplier_ref}",
                'default_code': catalog_product.supplier_ref,
                'website_id': self.website_id.id if self.website_id else False,
                'is_published': True,
                'sale_ok': True,
                'purchase_ok': True,
                'type': 'product',
                'categ_id': self.category_id.id if self.category_id else 1,  # All par défaut
                'description': catalog_product.description or '',
                'website_description': catalog_product.description or '',
                'list_price': catalog_product.price or 0.0,
                'standard_price': catalog_product.price * 0.65 if catalog_product.price else 0.0,  # Marge 35%
            }
            
            # Image principale
            if primary_image:
                product_vals['image_1920'] = primary_image.image_final
            
            # Créer le produit
            product = self.env['product.template'].sudo().create(product_vals)
            
            # Images secondaires
            if secondary_images:
                self._create_secondary_images(product, secondary_images)
            
            _logger.info(f"Produit créé: {product.name} (ID: {product.id})")
            return product
            
        except Exception as e:
            _logger.error(f"Erreur création produit {catalog_product.name}: {e}")
            raise
    
    def _update_product_images(self, product, primary_image, secondary_images):
        """
        Met à jour les images d'un product.template existant.
        """
        try:
            # Mise à jour image principale
            if primary_image:
                product.sudo().write({'image_1920': primary_image.image_final})
            
            # Supprimer anciennes images secondaires si remplacement
            if self.overwrite_existing_images:
                old_images = self.env['product.image'].sudo().search([
                    ('product_tmpl_id', '=', product.id)
                ])
                old_images.unlink()
            
            # Ajouter nouvelles images secondaires
            if secondary_images:
                self._create_secondary_images(product, secondary_images)
            
            _logger.info(f"Images mises à jour pour: {product.name}")
            
        except Exception as e:
            _logger.error(f"Erreur mise à jour images {product.name}: {e}")
            raise
    
    def _create_secondary_images(self, product, secondary_images):
        """
        Crée les images secondaires pour un produit.
        """
        try:
            for i, image in enumerate(secondary_images[:5]):  # Max 5 images secondaires
                self.env['product.image'].sudo().create({
                    'product_tmpl_id': product.id,
                    'name': f"Image {i+1} - {image.name}",
                    'image_1920': image.image_final,
                    'sequence': i + 1
                })
            
        except Exception as e:
            _logger.error(f"Erreur création images secondaires {product.name}: {e}")
            raise


class PoolCatalogImageBulkAssignWizard(models.TransientModel):
    _name = 'pool.catalog.image.bulk.wizard'
    _description = 'Assistant attribution en masse'
    
    pdf_import_id = fields.Many2one(
        'pool.catalog.pdf.import',
        string='Import PDF',
        required=True,
        readonly=True
    )
    
    # Actions en masse
    action_type = fields.Selection([
        ('auto_primary', 'Auto: Meilleure image → Principale'),
        ('auto_secondary', 'Auto: Autres images → Secondaires'),
        ('reset_all', 'Reset: Tout en non-attribué'),
        ('reject_low_quality', 'Rejeter: Score qualité < seuil'),
    ], string='Action', required=True)
    
    quality_threshold = fields.Float(
        string='Seuil qualité',
        default=0.3,
        digits=(3, 3),
        help="Images avec score inférieur seront rejetées"
    )
    
    # Filtres
    filter_unassigned_only = fields.Boolean(
        string='Uniquement non-attribuées',
        default=True,
        help="Appliquer seulement aux images non-attribuées"
    )
    
    def action_execute_bulk(self):
        """Exécute l'action en masse."""
        self.ensure_one()
        
        images = self.pdf_import_id.extracted_image_ids
        
        # Appliquer filtres
        if self.filter_unassigned_only:
            images = images.filtered(lambda i: i.role == 'unassigned')
        
        count = 0
        
        if self.action_type == 'auto_primary':
            # Pour chaque produit, assigner l'image avec le meilleur score comme principale
            products_with_images = {}
            
            for image in images:
                if image.matched_product_id:
                    prod_id = image.matched_product_id.id
                    if prod_id not in products_with_images:
                        products_with_images[prod_id] = []
                    products_with_images[prod_id].append(image)
            
            for prod_id, prod_images in products_with_images.items():
                # Trier par score qualité décroissant
                prod_images.sort(key=lambda i: i.quality_score, reverse=True)
                best_image = prod_images[0]
                best_image.role = 'primary'
                count += 1
        
        elif self.action_type == 'auto_secondary':
            # Assigner en secondaire les images non-principales avec produit associé
            for image in images:
                if image.matched_product_id and image.role != 'primary':
                    image.role = 'secondary'
                    count += 1
        
        elif self.action_type == 'reset_all':
            images.write({'role': 'unassigned'})
            count = len(images)
        
        elif self.action_type == 'reject_low_quality':
            low_quality = images.filtered(lambda i: i.quality_score < self.quality_threshold)
            low_quality.write({'role': 'rejected'})
            count = len(low_quality)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Action terminée : {count} images traitées",
                'type': 'success'
            }
        }
