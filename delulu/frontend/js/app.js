// ==========================================================================
// DELULU // J.A.R.V.I.S. - REAL-LIFE AI ASSISTANT FRONTEND ENGINE
// ==========================================================================

const API_BASE = "";

// Global Application State
const state = {
  token: localStorage.getItem("delulu_token") || null,
  user: null,
  currentConvId: null,
  isListening: false,
  voiceLang: localStorage.getItem("delulu_voice_lang") || "ml-IN"
};

const $ = id => document.getElementById(id);

// --- 1. CORE AI REACTOR STATE MACHINE & PALETTES ---
// [name, caption, spin, pulse, rings, wave, rgb]
const S = {
  IDLE: ['Ready', 'Waiting for “Hey Delulu” or Ctrl + 0', .12, .02, .3, 0, [61, 232, 255]],
  WAKE: ['Awake', 'JARVIS is online', .9, .1, 1, 0, [205, 248, 255]],
  LISTENING: ['Listening', 'Go ahead, I am listening...', .4, .06, .7, 1, [61, 232, 255]],
  THINKING: ['Thinking', 'Analyzing and reasoning...', 1.8, .03, 1, 0, [110, 190, 255]],
  SPEAKING: ['Speaking', '', .45, .08, .6, 1.2, [61, 232, 255]],
  EXECUTING: ['Executing', 'Running verified task...', 1.2, .03, 1, 0, [61, 232, 255]],
  APPROVAL_REQUIRED: ['Approval Required', 'Action needs confirmation', .08, .05, .5, 0, [255, 196, 92]],
  ERROR: ['Error', 'Encountered an issue processing request', .04, .02, .2, 0, [255, 96, 96]]
};

let coreState = 'IDLE', tg = S.IDLE, T = [], pulse = 0;
let cur = { sp: .12, amp: .02, rg: .3, w: 0, c: [61, 232, 255] };

function clr() {
  T.forEach(clearTimeout);
  T = [];
}

function setCoreState(s, m) {
  if (!S[s]) return;
  coreState = s;
  tg = S[s];
  document.documentElement.style.setProperty('--acc', tg[6].join(','));
  
  const stEl = $('st');
  const capEl = $('cap');
  const tagEl = $('state-tag');
  
  if (stEl) stEl.textContent = tg[0];
  if (capEl) {
    capEl.textContent = m || tg[1];
    if (s === 'SPEAKING') {
      capEl.classList.add('active-speech');
    } else {
      capEl.classList.remove('active-speech');
    }
  }
  if (tagEl) tagEl.textContent = `SYSTEM ${s}`;

  const voiceBadge = $('voice-indicator');
  if (voiceBadge) {
    voiceBadge.textContent = s === 'LISTENING' ? 'MIC OPEN' : (s === 'SPEAKING' ? 'AUDIO OUT' : 'VOICE READY');
  }

  // ADA Screen Reader Announcements
  if (s === 'SPEAKING' && m) {
    announceToScreenReader(`JARVIS: ${m}`);
  } else if (s === 'LISTENING') {
    announceToScreenReader('Microphone open. JARVIS is listening...');
  } else if (s === 'EXECUTING') {
    announceToScreenReader(m || 'Executing system action...');
  }

  const apprEl = $('appr');
  if (apprEl) {
    apprEl.hidden = s !== 'APPROVAL_REQUIRED';
    if (s === 'APPROVAL_REQUIRED') {
      const aptEl = $('apt');
      if (aptEl) aptEl.textContent = m || 'Delulu needs your approval to continue.';
    }
  }

  if (s === 'WAKE') pulse = 1;
}

// --- 2. HTTP API CLIENT ---
async function api(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

  if (res.status === 401) {
    const isAuthRoute = endpoint.includes("/auth/login") || endpoint.includes("/auth/register") || endpoint.includes("/auth/guest") || endpoint.includes("/auth/default");
    if (!isAuthRoute) {
      try {
        const authData = await api("/api/v1/auth/default", { method: "POST" });
        state.token = authData.access_token;
        localStorage.setItem("delulu_token", authData.access_token);
      } catch (err) {
        console.warn("Silent token refresh failed:", err);
      }
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json().catch(() => ({}));
}

// --- 3. LIFECYCLE & INITIALIZATION ---
document.addEventListener("DOMContentLoaded", async () => {
  setupCommandBar();
  initClock();
  init3DCore();
  updateVoiceLangUI();

  // Direct Access: Auto-connect to personal space without login
  await initDirectSession();
  setCoreState("IDLE");
  loadRecentHistory();

  // ADA & Real Features
  setupGlobalShortcuts();
  initTelemetrySystem();
  fetchCurrentVolume();
});

async function initDirectSession() {
  try {
    if (!state.token) {
      const data = await api("/api/v1/auth/default", { method: "POST" });
      state.token = data.access_token;
      localStorage.setItem("delulu_token", data.access_token);
    }
    await loadCurrentUser();
  } catch (err) {
    console.warn("Direct session connecting to default space...", err);
    try {
      const data = await api("/api/v1/auth/default", { method: "POST" });
      state.token = data.access_token;
      localStorage.setItem("delulu_token", data.access_token);
      await loadCurrentUser();
    } catch (e) {
      console.error("Direct access auto-login failed:", e);
    }
  }
}

function initClock() {
  const tick = () => {
    const clk = $('clk');
    if (clk) clk.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };
  tick();
  setInterval(tick, 1000);
}

// --- 4. 3D GLASS REACTOR CORE (CANVAS) ---
function init3DCore() {
  const cv = $('c');
  if (!cv) return;
  const x = cv.getContext('2d');
  const rm = matchMedia('(prefers-reduced-motion:reduce)').matches;
  let W, H, D;

  function fit() {
    D = window.devicePixelRatio || 1;
    const r = cv.getBoundingClientRect();
    W = r.width;
    H = r.height;
    cv.width = W * D;
    cv.height = H * D;
  }
  new ResizeObserver(fit).observe(cv);

  // 500 orbital points
  const P = [];
  for (let i = 0; i < 500; i++) {
    const y = 1 - 2 * (i + .5) / 500;
    const r = Math.sqrt(1 - y * y);
    const t = i * 2.39996;
    P.push([Math.cos(t) * r, y, Math.sin(t) * r]);
  }

  const L = (a, b, k) => a + (b - a) * k;
  let ang = 0;

  function draw(ms) {
    const t = ms / 1000, k = .06;
    cur.sp = L(cur.sp, tg[2] * (rm ? .2 : 1), k);
    cur.amp = L(cur.amp, tg[3], k);
    cur.rg = L(cur.rg, tg[4], k);
    cur.w = L(cur.w, tg[5], k);
    cur.c = cur.c.map((v, i) => L(v, tg[6][i], k));
    ang += cur.sp * .012;
    pulse = Math.max(0, pulse - .012);

    x.setTransform(D, 0, 0, D, 0, 0);
    x.clearRect(0, 0, W, H);

    const j = coreState === 'ERROR' ? (Math.random() - .5) * 3 : 0;
    const cx = W / 2 + j, cy = H * .42;
    const R = Math.min(W * .8, H * .88) * .31 * (1 + cur.amp * Math.sin(t * 3) + cur.w * .06 * Math.sin(t * 9) * Math.sin(t * 2.3));
    const C = a => `rgba(${cur.c.map(Math.round)},${a})`;

    // Core Aura
    let g = x.createRadialGradient(cx, cy, R * .3, cx, cy, R * 2.4);
    g.addColorStop(0, C(.18));
    g.addColorStop(1, C(0));
    x.fillStyle = g;
    x.fillRect(0, 0, W, H);

    // Orbital Rings
    for (let i = 0; i < 3; i++) {
      x.save();
      x.translate(cx, cy);
      x.rotate(ang * (i % 2 ? -2 : 3) + i * 1.05);
      x.scale(1, .3 + i * .2);
      x.beginPath();
      x.arc(0, 0, R * (1.3 + i * .2), 0, 6.283 * (.5 + .5 * cur.rg));
      x.strokeStyle = C(.1 + .3 * cur.rg * (1 - i * .25));
      x.lineWidth = 1.3;
      x.stroke();
      x.restore();
    }

    // 3D Point Cloud
    const ca = Math.cos(ang), sa = Math.sin(ang), ct = .94, st = .34;
    for (const p of P) {
      const X = p[0] * ca - p[2] * sa;
      const Z0 = p[0] * sa + p[2] * ca;
      const Y = p[1] * ct - Z0 * st;
      const Z = p[1] * st + Z0 * ct;
      const s = 1 + Z * .12;
      const z = (Z + 1) / 2;
      x.fillStyle = C(.12 + .6 * z);
      x.fillRect(cx + X * R * s * .96, cy + Y * R * s * .96, 1 + 1.6 * z, 1 + 1.6 * z);
    }

    // Glass Sphere Overlay
    g = x.createRadialGradient(cx - R * .3, cy - R * .38, R * .05, cx, cy, R);
    g.addColorStop(0, 'rgba(255,255,255,.3)');
    g.addColorStop(.5, C(.05));
    g.addColorStop(.88, C(.18));
    g.addColorStop(1, C(.6));
    x.beginPath();
    x.arc(cx, cy, R, 0, 6.283);
    x.fillStyle = g;
    x.fill();
    x.lineWidth = 1.2;
    x.strokeStyle = 'rgba(255,255,255,.3)';
    x.stroke();

    // Specular Highlight
    x.beginPath();
    x.arc(cx, cy, R * .9, 3.5, 4.55);
    x.lineCap = 'round';
    x.lineWidth = 2.5;
    x.strokeStyle = 'rgba(255,255,255,.55)';
    x.stroke();

    // Inner Glow
    g = x.createRadialGradient(cx, cy, 0, cx, cy, R * .5);
    g.addColorStop(0, C(.6 + .2 * Math.sin(t * 2)));
    g.addColorStop(1, C(0));
    x.fillStyle = g;
    x.beginPath();
    x.arc(cx, cy, R * .5, 0, 6.283);
    x.fill();

    // Waveform Visualizer
    if (cur.w > .02) {
      for (let i = 0; i < 80; i++) {
        const q = i / 80 * 6.283;
        const l = cur.w * R * .32 * Math.abs(Math.sin(t * 5 + i * .7) * Math.sin(t * 1.7 + i * .31));
        const r0 = R * 1.06;
        x.beginPath();
        x.moveTo(cx + Math.cos(q) * r0, cy + Math.sin(q) * r0);
        x.lineTo(cx + Math.cos(q) * (r0 + 4 + l), cy + Math.sin(q) * (r0 + 4 + l));
        x.strokeStyle = C(.55);
        x.lineWidth = 1.5;
        x.stroke();
      }
    }

    // Wake Pulse
    if (pulse > 0) {
      x.beginPath();
      x.arc(cx, cy, R * (1.1 + (1 - pulse) * 1.4), 0, 6.283);
      x.strokeStyle = C(pulse * .6);
      x.lineWidth = 2;
      x.stroke();
    }

    requestAnimationFrame(draw);
  }

  fit();
  setCoreState('IDLE');
  requestAnimationFrame(draw);
}

// --- 5. COMMAND BAR & SPEECH RECOGNITION (SIRI / GEMINI / CHATGPT STYLE) ---
function setupCommandBar() {
  const f = $('f');
  const mic = $('mic');
  const cv = $('c');

  if (f) {
    f.onsubmit = e => {
      e.preventDefault();
      const input = $('cmd');
      const text = input.value.trim();
      if (text) {
        runDeluluCommand(text);
        input.value = '';
      }
    };
  }

  if (mic) mic.onclick = () => triggerWake();
  if (cv) cv.onclick = () => triggerWake();

  // Approvals
  const okBtn = $('ok');
  const noBtn = $('no');
  if (okBtn) {
    okBtn.onclick = () => {
      setCoreState('EXECUTING', 'Permission granted. Running task.');
      setTimeout(() => {
        setCoreState('SPEAKING', 'Task executed successfully.');
        setTimeout(() => setCoreState('IDLE'), 2000);
      }, 800);
    };
  }
  if (noBtn) {
    noBtn.onclick = () => {
      setCoreState('IDLE', 'Action denied by user.');
    };
  }
}

let activeRecognition = null;
let wakeWordRecognizer = null;
let isWakeWordActive = localStorage.getItem('delulu_wake_active') === 'true';

const WAKE_WORDS = [
  // English
  "hey delulu", "delulu", "jarvis", "hey jarvis", "hi delulu", "hello delulu", "ok delulu",
  // Malayalam phonetic & script
  "ഹേ ഡെലുലു", "ഡെലുലു", "ഡിലുലു", "ദെലുലു", "ദിലുലു", "ഡീലുലു",
  "ജാർവിസ്", "ഹേ ജാർവിസ്", "ജാർവീസ്", "ജാർവിസെ",
  "ഹായ് ഡെലുലു", "ഹലോ ഡെലുലു", "ഹേയ് ഡെലുലു", "ഹെ ഡെലുലു",
  // Acoustic / Manglish interpretations
  "a delulu", "hey dilulu", "dilulu", "deluloo"
];

function playJarvisChime() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    const now = ctx.currentTime;
    osc.frequency.setValueAtTime(587.33, now); // D5
    osc.frequency.exponentialRampToValueAtTime(880, now + 0.12); // A5
    gain.gain.setValueAtTime(0.16, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    osc.start(now);
    osc.stop(now + 0.32);
  } catch(e) {}
}

// Master wake trigger (used by Ctrl+0, Canvas click, and Wake Word detection)
function triggerWake() {
  unlockAudioEngine();
  playJarvisChime();
  pulse = 1;

  // Temporarily pause wake word ambient listener to free the microphone
  if (wakeWordRecognizer) {
    try { wakeWordRecognizer.stop(); } catch(e){}
    wakeWordRecognizer = null;
  }

  setCoreState('WAKE');
  setCoreState('LISTENING', state.voiceLang === 'ml-IN' ? 'കേൾക്കുന്നു, പറയൂ...' : 'Listening...');

  // Start dedicated single-shot speech recognizer with zero delay
  startVoiceRecognition();
}

function toggleWakeWordListener() {
  if (isWakeWordActive) {
    stopWakeWordListener();
  } else {
    isWakeWordActive = true;
    localStorage.setItem('delulu_wake_active', 'true');
    startWakeWordListener();
  }
}

function startWakeWordListener() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    setCoreState('IDLE', 'Wake word listening not supported in this browser. Please use Chrome or Edge.');
    return;
  }

  // If already active or currently speaking, don't duplicate
  if (wakeWordRecognizer || activeRecognition) return;

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  wakeWordRecognizer = new SpeechRec();
  wakeWordRecognizer.continuous = true;
  wakeWordRecognizer.interimResults = true;
  wakeWordRecognizer.lang = state.voiceLang || 'ml-IN';

  updateWakeWordUI();

  wakeWordRecognizer.onresult = (e) => {
    // If assistant is currently speaking or executing, ignore
    if (coreState === 'SPEAKING' || coreState === 'EXECUTING' || coreState === 'THINKING') {
      return;
    }

    for (let i = e.resultIndex; i < e.results.length; i++) {
      const res = e.results[i];
      const transcript = res[0].transcript.toLowerCase().trim();

      // Check for wake word in transcript
      let matchedWake = null;
      for (const w of WAKE_WORDS) {
        if (transcript.includes(w)) {
          matchedWake = w;
          break;
        }
      }

      if (matchedWake) {
        console.log("Wake word detected:", matchedWake);
        const wakeIdx = transcript.indexOf(matchedWake);
        let afterWake = transcript.slice(wakeIdx + matchedWake.length).replace(/^[,\s]+/, '').trim();

        // Halt ambient recognizer to prevent collision
        if (wakeWordRecognizer) {
          try { wakeWordRecognizer.stop(); } catch(err){}
          wakeWordRecognizer = null;
        }

        if (afterWake && afterWake.length > 2) {
          // Command spoken in the same breath (e.g. "Hey Delulu what is the time?")
          playJarvisChime();
          pulse = 1;
          runDeluluCommand(afterWake);
        } else {
          // Just wake word spoken -> Transition to listening for command
          triggerWake();
        }
        break;
      }
    }
  };

  wakeWordRecognizer.onerror = (err) => {
    wakeWordRecognizer = null;
    if (isWakeWordActive && err.error !== 'not-allowed') {
      setTimeout(() => {
        if (isWakeWordActive && !activeRecognition && coreState === 'IDLE') {
          startWakeWordListener();
        }
      }, 1000);
    }
  };

  wakeWordRecognizer.onend = () => {
    wakeWordRecognizer = null;
    if (isWakeWordActive && !activeRecognition && coreState === 'IDLE') {
      setTimeout(() => {
        if (isWakeWordActive && !activeRecognition && coreState === 'IDLE') {
          startWakeWordListener();
        }
      }, 300);
    }
  };

  try {
    wakeWordRecognizer.start();
  } catch (err) {
    wakeWordRecognizer = null;
  }
}

function stopWakeWordListener() {
  isWakeWordActive = false;
  localStorage.setItem('delulu_wake_active', 'false');
  if (wakeWordRecognizer) {
    try { wakeWordRecognizer.stop(); } catch(e){}
    wakeWordRecognizer = null;
  }
  updateWakeWordUI();
}

function resumeWakeWordListener() {
  if (isWakeWordActive && !wakeWordRecognizer && !activeRecognition) {
    setTimeout(() => {
      if (isWakeWordActive && !wakeWordRecognizer && !activeRecognition && coreState === 'IDLE') {
        startWakeWordListener();
      }
    }, 500);
  }
}

function updateWakeWordUI() {
  const btn = $('wake-toggle-btn');
  if (btn) {
    if (isWakeWordActive) {
      btn.textContent = '👂 WAKE WORD: ON (Say “Hey Delulu”)';
      btn.style.background = 'rgba(var(--acc), .22)';
      btn.style.borderColor = 'rgb(var(--acc))';
      btn.style.color = '#fff';
      btn.style.boxShadow = '0 0 14px rgba(var(--acc), .4)';
    } else {
      btn.textContent = '👂 WAKE WORD: OFF';
      btn.style.background = 'rgba(255, 255, 255, .05)';
      btn.style.borderColor = 'var(--line)';
      btn.style.color = 'var(--mut)';
      btn.style.boxShadow = 'none';
    }
  }
}

function toggleVoiceLang() {
  state.voiceLang = state.voiceLang === 'ml-IN' ? 'en-US' : 'ml-IN';
  localStorage.setItem('delulu_voice_lang', state.voiceLang);
  updateVoiceLangUI();
  if (isWakeWordActive) {
    if (wakeWordRecognizer) {
      try { wakeWordRecognizer.stop(); } catch(e){}
      wakeWordRecognizer = null;
    }
    startWakeWordListener();
  }
}

function updateVoiceLangUI() {
  const btn = $('voice-lang-btn');
  if (btn) {
    btn.textContent = state.voiceLang === 'ml-IN' ? '🎙️ വോയ്സ്: മലയാളം (ML)' : '🎙️ VOICE: ENGLISH (EN)';
    btn.style.background = state.voiceLang === 'ml-IN' ? 'rgba(var(--acc), .18)' : 'rgba(255, 255, 255, .05)';
  }
}

function wakeDeluluVoice() {
  triggerWake();
}

function startVoiceRecognition() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    setCoreState('IDLE', 'Voice input not supported in this browser. Please type.');
    return;
  }

  // Ensure any previous active recognizer is cleanly stopped
  if (activeRecognition) {
    try { activeRecognition.stop(); } catch(e){}
    activeRecognition = null;
  }

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new SpeechRec();
  activeRecognition = rec;
  rec.lang = state.voiceLang || 'ml-IN';
  rec.interimResults = false;
  rec.continuous = false;

  const micBtn = $('mic');
  if (micBtn) micBtn.classList.add('active');

  rec.onresult = e => {
    if (micBtn) micBtn.classList.remove('active');
    activeRecognition = null;

    let transcript = e.results[0][0].transcript;
    if (transcript && transcript.trim()) {
      let cleanCmd = transcript.trim();
      for (const w of WAKE_WORDS) {
        if (cleanCmd.toLowerCase().startsWith(w)) {
          cleanCmd = cleanCmd.slice(w.length).trim();
          break;
        }
      }
      runDeluluCommand(cleanCmd || transcript);
    } else {
      setCoreState('IDLE');
      resumeWakeWordListener();
    }
  };

  rec.onerror = (err) => {
    console.warn("Direct voice recognition error:", err);
    if (micBtn) micBtn.classList.remove('active');
    activeRecognition = null;
    setCoreState('IDLE');
    resumeWakeWordListener();
  };

  rec.onend = () => {
    if (micBtn) micBtn.classList.remove('active');
    activeRecognition = null;
    if (coreState === 'LISTENING') {
      setCoreState('IDLE');
      resumeWakeWordListener();
    }
  };

  try {
    rec.start();
  } catch (err) {
    console.warn("Could not start active recognition:", err);
    if (micBtn) micBtn.classList.remove('active');
    activeRecognition = null;
    setCoreState('IDLE');
    resumeWakeWordListener();
  }
}

function stopVoiceRecognition() {
  if (activeRecognition) {
    try { activeRecognition.stop(); } catch(e){}
    activeRecognition = null;
  }
  const micBtn = $('mic');
  if (micBtn) micBtn.classList.remove('active');
  resumeWakeWordListener();
}

// Quick chip execution
function executeChip(promptText) {
  const input = $('cmd');
  if (input) input.value = '';
  runDeluluCommand(promptText);
}

// --- 6. ULTRA-FAST JARVIS COMMAND PIPELINE ---
async function runDeluluCommand(cmdText) {
  if (!cmdText) return;

  // 1. Immediately post user bubble to history feed
  appendHistoryItem('user', cmdText);

  // 2. Set Core State to THINKING with zero artificial delay
  setCoreState('THINKING', `Analyzing: “${cmdText}”`);

  const t0 = performance.now();

  try {
    // Sub-second API request to orchestrator
    const res = await api("/api/v1/chat/send", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: state.currentConvId,
        content: cmdText
      })
    });

    const elapsedMs = Math.round(performance.now() - t0);
    state.currentConvId = res.conversation_id;
    const asstMsg = res.assistant_message;

    // Update engine badge with SPDP Neural Engine (never leak model)
    const engineBadge = $('engine-badge');
    if (engineBadge) {
      engineBadge.textContent = `SPDP NEURAL ENGINE // ${elapsedMs}ms`;
    }

    // Check if tools were executed
    let toolTag = null;
    if (asstMsg.tool_calls && asstMsg.tool_calls.length) {
      setCoreState('EXECUTING', `Executed: ${asstMsg.tool_calls.map(t => t.tool).join(', ')}`);
      toolTag = asstMsg.tool_calls.map(t => t.tool).join(', ');
    }

    // 3. Immediately display in history feed and set state to SPEAKING
    appendHistoryItem('assistant', asstMsg.content, {
      tool: toolTag,
      brain: 'SPDP NEURAL ENGINE',
      elapsed: `${elapsedMs}ms`
    });

    setCoreState('SPEAKING', asstMsg.content);

    // 4. Trigger voice synthesis instantly
    speakText(asstMsg.content);

  } catch (err) {
    setCoreState('ERROR', err.message || 'Operation failed');
    appendHistoryItem('assistant', `Error: ${err.message || 'Could not complete command.'}`);
    setTimeout(() => setCoreState('IDLE'), 3500);
  }
}

// --- AUDIO PLAYBACK & UNLOCK ENGINE ---
let isAudioEngineUnlocked = false;

function unlockAudioEngine() {
  if (isAudioEngineUnlocked) return;
  isAudioEngineUnlocked = true;
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      const ctx = new AudioCtx();
      ctx.resume().then(() => ctx.close()).catch(() => {});
    }
    const player = $('delulu-audio-player');
    if (player) {
      player.play().catch(() => {});
      player.pause();
    }
  } catch(e) {}
}

window.addEventListener('click', unlockAudioEngine);
window.addEventListener('keydown', unlockAudioEngine);
window.addEventListener('touchstart', unlockAudioEngine);

// Spoken voice synthesis (Native Malayalam Neural Voice + Web Speech API)
function speakText(text) {
  unlockAudioEngine();

  // Cancel any ongoing audio/speech
  const player = $('delulu-audio-player');
  if (player) {
    player.pause();
    player.removeAttribute('src');
  }
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }

  // Strip markdown symbols for clean speech
  const clean = text.replace(/[*_#`[\]()]/g, '').trim();
  if (!clean) {
    setCoreState('IDLE');
    return;
  }

  const hasMalayalam = /[\u0D00-\u0D7F]/.test(clean);

  // If text contains Malayalam: use Malayalam voice
  if (hasMalayalam) {
    // 1. Check if browser has a native Malayalam voice
    if ('speechSynthesis' in window) {
      const voices = window.speechSynthesis.getVoices();
      const mlVoice = voices.find(v => v.lang.startsWith('ml') || v.name.toLowerCase().includes('malayalam'));
      if (mlVoice) {
        speakWithWebSpeech(clean, 'ml-IN', mlVoice);
        return;
      }
    }

    // 2. Stream Malayalam voice (ElevenLabs Mahendran J / Neural fallback) from backend
    playServerTTS(clean, 'malayalam');
    return;
  }

  // For English / Latin text: Use high-quality English voice
  if ('speechSynthesis' in window) {
    const voices = window.speechSynthesis.getVoices();
    const enVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Neural') || v.name.includes('Guy') || v.name.includes('Google') || v.name.includes('David')));
    speakWithWebSpeech(clean, 'en-US', enVoice);
  } else {
    playServerTTS(clean, 'en-GB-RyanNeural');
  }
}

function playServerTTS(text, voice) {
  const player = $('delulu-audio-player') || new Audio();
  const url = `/api/v1/voice/tts?text=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}`;
  
  let safetyTimeout = setTimeout(() => {
    if (coreState === 'SPEAKING') setCoreState('IDLE');
  }, 16000);

  player.src = url;
  player.onended = () => {
    clearTimeout(safetyTimeout);
    if (coreState === 'SPEAKING') setCoreState('IDLE');
  };
  player.onerror = (e) => {
    clearTimeout(safetyTimeout);
    console.warn("Server TTS playback issue, falling back to Web Speech:", e);
    speakWithWebSpeech(text, voice.startsWith('ml') ? 'ml-IN' : 'en-US');
  };

  const playPromise = player.play();
  if (playPromise !== undefined) {
    playPromise.catch(err => {
      clearTimeout(safetyTimeout);
      console.warn("Audio autoplay blocked by browser, falling back:", err);
      speakWithWebSpeech(text, voice.startsWith('ml') ? 'ml-IN' : 'en-US');
    });
  }
}

function speakWithWebSpeech(text, lang, voice = null) {
  if (!('speechSynthesis' in window)) {
    if (coreState === 'SPEAKING') setCoreState('IDLE');
    return;
  }

  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = lang;
  utter.rate = 1.0;
  if (voice) utter.voice = voice;

  let safetyTimeout = setTimeout(() => {
    if (coreState === 'SPEAKING') setCoreState('IDLE');
  }, 16000);

  utter.onend = () => {
    clearTimeout(safetyTimeout);
    if (coreState === 'SPEAKING') setCoreState('IDLE');
  };
  utter.onerror = () => {
    clearTimeout(safetyTimeout);
    if (coreState === 'SPEAKING') setCoreState('IDLE');
  };

  window.speechSynthesis.speak(utter);
}

// --- 7. HISTORY FEED MANAGEMENT ---
function appendHistoryItem(role, text, meta = {}) {
  const feed = $('history-feed');
  if (!feed) return;

  const emptyEl = $('history-empty');
  if (emptyEl) emptyEl.style.display = 'none';

  const item = document.createElement('div');
  item.className = `history-item ${role}`;

  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (role === 'user') {
    item.innerHTML = `
      <div class="bubble">${escapeHtml(text)}</div>
      <div class="history-meta">
        <span>YOU</span>
        <span>${timeStr}</span>
      </div>
    `;
  } else {
    const escaped = escapeHtml(text);
    const toolHtml = meta.tool ? `<div class="tool-tag">⚡ Tool: ${escapeHtml(meta.tool)}</div>` : '';
    item.innerHTML = `
      <div class="bubble">
        <div>${escaped}</div>
        ${toolHtml}
      </div>
      <div class="history-meta">
        <span class="brain-tag">⚡ SPDP ENGINE ${meta.elapsed ? '(' + meta.elapsed + ')' : ''}</span>
        <div style="display: flex; align-items: center; gap: 8px;">
          <button class="history-speak-btn" title="Replay voice" onclick="speakText('${escapeQuotes(text)}')">🔊 Listen</button>
          <span>${timeStr}</span>
        </div>
      </div>
    `;
  }

  feed.appendChild(item);
  feed.scrollTop = feed.scrollHeight;
}

function clearHistoryUI() {
  const feed = $('history-feed');
  if (!feed) return;
  feed.innerHTML = `
    <div class="history-empty" id="history-empty">
      <i>✦</i>
      <p>History cleared.<br>Speak or send a command to start.</p>
    </div>
  `;
}

async function createNewChatSession() {
  clearHistoryUI();
  state.currentConvId = null;
  setCoreState('IDLE', 'Started new session. How can I help?');
}

async function loadRecentHistory() {
  try {
    const convs = await api("/api/v1/chat/conversations");
    if (convs && convs.length) {
      const latest = convs[0];
      state.currentConvId = latest.id;
      const msgs = await api(`/api/v1/chat/conversations/${latest.id}/messages`);
      if (msgs && msgs.length) {
        const feed = $('history-feed');
        if (feed) feed.innerHTML = '';
        msgs.forEach(m => {
          appendHistoryItem(m.role, m.content, {
            tool: m.tool_calls && m.tool_calls.length ? m.tool_calls.map(t => t.tool).join(', ') : null,
            brain: 'SPDP NEURAL ENGINE'
          });
        });
      }
    }
  } catch (e) {
    console.log("Could not load recent history:", e);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[m]);
}

function escapeQuotes(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/\n/g, ' ');
}

// --- 8. AUTH CONTROLS & USER SESSION ---
function setupAuthTabs() {
  const tabs = document.querySelectorAll(".auth-tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.dataset.target;
      const loginForm = $("login-form");
      const regForm = $("register-form");
      const alertBox = $("auth-alert");
      if (alertBox) alertBox.style.display = "none";

      if (target === "login") {
        if (loginForm) loginForm.style.display = "block";
        if (regForm) regForm.style.display = "none";
      } else {
        if (loginForm) loginForm.style.display = "none";
        if (regForm) regForm.style.display = "block";
      }
    });
  });

  const gotoReg = $("goto-register");
  if (gotoReg) {
    gotoReg.onclick = (e) => {
      e.preventDefault();
      const regTab = document.querySelector('.auth-tab-btn[data-target="register"]');
      if (regTab) regTab.click();
    };
  }

  const gotoLogin = $("goto-login");
  if (gotoLogin) {
    gotoLogin.onclick = (e) => {
      e.preventDefault();
      const loginTab = document.querySelector('.auth-tab-btn[data-target="login"]');
      if (loginTab) loginTab.click();
    };
  }

  const loginForm = $("login-form");
  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();
      const email = $("login-email").value.trim();
      const password = $("login-password").value;
      const submitBtn = loginForm.querySelector("button[type='submit']");
      const origText = submitBtn.textContent;
      try {
        submitBtn.disabled = true;
        submitBtn.textContent = "VERIFYING CREDENTIALS...";
        showAuthAlert("Authenticating with Delulu Core...", "info");

        const data = await api("/api/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password })
        });

        state.token = data.access_token;
        localStorage.setItem("delulu_token", data.access_token);
        await loadCurrentUser();
        hideAuthOverlay();
        setCoreState("IDLE");
        loadRecentHistory();
      } catch (err) {
        showAuthAlert(err.message || "Invalid credentials. Please try again.", "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = origText;
      }
    };
  }

  const regForm = $("register-form");
  if (regForm) {
    regForm.onsubmit = async (e) => {
      e.preventDefault();
      const full_name = $("reg-name").value.trim();
      const email = $("reg-email").value.trim();
      const password = $("reg-password").value;
      const submitBtn = regForm.querySelector("button[type='submit']");
      const origText = submitBtn.textContent;
      try {
        submitBtn.disabled = true;
        submitBtn.textContent = "INITIALIZING SPACE...";
        showAuthAlert("Provisioning private workspace & memory vault...", "info");

        const data = await api("/api/v1/auth/register", {
          method: "POST",
          body: JSON.stringify({ full_name, email, password })
        });

        state.token = data.access_token;
        localStorage.setItem("delulu_token", data.access_token);
        await loadCurrentUser();
        hideAuthOverlay();
        setCoreState("IDLE");
        loadRecentHistory();
      } catch (err) {
        showAuthAlert(err.message || "Registration failed. Try a different username.", "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = origText;
      }
    };
  }

  const guestBtn = $("btn-guest-login");
  if (guestBtn) {
    guestBtn.onclick = async () => {
      const origText = guestBtn.textContent;
      try {
        guestBtn.disabled = true;
        guestBtn.textContent = "⚡ LAUNCHING INSTANT SPACE...";
        showAuthAlert("Launching private demo workspace...", "info");

        const data = await api("/api/v1/auth/guest", {
          method: "POST"
        });

        state.token = data.access_token;
        localStorage.setItem("delulu_token", data.access_token);
        await loadCurrentUser();
        hideAuthOverlay();
        setCoreState("IDLE");
        loadRecentHistory();
      } catch (err) {
        showAuthAlert(err.message || "Failed to launch instant demo. Please try again.", "error");
      } finally {
        guestBtn.disabled = false;
        guestBtn.textContent = origText;
      }
    };
  }
}

function showAuthAlert(msg, type = "info") {
  const alertBox = $("auth-alert");
  if (!alertBox) return;
  alertBox.className = `auth-alert ${type}`;
  alertBox.textContent = msg;
  alertBox.style.display = "flex";
}

async function loadCurrentUser() {
  const user = await api("/api/v1/auth/me");
  state.user = user;
  const link = $("link");
  if (link) {
    link.textContent = user.full_name || user.username || "JARVIS";
  }
}

function showAuthOverlay() {
  // Direct Access: Sign-in modal disabled
  const overlay = $("auth-overlay");
  if (overlay) overlay.style.display = "none";
}

function hideAuthOverlay() {
  const overlay = $("auth-overlay");
  if (overlay) overlay.style.display = "none";
}

function logout() {
  // In Direct Access mode, clear active conversation without locking the screen
  state.currentConvId = null;
  loadRecentHistory();
}

// --- 8. PROGRESSIVE WEB APP (PWA) 1-CLICK DESKTOP INSTALLATION ---
let deferredPWAInstallPrompt = null;

if ('serviceWorker' in navigator) {
  let isRefreshing = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!isRefreshing) {
      isRefreshing = true;
      console.log('New version detected! Auto-reloading website...');
      window.location.reload();
    }
  });

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js?v=3.1').then((reg) => {
      reg.update();
      console.log('DELULU PWA ServiceWorker active:', reg.scope);
    }).catch((err) => {
      console.log('PWA ServiceWorker note:', err);
    });
  });
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPWAInstallPrompt = e;
  const btn = $('pwa-install-btn');
  if (btn) {
    btn.style.display = 'inline-flex';
  }
});

window.addEventListener('appinstalled', () => {
  console.log('DELULU PWA installed successfully.');
  deferredPWAInstallPrompt = null;
  const btn = $('pwa-install-btn');
  if (btn) btn.style.display = 'none';
});

function promptPWAInstall() {
  if (deferredPWAInstallPrompt) {
    deferredPWAInstallPrompt.prompt();
    deferredPWAInstallPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        const btn = $('pwa-install-btn');
        if (btn) btn.style.display = 'none';
      }
      deferredPWAInstallPrompt = null;
    });
  } else {
    alert("To install DELULU as a desktop app:\nClick the Install icon (computer screen with down arrow) in your browser address bar at the top right.");
  }
}

// ==========================================================================
// ADA ACCESSIBILITY, REAL TELEMETRY & SYSTEM POWER FEATURES
// ==========================================================================

function announceToScreenReader(msg) {
  const el = $('a11y-announcer');
  if (!el || !msg) return;
  el.textContent = '';
  setTimeout(() => { el.textContent = msg; }, 40);
}

// --- Real Hardware Telemetry Polling ---
let telemetryPollInterval = null;

function initTelemetrySystem() {
  fetchLiveTelemetry();
  if (!telemetryPollInterval) {
    telemetryPollInterval = setInterval(fetchLiveTelemetry, 4500);
  }
}

async function fetchLiveTelemetry(manual = false) {
  try {
    const data = await api("/api/v1/system/telemetry");
    if (!data || data.status === "error") return;

    // 1. Top HUD Quick Badges
    const cpuEl = $('tele-cpu');
    const ramEl = $('tele-ram');
    const battEl = $('tele-batt');
    const battWrap = $('tele-batt-wrap');

    if (cpuEl && data.cpu) cpuEl.textContent = Math.round(data.cpu.percent);
    if (ramEl && data.memory) ramEl.textContent = Math.round(data.memory.percent);
    if (battEl && data.battery) {
      battEl.textContent = data.battery.percent;
      if (battWrap) battWrap.style.display = 'inline-flex';
    } else if (battWrap && !data.battery) {
      battWrap.style.display = 'none';
    }

    // 2. Full Diagnostics Modal Fields
    const diagCpuVal = $('diag-cpu-val');
    const diagCpuCores = $('diag-cpu-cores');
    const diagRamVal = $('diag-ram-val');
    const diagRamGb = $('diag-ram-gb');
    const diagBattVal = $('diag-batt-val');
    const diagBattStat = $('diag-batt-stat');
    const diagDiskVal = $('diag-disk-val');
    const diagDiskTotal = $('diag-disk-total');
    const diagUptime = $('diag-uptime');
    const diagOs = $('diag-os');

    if (diagCpuVal && data.cpu) diagCpuVal.textContent = data.cpu.percent;
    if (diagCpuCores && data.cpu) diagCpuCores.textContent = data.cpu.cores;
    if (diagRamVal && data.memory) diagRamVal.textContent = data.memory.percent;
    if (diagRamGb && data.memory) diagRamGb.textContent = `${data.memory.used_gb} / ${data.memory.total_gb}`;
    
    if (diagBattVal && data.battery) {
      diagBattVal.textContent = data.battery.percent;
      if (diagBattStat) diagBattStat.textContent = data.battery.power_plugged ? "⚡ Plugged in / Charging" : "🔋 On Battery Power";
    } else if (diagBattVal) {
      diagBattVal.textContent = "AC";
      if (diagBattStat) diagBattStat.textContent = "Desktop Workstation (AC Power)";
    }

    if (diagDiskVal && data.disk) diagDiskVal.textContent = data.disk.free_gb;
    if (diagDiskTotal && data.disk) diagDiskTotal.textContent = data.disk.total_gb;
    if (diagUptime) diagUptime.textContent = data.uptime || "Running";
    if (diagOs) diagOs.textContent = data.os === "win32" ? "Windows 11 / 10" : data.os;

    if (manual) {
      announceToScreenReader(`System hardware metrics refreshed. CPU at ${data.cpu?.percent} percent, RAM at ${data.memory?.percent} percent.`);
    }
  } catch (err) {
    console.warn("Telemetry note:", err);
  }
}

// Master Volume Controls
async function fetchCurrentVolume() {
  try {
    const res = await api("/api/v1/system/volume");
    if (res && res.level !== undefined) {
      updateVolumeUI(res.level);
    }
  } catch (e) {}
}

function updateVolumeUI(level) {
  const btnVal = $('vol-val-btn');
  const slider = $('master-vol-range');
  const sliderLbl = $('vol-slider-label');
  if (btnVal) btnVal.textContent = `${level}%`;
  if (slider) slider.value = level;
  if (sliderLbl) sliderLbl.textContent = `${level}%`;
}

function toggleVolumePopover() {
  const pop = $('vol-popover');
  if (!pop) return;
  const isHidden = pop.style.display === 'none' || !pop.style.display;
  pop.style.display = isHidden ? 'flex' : 'none';
  if (isHidden) fetchCurrentVolume();
}

let volDebounce = null;
function changeMasterVolume(val) {
  updateVolumeUI(val);
  clearTimeout(volDebounce);
  volDebounce = setTimeout(async () => {
    try {
      await api("/api/v1/system/volume", {
        method: "POST",
        body: JSON.stringify({ level: parseInt(val) })
      });
      announceToScreenReader(`System volume adjusted to ${val} percent.`);
    } catch (e) {}
  }, 200);
}

// Instant Desktop Screenshot Action
async function triggerQuickScreenshot() {
  announceToScreenReader("Capturing screenshot of your Windows display...");
  try {
    const res = await api("/api/v1/system/action", {
      method: "POST",
      body: JSON.stringify({ action: "screenshot" })
    });

    if (res && res.status === "success") {
      playJarvisChime();
      appendHistoryItem("assistant", `📸 Screenshot saved to Desktop: ${res.filename}`);
      announceToScreenReader(`Screenshot captured successfully: ${res.filename}`);
    } else {
      appendHistoryItem("assistant", `Could not take screenshot: ${res.message || "Driver error"}`);
    }
  } catch (err) {
    appendHistoryItem("assistant", `Screenshot failed: ${err.message}`);
  }
}

// Accessible Native Dialog Handlers
function openShortcutsModal() {
  const d = $('shortcuts-dialog');
  if (d && typeof d.showModal === 'function') {
    d.showModal();
    announceToScreenReader("Keyboard shortcuts guide opened. Press Escape to close.");
  }
}

function closeShortcutsModal() {
  const d = $('shortcuts-dialog');
  if (d && typeof d.close === 'function') d.close();
}

function openDiagnosticsModal() {
  const d = $('diagnostics-dialog');
  if (d && typeof d.showModal === 'function') {
    d.showModal();
    fetchLiveTelemetry(true);
  }
}

function closeDiagnosticsModal() {
  const d = $('diagnostics-dialog');
  if (d && typeof d.close === 'function') d.close();
}

// Comprehensive Global ADA Keyboard Navigation
function setupGlobalShortcuts() {
  window.addEventListener('keydown', (e) => {
    const isCtrl = e.ctrlKey || e.metaKey;
    const key = e.key;
    const isInputActive = ['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName);

    // 1. Ctrl + 0: Mic Toggle
    if (isCtrl && (key === '0' || e.code === 'Digit0' || e.code === 'Numpad0')) {
      e.preventDefault();
      triggerWake();
      return;
    }

    // 2. Ctrl + Shift + S: Quick Screenshot
    if (isCtrl && e.shiftKey && (key === 'S' || key === 's')) {
      e.preventDefault();
      triggerQuickScreenshot();
      return;
    }

    // 3. Ctrl + Shift + D: Hardware Diagnostics
    if (isCtrl && e.shiftKey && (key === 'D' || key === 'd')) {
      e.preventDefault();
      openDiagnosticsModal();
      return;
    }

    // 4. Ctrl + M: Toggle Voice Language
    if (isCtrl && (key === 'm' || key === 'M')) {
      e.preventDefault();
      toggleVoiceLang();
      announceToScreenReader(`Voice language switched to ${state.voiceLang === 'ml-IN' ? 'Malayalam' : 'English'}`);
      return;
    }

    // 5. Ctrl + K or '/' to focus command input
    if ((isCtrl && (key === 'k' || key === 'K')) || (key === '/' && !isInputActive)) {
      e.preventDefault();
      const cmdInput = $('cmd');
      if (cmdInput) cmdInput.focus();
      return;
    }

    // 6. '?' to open shortcuts modal
    if (key === '?' && !isInputActive) {
      e.preventDefault();
      openShortcutsModal();
      return;
    }

    // 7. Escape key
    if (key === 'Escape') {
      const volPop = $('vol-popover');
      if (volPop && volPop.style.display !== 'none') {
        volPop.style.display = 'none';
      }
      closeShortcutsModal();
      closeDiagnosticsModal();
      if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        setCoreState('IDLE');
        announceToScreenReader("Speech canceled.");
      }
    }
  });
}
