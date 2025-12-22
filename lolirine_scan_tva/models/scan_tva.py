import base64
import re
import logging
from datetime import datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Essayer d'importer les bibliothèques OCR
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    _logger.warning("pytesseract ou PIL non disponible. L'OCR ne fonctionnera pas.")

try:
    from pdf2image import convert_from_bytes
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    _logger.warning("pdf2image non disponible. La conversion PDF ne fonctionnera pas.")


class LolirineScanTva(models.Model):
    _name = "lolirine.scan.tva"
    _description = "Scan de souche TVA"
    _order = "create_date desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scanned', 'Scanne'),
        ('extracted', 'Extrait'),
        ('validated', 'Valide'),
        ('invoiced', 'Facture creee'),
        ('cancelled', 'Annule'),
    ], string="Etat", default='draft')
    
    # Document source (attachment=False pour éviter intégration automatique module Documents)
    document_type = fields.Selection([
        ('image', 'Image'),
        ('pdf', 'PDF'),
    ], string="Type de document", default='image')
    
    document = fields.Binary(
        string="Document",
        attachment=False,
        help="Image ou PDF de la souche TVA"
    )
    document_filename = fields.Char(string="Nom du fichier")
    
    document_preview = fields.Binary(
        string="Apercu",
        compute="_compute_document_preview",
        store=False
    )
    
    # Texte extrait par OCR
    ocr_text = fields.Text(
        string="Texte OCR",
        readonly=True,
        help="Texte brut extrait par OCR"
    )
    
    # Informations extraites - Fournisseur
    supplier_vat = fields.Char(
        string="Numero TVA",
        
        help="Numero de TVA du fournisseur (format BE0123456789)"
    )
    supplier_name = fields.Char(
        string="Nom du fournisseur",
        
    )
    supplier_street = fields.Char(string="Adresse")
    supplier_zip = fields.Char(string="Code postal")
    supplier_city = fields.Char(string="Ville")
    supplier_country_id = fields.Many2one(
        "res.country",
        string="Pays",
        default=lambda self: self.env.ref('base.be', raise_if_not_found=False)
    )
    supplier_phone = fields.Char(string="Telephone")
    supplier_email = fields.Char(string="Email")
    
    # Fournisseur lié
    partner_id = fields.Many2one(
        "res.partner",
        string="Fournisseur",
        domain="[('supplier_rank', '>', 0)]",
        
    )
    partner_exists = fields.Boolean(
        string="Fournisseur existant",
        compute="_compute_partner_exists"
    )
    
    # Informations facture
    invoice_number = fields.Char(
        string="Numero facture/ticket",
        
    )
    invoice_date = fields.Date(
        string="Date de facture",
        default=fields.Date.today,
        
    )
    
    # Montants
    amount_untaxed = fields.Monetary(
        string="Montant HT",
        currency_field='currency_id',
        
    )
    amount_tax = fields.Monetary(
        string="Montant TVA",
        currency_field='currency_id',
        
    )
    amount_total = fields.Monetary(
        string="Montant TTC",
        currency_field='currency_id',
        
    )
    tax_rate = fields.Selection([
        ('0', '0%'),
        ('6', '6%'),
        ('12', '12%'),
        ('21', '21%'),
    ], string="Taux TVA", default='21')
    
    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        default=lambda self: self.env.company.currency_id
    )
    
    # Compte comptable
    account_id = fields.Many2one(
        "account.account",
        string="Compte de charge",
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost'))]",
        help="Compte comptable pour imputer la charge"
    )
    
    # Facture générée
    invoice_id = fields.Many2one(
        "account.move",
        string="Facture fournisseur",
        readonly=True
    )
    
    # Notes
    notes = fields.Text(string="Notes")
    
    # Champs techniques
    company_id = fields.Many2one(
        "res.company",
        string="Societe",
        default=lambda self: self.env.company
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('lolirine.scan.tva') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('document', 'document_type')
    def _compute_document_preview(self):
        for record in self:
            record.document_preview = record.document

    @api.depends('supplier_vat')
    def _compute_partner_exists(self):
        for record in self:
            if record.supplier_vat:
                partner = self.env['res.partner'].search([
                    ('vat', '=ilike', record.supplier_vat)
                ], limit=1)
                record.partner_exists = bool(partner)
                if partner and not record.partner_id:
                    record.partner_id = partner
            else:
                record.partner_exists = False

    @api.onchange('supplier_vat')
    def _onchange_supplier_vat(self):
        """Rechercher le fournisseur par numéro TVA"""
        if self.supplier_vat:
            # Nettoyer le numéro TVA
            vat_clean = self.supplier_vat.upper().replace(' ', '').replace('.', '')
            self.supplier_vat = vat_clean
            
            # Rechercher le fournisseur
            partner = self.env['res.partner'].search([
                ('vat', '=ilike', vat_clean)
            ], limit=1)
            
            if partner:
                self.partner_id = partner
                self.supplier_name = partner.name
                self.supplier_street = partner.street
                self.supplier_zip = partner.zip
                self.supplier_city = partner.city
                self.supplier_country_id = partner.country_id
                self.supplier_phone = partner.phone
                self.supplier_email = partner.email

    @api.onchange('amount_untaxed', 'tax_rate')
    def _onchange_amounts(self):
        """Calculer les montants automatiquement"""
        if self.amount_untaxed and self.tax_rate:
            rate = float(self.tax_rate) / 100
            self.amount_tax = self.amount_untaxed * rate
            self.amount_total = self.amount_untaxed + self.amount_tax

    @api.onchange('amount_total', 'tax_rate')
    def _onchange_amount_total(self):
        """Calculer HT depuis TTC"""
        if self.amount_total and self.tax_rate and not self.amount_untaxed:
            rate = float(self.tax_rate) / 100
            self.amount_untaxed = self.amount_total / (1 + rate)
            self.amount_tax = self.amount_total - self.amount_untaxed

    def action_scan_ocr(self):
        """Lancer l'extraction OCR du document"""
        self.ensure_one()
        
        if not self.document:
            raise UserError(_("Veuillez d'abord uploader un document."))
        
        try:
            # Décoder le document
            document_data = base64.b64decode(self.document)
            
            _logger.info("Document reçu: %s, taille: %d bytes", 
                        self.document_filename or 'inconnu', len(document_data))
            
            # Détecter si c'est un PDF
            is_pdf = False
            if self.document_filename and self.document_filename.lower().endswith('.pdf'):
                is_pdf = True
            elif document_data[:4] == b'%PDF':
                is_pdf = True
            
            ocr_text = ''
            images = []
            
            if is_pdf:
                _logger.info("Document detecte comme PDF")
                self.document_type = 'pdf'
                
                # Essayer d'abord d'extraire le texte natif du PDF avec PyMuPDF
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(stream=document_data, filetype="pdf")
                    pdf_text_parts = []
                    for page_num, page in enumerate(doc):
                        page_text = page.get_text()
                        if page_text.strip():
                            pdf_text_parts.append(page_text)
                            _logger.info("PDF page %d: %d caracteres (texte natif)", page_num+1, len(page_text))
                    doc.close()
                    
                    if pdf_text_parts:
                        ocr_text = '\n'.join(pdf_text_parts)
                        _logger.info("Texte PDF natif extrait: %d caracteres total", len(ocr_text))
                except ImportError:
                    _logger.info("PyMuPDF non disponible, utilisation de pdf2image + OCR")
                except Exception as e:
                    _logger.warning("Extraction texte PDF natif echouee: %s", str(e))
                
                # Si pas assez de texte natif, convertir en images pour OCR
                if not ocr_text.strip() or len(ocr_text.strip()) < 50:
                    _logger.info("Pas assez de texte natif, conversion en image pour OCR")
                    
                    if not PDF_AVAILABLE:
                        raise UserError(_("pdf2image n'est pas installe pour convertir les PDF."))
                    
                    if not OCR_AVAILABLE:
                        raise UserError(_("pytesseract n'est pas disponible pour l'OCR."))
                    
                    try:
                        pdf_images = convert_from_bytes(document_data, dpi=300)
                        images = pdf_images
                        _logger.info("PDF converti en %d image(s)", len(images))
                    except Exception as e:
                        _logger.error("Erreur conversion PDF: %s", str(e))
                        raise UserError(_("Erreur lors de la conversion du PDF: %s") % str(e))
            else:
                _logger.info("Document detecte comme image")
                self.document_type = 'image'
                
                if not OCR_AVAILABLE:
                    raise UserError(_("pytesseract n'est pas disponible pour l'OCR."))
                
                try:
                    image = Image.open(io.BytesIO(document_data))
                    images = [image]
                except Exception as e:
                    _logger.error("Erreur ouverture image: %s", str(e))
                    raise UserError(_("Erreur lors de l'ouverture de l'image: %s") % str(e))
            
            # Si on a des images à traiter par OCR
            if images and not ocr_text.strip():
                all_text = []
                for i, image in enumerate(images):
                    _logger.info("OCR page %d/%d, taille: %s", i+1, len(images), image.size)
                    
                    # Configuration tesseract pour meilleure reconnaissance
                    custom_config = r'--oem 3 --psm 6 -l fra+nld'
                    
                    try:
                        page_text = pytesseract.image_to_string(image, config=custom_config)
                        all_text.append(page_text)
                        _logger.info("Page %d: %d caracteres extraits", i+1, len(page_text))
                    except Exception as e:
                        _logger.warning("OCR page %d echoue avec config: %s", i+1, str(e))
                        try:
                            page_text = pytesseract.image_to_string(image)
                            all_text.append(page_text)
                        except Exception as e2:
                            _logger.error("OCR page %d echoue completement: %s", i+1, str(e2))
                
                ocr_text = '\n\n'.join(all_text)
            
            self.ocr_text = ocr_text
            
            _logger.info("=== Texte total extrait: %d caracteres ===", len(ocr_text))
            _logger.info("Contenu:\n%s", ocr_text[:2000] if ocr_text else "(vide)")
            
            if not ocr_text.strip():
                _logger.warning("Aucun texte n'a pu etre extrait du document.")
                self.state = 'scanned'
                return
            
            # Extraction automatique des données
            self._extract_data_from_ocr(ocr_text)
            
            self.state = 'extracted'
            _logger.info("Document scanne et donnees extraites avec succes.")
            
        except UserError:
            raise
        except Exception as e:
            _logger.error("Erreur OCR: %s", str(e), exc_info=True)
            raise UserError(_("Erreur lors de l'extraction OCR: %s") % str(e))

    def _extract_data_from_ocr(self, text):
        """Extraire les données du texte OCR - Support multi-fournisseurs"""
        if not text:
            return
        
        text_upper = text.upper()
        text_lines = text.split('\n')
        
        _logger.info("=== Extraction des donnees ===")
        _logger.info("Texte brut (%d car.):\n%s", len(text), text[:2000])
        
        # ========================================
        # DÉTECTION DU TYPE DE DOCUMENT
        # ========================================
        doc_type = 'generic'
        if 'COLRUYT' in text_upper:
            doc_type = 'colruyt'
        elif 'DELHAIZE' in text_upper or 'AD DELHAIZE' in text_upper:
            doc_type = 'delhaize'
        elif any(x in text_upper for x in ['TOTAL ENERGIES', 'TOTAL BOUGE', 'TOTALENERGIES']) or \
             ('TOTAL' in text_upper and any(x in text_upper for x in ['DIESEL', 'ESSENCE', 'CARBURANT', 'LITRE'])):
            doc_type = 'station'
        elif 'CARREFOUR' in text_upper:
            doc_type = 'carrefour'
        elif 'ALDI' in text_upper:
            doc_type = 'aldi'
        elif 'LIDL' in text_upper:
            doc_type = 'lidl'
        elif 'PROXIMUS' in text_upper:
            doc_type = 'telecom'
        elif 'ORANGE' in text_upper or 'BASE' in text_upper:
            doc_type = 'telecom'
        elif any(x in text_upper for x in ['HTVA', 'HORS TVA', 'MONTANT HT']):
            doc_type = 'facture_pro'
        
        _logger.info("Type de document detecte: %s", doc_type)
        
        # ========================================
        # EXTRACTION DU NUMÉRO DE TVA BELGE
        # ========================================
        vat_patterns = [
            r'TVA\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'BTW\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'N[°o]?\s*(?:TVA|ENTREPRISE)\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'(BE\s*0\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'(BE0\d{9})',
        ]
        for pattern in vat_patterns:
            match = re.search(pattern, text_upper)
            if match:
                vat = match.group(1) if match.lastindex else match.group(0)
                vat = re.sub(r'[\s\.]', '', vat)
                if not vat.startswith('BE'):
                    vat = 'BE' + vat
                if re.match(r'^BE0\d{9}$', vat):
                    self.supplier_vat = vat
                    _logger.info("TVA trouvee: %s", vat)
                    break
        
        # ========================================
        # EXTRACTION DU NOM DU FOURNISSEUR
        # ========================================
        known_suppliers = {
            'COLRUYT': 'Colruyt',
            'DELHAIZE': 'Delhaize',
            'AD DELHAIZE': 'AD Delhaize',
            'CARREFOUR': 'Carrefour',
            'ALDI': 'Aldi',
            'LIDL': 'Lidl',
            'PROXIMUS': 'Proximus',
            'ORANGE': 'Orange',
            'TOTAL ENERGIES': 'TotalEnergies',
            'TOTALENERGIES': 'TotalEnergies',
            'SHELL': 'Shell',
            'TEXACO': 'Texaco',
            'Q8': 'Q8',
            'LUKOIL': 'Lukoil',
            'ESSO': 'Esso',
        }
        
        for key, name in known_suppliers.items():
            if key in text_upper:
                self.supplier_name = name
                _logger.info("Fournisseur connu: %s", name)
                break
        
        if not self.supplier_name:
            for line in text_lines[:10]:
                line = line.strip()
                if line and len(line) > 3:
                    skip_keywords = ['TVA', 'BTW', 'FACTURE', 'DATE', 'TOTAL', 'CLIENT', 
                                    'BANCONTACT', 'ARTICLE', 'MONTANT', '€', 'TICKET',
                                    'CAISSE', 'MAGASIN', 'TEL', 'FAX', 'WWW', 'HTTP', 'ADRESSE']
                    if any(kw in line.upper() for kw in skip_keywords):
                        continue
                    if re.match(r'^[\d\s\-\.\,\/\:]+$', line):
                        continue
                    if re.match(r'^\d{4}\s+\w+$', line):
                        continue
                    if re.search(r'\b(SRL|SPRL|SA|NV|BVBA|BV)\b', line.upper()):
                        self.supplier_name = line.strip()
                        break
                    if len(line) > 5:
                        self.supplier_name = line
                        break
            if self.supplier_name:
                _logger.info("Nom fournisseur: %s", self.supplier_name)
        
        # ========================================
        # EXTRACTION DE L'ADRESSE
        # ========================================
        cp_pattern = r'(\d{4})\s+([A-Za-zÀ-ÿ\-]+)'
        for line in text_lines:
            match = re.search(cp_pattern, line)
            if match:
                cp = match.group(1)
                if 1000 <= int(cp) <= 9999:
                    self.supplier_zip = cp
                    self.supplier_city = match.group(2).title()
                    _logger.info("Adresse: %s %s", self.supplier_zip, self.supplier_city)
                    break
        
        street_pattern = r'((?:RUE|AVENUE|AV\.|CHAUSSEE|CH\.|CHEE|BOULEVARD|BLD|BD|PLACE|PL\.|ROUTE)[^\n,]+)'
        match = re.search(street_pattern, text_upper)
        if match:
            self.supplier_street = match.group(1).strip().title()
        
        # ========================================
        # EXTRACTION DES MONTANTS PAR TYPE
        # ========================================
        
        # --- COLRUYT ---
        if doc_type == 'colruyt':
            match = re.search(r'TOTAAL\s*(?:EUR)?\s*(\d+[,\.]\d{2})', text_upper)
            if match:
                self.amount_total = float(match.group(1).replace(',', '.'))
            match = re.search(r'BTW\s*(\d+[,\.]\d{2})', text_upper)
            if match:
                self.amount_tax = float(match.group(1).replace(',', '.'))
        
        # --- DELHAIZE ---
        elif doc_type == 'delhaize':
            match = re.search(r'TOTA+L\s*(?:EUR)?\s*(\d+[,\.]\d{2})', text_upper)
            if match:
                self.amount_total = float(match.group(1).replace(',', '.'))
            match = re.search(r'(?:TVA|BTW)\s*(?:\d+\s*%?)?\s*(\d+[,\.]\d{2})', text_upper)
            if match:
                self.amount_tax = float(match.group(1).replace(',', '.'))
        
        # --- STATION ESSENCE ---
        elif doc_type == 'station':
            # Format tableau: taux% Net TVA
            # Le texte OCR peut avoir des espaces et caractères parasites : "Ï 21.00 € 58 98 € 12.38"
            # Patterns avec espaces optionnels dans les nombres
            tva_table_patterns = [
                # Pattern avec espaces dans les montants : "21.00 € 58 98 € 12.38"
                r'[^\d]*(\d{1,2})[\.,]00\s*€?\s*(\d+)\s+(\d{2})\s*€?\s*(\d+)[\.,](\d{2})',
                # Pattern standard : "21.00 € 58.98 € 12.38"
                r'[^\d]*(\d{1,2})[\.,]00\s*€?\s*(\d+)[\.,](\d{2})\s*€?\s*(\d+)[\.,](\d{2})',
            ]
            for pattern in tva_table_patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    rate = groups[0]
                    self.amount_untaxed = float(f"{groups[1]}.{groups[2]}")
                    self.amount_tax = float(f"{groups[3]}.{groups[4]}")
                    self.amount_total = round(self.amount_untaxed + self.amount_tax, 2)
                    if rate in ('0', '6', '12', '21'):
                        self.tax_rate = rate
                    _logger.info("Station tableau: rate=%s, HT=%s, TVA=%s, TTC=%s", 
                                rate, self.amount_untaxed, self.amount_tax, self.amount_total)
                    break
            
            # Si pas trouvé via tableau, chercher TOTAL seul
            if not self.amount_total:
                match = re.search(r'TOTAL\s*[€:]?\s*(\d+)[\.,](\d{2})', text_upper)
                if match:
                    self.amount_total = float(f"{match.group(1)}.{match.group(2)}")
        
        # --- TELECOM (Proximus, Orange) ---
        elif doc_type == 'telecom':
            match = re.search(r'(?:TOTAL\s*)?(?:TTC|TVAC|A\s*PAYER)\s*:?\s*€?\s*(\d+[\.,]\d{2})', text_upper)
            if match:
                self.amount_total = float(match.group(1).replace(',', '.'))
            match = re.search(r'(?:TOTAL\s*)?HTVA?\s*:?\s*€?\s*(\d+[\.,]\d{2})', text_upper)
            if match:
                self.amount_untaxed = float(match.group(1).replace(',', '.'))
            match = re.search(r'TVA\s*(?:21)?\s*%?\s*:?\s*€?\s*(\d+[\.,]\d{2})', text_upper)
            if match:
                self.amount_tax = float(match.group(1).replace(',', '.'))
        
        # --- FACTURE PRO ---
        elif doc_type == 'facture_pro':
            match = re.search(r'(?:TOTAL\s*)?(?:HTVA|HT|HORS\s*TVA)\s*:?\s*€?\s*(\d+[\.,]\d{2})', text_upper)
            if match:
                self.amount_untaxed = float(match.group(1).replace(',', '.'))
            match = re.search(r'(?:TOTAL\s*)?TVA\s*(?:\d+\s*%?)?\s*:?\s*€?\s*(\d+[\.,]\d{2})', text_upper)
            if match:
                self.amount_tax = float(match.group(1).replace(',', '.'))
            match = re.search(r'(?:TOTAL\s*)?(?:TTC|TVAC|A\s*PAYER)\s*:?\s*€?\s*(\d+[\.,]\d{2})', text_upper)
            if match:
                self.amount_total = float(match.group(1).replace(',', '.'))
        
        # --- GÉNÉRIQUE ---
        if not self.amount_total:
            for pattern in [
                r'TOTAL\s*(?:TTC|TVAC|EUR|€)?\s*:?\s*€?\s*(\d+[\.,]\d{2})',
                r'TOTAAL\s*(?:EUR)?\s*:?\s*€?\s*(\d+[\.,]\d{2})',
                r'A\s*PAYER\s*:?\s*€?\s*(\d+[\.,]\d{2})',
                r'MONTANT\s*TOTAL\s*:?\s*€?\s*(\d+[\.,]\d{2})',
            ]:
                match = re.search(pattern, text_upper)
                if match:
                    self.amount_total = float(match.group(1).replace(',', '.'))
                    break
        
        if not self.amount_untaxed:
            for pattern in [
                r'(?:HTVA|HT|HORS\s*TVA|SOUS-?TOTAL)\s*:?\s*€?\s*(\d+[\.,]\d{2})',
                r'NET\s*:?\s*€?\s*(\d+[\.,]\d{2})',
            ]:
                match = re.search(pattern, text_upper)
                if match:
                    self.amount_untaxed = float(match.group(1).replace(',', '.'))
                    break
        
        if not self.amount_tax:
            for pattern in [
                r'(?:MONTANT\s*)?TVA\s*(?:\d+\s*%?)?\s*:?\s*€?\s*(\d+[\.,]\d{2})',
                r'BTW\s*(?:\d+\s*%?)?\s*:?\s*€?\s*(\d+[\.,]\d{2})',
            ]:
                match = re.search(pattern, text_upper)
                if match:
                    self.amount_tax = float(match.group(1).replace(',', '.'))
                    break
        
        # Calculs automatiques
        if self.amount_total and self.amount_tax and not self.amount_untaxed:
            self.amount_untaxed = round(self.amount_total - self.amount_tax, 2)
        if self.amount_total and self.amount_untaxed and not self.amount_tax:
            self.amount_tax = round(self.amount_total - self.amount_untaxed, 2)
        if self.amount_untaxed and self.amount_tax and not self.amount_total:
            self.amount_total = round(self.amount_untaxed + self.amount_tax, 2)
        
        # ========================================
        # EXTRACTION DE LA DATE
        # ========================================
        for pattern in [
            r'(\d{2})[-/\.](\d{2})[-/\.](\d{4})',
            r'(\d{2})[-/\.](\d{2})[-/\.](\d{2})(?:\s|$|[^\d])',
        ]:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    day, month, year = match
                    if len(year) == 2:
                        year = '20' + year
                    inv_date = date(int(year), int(month), int(day))
                    today = date.today()
                    if inv_date <= today and inv_date.year >= 2020:
                        self.invoice_date = inv_date
                        _logger.info("Date: %s", inv_date)
                        break
                except (ValueError, TypeError):
                    continue
            if self.invoice_date:
                break
        
        # ========================================
        # EXTRACTION DU NUMÉRO DE FACTURE
        # ========================================
        for pattern in [
            r'FACTURE\s*(?:SIMPLIFIEE|N[°o]?)?\s*:?\s*(\d{6,})',
            r'TICKET\s*(?:N[°o]?)?\s*:?\s*(\d{4,})',
            r'(?:N[°oO]|NR)\s*(?:FACTURE)?\s*:?\s*([A-Z0-9\-/]{4,})',
            r'(?:REF|REFERENCE)\s*:?\s*([A-Z0-9\-/]{4,})',
        ]:
            match = re.search(pattern, text_upper)
            if match:
                num = match.group(1).strip()
                if len(num) >= 4 and not num.startswith('BE0'):
                    self.invoice_number = num
                    _logger.info("N° Facture: %s", num)
                    break
        
        # ========================================
        # DÉTECTION DU TAUX DE TVA
        # ========================================
        if not self.tax_rate:
            for pattern, rate in [(r'21[\.,]00', '21'), (r'21\s*%', '21'),
                                   (r'12[\.,]00', '12'), (r'12\s*%', '12'),
                                   (r'6[\.,]00', '6'), (r'6\s*%', '6')]:
                if re.search(pattern, text):
                    self.tax_rate = rate
                    break
            if not self.tax_rate and self.amount_untaxed and self.amount_tax:
                calc_rate = round((self.amount_tax / self.amount_untaxed) * 100)
                if calc_rate in (6, 12, 21):
                    self.tax_rate = str(calc_rate)
        
        # Résumé
        _logger.info("=== Resume: Type=%s, %s (TVA:%s), %s %s, N°%s, Date:%s, HT=%s TVA=%s TTC=%s ===",
                    doc_type, self.supplier_name, self.supplier_vat, self.supplier_zip, 
                    self.supplier_city, self.invoice_number, self.invoice_date,
                    self.amount_untaxed, self.amount_tax, self.amount_total)

    def action_validate(self):
        """Valider les données extraites"""
        self.ensure_one()
        
        if not self.supplier_vat and not self.supplier_name:
            raise UserError(_("Veuillez renseigner au moins le numero TVA ou le nom du fournisseur."))
        
        if not self.amount_total:
            raise UserError(_("Veuillez renseigner le montant total."))
        
        # Créer ou récupérer le fournisseur
        if not self.partner_id:
            self._create_or_find_partner()
        
        self.state = 'validated'
        _logger.info("Donnees validees pour %s", self.name)

    def _create_or_find_partner(self):
        """Créer ou trouver le fournisseur"""
        self.ensure_one()
        
        Partner = self.env['res.partner']
        
        # Recherche par TVA
        if self.supplier_vat:
            partner = Partner.search([
                ('vat', '=ilike', self.supplier_vat)
            ], limit=1)
            if partner:
                self.partner_id = partner
                return
        
        # Recherche par nom
        if self.supplier_name:
            partner = Partner.search([
                ('name', '=ilike', self.supplier_name),
                ('supplier_rank', '>', 0)
            ], limit=1)
            if partner:
                self.partner_id = partner
                return
        
        # Création du fournisseur
        partner_vals = {
            'name': self.supplier_name or _("Fournisseur %s") % self.supplier_vat,
            'supplier_rank': 1,
            'is_company': True,
            'vat': self.supplier_vat,
            'street': self.supplier_street,
            'zip': self.supplier_zip,
            'city': self.supplier_city,
            'country_id': self.supplier_country_id.id if self.supplier_country_id else False,
            'phone': self.supplier_phone,
            'email': self.supplier_email,
        }
        
        self.partner_id = Partner.create(partner_vals)
        _logger.info("Nouveau fournisseur cree: %s", self.partner_id.name)

    def action_create_invoice(self):
        """Créer la facture fournisseur"""
        self.ensure_one()
        
        if self.state != 'validated':
            raise UserError(_("Veuillez d'abord valider les donnees."))
        
        if not self.partner_id:
            raise UserError(_("Veuillez selectionner ou creer un fournisseur."))
        
        if not self.account_id:
            # Chercher un compte de charge par défaut (Odoo 18: pas de company_id sur account.account)
            self.account_id = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
            ], limit=1)
            
            if not self.account_id:
                # Essayer avec un autre type de compte de charge
                self.account_id = self.env['account.account'].search([
                    ('account_type', 'in', ['expense', 'expense_direct_cost', 'expense_depreciation']),
                ], limit=1)
            
            if not self.account_id:
                raise UserError(_("Veuillez selectionner un compte de charge."))
        
        # Chercher la taxe appropriée
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', float(self.tax_rate)),
        ], limit=1)
        
        # Créer la facture fournisseur
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'ref': self.invoice_number or self.name,
            'invoice_line_ids': [(0, 0, {
                'name': _("Achat - %s") % (self.invoice_number or self.name),
                'account_id': self.account_id.id,
                'quantity': 1,
                'price_unit': self.amount_untaxed or self.amount_total,
                'tax_ids': [(6, 0, [tax.id])] if tax else [],
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Attacher le document scanné à la facture
        if self.document:
            self.env['ir.attachment'].create({
                'name': self.document_filename or 'scan_tva.jpg',
                'type': 'binary',
                'datas': self.document,
                'res_model': 'account.move',
                'res_id': invoice.id,
            })
        
        self.invoice_id = invoice
        self.state = 'invoiced'
        _logger.info("Facture fournisseur creee: %s", invoice.name)
        
        # Ouvrir la facture
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        """Voir la facture générée"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("Aucune facture n'a ete creee."))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.ensure_one()
        self.state = 'draft'

    def action_cancel(self):
        """Annuler"""
        self.ensure_one()
        self.state = 'cancelled'

    def action_manual_extract(self):
        """Ouvrir le wizard d'extraction manuelle"""
        self.ensure_one()
        return {
            'name': _('Extraction manuelle'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.scan.tva.extract.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_scan_id': self.id,
                'default_ocr_text': self.ocr_text,
            },
        }
