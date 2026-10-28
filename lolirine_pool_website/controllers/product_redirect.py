# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale, handle_product_params_error


def handle_product_redirect(exc, product, category=None, **kwargs):
    """Fiche produit archivee ou inaccessible : avant la 404 standard, on applique
    la redirection 301/302 (website.rewrite) prevue pour elle, par exemple apres
    une fusion de fiches. Recherche par adresse exacte, puis par identifiant de la
    fiche (toutes ses anciennes adresses finissent par -<id>, quel que soit le nom)."""
    Rewrite = request.env['website.rewrite'].sudo()
    base = [('redirect_type', 'in', ['301', '302']), ('website_id', 'in', [False, request.website.id])]
    path = request.httprequest.path
    lang = request.lang.url_code if request.lang else ''
    chemins = {path}
    if lang and path.startswith('/%s/' % lang):
        chemins.add(path[len(lang) + 1:])
    rw = Rewrite.search(base + [('url_from', 'in', list(chemins))], limit=1)
    if not rw and product:
        rw = Rewrite.search(base + [('url_from', '=like', '/shop/%%-%d' % product.id)], limit=1)
    if rw:
        return request.redirect(request.env['ir.http']._url_for(rw.url_to), code=int(rw.redirect_type))
    return handle_product_params_error(exc, product, category=category, **kwargs)


class WebsiteSaleRedirectionFiches(WebsiteSale):

    @http.route(handle_params_access_error=handle_product_redirect)
    def product(self, product, category=None, pricelist=None, **kwargs):
        return super().product(product, category=category, pricelist=pricelist, **kwargs)
