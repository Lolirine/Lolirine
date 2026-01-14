# -*- coding: utf-8 -*-
"""
Biztax Attachment Model - PDF annexes for declarations
"""
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiztaxAttachment(models.Model):
    """
    Attachment/Annex for Biztax declaration.
    Manages PDF documents that must be included in the .biztax package.
    """
    _name = 'biztax.attachment'
    _description = 'Annexe Biztax'
    _order = 'sequence, id'

    # -------------------------------------------------------------------------
    # BASIC FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Description',
        required=True,
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
    )
    
    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    # -------------------------------------------------------------------------
    # ATTACHMENT TYPE
    # -------------------------------------------------------------------------
    annex_type = fields.Selection([
        # Mandatory annexes
        ('275c', '275C - Relevé des dirigeants'),
        ('275w', '275W - Relevé des prêts'),
        ('276', '276 - Rémunérations du personnel'),
        ('328', '328 - Fiches fiscales'),
        
        # Financial statements
        ('annual_accounts', 'Comptes annuels'),
        ('balance_sheet', 'Bilan'),
        ('income_statement', 'Compte de résultats'),
        ('notes', 'Annexes aux comptes annuels'),
        
        # Tax specific
        ('dna_detail', 'Détail DNA'),
        ('vehicle_list', 'Liste véhicules de société'),
        ('provisions_detail', 'Détail provisions'),
        ('plus_values', 'Détail plus-values'),
        ('rdt_detail', 'Détail RDT'),
        ('losses_detail', 'Historique pertes'),
        ('investment_deduction', 'Déduction pour investissement'),
        
        # Transfer pricing
        ('transfer_pricing', 'Documentation prix de transfert'),
        ('local_file', 'Local File'),
        ('master_file', 'Master File'),
        ('cbcr', 'Country-by-Country Report'),
        
        # Other
        ('power_of_attorney', 'Procuration'),
        ('mandate', 'Mandat représentant'),
        ('other', 'Autre document'),
    ], string='Type d\'annexe', required=True, default='other')
    
    is_mandatory = fields.Boolean(
        string='Obligatoire',
        compute='_compute_is_mandatory',
        store=True,
    )
    
    # -------------------------------------------------------------------------
    # FILE DATA
    # -------------------------------------------------------------------------
    file_data = fields.Binary(
        string='Fichier PDF',
        attachment=True,
        required=True,
    )
    
    file_name = fields.Char(
        string='Nom du fichier',
    )
    
    file_size = fields.Integer(
        string='Taille (Ko)',
        compute='_compute_file_size',
    )
    
    file_mimetype = fields.Char(
        string='Type MIME',
        default='application/pdf',
    )
    
    # -------------------------------------------------------------------------
    # GENERATION FROM ODOO
    # -------------------------------------------------------------------------
    generated_from_odoo = fields.Boolean(
        string='Généré depuis Odoo',
        default=False,
        help="Document généré automatiquement par Odoo",
    )
    
    source_report = fields.Char(
        string='Rapport source',
        help="XML ID du rapport QWeb utilisé pour générer ce document",
    )
    
    # -------------------------------------------------------------------------
    # NOTES
    # -------------------------------------------------------------------------
    notes = fields.Text(
        string='Notes',
    )
    
    # -------------------------------------------------------------------------
    # COMPUTED FIELDS
    # -------------------------------------------------------------------------
    @api.depends('annex_type')
    def _compute_is_mandatory(self):
        """Determine if annex type is mandatory"""
        mandatory_types = ['275c', '275w', '276', 'annual_accounts']
        for record in self:
            record.is_mandatory = record.annex_type in mandatory_types
    
    @api.depends('file_data')
    def _compute_file_size(self):
        for record in self:
            if record.file_data:
                # file_data is base64, actual size is ~75% of base64 length
                record.file_size = int(len(record.file_data) * 0.75 / 1024)
            else:
                record.file_size = 0
    
    # -------------------------------------------------------------------------
    # ONCHANGE
    # -------------------------------------------------------------------------
    @api.onchange('annex_type')
    def _onchange_annex_type(self):
        """Set default name based on annex type"""
        type_names = {
            '275c': 'Relevé 275C - Dirigeants',
            '275w': 'Relevé 275W - Prêts',
            '276': 'Relevé 276 - Rémunérations',
            '328': 'Fiches fiscales 328',
            'annual_accounts': 'Comptes annuels',
            'balance_sheet': 'Bilan',
            'income_statement': 'Compte de résultats',
            'dna_detail': 'Détail des DNA',
            'vehicle_list': 'Liste des véhicules',
            'provisions_detail': 'Détail des provisions',
            'plus_values': 'Plus-values réalisées',
            'rdt_detail': 'Revenus définitivement taxés',
            'losses_detail': 'Historique des pertes',
        }
        if self.annex_type and not self.name:
            self.name = type_names.get(self.annex_type, '')
    
    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('file_data', 'file_name')
    def _check_pdf(self):
        """Ensure file is PDF"""
        for record in self:
            if record.file_name and not record.file_name.lower().endswith('.pdf'):
                raise ValidationError(_(
                    "Seuls les fichiers PDF sont acceptés pour les annexes Biztax."
                ))
    
    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------
    def get_file_content(self):
        """Return decoded file content"""
        self.ensure_one()
        if self.file_data:
            return base64.b64decode(self.file_data)
        return b''
    
    def get_biztax_filename(self):
        """Return filename for biztax package"""
        self.ensure_one()
        if self.file_name:
            return self.file_name
        return f"{self.annex_type}_{self.id}.pdf"
