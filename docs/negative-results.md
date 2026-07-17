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

---

## The reading gap is a LONG TAIL — GSM8K coverage is DONE (2026-07-14)

`docs/reading-gap.md` asked one question: of the ~1,164 declining items whose numbers the
engine never extracts, **is the reading gap a handful of premise surfaces, or a long tail?**

It ran. **It is a long tail.** Two independent findings kill it, and the second kills it twice.

### Finding 1 — two-thirds of the "reading gap" is not a reading gap

The brief assumed reading was the blocker. It is not. Bucketing the reading-gap pool by the
engine's own decline reason:

| reading-gap pool (≥1 unread numeric premise, fully-read, addressable) | 1,002 | |
|---|---|---|
| `no ask shape recognizes this question` | 496 | 49% |
| `no 'X' events known for 'X'/'X'` | 169 | 17% |
| **ask never fired → reading the premise converts NOTHING** | **670** | **67%** |
| premise-blocked (the ask FIRED and found nothing to consume) | 332 | 33% |

**The reading gap sits behind the ask-shape wall** — the seam already closed (5 batches,
+2 net). Fixing the reading on those 670 items converts zero of them. The convertible
sub-pool is 332, and — as always — **332 is a CEILING, not a yield.**

### Finding 2 — the structural clusters do not predict their own mechanism

The brief's central instruction was *cluster by STRUCTURE, never by lexical frame*, because
that inversion had flipped a conclusion three times. It was followed. It did not save the
hypothesis.

**The null control for clustering:** a structural cluster is a real mechanism class only if it
PREDICTS the missing fold. Operationalized — within a cluster, the engine's decline reason
should CONCENTRATE. Null = a random subset of the same size drawn from the same pool.

| cluster | n | top-share | null | signal |
|---|---|---|---|---|
| UNCLASSIFIED | 159 | 17% | 17% | **+0%** |
| partitive | 60 | 30% | 18% | +12% |
| distributive-each | 55 | 20% | 19% | **+1%** |
| mult-comparative | 53 | 19% | 18% | **+1%** |
| coordinated-qty | 30 | 37% | 20% | +16% |
| additive-comparative | 18 | 33% | 22% | +11% |
| **affine-comparative** | **14** | 21% | 24% | **−3%** |
| aggregate | 11 | 18% | 25% | −7% |

Read that table carefully:

- **`affine-comparative` — the flagship — has NEGATIVE signal and 14 items.** This is the
  Randy-the-mango-trees family (`5 less than half as many coconut trees as mango trees`) that
  the brief called "the reason to be hopeful." Its items share a surface and nothing else.
  **The hypothesis was falsified by its own headline example.**
- The three biggest clusters (`UNCLASSIFIED` 159, `distributive-each` 55, `mult-comparative`
  53) are at **+0%, +1%, +1%** — indistinguishable from random subsets. They are surfaces.
- `UNCLASSIFIED`, at 159, is the **largest bucket in the premise-blocked pool** (48%). A
  long tail announcing itself.

### The strongest cluster was a GUARD DOING ITS JOB

`coordinated-qty` (+16%, top-share 37%) looked like the most promising seam in the corpus and
would have been the obvious first mining brief. Its dominant member — **11 of 30** — is:

```
conflict: fold and fold disagree about ('quantity', 'james', 'week', 'sell', …)
```

That is **not a reading gap.** That is the engine reading the sentence *successfully* and the
collision guard firing on a precision conflict. The cluster's entire apparent signal is a
precision guard — **the worst possible thing to have "fixed."**

After removing it, the largest genuinely-coherent, reading-blocked, mechanism-sharing cluster
in the whole corpus is `partitive ∩ value-accounting-miss` ≈ **18 items** — and even
"value-accounting miss" is a SYMPTOM (a number reached no fact), not a shared MECHANISM.

### The verdict

Stop condition 1 of `docs/reading-gap.md`, met exactly as written:

> **The top 5 structural clusters cover < ~150 items, or fail hand-verification at 10/10.**
> → long tail. GSM8K coverage is done. Record it and move to the difg corpus.

**GSM8K coverage is DONE at 103/0 (100% precision), 40/0 dev-holdout, 91.7% TEST.** Not
failed — *converged*. Both halves of the engine are now measured and closed: the ask-shape
seam is exhausted, and the premise seam behind it is a long tail with no class big enough or
coherent enough to justify general machinery.

**The binding constraint is rule 2, NOT rule 1.** (An earlier draft of this entry said
"further coverage would require word lists and per-problem branches" — the "word lists" half
was **wrong** and is retracted. Word-specific facts in YAML packs are the *sanctioned*
architecture; rule 1 forbids them only in *Python*.) The reason coverage is closed is that
**no class is large or coherent enough to justify a rule at all** — a rule written for the
residual would be justified by a handful of items each, which is rule 2 and is difg's
`vocab_singles` sin. Where the words live is not the problem; there being no shared mechanism
is.

**The next lever is a different corpus, not a deeper one:** `docs/difg-corpus-plan.md`.

### The lesson (the third time this exact shape has appeared)

The 481 was a ceiling read as a yield. The 271 was a search artifact read as an opportunity.
**The `coordinated-qty` cluster was a precision guard read as a reading gap.** All three
survived until someone asked *"would this number also appear if my hypothesis were false?"*

> **A cluster is not a class until it predicts the missing mechanism. A regex that matches
> 200 sentences has told you about your regex.** Cluster-by-structure was necessary and was
> not sufficient — the structural clusters were still surfaces. The only thing that
> distinguishes a class from a surface is a null control.

### Finding 3 — the SECOND axis (grammatical near-miss) is a long tail too

The first write-up of this result clustered only by **decline reason**. That misses any item
whose rule dies *before* it ever reaches a decline reason — such an item scatters across
reasons while sharing one cause. Fair challenge, and a real hole. So the second axis was
measured: **does a fold die on grammatical SKELETON?** (This would be a legal, general fix —
an `opt` particle slot, a noun-modifier slot — not a word list and not a per-problem branch.)

The motivating pair, both fully-read, no unknown words:

```
Jake baked twice as many cookies as Clementine.        -> Relation (arithmetic/times-as-many)
Tom filled up 3 times as many water balloons as Luke.  -> bare Predication, number DROPPED
```

`arithmetic/times-as-many` wants `ENTITY VERB MULT 'as' 'many' PLURAL 'as' ENTITY`. `filled`
is followed by the particle `up`, so the MULT slot misses; and `item (type: plural)` hits
`water` (singular) before `balloons`. Two clean structural deaths. It looked like a class.

**It is not.** Over the 332 premise-blocked items:

| | |
|---|---|
| carrying the `as many/much … as` frame at all | 51 |
| killed by a **phrasal-verb particle** | **1** |
| killed by a **compound item noun** | 12 |
| killed by something else | 38 |

**The phrasal-verb theory was a class of ONE** — generalized from a single hand-picked
example and asserted confidently before it was counted. The `vocab_singles` sin, committed
*while writing the document warning against it.* And the 38 "something else" scatter across at
least six distinct shapes: the affine offset (`5 less than half as many`), a relative-clause
standard (`as were in Beatrice's box`), common-noun entities (`house 4 has twice as many…`),
an elided head noun (`3 times as many pink as orange balls`), `half times as many`,
`3/4 times as many`. Largest coherent structural cause in the whole pool: **12 items.**

> **Two independent axes — decline reason and grammatical skeleton — both return a long tail.**
> That is what closes GSM8K. Not "we'd need word lists" (we wouldn't, and they'd be legal);
> **there is no mechanism left that enough items share.**

**And the meta-lesson, earned twice in one session:** a structural hypothesis built from ONE
example is not a hypothesis, it is an anecdote. Count it *before* you believe it — even when
the mechanism is so clean you can see it in the YAML.

## The ask layer is a PRODUCT, and single-dimension fixes buy ZERO (2026-07-14)

**The buy-test.** All 32 remaining ask auxiliary slots widened from `type: auxiliary`
(do/does/did) to `type: future_modal` (+ will/would) — one sed, zero Python, and the category
already existed and was already live on the other 31 asks. Target: the **92** declining items
whose question carries a future auxiliary (`will he weigh`, `will they have saved`).

```
SOLVED      0        <- converts NONE of the 92
DECL->WRONG 1        <- manufactures a confident wrong (expected 490, got 500)
VERDICT: REVERT
```

**Zero coverage AND a precision loss.** Dead on rule 4 regardless of the linguistics.

**The `0 SOLVED` is the real finding: ask failures are MULTIPLY BLOCKED.** Those 92 questions
carry `will` *and something else*. The ask space is a PRODUCT:

```
{how many, how much, how long, how old, what is}                     wh-operator
  x {bare, named, common-noun, possessed, qualified, elided}          entity form
  x {simple, combined, in-all, partitive, more-than, average, ...}    aggregation
  x {do/does/did, will, has+Ven, be+Ven, not}                         TAM / voice / polarity
```

Each of the 79 ask shapes is ONE CELL. A question that misses lands outside several coordinates
at once, so **removing one blocker converts nothing — the next one is right behind it.**

> **This is why five mining batches on the ask seam netted +2.** Not bad luck, not an
> exhausted seam: **single-dimension fixes have zero marginal yield on a product space.** Two
> independent measurements now say the same thing — five batches, and this 90-second buy-test.

**The incremental path into the ask layer is CLOSED.** Do not widen another slot; do not mine
another ask cell. The only thing that dissolves a product is a COMPOSITIONAL parser that turns
it into a SUM (handle wh-operator, entity form, aggregation, and TAM once each, independently).
Half a compositional parser buys exactly what was measured above: nothing, plus a wrong.

**Caveat carried forward:** the ask layer is the layer that COMMITS. This buy-test produced a
confident wrong from a single line of YAML. Any compositional work must be a FALLBACK behind
the existing 79 asks (0 BROKE by construction) and must still argue DECL->WRONG, never BROKE
(`0 BROKE by construction is not 0 wrongs by construction`).

## THE MUTUAL BLOCK: the premise gap and the ask gap block EACH OTHER (2026-07-14)

**The experiment.** A complete compositional ask parser (`kernel/askframe.py`, branch
`experiment/compositional-ask`) — the fix the previous entry argued for. It reads a question
BY ROLE (wh-operator, measure, entity, aggregation) instead of matching it against one of 79
whole-question templates, and maps onto the SAME consumers `answer.py` already implements.
Coordinates declared once each; the product becomes a sum. Runs as a strict FALLBACK behind
the templates (0 BROKE by construction).

**It works. It is safe. It converts NOTHING.**

```
dev-train  103 / 0     dev-holdout 40 / 0     suite 52/52     pytest 998
SOLVED 0   BROKE 0   DECL->WRONG 0            VERDICT: NEUTRAL
```

### Why: the frame parses the question correctly and the FACTS AREN'T THERE

Of the declining items no template claims, the frame successfully reads 24. **All 24 then die
on the PREMISE side:**

```
How many Buicks does Jim have?         -> no quantity known for 'jim' of 'buicks'
How many dresses can Alex make?        -> no 'make' events known for 'alex'/'dress'
How many cups of lemonade did Tonya sell? -> no 'sell' events known for 'tonya'/'cup'
```

Put that beside this session's FIRST finding — *67% of the reading gap declines because no ask
shape fires* — and the law appears:

> **Fix the READING → the items die at the ASK wall.**
> **Fix the ASK → the items die at the READING gap.**
> **The two gaps are MUTUALLY BLOCKING. Neither side alone converts anything.**

This is why EVERY single-sided intervention in this campaign measured 0 SOLVED: the 481
per-unit seam, the GroupTotal consumer fix, the month/time guard, verb categorization
(`save`->`acquire`), the `future_modal` widening, and now a working compositional ask parser.
It is not a coincidence and it was never bad luck. **An item that declines is blocked on
several coordinates at once, and a fix to one coordinate leaves it declining on the next.**

To convert an item you must fix BOTH halves FOR THE SAME ITEM. A brief naming only one half
is a dead brief — which is what `evidence.premise_mechanism` in `.claude/workflows/mine.js`
was reaching for, and it is now measured rather than intuited.

### Three sharp lessons, each bought with a wrong

**1. A permissive parser must pay for its flexibility with a stricter refusal rule.**
A template that does not match simply declines: ITS RIGIDITY IS ITS SAFETY. A role-based frame
is permissive by nature, so every operator it fails to model becomes a CONFIDENT WRONG:

```
Q: "how many ounces of milk does James have LEFT?"   gold 371  -> frame answered -13.0
```

It silently dropped `left`. The fix is not a blacklist of known operators (that just
re-enumerates the product from the other side and still misses what nobody thought of) but
QUESTION ACCOUNTING: every content word must be read, or decline. This is the premise side's
value-accounting invariant, applied to the question.

**2. "Read" is not "used". A vacuously-satisfiable safety check is WORSE than none.**

```
Q: "How many pounds of vegetables did he use?"   gold 6  -> frame answered 1.0 (the BEEF)
```

The frame marked `vegetables` read, then dropped it — so pounds-of-vegetables and
pounds-of-beef collapsed to the key `pound`. Question accounting was satisfied VACUOUSLY:
touched, never used. **A safety invariant that can be satisfied without using the information
launders a guess as a checked answer.**

**3. TAM is NOT uniformly orthogonal — and only the UNIT TESTS caught it.**
The premise that motivated the whole experiment ("tense/aspect/modality say WHEN, not WHAT, so
strip them") is FALSE for one class:

```
'will' / 'would'  (future)         factually transparent: same facts, later time
'can' / 'could' / 'must' / 'may'   CHANGE THE QUESTION
```

"How many CAN he buy" is a CAPACITY question (budget ÷ unit price), not a factual one. Listing
`modal` as inert made the frame answer hypotheticals as facts, committing numbers on items the
engine had DELIBERATELY declined (the increment-14 kirsty lesson). **The dev diff said NEUTRAL
— 3,772 items saw nothing. Two synthetic unit tests caught it.** A clean DEV gate is necessary
and NEVER sufficient, demonstrated one more time.

### Disposition: NOT LANDED

0 SOLVED. **An enabler must be BOUGHT, not promised** — two increments (128, 129) passed a
clean dev gate on 0 SOLVED and shipped wrongs to TEST. This one stays on its branch. The
architecture is sound and the code is safe; it is simply not worth anything until the premise
half of the same items is fixed too, and that is the whole point of the finding above.

## ⚠ THE 100% PRECISION IS AN ARTIFACT OF GSM8K (2026-07-14)

**The claim this project rests on is that its rules are GENERAL machinery, not
benchmark-shaped solvers (constitution rule 2). That claim had never been tested against
text from a DIFFERENT SOURCE. It has now. It fails.**

ASDiv (2,305 grade-school arithmetic word problems, different authors, per-item
`solution_type`, unit-bearing golds) split DEV/TEST first (salted, stratified — TEST never
touched), then the UNMODIFIED 103-rule engine run on ASDiv-DEV, zero tuning:

```
                          correct  wrong  precision   coverage
GSM8K dev-train  (seen)       103      0     100.0%       2.7%
GSM8K TEST       (held out)    11      1      91.7%          —
ASDiv-DEV        (DIFFERENT SOURCE)  37      9      80.4%       2.2%
```

**Coverage is UNCHANGED (2.2% vs 2.7%). The rules fire at the same rate on unseen text —
they are simply WRONG 20% of the time.** This is a generalization GRADIENT: the further from
the corpus the rules were mined on, the worse precision gets. 100% → 91.7% → 80.4%.

### All 9 wrongs are genuine, and they are on TRIVIAL text

Verified by hand (ASDiv-DEV is readable; no gold-parsing artifacts):

```
"Gino has 15 brown bears, 24 white bears, and 27 black bears. How many bears?"
   gold 66     ENGINE SAID 27      <- returned the LAST conjunct
"There were 150 book shelves. Each book shelf had 15 books. How many books?"
   gold 2250   ENGINE SAID 15      <- returned the per-unit RATE
"Jerry walked nine miles on Monday and nine more on Tuesday. How many miles?"
   gold 18     ENGINE SAID 9       <- returned ONE of two identical quantities
"Maria took sixteen fish out of her tank. Now there are three fish. How many were there?"
   gold 19     ENGINE SAID 3       <- returned the remainder, not the total
"Beth has 4 packs of crayons. Each pack has 10. She also has 6 extra. How many crayons?"
   gold 46     ENGINE SAID 6       <- returned the ADDEND
```

**Every one is the same failure: the engine COMMITS A PARTIAL READING.** It extracts one
number and answers with it instead of combining. It does not decline — it confidently returns
a premise.

### The guard hole this exposes, which GSM8K could never show

**Value accounting checks NUMBERS → FACTS ("a stated number that reached no fact declines the
item"). It does NOT check FACTS → ANSWER.** A fact can be extracted perfectly and then
silently ignored by the consumer, and no guard objects. On GSM8K's phrasing the ask shapes
happen to consume everything; on ASDiv's phrasing they do not, and nothing notices.

Worse, `Jerry walked nine miles ... and nine more`: two identical `Quantity(jerry, mile, 9)`
facts DEDUPE by frozen-dataclass equality, so the second nine disappears before any guard can
see it. (`model.py`'s conjunct-index comment anticipates exactly this hazard; it is not firing
on this surface.)

> **THE GENERAL FIX, and it is the highest-value work available:** extend value accounting to
> the ANSWER. If the answering entity holds facts the consumer did not consume, the reading is
> PARTIAL and the item must DECLINE. A confident-wrong is worse than a decline (rule 4) — and
> right now the engine cannot even tell it produced one.

### What this means for the campaign

- **"103 correct / 0 wrong at 100% precision" is a statement about GSM8K, not about the
  engine.** It must never again be quoted as a precision claim without this caveat.
- The mining loop optimized precision against a corpus whose surface conventions the rules had
  already absorbed. That is the `vocab_singles` disease at the level of the RULE SET rather
  than the solver — the exact thing the constitution was written to prevent, and the gates did
  not catch it because **every gate reads from the same corpus.**
- **A cross-corpus gate is now mandatory.** ASDiv-DEV precision belongs in the ship gate
  beside dev-train, or the next 100% will be just as hollow.
- The 9 wrongs are a WORKLIST, not a disaster: each is diagnosable, and they cluster on ONE
  mechanism (partial reading), which is a general fix, not 9 patches.

## The typed-gold KERNEL change is NOT the big lever — Frontier 2 is CLOSED (2026-07-16)

**The claim under test** (`docs/difg-corpus-plan.md`, and every HANDOFF since):
"55.5% of difg answers are NON-numeric and the kernel cannot commit them
(`Answer.committed == (kind == "number")`). No commit → no score → no mining
signal for physics / logic / clock / unit_conversion. The KERNEL commit-path
change unlocks the majority of difg."

**It does not.** Measured on difg-DEV (342 items) after the corpus half of typed
gold landed (`a241f38`), by classifying every gold:

| gold kind | count | scorable today? |
|---|---|---|
| number | 145 | yes |
| quantity (+unit) | 108 | **yes** |
| money | 21 | yes |
| percent | 10 | yes |
| verdict (bare True/False) | 2 | no — needs the kernel change |
| text | 56 | no |

**284 of 342 (83%) are already scorable and NONE of them needed the kernel
change.** The plan's "55.5% non-numeric" headline counted quantity+unit (29.5%)
— but a quantity gold is a NUMBER under a formatting wrapper ("68.04 kg"), and
`_judge_typed` compares it numerically. `Answer.committed` was never its blocker.
The two halves were conflated, and the smaller half was mistaken for the lever.

**What the kernel change would actually buy: ~10 items (2.9%), and it would ship
CONFIDENT-WRONGS doing it.**

1. **2 bare verdicts.** That is the entire `verdict`-gold population of DEV.
2. **8 prose yes/no golds** — `Is 17 a prime number?` golds as **`'Yes, 17 is
   prime.'`**, a SENTENCE. Widening `committed` makes the engine commit `yes`,
   which is CORRECT, and `_judge_typed` then scores it WRONG
   (`norm('Yes, 17 is prime.') != norm('yes')`). The kernel change manufactures
   confident-wrongs out of right answers unless a prose-verdict comparator lands
   with it.
3. **The prose-verdict comparator must NOT be built either — the signal is
   degenerate.** All **8 of 8** prose yes/no golds in DEV answer **'Yes'**. There
   is not one 'No'. A comparator over that set cannot distinguish a working
   engine from one that answers 'yes' unconditionally: a stuck engine scores 8/8.
   This is [[measure-with-a-null-control]] exactly — the null (always-yes) scores
   as well as the real thing, so the measurement carries no information.
4. **The remaining 43 text items are a DIFFERENT ENGINE.** Integrals (`x**3/3`),
   Taylor series, power sets, topology closure/interior/exterior, subgroups of
   Z_6, quaternion inverses, Cantor normal form, residues, RSA keys. These are
   symbolic-algebra answers (difg produced them with SymPy). A grammar-driven
   reading engine does not have a road to them, and no rule pack makes one.

**Also measured, so it is not re-proposed:** 5 further items are money with a
trailing qualifier (`'$71.71 each'`) that the loader classifies as text. That is a
CLASSIFIER gap, not a kernel gap — and it is worth nothing today: all 5 decline at
`no ask shape` (they are compound multi-step: 17% off, then 8% tax, then split 3
ways). Fixing the classifier alone would be an unbought enabler
([[enabler-must-be-bought]]).

**Action: Frontier 2 is CLOSED. Do not widen `Answer.committed` for difg's sake.**
The corpus half (`gold: typed`) was the whole prize and it has landed. If the
kernel ever grows a non-numeric commit path, let a DIFFERENT motivation drive it —
and re-read `_judge_typed`'s in-code ⚠ first, because its "a verdict against a
non-verdict gold is a decline" rule is correct ONLY while verdicts are
non-commitments.

**The transferable lesson:** a corpus-composition headline ("55.5% is
non-numeric") is a claim about GOLD FORMATTING, not about the engine's blockers.
Classify the golds and ask "what would actually score?" before believing a
percentage names a lever. The 29.5% that made the number impressive was already
free.

## The `_TOKEN` compound-unit change is SAFE but UNBUYABLE — physics stops at 3/14 (2026-07-16)

**The plan** (HANDOFF, after physics landed at 3/14): "the next physics increment is the `_TOKEN`
change (compound units as ONE token), BOUGHT by the 6 rows it unblocks." Built it, measured it,
reverted it. The change works and is safe; there is nothing that can pay for it.

**The change itself is fine, and that is the surprising half.** Adding a compound-unit alternative to
`tokenize.py`'s `_TOKEN` (`[A-Za-z]+(?:\^\d+)?(?:[/·][A-Za-z]+(?:\^\d+)?)+`) makes "m/s", "m/s^2",
"cm^3" ONE token and kills the phantom-exponent hazard ("3 m/s^2" reading as the numbers [3, 2]).
Measured, not argued:
- **All five word-problem corpora gate byte-neutral** (GSM8K dev-train + dev-holdout, ASDiv, SVAMP,
  MAWPS, SciBench).
- It DOES fuse slashed word-pairs — "blondies/brownies", "installed/hung", "feet/minute" — into one
  unknown token, and the tokenizer **cannot** tell them from units: `tokenize()` takes no registry, so
  it cannot ask whether the parts are unit words. But **51 GSM8K-train items contain the pattern and
  ZERO of them commit** (they are the hard multi-step tail), so it changes nothing that works.

**It buys nothing, because every formula it unblocks needs a word with GSM8K TEST exposure:**

| formula | the word it needs | GSM8K TEST | verdict |
|---|---|---|---|
| `force = mass * acceleration` | 'force' | **1 item** | refuse |
| `kinetic energy = ½mv²` | 'energy' | **2 items** | refuse |
| `momentum = mass * velocity` | **'moving'** | **1 item** | refuse |
| `density = mass / volume` | — | — | **scale-blocked** |

'momentum' itself is SciBench-only and looked like the safe buyer — until the item turned out to need
'moving' ("a 4 kg object MOVING at 8 m/s"), an ordinary verb absent from the lexicon and present in 1
GSM8K TEST item. The unknown-word guard checks the whole reading, so the ask cannot route around it.

**`density` is blocked by something better than a policy — a real contradiction the SCHEMA caught.**
Its gold is "3 g/cm³" (300 g / 100 cm^3), so `mass` would have to be in GRAMS; `weight`'s gold is
"98 N" (10 kg × 9.8), so `mass` must be in KILOGRAMS. `rulekit/formulas@1` permits ONE canonical unit
per dimension, so the two cannot coexist — and the alternative (listing gram AND kilogram under `mass`)
is exactly the silent scale-mix that validator exists to stop: "the weight of a 300 g object" would
answer 2940 N instead of 2.94. A per-scale dimension would be the honest fix and is not worth 2 items.

**The trade, stated plainly:** ~4 items on a corpus that reports COVERAGE (79.3% of it is difg's own
example_queries) against lifting decline guards on 4 GSM8K TEST items, on a TEST corpus at a hard-won
92.3% that cannot be re-measured without spending a look. That is the same trade already refused for
'line' (`720c071`), 'find' and 'tan' (`4ed9956`). Refusing it again is consistency, not timidity.

**Action: physics stays at 3/14. Do not re-propose the `_TOKEN` change on its own.** The measurement
is banked — if a FUTURE increment ever has an independent reason to admit 'force'/'energy'/'moving'
(and buys that admission with a TEST look), the tokenizer change lands with it in one step and needs no
re-litigating: it is byte-neutral on all five corpora and 0/51 of the pattern's GSM8K items commit.

**The transferable lesson:** an enabler is not "safe therefore land it". `_TOKEN` passed every gate —
the reason to revert was not risk, it was that **nothing could pay for it**. A byte-neutral change with
no buyer is the infrastructure trap wearing a clean gate (`docs/negative-results.md`, "The
infrastructure trap: 0 SOLVED on DEV, a WRONG on TEST"). Measure the BUYER before building the enabler,
not after.

## Two walked levers, two collapses: start-state 177→5, elided-measure 508→8 (2026-07-16)

Walked after difg's tail thinned, looking for the next real class on the corpora
that measure PRECISION (ASDiv/SVAMP/MAWPS) rather than difg's coverage. Both
candidates looked large by surface count. Both collapsed for the SAME documented
reason. Recording the numbers so neither is re-proposed on its count.

### Start-state reconstruction ("how many did X have to begin with?")

Surface: 177 DEV items with a question-position marker (MAWPS 134, ASDiv 30,
SVAMP 13). Walked:

| | ASDiv | SVAMP | MAWPS |
|---|---|---|---|
| genuine start-state ask | 24 | 9 | 134 |
| **commits WRONG** (inversion is the LAST blocker) | **2** | **1** | **0** |
| declines (blocked on something else) | 22 | 8 | **134** |
| `if`-clause premise — NOT this class at all | 6 | 4 | 0 |

**Real yield: 5** — 3 confident-wrongs (inversion is genuinely last: the engine
folds, it just folds the wrong direction) plus 2 ASDiv declines whose premises DO
yield `Quantity + Quantity`. Ten of the 177 are not the class at all: the marker
sits in an `if`-clause PREMISE ("If she had $36 in the beginning, how much did
Andrea save?"), not in the ask.

**MAWPS's 134 convert ZERO**, and the reason is already in DEAD_CLASSES:
```
Predication      <- "Elizabeth had some cherry"
Predication      <- "Don took 74 from him"      <- the ELIDED-MEASURE event
AnchorQuantity   <- "Now Elizabeth has 74 cherry"
```
The event folds as a Predication with a string dobj, never a Quantity — clause (b)
of `equal-share-division`'s blockers. No ask can fold what was never a Quantity.

### Elided-measure events ("Don took 74 from him")

Surface: 508 (MAWPS 427, GSM8K-train 49, ASDiv 25, SVAMP 7). **Note the first
count was wrong and inflated** — a regex matching `verb + N + more` also caught
"added 2 MORE ACTION FIGURES", where the measure is PRESENT. Only `from`/`to`/
clause-end are true elision. SVAMP fell 47 -> 7 on the correction.

Walked by decline reason — `value-accounting: stated count 'N' reached no fact` is
the elision's signature (the ask fired, the fold ran, only the bare number never
became a Quantity):

| | MAWPS | GSM8K | ASDiv | SVAMP |
|---|---|---|---|---|
| **blocked BY the elision** | **2** | **2** | **2** | **2** |
| blocked at `no ask shape` TOO (mutual block) | 423 | 27 | 17 | 4 |

**Real yield: 8 of 508.** Confirmed by rewrite probe: "Sarah had 51 trucks. She
gave 13 to Jeff" declines on value-accounting and answers 38 correctly the moment
the measure is explicit — but "Cade had 87 marbles. He gave 8 to Dylan" declines
at `no ask shape` and STILL declines when made explicit. The elision is the last
blocker on the first and irrelevant on the second.

**MAWPS's 423 are not merely blocked — they are UNGRAMMATICAL template junk**:
"Now How many fig Joseph have minus?", "How many blueberry Paul have left over?",
"How many cherry Elizabeth had in the beginning?" (no `did`). ~84% of the pool is
one auto-generated template with substituted nouns ('some Beg', 'some Box'), much
of it not English. No ask will ever match it, and fitting one to it would be
measuring the generator, not reading.

### The finding

Both walks reproduce the MUTUAL BLOCK exactly as documented ("The ask layer is a
PRODUCT, and single-dimension fixes buy ZERO"; the 481-item per-unit seam). A
declining item is blocked on SEVERAL coordinates at once; fixing one leaves it on
the next. Surface counts of 177 and 508 yielded 5 and 8.

**Action:** the 3 start-state CONFIDENT-WRONGS remain worth fixing — not for
coverage, but because they are precision failures on two independent corpora and a
wrong->correct move is the metric that matters. Do NOT brief either class on its
surface count. Do NOT chase MAWPS coverage: 84% of its elided pool and 100% of its
start-state pool is one ungrammatical template.

**The transferable lesson:** this is the third large surface count this session to
collapse on contact (difg's 243-item pool into a long tail; 177 -> 5; 508 -> 8).
The walk is cheap and the brief is expensive — walk FIRST, and walk by DECLINE
REASON, which names the blocker, rather than by surface, which names only the
shape.

### Addendum: the 5 start-state items are TWO mechanisms, not one (walked by FACT STRUCTURE)

The recommendation above — "3 confident-wrongs, one class: invert the fold" — is
WRONG at the mechanism level, and only reading the FACTS showed it. Surface said
one class. Decline reason could not help: these items COMMIT, so they have no
decline reason. The fact store settles it:

```
Paco:    paco/cookie/19 (eat)   paco/cookie/35 (have)   <- SAME entity
Rachel:  rachel/apple/3 (pick)  tree/apple/4 (have)     <- DIFFERENT entities
Maria:   maria/fish/16 (take)   tank/fish/3 (have)      <- DIFFERENT entities
```

- **SAME-ENTITY INVERSION (3 items):** the asked entity holds BOTH the events and
  the anchor, so `_entity_total` already folds `anchor + Σ(signed events)` and the
  start state is `anchor − Σ(signed events)`. Paco: 35 − (−19) = 54. The 2 ASDiv
  declines whose premises yield Quantity+Quantity are also same-entity ('person',
  'rachel'), so they join THIS group, not the one they look like.
- **SOURCE-TRANSFER (2 items):** the asked entity (tree/tank) holds ONLY the
  anchor. The removal is an event on the AGENT — "Rachel picked 3 apples FROM HER
  TREE" folds as `rachel/apple/3`, and the tree never loses anything. There is
  nothing to invert. These need the source-marked transfer ("from X" / "out of X"
  debits X) — a different, larger mechanism, and NOT a start-state fix at all: the
  tree's CURRENT total is equally unread.

**The lesson, one grain finer than "a cluster is not a class":** walking by
DECLINE REASON is better than walking by surface, and still not enough for
CONFIDENT-WRONGS — a wrong answer has no decline reason to cluster on. Walk those
by FACT STRUCTURE (which entity holds what), because that is what the consumer
actually reads. Two items can share a question shape, a marker, a gold arithmetic
(a + b) and an error direction, and still be two mechanisms.

## The logic-corpus search: ProofWriter REJECTED, FOLIO wired (2026-07-16)

The task was the previous session's brief: find an independently-authored logic
corpus, since difg's own logic cannot buy Frontier 2 (8 of 8 prose yes/no golds
say 'Yes' — the always-yes null scores 8/8). All four HANDOFF checks were
MEASURED before any wiring. Do not re-derive these.

### ProofWriter / RuleTaker — REJECTED on check #3 (natural English)

`tasksource/proofwriter`, 292,776 rows, labels near-balanced (Unknown 135,774 /
True 78,501 / False 78,501 — it passes check #2 easily). It fails on the text,
and the number is not close:

```
distinct question skeletons: 1,428 of 292,776   (top skeleton 2.5%)
distinct WORD TYPES in ALL 292,776 questions: 52
vocab: is the not does bob charlie harry gary dave mouse squirrel cat bear
       bald eagle tiger cow dog nice round rabbit lion young cold blue big
       green red kind rough fiona anne erin furry quiet smart white ...
theory: "Gary is furry. Gary is nice. Gary is red. Gary is not smart."
```

A 52-word vocabulary over template-generated triples IS the MAWPS trap (84% one
auto-generated template), and it is worse: MAWPS at least had human nouns. Any
rule fitted to this measures the generator. **Size is not independence** — 292K
rows of a generator carry less information than 1K rows of human prose. LogiQA /
ReClor were not measured: the HANDOFF's prediction is structural and correct —
they are multiple-choice, so the gold is an option LABEL, not a verdict, and the
shape is wrong regardless of the text.

### FOLIO — PASSES 4/4, wired as `projects/folio/`

`tasksource/folio` (ungated mirror of Yale-LILY's FOLIO, arxiv:2209.00840;
`yale-nlp/FOLIO` itself is gated). 1,204 rows.

| check | measurement | verdict |
|---|---|---|
| 1 independent authors | Yale NLP annotators, human-written | pass |
| 2 balanced labels | True 38.8% / Uncertain 32.4% / False 28.9% → **null = 38.8%** | pass |
| 3 natural English | 1,662 skeletons / 5,286 premise sentences; top skeleton **0.2%** | pass |
| 4 verifiable golds | premises-FOL + conclusion-FOL on 100% of rows | pass, with a caveat |

**Check #4's caveat, found by testing it instead of trusting the schema:** the FOL
is human-written ANNOTATION, not an executable oracle — **3.2% of conclusion-FOL
strings do not have balanced parens** (one sample also references a free `Studen(x)`
in a bonnie-grounded formula). It is carried for AUDITING a disagreement; the gold
is FOLIO's human-verified label. "Mechanically checkable in principle" is not the
same as "runnable", and the difference would have been invisible from the dataset
card.

### Two traps this corpus set, both caught BEFORE landing

1. **'Uncertain' must NOT be a `decline` gold.** `_judge_typed` scores a declining
   engine `correct` against `gold.kind == "decline"`. FOLIO is 32% Uncertain, so
   that mapping would hand an ALWAYS-DECLINE engine ~32% of the corpus for zero
   reasoning — difg's degenerate-measurement disease, reappearing in a corpus
   picked specifically to avoid it. The null control has to be re-run on every
   design decision, not just on corpus selection. 'Uncertain' is a **text** gold,
   where a decline scores `declined`. FOLIO's 'Uncertain' is the POSITIVE claim
   "this does not follow"; failing to read a sentence is not concluding
   uncertainty, and the harness must never conflate them.
2. **The firewall bucket is the PREMISE BLOCK, not the item.** FOLIO's 1,001 train
   rows share only **340 distinct premise blocks** (mean 2.94 examples/story, one
   reused 10×). asdiv's per-item `md5(SALT + text)` would have split stories across
   the cut and **leaked 661 of 1,001 rows** — a TEST item whose premises were
   already mined in DEV. Copying the existing builder verbatim was the wrong move
   and the two-file recipe hid it; a corpus with a one-to-many story→item relation
   needs the story as the key.

## The FOLIO gate paid for itself on run #1 — and the payment arrived as a `correct` (2026-07-16)

The logic gate was wired the previous session with an explicit prediction: *"expect
0 correct / 0 wrong … the number that matters is the WRONG column. If it is >0,
that is the gate paying for itself on its first run."*

**The first run returned `1 correct / 0 wrong`.** The prediction was right that the
gate would pay immediately and wrong about the column it would pay in. The WRONG
column — the one the corpus was designed around, the one the docstring, the
project.yaml comment and the handoff all pointed at — was **0 and stayed 0**. The
bug came in as a *correct*, which on a safety gate reads like good news.

### What it was

`ask/is-membership` matches `is <name> <noun>` as a SUBSEQUENCE. On *"Is it true
that Jim is a **Knicks player**?"* the proper noun QUALIFYING the collection binds
the member slot and the real subject is dropped — `member='knicks'`, `'jim'` never
read — and the consumer answered from a `Membership(knicks, player, False)` fact
folded out of an unrelated premise. Gold was `False`. It scored **correct**.

### The null control is what convicted it, and nothing else would have

A single `correct` is indistinguishable from luck by inspection. Three probes:

| probe | before | should be |
|---|---|---|
| swap `Jim` → `Zoe` (absent from the premises) | still `no` | undetermined |
| `Jim is a Knicks player. Is it true that Jim is a Knicks player?` | **`undetermined`** | yes |
| `Mary is a student. Is Mary a student?` (the mined shape) | `yes` | yes |

**The verdict did not depend on who was asked about.** An answer invariant to its
own question is not an answer — it is a constant with a reason string. The second
row is the tell that it was not merely over-eager: the one phrasing that *should*
have answered `yes` was the one that declined.

### The lessons

1. **On a safety gate, a nonzero `correct` is exactly as suspicious as a nonzero
   `wrong`, and it is harder to act on because it looks like progress.** The
   handoff DID say "treat any nonzero correct here as suspect until the item is
   read" — that line was worth the whole session. Keep it.
2. **A guess and a capability are indistinguishable at n=1.** With a 3-label corpus
   a wrong guess had a ~61% chance of showing up as a WRONG and being obvious. It
   drew the other ~39%. The gate did not get lucky — *the bug* did.
3. **Value-accounting is numeric, so a dropped NAME is invisible to every guard we
   have.** This is the physics *"BINDABLE is not READ"* lesson in a kind with no
   digits: five arithmetic corpora sat on this silently because verdicts are not
   `Answer.committed`, so each scored it a harmless decline. Every new value kind
   a consumer BINDS needs its own read-accounting; the numeric guard does not
   generalize for free.
4. The fix guards the CONSUMER, not the ask's shape — the shape is right for the
   prose it was mined on — and closes the CLASS (any un-bound name), not the
   witness. `undetermined` still survives where nothing is unread; a decline there
   would cannibalize the epistemic square's "I don't know".

Landed: gate `f7b059c`, fix `b1db917`. folio 1/0 → **0/0**. GSM8K byte-neutral.

### Two false claims inherited from the previous handoff (both cost real time)

- **"the two files are WRITTEN and committed"** — they were UNTRACKED. A handoff's
  push claims are a memory of intent; `git status` is the fact.
- **`bench --snapshot` crashed on EVERY `gold: typed` project** (`TypedGold is not
  JSON serializable`), so the `rulekit diff` ship gate had been quietly unavailable
  for difg — the ACTIVE frontier — and for folio. Nothing announced it, because
  nothing had run it. Fixed in `d0a818e`. **A gate you have never executed is not a
  gate**; the same sentence explains why FOLIO's own bug sat unwritten until a
  bench actually ran.
- Related: `conj-train.json` is not "identical to head behavior" — it is the
  original ~14-correct baseline and reads 90 SOLVED against head. A stale baseline
  still floors 0-BROKE correctly, but its NET is noise.

## The unread-name guard was the WITNESS fix; the class was grammar (2026-07-16)

The FOLIO catch above was fixed with a consumer guard: *an unread NAME is a
decline*. It shipped with a clean 6-corpus gate, a null-control test, and a
commit message claiming it "closes the CLASS (any un-bound name), not the
witness."

**That claim was false, and the counter-example took one probe to find:**

```
Is it true that Jim is a Knicks player?         -> decline   (guard fires)
Is it true that THE PILOT is a Knicks player?   -> verdict: no    ← still committing
```

A common-noun subject has **no name to be unread**, so the guard is inert and the
engine still answered about the Knicks. Same confident answer, **one value-kind
over** — the precise shape of the failure already recorded as *fix the class, not
the witness*. Writing "this closes the class" in a commit message does not close
the class. The guard's own framing hid it: keyed on the witness's value KIND
(a name), it inherited the witness's blind spot.

### The actual defect was grammar, and the engine already knew the answer

English **fronts the auxiliary** to ask — "IS Mary a student?" (subject-auxiliary
inversion), so the subject FOLLOWS the copula. That is the *only* reason
`is <name> <noun>` reads a membership question. An **embedded declarative**
leaves the copula in place — "...that Jim is a Knicks player" — so its subject
PRECEDES it. A match sequence is contiguous but **FLOATS** (`match_all` retries at
every start offset), so the shape landed on the second construction and bound the
complement's proper-noun modifier as the member.

The engine had bound `is.subject -> jim` **correctly all along** (`u5` in the unit
dump). The ask never looked. A misreading is not always missing information — here
every fact needed to refuse was already computed and simply unconsulted.

### Lessons

1. **A guard keyed on the witness's value KIND inherits the witness's blind
   spot.** Ask what the witness is an *instance* of before choosing the level to
   fix at. The question "what else could be in this position?" would have found
   the common-noun case in one probe — cheaper than the gate, the tests and the
   commit that followed.
2. **When a shape misfires, suspect the CONSTRUCTION before the guard.** A pattern
   mined on one grammar floats onto any other containing the same token run;
   guarding downstream treats the symptom and leaves the shape wrong for the next
   consumer that reuses it.
3. **Two mechanisms, two levels, neither subsuming the other** — the ask decides
   WHICH construction it may read (`at_start`); the consumer decides whether the
   reading used everything the question said (unread-name). "Is Mary a student AT
   YALE?" still needs the second. Checking whether the earlier fix had become dead
   code is what proved they were different classes rather than one patched twice.
4. A test can be wrong in a load-bearing way: the first anchor test asserted an
   unanchored token floats inside `_try_match_at`. It does not — `_try_match_at`
   is contiguous from where it is told to start; the floating is `match_all`'s
   retry loop. The failing test corrected the mental model, which is what tests of
   a mechanism are for.

Landed `b5655ca`. All six corpora byte-neutral; pytest 1179 → 1188.

## The 7 confident-wrongs triaged: "the hard tail" was FALSE (2026-07-16)

The handoff recorded the remaining ASDiv/SVAMP wrongs as "the hard tail:
age-algebra, multi-step transfer, a '9 books about plants' parse error,
same-value/cross-holder reads". Reading all seven says otherwise: **five fall
into three real classes, two of which need no new capability at all, and one of
the seven is not winnable by anyone.** Triage cost one script.

| item | expected → got | class |
|---|---|---|
| SVAMP ×2 | 1→0, 2→0 | **self-comparison** — FIXED (`2b8430b`) |
| ASDiv "apples to begin with" | 7→4 | **start-state** |
| ASDiv "fish to start with" | 19→3 | **start-state** (same class) |
| ASDiv marbles | 17→16.5 | **transfer conservation** |
| ASDiv "9 books and 1 book" | 170→155 | conjunct dobj (known) |
| ASDiv age-algebra | 6→11 | **POISONED GOLD — unwinnable** |

### ⚠ The age item's GOLD IS WRONG — never chase it

*"London is 11 years old and Blair is 16 years old. Several years ago, Blair was
twice as old as London. How old was London then?"* — **gold 6.0**.

The age gap is invariant at 5, so `B_then = 2·L_then` with `B_then − L_then = 5`
gives `L_then = 5` (Blair 10), six years ago. **The gold answers "how many years
ago"; the text asks "how old was London then".** Six is the wrong question's
answer. Like base_conversion's coerced binary strings, a correct engine scores
WRONG here — do not count it as addressable, and do not tune toward it. (The
engine's 11 is still a guess: it ignored "several years ago" entirely and
answered London's CURRENT age, so it should decline regardless. Fixing that is
worth 0 items on this corpus and should be justified by the class, not this row.)

### The two SVAMP wrongs were ONE mechanism, and the `0.0` was the tell

Both committed exactly `0.0`, which is what prompted reading them together — but
"both end in 0" is a shared SURFACE, and a shared surface is not a shared
mechanism ([[a-cluster-is-not-a-class]]). The reason string is what proved it:
`|josh - josh| of 'marble'` on both. An EVENT comparative ("how many more did he
FIND than those he LOST") read as an ENTITY comparative. Fixed by declining
`a == b` — see the commit; the verb-vs-verb consumer stays unbuilt.

### What is left, and what it is worth

- **start-state ×2** — a KNOWN class (`d46484d` fixed a SVAMP one; the pools
  collapsed 177→5). Both commit the CURRENT state ("Now the tree has four") where
  the question asks the START. These are wrongs, not declines, so they are worth
  more than their count.
- **transfer conservation ×1** — a real invariant and the most interesting one
  left: Ben gives half his marbles to John, the giver loses **9** (half of 18) but
  the receiver gains **8.5** (half of 17 — `his` resolved to JOHN on that leg), so
  `25.5 − 9 = 16.5`. **A transfer must move ONE amount**; that both legs may
  disagree is a conservation hole no numeric guard sees, because each leg's
  arithmetic is impeccable on its own.
- **conjunct dobj ×1** — "bought 9 books about plants **and 1 book about fish**"
  reads only the first conjunct (155 = 9×15+20, dropping the fish book). The
  handoff's standing note says the first-conjunct-only binding is CLOSED for
  purchase verbs; this item says it is not closed when a PP intervenes.

### The lesson

**"Characterized" is not "measured".** Three of this session's findings were
inherited claims that failed on contact (untracked files, a stale baseline, a
crashed ship gate) — and so was this one. A worklist described as a hard tail had
a 2-item mechanical class sitting in it, fixable by one condition, worth a corpus
going to 100% precision. Re-read a tail before believing it; the read is cheap and
the description is a memory of someone else's session.

## The holder-count fraction guard: BUILT, BROKE a pinned contract, REVERTED (2026-07-16)

Chasing ASDiv's `17 → 16.5` ("Ben gave half of his marbles to John"), the root
looked like this: `_fraction_synth` sizes a fraction against `_pool_before` —
the signed sum across EVERY entity — then attributes the result to `fq.entity`
alone. With one holder those are the same number, which is why it hid. So the
guard wrote itself: **when the pool spans >1 holder it is not this entity's
pool → leave unresolved → decline.**

It worked on the witness. ASDiv went 43/5 → 43/4, GSM8K stayed byte-neutral at
104/0, all six corpora clean. **And it was wrong.** pytest failed:

```python
def test_fraction_pool_spans_entities(registry):
    # "THE eggs" is the definite pool — everyone's eggs (12 + 10)
    "Tom found 12 eggs. Mary found 10 eggs. Tom ate half of the eggs."  → 11
```

**A DEFINITE pool legitimately SPANS ENTITIES.** "Half of *the eggs*" IS half of
everyone's eggs — correct English, pinned since increment 5. Holder count was a
SYMPTOM of the witness, not the defect.

### What the defect actually was

Two constructions, one rule:

| phrasing | base | rule |
|---|---|---|
| "half of **the** eggs" | the definite pool, spans entities | `fraction-of-pool` ✓ |
| "half of **it**" | the unique pool | `fraction-of-pronoun` ✓ |
| "half of **his** marbles" | the POSSESSOR's holdings | `fraction-of-pronoun` ✗ |

`fraction-of-pronoun` was written for a pronoun that DENOTES THE POOL. A
possessive determiner senses as 'pronoun' too, so it floated onto a different
construction — **the third instance of that exact shape in one session**
(ask/is-membership's fronted auxiliary, the event-vs-entity comparative, this).
Fixed by gating the slot to a MEASURED `pool_pronoun` category (`a874887`).

### The lessons

1. **Guarding on the witness's SYMPTOM breaks the class the symptom belongs to.**
   Holder count correlated perfectly with the bug ON THE WITNESS and was causally
   irrelevant. This is [[fix-the-class-not-the-witness]] wearing a third face in
   one session: the first fix keyed on the witness's value KIND, this one on its
   incidental SHAPE. Both passed a six-corpus gate.
2. **The corpus gate cannot see a contract no corpus phrases.** All six were
   clean through the broken version — ASDiv even IMPROVED. Only the unit test,
   written by someone who had thought about "the eggs" deliberately, knew. That
   is what synthetic tests are FOR, and it is why "all gates green" is not a
   verdict on a shared-kernel change.
3. **A test's NAME can be the whole review.** `test_fraction_pool_spans_entities`
   states the contract in five words. Grepping the tests for the behavior being
   changed — before writing the guard — would have cost one command.
4. The measurement that made the real fix safe was cheap and came LATE: 78 GSM8K
   dev-train + 76 dev-holdout 'fraction of <possessive>' items ALL already
   declined, so restricting the rule could not break anything. Do that count
   FIRST — it decides guard-vs-capability before a line is written.

## Start-state: "no events means decline" is WRONG; the predicate is a narrated change (2026-07-16)

The last two start-state confident-wrongs ("Rachel picked 3 apples FROM HER TREE.
Now the tree has 4. How many did the tree have to begin with?" → 4, gold 7) had
TWO independent defects, and only fixing both stops the guessing:

1. **The base asks ignored the marker.** `ask/how-many-entity-common-noun` and
   `ask/how-many-in-place` matched those questions and answered the CURRENT state
   — the exact bug `rules/start-state.yaml` was created to fix for "in the
   beginning", one shape over. A file that fixes a bug for one shape is a
   standing invitation to check the siblings.
2. **Consuming the marker is not enough.** Inverting *nothing* returns the same
   wrong answer — which that file explicitly warned about. The tree holds no
   event (the pick folds as rachel/apple/3), so `invert_events` is a no-op.

### The guard that was tried, and why the suite rejected it

The obvious predicate — **`invert_events` and no events → decline** — passed
every corpus and broke a pinned unit test:

```python
"Tomas has 30 red grapes. Tomas has 6 green grapes.
 How many red grapes did Tomas have in the beginning?"   → 30
```

**A document that narrates NO change has start == current, so answering IS
correct.** "The question presupposes a change" is true of the *question* and not
of the *document*.

The right predicate is that an event of the same MEASURE exists on **another
entity** — a change WAS narrated and this entity's fold never received it:

| case | events on entity | same-measure events elsewhere | correct |
|---|---|---|---|
| Tomas (nothing happened) | — | — | answer 30 |
| Rachel / Maria (source transfer) | — | `picked 3 apples` | **decline** |
| Paco (own events) | `ate 19` | — | invert → 54 |

Deliberately conservative: it also declines a genuinely irrelevant foreign event
("Mary ate 2 apples" while asking Tom's start). Without source-reading the two
are indistinguishable, and 333 of 336 marker items already decline, so the
coverage cost is ~0.

### The lessons

1. **THE SECOND TIME IN ONE SESSION A GUARD PASSED ALL SIX CORPORA AND WAS
   WRONG** (the other: the holder-count fraction guard). Both were caught only by
   a unit test encoding a contract no corpus phrases. **"All gates green" is not
   a verdict on a shared-kernel change** — the corpora are a sample, the tests are
   the specification.
2. **A latent confident-wrong is worth pinning the moment you walk past it.** The
   `place_fallback_entity` branch calls `_entity_total` WITHOUT `invert_events`,
   so an in-place start-state ask binding that field would answer the fallback
   entity's CURRENT total under the start-state name. Unreachable today — which
   is exactly why a comment would not have held. `not invert` mirrors the
   superordinate fallback beside it.
3. **Measure the marker's TEST exposure before choosing which to admit.** 'to
   begin with'/'to start with' have ZERO GSM8K TEST occurrences; 'originally'
   (4), 'in the beginning' (2), 'initially' (2), 'at first' (1) do. Landing the
   two with no exposure bought both wrongs at no TEST risk — the trig 'tan'/'cos'
   discipline, applied to markers.
4. 336 marker items across six corpora, **333 already decline**. The family is
   unread, not half-read — so any new shape here can only turn a decline into a
   decline or a WRONG into a decline. That measurement is what made this a
   precision increment rather than a gamble.

## Zero confident-wrongs: what the last two ASDiv fixes actually cost (2026-07-16)

ASDiv 43/2 → **43/0**, and with it every corpus reaches zero confident-wrongs.
Both fixes are worth recording for what they were NOT.

### "conjunct dobj" was a SENSE bug, and the handoff's label sent me the wrong way

`170 → 155` was recorded as "a '9 books about plants' parse error (verb
mis-tag)" and listed under conjunct-dobj binding. The fact store:

```
Quantity(maggie, book,  9.0, verb='buy')
Quantity(maggie, book,  1.0, verb='plants')   ← 'plants' sensed as a VERB
Quantity(maggie, magazine, 10.0, verb='buy')
```

The conjunct binding is FINE. `plants` was in difg-mined as `senses: [verb]`
ALONE while `plant` already declared `plural: plants` — a **redundant second
identity shadowing the plural map**, the exact failure the 'average' invariant
names. The cascade: 'about' could not bind a verb as its object, so it reached
past 'plants' to '1 book'; 'plants' then took '1 book' as its own dobj; the fish
book landed under a verb no category tags and the purchase total dropped it.

It now DECLINES (arbitration cannot choose between the two senses). **Solving it
(170) needs arbitration to prefer a noun after a preposition — core sense
machinery, deliberately not attempted for one item.**

This is the third handoff label this session that did not survive the fact store
("transfer conservation", "the hard tail", this). **A label is a compressed
memory of a diagnosis; dump the facts.**

### The relation guard: the naive version would have broken SIX correct items

"London is 11 and Blair is 16. Several years ago, Blair was twice as old as
London" committed 11. A Relation over-determined by two stated states is DROPPED
by saturate ("only an existing STATE for the subject blocks resolution") — right
for a consistent restatement, silent for a contradiction (16 ≠ 2×11).

The obvious guard — *violated over-determined relation → decline* — was measured
BEFORE being written, and the measurement killed two versions of it:

| guard version | correct items it would break |
|---|---|
| violated relation | **6** — the "in 5 years, X will be 4× as old as Y" family is violated at t=0 BY DESIGN |
| + same-time only | **2** — three jars bare-fold to lemma 'jar', so bare-lemma comparison reads them as ONE entity |
| + label-keyed | **0** — exactly 1 item in five corpora: the wrong |

Both conditions are pinned as tests. **The labeled-entity trap caught my
MEASUREMENT SCRIPT before it could catch the guard** — the same bare-lemma error
the `distinct: [who, std]` comment documents, now three-for-three this session.

### The lesson

**Measure the guard's false positives before writing it, not after.** Both
versions above would have passed a naive review and been caught only by the dev
gate — or, for the offsets, possibly not at all if the family had been slightly
smaller. The script that finds them is the same one that sizes the class, so it
costs nothing extra: enumerate every item the guard WOULD fire on, and read their
current outcomes. A guard is a claim about a class; the class is countable.

## FOLIO Phase 1 (verdict commitment + phrase-keyed syllogisms): REVERTED at folio TEST look #1 (2026-07-16)

The full increment — `Answer.committed` admitting verdict yes/no, both judge flips,
per-kind guards (supported-fragment), `packs/logic` (span-capture phrase-keyed
extraction, Horn instantiation/chaining, embedded-declarative asks, is-membership
moved in) — passed EVERYTHING: folio dev-train diff SOLVED 1 / 0 BROKE / 0
DECL→WRONG across 919 DEV items, null controls proving the one solve was a real
derivation (the answer moved with both subject and predicate), pytest 1231, all six
cross-corpus gates clean, gsm8k byte-neutral by pack-scoping proof + measurement.

**folio TEST look #1: 0 correct / 1 WRONG → revert** (`88f6382` reverted by its
successor). The failing shape exists only in TEST's distribution — the §3a case the
look exists to catch, and the reason the look is spent BEFORE trusting an increment.
DEV showed zero wrongs, so the culprit cannot be diagnosed from DEV; TEST is
aggregate-only and stays that way.

What re-landing must do differently (narrow first, one look per piece):
1. **Drop the verbal-universal rules** — a known-verb participle missplits the
   cls/pred boundary ("All students TRAINED by Yale are…" → v='trained'), the
   likeliest unsound reader of the lot.
2. **Drop "All X are not Y"** — read as ∀¬ on one Phase 0a gold, but the English is
   genuinely ambiguous (¬∀ vs ∀¬) and FOLIO annotators decide per item; one
   mis-scoped item is exactly one TEST wrong.
3. **Drop ground-verbal** (widest ground rule; the 'be'-twin redundancy came from it).
4. Keep: copular universals (all/every/no), copular grounds ± not, instantiation +
   chain synths, the embedded copular asks. The Robert-Zimmer-class item this bought
   used ONLY these.
5. The kernel half (committed/judges/guards/span machinery) was NOT shown unsound —
   but it is unbuyable without rules, so it re-lands WITH the narrowed pack, one
   revertible commit, one fresh look.

Also banked from the increment (all still true, re-derivable from `88f6382`):
'true' must be an ADJECTIVE (noun sense makes ask/is-membership parse the wrapper
itself — an answer invariant to its own question); the generic SVO fold drops
qualifiers and mints junk from passives, so a verdict consumer may only read
phrase-keyed logic facts; the clause pre-split erases its boundary word (any split
story must veto verdicts); a bound quantifier is attached, not understood; moving
is-membership out of arithmetic costs the 4 curated membership suite items (they
must move to pytest under a logic registry — suite 52→48 while the move holds).

## FOLIO Phase 1 v2 (COPULAR-ONLY): ALSO REVERTED — TEST look #2 was again 0 correct / 1 WRONG (2026-07-17)

The narrowed re-landing (verbal universals, "All X are not Y", ground-verbal and the
verbal asks all dropped) still scored 0/1 on folio TEST. **The culprit commits through
the copular-only surface**: copular universals (all/every/no × is/are), copular
grounds (± not), instantiation/chain, the embedded copular asks, or the Atom fallback
in membership-verdict. v2 survives in `bbfc03c` (reverted by its successor).

**The real lesson is the BUYER, not the rule set.** DEV coverage was 1/494 (0.2%), so
TEST's expected commit count is ~1 — the two looks were coin flips on n≈1, and both
came up wrong. Two looks are now spent for zero information about WHICH rule is
unsound. DO NOT re-land a third thin variant: the next landing must first widen the
buyer on DEV (the 'citizens' plural-head family + more syllogism morphology — enough
for ~10-30 DEV commits, all null-controlled) so a TEST look measures a CLASS, not a
coin. Candidate unsoundness to probe on DEV first, cheapest first:
1. **Tense collapse**: ground-copular-was emits the same Atom as -is, and the was/is
   asks query one pred — a "was a Y" premise answers an "is a Y" conclusion. FOLIO
   annotators may treat those as distinct predicates. Key the atom (or gate the ask)
   on tense and measure what DEV loses.
2. The membership-verdict Atom fallback (added when logic rules stole the fold's
   copular facts) — drop it; nothing on DEV needs it.
3. Indefinite conclusion subjects ("A Czech published...") binding as names.
4. Chain/instantiation polarity interactions with 'no' universals.
