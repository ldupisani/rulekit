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
from . import deixis
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
                # deixis.resolve with the CONSTANT metric is exactly the rule this
                # site hand-wrote ("unique antecedent, or leave unmet"): under a
                # constant distance no candidate can strictly dominate another, so
                # two-or-more always declines. Migrating is provably 0-diff; the
                # PERSON metric is switched on later as its own gated increment
                # (docs/deixis.md phase 5).
                candidates = _discourse_candidates(readings, reading.sentence_index)
                winner = deixis.resolve(
                    [
                        deixis.Referent(dimension=deixis.PERSON, key=lemma, payload=target)
                        for lemma, target in candidates.items()
                    ],
                    deixis.Origo(sentence=reading.sentence_index, span=unit.span),
                    deixis.constant,
                    dimension=deixis.PERSON,
                )
                if winner is not None:
                    lemma, target = winner.key, winner.payload
                    new = list(obligations)
                    new[i] = Obligation(ob.role, ob.need, target=target, optional=ob.optional)
                    reading.record(
                        "bind-discourse", unit,
                        {"obligations": new},
                        f"{unit.surface!r} -> {lemma!r} (unique antecedent in document)",
                    )
                    changed.add(reading.sentence_index)
    return changed


def _measure_anaphor_candidate_lemma(unit: Unit) -> str | None:
    if unit.sense() != "noun" or unit.features.get("measure_anaphor"):
        return None
    if unit.features.get("number") != "plural":
        return None
    lemma = unit.features.get("lemma") or unit.features.get("fold")
    return lemma or None


def _bind_measure_anaphor(readings: list[Reading]) -> set[int]:
    """Bind unresolved measure-noun anaphors (mining candidate measure-
    noun-anaphor: 'ones'-headed counted NPs, condense.py's merge-measure-
    anaphor) to the UNIQUE prior counted-noun lemma in the document — the
    measure-noun sibling of `_bind_discourse` above, resolving WHAT is
    being counted rather than WHO holds it. Candidates are PLURAL noun-
    sensed units only, drawn from every sentence up to and including this
    one (same-sentence mentions BEFORE the anaphor's own position count
    too — "6 blue balls, ... blue ONES" resolves within one sentence, no
    document round needed for that shape). Zero or two-or-more distinct
    candidate lemmas leaves it unresolved this round (learn.py's `_lemma`
    then returns a reserved sentinel no ask can ever match); a later round
    can still resolve it once a sibling sentence's own anaphor binding
    (rerun_rules) or an unrelated fact narrows the candidate set — the
    same reason `_bind_discourse` re-tries every round instead of once.
    Returns the sentence indexes that gained a binding this round."""
    changed: set[int] = set()
    for reading in readings:
        for unit in reading.units:
            if not unit.features.get("measure_anaphor"):
                continue
            if unit.features.get("antecedent_lemma") is not None:
                continue
            candidates: set[str] = set()
            for other in readings:
                if other.sentence_index > reading.sentence_index:
                    continue
                for cand in other.units:
                    if cand.uid == unit.uid:
                        continue
                    if (
                        other.sentence_index == reading.sentence_index
                        and cand.span[0] >= unit.span[0]
                    ):
                        continue
                    lemma = _measure_anaphor_candidate_lemma(cand)
                    if lemma is not None:
                        candidates.add(lemma)
            # Same primitive, DISCOURSE dimension: this resolves WHAT is counted, not
            # WHO holds it. Typing the candidates is the point — a person antecedent
            # can never be mistaken for a measure-noun antecedent, and vice versa.
            # Constant metric => byte-identical to the `len(candidates) == 1` it
            # replaces. Sorted for a deterministic candidate order (the set's
            # iteration order must never be able to decide a binding).
            winner = deixis.resolve(
                [
                    deixis.Referent(dimension=deixis.DISCOURSE, key=lemma)
                    for lemma in sorted(candidates)
                ],
                deixis.Origo(sentence=reading.sentence_index, span=unit.span),
                deixis.constant,
                dimension=deixis.DISCOURSE,
            )
            if winner is not None:
                lemma = winner.key
                reading.record(
                    "bind-measure-anaphor", unit,
                    {"antecedent_lemma": lemma},
                    f"{unit.surface!r} -> {lemma!r} (unique prior counted-noun lemma)",
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

    def rerun_rules(sentence_indexes: set[int]) -> None:
        """Discourse binding changed these sentences — their pattern rules
        get a fresh look (a resolved pronoun now satisfies name slots)."""
        for reading in premises:
            if reading.sentence_index not in sentence_indexes:
                continue
            results = run_rules(reading, reg, phase="read", log=log)
            doc.rule_results[reading.sentence_index] = results
            consumed = doc.consumed_uids.setdefault(reading.sentence_index, set())
            for r in results:
                for uid in r.match.consumed:
                    if uid in consumed:
                        continue
                    consumed.add(uid)
                    reading.record(
                        "pattern-consume", reading.unit(uid),
                        {"pattern_consumed": True},
                        f"consumed by rule {r.match.rule.id}",
                        rule_id=r.match.rule.id,
                    )

    doc.store = rebuild_store()
    for round_no in range(1, MAX_ROUNDS + 1):
        doc.rounds = round_no
        changed = _bind_discourse(premises)
        changed |= _bind_measure_anaphor(premises)
        if not changed:
            break
        rerun_rules(changed)
        doc.store = rebuild_store()
    else:
        raise RuntimeError(
            f"document loop did not settle in {MAX_ROUNDS} rounds — "
            "a synthesizer or discourse pass is oscillating"
        )

    doc.gaps = collect_gaps(premises)
    return doc
