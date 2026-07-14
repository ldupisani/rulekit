# NEXT SESSION: the DUAL brief — fix BOTH halves of the SAME items

**Self-contained. Read `CLAUDE.md` (the constitution) and this file.**

Branch: `experiment/compositional-ask` (pushed, `92864f0`). `main` is untouched at 103/0.
Working tree there is clean and fully gated: **dev-train 103/0, dev-holdout 40/0, suite 52/52,
pytest 998, 0 BROKE, 0 DECL→WRONG** — and **0 SOLVED**.

> **NEUTRAL is a PLATFORM, not a verdict.** `enabler-must-be-bought` exists to stop unbought
> infrastructure reaching **TEST**. It is not a reason to stop exploring. We do not *commit* a
> neutral to `main` — we *build from* it, on the branch, until we hit wrongs or false
> positives. That is the wall. 0 SOLVED is not the wall.

---

## 1. THE LAW that makes every previous brief shape dead

Measured this session, from both directions (`docs/negative-results.md`, "THE MUTUAL BLOCK"):

> **Fix the READING → the items die at the ASK wall.** (67% of the reading gap: no ask fires.)
> **Fix the ASK → the items die at the READING gap.** (The frame parses 24 questions
> correctly; all 24 die on missing premise facts.)
>
> **The two gaps are MUTUALLY BLOCKING. Neither side alone converts anything.**

This is why **every** single-sided intervention in this campaign measured 0 SOLVED — the 481
per-unit seam, the GroupTotal fix, the month/time guard, `save`→`acquire`, the `future_modal`
widening, and a working compositional ask parser. It was never bad luck, and the seams were
never "exhausted." **A declining item is blocked on several coordinates at once, and fixing one
coordinate leaves it declining on the next.**

**Therefore: a brief that names one half is a dead brief.** Every increment from here must name
**both**:

```
evidence.premise_mechanism : the fact the premises fail to yield
evidence.ask               : the ask that folds it
evidence.same_items        : the ITEM IDS where BOTH are the only blockers   <- NEW, REQUIRED
```

`premise_mechanism` already exists as a required schema field in `.claude/workflows/mine.js`.
It was reaching for exactly this. **Add `same_items`** — a brief that cannot list the items
where its two halves are *jointly sufficient* has not been measured, and the shape gate must
reject it.

## 2. What the compositional frame actually bought

It converted **multiply-blocked items into SINGLY-blocked ones.** That is its whole value, and
it is why it stays alive despite 0 SOLVED:

```
before the frame:  item blocked on {premise, ask}   -> no single fix can convert it
after  the frame:  item blocked on {premise}        -> ONE fix converts it
```

The items it parses are the **only place in the corpus where a premise fix can convert
anything.** They are the seed pool for every dual brief below.

## 3. THE SEED INCREMENT — superordinate aggregation

The dominant premise failure among frame-parsed items (5 of 10) is one mechanism:

```
"A zoo has 21 penguins and twice as many polar bears?  How many total animals do they have?"
gold 63  ( = 21 + 42 )

FACTS:   Quantity(penguin, 21)   Quantity(bear, 42)    <- premises READ PERFECTLY
ASK:     frame -> {consumer: combined, measure: 'animal'}   <- question PARSED
DECLINE: "a combined ask needs at least two holders of 'animal'; found []"
```

**The question asks about a CATEGORY; the premises state its MEMBERS.** Both halves are already
in hand. The facts are keyed `penguin`/`bear`; the ask asks for `animal`; and `animal` is
*already a pack-owned category with 46 members*.

Siblings in the same pool, all `found []` on a superordinate measure:

```
How many total animals do they have?           -> holders are penguins, bears
How many total matchbox vehicles does he buy?  -> holders are cars, trucks
How much do the two siblings weigh together?   -> holders are two named people
```

### The mechanism (both halves, named)

- **Premise half:** member quantities — *already extracted*. No new fact kind, no new fold.
- **Ask half:** `how many total ANIMALS` — *already parsed* by `kernel/askframe.py`.
- **The missing fold:** `_combined_holder_totals` (`kernel/answer.py`) resolves the ask's
  measure **through the category hierarchy** when no direct holder exists: if `measure` names a
  category, sum the quantities of its **member** measures (`reg.cat_members_deep(measure)`).

This is **hypernymy** — superordinate reference — a construction attested in every reference
grammar, and the category hierarchy it needs is already pack-owned. Constitution-clean: the
kernel names a CATEGORY as structure; every word stays in YAML.

### ⚠ THE PRECISION LINE — read before writing a line of code

The codebase **already forbids** something that looks like this, and the distinction is the
whole increment. From `currency` in `packs/core-english/categories/core.yaml`:

> `interchangeable: true` — *the ONLY category allowed to resolve a factless ask noun to its
> in-store sibling (**cat/dog in 'animal' must never stand in for each other**).*

That prohibition is on **SUBSTITUTION** — letting `cat` answer a question about `dog`. It is
correct and must stay.

**This increment is AGGREGATION, not substitution:** summing *every* member of the category to
answer about the category. `cat + dog = animal` is sound; `cat ⇒ dog` is not. They are different
operations and the guard must distinguish them explicitly, not be relaxed.

**The guard:** superordinate resolution fires ONLY for the `combined`/`average` consumers (which
sum over ALL holders), NEVER for `single-entity` (which picks one). If a `single-entity` ask
ever resolves through a category, the increment is wrong — that is substitution wearing
aggregation's coat.

### Known sub-gap, and it is the dangerous one

`penguin` is **not** in the `animal` category (46 members; `bear` is, `penguin` is not). So the
zoo item needs the mechanism **and** a category-membership admission.

**That is vocabulary admission — the single most precision-dangerous change class in this
project.** It TEST-killed the 12-word batch (85.7% → 75%) and put `fruit` in
`quarantine.yaml` as measured poison. **CHECK `packs/difg-mined/quarantine.yaml` FIRST**, admit
ONE tight family per increment, run the methodology §4 permissive scan, and expect the TEST look
to be the real gate.

Land the **mechanism** first, on items whose members are *already* in the category. Admit
vocabulary as a separate, later increment with its own TEST look. Do not bundle them — a TEST
drop must be attributable.

## 4. The frame roadmap — what FEEDS more dual briefs

The seed pool is only 10 items because the frame is deliberately conservative. Each bail below
is a **frame capability** that would enlarge the singly-blocked pool. Measured over declining
`how many`/`how much` questions no template claims:

| frame bails on | items | verdict |
|---|---|---|
| other unread content | 616 | investigate — the residual |
| verb count ≠ 1 (perfect / copula / elided verb) | 402 | **best next capability** |
| capacity modal (`can`/`could`/`must`) | 397 | **LEAVE — a deliberate guard.** *How many CAN he buy* is a capacity question, not a factual one (the increment-14 kirsty lesson). Two unit tests enforce it. |
| comparative operator (`more`/`fewer` … `than`) | 177 | real: route to the `difference` consumer |
| remainder operator (`left`/`remaining`) | 105 | real: route to a remainder consumer |

**Work the frame ONLY to feed a dual brief.** Growing the frame for its own sake is another
single-sided fix and will measure 0 SOLVED again — that is the law in §1, and it applies to the
frame as much as to anything else.

## 5. The gates (unchanged, and they have all earned it)

Per increment: baseline snapshot → change → `rulekit diff` (**0 BROKE, 0 DECL→WRONG**) →
dev-holdout (0 new wrongs) → synthetic unit test (never a GSM8K string in `tests/`) → **one TEST
look**. A TEST precision drop reverts that commit, no matter how good DEV looked.

**Two traps this session proved are live, on my own code:**

- **A clean DEV gate is necessary and NEVER sufficient.** The frame listed `modal` as inert and
  answered hypotheticals as facts. The dev diff said NEUTRAL across all 3,772 items. **Two
  synthetic unit tests caught it.** Write the unit test for the *guard*, not just the feature.
- **"Read" is not "used."** A safety invariant satisfiable *vacuously* launders a guess as a
  checked answer (the frame marked `vegetables` read, dropped it, and answered about beef).
  Every content word must be **used in the resolves**, not merely touched.

## 6. Stop conditions

- **The dual pool cannot be grown past ~30 items even with the frame roadmap.** → the mutual
  block is the true ceiling; GSM8K is done for real. Record it, move to
  `docs/difg-corpus-plan.md`.
- **Superordinate aggregation produces a DECL→WRONG on dev, or a TEST precision drop.** → revert;
  the substitution/aggregation line could not be held in practice, and that is a real result.
- **A brief cannot list `same_items`.** → it has not been measured. Reject it at the gate.
