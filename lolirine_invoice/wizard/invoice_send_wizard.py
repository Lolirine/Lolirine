# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)


class LolirineInvoiceSendWizard(models.TransientModel):
    _name = "lolirine.invoice.send.wizard"
    _description = "Assistant d'envoi de facture Lolirine"

    invoice_id = fields.Many2one(
        "account.move",
        string="Facture",
        required=True,
        ondelete="cascade"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Client",
        related="invoice_id.partner_id",
        readonly=True
    )
    
    # Champs email avec previsualisation
    email_to = fields.Char(
        string="Destinataire",
        required=True,
        help="Adresse email du destinataire"
    )
    email_subject = fields.Char(
        string="Sujet",
        required=True
    )
    email_body = fields.Html(
        string="Contenu de l'email",
        required=True
    )
    
    # Options d'envoi
    send_method = fields.Selection([
        ('email', 'Email'),
        ('peppol', 'Peppol (facturation electronique)'),
        ('both', 'Email + Peppol'),
    ], string="Methode d'envoi", default='email', required=True)
    
    include_pdf = fields.Boolean(
        string="Joindre le PDF Lolirine",
        default=True
    )
    
    # Info Peppol
    peppol_available = fields.Boolean(
        string="Peppol disponible",
        compute="_compute_peppol_available"
    )
    peppol_eas = fields.Selection(
        string="EAS",
        related="partner_id.peppol_eas",
        readonly=True
    )
    peppol_endpoint = fields.Char(
        string="Endpoint Peppol",
        related="partner_id.peppol_endpoint",
        readonly=True
    )

    @api.depends('partner_id')
    def _compute_peppol_available(self):
        for wizard in self:
            wizard.peppol_available = bool(
                wizard.partner_id and 
                wizard.partner_id.peppol_eas and 
                wizard.partner_id.peppol_endpoint
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        active_id = self.env.context.get('active_id')
        if active_id:
            invoice = self.env['account.move'].browse(active_id)
            res['invoice_id'] = invoice.id
            res['email_to'] = invoice.partner_id.email or ''
            res['email_subject'] = self._get_default_subject(invoice)
            res['email_body'] = self._get_default_body(invoice)
        
        return res

    def _get_default_subject(self, invoice):
        """Generer le sujet par defaut"""
        return f"Envoi de votre facture mensuelle - Garde-meubles Lolirine"

    def _get_default_body(self, invoice):
        """Generer le corps de l'email par defaut - identique au template Odoo"""
        return f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {invoice.partner_id.name or ''},</p>
    
    <p>Veuillez trouver en piece jointe votre facture mensuelle relative a la location de votre box au sein de notre site Lolirine.</p>
    
    <p>Cette facture correspond a la periode de location en cours et reprend le detail des prestations facturees, conformement aux conditions prevues dans votre contrat de garde-meubles. Nous vous invitons a en prendre connaissance et a proceder au reglement selon les modalites indiquees sur le document.</p>
    
    <p>Sauf disposition contraire, le paiement est attendu a la date d'echeance mentionnee sur la facture. En cas de retard de paiement, des penalites pourront etre appliquees conformement aux conditions contractuelles.</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px;">
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numero de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{invoice.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date de facturation</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{invoice.invoice_date or ''}</td>
        </tr>
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'echeance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{invoice.invoice_date_due or ''}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant total</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{invoice.amount_total:.2f} EUR</strong></td>
        </tr>
    </table>
    
    <p><strong>Modalites de paiement :</strong></p>
    <ul>
        <li>Communication structuree : {invoice.payment_reference or 'Voir facture'}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
    </ul>
    
    <p>Pour toute question concernant cette facture, votre contrat ou les modalites de paiement, vous pouvez nous contacter a l'adresse suivante : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a> ou par telephone au 0497/44 41 46.</p>
    
    <p>Nous vous remercions de votre confiance et restons a votre disposition.</p>
    
    <p>Cordialement,</p>
    
    <p style="margin-top: 20px;">
        <strong>Lolirine Garde-Meubles</strong><br/>
        Feron Rodney<br/>
        Tel. : 0497/44 41 46<br/>
        Email : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a>
    </p>
</div>
        """

    def action_preview_pdf(self):
        """Apercu du PDF de la facture"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/lolirine_invoice.report_invoice_lolirine/{self.invoice_id.id}',
            'target': 'new',
        }

    def action_send(self):
        """Envoyer la facture selon la methode choisie"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError("Aucune facture selectionnee.")
        
        messages = []
        
        if self.send_method in ('email', 'both'):
            if not self.email_to:
                raise UserError("Veuillez specifier une adresse email.")
            self._send_by_email()
            messages.append(f"Email envoye a {self.email_to}")
        
        if self.send_method in ('peppol', 'both'):
            result = self._send_by_peppol()
            if result:
                messages.append(f"Envoye via Peppol a {self.peppol_endpoint}")
        
        # Marquer comme envoyee
        self.invoice_id.write({'is_move_sent': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Facture envoyee',
                'message': f"La facture {self.invoice_id.name} a ete envoyee. {' | '.join(messages)}",
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_by_email(self):
        """Envoyer la facture par email avec le contenu personnalise"""
        attachment_ids = []
        
        # Generer le PDF si demande
        if self.include_pdf:
            try:
                report = self.env.ref('lolirine_invoice.action_report_invoice_lolirine', raise_if_not_found=False)
                if not report:
                    report = self.env.ref('account.account_invoices', raise_if_not_found=False)
                
                if report:
                    pdf_content, _unused = report._render_qweb_pdf(report.id, [self.invoice_id.id])
                    attachment = self.env['ir.attachment'].create({
                        'name': f"Facture_{self.invoice_id.name.replace('/', '_')}.pdf",
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'account.move',
                        'res_id': self.invoice_id.id,
                        'mimetype': 'application/pdf',
                    })
                    attachment_ids.append(attachment.id)
            except Exception as e:
                _logger.error(f"Erreur generation PDF: {e}")
        
        # Creer et envoyer l'email
        mail = self.env['mail.mail'].sudo().create({
            'subject': self.email_subject,
            'body_html': self.email_body,
            'email_from': 'gardemeublelolirine@gmail.com',
            'email_to': self.email_to,
            'model': 'account.move',
            'res_id': self.invoice_id.id,
            'attachment_ids': [(6, 0, attachment_ids)],
        })
        mail.send()
        
        # Poster dans le chatter
        self.invoice_id.message_post(
            body=f"Facture envoyee par email a {self.email_to} avec PDF Lolirine attache.",
            attachment_ids=attachment_ids,
            message_type='notification'
        )

    def _send_by_peppol(self):
        """Envoyer la facture via Peppol"""
        if not self.peppol_available:
            raise UserError(
                "L'envoi Peppol n'est pas disponible pour ce client. "
                "Veuillez configurer l'EAS et l'endpoint Peppol dans la fiche client "
                "(onglet 'Facturation electronique')."
            )
        
        return self.invoice_id._send_invoice_peppol_auto()

    def action_send_and_close(self):
        """Envoyer et fermer le wizard"""
        self.action_send()
        return {'type': 'ir.actions.act_window_close'}
