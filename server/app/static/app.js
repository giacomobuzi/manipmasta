/* ManipMasta — UI di comando (vanilla JS, nessuna dipendenza esterna). */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const TOKEN_KEY = "mm_token";
const RECIPE_KEY = "mm_active_recipe";

/* ------------------------------------------------------------ stato client */
const S = {
  token: null, ws: null, wsTry: 0, online: false, mqtt: false,
  st: null, recipes: [], step: 1, active: null, lastDoughGap: null, pingT: null,
};
try { S.token = localStorage.getItem(TOKEN_KEY); } catch (e) { /* storage non disponibile */ }
try { S.active = JSON.parse(localStorage.getItem(RECIPE_KEY) || "null"); } catch (e) { S.active = null; }

/* token passato dall'app Android o da link: #token=... */
(function tokenFromHash() {
  const m = location.hash.match(/token=([^&]+)/);
  if (m) {
    S.token = decodeURIComponent(m[1]);
    try { localStorage.setItem(TOKEN_KEY, S.token); } catch (e) {}
    history.replaceState(null, "", location.pathname + location.search);
  }
})();

/* ------------------------------------------------------------ util */
const fmt = (v, d = 1) => (v === null || v === undefined || isNaN(v)) ? "—" :
  Number(v).toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtDur = (s) => {
  if (s === null || s === undefined) return "—";
  s = Math.round(s);
  const m = Math.floor(s / 60), r = s % 60;
  return m ? `${m} min ${String(r).padStart(2, "0")} s` : `${r} s`;
};
const fmtTime = (ts) => new Date(ts * 1000).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const fmtDate = (ts) => new Date(ts * 1000).toLocaleString("it-IT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let toastT = null;
function toast(msg, bad = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = "toast"), bad ? 4500 : 2600);
}

/* ------------------------------------------------------------ API */
async function api(path, opts = {}) {
  const headers = { Authorization: `Bearer ${S.token}` };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(path, {
    method: opts.method || "GET", headers, keepalive: !!opts.keepalive,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401) { logout("Token non valido o scaduto."); throw new Error("401"); }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) {
    let msg = data && data.detail;
    if (Array.isArray(msg)) msg = msg.map((d) => (d.msg || "").replace(/^Value error, /, "")).join("; ");
    throw new Error(msg || `Errore ${res.status}`);
  }
  return data;
}

async function cmd(line, { quiet = false, keepalive = false } = {}) {
  try {
    const r = await api("/api/cmd", { method: "POST", body: { cmd: line }, keepalive });
    showResp(r);
    if (!quiet && r.resp && !r.ok) toast(errText(r.resp), true);
    if (!quiet && r.timeout) toast(`${line}: nessuna risposta dalla macchina`, true);
    return r;
  } catch (e) {
    if (e.message !== "401") { toast(e.message, true); setLast(e.message, true); }
    return null;
  }
}

const ERR = {
  E01: "comando sconosciuto", E02: "parametro non valido", E03: "eseguire prima l'homing",
  E04: "lo stato attuale non lo consente", E05: "fuori dai limiti", E06: "portale non in sede",
  E07: "emergenza attiva", E08: "allarme driver",
};
function errText(resp) {
  const m = /^ERR\s+(E\d\d)\s*(.*)$/i.exec(resp || "");
  if (!m) return resp;
  return `${ERR[m[1].toUpperCase()] || m[1]}${m[2] ? ` (${m[2]})` : ""}`;
}
function setLast(text, bad) {
  const el = $("#lastResp");
  el.textContent = text;
  el.className = "last" + (bad ? " err" : "");
}
function showResp(r) {
  if (!r) return;
  if (r.resp) setLast(`${r.cmd} → ${r.ok ? r.resp : errText(r.resp)}`, !r.ok);
  else setLast(`${r.cmd} → nessuna risposta entro 2 s`, true);
}

/* ------------------------------------------------------------ login */
function showLogin(msg = "") {
  $("#app").hidden = true;
  $("#login").hidden = false;
  $("#loginErr").textContent = msg;
  setTimeout(() => $("#tokenInput").focus(), 50);
}
function logout(msg = "") {
  S.token = null;
  try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
  if (S.ws) { S.ws.onclose = null; S.ws.close(); S.ws = null; }
  showLogin(msg);
}
$("#loginForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const tok = $("#tokenInput").value.trim();
  if (!tok) return;
  try {
    const r = await fetch("/api/state", { headers: { Authorization: `Bearer ${tok}` } });
    if (r.status === 401) { $("#loginErr").textContent = "Token non valido."; return; }
    if (!r.ok) { $("#loginErr").textContent = `Server non raggiungibile (${r.status}).`; return; }
  } catch (e) { $("#loginErr").textContent = "Server non raggiungibile."; return; }
  S.token = tok;
  try { localStorage.setItem(TOKEN_KEY, tok); } catch (e) {}
  $("#tokenInput").value = "";
  start();
});
$("#logoutBtn").addEventListener("click", () => logout());

/* ------------------------------------------------------------ WebSocket */
function connectWs() {
  if (!S.token) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(S.token)}`);
  S.ws = ws;
  ws.onopen = () => {
    S.wsTry = 0;
    clearInterval(S.pingT);
    S.pingT = setInterval(() => ws.readyState === 1 && ws.send("ping"), 20000);
  };
  ws.onmessage = (m) => {
    let msg;
    try { msg = JSON.parse(m.data); } catch (e) { return; }
    onMsg(msg);
  };
  ws.onclose = (e) => {
    clearInterval(S.pingT);
    if (e.code === 4401) { logout("Token non valido."); return; }
    S.online = false;
    renderState();
    const delay = Math.min(10000, 500 * 2 ** S.wsTry++);
    setTimeout(() => S.token && connectWs(), delay);
  };
}

function onMsg({ type, data }) {
  switch (type) {
    case "state": S.st = data; renderState(); break;
    case "online": S.online = !!data; renderState(); break;
    case "mqtt": S.mqtt = !!data; renderState(); break;
    case "event": onEvent(data); break;
    case "resp": addLog(data, /^OK/i.test(data) ? "ok" : "bad"); break;
    case "cmd": addLog(`→ ${data}`, "cmd"); break;
    case "history": if (!$("#tab-history").hidden) loadHistory(); break;
  }
  if (window.ManipMastaAndroid && typeof window.ManipMastaAndroid.onMessage === "function") {
    try { window.ManipMastaAndroid.onMessage(JSON.stringify({ type, data })); } catch (e) {}
  }
}

function onEvent(ev) {
  const t = ev.text || "";
  addLog(t, /^(ALARM|ESTOP)/.test(t) ? "bad" : "ev", ev.ts);
  if (t === "CYCLE_DONE") {
    toast("Ciclo completato");
    if (navigator.vibrate) navigator.vibrate([120, 80, 120]);
    if (S.active) { S.active.done = true; saveActive(); }
  } else if (t === "CYCLE_START") {
    if (S.active && Date.now() - S.active.sent > 60000) clearActive();
    if (S.active) { S.active.started = Date.now(); S.active.done = false; saveActive(); }
  } else if (/^(ALARM|ESTOP)/.test(t)) {
    toast(t === "ESTOP" ? "Emergenza attiva" : `Allarme: ${t.slice(6)}`, true);
    if (navigator.vibrate) navigator.vibrate(400);
  } else if (t === "STOP") {
    toast("Macchina fermata");
  }
}
function saveActive() { try { localStorage.setItem(RECIPE_KEY, JSON.stringify(S.active)); } catch (e) {} }
function clearActive() { S.active = null; try { localStorage.removeItem(RECIPE_KEY); } catch (e) {} }

/* ------------------------------------------------------------ rendering stato */
const ST = {
  BOOT: ["Avvio", "La scheda si sta avviando", "y", false],
  IDLE: ["Da azzerare", "Esegui l'homing prima di muovere", "y", false],
  HOMING: ["Homing", "Ricerca dei finecorsa in corso", "g", true],
  READY: ["Pronta", "In attesa di comandi", "g", false],
  MOVING: ["In movimento", "Movimento manuale", "g", true],
  RUNNING: ["Ciclo in corso", "Sfogliatura in esecuzione", "g", true],
  PAUSED: ["In pausa", "Rullo fermo in quota: Riprendi o STOP", "y", false],
  ALARM: ["Allarme", "Rimuovi la causa e premi Reset allarmi", "r", false],
  ESTOP: ["Emergenza", "Ripristina il fungo e premi Reset allarmi", "r", true],
};

function chip(k, s, text) {
  const li = $(`#chips li[data-k="${k}"]`);
  li.dataset.s = s;
  li.lastChild.textContent = text;
}

function renderState() {
  const st = S.st;
  const live = S.online && st;
  const [name, desc, tone, blink] = live ? (ST[st.st] || [st.st, "", "y", false]) :
    ["Non collegata", S.mqtt === false && S.ws && S.ws.readyState === 1 ? "Server senza collegamento al broker MQTT" :
      (S.ws && S.ws.readyState === 1 ? "La macchina non è in linea" : "Collegamento al server in corso…"), "", false];
  $("#stName").textContent = name;
  let d = desc;
  if (live && st.alm) d = `${desc} · causa: ${st.alm}`;
  $("#stDesc").textContent = d;
  $(".status").dataset.tone = tone;
  const tw = $("#tower");
  tw.dataset.l = tone;
  if (blink) tw.dataset.blink = ""; else delete tw.dataset.blink;

  chip("online", S.online ? "ok" : "bad", S.online ? "In linea" : "Non in linea");
  if (st) {
    const i = st.in || {};
    chip("hm", st.hm ? "ok" : "warn", st.hm ? "Azzerata" : "Non azzerata");
    chip("seat", i.seat ? "ok" : "bad", i.seat ? "In sede" : "Portale fuori sede");
    chip("estop", i.estop ? "bad" : "ok", i.estop ? "Emergenza premuta" : "Emergenza ok");
    chip("curt", i.curt ? "bad" : "ok", i.curt ? "Barriera interrotta" : "Barriera libera");
    chip("en", st.en ? "ok" : "warn", st.en ? "Driver on" : "Driver off");
  }

  $("#roX").textContent = st ? fmt(st.x, 1) : "—";
  $("#roG").textContent = st ? fmt(st.g, 2) : "—";
  const c = st && st.cyc;
  const inCycle = st && (st.st === "RUNNING" || st.st === "PAUSED");
  $("#roP").textContent = c && c.np ? `${c.pass}/${c.np}` : "—";
  const pr = $("#progress");
  if (c && c.np && (inCycle || (S.active && S.active.done))) {
    pr.hidden = false;
    const frac = inCycle ? Math.max(0, (c.pass - 1) / c.np) : 1;
    $("#progBar").style.width = `${Math.round(frac * 100)}%`;
    let txt = inCycle ? `Passata ${c.pass} di ${c.np} · gap di lavoro ${fmt(c.gap, 1)} mm` : `Ciclo completato: ${c.np} passate`;
    if (S.active && S.active.name) txt = `${S.active.name} · ${txt}`;
    if (inCycle && S.active && S.active.started && S.active.t_est) {
      const left = S.active.t_est - (Date.now() - S.active.started) / 1000;
      if (left > 0) txt += ` · circa ${fmtDur(left)} alla fine`;
    }
    $("#progTxt").textContent = txt;
  } else pr.hidden = true;

  // pulsanti
  const enB = $("#enableBtn");
  enB.textContent = st && st.en ? "Disabilita driver" : "Abilita driver";
  enB.classList.toggle("on", !!(st && st.en));
  const pB = $("#pauseBtn");
  if (st && st.st === "PAUSED") { pB.textContent = "Riprendi"; pB.disabled = false; }
  else { pB.textContent = "Pausa"; pB.disabled = !(st && st.st === "RUNNING"); }
  const canMove = live && st.st === "READY";
  $$(".jogb, .goto .btn").forEach((b) => (b.disabled = !canMove));
  renderScheme();
}

/* ------------------------------------------------------------ schema SVG */
const SX = 0.46;           // px/mm orizzontale (tavolo 2000 mm su 920 px)
const TABLE_Y = 250, ROLL_R = 23;
const gpx = (g) => 150 * Math.sqrt(Math.max(0, Math.min(150, g)) / 150); // gap ingrandito (non lineare)
const xpx = (x) => 500 + x * SX;
let view = "side";

function currentS() {
  const st = S.st, a = S.active;
  if (!st || !a || !st.cyc || !st.cyc.np) return null;
  const k = Math.max(0, (st.cyc.pass || 1) - 1);
  return a.s0 + (a.s1 - a.s0) * (st.cyc.np > 1 ? k / (st.cyc.np - 1) : 1);
}

function renderScheme() {
  const st = S.st;
  const x = st ? st.x : 0, g = st ? st.g : 150;
  const moving = st && ["HOMING", "MOVING", "RUNNING"].includes(st.st);
  $(".scheme").classList.toggle("moving", !!moving);
  const cy = TABLE_Y - gpx(g) - ROLL_R;
  $("#carriage").setAttribute("transform", `translate(${xpx(x).toFixed(1)} 0)`);
  $("#roller").setAttribute("transform", `translate(0 ${cy.toFixed(1)})`);
  $("#zrod").setAttribute("y2", cy.toFixed(1));
  const rot = st ? ((st.r || 0) / (Math.PI * 100)) * 360 : 0;
  $("#spoke").setAttribute("transform", `rotate(${(rot % 360).toFixed(1)})`);
  const gy = cy + ROLL_R;
  $("#gapLine").setAttribute("y1", gy.toFixed(1));
  $("#gapLine").setAttribute("y2", TABLE_Y);
  $("#gapT1").setAttribute("y1", gy.toFixed(1));
  $("#gapT1").setAttribute("y2", gy.toFixed(1));
  const gt = $("#gapTxt");
  gt.textContent = st ? `${fmt(g, 1)} mm` : "—";
  gt.setAttribute("y", Math.min(TABLE_Y - 6, (gy + TABLE_Y) / 2 + 8).toFixed(1));
  // il testo va dal lato con più spazio
  const right = xpx(x) < 760;
  gt.setAttribute("x", right ? 54 : -54);
  gt.setAttribute("text-anchor", right ? "start" : "end");
  $$("#gapDim line").forEach((l, i) => {
    const sgn = right ? 1 : -1;
    if (i === 0) { l.setAttribute("x1", 34 * sgn); l.setAttribute("x2", 34 * sgn); }
    else { l.setAttribute("x1", 28 * sgn); l.setAttribute("x2", 40 * sgn); }
  });

  // impasto: palla a riposo, sfoglia durante/dopo il ciclo
  const s = currentS();
  let half, thick, cxm = S.active ? S.active.cx || 0 : 0;
  const inCycle = st && ["RUNNING", "PAUSED"].includes(st.st);
  if (s !== null && (inCycle || (S.active && S.active.done))) {
    const gw = inCycle ? st.cyc.gap : (S.lastDoughGap ?? st.cyc.gap);
    if (inCycle) S.lastDoughGap = Math.min(gw, S.lastDoughGap ?? gw);
    half = s; thick = gpx(S.lastDoughGap ?? gw);
  } else if (inCycle) {
    // ciclo avviato da un altro client: larghezza indicativa, spessore dal gap di lavoro
    S.lastDoughGap = Math.min(st.cyc.gap, S.lastDoughGap ?? st.cyc.gap);
    half = 260; thick = gpx(S.lastDoughGap); cxm = 0;
  } else {
    half = 140; thick = gpx(Math.min(30, g)); cxm = 0; S.lastDoughGap = null;
  }
  const L = xpx(cxm - half), R = xpx(cxm + half), T = TABLE_Y - thick;
  const rr = Math.min(thick, 40);
  $("#dough").setAttribute("d",
    `M${L.toFixed(1)} ${TABLE_Y} C${(L + rr * 0.1).toFixed(1)} ${T.toFixed(1)} ${(L + rr).toFixed(1)} ${T.toFixed(1)} ${(L + rr * 1.6).toFixed(1)} ${T.toFixed(1)} ` +
    `L${(R - rr * 1.6).toFixed(1)} ${T.toFixed(1)} C${(R - rr).toFixed(1)} ${T.toFixed(1)} ${(R - rr * 0.1).toFixed(1)} ${T.toFixed(1)} ${R.toFixed(1)} ${TABLE_Y} Z`);
  // vista dall'alto
  $("#rollerTop").setAttribute("transform", `translate(${xpx(x).toFixed(1)} 0)`);
  const dt = $("#doughTop");
  dt.setAttribute("cx", xpx(cxm).toFixed(1));
  dt.setAttribute("rx", (half * SX).toFixed(1));
  dt.setAttribute("ry", (Math.min(170, 70 + half * 0.3) * SX * 1.6).toFixed(1));
}

$$(".scheme .seg button").forEach((b) => b.addEventListener("click", () => {
  view = b.dataset.view;
  $$(".scheme .seg button").forEach((o) => o.setAttribute("aria-selected", String(o === b)));
  $("#side").toggleAttribute("hidden", view !== "side");  // elementi SVG: niente proprietà .hidden
  $("#top").toggleAttribute("hidden", view !== "top");
  $("#scheme").setAttribute("viewBox", view === "side" ? "0 0 1000 300" : "0 50 1000 420");
  $("#viewLabel").textContent = view === "side" ? "Vista laterale" : "Vista dall'alto";
  $("#schemeCap").textContent = view === "side" ? "Scala orizzontale reale; altezza del gap ingrandita." :
    "Tavolo 2000 × 800 mm, rullo da 400 mm, impasto indicativo.";
}));

/* ------------------------------------------------------------ comandi */
$("#stopBtn").addEventListener("click", () => {
  cmd("STOP", { keepalive: true });
  if (navigator.vibrate) navigator.vibrate(60);
});
$$("[data-cmd]").forEach((b) => b.addEventListener("click", () => cmd(b.dataset.cmd)));
$("#enableBtn").addEventListener("click", () => cmd(S.st && S.st.en ? "ENABLE 0" : "ENABLE 1"));
$("#pauseBtn").addEventListener("click", () => cmd(S.st && S.st.st === "PAUSED" ? "RESUME" : "PAUSE"));
$$("#stepSeg button").forEach((b) => b.addEventListener("click", () => {
  S.step = parseFloat(b.dataset.step);
  $$("#stepSeg button").forEach((o) => o.setAttribute("aria-checked", String(o === b)));
}));
$$(".jogb").forEach((b) => b.addEventListener("click", () => {
  const d = S.step * parseInt(b.dataset.dir, 10);
  cmd(`JOG ${b.dataset.jog} ${d}`);
}));
$("#gotoX").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = $("#gotoXv").value;
  if (v !== "") cmd(`MOVE X ${v}`);
});
$("#gotoG").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = $("#gotoGv").value;
  if (v !== "") cmd(`GAP ${v}`);
});

/* ------------------------------------------------------------ tabs */
$$(".tabs button").forEach((b) => b.addEventListener("click", () => openTab(b.dataset.tab)));
function openTab(name) {
  $$(".tabs button").forEach((o) => o.setAttribute("aria-selected", String(o.dataset.tab === name)));
  $$(".pane").forEach((p) => (p.hidden = p.id !== `tab-${name}`));
  try { localStorage.setItem("mm_tab", name); } catch (e) {}
  if (name === "recipes") loadRecipes();
  if (name === "history") loadHistory();
  if (name === "params" && !$("#paramList").children.length) buildParams();
}

/* ------------------------------------------------------------ stima ciclo (come app/protocol.py) */
const PDEF = { x_vmax: 150, x_acc: 300, z_vmax: 8, z_acc: 20, g_max: 150 };
function moveTime(dist, v, a) {
  const d = Math.abs(dist);
  if (d <= 0) return 0;
  return d >= v * v / a ? d / v + v / a : 2 * Math.sqrt(d / a);
}
function numPasses(p) {
  if (!(p.dg > 0)) return NaN;
  return Math.max(0, Math.ceil(Math.round(((p.g0 - p.g1) / p.dg) * 1e9) / 1e9)) + Math.trunc(p.n);
}
function estimate(p) {
  const np = numPasses(p);
  if (!(np > 0)) return 0;
  const f = Math.min(p.f, PDEF.x_vmax), M = 60;
  let t = moveTime(20, PDEF.z_vmax, PDEF.z_acc);
  const x0 = p.cx - p.s0 - M;
  t += moveTime(x0, PDEF.x_vmax, PDEF.x_acc);
  t += moveTime(Math.min(PDEF.g_max, p.g0 + 20) - p.g0, PDEF.z_vmax, PDEF.z_acc);
  let gap = p.g0, x = x0;
  for (let k = 0; k < np; k++) {
    const s = p.s0 + (p.s1 - p.s0) * (np > 1 ? k / (np - 1) : 1);
    const nxt = Math.max(p.g1, gap - p.dg);
    const a = p.cx - s - M, b = p.cx + s + M;
    t += moveTime(a - x, f, PDEF.x_acc) + 2 * moveTime(b - a, f, PDEF.x_acc) + moveTime(gap - nxt, PDEF.z_vmax, PDEF.z_acc);
    gap = nxt; x = a;
  }
  t += moveTime(p.g1 + 30 - gap, PDEF.z_vmax, PDEF.z_acc) + moveTime(p.cx - x, PDEF.x_vmax, PDEF.x_acc);
  return t;
}

/* ------------------------------------------------------------ ricette */
function thickGlyph(g0, g1) {
  const h0 = Math.max(3, Math.min(20, g0 / 2.5)), h1 = Math.max(1.5, Math.min(20, g1 / 2.5));
  return `<svg viewBox="0 0 66 22" aria-hidden="true"><path d="M2 21 L2 ${21 - h0} Q14 ${21 - h0} 30 ${21 - h1} L64 ${21 - h1} L64 21 Z" fill="var(--dough)" stroke="var(--dough-edge)"/></svg>`;
}

async function loadRecipes() {
  try { S.recipes = await api("/api/recipes"); } catch (e) { return; }
  const ul = $("#recipeList");
  if (!S.recipes.length) {
    ul.innerHTML = `<li class="empty">Nessuna ricetta. Crea la prima con Nuova ricetta.</li>`;
    return;
  }
  ul.innerHTML = S.recipes.map((r) => `
    <li class="recipe">
      <h3>${esc(r.name)}</h3>
      <div class="thick">${thickGlyph(r.g0, r.g1)}<span><b>${fmt(r.g0, 1)}</b> → <b>${fmt(r.g1, 1)} mm</b></span></div>
      <div class="spec">
        <span>riduzione <b>${fmt(r.dg, 1)} mm</b></span>
        <span>velocità <b>${fmt(r.f, 0)} mm/s</b></span>
        <span>passate <b>${r.np}</b></span>
        <span>durata <b>${fmtDur(r.t_est)}</b></span>
      </div>
      ${r.note ? `<p class="note">${esc(r.note)}</p>` : ""}
      <div class="acts">
        <button class="btn primary" data-run="${r.id}">Avvia ciclo</button>
        <button class="btn" data-edit="${r.id}">Modifica</button>
      </div>
    </li>`).join("");
  $$("[data-run]", ul).forEach((b) => b.addEventListener("click", () => confirmRun(+b.dataset.run)));
  $$("[data-edit]", ul).forEach((b) => b.addEventListener("click", () => editRecipe(+b.dataset.edit)));
}

function ask(title, html, yesLabel = "Conferma") {
  const dlg = $("#confirmDlg");
  $("#confirmTitle").textContent = title;
  $("#confirmBody").innerHTML = html;
  $("#confirmYes").textContent = yesLabel;
  dlg.returnValue = "";
  dlg.showModal();
  return new Promise((res) => dlg.addEventListener("close", () => res(dlg.returnValue === "yes"), { once: true }));
}

async function confirmRun(id) {
  const r = S.recipes.find((x) => x.id === id);
  if (!r) return;
  const st = S.st;
  let warn = "";
  if (!S.online) warn = "La macchina non è in linea.";
  else if (!st || st.st !== "READY") warn = `Stato attuale: ${(ST[st && st.st] || ["?"])[0]}. La macchina deve essere Pronta (homing eseguito).`;
  else if (!st.in.seat) warn = "Portale non in sede.";
  const html = `
    <dl class="confirm-tbl">
      <dt>Ricetta</dt><dd>${esc(r.name)}</dd>
      <dt>Spessore</dt><dd>${fmt(r.g0, 1)} → ${fmt(r.g1, 1)} mm</dd>
      <dt>Passate doppie</dt><dd>${r.np}</dd>
      <dt>Durata stimata</dt><dd>${fmtDur(r.t_est)}</dd>
      <dt>Corsa</dt><dd>${fmt(r.cx - Math.max(r.s0, r.s1) - 60, 0)} … ${fmt(r.cx + Math.max(r.s0, r.s1) + 60, 0)} mm</dd>
    </dl>
    <p class="hint">Impasto al centro (X = ${fmt(r.cx, 0)} mm), zona del tavolo libera.</p>
    <code>${esc(r.run_line)}</code>
    ${warn ? `<p class="warnbox">${esc(warn)}</p>` : ""}`;
  if (!(await ask("Avviare il ciclo?", html, "Avvia ciclo"))) return;
  S.active = { id: r.id, name: r.name, s0: r.s0, s1: r.s1, cx: r.cx, np: r.np, t_est: r.t_est, sent: Date.now(), done: false };
  saveActive();
  try {
    const res = await api(`/api/recipes/${id}/run`, { method: "POST" });
    showResp(res);
    if (res.ok) toast(`Ciclo avviato: ${r.name}`);
    else { toast(res.resp ? errText(res.resp) : "Nessuna risposta dalla macchina", true); }
  } catch (e) { if (e.message !== "401") toast(e.message, true); }
}

const RFIELDS = ["name", "cx", "s0", "s1", "g0", "g1", "dg", "f", "n", "od", "note"];
let editingId = null;
function editRecipe(id) {
  editingId = id;
  const f = $("#recipeForm");
  const r = id ? S.recipes.find((x) => x.id === id) :
    { name: "", cx: 0, s0: 150, s1: 300, g0: 40, g1: 5, dg: 3, f: 60, n: 2, od: 2, note: "" };
  RFIELDS.forEach((k) => (f.elements[k].value = r[k]));
  $("#recipeDlgTitle").textContent = id ? "Modifica ricetta" : "Nuova ricetta";
  $("#recipeDelete").hidden = !id;
  $("#recipeErr").textContent = "";
  updatePreview();
  $("#recipeDlg").showModal();
}
function formRecipe() {
  const f = $("#recipeForm"), o = {};
  RFIELDS.forEach((k) => (o[k] = ["name", "note"].includes(k) ? f.elements[k].value : parseFloat(f.elements[k].value)));
  o.n = Math.trunc(o.n);
  return o;
}
function updatePreview() {
  const p = formRecipe();
  const np = numPasses(p);
  const el = $("#recipePreview");
  if (!(np >= 0) || p.g0 < p.g1) { el.textContent = "Controlla gap e riduzione: g0 ≥ g1 e dg > 0."; return; }
  el.innerHTML = `Passate doppie <b>${np}</b> = ⌈(${fmt(p.g0, 1)} − ${fmt(p.g1, 1)}) / ${fmt(p.dg, 1)}⌉ + ${p.n} · durata stimata <b>${fmtDur(estimate(p))}</b>`;
}
$("#recipeForm").addEventListener("input", updatePreview);
$("#newRecipe").addEventListener("click", () => editRecipe(null));
$("#recipeCancel").addEventListener("click", () => $("#recipeDlg").close());
$("#recipeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = formRecipe();
  try {
    await api(editingId ? `/api/recipes/${editingId}` : "/api/recipes", { method: editingId ? "PUT" : "POST", body });
    $("#recipeDlg").close();
    toast("Ricetta salvata");
    loadRecipes();
  } catch (err) { $("#recipeErr").textContent = err.message; }
});
$("#recipeDelete").addEventListener("click", async () => {
  const r = S.recipes.find((x) => x.id === editingId);
  $("#recipeDlg").close();
  if (!(await ask("Eliminare la ricetta?", `<p>${esc(r ? r.name : "")} verrà eliminata definitivamente.</p>`, "Elimina"))) return;
  try { await api(`/api/recipes/${editingId}`, { method: "DELETE" }); toast("Ricetta eliminata"); loadRecipes(); }
  catch (err) { toast(err.message, true); }
});

/* ------------------------------------------------------------ storico */
const OUT = { completato: "ok", interrotto: "warn", allarme: "bad", emergenza: "bad", "in corso": "run", sconosciuto: "warn" };
async function loadHistory() {
  let rows;
  try { rows = await api("/api/history?limit=100"); } catch (e) { return; }
  const ul = $("#historyList");
  if (!rows.length) { ul.innerHTML = `<li class="empty">Nessun ciclo registrato. I cicli avviati compariranno qui.</li>`; return; }
  ul.innerHTML = rows.map((h) => `
    <li>
      <span class="h-name">${esc(h.recipe_name || "Ciclo manuale")}</span>
      <span class="badge ${OUT[h.outcome] || "warn"}">${esc(h.outcome)}</span>
      <span class="h-meta">${fmtDate(h.started_at)} · ${h.duration_s != null ? fmtDur(h.duration_s) : "in corso"} ·
        passate ${h.passes_done}${h.np ? "/" + h.np : ""}${h.detail ? " · " + esc(h.detail) : ""}</span>
    </li>`).join("");
}
$("#histReload").addEventListener("click", loadHistory);

/* ------------------------------------------------------------ parametri (SPEC §2.2) */
const PARAMS = [
  ["Assi", [
    ["x_spm", "step/mm asse X"], ["z_spm", "step/mm asse Z"], ["r_spm", "step/mm superficie rullo"],
    ["x_min", "limite software X min (mm)"], ["x_max", "limite software X max (mm)"],
    ["g_min", "gap minimo (mm)"], ["g_max", "gap massimo (mm)"],
    ["z_home_gap", "gap reale con Z sul finecorsa alto"], ["x_home_off", "offset dopo homing X (mm)"],
  ]],
  ["Velocità", [
    ["x_vmax", "velocità max X (mm/s)"], ["x_acc", "accelerazione X (mm/s²)"],
    ["z_vmax", "velocità max Z (mm/s)"], ["z_acc", "accelerazione Z (mm/s²)"], ["od", "overdrive rullo (%)"],
  ]],
  ["Rete", [
    ["ip", "indirizzo IP"], ["gw", "gateway"], ["mask", "subnet mask"], ["dns", "DNS"],
    ["mqtt_host", "broker MQTT"], ["mqtt_port", "porta MQTT"], ["mqtt_user", "utente MQTT"], ["mqtt_pass", "password MQTT (solo scrittura)"],
  ]],
];
function buildParams() {
  const box = $("#paramList");
  box.innerHTML = PARAMS.map(([grp, keys]) => `<h3 class="pgroup">${grp}</h3>` + keys.map(([k, d]) => `
    <form class="param" data-k="${k}">
      <label class="p-k" for="p_${k}">${k}<span class="p-d">${esc(d)}</span></label>
      <input id="p_${k}" name="v" ${k === "mqtt_pass" ? 'type="password" autocomplete="new-password"' :
        ["ip", "gw", "mask", "dns", "mqtt_host", "mqtt_user"].includes(k) ? 'type="text" spellcheck="false"' : 'type="text" inputmode="decimal"'}>
      <button class="btn" type="submit">Imposta</button>
    </form>`).join("")).join("");
  $$(".param", box).forEach((f) => {
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const v = f.elements.v.value.trim().replace(",", ".");
      if (!v) return;
      const r = await cmd(`SET ${f.dataset.k} ${v}`);
      if (r && r.ok) { f.elements.v.classList.remove("dirty"); toast(`${f.dataset.k} impostato`); }
    });
    f.elements.v.addEventListener("input", () => f.elements.v.classList.add("dirty"));
  });
}
async function readParams() {
  buildParams();
  for (const f of $$(".param")) {
    const k = f.dataset.k;
    if (k === "mqtt_pass") continue;
    const r = await cmd(`GET ${k}`, { quiet: true });
    if (!r) return;
    if (r.timeout) { toast("La macchina non risponde", true); return; }
    const m = /^OK\s+GET\s+(\S+)\s+(.*)$/i.exec(r.resp || "");
    if (m) { f.elements.v.value = m[2]; f.elements.v.classList.remove("dirty"); }
  }
  toast("Parametri letti");
}
$("#paramsRead").addEventListener("click", readParams);
$("#paramsSave").addEventListener("click", async () => {
  if (await ask("Salvare in EEPROM?", "<p>I valori attuali resteranno anche dopo lo spegnimento.</p>", "Salva")) {
    const r = await cmd("SAVE");
    if (r && r.ok) toast("Parametri salvati in EEPROM");
  }
});
$("#paramsDefaults").addEventListener("click", async () => {
  if (await ask("Ripristinare i default?", "<p>Tutti i parametri tornano ai valori di fabbrica (SPEC). Per renderli permanenti usa poi Salva in EEPROM. Ricontrolla la rete prima di salvare.</p>", "Ripristina")) {
    const r = await cmd("DEFAULTS");
    if (r && r.ok) readParams();
  }
});

/* ------------------------------------------------------------ log */
function addLog(text, cls = "ev", ts = Date.now() / 1000) {
  const ol = $("#logList");
  const li = document.createElement("li");
  li.className = cls;
  li.innerHTML = `<time>${fmtTime(ts)}</time><span>${esc(text)}</span>`;
  ol.prepend(li);
  while (ol.children.length > 300) ol.lastChild.remove();
}
$("#logClear").addEventListener("click", () => ($("#logList").innerHTML = ""));

/* ------------------------------------------------------------ avvio */
async function start() {
  $("#login").hidden = true;
  $("#app").hidden = false;
  try {
    const s = await api("/api/state");
    S.st = s.state; S.online = s.online; S.mqtt = s.mqtt;
    renderState();
    const evs = await api("/api/events?limit=100");
    $("#logList").innerHTML = "";
    evs.slice().reverse().forEach((e) => addLog(e.text, /^(ALARM|ESTOP)/.test(e.text) ? "bad" : "ev", e.ts));
  } catch (e) { if (e.message === "401") return; }
  let tab = "cmd";
  try { tab = localStorage.getItem("mm_tab") || "cmd"; } catch (e) {}
  openTab($(`.tabs [data-tab="${tab}"]`) ? tab : "cmd");
  if (!S.ws) connectWs();
}

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
renderScheme();
if (S.token) start(); else showLogin();
