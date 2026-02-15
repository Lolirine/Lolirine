# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # === DROPSHIPPING ===
    is_dropship_order = fields.Boolean(string='Commande dropshipping',
                                        compute='_compute_is_dropship', store=True)
    dropship_status = fields.Selection([
        ('pending', 'En attente d\'analyse'),
        ('analyzed', 'Analysée'),
        ('supplier_selected', 'Fournisseur sélectionné'),
        ('to_process', 'À traiter'),
        ('po_created', 'BC fournisseur créé'),
        ('po_sent', 'BC envoyé'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('issue', 'Problème'),
    ], string='Statut dropship', default='pending', tracking=True)
    
    # Relations
    dropship_purchase_ids = fields.One2many('purchase.order', 'dropship_sale_id',
                                             string='Commandes fournisseur')
    dropship_purchase_count = fields.Integer(compute='_compute_dropship_purchase_count')
    dropship_decision_log_ids = fields.One2many('dropship.decision.log', 'sale_order_id',
                                                 string='Journal des décisions')
    
    # Marges
    dropship_estimated_margin = fields.Monetary(string='Marge estimée',
                                                 compute='_compute_dropship_margins',
                                                 currency_field='currency_id')
    dropship_margin_percent = fields.Float(string='Marge (%)',
                                            compute='_compute_dropship_margins')
    dropship_total_supplier_cost = fields.Monetary(string='Coût fournisseur total',
                                                    compute='_compute_dropship_margins',
                                                    currency_field='currency_id')
    
    # Alertes
    dropship_has_alerts = fields.Boolean(compute='_compute_dropship_alerts')
    dropship_alert_message = fields.Text(compute='_compute_dropship_alerts')
    
    # Workflow
    dropship_needs_processing = fields.Boolean(
        string='À traiter',
        compute='_compute_dropship_needs_processing',
    )

    @api.depends('order_line.product_id.is_dropship_product')
    def _compute_is_dropship(self):
        for order in self:
            order.is_dropship_order = any(
                line.product_id.product_tmpl_id.is_dropship_product 
                for line in order.order_line if line.product_id
            )

    def _compute_dropship_purchase_count(self):
        for order in self:
            order.dropship_purchase_count = len(order.dropship_purchase_ids)

    @api.depends('order_line.dropship_supplier_cost', 'amount_untaxed')
    def _compute_dropship_margins(self):
        for order in self:
            total_cost = sum(line.dropship_supplier_cost for line in order.order_line)
            order.dropship_total_supplier_cost = total_cost
            
            if order.amount_untaxed > 0:
                margin = order.amount_untaxed - total_cost
                order.dropship_estimated_margin = margin
                order.dropship_margin_percent = (margin / order.amount_untaxed) * 100
            else:
                order.dropship_estimated_margin = 0
                order.dropship_margin_percent = 0

    @api.depends('order_line.dropship_alert')
    def _compute_dropship_alerts(self):
        for order in self:
            alerts = order.order_line.filtered('dropship_alert')
            order.dropship_has_alerts = bool(alerts)
            if alerts:
                order.dropship_alert_message = '\n'.join(
                    f"• {line.product_id.name}: {line.dropship_alert}" 
                    for line in alerts
                )
            else:
                order.dropship_alert_message = ''

    @api.depends('is_dropship_order', 'state', 'dropship_status', 'dropship_purchase_count')
    def _compute_dropship_needs_processing(self):
        for order in self:
            order.dropship_needs_processing = (
                order.is_dropship_order
                and order.state == 'sale'
                and order.dropship_status in ('pending', 'to_process', 'analyzed', 'supplier_selected')
                and order.dropship_purchase_count == 0
            )

    def action_confirm(self):
        """Override: Analyser les fournisseurs avant confirmation"""
        for order in self:
            if order.is_dropship_order:
                order._analyze_dropship_suppliers()
        
        result = super().action_confirm()
        
        # Créer automatiquement les BC fournisseur si configuré
        config = self.env['dropship.config'].get_config()
        if config.auto_create_po:
            for order in self:
                if order.is_dropship_order and order.dropship_status == 'supplier_selected':
                    order._create_dropship_purchase_orders()
        
        return result

    def _analyze_dropship_suppliers(self):
        """Analyse et sélectionne les meilleurs fournisseurs pour chaque ligne"""
        self.ensure_one()
        config = self.env['dropship.config'].get_config()
        
        destination_country_id = self.partner_shipping_id.country_id.id if self.partner_shipping_id else None
        
        all_selected = True
        
        for line in self.order_line:
            if not line.product_id or not line.product_id.product_tmpl_id.is_dropship_product:
                continue
            
            result = line.product_id.get_best_supplier(
                quantity=line.product_uom_qty,
                destination_country_id=destination_country_id,
                urgent=False
            )
            
            if result['success']:
                supplier_info = result['supplier_info']
                
                # Mettre à jour la ligne
                line.write({
                    'dropship_supplier_info_id': supplier_info.id,
                    'dropship_supplier_id': supplier_info.supplier_id.id,
                    'dropship_supplier_cost': result['costs']['total_cost'],
                    'dropship_margin': result['margin'],
                    'dropship_score': result['score'],
                    'dropship_alert': '',
                })
                
                # Logger la décision
                self.env['dropship.decision.log'].create({
                    'sale_order_id': self.id,
                    'sale_line_id': line.id,
                    'product_id': line.product_id.id,
                    'selected_supplier_id': supplier_info.supplier_id.id,
                    'supplier_info_id': supplier_info.id,
                    'decision_type': 'auto' if config.auto_select_supplier else 'manual',
                    'sale_price': line.price_subtotal,
                    'supplier_cost': result['costs']['total_cost'],
                    'margin_amount': line.price_subtotal - result['costs']['total_cost'],
                    'margin_percent': result['margin'],
                    'score': result['score'],
                    'reasons': '\n'.join(result['reasons']),
                    'alternatives_count': len(result.get('alternatives', [])),
                })
            else:
                all_selected = False
                line.write({
                    'dropship_alert': result['error'],
                })
                
                # Notifier si configuré
                if config.notify_no_supplier:
                    self._notify_no_supplier(line, result['error'])
        
        self.dropship_status = 'supplier_selected' if all_selected else 'analyzed'

    def _create_dropship_purchase_orders(self):
        """Crée les commandes fournisseur pour les lignes dropshipping"""
        self.ensure_one()
        
        # Grouper les lignes par fournisseur
        lines_by_supplier = {}
        for line in self.order_line:
            if line.dropship_supplier_id:
                supplier_id = line.dropship_supplier_id.id
                if supplier_id not in lines_by_supplier:
                    lines_by_supplier[supplier_id] = []
                lines_by_supplier[supplier_id].append(line)
        
        created_pos = self.env['purchase.order']
        config = self.env['dropship.config'].get_config()
        
        for supplier_id, lines in lines_by_supplier.items():
            supplier = self.env['res.partner'].browse(supplier_id)
            
            # Créer la commande fournisseur
            po_vals = {
                'partner_id': supplier_id,
                'dropship_sale_id': self.id,
                'is_dropship_order': True,
                'dest_address_id': self.partner_shipping_id.id,
                'origin': self.name,
                'notes': self._prepare_dropship_notes(supplier, config),
            }
            
            po = self.env['purchase.order'].create(po_vals)
            
            # Créer les lignes
            for sale_line in lines:
                supplier_info = sale_line.dropship_supplier_info_id
                
                # Utiliser le prix négocié pour le bon de commande fournisseur
                purchase_price = supplier_info.negotiated_price if supplier_info.negotiated_price else supplier_info.price
                
                po_line_vals = {
                    'order_id': po.id,
                    'product_id': sale_line.product_id.id,
                    'name': supplier_info.supplier_product_name or sale_line.product_id.name,
                    'product_qty': sale_line.product_uom_qty,
                    'product_uom': sale_line.product_uom.id,
                    'price_unit': purchase_price,
                    'date_planned': fields.Datetime.now(),
                    'sale_line_id': sale_line.id,
                    'supplier_product_ref': supplier_info.supplier_product_ref,
                }
                
                self.env['purchase.order.line'].create(po_line_vals)
            
            created_pos |= po
            
            _logger.info(f"Dropship PO {po.name} created for SO {self.name} (supplier: {supplier.name})")
        
        if created_pos:
            self.dropship_status = 'po_created'
            
            # Message informatif
            self.message_post(
                body=f"📋 {len(created_pos)} bon(s) de commande fournisseur créé(s) en brouillon.<br/>"
                     f"Veuillez vérifier les prix et envoyer aux fournisseurs après validation."
            )
        
        return created_pos

    def _prepare_dropship_notes(self, supplier, config):
        """Prépare les notes/instructions pour le BC fournisseur"""
        notes = []
        
        notes.append(f"=== COMMANDE DROPSHIPPING ===")
        notes.append(f"Référence client: {self.name}")
        notes.append(f"")
        notes.append(f"LIVRAISON DIRECTE AU CLIENT FINAL:")
        notes.append(f"  {self.partner_shipping_id.name}")
        if self.partner_shipping_id.street:
            notes.append(f"  {self.partner_shipping_id.street}")
        if self.partner_shipping_id.street2:
            notes.append(f"  {self.partner_shipping_id.street2}")
        notes.append(f"  {self.partner_shipping_id.zip} {self.partner_shipping_id.city}")
        if self.partner_shipping_id.country_id:
            notes.append(f"  {self.partner_shipping_id.country_id.name}")
        if self.partner_shipping_id.phone:
            notes.append(f"  Tél: {self.partner_shipping_id.phone}")
        
        notes.append(f"")
        
        if config.use_neutral_packaging:
            notes.append("⚠️ EMBALLAGE NEUTRE REQUIS - Pas de mention fournisseur")
        
        if not config.include_packing_slip:
            notes.append("⚠️ NE PAS INCLURE DE BON DE LIVRAISON/FACTURE")
        
        if config.default_shipping_instructions:
            notes.append(f"")
            notes.append(f"Instructions: {config.default_shipping_instructions}")
        
        if supplier.dropship_special_instructions:
            notes.append(f"")
            notes.append(f"Note fournisseur: {supplier.dropship_special_instructions}")
        
        return '\n'.join(notes)

    def _notify_no_supplier(self, line, error_message):
        """Envoie une notification quand aucun fournisseur n'est trouvé"""
        config = self.env['dropship.config'].get_config()
        
        if config.notification_user_ids:
            self.message_post(
                body=f"⚠️ <b>Alerte Dropshipping</b><br/>"
                     f"Produit: {line.product_id.name}<br/>"
                     f"Problème: {error_message}",
                partner_ids=config.notification_user_ids.mapped('partner_id').ids,
                message_type='notification',
            )

    def action_view_dropship_purchases(self):
        """Action pour voir les BC fournisseur liés"""
        self.ensure_one()
        return {
            'name': _('Commandes fournisseur'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('dropship_sale_id', '=', self.id)],
        }

    def action_manual_supplier_selection(self):
        """Ouvre le wizard de sélection manuelle de fournisseur"""
        self.ensure_one()
        return {
            'name': _('Sélection fournisseur'),
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.selection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            },
        }

    def action_create_dropship_po(self):
        """Action manuelle pour créer les BC fournisseur"""
        self.ensure_one()
        
        if self.dropship_status not in ['analyzed', 'supplier_selected']:
            raise UserError(_("Veuillez d'abord analyser les fournisseurs."))
        
        # Vérifier que tous les produits ont un fournisseur
        lines_without_supplier = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.is_dropship_product and not l.dropship_supplier_id
        )
        
        if lines_without_supplier:
            raise UserError(_(
                "Les produits suivants n'ont pas de fournisseur sélectionné:\n%s"
            ) % '\n'.join(f"- {l.product_id.name}" for l in lines_without_supplier))
        
        return self._create_dropship_purchase_orders()

    def action_reanalyze_suppliers(self):
        """Relance l'analyse des fournisseurs"""
        self.ensure_one()
        self._analyze_dropship_suppliers()
        return True

    def action_open_create_dropship_po_wizard(self):
        """Ouvre le wizard de création de BC fournisseur"""
        self.ensure_one()
        return {
            'name': _('Créer BC Dropshipping'),
            'type': 'ir.actions.act_window',
            'res_model': 'create.dropship.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_sale_order_id': self.id,
            },
        }

    def action_mark_shipped(self):
        """Marque la commande comme expédiée"""
        self.ensure_one()
        self.dropship_status = 'shipped'
        self.message_post(body="📦 Commande marquée comme expédiée")

    def action_mark_delivered(self):
        """Marque la commande comme livrée"""
        self.ensure_one()
        self.dropship_status = 'delivered'
        self.message_post(body="✅ Commande marquée comme livrée")

    def action_mark_issue(self):
        """Marque la commande comme ayant un problème"""
        self.ensure_one()
        self.dropship_status = 'issue'
        self.message_post(body="⚠️ Problème signalé sur la commande")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # === DROPSHIPPING ===
    dropship_supplier_info_id = fields.Many2one('supplier.dropship.info',
                                                 string='Info fournisseur')
    dropship_supplier_id = fields.Many2one('res.partner', string='Fournisseur dropship',
                                           domain=[('supplier_rank', '>', 0)])
    dropship_supplier_cost = fields.Monetary(string='Coût fournisseur',
                                              currency_field='currency_id')
    dropship_margin = fields.Float(string='Marge (%)')
    dropship_score = fields.Float(string='Score sélection')
    dropship_alert = fields.Text(string='Alerte')
    
    # Tracking
    dropship_tracking_number = fields.Char(string='N° de suivi')
    dropship_carrier = fields.Char(string='Transporteur')
    dropship_shipped_date = fields.Datetime(string='Date expédition')
    dropship_delivered_date = fields.Datetime(string='Date livraison')

    @api.onchange('product_id')
    def _onchange_product_dropship(self):
        """Met à jour les infos dropshipping quand le produit change"""
        if self.product_id and self.product_id.product_tmpl_id.is_dropship_product:
            best = self.product_id.get_best_supplier(quantity=self.product_uom_qty or 1)
            if best['success']:
                self.dropship_supplier_info_id = best['supplier_info'].id
                self.dropship_supplier_id = best['supplier_info'].supplier_id.id
                self.dropship_supplier_cost = best['costs']['total_cost']
                self.dropship_margin = best['margin']
