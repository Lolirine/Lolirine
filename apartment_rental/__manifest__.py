# -*- coding: utf-8 -*-
{
    'name': 'Gestion Locative Appartement',
    'version': '19.0.1.0.2',
    'category': 'Real Estate',
    'summary': 'Gestion complète de location d\'appartement - Loyer, indexation, états des lieux, visites de contrôle',
    'description': """
Gestion Locative Appartement pour Lolirine SPRL
================================================

Module complet de gestion locative conforme à la législation belge:

**Gestion du bien**
* Fiche détaillée de l'appartement
* Photos et documentation
* Caractéristiques et équipements

**Gestion des baux**
* Contrats de location
* Indexation automatique (indice santé belge)
* Historique des locataires

**États des lieux**
* État des lieux d'entrée avec photos
* État des lieux de sortie avec photos
* Comparaison entrée/sortie
* Génération de rapports PDF

**Visites de contrôle**
* Planification des visites périodiques
* Photos et observations
* Suivi des anomalies

**Gestion financière**
* Génération des loyers
* Suivi des paiements
* Gestion des charges
* Relevés de compteurs

**Alertes et rappels**
* Fin de bail
* Indexation annuelle
* Visites de contrôle
* Loyers impayés
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'calendar',
        'account',
    ],
    'data': [
        # Security
        'security/apartment_rental_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'data/apartment_room_type_data.xml',
        # Views
        'views/apartment_property_views.xml',
        'views/apartment_tenant_views.xml',
        'views/apartment_lease_views.xml',
        'views/apartment_inventory_views.xml',
        'views/apartment_control_visit_views.xml',
        'views/apartment_rent_views.xml',
        'views/apartment_meter_views.xml',
        'views/apartment_intervention_views.xml',
        'views/apartment_document_views.xml',
        'views/apartment_index_history_views.xml',
        'views/apartment_maintenance_contract_views.xml',
        'views/apartment_menuitem.xml',
        # Wizards
        'wizard/apartment_generate_rent_wizard_views.xml',
        'wizard/apartment_indexation_wizard_views.xml',
        # Reports
        'report/apartment_inventory_report.xml',
        'report/apartment_inventory_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'apartment_rental/static/src/css/apartment_rental.css',
        ],
    },
    'demo': [
        'data/apartment_demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
