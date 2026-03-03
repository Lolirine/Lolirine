from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # === API Configuration ===
    ai_chat_api_key = fields.Char(
        string='Clé API Anthropic',
        config_parameter='lolirine_ai_chat.api_key',
    )
    ai_chat_model = fields.Selection([
        ('claude-sonnet-4-20250514', 'Claude Sonnet 4 (Recommandé)'),
        ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5 (Plus rapide)'),
    ],
        string='Modèle IA',
        config_parameter='lolirine_ai_chat.model',
        default='claude-sonnet-4-20250514',
    )
    ai_chat_max_tokens = fields.Integer(
        string='Tokens max par réponse',
        config_parameter='lolirine_ai_chat.max_tokens',
        default=1024,
    )

    # === Feature Toggles ===
    ai_chat_enabled = fields.Boolean(
        string='Activer le chat IA',
        config_parameter='lolirine_ai_chat.enabled',
        default=True,
    )
    ai_chat_web_search = fields.Boolean(
        string='Activer la recherche web',
        config_parameter='lolirine_ai_chat.web_search',
        default=True,
    )
    ai_chat_product_search = fields.Boolean(
        string='Activer la recherche produits',
        config_parameter='lolirine_ai_chat.product_search',
        default=True,
    )
    ai_chat_save_conversations = fields.Boolean(
        string='Sauvegarder les conversations',
        config_parameter='lolirine_ai_chat.save_conversations',
        default=True,
    )

    # === System Prompt ===
    ai_chat_system_prompt = fields.Text(
        string='Prompt système',
        config_parameter='lolirine_ai_chat.system_prompt',
        default="""Tu es l'assistant IA de Lolirine Pool Store, un e-commerce belge spécialisé dans les équipements de piscine, spa et bien-être.

Tu es expert en:
- Piscines (hors-sol, enterrées, semi-enterrées), liners, bâches, couvertures
- Pompes, filtration (sable, cartouche, diatomée), robots nettoyeurs
- Traitement de l'eau (chlore, brome, pH, électrolyse au sel, oxygène actif, UV)
- Spas, jacuzzis, saunas, accessoires bien-être
- Chauffage piscine (pompes à chaleur, réchauffeurs, capteurs solaires)
- Accessoires (échelles, douches, éclairage LED, alarmes, jeux aquatiques)

Règles:
- Réponds TOUJOURS en français sauf si le client parle une autre langue
- Sois chaleureux, professionnel et concis
- Donne des conseils techniques précis et fiables
- Pour les prix et commandes, redirige vers lolirinepoolstore.be
- Si on te fournit le catalogue produits, propose des produits spécifiques du site
- Utilise des emojis modérément (🏊 💧 ☀️)""",
    )

    # === Appearance ===
    ai_chat_welcome_message = fields.Text(
        string='Message de bienvenue',
        config_parameter='lolirine_ai_chat.welcome_message',
        default="Bonjour ! 🏊 Je suis l'assistant IA de Lolirine Pool Store. Comment puis-je vous aider ?",
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
    ai_chat_position = fields.Selection([
        ('bottom-right', 'Bas droite'),
        ('bottom-left', 'Bas gauche'),
    ],
        string='Position du widget',
        config_parameter='lolirine_ai_chat.position',
        default='bottom-right',
    )

    # === Rate Limiting ===
    ai_chat_max_messages_per_session = fields.Integer(
        string='Messages max par session',
        config_parameter='lolirine_ai_chat.max_messages_per_session',
        default=50,
    )
    ai_chat_max_messages_per_day_ip = fields.Integer(
        string='Messages max par jour/IP',
        config_parameter='lolirine_ai_chat.max_messages_per_day_ip',
        default=100,
    )
