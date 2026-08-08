# Deixis: a design note

*Research pass, 2026-07-14. Analysis + one experiment (run, gated, reverted).*
*All measurements taken at `744973f` (dev-train 93/0, 100% precision). The
§4 gate result is reproducible from that base; increments 112–113 landed
concurrently and moved dev-train to 95, which does not affect the argument.*

**Deixis** is the linguistic phenomenon of expressions whose referent is fixed only
relative to a *reference point* — Bühler's **origo**. "She", "the rest", "that many",
"now", "there", "back" all denote nothing until you know who is speaking, when, where,
and what was just said.

This note argues that deixis is the organising abstraction rulekit is missing, and
that its absence is not merely a coverage limitation — it is an active generator of
bugs and a blocker on otherwise-safe fixes.

---

## The thesis

> **rulekit has re-implemented deictic resolution ~15 times, under other names, and
> always in its degenerate form — because it has no origo.**
>
> With no reference point, candidate referents cannot be *ranked*. So the only safe
> acceptance rule is *"bind iff exactly one candidate exists in the whole document,
> else decline."* That rule is hand-written at 15 sites. It was never *chosen* as a
> precision policy; it is the **only** policy available when there is no reference
> point to measure distance from.

---

## 1. What the engine has today

### 1.1 Fifteen re-inventions of "unique candidate, or decline"

Each site builds its own candidate set, then applies an identical acceptance test.

| Site | Candidate set |
|---|---|
| `document.py:83` `_bind_discourse` | prior `name`-sensed units, doc-wide |
| `document.py:122` `_bind_measure_anaphor` | prior plural noun lemmas ("12 yellow **ones**") |
| `saturate.py:336` anaphoric-quantity sentinel | prior `Quantity` facts ("twice **that many**") |
| `saturate.py:377` anaphoric-price sentinel | prior `Price` facts ("twice **that much**") |
| `saturate.py:402` elided standard | prior same-measure holders ≠ subject |
| `saturate.py:461` elided measure | measures known for the standard |
| `saturate.py:792` `_anchor_quantity_synth` | measures in play for the entity |
| `saturate.py:883` `_fraction_synth` | the unique pool in play ("half of **them**") |
| `saturate.py:939` `_rest_synth` | exactly one measure doc-wide ("**the rest**") |
| `saturate.py:1001` `_partition_synth` | measures from strictly-prior sentences |
| `saturate.py:1148` `_partition_membership_synth` | the unique holder of the collection |
| `answer.py:44` `_resolve_measure_against` | in-store measures of an `interchangeable` category |
| `answer.py:1169` `unique-entity` consumer | exactly one entity holds the measure |
| `answer.py:1295` `difference` consumer | exactly two holders |
| `obligations.py:249` `_candidates` | **the sole exception — it *ranks*** |

`obligations.py:249-254` is the only place in the codebase that ranks candidates:

```python
if len(out) > 1:
    # Adjacency arbitration: the nearest candidate wins ONLY if strictly
    # nearer than all others; equal distance stays ambiguous.
    out.sort(key=lambda u: (abs(u.span[0] - holder.span[0]), u.span[0]))
    if abs(out[0].span[0] - holder.span[0]) < abs(out[1].span[0] - holder.span[0]):
        return [out[0]]
```

That is already a **deictic distance with strict-dominance arbitration**: an origo (the
holder's span), a metric (token distance), and a tie→decline rule. It is sentence-local
and serves one obligation kind. **It is the seed of the design in §2.**

### 1.2 Referent identity is a string, repaired retroactively

`Quantity.entity` is a `str`. Two mentions co-refer because their **strings are equal**.
When two distinct referents collide on one string, `FactStore.admit` (`facts.py:33-268`)
repairs it *after the fact* via five near-identical "mirrors" that re-key `entity` →
`entity[owner]`, `entity[qualifier]`, `measure[qualifier]`, `entity[label]`, or split on
conjunct `segment` — all documented as consulted "**only** at collision time".

The consequence is in the code: **two referents are distinguished only once they
disagree numerically.** "Jar A" and "Jar B" both holding 5 marbles silently dedupe into
one fact. That is individuation done backwards — what you must do with strings instead
of referent objects.

### 1.3 Relative event time exists; quantity time is still opaque

- `Quantity.time` is the **two-word surface string** of a sentence-initial `timeperiod`
  adjunct (`"last year"`), set by `learn._sentence_time()`. Never ordered or normalised.
- Its only use is to **refuse** to combine facts. Five sites say verbatim:
  `# mixed times — time arithmetic is unbuilt` (`answer.py:187,314,415`;
  `saturate.py:872,1436`).
- Tense is **erased** by `condense.py` ("has found" → `find`), never recorded.
- The relative markers `yesterday`, `now`, `today`, and `tomorrow` now carry signed
  offsets in pack data. One marker attached to one unambiguous predicate emits an
  `EventTime`; differing offsets derive `Before(earlier, later)`. This orders those
  event occurrences without pretending that opaque calendar labels are comparable.
- `Before` still has no standalone answer consumer. It is preserved semantic evidence,
  visible in the fact and deictic-field views.
- One narrow ask can now say *which relative day* it means: the finite-domain location-
  witness query carries a declared `when` marker. There is still no generic reference-
  time field shared by quantity, state, and event asks. (§4 shows what this costs.)
- Time units (`day`→`hour`) share the flat conversion graph with `gallon`→`pint`. A week
  is 7 days in exactly the sense that a gallon is 8 pints.

### 1.4 Space exists as event-linked roles, not yet as a general geometry

- Exact pack-declared preposition/object/verb frames preserve spatial location, source,
  goal, and path as `VerbalRelation` facts. `in`, `into`, `from`, `to`, and `at` are no
  longer discarded or treated as interchangeable when such a frame survives.
- Spatial relations share an event identity with `EventTime`. Declared initiating,
  terminating, and holding predicates can therefore emit `LocationEvent` fluents without
  joining unrelated occurrences of the same verb.
- A narrow finite-domain ask can query which named members of a prior subject group are
  at one place on one relative day. An impossible-termination assumption may preserve an
  earlier initiation. A direct negative location observation is `contradicted`; silence
  remains `unknown` and conflicting direct observations decline.
- An explicit factual no-departure sentence can also preserve an earlier initiation, but
  through `LocationTransitionAbsence`, not impossibility. Its first controlled scope is
  the current narrative through the question's reference day; a departure within that
  interval conflicts, while a declared future departure does not.
- Places are still normalized entity strings, not typed spatial regions. There is no
  containment lattice, distance metric, route reasoning, or generic transfer endpoint.
  The arithmetic holder/location shortcuts also remain separate from these event fluents.

---

## 2. The abstraction

A deictic expression resolves as **(dimension, origo, distance, arbitration)**:

- **dimension** — `person` | `discourse` | `time` | `place`. Referents are *typed*, so a
  time expression is never a candidate antecedent for a personal pronoun.
- **origo** — the reference point: where/when/who the reading is "standing".
- **distance** — how far a candidate sits from the origo *along that dimension*
  (recency for discourse, elapsed time for temporal, containment depth for spatial).
- **arbitration** — strict dominance: nearest wins **iff strictly nearer than every other
  survivor**; ties decline. Precisely `obligations.py:249`.

The load-bearing engineering consequence:

> **With a constant distance function this reduces *exactly* to "unique candidate, or
> decline."**

So the fifteen sites can migrate onto one primitive with a **provably 0-diff** behaviour
change, and each dimension's real metric is switched on afterwards as its own gated
increment. No site changes behaviour at migration time — which is the answer to the
shared-kernel blast radius this project has been bitten by before.

---

## 3. Evidence (dev-train, read-only; TEST untouched)

| | share of dev-train |
|---|---|
| contains any deictic/anaphoric expression | **90.1%** |
| **ask sentence** depends on unresolved reference | **63.1%** |
| singular/neuter pronoun + 2+ names → **unbindable today** | 22.7% |
| plural pronoun → **never binds** (hard-coded skip, `document.py:92`) | 21.0% |

**Stated honestly: deixis is *not* the main cause of the 61% "no ask shape" gap.** Items
whose ask pronoun is unbindable decline on that reason at **58.5%**, versus **43.7%**
when the pronoun *is* bindable and **45.6%** when there is no pronoun. A real but modest
elevation. Deixis is a pervasive, independently-addressable weakness — not the seam.

**Three measured openings:**

1. **Group/plural reference is entirely unbuilt.** `document.py:92-94` skips plural
   pronouns outright ("group referents are unbuilt"). Addressable pool: **141 dev-train
   items** — *"How long is **their combined** experience?"*, *"How much did **their**
   breakfast cost?"* — all `no ask shape`.
   *Latent hazard:* the `combined` consumer enumerates **all** holders and never resolves
   "they", so a **sub-group** reference (*"Bill and Dale eat 50% of their pizzas and Ann
   and Cate eat 75%…"*, a real dev item) would silently sum the wrong set.

2. **Temporal: the documented open bug is an origo bug.** `answer.py:318-331` declines
   whenever a `state` is narrated *after* an event, because *"Kendall finds 6 dimes. She
   **now** has 6 dimes"* is 6, not 12, and nothing distinguishes a restatement from an
   extra holding. But the deictic `now` **is** that signal, and the `temporal_marker`
   category (`now`, `today`) already exists as data.

3. **Spatial: a latent confident-wrong.** The source PP is discarded, so a removal never
   decrements the container:
   ```
   "The jar has 10 marbles. Sam took 3 marbles from the jar.
    How many marbles are in the jar?"     → engine COMMITS 10.0   (gold 7)
   ```
   4/4 synthetic variants commit wrong — including `ate`, which *is* a signed `lose` verb;
   the event attaches to Sam and the jar is untouched. On dev-train the shape appears in
   **33 items, all currently declining** for other reasons. It costs nothing today, but it
   is a confident-wrong generator that **ask-shape growth will switch on**.

---

## 4. The month experiment — run, gated, REVERTED

This is the most informative result of the pass, and it is a **negative** one.

### The bug

`senses.py`'s capitalisation heuristic overrides any capitalised mid-sentence word to
`name` — *unless* it is in the `timeperiod` category (the exemption **increment 88** added
for weekdays). Weekdays were retagged `time` → `noun` + `timeperiod` and are safe.
**Months were not:**

```
march     senses=['time']   in timeperiod=False   → sensed as a proper NAME
monday    senses=['noun']   in timeperiod=True    → correct (increment 88)
```

So *"In March, Sam had 12 apples. He found 5."* puts **March** in the antecedent pool as a
rival person; `He` can no longer bind uniquely; Sam's quantity is dropped entirely
(`no quantity known for 'sam'`). All twelve months carry this. dev-train: 66 items mention
a month, **49 of those also contain a singular pronoun, and none are solved.**

**This is the thesis in miniature:** a *time* expression pollutes the *person* antecedent
pool because referents carry no dimension type. Increment 88 fixed one instance by hand;
months are the same bug in a new costume.

### The fix, and why it failed

Retag the 11 unambiguous months (`may` excluded — it is genuinely modal/month ambiguous,
and a second sense would trigger the `obligations.disambiguate()` race `registry.py`
documents for `ones`) to `noun` + `timeperiod`. Pure data, zero Python.

**The dev gate rejected it: `DECL→WRONG 1`, precision 100% → 98.9%, `VERDICT: REVERT`.**

```
Benny ... In January he adds $19, then adds the same amount in February.
By the end of March, he has $46. How many dollars did he add ... in March?
                                        gold 8    →    engine committed 19
```

Once `March` became a readable time-noun, an ask shape **finally matched** — and the
consumer returned **19**, the *January* amount. The store held
`Quantity(add, $19, time='in january')`; the question asked about **March**; **nothing
compared them**, because *no ask can express a reference time* (§1.3).

### What it proves

The two halves of the fix are **inseparable**: `senses.py`'s exemption is keyed on
`timeperiod` membership, so a month must join that category to stop being a rival name —
and joining it is exactly what makes `learn._sentence_time()` start stamping `time` and
lets time-adjunct asks match.

> **Making a time expression *readable* exposes the fact that the engine cannot ask
> *when*. The month fix is therefore not "free" — it is *gated on* the temporal origo.**

This re-orders the roadmap: **Phase 3 (the temporal origo) must land before the month
fix**, not after it. And it is direct evidence for the thesis — the missing origo is not
merely a coverage ceiling; it actively **blocks an otherwise-clean precision fix**, and
turns it into a confident-wrong.

The generalised lesson, now confirmed twice (here for time, and predicted in §3.3 for
space):

> **Do not make a deictic dimension readable before the ask can name a point along it.**
> Doing so converts declines into wrongs.

---

## 5. Roadmap

- **Phase 1 — the seam.** `kernel/deixis.py` (new, additive): `Origo`
  (sentence, span, moment, locus), `Referent` (typed by dimension, with `number` and group
  `members`), `resolve(candidates, origo, distance, *, filters=())` with strict-dominance
  arbitration. `filters` are precision-only (they can only shrink a candidate set).
  No pack-schema change. **Do not name anything `anchor`** — already taken three times
  (obligation role, `AnchorQuantity`, `anchored-relation`).

- **Phase 2 — the temporal origo (in progress).** Relative event markers now have signed
  offsets as DATA (`now`/`today` = 0, `yesterday` = −1, `tomorrow` = +1), emit
  `EventTime`, and derive the formerly dead `Before` relation. One location ask carries
  a day-grained reference marker, proving the query seam without claiming a universal
  temporal model. Absolute-year ages use a separate conservative seam:
  `AgeAtYear` preserves the entity, age, and integral source year. Its dedicated asks
  project one entity to another explicit integral year, every member of one exact
  prior subject group to a caller-supplied current year, or that exact group to an
  explicit year and sum it when the surface explicitly asks for a combined or total
  age. Group projection is all-or-nothing. The engine never reads the wall clock, and
  a missing current-year context declines. It does not order or extrapolate
  `Quantity.time` values. Remaining: promote quantity `time` to an ordered **`Moment`**, advance
  the narrative origo, support counted expressions such as `ago` = −N, and add a shared
  reference-time field to other ask families. Flagship: a state narrated at the deictic
  present *restates* the running total → anchor/replace instead of sum, fixing the open
  `answer.py:318-331` bug.

- **Phase 3 — the month fix** (blocked on Phase 2; see §4).

- **Phase 4 — the spatial origo (partially implemented).** Source-indexed adposition
  frames now preserve spatial location/source/goal/path roles, and a small declared verb
  class maps some of those event-linked roles to initiating/terminating/holding location
  fluents. A finite named group plus an explicit day and place supports conservative
  witness selection. Remaining: typed place referents, containment and movement paths,
  generic transfer endpoints, and a spatial origo/distance model. Those pieces must land
  before broad container asks or inferred route membership.

- **Phase 5 — person/group deixis.** Group referents for they/them/their (141 items),
  routed into `combined` and used to *bound* it — which also closes the sub-group hazard.

- **Phase 6 — migrate the fifteen**, one per increment, constant distance ⇒ 0-diff.

## 6. Risks

- **A clean DEV gate is necessary but never sufficient** (`negative-results.md`: increment
  81 died at TEST look #78 with 7,473 DEV items saying it was safe). Phases 2, 4, 5 add
  *inference* — exactly where that lesson was learned.
- **Strict-dominance ranking is the one genuinely new precision surface.** Ties must
  decline. Any increment that makes ranking *less* strict is a confident-wrong factory.
