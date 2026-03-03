from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_chat_api_key = fields.Char(
        string='Cle API Anthropic',
        config_parameter='lolirine_ai_chat.api_key',
    )
    ai_chat_model = fields.Selection([
        ('claude-sonnet-4-20250514', 'Claude Sonnet 4'),
        ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5'),
    ],
        string='Modele IA',
        config_parameter='lolirine_ai_chat.model',
        default='claude-sonnet-4-20250514',
    )
    ai_chat_max_tokens = fields.Integer(
        string='Tokens max',
        config_parameter='lolirine_ai_chat.max_tokens',
        default=1024,
    )
    ai_chat_enabled = fields.Boolean(
        string='Activer le chat IA',
        config_parameter='lolirine_ai_chat.enabled',
        default=True,
    )
    ai_chat_web_search = fields.Boolean(
        string='Recherche web',
        config_parameter='lolirine_ai_chat.web_search',
        default=True,
    )
    ai_chat_product_search = fields.Boolean(
        string='Recherche produits',
        config_parameter='lolirine_ai_chat.product_search',
        default=True,
    )
    ai_chat_system_prompt = fields.Text(
        string='Prompt systeme',
        config_parameter='lolirine_ai_chat.system_prompt',
    )
    ai_chat_welcome_message = fields.Text(
        string='Message de bienvenue',
        config_parameter='lolirine_ai_chat.welcome_message',
        default='Bonjour ! Je suis l assistant IA de Lolirine Pool Store. Comment puis-je vous aider ?',
    )
    ai_chat_primary_color = fields.Char(
        string='Couleur principale',
        config_parameter='lolirine_ai_chat.primary_color',
        default='#0369a1',
    )
