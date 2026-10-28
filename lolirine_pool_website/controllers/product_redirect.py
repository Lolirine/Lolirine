# -*- coding: utf-8 -*-
import logging
import re

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale, handle_product_params_error

_logger = logging.getLogger(__name__)
PREFIXE_LANGUE = re.compile(r'^/[a-z]{2}(?:_[A-Za-z]{2})?(?=/shop/)')


def _redirection_fiche(product):
    """Cherche la redirection 301/302 prevue pour une fiche archivee : par adresse
    exacte, puis par identifiant de fiche (anciennes adresses en -<id>)."""
    website = request.env['website'].sudo().get_current_website()
    Rewrite = request.env['website.rewrite'].sudo()
    base = [('redirect_type', 'in', ['301', '302']), ('website_id', 'in', [False, website.id])]
    path = request.httprequest.path
    chemins = list({path, PREFIXE_LANGUE.sub('', path)})
    rw = Rewrite.search(base + [('url_from', 'in', chemins)], limit=1)
    if not rw and product and product.id:
        rw = Rewrite.search(base + [('url_from', '=like', '/shop/%%-%d' % product.id)], limit=1)
    return rw


def handle_product_redirect(exc, product=None, category=None, **kwargs):
    """Appele par Odoo avant le controleur quand la fiche est inaccessible
    (archivee, fusionnee). Applique la redirection prevue, sinon comportement
    standard. Ne doit jamais lever d'erreur : en cas de probleme, 404 standard."""
    try:
        rw = _redirection_fiche(product)
        if rw:
            return request.redirect(rw.url_to, code=int(rw.redirect_type), local=True)
    except Exception:
        _logger.exception("Redirection de fiche archivee impossible pour %s", request.httprequest.path)
    return handle_product_params_error(exc, product, category=category, **kwargs)


class WebsiteSaleRedirectionFiches(WebsiteSale):

    @http.route(handle_params_access_error=handle_product_redirect)
    def product(self, product, category=None, pricelist=None, **kwargs):
        return super().product(product, category=category, pricelist=pricelist, **kwargs)
