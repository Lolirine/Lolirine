# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _search_default_journal(self):
        """Etend la selection du journal par defaut pour tenir compte de la
        preference eventuellement configuree sur le partenaire.

        Ordre de resolution:
        1. Si un partenaire est defini et qu'il a un journal prefere du bon
           type (achat pour in_invoice/in_refund, vente pour out_*), on l'utilise.
        2. Sinon, comportement standard Odoo (super).

        On respecte scrupuleusement les contraintes de la methode originale:
        - domaine de societe
        - type de journal compatible avec le move_type
        - devise coherente si specifiee
        """
        partner = self.partner_id
        if partner:
            # On regarde d'abord si le partenaire a une preference dans la
            # societe courante (les champs sont company_dependent).
            company = self.company_id or self.env.company
            journal_types = self._get_valid_journal_types()

            preferred = None
            if 'purchase' in journal_types:
                preferred = partner.with_company(company).property_purchase_journal_id
            elif 'sale' in journal_types:
                preferred = partner.with_company(company).property_sale_journal_id

            if preferred:
                # Verifier que le journal prefere est bien valide dans le contexte
                # (bonne societe, bon type, devise compatible si applicable).
                domain = [
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', 'in', journal_types),
                    ('id', '=', preferred.id),
                ]
                if self.env.cache.contains(self, self._fields['currency_id']):
                    currency_id = (
                        self.currency_id.id
                        or self.env.context.get('default_currency_id')
                    )
                    if currency_id and currency_id != company.currency_id.id:
                        domain.append(('currency_id', '=', currency_id))

                journal = self.env['account.journal'].search(domain, limit=1)
                if journal:
                    return journal
                # Si le journal prefere n'est plus valide (societe/type change,
                # journal desactive...), on retombe silencieusement sur le
                # comportement standard plutot que de lever une erreur.

        return super()._search_default_journal()
