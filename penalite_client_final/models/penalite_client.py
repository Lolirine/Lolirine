from odoo import models, fields, api
from datetime import date

class PenaliteClient(models.Model):
    _name = "penalite_client"
    _description = "Pénalité Client"
    _order = "date desc"

    partner_id = fields.Many2one('res_partner', string="Client", required=True)
    montant = fields.Float(string="Montant", required=True)
    motif = fields.Char(string="Motif", required=True)
    date = fields.Date(string="Date", default=fields.Date.today)
    statut = fields.Selection([('non_paye', 'Non payé'), ('paye', 'Payé')], string="Statut", default='non_paye')

    @api.model
    def create_penalite_for_canceled_subscriptions(self):
        subs = self.env['sale_subscription'].search([
            ('stage_id.category', '=', 'closed'),
            ('date_end', '<', fields.Date.today())
        ])
        for sub in subs:
            if not self.search([('partner_id', '=', sub.partner_id.id), ('motif', '=', 'Annulation tardive')]):
                self.create({
                    'partner_id': sub.partner_id.id,
                    'montant': 50.0,
                    'motif': 'Annulation tardive',
                    'date': fields.Date.today(),
                })
