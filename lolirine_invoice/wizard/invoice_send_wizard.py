from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
    email = fields.Char(
        string="Email",
        help="Adresse email du destinataire"
    )
    send_method = fields.Selection([
        ('email', 'Email'),
        ('peppol', 'Peppol (facturation electronique)'),
        ('both', 'Email + Peppol'),
    ], string="Methode d'envoi", default='email', required=True)
    
    include_attachment = fields.Boolean(
        string="Joindre le PDF",
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

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.email = self.partner_id.email

    @api.onchange('peppol_available')
    def _onchange_peppol_available(self):
        """Suggérer Peppol si disponible"""
        if self.peppol_available and self.partner_id.auto_send_peppol:
            self.send_method = 'peppol'

    def action_preview(self):
        """Apercu de la facture"""
        self.ensure_one()
        return self.invoice_id.action_preview_invoice()

    def action_send(self):
        """Envoyer la facture selon la methode choisie"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_("Aucune facture selectionnee."))
        
        messages = []
        
        if self.send_method in ('email', 'both'):
            if not self.email:
                raise UserError(_("Veuillez specifier une adresse email."))
            self._send_by_email()
            messages.append(_("Email envoye a %s") % self.email)
        
        if self.send_method in ('peppol', 'both'):
            result = self._send_by_peppol()
            if result:
                messages.append(_("Envoye via Peppol a %s") % self.peppol_endpoint)
        
        # Marquer comme envoyée
        self.invoice_id.write({'is_move_sent': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Facture envoyee'),
                'message': _('La facture %s a ete envoyee avec succes. %s') % (
                    self.invoice_id.name,
                    ' | '.join(messages)
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_by_email(self):
        """Envoyer la facture par email"""
        template = self.env.ref('lolirine_invoice.email_template_invoice', raise_if_not_found=False)
        
        if template:
            template.send_mail(
                self.invoice_id.id,
                force_send=True,
                email_values={'email_to': self.email}
            )
            self.invoice_id.message_post(
                body=_("Facture envoyee par email a %s") % self.email,
                message_type='notification'
            )
        else:
            self.invoice_id.message_post(
                body=_("Facture envoyee par email a %s") % self.email,
                subject=_("Facture %s") % self.invoice_id.name,
                partner_ids=[self.partner_id.id],
            )

    def _send_by_peppol(self):
        """Envoyer la facture via Peppol"""
        if not self.peppol_available:
            raise UserError(_(
                "L'envoi Peppol n'est pas disponible pour ce client. "
                "Veuillez configurer l'EAS et l'endpoint Peppol dans la fiche client "
                "(onglet 'Facturation electronique')."
            ))
        
        # Utiliser la méthode du modèle account.move
        return self.invoice_id._send_invoice_peppol_auto()

    def action_send_and_close(self):
        """Envoyer et fermer le wizard"""
        self.action_send()
        return {'type': 'ir.actions.act_window_close'}
