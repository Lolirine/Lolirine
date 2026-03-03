from odoo import models, fields


class AiChatConversation(models.Model):
    _name = 'ai.chat.conversation'
    _description = 'AI Chat Conversation'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Session', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Client', index=True, ondelete='set null')
    visitor_name = fields.Char(string='Visiteur', default='Anonyme')
    message_ids = fields.One2many('ai.chat.message', 'conversation_id', string='Messages')
    state = fields.Selection([
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ], string='Statut', default='active', index=True)
    source_url = fields.Char(string='Page source')
    rating = fields.Selection([
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
    ], string='Satisfaction')

    def action_close(self):
        self.write({'state': 'closed'})

    def action_archive_conv(self):
        self.write({'state': 'archived'})

    def action_reopen(self):
        self.write({'state': 'active'})
