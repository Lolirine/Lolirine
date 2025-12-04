# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class KmExpenseGenerateWizard(models.TransientModel):
    """Wizard pour générer une feuille d'indemnités kilométriques"""
    _name = 'km.expense.generate.wizard'
    _description = 'Assistant de génération de feuille IK'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        default=lambda self: self.env.user.employee_id,
    )
    
    periode = fields.Selection([
        ('mois_precedent', 'Mois précédent'),
        ('mois_courant', 'Mois courant'),
        ('trimestre', 'Trimestre précédent'),
        ('personnalise', 'Période personnalisée'),
    ], string='Période', default='mois_precedent', required=True)
    
    date_debut = fields.Date(
        string='Date de début',
        compute='_compute_dates',
        store=True,
        readonly=False,
    )
    date_fin = fields.Date(
        string='Date de fin',
        compute='_compute_dates',
        store=True,
        readonly=False,
    )
    
    nombre_trajets = fields.Integer(
        string='Trajets trouvés',
        compute='_compute_trajets',
    )
    total_km = fields.Float(
        string='Total km',
        compute='_compute_trajets',
    )
    total_indemnites = fields.Float(
        string='Total indemnités (€)',
        compute='_compute_trajets',
    )

    @api.depends('periode')
    def _compute_dates(self):
        today = date.today()
        for wizard in self:
            if wizard.periode == 'mois_precedent':
                premier_mois_prec = (today - relativedelta(months=1)).replace(day=1)
                wizard.date_debut = premier_mois_prec
                wizard.date_fin = today.replace(day=1) - relativedelta(days=1)
            elif wizard.periode == 'mois_courant':
                wizard.date_debut = today.replace(day=1)
                wizard.date_fin = (today + relativedelta(months=1)).replace(day=1) - relativedelta(days=1)
            elif wizard.periode == 'trimestre':
                trimestre_actuel = (today.month - 1) // 3
                if trimestre_actuel == 0:
                    # Q4 de l'année précédente
                    wizard.date_debut = date(today.year - 1, 10, 1)
                    wizard.date_fin = date(today.year - 1, 12, 31)
                else:
                    premier_mois_trim = (trimestre_actuel - 1) * 3 + 1
                    wizard.date_debut = date(today.year, premier_mois_trim, 1)
                    dernier_mois_trim = trimestre_actuel * 3
                    wizard.date_fin = (date(today.year, dernier_mois_trim, 1) + 
                                      relativedelta(months=1) - relativedelta(days=1))
            else:
                # personnalise : garder les dates existantes ou mettre des valeurs par défaut
                if not wizard.date_debut:
                    wizard.date_debut = today.replace(day=1)
                if not wizard.date_fin:
                    wizard.date_fin = today

    @api.depends('employee_id', 'date_debut', 'date_fin')
    def _compute_trajets(self):
        for wizard in self:
            if not wizard.employee_id or not wizard.date_debut or not wizard.date_fin:
                wizard.nombre_trajets = 0
                wizard.total_km = 0.0
                wizard.total_indemnites = 0.0
                continue
            
            trajets = self.env['km.trajet'].search([
                ('employee_id', '=', wizard.employee_id.id),
                ('date', '>=', wizard.date_debut),
                ('date', '<=', wizard.date_fin),
                ('state', '=', 'valide'),
                ('expense_sheet_id', '=', False),
            ])
            wizard.nombre_trajets = len(trajets)
            wizard.total_km = sum(trajets.mapped('distance'))
            wizard.total_indemnites = sum(trajets.mapped('montant_indemnite'))

    def action_generer(self):
        """Génère la feuille d'indemnités kilométriques"""
        self.ensure_one()
        
        if self.nombre_trajets == 0:
            raise UserError(
                "Aucun trajet validé sans feuille IK pour cette période.\n"
                "Vérifiez que vos trajets sont bien validés."
            )
        
        # Création de la feuille
        feuille = self.env['km.expense'].create({
            'employee_id': self.employee_id.id,
            'date_debut': self.date_debut,
            'date_fin': self.date_fin,
        })
        
        # Ajout des trajets
        feuille.action_ajouter_trajets()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Feuille IK',
            'res_model': 'km.expense',
            'res_id': feuille.id,
            'view_mode': 'form',
            'target': 'current',
        }
