# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Compteurs de visites
    visite_ids = fields.One2many(
        'visite.box',
        'partner_id',
        string='Visites'
    )
    visite_count = fields.Integer(
        string='Nombre de visites',
        compute='_compute_visite_count'
    )
    
    # Box louées
    storage_box_ids = fields.One2many(
        'storage.box',
        'partner_id',
        string='Box louées'
    )
    storage_box_count = fields.Integer(
        string='Nombre de box',
        compute='_compute_storage_box_count'
    )
    
    # Statut prospect/client garde-meubles
    storage_status = fields.Selection([
        ('prospect', 'Prospect'),
        ('visited', 'A visité'),
        ('client', 'Client actif'),
        ('former', 'Ancien client'),
    ], string='Statut garde-meubles', default='prospect')
    
    # Dernière visite
    last_visite_date = fields.Datetime(
        string='Dernière visite',
        compute='_compute_last_visite'
    )
    last_visite_state = fields.Char(
        string='État dernière visite',
        compute='_compute_last_visite'
    )

    def _compute_visite_count(self):
        for partner in self:
            partner.visite_count = self.env['visite.box'].search_count([
                ('partner_id', '=', partner.id)
            ])

    def _compute_storage_box_count(self):
        for partner in self:
            partner.storage_box_count = self.env['storage.box'].search_count([
                ('partner_id', '=', partner.id)
            ])

    @api.depends('visite_ids', 'visite_ids.date_visite', 'visite_ids.state')
    def _compute_last_visite(self):
        for partner in self:
            last_visite = self.env['visite.box'].search([
                ('partner_id', '=', partner.id)
            ], order='date_visite desc', limit=1)
            if last_visite:
                partner.last_visite_date = last_visite.date_visite
                partner.last_visite_state = dict(
                    last_visite._fields['state'].selection
                ).get(last_visite.state, '')
            else:
                partner.last_visite_date = False
                partner.last_visite_state = False

    def action_view_visites(self):
        """Voir les visites du partenaire"""
        self.ensure_one()
        return {
            'name': _('Visites'),
            'type': 'ir.actions.act_window',
            'res_model': 'visite.box',
            'view_mode': 'tree,form,kanban,calendar',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_storage_boxes(self):
        """Voir les box du partenaire"""
        self.ensure_one()
        return {
            'name': _('Box de stockage'),
            'type': 'ir.actions.act_window',
            'res_model': 'storage.box',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }

    def action_create_visite(self):
        """Créer une nouvelle visite pour ce partenaire"""
        self.ensure_one()
        return {
            'name': _('Nouvelle visite'),
            'type': 'ir.actions.act_window',
            'res_model': 'visite.box',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
            },
        }
