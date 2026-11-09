# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models

from . import seo_sources as S

PAGE_TYPES = [
    ('home', 'Accueil'), ('shop', 'Boutique'), ('category', 'Catégorie'),
    ('product', 'Fiche produit'), ('guide', 'Guide'), ('search', 'Recherche interne'),
    ('checkout', 'Panier / commande'), ('confirmation', 'Commande confirmée'),
    ('page', 'Autre page'),
]


class LolirineSeoHit(models.Model):
    """Une page vue. is_landing = première page d'une visite (entrée sur le site).

    Aucune donnée personnelle : pas d'IP, pas de cookie, pas d'identifiant.
    La source d'entrée de la visite est recopiée sur chaque page vue (via
    sessionStorage côté navigateur) pour attribuer les conversions.
    """
    _name = 'lolirine.seo.hit'
    _description = 'Page vue (SEO & trafic)'
    _order = 'date desc, id desc'
    _rec_name = 'path'

    date = fields.Datetime('Date', required=True, default=fields.Datetime.now, index=True)
    day = fields.Date('Jour', required=True, index=True, default=fields.Date.context_today)
    website_id = fields.Many2one('website', 'Site', index=True, ondelete='cascade')
    path = fields.Char('Page', required=True, index=True)
    lang = fields.Char('Langue')
    page_type = fields.Selection(PAGE_TYPES, 'Type de page', index=True)
    product_tmpl_id = fields.Many2one('product.template', 'Produit', index='btree_not_null',
                                      ondelete='set null')
    is_landing = fields.Boolean('Entrée', index=True,
                                help="Première page de la visite (la visite est comptée ici).")
    source_type = fields.Selection(S.SOURCE_TYPES, 'Type de source', index=True)
    source_name = fields.Char('Source', index=True)
    referrer_host = fields.Char('Site référent')
    search_query = fields.Char('Requête (si transmise)')
    utm_source = fields.Char('utm_source')
    utm_medium = fields.Char('utm_medium')
    utm_campaign = fields.Char('Campagne')
    landing_path = fields.Char('Page d\'entrée de la visite')
    device = fields.Selection([('desktop', 'Ordinateur'), ('tablet', 'Tablette'),
                               ('mobile', 'Mobile')], 'Appareil')
    country_code = fields.Char('Pays', size=2)
    order_id = fields.Many2one('sale.order', 'Commande', index='btree_not_null',
                               ondelete='set null')
    amount = fields.Float('Montant commande', help="Montant TTC de la commande confirmée.")

    @api.model
    def _site_hosts(self, website):
        hosts = set()
        for site in self.env['lolirine.seo.config']._target_websites() | website:
            h = S.host_of(site.domain or '')
            if h:
                hosts.update({h, h[4:] if h.startswith('www.') else 'www.' + h})
        return hosts

    @api.model
    def _record(self, website, payload, user_agent, country_code=None, order=None):
        """Crée une page vue depuis la balise JS. Retourne le record ou False."""
        path = (payload.get('p') or '/')[:500]
        if not path.startswith('/'):
            return False
        lang, bare = S.split_lang(path.split('?')[0].split('#')[0])
        page_type, tmpl_id = S.page_type_of(bare)
        entry_ref = payload.get('er') or ''
        entry_url = payload.get('eu') or ''
        hosts = self._site_hosts(website)
        src = S.classify(entry_ref, entry_url, hosts)
        landing = bool(payload.get('l'))
        if src['source_type'] == 'internal':
            # Entrée interne = sessionStorage perdu (nouvel onglet) -> direct
            src['source_type'] = 'direct'
        vals = {
            'website_id': website.id,
            'path': bare[:255],
            'lang': lang or (payload.get('lg') or '')[:8],
            'page_type': page_type,
            'is_landing': landing,
            'source_type': src['source_type'],
            'source_name': src['source_name'] or False,
            'referrer_host': src['referrer_host'] or False,
            'search_query': src['search_query'] or False,
            'utm_source': src['utm_source'] or False,
            'utm_medium': src['utm_medium'] or False,
            'utm_campaign': src['utm_campaign'] or False,
            'landing_path': S.split_lang(
                (S.urlsplit(entry_url).path if entry_url else bare))[1][:255],
            'device': S.device_of(user_agent),
            'country_code': (country_code or '')[:2].upper() or False,
        }
        if tmpl_id:
            tmpl = self.env['product.template'].sudo().browse(tmpl_id).exists()
            vals['product_tmpl_id'] = tmpl.id or False
        if page_type == 'confirmation' and order:
            vals.update(order_id=order.id, amount=order.amount_total)
        return self.sudo().create(vals)

    @api.autovacuum
    def _gc_old_hits(self):
        limit = fields.Datetime.now() - timedelta(days=400)
        self.sudo().search([('date', '<', limit)], limit=50000).unlink()
