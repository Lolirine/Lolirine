# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_extract_SIMPLE.py
==================================
Version simplifiée avec filtrage intelligent mais sans nouveaux champs.
Compatible avec la structure existante.
"""

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import base64
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat
import fitz  # PyMuPDF
import io
import json
import math
import logging

_logger = logging.getLogger(__name__)


class PoolCatalogPdfImport(models.Model):
    _inherit = 'pool.catalog.pdf.import'
    
    def action_extract_images_advanced(self):
        """
        Extraction d'images avec filtrage intelligent simplifié.
        Compatible avec la structure existante.
        """
        self.ensure_one()
        
        if not self.source_pdf:
            raise UserError("Aucun fichier PDF n'est attaché à cet import.")
        
        try:
            # Décoder le PDF
            pdf_data = base64.b64decode(self.source_pdf)
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            total_pages = len(doc)
            
            _logger.info(f"🚀 Extraction intelligente PDF: {total_pages} pages")
            
            extracted_count = 0
            rejected_count = 0
            
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    
                    # EXTRACTION avec filtrage intelligent
                    page_images = self._extract_images_smart_simple(page, page_num + 1)
                    rejected_count += len([img for img in page_images if img.get('rejected', False)])
                    
                    # Ne garder que les images validées
                    valid_images = [img for img in page_images if not img.get('rejected', False)]
                    
                    # Créer les enregistrements d'images
                    for img_data in valid_images:
                        image_vals = {
                            'pdf_import_id': self.id,
                            'page_number': page_num + 1,
                            'quality_score': img_data.get('quality_score', 0.7),
                            'confidence_score': 0.7,  # Confiance par défaut
                            'image_raw': img_data['raw_b64'],
                            'image_enhanced': img_data.get('enhanced_b64', img_data['raw_b64']),
                            'original_width': img_data['raw_size'][0],
                            'original_height': img_data['raw_size'][1],
                            'file_size_kb': len(base64.b64decode(img_data['raw_b64'])) / 1024,
                            'notes': img_data.get('analysis_summary', 'Filtrage intelligent appliqué')
                        }
                        
                        self.env['pool.catalog.pdf.image'].create(image_vals)
                        extracted_count += 1
                    
                    # Log progression
                    if (page_num + 1) % 5 == 0:
                        _logger.info(f"📊 Page {page_num + 1}/{total_pages}: {len(valid_images)} images ✅, {rejected_count} rejetées ❌")
                
                except Exception as e:
                    _logger.error(f"❌ Erreur extraction page {page_num + 1}: {str(e)}")
                    continue
            
            doc.close()
            
            # Message de succès
            success_message = f"🎉 Extraction intelligente terminée !\n"
            success_message += f"✅ {extracted_count} vraies images extraites\n" 
            success_message += f"❌ {rejected_count} images parasites rejetées\n"
            if extracted_count + rejected_count > 0:
                precision = (extracted_count/(extracted_count+rejected_count)*100)
                success_message += f"📊 Taux de précision: {precision:.1f}%"
            
            _logger.info(success_message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Extraction Intelligente Réussie',
                    'message': success_message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f"❌ Erreur extraction images intelligente: {str(e)}")
            raise UserError(f"Erreur lors de l'extraction intelligente: {str(e)}")

    def _extract_images_smart_simple(self, page, page_number):
        """
        🧠 EXTRACTION AVEC FILTRAGE INTELLIGENT SIMPLE
        Version simplifiée sans dépendances sur nouveaux champs.
        """
        extracted_images = []
        
        # Paramètres de filtrage (valeurs par défaut)
        min_image_size = 100
        max_image_size = 800
        min_color_variance = 500.0
        min_edge_density = 0.15
        max_text_ratio = 0.8
        
        # Récupérer la liste des images embarquées sur cette page
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]  # Référence de l'image dans le PDF
                
                # Extraire l'image
                base_img = page.parent.extract_image(xref)
                image_bytes = base_img["image"]
                
                # Convertir en PIL Image
                image_pil = Image.open(io.BytesIO(image_bytes))
                
                # ÉTAPE 1: Filtres de base (taille)
                width, height = image_pil.size
                if (width < min_image_size or height < min_image_size or
                    width > max_image_size or height > max_image_size):
                    continue
                
                # ÉTAPE 2: FILTRAGE INTELLIGENT 🧠
                is_valid, analysis = self._analyze_image_content_simple(
                    image_pil, min_color_variance, min_edge_density, max_text_ratio
                )
                
                if not is_valid:
                    # Enregistrer comme image rejetée pour diagnostic
                    extracted_images.append({
                        'rejected': True,
                        'filter_reason': analysis['rejection_reason'],
                        'raw_size': image_pil.size,
                        'xref': xref
                    })
                    continue
                
                # ÉTAPE 3: Score de qualité amélioré
                quality_score = self._calculate_smart_quality_score(image_pil, analysis)
                
                # ÉTAPE 4: Générer variantes
                variants = self._create_smart_variants(image_pil)
                
                extracted_images.append({
                    'quality_score': quality_score,
                    'raw_b64': variants['raw'],
                    'enhanced_b64': variants['enhanced'],
                    'raw_size': image_pil.size,
                    'xref': xref,
                    'rejected': False,
                    'analysis_summary': analysis.get('summary', 'Analysé')
                })
                
            except Exception as e:
                _logger.warning(f"⚠️ Erreur analyse image {img_index} page {page_number}: {e}")
                continue
        
        return extracted_images

    def _analyze_image_content_simple(self, image_pil, min_variance, min_density, max_text):
        """
        🔍 ANALYSE INTELLIGENTE SIMPLIFIÉE
        """
        try:
            # Convertir en RGB si nécessaire
            if image_pil.mode != 'RGB':
                image_rgb = image_pil.convert('RGB')
            else:
                image_rgb = image_pil
            
            # CRITÈRE 1: Variance des couleurs
            color_variance = self._calculate_color_variance_simple(image_rgb)
            
            # CRITÈRE 2: Densité des contours
            edge_density = self._calculate_edge_density_simple(image_rgb)
            
            # CRITÈRE 3: Détection patterns texte
            text_ratio = self._detect_text_patterns_simple(image_rgb)
            
            # DÉCISION
            rejection_reasons = []
            
            if color_variance < min_variance:
                rejection_reasons.append(f"Trop monochrome (var:{color_variance:.0f})")
            
            if edge_density < min_density:
                rejection_reasons.append(f"Trop uniforme (edge:{edge_density:.3f})")
            
            if text_ratio > max_text:
                rejection_reasons.append(f"Ressemble à du texte (txt:{text_ratio:.2f})")
            
            is_valid = len(rejection_reasons) == 0
            
            analysis = {
                'color_variance': color_variance,
                'edge_density': edge_density, 
                'text_ratio': text_ratio,
                'summary': f"V:{color_variance:.0f}, E:{edge_density:.2f}, T:{text_ratio:.2f}"
            }
            
            if not is_valid:
                analysis['rejection_reason'] = " | ".join(rejection_reasons)
            
            return is_valid, analysis
            
        except Exception as e:
            _logger.warning(f"⚠️ Erreur analyse: {e}")
            return True, {'summary': f'Erreur: {e}'}

    def _calculate_color_variance_simple(self, image_rgb):
        """Calcule la variance des couleurs."""
        try:
            stats = ImageStat.Stat(image_rgb)
            return sum(stats.var)  # Variance R + G + B
        except:
            return 1000  # Valeur par défaut

    def _calculate_edge_density_simple(self, image_rgb):
        """Calcule la densité des contours."""
        try:
            gray = image_rgb.convert('L')
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_pixels = sum(1 for pixel in edges.getdata() if pixel > 50)
            total_pixels = edges.size[0] * edges.size[1]
            return edge_pixels / total_pixels if total_pixels > 0 else 0
        except:
            return 0.5

    def _detect_text_patterns_simple(self, image_rgb):
        """Détecte les motifs texte."""
        try:
            gray = image_rgb.convert('L')
            binary = gray.point(lambda p: 255 if p > 128 else 0)
            width, height = binary.size
            
            # Échantillonner quelques lignes
            sample_lines = range(10, height-10, max(1, height//20))
            horizontal_runs = 0
            
            for y in sample_lines:
                pixels = [binary.getpixel((x, y)) for x in range(width)]
                transitions = sum(1 for i in range(1, len(pixels)) 
                                if pixels[i] != pixels[i-1])
                
                if transitions > width * 0.1:
                    horizontal_runs += 1
            
            return horizontal_runs / len(sample_lines) if sample_lines else 0
            
        except:
            return 0.3

    def _calculate_smart_quality_score(self, image_pil, analysis):
        """Score de qualité intelligent."""
        try:
            width, height = image_pil.size
            area = width * height
            ratio = width / height if height > 0 else 1
            
            # Score de base
            base_score = min(1.0, (area / 50000) * 0.4 + (1 - abs(ratio - 1) * 0.5) * 0.2)
            
            # Bonus contenu
            content_bonus = 0
            if 'color_variance' in analysis:
                content_bonus += min(0.2, analysis['color_variance'] / 2500 * 0.2)
            if 'edge_density' in analysis:
                content_bonus += min(0.2, analysis['edge_density'] * 0.2)
            
            return min(1.0, base_score + content_bonus)
            
        except:
            return 0.7

    def _create_smart_variants(self, image_pil):
        """Crée variantes optimisées."""
        try:
            # Raw
            if image_pil.mode != 'RGB':
                raw_img = image_pil.convert('RGB')
            else:
                raw_img = image_pil
            
            raw_buffer = io.BytesIO()
            raw_img.save(raw_buffer, format='PNG', optimize=True)
            raw_b64 = base64.b64encode(raw_buffer.getvalue())
            
            # Enhanced
            enhanced_img = self._enhance_smart(raw_img)
            enhanced_buffer = io.BytesIO()
            enhanced_img.save(enhanced_buffer, format='PNG', optimize=True)
            enhanced_b64 = base64.b64encode(enhanced_buffer.getvalue())
            
            return {
                'raw': raw_b64,
                'enhanced': enhanced_b64
            }
        except:
            return {'raw': raw_b64, 'enhanced': raw_b64}

    def _enhance_smart(self, img):
        """Amélioration intelligente."""
        try:
            # Netteté
            sharpness = ImageEnhance.Sharpness(img)
            enhanced = sharpness.enhance(1.2)
            
            # Contraste
            contrast = ImageEnhance.Contrast(enhanced)
            return contrast.enhance(1.1)
        except:
            return img

    # Alias pour compatibilité
    action_extract_images = action_extract_images_advanced
    action_extract_images_lite = action_extract_images_advanced
