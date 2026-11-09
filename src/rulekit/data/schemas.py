"""Pydantic models for every rulekit YAML document kind.

Each document declares `format: rulekit/<kind>@<version>`; the loader picks
the model from KIND_MODELS. These models are the single source of truth for
the file formats — the registry compiles from them and the web editor's
JSON Schema is exported from them.
"""

from __future__ import annotations

from typing import Literal
import math

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# lexicon
# ---------------------------------------------------------------------------


class VerbInfo(StrictModel):
    lemma: str | None = None
    past_participle: bool = False
    number: Literal["singular", "plural"] | None = None
    finite: bool | None = None


class AnaphoricForm(StrictModel):
    """Pack-owned form family; referent number is not verb agreement number."""

    paradigm: str = Field(min_length=1)
    referent_numbers: list[Literal["singular", "plural"]] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_numbers(self) -> "AnaphoricForm":
        if self.paradigm != self.paradigm.strip():
            raise ValueError("anaphoric paradigm must be trimmed")
        if len(self.referent_numbers) != len(set(self.referent_numbers)):
            raise ValueError("anaphoric referent numbers must be unique")
        return self


class LexiconEntry(StrictModel):
    senses: list[str]
    plural: str | list[str] | None = None  # noun senses: plural surface(s)
    number: Literal["singular", "plural"] | None = None  # grammatical number of this surface
    anaphoric_form: AnaphoricForm | None = None
    verb: VerbInfo | None = None  # for verb senses: irregular lemma etc.
    # An explicitly indivisible multiword noun/adverb. Unlike an ordinary
    # compositional compound, this phrase owns its full lexical identity.
    lexical_phrase: bool = False
    notes: str | None = None

    def plurals(self) -> list[str]:
        if self.plural is None:
            return []
        return [self.plural] if isinstance(self.plural, str) else list(self.plural)

    def number_for_sense(self, sense: str) -> str | None:
        """A noun/verb homograph can have different agreement in each use."""
        if sense == 'verb' and self.verb is not None and self.verb.number is not None:
            return self.verb.number
        return self.number

    @model_validator(mode="after")
    def _sense_scoped(self) -> "LexiconEntry":
        if self.verb is not None and "verb" not in self.senses:
            raise ValueError("verb info on an entry without a verb sense")
        if self.anaphoric_form is not None and "pronoun" not in self.senses:
            raise ValueError("anaphoric form on an entry without a pronoun sense")
        if self.plural is not None and "noun" not in self.senses:
            raise ValueError("plural on an entry without a noun sense")
        if self.lexical_phrase and self.senses not in (["noun"], ["adverb"], ["adjective"]):
            raise ValueError("lexical phrases require one noun, adjective or adverb sense")
        return self


class LexiconDoc(StrictModel):
    format: Literal["rulekit/lexicon@1"]
    entries: dict[str, LexiconEntry]


# ---------------------------------------------------------------------------
# categories (hierarchy + antonyms + context synonyms + attrs)
# ---------------------------------------------------------------------------


DimensionSpec = str | dict[str, int]


class DerivedAttributeDef(StrictModel):
    """A typed arithmetic property; names bind to roles, never text positions."""

    inputs: dict[str, DimensionSpec]
    expr: str = Field(min_length=1)
    result_dimension: DimensionSpec
    constants: dict[str, float] | list[str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _well_formed(self) -> "DerivedAttributeDef":
        for name in (*self.inputs, *self.constants):
            if not name.isidentifier():
                raise ValueError("formula parameter and constant names must be identifiers")
        if self.inputs.keys() & set(self.constants):
            raise ValueError("formula inputs and constants must be distinct")
        if isinstance(self.constants, dict) and any(not math.isfinite(v) for v in self.constants.values()):
            raise ValueError("formula constants must be finite")
        for dimension in (*self.inputs.values(), self.result_dimension):
            names = (dimension,) if isinstance(dimension, str) else dimension
            if any(not name.isidentifier() for name in names):
                raise ValueError("dimension names must be identifiers")
        return self


class CategoryDef(StrictModel):
    parent: str
    attrs: dict[str, float] = Field(default_factory=dict)
    formulas: dict[str, DerivedAttributeDef] = Field(default_factory=dict)
    # Explicit parameter equalities, e.g. both rectangle sides bind to a
    # square's side. Membership alone never supplies these relationships.
    parameter_bindings: dict[str, str] = Field(default_factory=dict)
    # Nominal role sets may include other nominal families (and descendants)
    # without inheriting their taxonomy or behavioral flags. No word copying.
    includes: list[str] = Field(default_factory=list)
    # Explicitly separate nominal families. Non-membership is otherwise
    # unknown; sibling categories and incomplete word lists are not negation.
    disjoint_with: list[str] = Field(default_factory=list)
    antonym: str | None = None
    # Direction for polarity-pair categories (lose=-1/acquire=+1, fewer=-1/
    # more=+1). Consumed by sign(<slot>) in rule emit expressions — the
    # polarity is DATA, derived nowhere else (the difg LOSS_VERBS lesson).
    polarity: Literal[1, -1] | None = None
    # Members denominate the SAME underlying stuff (currency: money/dollars/
    # pounds). Only such categories let an ask noun with no facts of its own
    # resolve to the unique in-store member — sibling count nouns (cat/dog in
    # 'animal') never stand in for each other.
    interchangeable: bool = False
    # Members are EXHAUSTIVE, author-vetted SUBTYPES of the category's own
    # NAME (mining candidate subtype-total-asks: 'child' -> daughter/son) —
    # the category NAME doubles as the superordinate MEASURE word. Only
    # such categories let answer.py's `_superordinate_total` sum an
    # entity's own subtype holdings into an otherwise-factless ask for the
    # category's name. Deliberately a SEPARATE opt-in flag from
    # `interchangeable`, never inferred from "has members" alone — `pet`
    # also declares members for a DIFFERENT purpose (decline-safety
    # regression coverage in `_resolve_measure_against`'s own docstring)
    # with a deliberately PARTIAL, non-exhaustive list — if
    # `_superordinate_total` read `members` directly it would silently sum
    # only the CAPTURED subset while the text's own uncaptured subtype
    # (e.g. an unresolved 'fish' relation) drops out unaccounted, a
    # confident-wrong the dev-train gate itself caught. This flag is the
    # single mandatory guard against that: a category must be explicitly
    # author-vetted as exhaustive before this consumer will touch it.
    superordinate: bool = False
    # Members are valid SUBTYPES of an open-ended superclass, but are not an
    # exhaustive ontology. Such a category may be totalled only when every
    # contributing quantity was emitted by one explicit coordinated premise
    # (for example, "N penguins and twice as many bears" -> animals). This is
    # intentionally separate from `superordinate`: closed subtype families
    # can compose facts across sentences; open classes cannot safely do so.
    coordinated_superordinate: bool = False
    # mining candidate dimension-aggregate-asks: a UNIT-FAMILY category —
    # members are EITHER a concrete unit lemma ('foot'/'pound'/'minute'/...)
    # OR a DIMENSION word that names the same family without naming a unit
    # ('height'/'weight'/'age' — all noun-sensed, so they can share a
    # `parent: noun` category with the concrete units without breaking the
    # "member carries the root sense" invariant below) OR the CATEGORY
    # NAME ITSELF, bound directly by an ask that already knows which family
    # it wants (mirrors `currency`'s own `measure: currency` precedent — a
    # bare ask noun the fact store has no literal match for still resolves
    # against the family's UNIQUE in-store member). A SEPARATE opt-in flag
    # from `interchangeable`: `answer.py`'s `_resolve_dimension_measure` is
    # consulted ONLY by the 'combined'/'average' consumers when an ask
    # opts in via `dimension_measure: true` — every other consumer keeps
    # calling `_resolve_measure`/`_resolve_measure_against`
    # (`interchangeable_categories`) exactly as before, so a dimension
    # family can never silently widen what an UNRELATED existing ask
    # resolves (the shared-function blast-radius HANDOFF invariant).
    dimension: bool = False
    # Semantic role -> noun category selected by members of this verb
    # category.  These contracts are inherited through the category tree;
    # a child may only replace a target with one of its subcategories.  The
    # grammar maps its structural slots onto the semantic role names, while
    # the vocabulary-owning category declares which nouns can fill them.
    selectional_roles: dict[str, str] = Field(default_factory=dict)
    # Optional grammatical-number refinements for those semantic roles. A
    # lexical frame may therefore distinguish a plural collection theme from
    # a singular/mass material theme without putting either vocabulary or
    # surface-form exceptions in a grammar rule. These constraints inherit
    # with the role contract and may only be added or retained by children.
    selectional_role_numbers: dict[
        str, Literal["singular", "plural"]
    ] = Field(default_factory=dict)
    notes: str | None = None

    @model_validator(mode="after")
    def _one_superordinate_contract(self) -> "CategoryDef":
        if self.attrs.keys() & self.formulas.keys():
            raise ValueError("a property cannot be both scalar and derived")
        if any(not math.isfinite(value) for value in self.attrs.values()):
            raise ValueError("category attributes must be finite")
        if any(not name.isidentifier() for pair in self.parameter_bindings.items() for name in pair):
            raise ValueError("parameter bindings must name identifiers")
        if self.superordinate and self.coordinated_superordinate:
            raise ValueError(
                "a category cannot be both closed and coordinated-only "
                "superordinate"
            )
        return self

    @model_validator(mode="after")
    def _selectional_role_names(self) -> "CategoryDef":
        for role, category in self.selectional_roles.items():
            if not role or role.strip() != role:
                raise ValueError(
                    "selectional role names must be non-empty and trimmed"
                )
            if not category or category.strip() != category:
                raise ValueError(
                    "selectional role categories must be non-empty and trimmed"
                )
        for role in self.selectional_role_numbers:
            if not role or role.strip() != role:
                raise ValueError(
                    "selectional role number names must be non-empty and trimmed"
                )
        return self


class ContextSynonym(StrictModel):
    gate: str  # governing category that must be present in the text
    forms: list[str]


class SubjectRoleDerivation(StrictModel):
    """A verb-licensed role for its grammatical subject.

    Every listed preposition is both a licence and a preservation policy:
    ``teach`` plus ``at`` may derive ``teacher at PLACE``. An unlisted PP is
    not silently dropped and does not derive an unscoped role.
    """

    role: str
    preserve_prepositions: list[str]

    @model_validator(mode="after")
    def _complete_unique_policy(self) -> "SubjectRoleDerivation":
        if not self.role:
            raise ValueError("a subject-role derivation needs a role")
        if not self.preserve_prepositions:
            raise ValueError(
                "a subject-role derivation needs at least one preserved "
                "preposition"
            )
        if len(self.preserve_prepositions) != len(
            set(self.preserve_prepositions)
        ):
            raise ValueError(
                "a subject-role derivation repeats a preserved preposition"
            )
        return self


class AdpositionRoleDef(StrictModel):
    """One declarative verb–preposition–object semantic licence.

    The three categories jointly license the role. A polysemous preposition
    therefore contributes evidence without deciding the interpretation alone.
    Proper-name objects are an explicit opt-in because their denotation is not
    available from the lexicon.
    """

    preposition_category: str
    object_category: str
    verb_category: str
    allow_name_object: bool = False


class ModifierAttachmentDef(StrictModel):
    """One noun–preposition–object attachment boundary.

    All three roles are category-gated pack knowledge. This allows a location
    to narrow the nouns that can plausibly carry that modifier without making
    the preposition globally narrow.
    """

    preposition_category: str
    object_category: str
    host_category: str


class FormulaUnitDef(StrictModel):
    """Canonical unit and the lexical family through which it may convert."""

    unit: str
    category: str


class CategoriesDoc(StrictModel):
    format: Literal["rulekit/categories@1"]
    categories: dict[str, CategoryDef] = Field(default_factory=dict)
    members: dict[str, list[str]] = Field(default_factory=dict)
    # Descriptor category -> one or more noun categories it can describe or
    # govern.  The original adjective use remains the common case; comparative
    # and preposition categories declare dimension/unit and adjunct/object
    # compatibility; noun categories license nominal compounds. Vocabulary
    # remains in packs.
    # This is deliberately many-to-many: words may belong to several
    # categories on either side, and pack extensions may add another target
    # category without redefining either lexeme.
    attribute_compatibility: dict[str, list[str]] = Field(default_factory=dict)
    # Preposition category -> noun categories that the resulting modifier may
    # attach to.  This is intentionally separate from
    # ``attribute_compatibility``: one relation licenses the PP object
    # (``about`` -> ``topic``), while this relation licenses the modified head
    # (``about the topic`` -> ``book``, but not ``egg``).
    modifier_host_compatibility: dict[str, list[str]] = Field(
        default_factory=dict
    )
    # Adverb category -> verb categories whose temporal/aspectual form it may
    # modify.  This keeps tense-sensitive lexical knowledge in pack data: a
    # rule names the two grammatical slots, while categories decide that
    # e.g. ``currently`` can modify a present holding but not a past one.
    adverb_verb_compatibility: dict[str, list[str]] = Field(
        default_factory=dict
    )
    # Object-sensitive nominal attachment frames. A frame becomes restrictive
    # only when its preposition and object categories both match; otherwise
    # the construction retains the ordinary open modifier behaviour.
    modifier_attachment_compatibility: list[ModifierAttachmentDef] = Field(
        default_factory=list
    )
    # Measure category -> noun categories whose members can bear that
    # dimension. This is deliberately separate from descriptor compatibility:
    # `shorter` can describe both a physical object and a duration, so the
    # selected unit—not the ambiguous comparative surface—must determine which
    # holder role is licensed.
    measure_holder_compatibility: dict[str, list[str]] = Field(
        default_factory=dict
    )
    # Measure category -> noun categories that may fill an ``of NOUN``
    # partitive complement.  This is pairwise on purpose: independently
    # declaring ``cup`` and ``shoe`` as partitive-capable must not license
    # the cross-product "cups of shoes".
    partitive_measure_compatibility: dict[str, list[str]] = Field(
        default_factory=dict
    )
    # Verb lemma -> subject role plus the PP forms whose restriction survives
    # in that role. This is lexical knowledge, so the mapping lives in pack
    # data; the kernel only performs the generic exact-key composition.
    subject_role_derivations: dict[str, SubjectRoleDerivation] = Field(
        default_factory=dict
    )
    # Semantic role -> one or more category-gated frames that license that
    # same exact governed PP relation. A singleton mapping retains the compact
    # form; a list expresses alternate constructions without inventing a new
    # semantic role name. The kernel joins frames and still refuses zero or
    # multiple surviving ROLES.
    adposition_roles: dict[
        str, AdpositionRoleDef | list[AdpositionRoleDef]
    ] = Field(default_factory=dict)
    # Time-sensed deictic marker -> signed distance from the document's
    # present moment.  The words and their ordering are data: the kernel only
    # compares declared numeric coordinates and never contains a temporal
    # vocabulary list of its own.
    temporal_offsets: dict[str, float] = Field(default_factory=dict)
    context_synonyms: dict[str, ContextSynonym] = Field(default_factory=dict)
    attrs: dict[str, dict[str, float]] = Field(default_factory=dict)
    formulas: dict[str, dict[str, DerivedAttributeDef]] = Field(default_factory=dict)
    parameter_bindings: dict[str, dict[str, str]] = Field(default_factory=dict)
    # Canonical units for the physical bases used by derived properties.
    # Existing conversion machinery supplies all scale factors.
    formula_units: dict[str, str | FormulaUnitDef] = Field(default_factory=dict)
    formula_constants: dict[str, float] = Field(default_factory=dict)
    property_aliases: dict[str, str] = Field(default_factory=dict)
    part_counts: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _compatibility_targets(self) -> "CategoriesDoc":
        for family, compatibility in (
            ("attribute", self.attribute_compatibility),
            ("modifier-host", self.modifier_host_compatibility),
            ("adverb-verb", self.adverb_verb_compatibility),
            ("measure-holder", self.measure_holder_compatibility),
            ("partitive-measure", self.partitive_measure_compatibility),
        ):
            for source, targets in compatibility.items():
                if not targets:
                    raise ValueError(
                        f"{family} compatibility {source!r} needs a noun category"
                    )
                if len(targets) != len(set(targets)):
                    raise ValueError(
                        f"{family} compatibility {source!r} repeats a noun category"
                    )
        attachment_keys = [
            (
                frame.preposition_category,
                frame.object_category,
                frame.host_category,
            )
            for frame in self.modifier_attachment_compatibility
        ]
        if len(attachment_keys) != len(set(attachment_keys)):
            raise ValueError("modifier attachment compatibility repeats a frame")
        return self

    @model_validator(mode="after")
    def _complete_unique_adposition_frames(self) -> "CategoriesDoc":
        for role, declared in self.adposition_roles.items():
            frames = declared if isinstance(declared, list) else [declared]
            if not frames:
                raise ValueError(f"adposition role {role!r} needs a frame")
            signatures = [
                (
                    frame.preposition_category,
                    frame.object_category,
                    frame.verb_category,
                    frame.allow_name_object,
                )
                for frame in frames
            ]
            if len(signatures) != len(set(signatures)):
                raise ValueError(
                    f"adposition role {role!r} repeats an identical frame"
                )
        return self


# ---------------------------------------------------------------------------
# numbers (number words, scales, multipliers, fractions, operators)
# ---------------------------------------------------------------------------


class NumbersDoc(StrictModel):
    format: Literal["rulekit/numbers@1"]
    numbers: dict[str, float] = Field(default_factory=dict)  # "seven" -> 7
    scales: dict[str, float] = Field(default_factory=dict)  # "dozen" -> 12
    multipliers: dict[str, float] = Field(default_factory=dict)  # "twice" -> 2
    fractions: dict[str, float] = Field(default_factory=dict)  # "half" -> 0.5
    # Count-requiring plural surface -> singular fraction lemma.
    fraction_plurals: dict[str, str] = Field(default_factory=dict)
    operators: dict[str, str] = Field(default_factory=dict)  # "plus" -> "+"
    currencies: dict[str, str] = Field(default_factory=dict)  # "$" -> dollar
    percents: dict[str, float] = Field(default_factory=dict)  # "percent" -> 0.01


# ---------------------------------------------------------------------------
# obligations (role -> needs)
# ---------------------------------------------------------------------------


class RoleObligation(StrictModel):
    needs: list[str]
    optional: list[str] = Field(default_factory=list)  # subset of needs
    direction: dict[str, Literal["left", "right", "either"]] = Field(default_factory=dict)
    notes: str | None = None

    @model_validator(mode="after")
    def _optional_subset(self) -> "RoleObligation":
        extra = set(self.optional) - set(self.needs)
        if extra:
            raise ValueError(f"optional needs not declared in needs: {sorted(extra)}")
        return self


class ObligationsDoc(StrictModel):
    format: Literal["rulekit/obligations@1"]
    roles: dict[str, RoleObligation]


# ---------------------------------------------------------------------------
# pattern rules + asks
# ---------------------------------------------------------------------------

SLOT_TYPES = (
    "number", "ordinal", "scale_label", "fraction", "multiplier", "nonunit_multiplier", "ratio",
    "name", "noun", "plural", "counted",
    "entity", "verb", "auxiliary", "modal", "future_modal",
    "pronoun", "word",
    "adjective", "possessed", "qualified", "percent",
    # an EVENT verb: verb-sensed and NOT in the `state` category — the
    # verbal logic rules gate on this so 'is'/'was' sentences stay the
    # copular rules' territory (the v1 'be'-twin lesson)
    "nonstate_verb",
    # a NAME-SENSED unit ONLY — unlike `name`, a resolved pronoun never
    # satisfies it. The bare-plural universal rule reads "Mushrooms are
    # fungi" as a GENERIC (∀), and a pronoun subject is definite reference
    # ("They are dogs" states a fact about the antecedents) — admitting it
    # would mint a universal from a ground statement.
    "proper_name",
    # a PREPOSITION-sensed unit — the composition rules capture the PP's
    # preposition as its own slot (VerbalRelation.prep) so the relation's
    # segmentation is match-token work, never key surgery
    "preposition",
    # a plural common noun that can head a GENERIC: sense noun, number
    # plural, no `owner` (a possessive subject is definite reference), no
    # `qualifier` (compound generics stay unread — monotone-safe), and NO
    # count value — merge-count folds "Three dogs" into one plural NOUN
    # unit, and "Three dogs are pets" is about three particular dogs, not
    # dogkind (caught by an adversarial probe, not the first test round).
    "bare_plural",
    # A bare-plural GENERIC that may carry a compound modifier. Like
    # `bare_plural`, this refuses possessive and counted units; unlike it, the
    # complete qualified class phrase remains available to the emitter. This
    # is the structural shape of "all head teachers", not a license for any
    # particular modifier.
    "generic_plural",
    # a COORDINATE TUPLE ("(3,4)", "(1,2)") — numbers.py's _TUPLE gives it
    # value_kind "tuple" and a `components` feature; senses.py gives it the
    # `tuple` sense. Structurally disjoint from every other slot type: no
    # scalar-valued unit is ever a tuple and vice versa, so a `point` slot can
    # never tie-break collide with a `number` slot.
    "point",
    # an ISO DATE ("2024-01-01") — numbers.py's _ISO_DATE gives it value_kind
    # "date" and a `components` feature; senses.py gives it the `date` sense.
    # Disjoint from every scalar slot type on the same argument as `point`: a
    # date carries no scalar, so it can never collide with a `number` slot.
    "date",
    # a CHEMICAL FORMULA ("H2O", "NaCl") — numbers.py's `_FORMULA`, gated on
    # every symbol being a key in the element table so an acronym-shaped word
    # cannot masquerade as a compound.
    "formula",
    # mining candidate conjunct-comparative-quantities: a BARE common-noun
    # holder ("the vehicle", "the animal") — sense noun, no `owner` feature
    # (never a possessive-merged noun, see `possessed`), no `qualifier`
    # feature (never an attribute-merged noun, see `qualified`), singular
    # only. Structurally DISJOINT from both `possessed` and `qualified` (no
    # unit can carry BOTH a bare identity and either merge tag), and from
    # `name` (a name's sense is never `noun`) — so a new ask built on this
    # type can never tie-break collide with ask/how-many-entity-possessed or
    # ask/how-many-entity-qualified the way widening `who` to `type: entity`
    # on ask/how-many-entity itself already tried and reverted (see that
    # ask's own comment). Singular-only so it cannot steal a plural
    # common-noun subject from the plural-combined ask family.
    "common_noun",
)


class MatchToken(StrictModel):
    """One position in a match sequence: a literal or a typed/gated slot."""

    # A literal fold, or an ALTERNATION over folds ("one of these words").
    #
    # The alternation exists because a CATEGORY cannot always express the
    # choice: a category roots at exactly ONE sense (registry: a member lacking
    # the root sense is a CompileError), so words carrying an off-class sense
    # can never join one -- 'any' is article-sensed, 'many' is interrogative
    # (not a root sense at all), 'second'/'average' are the documented lexicon
    # traps. `packs/arithmetic/rules/core.yaml` names the gap outright: "there
    # is no OR primitive over match tokens".
    #
    # PREFER A CATEGORY WHEN ONE FITS. A category NAME is addressable by
    # `span_blocks` from other rules and is visible to the blast-radius lint;
    # an alternation is deliberately neither -- it is grammatical skeleton,
    # scoped to the rule that writes it. Reach for it only where a category is
    # structurally impossible. The `alternation-should-be-category` lint check
    # flags the cases where one would have fitted.
    #
    # It contributes ZERO gate depth (see patterns._ask_rank) BY DESIGN: an
    # alternation must rank exactly as the N separate rules it replaces, or a
    # collapse stops being a provable no-op.
    lit: str | list[str] | None = None
    slot: str | None = None
    type: str | None = None  # builtin slot type
    cat: str | None = None  # category gate (slot form)
    # OPT-IN semantic role boundary for an entity slot. Proper names and
    # resolved pronouns retain the ordinary `entity` path; a COMMON NOUN must
    # additionally belong to this pack-declared category. This lets a rule
    # say which nouns may act as holders/participants without either reducing
    # the slot to names or maintaining an open-ended negative blacklist.
    common_noun_cat: str | None = None
    # OPT-IN: a category-gated noun must also be a condensed counted unit
    # ("4 years", not bare "year"/"years"). This is the category-aware
    # counterpart of `type: counted`: the number/noun agreement remains the
    # generic counted-unit machinery, while the noun lemma must satisfy the
    # pack-declared category. Defaults False so every existing category slot
    # remains byte-identical.
    counted: bool = False
    # OPT-IN: a category-gated noun must also be an owned/possessive merged
    # unit ("Aven's age", not bare "age"). This composes the existing
    # `type: possessed` structure with a semantic noun category without
    # weakening the schema invariant that a slot names exactly one type OR
    # category gate. Defaults False so existing category slots are unchanged.
    possessed: bool = False
    # OPT-IN: a category-gated noun must also be an attribute/compound merged
    # unit ("science courses", not bare "courses"). This composes the
    # existing `type: qualified` structure with a semantic noun category, so
    # rules can constrain the head without losing the full qualified phrase.
    # Defaults False so existing category slots are unchanged.
    qualified: bool = False
    # OPT-IN: a qualified noun carries an explicit numeric value on its
    # hyphenated nominal modifier ("a 100-page book").  The analyzer keeps
    # this distinct from an ordinary counted head ("100 page books"), and
    # matching additionally requires the pack-declared modifier-measure ->
    # head-holder relationship.  This lets vocabulary extend the construction
    # without teaching the kernel that pages belong to books.
    attributive_counted: bool = False
    # OPT-IN category boundary for the retained modifier of a qualified noun.
    # The head still uses the slot's ordinary `cat`; this independently gates
    # the internal noun/adjective modifier after condensation.
    qualifier_cat: str | None = None
    # OPT-IN: every retained modifier, including nested qualifiers, must be
    # in `qualifier_cat`. Use when a query or emitter projects the description
    # to its head and cannot preserve additional identity restrictions.
    all_qualifiers: bool = False
    # OPT-IN grammatical-number constraint on any scalar slot. The matched
    # unit must carry the declared singular/plural feature; it never infers a
    # word's number. This is separate from `same_number`, which relates slots.
    number: Literal["singular", "plural"] | None = None
    # OPT-IN: a `type: number` slot must bind a standalone scalar, not the
    # condensed counted-noun unit produced from "6 marbles". Both carry
    # `value_kind: count`, so the ordinary number type intentionally accepts
    # both; rules whose grammar elides the measure noun need this additional
    # structural distinction. Multiword scalars such as "twenty three" remain
    # valid because this checks the unit's sense, not its original word count.
    standalone: bool = False
    # OPT-IN: a scalar number must be integral. Calendar-year coordinates are
    # the first consumer; range or era policy remains independently authored.
    integer: bool = False
    # OPT-IN inclusive scalar bounds. These are generic numeric structure;
    # the meaning of a bound (for example, a four-digit calendar year) stays
    # in the rule pack that declares it.
    value_positive: bool = False
    value_min: float | None = None
    value_max: float | None = None
    # OPT-IN: a fraction used as a part of one finite whole must remain in
    # [0, 1]. Improper fractions remain valid in ratios, affine relations, and
    # other unbounded scalar positions; only an authored part-of-whole slot
    # declares this semantic magnitude boundary.
    fraction_within_whole: bool = False
    # OPT-IN: a WORD or slash fraction used as a natural-language comparison
    # must remain in [0, 1]. Percentage surfaces are deliberately exempt:
    # "150 percent more" is ordinary English, while "three halves more" and
    # "seventy ninths as many" should use a percentage or multiplier frame.
    # This is a surface boundary, unlike `fraction_within_whole`, which also
    # constrains percentages because the underlying quantity is part of one
    # finite whole.
    word_fraction_within_whole: bool = False
    # OPT-IN: a fraction that contributes a comparison or change magnitude
    # must be strictly positive.  Zero remains valid for independently useful
    # part-of-pool and partition statements; rules whose standard would become
    # mathematically irrelevant declare this narrower boundary explicitly.
    fraction_positive: bool = False
    # GENERATION-ONLY rendering choice for standalone unit fractions in
    # contexts where an explicit numerator is clearer ("one third" rather
    # than bare "third"). Matcher acceptance remains unchanged.
    generation_explicit_unit_fraction: bool = False
    # GENERATION-ONLY: expose both the singular lexicon entry and its declared
    # plural surfaces for an otherwise number-neutral noun category slot.
    # Matcher acceptance remains unchanged. This is for constructions whose
    # grammar genuinely admits either number while deterministic generation
    # should exercise both (for example, a singular wallet or plural shoes).
    generation_all_numbers: bool = False
    # OPT-IN: a common-noun slot must be a complete argument, not a floating
    # bare singular. Names, resolved pronouns, counted nouns, possessed nouns,
    # and bare plurals are already complete; another common noun needs a
    # pack-declared definite article / possessive determiner immediately to
    # its left. Defaults False so existing slots are unchanged.
    referential: bool = False
    # GENERATION-ONLY rendering choice for a referential noun whose required
    # determiner is already an explicit preceding literal in the rule. The
    # matcher still enforces `referential`; realization selects the bare head
    # so the explicit literal and filler do not produce "the the rest".
    generation_bare_reference: bool = False
    # OPT-IN exception to `referential`: nouns in this category may occur bare.
    # This is for independently licensed adverbial nouns ("by day", "at
    # night"), not a general weakening of noun-phrase definiteness.
    bare_reference_category: str | None = None
    # OPT-IN: nouns in this category must occur without an article or
    # possessive determiner at this slot. This is narrower than `bare: true`,
    # which governs compound/possessive noun structure for every filler: a
    # normal common noun can still be definite while a named calendar member
    # in the same slot stays bare ("in April", never "in the April").
    determinerless_category: str | None = None
    # OPT-IN: require the slot's noun to be BARE — no compound modifier
    # (condense merge-compound) and no possessive owner. A category gate matches
    # on the unit's LEMMA, and a compound noun keeps its HEAD's lemma, so "the
    # dot product" satisfies a `statistic`-gated slot exactly as "the product"
    # does — and answers 720 (the product of all six components) for a dot
    # product whose answer is 32.
    #
    # This is not the default: many compounds can validly fill a head-noun
    # category. Use it when a construction cannot preserve the distinction.
    # The restriction follows resolved pronouns and excludes instance labels.
    bare: bool = False
    # A class-level noun may carry an attribute modifier, but no owner or
    # instance label. Use when emitted facts preserve the class rather than
    # the identity of one possessed/labeled object.
    class_only: bool = False
    # The noun names an item but states no numeric count or measured extent.
    uncounted: bool = False
    # OPT-IN phrase capture: this slot binds a RUN of units (greedy-longest,
    # backtracking against the rest of the sequence; a FINAL span must reach
    # the sentence end). Its value is the canonical phrase — per-token lemma
    # normalization, articles/punct dropped, NOTHING looser: logic prose
    # distinguishes classes one NP-internal word apart, and a phrase key is
    # what keeps "opera singer" from answering for "singer" (patterns.
    # _canonical_phrase, model.Atom). Defaults False: every existing slot
    # binds exactly one unit, byte-identical.
    span: bool = False
    enumeration_cat: str | None = None
    enumeration_min_members: int = Field(default=1, ge=1)
    # Each list member is one counted nominal rather than an uncounted
    # class/name. Per-item emission retains that nominal's scalar value and
    # reference; it does not flatten a count into a textual class key.
    enumeration_counted: bool = False
    enumeration_qualified: bool = False
    # OPT-IN, span-only: name a CATEGORY whose members may never be swallowed
    # into the captured phrase (e.g. packs/logic's `negation`) — a polarity
    # word hidden inside a phrase key would bury the negation where no
    # consumer can see it, so the match FAILS instead. Category name only;
    # the members live in the pack (constitution rule 1).
    span_blocks: str | list[str] | None = None
    # OPT-IN: this token may only match with NOTHING MEANINGFUL BEFORE IT — every
    # preceding unit must be skippable. A match sequence is contiguous (modulo
    # SKIPPABLE_SENSES) but FLOATS: match_all retries at every start offset, so a
    # shape mined on one construction will happily land on another that merely
    # contains the same token run.
    #
    # That is a grammar bug, not a tuning knob. English fronts the auxiliary to
    # ask a question ("IS Mary a student?" — subject-auxiliary inversion, so the
    # subject FOLLOWS the copula), but leaves it in place in an embedded
    # declarative ("…that Jim is a Knicks player" — the subject PRECEDES it).
    # `is <name> <noun>` reads the first correctly and, floating onto the second,
    # binds the complement's proper-noun modifier ('Knicks') as the subject and
    # drops the real one. Anchoring says: this literal is the FRONTED auxiliary,
    # not any copula that happens to appear.
    #
    # Structure, never lexicon — it constrains WHERE a token may match, not which
    # words exist. Defaults False so every existing ask and pattern rule stays
    # byte-identical (the "opt-in parameter, defaulted to old behavior" rule for
    # any change to a shared matcher).
    at_start: bool = False
    # OPT-IN: this LITERAL may match a unit whose sense is SKIPPABLE. The
    # auto-skip loop normally walks straight past articles, so `{lit: any}`
    # can never see 'any' (an article-sensed word, difg-mined) — with this
    # flag the skip stops AT the matching word and consumes it as the token.
    # Only the named word(s) are affected — an ALTERNATION claims whichever
    # of its options is present: other skippables are still skipped,
    # and a sentence without the word fails the match exactly as any lit
    # does. Default False — every existing rule is byte-identical.
    consume_skipped: bool = False
    # OPT-IN: fail the match when a unit of the named CATEGORY was skipped
    # IMMEDIATELY before this token. The auto-skip makes articles invisible,
    # so "...that A Czech is a European?" binds subj='czech' as if the
    # existential were a name — the campaign closure's one real hazard
    # (negative-results §3). `blocks_skipped: indefinite_article` on a subj
    # slot refuses the indefinite while 'the' (definite reference, "The USS
    # Lyon") passes. Category name as structure; members live in packs; a
    # registry without the category is a NO-OP by construction.
    blocks_skipped: str | None = None
    # OPT-IN (span slots): the span may not capture a MERGED COUNTED NOUN
    # ('3 apples' — sense noun carrying a value feature). The verbal logic
    # rules set this so arithmetic material stays the fold's: a consumed
    # sentence suppresses fold facts, and 'Tom bought 3 apples' must keep
    # its Quantity. Bare values ('in 1946') pass — dates are logic prose.
    span_blocks_counted: bool = False
    # OPT-IN: this verb slot only matches the verb's BARE form (fold ==
    # lemma). English marks plural agreement on the bare present ("Writers
    # CREATE ideas" vs "Mary CREATES ideas"), so on a verb after a
    # bare-plural/name-fallback subject this is the structural signal that
    # the sentence is a GENERIC and not a ground statement — the verbal
    # sibling of the copular rules' plural-agreeing {lit: are}. Defaults
    # False: every existing verb slot is byte-identical.
    bare_form: bool = False
    # OPT-IN: this verb slot must carry a finite-capable surface. Productive
    # non-finite ``-ing`` forms whose registered lemma differs are refused;
    # bare present, third-person present, and simple past remain available.
    # This is intentionally separate from ``bare_form`` because a matrix verb
    # such as "wants/wanted" is finite without being the lemma surface.
    finite_form: bool = False
    # OPT-IN: require a slot to bind one original token, not a unit produced by
    # condensation. Logic implication keys use this on verb slots because a
    # merged particle verb intentionally keeps the base verb's lemma ("gets
    # up" -> "get" for arithmetic event polarity); reusing that lemma as a
    # logical predicate would conflate "get up early" with "get early".
    # Defaults False so every existing rule remains byte-identical.
    single_word: bool = False
    # OPT-IN: this verb slot only matches an inflected present participle:
    # the surface fold ends in ``-ing`` and differs from its registered
    # lemma. This is the grammatical signal for an active reduced relative
    # ("Everyone carrying boxes ..."), while a finite/bare verb — including
    # a lemma that happens to end in ``-ing`` — refuses. Defaults False so
    # every existing rule remains byte-identical.
    present_participle: bool = False
    # OPT-IN: this verb slot only matches an inflected past participle whose
    # surface has regular ``-ed`` or productive ``-en`` morphology and differs
    # from its registered lemma. This is the grammatical signal used by
    # direct passive readers ("is produced by ..."); a finite present or bare
    # verb after the copula must not masquerade as passive syntax. Defaults
    # False so every existing rule remains byte-identical. Irregular forms
    # without either suffix deliberately decline until morphology represents
    # them structurally.
    past_participle: bool = False
    opt: list["MatchToken"] | None = None  # optional sub-sequence

    @property
    def lit_options(self) -> tuple[str, ...]:
        """The folds this token accepts — the ONE definition every caller uses.

        A scalar `lit` is a one-element tuple, so the matcher, the prefilter and
        the overlap linter all take the identical code path whether or not the
        author wrote an alternation.
        """
        if self.lit is None:
            return ()
        return (self.lit,) if isinstance(self.lit, str) else tuple(self.lit)

    @model_validator(mode="after")
    def _one_form(self) -> "MatchToken":
        if isinstance(self.lit, list):
            # An alternation of one is a scalar written the long way. Refusing
            # it keeps ONE spelling per meaning, which is what lets a collapse
            # be diffed as a no-op.
            if len(self.lit) < 2:
                raise ValueError(
                    "a `lit` alternation needs at least two options — "
                    "write a plain string for one"
                )
            if any(not isinstance(x, str) or not x for x in self.lit):
                # ⚠ YAML 1.1 coerces a bare `no`/`off`/`yes`/`on` to a BOOLEAN,
                # and inside a list that is far easier to miss than at the
                # scalar `lit: 'no'` the logic pack already quotes. Name it.
                raise ValueError(
                    f"`lit` alternation options must be non-empty strings, got "
                    f"{self.lit!r} — quote YAML booleans like 'no'/'off'/'yes'"
                )
            if len(set(self.lit)) != len(self.lit):
                raise ValueError(f"`lit` alternation has duplicate options: {self.lit!r}")
        forms = [self.lit is not None, self.slot is not None, self.opt is not None]
        if sum(forms) != 1:
            raise ValueError("a match token is exactly one of lit/slot/opt")
        if self.span:
            # a span slot captures a RUN of units; it is gated by span_blocks
            # (and by what the surrounding tokens demand), never by type/cat
            if self.slot is None:
                raise ValueError("`span` only qualifies a slot")
            if (
                self.type is not None
                or self.cat is not None
                or self.common_noun_cat is not None
                or self.bare
                or self.uncounted
                or self.counted
                or self.possessed
                or self.qualified
                or self.attributive_counted
                or self.qualifier_cat is not None
                or self.all_qualifiers
                or self.number is not None
                or self.standalone
                or self.integer
                or self.value_positive
                or self.value_min is not None
                or self.value_max is not None
                or self.fraction_within_whole
                or self.word_fraction_within_whole
                or self.fraction_positive
                or self.generation_explicit_unit_fraction
                or self.generation_all_numbers
                or self.referential
                or self.generation_bare_reference
                or self.bare_reference_category is not None
                or self.determinerless_category is not None
                or self.bare_form
                or self.finite_form
            ):
                raise ValueError(
                    "a span slot takes no "
                    "type/cat/bare/counted/possessed/qualified/attributive_counted/"
                    "qualifier_cat/all_qualifiers/number/standalone/integer/value bounds/"
                    "fraction_within_whole/word_fraction_within_whole/"
                    "fraction_positive/generation_explicit_unit_fraction/"
                    "generation_all_numbers/"
                    "referential/generation_bare_reference/"
                    "determinerless_category/"
                    "common_noun_cat/bare_form/finite_form"
                )
        elif self.slot is not None and (self.type is None) == (self.cat is None):
            raise ValueError("a slot needs exactly one of type/cat")
        if self.counted and self.cat is None:
            raise ValueError("`counted` only qualifies a category-gated slot")
        if self.uncounted and (self.counted or self.type == "counted" or self.attributive_counted):
            raise ValueError("`uncounted` contradicts a counted slot")
        if self.possessed and self.cat is None:
            raise ValueError("`possessed` only qualifies a category-gated slot")
        if self.qualified and self.cat is None:
            raise ValueError("`qualified` only qualifies a category-gated slot")
        if self.common_noun_cat is not None and self.type != "entity":
            raise ValueError(
                "`common_noun_cat` only qualifies a `type: entity` slot"
            )
        if self.counted and self.possessed:
            raise ValueError("a category slot cannot be both counted and possessed")
        # Counted qualified nominals are a genuine composed form ("3 large
        # bags"). The analyzer already preserves both the scalar and the
        # qualifier on one condensed unit; generation now mirrors that form.
        if self.attributive_counted and not (
            self.qualified or self.type == "qualified"
        ):
            raise ValueError(
                "`attributive_counted` requires a qualified noun slot"
            )
        if self.attributive_counted and (self.counted or self.possessed):
            raise ValueError(
                "`attributive_counted` cannot be counted or possessed"
            )
        if self.qualifier_cat is not None and not (
            self.qualified or self.type == "qualified"
        ):
            raise ValueError("`qualifier_cat` requires a qualified noun slot")
        if self.all_qualifiers and self.qualifier_cat is None:
            raise ValueError("`all_qualifiers` requires `qualifier_cat`")
        if self.possessed and self.qualified:
            raise ValueError("a category slot cannot be both possessed and qualified")
        if self.number is not None and self.slot is None:
            raise ValueError("`number` only qualifies a slot")
        if self.standalone and self.type != "number":
            raise ValueError(
                "`standalone` only qualifies a `type: number` slot"
            )
        if self.integer and self.type != "number":
            raise ValueError("`integer` only qualifies a `type: number` slot")
        if (
            self.value_positive or self.value_min is not None or self.value_max is not None
        ) and self.type not in {"number", "ratio", "counted"} and not self.counted:
            raise ValueError(
                "`value_positive`/`value_min`/`value_max` only qualify number, ratio, "
                "or counted slots"
            )
        if (
            self.value_min is not None
            and self.value_max is not None
            and self.value_min > self.value_max
        ):
            raise ValueError("`value_min` cannot exceed `value_max`")
        if self.fraction_within_whole and self.type != "fraction":
            raise ValueError(
                "`fraction_within_whole` only qualifies a `type: fraction` slot"
            )
        if self.word_fraction_within_whole and self.type != "fraction":
            raise ValueError(
                "`word_fraction_within_whole` only qualifies a "
                "`type: fraction` slot"
            )
        if self.fraction_positive and self.type != "fraction":
            raise ValueError(
                "`fraction_positive` only qualifies a `type: fraction` slot"
            )
        if self.generation_explicit_unit_fraction and self.type != "fraction":
            raise ValueError(
                "`generation_explicit_unit_fraction` only qualifies a "
                "`type: fraction` slot"
            )
        if self.generation_all_numbers and (
            self.cat is None or self.number is not None
        ):
            raise ValueError(
                "`generation_all_numbers` requires a number-neutral "
                "category-gated slot"
            )
        if self.referential and self.slot is None:
            raise ValueError("`referential` only qualifies a slot")
        if self.generation_bare_reference and not self.referential:
            raise ValueError(
                "`generation_bare_reference` requires `referential: true`"
            )
        if self.bare_reference_category is not None and not self.referential:
            raise ValueError(
                "`bare_reference_category` requires `referential: true`"
            )
        if self.determinerless_category is not None and not self.referential:
            raise ValueError(
                "`determinerless_category` requires `referential: true`"
            )
        if self.enumeration_min_members != 1 and self.enumeration_cat is None:
            raise ValueError("enumeration_min_members requires enumeration_cat")
        if self.enumeration_counted and self.enumeration_cat is None:
            raise ValueError("enumeration_counted requires enumeration_cat")
        if self.enumeration_qualified and self.enumeration_cat is None:
            raise ValueError("enumeration_qualified requires enumeration_cat")
        if self.enumeration_cat is not None and not self.span:
            raise ValueError("enumeration_cat requires a span")
        if self.span_blocks is not None and not self.span:
            raise ValueError("`span_blocks` only qualifies a span slot")
        if self.bare and self.slot is None:
            raise ValueError("`bare` only qualifies a slot")
        if self.class_only and (self.slot is None or self.possessed or self.type == "possessed"):
            raise ValueError("`class_only` requires a non-possessed slot")
        if self.finite_form and self.slot is None:
            raise ValueError("`finite_form` only qualifies a slot")
        if self.finite_form and self.bare_form:
            raise ValueError("a verb slot cannot require both finite and bare form")
        if self.bare and self.type in ("possessed", "qualified"):
            # `possessed`/`qualified` are DEFINED by carrying an owner/qualifier,
            # which is exactly what `bare` forbids — the combination is always
            # false, so it is a authoring mistake, not a narrow gate.
            raise ValueError(f"`bare` contradicts type {self.type!r} (always false)")
        if self.bare and self.possessed:
            raise ValueError("`bare` contradicts `possessed` (always false)")
        if self.bare and self.qualified:
            raise ValueError("`bare` contradicts `qualified` (always false)")
        if self.consume_skipped and self.lit is None:
            raise ValueError("`consume_skipped` only qualifies a lit")
        if self.at_start and self.opt is not None:
            # An OPTIONAL sub-sequence that must sit at the start is either not
            # optional or not at the start — the anchor belongs on a token inside
            # the group, where it says something. Same rule as `bare` above: a
            # combination that can never mean what it looks like is an authoring
            # mistake, so it fails loudly at load rather than matching nothing.
            raise ValueError("`at_start` does not qualify an `opt` group")
        if self.type is not None and self.type not in SLOT_TYPES:
            raise ValueError(f"unknown slot type {self.type!r}")
        return self


class AttributeCompatibilityPredicate(StrictModel):
    """The descriptor and noun slots participating in a compatibility check.

    The historical field names remain ``attribute``/``noun`` because the
    first consumer was adjective/noun compatibility.  The descriptor may now
    also be comparative- or preposition-rooted; the pack-declared category
    pair remains the sole lexical authority.
    """

    attribute: str
    noun: str
    # Optional boundary: undeclared descriptors retain the existing open frame.
    when_declared: bool = False


class ModifierHostCompatibilityPredicate(StrictModel):
    """Relate an optional PP to a nominal or verbal host."""

    modifier: str
    host: str
    object: str | None = None
    host_type: Literal["noun", "verb"] = "noun"
    nominal_host: str | None = None

    @model_validator(mode="after")
    def _different_slots(self) -> "ModifierHostCompatibilityPredicate":
        if self.host_type == "verb" and self.object is None:
            raise ValueError("a verbal modifier requires its object slot")
        slots = [self.modifier, self.host]
        if self.nominal_host is not None:
            if self.host_type != "verb":
                raise ValueError("nominal_host is an alternative to a verbal host")
            slots.append(self.nominal_host)
        if self.object is not None:
            slots.append(self.object)
        if len(slots) != len(set(slots)):
            raise ValueError(
                "modifier-host compatibility needs distinct role slots"
            )
        return self


class AdverbVerbCompatibilityPredicate(StrictModel):
    """Relate an optional adverb to the finite verb it modifies."""

    adverb: str
    verb: str

    @model_validator(mode="after")
    def _different_slots(self) -> "AdverbVerbCompatibilityPredicate":
        if self.adverb == self.verb:
            raise ValueError(
                "adverb-verb compatibility needs distinct role slots"
            )
        return self


class BoundRequiresTypePredicate(StrictModel):
    """Require one slot type only when another optional slot was bound."""

    bound: str
    slot: str
    type: str

    @model_validator(mode="after")
    def _known_type(self) -> "BoundRequiresTypePredicate":
        if self.type not in SLOT_TYPES:
            raise ValueError(f"unknown slot type {self.type!r}")
        return self


class BoundRequiresCategoryPredicate(StrictModel):
    """Require a slot category only when another optional slot was bound."""

    bound: str
    slot: str
    cat: str
    bound_cat: str | None = None
    # Semantic entity roles commonly license open proper names alongside a
    # positive common-noun category. This stays opt-in so existing conditional
    # category predicates retain their exact membership-only behavior.
    allow_proper_name: bool = False


class BoundRejectsCategoryPredicate(StrictModel):
    """Reject a slot category only when an optional slot was bound."""

    bound: str
    slot: str
    cat: str


class CategoryRequiresBoundPredicate(StrictModel):
    """Require an optional slot when another slot belongs to a category."""

    slot: str
    cat: str
    bound: str

    @model_validator(mode="after")
    def _different_slots(self) -> "CategoryRequiresBoundPredicate":
        if self.slot == self.bound:
            raise ValueError(
                "category-requires-bound needs two different slots"
            )
        return self


class BoundRequiresFormPredicate(StrictModel):
    """Require verb morphology only when another optional slot was bound."""

    bound: str
    slot: str
    form: Literal["bare", "finite"]


class OwnerMatchesPredicate(StrictModel):
    """Require a determiner slot to be the possessed noun's exact owner."""

    owner: str
    possessed: str

    @model_validator(mode="after")
    def _different_slots(self) -> "OwnerMatchesPredicate":
        if self.owner == self.possessed:
            raise ValueError("owner matching needs two different slots")
        return self


class PolarityCompatibilityPredicate(StrictModel):
    """Reject contradictory declared polarity within category scopes.

    Each slot is paired with the category subtree whose polarity counts.
    A slot with no polarity-bearing membership inside its scope is neutral.
    """

    slots: list[str] = Field(min_length=2)
    categories: list[str] = Field(min_length=2)

    @model_validator(mode="after")
    def _parallel_scopes(self) -> "PolarityCompatibilityPredicate":
        if len(self.slots) != len(self.categories):
            raise ValueError(
                "polarity compatibility needs one category per slot"
            )
        if len(self.slots) != len(set(self.slots)):
            raise ValueError("polarity compatibility repeats a slot")
        return self


class ProportionalDeltaCompatibilityPredicate(StrictModel):
    """Keep a proportional decrease inside the non-negative domain.

    ``fraction`` supplies the magnitude and ``direction`` supplies a declared
    polarity inside ``direction_cat``. Positive deltas are unbounded; a
    negative delta may be at most one, because ``1 - fraction`` is the emitted
    relation factor.
    """

    fraction: str
    direction: str
    direction_cat: str

    @model_validator(mode="after")
    def _different_slots(self) -> "ProportionalDeltaCompatibilityPredicate":
        if self.fraction == self.direction:
            raise ValueError(
                "proportional delta needs different fraction/direction slots"
            )
        return self


class VerbRoleCompatibilityPredicate(StrictModel):
    """Constrain lexical roles only for a declared trigger class.

    The historical field names are ``verb``/``verb_cat`` because quantitative
    event verbs are the usual trigger. The same structural relation also
    supports another category-compatible trigger, such as an optional
    possessive determiner, provided its slot and declared category share a
    root sense. Positive constraints admit proper names or common nouns in
    ``role_cat``.
    A separately declared ``allow_plural_class`` lets a plural noun occupy a
    comparison-standard role as a measured class rather than an event actor.
    Negative constraints reject roles in ``excluded_role_cat``. Exactly one
    role boundary must be declared.
    """

    verb: str
    roles: list[str] = Field(min_length=1)
    verb_cat: str
    role_cat: str | None = None
    excluded_role_cat: str | None = None
    allow_plural_class: bool = False
    # Some triggers live in optional grammar, such as a third-person
    # possessive determiner inside an optional PP. When absent, that trigger
    # contributes no contrary evidence; when present, the ordinary category
    # and role checks apply unchanged.
    allow_unbound_trigger: bool = False

    @model_validator(mode="after")
    def _valid_boundary(self) -> "VerbRoleCompatibilityPredicate":
        if len(self.roles) != len(set(self.roles)):
            raise ValueError("verb-role compatibility repeats a role slot")
        if (self.role_cat is None) == (self.excluded_role_cat is None):
            raise ValueError(
                "verb-role compatibility needs exactly one of "
                "role_cat/excluded_role_cat"
            )
        if self.allow_plural_class and self.role_cat is None:
            raise ValueError(
                "plural comparison classes require a positive role category"
            )
        return self


class VerbRolesCompatibilityPredicate(StrictModel):
    """Map construction slots onto category-owned semantic verb roles.

    The governing verb's most-specific applicable category supplies the role
    targets through ``CategoryDef.selectional_roles``.  Sibling categories
    remain alternative complete frames; constraints from two senses are never
    mixed. Proper names and plural comparison classes are construction-level
    permissions because they are properties of the surface frame, not lexical
    properties of the governing verb.
    """

    verb: str
    roles: dict[str, list[str]]
    frame_categories: list[str] = Field(default_factory=list)
    # Historical role predicates deliberately leave verbs without a declared
    # lexical frame open. A construction that claims a semantically complete
    # direct relation can opt into a positive contract instead: at least one
    # applicable category-owned frame must exist and accept every mapped role.
    require_declared_frame: bool = False
    allow_proper_name: list[str] = Field(default_factory=list)
    allow_plural_class: list[str] = Field(default_factory=list)
    # A surface group pronoun may name an as-yet unresolved participant
    # group. Unlike plural-class permission, this never licenses arbitrary
    # plural common nouns to bypass their actor category.
    allow_plural_pronoun: list[str] = Field(default_factory=list)
    allow_unbound_trigger: bool = False

    @model_validator(mode="after")
    def _complete_unique_mapping(self) -> "VerbRolesCompatibilityPredicate":
        if not self.roles:
            raise ValueError("verb roles compatibility needs at least one role")
        slots: list[str] = []
        for role, mapped in self.roles.items():
            if not role or role.strip() != role:
                raise ValueError(
                    "verb roles compatibility role names must be non-empty and trimmed"
                )
            if not mapped:
                raise ValueError(
                    f"verb roles compatibility role {role!r} needs a slot"
                )
            if len(mapped) != len(set(mapped)):
                raise ValueError(
                    f"verb roles compatibility role {role!r} repeats a slot"
                )
            slots.extend(mapped)
        if len(slots) != len(set(slots)):
            raise ValueError("verb roles compatibility maps a slot twice")
        if len(self.frame_categories) != len(set(self.frame_categories)):
            raise ValueError(
                "verb roles compatibility repeats a frame category"
            )
        known = set(slots)
        for permission, declared in (
            ("proper-name", self.allow_proper_name),
            ("plural-class", self.allow_plural_class),
            ("plural-pronoun", self.allow_plural_pronoun),
        ):
            if len(declared) != len(set(declared)):
                raise ValueError(
                    f"verb roles compatibility repeats a {permission} slot"
                )
            unknown = set(declared) - known
            if unknown:
                raise ValueError(
                    f"verb roles compatibility {permission} permission names "
                    f"unmapped slots {sorted(unknown)!r}"
                )
        return self


class MeasureHolderCompatibilityPredicate(StrictModel):
    """Require every holder to bear the dimension named by a measure.

    The lexical relation lives in ``measure_holder_compatibility`` pack data.
    Proper names stay an explicit opt-in because open project fixtures cannot
    carry closed noun-category membership.
    """

    measure: str
    # When present, the measure/holder licence must use the noun category
    # selected by this descriptor's declared attribute compatibility.  This
    # matters for genuinely polysemous measures such as ``year``: it can name
    # either age or duration, but ``older`` and ``longer`` select different
    # routes through those memberships.
    attribute: str | None = None
    holders: list[str] = Field(min_length=1)
    allow_proper_name: bool = False
    proper_name_measure_categories: list[str] = Field(default_factory=list)
    # A broad grammar may contain both relational measures and ordinary count
    # nouns. In that case a declared source-category relationship activates
    # the boundary, while measures with no relationship remain unchanged.
    # The default stays strict for dimension rules whose entire measure domain
    # must have a holder contract.
    when_declared: bool = False

    @model_validator(mode="after")
    def _unique_holders(self) -> "MeasureHolderCompatibilityPredicate":
        if len(self.holders) != len(set(self.holders)):
            raise ValueError("measure-holder compatibility repeats a holder")
        if self.measure in self.holders:
            raise ValueError(
                "measure-holder compatibility cannot reuse the measure as a holder"
            )
        if self.attribute is not None and self.attribute in {
            self.measure,
            *self.holders,
        }:
            raise ValueError(
                "measure-holder compatibility cannot reuse its attribute slot"
            )
        if self.proper_name_measure_categories and not self.allow_proper_name:
            raise ValueError(
                "proper-name measure categories require allow_proper_name"
            )
        if len(self.proper_name_measure_categories) != len(
            set(self.proper_name_measure_categories)
        ):
            raise ValueError(
                "measure-holder compatibility repeats a proper-name measure category"
            )
        return self


class PartitiveCompatibilityPredicate(StrictModel):
    """Require a measure and its ``of`` complement to form a licensed pair."""

    measure: str
    substance: str

    @model_validator(mode="after")
    def _distinct_slots(self) -> "PartitiveCompatibilityPredicate":
        if self.measure == self.substance:
            raise ValueError(
                "partitive compatibility needs distinct measure/substance slots"
            )
        return self


class DistinctFromOwnerPredicate(StrictModel):
    """Keep an entity distinct from a possessed noun's declared owner."""

    entity: str
    possessed: str

    @model_validator(mode="after")
    def _different_slots(self) -> "DistinctFromOwnerPredicate":
        if self.entity == self.possessed:
            raise ValueError(
                "entity/possessed owner comparison needs two different slots"
            )
        return self


class SameCategoryMembershipPredicate(StrictModel):
    """Require several slots to agree on membership in one category.

    Slots need not share a lemma. Apples/oranges are both
    non-temporal and mornings/afternoons are both temporal; a mixed pair
    fails. Shared absence is category agreement, not evidence of compatible
    pronoun forms; those use positive anaphoric paradigm declarations.
    """

    slots: list[str] = Field(min_length=2)
    cat: str

    @model_validator(mode="after")
    def _unique_slots(self) -> "SameCategoryMembershipPredicate":
        if len(self.slots) != len(set(self.slots)):
            raise ValueError("category membership agreement repeats a slot")
        return self


class CategoryContainsPredicate(StrictModel):
    """Require a collection slot to name a category containing member slots."""

    collection: str
    members: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _distinct_roles(self) -> "CategoryContainsPredicate":
        if len(self.members) != len(set(self.members)):
            raise ValueError("category containment repeats a member slot")
        if self.collection in self.members:
            raise ValueError(
                "category containment cannot reuse its collection as a member"
            )
        return self


class TextPrefixSplitPredicate(StrictModel):
    """Validate the source spelling against an explicit component layout."""

    text: str
    prefix: str
    prefix_attr: Literal["lemma", "owner", "written"] = "lemma"
    layout: Literal["two-part", "capitalized-tail"] = "two-part"


class WherePredicate(StrictModel):
    """Closed set of cross-slot constraints."""

    same_lemma: list[str] | None = None
    # An elliptical continuation may inherit only the nearest preceding verb,
    # never search past an intervening predicate for a convenient antecedent.
    preceding_verb_category: dict[str, str] | None = None
    # All named single-unit slots must expose the same written surface,
    # case-insensitively. This deliberately differs from ``same_lemma``:
    # pronoun lemmas follow resolved referents, while repeated possessive/
    # object forms such as "her ... her" can themselves be the grammatical
    # evidence that a coordinated construction shares one participant.
    same_surface: list[str] | None = None
    text_prefix_split: TextPrefixSplitPredicate | None = None
    # All named slots must carry the same grammatical number. Count-valued
    # units derive singular only from value 1 and plural otherwise; lexical
    # units use their pack-declared `number`. This is grammar structure, not a
    # word list, and lets a rule declare agreement without teaching the kernel
    # which words are singular or plural.
    same_number: list[str] | None = None
    # All named slots must either belong to `cat` or all remain outside it.
    # Unlike `same_lemma`, this permits distinct members of the same semantic
    # class and also distinct nouns that share the absence of that class.
    same_category_membership: SameCategoryMembershipPredicate | None = None
    # Reject an EXPLICIT grammatical-number conflict while allowing a
    # number-neutral form (notably English past tense) to remain compatible.
    # This differs deliberately from `same_number`, which requires every slot
    # to carry singular/plural evidence.
    number_compatible: list[str] | None = None
    # Conditional phrase structure. An optional prefix may narrow the type of
    # the following head: an appositive "his friend Sam" requires a proper
    # name after the bound role, while the prefix-free sibling may still admit
    # a definite common-noun standard.
    bound_requires_type: BoundRequiresTypePredicate | None = None
    # Category-qualified sibling of ``bound_requires_type``.  This is useful
    # when an optional grammatical continuation changes the lexical class of
    # an earlier slot, e.g. an optional destination preposition requires a
    # motion verb while the direct-object form remains open.
    bound_requires_category: BoundRequiresCategoryPredicate | None = None
    # Negative conditional sibling: when the optional continuation matched,
    # the named slot must remain outside the declared category.
    bound_rejects_category: BoundRejectsCategoryPredicate | None = None
    # Inverse conditional: a slot in the named category requires an optional
    # grammatical continuation to have matched. This keeps governed verbs out
    # of a direct-object surface without making that surface a second rule.
    category_requires_bound: CategoryRequiresBoundPredicate | None = None
    # Morphology-qualified sibling. A modal auxiliary, for example, requires
    # the following verb to be bare while the auxiliary-free clause retains
    # its ordinary finite surface.
    bound_requires_form: BoundRequiresFormPredicate | None = None
    owner_matches: OwnerMatchesPredicate | None = None
    # Compare only polarity declarations inside each slot's paired category
    # subtree. Unscoped meanings remain neutral: an explicitly directional
    # change verb must agree with its direction word, while a general event
    # verb is not reinterpreted through an unrelated acquire/lose category.
    polarity_compatible: PolarityCompatibilityPredicate | None = None
    # A proportional relation emits ``1 + fraction * sign(direction)``.
    # Declared positive directions remain unbounded; declared negative
    # directions require fraction <= 1 so the result cannot become negative.
    proportional_delta_compatible: (
        ProportionalDeltaCompatibilityPredicate | None
    ) = None
    # The named optional slots must either all be present or all be absent.
    # This makes discontinuous paired structure declarative: a repeated
    # preposition can surround an intervening relative clause without either
    # half being independently optional.
    same_presence: list[str] | None = None
    # At most one named optional slot may bind. This distinguishes alternate
    # realizations such as "their average age" and "average age of the 5"
    # without splitting an otherwise identical ask into sibling rules.
    mutually_exclusive: list[str] | None = None
    # A verb in ``verb_cat`` requires each named semantic role to be a proper
    # name or a common noun in ``role_cat``. Verbs outside the triggering
    # category remain unchanged. This keeps agency knowledge in pack data.
    verb_role_compatible: VerbRoleCompatibilityPredicate | None = None
    # Structural sibling backed by category-owned selectional-role contracts.
    # Unlike ``verb_role_compatible``, the rule contains no lexical category
    # pair: it only maps surface slots to semantic roles.
    verb_roles_compatible: VerbRolesCompatibilityPredicate | None = None
    # A counted dimension only relates entities licensed to bear that measure.
    # The mapping remains pack-owned; this predicate merely relates slots.
    measure_holder_compatible: (
        MeasureHolderCompatibilityPredicate | None
    ) = None
    # A MEASURE-of-SUBSTANCE noun phrase must be licensed by one pair in the
    # pack-owned partitive compatibility table.
    partitive_compatible: PartitiveCompatibilityPredicate | None = None
    # Opt-in equality for whole rendered slot values, including span slots.
    # `same_lemma` deliberately skips spans; constructions with repeated
    # multi-unit phrases need exact phrase identity, not head-lemma identity.
    same_phrase: list[str] | None = None
    distinct: list[str] | None = None
    # Opt-in semantic complement to lexical ``distinct``. The named entity or
    # noun roles must not be an unqualified category/member pair in either
    # direction (``animal`` versus ``hamster``). Sibling members remain
    # compatible, and the matcher preserves independently distinguished names,
    # labels, and owners. Category structure stays wholly pack-declared.
    category_nonoverlap: list[str] | None = Field(
        default=None, min_length=2
    )
    # Directional category/member containment. The collection role must name
    # a noun category and every member role must belong to it. This licenses
    # "animals are dogs" partitions while refusing both unrelated pairs and
    # the reversed, uninformative "dogs are animals" partition shape.
    category_contains: CategoryContainsPredicate | None = None
    # Every named slot must carry a non-empty possessive owner, and those
    # owners must be distinct. The noun lemmas may intentionally be identical
    # ("Aven's age ... Bira's age"); ordinary `distinct` compares lemmas and
    # therefore cannot express this relation.
    distinct_owner: list[str] | None = None
    # Compare one ordinary entity slot with the independently represented
    # owner of a possessed noun slot. Ordinary ``distinct`` compares slot
    # lemmas, so "Fia ... Fia's apples" otherwise compares `fia` with `apple`
    # and misses the self-reference.
    distinct_from_owner: DistinctFromOwnerPredicate | None = None
    # The descriptor slot must be licensed for the noun slot by at least one
    # pack-declared descriptor-category -> noun-category compatibility pair.
    # Descriptors may be adjectives, comparatives, prepositions, or nominal modifiers.
    # Both words may belong to multiple categories; this is existential over
    # the cross-product, never a single hardwired category.
    attribute_compatible: AttributeCompatibilityPredicate | None = None
    # When the modifier is present and belongs to a preposition category with
    # a declared host boundary, its head noun must belong to one of the
    # corresponding host categories. Undeclared prepositions remain open.
    modifier_host_compatible: ModifierHostCompatibilityPredicate | None = None
    # When the adverb is present, its pack-declared category must license the
    # bound verb category. An omitted optional adverb is neutral.
    adverb_verb_compatible: AdverbVerbCompatibilityPredicate | None = None
    # mining candidate qualified-measure-keys: the SAME self-reference
    # guard as `distinct` (lemma, label), plus each slot's own `qualifier`
    # feature (condense.py merge-attribute/merge-compound) — "12 more
    # GREEN apples than RED apples" bare-folds item/std to lemma 'apple'
    # but carries two DIFFERENT qualifiers, so it is NOT the self-
    # referential "compares a measure to itself" shape `distinct` exists to
    # block; two bare (qualifier-less) units still collide exactly as
    # `distinct` always has. A SEPARATE predicate name, not a widening of
    # `distinct` itself: `distinct: [who, std]` (entity-holder identity)
    # must keep its exact pre-existing behavior everywhere it is already
    # used — this is opt-in per rule, applied only where a measure-noun
    # slot pair (`item`/`std`) needs the qualifier-aware comparison.
    distinct_measure: list[str] | None = None
    name_count: dict[str, int] | None = None  # {"exactly": 2}
    absent: dict[str, str] | None = None  # {"cat": name} — no such word in sentence
    # {"slot": name, "cat": name} — that SLOT's bound unit must NOT be in
    # the category. A SEPARATE predicate rather than a widening of `absent`
    # (which scans the WHOLE sentence): a relation's standard must not be a
    # TIME PERIOD, while the sentence may legitimately contain time words
    # elsewhere ("Last month, he made three fewer tables THAN THIS MONTH" —
    # 'month' is both the adverbial and the illegal standard). Same opt-in
    # discipline `distinct_measure` records: no existing rule's behaviour
    # changes, only rules that name this predicate get the check.
    slot_not_category: dict[str, str] | None = None
    # mining candidate elided-comparative-standards: these OPTIONAL slots
    # must NOT have matched anything — the general, reusable mirror of a
    # positional negative lookahead this engine otherwise has no way to
    # express (no rule can require "nothing of shape X follows"). A rule
    # that WANTS to decline whenever its own trailing optional clause
    # happens to bind (rather than silently truncating a longer, still-
    # grammatical continuation it isn't equipped to interpret) matches
    # that continuation into a slot and lists it here: if a sibling rule
    # was meant to own that fuller span but itself declines for an
    # unrelated reason (a different `where` guard elsewhere rejects it),
    # this rule still won't step in and misread the truncated prefix as
    # the whole story.
    unbound: list[str] | None = None

    @model_validator(mode="after")
    def _one(self) -> "WherePredicate":
        if (
            self.category_nonoverlap is not None
            and len(self.category_nonoverlap)
            != len(set(self.category_nonoverlap))
        ):
            raise ValueError("category nonoverlap repeats a slot")
        set_ = [
            v for v in (
                self.same_lemma, self.same_surface, self.text_prefix_split, self.same_number,
                self.preceding_verb_category,
                self.same_category_membership, self.number_compatible,
                self.bound_requires_type, self.bound_requires_category,
                self.bound_rejects_category,
                self.category_requires_bound,
                self.bound_requires_form, self.polarity_compatible,
                self.owner_matches,
                self.proportional_delta_compatible,
                self.same_presence,
                self.mutually_exclusive,
                self.verb_role_compatible,
                self.verb_roles_compatible,
                self.measure_holder_compatible,
                self.partitive_compatible,
                self.same_phrase,
                self.distinct,
                self.category_nonoverlap,
                self.category_contains,
                self.distinct_owner, self.distinct_from_owner,
                self.attribute_compatible,
                self.modifier_host_compatible,
                self.adverb_verb_compatible,
                self.distinct_measure,
                self.name_count, self.absent, self.unbound,
                self.slot_not_category,
            )
            if v is not None
        ]
        if len(set_) != 1:
            raise ValueError("exactly one predicate per where item")
        return self


class FactEmit(StrictModel):
    fact: Literal[
        "batch_evidence", "activity_account_evidence", "region_evidence", "specification_evidence", "population_evidence", "mixture_evidence", "proportional_base_evidence",
        "account_entry",
        "text_value", "text_prefix_split",
        "commercial_term",
        "allocation_ratio", "allocation_group", "indexed_path_evidence", "measured_component",
        "inventory_scope", "inventory_withdrawal",
        "journey_leg", "journey_schedule", "journey_extra", "journey_pace",
        "accumulation_window", "earning_rate", "service_scope", "purchase_endpoint",
        "event_cadence", "sequence_total", "sequence_step",
        "rate_threshold", "rate_premium", "repeated_activity_duration",
        "resource_allocation", "resource_balance", "expenditure", "activity_duration", "bounded_activity_inquiry", "age_at_year",
        "task_completion_duration",
        "rate_scope", "quantity", "relation", "contribution",
        "membership", "subset", "predication", "collection_context", "collection_attribute", "quantity_event_context",
        "before", "fraction_quantity", "rest_quantity", "partition_quantity",
        "partition_aggregate_share",
        "sequential_partition", "sequential_partition_prefix",
        "sequential_partition_remainder", "sequential_partition_initial_share",
        "sequential_partition_remaining_share", "ratio_quantity", "goal",
        "group_total", "rate", "price", "discount",
        "percent_change", "atom", "quantified", "quantified_quantity",
        "quantified_adjustment",
        "class_refinement", "conditional",
        "disjunction", "equivalence", "quantified_disjunction", "existential",
        "verbal_relation", "location_event", "location_constraint",
        "location_transition_absence",
        "spatial_placement", "measured_content_change", "container_content",
        "container_capacity_inquiry", "container_capacity_observation",
        "totality_transfer", "totality_event",
        "semantic_graph_node", "semantic_graph_edge",
        "alias", "enumerated_disjunction",
        "disjunctive_conditional", "ground_conditional",
        "positive_ground_conditional",
    ]
    # remaining fields are fact-kind specific; templated strings "{slot}" or
    # expressions evaluated by the safe evaluator.
    fields: dict[str, str | float | bool] = Field(default_factory=dict)
    # Stage 9g: per-item emission over an ENUMERATION span. Names a span
    # slot; the emit fires once per comma/conjunction-separated segment of
    # that span, with the segment bound as the reserved `{item}` slot
    # ("There are six types of wild turkeys: A, B, …, and F" → one fact per
    # listed type). Declared here so it never falls into `fields` via the
    # extra-collector below.
    # An enumeration_counted span binds each counted member as a scalar Unit,
    # retaining its numeric value, modifiers and reference identity.
    each: str | None = None
    # Stage 9h: whole-list emission over an ENUMERATION span. Names a span
    # slot; the emit fires ONCE with every comma/conjunction-separated
    # segment of that span rendered as an option key (fact kind
    # `enumerated_disjunction` only). Requires a `count` field template —
    # the fact is minted ONLY when the rendered stated count equals the
    # number of segments (exhaustiveness is what the count licenses;
    # mismatch emits nothing, fail closed).
    options_from: str | None = None
    # Optional evidence-time metadata. The value may be a literal
    # (``present``/``past``/``future``) or a normal slot template such as
    # ``{verb.surface}``; it belongs to Provenance rather than the emitted
    # Fact's semantic fields and therefore never changes fact identity.
    temporal_perspective: str | None = None
    # Optional evidence-shape metadata for a stated per-member quantity or
    # temporal rate. This distinguishes a class quota from a specific
    # instance without inventing additional holding facts.
    distributive: bool = False
    # Optional evidence-shape marker for a rule-emitted count of packages.
    # It is provenance rather than quantity identity, like `distributive`.
    container_count: bool = False

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def _collect_extra(self) -> "FactEmit":
        if self.distributive and self.fact not in {"quantity", "rate"}:
            raise ValueError("distributive provenance is valid only for quantity or rate facts")
        if self.container_count and self.fact != "quantity":
            raise ValueError("container_count provenance is valid only for quantity facts")
        if self.model_extra:
            self.fields = {**self.fields, **self.model_extra}
        return self


class GenerationContextSentence(StrictModel):
    """One declarative support sentence surrounding a generated target."""

    sentence: list[MatchToken] = Field(min_length=1)
    where: list[WherePredicate] = Field(default_factory=list)


class GenerationContextDef(StrictModel):
    """Minimum adjacent discourse required to review a contextual rule."""

    before: list[GenerationContextSentence] = Field(default_factory=list)
    after: list[GenerationContextSentence] = Field(default_factory=list)
    required_fact_counts: dict[str, int] = Field(default_factory=dict)
    # Context fillers may need the same lexical identity as a target slot while
    # realizing a different surface shape.  For example, target `bags` links
    # to contextual counted `3 large bags`; a surface lock would be impossible,
    # but an identity lock preserves the shared package head generically.
    target_identity_links: dict[str, str] = Field(default_factory=dict)
    target_commas_after: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _has_context(self) -> "GenerationContextDef":
        if not self.before and not self.after:
            raise ValueError("generation context needs a before or after sentence")
        if any(count < 1 for count in self.required_fact_counts.values()):
            raise ValueError("required contextual fact counts must be positive")
        if any(
            not context_slot or not target_slot
            for context_slot, target_slot in self.target_identity_links.items()
        ):
            raise ValueError("context identity links need non-empty slot names")
        return self


def _declared_match_tokens(match) -> dict[str, MatchToken]:
    declared = {}
    pending = [token for sequence in match.values() for token in sequence]
    while pending:
        token = pending.pop()
        if isinstance(token, list):
            pending.extend(token)
            continue
        pending.extend(token.opt or ())
        if token.slot is not None:
            declared[token.slot] = token
    return declared


def _validate_sense_selection(selected, declared) -> None:
    if len(selected) != len(set(selected)):
        raise ValueError('sense selection slots must be unique')
    for slot in selected:
        token = declared.get(slot)
        if token is None or not token.cat or token.span:
            raise ValueError('sense selection requires a named, category-gated single-unit slot')


class PatternRule(StrictModel):
    id: str
    phase: Literal["read", "post-saturation"] = "read"
    # Most read rules describe prose that the Designer may present as a
    # candidate premise. A contextual rule is also reviewable, but only with
    # generator-supplied adjacent discourse; a reader-only rule preserves a
    # narrow corpus compatibility surface that human review should not
    # reproduce; a safety consumer recognizes bad or incomplete prose only to
    # stop fallback folds from asserting a fact. Keeping those distinctions in
    # rule data prevents the generator from presenting invalid isolated prose.
    generation: Literal[
        "premise", "contextual", "reader-only", "safety"
    ] = "premise"
    generation_context: GenerationContextDef | None = None
    description: str | None = None
    # Opt in to promotion from an immediately pre-question detached `If`
    # sentence. Adjacency supplies scope, while this declaration proves that
    # the stripped clause has assumption semantics. Ordinary conditional
    # rules remain asserted premises and are never stolen by the splitter.
    question_assumption: bool = False
    # Opt-in local-chain matching. Default rules advance past a whole match;
    # an overlapping rule advances one unit past its match start so adjacent
    # windows such as N-P-N-P-N can emit both N-P-N links.
    overlapping: bool = False
    match: dict[Literal["sentence", "sentences", "question"], list[MatchToken] | list[list[MatchToken]]]
    where: list[WherePredicate] = Field(default_factory=list)
    # Constraints that shape authored generation without narrowing historical
    # reader acceptance. This is appropriate for surface-quality contracts
    # such as agreement when a human has validated the interpretation of a
    # marginal form. The generator applies the same declarative predicate
    # vocabulary as `where`; the runtime matcher deliberately does not.
    generation_where: list[WherePredicate] = Field(default_factory=list)
    consumes: list[str] = Field(default_factory=list)  # value-accounting slots
    # A pattern may structurally discharge an obligation that cannot bind to
    # one ordinary Unit. Coordinated subjects are the first case: the verb's
    # subject is the whole coordination, so binding either conjunct would be
    # false. The target becomes the model.PATTERN sentinel; only explicitly
    # named slot/need pairs are affected.
    satisfies: dict[str, list[str]] = Field(default_factory=dict)
    # Complete constructions may explicitly bind a referring slot to another
    # slot. Unlike `satisfies`, this retains a real Unit target. All forms
    # sharing a target need a declared compatible anaphoric paradigm; a
    # repeated explicit name must denote that exact target.
    # Complete-construction role links retain real Unit targets. Unlike
    # references these bind a grammatical need (e.g. each.collection), not
    # an anaphoric identity; unlike satisfies they never use a sentinel.
    bindings: dict[str, dict[str, str]] = Field(default_factory=dict)
    references: dict[str, str] = Field(default_factory=dict)
    disambiguates: list[str] = Field(default_factory=list)
    independent_clause: bool = False
    emits: list[FactEmit] = Field(default_factory=list)
    overrides: dict[str, str] | None = None  # {"rule": id, "reason": ...}

    @model_validator(mode="after")
    def _satisfaction_contract_is_explicit(self) -> "PatternRule":
        if self.independent_clause and (self.phase != 'read' or 'sentence' not in self.match or not self.emits):
            raise ValueError('independent_clause requires a fact-emitting read-phase sentence rule')
        _validate_sense_selection(self.disambiguates, _declared_match_tokens(self.match))
        if self.disambiguates and (self.phase != 'read' or 'sentence' not in self.match):
            raise ValueError('sense selection requires a read-phase sentence rule')
        if self.references and (self.phase != "read" or "sentence" not in self.match):
            raise ValueError("reference bindings require a read-phase sentence rule")
        for source, target in self.references.items():
            if not source or not target or source == target or target in self.references:
                raise ValueError("reference bindings need distinct, direct target slots")
            if "refers" in self.satisfies.get(source, []):
                raise ValueError("reference binding cannot also satisfy refers with a sentinel")
        if self.generation == "contextual" and self.generation_context is None:
            raise ValueError("a contextual rule needs `generation_context`")
        if self.generation != "contextual" and self.generation_context is not None:
            raise ValueError(
                "`generation_context` requires `generation: contextual`"
            )
        if self.question_assumption and (
            self.phase != "read" or "sentence" not in self.match
        ):
            raise ValueError(
                f"rule {self.id!r}: question_assumption requires a read-phase "
                "sentence rule"
            )
        for slot, needs in self.satisfies.items():
            if not slot or not needs:
                raise ValueError(
                    f"rule {self.id!r}: pattern satisfaction needs a slot "
                    "and at least one obligation"
                )
            if len(needs) != len(set(needs)) or any(not need for need in needs):
                raise ValueError(
                    f"rule {self.id!r}: pattern satisfaction obligations "
                    "must be non-empty and unique"
                )
        return self


class AskInterpretation(StrictModel):
    """One explicit semantic reading of an ambiguous ask surface."""

    id: str
    label: str
    description: str = ""
    kind: str
    # Most query fields are one templated scalar. Exact coordinated-holder
    # asks preserve their explicitly named members as a templated list so a
    # consumer never has to recover scope by enumerating every fact holder.
    resolves: dict[str, str | list[str]]


class AskEvidenceRule(StrictModel):
    """One ordinary premise rule required by an answerable ask scenario.

    ``bindings`` maps a premise-rule slot to a normalized query field. The
    generator still realizes the premise through that rule and the ordinary
    document solver remains the only proof that the resulting set suffices.
    """

    rule: str
    bindings: dict[str, str] = Field(default_factory=dict)


class AskValidatedSlotBinding(StrictModel):
    """Map one generated ask slot to typed fields on reviewed facts.

    A counted slot needs both its lexical identity and numeric value. Keeping
    those field names in pack data lets, for example, a duration span align
    with a reviewed rate denominator without teaching the authoring runtime a
    specific consumer or sentence shape.
    """

    identity_field: str = Field(min_length=1)
    value_field: str | None = Field(default=None, min_length=1)


class PropertyParameterSlot(StrictModel):
    slot: str
    component: Literal["identity", "qualifier"] = "identity"


class PropertyGenerationDef(StrictModel):
    subject: str
    property: str
    parameters: list[PropertyParameterSlot]


class AskGenerationDef(StrictModel):
    """Declarative constraints that apply only to ask realization.

    Some ask grammars are valid only inside a larger clause, while others
    draw slot values from compiled project data rather than open lexical
    fixtures. These fields keep both facts in the owning pack instead of
    teaching the generator individual ask ids or vocabulary.
    """

    context_required: bool = False
    # A context-required ask must declare what kind of ordinary document
    # context makes it valid. ``evidence`` keeps the question intact and
    # searches generated premise evidence; ``conditional`` embeds one
    # generated premise as an ``If ..., <question>`` frame so uninverted
    # indirect-question order is never offered as a standalone sentence.
    context_strategy: Literal["evidence", "conditional"] | None = None
    evidence_rules: list[AskEvidenceRule] = Field(default_factory=list)
    slot_sources: dict[
        str, Literal["reference_group", "reference_year"]
    ] = Field(default_factory=dict)
    slot_categories: dict[str, str | list[str]] = Field(default_factory=dict)
    validated_slot_bindings: dict[str, AskValidatedSlotBinding] = Field(
        default_factory=dict
    )
    # Preserve a surface explicitly bound by the reviewed premise rule when
    # the generated ask has a corresponding slot.  This is intentionally
    # separate from ``validated_slot_bindings``: those read normalized FACT
    # fields (for example Rate.per/denominator), while these read the pinned
    # rule derivation (for example the modal auxiliary that licensed that
    # Rate).  If reviewed evidence binds the source slot but its surface is
    # incompatible with the ask slot, that premise/ask pairing is rejected;
    # silently choosing another surface would change tense or modality.
    validated_source_bindings: dict[str, str] = Field(default_factory=dict)
    # Slots in rejection-only optional branches remain part of the reader
    # grammar so a malformed continuation cannot be ignored as an accepted
    # prefix. Ask generation must never realize those capture-only branches.
    omit_slots: list[str] = Field(default_factory=list)
    requires_committed_answer: bool = False
    property_bindings: PropertyGenerationDef | None = None

    @model_validator(mode="after")
    def _context_strategy_is_explicit(self) -> "AskGenerationDef":
        if self.context_required != (self.context_strategy is not None):
            raise ValueError(
                "context_required and context_strategy must be declared together"
            )
        if self.evidence_rules and self.context_strategy not in {
            "evidence",
            "conditional",
        }:
            raise ValueError(
                "evidence_rules require a generated context strategy"
            )
        if self.context_strategy is not None and not self.evidence_rules:
            raise ValueError(
                "a generated context strategy requires at least one evidence rule"
            )
        return self


class AskRule(StrictModel):
    id: str
    match: dict[Literal["question"], list[MatchToken]]
    where: list[WherePredicate] = Field(default_factory=list)
    # Ask-only grammatical material may discharge an obligation without a
    # discourse antecedent.  The first use is deictic speaker ``we`` inside
    # "can we safely say ...": it denotes the current reasoners rather than a
    # previously mentioned plural group.  This mirrors PatternRule.satisfies
    # and remains explicit per slot/need pair.
    satisfies: dict[str, list[str]] = Field(default_factory=dict)
    # A complete selected construction may commit explicitly named category
    # slots to their declared root sense. Unmatched prose stays ambiguous.
    disambiguates: list[str] = Field(default_factory=list)
    resolves: dict[str, str | list[str]] = Field(default_factory=dict)
    clarification: str | None = None
    interpretations: list[AskInterpretation] = Field(default_factory=list)
    generation: AskGenerationDef = Field(default_factory=AskGenerationDef)

    @model_validator(mode="after")
    def _anchor_is_first(self) -> "AskRule":
        """`at_start` on any token but the first can never match.

        Token N>0 anchored to the start would need tokens 0..N-1 to match BEFORE
        the start, so the ask silently matches nothing — a dead rule that a dev
        gate reports as a clean 0 SOLVED. Fail at load instead: an anchor that
        cannot fire is an authoring mistake, and prose does not enforce.
        """
        for seq in self.match.values():
            for i, tok in enumerate(seq):
                if tok.at_start and i != 0:
                    raise ValueError(
                        f"ask {self.id!r}: `at_start` is only meaningful on the "
                        f"FIRST token of a match sequence (found at index {i})"
                    )
        has_resolution = bool(self.resolves)
        has_interpretations = bool(self.interpretations)
        if has_resolution == has_interpretations:
            raise ValueError(
                f"ask {self.id!r}: define exactly one of `resolves` or "
                "`interpretations`"
            )
        if self.interpretations:
            if not self.clarification:
                raise ValueError(
                    f"ask {self.id!r}: ambiguous asks require `clarification`"
                )
            ids = [choice.id for choice in self.interpretations]
            if len(ids) != len(set(ids)):
                raise ValueError(
                    f"ask {self.id!r}: interpretation ids must be unique"
                )
        declared_tokens = _declared_match_tokens(self.match)
        declared_slots = set(declared_tokens)
        _validate_sense_selection(self.disambiguates, declared_tokens)
        for slot, needs in self.satisfies.items():
            if slot not in declared_slots:
                raise ValueError(
                    f"ask {self.id!r}: pattern satisfaction names unknown "
                    f"slot {slot!r}"
                )
            if not needs or len(needs) != len(set(needs)) or any(
                not need for need in needs
            ):
                raise ValueError(
                    f"ask {self.id!r}: pattern satisfaction obligations "
                    "must be non-empty and unique"
                )
        if self.generation.property_bindings is not None:
            binding = self.generation.property_bindings
            names = [binding.subject, binding.property, *(p.slot for p in binding.parameters)]
            if len(names) != len(set(names)) or set(names) - declared_slots:
                raise ValueError("property generation bindings need distinct declared slots")
        unknown_generation_slots = (
            set(self.generation.slot_sources)
            | set(self.generation.slot_categories)
            | set(self.generation.validated_slot_bindings)
            | set(self.generation.validated_source_bindings)
            | set(self.generation.omit_slots)
        ) - declared_slots
        if unknown_generation_slots:
            raise ValueError(
                f"ask {self.id!r}: generation constraints name unknown slots: "
                + ", ".join(sorted(unknown_generation_slots))
            )
        if len(self.generation.omit_slots) != len(
            set(self.generation.omit_slots)
        ):
            raise ValueError(
                f"ask {self.id!r}: generation omit_slots repeats a slot"
            )
        locked_generation_slots = (
            set(self.generation.slot_sources)
            | set(self.generation.slot_categories)
            | set(self.generation.validated_slot_bindings)
            | set(self.generation.validated_source_bindings)
        ) & set(self.generation.omit_slots)
        if locked_generation_slots:
            raise ValueError(
                f"ask {self.id!r}: omitted generation slots also have "
                "generation sources/categories/validated bindings: "
                + ", ".join(sorted(locked_generation_slots))
            )
        if any(
            not source_slot
            for source_slot in self.generation.validated_source_bindings.values()
        ):
            raise ValueError(
                f"ask {self.id!r}: validated source bindings need a "
                "non-empty premise slot"
            )
        for slot, categories in self.generation.slot_categories.items():
            declared = categories if isinstance(categories, list) else [categories]
            if not declared or any(not category for category in declared):
                raise ValueError(
                    f"ask {self.id!r}: generation slot {slot!r} needs at "
                    "least one non-empty category"
                )
            if len(declared) != len(set(declared)):
                raise ValueError(
                    f"ask {self.id!r}: generation slot {slot!r} repeats a category"
                )
        return self


class RuleTemplate(StrictModel):
    """Local, data-only defaults and a premise or ask body with parameters."""

    parameters: dict[str, object] = Field(default_factory=dict)
    rule: dict[str, object]


class TemplateVariant(StrictModel):
    """A stable public identity instantiated from one local template."""

    id: str
    template: str
    arguments: dict[str, object] = Field(default_factory=dict)


class RuleVariant(TemplateVariant):
    """Premise variants may also override their author-facing description."""

    description: str | None = None


class RulesDoc(StrictModel):
    format: Literal["rulekit/rules@1"]
    rules: list[PatternRule] = Field(default_factory=list)
    asks: list[AskRule] = Field(default_factory=list)
    templates: dict[str, RuleTemplate] = Field(default_factory=dict)
    variants: list[RuleVariant] = Field(default_factory=list)
    ask_variants: list[TemplateVariant] = Field(default_factory=list)
    _expanded_variants: list[PatternRule] = PrivateAttr(default_factory=list)
    _expanded_ask_variants: list[AskRule] = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def _expand_variants(self):
        from .rule_templates import expand_rule_template

        ids: set[str] = set()
        for rule in [*self.rules, *self.asks]:
            if rule.id in ids:
                raise ValueError(f"rule id {rule.id!r} defined twice")
            ids.add(rule.id)

        def expand(variants, model):
            expanded = []
            for variant in variants:
                if variant.template not in self.templates:
                    raise ValueError(f"rule {variant.id!r}: unknown template {variant.template!r}")
                if variant.id in ids:
                    raise ValueError(f"rule id {variant.id!r} defined twice")
                try:
                    raw, _ = expand_rule_template(self.templates[variant.template], variant)
                    expanded.append(model.model_validate(raw))
                except ValueError as error:
                    raise ValueError(
                        f"rule {variant.id!r} from template {variant.template!r}: {error}"
                    ) from error
                ids.add(variant.id)
            return expanded

        self._expanded_variants = expand(self.variants, PatternRule)
        self._expanded_ask_variants = expand(self.ask_variants, AskRule)
        return self

    @property
    def compiled_rules(self) -> list[PatternRule]:
        return [*self.rules, *self._expanded_variants]

    @property
    def compiled_asks(self) -> list[AskRule]:
        return [*self.asks, *self._expanded_ask_variants]


# ---------------------------------------------------------------------------
# synth rules
# ---------------------------------------------------------------------------


class FactShape(StrictModel):
    fact: str
    model_config = ConfigDict(extra="allow")  # field -> variable or literal

    def bindings(self) -> dict[str, object]:
        return dict(self.model_extra or {})


class SynthRule(StrictModel):
    id: str
    when: list[FactShape]
    unless: list[FactShape] = Field(default_factory=list)
    emit: list[FactShape]


class SynthDoc(StrictModel):
    format: Literal["rulekit/synth@1"]
    rules: list[SynthRule]


# ---------------------------------------------------------------------------
# question requirements
# ---------------------------------------------------------------------------


class RequirementShape(StrictModel):
    id: str
    match: dict[str, list[MatchToken]]
    needs: list[dict[str, str]]
    supplied_when: dict[str, dict[str, str]] | None = None


class RequirementsDoc(StrictModel):
    format: Literal["rulekit/requirements@1"]
    shapes: list[RequirementShape]


# ---------------------------------------------------------------------------
# guards / pack / project
# ---------------------------------------------------------------------------


class ConversionDef(StrictModel):
    from_: str = Field(alias="from")
    to: str
    factor: float
    # A cross-dimension factor may be valid only for one substance. Water's
    # mass/volume relation, for example, must never make kilograms globally
    # interchangeable with litres. The registry stores these rows separately
    # and only a consumer carrying the matching substance may traverse them.
    substance: str | None = None
    # Some conventional period factors are valid for projecting a cadence but
    # not for exact elapsed-time comparison (a year is treated as 52 weeks in
    # elementary word problems, while calendar duration is not exactly 364
    # days). Scoped pairs keep that assumption out of general unit folding.
    scope: Literal["general", "cadence"] = "general"

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ConversionsDoc(StrictModel):
    format: Literal["rulekit/conversions@1"]
    conversions: list[ConversionDef]


class AffineScaleDef(StrictModel):
    # to_value = (from_value + offset) * factor
    from_: str = Field(alias="from")
    to: str
    offset: float
    factor: float

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AffineConversionsDoc(StrictModel):
    """Conversions between scales with a ZERO POINT of their own.

    `rulekit/conversions@1` holds a FACTOR only, which is right for units that
    share an origin (a kilometre is a thousand metres from the same zero) and
    wrong for temperature: Celsius and Fahrenheit disagree about where zero is,
    so no factor can relate them. The form here is affine:

        to_value = (from_value + offset) * factor

    A SEPARATE table, deliberately, for the same reason `rulekit/calendar@1` is
    separate: `conversions@1` is read PAIRWISE by the word-problem
    convertible-unit fold in every arithmetic corpus, and teaching that fold
    about offsets would change unit folding everywhere to serve two questions.
    Nothing but the `affine-convert` consumer reads this.
    """

    format: Literal["rulekit/affine-conversions@1"]
    scales: list[AffineScaleDef]


class ContractionsDoc(StrictModel):
    """Clitic -> the word it stands for, applied at tokenization.

    A word-specific fact, so it is pack data (constitution rule 1) rather than
    the dict it used to be in `kernel/tokenize.py`. The morphology helpers next
    to it there (`_naive_singular`, `_ORDINAL`) derive a form from a SHAPE and
    are legitimately structural; this derives one WORD from another, and only a
    table can say which.
    """

    format: Literal["rulekit/contractions@1"]
    expansions: dict[str, str]

    @model_validator(mode="after")
    def _clitics_are_suffixes(self) -> "ContractionsDoc":
        for clitic in self.expansions:
            if not clitic:
                raise ValueError("a contraction clitic must not be empty")
            if clitic != clitic.lower():
                # matching is done on a lower-cased surface, so an upper-case
                # key would sit in the table matching nothing
                raise ValueError(f"contraction clitic {clitic!r} must be lower-case")
        return self


class ElementsDoc(StrictModel):
    """Standard atomic weights, element symbol -> g/mol.

    An atomic mass keyed on a SYMBOL is a word-specific fact, so it is pack
    data and no element is ever named in a consumer.

    The table doubles as the VALIDATOR for the formula reader: a token is read
    as a chemical formula only when EVERY symbol in it is a key here. Without
    that, an acronym-shaped word would parse as a compound — 'FBI' is F+B+I and
    all three are real symbols, which is exactly why the reader ALSO requires a
    digit and why the formula slot only appears in a chemistry ask.
    """

    format: Literal["rulekit/elements@1"]
    masses: dict[str, float]

    @model_validator(mode="after")
    def _symbols_are_well_formed(self) -> "ElementsDoc":
        # A symbol is one capital plus an optional lowercase — the shape the
        # tokenizer and the reader both assume. A malformed key would sit in
        # the table matching nothing, which is the dead-rule failure mode this
        # repo fails loudly on rather than tolerating.
        import re
        for sym in self.masses:
            if not re.fullmatch(r"[A-Z][a-z]?", sym):
                raise ValueError(
                    f"element symbol {sym!r} must be one capital plus an "
                    "optional lowercase letter"
                )
        return self


class CalendarDoc(StrictModel):
    """How many DAYS make one unit of each calendar span.

    A divisor keyed on a UNIT WORD is a word-specific fact, so it lives in a
    pack rather than in the `calendar` consumer (constitution rule 1).

    Deliberately NOT `rulekit/conversions@1`, though the shape is similar: that
    table is read PAIRWISE by the word-problem convertible-unit fold, so a
    'month -> day' row there would silently rewrite "$5 per month" in every
    arithmetic corpus. A separate table keeps the blast radius at this one
    consumer. 'month' and 'year' are averages (365.25/12 and the Julian year) --
    a calendar month has no fixed length, and a whole-unit span is what this
    family asks for.
    """

    format: Literal["rulekit/calendar@1"]
    span_units: dict[str, float]
    # month NAME (and abbreviation) -> its number. Word-specific facts,
    # so they live here and not in the consumer -- the same reason as
    # the span divisors above. English-only by construction: a pack for
    # another language ships its own table and the consumer is unchanged.
    months: dict[str, int] = Field(default_factory=dict)


class QuantityFormulaDef(StrictModel):
    # a named physical quantity -> an expression over DIMENSION names, e.g.
    # quantity=speed expr="distance / time". Sibling of FormulaDef below: that
    # one keys on (shape, quantity) because a geometry formula needs the shape to
    # disambiguate; a physical quantity names its formula on its own.
    quantity: str
    expr: str
    # Where unit-bearing operands may be read. Question-only is the safe,
    # backward-compatible default; document scope is an explicit trade in
    # which the physics consumer owns every accounted premise value too.
    scope: Literal["question", "document"] = "question"


class FormulasDoc(StrictModel):
    """A quantity->formula table plus the unit->dimension map that binds it.

    The dimensions map is what makes operand binding ORDER-INDEPENDENT, and that
    is the whole point of it. The alternative — filling the formula's parameters
    from the question's numbers positionally — reads difg's phrasing correctly
    and is WRONG on English: "an object that took 5 seconds to travel 100 meters"
    would answer 0.05 m/s with total confidence. Binding each number by the
    DIMENSION of its own unit cannot be fooled by word order.

    ONE canonical unit per dimension, on purpose. Listing both 'kilogram' and
    'gram' under `mass` would silently scale-mix: "the weight of a 300 g object"
    would answer 2940 N instead of 2.94. An unlisted unit binds nothing and the
    formula declines (a NameError in `evaluate`), which is the honest outcome —
    precision before coverage.
    """

    format: Literal["rulekit/formulas@1"]
    dimensions: dict[str, list[str]]
    formulas: list[QuantityFormulaDef]

    @model_validator(mode="after")
    def _one_unit_per_dimension(self) -> "FormulasDoc":
        # The docstring's "ONE canonical unit per dimension" is ENFORCED here,
        # because prose does not enforce: a second unit is a second SCALE, and
        # the consumer multiplies whatever it binds ("the weight of a 300 g
        # object" -> 2940 N instead of 2.94). A list is still the shape because
        # the field reads as a set of units, but exactly one is admissible.
        #
        # Surface VARIANTS are not a reason to widen this — the map is keyed on
        # LEMMAS, and canonicalising 'metres'/'meters' -> 'meter' is the
        # lexicon's job (its `plural:` field), not this table's.
        for dim, units in self.dimensions.items():
            if len(units) != 1:
                raise ValueError(
                    f"dimension {dim!r} must list exactly one canonical unit "
                    f"(got {units!r}) — a second unit is a second scale"
                )
        return self


class FormulaDef(StrictModel):
    # a geometry formula: (shape, quantity) -> an expression over named dimensions
    # and the constant `pi`, e.g. shape=circle quantity=area expr="pi * radius**2".
    # DECLARATIVE DATA, never a Python branch (constitution: formulas ->
    # synthesizers with category gates). The `geometry` consumer binds the named
    # dimensions from the ask and evaluates expr.
    shape: str
    quantity: str
    expr: str


class GeometryDoc(StrictModel):
    format: Literal["rulekit/geometry@1"]
    formulas: list[FormulaDef]


class QuarantineEntry(StrictModel):
    tags: list[str] = Field(default_factory=list)
    reason: str


class QuarantineDoc(StrictModel):
    """Words deliberately withheld from the lexicon (difg's poison list).
    Loaded as documentation + lint data, never as vocabulary — re-admission
    is a deliberate, firewalled act."""

    format: Literal["rulekit/quarantine@1"]
    words: dict[str, QuarantineEntry]


class GuardSetting(StrictModel):
    enabled: bool = True
    model_config = ConfigDict(extra="allow")


class GuardsDoc(StrictModel):
    format: Literal["rulekit/guards@1"]
    guards: dict[str, GuardSetting]


class PackDoc(StrictModel):
    format: Literal["rulekit/pack@1"]
    name: str
    version: str = "0.1.0"
    requires: list[str] = Field(default_factory=list)
    activation: dict[str, object] = Field(default_factory=lambda: {"always": True})
    description: str | None = None


class DatasetDef(StrictModel):
    parquet: str
    question: str = "question"
    answer: str = "answer"
    # TYPED GOLD (docs/corpora.md). Absent (the default) => today's
    # float path, byte-identical: the loader parses "#### <n>" to a bare float and
    # skips any row it cannot. `typed` => the loader classifies the gold payload
    # STRUCTURALLY into a harness.firewall.TypedGold, so a gold like "68.04 kg",
    # "$215.14" or "50%" becomes scorable instead of being dropped at build time.
    # GSM8K does NOT set this, so no GSM8K item can construct a TypedGold and no
    # GSM8K item can take the typed branch — byte-identity is a property of the
    # SHAPE of the change, not a lucky outcome.
    gold: Literal["typed"] | None = None
    # HOLDOUT GROUPING. Absent (the default) => the dev-train/dev-holdout cut
    # buckets on the item's own text, byte-identical to before this field
    # existed. Set to a parquet column name => items sharing that column's value
    # land on the SAME side of the internal cut. FOLIO needs this because its
    # items share premise blocks (340 stories -> 1,001 items): a per-item hash
    # puts one story's conclusions on both sides, so dev-holdout stops being a
    # tuning-overfit proxy — the story was already visible from dev-train.
    # Item IDENTITY (item_id) stays on the question text regardless.
    group: str | None = None


class SplitDef(StrictModel):
    from_: str = Field(alias="from")
    bucket: Literal["md5-even", "md5-odd"] | None = None
    firewall: Literal["aggregate-only"] | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProjectionSplitDef(StrictModel):
    """One sentence→semantic-graph corpus slice.

    Projection corpora are deliberately separate from ``DatasetDef``: their
    gold is a logical form, not an answer payload, so routing them through the
    numeric/typed answer judge would erase the intermediate representation the
    corpus exists to measure.
    """

    parquet: str
    text: str = "text"
    logical_form: str = "logical_form"
    item_id: str = "id"
    case: str = "case"
    scored: str | None = "scored"
    firewall: Literal["inspectable", "aggregate-only"] = "inspectable"


class ProjectionProjectDef(StrictModel):
    adapter: Literal["cogs", "pmb"]
    legacy_bridge: bool = True
    splits: dict[str, ProjectionSplitDef]

    @model_validator(mode="after")
    def _required_slices(self) -> "ProjectionProjectDef":
        if self.adapter == "cogs":
            required = {
                "dev-train",
                "dev-holdout",
                "calibration",
                "test",
                "generalization",
            }
            protected = {"test", "generalization"}
        else:
            required = {"train", "development", "test"}
            protected = {"test"}
        missing = required - set(self.splits)
        if missing:
            raise ValueError(
                f"projection project is missing required slices: {sorted(missing)}"
            )
        for name in protected:
            if self.splits[name].firewall != "aggregate-only":
                raise ValueError(
                    f"projection split {name!r} must be aggregate-only"
                )
        return self


class ProjectDoc(StrictModel):
    format: Literal["rulekit/project@1"]
    name: str
    packs: list[str]
    datasets: dict[str, dict[str, DatasetDef]] = Field(default_factory=dict)
    splits: dict[str, SplitDef] = Field(default_factory=dict)
    projection: ProjectionProjectDef | None = None
    suite: str | None = None  # path to a curated YAML suite (small projects)

    @model_validator(mode="after")
    def _one_evaluation_shape(self) -> "ProjectDoc":
        if self.projection is not None and (self.datasets or self.suite is not None):
            raise ValueError(
                "a projection project cannot also declare answer datasets or a suite"
            )
        return self


class ReferenceAttrDef(StrictModel):
    """One attribute of a reference table's rows.

    `by: year` marks a TIME-SERIES attribute: its row values are {year: number}
    maps and a lookup without a stated year DECLINES (answering "the population
    of France" with some silently-chosen year would be a confident guess — the
    engine's epistemics require the question to pin the series point).

    `group: true` marks a TEXT grouping column (e.g. continent): its values
    name the sets aggregates run over ("the total population of Europe") and
    are never themselves answerable — the engine has no text answer kind."""

    by: Literal["year"] | None = None
    group: bool = False

    @model_validator(mode="after")
    def _group_is_not_a_series(self) -> "ReferenceAttrDef":
        if self.group and self.by is not None:
            raise ValueError("a group column cannot also be a time series")
        return self


class ReferenceTableDef(StrictModel):
    """A table of curated real-world facts (difg's reference-seed pattern).

    Rows are plain mappings validated at REGISTRY COMPILE (not here) so the
    error can name the table, row and attribute. `key` names the row field the
    entity slot must match; every other row field must be a declared attribute."""

    name: str
    key: str
    attributes: dict[str, ReferenceAttrDef]
    rows: list[dict[str, object]]


class ReferenceDoc(StrictModel):
    """Curated reference data compiled into the FROZEN registry.

    The dict-not-DuckDB decision is deliberate for this tier: a point lookup
    against a frozen mapping is deterministic across processes by construction
    (the registry contract), and the data is hand-curated pack YAML exactly as
    conversions/formulas are. Tables that outgrow YAML arrive with the
    non-frozen resolver seam (plan phase B2), not by bloating this one."""

    format: Literal["rulekit/reference@1"]
    tables: list[ReferenceTableDef]


KIND_MODELS: dict[str, type[BaseModel]] = {
    "rulekit/lexicon@1": LexiconDoc,
    "rulekit/categories@1": CategoriesDoc,
    "rulekit/conversions@1": ConversionsDoc,
    "rulekit/geometry@1": GeometryDoc,
    "rulekit/formulas@1": FormulasDoc,
    "rulekit/calendar@1": CalendarDoc,
    "rulekit/elements@1": ElementsDoc,
    "rulekit/contractions@1": ContractionsDoc,
    "rulekit/affine-conversions@1": AffineConversionsDoc,
    "rulekit/quarantine@1": QuarantineDoc,
    "rulekit/reference@1": ReferenceDoc,
    "rulekit/numbers@1": NumbersDoc,
    "rulekit/obligations@1": ObligationsDoc,
    "rulekit/rules@1": RulesDoc,
    "rulekit/synth@1": SynthDoc,
    "rulekit/requirements@1": RequirementsDoc,
    "rulekit/guards@1": GuardsDoc,
    "rulekit/pack@1": PackDoc,
    "rulekit/project@1": ProjectDoc,
}
