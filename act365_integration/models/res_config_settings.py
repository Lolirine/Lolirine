# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuration ACT365
    act365_api_url = fields.Char(
        string='URL API ACT365',
        config_parameter='act365.api_url',
        default='https://api.act365.eu',
        help="URL de base de l'API ACT365 (ex: https://api.act365.eu)",
    )
    act365_api_key = fields.Char(
        string='Clé API ACT365',
        config_parameter='act365.api_key',
        help="Clé API générée depuis votre compte ACT365 (Profile > Apps & Integrations)",
    )
    act365_default_group_id = fields.Many2one(
        'act365.cardholder.group',
        string='Groupe ACT365 par défaut',
        help="Groupe de cardholders par défaut pour les nouveaux abonnés",
    )
    act365_pin_length = fields.Integer(
        string='Longueur du code PIN',
        config_parameter='act365.pin_length',
        default=4,
        help="Nombre de chiffres pour les codes PIN générés automatiquement",
    )
    act365_auto_sync = fields.Boolean(
        string='Synchronisation automatique',
        config_parameter='act365.auto_sync',
        default=True,
        help="Synchroniser automatiquement les cardholders lors de la validation d'un abonnement",
    )
    act365_enable_on_confirm = fields.Boolean(
        string='Activer à la confirmation',
        config_parameter='act365.enable_on_confirm',
        default=True,
        help="Activer automatiquement le cardholder lors de la confirmation de l'abonnement",
    )
    act365_disable_on_close = fields.Boolean(
        string='Désactiver à la clôture',
        config_parameter='act365.disable_on_close',
        default=True,
        help="Désactiver automatiquement le cardholder lors de la clôture/résiliation de l'abonnement",
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Récupérer l'ID du groupe par défaut
        default_group_id = ICP.get_param('act365.default_group_id', default='0')
        try:
            default_group_id = int(default_group_id)
        except (ValueError, TypeError):
            default_group_id = 0
        
        res.update(
            act365_default_group_id=default_group_id if default_group_id else False,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Sauvegarder l'ID du groupe par défaut
        ICP.set_param('act365.default_group_id', 
                      self.act365_default_group_id.id if self.act365_default_group_id else '0')
        
        # Mettre à jour le flag is_default sur le groupe
        if self.act365_default_group_id:
            self.act365_default_group_id.set_as_default()

    def action_test_act365_connection(self):
        """Teste la connexion à l'API ACT365"""
        self.ensure_one()
        
        ACT365API = self.env['act365.api']
        result = ACT365API.test_connection()
        
        notification_type = 'success' if result['success'] else 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test de connexion ACT365'),
                'message': result['message'],
                'type': notification_type,
                'sticky': False,
            }
        }

    def action_sync_act365_groups(self):
        """Synchronise les groupes de cardholders depuis ACT365"""
        self.ensure_one()
        
        ACT365API = self.env['act365.api']
        result = ACT365API.sync_cardholder_groups()
        
        notification_type = 'success' if result['success'] else 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation ACT365'),
                'message': result['message'],
                'type': notification_type,
                'sticky': False,
            }
        }

    def action_open_act365_groups(self):
        """Ouvre la liste des groupes ACT365"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Groupes ACT365'),
            'res_model': 'act365.cardholder.group',
            'view_mode': 'tree,form',
            'target': 'current',
        }
