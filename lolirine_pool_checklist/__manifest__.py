# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Checklist',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Fiche de visite chantier piscine — Lolirine Pool Store',
    'description': """
Fiche de visite chantier interactive pour les techniciens Lolirine Pool Store.

Fonctionnalités :
- 6 types d'intervention : construction, rénovation, entretien, hivernage, remise en route, matériel
- Statut par item : OK / Attention / Problème + note inline + recherche produits
- Recherche catalogue Odoo Pool Store + suggestions IA (proxy serveur Anthropic)
- Autocomplétion client (partenaires Odoo) et adresse (Nominatim BE)
- Création de devis Odoo style Odoo : onglets Lignes / Frais & services / Dropshipping / Notes
- TVA 21% BE — Frais de déplacement auto calculés depuis Boninne (Namur)
- Signatures technicien + client
- Statut de visite et enregistrement (localStorage)
- Impression / PDF optimisé A4
- Accès /visite-chantier réservé aux utilisateurs connectés
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
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
