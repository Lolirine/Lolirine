import math

from odoo import _, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _verify_updated_quantity(self, order_line, product_id, new_qty, uom_id, **kwargs):
        """Arrondit la quantité demandée au multiple supérieur du colisage produit.

        Hook standard d'Odoo 19 (website_sale/models/sale_order.py), appelé aussi
        bien depuis ``_cart_add`` que depuis ``_cart_update_line_quantity``.
        Retourne ``(quantite, message)`` ; le message remonte au client.
        """
        new_qty, warning = super()._verify_updated_quantity(
            order_line, product_id, new_qty, uom_id, **kwargs
        )
        colis = self.env['product.product'].browse(product_id).product_tmpl_id.x_colisage or 1
        if colis > 1 and new_qty and new_qty > 0:
            rounded = math.ceil(new_qty / colis) * colis
            if rounded != new_qty:
                extra = _(
                    "Vendu par colis de %(colis)s : quantité ajustée à %(qty)s.",
                    colis=colis, qty=int(rounded),
                )
                warning = ("%s %s" % (warning, extra)).strip() if warning else extra
                new_qty = rounded
        return new_qty, warning
