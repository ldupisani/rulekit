# Parked campaign: difg/SciBench physics formula coverage

**Status:** PARKED on 2026-07-20 at `main` commit `5b9d62c`.

This is the re-entry guide for the physics-formula campaign developed in
Sessions 9–17 of [`HANDOFF.md`](HANDOFF.md). It records the state needed to
resume without rereading the full session history. Project-wide rules and gate
discipline remain authoritative in [`../CLAUDE.md`](../CLAUDE.md); they are not
duplicated here.

## Resume in 60 seconds

1. Confirm `main` contains `5b9d62c` or a descendant and the worktree is clean.
2. Read this file, then the newest entries in [`HANDOFF.md`](HANDOFF.md).
3. Inspect the current formula data in
   [`../packs/difg-mined/formulas.yaml`](../packs/difg-mined/formulas.yaml).
4. Take fresh snapshots of every DEV gate before editing.
5. Treat the next candidate below as a survey target, not a pre-approved build.

## Parked baseline

The last shipped increment added direct translational kinetic energy. The
working tree was clean and synchronized with `origin/main`.

| Gate | Parked result |
|---|---:|
| difg DEV | 75 correct / 0 wrong / 267 declined |
| GSM8K dev-train | 104 / 0 / 3668 |
| GSM8K dev-holdout | 40 / 0 / 3661 |
| ASDiv DEV | 44 / 0 / 1626 |
| SVAMP DEV | 30 / 0 / 724 |
| MAWPS DEV | 9 / 0 / 1998 |
| SciBench DEV | 6 / 0 / 518 |
| FOLIO DEV | 0 / 0 / 919 |
| Curated suite | 65 / 65 in two fresh processes |
| Unit tests | 1953 passed |
| Lint | 0 errors; 2 existing warnings |

Aggregate-only TEST fingerprints at parking time:

- difg: **15 correct / 0 wrong / 92 declined**
- GSM8K: **13 correct / 1 persistent wrong / 1305 declined**
- SciBench: **0 correct / 0 wrong / 168 declined**

The difg DEV count includes a duplicated direct kinetic-energy row. Bench
counts both copies, while snapshots use the same question-derived ID for both;
therefore Session 17 moved the aggregate 73 → 75 but `rulekit diff` reported
one solved ID (`8b9b4219aeb7`). Do not confuse that pre-existing bookkeeping
quirk with nondeterminism.

## What landed

The current generic physics consumer supports exact named-quantity formulas,
unit-dimension operand binding, scale conversion, and explicit question versus
document scope. Current formula keys are:

- `speed`, `weight`, `voltage`
- `entropy change`
- `de broglie wavelength`
- `initial speed`, `frequency`, `maximum wavelength`
- `power`
- `gravitational potential energy`
- `momentum`
- `kinetic energy` for a directly stated velocity

Campaign commits, in landing order:

| Commit | Increment |
|---|---|
| `b57f562` | conservative LaTeX reader + entropy-change buyers |
| `cf539f5` | eponymic quantity grammar + de Broglie wavelength |
| `09a72ab` | formula-level document scope + projectile initial speed |
| `118d7b0` | premise-scoped photon frequency |
| `3c7ef3a` | Wien maximum wavelength |
| `a2e04ec` | document-scoped power + partitive noun arbitration |
| `96f07f9` | full qualified keys + gravitational potential energy |
| `a3b421f` | compound-unit tokens + momentum |
| `5b9d62c` | direct translational kinetic energy |

## Invariants that made the campaign safe

- Formula selection uses the **complete qualified quantity key**. Kinetic,
  gravitational potential, bare, rotational, and relativistic energy must not
  collapse to one key.
- Operands bind by the **dimension of their own unit**, never by number order.
- Each dimension has exactly **one canonical unit**. Other scales reach it only
  through declared conversion data; otherwise the answer declines.
- The physics consumer owns whole-list accounting. Every stated count,
  multiplier, or fraction is read by the selected expression or the answer
  declines. Duplicate values for one dimension also decline, even when equal.
- Document operands are available only when the selected formula declares
  `scope: document`.
- Compound typography (`m/s`, `m/s^2`, `cm^3`) is preserved structurally, but a
  symbol is semantic only when pack data gives it a canonical unit.
- SciBench uses typed gold with 1% relative tolerance. Preflight every reachable
  sibling against its rounded gold before naming it as a buyer.
- Vocabulary admission removes an unknown-word decline guard. Collision-grep
  all corpora and spend relevant aggregate-only TEST looks.

## Best next survey: guarded formula alternatives

The remaining classical kinetic-energy row states mass, distance, and time,
not velocity. Its physical expression is:

```text
0.5 * mass * (distance / time)**2
```

This is **not** another formula-line increment. Two independent blockers remain:

1. `rulekit/formulas@1` and the registry currently map one quantity to one
   expression/scope. A second different definition for `kinetic energy` is a
   compile error.
2. The row uses the symbol `s`. That surface already has an exact `possessive`
   lexicon entry. Adding `s` as a plural alias of `seconds` changes its lemma but
   does not replace the exact entry's sense, so the naive alias does not create
   a noun unit. The solution must disambiguate a unit symbol structurally after
   a number or introduce explicit unit-symbol data; do not globally turn `s`
   into a noun.

If the survey finds enough buyers to justify the mechanism, formula alternatives
should satisfy all of these conditions:

- choose an alternative only when exactly one referenced-dimension set is fully
  and unambiguously supplied;
- decline when two alternatives are simultaneously satisfiable;
- account and log only values referenced by the selected expression;
- retain duplicate-dimension and unread-value declines;
- keep scope explicit per alternative;
- reject duplicate operand signatures at compile time;
- add no quantity- or unit-specific branch to Python.

Before building, inventory other quantities that genuinely need alternative
operand sets. One remaining duplicate corpus row alone may not pay for a schema
and consumer expansion.

## Known parked or rejected paths

- **Force:** still needs vocabulary admission and an acceleration dimension.
  Coulomb-force siblings have contradictory answer scaling after corpus
  extraction, so “force” is not one clean formula class.
- **Density:** gram/cubic-centimetre buyers conflict with the one-canonical-unit
  scale contract already used by kilogram-based formulas.
- **Relativistic kinetic energy:** has a different formula and an unrecognized
  ask shape; it must not borrow the translational formula.
- **Repeated-dimension formulas:** Coulomb charge pairs, double-slit distances,
  and similar classes need role-aware/repeated operands and retain separately
  recorded gold or language blockers.
- **Text answers:** still require a separately scoped kernel + judge answer kind.
  Do not mix that frontier into formula alternatives.

Historical measurements and rejected implementations live in
[`negative-results.md`](negative-results.md), especially the compound-unit,
repeated-dimension, Coulomb, Carnot, and text-answer findings.

## Gate recipe when resuming

Use `UV_CACHE_DIR=/tmp/rulekit-uv-cache` in the managed workspace if uv cannot
write its default cache.

1. Snapshot before and after on difg DEV, both GSM8K DEV slices, ASDiv, SVAMP,
   MAWPS, SciBench, and FOLIO.
2. Require every diff to show `BROKE 0` and `DECL->WRONG 0`.
3. Add synthetic mechanism tests; never copy a corpus question into tests.
4. Run curated through `projects/curated` twice in fresh processes.
5. Run project lint and the complete pytest suite.
6. Spend TEST looks only after the DEV gate is clean, and only for corpora the
   increment can materially reach. Any new wrong reverts the increment.

## Primary implementation files

- [`../packs/difg-mined/formulas.yaml`](../packs/difg-mined/formulas.yaml)
- [`../packs/difg-mined/rules/physics.yaml`](../packs/difg-mined/rules/physics.yaml)
- [`../packs/difg-mined/categories/physics.yaml`](../packs/difg-mined/categories/physics.yaml)
- [`../packs/difg-mined/lexicon/physics-ops.yaml`](../packs/difg-mined/lexicon/physics-ops.yaml)
- [`../src/rulekit/data/schemas.py`](../src/rulekit/data/schemas.py)
- [`../src/rulekit/data/registry.py`](../src/rulekit/data/registry.py)
- [`../src/rulekit/kernel/consumers/physics.py`](../src/rulekit/kernel/consumers/physics.py)
- [`../src/rulekit/kernel/senses.py`](../src/rulekit/kernel/senses.py)
- [`../tests/test_physics.py`](../tests/test_physics.py)
