# The breadth-first premise-reader campaign — FOLIO logic → full integration

**PLAN ONLY. No implementation in this session.**

## Context

The benchmark-loaded FOLIO logic frontier lives in `projects/scratch/`: no benchmark project
loads `projects/scratch/packs/logic`, and the real `projects/folio` remains the repo's sole
expect-0-commits safety gate. Some supporting consumers and saturation plugins already live
in the shared kernel, dormant unless pack rules make them reachable; Phase A therefore
inventories that shared machinery rather than treating Phase D as merely a pack move. Five
TEST looks are spent. Looks #3–#5 returned identical aggregates
(1 correct / 1 wrong / 283 declined of 285, precision 0.5 held), and looks #4–#5 measured
**zero transfer** from ~19 dev-train conversions across 8+ distinct stories — including three
designed inference stages (elimination, reductio, identity). The recorded diagnosis
(`projects/scratch/ROADMAP.md` look-#5 entry; `folio-campaign-state` memory): a TEST
conversion requires an entire story STACK (every premise reader + inference shape + ask) to
align, and at 285 TEST items the overlap with any 20-story dev sample is ~0. Story-by-story
mining cannot move TEST. The sanctioned route to integration is **breadth-first
premise-reader coverage of the convertible pool's common blocker classes** — a different
campaign with a different cost curve. This file is that campaign's plan.

## Fixed facts the plan is built on (do not re-derive)

- **Convertible pool = 314** dev-train declines (137 false-gold + 177 true-gold);
  `ROADMAP.md:613-620`. The 169 'Uncertain' items are `text` golds — never convertible,
  wrong-hazards only. (ROADMAP also says "311" at line 891; Phase A re-measures and fixes
  the number.)
- Post-Stage-7 split: 301 no-ask declines vs 179 consumer-reached undetermined; 76
  "near-frontier" declines (conclusion side reads, no logic fact decides).
- Stage-6 gap taxonomy (over the then-170 undetermined; STALE, re-measure in Phase A):
  entity-atoms-unrelated 52 · entity-raw-other 37 · paraphrase-gap 28 · entity-in-raw-or 23 ·
  entity-absent 13 · entity-in-raw-if 10 · substring-bridge 2.
- Banked zeros (rebuild only WITH a measured buyer): `_naive_singular` -se/-ce/-ze fix,
  CamelCase-name senses, verbal universal conclusion asks. Re-measure after reader changes
  (the 8d lesson: a zero is scoped to its join).
- Unwinnable, never chase: Dickinson [7]/[8]/[9] (missing-period mega-sentence), item 228
  (FOL-verified poisoned gold), [99] (event/time machinery).
- The one real TEST hazard: indefinite subjects — the `blocks_skipped: indefinite_article`
  gate is BUILT (Stage 5 precondition 1). Preconditions 2–3 (ladder re-measure with null
  controls; looks only at class-sized commit counts) still bind.
- Measurement harness: no scratch datasets — folio-with-logic is measured by temporarily
  wiring `./packs/logic` into the folio project (never committed), `rulekit --project
  projects/folio bench --slice dev-train|dev-holdout --snapshot` + `diff`
  (`src/rulekit/cli.py:72,107-114,276-306`). Snapshots in `projects/folio/snapshots/`.
  Firewall: `build_corpus.py` buckets by PREMISE BLOCK, `SALT = "folio-test@1"` — never touch.
- Existing machinery (`projects/scratch/packs/logic/`): ~70 rules in `rules/logic.yaml`
  (copular/bare-plural/verbal universals, conditionals, disjunctions, enumeration, alias,
  appointive passive, ~14 ask shapes), 16 synths in `synth.yaml` (instantiation, chains,
  MT, DS, XOR, case analysis) + 3 saturate plugins (elimination, name-prefix-alias,
  name-head-sortal) + the reductio engine in `consumers/logic_verdict.py`.

## Campaign phases

### Phase A — re-survey the pool by BLOCKER CLASS (measurement only, ~1 session)

Goal: replace the stale Stage-6 taxonomy with a current, per-PREMISE classification of the
314-pool, ranked by expected stack-readiness gain / estimated reader cost, scoped to
verdict-gold items only. A large expensive class does not rank higher merely because its cost
is larger.

1. Scratchpad classifier (throwaway, per `docs/methodology.md` §4 — never committed):
   for every item in the pool, dump the fact store + fragment-veto reasons per premise
   sentence; bucket premises by construction (passive, relative clause, do-support negation,
   compound generic, scope-ambiguous "All X are not Y", unknown vocabulary, coordination,
   definite description/anaphora, modal, temporal). Labels are MULTI-LABEL: a premise may
   carry several blockers, and class totals therefore need not sum to the premise count. A
   separately recorded primary blocker may be used for ordering, but its precedence must be
   declared rather than inherited from classifier branch order.
2. **Optional oracle (pydelphin/ACE+ERG, offline only):** run the ERG over the pool's
   premise sentences to label constructions mechanically (passive/relative/scope/unknown
   word). Strictly a survey tool in the scratchpad — never a runtime dependency, never in
   the verdict path. Skip if setup costs more than a session; hand-classification of veto
   reasons is the fallback.
3. The classifier may be throwaway; the evidence defining a long-running gate may not be.
   Deliverables committed to `projects/scratch/`: a refreshed taxonomy table in ROADMAP.md,
   the resolved 311-vs-314 number, exact label/precedence definitions, corpus + registry
   fingerprints, counts by dev-train/dev-holdout and story, and a machine-readable DEV-only
   baseline report containing IDs/labels but no copied TEST data. Record enough regeneration
   detail that a later session can reproduce the totals without relying on memory.
4. Record three nested baselines, not one soft proxy:
   - **fact-bearing**: premise mints at least one fact (diagnostic only; insufficient alone);
   - **fully read**: no operative span remains under a fragment veto or unknown-word block;
   - **stack-ready**: the ask and conclusion are represented, every required premise is fully
     read, at least one fact-key path overlaps the conclusion's entities/predicates, and the
     story has no new contradiction, quarantine, or ambiguous-alternative state.
5. Inventory the already-shared kernel consumers/plugins reached by the scratch logic pack.
   Promotion risk is the change in reachability of shared machinery, not just moving YAML.
6. Phase A closes by pre-registering numeric Phase C thresholds for BOTH grouped DEV splits
   and publishing the Phase B build order by expected stack-ready gain / cost.

### Phase B — premise readers by class, breadth-first (the long middle)

Goal: raise READING coverage across the pool, class by class — not conversions per story.
The measured lever is the veto-lift (four precedents: 8g, 9d ×2, 9f): a read sentence stops
pricing its item, independent of whether that item converts.

Rules of engagement (all inherited, non-negotiable):
- One class = one increment = one revertible commit, landed in `projects/scratch/packs/logic`.
  Full gate per increment: pytest (synthetic only), all nine benchmark slices snapshot-diff
  NEUTRAL, folio-with-logic dev-train + dev-holdout diff (0 BROKE, 0 DECL→WRONG), null
  controls on every conversion. Whole-construction-or-nothing matching; unread stays
  monotone-safe.
- Track THREE metrics per increment: conversions (may be 0 — acceptable for readers),
  fully-read/veto movement for the targeted class, and stack-ready story movement. Merely
  minting any fact is not buying: the intended blocker must disappear and the emitted key
  must be relevant to an existing conclusion/inference join. An increment that moves none is
  an unbought enabler — revert and bank it (the `enabler-must-be-bought` memory, relaxed ONLY
  in that measured reader or stack movement now counts as buying).
- Every reader increment gets falsification tests even when it converts zero corpus items:
  a synthetic positive asserting the exact emitted fact shape, a minimal-pair negative that
  mints nothing, a synthetic composition proving that key can join existing inference, and
  a larger-construction probe that refuses partial reading. Conversion-specific null controls
  remain mandatory in addition to these reader controls.
- After each class lands, re-measure the banked zeros against the new join surface before
  starting the next class (the 8d/9d lesson).

Candidate class order (Phase A finalizes; expected shape from current data):
1. **Do-support negation VR** — biggest single conclusion surface (29), blocked on the
   state-verb 'have' discipline + 'live' vocabulary; parts already staged by 9j's MT pair.
   Keep it first only if Phase A shows that serving the conclusion surface materially raises
   stack readiness; conclusion count by itself is not a premise-reader buyer.
2. **entity-raw-other constructions** (37): compound generics ("Guard dogs are protective"),
   remaining passives, participials — mostly one-rule reader families.
3. **entity-in-raw-or** (23): conjunctive disjuncts ("either P and Q, or ¬P and R") —
   Stage 3 extension, machinery exists.
4. **entity-in-raw-if** (10): negated-antecedent conditionals — needs Stage 3 case analysis
   already built; reader only.
5. **Scope-marked universals** ("All X are not Y"): a designed stage — an
   unresolved-scope fact marker consumable only by scope-invariant verdicts (the MRS
   underspecification borrowing). Only if Phase A shows the class has verdict-gold buyers.
6. **paraphrase-gap** (28) stays LAST — it is the composition frontier
   (`composition-design.md` stacks), the steepest cost curve.

Infrastructure borrowings (each its own increment, only if Phase B friction proves the need):
- **Key-schema lint** (the SEM-I borrowing): every emitting rule declares its mintable key
  shapes; lint joins them against consumer key shapes. Catches the curly-apostrophe /
  double-render / self-lemma class at build time. Extends `rulekit lint`.
- **Verb-lemma table completion** (the 71 self-lemma verbs, 9c): a difg-mined/core-english
  pack change with repo-wide key churn — own increment, full nine-slice gate, only when a
  class (e.g. 'lives in' locatives) is measurably blocked on it.

### Phase C — the look-#6 coverage checkpoint

Look #6 is NOT scheduled off conversion count (twice-measured lesson). Phase A pre-registers
the numeric trigger; it must include ALL of:
- fragment-veto / fully-read improvement reaches its target on BOTH dev-train and the grouped
  dev-holdout, not only on the mined split;
- stack-ready coverage rises by its target across multiple distinct stories on BOTH splits;
- ≥3 blocker classes are fully served;
- contradiction, quarantine, ambiguous-reading, and wrong-hazard metrics do not increase.

The user calls the look (TEST looks are always user-directed); one aggregate-only look,
walked in commit order. The parked aggregate is 1 correct / 1 wrong / 283 declined. TEST
acceptance requires **wrong ≤1, correct ≥1, errors = 0, and precision ≥0.5**. Any wrong-count
increase reverts the responsible commit even when correct count rises enough for precision to
hold or improve; a ratio may never launder a new confident wrong.

### Phase D — the gate back to FOLIO (integration proper)

Only after a look #6 that shows nonzero transfer at held precision:
1. Re-run the Stage 5 preconditions: ladder re-measure with the real machinery, every
   commit null-controlled; the indefinite-article gate already covers the one known hazard.
2. **Recommended end state: promote `packs/logic` to top-level `packs/` and add a parallel
   `projects/folio-logic`** that loads it — making folio-logic an ATTEMPTED corpus with the
   standard bar (0 BROKE, 0 DECL→WRONG, hand-inspected commits), while `projects/folio`
   keeps loading
   `[core-english, arithmetic, difg-mined]` and remains the repo's only 0-commit safety
   gate. Flipping folio itself would forfeit that gate (the SciBench precedent shows a
   replacement corpus is expensive); revisit only if folio-logic proves stable across
   multiple TEST looks.
3. `folio-logic` references the existing `projects/folio/data/*.parquet` files. Do NOT copy
   `build_corpus.py`, re-materialize the corpus, or define a second SALT: the existing FOLIO
   builder remains the one firewall definition.
4. TEST history must not reset when the project root changes. Before the first folio-logic
   look, preserve/import the five historical ledger rows with provenance and designate one
   continuing campaign ledger; document the transition in ROADMAP/HANDOFF. A fresh project-
   scoped `snapshots/test-ledger.jsonl` must never be presented as zero prior looks.
5. Update CLAUDE.md (gate table) and `docs/HANDOFF.md`; per standing instruction, push
   after each landed batch.

## Files touched (implementation phase, for scoping only)

- `projects/scratch/packs/logic/rules/logic.yaml`, `synth.yaml`, `categories/logic.yaml` —
  the Phase B readers (bulk of the work; pattern per class, one commit each).
- `projects/scratch/ROADMAP.md` — taxonomy refresh + per-stage records.
- `src/rulekit/kernel/` — only for designed stages (scope marker) or the key-schema lint;
  every kernel touch gets the full nine-slice NEUTRAL gate (shared-reader blast radius).
- Phase D: `packs/logic/` (moved), `projects/folio-logic/project.yaml`, the continuing
  TEST-ledger record/provenance, `CLAUDE.md`, `docs/HANDOFF.md`. The project references the
  existing FOLIO parquets; it owns no duplicate corpus builder.
- Scratchpad only, never committed: the Phase A classifier and any ERG survey tooling. Its
  reproducible DEV-only baseline report and metric definitions ARE committed.

## Verification

- Per increment: `uv run pytest`; `uv run rulekit --project projects/curated bench --slice
  suite`; snapshot+diff on **difg dev**, gsm8k dev-train/dev-holdout, asdiv, svamp, mawps,
  scibench, and folio (all NEUTRAL); folio-with-logic dev-train + dev-holdout diff (0 BROKE,
  0 DECL→WRONG). Pack-only scratch changes are expected to be neutral on projects that do
  not load the pack; those runs preserve the gate but do not substitute for folio-with-logic
  behavior. Kernel/core changes require the full matrix because their blast radius is live.
- Per reader increment: the four synthetic falsification/composition probes above, plus null
  controls on every conversion (swap subject/predicate/premise — the answer must move).
- Per phase: fact-bearing, fully-read/veto, stack-ready, and hazard metrics vs the Phase A
  baseline, split by grouped dev-train/dev-holdout and recorded in ROADMAP.md.
- TEST: user-directed looks only, ledgered in `projects/folio/snapshots/test-ledger.jsonl`;
  TEST-look scripts must be FILES, never heredocs (jobs>1 spawn crash, pinned in memory).
  After Phase D, follow the explicitly migrated continuing campaign ledger. Accept only when
  wrong ≤1, correct ≥1, errors = 0, and precision ≥0.5.

## Explicitly out of scope

- Any TEST mining or item-level TEST inspection (aggregate-only, forever).
- Chasing item 228, the Dickinson items, [99], or the Bayern sortal-free instantiation.
- pydelphin/ACE/ERG anywhere in the runtime or verdict path.
- difg's logic domain (8-of-8 'Yes' golds — an always-yes engine aces it).
