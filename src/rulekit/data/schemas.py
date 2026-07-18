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
    # OPT-IN phrase capture: this slot binds a RUN of units (greedy-longest,
    # backtracking against the rest of the sequence; a FINAL span must reach
    # the sentence end). Its value is the canonical phrase — per-token lemma
    # normalization, articles/punct dropped, NOTHING looser: logic prose
    # distinguishes classes one NP-internal word apart, and a phrase key is
    # what keeps "opera singer" from answering for "singer" (patterns.
    # _canonical_phrase, model.Atom). Defaults False: every existing slot
    # binds exactly one unit, byte-identical.
    span: bool = False
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
    # Only the named word is affected: other skippables are still skipped,
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
    opt: list["MatchToken"] | None = None  # optional sub-sequence

    @model_validator(mode="after")
    def _one_form(self) -> "MatchToken":
        forms = [self.lit is not None, self.slot is not None, self.opt is not None]
        if sum(forms) != 1:
            raise ValueError("a match token is exactly one of lit/slot/opt")
        if self.span:
            # a span slot captures a RUN of units; it is gated by span_blocks
            # (and by what the surrounding tokens demand), never by type/cat
            if self.slot is None:
                raise ValueError("`span` only qualifies a slot")
            if self.type is not None or self.cat is not None or self.bare:
                raise ValueError("a span slot takes no type/cat/bare")
        elif self.slot is not None and (self.type is None) == (self.cat is None):
            raise ValueError("a slot needs exactly one of type/cat")
        if self.span_blocks is not None and not self.span:
            raise ValueError("`span_blocks` only qualifies a span slot")
        if self.bare and self.slot is None:
            raise ValueError("`bare` only qualifies a slot")
        if self.bare and self.type in ("possessed", "qualified"):
            # `possessed`/`qualified` are DEFINED by carrying an owner/qualifier,
            # which is exactly what `bare` forbids — the combination is always
            # false, so it is a authoring mistake, not a narrow gate.
            raise ValueError(f"`bare` contradicts type {self.type!r} (always false)")
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
        "percent_change", "atom", "quantified", "conditional",
        "disjunction", "quantified_disjunction", "existential",
        "verbal_relation",
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
        return self


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


class QuantityFormulaDef(StrictModel):
    # a named physical quantity -> an expression over DIMENSION names, e.g.
    # quantity=speed expr="distance / time". Sibling of FormulaDef below: that
    # one keys on (shape, quantity) because a geometry formula needs the shape to
    # disambiguate; a physical quantity names its formula on its own.
    quantity: str
    expr: str


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
    # TYPED GOLD (docs/difg-corpus-plan.md). Absent (the default) => today's
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
    "rulekit/formulas@1": FormulasDoc,
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
