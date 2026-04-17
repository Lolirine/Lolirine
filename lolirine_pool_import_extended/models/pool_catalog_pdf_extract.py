# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_extract.py
===========================
Extension du modèle pool.catalog.pdf.import pour l'extraction d'images.
Ajoute la méthode action_extract_images() et le matching automatique.
"""

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import base64
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
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
    
    # Paramètres d'extraction
    min_image_area = fields.Integer(
        string='Surface minimum (px²)',
        default=2000,
        help="Surface minimum pour considérer une région comme une photo produit"
    )
    max_image_area = fields.Integer(
        string='Surface maximum (px²)', 
        default=100000,
        help="Surface maximum pour éviter les grandes images de fond"
    )
    min_aspect_ratio = fields.Float(
        string='Ratio minimum',
        default=0.2,
        digits=(3, 2),
        help="Ratio largeur/hauteur minimum (0.2 = très vertical autorisé)"
    )
    max_aspect_ratio = fields.Float(
        string='Ratio maximum',
        default=5.0,
        digits=(3, 2),
        help="Ratio largeur/hauteur maximum (5.0 = très horizontal autorisé)"
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
    
    def action_extract_images(self):
        """
        Lance l'extraction d'images depuis le PDF.
        Traitement page par page avec checkpoint pour resumabilité.
        """
        self.ensure_one()
        
        if not self.pdf_file:
            raise UserError("Aucun fichier PDF n'est attaché à cet import.")
        
        if self.image_extraction_state == 'in_progress':
            raise UserError("Une extraction est déjà en cours. Attendez qu'elle se termine.")
        
        try:
            self.write({
                'image_extraction_state': 'in_progress',
                'image_extraction_progress': 0.0
            })
            
            # Décoder le PDF
            pdf_data = base64.b64decode(self.pdf_file)
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            total_pages = len(doc)
            
            _logger.info(f"Début extraction images PDF {self.filename}: {total_pages} pages")
            
            extracted_count = 0
            
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    
                    # Extraire les images de cette page
                    page_images = self._extract_page_images(page, page_num + 1)
                    
                    # Associer automatiquement aux produits
                    for img_data in page_images:
                        matched_product, confidence = self._match_image_to_product(
                            page, img_data, page_num + 1
                        )
                        
                        # Créer l'enregistrement image
                        image_vals = {
                            'pdf_import_id': self.id,
                            'page_number': page_num + 1,
                            'bbox_x': img_data['bbox'][0],
                            'bbox_y': img_data['bbox'][1], 
                            'bbox_width': img_data['bbox'][2],
                            'bbox_height': img_data['bbox'][3],
                            'quality_score': img_data['quality_score'],
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
                    
                    # Commit intermédiaire tous les 5 pages pour resumabilité
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
            
            # Notification et ouverture de la vue
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
    
    def _extract_page_images(self, page, page_number):
        """
        Extrait les images d'une page PDF.
        Retourne une liste d'objets image avec les 3 variantes.
        """
        # Convertir la page en image pour la détection de contours
        mat = fitz.Matrix(2, 2)  # 2x zoom pour meilleure détection
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Charger avec OpenCV pour détection
        nparr = np.frombuffer(img_data, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_cv is None:
            return []
        
        # Redimensionner selon le facteur de zoom pour avoir les vraies coordonnées
        height, width = img_cv.shape[:2]
        original_height, original_width = page.rect.height, page.rect.width
        scale_x = width / (original_width * 2)  # Facteur 2 du zoom
        scale_y = height / (original_height * 2)
        
        # Détecter les régions de produits
        product_regions = self._detect_product_regions(img_cv)
        
        extracted_images = []
        
        for region in product_regions:
            # Convertir les coordonnées vers l'espace PDF original
            bbox_scaled = (
                region['bbox'][0] / scale_x,
                region['bbox'][1] / scale_y,
                region['bbox'][2] / scale_x,
                region['bbox'][3] / scale_y
            )
            
            # Extraire l'image à partir du PDF original (meilleure qualité)
            try:
                variants = self._extract_image_variants(page, bbox_scaled)
                if variants:
                    extracted_images.append({
                        'bbox': bbox_scaled,
                        'quality_score': region['quality_score'],
                        'raw_b64': variants['raw'],
                        'trimmed_b64': variants['trimmed'],
                        'enhanced_b64': variants['enhanced'],
                        'raw_size': variants['raw_size']
                    })
            except Exception as e:
                _logger.warning(f"Erreur extraction région page {page_number}: {e}")
                continue
        
        return extracted_images
    
    def _detect_product_regions(self, img_cv):
        """
        Détecte les régions contenant des photos de produits.
        Algorithme optimisé basé sur les tests de validation.
        """
        height, width = img_cv.shape[:2]
        
        # Conversion niveaux de gris
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Seuillage adaptatif pour détecter les objets
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Inverser: objets en blanc sur fond noir
        binary = cv2.bitwise_not(binary)
        
        # Opérations morphologiques
        kernel_open = np.ones((3, 3), np.uint8)
        kernel_close = np.ones((8, 8), np.uint8)
        
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
        
        # Trouver les contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filtres de base
            if area < self.min_image_area or area > self.max_image_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            ratio = w / h if h > 0 else 0
            
            if ratio < self.min_aspect_ratio or ratio > self.max_aspect_ratio:
                continue
            
            # Éviter les bords de page
            margin = 50
            if (y < margin or y + h > height - margin or 
                x < margin or x + w > width - margin):
                continue
            
            # Calculer la densité de l'objet
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            roi_mask = mask[y:y+h, x:x+w]
            density = np.sum(roi_mask > 0) / (w * h)
            
            if density < 0.1:  # Trop sparse
                continue
            
            # Score de qualité
            center_x = x + w/2
            left_preference = max(0, 1 - (center_x / (width * 0.6)))
            
            quality_score = (
                (area / 50000) * 0.4 +
                (1 - abs(ratio - 1)) * 0.3 +
                left_preference * 0.2 +
                density * 0.1
            )
            
            candidates.append({
                'bbox': (x, y, w, h),
                'quality_score': min(1.0, quality_score)
            })
        
        # Trier par score et supprimer chevauchements
        candidates.sort(key=lambda c: c['quality_score'], reverse=True)
        
        filtered = []
        for candidate in candidates:
            overlap = False
            x1, y1, w1, h1 = candidate['bbox']
            
            for existing in filtered:
                x2, y2, w2, h2 = existing['bbox']
                
                # Calculer IoU
                ix = max(x1, x2)
                iy = max(y1, y2)
                iw = max(0, min(x1+w1, x2+w2) - ix)
                ih = max(0, min(y1+h1, y2+h2) - iy)
                intersection = iw * ih
                union = w1*h1 + w2*h2 - intersection
                
                if union > 0 and intersection / union > 0.3:
                    overlap = True
                    break
            
            if not overlap:
                filtered.append(candidate)
        
        return filtered[:8]  # Maximum 8 images par page
    
    def _extract_image_variants(self, page, bbox):
        """
        Extrait les 3 variantes d'une image depuis le PDF.
        """
        x, y, w, h = bbox
        
        # Créer le rectangle de clipping avec padding
        padding = 10
        clip_rect = fitz.Rect(
            max(0, x - padding),
            max(0, y - padding), 
            min(page.rect.width, x + w + padding),
            min(page.rect.height, y + h + padding)
        )
        
        # Extraire l'image à haute résolution
        mat = fitz.Matrix(3, 3)  # 300 DPI équivalent
        pix = page.get_pixmap(matrix=mat, clip=clip_rect)
        
        if pix.width == 0 or pix.height == 0:
            return None
        
        # Convertir en PIL
        img_data = pix.tobytes("png")
        pix.clear()
        
        raw_img = Image.open(io.BytesIO(img_data))
        raw_size = raw_img.size
        
        # Variante 1: Raw (juste encoder)
        raw_buffer = io.BytesIO()
        raw_img.save(raw_buffer, format='PNG', optimize=True)
        raw_b64 = base64.b64encode(raw_buffer.getvalue())
        
        # Variante 2: Trimmed (bordures supprimées)
        trimmed_img = self._trim_image_borders(raw_img)
        trimmed_buffer = io.BytesIO()
        trimmed_img.save(trimmed_buffer, format='PNG', optimize=True)
        trimmed_b64 = base64.b64encode(trimmed_buffer.getvalue())
        
        # Variante 3: Enhanced (netteté + contraste, correction du flou)
        enhanced_img = self._enhance_image_quality(trimmed_img)
        enhanced_buffer = io.BytesIO()
        enhanced_img.save(enhanced_buffer, format='PNG', optimize=True, quality=95)
        enhanced_b64 = base64.b64encode(enhanced_buffer.getvalue())
        
        return {
            'raw': raw_b64,
            'trimmed': trimmed_b64,
            'enhanced': enhanced_b64,
            'raw_size': raw_size
        }
    
    def _trim_image_borders(self, img):
        """
        Supprime les bordures uniformes d'une image.
        Version optimisée pour les produits sur fond blanc.
        """
        # Convertir en array numpy
        arr = np.array(img.convert('RGB'))
        
        # Détecter les bords de l'objet principal
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        # Seuillage adaptatif
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Trouver le plus grand contour (objet principal)
        contours, _ = cv2.findContours(cv2.bitwise_not(binary), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return img  # Pas de contour, garder l'original
        
        # Plus grand contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Ajouter un padding
        padding = 15
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(arr.shape[1] - x, w + 2*padding)
        h = min(arr.shape[0] - y, h + 2*padding)
        
        return img.crop((x, y, x+w, y+h))
    
    def _enhance_image_quality(self, img):
        """
        Améliore la qualité de l'image pour l'e-commerce.
        Correction spécifique du flou mentionné par l'utilisateur.
        """
        try:
            # Conversion RGB si nécessaire
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Unsharp masking pour corriger le flou
            # 1. Version légèrement floutée
            blurred = img.filter(ImageFilter.GaussianBlur(radius=0.8))
            
            # 2. Calculer le masque de netteté
            img_array = np.array(img, dtype=np.float32)
            blur_array = np.array(blurred, dtype=np.float32)
            mask = img_array - blur_array
            
            # 3. Appliquer le masque (facteur 0.4 pour netteté sans sur-traitement)
            sharpened = img_array + mask * 0.4
            sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
            
            # 4. Légère amélioration du contraste
            enhanced_img = Image.fromarray(sharpened)
            enhancer = ImageEnhance.Contrast(enhanced_img)
            final_img = enhancer.enhance(1.08)  # +8% contraste subtil
            
            return final_img
            
        except Exception as e:
            _logger.warning(f"Erreur amélioration image: {e}")
            return img  # Retourner l'original en cas d'erreur
    
    def _match_image_to_product(self, page, img_data, page_number):
        """
        Associe automatiquement une image à un produit par proximité textuelle.
        Retourne (produit, score_confiance).
        """
        try:
            # Récupérer les produits de cette page
            page_products = self.extracted_product_ids.filtered(
                lambda p: p.page_number == page_number
            )
            
            if not page_products:
                return None, 0.0
            
            # Extraire les blocs de texte de la page
            blocks = page.get_text("blocks")
            
            # Coordonnées du centre de l'image
            bbox = img_data['bbox']
            img_center_x = bbox[0] + bbox[2] / 2
            img_center_y = bbox[1] + bbox[3] / 2
            
            best_product = None
            best_distance = float('inf')
            best_confidence = 0.0
            
            for product in page_products:
                # Chercher la référence du produit dans les blocs de texte
                if not product.supplier_ref:
                    continue
                
                ref = product.supplier_ref.strip()
                
                for block in blocks:
                    x0, y0, x1, y1, text, *_ = block
                    
                    # Vérifier si ce bloc contient la référence
                    if ref in text:
                        # Calculer la distance au centre de l'image
                        block_center_x = (x0 + x1) / 2
                        block_center_y = (y0 + y1) / 2
                        
                        distance = math.sqrt(
                            (img_center_x - block_center_x) ** 2 + 
                            (img_center_y - block_center_y) ** 2
                        )
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_product = product
                            
                            # Score de confiance basé sur la distance
                            # Distance de 0-200 pixels = confiance 1.0-0.5
                            max_distance = 400
                            confidence = max(0.2, 1.0 - (distance / max_distance))
                            best_confidence = min(1.0, confidence)
            
            return best_product, best_confidence
            
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
    
    def action_view_images(self):
        """Action pour voir les images extraites."""
        self.ensure_one()
        return self._action_view_extracted_images()
    
    def action_reset_image_extraction(self):
        """Remet à zéro l'extraction d'images (supprime toutes les images extraites)."""
        self.ensure_one()
        
        if self.image_extraction_state == 'in_progress':
            raise UserError("Impossible de réinitialiser : extraction en cours.")
        
        # Supprimer toutes les images extraites
        self.extracted_image_ids.unlink()
        
        self.write({
            'images_extracted': False,
            'image_extraction_state': 'not_started',
            'image_extraction_progress': 0.0
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification', 
            'params': {
                'message': 'Extraction d\'images réinitialisée',
                'type': 'info'
            }
        }
