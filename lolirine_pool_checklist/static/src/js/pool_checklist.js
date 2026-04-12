/* pool_checklist.js — Lolirine Pool Store © 2025
   React 18 via Babel standalone (CDN). Pas de build step.
   window.LOLIRINE_CHECKLIST_CONFIG doit être défini dans le template :
     { csrfToken, productsEndpoint, aiEndpoint, partnerEndpoint }
*/

/* global React, ReactDOM */
const { useState, useEffect, useRef, useCallback } = React;

/* ─────────────────────────────────────────────────────
   DONNÉES — Sections par type d'intervention
───────────────────────────────────────────────────── */
const SECTIONS_DATA = {
  construction: [
    { section: "🏗️ Génie civil & structure",
      items: ["Type de bassin : béton coulé / béton projeté / kit acier / polyester / bois","Dimensions retenues (L × l × prof.) : ______","Forme : rectangulaire / carré / L / ovale / haricot / sur mesure","Profondeur mini : ______ m  —  maxi : ______ m","Escalier : romain / angles / bloc côté","Banquette assise prévue","Plage bain de soleil (sun-shelf) ≤ 0,20 m","Vérification portance sol / étude géotechnique","Blindage / palplanches si nappe phréatique","Étanchéité : enduit hydraulique / membrane / liner / résine","Joints de dilatation entre bassin et plage","Regards de visite / accès coffret technique"] },
    { section: "🔧 Filtration & hydraulique",
      items: ["Débit filtration calculé (m³/h) : ______","Pompe principale : ______ kW / ______ m³/h","Filtre : sable / verre filtrant / cartouche / DE — volume ______ m³","Skimmer(s) : nombre ______ / largeur goulotte ______ mm","Bonde(s) de fond : nombre ______","Refoulement(s) : nombre / emplacement","Vanne multivoies 6 voies / 4 voies","Préfiltre pompe (panier inox)","Tuyauterie : PVC ø50 / ø63 / ø90 selon débit","Regards de soufflage / brassage (optionnel)","Pompe de brassage / nage à contre-courant","Branchements électriques armoire"] },
    { section: "💊 Traitement de l'eau",
      items: ["Électrolyseur au sel (capacité m³) : ______","Pompe doseuse pH-","Pompe doseuse chlore liquide / PAC","Régulateur ORP + sonde","Sonde pH industrielle","Analyseur en ligne (Lovibond PoolManager)","Bac tampon / cuve de dilution acide","Emplacement prévu pour produits chimiques (local fermé)"] },
    { section: "🌡️ Chauffage",
      items: ["Pompe à chaleur air/eau (puissance ______ kW)","Pompe à chaleur réversible (piscine + abri)","Échangeur thermique (raccordement chaudière gaz/mazout)","Chauffe-eau solaire (capteurs ______ m²)","Résistance électrique (puissance ______ kW)","Couverture solaire à bulles (ép. 400 µ)","Volet roulant isolant (R thermique)","Vanne de by-pass pompe à chaleur"] },
    { section: "💡 Électricité & éclairage",
      items: ["Projecteurs LED RGB subaquatiques","Spots LED encastrés paroi (niche inox)","Bandeau LED périmétral (plage)","Éclairage escalier submergé","Coffret électrique IP65 dédié piscine","Disjoncteur différentiel 30 mA obligatoire","Liaison équipotentielle (norme NF C 15-100)","Mise à la terre générale","Chemin de câbles gainés sous dallage","Raccordement armoire domotique (optionnel)","Prise extérieure étanche (pour accessoires)"] },
    { section: "🪟 Couverture & sécurité",
      items: ["Volet roulant immergé (lames polycarbonate / alu)","Volet roulant hors-sol (banc / coffre intégré)","Couverture à barres automatique / manuelle","Filet de protection (norme NF P 90-308)","Alarme piscine (OBLIGATOIRE) – type : ______","Conformité norme NF P 90-306 à vérifier","Clôture de protection (h ≥ 1,10 m) + portillon auto-fermant","Signalétique profondeur / interdiction plongée"] },
    { section: "🏡 Plage, abords & finitions",
      items: ["Margelles (carrelage / pierre naturelle / béton désactivé)","Dallage plage (antidérapant R11 minimum)","Drainage plage (pente 1 % minimum vers extérieur)","Caniveau de récupération eaux de plage","Douche solaire / raccordement eau froide + ECS","Lave-pieds","Local technique (préfabriqué / maçonné / enterré)","Ventilation local technique (gaine Ø125 mini)","Clôture / portillon de sécurité piscine","Haie / écran végétal (brise-vent)","Nettoyage chantier / évacuation gravats","Réception chantier avec fiche technique équipements","Notice utilisation + entretien remise client"] },
    { section: "🤝 Administratif & SAV",
      items: ["Devis signé + acompte encaissé","Planning prévisionnel remis","Coordonnées sous-traitants (maçon, électricien, plombier)","Garanties décennale + RC professionnelle","Dossier photos avant / pendant / après","Formation client sur équipements","Contrat d'entretien proposé"] },
  ],

  renovation: [
    { section: "🔍 Diagnostic structure",
      items: ["Fissures structure (fines / traversantes / actives)","Test étanchéité (baisse niveau eau / test colorant)","État du fond (dénivellations, décollements)","État des parois (cloques, éclatement béton)","Corrosion armatures (épaufrures, rouille visible)","État des scellements (bondes, skimmers, projecteurs)","Désolidarisation margelles / plage","Tassement / fissures plage"] },
    { section: "🎨 Revêtement existant",
      items: ["Type de revêtement actuel : ______","Âge du revêtement (années) : ______","Liner : déchirures / décollements / décolorations","Liner : vieillissement, perte de souplesse","Carrelage : joints décollés / cassés / tâchés","Carrelage : carreau(x) décollé(s) / fissuré(s)","Enduit : farinage / effritement / tâches","Membrane armée : décollement / percement","Évaluation : remplacement ou réfection partielle ?"] },
    { section: "🔧 Équipements existants",
      items: ["Âge pompe : ______ ans — état : ______","Filtre — type / âge / état : ______","Skimmers : état joints / collerettes","Bondes de fond : étanchéité OK ?","Vanne multivoies : état + étanchéité","Électrolyseur : cellule OK / à remplacer","Éclairage : projecteurs à remplacer / optique HS","Câblage : conformité + état isolations","Armoire électrique : disjoncteur différentiel présent ?"] },
    { section: "🛠️ Travaux rénovation prévus",
      items: ["Reprise fissures (résine époxy / mortier cristallin)","Traitement anti-calcaire parois","Nouveau revêtement : liner / carrelage / résine / membrane","Remplacement skimmer(s)","Remplacement bonde(s) de fond","Remplacement projecteurs LED","Remplacement pompe","Remplacement filtre + média filtrant","Mise aux normes électriques (liaison équipotentielle)","Remplacement volet + rail","Reprise margelles / plage"] },
    { section: "🤝 Fin de chantier rénovation",
      items: ["Photos avant / pendant / après","Mise en eau contrôlée (24 h surveillance)","Réglage équilibrage hydraulique","Première analyse eau + traitements de départ","Notice remise client","Formulaire de réception signé"] },
  ],

  entretien: [
    { section: "💧 Analyse et mesures eau",
      items: ["pH (cible 7,2 – 7,6) → mesuré : ______","TAC – alcalinité (cible 80–120 mg/L) → mesuré : ______","TH – dureté (cible 150–300 mg/L) → mesuré : ______","Chlore libre (cible 1,0 – 3,0 mg/L) → mesuré : ______","Chlore combiné (< 0,6 mg/L) → mesuré : ______","Taux de sel si électrolyseur (cible ______ g/L) → mesuré : ______","Cyanurate (< 75 mg/L) → mesuré : ______","Phosphates (< 0,1 mg/L) → mesuré : ______","Température eau (°C) : ______","Turbidité : eau limpide / trouble / verte"] },
    { section: "🧹 Nettoyage bassin",
      items: ["Écrémage surface (feuilles, insectes, pollens)","Aspiration fond (manuelle / robot)","Brossage parois et fond","Nettoyage ligne de flottaison (dépôt calcaire / graisses)","Nettoyage panier(s) skimmer(s)","Nettoyage panier préfiltre pompe","Nettoyage fond filtre (sable) — contre-lavage si pression ≥ 0,5 bar","Nettoyage cartouche filtrante (si applicable)","Nettoyage niche projecteur(s)","Rinçage plage / abords","Nettoyage local technique"] },
    { section: "🔄 Filtration & équipements",
      items: ["Pression manomètre relevée : ______ bar","Débit pompe vérifié","Bruit / vibration anormal pompe","Vérification programmateur / horloge","Vérification vanne multivoies (absence de fuite)","Vérification électrolyseur (cellule / production)","Vérification pompe doseuse pH","Vérification sonde ORP / pH","Niveau d'eau ajusté (mi-skimmer)","Vérification alarme piscine","Vérification volet / mécanisme"] },
    { section: "💊 Traitements correctifs appliqués",
      items: ["Correction pH (produit utilisé / dose) : ______","Correction TAC (bicarbonate / CO2) : ______","Correction TH (anti-calcaire / eau douce) : ______","Choc chlore (dose) : ______","Algicide préventif appliqué","Floculant / clarifiant appliqué","Anti-phosphates appliqué"] },
    { section: "📋 Observations & recommandations",
      items: ["Prochaine vidange partielle recommandée (%)","Prochain contre-lavage prévu","Remplacement média filtrant à prévoir","Pièces à commander / en attente","Prochain passage programmé (date) : ______","Rapport envoyé au client : OUI / NON"] },
  ],

  hivernage: [
    { section: "💧 Traitement eau avant hivernage",
      items: ["Analyse complète eau réalisée","Correction pH à 7,2","Choc chlore (dose hivernage) : ______","Algicide hivernage longue durée appliqué","Anti-calcaire / séquestrant appliqué","Floculant appliqué si eau trouble","Niveau eau abaissé sous les skimmers"] },
    { section: "🔧 Filtration & hydraulique",
      items: ["Contre-lavage filtre effectué","Rinçage filtre effectué","Vidange pompe principale (corps + préfiltre)","Vidange filtre","Vidange vanne multivoies / by-pass","Vidange tuyauteries (air comprimé ou bouchons)","Vanne multivoies en position hivernage / ouverte","Débranchement pompe + mise hors tension","Démontage et rangement accessoires (balai, manche, raclette)"] },
    { section: "🌡️ Protection gel équipements",
      items: ["Déconnexion / rangement électrolyseur (cellule)","Démontage pompe doseuse + rinçage","Protection anti-gel locale technique (chauffage / isolant)","Gaine isolante sur tuyauteries exposées","Mise hors service chauffe-eau / PAC (procédure fabricant)","Vérification flotteur(s) anti-gel posé(s) dans bassin","Alimentation électrique générale piscine coupée"] },
    { section: "🪟 Couverture & sécurité hivernage",
      items: ["Volet / couverture barres en place et verrouillé","Filet de protection anti-feuilles posé","Nettoyage de la couverture avant pose","Alarme piscine : vérification piles / fonctionnement","Signalétique de sécurité en place"] },
    { section: "📋 Fin d'hivernage",
      items: ["Photos état fin de saison effectuées","Date hivernage + date remise en route estimée notées","Rapport hivernage envoyé au client","Commandes produits remise en route anticipées"] },
  ],

  remise_en_route: [
    { section: "🧹 Nettoyage général",
      items: ["Retrait couverture / filet — nettoyage et rangement","Remise en eau (niveau mi-skimmer)","Nettoyage fond et parois (dépôts hivernage)","Aspiration résidus fond","Nettoyage skimmers et préfiltre","Nettoyage local technique"] },
    { section: "🔧 Remontage équipements",
      items: ["Remontage / reconnexion pompe principale","Remontage préfiltre pompe (joint neuf si besoin)","Reconnexion vanne multivoies (position filtration)","Remontage cellule électrolyseur","Remontage pompe doseuse + amorçage","Remontage sondes pH / ORP","Vérification raccords et joints (absence de fuite)","Mise sous tension armoire électrique","Test démarrage pompe (amorçage, purge air)"] },
    { section: "💧 Première analyse & traitement",
      items: ["pH mesuré : ______ → correction : ______","TAC mesuré : ______ → correction : ______","TH mesuré : ______ → correction : ______","Taux de sel mesuré : ______ → correction : ______","Choc chlore d'ouverture (dose) : ______","Algicide préventif de départ appliqué","Anti-calcaire / séquestrant appliqué","Floculant si eau trouble appliqué","Attente filtration 48 h avant analyse définitive"] },
    { section: "⚙️ Vérifications finales",
      items: ["Programmateur réglé (horaires filtration)","Électrolyseur réglé (% production)","PAC / chauffe-eau remis en route (procédure fabricant)","Alarme piscine testée et validée","Volet / couverture testé (course complète)","Éclairage subaquatique testé","Formation / rappel client si besoin","Rapport remise en route envoyé au client"] },
  ],

  materiel: [
    { section: "🔧 Matériel à remplacer",
      items: ["Pompe principale — référence actuelle : ______","Pompe à remplacer par : ______","Filtre — référence actuelle : ______","Filtre à remplacer par : ______","Électrolyseur — cellule / groupe : ______","Projecteur(s) — nombre + type LED : ______","Volet / armoire volet : ______","Pompe doseuse — type : ______","Vanne multivoies — ø raccordement : ______","Robot nettoyeur — type : ______","Autre : ______"] },
    { section: "📦 Accessoires & consommables",
      items: ["Panier skimmer(s) — référence : ______","Panier préfiltre — référence : ______","Médias filtrants — type + quantité : ______","Manomètre — ø filetage : ______","Joints vanne multivoies — référence : ______","Embouts / bouchons hivernage","Manche + balai aspirateur","Raclette / épuisette","Thermomètre flottant / numérique","Bâche à bulles — dimensions : ______"] },
    { section: "💊 Produits chimiques commandés",
      items: ["pH- (acide chlorhydrique / pH minus granulés) — quantité : ______","pH+ (carbonate de soude) — quantité : ______","Chlore choc (granulés / liquide) — quantité : ______","Chlore lent (galets 200 g) — quantité : ______","Algicide concentré — quantité : ______","Anti-calcaire / séquestrant — quantité : ______","Floculant / clarifiant — quantité : ______","Anti-phosphates — quantité : ______","Sel électrolyse (sacs 25 kg) — nombre : ______"] },
    { section: "🤝 Fin d'intervention matériel",
      items: ["Ancien matériel déposé / évacué","Mise en service nouveau matériel effectuée","Test fonctionnement validé","Notice et garanties remises au client","Bon de livraison / facture émis"] },
  ],
};

const INTERVENTION_TYPES = [
  { key: "construction",    label: "🏗️ Construction" },
  { key: "renovation",      label: "🔨 Rénovation" },
  { key: "entretien",       label: "🧹 Entretien" },
  { key: "hivernage",       label: "❄️ Hivernage" },
  { key: "remise_en_route", label: "🌱 Remise en route" },
  { key: "materiel",        label: "📦 Changement matériel" },
];

/* ─────────────────────────────────────────────────────
   ClientAutocomplete — recherche partenaire Odoo
───────────────────────────────────────────────────── */
function ClientAutocomplete({ value, onChange, onSelectId }) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};
  const [suggs, setSuggs] = useState([]);
  const [show, setShow] = useState(false);
  const timerRef = useRef(null);
  const wrapRef = useRef(null);

  useEffect(() => {
    function handler(e) { if (wrapRef.current && !wrapRef.current.contains(e.target)) setShow(false); }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function handleInput(val) {
    onChange(val);
    clearTimeout(timerRef.current);
    if (val.length < 2) { setSuggs([]); setShow(false); return; }
    timerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(cfg.partnerEndpoint || "/pool-checklist/search-partner", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params: { query: val, limit: 8 } }),
        });
        const d = await res.json();
        const partners = d?.result?.partners || [];
        setSuggs(partners);
        setShow(partners.length > 0);
      } catch { setSuggs([]); setShow(false); }
    }, 250);
  }

  return (
    <div ref={wrapRef} style={{position:"relative"}}>
      <input value={value} onChange={e => handleInput(e.target.value)}
        placeholder="Nom du client…"
        style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:9,padding:"9px 13px",fontFamily:"inherit",fontSize:14,outline:"none",boxSizing:"border-box"}}
        onFocus={() => suggs.length && setShow(true)} />
      {show && (
        <div style={{position:"absolute",top:"100%",left:0,right:0,zIndex:1000,background:"#fff",border:"1.5px solid #dde4ed",borderRadius:10,boxShadow:"0 8px 30px rgba(0,0,0,.12)",marginTop:4,maxHeight:220,overflowY:"auto"}}>
          {suggs.map((p, i) => (
            <div key={i} onClick={() => { onChange(p.name); onSelectId && onSelectId(p.id); setShow(false); }}
              style={{padding:"9px 14px",cursor:"pointer",fontSize:13,borderBottom:i<suggs.length-1?"1px solid #f0f4f8":"none",display:"flex",gap:8,alignItems:"flex-start"}}
              onMouseEnter={e => e.currentTarget.style.background="#f0f9ff"}
              onMouseLeave={e => e.currentTarget.style.background="transparent"}>
              <div>
                <div style={{fontWeight:600,color:"#1e293b"}}>{p.name}</div>
                {p.city && <div style={{fontSize:11,color:"#94a3b8"}}>{p.city}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ─────────────────────────────────────────────────────
   SuggDropdown — liste déroulante de suggestions
───────────────────────────────────────────────────── */
function SuggDropdown({ items, onSelect, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    function handler(e) { if (ref.current && !ref.current.contains(e.target)) onClose(); }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);
  if (!items || items.length === 0) return null;
  return (
    <div ref={ref} style={{position:"absolute",top:"100%",left:0,right:0,zIndex:1000,background:"#fff",
      border:"1.5px solid #dde4ed",borderRadius:10,boxShadow:"0 8px 30px rgba(0,0,0,.12)",marginTop:4,maxHeight:220,overflowY:"auto"}}>
      {items.map((item, i) => (
        <div key={i} onClick={() => onSelect(item)}
          style={{padding:"9px 14px",cursor:"pointer",fontSize:13,color:"#1e293b",borderBottom:i<items.length-1?"1px solid #f0f4f8":"none",
            transition:"background .1s"}}
          onMouseEnter={e=>e.currentTarget.style.background="#f0f9ff"}
          onMouseLeave={e=>e.currentTarget.style.background="transparent"}>
          {item}
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   AddressAutocomplete — champ adresse avec suggestions
───────────────────────────────────────────────────── */
function AddressAutocomplete({ value, onChange, placeholder }) {
  const [suggs, setSuggs] = useState([]);
  const [show, setShow] = useState(false);
  const timerRef = useRef(null);
  const wrapRef = useRef(null);

  useEffect(() => {
    function handler(e) { if (wrapRef.current && !wrapRef.current.contains(e.target)) setShow(false); }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function handleInput(val) {
    onChange(val);
    clearTimeout(timerRef.current);
    if (val.length < 3) { setSuggs([]); setShow(false); return; }
    timerRef.current = setTimeout(async () => {
      try {
        const r = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(val)}&countrycodes=be&format=json&limit=5&addressdetails=1`,
          { headers: { "Accept-Language": "fr" } });
        const data = await r.json();
        const results = data.map(d => d.display_name);
        setSuggs(results);
        setShow(results.length > 0);
      } catch { setSuggs([]); setShow(false); }
    }, 300);
  }

  return (
    <div ref={wrapRef} style={{position:"relative"}}>
      <input value={value} onChange={e => handleInput(e.target.value)}
        placeholder={placeholder || "Adresse du chantier…"}
        style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:9,padding:"9px 13px",fontFamily:"inherit",fontSize:14,outline:"none",boxSizing:"border-box"}}
        onFocus={() => suggs.length && setShow(true)} />
      {show && <SuggDropdown items={suggs} onSelect={v => { onChange(v); setShow(false); }} onClose={() => setShow(false)} />}
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   HistoryModal — historique des fiches (localStorage)
───────────────────────────────────────────────────── */
function HistoryModal({ onClose, onLoad }) {
  const [records, setRecords] = useState([]);
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("pool_checklist_history") || "[]");
      setRecords(stored.reverse());
    } catch { setRecords([]); }
  }, []);

  function del(idx) {
    const stored = JSON.parse(localStorage.getItem("pool_checklist_history") || "[]");
    stored.splice(stored.length - 1 - idx, 1);
    localStorage.setItem("pool_checklist_history", JSON.stringify(stored));
    setRecords(stored.reverse());
  }

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,.45)",zIndex:9999,display:"flex",alignItems:"center",justifyContent:"center"}}>
      <div style={{background:"#fff",borderRadius:16,padding:28,width:"min(600px,95vw)",maxHeight:"80vh",overflow:"hidden",display:"flex",flexDirection:"column",boxShadow:"0 20px 60px rgba(0,0,0,.2)"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
          <h3 style={{margin:0,fontSize:17,color:"#1e293b",fontWeight:700}}>📋 Historique des fiches</h3>
          <button onClick={onClose} style={{background:"none",border:"1.5px solid #dde4ed",borderRadius:8,padding:"5px 12px",cursor:"pointer",fontSize:13,color:"#6b7a8d"}}>✕</button>
        </div>
        {records.length === 0
          ? <div style={{textAlign:"center",padding:"40px 0",color:"#94a3b8",fontSize:14}}>Aucune fiche sauvegardée</div>
          : <div style={{overflowY:"auto",flex:1,display:"flex",flexDirection:"column",gap:8}}>
              {records.map((r, i) => (
                <div key={i} style={{border:"1.5px solid #e8edf3",borderRadius:10,padding:"12px 16px",display:"flex",justifyContent:"space-between",alignItems:"center",gap:12}}>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontWeight:600,fontSize:14,color:"#1e293b",marginBottom:3}}>{r.client || "Client non renseigné"}</div>
                    <div style={{fontSize:12,color:"#64748b"}}>{r.type} — {r.date || "—"}</div>
                    <div style={{fontSize:12,color:"#94a3b8",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{r.address || ""}</div>
                  </div>
                  <div style={{display:"flex",gap:8,flexShrink:0}}>
                    <button onClick={() => { onLoad(r); onClose(); }}
                      style={{background:"#0ea5e9",color:"#fff",border:"none",borderRadius:8,padding:"6px 14px",cursor:"pointer",fontSize:12,fontWeight:600}}>
                      Ouvrir
                    </button>
                    <button onClick={() => del(i)}
                      style={{background:"none",border:"1.5px solid #fca5a5",color:"#ef4444",borderRadius:8,padding:"6px 10px",cursor:"pointer",fontSize:12}}>
                      🗑
                    </button>
                  </div>
                </div>
              ))}
            </div>
        }
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   ProductPanel — recherche produits + suggestions IA
───────────────────────────────────────────────────── */
function ProductPanel({ item, sectionLabel, onAddProducts, onClose }) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};
  const [q, setQ] = useState(item || "");
  const [results, setResults] = useState([]);
  const [sel, setSel] = useState({});
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState(null);

  useEffect(() => { if (item) search(item); }, []);

  async function searchOdooProducts(query) {
    try {
      const res = await fetch(cfg.productsEndpoint || "/pool-checklist/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params: { query, limit: 12 } }),
      });
      const d = await res.json();
      const prods = d?.result?.products || [];
      return prods.length ? { source: "odoo", products: prods } : null;
    } catch (e) { console.warn("[checklist] Odoo search failed:", e); return null; }
  }

  async function suggestViaAI(itemText, sectLabel) {
    try {
      const res = await fetch(cfg.aiEndpoint || "/pool-checklist/ai-suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params: { item_text: itemText, section_label: sectLabel } }),
      });
      if (!res.ok) return null;
      const d = await res.json();
      const prods = d?.result?.products || [];
      return prods.length ? { source: "ai", products: prods } : null;
    } catch (e) { console.warn("[checklist] AI suggest failed:", e); return null; }
  }

  async function search(query) {
    if (!query.trim()) return;
    setLoading(true); setResults([]); setSource(null); setSel({});
    const odoo = await searchOdooProducts(query);
    if (odoo) { setResults(odoo.products); setSource("odoo"); setLoading(false); return; }
    const ai = await suggestViaAI(query, sectionLabel);
    if (ai) { setResults(ai.products); setSource("ai"); } else { setSource("empty"); }
    setLoading(false);
  }

  function toggle(i) { setSel(s => ({ ...s, [i]: !s[i] })); }

  function addSelected() {
    const chosen = results.filter((_, i) => sel[i]);
    if (chosen.length) onAddProducts(chosen);
  }

  const nSelected = Object.values(sel).filter(Boolean).length;

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(15,23,42,.5)",zIndex:9990,display:"flex",alignItems:"center",justifyContent:"center"}}>
      <div style={{background:"#fff",borderRadius:16,width:"min(680px,96vw)",maxHeight:"88vh",display:"flex",flexDirection:"column",boxShadow:"0 24px 80px rgba(0,0,0,.22)"}}>
        {/* header */}
        <div style={{padding:"18px 20px 12px",borderBottom:"1px solid #f0f4f8",display:"flex",gap:12,alignItems:"flex-start"}}>
          <div style={{flex:1,minWidth:0}}>
            <div style={{fontWeight:700,fontSize:16,color:"#1e293b",marginBottom:3}}>🔍 Produits associés</div>
            <div style={{fontSize:12,color:"#64748b",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{item}</div>
          </div>
          <button onClick={onClose} style={{background:"none",border:"1.5px solid #dde4ed",borderRadius:8,padding:"5px 12px",cursor:"pointer",fontSize:13,color:"#6b7a8d",flexShrink:0}}>✕</button>
        </div>
        {/* search bar */}
        <div style={{padding:"10px 20px",borderBottom:"1px solid #f0f4f8",display:"flex",gap:8}}>
          <input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === "Enter" && search(q)}
            placeholder="Nom de produit, référence, marque…"
            style={{flex:1,border:"1.5px solid #dde4ed",borderRadius:9,padding:"8px 13px",fontFamily:"inherit",fontSize:14,outline:"none"}} />
          <button onClick={() => search(q)}
            style={{background:"#0ea5e9",color:"#fff",border:"none",borderRadius:9,padding:"8px 18px",fontWeight:600,cursor:"pointer",fontSize:13,whiteSpace:"nowrap"}}>
            {loading ? "…" : "Chercher"}
          </button>
        </div>
        {/* source badge */}
        {source && source !== "empty" && (
          <div style={{padding:"5px 20px",background:source==="odoo"?"#f0fdf4":"#fffbeb",borderBottom:"1px solid #f0f4f8"}}>
            <span style={{fontSize:11,fontWeight:600,padding:"2px 9px",borderRadius:20,background:source==="odoo"?"#dcfce7":"#fef3c7",color:source==="odoo"?"#166534":"#92400e"}}>
              {source==="odoo" ? "✅ Catalogue Lolirine Pool Store (données live)" : "✨ Suggestions IA (catalogue non accessible en direct)"}
            </span>
          </div>
        )}
        {/* results */}
        <div style={{flex:1,overflowY:"auto",padding:"6px 20px"}}>
          {loading && <div style={{padding:40,textAlign:"center",color:"#6b7a8d"}}><div style={{fontSize:28}}>🔄</div><div style={{fontSize:14,marginTop:10}}>Recherche en cours…</div></div>}
          {!loading && source==="empty" && <div style={{padding:30,textAlign:"center",color:"#94a3b8",fontSize:14}}>Aucun résultat trouvé.</div>}
          {!loading && source===null && results.length===0 && <div style={{padding:30,textAlign:"center",color:"#94a3b8",fontSize:14}}>Lancez une recherche ou appuyez Entrée.</div>}
          {results.map((p, i) => {
            const price = typeof p.price === "number" ? p.price : (parseFloat(p.price) || 0);
            const sup = p.suppliers?.[0] || {};
            return (
              <div key={i} onClick={() => toggle(i)}
                style={{display:"flex",gap:11,padding:"9px 11px",margin:"4px 0",borderRadius:10,border:`1.5px solid ${sel[i]?"#0ea5e9":"#e8edf3"}`,background:sel[i]?"rgba(14,165,233,.05)":"#fff",cursor:"pointer",alignItems:"flex-start",transition:"all .15s"}}>
                <div style={{width:18,height:18,border:`2px solid ${sel[i]?"#0ea5e9":"#bbb"}`,borderRadius:5,background:sel[i]?"#0ea5e9":"transparent",flexShrink:0,marginTop:2,display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontSize:12}}>
                  {sel[i] && "✓"}
                </div>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontWeight:600,fontSize:13,color:"#1e293b",marginBottom:2}}>{p.name}</div>
                  <div style={{fontSize:11,color:"#64748b",display:"flex",gap:10,flexWrap:"wrap"}}>
                    {p.ref && <span>Réf : {p.ref}</span>}
                    {p.category && <span>• {p.category}</span>}
                    {p.unit && <span>• {p.unit}</span>}
                    {sup.name && <span style={{color:"#7c3aed"}}>• {sup.name}</span>}
                    {price > 0 && <span style={{color:"#16a34a",fontWeight:600}}>• {price.toFixed(2)} € HT</span>}
                  </div>
                  {p.note && <div style={{fontSize:11,color:"#94a3b8",marginTop:2,fontStyle:"italic"}}>{p.note}</div>}
                </div>
              </div>
            );
          })}
        </div>
        {/* footer */}
        {results.length > 0 && (
          <div style={{padding:"12px 20px",borderTop:"1px solid #f0f4f8",display:"flex",justifyContent:"flex-end",gap:10}}>
            <button onClick={onClose} style={{background:"none",border:"1.5px solid #dde4ed",borderRadius:9,padding:"8px 18px",cursor:"pointer",fontSize:13,color:"#64748b"}}>Annuler</button>
            <button onClick={addSelected} disabled={nSelected===0}
              style={{background:nSelected?`#0ea5e9`:"#cbd5e1",color:"#fff",border:"none",borderRadius:9,padding:"8px 20px",fontWeight:700,cursor:nSelected?"pointer":"default",fontSize:13}}>
              Ajouter {nSelected ? `(${nSelected})` : "la sélection"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   SectionBlock — section checklist avec cases + produits
───────────────────────────────────────────────────── */
function SectionBlock({ section, items, checked, onToggle, onOpenProducts }) {
  const [open, setOpen] = useState(true);
  const done = items.filter((_, i) => checked[i]).length;
  const pct = Math.round((done / items.length) * 100);

  return (
    <div style={{background:"#fff",borderRadius:14,border:"1.5px solid #e2e8f0",marginBottom:16,overflow:"hidden",boxShadow:"0 2px 8px rgba(0,0,0,.04)"}}>
      <div onClick={() => setOpen(o => !o)} style={{padding:"14px 18px",display:"flex",alignItems:"center",gap:12,cursor:"pointer",userSelect:"none",background:"#f8fafc"}}>
        <div style={{flex:1}}>
          <div style={{fontWeight:700,fontSize:15,color:"#1e293b"}}>{section}</div>
          <div style={{marginTop:4,height:4,background:"#e2e8f0",borderRadius:4,overflow:"hidden"}}>
            <div style={{height:"100%",background:pct===100?"#16a34a":"#0ea5e9",width:`${pct}%`,borderRadius:4,transition:"width .3s"}} />
          </div>
        </div>
        <span style={{fontSize:12,color:"#64748b",whiteSpace:"nowrap"}}>{done}/{items.length}</span>
        <span style={{fontSize:11,color:"#94a3b8"}}>{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div style={{padding:"4px 0 8px"}}>
          {items.map((item, i) => (
            <div key={i} style={{display:"flex",alignItems:"flex-start",gap:10,padding:"7px 18px",borderTop:"1px solid #f8fafc"}}>
              <input type="checkbox" checked={!!checked[i]} onChange={() => onToggle(i)}
                style={{marginTop:2,width:16,height:16,accentColor:"#0ea5e9",cursor:"pointer",flexShrink:0}} />
              <span style={{flex:1,fontSize:13.5,color:checked[i]?"#94a3b8":"#334155",textDecoration:checked[i]?"line-through":"none",lineHeight:1.4}}>
                {item}
              </span>
              <button onClick={() => onOpenProducts(item, section)}
                title="Rechercher des produits"
                style={{background:"none",border:"1px solid #e2e8f0",borderRadius:6,padding:"2px 7px",cursor:"pointer",fontSize:11,color:"#94a3b8",flexShrink:0,whiteSpace:"nowrap",transition:"all .15s"}}
                onMouseEnter={e=>{e.currentTarget.style.borderColor="#0ea5e9";e.currentTarget.style.color="#0ea5e9";}}
                onMouseLeave={e=>{e.currentTarget.style.borderColor="#e2e8f0";e.currentTarget.style.color="#94a3b8";}}>
                🔍
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   QuoteModal — Devis piscine style Odoo
   Onglets : Lignes · Frais & services · Dropshipping · Notes
   TVA 21% BE · Fournisseurs SCP / Fluidra · Déplacement auto
───────────────────────────────────────────────────── */

/* ── Helpers ── */
function calcDeplacement(km) {
  const n = Number(km) || 0;
  if (n <= 0)  return 0;
  if (n <= 30) return 50;
  return 50 + Math.ceil((n - 30) / 25) * 10;
}

const EVAC_OPTIONS = [
  { key:'forfait', label:'🚛 Forfait évacuation Lolirine', price:150 },
  { key:'client',  label:'🤝 Évacuation prise en charge client', price:0 },
  { key:'sans',    label:'— Sans évacuation', price:0 },
];

const PAYMENT_TERMS = [
  'Paiement à terme échu (30 j)',
  'Paiement comptant',
  'Acompte 30 % + solde livraison',
  'Acompte 50 % + solde livraison',
  'Virement avant expédition',
];

const SUPPLIERS = ['Fluidra / SIBO','SCP Bénélux','HTH / BWT','Zodiac / Fluidra','Hayward','Astralpool','Pentair'];

const TVA_RATE = 0.21;

function QuoteModal({ products, client, clientId, address, refDossier, onClose, onCreated }) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};
  const [tab, setTab]   = useState('lines');
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState(null);
  const [error,   setError]   = useState(null);

  /* ── Onglet Lignes ── */
  const [lines, setLines] = useState(
    (products||[]).map(p => ({
      ...p, qty: p.qty||1, include: true,
      remise: 0,
      price_unit: typeof p.price==='number' ? p.price : (parseFloat(p.price)||0),
    }))
  );

  /* ── Onglet Frais & services ── */
  const [evac,      setEvac]      = useState('client');
  const [km,        setKm]        = useState(0);
  const [deplAuto,  setDeplAuto]  = useState(true);
  const [deplMt,    setDeplMt]    = useState(0);
  const [moeuvre,   setMoeuvre]   = useState(0);
  const [inclDepl,  setInclDepl]  = useState(false);
  const [inclMO,    setInclMO]    = useState(false);

  /* ── Onglet Dropshipping ── */
  const [supplier,    setSupplier]    = useState('Fluidra / SIBO');
  const [supplierRef, setSupplierRef] = useState('');
  const [delaiLivr,   setDelaiLivr]   = useState('5-10 jours ouvrés');
  const [livrAdresse, setLivrAdresse] = useState(address || '');
  const [livrDirect,  setLivrDirect]  = useState(true);
  const [commandeFourn, setCommandeFourn] = useState('');

  /* ── Onglet Notes / conditions ── */
  const [notesInt,    setNotesInt]    = useState(address ? 'Chantier : '+address : '');
  const [conditions,  setConditions]  = useState('');
  const [paymentTerm, setPaymentTerm] = useState(PAYMENT_TERMS[0]);
  const [validite,    setValidite]    = useState(30);

  /* ── Géocodage adresse → km auto ── */
  useEffect(() => {
    if (!address || Number(km)>0) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(
          'https://nominatim.openstreetmap.org/search?q='+encodeURIComponent(address)+
          '&format=json&limit=1&countrycodes=be',
          { headers:{'Accept-Language':'fr','User-Agent':'LolirinePoolChecklist/1.0'} }
        );
        const d = await r.json();
        if (cancelled||!d[0]) return;
        const lat2=parseFloat(d[0].lat), lon2=parseFloat(d[0].lon);
        const R=6371, dLat=(lat2-50.4530)*Math.PI/180, dLon=(lon2-4.9030)*Math.PI/180;
        const a=Math.sin(dLat/2)**2+Math.cos(50.4530*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
        const dist=Math.round(R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a))*1.3);
        if (!cancelled && dist>0) { setKm(dist); setInclDepl(dist>0); }
      } catch {}
    })();
    return ()=>{cancelled=true;};
  }, [address]);

  useEffect(()=>{ if(deplAuto) setDeplMt(calcDeplacement(Number(km))); }, [km, deplAuto]);

  /* ── Calculs totaux ── */
  const totalMat = lines.filter(l=>l.include).reduce((a,l)=>{
    const p = l.price_unit||0;
    return a + p*(l.qty||1)*(1-(l.remise||0)/100);
  }, 0);
  const totalDepl = inclDepl ? (deplAuto ? calcDeplacement(Number(km)) : Number(deplMt)||0) : 0;
  const totalEvac = evac!=='sans' ? (EVAC_OPTIONS.find(o=>o.key===evac)?.price||0) : 0;
  const totalMO   = inclMO ? (Number(moeuvre)||0) : 0;
  const subtotalHT = totalMat + totalDepl + totalEvac + totalMO;
  const tva        = subtotalHT * TVA_RATE;
  const totalTTC   = subtotalHT + tva;

  /* ── Mutations lignes ── */
  function toggleLine(i)     { setLines(ls=>ls.map((l,x)=>x===i?{...l,include:!l.include}:l)); }
  function updQty(i,d)       { setLines(ls=>ls.map((l,x)=>x===i?{...l,qty:Math.max(1,(l.qty||1)+d)}:l)); }
  function updPrice(i,v)     { setLines(ls=>ls.map((l,x)=>x===i?{...l,price_unit:parseFloat(v)||0}:l)); }
  function updRemise(i,v)    { setLines(ls=>ls.map((l,x)=>x===i?{...l,remise:Math.min(100,Math.max(0,parseFloat(v)||0))}:l)); }
  function removeLine(i)     { setLines(ls=>ls.filter((_,x)=>x!==i)); }

  /* ── Création devis Odoo ── */
  async function createQuote() {
    setLoading(true); setError(null);
    const allLines = [
      ...lines.filter(l=>l.include).map(l=>({
        product_id: l.id||null,
        name: l.name,
        product_uom_qty: l.qty,
        price_unit: l.price_unit||0,
        discount: l.remise||0,
        default_code: l.ref||'',
      })),
      ...(totalDepl>0?[{product_id:null,name:'Frais de déplacement ('+km+' km depuis Namur)',product_uom_qty:1,price_unit:totalDepl,discount:0,default_code:''}]:[]),
      ...(totalEvac>0?[{product_id:null,name:EVAC_OPTIONS.find(o=>o.key===evac)?.label,product_uom_qty:1,price_unit:totalEvac,discount:0,default_code:''}]:[]),
      ...(totalMO>0?[{product_id:null,name:'Main d\'œuvre technicien',product_uom_qty:1,price_unit:totalMO,discount:0,default_code:''}]:[]),
    ];
    if (!allLines.length) { setError('Aucune ligne à inclure.'); setLoading(false); return; }
    try {
      const r = await fetch(cfg.quoteEndpoint||'/pool-checklist/create-quote',{
        method:'POST', headers:{'Content-Type':'application/json'}, credentials:'same-origin',
        body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{
          partner_id:clientId||null, partner_name:client||'',
          ref_dossier:refDossier||'',
          note:[notesInt,conditions,
            livrDirect?'Livraison directe chantier : '+livrAdresse:'',
            commandeFourn?'Réf. commande fourn. : '+commandeFourn:'',
            supplierRef?'Réf. fournisseur : '+supplierRef:'',
          ].filter(Boolean).join('\n'),
          payment_term:paymentTerm,
          lines:allLines,
        }}),
      });
      const d = await r.json();
      if (d?.result?.error) { setError(d.result.error); setLoading(false); return; }
      setResult(d?.result||{});
      if (onCreated) onCreated(d?.result);
    } catch(e) { setError(e.message); }
    setLoading(false);
  }

  /* ── Succès ── */
  if (result) return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center'}}>
      <div style={{background:'#fff',borderRadius:18,padding:36,width:'min(480px,92vw)',textAlign:'center',boxShadow:'0 24px 80px rgba(0,0,0,.25)'}}>
        <div style={{fontSize:52,marginBottom:10}}>✅</div>
        <div style={{fontWeight:800,fontSize:20,color:'#1e293b',marginBottom:4}}>Devis créé !</div>
        {result.name&&<div style={{fontSize:18,color:'#0ea5e9',fontWeight:700,marginBottom:4}}>{result.name}</div>}
        {result.partner_name&&<div style={{fontSize:13,color:'#64748b',marginBottom:20}}>Client : {result.partner_name}</div>}
        <div style={{display:'flex',gap:10,justifyContent:'center',flexWrap:'wrap'}}>
          {result.url&&<a href={result.url} target='_blank' rel='noreferrer'
            style={{background:'#0ea5e9',color:'#fff',borderRadius:10,padding:'10px 22px',fontWeight:700,fontSize:14,textDecoration:'none'}}>Ouvrir le devis →</a>}
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:10,padding:'10px 22px',fontWeight:600,fontSize:14,cursor:'pointer',color:'#475569'}}>Fermer</button>
        </div>
      </div>
    </div>
  );

  /* ── Styles réutilisables ── */
  const F = { label:{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.5px',display:'block',marginBottom:4} };
  const inputSt = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'7px 11px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'};
  const TABS = [
    {key:'lines',     icon:'📦', label:'Lignes de commande'},
    {key:'services',  icon:'🔧', label:'Frais & services'},
    {key:'dropship',  icon:'🚚', label:'Dropshipping'},
    {key:'notes',     icon:'📝', label:'Notes & conditions'},
  ];

  /* ── Rendu principal ── */
  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f1f5f9',borderRadius:16,width:'min(960px,100%)',maxHeight:'96vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.28)',overflow:'hidden'}}>

        {/* ══ Barre titre style Odoo ══ */}
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',padding:'12px 20px',display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:17,color:'#1e293b'}}>📄 Nouveau devis — Lolirine Pool Store</div>
            <div style={{fontSize:12,color:'#64748b',marginTop:1}}>
              {client&&<span style={{fontWeight:600,color:'#0ea5e9'}}>{client}</span>}
              {address&&<span style={{color:'#94a3b8'}}> · {address.split(',')[0]}</span>}
              {refDossier&&<span style={{color:'#7c3aed'}}> · {refDossier}</span>}
            </div>
          </div>
          <div style={{display:'flex',gap:8,alignItems:'center',flexShrink:0}}>
            <div style={{background:'#f0fdf4',border:'1.5px solid #bbf7d0',borderRadius:20,padding:'4px 12px',fontSize:12,fontWeight:700,color:'#16a34a'}}>Brouillon</div>
            <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:8,padding:'5px 13px',cursor:'pointer',fontSize:13,color:'#6b7a8d'}}>✕</button>
          </div>
        </div>

        {/* ══ Fiche client style Odoo ══ */}
        <div style={{background:'#fff',borderBottom:'1px solid #e8edf3',padding:'14px 20px',display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(180px,1fr))',gap:12,flexShrink:0}}>
          <div>
            <label style={F.label}>Client</label>
            <div style={{fontWeight:600,fontSize:14,color:'#1e293b',padding:'6px 0'}}>{client||<span style={{color:'#94a3b8'}}>Non renseigné</span>}</div>
            {address&&<div style={{fontSize:11,color:'#64748b'}}>{address}</div>}
          </div>
          <div>
            <label style={F.label}>Référence dossier</label>
            <div style={{fontWeight:600,fontSize:14,color:'#7c3aed',padding:'6px 0'}}>{refDossier||'—'}</div>
          </div>
          <div>
            <label style={F.label}>Date du devis</label>
            <div style={{fontSize:13,color:'#1e293b',padding:'6px 0'}}>{new Date().toLocaleDateString('fr-BE')}</div>
          </div>
          <div>
            <label style={F.label}>Validité</label>
            <div style={{display:'flex',alignItems:'center',gap:6}}>
              <input type='number' value={validite} min={1} max={90} onChange={e=>setValidite(e.target.value)}
                style={{width:56,...inputSt,padding:'5px 8px',textAlign:'center'}} />
              <span style={{fontSize:12,color:'#64748b'}}>jours</span>
            </div>
          </div>
          <div>
            <label style={F.label}>Conditions de paiement</label>
            <select value={paymentTerm} onChange={e=>setPaymentTerm(e.target.value)}
              style={{...inputSt,background:'#fff',cursor:'pointer'}}>
              {PAYMENT_TERMS.map(t=><option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={F.label}>TVA appliquée</label>
            <div style={{fontSize:13,fontWeight:600,color:'#475569',padding:'6px 0'}}>21 % (BE)</div>
          </div>
        </div>

        {/* ══ Onglets style Odoo ══ */}
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',display:'flex',gap:0,flexShrink:0,overflowX:'auto'}}>
          {TABS.map(t=>(
            <button key={t.key} onClick={()=>setTab(t.key)}
              style={{padding:'10px 20px',border:'none',borderBottom:tab===t.key?'3px solid #0ea5e9':'3px solid transparent',
                background:'transparent',cursor:'pointer',fontWeight:tab===t.key?700:500,fontSize:13,
                color:tab===t.key?'#0ea5e9':'#64748b',whiteSpace:'nowrap',transition:'all .15s',
                display:'flex',alignItems:'center',gap:6}}>
              {t.icon} {t.label}
              {t.key==='lines'&&<span style={{background:'#e0f2fe',color:'#0369a1',borderRadius:20,padding:'1px 7px',fontSize:11,fontWeight:700,marginLeft:4}}>{lines.filter(l=>l.include).length}</span>}
            </button>
          ))}
        </div>

        {/* ══ Corps défilable ══ */}
        <div style={{flex:1,overflowY:'auto',padding:'0'}}>

          {/* ── Onglet Lignes ── */}
          {tab==='lines' && (
            <div style={{padding:'0'}}>
              <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
                <thead style={{background:'#f8fafc',position:'sticky',top:0,zIndex:1}}>
                  <tr style={{borderBottom:'2px solid #e2e8f0'}}>
                    {['','Produit','Fournisseur','Réf. fourn.','Qté','Prix unit. HT','Rem. %','Montant HT',''].map((h,i)=>(
                      <th key={i} style={{padding:'9px 10px',textAlign:'left',fontWeight:700,color:'#64748b',fontSize:11,whiteSpace:'nowrap'}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {lines.map((l,i)=>{
                    const sup=l.suppliers?.[0]||{};
                    const mt=(l.price_unit||0)*(l.qty||1)*(1-(l.remise||0)/100);
                    return (
                      <tr key={i} style={{borderBottom:'1px solid #f1f5f9',background:l.include?'#fff':'#f8fafc',opacity:l.include?1:.5}}>
                        <td style={{padding:'8px 10px',width:22}}>
                          <input type='checkbox' checked={!!l.include} onChange={()=>toggleLine(i)} style={{accentColor:'#0ea5e9',width:15,height:15,cursor:'pointer'}} />
                        </td>
                        <td style={{padding:'8px 10px',minWidth:180}}>
                          <div style={{fontWeight:600,color:'#1e293b'}}>{l.name}</div>
                          {l.ref&&<div style={{fontSize:11,color:'#94a3b8'}}>Réf. : {l.ref}</div>}
                          {l.category&&<div style={{fontSize:11,color:'#7c3aed'}}>{l.category}</div>}
                        </td>
                        <td style={{padding:'8px 10px',fontSize:12,color:'#7c3aed',whiteSpace:'nowrap'}}>{sup.name||'—'}</td>
                        <td style={{padding:'8px 10px',fontSize:12,color:'#64748b'}}>{sup.ref||l.ref||'—'}</td>
                        <td style={{padding:'8px 10px'}}>
                          <div style={{display:'flex',alignItems:'center',gap:4}}>
                            <button onClick={()=>updQty(i,-1)} style={{width:22,height:22,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:13,lineHeight:'20px',textAlign:'center'}}>−</button>
                            <span style={{fontWeight:700,minWidth:22,textAlign:'center'}}>{l.qty}</span>
                            <button onClick={()=>updQty(i,+1)} style={{width:22,height:22,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:13,lineHeight:'20px',textAlign:'center'}}>+</button>
                          </div>
                        </td>
                        <td style={{padding:'8px 10px',width:90}}>
                          <input type='number' value={l.price_unit} min={0} step={0.01}
                            onChange={e=>updPrice(i,e.target.value)}
                            style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 7px',fontFamily:'inherit',fontSize:13,textAlign:'right',outline:'none'}} />
                        </td>
                        <td style={{padding:'8px 10px',width:70}}>
                          <input type='number' value={l.remise||0} min={0} max={100} step={1}
                            onChange={e=>updRemise(i,e.target.value)}
                            style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 7px',fontFamily:'inherit',fontSize:13,textAlign:'right',outline:'none'}} />
                        </td>
                        <td style={{padding:'8px 10px',fontWeight:700,color:'#0369a1',whiteSpace:'nowrap',textAlign:'right'}}>{mt>0?mt.toFixed(2)+' €':'—'}</td>
                        <td style={{padding:'8px 10px'}}>
                          <button onClick={()=>removeLine(i)} style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',fontSize:14,padding:'2px 4px'}}>✕</button>
                        </td>
                      </tr>
                    );
                  })}
                  {lines.length===0&&(
                    <tr><td colSpan={9} style={{padding:'30px',textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucun produit. Ajoutez des articles depuis la fiche checklist.</td></tr>
                  )}
                </tbody>
              </table>
              {/* Sous-total lignes */}
              <div style={{padding:'12px 20px',borderTop:'1px solid #e2e8f0',background:'#f8fafc',textAlign:'right',fontSize:13,color:'#64748b'}}>
                Sous-total matériaux HT : <strong style={{color:'#0369a1'}}>{totalMat.toFixed(2)} €</strong>
              </div>
            </div>
          )}

          {/* ── Onglet Frais & services ── */}
          {tab==='services' && (
            <div style={{padding:'20px',display:'flex',flexDirection:'column',gap:20}}>

              {/* Évacuation */}
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'16px 18px'}}>
                <div style={{fontWeight:700,fontSize:14,color:'#1e293b',marginBottom:12}}>🗑️ Évacuation déchets</div>
                <div style={{display:'flex',flexDirection:'column',gap:8}}>
                  {EVAC_OPTIONS.map(opt=>(
                    <label key={opt.key}
                      style={{display:'flex',alignItems:'center',gap:10,padding:'10px 14px',borderRadius:10,
                        border:`2px solid ${evac===opt.key?'#0ea5e9':'#e8edf3'}`,background:evac===opt.key?'#eff9ff':'#fff',cursor:'pointer'}}>
                      <input type='radio' name='evac' value={opt.key} checked={evac===opt.key} onChange={()=>setEvac(opt.key)} style={{accentColor:'#0ea5e9',width:16,height:16}} />
                      <span style={{flex:1,fontSize:13,fontWeight:evac===opt.key?600:400,color:evac===opt.key?'#0369a1':'#334155'}}>{opt.label}</span>
                      {opt.price>0&&<span style={{fontWeight:700,color:'#0369a1',fontSize:14}}>{opt.price.toFixed(2)} €</span>}
                    </label>
                  ))}
                </div>
              </div>

              {/* Déplacement */}
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'16px 18px'}}>
                <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:12}}>
                  <input type='checkbox' checked={inclDepl} onChange={e=>setInclDepl(e.target.checked)} style={{accentColor:'#0ea5e9',width:16,height:16,cursor:'pointer'}} />
                  <span style={{fontWeight:700,fontSize:14,color:'#1e293b'}}>🚗 Frais de déplacement</span>
                  <span style={{fontSize:11,color:'#94a3b8',fontStyle:'italic'}}>depuis Namur · ≤30 km = 50 € · +10 €/25 km</span>
                </div>
                <div style={{display:'flex',gap:16,alignItems:'flex-end',flexWrap:'wrap'}}>
                  <div>
                    <label style={F.label}>Distance (km)</label>
                    <div style={{display:'flex',alignItems:'center',gap:6}}>
                      <button onClick={()=>setKm(Math.max(0,Number(km)-5))} style={{width:28,height:28,border:'1px solid #e2e8f0',borderRadius:6,background:'#f8fafc',cursor:'pointer',fontSize:16}}>−</button>
                      <input type='number' value={km} min={0} onChange={e=>setKm(e.target.value)}
                        style={{width:70,...inputSt,padding:'6px 8px',textAlign:'center'}} />
                      <button onClick={()=>setKm(Number(km)+5)} style={{width:28,height:28,border:'1px solid #e2e8f0',borderRadius:6,background:'#f8fafc',cursor:'pointer',fontSize:16}}>+</button>
                    </div>
                  </div>
                  <div>
                    <label style={F.label}>
                      Montant HT (€)&nbsp;
                      <label style={{fontWeight:400,cursor:'pointer'}}>
                        <input type='checkbox' checked={deplAuto} onChange={e=>setDeplAuto(e.target.checked)} style={{accentColor:'#0ea5e9',marginRight:3}} />Auto
                      </label>
                    </label>
                    <input type='number' value={deplAuto?calcDeplacement(Number(km)):deplMt} min={0} readOnly={deplAuto}
                      onChange={e=>!deplAuto&&setDeplMt(e.target.value)}
                      style={{width:90,...inputSt,padding:'6px 8px',textAlign:'center',background:deplAuto?'#f8fafc':'#fff'}} />
                  </div>
                  <div style={{fontSize:12,color:'#64748b',paddingBottom:4}}>
                    {address&&<div>📍 {address.split(',')[0]}</div>}
                    {Number(km)>0&&<div style={{color:'#0ea5e9',fontWeight:600,marginTop:2}}>→ Barème : {calcDeplacement(Number(km)).toFixed(2)} €</div>}
                  </div>
                </div>
              </div>

              {/* Main d'œuvre */}
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'16px 18px'}}>
                <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:12}}>
                  <input type='checkbox' checked={inclMO} onChange={e=>setInclMO(e.target.checked)} style={{accentColor:'#0ea5e9',width:16,height:16,cursor:'pointer'}} />
                  <span style={{fontWeight:700,fontSize:14,color:'#1e293b'}}>🔨 Main d'œuvre technicien</span>
                </div>
                <div style={{display:'flex',gap:10,alignItems:'center',flexWrap:'wrap'}}>
                  <button onClick={()=>setMoeuvre(Math.max(0,(Number(moeuvre)||0)-50))} style={{width:28,height:28,border:'1px solid #e2e8f0',borderRadius:6,background:'#f8fafc',cursor:'pointer',fontSize:16}}>−</button>
                  <input type='number' value={moeuvre} min={0} step={50} onChange={e=>setMoeuvre(e.target.value)}
                    style={{width:100,...inputSt,padding:'7px 10px',textAlign:'center',fontSize:15,fontWeight:700}} />
                  <span style={{fontSize:13,color:'#475569'}}>€ HT</span>
                  <button onClick={()=>setMoeuvre((Number(moeuvre)||0)+50)} style={{width:28,height:28,border:'1px solid #e2e8f0',borderRadius:6,background:'#f8fafc',cursor:'pointer',fontSize:16}}>+</button>
                  <div style={{display:'flex',gap:6,marginLeft:4}}>
                    {[0,500,750,1000,1500,2000].map(v=>(
                      <button key={v} onClick={()=>setMoeuvre(v)}
                        style={{padding:'4px 9px',borderRadius:7,border:`1px solid ${moeuvre==v?'#0ea5e9':'#e2e8f0'}`,
                          background:moeuvre==v?'#eff9ff':'#f8fafc',color:moeuvre==v?'#0369a1':'#64748b',fontSize:11,cursor:'pointer',fontWeight:moeuvre==v?700:400}}>
                        {v===0?'—':v+'€'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* ── Onglet Dropshipping ── */}
          {tab==='dropship' && (
            <div style={{padding:'20px',display:'flex',flexDirection:'column',gap:16}}>
              <div style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:12,padding:'12px 16px',fontSize:13,color:'#92400e'}}>
                ⚡ En dropshipping, la commande fournisseur est transmise après validation du devis client. La livraison est effectuée directement sur le chantier.
              </div>

              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'18px',display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
                <div>
                  <label style={F.label}>Fournisseur principal</label>
                  <select value={supplier} onChange={e=>setSupplier(e.target.value)} style={{...inputSt,background:'#fff',cursor:'pointer'}}>
                    {SUPPLIERS.map(s=><option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label style={F.label}>Référence commande fournisseur</label>
                  <input value={commandeFourn} onChange={e=>setCommandeFourn(e.target.value)} placeholder='BC-FOURN-2025-XXX'
                    style={inputSt} />
                </div>
                <div>
                  <label style={F.label}>Référence produit fournisseur</label>
                  <input value={supplierRef} onChange={e=>setSupplierRef(e.target.value)} placeholder='ex : FLU-PMP-00312'
                    style={inputSt} />
                </div>
                <div>
                  <label style={F.label}>Délai de livraison estimé</label>
                  <input value={delaiLivr} onChange={e=>setDelaiLivr(e.target.value)}
                    style={inputSt} />
                </div>
              </div>

              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'18px'}}>
                <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:12}}>
                  <input type='checkbox' checked={livrDirect} onChange={e=>setLivrDirect(e.target.checked)} style={{accentColor:'#0ea5e9',width:16,height:16}} />
                  <span style={{fontWeight:700,fontSize:14,color:'#1e293b'}}>📍 Livraison directe sur chantier</span>
                </div>
                {livrDirect ? (
                  <div>
                    <label style={F.label}>Adresse de livraison</label>
                    <input value={livrAdresse} onChange={e=>setLivrAdresse(e.target.value)}
                      placeholder='Adresse complète de livraison…' style={inputSt} />
                  </div>
                ) : (
                  <div style={{fontSize:13,color:'#64748b',padding:'6px 0'}}>📦 Livraison à l'entrepôt Lolirine — retrait par le technicien</div>
                )}
              </div>

              {/* Tableau produits dropship */}
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',overflow:'hidden'}}>
                <div style={{background:'#f8fafc',padding:'10px 16px',borderBottom:'1px solid #e2e8f0',fontWeight:700,fontSize:13,color:'#1e293b'}}>
                  📦 Articles à commander ({lines.filter(l=>l.include).length})
                </div>
                <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
                  <thead>
                    <tr style={{borderBottom:'1px solid #f0f4f8'}}>
                      {['Désignation','Réf. catalogue','Fournisseur','Qté','Prix d\'achat estimé'].map((h,i)=>(
                        <th key={i} style={{padding:'7px 12px',textAlign:'left',fontWeight:600,color:'#64748b',fontSize:11}}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {lines.filter(l=>l.include).map((l,i)=>{
                      const sup=l.suppliers?.[0]||{};
                      return (
                        <tr key={i} style={{borderBottom:'1px solid #f8fafc'}}>
                          <td style={{padding:'8px 12px',fontWeight:500,color:'#1e293b'}}>{l.name}</td>
                          <td style={{padding:'8px 12px',color:'#64748b',fontSize:11}}>{l.ref||'—'}</td>
                          <td style={{padding:'8px 12px',color:'#7c3aed',fontSize:11}}>{sup.name||supplier}</td>
                          <td style={{padding:'8px 12px',fontWeight:700}}>{l.qty}</td>
                          <td style={{padding:'8px 12px',color:'#16a34a',fontWeight:600}}>{sup.price>0?(sup.price*l.qty).toFixed(2)+' €':'—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Onglet Notes ── */}
          {tab==='notes' && (
            <div style={{padding:'20px',display:'flex',flexDirection:'column',gap:14}}>
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'16px 18px'}}>
                <label style={F.label}>Notes internes / chantier</label>
                <textarea value={notesInt} onChange={e=>setNotesInt(e.target.value)} rows={4}
                  placeholder='Observations de la visite, accès chantier, remarques techniques…'
                  style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 13px',fontFamily:'inherit',fontSize:13,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} />
              </div>
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'16px 18px'}}>
                <label style={F.label}>Conditions particulières</label>
                <textarea value={conditions} onChange={e=>setConditions(e.target.value)} rows={3}
                  placeholder='Conditions de garantie, délais d'exécution, restrictions techniques…'
                  style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 13px',fontFamily:'inherit',fontSize:13,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} />
              </div>
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'16px 18px'}}>
                <label style={F.label}>Conditions de paiement</label>
                <select value={paymentTerm} onChange={e=>setPaymentTerm(e.target.value)}
                  style={{...inputSt,background:'#fff',cursor:'pointer',fontSize:13}}>
                  {PAYMENT_TERMS.map(t=><option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
          )}

        </div>{/* fin scroll */}

        {/* ══ Récapitulatif totaux style Odoo + footer ══ */}
        <div style={{background:'#fff',borderTop:'2px solid #e2e8f0',flexShrink:0}}>
          <div style={{display:'flex',gap:0,flexWrap:'wrap'}}>
            {/* Totaux */}
            <div style={{flex:1,padding:'14px 20px',minWidth:260}}>
              <table style={{width:'100%',fontSize:13}}>
                <tbody>
                  {totalMat>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Matériaux & produits HT</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{totalMat.toFixed(2)} €</td></tr>}
                  {totalDepl>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Déplacement ({km} km)</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{totalDepl.toFixed(2)} €</td></tr>}
                  {totalEvac>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Évacuation</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{totalEvac.toFixed(2)} €</td></tr>}
                  {totalMO>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Main d'œuvre</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{totalMO.toFixed(2)} €</td></tr>}
                  <tr style={{borderTop:'1px solid #f0f4f8'}}><td style={{color:'#64748b',padding:'6px 0 2px'}}>Montant hors taxes</td><td style={{textAlign:'right',fontWeight:700,color:'#1e293b',fontSize:14}}>{subtotalHT.toFixed(2)} €</td></tr>
                  <tr><td style={{color:'#64748b',padding:'2px 0'}}>TVA 21%</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tva.toFixed(2)} €</td></tr>
                  <tr style={{borderTop:'2px solid #0ea5e9'}}><td style={{fontWeight:800,fontSize:15,color:'#0ea5e9',padding:'6px 0 0'}}>Total TTC</td><td style={{textAlign:'right',fontWeight:800,fontSize:16,color:'#0ea5e9'}}>{totalTTC.toFixed(2)} €</td></tr>
                </tbody>
              </table>
            </div>
            {/* Boutons action */}
            <div style={{padding:'14px 20px',display:'flex',flexDirection:'column',gap:8,justifyContent:'center',minWidth:200,alignItems:'stretch'}}>
              {error&&<div style={{color:'#ef4444',fontSize:12,textAlign:'center',padding:'4px 0'}}>{error}</div>}
              <button onClick={createQuote} disabled={loading}
                style={{background:loading?'#cbd5e1':'#0ea5e9',color:'#fff',border:'none',borderRadius:10,padding:'11px 24px',fontWeight:700,fontSize:14,cursor:loading?'wait':'pointer',whiteSpace:'nowrap'}}>
                {loading?'⏳ Création…':'📄 Créer le devis Odoo'}
              </button>
              <button onClick={onClose}
                style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:10,padding:'9px 24px',fontWeight:600,fontSize:13,cursor:'pointer',color:'#475569'}}>
                ← Annuler
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   PoolChecklist — composant principal
───────────────────────────────────────────────────── */
function PoolChecklist() {
  const [type, setType] = useState("entretien");
  const [client, setClient] = useState("");
  const [clientId, setClientId] = useState(null);
  const [address, setAddress] = useState("");
  const [technicien, setTechnicien] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [ref, setRef] = useState("");
  const [observations, setObservations] = useState("");
  const [checked, setChecked] = useState({});
  const [products, setProducts] = useState([]);
  const [panel, setPanel] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [showQuote, setShowQuote] = useState(false);
  const [saved, setSaved] = useState(false);
  const [statut, setStatut] = useState('en_cours');
  const [signClient, setSignClient] = useState('');
  const [signTech, setSignTech] = useState('');

  const sections = SECTIONS_DATA[type] || [];

  const totalItems = sections.reduce((a, s) => a + s.items.length, 0);
  const totalDone = sections.reduce((a, s, si) => {
    return a + s.items.filter((_, ii) => checked[`${si}_${ii}`]).length;
  }, 0);
  const pct = totalItems ? Math.round((totalDone / totalItems) * 100) : 0;

  function handleToggle(si, ii) {
    const k = `${si}_${ii}`;
    setChecked(c => ({ ...c, [k]: !c[k] }));
  }

  function handleOpenProducts(item, sectionLabel) {
    setPanel({ item, sectionLabel });
  }

  function handleAddProducts(newProds) {
    setProducts(ps => {
      const existing = new Set(ps.map(p => p.ref || p.name));
      const toAdd = newProds.filter(p => !existing.has(p.ref || p.name));
      return [...ps, ...toAdd.map(p => ({ ...p, qty: 1 }))];
    });
    setPanel(null);
  }

  function updateQty(i, delta) {
    setProducts(ps => ps.map((p, idx) => idx===i ? { ...p, qty: Math.max(0, (p.qty||1)+delta) } : p).filter(p => p.qty > 0));
  }

  function removeProduct(i) { setProducts(ps => ps.filter((_, idx) => idx !== i)); }

  function resetChecklist() {
    if (confirm("Réinitialiser toute la fiche ?")) {
      setChecked({}); setProducts([]); setClient(""); setClientId(null);
      setAddress(""); setTechnicien(""); setObservations(""); setRef("");
      setDate(new Date().toISOString().split("T")[0]); setSaved(false);
    }
  }

  function saveToHistory() {
    try {
      const stored = JSON.parse(localStorage.getItem("pool_checklist_history") || "[]");
      stored.push({ client, address, technicien, date, ref, type, observations, checked, products,
        statut, signClient, signTech, savedAt: new Date().toISOString() });
      localStorage.setItem("pool_checklist_history", JSON.stringify(stored.slice(-50)));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) { alert("Erreur lors de la sauvegarde : " + e.message); }
  }

  function loadRecord(r) {
    setType(r.type || "entretien");
    setClient(r.client || ""); setClientId(null);
    setAddress(r.address || ""); setTechnicien(r.technicien || "");
    setDate(r.date || ""); setRef(r.ref || "");
    setObservations(r.observations || "");
    setChecked(r.checked || {}); setProducts(r.products || []);
    setStatut(r.statut || 'en_cours');
    setSignClient(r.signClient || ''); setSignTech(r.signTech || '');
  }

  function handlePrint() {
    window.print();
  }

  const totalHT = products.reduce((a, p) => {
    const price = typeof p.price === "number" ? p.price : (parseFloat(p.price) || 0);
    return a + price * (p.qty || 1);
  }, 0);

  return (
    <div style={{fontFamily:"'Inter','Segoe UI',system-ui,sans-serif",background:"#f1f5f9",minHeight:"100vh"}}>
      {/* Barre supérieure */}
      <div style={{background:"#0ea5e9",color:"#fff",padding:"14px 24px",display:"flex",alignItems:"center",gap:14,flexWrap:"wrap"}}>
        <div style={{flex:1,minWidth:200}}>
          <div style={{fontWeight:800,fontSize:20,letterSpacing:"-.5px"}}>📋 Fiche de visite chantier</div>
          <div style={{fontSize:12,opacity:.85,marginTop:1}}>Lolirine Pool Store</div>
        </div>
        <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
          <button onClick={() => setShowHistory(true)}
            style={{background:"rgba(255,255,255,.2)",color:"#fff",border:"1.5px solid rgba(255,255,255,.4)",borderRadius:9,padding:"7px 15px",cursor:"pointer",fontWeight:600,fontSize:13}}>
            📁 Historique
          </button>
          <button onClick={saveToHistory}
            style={{background:saved?"#16a34a":"rgba(255,255,255,.15)",color:"#fff",border:"1.5px solid rgba(255,255,255,.4)",borderRadius:9,padding:"7px 15px",cursor:"pointer",fontWeight:600,fontSize:13,transition:"background .3s"}}>
            {saved ? "✅ Sauvegardé !" : "💾 Sauvegarder"}
          </button>
          <button onClick={handlePrint}
            style={{background:"rgba(255,255,255,.15)",color:"#fff",border:"1.5px solid rgba(255,255,255,.4)",borderRadius:9,padding:"7px 15px",cursor:"pointer",fontWeight:600,fontSize:13}}>
            🖨️ Imprimer
          </button>
          <button onClick={resetChecklist}
            style={{background:"rgba(255,255,255,.1)",color:"rgba(255,255,255,.8)",border:"1px solid rgba(255,255,255,.3)",borderRadius:9,padding:"7px 13px",cursor:"pointer",fontSize:12}}>
            ↺ Réinitialiser
          </button>
        </div>
      </div>

      {/* Barre de progression */}
      <div style={{background:"#fff",padding:"10px 24px",borderBottom:"1px solid #e2e8f0",display:"flex",alignItems:"center",gap:14}}>
        <div style={{flex:1,height:8,background:"#e2e8f0",borderRadius:8,overflow:"hidden"}}>
          <div style={{height:"100%",background:pct===100?"#16a34a":"#0ea5e9",width:`${pct}%`,borderRadius:8,transition:"width .4s"}} />
        </div>
        <span style={{fontSize:13,fontWeight:700,color:pct===100?"#16a34a":"#0ea5e9",whiteSpace:"nowrap"}}>{pct} % — {totalDone}/{totalItems}</span>
      </div>

      <div style={{maxWidth:1000,margin:"0 auto",padding:"24px 16px"}}>
        {/* Type d'intervention */}
        <div style={{background:"#fff",borderRadius:14,padding:"18px 20px",marginBottom:20,border:"1.5px solid #e2e8f0"}}>
          <div style={{fontWeight:700,fontSize:14,color:"#1e293b",marginBottom:12}}>Type d'intervention</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
            {INTERVENTION_TYPES.map(t => (
              <button key={t.key} onClick={() => { setType(t.key); setChecked({}); }}
                style={{padding:"8px 16px",borderRadius:10,border:`2px solid ${type===t.key?"#0ea5e9":"#e2e8f0"}`,background:type===t.key?"#eff9ff":"#fff",color:type===t.key?"#0369a1":"#475569",fontWeight:type===t.key?700:500,fontSize:13,cursor:"pointer",transition:"all .15s"}}>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Fiche client */}
        <div style={{background:"#fff",borderRadius:14,padding:"18px 20px",marginBottom:20,border:"1.5px solid #e2e8f0"}}>
          <div style={{fontWeight:700,fontSize:14,color:"#1e293b",marginBottom:14}}>Informations client</div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(220px,1fr))",gap:12}}>
            <div>
              <label style={{fontSize:12,fontWeight:600,color:"#64748b",display:"block",marginBottom:4}}>Client *</label>
              <ClientAutocomplete value={client} onChange={setClient} onSelectId={setClientId} />
            </div>
            <div>
              <label style={{fontSize:12,fontWeight:600,color:"#64748b",display:"block",marginBottom:4}}>Adresse chantier</label>
              <AddressAutocomplete value={address} onChange={setAddress} placeholder="Adresse du chantier…" />
            </div>
            <div>
              <label style={{fontSize:12,fontWeight:600,color:"#64748b",display:"block",marginBottom:4}}>Technicien</label>
              <input value={technicien} onChange={e => setTechnicien(e.target.value)} placeholder="Prénom Nom"
                style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:9,padding:"9px 13px",fontFamily:"inherit",fontSize:14,outline:"none",boxSizing:"border-box"}} />
            </div>
            <div>
              <label style={{fontSize:12,fontWeight:600,color:"#64748b",display:"block",marginBottom:4}}>Date</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)}
                style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:9,padding:"9px 13px",fontFamily:"inherit",fontSize:14,outline:"none",boxSizing:"border-box"}} />
            </div>
            <div>
              <label style={{fontSize:12,fontWeight:600,color:"#64748b",display:"block",marginBottom:4}}>Référence dossier</label>
              <input value={ref} onChange={e => setRef(e.target.value)} placeholder="ex : CHT-2025-042"
                style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:9,padding:"9px 13px",fontFamily:"inherit",fontSize:14,outline:"none",boxSizing:"border-box"}} />
            </div>
          </div>
        </div>

        {/* Sections checklist */}
        {sections.map((s, si) => (
          <SectionBlock key={si}
            section={s.section}
            items={s.items}
            checked={Object.fromEntries(s.items.map((_, ii) => [ii, !!checked[`${si}_${ii}`]]))}
            onToggle={ii => handleToggle(si, ii)}
            onOpenProducts={(item, sectionLabel) => handleOpenProducts(item, sectionLabel)} />
        ))}

        {/* Observations */}
        <div style={{background:"#fff",borderRadius:14,padding:"18px 20px",marginBottom:20,border:"1.5px solid #e2e8f0"}}>
          <div style={{fontWeight:700,fontSize:14,color:"#1e293b",marginBottom:10}}>📝 Observations & recommandations</div>
          <textarea value={observations} onChange={e => setObservations(e.target.value)}
            placeholder="Observations particulières, travaux à prévoir, commentaires client…"
            style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:10,padding:"12px 14px",fontFamily:"inherit",fontSize:14,outline:"none",resize:"vertical",minHeight:100,boxSizing:"border-box",lineHeight:1.5}} />
        </div>

        {/* Récapitulatif produits */}
        {products.length > 0 && (
          <div style={{background:"#fff",borderRadius:14,padding:"18px 20px",marginBottom:20,border:"1.5px solid #e2e8f0"}}>
            <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:14,flexWrap:"wrap"}}>
              <div style={{fontWeight:700,fontSize:14,color:"#1e293b",flex:1}}>🛒 Matériaux & produits ({products.length})</div>
              <button onClick={() => setShowQuote(true)}
                style={{background:"#0ea5e9",color:"#fff",border:"none",borderRadius:10,padding:"8px 18px",fontWeight:700,fontSize:13,cursor:"pointer",display:"flex",alignItems:"center",gap:6}}>
                📄 Créer un devis
              </button>
            </div>
            <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
              <thead>
                <tr style={{borderBottom:"2px solid #f0f4f8"}}>
                  {["Référence","Désignation","Fournisseur","Unité","Qté","Prix unit. HT","Total HT",""].map((h,i) => (
                    <th key={i} style={{textAlign:"left",padding:"6px 8px",fontWeight:600,color:"#64748b",fontSize:12}}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {products.map((p, i) => {
                  const price = typeof p.price === "number" ? p.price : (parseFloat(p.price) || 0);
                  const sup = p.suppliers?.[0] || {};
                  return (
                    <tr key={i} style={{borderBottom:"1px solid #f8fafc"}}>
                      <td style={{padding:"7px 8px",color:"#94a3b8",fontSize:12}}>{p.ref || "—"}</td>
                      <td style={{padding:"7px 8px",fontWeight:500,color:"#1e293b"}}>{p.name}</td>
                      <td style={{padding:"7px 8px",color:"#7c3aed",fontSize:12}}>{sup.name || p.category || "—"}</td>
                      <td style={{padding:"7px 8px",color:"#64748b",fontSize:12}}>{p.unit || "pcs"}</td>
                      <td style={{padding:"7px 8px"}}>
                        <div style={{display:"flex",alignItems:"center",gap:6}}>
                          <button onClick={() => updateQty(i, -1)} style={{width:22,height:22,border:"1px solid #e2e8f0",borderRadius:5,background:"#f8fafc",cursor:"pointer",fontSize:14,lineHeight:"20px",textAlign:"center"}}>−</button>
                          <span style={{fontWeight:600,fontSize:14,minWidth:20,textAlign:"center"}}>{p.qty||1}</span>
                          <button onClick={() => updateQty(i, 1)} style={{width:22,height:22,border:"1px solid #e2e8f0",borderRadius:5,background:"#f8fafc",cursor:"pointer",fontSize:14,lineHeight:"20px",textAlign:"center"}}>+</button>
                        </div>
                      </td>
                      <td style={{padding:"7px 8px",color:"#16a34a",fontWeight:600}}>{price > 0 ? price.toFixed(2)+" €" : "—"}</td>
                      <td style={{padding:"7px 8px",color:"#0369a1",fontWeight:700}}>{price > 0 ? (price*(p.qty||1)).toFixed(2)+" €" : "—"}</td>
                      <td style={{padding:"7px 8px"}}>
                        <button onClick={() => removeProduct(i)} style={{background:"none",border:"none",cursor:"pointer",color:"#ef4444",fontSize:14,padding:"2px 5px"}}>✕</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {totalHT > 0 && (
                <tfoot>
                  <tr style={{borderTop:"2px solid #e2e8f0"}}>
                    <td colSpan={7} style={{padding:"10px 8px",textAlign:"right",fontWeight:800,fontSize:15,color:"#0369a1"}}>
                      Total estimatif HT : {totalHT.toFixed(2)} €
                    </td>
                    <td />
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}

      {/* ── Section Enregistrement de la fiche ── */}
      <div style={{background:"#fff",borderRadius:14,border:"1.5px solid #e2e8f0",marginBottom:20,overflow:"hidden"}}>
        <div style={{background:"#1e293b",padding:"14px 20px",display:"flex",alignItems:"center",gap:10}}>
          <span style={{fontSize:18}}>📋</span>
          <span style={{fontWeight:800,fontSize:15,color:"#fff"}}>Enregistrement de la fiche</span>
          <span style={{marginLeft:"auto",fontSize:12,color:"rgba(255,255,255,.6)"}}>Statut & signatures</span>
        </div>
        <div style={{padding:"20px"}}>
          {/* Statut */}
          <div style={{marginBottom:18}}>
            <div style={{fontWeight:700,fontSize:13,color:"#1e293b",marginBottom:8}}>Statut de la visite</div>
            <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              {[
                {key:"en_cours",    label:"🔄 En cours",     color:"#f59e0b"},
                {key:"termine",     label:"✅ Terminée",      color:"#16a34a"},
                {key:"a_replanifier",label:"🔁 À replanifier",color:"#ef4444"},
                {key:"attente_pieces",label:"⏳ Attente pièces",color:"#8b5cf6"},
              ].map(s=>(
                <button key={s.key} onClick={()=>setStatut(s.key)}
                  style={{padding:"8px 16px",borderRadius:10,border:`2px solid ${statut===s.key?s.color:"#e2e8f0"}`,
                    background:statut===s.key?s.color+"22":"#fff",color:statut===s.key?s.color:"#475569",
                    fontWeight:statut===s.key?700:500,fontSize:13,cursor:"pointer",transition:"all .15s"}}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          {/* Signatures */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:18}}>
            <div>
              <div style={{fontWeight:700,fontSize:13,color:"#1e293b",marginBottom:6}}>✍️ Signature client</div>
              <input value={signClient} onChange={e=>setSignClient(e.target.value)}
                placeholder="Nom complet du client (validation)"
                style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:9,padding:"10px 13px",fontFamily:"inherit",fontSize:14,outline:"none",boxSizing:"border-box",fontStyle:signClient?"italic":"normal"}} />
              {signClient && <div style={{fontSize:11,color:"#16a34a",marginTop:3}}>✓ Lu et approuvé par {signClient}</div>}
            </div>
            <div>
              <div style={{fontWeight:700,fontSize:13,color:"#1e293b",marginBottom:6}}>🔧 Visa technicien</div>
              <input value={signTech} onChange={e=>setSignTech(e.target.value)}
                placeholder={technicien || "Nom du technicien"}
                style={{width:"100%",border:"1.5px solid #dde4ed",borderRadius:9,padding:"10px 13px",fontFamily:"inherit",fontSize:14,outline:"none",boxSizing:"border-box",fontStyle:signTech?"italic":"normal"}} />
              {signTech && <div style={{fontSize:11,color:"#0ea5e9",marginTop:3}}>✓ Intervenu par {signTech}</div>}
            </div>
          </div>
          {/* Résumé avant enregistrement */}
          <div style={{background:"#f8fafc",borderRadius:10,padding:"12px 16px",marginBottom:16,fontSize:13,color:"#475569",display:"flex",gap:16,flexWrap:"wrap"}}>
            <span>👤 {client||"Client non renseigné"}</span>
            <span>📅 {date}</span>
            <span>🔧 {INTERVENTION_TYPES.find(t=>t.key===type)?.label||type}</span>
            <span>✅ {totalDone}/{totalItems} points</span>
            {products.length>0&&<span>🛒 {products.length} produit{products.length>1?"s":""}</span>}
          </div>
          {/* Bouton enregistrement */}
          <div style={{display:"flex",gap:10,flexWrap:"wrap"}}>
            <button onClick={saveToHistory}
              style={{background:saved?"#16a34a":"#0ea5e9",color:"#fff",border:"none",borderRadius:10,padding:"10px 24px",fontWeight:700,fontSize:14,cursor:"pointer",transition:"background .3s",flex:1,minWidth:160}}>
              {saved?"✅ Fiche enregistrée !":"💾 Enregistrer la fiche"}
            </button>
            <button onClick={handlePrint}
              style={{background:"none",border:"1.5px solid #e2e8f0",borderRadius:10,padding:"10px 20px",fontWeight:600,fontSize:13,cursor:"pointer",color:"#475569"}}>
              🖨️ Imprimer / PDF
            </button>
            {products.length>0&&(
              <button onClick={()=>setShowQuote(true)}
                style={{background:"#7c3aed",color:"#fff",border:"none",borderRadius:10,padding:"10px 20px",fontWeight:700,fontSize:13,cursor:"pointer"}}>
                📄 Créer un devis
              </button>
            )}
          </div>
        </div>
      </div>
      </div>{/* fin maxWidth container */}

      {/* Panel produits */}
      {panel && <ProductPanel item={panel.item} sectionLabel={panel.sectionLabel} onAddProducts={handleAddProducts} onClose={() => setPanel(null)} />}

      {/* Modal devis */}
      {showQuote && products.length > 0 && (
        <QuoteModal
          products={products}
          client={client}
          clientId={clientId}
          address={address}
          refDossier={ref}
          onClose={() => setShowQuote(false)}
          onCreated={() => {}}
        />
      )}

      {/* Modal historique */}
      {showHistory && <HistoryModal onClose={() => setShowHistory(false)} onLoad={loadRecord} />}
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   MOUNT
───────────────────────────────────────────────────── */
ReactDOM.createRoot(document.getElementById("pool-checklist-root")).render(<PoolChecklist />);
