from odoo import models, fields


class AiChatMessage(models.Model):
    _name = 'ai.chat.message'
    _description = 'AI Chat Message'
    _order = 'create_date asc, id asc'

    conversation_id = fields.Many2one(
        'ai.chat.conversation',
        string='Conversation',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # === Content ===
    role = fields.Selection([
        ('user', 'Client'),
        ('assistant', 'Assistant IA'),
        ('system', 'Système'),
    ], string='Rôle', required=True, index=True)
    content = fields.Text(string='Contenu', required=True)

    # === Web Search ===
    has_web_search = fields.Boolean(
        string='Recherche web',
        default=False,
    )
    web_sources = fields.Text(
        string='Sources web',
        help='Sources web utilisées (JSON)',
    )

    # === Metadata ===
    tokens_used = fields.Integer(string='Tokens utilisés')
    response_time_ms = fields.Integer(string='Temps de réponse (ms)')
    model_used = fields.Char(string='Modèle IA', default='claude-sonnet-4-20250514')

    # === Product Context ===
    product_ids = fields.Many2many(
        'product.template',
        string='Produits mentionnés',
    )
