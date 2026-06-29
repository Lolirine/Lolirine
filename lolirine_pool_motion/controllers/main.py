# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class LolirineMotionCart(http.Controller):
    """Endpoint LECTURE-SEULE pour le mini-cart drawer (vague 2).

    Ne modifie jamais le panier : lit le panier courant via l'ORM et renvoie
    du JSON. Aucune dépendance au HTML de /shop/cart (robuste entre versions).
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
        order = request.website.sale_get_order()
        currency = order.currency_id if order else request.website.currency_id
        payload = {
            "count": 0,
            "currency": (currency.name if currency else "EUR") or "EUR",
            "amount_total": 0.0,
            "lines": [],
        }
        if order:
            lines = []
            for line in order.website_order_line:
                product = line.product_id
                tmpl = product.product_tmpl_id
                lines.append(
                    {
                        "id": line.id,
                        "name": product.display_name or (line.name or ""),
                        "qty": line.product_uom_qty,
                        "price_total": line.price_total,
                        "image_url": "/web/image/product.product/%s/image_128"
                        % product.id,
                        "url": (tmpl.website_url if tmpl else "/shop") or "/shop",
                    }
                )
            payload.update(
                {
                    "count": int(order.cart_quantity or 0),
                    "amount_total": order.amount_total,
                    "lines": lines,
                }
            )
        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json")],
        )
