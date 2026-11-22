const API="http://127.0.0.1:8000";
const S={view:"fleet",assets:[],rows:[],selected:null,asset:null,sim:{speed:1,running:false}};
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const first=(o,ks,d=null)=>{for(const k of ks)if(o&&o[k]!=null)return o[k];return d};
function esc(v){return String(v??"—").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function n(v,d=0){let x=Number(v);return Number.isFinite(x)?x:d}
function f(v,d=2){return n(v).toFixed(d)}
function toast(x){let t=$("#toast");t.textContent=x;t.className="show";setTimeout(()=>t.className="",2600)}
async function api(path,opt={},ms=4500){let c=new AbortController(),t=setTimeout(()=>c.abort(),ms);try{let r=await fetch(API+path,{...opt,signal:c.signal,headers:{"Content-Type":"application/json",...(opt.headers||{})}}),txt=await r.text(),d={};try{d=JSON.parse(txt)}catch{d={raw:txt}}if(!r.ok)throw Error(`${r.status}: ${d.detail||d.raw||"request failed"}`);return d}finally{clearTimeout(t)}}
async function fetchAssetPayload(id){
 const paths=[
  `/api/assets/${encodeURIComponent(id)}`,
  `/api/assets/${encodeURIComponent(id)}/exposure`,
  `/api/assets/${encodeURIComponent(id)}/timeline`,
  `/api/exposure/${encodeURIComponent(id)}`
 ];
 let last=null;
 for(const p of paths){
  try{
   const d=await api(p);
   if(d && typeof d==="object" && (timelineOf(d).length || d.exposure_summary || d.evidence_quality || d.inspection_priority)) return d;
  }catch(e){last=e}
 }
 throw last || Error("Asset exposure data unavailable");
}

function rowsOf(d){if(Array.isArray(d))return d;for(const k of["assets","fleet","rows","results","data","inspection_queue"])if(Array.isArray(d?.[k]))return d[k];return []}
function norm(x){return {asset_id:first(x,["asset_id","id","assetId"],"UNKNOWN"),scenario:first(x,["scenario"],"—"),exposure:first(x,["maximum_exposure","maximum_exposure_state","exposure_state"],"—"),water:n(first(x,["maximum_water_level_m","peak_water_level_m","water_level_m"],0)),duration:n(first(x,["exposure_duration_minutes","total_exposure_duration_minutes"],0)),evidence:n(first(x,["evidence_quality_score","evidence_score","confidence_score"],0)),priority:n(first(x,["priority_score"],0)),priorityClass:first(x,["inspection_priority","priority_class"],"—")}}
async function fleet(){
 try{let d=await api("/api/fleet"),r=rowsOf(d).map(norm).filter(x=>x.asset_id!="UNKNOWN");S.rows=r;S.assets=[...new Map(r.map(x=>[x.asset_id,x])).values()];if(!S.selected&&S.assets.length)S.selected=S.assets[0].asset_id;populate();apiState(true,`${S.assets.length} assets loaded`)}
 catch(e){apiState(false,e.name==="AbortError"?"API timeout":e.message)}
}
function apiState(ok,msg){$("#apiDot").className="dot "+(ok?"good":"bad");$("#apiText").textContent=ok?"API ONLINE":"API OFFLINE";$("#apiMsg").textContent=msg;$("#sys").textContent=ok?"● System Live":"● API Disconnected"}
function populate(){let s=$("#asset");s.innerHTML=S.assets.map(a=>`<option value="${esc(a.asset_id)}">${esc(a.asset_id)} · ${esc(a.scenario)}</option>`).join("");if(S.selected)s.value=S.selected;$("#selectedPill").textContent=S.selected||"Choose Asset"}
async function loadAsset(id){
 S.selected=id; populate();
 try{S.asset=await fetchAssetPayload(id);apiState(true,`Asset ${id} online`)}
 catch(e){S.asset=S.rows.find(x=>x.asset_id===id)||{};apiState(false,e.message||"Asset API unavailable")}
}
function deep(o,keys,seen=new Set()){if(o==null||typeof o!=="object"||seen.has(o))return null;seen.add(o);for(const k of keys)if(o[k]!=null)return o[k];for(const v of Object.values(o)){let z=deep(v,keys,seen);if(z!=null)return z}return null}
function timelineOf(o){let t=deep(o,["reconstructed_timeline","exposure_timeline","timeline","samples","sensor_data","readings"]);return Array.isArray(t)?t:[]}
function timeOf(p){return first(p,["timestamp","time","datetime","date"],null)}
function waterOf(p){return n(first(p,["water_level_m","water_level","waterLevel","depth_m","depth"],0))}
function deriveDuration(t){
 if(t.length<2)return null;let a=timeOf(t[0]),b=timeOf(t[t.length-1]);if(!a||!b)return null;let x=Date.parse(a),y=Date.parse(b);return Number.isFinite(x)&&Number.isFinite(y)?Math.max(0,(y-x)/60000):null
}
function data(o){
 let e=deep(o,["exposure_summary","exposure","summary"])||{},ev=deep(o,["evidence_quality","evidence"])||{},pr=deep(o,["inspection_priority","priority"])||{};
 let t=timelineOf(o),dur=first(e,["total_exposure_duration_minutes","exposure_duration_minutes"],null);if(dur==null)dur=deriveDuration(t);
 return {e,ev,pr,t,dur,water:first(e,["maximum_water_level_m","peak_water_level_m","water_level_m"],null),cond:first(e,["maximum_conductivity_ms_cm"],null),hum:first(e,["maximum_humidity_pct"],null),priority:first(pr,["priority_score"],null),pclass:first(pr,["priority_class","inspection_priority"],null),score:first(ev,["confidence_score","score"],null)}
}
function nav(){
 $$(".nav").forEach(x=>x.classList.toggle("active",x.dataset.view===S.view));
 $$(".subnav [data-view]").forEach(x=>x.classList.toggle("active",x.dataset.view===S.view));
}
function render(){nav();({fleet:fleetView,assets:assetView,reports:passport,sim:simView,settings:settings,support:support}[S.view]||fleetView)()}
function fleetView(){
 const avg=S.rows.length?S.rows.reduce((a,x)=>a+x.priority,0)/S.rows.length:0;
 const critical=S.rows.filter(x=>String(x.priorityClass).toUpperCase().includes("CRITICAL")).length;
 const high=S.rows.filter(x=>String(x.priorityClass).toUpperCase().includes("HIGH")).length;
 const selected=S.rows.find(x=>x.asset_id===S.selected)||{};
 $("#app").innerHTML=`
 <div class="fleet-page">
   <div class="fleet-title-row">
     <div><div class="title">Fleet Overview</div><div class="subtitle">Exposure reconstruction and inspection prioritization across the simulated fleet.</div></div>
     <div class="top-search fleet-inline-search"><span>⌕</span><input id="fleetSearch" placeholder="Search asset ID, scenario or exposure..."></div>
   </div>

   <div class="cards">
    <div class=card><div class=label>Total Active Assets</div><div class=big>${S.rows.length}</div><div class=cyan>CONNECTED DATASET</div></div>
    <div class=card><div class=label>Critical Assets</div><div class="big red">${critical}</div><div>${S.rows.length?f(critical/S.rows.length*100,1)+"% of fleet":"—"}</div></div>
    <div class=card><div class=label>High Priority</div><div class=big>${high}</div><div>${S.rows.length?f(high/S.rows.length*100,1)+"% of fleet":"—"}</div></div>
    <div class=card><div class=label>Fleet Priority Average</div><div class=big>${f(avg)} /100</div><div class=bar><i style="width:${Math.min(100,avg)}%"></i></div></div>
   </div>

   <div class="panel unified-assets">
    <div class="unified-head">
      <div><h3>Fleet Assets & Inspection Queue</h3><div class=muted>Select an asset below to view its inspection details.</div></div>
      <select id="fleetAssetSelect" class="select compact">${S.assets.map(a=>`<option ${a.asset_id===S.selected?"selected":""} value="${esc(a.asset_id)}">${esc(a.asset_id)} · ${esc(a.scenario)}</option>`).join("")}</select>
    </div>
    <div class="unified-body">
      <div class="asset-directory-pane">
        <div class="pane-label">ASSET DIRECTORY</div>
        <div id="assetList" class="asset-list">${S.rows.slice().sort((a,b)=>b.priority-a.priority).map(x=>`
          <button class="asset-row ${x.asset_id===S.selected?"selected":""}" data-id="${esc(x.asset_id)}">
            <span class="asset-main"><b>${esc(x.asset_id)}</b><small>${esc(x.scenario)} · ${esc(x.exposure)}</small></span>
            <span class=asset-water>${f(x.water,3)} m</span>
            <span class=asset-priority>${f(x.priority,2)}</span>
          </button>`).join("")}</div>
      </div>

      <div class="selected-pane" id="selectedAssetCard">
        <div class="pane-label">SELECTED ASSET</div>
        <div class=selected-id>${esc(selected.asset_id||S.selected||"—")}</div>
        <div class="selected-sub">${esc(selected.scenario||"")} · ${esc(selected.exposure||"")}</div>
        <div class="selected-grid">
          <div class=mini><span>Peak Water</span><strong>${selected.water!=null?f(selected.water,3)+" m":"—"}</strong></div>
          <div class=mini><span>Evidence</span><strong>${selected.evidence!=null?f(selected.evidence,2)+"%":"—"}</strong></div>
          <div class=mini><span>Priority</span><strong>${selected.priority!=null?f(selected.priority,2):"—"}</strong></div>
          <div class=mini><span>Duration</span><strong>${selected.duration!=null?f(selected.duration,1)+" min":"—"}</strong></div>
        </div>
        <div class="selected-actions">
          <button data-action=open-monitor>Open Live Monitor</button>
          <button data-action=open-passport>Open Passport</button>
        </div>
      </div>
    </div>
   </div>
 </div>`;
}
function scenarioBtns(){return [["rain","HEAVY RAIN"],["partial_submersion","PARTIAL SUB"],["deep_submersion","DEEP SUB"],["power_network_failure","CASCADING FAIL"],["sensor_failure","SENSOR FAIL"]].map(([v,l])=>`<button data-scen=${v} class="${$("#scenario").value===v?"active":""}">${l}</button>`).join("")}
function axisGraph(t){
 if(!t||!t.length)return `<div class="graph-empty"><div class="graph-empty-icon">⌁</div><b>No reconstructed timeline available</b><span>The backend did not return timeline samples for this asset.</span></div>`;
 const vals=t.map(waterOf),max=Math.max(...vals),min=Math.min(...vals),range=(max-min)||1,W=1100,H=390,L=86,R=30,T=28,B=64,iw=W-L-R,ih=H-T-B;
 const pts=vals.map((v,i)=>[L+(t.length===1?iw/2:i/(t.length-1)*iw),T+(max-v)/range*ih]);
 const d=pts.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join(" ");
 const area=d+` L ${pts.at(-1)[0]} ${T+ih} L ${pts[0][0]} ${T+ih} Z`;
 let grid="";for(let i=0;i<=5;i++){const y=T+i*ih/5,v=max-i*range/5;grid+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" class="gridline"/><text x="${L-13}" y="${y+4}" text-anchor="end" class="ticktext">${v.toFixed(2)}</text>`}
 const ids=[0,Math.floor((t.length-1)/4),Math.floor((t.length-1)/2),Math.floor((t.length-1)*3/4),t.length-1].filter((x,i,a)=>a.indexOf(x)===i);let xt="";
 ids.forEach(i=>{const x=pts[i][0],q=timeOf(t[i]),lab=q?new Date(q).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}):`#${i+1}`;xt+=`<line x1="${x}" x2="${x}" y1="${T}" y2="${T+ih}" class="vgrid"/><text x="${x}" y="${H-19}" text-anchor="middle" class="ticktext">${esc(lab)}</text>`});
 const pi=vals.indexOf(max),peak=pts[pi];
 return `<div class="graph-shell"><div class="graph-top"><div><b>Water Level</b><span>metres</span></div><div class="graph-legend"><i></i>Reconstructed exposure</div></div><div class="graph-canvas"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}${xt}<line x1="${L}" x2="${L}" y1="${T}" y2="${T+ih}" class="axis"/><line x1="${L}" x2="${W-R}" y1="${T+ih}" y2="${T+ih}" class="axis"/><path d="${area}" class="area"/><path d="${d}" class="line"/><circle cx="${peak[0]}" cy="${peak[1]}" r="5" class="peak-dot"/></svg></div><div class="graph-footer"><span>TIME</span><span>${t.length} samples</span><strong>Peak ${max.toFixed(3)} m</strong><span>Minimum ${min.toFixed(3)} m</span></div></div>`;
}
function assetView(){
 let a=S.rows.find(x=>x.asset_id===S.selected)||{},d=data(S.asset||{}),water=d.water??a.water,dur=d.dur??a.duration,pri=d.priority??a.priority,evscore=d.score??a.evidence;
 let t=d.t,vals=t.map(waterOf),peak=vals.length?Math.max(...vals):water;
 $("#app").innerHTML=`<div class=title>${esc(S.selected)} <span class=state-badge>● RECONSTRUCTED</span></div><div class=subtitle>Live asset monitor · ${esc(a.scenario||"scenario unavailable")}</div>
 <div class=cards><div class=card><div class=label>Peak Water Level</div><div class=big cyan>${water==null?"—":f(water,3)+" m"}</div><div class=muted>from reconstructed evidence</div></div><div class=card><div class=label>Exposure Duration</div><div class=big>${dur==null?"—":f(dur,0)+" min"}</div><div class=muted>${dur==null?"Not returned / derivable":"derived from event timeline"}</div></div><div class=card><div class=label>Conductivity</div><div class=big>${d.cond==null?"—":f(d.cond,3)+" mS/cm"}</div><div class=muted>peak event value</div></div><div class=card><div class=label>Maximum Humidity</div><div class=big>${d.hum==null?"—":f(d.hum,1)+"%"}</div><div class=muted>peak event value</div></div></div>
 <div class=panel><h3>Exposure Reconstruction — Water Level vs Time</h3>${axisGraph(t)}<div class=metrics style="margin-top:10px"><div class=mini><span>Samples</span><strong>${t.length}</strong></div><div class=mini><span>Peak</span><strong>${peak==null?"—":f(peak,3)+" m"}</strong></div><div class=mini><span>Start</span><strong>${esc(timeOf(t[0])||"—")}</strong></div><div class=mini><span>End</span><strong>${esc(timeOf(t.at(-1))||"—")}</strong></div></div></div>
 <div class=grid2><div class=panel><h3>Evidence Engine</h3>${evRows(d.ev)}</div><div class=panel><h3>Priority Engine</h3><div class=big red>${pri==null?"—":f(pri,2)+" /100"}</div><p><b>${esc(d.pclass??a.priorityClass??"—")}</b></p><div class=bar><i style="width:${pri==null?0:Math.min(100,pri)}%"></i></div><p class=muted>Evidence confidence: ${evscore==null?"—":f(evscore,2)+"%"}</p>${dur===0&&pri>=70?`<div class="notice error"><b>Data mismatch detected:</b> backend priority is ${f(pri,2)} but the exposure duration is 0. The UI will not invent a duration; inspect the API payload/timeline.</div>`:""}</div></div>`;
}
function evRows(ev){
 const keys=[["Data Completeness",["data_completeness","completeness"]],["Sensor Integrity",["sensor_integrity","integrity"]],["Temporal Continuity",["temporal_continuity","continuity"]],["Cross Sensor Consistency",["cross_sensor_consistency","consistency"]],["Reconstruction Stability",["reconstruction_stability","stability"]]];
 return keys.map(([label,ks])=>{let v=deep(ev,ks);return `<div class=evidence-row><div class=evidence-head><span>${label}</span><b class=cyan>${v==null?"NOT RETURNED":f(v,2)+"%"}</b></div><div class=bar><i style="width:${v==null?0:Math.min(100,n(v))}%"></i></div></div>`}).join("")
}
function passport(){
 let a=S.rows.find(x=>x.asset_id===S.selected)||{},d=data(S.asset||{}),pri=d.priority??a.priority,ev=d.score??a.evidence;
 $("#app").innerHTML=`<div class=passport><div class=panel><div class=passport-header><div><div class=subtitle>ASSET EXPOSURE PASSPORT</div><h1>${esc(S.selected)}</h1><div class=subtitle>Scenario: ${esc(a.scenario)}</div></div><div class=badge>${esc(d.pclass??a.priorityClass??"NOT CLASSIFIED")}</div></div>
 <div class=metrics style="margin-top:20px"><div class=mini><span>Maximum Exposure</span><strong class=fit>${esc(first(d.e,["maximum_exposure_state","maximum_exposure"],a.exposure)||"—")}</strong></div><div class=mini><span>Peak Water</span><strong>${d.water==null?"—":f(d.water,3)+" m"}</strong></div><div class=mini><span>Exposure Duration</span><strong>${d.dur==null?"—":f(d.dur,0)+" min"}</strong></div><div class=mini><span>Evidence</span><strong>${ev==null?"—":f(ev,2)+"%"}</strong></div></div>
 <div class=panel><h3>Evidence Quality</h3>${evRows(d.ev)}</div><div class=notice><b>System boundary</b><p class=fit>This passport reconstructs exposure evidence and prioritizes inspection attention. It does not diagnose damage, certify safety, or authorize re-energization. Qualified inspection remains required.</p></div><button data-action=print style="margin-top:16px">Export / Print Passport</button></div></div>`
}
function simView(){
 $("#app").innerHTML=`<div class=title>Simulation Control Center</div><div class=subtitle>Choose the asset and scenario. Controls update the same selected asset used by Fleet, Monitor and Passport.</div><div class=panel><h3>Asset</h3><select id=simAsset2 class=select>${S.assets.map(a=>`<option ${a.asset_id===S.selected?"selected":""} value="${esc(a.asset_id)}">${esc(a.asset_id)} · ${esc(a.scenario)}</option>`).join("")}</select><h3 style="margin-top:20px">Scenario</h3><div class=scenario-grid>${scenarioBtns()}</div><h3 style="margin-top:20px">Speed</h3><div class=speed>${["0.5","1","2","5"].map(v=>`<button data-speed=${v} class="${S.sim.speed==v?"active":""}">${v}×</button>`).join("")}</div><div style="margin-top:16px"><button data-action=run>RUN</button> <button data-action=pause>PAUSE</button> <button data-action=reset>RESET</button></div></div><div class=panel><h3>Current State</h3><div class=notice>${S.sim.running?"RUNNING":"READY"} · ${esc(S.selected)} · ${esc($("#scenario").value)}</div></div>`
}
function settings(){$("#app").innerHTML=`<div class=title>Settings</div><div class=panel><h3>Backend Connection</h3><p>API: ${API}</p><p>Status: <b>${$("#apiText").textContent}</b></p><button data-action=reconnect>Test Connection</button></div><div class=panel><h3>Dashboard</h3><p class=fit>Single-page local dashboard. No document index is required.</p></div>`}
function support(){$("#app").innerHTML=`<div class=title>Support</div><div class=panel><h3>Diagnostics</h3><p>Keep FastAPI on port 8000 and this dashboard on port 5500.</p><p>If a metric says NOT RETURNED, the backend payload does not contain that metric; the UI intentionally refuses to fabricate it.</p><button data-action=reconnect>Test API</button></div>`}
async function select(id){
 S.selected=id;
 await loadAsset(id);
 render();
 requestAnimationFrame(()=>{
   const el=document.querySelector(`.asset-row[data-id="${CSS.escape(id)}"]`);
   if(el)el.scrollIntoView({behavior:"smooth",block:"center"});
   const card=document.querySelector("#selectedAssetCard");
   if(card)card.classList.add("focus-pulse");
 });
}
document.addEventListener("click",async e=>{
 let v=e.target.closest("[data-view]")?.dataset.view;if(v){S.view=v;render();return}
 let id=e.target.closest("tr[data-id]")?.dataset.id;if(id){await select(id);S.view="assets";render();return}
 let sc=e.target.closest("[data-scen]")?.dataset.scen;if(sc){$("#scenario").value=sc;render();return}
 let sp=e.target.closest("[data-speed]")?.dataset.speed;if(sp){S.sim.speed=Number(sp);render();return}
 let a=e.target.closest("[data-action]")?.dataset.action;if(!a)return;
 if(a==="open-monitor"){S.view="assets";render()}else if(a==="open-passport"){S.view="reports";render()}else if(["run","pause","reset"].includes(a))await sim(a);else if(a==="new"){S.view="sim";render()}else if(a==="print")window.print();else if(a==="reconnect"){await fleet();if(S.selected)await loadAsset(S.selected);render()}
});
$("#asset").onchange=async e=>{await select(e.target.value)}
document.addEventListener("change",async e=>{if(e.target.id==="simAsset"||e.target.id==="simAsset2")await select(e.target.value)})
$("#scenario").onchange=()=>render();
$("#search").oninput=e=>{let q=e.target.value.toLowerCase();$$(".table tbody tr").forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?"":"none")}
setInterval(()=>$("#clock").textContent=new Date().toISOString().slice(11,19)+" UTC",1000);$("#clock").textContent=new Date().toISOString().slice(11,19)+" UTC";
(async()=>{await fleet();if(S.selected)await loadAsset(S.selected);render();setInterval(async()=>{if(S.view==="assets"||S.view==="reports"){await loadAsset(S.selected);render()}},5000)})();

document.addEventListener("input",e=>{if(e.target.id!=="fleetSearch")return;const q=e.target.value.toLowerCase();document.querySelectorAll(".asset-row,#queuePanel tbody tr").forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?"":"none")});
document.addEventListener("change",async e=>{if(e.target.id==="fleetAssetSelect"){await select(e.target.value);}});

document.addEventListener("input",e=>{
 if(e.target.id!=="fleetSearch" && e.target.id!=="fleetSearchTop") return;
 const q=e.target.value.trim().toLowerCase();
 document.querySelectorAll(".asset-row").forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?"":"none");
});
document.addEventListener("change",async e=>{
 if(e.target.id==="fleetAssetSelect") await select(e.target.value);
});
