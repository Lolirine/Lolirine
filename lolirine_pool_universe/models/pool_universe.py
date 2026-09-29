import logging
import random
import time

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Cache des blocs (boutique, accueil) pour les visiteurs anonymes (par processus).
# Le tirage change toutes les SHOP_TTL secondes ; les clients connectés sont
# toujours calculés en direct (liste de prix / position fiscale propres).
_SHOP_CACHE = {}
SHOP_TTL = 600


class LolirinePoolUniverse(models.Model):
    _name = 'lolirine.pool.universe'
    _description = "Univers produits (défilés fiche produit, boutique et accueil)"
    _order = 'sequence, id'

    name = fields.Char(string="Univers", required=True)
    sequence = fields.Integer(
        default=10,
        help="Ordre des zones sur la page boutique. Sur une fiche produit qui correspond "
             "à plusieurs univers, le premier dans l'ordre gagne.")
    active = fields.Boolean(default=True)
    website_id = fields.Many2one('website', string="Site web", ondelete='cascade')

    title = fields.Char(string="Titre affiché", required=True, translate=True)
    subtitle = fields.Char(string="Sous-titre", translate=True)

    trigger_categ_ids = fields.Many2many(
        'product.public.category', 'lolirine_universe_trigger_rel', 'universe_id', 'categ_id',
        string="Déclenché par",
        help="Fiche produit : le défilé s'affiche sur les produits de ces catégories "
             "(sous-catégories comprises). Boutique et accueil : ces catégories alimentent aussi la zone.")
    related_categ_ids = fields.Many2many(
        'product.public.category', 'lolirine_universe_related_rel', 'universe_id', 'categ_id',
        string="Gammes montrées",
        help="Les produits sont tirés au hasard dans ces catégories (sous-catégories comprises), "
             "en alternant les gammes.")

    limit = fields.Integer(string="Produits (fiche produit)", default=24)
    show_on_shop = fields.Boolean(string="Zone sur la boutique et l'accueil", default=True)
    shop_limit = fields.Integer(string="Produits (page boutique)", default=16)
    min_products = fields.Integer(
        string="Minimum pour afficher", default=6,
        help="En dessous de ce nombre, le défilé ou la zone n'est pas affiché.")
    seconds_per_item = fields.Float(string="Secondes par produit", default=3.5)
    only_with_image = fields.Boolean(string="Seulement les produits avec image", default=True)
    exclude_same_category = fields.Boolean(
        string="Exclure la gamme du produit affiché", default=True,
        help="Sur une pompe, on ne montre pas d'autres pompes mais le reste du local technique.")

    # ------------------------------------------------------------ cache
    @api.model_create_multi
    def create(self, vals_list):
        _SHOP_CACHE.clear()
        return super().create(vals_list)

    def write(self, vals):
        _SHOP_CACHE.clear()
        return super().write(vals)

    def unlink(self):
        _SHOP_CACHE.clear()
        return super().unlink()

    @api.model
    def _cached(self, key, builder):
        public = self.env.user._is_public()
        if public:
            hit = _SHOP_CACHE.get(key)
            if hit and time.time() - hit[0] < SHOP_TTL:
                return hit[1]
        value = builder()
        if public:
            _SHOP_CACHE[key] = (time.time(), value)
        return value

    # ------------------------------------------------------ fiche produit
    @api.model
    def _get_for_product(self, product, website=None):
        website = website or self.env['website'].get_current_website()
        product = product.sudo()
        universe = self._match(product, website)
        if not universe:
            return False
        try:
            items = universe._pick_items(website, product=product, limit=universe.limit)
        except Exception:
            _logger.exception("Défilé univers %s : échec pour le produit %s", universe.name, product.id)
            return False
        if len(items) < universe.min_products:
            return False
        return universe._zone_dict(items, universe.related_categ_ids)

    # ------------------------------------------------------ page boutique
    @api.model
    def _get_shop_zones(self, website=None):
        website = website or self.env['website'].get_current_website()
        return self._cached(('shop', website.id, self.env.lang),
                            lambda: self._build_shop_zones(website))

    @api.model
    def _build_shop_zones(self, website):
        zones, seen = [], set()
        for universe in self._shop_universes(website):
            categs = universe.related_categ_ids | universe.trigger_categ_ids
            try:
                items = universe._pick_items(website, limit=universe.shop_limit,
                                             seen=seen, categories=categs)
            except Exception:
                _logger.exception("Zone boutique %s : échec de sélection", universe.name)
                continue
            if len(items) < universe.min_products:
                continue
            zones.append(universe._zone_dict(items, categs))
        return zones

    # ------------------------------------------------------ page d'accueil
    @api.model
    def _get_home_blocks(self, website=None):
        website = website or self.env['website'].get_current_website()
        return self._cached(('home', website.id, self.env.lang),
                            lambda: self._build_home_blocks(website))

    @api.model
    def _build_home_blocks(self, website):
        blocks = {'showcase': False, 'tiles': [], 'lowprice': False}
        universes = self._shop_universes(website)
        if not universes:
            return blocks

        # 1. Vitrine du haut : quelques produits de CHAQUE univers, entrelacés
        seen, picks = set(), []
        per_universe = max(2, -(-(website.pu_showcase_count or 36) // len(universes)))
        for universe in universes:
            categs = universe.related_categ_ids | universe.trigger_categ_ids
            try:
                items = universe._pick_items(website, limit=per_universe, seen=seen, categories=categs)
            except Exception:
                _logger.exception("Vitrine accueil %s : échec de sélection", universe.name)
                items = []
            for item in items:
                item['tag'] = universe.name
            picks.append((universe, categs, items))

        filled = [(u, c, i) for u, c, i in picks if i]
        queues = [list(i) for _u, _c, i in filled]
        mixed = []
        while any(queues):
            for queue in queues:
                if queue:
                    mixed.append(queue.pop(0))
        if len(mixed) >= 12:
            half = (len(mixed) + 1) // 2
            rows = [mixed[:half], mixed[half:]]
            blocks['showcase'] = {
                'title': "Tout pour votre piscine",
                'subtitle': "Un aperçu de nos %d univers, de la construction au bien-être" % len(filled),
                'links': [{'name': u.name, 'url': '/shop#pu-zone-%d' % u.id} for u, _c, _i in filled],
                'rows': [{'items': row,
                          'duration': max(30, round(len(row) * 3.5)),
                          'reverse': index == 1}
                         for index, row in enumerate(rows)],
            }

        # 2. Tuiles « Explorez par univers » : nombre de produits + 3 vignettes
        if website.pu_home_tiles:
            PT = self.env['product.template'].sudo()
            base = [('is_published', '=', True), ('sale_ok', '=', True),
                    ('website_id', 'in', [website.id, False])]
            for universe, categs, items in filled:
                count = PT.search_count(base + [('public_categ_ids', 'child_of', categs.ids)])
                if not count:
                    continue
                blocks['tiles'].append({
                    'name': universe.name,
                    'count': count,
                    'url': '/shop#pu-zone-%d' % universe.id,
                    'thumbs': [item['image'] for item in items[:3]],
                })

        # 3. Petits prix : accessoires et consommables sous le seuil, toutes gammes
        if website.pu_home_lowprice:
            all_categs = self.env['product.public.category'].browse()
            for _u, categs, _i in picks:
                all_categs |= categs
            max_price = website.pu_lowprice_max or 25.0
            try:
                items = universes[:1]._pick_items(
                    website, limit=24, seen=seen, categories=all_categs,
                    extra_domain=[('list_price', '<=', max_price)])
            except Exception:
                _logger.exception("Petits prix accueil : échec de sélection")
                items = []
            if len(items) >= 6:
                blocks['lowprice'] = {
                    'id': 0,
                    'anchor': 'pu-home-lowprice',
                    'name': "Petits prix",
                    'title': "Petits prix",
                    'subtitle': "Accessoires et consommables pour un petit budget",
                    'chips': [{'name': "Toute la boutique", 'url': '/shop'}],
                    'items': items,
                    'duration': max(30, round(len(items) * 3.5)),
                }
        return blocks

    # ------------------------------------------------------------ helpers
    @api.model
    def _shop_universes(self, website):
        return self.search([('website_id', 'in', [website.id, False]), ('show_on_shop', '=', True)])

    def _zone_dict(self, items, categs):
        self.ensure_one()
        return {
            'id': self.id,
            'anchor': 'pu-zone-%d' % self.id,
            'name': self.name,
            'title': self.title,
            'subtitle': self.subtitle or '',
            'chips': [{'name': c.name, 'url': '/shop?category=%d' % c.id} for c in categs[:8]],
            'items': items,
            'duration': max(30, round(len(items) * (self.seconds_per_item or 3.5))),
        }

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

    def _pick_items(self, website, product=None, limit=24, seen=None, categories=None,
                    extra_domain=None):
        """Tirage aléatoire en alternant les gammes.

        product      : fiche affichée (exclue, et sa gamme aussi si exclude_same_category)
        seen         : set partagé entre zones pour ne pas répéter un produit sur la page
        categories   : gammes à piocher (par défaut related_categ_ids)
        extra_domain : filtre supplémentaire (ex. prix maximum)
        """
        self.ensure_one()
        PT = self.env['product.template'].sudo()
        seen = seen if seen is not None else set()
        categories = categories if categories is not None else self.related_categ_ids

        base = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('list_price', '>', 0),
            ('website_id', 'in', [website.id, False]),
        ] + list(extra_domain or [])
        if self.only_with_image:
            base.append(('image_128', '!=', False))
        if product:
            base.append(('id', '!=', product.id))
            own = product.public_categ_ids.ids
            if self.exclude_same_category and own:
                base.append(('public_categ_ids', 'not in', own))

        pools = []
        for categ in categories:
            ids = [i for i in PT.search(base + [('public_categ_ids', 'child_of', categ.id)]).ids
                   if i not in seen]
            if ids:
                random.shuffle(ids)
                pools.append(ids)
        random.shuffle(pools)

        picked = []
        while pools and len(picked) < limit:
            for pool in list(pools):
                while pool and pool[-1] in seen:
                    pool.pop()
                if not pool:
                    pools.remove(pool)
                    continue
                pid = pool.pop()
                seen.add(pid)
                picked.append(pid)
                if len(picked) >= limit:
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
