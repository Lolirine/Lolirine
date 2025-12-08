# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VisiteBox(models.Model):
    _name = 'visite.box'
    _description = 'Visite client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_visite desc, id desc'

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default='Nouveau'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True
    )
    date_visite = fields.Datetime(
        string='Date de visite',
        required=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifiée'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string='État', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('visite.box') or 'Nouveau'
        return super().create(vals_list)

    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})
