# Patch lolirine_pool_import - Assignation automatique au Pool Store

## Problème résolu
Les produits importés via le module `lolirine_pool_import` n'étaient pas automatiquement assignés au site web "Lolirine Pool Store". Ils étaient donc visibles sur tous les sites (y compris le garde-meubles).

## Solution
Ce patch modifie le module pour :
1. Assigner automatiquement `website_id` = Pool Store lors de l'import
2. Assigner automatiquement `is_pool_product` = True
3. Fournir une méthode pour assigner les produits existants

---

## Installation

### Étape 1 : Modifier product_template.py

Remplace le contenu de `lolirine_pool_import/models/product_template.py` par le fichier fourni dans ce patch.

Le fichier ajoute :
- La méthode `_get_pool_website_id()` qui trouve automatiquement le site Pool Store
- L'override de `create()` pour assigner le `website_id` automatiquement
- L'override de `write()` pour gérer les changements de `is_pool_product`
- Une action `action_assign_to_pool_website()` pour assignation manuelle

### Étape 2 : Mettre à jour le module

```bash
# Sur Odoo.sh, dans ton terminal
cd /home/odoo/src/user
# Commiter les changements
git add lolirine_pool_import/
git commit -m "feat: auto-assign products to Pool Store website"
git push
```

Odoo.sh va redéployer automatiquement.

### Étape 3 : Assigner les produits existants

Exécute le script `assign_products_to_pool_store.py` dans le shell Odoo :

1. Va sur Odoo.sh → ton projet → Shell
2. Lance : `odoo-bin shell -d <nom_de_ta_base>`
3. Copie-colle le contenu du script

---

## Vérification

### Dans Odoo
1. Va dans **Ventes → Produits**
2. Ajoute la colonne "Site web" à la liste
3. Filtre sur `is_pool_product = True`
4. Vérifie que tous ont "Lolirine Pool Store" comme site web

### Test d'import
1. Importe un nouveau produit via le module
2. Vérifie qu'il a automatiquement :
   - `is_pool_product` = ✓
   - `website_id` = Lolirine Pool Store

---

## Fonctionnement technique

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPORT DE PRODUIT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. Extraction OCR / Import CSV                                │
│                    ↓                                            │
│   2. Création du produit avec is_pool_product = True            │
│                    ↓                                            │
│   3. Override create() détecte is_pool_product                  │
│                    ↓                                            │
│   4. _get_pool_website_id() trouve le site Pool Store           │
│                    ↓                                            │
│   5. website_id assigné automatiquement                         │
│                    ↓                                            │
│   6. Produit visible UNIQUEMENT sur www.lolirinepoolstore.be   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Fichiers inclus

```
lolirine_pool_import_patch/
├── README.md                           # Ce fichier
├── models/
│   ├── product_template.py             # À copier dans lolirine_pool_import/models/
│   └── pool_catalog_extraction.py      # Référence (pas à copier directement)
└── scripts/
    └── assign_products_to_pool_store.py # Script pour les produits existants
```
