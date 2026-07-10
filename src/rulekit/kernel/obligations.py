"""Obligation attachment, sense disambiguation by coverage, and binding.

THE CORE PRINCIPLE: every word's role places a demand on the rest of the
sentence; parsing is the discharge of those demands. An obligation binds iff
exactly one candidate satisfies it (definitive-or-decline); what stays unmet
is the deficiency report. Sense ambiguity is resolved by trying each
assignment on a throwaway copy and keeping the unique best-covering one.
"""

from __future__ import annotations

import copy
import itertools

from ..data.registry import Registry
from .model import Obligation, Reading, Unit

# Which sense classes can satisfy each need. Structural knowledge (what KIND
# of word fills a slot), deliberately small and fixed — the per-word facts
# live in the packs.
NEED_CANDIDATES: dict[str, frozenset[str]] = {
    "collection": frozenset({"noun", "pronoun"}),
    "subject": frozenset({"noun", "name", "pronoun"}),
    "dobj": frozenset({"noun", "name", "pronoun", "value"}),
    "object": frozenset({"noun", "name", "pronoun", "value"}),
    "anchor": frozenset({"noun", "name", "value", "verb"}),
    "quantifies": frozenset({"noun"}),
    "negates": frozenset({"verb"}),
    "standard": frozenset({"noun", "name", "value"}),
    "modifies": frozenset({"noun"}),
    "scales": frozenset({"noun", "value"}),
    # "refers" is deliberately ABSENT: a pronoun's antecedent is bound by the
    # DOCUMENT loop against prior sentences, never within its own sentence
    # (a same-sentence noun is an object, not an antecedent)
    "left": frozenset({"value"}),
    "right": frozenset({"value"}),
}

MAX_AMBIGUOUS_UNITS = 4  # cartesian-trial cap; beyond this, decline as ambiguous


def _unit_sense_class(unit: Unit) -> str | None:
    """The sense class a unit presents as a binding candidate."""
    sense = unit.sense()
    if sense in ("value", "multiplier", "fraction"):
        return "value"
    return sense


def _conjoined_sibling(reading: Reading, unit: Unit) -> Unit | None:
    """The other name in an '<name> and <name>' pair containing `unit`."""
    units = reading.units
    try:
        i = units.index(unit)
    except ValueError:
        return None
    if (
        i + 2 < len(units)
        and units[i + 1].sense() == "conjunction"
        and units[i + 2].sense() == "name"
    ):
        return units[i + 2]
    if (
        i - 2 >= 0
        and units[i - 1].sense() == "conjunction"
        and units[i - 2].sense() == "name"
    ):
        return units[i - 2]
    return None


def attach_obligations(reading: Reading, reg: Registry) -> Reading:
    for unit in reading.units:
        sense = unit.sense()
        if sense is None:
            continue
        role = reg.role_obligations.get(sense)
        if role is None:
            continue
        obligations = [
            Obligation(role=sense, need=need, optional=need in role.optional)
            for need in role.needs
        ]
        reading.record(
            "attach-obligations", unit,
            {"obligations": obligations},
            f"role {sense!r} demands {role.needs}",
        )
    return reading


def _candidates(reading: Reading, holder: Unit, ob: Obligation, reg: Registry) -> list[Unit]:
    wanted = NEED_CANDIDATES.get(ob.need, frozenset())
    role = reg.role_obligations.get(ob.role)
    direction = role.direction.get(ob.need, "either") if role else "either"

    # `quantifies` is strictly LOCAL: a count quantifies the noun it can
    # reach crossing only nominal material (articles, adjectives, punct-free
    # nouns). Any other sense in between ("5 LESS THAN half as many coconut
    # trees") means the value does NOT count that noun — leave it unmet and
    # let the deficiency/guard machinery decline, never mis-bind.
    if ob.need == "quantifies":
        idx = reading.units.index(holder)
        for unit in reading.units[idx + 1 :]:
            sense = unit.sense()
            if sense in ("article", "adjective"):
                continue
            if sense == "noun":
                return [unit]
            return []
        return []
    out = []
    for unit in reading.units:
        if unit.uid == holder.uid:
            continue
        if _unit_sense_class(unit) not in wanted:
            continue
        if direction == "left" and unit.span[0] > holder.span[0]:
            continue
        if direction == "right" and unit.span[0] < holder.span[0]:
            continue
        out.append(unit)
    # A conjoined name ("Frankie AND Carla played…") is not a lone subject —
    # the subject is the GROUP. Keep both conjuncts in play and FORBID
    # adjacency from arbitrating between them: the binding stays non-unique
    # (unmet) rather than attributing the fact to the nearer name.
    if ob.need == "subject":
        for candidate in list(out):
            sibling = _conjoined_sibling(reading, candidate)
            if sibling is not None:
                if sibling not in out:
                    out.append(sibling)
                return out
    # A bare value competes for an argument slot only when nothing nominal
    # does ("Tom ate 3" is elliptical; "Tom ate 3 apples" condensed anyway).
    if ob.need in ("dobj", "object", "standard"):
        nominal = [u for u in out if _unit_sense_class(u) != "value"]
        if nominal:
            out = nominal
    if len(out) > 1:
        # Adjacency arbitration: the nearest candidate wins ONLY if strictly
        # nearer than all others; equal distance stays ambiguous.
        out.sort(key=lambda u: (abs(u.span[0] - holder.span[0]), u.span[0]))
        if abs(out[0].span[0] - holder.span[0]) < abs(out[1].span[0] - holder.span[0]):
            return [out[0]]
    return out


def bind(reading: Reading, reg: Registry) -> Reading:
    """Discharge obligations where exactly one candidate fits. Iterates to a
    fixpoint: a binding can disambiguate a later one."""
    changed = True
    while changed:
        changed = False
        for unit in reading.units:
            obligations = unit.obligations()
            for i, ob in enumerate(obligations):
                if ob.met:
                    continue
                found = _candidates(reading, unit, ob, reg)
                if len(found) == 1:
                    new = list(obligations)
                    new[i] = Obligation(ob.role, ob.need, target=found[0], optional=ob.optional)
                    reading.record(
                        "bind", unit,
                        {"obligations": new},
                        f"{unit.surface!r}.{ob.need} -> {found[0].surface!r} (unique candidate)",
                    )
                    changed = True
    return reading


def _coverage_score(reading: Reading, reg: Registry) -> tuple[int, int]:
    """(unmet non-optional obligations, orphan units) — lower is better."""
    trial = copy.deepcopy(reading)
    attach_obligations(trial, reg)
    bind(trial, reg)
    unmet = sum(len(u.unmet()) for u in trial.units)
    bound_targets = {
        ob.target.uid
        for u in trial.units
        for ob in u.obligations()
        if ob.met and isinstance(ob.target, Unit)
    }
    orphans = sum(
        1
        for u in trial.units
        if u.sense() not in (None, "punct")
        and not u.obligations()
        and u.uid not in bound_targets
    )
    return (unmet, orphans)


def disambiguate(reading: Reading, reg: Registry) -> Reading:
    """Commit one sense per multi-sense unit: the assignment with the best
    obligation coverage wins, and only a unique winner commits."""
    ambiguous = [u for u in reading.units if len(u.senses()) > 1]
    if not ambiguous:
        return reading
    if len(ambiguous) > MAX_AMBIGUOUS_UNITS:
        for u in ambiguous:
            reading.record(
                "ambiguity-overflow", u, {"ambiguous": True},
                f"{len(ambiguous)} ambiguous units exceeds trial cap",
            )
        return reading

    options = [u.senses() for u in ambiguous]
    scored: list[tuple[tuple[int, int], tuple[str, ...]]] = []
    for assignment in itertools.product(*options):
        trial = copy.deepcopy(reading)
        for u, sense in zip(ambiguous, assignment):
            trial.unit(u.uid).features["senses"] = [sense]
        scored.append((_coverage_score(trial, reg), assignment))
    scored.sort(key=lambda pair: (pair[0], pair[1]))

    best_score, best_assignment = scored[0]
    unique = len(scored) == 1 or scored[1][0] > best_score
    if unique:
        for u, sense in zip(ambiguous, best_assignment):
            reading.record(
                "assign-sense", u,
                {"senses": [sense]},
                f"coverage arbitration: {sense!r} leaves {best_score[0]} unmet",
            )
    else:
        for u in ambiguous:
            reading.record(
                "ambiguous", u, {"ambiguous": True},
                "no sense assignment covers strictly best — genuinely ambiguous",
            )
    return reading
