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
