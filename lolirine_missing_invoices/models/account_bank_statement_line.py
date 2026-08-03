# -*- coding: utf-8 -*-
import re

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import float_compare, float_is_zero

NO_INVOICE_PARAM = 'lolirine_missing_invoices.no_invoice_labels'

INVOICE_TYPES = ('in_invoice', 'in_refund', 'out_invoice', 'out_refund',
                 'out_receipt', 'in_receipt')

# payment_state considérés comme "il reste quelque chose à rapprocher".
# 'in_payment' est essentiel : un paiement enregistré mais non lettré met la
# facture dans cet état, et l'ancienne version du module l'excluait du pool,
# ce qui produisait de faux "facture manquante".
OPEN_PAYMENT_STATES = ('not_paid', 'partial', 'in_payment')


def _digits(text):
    """Ne garde que les chiffres (pour comparer communications structurées / refs)."""
    return re.sub(r'\D', '', text or '')


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    x_invoice_status = fields.Selection(
        selection=[
            ('reconciled', 'Rapprochée'),
            ('found', 'Facture candidate trouvée'),
            ('invoiced', 'Facture existante (déjà soldée)'),
            ('missing', 'Facture manquante'),
            ('no_invoice', 'Sans facture attendue'),
            ('na', 'Non applicable'),
        ],
        string='Statut facture',
        compute='_compute_x_invoice_status',
        search='_search_x_invoice_status',
        help="Facture manquante = aucune facture de la base ne correspond à cette "
             "transaction, ni par référence, ni par montant, ni par partenaire. "
             "Les remboursements de crédit, la TVA et les virements internes sont "
             "classés « Sans facture attendue » et n'apparaissent pas dans le rapport.",
    )
    x_invoice_candidate_ids = fields.Many2many(
        'account.move',
        relation='x_stl_invoice_candidate_rel',
        string='Factures candidates',
        compute='_compute_x_invoice_status',
        help="Factures ouvertes qui pourraient être rapprochées de cette transaction.",
    )
    x_matched_move_ids = fields.Many2many(
        'account.move',
        relation='x_stl_matched_move_rel',
        string='Factures liées',
        compute='_compute_x_invoice_status',
        help="Factures effectivement lettrées avec cette transaction, ou factures "
             "déjà soldées portant la référence trouvée dans le libellé.",
    )

    # ------------------------------------------------------------------
    # Exclusions : transactions qui n'auront jamais de facture
    # ------------------------------------------------------------------
    @api.model
    def _get_no_invoice_matchers(self):
        """Motifs (journaux, type, paramètre) identifiant ces transactions.

        Trois sources cumulées :
          1. les modèles de rapprochement cochés « Aucune facture attendue » ;
          2. les références des crédits encadrés par account_loans ;
          3. une liste libre de motifs (Paramètres système).
        """
        out = []

        for m in self.env['account.reconcile.model'].search(
                [('x_no_invoice_expected', '=', True)]):
            if m.match_label and m.match_label_param:
                out.append((set(m.match_journal_ids.ids),
                            m.match_label, m.match_label_param))

        if 'account.loan' in self.env:
            for loan in self.env['account.loan'].sudo().search([]):
                ref = (loan.name or '').replace('Emprunt', '').strip()
                if len(ref) >= 6:
                    out.append((set(), 'contains', ref))

        raw = self.env['ir.config_parameter'].sudo().get_param(NO_INVOICE_PARAM, '')
        for pat in filter(None, (p.strip() for p in raw.splitlines())):
            out.append((set(), 'contains', pat))

        return out

    def _x_no_invoice_expected(self, matchers):
        self.ensure_one()
        label = self.payment_ref or ''
        upper = label.upper()
        for journals, kind, param in matchers:
            if journals and self.journal_id.id not in journals:
                continue
            if kind == 'contains' and param.upper() in upper:
                return True
            if kind == 'match_regex':
                try:
                    if re.search(param, label, re.IGNORECASE):
                        return True
                except re.error:
                    continue
        return False

    # ------------------------------------------------------------------
    # Relations déjà lettrées
    # ------------------------------------------------------------------
    def _x_get_reconciled_moves(self):
        """Pièces effectivement lettrées avec l'écriture bancaire de la ligne."""
        self.ensure_one()
        moves = self.env['account.move']
        for aml in self.move_id.line_ids:
            for part in (aml.matched_debit_ids | aml.matched_credit_ids):
                other = part.debit_move_id if part.debit_move_id != aml else part.credit_move_id
                if other.move_id and other.move_id != self.move_id:
                    moves |= other.move_id
        return moves

    # ------------------------------------------------------------------
    # Pools de recherche
    # ------------------------------------------------------------------
    def _get_matching_pools(self):
        """(factures ouvertes, toutes factures) sur une fenêtre glissante.

        Le pool « toutes » sert uniquement à constater qu'une facture EXISTE
        (match par référence), pour ne pas la déclarer manquante quand elle est
        déjà soldée. Le pool « ouvertes » sert à proposer un rapprochement.
        """
        Move = self.env['account.move']
        domain = [('state', '=', 'posted'), ('move_type', 'in', INVOICE_TYPES)]
        dates = [l.date for l in self if l.date]
        if dates:
            domain.append(('invoice_date', '>=', min(dates) - relativedelta(months=6)))
        all_moves = Move.search(domain)
        open_moves = all_moves.filtered(
            lambda m: m.payment_state in OPEN_PAYMENT_STATES
            and not float_is_zero(m.amount_residual, precision_digits=2)
        )
        return open_moves, all_moves

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('is_reconciled', 'state', 'amount', 'partner_id', 'payment_ref')
    def _compute_x_invoice_status(self):
        matchers = self._get_no_invoice_matchers()
        open_moves, all_moves = self._get_matching_pools()

        move_refs = {
            m.id: {_digits(m.name), _digits(m.ref), _digits(m.payment_reference)} - {''}
            for m in all_moves
        }

        for line in self:
            line.x_invoice_candidate_ids = False
            line.x_matched_move_ids = False

            if line.state != 'posted' or not line.amount:
                line.x_invoice_status = 'na'
                continue

            # 1) Crédits, TVA, virements internes... : jamais de facture
            if line._x_no_invoice_expected(matchers):
                line.x_invoice_status = 'no_invoice'
                continue

            # 2) Déjà rapprochée : on remonte la relation réelle
            if line.is_reconciled:
                line.x_matched_move_ids = line._x_get_reconciled_moves()
                line.x_invoice_status = 'reconciled'
                continue

            if line.amount < 0:
                move_types = ('in_invoice', 'out_refund', 'in_receipt')
            else:
                move_types = ('out_invoice', 'in_refund', 'out_receipt')

            target = abs(line.amount)
            line_digits = _digits(line.payment_ref)
            partner = line.partner_id.commercial_partner_id

            def _same_scope(m):
                return m.move_type in move_types and m.company_id == line.company_id

            def _ref_hit(m):
                return bool(line_digits) and any(
                    r and len(r) >= 5 and r in line_digits
                    for r in move_refs.get(m.id, ())
                )

            pool_open = open_moves.filtered(_same_scope)

            # a) Référence / communication structurée dans le libellé
            ref_open = pool_open.filtered(_ref_hit)

            # b) Montant résiduel exact
            amount_open = pool_open.filtered(
                lambda m: float_compare(abs(m.amount_residual_signed), target,
                                        precision_digits=2) == 0
            )
            if partner:
                narrowed = amount_open.filtered(
                    lambda m: m.partner_id.commercial_partner_id == partner)
                if narrowed:
                    amount_open = narrowed

            # c) Partenaire connu + montant total (facture partiellement payée)
            partner_total = self.env['account.move']
            if partner:
                partner_total = pool_open.filtered(
                    lambda m: m.partner_id.commercial_partner_id == partner
                    and float_compare(abs(m.amount_total), target,
                                      precision_digits=2) == 0
                )

            candidates = ref_open | amount_open | partner_total
            if candidates:
                line.x_invoice_candidate_ids = candidates
                line.x_invoice_status = 'found'
                continue

            # 3) La facture existe mais est déjà soldée (payée ailleurs,
            #    lettrée manuellement, avoir...) : ce n'est pas un manquant.
            already = all_moves.filtered(lambda m: _same_scope(m) and _ref_hit(m))
            if already:
                line.x_matched_move_ids = already
                line.x_invoice_status = 'invoiced'
                continue

            line.x_invoice_status = 'missing'

    # ------------------------------------------------------------------
    # Search (champ non stocké)
    # ------------------------------------------------------------------
    def _search_x_invoice_status(self, operator, value):
        # Odoo 19 normalise les domaines avant d'atteindre cette méthode :
        # ('=', 'missing') devient ('in', OrderedSet(['missing'])). Il faut donc
        # accepter tout itérable, pas seulement list/tuple.
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError()
        values = {value} if isinstance(value, str) else set(value)
        negative = operator in ('!=', 'not in')

        domain = [('state', '=', 'posted')]
        # Seul le statut 'reconciled' concerne les lignes déjà rapprochées :
        # dans tous les autres cas on évite de calculer sur toute la base.
        if not values & {'reconciled', 'na'}:
            domain.append(('is_reconciled', '=', False))

        lines = self.search(domain)
        matched = lines.filtered(lambda l: l.x_invoice_status in values)
        return [('id', 'not in' if negative else 'in', matched.ids)]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_open_candidates(self):
        self.ensure_one()
        moves = self.x_invoice_candidate_ids | self.x_matched_move_ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factures liées',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
        }

    def action_x_link_single_candidate(self):
        """Rapproche les lignes n'ayant qu'une seule candidate au montant exact.

        Sans effet sur les lignes ambiguës : elles restent à traiter à la main
        dans le rapprochement bancaire.
        """
        done = self.env['account.bank.statement.line']
        for line in self:
            if line.is_reconciled or line.x_invoice_status != 'found':
                continue
            inv = line.x_invoice_candidate_ids
            if len(inv) != 1:
                continue
            if float_compare(abs(inv.amount_residual), abs(line.amount),
                             precision_digits=2) != 0:
                continue
            if line._x_link_invoice(inv):
                done |= line
        return done

    def _x_link_invoice(self, invoice):
        """Bascule la ligne de suspens sur le compte tiers et lettre."""
        self.ensure_one()
        aml = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable',
                                                    'liability_payable')
            and not l.reconciled
        )
        suspense = self.move_id.line_ids.filtered(
            lambda l: l.account_id == self.journal_id.suspense_account_id)
        if len(aml) != 1 or len(suspense) != 1:
            return False
        suspense.with_context(check_move_validity=False).write({
            'account_id': aml.account_id.id,
            'partner_id': aml.partner_id.id,
        })
        if not self.partner_id:
            self.with_context(check_move_validity=False).partner_id = aml.partner_id
        (suspense + aml).reconcile()
        return True
