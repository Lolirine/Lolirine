# -*- coding: utf-8 -*-

import base64
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class InvoiceReminder(models.Model):
    """Suivi des relances pour factures impayées"""
    _name = 'lolirine.invoice.reminder'
    _description = 'Relance facture'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Référence',
        compute='_compute_name',
        store=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        ondelete='cascade',
        domain=[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')],
        tracking=True
    )
    
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string='Client',
        store=True
    )
    
    reminder_type = fields.Selection([
        ('reminder_1', '1er Rappel'),
        ('reminder_2', '2ème Rappel'),
        ('reminder_3', '3ème Rappel'),
        ('formal_notice', 'Mise en demeure'),
        ('lawyer', 'Transmission avocat'),
    ], string='Type de relance', required=True, default='reminder_1', tracking=True)
    
    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    
    send_date = fields.Datetime(
        string='Date envoi',
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyée'),
        ('paid', 'Payée'),
        ('cancelled', 'Annulée'),
    ], string='État', default='draft', tracking=True)
    
    amount_due = fields.Monetary(
        related='invoice_id.amount_residual',
        string='Montant dû',
        store=True
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id'
    )
    
    days_overdue = fields.Integer(
        string='Jours de retard',
        compute='_compute_days_overdue',
        store=True
    )
    
    days_overdue_badge = fields.Char(
        string='Retard',
        compute='_compute_days_overdue_badge'
    )
    
    penalty_amount = fields.Monetary(
        string='Pénalités de retard',
        compute='_compute_penalty_amount',
        store=True,
        help='Pénalités calculées selon le taux légal belge'
    )
    
    total_due = fields.Monetary(
        string='Total dû',
        compute='_compute_penalty_amount',
        store=True,
        help='Montant dû + pénalités'
    )
    
    notes = fields.Text(string='Notes internes')
    
    email_sent = fields.Boolean(string='Email envoyé', default=False)
    
    auto_generated = fields.Boolean(
        string='Généré automatiquement',
        default=False,
        help='Indique si cette relance a été créée par le système automatique'
    )
    
    company_id = fields.Many2one(
        related='invoice_id.company_id',
        store=True
    )

    # ==================== COMPUTE METHODS ====================

    @api.depends('invoice_id', 'reminder_type', 'date')
    def _compute_name(self):
        type_names = {
            'reminder_1': 'R1',
            'reminder_2': 'R2',
            'reminder_3': 'R3',
            'formal_notice': 'MED',
            'lawyer': 'AVO',
        }
        for rec in self:
            if rec.invoice_id and rec.reminder_type:
                rec.name = f"{type_names.get(rec.reminder_type, 'REL')}/{rec.invoice_id.name}"
            else:
                rec.name = 'Nouvelle relance'

    @api.depends('invoice_id.invoice_date_due')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for rec in self:
            if rec.invoice_id and rec.invoice_id.invoice_date_due:
                delta = today - rec.invoice_id.invoice_date_due
                rec.days_overdue = max(0, delta.days)
            else:
                rec.days_overdue = 0

    @api.depends('days_overdue')
    def _compute_days_overdue_badge(self):
        for rec in self:
            if rec.days_overdue <= 7:
                rec.days_overdue_badge = 'success'
            elif rec.days_overdue <= 21:
                rec.days_overdue_badge = 'warning'
            else:
                rec.days_overdue_badge = 'danger'

    @api.depends('amount_due', 'days_overdue')
    def _compute_penalty_amount(self):
        """Calcul des pénalités selon le taux légal belge"""
        config = self.env['lolirine.invoice.reminder.config'].search([], limit=1)
        annual_rate = config.penalty_rate / 100 if config else 0.105
        
        for rec in self:
            if rec.days_overdue > 0 and rec.amount_due > 0:
                rec.penalty_amount = rec.amount_due * (annual_rate / 365) * rec.days_overdue
                rec.total_due = rec.amount_due + rec.penalty_amount
            else:
                rec.penalty_amount = 0.0
                rec.total_due = rec.amount_due or 0.0

    # ==================== EMAIL BODY GENERATION ====================

    def _get_email_subject(self):
        """Génère le sujet de l'email selon le type de relance"""
        self.ensure_one()
        subjects = {
            'reminder_1': f"Rappel de paiement - Facture {self.invoice_id.name}",
            'reminder_2': f"2ème Rappel - Facture {self.invoice_id.name} impayée",
            'reminder_3': f"URGENT - 3ème Rappel - Facture {self.invoice_id.name}",
            'formal_notice': f"MISE EN DEMEURE - Facture {self.invoice_id.name}",
        }
        return subjects.get(self.reminder_type, f"Relance - Facture {self.invoice_id.name}")

    def _get_email_body_reminder_1(self):
        """Corps de l'email pour le 1er rappel"""
        self.ensure_one()
        return f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p>Sauf erreur ou omission de notre part, nous n'avons pas encore reçu le paiement de la facture mentionnée ci-dessous :</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px;">
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numéro de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'échéance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.invoice_date_due or ''}</td>
        </tr>
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant dû</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.amount_due:.2f} EUR</strong></td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Jours de retard</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.days_overdue} jours</td>
        </tr>
    </table>
    
    <p>Nous vous serions reconnaissants de bien vouloir procéder au règlement de cette facture dans les meilleurs délais.</p>
    
    <p><strong>Modalités de paiement :</strong></p>
    <ul>
        <li>Communication structurée : {self.invoice_id.payment_reference or self.invoice_id.name}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
    </ul>
    
    <p>Si vous avez déjà effectué le paiement, nous vous prions de ne pas tenir compte de ce message.</p>
    
    <p>Pour toute question, n'hésitez pas à nous contacter.</p>
    
    <p>Cordialement,</p>
    
    <p style="margin-top: 20px;">
        <strong>Lolirine Garde-Meubles</strong><br/>
        Tél. : 0497/44 41 46<br/>
        Email : gardemeublelolirine@gmail.com
    </p>
</div>
"""

    def _get_email_body_reminder_2(self):
        """Corps de l'email pour le 2ème rappel"""
        self.ensure_one()
        return f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p><strong>Ceci est notre deuxième rappel concernant votre facture impayée.</strong></p>
    
    <p>Malgré notre précédent rappel, nous constatons que le paiement de la facture ci-dessous n'a toujours pas été effectué :</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px;">
        <tr style="background-color: #fff3cd;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numéro de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'échéance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.invoice_date_due or ''}</td>
        </tr>
        <tr style="background-color: #fff3cd;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant dû</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.amount_due:.2f} EUR</strong></td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Jours de retard</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd; color: #dc3545;"><strong>{self.days_overdue} jours</strong></td>
        </tr>
    </table>
    
    <p>Nous vous prions de régulariser cette situation dans les plus brefs délais afin d'éviter des frais supplémentaires.</p>
    
    <p><strong>Modalités de paiement :</strong></p>
    <ul>
        <li>Communication structurée : {self.invoice_id.payment_reference or self.invoice_id.name}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
    </ul>
    
    <p>En cas de difficulté de paiement, nous vous invitons à nous contacter pour trouver une solution.</p>
    
    <p>Cordialement,</p>
    
    <p style="margin-top: 20px;">
        <strong>Lolirine Garde-Meubles</strong><br/>
        Tél. : 0497/44 41 46<br/>
        Email : gardemeublelolirine@gmail.com
    </p>
</div>
"""

    def _get_email_body_reminder_3(self):
        """Corps de l'email pour le 3ème rappel"""
        self.ensure_one()
        return f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p style="color: #dc3545;"><strong>TROISIÈME ET DERNIER RAPPEL AVANT MISE EN DEMEURE</strong></p>
    
    <p>Malgré nos précédentes relances, votre facture reste impayée :</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px; border: 2px solid #dc3545;">
        <tr style="background-color: #f8d7da;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numéro de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'échéance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.invoice_date_due or ''}</td>
        </tr>
        <tr style="background-color: #f8d7da;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant dû</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong style="color: #dc3545;">{self.amount_due:.2f} EUR</strong></td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Jours de retard</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong style="color: #dc3545;">{self.days_overdue} jours</strong></td>
        </tr>
        <tr style="background-color: #f8d7da;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Pénalités de retard</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.penalty_amount:.2f} EUR</td>
        </tr>
    </table>
    
    <p><strong>Sans paiement de votre part dans les 7 jours, nous serons contraints de vous adresser une mise en demeure formelle, pouvant entraîner :</strong></p>
    <ul>
        <li>L'application de pénalités de retard au taux légal belge (10,5% annuel)</li>
        <li>La suspension de l'accès à votre box</li>
        <li>Le recours à une société de recouvrement</li>
    </ul>
    
    <p><strong>Modalités de paiement :</strong></p>
    <ul>
        <li>Communication structurée : {self.invoice_id.payment_reference or self.invoice_id.name}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
    </ul>
    
    <p>Nous restons disponibles pour discuter d'un échelonnement de paiement si nécessaire.</p>
    
    <p>Cordialement,</p>
    
    <p style="margin-top: 20px;">
        <strong>Lolirine Garde-Meubles</strong><br/>
        Tél. : 0497/44 41 46<br/>
        Email : gardemeublelolirine@gmail.com
    </p>
</div>
"""

    def _get_email_body_formal_notice(self):
        """Corps de l'email pour la mise en demeure"""
        self.ensure_one()
        total = self.amount_due + self.penalty_amount
        return f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p style="text-align: center; font-size: 16px; color: #dc3545; border: 2px solid #dc3545; padding: 10px;">
        <strong>MISE EN DEMEURE</strong>
    </p>
    
    <p>{self.partner_id.name or ''}<br/>
    {self.partner_id.street or ''}<br/>
    {self.partner_id.zip or ''} {self.partner_id.city or ''}</p>
    
    <p>Objet : Mise en demeure de payer - Facture {self.invoice_id.name}</p>
    
    <p>Madame, Monsieur,</p>
    
    <p>Malgré nos nombreuses relances, nous constatons que vous n'avez toujours pas procédé au règlement de la facture suivante :</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 500px; border: 2px solid #dc3545;">
        <tr style="background-color: #f8d7da;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numéro de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'échéance initiale</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.invoice_date_due or ''}</td>
        </tr>
        <tr style="background-color: #f8d7da;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Principal</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.amount_due:.2f} EUR</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Pénalités de retard ({self.days_overdue} jours)</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.penalty_amount:.2f} EUR</td>
        </tr>
        <tr style="background-color: #f8d7da;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>TOTAL À PAYER</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong style="color: #dc3545; font-size: 16px;">{total:.2f} EUR</strong></td>
        </tr>
    </table>
    
    <p><strong>Par la présente, nous vous mettons en demeure de nous régler la somme totale de {total:.2f} EUR dans un délai de 8 jours à compter de la réception de ce courrier.</strong></p>
    
    <p>À défaut de règlement dans ce délai, nous nous réservons le droit de :</p>
    <ul>
        <li>Suspendre immédiatement l'accès à votre box de stockage</li>
        <li>Transmettre le dossier à notre service contentieux</li>
        <li>Engager une procédure judiciaire de recouvrement</li>
        <li>Faire valoir notre droit de rétention sur les biens stockés conformément aux conditions générales</li>
    </ul>
    
    <p><strong>Modalités de paiement :</strong></p>
    <ul>
        <li>Communication structurée : {self.invoice_id.payment_reference or self.invoice_id.name}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
        <li>Titulaire : Lolirine SPRL</li>
    </ul>
    
    <p>Cette mise en demeure vaut interpellation au sens de l'article 1153 du Code civil et fait courir les intérêts de retard au taux légal.</p>
    
    <p>Nous vous prions d'agréer, Madame, Monsieur, l'expression de nos salutations distinguées.</p>
    
    <p style="margin-top: 30px;">
        <strong>Lolirine SPRL</strong><br/>
        Feron Rodney - Gérant<br/>
        Tél. : 0497/44 41 46<br/>
        Email : gardemeublelolirine@gmail.com
    </p>
    
    <p style="font-size: 11px; color: #666; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px;">
        Ce document constitue une mise en demeure au sens juridique du terme. 
        Une copie de ce courrier est conservée dans nos archives.
    </p>
</div>
"""

    def _get_email_body(self):
        """Retourne le corps de l'email selon le type de relance"""
        self.ensure_one()
        body_methods = {
            'reminder_1': self._get_email_body_reminder_1,
            'reminder_2': self._get_email_body_reminder_2,
            'reminder_3': self._get_email_body_reminder_3,
            'formal_notice': self._get_email_body_formal_notice,
        }
        method = body_methods.get(self.reminder_type)
        if method:
            return method()
        return self._get_email_body_reminder_1()

    # ==================== ACTIONS ====================

    def action_send_reminder(self):
        """Envoyer la relance par email avec la facture en pièce jointe"""
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError("Le client n'a pas d'adresse email configurée.")
        
        if not self.invoice_id:
            raise UserError("Aucune facture associée à cette relance.")
        
        self._send_reminder_email()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Relance envoyée',
                'message': f'Email envoyé à {self.partner_id.email} avec la facture en pièce jointe',
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_reminder_email(self):
        """Méthode interne pour envoyer l'email de relance"""
        self.ensure_one()
        
        if not self.partner_id.email:
            _logger.warning(f"Relance {self.name}: pas d'email pour {self.partner_id.name}")
            return False
        
        # Générer le PDF de la facture
        report = self.env.ref('lolirine_invoice.action_report_invoice_lolirine', raise_if_not_found=False)
        if not report:
            report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        
        attachment_ids = []
        if report:
            try:
                pdf_content, _ = report._render_qweb_pdf(report.id, [self.invoice_id.id])
                
                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.invoice_id.name.replace('/', '_')}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'lolirine.invoice.reminder',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                attachment_ids.append(attachment.id)
            except Exception as e:
                _logger.error(f"Erreur génération PDF pour relance {self.name}: {e}")
        
        # Créer et envoyer l'email
        mail_values = {
            'subject': self._get_email_subject(),
            'body_html': self._get_email_body(),
            'email_from': 'gardemeublelolirine@gmail.com',
            'email_to': self.partner_id.email,
            'model': 'lolirine.invoice.reminder',
            'res_id': self.id,
            'attachment_ids': [(6, 0, attachment_ids)],
            'auto_delete': False,
        }
        
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        
        self.write({
            'state': 'sent',
            'send_date': fields.Datetime.now(),
            'email_sent': True,
        })
        
        self.message_post(
            body=f"✅ Relance envoyée automatiquement à {self.partner_id.email}",
            message_type='notification'
        )
        
        _logger.info(f"Relance {self.name} envoyée à {self.partner_id.email}")
        return True

    def action_open_composer(self):
        """Ouvrir le compositeur d'email pour prévisualiser avant envoi"""
        self.ensure_one()
        
        # Générer le PDF de la facture
        attachment_ids = []
        if self.invoice_id:
            report = self.env.ref('lolirine_invoice.action_report_invoice_lolirine', raise_if_not_found=False)
            if not report:
                report = self.env.ref('account.account_invoices', raise_if_not_found=False)
            
            if report:
                pdf_content, _ = report._render_qweb_pdf(report.id, [self.invoice_id.id])
                
                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.invoice_id.name.replace('/', '_')}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'lolirine.invoice.reminder',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                attachment_ids = [attachment.id]
        
        ctx = {
            'default_model': 'lolirine.invoice.reminder',
            'default_res_ids': self.ids,
            'default_composition_mode': 'comment',
            'default_attachment_ids': [(6, 0, attachment_ids)],
            'default_subject': self._get_email_subject(),
            'default_body': self._get_email_body(),
            'force_email': True,
        }
        
        return {
            'name': 'Envoyer la relance',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }

    def action_mark_paid(self):
        """Marquer comme payée"""
        self.write({'state': 'paid'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Relance clôturée',
                'message': 'La relance a été marquée comme payée.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Annuler la relance"""
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.write({
            'state': 'draft',
            'send_date': False,
            'email_sent': False,
        })

    def action_view_invoice(self):
        """Voir la facture associée"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_create_next_reminder(self):
        """Créer la relance suivante"""
        self.ensure_one()
        
        next_type_map = {
            'reminder_1': 'reminder_2',
            'reminder_2': 'reminder_3',
            'reminder_3': 'formal_notice',
            'formal_notice': 'lawyer',
        }
        
        next_type = next_type_map.get(self.reminder_type)
        if not next_type:
            raise UserError("Aucune relance suivante disponible après ce niveau.")
        
        # Vérifier si une relance de ce type existe déjà
        existing = self.search([
            ('invoice_id', '=', self.invoice_id.id),
            ('reminder_type', '=', next_type),
            ('state', '!=', 'cancelled'),
        ], limit=1)
        
        if existing:
            raise UserError(f"Une relance de type '{dict(self._fields['reminder_type'].selection).get(next_type)}' existe déjà pour cette facture.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle relance',
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_invoice_id': self.invoice_id.id,
                'default_reminder_type': next_type,
            },
        }

    # ==================== AUTO-RELANCE CRON ====================

    @api.model
    def _cron_auto_reminder(self):
        """Cron pour générer et envoyer automatiquement les relances"""
        config = self.env['lolirine.invoice.reminder.config'].search([('auto_reminder', '=', True)], limit=1)
        
        if not config:
            _logger.info("Auto-relance désactivée - pas de configuration active")
            return
        
        _logger.info("=== Début du traitement auto-relance ===")
        
        today = fields.Date.today()
        
        # Récupérer toutes les factures clients impayées
        overdue_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('partner_id.email', '!=', False),  # Seulement si email disponible
        ])
        
        _logger.info(f"Factures impayées trouvées: {len(overdue_invoices)}")
        
        reminders_created = 0
        reminders_sent = 0
        
        for invoice in overdue_invoices:
            days_overdue = (today - invoice.invoice_date_due).days
            
            # Déterminer le type de relance approprié
            reminder_type = self._get_reminder_type_for_days(days_overdue, config)
            
            if not reminder_type:
                continue
            
            # Vérifier si une relance de ce type existe déjà
            existing = self.search([
                ('invoice_id', '=', invoice.id),
                ('reminder_type', '=', reminder_type),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            
            if existing:
                continue
            
            # Vérifier que la relance précédente a été envoyée (sauf pour reminder_1)
            if reminder_type != 'reminder_1':
                prev_type = self._get_previous_reminder_type(reminder_type)
                prev_reminder = self.search([
                    ('invoice_id', '=', invoice.id),
                    ('reminder_type', '=', prev_type),
                    ('state', '=', 'sent'),
                ], limit=1)
                
                if not prev_reminder:
                    continue
            
            # Créer la relance
            try:
                reminder = self.create({
                    'invoice_id': invoice.id,
                    'reminder_type': reminder_type,
                    'auto_generated': True,
                })
                reminders_created += 1
                _logger.info(f"Relance créée: {reminder.name} pour {invoice.partner_id.name}")
                
                # Envoyer automatiquement
                if reminder._send_reminder_email():
                    reminders_sent += 1
                    
            except Exception as e:
                _logger.error(f"Erreur création relance pour facture {invoice.name}: {e}")
                continue
        
        _logger.info(f"=== Fin auto-relance: {reminders_created} créées, {reminders_sent} envoyées ===")
        
        return {
            'created': reminders_created,
            'sent': reminders_sent,
        }

    def _get_reminder_type_for_days(self, days_overdue, config):
        """Détermine le type de relance selon les jours de retard"""
        if days_overdue >= config.formal_notice_days:
            return 'formal_notice'
        elif days_overdue >= config.reminder_3_days:
            return 'reminder_3'
        elif days_overdue >= config.reminder_2_days:
            return 'reminder_2'
        elif days_overdue >= config.reminder_1_days:
            return 'reminder_1'
        return None

    def _get_previous_reminder_type(self, reminder_type):
        """Retourne le type de relance précédent"""
        prev_map = {
            'reminder_2': 'reminder_1',
            'reminder_3': 'reminder_2',
            'formal_notice': 'reminder_3',
            'lawyer': 'formal_notice',
        }
        return prev_map.get(reminder_type)

    # ==================== MARQUER PAYÉ AUTOMATIQUEMENT ====================

    @api.model
    def _cron_check_paid_invoices(self):
        """Cron pour marquer les relances comme payées si la facture est payée"""
        paid_reminders = self.search([
            ('state', 'in', ['draft', 'sent']),
            ('invoice_id.payment_state', '=', 'paid'),
        ])
        
        for reminder in paid_reminders:
            reminder.write({'state': 'paid'})
            reminder.message_post(
                body="✅ Facture payée - Relance clôturée automatiquement",
                message_type='notification'
            )
        
        if paid_reminders:
            _logger.info(f"{len(paid_reminders)} relances marquées comme payées")


class InvoiceReminderConfig(models.Model):
    """Configuration des délais de relance"""
    _name = 'lolirine.invoice.reminder.config'
    _description = 'Configuration relances'

    name = fields.Char(string='Nom', default='Configuration par défaut')
    
    reminder_1_days = fields.Integer(
        string='1er rappel après',
        default=7,
        help='Nombre de jours après échéance pour le 1er rappel'
    )
    reminder_2_days = fields.Integer(
        string='2ème rappel après',
        default=14,
        help='Nombre de jours après échéance pour le 2ème rappel'
    )
    reminder_3_days = fields.Integer(
        string='3ème rappel après',
        default=21,
        help='Nombre de jours après échéance pour le 3ème rappel'
    )
    formal_notice_days = fields.Integer(
        string='Mise en demeure après',
        default=30,
        help='Nombre de jours après échéance pour la mise en demeure'
    )
    
    penalty_rate = fields.Float(
        string='Taux de pénalité annuel (%)',
        default=10.5,
        help='Taux légal belge pour les pénalités de retard'
    )
    
    auto_reminder = fields.Boolean(
        string='Relances automatiques',
        default=False,
        help='Activer la génération et l\'envoi automatique des relances'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company
    )
    
    def action_test_auto_reminder(self):
        """Bouton pour tester l'auto-relance manuellement"""
        self.ensure_one()
        result = self.env['lolirine.invoice.reminder']._cron_auto_reminder()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test auto-relance terminé',
                'message': f"Relances créées: {result.get('created', 0)}, envoyées: {result.get('sent', 0)}",
                'type': 'success',
                'sticky': True,
            }
        }
        
