# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    api_key = fields.Char(string="Clé d'API", copy=False, readonly=True)

    def _generate_api_key(self):
        self.ensure_one()
        # Génère une clé unique et sécurisée
        self.api_key = str(uuid.uuid4())

    @api.model
    def _get_user_from_api_key(self, api_key):
        return self.sudo().search([('api_key', '=', api_key)], limit=1)
