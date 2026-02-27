# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging
import base64
_logger = logging.getLogger(__name__)
class InvoiceReminder(models.Model):
    """Suivi des relances pour factures impayees"""
    _name = 'lolirine.invoice.reminder'
    _description = 'Relance facture'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']
    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        ondelete='cascade',
        domain=[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')]
    )
    
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string='Client',
        store=True
    )
    
    reminder_type = fields.Selection([
        ('reminder_1', '1er Rappel'),
        ('reminder_2', '2eme Rappel'),
        ('reminder_3', '3eme Rappel'),
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
        ('sent', 'Envoyee'),
        ('paid', 'Payee'),
        ('cancelled', 'Annulee'),
    ], string='Etat', default='draft', tracking=True)
    
    amount_due = fields.Monetary(
        related='invoice_id.amount_residual',
        string='Montant du'
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id'
    )
    
    days_overdue = fields.Integer(
        string='Jours de retard',
        compute='_compute_days_overdue'
    )
    
    penalty_amount = fields.Monetary(
        string='Penalites de retard',
        compute='_compute_penalty_amount',
        help='Penalites calculees selon le taux legal belge'
    )
    
    notes = fields.Text(string='Notes internes')
    
    email_sent = fields.Boolean(string='Email envoye', default=False)
    
    fee_added = fields.Boolean(
        string='Frais ajoutés à la facture',
        default=False,
        help='Indique si les frais de relance ont été ajoutés (facture séparée)'
    )
    
    fee_invoice_id = fields.Many2one(
        'account.move',
        string='Facture de frais',
        help='Facture séparée contenant les frais de relance'
    )
    
    company_id = fields.Many2one(
        related='invoice_id.company_id',
        store=True
    )
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
            if rec.invoice_id.invoice_date_due:
                delta = today - rec.invoice_id.invoice_date_due
                rec.days_overdue = max(0, delta.days)
            else:
                rec.days_overdue = 0
    @api.depends('invoice_id.amount_residual', 'days_overdue')
    def _compute_penalty_amount(self):
        """Calcul des penalites selon le taux legal belge (10.5% annuel pour 2024)"""
        annual_rate = 0.105
        for rec in self:
            if rec.days_overdue > 0 and rec.invoice_id.amount_residual > 0:
                rec.penalty_amount = rec.invoice_id.amount_residual * (annual_rate / 365) * rec.days_overdue
            else:
                rec.penalty_amount = 0.0
    # ==================== AJOUT FRAIS - FACTURE SÉPARÉE ====================
    def _add_fee_to_invoice(self):
        """Créer une facture SÉPARÉE pour les frais de relance.
        
        Ne modifie JAMAIS la facture originale (évite les problèmes de
        draft/post et de total attendu).
        
        Frais appliqués :
        - R2 : 20€ frais de rappel
        - R3 : 20€ frais de rappel (si pas déjà ajouté par R2)
        - MED : 20€ rappel (si pas déjà) + 50€ mise en demeure
        """
        self.ensure_one()
        
        if self.fee_added:
            return
        
        inv = self.invoice_id
        lines_to_add = []
        
        if self.reminder_type in ('reminder_2', 'reminder_3'):
            # Vérifier si frais de rappel déjà ajoutés par un R2 ou R3 précédent
            existing_fee = self.search([
                ('invoice_id', '=', inv.id),
                ('reminder_type', 'in', ['reminder_2', 'reminder_3']),
                ('fee_added', '=', True),
                ('id', '!=', self.id),
            ], limit=1)
            if not existing_fee:
                lines_to_add.append({
                    'label': 'Frais de rappel',
                    'amount': 20.00,
                })
                
        elif self.reminder_type == 'formal_notice':
            # Frais de rappel (si pas déjà ajoutés)
            existing_rappel = self.search([
                ('invoice_id', '=', inv.id),
                ('reminder_type', 'in', ['reminder_2', 'reminder_3', 'formal_notice']),
                ('fee_added', '=', True),
                ('id', '!=', self.id),
            ], limit=1)
            if not existing_rappel:
                lines_to_add.append({
                    'label': 'Frais de rappel',
                    'amount': 20.00,
                })
            # Frais de mise en demeure (toujours)
            lines_to_add.append({
                'label': 'Frais de mise en demeure',
                'amount': 50.00,
            })
        
        if not lines_to_add:
            self.fee_added = True
            return
        
        try:
            # Produit "Frais administratifs de gestion d'impayé"
            product = self.env['product.product'].browse(8859)
            if not product.exists():
                product = self.env['product.product'].search([
                    ('name', 'ilike', 'Frais administratifs')
                ], limit=1)
            
            # Créer une facture SÉPARÉE pour les frais
            fee_invoice_lines = []
            for line_data in lines_to_add:
                line_vals = {
                    'name': f"{line_data['label']} - Facture {inv.name} impayée",
                    'quantity': 1,
                    'price_unit': line_data['amount'],
                    'tax_ids': [(5, 0, 0)],  # Pas de TVA sur les frais de relance
                }
                if product:
                    line_vals['product_id'] = product.id
                fee_invoice_lines.append((0, 0, line_vals))
            
            fee_invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': inv.partner_id.id,
                'invoice_date': fields.Date.today(),
                'ref': f'Frais de relance - {inv.name}',
                'invoice_line_ids': fee_invoice_lines,
            })
            fee_invoice.action_post()
            
            self.write({
                'fee_added': True,
                'fee_invoice_id': fee_invoice.id,
            })
            
            total_fees = sum(l['amount'] for l in lines_to_add)
            detail = ' + '.join([f"{l['label']} ({l['amount']:.2f}€)" for l in lines_to_add])
            inv.message_post(
                body=f"💰 {detail} — facture de frais {fee_invoice.name} créée automatiquement suite à la relance {self.name}",
                message_type='notification'
            )
            
            _logger.info(f"Facture de frais {fee_invoice.name} ({total_fees}€) créée pour {inv.name} - relance {self.name}")
            
        except Exception as e:
            _logger.error(f"Erreur création facture de frais pour {inv.name}: {e}")
            inv.message_post(
                body=f"⚠️ Impossible de créer la facture de frais automatiquement : {e}",
                message_type='notification'
            )
    # ==================== GENERATION PDF FACTURE ====================
    def _generate_invoice_pdf(self):
        """Générer le PDF de la facture et retourner la liste d'IDs d'attachment"""
        attachment_ids = []
        inv = self.invoice_id
        
        try:
            report = self.env.ref('lolirine_invoice.action_report_invoice_lolirine', raise_if_not_found=False)
            if not report:
                report = self.env.ref('account.account_invoices', raise_if_not_found=False)
            
            if report:
                pdf_content, _unused = report._render_qweb_pdf(report.id, [inv.id])
                attachment = self.env['ir.attachment'].create({
                    'name': f"Facture_{inv.name.replace('/', '_')}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'lolirine.invoice.reminder',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                attachment_ids.append(attachment.id)
                _logger.info(f"PDF facture {inv.name} généré pour relance {self.name}")
            else:
                _logger.warning(f"Aucun rapport de facture trouvé pour {inv.name}")
                
        except Exception as e:
            _logger.warning(f"Erreur génération PDF pour {inv.name}: {e}")
        
        return attachment_ids
    # ==================== ENVOI EMAIL ====================
    def action_send_reminder(self):
        """Envoyer la relance par email avec PDF facture en PJ"""
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_("Le client n'a pas d'adresse email configurée."))
        
        # 1. Créer une facture séparée pour les frais si R2, R3 ou MED
        if self.reminder_type in ('reminder_2', 'reminder_3', 'formal_notice'):
            self._add_fee_to_invoice()
        
        # 2. Construire l'email
        subject, body_html = self._build_reminder_email()
        
        # 3. Générer le PDF de la facture originale
        attachment_ids = self._generate_invoice_pdf()
        
        # 4. Créer et envoyer l'email via le serveur Odoo
        mail_vals = {
            'subject': subject,
            'body_html': body_html,
            'email_from': 'Srl Lolirine <gardemeublelolirine@gmail.com>',
            'email_to': self.partner_id.email,
            'model': 'lolirine.invoice.reminder',
            'res_id': self.id,
        }
        if attachment_ids:
            mail_vals['attachment_ids'] = [(6, 0, attachment_ids)]
        
        mail = self.env['mail.mail'].sudo().create(mail_vals)
        mail.send()
        
        self.write({
            'state': 'sent',
            'send_date': fields.Datetime.now(),
            'email_sent': True,
        })
        
        # Log dans le chatter de la facture
        pj_text = " (avec facture PDF en PJ)" if attachment_ids else ""
        self.invoice_id.message_post(
            body=f"📧 Relance {self._get_type_label()} envoyée par email à {self.partner_id.email}{pj_text}",
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Relance envoyée'),
                'message': _('Email envoyé à %s') % self.partner_id.email,
                'type': 'success',
                'sticky': False,
            }
        }
    def _get_type_label(self):
        labels = {
            'reminder_1': '1er Rappel',
            'reminder_2': '2ème Rappel',
            'reminder_3': '3ème Rappel',
            'formal_notice': 'Mise en demeure',
            'lawyer': 'Transmission avocat',
        }
        return labels.get(self.reminder_type, 'Relance')
    def _build_reminder_email(self):
        """Construit le sujet et le corps HTML de l'email selon le type"""
        self.ensure_one()
        
        inv = self.invoice_id
        partner = self.partner_id
        
        # Calculer le montant total dû (facture originale + factures de frais)
        total_due = inv.amount_residual
        # Chercher les factures de frais liées non payées
        fee_invoices = self.env['account.move'].search([
            ('ref', 'ilike', inv.name),
            ('partner_id', '=', partner.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ])
        for fee_inv in fee_invoices:
            if fee_inv.id != inv.id:
                total_due += fee_inv.amount_residual
        
        amount_due = f"{total_due:.2f}"
        due_date = inv.invoice_date_due.strftime('%d/%m/%Y') if inv.invoice_date_due else ''
        inv_name = inv.name or ''
        payment_ref = inv.payment_reference or 'Voir facture'
        days = self.days_overdue
        penalty = f"{self.penalty_amount:.2f}"
        
        if self.reminder_type == 'reminder_1':
            return self._build_email_reminder_1(partner, inv_name, due_date, amount_due, days, payment_ref)
        elif self.reminder_type == 'reminder_2':
            return self._build_email_reminder_2(partner, inv_name, due_date, amount_due, days, payment_ref)
        elif self.reminder_type == 'reminder_3':
            return self._build_email_reminder_3(partner, inv_name, due_date, amount_due, days, penalty, payment_ref)
        elif self.reminder_type == 'formal_notice':
            return self._build_email_formal_notice(partner, inv_name, due_date, amount_due, days, penalty, payment_ref)
        else:
            return (f"Relance - Facture {inv_name}", "<p>Relance</p>")
    # ==================== TEMPLATES EMAIL HTML ====================
    def _email_style(self):
        return 'font-family: Arial, sans-serif; font-size: 13px; color: #333;'
    def _email_table_row(self, label, value, bold=False, color=None):
        style_val = ''
        if bold:
            style_val = ' font-weight: bold;'
        if color:
            style_val += f' color: {color};'
        return f"""
        <tr>
            <td style="padding: 8px 12px; border: 1px solid #ddd; background-color: #f5f5f5; font-weight: bold; width: 180px;">{label}</td>
            <td style="padding: 8px 12px; border: 1px solid #ddd;{style_val}">{value}</td>
        </tr>"""
    def _email_payment_block(self, payment_ref):
        return f"""
    <p><strong>Modalités de paiement :</strong></p>
    <ul>
        <li>Communication structurée : {payment_ref}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
        <li>Titulaire : Lolirine SRL</li>
    </ul>"""
    def _email_signature(self):
        return """
    <p style="margin-top: 25px;">
        <strong>Lolirine Garde-Meubles</strong><br/>
        Feron Rodney<br/>
        Tél. : 0497/44 41 46<br/>
        Email : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a>
    </p>"""
    # -------------------- 1er RAPPEL --------------------
    def _build_email_reminder_1(self, partner, inv_name, due_date, amount_due, days, payment_ref):
        subject = f"Rappel de paiement - Facture {inv_name} impayée"
        
        body = f"""
<div style="{self._email_style()}">
    <p>Bonjour {partner.name},</p>
    
    <p>Sauf erreur ou omission de notre part, nous n'avons pas encore reçu le paiement de la facture mentionnée ci-dessous :</p>
    
    <table style="margin: 15px 0; border-collapse: collapse; width: 100%; max-width: 450px;">
        {self._email_table_row("Numéro de facture", inv_name)}
        {self._email_table_row("Date d'échéance", due_date)}
        {self._email_table_row("Montant dû", f"{amount_due} EUR", bold=True)}
        {self._email_table_row("Jours de retard", f"{days} jours")}
    </table>
    
    <p>Vous trouverez en pièce jointe une copie de la facture concernée.</p>
    
    <p>Nous vous serions reconnaissants de bien vouloir procéder au règlement de cette facture dans les meilleurs délais.</p>
    
    {self._email_payment_block(payment_ref)}
    
    <p>Si vous avez déjà effectué le paiement, nous vous prions de ne pas tenir compte de ce message.</p>
    
    <p>Pour toute question, n'hésitez pas à nous contacter.</p>
    
    <p>Cordialement,</p>
    {self._email_signature()}
</div>"""
        return subject, body
    # -------------------- 2ème RAPPEL --------------------
    def _build_email_reminder_2(self, partner, inv_name, due_date, amount_due, days, payment_ref):
        subject = f"2ème Rappel - Facture {inv_name} impayée"
        
        body = f"""
<div style="{self._email_style()}">
    <p>Bonjour {partner.name},</p>
    
    <p><strong>Ceci est notre deuxième rappel concernant votre facture impayée.</strong></p>
    
    <p>Malgré notre précédent rappel, nous constatons que le paiement de la facture ci-dessous n'a toujours pas été effectué :</p>
    
    <table style="margin: 15px 0; border-collapse: collapse; width: 100%; max-width: 450px;">
        {self._email_table_row("Numéro de facture", inv_name)}
        {self._email_table_row("Date d'échéance", due_date)}
        {self._email_table_row("Jours de retard", f"{days} jours", color="#dc3545")}
        {self._email_table_row("MONTANT TOTAL DÛ", f"{amount_due} EUR", bold=True, color="#dc3545")}
    </table>
    
    <p>Conformément à nos conditions générales, des <strong>frais de rappel de 20,00 EUR</strong> ont été facturés séparément.</p>
    
    <p>Vous trouverez en pièce jointe la facture originale.</p>
    
    <p>Nous vous prions de régulariser cette situation dans les plus brefs délais afin d'éviter des frais supplémentaires.</p>
    
    {self._email_payment_block(payment_ref)}
    
    <p>En cas de difficulté de paiement, nous vous invitons à nous contacter pour trouver une solution.</p>
    
    <p>Cordialement,</p>
    {self._email_signature()}
</div>"""
        return subject, body
    # -------------------- 3ème RAPPEL --------------------
    def _build_email_reminder_3(self, partner, inv_name, due_date, amount_due, days, penalty, payment_ref):
        subject = f"URGENT - 3ème Rappel - Facture {inv_name} impayée"
        
        body = f"""
<div style="{self._email_style()}">
    <p>Bonjour {partner.name},</p>
    
    <p style="color: #dc3545; font-weight: bold; font-size: 14px;">TROISIÈME ET DERNIER RAPPEL AVANT MISE EN DEMEURE</p>
    
    <p>Malgré nos précédentes relances, votre facture reste impayée :</p>
    
    <table style="margin: 15px 0; border-collapse: collapse; width: 100%; max-width: 450px; border: 2px solid #dc3545;">
        {self._email_table_row("Numéro de facture", inv_name)}
        {self._email_table_row("Date d'échéance", due_date)}
        {self._email_table_row("Jours de retard", f"{days} jours", color="#dc3545")}
        {self._email_table_row("MONTANT TOTAL DÛ", f"{amount_due} EUR", bold=True, color="#dc3545")}
    </table>
    
    <p>Le montant ci-dessus inclut les frais de rappel facturés séparément.</p>
    
    <p><strong>Sans paiement de votre part dans les 7 jours</strong>, nous serons contraints de vous adresser une <strong>mise en demeure formelle</strong>, pouvant entraîner :</p>
    
    <ul>
        <li>L'application de pénalités de retard au taux légal belge (10,5% annuel)</li>
        <li>La suspension de l'accès à votre box</li>
        <li>Le recours à une société de recouvrement</li>
    </ul>
    
    {self._email_payment_block(payment_ref)}
    
    <p>Nous restons disponibles pour discuter d'un échelonnement de paiement si nécessaire.</p>
    
    <p>Cordialement,</p>
    {self._email_signature()}
</div>"""
        return subject, body
    # -------------------- MISE EN DEMEURE --------------------
    def _build_email_formal_notice(self, partner, inv_name, due_date, amount_due, days, penalty, payment_ref):
        subject = f"MISE EN DEMEURE - Facture {inv_name}"
        
        partner_street = partner.street or ''
        partner_zip = partner.zip or ''
        partner_city = partner.city or ''
        
        body = f"""
<div style="{self._email_style()}">
    
    <div style="background-color: #dc3545; color: white; text-align: center; padding: 15px; font-size: 18px; font-weight: bold; margin-bottom: 20px;">
        MISE EN DEMEURE
    </div>
    
    <p>
        {partner.name}<br/>
        {partner_street}<br/>
        {partner_zip} {partner_city}
    </p>
    
    <p><strong>Objet : Mise en demeure de payer - Facture {inv_name}</strong></p>
    
    <p>Madame, Monsieur,</p>
    
    <p>Malgré nos nombreuses relances, nous constatons que vous n'avez toujours pas procédé au règlement de la/des facture(s) relative(s) à la location de votre box au sein de notre site Lolirine.</p>
    
    <table style="margin: 15px 0; border-collapse: collapse; width: 100%; max-width: 500px; border: 2px solid #dc3545;">
        {self._email_table_row("Numéro de facture", inv_name)}
        {self._email_table_row("Date d'échéance initiale", str(due_date))}
        {self._email_table_row("MONTANT TOTAL DÛ", f"{amount_due} EUR", bold=True, color="#dc3545")}
    </table>
    
    <p>Le montant ci-dessus inclut les frais de rappel et de mise en demeure facturés séparément.</p>
    
    <p>Par la présente, nous vous mettons en demeure de nous régler la somme totale de <strong>{amount_due} EUR</strong> dans un délai de <strong>8 jours</strong> à compter de la réception de ce courrier.</p>
    
    <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 15px 0;">
        <p style="font-weight: bold; margin-top: 0;">À DÉFAUT DE PAIEMENT :</p>
        <ul style="margin-bottom: 0;">
            <li>Votre <strong>contrat de garde-meubles sera résilié</strong> avec effet immédiat</li>
            <li>Les biens stockés feront l'objet d'une <strong>rétention</strong> jusqu'au paiement intégral</li>
            <li>Le dossier sera transmis à notre <strong>service contentieux</strong> pour recouvrement judiciaire</li>
        </ul>
    </div>
    
    {self._email_payment_block(payment_ref)}
    
    <p><em>Cette mise en demeure vaut interpellation au sens de l'article 1153 du Code civil et fait courir les intérêts de retard au taux légal.</em></p>
    
    <p>Nous vous prions d'agréer, Madame, Monsieur, l'expression de nos salutations distinguées.</p>
    
    <p style="margin-top: 25px;">
        <strong>Lolirine SRL</strong><br/>
        Feron Rodney - Gérant<br/>
        Tél. : 0497/44 41 46<br/>
        Email : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a>
    </p>
    
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;"/>
    <p style="font-size: 11px; color: #999;">
        Ce document constitue une mise en demeure au sens juridique du terme. Une copie de ce courrier est conservée dans nos archives.
    </p>
</div>"""
        return subject, body
    # ==================== ACTIONS ====================
    def action_mark_paid(self):
        self.write({'state': 'paid'})
    def action_cancel(self):
        self.write({'state': 'cancelled'})
    def action_reset_draft(self):
        self.write({'state': 'draft'})
    # ==================== AUTO-RELANCE CRON ====================
    @api.model
    def _cron_auto_reminder(self):
        """Cron pour generer et envoyer automatiquement les relances"""
        config = self.env['lolirine.invoice.reminder.config'].search(
            [('auto_reminder', '=', True)], limit=1
        )
        
        if not config:
            _logger.info("Auto-relance desactivee - pas de configuration active")
            return {'created': 0, 'sent': 0}
        
        _logger.info("=== Debut du traitement auto-relance ===")
        
        today = fields.Date.today()
        
        overdue_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('partner_id.email', '!=', False),
        ])
        
        _logger.info(f"Factures impayees trouvees: {len(overdue_invoices)}")
        
        reminders_created = 0
        reminders_sent = 0
        
        for invoice in overdue_invoices:
            days_overdue = (today - invoice.invoice_date_due).days
            
            reminder_type = self._get_reminder_type_for_days(days_overdue, config)
            
            if not reminder_type:
                continue
            
            existing = self.search([
                ('invoice_id', '=', invoice.id),
                ('reminder_type', '=', reminder_type),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            
            if existing:
                continue
            
            try:
                reminder = self.create({
                    'invoice_id': invoice.id,
                    'reminder_type': reminder_type,
                    'date': today,
                    'notes': f'Relance automatique - {days_overdue} jours de retard',
                })
                reminders_created += 1
                _logger.info(f"Relance creee: {reminder.name} pour {invoice.partner_id.name}")
                
                try:
                    reminder.action_send_reminder()
                    reminders_sent += 1
                    _logger.info(f"Relance envoyee: {reminder.name}")
                except Exception as e:
                    _logger.warning(f"Erreur envoi relance {reminder.name}: {e}")
                    
            except Exception as e:
                _logger.error(f"Erreur creation relance pour {invoice.name}: {e}")
        
        _logger.info(f"=== Fin auto-relance: {reminders_created} creees, {reminders_sent} envoyees ===")
        return {'created': reminders_created, 'sent': reminders_sent}
    @api.model
    def _get_reminder_type_for_days(self, days_overdue, config):
        if days_overdue >= config.formal_notice_days:
            return 'formal_notice'
        elif days_overdue >= config.reminder_3_days:
            return 'reminder_3'
        elif days_overdue >= config.reminder_2_days:
            return 'reminder_2'
        elif days_overdue >= config.reminder_1_days:
            return 'reminder_1'
        return False
    @api.model
    def _cron_check_paid(self):
        open_reminders = self.search([
            ('state', 'in', ('draft', 'sent')),
        ])
        for reminder in open_reminders:
            if reminder.invoice_id.payment_state in ('paid', 'reversed'):
                reminder.write({'state': 'paid'})
class InvoiceReminderConfig(models.Model):
    """Configuration des delais de relance"""
    _name = 'lolirine.invoice.reminder.config'
    _description = 'Configuration relances'
    name = fields.Char(string='Nom', default='Configuration par defaut')
    
    reminder_1_days = fields.Integer(
        string='1er rappel apres',
        default=7,
        help='Nombre de jours apres echeance pour le 1er rappel'
    )
    reminder_2_days = fields.Integer(
        string='2eme rappel apres',
        default=14,
        help='Nombre de jours apres echeance pour le 2eme rappel'
    )
    reminder_3_days = fields.Integer(
        string='3eme rappel apres',
        default=21,
        help='Nombre de jours apres echeance pour le 3eme rappel'
    )
    formal_notice_days = fields.Integer(
        string='Mise en demeure apres',
        default=30,
        help='Nombre de jours apres echeance pour la mise en demeure'
    )
    
    penalty_rate = fields.Float(
        string='Taux de penalite annuel (%)',
        default=10.5,
        help='Taux legal belge pour les penalites de retard'
    )
    
    fee_reminder = fields.Float(
        string='Frais de rappel (EUR)',
        default=20.0,
        help='Frais appliques a partir du 2eme rappel'
    )
    
    fee_formal_notice = fields.Float(
        string='Frais mise en demeure (EUR)',
        default=50.0,
        help='Frais supplementaires pour la mise en demeure (en plus des frais de rappel)'
    )
    
    auto_reminder = fields.Boolean(
        string='Relances automatiques',
        default=False,
        help='Generer automatiquement les relances selon le calendrier'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company
    )
    
    def action_test_auto_reminder(self):
        result = self.env['lolirine.invoice.reminder']._cron_auto_reminder()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test auto-relance terminé',
                'message': f"Créées: {result.get('created', 0)}, Envoyées: {result.get('sent', 0)}",
                'type': 'success' if result.get('created', 0) > 0 else 'warning',
                'sticky': True,
            }
        }
