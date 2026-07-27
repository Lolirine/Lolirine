# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_available_box_domain(self):
        """Retourne le domaine pour filtrer les box disponibles"""
        rented_products = self.env['product.template'].search([
            ('is_storage_box', '=', True),
            ('storage_status', '=', 'rented')
        ])

        return [
            '|',
            ('is_storage_box', '=', False),
            '&',
            ('is_storage_box', '=', True),
            ('id', 'not in', rented_products.ids)
        ]

    def action_confirm(self):
        """Bloque la confirmation (pas la creation du devis) si un box
        est deja attribue a un autre abonnement actif."""
        for order in self:
            if not order.is_subscription:
                continue
            for line in order.order_line:
                conflict = line._get_box_conflict_line()
                if conflict:
                    existing_order = conflict.order_id
                    raise ValidationError(_(
                        "Impossible de confirmer : le box '%(box_name)s' est deja "
                        "attribue a l'abonnement '%(subscription_name)s' "
                        "(%(partner_name)s).\n\n"
                        "Cloturez d'abord cet abonnement ou retirez ce box du devis.",
                        box_name=line.product_template_id.name,
                        subscription_name=existing_order.name,
                        partner_name=existing_order.partner_id.name
                    ))
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_is_storage_box = fields.Boolean(
        related='product_template_id.is_storage_box',
        string='Est un box',
        store=True
    )

    def _get_box_conflict_line(self):
        """Retourne la ligne d'un AUTRE abonnement actif (en cours ou en pause)
        qui contient deja ce box, ou un recordset vide."""
        self.ensure_one()
        product = self.product_template_id
        if not product or not product.is_storage_box:
            return self.env['sale.order.line']
        return self.env['sale.order.line'].search([
            ('product_template_id', '=', product.id),
            ('order_id', '!=', self.order_id.id),
            ('order_id.is_subscription', '=', True),
            ('order_id.state', '=', 'sale'),
            ('order_id.subscription_state', 'in', ['3_progress', '4_paused']),
        ], limit=1)

    @api.constrains('product_id', 'order_id')
    def _check_box_availability(self):
        """Verifie la disponibilite du box UNIQUEMENT sur les commandes deja
        confirmees (ajout d'une ligne a un abonnement en cours).
        Les devis en brouillon ou envoyes sont libres : on peut chiffrer un
        box loue, le controle se fait a la confirmation (action_confirm)."""
        for line in self:
            if not line.product_template_id or not line.order_id:
                continue
            if line.order_id.state != 'sale':
                continue
            if not line.order_id.is_subscription:
                continue

            conflict = line._get_box_conflict_line()
            if conflict:
                existing_order = conflict.order_id
                raise ValidationError(_(
                    "Le box '%(box_name)s' est deja attribue a l'abonnement "
                    "'%(subscription_name)s' (%(partner_name)s).\n\n"
                    "Veuillez d'abord cloturer cet abonnement ou choisir un autre box.",
                    box_name=line.product_template_id.name,
                    subscription_name=existing_order.name,
                    partner_name=existing_order.partner_id.name
                ))

    @api.onchange('product_id')
    def _onchange_product_check_box_availability(self):
        """Avertit (sans bloquer) si le produit selectionne est deja loue"""
        if not self.product_id:
            return

        product_tmpl = self.product_template_id
        if not product_tmpl or not product_tmpl.is_storage_box:
            return

        conflict = self.env['sale.order.line'].search([
            ('product_template_id', '=', product_tmpl.id),
            ('order_id.is_subscription', '=', True),
            ('order_id.state', '=', 'sale'),
            ('order_id.subscription_state', 'in', ['3_progress', '4_paused']),
        ], limit=1)

        if conflict and (not self.order_id or conflict.order_id.id != self.order_id.id):
            existing_order = conflict.order_id
            return {
                'warning': {
                    'title': _("Box deja loue"),
                    'message': _(
                        "Attention : le box '%(box_name)s' est actuellement attribue "
                        "a l'abonnement %(subscription_name)s (%(partner_name)s).\n\n"
                        "Vous pouvez etablir ce devis, mais vous ne pourrez pas le "
                        "confirmer tant que l'autre abonnement est actif.",
                        box_name=self.product_id.name,
                        subscription_name=existing_order.name,
                        partner_name=existing_order.partner_id.name
                    )
                }
            }
