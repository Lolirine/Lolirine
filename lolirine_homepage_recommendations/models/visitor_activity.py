# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class VisitorProductActivity(models.Model):
    """
    Modèle pour tracker l'activité des visiteurs sur les produits.
    Stocke les vues de produits, ajouts au panier, et achats.
    """
    _name = 'visitor.product.activity'
    _description = 'Activité Visiteur sur les Produits'
    _order = 'create_date desc'

    visitor_id = fields.Many2one(
        'website.visitor',
        string='Visiteur',
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Template Produit',
        related='product_id.product_tmpl_id',
        store=True,
        index=True,
    )
    category_id = fields.Many2one(
        'product.public.category',
        string='Catégorie',
        compute='_compute_category',
        store=True,
        index=True,
    )
    activity_type = fields.Selection([
        ('view', 'Consultation'),
        ('cart', 'Ajout Panier'),
        ('wishlist', 'Liste de souhaits'),
        ('purchase', 'Achat'),
    ], string='Type d\'activité', required=True, default='view', index=True)
    
    view_count = fields.Integer(string='Nombre de vues', default=1)
    last_view_date = fields.Datetime(string='Dernière consultation', default=fields.Datetime.now)
    session_id = fields.Char(string='Session ID', index=True)
    website_id = fields.Many2one('website', string='Site Web', index=True)

    @api.depends('product_tmpl_id', 'product_tmpl_id.public_categ_ids')
    def _compute_category(self):
        for record in self:
            if record.product_tmpl_id and record.product_tmpl_id.public_categ_ids:
                # Prendre la première catégorie principale
                record.category_id = record.product_tmpl_id.public_categ_ids[0]
            else:
                record.category_id = False

    @api.model
    def log_product_view(self, product_id, visitor_id=None, partner_id=None, session_id=None, website_id=None):
        """
        Enregistre ou met à jour une vue de produit.
        Si le produit a déjà été vu récemment, incrémente le compteur.
        """
        domain = [
            ('product_id', '=', product_id),
            ('activity_type', '=', 'view'),
        ]
        
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        elif visitor_id:
            domain.append(('visitor_id', '=', visitor_id))
        elif session_id:
            domain.append(('session_id', '=', session_id))
        else:
            return False
        
        existing = self.search(domain, limit=1)
        
        if existing:
            existing.write({
                'view_count': existing.view_count + 1,
                'last_view_date': fields.Datetime.now(),
            })
            return existing
        else:
            vals = {
                'product_id': product_id,
                'activity_type': 'view',
                'visitor_id': visitor_id,
                'partner_id': partner_id,
                'session_id': session_id,
                'website_id': website_id,
            }
            return self.create(vals)

    @api.model
    def log_purchase(self, product_id, partner_id, website_id=None):
        """
        Enregistre un achat de produit.
        """
        return self.create({
            'product_id': product_id,
            'partner_id': partner_id,
            'activity_type': 'purchase',
            'website_id': website_id,
        })

    @api.model
    def cleanup_old_activities(self, days=90):
        """
        Nettoie les activités anciennes pour éviter une croissance infinie de la base.
        Garde les achats mais supprime les vues anciennes.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        old_views = self.search([
            ('activity_type', '=', 'view'),
            ('create_date', '<', cutoff_date),
        ])
        _logger.info(f"Nettoyage de {len(old_views)} anciennes activités de vue")
        old_views.unlink()


class VisitorCategoryPreference(models.Model):
    """
    Stocke les préférences de catégorie calculées pour chaque visiteur.
    """
    _name = 'visitor.category.preference'
    _description = 'Préférence de Catégorie Visiteur'
    _order = 'score desc'

    visitor_id = fields.Many2one(
        'website.visitor',
        string='Visiteur',
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        ondelete='cascade',
        index=True,
    )
    category_id = fields.Many2one(
        'product.public.category',
        string='Catégorie',
        required=True,
        ondelete='cascade',
        index=True,
    )
    score = fields.Float(string='Score d\'intérêt', default=0.0)
    view_count = fields.Integer(string='Nombre de vues', default=0)
    purchase_count = fields.Integer(string='Nombre d\'achats', default=0)
    last_interaction = fields.Datetime(string='Dernière interaction')

    @api.model
    def compute_preferences(self, visitor_id=None, partner_id=None):
        """
        Calcule les scores de préférence pour un visiteur basé sur son activité.
        Score = (vues * 1) + (ajouts panier * 3) + (achats * 10)
        """
        Activity = self.env['visitor.product.activity']
        
        domain = []
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        elif visitor_id:
            domain.append(('visitor_id', '=', visitor_id))
        else:
            return
        
        activities = Activity.search(domain)
        
        # Calculer les scores par catégorie
        category_scores = {}
        for activity in activities:
            if not activity.category_id:
                continue
            cat_id = activity.category_id.id
            if cat_id not in category_scores:
                category_scores[cat_id] = {
                    'score': 0,
                    'views': 0,
                    'purchases': 0,
                    'last_date': activity.last_view_date or activity.create_date,
                }
            
            # Pondération selon le type d'activité
            weights = {'view': 1, 'cart': 3, 'wishlist': 2, 'purchase': 10}
            weight = weights.get(activity.activity_type, 1)
            
            if activity.activity_type == 'view':
                category_scores[cat_id]['views'] += activity.view_count
                category_scores[cat_id]['score'] += activity.view_count * weight
            else:
                category_scores[cat_id]['score'] += weight
            
            if activity.activity_type == 'purchase':
                category_scores[cat_id]['purchases'] += 1
            
            # Mettre à jour la dernière date
            activity_date = activity.last_view_date or activity.create_date
            if activity_date > category_scores[cat_id]['last_date']:
                category_scores[cat_id]['last_date'] = activity_date
        
        # Mettre à jour les préférences
        for cat_id, data in category_scores.items():
            domain = [('category_id', '=', cat_id)]
            if partner_id:
                domain.append(('partner_id', '=', partner_id))
            elif visitor_id:
                domain.append(('visitor_id', '=', visitor_id))
            
            existing = self.search(domain, limit=1)
            vals = {
                'score': data['score'],
                'view_count': data['views'],
                'purchase_count': data['purchases'],
                'last_interaction': data['last_date'],
            }
            
            if existing:
                existing.write(vals)
            else:
                vals.update({
                    'category_id': cat_id,
                    'visitor_id': visitor_id,
                    'partner_id': partner_id,
                })
                self.create(vals)

    @api.model
    def cron_compute_all_preferences(self):
        """
        Méthode appelée par le cron pour recalculer les préférences
        de tous les visiteurs actifs des 7 derniers jours.
        """
        cutoff = datetime.now() - timedelta(days=7)
        Activity = self.env['visitor.product.activity']
        
        activities = Activity.search([('create_date', '>=', cutoff)])
        
        # Récupérer les visiteurs et partenaires uniques
        visitor_ids = set()
        partner_ids = set()
        
        for activity in activities:
            if activity.visitor_id:
                visitor_ids.add(activity.visitor_id.id)
            if activity.partner_id:
                partner_ids.add(activity.partner_id.id)
        
        # Calculer les préférences pour chaque visiteur
        for visitor_id in visitor_ids:
            try:
                self.compute_preferences(visitor_id=visitor_id)
            except Exception as e:
                _logger.warning(f"Erreur calcul préférences visiteur {visitor_id}: {e}")
        
        # Calculer les préférences pour chaque partenaire
        for partner_id in partner_ids:
            try:
                self.compute_preferences(partner_id=partner_id)
            except Exception as e:
                _logger.warning(f"Erreur calcul préférences partenaire {partner_id}: {e}")
        
        _logger.info(f"Préférences recalculées pour {len(visitor_ids)} visiteurs et {len(partner_ids)} partenaires")
