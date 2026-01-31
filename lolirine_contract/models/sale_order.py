from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    contract_access_code = fields.Char(string="Code acces")
    contract_forklift_code = fields.Char(string="Code gerbeur")
    contract_deposit_date = fields.Date(string="Date de depot des effets")
    contract_signature_date = fields.Date(string="Date de signature", default=fields.Date.context_today)
    contract_signature_location = fields.Char(string="Lieu de signature", default="Boninne")
    contract_deposit_amount = fields.Monetary(string="Montant caution", compute="_compute_contract_amounts", store=True)
    contract_monthly_rent = fields.Monetary(string="Loyer mensuel", compute="_compute_contract_amounts", store=True)
    contract_dossier_fees = fields.Monetary(string="Frais de dossier", compute="_compute_contract_amounts", store=True)
    
    # Champs related pour la carte d'identité du client
    partner_id_card_recto = fields.Binary(related="partner_id.id_card_recto", string="CI Recto", readonly=True)
    partner_id_card_verso = fields.Binary(related="partner_id.id_card_verso", string="CI Verso", readonly=True)
    partner_id_card_uploaded = fields.Boolean(related="partner_id.id_card_uploaded", string="CI fournie", readonly=True)

    @api.depends("order_line", "order_line.price_total", "order_line.product_id")
    def _compute_contract_amounts(self):
        for order in self:
            monthly_rent = 0.0
            dossier_fees = 0.0
            for line in order.order_line:
                if line.product_id and line.product_id.recurring_invoice:
                    monthly_rent += line.price_total
                elif line.product_id and "dossier" in (line.product_id.name or "").lower():
                    dossier_fees += line.price_total
            order.contract_monthly_rent = monthly_rent
            order.contract_dossier_fees = dossier_fees
            order.contract_deposit_amount = monthly_rent * 2

    # === EMAIL DE BIENVENUE ===
    def _send_welcome_email(self):
        """Envoyer l'email de bienvenue automatiquement pour les abonnements garde-meuble"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.message_post(
                body="⚠️ Envoi email de bienvenue impossible : le client n'a pas d'adresse email.",
                message_type='notification'
            )
            return False
        
        try:
            # Récupérer les infos du box
            box_name = self.order_line[0].product_id.name if self.order_line else "votre box"
            start_date = self.start_date.strftime('%d/%m/%Y') if self.start_date else 'À définir'
            portal_url = self.get_portal_url()
            
            # Construire le corps de l'email
            body_html = f"""
<div style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p>Toute l'équipe vous souhaite la bienvenue et vous remercie de votre confiance !</p>
    
    <p>Nous avons le plaisir de confirmer l'activation de votre contrat pour le box de stockage 
    <strong>{box_name}</strong>.</p>
    
    <p>Voici un résumé des informations utiles :</p>
    <ul>
        <li><strong>Date de début :</strong> {start_date}</li>
        <li><strong>Votre site de stockage :</strong> Rue Drève Boninas 2, 5021 Boninne</li>
        <li><strong>Horaires d'accès :</strong> 24H/24 et 7J/7</li>
    </ul>
    
    <p>Votre première facture sera générée prochainement. Vous pouvez à tout moment consulter vos documents, gérer votre abonnement et mettre à jour vos informations depuis votre portail client personnel.</p>
    
    <p>Votre Code d'accès vous sera fourni sur place, lors de la signature de votre contrat. Vous pouvez prendre contact avec nos services soit en ligne soit par téléphone pour convenir d'un rendez-vous.</p>
    
    <p style="margin: 20px 0;">
        <a href="{portal_url}" style="background-color: #875a7b; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            Accéder à mon portail client
        </a>
    </p>
    
    <p>N'hésitez pas à nous contacter si vous avez la moindre question.</p>
    
    <p>Cordialement,</p>
    
    <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #dee2e6;">
        <p style="margin: 0;">
            <strong style="color: #495057;">Lolirine Garde-Meubles</strong><br/>
            <span style="color: #6c757d;">Feron Rodney</span><br/>
            <span style="color: #6c757d;">Tél. : 0497/44 41 46 - 0498/52 11 31</span><br/>
            <span style="color: #6c757d;">Email : <a href="mailto:gardemeublelolirine@gmail.com" style="color: #007bff;">gardemeublelolirine@gmail.com</a></span>
        </p>
    </div>
</div>
"""
            
            # Créer et envoyer l'email
            mail_values = {
                'subject': f"Bienvenue ! Votre accès au box {box_name}",
                'body_html': body_html,
                'email_from': self.company_id.email_formatted or 'gardemeublelolirine@gmail.com',
                'email_to': self.partner_id.email,
                'model': 'sale.order',
                'res_id': self.id,
                'auto_delete': False,
            }
            
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            
            self.message_post(
                body=f"✅ Email de bienvenue envoyé à {self.partner_id.email}",
                message_type='notification'
            )
            return True
            
        except Exception as e:
            _logger.error(f"Erreur envoi email bienvenue {self.name}: {e}")
            self.message_post(
                body=f"❌ Erreur lors de l'envoi de l'email de bienvenue : {e}",
                message_type='notification'
            )
            return False

    def action_send_contract(self):
        self.ensure_one()
        template = self.env.ref("lolirine_contract.email_template_contract", raise_if_not_found=False)
        if not template:
            return True
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", raise_if_not_found=False)
        ctx = {
            "default_model": "sale.order",
            "default_res_ids": self.ids,
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
        }
        return {
            "name": "Envoyer le contrat",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": ctx,
        }

    def action_preview_contract(self):
        """Aperçu du contrat en HTML sans téléchargement"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/report/html/lolirine_contract.report_contract_document/%s" % self.id,
            "target": "new",
        }

    def action_preview_quotation(self):
        """Aperçu du devis en HTML sans téléchargement"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/report/html/lolirine_contract.report_lolirine_quotation_document/%s" % self.id,
            "target": "new",
        }

    def action_send_quotation(self):
        """Envoyer le devis par email avec le PDF en pièce jointe"""
        self.ensure_one()
        template = self.env.ref("lolirine_contract.email_template_quotation", raise_if_not_found=False)
        if not template:
            return True
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", raise_if_not_found=False)
        ctx = {
            "default_model": "sale.order",
            "default_res_ids": self.ids,
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
        }
        return {
            "name": "Envoyer le devis",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": ctx,
        }
