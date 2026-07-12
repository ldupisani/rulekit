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
    # the possessive owner of `entity`, when the subject was merged from
    # "OWNER 's NOUN" (condense.py merge-possessive) — NOT part of key() or
    # value_part(): identity stays the bare entity lemma everywhere it
    # already worked (cross-mention folding, e.g. "Tom's dog ... the dog
    # ..."). Read ONLY by FactStore.admit's collision handling, to split a
    # genuine same-key VALUE conflict ("Kennedy's house" vs "Benedict's
    # house", both bare-folding to entity='house') into two entities —
    # never to change identity absent a real conflict.
    owner: str | None = None
    # the attributive modifier of `entity`, when the subject noun was
    # merged from ADJECTIVE+NOUN or NOUN+NOUN (condense.py merge-attribute
    # / merge-compound: "coconut trees" / "mango trees") — the second,
    # independent qualifier field beside `owner` (increment 25's mirror).
    # NOT part of key() or value_part(): identity stays the bare entity
    # lemma everywhere it already worked (bare-noun folding is untouched,
    # e.g. "the tree ... it ..." keeps folding into one entity). Read
    # ONLY by FactStore.admit's collision handling, to split a genuine
    # same-key VALUE conflict ("coconut tree" vs "mango tree", both
    # bare-folding to entity='tree') into two entities — never to change
    # identity absent a real conflict.
    qualifier: str | None = None

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
class FractionQuantity(Fact):
    """'ate HALF of the sandwiches' — a fraction of the definite pool (the
    unique STATE quantity of the measure). Resolved to an event Quantity by
    the fraction synthesizer; UNRESOLVED ones veto any commit (a silently
    dropped 'half' is a confident-wrong factory)."""

    entity: str
    measure: str
    fraction: float
    verb: str = "have"
    occurrence: int | None = None
    time: str | None = None

    def key(self) -> tuple:
        return ("fraction_quantity", self.entity, self.measure, self.verb,
                self.occurrence, self.time)

    def value_part(self) -> Any:
        return self.fraction


@dataclass(frozen=True)
class RestQuantity(Fact):
    """'He picked THE REST' — the remainder of the unique pool after its
    events. Resolved by the rest synthesizer; unresolved ones veto."""

    entity: str
    verb: str
    occurrence: int | None = None
    time: str | None = None

    def key(self) -> tuple:
        return ("rest_quantity", self.entity, self.verb, self.occurrence, self.time)


@dataclass(frozen=True)
class PartitionQuantity(Fact):
    """'Ten of THEM are yellow' — N members of a prior collection share an
    attribute. `collection` starts as the plural pronoun's raw word ('them'/
    'these'/'those') and the partition synthesizer resolves it to the
    collection's actual measure via the same unique-pool-in-play principle
    FractionQuantity's pronoun form uses; an unresolved one (ambiguous or
    absent prior collection) vetoes any commit.

    `kind` distinguishes the ADJECTIVE form ("...are yellow", the default)
    from the MEMBERSHIP form ("8 of them are dogs" — `attribute` is a plural
    common noun naming a subset of the collection, not a modifier of it).
    The membership form additionally drives a companion Quantity synth (see
    saturate.py) so the general entity-less "how many NOUN are there" ask
    answers it directly, with no bespoke consumer.

    `is_fraction` marks a FRACTIONAL partition ("25%"/"half" OF THEM are
    ADJ|NOUN, the pattern's PREMISE-side counterpart to `is_fraction=False`'s
    stated cardinal): `value` starts as the raw fraction (0-1), and the
    collection synthesizer — once it resolves the pronoun to the real prior
    collection, exactly as the cardinal form does — additionally multiplies
    that fraction against the collection's own total before re-emitting, at
    which point the resolved fact carries a real count and `is_fraction`
    goes back to False. An unresolvable total (ambiguous or absent pool)
    leaves it unresolved, same decline discipline as fraction-of-pool.

    EXISTENCE, not use, counts as "read" for value accounting (like Quantity/
    FractionQuantity, unlike Rate/Price): this fact IS the captured stated
    count, not a dormant multiplier that arithmetic must actively consult —
    a partition mentioned but irrelevant to the asked attribute is exactly
    like an entity's quantity irrelevant to a different entity's question."""

    collection: str
    attribute: str
    value: float
    verb: str = "be"
    polarity: bool = True
    kind: str = "adjective"
    is_fraction: bool = False

    def key(self) -> tuple:
        return ("partition_quantity", self.collection, self.attribute, self.verb)

    def value_part(self) -> Any:
        return (self.value, self.polarity)


@dataclass(frozen=True)
class Rate(Fact):
    """'makes $18 an hour' / '4 cars a day' — value of measure PER unit.
    Informative on its own (never folds into holdings); the rate-span
    consumer multiplies it against an asked span.

    `numerator`/`denominator` are set ONLY for a COMPOUND rate stated as
    two numbers ("8 pages in 20 minutes" -> numerator=8, denominator=20,
    value=8/20) rather than the simple per-unit article form ("4 cars a
    day" -> value=4, numerator/denominator left None). `value` is always
    the per-ONE-unit quotient either way, read identically by every
    existing consumer — the split fields exist ONLY so value-accounting
    (guards.py) can credit the text's own TWO stated numbers as read when
    a consumer's arithmetic actually uses them; a consumer that instead
    multiplies/divides by the bare `value` never touches either raw
    number and value-accounting correctly declines rather than commit
    around them unread."""

    entity: str
    measure: str
    per: str  # the unit noun's lemma ("hour", "day")
    value: float
    verb: str = "make"
    occurrence: int | None = None
    numerator: float | None = None
    denominator: float | None = None

    def key(self) -> tuple:
        return ("rate", self.entity, self.measure, self.per, self.verb, self.occurrence)


@dataclass(frozen=True)
class Price(Fact):
    """'3 toys at $10 each' — the per-unit PRICE of an item. Distinct from
    Rate: the quantity purchased is its own ordinary Quantity fact (not a
    rate over time); the purchase-total consumer multiplies the two."""

    item: str
    value: float
    verb: str = "buy"
    occurrence: int | None = None

    def key(self) -> tuple:
        return ("price", self.item, self.verb, self.occurrence)

    def value_part(self) -> Any:
        return self.value

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class Goal(Fact):
    """'Lena wants to collect 30 stamps' — a stated TARGET quantity, not a
    holding or an event. USE-GATED for value accounting, like Rate/Price:
    a goal that merely EXISTS has not been read — only the deficit consumer
    actually subtracting a holding from it counts as use (a wanted purchase
    is not a purchase, the increment-14 kirsty lesson generalized to
    desire verbs). `verb` records the stated desire verb ('want'); the
    target action verb ('collect') is deliberately NOT captured here — the
    goal is the quantity, not the activity."""

    entity: str
    measure: str
    value: float
    verb: str = "want"

    def key(self) -> tuple:
        return ("goal", self.entity, self.measure)

    def value_part(self) -> Any:
        return self.value


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
