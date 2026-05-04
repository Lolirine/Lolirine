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
        string="Date de fin du contrat",
        required=True,
        default=fields.Date.context_today,
        help="Date à laquelle le contrat se termine. Le prorata sera calculé "
             "sur la base de cette date (jusqu'à et y compris ce jour)."
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

    @api.depends('prorata_line_ids')
    def _compute_has_calculation(self):
        for wiz in self:
            wiz.has_calculation = bool(wiz.prorata_line_ids)

    @api.depends('prorata_line_ids', 'detail_per_box', 'send_email')
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
    # ACTION 1 : CALCULER LE PRORATA
    # ========================================================================

    def action_compute_prorata(self):
        """Calcule les lignes de prorata pour chaque ligne récurrente du contrat."""
        self.ensure_one()

        if not self.subscription_id:
            raise UserError(_("Aucun contrat sélectionné."))

        if self.end_date < (self.subscription_id.start_date or date.min):
            raise UserError(_(
                "La date de fin (%s) ne peut pas être antérieure à la date "
                "de début du contrat (%s)."
            ) % (self.end_date, self.subscription_id.start_date))

        # Vide les lignes existantes
        self.prorata_line_ids.unlink()

        # Pour chaque ligne récurrente, calcule le prorata
        new_lines = []
        for sol in self.subscription_id.order_line:
            if not self._is_line_recurring(sol):
                continue

            prorata_data = self._compute_prorata_for_line(sol)
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

    def _compute_prorata_for_line(self, sol):
        """Calcule le prorata d'une ligne d'abonnement.

        Logique :
        - On regarde la dernière facture postée pour cette ligne
        - On détermine la dernière date couverte (last_billed_until)
        - Si end_date <= last_billed_until : pas de prorata (déjà couvert)
        - Sinon : on calcule du jour suivant last_billed_until jusqu'à end_date

        Returns:
            dict avec les valeurs pour créer une lolirine.contract.close.prorata.line,
            ou None si rien à facturer.
        """
        sub = self.subscription_id

        # 1. Trouver la dernière période facturée pour ce produit
        last_billed = self._get_last_billed_date(sol)

        # 2. Période à facturer : last_billed + 1 → end_date
        period_start = last_billed + timedelta(days=1) if last_billed else sub.start_date
        period_end = self.end_date

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
        taxes = sol.tax_ids
        if taxes:
            tax_results = taxes.compute_all(
                amount_ht,
                currency=self.currency_id,
                quantity=1,
                product=sol.product_id,
                partner=self.partner_id,
            )
            amount_ttc = tax_results['total_included']
        else:
            amount_ttc = amount_ht

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

        Returns:
            date ou None si jamais facturé.
        """
        sub = self.subscription_id

        # Chercher les factures postées liées à ce SO et ce produit
        invoice_lines = self.env['account.move.line'].search([
            ('move_id.invoice_origin', '=', sub.name),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('product_id', '=', sol.product_id.id),
        ])

        if not invoice_lines:
            return None

        # En Odoo 19, la période de service d'une ligne est sur deferred_start_date
        # / deferred_end_date OU subscription_start_date / subscription_end_date
        last_dates = []
        for line in invoice_lines:
            for date_field in ('subscription_end_date',
                               'deferred_end_date'):
                if date_field in line._fields:
                    val = line[date_field]
                    if val:
                        last_dates.append(val)
                        break

        if not last_dates:
            # Fallback : prendre la date de facturation la plus récente
            return max(invoice_lines.mapped('move_id.invoice_date') or [None])

        return max(last_dates)

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
        if self.attach_pdf_for_companies and self.partner_id.is_company:
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
        # 2. Passer le contrat en churn
        # ====================================================================
        sub.write({
            'end_date': self.end_date,
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
        sub.message_post(
            body=_(
                "📋 Contrat clôturé via wizard au %s.<br/>"
                "%d facture(s) de prorata créée(s) en draft.<br/>"
                "Mail récap : %s"
            ) % (
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

        # Description avec période
        description = (
            f"{sol.name or sol.product_id.name}\n"
            f"Prorata du {prorata_line.period_start.strftime('%d/%m/%Y')} "
            f"au {prorata_line.period_end.strftime('%d/%m/%Y')} "
            f"({prorata_line.days_to_bill} jour(s))"
        )

        # Compte de produit
        account = sol.product_id.product_tmpl_id._get_product_accounts()['income']

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.end_date,
            'invoice_origin': sub.name,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'product_id': sol.product_id.id,
                'quantity': 1,
                'price_unit': prorata_line.amount_ht,
                'tax_ids': [(6, 0, sol.tax_ids.ids)],
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
        return f"Clôture de votre contrat de location box - {self.subscription_id.name}"

    def _render_email_body(self):
        """Construit le HTML du mail récap (utilisé en aperçu et envoi réel)."""
        return self._render_email_preview()

    def _render_email_preview(self):
        """Construit l'aperçu HTML du mail."""
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
        end_date_str = self.end_date.strftime('%d/%m/%Y') if self.end_date else '-'
        total_str = f"{self.prorata_total_ttc:.2f}"
        contract_name = self.subscription_id.name

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
        if self.attach_pdf_for_companies and self.partner_id.is_company:
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

        return f"""
<div style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #28a745;">✅ Clôture effectuée avec succès</h2>
    
    <p>Le contrat <strong>{self.subscription_id.name}</strong> a été clôturé
    à la date du <strong>{self.end_date.strftime('%d/%m/%Y')}</strong>.</p>
    
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
        required=True,
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
