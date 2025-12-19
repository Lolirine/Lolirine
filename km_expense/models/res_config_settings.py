# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    km_expense_api_key = fields.Char(
        string='Clé API Google',
        config_parameter='km_expense.distance_api_key',
        help="Clé API Google pour les services Distance Matrix et Places (autocomplétion d'adresses)",
    )
    
    km_expense_api_provider = fields.Selection([
        ('google', 'Google Maps'),
        ('openroute', 'OpenRouteService (gratuit)'),
    ], string='Fournisseur API',
       config_parameter='km_expense.distance_api_provider',
       default='google',
       help="Service utilisé pour le calcul des distances",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            km_expense_api_key=params.get_param('km_expense.distance_api_key', default=''),
            km_expense_api_provider=params.get_param('km_expense.distance_api_provider', default='google'),
        )
        return res

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('km_expense.distance_api_key', self.km_expense_api_key or '')
        params.set_param('km_expense.distance_api_provider', self.km_expense_api_provider or 'google')
