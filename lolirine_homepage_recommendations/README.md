# Lolirine Homepage Recommendations

Module Odoo 19 de recommandations personnalisées inspiré d'Amazon pour la page d'accueil.

## 🎯 Fonctionnalités

### Sections de recommandations disponibles

1. **Produits récemment consultés** - Historique de navigation du visiteur
2. **Continuez vos achats** - Paniers abandonnés et produits liés aux achats
3. **Meilleures ventes** - Produits les plus vendus (30 derniers jours)
4. **Les mieux notés** - Produits avec 4+ étoiles
5. **Offres du moment** - Produits en promotion
6. **Nouveautés** - Derniers produits ajoutés
7. **En lien avec vos consultations** - Produits similaires à l'historique
8. **Pour vous dans [Catégorie]** - Recommandations par catégorie préférée
9. **Grille de catégories** - Navigation visuelle des catégories

### Caractéristiques techniques

- ✅ Tracking automatique des vues de produits
- ✅ Carrousels responsives avec navigation
- ✅ Skeleton loaders pendant le chargement
- ✅ Boutons d'ajout rapide au panier et wishlist
- ✅ Support visiteurs anonymes et connectés
- ✅ Configurable via le Website Builder
- ✅ Nettoyage automatique des anciennes données (cron)
- ✅ Calcul des préférences par catégorie

## 📦 Installation

### Prérequis
- Odoo 19 Enterprise
- Modules requis : `website_sale`, `website_sale_wishlist`, `sale`, `product`, `rating`

### Étapes

1. Copier le dossier `lolirine_homepage_recommendations` dans votre répertoire `custom_addons`

2. Mettre à jour la liste des modules :
```bash
./odoo-bin -u all -d votre_base --stop-after-init
```

3. Installer le module via l'interface Odoo :
   - Allez dans Apps
   - Cherchez "Lolirine Homepage Recommendations"
   - Cliquez sur Installer

## 🚀 Utilisation

### Ajouter une section à la page d'accueil

1. Allez sur votre site web → Page d'accueil
2. Cliquez sur **Éditer**
3. Dans le panneau des snippets, cherchez les nouveaux blocs :
   - "Recommandations Produits"
   - "Produits Récemment Consultés"
   - "Continuez vos achats"
   - etc.
4. Glissez-déposez le snippet souhaité sur la page
5. Cliquez sur le snippet pour voir les options de configuration

### Options de configuration (Website Builder)

- **Type de recommandation** : Choisir parmi les 8 types
- **Nombre de produits** : 1-20 produits à afficher
- **Catégorie** : Filtrer par catégorie spécifique
- **Masquer si vide** : Cacher la section s'il n'y a pas de produits
- **Afficher % réduction** : Badge de réduction sur les promos
- **Badge personnalisé** : Texte du badge (Nouveau, Promo, etc.)

### Exemple de configuration recommandée pour une homepage e-commerce

```
1. [Banner principal]
2. Produits récemment consultés (si connecté)
3. Offres du moment
4. Meilleures ventes
5. Nouveautés
6. Les mieux notés
7. Grille de catégories
```

## 🔧 Configuration avancée

### Personnaliser les algorithmes

Les algorithmes de recommandation sont dans `models/product_recommendation.py`. Vous pouvez ajuster :

- La période pour les meilleures ventes (défaut: 30 jours)
- Le seuil de notation minimum (défaut: 4 étoiles)
- Les pondérations pour le calcul des préférences

### Crons

Deux tâches planifiées sont créées :

1. **Nettoyage des activités** (hebdomadaire) - Supprime les vues > 90 jours
2. **Calcul des préférences** (quotidien) - Recalcule les scores de catégories

### API Endpoints

- `POST /shop/track/view` - Tracker une vue produit
- `POST /shop/recommendations` - Récupérer des recommandations
- `POST /shop/recommendations/all` - Récupérer toutes les recommandations
- `POST /shop/preferences/categories` - Récupérer les catégories préférées

## 📊 Structure du module

```
lolirine_homepage_recommendations/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py                    # API endpoints
├── data/
│   └── ir_cron_data.xml           # Tâches planifiées
├── models/
│   ├── __init__.py
│   ├── product_recommendation.py  # Algorithmes de recommandation
│   └── visitor_activity.py        # Tracking des activités
├── security/
│   └── ir.model.access.csv        # Droits d'accès
├── static/src/
│   ├── img/                       # Thumbnails des snippets
│   ├── js/
│   │   ├── homepage_recommendations.js  # Widgets frontend
│   │   └── snippets_options.js          # Options éditeur
│   └── scss/
│       └── homepage_recommendations.scss # Styles
└── views/
    ├── snippets/
    │   ├── homepage_recommendations.xml  # Templates snippets
    │   └── options.xml                   # Options snippets
    └── website_templates.xml             # Injection tracking
```

## 🎨 Personnalisation du style

Les variables SCSS principales sont dans `static/src/scss/homepage_recommendations.scss` :

```scss
$card-width: 200px;        // Largeur des cartes produit
$card-width-sm: 160px;     // Largeur mobile
$card-gap: 16px;           // Espacement entre cartes
$card-border-radius: 8px;  // Arrondi des cartes
```

## 🐛 Dépannage

### Les recommandations ne s'affichent pas

1. Vérifier que le module est bien installé et activé
2. Vérifier que des produits sont publiés sur le website
3. Ouvrir la console du navigateur pour voir les erreurs JS

### Le tracking ne fonctionne pas

1. Vérifier que la page produit hérite bien du template `website_sale.product`
2. Vérifier les permissions de l'utilisateur public

### Les sections sont vides

- Les sections personnalisées (récemment vus, continue shopping) nécessitent de l'activité utilisateur
- Utilisez les options "Masquer si vide" pour une meilleure expérience

## 📄 Licence

LGPL-3

## 👨‍💻 Auteur

Lolirine SPRL - https://www.lolirine.be
