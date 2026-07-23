# RuleKit — grammar-driven reading & reasoning engine (fresh start)

## Context

The predecessor (`~/Development/experiments/difg`) proved the thesis: a model-free **obligation
parser** reads word problems into facts and answers deterministically (GSM8K TEST precision ~89%,
0 LLM calls). It died of a representation problem, not a mechanism problem:

- `reasoning/reading.py` = **28,871 lines**, ~382 functions, ~129 "system solvers" in two
  hand-ordered first-match-wins dispatch lists (ordering constraints live in comments).
- All grammar/lexical data are Python literals scattered through the file (LEXICON updated in
  8 places with duplicate-key shadowing).
- Conflicts are post-hoc: category registration is global state with invisible blast radius
  (tagging `pet` once silently turned a correct decline into a confident wrong); collisions are
  only caught by an offline audit; guards and solvers are mutually entangled.
- An LLM translator fallback is woven into the `ask` surface.

**RuleKit** (`~/Development/rulekit`, currently empty) keeps the mechanism and inverts the
representation: **small frozen kernel, big declarative data; no LLM anywhere; conflict detection
always on.**

User decisions already made: **Python engine + web UI** (FastAPI bridge, Vite/React/Monaco
frontend) · **rules as schema-validated YAML** (no custom DSL) · **engine + harness first, mine
difg's lexical data, GSM8K + visual tool after**.

## What survives from difg (the DNA)

1. **Obligation-driven parsing** — every word carries a demand it discharges by binding; parsing
   IS discharge; deficiency = unmet obligation; sense disambiguation = best obligation coverage;
   reasoning = facts off the saturated graph. Obligations attach by ROLE (quantifier→collection,
   verb→subject+dobj, preposition→anchor+object…).
2. **Definitive-or-decline** — bind/commit only when exactly one candidate fits.
3. **Epistemic surface** — diagnose (why declined), known_facts, question-requirements corpus
   (shape → needed world-knowledge → supplied?), report; provider loop supplies missing facts.
4. **Minimum-structure rule** — patterns hardcode only grammatical skeleton; content words are
   captured + category-gated with cross-slot lemma consistency.
5. **Category hierarchy** with sense roots, antonym links (polarity sets DERIVED, single source),
   context synonyms (gated by governing category), quantitative attrs (dog→4 legs).
6. **Rules emit FACTS, not answers** (SystemResult lesson) — one shared saturate/answer pipeline.
7. **Every mutation a reversible Decision** through one chokepoint → serializable trace.
8. **Value accounting** — every stated number must be consumed or the reading declines.
9. **The testing methodology** (port `reading-coverage-methodology.md` near-verbatim): harm-ordered
   outcomes (wrong ≫ declined), precision = correct/committed is THE metric, DEV/TEST firewall,
   stable-md5 dev-train/dev-holdout split, per-increment diff with SOLVED/BROKE/DECL→WRONG ship
   gate, collision audit, rule attribution, unknown-word worklist, coverage = ceiling × hit-rate.

## Architecture

### Repo layout

```
rulekit/
├── pyproject.toml            # uv, Python 3.12+; deps: pydantic v2, ruamel.yaml, pyarrow (+fastapi/uvicorn extra)
├── docs/                     # methodology.md (ported), playbook.md (distilled), rule-authoring.md, architecture.md
├── src/rulekit/
│   ├── kernel/               # stable core, each module ≤ ~400 lines
│   │   ├── model.py          # Word, Unit, Obligation, Decision(+rule provenance), Reading, Document, Fact types
│   │   ├── tokenize.py  numbers.py  senses.py  obligations.py  condense.py
│   │   ├── patterns.py       # pattern-rule compiler/matcher (catsearch successor), trigger index, subsumption
│   │   ├── facts.py          # fact store: dedupe, agreement, conflict adjudication (always-on)
│   │   ├── saturate.py       # synthesizer fixpoint: YAML synth rules + entry-point Python plugins
│   │   ├── answer.py         # the few generic consumers (fold, combined, comparative, category-sum…)
│   │   ├── guards.py         # value accounting etc., config-driven, may NOT reference rule ids (lint-enforced)
│   │   ├── evaluate.py       # safe arithmetic evaluator (ast whitelist; the only math path; logs provenance)
│   │   └── document.py       # document blackboard + re-parse fixpoint (gap table, rounds)
│   ├── data/                 # schemas.py (pydantic = the one format truth), packs.py, registry.py (immutable compile)
│   ├── epistemic/            # diagnose.py, requirements.py, providers.py
│   ├── lint/                 # overlap.py, blast_radius.py, checks.py
│   ├── harness/              # bench.py, firewall.py, snapshot.py, collisions.py, attribution.py, cache.py
│   ├── server/               # FastAPI app + routes (trace, docs CRUD, impact, bench SSE, schema export)
│   └── cli.py
├── packs/core-english/       # migrated difg lexical data + core grammar
├── packs/arithmetic/         # general solver families as pattern rules + plugin synthesizers
├── projects/curated/         # phase-1 hand-written validation suite
├── projects/gsm8k/           # parquets copied from difg/data (gitignored)
├── tools/migrate_difg.py     # one-off: import difg reading.py, dump runtime tables → YAML
├── web/                      # Vite + React + TS + Monaco designer
└── tests/                    # pytest, synthetic strings only (firewall: never benchmark items)
```

### Execution model — the ordering fix

- Per-sentence pipeline (difg's proven order): tokenize → numbers → senses → disambiguate →
  obligations → condense → resolve → **pattern rules** → learn → saturate (fixpoint) → guards →
  answer. Each stage a pure function `Reading → Reading` over the immutable compiled Registry.
- **No ordered dispatch.** ALL triggered pattern rules match (no short-circuit); all emit facts.
  Conflicts adjudicated in the fact store: **computed subsumption** (strictly-more-specific match
  — wider consumed span + equal-or-narrower category gates — shadows silently; this replaces
  "narrow the category" as the conflict lever), non-subsuming disagreement → both withheld, item
  declines, `Collision` recorded. Agreement → dedupe. Only scheduling knob: `phase: read |
  post-saturation`. difg's masked-collision failure mode is unrepresentable.
- Rules match the annotated **unit sequence**, not raw text ("1,200" ≡ "twelve hundred" — retires
  the comma-regex bug class). Matched slots discharge obligations to a PATTERN sentinel; a rule's
  `consumes:` feeds value accounting so guards never know rule names.
- **Determinism invariant**: immutable registries, sorted iteration everywhere, `bench --twice`
  (two fresh processes, diff) in CI — the `next(iter(set))` lesson as tooling.

### YAML formats (all `format: rulekit/<kind>@1`, pydantic-validated; Monaco gets JSON Schema free)

Lexicon (merges difg LEXICON+PLURALS+VERB_LEMMA; duplicate keys across a pack = load error):
```yaml
entries:
  rose: {senses: [noun, verb], verb: {lemma: rise}, notes: "flower or past of rise"}
  student: {senses: [noun], plural: students}
```

Categories (hierarchy + antonyms + context synonyms + attrs in one kind; compile invariants:
one root sense per category, antonym memberships disjoint, members must exist in lexicon):
```yaml
categories:
  pet:  {parent: animal}
  lose: {parent: verb, antonym: acquire}
members: {animal: [dog, cat, lizard], lose: [lose, lost, spend, "give away"]}
context_synonyms:
  appendage: {gate: animal, forms: [leg, legs, foot, feet]}
attrs: {dog: {legs: 4}, quarter: {cents: 25}}
```

Pattern rules (successor of the 129 solvers; literals allowed only as skeleton; **no priority
field — specificity is computed**; `overrides:` escape hatch requires a reason and is lint-reported):
```yaml
rules:
  - id: arithmetic/anchored-relation
    phase: read
    match:
      sentence:
        - {slot: who, type: name}
        - {lit: has}
        - {slot: n, type: number}
        - {slot: dir, cat: comparative}
        - {slot: item, type: noun}
        - {lit: than}
        - {slot: std, type: name}
    where: [{distinct: [who, std]}, {name_count: {exactly: 2}}]
    consumes: [n]
    emits:
      - {fact: relation, subject: "{who}", standard: "{std}",
         measure: "{item.lemma}", offset: "n * sign(dir)"}
asks:
  - id: ask/how-many-entity
    match: {question: [{lit: how}, {lit: many}, {slot: item, type: noun}, ...]}
    resolves: {consumer: single-entity, entity: "{who}", measure: "{item.lemma}"}
```

Synth rules (datalog-ish; monotone; safe-evaluator expressions; algorithmic ones — affine graph,
partition saturation — stay Python plugins via `rulekit.synthesizers` entry points with declared
reads/emits footprints):
```yaml
rules:
  - id: synth/fraction-of-parent
    when:
      - {fact: subset, part: P, whole: W, fraction: F}
      - {fact: quantity, entity: W, measure: M, value: N}
    unless: [{fact: quantity, entity: P, measure: M}]
    emit: [{fact: quantity, entity: P, measure: M, value: "N * F"}]
```

Plus: requirements corpus (question shape → needs → supplied_when), guards.yaml, pack.yaml
(name, requires, `activation: {always | when: <condition over fact store>}`), project.yaml
(packs, datasets, md5 splits, firewall config).

### Conflict detection — four layers, cheapest first

1. **Compile invariants** (build fails loudly): duplicate lexicon keys, dangling parents, antonym
   overlap, undeclared slot refs.
2. **Static lint**: pattern-overlap analysis with synthesized witness sentences; specificity ties
   between overlapping rules = error; **category blast-radius diff** — "tagging pet⊂animal with
   {dog,cat} makes rules [category-sum, part-count] newly applicable to N dev-train items" —
   printed BEFORE anything runs (the direct fix for the `pet` disaster).
3. **Always-on runtime adjudication** (§ execution model) — collisions can't be masked by order.
4. **`rulekit collisions`** — reads Collision records from the last snapshot (free; TEST-safe,
   counts only). Ship gate: disagreeing collisions = 0.

### Document-level re-parse loop (the big new capability)

`Document` blackboard: per-sentence Readings, global fact store, discourse referents, active
packs, and a **gap table** (typed records: unknown-word / ambiguous-sense / unmet-obligation /
missing-fact, keyed by what would fill them). Round 0 parses all sentences; each later round
re-parses **only sentences owning a gap matched by a new event** (fact admitted, referent
resolved, provider supplied, pack activated). Re-parse is a pure recompute with enriched context;
old facts retracted atomically with provenance-chained retraction of downstream synthesized
facts. Termination: each round must resolve a gap or grow the store; round cap (default 6) errors
loudly. Between rounds: requirements corpus matches open gaps → deterministic **providers**
(entry points: conversion tables, attr databases, project fact files — no LLM) supply
document-scoped facts; **task-specific packs activate** on fact-store conditions (monotone,
between rounds only). Superseded readings stay in the trace (`superseded_by_round=N`).

### Harness & CLI

```
rulekit parse|solve|diagnose <text|file> [--trace --json]
rulekit lint [--diff]              # static checks + blast radius
rulekit bench --project P --slice dev-train [--twice]
rulekit diff <snapA> <snapB>       # SOLVED/BROKE/DECL→WRONG + ship-gate exit code
rulekit collisions | stats         # collision report; rule attribution + unknown-word worklist
rulekit serve --project P          # web designer
rulekit migrate-difg <path>
```

Firewall with teeth: md5 bucket is the only split path; `--slice test` is aggregate-only and
requires `--spend-test-look`, appending to an auditable `test-ledger.jsonl`; `--limit` prints the
PARTIAL-FIREWALL warning. Snapshot = per-item {outcome, answer, rule ids, collisions, decline
reason} + registry fingerprint.

**Honest incrementality**: per-item cache keyed on (item hash, relevant fingerprint) computed
from the trigger index; kernel/guard/plugin/answer-fold changes invalidate everything (they're in
every relevant set); category changes over-invalidate the whole subtree's items; TEST look always
`--no-cache`; CI periodically asserts cache ≡ full run. Effect: the designer's impact panel
re-runs tens of items, not thousands.

### Web designer (v1)

Engine records every mutation as a serializable Decision → **step-through needs no engine
pauses**: server returns the full decision stream; UI steps a cursor, reconstructing state.
The designer has four complementary lenses over one result: **Reading** shows
the token ribbon, obligations, decisions, facts, and gaps; **Semantic field**
groups facts by observed/knowledge/derived epistemic role and independently
marks exact versus structured representation; **Deictic field** shows reference
coordinates and declines; **Proof** shows a consumer-owned normalized query,
named inference steps, and evidence fact ids. Semantic and proof views are
projections of the result, never a second inference engine. The editor writes
schema-validated YAML back with comments preserved, while the impact panel
enforces the DEV/TEST firewall. Later: category graph, collision explorer,
rule-from-example scaffolding.

Ask ambiguity is represented before consumer dispatch. A pack ask may provide
multiple normalized interpretations; without a caller selection the answer is
a non-committing clarification request and Proof remains paused. The trace API
round-trips an interpretation id, then reruns the ordinary solve path with only
that query selected. This is distinct from `undetermined`, which means one
query was understood but the fact store cannot decide it.

### Migration from difg

`tools/migrate_difg.py`: **import, don't parse** — `import reasoning.reading` executes all 8
LEXICON update sites and every `_register_category`/`_tag_word`/`_tag_attr`, so dumping the final
runtime dicts captures true merged state. Dump (sorted, deterministic) → core-english pack:
LEXICON/PLURALS/VERB_LEMMA → lexicon files; WORD_CATEGORIES/CATEGORY_PARENTS/CATEGORY_ANTONYMS/
CONTEXT_SYNONYMS/WORD_ATTRS/PART_COUNTS → categories; CONVERSIONS/_UNIT_ALIAS → units;
NUMBERS/SCALES/MULTIPLIERS/OPERATORS → numbers; ROLE_OBLIGATIONS → obligations.yaml.
Cross-validate through the registry compiler. Mine the **poison list** (words withheld because
they regressed holdout) into `quarantine.yaml` as documentation/lint data. **Not migrated**: the
~90 per-problem `vocab_singles` branches (methodology §9 prices them dev-only — carrying them
imports the sprawl). The general families that carry TEST (fold, anchored, affine, fraction,
percent) are hand-ported as pattern rules + plugin synthesizers in `packs/arithmetic/`.

## Phases (each with verification)

- **P0 scaffold**: uv/pyproject, git init, pydantic schemas, pack loader + compile invariants,
  determinism harness, CI. ✓ toy pack compiles; two fresh-process compiles → identical fingerprints.
- **P1 kernel + curated suite** (the milestone): full pipeline, Decision/trace, evaluator, value
  accounting, pattern matcher; starter core-english (~200 words, 5–10 rules, 3–5 asks, 2 synths);
  `projects/curated` ~100 hand-written items covering fact types, consumers, ambiguity, negation,
  declines; bench + snapshots + diff + ship gate. ✓ curated bench: 100% precision, >0 coverage;
  `--twice` identical; every mutation in `--trace`.
- **P2 migration + conflict tooling**: migrate-difg; lint overlap/blast-radius/ties; collision
  surfacing. ✓ migrated pack compiles (documented exceptions); planted overlapping rule caught
  statically with witness; the `pet` scenario reproduced as a test.
- **P3 document loop + epistemic surface**: blackboard, gaps, rounds, retraction, providers,
  requirements, diagnose, pack activation. ✓ multi-sentence curated docs reach fixpoint; a
  round-2-dependent doc answers correctly with superseded trace visible; cyclic doc hits cap loudly.
- **P4 GSM8K + arithmetic pack + cache**: parquets, splits/firewall/ledger, general families
  ported, trigger-index cache + cache≡full CI check. ✓ precision matches difg's general machinery
  at corresponding coverage; 0 disagreeing collisions; single-rule edit re-runs only affected items.
- **P5 web designer v1**: routes, Monaco, stepper, impact panel. ✓ UI edit preserves YAML
  comments; save→impact cycle < ~15 s via cache.
- **P6 workflow surface**: library API (`rulekit.load_project(p).solve(text)`), MCP wrapper,
  docs pass.

## Verification (end-to-end)

- `uv run pytest` green at every phase; `rulekit bench --project curated` = 100% precision.
- Determinism: `rulekit bench --twice` byte-identical outcomes.
- Conflict tooling proven by planted-failure tests (overlap witness, blast radius, collision).
- P4 exit: GSM8K dev-train/holdout run clean; one audited TEST look recorded in the ledger.
- P5 exit: full author-loop in the browser — edit rule → lint → step trace → impact buckets.
