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
