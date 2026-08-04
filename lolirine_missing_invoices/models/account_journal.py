# -*- coding: utf-8 -*-
import logging

from dateutil.relativedelta import relativedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        """Ajoute le compteur de factures manquantes sur la carte du journal banque."""
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        StLine = self.env['account.bank.statement.line']
        floor = fields.Date.context_today(self) - relativedelta(months=12)
        for journal in self.filtered(lambda j: j.type == 'bank'):
            dashboard_data[journal.id]['lolirine_missing_invoice_count'] = 0
            try:
                lines = StLine.search([
                    ('journal_id', '=', journal.id),
                    ('is_reconciled', '=', False),
                    ('state', '=', 'posted'),
                    ('amount', '<', 0),
                    ('date', '>=', floor),
                ])
                missing = lines.filtered(lambda l: l.x_invoice_status == 'missing')
                dashboard_data[journal.id]['lolirine_missing_invoice_count'] = len(missing)
            except Exception:
                _logger.exception("Compteur factures manquantes, journal %s", journal.id)

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
