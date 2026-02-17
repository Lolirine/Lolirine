# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResolveIssueWizard(models.TransientModel):
    _name = 'resolve.issue.wizard'
    _description = 'Résoudre un problème dropshipping'

    sale_order_id = fields.Many2one('sale.order', string='Commande', required=True)
    resolve_action = fields.Selection([
        ('back_to_po_sent', 'Retour à "BC envoyé" — En attente expédition'),
        ('back_to_po_created', 'Retour à "BC créé" — Revoir le BC fournisseur'),
        ('back_to_pending', 'Retour à "En attente" — Recommencer l\'analyse'),
        ('mark_shipped', 'Marquer comme expédiée'),
        ('mark_delivered', 'Marquer comme livrée — Problème résolu'),
        ('cancel', 'Annuler la commande'),
    ], string='Action', required=True, default='back_to_po_sent')
    resolution_note = fields.Text(string='Note de résolution',
                                   help='Décrivez comment le problème a été résolu')

    def action_resolve(self):
        """Résoudre le problème et changer le statut"""
        self.ensure_one()
        order = self.sale_order_id

        status_map = {
            'back_to_po_sent': 'po_sent',
            'back_to_po_created': 'po_created',
            'back_to_pending': 'pending',
            'mark_shipped': 'shipped',
            'mark_delivered': 'delivered',
        }

        if self.resolve_action == 'cancel':
            order.dropship_status = 'pending'
            order.action_cancel()
            body = f"🔧 <b>Problème résolu — Commande annulée</b>"
        else:
            new_status = status_map[self.resolve_action]
            old_status = order.dropship_status
            order.dropship_status = new_status
            label = dict(order._fields['dropship_status'].selection).get(new_status, new_status)
            body = f"🔧 <b>Problème résolu</b><br/>Statut : {label}"

        if self.resolution_note:
            body += f"<br/>Note : {self.resolution_note}"

        order.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')

        return {'type': 'ir.actions.act_window_close'}
