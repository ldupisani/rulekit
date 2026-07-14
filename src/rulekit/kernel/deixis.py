"""Deictic resolution: one primitive for the fifteen hand-written acceptance tests.

A deictic expression ("she", "the rest", "that many", "now", "in the jar") denotes
nothing until you know the REFERENCE POINT it is measured from — Bühler's *origo*.

`docs/deixis.md` shows that rulekit resolves referents at ~15 sites, and that every one
of them hand-writes the SAME acceptance rule:

    exactly one candidate in scope -> bind it; otherwise decline.

That rule was never chosen as a precision policy. It is the ONLY policy available when
there is no reference point to measure distance from: with no origo, candidates cannot
be ranked, so "more than one" can only mean "ambiguous".

This module supplies the missing primitive.

    resolve(candidates, origo, distance, filters) -> the winner, or None

with STRICT-DOMINANCE arbitration: the nearest candidate wins if and only if it is
strictly nearer than every other survivor. Ties decline.

THE LOAD-BEARING PROPERTY, and the reason this can be adopted safely:

    Under a CONSTANT distance function every candidate is equidistant, so strict
    dominance can never be satisfied when two or more candidates survive. `resolve`
    then degenerates EXACTLY to "unique candidate, or decline" — which is precisely
    what the fifteen sites already do.

So a site migrates onto this primitive with a provably ZERO-DIFF behaviour change, and
its real distance metric is switched on afterwards as its own separately-gated
increment. The refactor and the behaviour change never ride in the same commit — which
is what the shared-kernel blast radius in this repo's history demands (HANDOFF: "an
increment you cannot revert independently is not an increment").

The seed of this design is already in the tree: `obligations.py::_candidates` is the one
site that RANKS, using token distance from the holder's span with exactly this
strict-dominance rule.

NOTHING IN THIS MODULE ENUMERATES A WORD. Dimensions are structure, not lexicon
(constitution rule 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

# ---------------------------------------------------------------------------
# Dimensions — referents are TYPED, so a time expression is never a candidate
# antecedent for a personal pronoun. That type confusion is a live bug generator:
# increment 88 (weekday names read as proper names, polluting the antecedent pool
# and breaking the NEXT sentence's pronoun binding) was exactly this, fixed by hand
# for one word family. docs/deixis.md §4 shows months are the same bug in a new
# costume.
# ---------------------------------------------------------------------------
PERSON = "person"
DISCOURSE = "discourse"
TIME = "time"
PLACE = "place"

DIMENSIONS = (PERSON, DISCOURSE, TIME, PLACE)


@dataclass(frozen=True)
class Origo:
    """The reference point a deictic expression is measured from.

    Fields are all optional: a dimension that has no metric yet simply leaves its
    coordinate unset, and its distance function ignores it. `sentence` and `span` are
    available today (they are what `obligations.py` already ranks on). `moment` and
    `locus` are the temporal and spatial coordinates — reserved, and unused until
    those origos are built (deixis.md phases 2 and 4).
    """

    sentence: int | None = None
    span: tuple[int, int] | None = None
    moment: Any = None  # reserved: the temporal origo (deixis.md phase 2)
    locus: Any = None  # reserved: the spatial origo (deixis.md phase 4)


@dataclass(frozen=True)
class Referent:
    """A candidate the origo can measure a distance to.

    `dimension` types the referent so cross-dimension pollution is unrepresentable.
    `key` is the identity the caller cares about (a lemma, a fact, a unit). `payload`
    is whatever the caller wants back.
    """

    dimension: str
    key: Any
    payload: Any = None
    sentence: int | None = None
    span: tuple[int, int] | None = None


# ---------------------------------------------------------------------------
# Distance functions
# ---------------------------------------------------------------------------

Distance = Callable[[Referent, Origo], Any]


def constant(_referent: Referent, _origo: Origo) -> int:
    """Every candidate equidistant.

    This is the migration metric, and the whole safety argument. Under it, strict
    dominance is unsatisfiable whenever two or more candidates survive, so `resolve`
    returns None for any ambiguity — byte-for-byte the behaviour of the fifteen
    hand-written "exactly one, or decline" tests.
    """
    return 0


def token_distance(referent: Referent, origo: Origo) -> int:
    """Token distance from the origo's span — the metric `obligations.py` already uses.

    NOT wired into any site yet. Switching a site from `constant` to this is a
    BEHAVIOUR CHANGE and must be its own gated increment with its own TEST look.
    """
    if referent.span is None or origo.span is None:
        return 0
    return abs(referent.span[0] - origo.span[0])


# ---------------------------------------------------------------------------
# The primitive
# ---------------------------------------------------------------------------

Filter = Callable[[Referent, Origo], bool]


def resolve(
    candidates: Iterable[Referent],
    origo: Origo,
    distance: Distance = constant,
    *,
    filters: Sequence[Filter] = (),
    dimension: str | None = None,
) -> Referent | None:
    """The single acceptance test. Returns the winning Referent, or None to decline.

    1. Keep only candidates of the requested `dimension` (if given). A typed candidate
       set is what stops a TIME word competing to be a PERSON antecedent.
    2. Apply `filters`. Filters are PRECISION-ONLY: they may only shrink the candidate
       set, never add to it, so no filter can turn a decline into a commit.
    3. Rank by `distance` and apply STRICT DOMINANCE: the nearest wins iff it is
       strictly nearer than every other survivor. A tie is ambiguity, and ambiguity
       declines.

    With `distance=constant` (the default) step 3 reduces to "exactly one survivor, or
    decline" — the behaviour every migrating site already has.
    """
    survivors = [c for c in candidates if dimension is None or c.dimension == dimension]
    for keep in filters:
        survivors = [c for c in survivors if keep(c, origo)]

    if not survivors:
        return None
    if len(survivors) == 1:
        return survivors[0]

    # Deterministic order first — the store's iteration order must never decide a
    # binding. Sort by (distance, then a stable tiebreak) exactly as obligations.py does.
    survivors.sort(key=lambda c: (distance(c, origo), _stable(c)))
    if distance(survivors[0], origo) < distance(survivors[1], origo):
        return survivors[0]
    # Strictly-equal nearest candidates: ambiguous. DECLINE.
    #
    # This is the one genuinely new precision surface in the design (deixis.md §6), and
    # the rule is absolute: any change that makes arbitration LESS strict is a
    # confident-wrong factory.
    return None


def _stable(referent: Referent) -> tuple:
    """A total order that never depends on dict/set iteration order."""
    span = referent.span if referent.span is not None else (-1, -1)
    sentence = referent.sentence if referent.sentence is not None else -1
    return (sentence, span, str(referent.key))
