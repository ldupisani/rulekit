"""Core data model: Word, Unit, Obligation, Decision, Reading, Fact.

Invariants this module enforces:
- A Word's surface is immutable; findings accumulate as Unit features.
- Every mutation of a Unit goes through Reading.record() and is stored as a
  reversible before/after diff carrying provenance (rule id or stage name).
- Facts are frozen and hashable; the store dedupes by equality.
- All iteration surfaces are deterministic (insertion/sorted order only).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Iterator

# Sentinel target: an obligation discharged by a pattern rule rather than by
# binding to another unit (difg's _PATTERN_UNIT).
PATTERN: object = type("PatternSentinel", (), {"__repr__": lambda s: "<PATTERN>"})()


@dataclass(frozen=True)
class Word:
    """Immutable atom of input text."""

    surface: str
    index: int  # token position in the sentence


@dataclass
class Obligation:
    """A demand a word's role places on the rest of the sentence.

    `target` is None while unmet; a Unit once bound; PATTERN when a pattern
    rule consumed the unit. Replaced (never mutated in place) on binding so
    Decision diffs stay clean snapshots.
    """

    role: str  # the sense/role that imposed it, e.g. "quantifier"
    need: str  # what it must find, e.g. "collection"
    target: Any = None
    optional: bool = False

    @property
    def met(self) -> bool:
        return self.target is not None


class Unit:
    """A unit of meaning: one or more words plus accumulated findings.

    Direct feature assignment is forbidden outside Reading.record; use
    reading.record(...) so the change is logged and reversible.
    """

    __slots__ = ("uid", "words", "features")

    def __init__(self, uid: int, words: tuple[Word, ...], features: dict[str, Any] | None = None):
        self.uid = uid
        self.words = words
        self.features: dict[str, Any] = features if features is not None else {}

    @property
    def surface(self) -> str:
        return " ".join(w.surface for w in self.words)

    @property
    def span(self) -> tuple[int, int]:
        return (self.words[0].index, self.words[-1].index)

    def obligations(self) -> list[Obligation]:
        return self.features.get("obligations", [])

    def unmet(self) -> list[Obligation]:
        return [o for o in self.obligations() if not o.met and not o.optional]

    def senses(self) -> list[str]:
        return self.features.get("senses", [])

    def sense(self) -> str | None:
        """The committed sense, once disambiguation has run."""
        s = self.senses()
        return s[0] if len(s) == 1 else self.features.get("sense")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Unit({self.uid}:{self.surface!r})"


@dataclass
class Decision:
    """One reversible change: a feature diff on a target unit.

    `before`/`after` are deep-copied snapshots of the changed feature keys, so
    restoring `before` undoes the decision exactly. `target_surface` is the
    unit's surface AT RECORD TIME — merges retire uids, so the trace keeps
    its own name for the target.
    """

    seq: int
    kind: str  # e.g. "annotate-number", "assign-sense", "bind", "merge"
    target_uid: int
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str
    rule_id: str | None = None  # pattern/synth rule provenance, if any
    target_surface: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "kind": self.kind,
            "target": self.target_uid,
            "target_surface": self.target_surface,
            "before": _jsonable(self.before),
            "after": _jsonable(self.after),
            "reason": self.reason,
            "rule_id": self.rule_id,
        }


def _jsonable(value: Any) -> Any:
    """Best-effort JSON projection for trace serialization."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Obligation):
        target = value.target
        if isinstance(target, Unit):
            target = f"unit:{target.uid}"
        elif target is PATTERN:
            target = "<pattern>"
        return {"role": value.role, "need": value.need, "target": target, "optional": value.optional}
    if isinstance(value, Unit):
        return f"unit:{value.uid}"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


# ---------------------------------------------------------------------------
# Facts — frozen, hashable, provenance-carrying.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provenance:
    source: str  # rule id, "fold", or synthesizer name
    sentence: int  # sentence index within the document
    decision_seq: int | None = None


@dataclass(frozen=True)
class Fact:
    provenance: Provenance

    def key(self) -> tuple:
        """Identity for conflict adjudication: facts with the same key but
        different values conflict. Subclasses override."""
        raise NotImplementedError

    def value_part(self) -> Any:
        """The part compared for agreement between same-key facts."""
        return None


@dataclass(frozen=True)
class Predication(Fact):
    subject: str
    verb: str
    polarity: bool = True
    dobj: str | None = None

    def key(self) -> tuple:
        return ("predication", self.subject, self.verb, self.dobj)

    def value_part(self) -> Any:
        return self.polarity


@dataclass(frozen=True)
class Membership(Fact):
    member: str
    collection: str
    polarity: bool = True

    def key(self) -> tuple:
        return ("membership", self.member, self.collection)

    def value_part(self) -> Any:
        return self.polarity


@dataclass(frozen=True)
class Subset(Fact):
    part: str
    whole: str
    fraction: float | None = None  # part = fraction * whole, when stated

    def key(self) -> tuple:
        return ("subset", self.part, self.whole)

    def value_part(self) -> Any:
        return self.fraction


@dataclass(frozen=True)
class Quantity(Fact):
    entity: str
    measure: str  # what is counted/measured (noun lemma)
    value: float
    verb: str = "have"  # the stating verb's lemma (state vs event matters)
    time: str | None = None  # a time node's label, when timestamped
    # None for a STATE quantity (a holding — same-key disagreement is a
    # conflict); the sentence index for an EVENT (each occurrence is its own
    # fact: "finds 3 … finds 5" accumulates, never collides)
    occurrence: int | None = None

    @property
    def is_state(self) -> bool:
        return self.occurrence is None

    def key(self) -> tuple:
        return ("quantity", self.entity, self.measure, self.verb, self.time, self.occurrence)

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class Relation(Fact):
    """subject = factor * standard + offset (measure-scoped)."""

    subject: str
    standard: str
    measure: str
    factor: float = 1.0
    offset: float = 0.0
    verb: str = "have"

    def key(self) -> tuple:
        return ("relation", self.subject, self.standard, self.measure, self.verb)

    def value_part(self) -> Any:
        return (self.factor, self.offset)


@dataclass(frozen=True)
class Before(Fact):
    earlier: str
    later: str

    def key(self) -> tuple:
        return ("before", self.earlier, self.later)


# ---------------------------------------------------------------------------
# Reading — one sentence's workspace.
# ---------------------------------------------------------------------------


class Reading:
    """The per-sentence workspace. `record()` is the single mutation door."""

    def __init__(self, text: str, sentence_index: int = 0):
        self.text = text
        self.sentence_index = sentence_index
        self.units: list[Unit] = []
        self.decisions: list[Decision] = []
        self.facts: list[Fact] = []
        self._next_uid = 0

    # -- construction -------------------------------------------------------

    def new_unit(self, words: tuple[Word, ...], features: dict[str, Any] | None = None) -> Unit:
        unit = Unit(self._next_uid, words, features)
        self._next_uid += 1
        return unit

    # -- the mutation chokepoint --------------------------------------------

    def record(
        self,
        kind: str,
        target: Unit,
        changes: dict[str, Any],
        reason: str,
        rule_id: str | None = None,
    ) -> Decision:
        """Apply `changes` to target.features, logging a reversible diff."""
        before = {k: copy.deepcopy(target.features.get(k)) for k in changes}
        target.features.update(changes)
        after = {k: copy.deepcopy(target.features.get(k)) for k in changes}
        decision = Decision(
            seq=len(self.decisions),
            kind=kind,
            target_uid=target.uid,
            before=before,
            after=after,
            reason=reason,
            rule_id=rule_id,
            target_surface=target.surface,
        )
        self.decisions.append(decision)
        return decision

    def undo(self, decision: Decision) -> None:
        unit = self.unit(decision.target_uid)
        for key, val in decision.before.items():
            if val is None and key not in decision.after:
                unit.features.pop(key, None)
            else:
                unit.features[key] = copy.deepcopy(val)

    # -- accessors -----------------------------------------------------------

    def unit(self, uid: int) -> Unit:
        for u in self.units:
            if u.uid == uid:
                return u
        raise KeyError(uid)

    def iter_units(self) -> Iterator[Unit]:
        return iter(self.units)

    def unknown_words(self) -> list[str]:
        return [u.surface for u in self.units if u.features.get("unknown")]

    def deficiencies(self) -> list[str]:
        """Human-readable statements of what stops this reading being complete."""
        out: list[str] = []
        for u in self.units:
            if u.features.get("unknown"):
                out.append(f"I have no information about the word '{u.surface}'.")
            for ob in u.unmet():
                out.append(
                    f"'{u.surface}' ({ob.role}) needs a {ob.need} and none was found."
                )
        return out

    @property
    def saturated(self) -> bool:
        return not any(u.unmet() for u in self.units) and not any(
            u.features.get("unknown") for u in self.units
        )
