# ACT365 Integration pour Odoo 18

Module d'intégration entre Odoo 18 (module Abonnements) et le système de contrôle d'accès ACT365 de Vanderbilt/ACRE.

## 🎯 Fonctionnalités

- **Attribution automatique de codes PIN** aux abonnés du garde-meubles
- **Synchronisation bidirectionnelle** avec ACT365 (création/mise à jour des cardholders)
- **Gestion des groupes d'accès** ACT365 depuis Odoo
- **Affichage du code d'accès** sur la fiche client ET sur l'abonnement
- **Activation/Désactivation automatique** selon l'état de l'abonnement
- **Interface intuitive** avec boutons d'action directe

## 📋 Prérequis

- Odoo 18 Community ou Enterprise
- Module `sale_subscription` installé
- Compte ACT365 avec accès API activé
- Python packages: `requests` (normalement inclus)

## 🔧 Installation

1. **Copier le module** dans le répertoire des addons Odoo:
   ```bash
   cp -r act365_integration /path/to/odoo/addons/
   ```

2. **Mettre à jour la liste des modules**:
   - Aller dans Apps
   - Cliquer sur "Mettre à jour la liste des apps"

3. **Installer le module**:
   - Rechercher "ACT365"
   - Cliquer sur "Installer"

## ⚙️ Configuration

### 1. Obtenir la clé API ACT365

1. Connectez-vous à [ACT365](https://www.act365.eu)
2. Allez dans **Profile** > **Apps & Integrations**
3. Cliquez sur **Generate API Key**
4. Copiez la clé générée

### 2. Configurer le module dans Odoo

1. Aller dans **Paramètres** > **ACT365**
2. Renseigner:
   - **URL API**: `https://api.act365.eu` (par défaut)
   - **Clé API**: Coller votre clé API
3. Cliquer sur **Tester la connexion** pour vérifier
4. Cliquer sur **Synchroniser les groupes** pour importer les groupes ACT365
5. Sélectionner le **Groupe par défaut** pour les nouveaux abonnés

### 3. Options d'automatisation

- **Synchronisation automatique**: Crée automatiquement le cardholder lors de la validation
- **Activer à la confirmation**: Active l'accès dès la confirmation de l'abonnement
- **Désactiver à la clôture**: Désactive l'accès lors de la résiliation

## 📖 Utilisation

### Attribuer un code d'accès

1. Ouvrir un **abonnement** (Ventes > Abonnements)
2. Cliquer sur le bouton **🔑 Code ACT365** en haut
3. Dans le wizard:
   - Choisir le mode de génération (auto ou manuel)
   - Sélectionner le groupe ACT365
   - Définir les dates de validité (optionnel)
   - Cocher "Synchroniser immédiatement" pour créer dans ACT365
4. Cliquer sur **✓ Attribuer le code**

### Gérer l'accès

Dans l'onglet **Accès ACT365** de l'abonnement:

- **🔄 Synchroniser**: Met à jour le cardholder dans ACT365
- **✓ Activer l'accès**: Active le cardholder
- **✗ Désactiver l'accès**: Désactive temporairement l'accès
- **ℹ️ Infos ACT365**: Affiche les informations du cardholder

### Consulter le code d'accès d'un client

Le code d'accès est visible:
- Sur la **fiche client** (onglet "Accès Garde-Meubles")
- Sur l'**abonnement** (onglet "Accès ACT365")
- Dans la **liste des abonnements** (colonne optionnelle)

## 🔒 Sécurité

- Les codes PIN sont générés aléatoirement et évitent les séquences simples (0000, 1234, etc.)
- Les clés API sont stockées de manière sécurisée dans les paramètres système
- Les communications avec ACT365 utilisent HTTPS/SSL

## 🛠️ Support technique

### Endpoints API utilisés

Le module utilise les endpoints REST ACT365 suivants:

```
GET    /api/v1/cardholders                  # Liste des cardholders
POST   /api/v1/cardholders                  # Créer un cardholder
PUT    /api/v1/cardholders/{id}             # Mettre à jour
PATCH  /api/v1/cardholders/{id}/enable      # Activer
PATCH  /api/v1/cardholders/{id}/disable     # Désactiver
DELETE /api/v1/cardholders/{id}             # Supprimer

GET    /api/v1/cardholders/{id}/credentials # Credentials
POST   /api/v1/cardholders/{id}/credentials # Ajouter credential

GET    /api/v1/cardholdergroups             # Liste des groupes
```

### Logs

Les interactions avec l'API sont loggées avec le niveau INFO:
```
ACT365 API Request: POST /api/v1/cardholders
ACT365 API Response: 201
```

Pour activer le debug:
```bash
./odoo-bin --log-handler=odoo.addons.act365_integration:DEBUG
```

## 📝 Notes de version

### v18.0.1.0.0
- Version initiale
- Support complet des cardholders et credentials PIN
- Intégration avec le module abonnements Odoo 18
- Interface utilisateur avec wizard d'attribution

## 📄 Licence

LGPL-3.0

## 👤 Auteur

Lolirine SPRL - [www.lolirine.be](https://www.lolirine.be)
