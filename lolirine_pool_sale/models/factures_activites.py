# -*- coding: utf-8 -*-
"""Factures séparées par activité : garde-meuble (journaux INV / MEUBL) et Pool Store (POOL / PISC)."""
from odoo import api, models
from odoo.tools.safe_eval import safe_eval

ACTIVITES = {
    # clé : (code du journal, action de base, titre)
    'ventes_gm': ('INV', 'account.action_move_out_invoice', "Factures clients garde-meuble"),
    'ventes_pool': ('POOL', 'account.action_move_out_invoice', "Factures clients Pool Store"),
    'achats_gm': ('MEUBL', 'account.action_move_in_invoice', "Factures fournisseurs garde-meuble"),
    'achats_pool': ('PISC', 'account.action_move_in_invoice', "Factures fournisseurs Pool Store"),
}


class AccountMoveActivites(models.Model):
    _inherit = 'account.move'

    @api.model
    def _lolirine_action_factures(self, cle):
        code, base, titre = ACTIVITES[cle]
        journal = self.env['account.journal'].search(
            [('code', '=', code), ('company_id', 'in', self.env.companies.ids)], limit=1)
        action = self.env['ir.actions.act_window']._for_xml_id(base)
        action['name'] = titre
        dom = action.get('domain') or []
        if isinstance(dom, str):
            dom = safe_eval(dom)
        action['domain'] = list(dom) + [('journal_id.code', '=', code)]
        ctx = action.get('context') or {}
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)
        ctx = dict(ctx)
        if journal:
            ctx['default_journal_id'] = journal.id
        action['context'] = ctx
        action.pop('path', None)
        return action
