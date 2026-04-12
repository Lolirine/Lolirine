/* pool_checklist.js — Lolirine Pool Store © 2025
   React 18 · Babel standalone · Pas de build
   window.LOLIRINE_CHECKLIST_CONFIG = { csrfToken, productsEndpoint, aiEndpoint, partnerEndpoint, quoteEndpoint }
*/
/* global React, ReactDOM */
const { useState, useEffect, useRef, useCallback } = React;

/* ═══════════════════════════════════════════════════
   DONNÉES — sections par type d'intervention
═══════════════════════════════════════════════════ */
const SECTIONS_DATA = {
  construction: [
    { section:"🏗️ Génie civil & structure", items:["Type de bassin : béton / projeté / kit acier / polyester","Dimensions (L×l×prof.) : ______","Forme : rectangulaire / L / ovale / haricot","Profondeur mini : ___m — maxi : ___m","Escalier : romain / angles / côté","Banquette / sun-shelf prévue","Vérification portance sol","Étanchéité : enduit / membrane / liner","Joints de dilatation bassin/plage"] },
    { section:"🔧 Filtration & hydraulique", items:["Débit calculé (m³/h) : ______","Pompe : ___kW / ___m³/h","Filtre : sable / cartouche / DE — vol. ___m³","Skimmer(s) : nombre ___","Bonde(s) de fond : nombre ___","Vanne multivoies 6/4 voies","Préfiltre pompe inox","Tuyauterie PVC ø50/63/90","Pompe brassage / nage à contre-courant"] },
    { section:"💊 Traitement de l'eau", items:["Électrolyseur sel (capacité m³) : ______","Pompe doseuse pH-","Pompe doseuse chlore / PAC","Régulateur ORP + sonde","Sonde pH","Analyseur en ligne (Lovibond)","Local produits chimiques (fermé)"] },
    { section:"🌡️ Chauffage", items:["Pompe à chaleur air/eau (___kW)","PAC réversible (piscine + abri)","Échangeur thermique (chaudière)","Solaire thermique (___m²)","Résistance électrique (___kW)","Couverture solaire à bulles 400µ","Volet roulant isolant"] },
    { section:"💡 Électricité & éclairage", items:["Projecteurs LED RGB subaquatiques","Coffret IP65 dédié piscine","Disjoncteur différentiel 30mA","Liaison équipotentielle NF C 15-100","Mise à la terre générale","Câbles gainés sous dallage","Armoire domotique (optionnel)"] },
    { section:"🪟 Couverture & sécurité", items:["Volet roulant immergé / hors-sol","Couverture barres auto/manuelle","Filet NF P 90-308","Alarme piscine OBLIGATOIRE — type : ______","Clôture h≥1,10m + portillon auto-fermant","Signalétique profondeur / plongée"] },
    { section:"🏡 Plage & finitions", items:["Margelles (carrelage / pierre / béton)","Dallage antidérapant R11","Drainage plage (pente 1%)","Douche solaire","Local technique (ventilé)","Nettoyage chantier / réception","Notice utilisation remise client"] },
    { section:"🤝 Administratif", items:["Devis signé + acompte","Planning remis","Coordonnées sous-traitants","Garantie décennale + RC pro","Photos avant/pendant/après","Formation client","Contrat d'entretien proposé"] },
  ],
  renovation: [
    { section:"🔍 Diagnostic structure", items:["Fissures (fines / traversantes / actives)","Test étanchéité (colorant)","État fond & parois","Corrosion armatures","Scellements (bondes, skimmers, projecteurs)","Désolidarisation margelles / plage","Tassement plage"] },
    { section:"🎨 Revêtement existant", items:["Type actuel : ______  — Âge : ___ans","Liner : déchirures / décollements","Carrelage : joints décollés / cassés","Enduit : farinage / effritement","Membrane armée : décollement","Décision : remplacement ou réfection ?"] },
    { section:"🔧 Équipements existants", items:["Pompe — âge : ___ans — état : ______","Filtre — type / âge : ______","Skimmers : joints / collerettes","Bondes de fond : étanchéité","Vanne multivoies : état","Électrolyseur : cellule OK ?","Câblage conforme ?"] },
    { section:"🛠️ Travaux prévus", items:["Reprise fissures (résine / mortier cristallin)","Nouveau revêtement : liner / carrelage / résine","Remplacement skimmer(s)","Remplacement pompe","Remplacement filtre + média","Mise aux normes électriques","Reprise margelles / plage"] },
    { section:"🤝 Fin chantier rénovation", items:["Photos avant/après","Mise en eau 24h surveillée","Première analyse eau","Rapport remis client"] },
  ],
  entretien: [
    { section:"💧 Analyse eau", items:["pH (cible 7,2–7,6) → ______","TAC (80–120 mg/L) → ______","TH (150–300 mg/L) → ______","Chlore libre (1–3 mg/L) → ______","Chlore combiné (<0,6 mg/L) → ______","Sel électrolyseur (cible ___ g/L) → ______","Cyanurate (<75 mg/L) → ______","Phosphates (<0,1 mg/L) → ______","Température eau (°C) → ______","Turbidité : limpide / trouble / verte"] },
    { section:"🧹 Nettoyage bassin", items:["Écrémage surface","Aspiration fond (manuel / robot)","Brossage parois & fond","Ligne de flottaison (calcaire / graisses)","Panier(s) skimmer(s)","Panier préfiltre pompe","Contre-lavage filtre (si pression ≥0,5 bar)","Cartouche filtrante (si applicable)","Niche projecteur(s)","Rinçage plage / abords","Nettoyage local technique"] },
    { section:"🔄 Filtration & équipements", items:["Pression manomètre : ___bar","Débit pompe vérifié","Bruit / vibration pompe","Programmateur / horloge","Vanne multivoies (fuite ?)","Électrolyseur (cellule / production)","Pompe doseuse pH","Sonde ORP / pH","Niveau eau (mi-skimmer)","Alarme piscine","Volet / mécanisme"] },
    { section:"💊 Traitements correctifs", items:["Correction pH : ______","Correction TAC : ______","Correction TH : ______","Choc chlore (dose) : ______","Algicide préventif","Floculant / clarifiant","Anti-phosphates"] },
    { section:"📋 Observations & suivi", items:["Prochaine vidange partielle (%) : ______","Prochain contre-lavage","Remplacement média filtrant à prévoir","Pièces à commander : ______","Prochain passage : ______","Rapport envoyé client"] },
  ],
  hivernage: [
    { section:"💧 Traitement avant hivernage", items:["Analyse complète","Correction pH à 7,2","Choc chlore hivernage : ______","Algicide longue durée","Anti-calcaire / séquestrant","Floculant si eau trouble","Niveau eau abaissé sous skimmers"] },
    { section:"🔧 Vidange équipements", items:["Contre-lavage + rinçage filtre","Vidange pompe (corps + préfiltre)","Vidange filtre","Vidange vanne multivoies","Vidange tuyauteries (air comprimé)","Vanne multivoies en position hivernage","Débranchement pompe + hors tension","Rangement accessoires"] },
    { section:"❄️ Protection gel", items:["Déconnexion / rangement électrolyseur","Démontage pompe doseuse","Protection anti-gel local technique","Isolant tuyauteries exposées","Flotteur(s) anti-gel posé(s)","Alimentation électrique coupée"] },
    { section:"🪟 Couverture hivernage", items:["Volet / couverture en place","Filet anti-feuilles posé","Nettoyage couverture avant pose","Alarme piscine : piles / fonctionnement"] },
  ],
  remise_en_route: [
    { section:"🧹 Remise en état", items:["Retrait couverture / filet — nettoyage","Remise en eau (niveau mi-skimmer)","Nettoyage fond et parois","Aspiration résidus fond","Nettoyage skimmers et préfiltre","Nettoyage local technique"] },
    { section:"🔧 Remontage équipements", items:["Remontage pompe + joint préfiltre","Reconnexion vanne multivoies","Remontage cellule électrolyseur","Remontage pompe doseuse + amorçage","Reconnexion sondes pH / ORP","Vérification raccords (fuites ?)","Mise sous tension + test démarrage"] },
    { section:"💧 1ère analyse & traitement", items:["pH : ___→correction : ______","TAC : ___→correction : ______","Sel : ___→correction : ______","Choc chlore d'ouverture : ______","Algicide de départ","Anti-calcaire","Attente filtration 48h"] },
    { section:"⚙️ Vérifications finales", items:["Programmateur réglé","Électrolyseur réglé (% production)","PAC / chauffe-eau remis en route","Alarme testée","Volet testé (course complète)","Éclairage testé","Rapport remise en route envoyé"] },
  ],
  materiel: [
    { section:"🔧 Matériel à remplacer", items:["Pompe — modèle actuel : ______","Remplacement par : ______","Filtre — modèle actuel : ______","Remplacement par : ______","Électrolyseur (cellule/groupe) : ______","Projecteur(s) — type LED : ______","Volet / armoire volet : ______","Robot nettoyeur : ______","Autre : ______"] },
    { section:"📦 Accessoires & consommables", items:["Panier skimmer(s) — réf : ______","Panier préfiltre — réf : ______","Médias filtrants — type + qté : ______","Joints vanne multivoies — réf : ______","Manche + balai aspirateur","Raclette / épuisette","Bâche à bulles — dim : ______"] },
    { section:"💊 Produits chimiques", items:["pH- — qté : ______","pH+ — qté : ______","Chlore choc — qté : ______","Chlore lent galets — qté : ______","Algicide concentré — qté : ______","Anti-calcaire — qté : ______","Sel électrolyse (sacs 25kg) — nb : ______"] },
    { section:"🤝 Fin intervention", items:["Ancien matériel évacué","Mise en service validée","Test fonctionnement OK","Notice + garanties remises","Bon livraison / facture émis"] },
  ],
};

const INTERVENTION_TYPES = [
  {key:"construction",    label:"🏗️ Construction"},
  {key:"renovation",      label:"🔨 Rénovation"},
  {key:"entretien",       label:"🧹 Entretien"},
  {key:"hivernage",       label:"❄️ Hivernage"},
  {key:"remise_en_route", label:"🌱 Remise en route"},
  {key:"materiel",        label:"📦 Changement matériel"},
];

/* ═══════════════════════════════════════════════════
   ClientAutocomplete
═══════════════════════════════════════════════════ */
function ClientAutocomplete({value, onChange, onSelectId}) {
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
        const r = await fetch(cfg.partnerEndpoint || '/pool-checklist/search-partner', {
          method:'POST', credentials:'same-origin',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{query:v,limit:8}})
        });
        const d = await r.json();
        const list = d?.result?.partners || [];
        setSuggs(list); setOpen(list.length > 0);
      } catch { setSuggs([]); setOpen(false); }
    }, 280);
  }

  return (
    <div ref={wrap} style={{position:'relative'}}>
      <input value={value} onChange={e=>handleChange(e.target.value)}
        onFocus={()=>suggs.length && setOpen(true)}
        placeholder="Nom du client…"
        style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'8px 12px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'}} />
      {open && (
        <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:900,background:'#fff',border:'1.5px solid #dde4ed',borderRadius:9,boxShadow:'0 8px 24px rgba(0,0,0,.12)',marginTop:3,maxHeight:200,overflowY:'auto'}}>
          {suggs.map((p,i)=>(
            <div key={i} onClick={()=>{onChange(p.name);onSelectId&&onSelectId(p.id);setOpen(false);setSuggs([]);}}
              style={{padding:'8px 13px',cursor:'pointer',fontSize:13,borderBottom:i<suggs.length-1?'1px solid #f0f4f8':'none'}}
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
function AddressAutocomplete({value, onChange}) {
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
        'https://nominatim.openstreetmap.org/search?' +
        new URLSearchParams({q:v, countrycodes:'be,lu,fr,nl', format:'json', limit:'6', addressdetails:'1'}),
        {mode:'cors', headers:{'Accept-Language':'fr'}}
      );
      const data = await res.json();
      const list = data.map(d => {
        const a = d.address || {};
        const parts = [
          a.road && (a.road + (a.house_number?' '+a.house_number:'')),
          a.postcode,
          a.city || a.town || a.village || a.municipality
        ].filter(Boolean);
        return parts.length > 1 ? parts.join(', ') : d.display_name.split(',').slice(0,3).join(',').trim();
      }).filter(Boolean);
      setSuggs(list); setOpen(list.length > 0);
    } catch { setSuggs([]); setOpen(false); }
    setBusy(false);
  }

  return (
    <div ref={wrap} style={{position:'relative'}}>
      <div style={{position:'relative'}}>
        <input value={value} onChange={e=>handleChange(e.target.value)}
          onFocus={()=>suggs.length && setOpen(true)}
          placeholder="Adresse du chantier…"
          style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'8px 28px 8px 12px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'}} />
        <span style={{position:'absolute',right:9,top:'50%',transform:'translateY(-50%)',fontSize:12,color:'#94a3b8',cursor:value?'pointer':'default'}}
          onClick={()=>value&&onChange('')}>{busy?'⌛':value?'✕':''}</span>
      </div>
      {open && suggs.length>0 && (
        <div style={{position:'absolute',top:'100%',left:0,right:0,zIndex:900,background:'#fff',border:'1.5px solid #dde4ed',borderRadius:9,boxShadow:'0 8px 24px rgba(0,0,0,.12)',marginTop:3,maxHeight:200,overflowY:'auto'}}>
          {suggs.map((s,i)=>(
            <div key={i} onClick={()=>{onChange(s);setOpen(false);setSuggs([]);}}
              style={{padding:'8px 12px',cursor:'pointer',fontSize:12,color:'#334155',borderBottom:i<suggs.length-1?'1px solid #f0f4f8':'none',display:'flex',gap:6,alignItems:'flex-start'}}
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
function HistoryModal({onClose, onLoad}) {
  const [records, setRecords] = useState([]);
  useEffect(()=>{
    try { setRecords(JSON.parse(localStorage.getItem('pool_checklist_history')||'[]').reverse()); }
    catch { setRecords([]); }
  },[]);
  function del(i) {
    try {
      const s = JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
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
                    <div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{r.client||'Client non renseigné'}</div>
                    <div style={{fontSize:11,color:'#64748b'}}>{r.type} — {r.date||'—'}</div>
                    {r.address&&<div style={{fontSize:11,color:'#94a3b8',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.address}</div>}
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
   ProductPanel — recherche catalogue + IA fallback
═══════════════════════════════════════════════════ */
function ProductPanel({item, sectionLabel, onAdd, onClose}) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};
  const [q, setQ]         = useState(item||'');
  const [results, setRes] = useState([]);
  const [sel, setSel]     = useState({});
  const [busy, setBusy]   = useState(false);
  const [src, setSrc]     = useState(null);

  useEffect(()=>{ if(item) run(item); },[]);

  async function run(query) {
    setBusy(true); setRes([]); setSrc(null); setSel({});
    /* 1 — Odoo catalogue */
    try {
      const r = await fetch(cfg.productsEndpoint||'/pool-checklist/products',{
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{query,limit:15}})
      });
      const d = await r.json();
      const prods = d?.result?.products||[];
      if(prods.length){ setRes(prods); setSrc('odoo'); setBusy(false); return; }
    } catch {}
    /* 2 — IA proxy serveur */
    try {
      const r = await fetch(cfg.aiEndpoint||'/pool-checklist/ai-suggest',{
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{item_text:query,section_label:sectionLabel}})
      });
      const d = await r.json();
      const prods = d?.result?.products||[];
      setRes(prods); setSrc(prods.length?'ai':'empty');
    } catch { setSrc('empty'); }
    setBusy(false);
  }

  function toggle(i){ setSel(s=>({...s,[i]:!s[i]})); }
  function addSel(){
    const chosen = results.filter((_,i)=>sel[i]);
    if(chosen.length) onAdd(chosen);
  }
  const nSel = Object.values(sel).filter(Boolean).length;

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.5)',zIndex:9990,display:'flex',alignItems:'center',justifyContent:'center'}}>
      <div style={{background:'#fff',borderRadius:15,width:'min(660px,96vw)',maxHeight:'88vh',display:'flex',flexDirection:'column',boxShadow:'0 24px 80px rgba(0,0,0,.22)'}}>
        {/* header */}
        <div style={{padding:'16px 18px 10px',borderBottom:'1px solid #f0f4f8',display:'flex',gap:10,alignItems:'flex-start'}}>
          <div style={{flex:1}}>
            <div style={{fontWeight:700,fontSize:15,color:'#1e293b'}}>🔍 Produits associés</div>
            <div style={{fontSize:11,color:'#64748b',marginTop:2,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{item}</div>
          </div>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 11px',cursor:'pointer',fontSize:13,color:'#6b7a8d',flexShrink:0}}>✕</button>
        </div>
        {/* search */}
        <div style={{padding:'10px 18px',borderBottom:'1px solid #f0f4f8',display:'flex',gap:8}}>
          <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==='Enter'&&run(q)}
            placeholder="Référence, nom produit, marque…"
            style={{flex:1,border:'1.5px solid #dde4ed',borderRadius:8,padding:'7px 12px',fontFamily:'inherit',fontSize:13,outline:'none'}} />
          <button onClick={()=>run(q)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:8,padding:'7px 16px',fontWeight:600,cursor:'pointer',fontSize:13,whiteSpace:'nowrap'}}>
            {busy?'…':'Chercher'}
          </button>
        </div>
        {/* badge source */}
        {src && src!=='empty' && (
          <div style={{padding:'4px 18px',background:src==='odoo'?'#f0fdf4':'#fffbeb',borderBottom:'1px solid #f0f4f8'}}>
            <span style={{fontSize:11,fontWeight:700,padding:'2px 8px',borderRadius:20,background:src==='odoo'?'#dcfce7':'#fef3c7',color:src==='odoo'?'#166534':'#92400e'}}>
              {src==='odoo'?'✅ Catalogue Lolirine Pool Store':'✨ Suggestions IA (catalogue non accessible)'}
            </span>
          </div>
        )}
        {/* results */}
        <div style={{flex:1,overflowY:'auto',padding:'4px 18px'}}>
          {busy&&<div style={{padding:32,textAlign:'center',color:'#6b7a8d'}}><div style={{fontSize:26}}>🔄</div><div style={{fontSize:13,marginTop:8}}>Recherche…</div></div>}
          {!busy&&src==='empty'&&<div style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucun résultat.</div>}
          {!busy&&!src&&<div style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Lancez une recherche.</div>}
          {results.map((p,i)=>{
            const price = typeof p.price==='number'?p.price:(parseFloat(p.price)||0);
            const sup = p.suppliers?.[0]||{};
            return (
              <div key={i} onClick={()=>toggle(i)} style={{display:'flex',gap:10,padding:'8px 10px',margin:'3px 0',borderRadius:9,border:`1.5px solid ${sel[i]?'#0ea5e9':'#e8edf3'}`,background:sel[i]?'rgba(14,165,233,.05)':'#fff',cursor:'pointer',alignItems:'flex-start'}}>
                <div style={{width:17,height:17,border:`2px solid ${sel[i]?'#0ea5e9':'#bbb'}`,borderRadius:4,background:sel[i]?'#0ea5e9':'transparent',flexShrink:0,marginTop:2,display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',fontSize:11}}>
                  {sel[i]&&'✓'}
                </div>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{p.name}</div>
                  <div style={{fontSize:11,color:'#64748b',display:'flex',gap:9,flexWrap:'wrap',marginTop:2}}>
                    {p.ref&&<span>Réf: {p.ref}</span>}
                    {p.category&&<span>· {p.category}</span>}
                    {p.unit&&<span>· {p.unit}</span>}
                    {sup.name&&<span style={{color:'#7c3aed'}}>· {sup.name}</span>}
                    {price>0&&<span style={{color:'#16a34a',fontWeight:600}}>· {price.toFixed(2)} €</span>}
                  </div>
                  {p.note&&<div style={{fontSize:11,color:'#94a3b8',marginTop:2,fontStyle:'italic'}}>{p.note}</div>}
                </div>
              </div>
            );
          })}
        </div>
        {/* footer */}
        {results.length>0&&(
          <div style={{padding:'10px 18px',borderTop:'1px solid #f0f4f8',display:'flex',justifyContent:'flex-end',gap:9}}>
            <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:8,padding:'7px 16px',cursor:'pointer',fontSize:13,color:'#64748b'}}>Annuler</button>
            <button onClick={addSel} disabled={!nSel} style={{background:nSel?'#0ea5e9':'#cbd5e1',color:'#fff',border:'none',borderRadius:8,padding:'7px 18px',fontWeight:700,cursor:nSel?'pointer':'default',fontSize:13}}>
              Ajouter {nSel?`(${nSel})`:' la sélection'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SectionBlock — section checklist
   Item row : [checkbox] [✓OK] [⚠attention] [✗problème] texte [📷] [🛒] [Note]
═══════════════════════════════════════════════════ */
function SectionBlock({section, items, state, onSetState, onOpenProducts}) {
  const [open, setOpen]  = useState(true);
  const [notes, setNotes] = useState({});
  const done = items.filter((_,i)=>(state[i]||'')!=='').length;
  const pct  = items.length ? Math.round(done/items.length*100) : 0;

  return (
    <div style={{background:'#fff',borderRadius:13,border:'1.5px solid #e2e8f0',marginBottom:14,overflow:'hidden',boxShadow:'0 2px 6px rgba(0,0,0,.04)'}}>
      {/* header */}
      <div onClick={()=>setOpen(o=>!o)} style={{padding:'12px 16px',display:'flex',alignItems:'center',gap:10,cursor:'pointer',userSelect:'none',background:'#f8fafc'}}>
        <div style={{flex:1}}>
          <div style={{fontWeight:700,fontSize:14,color:'#1e293b'}}>{section}</div>
          <div style={{marginTop:4,height:4,background:'#e2e8f0',borderRadius:4,overflow:'hidden'}}>
            <div style={{height:'100%',background:pct===100?'#16a34a':'#0ea5e9',width:`${pct}%`,borderRadius:4,transition:'width .3s'}} />
          </div>
        </div>
        <span style={{fontSize:12,color:'#64748b',whiteSpace:'nowrap'}}>{done}/{items.length}</span>
        <span style={{fontSize:11,color:'#94a3b8'}}>{open?'▲':'▼'}</span>
      </div>
      {/* items */}
      {open && (
        <div style={{padding:'3px 0 6px'}}>
          {items.map((item,i)=>{
            const s = state[i]||'';
            return (
              <div key={i} style={{padding:'6px 14px',borderTop:'1px solid #f8fafc',display:'flex',alignItems:'center',gap:8,flexWrap:'nowrap'}}>
                {/* checkbox */}
                <input type="checkbox" checked={s!==''} onChange={()=>onSetState(i,s?'':null)}
                  style={{width:15,height:15,accentColor:'#0ea5e9',cursor:'pointer',flexShrink:0}} />
                {/* icônes statut */}
                <button title="OK / Conforme" onClick={()=>onSetState(i,'ok')}
                  style={{background:'none',border:'none',cursor:'pointer',fontSize:16,padding:'0 2px',opacity:s==='ok'?1:.3,transition:'opacity .15s'}}>✅</button>
                <button title="Attention / à surveiller" onClick={()=>onSetState(i,'warn')}
                  style={{background:'none',border:'none',cursor:'pointer',fontSize:16,padding:'0 2px',opacity:s==='warn'?1:.3,transition:'opacity .15s'}}>⚠️</button>
                <button title="Problème / non conforme" onClick={()=>onSetState(i,'bad')}
                  style={{background:'none',border:'none',cursor:'pointer',fontSize:16,padding:'0 2px',opacity:s==='bad'?1:.3,transition:'opacity .15s'}}>❌</button>
                {/* texte item */}
                <span style={{flex:1,fontSize:13,color:s?'#94a3b8':'#334155',textDecoration:s==='ok'?'line-through':'none',lineHeight:1.35}}>{item}</span>
                {/* bouton produits */}
                <button title="Produits associés" onClick={()=>onOpenProducts(item,section)}
                  style={{background:'none',border:'1px solid #e2e8f0',borderRadius:6,padding:'2px 6px',cursor:'pointer',fontSize:14,color:'#94a3b8',flexShrink:0,transition:'all .15s'}}
                  onMouseEnter={e=>{e.currentTarget.style.borderColor='#0ea5e9';e.currentTarget.style.color='#0ea5e9';}}
                  onMouseLeave={e=>{e.currentTarget.style.borderColor='#e2e8f0';e.currentTarget.style.color='#94a3b8';}}>🛒</button>
                {/* note inline */}
                <input value={notes[i]||''} onChange={e=>setNotes(n=>({...n,[i]:e.target.value}))}
                  placeholder="Note…"
                  style={{width:100,border:'1px solid #e8edf3',borderRadius:6,padding:'3px 7px',fontFamily:'inherit',fontSize:11,outline:'none',color:'#475569',background:'#fafafa',flexShrink:0}}
                  onClick={e=>e.stopPropagation()} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   QuoteModal — devis style Odoo
   Onglets : Lignes · Frais & services · Dropshipping · Notes
═══════════════════════════════════════════════════ */
const EVAC_OPT = [
  {key:'client',  label:'🤝 Évacuation client', price:0},
  {key:'forfait', label:'🚛 Forfait évacuation Lolirine', price:150},
  {key:'sans',    label:'— Sans évacuation', price:0},
];
const PAY_TERMS = ['Paiement à terme échu (30j)','Paiement comptant','Acompte 30%+solde livraison','Acompte 50%+solde livraison','Virement avant expédition'];
const FOURNISSEURS = ['Fluidra / SIBO','SCP Bénélux','HTH / BWT','Zodiac / Fluidra','Hayward','Astralpool','Pentair'];

function deplCost(km) {
  const n=Number(km)||0;
  if(n<=0) return 0;
  if(n<=30) return 50;
  return 50+Math.ceil((n-30)/25)*10;
}

function QuoteModal({products, client, clientId, address, refDossier, onClose, onCreated}) {
  const cfg = window.LOLIRINE_CHECKLIST_CONFIG || {};
  const [tab, setTab]   = useState('lines');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr]   = useState(null);

  /* Lignes */
  const [lines, setLines] = useState((products||[]).map(p=>({
    ...p, qty:p.qty||1, include:true,
    price_unit:typeof p.price==='number'?p.price:(parseFloat(p.price)||0), remise:0,
  })));

  /* Frais */
  const [evac, setEvac]       = useState('client');
  const [km, setKm]           = useState(0);
  const [kmAuto, setKmAuto]   = useState(true);
  const [kmMt, setKmMt]       = useState(0);
  const [inclDepl, setInclDepl] = useState(false);
  const [inclMO, setInclMO]   = useState(false);
  const [mo, setMo]           = useState(0);

  /* Dropship */
  const [fourn, setFourn]     = useState('Fluidra / SIBO');
  const [fournRef, setFournRef] = useState('');
  const [delai, setDelai]     = useState('5-10 jours ouvrés');
  const [livrDir, setLivrDir] = useState(true);
  const [livrAdr, setLivrAdr] = useState(address||'');
  const [cmdFourn, setCmdFourn] = useState('');

  /* Notes */
  const [noteInt, setNoteInt] = useState(address?'Chantier : '+address:'');
  const [cond, setCond]       = useState('');
  const [payTerm, setPayTerm] = useState(PAY_TERMS[0]);
  const [valid, setValid]     = useState(30);

  /* Géocodage adresse → km */
  useEffect(()=>{
    if(!address || Number(km)>0) return;
    let cancel=false;
    (async()=>{
      try {
        const r=await fetch('https://nominatim.openstreetmap.org/search?'+new URLSearchParams({q:address,countrycodes:'be,lu,fr,nl',format:'json',limit:'1'}),{mode:'cors',headers:{'Accept-Language':'fr'}});
        const d=await r.json();
        if(cancel||!d[0]) return;
        const lat2=parseFloat(d[0].lat),lon2=parseFloat(d[0].lon);
        const R=6371,dLat=(lat2-50.4875)*Math.PI/180,dLon=(lon2-4.9215)*Math.PI/180;
        const a=Math.sin(dLat/2)**2+Math.cos(50.4875*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
        const dist=Math.round(R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a))*1.3);
        if(!cancel&&dist>0){setKm(dist);setInclDepl(true);}
      } catch {}
    })();
    return ()=>{cancel=true;};
  },[address]);

  useEffect(()=>{if(kmAuto)setKmMt(deplCost(Number(km)));},[km,kmAuto]);

  /* Totaux */
  const tMat  = lines.filter(l=>l.include).reduce((a,l)=>a+(l.price_unit||0)*(l.qty||1)*(1-(l.remise||0)/100),0);
  const tDepl = inclDepl?(kmAuto?deplCost(Number(km)):(Number(kmMt)||0)):0;
  const tEvac = evac!=='sans'?(EVAC_OPT.find(o=>o.key===evac)?.price||0):0;
  const tMO   = inclMO?(Number(mo)||0):0;
  const sHT   = tMat+tDepl+tEvac+tMO;
  const tva   = sHT*0.21;
  const tTTC  = sHT+tva;

  function toggleLine(i){setLines(ls=>ls.map((l,x)=>x===i?{...l,include:!l.include}:l));}
  function updQty(i,d){setLines(ls=>ls.map((l,x)=>x===i?{...l,qty:Math.max(1,(l.qty||1)+d)}:l));}
  function updP(i,v){setLines(ls=>ls.map((l,x)=>x===i?{...l,price_unit:parseFloat(v)||0}:l));}
  function updR(i,v){setLines(ls=>ls.map((l,x)=>x===i?{...l,remise:Math.min(100,Math.max(0,parseFloat(v)||0))}:l));}
  function delLine(i){setLines(ls=>ls.filter((_,x)=>x!==i));}

  async function doCreate(){
    setBusy(true); setErr(null);
    const allLines=[
      ...lines.filter(l=>l.include).map(l=>({product_id:l.id||null,name:l.name,product_uom_qty:l.qty,price_unit:l.price_unit||0,discount:l.remise||0,default_code:l.ref||''})),
      ...(tDepl>0?[{product_id:null,name:`Frais déplacement (${km}km)`,product_uom_qty:1,price_unit:tDepl,discount:0,default_code:''}]:[]),
      ...(tEvac>0?[{product_id:null,name:EVAC_OPT.find(o=>o.key===evac)?.label||'Évacuation',product_uom_qty:1,price_unit:tEvac,discount:0,default_code:''}]:[]),
      ...(tMO>0?[{product_id:null,name:'Main d\'œuvre technicien',product_uom_qty:1,price_unit:tMO,discount:0,default_code:''}]:[]),
    ];
    if(!allLines.length){setErr('Aucune ligne.');setBusy(false);return;}
    try {
      const r=await fetch(cfg.quoteEndpoint||'/pool-checklist/create-quote',{
        method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({jsonrpc:'2.0',method:'call',id:1,params:{
          partner_id:clientId||null,partner_name:client||'',ref_dossier:refDossier||'',payment_term:payTerm,
          note:[noteInt,cond,livrDir?'Livraison chantier : '+livrAdr:'',cmdFourn?'BC fourn: '+cmdFourn:'',fournRef?'Réf fourn: '+fournRef:''].filter(Boolean).join('\n'),
          lines:allLines,
        }})
      });
      const d=await r.json();
      if(d?.result?.error){setErr(d.result.error);setBusy(false);return;}
      setResult(d?.result||{});
      if(onCreated)onCreated(d?.result);
    } catch(e){setErr(e.message);}
    setBusy(false);
  }

  if(result) return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center'}}>
      <div style={{background:'#fff',borderRadius:16,padding:32,width:'min(460px,92vw)',textAlign:'center',boxShadow:'0 24px 80px rgba(0,0,0,.25)'}}>
        <div style={{fontSize:48,marginBottom:10}}>✅</div>
        <div style={{fontWeight:800,fontSize:19,color:'#1e293b',marginBottom:4}}>Devis créé !</div>
        {result.name&&<div style={{fontSize:17,color:'#0ea5e9',fontWeight:700,marginBottom:4}}>{result.name}</div>}
        {result.partner_name&&<div style={{fontSize:13,color:'#64748b',marginBottom:18}}>Client : {result.partner_name}</div>}
        <div style={{display:'flex',gap:9,justifyContent:'center',flexWrap:'wrap'}}>
          {result.url&&<a href={result.url} target='_blank' rel='noreferrer' style={{background:'#0ea5e9',color:'#fff',borderRadius:9,padding:'9px 20px',fontWeight:700,fontSize:13,textDecoration:'none'}}>Ouvrir →</a>}
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'9px 20px',fontWeight:600,fontSize:13,cursor:'pointer',color:'#475569'}}>Fermer</button>
        </div>
      </div>
    </div>
  );

  const IS = {width:'100%',border:'1.5px solid #dde4ed',borderRadius:7,padding:'6px 10px',fontFamily:'inherit',fontSize:12,outline:'none',boxSizing:'border-box'};
  const LB = {fontSize:11,fontWeight:700,color:'#64748b',textTransform:'uppercase',letterSpacing:'.4px',display:'block',marginBottom:3};
  const TABS=[{k:'lines',lbl:'📦 Lignes',badge:lines.filter(l=>l.include).length},{k:'services',lbl:'🔧 Frais & services'},{k:'dropship',lbl:'🚚 Dropshipping'},{k:'notes',lbl:'📝 Notes'}];

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(15,23,42,.6)',zIndex:9995,display:'flex',alignItems:'center',justifyContent:'center',padding:8}}>
      <div style={{background:'#f1f5f9',borderRadius:15,width:'min(940px,100%)',maxHeight:'95vh',display:'flex',flexDirection:'column',boxShadow:'0 28px 90px rgba(0,0,0,.28)',overflow:'hidden'}}>

        {/* barre titre */}
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',padding:'11px 18px',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:16,color:'#1e293b'}}>📄 Nouveau devis — Lolirine Pool Store</div>
            <div style={{fontSize:12,color:'#64748b',marginTop:1}}>
              {client&&<span style={{fontWeight:600,color:'#0ea5e9'}}>{client}</span>}
              {address&&<span style={{color:'#94a3b8'}}> · {address.split(',')[0]}</span>}
              {refDossier&&<span style={{color:'#7c3aed'}}> · {refDossier}</span>}
            </div>
          </div>
          <span style={{background:'#f0fdf4',border:'1.5px solid #bbf7d0',borderRadius:20,padding:'3px 11px',fontSize:12,fontWeight:700,color:'#16a34a',flexShrink:0}}>Brouillon</span>
          <button onClick={onClose} style={{background:'none',border:'1.5px solid #dde4ed',borderRadius:7,padding:'4px 12px',cursor:'pointer',fontSize:13,color:'#6b7a8d',flexShrink:0}}>✕</button>
        </div>

        {/* fiche client */}
        <div style={{background:'#fff',borderBottom:'1px solid #e8edf3',padding:'11px 18px',display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))',gap:10,flexShrink:0}}>
          <div><label style={LB}>Client</label><div style={{fontWeight:600,fontSize:13,color:'#1e293b'}}>{client||'—'}</div>{address&&<div style={{fontSize:11,color:'#64748b'}}>{address}</div>}</div>
          <div><label style={LB}>Référence dossier</label><div style={{fontSize:13,color:'#7c3aed',fontWeight:600}}>{refDossier||'—'}</div></div>
          <div><label style={LB}>Date</label><div style={{fontSize:13,color:'#1e293b'}}>{new Date().toLocaleDateString('fr-BE')}</div></div>
          <div><label style={LB}>Validité (jours)</label><input type="number" value={valid} min={1} onChange={e=>setValid(e.target.value)} style={{...IS,width:70}} /></div>
          <div><label style={LB}>Conditions paiement</label><select value={payTerm} onChange={e=>setPayTerm(e.target.value)} style={{...IS,background:'#fff'}}>{PAY_TERMS.map(t=><option key={t}>{t}</option>)}</select></div>
          <div><label style={LB}>TVA</label><div style={{fontSize:13,fontWeight:600,color:'#475569'}}>21 % (BE)</div></div>
        </div>

        {/* onglets */}
        <div style={{background:'#fff',borderBottom:'2px solid #e2e8f0',display:'flex',flexShrink:0,overflowX:'auto'}}>
          {TABS.map(t=>(
            <button key={t.k} onClick={()=>setTab(t.k)}
              style={{padding:'9px 17px',border:'none',borderBottom:`3px solid ${tab===t.k?'#0ea5e9':'transparent'}`,background:'transparent',cursor:'pointer',fontWeight:tab===t.k?700:500,fontSize:13,color:tab===t.k?'#0ea5e9':'#64748b',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5}}>
              {t.lbl}{t.badge!=null&&<span style={{background:tab===t.k?'#0ea5e9':'#e2e8f0',color:tab===t.k?'#fff':'#64748b',borderRadius:20,padding:'1px 6px',fontSize:11,fontWeight:700}}>{t.badge}</span>}
            </button>
          ))}
        </div>

        {/* corps */}
        <div style={{flex:1,overflowY:'auto'}}>

          {/* ── Lignes ── */}
          {tab==='lines'&&(
            <div>
              <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
                <thead style={{background:'#f8fafc',position:'sticky',top:0,zIndex:1}}>
                  <tr style={{borderBottom:'2px solid #e2e8f0'}}>
                    {['','Produit','Fourn.','Réf.','Qté','Prix HT','Rem%','Total HT',''].map((h,i)=><th key={i} style={{padding:'8px 9px',textAlign:'left',fontWeight:700,color:'#64748b',fontSize:11,whiteSpace:'nowrap'}}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {lines.map((l,i)=>{
                    const sup=l.suppliers?.[0]||{};
                    const mt=(l.price_unit||0)*(l.qty||1)*(1-(l.remise||0)/100);
                    return <tr key={i} style={{borderBottom:'1px solid #f1f5f9',background:l.include?'#fff':'#f8fafc',opacity:l.include?1:.5}}>
                      <td style={{padding:'7px 9px',width:22}}><input type="checkbox" checked={!!l.include} onChange={()=>toggleLine(i)} style={{accentColor:'#0ea5e9',width:14,height:14,cursor:'pointer'}} /></td>
                      <td style={{padding:'7px 9px',minWidth:160}}><div style={{fontWeight:600,color:'#1e293b',fontSize:13}}>{l.name}</div>{l.ref&&<div style={{fontSize:11,color:'#94a3b8'}}>Réf: {l.ref}</div>}{l.category&&<div style={{fontSize:11,color:'#7c3aed'}}>{l.category}</div>}</td>
                      <td style={{padding:'7px 9px',fontSize:12,color:'#7c3aed',whiteSpace:'nowrap'}}>{sup.name||'—'}</td>
                      <td style={{padding:'7px 9px',fontSize:12,color:'#64748b'}}>{sup.ref||l.ref||'—'}</td>
                      <td style={{padding:'7px 9px'}}><div style={{display:'flex',alignItems:'center',gap:3}}><button onClick={()=>updQty(i,-1)} style={{width:20,height:20,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:12}}>−</button><span style={{fontWeight:700,minWidth:20,textAlign:'center'}}>{l.qty}</span><button onClick={()=>updQty(i,+1)} style={{width:20,height:20,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:12}}>+</button></div></td>
                      <td style={{padding:'7px 9px',width:85}}><input type="number" value={l.price_unit} min={0} step={0.01} onChange={e=>updP(i,e.target.value)} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:6,padding:'3px 6px',fontFamily:'inherit',fontSize:12,textAlign:'right',outline:'none'}} /></td>
                      <td style={{padding:'7px 9px',width:60}}><input type="number" value={l.remise||0} min={0} max={100} onChange={e=>updR(i,e.target.value)} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:6,padding:'3px 6px',fontFamily:'inherit',fontSize:12,textAlign:'right',outline:'none'}} /></td>
                      <td style={{padding:'7px 9px',fontWeight:700,color:'#0369a1',textAlign:'right',whiteSpace:'nowrap'}}>{mt>0?mt.toFixed(2)+' €':'—'}</td>
                      <td style={{padding:'7px 9px'}}><button onClick={()=>delLine(i)} style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',fontSize:13}}>✕</button></td>
                    </tr>;
                  })}
                  {lines.length===0&&<tr><td colSpan={9} style={{padding:28,textAlign:'center',color:'#94a3b8',fontSize:13}}>Aucun produit. Ajoutez des articles depuis la fiche.</td></tr>}
                </tbody>
              </table>
              <div style={{padding:'10px 16px',background:'#f8fafc',borderTop:'1px solid #e2e8f0',textAlign:'right',fontSize:13,color:'#64748b'}}>
                Sous-total matériaux HT : <strong style={{color:'#0369a1'}}>{tMat.toFixed(2)} €</strong>
              </div>
            </div>
          )}

          {/* ── Frais & services ── */}
          {tab==='services'&&(
            <div style={{padding:18,display:'flex',flexDirection:'column',gap:16}}>
              {/* évacuation */}
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
                <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:10}}>🗑️ Évacuation déchets</div>
                {EVAC_OPT.map(o=>(
                  <label key={o.key} style={{display:'flex',alignItems:'center',gap:9,padding:'8px 12px',borderRadius:9,border:`2px solid ${evac===o.key?'#0ea5e9':'#e8edf3'}`,background:evac===o.key?'#eff9ff':'#fff',cursor:'pointer',marginBottom:6}}>
                    <input type="radio" name="evac" value={o.key} checked={evac===o.key} onChange={()=>setEvac(o.key)} style={{accentColor:'#0ea5e9',width:15,height:15}} />
                    <span style={{flex:1,fontSize:13,fontWeight:evac===o.key?600:400,color:evac===o.key?'#0369a1':'#334155'}}>{o.label}</span>
                    {o.price>0&&<span style={{fontWeight:700,color:'#0369a1',fontSize:14}}>{o.price} €</span>}
                  </label>
                ))}
              </div>
              {/* déplacement */}
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
                <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
                  <input type="checkbox" checked={inclDepl} onChange={e=>setInclDepl(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15,cursor:'pointer'}} />
                  <span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>🚗 Frais de déplacement</span>
                  <span style={{fontSize:11,color:'#94a3b8',fontStyle:'italic'}}>depuis Namur · ≤30km=50€ · +10€/25km</span>
                </div>
                <div style={{display:'flex',gap:14,alignItems:'flex-end',flexWrap:'wrap'}}>
                  <div><label style={LB}>Distance (km)</label>
                    <div style={{display:'flex',alignItems:'center',gap:5}}>
                      <button onClick={()=>setKm(Math.max(0,Number(km)-5))} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>−</button>
                      <input type="number" value={km} min={0} onChange={e=>setKm(e.target.value)} style={{width:65,...IS,textAlign:'center',padding:'4px 7px'}} />
                      <button onClick={()=>setKm(Number(km)+5)} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>+</button>
                    </div>
                  </div>
                  <div><label style={LB}>Montant HT (€) &nbsp;<label style={{fontWeight:400}}><input type="checkbox" checked={kmAuto} onChange={e=>setKmAuto(e.target.checked)} style={{accentColor:'#0ea5e9',marginRight:3}} />Auto</label></label>
                    <input type="number" value={kmAuto?deplCost(Number(km)):kmMt} readOnly={kmAuto} min={0} onChange={e=>!kmAuto&&setKmMt(e.target.value)} style={{width:85,...IS,textAlign:'center',padding:'4px 7px',background:kmAuto?'#f8fafc':'#fff'}} />
                  </div>
                  <div style={{fontSize:12,color:'#64748b',paddingBottom:4}}>
                    {address&&<div>📍 {address.split(',')[0]}</div>}
                    {Number(km)>0&&<div style={{color:'#0ea5e9',fontWeight:600,marginTop:2}}>Barème : {deplCost(Number(km))} €</div>}
                  </div>
                </div>
              </div>
              {/* main d'œuvre */}
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
                <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
                  <input type="checkbox" checked={inclMO} onChange={e=>setInclMO(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15,cursor:'pointer'}} />
                  <span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>🔨 Main d'œuvre technicien</span>
                </div>
                <div style={{display:'flex',gap:9,alignItems:'center',flexWrap:'wrap'}}>
                  <button onClick={()=>setMo(Math.max(0,(Number(mo)||0)-50))} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>−</button>
                  <input type="number" value={mo} min={0} step={50} onChange={e=>setMo(e.target.value)} style={{width:95,...IS,textAlign:'center',fontSize:15,fontWeight:700,padding:'5px 9px'}} />
                  <span style={{fontSize:13,color:'#475569'}}>€ HT</span>
                  <button onClick={()=>setMo((Number(mo)||0)+50)} style={{width:26,height:26,border:'1px solid #e2e8f0',borderRadius:5,background:'#f8fafc',cursor:'pointer',fontSize:14}}>+</button>
                  {[0,500,750,1000,1500,2000].map(v=><button key={v} onClick={()=>setMo(v)} style={{padding:'3px 8px',borderRadius:6,border:`1px solid ${mo==v?'#0ea5e9':'#e2e8f0'}`,background:mo==v?'#eff9ff':'#f8fafc',color:mo==v?'#0369a1':'#64748b',fontSize:11,cursor:'pointer',fontWeight:mo==v?700:400}}>{v===0?'—':v+'€'}</button>)}
                </div>
              </div>
            </div>
          )}

          {/* ── Dropshipping ── */}
          {tab==='dropship'&&(
            <div style={{padding:18,display:'flex',flexDirection:'column',gap:14}}>
              <div style={{background:'#fffbeb',border:'1.5px solid #fde68a',borderRadius:11,padding:'10px 14px',fontSize:13,color:'#92400e'}}>
                ⚡ En dropshipping, la commande fournisseur est transmise après validation du devis. La livraison peut être directe chantier.
              </div>
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'16px',display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
                <div><label style={LB}>Fournisseur principal</label><select value={fourn} onChange={e=>setFourn(e.target.value)} style={{...IS,background:'#fff'}}>{FOURNISSEURS.map(s=><option key={s}>{s}</option>)}</select></div>
                <div><label style={LB}>Réf. commande fournisseur</label><input value={cmdFourn} onChange={e=>setCmdFourn(e.target.value)} placeholder="BC-FOURN-2025-XXX" style={IS} /></div>
                <div><label style={LB}>Réf. produit fournisseur</label><input value={fournRef} onChange={e=>setFournRef(e.target.value)} placeholder="ex: FLU-PMP-00312" style={IS} /></div>
                <div><label style={LB}>Délai de livraison estimé</label><input value={delai} onChange={e=>setDelai(e.target.value)} style={IS} /></div>
              </div>
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'16px'}}>
                <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
                  <input type="checkbox" checked={livrDir} onChange={e=>setLivrDir(e.target.checked)} style={{accentColor:'#0ea5e9',width:15,height:15}} />
                  <span style={{fontWeight:700,fontSize:13,color:'#1e293b'}}>📍 Livraison directe sur chantier</span>
                </div>
                {livrDir ? <div><label style={LB}>Adresse de livraison</label><input value={livrAdr} onChange={e=>setLivrAdr(e.target.value)} placeholder="Adresse complète…" style={IS} /></div>
                  : <div style={{fontSize:13,color:'#64748b'}}>📦 Livraison à l'entrepôt Lolirine — retrait technicien</div>}
              </div>
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',overflow:'hidden'}}>
                <div style={{background:'#f8fafc',padding:'9px 14px',borderBottom:'1px solid #e2e8f0',fontWeight:700,fontSize:12,color:'#1e293b'}}>
                  📦 Articles à commander ({lines.filter(l=>l.include).length})
                </div>
                <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
                  <thead><tr style={{borderBottom:'1px solid #f0f4f8'}}>{['Désignation','Réf.','Fourn.','Qté','Px achat'].map((h,i)=><th key={i} style={{padding:'6px 11px',textAlign:'left',fontWeight:600,color:'#64748b',fontSize:11}}>{h}</th>)}</tr></thead>
                  <tbody>{lines.filter(l=>l.include).map((l,i)=>{const sup=l.suppliers?.[0]||{};return <tr key={i} style={{borderBottom:'1px solid #f8fafc'}}><td style={{padding:'7px 11px',fontWeight:500,color:'#1e293b'}}>{l.name}</td><td style={{padding:'7px 11px',color:'#64748b',fontSize:11}}>{l.ref||'—'}</td><td style={{padding:'7px 11px',color:'#7c3aed',fontSize:11}}>{sup.name||fourn}</td><td style={{padding:'7px 11px',fontWeight:700}}>{l.qty}</td><td style={{padding:'7px 11px',color:'#16a34a',fontWeight:600}}>{sup.price>0?(sup.price*l.qty).toFixed(2)+' €':'—'}</td></tr>;})}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Notes ── */}
          {tab==='notes'&&(
            <div style={{padding:18,display:'flex',flexDirection:'column',gap:12}}>
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
                <label style={LB}>Notes internes / chantier</label>
                <textarea value={noteInt} onChange={e=>setNoteInt(e.target.value)} rows={4} placeholder="Observations de la visite, accès, remarques techniques…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'9px 12px',fontFamily:'inherit',fontSize:12,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} />
              </div>
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
                <label style={LB}>Conditions particulières</label>
                <textarea value={cond} onChange={e=>setCond(e.target.value)} rows={3} placeholder="Garanties, délais, restrictions…" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'9px 12px',fontFamily:'inherit',fontSize:12,outline:'none',resize:'vertical',lineHeight:1.5,boxSizing:'border-box'}} />
              </div>
              <div style={{background:'#fff',borderRadius:11,border:'1.5px solid #e2e8f0',padding:'14px 16px'}}>
                <label style={LB}>Conditions de paiement</label>
                <select value={payTerm} onChange={e=>setPayTerm(e.target.value)} style={{...IS,background:'#fff'}}>{PAY_TERMS.map(t=><option key={t}>{t}</option>)}</select>
              </div>
            </div>
          )}
        </div>

        {/* footer totaux */}
        <div style={{background:'#fff',borderTop:'2px solid #e2e8f0',flexShrink:0,display:'flex',flexWrap:'wrap'}}>
          <div style={{flex:1,padding:'12px 18px',minWidth:240}}>
            <table style={{width:'100%',fontSize:13}}>
              <tbody>
                {tMat>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Matériaux HT</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tMat.toFixed(2)} €</td></tr>}
                {tDepl>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Déplacement ({km}km)</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tDepl.toFixed(2)} €</td></tr>}
                {tEvac>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Évacuation</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tEvac.toFixed(2)} €</td></tr>}
                {tMO>0&&<tr><td style={{color:'#64748b',padding:'2px 0'}}>Main d'œuvre</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tMO.toFixed(2)} €</td></tr>}
                <tr style={{borderTop:'1px solid #f0f4f8'}}><td style={{color:'#64748b',padding:'5px 0 2px',fontWeight:600}}>Montant HT</td><td style={{textAlign:'right',fontWeight:700,color:'#1e293b',fontSize:14}}>{sHT.toFixed(2)} €</td></tr>
                <tr><td style={{color:'#64748b',padding:'2px 0'}}>TVA 21%</td><td style={{textAlign:'right',fontWeight:600,color:'#1e293b'}}>{tva.toFixed(2)} €</td></tr>
                <tr style={{borderTop:'2px solid #0ea5e9'}}><td style={{fontWeight:800,fontSize:15,color:'#0ea5e9',padding:'5px 0 0'}}>Total TTC</td><td style={{textAlign:'right',fontWeight:800,fontSize:16,color:'#0ea5e9'}}>{tTTC.toFixed(2)} €</td></tr>
              </tbody>
            </table>
          </div>
          <div style={{padding:'12px 18px',display:'flex',flexDirection:'column',gap:8,justifyContent:'center',minWidth:190,alignItems:'stretch'}}>
            {err&&<div style={{color:'#ef4444',fontSize:12,textAlign:'center'}}>{err}</div>}
            <button onClick={doCreate} disabled={busy} style={{background:busy?'#cbd5e1':'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'10px 22px',fontWeight:700,fontSize:14,cursor:busy?'wait':'pointer',whiteSpace:'nowrap'}}>
              {busy?'⏳ Création…':'📄 Créer le devis Odoo'}
            </button>
            <button onClick={onClose} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'8px 22px',fontWeight:600,fontSize:13,cursor:'pointer',color:'#475569'}}>← Annuler</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   PoolChecklist — composant principal
   Layout linéaire + panneau devis en modal
═══════════════════════════════════════════════════ */
function PoolChecklist() {
  const [type,    setType]    = useState('entretien');
  const [client,  setClient]  = useState('');
  const [clientId,setClientId]= useState(null);
  const [address, setAddress] = useState('');
  const [tech,    setTech]    = useState('');
  const [date,    setDate]    = useState(new Date().toISOString().split('T')[0]);
  const [ref,     setRef]     = useState('');
  const [obs,     setObs]     = useState('');
  const [itemState,setItemState] = useState({});  /* {`${si}_${ii}` : 'ok'|'warn'|'bad'} */
  const [products, setProducts] = useState([]);
  const [panel,    setPanel]   = useState(null);
  const [showHistory,setShowHistory] = useState(false);
  const [showQuote,  setShowQuote]   = useState(false);
  const [saved,      setSaved]       = useState(false);
  const [statut,     setStatut]      = useState('en_cours');
  const [signClient, setSignClient]  = useState('');
  const [signTech,   setSignTech]    = useState('');

  const sections   = SECTIONS_DATA[type] || [];
  const totalItems = sections.reduce((a,s)=>a+s.items.length,0);
  const totalDone  = sections.reduce((a,s,si)=>a+s.items.filter((_,ii)=>!!itemState[`${si}_${ii}`]).length,0);
  const pct = totalItems ? Math.round(totalDone/totalItems*100) : 0;
  const totalHT = products.reduce((a,p)=>{const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);return a+price*(p.qty||1);},0);

  function setItemSt(si,ii,val) {
    const k=`${si}_${ii}`;
    setItemState(st=>({...st,[k]:val===null?undefined:val}));
  }

  function handleAddProducts(newProds) {
    setProducts(ps=>{const ex=new Set(ps.map(p=>p.ref||p.name));const toAdd=newProds.filter(p=>!ex.has(p.ref||p.name));return[...ps,...toAdd.map(p=>({...p,qty:1}))];});
    setPanel(null);
  }

  function updateQty(i,d){setProducts(ps=>ps.map((p,x)=>x===i?{...p,qty:Math.max(0,(p.qty||1)+d)}:p).filter(p=>p.qty>0));}
  function removeProd(i){setProducts(ps=>ps.filter((_,x)=>x!==i));}

  function saveToHistory(){
    try{
      const s=JSON.parse(localStorage.getItem('pool_checklist_history')||'[]');
      s.push({client,address,tech,date,ref,type,obs,itemState,products,statut,signClient,signTech,savedAt:new Date().toISOString()});
      localStorage.setItem('pool_checklist_history',JSON.stringify(s.slice(-50)));
      setSaved(true); setTimeout(()=>setSaved(false),2500);
    }catch(e){alert('Erreur: '+e.message);}
  }

  function loadRecord(r){
    setType(r.type||'entretien');
    setClient(r.client||''); setClientId(null); setAddress(r.address||''); setTech(r.tech||'');
    setDate(r.date||''); setRef(r.ref||''); setObs(r.obs||'');
    setItemState(r.itemState||{}); setProducts(r.products||[]);
    setStatut(r.statut||'en_cours'); setSignClient(r.signClient||''); setSignTech(r.signTech||'');
  }

  function reset(){if(!confirm('Réinitialiser toute la fiche ?'))return;setType('entretien');setClient('');setClientId(null);setAddress('');setTech('');setDate(new Date().toISOString().split('T')[0]);setRef('');setObs('');setItemState({});setProducts([]);setStatut('en_cours');setSignClient('');setSignTech('');}

  return (
    <div style={{fontFamily:"'Inter','Segoe UI',system-ui,sans-serif",background:'#f1f5f9',minHeight:'100vh'}}>

      {/* ── Barre top ── */}
      <div style={{background:'#0ea5e9',color:'#fff',padding:'11px 18px',display:'flex',alignItems:'center',gap:10,flexWrap:'wrap'}}>
        <div style={{flex:1}}>
          <div style={{fontWeight:800,fontSize:18,letterSpacing:'-.5px'}}>📋 Fiche de visite chantier</div>
          <div style={{fontSize:11,opacity:.8}}>Lolirine Pool Store</div>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:6,background:'rgba(255,255,255,.15)',borderRadius:9,padding:'4px 11px'}}>
          <div style={{width:72,height:4,background:'rgba(255,255,255,.3)',borderRadius:4,overflow:'hidden'}}><div style={{height:'100%',background:pct===100?'#4ade80':'#fff',width:`${pct}%`,borderRadius:4,transition:'width .3s'}} /></div>
          <span style={{fontSize:12,fontWeight:700}}>{pct}%</span>
        </div>
        <button onClick={()=>setShowHistory(true)} style={{background:'rgba(255,255,255,.18)',color:'#fff',border:'1.5px solid rgba(255,255,255,.4)',borderRadius:8,padding:'6px 12px',cursor:'pointer',fontWeight:600,fontSize:12}}>📁 Historique</button>
        <button onClick={saveToHistory} style={{background:saved?'rgba(74,222,128,.7)':'rgba(255,255,255,.15)',color:'#fff',border:'1.5px solid rgba(255,255,255,.4)',borderRadius:8,padding:'6px 12px',cursor:'pointer',fontWeight:600,fontSize:12,transition:'background .3s'}}>{saved?'✅ Sauvegardé !':'💾 Sauvegarder'}</button>
        <button onClick={()=>window.print()} style={{background:'rgba(255,255,255,.15)',color:'#fff',border:'1.5px solid rgba(255,255,255,.4)',borderRadius:8,padding:'6px 12px',cursor:'pointer',fontWeight:600,fontSize:12}}>🖨️ PDF</button>
        <button onClick={reset} style={{background:'rgba(255,255,255,.08)',color:'rgba(255,255,255,.75)',border:'1px solid rgba(255,255,255,.25)',borderRadius:8,padding:'6px 10px',cursor:'pointer',fontSize:11}}>↺</button>
      </div>

      {/* ── Barre progression ── */}
      <div style={{background:'#fff',padding:'8px 18px',borderBottom:'1px solid #e2e8f0',display:'flex',alignItems:'center',gap:12}}>
        <div style={{flex:1,height:6,background:'#e2e8f0',borderRadius:6,overflow:'hidden'}}>
          <div style={{height:'100%',background:pct===100?'#16a34a':'#0ea5e9',width:`${pct}%`,borderRadius:6,transition:'width .4s'}} />
        </div>
        <span style={{fontSize:12,fontWeight:700,color:pct===100?'#16a34a':'#0ea5e9',whiteSpace:'nowrap'}}>{totalDone}/{totalItems} · {pct}%</span>
      </div>

      <div style={{maxWidth:1000,margin:'0 auto',padding:'18px 12px'}}>

        {/* Type d'intervention */}
        <div style={{background:'#fff',borderRadius:13,padding:'14px 16px',marginBottom:14,border:'1.5px solid #e2e8f0'}}>
          <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:9}}>Type d'intervention</div>
          <div style={{display:'flex',flexWrap:'wrap',gap:7}}>
            {INTERVENTION_TYPES.map(t=>(
              <button key={t.key} onClick={()=>{setType(t.key);setItemState({});}}
                style={{padding:'6px 13px',borderRadius:9,border:`2px solid ${type===t.key?'#0ea5e9':'#e2e8f0'}`,background:type===t.key?'#eff9ff':'#fff',color:type===t.key?'#0369a1':'#475569',fontWeight:type===t.key?700:500,fontSize:12,cursor:'pointer',transition:'all .15s'}}>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Infos client */}
        <div style={{background:'#fff',borderRadius:13,padding:'14px 16px',marginBottom:14,border:'1.5px solid #e2e8f0'}}>
          <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:11}}>Informations client</div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(190px,1fr))',gap:10}}>
            <div><label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:3}}>Client *</label><ClientAutocomplete value={client} onChange={setClient} onSelectId={setClientId} /></div>
            <div><label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:3}}>Adresse chantier</label><AddressAutocomplete value={address} onChange={setAddress} /></div>
            <div><label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:3}}>Technicien</label><input value={tech} onChange={e=>setTech(e.target.value)} placeholder="Prénom Nom" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'8px 12px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'}} /></div>
            <div><label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:3}}>Date</label><input type="date" value={date} onChange={e=>setDate(e.target.value)} style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'8px 12px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'}} /></div>
            <div><label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:3}}>Référence dossier</label><input value={ref} onChange={e=>setRef(e.target.value)} placeholder="ex : CHT-2025-042" style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'8px 12px',fontFamily:'inherit',fontSize:13,outline:'none',boxSizing:'border-box'}} /></div>
          </div>
        </div>

        {/* Sections checklist */}
        {sections.map((s,si)=>(
          <SectionBlock key={`${type}-${si}`} section={s.section} items={s.items}
            state={Object.fromEntries(s.items.map((_,ii)=>[ii,itemState[`${si}_${ii}`]||'']))}
            onSetState={(ii,val)=>setItemSt(si,ii,val)}
            onOpenProducts={(item,sec)=>setPanel({item,sectionLabel:sec})} />
        ))}

        {/* Remarques générales */}
        <div style={{background:'#fff',borderRadius:13,padding:'14px 16px',marginBottom:14,border:'1.5px solid #e2e8f0'}}>
          <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:8}}>📝 Remarques générales</div>
          <textarea value={obs} onChange={e=>setObs(e.target.value)}
            placeholder="Observations générales, conditions d'accès, points particuliers à noter…"
            style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:9,padding:'10px 12px',fontFamily:'inherit',fontSize:13,outline:'none',resize:'vertical',minHeight:88,boxSizing:'border-box',lineHeight:1.5}} />
        </div>

        {/* Matériaux sélectionnés */}
        {products.length>0&&(
          <div style={{background:'#fff',borderRadius:13,padding:'14px 16px',marginBottom:14,border:'1.5px solid #e2e8f0'}}>
            <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:11,flexWrap:'wrap'}}>
              <div style={{fontWeight:700,fontSize:13,color:'#1e293b',flex:1}}>🛒 Matériaux & produits ({products.length})</div>
              <button onClick={()=>setShowQuote(true)} style={{background:'#0ea5e9',color:'#fff',border:'none',borderRadius:8,padding:'6px 14px',fontWeight:700,fontSize:12,cursor:'pointer'}}>📄 Créer un devis</button>
            </div>
            <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
              <thead><tr style={{borderBottom:'2px solid #f0f4f8'}}>{['Désignation','Fourn.','Unité','Qté','Total HT',''].map((h,i)=><th key={i} style={{textAlign:'left',padding:'5px 7px',fontWeight:600,color:'#64748b',fontSize:11}}>{h}</th>)}</tr></thead>
              <tbody>
                {products.map((p,i)=>{
                  const price=typeof p.price==='number'?p.price:(parseFloat(p.price)||0);
                  const sup=p.suppliers?.[0]||{};
                  return <tr key={i} style={{borderBottom:'1px solid #f8fafc'}}>
                    <td style={{padding:'6px 7px',fontWeight:500,color:'#1e293b'}}>{p.name}</td>
                    <td style={{padding:'6px 7px',color:'#7c3aed',fontSize:11}}>{sup.name||p.category||'—'}</td>
                    <td style={{padding:'6px 7px',color:'#64748b',fontSize:11}}>{p.unit||'pcs'}</td>
                    <td style={{padding:'6px 7px'}}><div style={{display:'flex',alignItems:'center',gap:3}}><button onClick={()=>updateQty(i,-1)} style={{width:19,height:19,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:11}}>−</button><span style={{fontWeight:700,minWidth:18,textAlign:'center'}}>{p.qty||1}</span><button onClick={()=>updateQty(i,+1)} style={{width:19,height:19,border:'1px solid #e2e8f0',borderRadius:4,background:'#f8fafc',cursor:'pointer',fontSize:11}}>+</button></div></td>
                    <td style={{padding:'6px 7px',color:'#0369a1',fontWeight:700,whiteSpace:'nowrap'}}>{price>0?(price*(p.qty||1)).toFixed(2)+' €':'—'}</td>
                    <td style={{padding:'6px 7px'}}><button onClick={()=>removeProd(i)} style={{background:'none',border:'none',cursor:'pointer',color:'#ef4444',fontSize:13}}>✕</button></td>
                  </tr>;
                })}
              </tbody>
              {totalHT>0&&<tfoot><tr style={{borderTop:'2px solid #e2e8f0'}}><td colSpan={4} style={{padding:'7px 7px',textAlign:'right',fontWeight:800,fontSize:13,color:'#0369a1'}}>Total estimatif HT :</td><td style={{padding:'7px 7px',fontWeight:800,fontSize:14,color:'#0369a1',whiteSpace:'nowrap'}}>{totalHT.toFixed(2)} €</td><td/></tr></tfoot>}
            </table>
          </div>
        )}

        {/* ── Signatures ── */}
        <div style={{background:'#fff',borderRadius:13,padding:'14px 16px',marginBottom:14,border:'1.5px solid #e2e8f0'}}>
          <div style={{fontWeight:700,fontSize:13,color:'#1e293b',marginBottom:12}}>✍️ Signatures</div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
            <div>
              <label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:5}}>Signature du technicien</label>
              <input value={signTech||tech} onChange={e=>setSignTech(e.target.value)}
                placeholder={tech||'Prénom Nom technicien'}
                style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'10px 12px',fontFamily:"Georgia,serif",fontSize:16,outline:'none',boxSizing:'border-box',fontStyle:'italic',color:'#1e293b'}} />
              {(signTech||tech)&&<div style={{fontSize:11,color:'#0ea5e9',marginTop:3}}>✓ Intervenu par {signTech||tech} le {date}</div>}
            </div>
            <div>
              <label style={{fontSize:11,fontWeight:600,color:'#64748b',display:'block',marginBottom:5}}>Signature du client (bon pour accord)</label>
              <input value={signClient} onChange={e=>setSignClient(e.target.value)}
                placeholder={client||'Nom complet du client'}
                style={{width:'100%',border:'1.5px solid #dde4ed',borderRadius:8,padding:'10px 12px',fontFamily:"Georgia,serif",fontSize:16,outline:'none',boxSizing:'border-box',fontStyle:'italic',color:'#1e293b'}} />
              {signClient&&<div style={{fontSize:11,color:'#16a34a',marginTop:3}}>✓ Lu et approuvé par {signClient}</div>}
            </div>
          </div>
        </div>

        {/* ── Enregistrement ── */}
        <div style={{background:'#fff',borderRadius:13,border:'1.5px solid #e2e8f0',marginBottom:14,overflow:'hidden'}}>
          <div style={{background:'#1e293b',padding:'11px 16px',display:'flex',alignItems:'center',gap:8}}>
            <span style={{fontWeight:800,fontSize:14,color:'#fff'}}>📋 Enregistrement de la fiche</span>
            <span style={{marginLeft:'auto',fontSize:11,color:'rgba(255,255,255,.55)'}}>Statut · Signatures · Sauvegarde</span>
          </div>
          <div style={{padding:'16px'}}>
            <div style={{fontWeight:700,fontSize:12,color:'#1e293b',marginBottom:8}}>Statut de la visite</div>
            <div style={{display:'flex',gap:7,flexWrap:'wrap',marginBottom:14}}>
              {[{k:'en_cours',l:'🔄 En cours',c:'#f59e0b'},{k:'termine',l:'✅ Terminée',c:'#16a34a'},{k:'a_replanifier',l:'🔁 À replanifier',c:'#ef4444'},{k:'attente_pieces',l:'⏳ Attente pièces',c:'#8b5cf6'}].map(s=>(
                <button key={s.k} onClick={()=>setStatut(s.k)}
                  style={{padding:'7px 13px',borderRadius:9,border:`2px solid ${statut===s.k?s.c:'#e2e8f0'}`,background:statut===s.k?s.c+'22':'#fff',color:statut===s.k?s.c:'#475569',fontWeight:statut===s.k?700:500,fontSize:12,cursor:'pointer',transition:'all .15s'}}>
                  {s.l}
                </button>
              ))}
            </div>
            {/* résumé */}
            <div style={{background:'#f8fafc',borderRadius:9,padding:'10px 14px',marginBottom:14,fontSize:12,color:'#475569',display:'flex',gap:14,flexWrap:'wrap'}}>
              <span>👤 {client||'—'}</span><span>📅 {date}</span>
              <span>🔧 {INTERVENTION_TYPES.find(t=>t.key===type)?.label||type}</span>
              <span>✅ {totalDone}/{totalItems} ({pct}%)</span>
              {products.length>0&&<span>🛒 {products.length} produit{products.length>1?'s':''} — {totalHT.toFixed(2)} € HT</span>}
            </div>
            {/* boutons */}
            <div style={{display:'flex',gap:9,flexWrap:'wrap'}}>
              <button onClick={saveToHistory} style={{background:saved?'#16a34a':'#0ea5e9',color:'#fff',border:'none',borderRadius:9,padding:'10px 22px',fontWeight:700,fontSize:13,cursor:'pointer',flex:1,minWidth:180,transition:'background .3s'}}>
                {saved?'✅ Fiche enregistrée !':'💾 Enregistrer la fiche'}
              </button>
              <button onClick={()=>setShowQuote(true)} style={{background:'#7c3aed',color:'#fff',border:'none',borderRadius:9,padding:'10px 18px',fontWeight:700,fontSize:12,cursor:'pointer'}}>
                📄 Créer un devis
              </button>
              <button onClick={()=>window.print()} style={{background:'none',border:'1.5px solid #e2e8f0',borderRadius:9,padding:'10px 16px',fontWeight:600,fontSize:12,cursor:'pointer',color:'#475569'}}>
                🖨️ Imprimer / PDF
              </button>
            </div>
          </div>
        </div>

        {/* pied de page */}
        <div style={{textAlign:'center',padding:'8px 0 16px',fontSize:11,color:'#94a3b8'}}>
          Lolirine Pool Store · lolirinepoolstore.be · BCE 0650.891.279
        </div>

      </div>{/* fin container */}

      {/* ── Modals ── */}
      {panel&&<ProductPanel item={panel.item} sectionLabel={panel.sectionLabel} onAdd={handleAddProducts} onClose={()=>setPanel(null)} />}
      {showQuote&&<QuoteModal products={products} client={client} clientId={clientId} address={address} refDossier={ref} onClose={()=>setShowQuote(false)} onCreated={()=>{}} />}
      {showHistory&&<HistoryModal onClose={()=>setShowHistory(false)} onLoad={loadRecord} />}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   MOUNT
═══════════════════════════════════════════════════ */
ReactDOM.createRoot(document.getElementById('pool-checklist-root')).render(<PoolChecklist />);
