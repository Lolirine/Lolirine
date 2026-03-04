from odoo import models, fields


class StorageChatMessage(models.Model):
    _name = 'storage.chat.message'
    _description = 'Storage Chat Message'
    _order = 'create_date asc, id asc'

    conversation_id = fields.Many2one(
        'storage.chat.conversation', string='Conversation',
        required=True, ondelete='cascade', index=True,
    )
    role = fields.Selection([
        ('user', 'Client'),
        ('assistant', 'Assistant IA'),
        ('system', 'Systeme'),
    ], string='Role', required=True, index=True)
    content = fields.Text(string='Contenu', required=True)
    has_web_search = fields.Boolean(string='Recherche web', default=False)
    web_sources = fields.Text(string='Sources web (JSON)')
    tokens_used = fields.Integer(string='Tokens utilises')
    response_time_ms = fields.Integer(string='Temps de reponse (ms)')
    model_used = fields.Char(string='Modele IA')
