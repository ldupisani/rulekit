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
from .model import Reading


@dataclass
class GuardVeto:
    guard: str
    reason: str


def _enabled(reg: Registry, name: str) -> bool:
    cfg = reg.guard_config.get(name)
    return bool(cfg.get("enabled", True)) if cfg is not None else True


def check(
    premises: list[Reading],
    consumed_uids: dict[int, set[int]],  # sentence index -> consumed unit uids
    log: ArithmeticLog,
    reg: Registry,
    proposed: Answer,
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
        for reading in premises:
            used = consumed_uids.get(reading.sentence_index, set())
            for unit in reading.units:
                if unit.features.get("value_kind") != "count":
                    continue
                if unit.uid in used:
                    continue
                bound = any(
                    ob.met for ob in unit.obligations()
                ) or any(
                    ob.target is unit
                    for u in reading.units
                    for ob in u.obligations()
                    if ob.met
                )
                if bound or log.uses_value(unit.features["value"]):
                    continue
                return GuardVeto(
                    "value-accounting",
                    f"stated value {unit.surface!r} (sentence "
                    f"{reading.sentence_index}) was never used — declining "
                    "rather than risk a wrong commit",
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
