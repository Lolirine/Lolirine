# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LolirineRefundWizard(models.TransientModel):
    _name = 'lolirine.refund.wizard'
    _description = 'Assistant de remboursement client'

    invoice_id = fields.Many2one('account.move', string='Facture', readonly=True)
    partner_id = fields.Many2one(related='invoice_id.partner_id', readonly=True)
    amount_invoice = fields.Monetary(related='invoice_id.amount_total', string='Montant facture', readonly=True)
    amount = fields.Monetary(string='Montant à rembourser', required=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id', readonly=True)
    journal_id = fields.Many2one(
        'account.journal', string='Journal de remboursement',
        required=True, domain=[('type', '=', 'bank')],
    )
    date = fields.Date(string='Date du remboursement', required=True, default=fields.Date.today)
    reason = fields.Char(string='Motif', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        be82 = self.env['account.journal'].search([('code', '=', 'BNK4')], limit=1)
        if be82:
            res['journal_id'] = be82.id
        if res.get('invoice_id'):
            inv = self.env['account.move'].browse(res['invoice_id'])
            res['amount'] = inv.amount_total
        return res

    def action_confirm_refund(self):
        self.ensure_one()
        inv = self.invoice_id
        if self.amount <= 0:
            raise UserError(_("Le montant du remboursement doit être positif."))
        if self.amount > inv.amount_total:
            raise UserError(_(
                "Le montant (%(amount)s €) ne peut pas dépasser le montant de la facture (%(total)s €).",
                amount=self.amount, total=inv.amount_total
            ))
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': inv.partner_id.id,
            'amount': self.amount,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'memo': f'Remboursement {inv.name} — {self.reason}',
            'currency_id': inv.currency_id.id,
        })
        payment.action_post()
        inv_line = inv.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        pay_line = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        if inv_line and pay_line:
            (inv_line + pay_line).reconcile()
        inv.message_post(body=_(
            "💸 Remboursement de %(amount)s € via %(journal)s (%(payment)s) — Motif : %(reason)s",
            amount=self.amount, journal=self.journal_id.name,
            payment=payment.name, reason=self.reason,
        ))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }
