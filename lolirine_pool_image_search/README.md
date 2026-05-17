# Lolirine Pool Image Search

Module Odoo 19 de recherche d'images produits via scraping ciblé.

## Objectif

Résoudre le problème des images extraites depuis les catalogues PDF qui
contiennent souvent des éléments parasites ou des délimitations imprécises.
Au lieu d'extraire les images du PDF, on les **recherche sur le web** sur
base du nom et de la référence du produit.

## Architecture

```
┌─────────────────┐
│  Produits ciblés│ (sélection multi-records dans tree view)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Wizard de lancement        │
│  - Max candidats/produit    │
│  - Seuil auto-validation    │
│  - Options post-traitement  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐         ┌──────────────────┐
│  Session de recherche       │◄────────│  Cron toutes     │
│  - file d'attente           │         │  les 10 min      │
│  - progression              │         └──────────────────┘
└────────┬────────────────────┘
         │
         ▼ pour chaque produit
┌─────────────────────────────┐
│  ScraperOrchestrator        │
│  ├─ ScraperFluidra          │  (direct search Fluidra)
│  ├─ ScraperSCP              │  (direct search SCP)
│  └─ ScraperDuckDuckGo       │  (site: pentair/hayward/zodiac/...)
└────────┬────────────────────┘
         │ 10–15 candidats bruts
         ▼
┌─────────────────────────────┐
│  ImageProcessor             │
│  1. Décodage PIL            │
│  2. rembg (bg removal)      │
│  3. Resize 1200×1200        │
│  4. Conversion WebP         │
│  5. Thumbnail 300×300       │
│  6. phash perceptuel        │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Scoring (0–100)            │
│  - Résolution      30 pts   │
│  - Source fiable   25 pts   │
│  - Ratio packshot  15 pts   │
│  - Réf dans URL    15 pts   │
│  - Nom dans URL    10 pts   │
│  - Pénalités logos  -20 pts │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Déduplication phash        │
│  (hamming distance < 5)     │
└────────┬────────────────────┘
         │ top 5 candidats
         ▼
┌─────────────────────────────┐
│  pool.image.search.candidate│
└────────┬────────────────────┘
         │
         ▼
   score >= 90% ?
    │              │
   OUI            NON
    │              │
    ▼              ▼
 Auto-          Kanban
 validé       (validation
 (main)        manuelle)
```

## Dépendances Python

```bash
pip install requests beautifulsoup4 Pillow imagehash
# Optionnel mais recommandé pour le background removal :
pip install rembg
```

**Note rembg** : charge un modèle ONNX ~4 MB (u2netp) ou ~170 MB (u2net) au
premier appel. Sur Odoo.sh, le premier scoring d'une session sera lent
(15–30s d'init), puis instantané pour les suivants.

## Installation

1. Copier le dossier dans `/extra-addons/` de votre projet Odoo.sh
2. Mettre à jour la liste des modules (`-u all` ou via UI)
3. Installer "Lolirine Pool Image Search" depuis Apps
4. Aller dans **Ventes > Recherche images > Sources de scraping**
   pour vérifier les sources actives

## Utilisation

### Recherche en masse

1. Ouvrir la liste des produits (`Inventaire > Produits` ou `Site web > eCommerce > Produits`)
2. Filtrer "Sans image" (filtre ajouté par le module)
3. Sélectionner les produits → menu Action → "Rechercher images web"
4. Configurer la session et valider
5. La session passe en `queued`, le cron la prendra dans les 10 min
6. (ou cliquer "Lancer maintenant" pour test synchrone)

### Validation

1. Ouvrir la session → cliquer "Candidats"
2. Kanban groupé par produit, 5 candidats par groupe
3. Pour chaque produit :
   - ⭐ Définir comme image principale
   - **+** Ajouter à la galerie
   - 🪄 Re-détourer (relance rembg)
   - ✗ Rejeter
4. Les actions appliquent immédiatement sur `product.template`

### Bouton sur fiche produit

Sur chaque fiche produit, deux nouveaux stat buttons :
- **🔍 Recherche web** : lance une recherche pour ce seul produit
- **Candidats** : affiche les candidats déjà trouvés

## Configuration avancée

### Désactiver une source

`Ventes > Recherche images > Sources de scraping` → décocher `active`.

### Ajuster les quotas

Chaque source a un `daily_quota`. Le compteur se reset à minuit
automatiquement.

### Ajuster le scoring

Modifier `services/scraper_orchestrator.py:_score_candidate()` pour adapter
les poids des critères à ton usage.

## Limites connues

- Les sites fournisseurs peuvent changer leur HTML, cassant les scrapers
  directs (Fluidra/SCP). Le fallback DDG reste fonctionnel.
- rembg peut produire des découpes imparfaites sur produits transparents
  (filets, robots avec membranes). Bouton "Re-détourer" + image brute toujours dispo.
- Throttling à 1 req/s = ~3600 req/h max → traiter 5000 produits prend
  ~6–10h en fonction des sources.

## TODO futur

- [ ] Detection automatique de la marque depuis le nom produit pour
      router vers le bon scraper en priorité
- [ ] Cache des recherches (clé = ref+nom) pour éviter les re-runs payants
- [ ] Export CSV des candidats pour validation hors Odoo
- [ ] Intégration avec `lolirine_pool_import` pour traiter les produits
      fraîchement importés automatiquement
