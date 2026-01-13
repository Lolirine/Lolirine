# -*- coding: utf-8 -*-
import base64
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BiztaxAttachment(models.Model):
    """
    PDF attachments for Biztax declaration
    These are the annexes that will be included in the .biztax package
    """
    _name = 'biztax.attachment'
    _description = 'Annexe Biztax'
    _order = 'annex_type, sequence'

    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
        ondelete='cascade',
    )
    
    name = fields.Char(
        string='Nom du document',
        required=True,
    )
    sequence = fields.Integer(default=10)
    
    annex_type = fields.Selection([
        # Standard annexes from Biztax
        ('275C', '275C - Tableau de situation'),
        ('275U', '275U - Déduction RDT'),
        ('275W', '275W - Exonération bénéfices de brevets'),
        ('275N', '275N - Innovation'),
        ('275F', '275F - Plus-values'), 
        ('275P', '275P - Provisions'),
        ('275K', '275K - Investissements'),
        ('275A', '275A - Versements anticipés'),
        ('275COC', '275COC - Contrôle interne'),
        ('275CbCR', '275CbCR - Country-by-Country'),
        ('275MKB', '275MKB - PME (petit entrepreneur)'),
        ('328S', '328S - Fiche de rémunération'),
        ('274DIV', '274DIV - Dividendes'),
        # Custom annexes
        ('balance', 'Bilan'),
        ('pnl', 'Compte de résultat'),
        ('annualreport', 'Comptes annuels'),
        ('other', 'Autre'),
    ], string='Type d\'annexe', required=True, default='other')
    
    # File data
    file_data = fields.Binary(
        string='Fichier',
        required=True,
        attachment=True,
    )
    file_name = fields.Char(
        string='Nom du fichier',
    )
    file_size = fields.Integer(
        string='Taille (Ko)',
        compute='_compute_file_size',
    )
    
    # For XBRL reference
    xbrl_attachment_id = fields.Char(
        string='ID XBRL',
        help="Identifiant unique dans le document XBRL",
    )
    
    description = fields.Text(string='Description')
    
    # Auto-generated from Odoo
    auto_generated = fields.Boolean(
        string='Généré automatiquement',
        default=False,
    )
    source_model = fields.Char(string='Modèle source')
    source_id = fields.Integer(string='ID source')

    @api.depends('file_data')
    def _compute_file_size(self):
        for record in self:
            if record.file_data:
                # Binary is base64 encoded, so actual size is ~75% of stored size
                record.file_size = int(len(record.file_data) * 0.75 / 1024)
            else:
                record.file_size = 0

    @api.constrains('file_data', 'file_name')
    def _check_file_type(self):
        for record in self:
            if record.file_name and not record.file_name.lower().endswith('.pdf'):
                raise ValidationError(
                    _("Seuls les fichiers PDF sont acceptés pour les annexes Biztax.")
                )
            if record.file_size > 50 * 1024:  # 50 MB max
                raise ValidationError(
                    _("La taille du fichier ne peut pas dépasser 50 Mo.")
                )

    @api.onchange('annex_type')
    def _onchange_annex_type(self):
        if self.annex_type and not self.name:
            # Set default name based on annex type
            annex_labels = dict(self._fields['annex_type'].selection)
            self.name = annex_labels.get(self.annex_type, self.annex_type)

    def _get_xbrl_attachment_id(self):
        """Generate unique XBRL attachment ID"""
        self.ensure_one()
        if not self.xbrl_attachment_id:
            self.xbrl_attachment_id = f"ATT_{self.annex_type}_{self.id}"
        return self.xbrl_attachment_id


class BiztaxAttachmentWizard(models.TransientModel):
    """Wizard to add attachment from Odoo reports"""
    _name = 'biztax.attachment.wizard'
    _description = 'Assistant d\'ajout d\'annexe'

    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
    )
    
    annex_type = fields.Selection([
        ('275C', '275C - Tableau de situation'),
        ('275U', '275U - Déduction RDT'),
        ('275N', '275N - Innovation'),
        ('275F', '275F - Plus-values'),
        ('275P', '275P - Provisions'),
        ('275K', '275K - Investissements'),
        ('275A', '275A - Versements anticipés'),
        ('balance', 'Bilan'),
        ('pnl', 'Compte de résultat'),
        ('annualreport', 'Comptes annuels'),
        ('other', 'Autre'),
    ], string='Type d\'annexe', required=True, default='other')
    
    source = fields.Selection([
        ('upload', 'Télécharger un fichier'),
        ('odoo_report', 'Générer depuis Odoo'),
    ], string='Source', default='upload')
    
    # Upload
    file_data = fields.Binary(string='Fichier PDF')
    file_name = fields.Char(string='Nom du fichier')
    
    # Odoo report
    odoo_report_id = fields.Many2one(
        'ir.actions.report',
        string='Rapport Odoo',
        domain=[('report_type', '=', 'qweb-pdf')],
    )

    def action_add_attachment(self):
        """Add the attachment to the declaration"""
        self.ensure_one()
        
        if self.source == 'upload':
            if not self.file_data:
                raise ValidationError(_("Veuillez sélectionner un fichier."))
            
            self.env['biztax.attachment'].create({
                'declaration_id': self.declaration_id.id,
                'name': self.file_name or f"Annexe {self.annex_type}",
                'annex_type': self.annex_type,
                'file_data': self.file_data,
                'file_name': self.file_name,
                'auto_generated': False,
            })
        
        elif self.source == 'odoo_report':
            if not self.odoo_report_id:
                raise ValidationError(_("Veuillez sélectionner un rapport."))
            
            # Generate PDF from Odoo report
            report = self.odoo_report_id
            pdf_content, _ = report._render_qweb_pdf(
                report.id, 
                [self.declaration_id.company_id.id]
            )
            
            self.env['biztax.attachment'].create({
                'declaration_id': self.declaration_id.id,
                'name': report.name,
                'annex_type': self.annex_type,
                'file_data': base64.b64encode(pdf_content),
                'file_name': f"{report.name}.pdf",
                'auto_generated': True,
                'source_model': report.model,
            })
        
        return {'type': 'ir.actions.act_window_close'}
