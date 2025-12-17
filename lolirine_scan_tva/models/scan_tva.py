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
    _inherit = ["mail.thread", "mail.activity.mixin"]
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
    ], string="Etat", default='draft', tracking=True)
    
    # Document source
    document_type = fields.Selection([
        ('image', 'Image'),
        ('pdf', 'PDF'),
    ], string="Type de document", default='image')
    
    document = fields.Binary(
        string="Document",
        attachment=True,
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
        tracking=True,
        help="Numero de TVA du fournisseur (format BE0123456789)"
    )
    supplier_name = fields.Char(
        string="Nom du fournisseur",
        tracking=True
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
        tracking=True
    )
    partner_exists = fields.Boolean(
        string="Fournisseur existant",
        compute="_compute_partner_exists"
    )
    
    # Informations facture
    invoice_number = fields.Char(
        string="Numero facture/ticket",
        tracking=True
    )
    invoice_date = fields.Date(
        string="Date de facture",
        default=fields.Date.today,
        tracking=True
    )
    
    # Montants
    amount_untaxed = fields.Monetary(
        string="Montant HT",
        currency_field='currency_id',
        tracking=True
    )
    amount_tax = fields.Monetary(
        string="Montant TVA",
        currency_field='currency_id',
        tracking=True
    )
    amount_total = fields.Monetary(
        string="Montant TTC",
        currency_field='currency_id',
        tracking=True
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
        
        if not OCR_AVAILABLE:
            raise UserError(_(
                "La bibliotheque OCR n'est pas disponible. "
                "Veuillez installer pytesseract et Pillow."
            ))
        
        try:
            # Décoder le document
            document_data = base64.b64decode(self.document)
            
            # Convertir en image si PDF
            if self.document_type == 'pdf' or (self.document_filename and self.document_filename.lower().endswith('.pdf')):
                if not PDF_AVAILABLE:
                    raise UserError(_("pdf2image n'est pas installe pour convertir les PDF."))
                images = convert_from_bytes(document_data)
                image = images[0] if images else None
            else:
                image = Image.open(io.BytesIO(document_data))
            
            if not image:
                raise UserError(_("Impossible de lire l'image."))
            
            # Extraction OCR
            ocr_text = pytesseract.image_to_string(image, lang='fra+nld')
            self.ocr_text = ocr_text
            
            # Extraction automatique des données
            self._extract_data_from_ocr(ocr_text)
            
            self.state = 'extracted'
            
            self.message_post(
                body=_("Document scanne et donnees extraites avec succes."),
                message_type='notification'
            )
            
        except Exception as e:
            _logger.error("Erreur OCR: %s", str(e))
            raise UserError(_("Erreur lors de l'extraction OCR: %s") % str(e))

    def _extract_data_from_ocr(self, text):
        """Extraire les données du texte OCR"""
        if not text:
            return
        
        text_upper = text.upper()
        
        # Extraction du numéro de TVA belge (BE + 10 chiffres)
        vat_patterns = [
            r'BE\s*0?\d{3}\.?\d{3}\.?\d{3}',
            r'TVA\s*:?\s*(BE\s*0?\d{3}\.?\d{3}\.?\d{3})',
            r'BTW\s*:?\s*(BE\s*0?\d{3}\.?\d{3}\.?\d{3})',
        ]
        for pattern in vat_patterns:
            match = re.search(pattern, text_upper)
            if match:
                vat = match.group(0) if 'BE' in match.group(0) else match.group(1)
                self.supplier_vat = re.sub(r'[\s\.]', '', vat)
                break
        
        # Extraction des montants
        # Pattern pour montants en euros
        amount_patterns = [
            (r'TOTAL\s*(?:TTC|TVAC)?\s*:?\s*(\d+[.,]\d{2})\s*€?', 'total'),
            (r'TOTAAL\s*:?\s*(\d+[.,]\d{2})\s*€?', 'total'),
            (r'€\s*(\d+[.,]\d{2})\s*$', 'total'),
            (r'HTVA\s*:?\s*(\d+[.,]\d{2})', 'untaxed'),
            (r'HORS\s*TVA\s*:?\s*(\d+[.,]\d{2})', 'untaxed'),
            (r'TVA\s*(?:21|12|6)?\s*%?\s*:?\s*(\d+[.,]\d{2})', 'tax'),
            (r'BTW\s*(?:21|12|6)?\s*%?\s*:?\s*(\d+[.,]\d{2})', 'tax'),
        ]
        
        for pattern, amount_type in amount_patterns:
            match = re.search(pattern, text_upper)
            if match:
                amount_str = match.group(1).replace(',', '.')
                amount = float(amount_str)
                if amount_type == 'total' and not self.amount_total:
                    self.amount_total = amount
                elif amount_type == 'untaxed' and not self.amount_untaxed:
                    self.amount_untaxed = amount
                elif amount_type == 'tax' and not self.amount_tax:
                    self.amount_tax = amount
        
        # Extraction de la date
        date_patterns = [
            r'(\d{2})[/.-](\d{2})[/.-](\d{4})',
            r'(\d{2})[/.-](\d{2})[/.-](\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    day, month, year = match.groups()
                    if len(year) == 2:
                        year = '20' + year
                    self.invoice_date = date(int(year), int(month), int(day))
                    break
                except (ValueError, TypeError):
                    pass
        
        # Extraction du numéro de facture/ticket
        ticket_patterns = [
            r'(?:FACTURE|FACTUUR|TICKET|BON)\s*(?:N[°o]?|NR)?\s*:?\s*([A-Z0-9/-]+)',
            r'N[°o]?\s*:?\s*([A-Z0-9/-]+)',
        ]
        for pattern in ticket_patterns:
            match = re.search(pattern, text_upper)
            if match:
                self.invoice_number = match.group(1).strip()
                break
        
        # Détection du taux de TVA
        if '21%' in text_upper or '21 %' in text_upper:
            self.tax_rate = '21'
        elif '12%' in text_upper or '12 %' in text_upper:
            self.tax_rate = '12'
        elif '6%' in text_upper or '6 %' in text_upper:
            self.tax_rate = '6'
        elif '0%' in text_upper or '0 %' in text_upper:
            self.tax_rate = '0'

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
        
        self.message_post(
            body=_("Donnees validees. Pret pour la creation de la facture."),
            message_type='notification'
        )

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
        
        self.message_post(
            body=_("Nouveau fournisseur cree: %s") % self.partner_id.name,
            message_type='notification'
        )

    def action_create_invoice(self):
        """Créer la facture fournisseur"""
        self.ensure_one()
        
        if self.state != 'validated':
            raise UserError(_("Veuillez d'abord valider les donnees."))
        
        if not self.partner_id:
            raise UserError(_("Veuillez selectionner ou creer un fournisseur."))
        
        if not self.account_id:
            # Chercher un compte de charge par défaut
            self.account_id = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if not self.account_id:
                raise UserError(_("Veuillez selectionner un compte de charge."))
        
        # Chercher la taxe appropriée
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', float(self.tax_rate)),
            ('company_id', '=', self.company_id.id)
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
        
        self.message_post(
            body=_("Facture fournisseur creee: %s") % invoice.name,
            message_type='notification'
        )
        
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
