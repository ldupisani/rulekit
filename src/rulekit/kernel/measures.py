"""Measure resolution: which fact key does the ask's measure word mean?

Moved out of `answer.py` UNCHANGED (session-4 refactor, step C) — each
function is byte-for-byte the one that lived there, pinned by the consumer
golden master and the full eight-slice gate. `answer.py` keeps the dispatch
and the `Answer` type; `totals.py` holds the folds that consume the measure
this module resolves.

The import direction is one-way BY DESIGN: measures -> answer (for `Answer`)
and nothing in `answer.py` imports back. `totals.py` sits above both.
"""

from __future__ import annotations

import re

from ..data.registry import Registry
from . import deixis
from .answer import Answer
from .facts import FactStore
from .model import Quantity


def _resolve_measure_against(
    measure: str, candidates: set[str], reg: Registry, journal=None
) -> str | None:
    """Resolve a measure word against a CANDIDATE set of in-play measures.

    - a word matching a candidate resolves to itself ('pounds' in a pounds
      problem — never collapsed onto some canonical currency);
    - a CATEGORY name ('currency' in a bare how-much ask) or a category
      member with no candidate of its own ('money') resolves to the UNIQUE
      candidate measure of that category — one currency in play uses it,
      mixed currencies are genuinely ambiguous and return None (decline).
      ONLY categories marked `interchangeable` in the packs resolve this
      way: currency denominations stand in for each other; sibling count
      nouns never do (a 'cats' ask must not answer from 'dog' facts — a
      real confident-wrong: "20 pets. 8 of them are dogs. How many cats?"
      answered 8 via the unique in-store 'animal' member);
    - anything else passes through unresolved (the singular form, unchanged).
    """
    singular = reg.plural_to_singular.get(measure, measure)
    if singular in candidates:
        return singular
    categories = (
        [singular] if singular in reg.category_parents
        else list(reg.word_categories.get(singular, ()))
    )
    categories = [c for c in categories if c in reg.interchangeable_categories]
    if not categories:
        return singular
    present = sorted(
        m for m in candidates
        if any(reg.word_in_category(m, c) for c in categories)
    )
    # THE WEAKEST ORIGO OF ALL THE SITES: no sentence, no span, no entity — an empty
    # Origo(), because "which measure does this ask mean?" is asked from nowhere at all.
    # Note the site is TRI-STATE, and only this branch is a deictic resolution: zero
    # candidates PASSES THROUGH unchanged (a soft non-decline), while two-or-more is a
    # hard decline. Constant metric => byte-identical to the `len(present) == 1` it
    # replaces.
    winner = deixis.resolve(
        [deixis.Referent(dimension=deixis.DISCOURSE, key=m) for m in present],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.DISCOURSE,
        journal=journal,
        source="answer/resolve-measure",
    )
    if winner is not None:
        return winner.key
    if present:
        return None  # mixed measures of the category — ambiguous
    return singular


def _resolve_measure(
    measure: str, store: FactStore, reg: Registry, journal=None
) -> str | None:
    """Resolve the ask's measure word against the FACTS (see
    `_resolve_measure_against` for the category-fallback rules)."""
    in_store = {q.measure for q in store.by_kind(Quantity)}
    return _resolve_measure_against(measure, in_store, reg, journal=journal)


def _resolve_dimension_measure(
    measure: str, store: FactStore, reg: Registry, journal=None
) -> str | None:
    """mining candidate dimension-aggregate-asks: resolve a DIMENSION word
    ('height'/'weight'/'age'/'distance'/'balance'/'earnings'/'cost' — an
    aggregate ask's measure named by WHAT is measured, not by the unit) or
    a unit-family CATEGORY NAME BOUND DIRECTLY ('time_measure', the way
    ask/how-long-is-total-dimension binds its `measure` field — mirrors
    `currency`'s own `measure: currency` precedent one level up) against
    the FACTS, by declared FAMILY membership (packs/core-english/
    categories/core.yaml's `length_measure`/`mass_measure`/`time_measure`/
    `currency_measure`, each `dimension: true`) — UNIQUE-OR-DECLINE exactly
    like `_resolve_measure_against`'s own currency-category discipline:
    zero or >=2 distinct family members present among the in-store
    measures is unresolvable and returns None, never a guess.

    Deliberately a SEPARATE function from `_resolve_measure`/
    `_resolve_measure_against`, consulting a SEPARATE registry set
    (`reg.dimension_categories`, never `interchangeable_categories`) —
    called ONLY from `_combined_holder_totals` when the ask opts in via
    `dimension_measure: true` (the new imperative-headed / dimension-
    adjective totality asks). Every OTHER consumer (single-entity,
    unique-entity, difference, ...) keeps calling `_resolve_measure`
    unchanged, so a question that happens to bind 'height'/'weight' as a
    measure through any OTHER, PRE-EXISTING ask id is completely
    unaffected (the shared-function blast-radius HANDOFF invariant)."""
    in_store = {q.measure for q in store.by_kind(Quantity)}
    if measure in reg.dimension_categories:
        families = [measure]
    else:
        singular = reg.plural_to_singular.get(measure, measure)
        families = [
            c for c in reg.word_categories.get(singular, ())
            if c in reg.dimension_categories
        ]
    if not families:
        return None
    # Another site docs/deixis.md's inventory of fifteen missed: the same degenerate
    # rule again, over a DIFFERENT registry set (dimension_categories, never
    # interchangeable_categories). Same empty Origo() — a dimension ask asks from
    # nowhere too. Unlike _resolve_measure_against this one is BINARY, not tri-state:
    # zero candidates declines rather than passing through.
    winner = deixis.resolve(
        [
            deixis.Referent(dimension=deixis.DISCOURSE, key=m)
            for m in sorted(
                m for m in in_store
                if any(reg.word_in_category(m, f) for f in families)
            )
        ],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.DISCOURSE,
        journal=journal,
        source="answer/resolve-dimension-measure",
    )
    # zero or ambiguous family members in the facts — never guess
    return winner.key if winner is not None else None


def _check_req_unit(
    req_unit: str | None, singular: str, store: FactStore, reg: Registry, journal=None
) -> bool:
    """Decline-safety for a parenthetical unit qualifier ("how much money,
    in dollars, ...", mining candidate unit-parenthetical-asks): the
    ask-bound unit must resolve to the SAME concrete measure the ask's own
    `measure` already resolved to (`singular`). Reuses
    `_resolve_measure_against` unchanged — a generic currency word
    ("money"/"pounds" standing in for whatever denomination is in play)
    still resolves via the existing interchangeable-category fallback, but
    a specific unit from a DIFFERENT, non-interchangeable category (asked
    dollars, facts in quarters — `currency` and `coin` are distinct
    categories in this pack) fails to resolve to `singular` and declines
    rather than silently answering in the wrong unit. `req_unit` absent
    (no parenthetical in the question) is always a pass-through."""
    if req_unit is None:
        return True
    in_store = {q.measure for q in store.by_kind(Quantity)}
    return _resolve_measure_against(req_unit, in_store, reg, journal=journal) == singular


def _measure_substance_guard(
    store: FactStore, measure: str, substance: str, entities: list[str] | None = None,
) -> Answer | None:
    """Decline-safety for a partitive-tail ask (mining candidate
    partitive-measure-ask-slot: "how many KILOGRAMS OF MEAT are left" /
    "... are there" / "... does WHO have"). The ask's `item` slot only ever
    binds the bare MEASURE noun ('kilogram') — the ASKED substance ('meat')
    names nothing any fact is keyed on, so a naive fold would silently sum
    every substance sharing that measure noun across the document, exactly
    the sibling-borrow wrong `_resolve_measure_against`'s own docstring
    warns about for non-interchangeable categories ("How many cats?"
    answered from 'dog' facts): a 'rice' quantity answering a 'meat'
    question.

    `measure_qualifier` (learn.py's `_measure_substance`, a fallback source
    for the SAME field `_qualifier`/`measure_qualifier` already use for
    adjective-qualified measures — mining candidate qualified-measure-keys)
    carries the STATED substance on every Quantity fact whose counted noun
    came from a partitive 'MEASURE of SUBSTANCE' phrase. Scanning the
    candidate facts (optionally scoped to `entities`, for a single-entity
    ask) for DISTINCT non-null `measure_qualifier` values:
    - more than one distinct substance attested -> the text names two+
      substances under this measure and the ask cannot tell which the fold
      already summed -> decline;
    - exactly one attested and it does not match the ASKED substance ->
      zero facts exist about the asked substance -> decline;
    - zero attested (the overwhelming case: no partitive tail anywhere, or
      every mention agrees with what was asked) -> None, proceed exactly as
      the bare (non-partitive) ask always has.

    Every EXISTING (non-partitive) ask never binds `measure_substance` in
    its query, so this function is never even called for them — a pure
    opt-in addition, zero change to any currently-shipped consumer path."""
    candidates = [
        q for q in store.by_kind(Quantity)
        if q.measure == measure and (entities is None or q.entity in entities)
    ]
    qualifiers = {q.measure_qualifier for q in candidates if q.measure_qualifier}
    if len(qualifiers) > 1:
        return Answer(
            "decline", None,
            f"measure {measure!r} names more than one substance in the "
            f"facts {sorted(qualifiers)!r} — asked for {substance!r}",
        )
    if len(qualifiers) == 1 and substance not in qualifiers:
        return Answer(
            "decline", None,
            f"no {substance!r} facts known for measure {measure!r}",
        )
    return None


