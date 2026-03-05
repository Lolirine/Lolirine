from odoo import models, fields, api


class ScanTvaLine(models.Model):
    _name = 'lolirine.scan.tva.line'
    _description = 'Ligne TVA Scan'
    _order = 'tax_rate'

    scan_id = fields.Many2one(
        'lolirine.scan.tva', string='Scan TVA',
        required=True, ondelete='cascade', index=True,
    )
    description = fields.Char(string='Description')
    tax_rate = fields.Float(string='Taux TVA (%)', digits=(5, 2))
    base_amount = fields.Monetary(string='Base HT', currency_field='currency_id')
    vat_amount = fields.Monetary(string='Montant TVA', currency_field='currency_id')
    total_amount = fields.Monetary(string='Total TTC', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='scan_id.currency_id', store=True, readonly=True,
    )

    @api.onchange('base_amount', 'tax_rate')
    def _onchange_compute_from_base(self):
        """Calculer TVA et TTC depuis Base HT + Taux"""
        if self.base_amount and self.tax_rate:
            self.vat_amount = round(self.base_amount * self.tax_rate / 100.0, 2)
            self.total_amount = round(self.base_amount + self.vat_amount, 2)
        elif self.base_amount and not self.tax_rate:
            self.vat_amount = 0.0
            self.total_amount = self.base_amount

    @api.onchange('vat_amount')
    def _onchange_vat_amount(self):
        """Recalculer TTC quand on modifie le montant TVA manuellement"""
        if self.base_amount:
            self.total_amount = round(self.base_amount + self.vat_amount, 2)

    @api.onchange('total_amount')
    def _onchange_total_amount(self):
        """Calculer Base HT depuis TTC si on saisit le TTC en premier"""
        if self.total_amount and self.tax_rate and not self.base_amount:
            self.base_amount = round(self.total_amount / (1 + self.tax_rate / 100.0), 2)
            self.vat_amount = round(self.total_amount - self.base_amount, 2)
