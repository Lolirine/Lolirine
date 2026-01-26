from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures email",
        default=False,
        help="Si active, les factures de ce client seront envoyees automatiquement par email"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto factures Peppol",
        default=False,
        help="Si active, les factures de ce client seront envoyees automatiquement via Peppol"
    )
    
    peppol_eas = fields.Selection([
        ('0002', '0002 - SIREN'),
        ('0007', '0007 - Numero TVA'),
        ('0009', '0009 - SIRET'),
        ('0088', '0088 - EAN Location Code'),
        ('0130', '0130 - EU VAT'),
        ('0208', '0208 - BE:EN'),
        ('9930', '9930 - BE:VAT'),
    ], string="EAS (Scheme ID)", 
       help="Electronic Address Scheme pour Peppol. Pour la Belgique, utilisez 0208 (BE:EN).")
    
    peppol_endpoint = fields.Char(
        string="Endpoint Peppol",
        help="Identifiant Peppol (ex: numero d'entreprise pour BE:EN)"
    )
    
    invoice_overdue_count = fields.Integer(
        string='Factures en retard',
        compute='_compute_invoice_stats'
    )
    
    invoice_overdue_amount = fields.Monetary(
        string='Montant en retard',
        compute='_compute_invoice_stats'
    )
    
    @api.onchange('vat')
    def _onchange_vat_peppol(self):
        if self.vat and not self.peppol_endpoint:
            vat_clean = self.vat.replace(' ', '').replace('.', '')
            if vat_clean.startswith('BE'):
                self.peppol_eas = '0208'
                self.peppol_endpoint = vat_clean[2:]

    def _compute_invoice_stats(self):
        for partner in self:
            overdue = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ('paid', 'reversed')),
                ('is_overdue', '=', True),
            ])
            partner.invoice_overdue_count = len(overdue)
            partner.invoice_overdue_amount = sum(overdue.mapped('amount_residual'))
