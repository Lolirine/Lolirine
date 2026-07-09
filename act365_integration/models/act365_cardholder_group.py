# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ACT365CardholderGroup(models.Model):
    """Modèle pour stocker les groupes de cardholders ACT365"""
    _name = 'act365.cardholder.group'
    _description = 'Groupe de Cardholders ACT365'
    _order = 'name'

    name = fields.Char(
        string='Nom du groupe',
        required=True,
    )
    act365_id = fields.Char(
        string='ID ACT365',
        required=True,
        index=True,
    )
    description = fields.Text(
        string='Description',
    )
    is_default = fields.Boolean(
        string='Groupe par défaut',
        default=False,
        help="Si coché, ce groupe sera utilisé par défaut pour les nouveaux abonnés",
    )
    active = fields.Boolean(
        string='Actif',
        default=True,
    )

    act365_id_unique = models.Constraint(
        'unique(act365_id)',
        "L'ID ACT365 doit être unique!",
    )

    @api.model
    def get_default_group(self):
        """Retourne le groupe par défaut"""
        group = self.search([('is_default', '=', True)], limit=1)
        if not group:
            group = self.search([], limit=1)
        return group

    def set_as_default(self):
        """Définit ce groupe comme groupe par défaut"""
        self.ensure_one()
        # Retirer le flag default des autres groupes
        self.search([('is_default', '=', True)]).write({'is_default': False})
        self.is_default = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Succès'),
                'message': _('"%s" est maintenant le groupe par défaut') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }
