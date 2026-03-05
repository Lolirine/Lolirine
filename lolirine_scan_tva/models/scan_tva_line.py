from odoo import models, fields


class ScanTvaLine(models.Model):
    _name = 'lolirine.scan.tva.line'
    _description = 'Ligne TVA Scan'
    _order = 'tax_rate'

    scan_id = fields.Many2one(
        'lolirine.scan.tva', string='Scan TVA',
        required=True, ondelete='cascade', index=True,
    )
    tax_rate = fields.Float(string='Taux TVA (%)', digits=(5, 2))
    base_amount = fields.Monetary(string='Base HT', currency_field='currency_id')
    vat_amount = fields.Monetary(string='Montant TVA', currency_field='currency_id')
    total_amount = fields.Monetary(string='Total TTC', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='scan_id.currency_id', store=True, readonly=True,
    )
