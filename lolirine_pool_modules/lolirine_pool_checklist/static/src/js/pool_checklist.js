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

                /* ─── API produits (endpoint Odoo same-origin) ─── */
                const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};

                async function searchOdooProducts(query) {
                  try {
                    const res = await fetch(cfg.productsEndpoint || '/pool-checklist/products', {
                      method:'POST',
                      headers:{'Content-Type':'application/json','X-CSRFToken': cfg.csrfToken||''},
                      credentials:'same-origin',
                      body: JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{query,limit:12}})
                    });
                    const d = await res.json();
                    const prods = d?.result?.products || d?.result || [];
                    if(prods.length) return {source:'odoo', products: prods};
                    return null;
                  } catch(e) {
                    console.warn('[checklist] Odoo search failed:', e);
                    return null;
                  }
                }

                async function suggestViaAI(itemText, sectionLabel) {
                  const res = await fetch('https://api.anthropic.com/v1/messages',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({
                      model:'claude-sonnet-4-20250514',max_tokens:800,
                      system:`Expert équipements piscine (Lolirine Pool Store, Belgique). Liste produits/matériaux concrets. JSON uniquement sans markdown :
{"products":[{"ref":"","name":"Nom","category":"Cat","unit":"pièce|kg|L|m|m²|lot","note":""}]}
Max 7 produits. Marques : Fluidra, Zodiac, Hayward, Pentair, Astralpool, SCP, HTH, BWT.`,
                      messages:[{role:'user',content:`Section : ${sectionLabel}\nPoint : "${itemText}"\nProduits à prévoir ?`}]
                    })
                  });
                  const d = await res.json();
                  const text = d.content?.[0]?.text || '{}';
                  const parsed = JSON.parse(text.replace(/```json|```/g,'').trim());
                  return {source:'ai', products: parsed.products||[]};
                }

                /* ─── ProductPanel ─── */
                function ProductPanel({itemText, sectionLabel, onAdd, onClose}) {
                  const [q,setQ] = React.useState(itemText.replace(/_{3,}/g,'').trim().slice(0,40));
                  const [results,setResults] = React.useState([]);
                  const [loading,setLoading] = React.useState(false);
                  const [source,setSource] = React.useState(null);
                  const [sel,setSel] = React.useState({});
                  const [qtys,setQtys] = React.useState({});

                  const search = async(query) => {
                    if(!query.trim()) return;
                    setLoading(true); setResults([]); setSource(null);
                    let r = await searchOdooProducts(query);
                    if(!r) r = await suggestViaAI(itemText, sectionLabel);
                    setResults(r?.products||[]); setSource(r?.source||null); setLoading(false);
                  };

                  React.useEffect(()=>{ search(q); },[]);

                  const toggle = i => setSel(p=>({...p,[i]:!p[i]}));
                  const setQty = (i,v) => setQtys(p=>({...p,[i]:v}));
                  const selCount = Object.values(sel).filter(Boolean).length;
                  const confirm = () => {
                    onAdd(results.filter((_,i)=>sel[i]).map((p,i)=>({...p,qty:Number(qtys[i]||1)})));
                    onClose();
                  };

                  return (
                    <div style={{position:'fixed',inset:0,background:'rgba(10,20,40,0.55)',zIndex:9999,display:'flex',alignItems:'center',justifyContent:'center',padding:16}}>
                      <div style={{background:'#fff',borderRadius:18,width:'100%',maxWidth:660,maxHeight:'88vh',display:'flex',flexDirection:'column',boxShadow:'0 24px 80px rgba(0,0,0,0.25)',overflow:'hidden'}}>
                        <div style={{padding:'15px 20px',borderBottom:'1.5px solid #dde4ed',display:'flex',gap:12,alignItems:'flex-start'}}>
                          <div style={{flex:1}}>
                            <div style={{fontWeight:700,fontSize:15}}>🛒 Lier des produits à ce point</div>
                            <div style={{fontSize:12,color:'#6b7a8d',marginTop:3}}>{itemText.slice(0,90)}{itemText.length>90?'…':''}</div>
                          </div>
                          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:8,padding:'5px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d'}}>✕</button>
                        </div>
                        <div style={{padding:'10px 20px',borderBottom:'1px solid #f0f4f8',display:'flex',gap:8}}>
                          <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==='Enter'&&search(q)}
                            placeholder="Nom de produit, référence, marque…"
                            style={{flex:1,border:'1.5px solid #dde4ed',borderRadius:9,padding:'8px 13px',fontFamily:'inherit',fontSize:14,outline:'none'}}/>
                          <button onClick={()=>search(q)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'8px 18px',fontWeight:600,cursor:'pointer',fontSize:13}}>{loading?'…':'Chercher'}</button>
                        </div>
                        {source && <div style={{padding:'5px 20px',background:source==='odoo'?'#f0fdf4':'#fffbeb',borderBottom:'1px solid #f0f4f8'}}>
                          <span style={{fontSize:11,fontWeight:600,padding:'2px 9px',borderRadius:20,background:source==='odoo'?'#dcfce7':'#fef3c7',color:source==='odoo'?'#166534':'#92400e'}}>
                            {source==='odoo'?'✅ Catalogue Lolirine Pool Store (données live)':'✨ Suggestions IA (catalogue non accessible en direct)'}
                          </span>
                        </div>}
                        <div style={{flex:1,overflowY:'auto',padding:'6px 20px'}}>
                          {loading && <div style={{padding:40,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:28}}>🔄</div><div style={{fontSize:14,marginTop:10}}>Recherche en cours…</div></div>}
                          {!loading && results.length===0 && source && <div style={{padding:30,textAlign:'center',color:'#6b7a8d',fontSize:13}}>Aucun résultat. Affinez la recherche.</div>}
                          {results.map((p,i)=>(
                            <div key={i} onClick={()=>toggle(i)}
                              style={{display:'flex',gap:11,padding:'9px 11px',margin:'4px 0',borderRadius:10,border:`1.5px solid ${sel[i]?'#0ea5e9':'#e8edf3'}`,background:sel[i]?'rgba(14,165,233,0.05)':'#fff',cursor:'pointer',alignItems:'flex-start'}}>
                              <div style={{width:18,height:18,border:`2px solid ${sel[i]?'#0ea5e9':'#ccc'}`,borderRadius:5,background:sel[i]?'#0ea5e9':'#fff',display:'grid',placeItems:'center',flexShrink:0,marginTop:3}}>
                                {sel[i]&&<span style={{color:'#fff',fontSize:11,fontWeight:700}}>✓</span>}
                              </div>
                              {p.image && <img src={p.image} alt="" style={{width:44,height:44,objectFit:'contain',borderRadius:6,border:'1px solid #f0f4f8',flexShrink:0}}/>}
                              {!p.image && <div style={{width:44,height:44,borderRadius:6,background:'#f0f6ff',display:'grid',placeItems:'center',flexShrink:0,fontSize:20}}>🏊</div>}
                              <div style={{flex:1,minWidth:0}}>
                                <div style={{fontWeight:600,fontSize:13}}>{p.name}</div>
                                <div style={{fontSize:11,color:'#6b7a8d',marginTop:2,display:'flex',gap:7,flexWrap:'wrap'}}>
                                  {p.ref&&<span style={{background:'#f0f4f8',padding:'1px 6px',borderRadius:4}}>{p.ref}</span>}
                                  {p.category&&<span>{p.category}</span>}
                                  {p.note&&<span style={{fontStyle:'italic',color:'#94a3b8'}}>{p.note}</span>}
                                </div>
                                {p.price>0&&<div style={{fontSize:12,fontWeight:600,color:'#0ea5e9',marginTop:3}}>{p.price.toFixed(2)} €</div>}
                              </div>
                              {sel[i]&&(<div style={{display:'flex',flexDirection:'column',alignItems:'center',gap:3,flexShrink:0}} onClick={e=>e.stopPropagation()}>
                                <span style={{fontSize:10,color:'#6b7a8d'}}>Qté</span>
                                <input type="number" min="1" value={qtys[i]||1} onChange={e=>setQty(i,e.target.value)}
                                  style={{width:50,textAlign:'center',border:'1.5px solid #0ea5e9',borderRadius:6,padding:'3px',fontSize:13,fontFamily:'inherit'}}/>
                                <span style={{fontSize:10,color:'#6b7a8d'}}>{p.unit||'pc'}</span>
                              </div>)}
                            </div>
                          ))}
                        </div>
                        <div style={{padding:'11px 20px',borderTop:'1.5px solid #dde4ed',display:'flex',alignItems:'center',gap:10}}>
                          <span style={{fontSize:13,color:'#6b7a8d',flex:1}}>{selCount} produit(s) sélectionné(s)</span>
                          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:9,padding:'8px 16px',cursor:'pointer',fontFamily:'inherit',fontSize:13}}>Annuler</button>
                          <button onClick={confirm} disabled={!selCount}
                            style={{background:selCount?'#0ea5e9':'#d1d5db',color:'#fff',border:'none',borderRadius:9,padding:'8px 20px',fontWeight:600,cursor:selCount?'pointer':'not-allowed',fontFamily:'inherit',fontSize:13}}>
                            ✓ Ajouter à l'intervention
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                }

                /* ─── SectionBlock ─── */
                function SectionBlock({sec,si,checked,notes,toggle,setNote,accent,linkedProducts,onAddProducts,onRemoveProduct}) {
                  const [open,setOpen] = React.useState(true);
                  const [productPanel,setProductPanel] = React.useState(null);
                  const sChecked = sec.items.filter((_,i)=>checked[`${si}_${i}`]).length;
                  return (
                    <>
                      {productPanel!==null&&<ProductPanel itemText={sec.items[productPanel]} sectionLabel={sec.section} onAdd={prods=>onAddProducts(si,productPanel,prods)} onClose={()=>setProductPanel(null)}/>}
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
                            const k=`${si}_${idx}`,isChk=!!checked[k],prods=linkedProducts[k]||[];
                            return (
                              <div key={idx}>
                                <div className={`lpc-item${isChk?' checked':''}`}>
                                  <input type="checkbox" checked={isChk} onChange={()=>toggle(si,idx)} style={{width:17,height:17,flexShrink:0,marginTop:2,accentColor:accent,cursor:'pointer'}}/>
                                  <span className={`lpc-item-text${isChk?' done':''}`}>{item}</span>
                                  <button className="lpc-add-btn no-print" title="Lier des produits" onClick={()=>setProductPanel(idx)} style={{'--acc':accent}}>
                                    🛒{prods.length>0&&<span className="lpc-badge">{prods.length}</span>}
                                  </button>
                                  <input className="lpc-note no-print" placeholder="Note…" value={notes[k]||''} onChange={e=>setNote(si,idx,e.target.value)}/>
                                </div>
                                {prods.length>0&&<div className="lpc-linked">{prods.map((p,pi)=>(
                                  <div key={pi} className="lpc-chip">
                                    <span className="lpc-chip-qty">{p.qty}×</span>
                                    {p.ref&&<span className="lpc-chip-ref">[{p.ref}]</span>}
                                    <span className="lpc-chip-name">{p.name}</span>
                                    {p.price>0&&<span className="lpc-chip-price">{(p.price*(p.qty||1)).toFixed(2)} €</span>}
                                    <button className="lpc-chip-del no-print" onClick={()=>onRemoveProduct(si,idx,pi)}>✕</button>
                                  </div>
                                ))}</div>}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </>
                  );
                }

                /* ─── Main App ─── */
                function PoolChecklist() {
                  const [step,setStep] = React.useState(0);
                  const [intervention,setIntervention] = React.useState(null);
                  const [plan,setPlan] = React.useState(null);
                  const [client,setClient] = React.useState({nom:'',adresse:'',date:new Date().toISOString().slice(0,10),technicien:cfg.userName||'',ref:'',tel:''});
                  const [checked,setChecked] = React.useState({});
                  const [notes,setNotes] = React.useState({});
                  const [linkedProducts,setLinkedProducts] = React.useState({});

                  const toggle  = (si,idx) => { const k=`${si}_${idx}`; setChecked(p=>({...p,[k]:!p[k]})); };
                  const setNote = (si,idx,v) => { const k=`${si}_${idx}`; setNotes(p=>({...p,[k]:v})); };
                  const addProducts = (si,idx,prods) => { const k=`${si}_${idx}`; setLinkedProducts(p=>({...p,[k]:[...(p[k]||[]),...prods]})); };
                  const removeProduct = (si,idx,pi) => { const k=`${si}_${idx}`; setLinkedProducts(p=>({...p,[k]:(p[k]||[]).filter((_,i)=>i!==pi)})); };

                  const intData  = INTERVENTIONS.find(i=>i.id===intervention);
                  const sections = intervention?CHECKLISTS[intervention]:[];
                  const totalItems = sections.reduce((a,s)=>a+s.items.length,0);
                  const checkedCount = Object.values(checked).filter(Boolean).length;
                  const accent = intData?.color||'#0ea5e9';
                  const allProds = Object.entries(linkedProducts).filter(([,a])=>a.length>0).flatMap(([k,a])=>a.map(p=>({...p,_k:k})));
                  const totalEst = allProds.reduce((a,p)=>a+(p.price||0)*(p.qty||1),0);

                  const steps = ["Type d'intervention","Infos client","Plan de bassin","Check-list & produits"];

                  return (
                    <div className="lpc-app">
                      <div className="lpc-hdr">
                        <div className="lpc-logo" style={{background:accent}}>🏊</div>
                        <div><h1>Lolirine Pool Store — Fiche de visite chantier</h1><p>Diagnostic · intervention · produits liés · devis estimatif</p></div>
                        <a href="/odoo/website" style={{marginLeft:'auto',background:'none',border:'1.5px solid #dde4ed',borderRadius:8,padding:'6px 14px',fontSize:13,color:'#6b7a8d',textDecoration:'none',flexShrink:0}}>← Retour Odoo</a>
                      </div>

                      <div className="lpc-stepper no-print">
                        {steps.map((lbl,i)=>(
                          <div key={i} className={`lpc-step${step===i?' active':step>i?' done':''}`} style={{'--acc':accent}}>
                            <div className="lpc-step-num">{step>i?'✓':i+1}</div>
                            <div className="lpc-step-lbl">{lbl}</div>
                          </div>
                        ))}
                      </div>

                      {step===0&&(
                        <div>
                          <h2 className="lpc-title">Sélectionner le type d'intervention</h2>
                          <div className="lpc-grid">
                            {INTERVENTIONS.map(iv=>(
                              <div key={iv.id} className={`lpc-card${intervention===iv.id?' sel':''}`} style={{'--acc':iv.color,'--acc-light':iv.color+'18'}} onClick={()=>setIntervention(iv.id)}>
                                <div className="lpc-card-title">{iv.label}</div>
                                <div className="lpc-card-sub">{CHECKLISTS[iv.id].reduce((a,s)=>a+s.items.length,0)} points · {CHECKLISTS[iv.id].length} sections</div>
                              </div>
                            ))}
                          </div>
                          <div className="lpc-acts no-print"><div style={{flex:1}}/><button className="lpc-btn-p" disabled={!intervention} style={{'--acc':accent}} onClick={()=>setStep(1)}>Suivant →</button></div>
                        </div>
                      )}

                      {step===1&&(
                        <div>
                          <h2 className="lpc-title">Informations client & chantier</h2>
                          <div className="lpc-section" style={{padding:20}}>
                            <div className="lpc-form-grid">
                              {[['Nom / Raison sociale','nom','text','M./Mme Dupont',true],['Adresse du chantier','adresse','text','Rue de la Piscine 12, 5000 Namur',true],['Téléphone','tel','tel','+32 4xx xx xx xx',false],['Date de visite','date','date','',false],['Technicien / Commercial','technicien','text','Prénom NOM',false],['Référence dossier','ref','text','LPS-2025-001',false]].map(([lbl,fld,typ,ph,full])=>(
                                <div key={fld} className={`lpc-fg${full?' full':''}`}>
                                  <label>{lbl}</label>
                                  <input type={typ} value={client[fld]} placeholder={ph} onChange={e=>setClient(p=>({...p,[fld]:e.target.value}))} style={{'--acc':accent}}/>
                                </div>
                              ))}
                            </div>
                          </div>
                          <div className="lpc-acts no-print">
                            <button className="lpc-btn-s" onClick={()=>setStep(0)}>← Retour</button><div style={{flex:1}}/>
                            <button className="lpc-btn-p" style={{'--acc':accent}} onClick={()=>setStep(2)}>Suivant →</button>
                          </div>
                        </div>
                      )}

                      {step===2&&(
                        <div>
                          <h2 className="lpc-title">Plan de bassin</h2>
                          <p style={{fontSize:13,color:'#6b7a8d',marginBottom:15}}>Sélectionner la forme correspondante (imprimée sur la fiche)</p>
                          <div className="lpc-grid">
                            {POOL_PLANS.map(p=>(
                              <div key={p.id} className={`lpc-plan-card${plan===p.id?' sel':''}`} style={{'--acc':accent}} onClick={()=>setPlan(p.id)}>
                                <PoolSvg plan={p} size={140}/><div className="lpc-plan-lbl">{p.label}</div>
                              </div>
                            ))}
                          </div>
                          <div className="lpc-acts no-print">
                            <button className="lpc-btn-s" onClick={()=>setStep(1)}>← Retour</button><div style={{flex:1}}/>
                            <button className="lpc-btn-g" onClick={()=>{setPlan(null);setStep(3);}}>Passer (sans plan)</button>
                            <button className="lpc-btn-p" disabled={!plan} style={{'--acc':accent}} onClick={()=>setStep(3)}>Suivant →</button>
                          </div>
                        </div>
                      )}

                      {step===3&&(
                        <div>
                          <div className="lpc-print-hdr">
                            <div className="lpc-sumbox">
                              {[['Client',client.nom],['Adresse',client.adresse],['Tél',client.tel],['Date',client.date],['Technicien',client.technicien],['Réf.',client.ref],['Intervention',intData?.label]].filter(([,v])=>v).map(([l,v])=>(
                                <div key={l} className="lpc-si2"><span>{l}</span><strong>{v}</strong></div>
                              ))}
                            </div>
                          </div>
                          <div className="lpc-sumbox no-print">
                            <div className="lpc-si2"><span>Client</span><strong>{client.nom||'—'}</strong></div>
                            <div className="lpc-si2"><span>Date</span><strong>{client.date}</strong></div>
                            <div className="lpc-si2"><span>Intervention</span><strong style={{color:accent}}>{intData?.label}</strong></div>
                            {plan&&<div className="lpc-si2"><span>Plan</span><strong>{POOL_PLANS.find(p=>p.id===plan)?.label}</strong></div>}
                            <div style={{flex:1}}/>
                            <div className="lpc-si2" style={{alignItems:'flex-end'}}><span>✅ Cochés</span><strong style={{color:accent}}>{checkedCount}/{totalItems}</strong></div>
                            <div className="lpc-si2" style={{alignItems:'flex-end'}}><span>🛒 Produits</span><strong style={{color:'#0ea5e9'}}>{allProds.length}</strong></div>
                            {totalEst>0&&<div className="lpc-si2" style={{alignItems:'flex-end'}}><span>💰 Estimation</span><strong style={{color:'#059669'}}>{totalEst.toFixed(2)} €</strong></div>}
                          </div>
                          <div className="no-print" style={{marginBottom:14}}>
                            <div className="lpc-progbar"><div className="lpc-progfill" style={{width:`${totalItems?(checkedCount/totalItems)*100:0}%`,'--acc':accent}}/></div>
                            <div style={{fontSize:12,color:'#6b7a8d',marginTop:5,textAlign:'right'}}>{totalItems?Math.round((checkedCount/totalItems)*100):0}% complété</div>
                          </div>
                          {plan&&(<>
                            <div style={{display:'flex',justifyContent:'center',marginBottom:14}} className="no-print">
                              <div style={{background:'#fff',border:'1.5px solid #dde4ed',borderRadius:12,padding:14,display:'inline-flex',flexDirection:'column',alignItems:'center',gap:7}}>
                                <PoolSvg plan={POOL_PLANS.find(p=>p.id===plan)} size={160}/>
                                <div style={{fontSize:12,fontWeight:600,color:accent}}>{POOL_PLANS.find(p=>p.id===plan)?.label}</div>
                              </div>
                            </div>
                            <div className="lpc-print-plan"><PoolSvg plan={POOL_PLANS.find(p=>p.id===plan)} size={100}/><div style={{fontSize:9}}>{POOL_PLANS.find(p=>p.id===plan)?.label}</div></div>
                          </>)}

                          {sections.map((sec,si)=>(
                            <SectionBlock key={si} sec={sec} si={si} checked={checked} notes={notes} toggle={toggle} setNote={setNote} accent={accent}
                              linkedProducts={linkedProducts} onAddProducts={addProducts} onRemoveProduct={removeProduct}/>
                          ))}

                          {allProds.length>0&&(
                            <div className="lpc-section" style={{marginTop:8}}>
                              <div className="lpc-sec-hdr">
                                <h3>🛒 Récapitulatif matériaux & produits liés</h3>
                                <span className="lpc-progress">{allProds.length} article(s){totalEst>0?` · ${totalEst.toFixed(2)} €`:''}</span>
                              </div>
                              <div style={{padding:'6px 0'}}>
                                <table className="lpc-mat-tbl">
                                  <thead><tr><th>Réf.</th><th>Désignation</th><th>Qté</th><th>Unité</th>{totalEst>0&&<><th>P.U.</th><th>Total HT</th></>}<th>Point de contrôle</th></tr></thead>
                                  <tbody>
                                    {allProds.map((p,i)=>(
                                      <tr key={i}>
                                        <td style={{color:'#6b7a8d',fontSize:11,fontFamily:'monospace'}}>{p.ref||'—'}</td>
                                        <td style={{fontWeight:500}}>{p.name}</td>
                                        <td style={{textAlign:'center'}}>{p.qty}</td>
                                        <td>{p.unit||'pc'}</td>
                                        {totalEst>0&&<>
                                          <td style={{textAlign:'right'}}>{p.price>0?`${p.price.toFixed(2)} €`:'—'}</td>
                                          <td style={{textAlign:'right',fontWeight:600}}>{p.price>0?`${(p.price*(p.qty||1)).toFixed(2)} €`:'—'}</td>
                                        </>}
                                        <td style={{fontSize:11,color:'#6b7a8d',maxWidth:140,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{p.itemText?.slice(0,50)||''}</td>
                                      </tr>
                                    ))}
                                    {totalEst>0&&<tr className="lpc-mat-tot">
                                      <td colSpan={totalEst>0?5:3} style={{textAlign:'right',fontWeight:700}}>Total estimatif HT</td>
                                      <td style={{textAlign:'right',fontWeight:700,color:'#059669'}}>{totalEst.toFixed(2)} €</td><td/>
                                    </tr>}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          <div className="lpc-section" style={{marginTop:12}}>
                            <div className="lpc-sec-hdr"><h3>✍️ Signature & validation</h3></div>
                            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:28,padding:18}}>
                              <div><div style={{fontSize:12,color:'#6b7a8d',marginBottom:44}}>Signature du technicien</div><div style={{borderTop:'1.5px solid #dde4ed',paddingTop:5,fontSize:12,color:'#6b7a8d'}}>Nom & Date</div></div>
                              <div><div style={{fontSize:12,color:'#6b7a8d',marginBottom:44}}>Signature du client (bon pour accord)</div><div style={{borderTop:'1.5px solid #dde4ed',paddingTop:5,fontSize:12,color:'#6b7a8d'}}>Nom & Date</div></div>
                            </div>
                            <div style={{padding:'0 18px 15px'}}>
                              <div style={{fontSize:12,color:'#6b7a8d',marginBottom:8}}>Remarques générales</div>
                              <div style={{height:54,border:'1.5px solid #dde4ed',borderRadius:8,background:'#f0f4f8'}}/>
                            </div>
                          </div>

                          <div style={{fontSize:11,color:'#6b7a8d',textAlign:'center',marginTop:14}}>
                            Lolirine Pool Store · lolirinepoolstore.be · BCE 0650.891.279
                          </div>

                          <div className="lpc-acts no-print" style={{marginTop:18}}>
                            <button className="lpc-btn-s" onClick={()=>setStep(2)}>← Retour</button>
                            <button className="lpc-btn-s" onClick={()=>{setChecked({});setNotes({});setLinkedProducts({});}}>🔄 Réinitialiser</button>
                            <div style={{flex:1}}/>
                            <button className="lpc-btn-pr" onClick={()=>window.print()}>🖨️ Imprimer / PDF</button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }

                ReactDOM.createRoot(document.getElementById('pool-checklist-root')).render(<PoolChecklist/>);