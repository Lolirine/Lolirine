# Changelog - Lolirine Pool Import

## Version 19.0.5.0.0 - 30/01/2026

### 🎯 Nouvelle fonctionnalité principale : Remises Fournisseur Fluidra

**Intégration automatique de la grille de remises Fluidra (075027-LOLIRINE)**

#### Codes de remise inclus :

| Code | Description | Remise |
|------|-------------|--------|
| C | Gamme CONSTRUCTION | 40% |
| F | Gamme SUR MESURE | 35% |
| FI01F | Liners | 40% |
| FI02F | Escaliers Liners | 50% |
| FI03F | PVC Armé | 40% |
| FI10F | Couvertures automatiques | 45% |
| FI11F | Abris & Terrasses mobiles | 35% |
| FI20F | Enrouleurs | 40% |
| FI21F | Bâches à bulles | 50% |
| FI23F | Couvertures Étanches | 50% |
| FI25F | Couvertures à Barres | 50% |
| M | MAGASIN (par défaut) | 35% |
| N | BASSIN NATUREL ET KOI | 25% |
| NK01N | Raccords et Tube | 25% |
| NK02N | Pompes & Filtres | 20% |
| R | PIÈCES DE RECHANGES | 40% |
| RPPRA/N/P/W/Z | PDR par marque | 40% |

### 📊 Calcul automatique des prix

Lors de l'extraction OCR d'un produit, le système calcule maintenant automatiquement :

1. **Prix catalogue** - Le prix extrait du document (prix brut)
2. **Remise fournisseur** - Appliquée selon la catégorie du produit
3. **Prix d'achat NET** - Prix catalogue × (1 - Remise%)
4. **Prix de vente suggéré** - Prix NET × (1 + Marge%)

### 🖥️ Affichage dans l'interface

L'extracteur de catalogue affiche maintenant une barre d'information bleue avec :
- % de remise Fluidra appliquée
- Prix d'achat NET calculé
- Prix de vente suggéré

### ⚙️ Configuration

La grille de remises est accessible dans :
**Pool Import > Configuration > Fournisseurs > Fluidra > Onglet "Grille de Remises"**

Chaque remise peut avoir :
- Code alphanumérique (ex: FI01F, M, NK01N)
- Description
- Mots-clés pour détection automatique
- % de remise
- % de marge de vente suggérée
- Flag "par défaut" (code M)

### 📝 Notes techniques

- Nouveau modèle : `pool.supplier.discount`
- Nouveaux champs calculés sur `pool.catalog.extraction.product` :
  - `discount_percent`
  - `purchase_price_net`
  - `selling_price_calculated`
- Méthode `calculate_prices()` sur `pool.supplier`

---

## Installation / Mise à jour

1. Remplacer le dossier `lolirine_pool_import` sur Odoo.sh
2. Redémarrer le serveur
3. Mettre à jour le module : `odoo-bin -u lolirine_pool_import`
4. Les données de remises Fluidra seront créées automatiquement (noupdate="1")

Pour modifier les remises après installation, aller dans :
Pool Import > Configuration > Fournisseurs > Fluidra
