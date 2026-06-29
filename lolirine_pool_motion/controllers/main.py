# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LolirineMotionCart(http.Controller):
    """Endpoint LECTURE-SEULE pour le mini-cart drawer.

    Robuste aux variantes d'API e-commerce (Odoo 17 vs 18/19) et ne renvoie
    jamais de 500 : en cas de souci, renvoie {"error": "..."} en JSON pour que
    le drawer affiche la cause réelle (et trace côté serveur).
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
