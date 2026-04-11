/* ─── Pool Plans ─── */
const POOL_PLANS = [{
  id: "rect",
  label: "Rectangulaire",
  w: 200,
  h: 100,
  shape: "rect"
}, {
  id: "square",
  label: "Carrée",
  w: 140,
  h: 140,
  shape: "rect"
}, {
  id: "l_shape",
  label: "En L",
  w: 200,
  h: 140,
  shape: "l"
}, {
  id: "oval",
  label: "Ovale / Ronde",
  w: 200,
  h: 120,
  shape: "oval"
}, {
  id: "kidney",
  label: "Forme libre / Haricot",
  w: 210,
  h: 130,
  shape: "kidney"
}, {
  id: "spa",
  label: "Rect. + Spa intégré",
  w: 220,
  h: 120,
  shape: "spa"
}];
function PoolSvg({
  plan,
  size = 180
}) {
  const scale = size / 240,
    s = v => v * scale;
  const fill = "rgba(14,165,233,0.18)",
    stroke = "#0ea5e9",
    sw = 2.5;
  const {
    w: W,
    h: H
  } = plan;
  if (plan.shape === "rect") return /*#__PURE__*/React.createElement("svg", {
    width: s(W + 30),
    height: s(H + 30),
    viewBox: `0 0 ${W + 30} ${H + 30}`
  }, /*#__PURE__*/React.createElement("rect", {
    x: "15",
    y: "15",
    width: W,
    height: H,
    rx: "6",
    fill: fill,
    stroke: stroke,
    strokeWidth: sw
  }), [[15, 15], [15 + W, 15], [15, 15 + H], [15 + W, 15 + H]].map(([cx, cy], i) => /*#__PURE__*/React.createElement("circle", {
    key: i,
    cx: cx,
    cy: cy,
    r: "4",
    fill: stroke
  })));
  if (plan.shape === "oval") return /*#__PURE__*/React.createElement("svg", {
    width: s(W + 30),
    height: s(H + 30),
    viewBox: `0 0 ${W + 30} ${H + 30}`
  }, /*#__PURE__*/React.createElement("ellipse", {
    cx: 15 + W / 2,
    cy: 15 + H / 2,
    rx: W / 2,
    ry: H / 2,
    fill: fill,
    stroke: stroke,
    strokeWidth: sw
  }));
  if (plan.shape === "kidney") return /*#__PURE__*/React.createElement("svg", {
    width: s(W + 30),
    height: s(H + 30),
    viewBox: `0 0 ${W + 30} ${H + 30}`
  }, /*#__PURE__*/React.createElement("path", {
    d: `M 15,${15 + H * .5} C 15,${15 + H * .05} ${15 + W * .35},15 ${15 + W * .5},${15 + H * .1} C ${15 + W * .72},${15 + H * .22} ${15 + W},${15 + H * .1} ${15 + W},${15 + H * .5} C ${15 + W},${15 + H * .88} ${15 + W * .72},${15 + H} ${15 + W * .5},${15 + H * .88} C ${15 + W * .28},${15 + H * .75} ${15 + W * .28},${15 + H * .55} ${15 + W * .15},${15 + H * .55} C 15,${15 + H * .55} 15,${15 + H * .95} 15,${15 + H * .5} Z`,
    fill: fill,
    stroke: stroke,
    strokeWidth: sw
  }));
  if (plan.shape === "l") return /*#__PURE__*/React.createElement("svg", {
    width: s(W + 30),
    height: s(H + 30),
    viewBox: `0 0 ${W + 30} ${H + 30}`
  }, /*#__PURE__*/React.createElement("path", {
    d: `M 15,15 H ${15 + W} V ${15 + H * .55} H ${15 + W * .55} V ${15 + H} H 15 Z`,
    fill: fill,
    stroke: stroke,
    strokeWidth: sw
  }));
  if (plan.shape === "spa") return /*#__PURE__*/React.createElement("svg", {
    width: s(W + 30),
    height: s(H + 30),
    viewBox: `0 0 ${W + 30} ${H + 30}`
  }, /*#__PURE__*/React.createElement("rect", {
    x: "15",
    y: "15",
    width: W * .72,
    height: H,
    rx: "5",
    fill: fill,
    stroke: stroke,
    strokeWidth: sw
  }), /*#__PURE__*/React.createElement("rect", {
    x: 15 + W * .76,
    y: 15 + H * .2,
    width: W * .24,
    height: H * .6,
    rx: "8",
    fill: "rgba(251,191,36,0.2)",
    stroke: "#f59e0b",
    strokeWidth: sw
  }), /*#__PURE__*/React.createElement("text", {
    x: 15 + W * .88,
    y: 15 + H * .54,
    textAnchor: "middle",
    fontSize: "8",
    fill: "#92400e",
    fontFamily: "sans-serif"
  }, "SPA"));
  return null;
}

/* ─── Interventions ─── */
const INTERVENTIONS = [{
  id: "construction",
  label: "🏗️ Construction neuve",
  color: "#0ea5e9"
}, {
  id: "renovation",
  label: "🔧 Rénovation",
  color: "#f59e0b"
}, {
  id: "entretien",
  label: "🧹 Entretien régulier",
  color: "#10b981"
}, {
  id: "hivernage",
  label: "❄️ Hivernage",
  color: "#6366f1"
}, {
  id: "remise_en_route",
  label: "☀️ Remise en route",
  color: "#f97316"
}, {
  id: "materiel",
  label: "⚙️ Changement de matériel",
  color: "#ec4899"
}];
const CHECKLISTS = {
  construction: [{
    section: "📍 Visite préalable du terrain",
    items: ["Accès chantier (largeur portail, chemin d'accès véhicule)", "Nature du sol (argile, sable, roche, remblai)", "Présence nappe phréatique (profondeur estimée)", "Déclivité / nivellement du terrain nécessaire", "Présence d'arbres / racines / végétation envahissante", "Réseaux enterrés repérés (gaz, eau, électricité, télécoms)", "Distance limites de propriété (min. 1,5 m / usage : 3 m)", "Permis de construire obtenu (>10 m² en Wallonie)", "Étude de sol réalisée (géotechnique)", "Évacuation des eaux de vidange (égout, infiltration, noue)", "Orientation solaire de la piscine optimisée"]
  }, {
    section: "📐 Dimensions & plan de bassin",
    items: ["Longueur (m) : ______", "Largeur (m) : ______", "Profondeur mini (m) : ______", "Profondeur maxi (m) : ______", "Forme retenue (voir plan sélectionné)", "Plage bain allongé (banquette immergée)", "Escalier intégré (roman, droit, d'angle)", "Escalier externe / échelle inox", "Plongeoir prévu (profondeur ≥ 2,5 m)", "Niche de filtration intégrée (réservation béton)", "Caniveau périphérique / margelles débordantes", "Couverture / volet roulant (réservation intégrée)"]
  }, {
    section: "🧱 Structure & étanchéité",
    items: ["Béton coulé (coffrage traditionnel)", "Béton projeté – Gunite", "Béton armé préfabriqué (panneaux)", "Coque polyester (monobloc)", "Kit panneaux acier galvanisé / inox", "Kit panneaux polypropylène", "Revêtement : liner armé (épaisseur 75/100 µ)", "Revêtement : carrelage (grès cérame antidérapant)", "Revêtement : enduit Marbrex / Marbelite", "Revêtement : membrane armée (alkorplan)", "Traitement des joints de structure", "Drain de fond (si présence nappe)", "Protection géotextile fond de fouille"]
  }, {
    section: "💧 Hydraulique",
    items: ["Nombre de bondes de fond : ______", "Nombre de skimmers : ______ (1 skimmer / 25 m²)", "Nombre de refoulements : ______", "Buses de nage (nage à contre-courant)", "Buse à balai (prise balai)", "Trop-plein / régulateur de niveau", "Tuyauterie PVC pression ∅ 50 mm (aspiration)", "Tuyauterie PVC pression ∅ 50 mm (refoulement)", "Manchons anti-vibratoires sur pompe", "Étanchéité traversées de paroi (joints EPDM)", "Test pression canalisations avant remblai"]
  }, {
    section: "🔄 Filtration",
    items: ["Filtre à sable (∅ cuve ______ / débit ______ m³/h)", "Filtre à cartouche", "Filtre à diatomées", "Sable de filtration (granulométrie 0,4–0,8 mm)", "Billes de verre (alternative sable)", "Pompe (marque / modèle / puissance kW) : ______", "Pompe vitesse variable (économie énergie)", "Préfiltre / panier préfiltre", "Vanne multivoies (6 voies)", "Débitmètre", "Manomètre", "Armoire électrique / coffret de commande"]
  }, {
    section: "🧪 Traitement de l'eau",
    items: ["Chlore manuel (galets, liquide)", "Électrolyseur au sel (concentration sel ______ g/L)", "Brome (pastilles / système automatique)", "Traitement UV (lampe UV-C)", "Ozone (générateur ozone)", "PHMB (sans chlore)", "Régulation pH automatique", "Sonde ORP (potentiel rédox)", "Pompe doseuse pH–", "Pompe doseuse désinfectant", "Analyseur connecté"]
  }, {
    section: "🌡️ Chauffage",
    items: ["Pompe à chaleur air/eau (puissance ______ kW)", "Pompe à chaleur réversible", "Échangeur thermique (raccordement chaudière)", "Chauffe-eau solaire (capteurs ______ m²)", "Résistance électrique (puissance ______ kW)", "Couverture solaire à bulles (ép. 400 µ)", "Volet roulant isolant", "Vanne de by-pass pompe à chaleur"]
  }, {
    section: "💡 Électricité & éclairage",
    items: ["Projecteurs LED RGB subaquatiques", "Spots LED encastrés paroi (niche inox)", "Bandeau LED périmétral (plage)", "Éclairage escalier submergé", "Coffret électrique IP65 dédié piscine", "Disjoncteur différentiel 30 mA obligatoire", "Liaison équipotentielle (norme NF C 15-100)", "Mise à la terre générale", "Prise extérieure étanche"]
  }, {
    section: "🪟 Couverture & sécurité",
    items: ["Volet roulant immergé (lames polycarbonate / alu)", "Volet roulant hors-sol", "Couverture à barres automatique / manuelle", "Filet de protection (normes NF P 90-308)", "Alarme piscine OBLIGATOIRE – type : ______", "Clôture de protection (h ≥ 1,10 m) + portillon", "Signalétique profondeur / interdiction plongée"]
  }, {
    section: "🏡 Plage, abords & finitions",
    items: ["Margelles (carrelage / pierre naturelle / béton désactivé)", "Dallage plage (antidérapant R11 minimum)", "Drainage plage (pente 1% minimum)", "Caniveau de récupération eaux de plage", "Douche solaire / raccordement eau", "Lave-pieds", "Local technique", "Nettoyage de chantier / évacuation gravats", "Notice d'utilisation remise au client"]
  }, {
    section: "🤝 Administratif & SAV",
    items: ["Devis signé + acompte encaissé", "Planning prévisionnel remis", "Garanties décennale + RC professionnelle", "Dossier photos avant / pendant / après", "Formation client sur équipements", "Contrat d'entretien proposé"]
  }],
  renovation: [{
    section: "🔍 Diagnostic structure",
    items: ["Fissures structure (fines / traversantes / actives)", "Test étanchéité (baisse niveau eau / test colorant)", "État du fond (dénivellations, décollements)", "État des parois (cloques, éclatement béton)", "Corrosion armatures", "État des scellements (bondes, skimmers, projecteurs)", "Désolidarisation margelles / plage", "Tassement / fissures plage"]
  }, {
    section: "🎨 Revêtement existant",
    items: ["Type de revêtement actuel : ______", "Âge du revêtement (années) : ______", "Liner : déchirures / décollements / décolorations", "Liner : vieillissement, perte de souplesse", "Carrelage : joints décollés / cassés / tâchés", "Enduit : farinage / effritement / tâches", "Membrane armée : décollement / percement", "Évaluation : remplacement ou réfection partielle ?"]
  }, {
    section: "🔧 Hydraulique & filtration existants",
    items: ["Âge de la pompe (années) : ______", "Débit pompe mesuré (m³/h) : ______", "Bruit / vibrations anormaux pompe", "Âge du filtre (années) : ______", "Sable à remplacer (> 5 ans)", "État vanne multivoies (fuites, jeu)", "État des canalisations", "Skimmers : panier cassé / joint usé", "Trop-plein fonctionnel"]
  }, {
    section: "⚡ Électricité & éclairage",
    items: ["Coffret électrique conforme (différentiel 30 mA)", "Liaison équipotentielle présente et vérifiée", "Projecteurs : fonctionnels / étanches", "Projecteurs : remplacement LED prévu", "Câblage apparent / dégradé", "Mise aux normes NF C 15-100 nécessaire"]
  }, {
    section: "🏗️ Travaux de structure prévus",
    items: ["Ragréage fond et parois", "Injection résine anti-fissures", "Reprise étanchéité générale", "Résine de pontage / primaire d'accrochage", "Pose nouveau liner (mesures relevées : ______)", "Réfection enduit complet", "Recarrelage partiel / complet", "Remplacement bondes / skimmers / refoulements", "Remplacement niche projecteur", "Remplacement margelles", "Réfection plage"]
  }, {
    section: "🆕 Équipements à remplacer / ajouter",
    items: ["Pompe (référence nouvelle : ______)", "Filtre à sable (référence nouvelle : ______)", "Vanne multivoies", "Système de traitement (type : ______)", "Pompe à chaleur (référence : ______)", "Volet / couverture", "Éclairage LED", "Robot nettoyeur", "Système domotique"]
  }, {
    section: "🤝 Administratif",
    items: ["Photos état avant travaux", "Devis détaillé postes par postes", "Planning et durée des travaux", "Vidange piscine planifiée", "Gestion eaux de vidange (évacuation conforme)", "Garanties travaux communiquées"]
  }],
  entretien: [{
    section: "🧪 Analyse de l'eau",
    items: ["pH (cible 7,2–7,4) → mesuré : ______", "TAC (cible 80–120 mg/L) → mesuré : ______", "TH – Dureté (cible 150–300 mg/L) → mesuré : ______", "Chlore libre (cible 1,0–3,0 mg/L) → mesuré : ______", "Chlore combiné (< 0,6 mg/L) → mesuré : ______", "Taux de sel si électrolyseur → mesuré : ______", "Cyanurate (< 75 mg/L) → mesuré : ______", "Phosphates (< 0,1 mg/L) → mesuré : ______", "Température eau (°C) : ______", "Turbidité (limpide / trouble / verte)"]
  }, {
    section: "🧹 Nettoyage bassin",
    items: ["Écrémage surface (feuilles, insectes, pollens)", "Aspiration fond (manuelle / robot)", "Brossage parois et fond", "Nettoyage ligne de flottaison", "Nettoyage panier(s) skimmer(s)", "Nettoyage panier préfiltre pompe", "Contre-lavage si pression ≥ 0,5 bar", "Nettoyage cartouche filtrante (si applicable)", "Rinçage plage / abords", "Nettoyage local technique"]
  }, {
    section: "🔄 Filtration & équipements",
    items: ["Pression manomètre relevée : ______ bar", "Débit pompe vérifié", "Bruit / vibration anormal pompe", "Vérification programmateur / horloge", "Vérification vanne multivoies", "Vérification électrolyseur (cellule / production)", "Vérification pompe doseuse pH", "Vérification sonde ORP / pH", "Niveau d'eau ajusté (mi-skimmer)", "Vérification alarme piscine", "Vérification volet / mécanisme"]
  }, {
    section: "💊 Traitements correctifs",
    items: ["Correction pH (produit / dose) : ______", "Correction TAC : ______", "Correction TH : ______", "Choc chlore (dose) : ______", "Algicide préventif appliqué", "Floculant / clarifiant appliqué", "Anti-phosphates appliqué", "Sel ajouté (kg) : ______"]
  }, {
    section: "📋 Observations & recommandations",
    items: ["Usure liner / revêtement à surveiller", "Équipement à remplacer prochainement : ______", "Travaux recommandés : ______", "Prochain entretien prévu (date) : ______", "Produits laissés au client : ______", "Bon de visite signé par le client"]
  }],
  hivernage: [{
    section: "🌊 Préparation de l'eau",
    items: ["Dernière analyse eau complète réalisée", "pH ajusté à 7,2–7,4", "TAC ajusté (> 120 mg/L recommandé)", "Chlore choc appliqué (J-3 minimum)", "Algicide hivernal longue durée appliqué", "Anti-calcaire hivernal appliqué", "Floculant final appliqué", "Nettoyage complet bassin", "Ligne de flottaison nettoyée"]
  }, {
    section: "📉 Niveau d'eau & bouchons",
    items: ["Abaissement niveau d'eau (sous le bas des skimmers)", "Niveau recommandé : ______ cm sous la margelle", "Bouchons hivernage posés dans skimmers", "Bouchons posés dans refoulements", "Bonde de fond : bouchon / clapet fermé", "Flotteurs antigel placés (nombre : ______)", "Prise balai bouchonnée"]
  }, {
    section: "🔌 Arrêt des équipements",
    items: ["Filtration arrêtée", "Vidange complète de la pompe", "Vidange filtre à sable", "Vidange vanne multivoies", "Soufflage des canalisations (compresseur)", "Arrêt électrolyseur + cellule démontée si gel <-10°C", "Arrêt UV / ozone", "Arrêt pompes doseuses + vidange", "Débranchement programmateur / coffret", "Hivernation pompe à chaleur"]
  }, {
    section: "🧳 Rangement & protection",
    items: ["Robot nettoyeur sorti, rincé, stocké", "Équipements de mesure rincés et rangés", "Couverture hivernage mise en place (type : ______)", "État couverture vérifié", "Filet anti-feuilles posé si couverture bulle", "Alarme piscine maintenue active"]
  }, {
    section: "📋 Observations & suivi",
    items: ["Photos état piscine à la fermeture", "Date d'hivernage : ______", "Date de remise en route prévisionnelle : ______", "Remarques particulières : ______", "Bon d'intervention signé"]
  }],
  remise_en_route: [{
    section: "🧹 Réouverture bassin",
    items: ["Retrait couverture hivernage", "Retrait filet anti-feuilles", "Retrait flotteurs antigel", "Retrait bouchons skimmers / refoulements / bonde de fond", "Nettoyage fond et parois", "Remontée du niveau d'eau (mi-skimmer)", "Rinçage plage et abords"]
  }, {
    section: "🔌 Redémarrage équipements",
    items: ["Remontage pompe (vérification sens rotation)", "Amorçage pompe / purge d'air", "Remontage vanne multivoies", "Mise en marche filtration", "Rinçage filtre (contre-lavage + rinçage)", "Remontage / reconnexion électrolyseur", "Remontage pompes doseuses", "Remontage UV / ozone", "Redémarrage pompe à chaleur", "Vérification programmateur / horloge (heure d'été !)", "Test coffret électrique / disjoncteur", "Vérification alarme piscine"]
  }, {
    section: "🧪 Remise en état de l'eau",
    items: ["Analyse eau complète (pH, TAC, TH, chlore, sel)", "Correction pH : ______", "Correction TAC : ______", "Traitement choc (chlore ou oxygène actif)", "Algicide curatif si présence d'algues", "Floculant / clarifiant", "Ajout sel si électrolyseur (quantité : ______ kg)", "Filtration continu 24h à 48h minimum", "Eau limpide atteinte avant baignade"]
  }, {
    section: "✅ Contrôle général",
    items: ["Vérification absence de fuite", "Vérification projecteurs (étanchéité)", "Test robot nettoyeur", "Vérification volet roulant / mécanisme", "Produits d'entretien réapprovisionnés", "Bon d'intervention signé"]
  }],
  materiel: [{
    section: "🔎 Diagnostic matériel existant",
    items: ["Pompe – marque / modèle actuel : ______", "Pompe – puissance (kW) : ______ / âge (ans) : ______", "Pompe – panne constatée : ______", "Filtre – marque / modèle : ______ / ∅ cuve : ______", "Filtre – âge : ______ / état du sable : ______", "Vanne multivoies – marque / état : ______", "Système de traitement – type : ______ / âge : ______", "Électrolyseur – marque / taux de sel actuel : ______", "PAC – marque / modèle : ______ / âge : ______", "Volet – type / état : ______", "Photos du matériel défectueux réalisées"]
  }, {
    section: "🔄 Remplacement pompe",
    items: ["Débit requis calculé (volume bassin / 4h) : ______ m³/h", "Référence nouvelle pompe : ______", "Pompe vitesse variable (VEI) recommandée", "Raccordements hydrauliques ∅ : ______", "Manchons anti-vibratoires neufs", "Test de débit après installation"]
  }, {
    section: "🔄 Remplacement filtre",
    items: ["Diamètre filtre recommandé : ______", "Référence nouveau filtre : ______", "Type de média filtrant : sable / verre / billes", "Quantité de sable / média : ______ kg", "Vanne multivoies adaptée", "Manomètre neuf posé", "Test de contre-lavage effectué"]
  }, {
    section: "🔄 Remplacement traitement",
    items: ["Électrolyseur – référence : ______ / production Cl/h : ______", "Cellule d'électrolyse (seule ou boîtier complet)", "Régulation pH automatique – marque : ______", "Sondes pH / ORP remplacées", "Pompes doseuses – marque / débit : ______", "UV – puissance W : ______ / lampe neuve", "Analyseur connecté / Wi-Fi : ______"]
  }, {
    section: "🔄 Remplacement chauffage",
    items: ["Pompe à chaleur – référence : ______ / COP : ______", "PAC réversible (climatisation abri incluse)", "Vanne de by-pass posée", "Test de montée en température bassin"]
  }, {
    section: "🔄 Remplacement couverture / volet",
    items: ["Type de couverture choisie : ______", "Volet roulant immergé – réservation béton vérifiée", "Volet roulant hors-sol – emplacement coffre", "Couverture à barres – type de motorisation", "Lames : polycarbonate / alu / PVC (couleur : ______)", "Test motorisation / sécurité anti-pincement"]
  }, {
    section: "🔄 Remplacement éclairage",
    items: ["Nombre de projecteurs : ______", "Type : LED RGB / LED blanc chaud", "Niche(s) existante(s) compatibles ou à remplacer", "Test d'étanchéité après installation", "Programmation RGB / scénarios lumineux"]
  }, {
    section: "🔄 Robot nettoyeur",
    items: ["Robot fond seul / fond+parois / complet", "Référence robot : ______", "Alimentation : filaire / sur batterie", "Application mobile configurée", "Sac / filtre de rechange laissé"]
  }, {
    section: "🤝 Clôture intervention",
    items: ["Mise en service complète réalisée", "Démonstration au client", "Ancien matériel évacué", "Garantie constructeur enregistrée", "Bon d'intervention signé", "Facture / attestation TVA réduite si applicable"]
  }]
};

/* ════════════════════════════════════════════════════════
   API & utilitaires
   ════════════════════════════════════════════════════════ */
const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};

/* ── Keyword map pour la recherche produits ── */
const KEYWORD_MAP = [[/bonde.{0,10}fond/i, 'bonde fond'], [/skimmer/i, 'skimmer'], [/refoulement/i, 'buse refoulement'], [/buse.{0,10}balai|prise balai/i, 'prise balai'], [/filtre.{0,10}sable/i, 'filtre sable'], [/filtre.{0,10}cartouche/i, 'filtre cartouche'], [/filtre.{0,10}diatom/i, 'filtre diatomées'], [/sable.{0,10}filtration/i, 'sable filtration'], [/billes.{0,10}verre/i, 'billes verre filtration'], [/pompe.{0,10}vitesse.{0,10}variable|VEI/i, 'pompe vitesse variable'], [/pompe.{0,5}chaleur/i, 'pompe chaleur piscine'], [/pompe.{0,10}doseuse/i, 'pompe doseuse'], [/vanne.{0,10}multivoies/i, 'vanne multivoies'], [/électrolyseur|electrolyseur/i, 'électrolyseur sel'], [/cellule.{0,10}électro/i, 'cellule électrolyse'], [/robot.{0,10}nettoyeur|robot.{0,10}fond/i, 'robot piscine'], [/liner/i, 'liner piscine'], [/projecteur.{0,10}LED|spot LED/i, 'projecteur LED piscine'], [/alarme.{0,10}piscine/i, 'alarme piscine'], [/volet.{0,10}roulant/i, 'volet roulant piscine'], [/couverture.{0,10}bulle|couverture.{0,10}solaire/i, 'couverture solaire piscine'], [/bouchon.{0,10}hivern/i, 'bouchon hivernage'], [/flotteur.{0,10}antigel/i, 'flotteur antigel piscine'], [/algicide/i, 'algicide'], [/chlore.{0,10}choc|choc chlore/i, 'chlore choc'], [/galets.{0,10}chlore/i, 'galets chlore'], [/pH.{0,5}moins|pH-/i, 'pH moins acide'], [/floculant/i, 'floculant piscine'], [/anti.{0,5}calcaire/i, 'anti calcaire piscine'], [/anti.{0,5}phosphate/i, 'anti phosphates piscine'], [/sonde.{0,5}pH|sonde.{0,5}ORP/i, 'sonde pH ORP piscine'], [/UV|ultra.{0,5}violet/i, 'lampe UV piscine'], [/ozone/i, 'générateur ozone piscine'], [/manomètre/i, 'manomètre piscine'], [/préfiltre|panier.{0,10}filtre/i, 'préfiltre panier pompe'], [/margelles/i, 'margelle piscine'], [/douche.{0,10}solaire/i, 'douche solaire'], [/échelle|escalier.{0,10}inox/i, 'escalier inox piscine']];
function extractKeywords(itemText) {
  const clean = itemText.replace(/_{2,}/g, '').replace(/\(.*?\)/g, '').trim();
  for (const [pat, kw] of KEYWORD_MAP) {
    if (pat.test(clean)) return kw;
  }
  return clean.replace(/[:()\[\]0-9]/g, ' ').split(/\s+/).filter(w => w.length > 3).slice(0, 4).join(' ');
}
function sortBySupplier(products) {
  return [...products].sort((a, b) => {
    const aH = (a.suppliers || []).some(s => s.type === 'fluidra' || s.type === 'scp');
    const bH = (b.suppliers || []).some(s => s.type === 'fluidra' || s.type === 'scp');
    return aH && !bH ? -1 : !aH && bH ? 1 : 0;
  });
}
async function apiPost(url, params = {}) {
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'call',
      id: 1,
      params
    })
  });
  const d = await res.json();
  return d?.result;
}
async function searchOdooProducts(query, supplier = null) {
  try {
    const r = await apiPost(cfg.productsEndpoint || '/pool-checklist/products', {
      query,
      limit: 24,
      supplier
    });
    const prods = r?.products || [];
    if (prods.length) return {
      source: 'odoo',
      products: sortBySupplier(prods)
    };
    return null;
  } catch (e) {
    console.warn('products:', e);
    return null;
  }
}
async function suggestViaAI(itemText, sectionLabel) {
  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 900,
        system: `Expert équipements piscine (Lolirine Pool Store, Belgique). JSON uniquement sans markdown :
{"products":[{"ref":"","name":"Nom produit précis","category":"Cat","unit":"pièce|kg|L|m|m²|lot","note":"","supplier":"Fluidra|SCP|HTH|BWT|Hayward|Pentair|Zodiac|Astralpool"}]}
Max 8 produits. Priorité aux produits Fluidra/SIBO et SCP Bénélux.`,
        messages: [{
          role: 'user',
          content: `Section : ${sectionLabel}\nPoint : "${itemText}"\nProduits à prévoir ?`
        }]
      })
    });
    if (!res.ok) return null;
    const d = await res.json();
    const parsed = JSON.parse((d.content?.[0]?.text || '{}').replace(/```json|```/g, '').trim());
    const prods = (parsed.products || []).map(p => ({
      ...p,
      suppliers: p.supplier ? [{
        name: p.supplier,
        ref: p.ref || '',
        price: 0,
        type: /fluidra|sibo/i.test(p.supplier) ? 'fluidra' : /scp/i.test(p.supplier) ? 'scp' : 'other'
      }] : []
    }));
    return {
      source: 'ai',
      products: sortBySupplier(prods)
    };
  } catch (e) {
    console.warn('AI:', e);
    return null;
  }
}
async function searchPartners(query) {
  try {
    const r = await apiPost(cfg.partnersEndpoint || '/pool-checklist/partners', {
      query
    });
    return r?.partners || [];
  } catch (e) {
    return [];
  }
}

/* ── Validation TVA via VIES (endpoint Odoo natif) ── */
async function checkVatVies(vat) {
  if (!vat || vat.trim().length < 8) return null;
  try {
    const r = await apiPost('/web/dataset/call_kw', {
      model: 'res.partner',
      method: 'simple_vat_check',
      args: [vat.trim().toUpperCase()],
      kwargs: {}
    });
    return r;
  } catch (e) {
    return null;
  }
}
async function checkVatOdoo(vat) {
  if (!vat || vat.trim().length < 8) return null;
  try {
    // Utilise le module base_vat natif Odoo
    const r = await apiPost('/web/dataset/call_kw', {
      model: 'res.partner',
      method: 'check_vat',
      args: [],
      kwargs: {
        vat: vat.trim().toUpperCase()
      }
    });
    if (r?.vat_formatted || r?.name) {
      return {
        valid: true,
        name: r.name || '',
        address: r.address || '',
        vat: r.vat_formatted || vat
      };
    }
    return {
      valid: !!r,
      name: '',
      address: '',
      vat: vat
    };
  } catch (e) {
    return null;
  }
}

/* Auto-save localStorage */
const LS_KEY = 'lpc_draft_v2';
function lsSave(data) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({
      ...data,
      _ts: Date.now()
    }));
  } catch (e) {}
}
function lsLoad() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || 'null');
  } catch (e) {
    return null;
  }
}
function lsClear() {
  try {
    localStorage.removeItem(LS_KEY);
  } catch (e) {}
}

/* ── Statuts des points de contrôle ── */
const STATUS_CONFIG = {
  pending: {
    icon: '⬜',
    label: 'Non vérifié',
    bg: 'transparent',
    color: '#6b7a8d'
  },
  ok: {
    icon: '✅',
    label: 'Conforme',
    bg: '#dcfce7',
    color: '#166534'
  },
  warn: {
    icon: '⚠️',
    label: 'À surveiller',
    bg: '#fef3c7',
    color: '#92400e'
  },
  action: {
    icon: '❌',
    label: 'Action requise',
    bg: '#fee2e2',
    color: '#991b1b'
  }
};

/* ════════════════════════════════════════════════════════
   Composants UI réutilisables
   ════════════════════════════════════════════════════════ */

function SupplierBadge({
  type,
  name
}) {
  const C = {
    fluidra: {
      bg: '#dbeafe',
      color: '#1d4ed8',
      label: 'Fluidra/SIBO'
    },
    scp: {
      bg: '#dcfce7',
      color: '#166534',
      label: 'SCP Bénélux'
    },
    other: {
      bg: '#f3f4f6',
      color: '#6b7a8d',
      label: name
    }
  };
  const c = C[type] || C.other;
  return /*#__PURE__*/React.createElement("span", {
    style: {
      background: c.bg,
      color: c.color,
      borderRadius: 5,
      padding: '2px 7px',
      fontSize: 11,
      fontWeight: 700
    }
  }, c.label);
}

/* ── ImageZoom ── */
function ImageZoom({
  src,
  name,
  onClose
}) {
  return /*#__PURE__*/React.createElement("div", {
    onClick: onClose,
    style: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.92)',
      zIndex: 99999,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
      cursor: 'zoom-out'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: name,
    style: {
      maxWidth: '88vw',
      maxHeight: '78vh',
      objectFit: 'contain',
      borderRadius: 14,
      background: '#fff',
      padding: 16,
      boxShadow: '0 24px 80px rgba(0,0,0,.6)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      color: 'rgba(255,255,255,.9)',
      marginTop: 18,
      fontSize: 16,
      fontWeight: 700,
      textAlign: 'center'
    }
  }, name), /*#__PURE__*/React.createElement("div", {
    style: {
      color: 'rgba(255,255,255,.4)',
      marginTop: 6,
      fontSize: 12
    }
  }, "Cliquer pour fermer"));
}

/* ── Signature Canvas ── */
function SignatureCanvas({
  label,
  onSave
}) {
  const canvasRef = React.useRef(null);
  const drawing = React.useRef(false);
  const [hasContent, setHasContent] = React.useState(false);
  const getPos = (e, canvas) => {
    const rect = canvas.getBoundingClientRect();
    const src = e.touches ? e.touches[0] : e;
    return {
      x: src.clientX - rect.left,
      y: src.clientY - rect.top
    };
  };
  const start = e => {
    e.preventDefault();
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const {
      x,
      y
    } = getPos(e, canvas);
    ctx.beginPath();
    ctx.moveTo(x, y);
    drawing.current = true;
  };
  const draw = e => {
    if (!drawing.current) return;
    e.preventDefault();
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const {
      x,
      y
    } = getPos(e, canvas);
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1a2332';
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasContent(true);
  };
  const end = () => {
    drawing.current = false;
  };
  const clear = () => {
    const canvas = canvasRef.current;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    setHasContent(false);
    onSave(null);
  };
  const save = () => {
    if (!hasContent) return;
    onSave(canvasRef.current.toDataURL('image/png'));
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      fontWeight: 600
    }
  }, label), /*#__PURE__*/React.createElement("canvas", {
    ref: canvasRef,
    width: 320,
    height: 120,
    style: {
      border: '1.5px solid #dde4ed',
      borderRadius: 8,
      background: '#fafafa',
      touchAction: 'none',
      cursor: 'crosshair',
      width: '100%'
    },
    onMouseDown: start,
    onMouseMove: draw,
    onMouseUp: end,
    onMouseLeave: end,
    onTouchStart: start,
    onTouchMove: draw,
    onTouchEnd: end
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: clear,
    style: {
      background: 'none',
      border: '1px solid #dde4ed',
      borderRadius: 6,
      padding: '4px 10px',
      fontSize: 12,
      cursor: 'pointer',
      color: '#6b7a8d'
    }
  }, "\uD83D\uDDD1\uFE0F Effacer"), hasContent && /*#__PURE__*/React.createElement("button", {
    onClick: save,
    style: {
      background: '#0ea5e9',
      color: '#fff',
      border: 'none',
      borderRadius: 6,
      padding: '4px 12px',
      fontSize: 12,
      cursor: 'pointer',
      fontWeight: 600
    }
  }, "\u2713 Valider signature")));
}
function SuggDropdown({
  suggestions,
  onSelect
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '100%',
      left: 0,
      right: 0,
      background: '#fff',
      border: '1.5px solid #dde4ed',
      borderRadius: 8,
      boxShadow: '0 8px 24px rgba(0,0,0,.12)',
      zIndex: 2000,
      maxHeight: 220,
      overflowY: 'auto'
    }
  }, suggestions.map((p, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    onMouseDown: () => onSelect(p),
    style: {
      padding: '9px 12px',
      fontSize: 13,
      cursor: 'pointer',
      borderBottom: '1px solid #f0f4f8',
      display: 'flex',
      gap: 10,
      alignItems: 'flex-start'
    },
    onMouseOver: e => e.currentTarget.style.background = '#f0f9ff',
    onMouseOut: e => e.currentTarget.style.background = '#fff'
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 18,
      flexShrink: 0
    }
  }, "\uD83D\uDC64"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      color: '#1a2332'
    }
  }, p.name), p.street && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#6b7a8d',
      marginTop: 1
    }
  }, p.street, ", ", p.zip, " ", p.city), (p.phone || p.mobile) && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#6b7a8d'
    }
  }, "\uD83D\uDCDE ", p.phone || p.mobile)))));
}

/* ── Autocomplete adresse (Google Places avec split rue/cp/ville/pays) ── */
function AddressAutocomplete({
  valueRue,
  valueCp,
  valueVille,
  valuePays,
  onChangeFull,
  placeholder,
  inputStyle
}) {
  const inputRef = React.useRef(null);
  const [localVal, setLocalVal] = React.useState(valueRue || '');
  const [ready, setReady] = React.useState(false);
  React.useEffect(() => {
    setLocalVal(valueRue || '');
  }, [valueRue]);
  React.useEffect(() => {
    const initAC = () => {
      if (!inputRef.current || !window.google?.maps?.places) return;
      const ac = new window.google.maps.places.Autocomplete(inputRef.current, {
        types: ['address'],
        componentRestrictions: {
          country: ['be', 'fr', 'lu', 'nl', 'de']
        },
        fields: ['address_components', 'formatted_address']
      });
      ac.addListener('place_changed', () => {
        const place = ac.getPlace();
        if (!place.address_components) return;
        const get = types => {
          const c = place.address_components.find(c => types.some(t => c.types.includes(t)));
          return c ? c.long_name : '';
        };
        const streetNum = get(['street_number']);
        const route = get(['route']);
        const rue = [route, streetNum].filter(Boolean).join(' ');
        const cp = get(['postal_code']);
        const ville = get(['locality', 'postal_town', 'sublocality']);
        const pays = get(['country']);
        onChangeFull({
          rue,
          cp,
          ville,
          pays
        });
        setLocalVal(rue);
      });
      setReady(true);
    };
    if (window.GOOGLE_PLACES_READY) {
      initAC();
    } else {
      document.addEventListener('googlePlacesReady', initAC, {
        once: true
      });
      // Retry si déjà chargé mais événement manqué
      setTimeout(() => {
        if (window.google?.maps?.places) initAC();
      }, 1000);
    }
    return () => {
      document.removeEventListener('googlePlacesReady', initAC);
    };
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'contents'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg full"
  }, /*#__PURE__*/React.createElement("label", null, "Rue ", /*#__PURE__*/React.createElement("span", {
    className: "lpc-required"
  }, "*")), /*#__PURE__*/React.createElement("input", {
    ref: inputRef,
    value: localVal,
    onChange: e => {
      setLocalVal(e.target.value);
      onChangeFull({
        rue: e.target.value,
        cp: valueCp,
        ville: valueVille,
        pays: valuePays
      });
    },
    placeholder: "Rue de la Piscine 12",
    style: inputStyle
  }), !ready && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#9ca3af',
      marginTop: 3
    }
  }, "\uD83D\uDCA1 Tapez l'adresse \u2014 autocompl\xE9tion Google Places")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg"
  }, /*#__PURE__*/React.createElement("label", null, "Code postal"), /*#__PURE__*/React.createElement("input", {
    value: valueCp,
    onChange: e => onChangeFull({
      rue: localVal,
      cp: e.target.value,
      ville: valueVille,
      pays: valuePays
    }),
    placeholder: "5000",
    style: inputStyle
  })), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg"
  }, /*#__PURE__*/React.createElement("label", null, "Ville"), /*#__PURE__*/React.createElement("input", {
    value: valueVille,
    onChange: e => onChangeFull({
      rue: localVal,
      cp: valueCp,
      ville: e.target.value,
      pays: valuePays
    }),
    placeholder: "Namur",
    style: inputStyle
  })), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg full"
  }, /*#__PURE__*/React.createElement("label", null, "Pays"), /*#__PURE__*/React.createElement("select", {
    value: valuePays,
    onChange: e => onChangeFull({
      rue: localVal,
      cp: valueCp,
      ville: valueVille,
      pays: e.target.value
    }),
    style: {
      ...inputStyle,
      cursor: 'pointer'
    }
  }, ['Belgique', 'France', 'Luxembourg', 'Pays-Bas', 'Allemagne', 'Suisse'].map(p => /*#__PURE__*/React.createElement("option", {
    key: p,
    value: p
  }, p)))));
}

/* ════════════════════════════════════════════════════════
   QuoteModal — Main d'œuvre, évacuation, déplacement
   ════════════════════════════════════════════════════════ */

/* Calcul frais de déplacement depuis Namur */
function calcDeplacementFee(km) {
  if (!km || km <= 0) return 0;
  if (km <= 30) return 50;
  const beyond = km - 30;
  const slices = Math.ceil(beyond / 5);
  return 50 + slices * 10;
}
function QuoteModal({
  client,
  allProds,
  reportId,
  onClose,
  onSuccess
}) {
  const [mainOeuvre, setMainOeuvre] = React.useState({
    enabled: false,
    heures: 0,
    tauxHoraire: 55,
    forfait: 0,
    mode: 'horaire'
  });
  const [evacuation, setEvacuation] = React.useState({
    mode: 'forfait',
    montant: 150
  }); // 'forfait'|'client'|'aucune'
  const [deplacement, setDeplacement] = React.useState({
    enabled: false,
    km: 0,
    fee: 0,
    autoCalc: true
  });
  const [notes, setNotes] = React.useState('');
  const [creating, setCreating] = React.useState(false);
  const [distLoading, setDistLoading] = React.useState(false);

  /* Calcul automatique distance via Google Maps */
  const calcDistance = async () => {
    if (!client.rue && !client.ville) return;
    if (!window.google?.maps) return;
    setDistLoading(true);
    try {
      const origin = 'Namur, Belgique';
      const dest = [client.rue, client.cp, client.ville, client.pays].filter(Boolean).join(', ');
      const svc = new window.google.maps.DistanceMatrixService();
      svc.getDistanceMatrix({
        origins: [origin],
        destinations: [dest],
        travelMode: window.google.maps.TravelMode.DRIVING,
        unitSystem: window.google.maps.UnitSystem.METRIC
      }, (res, status) => {
        if (status === 'OK' && res.rows[0]?.elements[0]?.status === 'OK') {
          const km = Math.round(res.rows[0].elements[0].distance.value / 1000);
          setDeplacement(p => ({
            ...p,
            km,
            fee: calcDeplacementFee(km),
            enabled: true
          }));
        }
        setDistLoading(false);
      });
    } catch (e) {
      setDistLoading(false);
    }
  };

  /* Recalcul fee quand km change */
  React.useEffect(() => {
    if (deplacement.autoCalc) {
      setDeplacement(p => ({
        ...p,
        fee: calcDeplacementFee(p.km)
      }));
    }
  }, [deplacement.km, deplacement.autoCalc]);

  /* Total estimatif */
  const prodsTotal = allProds.reduce((a, p) => a + (p.price || 0) * (p.qty || 1), 0);
  const moTotal = mainOeuvre.enabled ? mainOeuvre.mode === 'horaire' ? mainOeuvre.heures * mainOeuvre.tauxHoraire : mainOeuvre.forfait : 0;
  const evacTotal = evacuation.mode === 'forfait' ? evacuation.montant : 0;
  const deplTotal = deplacement.enabled ? deplacement.fee : 0;
  const grandTotal = prodsTotal + moTotal + evacTotal + deplTotal;
  const handleCreate = async () => {
    setCreating(true);
    const extraLines = [];

    /* Main d'œuvre */
    if (mainOeuvre.enabled) {
      if (mainOeuvre.mode === 'horaire' && mainOeuvre.heures > 0) {
        extraLines.push({
          name: `Main d'œuvre — ${mainOeuvre.heures}h × ${mainOeuvre.tauxHoraire} €/h`,
          qty: mainOeuvre.heures,
          price: mainOeuvre.tauxHoraire,
          ref: 'MO-HORAIRE',
          type: 'service'
        });
      } else if (mainOeuvre.mode === 'forfait' && mainOeuvre.forfait > 0) {
        extraLines.push({
          name: "Main d'œuvre — Forfait",
          qty: 1,
          price: mainOeuvre.forfait,
          ref: 'MO-FORFAIT',
          type: 'service'
        });
      }
    }

    /* Évacuation */
    if (evacuation.mode === 'forfait' && evacuation.montant > 0) {
      extraLines.push({
        name: "Forfait évacuation des déchets de chantier",
        qty: 1,
        price: evacuation.montant,
        ref: 'EVAC-FORFAIT',
        type: 'service'
      });
    } else if (evacuation.mode === 'client') {
      extraLines.push({
        name: "Évacuation des déchets — À charge du client",
        qty: 1,
        price: 0,
        ref: 'EVAC-CLIENT',
        type: 'service'
      });
    }

    /* Frais de déplacement */
    if (deplacement.enabled && deplacement.fee > 0) {
      const addr = [client.rue, client.cp, client.ville].filter(Boolean).join(', ');
      extraLines.push({
        name: `Frais de déplacement${deplacement.km > 0 ? ` (${deplacement.km} km depuis Namur)` : ''}${addr ? ' — ' + addr : ''}`,
        qty: 1,
        price: deplacement.fee,
        ref: 'DEPL',
        type: 'service'
      });
    }
    const r = await apiPost(cfg.quoteEndpoint || '/pool-checklist/create-quote', {
      report_id: reportId,
      products: allProds,
      extra_lines: extraLines,
      notes: notes,
      client: {
        ...client,
        nom: [client.prenom, client.nom].filter(Boolean).join(' '),
        adresse: [client.rue, client.cp, client.ville, client.pays].filter(Boolean).join(', ')
      }
    });
    setCreating(false);
    if (r?.success) onSuccess(r);else alert('Erreur : ' + (r?.error || 'inconnue'));
  };
  const secStyle = {
    background: '#fff',
    borderRadius: 12,
    padding: '16px 18px',
    marginBottom: 12,
    border: '1.5px solid #dde4ed'
  };
  const secHdr = {
    fontWeight: 700,
    fontSize: 14,
    marginBottom: 12,
    display: 'flex',
    alignItems: 'center',
    gap: 8
  };
  const inputS = {
    border: '1.5px solid #e5e7eb',
    borderRadius: 8,
    padding: '8px 12px',
    fontFamily: 'inherit',
    fontSize: 14,
    background: '#f9fafb',
    outline: 'none',
    width: '100%'
  };
  const numS = {
    border: '1.5px solid #e5e7eb',
    borderRadius: 8,
    padding: '8px 12px',
    fontFamily: 'inherit',
    fontSize: 14,
    background: '#f9fafb',
    outline: 'none',
    width: '90px',
    textAlign: 'center'
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(10,20,40,0.7)',
      zIndex: 9998,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#f0f4f8',
      borderRadius: 20,
      width: '100%',
      maxWidth: 680,
      maxHeight: '92vh',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 28px 90px rgba(0,0,0,.35)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 22px',
      borderBottom: '1.5px solid #dde4ed',
      background: '#fff',
      display: 'flex',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      fontSize: 16
    }
  }, "\uD83D\uDCCB Cr\xE9er un devis Odoo"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginTop: 2
    }
  }, allProds.length, " produit(s) \xB7 Total mat\xE9riaux : ", /*#__PURE__*/React.createElement("strong", null, allProds.reduce((a, p) => a + (p.price || 0) * (p.qty || 1), 0).toFixed(2), " \u20AC"))), /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      background: 'none',
      border: '1.5px solid #dde4ed',
      borderRadius: 8,
      padding: '5px 13px',
      cursor: 'pointer',
      fontSize: 14,
      color: '#6b7a8d'
    }
  }, "\u2715")), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: 'auto',
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: secStyle
  }, /*#__PURE__*/React.createElement("div", {
    style: secHdr
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: mainOeuvre.enabled,
    onChange: e => setMainOeuvre(p => ({
      ...p,
      enabled: e.target.checked
    })),
    style: {
      width: 16,
      height: 16,
      accentColor: '#0ea5e9',
      cursor: 'pointer'
    }
  }), "\uD83D\uDD28 Main d'\u0153uvre"), mainOeuvre.enabled && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginBottom: 12
    }
  }, [['horaire', "À l'heure"], ['forfait', 'Forfait']].map(([v, l]) => /*#__PURE__*/React.createElement("button", {
    key: v,
    onClick: () => setMainOeuvre(p => ({
      ...p,
      mode: v
    })),
    style: {
      padding: '6px 14px',
      borderRadius: 20,
      border: `1.5px solid ${mainOeuvre.mode === v ? '#0ea5e9' : '#dde4ed'}`,
      background: mainOeuvre.mode === v ? '#0ea5e9' : '#fff',
      color: mainOeuvre.mode === v ? '#fff' : '#6b7a8d',
      cursor: 'pointer',
      fontSize: 13,
      fontWeight: 600
    }
  }, l))), mainOeuvre.mode === 'horaire' ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr 1fr',
      gap: 10,
      alignItems: 'end'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginBottom: 5,
      fontWeight: 600
    }
  }, "Nombre d'heures"), /*#__PURE__*/React.createElement("input", {
    type: "number",
    min: "0",
    step: "0.5",
    value: mainOeuvre.heures,
    onChange: e => setMainOeuvre(p => ({
      ...p,
      heures: parseFloat(e.target.value) || 0
    })),
    style: numS
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginBottom: 5,
      fontWeight: 600
    }
  }, "Taux horaire (\u20AC/h)"), /*#__PURE__*/React.createElement("input", {
    type: "number",
    min: "0",
    value: mainOeuvre.tauxHoraire,
    onChange: e => setMainOeuvre(p => ({
      ...p,
      tauxHoraire: parseFloat(e.target.value) || 0
    })),
    style: numS
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginBottom: 5,
      fontWeight: 600
    }
  }, "Total"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      fontSize: 16,
      color: '#0ea5e9',
      padding: '8px 0'
    }
  }, (mainOeuvre.heures * mainOeuvre.tauxHoraire).toFixed(2), " \u20AC"))) : /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 10,
      alignItems: 'end'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginBottom: 5,
      fontWeight: 600
    }
  }, "Montant forfait (\u20AC HT)"), /*#__PURE__*/React.createElement("input", {
    type: "number",
    min: "0",
    value: mainOeuvre.forfait,
    onChange: e => setMainOeuvre(p => ({
      ...p,
      forfait: parseFloat(e.target.value) || 0
    })),
    style: numS
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      fontSize: 16,
      color: '#0ea5e9',
      padding: '8px 0'
    }
  }, mainOeuvre.forfait.toFixed(2), " \u20AC")))), /*#__PURE__*/React.createElement("div", {
    style: secStyle
  }, /*#__PURE__*/React.createElement("div", {
    style: secHdr
  }, "\uD83D\uDDD1\uFE0F \xC9vacuation des d\xE9chets de chantier"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, [['forfait', '💰 Forfait évacuation (à facturer)'], ['client', '🚛 Évacuation prise en charge par le client'], ['aucune', '➖ Sans évacuation']].map(([v, l]) => /*#__PURE__*/React.createElement("label", {
    key: v,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      cursor: 'pointer',
      padding: '10px 14px',
      borderRadius: 9,
      border: `1.5px solid ${evacuation.mode === v ? '#0ea5e9' : '#e5e7eb'}`,
      background: evacuation.mode === v ? 'rgba(14,165,233,0.04)' : '#fff',
      transition: 'all .15s'
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "radio",
    name: "evacuation",
    value: v,
    checked: evacuation.mode === v,
    onChange: () => setEvacuation(p => ({
      ...p,
      mode: v
    })),
    style: {
      accentColor: '#0ea5e9'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 600,
      fontSize: 13,
      flex: 1
    }
  }, l), v === 'forfait' && evacuation.mode === 'forfait' && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8
    },
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("input", {
    type: "number",
    min: "0",
    value: evacuation.montant,
    onChange: e => setEvacuation(p => ({
      ...p,
      montant: parseFloat(e.target.value) || 0
    })),
    style: {
      ...numS,
      width: 80
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: '#6b7a8d',
      fontWeight: 600
    }
  }, "\u20AC")), v === 'forfait' && evacuation.mode !== 'forfait' && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: '#9ca3af'
    }
  }, evacuation.montant.toFixed(2), " \u20AC"))))), /*#__PURE__*/React.createElement("div", {
    style: secStyle
  }, /*#__PURE__*/React.createElement("div", {
    style: secHdr
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: deplacement.enabled,
    onChange: e => setDeplacement(p => ({
      ...p,
      enabled: e.target.checked
    })),
    style: {
      width: 16,
      height: 16,
      accentColor: '#0ea5e9',
      cursor: 'pointer'
    }
  }), "\uD83D\uDE97 Frais de d\xE9placement", /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      color: '#9ca3af',
      fontWeight: 400,
      marginLeft: 4
    }
  }, "(depuis Namur \xB7 \u226430 km = 50 \u20AC \xB7 +10 \u20AC/5 km au-del\xE0)")), deplacement.enabled && /*#__PURE__*/React.createElement("div", null, window.google?.maps && client.rue && /*#__PURE__*/React.createElement("button", {
    onClick: calcDistance,
    disabled: distLoading,
    style: {
      background: '#f0f9ff',
      border: '1.5px solid #bae6fd',
      borderRadius: 8,
      padding: '7px 14px',
      cursor: 'pointer',
      fontSize: 13,
      fontWeight: 600,
      color: '#0369a1',
      marginBottom: 12,
      display: 'flex',
      alignItems: 'center',
      gap: 7
    }
  }, distLoading ? '⟳ Calcul en cours…' : '📍 Calculer la distance automatiquement'), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr 1fr',
      gap: 10,
      alignItems: 'end'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginBottom: 5,
      fontWeight: 600
    }
  }, "Distance (km)"), /*#__PURE__*/React.createElement("input", {
    type: "number",
    min: "0",
    value: deplacement.km,
    onChange: e => {
      const km = parseFloat(e.target.value) || 0;
      setDeplacement(p => ({
        ...p,
        km,
        fee: p.autoCalc ? calcDeplacementFee(km) : p.fee
      }));
    },
    style: numS
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginBottom: 5,
      fontWeight: 600
    }
  }, "Montant (\u20AC)", /*#__PURE__*/React.createElement("label", {
    style: {
      marginLeft: 8,
      fontSize: 11,
      fontWeight: 400,
      cursor: 'pointer'
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: deplacement.autoCalc,
    onChange: e => setDeplacement(p => ({
      ...p,
      autoCalc: e.target.checked
    })),
    style: {
      marginRight: 3,
      accentColor: '#0ea5e9'
    }
  }), "Auto")), /*#__PURE__*/React.createElement("input", {
    type: "number",
    min: "0",
    value: deplacement.fee,
    readOnly: deplacement.autoCalc,
    onChange: e => !deplacement.autoCalc && setDeplacement(p => ({
      ...p,
      fee: parseFloat(e.target.value) || 0
    })),
    style: {
      ...numS,
      background: deplacement.autoCalc ? '#f3f4f6' : '#f9fafb',
      cursor: deplacement.autoCalc ? 'not-allowed' : 'text'
    }
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginBottom: 5,
      fontWeight: 600
    }
  }, "Bar\xE8me appliqu\xE9"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#0ea5e9',
      fontWeight: 600,
      padding: '8px 0'
    }
  }, deplacement.km <= 30 && deplacement.km > 0 ? '≤ 30 km → 50 €' : deplacement.km > 30 ? `${deplacement.km} km → 50 € + ${Math.ceil((deplacement.km - 30) / 5)}×10 €` : '—'))), (client.rue || client.ville) && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#6b7a8d',
      marginTop: 8,
      padding: '6px 10px',
      background: '#f8fafc',
      borderRadius: 6
    }
  }, "\uD83D\uDCCD Chantier : ", [client.rue, client.cp, client.ville].filter(Boolean).join(', ')))), allProds.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: secStyle
  }, /*#__PURE__*/React.createElement("div", {
    style: secHdr
  }, "\uD83D\uDCE6 Mat\xE9riaux & produits (", allProds.length, " article(s))"), /*#__PURE__*/React.createElement("div", {
    style: {
      maxHeight: 180,
      overflowY: 'auto'
    }
  }, /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    style: {
      background: '#f8fafc'
    }
  }, /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'left',
      padding: '5px 8px',
      color: '#6b7a8d',
      fontSize: 11,
      fontWeight: 700,
      textTransform: 'uppercase'
    }
  }, "D\xE9signation"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'center',
      padding: '5px 8px',
      color: '#6b7a8d',
      fontSize: 11,
      fontWeight: 700
    }
  }, "Qt\xE9"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right',
      padding: '5px 8px',
      color: '#6b7a8d',
      fontSize: 11,
      fontWeight: 700
    }
  }, "P.U. HT"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right',
      padding: '5px 8px',
      color: '#6b7a8d',
      fontSize: 11,
      fontWeight: 700
    }
  }, "Total HT"))), /*#__PURE__*/React.createElement("tbody", null, allProds.map((p, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      borderBottom: '1px solid #f0f4f8'
    }
  }, /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '5px 8px',
      fontWeight: 500
    }
  }, p.name, p.ref && /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 6,
      background: '#f0f4f8',
      padding: '1px 5px',
      borderRadius: 3,
      fontSize: 11,
      fontFamily: 'monospace',
      color: '#6b7a8d'
    }
  }, p.ref)), /*#__PURE__*/React.createElement("td", {
    style: {
      textAlign: 'center',
      padding: '5px 8px'
    }
  }, p.qty), /*#__PURE__*/React.createElement("td", {
    style: {
      textAlign: 'right',
      padding: '5px 8px',
      color: '#0ea5e9',
      fontWeight: 600
    }
  }, p.price > 0 ? `${p.price.toFixed(2)} €` : '—'), /*#__PURE__*/React.createElement("td", {
    style: {
      textAlign: 'right',
      padding: '5px 8px',
      fontWeight: 700
    }
  }, p.price > 0 ? `${(p.price * (p.qty || 1)).toFixed(2)} €` : '—'))))))), /*#__PURE__*/React.createElement("div", {
    style: secStyle
  }, /*#__PURE__*/React.createElement("div", {
    style: secHdr
  }, "\uD83D\uDCDD Notes internes pour le devis"), /*#__PURE__*/React.createElement("textarea", {
    value: notes,
    onChange: e => setNotes(e.target.value),
    placeholder: "Conditions particuli\xE8res, d\xE9lais, remarques pour le devis\u2026",
    style: {
      width: '100%',
      minHeight: 60,
      border: '1.5px solid #e5e7eb',
      borderRadius: 8,
      padding: '9px 12px',
      fontFamily: 'inherit',
      fontSize: 13,
      resize: 'vertical',
      background: '#f9fafb',
      outline: 'none'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'linear-gradient(135deg,#0ea5e9,#0369a1)',
      borderRadius: 12,
      padding: '16px 20px',
      color: '#fff'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      opacity: .85,
      marginBottom: 8
    }
  }, "R\xE9capitulatif estimatif HT"), prodsTotal > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: 4,
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("span", null, "Mat\xE9riaux & produits"), /*#__PURE__*/React.createElement("strong", null, prodsTotal.toFixed(2), " \u20AC")), moTotal > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: 4,
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("span", null, "Main d'\u0153uvre"), /*#__PURE__*/React.createElement("strong", null, moTotal.toFixed(2), " \u20AC")), evacTotal > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: 4,
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("span", null, "\xC9vacuation d\xE9chets"), /*#__PURE__*/React.createElement("strong", null, evacTotal.toFixed(2), " \u20AC")), deplTotal > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: 4,
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("span", null, "Frais de d\xE9placement"), /*#__PURE__*/React.createElement("strong", null, deplTotal.toFixed(2), " \u20AC")), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: '1px solid rgba(255,255,255,.3)',
      marginTop: 8,
      paddingTop: 8,
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: 16,
      fontWeight: 700
    }
  }, /*#__PURE__*/React.createElement("span", null, "Total estimatif HT"), /*#__PURE__*/React.createElement("span", null, grandTotal.toFixed(2), " \u20AC")))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '13px 22px',
      borderTop: '1.5px solid #dde4ed',
      display: 'flex',
      gap: 10,
      background: '#fff'
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      background: 'none',
      border: '1.5px solid #dde4ed',
      borderRadius: 9,
      padding: '10px 18px',
      cursor: 'pointer',
      fontFamily: 'inherit',
      fontSize: 14,
      fontWeight: 600
    }
  }, "Annuler"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: handleCreate,
    disabled: creating,
    style: {
      background: creating ? '#d1d5db' : '#059669',
      color: '#fff',
      border: 'none',
      borderRadius: 9,
      padding: '10px 24px',
      fontWeight: 700,
      cursor: creating ? 'not-allowed' : 'pointer',
      fontFamily: 'inherit',
      fontSize: 14,
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, creating ? '⟳ Création…' : '✅ Créer le devis Odoo'))));
}

/* ── Modal historique des fiches ── */
function HistoryModal({
  onLoad,
  onClose
}) {
  const [reports, setReports] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiPost(cfg.listEndpoint || '/pool-checklist/list', {
      limit: 30
    }).then(r => {
      setReports(r?.reports || []);
      setLoading(false);
    });
  }, []);
  const intColors = {
    construction: '#0ea5e9',
    renovation: '#f59e0b',
    entretien: '#10b981',
    hivernage: '#6366f1',
    remise_en_route: '#f97316',
    materiel: '#ec4899'
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(10,20,40,0.65)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#f0f4f8',
      borderRadius: 20,
      width: '100%',
      maxWidth: 720,
      maxHeight: '85vh',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 24px 80px rgba(0,0,0,.3)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 22px',
      borderBottom: '1.5px solid #dde4ed',
      background: '#fff',
      display: 'flex',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      fontWeight: 700,
      fontSize: 16
    }
  }, "\uD83D\uDCCB Fiches de visite sauvegard\xE9es"), /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      background: 'none',
      border: '1.5px solid #dde4ed',
      borderRadius: 8,
      padding: '5px 13px',
      cursor: 'pointer',
      fontSize: 14,
      color: '#6b7a8d'
    }
  }, "\u2715")), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: 'auto',
      padding: 16
    }
  }, loading && /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      padding: 40,
      color: '#6b7a8d',
      fontSize: 28
    }
  }, "\uD83D\uDD04"), !loading && reports.length === 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      padding: 40,
      color: '#6b7a8d'
    }
  }, "Aucune fiche sauvegard\xE9e"), reports.map(r => /*#__PURE__*/React.createElement("div", {
    key: r.id,
    onClick: () => onLoad(r.id),
    style: {
      background: '#fff',
      borderRadius: 12,
      padding: '13px 16px',
      marginBottom: 8,
      cursor: 'pointer',
      border: '1.5px solid #dde4ed',
      transition: 'all .15s',
      display: 'flex',
      gap: 12,
      alignItems: 'center'
    },
    onMouseOver: e => e.currentTarget.style.borderColor = '#0ea5e9',
    onMouseOut: e => e.currentTarget.style.borderColor = '#dde4ed'
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: intColors[r.intervention_type] || '#6b7a8d',
      flexShrink: 0
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      fontSize: 13
    }
  }, r.partner_name || 'Sans nom'), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#6b7a8d',
      marginTop: 2
    }
  }, r.name, " \xB7 ", r.date, " \xB7 ", r.intervention_type)), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'right',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 700,
      color: r.state === 'done' ? '#059669' : '#f59e0b',
      background: r.state === 'done' ? '#dcfce7' : '#fef3c7',
      padding: '2px 8px',
      borderRadius: 10
    }
  }, r.state === 'done' ? '✅ Validée' : '📝 Brouillon'), r.completion_pct > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#6b7a8d',
      marginTop: 3
    }
  }, r.completion_pct, "% compl\xE9t\xE9"), r.items_action > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#ef4444',
      fontWeight: 600
    }
  }, "\u26A0\uFE0F ", r.items_action, " action(s)")))))));
}

/* ════════════════════════════════════════════════════════
   ProductPanel (version complète)
   ════════════════════════════════════════════════════════ */
function ProductPanel({
  itemText,
  sectionLabel,
  onAdd,
  onClose
}) {
  const autoKw = React.useMemo(() => extractKeywords(itemText), [itemText]);
  const [q, setQ] = React.useState(autoKw);
  const [allResults, setAll] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [source, setSource] = React.useState(null);
  const [tab, setTab] = React.useState('all');
  const [sel, setSel] = React.useState({});
  const [qtys, setQtys] = React.useState({});
  const [zoom, setZoom] = React.useState(null);
  const [openCats, setOpenCats] = React.useState({}); // catégories ouvertes

  const search = async query => {
    if (!query.trim()) return;
    setLoading(true);
    setAll([]);
    setSource(null);
    setSel({});
    setQtys({});
    try {
      let r = await searchOdooProducts(query);
      if (!r) r = await suggestViaAI(itemText, sectionLabel);
      const prods = r?.products || [];
      setAll(prods);
      setSource(r?.source || null);
      // Ouvrir auto la 1ère catégorie avec fournisseur
      const firstWithSupplier = prods.find(p => (p.suppliers || []).some(s => s.type === 'fluidra' || s.type === 'scp'));
      if (firstWithSupplier) {
        setOpenCats({
          [firstWithSupplier.category || 'Général']: true
        });
      }
    } catch (e) {
      setAll([]);
    }
    setLoading(false);
  };
  React.useEffect(() => {
    search(autoKw);
  }, []);

  // Filtrage par onglet fournisseur
  const results = React.useMemo(() => {
    if (tab === 'all') return allResults;
    return allResults.filter(p => (p.suppliers || []).some(s => s.type === tab));
  }, [allResults, tab]);

  // Comptages
  const counts = React.useMemo(() => ({
    all: allResults.length,
    fluidra: allResults.filter(p => (p.suppliers || []).some(s => s.type === 'fluidra')).length,
    scp: allResults.filter(p => (p.suppliers || []).some(s => s.type === 'scp')).length
  }), [allResults]);

  // Groupement par catégorie — fournisseurs connus en premier dans chaque groupe
  const grouped = React.useMemo(() => {
    const groups = {};
    results.forEach(p => {
      const cat = p.category || 'Général';
      if (!groups[cat]) groups[cat] = {
        withSupplier: [],
        other: []
      };
      const hasS = (p.suppliers || []).some(s => s.type === 'fluidra' || s.type === 'scp');
      if (hasS) groups[cat].withSupplier.push(p);else groups[cat].other.push(p);
    });
    // Trier les catégories : celles avec fournisseurs connus en tête
    return Object.entries(groups).sort(([, a], [, b]) => b.withSupplier.length - a.withSupplier.length);
  }, [results]);
  const toggleCat = cat => setOpenCats(p => ({
    ...p,
    [cat]: !p[cat]
  }));
  const toggle = uid => setSel(p => ({
    ...p,
    [uid]: !p[uid]
  }));
  const setQty = (uid, v) => setQtys(p => ({
    ...p,
    [uid]: v
  }));
  const selCount = Object.values(sel).filter(Boolean).length;

  // uid unique = index global
  const productUid = p => `${p.id || p.name}_${p.ref || ''}`;
  const confirm = () => {
    const added = results.filter(p => sel[productUid(p)]).map(p => ({
      ...p,
      qty: Number(qtys[productUid(p)] || 1)
    }));
    onAdd(added);
    onClose();
  };
  const TAB_S = (active, color = '#0ea5e9') => ({
    padding: '7px 14px',
    border: 'none',
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 13,
    fontWeight: 600,
    background: 'transparent',
    borderBottom: `3px solid ${active ? color : 'transparent'}`,
    color: active ? color : '#6b7a8d',
    transition: 'all .15s',
    whiteSpace: 'nowrap'
  });

  // Composant ligne produit (liste déroulante)
  const ProductRow = ({
    p,
    uid
  }) => {
    const hasS = (p.suppliers || []).some(s => s.type === 'fluidra' || s.type === 'scp');
    const mainS = (p.suppliers || []).find(s => s.type !== 'other') || (p.suppliers || [])[0];
    const isSelected = !!sel[uid];
    return /*#__PURE__*/React.createElement("div", {
      onClick: () => toggle(uid),
      style: {
        display: 'flex',
        gap: 0,
        borderRadius: 10,
        overflow: 'hidden',
        border: `2px solid ${isSelected ? '#0ea5e9' : hasS ? '#bfdbfe' : '#e8edf3'}`,
        background: isSelected ? 'rgba(14,165,233,0.04)' : '#fff',
        boxShadow: isSelected ? '0 4px 14px rgba(14,165,233,.15)' : hasS ? '0 2px 8px rgba(37,99,235,0.06)' : '0 1px 3px rgba(0,0,0,.04)',
        cursor: 'pointer',
        transition: 'all .18s',
        marginBottom: 6
      }
    }, hasS && /*#__PURE__*/React.createElement("div", {
      style: {
        width: 4,
        flexShrink: 0,
        background: (p.suppliers || []).find(s => s.type === 'fluidra') ? '#1d4ed8' : '#16a34a'
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        width: 80,
        flexShrink: 0,
        background: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        borderRight: '1px solid #f0f4f8',
        minHeight: 72
      }
    }, p.image ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("img", {
      src: p.image,
      alt: p.name,
      style: {
        maxWidth: 72,
        maxHeight: 64,
        objectFit: 'contain',
        padding: 4
      }
    }), /*#__PURE__*/React.createElement("button", {
      onClick: e => {
        e.stopPropagation();
        setZoom({
          src: p.image,
          name: p.name
        });
      },
      style: {
        position: 'absolute',
        bottom: 2,
        right: 2,
        background: 'rgba(0,0,0,.45)',
        border: 'none',
        borderRadius: 4,
        padding: '2px 5px',
        cursor: 'pointer',
        fontSize: 11,
        color: '#fff',
        lineHeight: 1
      }
    }, "\uD83D\uDD0D")) : /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 26,
        opacity: .25
      }
    }, "\uD83C\uDFCA")), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        padding: '9px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        width: 19,
        height: 19,
        border: `2px solid ${isSelected ? '#0ea5e9' : '#d1d5db'}`,
        borderRadius: 5,
        background: isSelected ? '#0ea5e9' : '#fff',
        display: 'grid',
        placeItems: 'center',
        flexShrink: 0,
        marginTop: 2
      }
    }, isSelected && /*#__PURE__*/React.createElement("span", {
      style: {
        color: '#fff',
        fontSize: 11,
        fontWeight: 800
      }
    }, "\u2713")), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 700,
        fontSize: 13,
        lineHeight: 1.3,
        color: '#1a2332'
      }
    }, p.name), p.category && /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        color: '#94a3b8',
        marginTop: 1
      }
    }, p.category)), p.price > 0 && /*#__PURE__*/React.createElement("span", {
      style: {
        fontWeight: 700,
        fontSize: 14,
        color: '#0ea5e9',
        flexShrink: 0,
        whiteSpace: 'nowrap'
      }
    }, p.price.toFixed(2), " \u20AC")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 5,
        flexWrap: 'wrap',
        alignItems: 'center'
      }
    }, p.ref && /*#__PURE__*/React.createElement("span", {
      style: {
        background: '#f0f4f8',
        padding: '1px 6px',
        borderRadius: 4,
        fontSize: 11,
        fontFamily: 'monospace',
        color: '#64748b'
      }
    }, p.ref), (p.suppliers || []).map((s, si) => /*#__PURE__*/React.createElement("span", {
      key: si,
      style: {
        display: 'inline-flex',
        gap: 4,
        alignItems: 'center'
      }
    }, /*#__PURE__*/React.createElement(SupplierBadge, {
      type: s.type,
      name: s.name
    }), s.ref && /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: 'monospace',
        fontSize: 11,
        color: '#64748b'
      }
    }, "#", s.ref), s.price > 0 && /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 11,
        color: '#059669',
        fontWeight: 700
      }
    }, s.price.toFixed(2), " \u20AC")))), isSelected && /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        marginTop: 2
      },
      onClick: e => e.stopPropagation()
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 12,
        color: '#6b7a8d',
        fontWeight: 600
      }
    }, "Qt\xE9 :"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        border: '2px solid #0ea5e9',
        borderRadius: 8,
        overflow: 'hidden'
      }
    }, /*#__PURE__*/React.createElement("button", {
      onClick: e => {
        e.stopPropagation();
        setQty(uid, Math.max(1, Number(qtys[uid] || 1) - 1));
      },
      style: {
        background: '#f0f9ff',
        border: 'none',
        padding: '3px 9px',
        cursor: 'pointer',
        fontSize: 14,
        color: '#0ea5e9',
        fontWeight: 700
      }
    }, "\u2212"), /*#__PURE__*/React.createElement("input", {
      type: "number",
      min: "1",
      value: qtys[uid] || 1,
      onChange: e => setQty(uid, e.target.value),
      style: {
        width: 46,
        textAlign: 'center',
        border: 'none',
        padding: '3px 4px',
        fontSize: 13,
        fontFamily: 'inherit',
        fontWeight: 700,
        outline: 'none'
      }
    }), /*#__PURE__*/React.createElement("button", {
      onClick: e => {
        e.stopPropagation();
        setQty(uid, Number(qtys[uid] || 1) + 1);
      },
      style: {
        background: '#f0f9ff',
        border: 'none',
        padding: '3px 9px',
        cursor: 'pointer',
        fontSize: 14,
        color: '#0ea5e9',
        fontWeight: 700
      }
    }, "+")), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 12,
        color: '#6b7a8d'
      }
    }, p.unit || 'pièce(s)'))));
  };
  return /*#__PURE__*/React.createElement(React.Fragment, null, zoom && /*#__PURE__*/React.createElement(ImageZoom, {
    src: zoom.src,
    name: zoom.name,
    onClose: () => setZoom(null)
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(10,20,40,0.65)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#f0f4f8',
      borderRadius: 20,
      width: '100%',
      maxWidth: 920,
      maxHeight: '93vh',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 28px 90px rgba(0,0,0,.3)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '15px 20px',
      borderBottom: '1.5px solid #dde4ed',
      display: 'flex',
      gap: 12,
      alignItems: 'flex-start',
      background: '#fff'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      fontSize: 15
    }
  }, "\uD83D\uDED2 Lier des produits \xE0 ce point"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginTop: 3
    }
  }, itemText.slice(0, 90), itemText.length > 90 ? '…' : '')), /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      background: 'none',
      border: '1.5px solid #dde4ed',
      borderRadius: 8,
      padding: '5px 12px',
      cursor: 'pointer',
      fontSize: 14,
      color: '#6b7a8d'
    }
  }, "\u2715")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '10px 20px',
      borderBottom: '1px solid #dde4ed',
      display: 'flex',
      gap: 8,
      background: '#fff'
    }
  }, /*#__PURE__*/React.createElement("input", {
    value: q,
    onChange: e => setQ(e.target.value),
    onKeyDown: e => e.key === 'Enter' && search(q),
    placeholder: "Nom de produit, r\xE9f\xE9rence, marque\u2026",
    style: {
      flex: 1,
      border: '2px solid #dde4ed',
      borderRadius: 10,
      padding: '9px 13px',
      fontFamily: 'inherit',
      fontSize: 14,
      outline: 'none',
      background: '#f8fafc'
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: () => search(q),
    style: {
      background: '#0ea5e9',
      color: '#fff',
      border: 'none',
      borderRadius: 10,
      padding: '9px 20px',
      fontWeight: 700,
      cursor: 'pointer',
      fontSize: 14
    }
  }, loading ? '…' : 'Chercher')), allResults.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      background: '#fff',
      borderBottom: '1px solid #dde4ed',
      paddingLeft: 20,
      paddingRight: 20,
      overflowX: 'auto'
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: TAB_S(tab === 'all'),
    onClick: () => setTab('all')
  }, "Tous ", /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 5,
      background: tab === 'all' ? '#0ea5e9' : '#f0f4f8',
      color: tab === 'all' ? '#fff' : '#6b7a8d',
      borderRadius: 10,
      padding: '1px 7px',
      fontSize: 11,
      fontWeight: 700
    }
  }, counts.all)), counts.fluidra > 0 && /*#__PURE__*/React.createElement("button", {
    style: TAB_S(tab === 'fluidra', '#1d4ed8'),
    onClick: () => setTab('fluidra')
  }, "Fluidra / SIBO ", /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 5,
      background: tab === 'fluidra' ? '#1d4ed8' : '#f0f4f8',
      color: tab === 'fluidra' ? '#fff' : '#6b7a8d',
      borderRadius: 10,
      padding: '1px 7px',
      fontSize: 11,
      fontWeight: 700
    }
  }, counts.fluidra)), counts.scp > 0 && /*#__PURE__*/React.createElement("button", {
    style: TAB_S(tab === 'scp', '#166534'),
    onClick: () => setTab('scp')
  }, "SCP B\xE9n\xE9lux ", /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 5,
      background: tab === 'scp' ? '#166534' : '#f0f4f8',
      color: tab === 'scp' ? '#fff' : '#6b7a8d',
      borderRadius: 10,
      padding: '1px 7px',
      fontSize: 11,
      fontWeight: 700
    }
  }, counts.scp)), source && /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 'auto',
      fontSize: 11,
      fontWeight: 700,
      padding: '2px 9px',
      borderRadius: 20,
      background: source === 'odoo' ? '#dcfce7' : '#fef3c7',
      color: source === 'odoo' ? '#166534' : '#92400e'
    }
  }, source === 'odoo' ? '✅ Catalogue live' : '✨ Suggestions IA')), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: 'auto',
      padding: '12px 20px'
    }
  }, loading && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 50,
      textAlign: 'center',
      color: '#6b7a8d',
      fontSize: 32
    }
  }, "\uD83D\uDD04"), !loading && results.length === 0 && source && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 30,
      textAlign: 'center',
      color: '#6b7a8d',
      fontSize: 13
    }
  }, "Aucun r\xE9sultat. Modifiez la recherche."), grouped.map(([cat, {
    withSupplier,
    other
  }]) => {
    const isOpen = openCats[cat] !== false; // ouvert par défaut
    const total = withSupplier.length + other.length;
    const hasKnownSupplier = withSupplier.length > 0;
    return /*#__PURE__*/React.createElement("div", {
      key: cat,
      style: {
        marginBottom: 10
      }
    }, /*#__PURE__*/React.createElement("div", {
      onClick: () => toggleCat(cat),
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '9px 14px',
        borderRadius: 10,
        cursor: 'pointer',
        background: hasKnownSupplier ? 'linear-gradient(135deg,#eff6ff,#f0fdf4)' : '#f8fafc',
        border: `1.5px solid ${hasKnownSupplier ? '#bfdbfe' : '#e8edf3'}`,
        marginBottom: isOpen ? 6 : 0,
        transition: 'all .15s'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 16
      }
    }, isOpen ? '▼' : '▶'), /*#__PURE__*/React.createElement("span", {
      style: {
        fontWeight: 700,
        fontSize: 14,
        flex: 1,
        color: '#1a2332'
      }
    }, cat), withSupplier.length > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 5
      }
    }, withSupplier.some(p => (p.suppliers || []).some(s => s.type === 'fluidra')) && /*#__PURE__*/React.createElement("span", {
      style: {
        background: '#dbeafe',
        color: '#1d4ed8',
        borderRadius: 5,
        padding: '2px 7px',
        fontSize: 11,
        fontWeight: 700
      }
    }, "Fluidra"), withSupplier.some(p => (p.suppliers || []).some(s => s.type === 'scp')) && /*#__PURE__*/React.createElement("span", {
      style: {
        background: '#dcfce7',
        color: '#166534',
        borderRadius: 5,
        padding: '2px 7px',
        fontSize: 11,
        fontWeight: 700
      }
    }, "SCP")), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 12,
        color: '#6b7a8d',
        background: '#f0f4f8',
        padding: '2px 8px',
        borderRadius: 12,
        fontWeight: 600
      }
    }, total, " produit", total > 1 ? 's' : '')), isOpen && /*#__PURE__*/React.createElement("div", {
      style: {
        paddingLeft: 4
      }
    }, withSupplier.length > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        marginBottom: 4
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        color: '#6b7a8d',
        textTransform: 'uppercase',
        letterSpacing: '.5px',
        padding: '4px 0',
        marginBottom: 4,
        display: 'flex',
        alignItems: 'center',
        gap: 6
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: '#10b981',
        display: 'inline-block'
      }
    }), "Fournisseurs r\xE9f\xE9renc\xE9s"), withSupplier.map(p => /*#__PURE__*/React.createElement(ProductRow, {
      key: productUid(p),
      p: p,
      uid: productUid(p)
    }))), other.length > 0 && /*#__PURE__*/React.createElement("div", null, withSupplier.length > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        fontWeight: 700,
        color: '#9ca3af',
        textTransform: 'uppercase',
        letterSpacing: '.5px',
        padding: '4px 0',
        marginBottom: 4,
        display: 'flex',
        alignItems: 'center',
        gap: 6
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: '#d1d5db',
        display: 'inline-block'
      }
    }), "Autres produits"), other.map(p => /*#__PURE__*/React.createElement(ProductRow, {
      key: productUid(p),
      p: p,
      uid: productUid(p)
    })))));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '12px 20px',
      borderTop: '1.5px solid #dde4ed',
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      background: '#fff'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: '#6b7a8d',
      flex: 1
    }
  }, selCount, " produit(s) s\xE9lectionn\xE9(s)"), /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    style: {
      background: 'none',
      border: '1.5px solid #dde4ed',
      borderRadius: 9,
      padding: '8px 16px',
      cursor: 'pointer',
      fontFamily: 'inherit',
      fontSize: 13,
      fontWeight: 600
    }
  }, "Annuler"), /*#__PURE__*/React.createElement("button", {
    onClick: confirm,
    disabled: !selCount,
    style: {
      background: selCount ? '#0ea5e9' : '#d1d5db',
      color: '#fff',
      border: 'none',
      borderRadius: 9,
      padding: '8px 20px',
      fontWeight: 700,
      cursor: selCount ? 'pointer' : 'not-allowed',
      fontFamily: 'inherit',
      fontSize: 13
    }
  }, "\u2713 Ajouter \xE0 l'intervention")))));
}
function SectionBlock({
  sec,
  si,
  statuses,
  notes,
  toggle,
  setStatus,
  setNote,
  accent,
  linkedProducts,
  photos,
  onAddProducts,
  onRemoveProduct,
  onPhoto
}) {
  const [open, setOpen] = React.useState(true);
  const [productPanel, setProductPanel] = React.useState(null);
  const sChecked = sec.items.filter((_, i) => statuses[`${si}_${i}`] && statuses[`${si}_${i}`] !== 'pending').length;
  return /*#__PURE__*/React.createElement(React.Fragment, null, productPanel !== null && /*#__PURE__*/React.createElement(ProductPanel, {
    itemText: sec.items[productPanel],
    sectionLabel: sec.section,
    onAdd: prods => onAddProducts(si, productPanel, prods),
    onClose: () => setProductPanel(null)
  }), /*#__PURE__*/React.createElement("div", {
    className: "lpc-section"
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-sec-hdr",
    onClick: () => setOpen(o => !o)
  }, /*#__PURE__*/React.createElement("h3", null, sec.section), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "lpc-progress"
  }, sChecked, "/", sec.items.length), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: '#6b7a8d'
    }
  }, open ? '▲' : '▼'))), /*#__PURE__*/React.createElement("div", {
    className: `lpc-sec-body${open ? '' : ' collapsed'}`
  }, sec.items.map((item, idx) => {
    const k = `${si}_${idx}`;
    const status = statuses[k] || 'pending';
    const sc = STATUS_CONFIG[status];
    const prods = linkedProducts[k] || [];
    const photo = photos[k] || null;
    return /*#__PURE__*/React.createElement("div", {
      key: idx
    }, /*#__PURE__*/React.createElement("div", {
      className: `lpc-item${status !== 'pending' ? ' checked' : ''}`,
      style: {
        background: sc.bg || 'transparent',
        borderLeft: status !== 'pending' ? `3px solid ${sc.color}` : '3px solid transparent'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 2,
        flexShrink: 0
      },
      className: "no-print"
    }, Object.entries(STATUS_CONFIG).map(([s, c]) => /*#__PURE__*/React.createElement("button", {
      key: s,
      onClick: () => setStatus(si, idx, s),
      title: c.label,
      style: {
        background: status === s ? c.bg : 'transparent',
        border: `1.5px solid ${status === s ? c.color : '#e2e8f0'}`,
        borderRadius: 5,
        padding: '2px 5px',
        cursor: 'pointer',
        fontSize: 14,
        lineHeight: 1,
        transition: 'all .15s'
      }
    }, c.icon))), /*#__PURE__*/React.createElement("span", {
      className: "print-only",
      style: {
        fontSize: 13,
        flexShrink: 0
      }
    }, sc.icon), item.includes('______') ? /*#__PURE__*/React.createElement("span", {
      className: "lpc-item-text",
      style: {
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 4
      }
    }, item.split('______').map((part, pi, arr) => /*#__PURE__*/React.createElement(React.Fragment, {
      key: pi
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        opacity: status === 'ok' ? .5 : 1
      }
    }, part), pi < arr.length - 1 && /*#__PURE__*/React.createElement("input", {
      type: "text",
      placeholder: "\u2026",
      defaultValue: notes[k]?.split('||')[pi] || '',
      onChange: e => {
        const parts = (notes[k] || '').split('||');
        while (parts.length <= pi) parts.push('');
        parts[pi] = e.target.value;
        setNote(si, idx, parts.join('||'));
      },
      onClick: ev => ev.stopPropagation(),
      className: "no-print",
      style: {
        border: '1.5px solid #0ea5e9',
        borderRadius: 5,
        padding: '2px 6px',
        fontSize: 13,
        fontFamily: 'inherit',
        width: item.toLowerCase().includes('m)') ? '60px' : item.toLowerCase().includes('km') ? '50px' : item.toLowerCase().includes('kg') ? '55px' : item.toLowerCase().includes('kw') ? '55px' : '100px',
        background: '#f0f9ff',
        outline: 'none',
        color: '#0369a1',
        fontWeight: 600
      }
    })))) : /*#__PURE__*/React.createElement("span", {
      className: `lpc-item-text${status === 'ok' ? ' done' : ''}`
    }, item), /*#__PURE__*/React.createElement("div", {
      className: "no-print",
      style: {
        flexShrink: 0,
        display: 'flex',
        gap: 4,
        alignItems: 'center'
      }
    }, photo ? /*#__PURE__*/React.createElement("img", {
      src: photo,
      alt: "photo",
      onClick: () => window.open(photo),
      style: {
        width: 32,
        height: 32,
        objectFit: 'cover',
        borderRadius: 4,
        cursor: 'pointer',
        border: '1.5px solid #dde4ed'
      }
    }) : null, /*#__PURE__*/React.createElement("label", {
      title: "Prendre/choisir une photo",
      style: {
        cursor: 'pointer',
        fontSize: 16,
        opacity: .5
      },
      onMouseOver: e => e.currentTarget.style.opacity = 1,
      onMouseOut: e => e.currentTarget.style.opacity = .5
    }, "\uD83D\uDCF7", /*#__PURE__*/React.createElement("input", {
      type: "file",
      accept: "image/*",
      capture: "environment",
      style: {
        display: 'none'
      },
      onChange: e => {
        const f = e.target.files[0];
        if (!f) return;
        const r = new FileReader();
        r.onload = ev => onPhoto(si, idx, ev.target.result);
        r.readAsDataURL(f);
      }
    }))), /*#__PURE__*/React.createElement("button", {
      className: "lpc-add-btn no-print",
      title: "Lier des produits",
      onClick: () => setProductPanel(idx),
      style: {
        '--acc': accent
      }
    }, "\uD83D\uDED2", prods.length > 0 && /*#__PURE__*/React.createElement("span", {
      className: "lpc-badge"
    }, prods.length)), /*#__PURE__*/React.createElement("input", {
      className: "lpc-note no-print",
      placeholder: "Note\u2026",
      value: notes[k] || '',
      onChange: e => setNote(si, idx, e.target.value)
    })), prods.length > 0 && /*#__PURE__*/React.createElement("div", {
      className: "lpc-linked"
    }, prods.map((p, pi) => /*#__PURE__*/React.createElement("div", {
      key: pi,
      className: "lpc-chip"
    }, /*#__PURE__*/React.createElement("span", {
      className: "lpc-chip-qty"
    }, p.qty, "\xD7"), p.ref && /*#__PURE__*/React.createElement("span", {
      className: "lpc-chip-ref"
    }, "[", p.ref, "]"), /*#__PURE__*/React.createElement("span", {
      className: "lpc-chip-name"
    }, p.name), p.price > 0 && /*#__PURE__*/React.createElement("span", {
      className: "lpc-chip-price"
    }, (p.price * (p.qty || 1)).toFixed(2), " \u20AC"), /*#__PURE__*/React.createElement("button", {
      className: "lpc-chip-del no-print",
      onClick: () => onRemoveProduct(si, idx, pi)
    }, "\u2715")))), photo && /*#__PURE__*/React.createElement("div", {
      className: "print-only",
      style: {
        padding: '2px 20px 6px 44px'
      }
    }, /*#__PURE__*/React.createElement("img", {
      src: photo,
      style: {
        height: 60,
        objectFit: 'cover',
        borderRadius: 4
      }
    })));
  }))));
}

/* ════════════════════════════════════════════════════════
   Application principale
   ════════════════════════════════════════════════════════ */
function PoolChecklist() {
  const [step, setStep] = React.useState(0);
  const [intervention, setInt] = React.useState(null);
  const [plan, setPlan] = React.useState(null);
  const [client, setClient] = React.useState({
    prenom: '',
    nom: '',
    tel: '',
    societe: '',
    tva: '',
    tvaStatus: null,
    tvaLoading: false,
    rue: '',
    cp: '',
    ville: '',
    pays: 'Belgique',
    date: new Date().toISOString().slice(0, 10),
    technicien: cfg.userName || '',
    ref: '',
    type: 'particulier',
    partner_id: null
  });
  const [statuses, setStatuses] = React.useState({});
  const [notes, setNotes] = React.useState({});
  const [linkedProducts, setLinked] = React.useState({});
  const [photos, setPhotos] = React.useState({});
  const [sigTech, setSigTech] = React.useState(null);
  const [sigClient, setSigClient] = React.useState(null);
  const [reportId, setReportId] = React.useState(null);
  const [saveStatus, setSaveStatus] = React.useState(null); // null|'saving'|'saved'|'error'
  const [showHistory, setShowHistory] = React.useState(false);
  const [quoteResult, setQuoteResult] = React.useState(null);
  const [showQuoteModal, setShowQuoteModal] = React.useState(false);
  const [generalNotes, setGeneralNotes] = React.useState('');
  const intData = INTERVENTIONS.find(i => i.id === intervention);
  const sections = intervention ? CHECKLISTS[intervention] : [];
  const accent = intData?.color || '#0ea5e9';
  const totalItems = sections.reduce((a, s) => a + s.items.length, 0);
  const okCount = Object.values(statuses).filter(s => s === 'ok').length;
  const warnCount = Object.values(statuses).filter(s => s === 'warn').length;
  const actionCount = Object.values(statuses).filter(s => s === 'action').length;
  const doneCount = okCount + warnCount + actionCount;
  const allProds = Object.entries(linkedProducts).filter(([, a]) => a.length > 0).flatMap(([k, a]) => a.map(p => ({
    ...p,
    _k: k
  })));
  const totalEst = allProds.reduce((a, p) => a + (p.price || 0) * (p.qty || 1), 0);
  const setStatus = (si, idx, s) => {
    const k = `${si}_${idx}`;
    setStatuses(p => ({
      ...p,
      [k]: s
    }));
  };
  const setNote = (si, idx, v) => {
    const k = `${si}_${idx}`;
    setNotes(p => ({
      ...p,
      [k]: v
    }));
  };
  const addProds = (si, idx, prods) => {
    const k = `${si}_${idx}`;
    setLinked(p => ({
      ...p,
      [k]: [...(p[k] || []), ...prods]
    }));
  };
  const remProd = (si, idx, pi) => {
    const k = `${si}_${idx}`;
    setLinked(p => ({
      ...p,
      [k]: (p[k] || []).filter((_, i) => i !== pi)
    }));
  };
  const setPhoto = (si, idx, data) => {
    const k = `${si}_${idx}`;
    setPhotos(p => ({
      ...p,
      [k]: data
    }));
  };

  /* Auto-save localStorage toutes les 15s */
  React.useEffect(() => {
    if (step < 3) return;
    const id = setInterval(() => {
      lsSave({
        step,
        intervention,
        plan,
        client,
        statuses,
        notes,
        linkedProducts,
        generalNotes,
        reportId
      });
    }, 15000);
    return () => clearInterval(id);
  }, [step, intervention, plan, client, statuses, notes, linkedProducts, generalNotes, reportId]);

  /* Restaurer brouillon au démarrage */
  React.useEffect(() => {
    const draft = lsLoad();
    if (draft && draft._ts && Date.now() - draft._ts < 48 * 3600 * 1000) {
      if (window.confirm('Un brouillon de fiche a été trouvé. Voulez-vous le restaurer ?')) {
        if (draft.step) setStep(draft.step);
        if (draft.intervention) setInt(draft.intervention);
        if (draft.plan) setPlan(draft.plan);
        if (draft.client) setClient(draft.client);
        if (draft.statuses) setStatuses(draft.statuses);
        if (draft.notes) setNotes(draft.notes);
        if (draft.linkedProducts) setLinked(draft.linkedProducts);
        if (draft.generalNotes) setGeneralNotes(draft.generalNotes);
        if (draft.reportId) setReportId(draft.reportId);
      }
    }
  }, []);

  /* Sauvegarder sur Odoo */
  const saveToOdoo = async () => {
    if (!cfg.isLoggedIn) {
      alert('Veuillez vous connecter pour sauvegarder.');
      return;
    }
    setSaveStatus('saving');
    try {
      const r = await apiPost(cfg.saveEndpoint || '/pool-checklist/save', {
        report_id: reportId,
        nom: [client.prenom, client.nom].filter(Boolean).join(' '),
        societe: client.societe || '',
        tva: client.tva || '',
        type_client: client.type || 'particulier',
        adresse: [client.rue, client.cp, client.ville, client.pays].filter(Boolean).join(', '),
        tel: client.tel,
        date: client.date,
        ref: client.ref,
        technicien: client.technicien,
        partner_id: client.partner_id,
        intervention,
        plan,
        checklist: statuses,
        products: allProds,
        notes: generalNotes,
        signature_technicien: sigTech,
        signature_client: sigClient
      });
      if (r?.success) {
        setReportId(r.report_id);
        setSaveStatus('saved');
        lsClear();
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch (e) {
      setSaveStatus('error');
    }
  };

  /* Charger une fiche depuis l'historique */
  const loadReport = async id => {
    const r = await apiPost(`${cfg.loadEndpoint || '/pool-checklist/load'}/${id}`, {});
    if (r?.success) {
      const d = r.data;
      setInt(d.intervention);
      setPlan(d.plan || null);
      setClient({
        nom: d.nom || '',
        adresse: d.adresse || '',
        tel: d.tel || '',
        date: d.date || '',
        ref: d.ref || '',
        technicien: d.technicien || '',
        partner_id: d.partner_id || null
      });
      setStatuses(d.checklist || {});
      setLinked(d.products ? Object.fromEntries(d.products.map((p, i) => [p._k || `_${i}`, [p]])) : {});
      setReportId(d.report_id);
      setGeneralNotes(d.notes || '');
      setStep(3);
      setShowHistory(false);
    }
  };

  /* Créer un devis */
  const createQuote = async () => {
    if (!allProds.length) {
      alert('Aucun produit lié à cette fiche.');
      return;
    }
    setSaveStatus('saving');
    const r = await apiPost(cfg.quoteEndpoint || '/pool-checklist/create-quote', {
      report_id: reportId,
      products: allProds,
      client: {
        ...client,
        nom: [client.prenom, client.nom].filter(Boolean).join(' '),
        adresse: [client.rue, client.cp, client.ville, client.pays].filter(Boolean).join(', ')
      }
    });
    setSaveStatus(null);
    if (r?.success) {
      setQuoteResult(r);
    } else {
      alert('Erreur lors de la création du devis : ' + (r?.error || 'inconnue'));
    }
  };

  /* Ouvrir la modale de création de devis */
  const openQuoteModal = () => {
    if (!allProds.length) {
      alert('Aucun produit lié à cette fiche.');
      return;
    }
    setShowQuoteModal(true);
  };

  /* Réinitialiser */
  const reset = () => {
    if (!window.confirm('Réinitialiser la fiche ? Toutes les données non sauvegardées seront perdues.')) return;
    setStatuses({});
    setNotes({});
    setLinked({});
    setPhotos({});
    setSigTech(null);
    setSigClient(null);
    setReportId(null);
    setGeneralNotes('');
    lsClear();
  };
  const STEPS = ["Type d'intervention", "Infos client", "Plan de bassin", "Check-list & produits"];
  const inputStyle = {
    border: '2px solid #dde4ed',
    borderRadius: 10,
    padding: '11px 14px',
    fontFamily: 'inherit',
    fontSize: 15,
    background: '#eef2f7',
    color: '#1a2332',
    transition: 'border .2s',
    width: '100%',
    outline: 'none'
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "lpc-app"
  }, showHistory && /*#__PURE__*/React.createElement(HistoryModal, {
    onLoad: loadReport,
    onClose: () => setShowHistory(false)
  }), showQuoteModal && /*#__PURE__*/React.createElement(QuoteModal, {
    client: client,
    allProds: allProds,
    reportId: reportId,
    onClose: () => setShowQuoteModal(false),
    onSuccess: r => {
      setQuoteResult(r);
      setShowQuoteModal(false);
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "lpc-hdr no-print"
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-logo",
    style: {
      background: accent
    }
  }, "\uD83C\uDFCA"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", null, "Lolirine Pool Store \u2014 Fiche de visite chantier"), /*#__PURE__*/React.createElement("p", null, "Diagnostic \xB7 intervention \xB7 produits li\xE9s \xB7 devis estimatif")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginLeft: 'auto',
      display: 'flex',
      gap: 8,
      flexShrink: 0
    }
  }, cfg.isLoggedIn && /*#__PURE__*/React.createElement("button", {
    onClick: () => setShowHistory(true),
    style: {
      background: 'none',
      border: '1.5px solid #dde4ed',
      borderRadius: 8,
      padding: '6px 13px',
      fontSize: 13,
      color: '#6b7a8d',
      cursor: 'pointer'
    }
  }, "\uD83D\uDCCB Historique"), saveStatus === 'saving' && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: '#6b7a8d',
      padding: '6px 0'
    }
  }, "\uD83D\uDCBE Sauvegarde\u2026"), saveStatus === 'saved' && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: '#059669',
      padding: '6px 0'
    }
  }, "\u2705 Sauvegard\xE9"), saveStatus === 'error' && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: '#ef4444',
      padding: '6px 0'
    }
  }, "\u274C Erreur"), reportId && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      padding: '6px 0',
      border: '1px solid #dde4ed',
      borderRadius: 6,
      paddingLeft: 8,
      paddingRight: 8
    }
  }, "\uD83D\uDCC4 ", reportId))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-stepper no-print"
  }, STEPS.map((lbl, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: `lpc-step${step === i ? ' active' : step > i ? ' done' : ''}`,
    style: {
      '--acc': accent
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-step-num"
  }, step > i ? '✓' : i + 1), /*#__PURE__*/React.createElement("div", {
    className: "lpc-step-lbl"
  }, lbl)))), step === 0 && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    className: "lpc-title"
  }, "S\xE9lectionner le type d'intervention"), /*#__PURE__*/React.createElement("div", {
    className: "lpc-grid"
  }, INTERVENTIONS.map(iv => /*#__PURE__*/React.createElement("div", {
    key: iv.id,
    className: `lpc-card${intervention === iv.id ? ' sel' : ''}`,
    style: {
      '--acc': iv.color
    },
    onClick: () => setInt(iv.id)
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-card-title"
  }, iv.label), /*#__PURE__*/React.createElement("div", {
    className: "lpc-card-sub"
  }, CHECKLISTS[iv.id].reduce((a, s) => a + s.items.length, 0), " points \xB7 ", CHECKLISTS[iv.id].length, " sections")))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-acts no-print"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-p",
    disabled: !intervention,
    style: {
      '--acc': accent
    },
    onClick: () => setStep(1)
  }, "Suivant \u2192"))), step === 1 && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    className: "lpc-title"
  }, "Informations client & chantier"), /*#__PURE__*/React.createElement("div", {
    className: "lpc-contact-section"
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-contact-header"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lpc-contact-header-icon"
  }, "\uD83D\uDC64"), /*#__PURE__*/React.createElement("span", null, "Vous \xEAtes")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-contact-body"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      marginBottom: 20
    }
  }, [['particulier', '👤 Particulier'], ['professionnel', '🏢 Professionnel']].map(([val, lbl]) => /*#__PURE__*/React.createElement("button", {
    key: val,
    onClick: () => setClient(p => ({
      ...p,
      type: val
    })),
    className: `lpc-toggle-btn${(client.type || 'particulier') === val ? ' active' : ''}`
  }, lbl))), (client.type || 'particulier') === 'professionnel' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "lpc-sub-header"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lpc-sub-icon"
  }, "\uD83C\uDFE2"), /*#__PURE__*/React.createElement("span", null, "Informations entreprise")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-form-grid",
    style: {
      marginTop: 12,
      marginBottom: 20
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg full"
  }, /*#__PURE__*/React.createElement("label", null, "D\xE9nomination sociale ", /*#__PURE__*/React.createElement("span", {
    className: "lpc-required"
  }, "*")), /*#__PURE__*/React.createElement("input", {
    value: client.societe,
    onChange: e => setClient(p => ({
      ...p,
      societe: e.target.value
    })),
    placeholder: "ACME SRL, Dupont & Associ\xE9s SA\u2026",
    style: {
      border: '1.5px solid #e5e7eb',
      borderRadius: 8,
      padding: '12px 16px',
      fontFamily: 'inherit',
      fontSize: 14,
      background: '#f9fafb',
      color: '#1a2332',
      width: '100%',
      outline: 'none'
    }
  })), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg full"
  }, /*#__PURE__*/React.createElement("label", null, "Num\xE9ro de TVA"), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      display: 'flex',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("input", {
    value: client.tva,
    onChange: e => {
      const v = e.target.value;
      setClient(p => ({
        ...p,
        tva: v,
        tvaStatus: null
      }));
    },
    onBlur: async e => {
      const v = e.target.value.trim();
      if (!v || v.length < 8) return;
      setClient(p => ({
        ...p,
        tvaLoading: true,
        tvaStatus: null
      }));
      const result = await checkVatOdoo(v);
      if (result?.valid && result?.name) {
        setClient(p => ({
          ...p,
          tvaLoading: false,
          tvaStatus: 'valid',
          societe: p.societe || result.name
        }));
      } else if (result !== null) {
        setClient(p => ({
          ...p,
          tvaLoading: false,
          tvaStatus: 'invalid'
        }));
      } else {
        setClient(p => ({
          ...p,
          tvaLoading: false,
          tvaStatus: null
        }));
      }
    },
    placeholder: "BE0650.891.279",
    style: {
      flex: 1,
      border: `1.5px solid ${client.tvaStatus === 'valid' ? '#10b981' : client.tvaStatus === 'invalid' ? '#ef4444' : '#e5e7eb'}`,
      borderRadius: 8,
      padding: '12px 16px',
      fontFamily: 'inherit',
      fontSize: 14,
      background: '#f9fafb',
      color: '#1a2332',
      outline: 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      right: 12,
      top: '50%',
      transform: 'translateY(-50%)',
      fontSize: 16
    }
  }, client.tvaLoading && /*#__PURE__*/React.createElement("span", {
    style: {
      animation: 'spin 1s linear infinite',
      display: 'inline-block'
    }
  }, "\u27F3"), !client.tvaLoading && client.tvaStatus === 'valid' && /*#__PURE__*/React.createElement("span", {
    title: "TVA valide"
  }, "\u2705"), !client.tvaLoading && client.tvaStatus === 'invalid' && /*#__PURE__*/React.createElement("span", {
    title: "TVA invalide"
  }, "\u274C"))), client.tvaStatus === 'valid' && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#059669',
      marginTop: 4,
      display: 'flex',
      gap: 4,
      alignItems: 'center'
    }
  }, "\u2705 Num\xE9ro de TVA v\xE9rifi\xE9 via VIES Odoo", client.societe && /*#__PURE__*/React.createElement("span", null, "\u2014 ", /*#__PURE__*/React.createElement("strong", null, client.societe))), client.tvaStatus === 'invalid' && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#ef4444',
      marginTop: 4
    }
  }, "\u274C Num\xE9ro de TVA invalide ou non trouv\xE9"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#9ca3af',
      marginTop: 3
    }
  }, "Format : BE0000.000.000 \u2014 La v\xE9rification se fait \xE0 la perte du focus")))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-sub-header"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lpc-sub-icon"
  }, "\uD83D\uDCCB"), /*#__PURE__*/React.createElement("span", null, "Informations de contact")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-form-grid",
    style: {
      marginTop: 16
    }
  }, /*#__PURE__*/React.createElement(ClientAutocomplete, {
    valuePrenom: client.prenom,
    valueNom: client.nom,
    onChangePrenom: v => setClient(p => ({
      ...p,
      prenom: v
    })),
    onChangeNom: v => setClient(p => ({
      ...p,
      nom: v
    })),
    onSelectPartner: partner => {
      const parts = (partner.name || '').trim().split(' ');
      const isCompany = partner.company_name || partner.is_company;
      setClient(p => ({
        ...p,
        prenom: isCompany ? p.prenom : parts.length > 1 ? parts[0] : '',
        nom: isCompany ? p.nom : parts.length > 1 ? parts.slice(1).join(' ') : parts[0],
        societe: partner.company_name || partner.name || p.societe,
        tva: partner.vat || p.tva,
        type: isCompany ? 'professionnel' : p.type,
        tel: partner.phone || partner.mobile || p.tel,
        rue: partner.street || p.rue,
        cp: partner.zip || p.cp,
        ville: partner.city || p.ville,
        partner_id: partner.id
      }));
    }
  }), client.partner_id && /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg full"
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-linked-badge"
  }, "\u2705 Contact Odoo #", client.partner_id, " li\xE9 \u2014 champs pr\xE9-remplis")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg"
  }, /*#__PURE__*/React.createElement("label", null, "T\xE9l\xE9phone ", /*#__PURE__*/React.createElement("span", {
    className: "lpc-required"
  }, "*")), /*#__PURE__*/React.createElement("input", {
    value: client.tel,
    onChange: e => setClient(p => ({
      ...p,
      tel: e.target.value
    })),
    placeholder: "0475/12 34 56",
    style: inputStyle
  })), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg"
  }, /*#__PURE__*/React.createElement("label", null, "Date de visite"), /*#__PURE__*/React.createElement("input", {
    type: "date",
    value: client.date,
    onChange: e => setClient(p => ({
      ...p,
      date: e.target.value
    })),
    style: inputStyle
  }))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-sub-header",
    style: {
      marginTop: 24
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "lpc-sub-icon"
  }, "\uD83D\uDCCD"), /*#__PURE__*/React.createElement("span", null, "Adresse du chantier")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-form-grid",
    style: {
      marginTop: 16
    }
  }, /*#__PURE__*/React.createElement(AddressAutocomplete, {
    valueRue: client.rue,
    valueCp: client.cp,
    valueVille: client.ville,
    valuePays: client.pays,
    onChangeFull: ({
      rue,
      cp,
      ville,
      pays
    }) => setClient(p => ({
      ...p,
      rue: rue !== undefined ? rue : p.rue,
      cp: cp !== undefined ? cp : p.cp,
      ville: ville !== undefined ? ville : p.ville,
      pays: pays !== undefined ? pays : p.pays
    })),
    inputStyle: inputStyle
  })), /*#__PURE__*/React.createElement("div", {
    className: "lpc-sub-header",
    style: {
      marginTop: 24
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "lpc-sub-icon"
  }, "\uD83D\uDD27"), /*#__PURE__*/React.createElement("span", null, "Informations de l'intervention")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-form-grid",
    style: {
      marginTop: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg"
  }, /*#__PURE__*/React.createElement("label", null, "Technicien / Commercial"), /*#__PURE__*/React.createElement("input", {
    value: client.technicien,
    onChange: e => setClient(p => ({
      ...p,
      technicien: e.target.value
    })),
    placeholder: "Pr\xE9nom NOM",
    style: inputStyle
  })), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg"
  }, /*#__PURE__*/React.createElement("label", null, "R\xE9f\xE9rence dossier"), /*#__PURE__*/React.createElement("input", {
    value: client.ref,
    onChange: e => setClient(p => ({
      ...p,
      ref: e.target.value
    })),
    placeholder: "LPS-2025-001",
    style: inputStyle
  }))))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-acts no-print"
  }, /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-s",
    onClick: () => setStep(0)
  }, "\u2190 Retour"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-p",
    style: {
      '--acc': accent
    },
    onClick: () => setStep(2)
  }, "Suivant \u2192"))), step === 2 && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    className: "lpc-title"
  }, "Plan de bassin"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 13,
      color: '#6b7a8d',
      marginBottom: 18
    }
  }, "S\xE9lectionner la forme correspondante"), /*#__PURE__*/React.createElement("div", {
    className: "lpc-grid"
  }, POOL_PLANS.map(p => /*#__PURE__*/React.createElement("div", {
    key: p.id,
    className: `lpc-plan-card${plan === p.id ? ' sel' : ''}`,
    style: {
      '--acc': accent
    },
    onClick: () => setPlan(p.id)
  }, /*#__PURE__*/React.createElement(PoolSvg, {
    plan: p,
    size: 140
  }), /*#__PURE__*/React.createElement("div", {
    className: "lpc-plan-lbl"
  }, p.label)))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-acts no-print"
  }, /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-s",
    onClick: () => setStep(1)
  }, "\u2190 Retour"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-g",
    onClick: () => {
      setPlan(null);
      setStep(3);
    }
  }, "Passer"), /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-p",
    disabled: !plan,
    style: {
      '--acc': accent
    },
    onClick: () => setStep(3)
  }, "Suivant \u2192"))), step === 3 && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "lpc-print-hdr"
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-sumbox",
    style: {
      display: 'flex'
    }
  }, [["Client", [client.prenom, client.nom].filter(Boolean).join(' ')], client.societe && ["Société", client.societe], client.tva && ["TVA", client.tva], ["Adresse", [client.rue, client.cp, client.ville, client.pays].filter(Boolean).join(', ')], ["Tél", client.tel], ["Date", client.date], ["Technicien", client.technicien], ["Réf.", client.ref], ["Intervention", intData?.label]].filter(Boolean).filter(([, v]) => v).map(([l, v]) => /*#__PURE__*/React.createElement("div", {
    key: l,
    className: "lpc-si2"
  }, /*#__PURE__*/React.createElement("span", null, l), /*#__PURE__*/React.createElement("strong", null, v))))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-sumbox no-print"
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2"
  }, /*#__PURE__*/React.createElement("span", null, "Client"), /*#__PURE__*/React.createElement("strong", null, [client.prenom, client.nom].filter(Boolean).join(' ') || '—')), /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2"
  }, /*#__PURE__*/React.createElement("span", null, "Date"), /*#__PURE__*/React.createElement("strong", null, client.date)), /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2"
  }, /*#__PURE__*/React.createElement("span", null, "Intervention"), /*#__PURE__*/React.createElement("strong", {
    style: {
      color: accent
    }
  }, intData?.label)), plan && /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2"
  }, /*#__PURE__*/React.createElement("span", null, "Plan"), /*#__PURE__*/React.createElement("strong", null, POOL_PLANS.find(p => p.id === plan)?.label)), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2",
    style: {
      alignItems: 'flex-end'
    }
  }, /*#__PURE__*/React.createElement("span", null, "\u2705 OK"), /*#__PURE__*/React.createElement("strong", {
    style: {
      color: '#059669'
    }
  }, okCount)), warnCount > 0 && /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2",
    style: {
      alignItems: 'flex-end'
    }
  }, /*#__PURE__*/React.createElement("span", null, "\u26A0\uFE0F Surveiller"), /*#__PURE__*/React.createElement("strong", {
    style: {
      color: '#d97706'
    }
  }, warnCount)), actionCount > 0 && /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2",
    style: {
      alignItems: 'flex-end'
    }
  }, /*#__PURE__*/React.createElement("span", null, "\u274C Actions"), /*#__PURE__*/React.createElement("strong", {
    style: {
      color: '#dc2626'
    }
  }, actionCount)), /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2",
    style: {
      alignItems: 'flex-end'
    }
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDED2 Produits"), /*#__PURE__*/React.createElement("strong", {
    style: {
      color: '#0ea5e9'
    }
  }, allProds.length)), totalEst > 0 && /*#__PURE__*/React.createElement("div", {
    className: "lpc-si2",
    style: {
      alignItems: 'flex-end'
    }
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCB0 Estimation"), /*#__PURE__*/React.createElement("strong", {
    style: {
      color: '#059669'
    }
  }, totalEst.toFixed(2), " \u20AC"))), /*#__PURE__*/React.createElement("div", {
    className: "no-print",
    style: {
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 4,
      height: 10,
      borderRadius: 20,
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${totalItems ? okCount / totalItems * 100 : 0}%`,
      background: '#10b981',
      transition: 'width .4s'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${totalItems ? warnCount / totalItems * 100 : 0}%`,
      background: '#f59e0b',
      transition: 'width .4s'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${totalItems ? actionCount / totalItems * 100 : 0}%`,
      background: '#ef4444',
      transition: 'width .4s'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      background: '#dde4ed'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#6b7a8d',
      marginTop: 5,
      display: 'flex',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("span", null, "\u2705 ", okCount, " conformes"), warnCount > 0 && /*#__PURE__*/React.createElement("span", null, "\u26A0\uFE0F ", warnCount, " \xE0 surveiller"), actionCount > 0 && /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#dc2626',
      fontWeight: 600
    }
  }, "\u274C ", actionCount, " actions requises"), /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 'auto'
    }
  }, totalItems ? Math.round(doneCount / totalItems * 100) : 0, "% compl\xE9t\xE9"))), /*#__PURE__*/React.createElement("div", {
    className: "no-print",
    style: {
      display: 'flex',
      gap: 8,
      flexWrap: 'wrap',
      marginBottom: 14,
      padding: '10px 14px',
      background: '#fff',
      borderRadius: 10,
      border: '1px solid #dde4ed',
      fontSize: 12
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 700,
      color: '#6b7a8d',
      marginRight: 4
    }
  }, "Statuts :"), Object.entries(STATUS_CONFIG).map(([s, c]) => /*#__PURE__*/React.createElement("span", {
    key: s,
    style: {
      display: 'inline-flex',
      gap: 4,
      alignItems: 'center',
      background: c.bg || '#f0f4f8',
      padding: '3px 9px',
      borderRadius: 20,
      color: c.color || '#6b7a8d',
      fontWeight: 600
    }
  }, c.icon, " ", c.label)), /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 'auto',
      color: '#6b7a8d'
    }
  }, "\uD83D\uDCF7 = photo \xB7 \uD83D\uDED2 = produits")), plan && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'center',
      marginBottom: 14
    },
    className: "no-print"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#fff',
      border: '1.5px solid #dde4ed',
      borderRadius: 12,
      padding: 14,
      display: 'inline-flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 7
    }
  }, /*#__PURE__*/React.createElement(PoolSvg, {
    plan: POOL_PLANS.find(p => p.id === plan),
    size: 160
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 600,
      color: accent
    }
  }, POOL_PLANS.find(p => p.id === plan)?.label))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-print-plan"
  }, /*#__PURE__*/React.createElement(PoolSvg, {
    plan: POOL_PLANS.find(p => p.id === plan),
    size: 100
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 9
    }
  }, POOL_PLANS.find(p => p.id === plan)?.label))), sections.map((sec, si) => /*#__PURE__*/React.createElement(SectionBlock, {
    key: si,
    sec: sec,
    si: si,
    statuses: statuses,
    notes: notes,
    photos: photos,
    setStatus: setStatus,
    setNote: setNote,
    accent: accent,
    linkedProducts: linkedProducts,
    onAddProducts: addProds,
    onRemoveProduct: remProd,
    onPhoto: setPhoto
  })), allProds.length > 0 && /*#__PURE__*/React.createElement("div", {
    className: "lpc-section",
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-sec-hdr"
  }, /*#__PURE__*/React.createElement("h3", null, "\uD83D\uDED2 R\xE9capitulatif mat\xE9riaux & produits li\xE9s"), /*#__PURE__*/React.createElement("span", {
    className: "lpc-progress"
  }, allProds.length, " article(s)", totalEst > 0 ? ` · ${totalEst.toFixed(2)} €` : '')), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '6px 0'
    }
  }, /*#__PURE__*/React.createElement("table", {
    className: "lpc-mat-tbl"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", null, "R\xE9f."), /*#__PURE__*/React.createElement("th", null, "D\xE9signation"), /*#__PURE__*/React.createElement("th", null, "Fournisseur"), /*#__PURE__*/React.createElement("th", null, "Qt\xE9"), /*#__PURE__*/React.createElement("th", null, "Unit\xE9"), totalEst > 0 && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("th", null, "P.U."), /*#__PURE__*/React.createElement("th", null, "Total HT")), /*#__PURE__*/React.createElement("th", null, "Point de contr\xF4le"))), /*#__PURE__*/React.createElement("tbody", null, allProds.map((p, i) => {
    const mainS = (p.suppliers || []).find(s => s.type !== 'other') || (p.suppliers || [])[0];
    return /*#__PURE__*/React.createElement("tr", {
      key: i
    }, /*#__PURE__*/React.createElement("td", {
      style: {
        fontSize: 11,
        fontFamily: 'monospace',
        color: '#6b7a8d'
      }
    }, p.ref || '—'), /*#__PURE__*/React.createElement("td", {
      style: {
        fontWeight: 500
      }
    }, p.name), /*#__PURE__*/React.createElement("td", null, mainS ? /*#__PURE__*/React.createElement(SupplierBadge, {
      type: mainS.type,
      name: mainS.name
    }) : '—'), /*#__PURE__*/React.createElement("td", {
      style: {
        textAlign: 'center'
      }
    }, p.qty), /*#__PURE__*/React.createElement("td", null, p.unit || 'pc'), totalEst > 0 && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("td", {
      style: {
        textAlign: 'right'
      }
    }, p.price > 0 ? `${p.price.toFixed(2)} €` : '—'), /*#__PURE__*/React.createElement("td", {
      style: {
        textAlign: 'right',
        fontWeight: 600
      }
    }, p.price > 0 ? `${(p.price * (p.qty || 1)).toFixed(2)} €` : '—')), /*#__PURE__*/React.createElement("td", {
      style: {
        fontSize: 11,
        color: '#6b7a8d',
        maxWidth: 130,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, p.itemText?.slice(0, 45) || ''));
  }), totalEst > 0 && /*#__PURE__*/React.createElement("tr", {
    className: "lpc-mat-tot"
  }, /*#__PURE__*/React.createElement("td", {
    colSpan: totalEst > 0 ? 6 : 4,
    style: {
      textAlign: 'right',
      fontWeight: 700
    }
  }, "Total estimatif HT"), /*#__PURE__*/React.createElement("td", {
    style: {
      textAlign: 'right',
      fontWeight: 700,
      color: '#059669'
    }
  }, totalEst.toFixed(2), " \u20AC"), /*#__PURE__*/React.createElement("td", null)))))), quoteResult && /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#f0fdf4',
      border: '2px solid #10b981',
      borderRadius: 12,
      padding: '14px 18px',
      marginTop: 10,
      display: 'flex',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 24
    }
  }, "\u2705"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      color: '#059669'
    }
  }, "Devis Pool Store ", quoteResult.quote_name || quoteResult.order_name, " cr\xE9\xE9 !"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: '#047857',
      marginTop: 2
    }
  }, "Num\xE9rotation s\xE9par\xE9e \u2014 visible dans Fiche chantier \u2192 Devis Pool Store")), /*#__PURE__*/React.createElement("a", {
    href: `/pool-checklist/open-quote/${quoteResult.quote_id}`,
    target: "_blank",
    style: {
      background: '#059669',
      color: '#fff',
      padding: '8px 16px',
      borderRadius: 8,
      textDecoration: 'none',
      fontWeight: 700,
      fontSize: 13
    }
  }, "Ouvrir le devis \u2192"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setQuoteResult(null),
    style: {
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      color: '#6b7a8d',
      fontSize: 16
    }
  }, "\u2715")), /*#__PURE__*/React.createElement("div", {
    className: "lpc-section",
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-sec-hdr"
  }, /*#__PURE__*/React.createElement("h3", null, "\uD83D\uDCDD Remarques g\xE9n\xE9rales")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("textarea", {
    value: generalNotes,
    onChange: e => setGeneralNotes(e.target.value),
    placeholder: "Observations g\xE9n\xE9rales, conditions d'acc\xE8s, points particuliers \xE0 noter\u2026",
    style: {
      width: '100%',
      minHeight: 80,
      border: '1.5px solid #dde4ed',
      borderRadius: 8,
      padding: '10px 12px',
      fontFamily: 'inherit',
      fontSize: 14,
      resize: 'vertical',
      background: '#f8fafc'
    }
  }))), /*#__PURE__*/React.createElement("div", {
    className: "lpc-section",
    style: {
      marginTop: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "lpc-sec-hdr"
  }, /*#__PURE__*/React.createElement("h3", null, "\u270D\uFE0F Signatures")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 24,
      padding: 20
    }
  }, /*#__PURE__*/React.createElement(SignatureCanvas, {
    label: "Signature du technicien",
    onSave: setSigTech
  }), /*#__PURE__*/React.createElement(SignatureCanvas, {
    label: "Signature du client (bon pour accord)",
    onSave: setSigClient
  })), (sigTech || sigClient) && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '0 20px 16px',
      display: 'flex',
      gap: 12
    }
  }, sigTech && /*#__PURE__*/React.createElement("img", {
    src: sigTech,
    alt: "Sig tech",
    style: {
      height: 50,
      border: '1px solid #dde4ed',
      borderRadius: 6
    }
  }), sigClient && /*#__PURE__*/React.createElement("img", {
    src: sigClient,
    alt: "Sig client",
    style: {
      height: 50,
      border: '1px solid #dde4ed',
      borderRadius: 6
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: '#6b7a8d',
      textAlign: 'center',
      marginTop: 14
    }
  }, "Lolirine Pool Store \xB7 lolirinepoolstore.be \xB7 BCE 0650.891.279"), /*#__PURE__*/React.createElement("div", {
    className: "lpc-acts no-print",
    style: {
      marginTop: 20,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-s",
    onClick: () => setStep(2)
  }, "\u2190 Retour"), /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-s",
    onClick: reset
  }, "\uD83D\uDD04 R\xE9initialiser"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), allProds.length > 0 && /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-p",
    style: {
      '--acc': '#10b981',
      background: '#10b981'
    },
    onClick: openQuoteModal
  }, "\uD83D\uDCCB Cr\xE9er un devis Odoo"), cfg.isLoggedIn && /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-p",
    style: {
      '--acc': '#6366f1',
      background: '#6366f1'
    },
    onClick: saveToOdoo
  }, "\uD83D\uDCBE Sauvegarder"), /*#__PURE__*/React.createElement("button", {
    className: "lpc-btn-pr",
    onClick: () => window.print()
  }, "\uD83D\uDDA8\uFE0F Imprimer / PDF"))));
}

/* ── Client Autocomplete — prénom + nom séparés ── */
function ClientAutocomplete({
  valuePrenom,
  valueNom,
  onChangePrenom,
  onChangeNom,
  onSelectPartner
}) {
  const [suggestions, setSugg] = React.useState([]);
  const [open, setOpen] = React.useState(false);
  const [activeField, setActiveField] = React.useState(null);
  const fieldStyle = {
    border: '1.5px solid #e5e7eb',
    borderRadius: 8,
    padding: '12px 16px',
    fontFamily: 'inherit',
    fontSize: 14,
    background: '#f9fafb',
    color: '#1a2332',
    width: '100%',
    transition: 'all .2s',
    outline: 'none'
  };
  const search = async (v, field) => {
    setActiveField(field);
    if (v.length >= 2) {
      const partners = await searchPartners(v);
      setSugg(partners);
      setOpen(partners.length > 0);
    } else {
      setSugg([]);
      setOpen(false);
    }
  };
  const selectPartner = p => {
    const parts = (p.name || '').trim().split(' ');
    const prenom = parts.length > 1 ? parts[0] : '';
    const nom = parts.length > 1 ? parts.slice(1).join(' ') : parts[0];
    onChangePrenom(prenom);
    onChangeNom(nom);
    onSelectPartner(p);
    setSugg([]);
    setOpen(false);
  };
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg",
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("label", null, "Pr\xE9nom ", /*#__PURE__*/React.createElement("span", {
    className: "lpc-required"
  }, "*")), /*#__PURE__*/React.createElement("input", {
    value: valuePrenom,
    onChange: e => {
      onChangePrenom(e.target.value);
      search(e.target.value, 'prenom');
    },
    onBlur: () => setTimeout(() => setOpen(false), 200),
    placeholder: "Jean",
    style: fieldStyle
  }), open && activeField === 'prenom' && suggestions.length > 0 && /*#__PURE__*/React.createElement(SuggDropdown, {
    suggestions: suggestions,
    onSelect: selectPartner
  })), /*#__PURE__*/React.createElement("div", {
    className: "lpc-fg",
    style: {
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement("label", null, "Nom ", /*#__PURE__*/React.createElement("span", {
    className: "lpc-required"
  }, "*")), /*#__PURE__*/React.createElement("input", {
    value: valueNom,
    onChange: e => {
      onChangeNom(e.target.value);
      search(e.target.value, 'nom');
    },
    onBlur: () => setTimeout(() => setOpen(false), 200),
    placeholder: "Dupont",
    style: fieldStyle
  }), open && activeField === 'nom' && suggestions.length > 0 && /*#__PURE__*/React.createElement(SuggDropdown, {
    suggestions: suggestions,
    onSelect: selectPartner
  })));
}
ReactDOM.createRoot(document.getElementById('pool-checklist-root')).render(/*#__PURE__*/React.createElement(PoolChecklist, null));
