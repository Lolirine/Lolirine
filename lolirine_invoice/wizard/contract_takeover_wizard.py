# -*- coding: utf-8 -*-
"""Reprise d'un contrat de garde-meuble par un autre locataire.

Le box ne change pas, le contrat (numero, tarif, plan, date de facturation)
non plus : seul le locataire change. Premier cas : CTR/2026/038, box 1D30,
repris par Mme Delzenne a M. Savigny (novembre 2026).

Ce que fait l'assistant, en une seule operation :

1. Ancien locataire : sa caution (compte 488000) est imputee sur ses factures
   restees ouvertes (option, montant modifiable). Le solde eventuel de sa
   caution reste a son nom, a lui rembourser.
2. Nouveau locataire : la caution du contrat est prelevee sur un versement
   deja recu de lui et non affecte (option, montant modifiable). Le reste du
   versement reste en avance et sera impute sur ses factures.
   Les deux mouvements passent en une seule operation diverse : aucun
   virement entre le compte courant et le compte caution n'est necessaire
   tant que les deux cautions se compensent.
3. Contrat : client, adresse de facturation et de livraison passent au nouveau
   locataire ; les factures deja emises restent au nom de l'ancien.
4. Notes : note interne du contrat (bandeau jaune) et notes des deux fiches
   contact, plus un message dans les trois historiques.
5. Plan des boxes : resynchronisation du box (locataire affiche).

Ce qu'il ne fait pas : reaffecter un versement que la banque a rattache au
mauvais client (a corriger d'abord sur la transaction bancaire), changer le
code d'acces ACT365 (bouton « Code ACT365 » du contrat).
"""
import logging

from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CAUTION_ACCOUNT_CODE = '488000'


class LolirineContractTakeoverWizard(models.TransientModel):
    _name = 'lolirine.contract.takeover.wizard'
    _description = "Reprise d'un contrat par un autre locataire"

    subscription_id = fields.Many2one(
        'sale.order', string="Contrat", required=True,
        domain="[('is_subscription', '=', True), ('state', '=', 'sale')]")
    company_id = fields.Many2one(related='subscription_id.company_id')
    currency_id = fields.Many2one(related='subscription_id.currency_id')
    old_partner_id = fields.Many2one(
        'res.partner', string="Locataire actuel",
        compute='_compute_old_partner', store=True, readonly=True)
    new_partner_id = fields.Many2one(
        'res.partner', string="Nouveau locataire", required=True,
        domain="[('id', '!=', old_partner_id)]")
    takeover_date = fields.Date(
        "Date de reprise", required=True, default=fields.Date.context_today)
    box_names = fields.Char("Box", compute='_compute_box_names')

    # Ancien locataire
    old_deposit_balance = fields.Monetary(
        "Caution disponible", compute='_compute_balances',
        help="Caution encore au nom du locataire actuel (compte 488000).")
    old_open_amount = fields.Monetary(
        "Factures ouvertes", compute='_compute_balances',
        help="Total restant du sur ses factures.")
    apply_old_deposit = fields.Boolean(
        "Imputer sa caution sur ses factures ouvertes", default=True)
    old_deposit_to_apply = fields.Monetary("Montant a imputer")

    # Nouveau locataire
    deposit_amount = fields.Monetary(
        "Caution du nouveau locataire",
        help="Par defaut, la caution prevue au contrat (deux mois de loyer).")
    new_partner_credit = fields.Monetary(
        "Versement non affecte", compute='_compute_balances',
        help="Montant deja recu du nouveau locataire et pas encore impute.")
    take_deposit_from_credit = fields.Boolean(
        "Prelever sa caution sur ce versement", default=True)

    note = fields.Text("Note", help="Ajoutee au contrat et aux deux fiches contact.")

    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if (self.env.context.get('active_model') == 'sale.order'
                and self.env.context.get('active_id') and 'subscription_id' in fields_list):
            res['subscription_id'] = self.env.context['active_id']
        return res

    @api.depends('subscription_id')
    def _compute_old_partner(self):
        for wiz in self:
            wiz.old_partner_id = wiz.subscription_id.partner_id

    def _box_products(self):
        helper = self.env['lolirine.contract.close.wizard'].new(
            {'subscription_id': self.subscription_id.id})
        return self.subscription_id.order_line.filtered(
            lambda l: helper._is_line_recurring(l)).mapped('product_id')

    def _storage_boxes(self):
        return self.env['storage.box'].search(
            [('product_tmpl_id', 'in', self._box_products().product_tmpl_id.ids)])

    @api.depends('subscription_id')
    def _compute_box_names(self):
        for wiz in self:
            wiz.box_names = ', '.join(
                p.default_code or p.name for p in wiz._box_products()) if wiz.subscription_id else False

    def _caution_account(self):
        account = self.env['account.account'].search([
            ('code', '=', CAUTION_ACCOUNT_CODE),
            ('company_ids', 'in', self.company_id.ids)], limit=1)
        if not account:
            raise UserError(_("Compte de cautions %s introuvable.") % CAUTION_ACCOUNT_CODE)
        return account

    def _receivable_account(self):
        return self.new_partner_id.with_company(self.company_id).property_account_receivable_id

    def _open_lines(self, partner, account, sign):
        """Lignes non lettrees du partenaire : sign=1 debits restant dus, sign=-1 credits."""
        if not partner:
            return self.env['account.move.line']
        domain = [
            ('partner_id', 'child_of', partner.commercial_partner_id.id),
            ('account_id', '=', account.id),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('company_id', '=', self.company_id.id),
        ]
        domain.append(('amount_residual', '>' if sign > 0 else '<', 0))
        return self.env['account.move.line'].search(domain, order='date, id')

    @api.depends('subscription_id', 'old_partner_id', 'new_partner_id')
    def _compute_balances(self):
        for wiz in self:
            wiz.old_deposit_balance = wiz.old_open_amount = wiz.new_partner_credit = 0.0
            if not wiz.subscription_id:
                continue
            caution = wiz._caution_account()
            receivable = wiz.old_partner_id.with_company(wiz.company_id).property_account_receivable_id
            wiz.old_deposit_balance = -sum(
                wiz._open_lines(wiz.old_partner_id, caution, -1).mapped('amount_residual'))
            wiz.old_open_amount = sum(
                wiz._open_lines(wiz.old_partner_id, receivable, 1).mapped('amount_residual'))
            if wiz.new_partner_id:
                wiz.new_partner_credit = -sum(
                    wiz._open_lines(wiz.new_partner_id, receivable, -1).mapped('amount_residual'))

    @api.onchange('subscription_id', 'new_partner_id')
    def _onchange_defaults(self):
        for wiz in self:
            wiz.old_deposit_to_apply = min(wiz.old_deposit_balance, wiz.old_open_amount)
            wiz.apply_old_deposit = wiz.old_deposit_to_apply > 0
            wiz.deposit_amount = wiz.subscription_id.contract_deposit_amount \
                if 'contract_deposit_amount' in wiz.subscription_id._fields else 0.0
            wiz.take_deposit_from_credit = wiz.new_partner_credit > 0
            if wiz.subscription_id and wiz.new_partner_id:
                wiz.note = _(
                    "%(date)s : contrat %(contract)s (box %(box)s) repris par %(new)s, "
                    "en remplacement de %(old)s. Les factures emises avant cette date "
                    "restent au nom de %(old)s.") % {
                        'date': fields.Date.to_string(wiz.takeover_date) if wiz.takeover_date else '',
                        'contract': wiz.subscription_id.name,
                        'box': wiz.box_names or '-',
                        'new': wiz.new_partner_id.name,
                        'old': wiz.old_partner_id.name,
                    }

    # ------------------------------------------------------------------
    def _check(self):
        self.ensure_one()
        if self.subscription_id.state != 'sale':
            raise UserError(_("Le contrat doit etre en cours."))
        if self.new_partner_id == self.old_partner_id:
            raise UserError(_("Le nouveau locataire est le locataire actuel."))
        cur = self.currency_id
        if self.apply_old_deposit and cur.compare_amounts(
                self.old_deposit_to_apply, min(self.old_deposit_balance, self.old_open_amount)) > 0:
            raise UserError(_(
                "Le montant a imputer (%.2f) depasse la caution disponible ou le montant "
                "des factures ouvertes de l'ancien locataire.") % self.old_deposit_to_apply)
        if self.take_deposit_from_credit and cur.compare_amounts(
                self.deposit_amount, self.new_partner_credit) > 0:
            raise UserError(_(
                "La caution (%.2f) depasse le versement non affecte du nouveau locataire "
                "(%.2f). Diminue le montant ou decoche l'option.")
                % (self.deposit_amount, self.new_partner_credit))

    def _post_accounting(self):
        """Une operation diverse pour les deux mouvements de caution."""
        caution = self._caution_account()
        old_recv = self.old_partner_id.with_company(self.company_id).property_account_receivable_id
        new_recv = self._receivable_account()
        old_amt = self.old_deposit_to_apply if self.apply_old_deposit else 0.0
        new_amt = self.deposit_amount if self.take_deposit_from_credit else 0.0
        if self.currency_id.is_zero(old_amt) and self.currency_id.is_zero(new_amt):
            return self.env['account.move']

        journal = self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.company_id.id)], limit=1)
        lines = []
        if old_amt > 0:
            lines += [
                (0, 0, {'account_id': caution.id, 'partner_id': self.old_partner_id.id,
                        'debit': old_amt, 'credit': 0.0,
                        'name': _("Caution %s imputee sur ses factures ouvertes") % self.old_partner_id.name}),
                (0, 0, {'account_id': old_recv.id, 'partner_id': self.old_partner_id.id,
                        'debit': 0.0, 'credit': old_amt,
                        'name': _("Imputation de la caution - reprise %s") % self.subscription_id.name}),
            ]
        if new_amt > 0:
            lines += [
                (0, 0, {'account_id': new_recv.id, 'partner_id': self.new_partner_id.id,
                        'debit': new_amt, 'credit': 0.0,
                        'name': _("Caution prelevee sur le versement recu")}),
                (0, 0, {'account_id': caution.id, 'partner_id': self.new_partner_id.id,
                        'debit': 0.0, 'credit': new_amt,
                        'name': _("Caution %s (%s)") % (self.subscription_id.name, self.box_names or '')}),
            ]
        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': self.takeover_date,
            'ref': _("Reprise %s par %s - cautions") % (self.subscription_id.name, self.new_partner_id.name),
            'line_ids': lines,
        })
        move.action_post()

        def lettrer(new_line, open_lines):
            if new_line and open_lines:
                (new_line | open_lines).reconcile()

        if old_amt > 0:
            lettrer(move.line_ids.filtered(lambda l: l.account_id == old_recv and l.credit),
                    self._open_lines(self.old_partner_id, old_recv, 1))
            lettrer(move.line_ids.filtered(lambda l: l.account_id == caution and l.debit),
                    self._open_lines(self.old_partner_id, caution, -1))
        if new_amt > 0:
            lettrer(move.line_ids.filtered(lambda l: l.account_id == new_recv and l.debit),
                    self._open_lines(self.new_partner_id, new_recv, -1))
        return move

    @staticmethod
    def _append_html(current, text):
        bloc = Markup('<p>%s</p>') % escape(text)
        return (Markup(current or '') + bloc) if current else bloc

    def action_apply(self):
        self._check()
        sub = self.subscription_id
        old, new = self.old_partner_id, self.new_partner_id

        move = self._post_accounting()

        addr = new.address_get(['invoice', 'delivery'])
        vals = {
            'partner_id': new.id,
            'partner_invoice_id': addr.get('invoice') or new.id,
            'partner_shipping_id': addr.get('delivery') or new.id,
        }
        if 'payment_token_id' in sub._fields:
            vals['payment_token_id'] = False  # carte/mandat de l'ancien locataire
        sub.write(vals)

        note = (self.note or '').strip()
        if note:
            if 'internal_note' in sub._fields:
                sub.internal_note = self._append_html(sub.internal_note, note)
            for partner in (old, new):
                partner.comment = self._append_html(partner.comment, note)

        details = [note] if note else []
        if move:
            details.append(_("Operation diverse %s : caution de l'ancien locataire imputee %.2f EUR, "
                             "caution du nouveau locataire %.2f EUR.") % (
                move.name,
                self.old_deposit_to_apply if self.apply_old_deposit else 0.0,
                self.deposit_amount if self.take_deposit_from_credit else 0.0))
        reste_old = self.old_deposit_balance - (self.old_deposit_to_apply if self.apply_old_deposit else 0.0)
        if reste_old > 0.005:
            details.append(_("Solde de caution a rembourser a %s : %.2f EUR.") % (old.name, reste_old))
        if 'act365_access_code' in sub._fields and sub.act365_access_code:
            details.append(_("Code d'acces ACT365 encore celui de l'ancien locataire : "
                             "en attribuer un nouveau (bouton « Code ACT365 »)."))
        body = Markup('<p><strong>%s</strong></p>') % _("Reprise du contrat") + Markup('').join(
            Markup('<p>%s</p>') % escape(d) for d in details)
        sub.message_post(body=body)
        old.message_post(body=body)
        new.message_post(body=body)

        boxes = self._storage_boxes()
        if boxes and hasattr(boxes, '_lolirine_sync_availability'):
            boxes._lolirine_sync_availability()
        self._box_products().product_tmpl_id.filtered(
            lambda t: 'current_tenant_id' in t._fields).write({'current_tenant_id': new.id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': sub.id,
            'view_mode': 'form',
            'target': 'current',
        }
