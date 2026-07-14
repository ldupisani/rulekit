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

from dataclasses import dataclass, field
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

# NOT a Bühler deictic dimension. It is the same ARBITRATION MACHINE (rank by distance
# from an origo, strict dominance, ties decline) applied to intra-sentential argument
# attachment — which unit fills this obligation's role. obligations.py has always done
# exactly this, by hand, and is the seed the rest of this module was generalised from.
#
# It is typed separately for the same reason the deictic dimensions are typed at all: a
# syntactic candidate must never be able to compete with a discourse antecedent.
SYNTAX = "syntax"

DIMENSIONS = (PERSON, DISCOURSE, TIME, PLACE, SYNTAX)


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


# ---------------------------------------------------------------------------
# The journal — what the engine THREW AWAY
#
# The Decision trace records mutations: target, before, after. A DECLINE mutates
# nothing, so it is structurally invisible to it — the designer can show every binding
# that succeeded and not one that failed. But the declines are where the information is:
# at most sites the entire candidate set is discarded with no record kept anywhere, and
# nothing computes distance because, modulo obligations.py, nothing has an origo to
# measure from.
#
# This is the parallel, observational channel that keeps it. It rides on ArithmeticLog
# (which is already threaded to every deep site) and is None whenever tracing is off, so
# bench pays nothing.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateRecord:
    """One candidate as it was SEEN at resolve() time.

    Every coordinate is optional and is None when the candidate genuinely HAS none.
    That honesty is load-bearing: most sites resolve over bare measure/entity strings
    with no span and no sentence, and a viewer that invented (0, 0) for them would draw
    a field that does not exist.
    """

    key: str
    dimension: str
    sentence: int | None = None
    span: tuple[int, int] | None = None
    uid: int | None = None
    # None => never measured (eliminated before ranking, or the lone survivor).
    distance: Any = None
    # None => survived. Otherwise "dimension" or "filter:<name>".
    eliminated_by: str | None = None


@dataclass
class Observation:
    """One resolve() call, whole: who asked, from where, over what, and what happened.

    Not frozen — `attempts` counts identical repeats (see Journal.record).
    """

    source: str
    dimension: str | None
    origo: Origo
    metric: str
    candidates: tuple[CandidateRecord, ...]
    filters: tuple[str, ...]
    outcome: str  # "bound" | "declined"
    winner: str | None
    arbitration: str | None  # "unique" | "dominant" | None
    reason: str | None  # "no-candidates" | "dimension-mismatch" | "filtered-out" | "tie"
    round: int = 0
    attempts: int = 1

    def identity(self) -> tuple:
        """What makes two observations THE SAME observation.

        Deliberately excludes `round` and `attempts`: a resolution re-attempted in a
        later round with an identical candidate set and an identical outcome is the
        same deictic event, not a new one.
        """
        return (
            self.source,
            self.dimension,
            self.origo.sentence,
            self.origo.span,
            tuple((c.key, c.eliminated_by) for c in self.candidates),
            self.outcome,
            self.winner,
            self.reason,
        )


@dataclass
class Journal:
    """Append-only, insertion-ordered, deduped by identity.

    resolve() runs inside fixpoints: document.py re-reads up to MAX_ROUNDS times, and
    saturate.py's own loop re-runs every plugin every round. A binding that SUCCEEDS is
    skipped on later rounds — but a DECLINE is retried every single round, so every
    interesting resolution is the repeated one, and naive appending would bury the
    reader in identical rows.

    So: an identical repeat bumps `attempts` and appends nothing (it carries literally
    zero information — same inputs, same verdict, same reason). But a resolution whose
    candidate set CHANGED is a new row, because that transition — "two candidates in
    round 1, one in round 3" — is the exact moment the reading happened, and collapsing
    it would erase the only thing worth watching.
    """

    observations: list[Observation] = field(default_factory=list)
    round: int = 0
    _index: dict[tuple, Observation] = field(default_factory=dict, repr=False)

    def record(self, obs: Observation) -> Observation:
        seen = self._index.get(obs.identity())
        if seen is not None:
            seen.attempts += 1
            return seen
        self._index[obs.identity()] = obs
        self.observations.append(obs)
        return obs


def _arbitrate(
    survivors: list[Referent], origo: Origo, distance: Distance
) -> tuple[Referent | None, str | None, str | None]:
    """The acceptance test proper: (winner, arbitration, decline_reason).

    THE ONLY implementation of strict dominance in the tree. Both `resolve` paths — the
    silent one and the journalling one — arbitrate through this function, so they cannot
    drift apart no matter what is edited later. A "0-diff fast path" that re-implements
    the decision is a 0-diff *hope*; this makes it a property.

    `arbitration` is how the winner won: "unique" (a lone survivor) or "dominant"
    (strictly nearest). Under `constant` every win is "unique" — a journal showing 100%
    "unique" is the visual proof that no real metric is live yet, and the first
    "dominant" row is the moment one is.
    """
    if not survivors:
        return None, None, None  # the caller knows WHY the set is empty; it says so
    if len(survivors) == 1:
        return survivors[0], "unique", None

    # Deterministic order first — the store's iteration order must never decide a
    # binding. Sort by (distance, then a stable tiebreak) exactly as obligations.py does.
    survivors.sort(key=lambda c: (distance(c, origo), _stable(c)))
    if distance(survivors[0], origo) < distance(survivors[1], origo):
        return survivors[0], "dominant", None
    # Strictly-equal nearest candidates: ambiguous. DECLINE.
    #
    # This is the one genuinely new precision surface in the design (deixis.md §6), and
    # the rule is absolute: any change that makes arbitration LESS strict is a
    # confident-wrong factory.
    return None, None, "tie"


def resolve(
    candidates: Iterable[Referent],
    origo: Origo,
    distance: Distance = constant,
    *,
    filters: Sequence[Filter] = (),
    dimension: str | None = None,
    journal: Journal | None = None,
    source: str = "?",
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

    `journal` is OBSERVATIONAL ONLY and cannot change the return value: it is what the
    designer renders (a decline mutates nothing, so it is invisible to the Decision
    trace — see the Journal docstring). It is None on every bench path, and the
    `journal is None` branch below does exactly the work this function did before the
    journal existed. `source` names the call site, in `Provenance.source` vocabulary, so
    an observation can be cross-linked to the facts and decisions it produced.

    CONTRACT — `distance` and `filters` MUST BE PURE. When a journal is attached,
    `resolve` calls `distance` for candidates the silent path short-circuits past (it
    has to, to record what it saw). Both shipped metrics are pure; keep it that way.
    """
    if journal is None:
        # The silent path. Statement-for-statement what this function has always done.
        survivors = [
            c for c in candidates if dimension is None or c.dimension == dimension
        ]
        for keep in filters:
            survivors = [c for c in survivors if keep(c, origo)]
        winner, _, _ = _arbitrate(survivors, origo, distance)
        return winner

    # The recording path. Same predicates, same call counts per (filter, survivor) — it
    # only remembers WHICH candidate each verdict fell on, and why.
    pool = list(candidates)
    eliminated: dict[int, str] = {}

    survivors = []
    for cand in pool:
        if dimension is None or cand.dimension == dimension:
            survivors.append(cand)
        else:
            eliminated[id(cand)] = "dimension"

    for index, keep in enumerate(filters):
        kept = []
        for cand in survivors:
            if keep(cand, origo):
                kept.append(cand)
            else:
                eliminated[id(cand)] = f"filter:{_filter_name(keep, index)}"
        survivors = kept

    winner, arbitration, reason = _arbitrate(survivors, origo, distance)

    if winner is not None:
        outcome = "bound"
    else:
        outcome = "declined"
        if not pool:
            reason = "no-candidates"
        elif not survivors:
            # Every candidate was thrown out. WHICH filter did it matters enormously:
            # "dimension-mismatch" is the fingerprint of cross-dimension pollution — a
            # TIME word competing to be a PERSON antecedent — which is the bug class
            # deixis.md §4 documents and nothing in the engine can currently observe.
            causes = set(eliminated.values())
            reason = "dimension-mismatch" if causes == {"dimension"} else "filtered-out"
        # else: reason is already "tie" from _arbitrate.

    survivor_ids = {id(c) for c in survivors}
    journal.record(
        Observation(
            source=source,
            dimension=dimension,
            origo=origo,
            metric=getattr(distance, "__name__", "?"),
            candidates=tuple(
                CandidateRecord(
                    key=str(cand.key),
                    dimension=cand.dimension,
                    sentence=cand.sentence,
                    span=cand.span,
                    # Duck-typed so deixis.py need not import model.Unit — a bare
                    # string candidate simply has no uid, and says so.
                    uid=getattr(cand.payload, "uid", None),
                    # Distance is only meaningful for a candidate that survived to be
                    # measured. An eliminated one was never ranked; None says that,
                    # rather than implying it lost on distance.
                    distance=(
                        distance(cand, origo) if id(cand) in survivor_ids else None
                    ),
                    eliminated_by=eliminated.get(id(cand)),
                )
                for cand in pool
            ),
            filters=tuple(
                _filter_name(keep, i) for i, keep in enumerate(filters)
            ),
            outcome=outcome,
            winner=str(winner.key) if winner is not None else None,
            arbitration=arbitration,
            reason=reason,
            round=journal.round,
        )
    )
    return winner


def _filter_name(keep: Filter, index: int) -> str:
    name = getattr(keep, "__name__", "")
    if not name or name == "<lambda>":
        return f"#{index}"
    return name


def _stable(referent: Referent) -> tuple:
    """A total order that never depends on dict/set iteration order."""
    span = referent.span if referent.span is not None else (-1, -1)
    sentence = referent.sentence if referent.sentence is not None else -1
    return (sentence, span, str(referent.key))
