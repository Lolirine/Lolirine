from odoo import models, fields, api
from datetime import timedelta


class StorageChatConversation(models.Model):
    _name = 'storage.chat.conversation'
    _description = 'Storage Chat Conversation'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Session', required=True, index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Client', index=True, ondelete='set null',
    )
    visitor_name = fields.Char(string='Visiteur', default='Anonyme')
    first_message = fields.Text(
        string='Premier message',
        compute='_compute_stats', store=True,
    )
    message_ids = fields.One2many(
        'storage.chat.message', 'conversation_id', string='Messages',
    )
    message_count = fields.Integer(
        string='Nb messages',
        compute='_compute_stats', store=True,
    )
    last_message_date = fields.Datetime(
        string='Dernier message',
        compute='_compute_stats', store=True,
    )
    duration_minutes = fields.Float(
        string='Duree (min)',
        compute='_compute_stats', store=True,
    )
    state = fields.Selection([
        ('active', 'Active'),
        ('closed', 'Terminee'),
        ('archived', 'Archivee'),
    ], string='Statut', default='active', index=True)
    source_url = fields.Char(string='Page source')
    ip_address = fields.Char(string='Adresse IP')
    user_agent = fields.Char(string='User Agent')
    rating = fields.Selection([
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
    ], string='Satisfaction')

    @api.depends('message_ids', 'message_ids.role', 'message_ids.create_date')
    def _compute_stats(self):
        for rec in self:
            msgs = rec.message_ids
            rec.message_count = len(msgs)
            user_msgs = msgs.filtered(lambda m: m.role == 'user')
            rec.first_message = user_msgs[0].content[:200] if user_msgs else ''
            if msgs:
                rec.last_message_date = msgs[-1].create_date
                if len(msgs) > 1 and msgs[0].create_date and msgs[-1].create_date:
                    delta = msgs[-1].create_date - msgs[0].create_date
                    rec.duration_minutes = round(delta.total_seconds() / 60.0, 1)
                else:
                    rec.duration_minutes = 0
            else:
                rec.last_message_date = False
                rec.duration_minutes = 0

    def action_close(self):
        self.write({'state': 'closed'})

    def action_archive_conv(self):
        self.write({'state': 'archived'})

    def action_reopen(self):
        self.write({'state': 'active'})

    @api.autovacuum
    def _gc_old_conversations(self):
        limit_date = fields.Datetime.now() - timedelta(days=90)
        old = self.search([
            ('state', '=', 'closed'),
            ('last_message_date', '<', limit_date),
        ])
        if old:
            old.write({'state': 'archived'})
