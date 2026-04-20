# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_image.py - VERSION COMPLÈTE AVEC NOUVEAUX CHAMPS
================================================================
Modèle enrichi avec champs pour extraction avancée (Sprint 1)
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
    
    # NOUVEAUX CHAMPS SPRINT 1 - Position dans PDF
    bbox_x = fields.Float(string='Position X', digits=(12, 2))
    bbox_y = fields.Float(string='Position Y', digits=(12, 2))  
    bbox_width = fields.Float(string='Largeur', digits=(12, 2))
    bbox_height = fields.Float(string='Hauteur', digits=(12, 2))
    
    # Scores qualité
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
    
    # Images (3 variantes) - SPRINT 1
    image_raw = fields.Binary(
        string='Image brute',
        help="Image extraite directement du PDF"
    )
    image_trimmed = fields.Binary(
        string='Image détourée', 
        help="Image avec bordures automatiquement supprimées (Sprint 1)"
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
        ('trimmed', 'Détourée'),     # NOUVEAU Sprint 1
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
    
    # Notes utilisateur + amélioration
    notes = fields.Text(string='Notes')
    enhancement_notes = fields.Text(string='Notes Amélioration Sprint 1')
    
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
            
            variant_icon = {
                'enhanced': '✨',
                'trimmed': '✂️',
                'raw': '📷'
            }.get(record.image_variant, '')
            
            record.display_name = f"{role_icon} {record.name} {variant_icon}"
    
    @api.depends('image_raw', 'image_trimmed', 'image_enhanced', 'image_variant')
    def _compute_image_final(self):
        for record in self:
            if record.image_variant == 'trimmed' and record.image_trimmed:
                record.image_final = record.image_trimmed
            elif record.image_variant == 'enhanced' and record.image_enhanced:
                record.image_final = record.image_enhanced
            elif record.image_variant == 'raw' and record.image_raw:
                record.image_final = record.image_raw
            else:
                # Fallback intelligent - priorité aux versions améliorées
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
    
    # NOUVELLES ACTIONS SPRINT 1
    def action_switch_to_trimmed(self):
        """Basculer vers la version détourée"""
        self.ensure_one()
        if self.image_trimmed:
            self.image_variant = 'trimmed'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': '✂️ Basculé vers la version détourée',
                    'type': 'info'
                }
            }
        else:
            raise UserError("Aucune version détourée disponible pour cette image")
    
    def action_switch_to_enhanced(self):
        """Basculer vers la version optimisée"""
        self.ensure_one() 
        if self.image_enhanced:
            self.image_variant = 'enhanced'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': '✨ Basculé vers la version optimisée',
                    'type': 'success'
                }
            }
        else:
            raise UserError("Aucune version optimisée disponible pour cette image")
    
    def action_preview_all_variants(self):
        """Action pour prévisualiser les 3 variantes côte à côte"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Variantes Sprint 1 - {self.name}',
            'res_model': 'pool.catalog.pdf.image',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
            'context': {
                'form_view_initial_mode': 'readonly',
                'show_variants_comparison': True
            }
        }
    
    # Actions héritées des versions précédentes
    def action_set_primary(self):
        """Marquer cette image comme principale"""
        self.ensure_one()
        if not self.matched_product_id:
            self._try_auto_match()
            if not self.matched_product_id:
                raise UserError("Impossible de définir comme principale : aucun produit associé. Utilisez 'Réassigner le produit' d'abord.")
        
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
                'message': f"🌟 Image définie comme principale pour {self.matched_product_id.name}",
                'type': 'success'
            }
        }
    
    def action_set_secondary(self):
        """Marquer comme image secondaire."""
        self.ensure_one()
        if not self.matched_product_id:
            self._try_auto_match()
        self.role = 'secondary'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': "📷 Image marquée comme secondaire",
                'type': 'success'
            }
        }
    
    def action_delete_image(self):
        """Supprimer cette image après confirmation."""
        self.ensure_one()
        name = self.name
        self.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"🗑️ Image '{name}' supprimée avec succès",
                'type': 'success'
            }
        }
    
    def _try_auto_match(self):
        """Essayer de faire l'association automatique pour cette image."""
        self.ensure_one()
        
        # Récupérer les produits de la même page
        page_products = self.pdf_import_id.product_ids.filtered(
            lambda p: p.page_number == self.page_number
        )
        
        if page_products:
            # Association simple : premier produit disponible de la page
            self.matched_product_id = page_products[0]
            self.confidence_score = 0.7  # Confiance modérée
            _logger.info(f"Auto-association image {self.id} -> produit {page_products[0].name}")
    
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
