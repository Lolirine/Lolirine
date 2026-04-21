# -*- coding: utf-8 -*-
"""
Extension de pool.catalog.pdf.product
=====================================

Ajoute :
- O2M vers les images extraites (pool.catalog.pdf.image)
- Champs calculés pour l'image principale et le compte des secondaires validées
- Helper `_attach_images_to_template(product_tmpl)` appelé lors de la création
  des product.template depuis un import
"""

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PoolCatalogPdfProductImages(models.Model):
    _inherit = 'pool.catalog.pdf.product'

    # --- O2M inverse des images ---
    image_ids = fields.One2many(
        'pool.catalog.pdf.image',
        'product_id',
        string='Images du catalogue',
    )

    # --- Agrégats d'affichage ---
    primary_image_id = fields.Many2one(
        'pool.catalog.pdf.image',
        string='Image principale',
        compute='_compute_image_aggregates',
        store=False,
    )
    primary_image_preview = fields.Binary(
        string='Aperçu principal',
        related='primary_image_id.image_data_thumb',
        readonly=True,
    )
    secondary_validated_count = fields.Integer(
        string='Secondaires validées',
        compute='_compute_image_aggregates',
    )
    secondary_proposed_count = fields.Integer(
        string='Secondaires proposées',
        compute='_compute_image_aggregates',
    )

    # =========================================================================
    # COMPUTES
    # =========================================================================

    @api.depends('image_ids', 'image_ids.role')
    def _compute_image_aggregates(self):
        for rec in self:
            primary = rec.image_ids.filtered(lambda i: i.role == 'primary')
            rec.primary_image_id = primary[:1]
            rec.secondary_validated_count = len(
                rec.image_ids.filtered(lambda i: i.role == 'secondary_validated')
            )
            rec.secondary_proposed_count = len(
                rec.image_ids.filtered(lambda i: i.role == 'secondary_proposed')
            )

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def action_view_images(self):
        """Ouvre la liste des images de ce produit catalogue."""
        self.ensure_one()
        return {
            'name': _("Images – %s") % (self.name or self.reference or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'pool.catalog.pdf.image',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
                'default_pdf_import_id': self.pdf_import_id.id if self.pdf_import_id else False,
            },
        }

    # =========================================================================
    # PUSH VERS product.template
    # =========================================================================

    def _attach_images_to_template(self, product_tmpl):
        """Attache les images extraites à un product.template Odoo.

        - L'image 'primary' → product_tmpl.image_1920
        - Les 'secondary_validated' → product.image (Extra Product Media)
        - Les 'secondary_proposed' sont IGNORÉES (doivent être validées manuellement)

        Retourne le nombre d'images attachées.
        """
        self.ensure_one()
        if not product_tmpl:
            return 0

        ProductImage = self.env['product.image']
        count = 0

        # 1. Image principale
        primary = self.image_ids.filtered(lambda i: i.role == 'primary' and i.image_data)
        if primary:
            main = primary[0]
            try:
                if not product_tmpl.image_1920:
                    product_tmpl.image_1920 = main.image_data
                else:
                    # Déjà une image → on ajoute en secondaire
                    ProductImage.create({
                        'product_tmpl_id': product_tmpl.id,
                        'name': _("Catalogue – %s") % (main.matched_reference or self.name or 'img'),
                        'image_1920': main.image_data,
                    })
                count += 1
                main.pushed_to_product = True
            except Exception as e:
                _logger.warning("Attach primary failed: %s", e)

        # 2. Secondaires validées uniquement
        secondaries = self.image_ids.filtered(
            lambda i: i.role == 'secondary_validated' and i.image_data
        )
        for img in secondaries:
            try:
                ProductImage.create({
                    'product_tmpl_id': product_tmpl.id,
                    'name': _("Catalogue %s – %s") % (
                        img.matched_reference or '',
                        img.display_name or 'secondaire',
                    ),
                    'image_1920': img.image_data,
                })
                img.pushed_to_product = True
                count += 1
            except Exception as e:
                _logger.warning("Attach secondary failed: %s", e)

        return count
