# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    api_key = fields.Char(string="Clé d'API", copy=False, readonly=True, help="Clé d'API unique pour cet utilisateur.")

    def _generate_api_key(self):
        for user in self:
            user.api_key = str(uuid.uuid4())

    @api.model
    def _get_user_from_api_key(self, api_key):
        if not api_key:
            return self.env['res.users']
        return self.sudo().search([('api_key', '=', api_key)], limit=1)
