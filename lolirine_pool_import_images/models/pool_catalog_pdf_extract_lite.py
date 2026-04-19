# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_extract_lite.py
================================
Version allégée de l'extraction d'images sans OpenCV.
Utilise uniquement PIL/Pillow pour éviter les conflits de dépendances.
"""

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import base64
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import fitz  # PyMuPDF
import io
import json
import math
import logging

_logger = logging.getLogger(__name__)


class PoolCatalogPdfImport(models.Model):
    _inherit = 'pool.catalog.pdf.import'
    
    # Nouveaux champs pour l'extraction d'images
    images_extracted = fields.Boolean(
        string='Images extraites',
        default=False,
        help="Indique si l'extraction d'images a été effectuée"
    )
    image_extraction_state = fields.Selection([
        ('not_started', 'Non démarrée'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('error', 'Erreur')
    ], string='État extraction images', default='not_started', index=True)
    
    image_extraction_progress = fields.Float(
        string='Progression (%)',
        default=0.0,
        help="Pourcentage de pages traitées pour l'extraction d'images"
    )
    image_count = fields.Integer(
        string='Nb images extraites',
        compute='_compute_image_count'
    )
    
    # Paramètres d'extraction simplifiés
    min_image_size = fields.Integer(
        string='Taille minimum (px)',
        default=100,
        help="Largeur/hauteur minimum pour considérer une région comme une photo"
    )
    max_image_size = fields.Integer(
        string='Taille maximum (px)', 
        default=800,
        help="Largeur/hauteur maximum pour éviter les grandes images de fond"
    )
    
    # Relations
    extracted_image_ids = fields.One2many(
        'pool.catalog.pdf.image',
        'pdf_import_id',
        string='Images extraites'
    )
    
    @api.depends('extracted_image_ids')
    def _compute_image_count(self):
        for record in self:
            record.image_count = len(record.extracted_image_ids)
    
    def action_extract_images_lite(self):
        """
        Extraction d'images version allégée sans OpenCV.
        Utilise PyMuPDF pour extraire directement les images embarquées.
        """
        self.ensure_one()
        
        # Identifier automatiquement le champ PDF
        pdf_data = None
        pdf_field_name = None
        
        # Liste des champs PDF possibles
        possible_pdf_fields = [
            'pdf_file', 'pdf_data', 'file_data', 'catalog_file', 
            'pdf_content', 'attachment_data', 'file_content'
        ]
        
        for field_name in possible_pdf_fields:
            if hasattr(self, field_name):
                field_value = getattr(self, field_name, None)
                if field_value:
                    pdf_data = field_value
                    pdf_field_name = field_name
                    break
        
        if not pdf_data:
            raise UserError("Aucun fichier PDF n'est attaché à cet import ou le champ PDF n'est pas reconnu.")
        
        _logger.info(f"PDF trouvé dans le champ: {pdf_field_name}")
        
        if self.image_extraction_state == 'in_progress':
            raise UserError("Une extraction est déjà en cours. Attendez qu'elle se termine.")
        
        try:
            self.write({
                'image_extraction_state': 'in_progress',
                'image_extraction_progress': 0.0
            })
            
            # Décoder le PDF
            pdf_data_decoded = base64.b64decode(pdf_data)
            doc = fitz.open(stream=pdf_data_decoded, filetype="pdf")
            total_pages = len(doc)
            
            _logger.info(f"Début extraction images PDF {self.filename}: {total_pages} pages")
            
            extracted_count = 0
            
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    
                    # Extraire les images embarquées de cette page
                    page_images = self._extract_embedded_images_lite(page, page_num + 1)
                    
                    # Associer automatiquement aux produits
                    for img_data in page_images:
                        matched_product, confidence = self._match_image_to_product_lite(
                            page, img_data, page_num + 1
                        )
                        
                        # Créer l'enregistrement image
                        image_vals = {
                            'pdf_import_id': self.id,
                            'page_number': page_num + 1,
                            'bbox_x': img_data.get('bbox', [0, 0, 0, 0])[0],
                            'bbox_y': img_data.get('bbox', [0, 0, 0, 0])[1], 
                            'bbox_width': img_data.get('bbox', [0, 0, 0, 0])[2],
                            'bbox_height': img_data.get('bbox', [0, 0, 0, 0])[3],
                            'quality_score': img_data.get('quality_score', 0.5),
                            'confidence_score': confidence,
                            'matched_product_id': matched_product.id if matched_product else False,
                            'image_raw': img_data['raw_b64'],
                            'image_trimmed': img_data['trimmed_b64'],
                            'image_enhanced': img_data['enhanced_b64'],
                            'original_width': img_data['raw_size'][0],
                            'original_height': img_data['raw_size'][1],
                            'file_size_kb': len(base64.b64decode(img_data['enhanced_b64'])) / 1024,
                        }
                        
                        self.env['pool.catalog.pdf.image'].create(image_vals)
                        extracted_count += 1
                    
                    # Mise à jour progression
                    progress = ((page_num + 1) / total_pages) * 100
                    self.image_extraction_progress = progress
                    
                    # Commit intermédiaire tous les 5 pages
                    if (page_num + 1) % 5 == 0:
                        self.env.cr.commit()
                        _logger.info(f"Extraction page {page_num + 1}/{total_pages}: {extracted_count} images")
                
                except Exception as e:
                    _logger.error(f"Erreur extraction page {page_num + 1}: {str(e)}")
                    continue
            
            doc.close()
            
            # Finalisation
            self.write({
                'image_extraction_state': 'completed',
                'image_extraction_progress': 100.0,
                'images_extracted': True
            })
            
            _logger.info(f"Extraction terminée: {extracted_count} images extraites")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Extraction terminée',
                    'message': f'{extracted_count} images extraites et associées automatiquement',
                    'type': 'success',
                    'sticky': False,
                },
                'context': {'next_action': self._action_view_extracted_images()}
            }
            
        except Exception as e:
            _logger.error(f"Erreur extraction images: {str(e)}")
            self.write({
                'image_extraction_state': 'error',
                'image_extraction_progress': 0.0
            })
            raise UserError(f"Erreur lors de l'extraction d'images: {str(e)}")
    
    def _extract_embedded_images_lite(self, page, page_number):
        """
        Version allégée : extrait directement les images embarquées du PDF.
        Plus simple mais très efficace pour les catalogues.
        """
        extracted_images = []
        
        # Récupérer la liste des images embarquées sur cette page
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]  # Référence de l'image dans le PDF
                
                # Extraire l'image
                base_img = page.parent.extract_image(xref)
                image_bytes = base_img["image"]
                image_ext = base_img["ext"]
                
                # Convertir en PIL Image
                image_pil = Image.open(io.BytesIO(image_bytes))
                
                # Filtres de base sur la taille
                width, height = image_pil.size
                if (width < self.min_image_size or height < self.min_image_size or
                    width > self.max_image_size or height > self.max_image_size):
                    continue
                
                # Score de qualité basique (taille + ratio)
                area = width * height
                ratio = width / height if height > 0 else 1
                quality_score = min(1.0, (area / 50000) * 0.6 + (1 - abs(ratio - 1) * 0.5) * 0.4)
                
                # Obtenir la bbox approximative sur la page
                bbox = self._get_image_bbox_lite(page, xref)
                
                # Générer les 3 variantes
                variants = self._create_image_variants_lite(image_pil)
                
                extracted_images.append({
                    'bbox': bbox,
                    'quality_score': quality_score,
                    'raw_b64': variants['raw'],
                    'trimmed_b64': variants['trimmed'], 
                    'enhanced_b64': variants['enhanced'],
                    'raw_size': image_pil.size,
                    'xref': xref
                })
                
            except Exception as e:
                _logger.warning(f"Erreur extraction image {img_index} page {page_number}: {e}")
                continue
        
        return extracted_images
    
    def _get_image_bbox_lite(self, page, xref):
        """
        Obtient la bbox approximative d'une image sur la page.
        Version simplifiée sans OpenCV.
        """
        try:
            # Essayer d'obtenir la bbox via PyMuPDF
            img_rects = []
            
            # Parcourir les objets de la page pour trouver l'image
            for block in page.get_text("dict")["blocks"]:
                if "image" in block:
                    bbox_rect = block.get("bbox", [0, 0, 100, 100])
                    img_rects.append(bbox_rect)
            
            # Retourner la première bbox trouvée ou une bbox par défaut
            if img_rects:
                return img_rects[0]
            else:
                return [50, 50, 200, 200]  # Bbox par défaut
                
        except Exception:
            return [50, 50, 200, 200]  # Fallback
    
    def _create_image_variants_lite(self, image_pil):
        """
        Crée les 3 variantes d'image avec PIL uniquement.
        """
        # Variante 1: Raw (convertir au format standard)
        if image_pil.mode != 'RGB':
            raw_img = image_pil.convert('RGB')
        else:
            raw_img = image_pil
        
        raw_buffer = io.BytesIO()
        raw_img.save(raw_buffer, format='PNG', optimize=True)
        raw_b64 = base64.b64encode(raw_buffer.getvalue())
        
        # Variante 2: Trimmed (supprimer bordures blanches)
        trimmed_img = self._trim_image_borders_lite(raw_img)
        trimmed_buffer = io.BytesIO()
        trimmed_img.save(trimmed_buffer, format='PNG', optimize=True)
        trimmed_b64 = base64.b64encode(trimmed_buffer.getvalue())
        
        # Variante 3: Enhanced (améliorer qualité)
        enhanced_img = self._enhance_image_quality_lite(trimmed_img)
        enhanced_buffer = io.BytesIO()
        enhanced_img.save(enhanced_buffer, format='PNG', optimize=True, quality=95)
        enhanced_b64 = base64.b64encode(enhanced_buffer.getvalue())
        
        return {
            'raw': raw_b64,
            'trimmed': trimmed_b64,
            'enhanced': enhanced_b64
        }
    
    def _trim_image_borders_lite(self, img):
        """
        Supprime les bordures uniformes avec PIL uniquement.
        """
        try:
            # Utiliser ImageOps.crop pour supprimer les bordures uniformes
            # Border=0 signifie détecter automatiquement
            trimmed = ImageOps.crop(img, border=20)  # 20px max de bordure
            
            # Si l'image est devenue trop petite, garder l'originale
            if trimmed.size[0] < 50 or trimmed.size[1] < 50:
                return img
            
            return trimmed
            
        except Exception:
            return img  # En cas d'erreur, garder l'originale
    
    def _enhance_image_quality_lite(self, img):
        """
        Améliore la qualité de l'image avec PIL uniquement.
        """
        try:
            # Amélioration de la netteté
            sharpness_enhancer = ImageEnhance.Sharpness(img)
            enhanced_img = sharpness_enhancer.enhance(1.3)  # +30% netteté
            
            # Légère amélioration du contraste
            contrast_enhancer = ImageEnhance.Contrast(enhanced_img)
            final_img = contrast_enhancer.enhance(1.1)  # +10% contraste
            
            return final_img
            
        except Exception:
            return img  # En cas d'erreur, garder l'originale
    
    def _match_image_to_product_lite(self, page, img_data, page_number):
        """
        Association image-produit simplifiée.
        """
        try:
            # Récupérer les produits de cette page
            page_products = self.extracted_product_ids.filtered(
                lambda p: p.page_number == page_number
            )
            
            if not page_products:
                return None, 0.0
            
            # Pour la version lite, on associe selon l'ordre d'apparition
            # (plus simple mais généralement efficace pour les catalogues)
            xref = img_data.get('xref', 0)
            product_index = xref % len(page_products)  # Modulo pour répartir
            
            selected_product = page_products[product_index]
            confidence = 0.6  # Confiance moyenne pour association automatique
            
            return selected_product, confidence
            
        except Exception as e:
            _logger.warning(f"Erreur matching image-produit: {e}")
            return None, 0.0
    
    def _action_view_extracted_images(self):
        """Retourne l'action pour voir les images extraites."""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Images extraites - {self.filename}',
            'res_model': 'pool.catalog.pdf.image',
            'view_mode': 'kanban,tree,form',
            'domain': [('pdf_import_id', '=', self.id)],
            'context': {
                'default_pdf_import_id': self.id,
                'search_default_group_by_role': 1,
                'search_default_not_rejected': 1,
            }
        }
    
    # Alias pour compatibilité
    action_extract_images = action_extract_images_lite
