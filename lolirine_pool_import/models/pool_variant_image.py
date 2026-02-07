# -*- coding: utf-8 -*-
"""
Pool Variant Images – Visuels dynamiques par variante
=====================================================

Permet de changer l'image produit sur le site e-commerce quand le client
sélectionne une valeur d'attribut (meuble spa, couleur cuve, diamètre PVC, …).

Architecture Odoo :
  product.template.attribute.value (PTAV) = croisement template × attribut × valeur
  → On y ajoute un champ `variant_image` (Binary/Image)
  → Le JS frontend écoute le changement de sélection et swap l'image

Ce fichier contient :
  1. Extension PTAV avec image
  2. Extension product.template pour gestion batch
  3. Extension product.image pour le lien variante
  4. Intégration avec pool.catalog.extraction
  5. Wizard de traitement en masse
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import json
import base64
import re

_logger = logging.getLogger(__name__)


# =====================================================================
# 1. IMAGE SUR CHAQUE VALEUR D'ATTRIBUT (PTAV)
# =====================================================================

class ProductTemplateAttributeValueImage(models.Model):
    """
    Ajoute une image à chaque PTAV.
    Quand le client clique sur "BUTTERFLY" dans le configurateur,
    l'image associée à ce PTAV s'affiche.
    """
    _inherit = 'product.template.attribute.value'

    variant_image = fields.Image(
        string='Image variante',
        max_width=1920, max_height=1920,
        help="Image affichée quand cette valeur est sélectionnée sur le site"
    )
    variant_image_128 = fields.Image(
        string='Image variante (miniature)',
        related='variant_image',
        max_width=128, max_height=128,
        store=True,
    )
    variant_image_url = fields.Char(
        string='URL image externe',
        help="URL externe d'une image pour cette variante (alternative au binaire)"
    )


# =====================================================================
# 2. EXTENSION PRODUCT.TEMPLATE – GESTION BATCH
# =====================================================================

class ProductTemplateVariantImages(models.Model):
    _inherit = 'product.template'

    variant_images_configured = fields.Boolean(
        string='Images variantes configurées',
        default=False,
        copy=False,
    )

    # ─── Actions depuis le formulaire produit ───────────────────────

    def action_auto_assign_variant_images(self):
        """Bouton : assigne automatiquement les images aux PTAV de ce produit."""
        results = []
        for tmpl in self:
            r = tmpl._auto_assign_variant_images()
            results.append(r)
        if len(self) == 1:
            r = results[0]
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Images variantes'),
                    'message': r.get('message', 'Terminé'),
                    'type': 'success' if r.get('count') else 'warning',
                    'sticky': False,
                }
            }

    def action_distribute_images_round_robin(self):
        """Distribue séquentiellement les product.image non-assignées aux variantes."""
        self.ensure_one()
        variants = self.product_variant_ids.sorted('id')
        if len(variants) <= 1:
            raise UserError(_("Ce produit n'a qu'une seule variante."))

        ProductImage = self.env['product.image']
        unassigned = ProductImage.search([
            ('product_tmpl_id', '=', self.id),
            ('product_variant_id', '=', False),
        ], order='sequence, id')

        if not unassigned:
            raise UserError(_("Aucune image supplémentaire à distribuer."))

        assigned = 0
        vlist = list(variants)
        for idx, img in enumerate(unassigned):
            target = vlist[idx % len(vlist)]
            img.product_variant_id = target.id
            if not target.image_variant_1920:
                target.image_variant_1920 = img.image_1920
            assigned += 1

        # Copier aussi vers les PTAV pour le switcher frontend
        self._sync_variant_images_to_ptav()
        self.variant_images_configured = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Distribution terminée'),
                'message': _("%d image(s) répartie(s) sur %d variantes") % (assigned, len(vlist)),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_variant_images(self):
        """Supprime toutes les assignations variante (images redeviennent globales)."""
        self.ensure_one()
        ProductImage = self.env['product.image']
        imgs = ProductImage.search([
            ('product_tmpl_id', '=', self.id),
            ('product_variant_id', '!=', False),
        ])
        imgs.write({'product_variant_id': False})

        for v in self.product_variant_ids:
            v.image_variant_1920 = False

        # Vider les PTAV
        for ptav in self.attribute_line_ids.product_template_value_ids:
            if ptav.variant_image:
                ptav.variant_image = False

        self.variant_images_configured = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reset effectué'),
                'message': _("%d assignation(s) supprimée(s)") % len(imgs),
                'type': 'info',
                'sticky': False,
            }
        }

    # ─── Logique d'auto-assignation ────────────────────────────────

    def _auto_assign_variant_images(self):
        """
        Assigne automatiquement les images aux PTAV en utilisant :
          1. Les product.image dont le nom matche une valeur d'attribut
          2. Les images d'extraction catalogue (pool.catalog.extraction)
          3. Les images variantes des product.product (image_variant_1920)
        """
        self.ensure_one()
        ptav_lines = self.attribute_line_ids.product_template_value_ids
        if not ptav_lines:
            return {'count': 0, 'message': _("Pas d'attributs sur ce produit.")}

        count = 0
        ProductImage = self.env['product.image']

        # Collecter toutes les images disponibles
        all_images = ProductImage.search([
            ('product_tmpl_id', '=', self.id),
        ])

        # ── Stratégie 1 : nom de l'image contient le nom de la valeur ──
        for ptav in ptav_lines:
            if ptav.variant_image:
                continue  # déjà configurée
            val_name = ptav.product_attribute_value_id.name.lower()
            val_words = [w for w in val_name.split() if len(w) >= 3]

            best_img = None
            best_score = 0

            for pimg in all_images:
                img_name = (pimg.name or '').lower()
                score = 0
                if val_name in img_name:
                    score += 20
                for w in val_words:
                    if w in img_name:
                        score += 5
                if score > best_score:
                    best_score = score
                    best_img = pimg
            if best_img and best_score >= 5:
                ptav.variant_image = best_img.image_1920
                count += 1
                _logger.info("  📌 PTAV '%s' ← image '%s' (score %d)",
                             ptav.product_attribute_value_id.name, best_img.name, best_score)

        # ── Stratégie 2 : images d'extraction catalogue ──
        count += self._assign_ptav_from_catalog_extraction(ptav_lines)

        # ── Stratégie 3 : image_variant_1920 des product.product ──
        for variant in self.product_variant_ids:
            if not variant.image_variant_1920:
                continue
            for ptav in variant.product_template_attribute_value_ids:
                if not ptav.variant_image:
                    ptav.variant_image = variant.image_variant_1920
                    count += 1
                    _logger.info("  📌 PTAV '%s' ← image variante %s",
                                 ptav.product_attribute_value_id.name, variant.display_name)

        if count:
            self.variant_images_configured = True

        msg = _("%d image(s) assignée(s) sur %d valeurs d'attribut") % (count, len(ptav_lines))
        _logger.info("✅ %s – %s", self.name, msg)
        return {'count': count, 'message': msg}

    def _assign_ptav_from_catalog_extraction(self, ptav_lines):
        """Cherche dans pool.catalog.extraction les images à associer aux PTAV."""
        count = 0
        if 'pool.catalog.extraction.product' not in self.env:
            return count

        ExtProduct = self.env['pool.catalog.extraction.product']
        ext_prods = ExtProduct.search([
            ('product_id', '=', self.id),
            ('state', '=', 'imported'),
        ])
        if not ext_prods:
            return count

        for ext_p in ext_prods:
            extraction = ext_p.extraction_id
            if not extraction:
                continue

            # Images du catalogue
            cat_images = extraction.catalog_image_ids if hasattr(extraction, 'catalog_image_ids') else []
            # Image du produit extrait
            images_with_meta = []
            if ext_p.product_image:
                images_with_meta.append({
                    'image': ext_p.product_image,
                    'ref': ext_p.reference or '',
                    'desc': ext_p.name or '',
                    'capacity': ext_p.capacity or '',
                    'variant_name': ext_p.variant_name or '',
                })
            for ci in cat_images:
                if ci.image:
                    images_with_meta.append({
                        'image': ci.image,
                        'ref': ci.reference or '',
                        'desc': ci.description or '',
                        'capacity': '',
                        'variant_name': '',
                    })

            # Essayer de matcher chaque image à un PTAV
            for img_data in images_with_meta:
                search_text = ' '.join([
                    img_data['ref'], img_data['desc'],
                    img_data['capacity'], img_data['variant_name'],
                ]).lower()

                for ptav in ptav_lines:
                    if ptav.variant_image:
                        continue
                    val_name = ptav.product_attribute_value_id.name.lower()
                    if val_name in search_text or any(
                        w in search_text for w in val_name.split() if len(w) >= 3
                    ):
                        ptav.variant_image = img_data['image']
                        count += 1
                        _logger.info("  📌 PTAV '%s' ← extraction '%s'",
                                     ptav.product_attribute_value_id.name, img_data['desc'][:50])
                        break
        return count

    def _sync_variant_images_to_ptav(self):
        """
        Synchronise : si product.product a une image_variant_1920
        mais que ses PTAV n'ont pas de variant_image, on copie.
        """
        self.ensure_one()
        for variant in self.product_variant_ids:
            if not variant.image_variant_1920:
                continue
            for ptav in variant.product_template_attribute_value_ids:
                if not ptav.variant_image:
                    ptav.variant_image = variant.image_variant_1920

    # ─── Méthode batch (tous les produits) ─────────────────────────

    @api.model
    def cron_assign_all_variant_images(self):
        """
        CRON / action planifiée : traite TOUS les produits avec variantes.
        À lancer une fois pour rétro-appliquer, puis périodiquement si besoin.
        """
        templates = self.search([
            ('product_variant_count', '>', 1),
        ])
        return self._batch_assign_variant_images(templates)

    @api.model
    def _batch_assign_variant_images(self, templates=None):
        """
        Traite un recordset de templates. Retourne un résumé.
        """
        if templates is None:
            templates = self.search([('product_variant_count', '>', 1)])

        total = 0
        processed = 0
        errors = []

        _logger.info("🖼️ Batch images variantes : %d templates", len(templates))

        for tmpl in templates:
            try:
                r = tmpl._auto_assign_variant_images()
                total += r.get('count', 0)
                processed += 1
            except Exception as e:
                errors.append(f"{tmpl.name}: {e}")
                _logger.error("Erreur variant images %s: %s", tmpl.name, e)

        _logger.info("✅ Batch terminé : %d produits, %d images, %d erreurs",
                      processed, total, len(errors))
        return {
            'processed': processed,
            'assigned': total,
            'errors': errors[:20],
        }


# =====================================================================
# 3. EXTENSION PRODUCT.IMAGE – helper product_variant_id
# =====================================================================

class ProductImageVariantHelper(models.Model):
    """
    Petite extension pour faciliter la copie product.image → PTAV.
    """
    _inherit = 'product.image'

    def action_copy_to_ptav(self):
        """Copie cette image vers la PTAV correspondante (si variant assignée)."""
        for img in self:
            if not img.product_variant_id:
                continue
            variant = img.product_variant_id
            for ptav in variant.product_template_attribute_value_ids:
                if not ptav.variant_image:
                    ptav.variant_image = img.image_1920
                    _logger.info("Copié image '%s' → PTAV '%s'",
                                 img.name, ptav.product_attribute_value_id.name)


# =====================================================================
# 4. INTÉGRATION EXTRACTION CATALOGUE
# =====================================================================

class PoolCatalogExtractionVariantImageInteg(models.Model):
    """
    Override des méthodes d'import pour assigner les images aux variantes
    au moment de l'import OCR.
    """
    _inherit = 'pool.catalog.extraction'

    def _assign_variant_images_post_import(self, template, products_to_import):
        """
        Appelé APRÈS la création du template avec variantes.
        Assigne les images aux PTAV du template.

        Args:
            template: product.template fraîchement créé
            products_to_import: pool.catalog.extraction.product records
        Returns:
            int : nombre d'images assignées
        """
        self.ensure_one()
        if not template or len(template.product_variant_ids) <= 1:
            return 0

        count = 0
        ptav_all = template.attribute_line_ids.product_template_value_ids

        _logger.info("🖼️ Post-import variant images : %s (%d PTAV)",
                      template.name, len(ptav_all))

        # ── A. Images des produits extraits → PTAV ──
        for ext_p in products_to_import:
            if not ext_p.product_image:
                continue

            matched_ptav = self._match_ptav(
                ptav_all, ext_p.reference, ext_p.type_code,
                ext_p.capacity, ext_p.variant_name, ext_p.name,
            )
            if matched_ptav and not matched_ptav.variant_image:
                matched_ptav.variant_image = ext_p.product_image
                count += 1
                _logger.info("  📌 PTAV '%s' ← ext_product '%s'",
                             matched_ptav.product_attribute_value_id.name, ext_p.name)

                # Aussi pousser vers la product.product
                variant = self._find_variant_for_ptav(template, matched_ptav)
                if variant and not variant.image_variant_1920:
                    variant.image_variant_1920 = ext_p.product_image

        # ── B. Images catalogue → PTAV ──
        if hasattr(self, 'catalog_image_ids') and self.catalog_image_ids:
            for cat_img in self.catalog_image_ids:
                if not cat_img.image or cat_img.assigned:
                    continue

                matched_ptav = self._match_ptav(
                    ptav_all,
                    cat_img.reference, cat_img.type_code,
                    description=cat_img.description,
                )
                if matched_ptav and not matched_ptav.variant_image:
                    matched_ptav.variant_image = cat_img.image
                    cat_img.assigned = True
                    count += 1
                    _logger.info("  📌 PTAV '%s' ← catalogue '%s'",
                                 matched_ptav.product_attribute_value_id.name,
                                 cat_img.description or cat_img.reference)

        # ── C. Données JSON furniture/shell → PTAV ──
        count += self._assign_from_json_variants(template, ptav_all)

        if count:
            template.variant_images_configured = True
        _logger.info("✅ %d images variantes assignées pour %s", count, template.name)
        return count

    def _match_ptav(self, ptav_records, reference=None, type_code=None,
                     capacity=None, variant_name=None, description=None):
        """Trouve la PTAV la plus proche d'un ensemble de critères textuels."""
        search_parts = [
            s.lower() for s in [reference or '', type_code or '',
                                capacity or '', variant_name or '',
                                description or '']
            if s
        ]
        if not search_parts:
            return None

        search_text = ' '.join(search_parts)
        best = None
        best_score = 0

        for ptav in ptav_records:
            if ptav.variant_image:
                continue
            val = ptav.product_attribute_value_id.name.lower()
            score = 0
            if val in search_text:
                score += 20
            for word in val.split():
                if len(word) >= 3 and word in search_text:
                    score += 5
            # Match inverse : mots du search_text dans val
            for part in search_parts:
                for word in part.split():
                    if len(word) >= 3 and word in val:
                        score += 3
            if score > best_score:
                best_score = score
                best = ptav

        return best if best and best_score >= 5 else None

    def _find_variant_for_ptav(self, template, ptav):
        """Trouve le product.product qui possède ce PTAV."""
        for variant in template.product_variant_ids:
            if ptav in variant.product_template_attribute_value_ids:
                return variant
        return None

    def _assign_from_json_variants(self, template, ptav_all):
        """
        Si furniture_variants_data / shell_colors_data contiennent des URLs
        ou des images encodées, les assigner aux PTAV correspondantes.
        """
        count = 0

        # Furniture variants avec images
        if hasattr(self, 'furniture_variants_data') and self.furniture_variants_data:
            try:
                fv_list = json.loads(self.furniture_variants_data)
                for fv in fv_list:
                    fv_name = (fv.get('name') or '').strip()
                    fv_image = fv.get('image')  # base64 si présent
                    if not fv_name or not fv_image:
                        continue
                    for ptav in ptav_all:
                        if ptav.variant_image:
                            continue
                        if ptav.product_attribute_value_id.name.lower() == fv_name.lower():
                            ptav.variant_image = fv_image
                            count += 1
                            _logger.info("  📌 PTAV '%s' ← JSON furniture", fv_name)
                            break
            except (json.JSONDecodeError, TypeError):
                pass

        # Shell colors avec images
        if hasattr(self, 'shell_colors_data') and self.shell_colors_data:
            try:
                sc_list = json.loads(self.shell_colors_data)
                for sc in sc_list:
                    sc_name = (sc.get('name') or '').strip()
                    sc_image = sc.get('image')
                    if not sc_name or not sc_image:
                        continue
                    for ptav in ptav_all:
                        if ptav.variant_image:
                            continue
                        if ptav.product_attribute_value_id.name.lower() == sc_name.lower():
                            ptav.variant_image = sc_image
                            count += 1
                            _logger.info("  📌 PTAV '%s' ← JSON shell_color", sc_name)
                            break
            except (json.JSONDecodeError, TypeError):
                pass

        return count
