# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_places_api_key = fields.Char(
        string="Clé API Google Places",
        help="Clé API Google pour l'autocomplétion des adresses. "
             "Obtenez-la sur https://console.cloud.google.com/apis/credentials"
    )

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'lolirine_contact_form.google_places_api_key',
            self.google_places_api_key or ''
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        res['google_places_api_key'] = self.env['ir.config_parameter'].sudo().get_param(
            'lolirine_contact_form.google_places_api_key', default=''
        )
        return res
