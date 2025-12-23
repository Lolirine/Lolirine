# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Champs ACT365
    act365_access_code = fields.Char(
        string='Code d\'accès ACT365',
        tracking=True,
        help="Code PIN principal pour l'accès au garde-meubles",
    )
    act365_cardholder_ids = fields.Char(
        string='IDs Cardholders ACT365',
        help="Liste des IDs de cardholders ACT365 associés (séparés par des virgules)",
    )
    
    # Champ calculé pour afficher les abonnements avec accès ACT365
    act365_subscription_ids = fields.One2many(
        'sale.order',
        'partner_id',
        string='Abonnements ACT365',
        domain=[('is_subscription', '=', True), ('act365_access_code', '!=', False)],
    )
    act365_subscription_count = fields.Integer(
        string='Nb. Abonnements ACT365',
        compute='_compute_act365_subscription_count',
    )

    @api.depends('act365_subscription_ids')
    def _compute_act365_subscription_count(self):
        for partner in self:
            partner.act365_subscription_count = len(partner.act365_subscription_ids)

    def action_view_act365_subscriptions(self):
        """Ouvre la liste des abonnements avec code ACT365"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Abonnements Garde-Meubles'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('is_subscription', '=', True),
                ('act365_access_code', '!=', False),
            ],
            'context': {'default_partner_id': self.id},
        }

    def action_copy_access_code(self):
        """Action pour copier le code d'accès (utile pour l'interface)"""
        self.ensure_one()
        if self.act365_access_code:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Code d\'accès'),
                    'message': _('Code d\'accès: %s') % self.act365_access_code,
                    'type': 'info',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Code d\'accès'),
                    'message': _('Aucun code d\'accès attribué'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
