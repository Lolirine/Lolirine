# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ApartmentMeter(models.Model):
    _name = 'apartment.meter'
    _description = 'Compteur'
    _inherit = ['mail.thread']
    _order = 'property_id, meter_type'

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )
    active = fields.Boolean(default=True)
    
    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
        ondelete='cascade',
    )
    
    meter_type = fields.Selection([
        ('electricity', 'Électricité'),
        ('gas', 'Gaz'),
        ('water', 'Eau'),
        ('heating', 'Chauffage'),
        ('other', 'Autre'),
    ], string='Type', required=True, tracking=True)
    
    meter_number = fields.Char(string='Numéro de compteur', tracking=True)
    ean_code = fields.Char(string='Code EAN', help='Code EAN du point de livraison')
    
    unit = fields.Selection([
        ('kwh', 'kWh'),
        ('m3', 'm³'),
        ('liters', 'Litres'),
        ('units', 'Unités'),
    ], string='Unité', required=True)
    
    location = fields.Char(string='Emplacement')
    supplier = fields.Char(string='Fournisseur')
    contract_number = fields.Char(string='N° contrat')
    
    # Dernier relevé
    last_reading = fields.Float(
        string='Dernier relevé',
        compute='_compute_last_reading',
        store=True,
    )
    last_reading_date = fields.Date(
        string='Date dernier relevé',
        compute='_compute_last_reading',
        store=True,
    )
    
    # Relevés
    reading_ids = fields.One2many(
        'apartment.meter.reading',
        'meter_id',
        string='Relevés',
    )
    
    notes = fields.Text(string='Notes')

    @api.depends('property_id', 'meter_type')
    def _compute_name(self):
        type_names = {
            'electricity': _('Électricité'),
            'gas': _('Gaz'),
            'water': _('Eau'),
            'heating': _('Chauffage'),
            'other': _('Autre'),
        }
        for record in self:
            type_name = type_names.get(record.meter_type, '')
            property_name = record.property_id.name if record.property_id else ''
            record.name = f"{type_name} - {property_name}"

    @api.depends('reading_ids', 'reading_ids.value', 'reading_ids.date')
    def _compute_last_reading(self):
        for record in self:
            last = record.reading_ids.sorted('date', reverse=True)[:1]
            record.last_reading = last.value if last else 0.0
            record.last_reading_date = last.date if last else False

    def action_add_reading(self):
        """Ajouter un relevé"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouveau relevé'),
            'res_model': 'apartment.meter.reading',
            'view_mode': 'form',
            'context': {
                'default_meter_id': self.id,
            },
            'target': 'new',
        }

    def action_view_readings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Relevés'),
            'res_model': 'apartment.meter.reading',
            'view_mode': 'list,form',
            'domain': [('meter_id', '=', self.id)],
            'context': {'default_meter_id': self.id},
        }
