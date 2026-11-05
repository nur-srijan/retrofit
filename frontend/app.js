const $ = id => document.getElementById(id);
const SERIES_COLORS = ['#e5a83b', '#8ec1b0', '#8fb4d6', '#d69ab0'];
let instruments = [], series = {}, ws;

function esc(s){ return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function colorFor(id){ const i = instruments.findIndex(x => x.id === id); return SERIES_COLORS[(i < 0 ? 0 : i) % SERIES_COLORS.length]; }
function frac(inst, v){ const r = inst.range.max - inst.range.min || 1; return Math.max(0, Math.min(1, (v - inst.range.min) / r)); }
function needleAngle(inst, v){ return -120 + frac(inst, v) * 240; }

function log(msg, kind = ''){
  const feed = $('feed'); const empty = feed.querySelector('.empty'); if (empty) empty.remove();
  const row = document.createElement('div'); row.className = 'feed-row' + (kind ? ' ' + kind : '');
  const label = kind === 'alert' ? 'Alert' : kind === 'incident' ? 'Incident' : kind === 'voice' ? 'Voice' : 'Agent';
  row.innerHTML = `<time>${new Date().toLocaleTimeString('en-GB')}</time><span class="kind">${label}</span><span>${esc(msg)}</span>`;
  feed.prepend(row);
}
function status(html){ $('status').innerHTML = html; }
async function api(path, opts = {}){
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!r.ok) throw new Error((await r.text()).slice(0, 300));
  return r.json();
}

async function health(){
  try {
    const h = await api('/api/health');
    const on = h.models.meta_key_present;
    $('badges').innerHTML = [
      ['SAM 3.1', on], ['Muse Spark', on], ['Spark Open', true],
      ['Muse Wonder', on], ['Voice Transcribe', on],
    ].map(([n, ok]) => `<span class="model-status"><span class="dot ${ok ? 'on' : ''}"></span>${n}</span>`).join('');
    status(`<strong>Connected.</strong> Spark Open: ${esc(h.models.spark_open_source)}. ${on ? 'Meta Model API key present.' : 'No Meta key — demo fallback active.'}`);
  } catch (e) { status('Backend unavailable: ' + esc(e.message)); }
}

function dialSVG(inst){
  let ticks = '';
  for (let i = 0; i <= 8; i++){
    const a = (-120 + i * 30) * Math.PI / 180, cx = 60, cy = 62;
    const x1 = cx + 42 * Math.sin(a), y1 = cy - 42 * Math.cos(a), x2 = cx + 48 * Math.sin(a), y2 = cy - 48 * Math.cos(a);
    ticks += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#4a4d45" stroke-width="1.5"/>`;
  }
  return `<svg class="dial" viewBox="0 0 120 78" aria-hidden="true">
    <path d="M 12 62 A 48 48 0 1 1 108 62" fill="none" stroke="#2b2d28" stroke-width="2"/>
    ${ticks}
    <g class="needle" id="needle-${inst.id}" style="transform:rotate(-120deg)"><line x1="60" y1="62" x2="60" y2="22" stroke="${colorFor(inst.id)}" stroke-width="2.5" stroke-linecap="round"/></g>
    <circle cx="60" cy="62" r="4" fill="#eceee8"/>
    <text x="14" y="76" fill="#6f7268" font-size="8">${inst.range.min}</text>
    <text x="98" y="76" fill="#6f7268" font-size="8">${inst.range.max}</text>
  </svg>`;
}
function faceHTML(inst){
  const head = `<div><div class="face-label">${esc(inst.label)}</div><div class="face-meta">${esc(inst.type.replace('_',' '))} · SAM track ${inst.track_id ?? '—'}</div></div>`;
  const value = `<div class="face-value" id="sim-${inst.id}">— <small>${esc(inst.unit)}</small></div>`;
  if (inst.type === 'gauge' || inst.type === 'thermometer') return `<div class="face">${head}${dialSVG(inst)}${value}</div>`;
  if (inst.type === 'digital_display') return `<div class="face">${head}<div class="readout" id="readout-${inst.id}">00.0</div><div class="face-meta">${esc(inst.unit)} elapsed</div></div>`;
  return `<div class="face">${head}<div class="lamp" id="lamp-${inst.id}"></div><div class="lamp-state" id="lampstate-${inst.id}">Off</div>${value}</div>`;
}

function renderInstruments(){
  $('simPanel').innerHTML = instruments.map(faceHTML).join('');
  $('cards').innerHTML = instruments.map(i => `
    <div class="reading">
      <div class="r-label">${esc(i.label)}</div>
      <div class="r-type">${esc(i.type.replace('_',' '))} · ${esc(i.source || '')}</div>
      <div class="r-value" id="val-${i.id}">— <small>${esc(i.unit)}</small></div>
      <div class="r-range">${i.range.min}–${i.range.max} ${esc(i.unit)}</div>
    </div>`).join('');
  $('chartLegend').innerHTML = instruments.map(i =>
    `<span class="legend-item" style="color:${colorFor(i.id)}"><span class="legend-swatch"></span><span style="color:var(--muted)">${esc(i.label)}</span></span>`).join('');
  $('compileList').innerHTML = instruments.map(i =>
    `<button type="button" onclick="compileOne('${i.id}')">Compile: ${esc(i.label)}</button>`).join('');
  drawOverlay();
}

function drawOverlay(){
  const c = $('overlay'), v = $('video'); if (!v.videoWidth) return;
  c.width = v.videoWidth; c.height = v.videoHeight;
  const x = c.getContext('2d'); x.clearRect(0, 0, c.width, c.height);
  if (!instruments.length) return;
  instruments.forEach(i => {
    // SAM 3.1 perception box (this IS instruments[i].bbox) in green
    x.strokeStyle = '#79c98a'; x.lineWidth = 3;
    x.strokeRect(i.bbox.x * c.width, i.bbox.y * c.height, i.bbox.w * c.width, i.bbox.h * c.height);
    // Spark's original classification box, when SAM moved it, in thin amber
    if (i.spark_bbox){
      x.strokeStyle = '#e5a83b'; x.lineWidth = 1;
      x.strokeRect(i.spark_bbox.x * c.width, i.spark_bbox.y * c.height, i.spark_bbox.w * c.width, i.spark_bbox.h * c.height);
    }
    // Spark classification label above the SAM box
    x.fillStyle = '#79c98a'; x.font = '600 17px "DM Sans", sans-serif';
    const last = (series[i.id] || []).slice(-1)[0];
    x.fillText(`${i.label}${last !== undefined ? '  ' + last + ' ' + i.unit : ''}`, i.bbox.x * c.width + 6, Math.max(20, i.bbox.y * c.height - 8));
  });
}

function pushReading(r){
  (series[r.instrument_id] = series[r.instrument_id] || []).push(r.value);
  if (series[r.instrument_id].length > 120) series[r.instrument_id].shift();
  const inst = instruments.find(i => i.id === r.instrument_id); if (!inst) return;
  const val = $('val-' + r.instrument_id); if (val) val.innerHTML = `${esc(r.value)} <small>${esc(r.unit)}</small>`;
  const sim = $('sim-' + r.instrument_id); if (sim && !$('readout-' + r.instrument_id)) sim.innerHTML = `${esc(r.value)} <small>${esc(r.unit)}</small>`;
  const needle = $('needle-' + r.instrument_id); if (needle) needle.style.transform = `rotate(${needleAngle(inst, Number(r.value))}deg)`;
  const readout = $('readout-' + r.instrument_id); if (readout) readout.textContent = Number(r.value).toFixed(1).padStart(4, '0');
  const lamp = $('lamp-' + r.instrument_id), ls = $('lampstate-' + r.instrument_id);
  if (lamp){ const on = Number(r.value) >= 0.5; lamp.classList.toggle('on', on); if (ls) ls.textContent = on ? 'On' : 'Off'; }
  drawChart();
  if ($('video').videoWidth) drawOverlay();
}

function drawChart(){
  const c = $('chart'); if (!c) return;
  const dpr = window.devicePixelRatio || 1, w = c.clientWidth || 900, h = 240;
  if (c.width !== w * dpr){ c.width = w * dpr; c.height = h * dpr; }
  const x = c.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, w, h);
  x.strokeStyle = '#23251f'; x.lineWidth = 1;
  for (let i = 1; i <= 4; i++){ const y = (h / 5) * i; x.beginPath(); x.moveTo(0, y); x.lineTo(w, y); x.stroke(); }
  instruments.forEach(inst => {
    const d = series[inst.id] || []; if (d.length < 2) return;
    x.strokeStyle = colorFor(inst.id); x.lineWidth = 2; x.beginPath();
    d.forEach((v, j) => { const px = d.length > 1 ? j / (d.length - 1) * w : 0, py = h - frac(inst, v) * (h - 16) - 8; j ? x.lineTo(px, py) : x.moveTo(px, py); });
    x.stroke();
  });
}

function connect(){
  ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/stream');
  ws.onmessage = e => {
    const ev = JSON.parse(e.data);
    if (ev.kind === 'reading') pushReading(ev.reading);
    else if (ev.kind === 'alert') log(ev.message, 'alert');
    else if (ev.kind === 'incident') log(`(${ev.source_model || 'agent'}) ${ev.message}`, 'incident');
    else if (ev.kind === 'voice_log') log(ev.transcript, 'voice');
  };
  ws.onclose = () => setTimeout(connect, 1500);
  ws.onerror = () => { try { ws.close(); } catch {} };
}

window.compileOne = async id => {
  const inst = instruments.find(i => i.id === id);
  $('compileOut').innerHTML = '<p class="empty">Muse Spark is writing and verifying the reader…</p>';
  try {
    const c = await api('/api/compile', { method: 'POST', body: JSON.stringify({ instrument: inst }) });
    const v = c.verification;
    $('compileOut').innerHTML = `
      <h3>${esc(id)} · ${esc(c.reader_type)} <span class="by">— generated by ${esc(c.generated_by)}</span></h3>
      <pre>${esc(c.code)}</pre>
      <div class="verify">
        <span>Accuracy <strong>${v.accuracy_pct}%</strong></span>
        <span>MAE <strong>${v.mae}</strong></span>
        <span>Max error <strong>${v.max_error}</strong></span>
        <span class="${v.passed ? 'pass' : 'fail'}">${v.passed ? 'Verified' : 'Failed verification'}</span>
        <span>n = ${v.n} held-out cases</span>
      </div>
      <div class="samples">Self-consistency on held-out synthetic features: ${v.samples.map(s => `${s.expected} → ${s.got}`).join(' · ')}</div>`;
    log(`Reader compiled for ${id} by ${c.generated_by}: ${v.accuracy_pct}% (${v.passed ? 'verified' : 'failed'})`);
  } catch (e) { $('compileOut').innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
};

let frameTimer = null, frameBusy = false;
function stopFrameStream(){ if (frameTimer) clearInterval(frameTimer); frameTimer = null; }
function startFrameStream(){
  stopFrameStream();
  const v = $('video'), c = document.createElement('canvas');
  frameTimer = setInterval(async () => {
    if (frameBusy || !v.videoWidth) return;
    frameBusy = true;
    try {
      const scale = Math.min(1, 640 / v.videoWidth);
      c.width = v.videoWidth * scale; c.height = v.videoHeight * scale;
      c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
      const r = await api('/api/frame', { method: 'POST', body: JSON.stringify({ image: c.toDataURL('image/jpeg', 0.7) }) });
      if (r.readings && r.readings.length) status(`<strong>Live camera.</strong> Reading ${r.readings.length} instruments from pixels at ~4 FPS (compiled readers, no per-frame model calls).`);
    } catch (e) { /* transient frame failure: next tick retries */ }
    frameBusy = false;
  }, 250);
}
$('camBtn').onclick = async () => {
  try {
    const s = await navigator.mediaDevices.getUserMedia({ video: true });
    $('video').srcObject = s; $('simPanel').style.display = 'none';
    log('Camera started - streaming frames to /api/frame (features extracted from pixels)');
    startFrameStream();
  } catch (e) { status('Camera unavailable: ' + esc(e.message) + ' — the demo panel works without one.'); }
};
$('detectBtn').onclick = async () => {
  const v = $('video'); let img = '';
  if (v.videoWidth){
    const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext('2d').drawImage(v, 0, 0); img = c.toDataURL('image/jpeg', 0.8);
  }
  status('<strong>Detecting…</strong> SAM 3.1 segmentation, then Muse Spark classification and calibration.');
  try {
    const r = await api('/api/detect', { method: 'POST', body: JSON.stringify({ image: img }) });
    instruments = r.instruments; renderInstruments();
    if (!instruments.length) {
      drawOverlay();
      status('<strong>No instruments found in frame.</strong> Point camera directly at a gauge, thermometer, or indicator light.');
      log('No instruments detected in camera frame', 'incident');
      return;
    }
    const sam = instruments[0]?.sam_boxes ?? 0;
    status(`<strong>Detected ${instruments.length} instruments</strong> via ${esc(r.source)}. SAM 3.1 boxes: ${sam}${sam === 0 && r.source !== 'demo-fallback' ? ' — SAM returned none, so Spark vision carried detection (disclosed fallback)' : ''}.`);
    log(`Detected ${instruments.length} instruments via ${r.source} (SAM boxes: ${sam})`);
  } catch (e) { status(esc(e.message)); }
};
$('demoBtn').onclick = async () => {
  stopFrameStream();
  if (!instruments.length || instruments[0]?.source === "none-detected"){
    const r = await api('/api/detect', { method: 'POST', body: JSON.stringify({ image: '' }) });
    instruments = r.instruments; renderInstruments();
  }
  await api('/api/demo/start', { method: 'POST', body: '{}' });
  $('demoBadge').classList.remove('hidden'); $('simPanel').style.display = 'grid';
  status('<strong>Demo panel live.</strong> Readings stream through the compiled readers.');
  log('Demo panel started');
};
$('stopBtn').onclick = async () => {
  stopFrameStream(); const v=$('video'); if(v.srcObject){v.srcObject.getTracks().forEach(tr=>tr.stop()); v.srcObject=null; $('simPanel').style.display='grid';}
  await api('/api/demo/stop', { method: 'POST', body: '{}' });
  $('demoBadge').classList.add('hidden'); log('Stream stopped');
};
$('ruleBtn').onclick = async () => {
  try {
    const r = await api('/api/rules', { method: 'POST', body: JSON.stringify({ text: $('ruleText').value }) });
    const d = document.createElement('div'); d.className = 'chip';
    d.innerHTML = `<span class="predicate">${esc(r.instrument_id)} ${esc(r.op)} ${esc(r.threshold)}</span> — “${esc(r.text)}”<small>Compiled by ${esc(r.source_model)}</small>`;
    $('rules').appendChild(d);
    log(`Rule compiled by ${r.source_model}: ${r.instrument_id} ${r.op} ${r.threshold}`);
  } catch (e) { status(esc(e.message)); }
};

let mediaRec = null, chunks = [];
$('voiceBtn').onclick = async () => {
  if (mediaRec && mediaRec.state === 'recording'){ mediaRec.stop(); $('voiceBtn').textContent = 'Record'; return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRec = new MediaRecorder(stream); chunks = [];
    mediaRec.ondataavailable = e => chunks.push(e.data);
    mediaRec.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const buf = new Uint8Array(await blob.arrayBuffer());
      let bin = ''; buf.forEach(b => bin += String.fromCharCode(b));
      try {
        const r = await api('/api/voice', { method: 'POST', body: JSON.stringify({ audio_base64: btoa(bin) }) });
        $('voiceText').value = r.transcript; log(`[${r.source}] ${r.transcript}`, 'voice');
      } catch (e) { status('Voice transcription failed: ' + esc(e.message) + ' — type the note and use Log note instead.'); }
    };
    mediaRec.start(); $('voiceBtn').textContent = 'Stop & transcribe'; log('Recording — stop to transcribe with Muse Voice Transcribe', 'voice');
  } catch (e) { status('Microphone unavailable: ' + esc(e.message) + ' — type the note instead.'); }
};
$('voiceSend').onclick = async () => {
  try {
    const r = await api('/api/voice', { method: 'POST', body: JSON.stringify({ transcript: $('voiceText').value }) });
    log(`[${r.source}] ${r.transcript}`, 'voice');
  } catch (e) { status(esc(e.message)); }
};
$('whyBtn').onclick = async () => {
  $('whyOut').innerHTML = '<p class="empty">Muse Wonder is reasoning over every series…</p>';
  try {
    const r = await api('/api/why', { method: 'POST', body: JSON.stringify({ question: $('whyText').value }) });
    $('whyOut').innerHTML = `
      <p class="why-answer">${esc(r.answer)}</p>
      <div class="why-model">Model: ${esc(r.model)}</div>
      <div class="evidence">${r.evidence.slice(0, 12).map(e => `<span>${esc(e.instrument_id)} ${esc(e.stat)} = ${esc(e.value)}</span>`).join('')}</div>`;
  } catch (e) { $('whyOut').innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
};

window.autopilot = async () => {
  log('Autopilot 1/4 — SAM 3.1 + Muse Spark detect the panel');
  await $('detectBtn').onclick();
  log('Autopilot 2/4 — Muse Spark compiles and verifies every reader');
  for (const i of instruments) await window.compileOne(i.id);
  log('Autopilot 3/4 — Muse Spark Open compiles the default alert rule');
  $('ruleText').value = 'alert when pressure goes above 80';
  await $('ruleBtn').onclick();
  await $('demoBtn').onclick();
  log('Autopilot 4/4 — live. On alert, Spark Open writes the incident summary; ask “why?” any time');
};

(async () => {
  await health();
  const r = await api('/api/detect', { method: 'POST', body: JSON.stringify({ image: '' }) });
  instruments = r.instruments; renderInstruments(); connect();
  status('<strong>Ready.</strong> Start the demo panel, or point a camera at a real one and capture &amp; detect.');
})();
