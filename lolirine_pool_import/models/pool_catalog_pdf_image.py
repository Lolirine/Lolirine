# -*- coding: utf-8 -*-
"""
Pool Catalog PDF Image
======================

Stocke les images extraites d'un catalogue PDF (SCP, Fluidra, etc.) avec :
- double stratégie d'extraction (native embarquée / rendu clippé 300 DPI)
- trim automatique des bordures uniformes
- score de qualité et score de confiance du matching au produit
- rôle : principale / secondaire proposée / secondaire validée / rejetée

Association directe avec pool.catalog.pdf.product via M2O.
"""

import base64
import io
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PoolCatalogPdfImage(models.Model):
    _name = 'pool.catalog.pdf.image'
    _description = "Image extraite d'un catalogue PDF"
    _order = 'page_number, sequence, id'
    _rec_name = 'display_name'

    # --- Liens ---
    pdf_import_id = fields.Many2one(
        'pool.catalog.pdf.import',
        string='Import PDF',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        'pool.catalog.pdf.product',
        string='Produit catalogue',
        ondelete='set null',
        index=True,
        help="Produit extrait auquel cette image est associée (par proximité textuelle).",
    )
    matched_reference = fields.Char(
        string='Référence matchée',
        help="Référence SCP/Fluidra trouvée à proximité de l'image dans le PDF.",
    )

    # --- Position dans le PDF ---
    page_number = fields.Integer(string='Page', required=True, index=True)
    sequence = fields.Integer(string='Ordre', default=10)
    bbox_x = fields.Float(string='BBox X')
    bbox_y = fields.Float(string='BBox Y')
    bbox_width = fields.Float(string='BBox largeur')
    bbox_height = fields.Float(string='BBox hauteur')

    # --- Données image ---
    image_data = fields.Binary(
        string='Image',
        attachment=True,
        help="Image finale après trim et optimisation.",
    )
    image_data_thumb = fields.Binary(
        string='Miniature',
        compute='_compute_image_thumb',
        store=True,
        attachment=True,
    )
    extraction_method = fields.Selection(
        [
            ('native', 'Native embarquée'),
            ('clipped', 'Rendu clippé 300 DPI'),
        ],
        string='Méthode',
        help="Native = extract_image(xref), Clippé = get_pixmap(clip=bbox).",
    )
    width_px = fields.Integer(string='Largeur (px)')
    height_px = fields.Integer(string='Hauteur (px)')
    file_size_kb = fields.Float(
        string='Taille (KB)',
        compute='_compute_file_size',
        store=True,
    )

    # --- Scores ---
    quality_score = fields.Float(
        string='Score qualité',
        digits=(3, 2),
        help="0-1. Combine surface, ratio, résolution native.",
    )
    confidence_score = fields.Float(
        string='Score confiance',
        digits=(3, 2),
        help="0-1. Basé sur la proximité de la référence produit dans le texte.",
    )
    combined_score = fields.Float(
        string='Score combiné',
        compute='_compute_combined_score',
        store=True,
        digits=(3, 2),
    )

    # --- Rôle & validation ---
    role = fields.Selection(
        [
            ('unassigned', 'Non assignée'),
            ('primary', '🥇 Principale'),
            ('secondary_proposed', '🔵 Secondaire proposée'),
            ('secondary_validated', '✅ Secondaire validée'),
            ('rejected', '❌ Rejetée'),
        ],
        string='Rôle',
        default='unassigned',
        required=True,
        index=True,
    )
    validated = fields.Boolean(
        string='Validée',
        help="Coché quand l'utilisateur a vérifié que l'association image/produit est correcte.",
    )
    note = fields.Text(string='Note')

    # --- État du push vers production ---
    pushed_to_product = fields.Boolean(
        string='Poussée vers le produit final',
        help="True quand cette image a été attachée au product.template d'Odoo lors de la création.",
    )

    # --- Affichage ---
    display_name = fields.Char(
        string='Nom',
        compute='_compute_display_name',
        store=True,
    )

    # =========================================================================
    # COMPUTES
    # =========================================================================

    @api.depends('page_number', 'matched_reference', 'product_id.name')
    def _compute_display_name(self):
        for rec in self:
            parts = [f"p.{rec.page_number}"]
            if rec.matched_reference:
                parts.append(rec.matched_reference)
            elif rec.product_id and rec.product_id.name:
                parts.append(rec.product_id.name[:40])
            else:
                parts.append("(non matchée)")
            rec.display_name = " – ".join(parts)

    @api.depends('quality_score', 'confidence_score')
    def _compute_combined_score(self):
        for rec in self:
            rec.combined_score = (rec.quality_score or 0.0) * (rec.confidence_score or 0.0)

    @api.depends('image_data')
    def _compute_file_size(self):
        for rec in self:
            if rec.image_data:
                try:
                    raw = base64.b64decode(rec.image_data)
                    rec.file_size_kb = len(raw) / 1024.0
                except Exception:
                    rec.file_size_kb = 0.0
            else:
                rec.file_size_kb = 0.0

    @api.depends('image_data')
    def _compute_image_thumb(self):
        """Génère une miniature 256x256 pour l'affichage list/kanban."""
        try:
            from PIL import Image
        except ImportError:
            for rec in self:
                rec.image_data_thumb = rec.image_data
            return

        for rec in self:
            if not rec.image_data:
                rec.image_data_thumb = False
                continue
            try:
                raw = base64.b64decode(rec.image_data)
                img = Image.open(io.BytesIO(raw))
                img.thumbnail((256, 256), Image.LANCZOS)
                buf = io.BytesIO()
                save_format = 'PNG' if img.mode in ('RGBA', 'LA') else 'JPEG'
                img.save(buf, format=save_format, optimize=True, quality=85)
                rec.image_data_thumb = base64.b64encode(buf.getvalue())
            except Exception as e:
                _logger.warning("Thumbnail failed for image %s: %s", rec.id, e)
                rec.image_data_thumb = rec.image_data

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def action_set_primary(self):
        """Marquer comme image principale (rétrograde l'ancienne principale du même produit)."""
        for rec in self:
            if not rec.product_id:
                continue
            current_primary = self.search([
                ('product_id', '=', rec.product_id.id),
                ('role', '=', 'primary'),
                ('id', '!=', rec.id),
            ])
            current_primary.write({'role': 'secondary_proposed'})
            rec.write({'role': 'primary', 'validated': True})
        return True

    def action_validate_secondary(self):
        self.write({'role': 'secondary_validated', 'validated': True})
        return True

    def action_reject(self):
        self.write({'role': 'rejected'})
        return True

    def action_reset(self):
        self.write({'role': 'unassigned', 'validated': False})
        return True
