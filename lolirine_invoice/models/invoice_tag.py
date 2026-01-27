# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InvoiceTag(models.Model):
    """Tags pour classifier les factures"""
    _name = 'lolirine.invoice.tag'
    _description = 'Tag de facture'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    color = fields.Integer(string='Couleur', default=0)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Actif', default=True)
    
    invoice_count = fields.Integer(
        string='Nb Factures',
        compute='_compute_invoice_count'
    )
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Le nom du tag doit etre unique !'),
    ]

    def _compute_invoice_count(self):
        for tag in self:
            tag.invoice_count = self.env['account.move'].search_count([
                ('invoice_tag_ids', 'in', tag.id),
                ('move_type', 'in', ('out_invoice', 'out_refund'))
            ])

    def action_view_invoices(self):
        """Voir les factures avec ce tag"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('invoice_tag_ids', 'in', self.id),
                ('move_type', 'in', ('out_invoice', 'out_refund'))
            ],
            'context': {'default_move_type': 'out_invoice'},
        }
