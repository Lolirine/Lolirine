# -*- coding: utf-8 -*-

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StorageIndexationWizard(models.TransientModel):
    """Assistant pour créer une nouvelle indexation"""
    _name = 'storage.indexation.wizard'
    _description = 'Assistant de création d\'indexation'

    # Étape 1: Sélection de l'indice
    index_type = fields.Selection([
        ('health', 'Indice Santé Belge'),
        ('cpi', 'Indice des Prix à la Consommation (CPI)'),
        ('custom', 'Indice Personnalisé'),
    ], string='Type d\'indice', required=True, default='health')
    
    new_index_id = fields.Many2one(
        'storage.price.index',
        string='Nouvel indice',
        domain="[('index_type', '=', index_type)]"
    )
    
    # Option pour créer un nouvel indice
    create_new_index = fields.Boolean(
        string='Créer un nouvel indice',
        default=False
    )
    new_index_date = fields.Date(
        string='Date du nouvel indice',
        default=lambda self: date.today().replace(day=1)
    )
    new_index_value = fields.Float(
        string='Valeur du nouvel indice',
        digits=(10, 2)
    )
    
    # Étape 2: Configuration
    indexation_date = fields.Date(
        string='Date d\'indexation',
        required=True,
        default=lambda self: date.today() + relativedelta(months=1, day=1),
        help="Date à partir de laquelle les nouveaux prix s'appliquent"
    )
    
    # Filtres sur les abonnements
    filter_partner_ids = fields.Many2many(
        'res.partner',
        string='Clients spécifiques',
        help="Laisser vide pour tous les clients"
    )
    filter_product_ids = fields.Many2many(
        'product.product',
        string='Produits spécifiques',
        help="Laisser vide pour tous les produits"
    )
    
    # Options
    send_notifications = fields.Boolean(
        string='Envoyer les notifications',
        default=True,
        help="Envoyer automatiquement les notifications aux clients après création"
    )
    notification_delay_days = fields.Integer(
        string='Délai de notification (jours)',
        default=30,
        help="Nombre de jours avant la date d'indexation pour envoyer les notifications"
    )
    
    # Aperçu
    preview_count = fields.Integer(
        string='Abonnements concernés',
        compute='_compute_preview'
    )
    preview_amount = fields.Monetary(
        string='Montant total actuel',
        compute='_compute_preview',
        currency_field='currency_id'
    )
    preview_increase = fields.Float(
        string='Augmentation estimée (%)',
        compute='_compute_preview'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('new_index_id', 'index_type', 'filter_partner_ids', 'filter_product_ids')
    def _compute_preview(self):
        for wizard in self:
            # Compter les abonnements éligibles (Odoo 18)
            domain = [
                ('is_subscription', '=', True),
                ('subscription_state', 'in', ['3_progress', 'in_progress', '2_progress']),
            ]
            
            # Si pas de résultat, essayer avec state = 'sale'
            subscriptions = self.env['sale.order'].search(domain)
            if not subscriptions:
                domain = [
                    ('is_subscription', '=', True),
                    ('state', '=', 'sale'),
                ]
                subscriptions = self.env['sale.order'].search(domain)
            
            # Filtrer par indexation_enabled si le champ existe
            subscriptions = subscriptions.filtered(
                lambda s: not hasattr(s, 'indexation_enabled') or s.indexation_enabled
            )
            
            if wizard.filter_partner_ids:
                subscriptions = subscriptions.filtered(lambda s: s.partner_id in wizard.filter_partner_ids)
            
            wizard.preview_count = len(subscriptions)
            
            # Calculer le montant total
            total = 0.0
            for sub in subscriptions:
                for line in sub.order_line:
                    # Vérifier si la ligne est récurrente
                    is_recurring = False
                    if hasattr(line, 'temporal_type'):
                        is_recurring = line.temporal_type == 'subscription'
                    elif hasattr(line.product_id, 'recurring_invoice'):
                        is_recurring = line.product_id.recurring_invoice
                    else:
                        is_recurring = sub.is_subscription
                    
                    if is_recurring:
                        if not wizard.filter_product_ids or line.product_id in wizard.filter_product_ids:
                            total += line.price_unit * line.product_uom_qty
            wizard.preview_amount = total
            
            # Estimer l'augmentation
            if wizard.new_index_id:
                # Utiliser un indice de base moyen
                base_indices = self.env['storage.price.index'].search([
                    ('index_type', '=', wizard.index_type)
                ], order='date asc', limit=1)
                
                if base_indices and base_indices.value:
                    wizard.preview_increase = (
                        (wizard.new_index_id.value - base_indices.value) 
                        / base_indices.value * 100
                    )
                else:
                    wizard.preview_increase = 0.0
            else:
                wizard.preview_increase = 0.0

    @api.onchange('index_type')
    def _onchange_index_type(self):
        """Met à jour le domaine de l'indice quand le type change"""
        self.new_index_id = False

    def action_fetch_latest_index(self):
        """Récupère le dernier indice depuis Statbel"""
        self.ensure_one()
        
        if self.index_type != 'health':
            raise UserError(_("La récupération automatique n'est disponible que pour l'indice santé"))
        
        index = self.env['storage.price.index'].fetch_latest_health_index()
        
        if index:
            self.new_index_id = index.id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Indice récupéré'),
                    'message': _('Indice %s (valeur: %s)') % (index.name, index.value),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_create_indexation(self):
        """Crée l'indexation avec les paramètres du wizard"""
        self.ensure_one()
        
        # Créer un nouvel indice si demandé
        if self.create_new_index:
            if not self.new_index_value:
                raise UserError(_("Veuillez saisir la valeur du nouvel indice"))
            
            new_index = self.env['storage.price.index'].create({
                'name': f"Indice {self.index_type} {self.new_index_date.strftime('%Y-%m')}",
                'index_type': self.index_type,
                'date': self.new_index_date,
                'value': self.new_index_value,
                'source': 'manual',
            })
            index_id = new_index.id
        else:
            if not self.new_index_id:
                raise UserError(_("Veuillez sélectionner un indice"))
            index_id = self.new_index_id.id
        
        # Créer l'indexation
        indexation = self.env['storage.indexation'].create({
            'index_type': self.index_type,
            'new_index_id': index_id,
            'date': self.indexation_date,
        })
        
        # Calculer l'indexation
        indexation.action_compute_indexation()
        
        # Filtrer les lignes si nécessaire
        if self.filter_partner_ids:
            lines_to_remove = indexation.line_ids.filtered(
                lambda l: l.partner_id not in self.filter_partner_ids
            )
            lines_to_remove.unlink()
        
        if self.filter_product_ids:
            lines_to_remove = indexation.line_ids.filtered(
                lambda l: l.product_id not in self.filter_product_ids
            )
            lines_to_remove.unlink()
        
        # Envoyer les notifications si demandé
        if self.send_notifications and indexation.line_ids:
            indexation.action_confirm()
            indexation.action_send_notifications()
        
        # Ouvrir l'indexation créée
        return {
            'type': 'ir.actions.act_window',
            'name': _('Indexation'),
            'res_model': 'storage.indexation',
            'res_id': indexation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_preview_subscriptions(self):
        """Affiche les abonnements qui seront indexés"""
        self.ensure_one()
        
        domain = [
            ('is_subscription', '=', True),
            ('subscription_state', '=', 'in_progress'),
            ('indexation_enabled', '=', True),
        ]
        if self.filter_partner_ids:
            domain.append(('partner_id', 'in', self.filter_partner_ids.ids))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Abonnements à indexer'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'new',
        }
