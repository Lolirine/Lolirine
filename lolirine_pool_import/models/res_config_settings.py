# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pool_claude_api_key = fields.Char(
        string='Clé API Claude',
        config_parameter='pool.claude_api_key',
        help="Clé API Anthropic Claude pour l'extraction OCR"
    )
