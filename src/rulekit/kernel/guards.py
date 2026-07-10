"""Guards: decline-safety checks between the pipeline and a committed answer.

Guards read only DECLARED properties (consumed unit ids, the arithmetic log,
unit features) — never rule identities. Config (guards.yaml) can enable or
tune a guard but cannot reference rules; that entanglement class is banned.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.registry import Registry
from .answer import Answer
from .evaluate import ArithmeticLog
from .facts import FactStore
from .model import Reading

_NUMERIC_FACT_FIELDS = ("value", "factor", "offset", "fraction")


@dataclass
class GuardVeto:
    guard: str
    reason: str


def _enabled(reg: Registry, name: str) -> bool:
    cfg = reg.guard_config.get(name)
    return bool(cfg.get("enabled", True)) if cfg is not None else True


def _fact_values(store: FactStore) -> set[float]:
    out: set[float] = set()
    for fact in store.facts:
        for field_name in _NUMERIC_FACT_FIELDS:
            v = getattr(fact, field_name, None)
            if isinstance(v, (int, float)):
                out.add(float(v))
    return out


def check(
    premises: list[Reading],
    consumed_uids: dict[int, set[int]],  # sentence index -> consumed unit uids
    log: ArithmeticLog,
    reg: Registry,
    proposed: Answer,
    store: FactStore | None = None,
) -> GuardVeto | None:
    """Run all enabled guards against a proposed committed answer.
    Returns the first veto, or None. Only 'number' answers are guarded —
    a decline is already safe."""
    if not proposed.committed:
        return None

    if _enabled(reg, "unknown-word"):
        for reading in premises:
            unknown = reading.unknown_words()
            if unknown:
                return GuardVeto(
                    "unknown-word",
                    f"cannot commit while {unknown} are unknown (sentence "
                    f"{reading.sentence_index})",
                )

    if _enabled(reg, "value-accounting"):
        # A stated value is accounted iff it reached the reading's OUTPUT: a
        # rule consumed it, a fact carries it, or the arithmetic used it.
        # Merely being syntactically bound is NOT enough — an ambiguous
        # pronoun's sentence parses fine yet yields no fact, and committing
        # an answer that ignores its value is the confident-wrong this
        # guard exists to prevent.
        fact_values = _fact_values(store) if store is not None else set()
        for reading in premises:
            used = consumed_uids.get(reading.sentence_index, set())
            for unit in reading.units:
                if unit.features.get("value_kind") != "count":
                    continue
                value = float(unit.features["value"])
                if unit.uid in used or value in fact_values or log.uses_value(value):
                    continue
                return GuardVeto(
                    "value-accounting",
                    f"stated value {unit.surface!r} (sentence "
                    f"{reading.sentence_index}) reached no fact and no "
                    "arithmetic — declining rather than risk a wrong commit",
                )

    if _enabled(reg, "ambiguity"):
        for reading in premises:
            for unit in reading.units:
                if unit.features.get("ambiguous"):
                    return GuardVeto(
                        "ambiguity",
                        f"{unit.surface!r} stayed ambiguous (sentence "
                        f"{reading.sentence_index})",
                    )
    return None
