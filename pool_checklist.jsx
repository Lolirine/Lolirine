import { useState, useCallback } from "react";

const POOL_PLANS = [
  { id:"rect",   label:"Rectangulaire",        w:200, h:100, shape:"rect"   },
  { id:"square", label:"Carrée",                w:140, h:140, shape:"rect"   },
  { id:"l_shape",label:"En L",                  w:200, h:140, shape:"l"      },
  { id:"oval",   label:"Ovale / Ronde",         w:200, h:120, shape:"oval"   },
  { id:"kidney", label:"Forme libre / Haricot", w:210, h:130, shape:"kidney" },
  { id:"spa",    label:"Rect. + Spa intégré",   w:220, h:120, shape:"spa"    },
];

function PoolSvg({ plan, size=180 }) {
  const scale=size/240, s=v=>v*scale;
  const fill="rgba(14,165,233,0.18)", stroke="#0ea5e9", sw=2.5;
  const W=plan.w, H=plan.h;
  if(plan.shape==="rect") return(
    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
      <rect x="15" y="15" width={W} height={H} rx="6" fill={fill} stroke={stroke} strokeWidth={sw}/>
      {[[15,15],[15+W,15],[15,15+H],[15+W,15+H]].map(([cx,cy],i)=><circle key={i} cx={cx} cy={cy} r="4" fill={stroke}/>)}
    </svg>);
  if(plan.shape==="oval") return(
    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
      <ellipse cx={15+W/2} cy={15+H/2} rx={W/2} ry={H/2} fill={fill} stroke={stroke} strokeWidth={sw}/>
    </svg>);
  if(plan.shape==="kidney") return(
    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
      <path d={`M 15,${15+H*.5} C 15,${15+H*.05} ${15+W*.35},15 ${15+W*.5},${15+H*.1} C ${15+W*.72},${15+H*.22} ${15+W},${15+H*.1} ${15+W},${15+H*.5} C ${15+W},${15+H*.88} ${15+W*.72},${15+H} ${15+W*.5},${15+H*.88} C ${15+W*.28},${15+H*.75} ${15+W*.28},${15+H*.55} ${15+W*.15},${15+H*.55} C 15,${15+H*.55} 15,${15+H*.95} 15,${15+H*.5} Z`} fill={fill} stroke={stroke} strokeWidth={sw}/>
    </svg>);
  if(plan.shape==="l") return(
    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
      <path d={`M 15,15 H ${15+W} V ${15+H*.55} H ${15+W*.55} V ${15+H} H 15 Z`} fill={fill} stroke={stroke} strokeWidth={sw}/>
    </svg>);
  if(plan.shape==="spa") return(
    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
      <rect x="15" y="15" width={W*.72} height={H} rx="5" fill={fill} stroke={stroke} strokeWidth={sw}/>
      <rect x={15+W*.76} y={15+H*.2} width={W*.24} height={H*.6} rx="8" fill="rgba(251,191,36,0.2)" stroke="#f59e0b" strokeWidth={sw}/>
      <text x={15+W*.88} y={15+H*.54} textAnchor="middle" fontSize="8" fill="#92400e" fontFamily="sans-serif">SPA</text>
    </svg>);
  return null;
}

const INTERVENTIONS=[
  {id:"construction",    label:"🏗️ Construction neuve",       color:"#0ea5e9"},
  {id:"renovation",      label:"🔧 Rénovation",                color:"#f59e0b"},
  {id:"entretien",       label:"🧹 Entretien régulier",        color:"#10b981"},
  {id:"hivernage",       label:"❄️ Hivernage",                 color:"#6366f1"},
  {id:"remise_en_route", label:"☀️ Remise en route",           color:"#f97316"},
  {id:"materiel",        label:"⚙️ Changement de matériel",    color:"#ec4899"},
];

const CHECKLISTS={
  construction:[
    {section:"📍 Visite préalable du terrain",items:["Accès chantier (largeur portail, chemin d'accès véhicule)","Nature du sol (argile, sable, roche, remblai)","Présence nappe phréatique (profondeur estimée)","Déclivité / nivellement du terrain nécessaire","Présence d'arbres / racines / végétation envahissante","Réseaux enterrés repérés (gaz, eau, électricité, télécoms)","Distance limites de propriété (min. 1,5 m / usage : 3 m)","Permis de construire obtenu (>10 m² en Wallonie)","Étude de sol réalisée (géotechnique)","Évacuation des eaux de vidange (égout, infiltration, noue)","Orientation solaire de la piscine optimisée"]},
    {section:"📐 Dimensions & plan de bassin",items:["Longueur (m) : ______","Largeur (m) : ______","Profondeur mini (m) : ______","Profondeur maxi (m) : ______","Forme retenue (voir plan sélectionné)","Plage bain allongé (banquette immergée)","Escalier intégré (roman, droit, d'angle)","Escalier externe / échelle inox","Plongeoir prévu (profondeur ≥ 2,5 m)","Niche de filtration intégrée (réservation béton)","Caniveau périphérique / margelles débordantes","Couverture / volet roulant (réservation intégrée)"]},
    {section:"🧱 Structure & étanchéité",items:["Béton coulé (coffrage traditionnel)","Béton projeté – Gunite","Béton armé préfabriqué (panneaux)","Coque polyester (monobloc)","Kit panneaux acier galvanisé / inox","Kit panneaux polypropylène","Revêtement : liner armé (épaisseur 75/100 µ)","Revêtement : carrelage (grès cérame antidérapant)","Revêtement : enduit Marbrex / Marbelite","Revêtement : membrane armée (alkorplan)","Traitement des joints de structure","Drain de fond (si présence nappe)","Protection géotextile fond de fouille"]},
    {section:"💧 Hydraulique",items:["Nombre de bondes de fond : ______","Nombre de skimmers : ______ (1 skimmer / 25 m²)","Nombre de refoulements : ______","Buses de nage (nage à contre-courant)","Buse à balai (prise balai)","Trop-plein / régulateur de niveau","Caniveau de débordement (piscine à débordement)","Tuyauterie PVC pression ∅ 50 mm (aspiration)","Tuyauterie PVC pression ∅ 50 mm (refoulement)","Manchons anti-vibratoires sur pompe","Étanchéité traversées de paroi (joints EPDM)","Test pression canalisations avant remblai"]},
    {section:"🔄 Filtration",items:["Filtre à sable (∅ cuve ______ / débit ______ m³/h)","Filtre à cartouche","Filtre à diatomées","Sable de filtration (granulométrie 0,4–0,8 mm)","Billes de verre (alternative sable)","Pompe (marque / modèle / puissance kW) : ______","Pompe vitesse variable (économie énergie)","Préfiltre / panier préfiltre","Vanne multivoies (6 voies)","Débitmètre","Manomètre","Durée filtration programmée (h/j) : ______","Armoire électrique / coffret de commande"]},
    {section:"🧪 Traitement de l'eau",items:["Chlore manuel (galets, liquide)","Électrolyseur au sel (concentration sel ______ g/L)","Brome (pastilles / système automatique)","Traitement UV (lampe UV-C)","Ozone (générateur ozone)","PHMB (sans chlore, ex. Baquacil)","Régulation pH automatique (sonde pH + pompe doseuse)","Sonde ORP (potentiel rédox)","Pompe doseuse pH– (acide chlorhydrique / bisulfate)","Pompe doseuse désinfectant","Analyseur connecté (ex. Lovibond PoolManager)","Emplacement prévu pour produits chimiques (local fermé)"]},
    {section:"🌡️ Chauffage",items:["Pompe à chaleur air/eau (puissance ______ kW)","Pompe à chaleur réversible (piscine + abri)","Échangeur thermique (raccordement chaudière gaz/mazout)","Chauffe-eau solaire (capteurs ______ m²)","Résistance électrique (puissance ______ kW)","Couverture solaire à bulles (ép. 400 µ)","Volet roulant isolant (R thermique)","Vanne de by-pass pompe à chaleur"]},
    {section:"💡 Électricité & éclairage",items:["Projecteurs LED RGB subaquatiques","Spots LED encastrés paroi (niche inox)","Bandeau LED périmétral (plage)","Éclairage escalier submergé","Coffret électrique IP65 dédié piscine","Disjoncteur différentiel 30 mA obligatoire","Liaison équipotentielle (norme NF C 15-100)","Mise à la terre générale","Chemin de câbles gainés sous dallage","Prise extérieure étanche (pour accessoires)"]},
    {section:"🪟 Couverture & sécurité",items:["Volet roulant immergé (lames polycarbonate / alu)","Volet roulant hors-sol (banc / coffre intégré)","Couverture à barres automatique / manuelle","Filet de protection (normes NF P 90-308)","Alarme piscine OBLIGATOIRE – type : ______","Clôture de protection (h ≥ 1,10 m) + portillon auto-fermant","Signalétique profondeur / interdiction plongée"]},
    {section:"🏡 Plage, abords & finitions",items:["Margelles (carrelage / pierre naturelle / béton désactivé)","Dallage plage (antidérapant R11 minimum)","Drainage plage (pente 1% minimum vers extérieur)","Caniveau de récupération eaux de plage","Douche solaire / raccordement eau froide + ECS","Lave-pieds","Local technique (préfabriqué / maçonné / enterré)","Clôture / portillon de sécurité piscine","Nettoyage de chantier / évacuation gravats","Réception chantier avec fiche technique équipements","Notice d'utilisation et d'entretien remise au client"]},
    {section:"🤝 Administratif & SAV",items:["Devis signé + acompte encaissé","Planning prévisionnel remis","Coordonnées sous-traitants (maçon, électricien, plombier)","Garanties décennale + RC professionnelle","Dossier photos avant / pendant / après","Formation client sur équipements","Contrat d'entretien proposé"]},
  ],
  renovation:[
    {section:"🔍 Diagnostic structure",items:["Fissures structure (fines / traversantes / actives)","Test étanchéité (baisse niveau eau / test colorant)","État du fond (dénivellations, décollements)","État des parois (cloques, éclatement béton)","Corrosion armatures (épaufrures, rouille visible)","État des scellements (bondes, skimmers, projecteurs)","Désolidarisation margelles / plage","Tassement / fissures plage"]},
    {section:"🎨 Revêtement existant",items:["Type de revêtement actuel : ______","Âge du revêtement (années) : ______","Liner : déchirures / décollements / décolorations","Liner : vieillissement, perte de souplesse","Carrelage : joints décollés / cassés / tâchés","Carrelage : carreau(x) décollé(s) / fissuré(s)","Enduit : farinage / effritement / tâches","Membrane armée : décollement / percement","Évaluation : remplacement ou réfection partielle ?"]},
    {section:"🔧 Hydraulique & filtration existants",items:["Âge de la pompe (années) : ______","Débit pompe mesuré (m³/h) : ______","Bruit / vibrations anormaux pompe","Pertes de charge importantes (pression manomètre)","Âge du filtre (années) : ______","Sable à remplacer (> 5 ans)","État vanne multivoies (fuites, jeu)","État des canalisations (fuite, réduction de section)","Skimmers : panier cassé / joint usé","Bondes de fond : obturation / état des garnitures","Trop-plein fonctionnel"]},
    {section:"⚡ Électricité & éclairage",items:["Coffret électrique conforme (différentiel 30 mA)","Liaison équipotentielle présente et vérifiée","Projecteurs : fonctionnels / étanches","Projecteurs : remplacement LED prévu","Câblage apparent / dégradé","Mise aux normes NF C 15-100 nécessaire"]},
    {section:"🏗️ Travaux de structure prévus",items:["Ragréage fond et parois","Injection résine anti-fissures","Reprise étanchéité générale","Résine de pontage / primaire d'accrochage","Pose nouveau liner (mesures relevées : ______)","Réfection enduit complet","Recarrelage partiel / complet","Remplacement bondes / skimmers / refoulements","Remplacement niche projecteur","Remplacement margelles","Réfection plage (dalle / carrelage / béton)"]},
    {section:"🆕 Équipements à remplacer / ajouter",items:["Pompe (référence nouvelle : ______)","Filtre à sable (référence nouvelle : ______)","Vanne multivoies","Système de traitement (type : ______)","Pompe à chaleur (référence : ______)","Volet / couverture","Éclairage LED","Robot nettoyeur","Compteur horaire / programmateur","Système domotique / pilotage connecté"]},
    {section:"🤝 Administratif",items:["Photos état avant travaux","Devis détaillé postes par postes","Planning et durée des travaux","Arrêt filtration prévu (date) : ______","Vidange piscine planifiée","Gestion eaux de vidange (évacuation conforme)","Garanties travaux communiquées"]},
  ],
  entretien:[
    {section:"🧪 Analyse de l'eau",items:["pH (cible 7,2–7,4) → mesuré : ______","TAC (cible 80–120 mg/L) → mesuré : ______","TH – Dureté (cible 150–300 mg/L) → mesuré : ______","Chlore libre (cible 1,0–3,0 mg/L) → mesuré : ______","Chlore combiné (< 0,6 mg/L) → mesuré : ______","Taux de sel si électrolyseur → mesuré : ______","Cyanurate (< 75 mg/L) → mesuré : ______","Phosphates (< 0,1 mg/L) → mesuré : ______","Température eau (°C) : ______","Turbidité (limpide / trouble / verte)"]},
    {section:"🧹 Nettoyage bassin",items:["Écrémage surface (feuilles, insectes, pollens)","Aspiration fond (manuelle / robot)","Brossage parois et fond","Nettoyage ligne de flottaison","Nettoyage panier(s) skimmer(s)","Nettoyage panier préfiltre pompe","Contre-lavage si pression ≥ 0,5 bar","Nettoyage cartouche filtrante (si applicable)","Nettoyage niche projecteur(s)","Rinçage plage / abords","Nettoyage local technique"]},
    {section:"🔄 Filtration & équipements",items:["Pression manomètre relevée : ______ bar","Débit pompe vérifié","Bruit / vibration anormal pompe","Vérification programmateur / horloge","Vérification vanne multivoies (absence de fuite)","Vérification électrolyseur (cellule / production)","Vérification pompe doseuse pH","Vérification sonde ORP / pH","Niveau d'eau ajusté (mi-skimmer)","Vérification alarme piscine","Vérification volet / mécanisme"]},
    {section:"💊 Traitements correctifs appliqués",items:["Correction pH (produit / dose) : ______","Correction TAC (bicarbonate / CO2) : ______","Correction TH (anti-calcaire / eau douce) : ______","Choc chlore (dose) : ______","Algicide préventif appliqué","Floculant / clarifiant appliqué","Anti-phosphates appliqué","Traitement sel ajouté (kg) : ______"]},
    {section:"📋 Observations & recommandations",items:["Usure liner / revêtement à surveiller","Équipement à remplacer prochainement : ______","Travaux recommandés : ______","Prochain entretien prévu (date) : ______","Produits laissés au client : ______","Bon de visite signé par le client"]},
  ],
  hivernage:[
    {section:"🌊 Préparation de l'eau",items:["Dernière analyse eau complète réalisée","pH ajusté à 7,2–7,4","TAC ajusté (> 120 mg/L recommandé)","Chlore choc appliqué (J-3 minimum)","Algicide hivernal longue durée appliqué","Anti-calcaire hivernal appliqué","Floculant final appliqué","Nettoyage complet bassin (aspiration + brossage)","Ligne de flottaison nettoyée"]},
    {section:"📉 Niveau d'eau & bouchons",items:["Abaissement niveau d'eau (sous le bas des skimmers)","Niveau recommandé : ______ cm sous la margelle","Si risque gel intense : vidange plus importante","Bouchons hivernage posés dans skimmers","Bouchons posés dans refoulements","Bonde de fond : bouchon / clapet fermé","Flotteurs antigel placés (nombre : ______)","Prise balai bouchonnée"]},
    {section:"🔌 Arrêt des équipements",items:["Filtration arrêtée","Vidange complète de la pompe","Vidange filtre à sable (vanne en position vidange)","Vidange vanne multivoies","Soufflage des canalisations (compresseur)","Vidange préfiltre pompe","Arrêt électrolyseur + cellule démontée si gel <-10°C","Arrêt UV / ozone","Arrêt pompes doseuses + vidange","Débranchement programmateur / coffret","Hivernation pompe à chaleur (procédure constructeur)","Vidange échangeur thermique si applicable"]},
    {section:"🧳 Rangement & protection",items:["Robot nettoyeur sorti, rincé, stocké","Thermomètre sorti","Équipements de mesure rincés et rangés","Skimmer(s) : panier rentré ou protégé","Couverture hivernage mise en place (type : ______)","État couverture vérifié (déchirures, attaches)","Filet anti-feuilles posé si couverture bulle","Alarme piscine vérifiée / maintenue active"]},
    {section:"📋 Observations & suivi",items:["Photos état piscine à la fermeture","Date d'hivernage : ______","Date de remise en route prévisionnelle : ______","Remarques particulières : ______","Bon d'intervention signé","Prochaine remise en route planifiée"]},
  ],
  remise_en_route:[
    {section:"🧹 Réouverture bassin",items:["Retrait couverture hivernage (nettoyage + séchage avant rangement)","Retrait filet anti-feuilles","Retrait flotteurs antigel","Retrait bouchons skimmers / refoulements / bonde de fond","Nettoyage fond et parois (algues, dépôts hivernaux)","Remontée du niveau d'eau (mi-skimmer)","Rinçage plage et abords"]},
    {section:"🔌 Redémarrage équipements",items:["Remontage pompe (vérification sens rotation)","Amorçage pompe / purge d'air","Remontage vanne multivoies","Mise en marche filtration","Rinçage filtre (contre-lavage + rinçage)","Remontage / reconnexion électrolyseur","Remontage pompes doseuses + vérification niveaux cuves","Remontage UV / ozone","Redémarrage pompe à chaleur (procédure constructeur)","Vérification programmateur / horloge (heure d'été !)","Test coffret électrique / disjoncteur différentiel","Vérification alarme piscine"]},
    {section:"🧪 Remise en état de l'eau",items:["Analyse eau complète (pH, TAC, TH, chlore, sel)","pH mesuré : ______ → correction : ______","TAC mesuré : ______ → correction : ______","TH mesuré : ______ → correction : ______","Traitement choc (chlore ou oxygène actif)","Algicide curatif si présence d'algues","Floculant / clarifiant","Ajout sel si électrolyseur (quantité : ______ kg)","Filtration continu 24h à 48h minimum","Eau limpide atteinte avant baignade"]},
    {section:"✅ Contrôle général",items:["Vérification absence de fuite (pompe, vanne, canalisations)","Vérification projecteurs (étanchéité)","Test robot nettoyeur","Vérification volet roulant / mécanisme","Nettoyage local technique","Produits d'entretien réapprovisionnés","Formation / rappel d'utilisation si nécessaire","Bon d'intervention signé","Prochain entretien programmé"]},
  ],
  materiel:[
    {section:"🔎 Diagnostic matériel existant",items:["Pompe – marque / modèle actuel : ______","Pompe – puissance (kW) : ______ / âge (ans) : ______","Pompe – panne constatée : ______","Filtre – marque / modèle : ______ / ∅ cuve : ______","Filtre – âge : ______ / état du sable : ______","Vanne multivoies – marque / état : ______","Système de traitement – type : ______ / âge : ______","Électrolyseur – marque / taux de sel actuel : ______","PAC – marque / modèle / puissance : ______ / âge : ______","Volet – type / état mécanique : ______","Éclairage – type / nb projecteurs : ______","Robot nettoyeur – marque / modèle : ______","Photos du matériel défectueux réalisées"]},
    {section:"🔄 Remplacement pompe",items:["Débit requis calculé (volume bassin / 4h) : ______ m³/h","Référence nouvelle pompe sélectionnée : ______","Pompe vitesse variable (VEI) recommandée","Raccordements hydrauliques (diamètre ∅) : ______","Manchons anti-vibratoires neufs","Test de débit après installation"]},
    {section:"🔄 Remplacement filtre",items:["Diamètre filtre recommandé selon débit : ______","Référence nouveau filtre : ______","Type de média filtrant : sable / verre / billes","Quantité de sable / média : ______ kg","Vanne multivoies adaptée","Manomètre neuf posé","Test de contre-lavage effectué"]},
    {section:"🔄 Remplacement traitement",items:["Électrolyseur – référence : ______ / production Cl/h : ______","Cellule d'électrolyse (remplacement seule ou boîtier complet)","Régulation pH automatique – marque : ______","Sondes pH / ORP remplacées","Pompes doseuses – marque / débit : ______","UV – puissance W : ______ / lampe neuve","Ozone – références : ______","Analyseur connecté / Wi-Fi : ______"]},
    {section:"🔄 Remplacement chauffage",items:["Pompe à chaleur – référence : ______ / COP : ______","PAC réversible (climatisation abri incluse)","Échangeur thermique – raccordement chaudière vérifié","Vanne de by-pass posée","Mise en service selon procédure constructeur","Test de montée en température bassin"]},
    {section:"🔄 Remplacement couverture / volet",items:["Type de couverture choisie : ______","Volet roulant immergé – réservation béton vérifiée","Volet roulant hors-sol – emplacement coffre","Couverture à barres – type de motorisation","Lames : polycarbonate / alu / PVC (couleur : ______)","Test motorisation / sécurité anti-pincement","Notice d'utilisation remise au client"]},
    {section:"🔄 Remplacement éclairage",items:["Nombre de projecteurs : ______","Type : LED RGB / LED blanc chaud / monochrome","Niche(s) existante(s) compatibles ou à remplacer","Transformateur basse tension 12V / 100V","Test d'étanchéité après installation","Programmation RGB / scénarios lumineux"]},
    {section:"🔄 Robot nettoyeur",items:["Robot fond seul / fond+parois / fond+parois+ligne d'eau","Référence robot : ______","Alimentation : filaire / sur batterie","Test de couverture fond / parois","Application mobile configurée","Sac / filtre cartouche de rechange laissé"]},
    {section:"🤝 Clôture intervention",items:["Mise en service complète réalisée","Démonstration au client","Ancien matériel évacué","Garantie constructeur enregistrée","Bon d'intervention signé","Facture / attestation TVA réduite si applicable"]},
  ],
};

/* ══════════════════════ PRODUCT PANEL ══════════════════════════════════════ */
async function searchOdooProducts(query) {
  try {
    const res = await fetch("https://www.lolirinepoolstore.be/web/dataset/call_kw", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        jsonrpc:"2.0",method:"call",id:1,
        params:{
          model:"product.template",method:"search_read",
          args:[[["website_published","=",true],["website_id","in",[6,false]],"|",["name","ilike",query],["description_sale","ilike",query]]],
          kwargs:{fields:["id","name","list_price","default_code","categ_id","image_128"],limit:10,order:"name asc"}
        }
      }),
      signal:AbortSignal.timeout(5000)
    });
    const d = await res.json();
    if(d?.result?.length) return {source:"odoo",products:d.result.map(p=>({
      id:p.id,ref:p.default_code||"",name:p.name,price:p.list_price,
      category:p.categ_id?.[1]||"",
      image:p.image_128?`data:image/png;base64,${p.image_128}`:null,unit:"pièce"
    }))};
    return null;
  } catch { return null; }
}

async function suggestViaAI(itemText, sectionLabel) {
  const res = await fetch("https://api.anthropic.com/v1/messages",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      model:"claude-sonnet-4-20250514",max_tokens:900,
      system:`Tu es expert en équipements de piscine (Lolirine Pool Store, Belgique).
Pour un point de contrôle d'une fiche d'intervention piscine, liste les produits/matériaux concrets à prévoir.
Réponds UNIQUEMENT en JSON valide sans markdown :
{"products":[{"ref":"","name":"Nom produit","category":"Catégorie","unit":"pièce|kg|L|m|m²|lot","note":"info"}]}
Max 7 produits. Utilise les marques : Fluidra, Zodiac, Hayward, Pentair, Astralpool, SCP, HTH, BWT, Dryden Aqua, Lovibond.`,
      messages:[{role:"user",content:`Section : ${sectionLabel}\nPoint de contrôle : "${itemText}"\nProduits à prévoir ?`}]
    })
  });
  const d = await res.json();
  const text = d.content?.[0]?.text||"{}";
  const parsed = JSON.parse(text.replace(/```json|```/g,"").trim());
  return {source:"ai", products:(parsed.products||[])};
}

function ProductPanel({itemText,sectionLabel,onAdd,onClose}) {
  const [q,setQ]           = useState(itemText.replace(/_{3,}/g,"").trim().slice(0,40));
  const [results,setResults]= useState([]);
  const [loading,setLoading]= useState(false);
  const [source,setSource]  = useState(null);
  const [sel,setSel]        = useState({});
  const [qtys,setQtys]      = useState({});

  const search = useCallback(async(query)=>{
    if(!query.trim())return;
    setLoading(true);setResults([]);setSource(null);
    let r = await searchOdooProducts(query);
    if(!r) r = await suggestViaAI(itemText,sectionLabel);
    setResults(r?.products||[]);setSource(r?.source||null);setLoading(false);
  },[itemText,sectionLabel]);

  useState(()=>{search(q);},[]);

  const toggle = i => setSel(p=>({...p,[i]:!p[i]}));
  const setQty = (i,v)=> setQtys(p=>({...p,[i]:v}));
  const selCount = Object.values(sel).filter(Boolean).length;

  const confirm = () => {
    onAdd(results.filter((_,i)=>sel[i]).map((p,i)=>({...p,qty:Number(qtys[i]||1)})));
    onClose();
  };

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(10,20,40,0.55)",zIndex:999,display:"flex",alignItems:"center",justifyContent:"center",padding:16}}>
      <div style={{background:"#fff",borderRadius:18,width:"100%",maxWidth:660,maxHeight:"88vh",display:"flex",flexDirection:"column",boxShadow:"0 24px 80px rgba(0,0,0,0.25)",overflow:"hidden"}}>
        {/* header */}
        <div style={{padding:"15px 20px",borderBottom:"1.5px solid #dde4ed",display:"flex",gap:12,alignItems:"flex-start"}}>
          <div style={{flex:1}}>
            <div style={{fontWeight:700,fontSize:15,fontFamily:"'DM Serif Display',serif"}}>🛒 Lier des produits à ce point</div>
            <div style={{fontSize:12,color:"#6b7a8d",marginTop:3,lineHeight:1.4,maxWidth:490}}>{itemText.slice(0,90)}{itemText.length>90?"…":""}</div>
          </div>
          <button onClick={onClose} style={{background:"none",border:"1.5px solid #dde4ed",borderRadius:8,padding:"5px 12px",cursor:"pointer",fontSize:13,color:"#6b7a8d",flexShrink:0}}>✕</button>
        </div>
        {/* search bar */}
        <div style={{padding:"10px 20px",borderBottom:"1px solid #f0f4f8",display:"flex",gap:8}}>
          <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==="Enter"&&search(q)}
            placeholder="Nom de produit, référence, marque…"
            style={{flex:1,border:"1.5px solid #dde4ed",borderRadius:9,padding:"8px 13px",fontFamily:"inherit",fontSize:14,outline:"none"}}/>
          <button onClick={()=>search(q)}
            style={{background:"#0ea5e9",color:"#fff",border:"none",borderRadius:9,padding:"8px 18px",fontWeight:600,cursor:"pointer",fontSize:13,whiteSpace:"nowrap"}}>
            {loading?"…":"Chercher"}
          </button>
        </div>
        {/* source badge */}
        {source && (
          <div style={{padding:"5px 20px",background:source==="odoo"?"#f0fdf4":"#fffbeb",borderBottom:"1px solid #f0f4f8"}}>
            <span style={{fontSize:11,fontWeight:600,padding:"2px 9px",borderRadius:20,background:source==="odoo"?"#dcfce7":"#fef3c7",color:source==="odoo"?"#166534":"#92400e"}}>
              {source==="odoo"?"✅ Catalogue Lolirine Pool Store (données live)":"✨ Suggestions IA basées sur le contexte (catalogue non accessible en direct)"}
            </span>
          </div>
        )}
        {/* results */}
        <div style={{flex:1,overflowY:"auto",padding:"6px 20px"}}>
          {loading && <div style={{padding:40,textAlign:"center",color:"#6b7a8d"}}><div style={{fontSize:30,marginBottom:12}}>🔄</div><div style={{fontSize:14}}>Recherche en cours…</div></div>}
          {!loading&&results.length===0&&source && <div style={{padding:30,textAlign:"center",color:"#6b7a8d",fontSize:13}}>Aucun résultat. Affinez la recherche.</div>}
          {results.map((p,i)=>(
            <div key={i} onClick={()=>toggle(i)}
              style={{display:"flex",gap:11,padding:"9px 11px",margin:"4px 0",borderRadius:10,border:`1.5px solid ${sel[i]?"#0ea5e9":"#e8edf3"}`,background:sel[i]?"rgba(14,165,233,0.05)":"#fff",cursor:"pointer",transition:"all .15s",alignItems:"flex-start"}}>
              <div style={{width:18,height:18,border:`2px solid ${sel[i]?"#0ea5e9":"#ccc"}`,borderRadius:5,background:sel[i]?"#0ea5e9":"#fff",display:"grid",placeItems:"center",flexShrink:0,marginTop:3}}>
                {sel[i]&&<span style={{color:"#fff",fontSize:11,fontWeight:700}}>✓</span>}
              </div>
              {p.image&&<img src={p.image} alt="" style={{width:46,height:46,objectFit:"contain",borderRadius:7,border:"1px solid #f0f4f8",flexShrink:0}}/>}
              {!p.image&&<div style={{width:46,height:46,borderRadius:7,background:"#f0f6ff",display:"grid",placeItems:"center",flexShrink:0,fontSize:22}}>🏊</div>}
              <div style={{flex:1,minWidth:0}}>
                <div style={{fontWeight:600,fontSize:13,lineHeight:1.35}}>{p.name}</div>
                <div style={{fontSize:11,color:"#6b7a8d",marginTop:2,display:"flex",gap:8,flexWrap:"wrap"}}>
                  {p.ref&&<span style={{background:"#f0f4f8",padding:"1px 6px",borderRadius:4}}>{p.ref}</span>}
                  {p.category&&<span>{p.category}</span>}
                  {p.note&&<span style={{fontStyle:"italic",color:"#94a3b8"}}>{p.note}</span>}
                </div>
                {p.price>0&&<div style={{fontSize:12,fontWeight:600,color:"#0ea5e9",marginTop:3}}>{p.price.toFixed(2)} €</div>}
              </div>
              {sel[i]&&(
                <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:3,flexShrink:0}} onClick={e=>e.stopPropagation()}>
                  <span style={{fontSize:10,color:"#6b7a8d"}}>Qté</span>
                  <input type="number" min="1" value={qtys[i]||1} onChange={e=>setQty(i,e.target.value)}
                    style={{width:52,textAlign:"center",border:"1.5px solid #0ea5e9",borderRadius:6,padding:"3px",fontSize:13,fontFamily:"inherit"}}/>
                  <span style={{fontSize:10,color:"#6b7a8d"}}>{p.unit||"pc"}</span>
                </div>
              )}
            </div>
          ))}
        </div>
        {/* footer */}
        <div style={{padding:"11px 20px",borderTop:"1.5px solid #dde4ed",display:"flex",alignItems:"center",gap:10}}>
          <span style={{fontSize:13,color:"#6b7a8d",flex:1}}>{selCount} produit(s) sélectionné(s)</span>
          <button onClick={onClose} style={{background:"none",border:"1.5px solid #dde4ed",borderRadius:9,padding:"8px 16px",cursor:"pointer",fontFamily:"inherit",fontSize:13}}>Annuler</button>
          <button onClick={confirm} disabled={!selCount}
            style={{background:selCount?"#0ea5e9":"#d1d5db",color:"#fff",border:"none",borderRadius:9,padding:"8px 20px",fontWeight:600,cursor:selCount?"pointer":"not-allowed",fontFamily:"inherit",fontSize:13}}>
            ✓ Ajouter à l'intervention
          </button>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════ SECTION BLOCK ════════════════════════════════════════ */
function SectionBlock({sec,si,checked,notes,toggle,setNote,accent,linkedProducts,onAddProducts,onRemoveProduct}) {
  const [open,setOpen]          = useState(true);
  const [productPanel,setProductPanel] = useState(null);
  const sChecked = sec.items.filter((_,i)=>checked[`${si}_${i}`]).length;

  return (
    <>
      {productPanel!==null&&(
        <ProductPanel
          itemText={sec.items[productPanel]}
          sectionLabel={sec.section}
          onAdd={prods=>onAddProducts(si,productPanel,prods)}
          onClose={()=>setProductPanel(null)}
        />
      )}
      <div className="section">
        <div className="section-header" onClick={()=>setOpen(o=>!o)}>
          <h3>{sec.section}</h3>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            <span className="section-progress">{sChecked}/{sec.items.length}</span>
            <span style={{fontSize:12,color:"#6b7a8d"}}>{open?"▲":"▼"}</span>
          </div>
        </div>
        <div className={`section-body${open?"":" collapsed"}`}>
          {sec.items.map((item,idx)=>{
            const k=`${si}_${idx}`, isChk=!!checked[k], prods=linkedProducts[k]||[];
            return (
              <div key={idx}>
                <div className={`item-row${isChk?" checked-row":""}`}>
                  <input type="checkbox" className="cb" checked={isChk} onChange={()=>toggle(si,idx)}/>
                  <span className={`item-text${isChk?" done":""}`}>{item}</span>
                  <button className="add-prod-btn no-print" title="Lier des produits du catalogue" onClick={()=>setProductPanel(idx)}>
                    🛒{prods.length>0&&<span className="prod-badge">{prods.length}</span>}
                  </button>
                  <input className="note-input no-print" placeholder="Note…" value={notes[k]||""} onChange={e=>setNote(si,idx,e.target.value)}/>
                </div>
                {prods.length>0&&(
                  <div className="linked-products">
                    {prods.map((p,pi)=>(
                      <div key={pi} className="linked-chip">
                        <span className="chip-qty">{p.qty}×</span>
                        {p.ref&&<span className="chip-ref">[{p.ref}]</span>}
                        <span className="chip-name">{p.name}</span>
                        {p.price>0&&<span className="chip-price">{(p.price*(p.qty||1)).toFixed(2)} €</span>}
                        <button className="chip-del no-print" onClick={()=>onRemoveProduct(si,idx,pi)}>✕</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

/* ════════════════════════ MAIN APP ════════════════════════════════════════ */
export default function PoolChecklist() {
  const [step,setStep]               = useState(0);
  const [intervention,setIntervention]= useState(null);
  const [plan,setPlan]               = useState(null);
  const [client,setClient]           = useState({nom:"",adresse:"",date:new Date().toISOString().slice(0,10),technicien:"",ref:"",tel:""});
  const [checked,setChecked]         = useState({});
  const [notes,setNotes]             = useState({});
  const [linkedProducts,setLinkedProducts] = useState({});

  const toggle  = (si,idx) => { const k=`${si}_${idx}`; setChecked(p=>({...p,[k]:!p[k]})); };
  const setNote = (si,idx,v)=> { const k=`${si}_${idx}`; setNotes(p=>({...p,[k]:v})); };
  const addProducts = (si,idx,prods)=>{ const k=`${si}_${idx}`; setLinkedProducts(p=>({...p,[k]:[...(p[k]||[]),...prods]})); };
  const removeProduct=(si,idx,pi)=>{ const k=`${si}_${idx}`; setLinkedProducts(p=>({...p,[k]:(p[k]||[]).filter((_,i)=>i!==pi)})); };

  const intData  = INTERVENTIONS.find(i=>i.id===intervention);
  const sections = intervention?CHECKLISTS[intervention]:[];
  const totalItems   = sections.reduce((a,s)=>a+s.items.length,0);
  const checkedCount = Object.values(checked).filter(Boolean).length;
  const accent = intData?.color||"#0ea5e9";

  const allProds = Object.entries(linkedProducts).filter(([,a])=>a.length>0).flatMap(([k,a])=>a.map(p=>({...p,_k:k})));
  const totalEst = allProds.reduce((a,p)=>a+(p.price||0)*(p.qty||1),0);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
        :root{--bg:#f0f4f8;--card:#fff;--text:#1a2332;--sub:#6b7a8d;--bd:#dde4ed;--acc:${accent};}
        *{box-sizing:border-box;margin:0;padding:0;}
        body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);}
        .app{max-width:920px;margin:0 auto;padding:22px 14px 60px;}
        .hdr{display:flex;align-items:center;gap:13px;margin-bottom:26px;padding-bottom:18px;border-bottom:2px solid var(--bd);}
        .logo{width:44px;height:44px;background:var(--acc);border-radius:10px;display:grid;place-items:center;font-size:22px;flex-shrink:0;}
        .hdr h1{font-family:'DM Serif Display',serif;font-size:21px;}
        .hdr p{font-size:13px;color:var(--sub);margin-top:2px;}
        .stepper{display:flex;gap:0;margin-bottom:26px;}
        .si{flex:1;display:flex;flex-direction:column;align-items:center;gap:5px;position:relative;}
        .si:not(:last-child)::after{content:'';position:absolute;top:15px;left:50%;width:100%;height:2px;background:var(--bd);z-index:0;}
        .si.a::after,.si.d::after{background:var(--acc);}
        .sn{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:600;border:2px solid var(--bd);background:var(--card);position:relative;z-index:1;color:var(--sub);}
        .si.a .sn,.si.d .sn{border-color:var(--acc);background:var(--acc);color:#fff;}
        .sl{font-size:11px;color:var(--sub);font-weight:500;text-align:center;}
        .si.a .sl{color:var(--acc);}
        .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:11px;}
        .card{background:var(--card);border:2px solid var(--bd);border-radius:12px;padding:17px;cursor:pointer;transition:all .2s;}
        .card:hover{border-color:var(--acc);transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.07);}
        .card.sel{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 9%,white);}
        .ct{font-size:15px;font-weight:600;}.cs{font-size:12px;color:var(--sub);margin-top:4px;}
        .pc{background:var(--card);border:2px solid var(--bd);border-radius:12px;padding:15px;cursor:pointer;transition:all .2s;display:flex;flex-direction:column;align-items:center;gap:9px;}
        .pc:hover{border-color:var(--acc);transform:translateY(-2px);}
        .pc.sel{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 8%,white);}
        .pl{font-size:13px;font-weight:600;text-align:center;}
        .fg{display:flex;flex-direction:column;gap:5px;}.fgf{grid-column:1/-1;}
        .fg label{font-size:12px;font-weight:600;color:var(--sub);text-transform:uppercase;letter-spacing:.5px;}
        .fg input{border:1.5px solid var(--bd);border-radius:8px;padding:9px 12px;font-family:inherit;font-size:14px;background:var(--bg);color:var(--text);transition:border .2s;}
        .fg input:focus{outline:none;border-color:var(--acc);background:#fff;}
        .section{background:var(--card);border-radius:13px;margin-bottom:11px;overflow:hidden;border:1.5px solid var(--bd);}
        .section-header{padding:12px 17px;display:flex;align-items:center;justify-content:space-between;cursor:pointer;background:#fafbfc;border-bottom:1.5px solid var(--bd);}
        .section-header h3{font-size:14px;font-weight:600;}
        .section-progress{font-size:12px;color:var(--sub);background:var(--bg);padding:3px 10px;border-radius:20px;border:1px solid var(--bd);}
        .section-body{padding:4px 0;}.section-body.collapsed{display:none;}
        .item-row{display:flex;gap:9px;align-items:flex-start;padding:7px 15px;transition:background .15s;}
        .item-row:hover{background:#f8fafc;}.item-row.checked-row{background:color-mix(in srgb,var(--acc) 5%,white);}
        .cb{width:17px;height:17px;flex-shrink:0;margin-top:2px;accent-color:var(--acc);cursor:pointer;}
        .item-text{flex:1;font-size:13.5px;line-height:1.5;}.item-text.done{text-decoration:line-through;color:var(--sub);}
        .add-prod-btn{background:none;border:1.5px solid var(--bd);border-radius:7px;padding:3px 8px;font-size:13px;cursor:pointer;transition:all .15s;position:relative;flex-shrink:0;}
        .add-prod-btn:hover{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 8%,white);}
        .prod-badge{position:absolute;top:-6px;right:-6px;background:var(--acc);color:#fff;border-radius:50%;width:16px;height:16px;font-size:10px;display:grid;place-items:center;font-weight:700;}
        .note-input{border:1px solid var(--bd);border-radius:6px;padding:4px 8px;font-size:12px;font-family:inherit;color:var(--text);background:var(--bg);width:120px;flex-shrink:0;}
        .note-input:focus{outline:none;border-color:var(--acc);}
        .linked-products{padding:3px 15px 8px 41px;display:flex;flex-direction:column;gap:4px;}
        .linked-chip{display:flex;gap:7px;align-items:center;background:color-mix(in srgb,var(--acc) 8%,white);border:1px solid color-mix(in srgb,var(--acc) 30%,#e0e0e0);border-radius:7px;padding:4px 10px;font-size:12px;}
        .chip-qty{font-weight:700;color:var(--acc);min-width:26px;}
        .chip-ref{color:var(--sub);font-size:11px;font-family:monospace;}
        .chip-name{flex:1;font-weight:500;}
        .chip-price{font-weight:600;color:#059669;margin-left:auto;white-space:nowrap;}
        .chip-del{background:none;border:none;cursor:pointer;color:#ccc;font-size:11px;padding:0 2px;}
        .chip-del:hover{color:#ef4444;}
        .progbar{background:var(--bd);border-radius:20px;height:8px;overflow:hidden;}
        .progfill{height:100%;border-radius:20px;background:linear-gradient(90deg,var(--acc),color-mix(in srgb,var(--acc) 70%,white));transition:width .4s;}
        .btn{padding:10px 21px;border-radius:9px;font-family:inherit;font-size:14px;font-weight:600;cursor:pointer;transition:all .2s;border:2px solid transparent;}
        .btn-p{background:var(--acc);color:#fff;}.btn-p:hover{filter:brightness(1.1);transform:translateY(-1px);}.btn-p:disabled{background:#ccc;cursor:not-allowed;transform:none;}
        .btn-s{background:var(--card);color:var(--text);border-color:var(--bd);}.btn-s:hover{border-color:var(--acc);color:var(--acc);}
        .btn-g{background:none;border:none;color:var(--sub);font-size:13px;cursor:pointer;padding:6px 10px;}.btn-g:hover{color:var(--text);}
        .btn-pr{background:#1a2332;color:#fff;}.btn-pr:hover{background:#2d3f57;}
        .acts{display:flex;gap:10px;align-items:center;flex-wrap:wrap;}.sp{flex:1;}
        .sumbox{background:var(--card);border:1.5px solid var(--bd);border-radius:12px;padding:13px 17px;display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-bottom:16px;}
        .si2{display:flex;flex-direction:column;gap:2px;}
        .si2 span{font-size:11px;color:var(--sub);text-transform:uppercase;letter-spacing:.5px;}
        .si2 strong{font-size:14px;font-weight:700;}
        .mat-tbl{width:100%;border-collapse:collapse;font-size:13px;}
        .mat-tbl th{text-align:left;padding:7px 11px;background:#f8fafc;border-bottom:2px solid var(--bd);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--sub);}
        .mat-tbl td{padding:7px 11px;border-bottom:1px solid var(--bd);}
        .mat-tbl tr:last-child td{border-bottom:none;}
        .mat-tot{background:color-mix(in srgb,var(--acc) 7%,white);}
        @media print{
          @page{size:A4;margin:15mm 13mm;}
          body{background:#fff!important;font-size:9pt;}
          .app{max-width:100%;padding:0;}
          .no-print,.stepper,.acts,.btn,.note-input,.add-prod-btn{display:none!important;}
          .hdr{border-bottom:1.5pt solid #000;padding-bottom:8pt;margin-bottom:10pt;}
          .hdr h1{font-size:14pt;}
          .p-hdr{display:block!important;}
          .sumbox{border:1pt solid #ccc;padding:6pt 10pt;margin-bottom:9pt;}
          .section{border:1pt solid #ccc;border-radius:0;page-break-inside:avoid;margin-bottom:6pt;}
          .section-header{background:#f2f2f2!important;padding:5pt 8pt;}
          .section-header h3{font-size:9.5pt;}
          .section-progress{display:none;}
          .item-row{padding:3pt 7pt;border-bottom:.4pt solid #eee;}
          .cb{width:9pt;height:9pt;}
          .item-text{font-size:8.5pt;}.item-text.done{text-decoration:none;color:#000;}
          .progbar{display:none!important;}
          .section-body.collapsed{display:block!important;}
          .linked-products{padding:2pt 7pt 3pt 22pt;}
          .linked-chip{border:.5pt solid #ccc;background:#f9f9f9!important;padding:2pt 5pt;font-size:7.5pt;}
          .chip-del{display:none;}
          .mat-tbl{font-size:8pt;}
          .mat-tbl th{font-size:7.5pt;}
          .p-plan{display:block!important;}
        }
      `}</style>
      <div className="app">
        {/* HEADER */}
        <div className="hdr">
          <div className="logo">🏊</div>
          <div>
            <h1>Lolirine Pool Store — Fiche de visite chantier</h1>
            <p>Diagnostic · intervention · produits liés · devis estimatif</p>
          </div>
        </div>

        {/* STEPPER */}
        <div className="stepper no-print">
          {["Type d'intervention","Infos client","Plan de bassin","Check-list & produits"].map((lbl,i)=>(
            <div key={i} className={`si${step===i?" a":step>i?" d":""}`}>
              <div className="sn">{step>i?"✓":i+1}</div>
              <div className="sl">{lbl}</div>
            </div>
          ))}
        </div>

        {/* STEP 0 */}
        {step===0&&(
          <div>
            <h2 style={{fontFamily:"'DM Serif Display',serif",fontSize:20,marginBottom:15}}>Sélectionner le type d'intervention</h2>
            <div className="grid">
              {INTERVENTIONS.map(iv=>(
                <div key={iv.id} className={`card${intervention===iv.id?" sel":""}`} style={{"--acc":iv.color}} onClick={()=>setIntervention(iv.id)}>
                  <div className="ct">{iv.label}</div>
                  <div className="cs">{CHECKLISTS[iv.id].reduce((a,s)=>a+s.items.length,0)} points · {CHECKLISTS[iv.id].length} sections</div>
                </div>
              ))}
            </div>
            <div className="acts" style={{marginTop:18}}><div className="sp"/><button className="btn btn-p" disabled={!intervention} onClick={()=>setStep(1)}>Suivant →</button></div>
          </div>
        )}

        {/* STEP 1 */}
        {step===1&&(
          <div>
            <h2 style={{fontFamily:"'DM Serif Display',serif",fontSize:20,marginBottom:15}}>Informations client & chantier</h2>
            <div className="section" style={{padding:20}}>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:13}}>
                <div className="fg fgf"><label>Nom / Raison sociale</label><input value={client.nom} onChange={e=>setClient(p=>({...p,nom:e.target.value}))} placeholder="M./Mme Dupont"/></div>
                <div className="fg fgf"><label>Adresse du chantier</label><input value={client.adresse} onChange={e=>setClient(p=>({...p,adresse:e.target.value}))} placeholder="Rue de la Piscine 12, 5000 Namur"/></div>
                <div className="fg"><label>Téléphone</label><input value={client.tel} onChange={e=>setClient(p=>({...p,tel:e.target.value}))} placeholder="+32 4xx xx xx xx"/></div>
                <div className="fg"><label>Date de visite</label><input type="date" value={client.date} onChange={e=>setClient(p=>({...p,date:e.target.value}))}/></div>
                <div className="fg"><label>Technicien / Commercial</label><input value={client.technicien} onChange={e=>setClient(p=>({...p,technicien:e.target.value}))} placeholder="Prénom NOM"/></div>
                <div className="fg"><label>Référence dossier</label><input value={client.ref} onChange={e=>setClient(p=>({...p,ref:e.target.value}))} placeholder="LPS-2025-001"/></div>
              </div>
            </div>
            <div className="acts" style={{marginTop:15}}>
              <button className="btn btn-s" onClick={()=>setStep(0)}>← Retour</button><div className="sp"/>
              <button className="btn btn-p" onClick={()=>setStep(2)}>Suivant →</button>
            </div>
          </div>
        )}

        {/* STEP 2 */}
        {step===2&&(
          <div>
            <h2 style={{fontFamily:"'DM Serif Display',serif",fontSize:20,marginBottom:6}}>Plan de bassin</h2>
            <p style={{fontSize:13,color:"var(--sub)",marginBottom:15}}>Sélectionner la forme correspondante (imprimée sur la fiche)</p>
            <div className="grid">
              {POOL_PLANS.map(p=>(
                <div key={p.id} className={`pc${plan===p.id?" sel":""}`} onClick={()=>setPlan(p.id)}>
                  <PoolSvg plan={p} size={145}/><div className="pl">{p.label}</div>
                </div>
              ))}
            </div>
            <div className="acts" style={{marginTop:18}}>
              <button className="btn btn-s" onClick={()=>setStep(1)}>← Retour</button><div className="sp"/>
              <button className="btn btn-g" onClick={()=>{setPlan(null);setStep(3);}}>Passer (sans plan)</button>
              <button className="btn btn-p" disabled={!plan} onClick={()=>setStep(3)}>Suivant →</button>
            </div>
          </div>
        )}

        {/* STEP 3 */}
        {step===3&&(
          <div>
            {/* Print header */}
            <div style={{display:"none"}} className="p-hdr">
              <div className="sumbox" style={{display:"flex"}}>
                {[["Client",client.nom],["Adresse",client.adresse],["Tél",client.tel],["Date",client.date],["Technicien",client.technicien],["Réf.",client.ref],["Intervention",intData?.label]].filter(([,v])=>v).map(([l,v])=>(
                  <div key={l} className="si2"><span>{l}</span><strong>{v}</strong></div>
                ))}
              </div>
            </div>

            {/* Summary bar (screen) */}
            <div className="sumbox no-print">
              <div className="si2"><span>Client</span><strong>{client.nom||"—"}</strong></div>
              <div className="si2"><span>Date</span><strong>{client.date}</strong></div>
              <div className="si2"><span>Intervention</span><strong style={{color:accent}}>{intData?.label}</strong></div>
              {plan&&<div className="si2"><span>Plan</span><strong>{POOL_PLANS.find(p=>p.id===plan)?.label}</strong></div>}
              <div className="sp"/>
              <div className="si2" style={{alignItems:"flex-end"}}><span>✅ Cochés</span><strong style={{color:accent}}>{checkedCount}/{totalItems}</strong></div>
              <div className="si2" style={{alignItems:"flex-end"}}><span>🛒 Produits</span><strong style={{color:"#0ea5e9"}}>{allProds.length}</strong></div>
              {totalEst>0&&<div className="si2" style={{alignItems:"flex-end"}}><span>💰 Estimation</span><strong style={{color:"#059669"}}>{totalEst.toFixed(2)} €</strong></div>}
            </div>

            {/* Progress */}
            <div className="no-print" style={{marginBottom:15}}>
              <div className="progbar"><div className="progfill" style={{width:`${totalItems?(checkedCount/totalItems)*100:0}%`}}/></div>
              <div style={{fontSize:12,color:"var(--sub)",marginTop:5,textAlign:"right"}}>{totalItems?Math.round((checkedCount/totalItems)*100):0}% complété</div>
            </div>

            {/* Plan preview */}
            {plan&&(
              <>
                <div style={{display:"flex",justifyContent:"center",marginBottom:14}} className="no-print">
                  <div style={{background:"var(--card)",border:"1.5px solid var(--bd)",borderRadius:12,padding:15,display:"inline-flex",flexDirection:"column",alignItems:"center",gap:7}}>
                    <PoolSvg plan={POOL_PLANS.find(p=>p.id===plan)} size={165}/>
                    <div style={{fontSize:12,fontWeight:600,color:accent}}>{POOL_PLANS.find(p=>p.id===plan)?.label}</div>
                  </div>
                </div>
                <div style={{display:"none",textAlign:"center",marginBottom:10}} className="p-plan">
                  <PoolSvg plan={POOL_PLANS.find(p=>p.id===plan)} size={105}/>
                  <div style={{fontSize:9}}>{POOL_PLANS.find(p=>p.id===plan)?.label}</div>
                </div>
              </>
            )}

            {/* SECTIONS */}
            {sections.map((sec,si)=>(
              <SectionBlock key={si} sec={sec} si={si} checked={checked} notes={notes} toggle={toggle} setNote={setNote} accent={accent}
                linkedProducts={linkedProducts} onAddProducts={addProducts} onRemoveProduct={removeProduct}/>
            ))}

            {/* RÉCAP MATÉRIAUX */}
            {allProds.length>0&&(
              <div className="section" style={{marginTop:8}}>
                <div className="section-header">
                  <h3>🛒 Récapitulatif matériaux & produits liés</h3>
                  <span className="section-progress">{allProds.length} article(s){totalEst>0?` · ${totalEst.toFixed(2)} €`:""}</span>
                </div>
                <div style={{padding:"6px 0"}}>
                  <table className="mat-tbl">
                    <thead>
                      <tr>
                        <th>Réf.</th><th>Désignation</th><th>Qté</th><th>Unité</th>
                        {totalEst>0&&<><th>P.U.</th><th>Total HT</th></>}
                        <th>Point de contrôle</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allProds.map((p,i)=>(
                        <tr key={i}>
                          <td style={{color:"#6b7a8d",fontSize:11,fontFamily:"monospace"}}>{p.ref||"—"}</td>
                          <td style={{fontWeight:500}}>{p.name}</td>
                          <td style={{textAlign:"center"}}>{p.qty}</td>
                          <td>{p.unit||"pc"}</td>
                          {totalEst>0&&<>
                            <td style={{textAlign:"right"}}>{p.price>0?`${p.price.toFixed(2)} €`:"—"}</td>
                            <td style={{textAlign:"right",fontWeight:600}}>{p.price>0?`${(p.price*(p.qty||1)).toFixed(2)} €`:"—"}</td>
                          </>}
                          <td style={{fontSize:11,color:"#6b7a8d",maxWidth:150,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{p.itemText?.slice(0,50)||""}</td>
                        </tr>
                      ))}
                      {totalEst>0&&(
                        <tr className="mat-tot">
                          <td colSpan={totalEst>0?5:3} style={{textAlign:"right",fontWeight:700}}>Total estimatif HT</td>
                          <td style={{textAlign:"right",fontWeight:700,color:"#059669"}}>{totalEst.toFixed(2)} €</td>
                          <td/>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* SIGNATURE */}
            <div className="section" style={{marginTop:12}}>
              <div className="section-header"><h3>✍️ Signature & validation</h3></div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:28,padding:18}}>
                <div>
                  <div style={{fontSize:12,color:"var(--sub)",marginBottom:42}}>Signature du technicien</div>
                  <div style={{borderTop:"1.5px solid var(--bd)",paddingTop:5,fontSize:12,color:"var(--sub)"}}>Nom & Date</div>
                </div>
                <div>
                  <div style={{fontSize:12,color:"var(--sub)",marginBottom:42}}>Signature du client (bon pour accord)</div>
                  <div style={{borderTop:"1.5px solid var(--bd)",paddingTop:5,fontSize:12,color:"var(--sub)"}}>Nom & Date</div>
                </div>
              </div>
              <div style={{padding:"0 18px 15px"}}>
                <div style={{fontSize:12,color:"var(--sub)",marginBottom:8}}>Remarques générales</div>
                <div style={{height:54,border:"1.5px solid var(--bd)",borderRadius:8,background:"var(--bg)"}}/>
              </div>
            </div>

            <div style={{fontSize:11,color:"var(--sub)",textAlign:"center",marginTop:14}}>
              Lolirine Pool Store · lolirinepoolstore.be · BCE 0650.891.279
            </div>

            {/* ACTIONS */}
            <div className="acts no-print" style={{marginTop:18}}>
              <button className="btn btn-s" onClick={()=>setStep(2)}>← Retour</button>
              <button className="btn btn-s" onClick={()=>{setChecked({});setNotes({});setLinkedProducts({});}}>🔄 Réinitialiser</button>
              <div className="sp"/>
              <button className="btn btn-pr" onClick={()=>window.print()}>🖨️ Imprimer / Télécharger PDF</button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
