# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class my_module(models.Model):
#     _name = 'my_module.my_module'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100
from odoo import models, fields

class PenaliteClient(models.Model):
    _name = 'penalite.client'
    _description = 'Pénalité Client'

    name = fields.Char(string="Nom", required=True)
    motif = fields.Text(string="Motif de la pénalité")
    montant = fields.Float(string="Montant", required=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
