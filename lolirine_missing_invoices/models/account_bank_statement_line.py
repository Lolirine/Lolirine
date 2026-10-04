# -*- coding: utf-8 -*-
import re
from itertools import combinations

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import float_compare, float_is_zero

NO_INVOICE_PARAM = 'lolirine_missing_invoices.no_invoice_labels'
FEE_TOLERANCE_PARAM = 'lolirine_missing_invoices.fee_tolerance'

INVOICE_TYPES = ('in_invoice', 'in_refund', 'out_invoice', 'out_refund',
                 'out_receipt', 'in_receipt')

# payment_state consideres comme "il reste quelque chose a rapprocher".
# 'in_payment' est essentiel : un paiement enregistre mais non lettre met la
# facture dans cet etat, et l'exclure du pool produit de faux "facture manquante".
OPEN_PAYMENT_STATES = ('not_paid', 'partial', 'in_payment')

# Tolerance par defaut (EUR) : frais d'intervention / commission de change CBC
# inclus dans le debit d'un paiement carte a l'etranger (0,61 / 0,95 EUR).
DEFAULT_FEE_TOLERANCE = 1.00

# Fenetre pour reconnaitre une facture deja soldee du meme fournisseur.
INVOICED_WINDOW_DAYS = 40

# Mots ignores pour reconnaitre un fournisseur par son nom dans le libelle.
NAME_STOPWORDS = {
    'SOCIETE', 'SPRL', 'SCRL', 'SRL', 'SA', 'NV', 'BV', 'BVBA', 'GMBH', 'LTD',
    'LIMITED', 'INC', 'LLC', 'SARL', 'SAS', 'THE', 'GROUP', 'BELGIUM', 'BELGIQUE',
    'SERVICES', 'SERVICE', 'COMPANY', 'MARKET', 'FOURNISSEURS', 'DIVERS',
    'PAIEMENT', 'DEBIT', 'CARTE', 'VIREMENT', 'DOMICILIATION',
}


def _digits(text):
    """Ne garde que les chiffres (pour comparer communications structurees)."""
    return re.sub(r'\D', '', text or '')


def _words(text):
    return [w for w in re.split(r'[^A-Z0-9]+', (text or '').upper()) if w]


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    x_invoice_status = fields.Selection(
        selection=[
            ('reconciled', 'Rapprochee'),
            ('found', 'Facture candidate trouvee'),
            ('invoiced', 'Facture existante (deja soldee)'),
            ('missing', 'Facture manquante'),
            ('no_invoice', 'Sans facture attendue'),
            ('na', 'Non applicable'),
        ],
        string='Statut facture',
        compute='_compute_x_invoice_status',
        search='_search_x_invoice_status',
        help="Facture manquante = aucune facture de la base ne correspond a cette "
             "transaction, ni par reference, ni par montant, ni par fournisseur.",
    )
    x_invoice_candidate_ids = fields.Many2many(
        'account.move',
        relation='x_stl_invoice_candidate_rel',
        column1='statement_line_id',
        column2='move_id',
        string='Factures candidates',
        compute='_compute_x_invoice_status',
    )
    x_matched_move_ids = fields.Many2many(
        'account.move',
        relation='x_stl_matched_move_rel',
        column1='statement_line_id',
        column2='move_id',
        string='Factures liees',
        compute='_compute_x_invoice_status',
    )
    x_expected_partner_id = fields.Many2one(
        'res.partner',
        string='Fournisseur identifie',
        compute='_compute_x_invoice_status',
        help="Fournisseur reconnu : motif de libelle bancaire configure, sinon nom "
             "d'un fournisseur present dans le libelle, sinon partenaire de la ligne.",
    )
    x_invoice_priority = fields.Boolean(
        string='Facture attendue (suggestion)',
        compute='_compute_x_invoice_status',
        search='_search_x_invoice_priority',
        help="Suggestion : le fournisseur identifie est marque « Facture attendue » "
             "et aucune facture ne correspond.",
    )
    x_to_claim = fields.Boolean(
        string='A reclamer',
        copy=False,
        help="Case manuelle : la facture de cette transaction est a demander au "
             "fournisseur.",
    )

    # ------------------------------------------------------------------
    # Parametres
    # ------------------------------------------------------------------
    @api.model
    def _x_fee_tolerance(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(FEE_TOLERANCE_PARAM)
        try:
            return float(raw) if raw not in (None, False, '') else DEFAULT_FEE_TOLERANCE
        except ValueError:
            return DEFAULT_FEE_TOLERANCE

    # ------------------------------------------------------------------
    # Identification du fournisseur
    # ------------------------------------------------------------------
    @api.model
    def _x_get_partner_index(self):
        """(motifs tries du plus long au plus court, politiques par partenaire)."""
        partners = self.env['res.partner'].sudo().search(
            ['|', ('x_invoice_policy', '!=', False), ('x_bank_label', '!=', False)])
        labels, policies = [], {}
        for p in partners:
            commercial = p.commercial_partner_id
            if p.x_invoice_policy:
                policies[commercial.id] = p.x_invoice_policy
            for motif in (p.x_bank_label or '').split('|'):
                motif = motif.strip().upper()
                if len(motif) >= 3:
                    labels.append((motif, commercial))
        labels.sort(key=lambda t: -len(t[0]))
        return labels, policies

    @api.model
    def _x_get_name_index(self, moves):
        """{mot distinctif du nom: partenaires} pour les fournisseurs des factures."""
        index = {}
        for p in moves.mapped('commercial_partner_id'):
            for w in _words(p.name):
                if len(w) >= 4 and not w.isdigit() and w not in NAME_STOPWORDS:
                    index.setdefault(w, self.env['res.partner'])
                    index[w] |= p
                    break
        return index

    def _x_identify_partners(self, labels, names):
        """Partenaires commerciaux reconnus (recordset, eventuellement multiple)."""
        self.ensure_one()
        upper = (self.payment_ref or '').upper()
        if upper:
            for motif, partner in labels:
                if motif in upper:
                    return partner
            hits = self.env['res.partner']
            for w in set(_words(upper)):
                if w in names:
                    hits |= names[w]
            if hits:
                return hits
        if self.partner_id:
            return self.partner_id.commercial_partner_id
        return self.env['res.partner']

    # ------------------------------------------------------------------
    # Exclusions par modele de rapprochement / credits / motifs libres
    # ------------------------------------------------------------------
    @api.model
    def _get_no_invoice_matchers(self):
        out = []

        models_ = self.env['account.reconcile.model'].search(
            [('x_no_invoice_expected', '=', True)])
        for m in models_:
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
    # Relations deja lettrees
    # ------------------------------------------------------------------
    def _x_get_reconciled_moves(self):
        self.ensure_one()
        moves = self.env['account.move']
        for aml in self.move_id.line_ids:
            for part in (aml.matched_debit_ids | aml.matched_credit_ids):
                other = part.debit_move_id if part.debit_move_id != aml \
                    else part.credit_move_id
                if other.move_id and other.move_id != self.move_id:
                    moves |= other.move_id
        return moves

    def _x_target_amount(self):
        """Montant restant a rapprocher (une partie peut deja etre lettree,
        ex. frais carte CBC impute sur la facture CBC)."""
        self.ensure_one()
        residual = self.amount_residual if 'amount_residual' in self._fields else 0.0
        if residual and not float_is_zero(residual, precision_digits=2):
            return abs(residual)
        return abs(self.amount)

    # ------------------------------------------------------------------
    # Pools de recherche
    # ------------------------------------------------------------------
    def _get_matching_pools(self):
        Move = self.env['account.move']
        domain = [('state', '=', 'posted'), ('move_type', 'in', INVOICE_TYPES)]
        dates = [l.date for l in self if l.date]
        if dates:
            domain.append(('invoice_date', '>=',
                           min(dates) - relativedelta(months=6)))
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
        labels, policies = self._x_get_partner_index()
        open_moves, all_moves = self._get_matching_pools()
        names = self._x_get_name_index(all_moves)
        tolerance = self._x_fee_tolerance()

        move_refs = {
            m.id: {_digits(m.name), _digits(m.ref), _digits(m.payment_reference)} - {''}
            for m in all_moves
        }

        for line in self:
            line.x_invoice_candidate_ids = False
            line.x_matched_move_ids = False
            line.x_invoice_priority = False

            idents = line._x_identify_partners(labels, names)
            line.x_expected_partner_id = idents[:1]
            policy = next((policies[p.id] for p in idents if p.id in policies), None)

            if line.state != 'posted' or not line.amount:
                line.x_invoice_status = 'na'
                continue

            # 1) Jamais de facture : credits, TVA, virements internes, magasins
            if policy == 'none' or line._x_no_invoice_expected(matchers):
                line.x_invoice_status = 'no_invoice'
                continue

            # 2) Deja rapprochee : on remonte la relation reelle
            if line.is_reconciled:
                line.x_matched_move_ids = line._x_get_reconciled_moves()
                line.x_invoice_status = 'reconciled'
                continue

            if line.amount < 0:
                move_types = ('in_invoice', 'out_refund', 'in_receipt')
            else:
                move_types = ('out_invoice', 'in_refund', 'out_receipt')

            target = line._x_target_amount()
            line_digits = _digits(line.payment_ref)

            def _same_scope(m, _types=move_types, _line=line):
                return m.move_type in _types and m.company_id == _line.company_id

            def _ref_hit(m, _digits_=line_digits):
                return bool(_digits_) and any(
                    r and len(r) >= 5 and r in _digits_
                    for r in move_refs.get(m.id, ())
                )

            def _of_ident(m, _idents=idents):
                return bool(_idents) and m.partner_id.commercial_partner_id in _idents

            pool_open = open_moves.filtered(_same_scope)

            # a) Reference / communication structuree dans le libelle
            ref_open = pool_open.filtered(_ref_hit)

            # b) Montant residuel exact
            amount_open = pool_open.filtered(
                lambda m: float_compare(abs(m.amount_residual_signed), target,
                                        precision_digits=2) == 0
            )
            if idents:
                narrowed = amount_open.filtered(_of_ident)
                if narrowed:
                    amount_open = narrowed

            # c) Fournisseur identifie + montant total (facture partiellement payee)
            partner_total = pool_open.filtered(
                lambda m: _of_ident(m)
                and float_compare(abs(m.amount_total), target, precision_digits=2) == 0
            ) if idents else self.env['account.move']

            # c2) Fournisseur identifie + frais carte CBC inclus dans le debit
            fee_match = pool_open.filtered(
                lambda m: _of_ident(m)
                and 0.005 < target - abs(m.amount_residual_signed) <= tolerance
            ) if idents else self.env['account.move']

            # d) Combinaison de factures (OVH : principale + 0,30 EUR), frais inclus
            combo_match = self.env['account.move']
            if idents and not (ref_open or amount_open or partner_total or fee_match):
                combo_match = line._x_combination_match(
                    pool_open.filtered(_of_ident), target, tolerance)

            candidates = ref_open | amount_open | partner_total | fee_match | combo_match
            if candidates:
                line.x_invoice_candidate_ids = candidates
                line.x_invoice_status = 'found'
                continue

            # 3) La facture existe mais est deja soldee : pas un manquant.
            already = all_moves.filtered(lambda m: _same_scope(m) and _ref_hit(m))
            if not already and idents and line.date:
                window = relativedelta(days=INVOICED_WINDOW_DAYS)
                already = all_moves.filtered(
                    lambda m: _same_scope(m) and _of_ident(m)
                    and m.payment_state in ('paid', 'reversed')
                    and m.invoice_date
                    and line.date - window <= m.invoice_date <= line.date + window
                    and -0.005 <= target - abs(m.amount_total) <= tolerance
                )
            if already:
                line.x_matched_move_ids = already
                line.x_invoice_status = 'invoiced'
                continue

            line.x_invoice_status = 'missing'
            line.x_invoice_priority = (policy == 'expected')

    # ------------------------------------------------------------------
    # Search (champs non stockes)
    # ------------------------------------------------------------------
    def _search_x_invoice_status(self, operator, value):
        # Odoo 19 normalise les domaines avant d'atteindre cette methode :
        # ('=', 'missing') devient ('in', OrderedSet(['missing'])).
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError()
        values = {value} if isinstance(value, str) else set(value)
        negative = operator in ('!=', 'not in')

        domain = [('state', '=', 'posted')]
        if values & {'reconciled', 'na'}:
            domain.append(('date', '>=', fields.Date.context_today(self)
                           - relativedelta(months=12)))
        else:
            domain.append(('is_reconciled', '=', False))

        lines = self.search(domain)
        matched = lines.filtered(lambda l: l.x_invoice_status in values)
        return [('id', 'not in' if negative else 'in', matched.ids)]

    def _search_x_invoice_priority(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError()
        want = bool(value) if operator == '=' else not bool(value)
        lines = self.search([('state', '=', 'posted'),
                             ('is_reconciled', '=', False)])
        matched = lines.filtered(lambda l: l.x_invoice_priority == want)
        return [('id', 'in', matched.ids)]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_open_candidates(self):
        self.ensure_one()
        moves = self.x_invoice_candidate_ids | self.x_matched_move_ids
        if len(moves) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': moves.name,
                'res_model': 'account.move',
                'res_id': moves.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factures liees',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
        }

    def action_x_open_transaction(self):
        """Ouvre la transaction : ecran de rapprochement si disponible,
        sinon l'ecriture comptable de la ligne bancaire."""
        self.ensure_one()
        if hasattr(self, 'action_open_recon_st_line'):
            try:
                return self.action_open_recon_st_line()
            except Exception:
                pass
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transaction',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_x_create_bill(self):
        """Nouvelle facture pre-remplie avec le fournisseur identifie et la date."""
        self.ensure_one()
        partner = self.x_expected_partner_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle facture',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_move_type': 'in_invoice' if self.amount < 0 else 'out_invoice',
                'default_partner_id': partner.id or False,
                'default_invoice_date': self.date,
            },
        }

    def action_x_link_single_candidate(self):
        """Rapproche les lignes n'ayant qu'une seule candidate au montant exact.
        Les candidates avec ecart (frais carte) restent a traiter dans le
        rapprochement bancaire."""
        done = self.env['account.bank.statement.line']
        skipped = 0
        for line in self:
            if line.is_reconciled or line.x_invoice_status != 'found':
                continue
            inv = line.x_invoice_candidate_ids
            if len(inv) != 1:
                skipped += 1
                continue
            if float_compare(abs(inv.amount_residual), line._x_target_amount(),
                             precision_digits=2) != 0:
                skipped += 1
                continue
            if line._x_link_invoice(inv):
                done |= line
            else:
                skipped += 1

        if done:
            message = "%s transaction(s) rapprochee(s)." % len(done)
            if skipped:
                message += (" %s laissee(s) de cote (candidates multiples ou "
                            "ecart de frais : a traiter via « Transaction »)." % skipped)
            kind = 'success'
        else:
            message = ("Aucune transaction rapprochee : candidates multiples ou "
                       "ecart de frais. Ouvre la transaction pour la rapprocher.")
            kind = 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Rapprochement automatique",
                'message': message,
                'type': kind,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _x_link_invoice(self, invoice):
        """Bascule la ligne de suspens sur le compte tiers et lettre.

        NE PAS ecrire partner_id sur la ligne bancaire : cela declenche
        _synchronize_to_moves, qui tente de reconstruire les ecritures d'une
        piece validee et leve une UserError. Le partenaire porte par la ligne
        d'ecriture suffit.
        """
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
        (suspense + aml).reconcile()
        return True

    def _x_combination_match(self, candidates, target, tolerance=0.0):
        """Cherche une combinaison de 2 ou 3 factures ouvertes du fournisseur
        dont la somme des residuels egale le montant de la transaction, a la
        tolerance de frais carte pres (le debit peut depasser, jamais l'inverse).

        Cas OVH : une facture principale plus une facture de 0,30 EUR, prelevees
        ensemble.
        """
        if len(candidates) < 2:
            return self.env['account.move']
        for taille in (2, 3):
            best = None
            for combo in combinations(candidates, taille):
                total = sum(abs(m.amount_residual_signed) for m in combo)
                ecart = target - total
                if -0.01 <= ecart <= max(0.01, tolerance):
                    if best is None or abs(ecart) < best[0]:
                        best = (abs(ecart), combo)
            if best:
                res = self.env['account.move']
                for m in best[1]:
                    res |= m
                return res
        return self.env['account.move']
