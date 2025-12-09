# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    """Extension du modèle sale.order pour l'indexation"""
    _inherit = 'sale.order'

    # Champs d'indexation
    indexation_enabled = fields.Boolean(
        string='Indexation activée',
        default=True,
        help="Si coché, cet abonnement sera inclus dans les indexations automatiques"
    )
    base_index_id = fields.Many2one(
        'storage.price.index',
        string='Indice de base',
        help="Indice de référence pour le calcul des indexations"
    )
    base_index_date = fields.Date(
        string='Date indice de base',
        help="Date de l'indice de base (généralement la date de début du contrat)"
    )
    last_indexation_id = fields.Many2one(
        'storage.indexation',
        string='Dernière indexation'
    )
    last_indexation_date = fields.Date(
        string='Date dernière indexation'
    )
    indexation_count = fields.Integer(
        string='Nombre d\'indexations',
        compute='_compute_indexation_count'
    )
    
    # Montants
    initial_recurring_amount = fields.Monetary(
        string='Montant récurrent initial',
        help="Montant récurrent au moment de la signature du contrat",
        currency_field='currency_id'
    )
    
    def _compute_indexation_count(self):
        IndexationLine = self.env['storage.indexation.line']
        for order in self:
            order.indexation_count = IndexationLine.search_count([
                ('subscription_id', '=', order.id)
            ])

    def action_view_indexations(self):
        """Affiche l'historique des indexations pour cet abonnement"""
        self.ensure_one()
        lines = self.env['storage.indexation.line'].search([
            ('subscription_id', '=', self.id)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Historique des indexations'),
            'res_model': 'storage.indexation.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', lines.ids)],
            'context': {'default_subscription_id': self.id},
        }

    def action_set_base_index(self):
        """Définit l'indice de base pour l'abonnement"""
        self.ensure_one()
        
        # Récupérer l'indice le plus proche de la date de commande
        index_date = self.date_order.date() if self.date_order else fields.Date.today()
        base_index = self.env['storage.price.index'].get_index_for_date(
            index_date, 'health'
        )
        
        if base_index:
            self.write({
                'base_index_id': base_index.id,
                'base_index_date': index_date,
            })
            
            # Calculer le montant récurrent initial
            recurring_total = 0.0
            for line in self.order_line:
                # Vérifier si la ligne est récurrente (Odoo 18)
                is_recurring = False
                if hasattr(line, 'temporal_type'):
                    is_recurring = line.temporal_type == 'subscription'
                elif hasattr(line.product_id, 'recurring_invoice'):
                    is_recurring = line.product_id.recurring_invoice
                else:
                    is_recurring = self.is_subscription
                
                if is_recurring:
                    recurring_total += line.price_unit * line.product_uom_qty
            
            self.initial_recurring_amount = recurring_total
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Indice de base défini'),
                    'message': _('Indice %s (valeur: %s) défini comme base') % (
                        base_index.name, base_index.value
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur'),
                    'message': _('Aucun indice trouvé pour la date %s') % index_date,
                    'type': 'warning',
                    'sticky': False,
                }
            }

    @api.model_create_multi
    def create(self, vals_list):
        """Initialise l'indice de base à la création d'un abonnement"""
        records = super().create(vals_list)
        
        for record in records:
            # Si c'est un abonnement, définir automatiquement l'indice de base
            if record.is_subscription and not record.base_index_id:
                index_date = record.date_order.date() if record.date_order else fields.Date.today()
                base_index = self.env['storage.price.index'].get_index_for_date(
                    index_date, 'health'
                )
                if base_index:
                    record.write({
                        'base_index_id': base_index.id,
                        'base_index_date': index_date,
                    })
        
        return records


class SaleOrderLine(models.Model):
    """Extension des lignes de commande pour l'indexation"""
    _inherit = 'sale.order.line'

    initial_price = fields.Monetary(
        string='Prix initial',
        help="Prix unitaire au moment de la signature du contrat",
        currency_field='currency_id'
    )
    last_indexed_price = fields.Monetary(
        string='Dernier prix indexé',
        currency_field='currency_id'
    )
    indexation_line_ids = fields.One2many(
        'storage.indexation.line',
        'subscription_line_id',
        string='Lignes d\'indexation'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Enregistre le prix initial à la création"""
        records = super().create(vals_list)
        for record in records:
            if not record.initial_price:
                record.initial_price = record.price_unit
        return records
