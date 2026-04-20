# -*- coding: utf-8 -*-
"""
advanced_image_extractor.py - SPRINT 1: DÉTOURAGE PRÉCIS
========================================================
Extracteur d'images amélioré pour éliminer l'aspect "scanner médical"
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import fitz  # PyMuPDF
import io
import base64
import logging
from typing import List, Dict, Tuple, Optional

_logger = logging.getLogger(__name__)


class AdvancedImageExtractor:
    """Extracteur d'images avec détourage précis et qualité optimisée"""
    
    def __init__(self):
        self.min_image_area = 10000  # Surface minimale (100x100px)
        self.min_aspect_ratio = 0.3   # Ratio largeur/hauteur minimal
        self.max_aspect_ratio = 3.0   # Ratio maximal
        self.border_threshold = 10    # Pixels pour détection bordures
        
    def extract_images_with_precise_cropping(self, pdf_document, page_num: int) -> List[Dict]:
        """
        Extraction d'images avec détourage précis et amélioration qualité
        
        Returns:
            List[Dict]: Images avec variantes Raw, Clean, Enhanced
        """
        _logger.info(f"Extraction avancée page {page_num}")
        
        try:
            page = pdf_document.load_page(page_num - 1)
            image_list = page.get_images()
            
            extracted_images = []
            
            for img_index, img in enumerate(image_list):
                try:
                    # Extraction image brute
                    xref = img[0]
                    pix = fitz.Pixmap(pdf_document, xref)
                    
                    # Conversion en PIL pour traitement avancé
                    if pix.n - pix.alpha < 4:  # GRAY ou RGB
                        img_data = pix.tobytes("ppm")
                        raw_image = Image.open(io.BytesIO(img_data))
                    else:
                        pix1 = fitz.Pixmap(fitz.csRGB, pix)
                        img_data = pix1.tobytes("ppm")
                        raw_image = Image.open(io.BytesIO(img_data))
                        pix1 = None
                    
                    pix = None
                    
                    # Filtrer les images trop petites
                    if not self._is_valid_image(raw_image):
                        continue
                    
                    # Traitement en 3 variantes
                    variants = self._create_image_variants(raw_image)
                    
                    # Calcul score qualité amélioré
                    quality_score = self._calculate_enhanced_quality_score(variants['enhanced'])
                    
                    # Position dans le PDF (approximative)
                    bbox = self._estimate_image_position(page, img_index)
                    
                    extracted_images.append({
                        'page_number': page_num,
                        'image_index': img_index,
                        'bbox': bbox,
                        'quality_score': quality_score,
                        'variants': variants,
                        'dimensions': raw_image.size,
                        'enhancement_notes': 'Détourage précis + amélioration qualité'
                    })
                    
                    _logger.debug(f"Image {img_index}: qualité {quality_score:.3f}")
                    
                except Exception as e:
                    _logger.error(f"Erreur traitement image {img_index}: {e}")
                    continue
            
            _logger.info(f"Page {page_num}: {len(extracted_images)} images extraites")
            return extracted_images
            
        except Exception as e:
            _logger.error(f"Erreur extraction page {page_num}: {e}")
            return []
    
    def _is_valid_image(self, image: Image.Image) -> bool:
        """Valider si l'image mérite d'être conservée"""
        width, height = image.size
        area = width * height
        
        # Filtres de base
        if area < self.min_image_area:
            return False
            
        aspect_ratio = width / height
        if not (self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio):
            return False
        
        # Détection images quasi-vides (logos blancs, etc.)
        if self._is_mostly_empty(image):
            return False
            
        return True
    
    def _is_mostly_empty(self, image: Image.Image) -> bool:
        """Détecter les images quasi-vides ou uniformes"""
        # Conversion en niveaux de gris pour analyse
        gray = image.convert('L')
        
        # Histogramme de l'image
        histogram = gray.histogram()
        
        # Si 90% des pixels sont dans la même plage de couleur
        max_count = max(histogram)
        total_pixels = sum(histogram)
        
        if max_count > total_pixels * 0.9:
            return True
            
        return False
    
    def _create_image_variants(self, raw_image: Image.Image) -> Dict[str, bytes]:
        """Créer 3 variantes : Raw, Clean (détourée), Enhanced (optimisée)"""
        variants = {}
        
        # Variante 1: Raw (originale)
        variants['raw'] = self._image_to_base64(raw_image)
        
        # Variante 2: Clean (détourage précis)
        clean_image = self._precise_crop_borders(raw_image)
        variants['clean'] = self._image_to_base64(clean_image)
        
        # Variante 3: Enhanced (optimisation e-commerce)
        enhanced_image = self._enhance_for_ecommerce(clean_image)
        variants['enhanced'] = self._image_to_base64(enhanced_image)
        
        return variants
    
    def _precise_crop_borders(self, image: Image.Image) -> Image.Image:
        """Détourage précis pour éliminer bordures grises/blanches"""
        # Conversion en numpy pour OpenCV
        img_array = np.array(image)
        
        # Si image en couleur, conversion BGR pour OpenCV
        if len(img_array.shape) == 3:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_array
        
        # Conversion en niveaux de gris pour détection contours
        if len(img_bgr.shape) == 3:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_bgr
        
        # Seuillage adaptatif pour contours
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Inversion si nécessaire (fond noir -> fond blanc)
        if np.mean(thresh) < 127:
            thresh = cv2.bitwise_not(thresh)
        
        # Recherche contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Plus grand contour = probablement l'objet principal
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Rectangle englobant
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Marges de sécurité (5% de chaque côté)
            margin_x = max(5, int(w * 0.05))
            margin_y = max(5, int(h * 0.05))
            
            # Ajustement avec marges
            x = max(0, x - margin_x)
            y = max(0, y - margin_y)
            w = min(image.width - x, w + 2 * margin_x)
            h = min(image.height - y, h + 2 * margin_y)
            
            # Recadrage
            cropped = image.crop((x, y, x + w, y + h))
            
            _logger.debug(f"Recadrage: {image.size} -> {cropped.size}")
            return cropped
        
        # Si pas de contour détecté, crop minimal des bordures
        return self._minimal_border_crop(image)
    
    def _minimal_border_crop(self, image: Image.Image) -> Image.Image:
        """Recadrage minimal des bordures uniformes"""
        # Détection bordures uniformes
        img_array = np.array(image)
        
        # Moyennes par ligne/colonne
        if len(img_array.shape) == 3:
            # Image couleur
            row_means = np.mean(img_array, axis=(1, 2))
            col_means = np.mean(img_array, axis=(0, 2))
        else:
            # Image grise
            row_means = np.mean(img_array, axis=1)
            col_means = np.mean(img_array, axis=0)
        
        # Détection bordures (variation faible)
        threshold = np.std(row_means) / 2
        
        # Trouve les limites non-uniformes
        top = 0
        bottom = len(row_means)
        left = 0
        right = len(col_means)
        
        # Top
        for i in range(len(row_means)):
            if abs(row_means[i] - row_means[0]) > threshold:
                top = max(0, i - self.border_threshold)
                break
        
        # Bottom
        for i in range(len(row_means) - 1, -1, -1):
            if abs(row_means[i] - row_means[-1]) > threshold:
                bottom = min(len(row_means), i + self.border_threshold)
                break
        
        # Left & Right (même logique)
        for i in range(len(col_means)):
            if abs(col_means[i] - col_means[0]) > threshold:
                left = max(0, i - self.border_threshold)
                break
                
        for i in range(len(col_means) - 1, -1, -1):
            if abs(col_means[i] - col_means[-1]) > threshold:
                right = min(len(col_means), i + self.border_threshold)
                break
        
        # Recadrage si significatif
        if (bottom - top) > image.height * 0.5 and (right - left) > image.width * 0.5:
            return image.crop((left, top, right, bottom))
        
        return image
    
    def _enhance_for_ecommerce(self, image: Image.Image) -> Image.Image:
        """Optimisation pour e-commerce: netteté, contraste, luminosité"""
        # Amélioration du contraste adaptatif
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)  # +20% contraste
        
        # Netteté
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)  # +30% netteté
        
        # Luminosité légère si trop sombre
        enhancer = ImageEnhance.Brightness(image)
        # Calcul luminosité moyenne
        gray_version = image.convert('L')
        mean_brightness = np.mean(np.array(gray_version))
        
        if mean_brightness < 120:  # Image sombre
            brightness_factor = 1.1
            image = enhancer.enhance(brightness_factor)
        
        # Filtre de netteté final
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=10))
        
        return image
    
    def _calculate_enhanced_quality_score(self, image: Image.Image) -> float:
        """Score qualité amélioré basé sur plusieurs critères"""
        try:
            # Conversion numpy pour calculs
            img_array = np.array(image.convert('L'))
            
            # Critère 1: Netteté (variance Laplacien)
            laplacian_var = cv2.Laplacian(img_array, cv2.CV_64F).var()
            sharpness_score = min(1.0, laplacian_var / 1000.0)
            
            # Critère 2: Contraste (écart-type)
            contrast_score = min(1.0, np.std(img_array) / 127.0)
            
            # Critère 3: Richesse détails (gradient)
            grad_x = cv2.Sobel(img_array, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(img_array, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            detail_score = min(1.0, np.mean(gradient_magnitude) / 50.0)
            
            # Critère 4: Taille (bonus pour images plus grandes)
            width, height = image.size
            size_bonus = min(1.0, (width * height) / 100000.0)
            
            # Score combiné pondéré
            quality_score = (
                0.4 * sharpness_score +    # 40% netteté
                0.3 * contrast_score +     # 30% contraste  
                0.2 * detail_score +       # 20% détails
                0.1 * size_bonus          # 10% taille
            )
            
            return round(quality_score, 3)
            
        except Exception as e:
            _logger.error(f"Erreur calcul qualité: {e}")
            return 0.5  # Score par défaut
    
    def _estimate_image_position(self, page, img_index: int) -> Tuple[float, float, float, float]:
        """Estimation position image dans la page (pour OCR contextuel futur)"""
        # Position approximative basée sur l'ordre d'extraction
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        # Grille approximative 3x3
        grid_x = img_index % 3
        grid_y = img_index // 3
        
        x = (grid_x * page_width / 3) + (page_width / 6)
        y = (grid_y * page_height / 3) + (page_height / 6) 
        w = page_width / 4
        h = page_height / 4
        
        return (x, y, w, h)
    
    def _image_to_base64(self, image: Image.Image) -> bytes:
        """Conversion Image PIL -> Base64 pour stockage Odoo"""
        buffer = io.BytesIO()
        
        # Format optimal selon le type d'image
        if image.mode in ['RGBA', 'LA']:
            format_img = 'PNG'  # Transparence
        else:
            format_img = 'JPEG'  # Plus compact
            
        image.save(buffer, format=format_img, quality=90, optimize=True)
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue())


# Fonctions d'intégration Odoo
def extract_images_advanced_v2(pdf_data: bytes, page_start: int, page_end: int) -> List[Dict]:
    """
    Point d'entrée principal pour l'extraction avancée
    
    Args:
        pdf_data: Données PDF en bytes
        page_start, page_end: Plage de pages
        
    Returns:
        List[Dict]: Images extraites avec variantes et métadonnées
    """
    extractor = AdvancedImageExtractor()
    all_images = []
    
    try:
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        
        for page_num in range(page_start, page_end + 1):
            if page_num <= pdf_document.page_count:
                page_images = extractor.extract_images_with_precise_cropping(pdf_document, page_num)
                all_images.extend(page_images)
        
        pdf_document.close()
        
    except Exception as e:
        _logger.error(f"Erreur extraction PDF: {e}")
        
    return all_images
