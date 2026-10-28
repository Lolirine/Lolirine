# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.account.controllers.terms import TermsController

SITE_POOL_STORE = 6
CGV_POOL_STORE = '/conditions-generales-de-vente'


class PoolTermsController(TermsController):
    """/terms affiche les conditions de la societe, qui sont celles du
    garde-meuble. Sur le Pool Store, on renvoie vers ses propres CGV
    (lien sous le bouton d'achat et case a cocher du paiement)."""

    @http.route()
    def terms_conditions(self, **kwargs):
        if request.website and request.website.id == SITE_POOL_STORE:
            url = request.env['ir.http']._url_for(CGV_POOL_STORE)
            return request.redirect(url, code=301)
        return super().terms_conditions(**kwargs)
