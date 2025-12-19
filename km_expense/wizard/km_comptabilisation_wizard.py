# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class KmComptabilisationWizard(models.TransientModel):
    _name = 'km.comptabilisation.wizard'
    _description = 'Comptabilisation des indemnités kilométriques'

    # Sélection de la période
    type_periode = fields.Selection([
        ('mois', 'Mois'),
        ('trimestre', 'Trimestre'),
        ('annee', 'Année'),
        ('personnalise', 'Période personnalisée'),
    ], string='Type de période', required=True, default='mois')
    
    mois = fields.Selection([
        ('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'),
        ('4', 'Avril'), ('5', 'Mai'), ('6', 'Juin'),
        ('7', 'Juillet'), ('8', 'Août'), ('9', 'Septembre'),
        ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre'),
    ], string='Mois', default=lambda self: str(date.today().month))
    
    trimestre = fields.Selection([
        ('1', 'T1 (Jan-Mar)'),
        ('2', 'T2 (Avr-Jun)'),
        ('3', 'T3 (Jul-Sep)'),
        ('4', 'T4 (Oct-Déc)'),
    ], string='Trimestre', default=lambda self: str((date.today().month - 1) // 3 + 1))
    
    annee = fields.Integer(
        string='Année',
        default=lambda self: date.today().year,
        required=True,
    )
    
    date_debut = fields.Date(string='Date début')
    date_fin = fields.Date(string='Date fin')
    
    # Filtres
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employés',
        help="Laisser vide pour inclure tous les employés",
    )
    
    # Comptes comptables
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', '=', 'general')]",
        default=lambda self: self._get_default_journal(),
    )
    
    compte_charge_id = fields.Many2one(
        'account.account',
        string='Compte de charges',
        required=True,
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost'])]",
        default=lambda self: self._get_default_compte_charge(),
        help="Compte de charges pour les frais de déplacement (ex: 617000)",
    )
    
    compte_dette_id = fields.Many2one(
        'account.account',
        string='Compte de dette',
        required=True,
        domain="[('account_type', 'in', ['liability_current', 'liability_payable'])]",
        default=lambda self: self._get_default_compte_dette(),
        help="Compte de dette envers les employés (ex: 455000)",
    )
    
    # Options
    regrouper_par_employe = fields.Boolean(
        string='Regrouper par employé',
        default=True,
        help="Créer une écriture par employé au lieu d'une seule écriture globale",
    )
    
    inclure_valides_seulement = fields.Boolean(
        string='Trajets validés uniquement',
        default=True,
        help="N'inclure que les trajets à l'état 'Validé'",
    )
    
    # Aperçu
    trajet_ids = fields.Many2many(
        'km.trajet',
        string='Trajets à comptabiliser',
        compute='_compute_trajets',
    )
    
    nombre_trajets = fields.Integer(
        string='Nombre de trajets',
        compute='_compute_trajets',
    )
    
    montant_total = fields.Float(
        string='Montant total',
        compute='_compute_trajets',
        digits=(10, 2),
    )
    
    distance_totale = fields.Float(
        string='Distance totale (km)',
        compute='_compute_trajets',
        digits=(10, 1),
    )

    def _get_default_journal(self):
        """Récupérer le journal des opérations diverses par défaut"""
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
        ], limit=1)
        return journal

    def _get_default_compte_charge(self):
        """Récupérer le compte de charges par défaut (617xxx)"""
        compte = self.env['account.account'].search([
            ('code', '=like', '617%'),
        ], limit=1)
        if not compte:
            compte = self.env['account.account'].search([
                ('code', '=like', '61%'),
                ('account_type', 'in', ['expense', 'expense_direct_cost']),
            ], limit=1)
        return compte

    def _get_default_compte_dette(self):
        """Récupérer le compte de dette par défaut (455xxx)"""
        compte = self.env['account.account'].search([
            ('code', '=like', '455%'),
        ], limit=1)
        if not compte:
            compte = self.env['account.account'].search([
                ('code', '=like', '45%'),
                ('account_type', 'in', ['liability_current', 'liability_payable']),
            ], limit=1)
        return compte

    @api.onchange('type_periode', 'mois', 'trimestre', 'annee')
    def _onchange_periode(self):
        """Calculer les dates de début et fin selon la période"""
        if self.type_periode == 'mois' and self.mois:
            mois = int(self.mois)
            self.date_debut = date(self.annee, mois, 1)
            if mois == 12:
                self.date_fin = date(self.annee, 12, 31)
            else:
                self.date_fin = date(self.annee, mois + 1, 1) - relativedelta(days=1)
        
        elif self.type_periode == 'trimestre' and self.trimestre:
            trim = int(self.trimestre)
            mois_debut = (trim - 1) * 3 + 1
            self.date_debut = date(self.annee, mois_debut, 1)
            self.date_fin = date(self.annee, mois_debut + 2, 1) + relativedelta(months=1) - relativedelta(days=1)
        
        elif self.type_periode == 'annee':
            self.date_debut = date(self.annee, 1, 1)
            self.date_fin = date(self.annee, 12, 31)

    @api.depends('date_debut', 'date_fin', 'employee_ids', 'inclure_valides_seulement')
    def _compute_trajets(self):
        """Calculer les trajets correspondants aux critères"""
        for wizard in self:
            domain = [
                ('comptabilise', '=', False),
                ('montant_indemnite', '>', 0),
            ]
            
            if wizard.date_debut:
                domain.append(('date', '>=', wizard.date_debut))
            if wizard.date_fin:
                domain.append(('date', '<=', wizard.date_fin))
            if wizard.employee_ids:
                domain.append(('employee_id', 'in', wizard.employee_ids.ids))
            if wizard.inclure_valides_seulement:
                domain.append(('state', '=', 'valide'))
            else:
                domain.append(('state', 'in', ['valide', 'soumis']))
            
            trajets = self.env['km.trajet'].search(domain)
            wizard.trajet_ids = trajets
            wizard.nombre_trajets = len(trajets)
            wizard.montant_total = sum(trajets.mapped('montant_indemnite'))
            wizard.distance_totale = sum(trajets.mapped('distance'))

    def action_apercu(self):
        """Afficher l'aperçu des trajets à comptabiliser"""
        self.ensure_one()
        
        return {
            'name': 'Trajets à comptabiliser',
            'type': 'ir.actions.act_window',
            'res_model': 'km.trajet',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.trajet_ids.ids)],
            'context': {'create': False},
        }

    def action_comptabiliser(self):
        """Créer les écritures comptables"""
        self.ensure_one()
        
        if not self.trajet_ids:
            raise UserError("Aucun trajet à comptabiliser pour cette période.")
        
        if not self.journal_id or not self.compte_charge_id or not self.compte_dette_id:
            raise UserError("Veuillez configurer le journal et les comptes comptables.")
        
        moves_created = self.env['account.move']
        
        if self.regrouper_par_employe:
            # Grouper par employé
            employees = self.trajet_ids.mapped('employee_id')
            for employee in employees:
                trajets_employee = self.trajet_ids.filtered(lambda t: t.employee_id == employee)
                if trajets_employee:
                    move = self._create_account_move(trajets_employee, employee)
                    moves_created |= move
        else:
            # Une seule écriture globale
            move = self._create_account_move(self.trajet_ids)
            moves_created |= move
        
        # Marquer les trajets comme comptabilisés
        self.trajet_ids.write({
            'comptabilise': True,
            'date_comptabilisation': fields.Date.today(),
        })
        
        # Afficher le résultat
        if len(moves_created) == 1:
            return {
                'name': 'Écriture comptable',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': moves_created.id,
                'view_mode': 'form',
            }
        else:
            return {
                'name': 'Écritures comptables',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_created.ids)],
            }

    def _create_account_move(self, trajets, employee=None):
        """Créer une écriture comptable pour les trajets"""
        montant_total = sum(trajets.mapped('montant_indemnite'))
        distance_totale = sum(trajets.mapped('distance'))
        
        # Référence
        periode_str = ""
        if self.type_periode == 'mois':
            periode_str = f"{dict(self._fields['mois'].selection).get(self.mois)} {self.annee}"
        elif self.type_periode == 'trimestre':
            periode_str = f"T{self.trimestre} {self.annee}"
        elif self.type_periode == 'annee':
            periode_str = str(self.annee)
        else:
            periode_str = f"{self.date_debut} - {self.date_fin}"
        
        if employee:
            ref = f"IK {employee.name} - {periode_str}"
            partner = employee.user_id.partner_id if employee.user_id else False
        else:
            ref = f"Indemnités KM - {periode_str}"
            partner = False
        
        # Description pour les lignes
        description = f"Indemnités kilométriques - {len(trajets)} trajets - {distance_totale:.1f} km"
        
        # Créer l'écriture
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date_fin or fields.Date.today(),
            'ref': ref,
            'move_type': 'entry',
            'line_ids': [
                # Ligne de charge (débit)
                (0, 0, {
                    'name': description,
                    'account_id': self.compte_charge_id.id,
                    'debit': montant_total,
                    'credit': 0.0,
                    'partner_id': partner.id if partner else False,
                }),
                # Ligne de dette (crédit)
                (0, 0, {
                    'name': description,
                    'account_id': self.compte_dette_id.id,
                    'debit': 0.0,
                    'credit': montant_total,
                    'partner_id': partner.id if partner else False,
                }),
            ],
        }
        
        move = self.env['account.move'].create(move_vals)
        
        # Lier les trajets à l'écriture
        trajets.write({'account_move_id': move.id})
        
        return move
