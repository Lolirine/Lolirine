import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LolirineScanTvaDocuments(models.Model):
    _inherit = "lolirine.scan.tva"

    # Lien vers le document dans l'app Documents
    documents_document_id = fields.Many2one(
        'documents.document',
        string="Document archive",
        readonly=True,
        ondelete='set null',
        help="Document archivé dans l'application Documents"
    )

    def _save_to_documents(self):
        """Sauvegarder le document dans l'application Documents pour archivage"""
        self.ensure_one()
        
        # Ne pas créer de doublon
        if self.documents_document_id:
            _logger.info("Document deja archive: %s", self.documents_document_id.name)
            return True
        
        if not self.document:
            _logger.warning("Pas de document a archiver")
            return False
        
        try:
            Folder = self.env['documents.folder'].sudo()
            Document = self.env['documents.document'].sudo()
            
            # Chercher le dossier "Scans TVA" existant
            folder = Folder.search([('name', '=', 'Scans TVA')], limit=1)
            _logger.info("Recherche dossier 'Scans TVA': %s", folder)
            
            if not folder:
                # Chercher le dossier parent "Finance"
                parent_folder = Folder.search([('name', '=', 'Finance')], limit=1)
                
                if not parent_folder:
                    # Chercher d'autres dossiers comptables
                    parent_folder = Folder.search([
                        '|', '|', '|',
                        ('name', 'ilike', 'Comptabilit'),
                        ('name', 'ilike', 'Accounting'),
                        ('name', 'ilike', 'Factures'),
                        ('name', 'ilike', 'Finance'),
                    ], limit=1)
                
                if not parent_folder:
                    # Prendre le premier dossier disponible
                    parent_folder = Folder.search([], limit=1)
                
                if not parent_folder:
                    _logger.error("Aucun dossier Documents trouve")
                    return False
                
                # Créer le dossier "Scans TVA"
                folder = Folder.create({
                    'name': 'Scans TVA',
                    'parent_folder_id': parent_folder.id,
                    'description': 'Documents scannés par le module Scan TVA',
                })
                _logger.info("Dossier 'Scans TVA' cree dans '%s'", parent_folder.name)
            
            # Créer l'attachment
            attachment = self.env['ir.attachment'].sudo().create({
                'name': self.document_filename or f"{self.name}.pdf",
                'datas': self.document,
                'res_model': self._name,
                'res_id': self.id,
            })
            _logger.info("Attachment cree: ID=%s", attachment.id)
            
            # Construire le nom du document
            doc_name = self.name
            if self.supplier_name:
                doc_name = f"{self.name} - {self.supplier_name}"
            if self.invoice_date:
                doc_name = f"{doc_name} ({self.invoice_date})"
            
            # Créer le document
            doc_vals = {
                'name': doc_name,
                'folder_id': folder.id,
                'attachment_id': attachment.id,
            }
            if self.partner_id:
                doc_vals['partner_id'] = self.partner_id.id
            
            document = Document.create(doc_vals)
            self.documents_document_id = document.id
            
            _logger.info("Document archive: %s (ID: %s)", document.name, document.id)
            return True
            
        except Exception as e:
            _logger.error("Erreur sauvegarde Documents: %s", str(e), exc_info=True)
            return False

    def action_scan_ocr(self):
        """Override pour sauvegarder dans Documents après OCR"""
        result = super().action_scan_ocr()
        # Sauvegarder dans Documents après extraction réussie
        if self.state in ('extracted', 'scanned'):
            self._save_to_documents()
        return result

    def action_validate(self):
        """Override pour mettre à jour le document après validation"""
        result = super().action_validate()
        
        # Mettre à jour le partenaire sur le document archivé
        if self.documents_document_id and self.partner_id:
            try:
                self.documents_document_id.write({
                    'partner_id': self.partner_id.id,
                })
                _logger.info("Document archive mis a jour avec partenaire %s", self.partner_id.name)
            except Exception as e:
                _logger.warning("Impossible de mettre a jour le document: %s", str(e))
        
        return result

    def action_view_document(self):
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

    def action_archive_document(self):
        """Archiver manuellement le document"""
        self.ensure_one()
        
        result = self._save_to_documents()
        if result and self.documents_document_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Document archive"),
                    'message': _("Le document a ete sauvegarde dans Documents (dossier Scans TVA)."),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Erreur"),
                    'message': _("Impossible d'archiver le document. Consultez les logs."),
                    'type': 'warning',
                    'sticky': True,
                }
            }
