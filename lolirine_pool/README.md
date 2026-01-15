# Lolirine Pool - Module Odoo 19

Module complet pour la gestion d'un e-commerce de matériel piscine.

## Compatibilité

- **Odoo 19.0** ✅
- Testé sur Odoo.sh

## Fonctionnalités

### Gestion des fournisseurs
- Configuration multi-fournisseurs (Fluidra, SCP, Allforpools, etc.)
- Mapping intelligent des colonnes CSV
- Calcul automatique des marges (pourcentage, fixe, formule)

### Import de produits
- Import CSV/Excel
- Prévisualisation avant import
- Mise à jour des produits existants
- Import automatique des images
- Historique et logs d'import

### Catalogue piscine
- Catégories spécialisées (Filtration, Pompes, Robots, etc.)
- Gestion des marques (AstralPool, Zodiac, Hayward, etc.)
- Attributs techniques (débit, puissance, volume)

### Site e-commerce
- Thème dédié piscine
- Snippets personnalisés
- Page d'accueil adaptée

## Installation

1. Copiez le dossier `lolirine_pool` dans `/home/odoo/src/user/`
2. Mettez à jour la liste des applications
3. Installez le module "Lolirine Pool"

```bash
# Sur Odoo.sh
cd /home/odoo/src/user/
git add lolirine_pool
git commit -m "Add lolirine_pool module"
git push
```

## Configuration

### 1. Configurer le domaine DNS

Dans **Odoo.sh → Settings → Custom Domains** :
1. Ajouter `piscine.lolirine.be`
2. Configurer le CNAME chez OVH

### 2. Configurer les fournisseurs

1. Aller dans **Piscine → Fournisseurs & Import → Fournisseurs**
2. Compléter les informations de connexion
3. Configurer le mapping des colonnes CSV

## Import de produits

### Format CSV attendu

```csv
REF;NOM;DESCRIPTION;PRIX_ACHAT;EAN;CATEGORIE;MARQUE
ABC123;Pompe Astral;Pompe filtration 1CV;450.00;3760123456789;Pompes;AstralPool
```

### Procédure d'import

1. Ouvrir la fiche du fournisseur
2. Cliquer sur **Importer des produits**
3. Charger le fichier CSV
4. Vérifier l'aperçu
5. Lancer l'import

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
│   ├── website_templates.xml
│   └── website_snippets.xml
├── data/
│   ├── product_category_data.xml
│   └── supplier_data.xml
├── static/src/
│   ├── css/pool_theme.css
│   └── js/pool_shop.js
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

Variables CSS dans `static/src/css/pool_theme.css` :

```css
:root {
    --pool-primary: #0077B6;
    --pool-primary-light: #00B4D8;
    --pool-primary-dark: #023E8A;
}
```

## Notes de migration Odoo 19

Ce module est **compatible Odoo 19**. Les changements majeurs appliqués :

- ✅ Suppression de `category_id` dans `res.groups`
- ✅ Utilisation de `self.env.context` au lieu de `self._context`
- ✅ Compatibilité avec les nouveaux systèmes de privilèges

## Support

Développé par **Lolirine SPRL** pour piscine.lolirine.be

## Licence

LGPL-3
