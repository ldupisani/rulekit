# Session handoff — 2026-07-11

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State below is committed through `87b8242` on `main` (github.com/ldupisani/rulekit;
check `git status`/`git log origin/main..HEAD` before assuming push parity).

## Where the project is

Everything through P5 of the original plan is DONE: kernel, YAML packs, lint
(overlap witnesses + blast radius), document re-parse loop, GSM8K harness with
firewall, visual designer (`rulekit serve`, port 8321 — busy-state, slice
targets, TEST gated behind a checkbox). The GSM8K mining campaign is in full
swing under the constitution (no lexicon in Python, no per-problem parsing,
every increment through the gates).

**Current numbers (all verified at head):**
- dev-train: 33 correct / 0 wrong (3,772 items, 100% precision) — GOAL: 100
- dev-holdout: 21 correct / 0 wrong (3,701 items)
- curated suite: 52/52 · pytest: 487 · lint: 0 errors, 1 intended warning
- TEST ledger (64 looks spent, `projects/gsm8k/snapshots/test-ledger.jsonl`):
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
  6/1 (85.7%, look #36) → 6/1 (#37) → 6/1 (#38) → 6/1 (#39) → 6/1 (#40) →
  6/1 (85.7%, look #41) → 6/1 (#42) → 6/1 (#43) →
  6/1 (85.7%, look #44) → 6/1 (#45) → 6/1 (#46) →
  6/1 (85.7%, look #47) → 6/1 (#48) → 6/1 (#49) →
  6/1 (85.7%, look #50) → 6/1 (#51) → 6/1 (#52) → 6/1 (#53) →
  6/1 (85.7%, look #54) →
  6/1 (85.7%, look #55) →
  7/1 (87.5%, look #56 — TEST coverage GAIN, the new floor) → 7/1 (#57) →
  7/1 (87.5%, look #58) →
  7/1 (87.5%, look #59) → 7/1 (#60) →
  7/1 (87.5%, look #61) → 7/1 (#62) →
  7/1 (87.5%, look #63) →
  **8/1 (88.9%, look #64) ← live at increment 62, the NEW FLOOR** —
  #62–#63 batch 18, #64 batch 19 (increment 62, elided-measure entity
  asks: +3 train / +3 holdout / +1 TEST — the largest single increment
  of the campaign) —
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
   Precision must hold vs the last look (88.9%, look #64) or the
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

## Increment 35: conjoined state-verb holdings (`b27e091`)

Re-land of `mining/parked/state-verb-conjunction-3`, the mechanism deferred
THREE times before — always for the same reason: its tests inherited a
verbatim GSM8K train substring ("Maria has 4 dimes, 4 quarters, and 7
nickels") from earlier parked branches' test files, blocking constitution
review each time. This attempt rebased the mechanism only and wrote every
test from a blank file with invented text (Priya/pens/pencils, Jordan/toys/
books) — no text read from, copied, or paraphrased from any prior
state-verb-conjunction branch.

Scopes increment 11's conjunct-recovery walker (`_conjoined_purchase_items`
in `learn.py`) to the `state` verb category (have/own/be) as well as
`purchase`: each comma/conjunction segment's own counted noun becomes a
sibling Quantity for the same subject, exactly like a purchase list's
siblings. State siblings are ordinary holdings, never priced — only a
purchase verb's own siblings emit a Price fact. Preserves the -3 branch's
stop-on-verb discipline: the shared walker's tail scan STOPS the instant it
meets another VERB and DISCARDS (does not flush) the in-progress segment
when it does — a second finite clause coordinated with ','/'and' ("Priya
has 5 pens, and Jordan has 6 books") is a NEW clause, not a sibling noun
phrase, and must never leak its own subject/dobj into the first entity's
count. This fires unconditionally in the shared walker (purchase-item lists
essentially never coordinate a whole second clause before the period), so
purchase-verb behavior (increment 11) is unaffected — verified by a
non-regression test in the new suite plus `tests/test_mining_increment_11.py`
(its `test_plain_multi_dobj_conjunction_still_declines` now uses an EVENT
verb, "ate", since it documented exactly the gap this candidate closes for
state verbs).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 288 passed (was 277 + 11 new, now
`tests/test_mining_increment_35.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 21
info. Shipped NEUTRAL on dev: this narrow, structural fix is proven
directly by the synthetic suite (two/three-item conjunct recovery including
Oxford comma, 'own' variant, spelled-out numbers, coordinated-second-clause
decline-safety with and without a counted subject in the second clause,
negated-state-conjunction decline-safety, state-sibling-never-priced
decline-safety, purchase-conjunction non-regression, event-verb
non-regression) — no dev-train/dev-holdout item happens to need exactly
this shape without also hitting an unrelated, already-open gap (matches the
prior parked attempt's own finding).
TEST look #37: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 36: copular-priced items (`691aaec`)

Re-land of `mining/parked/copular-priced-items` (bfa484a), rebased onto
current main (`learn.py` drifted through increments 20-34, especially
increment 29's subject-side determiner-each for `price_verb`). Reimplemented
directly against the drifted `price_verb` branch rather than cherry-picked
from the parked commit.

Closes: "Tickets are $5 each. Ben buys 4 tickets. How much does Ben spend?"
used to decline entirely — the purchase Quantity folds, but the copular
price sentence (`be` is not a `price_verb`) emitted no Price fact at all:
`be` + a currency dobj followed by `each` fell into the `dobj_is_rate`
branch, computed a rate/each-price against the wrong counted unit (the
currency noun itself, not the subject), got `None` back, and silently
dropped the sentence with zero facts.

`learn.py` extends increment 15's subject-keyed Price emission (currently
gated on the `price_verb` category, i.e. cost/costs) to the `state`
category's `be`, structurally gated — no YAML change, no widening of
`price_verb`'s other consumers. The new branch fires only when
`verb_lemma == "be"`, the dobj is a currency-valued count noun, the SUBJECT
is a plural common noun (`sense == noun`, `number == plural` — the same
structural check `patterns.py` already uses for the `plural` slot type),
and the existing distributive-`each` structure holds (`_is_rate`/
`_rate_unit` reused UNWIDENED, exactly as increment 15 calls them).
Increment 29's `_has_distributive_determiner` alternative ("Each ITEM costs
$PRICE") is deliberately NOT extended to this branch: that shape requires a
SINGULAR subject ("each ticket"), which conflicts with this branch's
plural-subject gate — the two forms are structurally exclusive, not
overlapping. Any `be`+currency-dobj sentence missing a piece of this gate
(no `each`, singular subject, a "per NOUN" rate marker) falls through
untouched to the existing state-verb Quantity/Membership/Predication fold.
No `answer.py` change: the increment-10 purchase-total consumer already
matches Price facts to purchase quantities by item noun regardless of
emission site (increment 15 precedent).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged) — dev slices carry no copular-priced items themselves,
consistent with the parked branch's original result; pytest 296 passed (was
288 + 8 new, now `tests/test_mining_increment_36.py`), suite 52/52, lint 0
errors / 1 known-good warning (fraction-of-remnant / fraction-of-pool,
unchanged) / 21 info.
TEST look #38: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 37: definite-NP partitions (`54d60df`)

Re-land of `mining/parked/partition-of-noun`, redone from scratch against
current main (post increment-34) in a fresh worktree.

Adds two pattern rules — `arithmetic/partition-attribute-of-noun` and
`arithmetic/partition-membership-of-noun` — mirroring the existing
partition-attribute/partition-membership pronoun-form rules (increments
16/17), but with the collection slot as a definite plural NP ("the
marbles") instead of the pronoun placeholder ("them"). "The" is already a
SKIPPABLE article (never a literal), so the pattern is just
number-of-plural-noun-verb-attribute.

Since the collection noun IS the measure, resolution is either trivial or
unnecessary. `_partition_synth` in `saturate.py` already had an
"already names a real measure — nothing to resolve" early-continue (added
by a later increment), so the raw fact is left untouched with its original
(non-synth/partition) provenance — but two shared gates still recognized
"resolved" ONLY via the synth/partition provenance tag:

- `src/rulekit/kernel/guards.py`: the unresolved-derivation guard now also
  treats a PartitionQuantity as resolved when its `collection` already
  names a known measure directly, not only when its provenance is
  synth/partition. This is a structural, declared-fact-store check (never
  a rule-identity check), and is a pure superset of the old condition — the
  pronoun path is unaffected (verified: increment 16/17 coverage plus a new
  `test_pronoun_partition_unaffected_by_noun_form`).
- `src/rulekit/kernel/saturate.py`: `_partition_membership_synth`'s gate
  widens identically, so the definite-NP membership form also gets its
  companion Quantity synthesized (the general entity-less "how many NOUN
  are there" ask answers it, same as the pronoun form), with no bespoke
  consumer.

The partition-complement consumer and PartitionQuantity fact are reused
completely unchanged.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 303 passed (was 296 + 7 new, now
`tests/test_mining_increment_37.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 21
info. Shipped NEUTRAL on dev: as with the parked attempt, this nets 0 on
both dev slices in this corpus sample — the candidate brief's "0 partition
facts known" / "no quantity known" stats evidence turned out, on
inspection, to be rest-of-pool problems sharing the same generic
decline-reason string via `ask/how-many-partition`, not actual "N of the
NOUN are ADJ" premises. The mechanism is verified directly via synthetic
probes in the test file and is a legitimate, general class per the
constitution (a definite-NP sibling of an already-shipped pronoun-form
class).
TEST look #39: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 38: item-subject cost asks (`b2731c9`)

Adds `ask/how-much-item-cost` (`packs/arithmetic/rules/core.yaml`): "how
much do/does/did ITEM cost", extending the increment 10/15/29 price-fact
family to the ask side. The item is the grammatical subject of `cost`
itself, with no `who`/name slot at all, so the token order (aux, item,
price_verb) never collides with the how-much-noun-entity family, which
needs item-then-aux-then-name-then-verb. The verb slot is gated on the
EXISTING `price_verb` category (cost/costs, increment 15) rather than the
general `verb` type — no category widening.

Pairs with a new "item-cost" consumer in `answer.py`: the asked item's
unique Price fact times its unique purchased/held Quantity ("Priya buys 4
jackets at $6 each. How much do the jackets cost?" -> 24), or the bare unit
price when no such Quantity is in play ("Each hat costs $12. How much does
a hat cost?" -> 12, routed through `evaluate()` so the value-accounting
guard sees the price value as read). More than one Price fact or more than
one Quantity fact for the item is a genuine ambiguity and declines outright
— the increment 19/30 exactly-one-fact-or-decline discipline.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 309 passed (was 303 + 6 new, now
`tests/test_mining_increment_38.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 20
info. The ask matches "how much ... cost" questions in both dev slices but
every matching item needs a derived multi-step total rather than a stated
Price fact, so all decline safely — 0 net DEV gain, 0 harm; the mechanism
is verified directly via synthetic probes in the test file.
TEST look #40: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 39: leading temporal-clause questions (After/When X, question?) (`8fa68fc`)

Extends `engine.py`'s leading-clause split (the increment-12-adjacent
`_split_leading_clause` mechanism, pre-existing for literal `if`) with a
sibling `_split_leading_temporal_clause` that recognizes `when`/`after` as
leading temporal subordinators. The marker set is pack-driven, never a
Python word list: two new categories in
`packs/difg-mined/categories/clauses.yaml` (`clause_marker` rooted at
`conjunction` for `when`; `clause_marker_prep` rooted at `preposition` for
`after` — the two words carry different lexicon senses and can't share one
category root) are queried via `Registry.word_in_category`. The category
lives in difg-mined rather than core-english because `when`/`after` are
only lexically defined there; `conjunction` was added to `registry.py`'s
`ROOT_SENSES` tuple to let the new category root there (purely additive —
the sense was already a valid pattern-rule gate; no existing category or
word behavior changes). Mirrors increment 12's digit gate: only a clause
containing a stated digit is promoted to a premise, so a bare narrative
marker with no quantity ("When she got home, ...") is never mis-promoted.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 318 passed (was 309 + 9 new, now
`tests/test_mining_increment_39.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info. SOLVED is 0: a dev-train scan confirmed the split now correctly fires
on real leading when/after-clause items (e.g. "Tom's fruit bowl contains 3
oranges and 6 lemons. After Tom eats 3 of the fruits, how many fruits
remain..."), but each still declines for an unrelated missing capability
(remainder-ask shapes, vocabulary gaps) — pure groundwork this increment,
correctly scoped to the clause-split class only, 0 net DEV gain, 0 harm.
TEST look #41: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 40: wh-copular total asks (`33c66f7`)

Adds two additive ask ids to `packs/arithmetic/rules/core.yaml`:
`ask/what-total-combined` — "What is/was the total (number/amount of) ITEM
((that) they VERB)?", the wh-copula (`what` + `{cat: state}`: is/was/are/
were) FRONTING the aggregate word 'total' instead of trailing it the way
the existing `ask/how-many-combined` does ("how many X ... in total") —
and `ask/what-total-combined-contracted` for the "what's" clitic, kept
separate because `tokenize.py` never expands `'s` into a verb token (its
lexicon sense is possessive, not state), so widening the shared `state`
category to admit it would touch `ask/how-old-is` and every other
state-gated rule. Both route to the EXISTING `combined` consumer in
`answer.py`, byte-for-byte unchanged — same Sigma-over-holders fold
`ask/how-many-combined` already uses. No kernel edit, no new vocabulary
(`total`/`number`/`amount` already carry the aggregate/aggregate_noun
senses). The trailing subject clause is scoped to a bare pronoun ('they')
or omitted; a counted/named subject ("the two have") is out of scope by
brief and verified to decline safely (fails the `{type: pronoun}` slot,
then the pre-existing value-accounting guard vetoes the commit because
'two' is an unaccounted stated count) rather than falling through to a
new fallback path.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 325 passed (was 318 + 7 new, now
`tests/test_mining_increment_40.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info. SOLVED is 0: the junior's own scan of the 91 dev-train items matching
the brief's cue found every match is either a genuinely-derived total
(needs multi-step arithmetic the `combined` consumer intentionally doesn't
do) or a premise-side gap unrelated to this ask — pure groundwork this
increment, correctly scoped to the wh-copular ask-shape class only, 0 net
DEV gain, 0 harm. The mechanism is fully general and may still pick up
dev-holdout/test items with a simpler 2-holder-total shape outside this
half of dev-train.
TEST look #42: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 41: combined how-much totals (`1b287b2`)

Adds the how-much sibling of `ask/how-many-combined` to
`packs/arithmetic/rules/core.yaml`: "How much {item, e.g. money} [aux]
{who: pronoun} {verb} [prep] {agg: cat aggregate}?" — same shape as the
existing "how many X do they have altogether?" ask, with 'much' in place
of 'many', routed to the SAME unchanged `combined` consumer in
`answer.py` (Sigma over every entity holding the resolved measure).
Measure resolution for 'money' reuses the currency interchangeability
introduced by increment 26; no new vocabulary ('altogether'/'total'
already carry the aggregate sense in the core-english lexicon). The
who-slot is gated to a bare PRONOUN, which keeps this ask disjoint from
the crowded "how much" family with a NAME subject
(`ask/how-much-noun-entity`, `ask/how-much-bare-entity`,
`ask/how-much-money-entity-left`, earn-span, rate-span): a named subject
with a trailing 'in total' still routes to the single-entity ask, verified
directly in the test file, and a single-holder or mixed-currency combined
question declines via the combined consumer's own pre-existing guards
rather than guessing.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 331 passed (was 325 + 6 new, now
`tests/test_mining_increment_41.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info. SOLVED is 0: the ask-shape gap this closes exists on dev-train, but
no dev-train item's earlier read stage reaches this ask on the actual
corpus (an upstream premise gap intervenes first) — pure groundwork this
increment, correctly scoped to the "how much combined" ask-shape class
only, 0 net DEV gain, 0 harm. The mechanism is fully general and may still
pick up dev-holdout/test items with a simpler shape outside this half of
dev-train.
TEST look #43: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 42: wh-difference asks (`141e2a0`)

Adds `ask/what-is-the-difference-named` and its pronoun mirror
`ask/what-is-the-difference-pronoun` to `packs/arithmetic/rules/core.yaml`:
"what is/are/was the difference (in/between the number of) ITEM NAME and
NAME have?" and "...ITEM they have?", both routed to the EXISTING
`difference` consumer already shared with `ask/how-many-more` and
`ask/how-much-noun-more-than`. The named-pair form is pure YAML (a/b bind
directly, same as the existing asks, reusing the aggregate_noun+'of'
framing already established by `arithmetic/times-the-number-of`); the
copula gate reuses the established 'state' category (has/have/is/are/
was/were/own/owns), the same pattern `ask/how-old-is` already uses. The
pronoun form binds no a/b pair, so `answer.py`'s difference consumer
gained a small fallback mirroring the 'combined' consumer's holder
enumeration: it commits only when EXACTLY two entities hold the resolved
measure, and declines otherwise (the established exactly-one/
exactly-two-or-decline discipline) — no widening of `how-many-more`'s own
slots.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 14/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
15/0 unchanged), pytest 337 passed (was 331 + 6 new, now
`tests/test_mining_increment_42.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info. SOLVED is 0 on both dev slices — the class is verified via a direct
probe (Mia/Leo apples) and the suite, not by a dev-train/holdout hit;
groundwork only, 0 net DEV gain, 0 harm.
TEST look #44: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 43: currency-interchangeable relation measures (`df1146f`)

Adds two coordinated, general, kernel-structural pieces (no new vocabulary)
so "twice as much money as Cecil" resolves when the anchor states dollars:

1. `packs/arithmetic/rules/core.yaml` gains `arithmetic/times-as-much` and
   `arithmetic/fraction-as-much` — MASS-NOUN counterparts of the existing
   `times-as-many`/`fraction-as-many` Relation rules. The item slot swaps
   the literal 'many' for 'much' and `type: plural` for `type: noun` (the
   same slot type `times-the-number-of`/`affine-frame-relation` already
   use for their item slot) — mass nouns like 'money' carry no plural
   morphology, so the plural-gated rules never matched them before.
2. `src/rulekit/kernel/saturate.py`'s `_relations_synth` (`synth/relation`)
   now resolves a Relation's stated measure against its ANCHOR entity's own
   holdings the same way `answer.py`'s `_resolve_measure` has resolved ask
   nouns since increment 26: an EXACT measure match first, else — ONLY for
   categories marked `interchangeable` in the packs (today: currency
   alone) — the anchor's own UNIQUE same-category measure. An anchor
   holding two DIFFERENT currencies is genuinely ambiguous and declines,
   never guesses; a non-interchangeable category never resolves this way
   either (increment 26's sibling-borrow discipline, generalized to
   relations).

Gates (integrated on staging, full re-proof): dev-train diff SHIP +2 (0
BROKE, 0 DECL→WRONG; 3772 items, 14→16 correct, 0 wrong), dev-holdout diff
SHIP +1 (0 BROKE, 0 DECL→WRONG; 3701 items, 15→16 correct, 0 wrong), pytest
344 passed (was 337 + 7 new, now `tests/test_mining_increment_43.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged) / 22 info.
TEST look #45: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 44: pronoun-subject/common-noun single-entity asks (`a580fa3`)

Declared infrastructure (goal-mode exemption): widens the `who` slot from
`type: name` to `type: entity` (the type already proven on
ask/how-many-rate-span, ask/how-much-rate-span, ask/earn-span, and
ask/how-many-capacity) on TWO single-entity ask ids in
`packs/arithmetic/rules/core.yaml`, so a resolved pronoun subject ("how much
money does she have?") or a bare common-noun subject ("how much money does
the teacher have?") is recognized alongside the existing name subject:

  - `ask/how-much-noun-entity`
  - `ask/how-much-money-entity-left`

Two sibling ids named in the brief — `ask/how-many-entity` and
`ask/how-much-bare-entity` — were tried and DROPPED: widening them ties on
consumed-unit count with `ask/how-many-entity-possessed`/`-qualified` and
`ask/how-much-item-cost` respectively, and the alphabetical id tie-break in
`patterns.match_ask` then silently shadows those narrower asks — caught by
the EXISTING synthetic suite (`test_mining_increment_25.py`, `_34.py`,
`_38.py`), not by the dev diff (which stayed NEUTRAL throughout). Those two
ids are left unchanged at `type: name`.

Recognition-only: every dev-corpus question newly recognized by this widening
still declines downstream today on a premise gap (unresolved pronoun
antecedent, or an entity never stated to hold the asked measure) — this is
pure infrastructure for a follow-up class (pronoun/common-noun forms of the
money-left / purchase-total / entity-fold ask families) to cash in as those
premise gaps close in later batches.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 16/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
16/0 unchanged), pytest 350 passed (was 344 + 6 new, now
`tests/test_mining_increment_44.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info.
TEST look #46: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 45: conjoined event-verb objects (`98d782a`)

Declared infrastructure per the brief: extends increment 11's conjunct-
recovery walker (`_conjoined_purchase_items` in `learn.py`, previously gated
to `purchase` and `state` verbs) to any verb tagged with a polarity category
(acquire/lose and their subcategories: produce, receive, sell, ...). A new
`_has_event_polarity(verb_lemma, reg)` helper mirrors `answer.py`'s
`_sign(strict=True)` test at the fold layer: each comma/conjunction segment
in "found A and B" / "lost A, B, and C" now yields an ordinary signed event
Quantity for the same subject and verb, exactly like a purchase list's or a
state verb's siblings already did. An event verb with NO polarity tag
(`keep`/`retain`, `want`/`desire` — deliberately untagged) is unchanged: the
walker still never fires for it, so a stated sibling count stays unaccounted
and the value-accounting guard declines the whole sentence (the polarity
invariant). Only a purchase verb's own siblings ever emit a Price fact
(increment 11's discipline, untouched); a polarity-tagged non-purchase verb
never prices its siblings even when a segment carries a distributive "each"
plus a currency noun — that segment is left unaccounted and the sentence
declines rather than invent a price. The stop-on-verb + discard-segment-
on-verb-break discipline (increment 35) is preserved byte-for-byte since the
shared walker itself is untouched — only its callers' gating condition
widened.

Caught mid-development (increment 11 precedent): two existing decline-safety
tests (`test_mining_increment_11.py`, `test_mining_increment_35.py`) asserted
decline for an "eat"-verb ("lose" category) conjunction — that case now
correctly resolves to a number since `eat` IS polarity-tagged. Both were
updated to exercise `keep` ("retain" category, deliberately untagged)
instead, which still declines, so they keep documenting the real remaining
gap (untagged event verbs) rather than one this candidate now closes.

Recognition-only in the sense that matters for the campaign target: a
scripted conjunct-split rewrite over 64 dev-train conflict items found 0
immediate gold flips (their asks hit the pronoun-subject-entity gap closed by
increment 44) — this is pure infrastructure converting fold-conflict
DECLINEs into folded sums a future pronoun-entity-ask candidate can cash in.
Follow-up: re-mine the 113-item fold-conflict bucket next batch now that both
increment 44 (pronoun/common-noun asks) and this one (event-verb conjuncts)
have landed.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 16/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
16/0 unchanged), pytest 357 passed (was 350 + 7 new, now
`tests/test_mining_increment_45.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info.
TEST look #47: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 46: affine relation offsets (c more/fewer than k times as many X as Y) (`c2d7759`)

Re-cut of the parked branch `mining/parked/affine-relations` (1c749d0) against
current main: it had already gated dev-train SOLVED 4 / BROKE 0 / DECL->WRONG
0 with a clean NEUTRAL holdout, and deferred only on a core.yaml insertion
conflict with increment 43 (now on main). This lands worklist directive 0
("TOP SEED... re-cut against current main first; expect +4 corrects").

Pure YAML: two new pattern rules in `packs/arithmetic/rules/core.yaml` —
`arithmetic/affine-times-as-many` and `arithmetic/affine-fraction-as-many` —
extend the existing times-as-many / fraction-as-many ratio family (the bare
"as many ITEM as STD" frame) with the anchored-relation offset prefix ("N
more/fewer than"), mirroring how `affine-frame-relation` already prefixes the
"the number of" frame: subject = ratio*standard + n*sign(dir). No kernel
changes — the Relation fact's `offset` field and saturate.py's forward/inverse
resolution (subject = factor*standard + offset; standard =
(subject - offset)/factor) already existed and are reused unchanged. Offset
sign comes from the existing `more_dir`/`less_dir` polarity categories in the
core-english lexicon, never a Python word list.

Tests rewritten from a blank file against synthetic names/quantities (Duncan,
Priyanka, Odalys, Beckett, Marisol, Tobias, Fenwick, Rosalind) — no GSM8K
substring reuse.

Gates (integrated on staging, full re-proof): dev-train diff SHIP +4/0/0
(3772 items, 14->18 corrects: 47dd39ea4382, 4a1c79e953f6, 683e8e1debaa,
cd7158be4a8a), dev-holdout diff NEUTRAL 0/0/0 (3701 items, 16/0 unchanged),
pytest 364 passed (was 357 + 7 new, now `tests/test_mining_increment_46.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged) / 22 info.
TEST look #48: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 47: parenthetical unit-qualified questions (`, in dollars,` / `, in minutes,` mid-question)

Lands worklist goal-mode directive 1 (mine the "no ask shape recognizes this
question" bucket by surface shape). 89 dev-train declines contain a mid-
question `, in UNIT,` parenthetical (dollars 42, minutes 11, hours 6, seconds
5, ounces 5, ...), 81 of them inside the dominant 2495-item no-ask-shape
bucket. Minimal pair verified the mechanism directly: "Randy has 10 dollars.
Smith gives him another 4 dollars. How much money does Randy have?" commits
14.0; inserting ", in dollars," into the identical question text declined
no-ask-shape before this change.

YAML-only: an optional `[in, req_unit]` group (comma literals + "in" literal
+ a unit/currency-sensed noun slot — grammatical skeleton, no new vocabulary)
added to `ask/how-much-noun-entity` and `ask/how-much-money-entity-left` in
`packs/arithmetic/rules/core.yaml`. When bound, `answer.py`'s single-entity
and money-left consumers check the bound unit against the measure they
actually resolve and decline on mismatch (asked one unit, facts state a
different non-interchangeable one) instead of committing in the wrong unit.
No kernel changes were needed — mid-pattern optional groups were already
supported in `patterns.py`. Re-checked the increment 44 shadowing lesson:
widening these two ask ids does not change their consumed-unit specificity
relative to the other ~25 asks (no new ties).

Gates (integrated on staging, full re-proof): dev-train diff SHIP +1/0/0
(3772 items, SOLVED 4085a62be26e), dev-holdout diff NEUTRAL 0/0/0 (3701
items, 16/0 unchanged), pytest 368 passed (was 364 + 4 new, now
`tests/test_mining_increment_47.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info.
TEST look #49: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 48: chained inverse relation resolution / multiplicative age comparatives (`8c08859`)

Candidate investigated the goal-mode "no quantity known" bucket's 2-hop
chain items (Thor/Captain America/Peter Parker ages; Kyle/Julian/Frederick/
Tyson ages). The proposed mechanism (extend `saturate.py`'s
`_relations_synth` to a fixed point so an inverse hop could consume a
derived, not only stated, quantity) turned out to already exist:
`saturate()`'s round-based loop already re-invokes `synth/relation-to-
quantity` each round against the store as it stood after the previous
round's admissions, so N-hop chains over already-supported relations (e.g.
"times as many") already resolve with zero code change (regression-checked
here, `test_two_hop_forward_as_many_chain_unaffected`, so a future
saturate.py edit can't silently narrow the fixpoint back to one hop
unnoticed).

The actual gap was a missing EXTRACTION rule: "X is N times older/younger
than Y" (a multiplicative age comparative with no stated noun) never
produced a Relation fact at all — unlike the additive "X is N years older
than Y" form, which already condenses a counted item via anchored-
relation-postfix. Fix, YAML-only:

- new `age_comparative` category (`packs/core-english/categories/core.yaml`,
  parent `comparative`, a SIBLING of `delta` — not a member, so general
  magnitude comparatives like "faster" don't inherit an implicit year
  measure), members `older`/`younger` tagged in `packs/difg-mined/
  categories/semantic.yaml`.
- `arithmetic/times-comparative-age-relation` (`packs/arithmetic/rules/
  core.yaml`): "WHO is K times {older|younger} than STD" emits the same
  Relation fact shape as every other relation rule in the file (factor =
  k**sign(dir), measure='year', offset=0). No consumer or kernel change;
  the existing single-entity ask, additive relations, and saturate.py
  fixpoint all compose with it unchanged (verified on a 3-hop mixed
  additive+multiplicative chain, 60 -> 48).

No dev-train item is resolved by this rule ALONE: the traced Thor/Captain
America items also carry a trailing-if-clause extraction gap (variant of
increment 12's split) and/or a bare no-noun age-statement gap, both scoped
out as separate follow-up candidates per the one-class-per-increment
discipline.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 21/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
16/0 unchanged), pytest 376 passed (was 368 + 8 new, now
`tests/test_mining_increment_48.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 22
info.
TEST look #50: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 49: future-modal factual asks (will/would-phrased questions over ordinary state/event folds) (`64b2053`)

Lands worklist goal-mode directive 1 (mine the "no ask shape recognizes this
question" bucket). Fresh stats over that bucket (2,481 dev-train declines):
486 contain will/would in the question's final clause. Minimal pair verified
the mechanism directly: "Tom has 12 dollars. He spends 4 dollars. How much
money does Tom have left?" commits 8.0, and the identical text with "will Tom
have left" declined no-ask-shape before this change — premises read, fold
produces gold, only the ask gate differed.

No new committer — reuses the four existing factual-ask consumers unchanged:

- new `future_modal` category (`packs/core-english/categories/core.yaml`,
  parent `modal`); `'modal'` added to `registry.ROOT_SENSES`
  (`src/rulekit/data/registry.py`) purely additively, mirroring the earlier
  `conjunction` root-sense addition, so the category can resolve. Both
  members (will/would) are difg-mined-only words and so are declared in
  `packs/difg-mined/categories/semantic.yaml` instead, mirroring the
  `negation`/`never` precedent.
- new `future_modal` slot type (`src/rulekit/data/schemas.py` SLOT_TYPES,
  `src/rulekit/kernel/patterns.py` `_slot_ok`, mirroring increment 19's
  `modal` type): matches an auxiliary-sense token OR a modal-sense token
  whose word is in `future_modal`. The other six modal-sense words
  (can/could/should/may/might/must — capacity/hypothetical modals) are NOT
  members, so `ask/how-many-capacity`'s own territory is untouched — the
  increment-14 kirsty lesson (a wanted/hypothetical purchase is not a
  purchase) cannot recur through this slot.
- applied to exactly four existing ask ids' `aux` slot
  (`packs/arithmetic/rules/core.yaml`): ask/how-many-entity,
  ask/how-much-money-entity-left, ask/how-much-noun-entity,
  ask/how-many-combined. Every other auxiliary-gated ask (~14 others) is
  byte-for-byte unchanged, per the no-blanket-widening invariant.

Ask-specificity ordering vs `ask/how-many-capacity` was verified explicitly
(per the brief's risk note): `ask/how-many-entity`'s widening ties exactly
with `ask/how-many-capacity` on consumed-unit count for any "how many ITEM
will/would WHO VERB" sentence, and `match_ask`'s deterministic id-order
tie-break keeps capacity winning ("ask/how-many-capacity" sorts before
"ask/how-many-entity") exactly as it already did before this change
("How many marbles can Tom have?" and its 'will' variant both still decline
via capacity's "0 price facts known"). The other three widened asks use a
different leading literal or an aggregate-category token and never collide
with capacity at all.

No dev-train item is resolved by this rule alone (0 SOLVED both slices) —
of 776 will/would-containing dev-train items scanned (scratchpad, not
committed), 38 moved from "no ask shape recognizes this question" to a
specific downstream decline reason, confirming the ask-shape gap is closing
even where the item also needs unrelated machinery correctly left out of
scope (compound interest, discounts, multi-service revenue, deposits-over-
time) — the same "shipped NEUTRAL, safe infrastructure" pattern as roughly
a dozen prior increments in this campaign.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 21/0 unchanged), dev-holdout diff NEUTRAL 0/0/0 (3701 items,
16/0 unchanged), pytest 383 passed (was 376 + 7 new, now
`tests/test_mining_increment_49.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 23
info.
TEST look #51: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 50: question-supplied-quantity pay/spend cost asks (`how much did WHO pay/spend for/on N ITEM`)

Lands part of worklist goal-mode directive 3 ("spend/pay event asks
66+44" + "0 price facts known 143"). Fresh stats: "no spend events known" 67
+ "no pay events known" 45. Probe-verified the mechanism directly: "Shirts
cost 5 dollars each. How much did Tom pay for 4 shirts?" declined "no pay
events known" before this change — the Price fact emits fine (increment
15/29/36 machinery), but the ask routed to the real-event fold instead of
N x price.

Note: the brief also proposed a sibling no-buyer surface ("how much does it
cost to buy N ITEM"); the implementer DROPPED that half after discovering
'cost' is a noun/verb homograph (charge-category noun vs `price_verb`) and a
trailing purchase infinitive gives the infinitive's own verb a second viable
subject candidate (the noun reading of 'cost', nearer than the pronoun
'it') — this ties `obligations.py`'s disambiguation score between 'cost's
two readings for every instance of that surface form, so the guard vetoes
any commit regardless of ask/consumer design. That half is out of scope here
(a shared disambiguation tie-break fix, not this candidate's files) and is
noted as a future mining candidate. Only the pay/spend-for-quantity ask
below actually shipped.

New ask `ask/how-much-pay-for-quantity` ("how much did WHO pay/spend for/on N
ITEM", `packs/arithmetic/rules/core.yaml`; the `spend_verb` category has
existed since increment 10) consumes the question's own stated N
(`{qty.value}` marked pattern-consumed, mirroring the rate-span
`{span.value}` precedent — never an existing Quantity fact). New narrow
category `spend_target_prep` (`packs/difg-mined/categories/semantic.yaml`,
parent `preposition`, members for/on) scopes the ask's trailing preposition
so it can never also match 'in', which `ask/how-much-rate-span` and
`ask/earn-span` already reserve as a literal for their own SPAN clause — a
general `preposition` gate would tie those asks on consumed-unit count for
"how much did WHO pay IN N months" and let alphabetical id order silently
mis-route a span question. New `cost-of-quantity` consumer in `answer.py`
commits N times the item's UNIQUE per-unit Price fact (increment 19's
exactly-one-Price discipline), declining on zero/multiple Price facts, on a
cost-splitting predicate touching the buyer (increment 10's invariant,
reused verbatim), or on a pre-existing Quantity of the same item for the
same buyer (ambiguous against the question's own count).

Verified: the pre-existing bare "how much did WHO pay" ask (no trailing
"for/on N ITEM" clause) keeps winning via the real purchase total when there
is no question-supplied quantity to consume, and "how much did WHO earn/pay
in N months" keeps routing to the rate-span/earn-span family untouched.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 21/0 unchanged — no matching items in this dev-train sample),
dev-holdout diff NEUTRAL 0/0/0 (3701 items, 16/0 unchanged), pytest 390
passed (was 383 + 7 new, now `tests/test_mining_increment_50.py`), suite
52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged) / 22 info.
TEST look #52: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 51: inverse rate-span (duration) asks (`how long / how many
TIMEUNIT does it take WHO to VERB N ITEM` = amount ÷ rate)

Lands HANDOFF's "Rate chaining" bullet (the 10-hours-over-5-days item
"needs an hours-per-day division the bridge doesn't synthesize") plus
goal-mode directive 1 / "0 rates known" 22 in fresh stats. Fresh stats: 41
no-ask-shape declines match "how long ... take" + "no take events known" 14
(probe showed "How many hours does it take Tom to read 20 pages?"
mis-routing there). Probe-verified the forward half already works — "Tom
reads 5 pages per hour. How many pages does Tom read in 3 hours?" commits
15.0 via the existing rate-span consumer reading the Rate fact forward —
the inverse question ("How long does it take Tom to read 20 pages?")
declined "no ask shape" with the identical premises. Only the ask forms and
the inverse division were missing.

Two new ask ids in `packs/arithmetic/rules/core.yaml`:
`ask/how-long-take-span` ("how long does/did it take WHO to VERB N ITEM?" —
the span is implicitly in the rate's own per-unit) and
`ask/how-many-timeunit-take-span` ("how many TIMEUNIT does/did it take WHO
to VERB N ITEM?" — the named time unit must match the committing rate's
per-unit or the ask declines). Both route to a NEW, additive
`rate-span-inverse` consumer in `answer.py`; the existing forward
`rate-span` consumer/branch (shared with increments 8/9/13/21) is untouched
byte-for-byte — confirmed by the zero-diff dev-train/dev-holdout re-gate
below. The inverse branch requires a UNIQUE Rate whose measured item
matches the asked item (same unique-rate-or-decline discipline as the
forward branch) and reads its value only through the shared arithmetic-log
accounting (the look #4-#7 lesson on leaky accounting in this same
consumer family). Scoped OUT: will-phrased forms ("how long will it take",
most of the raw 41) stay with `will-tense-asks` (increment 49) to keep the
two ask families disjoint — only bare aux does/did + "how long does" is
matched here.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 21/0 unchanged — no matching items in this dev-train sample),
dev-holdout diff NEUTRAL 0/0/0 (3701 items, 16/0 unchanged), pytest 399
passed (was 390 + 9 new, now `tests/test_mining_increment_51.py`), suite
52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged) / 22 info.
TEST look #53: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 52: average asks (`what is/was the average number of X
they VERB` = combined total ÷ holder count)

Lands goal-mode directive 1 (ask-shape bucket). Fresh stats: 70 of the
2481 no-ask-shape declines contain "average" (12 exact "average
number/amount of"; 8 "what is the average" + 7 "what was the average"
prefix buckets). Probe-verified: "Tom scored 3 points. Mary scored 9
points. What is the average number of points they scored?" declined
no-ask-shape while the combined machinery already enumerates the same
holders ("What is the total number of apples they have?" commits Sigma
over [mary, tom] — increment 40/41).

New ask shapes "what is/was the average number|amount of ITEM (they)
VERB" in `packs/arithmetic/rules/core.yaml`, strictly more specific than
`ask/what-total-combined` (increment 40) via the "average" token —
confirmed non-disturbing to that ask's own matching by the zero-diff
re-gate below. A new, narrow `average` consumer in `answer.py` reuses the
combined-total consumer's own holder-enumeration helper UNCHANGED (>=2
unambiguous holders each resolving a single value for the measure, same
state/event-verb fallback, same decline-on-ambiguity discipline) and
divides by the holder count. No new fact kind. `average`/`averaged`/
`averages` were already lexiconed (packs/difg-mined/lexicon/a-f.yaml,
sense "aggregate", not quarantined); moved alongside `total`/`combined`
so condense.py's general NOUN+NOUN merge-compound pass never eats it into
an "average number" compound before the ask pattern sees a separate
`average` token. Scoped OUT: any weighted-average cue ("per", rates in
play) and time-series phrasing ("average per day") — declined, out of
class.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL
0/0/0 (3772 items, 21/0 unchanged), dev-holdout diff SHIP +1/0/0 (3701
items, 16->17 correct, 0 wrong — SOLVED 076eae6e029a), pytest 409 passed
(was 399 + 10 new, now `tests/test_mining_increment_52.py`), suite 52/52,
lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged) / 22 info.
TEST look #54: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 53: comma-less trailing conditional clauses (`"How old is X
if Y is N years old?"` with no comma anywhere in the question)

Lands the comma-less half of the trailing-if-clause gap that increment 12
only closed for the comma-anchored form. Fresh stats: "no ask shape
recognizes this question" = 2419 of 3751 dev-train declines; scratchpad
scan found 83 currently-declining questions ending in a trailing ` if
<clause containing a digit>` with NO comma anywhere, so increment 12's
`_split_trailing_clause` (comma-anchored) never fires on them. Full-chain
verified on 2 of the 83 (the rest decline downstream, correctly out of
scope): an age-relation chain resolving through the increment-46/48
relation machinery, and a combined-items item resolving through the
increment-40/41 combined-total machinery.

`_split_trailing_clause` (`src/rulekit/kernel/engine.py`) gets a
comma-less fallback: only when the existing comma-anchored split finds NO
split at all does it fall back to splitting at the LAST ` if ` token
boundary of the question sentence, strip the trailing `?`, and promote
the clause to a premise. Both of increment 12's safety gates are
preserved verbatim: the fallback only runs when nothing else has already
split the question, and only when the promoted clause carries a digit
(a bare narrative tail like "... to see if that works?" is never
promoted). `if` remains a grammatical-skeleton literal, identical to its
use in increments 12/39 — no word list enters Python. The pre-existing
comma-anchored path is untouched byte-for-byte.

Gates (integrated on staging, full re-proof): dev-train diff SHIP +2/0/0
(3772 items, 21->23 correct, 0 wrong — SOLVED 123c7d57d7e0, a29f36cb3fd0),
dev-holdout diff NEUTRAL 0/0/0 (3701 items, 17/0 unchanged), pytest 418
passed (was 409 + 9 new, now `tests/test_mining_increment_53.py`), suite
52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged) / 22 info.
TEST look #55: 6/1 (85.7%) — precision HELD, increment kept.

## Increment 54: named-pair combined holdings asks (`"how many/much X do(es)
A and B have together/altogether/in total"`)

Re-cut of the parked `mining/parked/named-pair-combined` branch against
current main (blocked only for two docstring quotes containing GSM8K text;
every assertion in the landed test file is synthetic — invented names,
never reused from the parked branch's evidence or the brief). Fresh stats:
"no ask shape recognizes this question" = 2420 of 3749 dev-train declines;
scratchpad scan found 10 shaped "how many/much X do(es) A and B have
together/altogether/in total" where the existing combined asks only bind
a pronoun subject ("they"/"we"), never a named pair.

Two new ask ids in `packs/arithmetic/rules/core.yaml` —
`ask/how-many-combined-named` and `ask/how-much-combined-named` — mirror
`ask/how-many-combined`/`ask/how-much-combined`'s shape (item, aux,
aggregate tail) but bind the two named holders directly via `a`/`b` slots
joined by "and", the same named-pair binding `ask/what-is-the-difference-
named` (increment 42) already uses. Both route to the existing "combined"
consumer, `answer.py`'s `_combined_holder_totals`, additively extended:
when `a`/`b` are bound it sums EXACTLY those two named holders — a third,
unnamed holder mentioned elsewhere in the passage can never inflate the
sum. The pronoun path (and the increment-52 average consumer that reuses
the same helper) is untouched byte-for-byte.

Gates (integrated on staging, full re-proof): dev-train diff SHIP +3/0/0
(3772 items, 23->26 correct, 0 wrong), dev-holdout diff SHIP +1/0/0 (3701
items, 17->18 correct, 0 wrong), pytest 424 passed (was 418 + 6 new, now
`tests/test_mining_increment_54.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) /
22 info.
TEST look #56: 7/1 (87.5%) — a TEST coverage GAIN, increment kept.

## Increment 55: modal how-long / how-many-TIMEUNIT duration asks (`91a76e0`)
(will/would-phrased inverse rate-span questions)

Lands HANDOFF's "next mining worklist" TOP SEED (b): increment 51 shipped
the bare-aux ("does/did it take") forms of the inverse rate-span duration
asks but explicitly scoped OUT will/would-phrased forms as a separate
candidate — this closes that gap, mirroring increment 14's aux/modal
split. Fresh dev-train stats: 104 declining questions match "how long|how
many hours/minutes/days/weeks/months/years will|would"; 48 of the "0 price
facts known" reasons are time-unit capacity mis-routes (increment 51's
sibling `ask/how-many-capacity` claims the will/would modal slot and
declines on no Price fact instead of routing to duration). Full chain
traced on a synthetic minimal pair: "Tom reads 5 pages per hour. How long
does it take Tom to read 20 pages?" commits via rate-span-inverse; the
identical premises with "will it take" declined no-ask-shape, and "How
many hours will it take" declined "0 price facts known for hour".

YAML-only: adds future_modal variants of increment 51's two ask ids
(`ask/how-long-take-span`, `ask/how-many-timeunit-take-span`) in
`packs/arithmetic/rules/core.yaml`, gating the aux position on the
existing `future_modal` slot type (increment 49; will/would only —
can/could/should/may/might/must stay with capacity, same discipline
increment 49 established). Both route to the existing rate-span-inverse
consumer in `answer.py`, byte-for-byte unchanged — no new consumer, no new
fact kind. Ask-specificity vs `ask/how-many-capacity` (which also gates a
will/would-capable modal slot) is resolved the same way increment 51
resolved it against the bare-aux forms: the expletive 'it'/'take'/'to'
skeleton this ask requires either fails capacity's `who, type: entity`
slot outright or loses on consumed-unit specificity, so a genuine
capacity question ("how many hours will Tom read?") still only matches
`ask/how-many-capacity`.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 26/0 unchanged — no matching items in this dev-train sample),
dev-holdout diff NEUTRAL 0/0/0 (3701 items, 18/0 unchanged), pytest 434
passed (was 424 + 10 new, now `tests/test_mining_increment_55.py`), suite
52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged) / 22 info.
TEST look #57: 7/1 (87.5%) — precision HELD, increment kept.

## Increment 56: change asks (`"how much change does/did/will WHO get/
receive (back)"` = stated tender minus purchase total)

Fresh snapshot scratchpad scan: 19 declining dev-train items contain "how
much change" (18 no-ask-shape, 1 fold-conflict); leading-trigram "how much
change" 11. Full chain traced on a synthetic paraphrase before committing
to the mechanism: "Tom buys 3 shirts at 5 dollars each. He pays with a 20
dollar bill. How much did Tom pay?" commits 15.0 via purchase-total with
the tender sentence present and harmless — premises read, the purchase
total folds gold, only the change ask + tender-minus-total arithmetic were
missing.

New ask shape `ask/how-much-change` in `packs/arithmetic/rules/core.yaml`,
gated on the literal "change" — given a new noun sense alongside its
existing verb sense in `packs/difg-mined/lexicon/a-f.yaml` (mirrors
"cost", an existing noun+verb dual-sense word; `disambiguate()`'s general
obligation-coverage arbitration picks the noun reading, no code change).
Includes the future_modal aux variant from day one (will/would-phrased),
per the increment-49 precedent — most real items are will-phrased.
Routed to a new "change" consumer in `answer.py`: the buyer's stated
TENDER minus the SAME priced-purchase total the money-left consumer
already uses (`_purchase_total`, reused UNCHANGED — the increment-10
invariant travels with it unscoped: any unpriced purchase, or a "splits
the cost" predicate on the buyer, declines the whole total).

The tender itself needed NO new fact kind and no `learn.py` change:
"pays $50" / "pays with a $50 bill" / "gave $250 [to X]" already produce a
plain currency Quantity EVENT via the existing general SVO fold today. A
new `tender_verb` category (pay/give — `packs/difg-mined/categories/
semantic.yaml`) just lets the change consumer name that event
specifically, gated additionally on the fact's measure resolving to
`currency`. No unique stated tender -> decline (more than one, or none, is
a genuine ambiguity); negative change -> decline.

Two decline disciplines beyond straight reuse, both found by probing real
dev-train shapes before locking the mechanism:
- unlike money-left, a change ask presupposes a purchase actually
  happened, so "no priced purchase found" declines rather than defaulting
  spend to 0 — money-left's fallback would otherwise manufacture a wrong
  change amount here.
- a discount/tip predicate on the buyer (semantic.yaml's `discount`
  category, extended with 'tip'/'tips' — previously an unreferenced pack
  category, this is its first kernel consumer) declines, generalizing
  increment 10's single "splits the cost" verb check to a dobj category.

Scope: only tender-as-separate-clause shapes ("She paid $200 for X." /
"He paid with a $50 bill.") are covered — a leading "If X paid $N, how
much change..." conditional-question clause and ditransitive "gave the
cashier $N" (no preposition) are out of scope and stay declined;
'cashier' is deliberately NOT admitted as vocabulary here (a separate,
dedicated vocabulary-admission increment per methodology §4's one-word
discipline). 'change' and 'bill' were already lexiconed and not
quarantined; 'banknote' IS quarantined and was not touched.

Gates (integrated on staging, full re-proof): dev-train diff SHIP +1/0/0
(3772 items, 26->27 correct, 0 wrong), dev-holdout diff NEUTRAL 0/0/0
(3701 items, 18/0 unchanged), pytest 445 passed (was 434 + 11 new, now
`tests/test_mining_increment_56.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) /
23 info.
TEST look #58: 7/1 (87.5%) — precision HELD, increment kept.

## Increment 57: conjoined full-clause holdings (multi-clause premise (`3b4c332`)
sentences, one NAME subject per clause) (`6826419`)

Fourth landing attempt for this mechanism (`mining/parked/conjoined-clause-
holdings`, `840493c`) — gated NEUTRAL clean three prior times but blocked in
batch 14 on one remaining test-contamination finding: the Priya/Odell/Mabel
"54 pencils / 45 pencils" scenario was a name/item-swap of GSM8K dev-train
item "John has 54 pieces of gum, Cole has 45 pieces of gum and Aubrey has
no pieces of gum" (same two numbers, same three-clause "X has N ITEM"
shape). This re-cut fixes ONLY that hygiene finding — every scenario in the
test file and every matching docstring example in `engine.py` rewritten
with fresh names/numbers/items/structure (Nadia/Owen/Farah stickers;
Milo/Petra shells; Callum/Soraya fences; Idris/Wren/Talon/Yusuf boxes and
folders; Owen's ribbons/notebooks/bracelets purchase list; Petra/Callum/
Soraya races; Yusuf/Idris/Wren ages), each number-pair grepped against the
parquet before committing. Mechanism is byte-identical to `840493c`.

Class: a premise sentence coordinating multiple FULL clauses at the top
level, each with its OWN NAME subject and finite state/event verb ("Nadia
has 17 stickers, Owen has 29 stickers and Farah has 8 stickers.") —
previously only the FIRST clause folded (the verb->dobj obligation binds
once per sentence), so every subsequent conjunct's own subject/verb/number
was silently dropped. This is the CLAUSE-conjunction sibling of the
NP-conjunction walkers (increments 11/35/45, which recover extra sibling
ITEMS for the SAME subject) — distinct because here each conjunct
introduces a NEW subject.

Mechanism: a structural pre-split in `engine.py`
(`_split_conjoined_clauses`), ahead of any fold machinery — every
top-level ','/'and' boundary in a premise is a candidate clause boundary.
A boundary only splits when (1) the accumulated head is ALREADY a
complete clause with its own registered state/event verb
(`_has_finite_verb`) — telling a genuine clause boundary apart from a bare
compound-subject fragment ("Callum" in "Callum and Soraya paint 12 fences
over the weekend") — and (2) the candidate remainder opens with a NAME
subject (small compounds like "Talon and Yusuf" tolerated) reaching a
finite state/event verb with nothing else between (`_clause_finite_verb`)
and stating its own digit. Comparative/ratio clauses ("N more/fewer ITEM
than Y", "N times as many X as Y") are deliberately out of scope
(`_is_relational_clause`) — `than`/`times` recognized via the new
`relational_marker`/`multiplier_marker` categories (`packs/core-english`,
`packs/difg-mined`), never a Python word list. Does not touch
`_conjoined_purchase_items`/`_is_rate`/`_price_each_value` (increment 11's
existing NP-conjunction walkers) — a purely textual pre-split that runs
before any of that fold machinery sees the text.

Files: `src/rulekit/kernel/engine.py`, `packs/core-english/categories/
core.yaml`, `packs/difg-mined/categories/semantic.yaml`,
`src/rulekit/data/registry.py` (a `particle` root-sense addition),
`tests/test_mining_increment_57.py` (14 synthetic tests — clause-boundary
splitting, compound-subject/compound-object-tail non-boundaries, relative/
complementizer clauses, relational-clause and no-digit declines, and
non-interference with increments 11/35/45). `tests/test_mining_increment_
35.py` and `_45.py` carry forward only their own pre-existing, already
TEST-gated assertion updates from `840493c` — untouched otherwise by this
landing.

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 27/0 unchanged from baseline — infrastructure increment, no
new SOLVEs expected), dev-holdout diff NEUTRAL 0/0/0 (3701 items, 18/0
unchanged), pytest 459 passed (was 445 + 14 new, now
`tests/test_mining_increment_57.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
TEST look #59: 7/1 (87.5%) — precision HELD, increment kept.

## Increment 58: compound rate premises (`VERB N ITEM in T UNIT` feeding
rate-span/rate-span-inverse) (`6c7b357`)

Re-cut/reland of the parked `mining/parked/compound-rate-recut` (`bf93fbd`)
lineage named as top-seed (a) in batch 15's worklist. Rebased onto current
main (past increment 57) and re-gated from scratch on staging; the cherry-pick
landed with NO core.yaml conflict against increment 57's `relational_marker`/
`multiplier_marker` insertions (the candidate branch had already been rebased
past that point before hand-off) — no manual conflict resolution was needed
at integration time.

Class: a premise stating an amount over an elapsed span with TWO numbers
("Priya bakes 8 muffins in 4 minutes") — distinct from the existing per-unit
article form ("4 cars a day", `_rate_unit`) which recognizes only a SINGLE
stated number. Before this increment such a premise built NO Rate fact at
all, so a paired rate-span/rate-span-inverse question declined "0 rates
known" even though the ask ids and consumers were already live (increments
8/9/13/21/51/55).

Mechanism: `learn.py`'s `_compound_rate_span` recognizes the "N ITEM in T
UNIT" shape (scanning forward from the counted dobj for a pack-declared
`span_preposition`-category token — parent: preposition, members: [in],
`packs/core-english/categories/core.yaml` — introducing its own counted
noun; an intervening non-span prepositional frame is skipped, not treated as
ending the scan) and emits a Rate fact carrying both the derived per-unit
`value` and the two raw stated numbers (`Rate.numerator`/`denominator`,
`model.py`) — the split exists so `guards.py`'s value-accounting credits the
text's own two numbers as read only when a consumer's arithmetic actually
uses them (the look #4-#7 existence-vs-use invariant), never merely because
the Rate fact exists. `answer.py`'s existing `rate-span` (forward) and
`rate-span-inverse` consumers each gain a numerator/denominator branch: a
compound Rate divides/multiplies through its own raw stated numbers directly,
answering honestly, value-accounted, in EITHER direction, under EITHER
auxiliary or modal (increment 55) question phrasing. The plain (non-compound)
Rate path in each consumer is untouched.

Files: `src/rulekit/kernel/learn.py`, `src/rulekit/kernel/answer.py`,
`src/rulekit/kernel/guards.py`, `src/rulekit/kernel/model.py`,
`packs/core-english/categories/core.yaml`, `tests/test_mining_increment_58.py`
(6 synthetic tests — forward span, modal inverse own-per-unit, modal inverse
matching asked unit, an unrelated "in her closet" phrase correctly NOT
misread as a compound rate, no-rate-at-all decline, and an intervening
non-span prepositional frame correctly skipped rather than ending the scan).

Gates (integrated on staging, full re-proof): dev-train diff SHIP +1/0/0
(3772 items, 27->28 correct, 0 wrong; SOLVED 6bc7c26d8dd9), dev-holdout diff
NEUTRAL 0/0/0 (3701 items, 18/0 unchanged), pytest 465 passed (was 459 + 6
new, now `tests/test_mining_increment_58.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged) / 26
info.
TEST look #60: 7/1 (87.5%) — precision HELD, increment kept.

## Increment 59: future-modal spend/pay asks + measure-of-item price emission (`827e68d`)
(`a pound of coffee beans costs $2.50`) (`3bcc76f`)

Reland of the parked `mining/parked/modal-spend-measure-price` (`92183a9`)
lineage named as top-seed (a) in batch 15's worklist, alongside increment 58.
Rebased onto current main and re-gated from scratch on staging; the cherry-
pick landed with NO conflict against increment 58's compound-rate insertions
(a single-block union merge in `core.yaml` against an unrelated
`relational_marker` category landed earlier in the batch) — no manual
conflict resolution was needed at integration time.

Class: future-modal spend/pay asks ("how much will/would WHO pay?") PAIRED
with the payoff that unlocks them on partitive-priced text: a `price_verb`
statement whose subject is "a MEASURE of ITEM" ("a pound of coffee beans
costs $2.50", "4 pounds of coffee beans cost $10 each"). Before this
increment such a premise built NO Price fact at all (declined "0 price
facts known", frequency 136 in the fresh stats scan).

Mechanism: two coordinated pieces.
1. Ask widening (mirrors increment 49 exactly, no consumer changes): the
   `aux` slot on `ask/how-much-bare-entity` and `ask/how-much-pay-for-quantity`
   widens from `type: auxiliary` to `type: future_modal`
   (`packs/arithmetic/rules/core.yaml`) — "how much will/would WHO pay (for
   N ITEM)?" now recognized alongside the ordinary do/does/did form.
2. Price emission (`src/rulekit/kernel/learn.py`): a price_verb's subject
   binds through the existing partitive 'of' preposition to the ITEM noun
   (the of-object) — but the price is stated PER the MEASURE noun the 'of'
   phrase anchors to ('pound'), not per item. A new `_measure_partitive_anchor`
   helper finds that measure noun structurally: a `partitive`-category
   preposition (new category, `packs/core-english/categories/core.yaml`,
   exactly one member 'of') whose object is the subject, and whose anchor
   names a KNOWN physical measure unit (`reg.conversions` — data-driven,
   never a Python word list). The emitted Price is keyed on that measure
   noun, not the item, lining up with the purchase premise's own
   `Quantity.measure` (unwidened since increment 10) with zero changes to
   `_purchase_total`. A bare (uncounted) measure anchor is itself the
   per-unit signal ("a pound"); a counted anchor ("4 pounds") still needs
   the existing 'each'/distributive trigger.

A pre-existing rule collision is also fixed: `arithmetic/partition-
membership-of-noun`'s `verb` slot narrows from the general `type: verb` to
`cat: state` — a membership partition is always copular ("N of the X ARE
Y"); the unrestricted slot let it swallow an unrelated priced-measure
sentence sharing the same token order ("4 pounds of coffee beans COST 10
dollars each"), stealing it from the price-verb emission before it could
run and producing a bogus PartitionQuantity instead. Every real membership-
partition instance already uses a state verb, so this is a pure narrowing.

Files: `packs/arithmetic/rules/core.yaml`,
`packs/core-english/categories/core.yaml`, `src/rulekit/kernel/learn.py`,
`tests/test_mining_increment_59.py` (8 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SHIP +1/0/0
(3772 items, 28->29 correct, 0 wrong; SOLVED 10508e87ebf7), dev-holdout diff
NEUTRAL 0/0/0 (3701 items, 18/0 unchanged), pytest 473 passed (was 465 + 8
new, now `tests/test_mining_increment_59.py`), suite 52/52, lint 0 errors /
1 known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
TEST look #61: 7/1 (87.5%) — precision HELD, increment kept.

## Increment 60: temporal-offset age premises (`In N years, WHO will be M
years old` / `N years ago, WHO was M years old`) (`0c8a722`)

Class: a temporal-offset age premise states an entity's age at a FUTURE or
PAST point N years away rather than as a direct current holding — 28 dev-
train items pair such a premise with a plain "how old is WHO now?" ask and
declined "no quantity known for WHO of year" (the ask matched, the premise
read, only the offset clause emitted nothing).

Mechanism: two new pattern rules in `packs/arithmetic/rules/core.yaml` —
`arithmetic/temporal-offset-age-future` ("In N years, WHO will be M years
old") and the mirrored `arithmetic/temporal-offset-age-past` ("N years ago,
WHO was M years old") — emit the SAME Quantity shape `arithmetic/stated-age`
already produces (measure `year`), computed as stated age MINUS the offset
for the future form and PLUS the offset for the past form. No new fact
kind and no new consumer: ask/how-old-is and the existing relation/ratio
synthesizers chain through unchanged, simpler than the brief's proposed
OffsetAge-fact-plus-synthesizer route (reusing the Quantity shape sidesteps
the existence-vs-use accounting decision entirely, since no new fact kind
is introduced). Both consumed numbers (the offset and the stated age) go
through `consumes: [n, m]`, the same idiom `stated-age` and `anchored-
relation` already use. Decline-safety: `where: absent relational_marker /
multiplier_marker` (increment 57's clause-boundary categories) aborts
emission the instant the SAME sentence also carries a comparative or ratio
marker ("will be twice as old", "will be half of X's age") — those clauses
are left for the relation/ratio synthesizers, which is exercised directly
by a synthetic test chaining an offset premise into an existing relation-
inverse synth in a separate sentence. No new vocabulary (ago/old/be/in/
years were all already in the lexicon); no quarantine check needed.

Files: `packs/arithmetic/rules/core.yaml`, `tests/test_mining_increment_60.py`
(5 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SHIP +1/0/0
(3772 items, 29->30 correct, 0 wrong; SOLVED 77b1aa145a80), dev-holdout diff
NEUTRAL 0/0/0 (3701 items, 18/0 unchanged), pytest 478 passed (was 473 + 5
new, now `tests/test_mining_increment_60.py`), suite 52/52, lint 0 errors /
1 known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
TEST look #62: 7/1 (87.5%) — precision HELD, increment kept.

## Increment 61: cross-sentence item/measure inheritance for elided event (`05e7729`)
conjuncts (`sold 5 last week and 7 this week`) (`98b0fad`)

Class: an event verb's dobj obligation only binds the FIRST conjunct in a
sentence — the pre-existing general conjunction-handling gap that increments
11/35/45 closed for NOUN-bearing sibling conjuncts. This is the sibling for
a conjunct whose item noun is fully ELIDED: a bare, unmerged count value,
optionally trailing a bare temporal modifier ("last week", "this week").
Probe: "Vera has 18 chocolate bars. She sold 5 last week and 7 this week.
How many chocolate bars does Vera have left?" declined "stated count 7
reached no fact" — the second bare-number conjunct was invisible to value
accounting entirely. Named worklist TOP SEED (b), paired in the brief with
the parked `event-goal-progress` mechanism as the next batch's follow-up.

Mechanism: new walker `_conjoined_bare_number_events` in
`src/rulekit/kernel/learn.py`, sibling to `_conjoined_purchase_items`
(same top-level comma/conjunction segmentation, same clause-boundary
caution breaking on a fresh finite verb). Matches a segment only when it
holds EXACTLY one bare count-value unit (sense `value`, `value_kind`
`count` — never a genuinely named item, which is `_conjoined_purchase_
items`'s job) and every noun-sense unit in the segment is a `timeperiod`
category member (structure only, never a lexicon word list; any other
noun means a real item WAS stated and the walker declines that segment).
Scoped opt-in per the HANDOFF invariant: called only from the existing
`not is_state and _has_event_polarity(verb_lemma, reg)` block already
guarding `_conjoined_purchase_items`, so a state verb's conjuncts, an
untagged verb's conjuncts, and any genuinely noun-bearing conjunct are
byte-unchanged. Each recovered bare value folds as its own event Quantity,
inheriting entity/measure/verb/occurrence from the verb's own bound dobj.
By design this enabler still fully declines end-to-end by itself: two
facts recovered from the same head dobj share one fact-store key and
collide via the pre-existing same-key-different-value safety net rather
than silently summing (the sentence now declines for a fold/fold conflict
instead of "stated count reached no fact" — strictly more informative,
never a wrong commit). The brief's paired follow-up (re-cutting the parked
`event-goal-progress` mechanism on top) is deferred to the next batch.

Files: `src/rulekit/kernel/learn.py`, `tests/test_mining_increment_61.py`
(4 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL 0/0/0
(3772 items, 30/0 unchanged — by design, see above), dev-holdout diff
NEUTRAL 0/0/0 (3701 items, 18/0 unchanged), pytest 482 passed (was 478 + 4
new, now `tests/test_mining_increment_61.py`), suite 52/52, lint 0 errors /
1 known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
TEST look #63: 7/1 (87.5%) — precision HELD, increment kept.

## Increment 62: elided-measure entity asks ("How many does WHO have?" / (`87b8242`)
"How many did WHO VERB?") (`d85b6f8`)

Class: a question with NO item/measure noun at all — just "How many does
WHO have?" or "How many did WHO VERB?" — where the existing itemed asks
(ask/how-many-entity, the by-verb activity ask) all require a noun slot
and so decline "no ask shape recognizes this question". Scratchpad
fullread-declined scan found 6 dev-train items: "how many does W have" x4
(63ee7f480954, 9300451bebe1, ...) and "how many did W make" x2
(56ef08361887, fe95d045e503). Named worklist goal-mode directive 1 (ask-
shape bucket). Items with "how many does he have TO" were inspected and
excluded up front — that is modal "have to VERB", a different shape, not
this class.

Mechanism: two new ask ids mirroring ask/how-many-entity and the by-verb
activity ask but with no item slot, in `packs/arithmetic/rules/core.yaml`.
Resolution (a new `single-entity-elided-measure` branch in `answer.py`)
supplies the measure as the UNIQUE measure for which the asked entity
holds any fact — the same unique-pool-in-play discipline already used by
synth/partition-of-collection and fraction-of-pronoun, never document-
level guessing. Exactly one candidate measure for the entity or decline:
"Tom has 5 marbles and 3 pencils. How many does Tom have?" stays a
decline by design (probe-verified before landing) — that is the shipped
decline-safety behavior, not a gap. The new elided-measure asks lose the
specificity tie-break to every existing itemed ask (fewer consumed units),
so a real item noun in the question still routes to the pre-existing ask
unchanged — covered directly by a synthetic test. No new fact kind, no
new vocabulary.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/answer.py`,
`tests/test_mining_increment_62.py` (5 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SHIP +3/0/0
(3772 items, 30->33 correct, 0 wrong; SOLVED 63ee7f480954, 98030d1ebb74,
e895a4de0fdd), dev-holdout diff SHIP +3/0/0 (3701 items, 18->21 correct,
0 wrong; SOLVED 0bf508041d77, 64eddb42f33f, c60b4a7d4525), pytest 487
passed (was 482 + 5 new, now `tests/test_mining_increment_62.py`), suite
52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged).
TEST look #64: 8/1 (88.9%) — TEST coverage GAIN, new floor, increment kept.

## Increment 63: plural spelled fraction words ("two thirds", "three
fifths") (`e0f3f72`)

Class: plural spelled-out fraction words — TOP SEED (a) from the
worklist ("SPELLED-OUT NUMBER WORDS — scout MUST evaluate it this
batch"). Fresh stats unknown-word worklist: thirds 16, fifths 10,
fourths 5, sevenths 1, tenths 1 (quarters 26 excluded — `quarter`
already carries a coin/currency sense, so its plural is withheld from
this tight morphological family per the one-family-per-increment
vocabulary rule, look #20/#32). 32 dev-train items contain a plural
fraction word; in 11 it is the only unknown word (all 11 declined
pre-landing).

Mechanism: pack data only — add halves/thirds/fourths/fifths/sixths/
sevenths/eighths/ninths/tenths to the `fractions` table in
`packs/core-english/numbers.yaml`, beside their existing singulars.
`numbers.py`'s existing word-count x word-fraction merge in
`annotate_numbers` already reads any fold present in `reg.fractions`
— no kernel code change. "Two thirds" is now read as 2/3 the same way
"two fifths" already was, so the increment-28 fraction-partition
machinery and the fraction-of-remainder/fraction-of-pool consumers run
unchanged. DECLARED INFRASTRUCTURE: an in-memory injection scan across
all 32 containing dev-train items measured 0 outcome flips before
landing (a pure fully-read ceiling raise, +11 items fully read); the
integrated re-gate below reproduces that result exactly (0 SOLVED, 0
BROKE) — this increment cannot satisfy the SOLVED>=1 goal-mode gate on
its own. It unblocks the already-landed increment-28 fraction/percent-
partition and fraction-of-pool consumer families for "two thirds/three
fifths" phrasings; per methodology the ceiling raise is TEST leverage,
to be cashed in by this batch's own TEST look.

Files: `packs/core-english/numbers.yaml`,
`tests/test_mining_increment_63.py` (5 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL
+0/0/0 (3772 items, correct 33/0 wrong before and after; fully-read
38.4%->38.7%), dev-holdout diff NEUTRAL +0/0/0 (3701 items, correct
21/0 wrong before and after; fully-read 37.5%->37.9%), pytest 492
passed (was 487 + 5 new, now `tests/test_mining_increment_63.py`),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant
/ fraction-of-pool, unchanged).
TEST look: pending — spent manually.

## The next mining worklist (from the last close-miss scan)

**GOAL MODE (set 2026-07-11): the campaign target is 100 dev-train
corrects (currently 14).** Fresh stats after increment 39: the structure
worklist is dominated by **"no ask shape recognizes this question" —
2,604 of 3,758 declines**. Ask shapes are THE coverage lever; premise
machinery is now largely ahead of the questions it can serve. Scout
directives while goal mode holds:

0. **affine-relations-recut — LANDED as increment 46** (re-cut of
   `mining/parked/affine-relations` against current main; dev-train +4,
   holdout NEUTRAL).
0. TOP SEEDS (batch 19 output): increment 62 proves the elided/unique-
   measure ask family is rich — scout its siblings ("How many are
   left?", "How many more does X need?" with elided measures).
   (a) SPELLED-OUT NUMBER WORDS — STILL unattempted after two seedings;
   scout MUST evaluate it this batch (frequency scan, then pack-data
   word→value table through annotate-numbers).
   (b) The event-goal lineage needs a NARROW cross-sentence inheritance
   candidate: pass the entity's Goal facts (or accumulated FactStore
   context) into the fold, gated structurally on `timeperiod` — the
   occurrence-key shortcut is CONFIRMED UNSAFE (produces wrongs).
   (c) Parked gate-clean cash-ins: years-old-age-phrasings,
   parenthetical-currency-units, temporal-offset-age-asks (its
   increment-31 test update is correct and pre-approved), much-more-
   need-asks, each-container-rates, partitive-each-share,
   spend-on-conjuncts — a future batch landing an enabler should
   reland these in the SAME batch (they are already built and gated).
1. Prefer candidates that MINE THE ASK-SHAPE BUCKET: bucket the
   unrecognized questions by surface shape (scratchpad script over
   dev-train declines with that reason) and propose general ask shapes
   for the largest sub-buckets.
2. Every brief must cite VERIFIED matching dev-train evidence, and
   "verified" means the FULL CHAIN: the scout's traced paraphrase must
   show ask recognized AND premises read AND the fold producing the gold
   number under the proposed mechanism — not merely the ask matching
   (batch 8 landed three ask shapes that all re-gated 0 SOLVED because
   the items decline downstream). While goal mode holds, a coverage
   brief whose junior dev-train diff shows SOLVED = 0 is a FAILED gate:
   the junior returns status failed with the downstream decline reasons
   as its lesson, instead of landing dev-NEUTRAL machinery. Explicitly
   declared infrastructure briefs are exempt but must name the follow-up
   class and the batch that will cash it in.
2b. Juniors: the brief's evidence items are the reviewer's FIRST grep —
   never reuse ANY sentence, name, or number tuple from them in tests
   (four candidates have now been blocked for exactly this).
3. Precision rules are unchanged — never trade a wrong for coverage.
   Remaining buckets after ask shapes: "no quantity known" 191,
   "0 price facts known" 143 (the pricing stack is live — find why price
   facts don't emit), fold-conflicts 113, spend/pay event asks 66+44.

Numbers below predate this session's work and need a fresh `rulekit
stats` pass before trusting them.

- **state-verb-conjunction — LANDED as increment 35** after three prior
  deferrals for the same test contamination (verbatim GSM8K substring
  inherited from earlier parked branches' tests/); this attempt rebased
  the mechanism only and wrote every test from a blank file. (Batch 5's
  other parked briefs all landed in batch 6: `age-asks` → increment 31,
  `need-as-goal` → 32, `money-left-asks` → 33, `attr-qualified-entities`
  → 34.)

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
  Y" / "X, Y, and Z" for verbs outside the `purchase`/`state` categories —
  a pre-existing, general conjunction-handling gap that silently drops
  every conjunct after the first from the fold entirely. Increment 11
  closed it for purchase verbs, increment 35 for state verbs (have/own/
  be); it is STILL OPEN for 'contains' and event verbs generally.
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
