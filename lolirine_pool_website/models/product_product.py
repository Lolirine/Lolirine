# -*- coding: utf-8 -*-
from odoo import models

# Pool Store : données structurées « Produit » (JSON-LD) des fiches.
# website_sale_stock n'ajoute « availability » à l'offre que pour les articles
# stockés (is_storable) ; les articles du Pool Store sont en dropshipping
# (consommables) → Google Search Console : « Champ availability manquant (dans
# offers) ». On complète :
#   - article avec prix  → InStock (livré depuis le stock fournisseur) ;
#   - article sans prix (sur mesure, sur devis) → MadeToOrder.
ROOT = "https://schema.org/"


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _to_markup_data(self, website):
        markup_data = super()._to_markup_data(website)
        offre = markup_data.get("offers")
        if website.id == 6 and isinstance(offre, dict) and not offre.get("availability"):
            offre["availability"] = ROOT + ("InStock" if offre.get("price") else "MadeToOrder")
            offre.setdefault("itemCondition", ROOT + "NewCondition")
        return markup_data
