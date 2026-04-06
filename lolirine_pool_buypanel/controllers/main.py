from datetime import date, timedelta
import re
from odoo import http
from odoo.http import request


class BuyPanelController(http.Controller):

    @http.route('/shop/buypanel/info', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def buypanel_info(self, product_id=None, **kwargs):
        if not product_id:
            return {}

        product = request.env['product.product'].sudo().browse(int(product_id))
        if not product.exists():
            return {}

        tmpl = product.product_tmpl_id

        # ── Stock ──────────────────────────────────────────
        qty = product.virtual_available
        if qty > 50:
            qty = 50

        if qty > 10:
            stock_label = 'En stock'
            stock_class = 'lp-stock-green'
        elif qty > 0:
            stock_label = f'Plus que {int(qty)} en stock'
            stock_class = 'lp-stock-orange'
        else:
            stock_label = 'Sur commande'
            stock_class = 'lp-stock-gray'

        # ── Livraison estimée ──────────────────────────────
        def add_business_days(d, n):
            count = 0
            while count < n:
                d += timedelta(days=1)
                if d.weekday() < 5:
                    count += 1
            return d

        today = date.today()
        delivery_min = add_business_days(today, 2)
        delivery_max = add_business_days(today, 4)

        JOURS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']
        MOIS  = ['jan.', 'fév.', 'mar.', 'avr.', 'mai', 'juin',
                 'juil.', 'août', 'sep.', 'oct.', 'nov.', 'déc.']

        def fmt_date(d):
            return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"

        delivery_str = f"{fmt_date(delivery_min)} — {fmt_date(delivery_max)}"

        # ── Marque ────────────────────────────────────────
        brand = ''
        for line in tmpl.attribute_line_ids:
            if 'marque' in (line.attribute_id.name or '').lower():
                vals = line.product_template_value_ids.filtered(lambda v: v.ptav_active)
                if vals:
                    brand = vals[0].name
                    break
        if not brand and tmpl.seller_ids:
            brand = tmpl.seller_ids[0].partner_id.name or ''

        # ── Garantie ──────────────────────────────────────
        warranty = ''
        for line in tmpl.attribute_line_ids:
            if 'garantie' in (line.attribute_id.name or '').lower():
                vals = line.product_template_value_ids.filtered(lambda v: v.ptav_active)
                if vals:
                    warranty = vals[0].name
                    break
        if not warranty:
            desc = (tmpl.description_sale or '') + (tmpl.description or '')
            m = re.search(r'(\d+)\s*an', desc, re.IGNORECASE)
            if m:
                warranty = f"{m.group(1)} an{'s' if int(m.group(1)) > 1 else ''}"

        # ── Livraison offerte (Odoo 19 : list_price) ──────
        try:
            price = tmpl.list_price or 0.0
        except Exception:
            price = 0.0
        free_delivery = price >= 499

        return {
            'stock_label':  stock_label,
            'stock_class':  stock_class,
            'stock_qty':    int(qty),
            'delivery':     delivery_str,
            'brand':        brand,
            'warranty':     warranty,
            'default_code': product.default_code or tmpl.default_code or '',
            'free_delivery': free_delivery,
        }
