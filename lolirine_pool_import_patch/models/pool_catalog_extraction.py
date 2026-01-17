# -*- coding: utf-8 -*-
"""
Patch pour lolirine_pool_import - Assignation automatique du website_id

Ce fichier montre les modifications à apporter à pool_catalog_extraction.py
pour que les produits importés soient automatiquement assignés au site "Lolirine Pool Store"

INSTRUCTIONS:
1. Dans la méthode action_import_to_odoo() ou _prepare_product_vals()
2. Ajouter le code ci-dessous pour récupérer et assigner le website_id
"""

import logging
_logger = logging.getLogger(__name__)

# ============================================================================
# CODE À AJOUTER AU DÉBUT DE LA MÉTHODE DE CRÉATION DE PRODUIT
# ============================================================================

def _get_pool_website_id(self):
    """
    Récupère l'ID du site web Pool Store.
    À appeler avant la création du produit.
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
        _logger.info(f"Site Pool Store trouvé: ID={pool_website.id}, nom={pool_website.name}")
        return pool_website.id
    else:
        _logger.warning("Site Pool Store non trouvé - le produit sera visible sur tous les sites")
        return False


# ============================================================================
# MODIFICATION DES VALS DE CRÉATION DE PRODUIT
# ============================================================================

# Dans la méthode qui prépare les vals du produit, ajouter :

"""
# === AJOUTER CES LIGNES DANS _prepare_product_vals() ou action_import_to_odoo() ===

# Marquer comme produit piscine
vals['is_pool_product'] = True

# Assigner au site web Pool Store
pool_website_id = self._get_pool_website_id()
if pool_website_id:
    vals['website_id'] = pool_website_id

# ================================================================================
"""


# ============================================================================
# EXEMPLE COMPLET DE MÉTHODE MODIFIÉE
# ============================================================================

def action_import_to_odoo_MODIFIED(self):
    """
    Exemple de méthode modifiée avec assignation automatique du website_id
    """
    self.ensure_one()
    
    _logger.info(f"=== Début import produit OCR ID={self.id}, nom={self.name} ===")
    
    ProductTemplate = self.env['product.template']
    
    # Préparer les valeurs de base
    ref_code = self.reference or self.type_code or str(self.id)
    
    vals = {
        'name': self.name or 'Produit sans nom',
        'default_code': f"POOL-{ref_code}",
        'description_sale': self.description_fr or '',
        'standard_price': float(self.purchase_price or 0),
        'list_price': float(self.selling_price or 0),
        'sale_ok': True,
        'purchase_ok': True,
        'type': 'consu',
    }
    
    # =====================================================
    # NOUVEAU : Marquer comme produit piscine + website_id
    # =====================================================
    
    # Marquer comme produit piscine (pour le filtrage multi-site)
    if 'is_pool_product' in ProductTemplate._fields:
        vals['is_pool_product'] = True
    
    # Assigner au site web Pool Store uniquement
    if 'website_id' in ProductTemplate._fields:
        pool_website_id = self._get_pool_website_id()
        if pool_website_id:
            vals['website_id'] = pool_website_id
            _logger.info(f"Produit assigné au site Pool Store (ID={pool_website_id})")
    
    # =====================================================
    # FIN NOUVEAU CODE
    # =====================================================
    
    # Catégorie
    if self.category_id:
        vals['categ_id'] = self.category_id.id
    
    # Image
    if self.image_data:
        vals['image_1920'] = self.image_data
    
    _logger.info(f"Création du produit avec vals: {list(vals.keys())}")
    
    # Créer le produit
    product = ProductTemplate.create(vals)
    
    self.write({
        'created_product_id': product.id,
        'state': 'imported',
    })
    
    _logger.info(f"Produit créé: ID={product.id}, nom={product.name}")
    
    return product


# ============================================================================
# ALTERNATIVE : MÉTHODE POUR ASSIGNER EN MASSE LES PRODUITS EXISTANTS
# ============================================================================

def assign_existing_pool_products_to_website(self):
    """
    Méthode utilitaire pour assigner tous les produits piscine existants
    au site web Pool Store.
    
    À exécuter une seule fois via le shell Odoo :
    
    >>> self.env['product.template'].assign_existing_pool_products_to_website()
    """
    Website = self.env['website']
    ProductTemplate = self.env['product.template']
    
    # Trouver le site Pool Store
    pool_website = Website.search([
        '|',
        ('name', 'ilike', 'Pool Store'),
        ('name', 'ilike', 'Lolirine Pool'),
    ], limit=1)
    
    if not pool_website:
        _logger.error("Site Pool Store non trouvé!")
        return False
    
    # Trouver tous les produits piscine sans website_id
    pool_products = ProductTemplate.search([
        ('is_pool_product', '=', True),
        ('website_id', '=', False),
    ])
    
    if pool_products:
        pool_products.write({'website_id': pool_website.id})
        _logger.info(f"{len(pool_products)} produits assignés au site Pool Store")
        return len(pool_products)
    else:
        _logger.info("Aucun produit piscine à assigner")
        return 0
