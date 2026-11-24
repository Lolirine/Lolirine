# -*- coding: utf-8 -*-
"""Factures fournisseurs de l'activité piscine.

Les factures reçues par Peppol (ou par e-mail) arrivent toutes dans le journal d'achats
par défaut de la société, celui du garde-meuble. Quand le fournisseur est un fournisseur
du Pool Store (barème de port renseigné sur sa fiche), la facture encore en brouillon est
basculée dans le journal « Achats Piscines ».
"""
from odoo import api, models

JOURNAL_ACHATS_PISCINE = 'PISC'


class AccountMovePoolPurchase(models.Model):
    _inherit = 'account.move'

    def _pool_router_journal_achats(self):
        for move in self:
            if move.state != 'draft' or move.move_type not in ('in_invoice', 'in_refund'):
                continue
            partner = move.partner_id.commercial_partner_id
            if not partner or not partner.pool_bareme_port:
                continue
            journal = self.env['account.journal'].search([
                ('code', '=', JOURNAL_ACHATS_PISCINE), ('type', '=', 'purchase'),
                ('company_id', '=', move.company_id.id)], limit=1)
            if not journal or move.journal_id == journal:
                continue
            # Seulement depuis le journal d'achats par défaut : un choix manuel est respecté
            societe = move.company_id
            peppol = 'peppol_purchase_journal_id' in societe._fields and societe.peppol_purchase_journal_id
            defaut = peppol or self.env['account.journal'].search([
                ('type', '=', 'purchase'), ('company_id', '=', move.company_id.id)], limit=1)
            if move.journal_id != defaut:
                continue
            move.with_context(pool_routage_journal=True).journal_id = journal

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._pool_router_journal_achats()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if 'partner_id' in vals and not self.env.context.get('pool_routage_journal'):
            self._pool_router_journal_achats()
        return res
