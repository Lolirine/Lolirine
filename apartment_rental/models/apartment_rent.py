# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import date


class ApartmentRent(models.Model):
    _name = 'apartment.rent'
    _description = 'Loyer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_due desc'

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    active = fields.Boolean(default=True)
    
    # Relations
    lease_id = fields.Many2one(
        'apartment.lease',
        string='Bail',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        related='lease_id.property_id',
        store=True,
    )
    tenant_id = fields.Many2one(
        'apartment.tenant',
        string='Locataire',
        related='lease_id.tenant_id',
        store=True,
    )
    
    # Période
    period_start = fields.Date(
        string='Début de période',
        required=True,
    )
    period_end = fields.Date(
        string='Fin de période',
        required=True,
    )
    period_name = fields.Char(
        string='Période',
        compute='_compute_period_name',
        store=True,
    )
    
    # Montants
    rent_amount = fields.Float(
        string='Loyer (€)',
        required=True,
        tracking=True,
    )
    charges_amount = fields.Float(
        string='Charges (€)',
        default=0.0,
    )
    other_amount = fields.Float(
        string='Autres (€)',
        default=0.0,
        help='Régularisation, frais divers, etc.',
    )
    total_amount = fields.Float(
        string='Total dû (€)',
        compute='_compute_total',
        store=True,
    )
    
    # Paiement
    amount_paid = fields.Float(
        string='Montant payé (€)',
        default=0.0,
        tracking=True,
    )
    amount_due = fields.Float(
        string='Reste dû (€)',
        compute='_compute_amount_due',
        store=True,
    )
    
    # Dates
    date_due = fields.Date(
        string='Date d\'échéance',
        required=True,
        tracking=True,
    )
    date_paid = fields.Date(
        string='Date de paiement',
        tracking=True,
    )
    
    # Mode de paiement
    payment_method = fields.Selection([
        ('transfer', 'Virement bancaire'),
        ('domiciliation', 'Domiciliation'),
        ('cash', 'Espèces'),
        ('check', 'Chèque'),
        ('other', 'Autre'),
    ], string='Mode de paiement')
    payment_reference = fields.Char(string='Référence paiement')
    
    # Comptabilité (si module account installé)
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        ondelete='set null',
    )
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('late', 'En retard'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', tracking=True, compute='_compute_state', store=True)
    
    # Rappels
    reminder_sent = fields.Boolean(string='Rappel envoyé', default=False)
    reminder_date = fields.Date(string='Date rappel')
    reminder_count = fields.Integer(string='Nombre de rappels', default=0)
    
    # Notes
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('apartment.rent') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('period_start')
    def _compute_period_name(self):
        months_fr = {
            1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
            5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
            9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
        }
        for record in self:
            if record.period_start:
                month = months_fr.get(record.period_start.month, '')
                record.period_name = f"{month} {record.period_start.year}"
            else:
                record.period_name = ''

    @api.depends('rent_amount', 'charges_amount', 'other_amount')
    def _compute_total(self):
        for record in self:
            record.total_amount = record.rent_amount + record.charges_amount + record.other_amount

    @api.depends('total_amount', 'amount_paid')
    def _compute_amount_due(self):
        for record in self:
            record.amount_due = record.total_amount - record.amount_paid

    @api.depends('amount_due', 'date_due', 'amount_paid', 'total_amount')
    def _compute_state(self):
        today = date.today()
        for record in self:
            if record.amount_paid >= record.total_amount and record.total_amount > 0:
                record.state = 'paid'
            elif record.amount_paid > 0 and record.amount_paid < record.total_amount:
                if record.date_due and record.date_due < today:
                    record.state = 'late'
                else:
                    record.state = 'partial'
            elif record.date_due and record.date_due < today:
                record.state = 'late'
            elif record.state == 'draft':
                record.state = 'draft'
            else:
                record.state = 'pending'

    def action_confirm(self):
        """Confirmer le loyer"""
        for record in self:
            if record.state == 'draft':
                record.state = 'pending'

    def action_register_payment(self):
        """Enregistrer un paiement"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enregistrer paiement'),
            'res_model': 'apartment.rent',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def action_mark_paid(self):
        """Marquer comme payé"""
        for record in self:
            record.write({
                'amount_paid': record.total_amount,
                'date_paid': date.today(),
                'state': 'paid',
            })

    def action_send_reminder(self):
        """Envoyer un rappel de paiement"""
        for record in self:
            template = self.env.ref('apartment_rental.mail_template_rent_reminder', raise_if_not_found=False)
            if template:
                template.send_mail(record.id, force_send=True)
            
            record.write({
                'reminder_sent': True,
                'reminder_date': date.today(),
                'reminder_count': record.reminder_count + 1,
            })

    def action_cancel(self):
        """Annuler le loyer"""
        for record in self:
            record.state = 'cancelled'

    def action_create_invoice(self):
        """Créer une facture comptable"""
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_('Une facture existe déjà pour ce loyer.'))
        
        # Cette méthode peut être étendue pour créer une vraie facture
        # si le module account est installé
        raise UserError(_('La création de facture comptable nécessite une configuration supplémentaire.'))

    @api.model
    def _cron_check_late_rents(self):
        """Vérifier les loyers en retard"""
        today = date.today()
        late_rents = self.search([
            ('state', 'in', ['pending', 'partial']),
            ('date_due', '<', today),
        ])
        
        for rent in late_rents:
            rent.state = 'late'
            
            # Créer une activité
            rent.activity_schedule(
                'mail.mail_activity_data_warning',
                summary=_('Loyer en retard'),
                note=_('Le loyer %s de %s€ est en retard. Échéance: %s') % (
                    rent.name, rent.total_amount, rent.date_due
                ),
                user_id=self.env.user.id,
            )

    @api.model
    def _cron_send_rent_reminders(self):
        """Envoyer des rappels automatiques pour les loyers en retard"""
        today = date.today()
        late_rents = self.search([
            ('state', '=', 'late'),
            ('reminder_count', '<', 3),  # Maximum 3 rappels automatiques
            '|',
            ('reminder_date', '=', False),
            ('reminder_date', '<', today - relativedelta(days=7)),  # 1 rappel par semaine
        ])
        
        for rent in late_rents:
            rent.action_send_reminder()
