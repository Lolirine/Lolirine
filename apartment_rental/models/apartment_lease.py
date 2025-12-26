# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class ApartmentLease(models.Model):
    _name = 'apartment.lease'
    _description = 'Contrat de bail'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    active = fields.Boolean(default=True)
    
    # Parties
    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
        tracking=True,
        ondelete='restrict',
    )
    tenant_id = fields.Many2one(
        'apartment.tenant',
        string='Locataire',
        required=True,
        tracking=True,
        ondelete='restrict',
    )
    co_tenant_ids = fields.Many2many(
        'apartment.tenant',
        'apartment_lease_cotenant_rel',
        'lease_id',
        'tenant_id',
        string='Co-locataires',
    )
    
    # Dates
    date_start = fields.Date(
        string='Date de début',
        required=True,
        tracking=True,
    )
    date_end = fields.Date(
        string='Date de fin',
        tracking=True,
    )
    duration_months = fields.Integer(
        string='Durée (mois)',
        compute='_compute_duration',
        store=True,
    )
    
    # Type de bail
    lease_type = fields.Selection([
        ('short', 'Bail de courte durée (≤3 ans)'),
        ('long', 'Bail de longue durée (9 ans)'),
        ('student', 'Bail étudiant'),
        ('commercial', 'Bail commercial'),
        ('other', 'Autre'),
    ], string='Type de bail', default='long', required=True, tracking=True)
    
    # Loyer
    rent_amount = fields.Float(
        string='Loyer mensuel (€)',
        required=True,
        tracking=True,
    )
    charges_amount = fields.Float(
        string='Charges mensuelles (€)',
        default=0.0,
        tracking=True,
    )
    charges_type = fields.Selection([
        ('fixed', 'Forfait'),
        ('provision', 'Provision avec décompte'),
        ('real', 'Charges réelles'),
    ], string='Type de charges', default='fixed')
    total_monthly = fields.Float(
        string='Total mensuel (€)',
        compute='_compute_total_monthly',
        store=True,
    )
    
    # Garantie locative
    deposit_amount = fields.Float(
        string='Garantie locative (€)',
        tracking=True,
    )
    deposit_type = fields.Selection([
        ('bank', 'Compte bancaire bloqué'),
        ('cash', 'Espèces'),
        ('bank_guarantee', 'Garantie bancaire'),
        ('cpas', 'Garantie CPAS'),
    ], string='Type de garantie', default='bank')
    deposit_bank = fields.Char(string='Banque de la garantie')
    deposit_account = fields.Char(string='N° compte garantie')
    deposit_released = fields.Boolean(string='Garantie libérée', default=False)
    deposit_release_date = fields.Date(string='Date de libération')
    
    # Indexation
    indexation_enabled = fields.Boolean(
        string='Indexation activée',
        default=True,
        tracking=True,
    )
    indexation_month = fields.Selection([
        ('1', 'Janvier'),
        ('2', 'Février'),
        ('3', 'Mars'),
        ('4', 'Avril'),
        ('5', 'Mai'),
        ('6', 'Juin'),
        ('7', 'Juillet'),
        ('8', 'Août'),
        ('9', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre'),
    ], string='Mois d\'indexation', compute='_compute_indexation_month', store=True)
    base_index = fields.Float(
        string='Indice de base',
        digits=(10, 2),
        help='Indice santé du mois précédant la signature du bail',
        tracking=True,
    )
    current_index = fields.Float(
        string='Indice actuel',
        digits=(10, 2),
        tracking=True,
    )
    initial_rent = fields.Float(
        string='Loyer initial (€)',
        help='Loyer de base pour le calcul de l\'indexation',
        tracking=True,
    )
    last_indexation_date = fields.Date(
        string='Dernière indexation',
        tracking=True,
    )
    next_indexation_date = fields.Date(
        string='Prochaine indexation',
        tracking=True,
        help='Date de la prochaine indexation (modifiable manuellement)',
    )
    
    # Champs calculés pour la projection d'indexation
    projected_rent_increase = fields.Float(
        string='Indexation (€)',
        compute='_compute_projected_indexation',
        digits=(10, 2),
    )
    projected_new_rent = fields.Float(
        string='Nouveau loyer (€)',
        compute='_compute_projected_indexation',
        digits=(10, 2),
    )
    projected_total_indexed = fields.Float(
        string='Total indexé (€)',
        compute='_compute_projected_indexation',
        digits=(10, 2),
    )
    
    # Enregistrement
    registration_date = fields.Date(string='Date d\'enregistrement')
    registration_number = fields.Char(string='N° d\'enregistrement')
    registration_office = fields.Char(string='Bureau d\'enregistrement')
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'En cours'),
        ('ending', 'Préavis'),
        ('ended', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', tracking=True)
    
    # Préavis
    notice_date = fields.Date(string='Date de préavis')
    notice_end_date = fields.Date(string='Fin de préavis')
    notice_reason = fields.Selection([
        ('tenant', 'Initiative du locataire'),
        ('landlord', 'Initiative du bailleur'),
        ('mutual', 'Accord mutuel'),
        ('end_contract', 'Fin de contrat'),
    ], string='Motif de préavis')
    
    # Relations
    rent_ids = fields.One2many(
        'apartment.rent',
        'lease_id',
        string='Loyers',
    )
    inventory_entry_id = fields.Many2one(
        'apartment.inventory',
        string='État des lieux d\'entrée',
    )
    inventory_exit_id = fields.Many2one(
        'apartment.inventory',
        string='État des lieux de sortie',
    )
    index_history_ids = fields.One2many(
        'apartment.index.history',
        'lease_id',
        string='Historique indexations',
    )
    document_ids = fields.One2many(
        'apartment.document',
        'lease_id',
        string='Documents',
    )
    
    # Compteurs
    rent_count = fields.Integer(
        string='Nombre de loyers',
        compute='_compute_rent_count',
    )
    unpaid_rent_count = fields.Integer(
        string='Loyers impayés',
        compute='_compute_rent_count',
    )
    inventory_count = fields.Integer(
        string='Nombre d\'états des lieux',
        compute='_compute_inventory_count',
    )
    index_history_count = fields.Integer(
        string='Nombre d\'indexations',
        compute='_compute_index_history_count',
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    special_clauses = fields.Html(string='Clauses particulières')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('apartment.lease') or _('Nouveau')
            # Initialiser le loyer initial si non défini
            if not vals.get('initial_rent') and vals.get('rent_amount'):
                vals['initial_rent'] = vals['rent_amount']
        return super().create(vals_list)

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = relativedelta(record.date_end, record.date_start)
                record.duration_months = delta.years * 12 + delta.months
            else:
                record.duration_months = 0

    @api.depends('rent_amount', 'charges_amount')
    def _compute_total_monthly(self):
        for record in self:
            record.total_monthly = record.rent_amount + record.charges_amount

    @api.depends('date_start')
    def _compute_indexation_month(self):
        for record in self:
            if record.date_start:
                record.indexation_month = str(record.date_start.month)
            else:
                record.indexation_month = False

    @api.depends('initial_rent', 'base_index', 'current_index', 'charges_amount', 'indexation_enabled')
    def _compute_projected_indexation(self):
        """Calcule les montants projetés après indexation"""
        for record in self:
            if not record.indexation_enabled or not record.base_index or not record.current_index or not record.initial_rent:
                record.projected_rent_increase = 0.0
                record.projected_new_rent = record.rent_amount
                record.projected_total_indexed = record.rent_amount + record.charges_amount
            else:
                # Formule belge: Nouveau loyer = Loyer de base × (Nouvel indice / Indice de base)
                new_rent = record.initial_rent * (record.current_index / record.base_index)
                record.projected_new_rent = round(new_rent, 2)
                record.projected_rent_increase = round(new_rent - record.rent_amount, 2)
                record.projected_total_indexed = round(new_rent + record.charges_amount, 2)
    
    @api.onchange('date_start')
    def _onchange_date_start_indexation(self):
        """Met à jour les valeurs d'indexation lors du changement de date de début"""
        if self.date_start:
            # Calculer la prochaine date d'indexation (1 an après le début)
            if not self.next_indexation_date:
                self.next_indexation_date = self.date_start + relativedelta(years=1)
            # Initialiser le loyer initial si pas défini
            if not self.initial_rent and self.rent_amount:
                self.initial_rent = self.rent_amount
    
    @api.onchange('rent_amount')
    def _onchange_rent_amount_initial(self):
        """Met à jour le loyer initial si pas encore défini"""
        if self.rent_amount and not self.initial_rent:
            self.initial_rent = self.rent_amount

    def _compute_rent_count(self):
        for record in self:
            record.rent_count = len(record.rent_ids)
            record.unpaid_rent_count = len(record.rent_ids.filtered(lambda r: r.state in ['draft', 'partial']))

    def _compute_inventory_count(self):
        for record in self:
            count = 0
            if record.inventory_entry_id:
                count += 1
            if record.inventory_exit_id:
                count += 1
            record.inventory_count = count

    def _compute_index_history_count(self):
        for record in self:
            record.index_history_count = len(record.index_history_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end and record.date_start > record.date_end:
                raise ValidationError(_('La date de fin doit être postérieure à la date de début.'))

    @api.constrains('deposit_amount', 'rent_amount')
    def _check_deposit(self):
        for record in self:
            if record.deposit_amount and record.rent_amount:
                # En Belgique, la garantie ne peut excéder 3 mois de loyer pour un bail de résidence principale
                if record.lease_type in ['short', 'long'] and record.deposit_amount > record.rent_amount * 3:
                    raise ValidationError(_(
                        'La garantie locative ne peut excéder 3 mois de loyer pour un bail de résidence principale.'
                    ))

    def action_activate(self):
        """Activer le bail"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Seul un bail en brouillon peut être activé.'))
            if not record.inventory_entry_id:
                raise UserError(_('Un état des lieux d\'entrée est requis avant d\'activer le bail.'))
            record.state = 'active'

    def action_give_notice(self):
        """Donner le préavis"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Donner préavis'),
            'res_model': 'apartment.lease',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def action_end(self):
        """Terminer le bail"""
        for record in self:
            if record.state not in ['active', 'ending']:
                raise UserError(_('Seul un bail actif ou en préavis peut être terminé.'))
            if not record.inventory_exit_id:
                raise UserError(_('Un état des lieux de sortie est requis avant de terminer le bail.'))
            record.state = 'ended'

    def action_cancel(self):
        """Annuler le bail"""
        for record in self:
            if record.state not in ['draft']:
                raise UserError(_('Seul un bail en brouillon peut être annulé.'))
            record.state = 'cancelled'

    def action_view_rents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Loyers'),
            'res_model': 'apartment.rent',
            'view_mode': 'list,form',
            'domain': [('lease_id', '=', self.id)],
            'context': {'default_lease_id': self.id},
        }

    def action_view_inventories(self):
        self.ensure_one()
        inventory_ids = []
        if self.inventory_entry_id:
            inventory_ids.append(self.inventory_entry_id.id)
        if self.inventory_exit_id:
            inventory_ids.append(self.inventory_exit_id.id)
        return {
            'type': 'ir.actions.act_window',
            'name': _('États des lieux'),
            'res_model': 'apartment.inventory',
            'view_mode': 'list,form',
            'domain': [('id', 'in', inventory_ids)],
            'context': {'default_lease_id': self.id},
        }

    def action_view_index_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Historique indexations'),
            'res_model': 'apartment.index.history',
            'view_mode': 'list,form',
            'domain': [('lease_id', '=', self.id)],
            'context': {'default_lease_id': self.id},
        }

    def action_create_inventory_entry(self):
        """Créer l'état des lieux d'entrée"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('État des lieux d\'entrée'),
            'res_model': 'apartment.inventory',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.property_id.id,
                'default_lease_id': self.id,
                'default_tenant_id': self.tenant_id.id,
                'default_inventory_type': 'entry',
                'default_date': self.date_start,
            },
            'target': 'current',
        }

    def action_create_inventory_exit(self):
        """Créer l'état des lieux de sortie"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('État des lieux de sortie'),
            'res_model': 'apartment.inventory',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.property_id.id,
                'default_lease_id': self.id,
                'default_tenant_id': self.tenant_id.id,
                'default_inventory_type': 'exit',
                'default_entry_inventory_id': self.inventory_entry_id.id if self.inventory_entry_id else False,
            },
            'target': 'current',
        }

    def calculate_indexed_rent(self, new_index):
        """
        Calcule le loyer indexé selon la formule belge:
        Loyer indexé = (Loyer de base × Nouvel indice) / Indice de base
        """
        self.ensure_one()
        if not self.base_index or not self.initial_rent:
            raise UserError(_('L\'indice de base et le loyer initial doivent être définis.'))
        
        indexed_rent = (self.initial_rent * new_index) / self.base_index
        return round(indexed_rent, 2)

    def action_apply_indexation(self):
        """Appliquer l'indexation"""
        self.ensure_one()
        if not self.indexation_enabled:
            raise UserError(_('L\'indexation n\'est pas activée pour ce bail.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appliquer l\'indexation'),
            'res_model': 'apartment.indexation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lease_id': self.id,
                'default_current_rent': self.rent_amount,
                'default_base_index': self.base_index,
                'default_current_index': self.current_index,
            },
        }

    def _apply_indexation(self, new_index, new_rent, indexation_date):
        """Appliquer l'indexation au bail"""
        self.ensure_one()
        
        # Créer l'historique
        self.env['apartment.index.history'].create({
            'lease_id': self.id,
            'date': indexation_date,
            'old_rent': self.rent_amount,
            'new_rent': new_rent,
            'old_index': self.current_index or self.base_index,
            'new_index': new_index,
        })
        
        # Mettre à jour le bail
        self.write({
            'rent_amount': new_rent,
            'current_index': new_index,
            'last_indexation_date': indexation_date,
        })

    @api.model
    def _cron_check_indexation(self):
        """Cron pour vérifier les indexations à effectuer"""
        today = date.today()
        leases = self.search([
            ('state', '=', 'active'),
            ('indexation_enabled', '=', True),
            ('next_indexation_date', '<=', today),
        ])
        
        for lease in leases:
            # Créer une activité de rappel
            lease.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Indexation à effectuer'),
                note=_('Le bail %s nécessite une indexation. Date prévue: %s') % (
                    lease.name, lease.next_indexation_date
                ),
                user_id=self.env.user.id,
            )

    @api.model
    def _cron_check_lease_end(self):
        """Cron pour vérifier les fins de bail approchant"""
        today = date.today()
        warning_date = today + relativedelta(months=3)
        
        leases = self.search([
            ('state', '=', 'active'),
            ('date_end', '<=', warning_date),
            ('date_end', '>=', today),
        ])
        
        for lease in leases:
            days_remaining = (lease.date_end - today).days
            lease.activity_schedule(
                'mail.mail_activity_data_warning',
                summary=_('Fin de bail approchant'),
                note=_('Le bail %s se termine dans %s jours (%s).') % (
                    lease.name, days_remaining, lease.date_end
                ),
                user_id=self.env.user.id,
            )
