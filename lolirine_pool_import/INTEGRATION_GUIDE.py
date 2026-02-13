#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=================================================================
GUIDE D'INTÉGRATION : Visuels Variantes Dynamiques
=================================================================

Quand un client sélectionne une variante sur le site e-commerce
(meuble spa, couleur cuve, diamètre PVC, capacité PAC…), l'image
principale du produit change automatiquement.

=================================================================
FICHIERS À AJOUTER AU MODULE lolirine_pool_import
=================================================================

1. MODÈLES PYTHON
   ─────────────
   models/pool_variant_image.py        → NOUVEAU fichier
   models/__init__.py                  → AJOUTER: from . import pool_variant_image

2. CONTRÔLEUR HTTP
   ────────────────
   controllers/variant_image_controller.py  → NOUVEAU fichier
   controllers/__init__.py                  → AJOUTER: from . import variant_image_controller

3. JAVASCRIPT FRONTEND
   ────────────────────
   static/src/js/variant_image_switcher.js  → NOUVEAU fichier

4. VUES XML
   ─────────
   views/pool_variant_image_views.xml       → NOUVEAU fichier
   views/website_variant_image.xml          → NOUVEAU fichier

5. FICHIER PRINCIPAL (déjà patché)
   ────────────────────────────────
   models/pool_catalog_extraction.py        → REMPLACER par le fichier patché
   (contient les appels à _assign_variant_images_post_import)

6. __manifest__.py
   ─────────────────
   AJOUTER dans 'data':
       'views/pool_variant_image_views.xml',
       'views/website_variant_image.xml',

   AJOUTER dans 'depends' (si pas déjà):
       'website_sale',

   AJOUTER dans 'assets' (Odoo 17+/19):
       'web.assets_frontend': [
           'lolirine_pool_import/static/src/js/variant_image_switcher.js',
       ],


=================================================================
STRUCTURE FINALE DU MODULE
=================================================================

lolirine_pool_import/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py                          ← ajouter import
│   ├── pool_catalog_extraction.py           ← REMPLACÉ (avec patches 1-7)
│   ├── pool_variant_image.py                ← NOUVEAU
│   └── ...
├── controllers/
│   ├── __init__.py                          ← ajouter import
│   ├── variant_image_controller.py          ← NOUVEAU
│   └── ...
├── static/
│   └── src/
│       └── js/
│           └── variant_image_switcher.js    ← NOUVEAU
├── views/
│   ├── pool_variant_image_views.xml         ← NOUVEAU
│   ├── website_variant_image.xml            ← NOUVEAU
│   └── ...
└── security/
    └── ir.model.access.csv


=================================================================
COMMENT ÇA MARCHE
=================================================================

BACKEND (à l'import OCR) :
  1. Le produit est créé avec ses variantes (Meuble, Couleur, etc.)
  2. _add_product_image() assigne l'image au template
  3. _assign_variant_images_post_import() distribue les images aux PTAV :
     - Matche par nom (ex: image "BUTTERFLY" → PTAV "BUTTERFLY")
     - Matche par référence catalogue
     - Matche par données JSON (furniture_variants_data)

FRONTEND (site e-commerce) :
  1. Le JS charge /pool/variant_images/<tmpl_id> (JSON des PTAV+images)
  2. Quand le client clique sur un radio/couleur/select, le JS :
     - Trouve la PTAV sélectionnée
     - Si elle a une image → swap l'image principale avec fade transition
     - Sinon → garde l'image par défaut
  3. Bonus : ajoute des miniatures 32×32 à côté des labels d'attribut

BATCH (produits existants) :
  Menu Configuration > Batch images variantes
  Ou : action serveur sur la liste produits
  Ou : Odoo shell (voir ci-dessous)


=================================================================
LANCER LE BATCH SUR TOUS LES PRODUITS EXISTANTS
=================================================================

Méthode 1 : Via le menu Odoo
  Configuration piscine → Batch images variantes

Méthode 2 : Via Odoo shell
  $ odoo-bin shell -d <database>
  >>> result = env['product.template'].cron_assign_all_variant_images()
  >>> print(result)
  >>> env.cr.commit()

Méthode 3 : Via action planifiée (CRON)
  Activer le cron "Pool : Assigner images variantes" dans
  Paramètres → Technique → Actions planifiées

Méthode 4 : Via le bouton sur un produit
  Fiche produit → onglet "Images Variantes" → 🖼️ Auto-assigner

"""

# ─── Script exécutable Odoo Shell ─────────────────────────────────
# Copier-coller dans odoo-bin shell :

BATCH_SCRIPT = """
# === Script Odoo Shell : Assignation images variantes ===
# À exécuter avec : odoo-bin shell -d <database>

from odoo import api, SUPERUSER_ID

# Tous les produits avec plus d'une variante
templates = env['product.template'].search([
    ('product_variant_count', '>', 1),
])
print(f"Produits avec variantes : {len(templates)}")

total = 0
errors = []

for tmpl in templates:
    try:
        r = tmpl._auto_assign_variant_images()
        count = r.get('count', 0)
        if count:
            total += count
            print(f"  ✅ {tmpl.name}: {count} images assignées")
    except Exception as e:
        errors.append(f"{tmpl.name}: {e}")
        print(f"  ❌ {tmpl.name}: {e}")

print(f"\\n=== Résumé ===")
print(f"Produits traités : {len(templates)}")
print(f"Images assignées : {total}")
print(f"Erreurs : {len(errors)}")

# IMPORTANT : valider les changements
env.cr.commit()
print("\\n💾 Changements sauvegardés !")
"""

if __name__ == '__main__':
    print(__doc__)
    print("\n" + "="*65)
    print("SCRIPT ODOO SHELL :")
    print("="*65)
    print(BATCH_SCRIPT)
