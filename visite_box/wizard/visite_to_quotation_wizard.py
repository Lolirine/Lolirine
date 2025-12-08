# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VisiteToQuotationWizard(models.TransientModel):
    _name = 'visite.to.quotation.wizard'
    _description = 'Conversion visite en devis'

    visite_id = fields.Many2one(
        'visite.box',
        string='Visite',
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True
    )
    box_id = fields.Many2one(
        'storage.box',
        string='Box sélectionnée',
        required=True,
        domain="[('state', '=', 'available')]"
    )
    
    # Type de création
    creation_type = fields.Selection([
        ('quotation', 'Devis simple'),
        ('subscription', 'Abonnement'),
    ], string='Type', default='subscription', required=True)
    
    # Dates
    date_start = fields.Date(
        string='Date de début',
        required=True,
        default=fields.Date.today
    )
    duree_prevue = fields.Selection([
        ('1', '1 mois'),
        ('3', '3 mois'),
        ('6', '6 mois'),
        ('12', '1 an'),
        ('24', '2 ans'),
        ('indefini', 'Indéterminée'),
    ], string='Durée prévue', default='6')
    
    # Options
    include_assurance = fields.Boolean(
        string='Inclure assurance',
        default=True
    )
    include_depot_garantie = fields.Boolean(
        string='Inclure dépôt de garantie',
        default=True
    )
    depot_garantie_mois = fields.Integer(
        string='Mois de garantie',
        default=1
    )
    
    # Notes
    notes = fields.Text(string='Notes pour le devis')

    @api.onchange('visite_id')
    def _onchange_visite_id(self):
        if self.visite_id:
            self.partner_id = self.visite_id.partner_id
            self.duree_prevue = self.visite_id.duree_prevue
            if self.visite_id.box_selected_id:
                self.box_id = self.visite_id.box_selected_id
            elif self.visite_id.box_ids:
                self.box_id = self.visite_id.box_ids[0]

    def action_create_quotation(self):
        """Créer le devis ou l'abonnement"""
        self.ensure_one()
        
        if not self.box_id:
            raise UserError(_("Veuillez sélectionner une box."))
        
        # Préparer les lignes de commande
        order_lines = self._prepare_order_lines()
        
        # Créer la commande/abonnement
        if self.creation_type == 'subscription':
            order = self._create_subscription(order_lines)
        else:
            order = self._create_quotation(order_lines)
        
        # Mettre à jour la visite
        self.visite_id.write({
            'state': 'converted',
            'sale_order_id': order.id,
            'box_selected_id': self.box_id.id,
        })
        
        # Réserver la box
        self.box_id.write({
            'state': 'reserved',
            'partner_id': self.partner_id.id,
        })
        
        # Mettre à jour le statut du partenaire
        self.partner_id.write({
            'storage_status': 'client',
        })
        
        # Ouvrir le devis créé
        return {
            'name': _('Devis') if self.creation_type == 'quotation' else _('Abonnement'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
        }

    def _prepare_order_lines(self):
        """Préparer les lignes de commande"""
        lines = []
        
        # Ligne principale: location de box
        product = self.box_id.product_id
        if not product:
            # Chercher ou créer un produit générique
            product = self.env['product.product'].search([
                ('default_code', '=', 'STORAGE_BOX')
            ], limit=1)
            if not product:
                product = self.env['product.product'].create({
                    'name': 'Location Box de stockage',
                    'default_code': 'STORAGE_BOX',
                    'type': 'service',
                    'list_price': self.box_id.prix_mensuel,
                    'recurring_invoice': True if self.creation_type == 'subscription' else False,
                })
        
        lines.append((0, 0, {
            'product_id': product.id,
            'name': f"Location Box {self.box_id.name} - {self.box_id.surface}m²",
            'product_uom_qty': 1,
            'price_unit': self.box_id.prix_mensuel,
        }))
        
        # Dépôt de garantie
        if self.include_depot_garantie:
            garantie_product = self.env['product.product'].search([
                ('default_code', '=', 'DEPOT_GARANTIE')
            ], limit=1)
            if not garantie_product:
                garantie_product = self.env['product.product'].create({
                    'name': 'Dépôt de garantie',
                    'default_code': 'DEPOT_GARANTIE',
                    'type': 'service',
                    'list_price': 0,
                })
            lines.append((0, 0, {
                'product_id': garantie_product.id,
                'name': f"Dépôt de garantie ({self.depot_garantie_mois} mois)",
                'product_uom_qty': 1,
                'price_unit': self.box_id.prix_mensuel * self.depot_garantie_mois,
            }))
        
        return lines

    def _create_quotation(self, order_lines):
        """Créer un devis simple"""
        return self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_lines,
            'note': self.notes,
            'origin': self.visite_id.name,
        })

    def _create_subscription(self, order_lines):
        """Créer un abonnement (si le module subscription est installé)"""
        vals = {
            'partner_id': self.partner_id.id,
            'order_line': order_lines,
            'note': self.notes,
            'origin': self.visite_id.name,
        }
        
        # Chercher un plan d'abonnement (module Enterprise uniquement)
        if 'sale.subscription.plan' in self.env:
            plan = self.env['sale.subscription.plan'].search([], limit=1)
            if plan:
                vals['plan_id'] = plan.id
            vals['start_date'] = self.date_start
        
        return self.env['sale.order'].create(vals)
