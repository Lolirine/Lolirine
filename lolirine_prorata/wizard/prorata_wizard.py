import calendar
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveProrataWizard(models.TransientModel):
    _name = 'account.move.prorata.wizard'
    _description = 'Wizard Prorata Facturation'

    move_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        readonly=True,
    )
    date_start = fields.Date(
        string="Date de début (dépôt des effets)",
        required=True,
        help="Le prorata sera calculé de cette date jusqu'à la fin du mois.",
    )
    # Champs informatifs calculés
    days_total = fields.Integer(
        string="Jours dans le mois",
        compute='_compute_prorata_info',
    )
    days_remaining = fields.Integer(
        string="Jours facturés",
        compute='_compute_prorata_info',
    )
    ratio = fields.Float(
        string="Ratio",
        compute='_compute_prorata_info',
        digits=(6, 4),
    )
    preview_ids = fields.One2many(
        'account.move.prorata.wizard.line',
        'wizard_id',
        string="Aperçu des lignes",
        compute='_compute_preview_ids',
    )

    @api.depends('date_start')
    def _compute_prorata_info(self):
        for rec in self:
            if rec.date_start:
                days_in_month = calendar.monthrange(
                    rec.date_start.year, rec.date_start.month
                )[1]
                # Du jour de dépôt jusqu'à la fin du mois (inclus)
                days_remaining = days_in_month - rec.date_start.day + 1
                rec.days_total = days_in_month
                rec.days_remaining = days_remaining
                rec.ratio = days_remaining / days_in_month
            else:
                rec.days_total = 0
                rec.days_remaining = 0
                rec.ratio = 0.0

    @api.depends('date_start', 'move_id')
    def _compute_preview_ids(self):
        for rec in self:
            lines = []
            if rec.date_start and rec.move_id:
                for line in rec.move_id.invoice_line_ids:
                    if rec._is_excluded_line(line):
                        continue
                    new_price = round(line.price_unit * rec.ratio, 2)
                    lines.append((0, 0, {
                        'product_name': line.name[:80] if line.name else '',
                        'price_original': line.price_unit,
                        'price_prorata': new_price,
                    }))
            rec.preview_ids = lines

    def _is_excluded_line(self, line):
        """Lignes à ne pas modifier : frais de dossier, arrondi, lignes de taxe."""
        code = line.product_id.default_code or ''
        if 'FRAIS-DOSSIER' in code:
            return True
        if line.display_type in ('line_section', 'line_note'):
            return True
        if line.price_unit == -0.01:  # ligne arrondi
            return True
        if not line.product_id and 'Arrondi' in (line.name or ''):
            return True
        return False

    def action_apply(self):
        self.ensure_one()
        if not self.date_start:
            raise UserError(_("Veuillez saisir une date de début."))
        if self.move_id.state != 'draft':
            raise UserError(_("La facture doit être en brouillon pour appliquer le prorata."))

        # Calcul de la période
        days_in_month = self.days_total
        days_remaining = self.days_remaining
        ratio = self.ratio

        # Dates pour le libellé
        last_day = self.date_start.replace(day=days_in_month)
        period_label = (
            f"Prorata {self.date_start.strftime('%d/%m/%Y')} "
            f"au {last_day.strftime('%d/%m/%Y')} "
            f"({days_remaining}j/{days_in_month}j)"
        )

        modified = 0
        for line in self.move_id.invoice_line_ids:
            if self._is_excluded_line(line):
                continue

            new_price = round(line.price_unit * ratio, 2)

            # Nettoyer le libellé existant (supprimer un ancien prorata éventuel)
            name = line.name or ''
            if '\nProrata' in name:
                name = name.split('\nProrata')[0]

            line.with_context(check_move_validity=False).write({
                'price_unit': new_price,
                'name': f"{name}\n{period_label}",
            })
            modified += 1

        # Supprimer la ligne d'arrondi si présente
        for line in self.move_id.invoice_line_ids:
            if line.price_unit == -0.01 or (
                not line.product_id and 'Arrondi' in (line.name or '')
            ):
                line.with_context(check_move_validity=False).unlink()

        self.move_id.invalidate_recordset()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Prorata appliqué'),
                'message': _(
                    '%d ligne(s) mise(s) à jour — ratio %s/%s jours (%.4f)'
                ) % (modified, days_remaining, days_in_month, ratio),
                'type': 'success',
                'sticky': False,
            },
        }


class AccountMoveProrataWizardLine(models.TransientModel):
    _name = 'account.move.prorata.wizard.line'
    _description = 'Aperçu ligne prorata'

    wizard_id = fields.Many2one('account.move.prorata.wizard')
    product_name = fields.Char(string='Produit')
    price_original = fields.Float(string='Prix original', digits=(10, 2))
    price_prorata = fields.Float(string='Prix prorata', digits=(10, 2))
