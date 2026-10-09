# -*- coding: utf-8 -*-
import re
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Pattern utilisé pour retirer la mention "X <période> JJ/MM/AAAA au JJ/MM/AAAA"
# que sale_subscription ajoute automatiquement à la description de ligne.
# Tolérant : couvre mois / semaine(s) / jour(s) / an(s) / année(s).
_RECURRING_PERIOD_RE = re.compile(
    r'\s*\n+\s*\d+\s+'
    r'(?:mois|semaine|semaines|jour|jours|an|ans|année|années)'
    r'\s+\d{2}/\d{2}/\d{4}\s+au\s+\d{2}/\d{2}/\d{4}\s*$',
    re.IGNORECASE,
)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Retire la mention de période ajoutée automatiquement par sale_subscription
        dans la description de ligne de facture. Cette mention prête à confusion
        pour les clients du garde-meuble étant donné que les conditions de paiement
        sont 'à terme échu' alors que la période affichée est celle à venir.

        Ne s'applique QUE aux lignes d'abonnement récurrentes (recurring_invoice=True),
        ce qui protège :
          - les lignes de prorata créées par le wizard de clôture
          - les lignes de frais de rappel / mise en demeure
          - toute autre ligne manuelle ou ad-hoc
        """
        vals = super()._prepare_invoice_line(**optional_values)
        if self.recurring_invoice and vals.get('name'):
            cleaned = _RECURRING_PERIOD_RE.sub('', vals['name']).rstrip()
            if cleaned != vals['name']:
                vals['name'] = cleaned
        return vals


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_box_ids = fields.Many2many(
        'storage.box',
        string="Box",
        compute='_compute_x_box_ids',
        help="Box du garde-meuble lies aux produits des lignes du contrat.",
    )
    x_box_names = fields.Char(
        string="Box",
        compute='_compute_x_box_names',
        store=True,
        index=True,
        help="Numeros des box du contrat (ex. 2G37). Champ enregistre : "
             "permet de chercher, trier et grouper les contrats par box.",
    )

    def _x_find_boxes(self):
        """Retourne {commande: box} en retrouvant les box via le modele de
        produit des lignes du contrat, comme _sync_storage_boxes
        (storage.box.product_tmpl_id). Une seule recherche pour tout le lot."""
        Box = self.env['storage.box'].sudo()
        tmpl_by_order = {}
        all_tmpl = set()
        for order in self:
            tmpls = set(order.order_line.filtered(
                lambda l: l.product_id and not l.display_type
            ).mapped('product_id.product_tmpl_id').ids)
            tmpl_by_order[order.id] = tmpls
            all_tmpl |= tmpls
        boxes = Box.search([('product_tmpl_id', 'in', list(all_tmpl))]) if all_tmpl else Box
        box_by_tmpl = {}
        for box in boxes:
            box_by_tmpl[box.product_tmpl_id.id] = box_by_tmpl.get(box.product_tmpl_id.id, Box) | box
        result = {}
        for order in self:
            found = Box
            for tmpl_id in tmpl_by_order[order.id]:
                found |= box_by_tmpl.get(tmpl_id, Box)
            result[order.id] = found
        return result

    @api.depends('order_line.product_id', 'order_line.display_type')
    def _compute_x_box_ids(self):
        found = self._x_find_boxes()
        for order in self:
            order.x_box_ids = found[order.id]

    @api.depends('order_line.product_id', 'order_line.display_type')
    def _compute_x_box_names(self):
        found = self._x_find_boxes()
        for order in self:
            order.x_box_names = ', '.join(sorted(found[order.id].mapped('name'))) or False
