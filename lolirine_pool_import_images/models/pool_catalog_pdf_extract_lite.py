# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_extract_advanced.py - INTÉGRATION SPRINT 1
==========================================================
Intégration de l'extracteur avancé dans Odoo avec bouton d'action
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import base64
import logging

# Import de notre extracteur avancé
from .advanced_image_extractor import extract_images_advanced_v2

_logger = logging.getLogger(__name__)


class PoolCatalogPdfImport(models.Model):
    _inherit = 'pool.catalog.pdf.import'
    
    def action_extract_images_advanced(self):
        """
        NOUVELLE ACTION : Extraction d'images avec détourage précis
        Remplace l'ancien bouton par la version OCR v2.0
        """
        self.ensure_one()
        
        if not self.source_pdf:
            raise UserError("Aucun fichier PDF source trouvé pour l'extraction.")
        
        _logger.info(f"🚀 Extraction avancée démarrée: {self.name}")
        
        try:
            # Décodage PDF
            pdf_data = base64.b64decode(self.source_pdf)
            
            # Extraction avec algorithme avancé
            extracted_images = extract_images_advanced_v2(
                pdf_data=pdf_data,
                page_start=self.page_start or 1,
                page_end=self.page_end or 50
            )
            
            # Suppression anciennes images (si demandé)
            if extracted_images:
                existing_images = self.env['pool.catalog.pdf.image'].search([
                    ('pdf_import_id', '=', self.id)
                ])
                if existing_images:
                    existing_images.unlink()
                    _logger.info(f"🗑️ {len(existing_images)} anciennes images supprimées")
            
            # Création nouvelles images avec variantes
            created_count = 0
            for img_data in extracted_images:
                try:
                    # Récupération des variantes
                    variants = img_data['variants']
                    bbox = img_data['bbox']
                    
                    # Création enregistrement image
                    image_record = self.env['pool.catalog.pdf.image'].create({
                        'pdf_import_id': self.id,
                        'page_number': img_data['page_number'],
                        'bbox_x': bbox[0],
                        'bbox_y': bbox[1], 
                        'bbox_width': bbox[2],
                        'bbox_height': bbox[3],
                        'quality_score': img_data['quality_score'],
                        'confidence_score': 0.0,  # À calculer par OCR
                        
                        # Images variantes
                        'image_raw': variants['raw'],
                        'image_trimmed': variants['clean'],  # Nouvelle variante détourée
                        'image_enhanced': variants['enhanced'],
                        
                        # Métadonnées techniques
                        'original_width': img_data['dimensions'][0],
                        'original_height': img_data['dimensions'][1],
                        'image_format': 'JPEG',
                        'notes': img_data.get('enhancement_notes', ''),
                        
                        # Réglages par défaut
                        'image_variant': 'enhanced',  # Utilise la version optimisée
                        'role': 'unassigned'
                    })
                    
                    created_count += 1
                    _logger.debug(f"✅ Image créée: {image_record.id} (Q:{img_data['quality_score']})")
                    
                except Exception as e:
                    _logger.error(f"❌ Erreur création image: {e}")
                    continue
            
            # Message succès
            message = f"🎉 Extraction avancée terminée !\n"
            message += f"📸 {created_count} images extraites avec détourage précis\n"
            message += f"📊 Qualité moyenne améliorée avec 3 variantes par image"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Extraction Avancée Réussie',
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"❌ Erreur extraction avancée: {e}")
            raise UserError(f"Erreur lors de l'extraction avancée: {str(e)}")


class PoolCatalogPdfImage(models.Model):
    _inherit = 'pool.catalog.pdf.image'
    
    # Nouveau champ pour image détourée
    image_trimmed = fields.Binary(
        string='Image Détourée',
        help="Image avec bordures automatiquement supprimées (Sprint 1)"
    )
    
    # Champs métadonnées enrichis
    bbox_x = fields.Float(string='Position X', digits=(12, 2))
    bbox_y = fields.Float(string='Position Y', digits=(12, 2))
    bbox_width = fields.Float(string='Largeur', digits=(12, 2))
    bbox_height = fields.Float(string='Hauteur', digits=(12, 2))
    
    # Champ pour les notes d'amélioration
    enhancement_notes = fields.Text(string='Notes Amélioration')
    
    @api.depends('image_raw', 'image_trimmed', 'image_enhanced', 'image_variant')
    def _compute_image_final(self):
        """Version enrichie avec nouvelle variante 'trimmed'"""
        for record in self:
            if record.image_variant == 'trimmed' and record.image_trimmed:
                record.image_final = record.image_trimmed
            elif record.image_variant == 'enhanced' and record.image_enhanced:
                record.image_final = record.image_enhanced
            elif record.image_variant == 'raw' and record.image_raw:
                record.image_final = record.image_raw
            else:
                # Fallback intelligent
                record.image_final = (record.image_enhanced or 
                                    record.image_trimmed or 
                                    record.image_raw)
    
    # Choix de variante enrichi
    image_variant = fields.Selection([
        ('raw', 'Brute'),
        ('trimmed', 'Détourée'),      # Nouvelle option
        ('enhanced', 'Optimisée')
    ], string='Variante utilisée', default='enhanced')
    
    def action_preview_all_variants(self):
        """Action pour prévisualiser les 3 variantes côte à côte"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Variantes - {self.name}',
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
    
    def action_switch_to_trimmed(self):
        """Basculer vers la version détourée"""
        self.ensure_one()
        if self.image_trimmed:
            self.image_variant = 'trimmed'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Basculé vers la version détourée',
                    'type': 'info'
                }
            }
        else:
            raise UserError("Aucune version détourée disponible")
    
    def action_switch_to_enhanced(self):
        """Basculer vers la version optimisée"""
        self.ensure_one() 
        if self.image_enhanced:
            self.image_variant = 'enhanced'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Basculé vers la version optimisée',
                    'type': 'info'
                }
            }
        else:
            raise UserError("Aucune version optimisée disponible")
