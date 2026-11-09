# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

# Bloc ajouté au robots.txt du site s'il est encore vide (jamais écrasé).
# /web/ n'est PAS bloqué : les images produits (/web/image) doivent rester
# accessibles à Google Images / Google Shopping.
ROBOTS_DEFAULT = """Disallow: /shop/cart
Disallow: /shop/checkout
Disallow: /shop/address
Disallow: /shop/payment
Disallow: /shop/confirmation
Disallow: /shop/extra_info
Disallow: /shop/wishlist
Disallow: /shop/compare
Disallow: /my/
Disallow: /website/search
Disallow: /*?*attrib=
Disallow: /*?*search=
Disallow: /lolirine_seo/
"""


def post_init_hook(env):
    icp = env['ir.config_parameter'].sudo()
    if not icp.get_param('lolirine_seo.website_ids'):
        site = env['website'].sudo().search([('domain', 'ilike', 'lolirinepoolstore')], limit=1)
        icp.set_param('lolirine_seo.website_ids', str(site.id) if site else '6')
    for website in env['lolirine.seo.config']._target_websites():
        if not (website.robots_txt or '').strip():
            website.robots_txt = ROBOTS_DEFAULT
            _logger.info("lolirine_seo: robots.txt initialisé pour %s", website.name)
    if not icp.get_param('lolirine_seo.indexnow_enabled'):
        icp.set_param('lolirine_seo.indexnow_enabled', '1')
