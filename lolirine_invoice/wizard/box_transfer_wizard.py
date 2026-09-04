# -*- coding: utf-8 -*-
"""Wizard de transfert de box Lolirine.

Le client ne part pas : il change de box. On facture donc en une seule
facture le prorata de l'ancien box (jusqu'au transfert) et celui du nouveau
box (du transfert a la fin du cycle de facturation), puis on bascule la
ligne d'abonnement.

Reutilise les helpers de lolirine.contract.close.wizard sans les modifier :
- _get_last_billed_date(sol)
- _compute_prorata_amount(price, start, end)

Points de vigilance couverts :
- next_invoice_date pousse au cycle suivant (sinon la recurrence refacture
  le mois deja proratise)
- avoir automatique si le mois en cours etait deja facture sur l'ancien box
- synchronisation storage.box (fr) ET product.template.storage_status (en)
- ajustement de la caution via deposit_amount / deposit_months
"""

import base64
import calendar
import logging
from datetime import date, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# storage.box.status (FR) -> product.template.storage_status (EN).
# On ne mappe que les deux valeurs certaines : la selection cote produit est
# plus pauvre que celle de storage.box.
FREE_STATUSES = ('disponible', 'bientot_dispo')


class LolirineBoxTransferWizard(models.TransientModel):
    """Assistant de transfert d'un locataire d'un box vers un autre."""
    _name = 'lolirine.box.transfer.wizard'
    _description = "Assistant de transfert de box Lolirine"

    # ========================================================================
    # CONTEXTE
    # ========================================================================

    subscription_id = fields.Many2one(
        'sale.order', string="Contrat", required=True, readonly=True,
        default=lambda self: self.env.context.get('active_id'))
    partner_id = fields.Many2one(
        'res.partner', related='subscription_id.partner_id', readonly=True)
    company_id = fields.Many2one(
        'res.company', related='subscription_id.company_id', readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True)

    # ========================================================================
    # ANCIEN BOX
    # ========================================================================

    candidate_line_ids = fields.Many2many(
        'sale.order.line', compute='_compute_candidate_lines',
        string="Lignes eligibles")
    old_order_line_id = fields.Many2one(
        'sale.order.line', string="Box quitte", required=True,
        domain="[('id', 'in', candidate_line_ids)]",
        help="Ligne d'abonnement du box que le client libere.")
    old_product_id = fields.Many2one(
        'product.product', related='old_order_line_id.product_id', readonly=True)
    old_price_unit = fields.Float(
        related='old_order_line_id.price_unit', readonly=True,
        string="Loyer actuel HT")

    # ========================================================================
    # NOUVEAU BOX
    # ========================================================================

    available_box_ids = fields.Many2many(
        'product.product', compute='_compute_available_boxes',
        string="Box disponibles")
    new_box_product_id = fields.Many2one(
        'product.product', string="Nouveau box", required=True,
        domain="[('id', 'in', available_box_ids)]",
        help="Box repris par le client. Liste construite depuis storage.box "
             "filtre sur le statut 'Disponible'.")
    new_price_unit = fields.Float(
        string="Loyer du nouveau box HT",
        compute='_compute_new_price', store=True, readonly=False,
        help="Pre-rempli avec le prix de vente du box. Modifiable si tu "
             "accordes un tarif particulier.")
    new_price_ttc_info = fields.Char(
        string="Soit TVAC", compute='_compute_new_price_info')

    # ========================================================================
    # DATES ET PREAVIS
    # ========================================================================

    new_start_date = fields.Date(
        string="Prise du nouveau box", required=True,
        default=fields.Date.context_today,
        help="Premier jour d'occupation du nouveau box.")
    old_end_date = fields.Date(
        string="Liberation de l'ancien box", required=True,
        compute='_compute_old_end_default', store=True, readonly=False,
        help="Dernier jour d'occupation de l'ancien box. Un demenagement "
             "prend du temps : tant qu'il n'est pas termine le client "
             "occupe les deux box, et la periode de chevauchement est "
             "facturee sur les deux.")
    apply_notice = fields.Boolean(
        string="Appliquer le preavis de 15 jours",
        default=False,
        help="Decoche par defaut : le client reste locataire, il n'y a pas "
             "de perte de revenu a compenser. Coche pour prolonger malgre "
             "tout la facturation de l'ancien box jusqu'a la fin du "
             "preavis, au-dela de sa liberation reelle.")
    notice_date = fields.Date(
        string="Date d'avertissement par le client",
        default=fields.Date.context_today)
    notice_period_days = fields.Integer(
        string="Delai de preavis (jours)", default=15)
    legal_end_date = fields.Date(
        string="Fin de preavis", compute='_compute_legal_end_date')
    effective_old_end_date = fields.Date(
        string="Ancien box facture jusqu'au",
        compute='_compute_effective_old_end',
        help="Date de liberation saisie, ou fin du preavis si l'option "
             "est cochee.")
    overlap_days = fields.Integer(
        string="Jours de chevauchement", compute='_compute_effective_old_end',
        help="Nombre de jours pendant lesquels le client occupe les deux "
             "box. Ces jours sont factures sur les deux.")
    cycle_end_date = fields.Date(
        string="Fin du cycle couvert", compute='_compute_cycle_end')
    next_invoice_date_after = fields.Date(
        string="Prochaine facture apres transfert",
        compute='_compute_cycle_end',
        help="Date a laquelle la recurrence reprendra. Le wizard la repousse "
             "pour eviter une refacturation du mois deja proratise.")

    # ========================================================================
    # MODE CONTRAT
    # ========================================================================

    contract_mode = fields.Selection(
        [('same_contract', "Meme contrat (remplacement de la ligne)"),
         ('new_contract', "Cloture de l'ancien + nouveau contrat")],
        string="Traitement du contrat", default='same_contract', required=True,
        help="Meme contrat : le numero CTR est conserve, seule la ligne du "
             "box change. Nouveau contrat : l'ancien passe en churn et un "
             "nouvel abonnement est cree.")

    validation_mode = fields.Selection(
        [('signature', "Signature en ligne obligatoire (portail)"),
         ('manual', "Envoi simple, je confirme moi-meme ensuite")],
        string="Validation du nouveau contrat", default='signature',
        help="Signature : le client signe le devis depuis le portail, ce qui "
             "confirme l'abonnement. Envoi simple : le devis part par mail et "
             "tu le confirmes toi-meme.")
    send_quotation = fields.Boolean(
        string="Envoyer le devis au client", default=True,
        help="Envoie le devis du nouveau box par mail des l'encodage du "
             "transfert.")

    # ========================================================================
    # CAUTION
    # ========================================================================

    adjust_deposit = fields.Boolean(
        string="Ajuster la caution", default=True)
    old_deposit = fields.Monetary(
        string="Caution ancien box", compute='_compute_deposit',
        currency_field='currency_id')
    new_deposit = fields.Monetary(
        string="Caution nouveau box", compute='_compute_deposit',
        currency_field='currency_id')
    deposit_delta = fields.Monetary(
        string="Ecart de caution", compute='_compute_deposit',
        currency_field='currency_id')
    deposit_message = fields.Char(compute='_compute_deposit')

    # ========================================================================
    # PRORATA
    # ========================================================================

    prorata_line_ids = fields.One2many(
        'lolirine.box.transfer.prorata.line', 'wizard_id',
        string="Lignes de prorata")
    prorata_total_ht = fields.Monetary(
        compute='_compute_totals', currency_field='currency_id',
        string="Total HT")
    prorata_total_ttc = fields.Monetary(
        compute='_compute_totals', currency_field='currency_id',
        string="Total TTC")
    has_calculation = fields.Boolean(compute='_compute_has_calculation')
    warning_html = fields.Html(compute='_compute_warning', sanitize=False)

    # ========================================================================
    # ENVOI
    # ========================================================================

    send_email = fields.Boolean(string="Envoyer le mail au client", default=True)
    test_mode = fields.Boolean(string="Mode test", default=False)
    test_email = fields.Char(
        string="Email de test", default=lambda self: self.env.user.email or '')
    email_preview_html = fields.Html(
        string="Apercu du mail", compute='_compute_email_preview', sanitize=False)

    # ========================================================================
    # ETAPES
    # ========================================================================

    confirmation_step = fields.Selection(
        [('initial', 'Initial'), ('preview', 'Apercu'),
         ('confirm', 'Confirmation'), ('done', 'Termine')],
        default='initial', readonly=True)
    confirmation_text = fields.Char(string="Pour confirmer, tape : TRANSFERER")
    created_invoice_ids = fields.Many2many('account.move', readonly=True)
    new_subscription_id = fields.Many2one('sale.order', readonly=True)
    final_message = fields.Html(readonly=True)

    # ========================================================================
    # COMPUTES - SELECTION DES BOX
    # ========================================================================

    @api.depends('subscription_id')
    def _compute_candidate_lines(self):
        helper = self._helper()
        for wiz in self:
            lines = wiz.subscription_id.order_line.filtered(
                lambda l: helper._is_line_recurring(l))
            wiz.candidate_line_ids = [(6, 0, lines.ids)]

    @api.depends('subscription_id')
    def _compute_available_boxes(self):
        """Liste les box reellement disponibles via storage.box.

        On ne se fie pas a product.template.is_storage_box, qui est a True
        sur des produits qui ne sont pas des box.
        """
        boxes = self.env['storage.box'].search([
            ('status', '=', 'disponible'),
            ('is_personal_use', '=', False),
            ('product_tmpl_id', '!=', False),
        ])
        products = boxes.mapped('product_tmpl_id.product_variant_id')
        for wiz in self:
            wiz.available_box_ids = [(6, 0, products.ids)]

    # ========================================================================
    # COMPUTES - PRIX ET CAUTION
    # ========================================================================

    @api.depends('new_box_product_id')
    def _compute_new_price(self):
        for wiz in self:
            wiz.new_price_unit = wiz.new_box_product_id.list_price or 0.0

    @api.depends('new_price_unit', 'old_order_line_id')
    def _compute_new_price_info(self):
        for wiz in self:
            taxes = wiz.old_order_line_id.tax_ids
            if taxes and wiz.new_price_unit:
                res = taxes.compute_all(
                    wiz.new_price_unit, currency=wiz.currency_id, quantity=1,
                    product=wiz.new_box_product_id, partner=wiz.partner_id)
                wiz.new_price_ttc_info = "%.2f EUR TVAC / mois" % res['total_included']
            else:
                wiz.new_price_ttc_info = ""

    def _box_deposit(self, product):
        """Caution d'un box : deposit_amount, sinon deposit_months x loyer."""
        box = self._storage_box(product)
        if not box:
            return 0.0
        if box.deposit_amount:
            return box.deposit_amount
        return (box.deposit_months or 0) * (box.price_monthly or 0.0)

    @api.depends('old_product_id', 'new_box_product_id')
    def _compute_deposit(self):
        for wiz in self:
            old = wiz._box_deposit(wiz.old_product_id) if wiz.old_product_id else 0.0
            new = wiz._box_deposit(wiz.new_box_product_id) if wiz.new_box_product_id else 0.0
            wiz.old_deposit = old
            wiz.new_deposit = new
            wiz.deposit_delta = new - old
            if not old and not new:
                wiz.deposit_message = ""
            elif abs(new - old) < 0.01:
                wiz.deposit_message = "Caution inchangee (%.2f EUR)" % new
            elif new > old:
                wiz.deposit_message = (
                    "Complement de caution a reclamer : %.2f EUR "
                    "(%.2f -> %.2f)" % (new - old, old, new))
            else:
                wiz.deposit_message = (
                    "Quote-part de caution a restituer : %.2f EUR "
                    "(%.2f -> %.2f)" % (old - new, old, new))

    # ========================================================================
    # COMPUTES - DATES
    # ========================================================================

    @api.depends('notice_date', 'notice_period_days')
    def _compute_legal_end_date(self):
        for wiz in self:
            if wiz.notice_date and wiz.notice_period_days:
                wiz.legal_end_date = wiz.notice_date + timedelta(
                    days=wiz.notice_period_days)
            else:
                wiz.legal_end_date = False

    @api.depends('new_start_date')
    def _compute_old_end_default(self):
        """Par defaut, liberation le jour meme de la prise du nouveau box
        (transfert eclair). L'utilisateur repousse cette date si le
        demenagement s'etale."""
        for wiz in self:
            wiz.old_end_date = wiz.new_start_date

    @api.depends('old_end_date', 'new_start_date', 'apply_notice',
                 'legal_end_date')
    def _compute_effective_old_end(self):
        for wiz in self:
            end = wiz.old_end_date
            if wiz.apply_notice and wiz.legal_end_date and end:
                end = max(end, wiz.legal_end_date)
            wiz.effective_old_end_date = end
            if end and wiz.new_start_date and end >= wiz.new_start_date:
                wiz.overlap_days = (end - wiz.new_start_date).days + 1
            else:
                wiz.overlap_days = 0

    @api.depends('new_start_date', 'effective_old_end_date', 'subscription_id')
    def _compute_cycle_end(self):
        for wiz in self:
            if not wiz.new_start_date:
                wiz.cycle_end_date = False
                wiz.next_invoice_date_after = False
                continue
            pivot = max(wiz.new_start_date,
                        wiz.effective_old_end_date or wiz.new_start_date)
            last_day = calendar.monthrange(pivot.year, pivot.month)[1]
            cycle_end = date(pivot.year, pivot.month, last_day)
            wiz.cycle_end_date = cycle_end

            nxt = cycle_end + timedelta(days=1)
            sub_next = wiz.subscription_id.next_invoice_date
            day = sub_next.day if sub_next else 20
            day = min(day, calendar.monthrange(nxt.year, nxt.month)[1])
            wiz.next_invoice_date_after = date(nxt.year, nxt.month, day)

    # ========================================================================
    # COMPUTES - DIVERS
    # ========================================================================

    @api.depends('prorata_line_ids.amount_ht', 'prorata_line_ids.amount_ttc')
    def _compute_totals(self):
        for wiz in self:
            wiz.prorata_total_ht = sum(wiz.prorata_line_ids.mapped('amount_ht'))
            wiz.prorata_total_ttc = sum(wiz.prorata_line_ids.mapped('amount_ttc'))

    @api.depends('prorata_line_ids')
    def _compute_has_calculation(self):
        for wiz in self:
            wiz.has_calculation = bool(wiz.prorata_line_ids)

    @api.depends('prorata_line_ids', 'prorata_total_ttc', 'apply_notice',
                 'overlap_days', 'old_end_date', 'new_start_date')
    def _compute_warning(self):
        for wiz in self:
            msgs = []
            if wiz.has_calculation and wiz.prorata_total_ttc < 0:
                msgs.append(
                    "Le total est negatif (%.2f EUR). Une facture client ne "
                    "peut pas etre postee avec un total negatif : cree plutot "
                    "un avoir manuel apres le transfert." % wiz.prorata_total_ttc)
            if wiz.overlap_days:
                msgs.append(
                    "Chevauchement de %d jour(s), du %s au %s : le client "
                    "occupe les deux box et les deux sont factures sur "
                    "cette periode.%s"
                    % (wiz.overlap_days,
                       wiz.new_start_date.strftime('%d/%m/%Y'),
                       wiz.effective_old_end_date.strftime('%d/%m/%Y'),
                       " Preavis applique." if wiz.apply_notice else ""))
            if wiz.old_end_date and wiz.new_start_date \
                    and wiz.old_end_date < wiz.new_start_date:
                msgs.append(
                    "L'ancien box est libere avant la prise du nouveau : "
                    "le client n'occupe aucun box du %s au %s."
                    % ((wiz.old_end_date + timedelta(days=1)).strftime('%d/%m/%Y'),
                       (wiz.new_start_date - timedelta(days=1)).strftime('%d/%m/%Y')))
            if wiz.prorata_line_ids.filtered(lambda l: l.kind == 'credit'):
                msgs.append(
                    "Le mois en cours etait deja facture sur l'ancien box : "
                    "une ligne d'avoir compense les jours non occupes.")
            if not msgs:
                wiz.warning_html = False
                continue
            items = "".join("<li>%s</li>" % m for m in msgs)
            wiz.warning_html = (
                "<div style='background:#fff8e1;border-left:4px solid #f57c00;"
                "padding:12px 18px;'><strong>A verifier</strong>"
                "<ul style='margin:6px 0 0 0;'>%s</ul></div>" % items)

    @api.depends('prorata_line_ids', 'send_email')
    def _compute_email_preview(self):
        for wiz in self:
            if not wiz.has_calculation:
                wiz.email_preview_html = (
                    "<p style='color:#888;font-style:italic;padding:20px;'>"
                    "Lance le calcul pour voir l'apercu du mail.</p>")
            else:
                wiz.email_preview_html = wiz._render_email_body()

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _helper(self):
        """Enregistrement en memoire du wizard de cloture, pour reutiliser
        ses helpers de calcul sans dupliquer le code ni ecrire en base."""
        vals = {}
        if len(self) == 1 and self.subscription_id:
            vals['subscription_id'] = self.subscription_id.id
        return self.env['lolirine.contract.close.wizard'].new(vals)

    def _storage_box(self, product):
        if not product:
            return self.env['storage.box']
        return self.env['storage.box'].search(
            [('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1)

    def _amount_ttc(self, amount_ht, product):
        taxes = self.old_order_line_id.tax_ids
        if not taxes:
            return amount_ht
        res = taxes.compute_all(
            amount_ht, currency=self.currency_id, quantity=1,
            product=product, partner=self.partner_id)
        return res['total_included']

    # ========================================================================
    # ETAPE 1 : CALCUL
    # ========================================================================

    def action_compute_prorata(self):
        self.ensure_one()
        self._check_inputs()
        self.prorata_line_ids.unlink()

        helper = self._helper()
        sub = self.subscription_id
        sol = self.old_order_line_id
        lines = []

        # -- ANCIEN BOX ------------------------------------------------------
        last_billed = helper._get_last_billed_date(sol)
        old_end = self.effective_old_end_date

        if last_billed and last_billed > old_end:
            # Mois deja facture au-dela du depart : avoir sur les jours
            # non occupes.
            c_start = old_end + timedelta(days=1)
            c_end = last_billed
            amount, days, dim = helper._compute_prorata_amount(
                sol.price_unit, c_start, c_end)
            lines.append((0, 0, {
                'kind': 'credit',
                'product_id': sol.product_id.id,
                'order_line_id': sol.id,
                'monthly_price': sol.price_unit,
                'period_start': c_start,
                'period_end': c_end,
                'days_in_month': dim,
                'days_to_bill': days,
                'amount_ht': -amount,
                'amount_ttc': -self._amount_ttc(amount, sol.product_id),
                'note': "Avoir : jours non occupes deja factures",
            }))
        else:
            p_start = (last_billed + timedelta(days=1)) if last_billed \
                else sub.start_date
            if p_start and p_start <= old_end:
                amount, days, dim = helper._compute_prorata_amount(
                    sol.price_unit, p_start, old_end)
                lines.append((0, 0, {
                    'kind': 'old',
                    'product_id': sol.product_id.id,
                    'order_line_id': sol.id,
                    'monthly_price': sol.price_unit,
                    'period_start': p_start,
                    'period_end': old_end,
                    'days_in_month': dim,
                    'days_to_bill': days,
                    'amount_ht': amount,
                    'amount_ttc': self._amount_ttc(amount, sol.product_id),
                    'note': "Ancien box, jusqu'a sa liberation",
                }))

        # -- NOUVEAU BOX -----------------------------------------------------
        n_start = self.new_start_date
        n_end = self.cycle_end_date
        if n_start <= n_end:
            amount, days, dim = helper._compute_prorata_amount(
                self.new_price_unit, n_start, n_end)
            lines.append((0, 0, {
                'kind': 'new',
                'product_id': self.new_box_product_id.id,
                'monthly_price': self.new_price_unit,
                'period_start': n_start,
                'period_end': n_end,
                'days_in_month': dim,
                'days_to_bill': days,
                'amount_ht': amount,
                'amount_ttc': self._amount_ttc(amount, self.new_box_product_id),
                'note': "Nouveau box, jusqu'a la fin du cycle",
            }))

        if not lines:
            raise UserError(_(
                "Aucune ligne de prorata a creer. Verifie les dates : il se "
                "peut que la periode soit deja entierement facturee."))

        self.write({
            'prorata_line_ids': lines,
            'confirmation_step': 'preview',
        })
        return self._reload_view()

    def _check_inputs(self):
        if not self.old_order_line_id:
            raise UserError(_("Selectionne le box que le client quitte."))
        if not self.new_box_product_id:
            raise UserError(_("Selectionne le nouveau box."))
        if self.new_box_product_id == self.old_product_id:
            raise UserError(_("L'ancien et le nouveau box sont identiques."))
        if not self.new_start_date:
            raise UserError(_("Saisis la date de prise du nouveau box."))
        if not self.old_end_date:
            raise UserError(_(
                "Saisis la date de liberation de l'ancien box. Si le "
                "demenagement dure plusieurs jours, c'est le dernier jour "
                "ou le client occupe encore l'ancien box."))
        if self.subscription_id.start_date \
                and self.new_start_date < self.subscription_id.start_date:
            raise UserError(_(
                "La date du transfert (%s) est anterieure au debut du "
                "contrat (%s).") % (self.new_start_date,
                                    self.subscription_id.start_date))
        if self.new_price_unit <= 0:
            raise UserError(_("Le loyer du nouveau box doit etre positif."))
        # Le nouveau box ne doit pas etre pris ailleurs
        box = self._storage_box(self.new_box_product_id)
        if box and box.status != 'disponible':
            raise UserError(_(
                "Le box %s n'est pas disponible (statut : %s).")
                % (box.name, box.status))

    # ========================================================================
    # ETAPE 2 : CONFIRMATION
    # ========================================================================

    def action_request_confirmation(self):
        self.ensure_one()
        if not self.has_calculation:
            raise UserError(_("Lance d'abord le calcul du prorata."))
        self.confirmation_step = 'confirm'
        return self._reload_view()

    def action_send_preview_to_self(self):
        self.ensure_one()
        if not self.has_calculation:
            raise UserError(_("Lance d'abord le calcul du prorata."))
        target = self.test_email or self.env.user.email
        if not target:
            raise UserError(_("Aucune adresse de test definie."))
        self.env['mail.mail'].sudo().create({
            'subject': "[TEST] %s" % self._render_email_subject(),
            'body_html': self._render_email_body(),
            'email_from': self.company_id.email_formatted or 'noreply@lolirine.be',
            'email_to': target,
            'auto_delete': False,
        }).send()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _("Apercu envoye"),
                       'message': _("Mail envoye a %s") % target,
                       'type': 'success'},
        }

    # ========================================================================
    # ETAPE 3 : EXECUTION
    # ========================================================================

    def action_execute_transfer(self):
        self.ensure_one()
        if (self.confirmation_text or '').strip().upper() != 'TRANSFERER':
            raise UserError(_(
                "Saisie incorrecte.\n\nPour confirmer le transfert, saisis "
                "exactement le mot 'TRANSFERER' en majuscules."))

        sub = self.subscription_id
        invoice = self._create_transfer_invoice()

        if self.contract_mode == 'same_contract':
            new_sub = self._apply_same_contract()
        else:
            new_sub = self._apply_new_contract()

        self._sync_boxes(new_sub)

        if self.adjust_deposit:
            self._adjust_deposit(new_sub)

        email_sent = False
        if self.send_email:
            try:
                self._send_transfer_email(invoice)
                email_sent = True
            except Exception:
                _logger.exception("Erreur envoi mail de transfert")

        sub.message_post(body=_(
            "Transfert de box : %s -> %s.<br/>"
            "Nouveau box occupe a partir du %s, ancien box facture "
            "jusqu'au %s (%d jour(s) de chevauchement).<br/>"
            "Facture de prorata : %s.<br/>Mail : %s"
        ) % (
            self.old_product_id.display_name,
            self.new_box_product_id.display_name,
            self.new_start_date.strftime('%d/%m/%Y'),
            self.effective_old_end_date.strftime('%d/%m/%Y'),
            self.overlap_days,
            invoice.name or 'brouillon',
            "envoye" if email_sent else "non envoye",
        ))

        self.write({
            'created_invoice_ids': [(6, 0, invoice.ids)],
            'new_subscription_id': new_sub.id if new_sub != sub else False,
            'final_message': self._build_final_message(invoice, new_sub, email_sent),
            'confirmation_step': 'done',
        })
        return self._reload_view()

    # ------------------------------------------------------------------ #

    def _create_transfer_invoice(self):
        """Une seule facture en brouillon portant toutes les lignes."""
        sub = self.subscription_id
        inv_lines = []
        for pl in self.prorata_line_ids:
            product = pl.product_id
            account = product.product_tmpl_id._get_product_accounts()['income']
            label = "%s\n%s du %s au %s (%d jour(s))" % (
                product.display_name,
                "Avoir" if pl.kind == 'credit' else "Prorata",
                pl.period_start.strftime('%d/%m/%Y'),
                pl.period_end.strftime('%d/%m/%Y'),
                pl.days_to_bill,
            )
            inv_lines.append((0, 0, {
                'name': label,
                'product_id': product.id,
                'quantity': 1,
                'price_unit': pl.amount_ht,
                'tax_ids': [(6, 0, self.old_order_line_id.tax_ids.ids)],
                'account_id': account.id if account else False,
            }))

        vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': max(self.new_start_date,
                                self.effective_old_end_date or self.new_start_date),
            'invoice_origin': sub.name,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': inv_lines,
        }
        if 'invoice_user_id' in self.env['account.move']._fields:
            vals['invoice_user_id'] = sub.user_id.id if sub.user_id else self.env.uid
        return self.env['account.move'].create(vals)

    def _apply_same_contract(self):
        """Remplace la ligne du box sur le contrat existant."""
        sub = self.subscription_id
        sol = self.old_order_line_id
        # Lire les taxes AVANT toute suppression : apres unlink la ligne
        # n'existe plus et tax_ids renverrait vide.
        tax_ids = sol.tax_ids.ids

        # Ordre critique : retirer avant d'ajouter, sinon la contrainte
        # lolirine_storage_availability voit deux box en conflit.
        try:
            sol.unlink()
        except Exception:
            # Ligne deja facturee : Odoo refuse la suppression, on neutralise.
            sol.write({'product_uom_qty': 0})
            _logger.info("Ligne %s non supprimable, quantite mise a 0", sol.id)

        sub.order_line = [(0, 0, {
            'product_id': self.new_box_product_id.id,
            'name': self.new_box_product_id.display_name,
            'product_uom_qty': 1,
            'price_unit': self.new_price_unit,
            'tax_ids': [(6, 0, tax_ids)],
        })]
        sub.write({'next_invoice_date': self.next_invoice_date_after})
        return sub

    def _apply_new_contract(self):
        """Cloture l'ancien contrat et en cree un nouveau pour le box repris."""
        sub = self.subscription_id
        sub.write({'end_date': self.effective_old_end_date})
        if hasattr(sub, 'set_close'):
            sub.set_close()
        else:
            sub.write({'subscription_state': '6_churn', 'next_invoice_date': False})

        vals = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'origin': sub.name,
            'start_date': self.new_start_date,
            'next_invoice_date': self.next_invoice_date_after,
            'order_line': [(0, 0, {
                'product_id': self.new_box_product_id.id,
                'name': self.new_box_product_id.display_name,
                'product_uom_qty': 1,
                'price_unit': self.new_price_unit,
                'tax_ids': [(6, 0, self.old_order_line_id.tax_ids.ids)],
            })],
        }
        for fname in ('sale_order_template_id', 'plan_id', 'pricelist_id',
                      'payment_term_id', 'user_id', 'team_id',
                      'fiscal_position_id'):
            if fname in sub._fields and sub[fname]:
                vals[fname] = sub[fname].id

        if 'validity_date' in self.env['sale.order']._fields:
            vals['validity_date'] = self.new_start_date + timedelta(days=30)
        if 'require_signature' in self.env['sale.order']._fields:
            vals['require_signature'] = (self.validation_mode == 'signature')

        new_sub = self.env['sale.order'].create(vals)
        # Le devis reste en brouillon : c'est la signature du client (ou ta
        # confirmation manuelle) qui activera l'abonnement. next_invoice_date
        # est pose des maintenant pour qu'une date passee ne declenche pas
        # une facturation retroactive au moment de la confirmation.
        new_sub.write({'next_invoice_date': self.next_invoice_date_after})

        if self.send_quotation:
            self._send_quotation(new_sub)
        return new_sub

    def _send_quotation(self, new_sub):
        """Envoie le devis du nouveau box au client."""
        if self.test_mode:
            _logger.info("Mode test : devis %s non envoye au client",
                         new_sub.name)
            return
        template = self.env.ref('sale.email_template_edi_sale',
                                raise_if_not_found=False)
        if not template:
            _logger.warning("Modele de mail de devis introuvable")
            return
        try:
            template.send_mail(new_sub.id, force_send=True)
            if new_sub.state == 'draft':
                new_sub.write({'state': 'sent'})
        except Exception:
            _logger.exception("Erreur envoi du devis %s", new_sub.name)

    def _sync_boxes(self, subscription):
        """Met a jour storage.box (FR) et product.template (EN)."""
        today = fields.Date.context_today(self)

        old_box = self._storage_box(self.old_product_id)
        if old_box:
            libre_le = (self.effective_old_end_date or today) + timedelta(days=1)
            status = 'disponible' if libre_le <= today else 'bientot_dispo'
            old_box.write({
                'status': status,
                'current_partner_id': False,
                'current_subscription_id': False,
                'date_available': libre_le,
            })
            self.old_product_id.product_tmpl_id.write({
                'storage_status': 'available'
                if status in FREE_STATUSES else 'rented',
                'current_tenant_id': False,
            })

        new_box = self._storage_box(self.new_box_product_id)
        if new_box:
            # Tant que le devis n'est pas confirme, le box est reserve et non
            # loue : il sort du catalogue sans etre compte comme occupe.
            confirmed = subscription.state in ('sale', 'done')
            new_box.write({
                'status': 'occupe' if confirmed else 'reserve',
                'current_partner_id': self.partner_id.id,
                'current_subscription_id': subscription.id,
                'date_available': False,
            })
            self.new_box_product_id.product_tmpl_id.write({
                'storage_status': 'rented',
                'current_tenant_id': self.partner_id.id,
            })

    def _adjust_deposit(self, subscription):
        """Reporte l'ecart de caution sur le contrat.

        La caution n'est jamais facturee ni compensee avec un arriere :
        on ajuste le montant porte par le contrat et on signale le
        mouvement a effectuer.
        """
        if 'contract_deposit_amount' not in subscription._fields:
            return
        current = subscription.contract_deposit_amount or 0.0
        if self.contract_mode == 'same_contract':
            target = current - self.old_deposit + self.new_deposit
        else:
            target = self.new_deposit
        subscription.write({'contract_deposit_amount': target})
        if abs(self.deposit_delta) >= 0.01:
            subscription.message_post(body=_(
                "Caution ajustee suite au transfert : %.2f -> %.2f EUR. %s"
            ) % (current, target, self.deposit_message))

    # ========================================================================
    # MAIL
    # ========================================================================

    def _render_email_subject(self):
        return "Changement de box - %s" % self.subscription_id.name

    def _render_email_body(self):
        rows = ""
        for pl in self.prorata_line_ids:
            rows += (
                "<tr>"
                "<td style='padding:8px 12px;border-bottom:1px solid #e0e0e0;'>%s</td>"
                "<td style='padding:8px 12px;border-bottom:1px solid #e0e0e0;'>%s &rarr; %s</td>"
                "<td style='padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:right;'>%.2f &euro;</td>"
                "</tr>" % (
                    pl.product_id.name or '?',
                    pl.period_start.strftime('%d/%m/%Y'),
                    pl.period_end.strftime('%d/%m/%Y'),
                    pl.amount_ttc,
                ))

        deposit_block = ""
        if self.adjust_deposit and abs(self.deposit_delta) >= 0.01:
            if self.deposit_delta > 0:
                txt = ("Le nouveau box appelle une caution superieure : un "
                       "complement de <strong>%.2f &euro;</strong> vous sera "
                       "demande." % self.deposit_delta)
            else:
                txt = ("Le nouveau box appelle une caution inferieure : une "
                       "quote-part de <strong>%.2f &euro;</strong> vous sera "
                       "restituee." % abs(self.deposit_delta))
            deposit_block = (
                "<div style='background:#f9f9f9;border-left:4px solid #C91E18;"
                "padding:15px 20px;margin:20px 0;'>"
                "<p style='margin:0 0 5px 0;font-weight:bold;color:#C91E18;'>"
                "Caution</p><p style='margin:0;font-size:13px;'>%s</p></div>" % txt)

        return """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color:#C91E18;padding:20px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:22px;">LOLIRINE GARDE-MEUBLE</h1>
        <p style="color:#fff;margin:5px 0 0 0;font-size:13px;opacity:.9;">
            Confirmation de changement de box</p>
    </div>
    <div style="padding:30px;background:#fff;">
        <p>Bonjour <strong>%(partner)s</strong>,</p>
        <p>Nous vous confirmons le transfert de votre location du box
        <strong>%(old)s</strong> vers le box <strong>%(new)s</strong>.</p>
        <p>Le nouveau box est a votre disposition depuis le
        <strong>%(date)s</strong>. %(overlap)s</p>
        <p>Votre contrat <strong>%(contract)s</strong> se poursuit sans
        interruption. Le nouveau loyer mensuel s'eleve a
        <strong>%(newprice)s</strong>.</p>

        <h3 style="color:#C91E18;margin-top:25px;">Detail de la facture de transition</h3>
        <table style="width:100%%;border-collapse:collapse;border:1px solid #e0e0e0;">
            <thead><tr style="background:#C91E18;color:#fff;">
                <th style="padding:10px 12px;text-align:left;">Box</th>
                <th style="padding:10px 12px;text-align:left;">Periode</th>
                <th style="padding:10px 12px;text-align:right;">Montant TTC</th>
            </tr></thead>
            <tbody>%(rows)s</tbody>
        </table>
        <p style="margin-top:12px;font-size:18px;">
            Total : <strong>%(total).2f &euro;</strong></p>

        %(deposit)s

        <p>La facture correspondante vous parviendra separement. Les
        echeances suivantes reprendront leur rythme habituel a partir du
        <strong>%(nextinv)s</strong>.</p>

        <div style="background:#f4f4f4;padding:15px 20px;margin:25px 0;border-radius:4px;">
            <p style="margin:0 0 8px 0;font-weight:bold;">Questions ?</p>
            <p style="margin:0;font-size:13px;">
                <a href="mailto:gardemeublelolirine@gmail.com" style="color:#C91E18;">
                gardemeublelolirine@gmail.com</a><br/>
                <a href="tel:+32497444146" style="color:#C91E18;">0497 / 444 146</a></p>
        </div>
        <p>Cordialement,<br/><strong>L'equipe Lolirine Garde-meuble</strong></p>
    </div>
    <div style="background:#f4f4f4;padding:15px 30px;text-align:center;font-size:11px;color:#888;">
        <p style="margin:0;"><strong>Lolirine SRL</strong> &mdash; BCE BE 0650.891.279<br/>
        gardemeublelolirine@gmail.com &mdash; 0497/444 146</p>
    </div>
</div>
        """ % {
            'partner': self.partner_id.name or '[Client]',
            'old': self.old_product_id.name or '-',
            'new': self.new_box_product_id.name or '-',
            'date': self.new_start_date.strftime('%d/%m/%Y')
                    if self.new_start_date else '-',
            'overlap': self._overlap_sentence(),
            'contract': self.subscription_id.name,
            'newprice': self.new_price_ttc_info or '-',
            'rows': rows,
            'total': self.prorata_total_ttc,
            'deposit': deposit_block,
            'nextinv': self.next_invoice_date_after.strftime('%d/%m/%Y')
                       if self.next_invoice_date_after else '-',
        }

    def _overlap_sentence(self):
        """Phrase expliquant au client la periode ou il paie les deux box."""
        end = self.effective_old_end_date
        if not end:
            return ""
        end_str = end.strftime('%d/%m/%Y')
        if self.overlap_days > 0:
            return (
                "Le temps de votre demenagement, l'ancien box reste a votre "
                "disposition jusqu'au <strong>%s</strong> : les deux "
                "emplacements vous sont donc factures sur ces %d jour(s)."
                % (end_str, self.overlap_days))
        return ("L'ancien box est libere depuis le <strong>%s</strong>."
                % end_str)

    def _send_transfer_email(self, invoice):
        if self.test_mode:
            email_to = self.test_email or self.env.user.email
        else:
            email_to = self.partner_id.email
            if not email_to:
                raise UserError(_(
                    "Le client n'a pas d'adresse email. Decoche l'envoi ou "
                    "renseigne son adresse."))
        self.env['mail.mail'].sudo().create({
            'subject': self._render_email_subject(),
            'body_html': self._render_email_body(),
            'email_from': self.company_id.email_formatted or 'noreply@lolirine.be',
            'email_to': email_to,
            'auto_delete': False,
        }).send()

    # ========================================================================
    # RECAP
    # ========================================================================

    def _build_final_message(self, invoice, new_sub, email_sent):
        if self.contract_mode == 'same_contract':
            contract_line = (
                "Ligne remplacee sur <strong>%s</strong>, numero de contrat "
                "conserve" % self.subscription_id.name)
            box_line = "Nouveau box passe en <strong>Occupe</strong>"
        else:
            how = ("a signer par le client sur le portail"
                   if self.validation_mode == 'signature'
                   else "a confirmer manuellement")
            contract_line = (
                "Ancien contrat cloture, devis <strong>%s</strong> cree pour "
                "le nouveau box (%s)%s"
                % (new_sub.name or '-', how,
                   ", envoye au client" if self.send_quotation else ""))
            box_line = (
                "Nouveau box passe en <strong>Reserve</strong> : il ne sera "
                "marque Occupe qu'a la confirmation du devis, mais il est "
                "deja retire du catalogue")
        deposit_line = (
            "<li>%s</li>" % self.deposit_message
            if self.adjust_deposit and self.deposit_message else "")
        return """
<div style="font-family:Arial,sans-serif;padding:20px;">
    <h2 style="color:#28a745;">Transfert effectue</h2>
    <p>Le client passe du box <strong>%(old)s</strong> au box
    <strong>%(new)s</strong>.<br/>
    Nouveau box a partir du <strong>%(date)s</strong>, ancien box facture
    jusqu'au <strong>%(oldend)s</strong> (%(overlap)d jour(s) de
    chevauchement).</p>
    <h3 style="color:#C91E18;">Actions realisees</h3>
    <ul>
        <li>Facture <strong>%(inv)s</strong> creee en brouillon : %(total).2f &euro; TTC</li>
        <li>%(contract)s</li>
        <li>Prochaine facturation reportee au <strong>%(nextinv)s</strong></li>
        <li>Ancien box libere, %(boxline)s</li>
        %(deposit)s
        <li>Mail client : %(mail)s</li>
    </ul>
    <p style="margin-top:25px;padding:15px;background:#fff3cd;border-left:4px solid #ffc107;">
        <strong>A faire :</strong> valider la facture en brouillon, puis
        traiter le mouvement de caution s'il y en a un.</p>
</div>
        """ % {
            'old': self.old_product_id.display_name,
            'new': self.new_box_product_id.display_name,
            'date': self.new_start_date.strftime('%d/%m/%Y'),
            'oldend': self.effective_old_end_date.strftime('%d/%m/%Y'),
            'overlap': self.overlap_days,
            'inv': invoice.name or 'brouillon',
            'total': invoice.amount_total,
            'contract': contract_line,
            'nextinv': self.next_invoice_date_after.strftime('%d/%m/%Y')
                       if self.next_invoice_date_after else '-',
            'deposit': deposit_line,
            'mail': "envoye" if email_sent else "non envoye",
        }

    def _reload_view(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.box.transfer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_view_new_contract(self):
        """Ouvre le devis cree pour le nouveau box."""
        self.ensure_one()
        if not self.new_subscription_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouveau contrat'),
            'res_model': 'sale.order',
            'res_id': self.new_subscription_id.id,
            'view_mode': 'form',
        }

    def action_view_invoices(self):
        self.ensure_one()
        if not self.created_invoice_ids:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture de transfert'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.created_invoice_ids.ids)],
        }


class LolirineBoxTransferProrataLine(models.TransientModel):
    _name = 'lolirine.box.transfer.prorata.line'
    _description = "Ligne de prorata pour transfert de box"
    _order = 'kind desc, id'

    wizard_id = fields.Many2one(
        'lolirine.box.transfer.wizard', required=True, ondelete='cascade')
    kind = fields.Selection(
        [('old', "Ancien box"), ('new', "Nouveau box"), ('credit', "Avoir")],
        string="Nature", required=True)
    order_line_id = fields.Many2one('sale.order.line', string="Ligne d'origine")
    product_id = fields.Many2one('product.product', string="Box", required=True)
    monthly_price = fields.Float(string="Loyer mensuel HT")
    period_start = fields.Date(string="Debut")
    period_end = fields.Date(string="Fin")
    days_in_month = fields.Integer(string="Jours dans le mois")
    days_to_bill = fields.Integer(string="Jours factures")
    amount_ht = fields.Float(string="Montant HT", digits=(16, 2))
    amount_ttc = fields.Float(string="Montant TTC", digits=(16, 2))
    note = fields.Char(string="Note")
    currency_id = fields.Many2one(
        'res.currency', related='wizard_id.currency_id')
