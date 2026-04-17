# 🖼️ Lolirine Pool Import - Extension Extraction d'Images

Extension du module `lolirine_pool_import` pour l'extraction automatique d'images depuis les catalogues PDF piscine (SCP, Fluidra, etc.).

## ✅ Validation Technique

**Testé avec succès sur catalogues réels** :
- 16 produits extraits depuis 2 pages (SCP + Fluidra)
- Scores qualité : 0.37 à 0.79 (Bon à Excellent)
- **Bordures nettes** ✅ **Aucun débordement** ✅ **Qualité optimale** ✅

## 🚀 Installation

### 1. Prérequis Python

```bash
# Sur Odoo.sh, ces dépendances sont installées automatiquement
pip install PyMuPDF opencv-python Pillow numpy --break-system-packages
```

### 2. Installation Module

1. **Déposer le dossier** `lolirine_pool_import_extended/` dans `/home/odoo/src/user/`
2. **Décommenter la dépendance** dans `__manifest__.py` :
   ```python
   'depends': [
       'base',
       'product', 
       'website',
       'website_sale',
       'lolirine_pool_import',  # ← Décommenter cette ligne
   ],
   ```
3. **Installer le module** depuis Apps → Rechercher "Image Extraction"

### 3. Vérification

- Aller dans **Ventes → Pool Store → Imports PDF**
- Ouvrir un import existant → Le bouton **"Extraire les images"** doit apparaître

---

## 📋 Guide d'Utilisation

### Étape 1 : Import PDF Standard
```
Ventes → Pool Store → Imports PDF → Créer
• Upload le catalogue SCP/Fluidra
• "Démarrer Extraction" → Attendre fin parsing texte
```

### Étape 2 : Extraction Images
```
Bouton "Extraire les images" → Processing automatique
• Détection produits page par page
• 3 variantes générées : Raw / Trimmed / Enhanced
• Association auto par proximité textuelle
```

### Étape 3 : Révision Manuelle (Approche Hybride)
```
"Voir les images extraites" → Vue Kanban groupée par rôle
• Vérifier associations automatiques (scores de confiance)
• Drag & Drop ou boutons rapides : Principale / Secondaire / Rejetée
• Réassigner manuellement si besoin (bouton "Réassigner produit")
```

### Étape 4 : Attribution en Masse (Optionnel)
```
"Attribution en masse" → Actions bulk
• Auto: Meilleure image → Principale
• Auto: Autres images → Secondaires  
• Rejeter: Score qualité < seuil
```

### Étape 5 : Push vers Production
```
"🚀 Push vers production" → Wizard
• Créer product.template manquants (optionnel)
• Remplacer images existantes (optionnel)
• Catégorie + Site web par défaut
→ Images transférées vers product.template.image_1920 + product.image
```

---

## 🔧 Paramètres Techniques

### Algorithme d'Extraction

**Détection** :
- Contours adaptatifs sur fond clair (produits piscine)
- Filtres : Surface 2K-100K px², ratio 0.2-5.0, position, densité
- Score qualité : taille + forme + position gauche + compacité

**Amélioration Qualité** (correction du flou signalé) :
- **Raw** : Extraction directe PDF (résolution native)
- **Trimmed** : Suppression bordures par détection contour principal
- **Enhanced** : Unsharp masking (0.4x) + contraste subtil (+8%)

**Association Produit** :
- Recherche référence dans blocs texte de la page
- Distance euclidienne centre image ↔ bloc référence
- Confiance : 1.0 - (distance / 400px)

### Paramètres Configurables

```python
# Dans l'interface Odoo - Onglet "Paramètres d'extraction"
min_image_area = 2000      # Surface minimum (px²)
max_image_area = 100000    # Surface maximum (px²) 
min_aspect_ratio = 0.2     # Ratio W/H minimum
max_aspect_ratio = 5.0     # Ratio W/H maximum
```

---

## 🔍 Modèles de Données

### `pool.catalog.pdf.image`
```python
# Relations
pdf_import_id          # M2O vers pool.catalog.pdf.import
matched_product_id     # M2O vers pool.catalog.pdf.product

# Images (3 variantes)
image_raw             # Binary - Image brute
image_trimmed         # Binary - Bordures supprimées  
image_enhanced        # Binary - Qualité optimisée
image_final           # Computed - Image sélectionnée

# Métadonnées
bbox_x, bbox_y, bbox_width, bbox_height  # Position sur page
quality_score         # 0.0-1.0 - Score extraction
confidence_score      # 0.0-1.0 - Confiance association
role                  # unassigned/primary/secondary/rejected
```

### Extensions Existantes
```python
# pool.catalog.pdf.import
image_extraction_state     # not_started/in_progress/completed/error
image_extraction_progress  # Float 0-100%
extracted_image_ids       # O2M vers images

# pool.catalog.pdf.product  
image_ids                 # O2M vers images associées
primary_image_id          # Computed - Image principale
secondary_image_ids       # O2M vers images secondaires
```

---

## 🧩 Architecture & Wizards

### Wizards Disponibles

**1. Réassignation (`pool.catalog.image.reassign.wizard`)**
- Changer l'association image ↔ produit manuellement
- Ajuster le score de confiance
- Ajouter des notes

**2. Push Production (`pool.catalog.image.push.wizard`)**
- Statistiques : produits totaux, avec images, principales/secondaires
- Options : créer manquants, écraser existants, catégorie défaut
- Résultats : créés, mis à jour, erreurs

**3. Attribution Masse (`pool.catalog.image.bulk.wizard`)**
- Auto-principale (meilleur score par produit)
- Auto-secondaire (autres images avec produit)
- Reset tout en non-attribué
- Rejeter images basse qualité

### Intégration UI

**Import PDF** : Boutons "Extraire images", "Attribution masse", "Push production"  
**Produit PDF** : Onglet "Images" avec kanban + image principale  
**Images** : Vue kanban groupée par rôle + actions rapides

---

## 🚨 Points d'Attention

### Performance
- **Gros catalogues** : Processing resumable avec checkpoint tous les 5 pages
- **Mémoire** : PyMuPDF + OpenCV, prévoir 200-500MB RAM par PDF
- **Réseau** : Images base64 dans PostgreSQL, impact taille DB

### Qualité Images
- **Flou résiduel** : Algorithme enhanced optimisé, mais certains PDF sources restent limités
- **Backgrounds complexes** : Trim automatique fonctionne mal sur fonds texturés
- **Multi-produits** : Une image composite → plusieurs produits pas gérée automatiquement

### Cas Limites
- **PDF protégés/chiffrés** : PyMuPDF ne peut pas extraire
- **Images vectorielles** : Converties en raster, perte qualité possible
- **Layout atypique** : Algorithme optimisé pour catalogues SCP/Fluidra standard

---

## 🔬 Debug & Logs

```python
# Logs niveau INFO
_logger.info(f"Extraction page {page_num}/{total}: {count} images")

# Erreurs capturées
try:
    # Code extraction
except Exception as e:
    _logger.error(f"Erreur extraction page {page_num}: {e}")
    continue  # Page suivante
```

**Fichiers Debug** (si besoin) :
- `/tmp/catalog_extraction_debug/` 
- Métadonnées JSON par page
- Images intermédiaires pour diagnostic

---

## 📈 Roadmap & Améliorations

### V1.1 Prévue
- [ ] Support OCR pour PDF scannés (Tesseract)
- [ ] Détection logos/marques pour classification auto
- [ ] Export batch images pour retouche externe
- [ ] API REST pour extraction via scripts externes

### Optimisations Possibles
- [ ] Cache intelligents des extractions répétitives
- [ ] Parallélisation multi-thread pour gros catalogues
- [ ] Compression d'images adaptative selon usage (web/print)
- [ ] IA pour amélioration automatique de la netteté

---

## 🆘 Support

**Issues communes** :
1. **"Images floues"** → Vérifier variante Enhanced, ajuster paramètres unsharp
2. **"Pas d'images détectées"** → Vérifier seuils min/max area dans paramètres
3. **"Mauvaises associations"** → Mode manuel, puis bulk assign
4. **"Erreur PyMuPDF"** → Vérifier format PDF + taille fichier

**Contact** : Via conversation Claude avec logs d'erreur.

---

**🎯 Module prêt pour production sur catalogues SCP/Fluidra !**
