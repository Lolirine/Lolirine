# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class DropshipTrackingWizard(models.TransientModel):
    """Wizard pour mettre à jour les informations de suivi"""
    _name = 'dropship.tracking.wizard'
    _description = 'Mise à jour suivi dropshipping'

    purchase_id = fields.Many2one('purchase.order', string='Commande fournisseur', required=True)
    tracking_number = fields.Char(string='Numéro de suivi')
    carrier = fields.Char(string='Transporteur')
    carrier_selection = fields.Selection([
        ('bpost', 'bpost'),
        ('dhl', 'DHL'),
        ('ups', 'UPS'),
        ('fedex', 'FedEx'),
        ('dpd', 'DPD'),
        ('gls', 'GLS'),
        ('tnt', 'TNT'),
        ('chronopost', 'Chronopost'),
        ('colissimo', 'Colissimo'),
        ('mondialrelay', 'Mondial Relay'),
        ('other', 'Autre'),
    ], string='Transporteur (liste)')
    expected_delivery = fields.Date(string='Livraison prévue')
    supplier_order_ref = fields.Char(string='Réf. commande fournisseur')
    notify_customer = fields.Boolean(string='Notifier le client', default=True)
    notes = fields.Text(string='Notes')

    @api.onchange('carrier_selection')
    def _onchange_carrier_selection(self):
        if self.carrier_selection and self.carrier_selection != 'other':
            carriers = dict(self._fields['carrier_selection'].selection)
            self.carrier = carriers.get(self.carrier_selection, '')

    def action_update_tracking(self):
        """Met à jour les informations de suivi"""
        self.ensure_one()
        
        vals = {
            'dropship_tracking_number': self.tracking_number,
            'dropship_carrier': self.carrier,
            'dropship_expected_delivery': self.expected_delivery,
        }
        
        if self.supplier_order_ref:
            vals['supplier_order_ref'] = self.supplier_order_ref
        
        self.purchase_id.write(vals)
        
        # Mettre à jour les lignes de la commande client
        if self.purchase_id.dropship_sale_id:
            for po_line in self.purchase_id.order_line:
                if po_line.sale_line_id:
                    po_line.sale_line_id.write({
                        'dropship_tracking_number': self.tracking_number,
                        'dropship_carrier': self.carrier,
                    })
        
        # Notifier le client si demandé
        if self.notify_customer and self.purchase_id.dropship_sale_id:
            # Marquer comme expédié si un numéro de suivi est fourni
            if self.tracking_number and self.purchase_id.dropship_status in ('sent', 'confirmed'):
                self.purchase_id.action_mark_shipped()
        
        # Logger
        message = f"📦 Suivi mis à jour:\n"
        if self.tracking_number:
            message += f"- N° suivi: {self.tracking_number}\n"
        if self.carrier:
            message += f"- Transporteur: {self.carrier}\n"
        if self.expected_delivery:
            message += f"- Livraison prévue: {self.expected_delivery}\n"
        if self.notes:
            message += f"- Notes: {self.notes}\n"
        
        self.purchase_id.message_post(body=message)
        
        return {'type': 'ir.actions.act_window_close'}

    def action_update_and_notify(self):
        """Met à jour et notifie le client"""
        self.notify_customer = True
        return self.action_update_tracking()
