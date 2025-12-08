# -*- coding: utf-8 -*-

from odoo import models, fields, api


class VisiteChecklistTemplate(models.Model):
    """Template de check-list pour les visites"""
    _name = 'visite.checklist.template'
    _description = 'Modèle de check-list de visite'
    _order = 'sequence, id'

    name = fields.Char(string='Nom du modèle', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(default=True)
    item_ids = fields.One2many(
        'visite.checklist.template.item',
        'template_id',
        string='Éléments'
    )
    is_default = fields.Boolean(
        string='Modèle par défaut',
        help='Ce modèle sera utilisé automatiquement pour les nouvelles visites'
    )

    @api.model
    def create(self, vals):
        if vals.get('is_default'):
            self.search([('is_default', '=', True)]).write({'is_default': False})
        return super().create(vals)

    def write(self, vals):
        if vals.get('is_default'):
            self.search([('is_default', '=', True), ('id', 'not in', self.ids)]).write({'is_default': False})
        return super().write(vals)


class VisiteChecklistTemplateItem(models.Model):
    """Élément de template de check-list"""
    _name = 'visite.checklist.template.item'
    _description = 'Élément de modèle de check-list'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'visite.checklist.template',
        string='Modèle',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Élément', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    is_required = fields.Boolean(string='Obligatoire', default=False)
    category = fields.Selection([
        ('accueil', 'Accueil'),
        ('besoin', 'Analyse du besoin'),
        ('visite', 'Visite des lieux'),
        ('explication', 'Explications'),
        ('closing', 'Closing'),
    ], string='Catégorie', default='visite')
    help_text = fields.Text(string='Aide / Instructions')


class VisiteChecklistLine(models.Model):
    """Ligne de check-list pour une visite spécifique"""
    _name = 'visite.checklist.line'
    _description = 'Ligne de check-list de visite'
    _order = 'sequence, id'

    visite_id = fields.Many2one(
        'visite.box',
        string='Visite',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Élément', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    is_done = fields.Boolean(string='Fait', default=False)
    is_required = fields.Boolean(string='Obligatoire', default=False)
    notes = fields.Text(string='Notes')
    done_by = fields.Many2one(
        'res.users',
        string='Fait par',
        readonly=True
    )
    done_date = fields.Datetime(
        string='Date',
        readonly=True
    )

    def action_toggle_done(self):
        """Toggle l'état de la check-list"""
        for record in self:
            if record.is_done:
                record.write({
                    'is_done': False,
                    'done_by': False,
                    'done_date': False,
                })
            else:
                record.write({
                    'is_done': True,
                    'done_by': self.env.user.id,
                    'done_date': fields.Datetime.now(),
                })
