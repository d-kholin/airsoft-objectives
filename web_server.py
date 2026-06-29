import logging
from flask import Flask, request, jsonify, render_template_string, send_file
from config_store import ConfigStore
from game_controller import GameController
from game_registry import GAME_MODES, get_mode_info, list_modes
from history import load_history
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

INDEX_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Field Ops</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Courier New', monospace;
    background: #0a0a0f;
    color: #00c850;
    min-height: 100vh;
    padding: 20px;
  }
  h1 { text-align: center; font-size: 1.6em; margin-bottom: 4px; }
  .subtitle { text-align: center; color: #787878; font-size: 0.85em; margin-bottom: 20px; }
  .card {
    background: #1a1a22;
    border: 1px solid #00c850;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .card h2 { font-size: 1.1em; margin-bottom: 12px; }
  .card.active { border-color: #ffd800; }
  label { display: block; color: #787878; font-size: 0.85em; margin-bottom: 4px; }
  input[type=text], select {
    width: 100%;
    padding: 10px;
    font-family: 'Courier New', monospace;
    font-size: 1.1em;
    background: #0a0a0f;
    color: #00c850;
    border: 1px solid #005a24;
    border-radius: 4px;
    margin-bottom: 10px;
    text-transform: uppercase;
  }
  select { text-transform: none; }
  input:focus, select:focus { outline: none; border-color: #00c850; }
  button {
    width: 100%;
    padding: 12px;
    font-family: 'Courier New', monospace;
    font-size: 1em;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    margin-bottom: 8px;
  }
  .btn-green { background: #00c850; color: #0a0a0f; }
  .btn-red { background: #ff2828; color: #fff; }
  .btn-grey { background: #333; color: #aaa; }
  .btn-yellow { background: #ffd800; color: #0a0a0f; }
  .btn-outline { background: transparent; border: 1px solid #005a24; color: #787878; }
  .status-toast { padding: 10px; border-radius: 4px; text-align: center; margin-bottom: 10px; display: none; }
  .status-toast.ok { display: block; background: #003318; border: 1px solid #00c850; }
  .status-toast.err { display: block; background: #330000; border: 1px solid #ff2828; color: #ff2828; }
  .display { font-size: 1.1em; padding: 8px; background: #0a0a0f; border: 1px solid #005a24; border-radius: 4px; margin-bottom: 6px; }
  .empty { color: #333; font-style: italic; }
  .game-state { background: #0a0a0f; border: 1px solid #005a24; padding: 12px; border-radius: 4px; margin-bottom: 12px; }
  .state-line { margin-bottom: 6px; }
  .state-label { color: #787878; display: inline-block; width: 100px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .mode-btn {
    padding: 14px;
    font-family: 'Courier New', monospace;
    font-size: 1em;
    font-weight: bold;
    border: 1px solid #005a24;
    border-radius: 6px;
    cursor: pointer;
    margin-bottom: 8px;
    background: #0a0a0f;
    color: #00c850;
    text-align: left;
    width: 100%;
  }
  .mode-btn.selected { border-color: #00c850; background: #003318; }
  .mode-btn .mode-desc { font-size: 0.75em; color: #787878; font-weight: normal; margin-top: 4px; }
  .step { display: none; }
  .step.visible { display: block; }
  .step-indicator { text-align: center; margin-bottom: 16px; color: #787878; font-size: 0.85em; }
  .step-indicator span { margin: 0 4px; }
  .step-indicator .current { color: #00c850; font-weight: bold; }
  .nav-row { display: flex; gap: 8px; margin-top: 8px; }
  .nav-row button { flex: 1; }
  .code-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
  .code-row input { margin-bottom: 0; flex: 1; }
  .code-row .code-num { color: #787878; font-size: 0.85em; min-width: 20px; }
</style>
</head>
<body>
<h1>FIELD OPS</h1>
<p class="subtitle">Mission Control</p>

<div id="toast" class="status-toast"></div>

<!-- Live Game State -->
<div class="card" id="state-card">
  <h2>// STATUS</h2>
  <div class="game-state">
    <div class="state-line"><span class="state-label">Status:</span> <span id="state-status">—</span></div>
    <div class="state-line"><span class="state-label">Mode:</span> <span id="state-mode">—</span></div>
    <div class="state-line"><span class="state-label">Time:</span> <span id="state-time">—</span></div>
  </div>
  <img id="screen-img" src="/api/screen" style="width:100%;border-radius:4px;border:1px solid #005a24;margin-bottom:8px;display:none;">
  <button class="btn-red" id="kill-btn" onclick="confirmKill()">KILL / RESET</button>
</div>

<!-- Wizard -->
<div class="card" id="wizard-card">
  <h2>// NEW GAME</h2>

  <div id="step-dots" class="step-indicator"></div>

  <!-- Step 1: Pick Mode -->
  <div class="step visible" id="step-mode">
    <div id="mode-list"></div>
  </div>

  <!-- Step 2: Settings (dynamic per mode) -->
  <div class="step" id="step-settings">
    <div id="settings-fields"></div>
    <div class="nav-row">
      <button class="btn-outline" onclick="wizardBack()">BACK</button>
      <button class="btn-green" onclick="wizardNext()">NEXT</button>
    </div>
  </div>

  <!-- Step 3: Codes (comms only) -->
  <div class="step" id="step-codes">
    <p style="color:#787878;font-size:0.85em;margin-bottom:12px;">Set the 3 codes players must find and enter.</p>
    <div id="current-codes-display"></div>
    <div class="code-row"><span class="code-num">1</span><input type="text" id="code1" placeholder="e.g. ALPHA1" maxlength="20"></div>
    <div class="code-row"><span class="code-num">2</span><input type="text" id="code2" placeholder="e.g. BRAVO2" maxlength="20"></div>
    <div class="code-row"><span class="code-num">3</span><input type="text" id="code3" placeholder="e.g. CHARLIE3" maxlength="20"></div>
    <button class="btn-green" onclick="saveCodes()" style="margin-top:4px;">SAVE CODES</button>
    <div class="nav-row" style="margin-top:4px;">
      <button class="btn-outline" onclick="wizardBack()">BACK</button>
      <button class="btn-green" onclick="wizardNext()">NEXT</button>
    </div>
  </div>

  <!-- Step 3b: Launch code (missile only) -->
  <div class="step" id="step-launchcode">
    <p style="color:#787878;font-size:0.85em;margin-bottom:12px;">Set the launch code the attacking team must bring to the box and enter.</p>
    <div id="current-launchcode-display"></div>
    <div class="code-row"><span class="code-num">#</span><input type="text" id="launchcode" placeholder="e.g. ALPHA1" maxlength="20"></div>
    <div class="nav-row" style="margin-top:4px;">
      <button class="btn-outline" onclick="wizardBack()">BACK</button>
      <button class="btn-green" onclick="saveLaunchCodeAndNext()">NEXT</button>
    </div>
  </div>

  <!-- Step 4: Confirm & Launch -->
  <div class="step" id="step-confirm">
    <div id="confirm-summary" style="margin-bottom:12px;"></div>
    <button class="btn-green" onclick="launchGame()">START</button>
    <button class="btn-outline" onclick="wizardBack()" style="margin-top:4px;">BACK</button>
  </div>
</div>

<!-- History -->
<div class="card">
  <h2>// HISTORY</h2>
  <select id="history-mode" onchange="loadHistory()">
    <option value="">-- Select Mode --</option>
  </select>
  <div id="history-list"></div>
</div>

<script>
let allModes = {};
let wizStep = 0;
let selectedMode = null;
let wizSteps = [];

function toast(msg, ok) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'status-toast ' + (ok ? 'ok' : 'err');
  setTimeout(() => el.className = 'status-toast', 3000);
}

// --- Wizard ---

function buildSteps() {
  wizSteps = ['step-mode', 'step-settings', 'step-confirm'];
  if (selectedMode === 'comms_hack') {
    wizSteps = ['step-mode', 'step-settings', 'step-codes', 'step-confirm'];
  } else if (selectedMode === 'missile_launch') {
    wizSteps = ['step-mode', 'step-settings', 'step-launchcode', 'step-confirm'];
  }
}

function showStep() {
  document.querySelectorAll('.step').forEach(s => s.classList.remove('visible'));
  document.getElementById(wizSteps[wizStep]).classList.add('visible');

  const dots = document.getElementById('step-dots');
  const labels = wizSteps.map(s => {
    if (s === 'step-mode') return 'MODE';
    if (s === 'step-settings') return 'SETTINGS';
    if (s === 'step-codes') return 'CODES';
    if (s === 'step-launchcode') return 'CODE';
    if (s === 'step-confirm') return 'LAUNCH';
    return '?';
  });
  dots.innerHTML = labels.map((l, i) =>
    `<span class="${i === wizStep ? 'current' : ''}">${i === wizStep ? '[ ' + l + ' ]' : l}</span>`
  ).join(' > ');
}

function selectMode(modeId) {
  selectedMode = modeId;
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('selected', b.dataset.mode === modeId);
  });
  buildSteps();
  buildSettings();
  wizStep = 1;
  showStep();
}

function wizardNext() {
  if (wizStep < wizSteps.length - 1) {
    if (wizSteps[wizStep] === 'step-confirm' - 1) buildSummary();
    wizStep++;
    if (wizSteps[wizStep] === 'step-codes') loadCurrentCodes();
    if (wizSteps[wizStep] === 'step-launchcode') loadLaunchCode();
    if (wizSteps[wizStep] === 'step-confirm') buildSummary();
    showStep();
  }
}

function wizardBack() {
  if (wizStep > 0) {
    wizStep--;
    showStep();
  }
}

function buildSettings() {
  const container = document.getElementById('settings-fields');
  container.innerHTML = '';
  if (!selectedMode || !allModes[selectedMode]) return;
  const mode = allModes[selectedMode];
  Object.entries(mode.settings || {}).forEach(([key, setting]) => {
    const div = document.createElement('div');
    div.innerHTML = `<label>${setting.label}</label>`;
    const sel = document.createElement('select');
    sel.id = `setting-${key}`;
    setting.options.forEach(opt => {
      const o = document.createElement('option');
      o.value = opt.value;
      o.textContent = opt.label;
      if (opt.value === setting.default) o.selected = true;
      sel.appendChild(o);
    });
    div.appendChild(sel);

    if (setting.custom_min !== undefined) {
      const customDiv = document.createElement('div');
      customDiv.id = `custom-${key}`;
      customDiv.style.display = 'none';
      customDiv.innerHTML = `<label>Custom (minutes)</label>
        <input type="number" id="custom-val-${key}" min="${setting.custom_min}" max="${setting.custom_max}" value="10"
        style="width:100%;padding:10px;font-family:'Courier New',monospace;font-size:1.1em;background:#0a0a0f;color:#00c850;border:1px solid #005a24;border-radius:4px;margin-bottom:10px;">`;
      div.appendChild(customDiv);
      sel.addEventListener('change', () => {
        customDiv.style.display = sel.value === '-1' ? '' : 'none';
      });
    }

    container.appendChild(div);
  });
}

function getSettings() {
  const settings = {};
  document.querySelectorAll('#settings-fields select').forEach(sel => {
    const key = sel.id.replace('setting-', '');
    let val = parseInt(sel.value);
    if (val === -1) {
      const customInput = document.getElementById(`custom-val-${key}`);
      if (customInput) val = parseInt(customInput.value) * 60;
    }
    settings[key] = val;
  });
  return settings;
}

function loadCurrentCodes() {
  fetch('/api/codes').then(r => r.json()).then(data => {
    const container = document.getElementById('current-codes-display');
    if (data.codes.length === 3) {
      container.innerHTML = '<p style="color:#787878;font-size:0.85em;margin-bottom:8px;">Current codes:</p>' +
        data.codes.map((c, i) => `<div class="display">CODE ${i+1}: ${c}</div>`).join('');
      document.getElementById('code1').value = data.codes[0];
      document.getElementById('code2').value = data.codes[1];
      document.getElementById('code3').value = data.codes[2];
    } else {
      container.innerHTML = '<div class="display empty">No codes set yet</div>';
    }
  });
}

function saveCodes() {
  const codes = [
    document.getElementById('code1').value.toUpperCase().trim(),
    document.getElementById('code2').value.toUpperCase().trim(),
    document.getElementById('code3').value.toUpperCase().trim(),
  ];
  if (codes.some(c => !c)) { toast('All 3 codes are required', false); return; }
  fetch('/api/codes', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({codes: codes})
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) { toast('Codes saved', true); loadCurrentCodes(); }
    else toast(data.error || 'Failed', false);
  });
}

function loadLaunchCode() {
  fetch('/api/launch_code').then(r => r.json()).then(data => {
    const container = document.getElementById('current-launchcode-display');
    if (data.launch_code) {
      container.innerHTML = '<p style="color:#787878;font-size:0.85em;margin-bottom:8px;">Current code:</p>' +
        `<div class="display">LAUNCH CODE: ${data.launch_code}</div>`;
      document.getElementById('launchcode').value = data.launch_code;
    } else {
      container.innerHTML = '<div class="display empty">No launch code set yet</div>';
    }
  });
}

function saveLaunchCode() {
  const code = document.getElementById('launchcode').value.toUpperCase().trim();
  if (!code) return Promise.resolve(false);
  return fetch('/api/launch_code', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({launch_code: code})
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) { toast('Launch code saved', true); loadLaunchCode(); }
    else toast(data.error || 'Failed', false);
    return data.ok;
  });
}

function saveLaunchCodeAndNext() {
  const code = document.getElementById('launchcode').value.toUpperCase().trim();
  if (!code) { toast('Launch code is required', false); return; }
  saveLaunchCode().then(ok => { if (ok) wizardNext(); });
}

function buildSummary() {
  const mode = allModes[selectedMode];
  const settings = getSettings();
  let html = `<div class="display"><strong>${mode.name}</strong></div>`;
  Object.entries(mode.settings || {}).forEach(([key, setting]) => {
    const val = settings[key];
    const opt = setting.options.find(o => o.value === val);
    html += `<div class="display">${setting.label}: ${opt ? opt.label : val}</div>`;
  });
  if (selectedMode === 'comms_hack') {
    const codes = [
      document.getElementById('code1').value.toUpperCase().trim(),
      document.getElementById('code2').value.toUpperCase().trim(),
      document.getElementById('code3').value.toUpperCase().trim(),
    ];
    if (codes.every(c => c)) {
      codes.forEach((c, i) => { html += `<div class="display">CODE ${i+1}: ${c}</div>`; });
    } else {
      html += '<div class="display empty">Codes not set — will use manual entry on box</div>';
    }
  } else if (selectedMode === 'missile_launch') {
    const code = document.getElementById('launchcode').value.toUpperCase().trim();
    if (code) {
      html += `<div class="display">LAUNCH CODE: ${code}</div>`;
    } else {
      html += '<div class="display empty">Code not set — will use manual entry on box</div>';
    }
  }
  document.getElementById('confirm-summary').innerHTML = html;
}

function launchGame() {
  const settings = getSettings();
  const doQueue = () => {
    fetch('/api/queue', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mode: selectedMode, settings: settings, force: true})
    })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        toast('Game started', true);
        wizStep = 0;
        selectedMode = null;
        buildSteps();
        showStep();
        refreshState();
      } else toast(data.error || 'Failed', false);
    });
  };
  if (selectedMode === 'missile_launch') {
    const code = document.getElementById('launchcode').value.toUpperCase().trim();
    if (code) { saveLaunchCode().then(doQueue); return; }
  }
  doQueue();
}

// --- State ---

function refreshState() {
  fetch('/api/state').then(r => r.json()).then(data => {
    document.getElementById('state-status').textContent = data.status;
    document.getElementById('state-mode').textContent = data.mode || '—';
    if (data.time_remaining > 0) {
      const m = Math.floor(data.time_remaining / 60);
      const s = data.time_remaining % 60;
      document.getElementById('state-time').textContent = m + 'm' + String(s).padStart(2,'0') + 's';
    } else {
      document.getElementById('state-time').textContent = '—';
    }
    const wizard = document.getElementById('wizard-card');
    const killBtn = document.getElementById('kill-btn');
    if (data.status === 'running' || data.status === 'setup' || data.status === 'finished') {
      wizard.style.display = 'none';
      killBtn.style.display = '';
    } else {
      wizard.style.display = '';
      killBtn.style.display = 'none';
    }
  });
  const img = document.getElementById('screen-img');
  const newImg = new Image();
  newImg.onload = function() { img.src = newImg.src; img.style.display = 'block'; };
  newImg.src = '/api/screen?t=' + Date.now();
}

let killPending = false;
let killTimer = null;

function confirmKill() {
  if (!killPending) {
    killPending = true;
    const btn = document.getElementById('kill-btn');
    btn.textContent = 'CONFIRM KILL?';
    btn.style.background = '#aa0000';
    killTimer = setTimeout(() => {
      killPending = false;
      btn.textContent = 'KILL / RESET';
      btn.style.background = '';
    }, 3000);
  } else {
    clearTimeout(killTimer);
    killPending = false;
    const btn = document.getElementById('kill-btn');
    btn.textContent = 'KILL / RESET';
    btn.style.background = '';
    fetch('/api/kill', {method: 'POST'}).then(r => r.json()).then(data => {
      if (data.ok) { toast('Game killed', true); refreshState(); }
    });
  }
}

// --- History ---

function loadHistory() {
  const modeId = document.getElementById('history-mode').value;
  const container = document.getElementById('history-list');
  if (!modeId) { container.innerHTML = ''; return; }

  fetch('/api/history').then(r => r.json()).then(data => {
    const entries = data[modeId] || [];
    if (entries.length === 0) {
      container.innerHTML = '<div class="display empty">No games played</div>';
      return;
    }
    const th = 'style="text-align:left;padding:4px;"';
    const td = 'style="padding:4px;"';
    let html = '<div style="overflow-x:auto;margin-top:8px;">';
    html += '<table style="width:100%;border-collapse:collapse;font-size:0.85em;">';

    if (modeId === 'bomb_defusal') {
      html += `<tr style="color:#00c850;border-bottom:1px solid #005a24;">
        <th ${th}>Date</th><th ${th}>Result</th><th ${th}>Time</th><th ${th}>Strikes</th><th ${th}>Modules</th></tr>`;
      entries.forEach(e => {
        const mins = Math.floor((e.elapsed_seconds||0)/60);
        const secs = (e.elapsed_seconds||0)%60;
        const rc = (e.result||'').toUpperCase() === 'VICTORY' ? '#00c850' : '#ff2828';
        html += `<tr><td ${td}>${e.timestamp||'?'}</td>
          <td ${td} style="color:${rc}">${(e.result||'?').toUpperCase()}</td>
          <td ${td}>${mins}m${String(secs).padStart(2,'0')}s</td>
          <td ${td}>${e.strikes||0}/3</td>
          <td ${td}>${e.modules_solved||0}/${e.modules_total||'?'}</td></tr>`;
      });
    } else if (modeId === 'domination') {
      html += `<tr style="color:#00c850;border-bottom:1px solid #005a24;">
        <th ${th}>Date</th><th ${th}>Winner</th><th ${th}>Time</th><th ${th}>Red</th><th ${th}>Blue</th></tr>`;
      entries.forEach(e => {
        const mins = Math.floor((e.elapsed_seconds||0)/60);
        const secs = (e.elapsed_seconds||0)%60;
        const r = (e.result||'').toUpperCase();
        const rc = r === 'RED' ? '#ff2828' : '#2864ff';
        const rt = e.red_hold_time||0; const bt = e.blue_hold_time||0;
        html += `<tr><td ${td}>${e.timestamp||'?'}</td>
          <td ${td} style="color:${rc}">${r}</td>
          <td ${td}>${mins}m${String(secs).padStart(2,'0')}s</td>
          <td ${td}>${Math.floor(rt/60)}:${String(rt%60).padStart(2,'0')}</td>
          <td ${td}>${Math.floor(bt/60)}:${String(bt%60).padStart(2,'0')}</td></tr>`;
      });
    } else if (modeId === 'missile_launch') {
      html += `<tr style="color:#00c850;border-bottom:1px solid #005a24;">
        <th ${th}>Date</th><th ${th}>Outcome</th><th ${th}>Time</th><th ${th}>Failed</th><th ${th}>T-Left</th></tr>`;
      entries.forEach(e => {
        const mins = Math.floor((e.elapsed_seconds||0)/60);
        const secs = (e.elapsed_seconds||0)%60;
        const r = (e.result||'?').toUpperCase();
        const rc = r === 'LAUNCHED' ? '#00c850' : '#ff2828';
        const tl = e.time_left||0;
        html += `<tr><td ${td}>${e.timestamp||'?'}</td>
          <td ${td} style="color:${rc}">${r}</td>
          <td ${td}>${mins}m${String(secs).padStart(2,'0')}s</td>
          <td ${td}>${e.failed_attempts||0}</td>
          <td ${td}>${Math.floor(tl/60)}:${String(tl%60).padStart(2,'0')}</td></tr>`;
      });
    } else {
      html += `<tr style="color:#00c850;border-bottom:1px solid #005a24;">
        <th ${th}>Date</th><th ${th}>Result</th><th ${th}>Time</th><th ${th}>Failed</th><th ${th}>Codes</th></tr>`;
      entries.forEach(e => {
        const mins = Math.floor((e.elapsed_seconds||0)/60);
        const secs = (e.elapsed_seconds||0)%60;
        const rc = (e.result||'').toUpperCase() === 'VICTORY' ? '#00c850' : '#ff2828';
        html += `<tr><td ${td}>${e.timestamp||'?'}</td>
          <td ${td} style="color:${rc}">${(e.result||'?').toUpperCase()}</td>
          <td ${td}>${mins}m${String(secs).padStart(2,'0')}s</td>
          <td ${td}>${e.failed_attempts||0}</td>
          <td ${td}>${e.codes_unlocked||0}/3</td></tr>`;
      });
    }
    html += '</table></div>';
    container.innerHTML = html;
  });
}

// --- Init ---

fetch('/api/modes').then(r => r.json()).then(data => {
  allModes = data.info;
  const list = document.getElementById('mode-list');
  const histSel = document.getElementById('history-mode');
  data.modes.forEach(id => {
    const mode = data.info[id];
    const btn = document.createElement('button');
    btn.className = 'mode-btn';
    btn.dataset.mode = id;
    btn.innerHTML = `${mode.name}<div class="mode-desc">${mode.description}</div>`;
    btn.onclick = () => selectMode(id);
    list.appendChild(btn);

    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = mode.name;
    histSel.appendChild(opt);
  });
  buildSteps();
  showStep();
});
refreshState();
setInterval(refreshState, 2000);
</script>
</body>
</html>
"""


def create_app(config_store, game_controller):
    app = Flask(__name__)
    app.config_store = config_store
    app.game_controller = game_controller

    @app.route("/")
    def index():
        return render_template_string(INDEX_PAGE)

    @app.route("/api/modes")
    def get_modes():
        modes = list_modes()
        return jsonify({
            "modes": modes,
            "info": {mid: get_mode_info(mid) for mid in modes}
        })

    @app.route("/api/mode/<mode_id>")
    def get_mode(mode_id):
        info = get_mode_info(mode_id)
        if not info:
            return jsonify({"error": "Mode not found"}), 404
        return jsonify({"mode": info})

    @app.route("/api/state")
    def get_state():
        return jsonify(game_controller.get_state())

    @app.route("/api/queue", methods=["POST"])
    def queue_game():
        data = request.get_json(silent=True) or {}
        mode = data.get("mode")
        settings = data.get("settings", {})
        force = data.get("force", False)
        if not mode or mode not in GAME_MODES:
            return jsonify({"ok": False, "error": "Invalid mode"}), 400
        game_controller.queue_command(mode, settings, force)
        return jsonify({"ok": True})

    @app.route("/api/kill", methods=["POST"])
    def kill_game():
        game_controller.queue_command("__kill__", {})
        return jsonify({"ok": True})

    @app.route("/api/codes", methods=["GET"])
    def get_codes():
        return jsonify({"codes": config_store.get_codes()})

    @app.route("/api/codes", methods=["POST"])
    def set_codes():
        data = request.get_json(silent=True) or {}
        codes = data.get("codes", [])
        if len(codes) != 3 or not all(isinstance(c, str) and c.strip() for c in codes):
            return jsonify({"ok": False, "error": "Need exactly 3 non-empty codes"}), 400
        config_store.set_codes([c.strip().upper() for c in codes])
        return jsonify({"ok": True})

    @app.route("/api/codes", methods=["DELETE"])
    def clear_codes():
        config_store.clear_codes()
        return jsonify({"ok": True})

    @app.route("/api/launch_code", methods=["GET"])
    def get_launch_code():
        return jsonify({"launch_code": config_store.get_launch_code()})

    @app.route("/api/launch_code", methods=["POST"])
    def set_launch_code():
        data = request.get_json(silent=True) or {}
        code = (data.get("launch_code") or "").strip().upper()
        if not code:
            return jsonify({"ok": False, "error": "Launch code required"}), 400
        config_store.set_launch_code(code)
        return jsonify({"ok": True})

    @app.route("/api/launch_code", methods=["DELETE"])
    def clear_launch_code():
        config_store.clear_launch_code()
        return jsonify({"ok": True})

    @app.route("/api/history")
    def get_history():
        result = {}
        for mode_id in list_modes():
            entries = load_history(mode_id)
            entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
            result[mode_id] = entries[:50]
        return jsonify(result)

    @app.route("/api/screen")
    def get_screen():
        screen_file = DATA_DIR / "screen.jpg"
        if screen_file.exists():
            return send_file(screen_file, mimetype="image/jpeg")
        return "", 204

    return app


def run_web_server(config_store, game_controller, host="0.0.0.0", port=8080):
    """Run the web server (blocking)."""
    app = create_app(config_store, game_controller)
    app.run(host=host, port=port, use_reloader=False)
