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
Puis trim PIL sur bords uniformes (blanc/transparent) pour finir le detourage.

Matching au produit par proximite textuelle :
  - page.get_image_rects(xref) donne la position a l'ecran
  - page.get_text("blocks") donne les blocs texte avec leurs bboxes
  - Regex sur pattern de reference
  - Score de confiance base sur la distance euclidienne
  - Match uniquement contre les pool.catalog.pdf.product de la meme page

Robustesse :
  - Commit page par page (resiste aux timeouts workers HTTP/cron)
  - Mode reprise : si interrompu, skip les pages deja extraites au relance
  - Pour forcer un reset complet : .with_context(force_reset=True).action_extract_images()

Push vers Odoo :
  - action_push_to_products propage les images validees vers les product.template
  - L'image 'primary' devient image_1920 du produit Odoo
  - Les images 'secondary_validated' deviennent product.image extra
  - Idempotent (flag pushed_to_product)
"""

import base64
import gc
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
MIN_IMAGE_WIDTH_PT = 80
MIN_IMAGE_HEIGHT_PT = 80
MIN_IMAGE_AREA_PT = 8000

# DPI de rendu (300 = qualite optimale, 200 = compromis RAM)
RENDER_DPI = 300

# Largeur minimale (px) pour push vers product.template
MIN_PUSH_WIDTH_PX = 300


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
    # HELPERS
    # =========================================================================

    def _open_source_pdf(self):
        """Ouvre le PDF source via PyMuPDF, en preferant la lecture directe
        depuis le filestore (mmap, faible RAM) au lieu du base64 en memoire.

        Crucial pour les gros PDFs (>100 MB) qui sinon explosent la RAM.

        Retourne un objet fitz.Document ouvert. A fermer apres usage.
        """
        import fitz
        import os

        # Chercher l'attachment du source_pdf
        att = self.env['ir.attachment'].search([
            ('res_model', '=', 'pool.catalog.pdf.import'),
            ('res_field', '=', 'source_pdf'),
            ('res_id', '=', self.id),
        ], limit=1)

        # Si on a un fichier sur le filestore, ouverture directe (mmap)
        if att and att.type == 'binary' and att.store_fname:
            filestore = self.env['ir.attachment']._filestore()
            pdf_path = os.path.join(filestore, att.store_fname)
            if os.path.exists(pdf_path):
                _logger.info(
                    "Ouverture PDF en mode fichier (filestore) : %s (%.1f MB)",
                    pdf_path, att.file_size / 1024 / 1024,
                )
                return fitz.open(pdf_path)

        # Fallback : base64 en memoire (pour les petits PDFs en db_datas)
        if not self.source_pdf:
            raise UserError(_("Aucun PDF source disponible."))
        _logger.info("Ouverture PDF en mode stream (base64 en RAM)")
        pdf_data = base64.b64decode(self.source_pdf)
        return fitz.open(stream=pdf_data, filetype="pdf")
  
    # =========================================================================
    # ACTIONS UI
    # =========================================================================

    def action_extract_images(self):
        """Lance l'extraction d'images depuis le PDF pour cet import.

        Comportement par defaut : MODE REPRISE
          - Conserve les images deja extraites
          - Skip les pages deja traitees
          - Reprend la ou ca s'etait arrete

        Pour forcer un reset complet (effacer toutes les images existantes
        et tout reextraire depuis zero) :
          imp.with_context(force_reset=True).action_extract_images()
        """
        self.ensure_one()

        if not self.source_pdf:
            raise UserError(_("Aucun fichier PDF n'est attache a cet import."))

        if self.image_extraction_state == 'in_progress':
            raise UserError(_("Une extraction est deja en cours."))

        # Mode reset force : on efface tout avant de relancer
        force_reset = self.env.context.get('force_reset', False)
        if force_reset and self.image_ids:
            _logger.info("Reset force : suppression de %d images", len(self.image_ids))
            self.image_ids.unlink()

        self.write({
            'image_extraction_state': 'in_progress',
            'image_extraction_log': (self.image_extraction_log or '') +
                _("\n[Run] Demarrage / reprise extraction..."),
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
        """Extrait toutes les images du PDF en mode capture pure.

        - Commit page par page (resiste aux timeouts)
        - Liberation memoire active (gc + invalidate_all)
        - Mode reprise automatique : skip les pages deja traitees
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise UserError(_("PyMuPDF (fitz) n'est pas installe sur le serveur."))

        doc = self._open_source_pdf()

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

        # Mode reprise : recuperer la liste des pages deja traitees
        already_done_pages = set(
            Image.search([
                ('pdf_import_id', '=', self.id),
            ]).mapped('page_number')
        )
        if already_done_pages:
            log_lines.append(
                _("Reprise : %d pages deja traitees seront sautees.")
                % len(already_done_pages)
            )
            self.image_extraction_log = "\n".join(log_lines)
            self.env.cr.commit()

        for page_num in range(total_pages):
            page_vals = []
            page_idx = page_num + 1

            # Skip si page deja traitee (mode reprise)
            if page_idx in already_done_pages:
                continue

            try:
                page = doc[page_num]

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
                page_vals.clear()

            # Liberation memoire active apres chaque page
            self.env.cr.commit()
            self.env.invalidate_all()
            gc.collect()

            # Log d'avancement toutes les 5 pages
            if page_idx % 5 == 0 or page_idx == total_pages:
                log_lines.append(
                    _("  Page %d/%d -> %d images cumulees (cette session)")
                    % (page_idx, total_pages, total_created)
                )
                self.image_extraction_log = "\n".join(log_lines)
                self.env.cr.commit()

        doc.close()
        del doc
        gc.collect()

        log_lines.append(_("-> %d images creees au total cette session") % total_created)
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
        """Extrait une image en mode capture pure (rendu clippe RENDER_DPI).

        Avantages vs extraction native :
        - Couleurs fideles a l'affichage ecran (pas d'aspect "scanner medical")
        - Pas de drame CMJN -> RGB ni masque alpha sombre
        - Bords stricts au bbox affiche (clip=rect) -> aucun debordement
        - Resolution constante quel que soit l'encodage source SCP/Fluidra
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

        # 2. Capture pure : rendu clippe a RENDER_DPI
        try:
            scale = RENDER_DPI / 72
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
            image_bytes = pix.tobytes('png')
            final_w, final_h = pix.width, pix.height
            del pix
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

    def action_rematch_images(self):
        """Re-tente le matching produit pour toutes les images existantes,
        sans re-extraire. Utile quand le matching initial a echoue a cause
        d'un decalage de pages entre produits et images.

        Strategie : pour chaque image, lire le texte du PDF autour de sa
        position, detecter les refs, et matcher contre TOUS les produits
        de l'import (pas seulement ceux de la meme page).
        """
        self.ensure_one()

        if not self.source_pdf:
            raise UserError(_("Aucun PDF attache."))
        if not self.image_ids:
            raise UserError(_("Aucune image a rematcher."))

        try:
            import fitz
        except ImportError:
            raise UserError(_("PyMuPDF non installe."))

        # Index global : toutes les refs produits de l'import
        product_by_ref = {}
        for p in self.product_ids:
            if p.ref:
                product_by_ref[p.ref.strip().upper()] = p
        if not product_by_ref:
            raise UserError(_("Aucun produit avec reference dans cet import."))

        _logger.info("Rematch %s : %d images, %d produits indexes",
                     self.name, len(self.image_ids), len(product_by_ref))

        pdf_data = base64.b64decode(self.source_pdf)
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        total_pages = len(doc)

        # Pre-collecter les refs par page (texte complet)
        refs_by_page = {}
        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_num = page_idx + 1
            text_refs = self._collect_text_references(page)
            refs_by_page[page_num] = text_refs

        # Rematcher chaque image
        updated = 0
        cleared = 0
        for img in self.image_ids:
            page_refs = refs_by_page.get(img.page_number, [])
            img_center = (img.bbox_x + img.bbox_width / 2,
                          img.bbox_y + img.bbox_height / 2)

            # Chercher la ref la plus proche qui existe dans le catalogue
            best = None
            best_dist = float('inf')
            for tr in page_refs:
                ref_upper = tr['ref'].upper()
                if ref_upper not in product_by_ref:
                    continue
                d = math.sqrt(
                    (tr['center'][0] - img_center[0]) ** 2 +
                    (tr['center'][1] - img_center[1]) ** 2
                )
                if d < best_dist:
                    best_dist = d
                    best = {
                        'product': product_by_ref[ref_upper],
                        'ref': tr['ref'],
                        'distance': d,
                    }

            if best:
                confidence = max(0.0, min(1.0, 1.0 - (best['distance'] / 300.0)))
                if (img.product_id.id != best['product'].id
                        or img.matched_reference != best['ref']):
                    img.write({
                        'product_id': best['product'].id,
                        'matched_reference': best['ref'],
                        'confidence_score': confidence,
                    })
                    updated += 1
            else:
                # Aucune ref valide trouvee : on nettoie l'ancien match s'il y en avait
                if img.product_id:
                    img.write({
                        'product_id': False,
                        'matched_reference': False,
                        'confidence_score': 0.0,
                        'role': 'unassigned',
                    })
                    cleared += 1

        doc.close()

        # Reassigner les roles
        self._assign_image_roles()

        msg = _("Rematch termine : %d images mises a jour, %d nettoyees.") % (updated, cleared)
        self.image_extraction_log = (self.image_extraction_log or '') + "\n" + msg
        _logger.info(msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Rematch termine"),
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }

    # =========================================================================
    # PUSH VERS PRODUCT.TEMPLATE
    # =========================================================================

    def action_push_to_products(self):
        """Pousse les images validees vers les product.template Odoo lies.

        Pour chaque pool.catalog.pdf.product avec un product_id (product.template) :
          - L'image 'primary' devient image_1920 du produit Odoo
          - Les images 'secondary_validated' deviennent product.image extra

        Filtres appliques :
          - role IN ('primary', 'secondary_validated')
          - pushed_to_product == False (idempotence)
          - product_id.product_id != False (pool.product lie a un product.template)
          - width_px >= MIN_PUSH_WIDTH_PX (qualite suffisante)
          - image_data != False

        Skip silencieux pour les images en 'unassigned', 'rejected', 'secondary_proposed'.
        """
        self.ensure_one()

        # Images candidates
        candidates = self.image_ids.filtered(
            lambda i: (
                i.role in ('primary', 'secondary_validated')
                and not i.pushed_to_product
                and i.product_id
                and i.product_id.product_id  # le pool.product est lie a un product.template
                and i.width_px >= MIN_PUSH_WIDTH_PX
                and i.image_data
            )
        )

        if not candidates:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Rien a pousser"),
                    'message': _("Aucune image eligible "
                                 "(role primary/secondary_validated, non deja poussee, "
                                 "produit Odoo lie, taille >= %d px).") % MIN_PUSH_WIDTH_PX,
                    'type': 'warning',
                    'sticky': False,
                },
            }

        _logger.info(
            "Push %s : %d images candidates", self.name, len(candidates)
        )

        ProductImage = self.env['product.image']
        nb_primary_pushed = 0
        nb_secondary_pushed = 0
        nb_skipped_no_template = 0
        touched_templates = set()
        log_lines = []

        for img in candidates:
            pool_product = img.product_id
            template = pool_product.product_id

            if not template:
                nb_skipped_no_template += 1
                continue

            try:
                if img.role == 'primary':
                    # Ecrase l'image principale du product.template
                    template.write({'image_1920': img.image_data})
                    nb_primary_pushed += 1
                    log_lines.append(
                        _("  Primary -> %s (ref %s)")
                        % (template.display_name[:40], pool_product.ref or '?')
                    )
                else:
                    # role == 'secondary_validated' -> product.image extra
                    ProductImage.create({
                        'name': pool_product.ref or template.name,
                        'product_tmpl_id': template.id,
                        'image_1920': img.image_data,
                    })
                    nb_secondary_pushed += 1

                img.write({'pushed_to_product': True})
                touched_templates.add(template.id)

            except Exception as e:
                _logger.warning(
                    "Push echoue image=%s template=%s : %s",
                    img.id, template.id, e
                )
                log_lines.append(
                    _("  ECHEC image %d : %s") % (img.id, e)
                )

        # Commit final
        self.env.cr.commit()

        msg = _(
            "Push termine : %d principales, %d secondaires, "
            "%d produits Odoo mis a jour. "
            "%d images sans product.template lie (skippees)."
        ) % (nb_primary_pushed, nb_secondary_pushed,
             len(touched_templates), nb_skipped_no_template)

        full_log = msg
        if log_lines:
            full_log += "\n" + "\n".join(log_lines[:50])
            if len(log_lines) > 50:
                full_log += _("\n... (%d lignes supplementaires omises)") % (len(log_lines) - 50)

        self.image_extraction_log = (self.image_extraction_log or '') + "\n\n" + full_log
        _logger.info(msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Push termine"),
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }

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
