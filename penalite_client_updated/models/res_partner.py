
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res_partner'

    penalite_ids = fields.One2many('penalite_client', 'partner_id', string="Pénalités")
