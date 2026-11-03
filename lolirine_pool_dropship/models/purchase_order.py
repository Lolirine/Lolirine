# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # === DROPSHIPPING ===
    is_dropship_order = fields.Boolean(string='Commande dropshipping', default=False)
    dropship_sale_id = fields.Many2one('sale.order', string='Commande client liée',
                                        ondelete='set null')
    dropship_status = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyée'),
        ('confirmed', 'Confirmée fournisseur'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('issue', 'Problème'),
    ], string='Statut dropship', default='draft', tracking=True)
    
    # Destinataire final (client)
    dest_address_id = fields.Many2one('res.partner', string='Livrer à (client final)',
                                       help="Adresse de livraison du client final")
    
    # Tracking
    dropship_tracking_number = fields.Char(string='N° de suivi', tracking=True)
    dropship_carrier = fields.Char(string='Transporteur')
    dropship_shipped_date = fields.Datetime(string='Date expédition')
    dropship_expected_delivery = fields.Date(string='Livraison prévue')
    dropship_delivered_date = fields.Datetime(string='Date livraison effective')
    
    # Communication
    # même information que la « Référence fournisseur » standard d'Odoo (plus de doublon)
    supplier_order_ref = fields.Char(string='Réf. commande fournisseur', related='partner_ref',
                                     readonly=False, help="Numéro de commande chez le fournisseur")
    last_sent_date = fields.Datetime(string='Dernier envoi')
    send_email_on_confirm = fields.Boolean(string='Envoyer email au fournisseur',
                                           default=False,
                                           help="Cocher pour envoyer automatiquement l'email au fournisseur lors de la confirmation")
    email_sent = fields.Boolean(string='Email envoyé', default=False, readonly=True)
    
    # Coûts
    total_dropship_cost = fields.Monetary(string='Coût total dropship',
                                           compute='_compute_dropship_costs',
                                           currency_field='currency_id')
    shipping_cost = fields.Monetary(string='Frais de port', currency_field='currency_id')
    handling_cost = fields.Monetary(string='Frais manutention', currency_field='currency_id')

    @api.depends('order_line.price_subtotal', 'shipping_cost', 'handling_cost')
    def _compute_dropship_costs(self):
        for order in self:
            order.total_dropship_cost = (
                order.amount_untaxed + 
                order.shipping_cost + 
                order.handling_cost
            )

    def button_confirm(self):
        """Override: Met à jour le statut dropship et envoie email si demandé"""
        result = super().button_confirm()
        
        for order in self:
            if order.is_dropship_order:
                order.dropship_status = 'confirmed'
                
                # Envoyer l'email si la case est cochée
                if order.send_email_on_confirm and not order.email_sent:
                    order._pool_envoyer_direct()
                
                # Mettre à jour la commande client liée
                if order.dropship_sale_id:
                    if order.email_sent:
                        order.dropship_sale_id.dropship_status = 'po_sent'
                    else:
                        order.dropship_sale_id.dropship_status = 'po_created'
        
        return result

    def action_send_dropship_email(self):
        """Ouvre l'e-mail de commande au fournisseur (modèle « Dropshipping: Commande fournisseur »,
        bon de commande en PDF joint) pour relecture et modification avant l'envoi. La commande est
        marquée envoyée quand l'e-mail part."""
        self.ensure_one()
        if not self.is_dropship_order:
            return False
        modele = self.env.ref('lolirine_pool_dropship.email_template_dropship_po', raise_if_not_found=False)
        if not modele:
            self._pool_envoyer_direct()
            return True
        return {
            'type': 'ir.actions.act_window',
            'name': _("Envoyer la commande au fournisseur"),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_model': 'purchase.order',
                'default_res_ids': self.ids,
                'default_template_id': modele.id,
                'default_composition_mode': 'comment',
                'default_email_layout_xmlid': 'mail.mail_notification_light',
                'force_email': True,
                'hide_mail_template_management_options': True,
                'pool_dropship_marquer_envoye': True,
            },
        }

    def action_rfq_send(self):
        """« Envoyer un bon de commande » d'une commande dropship confirmée : même e-mail complet que
        « Envoyer au fournisseur » (coordonnées de la société, lignes, livraison au client final)."""
        if (len(self) == 1 and self.is_dropship_order and self.state in ('purchase', 'done')
                and not self.env.context.get('send_rfq')):
            return self.action_send_dropship_email()
        return super().action_rfq_send()

    def _pool_envoyer_direct(self):
        """Envoi sans relecture (case « Envoyer email au fournisseur » à la confirmation)."""
        for po in self.filtered('is_dropship_order'):
            po._send_dropship_order()
            po._pool_marquer_envoye()
        return True

    def _pool_marquer_envoye(self):
        for po in self:
            po.email_sent = True
            po.dropship_status = 'sent'
            if po.dropship_sale_id:
                po.dropship_sale_id.dropship_status = 'po_sent'

    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)
        if self.env.context.get('pool_dropship_marquer_envoye') and kwargs.get('message_type', 'notification') == 'comment':
            self.filtered('is_dropship_order')._pool_marquer_envoye()
        return message

    def _send_dropship_order(self):
        """Envoie la commande au fournisseur"""
        self.ensure_one()
        
        if not self.is_dropship_order:
            return
        
        supplier = self.partner_id
        
        # Déterminer la méthode d'envoi
        if supplier.dropship_api_enabled and supplier.dropship_api_endpoint:
            self._send_via_api()
        elif supplier.dropship_order_email:
            self._send_via_email()
        else:
            self._send_via_email()  # Fallback sur l'email standard
        
        self.last_sent_date = fields.Datetime.now()
        self.dropship_status = 'sent'

    def _send_via_email(self):
        """Envoie la commande par email"""
        self.ensure_one()
        
        template = self.env.ref('lolirine_pool_dropship.email_template_dropship_po', 
                               raise_if_not_found=False)
        
        if template:
            # Utiliser l'email dropship si disponible
            email_to = self.partner_id.dropship_order_email or self.partner_id.email
            
            template.with_context(email_to=email_to).send_mail(
                self.id, 
                force_send=True,
                email_values={'email_to': email_to}
            )
            
            self.message_post(body=f"📧 Commande envoyée par email à {email_to}")
            _logger.info(f"Dropship PO {self.name} sent via email to {email_to}")
        else:
            # Fallback: utiliser le mécanisme standard
            self.action_rfq_send()

    def _send_via_api(self):
        """Envoie la commande via API (à implémenter selon le fournisseur)"""
        self.ensure_one()
        
        _logger.warning(f"API sending not implemented for PO {self.name}")
        self.message_post(body="⚠️ Envoi API non implémenté - commande à envoyer manuellement")
        
        # TODO: Implémenter les appels API selon les fournisseurs
        # Exemple de structure:
        # api_endpoint = self.partner_id.dropship_api_endpoint
        # api_key = self.partner_id.dropship_api_key
        # payload = self._prepare_api_payload()
        # response = requests.post(api_endpoint, json=payload, headers={'Authorization': api_key})

    def action_update_tracking(self):
        """Action pour mettre à jour le numéro de suivi"""
        self.ensure_one()
        return {
            'name': _('Mettre à jour le suivi'),
            'type': 'ir.actions.act_window',
            'res_model': 'dropship.tracking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_tracking_number': self.dropship_tracking_number,
                'default_carrier': self.dropship_carrier,
            },
        }

    def action_mark_shipped(self):
        """Marque la commande comme expédiée"""
        self.ensure_one()
        
        self.dropship_status = 'shipped'
        self.dropship_shipped_date = fields.Datetime.now()
        
        # Mettre à jour les lignes de la commande client
        if self.dropship_sale_id:
            self.dropship_sale_id.dropship_status = 'shipped'
            
            for po_line in self.order_line:
                if po_line.sale_line_id:
                    po_line.sale_line_id.write({
                        'dropship_shipped_date': fields.Datetime.now(),
                        'dropship_tracking_number': self.dropship_tracking_number,
                        'dropship_carrier': self.dropship_carrier,
                    })
            
            # Notifier le client
            self._notify_customer_shipment()
        
        self.message_post(body=f"📦 Commande expédiée - Tracking: {self.dropship_tracking_number or 'N/A'}")

    def action_mark_delivered(self):
        """Marque la commande comme livrée"""
        self.ensure_one()
        
        self.dropship_status = 'delivered'
        self.dropship_delivered_date = fields.Datetime.now()
        
        if self.dropship_sale_id:
            self.dropship_sale_id.dropship_status = 'delivered'
            
            for po_line in self.order_line:
                if po_line.sale_line_id:
                    po_line.sale_line_id.dropship_delivered_date = fields.Datetime.now()
        
        self.message_post(body="✅ Commande livrée")

    def action_report_issue(self):
        """Signale un problème avec la commande"""
        self.ensure_one()
        
        self.dropship_status = 'issue'
        
        if self.dropship_sale_id:
            self.dropship_sale_id.dropship_status = 'issue'
        
        return {
            'name': _('Signaler un problème'),
            'type': 'ir.actions.act_window',
            'res_model': 'dropship.issue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_sale_id': self.dropship_sale_id.id if self.dropship_sale_id else False,
            },
        }

    def _notify_customer_shipment(self):
        """Envoie une notification d'expédition au client"""
        self.ensure_one()
        
        if not self.dropship_sale_id:
            return
        
        template = self.env.ref('lolirine_pool_dropship.email_template_dropship_shipped',
                               raise_if_not_found=False)
        
        if template:
            template.send_mail(self.dropship_sale_id.id, force_send=True)

    def action_view_sale_order(self):
        """Voir la commande client liée"""
        self.ensure_one()
        if self.dropship_sale_id:
            return {
                'name': _('Commande client'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.dropship_sale_id.id,
            }

    # =========================================================
    # FACTURATION : FORCER JOURNAL ACHATS PISCINES
    # =========================================================

    def _prepare_invoice(self):
        """Override: forcer le journal Achats Piscines (PISC) pour les BC dropship"""
        invoice_vals = super()._prepare_invoice()
        if self.is_dropship_order:
            journal = self.env['account.journal'].search([
                ('code', '=', 'PISC'),
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if journal:
                invoice_vals['journal_id'] = journal.id
                _logger.info("Dropship PO %s: forced journal PISC (id=%s)", self.name, journal.id)
        return invoice_vals


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Lien avec la ligne de vente
    sale_line_id = fields.Many2one('sale.order.line', string='Ligne vente liée')
    
    # Référence fournisseur
    supplier_product_ref = fields.Char(string='Réf. fournisseur')
