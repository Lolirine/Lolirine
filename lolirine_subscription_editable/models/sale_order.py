# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Champ pour forcer un numéro spécifique
    force_subscription_number = fields.Integer(
        string='Forcer numéro',
        help='Si renseigné, ce numéro sera utilisé pour générer la référence au format CTR/ANNÉE/NUMÉRO'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create pour générer le numéro d'abonnement automatiquement"""
        for vals in vals_list:
            # Si c'est un abonnement et que le nom n'est pas défini ou est '/'
            if vals.get('is_subscription') or vals.get('recurrence_id'):
                if not vals.get('name') or vals.get('name') == '/':
                    # Utiliser la séquence standard des abonnements
                    sequence = self.env['ir.sequence'].search([
                        ('code', '=', 'sale.subscription')
                    ], limit=1)
                    if sequence:
                        vals['name'] = sequence.next_by_id()
                    else:
                        # Fallback si pas de séquence trouvée
                        vals['name'] = self.env['ir.sequence'].next_by_code('sale.subscription') or '/'
        
        return super().create(vals_list)

    @api.onchange('force_subscription_number')
    def _onchange_force_subscription_number(self):
        """Génère automatiquement la référence basée sur le numéro forcé"""
        if self.force_subscription_number and self.force_subscription_number > 0:
            year = fields.Date.today().year
            self.name = "CTR/%s/%03d" % (year, self.force_subscription_number)

    @api.constrains('name')
    def _check_unique_subscription_name(self):
        """Vérifie que le numéro d'abonnement est unique"""
        for order in self:
            if order.name and order.name != '/' and order.is_subscription:
                duplicate = self.search([
                    ('name', '=', order.name),
                    ('id', '!=', order.id),
                    ('is_subscription', '=', True)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("Le numéro d'abonnement '%s' existe déjà. Veuillez en choisir un autre.") % order.name
                    )

    def action_reset_subscription_sequence(self):
        """Action pour réinitialiser la séquence des abonnements"""
        sequence = self.env['ir.sequence'].search([
            ('code', '=', 'sale.subscription')
        ], limit=1)
        
        if sequence:
            # Ouvrir un wizard pour choisir le prochain numéro
            return {
                'name': _('Réinitialiser la séquence'),
                'type': 'ir.actions.act_window',
                'res_model': 'lolirine.subscription.sequence.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_sequence_id': sequence.id,
                    'default_current_number': sequence.number_next_actual,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur'),
                    'message': _('Séquence des abonnements non trouvée.'),
                    'type': 'warning',
                }
            }


class SubscriptionSequenceWizard(models.TransientModel):
    _name = 'lolirine.subscription.sequence.wizard'
    _description = 'Wizard pour réinitialiser la séquence des abonnements'

    sequence_id = fields.Many2one('ir.sequence', string='Séquence', readonly=True)
    current_number = fields.Integer(string='Numéro actuel', readonly=True)
    new_number = fields.Integer(string='Nouveau numéro', required=True, default=1)

    def action_reset_sequence(self):
        """Réinitialise la séquence au numéro choisi"""
        self.ensure_one()
        if self.sequence_id and self.new_number > 0:
            self.sequence_id.sudo().write({
                'number_next_actual': self.new_number
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('La séquence a été réinitialisée à %s.') % self.new_number,
                    'type': 'success',
                    'sticky': False,
                }
            }
