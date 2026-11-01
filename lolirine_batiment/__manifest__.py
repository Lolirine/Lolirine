# -*- coding: utf-8 -*-
{
    'name': 'Lolirine — Devis Bâtiment',
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': 'Devis et chantiers bâtiment : ouvrages au métré, TVA 6 % / 21 %, avancement, procès-verbal',
    'description': """
        Devis bâtiment au nom de Lolirine SRL, sur la base des outils de chantier des devis piscine.

        - Menu Ventes > Bâtiment : devis et chantiers, tableau de bord, procès-verbaux, ouvrages, matériaux
        - Numérotation BAT/AAAA/NNNN, onglet chantier (adresse, description, visite, photos)
        - Ouvrages au m², au mètre, au m³, à la pièce ou au forfait : fournitures au métré avec perte
        - TVA au choix : 21 %, 6 % rénovation (attestation imprimée sur le devis), autoliquidation
        - Conditions de paiement, marge, avenants, relances, procès-verbal, chantier et pointage
    """,
    'author': 'Lolirine SRL',
    'license': 'LGPL-3',
    'depends': ['lolirine_pool_sale'],
    'data': [
        'data/batiment_data.xml',
        'data/batiment_prestations.xml',
        'views/batiment_views.xml',
        'reports/sale_report.xml',
    ],
    'installable': True,
    'application': False,
    'images': ['static/description/icon.png'],
}
