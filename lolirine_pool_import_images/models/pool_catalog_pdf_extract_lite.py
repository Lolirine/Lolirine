# -*- coding: utf-8 -*-
"""
pool_catalog_pdf_extract_ENHANCED.py
===================================
Version améliorée du filtrage d'images existant avec détection intelligente.
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
    
    # NOUVEAUX PARAMÈTRES DE FILTRAGE INTELLIGENT
    enable_smart_filtering = fields.Boolean(
        string='Filtrage intelligent',
        default=True,
        help="Activer la détection intelligente des vraies images produits"
    )
    min_color_variance = fields.Float(
        string='Variance couleur min',
        default=500.0,
        help="Variance minimale des couleurs pour considérer comme une vraie image"
    )
    min_edge_density = fields.Float(
        string='Densité contours min',
        default=0.15,
        help="Densité minimale de contours pour éviter les zones uniformes"
    )
    max_text_ratio = fields.Float(
        string='Ratio texte max',
        default=0.8,
        help="Ratio maximum de pixels 'texte-like' toléré dans l'image"
    )

    def action_extract_images_advanced(self):
        """
        Extraction d'images avec filtrage intelligent amélioré.
        Remplace action_extract_images_lite avec meilleure détection.
        """
        self.ensure_one()
        
        if not self.source_pdf:
            raise UserError("Aucun fichier PDF n'est attaché à cet import.")
        
        if self.image_extraction_state == 'in_progress':
            raise UserError("Une extraction est déjà en cours. Attendez qu'elle se termine.")
        
        try:
            self.write({
                'image_extraction_state': 'in_progress',
                'image_extraction_progress': 0.0
            })
            
            # Décoder le PDF
            pdf_data = base64.b64decode(self.source_pdf)
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            total_pages = len(doc)
            
            _logger.info(f"🚀 Extraction améliorée PDF {self.filename}: {total_pages} pages")
            
            extracted_count = 0
            rejected_count = 0
            
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    
                    # EXTRACTION AMÉLIORÉE avec filtrage intelligent
                    page_images = self._extract_images_with_smart_filtering(page, page_num + 1)
                    rejected_count += len([img for img in page_images if img.get('rejected', False)])
                    
                    # Ne garder que les images validées
                    valid_images = [img for img in page_images if not img.get('rejected', False)]
                    
                    # Associer automatiquement aux produits
                    for img_data in valid_images:
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
                            # NOUVEAUX CHAMPS pour diagnostic
                            'notes': img_data.get('filter_reason', ''),
                            'enhancement_notes': f"✅ Filtrage intelligent: {img_data.get('analysis_summary', 'OK')}"
                        }
                        
                        self.env['pool.catalog.pdf.image'].create(image_vals)
                        extracted_count += 1
                    
                    # Mise à jour progression
                    progress = ((page_num + 1) / total_pages) * 100
                    self.image_extraction_progress = progress
                    
                    # Commit intermédiaire tous les 5 pages
                    if (page_num + 1) % 5 == 0:
                        self.env.cr.commit()
                        _logger.info(f"📊 Page {page_num + 1}/{total_pages}: {len(valid_images)} images ✅, {rejected_count} rejetées ❌")
                
                except Exception as e:
                    _logger.error(f"❌ Erreur extraction page {page_num + 1}: {str(e)}")
                    continue
            
            doc.close()
            
            # Finalisation avec statistiques
            self.write({
                'image_extraction_state': 'completed',
                'image_extraction_progress': 100.0,
                'images_extracted': True
            })
            
            success_message = f"🎉 Extraction intelligente terminée !\n"
            success_message += f"✅ {extracted_count} vraies images extraites\n" 
            success_message += f"❌ {rejected_count} images parasites rejetées\n"
            success_message += f"📊 Taux de précision: {(extracted_count/(extracted_count+rejected_count)*100):.1f}%"
            
            _logger.info(success_message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Extraction Intelligente Réussie',
                    'message': success_message,
                    'type': 'success',
                    'sticky': True,
                },
                'context': {'next_action': self._action_view_extracted_images()}
            }
            
        except Exception as e:
            _logger.error(f"❌ Erreur extraction images améliorée: {str(e)}")
            self.write({
                'image_extraction_state': 'error',
                'image_extraction_progress': 0.0
            })
            raise UserError(f"Erreur lors de l'extraction améliorée: {str(e)}")

    def _extract_images_with_smart_filtering(self, page, page_number):
        """
        🧠 EXTRACTION AVEC FILTRAGE INTELLIGENT
        Rejette les fragments de texte, logos, bordures, etc.
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
                
                # Convertir en PIL Image
                image_pil = Image.open(io.BytesIO(image_bytes))
                
                # ÉTAPE 1: Filtres de base (taille)
                width, height = image_pil.size
                if (width < self.min_image_size or height < self.min_image_size or
                    width > self.max_image_size or height > self.max_image_size):
                    continue
                
                # ÉTAPE 2: FILTRAGE INTELLIGENT 🧠
                if self.enable_smart_filtering:
                    is_valid, analysis = self._analyze_image_content(image_pil)
                    if not is_valid:
                        # Enregistrer comme image rejetée pour diagnostic
                        extracted_images.append({
                            'rejected': True,
                            'filter_reason': analysis['rejection_reason'],
                            'raw_size': image_pil.size,
                            'xref': xref
                        })
                        continue
                else:
                    analysis = {'summary': 'Filtrage intelligent désactivé'}
                
                # ÉTAPE 3: Score de qualité amélioré
                quality_score = self._calculate_enhanced_quality_score(image_pil, analysis)
                
                # ÉTAPE 4: Obtenir la bbox et générer variantes
                bbox = self._get_image_bbox_lite(page, xref)
                variants = self._create_image_variants_lite(image_pil)
                
                extracted_images.append({
                    'bbox': bbox,
                    'quality_score': quality_score,
                    'raw_b64': variants['raw'],
                    'trimmed_b64': variants['trimmed'], 
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

    def _analyze_image_content(self, image_pil):
        """
        🔍 ANALYSE INTELLIGENTE DU CONTENU D'IMAGE
        Détermine si c'est une vraie image produit ou un parasite.
        """
        try:
            # Convertir en RGB si nécessaire
            if image_pil.mode != 'RGB':
                image_rgb = image_pil.convert('RGB')
            else:
                image_rgb = image_pil
            
            # CRITÈRE 1: Variance des couleurs (évite images monochromes/texte)
            color_variance = self._calculate_color_variance(image_rgb)
            
            # CRITÈRE 2: Densité des contours (évite zones uniformes)
            edge_density = self._calculate_edge_density(image_rgb)
            
            # CRITÈRE 3: Détection de motifs "texte-like"
            text_ratio = self._detect_text_patterns(image_rgb)
            
            # CRITÈRE 4: Analyse de la distribution spatiale
            spatial_complexity = self._analyze_spatial_distribution(image_rgb)
            
            # DÉCISION COMPOSITE
            rejection_reasons = []
            
            if color_variance < self.min_color_variance:
                rejection_reasons.append(f"Trop monochrome (variance: {color_variance:.0f} < {self.min_color_variance})")
            
            if edge_density < self.min_edge_density:
                rejection_reasons.append(f"Trop uniforme (contours: {edge_density:.3f} < {self.min_edge_density})")
            
            if text_ratio > self.max_text_ratio:
                rejection_reasons.append(f"Ressemble à du texte (ratio: {text_ratio:.2f} > {self.max_text_ratio})")
            
            if spatial_complexity < 0.2:
                rejection_reasons.append(f"Complexité spatiale insuffisante ({spatial_complexity:.2f})")
            
            # IMAGE VALIDE si aucun critère de rejet
            is_valid = len(rejection_reasons) == 0
            
            analysis = {
                'color_variance': color_variance,
                'edge_density': edge_density, 
                'text_ratio': text_ratio,
                'spatial_complexity': spatial_complexity,
                'summary': f"V:{color_variance:.0f}, C:{edge_density:.2f}, T:{text_ratio:.2f}, S:{spatial_complexity:.2f}"
            }
            
            if not is_valid:
                analysis['rejection_reason'] = " | ".join(rejection_reasons)
            
            return is_valid, analysis
            
        except Exception as e:
            _logger.warning(f"⚠️ Erreur analyse contenu: {e}")
            # En cas d'erreur, accepter l'image par précaution
            return True, {'summary': f'Erreur analyse: {e}'}

    def _calculate_color_variance(self, image_rgb):
        """Calcule la variance des couleurs pour détecter images monochromes."""
        try:
            # Statistiques sur chaque canal RGB
            stats = ImageStat.Stat(image_rgb)
            
            # Variance combinée des 3 canaux
            variance = sum(stats.var)  # Variance R + G + B
            return variance
        except:
            return 1000  # Valeur par défaut si erreur

    def _calculate_edge_density(self, image_rgb):
        """Calcule la densité des contours pour détecter zones uniformes."""
        try:
            # Convertir en niveaux de gris
            gray = image_rgb.convert('L')
            
            # Appliquer un filtre de détection de contours
            edges = gray.filter(ImageFilter.FIND_EDGES)
            
            # Calculer le pourcentage de pixels "contour"
            edge_pixels = sum(1 for pixel in edges.getdata() if pixel > 50)
            total_pixels = edges.size[0] * edges.size[1]
            
            density = edge_pixels / total_pixels if total_pixels > 0 else 0
            return density
        except:
            return 0.5  # Valeur par défaut

    def _detect_text_patterns(self, image_rgb):
        """Détecte les motifs ressemblant à du texte."""
        try:
            # Convertir en niveaux de gris
            gray = image_rgb.convert('L')
            
            # Seuillage pour binariser
            threshold = 128
            binary = gray.point(lambda p: 255 if p > threshold else 0)
            
            # Analyser les runs horizontaux (caractéristique du texte)
            width, height = binary.size
            horizontal_runs = 0
            total_transitions = 0
            
            # Échantillonner quelques lignes
            sample_lines = range(10, height-10, max(1, height//20))
            
            for y in sample_lines:
                pixels = [binary.getpixel((x, y)) for x in range(width)]
                
                # Compter les transitions noir->blanc et blanc->noir
                transitions = sum(1 for i in range(1, len(pixels)) 
                                if pixels[i] != pixels[i-1])
                total_transitions += transitions
                
                # Les zones de texte ont beaucoup de transitions courtes
                if transitions > width * 0.1:  # Plus de 10% de transitions
                    horizontal_runs += 1
            
            # Ratio de lignes "texte-like"
            text_ratio = horizontal_runs / len(sample_lines) if sample_lines else 0
            return text_ratio
            
        except:
            return 0.3  # Valeur par défaut

    def _analyze_spatial_distribution(self, image_rgb):
        """Analyse la complexité de la distribution spatiale."""
        try:
            # Diviser l'image en grille 4x4
            width, height = image_rgb.size
            grid_w, grid_h = width // 4, height // 4
            
            cell_variances = []
            
            for i in range(4):
                for j in range(4):
                    left = i * grid_w
                    top = j * grid_h
                    right = min(left + grid_w, width)
                    bottom = min(top + grid_h, height)
                    
                    # Extraire la cellule
                    cell = image_rgb.crop((left, top, right, bottom))
                    
                    # Calculer variance de cette cellule
                    cell_stats = ImageStat.Stat(cell)
                    cell_variance = sum(cell_stats.var)
                    cell_variances.append(cell_variance)
            
            # Complexité = variance des variances (diversité spatiale)
            if len(cell_variances) > 1:
                mean_var = sum(cell_variances) / len(cell_variances)
                complexity = sum((v - mean_var) ** 2 for v in cell_variances) / len(cell_variances)
                return min(1.0, complexity / 10000)  # Normaliser
            else:
                return 0.5
                
        except:
            return 0.5  # Valeur par défaut

    def _calculate_enhanced_quality_score(self, image_pil, analysis):
        """Score de qualité amélioré basé sur l'analyse de contenu."""
        try:
            # Score de base (taille + ratio)
            width, height = image_pil.size
            area = width * height
            ratio = width / height if height > 0 else 1
            base_score = min(1.0, (area / 50000) * 0.4 + (1 - abs(ratio - 1) * 0.5) * 0.2)
            
            # Bonus pour richesse du contenu
            content_bonus = 0
            
            if 'color_variance' in analysis:
                # Bonus variance couleur (max +0.2)
                color_bonus = min(0.2, analysis['color_variance'] / 2500 * 0.2)
                content_bonus += color_bonus
            
            if 'edge_density' in analysis:
                # Bonus densité contours (max +0.2) 
                edge_bonus = min(0.2, analysis['edge_density'] * 0.2)
                content_bonus += edge_bonus
            
            # Score final
            final_score = min(1.0, base_score + content_bonus)
            return round(final_score, 3)
            
        except:
            return 0.5  # Score par défaut

    # Remplacer l'action par défaut par la version améliorée
    action_extract_images = action_extract_images_advanced
    action_extract_images_enhanced = action_extract_images_advanced  # Alias
    action_extract_images_lite = action_extract_images_advanced  # Alias
