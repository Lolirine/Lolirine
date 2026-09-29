import logging
import random

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LolirinePoolUniverse(models.Model):
    _name = 'lolirine.pool.universe'
    _description = "Univers produits (défilé fiche produit)"
    _order = 'sequence, id'

    name = fields.Char(string="Univers", required=True)
    sequence = fields.Integer(
        default=10,
        help="Si un produit correspond à plusieurs univers, le premier dans l'ordre gagne.")
    active = fields.Boolean(default=True)
    website_id = fields.Many2one('website', string="Site web", ondelete='cascade')

    title = fields.Char(string="Titre affiché", required=True, translate=True)
    subtitle = fields.Char(string="Sous-titre", translate=True)

    trigger_categ_ids = fields.Many2many(
        'product.public.category', 'lolirine_universe_trigger_rel', 'universe_id', 'categ_id',
        string="Déclenché par",
        help="Le défilé s'affiche sur les fiches rangées dans ces catégories ou leurs sous-catégories.")
    related_categ_ids = fields.Many2many(
        'product.public.category', 'lolirine_universe_related_rel', 'universe_id', 'categ_id',
        string="Gammes montrées",
        help="Les produits du défilé sont tirés au hasard dans ces catégories (sous-catégories comprises), "
             "en alternant les gammes.")

    limit = fields.Integer(string="Produits dans le défilé", default=24)
    min_products = fields.Integer(
        string="Minimum pour afficher", default=6,
        help="En dessous de ce nombre, le défilé n'est pas affiché.")
    seconds_per_item = fields.Float(string="Secondes par produit", default=3.5)
    only_with_image = fields.Boolean(string="Seulement les produits avec image", default=True)
    exclude_same_category = fields.Boolean(
        string="Exclure la gamme du produit affiché", default=True,
        help="Sur une pompe, on ne montre pas d'autres pompes mais le reste du local technique.")

    # ------------------------------------------------------------------ API
    @api.model
    def _get_for_product(self, product, website=None):
        website = website or self.env['website'].get_current_website()
        product = product.sudo()
        universe = self._match(product, website)
        if not universe:
            return False
        try:
            items = universe._pick_items(product, website)
        except Exception:
            _logger.exception("Défilé univers %s : échec de sélection pour le produit %s",
                              universe.name, product.id)
            return False
        if len(items) < universe.min_products:
            return False
        return {
            'title': universe.title,
            'subtitle': universe.subtitle or '',
            'chips': [{'name': c.name, 'url': '/shop?category=%d' % c.id}
                      for c in universe.related_categ_ids[:8]],
            'items': items,
            'duration': max(30, round(len(items) * (universe.seconds_per_item or 3.5))),
        }

    # -------------------------------------------------------------- helpers
    @api.model
    def _match(self, product, website):
        lineage = set()
        for categ in product.public_categ_ids:
            path = [int(x) for x in (categ.parent_path or '').split('/') if x]
            lineage.update(path or [categ.id])
        if not lineage:
            return self.browse()
        for universe in self.search([('website_id', 'in', [website.id, False])]):
            if set(universe.trigger_categ_ids.ids) & lineage:
                return universe
        return self.browse()

    def _pick_items(self, product, website):
        self.ensure_one()
        PT = self.env['product.template'].sudo()
        base = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('id', '!=', product.id),
            ('website_id', 'in', [website.id, False]),
        ]
        if self.only_with_image:
            base.append(('image_128', '!=', False))
        own = product.public_categ_ids.ids
        if self.exclude_same_category and own:
            base.append(('public_categ_ids', 'not in', own))

        # Une réserve mélangée par gamme, puis tirage en alternance → variété maximale
        pools = []
        for categ in self.related_categ_ids:
            ids = PT.search(base + [('public_categ_ids', 'child_of', categ.id)]).ids
            if ids:
                random.shuffle(ids)
                pools.append(ids)
        random.shuffle(pools)

        picked, seen = [], set()
        while pools and len(picked) < self.limit:
            for pool in list(pools):
                while pool and pool[-1] in seen:
                    pool.pop()
                if not pool:
                    pools.remove(pool)
                    continue
                pid = pool.pop()
                seen.add(pid)
                picked.append(pid)
                if len(picked) >= self.limit:
                    break

        has_brand = 'pool_brand_id' in PT._fields
        items = []
        for p in PT.browse(picked):
            price = p.list_price
            try:
                price = p._get_combination_info(only_template=True).get('price', price)
            except Exception:
                pass
            items.append({
                'id': p.id,
                'name': p.name,
                'url': p.website_url,
                'image': website.image_url(p, 'image_512'),
                'brand': (p.pool_brand_id.name or '') if has_brand else '',
                'price': price,
                'from_price': p.product_variant_count > 1,
            })
        return items
