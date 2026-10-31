# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool — Devis Piscine',
    'version': '19.0.3.0.0',
    'category': 'Sales',
    'summary': 'Devis piscine : ouvrages, conditions de paiement, marge, autoliquidation, chantier',
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
        - Tableau de main-d'œuvre et bouton « Ajouter une prestation » (heures internes)
        - Ouvrages : fournitures liées aux prestations, options, enregistrement depuis un devis
        - Conditions de paiement calculées (PDF et devis en ligne), acompte en ligne = part matériel
        - Marge matériel avant commande (alerte sous 15 % ou coût inconnu)
        - Autoliquidation (régime du cocontractant) pour les travaux immobiliers B2B
        - Main-d'œuvre à l'avancement, chantier (projet) à la confirmation, pointage des heures
        - Fiche de visite technique avec photos
        - Avenants (travaux supplémentaires) liés au chantier, relances automatiques des devis
        - Procès-verbal de réception signé sur place, parc installé et garanties
        - Devis d'hivernage et de remise en route, campagnes saisonnières automatiques
        - Tableau de bord des chantiers, dossier documents du chantier
    """,
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'sale', 'purchase', 'sale_margin', 'sale_project', 'hr_timesheet',
                'lolirine_pool_dropship'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/sale_template.xml',
        'views/sale_order_views.xml',
        'views/pool_prestation_views.xml',
        'data/pool_prestation_data.xml',
        'data/project_chantier_data.xml',
        'data/pool_chantier_data.xml',
        'views/pool_devis_outils_views.xml',
        'views/portal_templates.xml',
        'views/pool_parc_pv_views.xml',
        'views/pool_chantier_views.xml',
        'reports/pool_devis_report.xml',
        'reports/pool_pv_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': ['static/description/icon.png'],
}
