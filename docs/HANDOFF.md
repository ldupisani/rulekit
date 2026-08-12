# rulekit handoff

**Updated:** 2026-08-12
**Runtime checkpoint:** `de6d74e` (`main`)
**Active campaign:** GSM8K Mining v2, M7 example-led vertical mining
**Immediate state:** all four published Mining v2 candidates are landed; no
candidate is awaiting human or machine review

This is the operational entry point. It records current state, durable
boundaries, and the next safe action. Completed increment narratives belong in
[`mining-log.md`](mining-log.md), measured dead ends in
[`negative-results.md`](negative-results.md), and design detail in the linked
plans and architecture document.

## Read first

1. [`../CLAUDE.md`](../CLAUDE.md) — constitution and standing gates.
2. [`architecture.md`](architecture.md) — current runtime and authoring
   architecture.
3. [`gsm8k-mining-v2-plan.md`](gsm8k-mining-v2-plan.md) — active campaign and
   promotion contract.
4. [`methodology.md`](methodology.md) — DEV/TEST firewall and precision policy.
5. [`generation-and-annotation-plan.md`](generation-and-annotation-plan.md) —
   implemented Designer product contract and milestone record.

## Current position

RuleKit is a deterministic controlled-English reader and reasoner. Language
knowledge lives in validated YAML packs; runtime Python provides grammatical,
fact, inference, and consumer machinery but contains no corpus vocabulary and
no per-question solvers. Generated examples and human reviews are authoring
evidence only and never enter the runtime registry.

The active mining method is M7:

1. select one currently declining GSM8K `dev-train` item;
2. record only its stable id and structural class, never its prose;
3. build invented end-to-end analogues and negative neighbours;
4. extend general grammar, inference, asks, and bounded YAML vocabulary;
5. pass synthetic tests before checking the original item locally by id;
6. publish an immutable candidate manifest for Designer review;
7. require exact human approval and the complete machine gate; and
8. integrate sequentially, then spend any protected look manually and
   deliberately.

The corpus sentence is never committed to tests, manifests, briefs, or docs.
One item can motivate an increment but cannot justify a one-off mechanism.
The shipped M7 increments are recorded in [`mining-log.md`](mining-log.md):
temporal event totals (130), task-completion duration gaps (131), and
anaphoric distance chains with exact combined totals (132).

### Latest implementation checkpoint

The latest consolidation moves positive lexical role knowledge out of grammar
rules and into extensible category relationships:

- `CategoryDef.selectional_roles` defines inherited actor/theme contracts for
  verb categories. Child categories may narrow, never broaden or replace a
  role with an unrelated target.
- `verb_roles_compatible` maps a construction's slots to those semantic roles.
  The registry selects one complete most-specific frame; sibling senses are
  alternatives and cannot be mixed.
- Bounded motion, completion, transfer, finding, enrollment, dropping,
  consumption, shucking, initiation, earning, production, and winning
  families now own their complete frames.
- `measure_holder_compatibility` and `measure_holder_compatible` provide the
  analogous extensible relationship for noun measures and plausible holders.
- Ordinary premise and ask clauses no longer restate an exact category-owned
  positive frame. A regression test scans both collections and allowlists only
  explicit construction-dependent slot mappings. Remaining
  `verb_role_compatible` clauses are construction-local facets, negative
  exclusions, or deliberately unresolved overlapping senses such as teaching.
- The ask-side migration exposed and corrected one vocabulary omission:
  generic `money`, like `dollar`, is an earnable quantity object.

This means adding a compatible verb or noun normally extends every applicable
premise and ask through category membership; it should not require copying a
new pair of category checks into each rule.

## Current measured baseline

These are the gates run at the current runtime checkpoint:

| Gate | Current result |
| --- | --- |
| full synthetic suite | 5,358 passed |
| curated suite | 71 correct, 0 wrong |
| GSM8K DEV-train | 108 correct, 0 wrong |
| GSM8K DEV-holdout | 42 correct, 0 wrong |
| ASDiv DEV | 45 correct, 0 wrong |
| SVAMP DEV | 31 correct, 0 wrong |
| MAWPS DEV | 11 correct, 0 wrong |
| SciBench DEV | 6 correct, 0 wrong |
| DIFG DEV | 75 correct, 0 wrong |
| FOLIO DEV | 0 numeric commitments |
| COGS DEV-train / holdout | 1,771 / 1,693 exact, 0 incorrect |
| PMB train / development | 117 / 4 exact, 0 incorrect |
| lint | 0 errors, 1 known warning |

The latest protected GSM8K TEST look is look 126: 13 correct, 1 persistent
wrong, and 1,305 declined. Increment 132 made no new protected commitment.
Do not spend another protected look merely to refresh these numbers.

### Generation availability

Availability means “the authoring layer can realize the declared contract and
round-trip it through the ordinary matcher.” It does not mean that a human has
judged the resulting English or emitted fact valid.

| Project | Premise rules | Independent asks |
| --- | ---: | ---: |
| curated | 125/125 targets (+5 safety interceptors) | 104/114 |
| GSM8K | 120/120 targets (+3 safety interceptors) | 135/152 |

The safety interceptors are intentionally separate from premise generation
and review. The ten curated ask blockers are contextual
discourse-group asks, one ontology-dependent membership ask, and one embedded
uninverted form. Contextual ask generation must synthesize the required
antecedent rather than pretending the question is independently realizable.

## Designer and promotion workflow

The Designer currently provides:

- strict-positive and controlled one-slot lexical-boundary premise generation;
- independent ask generation, bounded answerable-scenario search, and
  deliberate missing-evidence scenarios;
- seeded reproduction, structural coverage objectives, compatible category
  filters, and terminal-blocker health;
- Reading-origin targeted reviews and targetless interpretation or
  missing-rule reviews;
- premise-, sentence-, and fact-attached defects with source navigation;
- allowlisted YAML editing with compile-and-rollback, followed by exact pinned
  retest and before/after comparison;
- append-only corrections, resolutions, and tombstones; and
- a Mining v2 queue with immutable manifests, isolated candidate runners,
  fingerprint-pinned human decisions, exact machine gates, and durable landing
  records.

Human reviews check the premises and facts that the authored grammar commits
to. They are not model-training labels. Hypotheses are deterministic,
trace-backed suggestions and never mutate YAML automatically.

The campaign queue currently contains four `landed` revisions and no open
revision. Old candidate and staging worktrees still exist locally; their
presence is not campaign state. Trust the append-only queue and landing ledger,
not directory names.

## Durable boundaries

- **Language knowledge is data.** Words, morphology, categories, selectional
  roles, compatibility relations, conversions, formulas, and reference facts
  live in packs.
- **Reading and answering are separate.** Premise rules emit facts; asks bind a
  normalized query to a generic consumer.
- **One fact store owns commitments.** Authoring views and benchmark adapters
  do not create a parallel inference system.
- **Ambiguity fails closed.** Missing, conflicting, incomplete, or multiply
  licensed evidence produces a decline or clarification, never a guess.
- **Generation uses the runtime, never the reverse.** Kernel, bench, lint, and
  guards do not import generation fixtures, ledgers, or review judgments.
- **Generated defects remain visible.** Generation exposes the actual authored
  boundary; it must not silently improve plausibility beyond the grammar.
- **A category relationship has one owner.** Grammar maps structural slots;
  category documents own extensible vocabulary relationships. Rule-local
  copies require a construction-level reason.
- **Reviews are append-only.** Editing, resolving, and tombstoning append new
  rows; they do not rewrite evidence.
- **Precision precedes coverage.** Every increment must retain zero new wrong
  answers and zero incorrect projected graphs across the standing gates.

## Next safe action

For another capability increment, run the M7 mining workflow on one new
inspectable GSM8K `dev-train` decline. Before publishing a candidate:

1. fold any new non-tombstoned Designer reviews that touch the intended class;
2. prefer an existing category relationship or generic mechanism over a new
   rule-local vocabulary list;
3. add invented positive, paraphrase, boundary, ambiguity, and decline tests;
4. run the complete standing gate; and
5. stop after publication for Designer human review and the exact machine
   gate.

If the immediate goal is consolidation rather than mining, continue auditing
the remaining legacy compatibility clauses. Migrate one only when the category
has one coherent complete frame; do not force overlapping facets or
construction-dependent slot mappings into a misleading hierarchy.

Useful commands:

```bash
uv run pytest -q -n 4 --dist=worksteal
uv run rulekit --project projects/curated bench --slice suite
uv run rulekit --project projects/gsm8k bench --slice dev-train --jobs 8
uv run rulekit --project projects/gsm8k bench --slice dev-holdout --jobs 8
uv run rulekit --project projects/gsm8k lint
uv run rulekit --project projects/curated campaign-queue
uv run rulekit --project projects/curated serve
```

Use the commands in [`../CLAUDE.md`](../CLAUDE.md) for the complete
cross-corpus and projection gate. A TEST-capable CLI flag is not authorization
to spend a protected look.

## Parked semantic-projection campaign

COGS/PMB semantic projection remains parked. The repaired Phase D baseline and
two subsequent DEV-only common-subject increments are retained at 100%
projected-edge precision. The known unsafe generic proper-object ditransitive
transfer was removed: direct proper objects remain themes, double-object
surfaces decline, and only the construction-specific explicit-`to` recipient
graph is retained.

Phase E is still blocked. The one permitted PMB protected standard-test
aggregate produced 1 exact and 0 incorrect but did not demonstrate the
required independent role classes. The external synthetic dataset candidate
at `/Users/louis/Development/semantic-generator` remains a separate review and
sealing concern. Do not inspect protected COGS/PMB rows, tune against that
aggregate, seal the external candidate, or build an importer without an
explicit campaign resumption.

On resumption, follow
[`semantic-projection-plan.md`](semantic-projection-plan.md) and
[`semantic-projection-ood-gate-plan.md`](semantic-projection-ood-gate-plan.md),
verify the external release and licence boundary first, and preregister the
one-way import and evaluation thresholds before evaluating it.

## Historical record

- [`mining-log.md`](mining-log.md) — shipped increments 129 onward.
- [`HANDOFF-archive-2026-07-23.md`](HANDOFF-archive-2026-07-23.md) — frozen
  Session 1–105 narrative.
- [`HANDOFF-archive-2026-07-16.md`](HANDOFF-archive-2026-07-16.md) — earlier
  arithmetic and mining narrative.
- [`negative-results.md`](negative-results.md) — measured failures and retired
  approaches.
- [`parked-physics-campaign.md`](parked-physics-campaign.md) — parked physics
  work.

Git history preserves the material pruned from this handoff. Do not append
per-review or per-increment narratives here again; promote only current state,
the next action, or a durable invariant.
