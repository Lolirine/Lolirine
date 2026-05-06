# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command


class PartnerPenalty(models.Model):
    _name = 'partner.penalty'
    _description = 'Pénalité client'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', required=True, copy=False,
                       readonly=True, default='Nouveau')
    partner_id = fields.Many2one('res.partner', string='Client', required=True,
                                  ondelete='cascade', tracking=True)
    penalty_type_id = fields.Many2one('partner.penalty.type', string='Type de pénalité',
                                       required=True, tracking=True)
    category = fields.Selection(related='penalty_type_id.category', store=True,
                                 string='Catégorie')

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today,
                       tracking=True)
    amount = fields.Float(string='Montant (€)', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('invoiced', 'Facturé'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    invoice_id = fields.Many2one('account.move', string='Facture', readonly=True)

    description = fields.Text(string='Description / Motif')
    notes = fields.Text(string='Notes internes')

    # Champs liés au box
    product_id = fields.Many2one('product.template', string='Box concerné',
                                  domain="[('is_storage_box', '=', True)]")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('partner.penalty') or 'Nouveau'
        return super().create(vals_list)

    @api.onchange('penalty_type_id')
    def _onchange_penalty_type_id(self):
        if self.penalty_type_id:
            self.amount = self.penalty_type_id.default_amount

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_create_invoice(self):
        """Crée une facture pour cette pénalité"""
        self.ensure_one()
        if not self.partner_id:
            return

        # Rechercher un produit "Pénalité" ou en créer un
        product = self.env['product.product'].search([
            ('default_code', '=', 'PENALTY')
        ], limit=1)

        if not product:
            product = self.env['product.product'].create({
                'name': 'Pénalité / Frais',
                'default_code': 'PENALTY',
                'type': 'service',
                'list_price': 0,
                'taxes_id': [Command.clear()],
            })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.date,
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'name': f"{self.penalty_type_id.name}\n{self.description or ''}",
                'quantity': 1,
                'price_unit': self.amount,
            })],
        })

        self.write({
            'invoice_id': invoice.id,
            'state': 'invoiced',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
