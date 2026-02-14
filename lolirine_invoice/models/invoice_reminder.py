# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

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
        annual_rate = 0.105  # Taux legal belge 2024
        for rec in self:
            if rec.days_overdue > 0 and rec.invoice_id.amount_residual > 0:
                rec.penalty_amount = rec.invoice_id.amount_residual * (annual_rate / 365) * rec.days_overdue
            else:
                rec.penalty_amount = 0.0

    # ==================== ENVOI EMAIL ====================

    def action_send_reminder(self):
        """Envoyer la relance par email - construction directe du body HTML"""
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_("Le client n'a pas d'adresse email configurée."))
        
        # Construire l'email selon le type de relance
        subject, body_html = self._build_reminder_email()
        
        # Créer et envoyer l'email
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_from': 'gardemeublelolirine@gmail.com',
            'email_to': self.partner_id.email,
            'model': 'lolirine.invoice.reminder',
            'res_id': self.id,
        })
        mail.send()
        
        self.write({
            'state': 'sent',
            'send_date': fields.Datetime.now(),
            'email_sent': True,
        })
        
        # Log dans le chatter de la facture
        self.invoice_id.message_post(
            body=f"Relance {self._get_type_label()} envoyée par email à {self.partner_id.email}",
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
        """Retourne le libellé du type de relance"""
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
        amount_due = f"{inv.amount_residual:.2f}"
        due_date = inv.invoice_date_due or ''
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

    def _email_style(self):
        """Style CSS commun pour tous les emails"""
        return 'font-family: Arial, sans-serif; font-size: 13px; color: #333;'

    def _email_table_row(self, label, value, bold=False, color=None):
        """Génère une ligne de tableau HTML"""
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
        """Bloc modalités de paiement"""
        return f"""
    <p><strong>Modalités de paiement :</strong></p>
    <ul>
        <li>Communication structurée : {payment_ref}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
        <li>Titulaire : Lolirine SPRL</li>
    </ul>"""

    def _email_signature(self):
        """Signature commune"""
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
    
    <p>Nous vous serions reconnaissants de bien vouloir procéder au règlement de cette facture dans les meilleurs délais.</p>
    
    {self._email_payment_block(payment_ref)}
    
    <p>Si vous avez déjà effectué le paiement, nous vous prions de ne pas tenir compte de ce message.</p>
    
    <p>Pour toute question, n'hésitez pas à nous contacter.</p>
    
    <p>Cordialement,</p>
    {self._email_signature()}
</div>"""
        return subject, body

    # -------------------- 2ème RAPPEL (+ 20€ frais) --------------------

    def _build_email_reminder_2(self, partner, inv_name, due_date, amount_due, days, payment_ref):
        subject = f"2ème Rappel - Facture {inv_name} impayée"
        fee = 20.00
        total = float(amount_due) + fee
        
        body = f"""
<div style="{self._email_style()}">
    <p>Bonjour {partner.name},</p>
    
    <p><strong>Ceci est notre deuxième rappel concernant votre facture impayée.</strong></p>
    
    <p>Malgré notre précédent rappel, nous constatons que le paiement de la facture ci-dessous n'a toujours pas été effectué :</p>
    
    <table style="margin: 15px 0; border-collapse: collapse; width: 100%; max-width: 450px;">
        {self._email_table_row("Numéro de facture", inv_name)}
        {self._email_table_row("Date d'échéance", due_date)}
        {self._email_table_row("Montant dû", f"{amount_due} EUR")}
        {self._email_table_row("Jours de retard", f"{days} jours", color="#dc3545")}
        {self._email_table_row("Frais de rappel", f"{fee:.2f} EUR", color="#dc3545")}
        {self._email_table_row("TOTAL À PAYER", f"{total:.2f} EUR", bold=True, color="#dc3545")}
    </table>
    
    <p>Conformément à nos conditions générales, des frais de rappel de <strong>{fee:.2f} EUR</strong> sont appliqués à partir du deuxième rappel.</p>
    
    <p>Nous vous prions de régulariser cette situation dans les plus brefs délais afin d'éviter des frais supplémentaires.</p>
    
    {self._email_payment_block(payment_ref)}
    
    <p>En cas de difficulté de paiement, nous vous invitons à nous contacter pour trouver une solution.</p>
    
    <p>Cordialement,</p>
    {self._email_signature()}
</div>"""
        return subject, body

    # -------------------- 3ème RAPPEL (+ 20€ frais) --------------------

    def _build_email_reminder_3(self, partner, inv_name, due_date, amount_due, days, penalty, payment_ref):
        subject = f"URGENT - 3ème Rappel - Facture {inv_name} impayée"
        fee = 20.00
        total = float(amount_due) + fee
        
        body = f"""
<div style="{self._email_style()}">
    <p>Bonjour {partner.name},</p>
    
    <p style="color: #dc3545; font-weight: bold; font-size: 14px;">TROISIÈME ET DERNIER RAPPEL AVANT MISE EN DEMEURE</p>
    
    <p>Malgré nos précédentes relances, votre facture reste impayée :</p>
    
    <table style="margin: 15px 0; border-collapse: collapse; width: 100%; max-width: 450px; border: 2px solid #dc3545;">
        {self._email_table_row("Numéro de facture", inv_name)}
        {self._email_table_row("Date d'échéance", due_date)}
        {self._email_table_row("Montant dû", f"{amount_due} EUR")}
        {self._email_table_row("Jours de retard", f"{days} jours", color="#dc3545")}
        {self._email_table_row("Pénalités de retard", f"{penalty} EUR")}
        {self._email_table_row("Frais de rappel", f"{fee:.2f} EUR", color="#dc3545")}
        {self._email_table_row("TOTAL À PAYER", f"{total:.2f} EUR", bold=True, color="#dc3545")}
    </table>
    
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

    # -------------------- MISE EN DEMEURE (20€ rappel + 50€ MED = 70€) --------------------

    def _build_email_formal_notice(self, partner, inv_name, due_date, amount_due, days, penalty, payment_ref):
        subject = f"MISE EN DEMEURE - Facture {inv_name}"
        fee_rappel = 20.00
        fee_med = 50.00
        fee_total = fee_rappel + fee_med
        total = float(amount_due) + fee_total
        
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
        {self._email_table_row("Montant facture", f"{amount_due} EUR")}
        {self._email_table_row("Frais de rappel", f"{fee_rappel:.2f} EUR", color="#dc3545")}
        {self._email_table_row("Frais de mise en demeure", f"{fee_med:.2f} EUR", color="#dc3545")}
        {self._email_table_row("TOTAL DÛ", f"{total:.2f} EUR", bold=True, color="#dc3545")}
    </table>
    
    <p>Par la présente, nous vous mettons en demeure de nous régler la somme totale de <strong>{total:.2f} EUR</strong> dans un délai de <strong>8 jours</strong> à compter de la réception de ce courrier.</p>
    
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
        <strong>Lolirine SPRL</strong><br/>
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

    def action_mark_paid(self):
        """Marquer comme payee"""
        self.write({'state': 'paid'})

    def action_cancel(self):
        """Annuler la relance"""
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Remettre en brouillon"""
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
        
        # Recuperer toutes les factures clients impayees en retard
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
            
            # Determiner le type de relance appropriate
            reminder_type = self._get_reminder_type_for_days(days_overdue, config)
            
            if not reminder_type:
                continue
            
            # Verifier si une relance de ce type existe deja
            existing = self.search([
                ('invoice_id', '=', invoice.id),
                ('reminder_type', '=', reminder_type),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            
            if existing:
                continue
            
            # Creer la relance
            try:
                reminder = self.create({
                    'invoice_id': invoice.id,
                    'reminder_type': reminder_type,
                    'date': today,
                    'notes': f'Relance automatique - {days_overdue} jours de retard',
                })
                reminders_created += 1
                _logger.info(f"Relance creee: {reminder.name} pour {invoice.partner_id.name}")
                
                # Envoyer automatiquement
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
        """Determine le type de relance selon le nombre de jours de retard"""
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
        """Cron pour marquer les relances comme payees si la facture est reglee"""
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
        """Lancer manuellement le processus d'auto-relance pour test"""
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
