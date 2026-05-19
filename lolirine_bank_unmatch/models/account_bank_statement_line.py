# -*- coding: utf-8 -*-
import logging
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_open_unmatch_wizard(self):
        """Ouvre le wizard de confirmation pour annuler l'attribution
        d'une transaction bancaire (vue formulaire — single record)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Annuler l'attribution bancaire"),
            'res_model': 'lolirine.bank.unmatch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bank_line_ids': [(6, 0, [self.id])],
            },
        }

    def _do_unmatch_attribution(self):
        """Logique d'annulation : remet la transaction en suspense, sans partenaire.
        Délettre les éventuelles écritures réconciliées, replace la contrepartie
        sur le compte d'attente du journal, retire le partner_id du move et de
        la bank line elle-même."""
        self.ensure_one()
        move = self.move_id
        journal = self.journal_id
        bank_account = journal.default_account_id
        suspense_account = journal.suspense_account_id

        if not suspense_account:
            raise UserError(_(
                "Le journal '%s' n'a pas de compte suspense configuré. "
                "Configuration impossible.",
            ) % journal.name)
        if not bank_account:
            raise UserError(_(
                "Le journal '%s' n'a pas de compte par défaut configuré.",
            ) % journal.name)

        # 1) Délettrer les écritures éventuellement réconciliées
        matched = move.line_ids.filtered(lambda l: l.matching_number)
        if matched:
            matched.remove_move_reconcile()

        # 2) Passer le move en draft pour pouvoir le modifier
        if move.state == 'posted':
            move.button_draft()

        # 3) Modifier la (ou les) ligne(s) contrepartie vers le compte suspense
        #    et retirer le partner_id
        counter_lines = move.line_ids.filtered(
            lambda l: l.account_id != bank_account
        )
        if counter_lines:
            counter_lines.with_context(check_move_validity=False).write({
                'account_id': suspense_account.id,
                'partner_id': False,
                'name': self.payment_ref or _('À rapprocher'),
            })

        # 4) Retirer partner_id du move ET de la bank line
        move.write({'partner_id': False})
        self.write({'partner_id': False})

        # 5) Reposter le move
        move.action_post()

        # 6) Trace dans le chatter
        move.message_post(
            body=_(
                "Attribution annulée par <strong>%s</strong>. "
                "La transaction a été remise en suspense pour ré-attribution "
                "via le widget de rapprochement bancaire.",
            ) % self.env.user.name,
        )

        _logger.info(
            "Bank line %s (%s, %s€) : attribution annulée par %s",
            self.id, self.date, self.amount, self.env.user.login,
        )
        return True
