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
  interpretation: null, // explicitly confirmed query reading
  generationRules: [],
  candidate: null,
  reviewVerdict: null,
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
  await loadGenerationRules();
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

async function runTrace(interpretation = null) {
  const text = $("trace-input").value.trim();
  if (!text) return;
  setStatus("reading…");
  const t = await api("POST", "/api/trace", { text, interpretation });
  if (t.error) {
    setStatus(t.error, "err");
    return;
  }
  state.interpretation = interpretation;
  state.trace = t;
  state.decisions = t.sentences.flatMap((s) =>
    s.decisions.map((d) => ({ ...d, sentence: s.index, is_question: s.is_question }))
  );
  state.cursor = state.decisions.length - 1;
  renderAnswer(t);
  renderClarification(t);
  renderSentences(t);
  renderDecisions();
  renderFacts(t);
  renderGaps(t);
  renderSemantic(t);
  renderField(t);
  renderProof(t);
  selectDecision(state.cursor, false);
  const declines = (t.deixis?.observations || []).filter((o) => o.outcome === "declined").length;
  setStatus(
    `read in ${t.rounds} round(s) · ${state.decisions.length} decisions` +
    (declines ? ` · ${declines} deictic decline(s)` : ""),
    "ok",
  );
}

function renderAnswer(t) {
  const b = $("answer-banner");
  b.classList.remove("hidden", "number", "decline", "clarify", "undetermined");
  const clarification = t.answer.clarification;
  if (clarification && !clarification.selected) {
    b.classList.add("clarify");
    b.replaceChildren(
      el("span", "big", "needs clarification"),
      el("span", "reason", t.answer.reason),
    );
    return;
  }
  const isUndetermined =
    t.answer.kind === "verdict" && t.answer.value === "undetermined";
  const isAnswer =
    t.answer.kind === "number" ||
    (t.answer.kind === "verdict" && !isUndetermined);
  b.classList.add(
    isUndetermined ? "undetermined" : isAnswer ? "number" : "decline",
  );
  const confirmed = clarification?.selected
    ? `   ·   confirmed ${clarification.selected}`
    : "";
  b.replaceChildren(
    el(
      "span",
      "big",
      isUndetermined ? "undetermined" : isAnswer ? String(t.answer.value) : "declined",
    ),
    el(
      "span",
      "reason",
      t.answer.reason +
        confirmed +
        (t.ask ? `   ·   ask ${t.ask.id} → ${JSON.stringify(t.ask.query)}` : ""),
    ),
  );
}

function renderClarification(t) {
  const box = $("clarification");
  box.replaceChildren();
  const request = t.answer.clarification;
  box.classList.toggle("hidden", !request);
  if (!request) return;

  const head = el("div", "clarification-head");
  head.append(
    el("span", "clarification-kicker", request.selected ? "Interpretation confirmed" : "More information needed"),
    el("span", "clarification-prompt", request.prompt),
  );
  box.append(head);

  const choices = el("div", "clarification-options");
  for (const option of request.options) {
    const selected = option.id === request.selected;
    const button = el(
      "button",
      `clarification-option${selected ? " selected" : ""}`,
    );
    button.type = "button";
    button.setAttribute("aria-pressed", String(selected));
    button.append(
      el("span", "clarification-option-label", option.label),
      el("span", "clarification-option-description", option.description),
      semanticNodeCard(option.query, "clarification-query"),
    );
    button.onclick = () => runTrace(option.id);
    choices.append(button);
  }
  box.append(choices);
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

/* ---------- semantic field ---------- */

function semanticFields(fields) {
  return Object.entries(fields || {})
    .filter(([k, v]) => !(k === "polarity" && v === true))
    .map(([k, v]) => `${k}=${v}`)
    .join("  ");
}

function semanticFactCard(f, compact = false) {
  const card = el("div", `sem-fact role-${f.role} repr-${f.representation}`);
  if (f.id) card.dataset.factId = f.id;
  const head = el("div", "sem-fact-head");
  head.append(
    el("span", "sem-id mono", f.id || "—"),
    el("span", "sem-type", f.type),
    el("span", `sem-role role-${f.role}`, f.role),
    el("span", `sem-repr repr-${f.representation}`, f.representation),
  );
  card.append(head);
  card.append(el("div", "sem-fields mono", semanticFields(f.fields)));
  if (!compact) {
    card.append(el("div", "sem-source", `${f.source} · sentence ${f.sentence}`));
  }
  return card;
}

function semanticNodeCard(node, cls = "") {
  const card = el("div", `sem-node ${cls}`);
  card.append(el("span", "sem-type", node?.kind || "unrecognized query"));
  card.append(el("span", "sem-fields mono", semanticFields(node?.fields)));
  return card;
}

function renderSemantic(t) {
  const box = $("semantic");
  box.replaceChildren();
  const sem = t.semantic;
  if (!sem) {
    box.append(el("div", "dim", "no semantic projection supplied"));
    return;
  }

  const query = el("section", "sem-section query-section");
  query.append(el("div", "pane-title", "Query projection"));
  if (sem.query) query.append(semanticNodeCard(sem.query, "query-node"));
  else query.append(el("div", "dim", "no question was projected"));
  box.append(query);

  if (sem.interpretations?.length) {
    const candidates = el("section", "sem-section interpretation-section");
    candidates.append(el("div", "pane-title", "Supported interpretations"));
    const grid = el("div", "interpretation-grid");
    for (const option of sem.interpretations) {
      const card = el(
        "div",
        `interpretation-card${option.selected ? " selected" : ""}`,
      );
      card.append(
        el("div", "interpretation-label", option.label),
        semanticNodeCard(option.query),
        el("div", "sem-note", option.description),
      );
      grid.append(card);
    }
    candidates.append(grid);
    box.append(candidates);
  }

  const groups = [
    {
      title: "Observed · exact",
      note: "lossless phrase-keyed propositions read directly from the text",
      select: (f) => f.role === "observed" && f.representation === "exact",
    },
    {
      title: "Observed · structured",
      note: "typed relations, quantifiers, quantities, and other fielded assertions",
      select: (f) => f.role === "observed" && f.representation === "structured",
    },
    {
      title: "Knowledge",
      note: "explicitly enabled world or domain knowledge; parser categories do not appear here",
      select: (f) => f.role === "knowledge",
    },
    {
      title: "Derived",
      note: "facts produced by named inference rules from observed or knowledge facts",
      select: (f) => f.role === "derived",
    },
  ];

  for (const group of groups) {
    const section = el("section", "sem-section");
    const facts = sem.facts.filter(group.select);
    const title = el("div", "sem-section-title");
    title.append(
      el("span", "", group.title),
      el("span", "sem-count mono", String(facts.length)),
    );
    section.append(title, el("div", "sem-note", group.note));
    const grid = el("div", "sem-grid");
    for (const fact of facts) grid.append(semanticFactCard(fact));
    if (!facts.length) {
      grid.append(el(
        "div",
        "sem-empty",
        group.title === "Knowledge"
          ? "∅ no ontology or world-knowledge facts are enabled for this run"
          : "∅ none",
      ));
    }
    section.append(grid);
    box.append(section);
  }
}

/* ---------- proof ---------- */

function linkProofEvidence(node, factId) {
  if (!factId) return node;
  node.classList.add("linked");
  const target = () => document.querySelector(
    `#semantic [data-fact-id="${factId}"]`,
  );
  node.addEventListener("mouseenter", () => target()?.classList.add("sem-hl"));
  node.addEventListener("mouseleave", () => target()?.classList.remove("sem-hl"));
  node.title = `${factId} in semantic field`;
  return node;
}

function renderProof(t) {
  const box = $("proof");
  box.replaceChildren();
  const proof = t.semantic?.proof;

  const query = el("section", "proof-query");
  query.append(el("div", "pane-title", "Normalized question"));
  if (t.semantic?.query) query.append(semanticNodeCard(t.semantic.query, "query-node"));
  else query.append(el("div", "dim", "no recognized question"));
  box.append(query);

  const clarification = t.answer.clarification;
  if (clarification && !clarification.selected) {
    box.append(el(
      "div",
      "proof-empty clarification-paused",
      "REASONING PAUSED · choose an interpretation before asking the proof system to commit.",
    ));
    return;
  }

  if (!proof) {
    box.append(el(
      "div",
      "proof-empty",
      `No structured proof is available for this consumer. ${t.answer.reason}`,
    ));
    return;
  }
  if (!proof.steps.length) {
    box.append(el(
      "div",
      "proof-empty undetermined",
      `UNDETERMINED · ${t.answer.reason}`,
    ));
    return;
  }

  const flow = el("div", "proof-flow");
  for (const [i, step] of proof.steps.entries()) {
    const card = el("section", "proof-step");
    const head = el("div", "proof-step-head");
    head.append(
      el("span", "proof-index mono", String(i + 1)),
      el("span", "proof-rule mono", step.rule),
    );
    card.append(head);

    const evidence = el("div", "proof-evidence");
    evidence.append(el("div", "proof-label", "Evidence"));
    const evidenceGrid = el("div", "proof-evidence-grid");
    for (const fact of step.evidence) {
      evidenceGrid.append(linkProofEvidence(semanticFactCard(fact, true), fact.id));
    }
    if (!step.evidence.length) evidenceGrid.append(el("span", "dim", "no stored evidence"));
    evidence.append(evidenceGrid);
    card.append(evidence);

    card.append(el("div", "proof-arrow", "↓"));
    const conclusion = el("div", "proof-conclusion");
    conclusion.append(el("div", "proof-label", "Conclusion"));
    conclusion.append(semanticNodeCard(step.conclusion, "conclusion-node"));
    card.append(conclusion);
    if (step.detail) card.append(el("div", "proof-detail", step.detail));
    flow.append(card);
  }
  box.append(flow);

  const outcome = el("div", `proof-outcome ${proof.status}`);
  outcome.append(
    el("span", "proof-outcome-label", proof.status.toUpperCase()),
    el("span", "mono", `${t.answer.kind}:${t.answer.value}`),
    el("span", "dim", t.answer.reason),
  );
  box.append(outcome);
}

/* ---------- the deictic field ----------

   A deictic expression ("she", "the rest", "that many", "in the jar") denotes nothing
   until you know the reference point it is measured from — the ORIGO. This view draws
   that: where the engine was standing, what it could see from there, how far away each
   candidate was, and what it decided.

   The engine's Decision trace cannot show any of this, because a DECLINE mutates
   nothing and is therefore invisible to it. The declines are where the information is.

   THE HONESTY RULE. Three of the four dimensions have no coordinates at all, and this
   view renders that absence AS an absence: time labels get no axis (there is no
   ordering to draw one through), place gets an empty strip, and candidates that are
   bare strings get no position. Drawing a plausible timeline out of "in january" /
   "in march" would put a fabricated ordering one copy-paste from the kernel — which is
   precisely the experiment that already failed the gate (docs/deixis.md §4). */

const DIM_CLASS = {
  person: "d-person", discourse: "d-discourse", time: "d-time", place: "d-place",
};

function crossLink(node, dataUid) {
  if (!dataUid) return node;
  node.classList.add("linked");
  const chip = () => document.querySelector(`.chip[data-uid="${dataUid}"]`);
  node.addEventListener("mouseenter", () => chip()?.classList.add("hl"));
  node.addEventListener("mouseleave", () => chip()?.classList.remove("hl"));
  return node;
}

function renderResolution(obs) {
  const card = el("div", `res ${obs.outcome}`);

  const head = el("div", "res-head");
  head.append(el("span", `dim-tag ${DIM_CLASS[obs.dimension] || ""}`, obs.dimension || "—"));
  head.append(el("span", "res-src", obs.source));
  head.append(el("span", "res-metric mono", obs.metric));
  if (obs.attempts > 1) {
    head.append(el("span", "res-attempts",
      `×${obs.attempts} — retried every round, never got any better`));
  }
  card.append(head);

  const origo = el("div", "res-origo");
  origo.append(el("span", "lbl", "origo"));
  origo.append(el("span", "mono",
    `sentence ${obs.origo.sentence}` + (obs.origo.span ? ` · token ${obs.origo.span[0]}` : "")));
  card.append(origo);

  // The distance track. Candidates sit at their measured distance from the origo — so
  // under the constant metric, where every candidate is equidistant, they all collapse
  // onto the origin. That collapse IS the thesis: with nothing to rank by, "more than
  // one" can only mean "ambiguous".
  const survivors = obs.candidates.filter((c) => !c.eliminated_by);
  const dists = survivors.map((c) => c.distance ?? 0);
  const maxD = Math.max(0, ...dists);
  const flat = survivors.length > 1 && maxD === 0;

  const track = el("div", "track");
  track.append(el("div", "track-origin", "▲"));
  const lane = el("div", "lane");
  for (const c of obs.candidates) {
    const pill = el("span", `cand ${DIM_CLASS[c.dimension] || ""}`);
    pill.append(el("span", "cand-key", c.key));
    if (c.eliminated_by) {
      pill.classList.add("out");
      pill.append(el("span", "cand-meta", c.eliminated_by));
    } else {
      pill.append(el("span", "cand-meta mono", `d=${c.distance ?? "—"}`));
      if (maxD > 0) pill.style.marginLeft = `${(c.distance / maxD) * 60}%`;
    }
    if (c.span === null) {
      // A bare measure/entity string. It has no position in the text, and we refuse to
      // invent one — the site that produced it threw the position away (or never had it).
      pill.classList.add("unanchored");
      pill.title = "no span — this site's candidates are bare strings, not units";
    }
    lane.append(crossLink(pill, c.data_uid));
  }
  if (!obs.candidates.length) lane.append(el("span", "dim", "no candidates in scope"));
  track.append(lane);
  card.append(track);

  if (flat) {
    card.append(el("div", "flat-note",
      `${survivors.length} candidates, all at d=0 — the field is flat. Strict dominance ` +
      `is unsatisfiable, so this can only decline. Switch on a real metric and they spread.`));
  }

  const out = el("div", "res-out");
  if (obs.outcome === "bound") {
    out.classList.add("ok");
    out.append(el("span", "verdict", "BOUND"));
    out.append(el("span", "mono", obs.winner));
    out.append(el("span", "dim", `(${obs.arbitration})`));
  } else {
    out.classList.add("no");
    out.append(el("span", "verdict", "DECLINE"));
    out.append(el("span", "mono", obs.reason || "—"));
    out.append(el("span", "dim", DECLINE_GLOSS[obs.reason] || ""));
  }
  card.append(out);
  return card;
}

const DECLINE_GLOSS = {
  "tie": "two or more candidates, none strictly nearer — ambiguity declines",
  "no-candidates": "nothing in scope to bind to",
  "filtered-out": "every candidate removed by a precision filter",
  "dimension-mismatch":
    "candidates existed, but none of the right KIND — cross-dimension pollution",
};

function renderField(t) {
  const box = $("field");
  box.replaceChildren();
  const d = t.deixis;
  if (!d) return;
  const f = d.field;

  // --- the narrative spine: the ONE real temporal coordinate the engine has ---
  const spineWrap = el("div", "axis");
  spineWrap.append(el("div", "axis-name", "NARRATIVE"));
  const spine = el("div", "spine");
  for (const n of f.narrative) {
    const node = el("div", `snode${n.is_question ? " ask" : ""}`);
    node.append(el("span", "snode-id mono", n.is_question ? "ASK" : `s${n.sentence}`));
    node.append(el("span", "snode-text", n.text));
    spine.append(node);
  }
  spineWrap.append(spine);
  box.append(spineWrap);

  // --- PERSON: the only axis with true positional coordinates ---
  const person = el("div", "axis");
  person.append(el("div", "axis-name d-person", "PERSON"));
  const prow = el("div", "axis-row");
  for (const c of f.person.candidates) {
    const pill = el("span", "cand d-person");
    pill.append(el("span", "cand-key", c.surface));
    pill.append(el("span", "cand-meta mono", `s${c.sentence}·t${c.span[0]}`));
    prow.append(crossLink(pill, c.data_uid));
  }
  if (!f.person.candidates.length) prow.append(el("span", "dim", "no name units"));
  person.append(prow);
  box.append(person);

  // --- DISCOURSE: bare strings. Sentence BANDS, never spans. ---
  const disc = el("div", "axis");
  disc.append(el("div", "axis-name d-discourse", "DISCOURSE"));
  const drow = el("div", "axis-row");
  for (const [label, items] of [["measure", f.discourse.measures], ["entity", f.discourse.entities]]) {
    for (const b of items) {
      const pill = el("span", "cand d-discourse unanchored");
      pill.append(el("span", "cand-key", b.key));
      pill.append(el("span", "cand-meta mono", b.sentences.map((s) => `s${s}`).join(",")));
      pill.title = `${label} — a bare string. Its only coordinate is the sentence its facts came from: a band, not a position.`;
      drow.append(pill);
    }
  }
  if (!drow.children.length) drow.append(el("span", "dim", "no measures or entities"));
  disc.append(drow);
  box.append(disc);

  // --- TIME: labels, but NO ORDERING. No axis is drawn, deliberately. ---
  const time = el("div", "axis degenerate");
  time.append(el("div", "axis-name d-time", "TIME"));
  const trow = el("div", "axis-row");
  for (const label of f.time.labels) {
    const pill = el("span", "cand d-time unanchored floating");
    pill.append(el("span", "cand-key", label));
    trow.append(pill);
  }
  if (!f.time.labels.length) trow.append(el("span", "dim", "no time labels in this document"));
  time.append(trow);
  time.append(el("div", "axis-note", "⚠ no ordering exists — " + f.time.note));
  box.append(time);

  // --- PLACE: does not exist. An empty strip, and it says so. ---
  const place = el("div", "axis degenerate empty");
  place.append(el("div", "axis-name d-place", "PLACE"));
  place.append(el("div", "axis-row", ""));
  place.append(el("div", "axis-note", "∅ " + f.place.note));
  box.append(place);

  // --- the resolutions ---
  const res = el("div", "resolutions");
  res.append(el("div", "pane-title", `Resolutions (${d.observations.length})`));
  if (!d.observations.length) {
    res.append(el("div", "dim",
      "no deictic resolution was attempted. Only two of the fifteen sites route through " +
      "deixis.resolve() so far — the rest still hand-write the acceptance test and are " +
      "invisible here (docs/deixis.md phase 6)."));
  }
  for (const obs of d.observations) res.append(renderResolution(obs));
  box.append(res);
}

function setView(which) {
  for (const view of ["reading", "generate", "semantic", "field", "proof"]) {
    $(view).classList.toggle("hidden", which !== view);
    $(`view-${view}`).classList.toggle("on", which === view);
  }
  document.body.classList.toggle("generate-mode", which === "generate");
}

/* ---------- generation and human review ---------- */

async function loadGenerationRules() {
  const payload = await api("GET", "/api/generation/rules");
  state.generationRules = payload.rules || [];
  const select = $("generation-rule");
  select.replaceChildren();
  const random = el("option", "", "Random supported rule");
  random.value = "";
  select.append(random);
  for (const rule of state.generationRules) {
    const suffix = rule.supported ? "" : ` — blocked: ${rule.blockers.join("; ")}`;
    const option = el("option", "", rule.id + suffix);
    option.value = rule.id;
    option.dataset.supported = String(rule.supported);
    select.append(option);
  }
  $("generation-coverage").textContent =
    `${payload.supported}/${payload.total} premise rules realizable in G1`;
  select.onchange = updateGenerationRuleState;
  updateGenerationRuleState();
}

function selectedGenerationRule() {
  const id = $("generation-rule").value;
  return state.generationRules.find((rule) => rule.id === id) || null;
}

function updateGenerationRuleState() {
  const rule = selectedGenerationRule();
  const blocker = $("generation-blocker");
  const blocked = rule && !rule.supported;
  blocker.classList.toggle("hidden", !blocked);
  blocker.textContent = blocked ? rule.blockers.join(" · ") : "";
  $("generation-next").disabled = Boolean(blocked);
}

function generationFactCard(fact) {
  const card = el("div", "fact");
  card.append(
    el("span", "type", fact.type),
    el("span", "src", fact.source),
    document.createTextNode(JSON.stringify(fact.fields)),
  );
  return card;
}

function renderGenerationCandidate(candidate) {
  state.candidate = candidate;
  state.reviewVerdict = null;
  $("generation-empty").classList.add("hidden");
  $("generation-candidate").classList.remove("hidden");
  $("generation-target").textContent = candidate.target_rule;
  $("generation-description").textContent = candidate.target_description || "";
  $("generation-sentence").textContent = candidate.sentence;
  const status = $("generation-status");
  status.textContent = candidate.target_status;
  status.className = `generation-status ${candidate.target_status}`;
  $("generation-meta").textContent =
    `seed ${candidate.seed} · ${candidate.attempts} attempt(s) · ${candidate.registry_fingerprint.slice(0, 16)}`;
  $("generation-seed").value = candidate.seed;

  const matches = $("generation-matches");
  matches.replaceChildren();
  for (const match of candidate.actual_matches) {
    const card = el("div", `generation-match${match.shadowed ? " shadowed" : ""}`);
    card.append(
      el("span", "mono", match.rule_id),
      el("span", "dim", match.shadowed ? "shadowed" : "survived"),
      el("code", "", JSON.stringify(match.bindings)),
    );
    matches.append(card);
  }
  if (!candidate.actual_matches.length) {
    matches.append(el("div", "dim", "no premise rule matched"));
  }

  const facts = $("generation-facts");
  facts.replaceChildren();
  for (const fact of candidate.facts) facts.append(generationFactCard(fact));
  if (!candidate.facts.length) facts.append(el("div", "dim", "no surviving facts"));

  const issues = $("generation-deficiencies");
  issues.replaceChildren();
  for (const collision of candidate.collisions) {
    issues.append(
      el("div", "generation-issue collision",
        `collision ${collision.a_source} ↔ ${collision.b_source}: ${JSON.stringify(collision.key)}`),
    );
  }
  for (const deficiency of candidate.deficiencies) {
    issues.append(el("div", "generation-issue", deficiency));
  }
  if (!candidate.collisions.length && !candidate.deficiencies.length) {
    issues.append(el("div", "dim", "none"));
  }

  document.querySelectorAll(".review-verdicts button").forEach((button) => {
    button.classList.remove("selected");
  });
  $("generation-note").value = "";
  $("generation-save-review").disabled = true;
  $("generation-review-result").textContent = "";
}

async function generateNext() {
  const selected = selectedGenerationRule();
  if (selected && !selected.supported) return;
  const seedInput = $("generation-seed");
  const prior = Number(seedInput.value);
  const seed = Number.isSafeInteger(prior) && seedInput.value !== ""
    ? prior + (state.candidate ? 1 : 0)
    : Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
  setStatus("generating and round-tripping…");
  $("generation-next").disabled = true;
  try {
    const candidate = await api("POST", "/api/generation/candidate", {
      rule_id: selected?.id || null,
      seed,
    });
    if (candidate.detail) {
      setStatus(candidate.detail, "err");
      return;
    }
    renderGenerationCandidate(candidate);
    setStatus(
      `${candidate.target_rule}: ${candidate.target_status} · ${candidate.actual_rule_ids.length} actual rule(s)`,
      "ok",
    );
  } catch (exc) {
    setStatus(`generation failed: ${exc}`, "err");
  } finally {
    updateGenerationRuleState();
  }
}

function selectReviewVerdict(verdict, button) {
  state.reviewVerdict = verdict;
  document.querySelectorAll(".review-verdicts button").forEach((node) => {
    node.classList.toggle("selected", node === button);
  });
  $("generation-save-review").disabled = false;
}

async function saveGenerationReview() {
  const candidate = state.candidate;
  if (!candidate || !state.reviewVerdict) return;
  $("generation-save-review").disabled = true;
  const payload = await api("POST", "/api/generation/review", {
    candidate_id: candidate.id,
    sentence: candidate.sentence,
    target_rule: candidate.target_rule,
    seed: candidate.seed,
    registry_fingerprint: candidate.registry_fingerprint,
    verdict: state.reviewVerdict,
    note: $("generation-note").value,
  });
  if (!payload.ok) {
    $("generation-review-result").textContent = payload.detail || "review rejected";
    $("generation-save-review").disabled = false;
    return;
  }
  $("generation-review-result").textContent =
    `recorded ${state.reviewVerdict} · ${payload.review.timestamp}`;
  setStatus("review recorded in project generation history", "ok");
}

function inspectGeneratedReading() {
  if (!state.candidate) return;
  $("trace-input").value = state.candidate.sentence;
  setView("reading");
  runTrace();
}

/* ---------- impact ---------- */

function impactBody() {
  return {
    target: $("impact-target").value || "suite",
    spend_test_look: $("spend-look-cb").checked,
  };
}

let impactRunning = false;

function setImpactBusy(busy, label) {
  impactRunning = busy;
  for (const id of ["impact-btn", "baseline-btn", "impact-target", "spend-look-cb"]) {
    $(id).disabled = busy;
  }
  $("impact-btn").textContent = busy && label === "impact" ? "Running…" : "Run impact";
  $("baseline-btn").textContent = busy && label === "baseline" ? "Snapshotting…" : "Set baseline";
  document.body.classList.toggle("impact-busy", busy);
}

async function runImpact() {
  if (impactRunning) return;
  const body = impactBody();
  setImpactBusy(true, "impact");
  setStatus(`running ${body.target}… (full slices take ~10s)`);
  const started = performance.now();
  let r;
  try {
    r = await api("POST", "/api/impact", body);
  } catch (exc) {
    setStatus(`impact failed: ${exc}`, "err");
    return;
  } finally {
    setImpactBusy(false);
  }
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
  if (impactRunning) return;
  const body = impactBody();
  setImpactBusy(true, "baseline");
  setStatus(`snapshotting ${body.target} baseline…`);
  let r;
  try {
    r = await api("POST", "/api/baseline", body);
  } catch (exc) {
    setStatus(`baseline failed: ${exc}`, "err");
    return;
  } finally {
    setImpactBusy(false);
  }
  if (r.error) { setStatus(r.error, "err"); return; }
  setStatus(`baseline [${r.target}]: ${r.aggregates.correct}/${r.aggregates.items} correct`, "ok");
}

/* ---------- wiring ---------- */

$("trace-btn").onclick = () => runTrace();
$("trace-input").addEventListener("keydown", (e) => { if (e.key === "Enter") runTrace(); });
$("save-btn").onclick = saveDoc;
$("editor").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); saveDoc(); }
});
$("impact-btn").onclick = runImpact;
$("baseline-btn").onclick = setBaseline;
$("view-reading").onclick = () => setView("reading");
$("view-generate").onclick = () => setView("generate");
$("view-semantic").onclick = () => setView("semantic");
$("view-field").onclick = () => setView("field");
$("view-proof").onclick = () => setView("proof");
$("generation-next").onclick = generateNext;
$("generation-reading").onclick = inspectGeneratedReading;
$("generation-save-review").onclick = saveGenerationReview;
document.querySelectorAll(".review-verdicts button").forEach((button) => {
  button.onclick = () => selectReviewVerdict(button.dataset.verdict, button);
});
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
