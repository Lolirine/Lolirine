# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StorageFloor(models.Model):
    _name = 'storage.floor'
    _description = 'Étage du garde-meubles'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Actif', default=True)
    box_ids = fields.One2many('storage.box', 'floor_id', string='Boxes')
    box_count = fields.Integer(string='Nombre de boxes', compute='_compute_box_count')
    available_box_count = fields.Integer(string='Boxes disponibles', compute='_compute_box_count')

    @api.depends('box_ids', 'box_ids.status')
    def _compute_box_count(self):
        for floor in self:
            floor.box_count = len(floor.box_ids)
            floor.available_box_count = len(floor.box_ids.filtered(lambda b: b.status == 'disponible'))
