# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuration de l'indexation
    indexation_index_type = fields.Selection([
        ('health', 'Indice Santé Belge'),
        ('cpi', 'Indice des Prix à la Consommation (CPI)'),
        ('custom', 'Indice Personnalisé'),
    ], string='Type d\'indice par défaut',
        config_parameter='storage_indexation.default_index_type',
        default='health')
    
    indexation_auto_fetch = fields.Boolean(
        string='Récupération automatique des indices',
        config_parameter='storage_indexation.auto_fetch_index',
        default=True,
        help="Récupère automatiquement l'indice santé depuis Statbel chaque mois"
    )
    
    indexation_notification_days = fields.Integer(
        string='Jours avant notification',
        config_parameter='storage_indexation.notification_days',
        default=30,
        help="Nombre de jours avant la date d'application pour envoyer les notifications"
    )
    
    indexation_auto_apply = fields.Boolean(
        string='Application automatique',
        config_parameter='storage_indexation.auto_apply',
        default=False,
        help="Applique automatiquement l'indexation après notification (non recommandé)"
    )
    
    indexation_min_increase = fields.Float(
        string='Augmentation minimum (%)',
        config_parameter='storage_indexation.min_increase',
        default=0.0,
        help="Seuil minimum d'augmentation pour déclencher une indexation"
    )
    
    indexation_round_precision = fields.Selection([
        ('0.01', '0.01 € (centime)'),
        ('0.05', '0.05 €'),
        ('0.10', '0.10 €'),
        ('1.00', '1.00 € (euro)'),
    ], string='Précision d\'arrondi',
        config_parameter='storage_indexation.round_precision',
        default='0.01')
    
    indexation_email_template_id = fields.Many2one(
        'mail.template',
        string='Template d\'email',
        config_parameter='storage_indexation.email_template_id',
        help="Template utilisé pour les notifications d'indexation"
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    indexation_enabled = fields.Boolean(
        string='Indexation activée',
        default=True
    )
    default_base_year = fields.Integer(
        string='Année de base par défaut',
        default=2013,
        help="Année de référence pour l'indice santé (base 100)"
    )
