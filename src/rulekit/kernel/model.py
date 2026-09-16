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
from .reference_identity import ReferenceIdentity, flat_reference

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
    if isinstance(value, (ReferenceIdentity, ItemClassReference)):
        return value.to_dict()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Obligation):
        target = value.target
        if target is PATTERN:
            target = "<pattern>"
        else:
            # Group reference binds one obligation to a tuple of Units. Reuse
            # the recursive projection so neither a single nor grouped target
            # can leak a live Unit into an API trace.
            target = _jsonable(target)
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
    # Was the fact's SUBJECT scoped by a distributive determiner ('each'/'every'
    # box has 8 pens)? Metadata only — NOT part of any Fact.key(), so it never
    # affects dedup/conflict. saturate's distributive-container-total synth reads
    # it to tell a genuine PER-CONTAINER rate ('each box has 8 pens') from a
    # SPECIFIC instance's count ('bucket B has 30 seeds', 'the first warehouse
    # has 400 boxes') that folds to the identical (container, content) shape —
    # the conflation that produced garbage group totals (bucket seed=90,
    # warehouse box=800). Defaulted False: every non-fold provenance is unchanged.
    distributive: bool = False
    # True when a grammar rule explicitly emits a holder's count of
    # containers/packages. Ordinary folds remain eligible through their
    # historical source marker; rule-emitted quantities must opt in so a
    # rate-defining holder such as a video section cannot accidentally become
    # a package count merely because its measure belongs to a broad container
    # category.
    container_count: bool = False
    # True only when this fact depends on a clause promoted from the current
    # question's conditional frame ("If X, how many ...?"). Metadata only,
    # never part of a Fact.key(); omitted from repr so ordinary fact snapshots
    # remain stable.
    assumption: bool = field(default=False, repr=False)
    # The temporal perspective under which this fact is asserted. This is
    # evidence metadata, not part of Fact.key(): ``Bira was 20`` and ``Bira
    # is 20`` still describe the same quantity key and therefore conflict if
    # both are asserted without a rule explaining the change. Ask dispatch
    # may, however, require evidence from the matching perspective rather
    # than silently treating past, present, and future statements alike.
    temporal_perspective: str | None = field(default=None, repr=False)


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
    # The object exists in an unstated quantity: either a bare quantifier
    # ("has SOME blocks") or a declarative rule that explicitly preserves an
    # unquantified object. Total folds must not silently omit its unknown
    # amount. Deliberately NOT part of key(): quantifiedness
    # is evidence ABOUT the same predication, not a different fact — two
    # mints differing only here must still dedupe, never quarantine.
    dobj_unquantified: bool = False
    subject_ref: ReferenceIdentity | None = field(default=None, metadata={"reference_for": "subject"})

    def __post_init__(self):
        if self.subject_ref is None:
            object.__setattr__(self, "subject_ref", flat_reference(self.subject))

    def key(self) -> tuple:
        key = ("predication", self.subject, self.verb, self.dobj)
        return key + ((self.subject_ref.key(),) if self.subject_ref.described else ())

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
class Atom(Fact):
    """A ground proposition keyed by its FULL canonical phrase, never a lemma
    head. "Tom is a citizen of Lawton Park" -> ('tom', 'citizen of lawton
    park'), NOT ('tom', 'citizen'): FOLIO-style logic prose distinguishes
    classes one NP-internal word apart ("devices belonging to the company" vs
    "... to employees"), and a head-lemma key would make them one class — the
    Fiedler trap ("Czech mathematician" premise silently answering a "French
    mathematician" question). The phrase is per-token lemma-normalized only;
    no semantic loosening.

    Read semantics (the every-new-fact-kind decision): the emitting rule
    CONSUMES the span's units, so consumption — not existence or use — is
    what marks the sentence read; the fragment guard (guards.py) audits the
    units no logic rule consumed."""

    entity: str
    pred: str
    polarity: bool = True
    # True when the emitting span swallowed an INDEFINITE article ('a'/'an')
    # — the pred describes SOME object, not a particular one. Articles are
    # skippable senses and drop out of the phrase key, so 'plays for a
    # football club' and 'plays for THE football club' share one key; this
    # bit is what lets a consumer refuse the unsound cell of that matrix
    # (indefinite premise answering a definite-description question —
    # composition-design.md Phase 0). Deliberately NOT part of key() or
    # value_part(): two atoms differing only here are one fact, and either
    # dedup survivor is safe — a definite survivor answers (sound), an
    # indefinite survivor makes the definite question decline (monotone).
    indef_obj: bool = False

    def key(self) -> tuple:
        return ("logic-atom", self.entity, self.pred)

    def value_part(self) -> Any:
        return self.polarity


@dataclass(frozen=True)
class VerbalRelation(Fact):
    """A verbal predication whose DIRECT OBJECT is held structurally —
    the composition frontier's premise form (composition-design.md §2.2):
    "John Nash designed Oxford Circus" -> ('john nash', 'design', obj=
    'oxford circus'). Emitted BESIDE the flat Atom (whose one phrase key
    stays echo-exact and untouched); segmentation happens only in the
    emitting rule's match tokens, never by splitting a key string. `prep`
    is reserved for the PP form ("plays for Náutico") and stays '' for
    direct objects. Bridges (membership on the agent, later containment)
    run at QUERY time in consumers — no derived facts, no key surgery."""

    entity: str
    verb: str
    obj: str
    prep: str = ""
    # Optional semantic role licensed by a declarative verb–preposition–object
    # category triple. Empty on the older exact logic relations, whose packs
    # preserve the surface but make no role commitment.
    role: str = ""
    polarity: bool = True
    # same contract as Atom.indef_obj: the obj span swallowed an 'a'/'an',
    # so the object is SOME thing, never a particular referent — it must
    # not match a question's definite entity
    indef_obj: bool = False
    # Runtime-local predicate occurrence shared with EventTime and any
    # event-derived fluent evidence.  Pattern-emitted legacy relations leave
    # this unset; fold-derived governed relations always carry it.  Without a
    # shared identity, two same-verb events in one sentence cannot be joined
    # to their own time safely.
    event: str | None = None

    def key(self) -> tuple:
        return (
            "verbal-rel",
            self.entity,
            self.verb,
            self.prep,
            self.obj,
            self.role,
            self.event,
        )

    def value_part(self) -> Any:
        return self.polarity


@dataclass(frozen=True)
class SemanticGraphNode(Fact):
    """One first-class node in the structured semantic view.

    ``ref`` is a runtime-local identity supplied by the construction
    (``name:...``, ``entity:...``, or ``event:...``), never a benchmark
    variable.  Source spans remain metadata: they make the projection
    inspectable without changing semantic identity or conflict behavior.
    """

    ref: str
    kind: str
    span_start: str = ""
    span_end: str = ""

    def key(self) -> tuple:
        return (
            "semantic-node",
            self.provenance.sentence,
            self.ref,
            self.kind,
        )


@dataclass(frozen=True)
class SemanticGraphEdge(Fact):
    """One typed edge over ``SemanticGraphNode`` identities."""

    kind: str
    source: str
    target: str = ""
    label: str = ""
    span_start: str = ""
    span_end: str = ""

    def key(self) -> tuple:
        return (
            "semantic-edge",
            self.provenance.sentence,
            self.kind,
            self.source,
            self.target,
            self.label,
        )


@dataclass(frozen=True)
class Conditional(Fact):
    """A class-scoped implication read from a copular if-then sentence:
    "If a X is P, then it is [not] Q" -> Conditional(cls='x', pred='p',
    then_pred='q', polarity). Semantics: ∀e. e∈cls ∧ pred(e) → [¬]then_pred(e).

    Soundness boundaries (Stage 1, projects/scratch/ROADMAP.md):
    - Both antecedent conjuncts are queried POSITIVELY by the synth
      (synth/conditional-instantiation, packs/logic) — a negated-antecedent
      surface never matches an extraction rule, so its sentence stays whole-
      unread, which is monotone-safe.
    - cls and pred sit in DOWNWARD-monotone positions: they never decompose
      and never loosen; only exact atom phrases satisfy them. then_pred is
      the upward-monotone consequent and inherits Atom's phrase discipline.
    - A name-subject conditional ("If Rex is hungry, then it is ...") reads
      the name as a CLASS phrase — inert unless some premise asserts
      membership in that class, which is the compositional reading of that
      (unusual) English.

    Read semantics (the every-new-fact-kind decision): as Atom — the
    emitting rule consumes the whole construction's units or matches
    nothing; the fragment guard audits what no rule consumed."""

    cls: str
    pred: str
    then_pred: str
    polarity: bool = True

    def key(self) -> tuple:
        return ("logic-conditional", self.cls, self.pred, self.then_pred)

    def value_part(self) -> Any:
        return self.polarity


@dataclass(frozen=True)
class Disjunction(Fact):
    """A ground disjunction: x ∈ left ∨ right (inclusive) or left ⊕ right
    (exclusive). The `exclusive` flag is SURFACE-DECIDED, and the mapping is
    MEASURED from folio DEV golds (Stage 3, ROADMAP.md): bare 'or' is
    INCLUSIVE ("Heinrich Schmidt was German or Russian or both" golds True);
    'either...or' is EXCLUSIVE (the James minimal pair: same story, same
    disjuncts, bare-or conclusion golds True while the either-or conclusion
    golds False — both disjuncts hold; also the banked TikTok witness).

    Disjuncts are NOT in _DECOMPOSABLE_FIELDS and never decompose: XOR is
    non-monotone in both arguments, so stripping inside a disjunct is
    unsound for exclusive facts and stays off for both. Negated disjunctive
    surfaces are unread entirely (scope-ambiguous English)."""

    entity: str
    left: str
    right: str
    exclusive: bool = False

    def key(self) -> tuple:
        return ("logic-disj", self.entity, self.left, self.right)

    def value_part(self) -> Any:
        return self.exclusive


@dataclass(frozen=True)
class Equivalence(Fact):
    """A ground equivalence between two predicates of one named entity.

    The sole text reader is the narrow logic-pack construction
    ``X is either [both] A and B, or [PRONOUN is] neither``. That surface
    denotes ``A(X) ↔ B(X)``: knowing either predicate true licenses the
    other true, and knowing either explicitly false licenses the other
    false. The fact itself asserts neither side, preserving open-world
    behavior until another premise or a reductio hypothesis supplies one.

    ``left`` and ``right`` never decompose. They are exact Atom phrase keys;
    only the equivalence synth rules transfer an already established
    polarity between them.
    """

    entity: str
    left: str
    right: str

    def key(self) -> tuple:
        return ("logic-equivalence", self.entity, self.left, self.right)

    def value_part(self) -> Any:
        return True


@dataclass(frozen=True)
class Existential(Fact):
    """∃e. e ∈ cls ∧ [¬]pred(e) — "Some dogs are [not] pets". Emitted by the
    'some' extraction rules (which CONSUME the quantifier, relaxing the
    fragment guard's veto by capability, exactly as its docstring promises).
    The consumer answers 'yes' from an echo or a WITNESS (an entity holding
    both atoms — ∃-introduction at query time, no synth); 'no' ONLY from a
    matching NEGATIVE universal (∀¬ refutes ∃ soundly); everything else is
    'undetermined' — open world, no existential import from positive
    universals (classical FOL: "all dogs are animals" does not prove a dog
    exists)."""

    cls: str
    pred: str
    polarity: bool = True

    def key(self) -> tuple:
        return ("logic-exis", self.cls, self.pred)

    def value_part(self) -> Any:
        return self.polarity


@dataclass(frozen=True)
class Alias(Fact):
    """A stated identity between two NAMES: "Edwin Smith was also known as
    Ted Smith" asserts the two names refer to one individual, so every
    ground Atom of either carries over to the other (synth/alias-copy-*,
    both directions — identity is symmetric).

    Deliberately narrow (Stage 9e): only the overt 'known as' construction
    with a PROPER NAME on each side ever mints one from TEXT. Epithets
    ("known as THE King of Pop" — refused by the definite-article gate on
    the alias slot) stay unbuilt. Name-shortening ('Islip' for 'Islip
    Speedway') is Stage 9j's saturate plugin (synth/name-prefix-alias):
    an INFERENCE, gated on both names being fact subjects and the long
    extension being unique — see its docstring for the boundary."""

    a: str
    b: str

    def key(self) -> tuple:
        return ("logic-alias", self.a, self.b)

    def value_part(self) -> Any:
        return True


@dataclass(frozen=True)
class QuantifiedDisjunction(Fact):
    """A class-scoped disjunction: ∀e ∈ cls. e ∈ left ∨/⊕ right ("Every pet
    is a dog or a cat"). Instantiates to a ground Disjunction per member
    (synth/qdisj-instantiation). Same surface-decided exclusivity and the
    same no-decomposition rule as Disjunction."""

    cls: str
    left: str
    right: str
    exclusive: bool = False

    def key(self) -> tuple:
        return ("logic-qdisj", self.cls, self.left, self.right)

    def value_part(self) -> Any:
        return self.exclusive


@dataclass(frozen=True)
class DisjunctiveConditional(Fact):
    """A GROUND conditional whose antecedent is a two-way disjunction over
    one named entity: "If Bubbles is either an osprey or a goldfish, then
    Bubbles is not also a fish" -> (osprey(b) ⊕ goldfish(b)) → ¬fish(b).
    `exclusive` carries Disjunction's surface-decided reading ('either…or'
    = ⊕, Stage 3's James minimal pair).

    Fired ONLY by the exactly-one synths (synth/disj-conditional-fire-*):
    one disjunct true AND the other explicitly false establishes the
    antecedent under BOTH readings (⊕ needs exactly one; L∧¬R satisfies
    L∨R too), so no exclusivity gate is needed at fire time. A single
    true disjunct with the other UNDECIDED fires nothing — under ⊕ the
    antecedent is not yet established, and reading it as ∨ to fire early
    is exactly the confident-wrong the Stage 3 measurement forbids.

    Disjuncts and consequent never decompose (not in _DECOMPOSABLE_FIELDS):
    the antecedent sides are non-monotone under ⊕, and the consequent may
    carry polarity false, where stripping widens the denial."""

    entity: str
    left: str
    right: str
    then_pred: str
    then_polarity: bool = True
    exclusive: bool = False

    def key(self) -> tuple:
        return ("logic-disj-conditional", self.entity, self.left,
                self.right, self.then_pred)

    def value_part(self) -> Any:
        return (self.then_polarity, self.exclusive)


@dataclass(frozen=True)
class GroundConditional(Fact):
    """A GROUND implication over one named entity whose antecedent is a
    NEGATED predicate — the negative-antecedent same-entity conditional
    (Phase B reader 6): "If Marvin is not from Earth, then Marvin is an
    extraterrestrial" -> ¬from-earth(m) → extraterrestrial(m). The negation
    is STRUCTURAL (the reading consumes 'not' as skeleton), so `pred` holds
    the plain predicate P of ¬P(e); there is deliberately no antecedent-
    polarity field — a positive COPULAR antecedent ground surface ("If Nancy
    is a teacher, ...") already reads as a name-classed Conditional and must
    not acquire a second representation here. Reader 47's positive
    POSSESSION construction instead uses PositiveGroundConditional below.

    Same-entity by construction: the repeated-name surface is pinned by
    `same_lemma`, the anaphoric surface consumes the grammatically bound
    subject pronoun as skeleton. A DIFFERENT name in the consequent is a
    cross-entity conditional and stays whole-unread (monotone-safe).

    Fired only by synth/ground-conditional-fire on an EXPLICIT negative
    atom of the same entity and pred; an undecided antecedent fires
    nothing (open world). Neither `pred` nor `then_pred` decomposes (not
    in _DECOMPOSABLE_FIELDS): the antecedent position is non-monotone
    under the structural negation, and the consequent may carry
    then_polarity false, where stripping widens the denial."""

    entity: str
    pred: str
    then_pred: str
    then_polarity: bool = True

    def key(self) -> tuple:
        return ("logic-ground-conditional", self.entity, self.pred,
                self.then_pred)

    def value_part(self) -> Any:
        return self.then_polarity


@dataclass(frozen=True)
class PositiveGroundConditional(Fact):
    """A positive-antecedent implication over one named entity.

    ``If Orion has a velvet badge, then Orion is a patient artist`` becomes
    ``have velvet badge(Orion) -> patient artist(Orion)``.  This is separate
    from :class:`GroundConditional`, whose antecedent is structurally
    NEGATED: the two constructions have different firing evidence and must
    not share a defaulted polarity field.

    Both predicate positions are exact atomic phrase keys.  The antecedent
    never decomposes; only an explicit positive Atom with the complete key
    fires the implication.  Same-entity identity is proved by the emitting
    rule's repeated-name ``same_lemma`` gate.
    """

    entity: str
    pred: str
    then_pred: str
    then_polarity: bool = True

    def key(self) -> tuple:
        return (
            "logic-positive-ground-conditional",
            self.entity,
            self.pred,
            self.then_pred,
        )

    def value_part(self) -> Any:
        return self.then_polarity


@dataclass(frozen=True)
class EnumeratedDisjunction(Fact):
    """An EXHAUSTIVE n-way class disjunction licensed by a COUNTED
    enumeration: "There are six types of wild turkeys: A, B, …, and F"
    with exactly six listed segments -> ∀e ∈ cls. e ∈ o₁ ∨ … ∨ oₙ.
    INCLUSIVE only — the count licenses exhaustiveness ("there are six"
    + six listed = the list is the whole class), never pairwise
    exclusivity, so the only sound consumer is n-way elimination
    (synth/enumeration-elimination: all options but one refuted for a
    member ⊢ the last), never "member of one ⊢ not the others".

    Minted ONLY when the stated count equals the segment count —
    patterns.py enforces it at emit and a mismatched enumeration emits
    nothing (fail closed; a partial list claims nothing). Options carry
    Atom's phrase-key discipline and sit in a DOWNWARD-monotone position:
    they never decompose and never loosen (not in _DECOMPOSABLE_FIELDS).

    The key is the CLASS alone: two different exhaustive enumerations of
    one class are a genuine disagreement, and the store's collision
    machinery quarantining both is the correct reading (decline)."""

    cls: str
    options: tuple[str, ...]

    def key(self) -> tuple:
        return ("logic-enum-disj", self.cls)

    def value_part(self) -> Any:
        return self.options


@dataclass(frozen=True)
class Quantified(Fact):
    """A universally quantified statement over a class phrase: "All citizens
    of Lawton Park use the zip code 98199" -> Quantified('citizen of lawton
    park', 'use the zip code 98199', True); "No X are Y" is the same shape
    with polarity False. Same phrase-key discipline as LogicAtom. Contradictory
    universals ("All X are Y" / "No X are Y") share a key and differ in
    value_part -> the store's collision machinery quarantines both, which is
    the correct reading of contradictory premises: decline."""

    cls: str
    pred: str
    polarity: bool = True

    def key(self) -> tuple:
        return ("quantified", self.cls, self.pred)

    def value_part(self) -> Any:
        return self.polarity


@dataclass(frozen=True)
class QuantifiedQuantity(Fact):
    """A class-wide numeric holding.

    ``All teachers at the university have 20 students`` is represented as
    one exact class phrase plus the ordinary arithmetic measure/value/verb
    fields.  It is deliberately separate from :class:`Quantified`: a numeric
    amount is not an opaque predicate phrase, and arithmetic consumers must
    receive a real :class:`Quantity` only after class membership is proven.
    """

    cls: str
    measure: str
    value: float
    verb: str = "have"

    def key(self) -> tuple:
        return ("quantified-quantity", self.cls, self.measure, self.verb)

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class QuantifiedAdjustment(Fact):
    """A class-wide additive adjustment awaiting one inherited baseline.

    ``All head teachers have 5 more students`` does not state an independent
    holding and does not name an entity-to-entity comparison standard.  It
    therefore remains first-class until an exact member, a declared class
    refinement, and one compatible :class:`QuantifiedQuantity` jointly supply
    the missing baseline.  Conflicting offsets for the same class and measure
    collide in the ordinary fact store rather than being ordered.
    """

    cls: str
    measure: str
    offset: float
    verb: str = "have"

    def key(self) -> tuple:
        return ("quantified-adjustment", self.cls, self.measure, self.verb)

    def value_part(self) -> Any:
        return self.offset


@dataclass(frozen=True)
class ClassRefinement(Fact):
    """One declared class is a subsective refinement of another.

    ``head teacher -> teacher`` is the motivating shape.  This is not an
    intersective assertion: it says nothing about membership in ``head``, and
    it is deliberately separate from ordinary right-headed compound folding.
    Only a pack-declared refining modifier may create this fact.
    """

    subclass: str
    superclass: str

    def key(self) -> tuple:
        return ("class-refinement", self.subclass)

    def value_part(self) -> Any:
        return self.superclass


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
class AgeAtYear(Fact):
    """One entity's stated age at an absolute calendar-year coordinate.

    This is deliberately not a timestamped :class:`Quantity`.  A dated age
    may be projected because age advances with elapsed years; an arbitrary
    dated quantity may not.  Keeping the source coordinate first-class also
    prevents a lone dated age from leaking into an undated ``how old`` ask.

    The identity qualifiers mirror ``Quantity`` sufficiently to keep
    same-headed people distinct.  Pattern templates render a missing optional
    feature as ``""``; normalizing that representation here keeps fact keys
    and Designer output honest.
    """

    entity: str
    measure: str
    value: float
    year: float
    verb: str = "be"
    owner: str | None = None
    qualifier: str | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("owner", "qualifier", "label"):
            if getattr(self, field_name) == "":
                object.__setattr__(self, field_name, None)

    def key(self) -> tuple:
        return (
            "age-at-year",
            self.entity,
            self.owner,
            self.qualifier,
            self.label,
            self.measure,
            self.year,
        )

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class TaskCompletionDuration(Fact):
    """One participant's exact elapsed duration for completing one task.

    This is intentionally separate from :class:`Quantity`: an elapsed time
    is neither a holding nor an additive event amount.  The declared unit is
    preserved so the dedicated comparative consumer can use the registry's
    conversion graph without widening ordinary quantity folds to durations.
    """

    participant: str
    task: str
    elapsed: float
    unit: str
    verb: str

    def key(self) -> tuple:
        return ("task-completion-duration", self.participant, self.task)

    def value_part(self) -> Any:
        return (self.elapsed, self.unit, self.verb)


@dataclass(frozen=True)
class RateThreshold(Fact):
    """A policy boundary per session, never a performed duration."""

    entity: str
    activity: str
    unit: str
    value: float
    period: str
    tier: str

    def key(self) -> tuple:
        return ("rate-threshold", self.entity, self.tier, self.provenance.sentence)

    def value_part(self) -> Any:
        return (self.activity, self.unit, self.value, self.period)


@dataclass(frozen=True)
class RatePremium(Fact):
    """A tier's additive fraction of a described base rate."""

    tier: str
    basis: str
    descriptor: str
    fraction: float

    def key(self) -> tuple:
        return ("rate-premium", self.tier, self.provenance.sentence)

    def value_part(self) -> Any:
        return (self.basis, self.descriptor, self.fraction)


@dataclass(frozen=True)
class RepeatedActivityDuration(Fact):
    """Per-period activity duration and a separate explicit repeat count."""

    entity: str
    activity: str
    elapsed: float
    unit: str
    period: str
    value: float

    def key(self) -> tuple:
        return ("repeated-activity-duration", self.entity, self.activity,
                self.provenance.sentence)

    def value_part(self) -> Any:
        return (self.elapsed, self.unit, self.period, self.value)


@dataclass(frozen=True)
class EventCadence(Fact):
    """One carrier event per interval, not a constant quantity rate."""

    entity: str
    verb: str
    series: str
    value: float
    elapsed: float
    unit: str
    entity_qualifier: str = ""

    def key(self) -> tuple:
        return ("event-cadence", self.entity, self.series, self.provenance.sentence)

    def value_part(self) -> Any:
        return (self.verb, self.value, self.elapsed, self.unit, self.entity_qualifier)


@dataclass(frozen=True)
class SequenceTotal(Fact):
    """An event amount over a bounded interval, never a per-event holding."""

    entity: str
    verb: str
    measure: str
    value: float
    elapsed: float
    unit: str
    entity_qualifier: str = ""

    def key(self) -> tuple:
        return ("sequence-total", self.entity, self.measure, self.provenance.sentence)

    def value_part(self) -> Any:
        return (self.verb, self.value, self.elapsed, self.unit, self.entity_qualifier)


@dataclass(frozen=True)
class SequenceStep(Fact):
    """Adjacent terms obey next = factor * previous + offset.

    The series is a class of distinct occurrences, not one self-related
    holder. It must never enter the ordinary two-holder Relation solver.
    """

    series: str
    measure: str
    factor: float = 1.0
    offset: float = 0.0

    def key(self) -> tuple:
        return ("sequence-step", self.series, self.measure, self.provenance.sentence)

    def value_part(self) -> Any:
        return (self.factor, self.offset)


ORDERED_SEQUENCE_KINDS = (EventCadence, SequenceTotal, SequenceStep)


@dataclass(frozen=True)
class AccumulationWindow(Fact):
    """A resource-saving interval, not a holding or an initial balance."""

    entity: str
    measure: str
    elapsed: float
    unit: str
    cadence: str
    owner: str = ""

    def key(self):
        return ("accumulation-window", self.entity, self.provenance.sentence)

    def value_part(self):
        return (self.measure, self.elapsed, self.unit, self.cadence, self.owner)


@dataclass(frozen=True)
class EarningRate(Fact):
    """A quoted periodic income or per-service tariff, never earned cash.

    The Rate arithmetic protocol is shared; the distinct fact kind prevents
    ordinary holding/rate consumers from discarding its settlement scope.
    A missing service object remains unresolved until a unique declaration
    links the same actor and activity to an object.
    """

    entity: str
    measure: str
    per: str
    value: float
    verb: str
    basis: str
    source: str = ""
    position: int = 0
    numerator: float | None = None
    denominator: float | None = None

    def key(self):
        return ("earning-rate", self.entity, self.provenance.sentence, self.position)

    def value_part(self):
        return (self.measure, self.per, self.value, self.verb, self.basis, self.source)


@dataclass(frozen=True)
class ServiceScope(Fact):
    """A participant offers an activity on an object; no count is asserted."""

    entity: str
    verb: str
    item: str

    def key(self):
        return ("service-scope", self.entity, self.verb, self.item, self.provenance.sentence)


@dataclass(frozen=True)
class PurchaseEndpoint(Fact):
    """A quoted whole-target cost or cash remaining after its purchase.

    Target units and qualifiers stay separate: a pair is not one shoe.
    The quoted stage alone never establishes that a purchase took place.
    """

    entity: str
    item: str
    qualifier: str
    stage: str
    measure: str
    value: float
    unit: str = ""
    owner: str = ""
    unit_qualifier: str = ""

    def key(self):
        return ("purchase-endpoint", self.entity, self.stage, self.provenance.sentence)

    def value_part(self):
        return (self.item, self.qualifier, self.measure, self.value, self.unit,
                self.owner, self.unit_qualifier)


EARNINGS_ACCOUNT_KINDS = (AccumulationWindow, EarningRate, ServiceScope, PurchaseEndpoint)


@dataclass(frozen=True)
class CommercialTerm(Fact):
    """A scoped quote, not cash held: setup cost, unit cost or sale price.

    A relative sale quote retains its factor until one preceding unit cost
    supplies its reference. An omitted producer or product remains unresolved.
    """

    entity: str
    item: str
    basis: str
    measure: str
    value: float

    def key(self):
        return ("commercial-term", self.entity, self.item, self.basis,
                self.provenance.sentence)

    def value_part(self):
        return (self.measure, self.value)


@dataclass(frozen=True)
class AllocationRatio(Fact):
    """Ordered participants' relative shares of one named allocation.

    This is not a relation between their complete personal cash holdings.
    Raw parts and the declared group size remain source-auditable.
    """

    resource: str
    source: str
    first: str
    second: str
    numerator: float
    denominator: float
    group_size: float

    def key(self):
        return ("allocation-ratio", self.resource, self.source, self.first,
                self.second, self.provenance.sentence)

    def value_part(self):
        return (self.numerator, self.denominator, self.group_size)


@dataclass(frozen=True)
class InventoryScope(Fact):
    """One explicitly enumerated opening inventory, before any withdrawals."""

    container: str
    item: str

    def key(self):
        return ("inventory-scope", self.container, self.item, self.provenance.sentence)

    def value_part(self):
        return ()


@dataclass(frozen=True)
class InventoryWithdrawal(Fact):
    """An actor's absolute or explicitly anchored proportional removal."""

    actor: str
    item: str
    qualifier: str
    value: float | None = None
    factor: float | None = None
    standard_actor: str = ""
    standard_item: str = ""
    standard_qualifier: str = ""

    def key(self):
        return ("inventory-withdrawal", self.actor, self.item, self.qualifier,
                self.provenance.sentence)

    def value_part(self):
        return (self.value, self.factor, self.standard_actor, self.standard_item,
                self.standard_qualifier)


@dataclass(frozen=True)
class JourneyLeg(Fact):
    """One-way cost of an actor's exact route and travel mode."""

    entity: str
    mode: str
    destination: str
    value: float
    unit: str
    destination_owner: str = ""

    def key(self):
        return ("journey-leg", self.entity, self.mode, self.destination, self.provenance.sentence)

    def value_part(self):
        return (self.value, self.unit, self.destination_owner)


@dataclass(frozen=True)
class JourneySchedule(Fact):
    """Explicit repetitions per period, with directions kept separate."""

    entity: str
    mode: str
    destination: str
    value: float
    period: str
    legs: float

    def key(self):
        return ("journey-schedule", self.entity, self.mode, self.destination,
                self.period, self.provenance.sentence)

    def value_part(self):
        return (self.value, self.legs)


@dataclass(frozen=True)
class JourneyExtra(Fact):
    """A complete additional journey distance, not another one-way leg."""

    entity: str
    mode: str
    value: float
    unit: str
    period: str

    def key(self):
        return ("journey-extra", self.entity, self.mode, self.period, self.provenance.sentence)

    def value_part(self):
        return (self.value, self.unit)


@dataclass(frozen=True)
class JourneyPace(Fact):
    """A travel capability quote, not an asserted activity Rate."""

    entity: str
    mode: str
    measure: str
    per: str
    value: float

    def key(self):
        return ("journey-pace", self.entity, self.mode, self.provenance.sentence)

    def value_part(self):
        return (self.measure, self.per, self.value)


JOURNEY_KINDS = (JourneyLeg, JourneySchedule, JourneyExtra, JourneyPace)


@dataclass(frozen=True)
class RateScope(Fact):
    """The activity to which one participant's stated rate applies.

    ``Natalia earns $12 an hour for gardening`` does not license applying
    that rate to every elapsed duration associated with Natalia.  This fact
    preserves the explicit ``for ACTIVITY`` restriction independently of the
    numeric :class:`Rate`, so consumers can require an exact activity match.
    """

    participant: str
    activity: str
    verb: str

    def key(self) -> tuple:
        return ("rate-scope", self.participant, self.verb)

    def value_part(self) -> Any:
        return self.activity


@dataclass(frozen=True)
class ActivityDuration(Fact):
    """One participant's elapsed time spent on a named activity.

    This is not a Quantity holding: ``50 minutes of gardening`` records a
    duration qualified by an activity.  Keeping the unit and temporal label
    explicit permits ordinary conversion while preventing the duration from
    being borrowed by an unrelated rate.
    """

    participant: str
    activity: str
    elapsed: float
    unit: str
    verb: str
    time: str | None = None

    def key(self) -> tuple:
        return (
            "activity-duration",
            self.participant,
            self.activity,
            self.verb,
            self.time,
        )

    def value_part(self) -> Any:
        return (self.elapsed, self.unit)


@dataclass(frozen=True)
class ResourceAllocation(Fact):
    """An amount-bearing account phrase, before it has an event or owner.

    Source spans identify the exact grammatical head and amount. Recognizing
    this phrase alone does not establish whose allocation it is.
    """

    account: str
    measure: str
    value: float
    head_span: str
    amount_span: str
    owner: str = ""
    qualifier: str = ""
    amount_owner: str = ""

    def key(self) -> tuple:
        return ("resource-allocation", self.provenance.sentence, self.head_span)

    def value_part(self) -> Any:
        return (self.account, self.owner, self.amount_owner, self.qualifier, self.measure, self.value, self.amount_span)


@dataclass(frozen=True)
class ResourceBalance(Fact):
    """An explicit opening allocation or its closing remainder.

    The account label and participant must agree before a consumer may use
    these as the two endpoints of a conservation equation.
    """

    entity: str
    account: str
    stage: str
    measure: str
    value: float
    owner: str = ""
    qualifier: str = ""
    allocation_span: str = ""
    event: int = -1

    def key(self) -> tuple:
        return ("resource-balance", self.entity, self.account, self.qualifier, self.owner, self.stage,
                self.provenance.sentence)

    def value_part(self) -> Any:
        return (self.measure, self.value, self.allocation_span, self.event)


@dataclass(frozen=True)
class Expenditure(Fact):
    """A total resource cost tied to a purchase target, never a unit price.

    An actual purchase may leave its cost unstated (value and measure None).
    Position distinguishes repeated costs even within the same sentence.
    """

    entity: str
    item: str
    verb: str
    value: float | None = None
    measure: str | None = None
    qualifier: str = ""
    position: int = 0
    event: int = 0
    basis: str = "purchase"
    supplier: str = ""
    supplier_qualifier: str = ""
    channel: str = ""
    account: str = ""
    account_qualifier: str = ""
    account_owner: str = ""
    account_span: str = ""
    # A counted purchase with an explicit per-unit price is not a stated
    # total. Keep both operands and their source positions until used.
    quantity: float | None = None
    unit_price: float | None = None
    quantity_position: int = -1
    # A whole-lot price does not multiply by its descriptive mass/count.
    lot_measure: str = ""
    lot_quantity: float | None = None
    lot_position: int = -1
    # A relative price points to one other purchase by this participant.
    cost_reference: str = ""
    cost_reference_qualifier: str = ""
    cost_factor: float | None = None
    cost_factor_position: int = -1
    # False when the list or buyer identity is not fully represented.
    complete: bool = True

    def key(self) -> tuple:
        return ("expenditure", self.entity, self.provenance.sentence,
                self.position, self.item, self.qualifier)

    def value_part(self) -> Any:
        return (self.verb, self.measure, self.value, self.basis, self.supplier,
                self.supplier_qualifier, self.channel, self.account,
                self.account_qualifier, self.account_owner, self.account_span,
                self.quantity, self.unit_price, self.quantity_position,
                self.lot_measure, self.lot_quantity, self.lot_position,
                self.cost_reference, self.cost_reference_qualifier,
                self.cost_factor, self.cost_factor_position, self.complete)


@dataclass(frozen=True)
class ResourceAccountingIssue(Fact):
    """Inspectable evidence that a resource interval is not closed/read.

    Consumers use these shared reading results; they do not reinterpret verbs
    or decide grammatical completeness themselves.
    """

    position: int
    reason: str

    def key(self) -> tuple:
        return ("resource-accounting-issue", self.provenance.sentence, self.position, self.reason)

    def value_part(self) -> Any:
        return self.reason


@dataclass(frozen=True)
class BoundedActivityInquiry(Fact):
    """A non-assertive inquiry about one activity over a stated duration.

    ``Aven is wondering how much bread she can eat in one day`` does not
    state an eating rate or amount.  It does, however, establish the actor,
    theme, activity, and discourse interval that a later explicit totality
    event (``she eats it all``) may refer back to.  Keeping that frame as its
    own fact prevents the embedded question from folding into bogus
    membership or holding facts.
    """

    seeker: str
    activity: str
    content: str
    elapsed: float
    unit: str
    occurrence: int

    def key(self) -> tuple:
        return (
            "bounded-activity-inquiry",
            self.seeker,
            self.activity,
            self.content,
            self.occurrence,
        )

    def value_part(self) -> Any:
        return (self.elapsed, self.unit)


@dataclass(frozen=True)
class ItemClassReference:
    """A forward discourse link; the quantity's literal fields stay intact."""

    item: ReferenceIdentity
    participant: ReferenceIdentity
    predicate: str
    target: Provenance
    antecedents: tuple[Provenance, ...]

    def to_dict(self):
        return {"item": self.item.to_dict(), "participant": self.participant.to_dict(),
                "predicate": self.predicate, "target": dict(vars(self.target)),
                "antecedents": [dict(vars(source)) for source in self.antecedents]}


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
    # Legacy flat descriptor projections. Full participant identity lives in
    # entity_ref, independently of the display key or numerical value.
    owner: str | None = None
    qualifier: str | None = None
    # Item/subtype qualification is separate from participant identity. The
    # store preserves its existing part/whole and subtype-key discipline.
    measure_qualifier: str | None = None
    label: str | None = None
    # a within-sentence CONJUNCT index (mining candidate
    # conjoined-event-conjuncts): "sold 3 boxes to her aunt and 4 boxes to
    # her uncle" binds every conjunct to the SAME entity/measure/verb, and
    # `occurrence` alone (the sentence index) cannot tell them apart — the
    # second conjunct's fact collides with the first's at the identical
    # key(), even though they are two genuine, distinct events to be
    # SUMMED, not two disagreeing readings of one holding. `segment` carries
    # the conjunct's position (1, 2, 3, ... — the FIRST/only conjunct in a
    # sentence stays None). NOT part of key() or value_part() — the FIFTH
    # of FactStore.admit's collision-time mirrors (after owner/qualifier/
    # measure_qualifier/label): only consulted once a same-key VALUE
    # conflict has already happened and none of those four fields could
    # explain it (a genuinely unqualified repeated noun, "3 rolls to
    # grandma ... 3 rolls to a neighbour" — the distinguishing signal is
    # the conjunct's POSITION, never its value, so a SAME-VALUE pair
    # coexists as two facts too, instead of deduping and undercounting).
    # Ordering AFTER the other four matters: a genuinely qualifier-
    # differentiated conjunct pair ("1 purple hat" / "4 green hats") still
    # re-keys to measure[qualifier] exactly as it always did, keeping its
    # paired Price facts (which carry no `segment`) in lockstep. Left None
    # (and so never a factor) for STATE quantities: a same-key value
    # disagreement there is a genuine holding conflict, not a list of
    # distinct events, and must keep quarantining exactly as before.
    segment: int | None = None
    entity_ref: ReferenceIdentity | None = field(default=None, metadata={"reference_for": "entity"})
    item_reference: ItemClassReference | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.entity_ref is None:
            object.__setattr__(self, "entity_ref", flat_reference(
                self.entity, self.owner, self.label, self.qualifier))

    @property
    def is_state(self) -> bool:
        return self.occurrence is None

    def key(self) -> tuple:
        key = ("quantity", self.entity, self.measure, self.verb, self.time, self.occurrence)
        return key + ((self.entity_ref.key(),) if self.entity_ref.described else ())

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class Relation(Fact):
    """subject = factor * standard + offset (measure-scoped)."""

    subject: str
    standard: str
    # None only for a mining-candidate elided-measure-relations rule ("Ben
    # has twice as many as Ann" — no measure noun at all in the text): an
    # explicit UNRESOLVED sentinel, never a guess. saturate.py's
    # `_relations_synth` recovers it from the standard's own unique
    # in-play quantity before doing anything else with the relation;
    # every OTHER emitting rule always states a concrete measure, so this
    # stays `str` in practice everywhere except that one elided family.
    measure: str | None
    factor: float = 1.0
    offset: float = 0.0
    verb: str = "have"
    # the trailing index LABEL of `subject`/`standard`, when either side's
    # noun was merged from NOUN + single-capital-letter INDEX (condense.py
    # merge-label: "Jar A", "Class B") — mining candidate
    # labeled-entity-relations, the Relation-side mirror of Quantity.label
    # (increment 74). `subject`/`standard` themselves stay the bare entity
    # lemma everywhere they already worked (e.g. both sides of a "Jar A ...
    # Jar B ..." relation both read `subject='jar'`/`standard='jar'`, the
    # same as before this field existed); these two fields exist ONLY so
    # saturate.py's `_relations_synth` can (a) resolve a labeled standard
    # against the SPECIFIC labeled Quantity FactStore.admit's existing
    # label-collision re-key (facts.py) produces, instead of an arbitrary
    # same-lemma quantity, and (b) tag a derived subject Quantity with its
    # own label so a later same-lemma sibling can be told apart from it.
    # These flat projections remain in key() alongside the complete role
    # references; Quantity now also keys described participant identities.
    # Historically,
    # Relation.key() has no separate identity-collision-splitting path the
    # way Quantity/facts.py does, so two DIFFERENT labeled relations that
    # happen to share the same bare subject/standard/measure/verb (e.g. a
    # "Jar C = 2x Jar B" relation and a "Jar B = Jar A + 12" relation both
    # bare-key to subject='jar'/standard='jar') must not silently dedupe or
    # quarantine each other — including the label in the key keeps them
    # naturally distinct facts, with zero change to any existing (both
    # fields None) relation's key tuple.
    subject_label: str | None = None
    standard_label: str | None = None
    # Possessive owners of the two entity roles. Quantity already carries
    # the same owner field; these mirrors let relation saturation select the
    # exact owned standard (and tag an owned derived subject) instead of
    # collapsing `her child` and `his child` to the bare noun `child`.
    # Included in the relation key because differently-owned relations are
    # genuinely different assertions even when their bare heads coincide.
    subject_owner: str | None = None
    standard_owner: str | None = None
    # the attributive modifier of `measure`/`standard`, when the relation's
    # own ITEM or STANDARD noun was merged from ADJECTIVE+NOUN or NOUN+NOUN
    # (condense.py merge-attribute / merge-compound) — mining candidate
    # qualified-measure-keys, the Relation-side mirror of Quantity.
    # measure_qualifier (increment 70), one field over: "Sam has 16 red
    # apples. Sam has 12 more green apples than red apples" bare-folds
    # `item`/`std` to the SAME lemma 'apple' (patterns.py's qualifier-aware
    # `distinct_measure` where-predicate is what lets this rule match at
    # all instead of declining as self-referential); with no qualifier
    # carried through the Relation fact, saturate.py's same-holder subtype
    # branch had no way to (a) resolve the STANDARD side against the
    # SPECIFIC qualified sibling quantity (never an arbitrary same-lemma
    # one — the exact discipline `standard_label` already established for
    # index labels) or (b) tag the derived subject Quantity with its own
    # qualifier so a later same-key collision re-keys cleanly instead of
    # colliding null-vs-non-null (facts.py's own guard against exactly that
    # laundering). Included in `key()`, same reasoning as `subject_label`/
    # `standard_label`: two DIFFERENT qualified relations sharing a bare
    # subject/standard/measure/verb ("12 more green apples than red
    # apples" + "5 fewer blue apples than red apples") must not quarantine
    # each other as a same-key value disagreement. A direct measure-slot
    # emission retains its modifier when this field is omitted or null.
    # Explicit non-null YAML values, including empty strings, remain exact.
    measure_qualifier: str | None = field(default=None, metadata={"qualifier_for": "measure"})
    standard_qualifier: str | None = None
    # mining candidate temporal-offset-age-recut: "In N years, A will be K
    # times as old as B" states the ratio at a FUTURE (or past) point in
    # time, not today — `subject_offset`/`standard_offset` are the signed
    # year offsets (0 = today, the default every pre-existing relation
    # keeps) applied to each side's age BEFORE the factor/offset equation
    # is evaluated: age(subject)+subject_offset = factor*(age(standard)+
    # standard_offset)+offset. Purely additive like `subject_label`/
    # `standard_label` above: every relation that never sets them keeps
    # value 0.0 on both, so `_relations_synth`'s general formula (always
    # written in terms of these two fields) reduces to EXACTLY today's
    # arithmetic for every existing relation (adding/subtracting 0.0
    # changes no float result). Included in `key()`, mirroring `subject_
    # label`/`standard_label`'s own precedent: two relations for the same
    # (subject, standard, measure, verb) that state the ratio at DIFFERENT
    # time offsets are not a restatement of one fact, they are two
    # distinct facts — folding them to one key would make the second
    # either an agreement-dedupe false-positive or a spurious value
    # conflict, depending on which offset happened to be typed first.
    subject_offset: float = 0.0
    standard_offset: float = 0.0
    # Optional declarative antecedent gates for a reserved anaphoric
    # standard. A pattern rule may require the earlier Quantity's measure
    # and governing verb to belong to these registry categories before it
    # participates in anaphor resolution. None preserves the historical
    # measure-agnostic contract for the existing amount/number/much/many
    # families; a specialized rule can opt into one or both gates without a
    # word-specific resolver branch. Included in key(): otherwise two
    # otherwise-identical anaphoric relations with different admissible
    # antecedent domains could silently deduplicate.
    anaphor_measure_category: str | None = None
    anaphor_verb_category: str | None = None
    subject_ref: ReferenceIdentity | None = field(default=None, metadata={"reference_for": "subject"})
    standard_ref: ReferenceIdentity | None = field(default=None, metadata={"reference_for": "standard"})

    def __post_init__(self):
        if self.subject_ref is None:
            object.__setattr__(self, "subject_ref", flat_reference(
                self.subject, self.subject_owner, self.subject_label))
        if self.standard_ref is None:
            object.__setattr__(self, "standard_ref", flat_reference(
                self.standard, self.standard_owner, self.standard_label))

    def key(self) -> tuple:
        return (
            "relation", self.subject, self.subject_label, self.subject_owner,
            self.standard, self.standard_label, self.standard_owner, self.measure,
            self.measure_qualifier, self.standard_qualifier, self.verb,
            self.subject_offset, self.standard_offset,
            self.anaphor_measure_category, self.anaphor_verb_category,
            self.subject_ref.key(), self.standard_ref.key(),
        )

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
    pool_qualifier: str = ""

    def key(self) -> tuple:
        return ("fraction_quantity", self.entity, self.measure, self.verb,
                self.occurrence, self.time, self.pool_qualifier)

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
class CollectionContext(Fact):
    """An explicitly introduced, but not yet counted, collection.

    ``"Mira has a pantry with marbles"`` establishes both where later
    partitions belong and what plural an anaphor such as ``them`` denotes.
    It does *not* assert a zero quantity. Keeping that discourse evidence in
    its own fact prevents unknown cardinality from leaking into arithmetic.

    ``holder_owner`` preserves possessive identity for locations introduced
    through their owner (Mira's pantry versus Tova's pantry). The holder
    remains the ordinary noun lemma so existing in-place asks keep their
    established lookup shape.
    """

    holder: str
    collection: str
    verb: str = "have"
    holder_owner: str | None = None

    def key(self) -> tuple:
        return (
            "collection_context",
            self.holder,
            self.holder_owner,
            self.collection,
            self.verb,
        )


@dataclass(frozen=True)
class SequentialPartition(Fact):
    """A complete three-way allocation anchored by prior discourse.

    The first fraction is taken from the whole prior collection, the second
    from its remainder, and the final attribute receives what is left. The
    premise does not repeat the collection noun, so this remains a distinct
    unresolved fact until its synthesizer finds exactly one prior collection
    measure and holder. It then emits three ordinary ``PartitionQuantity``
    facts; every ask continues to consume the established partition contract.
    """

    first_attribute: str
    first_fraction: float
    second_attribute: str
    second_fraction: float
    rest_attribute: str
    verb: str

    def key(self) -> tuple:
        return (
            "sequential_partition",
            self.provenance.sentence,
            self.first_attribute,
            self.second_attribute,
            self.rest_attribute,
            self.verb,
        )

    def value_part(self) -> Any:
        return (self.first_fraction, self.second_fraction)


@dataclass(frozen=True)
class SequentialPartitionPrefix(Fact):
    """The first two stages of a partition completed by later discourse.

    This fact deliberately carries no population or final destination.  A
    synthesizer may combine it only with an immediately following
    ``SequentialPartitionRemainder``; the resulting complete partition then
    uses the ordinary unique-prior-collection resolution path.
    """

    first_attribute: str
    first_fraction: float
    second_attribute: str
    second_fraction: float
    verb: str

    def key(self) -> tuple:
        return (
            "sequential_partition_prefix",
            self.provenance.sentence,
            self.first_attribute,
            self.second_attribute,
            self.verb,
        )

    def value_part(self) -> Any:
        return (self.first_fraction, self.second_fraction)


@dataclass(frozen=True)
class SequentialPartitionRemainder(Fact):
    """A later ``the rest ...`` clause completing a staged partition."""

    rest_attribute: str
    verb: str

    def key(self) -> tuple:
        return (
            "sequential_partition_remainder",
            self.provenance.sentence,
            self.rest_attribute,
            self.verb,
        )


@dataclass(frozen=True)
class SequentialPartitionInitialShare(Fact):
    """The first whole-pool percentage in a sentence-split allocation."""

    first_attribute: str
    first_fraction: float
    verb: str

    def key(self) -> tuple:
        return (
            "sequential_partition_initial_share",
            self.provenance.sentence,
            self.first_attribute,
            self.verb,
        )

    def value_part(self) -> Any:
        return self.first_fraction


@dataclass(frozen=True)
class SequentialPartitionRemainingShare(Fact):
    """A percentage of the remainder after a preceding initial share."""

    second_attribute: str
    second_fraction: float
    verb: str

    def key(self) -> tuple:
        return (
            "sequential_partition_remaining_share",
            self.provenance.sentence,
            self.second_attribute,
            self.verb,
        )

    def value_part(self) -> Any:
        return self.second_fraction


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

    `is_rest` marks a REST partition ("THE REST are ADJ|NOUN" — mining
    candidate rest-partitions, the partition sibling of RestQuantity):
    `collection` starts as the bare "rest"/"remainder" word (never a real
    measure, exactly like the pronoun placeholder) and `value` starts as an
    unused 0 placeholder. The collection synthesizer resolves `collection`
    against the unique prior collection exactly as the cardinal/fractional
    forms do, but only once EVERY OTHER (non-rest) partition of that same
    collection has itself resolved to a real count — a still-pending
    sibling would make this an under-subtraction (a confident wrong, not a
    decline), so it stays unresolved that round instead. Once every sibling
    is in, `value` is re-sized to (the collection's own total as of this
    sentence) minus the signed sum of those prior partitions, and the
    resolved fact carries a real count with `is_rest` cleared, exactly like
    `is_fraction`.

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
    is_rest: bool = False

    def key(self) -> tuple:
        return ("partition_quantity", self.collection, self.attribute, self.verb)

    def value_part(self) -> Any:
        return (self.value, self.polarity)


@dataclass(frozen=True)
class PartitionAggregateShare(Fact):
    """A subgroup sized from an explicitly coordinated sibling total.

    For example, ``"25% as many green marbles as red and blue marbles"``
    states ``green = .25 * (red + blue)``. The fact remains unresolved until
    both named sibling partitions belong to one earlier collection; the
    synthesizer then emits an ordinary :class:`PartitionQuantity` so existing
    partition and qualified-measure consumers can reuse it.
    """

    collection: str
    attribute: str
    first_attribute: str
    second_attribute: str
    fraction: float
    verb: str = "be"

    def key(self) -> tuple:
        return (
            "partition_aggregate_share",
            self.collection,
            self.attribute,
            self.first_attribute,
            self.second_attribute,
            self.verb,
        )

    def value_part(self) -> Any:
        return self.fraction


@dataclass(frozen=True)
class RatioQuantity(Fact):
    """'the ratio of BOYS to GIRLS is 3:2' (mining candidate ratio-split-
    premises) — an UNRESOLVED share of an unnamed collection. `fraction`
    is this label's own portion (m/(m+n) for a two-part ratio) of
    whatever measure the ratio synthesizer (saturate.py's
    `_ratio_split_synth`) resolves as the collection anchor: the UNIQUE
    Quantity measure known as of this fact's OWN sentence — INCLUSIVE,
    not strictly prior. A ratio clause typically shares its sentence with
    its own anchor ("There are 100 students in class AND the ratio of
    boys to girls is 3:2" — one sentence, joined by 'and'), unlike the
    fraction/partition pool machinery's prior-sentence-only convention
    ("pools = signed sum of PRIOR-sentence facts" is load-bearing
    elsewhere), which is why this is its own fact kind with its own synth
    rather than a reuse of FractionQuantity/PartitionQuantity and
    `_pool_before` — the shared pool scan stays byte-for-byte untouched.

    Resolved into a real Quantity for `attribute` on the collection's
    unique holder once resolved. Unresolved ones (no unique non-ratio
    anchor measure known, or the only known measure is itself another
    label of the SAME ratio — a part is never its own whole) never
    commit anything: the downstream ask simply finds no Quantity for that
    label and declines, the same safety net every other "premise read but
    not yet computed" shape in this codebase relies on."""

    attribute: str
    fraction: float
    verb: str = "be"

    def key(self) -> tuple:
        return ("ratio_quantity", self.attribute, self.verb)

    def value_part(self) -> Any:
        return self.fraction


@dataclass(frozen=True)
class AnchorQuantity(Fact):
    """A bare numeral stated for an entity whose MEASURE NOUN is elided
    entirely — mining candidate elided-measure-anchors: "Quinn catches
    twice the amount of frogs as Alster WHO CAUGHT 2" (no 'frogs' in the
    relative clause), "...how many more turtles does Trey have than
    Kristen, IF KRISTEN HAS 12?" (the trailing conditional states a bare
    count, no 'turtles'). learn.py's generic SVO fold always needs a
    counted NOUN dobj to build a Quantity; a noun-less value has nowhere
    to go and would otherwise fall all the way to a valueless Predication
    (dobj holding the number's own surface, e.g. '2') — exactly the gap
    `_bare_age_anchor_synth` already patches for the age-specific case,
    generalized here to any measure via a proper fact kind instead of a
    bespoke per-category synth.

    Resolved to a real Quantity (measure filled in) by saturate.py's
    `_anchor_quantity_synth` — the anchor-quantity sibling of
    FractionQuantity/RestQuantity/PartitionQuantity: the measure comes
    from the UNIQUE measure already in play for this entity (a sibling
    Relation naming the entity as its subject/standard, or the entity's
    own other stated Quantity measure), the SAME unique-pool-in-play
    discipline `_relations_synth` (increment 85) already applies to
    elided-measure RELATIONS. Zero or two-or-more candidates is ambiguous
    and declines — never a guess.

    A SEPARATE fact kind from Quantity on purpose, not a nullable
    `measure` field on Quantity itself (Relation's increment-85 approach):
    Quantity is the single most-consumed fact kind in the engine (~30 call
    sites across answer.py/saturate.py/guards.py/facts.py, several
    building bare `{q.measure for q in ...}` sets used for ambiguity
    checks) — an unresolved `measure=None` sitting among them would
    silently pollute every one of those sets and collision-splitting
    mirrors in facts.py's `admit()` (all gated on `isinstance(fact,
    Quantity)`). A distinct class is invisible to all of that until this
    module's own synth explicitly promotes it into a real Quantity.

    UNRESOLVED ones veto any commit (guards.py's `unresolved-derivation`),
    exactly like Fraction/RestQuantity — a silently dropped bare count is
    a confident-wrong factory. EXISTENCE (not use) counts as value-
    accounting "read", same as Quantity/FractionQuantity/PartitionQuantity
    (unlike Rate/Price/Goal/GroupTotal): this fact IS the captured stated
    count the moment the fold sees it; the unresolved-derivation veto is
    what actually protects an anchor that never finds its measure."""

    entity: str
    value: float
    verb: str = "have"
    occurrence: int | None = None
    time: str | None = None
    owner: str | None = None
    qualifier: str | None = None
    label: str | None = None

    def key(self) -> tuple:
        return ("anchor_quantity", self.entity, self.verb, self.occurrence, self.time)

    def value_part(self) -> Any:
        return self.value


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
    # the attributive modifier of `item`, when the priced noun was merged
    # from ADJECTIVE+NOUN or NOUN+NOUN (condense.py's merge-attribute /
    # merge-compound) — the Price mirror of Quantity.measure_qualifier
    # (mining candidate qualified-measure-keys). NOT part of key() or
    # value_part(): identity stays the bare item lemma everywhere it
    # already worked. Read ONLY by FactStore.admit's collision handling,
    # to split a genuine same-key VALUE conflict ("red shirt" priced at
    # $32 vs "blue shirt" priced at $27, both bare-folding to item='shirt')
    # into two items — never to change identity absent a real conflict.
    qualifier: str | None = None

    def key(self) -> tuple:
        return ("price", self.item, self.verb, self.occurrence)

    def value_part(self) -> Any:
        return self.value

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class Goal(Fact):
    """A stated TARGET quantity, not a holding or an event.

    Surface constructions include direct requirements, infinitival intentions,
    and resource-building activities linked to a priced purpose. They normalize
    here because arithmetic needs the target, not a vocabulary-specific fact
    class. USE-GATED for value accounting, like Rate/Price:
    a goal that merely EXISTS has not been read — only the deficit consumer
    actually subtracting a holding from it counts as use (a wanted purchase
    is not a purchase, the increment-14 kirsty lesson generalized to
    goal predicates). `verb` retains the surface predicate for traceability;
    consumers deliberately do not use it to distinguish otherwise-compatible
    goals. The target action verb ('collect') is not captured here — the goal
    is the quantity, not the activity."""

    entity: str
    measure: str
    value: float
    verb: str = "want"
    # Optional concrete purpose of the goal ("money for shoes"). Existing
    # quantity goals leave this unset; purpose-qualified asks may require an
    # exact target rather than borrowing an unrelated monetary goal.
    target: str | None = None

    def key(self) -> tuple:
        return ("goal", self.entity, self.measure, self.target)

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class Contribution(Fact):
    """A stated contribution toward another entity's goal.

    The beneficiary owns the progress while the contributor remains explicit
    evidence. This avoids pretending that a decision to give has already
    changed either person's general-purpose holdings; only the deficit
    consumer incorporates these values into the named beneficiary's goal.
    """

    beneficiary: str
    contributor: str
    measure: str
    value: float
    verb: str = "give"
    segment: int | None = None

    def key(self) -> tuple:
        return (
            "contribution",
            self.beneficiary,
            self.contributor,
            self.measure,
            self.verb,
            self.segment,
        )

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class GroupTotal(Fact):
    """'There are 160 toys ALTOGETHER' / 'Tom and Devin have been teaching
    for a TOTAL of 70 years' — a stated SUM across whichever entities the
    passage names, never one entity's own holding (a sum-constraint linear
    system: mining candidate sum-constraint-relations). `scope` retains the
    exact normalized subject when the total construction itself binds one
    ("Total blue has 40 birds" -> scope='blue'). Tail-only constructions
    ("23 birds altogether") and synthesized totals have no mechanically
    available group identity and remain unscoped (`None`) rather than
    guessing one. This is exactly the premise arithmetic/existential-
    premise-bare's own `absent: {cat: aggregate}` guard REFUSES to read as a
    Quantity — it names the group total explicitly rather than widening that
    guard.

    USE-GATED for value accounting, like Rate/Price/Goal (the look #4-#7
    invariant every new fact kind must decide explicitly): a group total
    that merely EXISTS has not been read — only synth/sum-constraint
    actually solving a Relation against it (see saturate.py) counts as use.
    Same-key (scope, measure) disagreement is a genuine conflict, exactly
    like a STATE Quantity. Distinct non-null scopes may coexist for the same
    measure; two unscoped totals still collide exactly as before."""

    measure: str
    value: float
    scope: str | None = None
    verb: str = "have"

    def key(self) -> tuple:
        return ("group_total", self.scope, self.measure)

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class Discount(Fact):
    """'Tim buys a cabinet for $1200 and gets a 15% discount' / 'a $100
    discount' / 'a discount of $2 EACH' — a stated reduction applied to a
    priced purchase's total (mining candidate discounted-purchase-totals).
    USE-GATED for value accounting, like Rate/Price/Goal/GroupTotal (the
    look #4-#7 invariant every new fact kind must decide explicitly): a
    discount that merely EXISTS has not been read — only the purchase-total
    consumer (answer.py's `_purchase_total`) actually applying it to a
    committed total counts as use.

    `value` is the fraction (0.15 for '15%') for a percent discount, or the
    raw currency amount for a flat discount — `percent` disambiguates
    which. `scope` is 'total' (the bare/default reading: applies ONCE to
    the summed purchase total) or 'per_unit' (the surface explicitly scopes
    the discount to EACH unit bought — "a discount of $2 EACH" — so the
    consumer multiplies by the purchased quantity before subtracting).

    Same-key (global) disagreement is a genuine conflict, exactly like
    GroupTotal's single-measure invariant: a document states at most ONE
    discount the purchase-total consumer can safely apply. A SECOND,
    differently-valued discount mention (a compounding discount, e.g. "an
    additional 5% discount" stacked on a first one) is a genuinely
    different, out-of-scope arithmetic shape — colliding quarantines BOTH
    (facts.py's ordinary same-key-disagreement path), and the consumer
    checks `store.quarantined` too, so it declines rather than silently
    picking one discount, or worse, silently applying neither and
    committing the pre-discount total as though it were final."""

    value: float
    percent: bool
    scope: str = "total"

    def key(self) -> tuple:
        return ("discount",)

    def value_part(self) -> Any:
        return (self.value, self.percent, self.scope)


@dataclass(frozen=True)
class PercentChange(Fact):
    """'Susie puts 20% MORE money into her piggy bank' — a stated percent
    INCREASE or DECREASE applied to an entity's own EXISTING currency
    holding (mining candidate percent-change-values). Self-referential by
    construction: unlike Relation's percent-comparative family ("20% more
    pines THAN Ann"), there is no second entity here — the subject scales
    its OWN prior total, so `entity` names the SAME holder `_entity_total`
    (answer.py) folds state/event Quantity facts for, and the consumer
    multiplies that fold's total by (1 + `sign` * `value`) rather than
    comparing two different holders' totals.

    `value` is the RAW stated fraction (0.20 for '20%' — never
    pre-multiplied by `sign`), read directly off the `type: percent`
    token exactly like Discount.value; `sign` is +1 for an INCREASE
    direction word ('more', `more_dir`/delta polarity) or -1 for a
    DECREASE direction word ('fewer'/'less', `less_dir`), computed at
    emit time via the same `sign(dir)` numeric-field mechanism the
    percent-comparative Relation rules already use — never a hardcoded
    Python constant. `measure` is always the 'currency' CATEGORY name
    (never a specific denomination, the SAME `measure: currency`
    convention ask/how-much-bare-entity's query already uses): this
    increment scopes to monetary percent-change events only — every
    structural sample in the brief is a price/salary/money change — so
    the pattern rule gates its own dobj slot to `cat: currency`
    (dollar/dollars/money/pound/pounds), never a bare noun, which is what
    keeps an unrelated non-money event ("20% more pines") from ever
    reaching this fact kind at all.

    USE-GATED for value accounting, like Discount/Rate/Price/Goal/
    GroupTotal (the look #4-#7 invariant every new fact kind must decide
    explicitly): a percent-change that merely EXISTS has not been read —
    only `_entity_total` (answer.py) actually multiplying a committed
    fold by it counts as use. In practice the stated percent TOKEN is
    also part of this rule's own pattern-match span, so it is marked
    `pattern_consumed` regardless (guards.py) — USE-gating is declared
    here anyway, for the SAME reason Discount's docstring declares it:
    consistency with every sibling premise-adjustment fact kind, and
    defense-in-depth for any future consumer of this fact that does NOT
    happen to hold the matching token.

    `occurrence` is the emitting sentence's index (mirrors Quantity's own
    EVENT convention, auto-assigned by patterns.py's `_build_fact` — a
    percent-change is inherently an event, never a state) — this is what
    lets TWO percent-change events on the SAME entity, stated in two
    DIFFERENT sentences, key apart and both admit (`_entity_total` applies
    them in ascending sentence order, chaining: decreased-then-increased
    composes correctly). Two percent-change events for the same entity
    stated in the SAME sentence (a same-sentence compounding pair, e.g. a
    conjoined "decreased by 15% and then increased by 40%") share one
    `occurrence` and so COLLIDE at facts.py's ordinary same-key path —
    exactly like Discount's own compounding-discount scope note, this is a
    genuinely different, out-of-scope arithmetic shape (conjunction
    recovery for a new verb category — a further hop, not this
    increment's mechanism) that quarantines-and-declines rather than
    silently picking one of the two."""

    entity: str
    value: float
    sign: float
    measure: str = "currency"
    verb: str = "change"
    occurrence: int | None = None

    def key(self) -> tuple:
        return ("percent_change", self.entity, self.occurrence)

    def value_part(self) -> Any:
        return (self.value, self.sign)


@dataclass(frozen=True)
class SpatialPlacement(Fact):
    """One entity positioned relative to a supporting reference object.

    This is deliberately not a property of the reference object.  Placing a
    vessel on an instrument changes the spatial relation between them; it does
    not make the vessel's mass an intrinsic property of the instrument.  The
    relation is retained explicitly so a later consumer can distinguish
    ``on`` from another supported spatial configuration.
    """

    entity: str
    reference: str
    relation: str
    occurrence: int | None = None

    def key(self) -> tuple:
        return ("spatial-placement", self.entity, self.occurrence)

    def value_part(self) -> Any:
        return (self.reference, self.relation)


@dataclass(frozen=True)
class MeasuredContentChange(Fact):
    """One ordered change to the contents of a measured container.

    ``operation`` describes the effect on the aggregate reading, not an
    invented quantity for the added substance:

    - ``set_total`` records a stated resulting total;
    - ``multiply_total`` scales the prior total; and
    - ``add_quantity`` adds a stated amount in ``measure`` units.

    The content remains explicit even when its own amount is unknown.  Thus
    "enough brine to bring the weight to 4 kg" does not falsely assert that
    the brine itself weighs 4 kg.  ``container`` may carry the reserved
    discourse sentinel used by a rule whose surface omits the already-active
    measured container; the consumer resolves that sentinel only against one
    unique prior measurement stream.

    Numeric values are use-gated by ``guards.py``: merely extracting an update
    cannot account for a number.  A committing consumer must actually apply
    every update in narration order.
    """

    container: str
    content: str
    operation: str
    value: float
    dimension: str | None = None
    measure: str | None = None
    occurrence: int | None = None

    def key(self) -> tuple:
        return ("measured-content-change", self.container, self.occurrence)

    def value_part(self) -> Any:
        return (
            self.content,
            self.operation,
            self.value,
            self.dimension,
            self.measure,
        )


@dataclass(frozen=True)
class ContainerContent(Fact):
    """A named content introduced into a resolved container at one event.

    This is the inspectable container/content projection of a
    :class:`MeasuredContentChange`.  It carries no invented amount: the event
    may state only its effect on an aggregate reading.  Later containment
    reasoning can use the ordered events without reverse-engineering an
    internal active-stream sentinel.
    """

    container: str
    content: str
    operation: str
    occurrence: int

    def key(self) -> tuple:
        return (
            "container-content",
            self.container,
            self.content,
            self.occurrence,
        )

    def value_part(self) -> Any:
        return self.operation


@dataclass(frozen=True)
class TotalityTransfer(Fact):
    """A complete anaphoric collection placed into one destination.

    The surface may leave the collection's measure implicit ("put them all
    in the jar").  The source and destination remain explicit so saturation
    can resolve the transfer only when the source has one unambiguous
    non-container content total.  No amount is invented by this fact itself.
    """

    source: str
    destination: str
    verb: str
    occurrence: int
    # An explicit "both PACKAGE" surface selects two previously introduced
    # qualified package classes.  The ordinary anaphoric "them all" form
    # leaves this unset and retains its established unique-content contract.
    package_class_count: int | None = None
    # Explicit package-group surfaces retain their package and content heads.
    # They constrain which prior package quantities may satisfy the transfer;
    # neither field supplies an amount by itself.
    package: str | None = None
    content: str | None = None

    def key(self) -> tuple:
        return (
            "totality-transfer",
            self.source,
            self.destination,
            self.occurrence,
        )

    def value_part(self) -> Any:
        return (
            self.verb,
            self.package_class_count,
            self.package,
            self.content,
        )


@dataclass(frozen=True)
class TotalityEvent(Fact):
    """A participant performs an activity on one complete anaphoric pool.

    The surface deliberately carries no amount (``she eats it all``).  A
    synthesizer may materialize event quantities only when one compatible
    bounded inquiry and its acquired/held content totals identify the pool.
    """

    entity: str
    verb: str
    occurrence: int

    def key(self) -> tuple:
        return ("totality-event", self.entity, self.verb, self.occurrence)

    def value_part(self) -> Any:
        return True


@dataclass(frozen=True)
class ContainerCapacityInquiry(Fact):
    """A person's explicitly framed question about one container's capacity.

    This is discourse context, not evidence that the container has any
    particular capacity.  ``content`` is optional because ordinary assessment
    frames such as "measuring the capacity of a jar" name the container before
    a later clause identifies what is being counted.
    """

    seeker: str
    container: str
    content: str | None = None

    def __post_init__(self) -> None:
        if self.content == "":
            object.__setattr__(self, "content", None)

    def key(self) -> tuple:
        return (
            "container-capacity-inquiry",
            self.seeker,
            self.container,
            self.content,
        )


@dataclass(frozen=True)
class ContainerCapacityObservation(Fact):
    """Evidence constraining how much of one content a container can hold.

    ``all_available_fit`` establishes only a confirmed lower bound: every
    available item fitted, but a larger amount might also fit.
    ``remainder_after_fill`` is exact when the container is explicitly full:
    capacity is the available amount minus the stated remainder.  A missing
    container is resolved only through one compatible capacity inquiry.
    """

    content: str
    mode: str
    value: float = 0.0
    container: str | None = None

    def __post_init__(self) -> None:
        if self.container == "":
            object.__setattr__(self, "container", None)

    def key(self) -> tuple:
        return (
            "container-capacity-observation",
            self.provenance.sentence,
            self.container,
            self.content,
            self.mode,
        )

    def value_part(self) -> Any:
        return self.value


@dataclass(frozen=True)
class Before(Fact):
    """A strict ordering between two event identities.

    Relative event-time markers are observed as :class:`EventTime` facts;
    document inference emits this relation only when their pack-declared
    offsets differ.  Equal offsets assert simultaneity only through their
    shared coordinate and do not produce either direction.
    """

    earlier: str
    later: str

    def key(self) -> tuple:
        return ("before", self.earlier, self.later)


@dataclass(frozen=True)
class EventTime(Fact):
    """One predicate occurrence anchored by a relative temporal marker.

    ``event`` is a runtime-local identity (sentence plus verb unit), while
    the human-readable predicate fields keep the fact inspectable. ``offset``
    is read exclusively from pack data; the kernel contains no marker list.
    """

    event: str
    entity: str
    verb: str
    marker: str
    offset: float
    obj: str | None = None

    def key(self) -> tuple:
        return ("event-time", self.event)

    def value_part(self) -> Any:
        return (self.entity, self.verb, self.obj, self.marker, self.offset)


@dataclass(frozen=True)
class LocationEvent(Fact):
    """One event's exact effect on an entity's location fluent.

    ``effect`` is deliberately small and inspectable: ``initiates`` starts a
    location state, ``terminates`` ends one, and ``holds`` / ``not-holds``
    directly observe its positive or negative state at the event's stated
    time. The vocabulary that licenses an effect lives in pack categories;
    this fact only preserves the resulting event graph.
    """

    event: str
    entity: str
    place: str
    effect: str

    def key(self) -> tuple:
        return ("location-event", self.event, self.entity, self.place)

    def value_part(self) -> Any:
        return self.effect


@dataclass(frozen=True)
class LocationConstraint(Fact):
    """A scoped modal restriction on one location-state transition.

    The first supported form is an impossible termination (``nobody can
    leave PLACE``).  Keeping transition, modality, and subject class explicit
    prevents a prohibition from silently becoming a physical impossibility
    and leaves room for later entry/duration constraints without a new fact
    shape.
    """

    place: str
    transition: str
    modality: str
    subject_class: str

    def key(self) -> tuple:
        return (
            "location-constraint",
            self.place,
            self.transition,
            self.subject_class,
        )

    def value_part(self) -> Any:
        return self.modality


@dataclass(frozen=True)
class LocationTransitionAbsence(Fact):
    """An explicit statement that no transition occurred in an interval.

    Unlike :class:`LocationConstraint`, this is evidence about what happened,
    not a claim that the transition was impossible. The first controlled
    surface uses ``narrative-through-reference``: the current narrative up to
    the day selected by the question.
    """

    place: str
    transition: str
    scope: str
    subject_class: str

    def key(self) -> tuple:
        return (
            "location-transition-absence",
            self.place,
            self.transition,
            self.scope,
            self.subject_class,
        )


@dataclass(frozen=True)
class LocationConstraintViolation(Fact):
    """An observed transition conflicts with an active modal constraint."""

    event: str
    entity: str
    place: str
    transition: str

    def key(self) -> tuple:
        return ("location-constraint-violation", self.event)

    def value_part(self) -> Any:
        return (self.entity, self.place, self.transition)


# ---------------------------------------------------------------------------
# Reading — one sentence's workspace.
# ---------------------------------------------------------------------------


def _snapshot(value: Any) -> Any:
    """Copy a feature value for a Decision diff.

    Immutable values cannot be mutated out from under the trace, so copying one
    is a no-op that still pays deepcopy's full dispatch cost — and 60% of the
    values passing through `record` are bare scalars. Everything else (notably
    obligation lists, whose `target` is a live Unit) must still be deep-copied
    or the "diff" would alias state that keeps changing.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return copy.deepcopy(value)


class Reading:
    """The per-sentence workspace. `record()` is the single mutation door."""

    def __init__(
        self,
        text: str,
        sentence_index: int = 0,
        tracing: bool = True,
        assumption: bool = False,
    ):
        self.text = text
        self.sentence_index = sentence_index
        self.tracing = tracing
        # A question assumption participates in this solve's blackboard but is
        # not an asserted project premise. solve() creates a fresh document on
        # every call, so the scope cannot escape the current question.
        self.assumption = assumption
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
        """Apply `changes` to target.features, logging a reversible diff.

        When `self.tracing` is off the diff is not snapshotted: the Decision is
        still recorded (same seq, kind, target, reason) but `before`/`after` are
        empty. Only `Reading.undo` and `engine.trace` read those, and neither
        runs during a bench — snapshotting them cost 61% of bench wall-clock.
        """
        if self.tracing:
            before = {k: _snapshot(target.features.get(k)) for k in changes}
            target.features.update(changes)
            after = {k: _snapshot(target.features.get(k)) for k in changes}
        else:
            before = {}
            after = {}
            target.features.update(changes)
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
        if not self.tracing:
            raise RuntimeError(
                "cannot undo on a Reading built with tracing=False — the "
                "before/after diffs were never snapshotted"
            )
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
