# -*- coding: utf-8 -*-
import logging
import operator

from odoo import models

_logger = logging.getLogger(__name__)

# Pool Store : données structurées « Produit » (JSON-LD) des fiches, pour les
# fiches de marchand de Google Search Console / Merchant Center.
#
# 1. availability : website_sale_stock n'ajoute « availability » à l'offre que
#    pour les articles stockés (is_storable) ; les articles du Pool Store sont
#    en dropshipping (consommables). On complète :
#      - article avec prix  → InStock (livré depuis le stock fournisseur) ;
#      - article sans prix (sur mesure, sur devis) → MadeToOrder.
# 2. brand : marque de la fiche (pool_brand_id) → « GTIN ou marque » manquant.
# 3. shippingDetails : frais du mode « Livraison standard » du site 6 (règles
#    par tranche de montant), calculés pour l'article commandé seul.
# 4. hasMerchantReturnPolicy : rétractation 14 jours (CGV art. 7), renvoi par
#    colis, frais de renvoi à charge du client ; article sur devis / sur mesure
#    → pas de retour.
# 5. productGroupID / inProductGroupWithID : identifiant du groupe de variantes
#    (fiche à plusieurs variantes, schéma ProductGroup).
ROOT = "https://schema.org/"
SITE_POOL = 6
JOURS_RETOUR = 14
OPERATEURS = {"<": operator.lt, "<=": operator.le, ">": operator.gt,
              ">=": operator.ge, "==": operator.eq}


def _id_groupe(template):
    return "LPS-%d" % template.id


def _marque(template):
    marque = "pool_brand_id" in template._fields and template.sudo().pool_brand_id
    return {"@type": "Brand", "name": marque.name} if marque and marque.name else None


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _pool_pays_livraison(self, carrier):
        codes = [c.code for c in carrier.country_ids if c.code]
        return codes or ["BE"]

    def _pool_frais_livraison(self, website, prix):
        """Frais de la livraison standard du site pour une commande de `prix`
        (montant TVAC des articles, comme les règles du mode de livraison).
        Retourne (frais, pays) ou None si aucun mode ne s'applique."""
        # Livraison à domicile : le mode par tranches du site ; à défaut, un mode
        # à prix fixe non nul. Le « Retrait à Boninne » (fixe, 0 €) n'est pas
        # une livraison et ne doit pas être annoncé comme livraison gratuite.
        Carrier = self.env["delivery.carrier"].sudo()
        domaine = [("website_id", "=", website.id), ("is_published", "=", True)]
        carrier = (Carrier.search(domaine + [("delivery_type", "=", "base_on_rule")],
                                  order="sequence, id", limit=1)
                   or Carrier.search(domaine + [("delivery_type", "=", "fixed"), ("fixed_price", ">", 0)],
                                     order="sequence, id", limit=1))
        if not carrier:
            return None
        if carrier.delivery_type == "fixed":
            frais_ht = carrier.fixed_price
        else:
            frais_ht = None
            for regle in carrier.price_rule_ids.sorted("sequence"):
                test = OPERATEURS.get(regle.operator)
                if regle.variable == "price" and test and test(prix, regle.max_value):
                    frais_ht = regle.list_base_price
                    break
            if frais_ht is None:
                return None
        if carrier.free_over and prix >= carrier.amount:
            frais_ht = 0.0
        frais = frais_ht
        taxes = carrier.product_id.taxes_id._filter_taxes_by_company(website.company_id)
        if frais and taxes and website.show_line_subtotals_tax_selection == "tax_included":
            frais = taxes.compute_all(frais_ht, currency=website.currency_id)["total_included"]
        return round(frais, 2), self._pool_pays_livraison(carrier)

    def _to_markup_data(self, website):
        markup_data = super()._to_markup_data(website)
        if website.id != SITE_POOL:
            return markup_data
        template = self.product_tmpl_id
        offre = markup_data.get("offers")

        marque = _marque(template)
        if marque:
            markup_data.setdefault("brand", marque)
        if template.product_variant_count > 1:
            markup_data["inProductGroupWithID"] = _id_groupe(template)

        if not isinstance(offre, dict):
            return markup_data
        prix = offre.get("price") or 0.0
        if not offre.get("availability"):
            offre["availability"] = ROOT + ("InStock" if prix else "MadeToOrder")
        offre.setdefault("itemCondition", ROOT + "NewCondition")
        devise = offre.get("priceCurrency") or website.currency_id.name

        try:
            livraison = prix and self._pool_frais_livraison(website, prix)
        except Exception:  # jamais bloquer l'affichage de la fiche
            _logger.exception("Pool Store : frais de livraison JSON-LD non calculés")
            livraison = None
        if livraison:
            frais, pays = livraison
            offre["shippingDetails"] = {
                "@type": "OfferShippingDetails",
                "shippingRate": {"@type": "MonetaryAmount", "value": frais, "currency": devise},
                "shippingDestination": [{"@type": "DefinedRegion", "addressCountry": p} for p in pays],
            }
            pays_retour = pays
        else:
            pays_retour = ["BE"]

        if prix:
            offre["hasMerchantReturnPolicy"] = {
                "@type": "MerchantReturnPolicy",
                "applicableCountry": pays_retour,
                "returnPolicyCategory": ROOT + "MerchantReturnFiniteReturnWindow",
                "merchantReturnDays": JOURS_RETOUR,
                "returnMethod": ROOT + "ReturnByMail",
                "returnFees": ROOT + "ReturnFeesCustomerResponsibility",
            }
        else:
            offre["hasMerchantReturnPolicy"] = {
                "@type": "MerchantReturnPolicy",
                "applicableCountry": pays_retour,
                "returnPolicyCategory": ROOT + "MerchantReturnNotPermitted",
            }
        return markup_data


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _to_markup_data(self, website):
        markup_data = super()._to_markup_data(website)
        if website.id == SITE_POOL and markup_data.get("@type") == "ProductGroup":
            markup_data["productGroupID"] = _id_groupe(self)
            marque = _marque(self)
            if marque:
                markup_data.setdefault("brand", marque)
        return markup_data
