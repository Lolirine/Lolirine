# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Champ pour forcer/modifier le numéro d'abonnement
    subscription_reference = fields.Char(
        string='Référence abonnement',
        help='Référence personnalisée pour cet abonnement. Laissez vide pour générer automatiquement.',
        tracking=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create pour utiliser la référence personnalisée si fournie"""
        for vals in vals_list:
            # Si c'est un abonnement
            if vals.get('is_subscription') or vals.get('recurrence_id'):
                # Si une référence personnalisée est fournie, l'utiliser
                if vals.get('subscription_reference'):
                    vals['name'] = vals['subscription_reference']
                # Sinon, générer automatiquement via la séquence
                elif not vals.get('name') or vals.get('name') == '/':
                    # Chercher d'abord subscription.contract.custom, sinon sale.subscription
                    sequence = self.env['ir.sequence'].search([
                        ('code', '=', 'subscription.contract.custom')
                    ], limit=1)
                    if not sequence:
                        sequence = self.env['ir.sequence'].search([
                            ('code', '=', 'sale.subscription')
                        ], limit=1)
                    
                    if sequence:
                        vals['name'] = sequence.next_by_id()
                    else:
                        vals['name'] = self.env['ir.sequence'].next_by_code('subscription.contract.custom') or '/'
        
        return super().create(vals_list)

    def write(self, vals):
        """Override write pour permettre de modifier le numéro via subscription_reference"""
        for order in self:
            if vals.get('subscription_reference') and order.is_subscription:
                vals['name'] = vals['subscription_reference']
        return super().write(vals)

    @api.onchange('subscription_reference')
    def _onchange_subscription_reference(self):
        """Met à jour le nom quand on change la référence personnalisée"""
        if self.subscription_reference and self.is_subscription:
            self.name = self.subscription_reference

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

    def action_change_subscription_number(self):
        """Ouvre un wizard pour changer le numéro d'abonnement"""
        self.ensure_one()
        return {
            'name': _('Modifier le numéro d\'abonnement'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.change.subscription.number.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_current_number': self.name,
            }
        }

    def action_reset_subscription_sequence(self):
        """Action pour réinitialiser la séquence des abonnements"""
        # Chercher d'abord subscription.contract.custom, sinon sale.subscription
        sequence = self.env['ir.sequence'].search([
            ('code', '=', 'subscription.contract.custom')
        ], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].search([
                ('code', '=', 'sale.subscription')
            ], limit=1)
        
        if sequence:
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


class ChangeSubscriptionNumberWizard(models.TransientModel):
    _name = 'lolirine.change.subscription.number.wizard'
    _description = 'Wizard pour modifier le numéro d\'abonnement'

    sale_order_id = fields.Many2one('sale.order', string='Abonnement', required=True)
    current_number = fields.Char(string='Numéro actuel', readonly=True)
    new_number = fields.Char(string='Nouveau numéro', required=True)

    def action_change_number(self):
        """Change le numéro d'abonnement"""
        self.ensure_one()
        if self.new_number:
            # Vérifier l'unicité
            duplicate = self.env['sale.order'].search([
                ('name', '=', self.new_number),
                ('id', '!=', self.sale_order_id.id),
                ('is_subscription', '=', True)
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    _("Le numéro '%s' existe déjà pour l'abonnement %s.") % (self.new_number, duplicate.partner_id.name)
                )
            
            # Modifier directement via SQL pour contourner les restrictions
            self.env.cr.execute(
                "UPDATE sale_order SET name = %s, subscription_reference = %s WHERE id = %s",
                (self.new_number, self.new_number, self.sale_order_id.id)
            )
            # IMPORTANT: Commit pour valider la modification
            self.env.cr.commit()
            self.sale_order_id.invalidate_recordset(['name', 'subscription_reference'])
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Le numéro a été modifié en %s') % self.new_number,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
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
