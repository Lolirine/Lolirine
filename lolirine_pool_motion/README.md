# lolirine_pool_motion

Socle d'animations frontend pour le Pool Store (Odoo 19), construit sur la
classe **Interaction** d'Odoo 19 et le moteur **Motion** (motion.dev) v12,
embarqué localement (build UMD → `window.Motion`).

Pensé pour être **alimenté progressivement** : on ajoute les data-attributs sur
les templates, et plus tard de nouvelles interactions dans `static/src/js/`.

---

## Installation

1. Copier le dossier dans tes addons, commit, push sur Odoo.sh.
2. Activer le mode développeur → Apps → *Mettre à jour la liste*.
3. Installer **Lolirine Pool Store — Motion**.
   (ou en shell : `self.env['ir.module.module'].search([('name','=','lolirine_pool_motion')]).button_immediate_install()`)
4. Bump de version dans le manifest à chaque push pour forcer l'upgrade.

Aucune donnée, aucun modèle : module 100 % frontend. Désinstallation sans effet de bord.

---

## Utilisation (data-attributs, zéro JS à écrire)

### 1. Reveal au scroll
```html
<div data-motion-reveal>Apparaît en montant + fondu</div>
<h2 data-motion-reveal data-motion-axis="x" data-motion-dir="left"
    data-motion-distance="40" data-motion-delay="0.1">Glisse depuis la gauche</h2>
```
Options : `data-motion-axis` (y|x), `data-motion-dir` (up|down|left|right),
`data-motion-distance`, `data-motion-delay`, `data-motion-duration`,
`data-motion-once="false"` (rejoue à chaque passage).

### 2. Cascade (stagger)
```html
<div class="row" data-motion-stagger data-motion-gap="0.07">
  <div class="col" data-motion-item>Carte 1</div>
  <div class="col" data-motion-item>Carte 2</div>
  <div class="col" data-motion-item>Carte 3</div>
</div>
```
Sans `data-motion-item`, les enfants directs sont pris automatiquement.

### 3. Compteur animé
```html
<span data-motion-count="75">0</span> boxes
<span data-motion-count="98" data-motion-suffix=" %">0</span>
<span data-motion-count="44000" data-motion-suffix=" €">0</span>
```

### 4. Retour tactile (press)
Automatique sur les cartes produit `.oe_product`. Sinon :
```html
<button data-motion-press>Ajouter au panier</button>
```

> Le **survol** des cartes produit (élévation + zoom image) est géré en pur CSS
> dans `motion.scss` — plus performant et sans saccade en grille.

---

## Garanties intégrées

- **Accessibilité** : `prefers-reduced-motion: reduce` désactive toute animation.
- **Anti-flash** : pré-masquage CSS conditionné à l'exécution du JS.
- **Failsafe** : si le JS échoue, tout le contenu réapparaît après 4 s — jamais de bloc invisible.
- **Sans JS** : le contenu reste visible et utilisable (dégradation propre).
- **SEO** : rendu serveur intact, on n'anime que l'affichage. À ne PAS confondre
  avec les composants OWL frontend (eux pénalisent l'indexation).

---

## Charte de mouvement

Tout se règle dans `static/src/js/motion_helpers.js` → objet `MOTION`
(courbes, durées, distance, cascade). Modifier là = changer le ressenti du site
entier d'un coup.

---

## Note performance

Le build complet de Motion pèse ~46 ko gzip. Acceptable, mais si on veut alléger,
on pourra basculer sur le build « mini » de Motion (animate WAAPI + inView +
stagger, ~2–3× plus léger) sans changer l'API côté templates.

---

## Feuille de route — « le site le plus animé possible »

Par ordre d'impact / effort, ce que je propose d'ajouter ensuite (chaque point =
une nouvelle interaction ou un bloc de templates) :

**Vague 1 — finition perçue (faible risque)**
- Reveal/stagger posés sur : hero, grille catalogue, blocs marques, footer.
- Header rétractable au scroll (cache vers le bas, réapparaît vers le haut).
- Bouton « retour haut » avec apparition animée.
- Transition douce d'ajout au panier (flyer de l'image vers l'icône panier).

**Vague 2 — interactions e-commerce**
- Mini-cart drawer animé (slide-in) au lieu du rechargement.
- Quickview produit en overlay animé depuis la carte.
- Galerie produit : zoom/parallaxe léger, miniatures animées.
- Filtres à facettes avec apparition/disparition fluide des résultats.
- Skeletons animés pendant le chargement (anti-CLS perçu).

**Vague 3 — signature visuelle (à doser)**
- Hero avec parallaxe `Motion.scroll()` (eau / bulles / vagues subtiles — thème piscine).
- Compteurs de chiffres clés sur la page d'accueil.
- Effet « magnetic » sur les CTA principaux.
- Marquee de logos marques en boucle douce.

**Garde-fous à garder en tête**
- Ne jamais doubler une animation déjà gérée par l'éditeur Odoo (classes `o_animate`).
- Surveiller le LCP/CLS : pas d'animation sur les éléments above-the-fold critiques au chargement.
- Tout nouveau morceau doit respecter reduced-motion et le failsafe.

Dis-moi par quelle vague on commence et je code les interactions correspondantes.
