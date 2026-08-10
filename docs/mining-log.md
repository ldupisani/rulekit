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
protected TEST/generalization look was spent.
