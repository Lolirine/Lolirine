from datetime import date, timedelta
from odoo import http
from odoo.http import request
import json


class BuyPanelController(http.Controller):

    @http.route('/shop/buypanel/info', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def buypanel_info(self, product_id=None, **kwargs):
        """Retourne les infos dynamiques pour le panneau d'achat."""
        if not product_id:
            return {}

        product = request.env['product.product'].sudo().browse(int(product_id))
        if not product.exists():
            return {}

        # ── Stock ──────────────────────────────────────────
        qty = product.virtual_available
        if qty > 50:
            qty = 50  # Afficher max 50

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
        today = date.today()
        # Sauter le week-end
        def add_business_days(d, n):
            count = 0
            while count < n:
                d += timedelta(days=1)
                if d.weekday() < 5:
                    count += 1
            return d

        delivery_min = add_business_days(today, 2)
        delivery_max = add_business_days(today, 4)

        # Noms des jours en français
        JOURS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']
        MOIS  = ['jan.', 'fév.', 'mar.', 'avr.', 'mai', 'juin',
                 'juil.', 'août', 'sep.', 'oct.', 'nov.', 'déc.']

        def fmt_date(d):
            return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"

        delivery_str = f"{fmt_date(delivery_min)} — {fmt_date(delivery_max)}"

        # ── Infos produit ──────────────────────────────────
        tmpl = product.product_tmpl_id
        brand = ''
        warranty = ''
        for line in tmpl.attribute_line_ids:
            if 'marque' in line.attribute_id.name.lower():
                vals = line.product_template_value_ids.filtered(
                    lambda v: v.ptav_active
                )
                if vals:
                    brand = vals[0].name

        # Chercher la marque dans le nom du fournisseur ou le champ seller
        if not brand and tmpl.seller_ids:
            brand = tmpl.seller_ids[0].partner_id.name or ''

        # Garantie depuis les attributs
        for line in tmpl.attribute_line_ids:
            if 'garantie' in line.attribute_id.name.lower():
                vals = line.product_template_value_ids.filtered(
                    lambda v: v.ptav_active
                )
                if vals:
                    warranty = vals[0].name

        # Fallback garantie depuis la description
        if not warranty:
            desc = (tmpl.description_sale or '') + (tmpl.description or '')
            import re
            m = re.search(r'(\d+)\s*an', desc, re.IGNORECASE)
            if m:
                warranty = f"{m.group(1)} an{'s' if int(m.group(1)) > 1 else ''}"

        # Livraison offerte ?
        free_delivery = tmpl.lst_price >= 499

        return {
            'stock_label': stock_label,
            'stock_class': stock_class,
            'stock_qty':   int(qty),
            'delivery':    delivery_str,
            'brand':       brand,
            'warranty':    warranty,
            'default_code': product.default_code or tmpl.default_code or '',
            'free_delivery': free_delivery,
            'weight': tmpl.weight or 0,
        }
