/* rulekit designer — vanilla JS, no build step.
   The stepper replays the engine's serialized Decision stream: the engine
   records every mutation, so the UI needs no engine pauses — just a cursor. */

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};

const state = {
  trace: null,          // last /api/trace response
  decisions: [],        // flattened [{sentence, ...decision}]
  cursor: -1,
  currentDoc: null,     // path of the doc in the editor
};

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

function setStatus(text, cls) {
  const s = $("status");
  s.textContent = text;
  s.style.color = cls === "err" ? "var(--red)" : cls === "ok" ? "var(--green)" : "var(--dim)";
}

/* ---------- project / file tree ---------- */

async function loadProject() {
  const p = await api("GET", "/api/project");
  $("project-name").textContent = p.name;
  $("fingerprint").textContent = p.fingerprint;
  const target = $("impact-target");
  target.replaceChildren();
  for (const t of p.impact_targets) {
    const opt = el("option", "", t);
    opt.value = t;
    target.append(opt);
  }
  target.onchange = () => {
    $("spend-look").classList.toggle("hidden", target.value !== "test");
    $("spend-look-cb").checked = false;
  };
  const tree = $("file-tree");
  tree.replaceChildren();
  let pack = null;
  for (const doc of p.docs) {
    if (doc.pack !== pack) {
      pack = doc.pack;
      tree.append(el("div", "pack", pack));
    }
    const f = el("div", "file", doc.name);
    f.dataset.path = doc.path;
    f.onclick = () => openDoc(doc.path, f);
    tree.append(f);
  }
}

async function openDoc(path, node) {
  document.querySelectorAll("#file-tree .file.active").forEach((n) => n.classList.remove("active"));
  if (node) node.classList.add("active");
  const doc = await api("GET", `/api/doc?path=${encodeURIComponent(path)}`);
  state.currentDoc = path;
  $("editor").value = doc.content;
  $("editor-title").textContent = path.split("/").slice(-2).join("/");
  $("save-result").textContent = "";
}

async function saveDoc() {
  if (!state.currentDoc) return;
  setStatus("validating…");
  const res = await api("PUT", "/api/doc", { path: state.currentDoc, content: $("editor").value });
  const out = $("save-result");
  const lintBox = $("lint-box");
  lintBox.replaceChildren();
  if (!res.ok) {
    out.textContent = "✗ rejected (file rolled back)";
    out.style.color = "var(--red)";
    lintBox.append(el("div", "lint-item error", res.error));
    setStatus("compile failed — previous registry still live", "err");
    return;
  }
  out.textContent = "✓ compiled";
  out.style.color = "var(--green)";
  $("fingerprint").textContent = res.fingerprint;
  for (const f of res.lint) {
    lintBox.append(el("div", `lint-item ${f.level}`, `[${f.code}] ${f.message}`));
  }
  setStatus(`saved · ${res.lint.length} lint finding(s)`, "ok");
  if ($("trace-input").value.trim()) runTrace();  // live re-read
}

/* ---------- trace ---------- */

async function runTrace() {
  const text = $("trace-input").value.trim();
  if (!text) return;
  setStatus("reading…");
  const t = await api("POST", "/api/trace", { text });
  if (t.error) {
    setStatus(t.error, "err");
    return;
  }
  state.trace = t;
  state.decisions = t.sentences.flatMap((s) =>
    s.decisions.map((d) => ({ ...d, sentence: s.index, is_question: s.is_question }))
  );
  state.cursor = state.decisions.length - 1;
  renderAnswer(t);
  renderSentences(t);
  renderDecisions();
  renderFacts(t);
  renderGaps(t);
  selectDecision(state.cursor, false);
  setStatus(`read in ${t.rounds} round(s) · ${state.decisions.length} decisions`, "ok");
}

function renderAnswer(t) {
  const b = $("answer-banner");
  b.classList.remove("hidden", "number", "decline");
  const isAnswer = t.answer.kind === "number" || t.answer.kind === "verdict";
  b.classList.add(isAnswer ? "number" : "decline");
  b.replaceChildren(
    el("span", "big", isAnswer ? String(t.answer.value) : "declined"),
    el("span", "reason", t.answer.reason + (t.ask ? `   ·   ask ${t.ask.id} → ${JSON.stringify(t.ask.query)}` : "")),
  );
}

function senseBadgeClass(s) {
  return { name: "sense-name", verb: "sense-verb", noun: "sense-noun" }[s] || "";
}

function renderSentences(t) {
  const box = $("sentences");
  box.replaceChildren();
  for (const s of t.sentences) {
    const card = el("div", "sentence");
    const label = el("div", "label");
    label.append(
      s.is_question ? el("span", "q", "question · ") : el("span", "", `sentence ${s.index} · `),
      el("span", "", s.text),
    );
    card.append(label);
    const ribbon = el("div", "ribbon");
    for (const u of s.units) {
      const chip = el("div", "chip");
      chip.dataset.uid = `${s.index}:${u.uid}`;
      if (u.senses.includes("punct")) chip.classList.add("punct");
      if (u.unknown) chip.classList.add("unknown");
      if (u.ambiguous) chip.classList.add("ambiguous");
      if (u.pattern_consumed) chip.classList.add("consumed");
      chip.append(el("div", "", u.surface));
      const badges = el("div", "badges");
      for (const sense of u.senses.slice(0, 3)) {
        if (sense === "punct") continue;
        badges.append(el("span", `badge ${senseBadgeClass(sense)}`, sense));
      }
      if (u.value !== null && u.value !== undefined) {
        badges.append(el("span", "badge val", `${u.value_kind || "value"}=${u.value}`));
      }
      if (u.attributes.length) badges.append(el("span", "badge", `+${u.attributes.join("+")}`));
      if (badges.children.length) chip.append(badges);
      const obs = el("div", "obs");
      for (const ob of u.obligations) {
        obs.append(el("span", `ob ${ob.met ? "met" : "unmet"}`,
          ob.met ? `${ob.need}→${ob.target}` : `${ob.need}?${ob.optional ? " (opt)" : ""}`));
      }
      if (obs.children.length) chip.append(obs);
      ribbon.append(chip);
    }
    card.append(ribbon);
    box.append(card);
  }
}

function renderDecisions() {
  const box = $("decisions");
  box.replaceChildren();
  $("decision-count").textContent = `(${state.decisions.length})`;
  state.decisions.forEach((d, i) => {
    const row = el("div", "decision");
    row.dataset.index = i;
    row.append(
      el("span", "seq", `${d.sentence}·${String(d.seq).padStart(2, "0")}`),
      el("span", "kind", d.kind),
      el("span", "tgt", d.target_surface),
    );
    row.onclick = () => selectDecision(i, true);
    box.append(row);
  });
}

function fmtFeatures(obj) {
  if (!obj || !Object.keys(obj).length) return "∅";
  return Object.entries(obj)
    .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
    .join("\n");
}

function selectDecision(i, scroll) {
  if (i < 0 || i >= state.decisions.length) return;
  state.cursor = i;
  document.querySelectorAll(".decision.active").forEach((n) => n.classList.remove("active"));
  const row = document.querySelector(`.decision[data-index="${i}"]`);
  if (row) {
    row.classList.add("active");
    if (scroll !== false) row.scrollIntoView({ block: "nearest" });
  }
  const d = state.decisions[i];
  document.querySelectorAll(".chip.hl").forEach((n) => n.classList.remove("hl"));
  const chip = document.querySelector(`.chip[data-uid="${d.sentence}:${d.target}"]`);
  if (chip) chip.classList.add("hl");

  const detail = $("decision-detail");
  detail.classList.remove("dim");
  detail.replaceChildren();
  const kv = (k, v, cls) => {
    const row = el("div", "kv");
    row.append(el("span", "k", k), el("span", cls || "", v));
    detail.append(row);
  };
  kv("kind", d.kind);
  kv("target", `${d.target_surface}  (u${d.target}, sentence ${d.sentence})`);
  kv("reason", d.reason);
  if (d.rule_id) kv("rule", d.rule_id);
  const diff = el("div", "diff");
  const minus = el("div", "minus", `− ${fmtFeatures(d.before).replaceAll("\n", "\n− ")}`);
  const plus = el("div", "plus", `+ ${fmtFeatures(d.after).replaceAll("\n", "\n+ ")}`);
  diff.append(minus, plus);
  detail.append(diff);
}

function renderFacts(t) {
  const box = $("facts");
  box.replaceChildren();
  $("fact-count").textContent = `(${t.facts.length})`;
  for (const f of t.facts) {
    const card = el("div", "fact");
    card.append(
      el("span", "src", `${f.source} · s${f.sentence}`),
      el("span", "type", f.type),
      el("span", "", Object.entries(f.fields)
        .filter(([k]) => k !== "polarity" || f.fields[k] !== true)
        .map(([k, v]) => `${k}=${v}`).join("  ")),
    );
    box.append(card);
  }
  for (const c of t.collisions) {
    const card = el("div", "fact collision");
    card.append(
      el("span", "type", "COLLISION"),
      el("span", "", `${c.a}=${c.a_value} vs ${c.b}=${c.b_value} on ${JSON.stringify(c.key)}`),
    );
    box.append(card);
  }
}

function renderGaps(t) {
  const box = $("gaps");
  box.replaceChildren();
  const seen = new Set();
  for (const g of [...t.gaps, ...t.deficiencies]) {
    if (seen.has(g)) continue;
    seen.add(g);
    box.append(el("div", "gap", g));
  }
  if (!box.children.length) box.append(el("div", "dim", "none — the reading is saturated"));
}

/* ---------- impact ---------- */

function impactBody() {
  return {
    target: $("impact-target").value || "suite",
    spend_test_look: $("spend-look-cb").checked,
  };
}

async function runImpact() {
  const body = impactBody();
  setStatus(`running ${body.target}… (full slices take ~10s)`);
  const started = performance.now();
  const r = await api("POST", "/api/impact", body);
  if (r.error) { setStatus(r.error, "err"); return; }
  const s = $("impact-summary");
  s.replaceChildren();
  const a = r.aggregates;
  s.append(el("span", "bucket", `[${r.target}]`));
  s.append(el("span", "bucket", `✓ ${a.correct}`));
  s.append(el("span", "bucket", `✗ ${a.wrong} wrong`));
  s.append(el("span", "bucket", `− ${a.declined} declined`));
  s.append(el("span", "bucket", `precision ${a.precision === null ? "n/a" : (a.precision * 100).toFixed(1) + "%"}`));
  s.append(el("span", "bucket", `coverage ${(a.coverage * 100).toFixed(1)}%`));
  if (r.diff) {
    s.append(el("span", "bucket", `SOLVED ${r.diff.solved.length}`));
    s.append(el("span", "bucket", `BROKE ${r.diff.broke.length}`));
    s.append(el("span", "bucket", `DECL→WRONG ${r.diff.decl_to_wrong.length}`));
    s.append(el("span", `bucket ${r.diff.verdict.toLowerCase()}`, r.diff.verdict));
    const names = [...r.diff.solved.map((x) => `SOLVED ${x}`), ...r.diff.broke.map((x) => `BROKE ${x}`),
                   ...r.diff.decl_to_wrong.map((x) => `DECL→WRONG ${x}`)];
    if (names.length) s.append(el("span", "dim", "· " + names.slice(0, 6).join(", ")));
  } else if (r.target !== "test") {
    s.append(el("span", "dim", "· no baseline for this target yet"));
  }
  if (r.note) s.append(el("span", "dim", `· ${r.note}`));
  if (r.items) {
    const wrongs = Object.entries(r.items).filter(([, v]) => v.outcome === "wrong");
    if (wrongs.length) {
      s.append(el("span", "dim",
        "· wrongs: " + wrongs.slice(0, 5).map(([id, v]) => `${id} (${v.expected}→${v.got})`).join(", ")));
    }
  }
  const secs = ((performance.now() - started) / 1000).toFixed(1);
  setStatus(`${r.target}: ${a.items} items in ${secs}s`, a.wrong ? "err" : "ok");
  $("spend-look-cb").checked = false;
}

async function setBaseline() {
  const body = impactBody();
  setStatus(`snapshotting ${body.target} baseline…`);
  const r = await api("POST", "/api/baseline", body);
  if (r.error) { setStatus(r.error, "err"); return; }
  setStatus(`baseline [${r.target}]: ${r.aggregates.correct}/${r.aggregates.items} correct`, "ok");
}

/* ---------- wiring ---------- */

$("trace-btn").onclick = runTrace;
$("trace-input").addEventListener("keydown", (e) => { if (e.key === "Enter") runTrace(); });
$("save-btn").onclick = saveDoc;
$("editor").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); saveDoc(); }
});
$("impact-btn").onclick = runImpact;
$("baseline-btn").onclick = setBaseline;
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
  if (e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); selectDecision(state.cursor + 1); }
  if (e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); selectDecision(state.cursor - 1); }
});

/* ---------- resizable sidebar ---------- */

(function initResize() {
  const sidebar = $("sidebar");
  const handle = $("drag-handle");
  const saved = localStorage.getItem("rulekit.sidebarWidth");
  if (saved) sidebar.style.width = `${saved}px`;
  handle.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    handle.classList.add("dragging");
    document.body.classList.add("resizing");
    try { handle.setPointerCapture(e.pointerId); } catch { /* synthetic pointer */ }
    const move = (ev) => {
      const width = Math.min(window.innerWidth * 0.75, Math.max(240, ev.clientX));
      sidebar.style.width = `${width}px`;
    };
    const up = () => {
      handle.classList.remove("dragging");
      document.body.classList.remove("resizing");
      localStorage.setItem("rulekit.sidebarWidth", parseInt(sidebar.style.width, 10));
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    // window-level listeners: no dependence on pointer capture, and the
    // drag keeps tracking even when the cursor leaves the 5px handle
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  });
})();

loadProject();
