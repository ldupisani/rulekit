# Session handoff — 2026-07-11

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State below is committed through `87dbb7d` on `main` (github.com/ldupisani/rulekit;
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
- dev-holdout: 15 correct / 0 wrong (3,701 items — increment 33 was a real holdout SOLVE)
- curated suite: 52/52 · pytest: 277 · lint: 0 errors, 1 intended warning
- TEST ledger (36 looks spent, `projects/gsm8k/snapshots/test-ledger.jsonl`):
  0/1 (0%) → 4/1 (80%) → 5/1 (83.3%) → 5/2 REVERTED → 5/1 → 5/2 bisect →
  5/1 (83.3%) → 5/1 (look #8) → 5/1 (look #9) → 5/1 (look #10) →
  6/1 (85.7%, look #11 — a genuine COVERAGE GAIN) → 6/1 (#12) → 6/1 (#13) →
  6/1 (#14) → 6/1 (#15) → 6/1 (#16) → 6/1 (#17) → 6/1 (#18) →
  6/1 (85.7%, look #19) → 6/2 (75.0%, look #20: the 12-word vocab
  batch, REVERTED — the firewall's second kill, see
  docs/negative-results.md; main reset to the look-#19 state and dev
  verified item-identical, so 6/1 restored without a confirmation look) →
  6/1 (#21) → 6/1 (#22) → 6/1 (#23) → 6/1 (#24) → 6/1 (#25) → 6/1 (#26) →
  6/1 (85.7%, look #27) → 6/1 (#28) → 6/1 (#29) → 6/1 (#30) → 6/1 (#31) →
  6/2 (75.0%, look #32: the fruit/fruits family alone, REVERTED — and the
  look #20 culprit thereby IDENTIFIED; fruit is now quarantined, see
  docs/negative-results.md) → 6/1 (#33) → 6/1 (#34) → 6/1 (#35) →
  **6/1 (85.7%, look #36) ← live at increment 34** — #33–#36 batch 6
  (the parked briefs: increments 31–34 all held) —
  #12–#13 batch 1, #14 the modal split, #15–#16 batch 2, #17–#19 batch 3,
  #20 vocab revert, #21–#27 batch-4 re-land, #28–#32 batch 5 (increments
  27–30 held; 31 reverted); precision held on every surviving increment
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

## Increment 17: membership partitions (`d49bf50`)

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
TEST look #17: 6/1 (85.7%) — precision HELD vs look #16, increment kept.

## Increment 18: flat-priced purchase items (`eb0fe78`)

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
TEST look #18: 6/1 (85.7%) — precision HELD vs look #17, increment kept.

## Increment 19: capacity asks (budget / unit price) (`691c14f`)

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
TEST look #19: 6/1 (85.7%) — precision HELD vs look #18, increment kept.

## Increment 20: fused ordinal number tokens (5th, 3rd, 21st) (`7b5b49f`)

A pure unknown-word ceiling raise, not a new solver: the tokenizer
previously split a fused ordinal ("5th", "21st", "3rd") into a digit token
plus an orphan letter-token ("th"/"st"/"nd"/"rd"), which never resolves in
the lexicon and declines the whole reading as unknown-word (32 hits + 2
decline-reason mentions in the unknown-word worklist). Three general,
structural changes:

1. `tokenize.py`'s token regex gains a `\d[\d,]*(?:st|nd|rd|th)(?![A-Za-z])`
   alternative ahead of the plain-number pattern, recognizing digit+suffix
   as ONE token — productive grammatical morphology, like digit parsing
   itself, not a lexicon fact.
2. `numbers.py` gives the fused token its own `value_kind` ("ordinal"),
   distinct from count/multiplier/fraction.
3. `senses.py` maps `value_kind` "ordinal" to its own sense "ordinal" (not
   "value"). Because `guards.py`'s value-accounting only requires kinds in
   (count, multiplier, fraction), and `obligations.py`'s
   `NEED_CANDIDATES`/`_unit_sense_class` never grant "value" class to sense
   "ordinal", the ordinal token cannot feed the arithmetic fold or satisfy
   any dobj/object/count slot — it only stops being an unknown word,
   matching the decline-safety requirement that an ordinal is an
   index/modifier, never an operative count.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (14/0 unchanged), pytest
193 passed (was 184 + 9 new, now `tests/test_mining_increment_20.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, same as increments 16-19). Shipped NEUTRAL on dev: no
dev-train/dev-holdout item moves solved<->declined on this slice (the fix
raises the unknown-word ceiling generally rather than closing a specific
dev gap). The mechanism is exercised and verified via the synthetic suite
(fused-token recognition across 5th/21st/3rd/2nd/100th, a previously
unknown-word-blocked sentence now solving, decline-safety against the
ordinal feeding the fold as a count, decline-safety against the ordinal
satisfying a dobj slot, and a regression check that plain "5 dogs"
tokenization is unaffected) and confirmed against pre-fix behavior via git
stash (same input previously declined with "[unknown-word] cannot commit
while ['th'] are unknown"). This is a re-land: the candidate previously
passed constitution review and re-gated cleanly on a staging base that
included a since-reverted vocabulary increment; re-proven clean here on
`mining/batch-2026-07-11e`.
TEST look #21: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 21: wage earnings asks (rate x worked span) (`1bf8e4c`)

'How much does WHO earn/make (in SPAN)?' previously routed unconditionally
to the general event-fold ask (single-entity/bare-entity), which only
sums literal earn/make EVENTS — it never reached the rate-span consumer
even when a Rate fact ("$10 an hour") and a worked span ("Rob works 8
hours") were both known and read from the text. A new ask
(`packs/arithmetic/rules/core.yaml`, `ask/earn-span`) gates the verb slot
on a new narrow `wage_verb` category (`packs/difg-mined/categories/wage.yaml`:
earn/earns/earned/make/makes/made — multi-membership alongside the
existing acquire/produce categories, mirroring the `spend_verb` pattern in
`core-english/categories/core.yaml`) and routes to the SAME rate-span
consumer used since increments 8-9, untouched in its unique-rate/bridging/
conversion discipline. The 'in SPAN' clause is optional; its id sorts
(alphabetically) before `ask/how-much-bare-entity` on purpose so the
deterministic tie-break in `match_ask` sends a wage-verb question to
rate-span instead of an event-fold that never had a matching event to
fold. When the question names no span clause, a small, general extension
in `answer.py`'s rate-span consumer (not earn/make-specific) reads the
span off a standalone quantity fact for the entity in the rate's own
per-unit, on the same unique-fact-or-decline discipline as the existing
bridge lookup.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 199 passed (was 193 + 6 new, now
`tests/test_mining_increment_21.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, same as
increments 16-20). Shipped NEUTRAL on dev: no dev-train/dev-holdout item
happened to be simple enough (a lone rate + a lone matching quantity
fact, uncompounded by multi-day/multi-rate summation) to flip
solved<->declined on this split. The mechanism is exercised and verified
via the synthetic suite (span stated in its own separate sentence — the
gap the event-fold ask could never close; span named directly in the
question; the reused consumer's unit-conversion discipline firing
unchanged through the new ask; decline-safety with no span fact at all;
decline-safety with an ambiguous multi-span case; decline-safety against
an unrelated acquire verb like 'buy' being pulled into the wage gate). This
is a re-land: the candidate previously passed constitution review and
(except for the interchangeable-measure increment) already re-gated
cleanly on a staging base that included a since-reverted vocabulary
increment; re-proven clean here on `mining/batch-2026-07-11e`.
TEST look #22: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 22: remaining-budget capacity asks (budget minus other purchases, div unit price) (`481f792`)

Extends increment 19's 'capacity' consumer (budget / unit price) to a budget
entangled with OTHER purchases the same entity already made ("Pens cost $2
each. Nora has $20. She buys a notebook for $8. How many pens can Nora
buy?"). Increment 19 declined any such entanglement outright ("the budget
would need splitting across items"). Now: when every entangled other-priced
item is itself a fully-priced, unambiguous PURCHASE (qty and price both
known, no cost-splitting predicate on the entity), remaining = budget -
Σ(qty x price over those other purchases) is computed and the existing
floor division runs on the remainder instead of declining.

Mechanism (`src/rulekit/kernel/answer.py`): `_purchase_total` gains an
opt-in `exclude_item` parameter (default `None`, every existing caller
unaffected) so the capacity consumer can total the entity's OTHER priced
purchases without double-counting the asked item. This reuses
`_purchase_total`'s own increment-10 invariant (an unpriced purchase, or a
'splits/shares the cost' predicate on the entity, declines the WHOLE
total) unscoped, so it automatically extends to the subtraction path. A
negative remainder declines. Any other-priced item held via a NON-purchase
verb ("has"/"owns") is not spending and stays the original increment-19
decline (ambiguous). `tests/test_mining_increment_19.py` is updated in
step: its "entangled other priced item declines" case (Mary's 3 erasers
alongside a priced pen ask) is exactly the class this increment now
converts to a commit ((10 - 3) / 2 = 3 floor); the stale assertion and
comment are replaced, and a new decline case (an entangled purchase with a
FURTHER unpriced purchase) preserves coverage of the still-open
increment-10 invariant.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged — no dev-train item currently reaches this
exact entangled-other-purchase structure), dev-holdout diff NEUTRAL 0/0/0
(3701 items, 14/0 unchanged), pytest 206 passed (was 199 + 7 new, now
`tests/test_mining_increment_22.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, same as
increments 16-21). Shipped NEUTRAL on dev: the mechanism is exercised and
verified via the synthetic suite (direct entangled-purchase subtraction
computing the correct remaining budget, decline-safety when a further
purchase is unpriced, decline-safety when the remainder would go negative,
and a regression check that a non-purchase "has/owns" entanglement still
declines as increment 19 originally specified). This is a re-land: the
candidate previously passed constitution review and (except for the
interchangeable-measure increment) already re-gated cleanly on a staging
base that included a since-reverted vocabulary increment; re-proven clean
here on `mining/batch-2026-07-11e`.
TEST look #23: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 23: goal-deficit asks (how many more X does WHO need) (`7cb20ce`)

"How many more X does WHO need?" over a stated DESIRE goal ("Lena wants to
collect 30 stamps") plus a current STATE holding ("She has 12 stamps") now
resolves as goal minus holding, instead of declining. A DESIRE verb +
infinitive ("wants to collect 30 stamps") emits a new Goal fact — a stated
TARGET quantity, distinct from a holding or an event — via a new
`arithmetic/goal-desire-quantity` pattern rule, gated on a new `desire`
verb category (declared in `core-english/categories/core.yaml`, members in
`packs/difg-mined/categories/semantic.yaml`: want/wants/wanted/wanting;
deliberately untagged for polarity so it can never leak into the signed
event fold). A new ask shape ("how many more ITEM does WHO need", gated on
a dedicated `need_ask_verb` category kept separate from the pre-existing
broader `receive` category) resolves via a new `deficit` consumer
(`answer.py`): goal value minus the entity's single current STATE holding
of the same measure. Goal is use-gated for value accounting like
Rate/Price (`guards.py`) — existence alone doesn't count as read. Commits
only when exactly one Goal fact and exactly one current holding resolve
for the entity/measure; declines on no holding, more than one goal, a goal
already met (never a negative "how many more"), or conflicting goal
statements.

Verified side effect (in scope, not a separate change): the rule's own
item-slot consumption masks the generic SVO fold's redundant Quantity
emission for both the desire verb and its target verb on the same
sentence (learn.py's existing pattern-consumed masking, unchanged) — "how
many stamps does Lena have" over a goal-bearing sentence now answers from
the stated holding cleanly.

Scoped out (adjacent findings, not touched this increment): a possessive
"X's goal is N item" premise form overlaps the in-flight
possessive-entity-identity candidate; a "needs N item" premise form was
dropped because 'need' is already mined into the 'receive' category
(polarity +1) — folding it as a goal premise would sit next to a
pre-existing, unrelated bug where "Tom needs 30 apples. He has 12." already
answers 42 via the ordinary SVO scan today, on main, independent of this
change (confirmed via diagnose; not this candidate's class to fix).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 212 passed (was 206 + 6 new, now
`tests/test_mining_increment_23.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, same as
increments 16-22). Shipped NEUTRAL on dev: no dev-train/dev-holdout item
currently states both a desire-goal and a matching current holding — the
mechanism is exercised and verified via the synthetic suite (goal minus
holding across two independent entity/measure pairs; the unrelated-ask
regression that a goal-bearing sentence still answers a plain "how many
does X have" from the stated holding alone; decline-safety with no current
holding stated; decline-safety when the goal is already met; decline-safety
on two conflicting goal statements for the same entity/measure). This is a
re-land: the candidate previously passed constitution review and (except
for the interchangeable-measure increment) already re-gated cleanly on a
staging base that included a since-reverted vocabulary increment;
re-proven clean here on `mining/batch-2026-07-11e`.
TEST look #24: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 24: event-then-restate state disambiguation (`a8be7f0`)

`kernel/answer.py`'s `_entity_total` (the single-entity fold shared by
every state-verb ask) used to sum a STATE Quantity together with any
prior EVENT Quantity for the same entity/measure, even when the state
sentence is narratively just restating the post-event running total
("Kendall finds 6 dimes. She now has 6 dimes." returned 12 on unmodified
main, not 6). This was root-caused during an earlier failed
state-conjunction candidate and left as the worklist's top item.

Mechanism (kernel-structural, no lexicon, no per-problem parsing): when
both a state and an event Quantity exist for the same entity/measure, and
any state fact's sentence index is greater than the EARLIEST event's, the
fold now declines instead of summing — converting a silent latent wrong
into a safe decline rather than attempting a resolution rule. A state
that precedes every event (the ordinary anchor narrative order the fold
was built for) is completely unaffected, since the new check only fires
when the state comes strictly LATER than some event. All state verbs
(have/own/be) are one equivalence class per the campaign invariant; the
synthetic suite exercises more than one member of it ('have' and 'own').

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 218 passed (was 212 + 6 new, now
`tests/test_mining_increment_24.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
Shipped NEUTRAL on dev: no dev-train/dev-holdout item currently exercises
this exact event-then-restate pairing on this slice; the synthetic suite
(event-then-restate decline, multi-event-then-restate decline, state-verb-
equivalence-class decline via 'own', anchor-then-event regression,
state-only and event-only baselines) is the coverage evidence, and the
mechanism converts the exact silent-wrong class the failed
state-conjunction candidate traced (Kendall/dimes, 12 vs 6) into a safe
decline rather than a confident wrong. This is a re-land: the candidate
previously passed constitution review and (except for the
interchangeable-measure increment) already re-gated cleanly on a staging
base that included a since-reverted vocabulary increment; re-proven clean
here on `mining/batch-2026-07-11e`.
TEST look #25: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 25: possessive-qualified entity identity (`2ffa493`)

"Kennedy's house has 5 rooms. Benedict's house has 3 rooms." previously
folded to the bare noun lemma 'house' regardless of possessor
(`condense.py`'s merge-possessive doesn't touch the noun's own `lemma`
feature), so two DIFFERENT possessors' same-noun holdings collided as one
fact-store entity and the whole item declined with "conflict: fold and
fold disagree" instead of resolving either possessor's question.

Mechanism (kernel-structural, no lexicon): entity identity stays the bare
lemma everywhere it already worked — `Quantity.entity` is unchanged, so
"Tom's dog ... the dog ..." still folds into one entity exactly as
before. A NEW `owner` field on `Quantity` (`condense.py` tags the merged
possessive noun; `learn.py` copies it onto the fact) is read ONLY by
`FactStore.admit`'s collision handling: a same-key VALUE conflict between
two Quantity facts with two DIFFERENT non-null owners is not a genuine
disagreement — it's two entities the bare lemma alone can't
distinguish — so both re-key to `entity[owner]` and admit separately
instead of quarantining. A new ask id (`ask/how-many-entity-possessed`,
gated on a new `possessed` slot type requiring the noun to carry an
owner) resolves a possessive-qualified subject the same way, with an
owner-scoped fallback in the single-entity consumer so a bare
(non-conflicting) holding can still answer — but never across a
different NAMED owner. Decline-safety: an unmentioned owner's same-noun
entity declines rather than borrowing another owner's number.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 222 passed (was 218 + 4 new, now
`tests/test_mining_increment_25.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
Shipped NEUTRAL on dev: no dev-train/dev-holdout item currently states two
different possessors of the same-noun entity on this slice; the synthetic
suite (two possessors of the same noun each resolving independently,
cross-mention coreference still folding when only one owner is ever
named, decline-safety for an unmentioned second owner) is the coverage
evidence. This is a re-land: the candidate previously passed constitution
review and (except for the interchangeable-measure increment) already
re-gated cleanly on a staging base that included a since-reverted
vocabulary increment; re-proven clean here on `mining/batch-2026-07-11e`.
TEST look #26: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 26: category-sibling measure resolution is opt-in (interchangeable categories) (`38fc2a3`)

User-reported confident-wrong: "Tom has 20 pets. 8 of them are dogs. How
many cats are there?" answered 8 — `_resolve_measure` let an ask noun with
no facts of its own resolve to the UNIQUE in-store member of its semantic
category (here 'animal'), so the factless 'cat' ask silently borrowed the
'dog' fact. That sibling-resolution behavior was built for currency
("money" → the one currency actually in play) and over-applied to
concrete count nouns generally, turning any two-sibling-noun item into a
confident wrong rather than a decline.

Mechanism (kernel-structural, no lexicon): categories now declare an
`interchangeable: bool` field (`schemas.py`'s `CategoryDef`); only
`currency` sets it `true` in `packs/core-english/categories/core.yaml`.
Both category-sibling resolution paths (`registry.py`'s category-member
lookup and `answer.py`'s `_resolve_measure` fallback) require
`interchangeable` before letting an ask noun stand in for a same-category
sibling with its own facts. A category that doesn't opt in now declines
instead of borrowing a sibling's number — the ask noun still resolves
normally from its OWN facts when it has any (the fix only removes the
borrow-from-sibling fallback for non-interchangeable categories).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 227 passed (was 222 + 5 new, now
`tests/test_mining_increment_26.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
Shipped NEUTRAL on dev: no dev-train/dev-holdout item currently exercises
two same-category sibling count nouns on this slice; the synthetic suite
(sibling noun never stands in, with and without partition machinery;
currency still interchangeable; an ask noun's own facts still resolve;
both siblings with facts each answer from their own measure) is the
coverage evidence. This is a re-land: the candidate previously passed
constitution review and had already re-gated cleanly on a staging base
that included a since-reverted vocabulary increment (unlike its
batch-mates, its own gate outcome was also clean on that prior base); this
run re-proves the gate on `mining/batch-2026-07-11e`, the corrected
staging lineage, from scratch.
TEST look #27: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 27: negated-clause quantities (negation-blind fold) (`d2d92cb`)

Live confident-wrong invisible to the decline-bucket stats: "Tom does not
have 5 apples. How many apples does Tom have?" committed 5.0 — the fold
over tom/apple ignored the negation entirely (the existing `negates`
obligation only covers the copula shape "is not", never the auxiliary
shape "does not VERB", nor "never", "no longer"). 146/3772 dev-train
questions contain not/never/no longer/n't (scratchpad cue scan); this is
priority 1 under precision-before-coverage (constitution rule 4) even
though it isn't a stats decline bucket.

Mechanism (kernel-structural, no lexicon): a new `negation` category
declared in `packs/core-english/categories/core.yaml` with members
not/never/no longer (already-known words, none quarantined, tagged with
the existing `negator` sense). `learn.py`'s Quantity fold/emission path
structurally checks — via `guards.py` — whether a negation-category token
attaches to the verb whose Quantity is about to be folded, scoped to that
verb's OWN clause (the existing complementizer clause boundary, not the
whole sentence, so an unrelated negation elsewhere in the sentence cannot
blank an otherwise-fine fold on a different clause's verb). A hit
DECLINES that fact's contribution entirely — decline-only, no attempt to
compute negated semantics.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 233 passed (was 227 + 6 new, now
`tests/test_mining_increment_27.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
Shipped NEUTRAL on dev: no dev-train/dev-holdout item's current
correct/wrong classification changes on this slice (decline-only guard,
0 BROKE, 0 DECL→WRONG); the synthetic suite (auxiliary "does not VERB",
"never", "no longer", clause-scoped so an unrelated negation elsewhere in
the sentence doesn't blank an unrelated fold, and the pre-existing copula
"is not" shape still declines as before) is the coverage evidence.
TEST look #28: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 28: fraction/percent partitions (N% / half of them are ADJ|NOUN) (`7c7572b`)

The PREMISE-side counterpart of increments 16/17's count-valued partition
machinery ("N of them are ADJ/NOUN"): "25% of them are red" / "Half of the
10 apples are red" both declined `0 partition facts known` even though the
ask shape already matched — only the fact was missing. Scratchpad cue scan:
223 dev-train items contain "N% of", 61 contain "half/third/quarter/% of
them/the ... are"; feeds the ~171 "no quantity known: partitions" and part
of the 2669 "no ask shape" buckets on the worklist.

Mechanism (YAML-first): two new pattern rules in
`packs/arithmetic/rules/core.yaml` (partition-attribute-fraction,
partition-membership-fraction) mirror the existing partition-attribute/
partition-membership rules but gate on `{type: fraction}` instead of
`{type: number}`, emitting `PartitionQuantity` with the raw fraction (0-1)
as value and a new `is_fraction: bool = False` marker (default preserves
every existing cardinal-form fact unchanged — model.py). In
`saturate.py`'s `_partition_synth` (the increment-16/17
`synth/partition-of-collection`, extended not widened): once the
plural-pronoun collection resolves to the real prior measure exactly as
before, a fractional partition is additionally sized against that
collection's own total-as-of-this-sentence (`_pool_before`, the same
helper `synth/fraction-of-pool` already uses) before being re-emitted as a
real count (`is_fraction` reset to False); an unresolvable total declines
exactly like fraction-of-pool's own discipline. `guards.py`'s
unresolved-derivation check drops `value` from its identity key only for
`is_fraction=True` facts (a fractional partition's value legitimately
changes across resolution, fraction -> count); the cardinal form's guard
match is untouched, still exact-value. Reuses the increment-16/17 consumer
(`partition-complement` in answer.py) and the membership-count companion
synth completely unchanged — the resolved fact's `collection` field is
always the real measure name, never the raw pronoun, so
`partition-complement`'s `p.collection == item` filter naturally excludes
the still-pronoun-collection original.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 239 passed (was 233 + 6 new, now
`tests/test_mining_increment_28.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) /
22 info. Shipped NEUTRAL on dev: 0 SOLVED because no sampled dev-train/
dev-holdout item's grammatical shape is a full-commit fix on this slice
(other declines in those documents remain) — the mechanism is proven via
`rulekit solve` on synthetic probes matching the brief's own evidence
sentences ("25% of them are red", "Half of the 10 apples are red"), with
the decline discipline (ambiguous collection, no prior collection,
unresolved total) holding throughout.
TEST look #29: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 29: determiner-each subject prices (Each ITEM costs $N) (`7b66d7b`)

The SUBJECT-side counterpart of increment 15's TRAILING distributive-'each'
shape ("Eggs cost $2 each"): "Each pen costs 3 dollars" declined `0 price
facts known` because the price_verb emission path only recognized the
distributive quantifier trailing the currency dobj, never one scoping the
subject noun itself. Fresh stats: "0 price facts known" = 139, "no pay
events" = 45, "no spend events" = 67; cue scan found 47 dev-train items
matching "each NOUN cost(s)".

Mechanism: a new helper `_has_distributive_determiner` in `learn.py`
mirrors `_negated`'s reverse-obligation-lookup pattern — scanning every
unit in the reading for one whose `collection` obligation resolves to the
price_verb's SUBJECT noun (the quantifier -> collection edge only runs
quantifier-to-noun, never noun-to-quantifier, so the lookup must be
reversed). The price_verb Price-emission condition becomes an OR of the
pre-existing trailing-each test (`_is_rate` + `_rate_unit is None`,
UNWIDENED per the increment-11 invariant) and this new subject-side test —
same sense gate ('quantifier'), opposite side of the noun. No `answer.py`
change: the increment-10/15 purchase-total consumer already matches Price
facts by item noun regardless of emission site.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 246 passed (was 239 + 7 new, now
`tests/test_mining_increment_29.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info. Shipped NEUTRAL on dev: 0 SOLVED because no sampled dev-train/
dev-holdout item pairs this subject-priced-each shape with a companion
purchase sentence on the same item noun in this slice — the mechanism is
proven directly ("Tom buys 2 pens. Each pen costs 3 dollars. How much does
Tom pay?" -> 6) and via the 47-item cue scan (0 new correct, 0 new wrong;
every match still declines on a separate, unrelated gap).
TEST look #30: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 30: sales revenue asks (how much does WHO make/earn from selling N ITEM at $P each) (`be038b3`)

The sell-side mirror of increment 10's purchase-total. Fresh stats: "no
'make' events" = 33, "no 'sell'" = 7, "no 'earn'" = 7; probe "Tom sells 5
cakes at 3 dollars each. How much money does Tom make?" declined `no make
events known`. Cue scan: 137 dev-train items have a `$` near sell/sold; 112
ask "how much ... make/earn".

Mechanism: `learn.py` already emits Price/Quantity facts generically for
any "N ITEM at $PRICE each" dobj shape (not gated to the `purchase`
category), so sell-verb sentences already carry the same facts
purchase-total consumes — no `learn.py` change needed. Adds a new narrow
`sell` category (parent: `lose`) in
`packs/difg-mined/categories/semantic.yaml` tagging sell/sells/sold,
multi-membership alongside the existing broad `lose` tag (too wide to gate
a revenue consumer on) — same pattern as `purchase` (parent: `acquire`).
`answer.py` gets `_revenue_total`, summing qty x unit price over every
sell-category Quantity an entity holds, wired into the single-entity
event-ask branch alongside the existing spend_verb/purchase-total branch,
gated on the `wage_verb` category (make/earn) so an unrelated "how much did
Mary buy" is untouched. Any sold item missing its own Price fact declines
the WHOLE total (increment-10 discipline, unchanged). A Rate fact on the
same entity (increment 21's ask/earn-span territory) makes 'make'/'earn'
ambiguous between a wage rate and sale revenue for the same person —
declines rather than guessing which one the question means.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 252 passed (was 246 + 6 new, now
`tests/test_mining_increment_30.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info. Shipped NEUTRAL on dev: all real dev-train "sells ... how much does X
make" items involve multi-item conjunctions, wage-rate compositions, or
profit (revenue - cost) that this narrow single-conjunct mechanism
correctly leaves declined (matches the open conjunction-handling gap noted
above for verbs outside `purchase`; profit is out of this brief's scope) —
the mechanism is proven directly ("Tom sells 5 cakes at 3 dollars each. How
much money does Tom make?" -> 15) plus the ambiguity/decline probes in the
synthetic suite.
TEST look #31: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 31: age asks (how old is WHO, over stated ages and older/younger relations) (`f239764`)

Re-land of the batch-5 parked branch (`mining/parked/age-asks`), rebased onto
current main via cherry-pick (clean — no conflicts this time; the earlier
parking was against increments that have since landed and settled). Fresh
stats: "no ask shape recognizes this question" = 2668 (largest bucket); cue
scan over dev-train (3772 items) found 108 items with age cues (how old /
years old), 65 with an explicit "how old is/was" ask. Probe "How old is his
sister?" previously mis-routed to "no membership fact either way" — no age
ask shape existed.

Mechanism, three rules in `packs/arithmetic/rules/core.yaml`, no kernel
change:
1. `arithmetic/stated-age`: "WHO is N years old" (copula + counted noun +
   literal 'old') emits a Quantity(measure='year') — no new consumer needed.
2. `ask/how-old-is`: "how old is WHO" resolves via the EXISTING
   single-entity consumer, exactly like the sibling how-much/how-many entity
   asks. It outranks `ask/is-membership` on consumed-units specificity alone
   (4 tokens vs 3), never by reordering (increment 21's alphabetical
   ask-id tie-break lesson — watched, not triggered here).
3. `arithmetic/dangling-comparative-relation`: a decline-safety rule with NO
   emits. "X is N years older" with no "than Y" anchor was falling through
   to the general SVO fold, which reads "is [N years]" as a bare stated
   Quantity(N) — a confident-wrong once 'year' became an askable measure.
   This rule only consumes the clause (suppressing the fold's misread); an
   implicit-anchor comparative stays declined, not guessed.

Also tags 'older'/'younger' into the existing `more_dir`/`less_dir` (delta)
categories in `packs/difg-mined/categories/semantic.yaml` — both words were
already members of the unrelated 'higher'/'lower' magnitude-comparative
category but never of 'delta', so `arithmetic/anchored-relation-postfix`
("X is N years older/younger than Y") never actually fired for age
relations before this. Scoped to exactly these two words (quarantine-grepped
clean).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 258 passed (was 252 + 6 new, now
`tests/test_mining_increment_31.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 21
info. Shipped NEUTRAL on dev: no dev-train/dev-holdout item alone exercises
the full stated-age + relation chain end to end (typical for this pack) —
the mechanism is proven directly by the synthetic suite (stated-age lookup,
older/younger relation chaining in either narration order, dangling-
comparative decline, future-age decline) plus the frequency estimate above.
TEST look #33: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 32: stated-need premises as goals (WHO needs N ITEM) (`8263f1e`)

Re-land of the batch-5 parked branch (`mining/parked/need-as-goal`), reapplied
by hand (the stored patch no longer applied cleanly due to context drift in
`core.yaml` from increments 27/28/30 landing since parking) and re-gated from
scratch. Fresh stats: "no 'need' events known" = 39, "0 goal facts known" = 9;
cue scan found 63 dev-train items with a "needs N" premise. Probe "Tom needs
30 apples. He has 12 apples. How many more apples does Tom need?" declined
"0 goal facts known" — the increment-23 deficit ask matched, but no Goal fact
was ever emitted from a needs-premise.

Mechanism, one new rule in `packs/arithmetic/rules/core.yaml`, no kernel
change:
- `arithmetic/goal-need-quantity`: "WHO needs N ITEM" (direct-object form,
  no infinitive — the counterpart to `goal-desire-quantity`'s "wants to VERB
  N X") emits a Goal fact. No new consumer needed: the existing increment-23
  goal-deficit ask already resolves any Goal fact against the entity's
  single current STATE holding of the same measure, reused unchanged.

Category surgery makes the emission safe rather than double-counting: 'need'/
'needed'/'needs' are removed from the `receive` event category (polarity +1)
in `packs/difg-mined/categories/semantic.yaml` and reassigned to a new
`need_premise` category declared in `packs/core-english/categories/core.yaml`
— untagged for polarity, mirroring how 'desire' sits outside any event
category. This simultaneously kills a latent confident-wrong flagged at
increment 23's landing: "Tom needs 30 apples. He has 12 apples." used to fold
to 42 via the generic SVO event sum because 'need' carried receive's +1
polarity; it now declines that fold (untagged verb, pattern-consumed) while
"how many more apples does Tom need" correctly answers 18 via the deficit
consumer. `need_premise` is kept as its own category (not merged into
'desire') so the direct-object phrasing never widens 'want's own rule
family — a distinct blast-radius boundary.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
14/0 unchanged), pytest 265 passed (was 258 + 7 new, now
`tests/test_mining_increment_32.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 21
info. Shipped NEUTRAL on dev: no dev-train/dev-holdout item alone exercises
the full needs-premise + deficit-ask chain end to end (typical for this
pack) — the mechanism is proven directly by the synthetic suite (goal
emission, deficit resolution, the killed SVO-fold confident-wrong, and the
`need_premise`/`receive` category split) plus the frequency estimate above.
TEST look #34: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 33: remaining-money asks (how much money does WHO have left) (`51853aa`)

Re-land of the batch-5 parked branch (`mining/parked/money-left-asks`): the
mechanism had already passed the full dev gate once; it was blocked only
because its synthetic test file paraphrased a GSM8K corpus item (a
lightly-edited Phillip/$95/$14/oranges item). This increment reapplies the
unchanged mechanism and replaces the test file with entirely fresh names,
nouns, and numbers invented from scratch (`tests/test_mining_increment_33.py`).
Fresh stats: "no ask shape" = 2668 (money-left is a slice of it) plus "no
'spend' events" = 66; cue scan found 82 dev-train items ending a question in
"have left?", 76 matching "how much (money) ... left". Probe "Lily has 20
dollars. She buys 3 pens at 2 dollars each. How much money does Lily have
left?" declined via value-accounting before this increment — the facts
exist, the ask shape did not.

New ask (`ask/how-much-money-entity-left`, `packs/arithmetic/rules/core.yaml`)
matching "how much money does WHO have left", gated on the literal 'money'
plus a trailing 'left' plus the existing `state` verb category (have/has/
had/...) so it consumes MORE units than the pre-existing
`ask/how-much-noun-entity` over the same question and wins via max-consumed
specificity, routed to a new `money-left` consumer in `answer.py`.

Mechanism: the entity's general money total via the SHARED `_entity_total`
fold (the same state-anchor + signed-event fold the bare "how much money
does WHO have" ask already uses, so a "spends $N on Y" / "receives $N" event
already signed by category polarity folds in unchanged) minus its priced
purchases via `_purchase_total`, reused UNCHANGED so the increment-10/22
invariant travels with it (any unpriced purchase, or a 'splits/shares the
cost' predicate on the same entity, declines the WHOLE total rather than
risk a silently dropped term). The subtraction never double-counts: a
priced purchase ("buys a gadget for $8") never emits a currency-measured
Quantity at all (learn.py emits an ITEM-measured Quantity plus a separate
Price fact), so it is invisible to `_entity_total`'s currency fold and only
ever appears once, in the purchase-total subtraction. A negative remainder
(purchases exceeding the money total) declines rather than committing an
impossible answer. Purely additive: new ask + new consumer branch, no
shared-function widening (the `_purchase_total`/`_entity_total` call
signatures are unchanged from increment 22).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff SHIP +1/0/0 (3701 items,
15/1 solved — item `4a394fadccdf`), pytest 273 passed (was 265 + 8 new, now
`tests/test_mining_increment_33.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 21
info. TEST look #35: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 34: attribute-qualified entity identity (coconut trees vs mango
trees fold as distinct entities) (`87dbb7d`)

Re-land of the batch-5 parked branch (`mining/parked/attr-qualified-entities`),
rebased onto increment 25's owner machinery (the cherry-pick conflict that
parked it). Fresh stats: "conflict: fold and fold disagree about" = 92
(fourth-largest structure bucket) — the modifier-blind lemma collision class
this HANDOFF has tracked since possessives were fixed by increment 25; the
ADJECTIVE/noun-modifier half was still open. Two same-lemma nouns
distinguished only by an attributive modifier ("The coconut tree has 12
branches. The mango tree has 8 branches.") both folded to the bare noun
lemma 'tree' (condense.py's merge-attribute / merge-compound don't touch the
noun's own `lemma` feature), colliding as one fact-store entity and
declining the whole item ("conflict: fold and fold disagree").

Mechanism: a kernel-structural mirror of increment 25 (possessive-qualified
entity identity), swapping the qualifier's SOURCE from possessive 's to an
attributive modifier. Entity identity stays the bare lemma everywhere it
already worked (`Quantity.entity` is unchanged, so "the tree ... it ..."
keeps folding into one entity exactly as before). A new `qualifier` field on
`Quantity` (`model.py`), independent of `owner` and excluded from
`key()`/`value_part()`, is populated by `condense.py`'s merge-attribute
("red apple") and merge-compound ("mango tree") passes and copied onto the
fact by `learn.py`. It is read ONLY by `FactStore.admit`'s collision
handling (`facts.py`): a same-key VALUE conflict between two Quantity facts
with two DIFFERENT non-null qualifiers is not a genuine disagreement — it is
two entities the bare lemma alone can't distinguish — so both re-key to
`entity[qualifier]` and admit separately instead of quarantining. An
unmentioned qualifier on the same noun still declines rather than borrowing
a value from a differently-qualified sibling (increment 25/26
decline-safety precedent, preserved). A new ask id
(`ask/how-many-entity-qualified`, `packs/arithmetic/rules/core.yaml`) gated
on a new `qualified` slot type in `patterns.py`/`schemas.py` routes the
qualified question form through `answer.py`'s existing per-entity consumer,
unchanged.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 277 passed (was 273 + 4 new, now
`tests/test_mining_increment_34.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 21
info. TEST look #36: 6/1 (85.7%) — precision HELD, increment kept.

## The next mining worklist (from the last close-miss scan)

Numbers below predate this session's work and need a fresh `rulekit
stats` pass before trusting them.

- **state-verb-conjunction — deferred THREE times, always for the same
  test contamination.** Batch 6's attempt (parked as
  `mining/parked/state-verb-conjunction-3`) passed the dev gates but was
  review-blocked because its tests contain "Maria has 4 dimes, 4
  quarters, and 7 nickels" — a verbatim GSM8K train substring inherited
  from the earlier parked branches' tests. The MECHANISM appears sound
  across all three attempts. Next attempt: rebase the mechanism from
  `state-verb-conjunction-3`, but write the tests from a blank file —
  do NOT copy anything from any `mining/parked/state-*` branch's tests/.
  (Batch 5's other parked briefs all landed in batch 6: `age-asks` →
  increment 31, `need-as-goal` → 32, `money-left-asks` → 33,
  `attr-qualified-entities` → 34.)

- **Event-then-restate state disambiguation in `_entity_total`
  (answer.py)** — surfaced by /mine batch 3's failed `state-conjunction`
  candidate (`[FAILED-GATE]` WIP preserved on
  `mining/parked/state-conjunction`): when a `state` Quantity for
  entity/measure X appears in a LATER sentence than a prior EVENT
  Quantity for the same entity/measure, the state sentence may be a
  RESTATEMENT of the running total (should anchor/replace), not an
  independent additional holding (current behavior: sum). Corpus-wide and
  orthogonal to conjunctions — must be scouted and gated on its own
  BEFORE any conjunct-recovery widening can safely ship. The candidate's
  two structural `_conjoined_purchase_items` fixes (stop-on-verb,
  discard-segment-on-verb-break) are real, general, and preserved in the
  WIP commit — a future attempt should keep them.
- **vocab-ceiling-batch: deferred TWICE at constitution review for the
  same violation** — both juniors "synthesized" tests by trimming the
  GSM8K train item "Elysse can carry 3 bags of groceries…" (distinctive
  name verbatim; a DEV item leaking into the permanent test suite). The
  mechanism may be fine; do NOT re-propose this brief without instructing
  the junior to invent test text from scratch (new names, new nouns, new
  numbers — never paraphrase a corpus item).
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
