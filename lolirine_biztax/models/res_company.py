# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Biztax specific fields
    biztax_contact_name = fields.Char(
        string='Contact Biztax (Nom)',
        help="Nom de la personne de contact pour les déclarations Biztax",
    )
    biztax_contact_email = fields.Char(
        string='Contact Biztax (Email)',
    )
    biztax_contact_phone = fields.Char(
        string='Contact Biztax (Téléphone)',
    )
    
    # Company legal form for Biztax
    legal_form = fields.Selection([
        ('SA', 'Société Anonyme (SA/NV)'),
        ('SRL', 'Société à Responsabilité Limitée (SRL/BV)'),
        ('SC', 'Société Coopérative (SC/CV)'),
        ('SNC', 'Société en Nom Collectif (SNC/VOF)'),
        ('SCS', 'Société en Commandite Simple (SCS/CommV)'),
        ('SCA', 'Société en Commandite par Actions (SCA/CommVA)'),
        ('ASBL', 'Association Sans But Lucratif (ASBL/VZW)'),
        ('AISBL', 'Association Internationale (AISBL/IVZW)'),
        ('Foundation', 'Fondation (Stichting)'),
        ('Other', 'Autre'),
    ], string='Forme juridique')
    
    # Tax settings
    default_tax_rate = fields.Float(
        string='Taux ISOC standard (%)',
        default=25.0,
    )
    default_tax_rate_reduced = fields.Float(
        string='Taux réduit PME (%)',
        default=20.0,
    )
    
    # SME criteria
    is_sme_fiscal = fields.Boolean(
        string='PME au sens fiscal',
        help="La société répond aux critères PME de l'article 15 CDE",
        default=True,
    )
    employee_count = fields.Integer(
        string='Effectif moyen annuel',
    )
    annual_turnover = fields.Monetary(
        string='Chiffre d\'affaires annuel',
        currency_field='currency_id',
    )
    balance_sheet_total = fields.Monetary(
        string='Total du bilan',
        currency_field='currency_id',
    )
    
    # Linked company for groups
    parent_company_id = fields.Many2one(
        'res.company',
        string='Société mère',
    )
    is_group_member = fields.Boolean(
        string='Membre d\'un groupe',
        compute='_compute_is_group_member',
    )
    
    # Prepayment settings
    va_account_number = fields.Char(
        string='N° compte versements anticipés',
        help="Numéro de compte bancaire pour les versements anticipés",
    )

    @api.depends('parent_company_id')
    def _compute_is_group_member(self):
        for company in self:
            company.is_group_member = bool(company.parent_company_id)

    def action_open_biztax_declarations(self):
        """Open Biztax declarations for this company"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Déclarations Biztax'),
            'res_model': 'biztax.declaration',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
        }

    def action_create_biztax_mappings(self):
        """Create default account mappings from templates"""
        self.ensure_one()
        templates = self.env['biztax.account.mapping.template'].search([])
        
        for template in templates:
            existing = self.env['biztax.account.mapping'].search([
                ('company_id', '=', self.id),
                ('account_code_prefix', '=', template.account_code_prefix),
            ])
            if not existing:
                template.action_apply_to_company(self)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mappings créés'),
                'message': _('Les mappings par défaut ont été créés pour cette société.'),
                'type': 'success',
            }
        }
