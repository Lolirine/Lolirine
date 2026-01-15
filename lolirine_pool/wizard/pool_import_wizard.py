# -*- coding: utf-8 -*-
import base64
import csv
import io
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PoolImportWizard(models.TransientModel):
    """Assistant d'import de produits piscine"""
    _name = 'pool.import.wizard'
    _description = "Assistant d'import piscine"

    supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur',
        required=True
    )
    
    import_method = fields.Selection([
        ('csv', 'Import CSV/Excel'),
        ('api', 'API REST'),
        ('ocr', 'OCR (catalogue PDF)'),
    ], string="Méthode d'import", default='csv', required=True)
    
    # Fichier
    file_data = fields.Binary(string='Fichier à importer')
    file_name = fields.Char(string='Nom du fichier')
    
    # Options
    update_existing = fields.Boolean(
        string='Mettre à jour les produits existants',
        default=True,
        help="Si coché, les produits existants seront mis à jour avec les nouvelles valeurs"
    )
    create_category = fields.Boolean(
        string='Créer les catégories manquantes',
        default=True
    )
    import_images = fields.Boolean(
        string='Importer les images',
        default=True,
        help="Télécharger les images depuis les URLs fournies"
    )
    
    # Prévisualisation
    preview_line_ids = fields.One2many(
        'pool.import.wizard.line',
        'wizard_id',
        string='Aperçu des données'
    )
    preview_count = fields.Integer(
        string='Lignes détectées',
        compute='_compute_preview_count'
    )
    
    # État
    state = fields.Selection([
        ('upload', 'Chargement'),
        ('preview', 'Aperçu'),
        ('done', 'Terminé'),
    ], default='upload')
    
    # Résultat
    import_log_id = fields.Many2one('pool.import.log', string='Log import créé')
    
    @api.depends('preview_line_ids')
    def _compute_preview_count(self):
        for wizard in self:
            wizard.preview_count = len(wizard.preview_line_ids)
    
    @api.onchange('supplier_id')
    def _onchange_supplier(self):
        if self.supplier_id:
            self.import_method = self.supplier_id.import_method
    
    def action_preview(self):
        """Analyser le fichier et afficher un aperçu"""
        self.ensure_one()
        
        if not self.file_data:
            raise UserError(_("Veuillez charger un fichier."))
        
        # Nettoyer les anciennes lignes
        self.preview_line_ids.unlink()
        
        if self.import_method == 'csv':
            self._preview_csv()
        else:
            raise UserError(_("Seul l'import CSV est supporté pour l'instant."))
        
        self.state = 'preview'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _preview_csv(self):
        """Prévisualiser un fichier CSV"""
        file_content = base64.b64decode(self.file_data)
        encoding = self.supplier_id.csv_encoding or 'utf-8'
        delimiter = self.supplier_id.csv_delimiter or ';'
        
        try:
            text_content = file_content.decode(encoding)
        except UnicodeDecodeError:
            text_content = file_content.decode('latin-1')
        
        reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
        
        # Mapping des champs
        field_mapping = {
            m.source_field: m for m in self.supplier_id.field_mapping_ids
        }
        
        lines = []
        for i, row in enumerate(reader):
            if i >= 10:  # Limiter à 10 lignes pour l'aperçu
                break
            
            if i < (self.supplier_id.csv_skip_lines or 0):
                continue
            
            # Extraire les infos principales
            ref = ''
            name = ''
            price = 0.0
            
            for source_field, value in row.items():
                if source_field in field_mapping:
                    mapping = field_mapping[source_field]
                    target = mapping.target_field
                    transformed = mapping.apply_transformation(value)
                    
                    if target == 'default_code':
                        ref = transformed
                    elif target == 'name':
                        name = transformed
                    elif target == 'standard_price':
                        try:
                            price = float(transformed) if transformed else 0.0
                        except (ValueError, TypeError):
                            price = 0.0
            
            lines.append((0, 0, {
                'wizard_id': self.id,
                'product_ref': ref,
                'product_name': name or ref,
                'cost_price': price,
                'raw_data': str(row)[:500],
            }))
        
        self.preview_line_ids = lines
    
    def action_import(self):
        """Lancer l'import"""
        self.ensure_one()
        
        # Créer le log d'import
        log = self.env['pool.import.log'].create({
            'supplier_id': self.supplier_id.id,
            'import_method': self.import_method,
            'file_data': self.file_data,
            'file_name': self.file_name,
            'update_existing': self.update_existing,
            'create_category': self.create_category,
            'import_images': self.import_images,
        })
        
        # Lancer le traitement
        log.action_process()
        
        self.import_log_id = log
        self.state = 'done'
        
        # Afficher le résultat
        return {
            'name': _('Résultat import'),
            'type': 'ir.actions.act_window',
            'res_model': 'pool.import.log',
            'res_id': log.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_back(self):
        """Retour à l'étape précédente"""
        self.state = 'upload'
        self.preview_line_ids.unlink()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class PoolImportWizardLine(models.TransientModel):
    """Ligne d'aperçu pour l'assistant d'import"""
    _name = 'pool.import.wizard.line'
    _description = "Ligne aperçu import piscine"

    wizard_id = fields.Many2one(
        'pool.import.wizard',
        string='Assistant',
        ondelete='cascade'
    )
    
    product_ref = fields.Char(string='Référence')
    product_name = fields.Char(string='Nom')
    cost_price = fields.Float(string='Prix achat')
    raw_data = fields.Text(string='Données brutes')
