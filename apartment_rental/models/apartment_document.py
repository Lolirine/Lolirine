# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ApartmentDocument(models.Model):
    _name = 'apartment.document'
    _description = 'Document'
    _order = 'date desc, name'

    name = fields.Char(string='Nom', required=True)
    
    # Relations (un document peut être lié à plusieurs entités)
    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        ondelete='cascade',
    )
    tenant_id = fields.Many2one(
        'apartment.tenant',
        string='Locataire',
        ondelete='cascade',
    )
    lease_id = fields.Many2one(
        'apartment.lease',
        string='Bail',
        ondelete='cascade',
    )
    intervention_id = fields.Many2one(
        'apartment.intervention',
        string='Intervention',
        ondelete='cascade',
    )
    
    # Fichier
    file = fields.Binary(string='Fichier', required=True, attachment=True)
    file_name = fields.Char(string='Nom du fichier')
    file_size = fields.Integer(
        string='Taille',
        compute='_compute_file_size',
    )
    
    # Type de document
    document_type = fields.Selection([
        ('lease', 'Contrat de bail'),
        ('amendment', 'Avenant au bail'),
        ('inventory_entry', 'État des lieux d\'entrée'),
        ('inventory_exit', 'État des lieux de sortie'),
        ('id_card', 'Carte d\'identité'),
        ('income_proof', 'Justificatif de revenus'),
        ('insurance', 'Attestation d\'assurance'),
        ('bank_guarantee', 'Garantie bancaire'),
        ('registration', 'Enregistrement du bail'),
        ('peb', 'Certificat PEB'),
        ('quote', 'Devis'),
        ('invoice', 'Facture'),
        ('receipt', 'Quittance'),
        ('notice', 'Préavis'),
        ('letter', 'Courrier'),
        ('photo', 'Photo'),
        ('plan', 'Plan'),
        ('other', 'Autre'),
    ], string='Type', default='other')
    
    # Métadonnées
    date = fields.Date(
        string='Date du document',
        default=fields.Date.today,
    )
    expiry_date = fields.Date(string='Date d\'expiration')
    is_expired = fields.Boolean(
        string='Expiré',
        compute='_compute_is_expired',
        store=True,
    )
    
    # Validité
    is_signed = fields.Boolean(string='Signé')
    signed_date = fields.Date(string='Date de signature')
    signed_by = fields.Char(string='Signé par')
    
    # Origine
    source = fields.Selection([
        ('upload', 'Téléchargé'),
        ('generated', 'Généré'),
        ('received', 'Reçu'),
        ('scanned', 'Scanné'),
    ], string='Origine', default='upload')
    
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')

    def _compute_file_size(self):
        for record in self:
            if record.file:
                # Approximation de la taille (base64 augmente la taille d'environ 33%)
                record.file_size = len(record.file) * 3 // 4
            else:
                record.file_size = 0

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for record in self:
            record.is_expired = record.expiry_date and record.expiry_date < today

    def action_download(self):
        """Télécharger le document"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/apartment.document/{self.id}/file/{self.file_name}?download=true',
            'target': 'new',
        }
