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
    peppol_endpoint = fields.Char(
        string="Endpoint Peppol",
        related="partner_id.peppol_endpoint",
        readonly=True
    )

    @api.depends('partner_id')
    def _compute_peppol_available(self):
        for wizard in self:
            # Vérifier si Peppol est configuré pour ce partenaire
            wizard.peppol_available = bool(
                wizard.partner_id and 
                hasattr(wizard.partner_id, 'peppol_endpoint') and 
                wizard.partner_id.peppol_endpoint
            )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.email = self.partner_id.email

    def action_preview(self):
        """Apercu de la facture"""
        self.ensure_one()
        return self.invoice_id.action_preview_invoice()

    def action_send(self):
        """Envoyer la facture selon la methode choisie"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_("Aucune facture selectionnee."))
        
        if self.send_method in ('email', 'both'):
            if not self.email:
                raise UserError(_("Veuillez specifier une adresse email."))
            self._send_by_email()
        
        if self.send_method in ('peppol', 'both'):
            self._send_by_peppol()
        
        # Marquer comme envoyée
        self.invoice_id.write({'is_move_sent': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Facture envoyee'),
                'message': _('La facture %s a ete envoyee avec succes.') % self.invoice_id.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_by_email(self):
        """Envoyer la facture par email"""
        template = self.env.ref('lolirine_invoice.email_template_invoice', raise_if_not_found=False)
        
        if template:
            # Mettre à jour l'email du template temporairement
            template.with_context(
                default_email_to=self.email
            ).send_mail(
                self.invoice_id.id,
                force_send=True,
                email_values={'email_to': self.email}
            )
        else:
            # Fallback: envoi basique
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
                "Veuillez configurer l'endpoint Peppol dans la fiche client."
            ))
        
        # Vérifier si le module account_edi_ubl_cii est installé
        if 'account_edi_ubl_cii' in self.env.registry._init_modules:
            # Utiliser l'EDI standard d'Odoo
            self.invoice_id.action_process_edi_web_services()
        else:
            raise UserError(_(
                "Le module de facturation electronique Peppol n'est pas installe. "
                "Veuillez installer le module 'account_edi_ubl_cii' pour utiliser Peppol."
            ))

    def action_send_and_close(self):
        """Envoyer et fermer le wizard"""
        self.action_send()
        return {'type': 'ir.actions.act_window_close'}
