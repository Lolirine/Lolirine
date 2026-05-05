# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_available_box_domain(self):
        """Retourne le domaine pour filtrer les box disponibles"""
        # Trouver tous les produits déjà loués dans des abonnements actifs
        rented_products = self.env['product.template'].search([
            ('is_storage_box', '=', True),
            ('storage_status', '=', 'rented')
        ])

        return [
            '|',
            ('is_storage_box', '=', False),  # Tous les produits non-box
            '&',
            ('is_storage_box', '=', True),   # OU les box
            ('id', 'not in', rented_products.ids)  # qui ne sont pas loués
        ]


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_is_storage_box = fields.Boolean(
        related='product_template_id.is_storage_box',
        string='Est un box',
        store=True
    )

    @api.constrains('product_id', 'order_id')
    def _check_box_availability(self):
        """Vérifie que le box n'est pas déjà loué dans un autre abonnement actif"""
        for line in self:
            if not line.product_template_id or not line.order_id:
                continue

            product = line.product_template_id
            order = line.order_id

            # Vérifier seulement pour les box de stockage dans les abonnements
            if not product.is_storage_box:
                continue

            if not order.is_subscription:
                continue

            # Chercher si ce produit est déjà dans un autre abonnement actif
            existing_lines = self.env['sale.order.line'].search([
                ('product_template_id', '=', product.id),
                ('order_id', '!=', order.id),
                ('order_id.is_subscription', '=', True),
                ('order_id.state', '=', 'sale'),
                ('order_id.subscription_state', 'in', ['3_progress', '4_paused']),
            ], limit=1)

            if existing_lines:
                existing_order = existing_lines.order_id
                raise ValidationError(_(
                    "Le box '%(box_name)s' est déjà attribué à l'abonnement '%(subscription_name)s' (%(partner_name)s).\n\n"
                    "Veuillez d'abord clôturer cet abonnement ou choisir un autre box.",
                    box_name=product.name,
                    subscription_name=existing_order.name,
                    partner_name=existing_order.partner_id.name
                ))

    @api.onchange('product_id')
    def _onchange_product_check_box_availability(self):
        """Avertit si le produit sélectionné est déjà loué"""
        if not self.product_id:
            return

        product_tmpl = self.product_template_id
        if not product_tmpl or not product_tmpl.is_storage_box:
            return

        # Vérifier si déjà dans un abonnement actif
        if product_tmpl.storage_status == 'rented' and product_tmpl.current_subscription_id:
            # Vérifier si c'est pour le même abonnement (modification)
            if self.order_id and product_tmpl.current_subscription_id.id != self.order_id.id:
                return {
                    'warning': {
                        'title': _("Box déjà loué"),
                        'message': _(
                            "Attention : Le box '%(box_name)s' est actuellement loué par %(tenant_name)s "
                            "dans l'abonnement %(subscription_name)s.\n\n"
                            "Vous ne pourrez pas confirmer cette commande tant que "
                            "l'autre abonnement est actif.",
                            box_name=self.product_id.name,
                            tenant_name=product_tmpl.current_tenant_id.name or 'N/A',
                            subscription_name=product_tmpl.current_subscription_id.name or 'N/A'
                        )
                    }
                }

        # Vérifier aussi via recherche directe dans les lignes d'abonnement
        existing_lines = self.env['sale.order.line'].search([
            ('product_template_id', '=', product_tmpl.id),
            ('order_id.is_subscription', '=', True),
            ('order_id.state', '=', 'sale'),
            ('order_id.subscription_state', 'in', ['3_progress', '4_paused']),
        ], limit=1)

        if existing_lines:
            existing_order = existing_lines.order_id
            # Vérifier que ce n'est pas le même abonnement
            if self.order_id and existing_order.id != self.order_id.id:
                return {
                    'warning': {
                        'title': _("Box déjà loué"),
                        'message': _(
                            "Attention : Le box '%(box_name)s' est actuellement attribué "
                            "à l'abonnement %(subscription_name)s (%(partner_name)s).\n\n"
                            "Vous ne pourrez pas confirmer cette commande tant que "
                            "l'autre abonnement est actif.",
                            box_name=self.product_id.name,
                            subscription_name=existing_order.name,
                            partner_name=existing_order.partner_id.name
                        )
                    }
                }
