# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class BoxReservation(models.Model):
    _name = 'box.reservation'
    _description = 'Réservation de box'
    _order = 'create_date desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='New')
    box_id = fields.Many2one('storage.box', string='Box', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Client')
    
    # Informations contact
    customer_name = fields.Char(string='Nom du client', required=True)
    customer_email = fields.Char(string='Email', required=True)
    customer_phone = fields.Char(string='Téléphone', required=True)
    
    # Dates
    reservation_date = fields.Datetime(string='Date de réservation', default=fields.Datetime.now, required=True)
    appointment_date = fields.Datetime(string='Date de rendez-vous')
    start_date = fields.Date(string='Date de début')
    end_date = fields.Date(string='Date de fin')
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('ongoing', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', required=True)
    
    reservation_type = fields.Selection([
        ('appointment', 'Rendez-vous'),
        ('reservation', 'Réservation immédiate'),
    ], string='Type', required=True, default='appointment')
    
    # Informations financières
    monthly_price = fields.Float(string='Prix mensuel', related='box_id.price_monthly', readonly=True)
    registration_fee = fields.Float(string='Frais de dossier', related='box_id.registration_fee', readonly=True)
    deposit_amount = fields.Float(string='Caution', related='box_id.deposit_amount', readonly=True)
    total_amount = fields.Float(string='Montant total', compute='_compute_total_amount')
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                   default=lambda self: self.env.company.currency_id)
    
    # Notes
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Notes internes')
    active = fields.Boolean(string='Actif', default=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('box.reservation') or 'New'
        return super(BoxReservation, self).create(vals)
    
    @api.depends('monthly_price', 'registration_fee', 'deposit_amount', 'start_date', 'end_date')
    def _compute_total_amount(self):
        for reservation in self:
            if reservation.start_date and reservation.end_date:
                months = ((reservation.end_date.year - reservation.start_date.year) * 12 + 
                         (reservation.end_date.month - reservation.start_date.month))
                months = max(1, months)
                total = (reservation.monthly_price * months) + reservation.registration_fee + reservation.deposit_amount
            else:
                total = reservation.registration_fee + reservation.deposit_amount
            reservation.total_amount = total
    
    def action_confirm(self):
        self.state = 'confirmed'
        self.box_id.status = 'reserve'
        return True
    
    def action_start(self):
        self.state = 'ongoing'
        self.box_id.status = 'occupe'
        if not self.start_date:
            self.start_date = fields.Date.today()
        return True
    
    def action_complete(self):
        self.state = 'completed'
        self.box_id.status = 'disponible'
        if not self.end_date:
            self.end_date = fields.Date.today()
        return True
    
    def action_cancel(self):
        self.state = 'cancelled'
        if self.box_id.status in ['reserve', 'occupe']:
            self.box_id.status = 'disponible'
        return True
