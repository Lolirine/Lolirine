"""Filtres de la boutique limités aux valeurs réellement présentes.

Odoo n'affiche dans le panneau de filtres que les attributs utilisés par les
produits de la catégorie, mais il liste TOUTES les valeurs de chaque attribut
(plus de 100 marques sur « Chlore stabilisé », des tailles de robots…). On
calcule ici, pour le Pool Store, les valeurs portées par les produits de la
recherche en cours ; les gabarits de filtres (views/shop_filters.xml) n'en
affichent pas d'autres. Une valeur déjà cochée reste toujours visible.
"""
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request

SITE_POOL_STORE = 6


class WebsiteSaleFiltresPresents(WebsiteSale):

    def _get_additional_shop_values(self, values, **kwargs):
        res = super()._get_additional_shop_values(values, **kwargs)
        if request.website.id != SITE_POOL_STORE:
            return res
        produits = values.get('search_product')
        attributs = values.get('attributes')
        if not produits or not attributs:
            return res
        Value = request.env['product.attribute.value'].sudo()
        lignes = request.env['product.template.attribute.line'].sudo().search([
            ('product_tmpl_id', 'in', produits.ids),
            ('attribute_id', 'in', attributs.ids),
        ])
        presentes = {}
        for ligne in lignes:
            presentes.setdefault(ligne.attribute_id.id, set()).update(ligne.value_ids.ids)
        cochees = Value.browse(list(values.get('attrib_set') or ()))
        res['lp_vals'] = {
            attr_id: (Value.browse(list(ids))
                      | cochees.filtered(lambda v, a=attr_id: v.attribute_id.id == a)).sorted()
            for attr_id, ids in presentes.items()
        }
        return res
