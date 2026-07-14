# Composition: derived facts are terminal

> ## ⛔ VERDICT: ABANDONED (2026-07-14, same day)
>
> Phase 0 ran. **The composition ceiling is ~13 items, not 271.** The 271 was a
> measurement artifact — see §0 below, which was written after the rest of this note and
> overrides it. The design in §2 is sound and the hazard in §3 is real; neither is worth
> building for 13 items. **The engine's ceiling is READING, not composition.**
>
> This note is kept in full, with its wrong conclusion intact, because the *way* it was
> wrong is the most useful thing in it.

Research pass, 2026-07-14. Measured on dev-train at 103 correct / 0 wrong.
Nothing in this note is built. Two things in it are *measured*, and they disagree
with the hypothesis that prompted the investigation.

---

## The thesis

**rulekit can derive a number. It cannot use one.**

`saturate()` is a fixpoint over facts and it genuinely composes — `synth/distributive-
container-total` already turns *"each hand has 14 bananas"* + *"there are 9 hands"* into
`GroupTotal(banana, 126)`, correctly, today. But a `GroupTotal` is a **terminal fact**:

- it is not a `Quantity`, so `_entity_total` cannot fold it;
- holder enumeration (`_combined_holder_totals`, the `unique-entity` consumer) cannot see it;
- no synth reads it, so nothing can subtract from it, price it, or sum it with another.

A derivation can produce a number. **That number cannot become the input to the next
derivation.** Every multi-step problem dies at exactly that boundary.

```
"There are 9 hands. Each hand has 14 bananas. Sam ate 6 bananas. How many are left?"

  store:  Quantity(world, hand, 9)      <- arithmetic/existential-premise-bare
          Quantity(hand, banana, 14)    <- fold          (a PER-HAND RATE)
          Quantity(sam, banana, 6)      <- fold          (an EVENT)
          GroupTotal(banana, 126)       <- synth/distributive-container-total  ✅ CORRECT

  answer: DECLINE — "2 entities hold 'banana' — an entity-less ask needs exactly one"
```

The engine computed 126. The consumer enumerated `Quantity` holders (`hand`, `sam`), found
two, and declined — **without ever looking at the 126 it had just derived.** 120 is one
subtraction away and unreachable.

---

## §0 — PHASE 0 RAN. THE PROJECT IS DEAD. (written last; overrides everything below)

Phase 0 asked: of the 271 items whose gold an unconstrained ≤3-op search could reach from
the extracted facts, how many are reachable by a **TYPED** composition — a rate × a count, a
total ± an event, a total × a price — i.e. something rulekit could principledly do?

```
TYPED-REACHABLE:  13        vs   the ≤3-op oracle's   271
  12  "sum of same-measure holdings"  <- not even composition; the `combined`
                                         consumer already does this, and those items
                                         decline for unrelated reasons
   1  the GroupTotal simply IS the gold
```

13 < the ~20 stop-threshold recorded in §5. **Abandon.** But the interesting part is WHY the
two numbers disagree by 20×, and it is a methodological failure worth more than the project.

### The null control: the oracle was measuring nothing

An unconstrained `+ - × ÷` search to depth 3 over ~8 numbers explores a combinatorial space
large enough to hit almost any target by coincidence. So: run it against **another item's**
gold and see how often it "succeeds".

| ≤3-op oracle, 1,143 addressable declining items with ≥1 numeric fact | | |
|---|---|---|
| reaches the **TRUE** gold | 439 | 38% |
| reaches a **WRONG** (randomly reassigned) gold | 373 | **33%** ← the null |
| **signal above chance** | **+66** | **+6%** |

**The oracle reaches a wrong answer almost as often as the right one.** "19% of items have
facts that suffice" was never a fact about the corpus; it was a fact about the size of the
search space. The true signal is ~66 items at the absolute most, and the principled probe
finds 13.

### The lesson, which is general and was nearly expensive

> **A reachability bound without a null control is not evidence.**
>
> I ran the oracle, believed it, and wrote a roadmap around it — for the most dangerous
> mechanism ever proposed in this project, the one whose failure mode is a silent
> MULTIPLICATION rather than a decline. It survived only because the typed probe disagreed
> by 20× and I asked why instead of averaging them.
>
> Any "the information is already there, we just can't use it" claim must be tested against
> a shuffled target. If the method finds the answer when there is no answer to find, it has
> told you nothing.

### What is actually true, then

- **The composition gap is real but small** (~13-66 items). The architecture diagnosis in §2
  stands — `GroupTotal` genuinely is a terminal fact and the engine genuinely does derive
  numbers it cannot use. It is simply not where the corpus lives.
- **The engine's ceiling is READING.** 81% of the addressable pool never extracts the numbers
  at all ("*5 less than half as many coconut trees*" → the engine got `[60]`). That is the
  real project, it is much larger, and no amount of composition machinery touches it.
- **dev-train 150 is not reachable** by composition, by mining, or by consumer fixes. It
  requires closing the reading gap.

---

## §1 — The measurement that reframes this (do not skip)

*(Written before §0. Its 271 figure is the artifact §0 debunks — kept for the record.)*

The investigation started from a different hypothesis: that 481 addressable items carry an
`each`/`every`/`per` premise the engine fails to read as a rate, and that building per-unit
rate recognition was the big win. **Both halves of that were wrong.** The mechanism exists
(above), and the number was a ceiling, not a yield (`docs/negative-results.md`).

So the real question was measured directly: **for every addressable declining item, can the
gold be reached from the numeric facts the engine ALREADY extracted, by combining them with
`+ - × ÷` in ≤ 3 operations?** If yes, the facts suffice and only the composition is
missing. If no, the engine failed to *read*, and composition cannot help it.

| dev-train, addressable (fully-read) declining items | 1,435 | |
|---|---|---|
| no numeric facts extracted at all | 292 | 20% — **reading gap** |
| gold NOT reachable from the extracted facts | 872 | 61% — **reading gap** |
| gold reachable in ≤ 1 op | 86 | 6% |
| gold reachable in ≤ 3 ops | 185 | 13% |
| **COMPOSITION CEILING (the facts suffice)** | **271** | **19%** |

**81% of the addressable pool is a READING gap, not a composition gap.**

```
"Randy has 60 mango trees. He also has 5 LESS THAN HALF AS MANY coconut trees
 as mango trees. How many trees does he have?"        gold 85

  numeric facts the engine extracted:  [60.0]
```

The affine relation never folded. No amount of composition machinery reaches 85 from `[60]`.

### What this licenses, and what it does not

- **Composition is worth at most 271 items** — and that is an *oracle* bound (an ≤3-op
  search over the fact values found the gold; it does not mean any principled mechanism
  will). Treat it as a ceiling, never a forecast.
- 271 is still **2.6× everything this campaign has built** (103), and clears the 150 target
  if even a fifth of it converts.
- The reading gap (1,164 items) is larger and harder, and is **the real ceiling on rulekit**.
  It is not this project.

---

## §2 — The architecture gap, precisely

The store has two classes of numeric fact and only one of them composes:

| | composable? | who folds it |
|---|---|---|
| `Quantity` | **yes** | `_entity_total`, `_pool_before`, `_verb_total`, every synth |
| `GroupTotal` | **no** | one decline-guard reads it, to *refuse* |
| rate-span results | **no** | returned straight to the caller as an `Answer` |
| `Price` / `Rate` | partly | read by their own consumers; never re-enter the store |

A derived aggregate is computed **inside a consumer or a synth and then either returned or
parked**. It never re-enters the fact store as something the next step can pick up.

**The fix shape** (not built; this is the design, not a promise):

> A derived total re-enters the store **as a `Quantity`**, tagged with the provenance of the
> derivation that produced it, and the facts it CONSUMED are marked so they cannot be
> counted again.

The second clause is the whole difficulty. If `GroupTotal(banana, 126)` re-enters as
`Quantity(world, banana, 126)`, then the pool for `banana` becomes `126 + 14` — because
`Quantity(hand, banana, 14)` is still sitting there, and it is a **rate**, not a holding.
**That is a silent double-count, and it commits.**

The seed of the answer already exists: `ArithmeticLog.consumed_rate_keys` (landed
incidentally in a since-reverted increment) records exactly which `(entity, measure)` facts a
bridging synth consumed AS A RATE, populated at the synth's own emission site and never
guessed from the sentence shape. That is the `USE`-vs-`EXISTENCE` distinction the
value-accounting guard already enforces for `Rate`/`Price`/`GroupTotal` — applied to folding
instead of to accounting.

---

## §3 — The precision hazard, stated plainly

**This is the most dangerous change proposed in the project's history, and it must be treated
that way.**

Every other increment has had the property that its failure mode is a **decline**. This one's
failure mode is a **multiplication**. Confusing a per-unit rate with a total does not produce
"no answer"; it produces `9 × 14 = 126` where the truth was `14`, committed with full
confidence.

The relevant history, all of it earned in this campaign:

- **Increment 81** — spotless DEV gate (7,473 items), confident-wrong at TEST. Reverted.
- **128-retry** — `0 BROKE` *by construction*. The proof covered the wrong failure mode; it
  said nothing about `DECLINE → WRONG`. Confident-wrong at TEST. Reverted.
- **129** — gained a correct answer **and** a wrong one. Coverage up, precision down. Reverted.
- **The GroupTotal consumer fix** (built and measured during this pass) — correct, sound,
  **0 SOLVED**. Not landed, because 0 SOLVED means *it does not fire on text we can check*,
  and it makes a consumer COMMIT where it used to DECLINE.

**The rule that falls out of all four:** a mechanism whose safety argument names only one
failure mode has an unexamined one, and that is the one that kills it. For composition the
unexamined mode is **double-counting a consumed input**, and it is silent.

### Non-negotiable constraints on any composition increment

1. **A derived `Quantity` must carry its provenance and its consumed inputs.** Re-entry
   without consumption-marking is a double-count generator. No exceptions.
2. **Fire only on an explicit marker.** A distributive fold requires `each`/`every`/`per`/
   `apiece` on the surface. Never infer "this looks like a rate" from shape.
3. **Decline on any ambiguity** — two candidate rates, two group totals, an unresolvable
   count. Coverage is recoverable; a wrong is a revert.
4. **Every increment must be BOUGHT** (`negative-results.md`, "the infrastructure trap").
   The enabler lands folded into the increment that cashes it in, so its yield and its risk
   are measured in the same gate. A 0-SOLVED composition increment does not land, however
   good the argument.

---

## §4 — Roadmap

Phases are ordered so that **the first thing built is the thing that tells us whether to
build the rest.** No phase depends on a prediction.

### Phase 0 — the honest yield probe (MEASUREMENT, not a build)

The 271 ceiling is an oracle bound. Before writing kernel code, find out how much of it a
*principled* mechanism can reach: for each of the 271, check whether the gold is reachable by
a **typed** composition (a rate × a count; a total − an event; a total × a price) rather than
by an unconstrained arithmetic search over the values.

**This is the single highest-value hour in the plan.** If the typed-reachable count is ~50,
the project clears 150 and is worth the risk. If it is ~5, the 271 is an artifact of the
search and the whole project should be abandoned — cheaply, before any kernel change.

*Everything below is contingent on Phase 0.*

### Phase 1 — derived totals re-enter the store (the seam)

`GroupTotal` → also emitted as `Quantity(entity=<the group>, measure, value, source="synth/
composed")`, with the consumed rate keys recorded. Consumers change **not at all**; they
simply now find a foldable fact where before they found a terminal one.

Gated on: **no double-count**. The proof obligation is that for every item where a composed
`Quantity` enters, the fold excludes the inputs it consumed. Expect this to be where the
increment lives or dies.

*Cashes in with:* the `unique-entity`/`combined` consumers, which today decline in front of
a `GroupTotal` they cannot read (the patch is already written and recorded in
`negative-results.md` — it lands **here**, folded into this increment, not before).

### Phase 2 — the derived total as an operand

Once a composed total is an ordinary `Quantity`, the existing event fold (`_entity_total`:
states anchor, events add/subtract by verb polarity) composes it with subsequent events **for
free**. *"…Sam ate 6 bananas. How many are left?"* → `126 − 6`. No new machinery; this is the
payoff of Phase 1 being done as a `Quantity` rather than as a special case.

### Phase 3 — chained derivations

A composed total feeding a *second* derivation (total × price; total ÷ share). Needs the
fixpoint to iterate over composed facts, which `saturate()` already does — but the
consumption bookkeeping must survive a chain, and that is a genuinely new invariant. **Do not
start this until Phases 1-2 have held at TEST.**

### Explicitly NOT in scope

- **The reading gap** (1,164 items, 81% of the pool). Bigger, harder, and the real ceiling on
  the engine. It is the *next* project, not this one.
- Any inference of a rate from sentence shape without an explicit distributive marker.
- Any relaxation of the mixed-time refusals (measured: `0 SOLVED`, `docs/deixis.md`).

---

## §5 — What would make me stop

Recorded now, while it is cheap to be honest:

- **Phase 0 returns a typed-reachable count under ~20.** The 271 was a search artifact; the
  facts "suffice" only in the sense that an oracle could combine them. Abandon.
- **Phase 1 cannot be made double-count-safe without a word list or a per-problem branch.**
  That is constitution rule 1 or 2, and the answer is no, regardless of yield.
- **Any composition increment drops TEST precision.** It reverts, and two reverts in this
  family means the mechanism is unsafe at this granularity — which is a real finding and
  should be recorded as one, not worked around.
