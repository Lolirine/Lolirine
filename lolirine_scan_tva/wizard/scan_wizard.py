import base64
import logging
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class LolirineScanTvaWizard(models.TransientModel):
    _name = "lolirine.scan.tva.wizard"
    _description = "Assistant de scan TVA"
    capture_mode = fields.Selection([
        ('upload', '📤 Glisser / Uploader un fichier'),
        ('webcam', '📷 Caméra / Webcam'),
        ('scanner', '🖨️ Scanner Mac (instructions)'),
    ], string="Mode de capture", default='upload', required=True)
    document = fields.Binary(
        string="Document",
        help="Scanner ou uploader l'image/PDF de la souche TVA"
    )
    document_filename = fields.Char(string="Nom du fichier")
    document_type = fields.Selection([
        ('image', 'Image (JPG, PNG)'),
        ('pdf', 'PDF'),
    ], string="Type de document", default='image', required=True)
    notes = fields.Text(string="Notes")

    def action_create_scan(self):
        """Créer un nouveau scan à partir du document"""
        self.ensure_one()
        if not self.document:
            raise UserError(_("Veuillez uploader un document avant de continuer."))
        doc_type = 'image'
        if self.document_filename:
            if self.document_filename.lower().endswith('.pdf'):
                doc_type = 'pdf'
        scan = self.env['lolirine.scan.tva'].create({
            'document': self.document,
            'document_filename': self.document_filename,
            'document_type': doc_type,
            'notes': self.notes,
            'state': 'scanned',
        })
        try:
            scan.action_scan_ocr()
        except Exception as e:
            _logger.warning("OCR automatique echoue: %s", str(e))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.scan.tva',
            'res_id': scan.id,
            'view_mode': 'form',
            'target': 'main',
            'context': {'form_view_initial_mode': 'edit', 'clear_breadcrumbs': True},
        }


class LolirineScanTvaExtractWizard(models.TransientModel):
    _name = "lolirine.scan.tva.extract.wizard"
    _description = "Assistant d'extraction manuelle"

    scan_id = fields.Many2one(
        "lolirine.scan.tva",
        string="Scan",
        required=True
    )
    ocr_text = fields.Text(string="Texte OCR", readonly=True)
    supplier_vat = fields.Char(string="Numero TVA")
    supplier_name = fields.Char(string="Nom du fournisseur")
    invoice_number = fields.Char(string="Numero facture/ticket")
    invoice_date = fields.Date(string="Date", default=fields.Date.today)
    amount_untaxed = fields.Float(string="Montant HT")
    amount_tax = fields.Float(string="Montant TVA")
    amount_total = fields.Float(string="Montant TTC")

    # ── CORRECTION 1 : ajout de 'multi' dans la selection ──
    tax_rate = fields.Selection([
        ('0', '0%'),
        ('6', '6%'),
        ('12', '12%'),
        ('21', '21%'),
        ('multi', 'Taux multiples'),
    ], string="Taux TVA", default='21')

    @api.onchange('scan_id')
    def _onchange_scan_id(self):
        if self.scan_id:
            self.ocr_text = self.scan_id.ocr_text
            self.supplier_vat = self.scan_id.supplier_vat
            self.supplier_name = self.scan_id.supplier_name
            self.invoice_number = self.scan_id.invoice_number
            self.invoice_date = self.scan_id.invoice_date
            self.amount_untaxed = self.scan_id.amount_untaxed
            self.amount_tax = self.scan_id.amount_tax
            self.amount_total = self.scan_id.amount_total
            # ── CORRECTION 2 : protection si valeur invalide ──
            valid_rates = [v[0] for v in self._fields['tax_rate'].selection]
            self.tax_rate = self.scan_id.tax_rate if self.scan_id.tax_rate in valid_rates else False

    @api.onchange('amount_untaxed', 'tax_rate')
    def _onchange_amounts(self):
        # 'multi' n'est pas un taux numérique — on ne calcule pas
        if self.amount_untaxed and self.tax_rate and self.tax_rate != 'multi':
            rate = float(self.tax_rate) / 100
            self.amount_tax = self.amount_untaxed * rate
            self.amount_total = self.amount_untaxed + self.amount_tax

    def action_apply(self):
        """Appliquer les données extraites manuellement"""
        self.ensure_one()
        self.scan_id.write({
            'supplier_vat': self.supplier_vat,
            'supplier_name': self.supplier_name,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'amount_untaxed': self.amount_untaxed,
            'amount_tax': self.amount_tax,
            'amount_total': self.amount_total,
            'tax_rate': self.tax_rate,
            'state': 'extracted',
        })
        return {'type': 'ir.actions.act_window_close'}
