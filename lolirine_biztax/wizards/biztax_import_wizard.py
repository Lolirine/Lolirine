# -*- coding: utf-8 -*-
import base64
import csv
import io
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiztaxImportWizard(models.TransientModel):
    """Wizard to import fiscal adjustments from various sources"""
    _name = 'biztax.import.wizard'
    _description = 'Assistant d\'importation d\'ajustements'

    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
    )
    
    import_type = fields.Selection([
        ('csv', 'Fichier CSV'),
        ('excel', 'Fichier Excel'),
        ('previous', 'Déclaration précédente'),
        ('template', 'Modèles prédéfinis'),
    ], string='Source d\'importation', required=True, default='csv')
    
    # File import
    file_data = fields.Binary(string='Fichier')
    file_name = fields.Char(string='Nom du fichier')
    
    # Previous declaration
    previous_declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration précédente',
        domain="[('company_id', '=', company_id), ('id', '!=', declaration_id)]",
    )
    company_id = fields.Many2one(
        related='declaration_id.company_id',
    )
    
    # Template selection
    template_ids = fields.Many2many(
        'biztax.adjustment.template',
        string='Modèles à importer',
    )
    
    # Options
    replace_existing = fields.Boolean(
        string='Remplacer les ajustements existants',
        default=False,
    )
    import_amounts = fields.Boolean(
        string='Importer les montants',
        default=True,
    )

    def action_import(self):
        """Execute the import"""
        self.ensure_one()
        
        if self.import_type == 'csv':
            return self._import_from_csv()
        elif self.import_type == 'excel':
            return self._import_from_excel()
        elif self.import_type == 'previous':
            return self._import_from_previous()
        elif self.import_type == 'template':
            return self._import_from_templates()
        
        return {'type': 'ir.actions.act_window_close'}

    def _import_from_csv(self):
        """Import adjustments from CSV file"""
        if not self.file_data:
            raise UserError(_("Veuillez sélectionner un fichier CSV."))
        
        # Decode and parse CSV
        csv_data = base64.b64decode(self.file_data)
        try:
            # Try UTF-8 first, then fallback to latin-1
            try:
                content = csv_data.decode('utf-8')
            except UnicodeDecodeError:
                content = csv_data.decode('latin-1')
            
            reader = csv.DictReader(io.StringIO(content), delimiter=';')
            
            if self.replace_existing:
                self.declaration_id.adjustment_ids.unlink()
            
            imported_count = 0
            for row in reader:
                # Expected columns: code, name, category, type, amount
                code = row.get('code', '').strip()
                if not code:
                    continue
                
                tax_code = self.env['biztax.tax.code'].search([
                    ('code', '=', code),
                    ('taxonomy_version', '=', self.declaration_id.taxonomy_version),
                ], limit=1)
                
                if not tax_code:
                    # Try to find by name
                    name = row.get('name', '').strip()
                    if name:
                        tax_code = self.env['biztax.tax.code'].search([
                            ('name', 'ilike', name),
                            ('taxonomy_version', '=', self.declaration_id.taxonomy_version),
                        ], limit=1)
                
                if tax_code:
                    amount = 0
                    if self.import_amounts:
                        amount_str = row.get('amount', '0').replace(',', '.').replace(' ', '')
                        try:
                            amount = float(amount_str)
                        except ValueError:
                            amount = 0
                    
                    self.env['biztax.adjustment'].create({
                        'declaration_id': self.declaration_id.id,
                        'tax_code_id': tax_code.id,
                        'name': row.get('name', tax_code.name),
                        'category': row.get('category', 'other'),
                        'adjustment_type': row.get('type', 'increase'),
                        'amount': abs(amount),
                    })
                    imported_count += 1
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import terminé'),
                    'message': _('%d ajustements importés.') % imported_count,
                    'type': 'success',
                }
            }
            
        except Exception as e:
            raise UserError(_("Erreur lors de l'importation CSV: %s") % str(e))

    def _import_from_excel(self):
        """Import adjustments from Excel file"""
        if not self.file_data:
            raise UserError(_("Veuillez sélectionner un fichier Excel."))
        
        try:
            import openpyxl
        except ImportError:
            raise UserError(_("Le module openpyxl est requis pour l'import Excel."))
        
        try:
            excel_data = base64.b64decode(self.file_data)
            workbook = openpyxl.load_workbook(io.BytesIO(excel_data))
            sheet = workbook.active
            
            if self.replace_existing:
                self.declaration_id.adjustment_ids.unlink()
            
            imported_count = 0
            headers = [cell.value for cell in sheet[1]]
            
            for row in sheet.iter_rows(min_row=2, values_only=True):
                row_dict = dict(zip(headers, row))
                
                code = str(row_dict.get('code', '')).strip()
                if not code:
                    continue
                
                tax_code = self.env['biztax.tax.code'].search([
                    ('code', '=', code),
                    ('taxonomy_version', '=', self.declaration_id.taxonomy_version),
                ], limit=1)
                
                if tax_code:
                    amount = 0
                    if self.import_amounts:
                        amount = row_dict.get('amount', 0) or 0
                        if isinstance(amount, str):
                            amount = float(amount.replace(',', '.').replace(' ', ''))
                    
                    self.env['biztax.adjustment'].create({
                        'declaration_id': self.declaration_id.id,
                        'tax_code_id': tax_code.id,
                        'name': row_dict.get('name', tax_code.name),
                        'category': row_dict.get('category', 'other'),
                        'adjustment_type': row_dict.get('type', 'increase'),
                        'amount': abs(amount),
                    })
                    imported_count += 1
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import terminé'),
                    'message': _('%d ajustements importés.') % imported_count,
                    'type': 'success',
                }
            }
            
        except Exception as e:
            raise UserError(_("Erreur lors de l'importation Excel: %s") % str(e))

    def _import_from_previous(self):
        """Import adjustments from a previous declaration"""
        if not self.previous_declaration_id:
            raise UserError(_("Veuillez sélectionner une déclaration précédente."))
        
        if self.replace_existing:
            self.declaration_id.adjustment_ids.unlink()
        
        imported_count = 0
        for adj in self.previous_declaration_id.adjustment_ids:
            self.env['biztax.adjustment'].create({
                'declaration_id': self.declaration_id.id,
                'tax_code_id': adj.tax_code_id.id,
                'name': adj.name,
                'category': adj.category,
                'adjustment_type': adj.adjustment_type,
                'amount': adj.amount if self.import_amounts else 0,
                'dna_percentage': adj.dna_percentage,
                'notes': adj.notes,
            })
            imported_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': _('%d ajustements importés depuis %s.') % (
                    imported_count, self.previous_declaration_id.name
                ),
                'type': 'success',
            }
        }

    def _import_from_templates(self):
        """Import adjustments from templates"""
        if not self.template_ids:
            raise UserError(_("Veuillez sélectionner au moins un modèle."))
        
        if self.replace_existing:
            self.declaration_id.adjustment_ids.unlink()
        
        imported_count = 0
        for template in self.template_ids:
            template.action_create_adjustment(self.declaration_id)
            imported_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': _('%d ajustements créés depuis les modèles.') % imported_count,
                'type': 'success',
            }
        }
