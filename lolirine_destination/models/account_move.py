from odoo import models, fields, api

# IDs des comptes analytiques Destination (créés manuellement)
ANALYTIC_HANGAR = 87
ANALYTIC_APPART = 88
ANALYTIC_POOL   = 89

# Répartition légale hangar/appart
PCT_HANGAR = 89.0
PCT_APPART = 11.0


class AccountMove(models.Model):
    _inherit = 'account.move'

    destination_summary = fields.Char(
        string='Destination',
        compute='_compute_destination_summary',
        store=False,
    )
    has_hangar = fields.Boolean(compute='_compute_destination_flags', store=False)
    has_appart = fields.Boolean(compute='_compute_destination_flags', store=False)
    has_pool   = fields.Boolean(compute='_compute_destination_flags', store=False)
    has_mixed  = fields.Boolean(compute='_compute_destination_flags', store=False)

    @api.depends('invoice_line_ids.analytic_distribution')
    def _compute_destination_flags(self):
        for move in self:
            dests = set()
            for line in move.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product'
            ):
                dist = line.analytic_distribution or {}
                if str(ANALYTIC_HANGAR) in dist:
                    dests.add('hangar')
                if str(ANALYTIC_APPART) in dist:
                    dests.add('appart')
                if str(ANALYTIC_POOL) in dist:
                    dests.add('pool')
            move.has_hangar = 'hangar' in dests
            move.has_appart = 'appart' in dests
            move.has_pool   = 'pool' in dests
            move.has_mixed  = len(dests) > 1

    @api.depends('invoice_line_ids.analytic_distribution')
    def _compute_destination_summary(self):
        for move in self:
            parts = []
            if move.has_hangar:
                parts.append('🏭 Hangar')
            if move.has_appart:
                parts.append('🏠 Appart')
            if move.has_pool:
                parts.append('🏊 Pool Store')
            move.destination_summary = ' | '.join(parts) if parts else '—'

    def action_apply_hangar_appart(self):
        """Applique la répartition 89% Hangar / 11% Appartement sur toutes les lignes produit."""
        self.ensure_one()
        dist = {
            str(ANALYTIC_HANGAR): PCT_HANGAR,
            str(ANALYTIC_APPART): PCT_APPART,
        }
        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        ):
            line.analytic_distribution = dist
        return True

    def action_apply_hangar_only(self):
        """Applique 100% Hangar sur toutes les lignes produit."""
        self.ensure_one()
        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        ):
            line.analytic_distribution = {str(ANALYTIC_HANGAR): 100.0}
        return True

    def action_apply_pool_only(self):
        """Applique 100% Pool Store sur toutes les lignes produit."""
        self.ensure_one()
        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        ):
            line.analytic_distribution = {str(ANALYTIC_POOL): 100.0}
        return True

    def action_clear_destination(self):
        """Efface toutes les destinations analytiques."""
        self.ensure_one()
        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        ):
            line.analytic_distribution = {}
        return True
