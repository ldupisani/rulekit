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
