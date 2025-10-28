# Module Box Contact Redirect pour Odoo

## Description

Ce module personnalisé permet de remplacer le bouton "Ajouter au panier" par un bouton "Nous contacter" pour les box de garde-meubles disponibles qui nécessitent un contact préalable.

## Fonctionnalités

- Ajout de deux champs sur le produit :
  - **Box disponible** : indique si le box est actuellement disponible
  - **Rediriger vers contact** : active le remplacement du bouton d'achat par un bouton de contact
  
- Remplacement automatique du bouton "Ajouter au panier" par "Nous contacter" sur :
  - La page détail du produit
  - La grille de produits (vue liste/catalogue)
  
- Redirection vers le formulaire de contact avec pré-remplissage des informations du box

## Installation sur Odoo.sh avec Git

### 1. Préparer le dépôt Git

```bash
# Dans votre dépôt Git local pour Odoo.sh
cd /chemin/vers/votre/depot/odoo-sh

# Créer le dossier du module dans le répertoire approprié
# (généralement dans un dossier 'addons' ou directement à la racine)
mkdir -p box_contact_redirect

# Copier les fichiers du module
cp -r /chemin/vers/box_contact_redirect/* box_contact_redirect/
```

### 2. Structure du module

Assurez-vous que votre module a la structure suivante :

```
box_contact_redirect/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── models/
│   ├── __init__.py
│   └── product_template.py
└── views/
    ├── product_template_views.xml
    └── website_sale_templates.xml
```

### 3. Pousser vers Git

```bash
# Ajouter les fichiers au dépôt
git add box_contact_redirect/

# Commit
git commit -m "Ajout du module box_contact_redirect pour gestion des contacts box"

# Pousser vers Odoo.sh
git push origin master  # ou le nom de votre branche (production, staging, etc.)
```

### 4. Installation dans Odoo

1. Connectez-vous à votre instance Odoo.sh
2. Allez dans **Apps** (Applications)
3. Cliquez sur **Mettre à jour la liste des applications**
4. Recherchez "Box Contact Redirect"
5. Cliquez sur **Installer**

## Configuration et utilisation

### 1. Configurer un produit

1. Allez dans **Ventes > Produits > Produits**
2. Ouvrez le produit (box) que vous souhaitez configurer
3. Dans l'onglet **Ventes**, vous trouverez une nouvelle section "Gestion Box" avec :
   - **Box disponible** : cochez cette case si le box est disponible
   - **Rediriger vers contact** : cochez cette case pour remplacer le bouton d'achat par un bouton de contact

### 2. Résultat sur le site web

Lorsqu'un visiteur consulte un box configuré avec ces options :
- Sur la page produit : un bouton "Nous contacter pour ce box" remplace le bouton "Ajouter au panier"
- Dans le catalogue : un bouton "Nous contacter" remplace le bouton d'achat rapide
- Le clic redirige vers le formulaire de contact avec le nom du box pré-rempli

## Compatibilité

- Odoo 14.0+
- Module requis : `website_sale`, `sale_subscription`

## Support

Pour toute question ou problème, contactez l'équipe de développement.

## Notes techniques

### Personnalisation du formulaire de contact

Si vous souhaitez personnaliser davantage le formulaire de contact, vous pouvez :

1. Créer un template personnalisé en héritant de `website.contactus`
2. Ajouter des champs spécifiques pour les box
3. Modifier le controller `BoxContactController` pour gérer ces nouveaux champs

### Gestion avancée

Pour une gestion plus avancée (par exemple, synchronisation avec un système de disponibilité), vous pouvez :

1. Ajouter des champs calculés pour la disponibilité
2. Créer des automatisations avec Odoo Studio
3. Intégrer avec d'autres modules (planning, stock, etc.)

## Licence

LGPL-3
