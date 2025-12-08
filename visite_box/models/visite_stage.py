# -*- coding: utf-8 -*-

from odoo import models, fields


class VisiteStage(models.Model):
    _name = 'visite.stage'
    _description = 'Étape de visite'
    _order = 'sequence, id'

    name = fields.Char(string='Nom de l\'étape', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    
    fold = fields.Boolean(
        string='Replié dans le Kanban',
        help='Cette étape sera repliée par défaut dans la vue Kanban',
    )
    
    is_won = fields.Boolean(
        string='Étape gagnée',
        help='Cochez si cette étape représente une visite convertie en contrat',
    )
    is_lost = fields.Boolean(
        string='Étape perdue',
        help='Cochez si cette étape représente une visite annulée ou perdue',
    )
    
    requirements = fields.Text(
        string='Prérequis',
        help='Actions requises avant de passer à cette étape',
    )
    
    description = fields.Text(string='Description')
    color = fields.Integer(string='Couleur')
    
    visite_ids = fields.One2many(
        'visite.box',
        'stage_id',
        string='Visites',
    )
    visite_count = fields.Integer(
        string='Nombre de visites',
        compute='_compute_visite_count',
    )
    
    def _compute_visite_count(self):
        for stage in self:
            stage.visite_count = len(stage.visite_ids)
