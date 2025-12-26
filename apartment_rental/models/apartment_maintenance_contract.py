# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class ApartmentMaintenanceContract(models.Model):
    _name = 'apartment.maintenance.contract'
    _description = 'Contrat d\'entretien'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_payment_date asc, name'

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    active = fields.Boolean(default=True)
    
    # Relations
    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    
    # Prestataire
    provider_id = fields.Many2one(
        'res.partner',
        string='Prestataire',
        required=True,
        tracking=True,
    )
    provider_phone = fields.Char(
        related='provider_id.phone',
        string='Téléphone prestataire',
    )
    provider_email = fields.Char(
        related='provider_id.email',
        string='Email prestataire',
    )
    
    # Type de contrat
    contract_type = fields.Selection([
        ('boiler', 'Chaudière'),
        ('hvac', 'Climatisation/HVAC'),
        ('elevator', 'Ascenseur'),
        ('fire_safety', 'Sécurité incendie'),
        ('pest_control', 'Désinsectisation'),
        ('cleaning', 'Nettoyage'),
        ('garden', 'Jardinage'),
        ('alarm', 'Alarme/Sécurité'),
        ('other', 'Autre'),
    ], string='Type de contrat', required=True, default='boiler', tracking=True)
    
    # Équipement concerné
    equipment_brand = fields.Char(string='Marque équipement')
    equipment_model = fields.Char(string='Modèle équipement')
    equipment_serial = fields.Char(string='N° série équipement')
    equipment_year = fields.Integer(string='Année équipement')
    equipment_notes = fields.Text(string='Notes équipement')
    
    # Dates du contrat
    date_start = fields.Date(
        string='Date de début',
        required=True,
        tracking=True,
    )
    date_end = fields.Date(
        string='Date de fin',
        tracking=True,
    )
    is_renewable = fields.Boolean(
        string='Renouvellement automatique',
        default=True,
    )
    renewal_notice_days = fields.Integer(
        string='Préavis résiliation (jours)',
        default=30,
    )
    
    # Facturation
    payment_frequency = fields.Selection([
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('biannual', 'Semestriel'),
        ('annual', 'Annuel'),
        ('one_time', 'Paiement unique'),
    ], string='Fréquence de paiement', required=True, default='annual', tracking=True)
    
    payment_amount = fields.Float(
        string='Montant (€)',
        required=True,
        tracking=True,
    )
    payment_day = fields.Integer(
        string='Jour de paiement',
        default=1,
        help='Jour du mois pour le paiement (1-28)',
    )
    
    next_payment_date = fields.Date(
        string='Prochaine échéance',
        compute='_compute_next_payment_date',
        store=True,
    )
    days_until_payment = fields.Integer(
        string='Jours avant échéance',
        compute='_compute_days_until_payment',
    )
    
    # Rappels
    reminder_days = fields.Integer(
        string='Rappel (jours avant)',
        default=14,
        help='Nombre de jours avant l\'échéance pour envoyer un rappel',
    )
    last_reminder_date = fields.Date(string='Dernier rappel envoyé')
    
    # Historique des paiements
    payment_ids = fields.One2many(
        'apartment.maintenance.contract.payment',
        'contract_id',
        string='Paiements',
    )
    payment_count = fields.Integer(
        string='Nombre de paiements',
        compute='_compute_payment_stats',
    )
    total_paid = fields.Float(
        string='Total payé (€)',
        compute='_compute_payment_stats',
    )
    last_payment_date = fields.Date(
        string='Dernier paiement',
        compute='_compute_payment_stats',
    )
    
    # Documents
    document_ids = fields.One2many(
        'apartment.document',
        'maintenance_contract_id',
        string='Documents',
    )
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('expiring', 'Expire bientôt'),
        ('expired', 'Expiré'),
        ('cancelled', 'Résilié'),
    ], string='Statut', default='draft', tracking=True, compute='_compute_state', store=True)
    
    # Notes
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes internes')
    
    # Référence contrat externe
    external_reference = fields.Char(string='N° contrat prestataire')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('apartment.maintenance.contract') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('payment_ids.state', 'payment_ids.date', 'payment_ids.amount')
    def _compute_payment_stats(self):
        for record in self:
            paid_payments = record.payment_ids.filtered(lambda p: p.state == 'paid')
            record.payment_count = len(record.payment_ids)
            record.total_paid = sum(paid_payments.mapped('amount'))
            if paid_payments:
                record.last_payment_date = max(paid_payments.mapped('date'))
            else:
                record.last_payment_date = False

    @api.depends('payment_ids.state', 'payment_ids.due_date', 'payment_frequency', 'date_start')
    def _compute_next_payment_date(self):
        for record in self:
            # Chercher le prochain paiement non payé
            unpaid = record.payment_ids.filtered(lambda p: p.state != 'paid').sorted('due_date')
            if unpaid:
                record.next_payment_date = unpaid[0].due_date
            else:
                # Calculer la prochaine date basée sur la fréquence
                last_paid = record.payment_ids.filtered(lambda p: p.state == 'paid').sorted('due_date', reverse=True)
                if last_paid:
                    base_date = last_paid[0].due_date
                else:
                    base_date = record.date_start
                
                if base_date:
                    record.next_payment_date = record._get_next_date(base_date)
                else:
                    record.next_payment_date = False

    def _get_next_date(self, from_date):
        """Calculer la prochaine date de paiement"""
        self.ensure_one()
        if self.payment_frequency == 'monthly':
            return from_date + relativedelta(months=1)
        elif self.payment_frequency == 'quarterly':
            return from_date + relativedelta(months=3)
        elif self.payment_frequency == 'biannual':
            return from_date + relativedelta(months=6)
        elif self.payment_frequency == 'annual':
            return from_date + relativedelta(years=1)
        else:
            return False

    @api.depends('next_payment_date')
    def _compute_days_until_payment(self):
        today = fields.Date.today()
        for record in self:
            if record.next_payment_date:
                delta = record.next_payment_date - today
                record.days_until_payment = delta.days
            else:
                record.days_until_payment = 0

    @api.depends('date_end', 'date_start')
    def _compute_state(self):
        today = fields.Date.today()
        for record in self:
            # Keep cancelled state as is
            if record.state == 'cancelled':
                record.state = 'cancelled'
            elif not record.date_start:
                record.state = 'draft'
            elif record.date_end and record.date_end < today:
                record.state = 'expired'
            elif record.date_end and record.date_end <= today + relativedelta(days=30):
                record.state = 'expiring'
            elif record.date_start <= today:
                record.state = 'active'
            else:
                record.state = 'draft'

    @api.constrains('payment_day')
    def _check_payment_day(self):
        for record in self:
            if record.payment_day < 1 or record.payment_day > 28:
                raise ValidationError(_('Le jour de paiement doit être entre 1 et 28.'))

    def action_activate(self):
        """Activer le contrat"""
        for record in self:
            record.state = 'active'
            # Créer le premier paiement si nécessaire
            if not record.payment_ids:
                record.action_generate_next_payment()

    def action_cancel(self):
        """Résilier le contrat"""
        for record in self:
            record.state = 'cancelled'

    def action_renew(self):
        """Renouveler le contrat"""
        for record in self:
            if record.date_end:
                record.date_start = record.date_end
                record.date_end = record.date_end + relativedelta(years=1)
            record.state = 'active'

    def action_generate_next_payment(self):
        """Générer la prochaine échéance de paiement"""
        self.ensure_one()
        if self.payment_frequency == 'one_time' and self.payment_ids:
            return
        
        # Calculer la date d'échéance
        if self.payment_ids:
            last = self.payment_ids.sorted('due_date', reverse=True)[0]
            due_date = self._get_next_date(last.due_date)
        else:
            due_date = self.date_start
        
        if due_date:
            self.env['apartment.maintenance.contract.payment'].create({
                'contract_id': self.id,
                'due_date': due_date,
                'amount': self.payment_amount,
                'description': f'Échéance {due_date.strftime("%m/%Y")}',
            })

    def action_view_payments(self):
        """Voir les paiements"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paiements'),
            'res_model': 'apartment.maintenance.contract.payment',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {
                'default_contract_id': self.id,
                'default_amount': self.payment_amount,
            },
        }

    @api.model
    def _cron_check_payment_reminders(self):
        """Cron job pour vérifier les rappels de paiement"""
        today = fields.Date.today()
        contracts = self.search([
            ('state', 'in', ['active', 'expiring']),
            ('next_payment_date', '!=', False),
        ])
        
        for contract in contracts:
            reminder_date = contract.next_payment_date - relativedelta(days=contract.reminder_days)
            if today >= reminder_date and (not contract.last_reminder_date or contract.last_reminder_date < reminder_date):
                # Envoyer un rappel (créer une activité)
                contract.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=contract.next_payment_date,
                    summary=_('Échéance contrat d\'entretien'),
                    note=_(
                        'Le contrat "%s" pour le bien "%s" a une échéance de paiement le %s.\n'
                        'Montant: %.2f €'
                    ) % (
                        contract.name,
                        contract.property_id.name,
                        contract.next_payment_date.strftime('%d/%m/%Y'),
                        contract.payment_amount,
                    ),
                )
                contract.last_reminder_date = today

    @api.model
    def _cron_check_contract_expiry(self):
        """Cron job pour vérifier l'expiration des contrats"""
        today = fields.Date.today()
        expiring_contracts = self.search([
            ('state', '=', 'active'),
            ('date_end', '!=', False),
            ('date_end', '<=', today + relativedelta(days=30)),
        ])
        
        for contract in expiring_contracts:
            contract.state = 'expiring'
            contract.activity_schedule(
                'mail.mail_activity_data_warning',
                date_deadline=contract.date_end,
                summary=_('Contrat d\'entretien expire bientôt'),
                note=_(
                    'Le contrat "%s" pour le bien "%s" expire le %s.\n'
                    'Pensez à le renouveler ou à le résilier.'
                ) % (
                    contract.name,
                    contract.property_id.name,
                    contract.date_end.strftime('%d/%m/%Y'),
                ),
            )


class ApartmentMaintenanceContractPayment(models.Model):
    _name = 'apartment.maintenance.contract.payment'
    _description = 'Paiement de contrat d\'entretien'
    _order = 'due_date desc'

    contract_id = fields.Many2one(
        'apartment.maintenance.contract',
        string='Contrat',
        required=True,
        ondelete='cascade',
    )
    property_id = fields.Many2one(
        related='contract_id.property_id',
        string='Bien',
        store=True,
    )
    provider_id = fields.Many2one(
        related='contract_id.provider_id',
        string='Prestataire',
        store=True,
    )
    
    # Échéance
    due_date = fields.Date(
        string='Date d\'échéance',
        required=True,
    )
    amount = fields.Float(
        string='Montant (€)',
        required=True,
    )
    description = fields.Char(string='Description')
    
    # Paiement
    date = fields.Date(string='Date de paiement')
    payment_method = fields.Selection([
        ('bank_transfer', 'Virement bancaire'),
        ('direct_debit', 'Domiciliation'),
        ('card', 'Carte bancaire'),
        ('cash', 'Espèces'),
        ('check', 'Chèque'),
        ('other', 'Autre'),
    ], string='Mode de paiement')
    payment_reference = fields.Char(string='Référence paiement')
    
    # Facture
    invoice_number = fields.Char(string='N° facture')
    invoice_date = fields.Date(string='Date facture')
    invoice_file = fields.Binary(string='Facture (fichier)', attachment=True)
    invoice_filename = fields.Char(string='Nom du fichier')
    
    # État
    state = fields.Selection([
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('late', 'En retard'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='pending', compute='_compute_state', store=True)
    
    # Notes
    notes = fields.Text(string='Notes')

    @api.depends('due_date', 'date')
    def _compute_state(self):
        today = fields.Date.today()
        for record in self:
            # Keep cancelled state as is
            if record.state == 'cancelled':
                record.state = 'cancelled'
            elif record.date:
                record.state = 'paid'
            elif record.due_date and record.due_date < today:
                record.state = 'late'
            else:
                record.state = 'pending'

    def action_mark_paid(self):
        """Marquer comme payé"""
        for record in self:
            record.date = fields.Date.today()
            record.state = 'paid'
            # Générer la prochaine échéance
            record.contract_id.action_generate_next_payment()

    def action_cancel(self):
        """Annuler le paiement"""
        for record in self:
            record.state = 'cancelled'
