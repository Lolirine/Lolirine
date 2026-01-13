# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Biztax - Déclaration ISOC Belgique',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Génération automatique des déclarations ISOC pour Biztax (SPF Finances Belgique)',
    'description': """
Lolirine Biztax - Module de Déclaration Fiscale Belge
=====================================================

Ce module permet de générer automatiquement les déclarations fiscales belges 
conformes à la taxonomie be-tax pour dépôt via Biztax.

Fonctionnalités principales:
----------------------------
* Calcul automatique de la base imposable depuis la comptabilité Odoo
* **Correspondance complète PCMN (Plan Comptable Belge) → XBRL be-tax**
* **Gestion détaillée des mouvements extra-comptables**:
    - DNA (Dépenses Non Admises) avec calcul automatique
    - Amortissements fiscaux vs comptables
    - Provisions non déductibles
    - Plus-values (taxation normale, étalée, immunisée)
    - RDT (Revenus Définitivement Taxés)
    - NID (Intérêts Notionnels / Déduction pour capital à risque)
    - Pertes reportables avec règle du "basket" (1M + 70%)
* **Gestion multi-sociétés avec consolidation groupe**
* **Support multi-devises avec conversion EUR**
* **Gestion des écritures de clôture** (détection et traitement fiscal)
* Génération de fichiers XBRL conformes à la taxonomie be-tax-2025
* Assemblage de fichiers .biztax avec pièces jointes PDF (annexes 275)
* Support des trois types de déclarations:
    - Impôt des sociétés (ISOC/VenB)
    - Impôt des personnes morales (IPM/RPB)
    - Impôt des non-résidents/sociétés (INR/BNI)

DNA pré-configurées (codes belges):
-----------------------------------
* Frais de restaurant: 31% (Art. 53, 8° CIR92)
* Frais de réception: 50% (Art. 53, 7° CIR92)
* Cadeaux d'affaires: 50% (Art. 53, 7° CIR92)
* Amendes: 100% (Art. 53, 6° CIR92)
* Frais de voiture: formule CO2 (Art. 66 CIR92)
* ISOC et impôts similaires: 100% (Art. 198 CIR92)

Taxonomie supportée:
--------------------
* be-tax-2025-04-30 (Exercice d'imposition 2025)
* be-tax-2024-04-30 (Exercice d'imposition 2024)

Workflow:
---------
1. Création d'une déclaration fiscale
2. Importation automatique des données comptables
3. Détection des écritures de clôture
4. Saisie/calcul des ajustements fiscaux
5. Calcul de l'impôt (taux PME 20% / normal 25%)
6. Génération du fichier .biztax
7. Dépôt manuel via l'interface Biztax officielle

Note: Ce module génère les fichiers pour dépôt manuel. 
L'API Biztax ne permet pas de dépôt automatique.
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'l10n_be',
        'account_reports',
    ],
    'data': [
        # Security
        'security/biztax_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/biztax_sequence.xml',
        'data/biztax_tax_codes.xml',
        'data/biztax_account_mapping.xml',
        'data/biztax_pcmn_mapping.xml',
        'data/biztax_annex_registry.xml',
        
        # Wizards (MUST be before views that reference them)
        'wizards/biztax_generate_wizard_views.xml',
        'wizards/biztax_import_wizard_views.xml',
        
        # Views
        'views/biztax_adjustment_views.xml',
        'views/biztax_attachment_views.xml',
        'views/biztax_multicompany_views.xml',
        'views/biztax_company_extended_views.xml',
        'views/biztax_declaration_views.xml',
        'views/biztax_menu.xml',
        'views/res_company_views.xml',
    ],
    'external_dependencies': {
        'python': ['lxml'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
