# -*- coding: utf-8 -*-
from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        """Ajoute le compteur de factures manquantes sur la carte du journal banque."""
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        StLine = self.env['account.bank.statement.line']
        for journal in self.filtered(lambda j: j.type == 'bank'):
            lines = StLine.search([
                ('journal_id', '=', journal.id),
                ('is_reconciled', '=', False),
                ('state', '=', 'posted'),
                ('amount', '<', 0),  # sorties = factures fournisseurs attendues
            ])
            missing = lines.filtered(lambda l: l.x_invoice_status == 'missing')
            dashboard_data[journal.id]['lolirine_missing_invoice_count'] = len(missing)

    def action_open_missing_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'lolirine_missing_invoices.action_missing_invoice_lines')
        action['domain'] = [
            ('journal_id', '=', self.id),
            ('is_reconciled', '=', False),
            ('state', '=', 'posted'),
        ]
        return action
