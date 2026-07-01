# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class LolirineMotionCart(http.Controller):
    """Endpoints LECTURE-SEULE pour le mini-cart drawer et le quickview.

    Robuste aux variantes d'API e-commerce (Odoo 17 vs 18/19) et ne renvoie
    jamais de 500 : en cas de souci, renvoie {"error": "..."} en JSON pour que
    le front affiche la cause réelle (et trace côté serveur).
    """

    @http.route(
        "/lolirine_motion/cart",
        type="http",
        auth="public",
        website=True,
        methods=["GET"],
        sitemap=False,
    )
    def motion_cart(self, **kw):
        payload = {"count": 0, "currency": "EUR", "amount_total": 0.0, "lines": []}
        try:
            order = self._get_cart()
            currency = (order.currency_id if order else None) or request.website.currency_id
            payload["currency"] = (currency.name if currency else "EUR") or "EUR"

            if order:
                # Odoo 17 : website_order_line ; refactor récent : fallback order_line.
                line_field = (
                    "website_order_line"
                    if "website_order_line" in order._fields
                    else "order_line"
                )
                lines = []
                for line in order[line_field]:
                    if getattr(line, "display_type", False):
                        continue  # lignes de section / note
                    product = line.product_id
                    if not product:
                        continue
                    tmpl = product.product_tmpl_id
                    lines.append(
                        {
                            "id": line.id,
                            "product_id": product.id,
                            "name": product.display_name or (line.name or ""),
                            "qty": line.product_uom_qty,
                            "price_total": line.price_total,
                            "image_url": "/web/image/product.product/%s/image_128"
                            % product.id,
                            "url": (tmpl.website_url if tmpl else "/shop") or "/shop",
                        }
                    )
                cart_qty = (
                    order.cart_quantity
                    if "cart_quantity" in order._fields
                    else sum(l["qty"] for l in lines)
                )
                payload.update(
                    {
                        "count": int(cart_qty or 0),
                        "amount_total": order.amount_total,
                        "lines": lines,
                    }
                )
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_pool_motion: échec endpoint mini-cart")
            payload["error"] = str(e)

        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json")],
        )

    def _get_cart(self):
        """Récupère le panier courant sans le créer, selon la version d'Odoo."""
        website = request.website
        if hasattr(website, "sale_get_order"):
            try:
                return website.sale_get_order()
            except Exception:  # noqa: BLE001
                _logger.exception("sale_get_order a échoué, tentative request.cart")
        return getattr(request, "cart", None) or None

    # ------------------------------------------------------------------
    # Quickview produit (vague 2, option 2 : variantes) — lecture seule.
    # ------------------------------------------------------------------
    @http.route(
        "/lolirine_motion/product/<int:tmpl_id>",
        type="http",
        auth="public",
        website=True,
        methods=["GET"],
        sitemap=False,
    )
    def motion_product(self, tmpl_id, **kw):
        payload = {}
        try:
            tmpl = request.env["product.template"].sudo().browse(tmpl_id)
            if not tmpl.exists() or not tmpl.is_published:
                return request.make_response(
                    json.dumps({"error": "not_found"}),
                    headers=[("Content-Type", "application/json")],
                )

            # Prix via la logique website (pricelist/taxes) avec repli.
            price = list_price = tmpl.list_price
            try:
                combo = tmpl._get_combination_info()
                price = combo.get("price", price)
                list_price = combo.get("list_price", list_price)
            except Exception:  # noqa: BLE001
                _logger.exception("quickview: _get_combination_info indispo, repli list_price")

            currency = request.website.currency_id
            variants = tmpl.product_variant_ids
            default_variant = tmpl.product_variant_id

            payload = {
                "id": tmpl.id,
                "name": tmpl.display_name or tmpl.name or "",
                "price": price,
                "list_price": list_price,
                "has_discount": bool(list_price and price and list_price > price),
                "currency": (currency.name if currency else "EUR") or "EUR",
                "image_url": "/web/image/product.template/%s/image_512" % tmpl.id,
                "url": tmpl.website_url or "/shop",
                "description": self._short_specs(tmpl),
                "has_variants": len(variants) > 1 or bool(tmpl.attribute_line_ids),
                "variant_id": default_variant.id if default_variant else False,
                "attributes": self._attributes(tmpl),
                "default_combination": (
                    default_variant.product_template_attribute_value_ids.ids
                    if default_variant
                    else []
                ),
            }
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_pool_motion: échec endpoint quickview")
            payload = {"error": str(e)}

        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json")],
        )
    # ------------------------------------------------------------------
    # Ajout au panier — délègue à l'API interne d'Odoo (stable).
    # ------------------------------------------------------------------
    @http.route(
        "/lolirine_motion/cart/add",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=False,
    )
    @http.route(
        "/lolirine_motion/cart/add",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=False,
    )
    def motion_cart_add(self, product_id, quantity=1, **kw):
        try:
            pid = int(product_id)
            qty = int(quantity or 1)
            order = self._get_cart_force()
            if not order:
                return {"error": "panier introuvable (aucune API compatible)"}

            if hasattr(order, "_cart_update"):
                order._cart_update(product_id=pid, add_qty=qty)
            elif hasattr(order, "_cart_add"):
                order._cart_add(product_id=pid, quantity=qty)
            else:
                return {"error": "API panier (_cart_update) introuvable"}

            return {
                "count": int(order.cart_quantity or 0),
                "amount_total": order.amount_total,
            }
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_pool_motion: échec ajout panier")
            return {"error": str(e)}

    def _get_cart_force(self):
        """Récupère (ou crée) le panier courant, tolérant aux API d'Odoo 17/18/19."""
        website = request.website
        # Odoo <= 18
        if hasattr(website, "sale_get_order"):
            try:
                return website.sale_get_order(force_create=True)
            except Exception:  # noqa: BLE001
                _logger.exception("sale_get_order(force_create) indispo")
        # Odoo 19 : helper porté sur request
        for attr in ("sale_get_order", "_get_and_cache_current_order"):
            fn = getattr(request, attr, None)
            if callable(fn):
                try:
                    try:
                        return fn(force_create=True)
                    except TypeError:
                        return fn()
                except Exception:  # noqa: BLE001
                    _logger.exception("request.%s indispo", attr)
        # Dernier repli : attribut cart
        return getattr(request, "cart", None) or None
    def _short_specs(self, tmpl):
        """Extrait court : caractéristiques techniques en priorité, puis replis.
        Convertit le HTML en texte, garde les lignes non vides, limite la taille.
        """
        for field in ("x_specs_techniques", "description_sale", "website_description"):
            if field not in tmpl._fields:
                continue
            raw = tmpl[field]
            if not raw:
                continue
            txt = html2plaintext(raw or "")
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            if not lines:
                continue
            lines = lines[:6]  # max 6 lignes
            txt = "\n".join(lines)
            if len(txt) > 320:
                txt = txt[:320].rsplit(" ", 1)[0] + "…"
            elif len(lines) == 6:
                txt += "…"
            return txt
        return ""

    def _attributes(self, tmpl):
        """Attributs réellement variables (>1 valeur), pour le sélecteur quickview.
        Renvoie les ids de product.template.attribute.value (ptav) à passer ensuite
        à la route officielle /website_sale/get_combination_info.
        """
        out = []
        for line in tmpl.attribute_line_ids:
            values = []
            for ptav in line.product_template_value_ids:
                if hasattr(ptav, "ptav_active") and not ptav.ptav_active:
                    continue
                pav = ptav.product_attribute_value_id
                values.append(
                    {
                        "id": ptav.id,
                        "name": ptav.name,
                        "color": (pav.html_color or "") if pav else "",
                    }
                )
            if len(values) > 1:
                out.append(
                    {
                        "name": line.attribute_id.name,
                        "display_type": line.attribute_id.display_type or "radio",
                        "values": values,
                    }
                )
        return out
