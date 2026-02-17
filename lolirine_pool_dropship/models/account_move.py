# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_dropship_invoice = fields.Boolean(
        string='Facture Piscine',
        compute='_compute_is_dropship_invoice',
        store=True,
    )

    @api.depends('invoice_origin')
    def _compute_is_dropship_invoice(self):
        for move in self:
            if move.invoice_origin:
                # Chercher si la commande d'origine est dropship
                orders = self.env['sale.order'].search([
                    ('name', 'in', [o.strip() for o in move.invoice_origin.split(',')]),
                    ('is_dropship_order', '=', True),
                ])
                move.is_dropship_invoice = bool(orders)
            else:
                move.is_dropship_invoice = False

    def action_preview_pool_invoice_pdf(self):
        """Prévisualise le PDF de la facture piscine dans un nouvel onglet"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/lolirine_pool_dropship.report_pool_invoice_document/%s' % self.id,
            'target': 'new',
        }
