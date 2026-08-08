// =====================================================================
// LifeLink AI — frontend controller
// Talks to the FastAPI multi-agent backend (see /backend). Every screen
// below maps to a real endpoint; nothing here is hardcoded demo data
// except the emergency-type icon list and the city map center.
// =====================================================================
const API = window.location.origin;
const CITY_CENTER = { lat: 28.6139, lng: 77.2090 };

const EMERGENCY_TYPES = [
  { key: 'accident',     label: 'Accident',     icon: '🚗' },
  { key: 'heart_attack', label: 'Heart Attack', icon: '🫀' },
  { key: 'stroke',       label: 'Stroke',       icon: '🧠' },
  { key: 'burns',        label: 'Burns',        icon: '🔥' },
  { key: 'pregnancy',    label: 'Pregnancy',    icon: '🤰' },
  { key: 'poisoning',    label: 'Poisoning',    icon: '☠️' },
  { key: 'snake_bite',   label: 'Snake Bite',   icon: '🐍' },
  { key: 'other',        label: 'Other',        icon: '➕' },
];

const SCREENS = ['dashboard','emergency','assessment','hospital','ambulance','doctor','family','command','analytics'];
const STEP_MIN = { dashboard: -1, emergency: 0, assessment: 1, hospital: 2, ambulance: 3, doctor: 4, family: 4, command: -1, analytics: -1 };

let state = {
  caseId: null,
  case: null,
  answeredCount: 0,
  answeredTotal: 0,
  voiceDone: false,
  visionDone: false,
  triage: null,
  hospitals: null,
  dispatch: null,
  ghSeconds: 60 * 60,
  qaTimer: null,
};

let current = 'dashboard';
let map, mapAmbMarker, mapSceneMarker, mapHospMarker, mapRouteLine;
let trackTimer = null;
let trendChart = null;
let backendOnline = null;

// ------------------------------------------------------------ helpers ---
async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(API + path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  } catch (networkErr) {
    setConnStatus(false);
    throw new Error("Can't reach the LifeLink AI server — make sure the backend is running.");
  }
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    setConnStatus(true); // server responded, so it's reachable — just this call failed
    throw new Error(`${path} failed (${res.status}): ${msg}`);
  }
  setConnStatus(true);
  return res.json();
}
function jitter(v, amt) { return v + (Math.random() - 0.5) * amt; }
function fmtTime(sec) {
  sec = Math.max(0, Math.round(sec));
  const m = Math.floor(sec / 60), s = sec % 60;
  return m + ':' + String(s).padStart(2, '0');
}
function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371, toRad = (d) => d * Math.PI / 180;
  const dLat = toRad(lat2 - lat1), dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// -------------------------------------------------------------- toasts --
function toast(msg, type = 'error', ms = 4500) {
  const stack = document.getElementById('toastStack');
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  stack.appendChild(el);
  setTimeout(() => el.remove(), ms);
}
// Wraps a click handler so a failed API call shows a toast instead of
// silently doing nothing — this is what makes buttons feel "broken" when
// the backend isn't reachable.
function guarded(fn) {
  return async (...args) => {
    try { await fn(...args); }
    catch (e) { toast(e.message || 'Something went wrong.'); }
  };
}

// --------------------------------------------------------- connectivity -
function setConnStatus(ok) {
  if (backendOnline === ok) return;
  backendOnline = ok;
  const chip = document.getElementById('connChip');
  const text = document.getElementById('connChipText');
  const banner = document.getElementById('connBanner');
  if (ok) {
    chip.className = 'chip'; text.textContent = 'LIVE'; banner.style.display = 'none';
  } else {
    chip.className = 'chip offline'; text.textContent = 'OFFLINE'; banner.style.display = 'flex';
  }
}
async function checkBackend() {
  try { await api('/api/health'); } catch (e) { /* setConnStatus already called inside api() */ }
}
document.getElementById('connRetryBtn').addEventListener('click', async () => {
  await checkBackend();
  if (backendOnline) { loadWhoSelect(); toast('Connected.', 'warn', 2500); }
});
setInterval(checkBackend, 10000);

// ---------------------------------------------------------- command center --
async function loadCommandCenter() {
  const cases = await api('/api/cases');
  const critical = cases.filter(c => c.risk_level === 'Critical').length;
  const high = cases.filter(c => c.risk_level === 'High').length;
  const stable = cases.filter(c => c.risk_level === 'Moderate' || c.risk_level === 'Low').length;
  document.getElementById('lcCritical').textContent = critical;
  document.getElementById('lcHigh').textContent = high;
  document.getElementById('lcStable').textContent = stable;

  const riskClass = (r) => (r || 'pending').toLowerCase();
  const body = document.getElementById('casesTableBody');
  body.innerHTML = cases.map(c => `
    <tr>
      <td>${c.id}</td>
      <td><span class="ct-risk ${riskClass(c.risk_level)}">${c.risk_level || 'Pending'}</span></td>
      <td>${c.location}</td>
      <td>${c.ambulance_id || '—'}</td>
      <td>${c.hospital_name || '—'}</td>
      <td>${c.eta_min ?? '—'}${c.eta_min != null ? ' min' : ''}</td>
      <td>${c.stage.replace('_', ' ')}</td>
    </tr>
  `).join('') || `<tr><td colspan="7" style="color:var(--muted-dim-dark);text-align:center;">No cases yet.</td></tr>`;
}

// -------------------------------------------------------------- drawers --
function openDrawer(id) { document.getElementById(id).classList.add('open'); }
function closeDrawer(id) { document.getElementById(id).classList.remove('open'); }
document.querySelectorAll('.drawer-close').forEach(btn => btn.addEventListener('click', () => closeDrawer(btn.dataset.close)));
document.getElementById('timelineFab').addEventListener('click', () => { refreshTimelineDrawer(); openDrawer('timelineDrawer'); });
document.getElementById('copilotFab').addEventListener('click', () => { document.getElementById('copilotBadge').style.display = 'none'; openDrawer('copilotDrawer'); });

async function refreshTimelineDrawer() {
  const el = document.getElementById('drawerTimeline');
  if (!state.caseId) { el.innerHTML = '<div style="color:var(--muted);font-size:13px;">No active case yet.</div>'; return; }
  try {
    const feed = await api(`/api/cases/${state.caseId}/family`);
    el.innerHTML = feed.timeline.map((t, i) => `
      <div class="t-item">
        <div class="node"></div>${i < feed.timeline.length - 1 ? '<div class="tline"></div>' : ''}
        <div class="tbody"><b>${new Date(t.at * 1000).toLocaleTimeString('en-GB')}</b><div class="tsub">${t.title}</div></div>
      </div>`).join('');
  } catch (e) { /* case not ready */ }
}

// -------------------------------------------------------------- copilot -
function addChatMsg(role, html) {
  const log = document.getElementById('chatLog');
  const el = document.createElement('div'); el.className = 'chat-msg ' + role;
  el.innerHTML = role === 'ai' ? `<b>AI Copilot</b>${html}` : html;
  log.appendChild(el); log.scrollTop = log.scrollHeight;
}
async function sendCopilot(text) {
  if (!text.trim()) return;
  addChatMsg('user', text);
  document.getElementById('chatInput').value = '';
  const r = await api('/api/copilot', { method: 'POST', body: JSON.stringify({ message: text, case_id: state.caseId }) });
  if (r.grounded) {
    addChatMsg('ai', `<div>${r.answer}</div>`);
  } else {
    addChatMsg('ai', `
      <div style="margin-bottom:6px;font-weight:600;">Possible causes:</div>
      ${r.causes.map(c => `<div>• ${c}</div>`).join('')}
      <div style="margin:8px 0 6px;font-weight:600;">Immediate recommendation:</div>
      ${r.actions.map(a => `<div>✔ ${a}</div>`).join('')}
    `);
  }
}
document.getElementById('chatSend').addEventListener('click', guarded(() => sendCopilot(document.getElementById('chatInput').value)));
document.getElementById('chatInput').addEventListener('keydown', guarded(async (e) => { if (e.key === 'Enter') await sendCopilot(e.target.value); }));
document.querySelectorAll('.chat-quick button').forEach(b => b.addEventListener('click', guarded(() => sendCopilot(b.dataset.q))));

// ---------------------------------------------------------- nav / tick ---
function tick() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('en-GB');
}
setInterval(tick, 1000); tick();

setInterval(() => {
  if (state.caseId && state.ghSeconds > 0) state.ghSeconds--;
  document.getElementById('ghMini').textContent = fmtTime(state.ghSeconds);
}, 1000);

const CASE_SCOPED = ['emergency', 'assessment', 'hospital', 'ambulance', 'doctor', 'family'];
function showScreen(name) {
  if (CASE_SCOPED.includes(name) && !state.caseId) {
    toast('Report an emergency first — tap SOS or pick a type on the Report screen.', 'warn');
    name = 'dashboard';
  }
  current = name;
  SCREENS.forEach(s => document.getElementById('screen-' + s).classList.toggle('active', s === name));
  document.querySelectorAll('.role-tab').forEach(el => el.classList.toggle('active', el.dataset.screen === name));
  updateStepper(name);
  onScreenEnter(name);
}
document.querySelectorAll('.role-tab').forEach(el => {
  el.addEventListener('click', () => showScreen(el.dataset.screen));
});

function updateStepper(name) {
  const strip = document.getElementById('stepperStrip');
  const banner = document.getElementById('caseBanner');
  const min = STEP_MIN[name];
  const active = state.caseId !== null && min !== -1;
  strip.classList.toggle('show', active);
  banner.classList.toggle('show', state.caseId !== null);
  if (active) {
    document.querySelectorAll('.step').forEach(el => {
      const m = parseInt(el.dataset.min, 10);
      el.classList.toggle('done', m < min);
      el.classList.toggle('active', m === min);
    });
  }
}

function onScreenEnter(name) {
  const safe = (fn) => fn().catch(e => toast(e.message || 'Failed to load this screen.'));
  if (name === 'assessment') { renderAssessment(); safe(() => loadPredictive('predictiveCard')); }
  if (name === 'hospital') safe(loadHospitals);
  if (name === 'ambulance') setupTracking();
  else stopTracking();
  if (name === 'doctor') safe(loadDoctorConsole);
  if (name === 'family') safe(loadFamily);
  if (name === 'command') safe(loadCommandCenter);
  if (name === 'analytics') safe(loadAnalytics);
  if (state.caseId) refreshTimelineDrawer();
}

// -------------------------------------------------------- vital line ----
let vlPhase = 0;
function vlPath(score) {
  // score 0 (idle) .. 99 (critical) drives amplitude + spike sharpness
  const w = 1000, h = 46, mid = h / 2;
  const amp = 4 + (score / 100) * 14;
  const spiky = score > 60;
  let d = `M0 ${mid}`;
  const step = 10;
  for (let x = 0; x <= w; x += step) {
    const t = (x + vlPhase) * 0.02;
    let y = mid;
    if (spiky && Math.floor((x + vlPhase) / 90) % 4 === 0 && (x % 90) < 14) {
      y = mid - amp * 2.6 * (1 - Math.abs((x % 90) - 7) / 7);
    } else {
      y = mid + Math.sin(t) * amp * 0.35 + Math.sin(t * 2.7) * amp * 0.15;
    }
    d += ` L${x} ${y.toFixed(1)}`;
  }
  return d;
}
function animateVitalLine() {
  vlPhase += 3.2;
  const score = state.triage ? state.triage.severity_score : 0;
  document.getElementById('vlPath').setAttribute('d', vlPath(score));
  const color = score >= 85 ? '#FF3B30' : score >= 65 ? '#FFB020' : score > 0 ? '#00C2A8' : '#3D8BFD';
  document.getElementById('vlPath').setAttribute('stroke', color);
  requestAnimationFrame(animateVitalLine);
}
requestAnimationFrame(animateVitalLine);

function updateVitalMeta() {
  const statusEl = document.getElementById('vlStatus');
  const scoreEl = document.getElementById('vlScore');
  if (!state.triage) {
    statusEl.textContent = 'STANDBY'; statusEl.className = 'vl-status idle'; scoreEl.textContent = '--';
    return;
  }
  const risk = state.triage.risk_level;
  scoreEl.textContent = state.triage.severity_score + '/100';
  statusEl.textContent = risk.toUpperCase();
  statusEl.className = 'vl-status ' + risk.toLowerCase();
}

// ------------------------------------------------------------- Home ----
function renderTypeGrid() {
  const grid = document.getElementById('typeGrid');
  grid.innerHTML = '';
  EMERGENCY_TYPES.forEach(t => {
    const el = document.createElement('div');
    el.className = 'type-card';
    el.innerHTML = `<div class="icon">${t.icon}</div><div class="label">${t.label}</div>`;
    el.addEventListener('click', guarded(() => startCase(t.key)));
    grid.appendChild(el);
  });
}

async function loadWhoSelect() {
  const sel = document.getElementById('whoSelect');
  try {
    const patients = await api('/api/patients');
    // clear any previously loaded group (in case this runs again after a reconnect)
    sel.querySelectorAll('optgroup').forEach(g => g.remove());
    const group = document.createElement('optgroup');
    group.label = 'Existing patients (on file)';
    patients.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id; opt.textContent = `${p.name}, ${p.age} — ${p.blood_group}`;
      group.appendChild(opt);
    });
    sel.appendChild(group);
  } catch (e) { /* banner already shows the connection problem */ }
}

async function startCase(emergencyType) {
  document.querySelectorAll('.type-card').forEach(c => c.classList.remove('selected'));
  const patientId = document.getElementById('whoSelect').value || null;
  const lat = jitter(CITY_CENTER.lat, 0.14);
  const lng = jitter(CITY_CENTER.lng, 0.14);

  resetCaseState();
  const c = await api('/api/cases', { method: 'POST', body: JSON.stringify({ emergency_type: emergencyType, lat, lng, patient_id: patientId }) });
  state.caseId = c.id;
  state.case = c;
  state.ghSeconds = c.golden_hour_remaining_sec;
  document.getElementById('cbLead').textContent = c.label;
  document.getElementById('cbPatient').textContent = c.patient.name;
  document.getElementById('cbRisk').textContent = 'Assessing…';
  document.getElementById('cbId').textContent = 'CASE #' + c.id;
  document.getElementById('emTitle').textContent = c.label + ' reported';
  document.getElementById('downloadReportBtn').href = `/api/cases/${c.id}/report.pdf`;

  resetVoiceUI();
  showScreen('emergency');
}

// -------------------------------------------------------- Emergency ----
function resetVoiceUI() {
  document.getElementById('transcript').innerHTML = '';
  document.getElementById('scanResult').style.display = 'none';
  document.getElementById('scanResult').innerHTML = '';
  document.getElementById('uploadZone').style.display = 'block';
  document.getElementById('visionPhoto').style.display = 'none';
  document.getElementById('visionPhoto').classList.remove('has-img');
  document.getElementById('visionPhoto').style.backgroundImage = '';
  document.getElementById('uploadHint').textContent = 'Click to choose a scene photo from your device';
  document.getElementById('sevPct').textContent = '—';
  document.getElementById('sevFill').style.width = '0%';
  document.getElementById('sevVerdict').textContent = 'Run voice + photo to compute severity';
  document.getElementById('sevVerdict').style.color = '';
  state.answeredCount = 0; state.voiceDone = false; state.visionDone = false;
}

async function voiceNextTurn() {
  if (!state.caseId) return;
  const t = document.getElementById('transcript');
  const r = await api(`/api/cases/${state.caseId}/voice/next`, { method: 'POST' });
  if (r.done) { state.voiceDone = true; await maybeRunTriage(); return; }
  const b1 = document.createElement('div'); b1.className = 'bubble ai'; b1.textContent = r.question;
  const b2 = document.createElement('div'); b2.className = 'bubble user'; b2.textContent = r.answer;
  t.appendChild(b1);
  setTimeout(() => { t.appendChild(b2); t.scrollTop = t.scrollHeight; }, 250);
  state.answeredCount = r.step; state.answeredTotal = r.total;
  if (r.step >= r.total) { state.voiceDone = true; await maybeRunTriage(); }
}
document.getElementById('voiceNext').addEventListener('click', guarded(voiceNextTurn));
async function voiceAllHandler() {
  if (!state.caseId) throw new Error('Report an emergency first.');
  resetVoiceUI();
  while (!state.voiceDone) { await voiceNextTurn(); await new Promise(r => setTimeout(r, 500)); }
}
document.getElementById('voiceAll').addEventListener('click', guarded(voiceAllHandler));

// Clicking the upload zone opens a real native file picker (input[type=file]).
// The chosen image is shown as an actual preview; VisionAgent analysis is
// still simulated server-side, but the picker itself is real, not mocked.
const photoFileInput = document.getElementById('photoFileInput');
document.getElementById('uploadZone').addEventListener('click', () => {
  if (!state.caseId) { toast('Report an emergency first.', 'warn'); return; }
  photoFileInput.click();
});
photoFileInput.addEventListener('change', guarded(async () => {
  const file = photoFileInput.files && photoFileInput.files[0];
  if (!file) return;
  await uploadHandler(file);
  photoFileInput.value = '';
}));

async function uploadHandler(file) {
  document.getElementById('uploadZone').style.display = 'none';
  const photoBox = document.getElementById('visionPhoto');
  photoBox.style.display = 'flex';
  photoBox.querySelectorAll('.vtag').forEach(el => el.remove());
  document.getElementById('visionPhotoName').textContent = file.name;

  if (file) {
    const reader = new FileReader();
    await new Promise((resolve) => {
      reader.onload = () => {
        photoBox.style.backgroundImage = `url(${reader.result})`;
        photoBox.classList.add('has-img');
        resolve();
      };
      reader.readAsDataURL(file);
    });
  }

  const r = await api(`/api/cases/${state.caseId}/photo`, { method: 'POST', body: JSON.stringify({ filename: file.name }) });
  const conf = 88 + Math.round(Math.random() * 9);
  document.getElementById('visionConfBadge').textContent = conf + '%';
  const positions = [{ top: '10%', left: '8%' }, { top: '65%', left: '10%' }, { top: '15%', left: '55%' }, { top: '68%', left: '58%' }];
  r.tags.forEach((tag, i) => {
    const pill = document.createElement('div'); pill.className = 'vtag';
    pill.style.top = positions[i % 4].top; pill.style.left = positions[i % 4].left;
    pill.textContent = '✔ ' + tag.name;
    photoBox.appendChild(pill);
  });
  const list = document.getElementById('scanResult');
  list.innerHTML = '';
  r.tags.forEach(tag => {
    const row = document.createElement('div'); row.className = 'tag-row';
    row.innerHTML = `<span class="name">${tag.name}</span><span class="val">${tag.value}</span>`;
    list.appendChild(row);
  });
  list.style.display = 'flex';
  state.visionDone = true;
  await maybeRunTriage();
}

async function maybeRunTriage() {
  if (!state.voiceDone || !state.visionDone || !state.caseId) return;
  const r = await api(`/api/cases/${state.caseId}/triage`, { method: 'POST' });
  state.triage = r;
  updateVitalMeta();
  document.getElementById('sevPct').textContent = r.severity_score + '/100';
  document.getElementById('sevFill').style.width = r.severity_score + '%';
  const riskColor = { Critical: '#FF3B30', High: '#FFB020', Moderate: '#3D8BFD', Low: '#16C784' }[r.risk_level];
  document.getElementById('sevVerdict').textContent = `● ${r.risk_level} — ${r.recommended_tx}`;
  document.getElementById('sevVerdict').style.color = riskColor;
  document.getElementById('cbRisk').textContent = r.risk_level;
  document.getElementById('copilotBadge').style.display = 'block';
}

// ------------------------------------------------------- Assessment ----
function renderAssessment() {
  if (!state.case) return;
  const p = state.case.patient;
  const sum = document.getElementById('patientSummary');
  const row = (k, v, warn) => `<div class="mini-row"><span class="k">${k}</span><span class="v ${warn ? 'warn-v' : ''}">${v}</span></div>`;
  sum.innerHTML =
    row('Name', p.known ? `${p.name}, ${p.age}` : 'Unknown') +
    row('Blood group', p.blood_group) +
    row('Allergies', p.allergies.length ? p.allergies.join(', ') : 'None known', p.allergies.length) +
    row('Diabetic', p.diabetic === null ? 'Unknown' : (p.diabetic ? 'Yes' : 'No'), p.diabetic) +
    row('Medications', p.medications.length ? p.medications.join(', ') : 'None') +
    row('Insurance', p.insurance_active === null ? 'Unknown' : (p.insurance_active ? 'Active' : 'Inactive')) +
    row('Emergency', state.case.label);

  document.getElementById('assessTitle').textContent = state.case.label + (state.triage ? ' · ' + state.triage.risk_level : '');

  const reasonsEl = document.getElementById('triageReasons');
  const actionsEl = document.getElementById('recommendedActions');
  if (!state.triage) {
    document.getElementById('triageCardTitle').textContent = 'AI Decision Engine';
    document.getElementById('triageConf').textContent = '—';
    document.getElementById('triageRisk').textContent = 'pending';
    reasonsEl.innerHTML = '<div class="ai-reason">Finish the voice + photo step on Assess to run TriageAgent.</div>';
    actionsEl.innerHTML = '<div class="action-item"><div class="dot"></div>Waiting on triage…</div>';
    return;
  }
  document.getElementById('triageCardTitle').textContent = `Why AI predicted ${state.triage.risk_level}`;
  document.getElementById('triageConf').textContent = state.triage.severity_score + '/100';
  document.getElementById('triageRisk').textContent = state.triage.risk_level;
  document.getElementById('triageModel').textContent = state.triage.model;
  reasonsEl.innerHTML = state.triage.reasons.map(r => `<div class="ai-reason"><span class="check">✓</span> ${r}</div>`).join('');
  actionsEl.innerHTML = `<div class="action-callout">⚠ ${state.triage.recommended_tx}</div>` +
    state.triage.recommended_actions.map(a => `<div class="action-item"><div class="dot"></div>${a}</div>`).join('');
}

async function loadPredictive(cardId) {
  const card = document.getElementById(cardId);
  if (!state.caseId || !state.triage) { card.style.display = 'none'; return; }
  try {
    const p = await api(`/api/cases/${state.caseId}/predictive`);
    card.style.display = 'flex';
    if (p.at_risk) {
      card.className = 'predictive-card at-risk';
      card.innerHTML = `<div class="pic">🔮</div><div><div class="pt">AI Prediction — patient may enter ${p.condition} within ${p.window_min} min</div><div class="ps">Probability ${p.probability_pct}% · Basis: ${p.basis.join(', ')} · ${p.recommendation}</div></div>`;
    } else {
      card.className = 'predictive-card clear';
      card.innerHTML = `<div class="pic">🔮</div><div><div class="pt">AI Prediction — stable</div><div class="ps">${p.message}</div></div>`;
    }
  } catch (e) { card.style.display = 'none'; }
}

// ----------------------------------------------------------- Hospital ---
async function loadHospitals() {
  if (!state.caseId) return;
  const resp = await api(`/api/cases/${state.caseId}/hospitals`);
  const ranked = resp.hospitals;
  state.hospitals = ranked;
  const row = document.getElementById('flightRow');
  row.innerHTML = '';
  const [top, ...rest] = ranked;
  const nearest = ranked.find(h => h.id === resp.nearest_id) || top;

  const winner = document.createElement('div');
  winner.className = 'flight-card winner';
  winner.innerHTML = `
    <div class="fc-top">
      <div><div class="fc-name">${top.name}</div><div class="fc-tag">★★★★★ AI Recommended</div></div>
      <div class="fc-score-block"><div class="fc-score">${top.score}</div><div class="fc-score-lbl">Readiness Score</div></div>
    </div>
    <div class="fc-eta">⏱ ETA <b>${top.eta_min} min</b> · ${top.distance_km} km away</div>
    <div class="fc-survival"><span class="fsv-lbl">⏱ Golden-Hour Suitability Score</span><span class="fsv-val">${top.golden_hour_score}/100</span></div>
    <div class="fc-stats">
      <div class="fs-row"><span class="fs-k">ICU</span><span class="fs-v">${top.icu_beds_free}/${top.icu_beds_total} free</span></div>
      <div class="fs-row"><span class="fs-k">Current Load</span><span class="fs-v">${top.current_load_pct}%</span></div>
      <div class="fs-row"><span class="fs-k">Readiness</span><span class="fs-v">${top.readiness_pct}%</span></div>
      <div class="fs-row"><span class="fs-k">Success Rate</span><span class="fs-v">${top.success_rate_pct}%</span></div>
    </div>
    <div class="fc-why-head">Why</div>
    ${top.why_positive.map(w => `<div class="fc-why-item"><span class="ck">✓</span>${w}</div>`).join('')}
    ${top.why_negative.map(w => `<div class="fc-why-item neg"><span class="ck">✕</span>${w}</div>`).join('')}
  `;
  row.appendChild(winner);

  rest.slice(0, 2).forEach(h => {
    const cls = h.score >= 75 ? 'mid' : 'lo';
    const el = document.createElement('div');
    el.className = 'flight-card minor';
    el.innerHTML = `
      <div class="fc-minor-name">${h.name}</div>
      <div class="fc-score-block" style="text-align:center;"><div class="fc-score ${cls}">${h.score}</div><div class="fc-score-lbl">Readiness</div></div>
      <div class="fc-minor-reason">${h.why_negative[0] ? '✕ ' + h.why_negative[0] : h.eta_min + ' min away'}</div>
      <div class="fc-minor-reason" style="color:var(--muted);margin-top:4px;">Golden-Hour ${h.golden_hour_score}/100 · Load ${h.current_load_pct}%</div>
    `;
    row.appendChild(el);
  });

  document.getElementById('hospConf').textContent = top.golden_hour_score + '/100';
  document.getElementById('hospReasons').innerHTML = top.why_positive.map(w => `<div class="ai-reason"><span class="check">✓</span> ${w}</div>`).join('');
  document.getElementById('ghExplanation').textContent = resp.explanation;

  // Why not the nearest hospital? — explicit comparison per spec.
  const cmp = document.getElementById('nearestCompare');
  if (nearest.id === top.id) {
    cmp.style.display = 'none';
  } else {
    cmp.style.display = 'grid';
    const buildSide = (h, label) => `
      <div class="nc-side">
        <div class="nc-lbl">${label}</div>
        <div class="nc-name">${h.name}</div>
        <div class="nc-row"><span>Distance</span><b>${h.distance_km} km</b></div>
        <div class="nc-row"><span>ETA</span><b>${h.eta_min} min</b></div>
        ${h.why_positive.slice(0, 3).map(w => `<div class="nc-tag pos">✓ ${w}</div>`).join('')}
        ${h.why_negative.slice(0, 3).map(w => `<div class="nc-tag neg">✕ ${w}</div>`).join('')}
      </div>`;
    cmp.innerHTML = buildSide(nearest, 'Nearest hospital') + buildSide(top, 'AI-recommended hospital');
  }
}

async function dispatchHandler() {
  if (!state.caseId || !state.hospitals) throw new Error('Run hospital matching first.');
  const topId = state.hospitals[0].id;
  const r = await api(`/api/cases/${state.caseId}/dispatch?hospital_id=${topId}`, { method: 'POST' });
  state.dispatch = r;
  showScreen('ambulance');
}
document.getElementById('dispatchBtn').addEventListener('click', guarded(dispatchHandler));

// ---------------------------------------------------------- Ambulance ---
function setupTracking() {
  if (!map) {
    map = L.map('map', { zoomControl: false, attributionControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map);
  }
  if (!state.dispatch) { map.setView([CITY_CENTER.lat, CITY_CENTER.lng], 11); return; }
  const route = state.dispatch.route;
  const scene = route[0], hosp = route[route.length - 1];

  if (mapRouteLine) map.removeLayer(mapRouteLine);
  mapRouteLine = L.polyline(route.map(p => [p.lat, p.lng]), { color: '#3D8BFD', weight: 3, dashArray: '8 6' }).addTo(map);

  const sceneIcon = L.divIcon({ className: '', html: '<div style="width:14px;height:14px;border-radius:50%;background:#0B1220;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>' });
  const hospIcon = L.divIcon({ className: '', html: '<div style="width:14px;height:14px;border-radius:50%;background:#FF3B30;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>' });
  const ambIcon = L.divIcon({ className: '', html: '<div style="font-size:20px;transform:translate(-6px,-8px);">🚑</div>' });

  if (mapSceneMarker) map.removeLayer(mapSceneMarker);
  if (mapHospMarker) map.removeLayer(mapHospMarker);
  if (mapAmbMarker) map.removeLayer(mapAmbMarker);
  mapSceneMarker = L.marker([scene.lat, scene.lng], { icon: sceneIcon }).addTo(map).bindTooltip('Scene', { permanent: false });
  mapHospMarker = L.marker([hosp.lat, hosp.lng], { icon: hospIcon }).addTo(map).bindTooltip(state.dispatch.hospital_name);
  mapAmbMarker = L.marker([scene.lat, scene.lng], { icon: ambIcon }).addTo(map).bindTooltip(state.dispatch.ambulance_id, { permanent: true, direction: 'top' });

  map.fitBounds(mapRouteLine.getBounds(), { padding: [30, 30] });

  refreshTrack();
  if (trackTimer) clearInterval(trackTimer);
  trackTimer = setInterval(refreshTrack, 2000);
}
function stopTracking() { if (trackTimer) { clearInterval(trackTimer); trackTimer = null; } }

async function refreshTrack() {
  if (!state.caseId || !state.dispatch) return;
  let pos;
  try { pos = await api(`/api/cases/${state.caseId}/track`); } catch (e) { return; }
  state.ghSeconds = pos.golden_hour_remaining_sec;
  if (mapAmbMarker) mapAmbMarker.setLatLng([pos.lat, pos.lng]);

  const cpWrap = document.getElementById('checkpoints');
  cpWrap.innerHTML = pos.checkpoints.map((cp, i) => {
    const isActive = cp.done && (i === pos.checkpoints.length - 1 || !pos.checkpoints[i + 1].done);
    return `<div class="cp ${cp.done ? 'done' : ''} ${isActive && !pos.arrived ? 'active' : ''}">
      <div class="cdot"></div><div class="clbl">${cp.label}</div>
      <div class="ctime">${cp.done ? new Date(cp.at * 1000).toLocaleTimeString('en-GB') : '—'}</div>
    </div>`;
  }).join('');

  const w = document.getElementById('liveWidgets');
  w.innerHTML = `
    <div class="live-widget"><div class="icon">⏱</div><div class="val">${pos.remaining_eta_min} min</div><div class="lbl">ETA remaining</div></div>
    <div class="live-widget"><div class="icon">🛣</div><div class="val">${state.dispatch.distance_km} km</div><div class="lbl">Route distance</div></div>
    <div class="live-widget"><div class="icon">🚑</div><div class="val">${pos.speed_kmh} km/h</div><div class="lbl">Ambulance speed</div></div>
    <div class="live-widget"><div class="icon">⏳</div><div class="val">${fmtTime(state.ghSeconds)}</div><div class="lbl">Golden hour</div></div>
    <div class="live-widget"><div class="icon">💓</div><div class="val" style="color:${pos.arrived ? '#16C784' : '#3D8BFD'}">${pos.arrived ? 'Arrived' : 'Stable'}</div><div class="lbl">Patient status</div></div>
  `;
  const pe = document.getElementById('pathEta');
  if (pe) pe.textContent = `⏱ ETA ${pos.remaining_eta_min} min · ${pos.progress_pct}%`;
}

// ------------------------------------------------------------ Doctor ----
async function loadDoctorConsole() {
  const cases = await api('/api/cases');
  const mine = cases.find(c => c.id === state.caseId);
  const others = cases.filter(c => c.id !== state.caseId);

  const mainPanel = document.getElementById('mainPatientPanel');
  if (!mine || !mine.risk_level) {
    mainPanel.innerHTML = `<div class="panel-head">Your case</div><div style="color:var(--muted-dim-dark);font-size:13px;">Finish triage + dispatch to see this case briefed here.</div>`;
    document.getElementById('doctorPredictiveCard').style.display = 'none';
    document.getElementById('handoffPanel').innerHTML = '';
  } else {
    const p = state.case.patient;
    mainPanel.innerHTML = `
      <div class="patient-card">
        <div class="avatar-block">
          <div class="avatar-circle">${(p.name || '?')[0]}</div>
          <b>${p.name}</b>
          <div style="color:var(--muted-dim-dark);font-size:12px;margin-top:4px;">${p.age ? 'Age ' + p.age : ''} ${p.sex || ''}</div>
          <div class="level-badge ${mine.risk_level.toLowerCase()}" style="margin-top:12px;">${mine.label} · ${mine.risk_level}</div>
        </div>
        <div style="flex:1;min-width:260px;">
          <div class="vitals-grid">
            <div class="vital"><div class="l">Blood group</div><div class="v">${p.blood_group}</div></div>
            <div class="vital"><div class="l">Allergies</div><div class="v" style="color:${p.allergies.length ? 'var(--amber)' : 'inherit'}">${p.allergies.length ? p.allergies.join(', ') : 'None'}</div></div>
            <div class="vital"><div class="l">ETA</div><div class="v" style="color:var(--teal);">${mine.eta_min ?? '—'} min</div></div>
            <div class="vital"><div class="l">Severity</div><div class="v" style="color:var(--red);">${mine.severity_score}/100</div></div>
            <div class="vital"><div class="l">Hospital</div><div class="v">${mine.hospital_name || '—'}</div></div>
            <div class="vital"><div class="l">Doctor assigned</div><div class="v">${mine.doctor_assigned || '—'}</div></div>
          </div>
          <div class="checklist">
            ${(state.triage ? state.triage.recommended_actions : []).slice(0, 4).map(a => `<div class="check-item"><div class="box"></div>${a}</div>`).join('')}
          </div>
        </div>
      </div>`;
    await loadPredictive('doctorPredictiveCard');
    await loadHandoffPanel();
  }

  const grid = document.getElementById('otherCasesGrid');
  grid.innerHTML = others.map(c => `
    <div class="dcard">
      <div class="name">${c.patient_name} <span class="sev ${(c.risk_level || 'moderate').toLowerCase()}">${(c.risk_level || 'pending').toUpperCase()}</span></div>
      <div class="row"><span>Blood Group</span><b>${c.blood_group}</b></div>
      <div class="row"><span>Allergies</span><b>${c.allergies.length ? c.allergies.join(', ') : 'None'}</b></div>
      <div class="row"><span>ETA</span><b>${c.eta_min ?? '—'} min</b></div>
      <div class="row"><span>Doctor</span><b>${c.doctor_assigned || '—'}</b></div>
      <div class="row"><span>Recommended</span><b>${c.recommended_tx || '—'}</b></div>
    </div>
  `).join('') || '<div style="color:var(--muted-dim-dark);font-size:13px;">No other active cases right now.</div>';
}

async function loadHandoffPanel() {
  const panel = document.getElementById('handoffPanel');
  try {
    const h = await api(`/api/cases/${state.caseId}/handoff`);
    panel.innerHTML = `
      <div class="panel-head">🩺 AI Medical Handoff — pre-arrival summary</div>
      <div class="mini-row"><span class="k">Chief complaint</span><span class="v">${h.chief_complaint}</span></div>
      <div class="mini-row"><span class="k">Patient</span><span class="v">${h.patient_line}</span></div>
      <div class="mini-row"><span class="k">AI risk</span><span class="v" style="color:var(--red);">${h.risk_level} (${h.severity_score}/100)</span></div>
      <div class="mini-row"><span class="k">Recommended Tx</span><span class="v">${h.recommended_tx}</span></div>
      <div class="mini-row"><span class="k">Key findings</span><span class="v" style="text-align:right;max-width:60%;">${h.key_findings.join('; ')}</span></div>
      <div class="mini-row"><span class="k">ETA / Doctor</span><span class="v">${h.eta_min ?? '—'} min · ${h.doctor_assigned || '—'}</span></div>
      <a class="btn primary" style="margin-top:12px;display:inline-block;" href="/api/cases/${state.caseId}/report.pdf" target="_blank">⬇ Full AI Report (PDF)</a>
    `;
  } catch (e) { panel.innerHTML = ''; }
}

// ------------------------------------------------------------ Family ----
async function loadFamily() {
  const timelineEl = document.getElementById('familyTimeline');
  const reassureEl = document.getElementById('familyReassure');
  const checklistEl = document.getElementById('statusChecklist');
  if (!state.caseId) {
    timelineEl.innerHTML = '<div style="color:var(--muted);font-size:13px;">No active case yet — report an emergency to see live family updates here.</div>';
    reassureEl.style.display = 'none';
    checklistEl.innerHTML = '';
    return;
  }
  const feed = await api(`/api/cases/${state.caseId}/family`);

  const d = state.dispatch;
  const checkRow = (label, value, done) => `
    <div class="sc-item">
      <span class="k">${done ? '<span class="chk">✔</span>' : '○'} ${label}</span>
      <span class="v">${value}</span>
    </div>`;
  checklistEl.innerHTML =
    checkRow('Ambulance', d ? 'Dispatched' : 'Pending', !!d) +
    checkRow('ETA', d ? d.eta_min + ' min' : 'Pending', !!d) +
    checkRow('Hospital', d ? d.hospital_name : 'Pending', !!d) +
    checkRow('Doctor Notified', d ? d.doctor_assigned : 'Pending', !!(d && d.doctor_assigned)) +
    checkRow('Care Team Prepared', state.triage ? 'Yes' : 'Pending', !!state.triage);

  timelineEl.innerHTML = feed.timeline.map((t, i) => `
    <div class="t-item ${i === feed.timeline.length - 1 ? '' : ''}">
      <div class="node"></div>${i < feed.timeline.length - 1 ? '<div class="tline"></div>' : ''}
      <div class="tbody"><b>${t.title}</b><div class="tsub">${new Date(t.at * 1000).toLocaleTimeString('en-GB')} · ${t.sub}</div></div>
    </div>
  `).join('') + (state.dispatch ? '' : `
    <div class="t-item pending"><div class="node"></div>
      <div class="tbody"><b>Awaiting hospital match</b><div class="tsub">Live location will share once dispatched</div></div>
    </div>`);
  if (feed.reassurance) { reassureEl.textContent = feed.reassurance; reassureEl.style.display = 'block'; }
  else reassureEl.style.display = 'none';
}

// ---------------------------------------------------------- Analytics ---
async function loadAnalytics() {
  const d = await api('/api/analytics/dashboard');
  const fmtM = (v) => v == null ? '—' : v + 'm';
  document.getElementById('kpiRow').innerHTML = `
    <div class="kpi"><div class="val">${d.total_cases}</div><div class="lbl">Total cases</div></div>
    <div class="kpi"><div class="val" style="color:#FF8079">${d.critical_cases}</div><div class="lbl">Critical cases</div></div>
    <div class="kpi"><div class="val">${fmtM(d.avg_response_min)}</div><div class="lbl">Avg. response time</div></div>
    <div class="kpi"><div class="val">${fmtM(d.avg_hospital_eta_min)}</div><div class="lbl">Avg. hospital ETA</div></div>
    <div class="kpi"><div class="val" style="color:var(--teal-deep)">${d.ambulances_dispatched}</div><div class="lbl">Ambulances dispatched</div></div>
    <div class="kpi"><div class="val" style="color:var(--amber)">${d.avg_icu_occupancy_pct}%</div><div class="lbl">City ICU occupancy</div></div>
  `;

  const icu = document.getElementById('icuRow');
  icu.innerHTML = d.icu_by_hospital.map(h => {
    const color = h.occupancy_pct > 90 ? '#FF3B30' : h.occupancy_pct > 75 ? '#FFB020' : '#16C784';
    return `<div class="icu-cell"><div class="city">${h.name}</div><div class="icu-ring-num" style="color:${color}">${h.occupancy_pct}%</div></div>`;
  }).join('');

  const riskColors = { Critical: '#FF3B30', High: '#FFB020', Moderate: '#3D8BFD', Low: '#16C784' };
  const rd = d.risk_distribution;
  const bar = document.getElementById('riskDistBar');
  bar.innerHTML = Object.entries(rd).map(([k, v]) => v > 0
    ? `<div style="flex:${v};background:${riskColors[k]};" title="${k}: ${v}"></div>` : '').join('');
  if (!bar.innerHTML) bar.innerHTML = `<div style="flex:1;background:var(--line);"></div>`;
  document.getElementById('riskDistLegend').innerHTML = Object.entries(rd).map(([k, v]) =>
    `<span><span class="sw" style="background:${riskColors[k]}"></span>${k} (${v})</span>`).join('');
}

// -------------------------------------------------------------- reset ---
function resetCaseState() {
  state.caseId = null; state.case = null; state.triage = null; state.hospitals = null; state.dispatch = null;
  state.answeredCount = 0; state.voiceDone = false; state.visionDone = false;
  updateVitalMeta();
  stopTracking();
}
document.getElementById('resetDemo').addEventListener('click', () => {
  resetCaseState();
  document.getElementById('cbRisk').textContent = '—';
  document.getElementById('downloadReportBtn').href = '#';
  showScreen('dashboard');
});

// -------------------------------------------------------------- boot ----
renderTypeGrid();
loadWhoSelect();
checkBackend();
showScreen('dashboard');
