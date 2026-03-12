from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_chat_api_key = fields.Char(
        string='Cle API Anthropic',
        config_parameter='lolirine_ai_chat.api_key',
        default='',
    )
    ai_chat_model = fields.Selection(
        [
            ('claude-sonnet-4-20250514', 'Claude Sonnet 4'),
            ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5'),
        ],
        string='Modele IA',
        config_parameter='lolirine_ai_chat.model',
        default='claude-sonnet-4-20250514',
    )
    ai_chat_max_tokens = fields.Integer(
        string='Tokens max par reponse',
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
        string='Recherche produits catalogue',
        config_parameter='lolirine_ai_chat.product_search',
        default=True,
    )
    ai_chat_save_conversations = fields.Boolean(
        string='Sauvegarder les conversations',
        config_parameter='lolirine_ai_chat.save_conversations',
        default=True,
    )
    ai_chat_system_prompt = fields.Char(
        string='Prompt systeme',
        config_parameter='lolirine_ai_chat.system_prompt',
        default='',
    )
    ai_chat_welcome_message = fields.Char(
        string='Message de bienvenue',
        config_parameter='lolirine_ai_chat.welcome_message',
        default='',
    )
    ai_chat_primary_color = fields.Char(
        string='Couleur principale',
        config_parameter='lolirine_ai_chat.primary_color',
        default='#0369a1',
    )
    ai_chat_secondary_color = fields.Char(
        string='Couleur secondaire',
        config_parameter='lolirine_ai_chat.secondary_color',
        default='#0d9488',
    )
    ai_chat_position = fields.Selection(
        [('right', 'Droite'), ('left', 'Gauche')],
        string='Position du widget',
        config_parameter='lolirine_ai_chat.position',
        default='right',
    )
    ai_chat_max_messages_session = fields.Integer(
        string='Messages max par session',
        config_parameter='lolirine_ai_chat.max_messages_session',
        default=50,
    )
    ai_chat_max_sessions_day = fields.Integer(
        string='Sessions max par IP/jour',
        config_parameter='lolirine_ai_chat.max_sessions_day',
        default=20,
    )
    ai_chat_website_id = fields.Integer(
        string='Site web (ID)',
        config_parameter='lolirine_ai_chat.website_id',
        default=0,
    )

    ai_chat_teaser_delay = fields.Integer(
        string='Délai apparition teaser (secondes)',
        config_parameter='lolirine_ai_chat.teaser_delay',
        default=5,
    )
    ai_chat_teaser_interval = fields.Integer(
        string='Intervalle réapparition teaser (heures, 0=désactivé)',
        config_parameter='lolirine_ai_chat.teaser_interval',
        default=24,
    )
