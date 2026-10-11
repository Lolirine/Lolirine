import logging
import random
import time

from odoo import api, fields, models

from .pool_universe import _SHOP_CACHE, SHOP_TTL

_logger = logging.getLogger(__name__)

WEBSITE_ID = 6

# Réglages de départ. Les catégories absentes sont ignorées (plusieurs ont été
# fusionnées en juillet) : les mots-clés prennent alors le relais.
DEFAULT_CAMPAIGNS = [
    {
        'code': 'hivernage',
        'name': "Hivernage",
        'sequence': 10,
        'theme': 'winter',
        'badge': "Offre hivernage",
        'title': "Préparez l'hivernage de votre piscine",
        'subtitle': "Produits d'hivernage, couvertures, flotteurs et bouchons : "
                    "tout pour protéger votre bassin jusqu'au printemps",
        'start_month': 9, 'start_day': 1, 'end_month': 12, 'end_day': 15,
        'categ_ids': [84, 193],
        'keywords': "hivernage\nhiver\ngizzmo\nflotteur\nbouchon\nantigel\n"
                    "couverture à barres\nbâche à barres\nsandow",
        'exclude_keywords': "couverture d'été\nbâche d'été\nsolaire",
    },
    {
        'code': 'remise_en_route',
        'name': "Remise en route",
        'sequence': 20,
        'theme': 'spring',
        'badge': "Remise en route",
        'title': "Relancez votre piscine en toute sérénité",
        'subtitle': "Traitement choc, équilibre de l'eau, nettoyage et filtration : "
                    "tout pour une eau claire dès les beaux jours",
        'start_month': 2, 'start_day': 15, 'end_month': 6, 'end_day': 30,
        'categ_ids': [186, 184, 190, 189, 191, 171, 120, 90, 89],
        'keywords': "remise en route\nremise en service\ndémarrage\nchoc\nfloculant\n"
                    "clarifiant\nligne d'eau\ncartouche\nsable filtrant\nverre filtrant\n"
                    "bandelette\ntrousse d'analyse\ntesteur",
        'exclude_keywords': "hivernage",
    },
]


class LolirinePoolCampaign(models.Model):
    _name = 'lolirine.pool.campaign'
    _description = "Encart saisonnier (hivernage, remise en route…)"
    _order = 'sequence, id'

    name = fields.Char(string="Encart", required=True)
    code = fields.Char(
        string="Code", required=True,
        help="Identifiant technique utilisé par le bloc du constructeur et par l'adresse /saison/<code>.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one('website', string="Site web", ondelete='cascade')

    theme = fields.Selection([
        ('winter', "Hiver — bleu glacier"),
        ('spring', "Printemps — turquoise et soleil"),
    ], string="Ambiance", default='winter', required=True)
    badge = fields.Char(string="Badge clignotant", translate=True, default="Offre de saison")
    title = fields.Char(string="Titre", required=True, translate=True)
    subtitle = fields.Char(string="Sous-titre", translate=True)
    cta_label = fields.Char(string="Texte du bouton", translate=True, default="Voir toute la sélection")

    mode = fields.Selection([
        ('auto', "Selon la période"),
        ('on', "Toujours affiché"),
        ('off', "Masqué"),
    ], string="Affichage", default='auto', required=True,
        help="Selon la période : l'encart n'apparaît sur le site qu'entre les deux dates, chaque année. "
             "Le bloc reste en place dans la page et réapparaît tout seul la saison suivante.")
    start_month = fields.Integer(string="Début (mois)", default=9)
    start_day = fields.Integer(string="Début (jour)", default=1)
    end_month = fields.Integer(string="Fin (mois)", default=11)
    end_day = fields.Integer(string="Fin (jour)", default=30)

    categ_ids = fields.Many2many(
        'product.public.category', 'lolirine_campaign_categ_rel', 'campaign_id', 'categ_id',
        string="Catégories", help="Tous les produits de ces catégories (sous-catégories comprises).")
    keywords = fields.Text(
        string="Mots-clés", help="Un mot-clé par ligne, cherché dans le nom des produits publiés.")
    exclude_keywords = fields.Text(
        string="Mots-clés exclus", help="Un mot-clé par ligne : les produits dont le nom le contient sont retirés.")
    exclude_categ_ids = fields.Many2many(
        'product.public.category', 'lolirine_campaign_excl_categ_rel', 'campaign_id', 'categ_id',
        string="Catégories exclues",
        help="Les produits de ces catégories (sous-catégories comprises) sont retirés, "
             "même s'ils ont été trouvés par un mot-clé. Ex. : Raccorderie PVC, Plomberie.")
    exclude_product_ids = fields.Many2many(
        'product.template', 'lolirine_campaign_excl_product_rel', 'campaign_id', 'product_tmpl_id',
        string="Produits exclus",
        help="Produits retirés un par un (bouton « Exclure » de l'onglet Produits trouvés).")
    found_product_ids = fields.Many2many(
        'product.template', string="Produits trouvés (liste)", compute='_compute_found_products',
        help="Produits actuellement dans l'encart, après toutes les exclusions.")

    limit = fields.Integer(string="Produits dans le défilé", default=24)
    only_with_image = fields.Boolean(string="Défilé : seulement les produits avec image", default=True)

    product_count = fields.Integer(string="Produits trouvés", compute='_compute_live_info')
    is_live = fields.Boolean(string="Affiché aujourd'hui", compute='_compute_live_info')

    _code_unique = models.Constraint('UNIQUE(code)', "Ce code d'encart existe déjà.")

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

    # ------------------------------------------------------------ période
    def _in_period(self):
        self.ensure_one()
        if not self.active or self.mode == 'off':
            return False
        if self.mode == 'on':
            return True
        today = fields.Date.context_today(self)
        cur = (today.month, today.day)
        start = (self.start_month or 1, self.start_day or 1)
        end = (self.end_month or 12, self.end_day or 31)
        if start <= end:
            return start <= cur <= end
        return cur >= start or cur <= end      # période à cheval sur deux années

    def _website(self):
        self.ensure_one()
        return self.website_id or self.env['website'].browse(WEBSITE_ID).exists() \
            or self.env['website'].get_current_website()

    @api.depends('mode', 'active', 'start_month', 'start_day', 'end_month', 'end_day',
                 'categ_ids', 'keywords', 'exclude_keywords', 'exclude_categ_ids', 'exclude_product_ids')
    def _compute_live_info(self):
        for campaign in self:
            campaign.is_live = campaign._in_period()
            try:
                campaign.product_count = len(campaign._product_ids(campaign._website()))
            except Exception:
                campaign.product_count = 0

    # ------------------------------------------------------------ produits
    @staticmethod
    def _lines(text):
        return [line.strip() for line in (text or '').splitlines() if line.strip()]

    def _product_ids(self, website, with_image=False):
        """Tous les produits publiés de l'encart : catégories + mots-clés − exclusions."""
        self.ensure_one()
        PT = self.env['product.template'].sudo()
        base = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('list_price', '>=', 1),
            ('website_id', 'in', [website.id, False]),
        ]
        if with_image:
            base.append(('image_128', '!=', False))
        ids = set()
        if self.categ_ids:
            ids |= set(PT.search(base + [('public_categ_ids', 'child_of', self.categ_ids.ids)]).ids)
        for keyword in self._lines(self.keywords):
            ids |= set(PT.search(base + [('name', 'ilike', keyword)]).ids)
        for keyword in self._lines(self.exclude_keywords):
            if ids:
                ids -= set(PT.search([('id', 'in', list(ids)), ('name', 'ilike', keyword)]).ids)
        if ids and self.exclude_categ_ids:
            ids -= set(PT.search([('id', 'in', list(ids)),
                                  ('public_categ_ids', 'child_of', self.exclude_categ_ids.ids)]).ids)
        ids -= set(self.exclude_product_ids.ids)
        return list(ids)

    @api.depends('categ_ids', 'keywords', 'exclude_keywords', 'exclude_categ_ids', 'exclude_product_ids')
    def _compute_found_products(self):
        PT = self.env['product.template'].sudo()
        for campaign in self:
            try:
                ids = campaign._product_ids(campaign._website()) if campaign.id else []
            except Exception:
                ids = []
            campaign.found_product_ids = PT.browse(ids).sorted(
                lambda p: ((p.public_categ_ids[:1].name or 'zz').lower(), (p.name or '').lower()))

    @api.model
    def _items(self, website, products):
        PT = self.env['product.template'].sudo()
        has_brand = 'pool_brand_id' in PT._fields
        items = []
        for p in products:
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

    def _base_dict(self):
        self.ensure_one()
        return {
            'code': self.code,
            'theme': self.theme,
            'badge': self.badge or '',
            'title': self.title,
            'subtitle': self.subtitle or '',
            'cta_label': self.cta_label or "Voir toute la sélection",
            'url': '/saison/%s' % self.code,
        }

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

    def _block_data(self, website):
        """Encart posé dans une page : défilé aléatoire + lien vers la sélection complète."""
        self.ensure_one()

        def build():
            all_ids = self._product_ids(website)
            pick = self._product_ids(website, with_image=True) if self.only_with_image else list(all_ids)
            random.shuffle(pick)
            products = self.env['product.template'].sudo().browse(pick[:self.limit or 24])
            items = self._items(website, products)
            if len(items) < 4:
                return False
            data = self._base_dict()
            data.update({
                'items': items,
                'count': len(all_ids),
                'duration': max(30, round(len(items) * 3.5)),
            })
            return data

        return self._cached(('saison_bloc', self.id, website.id, self.env.lang), build)

    def _page_data(self, website, max_products=240):
        """Page /saison/<code> : toute la sélection, rangée par catégorie puis par nom."""
        self.ensure_one()

        def build():
            products = self.env['product.template'].sudo().browse(self._product_ids(website))
            products = products.sorted(lambda p: ((p.public_categ_ids[:1].name or 'zz').lower(),
                                                  (p.name or '').lower()))
            data = self._base_dict()
            data.update({
                'items': self._items(website, products[:max_products]),
                'count': len(products),
                'truncated': len(products) > max_products,
            })
            return data

        return self._cached(('saison_page', self.id, website.id, self.env.lang), build)

    # ------------------------------------------------------------ actions
    def action_select_products(self):
        """Liste complète des produits de l'encart (+ exclus) : cases à cocher, filtres, regroupements."""
        self.ensure_one()
        ids = set(self._product_ids(self._website())) | set(self.exclude_product_ids.ids)
        return {
            'type': 'ir.actions.act_window',
            'name': "Produits de l'encart « %s »" % self.name,
            'res_model': 'product.template',
            'view_mode': 'list',
            'views': [(self.env.ref('lolirine_pool_universe.view_pu_campaign_product_list').id, 'list')],
            'search_view_id': self.env.ref('lolirine_pool_universe.view_pu_campaign_product_search').id,
            'domain': [('id', 'in', list(ids))],
            'context': {'pu_campaign_id': self.id, 'create': False},
            'target': 'current',
        }

    def action_open_page(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': '/saison/%s' % self.code, 'target': 'new'}

    @api.model
    def action_seed_defaults(self):
        """Crée les deux encarts de départ s'ils n'existent pas (jamais d'écrasement)."""
        Campaign = self.sudo().with_context(active_test=False)
        Categ = self.env['product.public.category'].sudo()
        website = self.env['website'].browse(WEBSITE_ID).exists()
        for vals in DEFAULT_CAMPAIGNS:
            if Campaign.search_count([('code', '=', vals['code'])]):
                continue
            vals = dict(vals)
            vals['categ_ids'] = [(6, 0, Categ.browse(vals['categ_ids']).exists().ids)]
            vals['website_id'] = website.id if website else False
            Campaign.create(vals)
            _logger.info("Encart saisonnier créé : %s", vals['name'])
        return True
