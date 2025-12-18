# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ScanTvaWizard(models.TransientModel):
    _name = 'lolirine.scan.tva.wizard'
    _description = 'Assistant Scan TVA'

    document = fields.Binary(string='Document', required=True)
    document_filename = fields.Char(string='Nom du fichier')

    def action_create_scan(self):
        """Créer un nouveau scan avec le document"""
        self.ensure_one()
        
        scan = self.env['lolirine.scan.tva'].create({
            'document': self.document,
            'document_filename': self.document_filename,
            'state': 'scanned',
        })
        
        # Tenter l'extraction OCR automatique
        try:
            scan.action_scan_ocr()
        except Exception as e:
            _logger.warning("OCR automatique echoue: %s", str(e))
        
        # Ouvrir le scan créé
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.scan.tva',
            'res_id': scan.id,
            'view_mode': 'form',
            'target': 'main',
            'context': {'form_view_initial_mode': 'edit'},
        }


class ManualExtractionWizard(models.TransientModel):
    _name = 'lolirine.scan.tva.manual.wizard'
    _description = 'Extraction Manuelle'

    scan_id = fields.Many2one('lolirine.scan.tva', string='Scan', required=True)
    
    supplier_vat = fields.Char(string='Numero TVA')
    supplier_name = fields.Char(string='Nom du fournisseur')
    supplier_address = fields.Char(string='Adresse')
    supplier_zip = fields.Char(string='Code postal')
    supplier_city = fields.Char(string='Ville')
    
    invoice_number = fields.Char(string='Numero facture/ticket')
    invoice_date = fields.Date(string='Date de facture', default=fields.Date.today)
    
    vat_rate = fields.Selection([
        ('0', '0%'),
        ('6', '6%'),
        ('12', '12%'),
        ('21', '21%'),
    ], string='Taux TVA', default='21')
    amount_untaxed = fields.Float(string='Montant HT')
    amount_tax = fields.Float(string='Montant TVA')
    amount_total = fields.Float(string='Montant TTC')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('active_id'):
            scan = self.env['lolirine.scan.tva'].browse(self._context['active_id'])
            res.update({
                'scan_id': scan.id,
                'supplier_vat': scan.supplier_vat,
                'supplier_name': scan.supplier_name,
                'supplier_address': scan.supplier_address,
                'supplier_zip': scan.supplier_zip,
                'supplier_city': scan.supplier_city,
                'invoice_number': scan.invoice_number,
                'invoice_date': scan.invoice_date,
                'vat_rate': scan.vat_rate,
                'amount_untaxed': scan.amount_untaxed,
                'amount_tax': scan.amount_tax,
                'amount_total': scan.amount_total,
            })
        return res

    def action_apply(self):
        """Appliquer les données extraites manuellement"""
        self.ensure_one()
        
        self.scan_id.write({
            'supplier_vat': self.supplier_vat,
            'supplier_name': self.supplier_name,
            'supplier_address': self.supplier_address,
            'supplier_zip': self.supplier_zip,
            'supplier_city': self.supplier_city,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'vat_rate': self.vat_rate,
            'amount_untaxed': self.amount_untaxed,
            'amount_tax': self.amount_tax,
            'amount_total': self.amount_total,
            'state': 'extracted',
        })
        
        return {'type': 'ir.actions.act_window_close'}
