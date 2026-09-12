# -*- coding: utf-8 -*-
"""Wizard de clôture de contrat d'abonnement Lolirine.

Capitalise sur le travail manuel fait pour Mme LEMAL :
- Saisie de la date de fin
- Calcul automatique des factures de prorata
- Création des factures en DRAFT (pour revue)
- Envoi du mail récap au client
- Passage du contrat en churn
- Libération automatique des box (via hook _sync_storage_boxes)
- Génération PDF officiel pour les sociétés

Gère également le cas particulier de l'ANNULATION AVANT MISE À DISPOSITION :
le client se désiste avant d'avoir occupé le box. Dans ce cas, aucun loyer
n'est proratisé et le préavis ne s'applique pas : seuls les frais de dossier
sont dus, avec en option l'indemnité de 15 jours de redevance prévue à
l'article 4.4 des conditions générales.

Sécurité :
- Aperçu obligatoire avant validation
- Saisie du mot 'CLOTURER' pour confirmer
- Mode test pour le mail récap
"""

import calendar
import logging
from contextlib import contextmanager
from datetime import date, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ============================================================================
# WIZARD PRINCIPAL
# ============================================================================

class LolirineContractCloseWizard(models.TransientModel):
    """Wizard de clôture de contrat avec calcul prorata."""
    _name = 'lolirine.contract.close.wizard'
    _description = "Assistant de clôture de contrat Lolirine"

    # ========================================================================
    # CONTEXTE
    # ========================================================================

    subscription_id = fields.Many2one(
        'sale.order',
        string="Contrat",
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get('active_id')
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Client",
        related='subscription_id.partner_id',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        related='subscription_id.company_id',
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    # ========================================================================
    # OPTIONS
    # ========================================================================

    end_date = fields.Date(
        string="Date de fin demandée par le client",
        required=True,
        default=fields.Date.context_today,
        help="Date à laquelle le client souhaite arrêter (ou date à laquelle "
             "il a réellement quitté le box). Cette date sera comparée à la "
             "date minimale légale (date d'avertissement + délai de préavis)."
    )

    # ========================================================================
    # ANNULATION AVANT MISE À DISPOSITION (art. 4.4 des CG)
    # ========================================================================

    cloture_avant_occupation = fields.Boolean(
        string="Annulation avant mise à disposition",
        default=False,
        help="À cocher lorsque le client se désiste avant d'avoir occupé le "
             "box. Aucun loyer n'est proratisé et le préavis ne s'applique "
             "pas : seuls les frais de dossier sont dus (article 4.4 des "
             "conditions générales)."
    )
    appliquer_indemnite_4_4 = fields.Boolean(
        string="Appliquer l'indemnité de 15 jours (art. 4.4)",
        default=False,
        help="L'article 4.4 des conditions générales permet de réclamer, en "
             "plus des frais de dossier, une indemnité égale à quinze jours "
             "de redevance. Décoché par défaut : c'est un geste commercial "
             "qui se décide au cas par cas."
    )
    frais_dossier_product_id = fields.Many2one(
        'product.product',
        string="Produit frais de dossier",
        default=lambda self: self.env['product.product'].search(
            [('default_code', '=', 'FRAIS-DOSSIER')], limit=1),
        help="Produit utilisé pour facturer les frais de dossier lors d'une "
             "annulation avant mise à disposition."
    )

    # ========================================================================
    # PRÉAVIS
    # ========================================================================

    notice_date = fields.Date(
        string="Date d'avertissement par le client",
        required=True,
        default=fields.Date.context_today,
        help="Date à laquelle le client nous a officiellement prévenus de sa "
             "volonté de clôturer son contrat (par mail, téléphone, courrier)."
    )
    notice_period_days = fields.Integer(
        string="Délai de préavis (jours)",
        default=15,
        required=True,
        help="Nombre de jours de préavis exigés par les conditions générales. "
             "Standard Lolirine : 15 jours."
    )
    legal_end_date = fields.Date(
        string="Date de fin minimale légale",
        compute='_compute_legal_end_date',
        store=False,
        help="Date à partir de laquelle la clôture peut prendre effet "
             "(date d'avertissement + délai de préavis)."
    )
    effective_end_date = fields.Date(
        string="Date de fin effective (facturée)",
        compute='_compute_effective_end_date',
        store=False,
        help="Date réellement utilisée pour calculer le prorata. C'est le "
             "maximum entre la date demandée et la date min légale."
    )
    notice_respected = fields.Boolean(
        string="Préavis respecté",
        compute='_compute_notice_respected',
        store=False,
    )
    send_email = fields.Boolean(
        string="Envoyer le mail récap au client",
        default=True,
        help="Si coché, un mail récapitulatif sera envoyé au client après "
             "la clôture. Sinon, tu gères l'envoi manuellement plus tard."
    )
    detail_per_box = fields.Boolean(
        string="Détailler chaque box dans le mail",
        default=True,
        help="Si plusieurs box sur ce contrat : si coché, le mail détaille "
             "chaque box avec son prorata. Sinon, il affiche juste le total."
    )
    attach_pdf_for_companies = fields.Boolean(
        string="Joindre PDF de clôture (sociétés)",
        default=True,
        help="Si le client est une société, joint un PDF officiel de "
             "clôture en pièce jointe du mail."
    )
    test_mode = fields.Boolean(
        string="Mode test",
        default=False,
        help="Si coché, le mail récap est envoyé à l'adresse de test "
             "ci-dessous au lieu du client."
    )
    test_email = fields.Char(
        string="Email de test",
        default=lambda self: self.env.user.email or '',
    )

    # ========================================================================
    # CALCULS
    # ========================================================================

    prorata_line_ids = fields.One2many(
        'lolirine.contract.close.prorata.line',
        'wizard_id',
        string="Lignes de prorata",
    )
    prorata_total_ht = fields.Monetary(
        string="Total prorata HT",
        compute='_compute_totals',
        currency_field='currency_id'
    )
    prorata_total_ttc = fields.Monetary(
        string="Total prorata TTC",
        compute='_compute_totals',
        currency_field='currency_id'
    )

    # ========================================================================
    # APERÇU
    # ========================================================================

    has_calculation = fields.Boolean(
        compute='_compute_has_calculation',
        store=False,
    )
    email_preview_html = fields.Html(
        string="Aperçu du mail",
        compute='_compute_email_preview',
        sanitize=False,
    )

    # ========================================================================
    # CONFIRMATION (étape 3)
    # ========================================================================

    confirmation_step = fields.Selection(
        [('initial', 'Initial'),
         ('preview', 'Aperçu'),
         ('confirm', 'Confirmation'),
         ('done', 'Terminé')],
        default='initial',
        readonly=True,
    )
    confirmation_text = fields.Char(
        string="Pour confirmer, tape : CLOTURER",
        help="Saisie obligatoire pour confirmer la clôture du contrat."
    )

    # ========================================================================
    # RÉCAP FINAL (étape 4)
    # ========================================================================

    created_invoice_ids = fields.Many2many(
        'account.move',
        string="Factures créées",
        readonly=True,
    )
    final_message = fields.Html(
        string="Récapitulatif",
        readonly=True,
    )

    # ========================================================================
    # COMPUTES
    # ========================================================================

    @api.depends('prorata_line_ids', 'prorata_line_ids.amount_ht',
                 'prorata_line_ids.amount_ttc')
    def _compute_totals(self):
        for wiz in self:
            wiz.prorata_total_ht = sum(wiz.prorata_line_ids.mapped('amount_ht'))
            wiz.prorata_total_ttc = sum(wiz.prorata_line_ids.mapped('amount_ttc'))

    # ========================================================================
    # COMPUTES PRÉAVIS
    # ========================================================================

    @api.depends('notice_date', 'notice_period_days')
    def _compute_legal_end_date(self):
        for wiz in self:
            if wiz.notice_date and wiz.notice_period_days:
                wiz.legal_end_date = wiz.notice_date + timedelta(
                    days=wiz.notice_period_days
                )
            else:
                wiz.legal_end_date = False

    @api.depends('end_date', 'legal_end_date', 'cloture_avant_occupation')
    def _compute_effective_end_date(self):
        for wiz in self:
            if wiz.cloture_avant_occupation:
                # Pas de préavis applicable : le box n'a jamais été occupé.
                wiz.effective_end_date = wiz.end_date
            elif wiz.end_date and wiz.legal_end_date:
                wiz.effective_end_date = max(wiz.end_date, wiz.legal_end_date)
            elif wiz.end_date:
                wiz.effective_end_date = wiz.end_date
            else:
                wiz.effective_end_date = False

    @api.depends('end_date', 'legal_end_date', 'cloture_avant_occupation')
    def _compute_notice_respected(self):
        for wiz in self:
            if wiz.cloture_avant_occupation:
                # Notion sans objet : rien à reprocher au client.
                wiz.notice_respected = True
            elif wiz.end_date and wiz.legal_end_date:
                wiz.notice_respected = wiz.end_date >= wiz.legal_end_date
            else:
                wiz.notice_respected = True

    @api.depends('prorata_line_ids')
    def _compute_has_calculation(self):
        for wiz in self:
            wiz.has_calculation = bool(wiz.prorata_line_ids)

    @api.depends('prorata_line_ids', 'detail_per_box', 'send_email',
                 'cloture_avant_occupation', 'appliquer_indemnite_4_4')
    def _compute_email_preview(self):
        for wiz in self:
            if not wiz.has_calculation:
                wiz.email_preview_html = (
                    "<p style='color: #888; font-style: italic; padding: 20px;'>"
                    "Lance d'abord le calcul du prorata pour voir l'aperçu du mail."
                    "</p>"
                )
                continue

            wiz.email_preview_html = wiz._render_email_preview()

    # ========================================================================
    # ONCHANGE
    # ========================================================================

    @api.onchange('cloture_avant_occupation')
    def _onchange_cloture_avant_occupation(self):
        """Neutralise le préavis quand le box n'a jamais été occupé."""
        for wiz in self:
            if wiz.cloture_avant_occupation:
                wiz.notice_period_days = 0
            else:
                wiz.appliquer_indemnite_4_4 = False
                if not wiz.notice_period_days:
                    wiz.notice_period_days = 15

    # ========================================================================
    # ACTION 1 : CALCULER LE PRORATA
    # ========================================================================

    def action_compute_prorata(self):
        """Calcule les lignes de prorata pour chaque ligne récurrente du contrat."""
        self.ensure_one()

        if not self.subscription_id:
            raise UserError(_("Aucun contrat sélectionné."))

        # Cas particulier : le client se désiste avant d'occuper le box.
        # Aucun loyer n'est dû, seuls les frais de dossier (art. 4.4).
        if self.cloture_avant_occupation:
            return self._compute_annulation_avant_occupation()

        if self.notice_date and self.end_date and self.notice_date > self.end_date + timedelta(days=180):
            # Cas absurde : avertissement plus de 6 mois après la date de fin
            raise UserError(_(
                "La date d'avertissement (%s) est trop éloignée de la date "
                "de fin demandée (%s). Vérifie les dates saisies."
            ) % (self.notice_date, self.end_date))

        # On utilise effective_end_date (qui prend en compte le préavis)
        date_for_calc = self.effective_end_date or self.end_date

        if date_for_calc < (self.subscription_id.start_date or date.min):
            raise UserError(_(
                "La date de fin (%s) ne peut pas être antérieure à la date "
                "de début du contrat (%s)."
            ) % (date_for_calc, self.subscription_id.start_date))

        # Vide les lignes existantes
        self.prorata_line_ids.unlink()

        # Pour chaque ligne récurrente, calcule le prorata
        new_lines = []
        for sol in self.subscription_id.order_line:
            if not self._is_line_recurring(sol):
                continue

            prorata_data = self._compute_prorata_for_line(sol, date_for_calc)
            if prorata_data:
                new_lines.append((0, 0, prorata_data))

        if not new_lines:
            raise UserError(_(
                "Aucune ligne de prorata à créer. Soit le contrat est déjà "
                "facturé jusqu'après la date de fin, soit il n'y a pas de "
                "lignes récurrentes."
            ))

        self.write({
            'prorata_line_ids': new_lines,
            'confirmation_step': 'preview',
        })

        return self._reload_view()

    # ========================================================================
    # ANNULATION AVANT MISE À DISPOSITION
    # ========================================================================

    def _compute_annulation_avant_occupation(self):
        """Construit les lignes pour une annulation avant mise à disposition.

        Le box n'a jamais été occupé : aucun loyer n'est proratisé et le
        préavis ne s'applique pas. On facture uniquement les frais de dossier,
        et, si l'option est cochée, l'indemnité de quinze jours de redevance
        prévue à l'article 4.4 des conditions générales.
        """
        self.ensure_one()

        # Garde-fou : refuser si le contrat a déjà produit une facture de loyer.
        # Dans ce cas, le box a été occupé et ce mode n'est pas le bon.
        deja_facture = self.env['account.move.line'].search_count([
            ('move_id.invoice_origin', '=', self.subscription_id.name),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', '=', 'out_invoice'),
            ('display_type', '=', 'product'),
            ('product_id.default_code', 'not like', 'FRAIS-'),
        ])
        if deja_facture:
            raise UserError(_(
                "Ce contrat a déjà fait l'objet d'au moins une facture de "
                "loyer : le box a donc été mis à disposition.\n\n"
                "Décoche 'Annulation avant mise à disposition' et procède à "
                "une clôture normale avec calcul du prorata."
            ))

        if not self.frais_dossier_product_id:
            raise UserError(_(
                "Produit FRAIS-DOSSIER introuvable. Renseigne-le dans le "
                "champ 'Produit frais de dossier' avant de continuer."
            ))

        self.prorata_line_ids.unlink()

        end_date = self.end_date or fields.Date.context_today(self)
        new_lines = []

        # --------------------------------------------------------------
        # Ligne 1 : frais de dossier (toujours dus, non remboursables)
        # --------------------------------------------------------------
        sol_frais = self.subscription_id.order_line.filtered(
            lambda l: l.product_id == self.frais_dossier_product_id
        )[:1]
        prix_frais = sol_frais.price_unit if sol_frais else (
            self.frais_dossier_product_id.list_price or 15.0
        )
        taxes_frais = sol_frais.tax_ids if sol_frais else \
            self.frais_dossier_product_id.taxes_id
        ttc_frais = self._montant_ttc(
            prix_frais, taxes_frais, self.frais_dossier_product_id
        )

        new_lines.append((0, 0, {
            'product_id': self.frais_dossier_product_id.id,
            'order_line_id': sol_frais.id if sol_frais else False,
            'monthly_price': prix_frais,
            'period_start': end_date,
            'period_end': end_date,
            'days_in_month': 0,
            'days_to_bill': 0,
            'amount_ht': prix_frais,
            'amount_ttc': ttc_frais,
            'note': "Frais de dossier — non remboursables (art. 4.4 des CG)",
            'will_create_invoice': True,
        }))

        # --------------------------------------------------------------
        # Ligne 2 : indemnité de 15 jours de redevance (optionnelle)
        # --------------------------------------------------------------
        if self.appliquer_indemnite_4_4:
            # Quinze jours calendrier à compter de la date d'annulation,
            # bornes incluses : d'où le +14 et non le +15.
            periode_debut = end_date
            periode_fin = end_date + timedelta(days=14)

            for sol in self.subscription_id.order_line:
                if not self._is_line_recurring(sol):
                    continue

                # Prorata calendaire : la méthode gère le nombre réel de jours
                # du mois et le franchissement d'une fin de mois.
                montant_ht, jours, jours_du_mois = self._compute_prorata_amount(
                    sol.price_unit, periode_debut, periode_fin
                )
                montant_ttc = self._montant_ttc(
                    montant_ht, sol.tax_ids, sol.product_id
                )

                new_lines.append((0, 0, {
                    'product_id': sol.product_id.id,
                    'order_line_id': sol.id,
                    'monthly_price': sol.price_unit,
                    'period_start': periode_debut,
                    'period_end': periode_fin,
                    'days_in_month': jours_du_mois,
                    'days_to_bill': jours,
                    'amount_ht': montant_ht,
                    'amount_ttc': montant_ttc,
                    'note': "Indemnité d'annulation — 15 jours de redevance "
                            "(art. 4.4 des CG)",
                    'will_create_invoice': True,
                }))

        self.write({
            'prorata_line_ids': new_lines,
            'notice_period_days': 0,
            'confirmation_step': 'preview',
        })

        return self._reload_view()

    def _montant_ttc(self, amount_ht, taxes, product):
        """Calcule le montant TTC à partir d'un montant HT et de taxes."""
        if not taxes:
            return amount_ht
        return taxes.compute_all(
            amount_ht,
            currency=self.currency_id,
            quantity=1,
            product=product,
            partner=self.partner_id,
        )['total_included']

    def _is_line_recurring(self, line):
        """Détermine si une ligne est récurrente ET représente un vrai loyer
        à proratiser (et pas un ajustement, frais ponctuel, etc.).

        Filtre :
        - Pas une section/note
        - A un produit
        - Le produit est marqué récurrent
        - Le produit n'est pas un produit d'ajustement (Arrondi, Frais-*, etc.)
        - Le prix unitaire est positif (un loyer ne peut pas être négatif)
        """
        if line.display_type in ('line_section', 'line_note'):
            return False
        if not line.product_id:
            return False

        # Détection du caractère récurrent
        product = line.product_id
        if 'recurring_invoice' in product._fields:
            is_recurring = bool(product.recurring_invoice)
        elif hasattr(line, 'temporal_type'):
            is_recurring = line.temporal_type == 'subscription'
        elif hasattr(line, 'recurrence_id') and line.recurrence_id:
            is_recurring = True
        else:
            is_recurring = False

        if not is_recurring:
            return False

        # 🛟 Exclusions : produits non-loyer
        product_name_lower = (product.name or '').lower()
        product_code = (product.default_code or '').upper()

        # Exclure les ajustements d'arrondi
        if 'arrondi' in product_name_lower or 'rounding' in product_name_lower:
            return False

        # Exclure les frais ponctuels (FRAIS-DOSSIER, FRAIS-DECHETS, etc.)
        if product_code.startswith('FRAIS-') or product_code.startswith('FRAIS_'):
            return False

        # Exclure les lignes avec prix négatif (un loyer est toujours positif)
        if line.price_unit <= 0:
            return False

        return True

    def _compute_prorata_for_line(self, sol, end_date_to_use):
        """Calcule le prorata d'une ligne d'abonnement.

        Args:
            sol: sale.order.line à proratiser
            end_date_to_use: Date de fin effective (qui peut différer de
                self.end_date si le préavis force une date plus tardive)

        Returns:
            dict avec les valeurs pour créer une lolirine.contract.close.prorata.line,
            ou None si rien à facturer.
        """
        sub = self.subscription_id

        # 1. Trouver la dernière période facturée pour ce produit
        last_billed = self._get_last_billed_date(sol)

        # 2. Période à facturer : last_billed + 1 → end_date_to_use
        period_start = last_billed + timedelta(days=1) if last_billed else sub.start_date
        period_end = end_date_to_use

        if period_start > period_end:
            # Déjà tout facturé
            return {
                'product_id': sol.product_id.id,
                'order_line_id': sol.id,
                'monthly_price': sol.price_unit,
                'period_start': period_start,
                'period_end': period_end,
                'days_in_month': 0,
                'days_to_bill': 0,
                'amount_ht': 0.0,
                'amount_ttc': 0.0,
                'note': 'Déjà entièrement facturé',
                'will_create_invoice': False,
            }

        # 3. Calcul du prorata par mois (gérer le cas multi-mois)
        amount_ht, days_to_bill, days_in_month = self._compute_prorata_amount(
            sol.price_unit, period_start, period_end
        )

        # 4. Calcul TTC en utilisant les taxes de la ligne
        amount_ttc = self._montant_ttc(amount_ht, sol.tax_ids, sol.product_id)

        return {
            'product_id': sol.product_id.id,
            'order_line_id': sol.id,
            'monthly_price': sol.price_unit,
            'period_start': period_start,
            'period_end': period_end,
            'days_in_month': days_in_month,
            'days_to_bill': days_to_bill,
            'amount_ht': amount_ht,
            'amount_ttc': amount_ttc,
            'will_create_invoice': True,
        }

    def _get_last_billed_date(self, sol):
        """Trouve la dernière date couverte par une facture postée pour ce
        produit dans ce contrat.

        Modèle de facturation Lolirine : facture émise le 20 du mois pour le
        mois en cours (terme échu). Donc une facture datée du 20/04/2026
        couvre la période du 01/04 au 30/04.

        Logique :
        - On prend la dernière facture postée
        - last_billed_until = dernier jour du mois de invoice_date

        On cherche par DEUX critères pour récupérer toutes les factures :
        - invoice_origin = nom du contrat (factures manuelles)
        - subscription_id sur la ligne = id du contrat (factures auto Odoo 19)

        Returns:
            date ou None si jamais facturé.
        """
        sub = self.subscription_id

        # Recherche 1 : par invoice_origin
        invoice_lines_by_origin = self.env['account.move.line'].search([
            ('move_id.invoice_origin', '=', sub.name),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('product_id', '=', sol.product_id.id),
            ('display_type', '=', 'product'),
        ])

        # Recherche 2 : par subscription_id sur la ligne (Odoo 19 auto-billing)
        invoice_lines_by_sub = self.env['account.move.line']
        if 'subscription_id' in self.env['account.move.line']._fields:
            invoice_lines_by_sub = self.env['account.move.line'].search([
                ('subscription_id', '=', sub.id),
                ('move_id.state', '=', 'posted'),
                ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
                ('product_id', '=', sol.product_id.id),
                ('display_type', '=', 'product'),
            ])

        # Union des deux recherches (sans doublons)
        invoice_lines = invoice_lines_by_origin | invoice_lines_by_sub

        if not invoice_lines:
            return None

        # Récupérer la date de la facture la plus récente (mois facturé = mois courant)
        invoice_dates = [
            line.move_id.invoice_date for line in invoice_lines
            if line.move_id.invoice_date
        ]

        if not invoice_dates:
            return None

        last_invoice_date = max(invoice_dates)

        # Le mois facturé est le mois de invoice_date
        # last_billed_until = dernier jour de ce mois
        year = last_invoice_date.year
        month = last_invoice_date.month
        days_in_month = calendar.monthrange(year, month)[1]

        return date(year, month, days_in_month)

    def _compute_prorata_amount(self, monthly_price, period_start, period_end):
        """Calcule le montant HT du prorata pour une période.

        Si la période couvre 1 seul mois : monthly_price × jours/jours_du_mois
        Si la période couvre plusieurs mois : on additionne par mois.

        Returns:
            tuple (amount_ht, total_days_to_bill, days_in_first_month)
        """
        if period_start > period_end:
            return 0.0, 0, 0

        total_amount = 0.0
        total_days = 0
        first_month_days = 0
        is_first_month = True

        # Itérer mois par mois
        current = period_start
        while current <= period_end:
            year = current.year
            month = current.month
            days_in_month = calendar.monthrange(year, month)[1]

            # Fin du mois courant ou period_end (le plus tôt)
            month_end = date(year, month, days_in_month)
            slice_end = min(month_end, period_end)

            # Nombre de jours dans cette tranche
            days_in_slice = (slice_end - current).days + 1

            if is_first_month:
                first_month_days = days_in_month
                is_first_month = False

            # Si on facture tout le mois → loyer plein
            if current.day == 1 and slice_end.day == days_in_month:
                total_amount += monthly_price
            else:
                total_amount += monthly_price * days_in_slice / days_in_month

            total_days += days_in_slice

            # Passer au 1er du mois suivant
            if month == 12:
                current = date(year + 1, 1, 1)
            else:
                current = date(year, month + 1, 1)

        return round(total_amount, 2), total_days, first_month_days

    # ========================================================================
    # ACTION 2 : VOIR L'APERÇU & ENVOYER À SOI-MÊME
    # ========================================================================

    def action_send_preview_to_self(self):
        """Envoie un mail de test à l'utilisateur courant pour validation."""
        self.ensure_one()
        if not self.has_calculation:
            raise UserError(_(
                "Lance d'abord le calcul du prorata avant de tester le mail."
            ))

        test_email = self.test_email or self.env.user.email
        if not test_email:
            raise UserError(_("Aucune adresse email de test définie."))

        body_html = self._render_email_body()
        subject = self._render_email_subject()

        # Préparer attachment PDF si société
        attachment_ids = []
        if self._should_attach_pdf():
            attachment_ids = self._generate_pdf_attachment()

        mail = self.env['mail.mail'].sudo().create({
            'subject': f"[TEST] {subject}",
            'body_html': body_html,
            'email_from': self.company_id.email_formatted or 'noreply@lolirine.be',
            'email_to': test_email,
            'attachment_ids': [(6, 0, attachment_ids)],
            'auto_delete': False,
        })
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Aperçu envoyé"),
                'message': _("Mail envoyé à %s") % test_email,
                'type': 'success',
            }
        }

    # ========================================================================
    # ACTION 3 : DEMANDER CONFIRMATION
    # ========================================================================

    def action_request_confirmation(self):
        """Passe à l'écran de confirmation (étape 3)."""
        self.ensure_one()
        if not self.has_calculation:
            raise UserError(_(
                "Lance d'abord le calcul du prorata."
            ))
        self.confirmation_step = 'confirm'
        return self._reload_view()

    # ========================================================================
    # ACTION 4 : EXÉCUTER LA CLÔTURE
    # ========================================================================

    def action_execute_close(self):
        """Exécute la clôture après confirmation explicite."""
        self.ensure_one()

        # 🛟 Protection : exiger le mot CLOTURER
        if (self.confirmation_text or '').strip().upper() != 'CLOTURER':
            raise UserError(_(
                "Saisie incorrecte.\n\n"
                "Pour confirmer la clôture, tu dois saisir exactement le mot "
                "'CLOTURER' (en majuscules) dans le champ de confirmation.\n\n"
                "Si tu n'es pas sûr, clique 'Annuler' et reviens "
                "quand tu seras prêt."
            ))

        sub = self.subscription_id

        # ====================================================================
        # 1. Créer les factures de prorata en DRAFT
        # ====================================================================
        invoices = self.env['account.move']
        billable_lines = self.prorata_line_ids.filtered('will_create_invoice')

        for pl in billable_lines:
            inv = self._create_prorata_invoice(pl)
            invoices |= inv

        # ====================================================================
        # 2. Passer le contrat en churn (avec la date effective)
        # ====================================================================
        sub.write({
            'end_date': self.effective_end_date or self.end_date,
        })
        # set_close() en patch séparé : on appelle la bonne méthode
        if hasattr(sub, 'set_close'):
            sub.set_close()
        else:
            sub.write({
                'subscription_state': '6_churn',
                'next_invoice_date': False,
            })

        # ====================================================================
        # 3. Envoyer le mail récap si demandé
        # ====================================================================
        email_sent = False
        if self.send_email:
            try:
                self._send_recap_email(invoices)
                email_sent = True
            except Exception as e:
                _logger.exception("Erreur envoi mail récap")
                # On ne bloque pas la clôture si le mail échoue

        # ====================================================================
        # 4. Logger dans le chatter
        # ====================================================================
        motif = (
            "Annulation avant mise à disposition (art. 4.4)"
            if self.cloture_avant_occupation else "Clôture de contrat"
        )
        sub.message_post(
            body=_(
                "📋 %s via wizard au %s.<br/>"
                "%d facture(s) créée(s) en draft.<br/>"
                "Mail récap : %s"
            ) % (
                motif,
                self.end_date.strftime('%d/%m/%Y'),
                len(invoices),
                "✓ envoyé" if email_sent else (
                    "non envoyé (option décochée)" if not self.send_email
                    else "❌ erreur d'envoi"
                ),
            )
        )

        # ====================================================================
        # 5. Construire le récap final
        # ====================================================================
        final_msg = self._build_final_message(invoices, email_sent)

        self.write({
            'created_invoice_ids': [(6, 0, invoices.ids)],
            'final_message': final_msg,
            'confirmation_step': 'done',
        })

        return self._reload_view()

    def _create_prorata_invoice(self, prorata_line):
        """Crée une facture en DRAFT pour une ligne de prorata."""
        sub = self.subscription_id
        sol = prorata_line.order_line_id
        product = prorata_line.product_id

        # Description : on ne parle de prorata que lorsqu'il y en a un.
        if prorata_line.days_to_bill and prorata_line.period_start and prorata_line.period_end:
            description = (
                f"{sol.name or product.name}\n"
                f"Prorata du {prorata_line.period_start.strftime('%d/%m/%Y')} "
                f"au {prorata_line.period_end.strftime('%d/%m/%Y')} "
                f"({prorata_line.days_to_bill} jour(s))"
            )
        else:
            description = f"{product.name}"

        # En annulation avant occupation, la note porte le fondement contractuel
        if prorata_line.note:
            description = f"{description}\n{prorata_line.note}"

        # Taxes : celles de la ligne de contrat si elle existe, sinon celles
        # du produit (cas des frais de dossier absents du contrat).
        taxes = sol.tax_ids if sol else product.taxes_id

        # Compte de produit
        account = product.product_tmpl_id._get_product_accounts()['income']

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.effective_end_date or self.end_date,
            'invoice_origin': sub.name,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'product_id': product.id,
                'quantity': 1,
                'price_unit': prorata_line.amount_ht,
                'tax_ids': [(6, 0, taxes.ids)],
                'account_id': account.id if account else False,
            })],
        }

        # Lien vers le SO si la version d'Odoo le supporte
        if 'invoice_user_id' in self.env['account.move']._fields:
            invoice_vals['invoice_user_id'] = sub.user_id.id if sub.user_id else self.env.uid

        return self.env['account.move'].create(invoice_vals)

    # ========================================================================
    # MAIL & PDF
    # ========================================================================

    def _render_email_subject(self):
        if self.cloture_avant_occupation:
            return (f"Annulation de votre réservation de box - "
                    f"{self.subscription_id.name}")
        return f"Clôture de votre contrat de location box - {self.subscription_id.name}"

    def _render_email_body(self):
        """Construit le HTML du mail récap (utilisé en aperçu et envoi réel)."""
        return self._render_email_preview()

    def _render_email_preview(self):
        """Construit l'aperçu HTML du mail."""
        if self.cloture_avant_occupation:
            return self._render_email_annulation()

        billable = self.prorata_line_ids.filtered('will_create_invoice')

        # Bloc détail par box (si demandé)
        if self.detail_per_box and len(billable) > 0:
            rows = ""
            for pl in billable:
                rows += f"""
                <tr>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0;">
                        {pl.product_id.name or '?'}
                    </td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0;">
                        {pl.period_start.strftime('%d/%m/%Y')} → {pl.period_end.strftime('%d/%m/%Y')}
                    </td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; text-align: right;">
                        {pl.amount_ttc:.2f} €
                    </td>
                </tr>
                """
            details_block = f"""
            <h3 style="color: #C91E18; margin-top: 25px;">Détail des prorata</h3>
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #e0e0e0;">
                <thead>
                    <tr style="background-color: #C91E18; color: white;">
                        <th style="padding: 10px 12px; text-align: left;">Box</th>
                        <th style="padding: 10px 12px; text-align: left;">Période</th>
                        <th style="padding: 10px 12px; text-align: right;">Montant TTC</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """
        else:
            details_block = ""

        partner_name = self.partner_id.name or '[Client]'
        end_date_str = (self.effective_end_date or self.end_date).strftime('%d/%m/%Y') \
            if (self.effective_end_date or self.end_date) else '-'
        total_str = f"{self.prorata_total_ttc:.2f}"
        contract_name = self.subscription_id.name

        # Bloc préavis (si applicable)
        notice_block = ""
        if self.notice_date:
            notice_str = self.notice_date.strftime('%d/%m/%Y')
            if not self.notice_respected and self.legal_end_date:
                requested_str = self.end_date.strftime('%d/%m/%Y') if self.end_date else '-'
                legal_str = self.legal_end_date.strftime('%d/%m/%Y')
                notice_block = f"""
                <div style="background-color: #fff8e1; border-left: 4px solid #f57c00;
                            padding: 15px 20px; margin: 20px 0;">
                    <p style="margin: 0 0 5px 0; font-weight: bold; color: #e65100;">
                        ⚠️ Note concernant le préavis
                    </p>
                    <p style="margin: 0; font-size: 13px;">
                        Vous nous avez prévenus le <strong>{notice_str}</strong>
                        d'une fin souhaitée au <strong>{requested_str}</strong>.<br/>
                        Conformément aux conditions générales (préavis de
                        {self.notice_period_days} jours), la facturation est
                        étendue jusqu'au <strong>{legal_str}</strong>.
                    </p>
                </div>
                """
            else:
                notice_block = f"""
                <p style="margin: 10px 0; font-size: 13px; color: #555;">
                    <em>Préavis reçu le <strong>{notice_str}</strong> — délai
                    de {self.notice_period_days} jours respecté ✓</em>
                </p>
                """

        return f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #C91E18; padding: 20px 30px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 22px;">
            LOLIRINE GARDE-MEUBLE
        </h1>
        <p style="color: #ffffff; margin: 5px 0 0 0; font-size: 13px; opacity: 0.9;">
            Confirmation de clôture de contrat
        </p>
    </div>

    <div style="padding: 30px; background-color: #ffffff;">
        <p>Bonjour <strong>{partner_name}</strong>,</p>

        <p>Nous vous confirmons la clôture de votre contrat de location de box
        <strong>{contract_name}</strong>, à la date du <strong>{end_date_str}</strong>.</p>

        {notice_block}

        <div style="background-color: #f9f9f9; border-left: 4px solid #C91E18;
                    padding: 15px 20px; margin: 20px 0;">
            <p style="margin: 0 0 5px 0; font-weight: bold; color: #C91E18;">
                💰 Solde final
            </p>
            <p style="margin: 0; font-size: 18px;">
                Montant total à régler : <strong>{total_str} €</strong>
            </p>
        </div>

        {details_block}

        <p style="margin-top: 25px;">
            Une (ou plusieurs) facture(s) vous sera/seront envoyée(s) séparément
            pour le solde de cette clôture.
        </p>

        <p>Nous vous remercions pour la confiance que vous nous avez accordée
        et restons à votre disposition pour tout besoin futur.</p>

        <div style="background-color: #f4f4f4; padding: 15px 20px; margin: 25px 0;
                    border-radius: 4px;">
            <p style="margin: 0 0 8px 0; font-weight: bold;">❓ Questions ?</p>
            <p style="margin: 0; font-size: 13px;">
                📧 <a href="mailto:gardemeublelolirine@gmail.com"
                      style="color: #C91E18;">gardemeublelolirine@gmail.com</a><br/>
                📞 <a href="tel:+32497444146" style="color: #C91E18;">0497 / 444 146</a>
            </p>
        </div>

        <p>Cordialement,<br/>
        <strong>L'équipe Lolirine Garde-meuble</strong></p>
    </div>

    <div style="background-color: #f4f4f4; padding: 15px 30px; text-align: center;
                font-size: 11px; color: #888;">
        <p style="margin: 0;">
            <strong>Lolirine SRL</strong> — BCE BE 0650.891.279<br/>
            gardemeublelolirine@gmail.com — 0497/444 146
        </p>
    </div>
</div>
        """

    def _render_email_annulation(self):
        """Mail spécifique à l'annulation avant mise à disposition.

        Ne parle ni de préavis, ni de restitution de box, ni de décompte de
        caution : rien de tout cela ne s'applique puisque le box n'a jamais
        été occupé.
        """
        partner_name = self.partner_id.name or '[Client]'
        contract_name = self.subscription_id.name
        end_date_str = self.end_date.strftime('%d/%m/%Y') if self.end_date else '-'
        total_str = f"{self.prorata_total_ttc:.2f}"

        rows = ""
        for pl in self.prorata_line_ids.filtered('will_create_invoice'):
            rows += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0;">
                    {pl.note or pl.product_id.name or '?'}
                </td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0;
                           text-align: right;">
                    {pl.amount_ttc:.2f} €
                </td>
            </tr>
            """

        # Mention de la renonciation à l'indemnité, si elle n'est pas réclamée
        if self.appliquer_indemnite_4_4:
            indemnite_block = """
            <p style="margin: 15px 0; font-size: 13px;">
                Conformément à l'article 4.4 de nos conditions générales, une
                indemnité correspondant à quinze jours de redevance est due en
                cas d'annulation avant la mise à disposition du box. Elle
                figure dans le détail ci-dessus.
            </p>
            """
        else:
            indemnite_block = """
            <p style="margin: 15px 0; font-size: 13px;">
                L'article 4.4 de nos conditions générales prévoit, en cas
                d'annulation avant la mise à disposition du box, une indemnité
                correspondant à quinze jours de redevance en plus des frais de
                dossier. <strong>Nous y renonçons</strong> : seuls les frais de
                dossier vous sont facturés.
            </p>
            """

        return f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #C91E18; padding: 20px 30px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 22px;">
            LOLIRINE GARDE-MEUBLE
        </h1>
        <p style="color: #ffffff; margin: 5px 0 0 0; font-size: 13px; opacity: 0.9;">
            Annulation de votre réservation
        </p>
    </div>

    <div style="padding: 30px; background-color: #ffffff;">
        <p>Bonjour <strong>{partner_name}</strong>,</p>

        <p>Nous avons bien pris note de votre demande d'annulation et avons
        clôturé votre dossier <strong>{contract_name}</strong> à la date du
        <strong>{end_date_str}</strong>. Le box n'ayant pas été mis à votre
        disposition, aucun loyer ne vous est facturé.</p>

        {indemnite_block}

        <div style="background-color: #f9f9f9; border-left: 4px solid #C91E18;
                    padding: 15px 20px; margin: 20px 0;">
            <p style="margin: 0 0 5px 0; font-weight: bold; color: #C91E18;">
                💰 Montant dû
            </p>
            <p style="margin: 0; font-size: 18px;">
                <strong>{total_str} €</strong>
            </p>
        </div>

        <h3 style="color: #C91E18; margin-top: 25px;">Détail</h3>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #e0e0e0;">
            <thead>
                <tr style="background-color: #C91E18; color: white;">
                    <th style="padding: 10px 12px; text-align: left;">Objet</th>
                    <th style="padding: 10px 12px; text-align: right;">Montant TTC</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <p style="margin-top: 25px;">
            La facture correspondante vous sera envoyée séparément.
        </p>

        <p>Nous restons bien entendu à votre disposition le jour où votre
        projet se concrétisera, et vous souhaitons bonne continuation.</p>

        <div style="background-color: #f4f4f4; padding: 15px 20px; margin: 25px 0;
                    border-radius: 4px;">
            <p style="margin: 0 0 8px 0; font-weight: bold;">❓ Questions ?</p>
            <p style="margin: 0; font-size: 13px;">
                📧 <a href="mailto:gardemeublelolirine@gmail.com"
                      style="color: #C91E18;">gardemeublelolirine@gmail.com</a><br/>
                📞 <a href="tel:+32497444146" style="color: #C91E18;">0497 / 444 146</a>
            </p>
        </div>

        <p>Cordialement,<br/>
        <strong>L'équipe Lolirine Garde-meuble</strong></p>
    </div>

    <div style="background-color: #f4f4f4; padding: 15px 30px; text-align: center;
                font-size: 11px; color: #888;">
        <p style="margin: 0;">
            <strong>Lolirine SRL</strong> — BCE BE 0650.891.279<br/>
            gardemeublelolirine@gmail.com — 0497/444 146
        </p>
    </div>
</div>
        """

    def _send_recap_email(self, invoices):
        """Envoie le mail récap au client (ou en mode test)."""
        body_html = self._render_email_body()
        subject = self._render_email_subject()

        # Destinataire
        if self.test_mode:
            email_to = self.test_email or self.env.user.email
        else:
            email_to = self.partner_id.email
            if not email_to:
                raise UserError(_(
                    "Le client n'a pas d'adresse email — impossible d'envoyer "
                    "le mail récap. Décoche 'Envoyer le mail' ou ajoute "
                    "l'email du client."
                ))

        # PDF en pièce jointe si société
        attachment_ids = []
        if self._should_attach_pdf():
            attachment_ids = self._generate_pdf_attachment()

        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_from': self.company_id.email_formatted or 'noreply@lolirine.be',
            'email_to': email_to,
            'attachment_ids': [(6, 0, attachment_ids)],
            'auto_delete': False,
        })
        mail.send()

    def _should_attach_pdf(self):
        """Détermine si le PDF officiel de clôture doit être joint.

        Le rapport de clôture décrit un préavis, une date de libération et une
        restitution de box : rien de tout cela ne s'applique à une annulation
        avant mise à disposition. On ne le joint donc pas dans ce mode, pour
        ne pas envoyer au client un document qui contredit le mail.
        """
        self.ensure_one()
        if not self.attach_pdf_for_companies:
            return False
        if not self.partner_id.is_company:
            return False
        if self.cloture_avant_occupation:
            return False
        return True

    def _generate_pdf_attachment(self):
        """Génère le PDF de clôture et retourne son ID en attachment."""
        report = self.env.ref(
            'lolirine_invoice.action_report_contract_close',
            raise_if_not_found=False
        )
        if not report:
            _logger.warning("Rapport PDF de clôture introuvable")
            return []

        try:
            pdf_content, _content_type = report._render_qweb_pdf(
                report.report_name, [self.id]
            )
        except Exception:
            _logger.exception("Erreur génération PDF de clôture")
            return []

        import base64
        filename = f"Cloture_{self.subscription_id.name or self.id}.pdf".replace('/', '_')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': pdf_content if isinstance(pdf_content, str)
                     else base64.b64encode(pdf_content),
            'res_model': 'lolirine.contract.close.wizard',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return [attachment.id]

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _build_final_message(self, invoices, email_sent):
        """Construit le HTML du récapitulatif final."""
        invoices_html = ""
        for inv in invoices:
            invoices_html += f"""
            <li>
                Facture <strong>{inv.name or 'Brouillon'}</strong> — 
                {inv.amount_total:.2f} € (état : {inv.state})
            </li>
            """

        email_status = ""
        if self.send_email:
            if email_sent:
                target = self.test_email if self.test_mode else self.partner_id.email
                email_status = f"<li>✓ Mail récap envoyé à <strong>{target}</strong></li>"
            else:
                email_status = "<li>❌ Erreur lors de l'envoi du mail récap (voir logs)</li>"
        else:
            email_status = "<li>☐ Mail récap non envoyé (option décochée)</li>"

        if self.cloture_avant_occupation:
            titre = "✅ Annulation enregistrée"
            intro = (
                f"Le contrat <strong>{self.subscription_id.name}</strong> a été "
                f"clôturé sans mise à disposition du box, à la date du "
                f"<strong>{self.end_date.strftime('%d/%m/%Y')}</strong>.<br/>"
                f"Aucun loyer n'a été facturé"
                + (", l'indemnité de l'article 4.4 a été appliquée."
                   if self.appliquer_indemnite_4_4
                   else " et il a été renoncé à l'indemnité de l'article 4.4.")
            )
        else:
            titre = "✅ Clôture effectuée avec succès"
            intro = (
                f"Le contrat <strong>{self.subscription_id.name}</strong> a été "
                f"clôturé à la date du "
                f"<strong>{self.end_date.strftime('%d/%m/%Y')}</strong>."
            )

        return f"""
<div style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #28a745;">{titre}</h2>

    <p>{intro}</p>

    <h3 style="color: #C91E18;">Actions réalisées :</h3>
    <ul>
        {invoices_html}
        <li>✓ Contrat passé en état <strong>'Churn'</strong> (clôturé)</li>
        <li>✓ Box automatiquement libérées (via hook de synchro)</li>
        {email_status}
    </ul>

    <p style="margin-top: 25px; padding: 15px; background-color: #fff3cd;
              border-left: 4px solid #ffc107;">
        <strong>⚠️ Prochaine étape :</strong> Les factures sont en
        <strong>brouillon</strong>. Pense à les valider et les envoyer au client.
    </p>
</div>
        """

    def _reload_view(self):
        """Recharge la vue courante du wizard."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.contract.close.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_view_invoices(self):
        """Ouvre la liste des factures créées."""
        self.ensure_one()
        if not self.created_invoice_ids:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factures créées'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.created_invoice_ids.ids)],
        }


# ============================================================================
# LIGNE DE PRORATA (TransientModel)
# ============================================================================

class LolirineContractCloseProrataLine(models.TransientModel):
    _name = 'lolirine.contract.close.prorata.line'
    _description = "Ligne de prorata pour clôture de contrat"

    wizard_id = fields.Many2one(
        'lolirine.contract.close.wizard',
        required=True,
        ondelete='cascade',
    )
    order_line_id = fields.Many2one(
        'sale.order.line',
        string="Ligne d'origine",
        required=False,
        help="Ligne du contrat à l'origine de ce montant. Peut être vide "
             "lorsque le montant ne correspond à aucune ligne du contrat "
             "(frais de dossier absents du contrat, par exemple)."
    )
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        required=True,
    )
    monthly_price = fields.Float(
        string="Loyer mensuel",
    )
    period_start = fields.Date(
        string="Début période",
    )
    period_end = fields.Date(
        string="Fin période",
    )
    days_in_month = fields.Integer(
        string="Jours dans le mois",
    )
    days_to_bill = fields.Integer(
        string="Jours à facturer",
    )
    amount_ht = fields.Float(
        string="Montant HT",
        digits=(16, 2),
    )
    amount_ttc = fields.Float(
        string="Montant TTC",
        digits=(16, 2),
    )
    note = fields.Char(
        string="Note",
    )
    will_create_invoice = fields.Boolean(
        string="Sera facturé",
        default=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
    )
