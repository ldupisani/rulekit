# Session handoff — 2026-07-11

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State below is committed through `ea47e3e` on `main` (github.com/ldupisani/rulekit;
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
- curated suite: 52/52 · pytest: 161 · lint: 0 errors, 1 intended warning
- TEST ledger (16 looks spent, `projects/gsm8k/snapshots/test-ledger.jsonl`):
  0/1 (0%) → 4/1 (80%) → 5/1 (83.3%) → 5/2 REVERTED → 5/1 → 5/2 bisect →
  5/1 (83.3%) → 5/1 (look #8) → 5/1 (look #9) → 5/1 (look #10) →
  6/1 (85.7%, look #11 — a genuine COVERAGE GAIN) → 6/1 (#12) → 6/1 (#13) →
  6/1 (#14) → 6/1 (#15) → **6/1 (85.7%, look #16) ← live** — #12–#13 the
  first /mine batch, #14 the modal split, #15–#16 the second /mine batch;
  precision held every time
- The looks #12–#13 walk was the first spent from a /mine staging branch:
  fast-forward main to each increment's commit, one look each, from the
  main checkout (the ledger lives in its gitignored snapshots dir).
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

Batch alternative: `/mine [count]` (added 2026-07-11) runs steps 2–4 as a
multi-agent pipeline — scout → parallel Sonnet juniors in isolated worktrees →
constitution review → sequential landing onto `mining/batch-<date>` with a
full re-gate per increment. It never touches TEST or main: step 5 stays
manual, one look per landed increment walking the staging commits in order;
fast-forward main past survivors only. See `.claude/skills/mine/SKILL.md`.

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

## Increment 12: trailing conditional-clause questions (`8b454cb`)

Closes the trailing half of the leading/trailing "if"-clause split gap
traced at the end of the previous session. `_split_leading_clause`
(engine.py) already handled "If X, question?"; questions phrased the
other way round — "<wh-question>, if X has N?" — never had their
trailing clause promoted to a premise, so its number bound as a
spurious `dobj` on the wh-verb instead of becoming a fact (traced
example: "How many more marbles does Anna have than Carl, if Carl has
20?" declined "missing a total" while the logically identical
leading-clause phrasing solved).

`_split_trailing_clause` (engine.py, mirrors `_split_leading_clause`)
splits the question sentence at the LAST top-level comma whose
following text starts with the conditional marker "if" (structural
skeleton, not lexicon — the leading form already keys on the same
literal), strips the trailing "?", and promotes the clause to a
premise sentence ahead of the wh-part — but ONLY when the clause
contains a digit, so bare appositives and "in total, ..." tails are
never mis-promoted to a premise. Runs only when the leading-form split
finds nothing first, so existing leading-if behavior is byte-for-byte
unchanged. Pure sentence-splitting before any grammar/obligation
processing; no word list entered Python.

Verified end-to-end: "Anna has 4 times as many marbles as Carl. How
many more marbles does Anna have than Carl, if Carl has 20 marbles?"
now splits and solves (60). The originally-traced HANDOFF item
(Trey/Kris/Kristen) still declines post-fix — its trailing clause
omits the measure noun ("if Kristen has 12", no "turtles"), a separate
noun-ellipsis gap, out of scope here.

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 0 /
BROKE 0 / DECL→WRONG 0 (NEUTRAL, 14/0 unchanged), dev-holdout diff
identical (NEUTRAL, 14/0 unchanged), pytest 135 passed (was 130 + 5 new
synthetic in `tests/test_mining_increment_12.py`), suite 52/52, lint 0
errors / 1 known-good warning. Shipped NEUTRAL on dev (no dev-train/
dev-holdout item happens to use this exact trailing form) — the
targeted synthetic tests are the coverage evidence; a dev/TEST item
using this phrasing would show as a future SOLVED.
TEST look #12: 6/1 (85.7%) — precision HELD vs look #11, increment kept.

## Increment 13: chained rates (rate x rate spans) (`75f8ec4`)

Extends the rate-span consumer (`kernel/answer.py`, `consumer ==
"rate-span"`) for the observed 2-rate chained case only: pages/hour x
hours/day x days. When the asked span's unit does not match the
committing rate's `per` unit and no static `reg.conversions` entry
applies, a SECOND Rate fact for the same entity is checked — if it
UNIQUELY bridges the units (its measure equals the first rate's `per`,
its `per` equals the span's unit), its value multiplies through instead
of a generic physical conversion. A text-stated bridge deliberately
outranks the generic conversions table for the same units (a day is 24
hours in general, but the text may state the entity only runs some of
them) — this is what keeps "pages/hour x hours/day" from silently
picking the wrong factor via the pack's day->hour=24 conversion. Any
case without a unique bridge (zero or ambiguous — e.g. two candidate
bridge rates for the same entity) falls through byte-for-byte to the
untouched single-rate path, so existing single-rate and rate x
population behavior is unchanged.

Motivated by the "Rate chaining (14 '0 rates known' items)" worklist
bullet below. Manual inspection during implementation (dev-train only)
found none of those 14 items are actually a 2-rate chain in this exact
shape — most are unrelated decline reasons under similar text
(population growth, doubling, percentage raises), and the one item
structurally closest ("Tom reads 10 hours over 5 days. He can read 50
pages per hour...") is blocked by a separate modal-verb subject-binding
bug ("He can read" binds subject to 'can', not 'he'/'Tom'), out of scope
here and left on the worklist. The mechanism is implemented and gated as
a general class per the brief (kernel-structural, no new vocabulary, no
new ask shapes — the existing rate-span asks in
`packs/arithmetic/rules/core.yaml:490,508` already match); it is expected
to fire on real chained-rate-span text once encountered, and the
synthetic tests are the coverage evidence in the meantime.

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 0 /
BROKE 0 / DECL→WRONG 0 (NEUTRAL, 14/0 unchanged), dev-holdout diff
identical (NEUTRAL, 14/0 unchanged), pytest 141 passed (was 135 + 6 new
synthetic in `tests/test_mining_increment_13.py`), suite 52/52, lint 0
errors / 1 known-good warning. Shipped NEUTRAL on dev — no dev-train/
dev-holdout item happens to hit this exact chained-rate shape; the
targeted synthetic tests (including the ambiguous-bridge decline case
and the stated-bridge-overrides-generic-conversion case) are the
coverage evidence.
TEST look #13: 6/1 (85.7%) — precision HELD vs look #12, increment kept.

## Increment 14: modal-verb subject binding (`0eeaa76`)

"He can read 50 pages an hour" bound `read`.subject to 'can': coverage
arbitration preferred noun-'can' because the auxiliary reading left the
unit orphaned, and adjacency then made it the unique subject candidate.
Three coordinated structural pieces (no word list entered Python):

1. **`modal` sense split from `auxiliary`** (packs change: the 8
   difg-mined modals can/could/will/would/should/may/might/must; do/does/
   did stay `auxiliary` in core-english). Modals carry meaning: the
   pattern layer's `auxiliary` token no longer matches them, so factual
   ask shapes can't answer capacity questions — caught live by the dev
   gate as a DECL→WRONG ("How many models CAN she buy now?" answered by
   summing a hypothetical 'buy 30' event; expected 27 got 30).
2. **Disconnected-unit scoring** (`obligations._coverage_score`): orphan
   counting generalized to units with no MET obligation that are nobody's
   binding target; auxiliary/modal function words exempt (they are
   licensed by the verb complex / ask cues, not competing content words).
3. **Article licensing** (`obligations._article_licenses_noun`): an
   article immediately left (crossing only adjectives) rules out the
   auxiliary/modal sense — "A can costs $3" stays a nominal.

Gates: dev-train diff NEUTRAL 0/0/0 (14/0), dev-holdout diff NEUTRAL
0/0/0 (14/0), pytest 146 (5 new synthetic in
`tests/test_mining_increment_14.py`), suite 52/52, lint 0 errors.
Modal-stated rates now solve end to end ("Machines can produce 5 toys an
hour. How many toys do machines produce in 2 hours?" → 10).
TEST look #14: 6/1 (85.7%) — precision HELD vs look #13, increment kept.

## Increment 15: subject-priced items (`592e8f3`)

"ITEM cost(s) $X each" — the price stated with the ITEM as grammatical
SUBJECT, not the object of `buy` — used to fail to parse at all: 'cost'
had only a noun sense (`packs/difg-mined/lexicon/a-f.yaml`), so "Eggs
cost 2 dollars each" fused into a single broken compound noun with no
subject/verb/dobj structure whatsoever. Fix, YAML-first:

1. **`cost`/`costs` gain a verb sense**, gated by a new `price_verb`
   category (`packs/difg-mined/categories/semantic.yaml`, parent `verb`,
   no polarity — a pure emission/consumer gate mirroring increment 10's
   `spend_verb`/`purchase`). Noun uses ("the cost", "splits the cost")
   keep winning arbitration via the existing increment-14 article-
   licensing rule, unwidened.
2. **`learn.py`** emits a Price fact keyed on the SUBJECT noun's lemma
   when a `price_verb`'s dobj is a currency-valued count noun followed by
   the existing distributive-'each' structure, reusing `_is_rate`/
   `_rate_unit` from increment 10 UNWIDENED (`_rate_unit` must be `None`,
   else it's a "per NOUN" rate marker — different semantics, left alone).
   A `price_verb` with a currency dobj always skips the generic Quantity
   fallback: "X costs $Y" is never a bare holding, priced or not.
3. **No `answer.py` changes** — the increment-10 purchase-total consumer
   already matches Price facts to purchase quantities by item noun
   regardless of which sentence shape produced the fact, and its
   use-gated value-accounting check already covers this new emission site
   generically.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (14/0 unchanged), pytest
155 passed (was 146 + 9 new in `tests/test_mining_increment_15.py`), suite
52/52, lint 0 errors / 1 known-good warning. Shipped NEUTRAL on dev — no
dev-train/dev-holdout item happens to hit this exact subject-priced shape
with a companion purchase sentence linking the same item noun; the
targeted synthetic tests are the coverage evidence in the meantime.
TEST look #15: 6/1 (85.7%) — precision HELD vs look #14, increment kept.

## Increment 16: partitioned collections (`ea47e3e`)

"N of them are ADJ" premises ("4 of them are red") + adjective-qualified
count asks ("How many marbles are red?" / "...are not red?") previously
folded no usable fact and matched no ask shape at all — the two halves of
the ~164 "no quantity known" decline bucket HANDOFF attributed to
partitions and goal shapes. Fix, YAML-first:

1. **A new `PartitionQuantity` fact** (`packs/arithmetic/rules/core.yaml`,
   `model.py`) captures "N of them are ADJ" as a stated subset of a prior
   collection. The plural pronoun starts as a raw placeholder ('them'); a
   new `synth/partition-of-collection` plugin (`saturate.py`) resolves it
   against the unique prior Quantity measure in play — mirroring the
   unique-pool-in-play principle `fraction-of-pronoun` already uses, never
   document-level pronoun binding (which deliberately excludes plural
   pronouns; decline on ambiguous collection).
2. **A new "adjective" slot type** (`schemas.py`, `patterns.py`,
   `guards.py`) backs two new ask shapes: "how many NOUN are ADJ" (direct
   subset lookup) and "how many NOUN are not ADJ" (exact complement).
3. **`answer.py`** gains a `partition-complement` consumer: answers the
   named subset directly, or its EXACT complement (total minus that one
   named subset — never an exhaustive-enumeration assumption over other,
   unstated subsets) computed only when the collection's total resolves to
   a single holder; declines on an ambiguous total (mirrors the
   increment-10 whole-total-decline discipline).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (14/0 unchanged), pytest
161 passed (was 155 + 6 new, now `tests/test_mining_increment_16.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool). Shipped NEUTRAL on dev — no dev-train/dev-holdout item
happens to hit this exact "N of them are ADJ" + adjective-count-ask
pairing; the mechanism is exercised and verified via the synthetic suite
(direct lookup, exact complement, ambiguous-collection decline,
ambiguous-total decline) and the frequency estimate (31 dev-train items
matching the premise shape) is the coverage evidence in the meantime.
Scoped to the brief's literal ADJ predicate — "N of them are NOUN" (a
membership-style partition, the dominant real-world phrasing) is a
natural next candidate, not folded in here.
TEST look #16: 6/1 (85.7%) — precision HELD vs look #15, increment kept.

## Increment 17: membership partitions (`060c314`)

"N of them are NOUN" premises ("8 of them are dogs") — the dominant
real-world phrasing of the partition class increment 16 scoped away
("membership-style partition ... a natural next candidate, not folded in
here"). Extends increment 16's machinery to a noun predicate, YAML-first:

1. **A membership-kind partition** (`packs/arithmetic/rules/core.yaml`)
   matches "N of them are NOUN" where the subset label is a plural common
   noun rather than an adjective — reusing the same `PartitionQuantity`
   fact and the same `synth/partition-of-collection` plugin (`saturate.py`)
   to resolve 'them' against the unique prior collection, unchanged
   (same ambiguous-collection decline discipline).
2. **A companion synth step** (`saturate.py`): once the collection
   resolves, a membership-kind partition ALSO synthesizes a Quantity for
   the named subset noun — but only when the resolved collection's measure
   has exactly one holding entity, so an ambiguous holder (two entities
   each holding a measure of the same collection noun) declines rather
   than guessing which one the subset attaches to. This lets the EXISTING
   general entity-less "how many NOUN are there" ask answer it directly,
   with no bespoke consumer (`answer.py` untouched for this increment).
3. The adjective form from increment 16 is unaffected — the two pattern
   rules gate on mutually exclusive word senses (adjective vs. plural
   common noun) and never double-fire on the same text.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (14/0 unchanged), pytest
167 passed (was 161 + 6 new, now `tests/test_mining_increment_17.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, same as increment 16). Shipped NEUTRAL on dev, same
situation as increment 16: no dev-train/dev-holdout item happens to hit
this exact "N of them are NOUN" + entity-less-ask pairing on this slice;
the mechanism is exercised and verified via the synthetic suite (direct
lookup, named-holder resolution, no-partition-fact decline, ambiguous-
collection decline, ambiguous-holder decline, adjective-form
non-interference) and the frequency estimate (29 dev-train / 31
dev-holdout items matching the premise shape) is the coverage evidence
in the meantime.
TEST look: pending — spent manually.

## Increment 18: flat-priced purchase items (`2545a7f`)

"a hat for $10" mixed with "each"-priced items in the same purchase list
("Tom buys 3 shirts at 5 dollars each and a hat for 10 dollars"). The
purchase-total consumer already sums qty × price over every purchase-verb
Quantity that has a matching Price; the gap was that a SINGULAR purchased
item (no explicit count, or an explicit count of exactly 1) stated with a
flat 'for $N'/'at $N' total and no distributive 'each' never got a Price
fact at all. Two general causes, both fixed in `learn.py` only, gated on
the existing purchase category:

1. A shared clause-boundary scan (`_is_rate`'s DISTRIBUTIVE quantifier
   lookahead) let a LATER conjunct's 'each' leak backward across a
   comma/conjunction and misclassify an EARLIER flat-priced item as a
   rate, aborting its whole fact extraction. `_is_rate` and
   `_price_each_value` gained an opt-in `stop_at_list_boundary` flag —
   off by default, set only by the purchase-verb call site (increment 11
   invariant: shared clause-boundary/rate-marker scans are never widened
   globally).
2. `_conjoined_purchase_items`' item-picker preferred the currency noun
   over the purchased item itself when the item carried no explicit
   digit ("a hat for 10 dollars" picked 'dollars'). A new
   `_flat_purchase_price` helper resolves a flat total via the 'for'/'at'
   preposition's own resolved ANCHOR obligation (structural binding, not
   position) — a beneficiary/duration/exchange 'for' that anchors
   elsewhere, or whose object isn't a currency noun, returns None and the
   item declines exactly as before. Only fires at quantity exactly 1
   (explicit '1 hat' or implicit 'a hat') — qty > 1 with a flat 'for $N'
   stays genuinely ambiguous (total vs. each) and unbuilt, matching the
   class named at ship time. `answer.py` untouched (increment 15
   precedent: Price stays excluded from `_fact_values_by_sentence`, read
   only on arithmetic-log use).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (14/0 unchanged), pytest
175 passed (was 167 + 8 new, now `tests/test_mining_increment_18.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, same as increments 16-17). Shipped NEUTRAL on dev, same
situation as increments 16-17: no dev-train/dev-holdout item happens to
hit this exact flat-price/each-price mixed-list pairing on this slice;
the mechanism is exercised and verified via the synthetic suite (flat
item first, flat item second, qty>1 flat-total decline-safety,
beneficiary/duration 'for'-PP decline-safety, non-currency 'for'-object
decline-safety) and the frequency estimate (101 dev-train / 108
dev-holdout items matching the premise shape) is the coverage evidence in
the meantime.
TEST look: pending — spent manually.

## Increment 19: capacity asks (budget / unit price) (`<pending>`)

"How many X can/could/... WHO buy/purchase/afford (with $B)?" — a genuinely
NEW ask shape and a new committer (§3a unseen-structure risk family), kept
narrow via structural gates rather than surface cues:

1. A new `modal` slot type (`schemas.py` SLOT_TYPES, `patterns.py`
   `_slot_ok`) keyed on the `modal` sense increment 14 split from
   `auxiliary` — existing factual asks are auxiliary-gated and structurally
   cannot match a modal token, so `ask/how-many-capacity` (`core.yaml`) is
   the first ask able to claim this form. Zero ordering/overlap risk with
   the ~18 existing asks: they simply never see a modal.
2. `ask/how-many-capacity` matches "how many ITEM MODAL WHO VERB (with
   BUDGET)?" (WHO: `type: entity` — name | common noun | resolved pronoun,
   scoped to this ask id only). The optional "with $B" tail is the primary
   budget source; `{budget.value}` in `resolves` marks it
   pattern_consumed for the value-accounting guard, matching the rate-span
   asks' `{span.value}` precedent.
3. A new `capacity` consumer (`answer.py`) commits ONLY when: exactly one
   Price fact exists for the asked item; a UNIQUE budget resolves (the
   ask's own "with $B", or absent that, the entity's single stated money
   holding); and no OTHER priced item is entangled with the same entity (a
   shared budget across several purchases needs subtraction this mechanism
   does not attempt — declines rather than risks a wrong; caught in
   development against a real dev-train item shaped like a pens-and-pencils
   shared-budget problem). Floor semantics use `round(budget/price, 6) //
   1` rather than raw `//` — plain floordiv is a float-precision trap
   (`1.0 // 0.1 == 9.0` in raw IEEE division, not 10); the synthetic suite
   has a dedicated regression test for this (0.3 / 0.1).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (14/0 unchanged), pytest
184 passed (was 175 + 9 new, now `tests/test_mining_increment_19.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, same as increments 16-18). Shipped NEUTRAL on dev: the
7 dev-train / 2 dev-holdout items matching the surface "how many X can WHO
buy" shape all require additional derivation this brief scopes out
(remaining-money-after-other-purchases, rate-derived budgets, or
saves-enough-to-buy-N-at-an-old-price) and correctly decline rather than
risk a wrong. The mechanism is exercised and verified via the synthetic
suite (direct "with $B" budget, single-holding-fallback budget, multiple
candidate budgets → decline, missing Price → decline, entangled
second-priced-item → decline, floor-vs-round regression) — shipped as
tested, safe infrastructure for a future combined increment (e.g.
remaining-budget capacity asks), matching the pattern of several prior
NEUTRAL-on-dev increments in this campaign.
TEST look: pending — spent manually.

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
  now resolve; remaining blockers are price-per-item forms — flat-price
  items mixed with "each"-priced ones in the same purchase list)
- "ITEM cost(s) $X each" (item as SUBJECT, not object of buy) — FIXED,
  increment 15: `cost`/`costs` gained a `price_verb` sense and `learn.py`
  emits a subject-keyed Price fact; the existing purchase-total consumer
  matches it unchanged. Gated NEUTRAL on dev (no dev item happens to pair
  this shape with a companion purchase sentence); re-run `rulekit stats`
  to see whether this unblocks any of the "no quantity known"/"missing a
  total" buckets now that the grammar gap is closed.
- **Rate chaining (14 "0 rates known" items) — MECHANISM LANDED (increment
  13), bucket did not move.** The 2-rate bridge (pages/hour × hours/day ×
  days) is implemented in the rate-span consumer and gated clean, but
  none of the 14 dev "0 rates known" items are actually this exact shape
  on inspection. The modal-verb subject-binding bug that blocked the
  structurally-closest item is FIXED (increment 14, `0eeaa76`: `modal`
  sense split from `auxiliary`; "He can read 50 pages an hour" now binds
  subject through the pronoun, and modal-stated rates solve end to end) —
  but that item still declines on its remaining shape (10 hours over 5
  days needs an hours-per-day division the bridge doesn't synthesize).
  Re-run `rulekit stats` to see what the bucket looks like post-fix.
  NOTE for future capacity asks: "how many X can she buy" is deliberately
  NOT a factual ask — the pattern layer's `auxiliary` token no longer
  matches modals (the kirsty DECL→WRONG the dev gate caught). A capacity
  ask shape (budget ÷ unit price) is a separate future class.
- **Passive voice (blocks some of the 9 "missing a total" items,
  confirmed by tracing one example)**: "half of the $60 **was earned by**
  Lisa" garbles into nonsense Predication facts (subject='dollar',
  verb='be'/'earn', dobj='lisa') instead of a FractionQuantity — the
  grammar only understands active voice subject-verb-object. This is a
  tokenizer/obligation-attachment gap, not a fold or synthesizer gap;
  likely touches shared parsing code used by every sentence (see the
  blast-radius invariant below — gate this one especially hard). Do NOT
  assume every "missing a total" item is passive voice — only one was
  traced; the rest may be chained-fraction cases instead (Trey/Kris/
  Kristen: "7 times as many... 1/4 as many...", which might just need
  the EXISTING fraction/relation synthesizers to chain through an extra
  hop rather than any new grammar — TRACED, see next bullet: for THIS
  item specifically it's not the synthesizer, it's a trailing-if split.
- **Trailing "if" clause split — CONFIRMED, exact fix scoped, not yet
  built.** Traced the Trey/Kris/Kristen "missing a total" item precisely:
  "How many more turtles does Trey have than Kristen, if Kristen has
  12?" — both Relation facts parse fine (Trey=7×Kris, Kris=0.25×Kristen),
  but "if Kristen has 12" is a TRAILING clause inside the QUESTION
  sentence itself, and `_split_leading_clause` (`src/rulekit/kernel/
  engine.py:81`) only handles the LEADING form ("If X, question?"), not
  "question, if X?" — so "Kristen has 12" never becomes a premise; only a
  bare valueless Predication is folded from it. This is exactly the
  "153-ish embedded when/after clauses" bucket below. Fix: a
  `_split_trailing_clause` counterpart — split at the LAST comma whose
  following text starts with "if", strip the trailing "?", turn it into
  a premise sentence, keep the wh-part as the question. Pure
  sentence-splitting, before any grammar/obligation processing — low
  blast radius (only fires on text it doesn't already split), but still
  needs the full dev-train/holdout gate per the blast-radius invariant
  before trusting it (this session's lesson: "low blast radius" was
  wrong twice already about things that touch shared code paths).
- ~210 "no quantity known": partitions ("Ten OF THEM are yellow"), goal/
  deficit shapes ("goal is 30 situps … make up the rest")
- ~70 fold-vs-fold conflicts: possessed-noun entity identity (Kennedy's
  house vs Benedict's house both lemma 'house' — needs attr-qualified
  entities; also blocks "coconut trees vs mango trees" noun-standard
  relations, attr-blind measure matching generally)
- 153-ish questions with embedded when/after clauses (only "If…," splits
  today — see the trailing-if bullet above, likely the same root cause)
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
