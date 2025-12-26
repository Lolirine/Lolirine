# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ApartmentIndexHistory(models.Model):
    _name = 'apartment.index.history'
    _description = 'Historique d\'indexation'
    _order = 'date desc'

    lease_id = fields.Many2one(
        'apartment.lease',
        string='Bail',
        required=True,
        ondelete='cascade',
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
    
    date = fields.Date(
        string='Date d\'application',
        required=True,
    )
    
    # Loyers
    old_rent = fields.Float(
        string='Ancien loyer (€)',
        required=True,
        digits=(10, 2),
    )
    new_rent = fields.Float(
        string='Nouveau loyer (€)',
        required=True,
        digits=(10, 2),
    )
    rent_increase = fields.Float(
        string='Augmentation (€)',
        compute='_compute_increase',
        store=True,
        digits=(10, 2),
    )
    rent_increase_pct = fields.Float(
        string='Augmentation (%)',
        compute='_compute_increase',
        store=True,
        digits=(5, 2),
    )
    
    # Indices
    old_index = fields.Float(
        string='Ancien indice',
        required=True,
        digits=(10, 2),
    )
    new_index = fields.Float(
        string='Nouvel indice',
        required=True,
        digits=(10, 2),
    )
    index_increase_pct = fields.Float(
        string='Évolution indice (%)',
        compute='_compute_index_increase',
        store=True,
        digits=(5, 2),
    )
    
    # Source de l'indice
    index_source = fields.Selection([
        ('statbel', 'StatBel'),
        ('manual', 'Manuel'),
    ], string='Source indice', default='manual')
    index_month = fields.Char(string='Mois de référence')
    
    # Notification
    notification_sent = fields.Boolean(string='Notification envoyée')
    notification_date = fields.Date(string='Date notification')
    
    notes = fields.Text(string='Notes')

    @api.depends('old_rent', 'new_rent')
    def _compute_increase(self):
        for record in self:
            record.rent_increase = record.new_rent - record.old_rent
            if record.old_rent > 0:
                record.rent_increase_pct = ((record.new_rent - record.old_rent) / record.old_rent) * 100
            else:
                record.rent_increase_pct = 0

    @api.depends('old_index', 'new_index')
    def _compute_index_increase(self):
        for record in self:
            if record.old_index > 0:
                record.index_increase_pct = ((record.new_index - record.old_index) / record.old_index) * 100
            else:
                record.index_increase_pct = 0
