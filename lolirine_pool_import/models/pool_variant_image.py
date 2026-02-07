# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateAttributeValueImage(models.Model):
    _inherit = 'product.template.attribute.value'

    variant_image = fields.Image(
        string='Image variante',
        max_width=1920, max_height=1920,
    )
    variant_image_128 = fields.Image(
        string='Miniature',
        related='variant_image',
        max_width=128, max_height=128,
        store=True,
    )


class ProductTemplateVariantImages(models.Model):
    _inherit = 'product.template'

    variant_images_configured = fields.Boolean(
        string='Images variantes configurées',
        default=False,
        copy=False,
    )

    def action_auto_assign_variant_images(self):
        """Assigne automatiquement les images aux PTAV."""
        for tmpl in self:
            r = tmpl._auto_assign_variant_images()
        if len(self) == 1:
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
        """Distribue les product.image aux variantes."""
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
            raise UserError(_("Aucune image non-assignée disponible."))

        assigned = 0
        vlist = list(variants)
        for idx, img in enumerate(unassigned):
            target = vlist[idx % len(vlist)]
            img.product_variant_id = target.id
            if not target.image_variant_1920:
                target.image_variant_1920 = img.image_1920
            assigned += 1

        self._sync_variant_images_to_ptav()
        self.variant_images_configured = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Distribution terminée'),
                'message': _("%d image(s) répartie(s)") % assigned,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_variant_images(self):
        """Remet toutes les images en mode global."""
        self.ensure_one()
        ProductImage = self.env['product.image']
        imgs = ProductImage.search([
            ('product_tmpl_id', '=', self.id),
            ('product_variant_id', '!=', False),
        ])
        imgs.write({'product_variant_id': False})
        for v in self.product_variant_ids:
            v.image_variant_1920 = False
        for line in self.attribute_line_ids:
            for ptav in line.product_template_value_ids:
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

    def _auto_assign_variant_images(self):
        """Auto-assignation par matching nom image / nom valeur attribut."""
        self.ensure_one()
        ptav_list = []
        for line in self.attribute_line_ids:
            for ptav in line.product_template_value_ids:
                ptav_list.append(ptav)

        if not ptav_list:
            return {'count': 0, 'message': _("Pas d'attributs.")}

        count = 0
        ProductImage = self.env['product.image']
        all_images = ProductImage.search([('product_tmpl_id', '=', self.id)])

        for ptav in ptav_list:
            if ptav.variant_image:
                continue
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

        for variant in self.product_variant_ids:
            if not variant.image_variant_1920:
                continue
            for ptav in variant.product_template_attribute_value_ids:
                if not ptav.variant_image:
                    ptav.variant_image = variant.image_variant_1920
                    count += 1

        if count:
            self.variant_images_configured = True
        return {'count': count, 'message': _("%d image(s) assignée(s)") % count}

    def _sync_variant_images_to_ptav(self):
        """Copie image_variant_1920 → PTAV."""
        self.ensure_one()
        for variant in self.product_variant_ids:
            if not variant.image_variant_1920:
                continue
            for ptav in variant.product_template_attribute_value_ids:
                if not ptav.variant_image:
                    ptav.variant_image = variant.image_variant_1920

    @api.model
    def cron_assign_all_variant_images(self):
        """CRON : traite tous les produits avec variantes."""
        templates = self.search([('product_variant_count', '>', 1)])
        total = 0
        processed = 0
        for tmpl in templates:
            try:
                r = tmpl._auto_assign_variant_images()
                total += r.get('count', 0)
                processed += 1
            except Exception as e:
                _logger.error("Erreur variant images %s: %s", tmpl.name, e)
        _logger.info("Batch terminé: %d produits, %d images", processed, total)
        return {'processed': processed, 'assigned': total}
