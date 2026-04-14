/* pool_checklist.js — Lolirine Pool Store © 2025
   Wizard 4 étapes : Type · Infos client · Plan bassin · Check-list & produits
   React 18 · Babel standalone · No build step
*/
/* global React, ReactDOM */
const { useState, useEffect, useRef } = React;

/* ═══════════════════════════════════════════════════
   DONNÉES SECTIONS
═══════════════════════════════════════════════════ */
const SECTIONS_DATA = {
  construction: [
    { section:"🏗️ Génie civil & structure", items:["Type de bassin : béton coulé / projeté / kit acier / polyester / bois","Dimensions retenues (L × l × prof.) : ______","Forme : rectangulaire / carré / L / ovale / haricot / sur mesure","Profondeur mini : ___m — maxi : ___m","Escalier : romain / angles / côté","Banquette assise / sun-shelf prévue","Vérification portance sol / étude géotechnique","Étanchéité : enduit hydraulique / membrane / liner / résine","Joints de dilatation bassin/plage","Regards de visite / accès coffret technique"] },
    { section:"🔧 Filtration & hydraulique", items:["Débit filtration calculé (m³/h) : ______","Pompe principale : ___kW / ___m³/h","Filtre : sable / verre / cartouche — volume ___m³","Skimmer(s) : nombre ___","Bonde(s) de fond : nombre ___","Vanne multivoies 6 voies / 4 voies","Préfiltre pompe (panier inox)","Tuyauterie PVC ø50/63/90 selon débit","Pompe brassage / nage à contre-courant","Branchements électriques armoire"] },
    { section:"💊 Traitement de l'eau", items:["Électrolyseur sel (capacité m³) : ______","Pompe doseuse pH-","Pompe doseuse chlore / PAC","Régulateur ORP + sonde","Sonde pH industrielle","Analyseur en ligne (Lovibond PoolManager)","Local produits chimiques fermé à clé"] },
    { section:"🌡️ Chauffage", items:["Pompe à chaleur air/eau (___kW)","PAC réversible piscine + abri","Échangeur thermique (raccordement chaudière)","Solaire thermique (___m²)","Résistance électrique (___kW)","Couverture solaire à bulles 400µ","Volet roulant isolant"] },
    { section:"💡 Électricité & éclairage", items:["Projecteurs LED RGB subaquatiques","Coffret IP65 dédié piscine","Disjoncteur différentiel 30mA obligatoire","Liaison équipotentielle NF C 15-100","Mise à la terre générale","Câbles gainés sous dallage","Armoire domotique (optionnel)"] },
    { section:"🪟 Couverture & sécurité", items:["Volet roulant immergé / hors-sol","Couverture barres automatique / manuelle","Filet de protection NF P 90-308","Alarme piscine OBLIGATOIRE — type : ______","Clôture h≥1,10m + portillon auto-fermant","Signalétique profondeur / interdiction plongée"] },
    { section:"🏡 Plage & finitions", items:["Margelles (carrelage / pierre / béton désactivé)","Dallage antidérapant R11 minimum","Drainage plage (pente 1% minimum)","Douche solaire / raccordement ECS","Local technique (ventilé)","Nettoyage chantier / évacuation gravats","Réception chantier + notice client"] },
    { section:"📐 Abords & VRD", items:["Terrassement / nivellement","Voie d'accès chantier","Réseaux (eau / électricité / évacuation)","Clôture de chantier","Coordination sous-traitants"] },
    { section:"💧 Première mise en eau", items:["Remplissage contrôlé (24h surveillance)","Première analyse eau complète","Réglage équilibrage hydraulique","Paramétrage électrolyseur / pompes doseuses","Formation client sur équipements"] },
    { section:"📋 Administratif & garanties", items:["Devis signé + acompte encaissé","Planning prévisionnel remis","Garantie décennale + RC professionnelle","Dossier photos avant/pendant/après","Contrat d'entretien proposé"] },
    { section:"🤝 Réception chantier", items:["PV de réception signé","Notice utilisation + entretien remise","Coordonnées SAV communiquées","Clés et codes remis","Formation client complète effectuée"] },
  ],
  renovation: [
    { section:"🔍 Diagnostic structure", items:["Fissures (fines / traversantes / actives)","Test étanchéité (baisse niveau / colorant)","État fond & parois (dénivellations, décollements)","Corrosion armatures (épaufrures, rouille)","Scellements : bondes, skimmers, projecteurs","Désolidarisation margelles / plage","Tassement / fissures plage / abords"] },
    { section:"🎨 Revêtement existant", items:["Type actuel : ______  — Âge : ___ans","Liner : déchirures / décollements / décolorations","Carrelage : joints décollés / cassés / tâchés","Enduit : farinage / effritement / tâches","Membrane armée : décollement / percement","Décision : remplacement total ou réfection partielle ?"] },
    { section:"🔧 Équipements existants", items:["Pompe — âge : ___ans — état : ______","Filtre — type / âge / état : ______","Skimmers : joints / collerettes OK ?","Bondes de fond : étanchéité vérifiée","Vanne multivoies : état + absence de fuite","Électrolyseur : cellule OK / à remplacer","Câblage conforme NF C 15-100 ?"] },
    { section:"🛠️ Travaux prévus", items:["Reprise fissures (résine époxy / mortier cristallin)","Nouveau revêtement : liner / carrelage / résine / membrane","Remplacement skimmer(s)","Remplacement bonde(s) de fond","Remplacement pompe","Remplacement filtre + média filtrant","Mise aux normes électriques (équipotentielle)","Reprise margelles / plage"] },
    { section:"✅ Contrôle qualité rénovation", items:["Test étanchéité post-travaux (72h)","Mise en eau contrôlée (surveillance 24h)","Première analyse eau + traitements de départ","Photos avant / après transmises client","PV de réception signé"] },
    { section:"🤝 Fin chantier", items:["Rapport rénovation envoyé","Notice mise à jour remise","Contrat d'entretien proposé","Facture + garanties transmises"] },
    { section:"📋 Administratif", items:["Devis signé + acompte encaissé","Planning prévisionnel remis","Coordonnées sous-traitants","Garantie décennale si applicable"] },
  ],
  entretien: [
    { section:"💧 Analyse et mesures eau", items:["pH (cible 7,2–7,6) → mesuré : ______","TAC (80–120 mg/L) → mesuré : ______","TH (150–300 mg/L) → mesuré : ______","Chlore libre (1,0–3,0 mg/L) → mesuré : ______","Chlore combiné (< 0,6 mg/L) → mesuré : ______","Sel électrolyseur (cible ___g/L) → mesuré : ______","Cyanurate (< 75 mg/L) → mesuré : ______","Phosphates (< 0,1 mg/L) → mesuré : ______","Température eau (°C) : ______","Turbidité : limpide / trouble / verte"] },
    { section:"🧹 Nettoyage bassin", items:["Écrémage surface (feuilles, insectes, pollens)","Aspiration fond (manuelle / robot)","Brossage parois et fond","Ligne de flottaison (calcaire / graisses)","Panier(s) skimmer(s) vidé(s)","Panier préfiltre pompe nettoyé","Contre-lavage filtre si pression ≥ 0,5 bar","Cartouche filtrante nettoyée (si applicable)","Niche projecteur(s) nettoyée","Rinçage plage / abords","Nettoyage local technique"] },
    { section:"🔄 Filtration & équipements", items:["Pression manomètre relevée : ___bar","Débit pompe vérifié","Bruit / vibration anormal pompe ?","Programmateur / horloge correct","Vanne multivoies (fuite ?)","Électrolyseur (cellule / production)","Pompe doseuse pH (niveau / fonct.)","Sonde ORP / pH (étalonnage)","Niveau eau ajusté (mi-skimmer)","Alarme piscine testée","Volet / mécanisme vérifié"] },
    { section:"💊 Traitements correctifs appliqués", items:["Correction pH (produit / dose) : ______","Correction TAC (bicarbonate) : ______","Correction TH (anti-calcaire) : ______","Choc chlore (dose) : ______","Algicide préventif appliqué","Floculant / clarifiant appliqué","Anti-phosphates appliqué"] },
    { section:"📋 Observations & suivi", items:["Prochaine vidange partielle recommandée (%)","Prochain contre-lavage prévu","Remplacement média filtrant à prévoir","Pièces à commander : ______","Prochain passage prévu : ______","Rapport envoyé au client : OUI / NON"] },
  ],
  hivernage: [
    { section:"💧 Traitement eau avant hivernage", items:["Analyse complète réalisée","Correction pH à 7,2","Choc chlore hivernage (dose) : ______","Algicide longue durée appliqué","Anti-calcaire / séquestrant appliqué","Floculant si eau trouble","Niveau eau abaissé sous skimmers"] },
    { section:"🔧 Vidange & mise hors service", items:["Contre-lavage filtre effectué","Rinçage filtre effectué","Vidange pompe principale (corps + préfiltre)","Vidange filtre","Vidange vanne multivoies","Vidange tuyauteries (air comprimé / bouchons)","Vanne multivoies en position hivernage","Débranchement pompe + hors tension","Démontage et rangement accessoires"] },
    { section:"❄️ Protection gel", items:["Déconnexion / rangement cellule électrolyseur","Démontage pompe doseuse + rinçage","Protection anti-gel local technique","Isolant sur tuyauteries exposées","Flotteur(s) anti-gel posé(s)","Alimentation électrique générale coupée"] },
    { section:"🪟 Couverture & sécurité hivernage", items:["Volet / couverture en place et verrouillé","Filet anti-feuilles posé","Nettoyage couverture avant pose","Alarme piscine : piles / fonctionnement OK","Signalétique de sécurité en place"] },
    { section:"📋 Fin d'hivernage", items:["Photos état fin de saison","Date hivernage + remise en route estimée notées","Rapport hivernage envoyé client","Commandes produits remise en route anticipées"] },
  ],
  remise_en_route: [
    { section:"🧹 Nettoyage & remise en eau", items:["Retrait couverture / filet — nettoyage + rangement","Remise en eau (niveau mi-skimmer)","Nettoyage fond et parois (dépôts hivernage)","Aspiration résidus fond","Nettoyage skimmers et préfiltre","Nettoyage local technique"] },
    { section:"🔧 Remontage équipements", items:["Remontage / reconnexion pompe principale","Joint préfiltre pompe vérifié / remplacé","Reconnexion vanne multivoies (position filtration)","Remontage cellule électrolyseur","Remontage pompe doseuse + amorçage","Reconnexion sondes pH / ORP","Vérification raccords (absence de fuite)","Mise sous tension + test démarrage pompe"] },
    { section:"💧 1ère analyse & traitement", items:["pH mesuré : ___ → correction : ______","TAC mesuré : ___ → correction : ______","TH mesuré : ___ → correction : ______","Sel mesuré : ___ → correction : ______","Choc chlore d'ouverture (dose) : ______","Algicide préventif de départ","Anti-calcaire / séquestrant","Attente filtration 48h avant analyse définitive"] },
    { section:"⚙️ Vérifications finales", items:["Programmateur réglé (horaires filtration)","Électrolyseur réglé (% production)","PAC / chauffe-eau remis en route","Alarme piscine testée et validée","Volet / couverture testé (course complète)","Éclairage subaquatique testé","Formation / rappel client si besoin","Rapport remise en route envoyé client"] },
  ],
  materiel: [
    { section:"🔧 Diagnostic équipements", items:["Pompe actuelle — marque/modèle/âge : ______","Filtre actuel — type/marque/âge : ______","Électrolyseur actuel — marque/modèle : ______","Volet actuel — type/marque : ______","Robot nettoyeur actuel : ______","Autre matériel concerné : ______"] },
    { section:"📦 Matériel à remplacer", items:["Pompe → remplacer par : ______","Filtre → remplacer par : ______","Électrolyseur (cellule / groupe) → remplacer par : ______","Projecteur(s) LED → remplacer par : ______","Volet / armoire volet → remplacer par : ______","Robot nettoyeur → remplacer par : ______","Autre → remplacer par : ______"] },
    { section:"📦 Accessoires & consommables", items:["Panier skimmer(s) — réf : ______","Panier préfiltre pompe — réf : ______","Médias filtrants — type + qté : ______","Joints vanne multivoies — réf : ______","Manche + balai aspirateur","Raclette / épuisette de rechange","Bâche à bulles — dimensions : ______"] },
    { section:"💊 Produits chimiques à commander", items:["pH- — quantité : ______","pH+ — quantité : ______","Chlore choc — quantité : ______","Chlore lent galets 200g — quantité : ______","Algicide concentré — quantité : ______","Anti-calcaire / séquestrant — quantité : ______","Sel électrolyse (sacs 25kg) — nombre : ______"] },
    { section:"🚚 Logistique & livraison", items:["Mode de livraison : direct chantier / entrepôt Lolirine","Adresse livraison confirmée : ______","Date souhaitée : ______","Fournisseur principal : Fluidra / SCP / autre"] },
    { section:"🛠️ Intervention installation", items:["Démontage ancien matériel","Installation nouveau matériel","Test de fonctionnement","Mise au point / réglages","Formation client"] },
    { section:"✅ Réception matériel", items:["Mise en service validée","Test fonctionnement complet OK","Notice + garanties remises","Bon livraison / facture émis","Ancien matériel évacué"] },
    { section:"📋 Administratif", items:["Devis signé","Commande fournisseur passée","Réf. commande fournisseur : ______","Délai de livraison confirmé : ______"] },
    { section:"🤝 Fin d'intervention", items:["Rapport d'intervention envoyé","Photos avant/après transmises","Contrat d'entretien proposé","Satisfaction client notée : ___/5"] },
  ],
};

const INTERVENTION_TYPES = [
  { key:"construction",    icon:"🏗️", label:"Construction neuve",     color:"#0ea5e9" },
  { key:"renovation",      icon:"🔧", label:"Rénovation",              color:"#8b5cf6" },
  { key:"entretien",       icon:"🧹", label:"Entretien régulier",      color:"#16a34a" },
  { key:"hivernage",       icon:"❄️", label:"Hivernage",               color:"#64748b" },
  { key:"remise_en_route", icon:"🌱", label:"Remise en route",         color:"#f59e0b" },
  { key:"materiel",        icon:"⚙️", label:"Changement de matériel",  color:"#ef4444" },
];

const BASIN_SHAPES = [
  { key:"rectangulaire", icon:"⬜", label:"Rectangulaire" },
  { key:"carre",         icon:"🔲", label:"Carré" },
  { key:"l",             icon:"📐", label:"En L" },
  { key:"ovale",         icon:"🥚", label:"Ovale" },
  { key:"haricot",       icon:"🫘", label:"Haricot" },
  { key:"spa",           icon:"🛁", label:"Spa / Jacuzzi" },
];

/* ═══════════════════════════════════════════════════
   ClientAutocomplete
═══════════════════════════════════════════════════ */
function ClientAutocomplete({ value, onChange, onSelectPartner, placeholder }) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};
  const [suggs, setSuggs] = useState([]);
  const [open, setOpen]   = useState(false);
  const timer = useRef(null);
  const wrap  = useRef(null);
  useEffect(() => {
    const h = e => { if(wrap.current && !wrap.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);
  function handleChange(v) {
    onChange(v);
    clearTimeout(timer.current);
    if(v.length < 2) { setSuggs([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      try {
        const r = await fetch(cfg.partnerEndpoint||'/pool-checklist/search-partner', {
          method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'},
          body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{query:v,limit:8}})
        });
        const d = await r.json();
        const list = d?.result?.partners||[];
        setSuggs(list); setOpen(list.length>0);
      } catch { setSuggs([]); setOpen(false); }
    }, 280);
  }
  const IS = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 13px',fontFamily:'inherit',fontSize:14,outline:'none',boxSizing:'border-box'};
  return (
    <div ref={wrap} style={{position:'relative'}}>
      <input value={value} onChange={e=>handleChange(e.target.value)} onFocus={()=>suggs.length&&setOpen(true)}
        placeholder={placeholder||'Rechercher un client…'} style={IS} />
      {open && (
        <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:900,background:'#fff',border:'1.5px solid #dde4ed',borderRadius:9,boxShadow:'0 8px 24px rgba(0,0,0,.12)',marginTop:3,maxHeight:200,overflowY:'auto'}}>
          {suggs.map((p,i)=>(
            <div key={i} onClick={()=>{onSelectPartner&&onSelectPartner(p);setOpen(false);setSuggs([]);}}
              style={{padding:'9px 14px',cursor:'pointer',fontSize:13,borderBottom:i<suggs.length-1?'1px solid #f0f4f8':'none'}}
              onMouseEnter={e=>e.currentTarget.style.background='#f0f9ff'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
              <div style={{fontWeight:600,color:'#1e293b'}}>{p.name}</div>
              {p.city&&<div style={{fontSize:11,color:'#94a3b8'}}>{p.city}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   AddressAutocomplete
═══════════════════════════════════════════════════ */
function AddressAutocomplete({ value, onChange, placeholder }) {
  const [suggs, setSuggs] = useState([]);
  const [open, setOpen]   = useState(false);
  const [busy, setBusy]   = useState(false);
  const timer = useRef(null);
  const wrap  = useRef(null);
  useEffect(() => {
    const h = e => { if(wrap.current && !wrap.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);
  function handleChange(v) {
    onChange(v);
    clearTimeout(timer.current);
    if(v.length < 4) { setSuggs([]); setOpen(false); return; }
    timer.current = setTimeout(() => doSearch(v), 450);
  }
  async function doSearch(v) {
    setBusy(true);
    try {
      const res = await fetch(
        'https://nominatim.openstreetmap.org/search?'+new URLSearchParams({q:v,countrycodes:'be,lu,fr,nl',format:'json',limit:'6',addressdetails:'1'}),
        {mode:'cors',headers:{'Accept-Language':'fr'}}
      );
      const data = await res.json();
      const list = data.map(d => {
        const a = d.address||{};
        const parts = [a.road&&(a.road+(a.house_number?' '+a.house_number:'')),a.postcode,a.city||a.town||a.village||a.municipality].filter(Boolean);
        return parts.length>1?parts.join(', '):d.display_name.split(',').slice(0,3).join(',').trim();
      }).filter(Boolean);
      setSuggs(list); setOpen(list.length>0);
    } catch { setSuggs([]); setOpen(false); }
    setBusy(false);
  }
  const IS = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 28px 9px 13px',fontFamily:'inherit',fontSize:14,outline:'none',boxSizing:'border-box'};
  return (
    <div ref={wrap} style={{position:'relative'}}>
      <div style={{position:'relative'}}>
        <input value={value} onChange={e=>handleChange(e.target.value)} onFocus={()=>suggs.length&&setOpen(true)}
          placeholder={placeholder||'Adresse du chantier…'} style={IS} />
        <span style={{position:'absolute',right:10,top:'50%',transform:'translateY(-50%)',fontSize:12,color:'#94a3b8',cursor:value?'pointer':'default'}}
          onClick={()=>value&&onChange('')}>{busy?'⌛':value?'✕':''}</span>
      </div>
      {open&&suggs.length>0&&(
        <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:900,background:'#fff',border:'1.5px solid #dde4ed',borderRadius:9,boxShadow:'0 8px 24px rgba(0,0,0,.12)',marginTop:3,maxHeight:200,overflowY:'auto'}}>
          {suggs.map((s,i)=>(
            <div key={i} onClick={()=>{onChange(s);setOpen(false);setSuggs([]);}}
              style={{padding:'8px 13px',cursor:'pointer',fontSize:12,color:'#334155',borderBottom:i<suggs.length-1?'1px solid #f0f4f8':'none',display:'flex',gap:6}}
              onMouseEnter={e=>e.currentTarget.style.background='#f0f9ff'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
              <span style={{color:'#0ea5e9',flexShrink:0}}>📍</span>{s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   HistoryModal
═══════════════════════════════════════════════════ */
function HistoryModal({ onClose, onLoad }) {
  const [records, setRecords] = useState([]);
  useEffect(()=>{ try { setRecords(JSON.parse(localStorage.getItem('pool_checklist_history')||'[]').reverse()); } catch { setRecords([]); } },[]);
  function del(i) {
    try {
      const s=JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
      s.splice(s.length-1-i,1);
      localStorage.setItem('pool_checklist_history',JSON.stringify(s));
      setRecords(s.reverse());
    } catch {}
  }
  return (
    <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,.45)',zIndex:9999,display:'flex',alignItems:'center',justifyContent:'center'}}>
      <div style={{background:'#fff',borderRadius:16,padding:24,width:'min(560px,95vw)',maxHeight:'80vh',display:'flex',flexDirection:'column',boxShadow:'0 20px 60px rgba(0,0,0,.2)'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14}}>
          <h3 style={{margin:0,fontSize:16,color:'#1e293b',fontWeight:700}}>📋 Historique des fiches</h3>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d'}}>✕</button>
        </div>
        {records.length===0
          ? <div style={{textAlign:'center',padding:'30px 0',color:'#94a3b8',fontSize:13}}>Aucune fiche sauvegardée</div>
          : <div style={{overflowY:'auto',flex:1,display:'flex',flexDirection:'column',gap:7}}>
              {records.map((r,i)=>(
                <div key={i} style={{border:'1.5px solid #e8edf3',borderRadius:9,padding:'10px 14px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:10}}>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{r.nom||r.client||'Client non renseigné'} {r.prenom||''}</div>
                    <div style={{fontSize:11,color:'#64748b'}}>{INTERVENTION_TYPES.find(t=>t.key===r.type)?.label||r.type} — {r.date||'—'}</div>
                    {r.adresseChantier&&<div style={{fontSize:11,color:'#94a3b8',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.adresseChantier}</div>}
                  </div>
                  <div style={{display:'flex',gap:7,flexShrink:0}}>
                    <button onClick={()=>{onLoad(r);onClose();}} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:12,fontWeight:600}}>Ouvrir</button>
                    <button onClick={()=>del(i)} style={{background:'none',border:'1.5px solid #fca5a5',color:'#ef4444',borderRadius:7,padding:'5px 8px',cursor:'pointer',fontSize:12}}>🗑</button>
                  </div>
                </div>
              ))}
            </div>
        }
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   ProductPanel — 3 onglets : Recherche · Catalogue · IA
═══════════════════════════════════════════════════ */
function ProductPanel({ item, sectionLabel, onAdd, onClose }) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG||{};
  const [tab,setTab]       = useState(item?'search':'catalog');
  /* Recherche */
  const [q,setQ]           = useState(item||'');
  const [results,setRes]   = useState([]);
  const [sel,setSel]        = useState({});
  const [busy,setBusy]      = useState(false);
  const [src,setSrc]        = useState(null);
  const [sortBy,setSortBy]  = useState('name');
  const [suppFilter,setSuppFilter] = useState(null);
  const [suppliers,setSuppliers]   = useState([]);
  /* Catalogue */
  const [catPath,setCatPath]     = useState([]);
  const [categories,setCategories] = useState([]);
  const [catProds,setCatProds]   = useState([]);
  const [catBusy,setCatBusy]     = useState(false);
  const [catSel,setCatSel]       = useState({});
  /* IA */
  const [aiProds,setAiProds]     = useState([]);
  const [aiSel,setAiSel]         = useState({});
  const [aiBusy,setAiBusy]       = useState(false);
  const [aiDone,setAiDone]       = useState(false);

  /* Chargement initial */
  useEffect(()=>{
    if(item){ runSearch(item); }
    loadCategories(null);
    loadSuppliers();
  },[]);

  async function post(url,params){
    const r=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params})});
    return r.json();
  }

  async function loadSuppliers(){
    try{
      const d=await post('/pool-checklist/suppliers',{});
      setSuppliers(d?.result?.suppliers||[]);
    }catch{}
  }

  async function loadCategories(parentId){
    setCatBusy(true);
    try{
      const d=await post('/pool-checklist/categories',{parent_id:parentId});
      setCategories(d?.result?.categories||[]);
      if(parentId===null)setCatProds([]);
    }catch{}
    setCatBusy(false);
  }

  async function loadCategoryProducts(catId){
    setCatBusy(true);setCatProds([]);
    try{
      const d=await post('/pool-checklist/products',{category_id:catId,limit:50,sort:sortBy,supplier_id:suppFilter});
      setCatProds(d?.result?.products||[]);
    }catch{}
    setCatBusy(false);
  }

  async function runSearch(query){
    if(!query?.trim())return;
    setBusy(true);setRes([]);setSrc(null);setSel({});
    try{
      const d=await post('/pool-checklist/products',{query,limit:30,sort:sortBy,supplier_id:suppFilter});
      const prods=d?.result?.products||[];
      if(prods.length){setRes(prods);setSrc('odoo');setBusy(false);return;}
    }catch{}
    setSrc('empty');setBusy(false);
  }

  async function runAI(){
    if(aiDone)return;
    setAiBusy(true);setAiProds([]);
    try{
      const d=await post('/pool-checklist/ai-suggest',{item_text:item||q,section_label:sectionLabel||''});
      setAiProds(d?.result?.products||[]);setAiDone(true);
    }catch{}
    setAiBusy(false);
  }

  useEffect(()=>{ if(tab==='ai'&&!aiDone) runAI(); },[tab]);

  function drillCat(cat){
    setCatPath(p=>[...p,cat]);
    if(cat.has_children){ loadCategories(cat.id);setCatProds([]); }
    else{ loadCategoryProducts(cat.id);setCategories([]); }
  }
  function upCat(){
    const newPath=catPath.slice(0,-1);
    setCatPath(newPath);
    const parent=newPath.length>0?newPath[newPath.length-1]:null;
    if(parent){
      if(parent.has_children){loadCategories(parent.id);setCatProds([]);}
      else{loadCategoryProducts(parent.id);}
    }else{loadCategories(null);setCatProds([]);}
  }

  /* Sélection unifiée selon l'onglet actif */
  const curSel   = tab==='catalog'?catSel:tab==='ai'?aiSel:sel;
  const curRes   = tab==='catalog'?catProds:tab==='ai'?aiProds:results;
  const setCurSel= tab==='catalog'?setCatSel:tab==='ai'?setAiSel:setSel;
  function toggle(i){setCurSel(s=>({...s,[i]:!s[i]}));}
  function addSel(){
    const chosen=curRes.filter((_,i)=>curSel[i]);
    if(chosen.length)onAdd(chosen);
  }
  const nSel=Object.values(curSel).filter(Boolean).length;

  /* Filtre fournisseur appliqué à la recherche */
  useEffect(()=>{ if(q.trim()&&tab==='search') runSearch(q); },[suppFilter,sortBy]);

  /* Render produit */
  function ProductRow({p,i,selMap}){
    const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);
    const sup=p.suppliers?.[0]||{};
    const isSel=!!selMap[i];
    const [imgErr,setImgErr]=useState(false);
    return(
      <div onClick={()=>toggle(i)} style={{display:'flex',gap:10,padding:'9px 12px',borderRadius:10,border:`1.5px solid ${isSel?'#0ea5e9':'#e8edf3'}`,background:isSel?'rgba(14,165,233,.05)':'#fff',cursor:'pointer',alignItems:'flex-start',marginBottom:4,transition:'all .15s'}}>
        {/* Checkbox */}
        <div style={{width:18,height:18,border:`2px solid ${isSel?'#0ea5e9':'#bbb'}`,borderRadius:4,background:isSel?'#0ea5e9':'transparent',flexShrink:0,marginTop:2,display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',fontSize:11}}>{isSel&&'✓'}</div>
        {/* Image produit */}
        {p.image_url&&!imgErr
          ? <img src={p.image_url} alt="" onError={()=>setImgErr(true)} style={{width:52,height:52,objectFit:'contain',borderRadius:8,border:'1px solid #e2e8f0',background:'#f8fafc',flexShrink:0}} />
          : <div style={{width:52,height:52,borderRadius:8,border:'1px solid #e2e8f0',background:'#f8fafc',flexShrink:0,display:'flex',alignItems:'center',justifyContent:'center',fontSize:20,color:'#cbd5e1'}}>📦</div>
        }
        <div style={{flex:1,minWidth:0}}>
          <div style={{fontWeight:600,fontSize:13,color:'#1e293b',lineHeight:1.3}}>{p.name}</div>
          <div style={{fontSize:11,color:'#64748b',display:'flex',gap:8,flexWrap:'wrap',marginTop:3}}>
            {p.ref&&<span style={{background:'#f1f5f9',borderRadius:4,padding:'1px 6px'}}>Réf: {p.ref}</span>}
            {p.category&&<span style={{color:'#7c3aed'}}>📂 {p.category}</span>}
            {sup.name&&<span style={{color:'#0ea5e9'}}>🏭 {sup.name}</span>}
            {p.unit&&<span>{p.unit}</span>}
          </div>
          {p.description&&<div style={{fontSize:11,color:'#94a3b8',marginTop:2,fontStyle:'italic',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{p.description}</div>}
          {p.note&&<div style={{fontSize:11,color:'#94a3b8',marginTop:2,fontStyle:'italic'}}>{p.note}</div>}
        </div>
        {price>0&&<div style={{flexShrink:0,textAlign:'right'}}><div style={{fontWeight:700,fontSize:14,color:'#16a34a'}}>{price.toFixed(2)} €</div><div style={{fontSize:10,color:'#94a3b8'}}>HT</div></div>}
      </div>
    );
  }

  const TABS=[
    {k:'search', icon:'🔍', label:'Recherche'},
    {k:'catalog',icon:'📂', label:'Catalogue'},
    {k:'ai',     icon:'✨', label:'Suggestions IA'},
  ];

  return(
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.55)',zIndex:9990,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f8fafc',borderRadius:16,width:'min(780px,100%)',maxHeight:'94vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.25)',overflow:'hidden'}}>

        {/* Header */}
        <div style={{background:'#fff',padding:'14px 18px 10px',borderBottom:'1px solid #e2e8f0',display:'flex',gap:10,alignItems:'flex-start',flexShrink:0}}>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:15,color:'#1e293b'}}>🛒 Catalogue Pool Store</div>
            {item&&<div style={{fontSize:11,color:'#64748b',marginTop:2,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>Contexte : {item}</div>}
          </div>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d',flexShrink:0}}>✕</button>
        </div>

        {/* Onglets */}
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',display:'flex',flexShrink:0}}>
          {TABS.map(t=>(
            <button key={t.k} onClick={()=>setTab(t.k)}
              style={{padding:'9px 18px',border:'none',borderBottom:`3px solid ${tab===t.k?'#0ea5e9':'transparent'}`,background:'transparent',cursor:'pointer',fontWeight:tab===t.k?700:500,fontSize:13,color:tab===t.k?'#0ea5e9':'#64748b',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5}}>
              {t.icon} {t.label}
            </button>
          ))}
          {/* Filtre fournisseur (droite) */}
          <div style={{marginLeft:'auto',display:'flex',alignItems:'center',gap:6,padding:'0 14px'}}>
            <select value={suppFilter||''} onChange={e=>setSuppFilter(e.target.value||null)}
              style={{border:'1px solid #e2e8f0',borderRadius:7,padding:'4px 8px',fontSize:11,color:'#475569',background:'#fff',cursor:'pointer',outline:'none'}}>
              <option value="">Tous fournisseurs</option>
              {suppliers.slice(0,8).map(s=><option key={s.id} value={s.id}>{s.name} ({s.product_count})</option>)}
            </select>
            <select value={sortBy} onChange={e=>setSortBy(e.target.value)}
              style={{border:'1px solid #e2e8f0',borderRadius:7,padding:'4px 8px',fontSize:11,color:'#475569',background:'#fff',cursor:'pointer',outline:'none'}}>
              <option value="name">Nom A→Z</option>
              <option value="price_asc">Prix croissant</option>
              <option value="price_desc">Prix décroissant</option>
            </select>
          </div>
        </div>

        {/* Corps scroll */}
        <div style={{flex:1,overflowY:'auto',padding:'12px 14px',minHeight:0}}>

          {/* ── Onglet Recherche ── */}
          {tab==='search'&&(
            <div>
              <div style={{display:'flex',gap:8,marginBottom:12}}>
                <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==='Enter'&&runSearch(q)}
                  placeholder="Référence, nom produit, marque, catégorie…"
                  autoFocus
                  style={{flex:1,border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 14px',fontFamily:'inherit',fontSize:14,outline:'none',background:'#fff'}} />
                <button onClick={()=>runSearch(q)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'9px 18px',fontWeight:700,cursor:'pointer',fontSize:13,whiteSpace:'nowrap'}}>
                  {busy?'…':'Chercher'}
                </button>
              </div>
              {src&&src!=='empty'&&(
                <div style={{marginBottom:8,display:'flex',alignItems:'center',gap:8}}>
                  <span style={{fontSize:11,fontWeight:700,padding:'3px 9px',borderRadius:20,background:'#dcfce7',color:'#166534'}}>✅ {results.length} résultat{results.length>1?'s':''} — Catalogue Lolirine Pool Store</span>
                </div>
              )}
              {busy&&<div style={{padding:40,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:28,marginBottom:10}}>🔄</div>Recherche en cours…</div>}
              {!busy&&src==='empty'&&(
                <div style={{padding:32,textAlign:'center',color:'#94a3b8'}}>
                  <div style={{fontSize:32,marginBottom:8}}>🔍</div>
                  <div style={{fontSize:14,marginBottom:8}}>Aucun résultat dans le catalogue</div>
                  <button onClick={()=>setTab('ai')} style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#92400e',fontWeight:600}}>
                    ✨ Voir les suggestions IA
                  </button>
                </div>
              )}
              {!busy&&!src&&<div style={{padding:32,textAlign:'center',color:'#94a3b8',fontSize:13}}>Tapez votre recherche et appuyez Entrée</div>}
              {results.map((p,i)=><ProductRow key={i} p={p} i={i} selMap={sel} />)}
            </div>
          )}

          {/* ── Onglet Catalogue ── */}
          {tab==='catalog'&&(
            <div>
              {/* Breadcrumb */}
              <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:10,flexWrap:'wrap'}}>
                <span onClick={()=>{setCatPath([]);loadCategories(null);setCatProds([]);}} style={{fontSize:12,color:'#0ea5e9',cursor:'pointer',fontWeight:600}}>📂 Catalogue</span>
                {catPath.map((cat,i)=>(
                  <React.Fragment key={cat.id}>
                    <span style={{color:'#94a3b8',fontSize:12}}>›</span>
                    <span onClick={()=>{const np=catPath.slice(0,i+1);setCatPath(np);if(cat.has_children){loadCategories(cat.id);setCatProds([]);}else loadCategoryProducts(cat.id);}} style={{fontSize:12,color:i===catPath.length-1?'#1e293b':'#0ea5e9',cursor:'pointer',fontWeight:i===catPath.length-1?600:400}}>{cat.name}</span>
                  </React.Fragment>
                ))}
                {catPath.length>0&&<button onClick={upCat} style={{marginLeft:'auto',background:'none',border:'1px solid #e2e8f0',borderRadius:6,padding:'3px 10px',cursor:'pointer',fontSize:11,color:'#64748b'}}>← Retour</button>}
              </div>

              {catBusy&&<div style={{padding:40,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:28,marginBottom:10}}>🔄</div>Chargement…</div>}

              {/* Grille catégories */}
              {!catBusy&&categories.length>0&&(
                <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(170px,1fr))',gap:9,marginBottom:12}}>
                  {categories.map(cat=>(
                    <div key={cat.id} onClick={()=>drillCat(cat)}
                      style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'13px 14px',cursor:'pointer',transition:'all .15s'}}
                      onMouseEnter={e=>{e.currentTarget.style.borderColor='#0ea5e9';e.currentTarget.style.transform='translateY(-1px)';}}
                      onMouseLeave={e=>{e.currentTarget.style.borderColor='#e2e8f0';e.currentTarget.style.transform='none';}}>
                      <div style={{fontWeight:600,fontSize:13,color:'#1e293b',marginBottom:4,lineHeight:1.3}}>{cat.name}</div>
                      <div style={{fontSize:11,color:'#94a3b8',display:'flex',justifyContent:'space-between'}}>
                        <span>{cat.product_count} produit{cat.product_count>1?'s':''}</span>
                        {cat.has_children&&<span style={{color:'#0ea5e9'}}>→</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Produits de la catégorie sélectionnée */}
              {!catBusy&&catProds.length>0&&(
                <div>
                  <div style={{fontSize:12,color:'#64748b',marginBottom:8,fontWeight:600}}>{catProds.length} produit{catProds.length>1?'s':''}</div>
                  {catProds.map((p,i)=><ProductRow key={i} p={p} i={i} selMap={catSel} />)}
                </div>
              )}

              {!catBusy&&categories.length===0&&catProds.length===0&&(
                <div style={{padding:32,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucun contenu dans cette catégorie</div>
              )}
            </div>
          )}

          {/* ── Onglet IA ── */}
          {tab==='ai'&&(
            <div>
              <div style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:10,padding:'10px 14px',marginBottom:12,fontSize:12,color:'#92400e'}}>
                ✨ Suggestions générées par Claude AI en fonction du contexte de la check-list. Ces produits ne sont pas liés au catalogue Odoo — vérifiez la disponibilité.
              </div>
              {aiBusy&&<div style={{padding:40,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:28,marginBottom:10}}>✨</div>Génération des suggestions IA…</div>}
              {!aiBusy&&aiProds.length===0&&aiDone&&<div style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucune suggestion IA disponible.</div>}
              {!aiBusy&&!aiDone&&<div style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Chargement des suggestions…</div>}
              {aiProds.map((p,i)=><ProductRow key={i} p={p} i={i} selMap={aiSel} />)}
              {aiDone&&aiProds.length>0&&(
                <div style={{marginTop:10}}>
                  <button onClick={()=>{setAiDone(false);setAiProds([]);runAI();}} style={{background:'none',border:'1px solid #e2e8f0',borderRadius:8,padding:'6px 14px',cursor:'pointer',fontSize:12,color:'#64748b'}}>↺ Régénérer les suggestions</button>
                </div>
              )}
            </div>
          )}

        </div>{/* fin scroll */}

        {/* Footer */}
        <div style={{background:'#fff',borderTop:'1.5px solid #e2e8f0',padding:'11px 18px',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
          <span style={{fontSize:12,color:'#64748b',flex:1}}>{nSel>0?`${nSel} produit${nSel>1?'s':''} sélectionné${nSel>1?'s':''}`:''}</span>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#475569',fontWeight:600}}>Annuler</button>
          <button onClick={addSel} disabled={!nSel}
            style={{background:nSel?'#0ea5e9':'#cbd5e1',color:'#fff',border:'none',borderRadius:9,padding:'8px 22px',fontWeight:700,cursor:nSel?'pointer':'default',fontSize:13,whiteSpace:'nowrap'}}>
            Ajouter {nSel?`(${nSel})`:'la sélection'}
          </button>
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════
   ITEM SCHEMA DETECTION — détection automatique des champs
   à encoder par item de checklist
═══════════════════════════════════════════════════ */
const ITEM_SCHEMAS = {
  /* Mesures eau */
  ph:          { icon:'💧', title:'Mesure pH',           unit:'',     fields:[{k:'mesure',l:'Valeur mesurée',t:'number',step:.01,min:0,max:14,placeholder:'7.4'},{k:'cible',l:'Cible',t:'text',dfl:'7,2 – 7,6',ro:true},{k:'correction',l:'Correction apportée',t:'text'},{k:'produit',l:'Produit utilisé',t:'text'},{k:'dose',l:'Dose (g ou mL)',t:'number',step:.1}] },
  tac:         { icon:'💧', title:'Mesure TAC',          unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:1,placeholder:'100'},{k:'cible',l:'Cible',t:'text',dfl:'80 – 120 mg/L',ro:true},{k:'correction',l:'Correction',t:'text'},{k:'produit',l:'Produit (bicarbonate/CO2)',t:'text'},{k:'dose',l:'Dose',t:'number',step:.1}] },
  th:          { icon:'💧', title:'Mesure TH',           unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:1,placeholder:'200'},{k:'cible',l:'Cible',t:'text',dfl:'150 – 300 mg/L',ro:true},{k:'correction',l:'Correction',t:'text'}] },
  chlore:      { icon:'🧪', title:'Mesure Chlore',       unit:'mg/L', fields:[{k:'libre',l:'Chlore libre (mg/L)',t:'number',step:.01,placeholder:'2.0'},{k:'combine',l:'Chlore combiné (mg/L)',t:'number',step:.01,placeholder:'0.3'},{k:'cible',l:'Cible libre',t:'text',dfl:'1,0 – 3,0 mg/L',ro:true},{k:'produit',l:'Produit choc',t:'text'},{k:'dose',l:'Dose (g ou mL)',t:'number',step:.1}] },
  sel:         { icon:'🧂', title:'Taux de sel',         unit:'g/L',  fields:[{k:'mesure',l:'Taux mesuré (g/L)',t:'number',step:.1,placeholder:'5.0'},{k:'cible',l:'Cible électrolyseur',t:'number',step:.1,placeholder:'5.0'},{k:'correction',l:'Correction (kg sel)',t:'number',step:.5}] },
  cyanurate:   { icon:'☀️', title:'Cyanurate',           unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:1,placeholder:'40'},{k:'cible',l:'Cible max',t:'text',dfl:'< 75 mg/L',ro:true}] },
  phosphates:  { icon:'🌿', title:'Phosphates',          unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:.01,placeholder:'0.05'},{k:'cible',l:'Cible max',t:'text',dfl:'< 0,1 mg/L',ro:true},{k:'produit',l:'Anti-phosphates utilisé',t:'text'}] },
  temperature: { icon:'🌡️', title:'Température',        unit:'°C',   fields:[{k:'eau',l:'Température eau (°C)',t:'number',step:.5,placeholder:'24'},{k:'air',l:'Température air (°C)',t:'number',step:.5},{k:'turbidite',l:'Turbidité',t:'select',opts:['Limpide','Légèrement trouble','Trouble','Verte']}] },
  orp:         { icon:'⚡', title:'ORP / Redox',         unit:'mV',   fields:[{k:'mesure',l:'Valeur ORP (mV)',t:'number',step:1,placeholder:'700'},{k:'cible',l:'Cible',t:'text',dfl:'650 – 750 mV',ro:true}] },
  /* Équipements — nombres */
  skimmer:     { icon:'🔧', title:'Skimmers',           unit:'',     fields:[{k:'nombre',l:'Nombre de skimmers',t:'integer',min:1,max:10,placeholder:'2'},{k:'marque',l:'Marque / modèle',t:'text'},{k:'diam',l:'Largeur goulotte (mm)',t:'number',step:1,placeholder:'180'},{k:'etat',l:'État',t:'select',opts:['Bon état','Joint à remplacer','Collerette fissurée','À remplacer']}] },
  bonde:       { icon:'🔧', title:'Bondes de fond',    unit:'',     fields:[{k:'nombre',l:'Nombre de bondes',t:'integer',min:1,max:6,placeholder:'2'},{k:'marque',l:'Marque / modèle',t:'text'},{k:'etancheite',l:'Étanchéité',t:'select',opts:['OK','Suintement','Fuite','À remplacer']}] },
  refoulement: { icon:'🔧', title:'Refoulements',       unit:'',     fields:[{k:'nombre',l:'Nombre de refoulements',t:'integer',min:1,max:12,placeholder:'4'},{k:'emplacement',l:'Emplacement',t:'text',placeholder:'Fond + parois'},{k:'orientation',l:'Orientation',t:'select',opts:['Fixe','Orientable','Rotatif']}] },
  pompe:       { icon:'⚙️', title:'Pompe',              unit:'',     fields:[{k:'marque',l:'Marque / modèle',t:'text'},{k:'puissance',l:'Puissance (kW)',t:'number',step:.01,placeholder:'0.55'},{k:'debit',l:'Débit (m³/h)',t:'number',step:.5,placeholder:'10'},{k:'age',l:'Âge (années)',t:'integer',min:0,max:30},{k:'etat',l:'État général',t:'select',opts:['Bon état','Bruit','Vibration','Fuite','Hs']},{k:'pression',l:'Pression manomètre (bar)',t:'number',step:.1}] },
  filtre:      { icon:'🔵', title:'Filtre',             unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['Sable','Verre filtrant','Cartouche','Diatomées']},{k:'marque',l:'Marque / modèle',t:'text'},{k:'volume',l:'Volume filtrant (m³)',t:'number',step:.05,placeholder:'0.35'},{k:'pression',l:'Pression actuelle (bar)',t:'number',step:.05,placeholder:'0.8'},{k:'seuil',l:'Seuil contre-lavage (bar)',t:'number',step:.05,dfl:.5},{k:'media',l:'Média filtrant',t:'text',placeholder:'Sable 0,4–0,8 mm'}] },
  electrolyse: { icon:'⚡', title:'Électrolyseur',      unit:'',     fields:[{k:'marque',l:'Marque / modèle',t:'text'},{k:'capacite',l:'Capacité (m³)',t:'number',step:5,placeholder:'60'},{k:'production',l:'Production réglée (%)',t:'number',step:1,min:0,max:100,placeholder:'60'},{k:'etat_cellule',l:'État cellule',t:'select',opts:['Propre','Tartrée légère','Tartrée forte','Défaillante','À remplacer']},{k:'age_cellule',l:'Âge cellule (années)',t:'integer',min:0,max:10}] },
  pac:         { icon:'🌡️', title:'Pompe à chaleur',   unit:'',     fields:[{k:'marque',l:'Marque / modèle',t:'text'},{k:'puissance',l:'Puissance (kW)',t:'number',step:.5,placeholder:'12'},{k:'cop',l:'COP',t:'number',step:.1,placeholder:'5'},{k:'temp_consigne',l:'Température consigne (°C)',t:'number',step:.5,placeholder:'28'},{k:'etat',l:'État',t:'select',opts:['Fonctionnel','Bruit','Erreur affichée','Hors service']}] },
  /* Dimensions / surfaces */
  dimensions:  { icon:'📐', title:'Dimensions bassin',  unit:'',     fields:[{k:'longueur',l:'Longueur (m)',t:'number',step:.1,placeholder:'10'},{k:'largeur',l:'Largeur (m)',t:'number',step:.1,placeholder:'5'},{k:'prof_min',l:'Profondeur mini (m)',t:'number',step:.1,placeholder:'1.2'},{k:'prof_max',l:'Profondeur maxi (m)',t:'number',step:.1,placeholder:'2'},{k:'forme',l:'Forme',t:'select',opts:['Rectangulaire','Carré','L','Ovale','Haricot','Spa']}] },
  surface:     { icon:'📐', title:'Surface / Volume',   unit:'m²',   fields:[{k:'surface',l:'Surface (m²)',t:'number',step:.5},{k:'volume',l:'Volume (m³)',t:'number',step:.5},{k:'plage',l:'Surface plage (m²)',t:'number',step:.5}] },
  /* Traitements */
  traitement:  { icon:'💊', title:'Traitement appliqué',unit:'',     fields:[{k:'produit',l:'Produit utilisé',t:'text'},{k:'dose',l:'Dose (g / mL / L)',t:'number',step:.1},{k:'dilution',l:'Dilution préalable',t:'select',opts:['Non','Oui 10%','Oui 50%']},{k:'heure',l:'Heure application',t:'time'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Pression / débit */
  pression:    { icon:'🔵', title:'Pression',           unit:'bar',  fields:[{k:'pression',l:'Pression (bar)',t:'number',step:.05,placeholder:'0.8'},{k:'alarme',l:'Seuil alarme (bar)',t:'number',step:.05,placeholder:'1.5'},{k:'etat',l:'État',t:'select',opts:['Normal','Élevée — contre-lavage requis','Basse — contrôler pompe']}] },
  debit:       { icon:'💧', title:'Débit',              unit:'m³/h', fields:[{k:'debit',l:'Débit mesuré (m³/h)',t:'number',step:.5},{k:'debit_nominal',l:'Débit nominal (m³/h)',t:'number',step:.5},{k:'duree',l:'Durée filtration/jour (h)',t:'number',step:.5,placeholder:'8'}] },
  /* Planning / dates */
  date_prochaine: { icon:'📅', title:'Prochain passage',unit:'',    fields:[{k:'date',l:'Date prévue',t:'date'},{k:'type',l:'Type de passage',t:'select',opts:['Entretien standard','Analyse complète','Hivernage','Remise en route','Urgence']},{k:'technicien',l:'Technicien',t:'text'},{k:'notes',l:'Notes',t:'textarea'}] },
  /* Première mise en eau */
  mise_en_eau: { icon:'💧', title:'Première mise en eau',unit:'',   fields:[{k:'volume_rempli',l:'Volume rempli (m³)',t:'number',step:.5},{k:'duree_remplissage',l:'Durée remplissage (h)',t:'number',step:.5},{k:'turbidite',l:'Turbidité initiale',t:'select',opts:['Limpide','Légèrement trouble','Trouble']},{k:'choc_initial',l:'Choc chlore initial (g)',t:'number',step:50},{k:'ph_initial',l:'pH initial',t:'number',step:.01},{k:'sel_initial',l:'Sel initial (kg)',t:'number',step:5},{k:'floculation',l:'Floculation appliquée',t:'select',opts:['Non','Oui — floculant liquide','Oui — cartouche']},{k:'surveillance',l:'Durée surveillance (h)',t:'integer',min:1,max:72,placeholder:'24'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Éclairage */
  eclairage:   { icon:'💡', title:'Éclairage',          unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['LED RGB','LED blanc','Halogène (obsolète)','Fibre optique']},{k:'puissance',l:'Puissance (W)',t:'number',step:1},{k:'nombre',l:'Nombre',t:'integer',min:1,max:20},{k:'couleur',l:'Couleur / référence',t:'text'},{k:'etat',l:'État',t:'select',opts:['Fonctionnel','Défaillant','À remplacer']}] },
  /* Alarme / sécurité */
  alarme:      { icon:'🔔', title:'Alarme piscine',     unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['Détection de chute (immergé)','Détection de chute (barrière)','Barrière périmétrale','Couverture sécurisée']},{k:'marque',l:'Marque / modèle',t:'text'},{k:'norme',l:'Norme',t:'select',opts:['NF P 90-307 (chute)','NF P 90-308 (barrière)','NF P 90-306','Autre']},{k:'test',l:'Test fonctionnel',t:'select',opts:['OK','Défaillant — piles','Défaillant — capteur','Hors service']},{k:'date_test',l:'Date dernier test',t:'date'}] },
  /* Revêtement */
  revetement:  { icon:'🎨', title:'Revêtement',         unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['Liner PVC','Carrelage','Enduit hydraulique','Résine','Membrane armée','Béton brut']},{k:'age',l:'Âge (années)',t:'integer',min:0,max:30},{k:'etat',l:'État général',t:'select',opts:['Excellent','Bon','Usé','Fissuré','À remplacer']},{k:'surface',l:'Surface (m²)',t:'number',step:.5},{k:'couleur',l:'Couleur / référence',t:'text'}] },
  /* Câblage / électrique */
  electrique:  { icon:'⚡', title:'Installation électrique',unit:'', fields:[{k:'coffret',l:'Coffret IP',t:'select',opts:['IP65','IP66','IP54','Autre']},{k:'diff',l:'Disjoncteur différentiel 30mA',t:'select',opts:['Présent et testé','Présent — non testé','Absent']},{k:'equi',l:'Liaison équipotentielle',t:'select',opts:['Conforme','Non vérifiée','Non conforme']},{k:'section',l:'Section câbles (mm²)',t:'number',step:.5,placeholder:'2.5'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Générique texte */
  texte:       { icon:'✏️', title:'Informations',       unit:'',     fields:[{k:'valeur',l:'Valeur / Information',t:'text'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Générique nombre */
  nombre:      { icon:'🔢', title:'Quantité / Valeur',  unit:'',     fields:[{k:'valeur',l:'Valeur',t:'number',step:.01},{k:'unite',l:'Unité',t:'text'},{k:'observations',l:'Notes',t:'text'}] },
};

/* Détection automatique du schéma à partir du texte de l'item */
function detectSchema(text) {
  const t = text.toLowerCase();
  if (t.match(/\bph\b.*(?:mesur|cible|7[,.]2)/)) return 'ph';
  if (t.match(/\btac\b|alcalinité/)) return 'tac';
  if (t.match(/\bth\b|dureté/)) return 'th';
  if (t.match(/chlore/)) return 'chlore';
  if (t.match(/\bsel\b.*(?:électrolys|g\/l|mesur)/)) return 'sel';
  if (t.match(/cyanurate/)) return 'cyanurate';
  if (t.match(/phosphate/)) return 'phosphates';
  if (t.match(/température.*eau|°c/)) return 'temperature';
  if (t.match(/\borp\b|redox/)) return 'orp';
  if (t.match(/skimmer/)) return 'skimmer';
  if (t.match(/bonde.*fond|fond.*bonde/)) return 'bonde';
  if (t.match(/refoulement/)) return 'refoulement';
  if (t.match(/pompe.*(?:marque|modèle|kw|m³\/h|puissance|âge)/)) return 'pompe';
  if (t.match(/filtre.*(?:sable|cartouche|volume|média|pression)/)) return 'filtre';
  if (t.match(/électrolyseur|electrolyse/)) return 'electrolyse';
  if (t.match(/pompe à chaleur|pac\b/)) return 'pac';
  if (t.match(/dimensions?.*(?:l\s*[×x]|prof)/i) || t.match(/l\s*[×x]\s*l\s*[×x]\s*prof/i)) return 'dimensions';
  if (t.match(/surface.*m²|volume.*m³/)) return 'surface';
  if (t.match(/pression.*(?:manomètre|bar)/)) return 'pression';
  if (t.match(/débit.*m³\/h/)) return 'debit';
  if (t.match(/prochain.*passage|prochain.*contre-lavage|prochaine.*visite/)) return 'date_prochaine';
  if (t.match(/première mise en eau|mise en eau.*contrôlée|remplissage.*contrôlé/)) return 'mise_en_eau';
  if (t.match(/projecteur|éclairage|led.*subaquatique/)) return 'eclairage';
  if (t.match(/alarme.*piscine|détection/)) return 'alarme';
  if (t.match(/revêtement|liner|carrelage/)) return 'revetement';
  if (t.match(/coffret|disjoncteur|équipotentielle|câbl/)) return 'electrique';
  if (t.match(/traitement.*(?:correctif|appliqué|choc)|choc.*chlore|algicide|floculant/)) return 'traitement';
  if (t.match(/nombre\s*[_:]/i) || t.match(/nombre\s+___/i)) return 'nombre';
  if (t.match(/______+|___\s*$/)) return 'texte';
  return null;
}

/* ═══════════════════════════════════════════════════
   ItemDetailModal — fenêtre d'encodage contextuelle
═══════════════════════════════════════════════════ */
function ItemDetailModal({ item, schemaKey, savedValues, onSave, onClose }) {
  const schema = ITEM_SCHEMAS[schemaKey] || ITEM_SCHEMAS.texte;
  const [vals, setVals] = useState(() => {
    const init = {};
    schema.fields.forEach(f => { init[f.k] = (savedValues && savedValues[f.k] !== undefined) ? savedValues[f.k] : (f.dfl || ''); });
    return init;
  });

  function set(k, v) { setVals(s => ({...s, [k]: v})); }

  /* Calculs dérivés en temps réel */
  const derived = {};
  if (schemaKey === 'dimensions' && vals.longueur && vals.largeur) {
    derived.surface = (parseFloat(vals.longueur) * parseFloat(vals.largeur)).toFixed(1);
    if (vals.prof_max) derived.volume = (parseFloat(vals.longueur) * parseFloat(vals.largeur) * parseFloat(vals.prof_max) * 0.8).toFixed(1);
  }
  if (schemaKey === 'ph' || schemaKey === 'tac' || schemaKey === 'th' || schemaKey === 'sel') {
    const mesure = parseFloat(vals.mesure || vals.mesure);
    if (!isNaN(mesure)) {
      const ranges = {ph:[7.2,7.6], tac:[80,120], th:[150,300], sel:[4.5,5.5]};
      const r = ranges[schemaKey];
      if (r) derived.statut = mesure < r[0] ? '📉 En dessous — correction nécessaire' : mesure > r[1] ? '📈 Au-dessus — correction nécessaire' : '✅ Dans la plage cible';
    }
  }

  const IS = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 12px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'};

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.55)',zIndex:9998,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#fff',borderRadius:16,width:'min(620px,100%)',maxHeight:'90vh',display:'flex',flexDirection:'column',boxShadow:'0 24px 80px rgba(0,0,0,.25)',overflow:'hidden'}}>
        {/* Header */}
        <div style={{background:'#0ea5e9',padding:'14px 18px',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
          <span style={{fontSize:22}}>{schema.icon}</span>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:16,color:'#fff'}}>{schema.title}</div>
            <div style={{fontSize:11,color:'rgba(255,255,255,.75)',marginTop:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{item}</div>
          </div>
          <button onClick={onClose} style={{background:'rgba(255,255,255,.2)',border:'none',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:13,color:'#fff'}}>✕</button>
        </div>
        {/* Corps */}
        <div style={{overflowY:'auto',padding:'18px 20px',display:'flex',flexDirection:'column',gap:14}}>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
            {schema.fields.map(f => (
              <div key={f.k} style={{gridColumn:f.t==='textarea'?'1/-1':undefined}}>
                <label style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',display:'block',marginBottom:4}}>{f.l}{f.unit?` (${f.unit})`:''}</label>
                {f.t === 'select' ? (
                  <select value={vals[f.k]||''} onChange={e=>set(f.k,e.target.value)} style={{...IS,background:'#fff',cursor:'pointer'}}>
                    <option value="">— Choisir —</option>
                    {(f.opts||[]).map(o=><option key={o} value={o}>{o}</option>)}
                  </select>
                ) : f.t === 'textarea' ? (
                  <textarea value={vals[f.k]||''} onChange={e=>set(f.k,e.target.value)} rows={3} placeholder={f.placeholder||''} style={{...IS,resize:'vertical',lineHeight:1.5}} />
                ) : (
                  <input type={f.t==='integer'?'number':f.t||'text'} value={vals[f.k]||''} onChange={e=>set(f.k,e.target.value)}
                    readOnly={f.ro} min={f.min} max={f.max} step={f.step} placeholder={f.placeholder||f.dfl||''}
                    style={{...IS,background:f.ro?'#f8fafc':'#fff',color:f.ro?'#94a3b8':'#1e293b'}} />
                )}
              </div>
            ))}
          </div>
          {/* Calculs dérivés */}
          {Object.keys(derived).length > 0 && (
            <div style={{background:'#eff9ff',borderRadius:10,padding:'12px 16px',display:'flex',gap:16,flexWrap:'wrap'}}>
              {derived.surface && <div style={{fontSize:13,color:'#0369a1'}}><strong>Surface :</strong> {derived.surface} m²</div>}
              {derived.volume  && <div style={{fontSize:13,color:'#0369a1'}}><strong>Volume estimé :</strong> {derived.volume} m³</div>}
              {derived.statut  && <div style={{fontSize:13,fontWeight:600,color:derived.statut.startsWith('✅')?'#16a34a':'#e24b4a'}}>{derived.statut}</div>}
            </div>
          )}
        </div>
        {/* Footer */}
        <div style={{padding:'12px 20px',borderTop:'1px solid #f0f4f8',display:'flex',justifyContent:'flex-end',gap:9,flexShrink:0}}>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#475569',fontWeight:600}}>Annuler</button>
          <button onClick={()=>onSave(vals)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'8px 22px',fontWeight:700,fontSize:13,cursor:'pointer'}}>💾 Enregistrer</button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   PlanningModal — planning prévisionnel par type
═══════════════════════════════════════════════════ */
const PLANNING_TEMPLATES = {
  construction: [
    {phase:'Études & préparation',    days:7,  color:'#7c3aed', tasks:['Étude de sol','Validation devis','Obtention permis','Commande matériaux']},
    {phase:'Terrassement & VRD',      days:5,  color:'#0ea5e9', tasks:['Terrassement','Voirie & réseaux','Coffrage fond']},
    {phase:'Génie civil',             days:10, color:'#0369a1', tasks:['Coulage béton','Pose armatures','Étanchéité primaire']},
    {phase:'Plomberie & hydraulique', days:5,  color:'#16a34a', tasks:['Tuyauteries','Pose skimmers & bondes','Raccordements']},
    {phase:'Électricité & éclairage', days:4,  color:'#f59e0b', tasks:['Câblage','Coffret IP65','Projecteurs LED','Équipotentielle']},
    {phase:'Revêtement & finitions',  days:6,  color:'#ef4444', tasks:['Pose liner/carrelage','Margelles','Plage','Douche']},
    {phase:'Équipements filtration',  days:3,  color:'#8b5cf6', tasks:['Local technique','Pompe/filtre','Électrolyseur']},
    {phase:'Mise en eau & réglages',  days:3,  color:'#0ea5e9', tasks:['Remplissage','Analyses','Paramétrage','Formation client']},
  ],
  renovation: [
    {phase:'Diagnostic complet',      days:1,  color:'#7c3aed', tasks:['Inspection structure','Test étanchéité','Rapport diagnostic']},
    {phase:'Vidange & préparation',   days:2,  color:'#0ea5e9', tasks:['Vidange bassin','Nettoyage fond','Dépose revêtement']},
    {phase:'Travaux structure',       days:5,  color:'#ef4444', tasks:['Reprise fissures','Traitement armatures','Enduit de fond']},
    {phase:'Nouveau revêtement',      days:4,  color:'#16a34a', tasks:['Pose liner/carrelage/résine','Scellements','Joints']},
    {phase:'Équipements',             days:3,  color:'#f59e0b', tasks:['Pompe','Filtre','Électrolyseur','Éclairage']},
    {phase:'Remise en eau',           days:2,  color:'#0369a1', tasks:['Remplissage','Analyses','Réglages','Réception']},
  ],
  entretien: [
    {phase:'Analyse & mesures',       days:0.1, color:'#0ea5e9', tasks:['pH, TAC, TH, Chlore','Sel, Cyanurate, Phosphates','Turbidité']},
    {phase:'Nettoyage',               days:0.2, color:'#16a34a', tasks:['Aspiration fond','Brossage parois','Skimmers & préfiltre']},
    {phase:'Filtration',              days:0.1, color:'#7c3aed', tasks:['Contre-lavage si nécessaire','Vérif équipements']},
    {phase:'Traitements correctifs',  days:0.1, color:'#f59e0b', tasks:['Corrections mesures','Choc chlore si besoin']},
    {phase:'Rapport',                 days:0.1, color:'#64748b', tasks:['Rapport envoyé client','Recommandations']},
  ],
  hivernage: [
    {phase:'Traitement eau',          days:1,  color:'#0ea5e9', tasks:['Analyse complète','Choc chlore','Algicide hivernage']},
    {phase:'Mise hors service',       days:1,  color:'#64748b', tasks:['Vidange pompe/filtre','Tuyauteries','Débranchement']},
    {phase:'Protection gel',          days:0.5,color:'#3b82f6', tasks:['Flotteurs anti-gel','Isolation','Local technique']},
    {phase:'Couverture & sécurité',   days:0.5,color:'#8b5cf6', tasks:['Pose couverture','Filet','Alarme']},
  ],
  remise_en_route: [
    {phase:'Nettoyage général',       days:0.5,color:'#16a34a', tasks:['Retrait couverture','Nettoyage bassin','Local technique']},
    {phase:'Remontage équipements',   days:1,  color:'#0ea5e9', tasks:['Pompe','Sondes','Électrolyseur','Raccordements']},
    {phase:'Mise en eau',             days:1,  color:'#0369a1', tasks:['Remplissage','Test étanchéité']},
    {phase:'Analyses & réglages',     days:1,  color:'#f59e0b', tasks:['Analyses complètes','Réglages équipements','Filtration 48h']},
  ],
  materiel: [
    {phase:'Commande fournisseur',    days:5,  color:'#7c3aed', tasks:['Confirmation devis','Bon de commande','Confirmation délai']},
    {phase:'Réception matériel',      days:1,  color:'#0ea5e9', tasks:['Contrôle livraison','Vérification conformité']},
    {phase:'Démontage ancien',        days:0.5,color:'#ef4444', tasks:["Dépose ancien matériel","Mise hors service","Évacuation"]},
    {phase:'Installation',            days:1,  color:'#16a34a', tasks:['Pose nouveau matériel','Raccordements','Câblage']},
    {phase:'Mise en service',         days:0.5,color:'#f59e0b', tasks:['Tests','Réglages','Formation client','Réception']},
  ],
};

function PlanningModal({ type, clientName, startDate, onClose }) {
  const template = PLANNING_TEMPLATES[type] || PLANNING_TEMPLATES.entretien;
  const [start, setStart] = useState(startDate || new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');

  const totalDays = template.reduce((a,p) => a + p.days, 0);

  /* Calculer les dates de chaque phase */
  const phases = [];
  let cursor = new Date(start);
  template.forEach(p => {
    const s = new Date(cursor);
    const e = new Date(cursor);
    e.setDate(e.getDate() + Math.ceil(p.days));
    // Sauter les week-ends
    while (e.getDay() === 0 || e.getDay() === 6) e.setDate(e.getDate() + 1);
    phases.push({...p, startDate: new Date(s), endDate: new Date(e)});
    cursor = new Date(e);
    cursor.setDate(cursor.getDate() + 1);
  });

  const projectEnd = phases[phases.length-1]?.endDate;
  const fmt = d => d?.toLocaleDateString('fr-BE',{day:'2-digit',month:'2-digit',year:'2-digit'}) || '';

  function exportPDF() { window.print(); }

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.55)',zIndex:9997,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f8fafc',borderRadius:16,width:'min(820px,100%)',maxHeight:'92vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.25)',overflow:'hidden'}}>

        {/* Header */}
        <div style={{background:'#1e293b',padding:'14px 20px',display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
          <span style={{fontSize:24}}>📅</span>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:16,color:'#fff'}}>Planning prévisionnel</div>
            <div style={{fontSize:11,color:'rgba(255,255,255,.6)',marginTop:1}}>{clientName||'Client'} · {totalDays} jours ouvrés · Fin estimée : {fmt(projectEnd)}</div>
          </div>
          <button onClick={exportPDF} style={{background:'rgba(255,255,255,.1)',border:'1px solid rgba(255,255,255,.3)',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:12,color:'#fff'}}>🖨️ PDF</button>
          <button onClick={onClose} style={{background:'rgba(255,255,255,.2)',border:'none',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:13,color:'#fff'}}>✕</button>
        </div>

        <div style={{overflowY:'auto',flex:1,padding:'18px 20px'}}>

          {/* Date de début */}
          <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'14px 18px',marginBottom:16,display:'flex',gap:16,alignItems:'center',flexWrap:'wrap'}}>
            <div>
              <label style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',display:'block',marginBottom:4}}>Date de début</label>
              <input type="date" value={start} onChange={e=>setStart(e.target.value)}
                style={{border:'1.5px solid #dde4ed',borderRadius:8,padding:'7px 12px',fontFamily:'inherit',fontSize:14,outline:'none'}} />
            </div>
            <div style={{flex:1,display:'flex',gap:10,flexWrap:'wrap'}}>
              <div style={{background:'#eff9ff',borderRadius:9,padding:'8px 14px',fontSize:12}}>
                <div style={{fontWeight:700,color:'#0369a1'}}>Début</div>
                <div style={{color:'#475569'}}>{fmt(new Date(start))}</div>
              </div>
              <div style={{background:'#f0fdf4',borderRadius:9,padding:'8px 14px',fontSize:12}}>
                <div style={{fontWeight:700,color:'#16a34a'}}>Fin estimée</div>
                <div style={{color:'#475569'}}>{fmt(projectEnd)}</div>
              </div>
              <div style={{background:'#f8fafc',borderRadius:9,padding:'8px 14px',fontSize:12}}>
                <div style={{fontWeight:700,color:'#475569'}}>Durée totale</div>
                <div style={{color:'#64748b'}}>{totalDays} jours ouvrés</div>
              </div>
            </div>
          </div>

          {/* Gantt simplifié */}
          <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',marginBottom:16,overflow:'hidden'}}>
            <div style={{background:'#f8fafc',padding:'10px 16px',borderBottom:'1px solid #e2e8f0',fontWeight:700,fontSize:13,color:'#1e293b',display:'flex',gap:16}}>
              <span style={{width:180,flexShrink:0}}>Phase</span>
              <span style={{flex:1}}>Timeline</span>
              <span style={{width:140,textAlign:'right',flexShrink:0}}>Dates</span>
            </div>
            {phases.map((p,i)=>{
              const pct = Math.max(5, Math.round(p.days / totalDays * 100));
              return (
                <div key={i} style={{borderTop:i>0?'1px solid #f8fafc':'none',padding:'10px 16px',display:'flex',gap:16,alignItems:'center'}}>
                  <div style={{width:180,flexShrink:0}}>
                    <div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{p.phase}</div>
                    <div style={{fontSize:11,color:'#94a3b8',marginTop:1}}>{p.days < 1 ? Math.round(p.days*8)+'h' : p.days+' j'}</div>
                  </div>
                  <div style={{flex:1,display:'flex',alignItems:'center',gap:6}}>
                    <div style={{height:20,background:p.color,borderRadius:4,width:`${pct}%`,minWidth:30,display:'flex',alignItems:'center',padding:'0 8px'}}>
                      <span style={{fontSize:10,color:'#fff',fontWeight:600,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{p.days < 1 ? '' : p.phase.split(' ')[0]}</span>
                    </div>
                  </div>
                  <div style={{width:140,textAlign:'right',fontSize:11,color:'#64748b',flexShrink:0}}>
                    {fmt(p.startDate)} → {fmt(p.endDate)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Détail des tâches par phase */}
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(250px,1fr))',gap:10,marginBottom:16}}>
            {phases.map((p,i)=>(
              <div key={i} style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',overflow:'hidden'}}>
                <div style={{background:p.color,padding:'8px 12px',display:'flex',alignItems:'center',gap:8}}>
                  <div style={{flex:1,fontWeight:700,fontSize:12,color:'#fff'}}>{p.phase}</div>
                  <div style={{fontSize:10,color:'rgba(255,255,255,.8)',background:'rgba(255,255,255,.15)',borderRadius:4,padding:'2px 6px',whiteSpace:'nowrap'}}>{fmt(p.startDate)}</div>
                </div>
                <div style={{padding:'8px 12px'}}>
                  {(p.tasks||[]).map((t,j)=>(
                    <div key={j} style={{fontSize:12,color:'#475569',padding:'3px 0',display:'flex',alignItems:'center',gap:7,borderBottom:j<p.tasks.length-1?'1px solid #f8fafc':'none'}}>
                      <div style={{width:6,height:6,borderRadius:'50%',background:p.color,flexShrink:0}} />
                      {t}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Notes */}
          <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'14px 18px'}}>
            <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:8}}>📝 Notes & conditions particulières</div>
            <textarea value={notes} onChange={e=>setNotes(e.target.value)} rows={3}
              placeholder="Conditions d'accès, contraintes météo, disponibilités client, matériaux à confirmer…"
              style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:'inherit',fontSize:13,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} />
          </div>
        </div>

        {/* Footer */}
        <div style={{padding:'12px 20px',borderTop:'1px solid #e2e8f0',background:'#fff',display:'flex',justifyContent:'flex-end',gap:9,flexShrink:0}}>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#475569',fontWeight:600}}>Fermer</button>
          <button onClick={exportPDF} style={{background:'#1e293b',color:'#fff',border:'none',borderRadius:9,padding:'8px 22px',fontWeight:700,fontSize:13,cursor:'pointer'}}>🖨️ Imprimer le planning</button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SectionBlock — ring progress + badges colorés
   Utilise ItemRow pour éviter les IIFE non supportées
   par Babel standalone
═══════════════════════════════════════════════════ */

/* Sous-composant ItemRow — évite les IIFE dans le map */
function ItemRow({ item, i, stateVal, itemData, photos, fileInputRef,
                   onSetState, onOpenProducts, onSetItemData, onSetNote, noteVal,
                   onSetPhoto, filterStatus, searchText }) {
  const s           = stateVal || '';
  const schemaKey   = detectSchema(item);
  const savedVals   = itemData && itemData[i];
  const hasData     = savedVals && Object.values(savedVals).some(v => v !== '' && v !== undefined);
  const photoList   = photos || [];
  const isCountItem = !!item.toLowerCase().match(/nombre\s*[_:]/i);
  const [qty, setQty] = React.useState('');
  const [showDetail, setShowDetail] = React.useState(false);

  const borderColor = s==='ok'?'#16a34a':s==='warn'?'#f59e0b':s==='bad'?'#ef4444':'#e2e8f0';
  const bgColor     = s==='ok'?'rgba(22,163,74,.04)':s==='warn'?'rgba(245,158,11,.04)':s==='bad'?'rgba(239,68,68,.04)':'transparent';
  const textColor   = s==='ok'?'#3b6d11':s==='warn'?'#854f0b':s==='bad'?'#a32d2d':'#334155';

  /* Résumé des valeurs saisies */
  const dataSummary = hasData
    ? Object.values(savedVals).filter(v=>v&&v!=='').slice(0,3).join(' · ')
    : null;

  /* Filtre de visibilité */
  if (searchText && !item.toLowerCase().includes(searchText.toLowerCase())) return null;
  if (filterStatus && filterStatus !== 'all') {
    if (filterStatus==='ok'      && s!=='ok')    return null;
    if (filterStatus==='warn'    && s!=='warn')  return null;
    if (filterStatus==='bad'     && s!=='bad')   return null;
    if (filterStatus==='untreated' && s!=='')    return null;
  }

  function handlePhoto(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      onSetPhoto(i, ev.target.result);
      if (!s) onSetState(i, 'ok');
    };
    reader.readAsDataURL(file);
  }

  return (
    <div>
      <div style={{padding:'6px 14px 6px 11px',borderTop:'1px solid #f8fafc',display:'flex',alignItems:'center',gap:7,borderLeft:`3px solid ${borderColor}`,background:bgColor,transition:'all .2s'}}>
        <input type="checkbox" checked={s!==''} onChange={()=>onSetState(i, s?null:'ok')}
          style={{width:14,height:14,accentColor:'#0ea5e9',cursor:'pointer',flexShrink:0}} />
        <button title="OK / Conforme" onClick={()=>onSetState(i, s==='ok'?null:'ok')}
          style={{width:22,height:22,borderRadius:5,border:'none',cursor:'pointer',fontSize:13,
            background:s==='ok'?'#16a34a':'#f0fdf4',flexShrink:0,
            display:'flex',alignItems:'center',justifyContent:'center'}}>✅</button>
        <button title="Attention" onClick={()=>onSetState(i, s==='warn'?null:'warn')}
          style={{width:22,height:22,borderRadius:5,border:'none',cursor:'pointer',fontSize:13,
            background:s==='warn'?'#f59e0b':'#fffbeb',flexShrink:0,
            display:'flex',alignItems:'center',justifyContent:'center'}}>⚠️</button>
        <button title="Problème" onClick={()=>onSetState(i, s==='bad'?null:'bad')}
          style={{width:22,height:22,borderRadius:5,border:'none',cursor:'pointer',fontSize:13,
            background:s==='bad'?'#ef4444':'#fef2f2',flexShrink:0,
            display:'flex',alignItems:'center',justifyContent:'center'}}>❌</button>

        {/* Texte + résumé */}
        <div style={{flex:1,minWidth:0}}>
          <span style={{fontSize:12.5,color:textColor,textDecoration:s==='ok'?'line-through':'none',lineHeight:1.4}}>
            {item.replace(/_{3,}/g,'').replace(/:\s*$/,'').trim()}
          </span>
          {dataSummary && (
            <div style={{fontSize:10,fontWeight:600,marginTop:1,
              color:s==='ok'?'#16a34a':s==='warn'?'#f59e0b':s==='bad'?'#ef4444':'#0ea5e9'}}>
              → {dataSummary}
            </div>
          )}
        </div>

        {/* Quantité inline pour items "nombre :" */}
        {isCountItem && (
          <input type="number" min={0} max={99} value={qty}
            onChange={e=>setQty(e.target.value)}
            placeholder="Nb" onClick={e=>e.stopPropagation()}
            style={{width:50,border:`1.5px solid ${borderColor==='#e2e8f0'?'#e2e8f0':borderColor}`,
              borderRadius:6,padding:'2px 6px',fontFamily:'inherit',fontSize:12,
              textAlign:'center',outline:'none',flexShrink:0}} />
        )}

        {/* Bouton 📝 encodage détaillé */}
        {schemaKey && (
          <button title="Encoder les informations" onClick={e=>{e.stopPropagation();setShowDetail(true);}}
            style={{background:hasData?'#eff9ff':'none',border:`1.5px solid ${hasData?'#0ea5e9':'#e2e8f0'}`,
              borderRadius:5,padding:'2px 8px',cursor:'pointer',fontSize:12,
              color:hasData?'#0ea5e9':'#94a3b8',flexShrink:0,fontWeight:hasData?700:400}}>
            {hasData?'📝 ✓':'📝'}
          </button>
        )}

        {/* Photo */}
        <button title="Photo" onClick={e=>{e.stopPropagation();fileInputRef&&fileInputRef.click();}}
          style={{background:photoList.length>0?'#eff9ff':'none',
            border:`1px solid ${photoList.length>0?'#0ea5e9':'#e2e8f0'}`,
            borderRadius:5,padding:'2px 7px',cursor:'pointer',fontSize:11,
            color:photoList.length>0?'#0ea5e9':'#94a3b8',flexShrink:0,whiteSpace:'nowrap'}}>
          📷{photoList.length>0?` ${photoList.length}`:''}
        </button>
        <input ref={el=>{if(fileInputRef!==undefined)fileInputRef=el;}} type="file"
          accept="image/*" capture="environment"
          onChange={handlePhoto} style={{display:'none'}}
          id={`photo-input-${i}`} />

        {/* Produits */}
        <button title="Produits" onClick={e=>{e.stopPropagation();onOpenProducts(item);}}
          style={{background:s==='bad'?'#fef2f2':s==='warn'?'#fffbeb':'none',
            border:`1px solid ${s==='bad'?'#fca5a5':s==='warn'?'#fcd34d':'#e2e8f0'}`,
            borderRadius:5,padding:'2px 7px',cursor:'pointer',fontSize:13,
            color:s==='bad'?'#ef4444':s==='warn'?'#f59e0b':'#94a3b8',flexShrink:0}}>🛒</button>

        {/* Note */}
        <input value={noteVal||''} onChange={e=>{e.stopPropagation();onSetNote(i,e.target.value);}}
          placeholder="Note…"
          style={{width:80,border:`1px solid ${s==='bad'?'#fca5a5':s==='warn'?'#fcd34d':'#e8edf3'}`,
            borderRadius:5,padding:'2px 7px',fontFamily:'inherit',fontSize:11,
            outline:'none',color:textColor,background:'transparent',flexShrink:0}}
          onClick={e=>e.stopPropagation()} />
      </div>

      {/* Fenêtre d'encodage contextuelle */}
      {showDetail && schemaKey && (
        <ItemDetailModal
          item={item}
          schemaKey={schemaKey}
          savedValues={savedVals}
          onSave={vals=>{
            if(onSetItemData) onSetItemData(i, vals);
            if(!s) onSetState(i, 'ok');
            setShowDetail(false);
          }}
          onClose={()=>setShowDetail(false)}
        />
      )}
    </div>
  );
}

function SectionBlock({ section, items, state, onSetState, onOpenProducts,
                        filterStatus, searchText, itemData, onSetItemData }) {
  const [open, setOpen]   = useState(true);
  const [notes, setNotes] = useState({});
  const [photos, setPhotos] = useState({});
  const fileRefs = useRef({});

  const done  = items.filter((_,i) => (state[i]||'') !== '').length;
  const nOk   = items.filter((_,i) => state[i]==='ok').length;
  const nWarn = items.filter((_,i) => state[i]==='warn').length;
  const nBad  = items.filter((_,i) => state[i]==='bad').length;
  const pct   = items.length ? Math.round(done/items.length*100) : 0;
  const circ  = 2*Math.PI*15;
  const dash  = circ*pct/100;
  const ringColor = pct===100?'#16a34a':nBad>0?'#e24b4a':nWarn>0?'#f59e0b':'#0ea5e9';

  /* Visible selon les filtres actifs */
  const visibleItems = items.filter((item,i) => {
    const s = state[i] || '';
    if (searchText && !item.toLowerCase().includes(searchText.toLowerCase())) return false;
    if (!filterStatus || filterStatus==='all') return true;
    if (filterStatus==='ok')       return s==='ok';
    if (filterStatus==='warn')     return s==='warn';
    if (filterStatus==='bad')      return s==='bad';
    if (filterStatus==='untreated')return s==='';
    return true;
  });

  if (visibleItems.length === 0) return null;

  return (
    <div style={{background:'#fff',borderRadius:13,border:'1.5px solid #e2e8f0',marginBottom:12,overflow:'hidden'}}>
      {/* Header section */}
      <div onClick={()=>setOpen(o=>!o)}
        style={{padding:'11px 16px',display:'flex',alignItems:'center',gap:12,cursor:'pointer',userSelect:'none',background:'#f8fafc'}}>
        <svg width="38" height="38" viewBox="0 0 38 38" style={{flexShrink:0}}>
          <circle cx="19" cy="19" r="15" fill="none" stroke="#e2e8f0" strokeWidth="3"/>
          <circle cx="19" cy="19" r="15" fill="none" stroke={ringColor} strokeWidth="3"
            strokeDasharray={`${dash} ${circ-dash}`} strokeDashoffset={circ*0.25}
            strokeLinecap="round"/>
          <text x="19" y="23" textAnchor="middle" fontSize="9" fontWeight="700" fill={ringColor}>{pct}%</text>
        </svg>
        <div style={{flex:1,minWidth:0}}>
          <div style={{fontWeight:700,fontSize:14,color:'#1e293b'}}>{section}</div>
          <div style={{fontSize:11,color:'#64748b',marginTop:2}}>
            {done}/{items.length} points traités{nBad>0?` — ${nBad} problème${nBad>1?'s':''}`:''}</div>
        </div>
        <div style={{display:'flex',gap:4,flexShrink:0}}>
          {nOk>0&&<span style={{background:'#eaf3de',color:'#3b6d11',borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:600}}>{nOk} ok</span>}
          {nWarn>0&&<span style={{background:'#faeeda',color:'#854f0b',borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:600}}>{nWarn} attn</span>}
          {nBad>0&&<span style={{background:'#fcebeb',color:'#a32d2d',borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:600}}>{nBad} pb</span>}
        </div>
        <span style={{fontSize:11,color:'#94a3b8',flexShrink:0}}>{open?'▲':'▼'}</span>
      </div>

      {/* Items */}
      {open && (
        <div style={{padding:'2px 0 6px'}}>
          {items.map((item,i) => (
            <ItemRow key={i}
              item={item} i={i}
              stateVal={state[i]||''}
              itemData={itemData}
              photos={photos[i]}
              fileInputRef={fileRefs.current[i]}
              noteVal={notes[i]}
              filterStatus={filterStatus}
              searchText={searchText}
              onSetState={onSetState}
              onOpenProducts={(it)=>onOpenProducts(it,section)}
              onSetItemData={onSetItemData}
              onSetNote={(idx,v)=>setNotes(n=>({...n,[idx]:v}))}
              onSetPhoto={(idx,src)=>{
                setPhotos(p=>({...p,[idx]:[...(p[idx]||[]),src]}));
              }}
            />
          ))}
          {/* Miniatures photos */}
          {Object.values(photos).some(arr=>arr&&arr.length>0) && (
            <div style={{padding:'8px 14px',borderTop:'1px solid #f0f4f8',display:'flex',gap:6,flexWrap:'wrap'}}>
              {Object.entries(photos).flatMap(([k,imgs])=>(imgs||[]).map((src,j)=>(
                <img key={k+'-'+j} src={src} alt=""
                  style={{width:44,height:44,objectFit:'cover',borderRadius:6,border:'1.5px solid #e2e8f0',cursor:'pointer'}}
                  onClick={()=>window.open(src,'_blank')} />
              )))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════
   QuoteModal — devis style Odoo (4 onglets)
═══════════════════════════════════════════════════ */
const EVAC_OPT=[{key:'client',label:'🤝 Évacuation prise en charge client',price:0},{key:'forfait',label:'🚛 Forfait évacuation Lolirine',price:150},{key:'sans',label:'— Sans évacuation',price:0}];
const PAY_TERMS=['Paiement à terme échu (30j)','Paiement comptant','Acompte 30%+solde livraison','Acompte 50%+solde livraison','Virement avant expédition'];
const FOURNISSEURS=['Fluidra / SIBO','SCP Bénélux','HTH / BWT','Zodiac / Fluidra','Hayward','Astralpool','Pentair'];
function deplCost(km){const n=Number(km)||0;if(n<=0)return 0;if(n<=30)return 50;return 50+Math.ceil((n-30)/25)*10;}
function QuoteModal({products,clientInfo,onClose,onCreated}) {
  const cfg=window.LOLIRINE_CHECKLIST_CONFIG||{};
  const [tab,setTab]=useState('lines');
  const [busy,setBusy]=useState(false);
  const [result,setResult]=useState(null);
  const [err,setErr]=useState(null);
  const [lines,setLines]=useState((products||[]).map(p=>({...p,qty:p.qty||1,include:true,price_unit:typeof p.price==='number'?p.price:(parseFloat(p.price)||0),remise:0})));
  const [evac,setEvac]=useState('client');
  const [km,setKm]=useState(0);
  const [kmAuto,setKmAuto]=useState(true);
  const [kmMt,setKmMt]=useState(0);
  const [inclDepl,setInclDepl]=useState(false);
  const [inclMO,setInclMO]=useState(false);
  const [mo,setMo]=useState(0);
  const [fourn,setFourn]=useState('Fluidra / SIBO');
  const [fournRef,setFournRef]=useState('');
  const [delai,setDelai]=useState('5-10 jours ouvrés');
  const [livrDir,setLivrDir]=useState(true);
  const [livrAdr,setLivrAdr]=useState(clientInfo?.adresseChantier||'');
  const [cmdFourn,setCmdFourn]=useState('');
  const [noteInt,setNoteInt]=useState(clientInfo?.adresseChantier?'Chantier : '+clientInfo.adresseChantier:'');
  const [cond,setCond]=useState('');
  const [payTerm,setPayTerm]=useState(PAY_TERMS[0]);
  const [valid,setValid]=useState(30);
  const address = clientInfo?.adresseChantier||'';
  useEffect(()=>{
    if(!address||Number(km)>0)return;
    let cancel=false;
    (async()=>{
      try{
        const r=await fetch('https://nominatim.openstreetmap.org/search?'+new URLSearchParams({q:address,countrycodes:'be,lu,fr,nl',format:'json',limit:'1'}),{mode:'cors',headers:{'Accept-Language':'fr'}});
        const d=await r.json();
        if(cancel||!d[0])return;
        const lat2=parseFloat(d[0].lat),lon2=parseFloat(d[0].lon);
        const R=6371,dLat=(lat2-50.4875)*Math.PI/180,dLon=(lon2-4.9215)*Math.PI/180;
        const a=Math.sin(dLat/2)**2+Math.cos(50.4875*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
        const dist=Math.round(R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a))*1.3);
        if(!cancel&&dist>0){setKm(dist);setInclDepl(true);}
      }catch{}
    })();
    return()=>{cancel=true;};
  },[address]);
  useEffect(()=>{if(kmAuto)setKmMt(deplCost(Number(km)));},[km,kmAuto]);
  const tMat=lines.filter(l=>l.include).reduce((a,l)=>a+(l.price_unit||0)*(l.qty||1)*(1-(l.remise||0)/100),0);
  const tDepl=inclDepl?(kmAuto?deplCost(Number(km)):(Number(kmMt)||0)):0;
  const tEvac=evac!=='sans'?(EVAC_OPT.find(o=>o.key===evac)?.price||0):0;
  const tMO=inclMO?(Number(mo)||0):0;
  const sHT=tMat+tDepl+tEvac+tMO;
  const tva=sHT*0.21;
  const tTTC=sHT+tva;
  function toggleLine(i){setLines(ls=>ls.map((l,x)=>x===i?{...l,include:!l.include}:l));}
  function updQty(i,d){setLines(ls=>ls.map((l,x)=>x===i?{...l,qty:Math.max(1,(l.qty||1)+d)}:l));}
  function updP(i,v){setLines(ls=>ls.map((l,x)=>x===i?{...l,price_unit:parseFloat(v)||0}:l));}
  function updR(i,v){setLines(ls=>ls.map((l,x)=>x===i?{...l,remise:Math.min(100,Math.max(0,parseFloat(v)||0))}:l));}
  function delLine(i){setLines(ls=>ls.filter((_,x)=>x!==i));}
  async function doCreate(){
    setBusy(true);setErr(null);
    const allLines=[...lines.filter(l=>l.include).map(l=>({product_id:l.id||null,name:l.name,product_uom_qty:l.qty,price_unit:l.price_unit||0,discount:l.remise||0,default_code:l.ref||''})),...(tDepl>0?[{product_id:null,name:`Frais déplacement (${km}km depuis Boninne)`,product_uom_qty:1,price_unit:tDepl,discount:0,default_code:''}]:[]),...(tEvac>0?[{product_id:null,name:EVAC_OPT.find(o=>o.key===evac)?.label,product_uom_qty:1,price_unit:tEvac,discount:0,default_code:''}]:[]),...(tMO>0?[{product_id:null,name:"Main d'oeuvre technicien",product_uom_qty:1,price_unit:tMO,discount:0,default_code:''}]:[])];
    if(!allLines.length){setErr('Aucune ligne.');setBusy(false);return;}
    const clientName=[clientInfo?.prenom,clientInfo?.nom].filter(Boolean).join(' ')||clientInfo?.denominationSociale||'';
    try{
      const r=await fetch(cfg.quoteEndpoint||'/pool-checklist/create-quote',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{partner_id:clientInfo?.odooId||null,partner_name:clientName,ref_dossier:clientInfo?.refDossier||'',payment_term:payTerm,note:[noteInt,cond,livrDir?'Livraison chantier : '+livrAdr:'',cmdFourn?'BC fourn: '+cmdFourn:''].filter(Boolean).join('\n'),lines:allLines}})});
      const d=await r.json();
      if(d?.result?.error){setErr(d.result.error);setBusy(false);return;}
      setResult(d?.result||{});
      if(onCreated)onCreated(d?.result);
    }catch(e){setErr(e.message);}
    setBusy(false);
  }
  const IS={width:'100%',border:'1.5px solid #dde4ed',borderRadius:7,padding:'6px 10px',fontFamily:'inherit',fontSize:12,outline:'none',boxSizing:'border-box'};
  const TABS=[{k:'lines',lbl:'📦 Lignes',badge:lines.filter(l=>l.include).length},{k:'services',lbl:'🔧 Frais & services'},{k:'dropship',lbl:'🚚 Dropshipping'},{k:'notes',lbl:'📝 Notes'}];
  if(result)return(<div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center'}}><div style={{background:'#fff',borderRadius:16,padding:32,width:'min(460px,92vw)',textAlign:'center',boxShadow:'0 24px 80px rgba(0,0,0,.25)'}}><div style={{fontSize:48,marginBottom:10}}>✅</div><div style={{fontWeight:800,fontSize:19,color:'#1e293b',marginBottom:4}}>Devis créé !</div>{result.name&&<div style={{fontSize:17,color:'#0ea5e9',fontWeight:700,marginBottom:4}}>{result.name}</div>}{result.partner_name&&<div style={{fontSize:13,color:'#64748b',marginBottom:18}}>Client : {result.partner_name}</div>}<div style={{display:'flex',gap:9,justifyContent:'center'}}>{result.url&&<a href={result.url} target='_blank' rel='noreferrer' style={{background:'#0ea5e9',color:'#fff',borderRadius:9,padding:'9px 20px',fontWeight:700,fontSize:13,textDecoration:'none'}}>Ouvrir →</a>}<button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'9px 20px',fontWeight:600,fontSize:13,cursor:'pointer',color:'#475569'}}>Fermer</button></div></div></div>);
  return(
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f1f5f9',borderRadius:15,width:'min(940px,100%)',maxHeight:'95vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.28)',overflow:'hidden'}}>
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',padding:'11px 18px',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
          <div style={{flex:1}}><div style={{fontWeight:800,fontSize:16,color:'#1e293b'}}>📄 Nouveau devis — Lolirine Pool Store</div><div style={{fontSize:12,color:'#64748b',marginTop:1}}>{[clientInfo?.prenom,clientInfo?.nom].filter(Boolean).join(' ')||clientInfo?.denominationSociale||''}{clientInfo?.adresseChantier&&<span style={{color:'#94a3b8'}}> · {clientInfo.adresseChantier.split(',')[0]}</span>}</div></div>
          <span style={{background:'#f0fdf4',border:'1.5px solid #bbf7d0',borderRadius:20,padding:'3px 11px',fontSize:12,fontWeight:700,color:'#16a34a',flexShrink:0}}>Brouillon</span>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d',flexShrink:0}}>✕</button>
        </div>
        <div style={{background:'#fff',borderBottom:'1px solid #e8edf3',padding:'10px 18px',display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(150px,1fr))',gap:10,flexShrink:0}}>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Client</div><div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{[clientInfo?.prenom,clientInfo?.nom].filter(Boolean).join(' ')||clientInfo?.denominationSociale||'—'}</div>{clientInfo?.adresseChantier&&<div style={{fontSize:11,color:'#64748b'}}>{clientInfo.adresseChantier}</div>}</div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Date</div><div style={{fontSize:13,color:'#1e293b'}}>{new Date().toLocaleDateString('fr-BE')}</div></div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Validité</div><div style={{display:'flex',alignItems:'center',gap:4}}><input type="number" value={valid} min={1} onChange={e=>setValid(e.target.value)} style={{width:50,...IS,padding:'4px 7px',textAlign:'center'}} /><span style={{fontSize:12,color:'#64748b'}}>jours</span></div></div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Conditions paiement</div><select value={payTerm} onChange={e=>setPayTerm(e.target.value)} style={{...IS,background:'#fff',fontSize:11}}>{PAY_TERMS.map(t=><option key={t}>{t}</option>)}</select></div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>TVA</div><div style={{fontSize:13,fontWeight:600,color:'#475569'}}>21 % (BE)</div></div>
        </div>
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',display:'flex',flexShrink:0,overflowX:'auto'}}>
          {TABS.map(t=><button key={t.k} onClick={()=>setTab(t.k)} style={{padding:'9px 17px',border:'none',borderBottom:`3px solid ${tab===t.k?'#0ea5e9':'transparent'}`,background:'transparent',cursor:'pointer',fontWeight:tab===t.k?700:500,fontSize:13,color:tab===t.k?'#0ea5e9':'#64748b',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5}}>{t.lbl}{t.badge!=null&&<span style={{background:tab===t.k?'#0ea5e9':'#e2e8f0',color:tab===t.k?'#fff':'#64748b',borderRadius:20,padding:'1px 6px',fontSize:11,fontWeight:700}}>{t.badge}</span>}</button>)}
        </div>
        <div style={{flex:1,overflowY:'auto'}}>
          {tab==='lines'&&(<div>
            <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
              <thead style={{background:'#f8fafc',position:'sticky',top:0,zIndex:1}}><tr style={{borderBottom:'2px solid #e2e8f0'}}>{['','Produit','Fourn.','Réf.','Qté','Prix HT','Rem%','Total HT',''].map((h,i)=><th key={i} style={{padding:'8px 9px',textAlign:'left',fontWeight:700,color:'#64748b',fontSize:11,whiteSpace:'nowrap'}}>{h}</th>)}</tr></thead>
              <tbody>
                {lines.map((l,i)=>{const sup=l.suppliers?.[0]||{};const mt=(l.price_unit||0)*(l.qty||1)*(1-(l.remise||0)/100);return<tr key={i} style={{borderBottom:'1px solid #f1f5f9',background:l.include?'#fff':'#f8fafc',opacity:l.include?1:.5}}>
                  <td style={{padding:'7px 9px',width:22}}><input type="checkbox" checked={!!l.include} onChange={()=>toggleLine(i)} style={{accentColor:'#0ea5e9',width:14,height:14,cursor:'pointer'}} /></td>
                  <td style={{padding:'7px 9px',minWidth:160}}><div style={{fontWeight:600,color:'#1e293b',fontSize:13}}>{l.name}</div>{l.ref&&<div style={{fontSize:11,color:'#94a3b8'}}>Réf: {l.ref}</div>}</td>
                  <td style={{padding:'7px 9px',fontSize:12,color:'#7c3aed',whiteSpace:'nowrap'}}>{sup.name||'—'}</td>
                  <td style={{padding:'7px 9px',fontSize:12,color:'#64748b'}}>{sup.ref||l.ref||'—'}</td>
                  <td style={{padding:'7px 9px'}}><div style={{display:'flex',alignItems:'center',gap:3}}><button onClick={()=>updQty(i,-1)} style={{width:20,height:20,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:12}}>−</button><span style={{fontWeight:700,minWidth:20,textAlign:'center'}}>{l.qty}</span><button onClick={()=>updQty(i,+1)} style={{width:20,height:20,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:12}}>+</button></div></td>
                  <td style={{padding:'7px 9px',width:85}}><input type="number" value={l.price_unit} min={0} step={0.01} onChange={e=>updP(i,e.target.value)} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:6,padding:'3px 6px',fontFamily:'inherit',fontSize:12,textAlign:'right',outline:'none'}} /></td>
                  <td style={{padding:'7px 9px',width:60}}><input type="number" value={l.remise||0} min={0} max={100} onChange={e=>updR(i,e.target.value)} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:6,padding:'3px 6px',fontFamily:'inherit',fontSize:12,textAlign:'right',outline:'none'}} /></td>
                  <td style={{padding:'7px 9px',fontWeight:700,color:'#0369a1',textAlign:'right',whiteSpace:'nowrap'}}>{mt>0?mt.toFixed(2)+' €':'—'}</td>
                  <td style={{padding:'7px 9px'}}><button onClick={()=>delLine(i)} style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',fontSize:13}}>✕</button></td>
                </tr>;})}
                {lines.length===0&&<tr><td colSpan={9} style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucun produit. Ajoutez des articles via les boutons 🛒 de la check-list.</td></tr>}
              </tbody>
            </table>
            <div style={{padding:'10px 16px',background:'#f8fafc',borderTop:'1px solid #e2e8f0',textAlign:'right',fontSize:13,color:'#64748b'}}>Sous-total matériaux HT : <strong style={{color:'#0369a1'}}>{tMat.toFixed(2)} €</strong></div>
          </div>)}
          {tab==='services'&&(<div style={{padding:18,display:'flex',flexDirection:'column',gap:16}}>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
              <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:10}}>🗑️ Évacuation déchets</div>
              {EVAC_OPT.map(o=><label key={o.key} style={{display:'flex',alignItems:'center',gap:9,padding:'8px 12px',borderRadius:9,border:`2px solid ${evac===o.key?'#0ea5e9':'#e8edf3'}`,background:evac===o.key?'#eff9ff':'#fff',cursor:'pointer',marginBottom:6}}><input type="radio" name="evac" value={o.key} checked={evac===o.key} onChange={()=>setEvac(o.key)} style={{accentColor:'#0ea5e9',width:15,height:15}} /><span style={{flex:1,fontSize:13,fontWeight:evac===o.key?600:400,color:evac===o.key?'#0369a1':'#334155'}}>{o.label}</span>{o.price>0&&<span style={{fontWeight:700,color:'#0369a1',fontSize:14}}>{o.price} €</span>}</label>)}
            </div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}><input type="checkbox" checked={inclDepl} onChange={e=>setInclDepl(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15,cursor:'pointer'}} /><span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>🚗 Frais de déplacement</span><span style={{fontSize:11,color:'#94a3b8',fontStyle:'italic'}}>depuis Boninne · ≤30km=50€ · +10€/25km</span></div>
              <div style={{display:'flex',gap:14,alignItems:'flex-end',flexWrap:'wrap'}}>
                <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Distance (km)</div><div style={{display:'flex',alignItems:'center',gap:5}}><button onClick={()=>setKm(Math.max(0,Number(km)-5))} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>−</button><input type="number" value={km} min={0} onChange={e=>setKm(e.target.value)} style={{width:65,...IS,textAlign:'center',padding:'4px 7px'}} /><button onClick={()=>setKm(Number(km)+5)} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>+</button></div></div>
                <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Montant HT (€) <label style={{fontWeight:400}}><input type="checkbox" checked={kmAuto} onChange={e=>setKmAuto(e.target.checked)} style={{accentColor:'#0ea5e9',marginRight:3}} />Auto</label></div><input type="number" value={kmAuto?deplCost(Number(km)):kmMt} readOnly={kmAuto} min={0} onChange={e=>!kmAuto&&setKmMt(e.target.value)} style={{width:85,...IS,textAlign:'center',padding:'4px 7px',background:kmAuto?'#f8fafc':'#fff'}} /></div>
                <div style={{fontSize:12,color:'#64748b',paddingBottom:4}}>{address&&<div>📍 {address.split(',')[0]}</div>}{Number(km)>0&&<div style={{color:'#0ea5e9',fontWeight:600,marginTop:2}}>Barème : {deplCost(Number(km))} €</div>}</div>
              </div>
            </div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}><input type="checkbox" checked={inclMO} onChange={e=>setInclMO(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15,cursor:'pointer'}} /><span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>🔨 Main d'œuvre technicien</span></div>
              <div style={{display:'flex',gap:9,alignItems:'center',flexWrap:'wrap'}}><button onClick={()=>setMo(Math.max(0,(Number(mo)||0)-50))} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>−</button><input type="number" value={mo} min={0} step={50} onChange={e=>setMo(e.target.value)} style={{width:95,...IS,textAlign:'center',fontSize:15,fontWeight:700,padding:'5px 9px'}} /><span style={{fontSize:13,color:'#475569'}}>€ HT</span><button onClick={()=>setMo((Number(mo)||0)+50)} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>+</button>{[0,500,750,1000,1500,2000].map(v=><button key={v} onClick={()=>setMo(v)} style={{padding:'3px 8px',borderRadius:6,border:`1px solid ${mo==v?'#0ea5e9':'#e2e8f0'}`,background:mo==v?'#eff9ff':'#f8fafc',color:mo==v?'#0369a1':'#64748b',fontSize:11,cursor:'pointer',fontWeight:mo==v?700:400}}>{v===0?'—':v+'€'}</button>)}</div>
            </div>
          </div>)}
          {tab==='dropship'&&(<div style={{padding:18,display:'flex',flexDirection:'column',gap:14}}>
            <div style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:11,padding:'10px 14px',fontSize:13,color:'#92400e'}}>⚡ En dropshipping, la commande fournisseur est transmise après validation du devis. Livraison possible directement sur chantier.</div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'16px',display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Fournisseur principal</div><select value={fourn} onChange={e=>setFourn(e.target.value)} style={{...IS,background:'#fff'}}>{FOURNISSEURS.map(s=><option key={s}>{s}</option>)}</select></div>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Réf. commande fournisseur</div><input value={cmdFourn} onChange={e=>setCmdFourn(e.target.value)} placeholder="BC-FOURN-2025-XXX" style={IS} /></div>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Réf. produit fournisseur</div><input value={fournRef} onChange={e=>setFournRef(e.target.value)} placeholder="ex: FLU-PMP-00312" style={IS} /></div>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Délai de livraison estimé</div><input value={delai} onChange={e=>setDelai(e.target.value)} style={IS} /></div>
            </div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'16px'}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}><input type="checkbox" checked={livrDir} onChange={e=>setLivrDir(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15}} /><span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>📍 Livraison directe sur chantier</span></div>
              {livrDir?<div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Adresse de livraison</div><input value={livrAdr} onChange={e=>setLivrAdr(e.target.value)} placeholder="Adresse complète…" style={IS} /></div>:<div style={{fontSize:13,color:'#64748b'}}>📦 Livraison à l'entrepôt Lolirine — retrait technicien</div>}
            </div>
          </div>)}
          {tab==='notes'&&(<div style={{padding:18,display:'flex',flexDirection:'column',gap:12}}>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:5}}>Notes internes / chantier</div><textarea value={noteInt} onChange={e=>setNoteInt(e.target.value)} rows={4} placeholder="Observations de la visite, accès, remarques…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'9px 12px',fontFamily:'inherit',fontSize:12,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} /></div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:5}}>Conditions particulières</div><textarea value={cond} onChange={e=>setCond(e.target.value)} rows={3} placeholder="Garanties, délais, restrictions…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'9px 12px',fontFamily:'inherit',fontSize:12,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} /></div>
          </div>)}
        </div>
        <div style={{background:'#fff',borderTop:'2px solid #e2e8f0',flexShrink:0,display:'flex',flexWrap:'wrap'}}>
          <div style={{flex:1,padding:'12px 18px',minWidth:240}}>
            <table style={{width:'100%',fontSize:13}}><tbody>
              {tMat>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Matériaux HT</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tMat.toFixed(2)} €</td></tr>}
              {tDepl>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Déplacement ({km}km)</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tDepl.toFixed(2)} €</td></tr>}
              {tEvac>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Évacuation</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tEvac.toFixed(2)} €</td></tr>}
              {tMO>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Main d'œuvre</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tMO.toFixed(2)} €</td></tr>}
              <tr style={{borderTop:'1px solid #f0f4f8'}}><td style={{color:'#64748b',padding:'5px 0 2px',fontWeight:600}}>Montant HT</td><td style={{textAlign:'right',fontWeight:700,color:'#1e293b',fontSize:14}}>{sHT.toFixed(2)} €</td></tr>
              <tr><td style={{color:'#64748b',padding:'2px 0'}}>TVA 21%</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tva.toFixed(2)} €</td></tr>
              <tr style={{borderTop:'2px solid #0ea5e9'}}><td style={{fontWeight:800,fontSize:15,color:'#0ea5e9',padding:'5px 0 0'}}>Total TTC</td><td style={{textAlign:'right',fontWeight:800,fontSize:16,color:'#0ea5e9'}}>{tTTC.toFixed(2)} €</td></tr>
            </tbody></table>
          </div>
          <div style={{padding:'12px 18px',display:'flex',flexDirection:'column',gap:8,justifyContent:'center',minWidth:190,alignItems:'stretch'}}>
            {err&&<div style={{color:'#ef4444',fontSize:12,textAlign:'center'}}>{err}</div>}
            <button onClick={doCreate} disabled={busy} style={{background:busy?'#cbd5e1':'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'10px 22px',fontWeight:700,fontSize:14,cursor:busy?'wait':'pointer',whiteSpace:'nowrap'}}>{busy?'⏳ Création…':'📄 Créer le devis Odoo'}</button>
            <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 22px',fontWeight:600,fontSize:13,cursor:'pointer',color:'#475569'}}>← Annuler</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   PoolChecklist — Wizard 4 étapes
═══════════════════════════════════════════════════ */
function PoolChecklist() {
  const [step, setStep]   = useState(1);
  /* Étape 1 */
  const [type, setType]   = useState('');
  /* Étape 2 — Infos client */
  const [clientType, setClientType] = useState('particulier'); /* particulier | professionnel */
  const [prenom, setPrenom]     = useState('');
  const [nom, setNom]           = useState('');
  const [email, setEmail]       = useState('');
  const [telephone, setTelephone] = useState('');
  const [codePostal, setCodePostal] = useState('');
  const [adresseChantier, setAdresseChantier] = useState('');
  const [denomination, setDenomination] = useState('');
  const [tvaNum, setTvaNum]     = useState('');
  const [refDossier, setRefDossier] = useState('');
  const [technicien, setTechnicien] = useState('');
  const [date, setDate]         = useState(new Date().toISOString().split('T')[0]);
  const [odooId, setOdooId]     = useState(null);
  /* Étape 3 — Plan bassin */
  const [basinShape, setBasinShape] = useState('');
  const [basinL, setBasinL]     = useState('');
  const [basinW, setBasinW]     = useState('');
  const [basinD, setBasinD]     = useState('');
  const [basinNotes, setBasinNotes] = useState('');
  /* Étape 4 — Checklist */
  const [itemState, setItemState] = useState({});
  const [products, setProducts] = useState([]);
  const [panel, setPanel]       = useState(null);
  const [showQuote, setShowQuote] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [obs, setObs]           = useState('');
  const [statut, setStatut]     = useState('en_cours');
  const [itemData,setItemData]  = useState({});
  const [showPlanning,setShowPlanning] = useState(false);
  const [signClient, setSignClient] = useState('');
  const [signTech, setSignTech] = useState('');
  const [saved, setSaved]       = useState(false);
  const [filter4, setFilter4]   = useState('all');
  const [search4, setSearch4]   = useState('');
  const [lastSaved, setLastSaved] = useState(null);

  /* Auto-save toutes les 30s si données présentes */
  useEffect(()=>{
    if(!type&&!prenom&&!nom)return;
    const t=setInterval(()=>{
      try{
        const s=JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
        const record={type,clientType,prenom,nom,email,telephone,codePostal,adresseChantier,denomination,tvaNum,refDossier,technicien,date,basinShape,basinL,basinW,basinD,basinNotes,itemState,products,obs,statut,signClient,signTech,savedAt:new Date().toISOString(),autoSave:true};
        const lastIdx=s.findIndex(r=>r.autoSave&&r.type===type&&r.prenom===prenom&&r.nom===nom);
        if(lastIdx>=0)s[lastIdx]=record;else s.push(record);
        localStorage.setItem('pool_checklist_history',JSON.stringify(s.slice(-50)));
        setLastSaved(new Date());
      }catch{}
    },30000);
    return()=>clearInterval(t);
  },[type,prenom,nom,itemState,products]);

  const sections   = type ? (SECTIONS_DATA[type]||[]) : [];
  const totalItems = sections.reduce((a,s)=>a+s.items.length,0);
  const totalDone  = sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>!!itemState[`${si}_${ii}`]).length,0);
  const pct = totalItems ? Math.round(totalDone/totalItems*100) : 0;
  const totalHT = products.reduce((a,p)=>{const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);return a+price*(p.qty||1);},0);

  const clientInfo = { prenom, nom, email, telephone, codePostal, adresseChantier, denomination, tvaNum, clientType, refDossier, odooId };

  function handleAddProducts(newProds) {
    setProducts(ps=>{const ex=new Set(ps.map(p=>p.ref||p.name));const toAdd=newProds.filter(p=>!ex.has(p.ref||p.name));return[...ps,...toAdd.map(p=>({...p,qty:1}))];});
    setPanel(null);
  }
  function updateQty(i,d){setProducts(ps=>ps.map((p,x)=>x===i?{...p,qty:Math.max(0,(p.qty||1)+d)}:p).filter(p=>p.qty>0));}
  function removeProduct(i){setProducts(ps=>ps.filter((_,x)=>x!==i));}
  function setItemSt(si,ii,val){const k=`${si}_${ii}`;setItemState(st=>({...st,[k]:val===null?undefined:val}));}

  function saveToHistory(){
    try{
      const s=JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
      s.push({type,clientType,prenom,nom,email,telephone,codePostal,adresseChantier,denomination,tvaNum,refDossier,technicien,date,basinShape,basinL,basinW,basinD,basinNotes,itemState,itemData,products,obs,statut,signClient,signTech,savedAt:new Date().toISOString()});
      localStorage.setItem('pool_checklist_history',JSON.stringify(s.slice(-50)));
      setSaved(true);setTimeout(()=>setSaved(false),2500);
    }catch(e){alert('Erreur: '+e.message);}
  }
  function loadRecord(r){
    setType(r.type||'entretien');setStep(r.step||4);
    setClientType(r.clientType||'particulier');setPrenom(r.prenom||'');setNom(r.nom||'');setEmail(r.email||'');
    setTelephone(r.telephone||'');setCodePostal(r.codePostal||'');setAdresseChantier(r.adresseChantier||'');
    setDenomination(r.denomination||'');setTvaNum(r.tvaNum||'');setRefDossier(r.refDossier||'');
    setTechnicien(r.technicien||'');setDate(r.date||new Date().toISOString().split('T')[0]);
    setBasinShape(r.basinShape||'');setBasinL(r.basinL||'');setBasinW(r.basinW||'');setBasinD(r.basinD||'');setBasinNotes(r.basinNotes||'');
    setItemState(r.itemState||{});setItemData(r.itemData||{});setProducts(r.products||[]);setObs(r.obs||'');
    setStatut(r.statut||'en_cours');setSignClient(r.signClient||'');setSignTech(r.signTech||'');
  }
  function reset(){if(!confirm('Réinitialiser toute la fiche ?'))return;setStep(1);setType('');setPrenom('');setNom('');setEmail('');setTelephone('');setCodePostal('');setAdresseChantier('');setDenomination('');setTvaNum('');setRefDossier('');setTechnicien('');setDate(new Date().toISOString().split('T')[0]);setBasinShape('');setBasinL('');setBasinW('');setBasinD('');setBasinNotes('');setItemState({});setProducts([]);setObs('');setStatut('en_cours');setSignClient('');setSignTech('');setSaved(false);}

  const canNext = [
    true,
    type !== '',
    (prenom||nom||denomination) !== '',
    true,
  ];

  /* ── Styles ── */
  const LABEL_ST = {fontSize:13,fontWeight:600,color:'#475569',display:'block',marginBottom:5};
  const INPUT_ST = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 13px',fontFamily:'inherit',fontSize:14,outline:'none',boxSizing:'border-box'};

  const STEPS = ['Type d\'intervention','Infos client','Plan de bassin','Check-list & produits'];

  return (
    <div style={{fontFamily:"'Inter','Segoe UI',system-ui,sans-serif",background:'#f0f4f8',minHeight:'100vh',display:'flex',flexDirection:'column'}}>

      {/* ── Header ── */}
      <div style={{background:'#fff',borderBottom:'1.5px solid #e2e8f0',padding:'14px 24px',display:'flex',alignItems:'center',gap:14,flexShrink:0}}>
        <img src="/lolirine_pool_checklist/static/description/icon.png" alt="" style={{width:48,height:48,borderRadius:10,flexShrink:0}} />
        <div style={{flex:1}}>
          <div style={{fontWeight:800,fontSize:18,color:'#1e293b',letterSpacing:'-.3px'}}>Lolirine Pool Store — Fiche de visite chantier</div>
          <div style={{fontSize:12,color:'#94a3b8',marginTop:1}}>Diagnostic · intervention · produits liés · devis estimatif</div>
        </div>
        <div style={{display:'flex',gap:8,flexShrink:0}}>
          <button onClick={()=>setShowPlanning(true)} style={{background:'rgba(255,255,255,.15)',color:'#fff',border:'1.5px solid rgba(255,255,255,.4)',borderRadius:8,padding:'6px 12px',cursor:'pointer',fontWeight:600,fontSize:12}}>📅 Planning</button>
          <button onClick={()=>setShowHistory(true)} style={{background:'#f1f5f9',color:'#475569',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 13px',cursor:'pointer',fontWeight:600,fontSize:12}}>📁 Historique</button>
          <button onClick={saveToHistory} style={{background:saved?'#16a34a':'#f1f5f9',color:saved?'#fff':'#475569',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 13px',cursor:'pointer',fontWeight:600,fontSize:12,transition:'all .3s'}}>{saved?'✅ Sauvegardé':'💾 Sauvegarder'}</button>
          {lastSaved&&<span style={{fontSize:11,color:'#16a34a',display:'flex',alignItems:'center',gap:4,background:'#f0fdf4',border:'1px solid #bbf7d0',borderRadius:8,padding:'4px 9px',whiteSpace:'nowrap'}}><span style={{width:6,height:6,borderRadius:'50%',background:'#16a34a',display:'inline-block'}}/>Auto {Math.round((Date.now()-lastSaved)/1000)}s</span>}
          <button onClick={reset} style={{background:'#f1f5f9',color:'#94a3b8',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 10px',cursor:'pointer',fontSize:12}}>↺</button>
          <a href="/odoo" style={{background:'#f1f5f9',color:'#475569',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 13px',cursor:'pointer',fontWeight:600,fontSize:12,textDecoration:'none',display:'flex',alignItems:'center',gap:4}}>← Retour Odoo</a>
        </div>
      </div>

      {/* ── Stepper ── */}
      <div style={{background:'#fff',borderBottom:'1.5px solid #e2e8f0',padding:'16px 24px',flexShrink:0}}>
        <div style={{display:'flex',alignItems:'center',maxWidth:700,margin:'0 auto'}}>
          {STEPS.map((s,i)=>{
            const n=i+1;
            const done=n<step;
            const active=n===step;
            return(
              <React.Fragment key={n}>
                <div style={{display:'flex',flexDirection:'column',alignItems:'center',flex:i<STEPS.length-1?'none':1,cursor:done?'pointer':'default'}} onClick={()=>done&&setStep(n)}>
                  <div style={{width:36,height:36,borderRadius:'50%',background:done?'#0ea5e9':active?'#0ea5e9':'#e2e8f0',border:`2px solid ${done||active?'#0ea5e9':'#e2e8f0'}`,display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:14,color:done||active?'#fff':'#94a3b8',transition:'all .3s'}}>
                    {done?'✓':n}
                  </div>
                  <div style={{fontSize:11,fontWeight:active?700:500,color:active?'#0ea5e9':done?'#1e293b':'#94a3b8',marginTop:5,whiteSpace:'nowrap',textAlign:'center'}}>{s}</div>
                </div>
                {i<STEPS.length-1&&<div style={{flex:1,height:2,background:done?'#0ea5e9':'#e2e8f0',margin:'0 8px',marginBottom:20,transition:'background .3s'}} />}
              </React.Fragment>
            );
          })}
        </div>
        {step===4&&totalItems>0&&(
          <div style={{maxWidth:700,margin:'12px auto 0',display:'flex',alignItems:'center',gap:10}}>
            <div style={{flex:1,height:6,background:'#e2e8f0',borderRadius:6,overflow:'hidden'}}><div style={{height:'100%',background:pct===100?'#16a34a':'#0ea5e9',width:`${pct}%`,borderRadius:6,transition:'width .4s'}} /></div>
            <span style={{fontSize:12,fontWeight:700,color:pct===100?'#16a34a':'#0ea5e9',whiteSpace:'nowrap'}}>{totalDone}/{totalItems} · {pct}%</span>
          </div>
        )}
      </div>

      {/* ── Contenu ── */}
      <div style={{flex:1,overflowY:'auto',padding:'28px 16px'}}>
        <div style={{maxWidth:900,margin:'0 auto'}}>

          {/* ════ Étape 1 — Type d'intervention ════ */}
          {step===1&&(
            <div>
              <h2 style={{fontSize:22,fontWeight:800,color:'#1e293b',marginBottom:6,marginTop:0}}>Sélectionner le type d'intervention</h2>
              <p style={{fontSize:14,color:'#64748b',marginBottom:24,marginTop:0}}>Choisissez le type d'intervention pour charger la check-list correspondante.</p>
              <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:14}}>
                {INTERVENTION_TYPES.map(t=>{
                  const sects = SECTIONS_DATA[t.key]||[];
                  const pts   = sects.reduce((a,s)=>a+s.items.length,0);
                  const sel   = type===t.key;
                  return(
                    <div key={t.key} onClick={()=>setType(t.key)}
                      style={{background:'#fff',borderRadius:14,padding:'20px 22px',border:`2px solid ${sel?t.color:'#e2e8f0'}`,cursor:'pointer',transition:'all .2s',boxShadow:sel?`0 0 0 4px ${t.color}22`:'0 1px 4px rgba(0,0,0,.06)',transform:sel?'translateY(-2px)':'none'}}>
                      <div style={{fontSize:28,marginBottom:8}}>{t.icon}</div>
                      <div style={{fontWeight:800,fontSize:16,color:'#1e293b',marginBottom:4}}>{t.label}</div>
                      <div style={{fontSize:12,color:'#94a3b8'}}>{pts} points · {sects.length} sections</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ════ Étape 2 — Infos client ════ */}
          {step===2&&(
            <div style={{maxWidth:680,margin:'0 auto'}}>
              <h2 style={{fontSize:22,fontWeight:800,color:'#1e293b',marginBottom:6,marginTop:0}}>Informations client</h2>
              <p style={{fontSize:14,color:'#64748b',marginBottom:24,marginTop:0}}>Renseignez les coordonnées du client et les informations du chantier.</p>

              {/* Particulier / Professionnel */}
              <div style={{background:'#fff',borderRadius:14,padding:'20px 22px',marginBottom:20,border:'1.5px solid #e2e8f0'}}>
                <label style={{...LABEL_ST,marginBottom:12}}>Type de client</label>
                <div style={{display:'flex',gap:10,marginBottom:20}}>
                  {[{k:'particulier',l:'👤 Particulier'},{k:'professionnel',l:'🏢 Professionnel'}].map(opt=>(
                    <button key={opt.k} onClick={()=>setClientType(opt.k)}
                      style={{flex:1,padding:'10px 16px',borderRadius:10,border:`2px solid ${clientType===opt.k?'#0ea5e9':'#e2e8f0'}`,background:clientType===opt.k?'#eff9ff':'#fff',color:clientType===opt.k?'#0369a1':'#475569',fontWeight:clientType===opt.k?700:500,fontSize:14,cursor:'pointer',transition:'all .15s'}}>
                      {opt.l}
                    </button>
                  ))}
                </div>

                {/* Champs professionnel */}
                {clientType==='professionnel'&&(
                  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14,marginBottom:14,paddingBottom:14,borderBottom:'1px solid #f0f4f8'}}>
                    <div style={{gridColumn:'1/-1'}}>
                      <label style={LABEL_ST}>Dénomination sociale *</label>
                      <ClientAutocomplete value={denomination} onChange={setDenomination} onSelectPartner={p=>{setDenomination(p.name);setOdooId(p.id);}} placeholder="Rechercher une entreprise…" />
                    </div>
                    <div>
                      <label style={LABEL_ST}>Numéro de TVA (BE)</label>
                      <input value={tvaNum} onChange={e=>setTvaNum(e.target.value)} placeholder="BE 0XXX.XXX.XXX" style={INPUT_ST} />
                    </div>
                  </div>
                )}

                {/* Contact */}
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
                  {clientType==='particulier'&&(
                    <div style={{gridColumn:'1/-1'}}>
                      <label style={LABEL_ST}>Client Odoo (optionnel)</label>
                      <ClientAutocomplete value={prenom&&nom?`${prenom} ${nom}`:prenom||nom} onChange={v=>{setPrenom(v.split(' ')[0]||'');setNom(v.split(' ').slice(1).join(' ')||'');}} onSelectPartner={p=>{const parts=p.name.split(' ');setPrenom(parts[0]||'');setNom(parts.slice(1).join(' ')||'');setOdooId(p.id);}} placeholder="Rechercher un client existant…" />
                    </div>
                  )}
                  <div>
                    <label style={LABEL_ST}>Prénom *</label>
                    <input value={prenom} onChange={e=>setPrenom(e.target.value)} placeholder="Jean" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Nom *</label>
                    <input value={nom} onChange={e=>setNom(e.target.value)} placeholder="Dupont" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Email</label>
                    <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="jean.dupont@email.com" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Téléphone</label>
                    <input value={telephone} onChange={e=>setTelephone(e.target.value)} placeholder="0475/12 34 56" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Code postal</label>
                    <input value={codePostal} onChange={e=>setCodePostal(e.target.value)} placeholder="4000" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Référence dossier</label>
                    <input value={refDossier} onChange={e=>setRefDossier(e.target.value)} placeholder="CHT-2025-042" style={INPUT_ST} />
                  </div>
                  <div style={{gridColumn:'1/-1'}}>
                    <label style={LABEL_ST}>Adresse du chantier</label>
                    <AddressAutocomplete value={adresseChantier} onChange={setAdresseChantier} placeholder="Adresse complète du chantier…" />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Technicien</label>
                    <input value={technicien} onChange={e=>setTechnicien(e.target.value)} placeholder="Prénom Nom" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Date de visite</label>
                    <input type="date" value={date} onChange={e=>setDate(e.target.value)} style={INPUT_ST} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ════ Étape 3 — Plan de bassin ════ */}
          {step===3&&(
            <div style={{maxWidth:680,margin:'0 auto'}}>
              <h2 style={{fontSize:22,fontWeight:800,color:'#1e293b',marginBottom:6,marginTop:0}}>Plan de bassin</h2>
              <p style={{fontSize:14,color:'#64748b',marginBottom:24,marginTop:0}}>Forme, dimensions et caractéristiques du bassin (optionnel).</p>
              <div style={{background:'#fff',borderRadius:14,padding:'20px 22px',marginBottom:20,border:'1.5px solid #e2e8f0'}}>
                <label style={{...LABEL_ST,marginBottom:12}}>Forme du bassin</label>
                <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:10,marginBottom:20}}>
                  {BASIN_SHAPES.map(s=>(
                    <button key={s.key} onClick={()=>setBasinShape(s.key)}
                      style={{padding:'14px 10px',borderRadius:11,border:`2px solid ${basinShape===s.key?'#0ea5e9':'#e2e8f0'}`,background:basinShape===s.key?'#eff9ff':'#fff',cursor:'pointer',transition:'all .15s',textAlign:'center'}}>
                      <div style={{fontSize:24,marginBottom:4}}>{s.icon}</div>
                      <div style={{fontSize:12,fontWeight:basinShape===s.key?700:500,color:basinShape===s.key?'#0369a1':'#475569'}}>{s.label}</div>
                    </button>
                  ))}
                </div>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:14,marginBottom:14}}>
                  <div><label style={LABEL_ST}>Longueur (m)</label><input type="number" value={basinL} onChange={e=>setBasinL(e.target.value)} placeholder="10.0" min={0} step={0.1} style={INPUT_ST} /></div>
                  <div><label style={LABEL_ST}>Largeur (m)</label><input type="number" value={basinW} onChange={e=>setBasinW(e.target.value)} placeholder="5.0" min={0} step={0.1} style={INPUT_ST} /></div>
                  <div><label style={LABEL_ST}>Profondeur max (m)</label><input type="number" value={basinD} onChange={e=>setBasinD(e.target.value)} placeholder="1.5" min={0} step={0.1} style={INPUT_ST} /></div>
                </div>
                {basinL&&basinW&&basinD&&<div style={{background:'#f0f9ff',borderRadius:9,padding:'10px 14px',marginBottom:14,fontSize:13,color:'#0369a1',fontWeight:600}}>
                  Surface : {(parseFloat(basinL)*parseFloat(basinW)).toFixed(1)} m² · Volume estimé : {(parseFloat(basinL)*parseFloat(basinW)*parseFloat(basinD)*0.8).toFixed(1)} m³
                </div>}
                <div><label style={LABEL_ST}>Notes sur le bassin</label><textarea value={basinNotes} onChange={e=>setBasinNotes(e.target.value)} placeholder="Particularités, contraintes, équipements existants…" rows={3} style={{...INPUT_ST,resize:'vertical',lineHeight:1.5}} /></div>
              </div>
            </div>
          )}

          {/* ════ Étape 4 — Check-list & produits ════ */}
          {step===4&&(
            <div>
              {/* Stats bar */}
              {totalItems>0&&(
                <div style={{display:'flex',gap:9,marginBottom:16,flexWrap:'wrap'}}>
                  {[
                    {label:'Total',value:totalItems,bg:'#f1f5f9',tc:'#475569',vc:'#1e293b'},
                    {label:'Conformes',value:sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>itemState[`${si}_${ii}`]==='ok').length,0),bg:'#eaf3de',tc:'#639922',vc:'#3b6d11'},
                    {label:'Attention',value:sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>itemState[`${si}_${ii}`]==='warn').length,0),bg:'#faeeda',tc:'#ba7517',vc:'#854f0b'},
                    {label:'Problèmes',value:sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>itemState[`${si}_${ii}`]==='bad').length,0),bg:'#fcebeb',tc:'#e24b4a',vc:'#a32d2d'},
                    {label:'Non traités',value:totalItems-totalDone,bg:'#f8fafc',tc:'#94a3b8',vc:'#64748b'},
                  ].map(stat=>(
                    <div key={stat.label} style={{flex:1,minWidth:70,background:stat.bg,borderRadius:10,padding:'10px 12px',textAlign:'center',cursor:'pointer'}} onClick={()=>setFilter4(f=>f===stat.label.toLowerCase().replace(' ','_')?'all':stat.label.toLowerCase().replace(' ','_'))}>
                      <div style={{fontSize:22,fontWeight:700,color:stat.vc,lineHeight:1}}>{stat.value}</div>
                      <div style={{fontSize:11,color:stat.tc,marginTop:3}}>{stat.label}</div>
                    </div>
                  ))}
                </div>
              )}
              {/* Filtres + recherche */}
              <div style={{display:'flex',gap:6,marginBottom:14,flexWrap:'wrap',alignItems:'center'}}>
                {[{k:'all',l:'Tous'},{k:'ok',l:'OK'},{k:'warn',l:'Attention'},{k:'bad',l:'Problèmes'},{k:'untreated',l:'Non traités'}].map(f=>(
                  <button key={f.k} onClick={()=>setFilter4(filter4===f.k?'all':f.k)}
                    style={{padding:'4px 13px',borderRadius:20,border:`1.5px solid ${filter4===f.k?'#0ea5e9':'#e2e8f0'}`,background:filter4===f.k?'#0ea5e9':'#fff',color:filter4===f.k?'#fff':'#64748b',fontWeight:filter4===f.k?600:400,fontSize:12,cursor:'pointer',transition:'all .15s'}}>
                    {f.l}
                  </button>
                ))}
                <input value={search4} onChange={e=>setSearch4(e.target.value)} placeholder="Rechercher un point…"
                  style={{flex:1,minWidth:140,height:30,border:'1.5px solid #e2e8f0',borderRadius:20,padding:'0 14px',fontFamily:'inherit',fontSize:12,outline:'none',color:'#334155'}} />
              </div>
              {/* Sections filtrées */}
              {sections.map((s,si)=>{
                const filteredItems=s.items.map((item,ii)=>({item,ii})).filter(({item,ii})=>{
                  const st=itemState[`${si}_${ii}`]||'';
                  if(search4&&!item.toLowerCase().includes(search4.toLowerCase()))return false;
                  if(filter4==='all'||!filter4)return true;
                  if(filter4==='ok')return st==='ok';
                  if(filter4==='warn')return st==='warn';
                  if(filter4==='bad')return st==='bad';
                  if(filter4==='untreated')return st==='';
                  return true;
                });
                if(filteredItems.length===0)return null;
                return(
                  <SectionBlock key={`${type}-${si}`} section={s.section} items={s.items}
                    state={Object.fromEntries(s.items.map((_,ii)=>[ii,itemState[`${si}_${ii}`]||'']))}
                    onSetState={(ii,val)=>setItemSt(si,ii,val)}
                    onOpenProducts={(item,sec)=>setPanel({item,sectionLabel:sec})}
                    filterStatus={filter4}
                    searchText={search4}
                    itemData={Object.fromEntries(s.items.map((_,ii)=>[ii,itemData[`${si}_${ii}`]]))}
                    onSetItemData={(ii,vals)=>setItemData(d=>({...d,[`${si}_${ii}`]:vals}))} />
                );
              })}

              {/* Remarques */}
              <div style={{background:'#fff',borderRadius:12,padding:'16px 18px',marginBottom:12,border:'1.5px solid #e2e8f0'}}>
                <div style={{fontWeight:700,fontSize:14,color:'#1e293b',marginBottom:8}}>📝 Remarques générales</div>
                <textarea value={obs} onChange={e=>setObs(e.target.value)} placeholder="Observations générales, conditions d'accès, points particuliers à noter…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:'inherit',fontSize:13,outline:'none',resize:'vertical',minHeight:80,boxSizing:'border-box',lineHeight:1.5}} />
              </div>

              {/* Matériaux */}
              {products.length>0&&(
                <div style={{background:'#fff',borderRadius:12,padding:'16px 18px',marginBottom:12,border:'1.5px solid #e2e8f0'}}>
                  <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:12,flexWrap:'wrap'}}>
                    <div style={{fontWeight:700,fontSize:14,color:'#1e293b',flex:1}}>🛒 Matériaux sélectionnés ({products.length})</div>
                    <button onClick={()=>setShowQuote(true)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:8,padding:'7px 15px',fontWeight:700,fontSize:12,cursor:'pointer'}}>📄 Créer un devis</button>
                  </div>
                  <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
                    <thead><tr style={{borderBottom:'2px solid #f0f4f8'}}>{['Désignation','Fourn.','Unité','Qté','Total HT',''].map((h,i)=><th key={i} style={{textAlign:'left',padding:'5px 7px',fontWeight:600,color:'#64748b',fontSize:11}}>{h}</th>)}</tr></thead>
                    <tbody>{products.map((p,i)=>{const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);const sup=p.suppliers?.[0]||{};return<tr key={i} style={{borderBottom:'1px solid #f8fafc'}}>
                      <td style={{padding:'6px 7px',fontWeight:500,color:'#1e293b'}}>{p.name}</td>
                      <td style={{padding:'6px 7px',color:'#7c3aed',fontSize:11}}>{sup.name||p.category||'—'}</td>
                      <td style={{padding:'6px 7px',color:'#64748b',fontSize:11}}>{p.unit||'pcs'}</td>
                      <td style={{padding:'6px 7px'}}><div style={{display:'flex',alignItems:'center',gap:3}}><button onClick={()=>updateQty(i,-1)} style={{width:19,height:19,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:11}}>−</button><span style={{fontWeight:700,minWidth:18,textAlign:'center'}}>{p.qty||1}</span><button onClick={()=>updateQty(i,+1)} style={{width:19,height:19,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:11}}>+</button></div></td>
                      <td style={{padding:'6px 7px',color:'#0369a1',fontWeight:700,whiteSpace:'nowrap'}}>{price>0?(price*(p.qty||1)).toFixed(2)+' €':'—'}</td>
                      <td style={{padding:'6px 7px'}}><button onClick={()=>removeProduct(i)} style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',fontSize:13}}>✕</button></td>
                    </tr>;})}
                    </tbody>
                    {totalHT>0&&<tfoot><tr style={{borderTop:'2px solid #e2e8f0'}}><td colSpan={4} style={{padding:'7px 7px',textAlign:'right',fontWeight:800,fontSize:13,color:'#0369a1'}}>Total estimatif HT :</td><td style={{padding:'7px 7px',fontWeight:800,fontSize:14,color:'#0369a1',whiteSpace:'nowrap'}}>{totalHT.toFixed(2)} €</td><td/></tr></tfoot>}
                  </table>
                </div>
              )}

              {/* Signatures */}
              <div style={{background:'#fff',borderRadius:12,padding:'16px 18px',marginBottom:12,border:'1.5px solid #e2e8f0'}}>
                <div style={{fontWeight:700,fontSize:14,color:'#1e293b',marginBottom:12}}>✍️ Signatures</div>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
                  <div>
                    <label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:5}}>Signature du technicien</label>
                    <input value={signTech||technicien} onChange={e=>setSignTech(e.target.value)} placeholder={technicien||'Prénom Nom technicien'} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:"Georgia,serif",fontSize:16,outline:'none',boxSizing:'border-box',fontStyle:'italic',color:'#1e293b'}} />
                    {(signTech||technicien)&&<div style={{fontSize:11,color:'#0ea5e9',marginTop:3}}>✓ Intervenu par {signTech||technicien} le {date}</div>}
                  </div>
                  <div>
                    <label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:5}}>Signature du client (bon pour accord)</label>
                    <input value={signClient} onChange={e=>setSignClient(e.target.value)} placeholder={[prenom,nom].filter(Boolean).join(' ')||denomination||'Nom complet du client'} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:"Georgia,serif",fontSize:16,outline:'none',boxSizing:'border-box',fontStyle:'italic',color:'#1e293b'}} />
                    {signClient&&<div style={{fontSize:11,color:'#16a34a',marginTop:3}}>✓ Lu et approuvé par {signClient}</div>}
                  </div>
                </div>
              </div>

              {/* Enregistrement */}
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',marginBottom:12,overflow:'hidden'}}>
                <div style={{background:'#1e293b',padding:'11px 16px',display:'flex',alignItems:'center',gap:8}}>
                  <span style={{fontWeight:800,fontSize:14,color:'#fff'}}>📋 Enregistrement de la fiche</span>
                  <span style={{marginLeft:'auto',fontSize:11,color:'rgba(255,255,255,.55)'}}>Statut · Sauvegarde</span>
                </div>
                <div style={{padding:16}}>
                  <div style={{fontWeight:700,fontSize:12,color:'#1e293b',marginBottom:8}}>Statut de la visite</div>
                  <div style={{display:'flex',gap:7,flexWrap:'wrap',marginBottom:14}}>
                    {[{k:'en_cours',l:'🔄 En cours',c:'#f59e0b'},{k:'termine',l:'✅ Terminée',c:'#16a34a'},{k:'a_replanifier',l:'🔁 À replanifier',c:'#ef4444'},{k:'attente_pieces',l:'⏳ Attente pièces',c:'#8b5cf6'}].map(s=>(
                      <button key={s.k} onClick={()=>setStatut(s.k)} style={{padding:'7px 13px',borderRadius:9,border:`2px solid ${statut===s.k?s.c:'#e2e8f0'}`,background:statut===s.k?s.c+'22':'#fff',color:statut===s.k?s.c:'#475569',fontWeight:statut===s.k?700:500,fontSize:12,cursor:'pointer',transition:'all .15s'}}>{s.l}</button>
                    ))}
                  </div>
                  <div style={{background:'#f8fafc',borderRadius:9,padding:'10px 14px',marginBottom:14,fontSize:12,color:'#475569',display:'flex',gap:14,flexWrap:'wrap'}}>
                    <span>👤 {[prenom,nom].filter(Boolean).join(' ')||denomination||'—'}</span>
                    <span>📅 {date}</span>
                    <span>🔧 {INTERVENTION_TYPES.find(t=>t.key===type)?.label||type}</span>
                    <span>✅ {totalDone}/{totalItems} ({pct}%)</span>
                    {products.length>0&&<span>🛒 {products.length} produit{products.length>1?'s':''} — {totalHT.toFixed(2)} € HT</span>}
                  </div>
                  <div style={{display:'flex',gap:9,flexWrap:'wrap'}}>
                    <button onClick={saveToHistory} style={{background:saved?'#16a34a':'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'10px 22px',fontWeight:700,fontSize:13,cursor:'pointer',flex:1,minWidth:180,transition:'background .3s'}}>{saved?'✅ Fiche enregistrée !':'💾 Enregistrer la fiche'}</button>
                    <button onClick={()=>setShowQuote(true)} style={{background:'#7c3aed',color:'#fff',border:'none',borderRadius:9,padding:'10px 18px',fontWeight:700,fontSize:12,cursor:'pointer'}}>📄 Créer un devis</button>
                    <button onClick={()=>window.print()} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'10px 16px',fontWeight:600,fontSize:12,cursor:'pointer',color:'#475569'}}>🖨️ Imprimer / PDF</button>
                  </div>
                </div>
              </div>

              <div style={{textAlign:'center',padding:'8px 0 16px',fontSize:11,color:'#94a3b8'}}>Lolirine Pool Store · lolirinepoolstore.be · BCE 0650.891.279</div>
            </div>
          )}

        </div>{/* fin maxWidth */}
      </div>{/* fin scroll */}

      {/* ── Navigation bas ── */}
      <div style={{background:'#fff',borderTop:'1.5px solid #e2e8f0',padding:'14px 24px',display:'flex',justifyContent:'space-between',alignItems:'center',flexShrink:0}}>
        <button onClick={()=>setStep(s=>Math.max(1,s-1))} disabled={step===1}
          style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:10,padding:'10px 22px',fontWeight:600,fontSize:14,cursor:step===1?'default':'pointer',color:step===1?'#cbd5e1':'#475569',opacity:step===1?.4:1}}>
          ← Précédent
        </button>
        <div style={{display:'flex',gap:6}}>
          {[1,2,3,4].map(n=><div key={n} style={{width:8,height:8,borderRadius:'50%',background:step===n?'#0ea5e9':'#e2e8f0',transition:'background .3s'}} />)}
        </div>
        {step<4
          ? <button onClick={()=>canNext[step]&&setStep(s=>s+1)} disabled={!canNext[step]}
              style={{background:canNext[step]?'#0ea5e9':'#cbd5e1',color:'#fff',border:'none',borderRadius:10,padding:'10px 28px',fontWeight:700,fontSize:14,cursor:canNext[step]?'pointer':'default'}}>
              Suivant →
            </button>
          : <button onClick={()=>setShowQuote(true)}
              style={{background:'#7c3aed',color:'#fff',border:'none',borderRadius:10,padding:'10px 24px',fontWeight:700,fontSize:14,cursor:'pointer'}}>
              📄 Créer un devis
            </button>
        }
      </div>

      {/* Modals */}
      {showPlanning&&<PlanningModal type={type} clientName={[prenom,nom].filter(Boolean).join(' ')||denomination||'Client'} startDate={date} onClose={()=>setShowPlanning(false)} />
      }
      {panel&&<ProductPanel item={panel.item} sectionLabel={panel.sectionLabel} onAdd={handleAddProducts} onClose={()=>setPanel(null)} />}
      {showQuote&&<QuoteModal products={products} clientInfo={clientInfo} onClose={()=>setShowQuote(false)} onCreated={()=>{}} />}
      {showHistory&&<HistoryModal onClose={()=>setShowHistory(false)} onLoad={loadRecord} />}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   MOUNT
═══════════════════════════════════════════════════ */
ReactDOM.createRoot(document.getElementById('pool-checklist-root')).render(<PoolChecklist />);    { section:"🔄 Filtration & équipements", items:["Pression manomètre relevée : ___bar","Débit pompe vérifié","Bruit / vibration anormal pompe ?","Programmateur / horloge correct","Vanne multivoies (fuite ?)","Électrolyseur (cellule / production)","Pompe doseuse pH (niveau / fonct.)","Sonde ORP / pH (étalonnage)","Niveau eau ajusté (mi-skimmer)","Alarme piscine testée","Volet / mécanisme vérifié"] },
    { section:"💊 Traitements correctifs appliqués", items:["Correction pH (produit / dose) : ______","Correction TAC (bicarbonate) : ______","Correction TH (anti-calcaire) : ______","Choc chlore (dose) : ______","Algicide préventif appliqué","Floculant / clarifiant appliqué","Anti-phosphates appliqué"] },
    { section:"📋 Observations & suivi", items:["Prochaine vidange partielle recommandée (%)","Prochain contre-lavage prévu","Remplacement média filtrant à prévoir","Pièces à commander : ______","Prochain passage prévu : ______","Rapport envoyé au client : OUI / NON"] },
  ],
  hivernage: [
    { section:"💧 Traitement eau avant hivernage", items:["Analyse complète réalisée","Correction pH à 7,2","Choc chlore hivernage (dose) : ______","Algicide longue durée appliqué","Anti-calcaire / séquestrant appliqué","Floculant si eau trouble","Niveau eau abaissé sous skimmers"] },
    { section:"🔧 Vidange & mise hors service", items:["Contre-lavage filtre effectué","Rinçage filtre effectué","Vidange pompe principale (corps + préfiltre)","Vidange filtre","Vidange vanne multivoies","Vidange tuyauteries (air comprimé / bouchons)","Vanne multivoies en position hivernage","Débranchement pompe + hors tension","Démontage et rangement accessoires"] },
    { section:"❄️ Protection gel", items:["Déconnexion / rangement cellule électrolyseur","Démontage pompe doseuse + rinçage","Protection anti-gel local technique","Isolant sur tuyauteries exposées","Flotteur(s) anti-gel posé(s)","Alimentation électrique générale coupée"] },
    { section:"🪟 Couverture & sécurité hivernage", items:["Volet / couverture en place et verrouillé","Filet anti-feuilles posé","Nettoyage couverture avant pose","Alarme piscine : piles / fonctionnement OK","Signalétique de sécurité en place"] },
    { section:"📋 Fin d'hivernage", items:["Photos état fin de saison","Date hivernage + remise en route estimée notées","Rapport hivernage envoyé client","Commandes produits remise en route anticipées"] },
  ],
  remise_en_route: [
    { section:"🧹 Nettoyage & remise en eau", items:["Retrait couverture / filet — nettoyage + rangement","Remise en eau (niveau mi-skimmer)","Nettoyage fond et parois (dépôts hivernage)","Aspiration résidus fond","Nettoyage skimmers et préfiltre","Nettoyage local technique"] },
    { section:"🔧 Remontage équipements", items:["Remontage / reconnexion pompe principale","Joint préfiltre pompe vérifié / remplacé","Reconnexion vanne multivoies (position filtration)","Remontage cellule électrolyseur","Remontage pompe doseuse + amorçage","Reconnexion sondes pH / ORP","Vérification raccords (absence de fuite)","Mise sous tension + test démarrage pompe"] },
    { section:"💧 1ère analyse & traitement", items:["pH mesuré : ___ → correction : ______","TAC mesuré : ___ → correction : ______","TH mesuré : ___ → correction : ______","Sel mesuré : ___ → correction : ______","Choc chlore d'ouverture (dose) : ______","Algicide préventif de départ","Anti-calcaire / séquestrant","Attente filtration 48h avant analyse définitive"] },
    { section:"⚙️ Vérifications finales", items:["Programmateur réglé (horaires filtration)","Électrolyseur réglé (% production)","PAC / chauffe-eau remis en route","Alarme piscine testée et validée","Volet / couverture testé (course complète)","Éclairage subaquatique testé","Formation / rappel client si besoin","Rapport remise en route envoyé client"] },
  ],
  materiel: [
    { section:"🔧 Diagnostic équipements", items:["Pompe actuelle — marque/modèle/âge : ______","Filtre actuel — type/marque/âge : ______","Électrolyseur actuel — marque/modèle : ______","Volet actuel — type/marque : ______","Robot nettoyeur actuel : ______","Autre matériel concerné : ______"] },
    { section:"📦 Matériel à remplacer", items:["Pompe → remplacer par : ______","Filtre → remplacer par : ______","Électrolyseur (cellule / groupe) → remplacer par : ______","Projecteur(s) LED → remplacer par : ______","Volet / armoire volet → remplacer par : ______","Robot nettoyeur → remplacer par : ______","Autre → remplacer par : ______"] },
    { section:"📦 Accessoires & consommables", items:["Panier skimmer(s) — réf : ______","Panier préfiltre pompe — réf : ______","Médias filtrants — type + qté : ______","Joints vanne multivoies — réf : ______","Manche + balai aspirateur","Raclette / épuisette de rechange","Bâche à bulles — dimensions : ______"] },
    { section:"💊 Produits chimiques à commander", items:["pH- — quantité : ______","pH+ — quantité : ______","Chlore choc — quantité : ______","Chlore lent galets 200g — quantité : ______","Algicide concentré — quantité : ______","Anti-calcaire / séquestrant — quantité : ______","Sel électrolyse (sacs 25kg) — nombre : ______"] },
    { section:"🚚 Logistique & livraison", items:["Mode de livraison : direct chantier / entrepôt Lolirine","Adresse livraison confirmée : ______","Date souhaitée : ______","Fournisseur principal : Fluidra / SCP / autre"] },
    { section:"🛠️ Intervention installation", items:["Démontage ancien matériel","Installation nouveau matériel","Test de fonctionnement","Mise au point / réglages","Formation client"] },
    { section:"✅ Réception matériel", items:["Mise en service validée","Test fonctionnement complet OK","Notice + garanties remises","Bon livraison / facture émis","Ancien matériel évacué"] },
    { section:"📋 Administratif", items:["Devis signé","Commande fournisseur passée","Réf. commande fournisseur : ______","Délai de livraison confirmé : ______"] },
    { section:"🤝 Fin d'intervention", items:["Rapport d'intervention envoyé","Photos avant/après transmises","Contrat d'entretien proposé","Satisfaction client notée : ___/5"] },
  ],
};

const INTERVENTION_TYPES = [
  { key:"construction",    icon:"🏗️", label:"Construction neuve",     color:"#0ea5e9" },
  { key:"renovation",      icon:"🔧", label:"Rénovation",              color:"#8b5cf6" },
  { key:"entretien",       icon:"🧹", label:"Entretien régulier",      color:"#16a34a" },
  { key:"hivernage",       icon:"❄️", label:"Hivernage",               color:"#64748b" },
  { key:"remise_en_route", icon:"🌱", label:"Remise en route",         color:"#f59e0b" },
  { key:"materiel",        icon:"⚙️", label:"Changement de matériel",  color:"#ef4444" },
];

const BASIN_SHAPES = [
  { key:"rectangulaire", icon:"⬜", label:"Rectangulaire" },
  { key:"carre",         icon:"🔲", label:"Carré" },
  { key:"l",             icon:"📐", label:"En L" },
  { key:"ovale",         icon:"🥚", label:"Ovale" },
  { key:"haricot",       icon:"🫘", label:"Haricot" },
  { key:"spa",           icon:"🛁", label:"Spa / Jacuzzi" },
];

/* ═══════════════════════════════════════════════════
   ClientAutocomplete
═══════════════════════════════════════════════════ */
function ClientAutocomplete({ value, onChange, onSelectPartner, placeholder }) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};
  const [suggs, setSuggs] = useState([]);
  const [open, setOpen]   = useState(false);
  const timer = useRef(null);
  const wrap  = useRef(null);
  useEffect(() => {
    const h = e => { if(wrap.current && !wrap.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);
  function handleChange(v) {
    onChange(v);
    clearTimeout(timer.current);
    if(v.length < 2) { setSuggs([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      try {
        const r = await fetch(cfg.partnerEndpoint||'/pool-checklist/search-partner', {
          method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'},
          body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{query:v,limit:8}})
        });
        const d = await r.json();
        const list = d?.result?.partners||[];
        setSuggs(list); setOpen(list.length>0);
      } catch { setSuggs([]); setOpen(false); }
    }, 280);
  }
  const IS = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 13px',fontFamily:'inherit',fontSize:14,outline:'none',boxSizing:'border-box'};
  return (
    <div ref={wrap} style={{position:'relative'}}>
      <input value={value} onChange={e=>handleChange(e.target.value)} onFocus={()=>suggs.length&&setOpen(true)}
        placeholder={placeholder||'Rechercher un client…'} style={IS} />
      {open && (
        <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:900,background:'#fff',border:'1.5px solid #dde4ed',borderRadius:9,boxShadow:'0 8px 24px rgba(0,0,0,.12)',marginTop:3,maxHeight:200,overflowY:'auto'}}>
          {suggs.map((p,i)=>(
            <div key={i} onClick={()=>{onSelectPartner&&onSelectPartner(p);setOpen(false);setSuggs([]);}}
              style={{padding:'9px 14px',cursor:'pointer',fontSize:13,borderBottom:i<suggs.length-1?'1px solid #f0f4f8':'none'}}
              onMouseEnter={e=>e.currentTarget.style.background='#f0f9ff'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
              <div style={{fontWeight:600,color:'#1e293b'}}>{p.name}</div>
              {p.city&&<div style={{fontSize:11,color:'#94a3b8'}}>{p.city}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   AddressAutocomplete
═══════════════════════════════════════════════════ */
function AddressAutocomplete({ value, onChange, placeholder }) {
  const [suggs, setSuggs] = useState([]);
  const [open, setOpen]   = useState(false);
  const [busy, setBusy]   = useState(false);
  const timer = useRef(null);
  const wrap  = useRef(null);
  useEffect(() => {
    const h = e => { if(wrap.current && !wrap.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);
  function handleChange(v) {
    onChange(v);
    clearTimeout(timer.current);
    if(v.length < 4) { setSuggs([]); setOpen(false); return; }
    timer.current = setTimeout(() => doSearch(v), 450);
  }
  async function doSearch(v) {
    setBusy(true);
    try {
      const res = await fetch(
        'https://nominatim.openstreetmap.org/search?'+new URLSearchParams({q:v,countrycodes:'be,lu,fr,nl',format:'json',limit:'6',addressdetails:'1'}),
        {mode:'cors',headers:{'Accept-Language':'fr'}}
      );
      const data = await res.json();
      const list = data.map(d => {
        const a = d.address||{};
        const parts = [a.road&&(a.road+(a.house_number?' '+a.house_number:'')),a.postcode,a.city||a.town||a.village||a.municipality].filter(Boolean);
        return parts.length>1?parts.join(', '):d.display_name.split(',').slice(0,3).join(',').trim();
      }).filter(Boolean);
      setSuggs(list); setOpen(list.length>0);
    } catch { setSuggs([]); setOpen(false); }
    setBusy(false);
  }
  const IS = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 28px 9px 13px',fontFamily:'inherit',fontSize:14,outline:'none',boxSizing:'border-box'};
  return (
    <div ref={wrap} style={{position:'relative'}}>
      <div style={{position:'relative'}}>
        <input value={value} onChange={e=>handleChange(e.target.value)} onFocus={()=>suggs.length&&setOpen(true)}
          placeholder={placeholder||'Adresse du chantier…'} style={IS} />
        <span style={{position:'absolute',right:10,top:'50%',transform:'translateY(-50%)',fontSize:12,color:'#94a3b8',cursor:value?'pointer':'default'}}
          onClick={()=>value&&onChange('')}>{busy?'⌛':value?'✕':''}</span>
      </div>
      {open&&suggs.length>0&&(
        <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:900,background:'#fff',border:'1.5px solid #dde4ed',borderRadius:9,boxShadow:'0 8px 24px rgba(0,0,0,.12)',marginTop:3,maxHeight:200,overflowY:'auto'}}>
          {suggs.map((s,i)=>(
            <div key={i} onClick={()=>{onChange(s);setOpen(false);setSuggs([]);}}
              style={{padding:'8px 13px',cursor:'pointer',fontSize:12,color:'#334155',borderBottom:i<suggs.length-1?'1px solid #f0f4f8':'none',display:'flex',gap:6}}
              onMouseEnter={e=>e.currentTarget.style.background='#f0f9ff'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
              <span style={{color:'#0ea5e9',flexShrink:0}}>📍</span>{s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   HistoryModal
═══════════════════════════════════════════════════ */
function HistoryModal({ onClose, onLoad }) {
  const [records, setRecords] = useState([]);
  useEffect(()=>{ try { setRecords(JSON.parse(localStorage.getItem('pool_checklist_history')||'[]').reverse()); } catch { setRecords([]); } },[]);
  function del(i) {
    try {
      const s=JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
      s.splice(s.length-1-i,1);
      localStorage.setItem('pool_checklist_history',JSON.stringify(s));
      setRecords(s.reverse());
    } catch {}
  }
  return (
    <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,.45)',zIndex:9999,display:'flex',alignItems:'center',justifyContent:'center'}}>
      <div style={{background:'#fff',borderRadius:16,padding:24,width:'min(560px,95vw)',maxHeight:'80vh',display:'flex',flexDirection:'column',boxShadow:'0 20px 60px rgba(0,0,0,.2)'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14}}>
          <h3 style={{margin:0,fontSize:16,color:'#1e293b',fontWeight:700}}>📋 Historique des fiches</h3>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d'}}>✕</button>
        </div>
        {records.length===0
          ? <div style={{textAlign:'center',padding:'30px 0',color:'#94a3b8',fontSize:13}}>Aucune fiche sauvegardée</div>
          : <div style={{overflowY:'auto',flex:1,display:'flex',flexDirection:'column',gap:7}}>
              {records.map((r,i)=>(
                <div key={i} style={{border:'1.5px solid #e8edf3',borderRadius:9,padding:'10px 14px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:10}}>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{r.nom||r.client||'Client non renseigné'} {r.prenom||''}</div>
                    <div style={{fontSize:11,color:'#64748b'}}>{INTERVENTION_TYPES.find(t=>t.key===r.type)?.label||r.type} — {r.date||'—'}</div>
                    {r.adresseChantier&&<div style={{fontSize:11,color:'#94a3b8',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.adresseChantier}</div>}
                  </div>
                  <div style={{display:'flex',gap:7,flexShrink:0}}>
                    <button onClick={()=>{onLoad(r);onClose();}} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:12,fontWeight:600}}>Ouvrir</button>
                    <button onClick={()=>del(i)} style={{background:'none',border:'1.5px solid #fca5a5',color:'#ef4444',borderRadius:7,padding:'5px 8px',cursor:'pointer',fontSize:12}}>🗑</button>
                  </div>
                </div>
              ))}
            </div>
        }
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   ProductPanel — 3 onglets : Recherche · Catalogue · IA
═══════════════════════════════════════════════════ */
function ProductPanel({ item, sectionLabel, onAdd, onClose }) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG||{};
  const [tab,setTab]       = useState(item?'search':'catalog');
  /* Recherche */
  const [q,setQ]           = useState(item||'');
  const [results,setRes]   = useState([]);
  const [sel,setSel]        = useState({});
  const [busy,setBusy]      = useState(false);
  const [src,setSrc]        = useState(null);
  const [sortBy,setSortBy]  = useState('name');
  const [suppFilter,setSuppFilter] = useState(null);
  const [suppliers,setSuppliers]   = useState([]);
  /* Catalogue */
  const [catPath,setCatPath]     = useState([]);
  const [categories,setCategories] = useState([]);
  const [catProds,setCatProds]   = useState([]);
  const [catBusy,setCatBusy]     = useState(false);
  const [catSel,setCatSel]       = useState({});
  /* IA */
  const [aiProds,setAiProds]     = useState([]);
  const [aiSel,setAiSel]         = useState({});
  const [aiBusy,setAiBusy]       = useState(false);
  const [aiDone,setAiDone]       = useState(false);

  /* Chargement initial */
  useEffect(()=>{
    if(item){ runSearch(item); }
    loadCategories(null);
    loadSuppliers();
  },[]);

  async function post(url,params){
    const r=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params})});
    return r.json();
  }

  async function loadSuppliers(){
    try{
      const d=await post('/pool-checklist/suppliers',{});
      setSuppliers(d?.result?.suppliers||[]);
    }catch{}
  }

  async function loadCategories(parentId){
    setCatBusy(true);
    try{
      const d=await post('/pool-checklist/categories',{parent_id:parentId});
      setCategories(d?.result?.categories||[]);
      if(parentId===null)setCatProds([]);
    }catch{}
    setCatBusy(false);
  }

  async function loadCategoryProducts(catId){
    setCatBusy(true);setCatProds([]);
    try{
      const d=await post('/pool-checklist/products',{category_id:catId,limit:50,sort:sortBy,supplier_id:suppFilter});
      setCatProds(d?.result?.products||[]);
    }catch{}
    setCatBusy(false);
  }

  async function runSearch(query){
    if(!query?.trim())return;
    setBusy(true);setRes([]);setSrc(null);setSel({});
    try{
      const d=await post('/pool-checklist/products',{query,limit:30,sort:sortBy,supplier_id:suppFilter});
      const prods=d?.result?.products||[];
      if(prods.length){setRes(prods);setSrc('odoo');setBusy(false);return;}
    }catch{}
    setSrc('empty');setBusy(false);
  }

  async function runAI(){
    if(aiDone)return;
    setAiBusy(true);setAiProds([]);
    try{
      const d=await post('/pool-checklist/ai-suggest',{item_text:item||q,section_label:sectionLabel||''});
      setAiProds(d?.result?.products||[]);setAiDone(true);
    }catch{}
    setAiBusy(false);
  }

  useEffect(()=>{ if(tab==='ai'&&!aiDone) runAI(); },[tab]);

  function drillCat(cat){
    setCatPath(p=>[...p,cat]);
    if(cat.has_children){ loadCategories(cat.id);setCatProds([]); }
    else{ loadCategoryProducts(cat.id);setCategories([]); }
  }
  function upCat(){
    const newPath=catPath.slice(0,-1);
    setCatPath(newPath);
    const parent=newPath.length>0?newPath[newPath.length-1]:null;
    if(parent){
      if(parent.has_children){loadCategories(parent.id);setCatProds([]);}
      else{loadCategoryProducts(parent.id);}
    }else{loadCategories(null);setCatProds([]);}
  }

  /* Sélection unifiée selon l'onglet actif */
  const curSel   = tab==='catalog'?catSel:tab==='ai'?aiSel:sel;
  const curRes   = tab==='catalog'?catProds:tab==='ai'?aiProds:results;
  const setCurSel= tab==='catalog'?setCatSel:tab==='ai'?setAiSel:setSel;
  function toggle(i){setCurSel(s=>({...s,[i]:!s[i]}));}
  function addSel(){
    const chosen=curRes.filter((_,i)=>curSel[i]);
    if(chosen.length)onAdd(chosen);
  }
  const nSel=Object.values(curSel).filter(Boolean).length;

  /* Filtre fournisseur appliqué à la recherche */
  useEffect(()=>{ if(q.trim()&&tab==='search') runSearch(q); },[suppFilter,sortBy]);

  /* Render produit */
  function ProductRow({p,i,selMap}){
    const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);
    const sup=p.suppliers?.[0]||{};
    const isSel=!!selMap[i];
    const [imgErr,setImgErr]=useState(false);
    return(
      <div onClick={()=>toggle(i)} style={{display:'flex',gap:10,padding:'9px 12px',borderRadius:10,border:`1.5px solid ${isSel?'#0ea5e9':'#e8edf3'}`,background:isSel?'rgba(14,165,233,.05)':'#fff',cursor:'pointer',alignItems:'flex-start',marginBottom:4,transition:'all .15s'}}>
        {/* Checkbox */}
        <div style={{width:18,height:18,border:`2px solid ${isSel?'#0ea5e9':'#bbb'}`,borderRadius:4,background:isSel?'#0ea5e9':'transparent',flexShrink:0,marginTop:2,display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',fontSize:11}}>{isSel&&'✓'}</div>
        {/* Image produit */}
        {p.image_url&&!imgErr
          ? <img src={p.image_url} alt="" onError={()=>setImgErr(true)} style={{width:52,height:52,objectFit:'contain',borderRadius:8,border:'1px solid #e2e8f0',background:'#f8fafc',flexShrink:0}} />
          : <div style={{width:52,height:52,borderRadius:8,border:'1px solid #e2e8f0',background:'#f8fafc',flexShrink:0,display:'flex',alignItems:'center',justifyContent:'center',fontSize:20,color:'#cbd5e1'}}>📦</div>
        }
        <div style={{flex:1,minWidth:0}}>
          <div style={{fontWeight:600,fontSize:13,color:'#1e293b',lineHeight:1.3}}>{p.name}</div>
          <div style={{fontSize:11,color:'#64748b',display:'flex',gap:8,flexWrap:'wrap',marginTop:3}}>
            {p.ref&&<span style={{background:'#f1f5f9',borderRadius:4,padding:'1px 6px'}}>Réf: {p.ref}</span>}
            {p.category&&<span style={{color:'#7c3aed'}}>📂 {p.category}</span>}
            {sup.name&&<span style={{color:'#0ea5e9'}}>🏭 {sup.name}</span>}
            {p.unit&&<span>{p.unit}</span>}
          </div>
          {p.description&&<div style={{fontSize:11,color:'#94a3b8',marginTop:2,fontStyle:'italic',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{p.description}</div>}
          {p.note&&<div style={{fontSize:11,color:'#94a3b8',marginTop:2,fontStyle:'italic'}}>{p.note}</div>}
        </div>
        {price>0&&<div style={{flexShrink:0,textAlign:'right'}}><div style={{fontWeight:700,fontSize:14,color:'#16a34a'}}>{price.toFixed(2)} €</div><div style={{fontSize:10,color:'#94a3b8'}}>HT</div></div>}
      </div>
    );
  }

  const TABS=[
    {k:'search', icon:'🔍', label:'Recherche'},
    {k:'catalog',icon:'📂', label:'Catalogue'},
    {k:'ai',     icon:'✨', label:'Suggestions IA'},
  ];

  return(
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.55)',zIndex:9990,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f8fafc',borderRadius:16,width:'min(780px,100%)',maxHeight:'94vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.25)',overflow:'hidden'}}>

        {/* Header */}
        <div style={{background:'#fff',padding:'14px 18px 10px',borderBottom:'1px solid #e2e8f0',display:'flex',gap:10,alignItems:'flex-start',flexShrink:0}}>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:15,color:'#1e293b'}}>🛒 Catalogue Pool Store</div>
            {item&&<div style={{fontSize:11,color:'#64748b',marginTop:2,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>Contexte : {item}</div>}
          </div>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d',flexShrink:0}}>✕</button>
        </div>

        {/* Onglets */}
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',display:'flex',flexShrink:0}}>
          {TABS.map(t=>(
            <button key={t.k} onClick={()=>setTab(t.k)}
              style={{padding:'9px 18px',border:'none',borderBottom:`3px solid ${tab===t.k?'#0ea5e9':'transparent'}`,background:'transparent',cursor:'pointer',fontWeight:tab===t.k?700:500,fontSize:13,color:tab===t.k?'#0ea5e9':'#64748b',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5}}>
              {t.icon} {t.label}
            </button>
          ))}
          {/* Filtre fournisseur (droite) */}
          <div style={{marginLeft:'auto',display:'flex',alignItems:'center',gap:6,padding:'0 14px'}}>
            <select value={suppFilter||''} onChange={e=>setSuppFilter(e.target.value||null)}
              style={{border:'1px solid #e2e8f0',borderRadius:7,padding:'4px 8px',fontSize:11,color:'#475569',background:'#fff',cursor:'pointer',outline:'none'}}>
              <option value="">Tous fournisseurs</option>
              {suppliers.slice(0,8).map(s=><option key={s.id} value={s.id}>{s.name} ({s.product_count})</option>)}
            </select>
            <select value={sortBy} onChange={e=>setSortBy(e.target.value)}
              style={{border:'1px solid #e2e8f0',borderRadius:7,padding:'4px 8px',fontSize:11,color:'#475569',background:'#fff',cursor:'pointer',outline:'none'}}>
              <option value="name">Nom A→Z</option>
              <option value="price_asc">Prix croissant</option>
              <option value="price_desc">Prix décroissant</option>
            </select>
          </div>
        </div>

        {/* Corps scroll */}
        <div style={{flex:1,overflowY:'auto',padding:'12px 14px',minHeight:0}}>

          {/* ── Onglet Recherche ── */}
          {tab==='search'&&(
            <div>
              <div style={{display:'flex',gap:8,marginBottom:12}}>
                <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==='Enter'&&runSearch(q)}
                  placeholder="Référence, nom produit, marque, catégorie…"
                  autoFocus
                  style={{flex:1,border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 14px',fontFamily:'inherit',fontSize:14,outline:'none',background:'#fff'}} />
                <button onClick={()=>runSearch(q)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'9px 18px',fontWeight:700,cursor:'pointer',fontSize:13,whiteSpace:'nowrap'}}>
                  {busy?'…':'Chercher'}
                </button>
              </div>
              {src&&src!=='empty'&&(
                <div style={{marginBottom:8,display:'flex',alignItems:'center',gap:8}}>
                  <span style={{fontSize:11,fontWeight:700,padding:'3px 9px',borderRadius:20,background:'#dcfce7',color:'#166534'}}>✅ {results.length} résultat{results.length>1?'s':''} — Catalogue Lolirine Pool Store</span>
                </div>
              )}
              {busy&&<div style={{padding:40,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:28,marginBottom:10}}>🔄</div>Recherche en cours…</div>}
              {!busy&&src==='empty'&&(
                <div style={{padding:32,textAlign:'center',color:'#94a3b8'}}>
                  <div style={{fontSize:32,marginBottom:8}}>🔍</div>
                  <div style={{fontSize:14,marginBottom:8}}>Aucun résultat dans le catalogue</div>
                  <button onClick={()=>setTab('ai')} style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#92400e',fontWeight:600}}>
                    ✨ Voir les suggestions IA
                  </button>
                </div>
              )}
              {!busy&&!src&&<div style={{padding:32,textAlign:'center',color:'#94a3b8',fontSize:13}}>Tapez votre recherche et appuyez Entrée</div>}
              {results.map((p,i)=><ProductRow key={i} p={p} i={i} selMap={sel} />)}
            </div>
          )}

          {/* ── Onglet Catalogue ── */}
          {tab==='catalog'&&(
            <div>
              {/* Breadcrumb */}
              <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:10,flexWrap:'wrap'}}>
                <span onClick={()=>{setCatPath([]);loadCategories(null);setCatProds([]);}} style={{fontSize:12,color:'#0ea5e9',cursor:'pointer',fontWeight:600}}>📂 Catalogue</span>
                {catPath.map((cat,i)=>(
                  <React.Fragment key={cat.id}>
                    <span style={{color:'#94a3b8',fontSize:12}}>›</span>
                    <span onClick={()=>{const np=catPath.slice(0,i+1);setCatPath(np);if(cat.has_children){loadCategories(cat.id);setCatProds([]);}else loadCategoryProducts(cat.id);}} style={{fontSize:12,color:i===catPath.length-1?'#1e293b':'#0ea5e9',cursor:'pointer',fontWeight:i===catPath.length-1?600:400}}>{cat.name}</span>
                  </React.Fragment>
                ))}
                {catPath.length>0&&<button onClick={upCat} style={{marginLeft:'auto',background:'none',border:'1px solid #e2e8f0',borderRadius:6,padding:'3px 10px',cursor:'pointer',fontSize:11,color:'#64748b'}}>← Retour</button>}
              </div>

              {catBusy&&<div style={{padding:40,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:28,marginBottom:10}}>🔄</div>Chargement…</div>}

              {/* Grille catégories */}
              {!catBusy&&categories.length>0&&(
                <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(170px,1fr))',gap:9,marginBottom:12}}>
                  {categories.map(cat=>(
                    <div key={cat.id} onClick={()=>drillCat(cat)}
                      style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'13px 14px',cursor:'pointer',transition:'all .15s'}}
                      onMouseEnter={e=>{e.currentTarget.style.borderColor='#0ea5e9';e.currentTarget.style.transform='translateY(-1px)';}}
                      onMouseLeave={e=>{e.currentTarget.style.borderColor='#e2e8f0';e.currentTarget.style.transform='none';}}>
                      <div style={{fontWeight:600,fontSize:13,color:'#1e293b',marginBottom:4,lineHeight:1.3}}>{cat.name}</div>
                      <div style={{fontSize:11,color:'#94a3b8',display:'flex',justifyContent:'space-between'}}>
                        <span>{cat.product_count} produit{cat.product_count>1?'s':''}</span>
                        {cat.has_children&&<span style={{color:'#0ea5e9'}}>→</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Produits de la catégorie sélectionnée */}
              {!catBusy&&catProds.length>0&&(
                <div>
                  <div style={{fontSize:12,color:'#64748b',marginBottom:8,fontWeight:600}}>{catProds.length} produit{catProds.length>1?'s':''}</div>
                  {catProds.map((p,i)=><ProductRow key={i} p={p} i={i} selMap={catSel} />)}
                </div>
              )}

              {!catBusy&&categories.length===0&&catProds.length===0&&(
                <div style={{padding:32,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucun contenu dans cette catégorie</div>
              )}
            </div>
          )}

          {/* ── Onglet IA ── */}
          {tab==='ai'&&(
            <div>
              <div style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:10,padding:'10px 14px',marginBottom:12,fontSize:12,color:'#92400e'}}>
                ✨ Suggestions générées par Claude AI en fonction du contexte de la check-list. Ces produits ne sont pas liés au catalogue Odoo — vérifiez la disponibilité.
              </div>
              {aiBusy&&<div style={{padding:40,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:28,marginBottom:10}}>✨</div>Génération des suggestions IA…</div>}
              {!aiBusy&&aiProds.length===0&&aiDone&&<div style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucune suggestion IA disponible.</div>}
              {!aiBusy&&!aiDone&&<div style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Chargement des suggestions…</div>}
              {aiProds.map((p,i)=><ProductRow key={i} p={p} i={i} selMap={aiSel} />)}
              {aiDone&&aiProds.length>0&&(
                <div style={{marginTop:10}}>
                  <button onClick={()=>{setAiDone(false);setAiProds([]);runAI();}} style={{background:'none',border:'1px solid #e2e8f0',borderRadius:8,padding:'6px 14px',cursor:'pointer',fontSize:12,color:'#64748b'}}>↺ Régénérer les suggestions</button>
                </div>
              )}
            </div>
          )}

        </div>{/* fin scroll */}

        {/* Footer */}
        <div style={{background:'#fff',borderTop:'1.5px solid #e2e8f0',padding:'11px 18px',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
          <span style={{fontSize:12,color:'#64748b',flex:1}}>{nSel>0?`${nSel} produit${nSel>1?'s':''} sélectionné${nSel>1?'s':''}`:''}</span>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#475569',fontWeight:600}}>Annuler</button>
          <button onClick={addSel} disabled={!nSel}
            style={{background:nSel?'#0ea5e9':'#cbd5e1',color:'#fff',border:'none',borderRadius:9,padding:'8px 22px',fontWeight:700,cursor:nSel?'pointer':'default',fontSize:13,whiteSpace:'nowrap'}}>
            Ajouter {nSel?`(${nSel})`:'la sélection'}
          </button>
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════
   ITEM SCHEMA DETECTION — détection automatique des champs
   à encoder par item de checklist
═══════════════════════════════════════════════════ */
const ITEM_SCHEMAS = {
  /* Mesures eau */
  ph:          { icon:'💧', title:'Mesure pH',           unit:'',     fields:[{k:'mesure',l:'Valeur mesurée',t:'number',step:.01,min:0,max:14,placeholder:'7.4'},{k:'cible',l:'Cible',t:'text',dfl:'7,2 – 7,6',ro:true},{k:'correction',l:'Correction apportée',t:'text'},{k:'produit',l:'Produit utilisé',t:'text'},{k:'dose',l:'Dose (g ou mL)',t:'number',step:.1}] },
  tac:         { icon:'💧', title:'Mesure TAC',          unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:1,placeholder:'100'},{k:'cible',l:'Cible',t:'text',dfl:'80 – 120 mg/L',ro:true},{k:'correction',l:'Correction',t:'text'},{k:'produit',l:'Produit (bicarbonate/CO2)',t:'text'},{k:'dose',l:'Dose',t:'number',step:.1}] },
  th:          { icon:'💧', title:'Mesure TH',           unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:1,placeholder:'200'},{k:'cible',l:'Cible',t:'text',dfl:'150 – 300 mg/L',ro:true},{k:'correction',l:'Correction',t:'text'}] },
  chlore:      { icon:'🧪', title:'Mesure Chlore',       unit:'mg/L', fields:[{k:'libre',l:'Chlore libre (mg/L)',t:'number',step:.01,placeholder:'2.0'},{k:'combine',l:'Chlore combiné (mg/L)',t:'number',step:.01,placeholder:'0.3'},{k:'cible',l:'Cible libre',t:'text',dfl:'1,0 – 3,0 mg/L',ro:true},{k:'produit',l:'Produit choc',t:'text'},{k:'dose',l:'Dose (g ou mL)',t:'number',step:.1}] },
  sel:         { icon:'🧂', title:'Taux de sel',         unit:'g/L',  fields:[{k:'mesure',l:'Taux mesuré (g/L)',t:'number',step:.1,placeholder:'5.0'},{k:'cible',l:'Cible électrolyseur',t:'number',step:.1,placeholder:'5.0'},{k:'correction',l:'Correction (kg sel)',t:'number',step:.5}] },
  cyanurate:   { icon:'☀️', title:'Cyanurate',           unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:1,placeholder:'40'},{k:'cible',l:'Cible max',t:'text',dfl:'< 75 mg/L',ro:true}] },
  phosphates:  { icon:'🌿', title:'Phosphates',          unit:'mg/L', fields:[{k:'mesure',l:'Valeur mesurée (mg/L)',t:'number',step:.01,placeholder:'0.05'},{k:'cible',l:'Cible max',t:'text',dfl:'< 0,1 mg/L',ro:true},{k:'produit',l:'Anti-phosphates utilisé',t:'text'}] },
  temperature: { icon:'🌡️', title:'Température',        unit:'°C',   fields:[{k:'eau',l:'Température eau (°C)',t:'number',step:.5,placeholder:'24'},{k:'air',l:'Température air (°C)',t:'number',step:.5},{k:'turbidite',l:'Turbidité',t:'select',opts:['Limpide','Légèrement trouble','Trouble','Verte']}] },
  orp:         { icon:'⚡', title:'ORP / Redox',         unit:'mV',   fields:[{k:'mesure',l:'Valeur ORP (mV)',t:'number',step:1,placeholder:'700'},{k:'cible',l:'Cible',t:'text',dfl:'650 – 750 mV',ro:true}] },
  /* Équipements — nombres */
  skimmer:     { icon:'🔧', title:'Skimmers',           unit:'',     fields:[{k:'nombre',l:'Nombre de skimmers',t:'integer',min:1,max:10,placeholder:'2'},{k:'marque',l:'Marque / modèle',t:'text'},{k:'diam',l:'Largeur goulotte (mm)',t:'number',step:1,placeholder:'180'},{k:'etat',l:'État',t:'select',opts:['Bon état','Joint à remplacer','Collerette fissurée','À remplacer']}] },
  bonde:       { icon:'🔧', title:'Bondes de fond',    unit:'',     fields:[{k:'nombre',l:'Nombre de bondes',t:'integer',min:1,max:6,placeholder:'2'},{k:'marque',l:'Marque / modèle',t:'text'},{k:'etancheite',l:'Étanchéité',t:'select',opts:['OK','Suintement','Fuite','À remplacer']}] },
  refoulement: { icon:'🔧', title:'Refoulements',       unit:'',     fields:[{k:'nombre',l:'Nombre de refoulements',t:'integer',min:1,max:12,placeholder:'4'},{k:'emplacement',l:'Emplacement',t:'text',placeholder:'Fond + parois'},{k:'orientation',l:'Orientation',t:'select',opts:['Fixe','Orientable','Rotatif']}] },
  pompe:       { icon:'⚙️', title:'Pompe',              unit:'',     fields:[{k:'marque',l:'Marque / modèle',t:'text'},{k:'puissance',l:'Puissance (kW)',t:'number',step:.01,placeholder:'0.55'},{k:'debit',l:'Débit (m³/h)',t:'number',step:.5,placeholder:'10'},{k:'age',l:'Âge (années)',t:'integer',min:0,max:30},{k:'etat',l:'État général',t:'select',opts:['Bon état','Bruit','Vibration','Fuite','Hs']},{k:'pression',l:'Pression manomètre (bar)',t:'number',step:.1}] },
  filtre:      { icon:'🔵', title:'Filtre',             unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['Sable','Verre filtrant','Cartouche','Diatomées']},{k:'marque',l:'Marque / modèle',t:'text'},{k:'volume',l:'Volume filtrant (m³)',t:'number',step:.05,placeholder:'0.35'},{k:'pression',l:'Pression actuelle (bar)',t:'number',step:.05,placeholder:'0.8'},{k:'seuil',l:'Seuil contre-lavage (bar)',t:'number',step:.05,dfl:.5},{k:'media',l:'Média filtrant',t:'text',placeholder:'Sable 0,4–0,8 mm'}] },
  electrolyse: { icon:'⚡', title:'Électrolyseur',      unit:'',     fields:[{k:'marque',l:'Marque / modèle',t:'text'},{k:'capacite',l:'Capacité (m³)',t:'number',step:5,placeholder:'60'},{k:'production',l:'Production réglée (%)',t:'number',step:1,min:0,max:100,placeholder:'60'},{k:'etat_cellule',l:'État cellule',t:'select',opts:['Propre','Tartrée légère','Tartrée forte','Défaillante','À remplacer']},{k:'age_cellule',l:'Âge cellule (années)',t:'integer',min:0,max:10}] },
  pac:         { icon:'🌡️', title:'Pompe à chaleur',   unit:'',     fields:[{k:'marque',l:'Marque / modèle',t:'text'},{k:'puissance',l:'Puissance (kW)',t:'number',step:.5,placeholder:'12'},{k:'cop',l:'COP',t:'number',step:.1,placeholder:'5'},{k:'temp_consigne',l:'Température consigne (°C)',t:'number',step:.5,placeholder:'28'},{k:'etat',l:'État',t:'select',opts:['Fonctionnel','Bruit','Erreur affichée','Hors service']}] },
  /* Dimensions / surfaces */
  dimensions:  { icon:'📐', title:'Dimensions bassin',  unit:'',     fields:[{k:'longueur',l:'Longueur (m)',t:'number',step:.1,placeholder:'10'},{k:'largeur',l:'Largeur (m)',t:'number',step:.1,placeholder:'5'},{k:'prof_min',l:'Profondeur mini (m)',t:'number',step:.1,placeholder:'1.2'},{k:'prof_max',l:'Profondeur maxi (m)',t:'number',step:.1,placeholder:'2'},{k:'forme',l:'Forme',t:'select',opts:['Rectangulaire','Carré','L','Ovale','Haricot','Spa']}] },
  surface:     { icon:'📐', title:'Surface / Volume',   unit:'m²',   fields:[{k:'surface',l:'Surface (m²)',t:'number',step:.5},{k:'volume',l:'Volume (m³)',t:'number',step:.5},{k:'plage',l:'Surface plage (m²)',t:'number',step:.5}] },
  /* Traitements */
  traitement:  { icon:'💊', title:'Traitement appliqué',unit:'',     fields:[{k:'produit',l:'Produit utilisé',t:'text'},{k:'dose',l:'Dose (g / mL / L)',t:'number',step:.1},{k:'dilution',l:'Dilution préalable',t:'select',opts:['Non','Oui 10%','Oui 50%']},{k:'heure',l:'Heure application',t:'time'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Pression / débit */
  pression:    { icon:'🔵', title:'Pression',           unit:'bar',  fields:[{k:'pression',l:'Pression (bar)',t:'number',step:.05,placeholder:'0.8'},{k:'alarme',l:'Seuil alarme (bar)',t:'number',step:.05,placeholder:'1.5'},{k:'etat',l:'État',t:'select',opts:['Normal','Élevée — contre-lavage requis','Basse — contrôler pompe']}] },
  debit:       { icon:'💧', title:'Débit',              unit:'m³/h', fields:[{k:'debit',l:'Débit mesuré (m³/h)',t:'number',step:.5},{k:'debit_nominal',l:'Débit nominal (m³/h)',t:'number',step:.5},{k:'duree',l:'Durée filtration/jour (h)',t:'number',step:.5,placeholder:'8'}] },
  /* Planning / dates */
  date_prochaine: { icon:'📅', title:'Prochain passage',unit:'',    fields:[{k:'date',l:'Date prévue',t:'date'},{k:'type',l:'Type de passage',t:'select',opts:['Entretien standard','Analyse complète','Hivernage','Remise en route','Urgence']},{k:'technicien',l:'Technicien',t:'text'},{k:'notes',l:'Notes',t:'textarea'}] },
  /* Première mise en eau */
  mise_en_eau: { icon:'💧', title:'Première mise en eau',unit:'',   fields:[{k:'volume_rempli',l:'Volume rempli (m³)',t:'number',step:.5},{k:'duree_remplissage',l:'Durée remplissage (h)',t:'number',step:.5},{k:'turbidite',l:'Turbidité initiale',t:'select',opts:['Limpide','Légèrement trouble','Trouble']},{k:'choc_initial',l:'Choc chlore initial (g)',t:'number',step:50},{k:'ph_initial',l:'pH initial',t:'number',step:.01},{k:'sel_initial',l:'Sel initial (kg)',t:'number',step:5},{k:'floculation',l:'Floculation appliquée',t:'select',opts:['Non','Oui — floculant liquide','Oui — cartouche']},{k:'surveillance',l:'Durée surveillance (h)',t:'integer',min:1,max:72,placeholder:'24'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Éclairage */
  eclairage:   { icon:'💡', title:'Éclairage',          unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['LED RGB','LED blanc','Halogène (obsolète)','Fibre optique']},{k:'puissance',l:'Puissance (W)',t:'number',step:1},{k:'nombre',l:'Nombre',t:'integer',min:1,max:20},{k:'couleur',l:'Couleur / référence',t:'text'},{k:'etat',l:'État',t:'select',opts:['Fonctionnel','Défaillant','À remplacer']}] },
  /* Alarme / sécurité */
  alarme:      { icon:'🔔', title:'Alarme piscine',     unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['Détection de chute (immergé)','Détection de chute (barrière)','Barrière périmétrale','Couverture sécurisée']},{k:'marque',l:'Marque / modèle',t:'text'},{k:'norme',l:'Norme',t:'select',opts:['NF P 90-307 (chute)','NF P 90-308 (barrière)','NF P 90-306','Autre']},{k:'test',l:'Test fonctionnel',t:'select',opts:['OK','Défaillant — piles','Défaillant — capteur','Hors service']},{k:'date_test',l:'Date dernier test',t:'date'}] },
  /* Revêtement */
  revetement:  { icon:'🎨', title:'Revêtement',         unit:'',     fields:[{k:'type',l:'Type',t:'select',opts:['Liner PVC','Carrelage','Enduit hydraulique','Résine','Membrane armée','Béton brut']},{k:'age',l:'Âge (années)',t:'integer',min:0,max:30},{k:'etat',l:'État général',t:'select',opts:['Excellent','Bon','Usé','Fissuré','À remplacer']},{k:'surface',l:'Surface (m²)',t:'number',step:.5},{k:'couleur',l:'Couleur / référence',t:'text'}] },
  /* Câblage / électrique */
  electrique:  { icon:'⚡', title:'Installation électrique',unit:'', fields:[{k:'coffret',l:'Coffret IP',t:'select',opts:['IP65','IP66','IP54','Autre']},{k:'diff',l:'Disjoncteur différentiel 30mA',t:'select',opts:['Présent et testé','Présent — non testé','Absent']},{k:'equi',l:'Liaison équipotentielle',t:'select',opts:['Conforme','Non vérifiée','Non conforme']},{k:'section',l:'Section câbles (mm²)',t:'number',step:.5,placeholder:'2.5'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Générique texte */
  texte:       { icon:'✏️', title:'Informations',       unit:'',     fields:[{k:'valeur',l:'Valeur / Information',t:'text'},{k:'observations',l:'Observations',t:'textarea'}] },
  /* Générique nombre */
  nombre:      { icon:'🔢', title:'Quantité / Valeur',  unit:'',     fields:[{k:'valeur',l:'Valeur',t:'number',step:.01},{k:'unite',l:'Unité',t:'text'},{k:'observations',l:'Notes',t:'text'}] },
};

/* Détection automatique du schéma à partir du texte de l'item */
function detectSchema(text) {
  const t = text.toLowerCase();
  if (t.match(/\bph\b.*(?:mesur|cible|7[,.]2)/)) return 'ph';
  if (t.match(/\btac\b|alcalinité/)) return 'tac';
  if (t.match(/\bth\b|dureté/)) return 'th';
  if (t.match(/chlore/)) return 'chlore';
  if (t.match(/\bsel\b.*(?:électrolys|g\/l|mesur)/)) return 'sel';
  if (t.match(/cyanurate/)) return 'cyanurate';
  if (t.match(/phosphate/)) return 'phosphates';
  if (t.match(/température.*eau|°c/)) return 'temperature';
  if (t.match(/\borp\b|redox/)) return 'orp';
  if (t.match(/skimmer/)) return 'skimmer';
  if (t.match(/bonde.*fond|fond.*bonde/)) return 'bonde';
  if (t.match(/refoulement/)) return 'refoulement';
  if (t.match(/pompe.*(?:marque|modèle|kw|m³\/h|puissance|âge)/)) return 'pompe';
  if (t.match(/filtre.*(?:sable|cartouche|volume|média|pression)/)) return 'filtre';
  if (t.match(/électrolyseur|electrolyse/)) return 'electrolyse';
  if (t.match(/pompe à chaleur|pac\b/)) return 'pac';
  if (t.match(/dimensions?.*(?:l\s*[×x]|prof)/i) || t.match(/l\s*[×x]\s*l\s*[×x]\s*prof/i)) return 'dimensions';
  if (t.match(/surface.*m²|volume.*m³/)) return 'surface';
  if (t.match(/pression.*(?:manomètre|bar)/)) return 'pression';
  if (t.match(/débit.*m³\/h/)) return 'debit';
  if (t.match(/prochain.*passage|prochain.*contre-lavage|prochaine.*visite/)) return 'date_prochaine';
  if (t.match(/première mise en eau|mise en eau.*contrôlée|remplissage.*contrôlé/)) return 'mise_en_eau';
  if (t.match(/projecteur|éclairage|led.*subaquatique/)) return 'eclairage';
  if (t.match(/alarme.*piscine|détection/)) return 'alarme';
  if (t.match(/revêtement|liner|carrelage/)) return 'revetement';
  if (t.match(/coffret|disjoncteur|équipotentielle|câbl/)) return 'electrique';
  if (t.match(/traitement.*(?:correctif|appliqué|choc)|choc.*chlore|algicide|floculant/)) return 'traitement';
  if (t.match(/nombre\s*[_:]/i) || t.match(/nombre\s+___/i)) return 'nombre';
  if (t.match(/______+|___\s*$/)) return 'texte';
  return null;
}

/* ═══════════════════════════════════════════════════
   ItemDetailModal — fenêtre d'encodage contextuelle
═══════════════════════════════════════════════════ */
function ItemDetailModal({ item, schemaKey, savedValues, onSave, onClose }) {
  const schema = ITEM_SCHEMAS[schemaKey] || ITEM_SCHEMAS.texte;
  const [vals, setVals] = useState(() => {
    const init = {};
    schema.fields.forEach(f => { init[f.k] = (savedValues && savedValues[f.k] !== undefined) ? savedValues[f.k] : (f.dfl || ''); });
    return init;
  });

  function set(k, v) { setVals(s => ({...s, [k]: v})); }

  /* Calculs dérivés en temps réel */
  const derived = {};
  if (schemaKey === 'dimensions' && vals.longueur && vals.largeur) {
    derived.surface = (parseFloat(vals.longueur) * parseFloat(vals.largeur)).toFixed(1);
    if (vals.prof_max) derived.volume = (parseFloat(vals.longueur) * parseFloat(vals.largeur) * parseFloat(vals.prof_max) * 0.8).toFixed(1);
  }
  if (schemaKey === 'ph' || schemaKey === 'tac' || schemaKey === 'th' || schemaKey === 'sel') {
    const mesure = parseFloat(vals.mesure || vals.mesure);
    if (!isNaN(mesure)) {
      const ranges = {ph:[7.2,7.6], tac:[80,120], th:[150,300], sel:[4.5,5.5]};
      const r = ranges[schemaKey];
      if (r) derived.statut = mesure < r[0] ? '📉 En dessous — correction nécessaire' : mesure > r[1] ? '📈 Au-dessus — correction nécessaire' : '✅ Dans la plage cible';
    }
  }

  const IS = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'9px 12px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'};

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.55)',zIndex:9998,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#fff',borderRadius:16,width:'min(620px,100%)',maxHeight:'90vh',display:'flex',flexDirection:'column',boxShadow:'0 24px 80px rgba(0,0,0,.25)',overflow:'hidden'}}>
        {/* Header */}
        <div style={{background:'#0ea5e9',padding:'14px 18px',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
          <span style={{fontSize:22}}>{schema.icon}</span>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:16,color:'#fff'}}>{schema.title}</div>
            <div style={{fontSize:11,color:'rgba(255,255,255,.75)',marginTop:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{item}</div>
          </div>
          <button onClick={onClose} style={{background:'rgba(255,255,255,.2)',border:'none',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:13,color:'#fff'}}>✕</button>
        </div>
        {/* Corps */}
        <div style={{overflowY:'auto',padding:'18px 20px',display:'flex',flexDirection:'column',gap:14}}>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
            {schema.fields.map(f => (
              <div key={f.k} style={{gridColumn:f.t==='textarea'?'1/-1':undefined}}>
                <label style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',display:'block',marginBottom:4}}>{f.l}{f.unit?` (${f.unit})`:''}</label>
                {f.t === 'select' ? (
                  <select value={vals[f.k]||''} onChange={e=>set(f.k,e.target.value)} style={{...IS,background:'#fff',cursor:'pointer'}}>
                    <option value="">— Choisir —</option>
                    {(f.opts||[]).map(o=><option key={o} value={o}>{o}</option>)}
                  </select>
                ) : f.t === 'textarea' ? (
                  <textarea value={vals[f.k]||''} onChange={e=>set(f.k,e.target.value)} rows={3} placeholder={f.placeholder||''} style={{...IS,resize:'vertical',lineHeight:1.5}} />
                ) : (
                  <input type={f.t==='integer'?'number':f.t||'text'} value={vals[f.k]||''} onChange={e=>set(f.k,e.target.value)}
                    readOnly={f.ro} min={f.min} max={f.max} step={f.step} placeholder={f.placeholder||f.dfl||''}
                    style={{...IS,background:f.ro?'#f8fafc':'#fff',color:f.ro?'#94a3b8':'#1e293b'}} />
                )}
              </div>
            ))}
          </div>
          {/* Calculs dérivés */}
          {Object.keys(derived).length > 0 && (
            <div style={{background:'#eff9ff',borderRadius:10,padding:'12px 16px',display:'flex',gap:16,flexWrap:'wrap'}}>
              {derived.surface && <div style={{fontSize:13,color:'#0369a1'}}><strong>Surface :</strong> {derived.surface} m²</div>}
              {derived.volume  && <div style={{fontSize:13,color:'#0369a1'}}><strong>Volume estimé :</strong> {derived.volume} m³</div>}
              {derived.statut  && <div style={{fontSize:13,fontWeight:600,color:derived.statut.startsWith('✅')?'#16a34a':'#e24b4a'}}>{derived.statut}</div>}
            </div>
          )}
        </div>
        {/* Footer */}
        <div style={{padding:'12px 20px',borderTop:'1px solid #f0f4f8',display:'flex',justifyContent:'flex-end',gap:9,flexShrink:0}}>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#475569',fontWeight:600}}>Annuler</button>
          <button onClick={()=>onSave(vals)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'8px 22px',fontWeight:700,fontSize:13,cursor:'pointer'}}>💾 Enregistrer</button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   PlanningModal — planning prévisionnel par type
═══════════════════════════════════════════════════ */
const PLANNING_TEMPLATES = {
  construction: [
    {phase:'Études & préparation',    days:7,  color:'#7c3aed', tasks:['Étude de sol','Validation devis','Obtention permis','Commande matériaux']},
    {phase:'Terrassement & VRD',      days:5,  color:'#0ea5e9', tasks:['Terrassement','Voirie & réseaux','Coffrage fond']},
    {phase:'Génie civil',             days:10, color:'#0369a1', tasks:['Coulage béton','Pose armatures','Étanchéité primaire']},
    {phase:'Plomberie & hydraulique', days:5,  color:'#16a34a', tasks:['Tuyauteries','Pose skimmers & bondes','Raccordements']},
    {phase:'Électricité & éclairage', days:4,  color:'#f59e0b', tasks:['Câblage','Coffret IP65','Projecteurs LED','Équipotentielle']},
    {phase:'Revêtement & finitions',  days:6,  color:'#ef4444', tasks:['Pose liner/carrelage','Margelles','Plage','Douche']},
    {phase:'Équipements filtration',  days:3,  color:'#8b5cf6', tasks:['Local technique','Pompe/filtre','Électrolyseur']},
    {phase:'Mise en eau & réglages',  days:3,  color:'#0ea5e9', tasks:['Remplissage','Analyses','Paramétrage','Formation client']},
  ],
  renovation: [
    {phase:'Diagnostic complet',      days:1,  color:'#7c3aed', tasks:['Inspection structure','Test étanchéité','Rapport diagnostic']},
    {phase:'Vidange & préparation',   days:2,  color:'#0ea5e9', tasks:['Vidange bassin','Nettoyage fond','Dépose revêtement']},
    {phase:'Travaux structure',       days:5,  color:'#ef4444', tasks:['Reprise fissures','Traitement armatures','Enduit de fond']},
    {phase:'Nouveau revêtement',      days:4,  color:'#16a34a', tasks:['Pose liner/carrelage/résine','Scellements','Joints']},
    {phase:'Équipements',             days:3,  color:'#f59e0b', tasks:['Pompe','Filtre','Électrolyseur','Éclairage']},
    {phase:'Remise en eau',           days:2,  color:'#0369a1', tasks:['Remplissage','Analyses','Réglages','Réception']},
  ],
  entretien: [
    {phase:'Analyse & mesures',       days:0.1, color:'#0ea5e9', tasks:['pH, TAC, TH, Chlore','Sel, Cyanurate, Phosphates','Turbidité']},
    {phase:'Nettoyage',               days:0.2, color:'#16a34a', tasks:['Aspiration fond','Brossage parois','Skimmers & préfiltre']},
    {phase:'Filtration',              days:0.1, color:'#7c3aed', tasks:['Contre-lavage si nécessaire','Vérif équipements']},
    {phase:'Traitements correctifs',  days:0.1, color:'#f59e0b', tasks:['Corrections mesures','Choc chlore si besoin']},
    {phase:'Rapport',                 days:0.1, color:'#64748b', tasks:['Rapport envoyé client','Recommandations']},
  ],
  hivernage: [
    {phase:'Traitement eau',          days:1,  color:'#0ea5e9', tasks:['Analyse complète','Choc chlore','Algicide hivernage']},
    {phase:'Mise hors service',       days:1,  color:'#64748b', tasks:['Vidange pompe/filtre','Tuyauteries','Débranchement']},
    {phase:'Protection gel',          days:0.5,color:'#3b82f6', tasks:['Flotteurs anti-gel','Isolation','Local technique']},
    {phase:'Couverture & sécurité',   days:0.5,color:'#8b5cf6', tasks:['Pose couverture','Filet','Alarme']},
  ],
  remise_en_route: [
    {phase:'Nettoyage général',       days:0.5,color:'#16a34a', tasks:['Retrait couverture','Nettoyage bassin','Local technique']},
    {phase:'Remontage équipements',   days:1,  color:'#0ea5e9', tasks:['Pompe','Sondes','Électrolyseur','Raccordements']},
    {phase:'Mise en eau',             days:1,  color:'#0369a1', tasks:['Remplissage','Test étanchéité']},
    {phase:'Analyses & réglages',     days:1,  color:'#f59e0b', tasks:['Analyses complètes','Réglages équipements','Filtration 48h']},
  ],
  materiel: [
    {phase:'Commande fournisseur',    days:5,  color:'#7c3aed', tasks:['Confirmation devis','Bon de commande','Confirmation délai']},
    {phase:'Réception matériel',      days:1,  color:'#0ea5e9', tasks:['Contrôle livraison','Vérification conformité']},
    {phase:'Démontage ancien',        days:0.5,color:'#ef4444', tasks:["Dépose ancien matériel","Mise hors service","Évacuation"]},
    {phase:'Installation',            days:1,  color:'#16a34a', tasks:['Pose nouveau matériel','Raccordements','Câblage']},
    {phase:'Mise en service',         days:0.5,color:'#f59e0b', tasks:['Tests','Réglages','Formation client','Réception']},
  ],
};

function PlanningModal({ type, clientName, startDate, onClose }) {
  const template = PLANNING_TEMPLATES[type] || PLANNING_TEMPLATES.entretien;
  const [start, setStart] = useState(startDate || new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');

  const totalDays = template.reduce((a,p) => a + p.days, 0);

  /* Calculer les dates de chaque phase */
  const phases = [];
  let cursor = new Date(start);
  template.forEach(p => {
    const s = new Date(cursor);
    const e = new Date(cursor);
    e.setDate(e.getDate() + Math.ceil(p.days));
    // Sauter les week-ends
    while (e.getDay() === 0 || e.getDay() === 6) e.setDate(e.getDate() + 1);
    phases.push({...p, startDate: new Date(s), endDate: new Date(e)});
    cursor = new Date(e);
    cursor.setDate(cursor.getDate() + 1);
  });

  const projectEnd = phases[phases.length-1]?.endDate;
  const fmt = d => d?.toLocaleDateString('fr-BE',{day:'2-digit',month:'2-digit',year:'2-digit'}) || '';

  function exportPDF() { window.print(); }

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.55)',zIndex:9997,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f8fafc',borderRadius:16,width:'min(820px,100%)',maxHeight:'92vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.25)',overflow:'hidden'}}>

        {/* Header */}
        <div style={{background:'#1e293b',padding:'14px 20px',display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
          <span style={{fontSize:24}}>📅</span>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:16,color:'#fff'}}>Planning prévisionnel</div>
            <div style={{fontSize:11,color:'rgba(255,255,255,.6)',marginTop:1}}>{clientName||'Client'} · {totalDays} jours ouvrés · Fin estimée : {fmt(projectEnd)}</div>
          </div>
          <button onClick={exportPDF} style={{background:'rgba(255,255,255,.1)',border:'1px solid rgba(255,255,255,.3)',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:12,color:'#fff'}}>🖨️ PDF</button>
          <button onClick={onClose} style={{background:'rgba(255,255,255,.2)',border:'none',borderRadius:7,padding:'5px 12px',cursor:'pointer',fontSize:13,color:'#fff'}}>✕</button>
        </div>

        <div style={{overflowY:'auto',flex:1,padding:'18px 20px'}}>

          {/* Date de début */}
          <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'14px 18px',marginBottom:16,display:'flex',gap:16,alignItems:'center',flexWrap:'wrap'}}>
            <div>
              <label style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',display:'block',marginBottom:4}}>Date de début</label>
              <input type="date" value={start} onChange={e=>setStart(e.target.value)}
                style={{border:'1.5px solid #dde4ed',borderRadius:8,padding:'7px 12px',fontFamily:'inherit',fontSize:14,outline:'none'}} />
            </div>
            <div style={{flex:1,display:'flex',gap:10,flexWrap:'wrap'}}>
              <div style={{background:'#eff9ff',borderRadius:9,padding:'8px 14px',fontSize:12}}>
                <div style={{fontWeight:700,color:'#0369a1'}}>Début</div>
                <div style={{color:'#475569'}}>{fmt(new Date(start))}</div>
              </div>
              <div style={{background:'#f0fdf4',borderRadius:9,padding:'8px 14px',fontSize:12}}>
                <div style={{fontWeight:700,color:'#16a34a'}}>Fin estimée</div>
                <div style={{color:'#475569'}}>{fmt(projectEnd)}</div>
              </div>
              <div style={{background:'#f8fafc',borderRadius:9,padding:'8px 14px',fontSize:12}}>
                <div style={{fontWeight:700,color:'#475569'}}>Durée totale</div>
                <div style={{color:'#64748b'}}>{totalDays} jours ouvrés</div>
              </div>
            </div>
          </div>

          {/* Gantt simplifié */}
          <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',marginBottom:16,overflow:'hidden'}}>
            <div style={{background:'#f8fafc',padding:'10px 16px',borderBottom:'1px solid #e2e8f0',fontWeight:700,fontSize:13,color:'#1e293b',display:'flex',gap:16}}>
              <span style={{width:180,flexShrink:0}}>Phase</span>
              <span style={{flex:1}}>Timeline</span>
              <span style={{width:140,textAlign:'right',flexShrink:0}}>Dates</span>
            </div>
            {phases.map((p,i)=>{
              const pct = Math.max(5, Math.round(p.days / totalDays * 100));
              return (
                <div key={i} style={{borderTop:i>0?'1px solid #f8fafc':'none',padding:'10px 16px',display:'flex',gap:16,alignItems:'center'}}>
                  <div style={{width:180,flexShrink:0}}>
                    <div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{p.phase}</div>
                    <div style={{fontSize:11,color:'#94a3b8',marginTop:1}}>{p.days < 1 ? Math.round(p.days*8)+'h' : p.days+' j'}</div>
                  </div>
                  <div style={{flex:1,display:'flex',alignItems:'center',gap:6}}>
                    <div style={{height:20,background:p.color,borderRadius:4,width:`${pct}%`,minWidth:30,display:'flex',alignItems:'center',padding:'0 8px'}}>
                      <span style={{fontSize:10,color:'#fff',fontWeight:600,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{p.days < 1 ? '' : p.phase.split(' ')[0]}</span>
                    </div>
                  </div>
                  <div style={{width:140,textAlign:'right',fontSize:11,color:'#64748b',flexShrink:0}}>
                    {fmt(p.startDate)} → {fmt(p.endDate)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Détail des tâches par phase */}
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(250px,1fr))',gap:10,marginBottom:16}}>
            {phases.map((p,i)=>(
              <div key={i} style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',overflow:'hidden'}}>
                <div style={{background:p.color,padding:'8px 12px',display:'flex',alignItems:'center',gap:8}}>
                  <div style={{flex:1,fontWeight:700,fontSize:12,color:'#fff'}}>{p.phase}</div>
                  <div style={{fontSize:10,color:'rgba(255,255,255,.8)',background:'rgba(255,255,255,.15)',borderRadius:4,padding:'2px 6px',whiteSpace:'nowrap'}}>{fmt(p.startDate)}</div>
                </div>
                <div style={{padding:'8px 12px'}}>
                  {(p.tasks||[]).map((t,j)=>(
                    <div key={j} style={{fontSize:12,color:'#475569',padding:'3px 0',display:'flex',alignItems:'center',gap:7,borderBottom:j<p.tasks.length-1?'1px solid #f8fafc':'none'}}>
                      <div style={{width:6,height:6,borderRadius:'50%',background:p.color,flexShrink:0}} />
                      {t}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Notes */}
          <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',padding:'14px 18px'}}>
            <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:8}}>📝 Notes & conditions particulières</div>
            <textarea value={notes} onChange={e=>setNotes(e.target.value)} rows={3}
              placeholder="Conditions d'accès, contraintes météo, disponibilités client, matériaux à confirmer…"
              style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:'inherit',fontSize:13,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} />
          </div>
        </div>

        {/* Footer */}
        <div style={{padding:'12px 20px',borderTop:'1px solid #e2e8f0',background:'#fff',display:'flex',justifyContent:'flex-end',gap:9,flexShrink:0}}>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 18px',cursor:'pointer',fontSize:13,color:'#475569',fontWeight:600}}>Fermer</button>
          <button onClick={exportPDF} style={{background:'#1e293b',color:'#fff',border:'none',borderRadius:9,padding:'8px 22px',fontWeight:700,fontSize:13,cursor:'pointer'}}>🖨️ Imprimer le planning</button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SectionBlock — ring progress + badges colorés + photo
═══════════════════════════════════════════════════ */
function SectionBlock({ section, items, state, onSetState, onOpenProducts, filterStatus, itemData, onSetItemData }) {
  const [open,setOpen]=useState(true);
  const [notes,setNotes]=useState({});
  const [photos,setPhotos]=useState({});
  const [detailModal,setDetailModal]=useState(null); /* {itemIdx, item, schemaKey} */
  const [quantities,setQuantities]=useState({}); /* quantités inline */
  const fileInputRefs=useRef({});
  const done=items.filter((_,i)=>(state[i]||'')!=='').length;
  const nOk=items.filter((_,i)=>state[i]==='ok').length;
  const nWarn=items.filter((_,i)=>state[i]==='warn').length;
  const nBad=items.filter((_,i)=>state[i]==='bad').length;
  const pct=items.length?Math.round(done/items.length*100):0;
  const circ=2*Math.PI*15;
  const dash=circ*pct/100;
  const ringColor=pct===100?'#16a34a':nBad>0?'#e24b4a':nWarn>0?'#f59e0b':'#0ea5e9';

  function handlePhoto(i,e) {
    const file=e.target.files[0];
    if(!file)return;
    const reader=new FileReader();
    reader.onload=ev=>{
      setPhotos(p=>({...p,[i]:[...(p[i]||[]),ev.target.result]}));
      if(state[i]==='')onSetState(i,'ok');
    };
    reader.readAsDataURL(file);
  }

  const filteredItems = items.map((item,i)=>({item,i})).filter(({i})=>{
    if(!filterStatus||filterStatus==='all')return true;
    const s=state[i]||'';
    if(filterStatus==='ok')return s==='ok';
    if(filterStatus==='warn')return s==='warn';
    if(filterStatus==='bad')return s==='bad';
    if(filterStatus==='untreated')return s==='';
    return true;
  });

  if(filterStatus&&filterStatus!=='all'&&filteredItems.length===0)return null;

  return (
    <div style={{background:'#fff',borderRadius:13,border:'1.5px solid #e2e8f0',marginBottom:12,overflow:'hidden'}}>
      <div onClick={()=>setOpen(o=>!o)} style={{padding:'11px 16px',display:'flex',alignItems:'center',gap:12,cursor:'pointer',userSelect:'none',background:'#f8fafc'}}>
        <svg width="38" height="38" viewBox="0 0 38 38" style={{flexShrink:0}}>
          <circle cx="19" cy="19" r="15" fill="none" stroke="#e2e8f0" strokeWidth="3"/>
          <circle cx="19" cy="19" r="15" fill="none" stroke={ringColor} strokeWidth="3"
            strokeDasharray={`${dash} ${circ-dash}`} strokeDashoffset={circ*0.25}
            strokeLinecap="round" style={{transition:'stroke-dasharray .4s'}}/>
          <text x="19" y="23" textAnchor="middle" fontSize="9" fontWeight="700" fill={ringColor}>{pct}%</text>
        </svg>
        <div style={{flex:1,minWidth:0}}>
          <div style={{fontWeight:700,fontSize:14,color:'#1e293b'}}>{section}</div>
          <div style={{fontSize:11,color:'#64748b',marginTop:2}}>{done}/{items.length} points traités{nBad>0?` — ${nBad} problème${nBad>1?'s':''}`:''}</div>
        </div>
        <div style={{display:'flex',gap:4,flexShrink:0}}>
          {nOk>0&&<span style={{background:'#eaf3de',color:'#3b6d11',borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:600}}>{nOk} ok</span>}
          {nWarn>0&&<span style={{background:'#faeeda',color:'#854f0b',borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:600}}>{nWarn} attn</span>}
          {nBad>0&&<span style={{background:'#fcebeb',color:'#a32d2d',borderRadius:5,padding:'2px 7px',fontSize:11,fontWeight:600}}>{nBad} pb</span>}
        </div>
        <span style={{fontSize:11,color:'#94a3b8',flexShrink:0}}>{open?'▲':'▼'}</span>
      </div>
      {open&&(<div style={{padding:'2px 0 6px'}}>
        {filteredItems.map(({item,i})=>{
          const s=state[i]||'';
          const borderColor=s==='ok'?'#16a34a':s==='warn'?'#f59e0b':s==='bad'?'#ef4444':'#e2e8f0';
          const bgColor=s==='ok'?'rgba(22,163,74,.04)':s==='warn'?'rgba(245,158,11,.04)':s==='bad'?'rgba(239,68,68,.04)':'transparent';
          const textColor=s==='ok'?'#3b6d11':s==='warn'?'#854f0b':s==='bad'?'#a32d2d':'#334155';
          const photoList=photos[i]||[];
          return(
            {(() => {
              const schemaKey = detectSchema(item);
              const hasData = itemData && itemData[i] && Object.values(itemData[i]).some(v => v !== '' && v !== undefined);
              /* Résumé des valeurs saisies */
              const dataSummary = hasData ? Object.entries(itemData[i]).filter(([k,v])=>v&&v!=='').slice(0,3).map(([k,v])=>`${v}`).join(' · ') : null;
              /* Quantité inline pour items "nombre ___" */
              const isCountItem = item.toLowerCase().match(/nombre\s*[_:]/i);
              return (
            <div key={i} style={{padding:'6px 14px 6px 11px',borderTop:'1px solid #f8fafc',display:'flex',alignItems:'center',gap:7,borderLeft:`3px solid ${borderColor}`,background:bgColor,transition:'all .2s',flexWrap:'nowrap'}}>
              <input type="checkbox" checked={s!==''} onChange={()=>onSetState(i,s?null:'ok')} style={{width:14,height:14,accentColor:'#0ea5e9',cursor:'pointer',flexShrink:0}} />
              <button title="OK / Conforme" onClick={()=>onSetState(i,s==='ok'?null:'ok')}
                style={{width:22,height:22,borderRadius:5,border:'none',cursor:'pointer',fontSize:13,background:s==='ok'?'#16a34a':'#f0fdf4',transition:'all .15s',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>✅</button>
              <button title="Attention" onClick={()=>onSetState(i,s==='warn'?null:'warn')}
                style={{width:22,height:22,borderRadius:5,border:'none',cursor:'pointer',fontSize:13,background:s==='warn'?'#f59e0b':'#fffbeb',transition:'all .15s',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>⚠️</button>
              <button title="Problème / Non conforme" onClick={()=>onSetState(i,s==='bad'?null:'bad')}
                style={{width:22,height:22,borderRadius:5,border:'none',cursor:'pointer',fontSize:13,background:s==='bad'?'#ef4444':'#fef2f2',transition:'all .15s',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>❌</button>
              {/* Texte item + résumé données */}
              <div style={{flex:1,minWidth:0}}>
                <span style={{fontSize:12.5,color:textColor,textDecoration:s==='ok'?'line-through':'none',lineHeight:1.4}}>{item.replace(/_{3,}/g,'').replace(/:\s*$/,'').trim()}</span>
                {dataSummary&&<div style={{fontSize:10,color:s==='ok'?'#16a34a':s==='warn'?'#f59e0b':s==='bad'?'#ef4444':'#0ea5e9',marginTop:1,fontWeight:600}}>→ {dataSummary}</div>}
              </div>
              {/* Quantité inline */}
              {isCountItem&&(
                <input type="number" min={0} max={99} value={quantities[i]||''} onChange={e=>setQuantities(q=>({...q,[i]:e.target.value}))}
                  placeholder="Nb" onClick={e=>e.stopPropagation()}
                  style={{width:50,border:`1.5px solid ${borderColor==='#e2e8f0'?'#e2e8f0':borderColor}`,borderRadius:6,padding:'2px 6px',fontFamily:'inherit',fontSize:12,textAlign:'center',outline:'none',flexShrink:0}} />
              )}
              {/* Bouton 📝 encodage détaillé */}
              {schemaKey&&(
                <button title="Encoder les informations" onClick={e=>{e.stopPropagation();setDetailModal({itemIdx:i,item,schemaKey});}}
                  style={{background:hasData?'#eff9ff':'none',border:`1.5px solid ${hasData?'#0ea5e9':'#e2e8f0'}`,borderRadius:5,padding:'2px 8px',cursor:'pointer',fontSize:12,color:hasData?'#0ea5e9':'#94a3b8',flexShrink:0,fontWeight:hasData?700:400}}>
                  {hasData?'📝 ✓':'📝'}
                </button>
              )}
              {/* Photo */}
              <button title="Ajouter une photo" onClick={e=>{e.stopPropagation();fileInputRefs.current[i]?.click();}}
                style={{background:photoList.length>0?'#eff9ff':'none',border:`1px solid ${photoList.length>0?'#0ea5e9':'#e2e8f0'}`,borderRadius:5,padding:'2px 7px',cursor:'pointer',fontSize:11,color:photoList.length>0?'#0ea5e9':'#94a3b8',flexShrink:0,whiteSpace:'nowrap'}}>
                📷{photoList.length>0?` ${photoList.length}`:''}
              </button>
              <input ref={el=>fileInputRefs.current[i]=el} type="file" accept="image/*" capture="environment" onChange={e=>handlePhoto(i,e)} style={{display:'none'}} />
              {/* Produits */}
              <button title="Produits associés" onClick={e=>{e.stopPropagation();onOpenProducts(item,section);}}
                style={{background:s==='bad'?'#fef2f2':s==='warn'?'#fffbeb':'none',border:`1px solid ${s==='bad'?'#fca5a5':s==='warn'?'#fcd34d':'#e2e8f0'}`,borderRadius:5,padding:'2px 7px',cursor:'pointer',fontSize:13,color:s==='bad'?'#ef4444':s==='warn'?'#f59e0b':'#94a3b8',flexShrink:0}}>🛒</button>
              {/* Note */}
              <input value={notes[i]||''} onChange={e=>setNotes(n=>({...n,[i]:e.target.value}))} placeholder="Note…"
                style={{width:80,border:`1px solid ${s==='bad'?'#fca5a5':s==='warn'?'#fcd34d':'#e8edf3'}`,borderRadius:5,padding:'2px 7px',fontFamily:'inherit',fontSize:11,outline:'none',color:textColor,background:'transparent',flexShrink:0}} onClick={e=>e.stopPropagation()} />
            </div>
              );
            })()}
        {photos&&Object.keys(photos).some(k=>photos[k]?.length>0)&&(
          <div style={{padding:'8px 14px',borderTop:'1px solid #f0f4f8',display:'flex',gap:6,flexWrap:'wrap'}}>
            {Object.entries(photos).flatMap(([k,imgs])=>imgs.map((src,j)=>(
              <img key={k+'-'+j} src={src} alt="" style={{width:44,height:44,objectFit:'cover',borderRadius:6,border:'1.5px solid #e2e8f0',cursor:'pointer'}} onClick={()=>window.open(src,'_blank')} />
            )))}
          </div>
        )}
      </div>)}
      {detailModal&&(
        <ItemDetailModal
          item={detailModal.item}
          schemaKey={detailModal.schemaKey}
          savedValues={itemData&&itemData[detailModal.itemIdx]}
          onSave={vals=>{
            if(onSetItemData)onSetItemData(detailModal.itemIdx,vals);
            if(state[detailModal.itemIdx]==='')onSetState(detailModal.itemIdx,'ok');
            setDetailModal(null);
          }}
          onClose={()=>setDetailModal(null)}
        />
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   QuoteModal — devis style Odoo (4 onglets)
═══════════════════════════════════════════════════ */
const EVAC_OPT=[{key:'client',label:'🤝 Évacuation prise en charge client',price:0},{key:'forfait',label:'🚛 Forfait évacuation Lolirine',price:150},{key:'sans',label:'— Sans évacuation',price:0}];
const PAY_TERMS=['Paiement à terme échu (30j)','Paiement comptant','Acompte 30%+solde livraison','Acompte 50%+solde livraison','Virement avant expédition'];
const FOURNISSEURS=['Fluidra / SIBO','SCP Bénélux','HTH / BWT','Zodiac / Fluidra','Hayward','Astralpool','Pentair'];
function deplCost(km){const n=Number(km)||0;if(n<=0)return 0;if(n<=30)return 50;return 50+Math.ceil((n-30)/25)*10;}
function QuoteModal({products,clientInfo,onClose,onCreated}) {
  const cfg=window.LOLIRINE_CHECKLIST_CONFIG||{};
  const [tab,setTab]=useState('lines');
  const [busy,setBusy]=useState(false);
  const [result,setResult]=useState(null);
  const [err,setErr]=useState(null);
  const [lines,setLines]=useState((products||[]).map(p=>({...p,qty:p.qty||1,include:true,price_unit:typeof p.price==='number'?p.price:(parseFloat(p.price)||0),remise:0})));
  const [evac,setEvac]=useState('client');
  const [km,setKm]=useState(0);
  const [kmAuto,setKmAuto]=useState(true);
  const [kmMt,setKmMt]=useState(0);
  const [inclDepl,setInclDepl]=useState(false);
  const [inclMO,setInclMO]=useState(false);
  const [mo,setMo]=useState(0);
  const [fourn,setFourn]=useState('Fluidra / SIBO');
  const [fournRef,setFournRef]=useState('');
  const [delai,setDelai]=useState('5-10 jours ouvrés');
  const [livrDir,setLivrDir]=useState(true);
  const [livrAdr,setLivrAdr]=useState(clientInfo?.adresseChantier||'');
  const [cmdFourn,setCmdFourn]=useState('');
  const [noteInt,setNoteInt]=useState(clientInfo?.adresseChantier?'Chantier : '+clientInfo.adresseChantier:'');
  const [cond,setCond]=useState('');
  const [payTerm,setPayTerm]=useState(PAY_TERMS[0]);
  const [valid,setValid]=useState(30);
  const address = clientInfo?.adresseChantier||'';
  useEffect(()=>{
    if(!address||Number(km)>0)return;
    let cancel=false;
    (async()=>{
      try{
        const r=await fetch('https://nominatim.openstreetmap.org/search?'+new URLSearchParams({q:address,countrycodes:'be,lu,fr,nl',format:'json',limit:'1'}),{mode:'cors',headers:{'Accept-Language':'fr'}});
        const d=await r.json();
        if(cancel||!d[0])return;
        const lat2=parseFloat(d[0].lat),lon2=parseFloat(d[0].lon);
        const R=6371,dLat=(lat2-50.4875)*Math.PI/180,dLon=(lon2-4.9215)*Math.PI/180;
        const a=Math.sin(dLat/2)**2+Math.cos(50.4875*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
        const dist=Math.round(R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a))*1.3);
        if(!cancel&&dist>0){setKm(dist);setInclDepl(true);}
      }catch{}
    })();
    return()=>{cancel=true;};
  },[address]);
  useEffect(()=>{if(kmAuto)setKmMt(deplCost(Number(km)));},[km,kmAuto]);
  const tMat=lines.filter(l=>l.include).reduce((a,l)=>a+(l.price_unit||0)*(l.qty||1)*(1-(l.remise||0)/100),0);
  const tDepl=inclDepl?(kmAuto?deplCost(Number(km)):(Number(kmMt)||0)):0;
  const tEvac=evac!=='sans'?(EVAC_OPT.find(o=>o.key===evac)?.price||0):0;
  const tMO=inclMO?(Number(mo)||0):0;
  const sHT=tMat+tDepl+tEvac+tMO;
  const tva=sHT*0.21;
  const tTTC=sHT+tva;
  function toggleLine(i){setLines(ls=>ls.map((l,x)=>x===i?{...l,include:!l.include}:l));}
  function updQty(i,d){setLines(ls=>ls.map((l,x)=>x===i?{...l,qty:Math.max(1,(l.qty||1)+d)}:l));}
  function updP(i,v){setLines(ls=>ls.map((l,x)=>x===i?{...l,price_unit:parseFloat(v)||0}:l));}
  function updR(i,v){setLines(ls=>ls.map((l,x)=>x===i?{...l,remise:Math.min(100,Math.max(0,parseFloat(v)||0))}:l));}
  function delLine(i){setLines(ls=>ls.filter((_,x)=>x!==i));}
  async function doCreate(){
    setBusy(true);setErr(null);
    const allLines=[...lines.filter(l=>l.include).map(l=>({product_id:l.id||null,name:l.name,product_uom_qty:l.qty,price_unit:l.price_unit||0,discount:l.remise||0,default_code:l.ref||''})),...(tDepl>0?[{product_id:null,name:`Frais déplacement (${km}km depuis Boninne)`,product_uom_qty:1,price_unit:tDepl,discount:0,default_code:''}]:[]),...(tEvac>0?[{product_id:null,name:EVAC_OPT.find(o=>o.key===evac)?.label,product_uom_qty:1,price_unit:tEvac,discount:0,default_code:''}]:[]),...(tMO>0?[{product_id:null,name:"Main d'oeuvre technicien",product_uom_qty:1,price_unit:tMO,discount:0,default_code:''}]:[])];
    if(!allLines.length){setErr('Aucune ligne.');setBusy(false);return;}
    const clientName=[clientInfo?.prenom,clientInfo?.nom].filter(Boolean).join(' ')||clientInfo?.denominationSociale||'';
    try{
      const r=await fetch(cfg.quoteEndpoint||'/pool-checklist/create-quote',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{partner_id:clientInfo?.odooId||null,partner_name:clientName,ref_dossier:clientInfo?.refDossier||'',payment_term:payTerm,note:[noteInt,cond,livrDir?'Livraison chantier : '+livrAdr:'',cmdFourn?'BC fourn: '+cmdFourn:''].filter(Boolean).join('\n'),lines:allLines}})});
      const d=await r.json();
      if(d?.result?.error){setErr(d.result.error);setBusy(false);return;}
      setResult(d?.result||{});
      if(onCreated)onCreated(d?.result);
    }catch(e){setErr(e.message);}
    setBusy(false);
  }
  const IS={width:'100%',border:'1.5px solid #dde4ed',borderRadius:7,padding:'6px 10px',fontFamily:'inherit',fontSize:12,outline:'none',boxSizing:'border-box'};
  const TABS=[{k:'lines',lbl:'📦 Lignes',badge:lines.filter(l=>l.include).length},{k:'services',lbl:'🔧 Frais & services'},{k:'dropship',lbl:'🚚 Dropshipping'},{k:'notes',lbl:'📝 Notes'}];
  if(result)return(<div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center'}}><div style={{background:'#fff',borderRadius:16,padding:32,width:'min(460px,92vw)',textAlign:'center',boxShadow:'0 24px 80px rgba(0,0,0,.25)'}}><div style={{fontSize:48,marginBottom:10}}>✅</div><div style={{fontWeight:800,fontSize:19,color:'#1e293b',marginBottom:4}}>Devis créé !</div>{result.name&&<div style={{fontSize:17,color:'#0ea5e9',fontWeight:700,marginBottom:4}}>{result.name}</div>}{result.partner_name&&<div style={{fontSize:13,color:'#64748b',marginBottom:18}}>Client : {result.partner_name}</div>}<div style={{display:'flex',gap:9,justifyContent:'center'}}>{result.url&&<a href={result.url} target='_blank' rel='noreferrer' style={{background:'#0ea5e9',color:'#fff',borderRadius:9,padding:'9px 20px',fontWeight:700,fontSize:13,textDecoration:'none'}}>Ouvrir →</a>}<button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'9px 20px',fontWeight:600,fontSize:13,cursor:'pointer',color:'#475569'}}>Fermer</button></div></div></div>);
  return(
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f1f5f9',borderRadius:15,width:'min(940px,100%)',maxHeight:'95vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.28)',overflow:'hidden'}}>
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',padding:'11px 18px',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
          <div style={{flex:1}}><div style={{fontWeight:800,fontSize:16,color:'#1e293b'}}>📄 Nouveau devis — Lolirine Pool Store</div><div style={{fontSize:12,color:'#64748b',marginTop:1}}>{[clientInfo?.prenom,clientInfo?.nom].filter(Boolean).join(' ')||clientInfo?.denominationSociale||''}{clientInfo?.adresseChantier&&<span style={{color:'#94a3b8'}}> · {clientInfo.adresseChantier.split(',')[0]}</span>}</div></div>
          <span style={{background:'#f0fdf4',border:'1.5px solid #bbf7d0',borderRadius:20,padding:'3px 11px',fontSize:12,fontWeight:700,color:'#16a34a',flexShrink:0}}>Brouillon</span>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d',flexShrink:0}}>✕</button>
        </div>
        <div style={{background:'#fff',borderBottom:'1px solid #e8edf3',padding:'10px 18px',display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(150px,1fr))',gap:10,flexShrink:0}}>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Client</div><div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{[clientInfo?.prenom,clientInfo?.nom].filter(Boolean).join(' ')||clientInfo?.denominationSociale||'—'}</div>{clientInfo?.adresseChantier&&<div style={{fontSize:11,color:'#64748b'}}>{clientInfo.adresseChantier}</div>}</div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Date</div><div style={{fontSize:13,color:'#1e293b'}}>{new Date().toLocaleDateString('fr-BE')}</div></div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Validité</div><div style={{display:'flex',alignItems:'center',gap:4}}><input type="number" value={valid} min={1} onChange={e=>setValid(e.target.value)} style={{width:50,...IS,padding:'4px 7px',textAlign:'center'}} /><span style={{fontSize:12,color:'#64748b'}}>jours</span></div></div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>Conditions paiement</div><select value={payTerm} onChange={e=>setPayTerm(e.target.value)} style={{...IS,background:'#fff',fontSize:11}}>{PAY_TERMS.map(t=><option key={t}>{t}</option>)}</select></div>
          <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',marginBottom:3}}>TVA</div><div style={{fontSize:13,fontWeight:600,color:'#475569'}}>21 % (BE)</div></div>
        </div>
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',display:'flex',flexShrink:0,overflowX:'auto'}}>
          {TABS.map(t=><button key={t.k} onClick={()=>setTab(t.k)} style={{padding:'9px 17px',border:'none',borderBottom:`3px solid ${tab===t.k?'#0ea5e9':'transparent'}`,background:'transparent',cursor:'pointer',fontWeight:tab===t.k?700:500,fontSize:13,color:tab===t.k?'#0ea5e9':'#64748b',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5}}>{t.lbl}{t.badge!=null&&<span style={{background:tab===t.k?'#0ea5e9':'#e2e8f0',color:tab===t.k?'#fff':'#64748b',borderRadius:20,padding:'1px 6px',fontSize:11,fontWeight:700}}>{t.badge}</span>}</button>)}
        </div>
        <div style={{flex:1,overflowY:'auto'}}>
          {tab==='lines'&&(<div>
            <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
              <thead style={{background:'#f8fafc',position:'sticky',top:0,zIndex:1}}><tr style={{borderBottom:'2px solid #e2e8f0'}}>{['','Produit','Fourn.','Réf.','Qté','Prix HT','Rem%','Total HT',''].map((h,i)=><th key={i} style={{padding:'8px 9px',textAlign:'left',fontWeight:700,color:'#64748b',fontSize:11,whiteSpace:'nowrap'}}>{h}</th>)}</tr></thead>
              <tbody>
                {lines.map((l,i)=>{const sup=l.suppliers?.[0]||{};const mt=(l.price_unit||0)*(l.qty||1)*(1-(l.remise||0)/100);return<tr key={i} style={{borderBottom:'1px solid #f1f5f9',background:l.include?'#fff':'#f8fafc',opacity:l.include?1:.5}}>
                  <td style={{padding:'7px 9px',width:22}}><input type="checkbox" checked={!!l.include} onChange={()=>toggleLine(i)} style={{accentColor:'#0ea5e9',width:14,height:14,cursor:'pointer'}} /></td>
                  <td style={{padding:'7px 9px',minWidth:160}}><div style={{fontWeight:600,color:'#1e293b',fontSize:13}}>{l.name}</div>{l.ref&&<div style={{fontSize:11,color:'#94a3b8'}}>Réf: {l.ref}</div>}</td>
                  <td style={{padding:'7px 9px',fontSize:12,color:'#7c3aed',whiteSpace:'nowrap'}}>{sup.name||'—'}</td>
                  <td style={{padding:'7px 9px',fontSize:12,color:'#64748b'}}>{sup.ref||l.ref||'—'}</td>
                  <td style={{padding:'7px 9px'}}><div style={{display:'flex',alignItems:'center',gap:3}}><button onClick={()=>updQty(i,-1)} style={{width:20,height:20,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:12}}>−</button><span style={{fontWeight:700,minWidth:20,textAlign:'center'}}>{l.qty}</span><button onClick={()=>updQty(i,+1)} style={{width:20,height:20,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:12}}>+</button></div></td>
                  <td style={{padding:'7px 9px',width:85}}><input type="number" value={l.price_unit} min={0} step={0.01} onChange={e=>updP(i,e.target.value)} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:6,padding:'3px 6px',fontFamily:'inherit',fontSize:12,textAlign:'right',outline:'none'}} /></td>
                  <td style={{padding:'7px 9px',width:60}}><input type="number" value={l.remise||0} min={0} max={100} onChange={e=>updR(i,e.target.value)} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:6,padding:'3px 6px',fontFamily:'inherit',fontSize:12,textAlign:'right',outline:'none'}} /></td>
                  <td style={{padding:'7px 9px',fontWeight:700,color:'#0369a1',textAlign:'right',whiteSpace:'nowrap'}}>{mt>0?mt.toFixed(2)+' €':'—'}</td>
                  <td style={{padding:'7px 9px'}}><button onClick={()=>delLine(i)} style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',fontSize:13}}>✕</button></td>
                </tr>;})}
                {lines.length===0&&<tr><td colSpan={9} style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucun produit. Ajoutez des articles via les boutons 🛒 de la check-list.</td></tr>}
              </tbody>
            </table>
            <div style={{padding:'10px 16px',background:'#f8fafc',borderTop:'1px solid #e2e8f0',textAlign:'right',fontSize:13,color:'#64748b'}}>Sous-total matériaux HT : <strong style={{color:'#0369a1'}}>{tMat.toFixed(2)} €</strong></div>
          </div>)}
          {tab==='services'&&(<div style={{padding:18,display:'flex',flexDirection:'column',gap:16}}>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
              <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:10}}>🗑️ Évacuation déchets</div>
              {EVAC_OPT.map(o=><label key={o.key} style={{display:'flex',alignItems:'center',gap:9,padding:'8px 12px',borderRadius:9,border:`2px solid ${evac===o.key?'#0ea5e9':'#e8edf3'}`,background:evac===o.key?'#eff9ff':'#fff',cursor:'pointer',marginBottom:6}}><input type="radio" name="evac" value={o.key} checked={evac===o.key} onChange={()=>setEvac(o.key)} style={{accentColor:'#0ea5e9',width:15,height:15}} /><span style={{flex:1,fontSize:13,fontWeight:evac===o.key?600:400,color:evac===o.key?'#0369a1':'#334155'}}>{o.label}</span>{o.price>0&&<span style={{fontWeight:700,color:'#0369a1',fontSize:14}}>{o.price} €</span>}</label>)}
            </div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}><input type="checkbox" checked={inclDepl} onChange={e=>setInclDepl(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15,cursor:'pointer'}} /><span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>🚗 Frais de déplacement</span><span style={{fontSize:11,color:'#94a3b8',fontStyle:'italic'}}>depuis Boninne · ≤30km=50€ · +10€/25km</span></div>
              <div style={{display:'flex',gap:14,alignItems:'flex-end',flexWrap:'wrap'}}>
                <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Distance (km)</div><div style={{display:'flex',alignItems:'center',gap:5}}><button onClick={()=>setKm(Math.max(0,Number(km)-5))} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>−</button><input type="number" value={km} min={0} onChange={e=>setKm(e.target.value)} style={{width:65,...IS,textAlign:'center',padding:'4px 7px'}} /><button onClick={()=>setKm(Number(km)+5)} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>+</button></div></div>
                <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Montant HT (€) <label style={{fontWeight:400}}><input type="checkbox" checked={kmAuto} onChange={e=>setKmAuto(e.target.checked)} style={{accentColor:'#0ea5e9',marginRight:3}} />Auto</label></div><input type="number" value={kmAuto?deplCost(Number(km)):kmMt} readOnly={kmAuto} min={0} onChange={e=>!kmAuto&&setKmMt(e.target.value)} style={{width:85,...IS,textAlign:'center',padding:'4px 7px',background:kmAuto?'#f8fafc':'#fff'}} /></div>
                <div style={{fontSize:12,color:'#64748b',paddingBottom:4}}>{address&&<div>📍 {address.split(',')[0]}</div>}{Number(km)>0&&<div style={{color:'#0ea5e9',fontWeight:600,marginTop:2}}>Barème : {deplCost(Number(km))} €</div>}</div>
              </div>
            </div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}><input type="checkbox" checked={inclMO} onChange={e=>setInclMO(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15,cursor:'pointer'}} /><span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>🔨 Main d'œuvre technicien</span></div>
              <div style={{display:'flex',gap:9,alignItems:'center',flexWrap:'wrap'}}><button onClick={()=>setMo(Math.max(0,(Number(mo)||0)-50))} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>−</button><input type="number" value={mo} min={0} step={50} onChange={e=>setMo(e.target.value)} style={{width:95,...IS,textAlign:'center',fontSize:15,fontWeight:700,padding:'5px 9px'}} /><span style={{fontSize:13,color:'#475569'}}>€ HT</span><button onClick={()=>setMo((Number(mo)||0)+50)} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>+</button>{[0,500,750,1000,1500,2000].map(v=><button key={v} onClick={()=>setMo(v)} style={{padding:'3px 8px',borderRadius:6,border:`1px solid ${mo==v?'#0ea5e9':'#e2e8f0'}`,background:mo==v?'#eff9ff':'#f8fafc',color:mo==v?'#0369a1':'#64748b',fontSize:11,cursor:'pointer',fontWeight:mo==v?700:400}}>{v===0?'—':v+'€'}</button>)}</div>
            </div>
          </div>)}
          {tab==='dropship'&&(<div style={{padding:18,display:'flex',flexDirection:'column',gap:14}}>
            <div style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:11,padding:'10px 14px',fontSize:13,color:'#92400e'}}>⚡ En dropshipping, la commande fournisseur est transmise après validation du devis. Livraison possible directement sur chantier.</div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'16px',display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Fournisseur principal</div><select value={fourn} onChange={e=>setFourn(e.target.value)} style={{...IS,background:'#fff'}}>{FOURNISSEURS.map(s=><option key={s}>{s}</option>)}</select></div>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Réf. commande fournisseur</div><input value={cmdFourn} onChange={e=>setCmdFourn(e.target.value)} placeholder="BC-FOURN-2025-XXX" style={IS} /></div>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Réf. produit fournisseur</div><input value={fournRef} onChange={e=>setFournRef(e.target.value)} placeholder="ex: FLU-PMP-00312" style={IS} /></div>
              <div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Délai de livraison estimé</div><input value={delai} onChange={e=>setDelai(e.target.value)} style={IS} /></div>
            </div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'16px'}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}><input type="checkbox" checked={livrDir} onChange={e=>setLivrDir(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15}} /><span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>📍 Livraison directe sur chantier</span></div>
              {livrDir?<div><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:3}}>Adresse de livraison</div><input value={livrAdr} onChange={e=>setLivrAdr(e.target.value)} placeholder="Adresse complète…" style={IS} /></div>:<div style={{fontSize:13,color:'#64748b'}}>📦 Livraison à l'entrepôt Lolirine — retrait technicien</div>}
            </div>
          </div>)}
          {tab==='notes'&&(<div style={{padding:18,display:'flex',flexDirection:'column',gap:12}}>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:5}}>Notes internes / chantier</div><textarea value={noteInt} onChange={e=>setNoteInt(e.target.value)} rows={4} placeholder="Observations de la visite, accès, remarques…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'9px 12px',fontFamily:'inherit',fontSize:12,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} /></div>
            <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}><div style={{fontSize:11,fontWeight:700,color:'#64748b',marginBottom:5}}>Conditions particulières</div><textarea value={cond} onChange={e=>setCond(e.target.value)} rows={3} placeholder="Garanties, délais, restrictions…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'9px 12px',fontFamily:'inherit',fontSize:12,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} /></div>
          </div>)}
        </div>
        <div style={{background:'#fff',borderTop:'2px solid #e2e8f0',flexShrink:0,display:'flex',flexWrap:'wrap'}}>
          <div style={{flex:1,padding:'12px 18px',minWidth:240}}>
            <table style={{width:'100%',fontSize:13}}><tbody>
              {tMat>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Matériaux HT</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tMat.toFixed(2)} €</td></tr>}
              {tDepl>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Déplacement ({km}km)</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tDepl.toFixed(2)} €</td></tr>}
              {tEvac>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Évacuation</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tEvac.toFixed(2)} €</td></tr>}
              {tMO>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Main d'œuvre</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tMO.toFixed(2)} €</td></tr>}
              <tr style={{borderTop:'1px solid #f0f4f8'}}><td style={{color:'#64748b',padding:'5px 0 2px',fontWeight:600}}>Montant HT</td><td style={{textAlign:'right',fontWeight:700,color:'#1e293b',fontSize:14}}>{sHT.toFixed(2)} €</td></tr>
              <tr><td style={{color:'#64748b',padding:'2px 0'}}>TVA 21%</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tva.toFixed(2)} €</td></tr>
              <tr style={{borderTop:'2px solid #0ea5e9'}}><td style={{fontWeight:800,fontSize:15,color:'#0ea5e9',padding:'5px 0 0'}}>Total TTC</td><td style={{textAlign:'right',fontWeight:800,fontSize:16,color:'#0ea5e9'}}>{tTTC.toFixed(2)} €</td></tr>
            </tbody></table>
          </div>
          <div style={{padding:'12px 18px',display:'flex',flexDirection:'column',gap:8,justifyContent:'center',minWidth:190,alignItems:'stretch'}}>
            {err&&<div style={{color:'#ef4444',fontSize:12,textAlign:'center'}}>{err}</div>}
            <button onClick={doCreate} disabled={busy} style={{background:busy?'#cbd5e1':'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'10px 22px',fontWeight:700,fontSize:14,cursor:busy?'wait':'pointer',whiteSpace:'nowrap'}}>{busy?'⏳ Création…':'📄 Créer le devis Odoo'}</button>
            <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 22px',fontWeight:600,fontSize:13,cursor:'pointer',color:'#475569'}}>← Annuler</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   PoolChecklist — Wizard 4 étapes
═══════════════════════════════════════════════════ */
function PoolChecklist() {
  const [step, setStep]   = useState(1);
  /* Étape 1 */
  const [type, setType]   = useState('');
  /* Étape 2 — Infos client */
  const [clientType, setClientType] = useState('particulier'); /* particulier | professionnel */
  const [prenom, setPrenom]     = useState('');
  const [nom, setNom]           = useState('');
  const [email, setEmail]       = useState('');
  const [telephone, setTelephone] = useState('');
  const [codePostal, setCodePostal] = useState('');
  const [adresseChantier, setAdresseChantier] = useState('');
  const [denomination, setDenomination] = useState('');
  const [tvaNum, setTvaNum]     = useState('');
  const [refDossier, setRefDossier] = useState('');
  const [technicien, setTechnicien] = useState('');
  const [date, setDate]         = useState(new Date().toISOString().split('T')[0]);
  const [odooId, setOdooId]     = useState(null);
  /* Étape 3 — Plan bassin */
  const [basinShape, setBasinShape] = useState('');
  const [basinL, setBasinL]     = useState('');
  const [basinW, setBasinW]     = useState('');
  const [basinD, setBasinD]     = useState('');
  const [basinNotes, setBasinNotes] = useState('');
  /* Étape 4 — Checklist */
  const [itemState, setItemState] = useState({});
  const [products, setProducts] = useState([]);
  const [panel, setPanel]       = useState(null);
  const [showQuote, setShowQuote] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [obs, setObs]           = useState('');
  const [statut, setStatut]     = useState('en_cours');
  const [itemData,setItemData]  = useState({});
  const [showPlanning,setShowPlanning] = useState(false);
  const [signClient, setSignClient] = useState('');
  const [signTech, setSignTech] = useState('');
  const [saved, setSaved]       = useState(false);
  const [filter4, setFilter4]   = useState('all');
  const [search4, setSearch4]   = useState('');
  const [lastSaved, setLastSaved] = useState(null);

  /* Auto-save toutes les 30s si données présentes */
  useEffect(()=>{
    if(!type&&!prenom&&!nom)return;
    const t=setInterval(()=>{
      try{
        const s=JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
        const record={type,clientType,prenom,nom,email,telephone,codePostal,adresseChantier,denomination,tvaNum,refDossier,technicien,date,basinShape,basinL,basinW,basinD,basinNotes,itemState,products,obs,statut,signClient,signTech,savedAt:new Date().toISOString(),autoSave:true};
        const lastIdx=s.findIndex(r=>r.autoSave&&r.type===type&&r.prenom===prenom&&r.nom===nom);
        if(lastIdx>=0)s[lastIdx]=record;else s.push(record);
        localStorage.setItem('pool_checklist_history',JSON.stringify(s.slice(-50)));
        setLastSaved(new Date());
      }catch{}
    },30000);
    return()=>clearInterval(t);
  },[type,prenom,nom,itemState,products]);

  const sections   = type ? (SECTIONS_DATA[type]||[]) : [];
  const totalItems = sections.reduce((a,s)=>a+s.items.length,0);
  const totalDone  = sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>!!itemState[`${si}_${ii}`]).length,0);
  const pct = totalItems ? Math.round(totalDone/totalItems*100) : 0;
  const totalHT = products.reduce((a,p)=>{const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);return a+price*(p.qty||1);},0);

  const clientInfo = { prenom, nom, email, telephone, codePostal, adresseChantier, denomination, tvaNum, clientType, refDossier, odooId };

  function handleAddProducts(newProds) {
    setProducts(ps=>{const ex=new Set(ps.map(p=>p.ref||p.name));const toAdd=newProds.filter(p=>!ex.has(p.ref||p.name));return[...ps,...toAdd.map(p=>({...p,qty:1}))];});
    setPanel(null);
  }
  function updateQty(i,d){setProducts(ps=>ps.map((p,x)=>x===i?{...p,qty:Math.max(0,(p.qty||1)+d)}:p).filter(p=>p.qty>0));}
  function removeProduct(i){setProducts(ps=>ps.filter((_,x)=>x!==i));}
  function setItemSt(si,ii,val){const k=`${si}_${ii}`;setItemState(st=>({...st,[k]:val===null?undefined:val}));}

  function saveToHistory(){
    try{
      const s=JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
      s.push({type,clientType,prenom,nom,email,telephone,codePostal,adresseChantier,denomination,tvaNum,refDossier,technicien,date,basinShape,basinL,basinW,basinD,basinNotes,itemState,itemData,products,obs,statut,signClient,signTech,savedAt:new Date().toISOString()});
      localStorage.setItem('pool_checklist_history',JSON.stringify(s.slice(-50)));
      setSaved(true);setTimeout(()=>setSaved(false),2500);
    }catch(e){alert('Erreur: '+e.message);}
  }
  function loadRecord(r){
    setType(r.type||'entretien');setStep(r.step||4);
    setClientType(r.clientType||'particulier');setPrenom(r.prenom||'');setNom(r.nom||'');setEmail(r.email||'');
    setTelephone(r.telephone||'');setCodePostal(r.codePostal||'');setAdresseChantier(r.adresseChantier||'');
    setDenomination(r.denomination||'');setTvaNum(r.tvaNum||'');setRefDossier(r.refDossier||'');
    setTechnicien(r.technicien||'');setDate(r.date||new Date().toISOString().split('T')[0]);
    setBasinShape(r.basinShape||'');setBasinL(r.basinL||'');setBasinW(r.basinW||'');setBasinD(r.basinD||'');setBasinNotes(r.basinNotes||'');
    setItemState(r.itemState||{});setItemData(r.itemData||{});setProducts(r.products||[]);setObs(r.obs||'');
    setStatut(r.statut||'en_cours');setSignClient(r.signClient||'');setSignTech(r.signTech||'');
  }
  function reset(){if(!confirm('Réinitialiser toute la fiche ?'))return;setStep(1);setType('');setPrenom('');setNom('');setEmail('');setTelephone('');setCodePostal('');setAdresseChantier('');setDenomination('');setTvaNum('');setRefDossier('');setTechnicien('');setDate(new Date().toISOString().split('T')[0]);setBasinShape('');setBasinL('');setBasinW('');setBasinD('');setBasinNotes('');setItemState({});setProducts([]);setObs('');setStatut('en_cours');setSignClient('');setSignTech('');setSaved(false);}

  const canNext = [
    true,
    type !== '',
    (prenom||nom||denomination) !== '',
    true,
  ];

  /* ── Styles ── */
  const LABEL_ST = {fontSize:13,fontWeight:600,color:'#475569',display:'block',marginBottom:5};
  const INPUT_ST = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 13px',fontFamily:'inherit',fontSize:14,outline:'none',boxSizing:'border-box'};

  const STEPS = ['Type d\'intervention','Infos client','Plan de bassin','Check-list & produits'];

  return (
    <div style={{fontFamily:"'Inter','Segoe UI',system-ui,sans-serif",background:'#f0f4f8',minHeight:'100vh',display:'flex',flexDirection:'column'}}>

      {/* ── Header ── */}
      <div style={{background:'#fff',borderBottom:'1.5px solid #e2e8f0',padding:'14px 24px',display:'flex',alignItems:'center',gap:14,flexShrink:0}}>
        <img src="/lolirine_pool_checklist/static/description/icon.png" alt="" style={{width:48,height:48,borderRadius:10,flexShrink:0}} />
        <div style={{flex:1}}>
          <div style={{fontWeight:800,fontSize:18,color:'#1e293b',letterSpacing:'-.3px'}}>Lolirine Pool Store — Fiche de visite chantier</div>
          <div style={{fontSize:12,color:'#94a3b8',marginTop:1}}>Diagnostic · intervention · produits liés · devis estimatif</div>
        </div>
        <div style={{display:'flex',gap:8,flexShrink:0}}>
          <button onClick={()=>setShowPlanning(true)} style={{background:'rgba(255,255,255,.15)',color:'#fff',border:'1.5px solid rgba(255,255,255,.4)',borderRadius:8,padding:'6px 12px',cursor:'pointer',fontWeight:600,fontSize:12}}>📅 Planning</button>
          <button onClick={()=>setShowHistory(true)} style={{background:'#f1f5f9',color:'#475569',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 13px',cursor:'pointer',fontWeight:600,fontSize:12}}>📁 Historique</button>
          <button onClick={saveToHistory} style={{background:saved?'#16a34a':'#f1f5f9',color:saved?'#fff':'#475569',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 13px',cursor:'pointer',fontWeight:600,fontSize:12,transition:'all .3s'}}>{saved?'✅ Sauvegardé':'💾 Sauvegarder'}</button>
          {lastSaved&&<span style={{fontSize:11,color:'#16a34a',display:'flex',alignItems:'center',gap:4,background:'#f0fdf4',border:'1px solid #bbf7d0',borderRadius:8,padding:'4px 9px',whiteSpace:'nowrap'}}><span style={{width:6,height:6,borderRadius:'50%',background:'#16a34a',display:'inline-block'}}/>Auto {Math.round((Date.now()-lastSaved)/1000)}s</span>}
          <button onClick={reset} style={{background:'#f1f5f9',color:'#94a3b8',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 10px',cursor:'pointer',fontSize:12}}>↺</button>
          <a href="/odoo" style={{background:'#f1f5f9',color:'#475569',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'7px 13px',cursor:'pointer',fontWeight:600,fontSize:12,textDecoration:'none',display:'flex',alignItems:'center',gap:4}}>← Retour Odoo</a>
        </div>
      </div>

      {/* ── Stepper ── */}
      <div style={{background:'#fff',borderBottom:'1.5px solid #e2e8f0',padding:'16px 24px',flexShrink:0}}>
        <div style={{display:'flex',alignItems:'center',maxWidth:700,margin:'0 auto'}}>
          {STEPS.map((s,i)=>{
            const n=i+1;
            const done=n<step;
            const active=n===step;
            return(
              <React.Fragment key={n}>
                <div style={{display:'flex',flexDirection:'column',alignItems:'center',flex:i<STEPS.length-1?'none':1,cursor:done?'pointer':'default'}} onClick={()=>done&&setStep(n)}>
                  <div style={{width:36,height:36,borderRadius:'50%',background:done?'#0ea5e9':active?'#0ea5e9':'#e2e8f0',border:`2px solid ${done||active?'#0ea5e9':'#e2e8f0'}`,display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:14,color:done||active?'#fff':'#94a3b8',transition:'all .3s'}}>
                    {done?'✓':n}
                  </div>
                  <div style={{fontSize:11,fontWeight:active?700:500,color:active?'#0ea5e9':done?'#1e293b':'#94a3b8',marginTop:5,whiteSpace:'nowrap',textAlign:'center'}}>{s}</div>
                </div>
                {i<STEPS.length-1&&<div style={{flex:1,height:2,background:done?'#0ea5e9':'#e2e8f0',margin:'0 8px',marginBottom:20,transition:'background .3s'}} />}
              </React.Fragment>
            );
          })}
        </div>
        {step===4&&totalItems>0&&(
          <div style={{maxWidth:700,margin:'12px auto 0',display:'flex',alignItems:'center',gap:10}}>
            <div style={{flex:1,height:6,background:'#e2e8f0',borderRadius:6,overflow:'hidden'}}><div style={{height:'100%',background:pct===100?'#16a34a':'#0ea5e9',width:`${pct}%`,borderRadius:6,transition:'width .4s'}} /></div>
            <span style={{fontSize:12,fontWeight:700,color:pct===100?'#16a34a':'#0ea5e9',whiteSpace:'nowrap'}}>{totalDone}/{totalItems} · {pct}%</span>
          </div>
        )}
      </div>

      {/* ── Contenu ── */}
      <div style={{flex:1,overflowY:'auto',padding:'28px 16px'}}>
        <div style={{maxWidth:900,margin:'0 auto'}}>

          {/* ════ Étape 1 — Type d'intervention ════ */}
          {step===1&&(
            <div>
              <h2 style={{fontSize:22,fontWeight:800,color:'#1e293b',marginBottom:6,marginTop:0}}>Sélectionner le type d'intervention</h2>
              <p style={{fontSize:14,color:'#64748b',marginBottom:24,marginTop:0}}>Choisissez le type d'intervention pour charger la check-list correspondante.</p>
              <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:14}}>
                {INTERVENTION_TYPES.map(t=>{
                  const sects = SECTIONS_DATA[t.key]||[];
                  const pts   = sects.reduce((a,s)=>a+s.items.length,0);
                  const sel   = type===t.key;
                  return(
                    <div key={t.key} onClick={()=>setType(t.key)}
                      style={{background:'#fff',borderRadius:14,padding:'20px 22px',border:`2px solid ${sel?t.color:'#e2e8f0'}`,cursor:'pointer',transition:'all .2s',boxShadow:sel?`0 0 0 4px ${t.color}22`:'0 1px 4px rgba(0,0,0,.06)',transform:sel?'translateY(-2px)':'none'}}>
                      <div style={{fontSize:28,marginBottom:8}}>{t.icon}</div>
                      <div style={{fontWeight:800,fontSize:16,color:'#1e293b',marginBottom:4}}>{t.label}</div>
                      <div style={{fontSize:12,color:'#94a3b8'}}>{pts} points · {sects.length} sections</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ════ Étape 2 — Infos client ════ */}
          {step===2&&(
            <div style={{maxWidth:680,margin:'0 auto'}}>
              <h2 style={{fontSize:22,fontWeight:800,color:'#1e293b',marginBottom:6,marginTop:0}}>Informations client</h2>
              <p style={{fontSize:14,color:'#64748b',marginBottom:24,marginTop:0}}>Renseignez les coordonnées du client et les informations du chantier.</p>

              {/* Particulier / Professionnel */}
              <div style={{background:'#fff',borderRadius:14,padding:'20px 22px',marginBottom:20,border:'1.5px solid #e2e8f0'}}>
                <label style={{...LABEL_ST,marginBottom:12}}>Type de client</label>
                <div style={{display:'flex',gap:10,marginBottom:20}}>
                  {[{k:'particulier',l:'👤 Particulier'},{k:'professionnel',l:'🏢 Professionnel'}].map(opt=>(
                    <button key={opt.k} onClick={()=>setClientType(opt.k)}
                      style={{flex:1,padding:'10px 16px',borderRadius:10,border:`2px solid ${clientType===opt.k?'#0ea5e9':'#e2e8f0'}`,background:clientType===opt.k?'#eff9ff':'#fff',color:clientType===opt.k?'#0369a1':'#475569',fontWeight:clientType===opt.k?700:500,fontSize:14,cursor:'pointer',transition:'all .15s'}}>
                      {opt.l}
                    </button>
                  ))}
                </div>

                {/* Champs professionnel */}
                {clientType==='professionnel'&&(
                  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14,marginBottom:14,paddingBottom:14,borderBottom:'1px solid #f0f4f8'}}>
                    <div style={{gridColumn:'1/-1'}}>
                      <label style={LABEL_ST}>Dénomination sociale *</label>
                      <ClientAutocomplete value={denomination} onChange={setDenomination} onSelectPartner={p=>{setDenomination(p.name);setOdooId(p.id);}} placeholder="Rechercher une entreprise…" />
                    </div>
                    <div>
                      <label style={LABEL_ST}>Numéro de TVA (BE)</label>
                      <input value={tvaNum} onChange={e=>setTvaNum(e.target.value)} placeholder="BE 0XXX.XXX.XXX" style={INPUT_ST} />
                    </div>
                  </div>
                )}

                {/* Contact */}
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
                  {clientType==='particulier'&&(
                    <div style={{gridColumn:'1/-1'}}>
                      <label style={LABEL_ST}>Client Odoo (optionnel)</label>
                      <ClientAutocomplete value={prenom&&nom?`${prenom} ${nom}`:prenom||nom} onChange={v=>{setPrenom(v.split(' ')[0]||'');setNom(v.split(' ').slice(1).join(' ')||'');}} onSelectPartner={p=>{const parts=p.name.split(' ');setPrenom(parts[0]||'');setNom(parts.slice(1).join(' ')||'');setOdooId(p.id);}} placeholder="Rechercher un client existant…" />
                    </div>
                  )}
                  <div>
                    <label style={LABEL_ST}>Prénom *</label>
                    <input value={prenom} onChange={e=>setPrenom(e.target.value)} placeholder="Jean" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Nom *</label>
                    <input value={nom} onChange={e=>setNom(e.target.value)} placeholder="Dupont" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Email</label>
                    <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="jean.dupont@email.com" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Téléphone</label>
                    <input value={telephone} onChange={e=>setTelephone(e.target.value)} placeholder="0475/12 34 56" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Code postal</label>
                    <input value={codePostal} onChange={e=>setCodePostal(e.target.value)} placeholder="4000" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Référence dossier</label>
                    <input value={refDossier} onChange={e=>setRefDossier(e.target.value)} placeholder="CHT-2025-042" style={INPUT_ST} />
                  </div>
                  <div style={{gridColumn:'1/-1'}}>
                    <label style={LABEL_ST}>Adresse du chantier</label>
                    <AddressAutocomplete value={adresseChantier} onChange={setAdresseChantier} placeholder="Adresse complète du chantier…" />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Technicien</label>
                    <input value={technicien} onChange={e=>setTechnicien(e.target.value)} placeholder="Prénom Nom" style={INPUT_ST} />
                  </div>
                  <div>
                    <label style={LABEL_ST}>Date de visite</label>
                    <input type="date" value={date} onChange={e=>setDate(e.target.value)} style={INPUT_ST} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ════ Étape 3 — Plan de bassin ════ */}
          {step===3&&(
            <div style={{maxWidth:680,margin:'0 auto'}}>
              <h2 style={{fontSize:22,fontWeight:800,color:'#1e293b',marginBottom:6,marginTop:0}}>Plan de bassin</h2>
              <p style={{fontSize:14,color:'#64748b',marginBottom:24,marginTop:0}}>Forme, dimensions et caractéristiques du bassin (optionnel).</p>
              <div style={{background:'#fff',borderRadius:14,padding:'20px 22px',marginBottom:20,border:'1.5px solid #e2e8f0'}}>
                <label style={{...LABEL_ST,marginBottom:12}}>Forme du bassin</label>
                <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:10,marginBottom:20}}>
                  {BASIN_SHAPES.map(s=>(
                    <button key={s.key} onClick={()=>setBasinShape(s.key)}
                      style={{padding:'14px 10px',borderRadius:11,border:`2px solid ${basinShape===s.key?'#0ea5e9':'#e2e8f0'}`,background:basinShape===s.key?'#eff9ff':'#fff',cursor:'pointer',transition:'all .15s',textAlign:'center'}}>
                      <div style={{fontSize:24,marginBottom:4}}>{s.icon}</div>
                      <div style={{fontSize:12,fontWeight:basinShape===s.key?700:500,color:basinShape===s.key?'#0369a1':'#475569'}}>{s.label}</div>
                    </button>
                  ))}
                </div>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:14,marginBottom:14}}>
                  <div><label style={LABEL_ST}>Longueur (m)</label><input type="number" value={basinL} onChange={e=>setBasinL(e.target.value)} placeholder="10.0" min={0} step={0.1} style={INPUT_ST} /></div>
                  <div><label style={LABEL_ST}>Largeur (m)</label><input type="number" value={basinW} onChange={e=>setBasinW(e.target.value)} placeholder="5.0" min={0} step={0.1} style={INPUT_ST} /></div>
                  <div><label style={LABEL_ST}>Profondeur max (m)</label><input type="number" value={basinD} onChange={e=>setBasinD(e.target.value)} placeholder="1.5" min={0} step={0.1} style={INPUT_ST} /></div>
                </div>
                {basinL&&basinW&&basinD&&<div style={{background:'#f0f9ff',borderRadius:9,padding:'10px 14px',marginBottom:14,fontSize:13,color:'#0369a1',fontWeight:600}}>
                  Surface : {(parseFloat(basinL)*parseFloat(basinW)).toFixed(1)} m² · Volume estimé : {(parseFloat(basinL)*parseFloat(basinW)*parseFloat(basinD)*0.8).toFixed(1)} m³
                </div>}
                <div><label style={LABEL_ST}>Notes sur le bassin</label><textarea value={basinNotes} onChange={e=>setBasinNotes(e.target.value)} placeholder="Particularités, contraintes, équipements existants…" rows={3} style={{...INPUT_ST,resize:'vertical',lineHeight:1.5}} /></div>
              </div>
            </div>
          )}

          {/* ════ Étape 4 — Check-list & produits ════ */}
          {step===4&&(
            <div>
              {/* Stats bar */}
              {totalItems>0&&(
                <div style={{display:'flex',gap:9,marginBottom:16,flexWrap:'wrap'}}>
                  {[
                    {label:'Total',value:totalItems,bg:'#f1f5f9',tc:'#475569',vc:'#1e293b'},
                    {label:'Conformes',value:sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>itemState[`${si}_${ii}`]==='ok').length,0),bg:'#eaf3de',tc:'#639922',vc:'#3b6d11'},
                    {label:'Attention',value:sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>itemState[`${si}_${ii}`]==='warn').length,0),bg:'#faeeda',tc:'#ba7517',vc:'#854f0b'},
                    {label:'Problèmes',value:sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>itemState[`${si}_${ii}`]==='bad').length,0),bg:'#fcebeb',tc:'#e24b4a',vc:'#a32d2d'},
                    {label:'Non traités',value:totalItems-totalDone,bg:'#f8fafc',tc:'#94a3b8',vc:'#64748b'},
                  ].map(stat=>(
                    <div key={stat.label} style={{flex:1,minWidth:70,background:stat.bg,borderRadius:10,padding:'10px 12px',textAlign:'center',cursor:'pointer'}} onClick={()=>setFilter4(f=>f===stat.label.toLowerCase().replace(' ','_')?'all':stat.label.toLowerCase().replace(' ','_'))}>
                      <div style={{fontSize:22,fontWeight:700,color:stat.vc,lineHeight:1}}>{stat.value}</div>
                      <div style={{fontSize:11,color:stat.tc,marginTop:3}}>{stat.label}</div>
                    </div>
                  ))}
                </div>
              )}
              {/* Filtres + recherche */}
              <div style={{display:'flex',gap:6,marginBottom:14,flexWrap:'wrap',alignItems:'center'}}>
                {[{k:'all',l:'Tous'},{k:'ok',l:'OK'},{k:'warn',l:'Attention'},{k:'bad',l:'Problèmes'},{k:'untreated',l:'Non traités'}].map(f=>(
                  <button key={f.k} onClick={()=>setFilter4(filter4===f.k?'all':f.k)}
                    style={{padding:'4px 13px',borderRadius:20,border:`1.5px solid ${filter4===f.k?'#0ea5e9':'#e2e8f0'}`,background:filter4===f.k?'#0ea5e9':'#fff',color:filter4===f.k?'#fff':'#64748b',fontWeight:filter4===f.k?600:400,fontSize:12,cursor:'pointer',transition:'all .15s'}}>
                    {f.l}
                  </button>
                ))}
                <input value={search4} onChange={e=>setSearch4(e.target.value)} placeholder="Rechercher un point…"
                  style={{flex:1,minWidth:140,height:30,border:'1.5px solid #e2e8f0',borderRadius:20,padding:'0 14px',fontFamily:'inherit',fontSize:12,outline:'none',color:'#334155'}} />
              </div>
              {/* Sections filtrées */}
              {sections.map((s,si)=>{
                const filteredItems=s.items.map((item,ii)=>({item,ii})).filter(({item,ii})=>{
                  const st=itemState[`${si}_${ii}`]||'';
                  if(search4&&!item.toLowerCase().includes(search4.toLowerCase()))return false;
                  if(filter4==='all'||!filter4)return true;
                  if(filter4==='ok')return st==='ok';
                  if(filter4==='warn')return st==='warn';
                  if(filter4==='bad')return st==='bad';
                  if(filter4==='untreated')return st==='';
                  return true;
                });
                if(filteredItems.length===0)return null;
                return(
                  <SectionBlock key={`${type}-${si}`} section={s.section} items={s.items}
                    state={Object.fromEntries(s.items.map((_,ii)=>[ii,itemState[`${si}_${ii}`]||'']))}
                    onSetState={(ii,val)=>setItemSt(si,ii,val)}
                    onOpenProducts={(item,sec)=>setPanel({item,sectionLabel:sec})}
                    filterStatus={filter4}
                    searchText={search4}
                    itemData={Object.fromEntries(s.items.map((_,ii)=>[ii,itemData[`${si}_${ii}`]]))}
                    onSetItemData={(ii,vals)=>setItemData(d=>({...d,[`${si}_${ii}`]:vals}))} />
                );
              })}

              {/* Remarques */}
              <div style={{background:'#fff',borderRadius:12,padding:'16px 18px',marginBottom:12,border:'1.5px solid #e2e8f0'}}>
                <div style={{fontWeight:700,fontSize:14,color:'#1e293b',marginBottom:8}}>📝 Remarques générales</div>
                <textarea value={obs} onChange={e=>setObs(e.target.value)} placeholder="Observations générales, conditions d'accès, points particuliers à noter…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:'inherit',fontSize:13,outline:'none',resize:'vertical',minHeight:80,boxSizing:'border-box',lineHeight:1.5}} />
              </div>

              {/* Matériaux */}
              {products.length>0&&(
                <div style={{background:'#fff',borderRadius:12,padding:'16px 18px',marginBottom:12,border:'1.5px solid #e2e8f0'}}>
                  <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:12,flexWrap:'wrap'}}>
                    <div style={{fontWeight:700,fontSize:14,color:'#1e293b',flex:1}}>🛒 Matériaux sélectionnés ({products.length})</div>
                    <button onClick={()=>setShowQuote(true)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:8,padding:'7px 15px',fontWeight:700,fontSize:12,cursor:'pointer'}}>📄 Créer un devis</button>
                  </div>
                  <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
                    <thead><tr style={{borderBottom:'2px solid #f0f4f8'}}>{['Désignation','Fourn.','Unité','Qté','Total HT',''].map((h,i)=><th key={i} style={{textAlign:'left',padding:'5px 7px',fontWeight:600,color:'#64748b',fontSize:11}}>{h}</th>)}</tr></thead>
                    <tbody>{products.map((p,i)=>{const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);const sup=p.suppliers?.[0]||{};return<tr key={i} style={{borderBottom:'1px solid #f8fafc'}}>
                      <td style={{padding:'6px 7px',fontWeight:500,color:'#1e293b'}}>{p.name}</td>
                      <td style={{padding:'6px 7px',color:'#7c3aed',fontSize:11}}>{sup.name||p.category||'—'}</td>
                      <td style={{padding:'6px 7px',color:'#64748b',fontSize:11}}>{p.unit||'pcs'}</td>
                      <td style={{padding:'6px 7px'}}><div style={{display:'flex',alignItems:'center',gap:3}}><button onClick={()=>updateQty(i,-1)} style={{width:19,height:19,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:11}}>−</button><span style={{fontWeight:700,minWidth:18,textAlign:'center'}}>{p.qty||1}</span><button onClick={()=>updateQty(i,+1)} style={{width:19,height:19,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:11}}>+</button></div></td>
                      <td style={{padding:'6px 7px',color:'#0369a1',fontWeight:700,whiteSpace:'nowrap'}}>{price>0?(price*(p.qty||1)).toFixed(2)+' €':'—'}</td>
                      <td style={{padding:'6px 7px'}}><button onClick={()=>removeProduct(i)} style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',fontSize:13}}>✕</button></td>
                    </tr>;})}
                    </tbody>
                    {totalHT>0&&<tfoot><tr style={{borderTop:'2px solid #e2e8f0'}}><td colSpan={4} style={{padding:'7px 7px',textAlign:'right',fontWeight:800,fontSize:13,color:'#0369a1'}}>Total estimatif HT :</td><td style={{padding:'7px 7px',fontWeight:800,fontSize:14,color:'#0369a1',whiteSpace:'nowrap'}}>{totalHT.toFixed(2)} €</td><td/></tr></tfoot>}
                  </table>
                </div>
              )}

              {/* Signatures */}
              <div style={{background:'#fff',borderRadius:12,padding:'16px 18px',marginBottom:12,border:'1.5px solid #e2e8f0'}}>
                <div style={{fontWeight:700,fontSize:14,color:'#1e293b',marginBottom:12}}>✍️ Signatures</div>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
                  <div>
                    <label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:5}}>Signature du technicien</label>
                    <input value={signTech||technicien} onChange={e=>setSignTech(e.target.value)} placeholder={technicien||'Prénom Nom technicien'} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:"Georgia,serif",fontSize:16,outline:'none',boxSizing:'border-box',fontStyle:'italic',color:'#1e293b'}} />
                    {(signTech||technicien)&&<div style={{fontSize:11,color:'#0ea5e9',marginTop:3}}>✓ Intervenu par {signTech||technicien} le {date}</div>}
                  </div>
                  <div>
                    <label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:5}}>Signature du client (bon pour accord)</label>
                    <input value={signClient} onChange={e=>setSignClient(e.target.value)} placeholder={[prenom,nom].filter(Boolean).join(' ')||denomination||'Nom complet du client'} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:"Georgia,serif",fontSize:16,outline:'none',boxSizing:'border-box',fontStyle:'italic',color:'#1e293b'}} />
                    {signClient&&<div style={{fontSize:11,color:'#16a34a',marginTop:3}}>✓ Lu et approuvé par {signClient}</div>}
                  </div>
                </div>
              </div>

              {/* Enregistrement */}
              <div style={{background:'#fff',borderRadius:12,border:'1.5px solid #e2e8f0',marginBottom:12,overflow:'hidden'}}>
                <div style={{background:'#1e293b',padding:'11px 16px',display:'flex',alignItems:'center',gap:8}}>
                  <span style={{fontWeight:800,fontSize:14,color:'#fff'}}>📋 Enregistrement de la fiche</span>
                  <span style={{marginLeft:'auto',fontSize:11,color:'rgba(255,255,255,.55)'}}>Statut · Sauvegarde</span>
                </div>
                <div style={{padding:16}}>
                  <div style={{fontWeight:700,fontSize:12,color:'#1e293b',marginBottom:8}}>Statut de la visite</div>
                  <div style={{display:'flex',gap:7,flexWrap:'wrap',marginBottom:14}}>
                    {[{k:'en_cours',l:'🔄 En cours',c:'#f59e0b'},{k:'termine',l:'✅ Terminée',c:'#16a34a'},{k:'a_replanifier',l:'🔁 À replanifier',c:'#ef4444'},{k:'attente_pieces',l:'⏳ Attente pièces',c:'#8b5cf6'}].map(s=>(
                      <button key={s.k} onClick={()=>setStatut(s.k)} style={{padding:'7px 13px',borderRadius:9,border:`2px solid ${statut===s.k?s.c:'#e2e8f0'}`,background:statut===s.k?s.c+'22':'#fff',color:statut===s.k?s.c:'#475569',fontWeight:statut===s.k?700:500,fontSize:12,cursor:'pointer',transition:'all .15s'}}>{s.l}</button>
                    ))}
                  </div>
                  <div style={{background:'#f8fafc',borderRadius:9,padding:'10px 14px',marginBottom:14,fontSize:12,color:'#475569',display:'flex',gap:14,flexWrap:'wrap'}}>
                    <span>👤 {[prenom,nom].filter(Boolean).join(' ')||denomination||'—'}</span>
                    <span>📅 {date}</span>
                    <span>🔧 {INTERVENTION_TYPES.find(t=>t.key===type)?.label||type}</span>
                    <span>✅ {totalDone}/{totalItems} ({pct}%)</span>
                    {products.length>0&&<span>🛒 {products.length} produit{products.length>1?'s':''} — {totalHT.toFixed(2)} € HT</span>}
                  </div>
                  <div style={{display:'flex',gap:9,flexWrap:'wrap'}}>
                    <button onClick={saveToHistory} style={{background:saved?'#16a34a':'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'10px 22px',fontWeight:700,fontSize:13,cursor:'pointer',flex:1,minWidth:180,transition:'background .3s'}}>{saved?'✅ Fiche enregistrée !':'💾 Enregistrer la fiche'}</button>
                    <button onClick={()=>setShowQuote(true)} style={{background:'#7c3aed',color:'#fff',border:'none',borderRadius:9,padding:'10px 18px',fontWeight:700,fontSize:12,cursor:'pointer'}}>📄 Créer un devis</button>
                    <button onClick={()=>window.print()} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'10px 16px',fontWeight:600,fontSize:12,cursor:'pointer',color:'#475569'}}>🖨️ Imprimer / PDF</button>
                  </div>
                </div>
              </div>

              <div style={{textAlign:'center',padding:'8px 0 16px',fontSize:11,color:'#94a3b8'}}>Lolirine Pool Store · lolirinepoolstore.be · BCE 0650.891.279</div>
            </div>
          )}

        </div>{/* fin maxWidth */}
      </div>{/* fin scroll */}

      {/* ── Navigation bas ── */}
      <div style={{background:'#fff',borderTop:'1.5px solid #e2e8f0',padding:'14px 24px',display:'flex',justifyContent:'space-between',alignItems:'center',flexShrink:0}}>
        <button onClick={()=>setStep(s=>Math.max(1,s-1))} disabled={step===1}
          style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:10,padding:'10px 22px',fontWeight:600,fontSize:14,cursor:step===1?'default':'pointer',color:step===1?'#cbd5e1':'#475569',opacity:step===1?.4:1}}>
          ← Précédent
        </button>
        <div style={{display:'flex',gap:6}}>
          {[1,2,3,4].map(n=><div key={n} style={{width:8,height:8,borderRadius:'50%',background:step===n?'#0ea5e9':'#e2e8f0',transition:'background .3s'}} />)}
        </div>
        {step<4
          ? <button onClick={()=>canNext[step]&&setStep(s=>s+1)} disabled={!canNext[step]}
              style={{background:canNext[step]?'#0ea5e9':'#cbd5e1',color:'#fff',border:'none',borderRadius:10,padding:'10px 28px',fontWeight:700,fontSize:14,cursor:canNext[step]?'pointer':'default'}}>
              Suivant →
            </button>
          : <button onClick={()=>setShowQuote(true)}
              style={{background:'#7c3aed',color:'#fff',border:'none',borderRadius:10,padding:'10px 24px',fontWeight:700,fontSize:14,cursor:'pointer'}}>
              📄 Créer un devis
            </button>
        }
      </div>

      {/* Modals */}
      {showPlanning&&<PlanningModal type={type} clientName={[prenom,nom].filter(Boolean).join(' ')||denomination||'Client'} startDate={date} onClose={()=>setShowPlanning(false)} />
      }
      {panel&&<ProductPanel item={panel.item} sectionLabel={panel.sectionLabel} onAdd={handleAddProducts} onClose={()=>setPanel(null)} />}
      {showQuote&&<QuoteModal products={products} clientInfo={clientInfo} onClose={()=>setShowQuote(false)} onCreated={()=>{}} />}
      {showHistory&&<HistoryModal onClose={()=>setShowHistory(false)} onLoad={loadRecord} />}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   MOUNT
═══════════════════════════════════════════════════ */
ReactDOM.createRoot(document.getElementById('pool-checklist-root')).render(<PoolChecklist />);
