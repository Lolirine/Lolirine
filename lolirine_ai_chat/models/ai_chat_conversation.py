from odoo import models, fields, api
from datetime import timedelta


class AiChatConversation(models.Model):
    _name = 'ai.chat.conversation'
    _description = 'AI Chat Conversation'
    _order = 'last_message_date desc, id desc'
    _rec_name = 'conversation_name'

    # === Identification ===
    session_id = fields.Char(
        string='Session ID',
        required=True,
        index=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        index=True,
        ondelete='set null',
    )
    visitor_name = fields.Char(
        string='Visiteur',
        default='Visiteur anonyme',
    )

    # === Messages ===
    message_ids = fields.One2many(
        'ai.chat.message',
        'conversation_id',
        string='Messages',
    )
    message_count = fields.Integer(
        string='Nombre de messages',
        compute='_compute_message_count',
        store=True,
    )

    # === Metadata ===
    conversation_name = fields.Char(
        string='Conversation',
        compute='_compute_conversation_name',
        store=True,
    )
    first_message = fields.Text(
        string='Premier message',
        compute='_compute_first_message',
        store=True,
    )
    last_message_date = fields.Datetime(
        string='Dernier message',
        compute='_compute_last_message_date',
        store=True,
    )
    start_date = fields.Datetime(
        string='Début',
        default=fields.Datetime.now,
        readonly=True,
    )
    duration_minutes = fields.Float(
        string='Durée (min)',
        compute='_compute_duration',
        store=True,
    )

    # === Status ===
    state = fields.Selection([
        ('active', 'Active'),
        ('closed', 'Terminée'),
        ('archived', 'Archivée'),
    ], string='Statut', default='active', index=True)

    # === Analytics ===
    source_url = fields.Char(string='Page source')
    user_agent = fields.Char(string='User Agent')
    ip_address = fields.Char(string='Adresse IP')
    rating = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐'),
    ], string='Satisfaction')
    web_searches_count = fields.Integer(
        string='Recherches web',
        compute='_compute_web_searches_count',
        store=True,
    )

    @api.depends('message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    @api.depends('session_id', 'partner_id', 'visitor_name', 'start_date')
    def _compute_conversation_name(self):
        for rec in self:
            name = rec.partner_id.name or rec.visitor_name or 'Anonyme'
            date = rec.start_date.strftime('%d/%m/%Y %H:%M') if rec.start_date else ''
            rec.conversation_name = f"{name} — {date}"

    @api.depends('message_ids', 'message_ids.content')
    def _compute_first_message(self):
        for rec in self:
            user_msgs = rec.message_ids.filtered(lambda m: m.role == 'user').sorted('create_date')
            rec.first_message = user_msgs[0].content[:150] if user_msgs else ''

    @api.depends('message_ids', 'message_ids.create_date')
    def _compute_last_message_date(self):
        for rec in self:
            if rec.message_ids:
                rec.last_message_date = max(rec.message_ids.mapped('create_date'))
            else:
                rec.last_message_date = rec.start_date

    @api.depends('start_date', 'last_message_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.last_message_date:
                delta = rec.last_message_date - rec.start_date
                rec.duration_minutes = round(delta.total_seconds() / 60, 1)
            else:
                rec.duration_minutes = 0

    @api.depends('message_ids', 'message_ids.has_web_search')
    def _compute_web_searches_count(self):
        for rec in self:
            rec.web_searches_count = len(rec.message_ids.filtered('has_web_search'))

    def action_close(self):
        self.write({'state': 'closed'})

    def action_archive(self):
        self.write({'state': 'archived'})

    def action_reopen(self):
        self.write({'state': 'active'})

    @api.autovacuum
    def _gc_old_conversations(self):
        """Auto-clean conversations older than 90 days."""
        limit_date = fields.Datetime.now() - timedelta(days=90)
        old_convs = self.search([
            ('state', '=', 'closed'),
            ('last_message_date', '<', limit_date),
        ])
        old_convs.write({'state': 'archived'})
