# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ApartmentGenerateRentWizard(models.TransientModel):
    _name = 'apartment.generate.rent.wizard'
    _description = 'Assistant de génération des loyers'

    lease_id = fields.Many2one(
        'apartment.lease',
        string='Bail',
        required=True,
        domain="[('state', '=', 'active')]",
    )
    property_id = fields.Many2one(
        related='lease_id.property_id',
        string='Bien',
        readonly=True,
    )
    tenant_id = fields.Many2one(
        related='lease_id.tenant_id',
        string='Locataire',
        readonly=True,
    )
    current_rent = fields.Float(
        related='lease_id.rent_amount',
        string='Loyer actuel',
        readonly=True,
    )
    charges = fields.Float(
        related='lease_id.charges_amount',
        string='Charges',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    
    generation_mode = fields.Selection([
        ('single', 'Mois unique'),
        ('range', 'Période'),
        ('remaining', 'Jusqu\'à fin de bail'),
    ], string='Mode de génération', default='single', required=True)
    
    month = fields.Selection([
        ('01', 'Janvier'),
        ('02', 'Février'),
        ('03', 'Mars'),
        ('04', 'Avril'),
        ('05', 'Mai'),
        ('06', 'Juin'),
        ('07', 'Juillet'),
        ('08', 'Août'),
        ('09', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre'),
    ], string='Mois', default=lambda self: fields.Date.today().strftime('%m'))
    
    year = fields.Char(
        string='Année',
        default=lambda self: fields.Date.today().strftime('%Y'),
    )
    
    date_from = fields.Date(string='Du')
    date_to = fields.Date(string='Au')
    
    skip_existing = fields.Boolean(
        string='Ignorer les loyers existants',
        default=True,
        help="Si coché, ne génère pas de loyer pour les périodes déjà couvertes."
    )
    
    preview_count = fields.Integer(
        string='Nombre de loyers à générer',
        compute='_compute_preview',
        readonly=True,
    )
    preview_total = fields.Float(
        string='Montant total',
        compute='_compute_preview',
        readonly=True,
    )
    
    @api.depends('lease_id', 'generation_mode', 'month', 'year', 'date_from', 'date_to', 'skip_existing')
    def _compute_preview(self):
        for wizard in self:
            periods = wizard._get_periods_to_generate()
            wizard.preview_count = len(periods)
            if wizard.lease_id:
                monthly_total = wizard.lease_id.rent_amount + wizard.lease_id.charges_amount
                wizard.preview_total = monthly_total * len(periods)
            else:
                wizard.preview_total = 0
    
    def _get_periods_to_generate(self):
        """Retourne la liste des périodes (date_start, date_end) à générer."""
        self.ensure_one()
        periods = []
        
        if not self.lease_id:
            return periods
        
        if self.generation_mode == 'single':
            if self.month and self.year:
                try:
                    year = int(self.year)
                    month = int(self.month)
                    date_start = fields.Date.today().replace(year=year, month=month, day=1)
                    date_end = date_start + relativedelta(months=1, days=-1)
                    periods.append((date_start, date_end))
                except (ValueError, TypeError):
                    pass
        
        elif self.generation_mode == 'range':
            if self.date_from and self.date_to:
                current = self.date_from.replace(day=1)
                while current <= self.date_to:
                    date_start = current
                    date_end = current + relativedelta(months=1, days=-1)
                    periods.append((date_start, date_end))
                    current += relativedelta(months=1)
        
        elif self.generation_mode == 'remaining':
            lease = self.lease_id
            if lease.end_date:
                # Commencer au prochain mois
                current = fields.Date.today().replace(day=1)
                if fields.Date.today().day > 1:
                    current += relativedelta(months=1)
                
                while current <= lease.end_date:
                    date_start = current
                    date_end = current + relativedelta(months=1, days=-1)
                    if date_end > lease.end_date:
                        date_end = lease.end_date
                    periods.append((date_start, date_end))
                    current += relativedelta(months=1)
        
        # Filtrer les périodes existantes si demandé
        if self.skip_existing and periods:
            existing_rents = self.env['apartment.rent'].search([
                ('lease_id', '=', self.lease_id.id),
                ('state', '!=', 'cancelled'),
            ])
            existing_periods = set()
            for rent in existing_rents:
                existing_periods.add((rent.period_start, rent.period_end))
            
            periods = [p for p in periods if p not in existing_periods]
        
        return periods
    
    def action_generate(self):
        """Génère les loyers pour les périodes sélectionnées."""
        self.ensure_one()
        
        if not self.lease_id:
            raise UserError(_("Veuillez sélectionner un bail."))
        
        periods = self._get_periods_to_generate()
        
        if not periods:
            raise UserError(_("Aucun loyer à générer. Vérifiez les dates ou les loyers existants."))
        
        rent_ids = []
        for period_start, period_end in periods:
            rent = self.env['apartment.rent'].create({
                'lease_id': self.lease_id.id,
                'period_start': period_start,
                'period_end': period_end,
                'rent_amount': self.lease_id.rent_amount,
                'charges_amount': self.lease_id.charges_amount,
                'state': 'pending',
            })
            rent_ids.append(rent.id)
        
        # Retourner l'action pour voir les loyers créés
        return {
            'name': _('Loyers générés'),
            'type': 'ir.actions.act_window',
            'res_model': 'apartment.rent',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', rent_ids)],
            'target': 'current',
        }
    
    @api.onchange('generation_mode')
    def _onchange_generation_mode(self):
        if self.generation_mode == 'range':
            today = fields.Date.today()
            self.date_from = today.replace(day=1)
            self.date_to = today.replace(day=1) + relativedelta(months=3, days=-1)
