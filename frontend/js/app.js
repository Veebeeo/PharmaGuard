const API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:10000' 
    : 'https://pharmaguard-f2fy.onrender.com';
let curPage='landing',upFile=null,selDrugs=new Set(),aResults=null;

// ━━━ AUTH STATE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
let authToken=localStorage.getItem('pg_token')||null;
let authUser=JSON.parse(localStorage.getItem('pg_user')||'null');

function setAuth(token,user){
  authToken=token;authUser=user;
  if(token){localStorage.setItem('pg_token',token);localStorage.setItem('pg_user',JSON.stringify(user))}
  else{localStorage.removeItem('pg_token');localStorage.removeItem('pg_user')}
}
function isLoggedIn(){return !!authToken}

// ━━━ NAVIGATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function navigate(p){
  // Auth gates: landing & auth are public. Everything else requires login.
  const pub=['landing','auth'];
  if(!isLoggedIn()&&!pub.includes(p)){p='auth'}
  // If logged in and trying to go to auth/landing, redirect to home
  if(isLoggedIn()&&(p==='auth'||p==='landing')){p='home'}

  document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.nlk').forEach(x=>x.classList.remove('active'));
  const el=document.getElementById('page-'+p);
  if(el)el.classList.add('active');
  const nl=document.querySelector(`.nlk[data-page="${p}"]`);
  if(nl)nl.classList.add('active');

  // Show nav only when logged in
  document.getElementById('main-nav').classList.toggle('vis',isLoggedIn());

  curPage=p;
  window.scrollTo({top:0,behavior:'smooth'});

  if(p==='dashboard'&&isLoggedIn())loadDashboard();
  if(p==='home'&&isLoggedIn()){
    const hu=document.getElementById('home-user');
    if(hu)hu.textContent=authUser?.email?.split('@')[0]||'Clinician';
  }
}

window.addEventListener('load',()=>{
  const hash=window.location.hash;
  if(hash&&hash.includes('access_token=')){
    const params=new URLSearchParams(hash.substring(1));
    const token=params.get('access_token');
    if(token){setAuth(token,{email:"Confirmed User"});window.location.hash="";navigate('home')}
  }
});

document.querySelectorAll('.nlk').forEach(l=>l.addEventListener('click',()=>{if(l.dataset.page)navigate(l.dataset.page)}));

// ━━━ AUTH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function showAuthErr(msg,type){
  const el=document.getElementById('auth-err');
  document.getElementById('auth-err-t').textContent=msg;
  el.classList.remove('success');
  if(type==='success')el.classList.add('success');
  el.classList.add('vis');
}

async function doLogin(){
  const email=document.getElementById('auth-email').value.trim();
  const pw=document.getElementById('auth-pw').value;
  if(!email||!pw){showAuthErr('Email and password required.');return}
  try{
    const r=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password:pw})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'Login failed');
    setAuth(d.access_token,d.user);
    document.getElementById('user-tag').textContent=d.user.email;
    navigate('home');
  }catch(e){showAuthErr(e.message)}
}

async function doSignup(){
  const email=document.getElementById('auth-email').value.trim();
  const pw=document.getElementById('auth-pw').value;
  if(!email||!pw){showAuthErr('Email and password required.');return}
  if(pw.length<6){showAuthErr('Password must be 6+ characters.');return}
  try{
    const r=await fetch(API+'/api/auth/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password:pw})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'Signup failed');
    showAuthErr('Account created! You can now sign in.','success');
  }catch(e){showAuthErr(e.message)}
}

function doLogout(){
  setAuth(null,null);
  document.getElementById('auth-email').value='';
  document.getElementById('auth-pw').value='';
  document.getElementById('auth-err').classList.remove('vis','success');
  navigate('landing');
}

// ━━━ FILE UPLOAD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const uz=document.getElementById('uz'),finp=document.getElementById('finp');
['dragenter','dragover'].forEach(e=>uz.addEventListener(e,ev=>{ev.preventDefault();uz.classList.add('drag')}));
['dragleave','drop'].forEach(e=>uz.addEventListener(e,ev=>{ev.preventDefault();uz.classList.remove('drag')}));
uz.addEventListener('drop',ev=>{if(ev.dataTransfer.files.length)handleFile(ev.dataTransfer.files[0])});
finp.addEventListener('change',ev=>{if(ev.target.files.length)handleFile(ev.target.files[0])});

function handleFile(f){
  hideErr();
  if(!f.name.toLowerCase().endsWith('.vcf')){showErr('Invalid file type. Please upload a .vcf file.');uz.classList.add('err');setTimeout(()=>uz.classList.remove('err'),2e3);return}
  if(f.size>5*1024*1024){showErr('File too large. Maximum size is 5 MB.');uz.classList.add('err');setTimeout(()=>uz.classList.remove('err'),2e3);return}
  const r=new FileReader();
  r.onload=e=>{
    const c=e.target.result,lines=c.split('\n').filter(l=>l.trim());
    if(!lines.some(l=>l.startsWith('#CHROM')||l.startsWith('##fileformat')))showErr('Warning: File may not be valid VCF. Server will validate.');
    upFile=f;showOk(f);updSteps();updBtn();
  };r.readAsText(f);
}
function showOk(f){document.getElementById('uz-p').style.display='none';document.getElementById('uz-ok').style.display='block';document.getElementById('fn').textContent=f.name;document.getElementById('fs').textContent=fmtSz(f.size);uz.classList.add('has');uz.classList.remove('err')}
function rmFile(ev){ev.stopPropagation();upFile=null;finp.value='';document.getElementById('uz-p').style.display='';document.getElementById('uz-ok').style.display='none';uz.classList.remove('has');updSteps();updBtn()}
function fmtSz(b){if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(2)+' MB'}

// ━━━ DRUG SELECT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
document.querySelectorAll('.pill').forEach(p=>p.addEventListener('click',()=>{
  const d=p.dataset.drug;
  if(selDrugs.has(d)){selDrugs.delete(d);p.classList.remove('sel')}else{selDrugs.add(d);p.classList.add('sel')}
  syncDI();updSteps();updBtn();
}));
function syncDI(){document.getElementById('dinp').value=Array.from(selDrugs).join(', ')}
document.getElementById('dinp').addEventListener('input',ev=>{
  selDrugs=new Set(ev.target.value.split(',').map(d=>d.trim().toUpperCase()).filter(Boolean));
  document.querySelectorAll('.pill').forEach(p=>p.classList.toggle('sel',selDrugs.has(p.dataset.drug)));
  updSteps();updBtn();
});
function selAll(){document.querySelectorAll('.pill').forEach(p=>{selDrugs.add(p.dataset.drug);p.classList.add('sel')});syncDI();updSteps();updBtn()}

function updSteps(){
  const s1=document.getElementById('step-1'),s2=document.getElementById('step-2'),s3=document.getElementById('step-3');
  s1.className=upFile?'stp done':'stp act';
  s2.className=selDrugs.size>0?'stp done':(upFile?'stp act':'stp');
  s3.className=(upFile&&selDrugs.size>0)?'stp act':'stp';
}
function updBtn(){
  const ok=upFile&&selDrugs.size>0;
  document.getElementById('abtn').disabled=!ok;
  document.getElementById('astat').textContent=ok?`Ready — ${selDrugs.size} drug(s) selected`:(!upFile?'Upload a VCF file to continue':'Select at least one drug');
}
updBtn();

function showErr(m){document.getElementById('eb-t').textContent=m;document.getElementById('eb').classList.add('vis')}
function hideErr(){document.getElementById('eb').classList.remove('vis')}

// ━━━ ANALYSIS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async function runAnalysis(){
  if(!upFile||!selDrugs.size)return;hideErr();
  const lo=document.getElementById('lo'),los=document.getElementById('lo-s');lo.classList.add('active');
  const msgs=['Parsing VCF file...','Detecting pharmacogenomic variants...','Querying CPIC guidelines...','Generating AI explanations...','Saving to dashboard...','Assembling report...'];
  let mi=0;const si=setInterval(()=>{mi=(mi+1)%msgs.length;los.textContent=msgs[mi]},2e3);
  try{
    const fd=new FormData();fd.append('vcf_file',upFile);fd.append('drugs',Array.from(selDrugs).join(','));
    const endpoint=authToken?'/api/analyze-secure':'/api/analyze';
    const headers=authToken?{'Authorization':'Bearer '+authToken}:{};
    const res=await fetch(API+endpoint,{method:'POST',body:fd,headers});
    if(!res.ok){let em='Analysis failed.';try{em=(await res.json()).detail||em}catch{}throw new Error(em)}
    const data=await res.json();
    aResults=data.results?data:{results:data.results||[data],total_drugs_analyzed:data.total_drugs_analyzed||1,analysis_id:data.analysis_id||''};
    renderResults(aResults);
    document.getElementById('nav-results').style.display='';navigate('results');
  }catch(e){showErr(e.message||'Failed to connect to server.')}
  finally{clearInterval(si);lo.classList.remove('active')}
}

// ━━━ RENDER RESULTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function renderResults(data){
  const c=document.getElementById('rcon'),rs=data.results||[];
  document.getElementById('rs-sub').textContent=`${rs.length} drug(s) analyzed · Patient: ${rs[0]?.patient_id||'Unknown'}`;
  c.innerHTML=rs.map((r,i)=>renderCard(r,i)).join('');
  c.querySelectorAll('.st').forEach(b=>b.addEventListener('click',()=>{b.classList.toggle('open');b.nextElementSibling.classList.toggle('open')}));
}

function rc(l){const x=(l||'').toLowerCase().replace(/\s+/g,'');return x==='safe'?'safe':x==='adjustdosage'?'adjust':x==='toxic'?'toxic':x==='ineffective'?'ineffective':'unknown'}
function ri(c){return{safe:'<svg class="ic" style="width:14px;height:14px;stroke:#fff"><use href="#i-check"/></svg>',adjust:'<svg class="ic" style="width:14px;height:14px;stroke:#fff"><use href="#i-alert"/></svg>',toxic:'<svg class="ic" style="width:14px;height:14px;stroke:#fff"><use href="#i-x"/></svg>',ineffective:'<svg class="ic" style="width:14px;height:14px;stroke:#fff"><use href="#i-alert"/></svg>',unknown:'<svg class="ic" style="width:14px;height:14px;stroke:#fff"><use href="#i-info"/></svg>'}[c]||''}
function pf(p){return{PM:'Poor Metabolizer (PM)',IM:'Intermediate Metabolizer (IM)',NM:'Normal Metabolizer (NM)',RM:'Rapid Metabolizer (RM)',URM:'Ultra-Rapid Metabolizer (URM)'}[p]||p}
function fe(e){return(e||'unknown').replace(/_/g,' ')}
function eh(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

function renderCard(r,idx){
  const c=rc(r.risk_assessment.risk_label),p=r.pharmacogenomic_profile,rec=r.clinical_recommendation,llm=r.llm_generated_explanation,qm=r.quality_metrics,vs=p.detected_variants||[];
  return`<div class="rc fin" style="animation-delay:${idx*.08}s">
  <div class="rb ${c}"><div class="rl"><span class="r-drug">${r.drug}</span><span class="r-badge ${c}">${ri(c)} ${r.risk_assessment.risk_label}</span></div>
  <div class="rm"><span>Confidence: <strong>${(r.risk_assessment.confidence_score*100).toFixed(0)}%</strong></span><span>Severity: <strong>${r.risk_assessment.severity}</strong></span><span>Gene: <strong>${p.primary_gene}</strong></span><span>${p.diplotype} → ${p.phenotype}</span></div></div>
  <div>
  <div class="cs"><button class="st open"><svg class="ic" style="width:16px;height:16px"><use href="#i-dna"/></svg> Pharmacogenomic Profile<span class="chv">&#x25BC;</span></button>
  <div class="sc open"><div class="pg">
    <div class="pi"><div class="pi-l">Primary Gene</div><div class="pi-v mono">${p.primary_gene}</div></div>
    <div class="pi"><div class="pi-l">Diplotype</div><div class="pi-v mono">${p.diplotype}</div></div>
    <div class="pi"><div class="pi-l">Phenotype</div><div class="pi-v">${pf(p.phenotype)}</div></div>
    <div class="pi"><div class="pi-l">Variants Detected</div><div class="pi-v">${vs.length}</div></div>
  </div>${vs.length?`<table class="vt" style="margin-top:.8rem"><thead><tr><th>rsID</th><th>Star</th><th>GT</th><th>Effect</th><th>Qual</th></tr></thead><tbody>${vs.map(v=>`<tr><td class="rsid">${v.rsid}</td><td class="star">${v.star_allele}</td><td>${v.genotype||'—'}</td><td><span class="et ${v.functional_effect}">${fe(v.functional_effect)}</span></td><td>${v.quality||'—'}</td></tr>`).join('')}</tbody></table>`:'<p style="color:var(--text-3);font-size:.82rem;margin-top:.4rem">No variants — wildtype assumed.</p>'}</div></div>
  <div class="cs"><button class="st open"><svg class="ic" style="width:16px;height:16px"><use href="#i-clipboard"/></svg> Clinical Recommendation<span class="chv">&#x25BC;</span></button>
  <div class="sc open"><div class="rd">${rec.dosing_recommendation}</div>
  ${rec.urgency?`<div class="rr"><span class="rr-l">Urgency</span><span class="ut ${rec.urgency}">${rec.urgency}</span></div>`:''}
  ${rec.alternative_drugs?.length?`<div class="rr"><span class="rr-l">Alternatives</span><div class="rr-chips">${rec.alternative_drugs.map(d=>`<span class="rr-c">${d}</span>`).join('')}</div></div>`:''}
  ${rec.monitoring_parameters?.length?`<div class="rr"><span class="rr-l">Monitoring</span><div class="rr-chips">${rec.monitoring_parameters.map(m=>`<span class="rr-c">${m}</span>`).join('')}</div></div>`:''}
  ${rec.cpic_guideline_reference?`<div class="rr"><span class="rr-l">CPIC Ref</span><span style="font-size:.78rem;color:var(--text-3)">${rec.cpic_guideline_reference}</span></div>`:''}</div></div>
  <div class="cs"><button class="st"><svg class="ic" style="width:16px;height:16px"><use href="#i-brain"/></svg> AI-Generated Explanation<span class="chv">&#x25BC;</span></button>
  <div class="sc"><div class="llm">
    <p><strong>Summary:</strong> ${llm.summary}</p>
    ${llm.mechanism?`<p><strong>Mechanism:</strong> ${llm.mechanism}</p>`:''}
    ${llm.variant_specific_effects?.length?`<p><strong>Variant Effects:</strong></p><ul style="padding-left:1.1rem;margin-bottom:.8rem">${llm.variant_specific_effects.map(e=>`<li style="font-size:.82rem;color:var(--text-2);margin-bottom:.2rem">${e}</li>`).join('')}</ul>`:''}
    ${llm.patient_friendly_summary?`<p><strong>For the Patient:</strong> ${llm.patient_friendly_summary}</p>`:''}
    ${llm.citations?.length?`<p style="font-size:.76rem;color:var(--text-3)"><strong>References:</strong> ${llm.citations.join(' · ')}</p>`:''}
    <div class="llm-tag"><svg class="ic" style="width:12px;height:12px"><use href="#i-star"/></svg> ${llm.model_used}</div>
  </div></div></div>
  <div class="cs"><button class="st"><svg class="ic" style="width:16px;height:16px"><use href="#i-settings"/></svg> Quality Metrics<span class="chv">&#x25BC;</span></button>
  <div class="sc"><div class="pg">
    <div class="pi"><div class="pi-l">VCF Parsing</div><div class="pi-v">${qm.vcf_parsing_success?'Success':'Failed'}</div></div>
    <div class="pi"><div class="pi-l">Total Variants</div><div class="pi-v">${qm.total_variants_parsed}</div></div>
    <div class="pi"><div class="pi-l">PGx Variants</div><div class="pi-v">${qm.pharmacogenomic_variants_found}</div></div>
    <div class="pi"><div class="pi-l">Gene Coverage</div><div class="pi-v mono" style="font-size:.76rem">${qm.gene_coverage?.join(', ')||'None'}</div></div>
  </div></div></div>
  <div class="cs"><button class="st"><svg class="ic" style="width:16px;height:16px"><use href="#i-code"/></svg> Raw JSON Output<span class="chv">&#x25BC;</span></button>
  <div class="sc"><div class="jv"><div class="jv-bar"><button class="jv-btn" onclick="cpJ(${idx})">Copy</button><button class="jv-btn" onclick="dlJ(${idx})">Download</button></div><pre class="jv-pre">${eh(JSON.stringify(r,null,2))}</pre></div></div></div>
  </div></div>`;
}

function cpJ(i){const r=aResults.results[i];navigator.clipboard.writeText(JSON.stringify(r,null,2)).then(()=>{const cards=document.querySelectorAll('.rc');if(cards[i]){const b=cards[i].querySelector('.jv-btn');if(b){b.textContent='Copied!';b.classList.add('copied');setTimeout(()=>{b.textContent='Copy';b.classList.remove('copied')},2e3)}}})}
function dlJ(i){const r=aResults.results[i],b=new Blob([JSON.stringify(r,null,2)],{type:'application/json'}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=`pharmaguard_${r.drug}_${r.patient_id}.json`;a.click();URL.revokeObjectURL(u)}
function cpAll(){navigator.clipboard.writeText(JSON.stringify(aResults,null,2))}
function dlAll(){const b=new Blob([JSON.stringify(aResults,null,2)],{type:'application/json'}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download='pharmaguard_full_analysis.json';a.click();URL.revokeObjectURL(u)}

// ━━━ DASHBOARD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async function loadDashboard(){
  if(!authToken)return;
  const ll=document.getElementById('dash-loading'),em=document.getElementById('dash-empty'),ls=document.getElementById('dash-list');
  ll.style.display='';em.style.display='none';ls.innerHTML='';
  document.getElementById('dash-stats-row').style.display='none';
  try{
    const r=await fetch(API+'/api/dashboard',{headers:{'Authorization':'Bearer '+authToken}});
    if(!r.ok)throw new Error('Failed to load');
    const d=await r.json();
    ll.style.display='none';
    if(!d.reports||!d.reports.length){em.style.display='';return}

    // Stats
    document.getElementById('dash-stats-row').style.display='';
    document.getElementById('ds-total').textContent=d.total||d.reports.length;
    let ns=0,na=0,nt=0;
    d.reports.forEach(rp=>{const c=rc(rp.risk_label);if(c==='safe')ns++;else if(c==='adjust')na++;else nt++});
    document.getElementById('ds-safe').textContent=ns;
    document.getElementById('ds-adj').textContent=na;
    document.getElementById('ds-tox').textContent=nt;

    document.getElementById('dash-sub').textContent=`${d.total||d.reports.length} saved report(s) · ${authUser?.email||''}`;

    // Table
    ls.innerHTML=`<div class="dtbl"><div class="dtbl-h"><span>Drug</span><span>Gene / Diplotype</span><span>Risk</span><span>Patient</span><span>Date</span><span></span></div>${d.reports.map(rp=>{
      const cls=rc(rp.risk_label);
      return`<div class="drow" onclick="viewReport('${rp.id}')">
        <span class="dr-d">${rp.drug}</span>
        <span class="dr-g">${rp.gene} ${rp.diplotype||''} → ${rp.phenotype||''}</span>
        <span><span class="r-badge ${cls}" style="font-size:.68rem;padding:3px 9px">${ri(cls)} ${rp.risk_label}</span></span>
        <span class="dr-p">${rp.patient_id||'—'}</span>
        <span class="dr-dt">${new Date(rp.created_at).toLocaleDateString()}</span>
        <button class="ddel" onclick="event.stopPropagation();delReport('${rp.id}')" title="Delete"><svg class="ic" style="width:15px;height:15px"><use href="#i-trash"/></svg></button>
      </div>`;
    }).join('')}</div>`;
  }catch(e){ll.textContent='Failed to load reports. '+e.message}
}

async function viewReport(id){
  if(!authToken)return;
  try{
    const r=await fetch(API+'/api/dashboard/'+id,{headers:{'Authorization':'Bearer '+authToken}});
    if(!r.ok)throw new Error('Not found');
    const d=await r.json();
    if(d.report_json){
      aResults={results:[d.report_json],total_drugs_analyzed:1,analysis_id:''};
      renderResults(aResults);
      document.getElementById('nav-results').style.display='';navigate('results');
    }
  }catch(e){alert('Error loading report: '+e.message)}
}

async function delReport(id){
  if(!confirm('Delete this report?'))return;
  try{
    await fetch(API+'/api/dashboard/'+id,{method:'DELETE',headers:{'Authorization':'Bearer '+authToken}});
    loadDashboard();
  }catch(e){alert('Delete failed: '+e.message)}
}

// ━━━ INIT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if(isLoggedIn()){
  document.getElementById('user-tag').textContent=authUser?.email||'';
  navigate('home');
}else{
  navigate('landing');
}
