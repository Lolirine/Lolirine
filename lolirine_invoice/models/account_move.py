from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_send_invoice = fields.Boolean(
        string="Envoi automatique",
        default=False,
        help="Si active, la facture sera envoyee automatiquement par email apres confirmation"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi automatique Peppol",
        default=False,
        help="Si active, la facture sera envoyee automatiquement via Peppol apres confirmation"
    )
    
    peppol_sent = fields.Boolean(
        string="Envoyee via Peppol",
        default=False,
        copy=False,
        help="Indique si la facture a ete envoyee via Peppol"
    )
    
    peppol_sent_date = fields.Datetime(
        string="Date envoi Peppol",
        copy=False
    )

    def action_post(self):
        """Override pour envoyer automatiquement la facture après confirmation"""
        res = super().action_post()
        
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                # Envoyer automatiquement par email si l'option est activée
                if move.auto_send_invoice:
                    move._send_invoice_auto()
                
                # Envoyer automatiquement via Peppol si l'option est activée
                if move.auto_send_peppol:
                    move._send_invoice_peppol_auto()
        
        return res

    def _send_invoice_auto(self):
        """Envoyer la facture automatiquement par email"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.message_post(
                body=_("Envoi automatique impossible : le client n'a pas d'adresse email configuree."),
                message_type='notification'
            )
            return False
        
        template = self.env.ref('lolirine_invoice.email_template_invoice', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.write({'is_move_sent': True})
            self.message_post(
                body=_("Facture envoyee automatiquement par email a %s") % self.partner_id.email,
                message_type='notification'
            )
            return True
        return False

    def _send_invoice_peppol_auto(self):
        """Envoyer la facture automatiquement via Peppol"""
        self.ensure_one()
        
        # Vérifier si le client a un endpoint Peppol
        if not self.partner_id.peppol_eas or not self.partner_id.peppol_endpoint:
            self.message_post(
                body=_("Envoi Peppol impossible : le client n'a pas d'identifiant Peppol configure."),
                message_type='notification'
            )
            return False
        
        try:
            # Essayer d'envoyer via le module EDI standard d'Odoo
            if hasattr(self, 'edi_document_ids'):
                # Chercher le format Peppol/UBL
                peppol_format = self.env['account.edi.format'].search([
                    ('code', 'in', ['peppol', 'ubl_bis3', 'facturx', 'ubl_2_1'])
                ], limit=1)
                
                if peppol_format:
                    # Générer et envoyer le document EDI
                    self._process_edi_web_services(peppol_format)
                    self.write({
                        'peppol_sent': True,
                        'peppol_sent_date': fields.Datetime.now()
                    })
                    self.message_post(
                        body=_("Facture envoyee automatiquement via Peppol a %s") % self.partner_id.peppol_endpoint,
                        message_type='notification'
                    )
                    return True
            
            # Si le module account_peppol est installé
            if hasattr(self, 'action_process_edi_web_services'):
                self.action_process_edi_web_services()
                self.write({
                    'peppol_sent': True,
                    'peppol_sent_date': fields.Datetime.now()
                })
                self.message_post(
                    body=_("Facture envoyee via Peppol a %s") % self.partner_id.peppol_endpoint,
                    message_type='notification'
                )
                return True
                
            # Marquer comme envoyée même si le module EDI n'est pas disponible
            # (pour tracking manuel)
            self.message_post(
                body=_("Module EDI Peppol non configure. Veuillez installer et configurer account_edi_ubl_cii ou account_peppol."),
                message_type='notification'
            )
            return False
            
        except Exception as e:
            _logger.error("Erreur envoi Peppol pour facture %s: %s", self.name, str(e))
            self.message_post(
                body=_("Erreur lors de l'envoi Peppol : %s") % str(e),
                message_type='notification'
            )
            return False

    def action_send_peppol(self):
        """Action manuelle pour envoyer via Peppol"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee avant d'etre envoyee via Peppol."))
        
        if not self.partner_id.peppol_eas or not self.partner_id.peppol_endpoint:
            raise UserError(_("Le client n'a pas d'identifiant Peppol configure. Veuillez configurer l'EAS et l'endpoint Peppol sur la fiche client."))
        
        result = self._send_invoice_peppol_auto()
        
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succes'),
                    'message': _('Facture envoyee via Peppol'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Attention'),
                    'message': _('Verifiez le chatter pour les details'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def action_preview_invoice(self):
        """Ouvrir un apercu de la facture dans une nouvelle fenetre du navigateur"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        # Utiliser le rapport personnalisé Lolirine
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/lolirine_invoice.report_invoice_lolirine/%s' % self.id,
            'target': 'new',
        }

    def action_preview_invoice_html(self):
        """Ouvrir un apercu HTML de la facture dans le portail"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        # Ouvrir la page portail de la facture (avec le bon layout)
        if self.state == 'posted':
            return {
                'type': 'ir.actions.act_url',
                'url': '/my/invoices/%s' % self.id,
                'target': 'new',
            }
        else:
            # Pour les brouillons, utiliser le rapport HTML
            return {
                'type': 'ir.actions.act_url',
                'url': '/report/html/lolirine_invoice.report_invoice_lolirine/%s' % self.id,
                'target': 'new',
            }

    def action_confirm_and_send(self):
        """Confirmer la facture et ouvrir le wizard d'envoi"""
        self.ensure_one()
        
        # Si la facture est en brouillon, la confirmer d'abord
        if self.state == 'draft':
            self.action_post()
        
        # Ouvrir le wizard d'envoi
        return self.action_open_send_wizard()

    def action_open_send_wizard(self):
        """Ouvrir le wizard d'envoi de facture"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee avant d'etre envoyee."))
        
        return {
            'name': _('Envoyer la facture'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.invoice.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_email': self.partner_id.email,
            },
        }

    def action_send_invoice_email(self):
        """Envoyer la facture par email directement avec le template"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee avant d'etre envoyee."))
        
        template = self.env.ref('lolirine_invoice.email_template_invoice', raise_if_not_found=False)
        if not template:
            raise UserError(_("Le template d'email n'a pas ete trouve."))
        
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=False)
        
        ctx = {
            'default_model': 'account.move',
            'default_res_ids': self.ids,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'mark_invoice_as_sent': True,
            'force_email': True,
        }
        
        return {
            'name': _('Envoyer la facture par email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures email",
        default=False,
        help="Si active, les factures de ce client seront envoyees automatiquement par email apres confirmation"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto factures Peppol",
        default=False,
        help="Si active, les factures de ce client seront envoyees automatiquement via Peppol apres confirmation"
    )
    
    peppol_eas = fields.Selection([
        ('0002', '0002 - System Information et Coverage Area (SIREN)'),
        ('0007', '0007 - Numero TVA'),
        ('0009', '0009 - SIRET'),
        ('0037', '0037 - Numero TVA Finlandais'),
        ('0060', '0060 - DUNS'),
        ('0088', '0088 - EAN Location Code'),
        ('0096', '0096 - DANISH CHAMBER OF COMMERCE'),
        ('0106', '0106 - NL:KVK'),
        ('0130', '0130 - EU VAT'),
        ('0135', '0135 - IT:SIA'),
        ('0142', '0142 - IT:SECETI'),
        ('0151', '0151 - AU:ABN'),
        ('0183', '0183 - CH UIDB'),
        ('0184', '0184 - DE:LWID'),
        ('0190', '0190 - NL:OINO'),
        ('0191', '0191 - EE:CC'),
        ('0192', '0192 - NO:ORG'),
        ('0193', '0193 - UBLBE'),
        ('0195', '0195 - SG:UEN'),
        ('0196', '0196 - IS:KTNR'),
        ('0198', '0198 - DK:ERST'),
        ('0199', '0199 - LEI'),
        ('0200', '0200 - LT:LEC'),
        ('0201', '0201 - IT:CUUO'),
        ('0202', '0202 - DE:BWID'),
        ('0204', '0204 - DE:TID'),
        ('0208', '0208 - BE:EN'),
        ('0209', '0209 - GS1'),
        ('0210', '0210 - IT:CFI'),
        ('0211', '0211 - IT:IVA'),
        ('0212', '0212 - FI:OVT'),
        ('0213', '0213 - FI:OP'),
        ('9901', '9901 - DK:CPR'),
        ('9902', '9902 - DK:CVR'),
        ('9904', '9904 - DK:SE'),
        ('9905', '9905 - DK:VANS'),
        ('9906', '9906 - IT:VAT'),
        ('9907', '9907 - IT:CF'),
        ('9910', '9910 - HU:VAT'),
        ('9913', '9913 - EE:VAT'),
        ('9914', '9914 - AT:VAT'),
        ('9915', '9915 - AT:GOV'),
        ('9917', '9917 - AT:KUR'),
        ('9918', '9918 - AT:EB'),
        ('9919', '9919 - SEPA'),
        ('9920', '9920 - AT:UID'),
        ('9921', '9921 - IT:IPA'),
        ('9922', '9922 - AD:VAT'),
        ('9923', '9923 - AD:ESN'),
        ('9924', '9924 - SM:VAT'),
        ('9925', '9925 - SM:REN'),
        ('9926', '9926 - VA:VAT'),
        ('9928', '9928 - EE:EEID'),
        ('9930', '9930 - BE:VAT'),
        ('9931', '9931 - CY:VAT'),
        ('9932', '9932 - CZ:VAT'),
        ('9933', '9933 - DE:VAT'),
        ('9934', '9934 - EL:VAT'),
        ('9935', '9935 - ES:VAT'),
        ('9936', '9936 - FI:VAT'),
        ('9937', '9937 - FR:VAT'),
        ('9938', '9938 - GB:VAT'),
        ('9939', '9939 - IE:VAT'),
        ('9940', '9940 - IT:VAT'),
        ('9941', '9941 - LT:VAT'),
        ('9942', '9942 - LU:VAT'),
        ('9943', '9943 - LV:VAT'),
        ('9944', '9944 - MC:VAT'),
        ('9945', '9945 - ME:VAT'),
        ('9946', '9946 - MK:VAT'),
        ('9947', '9947 - MT:VAT'),
        ('9948', '9948 - NL:VAT'),
        ('9949', '9949 - PL:VAT'),
        ('9950', '9950 - PT:VAT'),
        ('9951', '9951 - RO:VAT'),
        ('9952', '9952 - RS:VAT'),
        ('9953', '9953 - SI:VAT'),
        ('9954', '9954 - SK:VAT'),
        ('9955', '9955 - SM:VAT'),
        ('9956', '9956 - TR:VAT'),
        ('9957', '9957 - VA:VAT'),
        ('9958', '9958 - SE:VAT'),
    ], string="EAS (Scheme ID)", 
       help="Electronic Address Scheme - Identifiant du schema pour Peppol. Pour la Belgique, utilisez 0208 (BE:EN) avec le numero d'entreprise.")
    
    peppol_endpoint = fields.Char(
        string="Endpoint Peppol",
        help="Identifiant Peppol du destinataire (ex: numero d'entreprise pour BE:EN)"
    )
    
    @api.onchange('vat')
    def _onchange_vat_peppol(self):
        """Suggérer l'endpoint Peppol basé sur le numéro TVA"""
        if self.vat and not self.peppol_endpoint:
            # Extraire le numéro sans le préfixe pays
            vat_clean = self.vat.replace(' ', '').replace('.', '')
            if vat_clean.startswith('BE'):
                self.peppol_eas = '0208'  # BE:EN
                self.peppol_endpoint = vat_clean[2:]  # Numéro sans BE


class SaleSubscription(models.Model):
    _inherit = "sale.order"
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto Peppol",
        default=False,
        help="Si active, les factures generees par cet abonnement seront envoyees automatiquement via Peppol"
    )
    
    @api.onchange('partner_id')
    def _onchange_partner_peppol(self):
        """Hériter les préférences Peppol du client"""
        if self.partner_id and self.partner_id.auto_send_peppol:
            self.auto_send_peppol = True
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        """Override pour propager l'option d'envoi auto du client/abonnement vers la facture"""
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        
        for move in moves:
            # Email auto
            if move.partner_id.auto_send_invoice:
                move.auto_send_invoice = True
            
            # Peppol auto - prioriser l'abonnement, sinon le client
            subscription = self.filtered(lambda s: move.partner_id in s.partner_id)
            if subscription and subscription[0].auto_send_peppol:
                move.auto_send_peppol = True
            elif move.partner_id.auto_send_peppol:
                move.auto_send_peppol = True
        
        return moves
