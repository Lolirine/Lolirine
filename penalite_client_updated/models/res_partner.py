
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    penalite_ids = fields.One2many('penalite.client', 'partner_id', string="Pénalités")
