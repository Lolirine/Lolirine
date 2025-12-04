# Indemnités Kilométriques pour Odoo 18

Module de gestion des trajets professionnels et calcul automatique des indemnités kilométriques.

## Description

Ce module combine les fonctionnalités des modules **Notes de frais** (`hr_expense`) et **Parc automobile** (`fleet`) pour créer une solution complète de gestion des indemnités kilométriques.

## Fonctionnalités

### Gestion des Trajets
- Enregistrement des trajets avec lieu de départ et d'arrivée
- Support des trajets aller-retour
- Catégorisation des trajets (Client, Prospect, Fournisseur, Formation, etc.)
- Association optionnelle à un client/fournisseur
- Workflow de validation (Brouillon → Soumis → Validé → Remboursé)
- Calendrier des déplacements
- Pièces jointes pour justificatifs (péage, parking, etc.)

### Gestion des Véhicules
- Support des véhicules de société (intégration avec le module Fleet)
- Support des véhicules personnels
- Enregistrement de la puissance fiscale
- Types de véhicules : Voiture, Moto, Cyclomoteur, Vélo/VAE

### Calcul des Indemnités
- Barèmes kilométriques configurables
- Calcul par tranches (0-5000km, 5001-20000km, >20000km)
- Cumul annuel automatique pour le calcul des tranches
- Support du barème belge (forfaitaire) et français (par CV)

### Feuilles d'Indemnités
- Regroupement des trajets par période
- Génération automatique via assistant
- Workflow d'approbation
- Génération de rapports de frais (`hr.expense.sheet`)
- Rapports PDF imprimables

### Rapports et Analyses
- Vue pivot pour l'analyse des trajets
- Graphiques de suivi
- Rapports PDF pour les feuilles IK et les trajets

## Installation

1. Copier le dossier `km_expense` dans le répertoire des addons Odoo
2. Mettre à jour la liste des applications
3. Installer le module "Indemnités Kilométriques"

## Dépendances

- `base`
- `hr` (Ressources Humaines)
- `hr_expense` (Notes de frais)
- `fleet` (Parc automobile)
- `account` (Comptabilité)

## Configuration

### 1. Barèmes Kilométriques
Allez dans **Indemnités KM > Configuration > Barèmes Kilométriques** pour configurer les taux selon votre législation.

Le module est livré avec :
- Barème belge 2024 (0,4280 €/km forfaitaire)
- Barèmes français 2024 (par puissance fiscale, désactivés par défaut)

### 2. Catégories de Trajets
Personnalisez les catégories dans **Indemnités KM > Configuration > Catégories de Trajets**.

### 3. Véhicules
- Pour les véhicules de société : configurez la puissance fiscale dans le module Fleet
- Pour les véhicules personnels : **Indemnités KM > Véhicules > Mes Véhicules Personnels**

## Utilisation

### Créer un Trajet

1. Aller dans **Indemnités KM > Trajets > Mes Trajets**
2. Cliquer sur "Créer"
3. Remplir les informations :
   - Date du trajet
   - Véhicule utilisé (personnel ou société)
   - Lieu de départ et d'arrivée
   - Distance aller (le total est calculé si aller-retour)
   - Catégorie et motif
4. Soumettre pour validation

### Générer une Feuille IK

1. Aller dans **Indemnités KM > Feuilles IK > Générer une Feuille**
2. Sélectionner la période (mois précédent, courant, trimestre, ou personnalisée)
3. Vérifier le nombre de trajets et le montant
4. Cliquer sur "Générer la Feuille"

### Workflow de Validation

**Trajets :**
1. **Brouillon** : Création du trajet
2. **Soumis** : En attente de validation par le manager
3. **Validé** : Approuvé, peut être inclus dans une feuille IK
4. **Remboursé** : Trajet payé

**Feuilles IK :**
1. **Brouillon** : Création de la feuille
2. **Soumis** : En attente d'approbation
3. **Approuvé** : Peut générer un rapport de frais
4. **Payé** : Indemnités versées

## Structure du Module

```
km_expense/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── hr_expense.py      # Extension hr.expense
│   ├── km_bareme.py       # Barèmes kilométriques
│   ├── km_expense.py      # Feuilles d'indemnités
│   ├── km_trajet.py       # Trajets et catégories
│   └── km_vehicule.py     # Véhicules personnels + extension fleet
├── views/
│   ├── km_bareme_views.xml
│   ├── km_expense_menus.xml
│   ├── km_expense_views.xml
│   ├── km_trajet_views.xml
│   └── km_vehicule_views.xml
├── wizard/
│   ├── __init__.py
│   ├── km_expense_generate_wizard.py
│   └── km_expense_generate_wizard_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── km_expense_security.xml
├── data/
│   ├── km_bareme_data.xml
│   └── km_expense_data.xml
├── reports/
│   ├── km_expense_report.xml
│   └── km_expense_report_templates.xml
└── static/
    └── description/
        └── icon.svg
```

## Groupes de Sécurité

- **Utilisateur** : Peut créer et gérer ses propres trajets et véhicules
- **Gestionnaire** : Peut valider les trajets, configurer les barèmes et catégories

## Licence

LGPL-3

## Auteur

Lolirine SPRL - https://www.lolirine.be

## Support

Pour toute question ou demande de fonctionnalité, contactez le support technique.
