# GSM8K Mining v2 — generated evidence and human promotion review

**Status:** active
**Started:** 2026-08-08
**Baseline commit:** `1dd2159`

## Objective

Resume GSM8K-style capability mining without returning to benchmark-shaped
one-off parsing. Each increment must be one complete, useful language class:
premise reading, exact facts, inference, ask binding, answer contract,
generation coverage, negative neighbours, and safe decline or clarification.

Human review is a promotion gate inside the Designer. Reviews check whether
the declared premises and emitted facts are justified; they are debugging
evidence, not training labels and not benchmark gold.

## Invariants

1. The existing DEV/TEST firewall, constitution, and precision-first rule
   remain unchanged. No phase in this plan authorizes a protected look.
2. A mining increment buys its own enabling machinery: no isolated premise,
   fact, consumer, or ask enabler lands on a promise of later coverage.
3. Coverage mining is example-led and advances one inspectable DEV-train item
   at a time. One item is enough to begin, but never enough to justify a
   one-off mechanism: the candidate must name a general construction and
   prove it with invented positive, paraphrase, boundary, and decline
   specimens before the original item is used as an acceptance check.
4. Strict generation, lexical-boundary probes, reader-only compatibility, and
   fact-free safety interception remain distinct evidence classes.
5. Candidate approval is pinned to an immutable commit and registry
   fingerprint. Any behaviour-changing revision makes prior approval stale.
6. Candidate worktrees never write the durable human-review ledger. The
   central Designer owns append-only review writes.
7. The existing Designer server stays available. Candidate code will execute
   in an isolated on-demand runner rather than being imported into that
   process.
8. A user may explicitly select a product-led manual class below the automatic
   yield threshold. Its manifest must say `mode: product`, claim no corpus
   pool or solved items, and state the product rationale. It receives every
   ordinary evidence and promotion gate; product selection never disguises a
   zero-yield automatic candidate.

## Candidate contract

Every brief and review manifest must name:

- the natural-language construction class and intended ordinary use;
- its premise rules and grammatical restrictions;
- exact fact types, identities, ownership, scope, time, and provenance;
- the inference or saturation mechanism;
- the ask family and complete query bindings;
- the answer kind and all-or-nothing behaviour;
- ambiguity, missing-evidence, and negative-neighbour outcomes;
- strict generated specimens and controlled boundary probes; and
- the DEV items on which all of those layers are jointly sufficient.

## Delivery phases

### M0 — freeze the preceding campaign — complete

Commit `1dd2159` records the complete generation, review, logic, ownership,
preposition, temporal, group-answer, and absolute-year age state. Its final
gate was 4,672 tests with zero new wrong or incorrect standing-DEV outcomes.

### M1 — durable web review queue — complete

- Add immutable, project-local candidate manifests under a fixed path.
- Pin each manifest to candidate id, commit, and registry fingerprint.
- Store central human decisions in a separate append-only JSONL ledger.
- Require every specimen to be reviewed valid before candidate approval.
- Expose awaiting, approved, changes-requested, unclear, and stale evidence in
  the existing Designer.

**Exit:** a synthetic manifest can be published, reviewed in the Designer,
reloaded from disk, and mechanically rejected if its commit/fingerprint or
specimen set is stale or incomplete.

Implemented in the first campaign increment. Candidate/commit manifests are
immutable and idempotent, promotion decisions are append-only, approval
requires a complete all-valid specimen set, and later revisions surface the
preserved earlier decision as stale. The Designer exposes the queue and only
offers current-runtime Reading/YAML controls when fingerprints agree. The gate
is green at 4,677 tests; curated and both GSM8K DEV partitions are neutral,
every standing answer corpus remains at zero wrong commitments, COGS/PMB
remain at zero incorrect graphs, and no protected look was spent.

### M2 — isolated candidate runner — complete

- Launch at most one selected candidate worktree server on demand.
- Proxy trace, source navigation, explicit YAML save, and pinned retest through
  the central Designer.
- Allowlist candidate roots and never give the candidate process the durable
  review-ledger path.
- Stop or replace only the candidate runner; never stop the ordinary server.

**Exit:** the central Designer resolves an exact registered candidate
worktree, commit, clean state, project path, and worktree-owned virtual
environment before starting one loopback-only child process. It validates the
candidate registry fingerprint and rejects any editable document or source
outside that worktree. The web application can inspect Reading, open and save
allowlisted YAML, and replay a pinned generated specimen through that child;
benchmark, impact, baseline, TEST, and review-ledger routes are not proxied.
An invalid replacement does not evict a healthy runner, shutdown cleans up
the owned child, and a live edit blocks approval until the change is committed,
gated, and published as a new manifest.

Implemented in the second campaign increment. The exact parallel synthetic
gate is green at 4,689 tests. Curated remains 71/71; GSM8K remains 107/0 on
DEV-train and 43/0 on DEV-holdout; ASDiv, SVAMP, MAWPS, SciBench, and FOLIO
retain zero wrong commitments; lint is 0 errors and 0 warnings. No protected
look was spent.

### M3 — G7 ask and scenario generation — complete

- Generate and round-trip an ask surface independently.
- Generate the smallest answerable premise set for one ask contract.
- Generate one deliberate missing/conflicting-evidence scenario.
- Keep premise, ask, answerable-scenario, and decline coverage separate.
- Validate number, series, witness, verdict, clarification, and decline shapes.

**Exit:** the Designer enumerates every loaded ask separately from premise
availability, exposes exact blockers, and can deterministically round-trip one
supported question through the ordinary ask matcher. It can leave that ask
without evidence or search supported generated premise rules for the smallest
solver-committed set found by the bounded search. Emit-template inversion only proposes bindings; the
ordinary solver is the sole answer oracle, removal proves minimality, and no
benchmark text, gold answer, or consumer-specific sentence template enters
the search. The current curated project has 93/104 independently realizable
ask surfaces; discourse-group and arbitrary-span asks remain honestly blocked
until contextual generation exists. Number, series, witness, verdict,
clarification, and decline projections are covered by synthetic tests.

Implemented in the third campaign increment. The exact parallel synthetic
gate is green at 4,702 tests. Curated remains 71/71; GSM8K remains 107/0 on
DEV-train and 43/0 on DEV-holdout; ASDiv, SVAMP, MAWPS, SciBench, and FOLIO
retain zero wrong commitments; COGS and PMB retain zero incorrect graph
projections. No protected TEST/generalization look was spent.

### M4 — machine-readable promotion gate — complete

- Replay every live candidate specimen and relevant non-tombstoned review.
- Diff matches, surviving facts, collisions, deficiencies, ask bindings,
  answer shape, proof, and clarification—not only final numeric answers.
- Run the exact parallel full suite and every standing answer/projection DEV
  gate from baseline-derived snapshots; remove hard-coded suite counts.
- Serialize expensive full gates while allowing implementation work to remain
  parallel.

Implemented in the fourth campaign increment. Candidate specimens now carry a
canonical trace contract covering ordinary matches and bindings, surviving
facts, collisions, deficiencies, ask bindings, answer value/shape/commitment,
proof, and clarification. The gate replays every specimen and every explicit
or target-rule-relevant live review against the exact isolated candidate.
Machine results append centrally to `generation/campaign/gates.jsonl`; a later
commit or fingerprint cannot reuse them, and approval is unavailable until the
exact revision has a passing result.

The expensive part is serialized by the Designer's benchmark lock. It derives
fresh baseline and candidate snapshots for curated, both GSM8K DEV slices, all
inspectable answer cross-corpora, both COGS DEV slices, and PMB
train/development. It also runs the exact parallel full suite, lint, FOLIO's
zero-numeric-commitment assertion, and content-blind before/after hashes of
protected ledgers and TEST/generalization files. Suite size and every other
cardinality come from emitted snapshots; workflow code contains no historical
count. The candidate runtime is held stable for the run and both checkouts are
revalidated afterward.

The exact parallel synthetic gate is green at 4,714 tests. Curated remains
71/71; GSM8K remains 107/0 on DEV-train and 43/0 on DEV-holdout; ASDiv, SVAMP,
MAWPS, SciBench, DIFG, and FOLIO retain zero wrong commitments; COGS and PMB
retain zero incorrect graph projections. Lint has zero errors. No protected
TEST/generalization look was spent.

### M5 — GSM8K-specific mining workflow — complete

- Create a new GSM8K scout; do not reuse the DIFG-domain scout.
- Repair the Codex workflow/agent source-of-truth paths and remove duplicated
  protocol drift.
- Extend candidate and gate schemas with the complete contract, generation,
  review, trace, cross-corpus, and projection evidence.
- Constitution-review, human-review, and integrate candidates sequentially
  after parallel implementation.

Implemented in the fifth campaign increment. `.agents/protocols/` is now the
single source of truth for scout, implementer, constitution reviewer,
integrator, and standing-gate behavior. Codex TOML and Claude Markdown agents
are thin launch adapters to those files. The obsolete DIFG scout body and the
JavaScript workflow that embedded stale corpus policy and historical suite
counts were removed. The Codex-native skill detects session-cached stale roles
and falls back to a default subagent reading the canonical file.

Candidate manifests advance to `rulekit/campaign-review@2`. They carry the
auditable class/yield claim, premise and ask mechanisms, bounded vocabulary and
quarantine/collision evidence, generated premise/ask targets, required
specimen kinds, expected implementation scope, synthetic-only test modules,
class justification, passing constitution verdict, explicit live-review ids,
and each specimen's canonical trace. Standing results also preserve baseline
and candidate fingerprints plus an opaque digest of item identities for both
answer and projection corpora. `campaign-trace`, `campaign-publish`, and
`campaign-queue`, and `campaign-land` provide fixed CLI seams for candidate
evidence capture, central publication, exact resumable state, and durable
staging completion.

The workflow now pauses after parallel implementation and read-only
constitution review. Humans inspect the published manifests and run the exact
machine gate in the existing Designer. A separate `--integrate-approved`
resume admits only exact human-approved and machine-passed revisions, then
integrates them one at a time with a complete re-gate. It still stops on the
staging branch before TEST and never merges or pushes main.

The exact parallel synthetic gate is green at 4,720 tests; curated remains
71/71 and lint has zero errors. The standing runtime matrix is unchanged from
M4 because M5 changes only Designer/orchestration/schema surfaces. No protected
TEST/generalization look was spent.

### M6 — smoke and first batch — complete

- Run one no-op smoke candidate through every stage without touching TEST.
  The no-op candidate passed human and exact machine review and landed as
  increment 129 at staging commit `13a1f65`. The smoke exposed one missing
  lifecycle edge: approval remained selectable after integration. Exact
  append-only landing evidence now closes that edge and makes repeat
  integration mechanically ineligible.
- Run an initial batch of two complete candidates.
  The first live scout attempted this at `59087b4` and dispatched no
  implementers. It measured 1,401 fully-read DEV-train declines, then found
  zero qualifying final-blocker wins in the two strongest semantic classes:
  question-scoped leading arithmetic conditions (264-row probe) and
  same-holder totals over explicit periods/occurrences (five-item fact walk).
  Thirty-six leading/postposed aggregate-marker rewrites also produced zero
  complete wins. This is a measured stop, not permission to weaken the ≥3
  threshold. Resume with a user-chosen product-led manual class, or re-scout
  only after a named missing premise/ask blocker has changed.
  A second scout re-ran that test at `c65fd53` after the product-led temporal
  event-total increment and review batch 34 had landed. The baseline remained
  107 correct / 0 wrong with 1,401 fully-read declines. It found 56 declines
  carrying at least one timed quantity, but only three also carried an
  anaphoric relation; those three require different missing premise and ask
  mechanisms, so they are not one complete class. The best unrelated walks
  each yielded only one complete win. No candidate cleared the automatic
  three-final-blocker bar, so no implementer was dispatched.
- Spend protected GSM8K TEST looks manually from the main checkout, one per
  approved vertical increment, only after all preceding gates pass.

### M7 — example-led vertical mining — active

The class-first scout repeatedly stopped because no three inspected declines
shared one final blocker, while individual end-to-end examples continued to
produce useful general grammar, inference, ask, and vocabulary improvements.
The user therefore selected an item-led loop for the next campaign stage.

For each increment:

1. select one currently declining item from inspectable `dev-train` only;
2. record its stable item id and a structural paraphrase, never its prose;
3. create invented analogues covering the complete premise-to-answer path;
4. extend general grammar and bounded lexicon entries YAML-first;
5. pass the synthetic analogues and negative neighbours;
6. only then load the original item locally by id and require it to answer
   correctly;
7. run the exact standing gate, including opaque `dev-holdout` and every
   cross-corpus/projection safety slice;
8. publish the ordinary immutable manifest for Designer review; and
9. periodically consolidate overlapping rules and categories after a small
   run of landed items.

The original corpus sentence is never copied into tests, manifests, briefs,
logs, or documentation. Its post-synthetic acceptance result is carried by
the ordinary DEV snapshot/diff and opaque item identity evidence. Frequency
remains useful for prioritisation, but it is no longer a threshold that blocks
an otherwise useful general vertical increment.

## Standing gate

Before promotion, every candidate must retain:

- zero `BROKE` and zero `DECL→WRONG` on GSM8K DEV-train/holdout and the
  inspectable answer-level cross-corpora;
- zero FOLIO numeric commitments;
- zero incorrect projected graphs on COGS and PMB when shared code or packs
  are affected;
- a green `pytest -q -n 4 --dist=worksteal` full suite;
- curated correctness with no fixed historical count embedded in workflow
  code;
- zero lint errors; and
- unchanged protected ledgers and slices.
