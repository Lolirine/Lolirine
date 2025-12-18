# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LolirineScanTvaDocuments(models.Model):
    _inherit = 'lolirine.scan.tva'

    # Champ pour stocker l'ID du document dans l'app Documents
    documents_document_id = fields.Many2one(
        'documents.document',
        string='Document archive',
        readonly=True,
        ondelete='set null'
    )
    
    def _get_or_create_scans_folder(self):
        """Trouver ou créer le dossier 'Scans TVA' dans Finance"""
        Document = self.env['documents.document']
        
        # Chercher le dossier Finance (workspace)
        finance_folder = Document.search([
            ('name', '=', 'Finance'),
            ('type', '=', 'folder'),
        ], limit=1)
        
        if not finance_folder:
            # Chercher n'importe quel workspace racine
            finance_folder = Document.search([
                ('type', '=', 'folder'),
                ('folder_id', '=', False),
            ], limit=1)
        
        if not finance_folder:
            raise UserError(_("Aucun dossier Documents trouve. Veuillez configurer l'application Documents."))
        
        # Chercher le dossier 'Scans TVA' dans Finance
        scans_folder = Document.search([
            ('name', '=', 'Scans TVA'),
            ('type', '=', 'folder'),
            ('folder_id', '=', finance_folder.id),
        ], limit=1)
        
        if not scans_folder:
            # Créer le dossier 'Scans TVA'
            scans_folder = Document.create({
                'name': 'Scans TVA',
                'type': 'folder',
                'folder_id': finance_folder.id,
            })
            _logger.info("Dossier 'Scans TVA' cree dans Finance")
        
        return scans_folder

    def action_archive_to_documents(self):
        """Archiver le document dans l'application Documents"""
        self.ensure_one()
        
        if not self.document:
            raise UserError(_("Aucun document a archiver."))
        
        if self.documents_document_id:
            raise UserError(_("Ce document est deja archive."))
        
        try:
            scans_folder = self._get_or_create_scans_folder()
            
            # Créer le document dans Documents
            doc_vals = {
                'name': self.document_filename or f"Scan_{self.name}",
                'datas': self.document,
                'folder_id': scans_folder.id,
                'type': 'binary',
            }
            
            # Ajouter le partenaire si disponible
            if self.supplier_id:
                doc_vals['partner_id'] = self.supplier_id.id
            
            doc = self.env['documents.document'].create(doc_vals)
            self.documents_document_id = doc.id
            
            _logger.info("Document archive: %s -> Documents ID %s", self.name, doc.id)
            
        except Exception as e:
            _logger.error("Erreur archivage Documents: %s", str(e), exc_info=True)
            raise UserError(_("Erreur lors de l'archivage: %s") % str(e))

    def action_open_document(self):
        """Ouvrir le document dans l'application Documents"""
        self.ensure_one()
        
        if not self.documents_document_id:
            raise UserError(_("Aucun document archive."))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'res_id': self.documents_document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_scan_ocr(self):
        """Override pour archiver automatiquement après OCR"""
        result = super().action_scan_ocr()
        
        # Archiver automatiquement si le document n'est pas encore archivé
        if self.document and not self.documents_document_id:
            try:
                self.action_archive_to_documents()
            except Exception as e:
                _logger.warning("Archivage automatique echoue: %s", str(e))
        
        return result

    def action_validate(self):
        """Override pour mettre à jour le partenaire sur le document archivé"""
        result = super().action_validate()
        
        # Mettre à jour le partenaire sur le document archivé
        if self.documents_document_id and self.supplier_id:
            try:
                self.documents_document_id.partner_id = self.supplier_id.id
            except Exception as e:
                _logger.warning("Mise a jour partenaire Documents echoue: %s", str(e))
        
        return result
