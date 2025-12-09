# Module Odoo - Plan Interactif Garde-Meubles

## Description

Ce module Odoo permet de gérer un garde-meubles avec un plan interactif accessible en ligne. Les clients peuvent visualiser les boxes disponibles, consulter leurs caractéristiques et effectuer des réservations directement depuis le site web.

## Fonctionnalités principales

### Backend (Administration)
- **Gestion des étages** : Configuration des différents niveaux du garde-meubles
- **Gestion des boxes** : 
  - Informations détaillées (dimensions, volume, prix)
  - Statuts multiples (disponible, occupé, maintenance, etc.)
  - Positionnement sur le plan (grille)
- **Gestion des réservations** :
  - Demandes de rendez-vous
  - Réservations immédiates
  - Suivi des états (en attente, confirmé, en cours, terminé)

### Frontend (Site web public)
- **Plan interactif** :
  - Visualisation des deux étages (rez-de-chaussée et premier étage)
  - Code couleur selon le statut des boxes
  - Légende interactive
  - Clic sur les boxes disponibles pour plus de détails

- **Modal de détails** :
  - Visualisation 3D isométrique du box
  - Dimensions complètes (largeur, profondeur, hauteur)
  - Volume en m³
  - Prix mensuel
  - Frais de dossier et caution
  - Statut en temps réel

- **Système de réservation** :
  - Formulaire de prise de rendez-vous
  - Formulaire de réservation immédiate
  - Validation des données
  - Confirmation par email (à configurer)

## Installation

### Prérequis
- Odoo 15.0, 16.0 ou 17.0
- Module `website` installé
- Module `portal` installé

### Étapes d'installation

1. **Copier le module dans votre répertoire addons** :
   ```bash
   cp -r storage_plan_module /path/to/odoo/addons/
   ```

2. **Mettre à jour la liste des modules** :
   - Aller dans Apps / Mise à jour de la liste des applications

3. **Installer le module** :
   - Rechercher "Plan Interactif Garde-Meubles"
   - Cliquer sur "Installer"

4. **Configuration initiale** :
   - Le module crée automatiquement 2 étages et quelques boxes d'exemple
   - Aller dans Garde-Meubles > Configuration pour personnaliser

## Configuration

### 1. Configuration des étages

Aller dans `Garde-Meubles > Boxes > Étages`

- Créer ou modifier les étages
- Définir le nom et le code (ex: "RDC", "R1")
- Définir la séquence d'affichage

### 2. Configuration des boxes

Aller dans `Garde-Meubles > Boxes > Tous les boxes`

Pour chaque box, définir :
- **Informations générales** :
  - Numéro du box
  - Étage
  - Statut initial

- **Dimensions** :
  - Largeur (cm)
  - Profondeur (cm)
  - Hauteur (cm)
  - Le volume se calcule automatiquement

- **Tarification** :
  - Prix mensuel
  - Frais de dossier (par défaut 15€)
  - Nombre de mois de caution (par défaut 2)

- **Position sur le plan** :
  - Ligne de la grille (grid_row)
  - Colonne de la grille (grid_col)
  - Ces valeurs définissent la position visuelle du box

### 3. Personnalisation du plan

Le plan utilise une grille CSS. Pour adapter la disposition :

1. Modifier le fichier CSS (`static/src/css/storage_plan.css`)
2. Ajuster les propriétés `grid-template-columns` et `grid-template-rows`
3. Adapter les positions des boxes via les champs `grid_row` et `grid_col`

## Utilisation

### Pour les administrateurs

1. **Gérer les boxes** :
   - Créer/modifier/archiver des boxes
   - Changer les statuts manuellement
   - Ajouter des notes internes

2. **Gérer les réservations** :
   - Voir toutes les demandes
   - Confirmer les réservations
   - Marquer comme "en cours" quand le client emménage
   - Terminer la réservation quand le client libère le box
   - Annuler si nécessaire

3. **Statistiques** :
   - Nombre de boxes par étage
   - Nombre de boxes disponibles
   - Taux d'occupation

### Pour les clients (site web)

1. **Consulter le plan** :
   - Accéder à `/storage/plan`
   - Visualiser les boxes disponibles (verts)
   - Voir les boxes occupés (roses) et en maintenance (jaunes)

2. **Réserver un box** :
   - Cliquer sur un box disponible (vert)
   - Consulter les détails et la visualisation 3D
   - Choisir entre "Prendre rendez-vous" ou "Réserver maintenant"
   - Remplir le formulaire de contact
   - Recevoir une confirmation

## Structure du module

```
storage_plan_module/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── storage_floor.py          # Modèle des étages
│   ├── storage_box.py             # Modèle des boxes
│   └── box_reservation.py         # Modèle des réservations
├── controllers/
│   ├── __init__.py
│   └── main.py                    # Contrôleur web (routes)
├── views/
│   ├── storage_floor_views.xml    # Vues backend étages
│   ├── storage_box_views.xml      # Vues backend boxes
│   ├── box_reservation_views.xml  # Vues backend réservations
│   ├── website_storage_plan_templates.xml  # Template web
│   └── menus.xml                  # Menus du backend
├── security/
│   └── ir.model.access.csv        # Droits d'accès
├── static/
│   └── src/
│       ├── css/
│       │   └── storage_plan.css   # Styles CSS
│       └── js/
│           └── storage_plan.js    # JavaScript interactif
└── data/
    └── floor_data.xml             # Données d'exemple
```

## API / Routes disponibles

### Routes publiques

- `GET /storage/plan` : Affiche le plan interactif
- `POST /storage/box/<id>/details` : Récupère les détails d'un box (JSON-RPC)
- `POST /storage/box/<id>/reserve` : Crée une réservation (JSON-RPC)
- `POST /storage/box/<id>/appointment` : Crée une demande de RDV (JSON-RPC)
- `POST /storage/boxes/search` : Recherche de boxes selon critères (JSON-RPC)

## Personnalisation

### Couleurs des statuts

Modifier dans `storage_box.py`, méthode `get_status_color()` :

```python
colors = {
    'disponible': '#90EE90',  # Vert clair
    'occupe': '#FFB6C1',       # Rose
    'maintenance': '#FFFF99',  # Jaune
    # ... etc
}
```

### Visualisation 3D

Le rendu 3D utilise HTML5 Canvas avec projection isométrique. Pour modifier :
- Éditer `static/src/js/storage_plan.js`
- Modifier la fonction `_draw3DBox()`

### Email de confirmation

Pour activer l'envoi d'emails automatiques :
1. Configurer le serveur SMTP dans Odoo (Paramètres > Technique > Email)
2. Créer un template d'email
3. Ajouter l'envoi dans le modèle `box_reservation.py`

## Support et contribution

Pour toute question ou suggestion :
- Email : contact@lolirine.be
- Développé par Lolirine SPRL

## Licence

Propriétaire - Lolirine SPRL © 2024

## Changelog

### Version 1.0 (2024-12-01)
- Première version
- Plan interactif avec 2 étages
- Visualisation 3D des boxes
- Système de réservation en ligne
- Interface d'administration complète
