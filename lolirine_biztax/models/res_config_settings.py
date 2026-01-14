# -*- coding: utf-8 -*-
"""
Configuration Settings for Biztax Module
Accessible via Settings → Biztax
"""

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # =============================================
    # COMPANY FISCAL INFORMATION
    # =============================================
    
    # BCE/KBO Number
    company_bce_number = fields.Char(
        related='company_id.bce_number',
        readonly=False,
        string="Numéro BCE/KBO",
        help="Numéro d'entreprise à la Banque-Carrefour des Entreprises (format: 0XXX.XXX.XXX)"
    )
    
    # Tax Identification Number (if different from BCE)
    company_tax_identification_number = fields.Char(
        related='company_id.tax_identification_number',
        readonly=False,
        string="Numéro d'identification fiscale",
        help="Numéro d'identification fiscale si différent du BCE"
    )
    
    # Legal Form
    company_legal_form = fields.Selection(
        related='company_id.legal_form',
        readonly=False,
        string="Forme juridique"
    )
    
    # NACE Code
    company_nace_code = fields.Char(
        related='company_id.nace_code',
        readonly=False,
        string="Code NACE",
        help="Code d'activité économique NACE-BEL"
    )
    
    # SME Status
    company_is_sme = fields.Boolean(
        related='company_id.is_sme',
        readonly=False,
        string="PME",
        help="L'entreprise est-elle une PME au sens fiscal belge?"
    )
    
    # =============================================
    # FISCAL YEAR CONFIGURATION
    # =============================================
    
    company_fiscal_year_start_day = fields.Integer(
        related='company_id.fiscal_year_start_day',
        readonly=False,
        string="Jour de début"
    )
    
    company_fiscal_year_start_month = fields.Selection(
        related='company_id.fiscal_year_start_month',
        readonly=False,
        string="Mois de début"
    )
    
    # =============================================
    # BIZTAX CONFIGURATION
    # =============================================
    
    # Default Taxonomy Version
    biztax_default_taxonomy = fields.Selection(
        related='company_id.biztax_default_taxonomy',
        readonly=False,
        string="Version taxonomie par défaut"
    )
    
    # Auto-generate standard adjustments
    biztax_auto_adjustments = fields.Boolean(
        related='company_id.biztax_auto_adjustments',
        readonly=False,
        string="Ajustements automatiques",
        help="Générer automatiquement les ajustements standards lors de la création d'une déclaration"
    )
    
    # Default Tax Rate
    biztax_default_tax_rate = fields.Float(
        related='company_id.biztax_default_tax_rate',
        readonly=False,
        string="Taux ISOC par défaut (%)"
    )
    
    # SME Reduced Rate
    biztax_sme_reduced_rate = fields.Float(
        related='company_id.biztax_sme_reduced_rate',
        readonly=False,
        string="Taux réduit PME (%)"
    )
    
    # SME Reduced Rate Threshold
    biztax_sme_threshold = fields.Float(
        related='company_id.biztax_sme_threshold',
        readonly=False,
        string="Seuil taux réduit PME (€)",
        help="Montant de base imposable jusqu'auquel le taux réduit PME s'applique"
    )
    
    # =============================================
    # ANNEXES CONFIGURATION
    # =============================================
    
    biztax_auto_generate_annexes = fields.Boolean(
        related='company_id.biztax_auto_generate_annexes',
        readonly=False,
        string="Générer annexes automatiquement",
        help="Générer automatiquement les annexes PDF obligatoires"
    )
    
    biztax_include_balance_sheet = fields.Boolean(
        related='company_id.biztax_include_balance_sheet',
        readonly=False,
        string="Inclure bilan",
        help="Inclure automatiquement le bilan dans les annexes"
    )
    
    biztax_include_profit_loss = fields.Boolean(
        related='company_id.biztax_include_profit_loss',
        readonly=False,
        string="Inclure compte de résultat",
        help="Inclure automatiquement le compte de résultat dans les annexes"
    )
    
    # =============================================
    # REPRESENTATIVE INFORMATION
    # =============================================
    
    company_representative_id = fields.Many2one(
        related='company_id.biztax_representative_id',
        readonly=False,
        string="Représentant légal",
        help="Personne autorisée à signer les déclarations fiscales"
    )
    
    company_accountant_id = fields.Many2one(
        related='company_id.biztax_accountant_id',
        readonly=False,
        string="Comptable/Expert-comptable",
        help="Comptable ou expert-comptable responsable"
    )
    
    # =============================================
    # ACTIONS
    # =============================================
    
    def action_open_tax_codes(self):
        """Open tax codes configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Codes fiscaux XBRL',
            'res_model': 'biztax.tax.code',
            'view_mode': 'list,form',
            'context': {'default_active': True},
        }
    
    def action_open_declaration_types(self):
        """Open declaration types configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Types de déclaration',
            'res_model': 'biztax.declaration.type',
            'view_mode': 'list,form',
        }
    
    def action_open_annexe_types(self):
        """Open annexe types configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Types d\'annexes',
            'res_model': 'biztax.annexe.type',
            'view_mode': 'list,form',
        }
    
    def action_sync_tax_codes(self):
        """Synchronize tax codes with latest taxonomy"""
        self.env['biztax.tax.code'].sudo().sync_from_taxonomy()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Synchronisation',
                'message': 'Codes fiscaux synchronisés avec succès',
                'type': 'success',
                'sticky': False,
            }
        }
