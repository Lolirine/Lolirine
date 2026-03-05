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
        ('2.1', '2,1% (FR)'),
        ('3', '3% (LU)'),
        ('5.5', '5,5% (FR)'),
        ('6', '6% (BE)'),
        ('7', '7% (DE)'),
        ('8', '8% (LU)'),
        ('9', '9% (NL)'),
        ('10', '10% (FR)'),
        ('12', '12% (BE)'),
        ('14', '14% (LU)'),
        ('17', '17% (LU)'),
        ('19', '19% (DE)'),
        ('20', '20% (FR)'),
        ('21', '21% (BE/NL)'),
        ('multi', 'Multiple'),
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

    # Lignes de ventilation TVA
    vat_line_ids = fields.One2many(
        'lolirine.scan.tva.line', 'scan_id',
        string='Ventilation TVA',
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
            
            # Detecter le pays depuis le prefixe TVA
            country_map = {
                'BE': 'base.be',
                'LU': 'base.lu',
                'FR': 'base.fr',
                'NL': 'base.nl',
                'DE': 'base.de',
            }
            prefix = vat_clean[:2] if len(vat_clean) >= 2 else ''
            if prefix in country_map:
                country = self.env.ref(country_map[prefix], raise_if_not_found=False)
                if country:
                    self.supplier_country_id = country
            
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
        if self.amount_untaxed and self.tax_rate and self.tax_rate != 'multi':
            rate = float(self.tax_rate) / 100
            self.amount_tax = self.amount_untaxed * rate
            self.amount_total = self.amount_untaxed + self.amount_tax

    @api.onchange('amount_total', 'tax_rate')
    def _onchange_amount_total(self):
        """Calculer HT depuis TTC"""
        if self.amount_total and self.tax_rate and self.tax_rate != 'multi' and not self.amount_untaxed:
            rate = float(self.tax_rate) / 100
            self.amount_untaxed = self.amount_total / (1 + rate)
            self.amount_tax = self.amount_total - self.amount_untaxed

    @api.onchange('vat_line_ids')
    def _onchange_vat_lines(self):
        """Synchroniser les totaux depuis les lignes de ventilation TVA"""
        if self.vat_line_ids:
            self.amount_untaxed = sum(line.base_amount for line in self.vat_line_ids)
            self.amount_tax = sum(line.vat_amount for line in self.vat_line_ids)
            self.amount_total = sum(line.total_amount for line in self.vat_line_ids)
            # Determiner le taux TVA
            rates = set(line.tax_rate for line in self.vat_line_ids if line.tax_rate)
            if len(rates) > 1:
                self.tax_rate = 'multi'
            elif len(rates) == 1:
                rate = rates.pop()
                rate_str = str(int(rate)) if rate == int(rate) else str(rate)
                selection_keys = [k for k, v in self._fields['tax_rate'].selection]
                if rate_str in selection_keys:
                    self.tax_rate = rate_str

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
                    
                    # Configuration tesseract adaptative selon la taille du document
                    # PSM 3 = fully automatic page segmentation (meilleur pour factures A4)
                    # PSM 6 = uniform block of text (meilleur pour tickets de caisse)
                    w, h = image.size
                    if w > 1500 or h > 2000:
                        # Grande image = probablement facture A4
                        custom_config = r'--oem 3 --psm 3 -l fra+nld+deu+eng'
                        _logger.info("Mode A4 detecte (PSM 3), langues: fra+nld+deu+eng")
                    else:
                        # Petite image = probablement ticket de caisse
                        custom_config = r'--oem 3 --psm 6 -l fra+nld'
                        _logger.info("Mode ticket detecte (PSM 6), langues: fra+nld")
                    
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
        elif any(x in text_upper for x in ['PALL CENTER', 'PALL', 'SPALL']):
            doc_type = 'pall_center'
        elif any(x in text_upper for x in ['HTVA', 'HORS TVA', 'MONTANT HT']):
            doc_type = 'facture_pro'
        
        _logger.info("Type de document detecte: %s", doc_type)
        
        # ========================================
        # EXTRACTION DU NUMÉRO DE TVA (BE, LU, FR, NL, DE)
        # ========================================
        vat_patterns = [
            # Belge
            r'TVA\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'BTW\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'N[°o]?\s*(?:TVA|ENTREPRISE)\s*:?\s*(BE\s*0?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'(BE\s*0\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'(BE0\d{9})',
            # Luxembourgeois
            r'(LU\s*\d{8})',
            r'TVA\s*:?\s*(LU\s*\d{8})',
            # Francais
            r'(FR\s*[A-Z0-9]{2}\s*\d{9})',
            r'TVA\s*:?\s*(FR\s*[A-Z0-9]{2}\s*\d{9})',
            # Neerlandais
            r'(NL\s*\d{9}B\d{2})',
            r'BTW\s*:?\s*(NL\s*\d{9}B\d{2})',
            # Allemand
            r'(DE\s*\d{9})',
            r'UST[\.\-]?(?:ID)?[\.\-]?(?:NR)?\s*:?\s*(DE\s*\d{9})',
        ]
        for pattern in vat_patterns:
            match = re.search(pattern, text_upper)
            if match:
                vat = match.group(1) if match.lastindex else match.group(0)
                vat = re.sub(r'[\s\.]', '', vat)
                self.supplier_vat = vat
                _logger.info("TVA trouvee: %s", vat)
                
                # Detecter le pays
                prefix = vat[:2]
                country_map = {
                    'BE': 'base.be', 'LU': 'base.lu', 'FR': 'base.fr',
                    'NL': 'base.nl', 'DE': 'base.de',
                }
                if prefix in country_map:
                    country = self.env.ref(country_map[prefix], raise_if_not_found=False)
                    if country:
                        self.supplier_country_id = country
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
            'PALL CENTER': 'Pall Center',
            'SPALL': 'Pall Center',
            'CACTUS': 'Cactus',
            'MATCH': 'Match',
            'INTERMARCHE': 'Intermarche',
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
                    if re.search(r'\b(SRL|SPRL|SA|NV|BVBA|BV|S\.A\.|S\.A\.R\.L)\b', line.upper()):
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
        # Code postal BE (4 chiffres) ou LU (4 chiffres) ou FR (5 chiffres) ou DE (5 chiffres)
        cp_pattern = r'(\d{4,5})\s+([A-Za-zÀ-ÿ\-]+)'
        for line in text_lines:
            match = re.search(cp_pattern, line)
            if match:
                cp = match.group(1)
                cp_int = int(cp)
                # BE: 1000-9999, LU: 1000-9999, FR: 01000-98999, DE: 01000-99999
                if (1000 <= cp_int <= 9999) or (10000 <= cp_int <= 99999):
                    self.supplier_zip = cp
                    self.supplier_city = match.group(2).title()
                    _logger.info("Adresse: %s %s", self.supplier_zip, self.supplier_city)
                    break
        
        street_pattern = r'((?:RUE|AVENUE|AV\.|CHAUSSEE|CH\.|CHEE|BOULEVARD|BLD|BD|PLACE|PL\.|ROUTE|STRASSE|STR\.|STRASZE)[^\n,]+)'
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
            tva_table_patterns = [
                r'[^\d]*(\d{1,2})[\.,]00\s*€?\s*(\d+)\s+(\d{2})\s*€?\s*(\d+)[\.,](\d{2})',
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
            
            if not self.amount_total:
                match = re.search(r'TOTAL\s*[€:]?\s*(\d+)[\.,](\d{2})', text_upper)
                if match:
                    self.amount_total = float(f"{match.group(1)}.{match.group(2)}")
        
        # --- PALL CENTER (Luxembourg - multi-taux) ---
        elif doc_type == 'pall_center':
            # Chercher le total
            match = re.search(r'TOTA+L?\s*(?:EUR|€)?\s*(\d+[\.,]\d{2})\s*€?', text_upper)
            if match:
                self.amount_total = float(match.group(1).replace(',', '.'))
            
            # Chercher le tableau TVA-Calculatio: Taux % Base HT TVA TTC
            tva_table = re.findall(
                r'(\d{1,2})\s+(\d{1,2})\s+(\d+[\.,]\d{2})\s+(\d+[\.,]\d{2})\s+(\d+[\.,]\d{2})',
                text
            )
            if tva_table:
                self.tax_rate = 'multi'
                total_ht = 0.0
                total_tva = 0.0
                total_ttc = 0.0
                for row in tva_table:
                    rate = float(row[1])
                    base = float(row[2].replace(',', '.'))
                    vat_amt = float(row[3].replace(',', '.'))
                    ttc = float(row[4].replace(',', '.'))
                    total_ht += base
                    total_tva += vat_amt
                    total_ttc += ttc
                    _logger.info("Pall Center TVA: %s%% Base=%s TVA=%s TTC=%s", rate, base, vat_amt, ttc)
                self.amount_untaxed = round(total_ht, 2)
                self.amount_tax = round(total_tva, 2)
                if not self.amount_total:
                    self.amount_total = round(total_ttc, 2)
        
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
                r'PAYE\s*:?\s*€?\s*(\d+[\.,]\d{2})\s*€',
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
            r'FACTURE\s*N[°o]?\s*:?\s*(\d+)',
            r'TICKET\s*(?:N[°o]?)?\s*:?\s*(\d{4,})',
            r'(?:N[°oO]|NR)\s*(?:FACTURE)?\s*:?\s*([A-Z0-9\-/]{4,})',
            r'(?:REF|REFERENCE)\s*:?\s*([A-Z0-9\-/]{4,})',
            r'NUMERO\s*DE\s*TICKET\s*:?\s*(\d{6,})',
        ]:
            match = re.search(pattern, text_upper)
            if match:
                num = match.group(1).strip()
                if len(num) >= 4 and not num.startswith('BE0') and not num.startswith('LU'):
                    self.invoice_number = num
                    _logger.info("N° Facture: %s", num)
                    break
        
        # ========================================
        # DÉTECTION DU TAUX DE TVA
        # ========================================
        if not self.tax_rate or self.tax_rate == '21':
            # Verifier d'abord si c'est un multi-taux (deja detecte pour pall_center)
            if self.tax_rate != 'multi':
                for pattern, rate in [
                    (r'21[\.,]00', '21'), (r'21\s*%', '21'),
                    (r'20[\.,]00', '20'), (r'20\s*%', '20'),
                    (r'19[\.,]00', '19'), (r'19\s*%', '19'),
                    (r'17[\.,]00', '17'), (r'17\s*%', '17'),
                    (r'14[\.,]00', '14'), (r'14\s*%', '14'),
                    (r'12[\.,]00', '12'), (r'12\s*%', '12'),
                    (r'9[\.,]00', '9'), (r'9\s*%', '9'),
                    (r'7[\.,]00', '7'), (r'7\s*%', '7'),
                    (r'6[\.,]00', '6'), (r'6\s*%', '6'),
                    (r'5[\.,]50', '5.5'), (r'5[,\.]5\s*%', '5.5'),
                    (r'3[\.,]00', '3'), (r'3\s*%', '3'),
                ]:
                    if re.search(pattern, text):
                        self.tax_rate = rate
                        break
                if not self.tax_rate and self.amount_untaxed and self.amount_tax:
                    calc_rate = round((self.amount_tax / self.amount_untaxed) * 100)
                    rate_map = {0: '0', 3: '3', 6: '6', 7: '7', 8: '8', 9: '9',
                               10: '10', 12: '12', 14: '14', 17: '17', 19: '19', 20: '20', 21: '21'}
                    if calc_rate in rate_map:
                        self.tax_rate = rate_map[calc_rate]
        
        # ========================================
        # CREATION AUTOMATIQUE DES LIGNES DE VENTILATION
        # pour les documents multi-taux detectes
        # ========================================
        if doc_type == 'pall_center' and tva_table:
            ScanLine = self.env['lolirine.scan.tva.line']
            for row in tva_table:
                rate = float(row[1])
                base = float(row[2].replace(',', '.'))
                vat_amt = float(row[3].replace(',', '.'))
                ttc = float(row[4].replace(',', '.'))
                ScanLine.create({
                    'scan_id': self.id,
                    'tax_rate': rate,
                    'base_amount': base,
                    'vat_amount': vat_amt,
                    'total_amount': ttc,
                })
            _logger.info("Lignes de ventilation TVA creees: %d lignes", len(tva_table))
        
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
        """Creer la facture fournisseur - supporte les lignes de ventilation multi-taux"""
        self.ensure_one()
        
        if self.state != 'validated':
            raise UserError(_("Veuillez d'abord valider les donnees."))
        
        if not self.partner_id:
            raise UserError(_("Veuillez selectionner ou creer un fournisseur."))
        
        if not self.account_id:
            self.account_id = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
            ], limit=1)
            
            if not self.account_id:
                self.account_id = self.env['account.account'].search([
                    ('account_type', 'in', ['expense', 'expense_direct_cost', 'expense_depreciation']),
                ], limit=1)
            
            if not self.account_id:
                raise UserError(_("Veuillez selectionner un compte de charge."))
        
        invoice_lines = []
        
        # Si on a des lignes de ventilation TVA, les utiliser
        if self.vat_line_ids:
            for line in self.vat_line_ids:
                # Chercher la taxe correspondante au taux
                tax = self.env['account.tax'].search([
                    ('type_tax_use', '=', 'purchase'),
                    ('amount', '=', line.tax_rate),
                ], limit=1)
                
                line_name = line.description or _("Achat - %s") % (self.invoice_number or self.name)
                if line.tax_rate:
                    line_name += " (TVA %.1f%%)" % line.tax_rate
                
                invoice_lines.append((0, 0, {
                    'name': line_name,
                    'account_id': self.account_id.id,
                    'quantity': 1,
                    'price_unit': line.base_amount,
                    'tax_ids': [(6, 0, [tax.id])] if tax else [],
                }))
        else:
            # Pas de ventilation: ligne unique (ancien comportement)
            tax = False
            if self.tax_rate and self.tax_rate != 'multi':
                tax = self.env['account.tax'].search([
                    ('type_tax_use', '=', 'purchase'),
                    ('amount', '=', float(self.tax_rate)),
                ], limit=1)
            
            invoice_lines.append((0, 0, {
                'name': _("Achat - %s") % (self.invoice_number or self.name),
                'account_id': self.account_id.id,
                'quantity': 1,
                'price_unit': self.amount_untaxed or self.amount_total,
                'tax_ids': [(6, 0, [tax.id])] if tax else [],
            }))
        
        # Creer la facture fournisseur
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'ref': self.invoice_number or self.name,
            'invoice_line_ids': invoice_lines,
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Attacher le document scanne a la facture
        if self.document:
            self.env['ir.attachment'].create({
                'name': self.document_filename or 'scan_tva.pdf',
                'type': 'binary',
                'datas': self.document,
                'res_model': 'account.move',
                'res_id': invoice.id,
            })
        
        self.invoice_id = invoice
        self.state = 'invoiced'
        _logger.info("Facture fournisseur creee: %s avec %d ligne(s)", invoice.name, len(invoice_lines))
        
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
