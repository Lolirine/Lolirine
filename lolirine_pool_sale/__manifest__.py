# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool — Devis Piscine',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Devis piscine avec séquence dédiée, onglets chantier et dropshipping',
    'description': """
        Extension du module Ventes pour les devis piscine Lolirine Pool Store.

        Fonctionnalités :
        - Séquence dédiée PSC/AAAA/XXXXX pour les devis piscine
        - Champ "Devis piscine" (booléen) sur sale.order
        - Onglet "🏊 Chantier" : type intervention, adresse, bassin (forme/L/l/prof), technicien
        - Onglet "🚚 Dropshipping" : fournisseur, référence commande, délai, livraison directe
        - Onglet "📋 Fiche de visite" : statut visite, lien fiche, observations
        - Masquage des onglets Contrat / Indexation sur les devis piscine
        - Bouton "Ouvrir la fiche de visite" depuis le devis
        - Widget de récapitulatif chantier dans le chatter
    """,
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/sale_template.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': ['static/description/icon.png'],
}
