# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import csv
from io import StringIO
from datetime import date


class InvoiceExportWizard(models.TransientModel):
    """Wizard pour exporter les factures au format comptable"""
    _name = 'lolirine.invoice.export.wizard'
    _description = 'Export comptable factures'

    date_from = fields.Date(
        string='Date debut',
        default=lambda self: date(date.today().year, date.today().month, 1)
    )
    
    date_to = fields.Date(
        string='Date fin',
        default=fields.Date.today
    )
    
    state_filter = fields.Selection([
        ('posted', 'Confirmees uniquement'),
        ('all', 'Toutes'),
    ], string='Etat', default='posted')
    
    payment_filter = fields.Selection([
        ('all', 'Toutes'),
        ('paid', 'Payees uniquement'),
        ('unpaid', 'Non payees uniquement'),
    ], string='Paiement', default='all')
    
    export_format = fields.Selection([
        ('csv_standard', 'CSV Standard'),
        ('csv_comptable', 'CSV Comptable (Winbooks)'),
        ('csv_bob', 'CSV BOB Software'),
    ], string='Format', default='csv_standard', required=True)
    
    include_lines = fields.Boolean(
        string='Inclure lignes de detail',
        default=False
    )
    
    invoice_count = fields.Integer(
        string='Factures trouvees',
        compute='_compute_invoice_count'
    )
    
    # Fichier genere
    file_data = fields.Binary(string='Fichier', readonly=True)
    file_name = fields.Char(string='Nom fichier', readonly=True)

    @api.depends('date_from', 'date_to', 'state_filter', 'payment_filter')
    def _compute_invoice_count(self):
        for wizard in self:
            wizard.invoice_count = len(wizard._get_invoices())

    def _get_invoices(self):
        """Recuperer les factures selon les filtres"""
        domain = [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]
        
        if self.state_filter == 'posted':
            domain.append(('state', '=', 'posted'))
        
        if self.payment_filter == 'paid':
            domain.append(('payment_state', '=', 'paid'))
        elif self.payment_filter == 'unpaid':
            domain.append(('payment_state', 'not in', ('paid', 'reversed')))
        
        return self.env['account.move'].search(domain, order='invoice_date, name')

    def action_export(self):
        """Generer le fichier d'export"""
        self.ensure_one()
        
        invoices = self._get_invoices()
        if not invoices:
            raise UserError(_("Aucune facture trouvee avec ces criteres."))
        
        if self.export_format == 'csv_standard':
            content = self._generate_csv_standard(invoices)
        elif self.export_format == 'csv_comptable':
            content = self._generate_csv_comptable(invoices)
        elif self.export_format == 'csv_bob':
            content = self._generate_csv_bob(invoices)
        else:
            raise UserError(_("Format d'export non supporte."))
        
        # Encoder et sauvegarder
        file_data = base64.b64encode(content.encode('utf-8-sig'))
        file_name = f"export_factures_{self.date_from}_{self.date_to}.csv"
        
        self.write({
            'file_data': file_data,
            'file_name': file_name,
        })
        
        # Retourner l'action pour telecharger
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.invoice.export.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_download': True},
        }

    def _generate_csv_standard(self, invoices):
        """Generer CSV standard"""
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        # En-tete
        headers = [
            'Numero', 'Date', 'Echeance', 'Client', 'TVA Client',
            'HT', 'TVA', 'TTC', 'Solde', 'Etat Paiement',
            'Email envoye', 'Peppol envoye'
        ]
        if self.include_lines:
            headers.extend(['Produit', 'Description', 'Quantite', 'Prix Unit', 'Total Ligne'])
        writer.writerow(headers)
        
        # Donnees
        for inv in invoices:
            base_row = [
                inv.name,
                inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '',
                inv.invoice_date_due.strftime('%d/%m/%Y') if inv.invoice_date_due else '',
                inv.partner_id.name,
                inv.partner_id.vat or '',
                f"{inv.amount_untaxed:.2f}".replace('.', ','),
                f"{inv.amount_tax:.2f}".replace('.', ','),
                f"{inv.amount_total:.2f}".replace('.', ','),
                f"{inv.amount_residual:.2f}".replace('.', ','),
                dict(inv._fields['payment_state'].selection).get(inv.payment_state, ''),
                'Oui' if inv.is_move_sent else 'Non',
                'Oui' if inv.peppol_sent else 'Non',
            ]
            
            if self.include_lines and inv.invoice_line_ids:
                for line in inv.invoice_line_ids.filtered(lambda l: not l.display_type):
                    row = base_row + [
                        line.product_id.default_code or '',
                        line.name[:50] if line.name else '',
                        f"{line.quantity:.2f}".replace('.', ','),
                        f"{line.price_unit:.2f}".replace('.', ','),
                        f"{line.price_subtotal:.2f}".replace('.', ','),
                    ]
                    writer.writerow(row)
            else:
                writer.writerow(base_row)
        
        return output.getvalue()

    def _generate_csv_comptable(self, invoices):
        """Generer CSV format Winbooks"""
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        # En-tete Winbooks
        headers = [
            'DBKCODE', 'DBKTYPE', 'DOCNUMBER', 'DOCORDER', 'OPCODE',
            'ACCOUNTGL', 'ACCOUNTRP', 'BOOKYEAR', 'PERIOD',
            'DATE', 'DATEA', 'DATEB', 'DATEC', 'DATEA',
            'COMMENT', 'AMOUNT', 'AMOUNTEUR', 'VATBASE', 'VATCODE',
            'CURRCODE', 'CURRAMOUNT', 'REMESSION', 'MATCHING'
        ]
        writer.writerow(headers)
        
        for inv in invoices:
            period = inv.invoice_date.month if inv.invoice_date else 1
            year = inv.invoice_date.year if inv.invoice_date else date.today().year
            
            row = [
                'VEN',  # Journal ventes
                '1',    # Type
                inv.name.replace('/', ''),
                '1',
                '',
                '400000',  # Compte client
                inv.partner_id.ref or '',
                str(year)[-2:],
                str(period).zfill(2),
                inv.invoice_date.strftime('%d%m%Y') if inv.invoice_date else '',
                inv.invoice_date_due.strftime('%d%m%Y') if inv.invoice_date_due else '',
                '', '', '',
                inv.partner_id.name[:40],
                f"{inv.amount_total:.2f}".replace('.', ','),
                f"{inv.amount_total:.2f}".replace('.', ','),
                f"{inv.amount_untaxed:.2f}".replace('.', ','),
                '21',  # Code TVA
                'EUR',
                f"{inv.amount_total:.2f}".replace('.', ','),
                '', ''
            ]
            writer.writerow(row)
        
        return output.getvalue()

    def _generate_csv_bob(self, invoices):
        """Generer CSV format BOB Software"""
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        # En-tete BOB
        headers = [
            'Journal', 'Annee', 'Mois', 'Numero', 'Date',
            'Compte', 'Libelle', 'Debit', 'Credit', 'Devise',
            'Reference', 'Echeance'
        ]
        writer.writerow(headers)
        
        for inv in invoices:
            # Ligne client (debit)
            writer.writerow([
                'VEN',
                inv.invoice_date.year if inv.invoice_date else '',
                inv.invoice_date.month if inv.invoice_date else '',
                inv.name,
                inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '',
                '400000',
                inv.partner_id.name[:30],
                f"{inv.amount_total:.2f}".replace('.', ','),
                '0,00',
                'EUR',
                inv.partner_id.vat or inv.partner_id.ref or '',
                inv.invoice_date_due.strftime('%d/%m/%Y') if inv.invoice_date_due else '',
            ])
            
            # Ligne ventes (credit)
            writer.writerow([
                'VEN',
                inv.invoice_date.year if inv.invoice_date else '',
                inv.invoice_date.month if inv.invoice_date else '',
                inv.name,
                inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '',
                '700000',
                'Ventes',
                '0,00',
                f"{inv.amount_untaxed:.2f}".replace('.', ','),
                'EUR',
                '', '',
            ])
            
            # Ligne TVA (credit)
            if inv.amount_tax > 0:
                writer.writerow([
                    'VEN',
                    inv.invoice_date.year if inv.invoice_date else '',
                    inv.invoice_date.month if inv.invoice_date else '',
                    inv.name,
                    inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '',
                    '451000',
                    'TVA due',
                    '0,00',
                    f"{inv.amount_tax:.2f}".replace('.', ','),
                    'EUR',
                    '', '',
                ])
        
        return output.getvalue()

    def action_download(self):
        """Telecharger le fichier"""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Aucun fichier a telecharger. Lancez d'abord l'export."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=lolirine.invoice.export.wizard&id={self.id}&field=file_data&filename={self.file_name}&download=true',
            'target': 'self',
        }
