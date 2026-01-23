# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class DropshipIssueWizard(models.TransientModel):
    """Wizard pour signaler un problème sur une commande dropshipping"""
    _name = 'dropship.issue.wizard'
    _description = 'Signalement problème dropshipping'

    purchase_id = fields.Many2one('purchase.order', string='Commande fournisseur')
    sale_id = fields.Many2one('sale.order', string='Commande client')
    
    issue_type = fields.Selection([
        ('delay', 'Retard de livraison'),
        ('damaged', 'Produit endommagé'),
        ('wrong_product', 'Mauvais produit'),
        ('missing_items', 'Articles manquants'),
        ('quality', 'Problème qualité'),
        ('packaging', 'Emballage non conforme'),
        ('communication', 'Problème de communication'),
        ('other', 'Autre'),
    ], string='Type de problème', required=True)
    
    severity = fields.Selection([
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('critical', 'Critique'),
    ], string='Gravité', default='medium', required=True)
    
    description = fields.Text(string='Description du problème', required=True)
    
    # Actions à entreprendre
    action_refund = fields.Boolean(string='Demander remboursement fournisseur')
    action_reship = fields.Boolean(string='Demander réexpédition')
    action_contact_customer = fields.Boolean(string='Contacter le client', default=True)
    action_update_reliability = fields.Boolean(string='Impacter le score fiabilité', default=True)
    
    # Données complémentaires
    affected_products = fields.Text(string='Produits concernés')
    evidence_note = fields.Text(string='Preuves / Photos (description)')

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        if self.purchase_id and not self.sale_id:
            self.sale_id = self.purchase_id.dropship_sale_id

    def action_report_issue(self):
        """Enregistre le problème et effectue les actions demandées"""
        self.ensure_one()
        
        # Créer une note détaillée
        issue_types = dict(self._fields['issue_type'].selection)
        severities = dict(self._fields['severity'].selection)
        
        message = f"""
<div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0;">
<h3 style="color: #721c24; margin-top: 0;">⚠️ PROBLÈME SIGNALÉ</h3>
<table style="width: 100%;">
<tr><td><strong>Type:</strong></td><td>{issue_types.get(self.issue_type)}</td></tr>
<tr><td><strong>Gravité:</strong></td><td>{severities.get(self.severity)}</td></tr>
<tr><td><strong>Description:</strong></td><td>{self.description}</td></tr>
"""
        if self.affected_products:
            message += f"<tr><td><strong>Produits:</strong></td><td>{self.affected_products}</td></tr>"
        if self.evidence_note:
            message += f"<tr><td><strong>Preuves:</strong></td><td>{self.evidence_note}</td></tr>"
        
        message += """
</table>
<hr/>
<strong>Actions demandées:</strong><ul>
"""
        if self.action_refund:
            message += "<li>Remboursement fournisseur</li>"
        if self.action_reship:
            message += "<li>Réexpédition</li>"
        if self.action_contact_customer:
            message += "<li>Contact client</li>"
        if self.action_update_reliability:
            message += "<li>Mise à jour score fiabilité</li>"
        
        message += "</ul></div>"
        
        # Poster sur la commande fournisseur
        if self.purchase_id:
            self.purchase_id.message_post(body=message, message_type='comment')
            self.purchase_id.dropship_status = 'issue'
            
            # Mettre à jour le score de fiabilité du fournisseur
            if self.action_update_reliability:
                supplier_infos = self.env['supplier.dropship.info'].search([
                    ('supplier_id', '=', self.purchase_id.partner_id.id)
                ])
                
                # Réduire le score selon la gravité
                penalty = {
                    'low': 2,
                    'medium': 5,
                    'high': 10,
                    'critical': 20,
                }.get(self.severity, 5)
                
                for info in supplier_infos:
                    new_score = max(0, info.reliability_score - penalty)
                    info.reliability_score = new_score
        
        # Poster sur la commande client
        if self.sale_id:
            customer_message = f"""
<div style="background-color: #fff3cd; padding: 15px; border-radius: 5px;">
<strong>⚠️ Incident signalé sur cette commande</strong><br/>
Type: {issue_types.get(self.issue_type)}<br/>
Notre équipe traite ce problème.
</div>
"""
            self.sale_id.message_post(body=customer_message, message_type='comment')
            self.sale_id.dropship_status = 'issue'
            
            # Notifier le client si demandé
            if self.action_contact_customer:
                # Envoyer un email au client
                template = self.env.ref('lolirine_pool_dropship.email_template_dropship_issue',
                                       raise_if_not_found=False)
                if template:
                    template.with_context(
                        issue_type=issue_types.get(self.issue_type),
                        issue_description=self.description
                    ).send_mail(self.sale_id.id, force_send=True)
        
        return {
            'type': 'ir.actions.act_window_close',
        }
