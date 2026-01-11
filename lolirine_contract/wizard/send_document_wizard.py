# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64


class SendDocumentWizard(models.TransientModel):
    _name = 'send.document.wizard'
    _description = 'Wizard d\'envoi de documents avec aperçu'

    sale_order_id = fields.Many2one('sale.order', string='Commande', required=True)
    document_type = fields.Selection([
        ('quotation', 'Devis'),
        ('contract', 'Contrat'),
    ], string='Type de document', required=True, default='contract')
    
    partner_id = fields.Many2one('res.partner', string='Client', related='sale_order_id.partner_id')
    partner_email = fields.Char(string='Email', related='partner_id.email')
    
    email_to = fields.Char(string='Destinataire', required=True)
    email_subject = fields.Char(string='Sujet', required=True)
    email_body = fields.Html(string='Message')
    
    attachment_id = fields.Many2one('ir.attachment', string='Pièce jointe')
    attachment_name = fields.Char(string='Nom du fichier')
    preview_pdf = fields.Binary(string='Aperçu PDF', attachment=False)
    preview_url = fields.Char(string='URL Aperçu', compute='_compute_preview_url')

    @api.depends('sale_order_id', 'document_type')
    def _compute_preview_url(self):
        for wizard in self:
            if wizard.sale_order_id and wizard.document_type:
                if wizard.document_type == 'contract':
                    report_name = 'lolirine_contract.report_contract_document'
                else:
                    report_name = 'lolirine_contract.report_lolirine_quotation_document'
                wizard.preview_url = f'/report/pdf/{report_name}/{wizard.sale_order_id.id}'
            else:
                wizard.preview_url = False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        active_id = self.env.context.get('active_id')
        document_type = self.env.context.get('default_document_type', 'contract')
        
        if active_id:
            order = self.env['sale.order'].browse(active_id)
            res['sale_order_id'] = order.id
            res['document_type'] = document_type
            res['email_to'] = order.partner_id.email or ''
            
            if document_type == 'contract':
                res['email_subject'] = f'Envoi de votre contrat de garde-meubles {order.name}'
                res['email_body'] = self._get_contract_email_body(order)
            else:
                res['email_subject'] = f'Envoi de votre devis garde-meubles {order.name}'
                res['email_body'] = self._get_quotation_email_body(order)
        
        return res

    def _get_contract_email_body(self, order):
        return f"""
        <p>Bonjour,</p>
        <p>Veuillez trouver en pièce jointe votre contrat de garde-meubles relatif à la location de votre box au sein de notre site Lolirine.</p>
        <p>Ce document reprend l'ensemble des conditions applicables à votre location (références du contrat, caractéristiques de la box, modalités financières, durée, conditions d'accès et de résiliation, etc.). Nous vous invitons à en prendre connaissance attentivement et à nous le retourner dûment signé, selon les modalités indiquées dans le contrat ou dans le message de signature électronique.</p>
        <p>Pour rappel, votre contrat ne sera pleinement effectif qu'après réception de la version signée et, le cas échéant, du paiement des premiers frais mentionnés.</p>
        <p>Pour toute question concernant le contenu du contrat, vos dates d'entrée/sortie, l'accès à votre box ou toute autre information pratique, vous pouvez nous contacter à l'adresse suivante : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a> ou par téléphone au 0497/44 41 46.</p>
        <p>Nous vous remercions de votre confiance et restons à votre disposition.</p>
        <p>Cordialement,</p>
        <p><strong>Lolirine Garde-Meubles</strong><br/>
        Tél. : 0497/44 41 46<br/>
        Email : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a></p>
        """

    def _get_quotation_email_body(self, order):
        return f"""
        <p>Bonjour,</p>
        <p>Veuillez trouver en pièce jointe votre devis pour la location d'un box de garde-meubles au sein de notre site Lolirine.</p>
        <p>Ce devis détaille les conditions de location proposées. N'hésitez pas à nous contacter pour toute question ou pour confirmer votre réservation.</p>
        <p>Pour toute information complémentaire, vous pouvez nous joindre à l'adresse suivante : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a> ou par téléphone au 0497/44 41 46.</p>
        <p>Nous vous remercions de votre intérêt et restons à votre disposition.</p>
        <p>Cordialement,</p>
        <p><strong>Lolirine Garde-Meubles</strong><br/>
        Tél. : 0497/44 41 46<br/>
        Email : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a></p>
        """

    def action_preview(self):
        """Ouvrir l'aperçu du document dans un nouvel onglet"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.preview_url,
            'target': 'new',
        }

    def action_send(self):
        """Envoyer le document par email"""
        self.ensure_one()
        
        if not self.email_to:
            raise UserError(_("Veuillez renseigner l'adresse email du destinataire."))
        
        # Générer le PDF
        if self.document_type == 'contract':
            report = self.env.ref('lolirine_contract.action_report_contract')
            filename = f'Contrat_{self.sale_order_id.name.replace("/", "_")}.pdf'
        else:
            report = self.env.ref('lolirine_contract.action_report_quotation')
            filename = f'Devis_{self.sale_order_id.name.replace("/", "_")}.pdf'
        
        # CORRECTION: Utiliser _unused au lieu de _ pour ne pas écraser la fonction de traduction
        pdf_content, _unused = report._render_qweb_pdf(report.report_name, [self.sale_order_id.id])
        
        # Créer la pièce jointe
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'mimetype': 'application/pdf',
        })
        
        # Créer et envoyer l'email
        mail_values = {
            'subject': self.email_subject,
            'body_html': self.email_body,
            'email_to': self.email_to,
            'email_from': self.env.company.email or self.env.user.email,
            'attachment_ids': [(4, attachment.id)],
            'model': 'sale.order',
            'res_id': self.sale_order_id.id,
        }
        
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        
        # Poster un message dans le chatter
        self.sale_order_id.message_post(
            body=f"{'Contrat' if self.document_type == 'contract' else 'Devis'} envoyé par email à {self.email_to}",
            attachment_ids=[attachment.id],
            message_type='notification',
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Succès'),
                'message': _('Le document a été envoyé avec succès à %s') % self.email_to,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_and_close(self):
        """Envoyer et fermer le wizard"""
        self.action_send()
        return {'type': 'ir.actions.act_window_close'}
