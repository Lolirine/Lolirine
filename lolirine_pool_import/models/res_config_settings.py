# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pool_claude_api_key = fields.Char(
        string='Clé API Claude',
        config_parameter='pool.claude_api_key',
        help="Clé API Anthropic Claude pour l'extraction OCR"
    )
    
    pool_google_api_key = fields.Char(
        string='Clé API Google',
        config_parameter='pool.google_api_key',
        help="Clé API Google Cloud pour la recherche d'images (Custom Search API)"
    )
    
    pool_google_search_engine_id = fields.Char(
        string='Search Engine ID (cx)',
        config_parameter='pool.google_search_engine_id',
        help="ID du moteur de recherche Google Programmable Search Engine"
    )
