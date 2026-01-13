# -*- coding: utf-8 -*-
"""
Comprehensive management of Biztax annexes (formulaires 275xxx).
Features:
- Automatic detection of mandatory annexes based on declaration content
- PDF generation from Odoo accounting reports
- Proper integration in .biztax envelope with manifest
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
from datetime import date


class BiztaxAnnexRegistry(models.Model):
    """
    Registry of all official Biztax annexes with their requirements.
    Used to determine which annexes are mandatory based on declaration content.
    """
    _name = 'biztax.annex.registry'
    _description = 'Registre des annexes Biztax'
    _order = 'code'

    code = fields.Char(
        string='Code annexe',
        required=True,
    )
    name = fields.Char(
        string='Nom officiel',
        required=True,
        translate=True,
    )
    name_nl = fields.Char(string='Naam (NL)')
    
    category = fields.Selection([
        ('identification', 'Identification'),
        ('financial', 'États financiers'),
        ('dna', 'Dépenses non admises'),
        ('deduction', 'Déductions'),
        ('provision', 'Provisions'),
        ('capital_gain', 'Plus-values'),
        ('investment', 'Investissements'),
        ('prepayment', 'Versements anticipés'),
        ('international', 'International'),
        ('other', 'Autres'),
    ], string='Catégorie', required=True)
    
    # Conditions for mandatory status
    is_always_mandatory = fields.Boolean(
        string='Toujours obligatoire',
        default=False,
    )
    mandatory_condition = fields.Text(
        string='Condition d\'obligation',
        help="Description de la condition rendant l'annexe obligatoire",
    )
    mandatory_field = fields.Char(
        string='Champ déclencheur',
        help="Champ de la déclaration qui déclenche l'obligation (ex: total_dna > 0)",
    )
    mandatory_adjustment_category = fields.Char(
        string='Catégorie ajustement',
        help="Catégorie d'ajustement déclenchant l'annexe",
    )
    
    # Declaration types concerned
    applicable_rcorp = fields.Boolean(
        string='ISOC',
        default=True,
    )
    applicable_rle = fields.Boolean(
        string='IPM',
        default=True,
    )
    applicable_nrcorp = fields.Boolean(
        string='INR-Soc',
        default=True,
    )
    
    # Company size applicability
    applicable_large = fields.Boolean(
        string='Grandes sociétés',
        default=True,
    )
    applicable_small = fields.Boolean(
        string='Petites sociétés',
        default=True,
    )
    applicable_micro = fields.Boolean(
        string='Micro-sociétés',
        default=True,
    )
    
    # Odoo report for auto-generation
    can_auto_generate = fields.Boolean(
        string='Génération auto possible',
        default=False,
    )
    odoo_report_name = fields.Char(
        string='Rapport Odoo',
        help="Nom technique du rapport Odoo (ex: l10n_be_reports.action_account_report_be_coa)",
    )
    
    # Template/Form
    template_url = fields.Char(
        string='URL formulaire officiel',
    )
    
    description = fields.Text(string='Description')
    legal_reference = fields.Char(string='Base légale')
    active = fields.Boolean(default=True)


class BiztaxAnnexRequirement(models.Model):
    """
    Tracks which annexes are required for a specific declaration
    and their completion status.
    """
    _name = 'biztax.annex.requirement'
    _description = 'Annexe requise'
    _order = 'is_mandatory desc, registry_id'

    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
        ondelete='cascade',
    )
    registry_id = fields.Many2one(
        'biztax.annex.registry',
        string='Type d\'annexe',
        required=True,
    )
    
    code = fields.Char(
        related='registry_id.code',
        store=True,
    )
    name = fields.Char(
        related='registry_id.name',
        store=True,
    )
    
    is_mandatory = fields.Boolean(
        string='Obligatoire',
        default=False,
    )
    mandatory_reason = fields.Char(
        string='Raison',
    )
    
    status = fields.Selection([
        ('missing', 'Manquante'),
        ('draft', 'En préparation'),
        ('ready', 'Prête'),
        ('validated', 'Validée'),
    ], string='Statut', default='missing', compute='_compute_status', store=True)
    
    attachment_id = fields.Many2one(
        'biztax.attachment',
        string='Fichier joint',
    )
    
    can_auto_generate = fields.Boolean(
        related='registry_id.can_auto_generate',
    )
    
    notes = fields.Text(string='Notes')

    @api.depends('attachment_id', 'attachment_id.file_data')
    def _compute_status(self):
        for req in self:
            if req.attachment_id and req.attachment_id.file_data:
                req.status = 'ready'
            else:
                req.status = 'missing'

    def action_generate_annex(self):
        """Generate the annex from Odoo report"""
        self.ensure_one()
        
        if not self.registry_id.can_auto_generate:
            raise UserError(_(
                "Cette annexe ne peut pas être générée automatiquement. "
                "Veuillez la télécharger manuellement."
            ))
        
        if not self.registry_id.odoo_report_name:
            raise UserError(_("Aucun rapport Odoo configuré pour cette annexe."))
        
        # Find the report
        report = self.env.ref(self.registry_id.odoo_report_name, raise_if_not_found=False)
        if not report:
            raise UserError(_(
                "Rapport Odoo '%s' non trouvé. "
                "Veuillez installer le module correspondant."
            ) % self.registry_id.odoo_report_name)
        
        # Generate PDF
        company = self.declaration_id.company_id
        
        # Determine the correct record(s) to render
        if report.model == 'res.company':
            doc_ids = [company.id]
        elif report.model == 'biztax.declaration':
            doc_ids = [self.declaration_id.id]
        else:
            doc_ids = [company.id]
        
        try:
            pdf_content, _ = report._render_qweb_pdf(report.id, doc_ids)
        except Exception as e:
            raise UserError(_("Erreur lors de la génération du PDF: %s") % str(e))
        
        # Create attachment
        attachment = self.env['biztax.attachment'].create({
            'declaration_id': self.declaration_id.id,
            'name': self.registry_id.name,
            'annex_type': self.code,
            'file_data': base64.b64encode(pdf_content),
            'file_name': f"{self.code}_{company.enterprise_number}_{self.declaration_id.assessment_year}.pdf",
            'auto_generated': True,
            'source_model': report.model,
        })
        
        self.attachment_id = attachment
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Annexe générée'),
                'message': _("L'annexe %s a été générée avec succès.") % self.code,
                'type': 'success',
            }
        }


class BiztaxDeclarationAnnexMixin(models.Model):
    """Mixin to add annex management to declarations"""
    _inherit = 'biztax.declaration'

    annex_requirement_ids = fields.One2many(
        'biztax.annex.requirement',
        'declaration_id',
        string='Annexes requises',
    )
    
    mandatory_annex_count = fields.Integer(
        compute='_compute_annex_stats',
        string='Annexes obligatoires',
    )
    missing_annex_count = fields.Integer(
        compute='_compute_annex_stats',
        string='Annexes manquantes',
    )
    annex_completion_rate = fields.Float(
        compute='_compute_annex_stats',
        string='Taux de complétion',
    )

    @api.depends('annex_requirement_ids', 'annex_requirement_ids.status', 
                 'annex_requirement_ids.is_mandatory')
    def _compute_annex_stats(self):
        for decl in self:
            mandatory = decl.annex_requirement_ids.filtered(lambda r: r.is_mandatory)
            decl.mandatory_annex_count = len(mandatory)
            decl.missing_annex_count = len(mandatory.filtered(lambda r: r.status == 'missing'))
            
            if decl.mandatory_annex_count > 0:
                ready = len(mandatory.filtered(lambda r: r.status in ('ready', 'validated')))
                decl.annex_completion_rate = (ready / decl.mandatory_annex_count) * 100
            else:
                decl.annex_completion_rate = 100

    def action_detect_required_annexes(self):
        """Analyze declaration and detect which annexes are mandatory"""
        self.ensure_one()
        
        AnnexRegistry = self.env['biztax.annex.registry']
        AnnexRequirement = self.env['biztax.annex.requirement']
        
        # Remove existing requirements that were auto-detected
        self.annex_requirement_ids.filtered(lambda r: not r.attachment_id).unlink()
        
        # Get all active annex types
        registries = AnnexRegistry.search([('active', '=', True)])
        
        for registry in registries:
            # Check declaration type applicability
            if self.declaration_type == 'rcorp' and not registry.applicable_rcorp:
                continue
            if self.declaration_type == 'rle' and not registry.applicable_rle:
                continue
            if self.declaration_type == 'nrcorp' and not registry.applicable_nrcorp:
                continue
            
            # Check company size applicability
            company = self.company_id
            if hasattr(company, 'is_micro_company'):
                if company.is_micro_company and not registry.applicable_micro:
                    continue
                if company.is_small_company and not company.is_micro_company and not registry.applicable_small:
                    continue
                if not company.is_small_company and not registry.applicable_large:
                    continue
            
            # Determine if mandatory
            is_mandatory = False
            reason = ""
            
            # Always mandatory
            if registry.is_always_mandatory:
                is_mandatory = True
                reason = _("Toujours obligatoire")
            
            # Check field condition
            elif registry.mandatory_field:
                try:
                    # Evaluate field condition (e.g., "total_dna > 0")
                    field_name = registry.mandatory_field.split()[0]
                    if hasattr(self, field_name):
                        field_value = getattr(self, field_name)
                        if field_value and float(field_value) > 0:
                            is_mandatory = True
                            reason = registry.mandatory_condition or f"{field_name} > 0"
                except Exception:
                    pass
            
            # Check adjustment category
            elif registry.mandatory_adjustment_category:
                categories = registry.mandatory_adjustment_category.split(',')
                for adj in self.adjustment_ids:
                    if adj.category in categories and adj.amount > 0:
                        is_mandatory = True
                        reason = _("Ajustement %s présent") % adj.category
                        break
            
            # Specific rules by annex code
            is_mandatory, reason = self._check_specific_annex_rules(registry, is_mandatory, reason)
            
            # Create requirement if mandatory or commonly used
            if is_mandatory or registry.is_always_mandatory:
                existing = self.annex_requirement_ids.filtered(
                    lambda r: r.registry_id.id == registry.id
                )
                if not existing:
                    AnnexRequirement.create({
                        'declaration_id': self.id,
                        'registry_id': registry.id,
                        'is_mandatory': is_mandatory,
                        'mandatory_reason': reason,
                    })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Annexes détectées'),
                'message': _('%d annexes obligatoires détectées') % self.mandatory_annex_count,
                'type': 'success',
            }
        }

    def _check_specific_annex_rules(self, registry, is_mandatory, reason):
        """Check specific rules for each annex type"""
        
        # 275C - Provisions
        if registry.code == '275C':
            provisions = self.adjustment_ids.filtered(
                lambda a: a.category in ('provision', 'dna_provision')
            )
            if provisions and sum(provisions.mapped('amount')) > 0:
                return True, _("Provisions présentes")
        
        # 275F - Frais de voiture
        elif registry.code == '275F':
            car_dna = self.adjustment_ids.filtered(
                lambda a: a.category in ('dna', 'dna_car') or 
                         (a.tax_code_id and 'voiture' in (a.tax_code_id.name or '').lower())
            )
            if car_dna and sum(car_dna.mapped('amount')) > 0:
                return True, _("DNA frais de voiture")
        
        # 275K - Déduction investissement
        elif registry.code == '275K':
            invest = self.adjustment_ids.filtered(lambda a: a.category == 'investment')
            if invest and sum(invest.mapped('amount')) > 0:
                return True, _("Déduction pour investissement")
        
        # 275N - NID (Intérêts notionnels)
        elif registry.code == '275N':
            nid = self.adjustment_ids.filtered(lambda a: a.category == 'rdi')
            if nid and sum(nid.mapped('amount')) > 0:
                return True, _("Déduction intérêts notionnels")
        
        # 275U - Plus-values
        elif registry.code == '275U':
            pv = self.adjustment_ids.filtered(lambda a: a.category == 'plus_value')
            if pv and sum(pv.mapped('amount')) > 0:
                return True, _("Plus-values à déclarer")
        
        # 275P - Pertes antérieures
        elif registry.code == '275P':
            losses = self.adjustment_ids.filtered(lambda a: a.category == 'loss_carryforward')
            if losses and sum(losses.mapped('amount')) > 0:
                return True, _("Déduction pertes antérieures")
        
        # 275W - Innovation
        elif registry.code == '275W':
            innovation = self.adjustment_ids.filtered(lambda a: a.category == 'innovation')
            if innovation and sum(innovation.mapped('amount')) > 0:
                return True, _("Déduction innovation")
        
        # 275A - Versements anticipés
        elif registry.code == '275A':
            if self.prepayments and self.prepayments > 0:
                return True, _("Versements anticipés déclarés")
        
        # 328S - Secret commissionnel
        elif registry.code == '328S':
            secret = self.adjustment_ids.filtered(
                lambda a: 'secret' in (a.name or '').lower() or 
                         'commission' in (a.name or '').lower()
            )
            if secret:
                return True, _("Commissions secrètes")
        
        return is_mandatory, reason

    def action_generate_all_annexes(self):
        """Generate all auto-generable annexes"""
        self.ensure_one()
        
        generated = 0
        errors = []
        
        for req in self.annex_requirement_ids.filtered(
            lambda r: r.can_auto_generate and r.status == 'missing'
        ):
            try:
                req.action_generate_annex()
                generated += 1
            except UserError as e:
                errors.append(f"{req.code}: {str(e)}")
        
        message = _("%d annexes générées") % generated
        if errors:
            message += "\n\n" + _("Erreurs:") + "\n" + "\n".join(errors)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Génération terminée'),
                'message': message,
                'type': 'success' if not errors else 'warning',
            }
        }

    def action_view_annex_requirements(self):
        """View annex requirements"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Annexes requises'),
            'res_model': 'biztax.annex.requirement',
            'view_mode': 'list,form',
            'domain': [('declaration_id', '=', self.id)],
            'context': {'default_declaration_id': self.id},
        }


class BiztaxAttachmentExtended(models.Model):
    """Extended attachment with manifest support"""
    _inherit = 'biztax.attachment'

    # Manifest data
    manifest_id = fields.Char(
        string='ID Manifest',
        compute='_compute_manifest_id',
        store=True,
    )
    manifest_sequence = fields.Integer(
        string='Séquence manifest',
        default=10,
    )
    
    # Validation
    is_validated = fields.Boolean(
        string='Validé',
        default=False,
    )
    validation_date = fields.Datetime(
        string='Date validation',
    )
    validated_by = fields.Many2one(
        'res.users',
        string='Validé par',
    )

    @api.depends('declaration_id', 'annex_type')
    def _compute_manifest_id(self):
        for att in self:
            if att.declaration_id and att.annex_type:
                # Use id if available, otherwise use a placeholder
                record_id = att.id if att.id else 'NEW'
                att.manifest_id = f"ATT-{att.annex_type}-{record_id}"
            else:
                att.manifest_id = False

    def get_manifest_entry(self):
        """Generate manifest entry for this attachment"""
        self.ensure_one()
        return {
            'id': self.manifest_id,
            'type': self.annex_type,
            'filename': self.file_name,
            'description': self.name,
            'size': self.file_size * 1024,  # Convert back to bytes
            'sequence': self.manifest_sequence,
        }

    def action_validate(self):
        """Mark attachment as validated"""
        self.ensure_one()
        self.write({
            'is_validated': True,
            'validation_date': fields.Datetime.now(),
            'validated_by': self.env.user.id,
        })
