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

                /* ─── API produits ─── */
                const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};

                async function searchOdooProducts(query, supplier=null) {
                  try {
                    const res = await fetch(cfg.productsEndpoint || '/pool-checklist/products', {
                      method:'POST',
                      headers:{'Content-Type':'application/json'},
                      credentials:'same-origin',
                      body: JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{query,limit:18,supplier}})
                    });
                    const d = await res.json();
                    const prods = d?.result?.products || [];
                    if(prods.length) return {source:'odoo', products: prods};
                    return null;
                  } catch(e) {
                    console.warn('[checklist] Odoo search failed:', e);
                    return null;
                  }
                }

                async function suggestViaAI(itemText, sectionLabel) {
                  try {
                    const res = await fetch('https://api.anthropic.com/v1/messages',{
                      method:'POST',
                      headers:{'Content-Type':'application/json'},
                      body:JSON.stringify({
                        model:'claude-sonnet-4-20250514',max_tokens:800,
                        system:`Expert équipements piscine (Lolirine Pool Store, Belgique). JSON uniquement sans markdown :
{"products":[{"ref":"","name":"Nom","category":"Cat","unit":"pièce|kg|L|m|m²|lot","note":"","supplier":"Fluidra|SCP|HTH|BWT|Hayward|Pentair"}]}
Max 7 produits.`,
                        messages:[{role:'user',content:`Section : ${sectionLabel}\nPoint : "${itemText}"\nProduits ?`}]
                      })
                    });
                    if(!res.ok) return null;
                    const d = await res.json();
                    const text = d.content?.[0]?.text || '{}';
                    const parsed = JSON.parse(text.replace(/```json|```/g,'').trim());
                    const prods = (parsed.products||[]).map(p=>({...p,
                      suppliers: p.supplier ? [{name:p.supplier,ref:p.ref||'',price:0,
                        type: /fluidra|sibo/i.test(p.supplier)?'fluidra': /scp/i.test(p.supplier)?'scp':'other'}] : []
                    }));
                    return {source:'ai', products: prods};
                  } catch(e) {
                    console.warn('[checklist] AI suggest failed:', e);
                    return null;
                  }
                }

                /* ─── ImageZoom ─── */
                function ImageZoom({src, name, onClose}) {
                  return (
                    <div onClick={onClose} style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.92)',zIndex:99999,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:24,cursor:'zoom-out'}}>
                      <img src={src} alt={name} style={{maxWidth:'88vw',maxHeight:'78vh',objectFit:'contain',borderRadius:14,boxShadow:'0 24px 80px rgba(0,0,0,0.6)',background:'#fff',padding:16}}/>
                      <div style={{color:'rgba(255,255,255,0.9)',marginTop:18,fontSize:16,fontWeight:700,textAlign:'center'}}>{name}</div>
                      <div style={{color:'rgba(255,255,255,0.4)',marginTop:6,fontSize:12}}>Cliquer pour fermer</div>
                    </div>
                  );
                }

                /* ─── Chip fournisseur ─── */
                function SupplierBadge({type, name}) {
                  const colors = {
                    fluidra: {bg:'#dbeafe',color:'#1d4ed8',label:'Fluidra/SIBO'},
                    scp:     {bg:'#dcfce7',color:'#166534',label:'SCP Bénélux'},
                    other:   {bg:'#f3f4f6',color:'#6b7a8d',label:name},
                  };
                  const c = colors[type]||colors.other;
                  return <span style={{background:c.bg,color:c.color,borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:700}}>{c.label}</span>;
                }

                /* ─── ProductPanel — grille images + onglets fournisseurs + zoom ─── */
                function ProductPanel({itemText, sectionLabel, onAdd, onClose}) {
                  const [q,setQ]            = React.useState(itemText.replace(/_{3,}/g,'').trim().slice(0,40));
                  const [allResults,setAll] = React.useState([]);
                  const [loading,setLoading]= React.useState(false);
                  const [source,setSource]  = React.useState(null);
                  const [tab,setTab]        = React.useState('all'); // 'all'|'fluidra'|'scp'|'other'
                  const [sel,setSel]        = React.useState({});
                  const [qtys,setQtys]      = React.useState({});
                  const [zoom,setZoom]      = React.useState(null);

                  const search = async(query, supplierFilter=null) => {
                    if(!query.trim()) return;
                    setLoading(true); setAll([]); setSource(null); setSel({}); setQtys({});
                    try {
                      let r = await searchOdooProducts(query, supplierFilter);
                      if(!r) r = await suggestViaAI(itemText, sectionLabel);
                      setAll(r?.products||[]); setSource(r?.source||null);
                    } catch(e) {
                      console.warn('[checklist] search error:', e);
                      setAll([]); setSource('error');
                    }
                    setLoading(false);
                  };

                  React.useEffect(()=>{ search(q); },[]);

                  // Filtrage par onglet fournisseur
                  const results = React.useMemo(()=>{
                    if(tab==='all') return allResults;
                    return allResults.filter(p=>(p.suppliers||[]).some(s=>s.type===tab));
                  },[allResults,tab]);

                  // Comptages par fournisseur
                  const counts = React.useMemo(()=>({
                    all: allResults.length,
                    fluidra: allResults.filter(p=>(p.suppliers||[]).some(s=>s.type==='fluidra')).length,
                    scp:     allResults.filter(p=>(p.suppliers||[]).some(s=>s.type==='scp')).length,
                    other:   allResults.filter(p=>(p.suppliers||[]).every(s=>s.type==='other')||(p.suppliers||[]).length===0).length,
                  }),[allResults]);

                  const toggle = i => setSel(p=>({...p,[i]:!p[i]}));
                  const setQty = (i,v) => setQtys(p=>({...p,[i]:v}));
                  const selCount = Object.values(sel).filter(Boolean).length;
                  const confirm = () => {
                    onAdd(results.filter((_,i)=>sel[i]).map((p,i)=>({...p,qty:Number(qtys[i]||1)})));
                    onClose();
                  };

                  const TAB_STYLE = (active) => ({
                    padding:'7px 16px', border:'none', cursor:'pointer', fontFamily:'inherit',
                    fontSize:13, fontWeight:600, borderBottom: active?'3px solid #0ea5e9':'3px solid transparent',
                    color: active?'#0ea5e9':'#6b7a8d', background:'transparent', transition:'all .15s',
                  });

                  return (
                    <>
                      {zoom && <ImageZoom src={zoom.src} name={zoom.name} onClose={()=>setZoom(null)}/>}
                      <div style={{position:'fixed',inset:0,background:'rgba(10,20,40,0.65)',zIndex:9999,display:'flex',alignItems:'center',justifyContent:'center',padding:16}}>
                        <div style={{background:'#f0f4f8',borderRadius:20,width:'100%',maxWidth:980,maxHeight:'93vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,0.35)',overflow:'hidden'}}>

                          <div style={{padding:'16px 22px',borderBottom:'1.5px solid #dde4ed',display:'flex',gap:12,alignItems:'flex-start',background:'#fff'}}>
                            <div style={{flex:1}}>
                              <div style={{fontWeight:700,fontSize:16}}>🛒 Lier des produits à ce point</div>
                              <div style={{fontSize:12,color:'#6b7a8d',marginTop:3}}>{itemText.slice(0,100)}{itemText.length>100?'…':''}</div>
                            </div>
                            <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:8,padding:'5px 13px',cursor:'pointer',fontSize:14,color:'#6b7a8d',flexShrink:0}}>✕</button>
                          </div>

                          <div style={{padding:'10px 22px',borderBottom:'1px solid #dde4ed',display:'flex',gap:8,background:'#fff'}}>
                            <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==='Enter'&&search(q)}
                              placeholder="Nom de produit, référence, marque…"
                              style={{flex:1,border:'2px solid #dde4ed',borderRadius:10,padding:'9px 14px',fontFamily:'inherit',fontSize:14,outline:'none',background:'#f8fafc'}}/>
                            <button onClick={()=>search(q)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:10,padding:'9px 22px',fontWeight:700,cursor:'pointer',fontSize:14,whiteSpace:'nowrap'}}>
                              {loading?'…':'Chercher'}
                            </button>
                          </div>

                          {allResults.length>0 && (
                            <div style={{display:'flex',alignItems:'center',gap:0,background:'#fff',borderBottom:'1px solid #dde4ed',paddingLeft:22,paddingRight:22,overflowX:'auto'}}>
                              {[
                                {id:'all',    label:'Tous',           color:'#0ea5e9', count:counts.all},
                                {id:'fluidra',label:'Fluidra / SIBO', color:'#1d4ed8', count:counts.fluidra},
                                {id:'scp',    label:'SCP Bénélux',    color:'#166534', count:counts.scp},
                                {id:'other',  label:'Autres',         color:'#6b7a8d', count:counts.other},
                              ].filter(t=>t.id==='all'||t.count>0).map(t=>(
                                <button key={t.id} onClick={()=>setTab(t.id)} style={{...TAB_STYLE(tab===t.id),color:tab===t.id?t.color:'#6b7a8d',borderBottomColor:tab===t.id?t.color:'transparent',whiteSpace:'nowrap'}}>
                                  {t.label}
                                  <span style={{marginLeft:6,background:tab===t.id?t.color:'#f0f4f8',color:tab===t.id?'#fff':'#6b7a8d',borderRadius:10,padding:'1px 7px',fontSize:11,fontWeight:700}}>
                                    {t.count}
                                  </span>
                                </button>
                              ))}
                              {source && (
                                <span style={{marginLeft:'auto',fontSize:11,fontWeight:700,padding:'2px 9px',borderRadius:20,flexShrink:0,
                                  background:source==='odoo'?'#dcfce7':'#fef3c7',color:source==='odoo'?'#166534':'#92400e'}}>
                                  {source==='odoo'?'✅ Live':'✨ IA'}
                                </span>
                              )}
                            </div>
                          )}

                          {source && allResults.length===0 && !loading && (
                            <div style={{padding:'6px 22px',background:'#fffbeb',borderBottom:'1px solid #e8edf3'}}>
                              <span style={{fontSize:11,fontWeight:700,padding:'3px 10px',borderRadius:20,background:'#fef3c7',color:'#92400e'}}>✨ Suggestions IA</span>
                            </div>
                          )}

                          <div style={{flex:1,overflowY:'auto',padding:'16px 22px'}}>
                            {loading && (
                              <div style={{padding:60,textAlign:'center',color:'#6b7a8d'}}>
                                <div style={{fontSize:40,marginBottom:14}}>🔄</div>
                                <div style={{fontSize:15}}>Recherche en cours…</div>
                              </div>
                            )}
                            {!loading && results.length===0 && source && (
                              <div style={{padding:40,textAlign:'center',color:'#6b7a8d',fontSize:14}}>
                                {tab!=='all'?'Aucun produit pour ce fournisseur.':'Aucun résultat. Affinez la recherche.'}
                              </div>
                            )}
                            <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(210px,1fr))',gap:14}}>
                              {results.map((p,i)=>{
                                const mainSupplier = (p.suppliers||[]).find(s=>s.type!=='other')||(p.suppliers||[])[0];
                                return (
                                  <div key={i} onClick={()=>toggle(i)}
                                    style={{background:'#fff',borderRadius:14,border:`2.5px solid ${sel[i]?'#0ea5e9':'#e8edf3'}`,overflow:'hidden',
                                      boxShadow:sel[i]?'0 6px 20px rgba(14,165,233,0.18)':'0 2px 8px rgba(0,0,0,0.05)',
                                      transition:'all .2s',cursor:'pointer',display:'flex',flexDirection:'column'}}>
                                    <div style={{position:'relative',background:'#f8fafc',height:180,display:'flex',alignItems:'center',justifyContent:'center',overflow:'hidden',borderBottom:'1px solid #f0f4f8'}}>
                                      {p.image ? (
                                        <>
                                          <img src={p.image} alt={p.name} style={{maxWidth:'100%',maxHeight:'100%',objectFit:'contain',padding:10}}/>
                                          <button onClick={e=>{ e.stopPropagation(); setZoom({src:p.image,name:p.name}); }}
                                            style={{position:'absolute',top:8,right:8,background:'rgba(0,0,0,0.55)',border:'none',borderRadius:6,padding:'4px 8px',cursor:'pointer',fontSize:13,color:'#fff'}}>
                                            🔍
                                          </button>
                                        </>
                                      ) : (
                                        <div style={{display:'flex',flexDirection:'column',alignItems:'center',gap:8,color:'#94a3b8'}}>
                                          <span style={{fontSize:44}}>🏊</span>
                                          <span style={{fontSize:11}}>Pas d'image</span>
                                        </div>
                                      )}
                                      <div style={{position:'absolute',top:8,left:8,width:22,height:22,border:`2.5px solid ${sel[i]?'#0ea5e9':'rgba(255,255,255,0.8)'}`,borderRadius:6,
                                        background:sel[i]?'#0ea5e9':'rgba(255,255,255,0.75)',display:'grid',placeItems:'center'}}>
                                        {sel[i]&&<span style={{color:'#fff',fontSize:13,fontWeight:800}}>✓</span>}
                                      </div>
                                      {mainSupplier && (
                                        <div style={{position:'absolute',bottom:6,left:6}}>
                                          <SupplierBadge type={mainSupplier.type} name={mainSupplier.name}/>
                                        </div>
                                      )}
                                    </div>
                                    <div style={{padding:'11px 13px',flex:1,display:'flex',flexDirection:'column',gap:5}}>
                                      <div style={{fontWeight:700,fontSize:13,lineHeight:1.3,color:'#1a2332'}}>{p.name}</div>
                                      <div style={{display:'flex',gap:5,flexWrap:'wrap'}}>
                                        {p.ref&&<span style={{background:'#f0f4f8',padding:'2px 6px',borderRadius:4,fontSize:11,fontFamily:'monospace',color:'#6b7a8d'}}>{p.ref}</span>}
                                        {p.category&&<span style={{fontSize:11,color:'#94a3b8'}}>{p.category}</span>}
                                      </div>
                                      {(p.suppliers||[]).filter(s=>s.ref||s.price>0).map((s,si)=>(
                                        <div key={si} style={{fontSize:11,display:'flex',gap:5,alignItems:'center',flexWrap:'wrap'}}>
                                          <SupplierBadge type={s.type} name={s.name}/>
                                          {s.ref&&<span style={{fontFamily:'monospace',color:'#6b7a8d'}}>Réf: {s.ref}</span>}
                                          {s.price>0&&<span style={{color:'#059669',fontWeight:700,marginLeft:'auto'}}>{s.price.toFixed(2)} €</span>}
                                        </div>
                                      ))}
                                      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginTop:'auto',paddingTop:5}}>
                                        {p.price>0?<span style={{fontWeight:700,fontSize:15,color:'#0ea5e9'}}>{p.price.toFixed(2)} €</span>:<span/>}
                                        {sel[i]&&(
                                          <div style={{display:'flex',alignItems:'center',gap:5}} onClick={e=>e.stopPropagation()}>
                                            <span style={{fontSize:11,color:'#6b7a8d',fontWeight:600}}>Qté</span>
                                            <input type="number" min="1" value={qtys[i]||1} onChange={e=>setQty(i,e.target.value)}
                                              style={{width:52,textAlign:'center',border:'2px solid #0ea5e9',borderRadius:7,padding:'3px',fontSize:13,fontFamily:'inherit',fontWeight:600}}/>
                                            <span style={{fontSize:11,color:'#6b7a8d'}}>{p.unit||'pc'}</span>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>

                          <div style={{padding:'13px 22px',borderTop:'1.5px solid #dde4ed',display:'flex',alignItems:'center',gap:10,background:'#fff'}}>
                            <span style={{fontSize:13,color:'#6b7a8d',flex:1}}>{selCount} produit(s) sélectionné(s)</span>
                            <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:10,padding:'9px 18px',cursor:'pointer',fontFamily:'inherit',fontSize:14,fontWeight:600}}>Annuler</button>
                            <button onClick={confirm} disabled={!selCount}
                              style={{background:selCount?'#0ea5e9':'#d1d5db',color:'#fff',border:'none',borderRadius:10,padding:'9px 22px',fontWeight:700,cursor:selCount?'pointer':'not-allowed',fontFamily:'inherit',fontSize:14}}>
                              ✓ Ajouter à l'intervention
                            </button>
                          </div>
                        </div>
                      </div>
                    </>
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
