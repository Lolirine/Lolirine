# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class KmExpense(models.Model):
    """Feuille mensuelle d'indemnites kilometriques"""
    _name = 'km.expense'
    _description = 'Feuille d\'Indemnites Kilometriques'
    _order = 'date_debut desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employe',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    
    date_debut = fields.Date(
        string='Date de debut',
        required=True,
        tracking=True,
    )
    date_fin = fields.Date(
        string='Date de fin',
        required=True,
        tracking=True,
    )
    
    trajet_ids = fields.One2many(
        'km.trajet',
        'expense_sheet_id',
        string='Trajets',
    )
    
    # Totaux
    total_trajets = fields.Integer(
        string='Nombre de trajets',
        compute='_compute_totaux',
        store=True,
    )
    total_km = fields.Float(
        string='Total kilometres',
        compute='_compute_totaux',
        store=True,
        digits=(10, 1),
    )
    total_indemnites = fields.Float(
        string='Total indemnites (EUR)',
        compute='_compute_totaux',
        store=True,
        digits=(10, 2),
    )
    
    # Cumul annuel
    cumul_km_annee = fields.Float(
        string='Cumul KM annee',
        compute='_compute_cumul_annuel',
        digits=(10, 1),
    )
    cumul_indemnites_annee = fields.Float(
        string='Cumul indemnites annee (EUR)',
        compute='_compute_cumul_annuel',
        digits=(10, 2),
    )
    
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('soumis', 'Soumis'),
        ('approuve', 'Approuve'),
        ('refuse', 'Refuse'),
        ('paye', 'Paye'),
    ], string='Statut', default='brouillon', tracking=True)
    
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Devise',
    )

    @api.depends('employee_id', 'date_debut', 'date_fin')
    def _compute_name(self):
        for record in self:
            if record.employee_id and record.date_debut:
                mois = record.date_debut.strftime('%B %Y').capitalize()
                record.name = f"IK - {record.employee_id.name} - {mois}"
            else:
                record.name = 'Nouvelle feuille IK'

    @api.depends('trajet_ids', 'trajet_ids.distance', 'trajet_ids.montant_indemnite')
    def _compute_totaux(self):
        for record in self:
            trajets = record.trajet_ids.filtered(lambda t: t.state in ('valide', 'rembourse'))
            record.total_trajets = len(trajets)
            record.total_km = sum(trajets.mapped('distance'))
            record.total_indemnites = sum(trajets.mapped('montant_indemnite'))

    @api.depends('employee_id', 'date_fin')
    def _compute_cumul_annuel(self):
        for record in self:
            if not record.employee_id or not record.date_fin:
                record.cumul_km_annee = 0.0
                record.cumul_indemnites_annee = 0.0
                continue
            
            debut_annee = date(record.date_fin.year, 1, 1)
            trajets = self.env['km.trajet'].search([
                ('employee_id', '=', record.employee_id.id),
                ('date', '>=', debut_annee),
                ('date', '<=', record.date_fin),
                ('state', 'in', ('valide', 'rembourse')),
            ])
            record.cumul_km_annee = sum(trajets.mapped('distance'))
            record.cumul_indemnites_annee = sum(trajets.mapped('montant_indemnite'))

    def action_ajouter_trajets(self):
        """Ajouter les trajets de la periode"""
        self.ensure_one()
        trajets = self.env['km.trajet'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_debut),
            ('date', '<=', self.date_fin),
            ('state', '=', 'valide'),
            ('expense_sheet_id', '=', False),
        ])
        trajets.write({'expense_sheet_id': self.id})
        return True

    def action_soumettre(self):
        """Soumettre la feuille pour approbation"""
        for record in self:
            if not record.trajet_ids:
                raise UserError("Aucun trajet a soumettre.")
            record.state = 'soumis'

    def action_approuver(self):
        """Approuver la feuille"""
        for record in self:
            record.state = 'approuve'

    def action_refuser(self):
        """Refuser la feuille"""
        for record in self:
            record.state = 'refuse'

    def action_payer(self):
        """Marquer comme paye"""
        for record in self:
            record.state = 'paye'
            record.trajet_ids.write({'state': 'rembourse'})

    def action_brouillon(self):
        """Remettre en brouillon"""
        for record in self:
            if record.state == 'paye':
                raise UserError("Une feuille payee ne peut pas etre remise en brouillon.")
            record.state = 'brouillon'


# Ajout du lien inverse dans km.trajet
class KmTrajetExpenseSheet(models.Model):
    _inherit = 'km.trajet'
    
    expense_sheet_id = fields.Many2one(
        'km.expense',
        string='Feuille IK',
        copy=False,
    )
