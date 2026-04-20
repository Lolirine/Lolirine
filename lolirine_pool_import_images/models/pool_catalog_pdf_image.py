# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_image.py
=========================
Modèle pour stocker les images extraites des catalogues PDF avec métadonnées
et système d'attribution aux produits (principale/secondaire).
"""

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
import base64
from PIL import Image, ImageEnhance, ImageFilter
import io
import logging

_logger = logging.getLogger(__name__)


class PoolCatalogPdfImage(models.Model):
    _name = 'pool.catalog.pdf.image'
    _description = 'Image extraite du catalogue PDF'
    _order = 'quality_score desc, id desc'

    # Relations
    pdf_import_id = fields.Many2one(
        'pool.catalog.pdf.import', 
        string='Import PDF',
        required=True, 
        ondelete='cascade',
        index=True
    )
    matched_product_id = fields.Many2one(
        'pool.catalog.pdf.product',
        string='Produit associé',
        ondelete='set null',
        index=True,
        help="Produit automatiquement détecté par proximité textuelle"
    )
    
    # Métadonnées d'extraction
    page_number = fields.Integer(string='Page', required=True, index=True)
    bbox_x = fields.Float(string='Position X', digits=(12, 2))
    bbox_y = fields.Float(string='Position Y', digits=(12, 2))  
    bbox_width = fields.Float(string='Largeur', digits=(12, 2))
    bbox_height = fields.Float(string='Hauteur', digits=(12, 2))
    quality_score = fields.Float(
        string='Score qualité', 
        digits=(3, 3),
        help="Score de 0 à 1 basé sur taille, forme, position et densité"
    )
    confidence_score = fields.Float(
        string='Confiance association',
        digits=(3, 3),
        help="Confiance de l'association automatique avec le produit (0-1)"
    )
    
    # Images (3 variantes)
    image_raw = fields.Binary(
        string='Image brute',
        help="Image extraite directement du PDF"
    )
    image_trimmed = fields.Binary(
        string='Image détourée', 
        help="Image avec bordures automatiquement supprimées"
    )
    image_enhanced = fields.Binary(
        string='Image optimisée',
        help="Image optimisée pour l'e-commerce (netteté, contraste)"
    )
    
    # Image sélectionnée pour utilisation
    image_final = fields.Binary(
        string='Image finale',
        compute='_compute_image_final',
        store=True,
        help="Image sélectionnée selon la variante choisie"
    )
    image_variant = fields.Selection([
        ('raw', 'Brute'),
        ('trimmed', 'Détourée'),
        ('enhanced', 'Optimisée')
    ], string='Variante utilisée', default='enhanced')
    
    # Métadonnées techniques
    original_width = fields.Integer(string='Largeur originale')
    original_height = fields.Integer(string='Hauteur originale')
    file_size_kb = fields.Float(string='Taille (KB)', digits=(8, 1))
    image_format = fields.Char(string='Format', default='PNG')
    
    # Attribution aux produits
    role = fields.Selection([
        ('unassigned', 'Non attribuée'),
        ('primary', 'Principale'),
        ('secondary', 'Secondaire'),
        ('rejected', 'Rejetée')
    ], string='Rôle', default='unassigned', index=True)
    
    # Champs calculés
    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True
    )
    display_name = fields.Char(
        compute='_compute_display_name'
    )
    
    # Notes utilisateur
    notes = fields.Text(string='Notes')
    
    @api.depends('page_number', 'matched_product_id', 'quality_score')
    def _compute_name(self):
        for record in self:
            if record.matched_product_id:
                name = f"P{record.page_number} - {record.matched_product_id.name}"
            else:
                name = f"Page {record.page_number} - Image #{record.id or 'nouveau'}"
            
            if record.quality_score:
                name += f" (Q:{record.quality_score:.2f})"
            
            record.name = name
    
    @api.depends('name', 'role', 'image_variant')
    def _compute_display_name(self):
        for record in self:
            role_icon = {
                'primary': '🌟',
                'secondary': '📷', 
                'rejected': '❌',
                'unassigned': '❓'
            }.get(record.role, '')
            
            record.display_name = f"{role_icon} {record.name} [{record.image_variant}]"
    
    @api.depends('image_raw', 'image_trimmed', 'image_enhanced', 'image_variant')
    def _compute_image_final(self):
        for record in self:
            variant_field = f'image_{record.image_variant}'
            if hasattr(record, variant_field):
                record.image_final = getattr(record, variant_field)
            else:
                # Fallback sur enhanced si disponible, sinon trimmed, sinon raw
                record.image_final = (record.image_enhanced or 
                                    record.image_trimmed or 
                                    record.image_raw)
    
    @api.constrains('role', 'matched_product_id')
    def _check_primary_unique(self):
        """Une seule image principale par produit."""
        for record in self:
            if record.role == 'primary' and record.matched_product_id:
                existing = self.search([
                    ('matched_product_id', '=', record.matched_product_id.id),
                    ('role', '=', 'primary'),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(
                        f"Le produit '{record.matched_product_id.name}' a déjà une image principale. "
                        f"Changez d'abord l'autre image en 'Secondaire' ou 'Rejetée'."
                    )
    
    def action_set_primary(self):
        """Marquer cette image comme principale (et les autres du même produit comme secondaires)."""
        self.ensure_one()
        if not self.matched_product_id:
            raise UserError("Impossible de définir comme principale : aucun produit associé.")
        
        # Marquer les autres images du même produit comme secondaires
        other_images = self.search([
            ('matched_product_id', '=', self.matched_product_id.id),
            ('role', 'in', ['primary', 'secondary']),
            ('id', '!=', self.id)
        ])
        other_images.write({'role': 'secondary'})
        
        # Marquer cette image comme principale
        self.role = 'primary'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Image définie comme principale pour {self.matched_product_id.name}",
                'type': 'success'
            }
        }
    
    def action_set_secondary(self):
        """Marquer comme image secondaire."""
        self.ensure_one()
        self.role = 'secondary'
    
    def action_set_rejected(self):
        """Marquer comme rejetée."""
        self.ensure_one()
        self.role = 'rejected'
    
    def action_reassign_product(self):
        """Ouvrir wizard de réassignation manuelle."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Réassigner le produit',
            'res_model': 'pool.catalog.image.reassign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_image_id': self.id}
        }
    
    def action_preview_variants(self):
        """Prévisualiser les 3 variantes de l'image."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Variantes - {self.name}',
            'res_model': 'pool.catalog.pdf.image',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
            'context': {'form_view_initial_mode': 'readonly'}
        }
    
    def enhance_image_sharpness(self, image_data):
        """
        Améliore la netteté de l'image avec PIL uniquement (version lite).
        """
        if not image_data:
            return image_data
        
        try:
            # Décoder l'image
            img_pil = Image.open(io.BytesIO(base64.b64decode(image_data)))
            
            # Amélioration de la netteté avec PIL
            sharpness_enhancer = ImageEnhance.Sharpness(img_pil)
            sharpened_img = sharpness_enhancer.enhance(1.3)  # +30% netteté
            
            # Légère amélioration du contraste
            contrast_enhancer = ImageEnhance.Contrast(sharpened_img)
            final_img = contrast_enhancer.enhance(1.1)  # +10% contraste
            
            # Réencoder en base64
            output = io.BytesIO()
            final_img.save(output, format='PNG', optimize=True)
            return base64.b64encode(output.getvalue())
            
        except Exception as e:
            _logger.warning(f"Erreur amélioration netteté image {self.id}: {e}")
            return image_data  # Retourner l'original en cas d'erreur
    
    @api.model
    def create(self, vals):
        """Override create pour améliorer automatiquement la netteté de l'image enhanced."""
        record = super().create(vals)
        
        # Améliorer la netteté de l'image enhanced si disponible
        if record.image_enhanced:
            enhanced_sharp = record.enhance_image_sharpness(record.image_enhanced)
            if enhanced_sharp != record.image_enhanced:
                record.write({'image_enhanced': enhanced_sharp})
        
        return record


class PoolCatalogPdfProduct(models.Model):
    _inherit = 'pool.catalog.pdf.product'
    
    # Relation vers les images
    image_ids = fields.One2many(
        'pool.catalog.pdf.image',
        'matched_product_id',
        string='Images extraites'
    )
    image_count = fields.Integer(
        string='Nb images',
        compute='_compute_image_count'
    )
    primary_image_id = fields.Many2one(
        'pool.catalog.pdf.image',
        string='Image principale',
        compute='_compute_primary_image',
        store=True
    )
    secondary_image_ids = fields.One2many(
        'pool.catalog.pdf.image',
        'matched_product_id',
        string='Images secondaires',
        domain=[('role', '=', 'secondary')]
    )
    
    @api.depends('image_ids')
    def _compute_image_count(self):
        for record in self:
            record.image_count = len(record.image_ids.filtered(lambda img: img.role != 'rejected'))
    
    @api.depends('image_ids.role')
    def _compute_primary_image(self):
        for record in self:
            primary = record.image_ids.filtered(lambda img: img.role == 'primary')
            record.primary_image_id = primary[0] if primary else False
    
    def action_view_images(self):
        """Ouvrir la vue des images pour ce produit."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Images - {self.name}',
            'res_model': 'pool.catalog.pdf.image',
            'view_mode': 'kanban,tree,form',
            'domain': [('matched_product_id', '=', self.id)],
            'context': {
                'default_matched_product_id': self.id,
                'search_default_not_rejected': 1,
            }
        }
