"""The document blackboard: multi-sentence texts, gap-driven re-parse rounds.

Round 0 parses every premise independently. Each later round supplies new
cross-sentence information (discourse referents now; providers and pack
activation later), re-derives facts for exactly the sentences whose gaps
that information can fill, rebuilds the store, and re-saturates. The loop
ends when a round changes nothing; a hard cap errors loudly.

Correctness choices: fact derivation per round is a pure recompute (the
store is rebuilt from scratch each round — no incremental patching to get
subtly wrong), and discourse binding is definitive-or-decline: a pronoun
binds only when exactly ONE antecedent candidate exists; ambiguity stays an
unmet obligation the diagnosis can name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.registry import Registry
from .evaluate import ArithmeticLog
from .facts import FactStore
from .learn import learn
from .model import Fact, Obligation, Reading, Unit
from .patterns import RuleMatchResult, run_rules
from .saturate import saturate

MAX_ROUNDS = 6


@dataclass(frozen=True)
class Gap:
    sentence: int
    kind: str  # unknown-word | ambiguous-sense | unmet-obligation
    key: tuple

    def describe(self) -> str:
        if self.kind == "unknown-word":
            return f"sentence {self.sentence}: unknown word {self.key[0]!r}"
        if self.kind == "ambiguous-sense":
            return f"sentence {self.sentence}: {self.key[0]!r} is ambiguous"
        return f"sentence {self.sentence}: {self.key[0]!r} needs a {self.key[1]}"


@dataclass
class Document:
    readings: list[Reading]
    store: FactStore
    log: ArithmeticLog
    consumed_uids: dict[int, set[int]] = field(default_factory=dict)
    rounds: int = 0
    gaps: list[Gap] = field(default_factory=list)
    rule_results: dict[int, list[RuleMatchResult]] = field(default_factory=dict)


def collect_gaps(readings: list[Reading]) -> list[Gap]:
    gaps: list[Gap] = []
    for reading in readings:
        for unit in reading.units:
            if unit.features.get("unknown"):
                gaps.append(Gap(reading.sentence_index, "unknown-word", (unit.surface,)))
            if unit.features.get("ambiguous"):
                gaps.append(Gap(reading.sentence_index, "ambiguous-sense", (unit.surface,)))
            for ob in unit.unmet():
                gaps.append(
                    Gap(reading.sentence_index, "unmet-obligation", (unit.surface, ob.need))
                )
    return gaps


def _discourse_candidates(readings: list[Reading], upto: int) -> dict[str, Unit]:
    """Name units introduced in sentences before `upto`, keyed by lemma."""
    out: dict[str, Unit] = {}
    for reading in readings:
        if reading.sentence_index >= upto:
            continue
        for unit in reading.units:
            if unit.sense() == "name":
                out[unit.features.get("lemma", unit.features["fold"])] = unit
    return out


def _bind_discourse(readings: list[Reading]) -> set[int]:
    """Bind unmet pronoun `refers` obligations to a UNIQUE prior name.
    Returns the sentence indexes that gained a binding this round."""
    changed: set[int] = set()
    for reading in readings:
        for unit in reading.units:
            if unit.sense() != "pronoun":
                continue
            # number agreement: a PLURAL pronoun ("they") never binds a lone
            # name — group referents are unbuilt, so it honestly stays unmet
            if unit.features.get("number") == "plural":
                continue
            obligations = unit.obligations()
            for i, ob in enumerate(obligations):
                if ob.need != "refers" or ob.met:
                    continue
                candidates = _discourse_candidates(readings, reading.sentence_index)
                if len(candidates) == 1:
                    (lemma, target), = candidates.items()
                    new = list(obligations)
                    new[i] = Obligation(ob.role, ob.need, target=target, optional=ob.optional)
                    reading.record(
                        "bind-discourse", unit,
                        {"obligations": new},
                        f"{unit.surface!r} -> {lemma!r} (unique antecedent in document)",
                    )
                    changed.add(reading.sentence_index)
    return changed


def run_document(premises: list[Reading], reg: Registry) -> Document:
    log = ArithmeticLog()
    doc = Document(readings=premises, store=FactStore(), log=log)

    # round 0: pattern rules per sentence (their matches never change across
    # rounds — rules see one sentence; discourse changes only the fold)
    for reading in premises:
        results = run_rules(reading, reg, phase="read", log=log)
        doc.rule_results[reading.sentence_index] = results
        consumed = doc.consumed_uids.setdefault(reading.sentence_index, set())
        for r in results:
            consumed.update(r.match.consumed)
            for uid in r.match.consumed:
                reading.record(
                    "pattern-consume", reading.unit(uid),
                    {"pattern_consumed": True},
                    f"consumed by rule {r.match.rule.id}",
                    rule_id=r.match.rule.id,
                )

    def rebuild_store() -> FactStore:
        store = FactStore()
        for reading in premises:
            store.admit_rule_results(doc.rule_results.get(reading.sentence_index, []), reg)
            for fact in learn(reading, reg):
                store.admit(fact)
        saturate(store, reg, log)
        return store

    doc.store = rebuild_store()
    for round_no in range(1, MAX_ROUNDS + 1):
        doc.rounds = round_no
        changed = _bind_discourse(premises)
        if not changed:
            break
        doc.store = rebuild_store()
    else:
        raise RuntimeError(
            f"document loop did not settle in {MAX_ROUNDS} rounds — "
            "a synthesizer or discourse pass is oscillating"
        )

    doc.gaps = collect_gaps(premises)
    return doc
