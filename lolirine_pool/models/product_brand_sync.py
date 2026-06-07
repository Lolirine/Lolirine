# -*- coding: utf-8 -*-
"""Synchronisation pool_brand_id -> attribut de filtrage "Marque".

L'attribut e-commerce "Marque" (no_variant, visible dans les filtres
boutique) est maintenu aligné sur le champ pool_brand_id :
- création/modification d'un produit avec marque -> ligne d'attribut posée/mise à jour ;
- marque retirée ou marque exclue (groupes, non-marques) -> ligne supprimée ;
- renommage d'une pool.brand -> la valeur d'attribut suit.

Périmètre global (tout le catalogue) : la généralisation aux autres
chapitres se fait donc progressivement, au fil des éditions de fiches.
"""
from odoo import api, models

# Entrées pool.brand qui ne sont pas des marques produit :
# jamais exposées dans le filtre boutique.
BRAND_SYNC_EXCLUDE = {
    'fluidra',
    'fluidra benelux',
    'astralpool / aquaforte',
}


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_brand_filter_attribute(self):
        """L'attribut Marque de filtrage — strictement no_variant
        (le critère évite tout attribut homonyme à variantes)."""
        return self.env['product.attribute'].search([
            ('name', '=', 'Marque'),
            ('create_variant', '=', 'no_variant'),
        ], limit=1)

    def _sync_brand_attribute(self):
        attr = self.sudo()._get_brand_filter_attribute()
        if not attr:
            return  # attribut absent : sync silencieusement inactive
        PAV = self.env['product.attribute.value'].sudo()
        for tmpl in self:
            line = tmpl.attribute_line_ids.filtered(
                lambda l: l.attribute_id == attr)
            brand = tmpl.pool_brand_id
            key = (brand.name or '').strip().lower() if brand else ''

            # Pas de marque, ou marque exclue -> retirer la ligne
            if not brand or key in BRAND_SYNC_EXCLUDE:
                if line:
                    line.unlink()
                continue

            val = attr.value_ids.filtered(
                lambda v: v.name.strip().lower() == key)[:1]
            if not val:
                val = PAV.create({
                    'attribute_id': attr.id,
                    'name': brand.name.strip(),
                })
            if line:
                if line.value_ids != val:
                    line.value_ids = [(6, 0, val.ids)]
            else:
                tmpl.attribute_line_ids = [(0, 0, {
                    'attribute_id': attr.id,
                    'value_ids': [(6, 0, val.ids)],
                })]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        to_sync = records.filtered('pool_brand_id')
        if to_sync:
            to_sync._sync_brand_attribute()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'pool_brand_id' in vals:
            self._sync_brand_attribute()
        return res


class PoolBrand(models.Model):
    _inherit = 'pool.brand'

    def write(self, vals):
        """Renommage d'une marque -> la valeur d'attribut suit."""
        old_names = {b.id: b.name for b in self} if 'name' in vals else {}
        res = super().write(vals)
        if 'name' in vals:
            attr = self.env['product.template']._get_brand_filter_attribute()
            if attr:
                for b in self:
                    old = (old_names.get(b.id) or '').strip().lower()
                    new = (b.name or '').strip()
                    val = attr.value_ids.filtered(
                        lambda v: v.name.strip().lower() == old)
                    if val and new and new.lower() != old:
                        val.name = new
        return res
