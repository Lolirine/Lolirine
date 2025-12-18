# -*- coding: utf-8 -*-
import re
import base64
import logging
from io import BytesIO
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Imports OCR optionnels
try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    _logger.warning("Pillow non disponible - OCR limite")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    _logger.warning("pytesseract non disponible - OCR desactive")

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    _logger.warning("pdf2image non disponible - PDF OCR desactive")


class LolirineScanTva(models.Model):
    _name = 'lolirine.scan.tva'
    _description = 'Scan TVA Fournisseur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='/'
    )
    
    # Document
    document = fields.Binary(string='Document', attachment=True)
    document_filename = fields.Char(string='Nom du fichier')
    document_type = fields.Selection([
        ('image', 'Image'),
        ('pdf', 'PDF'),
    ], string='Type de document', compute='_compute_document_type', store=True)
    
    # Texte OCR
    ocr_text = fields.Text(string='Texte OCR', readonly=True)
    
    # Informations fournisseur
    supplier_vat = fields.Char(string='Numero TVA', tracking=True)
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', tracking=True)
    supplier_name = fields.Char(string='Nom du fournisseur')
    supplier_address = fields.Char(string='Adresse')
    supplier_zip = fields.Char(string='Code postal')
    supplier_city = fields.Char(string='Ville')
    supplier_country_id = fields.Many2one('res.country', string='Pays', default=lambda self: self.env.ref('base.be', raise_if_not_found=False))
    
    # Informations facture
    invoice_number = fields.Char(string='Numero facture/ticket')
    invoice_date = fields.Date(string='Date de facture', default=fields.Date.today)
    
    # Montants
    vat_rate = fields.Selection([
        ('0', '0%'),
        ('6', '6%'),
        ('12', '12%'),
        ('21', '21%'),
    ], string='Taux TVA', default='21')
    amount_untaxed = fields.Float(string='Montant HT', digits=(16, 2))
    amount_tax = fields.Float(string='Montant TVA', digits=(16, 2))
    amount_total = fields.Float(string='Montant TTC', digits=(16, 2))
    
    # Comptabilite
    expense_account_id = fields.Many2one(
        'account.account',
        string='Compte de charge',
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost', 'expense_depreciation'])]"
    )
    invoice_id = fields.Many2one('account.move', string='Facture creee', readonly=True)
    responsible_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user)
    
    # Workflow
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scanned', 'Scanne'),
        ('extracted', 'Extrait'),
        ('validated', 'Valide'),
        ('invoiced', 'Facture creee'),
    ], string='Etat', default='draft', tracking=True)
    
    company_id = fields.Many2one('res.company', string='Societe', default=lambda self: self.env.company)

    @api.depends('document_filename')
    def _compute_document_type(self):
        for record in self:
            if record.document_filename:
                ext = record.document_filename.lower().split('.')[-1]
                if ext == 'pdf':
                    record.document_type = 'pdf'
                else:
                    record.document_type = 'image'
            else:
                record.document_type = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('lolirine.scan.tva') or '/'
        return super().create(vals_list)

    @api.onchange('amount_untaxed', 'vat_rate')
    def _onchange_amount_untaxed(self):
        if self.amount_untaxed and self.vat_rate:
            rate = float(self.vat_rate) / 100
            self.amount_tax = round(self.amount_untaxed * rate, 2)
            self.amount_total = round(self.amount_untaxed + self.amount_tax, 2)

    @api.onchange('amount_total', 'vat_rate')
    def _onchange_amount_total(self):
        if self.amount_total and self.vat_rate and not self.amount_untaxed:
            rate = float(self.vat_rate) / 100
            self.amount_untaxed = round(self.amount_total / (1 + rate), 2)
            self.amount_tax = round(self.amount_total - self.amount_untaxed, 2)

    def _preprocess_image(self, img):
        """Prétraitement de l'image pour améliorer l'OCR"""
        if not PIL_AVAILABLE:
            return img
        
        # Convertir en niveaux de gris
        img_gray = img.convert('L')
        
        # Augmenter le contraste
        enhancer = ImageEnhance.Contrast(img_gray)
        img_contrast = enhancer.enhance(2.0)
        
        # Binarisation (seuillage)
        threshold = 150
        img_binary = img_contrast.point(lambda x: 255 if x > threshold else 0, '1')
        
        return img_binary

    def action_scan_ocr(self):
        """Lancer l'extraction OCR du document"""
        self.ensure_one()
        
        if not self.document:
            raise UserError(_("Veuillez d'abord uploader un document."))
        
        if not PIL_AVAILABLE or not TESSERACT_AVAILABLE:
            raise UserError(_("OCR non disponible. Installez Pillow et pytesseract."))
        
        try:
            document_data = base64.b64decode(self.document)
            ocr_text = ""
            
            if self.document_type == 'pdf':
                if not PDF2IMAGE_AVAILABLE:
                    raise UserError(_("pdf2image non disponible pour les PDF."))
                
                # Convertir PDF en images avec haute résolution
                images = convert_from_bytes(document_data, dpi=300)
                
                for i, img in enumerate(images):
                    # Prétraitement de l'image
                    img_processed = self._preprocess_image(img)
                    
                    # OCR avec configuration optimisée
                    config = r'--oem 3 --psm 6 -l fra+eng'
                    page_text = pytesseract.image_to_string(img_processed, config=config)
                    ocr_text += f"=== Page {i+1} ===\n{page_text}\n"
            else:
                # Image directe
                img = Image.open(BytesIO(document_data))
                img_processed = self._preprocess_image(img)
                config = r'--oem 3 --psm 6 -l fra+eng'
                ocr_text = pytesseract.image_to_string(img_processed, config=config)
            
            self.ocr_text = ocr_text
            
            if not ocr_text or len(ocr_text.strip()) < 20:
                self.state = 'scanned'
                return
            
            # Extraction automatique des données
            self._extract_data_from_ocr(ocr_text)
            self.state = 'extracted'
            
        except UserError:
            raise
        except Exception as e:
            _logger.error("Erreur OCR: %s", str(e), exc_info=True)
            raise UserError(_("Erreur lors de l'extraction OCR: %s") % str(e))

    def _extract_data_from_ocr(self, text):
        """Extraire les données du texte OCR"""
        if not text:
            return
        
        text_upper = text.upper()
        text_lines = text.split('\n')
        
        _logger.info("=== Extraction des donnees ===")
        _logger.info("Texte OCR (%d caracteres)", len(text))
        
        # ========================================
        # DÉTECTION DU TYPE DE DOCUMENT
        # ========================================
        doc_type = 'generic'
        supplier_detected = None
        
        if 'INTERMARCHE' in text_upper or 'INTERMARCH' in text_upper:
            doc_type = 'intermarche'
            supplier_detected = 'Intermarché'
        elif 'COLRUYT' in text_upper:
            doc_type = 'colruyt'
            supplier_detected = 'Colruyt'
        elif 'DELHAIZE' in text_upper or 'AD DELHAIZE' in text_upper:
            doc_type = 'delhaize'
            supplier_detected = 'Delhaize'
        elif 'CARREFOUR' in text_upper:
            doc_type = 'carrefour'
            supplier_detected = 'Carrefour'
        elif 'ALDI' in text_upper:
            doc_type = 'aldi'
            supplier_detected = 'Aldi'
        elif 'LIDL' in text_upper:
            doc_type = 'lidl'
            supplier_detected = 'Lidl'
        elif 'TOTAL' in text_upper and ('DIESEL' in text_upper or 'ESSENCE' in text_upper or 'CARBURANT' in text_upper):
            doc_type = 'station'
        elif 'PROXIMUS' in text_upper:
            doc_type = 'proximus'
            supplier_detected = 'Proximus'
        
        _logger.info("Type de document detecte: %s", doc_type)
        
        # ========================================
        # EXTRACTION DU NUMÉRO DE TVA BELGE
        # ========================================
        # Patterns pour numéro TVA belge (différents formats)
        vat_patterns = [
            # Format standard BE0123456789
            r'TVA\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'BTW\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            # Format avec points et espaces : BE 100.90.990.17
            r'(BE\s*\d{2,3}[\.,\s]+\d{2,3}[\.,\s]+\d{3}[\.,\s]+\d{2})',
            # Format compact
            r'(BE\s*0\d{9})',
            r'(BE0\d{9})',
            # Format avec séparateurs variés
            r'TVA\s*[:\s]+(BE[\s\d\.,]+)',
        ]
        
        vat_found = None
        for pattern in vat_patterns:
            match = re.search(pattern, text_upper)
            if match:
                vat_raw = match.group(1)
                # Nettoyer : garder uniquement BE + chiffres
                vat_clean = re.sub(r'[^BE0-9]', '', vat_raw.upper())
                # Corriger les erreurs OCR courantes
                vat_clean = vat_clean.replace('O', '0').replace('I', '1').replace('L', '1')
                
                # Valider le format (BE + 9 ou 10 chiffres)
                if re.match(r'^BE0?\d{9,10}$', vat_clean):
                    # Normaliser au format BE0XXXXXXXXX
                    digits = re.sub(r'[^0-9]', '', vat_clean)
                    if len(digits) == 9:
                        vat_found = 'BE0' + digits
                    elif len(digits) == 10:
                        vat_found = 'BE' + digits
                    break
        
        if vat_found:
            self.supplier_vat = vat_found
            _logger.info("TVA extraite: %s", vat_found)
        
        # ========================================
        # EXTRACTION NOM DU FOURNISSEUR
        # ========================================
        # Pour les supermarchés, on utilise le nom détecté
        if supplier_detected:
            # Chercher le nom légal (S.A., SPRL, etc.)
            company_patterns = [
                r'(SPEECHLESS\s+S\.?A\.?)',
                r'([A-Z\s]+(?:S\.?A\.?|SPRL|SRL|BVBA|NV|SA))',
            ]
            for pattern in company_patterns:
                match = re.search(pattern, text_upper)
                if match:
                    self.supplier_name = match.group(1).strip()
                    break
            if not self.supplier_name:
                self.supplier_name = supplier_detected
        
        # ========================================
        # EXTRACTION ADRESSE (du fournisseur, pas du client)
        # ========================================
        # Pour les tickets, l'adresse du fournisseur est généralement en haut
        # L'adresse du client (ex: SRL LOLIRINE) vient après
        
        address_found = False
        for i, line in enumerate(text_lines[:15]):  # Chercher dans les 15 premières lignes
            line_clean = line.strip()
            
            # Ignorer si c'est l'adresse du client (détection par nom connu)
            if 'LOLIRINE' in line_clean.upper() or 'LOLIRIN' in line_clean.upper():
                # On a atteint la section client, arrêter
                break
            
            # Chercher une adresse (rue + numéro)
            if not address_found:
                addr_match = re.search(r'((?:RUE|ROUTE|AVENUE|CHAUSSEE|BOULEVARD|PLACE)\s+[A-Z\s]+\d+)', line_clean.upper())
                if addr_match:
                    self.supplier_address = addr_match.group(1).title()
                    address_found = True
                    continue
            
            # Chercher code postal (4 chiffres belges) + ville
            zip_match = re.search(r'^(\d{4})\s+([A-Z\s]+)$', line_clean.upper())
            if zip_match and address_found:
                self.supplier_zip = zip_match.group(1)
                self.supplier_city = zip_match.group(2).strip().title()
                break
        
        # ========================================
        # EXTRACTION DATE
        # ========================================
        date_patterns = [
            r'(?:LE\s*)?(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',
            r'DATE\s*:?\s*(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                day, month, year = match.groups()
                if len(year) == 2:
                    year = '20' + year
                try:
                    self.invoice_date = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y").date()
                    _logger.info("Date extraite: %s", self.invoice_date)
                    break
                except ValueError:
                    continue
        
        # ========================================
        # EXTRACTION NUMÉRO DE FACTURE/TICKET
        # ========================================
        invoice_patterns = [
            r'NUM[\.:\s]*(\d{8,15})',
            r'N[°o]?\s*:?\s*(\d{8,15})',
            r'FACTURE\s*(?:N[°o]?)?\s*:?\s*(\d+)',
            r'TICKET\s*(?:N[°o]?)?\s*:?\s*(\d+)',
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text_upper)
            if match:
                self.invoice_number = match.group(1)
                _logger.info("Numero facture: %s", self.invoice_number)
                break
        
        # ========================================
        # EXTRACTION DES MONTANTS
        # ========================================
        # Patterns pour montants (format européen avec virgule)
        
        # Total TTC
        ttc_patterns = [
            r'TOTAL\s*TTC\s*[:\s]*(\d+)[,\.](\d{2})',
            r'TTC\s*[:\s]*(\d+)[,\.](\d{2})',
            r'A\s*PAYER\s*[:\s]*(\d+)[,\.](\d{2})',
            r'BANCONTACT\s*[:\s]*(\d+)[,\.](\d{2})',
        ]
        for pattern in ttc_patterns:
            match = re.search(pattern, text_upper)
            if match:
                self.amount_total = float(f"{match.group(1)}.{match.group(2)}")
                _logger.info("Montant TTC: %s", self.amount_total)
                break
        
        # Total HT
        ht_patterns = [
            r'TOTAL\s*HT\s*[:\s]*(\d+)[,\.](\d{2})',
            r'H\.?T\.?\s*[:\s]*(\d+)[,\.](\d{2})',
            r'HTVA\s*[:\s]*(\d+)[,\.](\d{2})',
        ]
        for pattern in ht_patterns:
            match = re.search(pattern, text_upper)
            if match:
                self.amount_untaxed = float(f"{match.group(1)}.{match.group(2)}")
                _logger.info("Montant HT: %s", self.amount_untaxed)
                break
        
        # TVA
        tva_patterns = [
            r'TVA\s*[:\s]*(\d+)[,\.](\d{2})',
            r'T\.?V\.?A\.?\s*[:\s]*(\d+)[,\.](\d{2})',
        ]
        for pattern in tva_patterns:
            match = re.search(pattern, text_upper)
            if match:
                # Éviter de capturer le numéro de TVA comme montant
                amount = float(f"{match.group(1)}.{match.group(2)}")
                if amount < 1000:  # Un montant TVA raisonnable
                    self.amount_tax = amount
                    _logger.info("Montant TVA: %s", self.amount_tax)
                    break
        
        # ========================================
        # EXTRACTION DU TAUX TVA
        # ========================================
        rate_patterns = [
            r'(\d{1,2})[,\.]00\s*%',
            r'TAUX\s*[:\s]*(\d{1,2})',
            r'(\d{1,2})\s*%',
        ]
        for pattern in rate_patterns:
            match = re.search(pattern, text)
            if match:
                rate = int(match.group(1))
                if rate in [0, 6, 12, 21]:
                    self.vat_rate = str(rate)
                    _logger.info("Taux TVA: %s%%", rate)
                    break
        
        # ========================================
        # CALCULS AUTOMATIQUES SI MANQUANTS
        # ========================================
        if self.amount_total and self.vat_rate and not self.amount_untaxed:
            rate = float(self.vat_rate) / 100
            self.amount_untaxed = round(self.amount_total / (1 + rate), 2)
            self.amount_tax = round(self.amount_total - self.amount_untaxed, 2)
        elif self.amount_untaxed and self.vat_rate and not self.amount_total:
            rate = float(self.vat_rate) / 100
            self.amount_tax = round(self.amount_untaxed * rate, 2)
            self.amount_total = round(self.amount_untaxed + self.amount_tax, 2)

    def action_validate(self):
        """Valider le scan et créer/lier le fournisseur"""
        self.ensure_one()
        
        if not self.supplier_vat and not self.supplier_name:
            raise UserError(_("Veuillez renseigner au moins le numero TVA ou le nom du fournisseur."))
        
        # Rechercher ou créer le fournisseur
        Partner = self.env['res.partner']
        supplier = False
        
        if self.supplier_vat:
            # Normaliser le numéro TVA
            vat = self.supplier_vat.upper().replace(' ', '').replace('.', '')
            supplier = Partner.search([('vat', '=', vat)], limit=1)
            
            if not supplier:
                # Essayer avec format différent
                supplier = Partner.search([('vat', 'ilike', vat)], limit=1)
        
        if not supplier and self.supplier_name:
            supplier = Partner.search([('name', 'ilike', self.supplier_name)], limit=1)
        
        if not supplier:
            # Créer le fournisseur
            supplier_vals = {
                'name': self.supplier_name or f"Fournisseur {self.supplier_vat}",
                'supplier_rank': 1,
                'is_company': True,
                'company_type': 'company',
            }
            if self.supplier_vat:
                supplier_vals['vat'] = self.supplier_vat
            if self.supplier_address:
                supplier_vals['street'] = self.supplier_address
            if self.supplier_zip:
                supplier_vals['zip'] = self.supplier_zip
            if self.supplier_city:
                supplier_vals['city'] = self.supplier_city
            if self.supplier_country_id:
                supplier_vals['country_id'] = self.supplier_country_id.id
            
            supplier = Partner.create(supplier_vals)
        
        self.supplier_id = supplier.id
        self.state = 'validated'

    def action_create_invoice(self):
        """Créer la facture fournisseur"""
        self.ensure_one()
        
        if not self.supplier_id:
            raise UserError(_("Veuillez d'abord valider le fournisseur."))
        
        if not self.amount_total:
            raise UserError(_("Le montant total est requis."))
        
        # Trouver la taxe correspondante
        tax = False
        if self.vat_rate and self.vat_rate != '0':
            rate = float(self.vat_rate)
            tax = self.env['account.tax'].search([
                ('type_tax_use', '=', 'purchase'),
                ('amount', '=', rate),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        
        # Préparer la ligne de facture
        invoice_line_vals = {
            'name': f"Achat {self.supplier_id.name} - {self.invoice_number or self.name}",
            'quantity': 1,
            'price_unit': self.amount_untaxed or self.amount_total,
        }
        if self.expense_account_id:
            invoice_line_vals['account_id'] = self.expense_account_id.id
        if tax:
            invoice_line_vals['tax_ids'] = [(6, 0, [tax.id])]
        
        # Créer la facture
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.supplier_id.id,
            'invoice_date': self.invoice_date,
            'ref': self.invoice_number or self.name,
            'invoice_line_ids': [(0, 0, invoice_line_vals)],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Attacher le document scanné
        if self.document:
            self.env['ir.attachment'].create({
                'name': self.document_filename or f"Scan_{self.name}.pdf",
                'type': 'binary',
                'datas': self.document,
                'res_model': 'account.move',
                'res_id': invoice.id,
            })
        
        self.invoice_id = invoice.id
        self.state = 'invoiced'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.ensure_one()
        self.state = 'draft'

    def action_archive(self):
        """Archiver le scan"""
        self.write({'active': False})
