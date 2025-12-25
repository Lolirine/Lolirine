# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApartmentMeterReading(models.Model):
    _name = 'apartment.meter.reading'
    _description = 'Relevé de compteur'
    _order = 'date desc'

    meter_id = fields.Many2one(
        'apartment.meter',
        string='Compteur',
        required=True,
        ondelete='cascade',
    )
    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        related='meter_id.property_id',
        store=True,
    )
    meter_type = fields.Selection(
        related='meter_id.meter_type',
        store=True,
    )
    unit = fields.Selection(
        related='meter_id.unit',
        store=True,
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
    )
    value = fields.Float(
        string='Index',
        required=True,
        digits=(12, 3),
    )
    
    # Consommation calculée
    previous_reading_id = fields.Many2one(
        'apartment.meter.reading',
        string='Relevé précédent',
        compute='_compute_previous_reading',
        store=True,
    )
    previous_value = fields.Float(
        string='Index précédent',
        compute='_compute_consumption',
        store=True,
    )
    consumption = fields.Float(
        string='Consommation',
        compute='_compute_consumption',
        store=True,
        digits=(12, 3),
    )
    days_since_last = fields.Integer(
        string='Jours depuis dernier relevé',
        compute='_compute_consumption',
        store=True,
    )
    daily_average = fields.Float(
        string='Moyenne journalière',
        compute='_compute_consumption',
        store=True,
        digits=(12, 3),
    )
    
    # Type de relevé
    reading_type = fields.Selection([
        ('manual', 'Manuel'),
        ('entry', 'Entrée locataire'),
        ('exit', 'Sortie locataire'),
        ('annual', 'Annuel'),
        ('provider', 'Fournisseur'),
    ], string='Type', default='manual')
    
    # Lien avec état des lieux
    inventory_id = fields.Many2one(
        'apartment.inventory',
        string='État des lieux',
    )
    
    # Photo du compteur
    image = fields.Image(
        string='Photo',
        max_width=1920,
        max_height=1920,
    )
    
    read_by = fields.Many2one(
        'res.users',
        string='Relevé par',
        default=lambda self: self.env.user,
    )
    
    notes = fields.Text(string='Notes')

    @api.depends('meter_id', 'date')
    def _compute_previous_reading(self):
        for record in self:
            previous = self.search([
                ('meter_id', '=', record.meter_id.id),
                ('date', '<', record.date),
                ('id', '!=', record.id),
            ], order='date desc', limit=1)
            record.previous_reading_id = previous.id if previous else False

    @api.depends('value', 'previous_reading_id', 'previous_reading_id.value', 'date')
    def _compute_consumption(self):
        for record in self:
            if record.previous_reading_id:
                record.previous_value = record.previous_reading_id.value
                record.consumption = record.value - record.previous_reading_id.value
                
                if record.previous_reading_id.date and record.date:
                    days = (record.date - record.previous_reading_id.date).days
                    record.days_since_last = days
                    record.daily_average = record.consumption / days if days > 0 else 0
                else:
                    record.days_since_last = 0
                    record.daily_average = 0
            else:
                record.previous_value = 0
                record.consumption = 0
                record.days_since_last = 0
                record.daily_average = 0

    @api.constrains('value', 'previous_reading_id')
    def _check_value(self):
        for record in self:
            if record.previous_reading_id and record.value < record.previous_reading_id.value:
                raise ValidationError(_(
                    'L\'index (%s) ne peut pas être inférieur à l\'index précédent (%s).'
                ) % (record.value, record.previous_reading_id.value))
