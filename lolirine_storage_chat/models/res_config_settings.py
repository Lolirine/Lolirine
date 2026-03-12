from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    storage_chat_api_key = fields.Char(
        string='Cle API Anthropic (Garde-meuble)',
        config_parameter='lolirine_storage_chat.api_key',
        default='',
    )
    storage_chat_model = fields.Selection(
        [
            ('claude-sonnet-4-20250514', 'Claude Sonnet 4'),
            ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5'),
        ],
        string='Modele IA (Garde-meuble)',
        config_parameter='lolirine_storage_chat.model',
        default='claude-sonnet-4-20250514',
    )
    storage_chat_max_tokens = fields.Integer(
        string='Tokens max (Garde-meuble)',
        config_parameter='lolirine_storage_chat.max_tokens',
        default=1024,
    )
    storage_chat_enabled = fields.Boolean(
        string='Activer le chat IA (Garde-meuble)',
        config_parameter='lolirine_storage_chat.enabled',
        default=True,
    )
    storage_chat_web_search = fields.Boolean(
        string='Recherche web (Garde-meuble)',
        config_parameter='lolirine_storage_chat.web_search',
        default=True,
    )
    storage_chat_save_conversations = fields.Boolean(
        string='Sauvegarder conversations (Garde-meuble)',
        config_parameter='lolirine_storage_chat.save_conversations',
        default=True,
    )
    storage_chat_system_prompt = fields.Char(
        string='Prompt systeme (Garde-meuble)',
        config_parameter='lolirine_storage_chat.system_prompt',
        default='',
    )
    storage_chat_welcome_message = fields.Char(
        string='Message de bienvenue (Garde-meuble)',
        config_parameter='lolirine_storage_chat.welcome_message',
        default='',
    )
    storage_chat_primary_color = fields.Char(
        string='Couleur principale (Garde-meuble)',
        config_parameter='lolirine_storage_chat.primary_color',
        default='#C91E18',
    )
    storage_chat_secondary_color = fields.Char(
        string='Couleur secondaire (Garde-meuble)',
        config_parameter='lolirine_storage_chat.secondary_color',
        default='#8B0000',
    )
    storage_chat_position = fields.Selection(
        [('right', 'Droite'), ('left', 'Gauche')],
        string='Position du widget (Garde-meuble)',
        config_parameter='lolirine_storage_chat.position',
        default='right',
    )
    storage_chat_max_messages_session = fields.Integer(
        string='Messages max par session (Garde-meuble)',
        config_parameter='lolirine_storage_chat.max_messages_session',
        default=50,
    )
    storage_chat_website_id = fields.Integer(
        string='Site web ID (Garde-meuble)',
        config_parameter='lolirine_storage_chat.website_id',
        default=1,
    )

    storage_chat_teaser_delay = fields.Integer(
        string='Délai apparition teaser (secondes)',
        config_parameter='lolirine_storage_chat.teaser_delay',
        default=5,
    )
    storage_chat_teaser_interval = fields.Integer(
        string='Intervalle réapparition teaser (heures, 0=une seule fois)',
        config_parameter='lolirine_storage_chat.teaser_interval',
        default=24,
    )
