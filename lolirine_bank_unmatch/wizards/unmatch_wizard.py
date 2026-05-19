# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from markupsafe import Markup


class LolirineBankUnmatchWizard(models.TransientModel):
    _name = 'lolirine.bank.unmatch.wizard'
    _description = "Wizard de confirmation d'annulation d'attribution bancaire"

    bank_line_ids = fields.Many2many(
        'account.bank.statement.line',
        string="Transactions bancaires concernées",
        required=True,
    )
    line_count = fields.Integer(
        string="Nombre de transactions",
        compute='_compute_line_meta',
    )
    is_single = fields.Boolean(
        string="Mode unique",
        compute='_compute_line_meta',
    )
    single_line_id = fields.Many2one(
        'account.bank.statement.line',
        string="Transaction (mode unique)",
        compute='_compute_line_meta',
    )

    # Détails affichés en mode unique (related)
    single_date = fields.Date(
        related='single_line_id.date',
        string="Date",
        readonly=True,
    )
    single_amount = fields.Monetary(
        related='single_line_id.amount',
        string="Montant",
        readonly=True,
    )
    single_currency_id = fields.Many2one(
        related='single_line_id.currency_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='single_line_id.currency_id',
        readonly=True,
    )
    single_partner_id = fields.Many2one(
        related='single_line_id.partner_id',
        string="Partenaire actuel",
        readonly=True,
    )
    single_journal_id = fields.Many2one(
        related='single_line_id.journal_id',
        string="Journal",
        readonly=True,
    )
    single_payment_ref = fields.Char(
        related='single_line_id.payment_ref',
        string="Référence bancaire",
        readonly=True,
    )
    single_is_reconciled = fields.Boolean(
        related='single_line_id.is_reconciled',
        string="Réconciliée",
        readonly=True,
    )

    current_lines_preview = fields.Html(
        string="Écritures comptables actuelles",
        compute='_compute_current_lines_preview',
        sanitize=False,
    )

    @api.depends('bank_line_ids')
    def _compute_line_meta(self):
        for w in self:
            w.line_count = len(w.bank_line_ids)
            w.is_single = (w.line_count == 1)
            w.single_line_id = w.bank_line_ids[:1] if w.is_single else False

    @api.depends('single_line_id')
    def _compute_current_lines_preview(self):
        for w in self:
            if not w.single_line_id:
                w.current_lines_preview = False
                continue
            move = w.single_line_id.move_id
            rows = []
            for ml in move.line_ids:
                partner_name = ml.partner_id.name if ml.partner_id else '—'
                rec_icon = ('<span class="text-success">✓</span>'
                            if ml.reconciled else '<span class="text-muted">—</span>')
                rows.append(
                    f"<tr>"
                    f"<td><code>{ml.account_id.code}</code></td>"
                    f"<td>{ml.account_id.name}</td>"
                    f"<td>{partner_name}</td>"
                    f"<td class='text-end'>{ml.debit:.2f}</td>"
                    f"<td class='text-end'>{ml.credit:.2f}</td>"
                    f"<td class='text-center'>{rec_icon}</td>"
                    f"</tr>"
                )
            html = (
                "<table class='table table-sm table-bordered'>"
                "<thead class='table-light'>"
                "<tr>"
                "<th>Code</th><th>Compte</th><th>Partenaire</th>"
                "<th class='text-end'>Débit</th>"
                "<th class='text-end'>Crédit</th>"
                "<th class='text-center'>Lettré</th>"
                "</tr></thead><tbody>"
                + "".join(rows)
                + "</tbody></table>"
            )
            w.current_lines_preview = Markup(html)

    def action_confirm_unmatch(self):
        """Confirme et exécute l'annulation pour toutes les transactions sélectionnées."""
        self.ensure_one()
        if not self.bank_line_ids:
            return {'type': 'ir.actions.act_window_close'}

        for bl in self.bank_line_ids:
            bl._do_unmatch_attribution()

        # Notification du succès et rechargement
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Annulation réussie"),
                'message': _(
                    "%d transaction(s) bancaire(s) remise(s) en suspense. "
                    "Vous pouvez les ré-attribuer via le widget de rapprochement.",
                ) % len(self.bank_line_ids),
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }
