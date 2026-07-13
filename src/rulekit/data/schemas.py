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
    "adjective", "possessed", "qualified",
)


class MatchToken(StrictModel):
    """One position in a match sequence: a literal or a typed/gated slot."""

    lit: str | None = None
    slot: str | None = None
    type: str | None = None  # builtin slot type
    cat: str | None = None  # category gate (slot form)
    opt: list["MatchToken"] | None = None  # optional sub-sequence

    @model_validator(mode="after")
    def _one_form(self) -> "MatchToken":
        forms = [self.lit is not None, self.slot is not None, self.opt is not None]
        if sum(forms) != 1:
            raise ValueError("a match token is exactly one of lit/slot/opt")
        if self.slot is not None and (self.type is None) == (self.cat is None):
            raise ValueError("a slot needs exactly one of type/cat")
        if self.type is not None and self.type not in SLOT_TYPES:
            raise ValueError(f"unknown slot type {self.type!r}")
        return self


class WherePredicate(StrictModel):
    """Closed set of cross-slot constraints."""

    same_lemma: list[str] | None = None
    distinct: list[str] | None = None
    name_count: dict[str, int] | None = None  # {"exactly": 2}
    absent: dict[str, str] | None = None  # {"cat": name} — no such word in sentence

    @model_validator(mode="after")
    def _one(self) -> "WherePredicate":
        set_ = [
            v for v in (self.same_lemma, self.distinct, self.name_count, self.absent)
            if v is not None
        ]
        if len(set_) != 1:
            raise ValueError("exactly one predicate per where item")
        return self


class FactEmit(StrictModel):
    fact: Literal[
        "quantity", "relation", "membership", "subset", "predication",
        "before", "fraction_quantity", "rest_quantity", "partition_quantity",
        "goal", "group_total", "rate",
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
