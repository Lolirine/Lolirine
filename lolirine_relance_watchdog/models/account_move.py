# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

DEFAULT_ALERT_DAYS = 10
PAYMENT_JOURNAL_TYPES = ('bank', 'cash', 'credit')


def _digits(text):
    return re.sub(r'\D', '', text or '')


class AccountMove(models.Model):
    _inherit = 'account.move'

    lolirine_relance_alert = fields.Boolean(
        string="Relance incoherente",
        default=False,
        copy=False,
        index=True,
        help="Cochee automatiquement lorsque la facture est echue depuis "
             "plusieurs jours sans suivi de relance coherent.",
    )
    lolirine_relance_msg = fields.Char(
        string="Motif d'alerte",
        copy=False,
        help="Liste des anomalies detectees par la surveillance des relances.",
    )
    lolirine_payment_available = fields.Boolean(
        string="Paiement a lettrer",
        compute='_compute_lolirine_payment_available',
        search='_search_lolirine_payment_available',
        help="Le client a un paiement bancaire rapproche sur son compte client "
             "mais non lettre avec une facture : la facture peut etre soldee "
             "via le bouton « Actualiser le rapprochement ».",
    )
    lolirine_payment_available_amount = fields.Monetary(
        string="Montant disponible",
        compute='_compute_lolirine_payment_available',
        currency_field='company_currency_id',
    )

    # ------------------------------------------------------------------
    # Paiements bancaires non lettres
    # ------------------------------------------------------------------
    @api.model
    def _lolirine_open_payment_domain(self):
        """Lignes de credit client issues d'un journal de banque, non lettrees."""
        return [
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('balance', '<', 0),
            ('amount_residual', '!=', 0),
            ('journal_id.type', 'in', PAYMENT_JOURNAL_TYPES),
        ]

    def _lolirine_open_payment_lines(self):
        """Paiements non lettres du client de cette facture."""
        self.ensure_one()
        receivable = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable')
        return self.env['account.move.line'].search(
            self._lolirine_open_payment_domain() + [
                ('company_id', '=', self.company_id.id),
                ('account_id', 'in', receivable.account_id.ids),
                ('partner_id.commercial_partner_id', '=',
                 self.commercial_partner_id.id),
            ], order='date asc, id asc')

    def _lolirine_is_open_invoice(self):
        self.ensure_one()
        return (
            self.move_type == 'out_invoice'
            and self.state == 'posted'
            and self.payment_state not in ('paid', 'in_payment', 'reversed')
            and self.amount_residual > 0
        )

    @api.depends('payment_state', 'amount_residual', 'partner_id')
    def _compute_lolirine_payment_available(self):
        open_invs = self.filtered(lambda m: m.id and m._lolirine_is_open_invoice())
        totals = {}
        if open_invs:
            lines = self.env['account.move.line'].search(
                self._lolirine_open_payment_domain() + [
                    ('partner_id.commercial_partner_id', 'in',
                     open_invs.commercial_partner_id.ids),
                ])
            for line in lines:
                key = (line.company_id.id, line.partner_id.commercial_partner_id.id)
                totals[key] = totals.get(key, 0.0) - line.amount_residual
        for mv in self:
            amount = 0.0
            if mv in open_invs:
                amount = totals.get(
                    (mv.company_id.id, mv.commercial_partner_id.id), 0.0)
            mv.lolirine_payment_available = amount > 0
            mv.lolirine_payment_available_amount = amount

    def _search_lolirine_payment_available(self, operator, value):
        if operator in ('in', 'not in'):
            wanted = True in (value or [])
            positive = wanted if operator == 'in' else not wanted
        elif operator in ('=', '!='):
            positive = bool(value) if operator == '=' else not bool(value)
        else:
            return []
        lines = self.env['account.move.line'].search(
            self._lolirine_open_payment_domain())
        partner_ids = lines.partner_id.commercial_partner_id.ids
        invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ('paid', 'in_payment', 'reversed')),
            ('amount_residual', '>', 0),
            ('commercial_partner_id', 'in', partner_ids),
        ])
        return [('id', 'in' if positive else 'not in', invoices.ids)]

    # ------------------------------------------------------------------
    # Actualisation du rapprochement
    # ------------------------------------------------------------------
    def _lolirine_force_recompute_payment(self):
        """Recalcule residuels et statut de paiement (statut perime)."""
        lines = self.line_ids
        for fname in ('amount_residual', 'amount_residual_currency', 'reconciled'):
            self.env.add_to_compute(lines._fields[fname], lines)
        for fname in ('amount_residual', 'amount_residual_signed', 'payment_state'):
            self.env.add_to_compute(self._fields[fname], self)
        self.env.flush_all()

    def _lolirine_refs(self):
        """References permettant de reconnaitre un virement pour cette facture."""
        self.ensure_one()
        refs = set()
        for txt in (self.payment_reference, self.name):
            d = _digits(txt)
            if len(d) >= 8:
                refs.add(d)
        return refs

    @staticmethod
    def _lolirine_line_text(line):
        st = line.move_id.statement_line_id
        return ' '.join(filter(None, [
            st.payment_ref if st else '', line.name, line.ref, line.move_id.ref,
        ]))

    def _lolirine_pick_payment(self, candidates):
        """Choisit le paiement a lettrer : reference, puis montant exact,
        puis paiement unique du client. Retourne (ligne, raison)."""
        self.ensure_one()
        refs = self._lolirine_refs()
        if refs:
            for line in candidates:
                txt = _digits(self._lolirine_line_text(line))
                if any(r in txt for r in refs):
                    return line, "communication structuree"
        cur = self.company_currency_id
        exact = candidates.filtered(
            lambda l: cur.is_zero(-l.amount_residual - self.amount_residual))
        if len(exact) == 1:
            return exact, "montant identique"
        if len(candidates) == 1:
            return candidates, "seul paiement disponible du client"
        return self.env['account.move.line'], False

    def _lolirine_find_misplaced_bank_lines(self):
        """Virements portant la reference de la facture mais rapproches
        ailleurs (autre compte ou autre facture)."""
        self.ensure_one()
        refs = self._lolirine_refs()
        if not refs:
            return []
        StLine = self.env['account.bank.statement.line']
        tails = {r[-5:] for r in refs}
        dom = ['|'] * (len(tails) - 1) + [('payment_ref', 'ilike', t) for t in tails]
        st_lines = StLine.search(
            [('company_id', '=', self.company_id.id), ('amount', '>', 0)] + dom,
            limit=50)
        out = []
        for st in st_lines:
            if not any(r in _digits(st.payment_ref) for r in refs):
                continue
            mv_lines = st.move_id.line_ids
            recv = mv_lines.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable')
            if not st.is_reconciled:
                out.append("%s %.2f EUR : transaction non rapprochee"
                           % (st.date, st.amount))
            elif not recv:
                other = mv_lines.filtered(
                    lambda l: l.account_id != st.journal_id.default_account_id)
                out.append("%s %.2f EUR : rapprochee sur le compte %s "
                           "(et non sur le compte client) - utiliser "
                           "« Annuler l'attribution »"
                           % (st.date, st.amount,
                              ', '.join(other.account_id.mapped('code'))))
            else:
                targets = recv.matched_debit_ids.debit_move_id.move_id - self
                if targets:
                    out.append("%s %.2f EUR : lettree avec %s"
                               % (st.date, st.amount,
                                  ', '.join(targets.mapped('name'))))
        return out

    def action_lolirine_refresh_reconciliation(self):
        """Bouton / action serveur : recalcule le statut puis lettre les
        paiements bancaires disponibles sur les factures selectionnees."""
        invoices = self.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
        invoices._lolirine_force_recompute_payment()

        done, missing, already = [], [], []
        for inv in invoices.sorted(lambda m: (m.invoice_date_due or m.date, m.id)):
            if not inv._lolirine_is_open_invoice():
                already.append(inv.name)
                continue
            assigned = []
            tried = self.env['account.move.line']
            while inv._lolirine_is_open_invoice():
                line, reason = inv._lolirine_pick_payment(
                    inv._lolirine_open_payment_lines() - tried)
                if not line:
                    break
                tried |= line
                amount = min(-line.amount_residual, inv.amount_residual)
                inv.js_assign_outstanding_line(line.id)
                assigned.append("%.2f EUR du %s (%s)" % (amount, line.date, reason))
            if assigned:
                inv.message_post(body="Rapprochement actualise : " + ", ".join(assigned))
                done.append("%s : %s" % (inv.name, ", ".join(assigned)))
            if inv._lolirine_is_open_invoice():
                hints = inv._lolirine_find_misplaced_bank_lines()
                left = inv._lolirine_open_payment_lines()
                if left:
                    hints.append("%d paiement(s) non lettre(s) ambigu(s) - a "
                                 "rattacher via « Ajouter » sur la facture"
                                 % len(left))
                missing.append("%s (reste %.2f EUR)%s" % (
                    inv.name, inv.amount_residual,
                    (" : " + " ; ".join(hints)) if hints else
                    " : aucun paiement trouve"))
        if invoices:
            invoices._lolirine_check_relance()

        parts = []
        if already:
            parts.append("Deja soldee(s) apres recalcul : " + ", ".join(already))
        if done:
            parts.append("Lettree(s) : " + " | ".join(done))
        if missing:
            parts.append("Toujours ouverte(s) : " + " | ".join(missing))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Actualisation du rapprochement",
                'message': "\n".join(parts) or "Aucune facture client validee.",
                'type': 'warning' if missing else 'success',
                'sticky': bool(missing),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def _lolirine_relance_eligible(self):
        """Facture client postee, non soldee et echue."""
        self.ensure_one()
        return (
            self.move_type == 'out_invoice'
            and self.state == 'posted'
            and self.payment_state not in ('paid', 'in_payment', 'reversed')
            and self.amount_residual > 0
            and bool(self.invoice_date_due)
        )

    def _lolirine_last_followup_date(self):
        """Date du dernier courrier de relance envoye au client."""
        self.ensure_one()
        if not self.partner_id:
            return False
        msg = self.env['mail.message'].search([
            ('model', '=', 'res.partner'),
            ('res_id', '=', self.partner_id.id),
            ('message_type', '=', 'notification'),
            '|', ('subject', 'ilike', 'appel'),
                 ('subject', 'ilike', 'demeure'),
        ], order='date desc', limit=1)
        return msg.date.date() if msg and msg.date else False

    def _lolirine_check_relance(self):
        """Recalcule le drapeau d'alerte sur les factures du recordset."""
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            seuil = int(ICP.get_param('lolirine_relance.alert_days',
                                      DEFAULT_ALERT_DAYS))
        except (TypeError, ValueError):
            seuil = DEFAULT_ALERT_DAYS
        today = fields.Date.today()
        SO = self.env['sale.order']

        for mv in self:
            motifs = []
            if mv._lolirine_relance_eligible():
                retard = (today - mv.invoice_date_due).days
                if retard > seuil:

                    last = mv._lolirine_last_followup_date()
                    if not last or last < mv.invoice_date_due:
                        motifs.append(
                            "aucune relance depuis l'echeance (%s j de retard)" % retard)

                    if mv.partner_id.followup_reminder_type == 'manual':
                        motifs.append("suivi client en manuel")

                    if SO.search_count([
                        ('partner_id', '=', mv.partner_id.id),
                        ('subscription_state', '=', '3_progress'),
                    ]):
                        motifs.append("abonnement encore actif")

                    if any('frais de relance' in (line.name or '').lower()
                           for line in mv.invoice_line_ids):
                        motifs.append("facture de frais impayee")

                if mv.lolirine_payment_available:
                    motifs.append("paiement bancaire non lettre disponible")

            mv.lolirine_relance_alert = bool(motifs)
            mv.lolirine_relance_msg = " / ".join(motifs) if motifs else False

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_lolirine_relance_watchdog(self):
        """Passage quotidien : recalcule toutes les factures ouvertes."""
        moves = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ('paid', 'in_payment', 'reversed')),
        ])
        moves._lolirine_check_relance()

        # Les factures soldees entre-temps ne doivent plus porter d'alerte
        obsoletes = self.search([
            ('lolirine_relance_alert', '=', True),
            ('id', 'not in', moves.ids),
        ])
        if obsoletes:
            obsoletes.write({
                'lolirine_relance_alert': False,
                'lolirine_relance_msg': False,
            })
        return True

    # ------------------------------------------------------------------
    # Action manuelle
    # ------------------------------------------------------------------
    def action_lolirine_check_relance(self):
        """Bouton / action serveur : recalcul immediat sur la selection."""
        self._lolirine_check_relance()
        return True
