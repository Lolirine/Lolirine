# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Checklist',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Fiche de visite chantier piscine — Lolirine Pool Store',
    'description': """
        Fiche de visite chantier interactive pour les techniciens Lolirine Pool Store.

        Fonctionnalités :
        - 6 types d'intervention (construction, rénovation, entretien, hivernage, remise en route, matériel)
        - Statut par item : ✅ OK / ⚠️ Attention / ❌ Problème + note inline + bouton produits
        - Recherche produits dans le catalogue Odoo (website_id=6)
        - Suggestions IA via proxy serveur (clé API dans ir.config_parameter)
        - Autocomplétion client (partenaires Odoo) et adresse (Nominatim BE)
        - Création de devis Odoo directement depuis la fiche
        - Devis style Odoo : 4 onglets (Lignes, Frais & services, Dropshipping, Notes)
        - TVA 21% BE · Frais déplacement auto depuis Boninne · Main d'œuvre
        - Section signatures technicien + client
        - Enregistrement avec statut de visite (localStorage)
        - Impression / PDF
        - Accès réservé aux utilisateurs internes (/visite-chantier)
    """,
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': ['website', 'website_sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/menu.xml',
    ],
    'assets': {
        'lolirine_pool_checklist.assets_checklist': [
            'lolirine_pool_checklist/static/src/css/pool_checklist.css',
            'lolirine_pool_checklist/static/src/js/pool_checklist.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
