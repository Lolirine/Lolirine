# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.tools import float_compare


def _digits(text):
    """Ne garde que les chiffres (pour comparer communications structurées / refs)."""
    return re.sub(r'\D', '', text or '')


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    x_invoice_status = fields.Selection(
        selection=[
            ('found', 'Facture candidate trouvée'),
            ('missing', 'Facture manquante'),
            ('na', 'Non applicable'),
        ],
        string='Statut facture',
        compute='_compute_x_invoice_status',
        search='_search_x_invoice_status',
        help="Facture manquante = aucune facture ouverte dans la base ne correspond "
             "à cette transaction (montant, référence ou partenaire+montant).",
    )
    x_invoice_candidate_ids = fields.Many2many(
        'account.move',
        string='Factures candidates',
        compute='_compute_x_invoice_status',
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    def _get_open_moves_for_matching(self):
        """Toutes les factures/avoirs postés et non (totalement) payés."""
        return self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('move_type', 'in', ('in_invoice', 'in_refund',
                                 'out_invoice', 'out_refund')),
        ])

    @api.depends('is_reconciled', 'state', 'amount', 'partner_id', 'payment_ref')
    def _compute_x_invoice_status(self):
        open_moves = self._get_open_moves_for_matching()
        # Pré-calcul des refs (chiffres uniquement) pour le match par libellé
        move_refs = {
            m.id: {_digits(m.name), _digits(m.ref), _digits(m.payment_reference)} - {''}
            for m in open_moves
        }
        for line in self:
            if line.is_reconciled or line.state != 'posted' or not line.amount:
                line.x_invoice_status = 'na'
                line.x_invoice_candidate_ids = False
                continue

            if line.amount < 0:
                # Sortie d'argent -> facture fournisseur (ou avoir client)
                move_types = ('in_invoice', 'out_refund')
            else:
                # Entrée d'argent -> facture client (ou avoir fournisseur)
                move_types = ('out_invoice', 'in_refund')

            target = abs(line.amount)
            line_digits = _digits(line.payment_ref)

            pool = open_moves.filtered(
                lambda m: m.move_type in move_types
                and m.company_id == line.company_id
            )

            # 1) Match par référence dans le libellé (communication structurée,
            #    numéro de facture...). Le plus fiable.
            ref_matches = pool.filtered(
                lambda m: line_digits and any(
                    r and len(r) >= 5 and r in line_digits
                    for r in move_refs.get(m.id, set())
                )
            )

            # 2) Match par montant ouvert (résiduel) au centime près
            amount_matches = pool.filtered(
                lambda m: float_compare(
                    abs(m.amount_residual_signed), target, precision_digits=2
                ) == 0
            )

            # 3) Si partenaire connu sur la ligne, on privilégie ses factures
            if line.partner_id:
                partner_amount = amount_matches.filtered(
                    lambda m: m.partner_id.commercial_partner_id
                    == line.partner_id.commercial_partner_id
                )
                if partner_amount:
                    amount_matches = partner_amount

            candidates = ref_matches | amount_matches
            line.x_invoice_candidate_ids = candidates
            line.x_invoice_status = 'found' if candidates else 'missing'

    # ------------------------------------------------------------------
    # Search (champ non stocké)
    # ------------------------------------------------------------------
    def _search_x_invoice_status(self, operator, value):
        # Odoo 19 : les domaines sont normalises avant d'atteindre cette methode.
        # ('=', 'missing') devient ('in', OrderedSet(['missing'])) -> il faut
        # accepter tout iterable (list, tuple, set, OrderedSet), pas seulement
        # list/tuple.
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError()
        values = {value} if isinstance(value, str) else set(value)
        negative = operator in ('!=', 'not in')
        # Seules les lignes non rapprochées peuvent être found/missing
        lines = self.search([
            ('is_reconciled', '=', False),
            ('state', '=', 'posted'),
        ])
        matched = lines.filtered(lambda l: l.x_invoice_status in values)
        if 'na' in values:
            # 'na' couvre aussi tout le reste (rapprochées) -> domaine inversé
            other = lines - matched
            return [('id', 'in' if negative else 'not in', other.ids)]
        return [('id', 'not in' if negative else 'in', matched.ids)]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def action_open_candidates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factures candidates',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.x_invoice_candidate_ids.ids)],
        }
