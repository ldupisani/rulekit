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
  generationExploration: { rules: [], fillers: [], summary: {} },
  candidate: null,
  lastGenerationSeed: null,
  reviewVerdict: null,
  reviewRecorded: false,
  hypotheses: [],
  minimalPair: null,
  reviews: [],
  reviewSort: { key: "timestamp", dir: "desc" },
  editingReview: null,   // id of the row being corrected
  editorSaveBusy: false,
};

const GENERATION_DEFECTS = [
  [
    "premise_too_broad",
    "Premise too broad",
    "This premise accepts a word or structure that should fall outside the rule.",
  ],
  [
    "premise_too_narrow",
    "Premise too narrow",
    "This premise rejects an ordinary valid use that the rule should accept.",
  ],
  [
    "wrong_category_membership",
    "Wrong category membership",
    "The selected filler should not belong to the declared category that admitted it.",
  ],
  [
    "wrong_lexical_sense",
    "Wrong lexical sense",
    "The word was interpreted with a sense that is not justified in this sentence.",
  ],
  [
    "wrong_morphology_agreement",
    "Wrong morphology or agreement",
    "Number, tense, possessive form, inflection, or agreement is incorrect.",
  ],
  [
    "inappropriate_optional_branch",
    "Inappropriate optional branch",
    "An optional part was included or omitted in a way the rule should not permit.",
  ],
  [
    "missing_cross_slot_constraint",
    "Missing cross-slot constraint",
    "Two or more slot bindings need a relationship such as distinctness or shared identity.",
  ],
  [
    "sentence_ungrammatical",
    "Sentence ungrammatical",
    "The generated surface is not generally accepted ordinary English.",
  ],
  [
    "semantically_implausible",
    "Grammatical but implausible",
    "The sentence is grammatical, but its combination of meanings is unreasonable or unusable.",
  ],
  [
    "intended_rule_did_not_fire",
    "Intended rule did not fire",
    "The sentence should satisfy the selected rule, but the ordinary matcher did not retain it.",
  ],
  [
    "another_rule_interfered",
    "Another rule interfered",
    "A co-firing or more-specific rule changed, shadowed, or conflicted with the intended result.",
  ],
  [
    "generator_realization_defect",
    "Generator realization defect",
    "The premises look sound, but the generator assembled their surface forms incorrectly.",
  ],
  [
    "unexpected_fact",
    "Fact should not be emitted",
    "The attached surviving fact is not justified by this sentence.",
  ],
  [
    "incorrect_fact_field",
    "Fact type or field is wrong",
    "The fact is warranted, but its type, field mapping, or recorded value is incorrect.",
  ],
  [
    "missing_fact_context",
    "Fact omits needed context",
    "The fact drops an identity, qualifier, role, time, or other discriminator needed later.",
  ],
  [
    "other",
    "Other",
    "Use the review note to describe a defect that does not fit another choice.",
  ],
];
const HYPOTHESIS_STATUSES = ["open", "confirmed", "rejected", "inconclusive"];

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
  await loadGenerationExploration();
}

async function openDoc(path, node) {
  document.querySelectorAll("#file-tree .file.active").forEach((n) => n.classList.remove("active"));
  if (node) node.classList.add("active");
  const doc = await api("GET", `/api/doc?path=${encodeURIComponent(path)}`);
  state.currentDoc = path;
  $("editor").value = doc.content;
  $("editor-title").textContent = path.split("/").slice(-2).join("/");
  $("save-result").textContent = "";
  window.RulekitEditor?.refresh();  // repaint highlighting + syntax lint
  updateSaveRetestState();
}

function updateSaveRetestState() {
  $("save-btn").disabled = state.editorSaveBusy;
  $("save-retest-btn").disabled =
    state.editorSaveBusy || !state.currentDoc || !state.candidate
    || !state.candidate.target_rule;
}

async function saveCurrentDoc({ rerunTrace = true } = {}) {
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
    return res;
  }
  out.textContent = "✓ compiled";
  out.style.color = "var(--green)";
  $("fingerprint").textContent = res.fingerprint;
  for (const f of res.lint) {
    lintBox.append(el("div", `lint-item ${f.level}`, `[${f.code}] ${f.message}`));
  }
  await loadGenerationRules();
  await loadGenerationExploration();
  setStatus(`saved · ${res.lint.length} lint finding(s)`, "ok");
  if (rerunTrace && $("trace-input").value.trim()) runTrace();  // live re-read
  return res;
}

async function saveDoc() {
  if (state.editorSaveBusy) return;
  state.editorSaveBusy = true;
  updateSaveRetestState();
  try {
    await saveCurrentDoc();
  } finally {
    state.editorSaveBusy = false;
    updateSaveRetestState();
  }
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
  const reason = el(
    "span",
    "reason",
    t.answer.reason +
      confirmed +
      (t.ask ? `   ·   ask ${t.ask.id} → ${JSON.stringify(t.ask.query)}` : ""),
  );
  if (t.ask?.source_ref) {
    reason.append(
      " ",
      generationSourceControl(t.ask.source_ref, "Open ask YAML"),
    );
  }
  b.replaceChildren(
    el(
      "span",
      "big",
      isUndetermined ? "undetermined" : isAnswer ? String(t.answer.value) : "declined",
    ),
    reason,
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
    if (!s.is_question) {
      const review = el("div", "reading-review");
      const targets = s.review_targets || [];
      if (targets.length) {
        const select = el("select", "reading-review-target");
        select.setAttribute(
          "aria-label",
          `Premise rule to review for sentence ${s.index}`,
        );
        for (const target of targets) {
          const option = el(
            "option",
            "",
            `${target.rule_id} · ${target.status}`,
          );
          option.value = target.rule_id;
          option.title = target.description || target.rule_id;
          select.append(option);
        }
        const button = el("button", "reading-review-button", "Review premise");
        button.type = "button";
        button.onclick = () => promoteReadingSentence(
          s,
          select.value,
          button,
        );
        const source = el("span", "reading-review-source");
        const updateSource = () => {
          const target = targets.find(
            (candidate) => candidate.rule_id === select.value,
          );
          source.replaceChildren();
          if (target?.source_ref) {
            source.append(
              generationSourceControl(target.source_ref, "Open rule YAML"),
            );
          }
        };
        select.onchange = updateSource;
        updateSource();
        review.append(source);
        review.append(
          el("span", "dim", "Matched premise"),
          select,
          button,
        );
      } else {
        review.append(
          el(
            "span",
            "dim",
            "No matched premise rule is available for review.",
          ),
        );
      }
      const sentenceButton = el(
        "button",
        "reading-review-button",
        "Review sentence meaning",
      );
      sentenceButton.type = "button";
      sentenceButton.title =
        "Record an intended interpretation or suggest a missing premise rule without claiming an existing rule matched.";
      sentenceButton.onclick = () => promoteReadingSentence(
        s,
        null,
        sentenceButton,
      );
      review.append(sentenceButton);
      card.append(review);
    }
    box.append(card);
  }
}

async function promoteReadingSentence(sentence, ruleId, button) {
  button.disabled = true;
  const subject = ruleId || "sentence meaning";
  setStatus(`opening ${subject} for human review…`);
  try {
    const candidate = await api("POST", "/api/generation/from-reading", {
      rule_id: ruleId,
      sentence: sentence.text,
    });
    if (candidate.detail) {
      setStatus(candidate.detail, "err");
      return;
    }
    if (
      state.generationRules.some((rule) => rule.id === candidate.target_rule)
    ) {
      $("generation-rule").value = candidate.target_rule;
      updateGenerationRuleState();
    }
    renderGenerationCandidate(candidate);
    setView("generate");
    setStatus(
      `${candidate.target_rule || "sentence meaning"}: Reading sentence ready for review · ${candidate.target_status}`,
      "ok",
    );
  } catch (exc) {
    setStatus(`could not open Reading sentence for review: ${exc}`, "err");
  } finally {
    button.disabled = false;
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
    row.append(
      el("span", "k", k),
      v instanceof Node ? v : el("span", cls || "", v),
    );
    detail.append(row);
  };
  kv("kind", d.kind);
  kv("target", `${d.target_surface}  (u${d.target}, sentence ${d.sentence})`);
  kv("reason", d.reason);
  if (d.rule_id) {
    const rule = el("span", "reading-identified-source");
    rule.append(el("span", "mono", d.rule_id));
    if (d.source_ref) {
      rule.append(generationSourceControl(d.source_ref, "Open rule YAML"));
    }
    kv("rule", rule);
  }
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
    const header = el("div", "reading-fact-head");
    const source = el("span", "src");
    source.append(el("span", "", `${f.source} · s${f.sentence}`));
    if (f.source_ref) {
      source.append(generationSourceControl(f.source_ref, "Open rule YAML"));
    }
    header.append(el("span", "type", f.type), source);
    card.append(
      header,
      el("span", "reading-fact-fields", Object.entries(f.fields)
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
    const source = el("div", "sem-source");
    source.append(
      el("span", "", `${f.source} · sentence ${f.sentence}`),
    );
    if (f.source_ref) {
      source.append(generationSourceControl(f.source_ref, "Open rule YAML"));
    }
    card.append(source);
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
    if (step.source_ref) {
      head.append(generationSourceControl(step.source_ref, "Open rule YAML"));
    }
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
  for (const view of ["reading", "generate", "reviews", "semantic", "field", "proof"]) {
    $(view).classList.toggle("hidden", which !== view);
    $(`view-${view}`).classList.toggle("on", which === view);
  }
  document.body.classList.toggle("generate-mode", which === "generate");
  document.body.classList.toggle("reviews-mode", which === "reviews");
  if (which === "reviews") loadReviews();
  if (which === "generate") loadGenerationExploration();
}

/* ---------- review history ----------

   Edits and deletes POST corrections to the append-only ledger, so every
   mutation here is a round trip: we never patch the local array and hope it
   matches disk. `supersedes` on a record means it is itself a correction. */

const VERDICTS = ["valid", "invalid", "unclear"];
// worst-first, so sorting by verdict groups what still needs attention
const VERDICT_RANK = { invalid: 0, unclear: 1, valid: 2 };

async function loadReviews() {
  const payload = await api("GET", "/api/generation/history?limit=500");
  state.reviews = payload.reviews || [];
  renderReviews();
}

function sortedReviews() {
  const { key, dir } = state.reviewSort;
  const sign = dir === "asc" ? 1 : -1;
  const of = (r) =>
    key === "verdict" ? VERDICT_RANK[r.verdict] ?? 9
    : key === "target_rule" ? r.target_rule || ""
    : r.timestamp;
  return [...state.reviews].sort((a, b) => {
    const x = of(a), y = of(b);
    return x < y ? -sign : x > y ? sign : 0;
  });
}

function sortHeader(label, key) {
  const { key: active, dir } = state.reviewSort;
  const node = el("th", `rv-sort${active === key ? " on" : ""}`,
                  `${label}${active === key ? (dir === "asc" ? " ▲" : " ▼") : ""}`);
  node.onclick = () => {
    state.reviewSort = active === key
      ? { key, dir: dir === "asc" ? "desc" : "asc" }
      : { key, dir: key === "timestamp" ? "desc" : "asc" };
    renderReviews();
  };
  return node;
}

function renderReviews() {
  const box = $("reviews");
  box.replaceChildren();

  const head = el("div", "rv-head");
  head.append(el("div", "pane-title", "Human review history"));
  head.append(el("span", "dim",
    `${state.reviews.length} review${state.reviews.length === 1 ? "" : "s"} · ` +
    `edits and deletes append corrections; nothing is overwritten`));
  box.append(head);

  if (!state.reviews.length) {
    box.append(el("div", "rv-empty",
      "No reviews recorded for this project yet. Record one from Generate or Reading."));
    return;
  }

  const table = el("table", "rv-table");
  const thead = el("thead");
  const hrow = el("tr");
  hrow.append(sortHeader("Verdict", "verdict"));
  hrow.append(sortHeader("Recorded", "timestamp"));
  hrow.append(sortHeader("Target rule", "target_rule"));
  hrow.append(el("th", "", "Sentence"));
  hrow.append(el("th", "", "Note"));
  hrow.append(el("th", "", ""));
  thead.append(hrow);
  table.append(thead);

  const body = el("tbody");
  for (const r of sortedReviews()) {
    body.append(
      state.editingReview === r.id ? reviewEditRow(r) : reviewRow(r)
    );
  }
  table.append(body);
  box.append(table);
}

function reviewRow(r) {
  const row = el("tr", "rv-row");

  const verdict = el("td");
  verdict.append(el("span", `rv-verdict ${r.verdict}`, r.verdict));
  if (r.supersedes) {
    const tag = el("span", "rv-edited", "edited");
    tag.title = "this verdict supersedes an earlier one, still on disk";
    verdict.append(tag);
  }
  row.append(verdict);

  row.append(el("td", "rv-when mono", (r.timestamp || "").replace("T", " ").slice(0, 19)));
  const rule = el("td", "rv-rule mono");
  rule.append(
    document.createTextNode(r.target_rule || "No target rule"),
    el("span", "rv-origin", r.origin || "generated"),
    el(
      "span",
      "rv-origin",
      (r.generation_mode || "strict").replaceAll("_", " "),
    ),
  );
  row.append(rule);
  row.append(el("td", "rv-sentence", r.sentence));
  const note = el("td", "rv-note");
  note.append(document.createTextNode(r.note || "—"));
  if (r.interpretation) {
    note.append(el("div", "rv-structured", `interpretation: ${r.interpretation}`));
  }
  if (r.suggested_rule) {
    note.append(el("div", "rv-structured", `missing rule: ${r.suggested_rule}`));
  }
  if (r.defects?.length) {
    note.append(el("div", "rv-structured",
      `defects: ${r.defects.map((defect) =>
        `${defect.kind.replaceAll("_", " ")} → ` +
        (
          defect.attachment.kind === "sentence"
            ? "whole sentence"
            : `${defect.attachment.kind} ${defect.attachment.index + 1}`
        ) +
        (
          defect.fact
            ? ` (${defect.fact.type} ${JSON.stringify(defect.fact.fields)})`
            : ""
        )).join(" · ")}`));
  }
  if (r.hypotheses?.length) {
    note.append(el("div", "rv-structured",
      `hypotheses: ${r.hypotheses.map((hypothesis) =>
        `${hypothesis.kind.replaceAll("_", " ")} [${hypothesis.status}]`).join(" · ")}`));
  }
  row.append(note);

  const actions = el("td", "rv-actions");
  const open = el("button", "", "Open in reader");
  open.onclick = () => openReviewInReader(r);
  const edit = el("button", "", "Edit");
  edit.onclick = () => { state.editingReview = r.id; renderReviews(); };
  const del = el("button", "rv-danger", "Delete");
  // two-step in place: a modal confirm() would block the page
  del.onclick = () => {
    if (del.dataset.armed) return deleteReview(r);
    del.dataset.armed = "1";
    del.textContent = "Confirm?";
    setTimeout(() => {
      if (!del.isConnected) return;
      delete del.dataset.armed;
      del.textContent = "Delete";
    }, 4000);
  };
  actions.append(open, edit, del);
  row.append(actions);
  return row;
}

function reviewEditRow(r) {
  const row = el("tr", "rv-row editing");
  const cell = el("td");
  cell.colSpan = 6;

  const form = el("div", "rv-edit");
  form.append(el("div", "rv-edit-sentence", r.sentence));

  let verdict = r.verdict;
  const picker = el("div", "review-verdicts");
  for (const v of VERDICTS) {
    const b = el("button", v === verdict ? "selected" : "", v);
    b.dataset.verdict = v;
    b.onclick = () => {
      verdict = v;
      picker.querySelectorAll("button").forEach((n) =>
        n.classList.toggle("selected", n.dataset.verdict === v));
    };
    picker.append(b);
  }
  form.append(picker);

  let interpretation = null;
  let suggestedRule = null;
  if ((r.review_kind || "premise") === "sentence") {
    interpretation = el("textarea", "rv-edit-note");
    interpretation.maxLength = 4000;
    interpretation.value = r.interpretation || "";
    interpretation.placeholder = "In ordinary language, what does this sentence mean?";
    form.append(el("div", "pane-title", "Intended interpretation"), interpretation);

    suggestedRule = el("textarea", "rv-edit-note");
    suggestedRule.maxLength = 4000;
    suggestedRule.value = r.suggested_rule || "";
    suggestedRule.placeholder = "What sentence shape or premise rule should recognize it?";
    form.append(el("div", "pane-title", "Missing rule suggestion"), suggestedRule);
  }

  const note = el("textarea", "rv-edit-note");
  note.maxLength = 4000;
  note.value = r.note || "";
  note.placeholder = "why this verdict…";
  form.append(note);

  const hypotheses = (r.hypotheses || []).map((hypothesis) => ({
    ...hypothesis,
    observations: [...hypothesis.observations],
    sources: [...hypothesis.sources],
    premise: { ...hypothesis.premise },
  }));
  if (hypotheses.length) {
    const hypothesisBox = el("div", "rv-edit-hypotheses");
    for (const hypothesis of hypotheses) {
      const item = el("label", "rv-edit-hypothesis");
      item.append(el("span", "", hypothesis.claim));
      const status = el("select");
      for (const value of HYPOTHESIS_STATUSES) {
        const option = el("option", "", value);
        option.value = value;
        option.selected = value === hypothesis.status;
        status.append(option);
      }
      status.onchange = () => { hypothesis.status = status.value; };
      item.append(status);
      hypothesisBox.append(item);
    }
    form.append(hypothesisBox);
  }

  const actions = el("div", "rv-actions");
  const save = el("button", "primary", "Save correction");
  save.onclick = async () => {
    save.disabled = true;
    const res = await api("PATCH", `/api/generation/review/${encodeURIComponent(r.id)}`,
                          {
                            verdict,
                            note: note.value,
                            hypotheses,
                            ...(interpretation
                              ? { interpretation: interpretation.value }
                              : {}),
                            ...(suggestedRule
                              ? { suggested_rule: suggestedRule.value }
                              : {}),
                          });
    if (!res.ok) {
      setStatus(res.detail || "correction rejected", "err");
      save.disabled = false;
      return;
    }
    state.editingReview = null;
    await loadReviews();
    setStatus(`review corrected to ${verdict} — the previous verdict is still on disk`, "ok");
  };
  const cancel = el("button", "", "Cancel");
  cancel.onclick = () => { state.editingReview = null; renderReviews(); };
  actions.append(save, cancel);
  form.append(actions);

  cell.append(form);
  row.append(cell);
  return row;
}

async function deleteReview(r) {
  const res = await api("DELETE", `/api/generation/review/${encodeURIComponent(r.id)}`);
  if (!res.ok) {
    setStatus(res.detail || "delete rejected", "err");
    return;
  }
  await loadReviews();
  setStatus("review deleted — a tombstone was appended, the record is recoverable", "ok");
}

function openReviewInReader(r) {
  $("trace-input").value = r.sentence;
  setView("reading");
  $("view-reading").classList.add("on");
  runTrace();
}

/* ---------- generation and human review ---------- */

async function loadGenerationRules() {
  const payload = await api("GET", "/api/generation/rules");
  state.generationRules = payload.rules || [];
  const select = $("generation-rule");
  const priorSelection = select.value;
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
  if (state.generationRules.some((rule) => rule.id === priorSelection)) {
    select.value = priorSelection;
  }
  $("generation-coverage").textContent =
    `${payload.supported}/${payload.total} premise rules currently realizable`;
  select.onchange = updateGenerationRuleState;
  updateGenerationRuleState();
}

function explorationLabel(item) {
  if (item.status === "never_generated") return `untouched — ${item.identity}`;
  if (item.status === "attempted_failed") {
    return `attempted ${item.failed_count}×, not realized — ${item.identity}`;
  }
  if (item.status === "generated_unreviewed") {
    return (
      `generated ${item.generated_count}×` +
      `${item.failed_count ? ` · failed ${item.failed_count}×` : ""}` +
      ` — ${item.identity}`
    );
  }
  return (
    `reviewed ${item.reviewed_count}×` +
    `${item.failed_count ? ` · failed ${item.failed_count}×` : ""}` +
    ` — ${item.identity}`
  );
}

async function loadGenerationExploration() {
  const payload = await api("GET", "/api/generation/exploration");
  if (payload.detail) {
    setStatus(payload.detail, "err");
    return;
  }
  state.generationExploration = payload;
  const select = $("generation-filler");
  const priorSelection = select.value;
  select.replaceChildren();
  const automatic = el(
    "option",
    "",
    "Least-explored compatible lexicon entry",
  );
  automatic.value = "";
  select.append(automatic);
  const rank = {
    never_generated: 0,
    attempted_failed: 1,
    generated_unreviewed: 2,
    reviewed: 3,
  };
  const fillers = [...(payload.fillers || [])].sort((a, b) =>
    (a.attempt_count || 0) - (b.attempt_count || 0)
    || (rank[a.status] ?? 9) - (rank[b.status] ?? 9)
    || a.identity.localeCompare(b.identity)
  );
  for (const filler of fillers) {
    const option = el("option", "", explorationLabel(filler));
    option.value = filler.identity;
    select.append(option);
  }
  if (fillers.some((filler) => filler.identity === priorSelection)) {
    select.value = priorSelection;
  }
  select.onchange = updateGenerationRuleState;

  const ruleCounts = payload.summary?.rules || {};
  const fillerCounts = payload.summary?.fillers || {};
  const supported = state.generationRules.filter((rule) => rule.supported).length;
  $("generation-coverage").textContent =
    `${supported}/${state.generationRules.length} premise rules realizable · ` +
    `${ruleCounts.never_generated || 0} untouched rules · ` +
    `${ruleCounts.attempted_failed || 0} attempted, not realized · ` +
    `${ruleCounts.generated_unreviewed || 0} generated, unreviewed · ` +
    `${ruleCounts.reviewed || 0} reviewed · ` +
    `${fillerCounts.never_generated || 0}/${(payload.fillers || []).length} ` +
    `reachable lexicon entries untouched · ` +
    `${fillerCounts.attempted_failed || 0} attempted, not realized`;
  updateGenerationRuleState();
}

function selectedGenerationRule() {
  const id = $("generation-rule").value;
  return state.generationRules.find((rule) => rule.id === id) || null;
}

function selectedGenerationMode() {
  return $("generation-mode").value || "strict";
}

function selectedGenerationFiller() {
  const identity = $("generation-filler").value;
  return (state.generationExploration.fillers || [])
    .find((filler) => filler.identity === identity) || null;
}

function renderGenerationExplorationSelection(rule, filler) {
  const box = $("generation-exploration-selection");
  box.replaceChildren();
  const ruleStatus = (state.generationExploration.rules || [])
    .find((item) => item.id === rule?.id);
  const mode = selectedGenerationMode();
  box.append(
    el(
      "span",
      "mono",
      mode === "lexical_boundary"
        ? "lexical boundary: one category-gated slot may draw from its broader declared root sense"
        : ruleStatus
        ? `rule ${ruleStatus.status.replaceAll("_", " ")} · generated ${ruleStatus.generated_count} · failed ${ruleStatus.failed_count || 0} · reviewed ${ruleStatus.reviewed_count}`
        : "rule frontier: least attempted, with seeded tie-breaking",
    ),
  );
  if (mode === "lexical_boundary") {
    box.append(
      el(
        "span",
        "mono",
        "boundary probes do not count as strict rule or lexicon coverage",
      ),
    );
  } else if (filler) {
    box.append(
      el(
        "span",
        "mono",
        `lexicon ${filler.status.replaceAll("_", " ")} · generated ${filler.generated_count} · failed ${filler.failed_count || 0} · reviewed ${filler.reviewed_count}`,
      ),
      generationSourceControl(filler.source),
    );
  } else {
    box.append(
      el("span", "mono", "lexicon frontier: least generated compatible entry"),
    );
  }
}

function updateGenerationRuleState() {
  const rule = selectedGenerationRule();
  const filler = selectedGenerationFiller();
  const strict = selectedGenerationMode() === "strict";
  const blocker = $("generation-blocker");
  const blocked = rule && !rule.supported;
  const incompatible = Boolean(
    strict && rule && filler && !filler.compatible_rules.includes(rule.id),
  );
  blocker.classList.toggle("hidden", !blocked && !incompatible);
  blocker.textContent = blocked
    ? rule.blockers.join(" · ")
    : incompatible
      ? `${filler.identity} cannot fill a supported slot in ${rule.id}`
      : "";
  $("generation-next").disabled = Boolean(blocked || incompatible);
  $("generation-filler").disabled = !strict;
  renderGenerationExplorationSelection(rule, filler);
}

function generationFactCard(fact, index) {
  const card = el("div", "fact generation-fact");
  const header = el("div", "generation-fact-header");
  header.append(
    el("span", "fact-index", `fact ${index + 1}`),
    el("span", "type", fact.type),
    el("span", "generation-fact-origin", fact.source),
  );
  card.append(
    header,
    el("code", "generation-fact-fields", JSON.stringify(fact.fields)),
  );
  if (fact.derivation) {
    const detail = el("details", "generation-fact-derivation");
    detail.append(el("summary", "", "How this fact was derived"));
    const templates = fact.derivation.templates || {};
    for (const [field, expression] of Object.entries(templates)) {
      const resolved = Object.prototype.hasOwnProperty.call(fact.fields, field)
        ? fact.fields[field]
        : null;
      detail.append(
        el(
          "code",
          "generation-fact-derivation-row",
          `${field}: ${JSON.stringify(expression)} → ${JSON.stringify(resolved)}`,
        ),
      );
    }
    const bindings = fact.derivation.bindings || {};
    if (Object.keys(bindings).length) {
      detail.append(
        el(
          "code",
          "generation-fact-derivation-bindings",
          `bindings: ${JSON.stringify(bindings)}`,
        ),
      );
    }
    card.append(detail);
  }
  if (fact.source_ref) {
    const source = el("div", "generation-fact-source");
    source.append(generationSourceControl(fact.source_ref));
    card.append(source);
  }
  return card;
}

function editableSourceNode(source) {
  return Array.from(document.querySelectorAll("#file-tree .file"))
    .find((node) => node.dataset.path === source.path);
}

async function openGenerationSource(source) {
  const node = editableSourceNode(source);
  if (!node) return;
  await openDoc(source.path, node);
  window.RulekitEditor?.gotoLine(source.line);
}

function generationSourceControl(source, compactLabel = null) {
  const fullLabel = `${source.label} · ${source.path.split("/").pop()}:${source.line}`;
  const label = compactLabel || fullLabel;
  const node = editableSourceNode(source);
  if (!node) {
    const unavailable = el("span", "generation-source unavailable", label);
    unavailable.title = `${fullLabel}. Source is outside the editable pack-document allowlist`;
    return unavailable;
  }
  const button = el("button", "generation-source", label);
  button.type = "button";
  if (compactLabel) button.title = fullLabel;
  button.onclick = () => openGenerationSource(source);
  return button;
}

function initializeGenerationDefects() {
  const box = $("generation-defects");
  for (const [kind, label, help] of GENERATION_DEFECTS) {
    const control = el("label", "generation-defect");
    control.title = help;
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = kind;
    input.title = help;
    input.setAttribute("aria-label", `${label}. ${help}`);
    input.dataset.requiresFact = String(
      ["unexpected_fact", "incorrect_fact_field", "missing_fact_context"].includes(kind),
    );
    input.onchange = () => {
      clearGenerationHypotheses();
      updateGenerationReviewState();
    };
    const hint = el("span", "generation-defect-help", "?");
    hint.title = help;
    hint.setAttribute("aria-label", help);
    control.append(input, document.createTextNode(label), hint);
    box.append(control);
  }
  $("generation-attachment").onchange = () => {
    clearGenerationHypotheses();
    updateGenerationReviewState();
  };
}

function selectedGenerationAttachment() {
  const raw = $("generation-attachment").value || "sentence";
  if (raw === "sentence") return { kind: "sentence", index: null };
  const [kind, index] = raw.split(":");
  return { kind, index: Number(index) };
}

function selectedGenerationDefects() {
  const attachment = selectedGenerationAttachment();
  const displayedFact = attachment.kind === "fact"
    ? state.candidate?.facts[attachment.index]
    : null;
  const fact = displayedFact
    ? {
        type: displayedFact.type,
        fields: displayedFact.fields,
        source: displayedFact.source,
        sentence: displayedFact.sentence,
        ...(displayedFact.source_ref
          ? { source_ref: displayedFact.source_ref }
          : {}),
        ...(displayedFact.derivation
          ? { derivation: displayedFact.derivation }
          : {}),
      }
    : null;
  return Array.from(
    document.querySelectorAll("#generation-defects input:checked"),
  ).filter((input) =>
    !input.disabled
    && (input.dataset.requiresFact !== "true" || attachment.kind === "fact")
  ).map((input) => ({
    kind: input.value,
    attachment,
    ...(fact ? { fact } : {}),
  }));
}

function populateGenerationAttachments(candidate) {
  const select = $("generation-attachment");
  select.replaceChildren();
  const sentence = el("option", "", "Whole sentence");
  sentence.value = "sentence";
  select.append(sentence);
  for (const premise of candidate.premises) {
    const option = el(
      "option",
      "",
      `${premise.kind} ${premise.index + 1}: ${premise.expression}`,
    );
    option.value = `${premise.kind}:${premise.index}`;
    select.append(option);
  }
  candidate.facts.forEach((fact, index) => {
    const option = el(
      "option",
      "",
      `fact ${index + 1}: ${fact.type} ${JSON.stringify(fact.fields)}`,
    );
    option.value = `fact:${index}`;
    select.append(option);
  });
}

function clearGenerationHypotheses(detail = "") {
  state.hypotheses = [];
  $("generation-hypotheses").classList.toggle("hidden", !detail);
  $("generation-hypothesis-summary").textContent = detail;
  $("generation-hypothesis-list").replaceChildren();
}

function updateGenerationReviewState() {
  const hasVerdict = Boolean(state.reviewVerdict);
  const hasDefects = selectedGenerationDefects().length > 0;
  const locked = state.reviewRecorded;
  const unavailable = !state.candidate || locked;
  document.querySelectorAll(
    ".generation-review .review-verdicts button",
  ).forEach((button) => {
    button.disabled = unavailable;
  });
  const attachmentKind = selectedGenerationAttachment().kind;
  document.querySelectorAll("#generation-defects input").forEach((input) => {
    input.disabled = unavailable
      || (input.dataset.requiresFact === "true" && attachmentKind !== "fact");
  });
  $("generation-attachment").disabled = unavailable;
  $("generation-note").disabled = unavailable;
  $("generation-interpretation").disabled = unavailable;
  $("generation-rule-suggestion").disabled = unavailable;
  $("generation-form-hypotheses").disabled =
    unavailable || !state.candidate?.target_rule || !hasVerdict || !hasDefects;
  $("generation-save-review").disabled = unavailable || !hasVerdict;
}

function renderGenerationPremises(candidate) {
  const summary = $("generation-premise-summary");
  const sentenceReview = !candidate.target_rule;
  const boundary = candidate.generation_mode === "lexical_boundary";
  $("generation-premise-title").textContent = sentenceReview
    ? "Reading evidence"
    : boundary
      ? "Target premise boundary"
      : candidate.target_status === "matched"
        ? "Why the target premise matched"
        : "Target premise result";
  const specificity = candidate.target_specificity
    ? candidate.target_specificity.join("/")
    : "unavailable";
  summary.textContent = sentenceReview
    ? "no target rule selected · no rule coverage claimed"
    : boundary
      ? `${candidate.lexical_relaxations?.length || 0} lexical gate(s) relaxed · target ${candidate.target_status}`
      : `specificity ${specificity} · ${candidate.consumed_units.length} consumed unit(s)`;

  const list = $("generation-premise-list");
  list.replaceChildren();
  if (sentenceReview) {
    list.append(
      el(
        "div",
        "generation-premise unverified",
        "This review preserves the sentence and its ordinary Reading evidence without asserting that any premise rule consumed it.",
      ),
    );
    return;
  }
  if (candidate.target_source) {
    const target = el("div", "generation-target-source");
    target.append(el("span", "dim", "Target declaration"), generationSourceControl(candidate.target_source));
    list.append(target);
  }
  const targetAvailability = state.generationRules.find(
    (rule) => rule.id === candidate.target_rule,
  );
  for (const premise of candidate.premises) {
    const card = el("article", `generation-premise ${premise.status}`);
    const heading = el("div", "generation-premise-row");
    heading.append(
      el("span", `generation-premise-status ${premise.status}`, premise.status),
      el("code", "", premise.expression),
    );
    if (premise.binding) {
      heading.append(el("span", "generation-binding mono", `→ ${premise.binding}`));
    }
    card.append(heading, el("div", "generation-premise-reason", premise.reason));
    if (premise.category_path.length) {
      card.append(
        el("div", "generation-category-path mono", premise.category_path.join(" → ")),
      );
    }
    if (premise.consumed.length) {
      card.append(
        el("div", "dim mono", `consumed unit ${premise.consumed.join(", ")}`),
      );
    }
    if (premise.sources.length) {
      const sources = el("div", "generation-sources");
      for (const source of premise.sources) {
        sources.append(generationSourceControl(source));
      }
      card.append(sources);
    }
    if (
      targetAvailability?.supported
      && candidate.generation_mode !== "lexical_boundary"
      && premise.slot
      && candidate.requested_bindings[premise.slot]
    ) {
      const reroll = el(
        "button",
        "generation-reroll-slot",
        `Reroll only ${premise.slot}`,
      );
      reroll.type = "button";
      reroll.onclick = () => generateMinimalPair(premise.slot, reroll);
      card.append(reroll);
    }
    list.append(card);
  }
}

function minimalPairSide(label, candidate, rerollSlot) {
  const side = el("article", "generation-pair-side");
  const heading = el("div", "generation-pair-heading");
  heading.append(
    el("span", "pane-title", label),
    el("span", `generation-status ${candidate.target_status}`, candidate.target_status),
  );
  side.append(
    heading,
    el("div", "generation-pair-sentence", candidate.sentence),
    el(
      "div",
      "dim mono",
      `${rerollSlot} = ${candidate.requested_bindings[rerollSlot] ?? "unbound"}`,
    ),
  );
  const table = el("div", "generation-pair-premises");
  for (const premise of candidate.premises) {
    const row = el("div", `generation-pair-premise ${premise.status}`);
    row.append(
      el("span", `generation-premise-status ${premise.status}`, premise.status),
      el("code", "", premise.expression),
      el("span", "mono", premise.binding || "—"),
    );
    table.append(row);
  }
  side.append(table);
  return side;
}

function renderMinimalPair(before, response) {
  const after = response.candidate;
  state.minimalPair = { before, after, rerollSlot: response.reroll_slot };
  $("generation-minimal-pair-summary").textContent =
    `${response.reroll_slot} changed · ${Object.keys(response.locked_bindings).length} other slot(s) locked`;
  const grid = $("generation-minimal-pair-grid");
  grid.replaceChildren(
    minimalPairSide("Pinned specimen", before, response.reroll_slot),
    minimalPairSide("One-slot reroll", after, response.reroll_slot),
  );
  $("generation-minimal-pair").classList.remove("hidden");
}

async function generateMinimalPair(slot, button) {
  const before = state.candidate;
  if (!before) return;
  button.disabled = true;
  setStatus(`rerolling ${slot} while every other slot stays locked…`);
  try {
    const response = await api("POST", "/api/generation/minimal-pair", {
      rule_id: before.target_rule,
      base_seed: before.seed,
      original_bindings: before.requested_bindings,
      reroll_slot: slot,
    });
    if (response.detail) {
      setStatus(response.detail, "err");
      return;
    }
    renderMinimalPair(before, response);
    await loadGenerationExploration();
    setStatus(
      `${slot}: ${before.requested_bindings[slot]} → ${response.candidate.requested_bindings[slot]}`,
      "ok",
    );
  } catch (exc) {
    setStatus(`minimal-pair generation failed: ${exc}`, "err");
  } finally {
    button.disabled = false;
  }
}

function canonicalValue(value) {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, canonicalValue(value[key])]),
    );
  }
  return value;
}

function sameValue(left, right) {
  return JSON.stringify(canonicalValue(left)) === JSON.stringify(canonicalValue(right));
}

function premiseDiffValue(candidate) {
  return candidate.premises.map((premise) => ({
    kind: premise.kind,
    index: premise.index,
    expression: premise.expression,
    status: premise.status,
    binding: premise.binding,
    reason: premise.reason,
    category_path: premise.category_path,
  }));
}

function describePremises(candidate) {
  return candidate.premises.map((premise) =>
    `${premise.expression}=${premise.status}${premise.binding ? ` → ${premise.binding}` : ""}`
  ).join(" · ") || "none";
}

function describeFacts(candidate) {
  return candidate.facts.map((fact) =>
    `${fact.type} ${JSON.stringify(canonicalValue(fact.fields))} @ ${fact.source}`
  ).join(" · ") || "none";
}

function describeCollisions(candidate) {
  return candidate.collisions.map((collision) =>
    `${collision.a_source} ↔ ${collision.b_source}: ${JSON.stringify(collision.key)}`
  ).join(" · ") || "none";
}

function renderGenerationRetest(before, after) {
  const rows = [
    {
      label: "Registry",
      beforeValue: before.registry_fingerprint,
      afterValue: after.registry_fingerprint,
      beforeText: before.registry_fingerprint.slice(0, 16),
      afterText: after.registry_fingerprint.slice(0, 16),
    },
    {
      label: "Target rule",
      beforeValue: [before.target_status, before.target_specificity],
      afterValue: [after.target_status, after.target_specificity],
      beforeText: `${before.target_status} · specificity ${before.target_specificity?.join("/") || "n/a"}`,
      afterText: `${after.target_status} · specificity ${after.target_specificity?.join("/") || "n/a"}`,
    },
    {
      label: "Premises",
      beforeValue: premiseDiffValue(before),
      afterValue: premiseDiffValue(after),
      beforeText: describePremises(before),
      afterText: describePremises(after),
    },
    {
      label: "Co-firing rules",
      beforeValue: before.actual_rule_ids,
      afterValue: after.actual_rule_ids,
      beforeText: before.actual_rule_ids.join(", ") || "none",
      afterText: after.actual_rule_ids.join(", ") || "none",
    },
    {
      label: "Emitted facts",
      beforeValue: before.facts,
      afterValue: after.facts,
      beforeText: describeFacts(before),
      afterText: describeFacts(after),
    },
    {
      label: "Collisions",
      beforeValue: before.collisions,
      afterValue: after.collisions,
      beforeText: describeCollisions(before),
      afterText: describeCollisions(after),
    },
    {
      label: "Deficiencies",
      beforeValue: before.deficiencies,
      afterValue: after.deficiencies,
      beforeText: before.deficiencies.join(" · ") || "none",
      afterText: after.deficiencies.join(" · ") || "none",
    },
  ];
  const changed = rows.filter((row) =>
    !sameValue(row.beforeValue, row.afterValue)
  ).length;
  $("generation-retest-summary").textContent =
    `${changed}/${rows.length} changed · identical sentence preserved`;
  const diff = $("generation-retest-diff");
  diff.replaceChildren();
  const head = el("div", "generation-diff-row generation-diff-head");
  head.append(el("div", "", "Surface"), el("div", "", "Before"), el("div", "", "After"));
  diff.append(head);
  for (const row of rows) {
    const rowChanged = !sameValue(row.beforeValue, row.afterValue);
    const line = el("div", `generation-diff-row ${rowChanged ? "changed" : "unchanged"}`);
    const label = el("div", "generation-diff-label", row.label);
    label.append(el("span", "generation-diff-badge", rowChanged ? "changed" : "same"));
    line.append(
      label,
      el("div", "generation-diff-value", row.beforeText),
      el("div", "generation-diff-value", row.afterText),
    );
    diff.append(line);
  }
  $("generation-retest").classList.remove("hidden");
}

function renderGenerationHypotheses(detail = "") {
  const section = $("generation-hypotheses");
  const list = $("generation-hypothesis-list");
  list.replaceChildren();
  section.classList.remove("hidden");
  $("generation-hypothesis-summary").textContent = state.hypotheses.length
    ? (
      `${state.hypotheses.length} source-linked suggestion(s) · ` +
      (
        state.reviewRecorded
          ? "recorded; use Review history → Edit for corrections"
          : "no automatic edits"
      )
    )
    : detail;

  for (const hypothesis of state.hypotheses) {
    const card = el("article", "generation-hypothesis");
    card.append(
      el("div", "generation-hypothesis-claim", hypothesis.claim),
      el(
        "div",
        "dim mono",
        `attached to ${hypothesis.premise.kind}` +
          (hypothesis.premise.index === null
            ? ""
            : ` ${hypothesis.premise.index + 1}`),
      ),
    );
    const observations = el("ul", "generation-hypothesis-observations");
    for (const observation of hypothesis.observations) {
      observations.append(el("li", "", observation));
    }
    card.append(observations);

    if (hypothesis.sources.length) {
      const sources = el("div", "generation-sources");
      for (const source of hypothesis.sources) {
        sources.append(generationSourceControl(source));
      }
      card.append(sources);
    }

    const controls = el("div", "generation-hypothesis-controls");
    const editableSource = hypothesis.sources.find(
      (source) => editableSourceNode(source),
    );
    if (editableSource) {
      const open = el("button", "generation-hypothesis-open", "Open in editor");
      open.type = "button";
      open.onclick = () => openGenerationSource(editableSource);
      controls.append(open);
    }
    const status = el("div", "generation-hypothesis-statuses");
    for (const value of HYPOTHESIS_STATUSES) {
      const button = el(
        "button",
        value === hypothesis.status ? "selected" : "",
        value,
      );
      button.type = "button";
      button.disabled = state.reviewRecorded;
      button.onclick = () => {
        if (state.reviewRecorded) return;
        hypothesis.status = value;
        renderGenerationHypotheses();
      };
      status.append(button);
    }
    const note = el("textarea", "generation-hypothesis-note");
    note.maxLength = 4000;
    note.placeholder = "Optional hypothesis note";
    note.value = hypothesis.note || "";
    note.disabled = state.reviewRecorded;
    note.oninput = () => { hypothesis.note = note.value; };
    controls.append(status, note);
    card.append(controls);
    list.append(card);
  }
}

async function formGenerationHypotheses() {
  const candidate = state.candidate;
  const defects = selectedGenerationDefects();
  if (!candidate?.target_rule || !state.reviewVerdict || !defects.length) return;
  const button = $("generation-form-hypotheses");
  button.disabled = true;
  setStatus("replaying matcher evidence and forming bounded hypotheses…");
  try {
    const response = await api("POST", "/api/generation/hypotheses", {
      rule_id: candidate.target_rule,
      sentence: candidate.sentence,
      seed: candidate.seed,
      requested_bindings: candidate.requested_bindings,
      attempts: candidate.attempts,
      origin: candidate.origin || "generated",
      generation_mode: candidate.generation_mode || "strict",
      lexical_relaxations: candidate.lexical_relaxations || [],
      verdict: state.reviewVerdict,
      defects,
    });
    if (response.detail && !response.hypotheses) {
      throw new Error(response.detail);
    }
    state.hypotheses = response.hypotheses || [];
    renderGenerationHypotheses(response.detail || "");
    setStatus(
      state.hypotheses.length
        ? `${state.hypotheses.length} advisory hypothesis suggestion(s)`
        : response.detail,
      state.hypotheses.length ? "ok" : undefined,
    );
  } catch (exc) {
    clearGenerationHypotheses(String(exc));
    setStatus(`hypothesis formation failed: ${exc}`, "err");
  } finally {
    updateGenerationReviewState();
  }
}

function renderGenerationCandidate(
  candidate,
  { resetRetest = true, preserveReview = false } = {},
) {
  const sentenceReview = !candidate.target_rule;
  const generationMode = candidate.generation_mode || "strict";
  const priorAttachment = preserveReview
    ? $("generation-attachment").value
    : "sentence";
  state.candidate = candidate;
  updateSaveRetestState();
  state.minimalPair = null;
  $("generation-minimal-pair").classList.add("hidden");
  $("generation-minimal-pair-grid").replaceChildren();
  $("generation-minimal-pair-summary").textContent = "";
  if (resetRetest) {
    $("generation-retest").classList.add("hidden");
    $("generation-retest-diff").replaceChildren();
    $("generation-retest-summary").textContent = "";
  }
  $("generation-empty").classList.add("hidden");
  $("generation-candidate").classList.remove("hidden");
  $("generation-target").textContent =
    candidate.target_rule || "Sentence-level interpretation review";
  $("generation-description").textContent = candidate.target_description || "";
  $("generation-review-title").textContent = sentenceReview
    ? "Sentence meaning review"
    : "Human review";
  $("generation-note").placeholder = sentenceReview
    ? "What is ambiguous, unsupported, or otherwise worth preserving?"
    : "What premise or emitted fact appears correct or defective?";
  $("generation-sentence").textContent = candidate.sentence;
  const status = $("generation-status");
  status.textContent = candidate.target_status;
  status.className = `generation-status ${candidate.target_status}`;
  $("generation-meta").textContent =
    `${candidate.origin || "generated"} · ${candidate.generator_version} · ` +
    `${generationMode.replaceAll("_", " ")} · ` +
    `seed ${candidate.seed} · ` +
    `${candidate.attempts} attempt(s) · ${candidate.registry_fingerprint.slice(0, 16)}`;
  if (candidate.origin === "generated") {
    $("generation-mode").value = generationMode;
    updateGenerationRuleState();
  }
  const modeNote = $("generation-mode-note");
  modeNote.replaceChildren();
  if (generationMode === "lexical_boundary") {
    const relaxations = candidate.lexical_relaxations || [];
    modeNote.append(
      el(
        "div",
        "mono",
        relaxations.length
          ? `Lexical boundary probe · ${relaxations.map((item) =>
              `${item.slot}=${item.surface}: ${item.requirement} → ${item.broader_domain}`
            ).join(" · ")}`
          : "Lexical boundary mode found no active category gate with an outside filler; this specimen remained strict.",
      ),
      el(
        "div",
        "",
        "A missing target match is an expected boundary observation, not proof that the sentence itself is invalid.",
      ),
    );
    modeNote.classList.remove("hidden");
  } else {
    modeNote.classList.add("hidden");
  }
  const probe = $("generation-probe");
  probe.replaceChildren();
  if (candidate.exploration_probe) {
    probe.append(
      el(
        "span",
        "mono",
        `focused lexicon probe: ${candidate.exploration_probe.identity} → ` +
        `${candidate.exploration_probe.surface} in ${candidate.exploration_probe.slot}`,
      ),
      generationSourceControl(candidate.exploration_probe.source),
    );
    probe.classList.remove("hidden");
  } else {
    probe.classList.add("hidden");
  }
  $("generation-seed").value = candidate.seed;
  state.lastGenerationSeed = candidate.seed;
  $("generation-sentence-review-fields").classList.toggle(
    "hidden",
    !sentenceReview,
  );
  renderGenerationPremises(candidate);
  populateGenerationAttachments(candidate);
  if (
    preserveReview
    && Array.from($("generation-attachment").options)
      .some((option) => option.value === priorAttachment)
  ) {
    $("generation-attachment").value = priorAttachment;
  }

  const matches = $("generation-matches");
  matches.replaceChildren();
  for (const match of candidate.actual_matches) {
    const card = el("div", `generation-match${match.shadowed ? " shadowed" : ""}`);
    card.append(
      el("span", "mono", match.rule_id),
      el("span", "dim", match.shadowed ? "shadowed" : "survived"),
      el("code", "", JSON.stringify(match.bindings)),
      el("span", "dim mono", `consumed: ${match.consumed_surfaces.join(" · ")}`),
    );
    matches.append(card);
  }
  if (!candidate.actual_matches.length) {
    matches.append(el("div", "dim", "no premise rule matched"));
  }

  const facts = $("generation-facts");
  facts.replaceChildren();
  candidate.facts.forEach((fact, index) => {
    facts.append(generationFactCard(fact, index));
  });
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

  if (!preserveReview) {
    state.reviewVerdict = null;
    state.reviewRecorded = false;
    document.querySelectorAll(
      ".generation-review .review-verdicts button",
    ).forEach((button) => {
      button.classList.remove("selected");
    });
    document.querySelectorAll("#generation-defects input").forEach((input) => {
      input.checked = false;
    });
    $("generation-note").value = "";
    $("generation-interpretation").value = "";
    $("generation-rule-suggestion").value = "";
    $("generation-review-result").textContent = "";
    clearGenerationHypotheses();
  } else if (state.hypotheses.length) {
    renderGenerationHypotheses();
  }
  updateGenerationReviewState();
}

async function saveAndRetest() {
  if (state.editorSaveBusy || !state.currentDoc || !state.candidate) return;
  const before = state.candidate;
  state.editorSaveBusy = true;
  updateSaveRetestState();
  try {
    const saved = await saveCurrentDoc({ rerunTrace: false });
    if (!saved?.ok) return;
    setStatus("retesting the identical pinned sentence…");
    const after = await api("POST", "/api/generation/retest", {
      rule_id: before.target_rule,
      sentence: before.sentence,
      seed: before.seed,
      requested_bindings: before.requested_bindings,
      attempts: before.attempts,
      origin: before.origin || "generated",
      generation_mode: before.generation_mode || "strict",
      lexical_relaxations: before.lexical_relaxations || [],
    });
    if (after.detail) {
      $("generation-retest").classList.remove("hidden");
      $("generation-retest-summary").textContent = "retest failed";
      $("generation-retest-diff").replaceChildren(
        el("div", "generation-issue", after.detail),
      );
      setStatus(`retest failed: ${after.detail}`, "err");
      return;
    }
    if (after.sentence !== before.sentence) {
      throw new Error("retest changed the pinned sentence");
    }
    renderGenerationCandidate(
      after,
      { resetRetest: false, preserveReview: true },
    );
    renderGenerationRetest(before, after);
    setView("generate");
    setStatus(
      `${after.target_rule}: ${before.target_status} → ${after.target_status} on the pinned sentence`,
      "ok",
    );
  } catch (exc) {
    $("generation-retest").classList.remove("hidden");
    $("generation-retest-summary").textContent = "retest failed";
    $("generation-retest-diff").replaceChildren(
      el("div", "generation-issue", String(exc)),
    );
    setStatus(`retest failed: ${exc}`, "err");
  } finally {
    state.editorSaveBusy = false;
    updateSaveRetestState();
  }
}

async function generateNext() {
  const selected = selectedGenerationRule();
  const generationMode = selectedGenerationMode();
  if (selected && !selected.supported) return;
  const seedInput = $("generation-seed");
  const prior = Number(seedInput.value);
  const seed = Number.isSafeInteger(prior) && seedInput.value !== ""
    ? prior + (prior === state.lastGenerationSeed ? 1 : 0)
    : Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
  // Consume the seed before realization.  A failed request must not leave the
  // next click pinned to the same deterministically impossible candidate.
  seedInput.value = seed;
  state.lastGenerationSeed = seed;
  setStatus("generating and round-tripping…");
  $("generation-next").disabled = true;
  try {
    const candidate = await api("POST", "/api/generation/candidate", {
      rule_id: selected?.id || null,
      filler_identity: generationMode === "strict"
        ? selectedGenerationFiller()?.identity || null
        : null,
      seed,
      generation_mode: generationMode,
    });
    if (candidate.detail) {
      await loadGenerationExploration();
      setStatus(`seed ${seed}: ${candidate.detail}`, "err");
      return;
    }
    renderGenerationCandidate(candidate);
    if (generationMode === "strict") await loadGenerationExploration();
    setStatus(
      `${candidate.target_rule}: ${candidate.target_status} · ${candidate.actual_rule_ids.length} actual rule(s)`,
      "ok",
    );
  } catch (exc) {
    setStatus(`generation failed for seed ${seed}: ${exc}`, "err");
  } finally {
    updateGenerationRuleState();
  }
}

function selectReviewVerdict(verdict, button) {
  if (state.reviewRecorded) return;
  state.reviewVerdict = verdict;
  document.querySelectorAll(
    ".generation-review .review-verdicts button",
  ).forEach((node) => {
    node.classList.toggle("selected", node === button);
  });
  clearGenerationHypotheses();
  updateGenerationReviewState();
}

async function saveGenerationReview() {
  const candidate = state.candidate;
  if (!candidate || !state.reviewVerdict) return;
  $("generation-save-review").disabled = true;
  const payload = await api("POST", "/api/generation/review", {
    candidate_id: candidate.id,
    origin: candidate.origin || "generated",
    generation_mode: candidate.generation_mode || "strict",
    lexical_relaxations: candidate.lexical_relaxations || [],
    review_kind: candidate.target_rule ? "premise" : "sentence",
    sentence: candidate.sentence,
    target_rule: candidate.target_rule,
    seed: candidate.seed,
    registry_fingerprint: candidate.registry_fingerprint,
    verdict: state.reviewVerdict,
    requested_bindings: candidate.requested_bindings,
    defects: selectedGenerationDefects(),
    hypotheses: state.hypotheses,
    interpretation: candidate.target_rule
      ? ""
      : $("generation-interpretation").value,
    suggested_rule: candidate.target_rule
      ? ""
      : $("generation-rule-suggestion").value,
    note: $("generation-note").value,
  });
  if (!payload.ok) {
    $("generation-review-result").textContent = payload.detail || "review rejected";
    $("generation-save-review").disabled = false;
    return;
  }
  $("generation-review-result").textContent =
    `recorded ${state.reviewVerdict} · ${payload.review.timestamp}`;
  state.reviewRecorded = true;
  await loadGenerationExploration();
  if (state.hypotheses.length) renderGenerationHypotheses();
  updateGenerationReviewState();
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
$("save-retest-btn").onclick = saveAndRetest;
$("editor").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "s") {
    e.preventDefault();
    if (e.shiftKey) saveAndRetest();
    else saveDoc();
  }
});
$("impact-btn").onclick = runImpact;
$("baseline-btn").onclick = setBaseline;
$("view-reading").onclick = () => setView("reading");
$("view-generate").onclick = () => setView("generate");
$("view-reviews").onclick = () => setView("reviews");
$("view-semantic").onclick = () => setView("semantic");
$("view-field").onclick = () => setView("field");
$("view-proof").onclick = () => setView("proof");
$("generation-next").onclick = generateNext;
$("generation-mode").onchange = () => {
  if (selectedGenerationMode() === "lexical_boundary") {
    $("generation-filler").value = "";
  }
  updateGenerationRuleState();
};
$("generation-seed").addEventListener("input", () => {
  // A user-entered seed is an explicit request to try that exact seed once.
  state.lastGenerationSeed = null;
});
$("generation-reading").onclick = inspectGeneratedReading;
$("generation-form-hypotheses").onclick = formGenerationHypotheses;
$("generation-save-review").onclick = saveGenerationReview;
initializeGenerationDefects();
document.querySelectorAll(
  ".generation-review .review-verdicts button",
).forEach((button) => {
  button.onclick = () => selectReviewVerdict(button.dataset.verdict, button);
});
updateGenerationReviewState();
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
