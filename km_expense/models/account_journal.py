# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import fields, models
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _km_dashboard_main_journal(self):
        """Journal d'achats principal de la societe : il porte le bloc IK du garde-meuble."""
        return self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.company.id),
        ], order='sequence, id', limit=1)

    def _km_dashboard_pool_journal(self):
        """Journal « Achats Piscines » (code PISC) : il porte le bloc IK du Pool Store."""
        return self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('code', '=', 'PISC'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    def _km_activite(self):
        """Activite des trajets affiches sur la carte de ce journal."""
        self.ensure_one()
        return 'piscine' if (self.code or '').upper() in ('PISC', 'POOL') else 'garde_meuble'

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        """Ajoute le resume des indemnites kilometriques sur la carte du journal d'achats
        principal (garde-meuble) et sur celle du journal « Achats Piscines » (Pool Store)."""
        super()._fill_sale_purchase_dashboard_data(dashboard_data)
        for journal in self.filtered(lambda j: j.type == 'purchase'):
            dashboard_data.setdefault(journal.id, {})['km_show'] = False
        try:
            main = self._km_dashboard_main_journal()
            pool = self._km_dashboard_pool_journal()
            today = fields.Date.context_today(self)
            Trajet = self.env['km.trajet']
            for journal in (main | pool):
                if journal.id not in dashboard_data:
                    continue
                activite = journal._km_activite()
                if activite == 'piscine':
                    dom_activite = [('activite', '=', 'piscine')]
                elif pool:
                    dom_activite = [('activite', '!=', 'piscine')]
                else:
                    dom_activite = []
                year_dom = [
                    ('date', '>=', date(today.year, 1, 1)),
                    ('date', '<=', date(today.year, 12, 31)),
                    ('company_id', 'in', [False, journal.company_id.id]),
                ] + dom_activite
                trajets = Trajet.search(year_dom + [('state', '!=', 'refuse')])
                a_valider = trajets.filtered(lambda t: t.state in ('brouillon', 'soumis'))
                non_compta = trajets.filtered(
                    lambda t: t.state in ('valide', 'rembourse') and not t.comptabilise
                    and t.montant_indemnite > 0)
                currency = journal.company_id.currency_id
                dashboard_data[journal.id].update({
                    'km_show': True,
                    'km_year': today.year,
                    'km_total_km': formatLang(self.env, sum(trajets.mapped('distance')), digits=1),
                    'km_total_amount': formatLang(
                        self.env, sum(trajets.mapped('montant_indemnite')), currency_obj=currency),
                    'km_to_validate': len(a_valider),
                    'km_to_validate_amount': formatLang(
                        self.env, sum(a_valider.mapped('montant_indemnite')), currency_obj=currency),
                    'km_not_posted': len(non_compta),
                    'km_not_posted_amount': formatLang(
                        self.env, sum(non_compta.mapped('montant_indemnite')), currency_obj=currency),
                })
        except Exception:
            _logger.exception("Bloc indemnites km du tableau de bord comptable")

    # ------------------------------------------------------------------
    # Liens du bloc
    # ------------------------------------------------------------------
    def _km_action(self, context=None):
        action = self.env['ir.actions.act_window']._for_xml_id('km_expense.km_trajet_action_dashboard')
        ctx = {'search_default_annee_courante': 1}
        ctx.update(context or {})
        if len(self) == 1:
            # la carte cliquee decide de l'activite affichee
            if self._km_activite() == 'piscine':
                ctx['search_default_activite_piscine'] = 1
                ctx['default_activite'] = 'piscine'
            elif self._km_dashboard_pool_journal():
                ctx['search_default_activite_garde_meuble'] = 1
        action['context'] = ctx
        return action

    def action_open_km_dashboard(self):
        return self._km_action()

    def action_open_km_to_validate(self):
        action = self._km_action({'search_default_brouillon': 1, 'search_default_a_valider': 1})
        action['view_mode'] = 'list,form,graph,pivot'
        action['views'] = [(False, 'list'), (False, 'form'), (False, 'graph'), (False, 'pivot')]
        return action

    def action_open_km_not_posted(self):
        action = self._km_action({'search_default_valide': 1, 'search_default_non_comptabilise': 1})
        action['view_mode'] = 'list,form,graph,pivot'
        action['views'] = [(False, 'list'), (False, 'form'), (False, 'graph'), (False, 'pivot')]
        return action
