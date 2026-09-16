# Mining log — the per-increment record

This is the append-only narrative of shipped mining increments: one record per increment, in the
established style (class, mechanism, files, gate numbers, TEST look). The `/mine` integrator appends
here at finalization (`.claude/agents/mining-integrator.md` step 4).

**This file is a LOG, not an entry point.** It grows without bound by design. Nothing reads it to
learn the project's state:

- **Current state, frontiers, and invariants → `docs/HANDOFF.md`** (hand-curated, kept short).
- **Measured negatives → `docs/negative-results.md`.**
- **The GSM8K campaign, increments 10–128 → `docs/HANDOFF-archive-2026-07-16.md`**, the frozen
  original handoff. That log ran to 6,107 lines because it lived in HANDOFF.md itself; it was split
  out on 2026-07-16 so the entry point could stay readable.

If a record here turns out to carry a lesson that generalizes — an invariant, a blast radius, a
measured negative — **promote it** to HANDOFF.md or negative-results.md. A lesson that lives only in
this file will not be read again. (Prose does not enforce: the promotion is the point of the split.)

Every record names its commit, so `git show <sha>` is usually the faster route.

---

<!-- new increment records are appended below, newest last -->

## Increment 129 (2026-08-08) — Mining v2 no-op pipeline smoke

The exact human-approved and machine-passed candidate `smoke-noop-v2`
(`09b8edeb2d8b5b37184c28927adc82ede1299a6b`) lands one explanatory YAML
comment with no compiled-rule change. Its synthetic pin records the existing
scoped-total answerable neighbour and safe-decline boundary.

The integration gate passes 4,723 tests. All thirteen standing DEV diffs are
neutral, curated remains 71/71, lint reports zero errors and warnings, FOLIO
makes zero numeric commitments, and the content-blind protected digest is
unchanged. No protected TEST/generalization look was spent.

## Increment 130 (2026-08-09) — Role-licensed temporal-point event totals

The exact human-approved and machine-passed product candidate
`postverbal-temporal-event-totals`
(`014040841d7323a9a7ac4dd4b741f759908cad57`) preserves one uniquely
role-licensed trailing calendar point on an event quantity. Exact-period asks
select that point, same-verb non-state events may sum across explicit periods,
and mixed, cross-verb, unresolved, or state-snapshot neighbours decline. The
18 unambiguous calendar points move to core-English while modal `may` remains
outside the class.

The integration gate passes 4,749 tests. All thirteen standing DEV diffs are
neutral, curated remains 71/71, lint reports zero errors and warnings, FOLIO
makes zero numeric commitments, all four canonical specimens replay exactly,
and the content-blind protected digest is unchanged. No protected
TEST/generalization look was spent.

## Increment 131 (2026-08-10) — Unit-normalized task-completion duration gaps

The exact human-approved and machine-passed candidate
`unit-normalized-task-completion-duration-gap`
(`7c07d762acb617dad143520624a29c0c34046d29`) records typed completion
durations, normalizes compatible units, and answers an exact faster/slower
gap only when task identity, participants, direction, and evidence agree.
Ambiguous, incompatible, equal-duration, and contradictory neighbours decline.

The integration gate passes 4,836 tests. GSM8K DEV-train gains one correct
answer with zero breaks or new wrong commitments; the other twelve standing
DEV diffs are neutral. Curated remains 71/71, lint reports zero errors and
warnings, FOLIO makes zero numeric commitments, all four canonical specimens
replay exactly, and the content-blind protected digest is unchanged. No
protected generalization look was spent. Protected GSM8K TEST look 125 holds
the previous aggregate exactly at 13 correct, 1 wrong, 1,305 declined, and
92.9% precision; fully-read coverage moves from 385 to 386 without a new
commitment.

## Increment 132 (2026-08-11) — Anaphoric distance chains and combined totals

The exact human-approved and machine-passed candidate
`anaphoric-distance-chain-combined-total`
(`d297627542d9bda6aa3ede0d5b9f7e9c128863df`) adds a distance-specific
motion multiplier whose antecedent is selected only from one compatible
motion-distance quantity. A following measured distance offset can then feed
the existing exact named-holder combined total. Incompatible count, duration,
currency, year, and state-length quantities are ignored; multiple compatible
antecedents decline rather than using recency.

The integration gate passes 4,975 tests. GSM8K DEV-train gains one correct
answer with zero breaks or new wrong commitments; the other twelve standing
DEV diffs are neutral. Curated remains 71/71, lint reports zero errors and
warnings, FOLIO makes zero numeric commitments, and all four canonical
specimens replay exactly. No other protected generalization look was spent.
Protected GSM8K TEST look 126 holds the previous aggregate exactly at 13
correct, 1 wrong, 1,305 declined, and 92.9% precision; fully-read coverage
moves from 386 to 389 without a new commitment.

## Increment 133 (2026-08-17) — Refrigerated interior quantity locations

The exact human-approved and machine-passed candidate
`refrigerated-interior-quantity-location`
(`61cf33244f46c1664d4eb779e994f0de4ad11d0f`) admits the bounded
`fridge`/`fridges` noun family and classifies its singular lemma as an interior
quantity location. Existing quantity facts, event folding, asks, and consumers
remain unchanged; incomplete location evidence still declines.

The integration gate passes 5,620 tests. GSM8K DEV-train gains one correct
answer with zero breaks or new wrong commitments; the other twelve standing
DEV diffs are neutral. Curated remains 71/71, lint reports zero errors and
warnings, FOLIO makes zero numeric commitments, all four canonical specimens
replay exactly, and the content-blind protected digest is unchanged. No
protected TEST/generalization look was spent.

## Increment 134 (2026-09-16) — Shared participant and item-reference identity

The exact human-approved and machine-passed product candidate
`shared-reference-identity`
(`dc086bde3fbb4d6ce410d6445ce1259a59ab0cf9`) preserves recursive ownership,
labels, and intersecting qualifiers across quantities, comparisons, asks, and
totals. Explicit comparison-backed forward item references retain their
participant, activity, and provenance scope. Ambiguous identities, rival
classes, incomplete amounts, and unsupported subtype inferences decline.
This product increment claims no benchmark yield or vocabulary admission.

The DEV-only integration passes 7,798 tests, with seven existing optional
corpus-data skips under the same isolated setup as its fresh baseline. The
exact DEV corpus-prose guard passes separately. All thirteen standing DEV
diffs are neutral, including unchanged correct answers and projected graphs;
curated remains 71/71 and FOLIO makes zero numeric commitments. Both lints
have zero errors, with the existing GSM8K trig-alternation warning unchanged.
All 32 frozen canonical specimens and both saved review traces replay exactly;
both positive review contracts are machine-reconfirmed without changing the
review ledger. Runtime files remain byte-identical to the reviewed candidate,
and protected-file digests are unchanged. The reading tests are retained as
`tests/test_mining_increment_134.py`.
