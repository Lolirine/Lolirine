# -*- coding: utf-8 -*-
"""Navigation enrichie du Pool Store (bandeau, tiroir des rayons, listes,
fiche produit, panier, fonctions professionnelles).

Tous les blocs sont rendus cote navigateur par static/src/js/pool_nav.js ;
ce controleur ne fournit que des donnees JSON. Aucune route ne renvoie
d'erreur 500 : en cas de souci, la reponse contient {"error": "..."} et le
bloc concerne reste simplement masque sur le site.
"""
import json
import logging

from markupsafe import Markup

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

SITE_POOL_STORE = 6


def _json(payload):
    return request.make_response(
        json.dumps(payload),
        headers=[("Content-Type", "application/json"), ("Cache-Control", "no-store")],
    )


class LolirineNav(http.Controller):

    # ------------------------------------------------------------------
    # Outils
    # ------------------------------------------------------------------
    def _pool_store(self):
        return request.website and request.website.id == SITE_POOL_STORE

    def _slug(self, record):
        try:
            return request.env["ir.http"]._slug(record)
        except Exception:  # noqa: BLE001
            return str(record.id)

    def _prices(self, product, qty=1.0):
        """Prix unitaire (HTVA, TVAC) d'une variante, liste de prix et
        position fiscale du visiteur comprises."""
        website = request.website
        pricelist = getattr(request, "pricelist", None)
        if pricelist:
            price = pricelist._get_product_price(product, qty)
        else:
            price = product.lst_price
        taxes = product.sudo().taxes_id.filtered(
            lambda t: t.company_id == website.company_id
        )
        fpos = getattr(request, "fiscal_position", None)
        if fpos:
            taxes = fpos.sudo().map_tax(taxes)
        if not taxes:
            return price, price
        res = taxes.sudo().compute_all(
            price, currency=website.currency_id, quantity=1.0, product=product
        )
        return res["total_excluded"], res["total_included"]

    def _visible(self, templates):
        """Fiches publiees et vendables sur le Pool Store."""
        return templates.filtered(
            lambda t: t.is_published
            and t.sale_ok
            and (not t.website_id or t.website_id.id == SITE_POOL_STORE)
        )

    def _card(self, product):
        tmpl = product.product_tmpl_id
        ht, ttc = self._prices(product)
        return {
            "product_id": product.id,
            "tmpl_id": tmpl.id,
            "name": tmpl.name or "",
            "url": tmpl.website_url or "/shop",
            "image": "/web/image/product.product/%s/image_256" % product.id,
            "ht": ht,
            "ttc": ttc,
            "simple": len(tmpl.product_variant_ids) == 1
            and not tmpl.attribute_line_ids.filtered(
                lambda l: l.attribute_id.create_variant == "no_variant"
                or any(v.is_custom for v in l.value_ids)
            ),
        }

    # ------------------------------------------------------------------
    # Contexte : rayons + visiteur
    # ------------------------------------------------------------------
    @http.route("/lolirine_nav/context", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_context(self, **kw):
        payload = {"categories": [], "user": {"logged": False, "name": ""}}
        if not self._pool_store():
            return _json(payload)
        try:
            Categ = request.env["product.public.category"].sudo()
            domain = [("parent_id", "=", False),
                      ("website_id", "in", (False, SITE_POOL_STORE))]
            for cat in Categ.search(domain, order="sequence, name"):
                children = cat.child_id.filtered(
                    lambda c: not c.website_id or c.website_id.id == SITE_POOL_STORE
                ).sorted(lambda c: (c.sequence, c.name or ""))
                payload["categories"].append({
                    "id": cat.id,
                    "name": cat.name or "",
                    "url": "/shop/category/%s" % self._slug(cat),
                    "children": [{
                        "id": c.id,
                        "name": c.name or "",
                        "url": "/shop/category/%s" % self._slug(c),
                    } for c in children],
                })
            user = request.env.user
            if not user._is_public():
                payload["user"] = {
                    "logged": True,
                    "name": (user.partner_id.name or "").split(" ")[0],
                }
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec contexte")
            payload["error"] = str(e)
        return _json(payload)

    # ------------------------------------------------------------------
    # Liste de produits : nombre de resultats
    # ------------------------------------------------------------------
    @http.route("/lolirine_nav/count", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_count(self, category=None, search="", min_price=0.0, max_price=0.0,
                  tags="", **post):
        payload = {"count": None}
        if not self._pool_store():
            return _json(payload)
        try:
            from odoo.addons.website_sale.controllers.main import WebsiteSale
            shop = WebsiteSale()
            website = request.website
            categ = request.env["product.public.category"]
            if category:
                categ = categ.browse(int(category)).exists()
            values = request.httprequest.args.getlist("attribute_values")
            attribute_value_dict = shop._get_attribute_value_dict(values)
            try:
                min_price = float(min_price or 0)
                max_price = float(max_price or 0)
            except ValueError:
                min_price = max_price = 0.0
            if tags and website.is_view_active("website_sale.filter_products_tags"):
                post["tags"] = {
                    request.env["ir.http"]._unslug(tag)[1] for tag in tags.split(",")
                }
            options = shop._get_search_options(
                category=categ or None,
                attribute_value_dict=attribute_value_dict,
                min_price=min_price,
                max_price=max_price,
                conversion_rate=1,
                display_currency=website.currency_id,
                **post
            )
            _term, count, _products = shop._shop_lookup_products(
                options, post, search or "", website
            )
            payload["count"] = int(count or 0)
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec comptage")
            payload["error"] = str(e)
        return _json(payload)

    # ------------------------------------------------------------------
    # Liste de produits : prix HTVA/TVAC des tuiles affichees
    # ------------------------------------------------------------------
    @http.route("/lolirine_nav/prices", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_prices(self, ids="", **kw):
        payload = {"prices": {}}
        if not self._pool_store():
            return _json(payload)
        try:
            wanted = [int(x) for x in ids.split(",") if x.strip().isdigit()][:80]
            products = request.env["product.product"].sudo().browse(wanted).exists()
            for product in products:
                if not self._visible(product.product_tmpl_id):
                    continue
                card = self._card(product)
                payload["prices"][str(product.id)] = {
                    "ht": card["ht"], "ttc": card["ttc"], "simple": card["simple"],
                }
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec prix des tuiles")
            payload["error"] = str(e)
        return _json(payload)

    # ------------------------------------------------------------------
    # Fiche produit : achat groupe, comparatif, prix degressifs
    # ------------------------------------------------------------------
    @http.route("/lolirine_nav/product/<int:tmpl_id>", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_product(self, tmpl_id, product_id=None, **kw):
        payload = {"self": None, "bundle": [], "compare": None, "tiers": []}
        if not self._pool_store():
            return _json(payload)
        try:
            tmpl = request.env["product.template"].sudo().browse(tmpl_id).exists()
            if not tmpl or not self._visible(tmpl):
                return _json({"error": "not_found"})
            product = tmpl.product_variant_id
            if product_id and str(product_id).isdigit():
                chosen = tmpl.product_variant_ids.filtered(
                    lambda p: p.id == int(product_id)
                )
                product = chosen[:1] or product
            if not product:
                return _json(payload)

            me = self._card(product)
            payload["self"] = me

            # --- Frequemment achetes ensemble (accessoires = variantes) ---
            for acc in tmpl.accessory_product_ids:
                if len(payload["bundle"]) >= 3:
                    break
                if acc.product_tmpl_id == tmpl or not self._visible(acc.product_tmpl_id):
                    continue
                card = self._card(acc)
                if card["ttc"] > 0:
                    payload["bundle"].append(card)

            # --- Comparatif avec les produits alternatifs ---
            others = self._visible(tmpl.alternative_product_ids)[:3]
            if others:
                columns = [tmpl] + list(others)
                items, specs = [], []
                for t in columns:
                    variant = product if t == tmpl else t.product_variant_id
                    card = self._card(variant)
                    card["current"] = t == tmpl
                    items.append(card)
                    line_vals = {}
                    for line in t.attribute_line_ids:
                        names = line.value_ids.mapped("name")
                        # Caracteristiques seulement : un attribut a nombreuses
                        # valeurs est un choix de variante, pas une donnee a comparer.
                        if names and len(names) <= 3:
                            line_vals[line.attribute_id.name] = ", ".join(names)
                    specs.append(line_vals)
                labels = []
                for vals in specs:
                    for label in vals:
                        if label not in labels:
                            labels.append(label)
                rows = []
                for label in labels:
                    cells = [vals.get(label, "") for vals in specs]
                    if sum(1 for c in cells if c) >= 2:
                        rows.append({"label": label, "cells": cells})
                payload["compare"] = {"items": items, "rows": rows[:8]}

            # --- Prix degressifs (regles de la liste de prix du visiteur) ---
            pricelist = getattr(request, "pricelist", None)
            if pricelist and me["ht"] > 0:
                quantities = sorted({
                    int(q) for q in pricelist.sudo().item_ids.mapped("min_quantity")
                    if q and q > 1
                })[:6]
                for qty in quantities:
                    ht, ttc = self._prices(product, float(qty))
                    if ht < me["ht"] - 0.005:
                        payload["tiers"].append({
                            "qty": qty, "ht": ht, "ttc": ttc,
                            "pct": int(round((1 - ht / me["ht"]) * 100)),
                        })
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec donnees fiche produit")
            payload["error"] = str(e)
        return _json(payload)

    # ------------------------------------------------------------------
    # Tunnel de commande et confirmation
    # ------------------------------------------------------------------
    def _order_lines(self, order):
        return order.order_line.filtered(
            lambda l: not l.display_type and l.product_id
            and not getattr(l, "is_delivery", False)
        )

    def _order_promise(self, order):
        """Promesse de livraison d'une commande : le delai du produit le plus lent."""
        if "lolirine.livraison" not in request.env:
            return {}
        Liv = request.env["lolirine.livraison"].sudo()
        delais = [
            Liv.delai_fournisseur(line.product_id.product_tmpl_id)
            for line in self._order_lines(order)
        ]
        if not delais:
            return {}
        promesse = Liv.promesse(max(delais))
        return {"text": promesse["texte"], "countdown": promesse["compte_a_rebours"]}

    @http.route("/lolirine_nav/checkout", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_checkout(self, **kw):
        payload = {"delivery": {}}
        if not self._pool_store():
            return _json(payload)
        try:
            order = getattr(request, "cart", None)
            if order and order.order_line:
                payload["delivery"] = self._order_promise(order.sudo())
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec donnees tunnel de commande")
            payload["error"] = str(e)
        return _json(payload)

    @http.route("/lolirine_nav/confirmation", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_confirmation(self, **kw):
        """Donnees de la page de confirmation : uniquement la derniere commande
        de la session du visiteur (ou son panier en cours)."""
        payload = {"order": None, "delivery": {}, "complements": []}
        if not self._pool_store():
            return _json(payload)
        try:
            order = request.env["sale.order"]
            last_id = request.session.get("sale_last_order_id")
            if last_id:
                order = order.sudo().browse(int(last_id)).exists()
            if not order:
                cart = getattr(request, "cart", None)
                order = cart.sudo() if cart else order
            if not order:
                return _json(payload)
            payload["order"] = {
                "ref": order.name or "",
                "email": order.partner_id.email or "",
                "portal_url": order.get_portal_url(),
            }
            payload["delivery"] = self._order_promise(order)
            bought = self._order_lines(order).mapped("product_id.product_tmpl_id")
            for acc in bought.mapped("accessory_product_ids"):
                if len(payload["complements"]) >= 4:
                    break
                tmpl = acc.product_tmpl_id
                if tmpl in bought or not self._visible(tmpl):
                    continue
                card = self._card(acc)
                if card["ttc"] > 0:
                    payload["complements"].append(card)
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec donnees confirmation")
            payload["error"] = str(e)
        return _json(payload)

    # ------------------------------------------------------------------
    # Espace client : tableau de bord (dernieres commandes du client connecte)
    # ------------------------------------------------------------------
    @http.route("/lolirine_nav/account", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_account(self, **kw):
        payload = {"logged": False, "name": "", "orders": []}
        if not self._pool_store():
            return _json(payload)
        try:
            user = request.env.user
            if user._is_public():
                return _json(payload)
            partner = user.partner_id
            payload.update({"logged": True, "name": (partner.name or "").split(" ")[0]})
            # Memes commandes que la liste « Mes commandes » du portail, site 6 seulement.
            orders = request.env["sale.order"].sudo().search([
                ("partner_id", "child_of", [partner.commercial_partner_id.id]),
                ("state", "=", "sale"),
                ("website_id", "=", SITE_POOL_STORE),
            ], order="date_order desc, id desc", limit=2)
            for order in orders:
                lines = self._order_lines(order)
                invoice = order.invoice_ids.filtered(
                    lambda m: m.state == "posted" and m.move_type == "out_invoice"
                )[:1]
                payload["orders"].append({
                    "id": order.id,
                    "ref": order.name or "",
                    "date": order.date_order.strftime("%d/%m/%Y") if order.date_order else "",
                    "total": order.amount_total,
                    "count": int(sum(lines.mapped("product_uom_qty"))),
                    "url": order.get_portal_url(),
                    "invoice_url": invoice.get_portal_url() if invoice else "",
                    "return_url": "/my/orders/%s/retour" % order.id,
                    "images": [
                        "/web/image/product.product/%s/image_128" % line.product_id.id
                        for line in lines[:4]
                    ],
                })
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec tableau de bord client")
            payload["error"] = str(e)
        return _json(payload)

    # ------------------------------------------------------------------
    # Guides : produits du rayon lie au guide
    # ------------------------------------------------------------------
    @http.route("/lolirine_nav/guide", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def nav_guide(self, category=None, **kw):
        payload = {"category": None, "products": []}
        if not self._pool_store() or not str(category or "").isdigit():
            return _json(payload)
        try:
            categ = request.env["product.public.category"].sudo().browse(int(category)).exists()
            if not categ:
                return _json(payload)
            payload["category"] = {
                "name": categ.name or "",
                "url": "/shop/category/%s" % self._slug(categ),
            }
            templates = request.env["product.template"].sudo().search([
                ("public_categ_ids", "child_of", categ.id),
                ("is_published", "=", True),
                ("sale_ok", "=", True),
                ("website_id", "in", (False, SITE_POOL_STORE)),
            ], order="website_sequence, id", limit=12)
            for tmpl in templates:
                if len(payload["products"]) >= 4:
                    break
                product = tmpl.product_variant_id
                if not product:
                    continue
                card = self._card(product)
                if card["ttc"] > 0:
                    payload["products"].append(card)
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec produits du guide")
            payload["error"] = str(e)
        return _json(payload)

    # ------------------------------------------------------------------
    # Panier : demande de devis
    # ------------------------------------------------------------------
    @http.route("/lolirine_nav/quote", type="jsonrpc", auth="public",
                website=True, methods=["POST"], csrf=False)
    def nav_quote(self, name="", email="", phone="", company="", vat="", note="", **kw):
        if not self._pool_store():
            return {"error": "site"}
        try:
            order = getattr(request, "cart", None)
            if not order or not order.order_line:
                return {"error": "empty"}
            name, email = (name or "").strip()[:120], (email or "").strip()[:120]
            if not name or "@" not in email:
                return {"error": "contact"}
            done = request.session.get("lp_quote_sent") or []
            if order.id in done:
                return {"ok": True, "ref": order.name, "already": True}

            order = order.sudo()
            rows = Markup("")
            for line in order.order_line.filtered(lambda l: not l.display_type):
                rows += Markup("<li>%s × %s — %s HTVA</li>") % (
                    ("%g" % line.product_uom_qty),
                    line.product_id.display_name or line.name or "",
                    ("%.2f €" % line.price_subtotal),
                )
            body = Markup(
                "<p><strong>Demande de devis depuis le panier du Pool Store</strong></p>"
                "<p>Nom : %s<br/>E-mail : %s<br/>Téléphone : %s<br/>"
                "Société : %s<br/>TVA : %s</p><p>Message : %s</p>"
                "<ul>%s</ul><p>Total HTVA : %s — TVAC : %s</p>"
            ) % (
                name, email, (phone or "").strip()[:40] or "—",
                (company or "").strip()[:120] or "—", (vat or "").strip()[:40] or "—",
                (note or "").strip()[:1500] or "—", rows,
                "%.2f €" % order.amount_untaxed, "%.2f €" % order.amount_total,
            )
            order.message_post(body=body, subtype_xmlid="mail.mt_note")
            dest = order.company_id.email or request.website.company_id.email
            if dest:
                request.env["mail.mail"].sudo().create({
                    "subject": "Demande de devis Pool Store — %s (%s)" % (order.name, name),
                    "body_html": body,
                    "email_to": dest,
                    "reply_to": email,
                    "auto_delete": True,
                })
            request.session["lp_quote_sent"] = done + [order.id]
            return {"ok": True, "ref": order.name}
        except Exception as e:  # noqa: BLE001
            _logger.exception("lolirine_nav: echec demande de devis")
            return {"error": str(e)}
