# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    # ==========================================
    # Champs spécifiques Piscine
    # ==========================================
    
    is_pool_request = fields.Boolean(
        string='Demande Piscine',
        default=False,
    )
    
    pool_service_type = fields.Selection([
        ('entretien', 'Entretien & Réparation'),
        ('construction', 'Construction & Rénovation'),
        ('analyse', 'Analyse de l\'eau'),
        ('hivernage', 'Hivernage'),
        ('estivage', 'Remise en service'),
        ('contrat_ponctuel', 'Visite Ponctuelle'),
        ('contrat_saison', 'Contrat Saison'),
        ('contrat_annuel', 'Contrat Annuel'),
        ('autre', 'Autre'),
    ], string='Type de service')
    
    pool_type = fields.Selection([
        ('enterree', 'Piscine enterrée'),
        ('hors_sol', 'Piscine hors-sol'),
        ('semi_enterree', 'Piscine semi-enterrée'),
        ('interieure', 'Piscine intérieure'),
        ('naturelle', 'Piscine naturelle'),
        ('autre', 'Autre'),
    ], string='Type de piscine')
    
    pool_dimensions = fields.Char(string='Dimensions')
    pool_volume = fields.Float(string='Volume (m³)')
    
    pool_treatment = fields.Selection([
        ('chlore', 'Chlore'),
        ('sel', 'Électrolyse au sel'),
        ('brome', 'Brome'),
        ('oxygene', 'Oxygène actif'),
        ('uv', 'UV'),
        ('autre', 'Autre'),
        ('inconnu', 'Je ne sais pas'),
    ], string='Traitement actuel')
    
    pool_problem = fields.Text(string='Description du besoin')
    
    pool_urgency = fields.Selection([
        ('low', 'Pas urgent'),
        ('medium', 'Dans le mois'),
        ('high', 'Urgent'),
        ('critical', 'Très urgent'),
    ], string='Urgence', default='medium')
    
    pool_address = fields.Char(string='Adresse piscine')
    
    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        for lead in leads:
            if lead.is_pool_request:
                pool_tag = self.env['crm.tag'].search([('name', '=', 'Pool Store')], limit=1)
                if not pool_tag:
                    pool_tag = self.env['crm.tag'].create({'name': 'Pool Store', 'color': 4})
                lead.tag_ids = [(4, pool_tag.id)]
        return leads
