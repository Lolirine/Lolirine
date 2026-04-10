/* ─── Pool Plans ─── */
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
                  const {w:W,h:H}=plan;
                  if(plan.shape==="rect") return (
                    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
                      <rect x="15" y="15" width={W} height={H} rx="6" fill={fill} stroke={stroke} strokeWidth={sw}/>
                      {[[15,15],[15+W,15],[15,15+H],[15+W,15+H]].map(([cx,cy],i)=><circle key={i} cx={cx} cy={cy} r="4" fill={stroke}/>)}
                    </svg>);
                  if(plan.shape==="oval") return (
                    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
                      <ellipse cx={15+W/2} cy={15+H/2} rx={W/2} ry={H/2} fill={fill} stroke={stroke} strokeWidth={sw}/>
                    </svg>);
                  if(plan.shape==="kidney") return (
                    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
                      <path d={`M 15,${15+H*.5} C 15,${15+H*.05} ${15+W*.35},15 ${15+W*.5},${15+H*.1} C ${15+W*.72},${15+H*.22} ${15+W},${15+H*.1} ${15+W},${15+H*.5} C ${15+W},${15+H*.88} ${15+W*.72},${15+H} ${15+W*.5},${15+H*.88} C ${15+W*.28},${15+H*.75} ${15+W*.28},${15+H*.55} ${15+W*.15},${15+H*.55} C 15,${15+H*.55} 15,${15+H*.95} 15,${15+H*.5} Z`} fill={fill} stroke={stroke} strokeWidth={sw}/>
                    </svg>);
                  if(plan.shape==="l") return (
                    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
                      <path d={`M 15,15 H ${15+W} V ${15+H*.55} H ${15+W*.55} V ${15+H} H 15 Z`} fill={fill} stroke={stroke} strokeWidth={sw}/>
                    </svg>);
                  if(plan.shape==="spa") return (
                    <svg width={s(W+30)} height={s(H+30)} viewBox={`0 0 ${W+30} ${H+30}`}>
                      <rect x="15" y="15" width={W*.72} height={H} rx="5" fill={fill} stroke={stroke} strokeWidth={sw}/>
                      <rect x={15+W*.76} y={15+H*.2} width={W*.24} height={H*.6} rx="8" fill="rgba(251,191,36,0.2)" stroke="#f59e0b" strokeWidth={sw}/>
                      <text x={15+W*.88} y={15+H*.54} textAnchor="middle" fontSize="8" fill="#92400e" fontFamily="sans-serif">SPA</text>
                    </svg>);
                  return null;
                }

                /* ─── Interventions ─── */
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
                    {section:"💧 Hydraulique",items:["Nombre de bondes de fond : ______","Nombre de skimmers : ______ (1 skimmer / 25 m²)","Nombre de refoulements : ______","Buses de nage (nage à contre-courant)","Buse à balai (prise balai)","Trop-plein / régulateur de niveau","Tuyauterie PVC pression ∅ 50 mm (aspiration)","Tuyauterie PVC pression ∅ 50 mm (refoulement)","Manchons anti-vibratoires sur pompe","Étanchéité traversées de paroi (joints EPDM)","Test pression canalisations avant remblai"]},
                    {section:"🔄 Filtration",items:["Filtre à sable (∅ cuve ______ / débit ______ m³/h)","Filtre à cartouche","Filtre à diatomées","Sable de filtration (granulométrie 0,4–0,8 mm)","Billes de verre (alternative sable)","Pompe (marque / modèle / puissance kW) : ______","Pompe vitesse variable (économie énergie)","Préfiltre / panier préfiltre","Vanne multivoies (6 voies)","Débitmètre","Manomètre","Armoire électrique / coffret de commande"]},
                    {section:"🧪 Traitement de l'eau",items:["Chlore manuel (galets, liquide)","Électrolyseur au sel (concentration sel ______ g/L)","Brome (pastilles / système automatique)","Traitement UV (lampe UV-C)","Ozone (générateur ozone)","PHMB (sans chlore)","Régulation pH automatique","Sonde ORP (potentiel rédox)","Pompe doseuse pH–","Pompe doseuse désinfectant","Analyseur connecté"]},
                    {section:"🌡️ Chauffage",items:["Pompe à chaleur air/eau (puissance ______ kW)","Pompe à chaleur réversible","Échangeur thermique (raccordement chaudière)","Chauffe-eau solaire (capteurs ______ m²)","Résistance électrique (puissance ______ kW)","Couverture solaire à bulles (ép. 400 µ)","Volet roulant isolant","Vanne de by-pass pompe à chaleur"]},
                    {section:"💡 Électricité & éclairage",items:["Projecteurs LED RGB subaquatiques","Spots LED encastrés paroi (niche inox)","Bandeau LED périmétral (plage)","Éclairage escalier submergé","Coffret électrique IP65 dédié piscine","Disjoncteur différentiel 30 mA obligatoire","Liaison équipotentielle (norme NF C 15-100)","Mise à la terre générale","Prise extérieure étanche"]},
                    {section:"🪟 Couverture & sécurité",items:["Volet roulant immergé (lames polycarbonate / alu)","Volet roulant hors-sol","Couverture à barres automatique / manuelle","Filet de protection (normes NF P 90-308)","Alarme piscine OBLIGATOIRE – type : ______","Clôture de protection (h ≥ 1,10 m) + portillon","Signalétique profondeur / interdiction plongée"]},
                    {section:"🏡 Plage, abords & finitions",items:["Margelles (carrelage / pierre naturelle / béton désactivé)","Dallage plage (antidérapant R11 minimum)","Drainage plage (pente 1% minimum)","Caniveau de récupération eaux de plage","Douche solaire / raccordement eau","Lave-pieds","Local technique","Nettoyage de chantier / évacuation gravats","Notice d'utilisation remise au client"]},
                    {section:"🤝 Administratif & SAV",items:["Devis signé + acompte encaissé","Planning prévisionnel remis","Garanties décennale + RC professionnelle","Dossier photos avant / pendant / après","Formation client sur équipements","Contrat d'entretien proposé"]},
                  ],
                  renovation:[
                    {section:"🔍 Diagnostic structure",items:["Fissures structure (fines / traversantes / actives)","Test étanchéité (baisse niveau eau / test colorant)","État du fond (dénivellations, décollements)","État des parois (cloques, éclatement béton)","Corrosion armatures","État des scellements (bondes, skimmers, projecteurs)","Désolidarisation margelles / plage","Tassement / fissures plage"]},
                    {section:"🎨 Revêtement existant",items:["Type de revêtement actuel : ______","Âge du revêtement (années) : ______","Liner : déchirures / décollements / décolorations","Liner : vieillissement, perte de souplesse","Carrelage : joints décollés / cassés / tâchés","Enduit : farinage / effritement / tâches","Membrane armée : décollement / percement","Évaluation : remplacement ou réfection partielle ?"]},
                    {section:"🔧 Hydraulique & filtration existants",items:["Âge de la pompe (années) : ______","Débit pompe mesuré (m³/h) : ______","Bruit / vibrations anormaux pompe","Âge du filtre (années) : ______","Sable à remplacer (> 5 ans)","État vanne multivoies (fuites, jeu)","État des canalisations","Skimmers : panier cassé / joint usé","Trop-plein fonctionnel"]},
                    {section:"⚡ Électricité & éclairage",items:["Coffret électrique conforme (différentiel 30 mA)","Liaison équipotentielle présente et vérifiée","Projecteurs : fonctionnels / étanches","Projecteurs : remplacement LED prévu","Câblage apparent / dégradé","Mise aux normes NF C 15-100 nécessaire"]},
                    {section:"🏗️ Travaux de structure prévus",items:["Ragréage fond et parois","Injection résine anti-fissures","Reprise étanchéité générale","Résine de pontage / primaire d'accrochage","Pose nouveau liner (mesures relevées : ______)","Réfection enduit complet","Recarrelage partiel / complet","Remplacement bondes / skimmers / refoulements","Remplacement niche projecteur","Remplacement margelles","Réfection plage"]},
                    {section:"🆕 Équipements à remplacer / ajouter",items:["Pompe (référence nouvelle : ______)","Filtre à sable (référence nouvelle : ______)","Vanne multivoies","Système de traitement (type : ______)","Pompe à chaleur (référence : ______)","Volet / couverture","Éclairage LED","Robot nettoyeur","Système domotique"]},
                    {section:"🤝 Administratif",items:["Photos état avant travaux","Devis détaillé postes par postes","Planning et durée des travaux","Vidange piscine planifiée","Gestion eaux de vidange (évacuation conforme)","Garanties travaux communiquées"]},
                  ],
                  entretien:[
                    {section:"🧪 Analyse de l'eau",items:["pH (cible 7,2–7,4) → mesuré : ______","TAC (cible 80–120 mg/L) → mesuré : ______","TH – Dureté (cible 150–300 mg/L) → mesuré : ______","Chlore libre (cible 1,0–3,0 mg/L) → mesuré : ______","Chlore combiné (< 0,6 mg/L) → mesuré : ______","Taux de sel si électrolyseur → mesuré : ______","Cyanurate (< 75 mg/L) → mesuré : ______","Phosphates (< 0,1 mg/L) → mesuré : ______","Température eau (°C) : ______","Turbidité (limpide / trouble / verte)"]},
                    {section:"🧹 Nettoyage bassin",items:["Écrémage surface (feuilles, insectes, pollens)","Aspiration fond (manuelle / robot)","Brossage parois et fond","Nettoyage ligne de flottaison","Nettoyage panier(s) skimmer(s)","Nettoyage panier préfiltre pompe","Contre-lavage si pression ≥ 0,5 bar","Nettoyage cartouche filtrante (si applicable)","Rinçage plage / abords","Nettoyage local technique"]},
                    {section:"🔄 Filtration & équipements",items:["Pression manomètre relevée : ______ bar","Débit pompe vérifié","Bruit / vibration anormal pompe","Vérification programmateur / horloge","Vérification vanne multivoies","Vérification électrolyseur (cellule / production)","Vérification pompe doseuse pH","Vérification sonde ORP / pH","Niveau d'eau ajusté (mi-skimmer)","Vérification alarme piscine","Vérification volet / mécanisme"]},
                    {section:"💊 Traitements correctifs",items:["Correction pH (produit / dose) : ______","Correction TAC : ______","Correction TH : ______","Choc chlore (dose) : ______","Algicide préventif appliqué","Floculant / clarifiant appliqué","Anti-phosphates appliqué","Sel ajouté (kg) : ______"]},
                    {section:"📋 Observations & recommandations",items:["Usure liner / revêtement à surveiller","Équipement à remplacer prochainement : ______","Travaux recommandés : ______","Prochain entretien prévu (date) : ______","Produits laissés au client : ______","Bon de visite signé par le client"]},
                  ],
                  hivernage:[
                    {section:"🌊 Préparation de l'eau",items:["Dernière analyse eau complète réalisée","pH ajusté à 7,2–7,4","TAC ajusté (> 120 mg/L recommandé)","Chlore choc appliqué (J-3 minimum)","Algicide hivernal longue durée appliqué","Anti-calcaire hivernal appliqué","Floculant final appliqué","Nettoyage complet bassin","Ligne de flottaison nettoyée"]},
                    {section:"📉 Niveau d'eau & bouchons",items:["Abaissement niveau d'eau (sous le bas des skimmers)","Niveau recommandé : ______ cm sous la margelle","Bouchons hivernage posés dans skimmers","Bouchons posés dans refoulements","Bonde de fond : bouchon / clapet fermé","Flotteurs antigel placés (nombre : ______)","Prise balai bouchonnée"]},
                    {section:"🔌 Arrêt des équipements",items:["Filtration arrêtée","Vidange complète de la pompe","Vidange filtre à sable","Vidange vanne multivoies","Soufflage des canalisations (compresseur)","Arrêt électrolyseur + cellule démontée si gel <-10°C","Arrêt UV / ozone","Arrêt pompes doseuses + vidange","Débranchement programmateur / coffret","Hivernation pompe à chaleur"]},
                    {section:"🧳 Rangement & protection",items:["Robot nettoyeur sorti, rincé, stocké","Équipements de mesure rincés et rangés","Couverture hivernage mise en place (type : ______)","État couverture vérifié","Filet anti-feuilles posé si couverture bulle","Alarme piscine maintenue active"]},
                    {section:"📋 Observations & suivi",items:["Photos état piscine à la fermeture","Date d'hivernage : ______","Date de remise en route prévisionnelle : ______","Remarques particulières : ______","Bon d'intervention signé"]},
                  ],
                  remise_en_route:[
                    {section:"🧹 Réouverture bassin",items:["Retrait couverture hivernage","Retrait filet anti-feuilles","Retrait flotteurs antigel","Retrait bouchons skimmers / refoulements / bonde de fond","Nettoyage fond et parois","Remontée du niveau d'eau (mi-skimmer)","Rinçage plage et abords"]},
                    {section:"🔌 Redémarrage équipements",items:["Remontage pompe (vérification sens rotation)","Amorçage pompe / purge d'air","Remontage vanne multivoies","Mise en marche filtration","Rinçage filtre (contre-lavage + rinçage)","Remontage / reconnexion électrolyseur","Remontage pompes doseuses","Remontage UV / ozone","Redémarrage pompe à chaleur","Vérification programmateur / horloge (heure d'été !)","Test coffret électrique / disjoncteur","Vérification alarme piscine"]},
                    {section:"🧪 Remise en état de l'eau",items:["Analyse eau complète (pH, TAC, TH, chlore, sel)","Correction pH : ______","Correction TAC : ______","Traitement choc (chlore ou oxygène actif)","Algicide curatif si présence d'algues","Floculant / clarifiant","Ajout sel si électrolyseur (quantité : ______ kg)","Filtration continu 24h à 48h minimum","Eau limpide atteinte avant baignade"]},
                    {section:"✅ Contrôle général",items:["Vérification absence de fuite","Vérification projecteurs (étanchéité)","Test robot nettoyeur","Vérification volet roulant / mécanisme","Produits d'entretien réapprovisionnés","Bon d'intervention signé"]},
                  ],
                  materiel:[
                    {section:"🔎 Diagnostic matériel existant",items:["Pompe – marque / modèle actuel : ______","Pompe – puissance (kW) : ______ / âge (ans) : ______","Pompe – panne constatée : ______","Filtre – marque / modèle : ______ / ∅ cuve : ______","Filtre – âge : ______ / état du sable : ______","Vanne multivoies – marque / état : ______","Système de traitement – type : ______ / âge : ______","Électrolyseur – marque / taux de sel actuel : ______","PAC – marque / modèle : ______ / âge : ______","Volet – type / état : ______","Photos du matériel défectueux réalisées"]},
                    {section:"🔄 Remplacement pompe",items:["Débit requis calculé (volume bassin / 4h) : ______ m³/h","Référence nouvelle pompe : ______","Pompe vitesse variable (VEI) recommandée","Raccordements hydrauliques ∅ : ______","Manchons anti-vibratoires neufs","Test de débit après installation"]},
                    {section:"🔄 Remplacement filtre",items:["Diamètre filtre recommandé : ______","Référence nouveau filtre : ______","Type de média filtrant : sable / verre / billes","Quantité de sable / média : ______ kg","Vanne multivoies adaptée","Manomètre neuf posé","Test de contre-lavage effectué"]},
                    {section:"🔄 Remplacement traitement",items:["Électrolyseur – référence : ______ / production Cl/h : ______","Cellule d'électrolyse (seule ou boîtier complet)","Régulation pH automatique – marque : ______","Sondes pH / ORP remplacées","Pompes doseuses – marque / débit : ______","UV – puissance W : ______ / lampe neuve","Analyseur connecté / Wi-Fi : ______"]},
                    {section:"🔄 Remplacement chauffage",items:["Pompe à chaleur – référence : ______ / COP : ______","PAC réversible (climatisation abri incluse)","Vanne de by-pass posée","Test de montée en température bassin"]},
                    {section:"🔄 Remplacement couverture / volet",items:["Type de couverture choisie : ______","Volet roulant immergé – réservation béton vérifiée","Volet roulant hors-sol – emplacement coffre","Couverture à barres – type de motorisation","Lames : polycarbonate / alu / PVC (couleur : ______)","Test motorisation / sécurité anti-pincement"]},
                    {section:"🔄 Remplacement éclairage",items:["Nombre de projecteurs : ______","Type : LED RGB / LED blanc chaud","Niche(s) existante(s) compatibles ou à remplacer","Test d'étanchéité après installation","Programmation RGB / scénarios lumineux"]},
                    {section:"🔄 Robot nettoyeur",items:["Robot fond seul / fond+parois / complet","Référence robot : ______","Alimentation : filaire / sur batterie","Application mobile configurée","Sac / filtre de rechange laissé"]},
                    {section:"🤝 Clôture intervention",items:["Mise en service complète réalisée","Démonstration au client","Ancien matériel évacué","Garantie constructeur enregistrée","Bon d'intervention signé","Facture / attestation TVA réduite si applicable"]},
                  ],
                };

                /* ════════════════════════════════════════════════════════
                   API & utilitaires
                   ════════════════════════════════════════════════════════ */
                const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};

                /* ── Keyword map pour la recherche produits ── */
                const KEYWORD_MAP = [
                  [/bonde.{0,10}fond/i,'bonde fond'],
                  [/skimmer/i,'skimmer'],
                  [/refoulement/i,'buse refoulement'],
                  [/buse.{0,10}balai|prise balai/i,'prise balai'],
                  [/filtre.{0,10}sable/i,'filtre sable'],
                  [/filtre.{0,10}cartouche/i,'filtre cartouche'],
                  [/filtre.{0,10}diatom/i,'filtre diatomées'],
                  [/sable.{0,10}filtration/i,'sable filtration'],
                  [/billes.{0,10}verre/i,'billes verre filtration'],
                  [/pompe.{0,10}vitesse.{0,10}variable|VEI/i,'pompe vitesse variable'],
                  [/pompe.{0,5}chaleur/i,'pompe chaleur piscine'],
                  [/pompe.{0,10}doseuse/i,'pompe doseuse'],
                  [/vanne.{0,10}multivoies/i,'vanne multivoies'],
                  [/électrolyseur|electrolyseur/i,'électrolyseur sel'],
                  [/cellule.{0,10}électro/i,'cellule électrolyse'],
                  [/robot.{0,10}nettoyeur|robot.{0,10}fond/i,'robot piscine'],
                  [/liner/i,'liner piscine'],
                  [/projecteur.{0,10}LED|spot LED/i,'projecteur LED piscine'],
                  [/alarme.{0,10}piscine/i,'alarme piscine'],
                  [/volet.{0,10}roulant/i,'volet roulant piscine'],
                  [/couverture.{0,10}bulle|couverture.{0,10}solaire/i,'couverture solaire piscine'],
                  [/bouchon.{0,10}hivern/i,'bouchon hivernage'],
                  [/flotteur.{0,10}antigel/i,'flotteur antigel piscine'],
                  [/algicide/i,'algicide'],
                  [/chlore.{0,10}choc|choc chlore/i,'chlore choc'],
                  [/galets.{0,10}chlore/i,'galets chlore'],
                  [/pH.{0,5}moins|pH-/i,'pH moins acide'],
                  [/floculant/i,'floculant piscine'],
                  [/anti.{0,5}calcaire/i,'anti calcaire piscine'],
                  [/anti.{0,5}phosphate/i,'anti phosphates piscine'],
                  [/sonde.{0,5}pH|sonde.{0,5}ORP/i,'sonde pH ORP piscine'],
                  [/UV|ultra.{0,5}violet/i,'lampe UV piscine'],
                  [/ozone/i,'générateur ozone piscine'],
                  [/manomètre/i,'manomètre piscine'],
                  [/préfiltre|panier.{0,10}filtre/i,'préfiltre panier pompe'],
                  [/margelles/i,'margelle piscine'],
                  [/douche.{0,10}solaire/i,'douche solaire'],
                  [/échelle|escalier.{0,10}inox/i,'escalier inox piscine'],
                ];

                function extractKeywords(itemText) {
                  const clean = itemText.replace(/_{2,}/g,'').replace(/\(.*?\)/g,'').trim();
                  for(const [pat,kw] of KEYWORD_MAP) { if(pat.test(clean)) return kw; }
                  return clean.replace(/[:()\[\]0-9]/g,' ').split(/\s+/).filter(w=>w.length>3).slice(0,4).join(' ');
                }

                function sortBySupplier(products) {
                  return [...products].sort((a,b)=>{
                    const aH=(a.suppliers||[]).some(s=>s.type==='fluidra'||s.type==='scp');
                    const bH=(b.suppliers||[]).some(s=>s.type==='fluidra'||s.type==='scp');
                    return aH&&!bH?-1:!aH&&bH?1:0;
                  });
                }

                async function apiPost(url, params={}) {
                  const res = await fetch(url, {
                    method:'POST', credentials:'same-origin',
                    headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params})
                  });
                  const d = await res.json();
                  return d?.result;
                }

                async function searchOdooProducts(query, supplier=null) {
                  try {
                    const r = await apiPost(cfg.productsEndpoint||'/pool-checklist/products',{query,limit:24,supplier});
                    const prods = r?.products||[];
                    if(prods.length) return {source:'odoo', products:sortBySupplier(prods)};
                    return null;
                  } catch(e) { console.warn('products:', e); return null; }
                }

                async function suggestViaAI(itemText, sectionLabel) {
                  try {
                    const res = await fetch('https://api.anthropic.com/v1/messages',{
                      method:'POST', headers:{'Content-Type':'application/json'},
                      body:JSON.stringify({
                        model:'claude-sonnet-4-20250514',max_tokens:900,
                        system:`Expert équipements piscine (Lolirine Pool Store, Belgique). JSON uniquement sans markdown :
{"products":[{"ref":"","name":"Nom produit précis","category":"Cat","unit":"pièce|kg|L|m|m²|lot","note":"","supplier":"Fluidra|SCP|HTH|BWT|Hayward|Pentair|Zodiac|Astralpool"}]}
Max 8 produits. Priorité aux produits Fluidra/SIBO et SCP Bénélux.`,
                        messages:[{role:'user',content:`Section : ${sectionLabel}\nPoint : "${itemText}"\nProduits à prévoir ?`}]
                      })
                    });
                    if(!res.ok) return null;
                    const d = await res.json();
                    const parsed = JSON.parse((d.content?.[0]?.text||'{}').replace(/```json|```/g,'').trim());
                    const prods = (parsed.products||[]).map(p=>({...p,
                      suppliers: p.supplier?[{name:p.supplier,ref:p.ref||'',price:0,
                        type:/fluidra|sibo/i.test(p.supplier)?'fluidra':/scp/i.test(p.supplier)?'scp':'other'}]:[]
                    }));
                    return {source:'ai', products:sortBySupplier(prods)};
                  } catch(e) { console.warn('AI:', e); return null; }
                }

                async function searchPartners(query) {
                  try {
                    const r = await apiPost(cfg.partnersEndpoint||'/pool-checklist/partners',{query});
                    return r?.partners||[];
                  } catch(e) { return []; }
                }

                /* Auto-save localStorage */
                const LS_KEY = 'lpc_draft_v2';
                function lsSave(data) {
                  try { localStorage.setItem(LS_KEY, JSON.stringify({...data, _ts: Date.now()})); } catch(e){}
                }
                function lsLoad() {
                  try { return JSON.parse(localStorage.getItem(LS_KEY)||'null'); } catch(e){ return null; }
                }

                function lsClear() { try { localStorage.removeItem(LS_KEY); } catch(e){} }

                /* ── Statuts des points de contrôle ── */
                const STATUS_CONFIG = {
                  pending: {icon:'⬜', label:'Non vérifié',   bg:'transparent', color:'#6b7a8d'},
                  ok:      {icon:'✅', label:'Conforme',       bg:'#dcfce7',     color:'#166534'},
                  warn:    {icon:'⚠️', label:'À surveiller',  bg:'#fef3c7',     color:'#92400e'},
                  action:  {icon:'❌', label:'Action requise', bg:'#fee2e2',     color:'#991b1b'},
                };

                /* ════════════════════════════════════════════════════════
                   Composants UI réutilisables
                   ════════════════════════════════════════════════════════ */

                function SupplierBadge({type, name}) {
                  const C={fluidra:{bg:'#dbeafe',color:'#1d4ed8',label:'Fluidra/SIBO'},
                           scp:{bg:'#dcfce7',color:'#166534',label:'SCP Bénélux'},
                           other:{bg:'#f3f4f6',color:'#6b7a8d',label:name}};
                  const c=C[type]||C.other;
                  return <span style={{background:c.bg,color:c.color,borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:700}}>{c.label}</span>;
                }

                /* ── ImageZoom ── */
                function ImageZoom({src, name, onClose}) {
                  return (
                    <div onClick={onClose} style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.92)',zIndex:99999,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:24,cursor:'zoom-out'}}>
                      <img src={src} alt={name} style={{maxWidth:'88vw',maxHeight:'78vh',objectFit:'contain',borderRadius:14,background:'#fff',padding:16,boxShadow:'0 24px 80px rgba(0,0,0,.6)'}}/>
                      <div style={{color:'rgba(255,255,255,.9)',marginTop:18,fontSize:16,fontWeight:700,textAlign:'center'}}>{name}</div>
                      <div style={{color:'rgba(255,255,255,.4)',marginTop:6,fontSize:12}}>Cliquer pour fermer</div>
                    </div>
                  );
                }

                /* ── Signature Canvas ── */
                function SignatureCanvas({label, onSave}) {
                  const canvasRef = React.useRef(null);
                  const drawing = React.useRef(false);
                  const [hasContent, setHasContent] = React.useState(false);

                  const getPos = (e, canvas) => {
                    const rect = canvas.getBoundingClientRect();
                    const src = e.touches ? e.touches[0] : e;
                    return {x: src.clientX - rect.left, y: src.clientY - rect.top};
                  };

                  const start = (e) => {
                    e.preventDefault();
                    const canvas = canvasRef.current;
                    const ctx = canvas.getContext('2d');
                    const {x,y} = getPos(e, canvas);
                    ctx.beginPath(); ctx.moveTo(x,y);
                    drawing.current = true;
                  };
                  const draw = (e) => {
                    if(!drawing.current) return;
                    e.preventDefault();
                    const canvas = canvasRef.current;
                    const ctx = canvas.getContext('2d');
                    const {x,y} = getPos(e, canvas);
                    ctx.lineWidth=2.5; ctx.lineCap='round'; ctx.strokeStyle='#1a2332';
                    ctx.lineTo(x,y); ctx.stroke();
                    setHasContent(true);
                  };
                  const end = () => { drawing.current = false; };
                  const clear = () => {
                    const canvas = canvasRef.current;
                    canvas.getContext('2d').clearRect(0,0,canvas.width,canvas.height);
                    setHasContent(false); onSave(null);
                  };
                  const save = () => {
                    if(!hasContent) return;
                    onSave(canvasRef.current.toDataURL('image/png'));
                  };

                  return (
                    <div style={{display:'flex',flexDirection:'column',gap:8}}>
                      <div style={{fontSize:12,color:'#6b7a8d',fontWeight:600}}>{label}</div>
                      <canvas ref={canvasRef} width={320} height={120}
                        style={{border:'1.5px solid #dde4ed',borderRadius:8,background:'#fafafa',touchAction:'none',cursor:'crosshair',width:'100%'}}
                        onMouseDown={start} onMouseMove={draw} onMouseUp={end} onMouseLeave={end}
                        onTouchStart={start} onTouchMove={draw} onTouchEnd={end}/>
                      <div style={{display:'flex',gap:6}}>
                        <button onClick={clear} style={{background:'none',border:'1px solid #dde4ed',borderRadius:6,padding:'4px 10px',fontSize:12,cursor:'pointer',color:'#6b7a8d'}}>🗑️ Effacer</button>
                        {hasContent && <button onClick={save} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:6,padding:'4px 12px',fontSize:12,cursor:'pointer',fontWeight:600}}>✓ Valider signature</button>}
                      </div>
                    </div>
                  );
                }

                function SuggDropdown({suggestions, onSelect}) {
                  return (
                    <div style={{position:'absolute',top:'100%',left:0,right:0,background:'#fff',
                      border:'1.5px solid #dde4ed',borderRadius:8,
                      boxShadow:'0 8px 24px rgba(0,0,0,.12)',zIndex:2000,maxHeight:220,overflowY:'auto'}}>
                      {suggestions.map((p,i)=>(
                        <div key={i} onMouseDown={()=>onSelect(p)}
                          style={{padding:'9px 12px',fontSize:13,cursor:'pointer',
                            borderBottom:'1px solid #f0f4f8',display:'flex',gap:10,alignItems:'flex-start'}}
                          onMouseOver={e=>e.currentTarget.style.background='#f0f9ff'}
                          onMouseOut={e=>e.currentTarget.style.background='#fff'}>
                          <span style={{fontSize:18,flexShrink:0}}>👤</span>
                          <div>
                            <div style={{fontWeight:700,color:'#1a2332'}}>{p.name}</div>
                            {p.street && <div style={{fontSize:11,color:'#6b7a8d',marginTop:1}}>{p.street}, {p.zip} {p.city}</div>}
                            {(p.phone||p.mobile) && <div style={{fontSize:11,color:'#6b7a8d'}}>📞 {p.phone||p.mobile}</div>}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                }

                /* ── Autocomplete adresse (Google Places avec split rue/cp/ville/pays) ── */
                function AddressAutocomplete({valueRue, valueCp, valueVille, valuePays, onChangeFull, placeholder, inputStyle}) {
                  const inputRef = React.useRef(null);
                  const [localVal, setLocalVal] = React.useState(valueRue||'');
                  const [ready, setReady] = React.useState(false);

                  React.useEffect(()=>{
                    setLocalVal(valueRue||'');
                  },[valueRue]);

                  React.useEffect(()=>{
                    const initAC = () => {
                      if(!inputRef.current || !window.google?.maps?.places) return;
                      const ac = new window.google.maps.places.Autocomplete(inputRef.current, {
                        types:['address'],
                        componentRestrictions:{country:['be','fr','lu','nl','de']},
                        fields:['address_components','formatted_address'],
                      });
                      ac.addListener('place_changed', ()=>{
                        const place = ac.getPlace();
                        if(!place.address_components) return;
                        const get = (types) => {
                          const c = place.address_components.find(c=>types.some(t=>c.types.includes(t)));
                          return c ? c.long_name : '';
                        };
                        const streetNum = get(['street_number']);
                        const route     = get(['route']);
                        const rue       = [route, streetNum].filter(Boolean).join(' ');
                        const cp        = get(['postal_code']);
                        const ville     = get(['locality','postal_town','sublocality']);
                        const pays      = get(['country']);
                        onChangeFull({ rue, cp, ville, pays });
                        setLocalVal(rue);
                      });
                      setReady(true);
                    };
                    if(window.GOOGLE_PLACES_READY) { initAC(); }
                    else {
                      document.addEventListener('googlePlacesReady', initAC, {once:true});
                      // Retry si déjà chargé mais événement manqué
                      setTimeout(()=>{ if(window.google?.maps?.places) initAC(); }, 1000);
                    }
                    return ()=>{ document.removeEventListener('googlePlacesReady', initAC); };
                  },[]);

                  return (
                    <div style={{display:'contents'}}>
                      <div className="lpc-fg full">
                        <label>Rue <span className="lpc-required">*</span></label>
                        <input ref={inputRef} value={localVal}
                          onChange={e=>{ setLocalVal(e.target.value); onChangeFull({rue:e.target.value,cp:valueCp,ville:valueVille,pays:valuePays}); }}
                          placeholder="Rue de la Piscine 12"
                          style={inputStyle}/>
                        {!ready && (
                          <div style={{fontSize:11,color:'#9ca3af',marginTop:3}}>
                            💡 Tapez l'adresse — autocomplétion Google Places
                          </div>
                        )}
                      </div>
                      <div className="lpc-fg">
                        <label>Code postal</label>
                        <input value={valueCp}
                          onChange={e=>onChangeFull({rue:localVal,cp:e.target.value,ville:valueVille,pays:valuePays})}
                          placeholder="5000" style={inputStyle}/>
                      </div>
                      <div className="lpc-fg">
                        <label>Ville</label>
                        <input value={valueVille}
                          onChange={e=>onChangeFull({rue:localVal,cp:valueCp,ville:e.target.value,pays:valuePays})}
                          placeholder="Namur" style={inputStyle}/>
                      </div>
                      <div className="lpc-fg full">
                        <label>Pays</label>
                        <select value={valuePays}
                          onChange={e=>onChangeFull({rue:localVal,cp:valueCp,ville:valueVille,pays:e.target.value})}
                          style={{...inputStyle,cursor:'pointer'}}>
                          {['Belgique','France','Luxembourg','Pays-Bas','Allemagne','Suisse'].map(p=>(
                            <option key={p} value={p}>{p}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  );
                }

                /* ── Modal historique des fiches ── */
                function HistoryModal({onLoad, onClose}) {
                  const [reports, setReports] = React.useState([]);
                  const [loading, setLoading] = React.useState(true);

                  React.useEffect(()=>{
                    apiPost(cfg.listEndpoint||'/pool-checklist/list',{limit:30})
                      .then(r=>{ setReports(r?.reports||[]); setLoading(false); });
                  },[]);

                  const intColors = {construction:'#0ea5e9',renovation:'#f59e0b',entretien:'#10b981',
                    hivernage:'#6366f1',remise_en_route:'#f97316',materiel:'#ec4899'};

                  return (
                    <div style={{position:'fixed',inset:0,background:'rgba(10,20,40,0.65)',zIndex:9999,display:'flex',alignItems:'center',justifyContent:'center',padding:16}}>
                      <div style={{background:'#f0f4f8',borderRadius:20,width:'100%',maxWidth:720,maxHeight:'85vh',display:'flex',flexDirection:'column',boxShadow:'0 24px 80px rgba(0,0,0,.3)',overflow:'hidden'}}>
                        <div style={{padding:'16px 22px',borderBottom:'1.5px solid #dde4ed',background:'#fff',display:'flex',alignItems:'center',gap:12}}>
                          <div style={{flex:1,fontWeight:700,fontSize:16}}>📋 Fiches de visite sauvegardées</div>
                          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:8,padding:'5px 13px',cursor:'pointer',fontSize:14,color:'#6b7a8d'}}>✕</button>
                        </div>
                        <div style={{flex:1,overflowY:'auto',padding:16}}>
                          {loading && <div style={{textAlign:'center',padding:40,color:'#6b7a8d',fontSize:28}}>🔄</div>}
                          {!loading && reports.length===0 && <div style={{textAlign:'center',padding:40,color:'#6b7a8d'}}>Aucune fiche sauvegardée</div>}
                          {reports.map(r=>(
                            <div key={r.id} onClick={()=>onLoad(r.id)}
                              style={{background:'#fff',borderRadius:12,padding:'13px 16px',marginBottom:8,cursor:'pointer',border:'1.5px solid #dde4ed',transition:'all .15s',display:'flex',gap:12,alignItems:'center'}}
                              onMouseOver={e=>e.currentTarget.style.borderColor='#0ea5e9'}
                              onMouseOut={e=>e.currentTarget.style.borderColor='#dde4ed'}>
                              <div style={{width:10,height:10,borderRadius:'50%',background:intColors[r.intervention_type]||'#6b7a8d',flexShrink:0}}/>
                              <div style={{flex:1,minWidth:0}}>
                                <div style={{fontWeight:700,fontSize:13}}>{r.partner_name||'Sans nom'}</div>
                                <div style={{fontSize:11,color:'#6b7a8d',marginTop:2}}>{r.name} · {r.date} · {r.intervention_type}</div>
                              </div>
                              <div style={{textAlign:'right',flexShrink:0}}>
                                <div style={{fontSize:11,fontWeight:700,color:r.state==='done'?'#059669':'#f59e0b',background:r.state==='done'?'#dcfce7':'#fef3c7',padding:'2px 8px',borderRadius:10}}>
                                  {r.state==='done'?'✅ Validée':'📝 Brouillon'}
                                </div>
                                {r.completion_pct>0 && <div style={{fontSize:11,color:'#6b7a8d',marginTop:3}}>{r.completion_pct}% complété</div>}
                                {r.items_action>0 && <div style={{fontSize:11,color:'#ef4444',fontWeight:600}}>⚠️ {r.items_action} action(s)</div>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                }

                /* ════════════════════════════════════════════════════════
                   ProductPanel (version complète)
                   ════════════════════════════════════════════════════════ */
                function ProductPanel({itemText, sectionLabel, onAdd, onClose}) {
                  const autoKw = React.useMemo(()=>extractKeywords(itemText),[itemText]);
                  const [q,setQ]            = React.useState(autoKw);
                  const [allResults,setAll] = React.useState([]);
                  const [loading,setLoading]= React.useState(false);
                  const [source,setSource]  = React.useState(null);
                  const [tab,setTab]        = React.useState('all');
                  const [sel,setSel]        = React.useState({});
                  const [qtys,setQtys]      = React.useState({});
                  const [zoom,setZoom]      = React.useState(null);
                  const [openCats,setOpenCats] = React.useState({});   // catégories ouvertes

                  const search = async(query) => {
                    if(!query.trim()) return;
                    setLoading(true); setAll([]); setSource(null); setSel({}); setQtys({});
                    try {
                      let r = await searchOdooProducts(query);
                      if(!r) r = await suggestViaAI(itemText, sectionLabel);
                      const prods = r?.products||[];
                      setAll(prods); setSource(r?.source||null);
                      // Ouvrir auto la 1ère catégorie avec fournisseur
                      const firstWithSupplier = prods.find(p=>(p.suppliers||[]).some(s=>s.type==='fluidra'||s.type==='scp'));
                      if(firstWithSupplier) {
                        setOpenCats({[firstWithSupplier.category||'Général']:true});
                      }
                    } catch(e) { setAll([]); }
                    setLoading(false);
                  };

                  React.useEffect(()=>{ search(autoKw); },[]);

                  // Filtrage par onglet fournisseur
                  const results = React.useMemo(()=>{
                    if(tab==='all') return allResults;
                    return allResults.filter(p=>(p.suppliers||[]).some(s=>s.type===tab));
                  },[allResults,tab]);

                  // Comptages
                  const counts = React.useMemo(()=>({
                    all:     allResults.length,
                    fluidra: allResults.filter(p=>(p.suppliers||[]).some(s=>s.type==='fluidra')).length,
                    scp:     allResults.filter(p=>(p.suppliers||[]).some(s=>s.type==='scp')).length,
                  }),[allResults]);

                  // Groupement par catégorie — fournisseurs connus en premier dans chaque groupe
                  const grouped = React.useMemo(()=>{
                    const groups = {};
                    results.forEach(p=>{
                      const cat = p.category||'Général';
                      if(!groups[cat]) groups[cat] = {withSupplier:[], other:[]};
                      const hasS = (p.suppliers||[]).some(s=>s.type==='fluidra'||s.type==='scp');
                      if(hasS) groups[cat].withSupplier.push(p);
                      else      groups[cat].other.push(p);
                    });
                    // Trier les catégories : celles avec fournisseurs connus en tête
                    return Object.entries(groups).sort(([,a],[,b])=>
                      b.withSupplier.length - a.withSupplier.length
                    );
                  },[results]);

                  const toggleCat = (cat) => setOpenCats(p=>({...p,[cat]:!p[cat]}));
                  const toggle    = (uid) => setSel(p=>({...p,[uid]:!p[uid]}));
                  const setQty    = (uid,v) => setQtys(p=>({...p,[uid]:v}));
                  const selCount  = Object.values(sel).filter(Boolean).length;

                  // uid unique = index global
                  const productUid = (p) => `${p.id||p.name}_${p.ref||''}`;

                  const confirm = () => {
                    const added = results
                      .filter(p=>sel[productUid(p)])
                      .map(p=>({...p, qty:Number(qtys[productUid(p)]||1)}));
                    onAdd(added);
                    onClose();
                  };

                  const TAB_S = (active,color='#0ea5e9')=>({
                    padding:'7px 14px', border:'none', cursor:'pointer', fontFamily:'inherit',
                    fontSize:13, fontWeight:600, background:'transparent',
                    borderBottom:`3px solid ${active?color:'transparent'}`,
                    color:active?color:'#6b7a8d', transition:'all .15s', whiteSpace:'nowrap',
                  });

                  // Composant ligne produit (liste déroulante)
                  const ProductRow = ({p, uid}) => {
                    const hasS  = (p.suppliers||[]).some(s=>s.type==='fluidra'||s.type==='scp');
                    const mainS = (p.suppliers||[]).find(s=>s.type!=='other')||(p.suppliers||[])[0];
                    const isSelected = !!sel[uid];
                    return (
                      <div onClick={()=>toggle(uid)}
                        style={{display:'flex',gap:0,borderRadius:10,overflow:'hidden',
                          border:`2px solid ${isSelected?'#0ea5e9':hasS?'#bfdbfe':'#e8edf3'}`,
                          background:isSelected?'rgba(14,165,233,0.04)':'#fff',
                          boxShadow:isSelected?'0 4px 14px rgba(14,165,233,.15)':hasS?'0 2px 8px rgba(37,99,235,0.06)':'0 1px 3px rgba(0,0,0,.04)',
                          cursor:'pointer', transition:'all .18s', marginBottom:6}}>

                        {/* Barre couleur fournisseur */}
                        {hasS && <div style={{width:4,flexShrink:0,
                          background:(p.suppliers||[]).find(s=>s.type==='fluidra')?'#1d4ed8':'#16a34a'}}/>}

                        {/* Image */}
                        <div style={{width:80,flexShrink:0,background:'#f8fafc',display:'flex',
                          alignItems:'center',justifyContent:'center',position:'relative',
                          borderRight:'1px solid #f0f4f8',minHeight:72}}>
                          {p.image ? (
                            <>
                              <img src={p.image} alt={p.name}
                                style={{maxWidth:72,maxHeight:64,objectFit:'contain',padding:4}}/>
                              <button onClick={e=>{e.stopPropagation();setZoom({src:p.image,name:p.name});}}
                                style={{position:'absolute',bottom:2,right:2,background:'rgba(0,0,0,.45)',
                                  border:'none',borderRadius:4,padding:'2px 5px',cursor:'pointer',
                                  fontSize:11,color:'#fff',lineHeight:1}}>🔍</button>
                            </>
                          ) : <span style={{fontSize:26,opacity:.25}}>🏊</span>}
                        </div>

                        {/* Infos */}
                        <div style={{flex:1,padding:'9px 12px',display:'flex',flexDirection:'column',gap:4,minWidth:0}}>
                          <div style={{display:'flex',alignItems:'flex-start',gap:8}}>
                            {/* Checkbox */}
                            <div style={{width:19,height:19,border:`2px solid ${isSelected?'#0ea5e9':'#d1d5db'}`,
                              borderRadius:5,background:isSelected?'#0ea5e9':'#fff',
                              display:'grid',placeItems:'center',flexShrink:0,marginTop:2}}>
                              {isSelected&&<span style={{color:'#fff',fontSize:11,fontWeight:800}}>✓</span>}
                            </div>
                            <div style={{flex:1,minWidth:0}}>
                              <div style={{fontWeight:700,fontSize:13,lineHeight:1.3,color:'#1a2332'}}>{p.name}</div>
                              {p.category&&<div style={{fontSize:11,color:'#94a3b8',marginTop:1}}>{p.category}</div>}
                            </div>
                            {p.price>0 && <span style={{fontWeight:700,fontSize:14,color:'#0ea5e9',flexShrink:0,whiteSpace:'nowrap'}}>{p.price.toFixed(2)} €</span>}
                          </div>

                          {/* Refs + fournisseurs */}
                          <div style={{display:'flex',gap:5,flexWrap:'wrap',alignItems:'center'}}>
                            {p.ref&&<span style={{background:'#f0f4f8',padding:'1px 6px',borderRadius:4,
                              fontSize:11,fontFamily:'monospace',color:'#64748b'}}>{p.ref}</span>}
                            {(p.suppliers||[]).map((s,si)=>(
                              <span key={si} style={{display:'inline-flex',gap:4,alignItems:'center'}}>
                                <SupplierBadge type={s.type} name={s.name}/>
                                {s.ref&&<span style={{fontFamily:'monospace',fontSize:11,color:'#64748b'}}>#{s.ref}</span>}
                                {s.price>0&&<span style={{fontSize:11,color:'#059669',fontWeight:700}}>{s.price.toFixed(2)} €</span>}
                              </span>
                            ))}
                          </div>

                          {/* Quantité */}
                          {isSelected&&(
                            <div style={{display:'flex',alignItems:'center',gap:6,marginTop:2}}
                              onClick={e=>e.stopPropagation()}>
                              <span style={{fontSize:12,color:'#6b7a8d',fontWeight:600}}>Qté :</span>
                              <div style={{display:'flex',alignItems:'center',border:'2px solid #0ea5e9',
                                borderRadius:8,overflow:'hidden'}}>
                                <button onClick={e=>{e.stopPropagation();setQty(uid,Math.max(1,Number(qtys[uid]||1)-1));}}
                                  style={{background:'#f0f9ff',border:'none',padding:'3px 9px',cursor:'pointer',
                                    fontSize:14,color:'#0ea5e9',fontWeight:700}}>−</button>
                                <input type="number" min="1" value={qtys[uid]||1}
                                  onChange={e=>setQty(uid,e.target.value)}
                                  style={{width:46,textAlign:'center',border:'none',padding:'3px 4px',
                                    fontSize:13,fontFamily:'inherit',fontWeight:700,outline:'none'}}/>
                                <button onClick={e=>{e.stopPropagation();setQty(uid,Number(qtys[uid]||1)+1);}}
                                  style={{background:'#f0f9ff',border:'none',padding:'3px 9px',cursor:'pointer',
                                    fontSize:14,color:'#0ea5e9',fontWeight:700}}>+</button>
                              </div>
                              <span style={{fontSize:12,color:'#6b7a8d'}}>{p.unit||'pièce(s)'}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  };

                  return (
                    <>
                      {zoom && <ImageZoom src={zoom.src} name={zoom.name} onClose={()=>setZoom(null)}/>}
                      <div style={{position:'fixed',inset:0,background:'rgba(10,20,40,0.65)',zIndex:9999,
                        display:'flex',alignItems:'center',justifyContent:'center',padding:16}}>
                        <div style={{background:'#f0f4f8',borderRadius:20,width:'100%',maxWidth:920,
                          maxHeight:'93vh',display:'flex',flexDirection:'column',
                          boxShadow:'0 28px 90px rgba(0,0,0,.3)',overflow:'hidden'}}>

                          {/* Header */}
                          <div style={{padding:'15px 20px',borderBottom:'1.5px solid #dde4ed',
                            display:'flex',gap:12,alignItems:'flex-start',background:'#fff'}}>
                            <div style={{flex:1}}>
                              <div style={{fontWeight:700,fontSize:15}}>🛒 Lier des produits à ce point</div>
                              <div style={{fontSize:12,color:'#6b7a8d',marginTop:3}}>
                                {itemText.slice(0,90)}{itemText.length>90?'…':''}
                              </div>
                            </div>
                            <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',
                              borderRadius:8,padding:'5px 12px',cursor:'pointer',fontSize:14,color:'#6b7a8d'}}>✕</button>
                          </div>

                          {/* Barre de recherche */}
                          <div style={{padding:'10px 20px',borderBottom:'1px solid #dde4ed',
                            display:'flex',gap:8,background:'#fff'}}>
                            <input value={q} onChange={e=>setQ(e.target.value)}
                              onKeyDown={e=>e.key==='Enter'&&search(q)}
                              placeholder="Nom de produit, référence, marque…"
                              style={{flex:1,border:'2px solid #dde4ed',borderRadius:10,
                                padding:'9px 13px',fontFamily:'inherit',fontSize:14,
                                outline:'none',background:'#f8fafc'}}/>
                            <button onClick={()=>search(q)}
                              style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:10,
                                padding:'9px 20px',fontWeight:700,cursor:'pointer',fontSize:14}}>
                              {loading?'…':'Chercher'}
                            </button>
                          </div>

                          {/* Onglets fournisseurs */}
                          {allResults.length>0&&(
                            <div style={{display:'flex',alignItems:'center',background:'#fff',
                              borderBottom:'1px solid #dde4ed',paddingLeft:20,paddingRight:20,overflowX:'auto'}}>
                              <button style={TAB_S(tab==='all')} onClick={()=>setTab('all')}>
                                Tous <span style={{marginLeft:5,background:tab==='all'?'#0ea5e9':'#f0f4f8',
                                  color:tab==='all'?'#fff':'#6b7a8d',borderRadius:10,padding:'1px 7px',
                                  fontSize:11,fontWeight:700}}>{counts.all}</span>
                              </button>
                              {counts.fluidra>0&&(
                                <button style={TAB_S(tab==='fluidra','#1d4ed8')} onClick={()=>setTab('fluidra')}>
                                  Fluidra / SIBO <span style={{marginLeft:5,background:tab==='fluidra'?'#1d4ed8':'#f0f4f8',
                                    color:tab==='fluidra'?'#fff':'#6b7a8d',borderRadius:10,padding:'1px 7px',
                                    fontSize:11,fontWeight:700}}>{counts.fluidra}</span>
                                </button>
                              )}
                              {counts.scp>0&&(
                                <button style={TAB_S(tab==='scp','#166534')} onClick={()=>setTab('scp')}>
                                  SCP Bénélux <span style={{marginLeft:5,background:tab==='scp'?'#166534':'#f0f4f8',
                                    color:tab==='scp'?'#fff':'#6b7a8d',borderRadius:10,padding:'1px 7px',
                                    fontSize:11,fontWeight:700}}>{counts.scp}</span>
                                </button>
                              )}
                              {source&&<span style={{marginLeft:'auto',fontSize:11,fontWeight:700,
                                padding:'2px 9px',borderRadius:20,
                                background:source==='odoo'?'#dcfce7':'#fef3c7',
                                color:source==='odoo'?'#166534':'#92400e'}}>
                                {source==='odoo'?'✅ Catalogue live':'✨ Suggestions IA'}
                              </span>}
                            </div>
                          )}

                          {/* Résultats groupés par catégorie */}
                          <div style={{flex:1,overflowY:'auto',padding:'12px 20px'}}>
                            {loading&&(
                              <div style={{padding:50,textAlign:'center',color:'#6b7a8d',fontSize:32}}>🔄</div>
                            )}
                            {!loading&&results.length===0&&source&&(
                              <div style={{padding:30,textAlign:'center',color:'#6b7a8d',fontSize:13}}>
                                Aucun résultat. Modifiez la recherche.
                              </div>
                            )}

                            {grouped.map(([cat, {withSupplier, other}])=>{
                              const isOpen = openCats[cat] !== false; // ouvert par défaut
                              const total  = withSupplier.length + other.length;
                              const hasKnownSupplier = withSupplier.length > 0;
                              return (
                                <div key={cat} style={{marginBottom:10}}>
                                  {/* Header catégorie — accordéon */}
                                  <div onClick={()=>toggleCat(cat)}
                                    style={{display:'flex',alignItems:'center',gap:10,
                                      padding:'9px 14px',borderRadius:10,cursor:'pointer',
                                      background: hasKnownSupplier
                                        ? 'linear-gradient(135deg,#eff6ff,#f0fdf4)'
                                        : '#f8fafc',
                                      border:`1.5px solid ${hasKnownSupplier?'#bfdbfe':'#e8edf3'}`,
                                      marginBottom: isOpen?6:0,
                                      transition:'all .15s'}}>
                                    <span style={{fontSize:16}}>{isOpen?'▼':'▶'}</span>
                                    <span style={{fontWeight:700,fontSize:14,flex:1,color:'#1a2332'}}>{cat}</span>
                                    {/* Badges fournisseurs dans ce groupe */}
                                    {withSupplier.length>0&&(
                                      <div style={{display:'flex',gap:5}}>
                                        {withSupplier.some(p=>(p.suppliers||[]).some(s=>s.type==='fluidra'))&&(
                                          <span style={{background:'#dbeafe',color:'#1d4ed8',borderRadius:5,
                                            padding:'2px 7px',fontSize:11,fontWeight:700}}>Fluidra</span>
                                        )}
                                        {withSupplier.some(p=>(p.suppliers||[]).some(s=>s.type==='scp'))&&(
                                          <span style={{background:'#dcfce7',color:'#166534',borderRadius:5,
                                            padding:'2px 7px',fontSize:11,fontWeight:700}}>SCP</span>
                                        )}
                                      </div>
                                    )}
                                    <span style={{fontSize:12,color:'#6b7a8d',background:'#f0f4f8',
                                      padding:'2px 8px',borderRadius:12,fontWeight:600}}>
                                      {total} produit{total>1?'s':''}
                                    </span>
                                  </div>

                                  {/* Produits de la catégorie */}
                                  {isOpen&&(
                                    <div style={{paddingLeft:4}}>
                                      {/* Produits avec fournisseur connu en premier */}
                                      {withSupplier.length>0&&(
                                        <div style={{marginBottom:4}}>
                                          <div style={{fontSize:11,fontWeight:700,color:'#6b7a8d',
                                            textTransform:'uppercase',letterSpacing:'.5px',
                                            padding:'4px 0',marginBottom:4,display:'flex',
                                            alignItems:'center',gap:6}}>
                                            <span style={{width:8,height:8,borderRadius:'50%',
                                              background:'#10b981',display:'inline-block'}}/>
                                            Fournisseurs référencés
                                          </div>
                                          {withSupplier.map(p=>(
                                            <ProductRow key={productUid(p)} p={p} uid={productUid(p)}/>
                                          ))}
                                        </div>
                                      )}
                                      {/* Autres produits */}
                                      {other.length>0&&(
                                        <div>
                                          {withSupplier.length>0&&(
                                            <div style={{fontSize:11,fontWeight:700,color:'#9ca3af',
                                              textTransform:'uppercase',letterSpacing:'.5px',
                                              padding:'4px 0',marginBottom:4,display:'flex',
                                              alignItems:'center',gap:6}}>
                                              <span style={{width:8,height:8,borderRadius:'50%',
                                                background:'#d1d5db',display:'inline-block'}}/>
                                              Autres produits
                                            </div>
                                          )}
                                          {other.map(p=>(
                                            <ProductRow key={productUid(p)} p={p} uid={productUid(p)}/>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>

                          {/* Footer */}
                          <div style={{padding:'12px 20px',borderTop:'1.5px solid #dde4ed',
                            display:'flex',alignItems:'center',gap:10,background:'#fff'}}>
                            <span style={{fontSize:13,color:'#6b7a8d',flex:1}}>
                              {selCount} produit(s) sélectionné(s)
                            </span>
                            <button onClick={onClose}
                              style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:9,
                                padding:'8px 16px',cursor:'pointer',fontFamily:'inherit',
                                fontSize:13,fontWeight:600}}>Annuler</button>
                            <button onClick={confirm} disabled={!selCount}
                              style={{background:selCount?'#0ea5e9':'#d1d5db',color:'#fff',border:'none',
                                borderRadius:9,padding:'8px 20px',fontWeight:700,
                                cursor:selCount?'pointer':'not-allowed',fontFamily:'inherit',fontSize:13}}>
                              ✓ Ajouter à l'intervention
                            </button>
                          </div>
                        </div>
                      </div>
                    </>
                  );
                }


                function SectionBlock({sec,si,statuses,notes,toggle,setStatus,setNote,accent,linkedProducts,photos,onAddProducts,onRemoveProduct,onPhoto}) {
                  const [open,setOpen] = React.useState(true);
                  const [productPanel,setProductPanel] = React.useState(null);
                  const sChecked = sec.items.filter((_,i)=>statuses[`${si}_${i}`]&&statuses[`${si}_${i}`]!=='pending').length;

                  return (
                    <>
                      {productPanel!==null && (
                        <ProductPanel itemText={sec.items[productPanel]} sectionLabel={sec.section}
                          onAdd={prods=>onAddProducts(si,productPanel,prods)} onClose={()=>setProductPanel(null)}/>
                      )}
                      <div className="lpc-section">
                        <div className="lpc-sec-hdr" onClick={()=>setOpen(o=>!o)}>
                          <h3>{sec.section}</h3>
                          <div style={{display:'flex',gap:8,alignItems:'center'}}>
                            <span className="lpc-progress">{sChecked}/{sec.items.length}</span>
                            <span style={{fontSize:12,color:'#6b7a8d'}}>{open?'▲':'▼'}</span>
                          </div>
                        </div>
                        <div className={`lpc-sec-body${open?'':' collapsed'}`}>
                          {sec.items.map((item,idx)=>{
                            const k=`${si}_${idx}`;
                            const status=statuses[k]||'pending';
                            const sc=STATUS_CONFIG[status];
                            const prods=linkedProducts[k]||[];
                            const photo=photos[k]||null;
                            return (
                              <div key={idx}>
                                <div className={`lpc-item${status!=='pending'?' checked':''}`}
                                  style={{background:sc.bg||'transparent',borderLeft:status!=='pending'?`3px solid ${sc.color}`:'3px solid transparent'}}>

                                  {/* Boutons statut */}
                                  <div style={{display:'flex',gap:2,flexShrink:0}} className="no-print">
                                    {Object.entries(STATUS_CONFIG).map(([s,c])=>(
                                      <button key={s} onClick={()=>setStatus(si,idx,s)}
                                        title={c.label}
                                        style={{background:status===s?c.bg:'transparent',border:`1.5px solid ${status===s?c.color:'#e2e8f0'}`,borderRadius:5,padding:'2px 5px',cursor:'pointer',fontSize:14,lineHeight:1,transition:'all .15s'}}>
                                        {c.icon}
                                      </button>
                                    ))}
                                  </div>

                                  {/* Statut print uniquement */}
                                  <span className="print-only" style={{fontSize:13,flexShrink:0}}>{sc.icon}</span>

                                  <span className={`lpc-item-text${status==='ok'?' done':''}`}>{item}</span>

                                  {/* Photo */}
                                  <div className="no-print" style={{flexShrink:0,display:'flex',gap:4,alignItems:'center'}}>
                                    {photo ? (
                                      <img src={photo} alt="photo" onClick={()=>window.open(photo)}
                                        style={{width:32,height:32,objectFit:'cover',borderRadius:4,cursor:'pointer',border:'1.5px solid #dde4ed'}}/>
                                    ) : null}
                                    <label title="Prendre/choisir une photo" style={{cursor:'pointer',fontSize:16,opacity:.5}} onMouseOver={e=>e.currentTarget.style.opacity=1} onMouseOut={e=>e.currentTarget.style.opacity=.5}>
                                      📷
                                      <input type="file" accept="image/*" capture="environment"
                                        style={{display:'none'}}
                                        onChange={e=>{ const f=e.target.files[0]; if(!f) return; const r=new FileReader(); r.onload=ev=>onPhoto(si,idx,ev.target.result); r.readAsDataURL(f); }}/>
                                    </label>
                                  </div>

                                  {/* Caddie produits */}
                                  <button className="lpc-add-btn no-print" title="Lier des produits" onClick={()=>setProductPanel(idx)} style={{'--acc':accent}}>
                                    🛒{prods.length>0&&<span className="lpc-badge">{prods.length}</span>}
                                  </button>
                                  <input className="lpc-note no-print" placeholder="Note…" value={notes[k]||''} onChange={e=>setNote(si,idx,e.target.value)}/>
                                </div>

                                {/* Produits liés */}
                                {prods.length>0 && (
                                  <div className="lpc-linked">
                                    {prods.map((p,pi)=>(
                                      <div key={pi} className="lpc-chip">
                                        <span className="lpc-chip-qty">{p.qty}×</span>
                                        {p.ref&&<span className="lpc-chip-ref">[{p.ref}]</span>}
                                        <span className="lpc-chip-name">{p.name}</span>
                                        {p.price>0&&<span className="lpc-chip-price">{(p.price*(p.qty||1)).toFixed(2)} €</span>}
                                        <button className="lpc-chip-del no-print" onClick={()=>onRemoveProduct(si,idx,pi)}>✕</button>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Photo en print */}
                                {photo && <div className="print-only" style={{padding:'2px 20px 6px 44px'}}><img src={photo} style={{height:60,objectFit:'cover',borderRadius:4}}/></div>}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </>
                  );
                }

                /* ════════════════════════════════════════════════════════
                   Application principale
                   ════════════════════════════════════════════════════════ */
                function PoolChecklist() {
                  const [step,setStep]       = React.useState(0);
                  const [intervention,setInt]= React.useState(null);
                  const [plan,setPlan]       = React.useState(null);
                  const [client,setClient]   = React.useState({
                    prenom:'', nom:'', tel:'',
                    rue:'', cp:'', ville:'', pays:'Belgique',
                    date:new Date().toISOString().slice(0,10),
                    technicien:cfg.userName||'', ref:'', type:'particulier',
                    partner_id:null
                  });
                  const [statuses,setStatuses]       = React.useState({});
                  const [notes,setNotes]             = React.useState({});
                  const [linkedProducts,setLinked]   = React.useState({});
                  const [photos,setPhotos]           = React.useState({});
                  const [sigTech,setSigTech]         = React.useState(null);
                  const [sigClient,setSigClient]     = React.useState(null);
                  const [reportId,setReportId]       = React.useState(null);
                  const [saveStatus,setSaveStatus]   = React.useState(null); // null|'saving'|'saved'|'error'
                  const [showHistory,setShowHistory] = React.useState(false);
                  const [quoteResult,setQuoteResult] = React.useState(null);
                  const [generalNotes,setGeneralNotes]= React.useState('');

                  const intData  = INTERVENTIONS.find(i=>i.id===intervention);
                  const sections = intervention?CHECKLISTS[intervention]:[];
                  const accent   = intData?.color||'#0ea5e9';
                  const totalItems   = sections.reduce((a,s)=>a+s.items.length,0);
                  const okCount      = Object.values(statuses).filter(s=>s==='ok').length;
                  const warnCount    = Object.values(statuses).filter(s=>s==='warn').length;
                  const actionCount  = Object.values(statuses).filter(s=>s==='action').length;
                  const doneCount    = okCount + warnCount + actionCount;
                  const allProds     = Object.entries(linkedProducts).filter(([,a])=>a.length>0).flatMap(([k,a])=>a.map(p=>({...p,_k:k})));
                  const totalEst     = allProds.reduce((a,p)=>a+(p.price||0)*(p.qty||1),0);

                  const setStatus = (si,idx,s) => { const k=`${si}_${idx}`; setStatuses(p=>({...p,[k]:s})); };
                  const setNote   = (si,idx,v) => { const k=`${si}_${idx}`; setNotes(p=>({...p,[k]:v})); };
                  const addProds  = (si,idx,prods) => { const k=`${si}_${idx}`; setLinked(p=>({...p,[k]:[...(p[k]||[]),...prods]})); };
                  const remProd   = (si,idx,pi)    => { const k=`${si}_${idx}`; setLinked(p=>({...p,[k]:(p[k]||[]).filter((_,i)=>i!==pi)})); };
                  const setPhoto  = (si,idx,data)  => { const k=`${si}_${idx}`; setPhotos(p=>({...p,[k]:data})); };

                  /* Auto-save localStorage toutes les 15s */
                  React.useEffect(()=>{
                    if(step < 3) return;
                    const id = setInterval(()=>{
                      lsSave({step,intervention,plan,client,statuses,notes,linkedProducts,generalNotes,reportId});
                    }, 15000);
                    return ()=>clearInterval(id);
                  },[step,intervention,plan,client,statuses,notes,linkedProducts,generalNotes,reportId]);

                  /* Restaurer brouillon au démarrage */
                  React.useEffect(()=>{
                    const draft = lsLoad();
                    if(draft && draft._ts && (Date.now()-draft._ts) < 48*3600*1000) {
                      if(window.confirm('Un brouillon de fiche a été trouvé. Voulez-vous le restaurer ?')) {
                        if(draft.step)         setStep(draft.step);
                        if(draft.intervention) setInt(draft.intervention);
                        if(draft.plan)         setPlan(draft.plan);
                        if(draft.client)       setClient(draft.client);
                        if(draft.statuses)     setStatuses(draft.statuses);
                        if(draft.notes)        setNotes(draft.notes);
                        if(draft.linkedProducts) setLinked(draft.linkedProducts);
                        if(draft.generalNotes) setGeneralNotes(draft.generalNotes);
                        if(draft.reportId)     setReportId(draft.reportId);
                      }
                    }
                  },[]);

                  /* Sauvegarder sur Odoo */
                  const saveToOdoo = async() => {
                    if(!cfg.isLoggedIn) { alert('Veuillez vous connecter pour sauvegarder.'); return; }
                    setSaveStatus('saving');
                    try {
                      const r = await apiPost(cfg.saveEndpoint||'/pool-checklist/save', {
                        report_id:    reportId,
                        nom:          [client.prenom, client.nom].filter(Boolean).join(' '),
                        adresse:      [client.rue, client.cp, client.ville, client.pays].filter(Boolean).join(', '),
                        tel:          client.tel,
                        date:         client.date,
                        ref:          client.ref,
                        technicien:   client.technicien,
                        partner_id:   client.partner_id,
                        intervention, plan,
                        checklist:    statuses,
                        products:     allProds,
                        notes:        generalNotes,
                        signature_technicien: sigTech,
                        signature_client:     sigClient,
                      });
                      if(r?.success) {
                        setReportId(r.report_id);
                        setSaveStatus('saved');
                        lsClear();
                        setTimeout(()=>setSaveStatus(null), 3000);
                      } else { setSaveStatus('error'); }
                    } catch(e) { setSaveStatus('error'); }
                  };

                  /* Charger une fiche depuis l'historique */
                  const loadReport = async(id) => {
                    const r = await apiPost(`${cfg.loadEndpoint||'/pool-checklist/load'}/${id}`, {});
                    if(r?.success) {
                      const d = r.data;
                      setInt(d.intervention); setPlan(d.plan||null);
                      setClient({nom:d.nom||'',adresse:d.adresse||'',tel:d.tel||'',date:d.date||'',ref:d.ref||'',technicien:d.technicien||'',partner_id:d.partner_id||null});
                      setStatuses(d.checklist||{}); setLinked(d.products?Object.fromEntries(d.products.map((p,i)=>[p._k||`_${i}`,[p]])):{}); 
                      setReportId(d.report_id); setGeneralNotes(d.notes||'');
                      setStep(3); setShowHistory(false);
                    }
                  };

                  /* Créer un devis */
                  const createQuote = async() => {
                    if(!allProds.length) { alert('Aucun produit lié à cette fiche.'); return; }
                    setSaveStatus('saving');
                    const r = await apiPost(cfg.quoteEndpoint||'/pool-checklist/create-quote', {
                      report_id: reportId,
                      products:  allProds,
                      client: {...client, nom:[client.prenom,client.nom].filter(Boolean).join(' '), adresse:[client.rue,client.cp,client.ville,client.pays].filter(Boolean).join(', ')},
                    });
                    setSaveStatus(null);
                    if(r?.success) { setQuoteResult(r); }
                    else { alert('Erreur lors de la création du devis : '+(r?.error||'inconnue')); }
                  };

                  /* Réinitialiser */
                  const reset = () => {
                    if(!window.confirm('Réinitialiser la fiche ? Toutes les données non sauvegardées seront perdues.')) return;
                    setStatuses({}); setNotes({}); setLinked({}); setPhotos({});
                    setSigTech(null); setSigClient(null); setReportId(null);
                    setGeneralNotes(''); lsClear();
                  };

                  const STEPS = ["Type d'intervention","Infos client","Plan de bassin","Check-list & produits"];

                  const inputStyle = {
                    border:'2px solid #dde4ed',borderRadius:10,padding:'11px 14px',
                    fontFamily:'inherit',fontSize:15,background:'#eef2f7',
                    color:'#1a2332',transition:'border .2s',width:'100%',outline:'none',
                  };

                  return (
                    <div className="lpc-app">

                      {showHistory && <HistoryModal onLoad={loadReport} onClose={()=>setShowHistory(false)}/>}

                      {/* Header app (caché en print — hero Odoo prend le relais) */}
                      <div className="lpc-hdr no-print">
                        <div className="lpc-logo" style={{background:accent}}>🏊</div>
                        <div><h1>Lolirine Pool Store — Fiche de visite chantier</h1><p>Diagnostic · intervention · produits liés · devis estimatif</p></div>
                        <div style={{marginLeft:'auto',display:'flex',gap:8,flexShrink:0}}>
                          {cfg.isLoggedIn && <button onClick={()=>setShowHistory(true)} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:8,padding:'6px 13px',fontSize:13,color:'#6b7a8d',cursor:'pointer'}}>📋 Historique</button>}
                          {saveStatus==='saving' && <span style={{fontSize:13,color:'#6b7a8d',padding:'6px 0'}}>💾 Sauvegarde…</span>}
                          {saveStatus==='saved'  && <span style={{fontSize:13,color:'#059669',padding:'6px 0'}}>✅ Sauvegardé</span>}
                          {saveStatus==='error'  && <span style={{fontSize:13,color:'#ef4444',padding:'6px 0'}}>❌ Erreur</span>}
                          {reportId && <span style={{fontSize:12,color:'#6b7a8d',padding:'6px 0',border:'1px solid #dde4ed',borderRadius:6,paddingLeft:8,paddingRight:8}}>📄 {reportId}</span>}
                        </div>
                      </div>

                      {/* Stepper */}
                      <div className="lpc-stepper no-print">
                        {STEPS.map((lbl,i)=>(
                          <div key={i} className={`lpc-step${step===i?' active':step>i?' done':''}`} style={{'--acc':accent}}>
                            <div className="lpc-step-num">{step>i?'✓':i+1}</div>
                            <div className="lpc-step-lbl">{lbl}</div>
                          </div>
                        ))}
                      </div>

                      {/* ── STEP 0 : Type d'intervention ── */}
                      {step===0 && (
                        <div>
                          <h2 className="lpc-title">Sélectionner le type d'intervention</h2>
                          <div className="lpc-grid">
                            {INTERVENTIONS.map(iv=>(
                              <div key={iv.id} className={`lpc-card${intervention===iv.id?' sel':''}`}
                                style={{'--acc':iv.color}} onClick={()=>setInt(iv.id)}>
                                <div className="lpc-card-title">{iv.label}</div>
                                <div className="lpc-card-sub">{CHECKLISTS[iv.id].reduce((a,s)=>a+s.items.length,0)} points · {CHECKLISTS[iv.id].length} sections</div>
                              </div>
                            ))}
                          </div>
                          <div className="lpc-acts no-print"><div style={{flex:1}}/>
                            <button className="lpc-btn-p" disabled={!intervention} style={{'--acc':accent}} onClick={()=>setStep(1)}>Suivant →</button>
                          </div>
                        </div>
                      )}

                      {/* ── STEP 1 : Infos client avec autocomplétion ── */}
                      {step===1 && (
                        <div>
                          <h2 className="lpc-title">Informations client &amp; chantier</h2>

                          {/* ── Type de client ── */}
                          <div className="lpc-contact-section">
                            <div className="lpc-contact-header">
                              <span className="lpc-contact-header-icon">👤</span>
                              <span>Vous êtes</span>
                            </div>
                            <div className="lpc-contact-body">
                              <div style={{display:'flex',gap:10,marginBottom:20}}>
                                {[['particulier','👤 Particulier'],['professionnel','🏢 Professionnel']].map(([val,lbl])=>(
                                  <button key={val} onClick={()=>setClient(p=>({...p,type:val}))}
                                    className={`lpc-toggle-btn${(client.type||'particulier')===val?' active':''}`}>
                                    {lbl}
                                  </button>
                                ))}
                              </div>

                              {/* ── Informations de contact ── */}
                              <div className="lpc-sub-header">
                                <span className="lpc-sub-icon">📋</span>
                                <span>Informations de contact</span>
                              </div>

                              {/* Prénom + Nom */}
                              <div className="lpc-form-grid" style={{marginTop:16}}>
                                <ClientAutocomplete
                                  valuePrenom={client.prenom}
                                  valueNom={client.nom}
                                  onChangePrenom={v=>setClient(p=>({...p,prenom:v}))}
                                  onChangeNom={v=>setClient(p=>({...p,nom:v}))}
                                  onSelectPartner={partner=>{
                                    const parts=(partner.name||'').trim().split(' ');
                                    setClient(p=>({...p,
                                      prenom:    parts.length>1?parts[0]:'',
                                      nom:       parts.length>1?parts.slice(1).join(' '):parts[0],
                                      tel:       partner.phone||partner.mobile||p.tel,
                                      rue:       partner.street||p.rue,
                                      cp:        partner.zip||p.cp,
                                      ville:     partner.city||p.ville,
                                      partner_id:partner.id,
                                    }));
                                  }}
                                />
                                {client.partner_id && (
                                  <div className="lpc-fg full">
                                    <div className="lpc-linked-badge">✅ Contact Odoo #{client.partner_id} lié — champs pré-remplis</div>
                                  </div>
                                )}
                                <div className="lpc-fg">
                                  <label>Téléphone <span className="lpc-required">*</span></label>
                                  <input value={client.tel} onChange={e=>setClient(p=>({...p,tel:e.target.value}))}
                                    placeholder="0475/12 34 56" style={inputStyle}/>
                                </div>
                                <div className="lpc-fg">
                                  <label>Date de visite</label>
                                  <input type="date" value={client.date} onChange={e=>setClient(p=>({...p,date:e.target.value}))} style={inputStyle}/>
                                </div>
                              </div>

                              {/* ── Adresse du chantier ── */}
                              <div className="lpc-sub-header" style={{marginTop:24}}>
                                <span className="lpc-sub-icon">📍</span>
                                <span>Adresse du chantier</span>
                              </div>

                              <div className="lpc-form-grid" style={{marginTop:16}}>
                                <AddressAutocomplete
                                  valueRue={client.rue}
                                  valueCp={client.cp}
                                  valueVille={client.ville}
                                  valuePays={client.pays}
                                  onChangeFull={({rue,cp,ville,pays})=>setClient(p=>({
                                    ...p,
                                    rue:  rue  !== undefined ? rue  : p.rue,
                                    cp:   cp   !== undefined ? cp   : p.cp,
                                    ville:ville !== undefined ? ville: p.ville,
                                    pays: pays !== undefined ? pays : p.pays,
                                  }))}
                                  inputStyle={inputStyle}
                                />
                              </div>

                              {/* ── Informations de l'intervention ── */}
                              <div className="lpc-sub-header" style={{marginTop:24}}>
                                <span className="lpc-sub-icon">🔧</span>
                                <span>Informations de l'intervention</span>
                              </div>

                              <div className="lpc-form-grid" style={{marginTop:16}}>
                                <div className="lpc-fg">
                                  <label>Technicien / Commercial</label>
                                  <input value={client.technicien} onChange={e=>setClient(p=>({...p,technicien:e.target.value}))}
                                    placeholder="Prénom NOM" style={inputStyle}/>
                                </div>
                                <div className="lpc-fg">
                                  <label>Référence dossier</label>
                                  <input value={client.ref} onChange={e=>setClient(p=>({...p,ref:e.target.value}))}
                                    placeholder="LPS-2025-001" style={inputStyle}/>
                                </div>
                              </div>
                            </div>
                          </div>

                          <div className="lpc-acts no-print">
                            <button className="lpc-btn-s" onClick={()=>setStep(0)}>← Retour</button>
                            <div style={{flex:1}}/>
                            <button className="lpc-btn-p" style={{'--acc':accent}} onClick={()=>setStep(2)}>Suivant →</button>
                          </div>
                        </div>
                      )}

                      {/* ── STEP 2 : Plan de bassin ── */}
                      {step===2 && (
                        <div>
                          <h2 className="lpc-title">Plan de bassin</h2>
                          <p style={{fontSize:13,color:'#6b7a8d',marginBottom:18}}>Sélectionner la forme correspondante</p>
                          <div className="lpc-grid">
                            {POOL_PLANS.map(p=>(
                              <div key={p.id} className={`lpc-plan-card${plan===p.id?' sel':''}`} style={{'--acc':accent}} onClick={()=>setPlan(p.id)}>
                                <PoolSvg plan={p} size={140}/><div className="lpc-plan-lbl">{p.label}</div>
                              </div>
                            ))}
                          </div>
                          <div className="lpc-acts no-print">
                            <button className="lpc-btn-s" onClick={()=>setStep(1)}>← Retour</button>
                            <div style={{flex:1}}/>
                            <button className="lpc-btn-g" onClick={()=>{setPlan(null);setStep(3);}}>Passer</button>
                            <button className="lpc-btn-p" disabled={!plan} style={{'--acc':accent}} onClick={()=>setStep(3)}>Suivant →</button>
                          </div>
                        </div>
                      )}

                      {/* ── STEP 3 : Checklist ── */}
                      {step===3 && (
                        <div>
                          {/* Print header */}
                          <div className="lpc-print-hdr">
                            <div className="lpc-sumbox" style={{display:'flex'}}>
                              {[["Client",[client.prenom,client.nom].filter(Boolean).join(' ')],["Adresse",[client.rue,client.cp,client.ville,client.pays].filter(Boolean).join(', ')],["Tél",client.tel],["Date",client.date],["Technicien",client.technicien],["Réf.",client.ref],["Intervention",intData?.label]].filter(([,v])=>v).map(([l,v])=>(
                                <div key={l} className="lpc-si2"><span>{l}</span><strong>{v}</strong></div>
                              ))}
                            </div>
                          </div>

                          {/* Barre résumé */}
                          <div className="lpc-sumbox no-print">
                            <div className="lpc-si2"><span>Client</span><strong>{[client.prenom,client.nom].filter(Boolean).join(' ')||'—'}</strong></div>
                            <div className="lpc-si2"><span>Date</span><strong>{client.date}</strong></div>
                            <div className="lpc-si2"><span>Intervention</span><strong style={{color:accent}}>{intData?.label}</strong></div>
                            {plan && <div className="lpc-si2"><span>Plan</span><strong>{POOL_PLANS.find(p=>p.id===plan)?.label}</strong></div>}
                            <div style={{flex:1}}/>
                            <div className="lpc-si2" style={{alignItems:'flex-end'}}><span>✅ OK</span><strong style={{color:'#059669'}}>{okCount}</strong></div>
                            {warnCount>0 && <div className="lpc-si2" style={{alignItems:'flex-end'}}><span>⚠️ Surveiller</span><strong style={{color:'#d97706'}}>{warnCount}</strong></div>}
                            {actionCount>0 && <div className="lpc-si2" style={{alignItems:'flex-end'}}><span>❌ Actions</span><strong style={{color:'#dc2626'}}>{actionCount}</strong></div>}
                            <div className="lpc-si2" style={{alignItems:'flex-end'}}><span>🛒 Produits</span><strong style={{color:'#0ea5e9'}}>{allProds.length}</strong></div>
                            {totalEst>0 && <div className="lpc-si2" style={{alignItems:'flex-end'}}><span>💰 Estimation</span><strong style={{color:'#059669'}}>{totalEst.toFixed(2)} €</strong></div>}
                          </div>

                          {/* Barre de progression */}
                          <div className="no-print" style={{marginBottom:16}}>
                            <div style={{display:'flex',gap:4,height:10,borderRadius:20,overflow:'hidden'}}>
                              <div style={{width:`${totalItems?okCount/totalItems*100:0}%`,background:'#10b981',transition:'width .4s'}}/>
                              <div style={{width:`${totalItems?warnCount/totalItems*100:0}%`,background:'#f59e0b',transition:'width .4s'}}/>
                              <div style={{width:`${totalItems?actionCount/totalItems*100:0}%`,background:'#ef4444',transition:'width .4s'}}/>
                              <div style={{flex:1,background:'#dde4ed'}}/>
                            </div>
                            <div style={{fontSize:12,color:'#6b7a8d',marginTop:5,display:'flex',gap:12}}>
                              <span>✅ {okCount} conformes</span>
                              {warnCount>0 && <span>⚠️ {warnCount} à surveiller</span>}
                              {actionCount>0 && <span style={{color:'#dc2626',fontWeight:600}}>❌ {actionCount} actions requises</span>}
                              <span style={{marginLeft:'auto'}}>{totalItems?Math.round(doneCount/totalItems*100):0}% complété</span>
                            </div>
                          </div>

                          {/* Légende statuts */}
                          <div className="no-print" style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:14,padding:'10px 14px',background:'#fff',borderRadius:10,border:'1px solid #dde4ed',fontSize:12}}>
                            <span style={{fontWeight:700,color:'#6b7a8d',marginRight:4}}>Statuts :</span>
                            {Object.entries(STATUS_CONFIG).map(([s,c])=>(
                              <span key={s} style={{display:'inline-flex',gap:4,alignItems:'center',background:c.bg||'#f0f4f8',padding:'3px 9px',borderRadius:20,color:c.color||'#6b7a8d',fontWeight:600}}>
                                {c.icon} {c.label}
                              </span>
                            ))}
                            <span style={{marginLeft:'auto',color:'#6b7a8d'}}>📷 = photo · 🛒 = produits</span>
                          </div>

                          {/* Plan */}
                          {plan && (<>
                            <div style={{display:'flex',justifyContent:'center',marginBottom:14}} className="no-print">
                              <div style={{background:'#fff',border:'1.5px solid #dde4ed',borderRadius:12,padding:14,display:'inline-flex',flexDirection:'column',alignItems:'center',gap:7}}>
                                <PoolSvg plan={POOL_PLANS.find(p=>p.id===plan)} size={160}/>
                                <div style={{fontSize:12,fontWeight:600,color:accent}}>{POOL_PLANS.find(p=>p.id===plan)?.label}</div>
                              </div>
                            </div>
                            <div className="lpc-print-plan"><PoolSvg plan={POOL_PLANS.find(p=>p.id===plan)} size={100}/><div style={{fontSize:9}}>{POOL_PLANS.find(p=>p.id===plan)?.label}</div></div>
                          </>)}

                          {/* Sections */}
                          {sections.map((sec,si)=>(
                            <SectionBlock key={si} sec={sec} si={si}
                              statuses={statuses} notes={notes} photos={photos}
                              setStatus={setStatus} setNote={setNote}
                              accent={accent}
                              linkedProducts={linkedProducts}
                              onAddProducts={addProds} onRemoveProduct={remProd}
                              onPhoto={setPhoto}/>
                          ))}

                          {/* Récap matériaux */}
                          {allProds.length>0 && (
                            <div className="lpc-section" style={{marginTop:10}}>
                              <div className="lpc-sec-hdr">
                                <h3>🛒 Récapitulatif matériaux &amp; produits liés</h3>
                                <span className="lpc-progress">{allProds.length} article(s){totalEst>0?` · ${totalEst.toFixed(2)} €`:''}</span>
                              </div>
                              <div style={{padding:'6px 0'}}>
                                <table className="lpc-mat-tbl">
                                  <thead><tr><th>Réf.</th><th>Désignation</th><th>Fournisseur</th><th>Qté</th><th>Unité</th>{totalEst>0&&<><th>P.U.</th><th>Total HT</th></>}<th>Point de contrôle</th></tr></thead>
                                  <tbody>
                                    {allProds.map((p,i)=>{
                                      const mainS=(p.suppliers||[]).find(s=>s.type!=='other')||(p.suppliers||[])[0];
                                      return (
                                        <tr key={i}>
                                          <td style={{fontSize:11,fontFamily:'monospace',color:'#6b7a8d'}}>{p.ref||'—'}</td>
                                          <td style={{fontWeight:500}}>{p.name}</td>
                                          <td>{mainS?<SupplierBadge type={mainS.type} name={mainS.name}/>:'—'}</td>
                                          <td style={{textAlign:'center'}}>{p.qty}</td>
                                          <td>{p.unit||'pc'}</td>
                                          {totalEst>0&&<>
                                            <td style={{textAlign:'right'}}>{p.price>0?`${p.price.toFixed(2)} €`:'—'}</td>
                                            <td style={{textAlign:'right',fontWeight:600}}>{p.price>0?`${(p.price*(p.qty||1)).toFixed(2)} €`:'—'}</td>
                                          </>}
                                          <td style={{fontSize:11,color:'#6b7a8d',maxWidth:130,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{p.itemText?.slice(0,45)||''}</td>
                                        </tr>
                                      );
                                    })}
                                    {totalEst>0 && <tr className="lpc-mat-tot">
                                      <td colSpan={totalEst>0?6:4} style={{textAlign:'right',fontWeight:700}}>Total estimatif HT</td>
                                      <td style={{textAlign:'right',fontWeight:700,color:'#059669'}}>{totalEst.toFixed(2)} €</td><td/>
                                    </tr>}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* Résultat devis */}
                          {quoteResult && (
                            <div style={{background:'#f0fdf4',border:'2px solid #10b981',borderRadius:12,padding:'14px 18px',marginTop:10,display:'flex',alignItems:'center',gap:12}}>
                              <span style={{fontSize:24}}>✅</span>
                              <div style={{flex:1}}>
                                <div style={{fontWeight:700,color:'#059669'}}>Devis {quoteResult.order_name} créé avec succès !</div>
                                <div style={{fontSize:13,color:'#047857',marginTop:2}}>{allProds.length} ligne(s) de produits ajoutée(s)</div>
                              </div>
                              <a href={quoteResult.url} target="_blank"
                                style={{background:'#059669',color:'#fff',padding:'8px 16px',borderRadius:8,textDecoration:'none',fontWeight:700,fontSize:13}}>
                                Ouvrir le devis →
                              </a>
                              <button onClick={()=>setQuoteResult(null)} style={{background:'none',border:'none',cursor:'pointer',color:'#6b7a8d',fontSize:16}}>✕</button>
                            </div>
                          )}

                          {/* Notes générales */}
                          <div className="lpc-section" style={{marginTop:10}}>
                            <div className="lpc-sec-hdr"><h3>📝 Remarques générales</h3></div>
                            <div style={{padding:16}}>
                              <textarea value={generalNotes} onChange={e=>setGeneralNotes(e.target.value)}
                                placeholder="Observations générales, conditions d'accès, points particuliers à noter…"
                                style={{width:'100%',minHeight:80,border:'1.5px solid #dde4ed',borderRadius:8,padding:'10px 12px',fontFamily:'inherit',fontSize:14,resize:'vertical',background:'#f8fafc'}}/>
                            </div>
                          </div>

                          {/* Signatures */}
                          <div className="lpc-section" style={{marginTop:10}}>
                            <div className="lpc-sec-hdr"><h3>✍️ Signatures</h3></div>
                            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:24,padding:20}}>
                              <SignatureCanvas label="Signature du technicien" onSave={setSigTech}/>
                              <SignatureCanvas label="Signature du client (bon pour accord)" onSave={setSigClient}/>
                            </div>
                            {(sigTech||sigClient) && (
                              <div style={{padding:'0 20px 16px',display:'flex',gap:12}}>
                                {sigTech && <img src={sigTech} alt="Sig tech" style={{height:50,border:'1px solid #dde4ed',borderRadius:6}}/>}
                                {sigClient && <img src={sigClient} alt="Sig client" style={{height:50,border:'1px solid #dde4ed',borderRadius:6}}/>}
                              </div>
                            )}
                          </div>

                          <div style={{fontSize:11,color:'#6b7a8d',textAlign:'center',marginTop:14}}>
                            Lolirine Pool Store · lolirinepoolstore.be · BCE 0650.891.279
                          </div>

                          {/* Barre d'actions */}
                          <div className="lpc-acts no-print" style={{marginTop:20,flexWrap:'wrap'}}>
                            <button className="lpc-btn-s" onClick={()=>setStep(2)}>← Retour</button>
                            <button className="lpc-btn-s" onClick={reset}>🔄 Réinitialiser</button>
                            <div style={{flex:1}}/>
                            {allProds.length>0 && (
                              <button className="lpc-btn-p" style={{'--acc':'#10b981',background:'#10b981'}} onClick={createQuote}>
                                📋 Créer un devis Odoo
                              </button>
                            )}
                            {cfg.isLoggedIn && (
                              <button className="lpc-btn-p" style={{'--acc':'#6366f1',background:'#6366f1'}} onClick={saveToOdoo}>
                                💾 Sauvegarder
                              </button>
                            )}
                            <button className="lpc-btn-pr" onClick={()=>window.print()}>🖨️ Imprimer / PDF</button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }


                /* ── Client Autocomplete — prénom + nom séparés ── */
                function ClientAutocomplete({valuePrenom, valueNom, onChangePrenom, onChangeNom, onSelectPartner}) {
                  const [suggestions, setSugg] = React.useState([]);
                  const [open, setOpen]         = React.useState(false);
                  const [activeField, setActiveField] = React.useState(null);

                  const fieldStyle = {
                    border:'1.5px solid #e5e7eb',borderRadius:8,padding:'12px 16px',
                    fontFamily:'inherit',fontSize:14,background:'#f9fafb',
                    color:'#1a2332',width:'100%',transition:'all .2s',outline:'none',
                  };

                  const search = async(v, field) => {
                    setActiveField(field);
                    if(v.length >= 2) {
                      const partners = await searchPartners(v);
                      setSugg(partners); setOpen(partners.length > 0);
                    } else { setSugg([]); setOpen(false); }
                  };

                  const selectPartner = (p) => {
                    const parts = (p.name||'').trim().split(' ');
                    const prenom = parts.length > 1 ? parts[0] : '';
                    const nom    = parts.length > 1 ? parts.slice(1).join(' ') : parts[0];
                    onChangePrenom(prenom);
                    onChangeNom(nom);
                    onSelectPartner(p);
                    setSugg([]); setOpen(false);
                  };

                  return (
                    <React.Fragment>
                      <div className="lpc-fg" style={{position:'relative'}}>
                        <label>Prénom <span className="lpc-required">*</span></label>
                        <input value={valuePrenom}
                          onChange={e=>{ onChangePrenom(e.target.value); search(e.target.value,'prenom'); }}
                          onBlur={()=>setTimeout(()=>setOpen(false),200)}
                          placeholder="Jean" style={fieldStyle}/>
                        {open && activeField==='prenom' && suggestions.length>0 && (
                          <SuggDropdown suggestions={suggestions} onSelect={selectPartner}/>
                        )}
                      </div>
                      <div className="lpc-fg" style={{position:'relative'}}>
                        <label>Nom <span className="lpc-required">*</span></label>
                        <input value={valueNom}
                          onChange={e=>{ onChangeNom(e.target.value); search(e.target.value,'nom'); }}
                          onBlur={()=>setTimeout(()=>setOpen(false),200)}
                          placeholder="Dupont" style={fieldStyle}/>
                        {open && activeField==='nom' && suggestions.length>0 && (
                          <SuggDropdown suggestions={suggestions} onSelect={selectPartner}/>
                        )}
                      </div>
                    </React.Fragment>
                  );
                }

                ReactDOM.createRoot(document.getElementById('pool-checklist-root')).render(<PoolChecklist/>);
