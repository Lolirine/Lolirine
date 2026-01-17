# -*- coding: utf-8 -*-
"""
Extension de product.template pour le multi-site Pool Store

Ajoute la méthode _get_pool_website_id() et étend la méthode create()
pour assigner automatiquement les produits piscine au bon site web.

INSTRUCTION: Remplacer le contenu de models/product_template.py dans lolirine_pool_import
"""

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Champ pour identifier les produits piscine
    is_pool_product = fields.Boolean(
        string='Produit Piscine',
        default=False,
        help="Coché automatiquement pour les produits importés via le module Pool Import"
    )
    
    @api.model
    def _get_pool_website_id(self):
        """
        Récupère l'ID du site web Pool Store.
        Utilisé pour assigner automatiquement les produits piscine au bon site.
        
        Returns:
            int or False: L'ID du site web Pool Store, ou False si non trouvé
        """
        Website = self.env['website']
        
        # Chercher le site Pool Store par son nom
        pool_website = Website.search([
            '|',
            ('name', 'ilike', 'Pool Store'),
            ('name', 'ilike', 'Lolirine Pool'),
        ], limit=1)
        
        if not pool_website:
            # Essayer par le domaine
            pool_website = Website.search([
                '|',
                ('domain', 'ilike', 'lolirinepoolstore'),
                ('domain', 'ilike', 'lolirine-pool'),
            ], limit=1)
        
        if pool_website:
            _logger.debug(f"Site Pool Store trouvé: ID={pool_website.id}, nom={pool_website.name}")
            return pool_website.id
        else:
            _logger.warning("Site Pool Store non trouvé - le produit sera visible sur tous les sites")
            return False
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create pour assigner automatiquement le website_id
        aux produits piscine.
        """
        for vals in vals_list:
            # Si c'est un produit piscine et qu'aucun website_id n'est défini
            if vals.get('is_pool_product') and not vals.get('website_id'):
                pool_website_id = self._get_pool_website_id()
                if pool_website_id:
                    vals['website_id'] = pool_website_id
                    _logger.info(f"Produit '{vals.get('name', 'N/A')}' assigné au Pool Store (website_id={pool_website_id})")
        
        return super().create(vals_list)
    
    def write(self, vals):
        """
        Override write pour assigner le website_id si is_pool_product passe à True
        """
        # Si on passe is_pool_product à True
        if vals.get('is_pool_product') and not vals.get('website_id'):
            # Vérifier si les produits n'ont pas déjà un website_id
            products_without_website = self.filtered(lambda p: not p.website_id)
            if products_without_website:
                pool_website_id = self._get_pool_website_id()
                if pool_website_id:
                    vals['website_id'] = pool_website_id
        
        return super().write(vals)
    
    def action_assign_to_pool_website(self):
        """
        Action pour assigner manuellement les produits sélectionnés au site Pool Store.
        Peut être appelée depuis une action serveur ou un bouton.
        """
        pool_website_id = self._get_pool_website_id()
        if not pool_website_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur',
                    'message': 'Site Pool Store non trouvé!',
                    'type': 'danger',
                }
            }
        
        count = 0
        for product in self:
            if not product.website_id:
                product.website_id = pool_website_id
                product.is_pool_product = True
                count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': f'{count} produit(s) assigné(s) au Pool Store',
                'type': 'success',
            }
        }
