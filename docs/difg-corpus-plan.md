# difg-domains — corpus extraction plan

Extracting difg's multi-domain reasoning corpus into a rulekit project that the
mining loop can work, the way GSM8K is worked today. Planned 2026-07-12.
Source: `~/Development/experiments/difg` (read-only).

## The finding that shapes everything

**difg's test corpus is difg's self-portrait, not a benchmark.** Of the 454
gold-bearing items, **79.3% ARE the orchestrators' own advertised
`example_queries`** — the questions difg published as demonstrations of what it
could already do. Only **36.8%** have an independent gold (a captured Claude
answer); the rest are whatever difg's own code emitted, and a gold that is "what
the predecessor returned" cannot falsify the successor. Where the two sources
overlap, **14 disagree**.

A held-out score on such a set measures nothing about unseen text — there is no
unseen text, only unseen members of a set curated for solvability. It will read
high and the height will be an artifact.

**Therefore: this project's metric is `domain coverage`, never `precision`.**
"Precision" stays a GSM8K word. If this number is ever quoted next to the GSM8K
number without that caveat, the caveat has failed.

## Decisions taken (2026-07-12)

1. **Both, in order.** Ship the coverage checklist first so domain mining can
   start; commission a genuinely independent TEST set in parallel (items difg
   never saw). The checklist number is not quoted as precision until that lands.
2. **Typed gold waits for a campaign pause.** The change touches `answer.py`,
   `bench.py`, `firewall.py` and `diff` — shared code the live GSM8K campaign
   depends on, and widening shared kernel code for one caller has broken others
   before. It does not get done mid-campaign.

**Consequence: the split waits too.** Phase 3 is a one-way door and must not be
opened until Phase 0 passes (below). So no runnable difg project exists until
the pause. Phases 1, 2 and 6 are available now and are all reversible.

## Why typed gold is a KERNEL question, not a harness one

`src/rulekit/kernel/answer.py:24-30`:

```python
kind: str  # "number" | "verdict" | "decline"
@property
def committed(self) -> bool:
    return self.kind == "number"
```

A non-numeric answer is not even *committed*, so it can never score — meaning
mining has **no signal at all** in a non-numeric domain. Only 44.5% of difg's
answers are bare numbers. Restricting to numeric answers to dodge the kernel
change would delete `physics`, `logic`, `clock_arithmetic`, `string_operation`
and most of `unit_conversion` as scorable domains — i.e. it abandons the goal.

Answer types across the 454: number 202 (44.5%), quantity+unit 134 (29.5%),
entity/text 43, money 25, set/list 20, boolean 17, percent 13.

## Inventory

Corpus is NOT where a naive look would put it. `reasoning/tests/` is 13,795
lines, but 10,656 of them are `test_reading.py` — difg's **GSM8K** reading suite,
the direct ancestor of the current campaign. **Exclude it entirely**: it holds no
domain items and is maximally contaminating for the *other* project.

| Source | Count | Gold? | Domain label? |
|---|---|---|---|
| `tests/test_orchestrators.py` → `CASES` | **454** | yes | yes |
| `store/samples/*.json` (Claude teacher captures) | 187 (**20 net-new**) | yes | no |
| `store/orchestrators/*.py` → `META["example_queries"]` | 469 (**106 gold-less**) | no | yes |
| orchestrators themselves | **102** (98 `model_free`) | — | — |

`datasets.py` / `datagen.py` generate numeric data tables, not Q/A pairs — not a
corpus source. `eval.py` is difg's own typed comparator (numeric-tolerant +
verdict + containment): a good design reference for the future `_judge`.

**Yield: 454 − 5 (`expression`: raw calculator strings) − 1 (prose/SymPy repr)
+ 20 (net-new captures) = 468 items across 96 domains.**

Gold shapes are uniform tuples in one `CASES` list — there is no assertion-shape
zoo to normalise. 8 domains have ≥10 items; 20 are singletons.

## Contamination, measured

- **Vocabulary: mild.** Only **8.4%** of questions are fully covered by rulekit's
  2,623 admitted lexicon words; median 2 unknown alpha-words per question;
  exactly **one** quarantined word (`place`) appears. `packs/difg-mined/` did NOT
  pre-absorb this corpus — the domain nouns (`kg`, `moles`, `radius`) are unseen.
- **Item selection: severe** (the 79.3% above). This is the disqualifying layer.
- **Gold provenance: moderate.** 36.8% independently corroborated; 14 conflicts.

Honesty measures, none optional: rename the metric; ship `gold_source` /
`independent_gold` columns and report TEST **sliced by provenance** (the 36.8%
independent subset is the only sub-number worth half-believing); **quarantine the
14 disagreements** rather than adjudicating (a gold two sources disagree about is
not a gold — and adjudicating means reading them, which puts them in DEV forever).

## The DEV/TEST split

- **Naive global md5%4: REJECTED.** Puts 4 domains (`compound_interest`,
  `profit_margin`, `replace_text`, `weighted_average`) *entirely* in TEST — the
  TEST number would measure domain transfer, not coverage.
- **Per-file / per-domain: REJECTED.** Maximal version of the same disease.
- **CHOSEN: per-domain stratified, deterministic, salted, ~25% TEST.** Within
  each orchestrator, sort by `md5("difg-test@1" + question)`, take the first
  `max(1, round(0.25·n))` into TEST; domains with <2 items go entirely to DEV.
  Result: TEST 114 / DEV 340, **0 domains only-in-TEST**, 96/96 domains present
  in DEV. DEV then splits by the unchanged `firewall.holdout_bucket`.

**The salt is load-bearing**: `holdout_bucket` is unsalted `md5(question)%2`.
Reuse the same hash for both cuts and dev-holdout becomes a biased subsample.

**Read-leak ledger.** The planning survey displayed 51 item bodies, 11 of which
would land in TEST. Those are DEV forever. The extraction script must carry an
explicit `read_leak.txt` and force those ids to DEV regardless of hash — which
only ever shrinks TEST (114 → ~103), never grows it, so it cannot launder a bad
item into TEST. An auditable leak ledger beats an unverifiable purity claim.

## Target shape

```
projects/difg-domains/
  project.yaml     packs: [core-english, arithmetic, difg-mined]   # NO new pack yet
                   gold: typed        # NEW key; absent => today's float path, byte-identical for GSM8K
  suite.yaml       ~30 synthetic items, one per answer TYPE — never a difg string
  data/            gitignored          snapshots/  gitignored
```

Parquet columns: `question, answer, gold_type, gold_value, unit, domain,
gold_source, independent_gold, item_id`.

**No new pack up front.** Domain vocabulary and formulas belong in future
`packs/units/`, `packs/physics/` … mined increment by increment through the gate.
An empty pack invites bulk-loading difg's skill tables into it — the
`vocab_singles` sin at pack scale. Let the mining loop earn each pack.

## Phases (riskiest assumption disproved first)

- **Phase 0 — DISPROVE TYPED GOLD.** *(deferred to a campaign pause, per decision 2)*
  Prototype typed gold + per-type `_judge`, rebuild a GSM8K `dev-train` snapshot,
  **byte-compare against an existing snapshot**. Identical = pass. One byte moves
  = the change is not neutral; abandon it and fall back to numeric-only (24
  domains) with eyes open. Costs an afternoon; gates everything.
- **Phase 1 — Extraction dry-run, prints only.** Reproduce every count above.
  Writes nothing. *(available now)*
- **Phase 2 — Honesty scaffolding.** Provenance columns, 14-conflict quarantine,
  `read_leak.txt`, the docs note fixing the metric's name. Must precede the split.
  *(available now)*
- **Phase 3 — DRAW THE SPLIT. ⚠️ POINT OF NO RETURN.** Writes `difg_test.parquet`.
  Nothing afterwards can widen TEST; a bug found later can only shrink it. **Do
  not enter until Phase 0 passes and Phase 2 exists.**
- **Phase 4 — Project + synthetic suite + baseline.** The baseline will be a sea
  of `declined`. That is the correct and honest starting number.
- **Phase 5 — First mining increment: `geometry`** (12 items, all bare `number`).
  Needs no typed-gold machinery, so it validates the mining loop independently of
  Phase 0. If Phase 0 fails, this is still the project you can have.
- **Phase 6 — The independent TEST set.** *(starts in parallel, per decision 1)*
  Until it exists, the difg-derived TEST half is a **regression guard wearing a
  benchmark's clothes**.

## Mining-readiness gaps (beyond typed gold)

1. `Answer.committed == (kind == "number")` — **blocking** for every non-numeric
   domain: no commit, no score, no mining signal.
2. Ask-shape machinery is arithmetic-shaped. difg asks "what is the *area* of…",
   "convert X to Y", "is 2024 a leap year?" — formula-selection and conversion
   asks, not quantity-accumulation asks. New ask-shape families needed; each is a
   legitimate general class, nameable at ship time (constitution §2).
3. Goal-mode SOLVED gate assumes a numeric target; needs the typed comparator.
4. `stats` worklists need a `--domain` facet or they're unreadable across 96.
5. **The constitution binds this corpus identically, and the temptation is far
   worse here:** difg has 66 skill modules of formulas and 85 unit strings.
   Porting `skills/units.py` into Python is the fastest route to a great-looking
   number and a dead engine. Conversions → `packs/*/conversions.yaml` (exists);
   formulas → synthesizers with category gates. **No per-domain Python branch.**

## Open, still unanswered

- 25% TEST gives ~1.2 items/domain — almost no per-domain resolution. 40% (~180)
  would give a coarser but real per-domain read, at the cost of a thinner mining
  pool. Leaning 25% *only* because Phase 6 is meant to supply the real TEST set.
- The 5 `expression` calculator-string cases: excluded as not-natural-language;
  trivially includable.
