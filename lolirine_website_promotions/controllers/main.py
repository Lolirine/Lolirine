import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsitePromotions(http.Controller):

    @http.route(['/promotions'], type='http', auth='public', website=True, sitemap=True)
    def promotions_page(self, **kwargs):
        """Render the promotions page with dynamic products."""
        products = self._get_promo_products()
        values = {
            'promo_products': products,
        }
        return request.render('lolirine_website_promotions.promotions_page', values)

    def _get_promo_products(self, limit=12):
        """
        Retrieve products currently on sale.
        A product is considered 'on promo' if it has a compare_list_price
        greater than its actual selling price.
        """
        ProductTemplate = request.env['product.template'].sudo()
        website = request.website

        # Get current pricelist
        pricelist = website.pricelist_id

        # Search published products on the current website
        domain = website.sale_product_domain()
        domain += [('website_published', '=', True)]

        all_products = ProductTemplate.search(domain, limit=200)

        promo_products = []
        for product in all_products:
            # Check if product has a compare_list_price set (crossed out price)
            if product.compare_list_price and product.compare_list_price > 0:
                current_price = product._get_combination_info(
                    combination=product.product_variant_id.product_template_attribute_value_ids,
                    product_id=product.product_variant_id.id,
                    add_qty=1,
                    pricelist=pricelist,
                ).get('price', 0)

                if product.compare_list_price > current_price and current_price > 0:
                    discount_pct = round(
                        (1 - current_price / product.compare_list_price) * 100
                    )
                    if discount_pct > 0:
                        promo_products.append({
                            'product': product,
                            'original_price': product.compare_list_price,
                            'promo_price': current_price,
                            'discount_pct': discount_pct,
                        })

            if len(promo_products) >= limit:
                break

        # Sort by highest discount first
        promo_products.sort(key=lambda p: p['discount_pct'], reverse=True)
        return promo_products
