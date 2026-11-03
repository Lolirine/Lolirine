# -*- coding: utf-8 -*-
"""Supplément transport fournisseur ajouté à la livraison du panier.

Fluidra facture un transport (95 € HT) pour les colis lourds livrés chez le client.
Le client en supporte une part (40 % → 38 € HT) : quand le panier contient au moins
un article marqué « Supplément transport », le montant du mode de livraison est
augmenté une fois par commande, même quand la livraison est offerte (dès 499 € HT).
"""
from odoo import _, fields, models


class ProductTemplateSupplementTransport(models.Model):
    _inherit = 'product.template'

    pool_supplement_transport = fields.Boolean(
        "Supplément transport", help="Colis lourd livré par le transporteur du fournisseur : le supplément "
                                     "transport du mode de livraison est ajouté au panier qui contient cet article.")


class DeliveryCarrierSupplementTransport(models.Model):
    _inherit = 'delivery.carrier'

    pool_supplement_transport = fields.Monetary(
        "Supplément transport (HT)", currency_field='currency_id', default=0.0,
        help="Ajouté une fois par commande quand le panier contient un article marqué « Supplément transport » "
             "(part du transport fournisseur supportée par le client), même si la livraison est offerte.")
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    def rate_shipment(self, order):
        res = super().rate_shipment(order)
        if (res.get('success') and self.pool_supplement_transport and order
                and order.order_line.filtered(lambda l: not l.is_delivery
                                              and l.product_id.product_tmpl_id.pool_supplement_transport)):
            supplement = order.currency_id.round(self.pool_supplement_transport)
            res['price'] = (res.get('price') or 0.0) + supplement
            if 'carrier_price' in res:
                res['carrier_price'] = (res.get('carrier_price') or 0.0) + supplement
            note = _("Comprend un supplément transport de %s HT pour colis lourd.") % (
                ('%.2f €' % supplement).replace('.', ','))
            res['warning_message'] = ((res.get('warning_message') or '') + ' ' + note).strip()
        return res
