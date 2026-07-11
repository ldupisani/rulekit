# Session handoff — 2026-07-11

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State below is committed through `4bc6ed5` on `main` (github.com/ldupisani/rulekit;
check `git status`/`git log origin/main..HEAD` before assuming push parity).

## Where the project is

Everything through P5 of the original plan is DONE: kernel, YAML packs, lint
(overlap witnesses + blast radius), document re-parse loop, GSM8K harness with
firewall, visual designer (`rulekit serve`, port 8321 — busy-state, slice
targets, TEST gated behind a checkbox). The GSM8K mining campaign is in full
swing under the constitution (no lexicon in Python, no per-problem parsing,
every increment through the gates).

**Current numbers (all verified at head):**
- dev-train: 14 correct / 0 wrong (3,772 items, 100% precision)
- dev-holdout: 14 correct / 0 wrong (3,701 items)
- curated suite: 52/52 · pytest: 130 · lint: 0 errors, 1 intended warning
- TEST ledger (11 looks spent, `projects/gsm8k/snapshots/test-ledger.jsonl`):
  0/1 (0%) → 4/1 (80%) → 5/1 (83.3%) → 5/2 REVERTED → 5/1 → 5/2 bisect →
  5/1 (83.3%) → 5/1 (look #8) → 5/1 (look #9) → 5/1 (look #10) →
  **6/1 (85.7%, look #11) ← live** — a genuine COVERAGE GAIN on TEST
  (same single persistent wrong, one more correct)
- The 1 persistent TEST wrong is a stable §3a unseen shape, present since look #1.

## The mining loop (how work ships)

1. Baselines live in `projects/gsm8k/snapshots/` — the CURRENT baselines are
   `conj-train.json` / `conj-holdout.json` (identical to head behavior;
   supersede `price-*`/`pop-*`/`conv-*`/`narrow2-*`).
2. Mine with throwaway scripts in the session scratchpad (never the repo):
   bucket `solve()` decline reasons over dev-train; `rulekit stats` also works.
3. Build the tightest GENERAL mechanism (YAML rules/categories first; kernel
   only for structure). One class per increment, named at ship time.
4. Gate: `bench --slice dev-train --snapshot X.json` → `diff <baseline> X.json`
   (must be 0 BROKE / 0 DECL→WRONG) → same for dev-holdout → synthetic pytest
   (never GSM8K strings) → suite must hold 52/52.
5. TEST look per shipped increment: `bench --slice test --spend-test-look`.
   Precision must hold vs the last look (85.7%, look #11) or the
   increment REVERTS (this happened once — see docs/negative-results.md;
   the protocol works).

## Re-landing plan: COMPLETE

The rate-machinery revert is fully RESOLVED and re-landed, look by look
(docs/negative-results.md, looks #5–#9). Culprit for the original TEST
drop was accounting-by-existence (fixed: a Rate's value counts as read
only when the arithmetic log used it) — nothing to do with the
mechanisms themselves. All four original pieces are LIVE at `b8d7339`:
ask-specificity ordering, the rate-span committer, conversion spans, the
`entity` slot type (name | common noun | resolved pronoun — applied ONLY
to the two rate-span asks' `who` slot, not the ~18 other asks that still
require `type: name`), and rate × population on top of it. No more
parked pieces in `2d7b90c` — that history is fully absorbed.

## Increment 10: priced purchases (`9be1829`)

"N ITEM at/for $PRICE each" now emits a `Price` fact (learn.py) alongside
the ordinary purchase `Quantity`, instead of learn.py silently dropping
the whole clause (the old `_is_rate` distributive-"each" branch). A new
`purchase-total` fallback in `answer.py` answers "how much did X
pay/spend" by Σ qty × price over every purchase-verb quantity — gated on
the new `spend_verb` category (pay/spend only — deliberately narrower
than `lose` so an unrelated "how much did X sell" can't borrow purchase
data) and the existing `purchase` category (difg-mined, parent: acquire).
Declines whole-total (never undercounts) when any purchased item lacks a
price, OR when a `divide`-category predicate ("splits/shares the cost")
touches the same buyer — caught via a real dev-holdout wrong during
development (3 cakes at $12 each split with a brother: 36 raw vs 18
actual). `Price` follows the Rate lesson: excluded from
`guards._fact_values_by_sentence`, read only when the arithmetic log
actually used it. Shipped as NEUTRAL (0 dev coverage alone) — tested,
safe infrastructure for increment 11.

## Increment 11: conjoined purchases (`4bc6ed5`)

Closes the gap increment 10 flagged: the verb's `dobj` obligation only
ever binds the FIRST item in "A at $X each, B, and C at $Z each" — a
general, pre-existing conjunction-handling limitation. This ships a
SCOPED fix restricted to purchase-verb dobjs only (the FULL general fix —
every verb's dobj binding — is far higher blast radius and stays future
work; see the worklist below).

`_conjoined_purchase_items` (learn.py) walks the tail after the bound
first dobj, segmenting on top-level commas/conjunctions; each segment's
first counted noun is a sibling item, priced only if that SAME segment
has its own 'each' + currency noun. Gated on the existing `purchase`
category — every other verb ('contains', 'has', etc.) is untouched.

Caught and fixed during development, NOT shipped broken:
1. First pass reused item 1's own trailing price-clause tokens as a
   spurious extra sibling — fixed by discarding the first segment (it's
   the caller's item, already processed).
2. Second pass widened `_is_rate`/`_price_each_value`'s scan to stop at
   commas GLOBALLY (to stop an unpriced first item from crossing a comma
   into a later item's price). This introduced a real dev-train wrong
   (a box/bag/balloon composition, expected 480 got 12) — the widened
   boundary changed an unrelated 'contains' sentence's parse elsewhere in
   the corpus. Reverted the global change; `_price_each_value` instead
   takes an opt-in `stop_at_list_boundary` flag, passed `True` only from
   the purchase-conjunction call site. Every other verb's rate-marker
   scan is byte-for-byte unchanged from increment 10.

Gates: dev-train +1 SOLVED / 0 BROKE, dev-holdout +1 SOLVED / 0 BROKE
(both 14/0). TEST look #11: 6/1 (85.7%) — a genuine coverage GAIN, not
just NEUTRAL (same persistent wrong, one more correct).

## The next mining worklist (from the last close-miss scan)

Numbers below predate this session's work and need a fresh `rulekit
stats` pass before trusting them.

- **General conjunction/multi-dobj handling** (beyond purchase verbs) —
  increment 11 scoped the fix to `purchase`-category verbs only; the SAME
  gap exists for 'has'/'contains'/event verbs generally ("Mary has 5
  apples and 3 oranges" still drops the second conjunct). Generalizing
  is high blast radius (touches the fold's most-used path) — approach
  cautiously, gate hard, expect to catch a wrong mid-development like
  increment 11 did.
- ~500 rate/price compositions (single- and multi-item priced purchases
  now resolve; remaining blockers are price-per-item forms this session
  didn't reach — flat-price items mixed with "each"-priced ones in the
  same purchase list, and the "ITEM costs $X each" subject-price form,
  which doesn't even PARSE today — see next bullet)
- "ITEM cost(s) $X each" (item as SUBJECT, not object of buy) currently
  fails to parse at all — "Eggs cost $0.50 each" fuses into a single
  broken noun unit with no subject/verb/dobj structure. A grammar gap,
  not a fold-logic gap; needs investigation in the tokenizer/POS layer,
  not learn.py.
- ~210 "no quantity known": partitions ("Ten OF THEM are yellow"), goal/
  deficit shapes ("goal is 30 situps … make up the rest")
- ~70 fold-vs-fold conflicts: possessed-noun entity identity (Kennedy's
  house vs Benedict's house both lemma 'house' — needs attr-qualified
  entities; also blocks "coconut trees vs mango trees" noun-standard
  relations, attr-blind measure matching generally)
- 153-ish questions with embedded when/after clauses (only "If…," splits)
- noun-antecedent pronouns ("it" → the bear; needs animacy data in packs)

## Hard-won invariants (do not relearn these)

- Every new FACT KIND must decide explicitly whether existence or USE
  constitutes "read" for value accounting (the look #4–#7 lesson).
- Polarity/stateness/plurality are DATA (categories: acquire/lose ±1,
  state, produce/receive +1; lexicon `number:` field). An untagged event
  verb declines the fold — tag it in difg-mined members, never default +1.
- All state verbs (have/own/be) are ONE equivalence class for relation
  resolution blocking; relations carry the sentence's verb.
- Fractions/rest resolve strictly in sentence order (out-of-order = self-
  collision); pools = signed sum of prior-sentence facts, synth/rest excluded.
- Name merging: only single capitalized WORDS join names; merged units never do.
- Asks match by specificity (max consumed units); ask templates referencing
  unbound optional slots omit the key; only {slot.value} slots count as
  consumed by an ask.
- The one lint warning (fraction-of-remnant shadows fraction-of-pool) is
  intended subsumption documentation, not a problem.
- `check packs/difg-mined/quarantine.yaml` before admitting new vocabulary.
- The 'world' entity (bare existentials) and `measure: currency` (category
  name in ask data, resolved against facts) are pack-owned data constants.
- A widened slot TYPE (e.g. `entity` vs `name`) must be applied to the
  SPECIFIC ask/rule ids that need it, never via a blanket find-replace —
  most `who: name` slots across the ~18 other asks are intentionally
  name-only and widening them all would silently change what dozens of
  unrelated questions match (learned the hard way with `replace_all`
  during the population re-land; caught before it was gated, not after).
- rate × population only fires when the ask names the rate's holder via
  a resolvable common noun ("the bird") — it is NOT reachable through
  `type: name`-only asks, so it and the `entity` slot type ship together.
- A new derived-total consumer (e.g. purchase-total) must check for
  UNCONSUMED qualitative predicates on the same entity before committing,
  not just unaccounted NUMBERS — value-accounting only catches missing
  digits; "splits the cost with his brother" has none, so it slipped past
  every numeric guard and only a dev-holdout wrong caught it (increment 10).
- The verb→dobj binding only captures the FIRST conjunct in "buys X and
  Y" / "X, Y, and Z" for verbs outside the `purchase` category — a
  pre-existing, general conjunction-handling gap that silently drops
  every conjunct after the first from the fold entirely. Increment 11
  closed it for purchase verbs only; it is STILL OPEN for 'has',
  'contains', and event verbs generally.
- A shared clause-boundary scan (`_is_rate`/`_price_each_value`, used by
  EVERY verb's rate-marker detection) must never be widened globally to
  fix one caller's edge case — a comma-boundary fix aimed at purchase
  lists broke an unrelated 'contains 8 bags..., and ... each bag'
  sentence elsewhere in dev-train (increment 11). The fix: an opt-in
  parameter, defaulted to the old behavior, passed only by the caller
  that needs it. Any future tightening of shared scan functions needs a
  FULL dev-train/holdout diff, not just the target scenario's own tests.

## Quick commands

```
uv run pytest -q
uv run rulekit --project projects/gsm8k bench --slice suite|dev-train|dev-holdout [--snapshot F]
uv run rulekit --project projects/gsm8k diff conj-train.json <new>.json
uv run rulekit --project projects/gsm8k stats
uv run rulekit --project projects/gsm8k serve         # designer :8321
uv run rulekit --project projects/gsm8k bench --slice test --spend-test-look   # DELIBERATE
```

Auto-memory (`~/.claude/projects/-Users-louis-Development-rulekit/memory/`)
carries the same state in condensed form and is loaded automatically.
