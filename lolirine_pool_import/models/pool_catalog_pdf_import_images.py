# -*- coding: utf-8 -*-
"""
Extension de pool.catalog.pdf.import
====================================

Ajoute l'extraction d'images au module lolirine_pool_import existant.

Noms de champs adaptes au schema existant :
  - source_pdf (fichier PDF encode base64)
  - product_ids (O2M vers pool.catalog.pdf.product)
  - page_num (numero de page sur le produit)
  - ref (reference du produit)
  - import_id (M2O retour depuis le produit)

Strategie de capture pure :
  - Rendu clippe a 300 DPI via page.get_pixmap(matrix, clip=rect, alpha=False)
  - Restitue exactement ce que l'oeil voit dans le PDF (pas d'aspect "scanner")
  - Evite les surprises CMJN -> RGB et masques alpha sombres
  - Aucun debordement possible (clip strictement borne au bbox de l'image)
  - Resolution constante (~4x les dimensions du bbox affiche) quel que soit
    l'encodage source SCP/Fluidra
Puis trim PIL sur bords uniformes (blanc/transparent) pour finir le detourage.

Matching au produit par proximite textuelle :
  - page.get_image_rects(xref) donne la position a l'ecran
  - page.get_text("blocks") donne les blocs texte avec leurs bboxes
  - Regex sur pattern de reference
  - Score de confiance base sur la distance euclidienne
  - Match uniquement contre les pool.catalog.pdf.product de la meme page
"""

import base64
import io
import logging
import math
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Pattern pour capturer des references (SCP: 1478, 64170 / Fluidra: 70342, AR0048, W0012A)
REF_PATTERN = re.compile(r'\b([A-Z]{2,4}-\d{3,4}-\d{3,4}|[A-Z]{1,4}\d{3,8}[A-Z]{0,3}|\d{4,8})\b')

# Tailles minimales pour exclure icones/logos/pictos
MIN_IMAGE_WIDTH_PT = 40
MIN_IMAGE_HEIGHT_PT = 40
MIN_IMAGE_AREA_PT = 3000


class PoolCatalogPdfImportImageExtract(models.Model):
    _inherit = 'pool.catalog.pdf.import'

    # --- O2M vers les images extraites ---
    image_ids = fields.One2many(
        'pool.catalog.pdf.image',
        'pdf_import_id',
        string='Images extraites',
    )
    image_count = fields.Integer(
        string='Nb images',
        compute='_compute_image_counts',
    )
    image_primary_count = fields.Integer(
        string='Images principales',
        compute='_compute_image_counts',
    )
    image_secondary_proposed_count = fields.Integer(
        string='Secondaires a valider',
        compute='_compute_image_counts',
    )
    image_unmatched_count = fields.Integer(
        string='Non matchees',
        compute='_compute_image_counts',
    )

    # --- Etat de l'extraction d'images ---
    image_extraction_state = fields.Selection(
        [
            ('draft', 'Non demarree'),
            ('in_progress', 'En cours'),
            ('done', 'Terminee'),
            ('error', 'Erreur'),
        ],
        string='Etat extraction images',
        default='draft',
        copy=False,
    )
    image_extraction_log = fields.Text(
        string="Journal d'extraction images",
        copy=False,
    )

    # =========================================================================
    # COMPUTES
    # =========================================================================

    @api.depends('image_ids', 'image_ids.role', 'image_ids.product_id')
    def _compute_image_counts(self):
        for rec in self:
            imgs = rec.image_ids
            rec.image_count = len(imgs)
            rec.image_primary_count = len(imgs.filtered(lambda i: i.role == 'primary'))
            rec.image_secondary_proposed_count = len(
                imgs.filtered(lambda i: i.role == 'secondary_proposed')
            )
            rec.image_unmatched_count = len(imgs.filtered(lambda i: not i.product_id))

    # =========================================================================
    # ACTIONS UI
    # =========================================================================

    def action_extract_images(self):
        """Lance l'extraction d'images depuis le PDF pour cet import."""
        self.ensure_one()

        if not self.source_pdf:
            raise UserError(_("Aucun fichier PDF n'est attache a cet import."))

        if self.image_extraction_state == 'in_progress':
            raise UserError(_("Une extraction est deja en cours."))

        # Effacer les anciennes images si on relance
        # Mode reprise : si des images existent deja et qu'on n'a pas force le reset,
        # on reprend la ou on s'est arrete (skip des pages deja traitees).
        # Pour forcer un reset complet, passer en context : with_context(force_reset=True)
        force_reset = self.env.context.get('force_reset', False)
        if force_reset and self.image_ids:
            _logger.info("Reset force : suppression de %d images", len(self.image_ids))
            self.image_ids.unlink()

        self.write({
            'image_extraction_state': 'in_progress',
            'image_extraction_log': (self.image_extraction_log or '') +
                _("\n[Reprise] Demarrage / reprise extraction..."),
        })
        self.env.cr.commit()

        try:
            self._extract_all_images_from_pdf()
            self._assign_image_roles()
            self.write({
                'image_extraction_state': 'done',
                'image_extraction_log': (self.image_extraction_log or '') +
                    _("\nOK Extraction terminee : %d images, %d matchees, %d principales.") % (
                        self.image_count,
                        self.image_count - self.image_unmatched_count,
                        self.image_primary_count,
                    ),
            })
        except Exception as e:
            _logger.exception("Erreur extraction images PDF")
            self.write({
                'image_extraction_state': 'error',
                'image_extraction_log': (self.image_extraction_log or '') +
                    _("\nKO Erreur : %s") % str(e),
            })
            raise UserError(_("Echec de l'extraction : %s") % str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Extraction terminee"),
                'message': _("%d images extraites, %d associees a un produit.") % (
                    self.image_count,
                    self.image_count - self.image_unmatched_count,
                ),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_extracted_images(self):
        """Ouvre la liste des images extraites pour cet import."""
        self.ensure_one()
        return {
            'name': _("Images - %s") % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'pool.catalog.pdf.image',
            'view_mode': 'list,form',
            'domain': [('pdf_import_id', '=', self.id)],
            'context': {
                'default_pdf_import_id': self.id,
                'search_default_group_by_product': 1,
            },
        }

    def action_reassign_roles(self):
        """Reassigne automatiquement les roles (primary/secondary) sans reextraire."""
        self.ensure_one()
        self._assign_image_roles()
        return True

    # =========================================================================
    # CORE : EXTRACTION
    # =========================================================================

    def _extract_all_images_from_pdf(self):
        """Extrait toutes les images du PDF en mode capture pure 300 DPI.

        Commit page par page pour resister aux timeouts workers HTTP/cron.
        En cas d'interruption, les images deja extraites sont preservees et
        l'etat reste 'in_progress' jusqu'a la fin reelle.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise UserError(_("PyMuPDF (fitz) n'est pas installe sur le serveur."))

        pdf_data = base64.b64decode(self.source_pdf)
        doc = fitz.open(stream=pdf_data, filetype="pdf")

        total_pages = len(doc)
        log_lines = [_("Traitement de %d pages...") % total_pages]
        self.image_extraction_log = "\n".join(log_lines)
        self.env.cr.commit()

        # Pre-charger les produits existants groupes par page
        products_by_page = {}
        for p in self.product_ids:
            if p.page_num:
                products_by_page.setdefault(p.page_num, []).append(p)

        Image = self.env['pool.catalog.pdf.image']
        total_created = 0

        for page_num in range(total_pages):
            page_vals = []
            try:
                page = doc[page_num]
                page_idx = page_num + 1

                text_refs = self._collect_text_references(page)
                page_products = products_by_page.get(page_idx, [])

                for img_info in page.get_images(full=True):
                    vals = self._extract_single_image(
                        doc, page, page_idx, img_info, text_refs, page_products
                    )
                    if vals:
                        page_vals.append(vals)

            except Exception as e:
                _logger.warning("Page %d : %s", page_idx, e)
                log_lines.append(_("Avertissement page %d : %s") % (page_idx, e))

            # Commit immediat des images de la page
            if page_vals:
                Image.create(page_vals)
                total_created += len(page_vals)

            # Log d'avancement toutes les 5 pages
            if page_idx % 5 == 0 or page_idx == total_pages:
                log_lines.append(
                    _("  Page %d/%d -> %d images cumulees")
                    % (page_idx, total_pages, total_created)
                )
                self.image_extraction_log = "\n".join(log_lines)
                self.env.cr.commit()

        doc.close()

        log_lines.append(_("-> %d images creees au total") % total_created)
        self.image_extraction_log = "\n".join(log_lines)
        self.env.cr.commit()
       
    def _collect_text_references(self, page):
        """Retourne [{'ref', 'bbox', 'center'}, ...] pour tous les refs trouves sur la page."""
        refs = []
        try:
            blocks = page.get_text("blocks")
        except Exception:
            return refs

        for block in blocks:
            if len(block) < 5:
                continue
            x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
            if not text:
                continue
            for match in REF_PATTERN.finditer(text):
                ref = match.group(1)
                # Filtrer les pseudo-refs parasites (annees, pages, etc.)
                if ref.isdigit() and (len(ref) < 4 or len(ref) > 8):
                    continue
                if ref in ('2024', '2025', '2026', '2027'):
                    continue
                refs.append({
                    'ref': ref,
                    'bbox': (x0, y0, x1, y1),
                    'center': ((x0 + x1) / 2, (y0 + y1) / 2),
                })
        return refs

    def _extract_single_image(self, doc, page, page_num, img_info, text_refs, page_products):
        """Extrait une image en mode capture pure (rendu clippe 300 DPI).

        Avantages vs extraction native :
        - Couleurs fideles a l'affichage ecran (pas d'aspect "scanner medical")
        - Pas de drame CMJN -> RGB ni masque alpha sombre
        - Bords stricts au bbox affiche (clip=rect) -> aucun debordement
        - Resolution constante (~4x les dimensions du bbox) quel que soit
          l'encodage source SCP/Fluidra
        """
        try:
            import fitz
            from PIL import Image, ImageChops  # noqa: F401  (utilise par _trim_image_borders)
        except ImportError:
            return None

        xref = img_info[0]

        # 1. Recuperer la position a l'ecran
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        if not rects:
            return None

        rect = rects[0]
        display_w = rect.width
        display_h = rect.height

        # Filtre taille minimale (exclut icones / logos / pictos)
        if display_w < MIN_IMAGE_WIDTH_PT or display_h < MIN_IMAGE_HEIGHT_PT:
            return None
        if display_w * display_h < MIN_IMAGE_AREA_PT:
            return None

        # 2. Capture pure : rendu clippe a 300 DPI
        try:
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
            image_bytes = pix.tobytes('png')
            final_w, final_h = pix.width, pix.height
        except Exception as e:
            _logger.warning(
                "Capture clippee echouee page=%d xref=%s : %s",
                page_num, xref, e,
            )
            return None

        # 3. Trim des bords uniformes avec PIL
        trimmed_bytes, trim_w, trim_h = self._trim_image_borders(image_bytes)

        # 4. Calcul du score de qualite
        quality = self._compute_quality_score(trim_w, trim_h, display_w, display_h)

        # 5. Matching avec les produits de la page
        img_center = ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
        matched_product, matched_ref, confidence = self._match_image_to_product(
            img_center, text_refs, page_products
        )

        return {
            'pdf_import_id': self.id,
            'product_id': matched_product.id if matched_product else False,
            'matched_reference': matched_ref,
            'page_number': page_num,
            'bbox_x': rect.x0,
            'bbox_y': rect.y0,
            'bbox_width': display_w,
            'bbox_height': display_h,
            'image_data': base64.b64encode(trimmed_bytes),
            'extraction_method': 'clipped',
            'width_px': trim_w or final_w,
            'height_px': trim_h or final_h,
            'quality_score': quality,
            'confidence_score': confidence,
            'role': 'unassigned',
        }

    def _trim_image_borders(self, image_bytes):
        """Trim les bordures uniformes (blanc/transparent) avec PIL.
        Retourne (bytes, width, height).
        """
        try:
            from PIL import Image, ImageChops
        except ImportError:
            return image_bytes, 0, 0

        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Convertir palette/CMYK en RGB pour le trim
            if img.mode in ('P', 'CMYK', 'L'):
                img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')

            # Strategie selon mode
            if img.mode == 'RGBA':
                # Trim via alpha si disponible
                bbox = img.getbbox()
            else:
                # Trim contre fond blanc
                rgb = img.convert('RGB')
                bg = Image.new('RGB', rgb.size, (255, 255, 255))
                diff = ImageChops.difference(rgb, bg)
                bbox = diff.getbbox()

            if bbox:
                # Padding de securite pour ne pas couper l'objet
                padding = 8
                left = max(0, bbox[0] - padding)
                top = max(0, bbox[1] - padding)
                right = min(img.size[0], bbox[2] + padding)
                bottom = min(img.size[1], bbox[3] + padding)
                img = img.crop((left, top, right, bottom))

            # Sauver en PNG optimise
            output = io.BytesIO()
            save_mode = 'RGBA' if img.mode == 'RGBA' else 'RGB'
            if img.mode != save_mode:
                img = img.convert(save_mode)
            img.save(output, format='PNG', optimize=True)
            return output.getvalue(), img.size[0], img.size[1]

        except Exception as e:
            _logger.warning("Trim borders failed : %s", e)
            return image_bytes, 0, 0

    def _compute_quality_score(self, w, h, display_w, display_h):
        """Score qualite 0-1 base sur taille, ratio, et rapport pixels/points."""
        if not w or not h:
            return 0.0

        score = 0.0

        # Taille absolue (bonus pour grosses images)
        area = w * h
        if area > 500 * 500:
            score += 0.35
        elif area > 300 * 300:
            score += 0.25
        elif area > 150 * 150:
            score += 0.15
        else:
            score += 0.05

        # Ratio d'aspect raisonnable
        ar = w / h if h else 1
        if 0.5 <= ar <= 2.0:
            score += 0.35
        elif 0.3 <= ar <= 3.0:
            score += 0.20
        else:
            score += 0.05

        # Densite pixels/points (haute resolution = bon)
        if display_w and display_h:
            px_per_pt = (w * h) / (display_w * display_h)
            if px_per_pt > 10:
                score += 0.30
            elif px_per_pt > 4:
                score += 0.20
            elif px_per_pt > 1:
                score += 0.10

        return min(1.0, score)

    def _match_image_to_product(self, img_center, text_refs, page_products):
        """Trouve le produit le plus proche par proximite textuelle.
        Retourne (product_record|None, reference|None, confidence 0-1).
        """
        if not text_refs or not page_products:
            return None, None, 0.0

        # Index des produits par reference (champ 'ref' sur pool.catalog.pdf.product)
        product_by_ref = {}
        for p in page_products:
            if p.ref:
                product_by_ref[p.ref.strip().upper()] = p

        if not product_by_ref:
            return None, None, 0.0

        best_match = None
        best_distance = float('inf')

        for text_ref in text_refs:
            ref_upper = text_ref['ref'].upper()
            if ref_upper not in product_by_ref:
                continue
            distance = math.sqrt(
                (text_ref['center'][0] - img_center[0]) ** 2 +
                (text_ref['center'][1] - img_center[1]) ** 2
            )
            if distance < best_distance:
                best_distance = distance
                best_match = {
                    'product': product_by_ref[ref_upper],
                    'ref': text_ref['ref'],
                    'distance': distance,
                }

        if not best_match:
            return None, None, 0.0

        # Confidence : 300pt = distance moyenne acceptable sur une page A4
        confidence = max(0.0, min(1.0, 1.0 - (best_distance / 300.0)))
        return best_match['product'], best_match['ref'], confidence

    # =========================================================================
    # CORE : ASSIGNATION DES ROLES
    # =========================================================================

    def _assign_image_roles(self):
        """Pour chaque produit, la meilleure image = primary, les autres = secondary_proposed."""
        self.ensure_one()
        Image = self.env['pool.catalog.pdf.image']

        # Reset des roles sur toutes les images matchees
        matched_images = self.image_ids.filtered('product_id')
        matched_images.write({'role': 'unassigned', 'validated': False})

        # Regrouper par produit
        by_product = {}
        for img in matched_images:
            by_product.setdefault(img.product_id.id, Image)
            by_product[img.product_id.id] |= img

        # Pour chaque produit : trier par score combine, assigner les roles
        for product_id, imgs in by_product.items():
            sorted_imgs = imgs.sorted(key=lambda i: i.combined_score, reverse=True)
            # Meilleure image = principale (auto-validee)
            sorted_imgs[0].write({'role': 'primary', 'validated': True})
            # Autres = secondaires proposees (a valider manuellement)
            if len(sorted_imgs) > 1:
                sorted_imgs[1:].write({'role': 'secondary_proposed', 'validated': False})
