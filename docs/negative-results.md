# Negative results (methodology §8: record, don't repeat)

## 2026-07-11 — rate machinery reverted at TEST look #4

**What shipped:** increments 8+9 — Rate facts ("$18 an hour"), the
rate-span consumer with unit conversion, ask-specificity ordering
(max-consumed-units wins), the `entity` slot type, value-slot-only ask
consumption, rate × population.

**DEV evidence (all clean):** dev-train 13/0, dev-holdout 13/0 (+1 — the
Samuel-birds item), suite 52/52, 111 synthetic tests, two holdout-caught
classes fixed at the root during development (Minnie's absorbed
"four-minute", per-individual rates with populations).

**TEST verdict:** look #3 (before): 5 correct / 1 wrong / 83.3%.
Look #4 (after): 5 correct / 2 wrong / 71.4% — a precision DROP. The new
wrong is a §3a unseen-structure commit invisible to all 7,473 DEV items.

**Action:** full revert of both increments (`git revert 2d7b90c 0285d80`),
restoring the look-#3 committing surface exactly.

**Suspects (cannot be distinguished without breaking the firewall):**
1. the rate-span consumer's commits (rate matching on an unseen shape —
   most likely: it was the only genuinely new committer);
2. ask-specificity reordering (changes which ask wins on shapes where
   several match — could reroute an existing TEST commit to a different
   consumer).

**Re-landing plan:** one piece per increment, each with its OWN immediate
TEST look:
1. ask-specificity ordering alone (no new committers) → look;
2. Rate facts + rate-span WITHOUT conversion and WITHOUT population
   (the narrowest committer: exact-unit spans, lone-entity rates) → look;
3. conversion spans → look; 4. rate × population → look.
The reverted code is intact in git history at `2d7b90c`.

**Update (look #5, 2026-07-11):** re-landing step 1 (ask-specificity
ordering alone, DEV-diff-neutral) held TEST at exactly look #3's numbers —
5 correct / 1 wrong / 83.3%. The ordering is EXONERATED and shipped.
Suspicion now rests entirely on the rate-span consumer's commits.
Next: step 2, the narrowest committer (exact-unit spans, lone-entity
rates, no conversion, no population) behind its own look.

**RESOLVED (look #7, 2026-07-11):** the culprit was neither suspect. The
narrow rate-span committer re-landed with LEAKY accounting (look #6:
5/2/71.4% — the second wrong returned) and then with TIGHT accounting
(look #7: 5/1/83.3% — baseline restored, committer live). The regression
was the SIDE-EFFECT: a Rate fact's number satisfied value accounting by
mere existence, unlocking other consumers (the wage+bonus fold class:
"makes $18 an hour, got a $50 bonus" committed the bonus while ignoring
the wage). Fix: a rate's value counts as read only when the arithmetic
log consumed it. LESSON: a new FACT KIND changes what value accounting
considers "read" — every future fact kind must decide explicitly whether
existence or use constitutes reading. Remaining re-landing (conversion
spans, rate × population, entity slots) proceeds behind per-piece looks.

**Update (look #8, 2026-07-11):** re-landing step 3, conversion spans
(the `span_unit != rate.per` decline lifted, converting through the mined
`reg.conversions` table), held TEST at the exact look #7 fingerprint —
5/1/83.3%, zero TEST items touched at all. DEV both NEUTRAL. Shipped at
`4836b01`. Remaining: rate × population, the `entity` slot type.

**Update (look #9, 2026-07-11):** rate × population turned out to require
the `entity` slot type to be reachable at all — the only realistic
GSM8K shape ("the bird eats... in N days") names the rate's holder via a
common noun, and the live rate-span asks only accepted `type: name`. Both
landed together (`b8d7339`), the `entity` type applied narrowly to just
the two rate-span asks' `who` slot. TEST: precision held at 5/1/83.3%
(fingerprint changed — the committed/declined SET shifted, but correct
and wrong counts are unchanged, no regression). DEV: dev-train NEUTRAL,
dev-holdout +1 SOLVED / 0 BROKE / 0 DECL→WRONG (the same item the
original increment 9 predicted). Re-landing plan is now COMPLETE — all
four original pieces (ask ordering, narrow rate-span, conversion,
population/entity) are live.

## The 12-word vocabulary batch (staged as increment 20, REVERTED at look #20, 2026-07-11)

The /mine batch-4 candidate `vocab-ceiling-batch` admitted 12 quarantine-
clean words (fruit/fruits, complete, paper, planning, cream/creams, math,
fit, told, package/packages, carry, carton/cartons, stock) as pure YAML
lexicon additions. Every dev gate was clean (train and holdout diffs
NEUTRAL, fully-read ceiling +2.0pp train / +1.6pp holdout, 189 tests,
suite 52/52) — and TEST look #20 came back 6/2 (75.0%, was 6/1 85.7%):
one NEW confident-wrong unlocked on unseen text. Full revert of the
increment; main reset to the pre-batch state and dev verified
item-identical to the look #19 fingerprint (deterministic engine ⇒ TEST
restored without spending a confirmation look). The candidate branch
`mining/parked/vocab-ceiling-batch` preserves the exact word list.

Which of the 12 words unlocked the wrong is UNKNOWN (TEST is aggregate-
only; bisection would cost ~log2(12) ≈ 4 looks). Do not re-attempt as a
batch. LESSON (the difg vocab_singles lesson, now measured on rulekit):
vocabulary raises the fully-read ceiling for WRONGS as much as for
corrects, and dev/holdout cannot see the unseen-structure interactions
(§3a). Any future vocabulary admission must (a) run the methodology §4
permissive scan and ship only words whose unlocked problems are verified
decline→correct with zero new wrongs on dev, (b) admit ONE word (or one
tight family) per increment so a TEST drop identifies its culprit, and
(c) expect the TEST look to be the real gate. The implementer protocol
now requires the permissive scan for any vocabulary-admitting increment.

**Update (look #32, 2026-07-11): the batch culprit is IDENTIFIED — fruit/fruits.**
Batch 5 re-admitted the fruit family alone under the new one-family-per-
increment rule (increment 31, permissive-scan clean, all dev gates
NEUTRAL) and TEST dropped to exactly the look #20 signature: 6/2, 75.0%.
One word family, one look, culprit attributed — the isolation discipline
converted a ~4-look bisection into a single attributable revert.
fruit/fruits are now in packs/difg-mined/quarantine.yaml as TEST-measured
poison (the reviewer greps quarantine, so re-admission is blocked until
the underlying mechanism wrong is found and fixed). Whatever 'fruit'
unlocks commits a wrong via a mechanism dev never exercises — finding
THAT wrong from the dev side (permissive scan over fruit-containing
declines, looking for near-miss commits) is the durable fix path.

## The worklist counts surfaces, not shapes (batch 22, 2026-07-12)

**What happened:** three of five candidates in batch 22 gated cleanly, passed
review, and moved NOTHING — `percent-of-collection-asks`, `partitive-measure-recut`
and `attr-qualified-measure-subsets` all landed 0 dev-train SOLVED and were
demoted by the goal-mode gate. Three full implementer runs (worktree, dev gate,
synthetic tests, constitution review) bought zero coverage.

**The clearest case.** `percent-of-collection-asks` was scouted on a frequency
signal of 28 dev-train items (verified: 29 match `what percent(age)? of`). The
junior implemented the mechanism, then hand-scanned all 28 and found that **none
of them** present the shape it targets — `"N of them are ADJ. What percent of the
ITEM are ADJ?"`. What the 28 actually contain is multi-step arithmetic that
happens to *end* in a percent question:

- "However, 5% of the germs they kill are the same ones… What percentage of germs
  would be left after using both sprays?"
- "Then she quadruples the amount of water in the jug. What percentage of the
  liquid in the jug is koolaid powder?"

**The lesson — a frequency count is a SURFACE count, not a SHAPE count.** The
worklist tells you how many items contain a phrase. It cannot tell you how many
items have premises the mechanism can consume. For an ask shape, the ask is the
easy half; the premise structure is what decides whether anything resolves. A
high phrase frequency with an unexamined premise distribution is not evidence —
it is a hypothesis, and it is usually wrong, because the reason those items are
still declining is precisely that their premises are hard.

**What this costs:** ~1 implementer run per over-trusted signal, and it is the
single largest source of wasted work in the batches so far.

**What to do instead.** A brief that claims frequency N must also carry a
STRUCTURAL sample: quote 3–5 of the N items and show, for each, the premise the
mechanism would consume and the fact it would emit. If the scout cannot do that
for at least 3, the candidate is not ready — the number is a phrase count and the
class has not been demonstrated to exist. This is cheap for the scout (it is
already reading dev-train) and it is the difference between "28 items say
'percent'" and "28 items this mechanism can read".

**Not a constitution violation, and that is the point.** All three candidates were
clean, general, decline-safe machinery. The gate did its job and the goal-mode
SOLVED>0 check caught them. The failure was upstream, in candidate SELECTION —
and no amount of review discipline downstream recovers a wasted implementer run.

## Increment 81 KILLED at TEST look #78 (gifted-budget money-left asks, 2026-07-13)

**What it was:** "money-left asks over a GIFTED budget and container-partitive priced
purchases" — e.g. a budget arriving as a gift rather than as a stated holding, then
priced purchases drawn against it.

**DEV evidence (immaculate):** dev-train 59 -> 60 (SHIP, +1 SOLVED, 0 BROKE,
0 DECL->WRONG), dev-holdout NEUTRAL, suite 52/52, pytest green, lint clean. It also
passed constitution review. Nothing on 3,772 dev-train items or 3,701 dev-holdout
items said it was unsafe.

**TEST verdict (look #78):** 11 correct / **2 wrong** = **84.6%**, down from 10/1 =
90.9%. It bought +1 TEST correct and introduced a NEW CONFIDENT-WRONG. Precision
dropped 6.3 points.

**Action:** REVERTED — not landed on main. Branch `mining/cand-gifted-budget-money-left`
retained for postmortem.

**The isolation:** increment 82 shipped in the same batch and its look (#79, taken WITH
81 present) also read 11/2 — telling us nothing about 82 alone. So 82 was re-cut onto
bare main and given its OWN look (#80): **10/1, 90.9% — HELD.** That isolates 81 as the
sole culprit and let 82 land. A contaminated look is not evidence about the increment
sitting on top of the bad one; re-measure in isolation or you throw away good work with
the bad.

**The lesson (the whole reason the firewall exists):** a clean DEV gate is NECESSARY but
NEVER SUFFICIENT. Increment 81 commits on an unseen TEST structure that no DEV item
exercises — the §3a distribution-shift trap. 7,473 DEV items voted "safe" and were
wrong. This is the third TEST kill of the campaign (after the 12-word vocab batch at
look #20 and the fruit family at look #32), and the first of a STRUCTURAL increment
rather than vocabulary.

**Suspect, for any re-cut:** the gifted-budget premise likely widens what counts as a
budget/holding, letting money-left machinery commit where the budget was never really
stated. A re-cut must narrow the premise to an explicitly-stated budget and re-prove on
TEST with its own look.

## The shape gate was demanding PERFECT classes (2026-07-13)

**Three consecutive batches (35, 36, 37) landed zero coverage.** The cause was a gate I
built, not the seam.

`structural_sample.minItems` was **3**, and the shape gate required **>= 3 resolving**.
The scout, obeying the schema, walked exactly 3 items. So the gate was silently
demanding **3 of 3 — a 100% resolve rate on the sample.**

Batch 37's casualties tell the story:

| candidate | walked | pool |
|---|---|---|
| elided-measure-standards | **2 of 3** | 354 |
| discounted-purchase-totals | **2 of 3** | 24 |
| share-equally-division | 1 of 3 | 99 |
| capacity-ask-rate-fallback | 1 of 3 | 287 |

A class resolving 2 of 3 against a **354-item family** is an excellent candidate — it
was thrown away for a single non-resolving sample. Perfect classes do not exist in the
tail we are now mining, and we do not need them: a class that resolves 3 of 10 against a
70-item family is worth twenty-plus answers.

**FIX:** `minItems` raised to **8** (walk 8–12), bar unchanged at **>= 3 resolving** —
so the gate now means "38% of a real sample", not "100% of a token one".

**THE GENERAL LESSON:** a threshold and a sample size are one parameter, not two. I
tuned the threshold (3) and left the sample size at its minimum (3), which quietly
turned a reasonable-sounding bar into an impossible one. Whenever a gate reads "N of the
sample", ask what the sample size actually is in practice — the schema's `minItems` IS
the sample size, because an agent will supply exactly the minimum.

## Increment 128 — retry-on-decline (REVERTED at TEST look #122)

**What it did.** A clause promoted out of the question ("If Nils has 80 marbles, ...")
reads two ways and the surface order never says which: a CONDITION on the whole document
(belongs first) or the next EVENT in the narrative (belongs last). Reordering
unconditionally regressed 5 dev-train items, so the candidate instead **solved twice**:
today's order first, and — only if that DECLINED — again with the clause promoted to the
front.

**Why it looked safe.** `0 BROKE` was structural, not empirical: a committed answer is
returned untouched, so no previously-correct item can regress. The dev gate agreed —
**0 BROKE, 0 DECL->WRONG across 3,772 dev-train items**, 0 on dev-holdout.

**Why it was not.** *The safety proof covered the wrong failure mode.* `0 BROKE` says
nothing about **DECLINE -> WRONG**, and retry-on-decline hands every declining item — ~97%
of the corpus — a SECOND CHANCE TO COMMIT. TEST look #122: **11/1 (91.7%) -> 11/2
(84.6%)**. A new confident-wrong. Reverted; `main` fast-forwarded to increment 127 only.

**The tells, all visible BEFORE the look was spent:**
1. **0 SOLVED.** It bought nothing measurable and was justified purely as infrastructure
   for future classes — and `stated-total-complement-parts`, the very class it claimed to
   unblock, ALSO failed (0 SOLVED) in the same batch. Nothing cashed it in.
2. **A 32% bench tax** (dev-train 13.3s -> 17.5s), because it re-solves every declining
   item. Cost with no yield.
3. **A brand-new control-flow shape** — backtracking — introduced into `solve()`, whose
   whole character until now was a single deterministic pass.

**The lesson, and it is a general one:**

> **"0 BROKE by construction" is not "0 wrongs by construction."** A mechanism that only
> fires where the engine ALREADY declined cannot break a correct answer — but the declines
> are exactly where the engine has the least evidence, and giving them a second, weaker
> reading is a confident-wrong factory. **Precision-safety must be argued against
> DECLINE->WRONG, not against BROKE.**

This is the second increment killed at TEST after a spotless DEV gate (increment 81 was the
first, batch 2026-07-12). Both had a correctness argument that was *sound about the thing it
addressed* and *silent about the thing that killed them*. When a change's safety case names
only one of the two failure modes, assume the other is live.

## The infrastructure trap: 0 SOLVED on DEV, a WRONG on TEST (increments 128-retry, 129)

**Two consecutive TEST kills, same shape.** Both were "infrastructure" increments — a
widening of shared kernel machinery, justified not by items solved but by classes it would
unblock later. Both passed a spotless DEV gate. Both manufactured a confident-wrong on TEST.

| | dev-train | TEST | verdict |
|---|---|---|---|
| 128-retry (retry-on-decline premise reorder) | **0 SOLVED**, 0 BROKE, 0 DECL->WRONG | 11/1 -> **11/2** (91.7% -> 84.6%) | REVERTED |
| 129 (unbound event-verb themes, +230 lines in obligations.py) | **0 SOLVED**, 0 BROKE, 0 DECL->WRONG | 11/1 -> **12/2** (91.7% -> **85.7%**) | REVERTED |

129 is the more instructive of the two: **it gained a correct answer AND a wrong one.**
Coverage went UP. Precision went DOWN. Under "precision before coverage" that is a revert,
and it must be, because the +1 correct is visible and the +1 wrong is the one that
compounds — on unseen text there is no gold to tell you which is which.

### Why 0 SOLVED is a WARNING SIGN, not a neutral fact

An increment that widens what the engine will READ, and converts **nothing** on 3,772
dev-train items, has demonstrated exactly one thing: **its new bindings do not fire on text
we can check.** It has NOT demonstrated that they are harmless — only that DEV cannot see
them. TEST is where they fire, and there is no gold there to catch them.

A widening with 0 measured yield is not "safe because it changed nothing." It is
**unmeasured**, and the DEV gate's silence is the absence of evidence, not evidence of
absence.

### The rule

> **An infrastructure increment must be BOUGHT, not promised.** If it converts nothing on
> DEV, the only evidence for it is an argument — and every one of these had a sound
> argument that was silent about the failure mode that killed it.
>
> Do not land a shared-kernel widening on the strength of what it will unblock. **Land it
> together with the increment that cashes it in**, so its yield and its risk are measured in
> the same gate. If nothing can cash it in yet, it is not ready.

This retires the old infra bar (`unblocks` + >= 3 `resolves_after_unblocks`), which asked
for a PREDICTION and got one every time. Both of these cleared it. Neither survived.

## Process bug: five TEST looks spent, ledger rows LOST (2026-07-14)

Looks #120-124 were spent by checking out each staging commit **inside the staging
worktree** and running `--spend-test-look` there. Every git worktree has its OWN gitignored
`projects/gsm8k/snapshots/` directory, so each ledger row was written into the worktree —
and then deleted with it during cleanup.

The RESULTS survived (docs/HANDOFF.md and the commit messages). The LEDGER did not: 119
rows for 124 spent looks.

**Why this matters more than it looks.** The ledger is not a convenience — it is the
tamper-evident record of a deliberately RATIONED budget, and the only thing that makes "one
look per increment" auditable after the fact. A budget whose spend can silently vanish is
not rationed; it is merely believed to be.

**The rows were NOT reconstructed.** A `reconciliation` entry was appended disclosing the
gap, the five commits, and their results. An audit log with invented entries is strictly
worse than one with a disclosed hole — the hole is honest, the invention is not, and only
one of them survives someone checking.

**Fixed in the gate, not in prose:** `.claude/skills/mine/SKILL.md` now says looks are spent
FROM THE MAIN CHECKOUT (`git checkout <commit>` in the main repo, never in a worktree), and
mandates a post-batch reconciliation — `wc -l test-ledger.jsonl` must equal the looks spent
to date, or a look has leaked into a worktree.

## The 481-item per-unit seam: a CEILING, not a yield (2026-07-14)

**The measurement.** 481 dev-train items in the addressable pool (34% of it — 4.7x
everything the campaign has solved) contain an `each`/`every`/`per` premise that yields no
`Rate` fact. It looked like the single biggest missing mechanism in the engine.

**It is not missing.** `saturate.py::_distributive_container_total_synth` already composes
"each box has 8 pens" with "there are 20 boxes" into `GroupTotal(pen, 160)`. Probing eight
distributive surfaces, the engine derives the CORRECT total on five of them — and then the
entity-less consumer **declines in front of the answer it just computed**:

```
"There are 9 hands. Each hand has 14 bananas. How many bananas are there?"
  facts:  Quantity(world|hand|9)  Quantity(hand|banana|14)  GroupTotal(banana|126)
  answer: DECLINE — "'banana' has both a lone holder and a group total"
```

The guard's own comment refutes it: it establishes that the lone Quantity IS a per-unit rate
and the GroupTotal IS the total, then declines as if the ambiguity remained. An entity-less
ask ("how many bananas are there?") wants precisely the group's whole.

**Returning the GroupTotal fixes all five surfaces. It converts ZERO dev-train items.**
The guard fires on **0** real items. And the 182 declining items that DO carry a GroupTotal
die elsewhere — 110 on `no ask shape`, 26 on `no events known` — with golds that are not the
GroupTotal (one sample: GroupTotal=100, gold=16). They are multi-step.

**NOT LANDED, and that is the point.** The fix is correct, the argument is sound, and it is
0 SOLVED — which is precisely increment 129's shape, and 129's argument was sound too. A
change that makes a consumer COMMIT where it used to DECLINE, and that fires on nothing we
can check, is unmeasured, not safe. It would fire on TEST, unobserved, in the exact direction
that manufactures wrongs.

*A rule enforced on the scout and suspended for oneself is not a rule.* The patch is
recorded here; it lands WITH the class that cashes it in, or not at all.

**What this means for the ceiling.** The per-unit "seam" was a ceiling, not a yield. The
mechanism exists and works; the items are blocked further downstream, on multi-step
composition. **481 was the size of the hole, not the size of the fix.**

## A reachability bound without a null control is not evidence (2026-07-14)

Chasing the composition ceiling, I measured: *for each addressable declining item, can the
gold be reached from the numeric facts the engine already extracted, combining them with
`+ - × ÷` in ≤ 3 operations?* **271 of 1,435 (19%)** came back yes. That looked like a
well-bounded prize — 2.6× everything the campaign had built — and I wrote a four-phase
roadmap around it, for the most dangerous mechanism ever proposed here (the one whose failure
mode is a silent MULTIPLICATION, not a decline).

Then the TYPED probe — the same question restricted to compositions rulekit could
*principledly* perform — returned **13**. A 20× disagreement.

**The control that settles it:** run the same oracle against **another item's** gold.

| ≤3-op oracle, 1,143 items | | |
|---|---|---|
| reaches the TRUE gold | 439 | 38% |
| reaches a WRONG, randomly reassigned gold | 373 | **33%** |
| signal above chance | +66 | **+6%** |

**The oracle reaches a wrong answer almost as often as the right one.** An unconstrained
4-operator search to depth 3 over ~8 numbers explores a space big enough to hit nearly any
target by coincidence. The 271 was not a fact about the corpus. It was a fact about the size
of the search space.

> **Any "the information is already there, we just can't use it" claim must be tested against
> a shuffled target. If the method finds the answer when there is no answer to find, it has
> told you nothing.**

The composition project was abandoned before a line of kernel code was written
(`docs/composition.md`). It survived that long only because the typed probe disagreed and I
asked why rather than averaging the two numbers.

This is the same shape as every TEST kill in this campaign: **a measurement that was sound
about the thing it addressed and silent about the thing that mattered.** Here the unexamined
question was "would this method also succeed on a false hypothesis?" — and it would have,
33% of the time.
