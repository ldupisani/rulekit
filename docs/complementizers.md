# Complementizers: a design note

*Research pass, 2026-07-14. Analysis + one simulated experiment. Measured at `bc8f33b`
(dev-train 95/0, 100% precision).*

Companion to [`deixis.md`](deixis.md). Same question, different phenomenon.

A **complementizer** is a word that introduces a subordinate clause and makes it an
**argument of a higher predicate** — *that* / *if* / *whether* / infinitival *to*, plus
the relativizers *that* / *which* / *who*. "She knows **that** he has 5" does not assert
that he has 5; the clause is an argument of *knows*.

This note asks whether complementation is a useful organising abstraction for rulekit.

**It is genuinely absent from the engine — and, unlike deixis, building it buys almost
nothing. The recommendation is not to build it.** That negative is the deliverable: it
should save the project from an expensive, plausible-looking mistake.

---

## 1. What the engine has today

**A sentence is a flat bag of tokens.** `Reading.units` is a `list[Unit]` — no tree, no
nesting, no clause node, no sub-`Reading`. The whole representation is fixed at depth 2
(document → sentence → unit). **Clause structure is not representable.**

Four mechanisms compensate:

**1. Textual pre-splitting.** `engine.py` shreds clauses into separate *sentences*
**before tokenization**, by string surgery, deleting the marker with a slice index
(`clause[2:]` chops `"if "`):
`_split_leading_clause` (`:107`), `_split_leading_temporal_clause` (`:124`),
`_split_trailing_clause` (`:150`), `_split_trailing_clause_commaless` (`:189`),
`_split_conjoined_clauses` (`:349`).

`_split_conjoined_clauses`'s own docstring says why it must exist: the engine
*"folds only the FIRST clause (the verb→dobj obligation binds once per sentence)"*. It
cannot hold two clauses in one `Reading`, so it rewrites one sentence into N.

Note the asymmetry: `split_question` splits **only the question sentence**
(`premises = sentences[:-1]`, passed through untouched). A subordinate clause in a
premise is never promoted.

**2. One boundary predicate, keyed on one word.** `_crosses_clause_boundary`
(`obligations.py:81-86`) is the **only** clause-scope mechanism in the system:

```python
def _crosses_clause_boundary(reading: Reading, a: Unit, b: Unit) -> bool:
    lo, hi = sorted((a.span[0], b.span[0]))
    return any(u.sense() == "complementizer" and lo < u.span[0] < hi
               for u in reading.units)
```

**The lexicon contains exactly one `complementizer`: `that`.** Every other subordinator
— `because`, `while`, `when`, `since`, `if`, `so`, `but` — is sensed `conjunction`;
`before` is `preposition`; `which` is `wh_which` (no role, inert); **relative `who` does
not exist** (it is lexiconed `interrogative`). For all of them the predicate returns
`False`, and **argument binding is free to cross the clause boundary.**

`_clause_negated` (`learn.py:246`) also leans on this predicate, so negation scope
inherits the same blind spot.

**3. Sense priors instead of structure.** Increment 101 fixed a silently-dropped clause
not by representing the boundary but by *reordering* a "counted nouns are rarely agents"
heuristic. `_candidates` then bottoms out in **adjacency arbitration** — proximity
substituting for structure, the same tell the deixis pass found.

**4. Six copy-pasted stop-scans.** `learn.py:391,432,552,637,715,758` each repeat
`if unit.sense() == "complementizer" or unit.surface in (".", "?", "!")`.

### The discard inventory

Every complementizer is matched and thrown away:

| complementizer | where it dies |
|---|---|
| leading / trailing `if` | `engine.py:119,180,210` — `[2:]` string slice |
| `when` / `after` | `engine.py:142` — `[len(marker):]` |
| `because`/`so`/`but`/`since`/`while`/`or`/`nor` | `engine.py:408` — consumed as a *coordinator* boundary |
| `that` (relativizer) | bare `{lit: that}`, 9 sites in `core.yaml` |
| `that` (complementizer) | `{slot: c, cat: complementizer}` (`core.yaml:1513,1559`) — a **named slot read by nothing**, present only so the matcher can swallow the token |
| infinitival `to` | bare `{lit: to}`, 8 sites — and `to` has **one sense** (`preposition`), so infinitival and dative `to` are the same object |
| the infinitive's own verb | captured into a slot and **deliberately never emitted** (`Goal`, `model.py:659`) |
| `whether`, `whom`, `whose`, `unless`, `until`, `though` | not in any lexicon |

---

## 2. Measured: the coverage payoff is ≈ zero

The obvious avenue is to **extend the clause splitters to premise sentences**. I
simulated it at the input-text level (no engine change): rewrite every premise of the
form `<SUBORDINATOR> <clause>, <rest>` into two sentences, using the engine's own
digit guard, then re-run dev-train.

| splitter extended to premises | SOLVED | BROKE | DECL→WRONG |
|---|---|---|---|
| `if` only | **+0** | 0 | 0 |
| `when` + `after` | **+1** | 0 | 0 |
| all 8 subordinators | **+1** | 0 | 0 |

**One item.** And the project's own history says the same thing every time:

- **increment 39** (`when`/`after` splits) — **0 SOLVED**, "pure groundwork"
- **increment 12** (trailing `if`) — **NEUTRAL**
- **increment 53** (comma-less trailing `if`) — **+2 of 83** candidate items
- **increment 100** (`that`-relatives) — **+1 by design**

The reason is already recorded in `HANDOFF.md`: clause splits *reliably* gate
NEUTRAL/0-SOLVED **because the downstream consumer is the real blocker.** 46.9% of
dev-train items carry a subordinator inside a premise, and it does not matter — the
clause is not what is stopping them.

> **Complementation is a dead end for coverage.** This is the most useful thing the pass
> establishes, and it is worth more than another +1. A future scout proposing clause
> splitting as a coverage play should be pointed here.

---

## 3. Where complementation *has* mattered: precision

**Two of the four latent bugs ever found in this project are clause-boundary bugs** —
and neither was findable by coverage mining:

- **Increment 90** — appositive relation standards. Two confident wrongs on main:
  *"Harvey runs 8 miles more than his friend Sam. Sam runs 12 miles."* → committed
  **8.0** (gold 20).
- **Increment 101** — coordinated-clause binding. *"Bruce **scored** 4 goals and Michael
  scored 3"* silently dropped Michael's entire clause, while *"Bruce **ate** 4 apples and
  Michael ate 3"* worked. Verb-category-dependent, not lexical.

**Exposure surface today: 545 dev-train items (14.4%)** contain a premise with an
**unmarked two-clause boundary** — a non-`that` subordinator with a finite verb on both
sides, which `_crosses_clause_boundary` cannot see. **535 of them are masked only
because the item declines for an unrelated reason.** Ten commit, and all ten are
`as`-comparatives, which the relation rules *intentionally* match through.

That is the deixis lesson repeating exactly: **a latent confident-wrong pool that
growing ask coverage will switch on.**

> **Design constraint, found empirically: `as` must never become a clause boundary.** It
> is the comparative standard marker — `_is_relational_clause` already excludes
> comparative clauses for this reason.

---

## 4. Verified defects (known, unfixed)

All reproduced by running the engine at `bc8f33b`.

### (a) A false invariant in a frozen-kernel scan function

`_is_conjunction_word` (`engine.py:219`) decides clause boundaries by testing lexicon
sense `conjunction`. Its docstring asserts:

> *"packs/core-english's 'and' — **the ONLY member today**, but zero words are
> enumerated here; constitution rule 1"*

**False.** The bench registry has thirteen:

```
['&', '+', ':', 'and', 'because', 'but', 'if', 'nor', 'or', 'since', 'so', 'when', 'while']
```

So `_split_conjoined_clauses` treats **subordinators as coordinators**, splits the
sentence, discards the marker, and asserts both clauses as independent facts:

```
"Tom has 3 apples if Mary has 5 apples.  How many apples does Mary have?"   → 5.0
                                          (the conditional is simply erased)
```

**Honest assessment: benign on dev-train today.** Only **8** premises actually split at
a subordinator (7 × `while`, 1 × `so`), and in every one the clause *is* veridical
("Mila makes $10 an hour **while** Agnes makes $15"), so no wrong is produced. But the
docstring is wrong in a frozen scan function that increment 57 took **four** landing
attempts to stabilise, and the next author to reason from it will be misled.

*Principled fix (deferred):* a `coordinator` **category** in pack data (`and`/`or`/`but`)
tested instead of the raw `conjunction` sense — making the boundary set explicit data
rather than an accident of which packs are loaded, as constitution rule 1 intends. It
**narrows** the split, so it can BREAK the 8 items above and must be gated.

### (b) A live ordering bug — a promoted clause can never supply a pool total

Named at `HANDOFF-archive-2026-07-16.md:5443` (batch 39 finding #2). `_split_trailing_clause`
appends the promoted clause as the
**LAST** premise, but `_pool_before` / `_candidate_measure` (`saturate.py`) require a
pool total to come from a **strictly earlier** sentence.

```
"Sam ate half of the cookies. How many cookies did Sam eat, if there were 20 cookies?"
   premises: ['Sam ate half of the cookies.', 'there were 20 cookies.']   → DECLINED
"There were 20 cookies. Sam ate half of the cookies. How many cookies did Sam eat?"
   premises: ['There were 20 cookies.', 'Sam ate half of the cookies.']   → 10.0
```

Same facts, different order. Fixing it touches `_pool_before`'s hard-won sentence-order
invariant ("out-of-order = self-collision") and needs its own gated increment.

### (c) Dead schema

`match: {sentences: ...}` is declared in `schemas.py:281` and skipped in
`patterns.py:510` with a comment claiming document-level handling that **does not
exist**. Zero packs use it. (Twin of the dead `Before` fact class the deixis pass found.)

### (d) Reported speech is asserted as fact

*"John says he has 5 apples"* — no `that`, so no wall, so the ordinary SVO fold commits
`Quantity(…, 5)`. There is **no factivity or veridicality check anywhere in the
pipeline**. Latent; GSM8K's genre currently forgives it.

### (e) `needs to save $20` has no rule

`goal-need-quantity` requires `need` to be *immediately* followed by the counted item.
`to` is sense `preposition` and is not in `SKIPPABLE_SENSES`, so the infinitival form
never matches. `has to pay` — nothing at all.

---

## 5. Recommendation: do not build clause structure

The abstraction is real and genuinely missing, but the project's binding constraint is
**coverage** (95 → 100), and clause structure is measured at **+1**. Building it would
widen the boundary predicate, which makes *more* bindings fail — a BROKE risk against a
benefit of roughly zero.

**Deferred, and recorded here so it is not silently dropped:**

A **`clause: int` index on each Unit**, assigned once by a boundary scan over a
pack-declared `clause_boundary` category (excluding `as`). Then
`_crosses_clause_boundary` becomes `a.clause != b.clause`, the six copy-pasted
stop-scans collapse, negation scope becomes correct by construction, and
`_sentence_time` can be clause-scoped.

**Revisit only if TEST precision starts failing on clause-boundary shapes** — which §3
argues is the eventual failure mode as ask coverage grows.

---

## 6. The shared diagnosis

This pass and [`deixis.md`](deixis.md) reach the same place from opposite directions:

> **The engine substitutes proximity and string surgery for structure.**

Deixis: with no origo, referents cannot be *ranked*, so the only safe rule is "unique
candidate or decline" — written out 15 times. Complementation: with no clause node,
constituents cannot be *scoped*, so boundaries are approximated by deleting marker words
before tokenization and by one predicate keyed on the single word `that`.

Both bottom out in the same fallback — `obligations.py:249`'s **adjacency arbitration**,
where the nearest token wins. That function is the engine's structural model, and it is
a ruler.

The difference is what the missing abstraction *costs*:

|  | deixis | complementation |
|---|---|---|
| coverage upside | large (141-item group-reference pool alone) | **measured at +1** |
| precision risk | high, and **it blocked a clean fix** (the month experiment) | high, but **latent** (535 of 545 masked by declines) |
| verdict | **build it** (temporal origo first) | **do not build it** |
