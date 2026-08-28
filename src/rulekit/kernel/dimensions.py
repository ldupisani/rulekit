"""Shared dimensional algebra: unit conversion and dimension binding.

The ONE home of the conversion primitives that previously lived as separate,
drifting copies across `totals.py`, `learn.py`, `measurement_reading.py`, and
`consumers/physics.py`. This is the extraction increment: every function was
moved byte-for-byte from its original site (the only mechanical edit is
`ctx.reg` becoming a plain `reg` parameter), and each original site now
delegates here. The full eight-slice gate pins the move.

The contract this module owns, so no caller re-derives it:

- **Conversion factors are DATA.** `rulekit/conversions@1` pairs, stored both
  directions by the registry build; `rulekit/affine-conversions@1` for scales
  with a zero point of their own. No unit, scale, or factor is named here
  (constitution rule 1) — an unknown pair returns None and the caller
  declines rather than guessing.
- **Binding is by the DIMENSION OF A VALUE'S OWN UNIT, never by position.**
  `bind_count_to_dimension` is the general form of the discipline the physics
  consumer proved: direct `unit_dimension` hits, then scale-to-canonical
  through the declared tables, then ambiguity refusal.
- **Substance bridges are not transitive edges.** The ordinary table holds
  homographs (mass `ounce`, fluid `ounce`); treating it as one graph would
  connect every mass to every volume through the shared word. Each candidate
  uses one scoped bridge row and at most one direct ordinary edge on either
  side. Multiple complete candidates are accepted only when their factors
  agree; longer paths need an explicit scoped row rather than a guess.

The import direction is one-way BY DESIGN: this module imports only the data
layer (`Registry`) and nothing in the kernel above it — `totals.py` sits
above it, `learn.py` beside it, consumers above both.
"""

from __future__ import annotations

from ..data.registry import Registry


def conversion_factor(reg: Registry, from_unit: str, to_unit: str) -> float | None:
    """A MULTI-HOP factor from_unit -> to_unit over the `reg.conversions`
    graph (BFS; the table itself is small — a handful of declared pairs, both
    directions already stored by the registry build). Handles chains
    reg.conversions never states directly ("yard" -> "foot" -> "inch": the
    pack declares yard/foot and foot/inch, never yard/inch) without inventing
    a second conversions table. Returns None when NO declared path connects
    the two units at all (e.g. 'dog' has no relationship to 'inch') — the
    caller's signal that the units are simply unrelated, not that a
    conversion is missing.

    (mining candidate dimension-difference-asks; moved byte-for-byte from
    `totals.py`, which keeps the `_conversion_factor` alias for its existing
    callers.)"""
    if from_unit == to_unit:
        return 1.0
    seen = {from_unit}
    frontier = [(from_unit, 1.0)]
    while frontier:
        next_frontier = []
        for unit, factor in frontier:
            for (a, b), f in reg.conversions.items():
                if a == unit and b not in seen:
                    total = factor * f
                    if b == to_unit:
                        return total
                    seen.add(b)
                    next_frontier.append((b, total))
        frontier = next_frontier
    return None


def substance_conversion_factor(
    reg: Registry,
    substance: str,
    source: str,
    target: str,
) -> float | None:
    """Compose one substance bridge with direct same-dimension unit edges.

    The ordinary conversion table contains homographs such as mass ``ounce``
    and fluid ``ounce``. Treating that table as one transitive graph would
    accidentally connect every mass to every volume through the shared word.
    Each candidate therefore permits one scoped bridge row and at most one
    direct ordinary edge on either side. Multiple complete candidates are
    accepted only when their factors agree. Longer paths need an explicit
    scoped row rather than a guess.

    (Moved byte-for-byte from `consumers/measurement_reading.py`, with
    `ctx.reg` becoming the plain `reg` parameter; that module delegates.)"""

    if source == target:
        return 1.0
    candidates: list[float] = []
    for (owner, bridge_from, bridge_to), bridge_factor in (
        reg.substance_conversions.items()
    ):
        if owner != substance:
            continue
        before = (
            1.0
            if source == bridge_from
            else reg.conversions.get((source, bridge_from))
        )
        after = (
            1.0
            if target == bridge_to
            else reg.conversions.get((bridge_to, target))
        )
        if before is not None and after is not None:
            candidates.append(before * bridge_factor * after)
    if not candidates or any(
        abs(candidate - candidates[0]) > 1e-9 for candidate in candidates[1:]
    ):
        return None
    return candidates[0]


def is_measure_unit(reg: Registry, lemma: str) -> bool:
    """A lemma naming a KNOWN physical measure unit — one side of a
    `reg.conversions` pair (pound, gallon, ounce, ...; both directions are
    stored, so membership on either side is enough). Data-driven — never a
    Python word list; a made-up container noun ('box', 'bag') is never a
    member. (Moved byte-for-byte from `learn.py`'s `_is_measure_unit`, which
    keeps its Unit-shaped wrapper.)"""
    return any(lemma in pair for pair in reg.conversions)


def canonical_units(reg: Registry, read_names: set[str]) -> dict[str, str]:
    """The canonical unit of every READ dimension — dimension name -> its
    declared canonical unit, restricted to dimensions the expression actually
    references (`read_names`). (Extracted from `consumers/physics.py`.)"""
    return {
        d: unit
        for unit, d in reg.unit_dimension.items()
        if d in read_names
    }


def bind_count_to_dimension(
    reg: Registry,
    *,
    value: float,
    lemma: str | None,
    qualifier: str | None,
    label: str | None,
    read_names: set[str],
) -> tuple[str, float] | None:
    """Bind ONE stated count to a formula dimension by the DIMENSION OF ITS
    OWN UNIT, scaled to the canonical unit of that dimension. Returns
    `(dimension, value)` on a unique binding and None otherwise — the
    caller's signal to decline (an unread count is a decline, never a guess).

    Resolution order (moved byte-for-byte from `consumers/physics.py`'s bind
    loop; that consumer keeps the accounting around it):

    1. **Direct hit.** The counted unit's LEMMA ("100 meters" -> 'meter'),
       or its QUALIFIER when the noun itself is not a unit ("a 2 kg object"
       -> lemma 'object', qualifier 'kilogram'), names a dimension the
       formula references — the value binds unscaled.
    2. **Scale-to-canonical.** A stated unit that is not a dimension's
       canonical unit can still REACH one through the conversion tables —
       "25 kJ" reaches 'joule' by linear factor, "100 degrees C" reaches
       'kelvin' by the affine pair keyed on the merged LABEL. Both lookups
       are pure data (conversions@1 / affine-conversions@1); no unit, scale
       or factor is named here.
    3. **Ambiguity refuses.** A word or label that reaches the canonical
       units of TWO read dimensions is ambiguous and binds nothing — None,
       the safe outcome, exactly as for an unknown unit. Zero reachables is
       None too.
    """
    for word in (lemma, qualifier):
        d = reg.unit_dimension.get(word or "")
        # A dimension the FORMULA does not reference is not a reading of
        # this value — it is a quantity the answer would ignore. Treating
        # it as unbound routes it to the caller's decline, which is the whole
        # point: bindable != read.
        if d is not None and d in read_names:
            return d, value
    canon_units = canonical_units(reg, read_names)
    reachable: list[tuple[str, float]] = []
    for word in (lemma, qualifier):
        if not word:
            continue
        for d, canon in sorted(canon_units.items()):
            factor = reg.conversions.get((word, canon))
            if factor is not None:
                reachable.append((d, value * factor))
    if label:
        for d, canon in sorted(canon_units.items()):
            pair = reg.affine_scales.get((label.lower(), canon))
            if pair is not None:
                offset, factor = pair
                reachable.append((d, (value + offset) * factor))
    if len(reachable) == 1:
        return reachable[0]
    return None
