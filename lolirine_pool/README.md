# Lolirine Pool - Module E-commerce Piscine

## Description

Module Odoo 19 pour la gestion du site e-commerce **piscine.lolirine.be**.

Ce module permet de :
- Gérer un catalogue de produits piscine multi-fournisseurs
- Importer des produits depuis différentes sources (CSV, API, OCR)
- Personnaliser le thème du site piscine
- Gérer les caractéristiques techniques spécifiques aux équipements piscine

## Fournisseurs pré-configurés

| Fournisseur | Code | Méthode d'import |
|-------------|------|------------------|
| Fluidra | FLUIDRA | CSV / API |
| SCP Bénélux | SCP | CSV |
| Allforpools | AFP | CSV |
| MyPiscine.com | MYP | CSV |

## Installation

1. Copier le dossier `lolirine_pool` dans `/src/user/` sur Odoo.sh
2. Mettre à jour la liste des applications
3. Installer le module "Lolirine Pool - E-commerce Piscine"

```bash
# Sur Odoo.sh
cd /home/odoo/src/user
unzip lolirine_pool.zip
git add .
git commit -m "Add lolirine_pool module"
git push
```

## Configuration

### 1. Créer le website piscine

1. Aller dans **Website → Configuration → Websites**
2. Créer un nouveau site :
   - Nom : `Lolirine Piscine`
   - Domaine : `piscine.lolirine.be`
   - Société : `Lolirine SPRL`

### 2. Configurer le domaine DNS

Dans **Odoo.sh → Settings → Custom Domains** :
1. Ajouter `piscine.lolirine.be`
2. Configurer le CNAME chez OVH

### 3. Configurer les fournisseurs

1. Aller dans **Piscine → Fournisseurs & Import → Fournisseurs**
2. Compléter les informations de connexion pour chaque fournisseur
3. Configurer le mapping des colonnes CSV si nécessaire

## Import de produits

### Import CSV

1. Ouvrir la fiche du fournisseur
2. Cliquer sur **Importer des produits**
3. Charger le fichier CSV
4. Vérifier le mapping des colonnes
5. Lancer l'import

### Format CSV attendu

```csv
REF;NOM;DESCRIPTION;PRIX_ACHAT;EAN;CATEGORIE;MARQUE
ABC123;Pompe Astral;Pompe filtration 1CV;450.00;3760123456789;Pompes;AstralPool
```

## Structure du module

```
lolirine_pool/
├── __manifest__.py
├── models/
│   ├── pool_supplier.py      # Fournisseurs et mapping
│   ├── pool_import.py        # Import et logs
│   ├── pool_product.py       # Catégories et marques
│   └── product_template.py   # Extension produits
├── wizard/
│   └── pool_import_wizard.py # Assistant d'import
├── views/
│   ├── pool_supplier_views.xml
│   ├── pool_import_views.xml
│   ├── pool_product_views.xml
│   ├── website_templates.xml # Templates frontend
│   └── website_snippets.xml  # Blocs éditables
├── data/
│   ├── product_category_data.xml
│   ├── supplier_data.xml
│   └── website_data.xml
├── static/
│   └── src/
│       ├── css/
│       │   ├── pool_theme.css    # Thème frontend
│       │   └── pool_backend.css  # Style backend
│       └── js/
│           └── pool_shop.js      # JS frontend
└── security/
    ├── pool_security.xml
    └── ir.model.access.csv
```

## Catégories de produits

- Filtration
- Pompes
- Robots & Nettoyage
- Traitement de l'eau
- Chauffage
- Couvertures & Volets
- Accessoires
- Construction & Rénovation
- Spa & Bien-être

## Marques préconfigurées

- AstralPool
- Zodiac
- Hayward
- Pentair
- Dolphin (Maytronics)
- Bayrol

## Personnalisation du thème

Le fichier `static/src/css/pool_theme.css` contient les variables CSS :

```css
:root {
    --pool-primary: #0077B6;
    --pool-primary-light: #00B4D8;
    --pool-primary-dark: #023E8A;
}
```

## Support

Développé par Lolirine SPRL pour le site piscine.lolirine.be

## Licence

LGPL-3
