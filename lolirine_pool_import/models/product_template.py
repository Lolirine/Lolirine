# -*- coding: utf-8 -*-
"""
Extension de product.template pour le module Pool Import
Inclut tous les champs techniques et l'assignation automatique au Pool Store
"""

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # ==========================================
    # Champ pour le multi-site Pool Store
    # ==========================================
    is_pool_product = fields.Boolean(
        string='Produit Piscine',
        default=False,
        help="Coché automatiquement pour les produits importés via le module Pool Import"
    )
    
    # ==========================================
    # Champs Fournisseur
    # ==========================================
    x_pool_supplier_id = fields.Many2one(
        'pool.supplier',
        string='Fournisseur Piscine',
        help="Fournisseur piscine associé à ce produit"
    )
    x_pool_supplier_ref = fields.Char(
        string='Réf. Fournisseur',
        help="Référence du produit chez le fournisseur piscine"
    )
    x_pool_brand = fields.Char(
        string='Marque',
        help="Marque du produit"
    )
    x_pool_category = fields.Char(
        string='Catégorie Catalogue',
        help="Catégorie dans le catalogue fournisseur"
    )
    x_pool_subcategory = fields.Char(
        string='Sous-catégorie',
        help="Sous-catégorie dans le catalogue fournisseur"
    )
    
    # ==========================================
    # Champs Rentabilité
    # ==========================================
    x_purchase_margin = fields.Float(
        string='Marge achat (%)',
        help="Pourcentage de marge sur le prix d'achat"
    )
    x_profit_amount = fields.Float(
        string='Bénéfice',
        help="Montant du bénéfice par unité"
    )
    
    # ==========================================
    # Spécifications Techniques
    # ==========================================
    x_power_kw = fields.Float(
        string='Puissance (kW)',
        help="Puissance en kilowatts"
    )
    x_power_cv = fields.Float(
        string='Puissance (CV)',
        help="Puissance en chevaux-vapeur"
    )
    x_voltage = fields.Char(
        string='Tension (V)',
        help="Tension électrique"
    )
    x_flow_rate = fields.Float(
        string='Débit (m³/h)',
        help="Débit en mètres cubes par heure"
    )
    x_diameter_mm = fields.Float(
        string='Diamètre (mm)',
        help="Diamètre en millimètres"
    )
    x_filter_area = fields.Float(
        string='Surface filtration (m²)',
        help="Surface de filtration en mètres carrés"
    )
    x_cop = fields.Float(
        string='COP',
        help="Coefficient de performance"
    )
    x_noise_level = fields.Float(
        string='Niveau sonore (dB)',
        help="Niveau sonore en décibels"
    )
    
    # ==========================================
    # Descriptions multilingues
    # ==========================================
    x_description_fr = fields.Text(
        string='Description (FR)',
        help="Description en français"
    )
    x_description_nl = fields.Text(
        string='Description (NL)',
        help="Description en néerlandais"
    )
    
    # ==========================================
    # Champs Import
    # ==========================================
    x_pool_import_date = fields.Datetime(
        string="Date d'import",
        help="Date d'importation du produit"
    )
    x_pool_import_source = fields.Char(
        string="Source d'import",
        help="Source de l'importation (catalogue, fichier, etc.)"
    )
    
    # ==========================================
    # Méthodes pour le multi-site
    # ==========================================
    @api.model
    def _get_pool_website_id(self):
        """
        Récupère l'ID du site web Pool Store.
        """
        Website = self.env['website']
        
        pool_website = Website.search([
            '|',
            ('name', 'ilike', 'Pool Store'),
            ('name', 'ilike', 'Lolirine Pool'),
        ], limit=1)
        
        if not pool_website:
            pool_website = Website.search([
                '|',
                ('domain', 'ilike', 'lolirinepoolstore'),
                ('domain', 'ilike', 'lolirine-pool'),
            ], limit=1)
        
        if pool_website:
            _logger.debug(f"Site Pool Store trouvé: ID={pool_website.id}, nom={pool_website.name}")
            return pool_website.id
        else:
            _logger.warning("Site Pool Store non trouvé")
            return False
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create pour assigner automatiquement le website_id
        aux produits piscine.
        """
        for vals in vals_list:
            if vals.get('is_pool_product') and not vals.get('website_id'):
                pool_website_id = self._get_pool_website_id()
                if pool_website_id:
                    vals['website_id'] = pool_website_id
                    _logger.info(f"Produit '{vals.get('name', 'N/A')}' assigné au Pool Store")
        
        return super().create(vals_list)
    
    def write(self, vals):
        """
        Override write pour assigner le website_id si is_pool_product passe à True
        """
        if vals.get('is_pool_product') and not vals.get('website_id'):
            products_without_website = self.filtered(lambda p: not p.website_id)
            if products_without_website:
                pool_website_id = self._get_pool_website_id()
                if pool_website_id:
                    vals['website_id'] = pool_website_id
        
        return super().write(vals)
    
    def action_assign_to_pool_website(self):
        """
        Action pour assigner manuellement les produits sélectionnés au site Pool Store.
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
