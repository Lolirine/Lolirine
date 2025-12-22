from odoo import models, fields, api
from odoo.exceptions import UserError


class LolirineScanTVA(models.Model):
    _name = 'lolirine.scan.tva'
    _description = 'Scan TVA Lolirine'
    _order = 'create_date desc'

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default='Nouveau')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scanned', 'Scanne'),
        ('processed', 'Traite'),
        ('invoice_created', 'Facture creee'),
        ('cancelled', 'Annule'),
    ], string="Etat", default='draft', tracking=True)

    # Document
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Nom du fichier")

    # Informations extraites
    supplier_vat = fields.Char(string="Numero TVA fournisseur")
    supplier_name = fields.Char(string="Nom fournisseur")
    supplier_address = fields.Char(string="Adresse fournisseur")
    invoice_date = fields.Date(string="Date facture")
    invoice_number = fields.Char(string="Numero facture")
    amount_untaxed = fields.Float(string="Montant HT")
    amount_tax = fields.Float(string="Montant TVA")
    amount_total = fields.Float(string="Montant TTC")

    # Relations
    partner_id = fields.Many2one('res.partner', string="Fournisseur")
    invoice_id = fields.Many2one('account.move', string="Facture creee")
    company_id = fields.Many2one('res.company', string="Societe", default=lambda self: self.env.company)

    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('lolirine.scan.tva') or 'Nouveau'
        return super().create(vals_list)

    def action_scan(self):
        """Marquer comme scanné"""
        self.ensure_one()
        self.state = 'scanned'

    def action_process(self):
        """Traiter le scan"""
        self.ensure_one()
        # Rechercher ou créer le fournisseur
        if self.supplier_vat and not self.partner_id:
            partner = self.env['res.partner'].search([('vat', '=', self.supplier_vat)], limit=1)
            if not partner and self.supplier_name:
                partner = self.env['res.partner'].create({
                    'name': self.supplier_name,
                    'vat': self.supplier_vat,
                    'street': self.supplier_address,
                    'supplier_rank': 1,
                })
            self.partner_id = partner.id
        self.state = 'processed'

    def action_create_invoice(self):
        """Créer la facture fournisseur"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError("Veuillez d'abord sélectionner un fournisseur.")

        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'ref': self.invoice_number,
            'invoice_line_ids': [(0, 0, {
                'name': 'Achat - ' + (self.invoice_number or self.name),
                'quantity': 1,
                'price_unit': self.amount_untaxed or self.amount_total,
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.write({
            'invoice_id': invoice.id,
            'state': 'invoice_created',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Annuler le scan"""
        self.ensure_one()
        self.state = 'cancelled'

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.ensure_one()
        self.state = 'draft'
