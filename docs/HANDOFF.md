# Session handoff — 2026-07-11

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State below is committed through `da76539` on `main` (github.com/ldupisani/rulekit;
check `git status`/`git log origin/main..HEAD` before assuming push parity).

## Where the project is

Everything through P5 of the original plan is DONE: kernel, YAML packs, lint
(overlap witnesses + blast radius), document re-parse loop, GSM8K harness with
firewall, visual designer (`rulekit serve`, port 8321 — busy-state, slice
targets, TEST gated behind a checkbox). The GSM8K mining campaign is in full
swing under the constitution (no lexicon in Python, no per-problem parsing,
every increment through the gates).

**Current numbers (all verified at head):**
- dev-train: 70 correct / 0 wrong (3,772 items, 100% precision) — GOAL: 100
- dev-holdout: 28 correct / 0 wrong (3,701 items)
- curated suite: 52/52 · pytest: 757 · lint: 0 errors, 1 intended warning
- bench wall: dev-train 16.6s -> 9.0s (trace opt-out) -> 1.7s at `--jobs 12`.
  `--jobs` defaults to 1; spend it in the SERIAL integration tail, never in the
  implementers' gates (they already run concurrently). See the two infra notes below.
- TEST ledger (91 looks spent, `projects/gsm8k/snapshots/test-ledger.jsonl`):
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
  8/1 (88.9%, look #64 — the floor) →
  8/1 (88.9%, look #65) →
  8/1 (88.9%, look #66) →
  **8/1 (88.9%, look #67) ← live at increment 65** — #64 batch 19
  (increment 62: +3/+3/+1, the campaign's largest), #65 batch 20,
  #66 batch 21 (increment 64, entity-less totality asks re-cut; the
  parked-pile composition reland measured 0 SOLVED — those mechanisms
  await further enablers, not each other), #67 batch 22 (increment 65,
  common-noun relation subjects; HELD, no TEST coverage gain). GOAL RUN
  PAUSED at dev-train 33/100 by user decision; batch 22 was run anyway
  and took it to 34.
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

## Increment 63: plural spelled fraction words ("two thirds", "three (`eacb5d4`)
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
TEST look #65: 8/1 (88.9%) — precision HELD, increment kept.

## Increment 64: totality-marked entity-less there-asks (multi-holder sum), (`da76539`)
re-cut

Class: a "there" existential ask carrying an explicit totality marker
("in total" / "altogether" / "together" / "combined") over 2+ named
holders of a measure — the bare `ask/how-many-there` (unique-holder
discipline) correctly declines these, but the marker is explicit license
to sum, which nothing previously read. Re-cut of the parked candidate
`mining/parked/entityless-total-there-asks` (31af789), fixing ONLY the
review finding named in worklist TOP SEED (a): the `world` scene-holder
exclusion moves out of a Python-side constant in `answer.py` and into
the new ask's own `resolves` block as pack data.

Mechanism: new ask `ask/how-many-there-combined` in
`packs/arithmetic/rules/core.yaml` requires the trailing aggregate marker
and routes to the existing 'combined' consumer already used by the
pronoun/named-pair combined asks; `ask/how-many-there` itself is
untouched (still exactly-one-holder). `answer.py`'s
`_combined_holder_totals` gained an opt-in `exclude_entity` parameter
(default `None` — every pre-existing caller byte-unchanged) that takes
an ENTITY NAME rather than a boolean; only the new ask supplies
`exclude_entity: world` as pack data, so the literal `world` lives only
in YAML, never hardcoded in the kernel. No new vocabulary.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/answer.py`,
`tests/test_mining_increment_64.py` (7 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL
+0/0/0 (3772 items, correct 33/0 wrong before and after), dev-holdout
diff NEUTRAL +0/0/0 (3701 items, correct 21/0 wrong before and after),
pytest 499 passed (was 492 + 7 new, now
`tests/test_mining_increment_64.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).
TEST look #66: 8/1 (88.9%) — precision HELD, increment kept.

## Increment 65: common-noun relation subjects (definite/possessive common
noun as relation holder or standard), (`2353da0`)

Class: relation premises whose subject or standard is a definite/possessive
common noun rather than a name — "Her cousin has 6 fewer rubber bands than
he has." The `entity` slot type (name | common noun | resolved pronoun) was
already built for the rate-span re-land and already used by the relation
synthesizer and the combined-ask consumer; it had simply never been reached
through the relation rules' subject/standard slots, which all hard-required
`type: name`.

Mechanism: YAML-only. Widens `who`/`std` from `type: name` to `type: entity`
on the six Relation-emitting rules in `packs/arithmetic/rules/core.yaml`:
`arithmetic/anchored-relation`, `arithmetic/anchored-relation-postfix`,
`arithmetic/times-as-many`, `arithmetic/fraction-as-many`,
`arithmetic/affine-times-as-many`, `arithmetic/affine-fraction-as-many` —
each widened and gated individually per the HANDOFF invariant against
blanket find/replace. No kernel edit was needed: `patterns.py`'s
`_slot_ok` already implements `type: entity` generally, and the relation
synthesizer already keys Relation facts by bare entity lemma regardless of
whether it came from a name or a common noun. Widening surfaced a new
self-referential collision — "has 2 fewer animal stickers than flower
stickers" bare-folds `item` and `std` to the same measure lemma, comparing
two measures of the speaker's own holding rather than two holders of one
measure — caught on dev-train during landing; each widened rule gained a
`distinct: [item, std]` where-clause to keep it declined instead of minting
a confident-wrong.

Files: `packs/arithmetic/rules/core.yaml`, `tests/test_mining_increment_65.py`
(6 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 1, BROKE
0, DECL->WRONG 0 (3772 items, correct 33 -> 34, 0 wrong, VERDICT SHIP),
dev-holdout diff NEUTRAL +0/0/0 (3701 items, correct 21/0 wrong before and
after), pytest 505 passed (was 499 + 6 new, now
`tests/test_mining_increment_65.py`), suite 52/52, lint 0 errors / 1
known-good warning (fraction-of-remnant / fraction-of-pool, unchanged).

TEST look #67: 8/1 (88.9%) — precision HELD, increment kept. No TEST coverage
gain (correct 8 -> 8): the class is real on DEV (dev-train 33 -> 34) but no
TEST item exercises a common-noun relation subject. Held, not cashed.

## Increment 66: phrasal/particle event verbs (VERB + away/out/off/up) as
ordinary signed events (`750efd1`)

Class: premises whose disposal/removal event is expressed as a polarity-
tagged verb plus an immediately-following directional particle — "gives
away 1/4 of the marbles", "gave away half of the stickers", "throws away
the leftover", "takes 1/4 of them away" — where the particle currently
reads as a free adverb and orphans the fraction/count it modifies,
tripping the value-accounting guard on an unaccounted number.

Mechanism: YAML-first. Declares a `particle` category
(`packs/core-english/categories/core.yaml`) whose members are the existing
adverb-sense directional particles (away/out/off/up — already in the
lexicon, nothing new admitted, nothing quarantined). `condense.py` gained
a merge-particle-verb pass that fuses a polarity-tagged event verb with an
immediately adjacent particle into one verb lexeme, keeping the base
verb's own lemma and polarity category. Decline-safety is gated on
`_has_event_polarity` (the increment-45 invariant): an untagged verb plus
a particle — "looks up 4 words", "take up to 12 people" (take carries no
polarity tag in this pack) — stays exactly as declined as before. The
merge is adjacent-only, so dobj-crossing particles ("took two letters off
the shelf") are out of scope and stay decline-safe too.

Files: `packs/core-english/categories/core.yaml`,
`packs/difg-mined/categories/semantic.yaml`, `src/rulekit/kernel/condense.py`,
`tests/test_mining_increment_66.py` (6 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff NEUTRAL +0/0/0
(3772 items, correct 34/0 wrong before and after), dev-holdout diff NEUTRAL
+0/0/0 (3701 items, correct 21/0 wrong before and after), pytest 530 passed
(was 524 + 6 new), suite 52/52, lint 0 errors / 1 known-good warning
(fraction-of-remnant / fraction-of-pool, unchanged).

TEST look: pending — spent manually.

## Increment 67: plural-NP / collective-subject totality asks (`<squash-pending>`)

Class: questions whose subject is a definite plural NP or collective
pronoun standing in for two or more holders named earlier — "how many
total ITEM do the boys have?", "how many ITEM are there in total in the
two lakes?", "how many ITEM do NAME and NAME have combined?" with the
measure elided, "how many ITEM does all of them have combined?" — rather
than the single-name or explicit-pair subjects the existing combined/
totality asks already serve.

Mechanism: YAML-first, no new vocabulary. Four new ask ids in
`packs/arithmetic/rules/core.yaml` beside `ask/how-many-there-combined`
and `ask/how-many-combined-named`: `ask/how-many-plural-combined` (bare
or cardinal-merged definite plural common-noun subject), `ask/how-many-
all-combined` (plural-pronoun collective subject, a separate ask id
because `ask/how-many-combined`'s own opt group binds [aux, who, verb] as
one inseparable subsequence), and the elided-measure variants that reuse
increment 62's elided-measure resolution and increment 54's named-pair
combined consumer. All four route to EXISTING consumers (entity-less
totality from increment 64, or named-pair combined from increment 54) —
no new fact kind, no new committer. The one supporting mechanism change:
the collective cardinal in an ask NP ("the two lakes") is listed in the
ask's own `consumes:` so the value-accounting guard treats it as
structural rather than an unaccounted operative count — scoped to these
new ask ids' own consumed slot only, never a global loosening of the
guard.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/schemas.py`,
`src/rulekit/kernel/patterns.py`, `tests/test_mining_increment_67.py` (10
synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 3 /
BROKE 0 / DECL→WRONG 0 (SHIP; 0775ef2d50f6, a35290d93b09, b0b1d087abe4),
dev-holdout diff NEUTRAL +0/0/0, pytest 540 passed (was 530 + 10 new),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged).

TEST look: pending — spent manually.

## Increment 68: dimension-comparative relations and dimension asks (height /
length / weight / area) (`<squash-pending>`)

Class: physical-dimension comparatives — "Jake's snake is 12 inches longer
than Jenny's snake", "N square feet larger than", "N cm shorter than" —
paired with dimension asks ("how tall is X", "how many inches tall is X",
"how DIMENSION is X and Y combined"). Before this, `arithmetic/anchored-
relation-postfix` gated its direction word on `cat: delta` and the age
family gated on `age_comparative`; every other physical-dimension adjective
fell through and the general SVO fold misread the stated unit as a bare
absolute Quantity — a latent confident-wrong, not merely a decline.

Mechanism: YAML-first. (1) A new `dimension_comparative` category
(`packs/core-english/categories/core.yaml`, members in `packs/difg-mined/
categories/semantic.yaml`) tagging the dimension comparative adjectives
(taller/longer/heavier/larger/wider/deeper/higher = +1, shorter/lighter/
smaller/narrower = -1) via two child categories mirroring `more_dir`/
`less_dir`'s polarity structure, as a SIBLING of `delta` — `delta` itself
is untouched, and `age_comparative` (increment 48's TEST-proven surface)
is untouched. (2) A new rule, `arithmetic/anchored-relation-postfix-
dimension` (`packs/arithmetic/rules/core.yaml`), cloned from `arithmetic/
anchored-relation-postfix` with `cat: dimension_comparative` in place of
`cat: delta`, emitting the same Relation fact shape consumed by the
existing saturate fixpoint and fold/combined synthesizers — no new fact
kind, no new consumer. (3) New dimension asks modelled on `ask/how-old-
is`: bare ("how ADJ is X") and unit-qualified ("how many UNIT ADJ is X"),
resolving the measure from the named unit when present, else from the
unique measure in play; the dimension-name→unit mapping is pack data.
Every comparative word was already in the lexicon and none is in
`quarantine.yaml`.

Files: `packs/core-english/categories/core.yaml`, `packs/difg-mined/
categories/semantic.yaml`, `packs/arithmetic/rules/core.yaml`,
`tests/test_mining_increment_68.py` (9 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 1 /
BROKE 0 / DECL→WRONG 0 (SHIP; 91fa57c70298), dev-holdout diff SOLVED 1 /
BROKE 0 / DECL→WRONG 0 (SHIP; ebcfb7b49617), pytest 549 passed (was 540 +
9 new), suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-
remnant / fraction-of-pool, unchanged).

TEST look: pending — spent manually.

## Increment 69: sum-constraint linear systems (a stated relation between two
holders plus a stated group total) (`<squash-pending>`)

Class: premises pairing a two-holder Relation ("A has 11 more floors than
B", "one has 5 less than half the other") with a stated group TOTAL ("the
two together total 35 floors", "there are 160 toys altogether") — a
textbook 2x2 linear system. Before this, `arithmetic/existential-premise-
bare` deliberately REFUSED the bare-existential totality form via its
`absent: {cat: aggregate}` guard (documented in-line as "a group TOTAL,
never an independent holding"), and nothing else picked the pair up, so
these items declined with "no quantity known for 'X' of 'Y'" / "a combined
ask needs at least two holders".

Mechanism: BUNDLED enabler + payoff. (1) A new `GroupTotal` fact kind
(`src/rulekit/kernel/model.py`). (2) Two premise rules in
`packs/arithmetic/rules/core.yaml` emit it: the bare existential aggregate
form the old rule refused, and a general "... a total of N ITEM" tail
match. No new vocabulary — `aggregate` category already existed. (3) A new
`synth/sum-constraint` plugin (`src/rulekit/kernel/saturate.py`, registered
in `PLUGINS`): when exactly one Relation over a measure relates exactly two
entities and exactly one GroupTotal over that measure is in play, solves
standard = (T - offset) / (1 + factor), subject = T - standard, and emits
both as ordinary Quantity facts — the existing single-entity/entity-less/
combined consumers answer with no consumer change. Declines (emits
nothing) on multiple Relations, multiple GroupTotals, factor == -1, a
negative solution, or a third entity holding the measure. (4)
`src/rulekit/kernel/guards.py`: GroupTotal is USE-gated for value
accounting, like Rate/Price/Goal. A 3-entity chain extension (two relations
+ one total) is deliberately scoped out for a future increment.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/model.py`,
`src/rulekit/kernel/saturate.py`, `src/rulekit/kernel/guards.py`,
`tests/test_mining_increment_69.py` (6 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 1 /
BROKE 0 / DECL→WRONG 0 (SHIP; 7a124ab41af5), dev-holdout diff SOLVED 0 /
BROKE 0 / DECL→WRONG 0 (NEUTRAL), pytest 555 passed (was 549 + 6 new),
suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged).

## Increment 70: attribute-qualified measure keys (a qualified count noun
must not collide with its bare measure) (`<squash-pending>`)

Class: attribute-qualified count-noun premises ("12 white marbles and 6
blue marbles" alongside a bare "20 marbles" total; "1 red shirt for $32 and
3 blue shirts at $27 each") were folding BOTH qualified variants to the
bare measure lemma, so two differently-qualified holdings/prices of the
same noun collided as one fact-store key and the whole item declined with
"conflict: fold and fold disagree about (...)". This is the largest
structural decline bucket in the current worklist (146 quantity + 11 price
= 157 items, 54+ freshly evidenced) and is infrastructure: it unblocks the
`rest-partitions` class and qualified-price purchase totals, both starved
today by this same collision.

Mechanism: KERNEL-STRUCTURAL, no lexicon — the exact mirror of increment
25's owner split, applied to the MEASURE key instead of the entity key.
condense.py's merge-attribute already tags a merged ADJ+NOUN unit with a
`qualifier` feature; learn.py now also copies that qualifier onto the
emitted fact as a new `measure_qualifier` field on `Quantity` and
`qualifier` field on `Price` (`src/rulekit/kernel/model.py`), defaulting to
`None` so every existing fact is byte-identical. `FactStore.admit`
(`src/rulekit/kernel/facts.py`) reads that field ONLY in collision
handling: a same-key VALUE conflict between two facts with two DIFFERENT
non-null qualifiers is not a disagreement — it is two measures the bare
lemma can't distinguish — so both re-key to `measure[qualifier]` (or
`item[qualifier]`) and admit separately instead of quarantining. A
null-vs-non-null qualifier (the collection total vs. a named subset) is
deliberately NOT re-keyed — that stays a genuine part/whole relation and
keeps declining until `rest-partitions` supplies a fact for it. NO consumer
change: increment 26's `interchangeable` gate and the existing
ask/how-many-entity-qualified (increment 34) already read the qualified
keys correctly.

Files: `src/rulekit/kernel/learn.py`, `src/rulekit/kernel/facts.py`,
`src/rulekit/kernel/model.py`, `tests/test_mining_increment_70.py` (5
synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 0 /
BROKE 0 / DECL→WRONG 0 (NEUTRAL), dev-holdout diff SOLVED 0 / BROKE 0 /
DECL→WRONG 0 (NEUTRAL), pytest 560 passed (was 555 + 5 new), suite 52/52,
lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). Pure enabler on this dev slice — no items
resolve yet; payoff arrives when `rest-partitions` and qualified-price
consumers land on top. TEST look: pending — spent manually.

TEST look: pending — spent manually.

## The next mining worklist (from the last close-miss scan)

**GOAL MODE (set 2026-07-11, PAUSED 2026-07-12 at 33/100 by user
decision after 21 batches).** The directives below remain the playbook
for resuming the push to 100. Fresh stats after increment 39: the structure
worklist is dominated by **"no ask shape recognizes this question" —
2,604 of 3,758 declines**. Ask shapes are THE coverage lever; premise
machinery is now largely ahead of the questions it can serve. Scout
directives while goal mode holds:

0. **affine-relations-recut — LANDED as increment 46** (re-cut of
   `mining/parked/affine-relations` against current main; dev-train +4,
   holdout NEUTRAL).
0. TOP SEEDS (batch 20 output): (a) re-cut
   `mining/parked/entityless-total-there-asks` fixing ONLY the review
   finding: move the 'world' constant from answer.py into the ask's
   resolves block (e.g. `exclude_entity: world`) — the mechanism is
   otherwise gate-clean and its exclude_world fix already survived a
   real holdout catch. (b) reland the gate-clean parked pile in ONE
   batch (in-all-totality-tails, each-item-flat-cost-asks,
   years-old-age-phrasings, parenthetical-currency-units,
   temporal-offset-age-asks, much-more-need-asks, each-container-rates,
   partitive-each-share, spend-on-conjuncts) — individually NEUTRAL but
   their compositions may flip items; a single batch relanding them
   sequentially with re-gates measures the composition for the cost of
   at most a few looks. (c) spelled-out INTEGER words: increment 63
   covered plural fractions; verify whether cardinal words (eight,
   twelve) already parse and, if not, extend numbers.yaml the same way.
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

## Tracing is opt-out (2026-07-12, infra — not a mining increment)

`Reading.record` is the single mutation door and it deep-copied the before AND
after value of every changed feature, so each Decision carries a reversible
diff. Profiling a dev-train bench: **61% of wall-clock was `copy.deepcopy`**
(41.2s of 67.3s cumulative, 35.7M calls, ~9,465 per item).

Nothing in a bench reads those diffs. `Decision.before/after` are consumed only
by `engine.trace()` (engine.py:97), which is called only by the designer API
(`server/api.py:212`) — and `Reading.undo()`, the entire justification for
`before`, **is never called anywhere in the codebase**. Snapshots don't contain
decisions (`to_snapshot` derives `rules` from `fact.provenance`).

So: `Reading(tracing=...)`, threaded through `tokenize → analyze → solve`,
**defaulting to True** at every hop — every existing caller keeps today's
behaviour, and `run_suite` is the single opt-out. A missed consumer degrades to
"still traced", never to "silently lost its trace". `undo()` now raises on an
untraced Reading rather than silently restoring nothing.

Also added `model._snapshot`: immutable feature values (60% of everything
passing through `record`) are returned as-is instead of paying deepcopy's
dispatch for a no-op. Mutable values (obligation lists, whose `target` is a live
Unit) are still deep-copied — aliasing them would let later mutation rewrite
history.

PROOF (the gate for a perf change is byte-identity, not a diff verdict):
dev-train, dev-holdout and suite snapshots rebuilt and **byte-identical** to the
pre-change baselines (`cmp`, plus NEUTRAL on both diffs). pytest 505 -> 519
(+14 synthetic, `tests/test_tracing_optout.py`), suite 52/52, lint unchanged.

RESULT: dev-train bench 16.6s -> 9.0s (1.84x). Every dev gate runs ~3 benches,
and a mining batch runs a gate per implementer plus one per integration step, so
this compounds across the whole pipeline.

REMAINING HEADROOM (not taken):
- 10.1M deepcopy calls survive, ~11.5s cumulative, in `obligations.disambiguate`
  / `_coverage_score` — a genuine trial-state copy (one per sentence analysed),
  not a trace. Real work; optimising it is riskier and needs its own byte-proof.
- `run_suite` is still a single-threaded loop over independent items. The kernel
  is deterministic and per-item independent, so a process pool is the obvious
  next lever (~8 cores). Order-preserving `map` is required or snapshots move.

LATENT BUG FOUND, NOT FIXED: `undo`'s pop-branch (`val is None and key not in
decision.after`) is unreachable — `before`/`after` are built from the same
`changes` keys, so undoing a previously-absent feature leaves it as None instead
of removing it. Harmless while `undo` is dead code. Pinned as-is in the tests.

## Parallel bench is opt-in (2026-07-12, infra — not a mining increment)

`run_suite` was a single-threaded loop over independent items. The kernel is
deterministic and per-item independent, so items now fan out over a process pool
under `bench --jobs N`.

WHY IT DEFAULTS TO SERIAL (jobs=1): a mining batch already runs five implementers
concurrently, each running its own dev gate. If every bench grabbed every core,
that phase would oversubscribe the box (5 x 12 workers on 14 cores) and get
SLOWER. The machine is only idle where the pipeline is serial — the integration
tail. So `--jobs` is spent there and nowhere else; the integrator protocol now
passes `--jobs 8`, the implementer protocol deliberately does not.

MECHANICS: a Registry cannot be pickled (mappingproxy), so a worker cannot be
handed one — each rebuilds it from the project dir (~540ms, paid once per worker,
in parallel). `_worker_init` then checks the worker's pack fingerprint against
the parent's and RAISES on mismatch: a run dies loudly rather than quietly
benching a mixture of two pack states. `Pool.map` preserves input order. Start
method is spawn (never fork: the parent has pyarrow loaded, and forking a process
with native thread pools risks deadlock).

`_solve_item` is now the single code path for both serial and parallel — that is
what makes byte-identity achievable rather than merely hoped-for. The item-id
fallback is the item's INDEX, not `len(results)`, so a worker never needs to know
how many items preceded it.

`bench --twice` is now stronger: with `--jobs N` the second run is deliberately
SERIAL, making it a parallel-vs-serial equivalence check rather than a parallel
run agreeing with itself.

PROOF: dev-train snapshots at `--jobs 1`, `--jobs 6` and `--jobs 12` are all
byte-identical (`cmp`) to the baseline taken BEFORE both this and the trace
change. `--twice --jobs 12` passes. pytest 519 -> 524 (+5 synthetic,
`tests/test_bench_parallel.py`), suite 52/52, lint unchanged.

RESULT: dev-train 9.0s -> 1.73s at `--jobs 12` (~5.2x on top of the trace win;
~9.6x vs the 16.6s starting point).

NOT TAKEN: the ~11.5s cumulative deepcopy left in `obligations.disambiguate` /
`_coverage_score` is genuine trial-state copying (one per sentence analysed), not
trace overhead. Optimising it needs its own byte-proof.

## The shape gate, and a smoke-test bug it uncovered (2026-07-12, infra)

SHAPE GATE. A scout brief's `evidence.frequency` is a SURFACE count — how many
items contain a phrase, not how many the mechanism can READ. Batch 22 spent three
implementer runs on that confusion (docs/negative-results.md, "the worklist counts
surfaces, not shapes"). Briefs now require `evidence.structural_sample`: >= 3
dev-train items WALKED end-to-end, each recording item_id, a PARAPHRASED premise
and ask shape (never verbatim — deferred briefs are written back into this file),
the fact emitted, and an honest `resolves` boolean. `mine.js` drops any candidate
with fewer than 3 resolving samples BEFORE an implementer is spent; the drop is
reported in the deferred table, never silently. Infrastructure briefs are exempt.

SMOKE-TEST BUG FOUND AND FIXED. The smoke brief is a no-op by construction (a YAML
comment), so it can never show SOLVED > 0 and it is not marked `infrastructure`.
The goal-mode gate — added in an earlier batch — was therefore DEMOTING it to
`failed`, which meant `/mine --smoke` silently stopped exercising the Integrate
stage: no cherry-pick, no re-gate, no staging branch, and a green report anyway.
Both gates now carve out SMOKE explicitly. Lesson worth keeping: a self-test that
shares the production gates will be killed by them the moment a gate gets stricter,
and it fails GREEN.

## Batch 23 (2026-07-12) — the shape gate's first real batch; increment 66 HELD

SCOUTED 3, IMPLEMENTED 1, LANDED 0 ON MAIN. No TEST look spent (ledger still 69).

DROPPED AT THE SHAPE GATE, before an implementer was spent:
- `remnant-entity-subjects` — frequency **327**, 0 of 4 walked items resolve.
- `existential-pool-depletion` — frequency 53, 0 of 4 walked items resolve.

A 327-frequency signal that resolves nothing. Under the old pipeline that would
have been the most attractive candidate on the board and would have burned a full
implementer run to discover what the scout established in minutes. The gate paid
for itself on its first batch.

THE SCOUT'S OWN HEADLINE, which matters more than the batch: "I could not prove
END-TO-END resolution for ANY candidate this pass. Every `resolves` is false,
deliberately." It ran 14 mechanised end-to-end probes rather than trust the
counts. Read that as a signal about the campaign, not the scout: **the easy
classes are gone.** The remaining ~3,738 dev-train declines are not waiting on
more ask shapes, they are waiting on ENABLERS.

INCREMENT 66 (particle event verbs) — HELD, NOT LANDED.
Branch: `mining/parked/particle-event-verbs-enabler` @ abb6052 (was the batch-23
staging branch; renamed so its status is unambiguous).
Class: phrasal/particle event verbs (VERB + away/out/off/up) as ordinary signed
events. Touches packs/core-english/categories/core.yaml, difg-mined/semantic.yaml,
src/rulekit/data/registry.py, src/rulekit/kernel/condense.py (+6 synthetic tests).
Gate: both diffs NEUTRAL, **0 SOLVED on dev-train AND dev-holdout**, pytest 530,
suite 52/52, lint clean.

WHY HELD: a 0-SOLVED increment cannot GAIN precision — it commits nothing new on
DEV — but it CAN lose it, because new fusion machinery in condense.py may commit
on TEST's unseen structures. Spending a TEST look on it is a pure downside bet.
It is an enabler: the scout's probes showed the fraction-of-pool and remnant
classes are blocked precisely on unparsed particle verbs. So it waits on the
parked branch and lands TOGETHER with the first increment that cashes it in —
one TEST look then validates the enabler and its payoff.

NEXT: the payoff class. A brief that consumes the particle-verb fusion (the
fraction-of-pool / remnant-with-disposal shapes) should be built ON TOP of
`mining/parked/particle-event-verbs-enabler`, not on main, and land as one
increment with it.

INFRA FLAG HARDENED as a result. `infrastructure: true` skipped BOTH coverage
gates on a self-declaration — a free pass, and the goal-mode gate exists because
prose directives were being routed around. Infrastructure is now a DIFFERENT bar,
not an exemption: the brief must name `unblocks` (the follow-up class) AND carry
>= 3 walked items with `resolves_after_unblocks: true` (items that would resolve
once that class lands on the enabler). The batch-23 brief — flag only, no proven
payoff — would now be dropped before an implementer is spent.

## Batch 24 (2026-07-12) — the payoff batch: enabler cashed in, dev-train 34 -> 38

FIRST BATCH BUILT ON A PARKED ENABLER. `base = mining/parked/particle-event-verbs-enabler`,
so candidates were cut from the held increment 66 instead of main, and the staging
branch carried enabler + payoff. Landed on main as 3ed7005 (66), 21e25e3 (67),
4861d35 (68).

- increment 66 — phrasal/particle event verbs (the enabler, held since batch 23)
- increment 67 — plural-NP / collective-subject totality asks
- increment 68 — dimension-comparative relations and asks (height/length/weight/area)

COMPOSITION GATE vs FRESH MAIN BASELINES (the new phase 5): dev-train 34 -> 38
(SOLVED 4, BROKE 0, DECL->WRONG 0, SHIP), dev-holdout 21 -> 22 (SOLVED 1, SHIP),
suite 52/52, pytest 549, lint clean. **solved_vs_main = 5.**

Why that number matters: each increment was gated against its own predecessor (67
against the enabler, 68 against 67) and the enabler against main in a DIFFERENT
batch. The naive sum of per-increment SOLVED counts is not the truth — items can
be solved by one increment and merely reconfirmed by the next, and pattern gates
can target overlapping item sets. Only benching the COMPOSED TIP against MAIN says
what the batch actually buys. That number did not exist before this batch.

The enabler contributed 0 on its own; the +4 came from 67 and 68 on top of it.
Holding it was right: landing it alone would have spent a TEST look on a
zero-coverage change that could only LOSE precision.

TEST LOOKS (2 spent, per the held-enabler deal — the enabler rides with its first
payoff rather than costing a look of its own):
- look #68 @ dabd3ca (increments 66 + 67): 8/1 (88.9%) — precision HELD.
- look #69 @ b735e85 (increment 68): 8/1 (88.9%) — precision HELD.
Neither bought TEST coverage (correct 8 -> 8): +5 on DEV, +0 on TEST. The classes
are real but no TEST item exercises them. Held, not cashed.

Landed by cherry-pick (main had moved past the enabler's cut point); docs/HANDOFF.md
auto-merged. Landed state verified at head: dev-train 38/0, dev-holdout 22/0,
suite 52/52, pytest 549, lint 0 errors.

## Batch 25 (2026-07-12) — 10 scouted, 0 landed, 9 killed at the shape gate

NOTHING LANDED. No TEST look spent (ledger still 71). The batch cost 3 agents —
scout, one implementer, one reviewer — for ten candidates.

SHAPE GATE DROPPED 9 OF 10 before an implementer was spent:

| slug | frequency | walked items resolving |
|---|---|---|
| collective-totality-asks | 33 | 2 of 4 |
| modal-difference-asks | 19 | 0 of 3 |
| offset-age-asks | 17 | 0 of 4 |
| named-bare-dimension-asks | 15 | 1 of 3 |
| age-frame-fraction-relations | 13 | 0 of 3 |
| age-measure-name-unify | 12 | 0 of 3 |
| relative-clause-relations | 3 | 0 of 3 |
| retention-verb-asks | 1 | 1 of 3 |
| intervening-modifier-offsets | 1 | 0 of 3 |

Two came close (2/4, 1/3) — the gate is discriminating at its margin, not just
bluntly rejecting. Under the pre-shape-gate pipeline this batch would have spent
NINE implementer runs (worktree + dev gate + tests + Opus review each) to learn
what the scout established by walking items.

READ THIS AS A CAMPAIGN SIGNAL, not a bad batch. Two consecutive scouts have now
struggled to prove classes end-to-end. The remaining ~3,734 dev-train declines are
not waiting on more ask shapes.

### The near-miss worth re-cutting: `age-equative-relations`

Gated CLEAN on dev, then failed constitution review on **rule 1
(lexicon-in-Python)**: `_bare_age_anchor_synth` in `src/rulekit/kernel/saturate.py`
hardcodes the measure word `"year"` at four sites (≈lines 226, 227, 232, 243).
Branch retained: `mining/cand-age-equative-relations`.

THE FIX IS ONE LINE AWAY AND THE PRECEDENT IS ALREADY IN THE TREE. The reviewer
grepped `src/` and found those are the ONLY measure-word literals in the whole
Python tree. Every other kernel measure test goes through a pack-defined CATEGORY:

    answer.py:893   q.measure == "currency" or reg.word_in_category(q.measure, "currency")
    core.yaml:65    currency: {parent: noun, interchangeable: true}

So: declare an `age_measure: [year]` category in a pack and gate the synth on
`reg.word_in_category(...)`. The junior already took the pack route on the YAML
side (a `temporal_marker` category rather than a literal `"today"`) — this is
expedience in one corner, not a broken design. **Re-cut, don't discard**, with the
pack-category fix stated in the brief as a MUST.

### Invariant (do not relearn)

A kernel gate on a MEASURE or any other word fact goes through
`reg.word_in_category(word, "<category>")` with the category declared in a pack —
NEVER a string literal in Python. `currency` is the reference implementation.
Constitution rule 1 has no small-violation exemption: even a one-word lexicon fact

## Increment 71: equative age comparatives ("K times as old as Y") with
bare-age anchors (`9e84465`)

Class: equative age comparatives ("the eldest sibling is TWICE AS OLD AS
that sibling") paired with bare copula age anchors left behind by a
leading-'if' clause split ("if C is 11"). The ask matched and premises
parsed, but no equative Relation was ever emitted — this is the re-cut of
`mining/cand-age-equative-relations`, which gated clean on dev in Batch 25
but failed constitution review for hardcoding the measure word `"year"` in
`src/rulekit/kernel/saturate.py`. This version fixes that: gates the
bare-age synth on a pack-declared `age_measure` category instead of a
Python string literal.

Mechanism: (1) `packs/arithmetic/rules/core.yaml` gains
`arithmetic/times-as-old-as`, the equative sibling of the live
`arithmetic/times-comparative-age-relation`, emitting the SAME Relation
shape (measure year, factor k, offset 0, `distinct: [who, std]`) so the
existing saturate fixpoint, anchored-relation-postfix and ask/how-old-is
consume it with zero further change; decline-safety via
`absent: {cat: temporal_marker}`. (2) `src/rulekit/kernel/saturate.py`
gains `synth/bare-age-anchor`, promoting a bare copula number left by a
leading-'if' split to a Quantity, ONLY when that entity already appears as
subject or standard of a Relation whose measure is in the pack-declared
`age_measure` category (`packs/core-english/categories/core.yaml`, member
`year` supplied from `packs/difg-mined/categories/semantic.yaml`), gated
via `reg.word_in_category(measure, "age_measure")` — the `currency`
pattern in `answer.py:893`/`core.yaml:65`, no measure-word literal
survives in Python.

Files: `packs/arithmetic/rules/core.yaml`, `packs/core-english/categories/core.yaml`,
`packs/difg-mined/categories/semantic.yaml`, `src/rulekit/kernel/saturate.py`,
`src/rulekit/data/registry.py`, `tests/test_mining_increment_71.py` (8 synthetic
tests).

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 5 /
BROKE 0 / DECL→WRONG 0 (SHIP; 39→44: 073920968cf0, 0f2bea45f4a6,
5bda86806af4, 7b70d37fe734, 83278256af21), dev-holdout diff SOLVED 0 /
BROKE 0 / DECL→WRONG 0 (NEUTRAL; 22→22), pytest 568 passed (was 560 + 8
new), suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant
/ fraction-of-pool, unchanged). TEST look: pending — spent manually.
in the kernel is the wrong fix.

## Batch 26 (2026-07-12) — enabler-first scouting; increment 69 landed, 70 parked

First batch with the scout aimed at DECLINE REASONS rather than phrase frequencies.
It proposed 4 candidates (not 10 — enabler-shaped work is harder to prove, and
that is the honest number).

LANDED ON MAIN: **increment 69 — sum-constraint linear systems** (a stated relation
between two holders plus a stated group total). da0cca9. dev-train 38 -> 39, SHIP,
0 BROKE. TEST look #70: 8/1 (88.9%) — precision HELD, kept.

PARKED: **increment 70 — attribute-qualified measure keys** (a qualified count noun
must not collide with its bare measure). 0 SOLVED. Branch
`mining/parked/qualified-measure-keys-enabler`, rebuilt on top of the new main so a
payoff batch can use it directly as `base`.

DROPPED AT THE SHAPE GATE: relation-standard-forms (1 of 3 walked items resolve).

### THE PIPELINE LIMITATION THIS BATCH EXPOSED (important)

Increment 70's brief said it "unblocks rest-partitions ... queued later in this
batch". **That is structurally impossible.** Every candidate in a batch is cut from
`BASE` in parallel, so `rest-partitions` was built from main WITHOUT increment 70.
Its SOLVED=0 was measured in the enabler's ABSENCE, and the goal-mode gate then
demoted it for solving nothing. The payoff was never disproved — it was never
tested.

A payoff can only build on an enabler ACROSS batches, via `base=<enabler branch>`
(the mechanism batch 24 validated). Within one batch it cannot. The scout must not
promise same-batch payoffs; propose the enabler, and let the NEXT batch cash it in
with `base` pointed at it.

NEXT BATCH: run with `base=mining/parked/qualified-measure-keys-enabler` and re-cut
`rest-partitions` on top of it — that is the first honest test of whether increment
70 is worth anything. Branch `mining/cand-rest-partitions` retained.

### Free findings from the failed rest-partitions candidate

1. It caught a real **DECL->WRONG** its guard prevented: "80 passengers, equal men
   and women, the rest are children" — the men/women split is never stated as a
   PartitionQuantity, so an unguarded rest-rule commits 80 as the children count
   against a gold of 20. A REST partition with ZERO prior sibling partitions must
   DECLINE. ("The rest" is the complement of STATED subsets.)
2. **Pre-existing bug on main, unfixed:** `_partition_membership_synth` emits a
   Quantity for the subset noun that pollutes the "unique measure in play" candidate
   set for any LATER pronoun/remnant resolution in the same document. So sequential
   membership partitions ("5 of them are dogs. The rest are cats.") mis-resolve.
   Correctly left out of scope by the junior. Worth its own increment.
## Increment 72: group-total premises phrased as verb-subject totals ("A and
B have N ITEM together", "In total, they VERB N ITEM", "N ITEM total")

Class: group-total premises whose totality is stated as a TRAILING marker on
a quantity ("... N ITEM together / altogether / all together / in total /
total") or a LEADING "In total, SUBJ VERB N ITEM" clause — the two forms
increment 69's `arithmetic/group-total-of` cannot read (it only matches the
"a total of N ITEM" tail and the bare existential aggregate form).

Mechanism: YAML-only. Two new pattern rules in
`packs/arithmetic/rules/core.yaml` beside `arithmetic/group-total-of`,
emitting the SAME existing `GroupTotal` fact kind (model.py and guards.py
untouched) that increment 69's live `synth/sum-constraint` plugin already
consumes: `arithmetic/group-total-trailing` (a stated quantity followed by a
trailing totality marker, gated on the existing `aggregate` category — the
same category `arithmetic/existential-premise-bare`'s `absent:` guard
already uses, so the marker is grammatical skeleton, not a Python word
list) and `arithmetic/group-total-leading` ("In total, SUBJ VERB N ITEM").
No new fact kind, no new consumer, no new ask shape, no new vocabulary.
Decline-safety: `arithmetic/existential-premise-bare`'s existing
`absent: {cat: aggregate}` guard keeps the same sentence from also folding
as an ordinary holding (which would double-count the number); two holders
of the measure must be in play, and `synth/sum-constraint` already declines
on multiple Relations, multiple GroupTotals, factor == -1, negative
solutions, or a third holder.

Files: `packs/arithmetic/rules/core.yaml`, `tests/test_mining_increment_72.py`
(7 synthetic tests).

Gates (integrated on staging, full re-proof): dev-train diff SOLVED 3 /
BROKE 0 / DECL→WRONG 0 (SHIP; 6925c60de387, 8229217ed5cf, dd576541c9c9),
dev-holdout diff SOLVED 1 / BROKE 0 / DECL→WRONG 0 (SHIP; 5e1c4d6456b9),
pytest 575 passed, suite 52/52, lint 0 errors / 1 known-good warning
(fraction-of-remnant / fraction-of-pool, unchanged). TEST look: pending —
spent manually.

## Increment 73: "the rest are X" remainder partitions over a stated
collection with attribute-qualified subsets

Class: premises where a collection total is stated, one or more subsets are
explicitly named as partitions (by count, percent, fraction, or plain
membership), and a trailing "the rest (of the NOUN) are/is/were ADJ NOUN"
clause states the complement — cashed against a how-many ask for the
REST label, where the label's attribute sits either postfix or PRENOMINAL.
Cut from `mining/parked/qualified-measure-keys-enabler` (increment 70) so
the enabler and this first payoff land as one increment / one TEST look —
increment 70 alone measured zero net SOLVED, because no existing ask shape
read a resolved qualified PartitionQuantity when the attribute is
prenominal ("how many GREY cats").

Mechanism: two new pattern rules in `packs/arithmetic/rules/core.yaml`,
`arithmetic/partition-rest-attribute` and
`arithmetic/partition-rest-membership`, matching the REST determiner
(instead of a number/fraction/percent slot) and emitting a
PartitionQuantity marked `is_rest=True`. `src/rulekit/kernel/saturate.py`
gains a rest-specific sizing extension to `_partition_synth` (reusing the
existing `_pool_before` helper, no new pool notion) that resolves an
`is_rest=True` PartitionQuantity to the collection total minus the signed
sum of every already-resolved SIBLING partition, only once every sibling
has itself resolved — a rest partition with ZERO stated sibling
PartitionQuantity facts declines (the "rest" is the complement of STATED
subsets only, never implied ones; caught in review as a real
DECL→WRONG risk from a prior batch's unguarded attempt). Also lands the
free finding recorded in the increment-72 entry's era of scouting:
`_partition_membership_synth`'s emitted Quantity for the subset noun was
polluting the unique-measure-in-play candidate set for later
pronoun/remnant resolution in the same document; sequential membership
partitions ("5 of them are dogs. The rest are cats.") now resolve
correctly. `answer.py`'s partition-complement consumer is unchanged — it
already reads prenominal-qualified PartitionQuantity facts once
increment 70's measure keys exist. No new vocabulary.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/saturate.py`,
`src/rulekit/kernel/answer.py`, `tests/test_mining_increment_73.py` (12
synthetic tests).

Gates (integrated on staging, full re-proof against current staging
baseline, which already carries the increment 70 enabler): dev-train diff
SOLVED 1 / BROKE 0 / DECL→WRONG 0 (SHIP; e76c3cbb053c), dev-holdout diff
SOLVED 0 / BROKE 0 / DECL→WRONG 0 (NEUTRAL), pytest 587 passed, suite
52/52, lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). TEST look: pending — spent manually.

## Batch 27 (2026-07-12) — the enabler pays off. dev-train 39 -> 48, TEST 90.9% (NEW FLOOR)

Run with `base=mining/parked/qualified-measure-keys-enabler` (increment 70), so the
payoff classes could finally be built ON the enabler.

LANDED ON MAIN (70 rides with its first payoff, per the increment-66 precedent):
- 70 (9c14fe9) attribute-qualified measure keys — the enabler, 0 SOLVED alone
- 71 (e58a849) equative age comparatives, bare-age anchors — **+5**
- 72 (73c8b49) group-total premises as verb-subject totals — **+3** (+1 holdout)
- 73 (cb689a0) "the rest are X" partitions with qualified subsets — **+1**

PARKED: 74 index-labeled entity identity (Jar A / Machine C), 0 SOLVED. Branch
`mining/parked/labeled-entity-identity-enabler`, rebuilt on the new main.

COMPOSITION GATE vs fresh main: SOLVED 9 dev-train, SOLVED 1 dev-holdout, 0 BROKE,
0 DECL->WRONG, both SHIP. suite 52/52, pytest 595, lint clean.

**TEST LOOKS #71-#73: 10/1 (90.9%) — TEST COVERAGE GAIN, NEW FLOOR (was 8/1, 88.9%).**
Look #71 (enabler 70 + 71) took TEST correct 8 -> 10; #72 and #73 held at 10/1.
First TEST coverage gain since look #64.

### Two "failures" that were nothing of the kind

- **Increment 73 IS `rest-partitions`** — the candidate batch 26 demoted for solving
  nothing. That zero was measured WITHOUT the enabler (same-batch candidates all
  build from BASE in parallel). Rebuilt on increment 70 via `base`, it solves +1.
  The payoff was never disproved; it was never tested. The enabler mechanism works.
- **Increment 71 IS `age-equative-relations`** — the candidate the constitution
  reviewer KILLED in batch 25 for hardcoding "year" in saturate.py. Re-cut with the
  pack-category fix (`age_measure` + `reg.word_in_category`), it is the batch's
  biggest single win at +5.

Both were recovered by the standards, not despite them: the reviewer's precision
about WHY it failed made the re-cut a one-line fix, and the `base` mechanism made
the payoff measurable. Record failures with their fix, and they come back.

NOTE: cherry-picking onto main conflicted in docs/HANDOFF.md (both sides append
records). Resolved as a UNION — records are append-only, there is no semantic
conflict. Expect this on every multi-increment landing.

## Batch 28 (2026-07-12) — 0 landed; the scout was probing the WRONG TREE

All 5 candidates died at the shape gate (frequencies 9, 20, 87, 101, **444**;
0–2 of 3–4 walked items resolving). Cost: one agent.

THE CAUSE WAS OURS, NOT THE SCOUT'S. The batch ran with
`base=mining/parked/labeled-entity-identity-enabler`, but **the scout probes in the
MAIN checkout** — which does not contain that enabler. So when it walked an item
and asked "does this resolve end-to-end?", it asked a kernel LACKING the machinery
the batch was built on. Every item the enabler unblocks scored `resolves: false`
and was dropped.

Same failure family as batch 26 (rest-partitions measured without its enabler) and
the batch-27 smoke (BASE never reached the reviewer). `BASE` was threaded to the
implementer, integrator, reviewer and compose agent — and NOT to the scout. That is
the fourth time a new parameter reached only some of its readers.

FIXED: on a payoff batch the scout now creates ONE read-only `scout-probe` worktree
at `$BASE` and runs every stats run, solve probe and structural-sample walk inside
it, so `resolves` reflects the tree candidates will actually be built on.

INVARIANT: **when you add a parameter, enumerate its readers.** Four for four, the
misses were caught by a self-test or a gate, never by inspection.
## Increment 74: index-labeled entity identity (Jar A / Class B / Machine C /
District 1 / house 3)

Class: premises with two or more same-noun entities distinguished only by a
trailing index label (a single uppercase letter or a bare cardinal digit) —
"Jar A has 28 marbles. Jar B has 15 marbles." — where condense.py previously
dropped the label, so both holdings folded onto one bare-lemma fact-store
key and the item declined on `conflict: fold and fold disagree`. Proven by
substitution: replacing the labels with distinct proper names made
83ed471741f9 return the gold answer through the existing combined consumer
with no other change; this increment gives the SAME resolution path to the
label-bearing text itself. INFRASTRUCTURE — this is the enabler; it does
not itself unlock the labeled-collective totality asks ("how many do all 4
houses have in total", "how many total X in Districts 1-3") that motivated
it. Those need a follow-on ask-shape class layered on this seam.

Mechanism: a condense.py merge pass mirroring increment 25's merge-
possessive byte-for-byte, one field over: a common noun immediately
followed by a single uppercase letter or a bare cardinal index fuses into
ONE noun unit carrying a `label` feature, gated on SENSE names only (the
`unknown` sense for a bare capital with no lexicon entry, the `article`
sense for "a"/"A", and numeral senses for the digit form) — never a
lexicon word list, so no vocabulary is admitted and noise cases ("if I",
"A.T. Cross", "Mr. B") are excluded structurally. Quantity.entity is
unchanged (bare lemma), so existing coreference ("the jar ... it ...")
still works; the label is read only by `FactStore.admit`'s collision
handling, which now re-keys a same-key VALUE conflict between two
DIFFERENT non-null labels to `entity[label]` and admits both separately
instead of quarantining — the increment-25 `owner` design, one field over.
Also drops bare labeling capitals out of the unknown-word ceiling.

Files: `src/rulekit/kernel/condense.py`, `src/rulekit/kernel/model.py`,
`src/rulekit/kernel/facts.py`, `src/rulekit/kernel/learn.py`,
`tests/test_mining_increment_74.py` (8 synthetic tests).

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SOLVED 0 / BROKE 0 / DECL→WRONG 0 (NEUTRAL;
39/3772 correct before and after — the two known latent-WRONG substitution
items this enabler could have exposed, per the candidate brief, did not
land as commits on this dev slice), dev-holdout diff SOLVED 0 / BROKE 0 /
DECL→WRONG 0 (NEUTRAL; 22/3701 correct before and after), pytest 595
passed, suite 52/52, lint 0 errors / 1 known-good warning (fraction-of-
remnant / fraction-of-pool, unchanged). TEST look: pending — spent
manually.

## Increment 75: collective-subject totality asks (prenominal totality
marker, quantified/cardinal collective subject)

Class: asks whose collective subject already denotes the full group but
whose surface form falls outside `ask/how-many-plural-combined`
(increment 67) because the totality signal sits in a different position —
"how many total toys do the boys have?" (aggregate marker PRENOMINAL,
before the item noun, instead of trailing), "how many cookies do THESE
THREE boys have?" (no marker at all; an explicit cardinal on the subject
alone licenses the totality read), "how many points did ALL THREE friends
score together?" (leading quantifier 'all'/'both' on the subject, marker
still trailing). All three sample items' premises already fold to one
Quantity per holder; the gap was purely in ask recognition.

Mechanism: YAML-only, `packs/arithmetic/rules/core.yaml`, three new
sibling ask ids beside the byte-identical `ask/how-many-plural-combined`
(none of that ask's own match block touched): (a)
`ask/how-many-plural-combined-prenominal-marker` — an optional
`{slot: pre, cat: aggregate}` consumed between "how many|much" and
`{slot: item}`; (b) `ask/how-many-plural-combined-quantified-subject` —
the subject NP's leading `opt: {lit: the}` widens to also accept a
`quantifier`-sense word ('all'/'both'), trailing aggregate marker still
required; (c) `ask/how-many-plural-combined-cardinal-subject` — an
explicit cardinal on the subject ("these three boys", "all three
friends") licenses totality on its own, marker becomes optional, gated
strictly on the cardinal's presence so a bare "how many cookies do the
boys have?" still declines. The cardinal is consumed via the existing
`who_value: "{who.value}"` precedent. Consumer is the EXISTING `combined`
(answer.py untouched) — it already enumerates every holder of the
measure from the facts. All three new ask ids consume strictly more
units than the bare asks they sit beside, so max-consumed-units matching
cannot create a partial-match tie with them.

Files: `packs/arithmetic/rules/core.yaml`,
`tests/test_mining_increment_75.py` (8 synthetic tests).

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SOLVED 3 / BROKE 0 / DECL→WRONG 0 (SHIP;
92f395fa1709, 9a46ef7a9e2e, f59cecc6c642; 48→51/3772 correct), dev-holdout
diff SOLVED 0 / BROKE 0 / DECL→WRONG 0 (NEUTRAL; 23/3701 correct before
and after), pytest 603 passed, suite 52/52, lint 0 errors / 1 known-good
warning (fraction-of-remnant / fraction-of-pool, unchanged). TEST look:
pending — spent manually.

## Increment 76: complement-labeled subset asks (the ask names the
complementary label of a stated partition, not its negation)

Class: asks where the premise states a collection total plus ONE
fractional/spelled-fraction/percent membership partition naming a single
subgroup noun (e.g. "N are boys"), and the ask names the COMPLEMENTARY
label ("how many girls...") rather than the same label or its bare
negation. Three surface variants: (a) "how many <complement> are in the
<place>?" (routes to `ask/how-many-in-place`, previously died on "no
quantity known" because only the stated subset had a Quantity); (b) "how
many OF THE <collection> are <complement>?" (a partitive ask form with no
matching ask id before this increment); (c) a bare-existential collection
held by the scene (`world`), introduced by a leading place PP, asked via
"how many <complement> are at this <place>?" (the named place holds no
facts of the measure, only `world` does).

Mechanism, three pieces: (1) pack data — a complementary-pair relation
(boy<->girl only; neither word in `packs/difg-mined/quarantine.yaml`) in
`packs/core-english/categories/core.yaml`, declared as a word fact (not a
Python list), licensing exhaustiveness only for pairs an author has
vetted rather than any arbitrary unstated sibling noun (increment 16's
refusal still holds for unpaired words). (2) `saturate.py` —
`_partition_synth` gains an ADDITIVE branch: when the asked measure has
zero facts, exactly one non-fraction membership PartitionQuantity exists
over a collection whose total resolves to exactly one holder, and the
asked noun is the pack-declared complement of the partition's stated
attribute, emit a Quantity for the asked measure = total − subset, keyed
on the collection's own holder entity. Declines on a second stated
partition over the same collection, an ambiguous total, or an asked noun
with no declared complement; increment 73's rest-partition path is
untouched (separate branch). (3) YAML — a new "how many OF THE COLLECTION
are LABEL" partitive ask form routed to the existing entity-less consumer
(no new consumer), plus a decline-safe fallback on
`ask/how-many-in-place`'s single-entity consumer: when the named place
holds no facts of the asked measure and exactly one holder (`world`)
exists anywhere in the document, fall back to that holder — this can only
convert a decline into a commit, never move an already-committed answer.

Files: `packs/core-english/categories/core.yaml`,
`packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/saturate.py`,
`src/rulekit/kernel/answer.py`, `tests/test_mining_increment_76.py` (9
synthetic tests).

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SOLVED 3 / BROKE 0 / DECL→WRONG 0 (SHIP;
390d5fa105b6, 8da249810ab0, c09e5d318bb5; 51→54/3772 correct), dev-holdout
diff SOLVED 0 / BROKE 0 / DECL→WRONG 0 (NEUTRAL; 23/3701 correct before
and after), pytest 612 passed, suite 52/52, lint 0 errors / 1 known-good
warning (fraction-of-remnant / fraction-of-pool, unchanged). TEST look:
pending — spent manually.

## Batch 28-rerun (2026-07-12) — the scout-probe fix, immediately vindicated

Same base, same scout, same 5-candidate ask as the batch that landed NOTHING an hour
earlier. The only change: the scout now probes on `$BASE` instead of main.

LANDED (74 rides with its payoffs — the enabler proved itself):
- 74 (82c3257) index-labeled entity identity — the enabler, 0 SOLVED alone
- 75 (afe6966) collective-subject totality asks — **+3**
- 76 (b8a52cb) complement-labeled subset asks — **+3**

COMPOSITION GATE vs fresh main: SOLVED 6 dev-train, 0 BROKE, 0 DECL->WRONG, SHIP.
dev-train 48 -> 54. TEST looks #74, #75: both 10/1 (90.9%) — precision HELD.

`collective-totality-asks` is the SAME slug the shape gate dropped in the broken run
(and in batch 25). It was never a bad candidate; we were asking a kernel that lacked
the enabler whether the enabler's items resolved. Measure on the tree you will build
on.

## Batch 29 (2026-07-12) — 0 landed on bare main. The pattern is now conclusive.

All 5 candidates dropped at the shape gate (frequencies 103, 137, 137, 178, 252;
0–1 of 3–4 walked items resolving). The scout probed main correctly this time, so
this is a GENUINE result, not the batch-28 measurement bug.

| batch | base | landed | dev-train |
|---|---|---|---|
| 25 | main | 0 of 10 | — |
| 26 | main | 1 | +1 |
| 27 | **enabler** | 4 | **+9** |
| 28 | **enabler** | 2 | **+6** |
| 29 | main | **0 of 5** | — |

**Every batch that moved the number was built on an ENABLER. Every batch built on
bare main has stalled.** The remaining ~3,718 dev-train declines are blocked on
STRUCTURE, not on missing ask shapes.

### The fix: a blocked class IS an enabler brief

Batches 25 and 29 dropped TEN classes between them and produced ZERO enabler briefs
from that evidence. That is ten diagnoses thrown in the bin. A class with 0 of 3
walked items resolving at frequency 252 is not a dead end — it is a BLOCKER, already
proven to exist by the walking the scout just did.

The scout must now CONVERT a blocked class into an infrastructure brief: diagnose why
the items don't resolve, propose the missing structure as the enabler, set
`unblocks` to the class it just walked, and mark those same walked items
`resolves_after_unblocks: true`. The evidence for the enabler IS the failure of the
coverage class — it is handed to us for free.

If the scout cannot prove a coverage class, that is not an empty batch. It is an
ENABLER batch.

## Batch 30 (2026-07-13) — the scout produced an ENABLER. The conversion instruction works.

First batch after "a blocked class IS an enabler brief". The scout came back with a
structural brief instead of five coverage classes that don't resolve.

PARKED: **increment 77 — container-content bridge** (N containers x per-container
contents -> the holder's content total). An infrastructure synth in saturate.py:
use-gated (sentence=-1), raw-fold-only, single-hop. dev-train NEUTRAL (0 SOLVED),
dev-holdout SHIP +1 (23 -> 24). pytest 616, suite 52/52, lint clean.

Branch: `mining/parked/container-content-bridge-enabler` (rebuilt on main).
NOT landed and NO TEST look spent — a 0-dev-train-SOLVED increment cannot advance the
100 goal and a look on it can only LOSE precision. It rides with its payoff, per the
increment-66/70/74 precedent (all three of which paid off once cashed in).

Dropped at the shape gate: partitive-content-keys (70), more-quantifier-transparency
(76), resource-capacity-consumer (128), ask-side-qualified-measure (4).

NEXT: batch 31 runs with `base=mining/parked/container-content-bridge-enabler`.
## Increment 77 (2026-07-13) — container-content bridge (infrastructure)

Class: a Quantity whose ENTITY is another Quantity's MEASURE — a holder's
container COUNT bridged with a per-container content RATE into the holder's
derived content total ("Priya bought 6 boxes of marbles. Each box has 9
marbles." folds to two independently-true facts nothing previously
connected into "Priya bought 54 marbles"). New `synth/container-contents`
plugin in `saturate.py`: when a Quantity CR has entity == C and measure ==
I (a per-container content rate) and a DIFFERENT Quantity H has measure ==
C (the holder's container count), emit Quantity(entity=H.entity,
measure=I, value=H.value*CR.value, verb=H.verb). Restricted to raw-fold
facts only (never another synth's output) for a stable single-hop
fixpoint; decline-safe on exactly-one container-rate per (C, I), holder ≠
container, holder not already holding a Quantity of measure I, and shared
`time`. Emitted at sentence=-1 (the existing SynthRule datalog
convention) so it is use-gated, not existence-gated, per the look #4–7
invariant.

Infrastructure: 0 SOLVED on dev-train by design — this increment adds no
ask-shape consumer, it only makes the bridged fact available to whichever
consumer already reads a plain Quantity(entity, measure, verb). The
payoff class (container-content totality asks) is parked as the next
batch, based on this branch per the batch-27/28 lesson.

Files: `src/rulekit/kernel/saturate.py`, `tests/test_mining_increment_77.py`
(4 synthetic tests).

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff NEUTRAL, 0 BROKE, 0 DECL→WRONG (54/3772 correct
before and after); dev-holdout diff SHIP, SOLVED 1 (85bf6abfa0d2), 0
BROKE, 0 DECL→WRONG (23→24/3701 correct); pytest 616 passed; suite
52/52; lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). TEST look: pending — spent manually.

## Increment 78 (2026-07-13) — superordinate totality asks over same-holder
subtype comparatives (payoff, on increment 77's container-content bridge
branch)

Class: a superordinate totality ask ("how many children/toys/fish does he
have?") over an entity whose stated facts are all same-holder SUBTYPE
comparatives of that superordinate ("twice as many daughters as sons",
"N more X than Y" chains) rather than a direct fact for the superordinate
measure itself. Three-piece mechanism: (1) `saturate.py`
`_relations_synth` gains a strictly-additional same-holder SUBTYPE anchor
branch — when a Relation's `standard` is not another entity's holding but
IS a DIFFERENT measure the relation's own subject already holds, the
relation resolves against that subject-held quantity; the pre-existing
fixpoint driver reruns every synth each round so chained standards (A
derived from B, C derived from A) resolve with no extra loop. (2) The
additive "N more X than Y" pattern (`packs/arithmetic/rules/core.yaml`)
now emits a Relation (not just a bare Predication) when the "than"
standard is a same-holder measure. (3) A new `answer.py` consumer,
`_superordinate_total`, sums an entity's own subtype holdings into the
asked superordinate measure — gated on an explicit, opt-in
`superordinate: true` category flag (`packs/core-english/categories/core.yaml`,
`packs/difg-mined/categories/semantic.yaml`) naming the superordinate word
and its exhaustive subtype members (child: daughter/son; toy:
soldier/car; fish: goldfish/angelfish/guppy) — deliberately a separate
flag from bare category `members`, since pre-existing categories
(animal/pet) declare partial member lists for an unrelated purpose and
reading `members` alone would silently under-count. Also accepts the
optional prenominal `aggregate` marker (increment 75 precedent) on the
single-entity ask.

Files: `src/rulekit/kernel/saturate.py`, `src/rulekit/kernel/answer.py`,
`packs/core-english/categories/core.yaml`,
`packs/difg-mined/categories/semantic.yaml`,
`packs/arithmetic/rules/core.yaml`, `tests/test_mining_increment_78.py`.

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SHIP, SOLVED 3, 0 BROKE, 0 DECL→WRONG
(54→57/3772 correct; SOLVED 1a0944559f81, 397d6a52403e, f5d2b1bcc320);
dev-holdout diff SHIP, SOLVED 1, 0 BROKE, 0 DECL→WRONG (24→25/3701
correct; SOLVED 7822e5e02965); pytest 622 passed; suite 52/52; lint 0
errors / 1 known-good warning (fraction-of-remnant / fraction-of-pool,
unchanged). TEST look: pending — spent manually.

## Batch 31 (2026-07-13) — enabler 77 cashed in. dev-train 54 -> 57, holdout 23 -> 25.

Run with `base=mining/parked/container-content-bridge-enabler`.

## Increment 79 (2026-07-13) — extraposed-duration rate premises (infrastructure)

Class: the extraposed-infinitive duration idiom ("it takes/took WHO N
TIMEUNIT to VERB M ITEM") read as a PREMISE, not just as an ask. Today
this idiom's duration folds as a bare Quantity on the entity; nothing
turns it into a Rate, so the existing rate-span-inverse consumer
(`answer.py`) can never fire on it even though the identical rate stated
in SVO form ("Dev can wash 4 windows in 10 minutes") already commits.
Two-piece mechanism, YAML-first: (1) registers `rate` as a
pattern-emittable fact kind — `"rate": Rate` added to `_FACT_CLASSES`
(`src/rulekit/kernel/patterns.py`) and `"rate"` added to `FactEmit.fact`
(`src/rulekit/data/schemas.py`); additive only, Rate was previously
emitted only from `learn.py`. (2) new pattern rule
`arithmetic/extraposed-duration-rate`
(`packs/arithmetic/rules/core.yaml`), minimum-structure `it <duration_verb>
WHO SPAN to VERB ITEM`, emitting a compound Rate (value = item/span,
numerator/denominator preserved) exactly mirroring learn.py's
`_compound_rate_span` SVO branch, SVO-inverted; `consumes: [span, item]`
suppresses the redundant bare-Quantity fold on the same span/item pair
(a compound rate is never a holding — the increment-58 invariant). The
new `take/takes/took` duration-verb gate is a category declared in
`packs/difg-mined/categories/semantic.yaml`, not a Python word list. Rate
is already use-gated (guards.py `rate_values` + `log.uses_value`), so no
new value-accounting decision was needed.

Infrastructure: 0 SOLVED on dev-train by design — every dev-train item
carrying this premise idiom also needs one of two ask-side widenings
(a totality-marked asked item, or a conjoined multi-rate item list),
both parked as the next batch's payoff on this branch, per the
batch-27/28 (increment 77/78) precedent. Consumer chain already proven
by probe: the SVO-form rate commits 160.0 on "Dev can wash 4 windows in
10 minutes. How many minutes will it take Dev to wash 64 windows?"; this
increment only supplies the missing Rate for the extraposed-premise
form.

Files: `packs/arithmetic/rules/core.yaml`,
`packs/difg-mined/categories/semantic.yaml`,
`src/rulekit/kernel/patterns.py`, `src/rulekit/data/schemas.py`,
`tests/test_mining_increment_79.py` (6 synthetic tests).

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff NEUTRAL, 0 BROKE, 0 DECL→WRONG (57/3772 correct
before and after); dev-holdout diff NEUTRAL, 0 BROKE, 0 DECL→WRONG
(25/3701 correct before and after); pytest 628 passed; suite 52/52; lint
0 errors / 1 known-good warning (fraction-of-remnant / fraction-of-pool,
unchanged). TEST look: pending — spent manually.

LANDED: 77 (e635cd1) container-content bridge — the enabler, rides with its payoff.
        78 (c15a73b) superordinate totality asks over same-holder subtype
        comparatives ("twice as many daughters as sons ... how many children") — +3.

COMPOSITION GATE vs fresh main: SOLVED 3 dev-train + 2 dev-holdout, 0 BROKE,
0 DECL->WRONG, both SHIP. TEST look #76: 10/1 (90.9%) — precision HELD.

THE TWO-STROKE RHYTHM IS NOW THE METHOD (4 for 4):
  enabler batch on main (finds the blocker, parks it, 0 coverage)
  -> payoff batch on that enabler (cashes it in)
Enabler bases: 66 -> +9, 70 -> +6, 74 -> +6, 77 -> +5. Bare-main coverage batches:
0 of 10, 0 of 5. A single batch is HALF a cycle; the honest unit of progress is the
pair. Do not read an enabler batch's 0 coverage as a failed batch.

## Batch 32 (2026-07-13) — enabler batch: increment 79 parked

Scout returned one structural brief (the conversion instruction is holding).

PARKED: **increment 79 — extraposed-duration rate premises** ("it takes WHO N
TIMEUNIT to VERB M ITEM"). NEUTRAL on dev-train AND dev-holdout (0 SOLVED),
pytest 628, suite 52/52, lint clean.
Branch: `mining/parked/extraposed-duration-rates-enabler`. No TEST look spent.

NEXT: payoff batch on `base=mining/parked/extraposed-duration-rates-enabler`.
## Increment 80 (2026-07-13) — asked-item resolution in duration-rate inverse-span asks (totality-marked item, unit-mismatched asked time unit, 'for'-variant, conjoined item list) — the payoff for increment 79

Class: asked-item resolution in duration-rate inverse-span asks — the payoff
for increment 79's extraposed-duration-rate premise Rate. Four coordinated
pieces, all on the two EXISTING inverse-span asks
(`ask/how-long-take-span`, `ask/how-many-timeunit-take-span`,
`packs/arithmetic/rules/core.yaml`) and the EXISTING `rate-span-inverse`
consumer (`answer.py`) — the forward `rate-span` consumer/branch stays
byte-for-byte untouched. (1) TOTALITY ITEM: the asks' `item` slot also
binds a totality-marked bare noun ("all (of) the X"), and rate-span-inverse
resolves the count from the entity's own uniquely stated Quantity of that
measure, declining on zero or ambiguous totals. (2) ASKED-UNIT CONVERSION:
when the ask names a time unit differing from the committing Rate's `per`
unit, the same static `reg.conversions` lookup the forward rate-span
consumer already applies now fires here too, instead of an outright
decline; ambiguous/absent conversion still declines. (3) FOR-VARIANT: an
optional `{lit: for}` before the `who` slot in both asks ("how long does
it take FOR WHO to VERB N ITEM"), pure grammatical skeleton. (4) CONJOINED
ITEM LIST: an article-singular item in a duration-rate premise counts as
one (implicit-one); the elided conjunct in "N TU to VERB a X and M TU to
VERB a Y" distributes the extraposed/SVO subject+verb so both Rates emit;
the ask's `item` becomes a list of counted items and the consumer sums
item_i / rate_i, declining unless every asked item has exactly one
matching Rate (never a partial sum). Piece 4's premise-side widening
(`learn.py::_compound_rate_span`) is opt-in, defaulted to today's
behavior — the increment-11/18 shared-scan invariant.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/answer.py`,
`src/rulekit/kernel/patterns.py`, `src/rulekit/kernel/learn.py`,
`tests/test_mining_increment_80.py` (11 synthetic tests; also updates two
pre-existing tests in `test_mining_increment_51.py` /
`test_mining_increment_55.py` whose asserted "mismatched-unit always
declines" behavior is superseded by piece 2).

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SHIP, SOLVED 2 (1cfb8c5f4161, 81fc6d6693fd), 0
BROKE, 0 DECL→WRONG (57→59/3772 correct); dev-holdout diff NEUTRAL, 0
BROKE, 0 DECL→WRONG (25/3701 correct before and after); pytest 640 passed;
suite 52/52; lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). TEST look: pending — spent manually.

LANDED: 79 (b18e4da) extraposed-duration rate premises — the enabler, rides with its payoff.

## Batch 33 (2026-07-13) — enabler 79 cashed in. dev-train 57 -> 59.

LANDED: 79 (extraposed-duration rate premises, the enabler) + 80 (asked-item
resolution in duration-rate inverse-span asks — totality-marked item, unit-mismatched
asked time unit, "for"-variant, conjoined item list).

Composition gate vs fresh main: SOLVED 2 dev-train, 0 holdout, 0 BROKE,
0 DECL->WRONG. TEST look #77: 10/1 (90.9%) — precision HELD.

ENABLER YIELD IS DECLINING: 66 -> +9, 70 -> +6, 74 -> +6, 77 -> +5, 79 -> +2.
Still positive, still the only thing that works, but the seam is thinning. Watch this.

## Increment 81 (2026-07-13) — money-left asks over a gifted budget and container-partitive priced purchases

Class: money-left asks over a GIFTED budget ("X's RELATIVE gave him/her $N
...") and container-partitive priced purchases ("N CONTAINER of ITEM ...
each CONTAINER of ITEM costs $Y"). Two coordinated, strictly-additional
structural pieces. (1) POSSESSOR ANTECEDENT
(`document.py::_possessor_antecedent`, a new fallback inside
`_bind_discourse`): a possessive determiner merged into the clause
SUBJECT's NP is a legitimate antecedent for a NON-subject pronoun bound as
that same verb's own argument — "Clare's mother gave her $47" -> her =
clare (Principle B: an object pronoun cannot corefer with its own clause
subject). Fires ONLY as a fallback when no unique prior-sentence
antecedent exists; the pre-existing cross-sentence path is unchanged and
always takes priority. Paired with
`packs/arithmetic/rules/transfer.yaml`'s `giver` slot widened from
`type: name` to `type: entity` (name OR common noun, e.g. "mother"/
"uncle"). (2) CONTAINER-NOUN PARTITIVE PRICE ANCHOR
(`learn.py::_measure_partitive_anchor`): widened to key a `price_verb`
subject's Price on ANY partitive head that the purchase Quantity itself
already keys on (not just known measure units in `reg.conversions`), so
Price.item and Quantity.measure agree by construction; gated to fire only
when a matching purchase Quantity exists for the same entity. (3) The
partitive SECOND conjunct of a purchase list ("4 loaves of bread and 2
cartons of milk") now resolves via `_conjoined_purchase_items` taking the
partitive head of each segment. No `answer.py` change — the existing
increment-10 purchase-total and money-left consumer already read
Price/Quantity by matching noun.

Files: `src/rulekit/kernel/document.py`, `src/rulekit/kernel/obligations.py`,
`src/rulekit/kernel/learn.py`, `packs/arithmetic/rules/transfer.yaml`,
`tests/test_mining_increment_81.py`.

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SHIP, SOLVED 1 (af5cc0edbf84), 0 BROKE, 0
DECL→WRONG (59→60/3772 correct); dev-holdout diff NEUTRAL, 0 BROKE, 0
DECL→WRONG (25/3701 correct before and after); pytest 645 passed; suite
52/52; lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). TEST look: pending — spent manually.

## Increment 82 (2026-07-13) — relations whose subject or standard is an index- or ordinal-labeled entity (Jar A / house 3 / the second box)

Class: relations whose subject or standard is an index- or ordinal-LABELED
entity ("Jar A", "house 3", "the second box"). INFRASTRUCTURE (this
batch's one enabler): increment 74 made index/ordinal labels first-class
on Quantity only (a `label` field plus FactStore collision-time re-key),
but a RELATION between two labeled entities ("Jar B has 12 more marbles
than jar A") emitted NOTHING — the relation pattern rules' `who`/`std`
slots (already `type: entity`, so they structurally accept a labeled
common noun) still bare-fold both sides to the same lemma ('jar'), and
every `distinct: [who, std]` self-reference guard treated that as "X
compares to itself" and silently declined the whole relation. Mechanism
(kernel + YAML, additive only): (1) `_check_where`'s `distinct` predicate
(`patterns.py`) now compares (lemma, label) pairs instead of bare lemma
alone — two units sharing a lemma AND carrying two DIFFERENT non-null
labels are no longer treated as the same referent; every existing
`distinct` check where both sides are unlabeled (label=None on both)
compares exactly as before. (2) `Relation` (`model.py`) gains
`subject_label`/`standard_label` fields, defaulting to None, so every
existing fact is byte-identical. (3) `saturate.py::_relations_synth`
resolves a labeled standard against the `entity[label]` fact key
FactStore.admit already produces, and emits the derived Quantity carrying
the subject's label. No consumer change: the existing combined /
entity-less-totality consumers already sum labeled holders. Cashes in
immediately on one dev-train item (three index-labeled containers chained
by relations, entity-less totality ask); the rest of the named payoff
class (labeled in-place existentials as holders, labeled-entity
single-entity/place asks) is left for the next batch to build on this
branch, per brief.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/patterns.py`,
`src/rulekit/data/schemas.py`, `src/rulekit/kernel/model.py`,
`src/rulekit/kernel/saturate.py`, `tests/test_mining_increment_82.py`.

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SHIP, SOLVED 1 (83ed471741f9), 0 BROKE, 0
DECL→WRONG (60→61/3772 correct); dev-holdout diff NEUTRAL, 0 BROKE, 0
DECL→WRONG (25/3701 correct before and after); pytest 655 passed; suite
52/52; lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). TEST look: pending — spent manually.

## Increment 83 (2026-07-13) — conjoined event-verb object lists (each conjunct is its own event, bound to its own counted noun)

Class: conjoined EVENT-verb object lists where each conjunct is its own
event bound to its own counted noun ("sold 3 boxes to her aunt and 4
boxes to her uncle", "lost 20 chickens, 8 turkeys and 5 guinea fowls").
INFRASTRUCTURE (zero-risk enabler, not yet cashed in by any consumer on
dev): today `Quantity.occurrence` is the SENTENCE index, so two event
Quantities emitted from one sentence collide on `key()` and quarantine as
"fold and fold disagree" — 132 dev-train items carry exactly this
conflict bucket, the 4th-largest decline reason and the largest
non-ask-shape structural one. Mechanism (kernel-structural, no lexicon,
no per-problem parsing): (1) `learn.py` generalizes the segment-wise
conjunct-binding helper that increments 11/18 built for purchase verbs
(and 35 for state verbs) to EVENT-category verbs — polarity-tagged
acquire/lose/produce/receive members (the category is the gate, never a
word list) — so each comma/conjunction-segmented conjunct after the
first takes its OWN counted noun, inheriting the head noun by ellipsis
when a segment has a count but no noun of its own (precedented by
increment 80's elided-conjunct distribution). The shared
`_is_rate`/`_price_each_value` clause-boundary scans are untouched —
segmentation is opt-in per verb category, defaulted to today's behavior.
(2) `model.py`/`facts.py`: `Quantity` gains an optional `segment` field
(within-sentence conjunct index, default None) so every existing fact is
byte-identical; each conjunct now gets a distinct `key()` via its segment
position (NOT via its value — `FactStore.admit` still collides on equal
values from DIFFERENT segments correctly as two summable facts, avoiding
the undercount trap where two same-valued conjuncts would otherwise
silently dedupe). The existing Sigma-events fold in `answer.py` sums the
now-distinct facts with no consumer change. Confirmed by design as a
clean enabler: dev-train cannot cash this in alone (every item unblocked
by the fold fix carries a second, independent blocker — a remainder
consumer, a goal-deficit consumer, or a unit-converted event-total
consumer, none of which exist yet); those consumers are left for the
next payoff batch, per brief.

Files: `src/rulekit/kernel/learn.py`, `src/rulekit/kernel/model.py`,
`src/rulekit/kernel/facts.py`, `tests/test_mining_increment_83.py`.

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff NEUTRAL, 0 SOLVED, 0 BROKE, 0 DECL→WRONG
(60/3772 correct unchanged, 0 wrong); dev-holdout diff NEUTRAL, 0 SOLVED,
0 BROKE, 0 DECL→WRONG (25/3701 correct unchanged, 0 wrong); pytest 659 passed (+9 synthetic
tests in `tests/test_mining_increment_83.py` over the prior staging
baseline); suite 52/52; lint 0 errors / 1 known-good warning
(fraction-of-remnant / fraction-of-pool, unchanged). TEST look: pending
— spent manually.

## Increment 84 (2026-07-13) — partitive-measure asks ("how many MEASURE of SUBSTANCE ...") — the item slot cannot represent a partitive NP

Class: partitive-measure asks — questions that name the measure through a
partitive NP ("how many kilograms of meat are left?", "how many containers
of the substance were left?") rather than a bare measure noun. INFRASTRUCTURE
(enabler, cut from the parked `mining/parked/conjoined-event-conjuncts-enabler`
branch): every existing ask id binds `item` as a single `{type: noun}` slot,
so a partitive NP (MEASURE + `of` + SUBSTANCE) matches none of them and 71
dev-train items decline on "no ask shape recognizes this question" before any
premise or consumer is ever consulted. Walked all 71 by stripping only the
partitive tail: 0/71 resolve today — confirming this is a pure ask-shape
blocker, not a coverage gap needing new arithmetic.

Mechanism (no new slot TYPE; reuses the existing optional sub-sequence
machinery already precedented by ask/how-many-of-collection-are-label):
`packs/arithmetic/rules/core.yaml` — `ask/how-many-there`,
`ask/how-many-left-entityless`, and `ask/how-many-there-combined` each gain
an optional `[{lit: of}, {slot: substance, type: noun}]` group right after
their existing `item` slot. `item` still binds ONLY the bare measure noun
exactly as every existing bare-measure ask already does; the group exists
purely so the trailing "of SUBSTANCE" NP is CONSUMED instead of breaking the
match. When more than one substance shares the same measure noun, the ask
DECLINES rather than guessing which substance's quantity to report — same
discipline as increment 26's non-interchangeable categories, and the named
hazard (a partitive ask silently answering the wrong substance's question)
is covered by a synthetic multi-substance DECLINE test. Applied to a NAMED,
SHORT list of three existing ask ids, never find-replaced across the ~48
asks (HANDOFF invariant: a widened slot type must be applied to the specific
ask ids that need it). With the slot in place these route to consumers that
ALREADY exist (the signed event fold, the entity-less Σ, the multi-holder
combined Σ) — payoff lands next rather than needing new arithmetic.

Files: `packs/arithmetic/rules/core.yaml`, `tests/test_mining_increment_84.py`
(plus schema/pattern support files carried from the candidate branch).

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff NEUTRAL, 0 SOLVED, 0 BROKE, 0 DECL→WRONG
(60/3772 correct unchanged, 0 wrong); dev-holdout diff NEUTRAL, 0 SOLVED,
0 BROKE, 0 DECL→WRONG (25/3701 correct unchanged, 0 wrong); pytest 667
passed (+8 synthetic tests in `tests/test_mining_increment_84.py` over the
prior staging baseline of 659); suite 52/52; lint 0 errors / 1 known-good
warning (fraction-of-remnant / fraction-of-pool, unchanged). TEST look:
pending — spent manually.

## Batch 34 (2026-07-13) — FIRST PRECISION DROP OF THE RUN. Increment 81 killed.

Bare-main batch, 2 landed on staging, ONE SURVIVED.

- **increment 81 (gifted-budget money-left asks) — KILLED at TEST look #78.**
  DEV was immaculate (dev-train 59->60 SHIP, holdout NEUTRAL, suite 52/52, review
  passed). TEST: **11/2 = 84.6%**, down from 90.9% — a new confident-wrong. REVERTED.
  See docs/negative-results.md. Branch `mining/cand-gifted-budget-money-left` kept.
- **increment 82 (relations with index-/ordinal-LABELED subjects: Jar A, house 3, the
  second box) — HELD.** Its look #79 was CONTAMINATED (taken with 81 present, read
  11/2), so it was re-cut onto bare main and given its own look #80: **10/1, 90.9%.**
  Landed (2a34ec2). dev-train 59 -> 60.

THREE LOOKS SPENT (#78 kill, #79 contaminated, #80 clean re-measure). Worth it: a
contaminated look is not evidence about the increment above the bad one. Re-measure in
isolation or you discard good work along with the bad.

**A clean DEV gate is necessary but never sufficient.** 7,473 DEV items said increment
81 was safe. TEST disagreed. This is why looks are rationed and why DEV-clean is not a
licence to land.

## THE SEAM WAS MISDIAGNOSED (2026-07-13) — mine the fully-read / no-ask-shape pool

I told the scout on 2026-07-12 that "the ask-shape seam is worked out". **That was
wrong**, and it cost several batches. The measurement that settles it, at dev-train
= 60:

| | |
|---|---|
| dev-train items | 3,772 |
| fully-read (every word known) | 1,472 |
| ...of which DECLINE | **1,412** — the addressable pool |
| ...declining on `no ask shape recognizes this question` | **728** |

**728 items — 52% of the addressable pool — are fully readable and fail ONLY because
no ask shape matches the question.** The rest of the tail is negligible (51
fold-conflicts, then single digits). `bench` was telling us this all along in the
coverage factorization: `fully-read 39.0% × hit-rate 4.1%` — we can READ 39% of
items and ANSWER 4% of what we read.

WHY THE EARLIER ASK-SHAPE HUNTS FAILED — and it was our fault, not the seam's.
Batches 23–29 drew candidates from SURFACE-FREQUENCY worklists, which are dominated
by the 61% of items carrying UNKNOWN WORDS. Such an item cannot resolve whatever ask
you add: vocabulary blocks it first. So the scout proposed asks over unreadable
items, they failed end-to-end, the shape gate killed them, and the seam looked
exhausted. It was a sampling error, not a finding.

THE FIX: the scout now draws candidates ONLY from the fully-read AND `no ask shape`
intersection, clusters them by QUESTION SHAPE, and proposes the biggest clusters
whose premises already resolve. The shape gate is unchanged and still binding — but
in this pool a real ask-shape family should clear it easily, because the ask is the
only missing piece. A cluster that STILL fails to resolve is a genuine blocker, and
becomes an enabler brief.

Enabler yield was declining anyway (+9, +6, +6, +5, +2) — consistent with the
enabler path being a detour around a mis-sampled pool rather than the main seam.

## Batch 35 (2026-07-13) — increment 83 parked (last batch on the OLD targeting)

PARKED: **increment 83 — conjoined event-verb object lists** (each conjunct is its own
event, bound to its own counted noun). Both diffs NEUTRAL (0 SOLVED), pytest 659,
suite 52/52, lint clean. Branch `mining/parked/conjoined-event-conjuncts-enabler`.
No TEST look spent.

This was the last batch scouted under the surface-frequency worklist. From batch 36 the
scout runs on the ADDRESSABLE POOL with the yield gate (methodology §9). Batch 36 runs
on `base=mining/parked/conjoined-event-conjuncts-enabler` so the enabler rides with
whatever the new targeting wins.

## Batch 36 (2026-07-13) — first batch on the YIELD-BASED targeting. It found the real blocker.

LANDED (0 coverage, PARKED): **increment 84 — partitive-measure asks: THE ITEM SLOT
CANNOT REPRESENT A PARTITIVE NP.** Composition gate PASS (0 BROKE, 0 DECL->WRONG on both
slices, suite 52/52, pytest 667) but `solved_vs_main = 0`.

READ THAT CORRECTLY. It is not a failed ask shape. The scout walked the **70-item
partitive-measure family** (the pool's 4th-biggest), found the items do not resolve, and
diagnosed WHY: the ask's item slot has no way to hold "cups OF milk" as one thing. So it
produced the ENABLER for a 70-item family — exactly what §9 targeting is supposed to do.
The old targeting was finding 3-5 item classes.

CALIBRATION (first data point, methodology §9.4):
  partitive-measure family — pool_frequency ~70, solved_vs_main 0.
  Expected: what landed was the ENABLER, not the ask. The payoff batch is the test.

PARKED BASE: `mining/parked/partitive-slot-enabler` = main + increment 83
(conjoined event conjuncts) + increment 84 (partitive item slot). No TEST look spent on
either — both are 0-SOLVED.

NEXT: batch 37 on `base=mining/parked/partitive-slot-enabler`, aimed at the partitive
family's ASK SHAPES now that the slot can hold them.
## Increment 85 (2026-07-13) — comparative/multiplicative relations whose MEASURE NOUN is elided ("3 more than Tom", "twice as much as Cecil", "one-third as long")

Class: comparative/multiplicative relations whose measure noun is elided —
"Ben has twice as many apples as Ann" resolves today, but "Ben has twice as
many as Ann" (measure noun dropped) does not: no Relation fact forms at all,
so every downstream consumer (single-entity fold, combined-total ask,
comparative |a-b|) — already built and already correct — never fires.
Reproduced on synthetics: the spelled-measure and elided-measure forms of
the same premise diverge from 90 (correct) to a flat decline. Same split for
additive ("3 more marbles than Tom" vs "3 more than Tom") and percent ("20%
more apples than Ann" vs "20% more than Ann") forms.

Mechanism (YAML-first, no lexicon in Python): six new ELISION variants of
the existing relation pattern rules in `packs/arithmetic/rules/core.yaml`,
matching the same comparative shapes with the measure-noun slot ABSENT and
emitting the Relation with `measure: null` — an explicit unresolved
sentinel, never a guess. `saturate.py`'s `_relations_synth` gains a step
that recovers the sentinel from the STANDARD entity's own unique in-play
quantity, following the same unique-pool-in-play discipline already used by
`synth/fraction-of-pronoun` and `synth/partition-of-collection`: exactly one
measure known for the standard resolves the relation; zero or two-or-more
candidate measures (ambiguous) decline it for that round rather than guess.
Scoped to a NAMED standard only ("than Tom", "as Cecil") — a relation whose
standard is ALSO elided (a bare "twice as long") is out of scope here and
left as a follow-on. The elision rules match a strictly SHORTER comparative
NP than their spelled-measure siblings; arbitration is by specificity so the
spelled-measure rule still wins whenever the measure noun is present. No new
consumer was needed — the fold, combined-total ask, and comparative consumer
already resolve these items once the Relation exists.

Files: `packs/arithmetic/rules/core.yaml`, `src/rulekit/kernel/saturate.py`,
`tests/test_mining_increment_85.py`.

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SHIP, 2 SOLVED (1cd6e3e8a4a7, 56ef08361887), 0
BROKE, 0 DECL→WRONG (62/3772 correct, up from 60, 0 wrong); dev-holdout diff
SHIP, 1 SOLVED (8b664d490ea4), 0 BROKE, 0 DECL→WRONG (26/3701 correct, up
from 25, 0 wrong); pytest 677 passed (+10 synthetic tests in
`tests/test_mining_increment_85.py` over the prior staging baseline of 667);
suite 52/52; lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). TEST look: pending — spent manually.

## Increment 86 (2026-07-13) — distributive 'each' container totals (infrastructure, 0 SOLVED by design)

Class: distributive 'each' totals — N per EACH of M things ("there are 20
rows and 6 chairs in each row", "he gave 4 stickers each to 3 friends"). This
is a PRECISION finding first (constitution rule 4), not a coverage one:
verified on the parked partitive-slot-enabler baseline, "There are 40 rows of
chairs. There are 20 chairs in each row. How many chairs are there?" commits
a CONFIDENT WRONG **20.0** (gold 800) — the unique-entity fold reads the
per-container content Quantity as if it were the group's whole total. No
dev-train item currently exercises this shape (dev-train has 0 wrongs), so it
was a LATENT wrong of exactly the §3a shape that killed increment 81 on TEST.

Mechanism (kernel-structural, no lexicon): (a) a new `saturate.py` plugin
`synth/distributive-container-total` — when a Quantity's holder noun is
itself COUNTED elsewhere (a Quantity whose MEASURE is that holder noun),
synthesizes `GroupTotal(contained) = container_count × per_container_content`,
chained transitively across saturation rounds while the chain stays UNIQUE at
every hop; declines (never commits) whenever the chain is ambiguous or the
container count is missing; (b) the same distributive-EVENT form ("gave 4
stickers EACH to 3 friends" → value = 4×3) in `learn.py`, reusing the
existing `_is_rate` quantifier lookahead via an OPT-IN flag only — per the
increment-11 invariant, the shared clause-boundary scan is never widened
globally; (c) `answer.py`'s unique-entity fold now declines whenever a
GroupTotal already exists for the measure it's about to fold a lone holder
over, converting the latent confident-wrong into a safe decline. No ask
shape reads GroupTotal directly yet — that is later, follow-on machinery —
so this increment SOLVES 0 items by design; it only removes a latent wrong
and makes the composed total available downstream. Unblocks: entity-less
container-total asks ("how many CHAIRS are there", "how many LITERS
altogether") over a distributive container chain, and the remainder/fraction
consumers that need the group total as their pool.

Files: `src/rulekit/kernel/saturate.py`, `src/rulekit/kernel/learn.py`,
`src/rulekit/kernel/answer.py`, `packs/arithmetic/rules/core.yaml`,
`tests/test_mining_increment_86.py`.

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff NEUTRAL, 0 SOLVED, 0 BROKE, 0 DECL→WRONG
(62/3772 correct, unchanged, 0 wrong); dev-holdout diff NEUTRAL, 0 SOLVED, 0
BROKE, 0 DECL→WRONG (26/3701 correct, unchanged, 0 wrong); pytest 684 passed
(+7 synthetic tests in `tests/test_mining_increment_86.py` over the prior
staging baseline of 677); suite 52/52; lint 0 errors / 1 known-good warning
(fraction-of-remnant / fraction-of-pool, unchanged). TEST look: pending —
spent manually.

## Increment 87 (2026-07-13) — elided-measure anchor quantities (a bare numeral stated for an entity whose measure noun is dropped: "who caught 2", "if Kristen has 12", "Ben has 9")

Class: elided-measure anchor quantities — an event/state verb's dobj (or a
copula's complement) resolves to a COUNT-valued unit with no measure noun
attached ("...as X who caught 2", "..., if Kristen has 12?"). This is the
premise-side sibling of increment 85 (elided-measure RELATIONS) and
increment 62 (elided-measure ASKS); the anchor side was left open by
increment 12 and named again as a blocker in a FAILED batch-38 equal-share
junior. Marked infrastructure: only 2 of 12 walked dev-train items resolve on
this fix alone, below the 3-of-8 shape bar, while >=4 more resolve once the
named follow-on (conjoined elided-measure event lists) lands on top.

Mechanism (kernel-structural, no lexicon): in `learn.py`, when an event/state
verb's dobj (or copula complement) resolves to a bare COUNT with no measure
noun, emit a `Quantity` with `measure: null` — an explicit unresolved
sentinel, exactly as increment 85's elision rules do for `Relation` — instead
of dropping the fact and leaving only a string-dobj `Predication`. The
sentinel is recovered in `saturate.py` on the same unique-in-play discipline
`_relations_synth` (increment 85), `synth/fraction-of-pronoun`, and
`synth/partition-of-collection` already use: the measure resolves from the
unique measure in play for that entity/verb context (a sibling relation's
measure, the unique prior Quantity measure, or a conjoined list's spelled
sibling); zero or two-or-more candidates is AMBIGUOUS and declines that round
— never a guess. `guards.py`/`model.py` key the sentinel fact the way
increment 28 keys `is_fraction` facts: `value`/`measure` are dropped from the
identity key while unresolved, so a null-measure Quantity does not count as
"read" until resolved. Unblocks: conjoined elided-measure event lists
("A collected 29, B collected 17, and C collected 8 shells" combined/total
asks where only the last conjunct spells the measure).

Files: `src/rulekit/kernel/learn.py`, `src/rulekit/kernel/saturate.py`,
`src/rulekit/kernel/guards.py`, `src/rulekit/kernel/model.py`,
`tests/test_mining_increment_87.py`.

Gates (integrated on staging, full re-proof against current staging
baseline): dev-train diff SHIP, +3 SOLVED (094cfd5b94b8, 5dfb02752ef5,
9aaef1e4ce47), 0 BROKE, 0 DECL→WRONG (65/3772 correct, up from 62, 0 wrong);
dev-holdout diff NEUTRAL, 0 SOLVED, 0 BROKE, 0 DECL→WRONG (26/3701 correct,
unchanged, 0 wrong); pytest 691 passed (+7 synthetic tests in
`tests/test_mining_increment_87.py` over the prior staging baseline of 684);
suite 52/52; lint 0 errors / 1 known-good warning (fraction-of-remnant /
fraction-of-pool, unchanged). TEST look: pending — spent manually.

## Batch 38 (2026-07-13) — the gate fix vindicated. TEST 91.7% (NEW FLOOR), dev-train 62.

Same base, same pool targeting as the three empty batches — the ONLY change was walking
8 items instead of 3. **All 5 candidates reached implementers** (previously: zero).

LANDED: 83, 84 (parked enablers, riding with their payoff), 85, 86.
- **85 — elided-measure relations** ("3 more than Tom", "twice as much as Cecil",
  "one-third as long"): the 354-item family the old gate killed at 2-of-3. **+2 dev-train,
  +1 dev-holdout.**
- 86 — distributive 'each' totals: 0 SOLVED, infrastructure. Removes a LATENT
  CONFIDENT-WRONG in the unique-entity fold for distributive 'each' container premises.

**TEST looks #83 (85) and #84 (86): 11/1 = 91.7% — TEST COVERAGE GAIN and a NEW FLOOR**
(was 10/1, 90.9%). Increment 85 won a TEST item outright.

DEFERRED at integrate-conflict (back to the worklist, need rebase onto the new main):
`discounted-purchase-prices` (conflicted in answer.py), `percent-change-relations`
(shares saturate.py's relation/partition synths with 85; was explicitly cut to land AFTER
it). Both branches retained. These are NOT failures — they are candidates that need
re-cutting against the current tip.

FAILED: `equal-share-division-asks` (goal-mode, SOLVED=0). Its junior traced why its own
3 samples don't resolve, to three DISTINCT pre-existing gaps — each a nameable follow-on
candidate: (a) "each one" — 'one' senses only as a value, never a noun, so it cannot fill
a recipient-noun slot; (b) elided-measure events ("Priya collected 29") fold as a
Predication with a string dobj, never a Quantity, so the dividend has no holder; (c) a
trailing "...if they divide X amongst themselves?" fuses the division premise INTO the
question sentence, and read-phase pattern rules only run over premise readings.

CALIBRATION (§9.4): elided-measure family — pool_frequency 354, solved_vs_main +2
(dev-train). Resolve rate ~0.6%. Sobering: a 354-item family yielded 2. The pool count is
a CEILING, not a forecast, and the gap between them is where the real work is.

## Batch 39 (2026-07-13) — increment 87. dev-train 62 -> 65. TEST look #85: 11/1 (91.7%) HELD.

LANDED: **87 — elided-measure anchor quantities** (a bare numeral stated for an entity
whose measure noun is dropped: "who caught 2", "if Kristen has 12", "Ben has 9"). +3.

THREE GOAL-MODE DEMOTIONS THAT EACH FOUND A REAL BUG. Do not treat these as failures —
their branches are retained and each finding is a named candidate:

1. **LIVE BUG ON MAIN (weekday names).** `time-period-qualified-events` found that
   weekday words (monday..sunday) are lexically sensed `time` — an inert sense nothing
   reads — and, being always capitalized, were ALWAYS misread as bare PROPER NAMES by
   senses.py's capitalization heuristic. That silently adds a spurious second "name" to
   `_discourse_candidates` (document.py) whenever a premise carries a weekday adjunct,
   **breaking the FOLLOWING sentence's pronoun resolution.** Confirmed on unmodified main
   via manual probes. Its fix (retag weekday -> noun, admit to the EXISTING `timeperiod`
   category, exempt timeperiod words from the capitalization override) is
   category-gated and constitution-clean. Branch: `mining/cand-time-period-qualified-events`.
   **RE-CUT THIS — it is a precision bug on main, not a coverage candidate.**

2. **Coordinated-subject binding bug.** `container-pool-depletion` traced a general
   multi-clause bug in `obligations.py::_candidates`: a counted-noun object's
   conjoined-sibling check short-circuits with an early return BEFORE the
   uncounted-noun/adjacency-arbitration filters run — so "X did A and Y did B" loses Y's
   subject whenever the first clause's object noun sits right before "and Y".

3. **Existential-premise entity mis-binding.** Same candidate: "N pieces OF CANDY in a
   bowl" binds the existential rule's entity to the SUBSTANCE noun instead of the
   CONTAINER — a precedence gap between the 'of' partitive and the trailing 'in PLACE'
   phrase.

`partitive-combined-asks` shipped NEUTRAL honestly: no dev item hits its exact shape
today because the pool items carrying that ask have a SECOND blocker (elided standards,
equal-share division, dozen conversions, reverse solves). Its 12 synthetic tests stand.

## Increment 88 (2026-07-13) — WEEKDAY PRECISION FIX. A live bug on main, killed.

Not a coverage increment. Constitution rule 4: precision before coverage.

THE BUG (live on main until now): weekday words carried an inert `time` sense nothing
reads, and — always capitalized — senses.py's capitalization heuristic ALWAYS overrode them
to `name`. A weekday adjunct injected a spurious proper name into `_discourse_candidates`,
which could steal a following pronoun's binding and silently drop the real holder's
quantity.

PROVEN, not asserted. Same shape, two adjuncts:
  "On Monday,      Sam had 12 apples. He found 5 apples."  -> main: quantity LOST
  "In the morning, Sam had 12 apples. He found 5 apples."  -> main: quantity attached
The divergence IS the bug. With the fix they behave identically.

THE FIX IS STRUCTURAL: weekdays retagged `time` -> `noun`, admitted to the PRE-EXISTING
`timeperiod` category (with morning/week/year), and senses.py exempts timeperiod-category
words from the capitalization override. The kernel names a CATEGORY, never a word.
**NO NEW VOCABULARY** — all seven weekdays were already in the lexicon; only their SENSE is
corrected. Both prior TEST vocab kills were about admitting UNKNOWN words; this is a
different and far safer operation. Quarantine checked.

GATE: both diffs NEUTRAL (0 BROKE, 0 DECL->WRONG), suite 52/52, pytest 691 -> 708 (+17),
lint clean. 0 SOLVED — no DEV item happens to hit the trap, which is what "latent" means.
**TEST look #86: 11/1 (91.7%) — HELD.** Landed.

WORTH REMEMBERING: this came from a candidate the goal-mode gate DEMOTED for solving
nothing. "0 SOLVED" is not "worthless" — read the failed-candidate reports.

## Increment 89 (2026-07-13) — passive-voice entity-less event totality asks

CLASS: "how many X were eaten/sold/given/bought in total?" — the passive-voice sibling
of the existing active-voice entity-less totality asks (e.g. "how many pies did they
eat in total?"). Every ask id in `packs/arithmetic/rules/core.yaml` was ACTIVE-voice
only; not one matched a passive question, despite identical premises already building
the right facts.

MECHANISM: YAML-ONLY. Added `ask/how-many-passive-combined` to
`packs/arithmetic/rules/core.yaml` — a copula ({cat: state}: is/was/are/were) directly
followed by a bare past-participle verb form (no subject, no auxiliary, no literal
"there"), plus the same required trailing totality marker (optionally preceded by a
preposition: "in total", "altogether", "combined"). Routes to the SAME unchanged
`combined` consumer every other entity-less totality ask already uses. No new
consumer, no new fact kind, no new vocabulary — every past participle exercised
already carries `sense=verb` with its own `verb.lemma` feature in the shipped packs.
Zero ordering risk: the passive frame requires a copula + past participle, which no
active ask's frame admits, so it can never tie with an existing ask id (confirmed by
lint's overlap witness).

PROVEN on a controlled pair on unmodified main: "Sierra ate 12 pies. Bill ate 6 pies.
Adam ate 9 pies. How many pies did they eat in total?" -> commits 27.0 (correct).
Same premises, "...how many pies were eaten in total?" -> declined (no ask shape
recognized it). Confirmed on the real item 409628e79bf6 (gold 27): rewriting only its
ask to the active voice already committed correctly on main; the new passive ask id
now makes the ORIGINAL passive item commit 27.0 directly.

GATE: dev-train diff SOLVED 1 (409628e79bf6) / BROKE 0 / DECL->WRONG 0 — VERDICT SHIP.
dev-holdout diff NEUTRAL (0/0/0). Suite 52/52. Lint 0 errors (1 pre-existing warning:
fraction-of-remnant/fraction-of-pool overlap, known-good). pytest 708 -> 715 (+7).
**TEST look: pending — spent manually.**

## Increment 90 (2026-07-13) — appositive/relative-clause-introduced relation standards
(PRECISION FIX)

CLASS: relations whose STANDARD is introduced by an appositive or relative clause
("than his friend Sam", "than her sister Gigi", "than Sam, who runs 12 miles"). Not a
coverage candidate — a precision fix (increment 88's precedent): the relation pattern
rules in `packs/arithmetic/rules/core.yaml` bound their `standard` slot to the first
noun after "than"/"as", so a kinship/role common noun immediately followed by an
appositive NAME ("his friend Sam") bound the standard to the ROLE NOUN instead of the
NAME.

PROVEN on unmodified main: "Tom has 2 more apples than Ann. Ann has 5 apples." ->
Tom = 7 (correct). Insert a kinship appositive: "Tom has 2 more apples than his
sister, Ann." -> DECLINES. Worse, on an event verb it committed a confident wrong:
"Harvey runs 8 miles more than his friend Sam. Sam runs 12 miles. How many miles does
Harvey run?" -> committed 8.0 (gold 20). Second confident wrong: "Mr. Martinez is two
feet taller than his daughter, Chiquita. Chiquita is 5 feet tall. How many feet do
they have in total?" -> committed 7.0 (gold 12).

MECHANISM: pattern-only, no kernel edit. Added a `standard` slot variant to the
relation rules in `packs/arithmetic/rules/core.yaml` that consumes an optional
[poss/det + common-noun + optional comma] SKIPPABLE appositive prefix before the
name, so the standard binds to the NAME rather than the role noun. Decline-safety:
when the appositive slot is absent, the rules match byte-identically to today (purely
additive, strictly-longer match). Bare role-noun standards with no following name
("than his sister") are unchanged — out of scope, named at ship time. No word list
enters Python or the gate condition: the match is structural (possessive/determiner +
common noun + capitalized name), never an enumeration of "friend"/"sister"/"daughter".

GATE: dev-train diff NEUTRAL (0 SOLVED / 0 BROKE / 0 DECL->WRONG, 66 correct
unchanged). dev-holdout diff SOLVED 2 (107662a7cb1b, 11d78d0b4f70) / BROKE 0 /
DECL->WRONG 0 — VERDICT SHIP (26 -> 28 correct). Suite 52/52. Lint 0 errors (1
pre-existing warning: fraction-of-remnant/fraction-of-pool overlap, known-good).
pytest 715 -> 722 (+7).
**TEST look: pending — spent manually.**

## Increment 91 (2026-07-13) — generic unit-price premises (ENABLER)

CLASS: per-unit price premises whose subject frame the price_verb branch did not yet
read: indefinite-singular generics ("a book costs $5"), pronoun subjects ("they are
$20 each"), and floating-'each' relative clauses ("5 toys that each cost $3"). All
three emit the SAME `Price` fact increments 15/29/36 already emit and that the live
purchase-total/cost-of-quantity consumers already read by item lemma.

PROVEN on unmodified main as a minimal pair: "In a bookstore, EACH book costs $5.
Sheryll bought 10 books. How much did Sheryll pay in all?" commits 50.0 — change one
word to the indefinite generic, "In a bookstore, A book costs $5. ...", and it
declines `no 'pay' events known for 'sheryll'/'currency'`. Same minimal-pair shape
for the pronoun form and the floating-'each' relative clause.

MECHANISM: pattern-only, no kernel edit. Three additive pattern-rule variants of the
existing price rules in `packs/arithmetic/rules/core.yaml`: (1) an indefinite-singular
generic subject (det in {a, an, one} + count noun + price_verb/copula + currency
value); (2) a pronoun subject in the copular price frame ("they/it are/is $P each"),
resolved via the pipeline's existing discourse candidates, with an optional
hedging-adverb slot; (3) a relative clause with a floating quantifier ("N ITEMs that
each cost $P"). Arbitration by specificity — each variant matches a strictly longer
frame than any rule it could tie with, so no existing price rule loses. Filed as an
ENABLER, not coverage: of the 24 already-recognized-ask items blocked only on the
price frame, fixing the frame alone resolves 1 (the rest carry a second blocker —
discount, obligation-framed pay ask, or conjoined purchase — named as follow-on
classes, e.g. `discounted-purchase-totals`).

GATE: dev-train diff SOLVED 1 (b1cd78e295ec) / BROKE 0 / DECL->WRONG 0 — VERDICT
SHIP (66 -> 67 correct). dev-holdout diff NEUTRAL (0 SOLVED / 0 BROKE / 0
DECL->WRONG, 28 correct unchanged). Suite 52/52. Lint 0 errors (1 pre-existing
warning: fraction-of-remnant/fraction-of-pool overlap, known-good). pytest 722 -> 737
(+15).
**TEST look: pending — spent manually.**

## Increment 92 (2026-07-13) — discounted purchase totals (re-cut of the batch-38
`discounted-purchase-prices` deferral)

CLASS: a percent or flat discount applied to a priced purchase before the pay/spend
total ("N% off", "a N% discount", "on sale for N% off", "a $N discount", "$N off").
Re-cut against the current tip (which now includes increment 91's generic
unit-price-premise machinery) after the batch-38 attempt was DEFERRED at
integrate-conflict in `answer.py`.

PROVEN on unmodified main: "Jorge bought 24 tickets for $7 each. How much did Jorge
spend on tickets?" commits 168.0 via the live `Σ price × qty over 'jorge''s
purchases` consumer; the real item adds "he is given a discount of 50%" and gold is
84.0. Same shape for "Tim buys a cabinet for $1200" (1200.0 vs gold 1020.0 at 15%
off) and "Miley bought two cellphones... Each cellphone costs $800" (1520.0 already
correct pre-discount in one variant, 1520.0 post a 5% TOTAL discount in another —
the discount scope is on the total, not per unit).

MECHANISM: YAML-first plus one consumer edit. (1) `packs/arithmetic/rules/core.yaml`:
new pattern rules emitting a `Discount` fact — percent form ("N% off", "a N%
discount", "a discount of N%") and flat form ("a $N discount", "$N off", "a discount
of $N"), each carrying a `scope` of total|per_unit read from the surface ("a discount
of $N EACH" is per-unit; a bare discount is total). (2) `src/rulekit/kernel/model.py`:
the `Discount` fact kind. (3) `src/rulekit/kernel/guards.py`: USE-gated for value
accounting exactly like Rate/Price/Goal/GroupTotal — its number counts as read only
when the arithmetic log actually consumed it. (4) `src/rulekit/kernel/answer.py`: the
existing purchase-total consumer (`Σ price × qty over WHO's purchases`) applies at
most ONE in-play Discount to its total before committing; two or more Discounts, or a
Discount whose scope cannot be determined, DECLINE rather than guess. No new ask shape
and no new vocabulary — `discount`/`sale`/`off` were already in the lexicon.

Cherry-picked from `mining/cand-discounted-purchase-totals` onto the current staging
tip; the pick auto-merged cleanly in `answer.py` (no manual conflict resolution).

GATE (integrated, vs current staging baselines): dev-train diff SOLVED 1
(d7a0e512633b) / BROKE 0 / DECL->WRONG 0 — VERDICT SHIP (67 -> 68 correct).
dev-holdout diff NEUTRAL (0 SOLVED / 0 BROKE / 0 DECL->WRONG, 28 correct unchanged).
Suite 52/52. Lint 0 errors (1 pre-existing warning: fraction-of-remnant/
fraction-of-pool overlap, known-good). pytest 737 -> 748 (+11).
**TEST look: pending — spent manually.**

## Batch 40 (2026-07-13) — increments 89, 90. dev-train 66, holdout 28.

LANDED (looks #87, #88 — both 11/1, 91.7%, HELD):
- **89 — passive-voice entity-less event totality asks** ("how many X were eaten / sold /
  given / bought in total?"). +1 dev-train.
- **90 — appositive / relative-clause relation STANDARDS** ("than his friend Sam", "than
  her sister Gigi", "than Sam, who runs 12 miles"). 0 dev-train, **+2 dev-holdout** (26 ->
  28).

REVIEW KILL: `equal-share-division-asks` failed constitution review on **rule 1** —
`answer.py` hardcoded `recipient_noun in (None, "person")`, encoding "the word *person* is
the generic recipient placeholder" in Python. The reviewer verified `"person"` appears
NOWHERE under `src/` on main, and demolished the junior's pre-defence (that it is "a
pack-owned constant like world/currency"): `world` and `currency` are kernel SENTINELS
never matched against text-derived lemmas, whereas `person` IS. And a `person` category
already exists in the packs — the diff itself promotes it. Fix is one gate away. RE-CUT.

FAILED (goal-mode, 0 SOLVED) but valuable: `counted-subject-each-events` redesigned its
mechanism to emit two ordinary Quantity facts instead of a GroupTotal, so increment 86's
EXISTING distributive-container synth composes them for free — and got transitive chaining
gratis. It also caught a real KeyError (13 dev-train items errored) before shipping, and
documented a hard structural limit: **GroupTotal.key() is (measure,) only**, so two
same-measure GroupTotals quarantine each other at FactStore.admit and multi-group summing
is impossible without a distinguishing field on GroupTotal + a FactStore.admit re-key.
Named as a clean follow-on.

## Increment 93 (2026-07-13) — same-holder cross-measure relations: PP-interrupted
measure NPs, conjoined-clause premises, inverse resolution, superordinate totality asks

CLASS: same-holder cross-measure comparative relations ("twice as many SHOES as
BELTS", "9 more KNIVES than FORKS") reached through surfaces the existing same-holder
subtype-anchor branch (increment 78) does not yet see, plus the inverse resolution
direction and superordinate totality asks over the resolved subtypes.

PROVEN on unmodified main: "Clinton has twice as many shoes as belts. He has 2 more
belts than hats. He has 5 hats. How many shoes does Clinton have?" commits 14.0 (the
gold of the real item) but the real item — which interrupts the measure NP with a
locative PP and states the anchor quantity in a conjoined clause — declines. Likewise
"Mr. Rainwater has 9 cows. He has 4 times as many goats as cows." commits 36.0
forward, but the real item asks for the STANDARD measure (cows) from a known subject
measure (goats), which the existing branch cannot resolve backwards.

MECHANISM: YAML-first, one kernel widening. (1) `packs/arithmetic/rules/core.yaml`:
widened the existing same-holder comparative relation rules' measure-NP slot to skip
an optional trailing prepositional phrase before "as"/"than" (a skippable
`[prep + det? + noun]` prefix, structurally matched — mirrors increment 90's
appositive-prefix precedent, purely additive so the no-PP case matches
byte-identically to today). (2) same file: a new rule,
`arithmetic/anchored-relation-conjoined-anchor`, admits the conjoined-clause premise
form ("... N more X than Y and currently has M Y"), matching the state-verb
conjunction gap (increment 35) reaching a relation-bearing clause. (3)
`src/rulekit/kernel/saturate.py`'s `_relations_synth` same-holder subtype branch
gains the INVERSE direction (solve `standard = (subject - offset) / factor` from a
known subject measure), guarded by `is_subtype_standard` and the same
unique-in-play discipline — two candidate quantities, or a zero factor, decline for
that round rather than guess. (4) additional `superordinate: true` category entries
with exhaustive subtype member lists in `packs/core-english/categories/core.yaml` /
`packs/difg-mined/categories/semantic.yaml`, so increment 78's existing
`_superordinate_total` consumer answers totality asks over the newly-resolved
subtypes. No word list enters Python; the PP/conjunction matches are structural.

GATE: dev-train diff SOLVED 2 (7394eac428cb, 8ea333bd91f4) / BROKE 0 / DECL->WRONG
0 — VERDICT SHIP (68 -> 70 correct). dev-holdout diff NEUTRAL (0 SOLVED / 0 BROKE /
0 DECL->WRONG, 28 correct unchanged). Suite 52/52. Lint 0 errors (1 pre-existing
warning: fraction-of-remnant/fraction-of-pool overlap, known-good). pytest 748 -> 757
(+9).
**TEST look: pending — spent manually.**

## Batch 41 (2026-07-13) — three landed. dev-train 66 -> 70. Best batch of the goal run.

LANDED (looks #89, #90, #91 — all 11/1, 91.7%, HELD):
- **91 — generic unit-price premises**: per-unit prices whose subject frame was never read
  — indefinite-singular generics ("a book costs $5"), pronoun subjects ("they are $20
  each"), floating-'each' relative clauses ("5 toys that each cost $3"). +1.
- **92 — discounted purchase totals**: a percent or flat discount applied to a priced
  purchase before the pay/spend total. +1.
- **93 — same-holder cross-measure relations**: PP-interrupted measure NPs, conjoined-clause
  premises, inverse (standard-unknown) resolution, superordinate totality asks over them. +2.

REVIEW KILL — **rule 3, the most serious violation yet**: `temporal-offset-age-relations`
put a **VERBATIM GSM8K TRAIN ITEM** into `tests/` ("9 years from now, John will be 3 times
as old as he was 11 years ago. How old is he now?"). The reviewer verified it BYTE-FOR-BYTE
against `gsm8k_train.parquet` — item ae407466fc20, quoted in the brief's own structural
sample and copied straight through instead of synthesized. It caught a second, subtler one
in the same file: a truncated two-sentence premise from another train item with only the
ask swapped. Branch retained; fix is trivial (synthesize equivalents) but it goes back to
the worklist, NOT into a review-pressure edit.

**AUDITED main directly afterwards: no GSM8K train strings in tests/. The line held.**

SHAPE GATE: `rate-stack-robustness` dropped at 2 of 10 walked — the minItems=8 fix working
as intended (a real sample, an honest denominator).

## Increment 94 (2026-07-13) — anaphoric-multiplier relation standards

CLASS: demonstrative multiplier NPs used as a relation STANDARD — "twice that many",
"three times that amount", "half that much", "5 times that number", "twice this many",
"3 times that price" — the anaphoric sibling of increment 85's ELIDED-standard family
(85 handles a dropped measure noun; this handles a demonstrative pointing back at a
quantity or price already stated earlier in the document).

PROVEN on unmodified main: "John orders 1000 beef for $8 each. He also orders TWICE
THAT MUCH chicken at $3 each." declines with "stated multiplier twice (sentence 1)
reached no fact and no arithmetic"; substituting the explicit number into the same
text commits 14000.0 — the gold of item 84e2001d4069.

MECHANISM: INFRASTRUCTURE (enabler). `packs/arithmetic/rules/core.yaml` gains rules
admitting a demonstrative NP as a relation standard: [multiplier] + optional "times" +
{lit: that|this} + a head noun in the new `quantity_anaphor` category (much / many /
amount / number / price / cost) — all grammatical skeleton, no new vocabulary. The
rule emits the existing Relation fact with the standard left as the same null-standard
sentinel increments 85/87 use. `src/rulekit/kernel/saturate.py`'s `_relations_synth`
resolves it on the SAME unique-in-play discipline those two already use: the standard
binds to the unique prior Quantity of the same measure in play (or, for "that price",
the unique prior Price); zero or two-or-more candidates is ambiguous and declines —
never a guess. New category `quantity_anaphor` (parent noun) added to
`packs/core-english/categories/core.yaml`; `packs/difg-mined/categories/semantic.yaml`
touched to extend membership consistently with the root-sense invariant. Filed
infrastructure: only 1 of 12 walked items resolves on this fix alone — the rest are
blocked downstream on totality-ask surfaces this enabler does not build (unblocks:
single-holder totality/combining asks over anaphoric-multiplier event chains — a
present-perfect totality ask, a FRONTED "In total, how many X..." marker, and combined
value-accounting asks — the payoff class that cashes this in).

GATE: dev-train diff SOLVED 1 (a18c0df9ca3e) / BROKE 0 / DECL->WRONG 0 — VERDICT SHIP
(70 -> 71 correct). dev-holdout diff NEUTRAL (0 SOLVED / 0 BROKE / 0 DECL->WRONG, 28
correct unchanged). Suite 52/52. Lint 0 errors (1 pre-existing warning: fraction-of-
remnant/fraction-of-pool overlap, known-good). pytest 757 -> 765 (+8).
**TEST look: pending — spent manually.**
