"""Pydantic models for every rulekit YAML document kind.

Each document declares `format: rulekit/<kind>@<version>`; the loader picks
the model from KIND_MODELS. These models are the single source of truth for
the file formats — the registry compiles from them and the web editor's
JSON Schema is exported from them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# lexicon
# ---------------------------------------------------------------------------


class VerbInfo(StrictModel):
    lemma: str | None = None


class LexiconEntry(StrictModel):
    senses: list[str]
    plural: str | list[str] | None = None  # noun senses: plural surface(s)
    number: Literal["singular", "plural"] | None = None  # grammatical number (pronouns)
    verb: VerbInfo | None = None  # for verb senses: irregular lemma etc.
    notes: str | None = None

    def plurals(self) -> list[str]:
        if self.plural is None:
            return []
        return [self.plural] if isinstance(self.plural, str) else list(self.plural)

    @model_validator(mode="after")
    def _sense_scoped(self) -> "LexiconEntry":
        if self.verb is not None and "verb" not in self.senses:
            raise ValueError("verb info on an entry without a verb sense")
        if self.plural is not None and "noun" not in self.senses:
            raise ValueError("plural on an entry without a noun sense")
        return self


class LexiconDoc(StrictModel):
    format: Literal["rulekit/lexicon@1"]
    entries: dict[str, LexiconEntry]


# ---------------------------------------------------------------------------
# categories (hierarchy + antonyms + context synonyms + attrs)
# ---------------------------------------------------------------------------


class CategoryDef(StrictModel):
    parent: str
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
    # `interchangeable`, never inferred from "has members" alone — 'animal'/
    # 'pet' (this pack) also declare members, for a DIFFERENT purpose
    # (decline-safety regression coverage in `_resolve_measure_against`'s
    # own docstring) with a deliberately PARTIAL, non-exhaustive list (only
    # 3 of the animal words dev-train ever mentions are 'pet' members) — if
    # `_superordinate_total` read `members` directly it would silently sum
    # only the CAPTURED subset while the text's own uncaptured subtype
    # (e.g. an unresolved 'fish' relation) drops out unaccounted, a
    # confident-wrong the dev-train gate itself caught. This flag is the
    # single mandatory guard against that: a category must be explicitly
    # author-vetted as exhaustive before this consumer will touch it.
    superordinate: bool = False
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
    notes: str | None = None


class ContextSynonym(StrictModel):
    gate: str  # governing category that must be present in the text
    forms: list[str]


class CategoriesDoc(StrictModel):
    format: Literal["rulekit/categories@1"]
    categories: dict[str, CategoryDef] = Field(default_factory=dict)
    members: dict[str, list[str]] = Field(default_factory=dict)
    context_synonyms: dict[str, ContextSynonym] = Field(default_factory=dict)
    attrs: dict[str, dict[str, float]] = Field(default_factory=dict)
    part_counts: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# numbers (number words, scales, multipliers, fractions, operators)
# ---------------------------------------------------------------------------


class NumbersDoc(StrictModel):
    format: Literal["rulekit/numbers@1"]
    numbers: dict[str, float] = Field(default_factory=dict)  # "seven" -> 7
    scales: dict[str, float] = Field(default_factory=dict)  # "dozen" -> 12
    multipliers: dict[str, float] = Field(default_factory=dict)  # "twice" -> 2
    fractions: dict[str, float] = Field(default_factory=dict)  # "half" -> 0.5
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
    "number", "fraction", "multiplier", "name", "noun", "plural", "counted",
    "entity", "verb", "auxiliary", "modal", "future_modal", "pronoun", "word",
    "adjective", "possessed", "qualified", "percent",
    # a COORDINATE TUPLE ("(3,4)", "(1,2)") — numbers.py's _TUPLE gives it
    # value_kind "tuple" and a `components` feature; senses.py gives it the
    # `tuple` sense. Structurally disjoint from every other slot type: no
    # scalar-valued unit is ever a tuple and vice versa, so a `point` slot can
    # never tie-break collide with a `number` slot.
    "point",
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

    lit: str | None = None
    slot: str | None = None
    type: str | None = None  # builtin slot type
    cat: str | None = None  # category gate (slot form)
    # OPT-IN: require the slot's noun to be BARE — no compound modifier
    # (condense merge-compound) and no possessive owner. A category gate matches
    # on the unit's LEMMA, and a compound noun keeps its HEAD's lemma, so "the
    # dot product" satisfies a `statistic`-gated slot exactly as "the product"
    # does — and answers 720 (the product of all six components) for a dot
    # product whose answer is 32.
    #
    # This is deliberately NOT the default, because for most categories a
    # compound IS its head: a "guard dog" is a dog, a "school bus" is a bus, and
    # every entity/superordinate gate depends on that staying true. It is only
    # the OPERATION-NAMING categories where the head is a false friend — a dot
    # product is not a product, a cross product is not a product. Set it there
    # and nowhere else; defaulting to False keeps every existing slot byte-
    # identical (the "opt-in parameter, defaulted to old behavior" rule for any
    # change to a shared matcher).
    bare: bool = False
    opt: list["MatchToken"] | None = None  # optional sub-sequence

    @model_validator(mode="after")
    def _one_form(self) -> "MatchToken":
        forms = [self.lit is not None, self.slot is not None, self.opt is not None]
        if sum(forms) != 1:
            raise ValueError("a match token is exactly one of lit/slot/opt")
        if self.slot is not None and (self.type is None) == (self.cat is None):
            raise ValueError("a slot needs exactly one of type/cat")
        if self.bare and self.slot is None:
            raise ValueError("`bare` only qualifies a slot")
        if self.bare and self.type in ("possessed", "qualified"):
            # `possessed`/`qualified` are DEFINED by carrying an owner/qualifier,
            # which is exactly what `bare` forbids — the combination is always
            # false, so it is a authoring mistake, not a narrow gate.
            raise ValueError(f"`bare` contradicts type {self.type!r} (always false)")
        if self.type is not None and self.type not in SLOT_TYPES:
            raise ValueError(f"unknown slot type {self.type!r}")
        return self


class WherePredicate(StrictModel):
    """Closed set of cross-slot constraints."""

    same_lemma: list[str] | None = None
    distinct: list[str] | None = None
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
        set_ = [
            v for v in (
                self.same_lemma, self.distinct, self.distinct_measure,
                self.name_count, self.absent, self.unbound,
            )
            if v is not None
        ]
        if len(set_) != 1:
            raise ValueError("exactly one predicate per where item")
        return self


class FactEmit(StrictModel):
    fact: Literal[
        "quantity", "relation", "membership", "subset", "predication",
        "before", "fraction_quantity", "rest_quantity", "partition_quantity",
        "ratio_quantity", "goal", "group_total", "rate", "discount",
        "percent_change",
    ]
    # remaining fields are fact-kind specific; templated strings "{slot}" or
    # expressions evaluated by the safe evaluator.
    fields: dict[str, str | float | bool] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def _collect_extra(self) -> "FactEmit":
        if self.model_extra:
            self.fields = {**self.fields, **self.model_extra}
        return self


class PatternRule(StrictModel):
    id: str
    phase: Literal["read", "post-saturation"] = "read"
    description: str | None = None
    match: dict[Literal["sentence", "sentences", "question"], list[MatchToken] | list[list[MatchToken]]]
    where: list[WherePredicate] = Field(default_factory=list)
    consumes: list[str] = Field(default_factory=list)  # value-accounting slots
    emits: list[FactEmit] = Field(default_factory=list)
    overrides: dict[str, str] | None = None  # {"rule": id, "reason": ...}


class AskRule(StrictModel):
    id: str
    match: dict[Literal["question"], list[MatchToken]]
    resolves: dict[str, str]  # consumer + query fields, templated


class RulesDoc(StrictModel):
    format: Literal["rulekit/rules@1"]
    rules: list[PatternRule] = Field(default_factory=list)
    asks: list[AskRule] = Field(default_factory=list)


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

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ConversionsDoc(StrictModel):
    format: Literal["rulekit/conversions@1"]
    conversions: list[ConversionDef]


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


class SplitDef(StrictModel):
    from_: str = Field(alias="from")
    bucket: Literal["md5-even", "md5-odd"] | None = None
    firewall: Literal["aggregate-only"] | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProjectDoc(StrictModel):
    format: Literal["rulekit/project@1"]
    name: str
    packs: list[str]
    datasets: dict[str, dict[str, DatasetDef]] = Field(default_factory=dict)
    splits: dict[str, SplitDef] = Field(default_factory=dict)
    suite: str | None = None  # path to a curated YAML suite (small projects)


KIND_MODELS: dict[str, type[BaseModel]] = {
    "rulekit/lexicon@1": LexiconDoc,
    "rulekit/categories@1": CategoriesDoc,
    "rulekit/conversions@1": ConversionsDoc,
    "rulekit/geometry@1": GeometryDoc,
    "rulekit/quarantine@1": QuarantineDoc,
    "rulekit/numbers@1": NumbersDoc,
    "rulekit/obligations@1": ObligationsDoc,
    "rulekit/rules@1": RulesDoc,
    "rulekit/synth@1": SynthDoc,
    "rulekit/requirements@1": RequirementsDoc,
    "rulekit/guards@1": GuardsDoc,
    "rulekit/pack@1": PackDoc,
    "rulekit/project@1": ProjectDoc,
}
