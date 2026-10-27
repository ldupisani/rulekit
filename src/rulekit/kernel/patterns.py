"""Pattern-rule matching over the annotated unit sequence.

The successor to difg's 129 hand-ordered system solvers. Differences that
matter:
- Rules match UNITS, not raw text — "1,200" and "twelve hundred" present the
  same value feature, so the comma-regex bug class is gone.
- ALL triggered rules run; nothing short-circuits. Emitted facts go to the
  fact store, which adjudicates agreement/subsumption/collision (facts.py).
- Priority does not exist. Specificity is computed for subsumption only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields, replace
from .reference_identity import reference_from_unit
from .model import AllocationGroup, IndexedPathEvidence, MeasuredComponent, RegionEvidence
from .reference_bindings import project_references
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .facts import FactStore

from ..data.registry import Registry
from ..data.schemas import AskRule, MatchToken, PatternRule
from .evaluate import ArithmeticLog, EvaluationError, evaluate
from .model import (
    ActivityDuration,
    ResourceAllocation,
    ResourceBalance,
    AccountEntry,
    BatchEvidence,
    SpecificationEvidence,
    PopulationEvidence,
    ProportionalBaseEvidence,
    Expenditure,
    BoundedActivityInquiry,
    AgeAtYear,
    Alias,
    Before,
    ClassRefinement,
    CollectionAttribute,
    QuantityEventContext,
    CollectionContext,
    VerbalRelation,
    Conditional,
    ContainerCapacityInquiry,
    ContainerCapacityObservation,
    ContainerContent,
    Contribution,
    Discount,
    Price,
    Disjunction,
    DisjunctiveConditional,
    EnumeratedDisjunction,
    Equivalence,
    EventTime,
    Existential,
    Fact,
    Atom,
    FractionQuantity,
    Goal,
    GroundConditional,
    GroupTotal,
    LocationConstraint,
    LocationEvent,
    LocationTransitionAbsence,
    MeasuredContentChange,
    MixtureEvidence,
    Membership,
    PartitionQuantity,
    PartitionAggregateShare,
    PositiveGroundConditional,
    Quantified,
    QuantifiedAdjustment,
    QuantifiedQuantity,
    QuantifiedDisjunction,
    PercentChange,
    Predication,
    Provenance,
    Quantity,
    Rate,
    RateScope,
    RateThreshold,
    RatePremium,
    RepeatedActivityDuration,
    EventCadence,
    SequenceTotal,
    SequenceStep,
    AccumulationWindow,
    EarningRate,
    ServiceScope,
    PurchaseEndpoint,
    CommercialTerm,
    AllocationRatio,
    InventoryScope,
    InventoryWithdrawal,
    JourneyLeg,
    JourneySchedule,
    JourneyExtra,
    JourneyPace,
    Reading,
    Relation,
    RatioQuantity,
    RestQuantity,
    TotalityTransfer,
    TotalityEvent,
    SemanticGraphEdge,
    SemanticGraphNode,
    SequentialPartition,
    SequentialPartitionInitialShare,
    SequentialPartitionPrefix,
    SequentialPartitionRemainingShare,
    SequentialPartitionRemainder,
    SpatialPlacement,
    Subset,
    TaskCompletionDuration,
    TextValue,
    TextPrefixSplit,
    Unit,
)

SKIPPABLE_SENSES = {"article", "punct"}

_FACT_CLASSES = {
    "region_evidence": RegionEvidence,
    "allocation_group": AllocationGroup,
    "indexed_path_evidence": IndexedPathEvidence,
    "measured_component": MeasuredComponent,
    "batch_evidence": BatchEvidence,
    "specification_evidence": SpecificationEvidence,
    "population_evidence": PopulationEvidence,
    "proportional_base_evidence": ProportionalBaseEvidence,
    "account_entry": AccountEntry,
    "text_value": TextValue,
    "text_prefix_split": TextPrefixSplit,
    "commercial_term": CommercialTerm,
    "allocation_ratio": AllocationRatio,
    "inventory_scope": InventoryScope,
    "inventory_withdrawal": InventoryWithdrawal,
    "journey_leg": JourneyLeg,
    "journey_schedule": JourneySchedule,
    "journey_extra": JourneyExtra,
    "journey_pace": JourneyPace,
    "accumulation_window": AccumulationWindow,
    "earning_rate": EarningRate,
    "service_scope": ServiceScope,
    "purchase_endpoint": PurchaseEndpoint,
    "event_cadence": EventCadence,
    "sequence_total": SequenceTotal,
    "sequence_step": SequenceStep,
    "rate_threshold": RateThreshold,
    "rate_premium": RatePremium,
    "repeated_activity_duration": RepeatedActivityDuration,
    "resource_allocation": ResourceAllocation,
    "resource_balance": ResourceBalance,
    "expenditure": Expenditure,
    "activity_duration": ActivityDuration,
    "bounded_activity_inquiry": BoundedActivityInquiry,
    "age_at_year": AgeAtYear,
    "task_completion_duration": TaskCompletionDuration,
    "quantity": Quantity,
    "relation": Relation,
    "membership": Membership,
    "atom": Atom,
    "quantified": Quantified,
    "quantified_adjustment": QuantifiedAdjustment,
    "quantified_quantity": QuantifiedQuantity,
    "class_refinement": ClassRefinement,
    "conditional": Conditional,
    "contribution": Contribution,
    "disjunction": Disjunction,
    "equivalence": Equivalence,
    "disjunctive_conditional": DisjunctiveConditional,
    "ground_conditional": GroundConditional,
    "positive_ground_conditional": PositiveGroundConditional,
    "existential": Existential,
    "quantified_disjunction": QuantifiedDisjunction,
    "alias": Alias,
    "subset": Subset,
    "predication": Predication,
    "before": Before,
    "event_time": EventTime,
    "fraction_quantity": FractionQuantity,
    "rest_quantity": RestQuantity,
    "partition_quantity": PartitionQuantity,
    "partition_aggregate_share": PartitionAggregateShare,
    "collection_context": CollectionContext,
    "collection_attribute": CollectionAttribute,
    "quantity_event_context": QuantityEventContext,
    "sequential_partition": SequentialPartition,
    "sequential_partition_initial_share": SequentialPartitionInitialShare,
    "sequential_partition_prefix": SequentialPartitionPrefix,
    "sequential_partition_remaining_share": SequentialPartitionRemainingShare,
    "sequential_partition_remainder": SequentialPartitionRemainder,
    "ratio_quantity": RatioQuantity,
    "goal": Goal,
    "group_total": GroupTotal,
    "rate": Rate,
    "rate_scope": RateScope,
    "price": Price,
    "discount": Discount,
    "percent_change": PercentChange,
    "verbal_relation": VerbalRelation,
    "location_event": LocationEvent,
    "location_constraint": LocationConstraint,
    "location_transition_absence": LocationTransitionAbsence,
    "spatial_placement": SpatialPlacement,
    "measured_content_change": MeasuredContentChange,
    "mixture_evidence": MixtureEvidence,
    "container_content": ContainerContent,
    "container_capacity_inquiry": ContainerCapacityInquiry,
    "container_capacity_observation": ContainerCapacityObservation,
    "totality_transfer": TotalityTransfer,
    "totality_event": TotalityEvent,
    "semantic_graph_node": SemanticGraphNode,
    "semantic_graph_edge": SemanticGraphEdge,
}


@dataclass
class Match:
    rule: PatternRule
    slots: dict[str, Unit]
    consumed: tuple[int, ...]  # uids of consumed units (the match span)
    specificity: tuple[int, int, int] = (0, 0, 0)


@dataclass
class RuleMatchResult:
    match: Match
    facts: list[Fact] = field(default_factory=list)


def looks_third_person_singular(fold: str) -> bool:
    """Does this verb surface carry the -s AGREEMENT suffix?

    `bare_form` reads `fold == lemma` as "uninflected", which is only ever as
    good as the lemma data: a verb whose 3sg form is registered as its OWN
    lemma (no mapping to the bare form) passes the test while being the most
    inflected form there is. 71 such verbs are in the lexicon today -- 'lives'
    among them -- so "Rochelle lives in Europe" minted a UNIVERSAL over the
    class 'rochelle' from a ground sentence about one named individual.

    So test the SUFFIX too, and fail closed. An English bare form ending in a
    single 's' is essentially nonexistent: the real ones double it or sit on a
    Latin stem ('pass', 'discuss', 'possess', 'focus', 'bus'), both excluded
    here. Refusing is monotone-safe -- it mints FEWER universals, never more.
    """
    return (
        len(fold) > 3
        and fold.endswith("s")
        and not fold.endswith(("ss", "us"))
    )


def is_past_participle_form(fold: str, lemma: str, reg: Registry) -> bool:
    """Productive participles and explicitly declared invariant forms."""
    entry = reg.lexicon.get(fold)
    return bool(entry and entry.verb and entry.verb.past_participle) or (
        fold.endswith(("ed", "en")) and fold != lemma)


def is_bare_verb_form(fold: str, lemma: str) -> bool:
    """Whether one analyzed verb surface supplies bare-form evidence.

    Kept public so the authoring-only generator and the runtime matcher use
    one structural definition.  Lexical lemma declarations still come from
    packs; the suffix check only fails closed when that declaration is absent.
    """

    # Condensation keeps a particle on the unit surface (``pick up``) while
    # the lexical lemma remains the head verb (``pick``). Agreement belongs
    # to that first word, so test it rather than rejecting every valid bare
    # particle verb merely because the complete folded surface differs.
    head = fold.split(" ", 1)[0]
    return (fold == lemma or head == lemma) and not looks_third_person_singular(
        head
    )


def is_finite_verb_form(fold: str, lemma: str) -> bool:
    """Whether a verb surface can head a finite matrix clause.

    Productive ``-ing`` forms are the structurally observable non-finite class
    represented by the current lexicon. Simple past remains admitted because
    regular ``-ed`` is ambiguous between finite past and participial form
    without an auxiliary; the surrounding rule owns that distinction.
    """

    return not (fold.endswith("ing") and fold != lemma)


def proportional_delta_is_compatible(
    value: object, polarity: int | None
) -> bool:
    """Whether ``1 + value * polarity`` stays in its valid quantity domain."""

    return (
        isinstance(value, (int, float))
        and float(value) >= 0.0
        and polarity is not None
        and (polarity >= 0 or float(value) <= 1.0)
    )


def is_bare_referent(unit: Unit) -> bool:
    """No owner, modifier or instance label, including through a pronoun.

    A reference does not erase the identity restrictions on its antecedent.
    Cyclic or unresolved references cannot establish a bare individual.
    """
    seen = set()
    while id(unit) not in seen:
        seen.add(id(unit))
        if any(unit.features.get(key) is not None for key in ("qualifier", "owner", "label")):
            return False
        if unit.sense() != "pronoun":
            return True
        targets = [ob.target for ob in unit.obligations()
                   if ob.need == "refers" and ob.met and isinstance(ob.target, Unit)]
        if len(targets) != 1:
            return False
        unit = targets[0]
    return False


def _slot_ok(unit: Unit, token: MatchToken, reg: Registry) -> bool:
    if (
        token.common_noun_cat is not None
        and unit.sense() == "noun"
        and not _unit_in_category(unit, token.common_noun_cat, reg)
    ):
        # A proper name (or resolved pronoun) is independently referential;
        # only a common noun needs the rule's positive semantic-role license.
        return False
    if token.single_word and len(unit.words) != 1:
        # OPT-IN (schemas.MatchToken.single_word): condensation preserves the
        # original words on the merged Unit, so this structurally refuses
        # particle/perfect verbs without naming either vocabulary class.
        return False
    if token.present_participle:
        fold = unit.features.get("fold") or ""
        if not fold.endswith("ing") or fold == _lemma_of(unit):
            # OPT-IN (schemas.MatchToken.present_participle): an active
            # reduced relative needs non-finite -ing morphology. Requiring
            # an actual lemma change prevents a bare lemma such as "sing"
            # from masquerading as participial syntax by suffix alone.
            return False
    if token.past_participle:
        fold = unit.features.get("fold") or ""
        if not is_past_participle_form(fold, _lemma_of(unit), reg):
            # OPT-IN (schemas.MatchToken.past_participle): a direct passive
            # needs productive participial morphology or an explicit lexical
            # declaration. Bare suffix lookalikes remain excluded.
            return False
    if token.bare_form and not is_bare_verb_form(
        unit.features.get("fold") or "",
        _lemma_of(unit),
    ):
        # OPT-IN (schemas.MatchToken.bare_form): only the verb's BARE form —
        # plural agreement is the structural generic-vs-ground signal after a
        # bare-plural subject ("Writers CREATE" ∀ vs "Mary CREATES" ground)
        return False
    if token.finite_form and not is_finite_verb_form(
        unit.features.get("fold") or "",
        _lemma_of(unit),
    ):
        return False
    if token.class_only and (unit.sense() != "noun" or any(
        unit.features.get(key) is not None for key in ("owner", "label")
    )):
        return False
    if token.bare and not is_bare_referent(unit):
        # OPT-IN (schemas.MatchToken.bare, default False — every pre-existing
        # slot is byte-identical): a compound noun keeps its HEAD's lemma, so a
        # category gate cannot tell "the dot product" from "the product". An
        # operation-naming slot sets `bare: true` to demand the head itself.
        return False
    if token.uncounted and unit.features.get("value_kind") is not None:
        return False
    if token.counted and not (
        unit.sense() == "noun"
        and unit.features.get("value_kind") == "count"
    ):
        # OPT-IN (schemas.MatchToken.counted): category membership alone
        # admits the bare noun because a condensed count keeps its noun lemma.
        # Require the counted-unit structure as an independent gate.
        return False
    if token.possessed and not (
        unit.sense() == "noun" and unit.features.get("owner")
    ):
        # OPT-IN (schemas.MatchToken.possessed): category membership follows
        # the merged noun's lemma, so it otherwise also admits the bare head.
        # Require the independently represented possessive owner.
        return False
    if token.qualified and not (
        unit.sense() == "noun"
        and unit.features.get("qualifier") is not None
        and (
            unit.features.get("value_kind") != "attributive_count"
            or token.attributive_counted
        )
    ):
        # OPT-IN (schemas.MatchToken.qualified): category membership follows
        # a merged noun's head lemma, so it otherwise also admits the bare
        # head. Require the independently represented qualifier.
        return False
    if token.attributive_counted and not (
        unit.sense() == "noun"
        and unit.features.get("value_kind") == "attributive_count"
        and isinstance(unit.features.get("value"), (int, float))
        and unit.features.get("qualifier") is not None
        and reg.measure_applies_to_holder(
            unit.features["qualifier"], _lemma_of(unit)
        )
    ):
        # Numeric noun modifiers are structural, but their meaning is still
        # pack-owned: "100-page book" is licensed only when the qualifier is
        # a declared measure of the head noun.  An equally shaped
        # "100-rabbit book" remains unread.
        return False
    if token.qualifier_cat is not None and not reg.word_in_category(
        unit.features.get("qualifier", ""), token.qualifier_cat
    ):
        return False
    if (
        token.number is not None
        and unit.features.get("number") != token.number
    ):
        return False
    if token.standalone and unit.sense() == "noun":
        # A condensed count ("6 marbles") deliberately retains
        # value_kind=count, so it satisfies the broad `number` type. Elided
        # scalar constructions opt out of that reading without constraining
        # how many source words formed the standalone number itself.
        return False
    if token.integer:
        value = unit.features.get("value")
        if not isinstance(value, (int, float)) or not float(value).is_integer():
            return False
    if token.value_min is not None:
        value = unit.features.get("value")
        if not isinstance(value, (int, float)) or float(value) < token.value_min:
            return False
    if token.value_max is not None:
        value = unit.features.get("value")
        if not isinstance(value, (int, float)) or float(value) > token.value_max:
            return False
    if token.fraction_within_whole:
        value = unit.features.get("value")
        if not (
            isinstance(value, (int, float))
            and 0.0 <= float(value) <= 1.0
        ):
            return False
    if token.word_fraction_within_whole and not unit.features.get("percent"):
        value = unit.features.get("value")
        if not (
            isinstance(value, (int, float))
            and 0.0 <= float(value) <= 1.0
        ):
            return False
    if token.fraction_positive:
        value = unit.features.get("value")
        if not (
            isinstance(value, (int, float)) and float(value) > 0.0
        ):
            return False
    if token.type is not None:
        t = token.type
        sense = unit.sense()
        kind = unit.features.get("value_kind")
        if t == "scale_label":
            return kind == "scale_label"
        if t == "ordinal":
            return kind == "ordinal"
        if t == "number":
            return kind == "count"
        if t == "fraction":
            # A declared plural fraction surface ("fifths") is an
            # incomplete phrase until numbers.py merges an explicit word
            # count with it ("two fifths"). Singular forms and completed
            # counted forms remain ordinary fractions.
            return kind == "fraction" and not unit.features.get(
                "requires_count"
            )
        if t == "percent":
            # mining candidate discounted-purchase-totals: the PERCENT
            # subset of fraction tokens only — numbers.py sets the
            # `percent` feature exclusively for "%"/"percent" surface
            # forms, never for word fractions ("half", "one third"), so
            # "half off" structurally cannot satisfy this slot the way
            # "50% off" does. Keeps the discount rules structurally
            # disjoint from every existing fraction-consuming rule (the
            # relation rules read plain `type: fraction` under a
            # completely different trailing literal — "more"/"fewer"/"as
            # many as", never "off"/"discount" — so there is no overlap
            # even before this narrower gate).
            return kind == "fraction" and bool(unit.features.get("percent"))
        if t == "multiplier":
            return kind == "multiplier"
        if t == "nonunit_multiplier":
            value = unit.features.get("value")
            return (
                kind == "multiplier"
                and isinstance(value, (int, float))
                and float(value) != 1.0
            )
        if t == "formula":
            # a CHEMICAL FORMULA token (numbers.py `_FORMULA`, validated
            # against the element table). Disjoint from every scalar slot type
            # on the same argument as `point` and `date`: it carries no value.
            return kind == "formula"
        if t == "date":
            # an ISO date token (numbers.py _ISO_DATE). Disjoint from every
            # scalar slot type by construction: a date unit carries no `value`,
            # and a valued unit is never value_kind "date".
            return kind == "date"
        if t == "point":
            # a COORDINATE TUPLE ("(3,4)") — numbers.py's _TUPLE. Disjoint from
            # every scalar slot type by construction: a tuple unit carries no
            # `value`, and a valued unit is never value_kind "tuple".
            return kind == "tuple"
        if t == "name":
            # a RESOLVED pronoun satisfies a name slot (it denotes its
            # antecedent); an unresolved one never does (definitive-or-decline)
            if sense == "pronoun":
                return any(
                    ob.need == "refers" and ob.met for ob in unit.obligations()
                )
            return sense == "name"
        if t == "noun":
            return sense == "noun"
        if t == "preposition":
            return sense == "preposition"
        if t == "proper_name":
            # NAME sense only — no resolved-pronoun path (schemas.SLOT_TYPES:
            # a pronoun subject is definite reference, and the bare-plural
            # universal rule must never read "They are dogs" as a generic)
            return sense == "name"
        if t == "bare_plural":
            # a plural noun that can head a GENERIC (schemas.SLOT_TYPES):
            # possessive-merged, attribute-merged and COUNT-merged units all
            # refuse — "Three dogs are pets" is three particular dogs, and
            # merge-count leaves exactly a plural noun unit behind
            return (
                sense == "noun"
                and unit.features.get("number") == "plural"
                and unit.features.get("owner") is None
                and unit.features.get("qualifier") is None
                and kind != "count"
            )
        if t == "generic_plural":
            # The modifier-preserving sibling of `bare_plural`: a generic
            # class may be a compound ("head teachers"), but never a
            # possessive phrase or a numerically bounded group ("three
            # teachers"). The emitter uses `.qualified` to retain the full
            # class key rather than this unit's bare head lemma.
            return (
                sense == "noun"
                and unit.features.get("number") == "plural"
                and unit.features.get("owner") is None
                and kind != "count"
            )
        if t == "entity":
            # anything that can HOLD a quantity: a name, a common noun
            # ("the factory"), or a resolved pronoun
            if sense == "pronoun":
                return any(ob.need == "refers" and ob.met for ob in unit.obligations())
            return sense in ("name", "noun")
        if t == "possessed":
            # a noun merged from "OWNER 's NOUN" (condense.py merge-
            # possessive tags it with an `owner` feature) — structural
            # possessive 's, never a bare common noun or a plain name
            return sense == "noun" and unit.features.get("owner") is not None
        if t == "qualified":
            # a noun merged from ADJECTIVE+NOUN or NOUN+NOUN (condense.py
            # merge-attribute / merge-compound tags it with a `qualifier`
            # feature) — "coconut trees", "red apples"; a bare noun with no
            # attributive modifier never matches (increment 34 mirror of
            # `possessed`)
            return (
                sense == "noun"
                and unit.features.get("qualifier") is not None
                and (
                    kind != "attributive_count"
                    or token.attributive_counted
                )
            )
        if t == "plural":
            return (
                sense == "noun"
                and unit.features.get("number") == "plural"
                # A numeric hyphen modifier is a semantic restriction, not a
                # transparent plural surface. It needs a rule that explicitly
                # opts into `attributive_counted`; otherwise "four-minute
                # songs" could query all songs while silently dropping four.
                and kind != "attributive_count"
            )
        if t == "common_noun":
            # mining candidate conjunct-comparative-quantities: a BARE
            # common-noun holder — sense noun, no `owner` (never a
            # possessive-merged noun, `possessed`'s own tag), no
            # `qualifier` (never an attribute-merged noun, `qualified`'s
            # own tag), not plural (the plural-combined ask family's own
            # territory). Structurally disjoint from `possessed`/
            # `qualified`/`name` by construction — see SLOT_TYPES' comment.
            return (
                sense == "noun"
                and unit.features.get("owner") is None
                and unit.features.get("qualifier") is None
                and unit.features.get("number") != "plural"
            )
        if t == "counted":
            return sense == "noun" and kind == "count"
        if t == "verb":
            return sense == "verb"
        if t == "nonstate_verb":
            # an EVENT verb: verb-sensed and not in the structural
            # `non_event_verb` category. `state` inherits that category, while
            # copular forms that must stay out of event readers need not gain
            # arithmetic holding semantics. BOTH fold and lemma are checked:
            # categories may list surface forms or canonical forms.
            return sense == "verb" and not (
                reg.word_in_category(
                    unit.features.get("fold", ""), "non_event_verb"
                )
                or reg.word_in_category(
                    unit.features.get("lemma", ""), "non_event_verb"
                )
            )
        if t == "auxiliary":
            return sense == "auxiliary"
        if t == "modal":
            # increment 14 split 'modal' (can/could/will/would/should/may/
            # might/must) from 'auxiliary' precisely so factual asks
            # (auxiliary-gated) exclude it and a capacity ask (budget ÷
            # unit price) can claim the modal token structurally.
            return sense == "modal"
        if t == "future_modal":
            # mining candidate will-tense-asks: an ordinary factual ask's
            # aux slot ALSO accepts the future/conditional modal pair
            # (will/would, the `future_modal` category — packs/core-
            # english/categories/core.yaml) alongside the plain auxiliary
            # (do/does/did) it already matched. The other 6 modal-sense
            # words (can/could/should/may/might/must — capacity/
            # hypothetical modals) are NOT in `future_modal`, so they stay
            # excluded here exactly as before: the increment-14 kirsty
            # lesson (a wanted/hypothetical purchase is not a purchase)
            # cannot recur through this slot.
            if sense == "auxiliary":
                return True
            if sense == "modal":
                word = unit.features.get("lemma", unit.features.get("fold", ""))
                return reg.word_in_category(word, "future_modal")
            return False
        if t == "pronoun":
            return sense == "pronoun"
        if t == "word":
            return sense not in (None, "punct")
        if t == "adjective":
            return sense == "adjective"
        return False
    assert token.cat is not None
    word = unit.features.get("lemma", unit.features.get("fold", ""))
    return reg.word_in_category(word, token.cat) or reg.word_in_category(
        unit.features.get("fold", ""), token.cat
    )


def _referential_slot_ok(
    units: list[Unit],
    index: int,
    unit: Unit,
    token: MatchToken,
    reg: Registry,
) -> bool:
    """Check the opt-in surface-reference boundary for one matched slot."""

    if not token.referential:
        return True
    if unit.sense() in {"name", "pronoun"}:
        return True
    if unit.sense() != "noun":
        return False
    if (
        token.determinerless_category is not None
        and reg.word_in_category(
            _lemma_of(unit), token.determinerless_category
        )
    ):
        if unit.features.get("owner"):
            return False
        if index > 0:
            predecessor = units[index - 1]
            predecessor_fold = predecessor.features.get("fold", "")
            if (
                predecessor.sense() == "article"
                or reg.word_in_category(
                    predecessor_fold, "possessive_determiner"
                )
            ):
                return False
    if unit.features.get("owner"):
        return True
    # A productive index label makes a common-noun entity specific without
    # an article: "team A", "jar B", and "period 3" identify one member of
    # the named series. The label is structural condense output, not a
    # lexical exception, and is already part of relation identity.
    if unit.features.get("label"):
        return True
    if unit.features.get("value_kind") == "count":
        return True
    # Bare plural noun phrases are grammatically complete arguments and can
    # name a comparison class ("twice as many nickels as dimes"). The
    # determiner requirement is for otherwise-unanchored singular common
    # nouns such as "as pencil" or "in garden".
    if unit.features.get("number") == "plural":
        return True
    lemma = _lemma_of(unit)
    if (
        token.bare_reference_category is not None
        and reg.word_in_category(lemma, token.bare_reference_category)
    ):
        return True
    if index <= 0:
        return False
    predecessor = units[index - 1]
    fold = predecessor.features.get("fold", "")
    return (
        predecessor.sense() == "article"
        or reg.word_in_category(fold, "possessive_determiner")
    )


def is_referential_entity(
    reading: Reading,
    unit: Unit,
    reg: Registry,
    *,
    bare_reference_category: str | None = None,
) -> bool:
    """Apply the matcher's entity-reference boundary outside a rule match.

    Discourse grouping needs to decide whether a prior common-noun subject
    denotes one recoverable entity.  Reusing this entry point keeps articles,
    possessives, labels, counted references, plurals, and declared bare
    exceptions aligned with ``MatchToken(referential=True)`` rather than
    growing a second hand-copied definition in ``document.py``.
    """

    try:
        index = reading.units.index(unit)
    except ValueError:
        return False
    return _referential_slot_ok(
        reading.units,
        index,
        unit,
        MatchToken(
            slot="entity",
            type="entity",
            referential=True,
            bare_reference_category=bare_reference_category,
        ),
        reg,
    )


_MEASURE_ANAPHOR_UNRESOLVED = "$anaphor:measure-unresolved$"


def _lemma_of(unit: Unit) -> str:
    # an elided measure-noun anaphor ("12 yellow ONES" — mining candidate
    # measure-noun-anaphor, condense.py's merge-measure-anaphor) speaks AS
    # the antecedent document.py's `_bind_measure_anaphor` resolved it to;
    # unresolved leaves the SAME reserved sentinel learn.py's own `_lemma`
    # falls back to — this compound's own fold ("yellow ones") is never a
    # real measure name, and its stale `lemma` feature (senses.py's
    # fallback assignment for every lexicon word, pronouns included) is
    # the anaphor's OWN word, not the antecedent — using either would be a
    # silent wrong, not a decline.
    if unit.features.get("measure_anaphor"):
        antecedent_lemma = unit.features.get("antecedent_lemma")
        return antecedent_lemma if antecedent_lemma is not None else _MEASURE_ANAPHOR_UNRESOLVED
    # a pronoun whose `refers` bound cross-sentence speaks AS its antecedent
    if unit.sense() == "pronoun":
        for ob in unit.obligations():
            if ob.need == "refers" and ob.met and isinstance(ob.target, Unit):
                reference = reference_from_unit(unit)
                if reference.resolved:
                    return reference.head
    return unit.features.get("lemma", unit.features.get("fold", unit.surface.lower()))


def _role_is_proper_name(unit: Unit, reg: Registry) -> bool:
    """Whether a semantic role denotes a proper name, directly or by reference."""

    if _slot_ok(unit, MatchToken(slot="role", type="proper_name"), reg):
        return True
    if unit.sense() != "pronoun":
        return False
    return any(
        ob.need == "refers"
        and ob.met
        and isinstance(ob.target, Unit)
        and _slot_ok(
            ob.target,
            MatchToken(slot="role", type="proper_name"),
            reg,
        )
        for ob in unit.obligations()
    )


def _unit_in_category(unit: Unit, category: str, reg: Registry) -> bool:
    """Match category membership through either canonical or surface form."""

    return reg.word_in_category(
        _lemma_of(unit), category
    ) or reg.word_in_category(
        unit.features.get("fold", unit.surface.casefold()), category
    )


def _category_roles_overlap(left: Unit, right: Unit, reg: Registry) -> bool:
    """Whether unqualified noun roles are a declared category/member pair."""

    if left.sense() != "noun" or right.sense() != "noun":
        return False
    left_ref, right_ref = reference_from_unit(left), reference_from_unit(right)
    if (left_ref.head == right_ref.head and left_ref.described
            and right_ref.described and left_ref != right_ref):
        return False
    left_label = left.features.get("label")
    right_label = right.features.get("label")
    if left_label and right_label and left_label != right_label:
        return False
    left_owner = left.features.get("owner")
    right_owner = right.features.get("owner")
    if left_owner and right_owner and left_owner != right_owner:
        return False
    return reg.category_terms_overlap(_lemma_of(left), _lemma_of(right))


def _span_article_units(span: tuple, reading) -> list[tuple]:
    """(article_unit, successors) pairs for a span — its INTERNAL articles
    plus any article on its physical LEADING EDGE. The pre-token skip loop
    advances past leading skippables before a span starts capturing ("is A
    dog" — the article sits between the consumed lit and span[0]), so a
    span-internal scan alone misses exactly the copular construction; the
    walk-back over skippable predecessors is the blocks_skipped precedent."""
    pairs = []
    for i, u in enumerate(span):
        if u.sense() == "article":
            pairs.append((u, span[i + 1:]))
    if reading is not None and span:
        first = span[0]
        idx = next(
            (k for k, u in enumerate(reading.units) if u is first), None
        )
        j = (idx or 0) - 1
        while idx is not None and j >= 0:
            u = reading.units[j]
            if u.sense() not in SKIPPABLE_SENSES:
                break
            if u.sense() == "article":
                pairs.append((u, span))
                break
            j -= 1
    return pairs


def span_swallowed_indefinite(span: tuple, reading, reg: Registry) -> bool:
    """The span's phrase was INDEFINITE — an 'a'/'an' rode inside it or on
    its leading edge (dropped from the key either way, being skippable)."""
    return any(
        reg.word_in_category(u.features.get("fold", ""), "indefinite_article")
        for u, _tail in _span_article_units(span, reading)
    )


def resolution_templates(
    fields: Mapping[str, str | list[str]],
) -> Iterable[str]:
    """Yield scalar templates from an ask's scalar-or-list query fields."""
    for value in fields.values():
        if isinstance(value, str):
            yield value
        else:
            yield from value


def field_definite_common(ask, field: str, match, reading, reg: Registry) -> bool:
    """True when the ask FIELD's span carries a DEFINITE article (internal
    or leading-edge) whose next nominal — past adjectives and skippables —
    is a COMMON noun: the question phrase is a definite DESCRIPTION ('the
    football club'), which must never be satisfied by an indefinite premise
    (composition-design.md Phase 0). A definite-surfaced NAME ('the Emmet
    Building', 'the United Kingdom') is NOT a description — the article is
    part of the name's surface — so a name successor passes. Scoped to the
    one field: a definite article in the question's OTHER spans must not
    poison unrelated matches."""
    templates = list(
        resolution_templates(
            {field: ask.resolves.get(field, "")}
        )
    )
    for choice in ask.interpretations:
        templates.extend(
            resolution_templates(
                {field: choice.resolves.get(field, "")}
            )
        )
    tpl = " ".join(templates)
    for mm in _TEMPLATE.finditer(tpl):
        span = match.slots.get(mm.group(1))
        if not isinstance(span, tuple):
            continue
        for art, successors in _span_article_units(span, reading):
            if not reg.word_in_category(
                art.features.get("fold", ""), "definite_article"
            ):
                continue
            for nxt in successors:
                s = nxt.sense()
                if s in SKIPPABLE_SENSES or s == "adjective":
                    continue
                if s == "noun":
                    return True
                break
    return False


def qualified_render(words: list[str], lemma: str) -> str:
    """THE one definition of the qualified-phrase render: a unit's fold words
    with the head canonicalized to the lemma ('chocolate dogs' -> 'chocolate
    dog'). A multi-word lemma is a WHOLE-UNIT lemma, never a head replacement
    — merge-name (condense.py) sets a merged name's lemma to its full fold,
    and prepending the fold's other words again duplicated them ('Emmet
    Building' -> 'emmet emmet building') in every phrase key and query built
    from one. Four call sites shared the broken idiom (span capture, atom
    decomposition's lead nominal, {slot.qualified}, the fold's Membership);
    they all call this now."""
    if len(words) > 1 and " " not in lemma:
        return " ".join(words[:-1] + [lemma])
    return lemma


def _try_match_at(
    units: list[Unit],
    start: int,
    tokens: list[MatchToken],
    reg: Registry,
    slots: dict[str, Unit],
    consumed: list[int],
) -> int | None:
    """Match tokens against units from `start`; returns the next unit index
    after the match, or None. Skippable units may sit between tokens."""
    i = start
    for k, token in enumerate(tokens):
        if token.opt is not None:
            sub_slots = dict(slots)
            sub_consumed = list(consumed)
            end = _try_match_at(units, i, token.opt, reg, sub_slots, sub_consumed)
            if end is not None:
                slots.update(sub_slots)
                consumed[:] = sub_consumed
                i = end
            continue
        while i < len(units) and units[i].sense() in SKIPPABLE_SENSES:
            if (
                token.lit is not None
                and token.consume_skipped
                and units[i].features.get("fold") in token.lit_options
            ):
                # a consume_skipped lit CLAIMS its skippable unit — the skip
                # stops here and the normal lit match below consumes it
                break
            i += 1
        if i >= len(units):
            return None
        if (
            token.blocks_skipped
            and i > 0
            and units[i - 1].sense() in SKIPPABLE_SENSES
            and reg.word_in_category(
                units[i - 1].features.get("fold", ""), token.blocks_skipped
            )
        ):
            # the token's PHYSICAL predecessor is a skippable unit of the
            # blocked category — the construction is not the one this rule
            # reads (the indefinite-existential gate). Checked against the
            # predecessor, NOT this attempt's own skip walk: match_all
            # floats, and a retry that starts AFTER the article would
            # otherwise never see it.
            return None
        if not _referential_slot_ok(units, i, units[i], token, reg):
            return None
        if token.span:
            # OPT-IN phrase capture (schemas.MatchToken.span): bind a RUN of
            # units, GREEDY-LONGEST with backtracking — the longest capture
            # whose remainder still matches wins, so an inner copula stays
            # inside the phrase ("buildings that are tall" under a
            # `... {lit: are} ...` rule) unless the trailing tokens need it.
            # A FINAL span (nothing after it) must therefore run to the
            # sentence end: shorter captures only survive when the rest of
            # the sequence consumes what they leave, and an empty rest
            # consumes nothing — silently dropping a phrase TAIL would turn
            # exact-phrase matching into prefix matching, which is the
            # overclaim this flag exists to prevent.
            rest = tokens[k + 1:]
            for end in range(len(units), i, -1):
                captured = tuple(units[i:end])
                if token.enumeration_cat:
                    members = _category_enumeration(captured, token.enumeration_cat, reg)
                    if members is None or len(members) < token.enumeration_min_members:
                        continue
                if not any(u.sense() not in SKIPPABLE_SENSES for u in captured):
                    continue  # a span must capture something meaningful
                if not rest and any(
                    u.sense() not in SKIPPABLE_SENSES for u in units[end:]
                ):
                    continue  # final span: nothing meaningful may trail it
                if token.span_blocks_counted and any(
                    u.sense() == "noun" and "value" in u.features
                    for u in captured
                ):
                    # a merged counted noun may not ride inside this span
                    # (schemas.MatchToken.span_blocks_counted)
                    continue
                blocked_cats = (
                    [token.span_blocks] if isinstance(token.span_blocks, str)
                    else (token.span_blocks or [])
                )
                # both the lemma AND the fold are checked: an anaphora-
                # RESOLVED pronoun's lemma is its antecedent ('either' ->
                # 'rex'), so a lemma-only check waves the blocked word
                # through; the fold is the folded SURFACE and survives
                # resolution. (Every negation-block user has fold == lemma,
                # so this widening changes nothing for them.)
                if blocked_cats and any(
                    reg.word_in_category(_lemma_of(u), c)
                    or reg.word_in_category(u.features.get("fold", ""), c)
                    for u in captured for c in blocked_cats
                ):
                    # a blocked word (e.g. a negation) may NEVER be swallowed
                    # into a phrase — negation is read structurally by an
                    # explicit token or not at all. No shorter fallback that
                    # silently drops the tail: the guard above already keeps
                    # final spans full-length, and a non-final shorter capture
                    # still re-checks this condition on ITS OWN contents.
                    continue
                sub_slots = dict(slots)
                sub_consumed = list(consumed) + [u.uid for u in captured]
                tail = _try_match_at(units, end, rest, reg, sub_slots, sub_consumed)
                if tail is None:
                    continue
                sub_slots[token.slot] = captured  # type: ignore[assignment]
                slots.update(sub_slots)
                consumed[:] = sub_consumed
                return tail
            return None
        if token.at_start and any(
            u.sense() not in SKIPPABLE_SENSES for u in units[:i]
        ):
            # OPT-IN anchor (schemas.MatchToken.at_start): nothing MEANINGFUL may
            # precede. Skippables stay invisible here exactly as they are to the
            # loop above — an anchor that tripped on a leading article would be a
            # different rule than the one the author wrote.
            return None
        unit = units[i]
        if token.lit is not None:
            # `lit_options` is a one-element tuple for a scalar literal, so an
            # alternation takes the identical path (schemas.MatchToken)
            if unit.features.get("fold") not in token.lit_options:
                return None
        else:
            if not _slot_ok(unit, token, reg):
                return None
            name = token.slot
            if name in slots and (
                isinstance(slots[name], tuple)  # a span slot never re-binds
                or reference_from_unit(slots[name]) != reference_from_unit(unit)
            ):
                return None  # repeated slot must bind the same lemma
            slots[name] = unit
        consumed.append(unit.uid)
        i += 1
    return i


def match_sequence(
    reading: Reading, tokens: list[MatchToken], reg: Registry
) -> Match | None:
    """First (leftmost) match of a token sequence anywhere in the sentence."""
    matches = match_all(reading, tokens, reg, limit=1)
    return matches[0] if matches else None


def match_all(
    reading: Reading,
    tokens: list[MatchToken],
    reg: Registry,
    limit: int = 8,
    *,
    overlapping: bool = False,
) -> list[Match]:
    """All leftmost matches, non-overlapping unless explicitly requested.

    The default keeps compound-clause matching unchanged. Opt-in overlapping
    matching advances one unit after the previous match START, allowing one
    local rule to see both links in an adjacent chain such as N-P-N-P-N.
    """
    units = reading.units
    unit_index = {unit.uid: index for index, unit in enumerate(units)}
    out: list[Match] = []
    start = 0
    while start < len(units) and len(out) < limit:
        matched_here = None
        for begin in range(start, len(units)):
            slots: dict[str, Unit] = {}
            consumed: list[int] = []
            end = _try_match_at(units, begin, tokens, reg, slots, consumed)
            if end is not None:
                matched_here = (
                    Match(rule=None, slots=slots, consumed=tuple(consumed)),
                    end,
                    begin,
                )  # type: ignore[arg-type]
                break
        if matched_here is None:
            break
        out.append(matched_here[0])
        if overlapping:
            # `begin` may point at a skippable article immediately before the
            # first consumed unit. Advance from the ACTUAL match start or the
            # same semantic window is rediscovered once through the article
            # and once through its head.
            actual_start = min(unit_index[uid] for uid in matched_here[0].consumed)
            start = actual_start + 1
        else:
            start = matched_here[1]
    return out


def _check_where(
    rule: PatternRule | AskRule,
    slots: dict[str, Unit],
    reading: Reading,
    reg: Registry,
) -> bool:
    for pred in rule.where:
        if pred.same_lemma is not None:
            # span slots (tuple-valued) have no single lemma; they cannot
            # participate in where-predicates and are simply skipped
            lemmas = {
                _lemma_of(slots[s])
                for s in pred.same_lemma
                if s in slots and not isinstance(slots[s], tuple)
            }
            if len(lemmas) > 1:
                return False
        if pred.same_surface is not None:
            # Surface agreement is opt-in and stronger than lemma agreement.
            # Every slot must be present and single-unit: an absent optional
            # or a captured span cannot provide repeated-form evidence.
            if any(
                s not in slots or isinstance(slots[s], tuple)
                for s in pred.same_surface
            ):
                return False
            surfaces = {
                slots[s].surface.casefold() for s in pred.same_surface
            }
            if len(surfaces) > 1:
                return False
        if pred.text_prefix_split is not None:
            from .text_evidence import prefix_remainder

            spec = pred.text_prefix_split
            if spec.text not in slots or spec.prefix not in slots:
                return False
            if prefix_remainder(
                _slot_value(slots[spec.text], "written"),
                _slot_value(slots[spec.prefix], spec.prefix_attr),
                spec.layout,
            ) is None:
                return False
        if pred.same_number is not None:
            numbers = []
            for name in pred.same_number:
                unit = slots.get(name)
                if unit is None or isinstance(unit, tuple):
                    return False
                number = unit.features.get("number")
                if unit.features.get("value_kind") == "count":
                    value = unit.features.get("value")
                    if not isinstance(value, (int, float)):
                        return False
                    number = "singular" if float(value) == 1 else "plural"
                if number not in ("singular", "plural"):
                    return False
                numbers.append(number)
            if len(set(numbers)) > 1:
                return False
        if pred.same_category_membership is not None:
            agreement = pred.same_category_membership
            memberships = []
            for name in agreement.slots:
                unit = slots.get(name)
                if unit is None or isinstance(unit, tuple):
                    return False
                memberships.append(
                    _unit_in_category(unit, agreement.cat, reg)
                )
            if len(set(memberships)) > 1:
                return False
        if pred.number_compatible is not None:
            numbers = []
            for name in pred.number_compatible:
                unit = slots.get(name)
                # This predicate rejects an EXPLICIT conflict. An optional
                # slot that is absent contributes no contrary evidence.
                if unit is None:
                    continue
                if isinstance(unit, tuple):
                    return False
                number = unit.features.get("number")
                if unit.sense() in {"auxiliary", "modal"}:
                    lemma = _lemma_of(unit)
                    entry = reg.lexicon.get(lemma)
                    if entry is not None and entry.number is None:
                        # English past do-support and future/conditional
                        # modals are number-neutral. Annotation gives every
                        # standalone lexical unit a fallback number, but that
                        # fallback is not morphological agreement evidence.
                        number = None
                if unit.sense() == "verb":
                    entry = reg.lexicon.get(unit.surface.casefold())
                    if entry is not None and entry.number is None:
                        # Simple-past forms do not inflect for subject number
                        # ("she sold" / "they sold").  The analyzer gives an
                        # otherwise unannotated token a singular fallback, so
                        # only an explicit lexical number feature is genuine
                        # agreement evidence for a verb.
                        number = None
                if unit.features.get("value_kind") == "count":
                    value = unit.features.get("value")
                    if not isinstance(value, (int, float)):
                        return False
                    number = "singular" if float(value) == 1 else "plural"
                if number in ("singular", "plural"):
                    numbers.append(number)
            if len(set(numbers)) > 1:
                return False
        if pred.polarity_compatible is not None:
            polarities = [
                polarity
                for slot_name, category in zip(
                    pred.polarity_compatible.slots,
                    pred.polarity_compatible.categories,
                    strict=True,
                )
                if (
                    unit := slots.get(slot_name)
                ) is not None
                and not isinstance(unit, tuple)
                if (
                    polarity := _scoped_polarity_of(
                        unit, category, reg
                    )
                )
                is not None
            ]
            if len(set(polarities)) > 1:
                return False
        if pred.proportional_delta_compatible is not None:
            compatibility = pred.proportional_delta_compatible
            fraction = slots.get(compatibility.fraction)
            direction = slots.get(compatibility.direction)
            if (
                fraction is None
                or direction is None
                or isinstance(fraction, tuple)
                or isinstance(direction, tuple)
            ):
                return False
            value = fraction.features.get("value")
            polarity = _scoped_polarity_of(
                direction, compatibility.direction_cat, reg
            )
            if not proportional_delta_is_compatible(value, polarity):
                return False
        if pred.same_presence is not None:
            presence = [name in slots for name in pred.same_presence]
            if len(set(presence)) > 1:
                return False
        if pred.mutually_exclusive is not None:
            if sum(name in slots for name in pred.mutually_exclusive) > 1:
                return False
        if pred.verb_role_compatible is not None:
            compatibility = pred.verb_role_compatible
            verb = slots.get(compatibility.verb)
            if verb is None and compatibility.allow_unbound_trigger:
                continue
            if verb is None or isinstance(verb, tuple):
                return False
            if _unit_in_category(verb, compatibility.verb_cat, reg):
                for role_name in compatibility.roles:
                    role = slots.get(role_name)
                    if role is None or isinstance(role, tuple):
                        return False
                    if (
                        compatibility.role_cat is not None
                        and not (
                            _role_is_proper_name(role, reg)
                            or (
                                compatibility.allow_plural_class
                                and role.features.get("number") == "plural"
                            )
                            or _unit_in_category(
                                role, compatibility.role_cat, reg
                            )
                        )
                    ):
                        return False
                    if (
                        compatibility.excluded_role_cat is not None
                        and _unit_in_category(
                            role, compatibility.excluded_role_cat, reg
                        )
                    ):
                        return False
        if pred.verb_roles_compatible is not None:
            compatibility = pred.verb_roles_compatible
            verb = slots.get(compatibility.verb)
            if verb is None and compatibility.allow_unbound_trigger:
                continue
            if verb is None or isinstance(verb, tuple):
                return False
            # The registry already resolves both the surface form and its
            # lemma. Passing only the lemma loses category membership for
            # inflected forms when the bare lemma is intentionally absent
            # (for example ``drops``/``dropped`` in ``drop_quantity_verb``).
            frames = reg.selectional_frames(verb.surface.casefold())
            if compatibility.frame_categories:
                frames = tuple(
                    (category, frame)
                    for category, frame in frames
                    if any(
                        trigger in reg.cat_ancestors(category)
                        for trigger in compatibility.frame_categories
                    )
                )
            # Like the historical conditional predicate, verbs with no
            # declared lexical frame remain open. Once a verb category owns a
            # contract, one complete most-specific frame must accept every
            # mapped role; sibling senses are alternatives, never a mix.
            if not frames and compatibility.require_declared_frame:
                return False
            if frames:
                accepted = False
                for _category, frame in frames:
                    if not set(compatibility.roles) <= set(frame):
                        continue
                    frame_ok = True
                    for semantic_role, role_names in (
                        compatibility.roles.items()
                    ):
                        role_category = frame[semantic_role]
                        role_number = reg.selectional_role_number(
                            _category, semantic_role
                        )
                        for role_name in role_names:
                            role = slots.get(role_name)
                            if role is None or isinstance(role, tuple):
                                frame_ok = False
                                break
                            if (
                                role_number is not None
                                and role.features.get("number") != role_number
                            ):
                                frame_ok = False
                                break
                            if (
                                role_name in compatibility.allow_proper_name
                                and _role_is_proper_name(role, reg)
                            ):
                                continue
                            if (
                                role_name in compatibility.allow_plural_pronoun
                                and role.sense() == "pronoun"
                                and role.features.get("number") == "plural"
                            ):
                                continue
                            if (
                                role_name in compatibility.allow_plural_class
                                and role.features.get("number") == "plural"
                            ):
                                continue
                            if not _unit_in_category(
                                role, role_category, reg
                            ):
                                frame_ok = False
                                break
                        if not frame_ok:
                            break
                    if frame_ok:
                        accepted = True
                        break
                if not accepted:
                    return False
        if pred.measure_holder_compatible is not None:
            compatibility = pred.measure_holder_compatible
            measure = slots.get(compatibility.measure)
            if measure is None or isinstance(measure, tuple):
                return False
            measure_lemma = _lemma_of(measure)
            attribute = (
                slots.get(compatibility.attribute)
                if compatibility.attribute is not None
                else None
            )
            if attribute is not None and isinstance(attribute, tuple):
                return False
            attribute_lemma = (
                _lemma_of(attribute) if attribute is not None else None
            )
            if (
                compatibility.when_declared
                and not reg.measure_has_holder_boundary(measure_lemma)
            ):
                continue
            for holder_name in compatibility.holders:
                holder = slots.get(holder_name)
                if holder is None or isinstance(holder, tuple):
                    return False
                if (
                    compatibility.allow_proper_name
                    and _role_is_proper_name(holder, reg)
                    and (
                        not compatibility.proper_name_measure_categories
                        or any(
                            (
                                attribute_lemma is None
                                and reg.word_in_category(
                                    measure_lemma, category
                                )
                            )
                            or (
                                attribute_lemma is not None
                                and any(
                                    reg.category_routes_overlap(
                                        route_category, category
                                    )
                                    for _, route_category in (
                                        reg.attribute_compatibility_pairs(
                                            attribute_lemma, measure_lemma
                                        )
                                    )
                                )
                            )
                            for category in (
                                compatibility.proper_name_measure_categories
                            )
                        )
                    )
                ):
                    continue
                if not reg.measure_applies_to_holder(
                    measure_lemma,
                    _lemma_of(holder),
                    attribute_lemma,
                ):
                    return False
        if pred.partitive_compatible is not None:
            compatibility = pred.partitive_compatible
            measure = slots.get(compatibility.measure)
            substance = slots.get(compatibility.substance)
            # The predicate may qualify an optional ``of SUBSTANCE`` branch.
            # With no complement there is no partitive claim to validate; once
            # the complement is present, the declared measure/substance pair
            # is mandatory. A missing measure is never optional because it is
            # the head the predicate is anchored to.
            if substance is None:
                continue
            if (
                measure is None
                or isinstance(measure, tuple)
                or isinstance(substance, tuple)
                or not reg.partitive_applies_to(
                    _lemma_of(measure), _lemma_of(substance)
                )
            ):
                return False
        if pred.category_nonoverlap is not None:
            roles = []
            for role_name in pred.category_nonoverlap:
                role = slots.get(role_name)
                if role is None or isinstance(role, tuple):
                    return False
                roles.append(role)
            if any(
                _category_roles_overlap(left, right, reg)
                for index, left in enumerate(roles)
                for right in roles[index + 1:]
            ):
                return False
        if pred.category_contains is not None:
            containment = pred.category_contains
            collection = slots.get(containment.collection)
            members = [slots.get(name) for name in containment.members]
            if (
                collection is None
                or isinstance(collection, tuple)
                or any(
                    member is None or isinstance(member, tuple)
                    for member in members
                )
                or any(
                    not reg.category_term_contains(
                        _lemma_of(collection), _lemma_of(member)
                    )
                    for member in members
                    if member is not None and not isinstance(member, tuple)
                )
            ):
                return False
        if pred.bound_requires_type is not None:
            requirement = pred.bound_requires_type
            if requirement.bound not in slots:
                continue
            unit = slots.get(requirement.slot)
            if unit is None or isinstance(unit, tuple):
                return False
            if not _slot_ok(
                unit,
                MatchToken(slot=requirement.slot, type=requirement.type),
                reg,
            ):
                return False
        if pred.bound_requires_category is not None:
            requirement = pred.bound_requires_category
            if requirement.bound not in slots:
                continue
            if requirement.bound_cat is not None:
                trigger = slots[requirement.bound]
                if isinstance(trigger, tuple):
                    return False
                if not _slot_ok(trigger, MatchToken(slot=requirement.bound, cat=requirement.bound_cat), reg):
                    continue
            unit = slots.get(requirement.slot)
            if unit is None or isinstance(unit, tuple):
                return False
            if not (
                requirement.allow_proper_name
                and _role_is_proper_name(unit, reg)
            ) and not _slot_ok(
                unit,
                MatchToken(slot=requirement.slot, cat=requirement.cat),
                reg,
            ):
                return False
        if pred.bound_rejects_category is not None:
            requirement = pred.bound_rejects_category
            if requirement.bound not in slots:
                continue
            unit = slots.get(requirement.slot)
            if unit is None or isinstance(unit, tuple):
                return False
            if _slot_ok(
                unit,
                MatchToken(slot=requirement.slot, cat=requirement.cat),
                reg,
            ):
                return False
        if pred.category_requires_bound is not None:
            requirement = pred.category_requires_bound
            unit = slots.get(requirement.slot)
            if unit is None or isinstance(unit, tuple):
                return False
            if (
                _slot_ok(
                    unit,
                    MatchToken(slot=requirement.slot, cat=requirement.cat),
                    reg,
                )
                and requirement.bound not in slots
            ):
                return False
        if pred.bound_requires_form is not None:
            requirement = pred.bound_requires_form
            if requirement.bound not in slots:
                continue
            unit = slots.get(requirement.slot)
            if unit is None or isinstance(unit, tuple):
                return False
            fold = unit.features.get("fold") or ""
            lemma = _lemma_of(unit)
            if requirement.form == "bare":
                if not is_bare_verb_form(fold, lemma):
                    return False
            elif not is_finite_verb_form(fold, lemma):
                return False
        if pred.owner_matches is not None:
            relation = pred.owner_matches
            owner = slots.get(relation.owner)
            possessed = slots.get(relation.possessed)
            if (
                owner is None
                or possessed is None
                or isinstance(owner, tuple)
                or isinstance(possessed, tuple)
                or possessed.features.get("owner") != _lemma_of(owner)
            ):
                return False
        if pred.same_phrase is not None:
            # Unlike same_lemma, this predicate is designed for span slots:
            # compare the exact canonical value each slot would emit. Missing
            # optional slots do not create equality evidence, so every named
            # slot must be bound before the predicate can pass.
            if any(s not in slots for s in pred.same_phrase):
                return False
            values = {_slot_value(slots[s], None) for s in pred.same_phrase}
            if len(values) > 1:
                return False
        if pred.distinct is not None:
            # Full role descriptions can distinguish two labelled/owned
            # participants. Missing constraints cannot establish inequality:
            # a bare holder and its possessed description may be the same.
            from itertools import combinations
            from .reference_identity import distinct_references
            values = [
                reference_from_unit(slots[s])
                for s in pred.distinct if s in slots
            ]
            if any(not distinct_references(a, b) for a, b in combinations(values, 2)):
                return False
        if pred.distinct_owner is not None:
            owners = [
                slots[s].features.get("owner")
                for s in pred.distinct_owner
                if s in slots and not isinstance(slots[s], tuple)
            ]
            if (
                len(owners) != len(pred.distinct_owner)
                or any(not owner for owner in owners)
                or len(owners) != len(set(owners))
            ):
                return False
        if pred.distinct_from_owner is not None:
            entity = slots.get(pred.distinct_from_owner.entity)
            possessed = slots.get(pred.distinct_from_owner.possessed)
            if (
                entity is None
                or possessed is None
                or isinstance(entity, tuple)
                or isinstance(possessed, tuple)
                or not possessed.features.get("owner")
                or _lemma_of(entity) == possessed.features.get("owner")
            ):
                return False
        if pred.attribute_compatible is not None:
            attribute_name = pred.attribute_compatible.attribute
            noun_name = pred.attribute_compatible.noun
            attribute = slots.get(attribute_name)
            noun = slots.get(noun_name)
            if attribute is None or noun is None:
                # Compatibility asserts a relation only when both roles bind.
                # This covers both a wholly optional adjunct and a rule whose
                # optional explicit noun qualifies a mandatory descriptor.
                continue
            if (
                isinstance(attribute, tuple)
                or isinstance(noun, tuple)
                or not reg.attribute_applies_to(
                    _lemma_of(attribute), _lemma_of(noun)
                )
            ):
                return False
        if pred.modifier_host_compatible is not None:
            modifier_name = pred.modifier_host_compatible.modifier
            host_name = pred.modifier_host_compatible.host
            object_name = pred.modifier_host_compatible.object
            modifier = slots.get(modifier_name)
            host = slots.get(host_name)
            object_ = slots.get(object_name) if object_name is not None else None
            if modifier is None:
                # The modifier may live in an omitted optional branch.
                continue
            if (
                host is None
                or isinstance(modifier, tuple)
                or isinstance(host, tuple)
            ):
                return False
            if object_name is not None and (object_ is None or isinstance(object_, tuple)):
                return False
            nominal_name = pred.modifier_host_compatible.nominal_host
            nominal = slots.get(nominal_name) if nominal_name else None
            if nominal_name is not None and (nominal is None or isinstance(nominal, tuple)):
                return False
            if not reg.modifier_frame_compatible(
                    _lemma_of(modifier),
                    host.surface.casefold() if pred.modifier_host_compatible.host_type == "verb" else _lemma_of(host),
                    _lemma_of(object_) if object_ is not None else None,
                    host_type=pred.modifier_host_compatible.host_type,
                    name_object=object_ is not None and object_.sense() == "name",
                    nominal_host=_lemma_of(nominal) if nominal is not None else None):
                return False
        if pred.adverb_verb_compatible is not None:
            adverb_name = pred.adverb_verb_compatible.adverb
            verb_name = pred.adverb_verb_compatible.verb
            adverb = slots.get(adverb_name)
            verb = slots.get(verb_name)
            if adverb is None:
                # Optional adverb omitted: there is no modifier relation to
                # validate, so the predicate is deliberately neutral.
                continue
            if (
                verb is None
                or isinstance(adverb, tuple)
                or isinstance(verb, tuple)
                or not reg.adverb_applies_to_verb(
                    adverb.surface.casefold(), verb.surface.casefold()
                )
            ):
                return False
        if pred.distinct_measure is not None:
            # mining candidate qualified-measure-keys: the (lemma, label)
            # pair from `distinct` above, PLUS each slot's own `qualifier`
            # feature — "12 more green apples than red apples" shares
            # lemma 'apple' and label None on both sides but carries two
            # DIFFERENT non-null qualifiers ('green' vs 'red'), so this is
            # NOT the self-referential "compares a measure to itself" shape
            # (lemma, label, qualifier) all matching still blocks (a bare,
            # unqualified repeat, or two qualifiers that happen to agree,
            # is genuinely self-referential); only rules that opt into this
            # predicate (instead of plain `distinct`) get the widened
            # comparison — `distinct: [who, std]` elsewhere is untouched.
            values = [
                (
                    _lemma_of(slots[s]),
                    slots[s].features.get("label"),
                    slots[s].features.get("qualifier"),
                )
                for s in pred.distinct_measure if s in slots
            ]
            if len(values) != len(set(values)):
                return False
        if pred.preceding_verb_category is not None:
            spec = pred.preceding_verb_category
            unit = slots.get(spec["slot"])
            if not isinstance(unit, Unit):
                return False
            preceding = reading.units[:reading.units.index(unit)]
            verb = next((u for u in reversed(preceding) if "verb" in u.senses()), None)
            if verb is None or not _unit_in_category(verb, spec["cat"], reg):
                return False
        if pred.slot_not_category is not None:
            # A TIME PERIOD IS NOT A HOLDER. "he made three fewer tables
            # than this month" bound `std` to 'month' and minted a Relation
            # whose standard was a timeperiod, from which the engine then
            # invented a 'carpenter/month' quantity — a category error, not
            # a near-miss. Scoped to the SLOT, so the sentence's own time
            # adverbials are untouched.
            slot_name = pred.slot_not_category["slot"]
            cat = pred.slot_not_category["cat"]
            unit = slots.get(slot_name)
            if unit is not None:
                # Mirror ordinary category-slot matching: a declarative
                # boundary may name either the canonical lemma or an overt
                # inflected form. This remains opt-in to rules that declare
                # `slot_not_category`.
                lemma = unit.features.get("lemma", unit.features.get("fold", ""))
                fold = unit.features.get("fold", "")
                if (
                    reg.word_in_category(lemma, cat)
                    or reg.word_in_category(fold, cat)
                ):
                    return False
        if pred.absent is not None:
            cat = pred.absent["cat"]
            for u in reading.units:
                word = u.features.get("lemma", u.features.get("fold", ""))
                if reg.word_in_category(word, cat):
                    return False
        if pred.name_count is not None:
            exactly = pred.name_count.get("exactly")
            names = {u.features["fold"] for u in reading.units if u.sense() == "name"}
            if exactly is not None and len(names) != exactly:
                return False
        if pred.unbound is not None:
            # mining candidate elided-comparative-standards: a general
            # negative-lookahead mirror (schemas.py's own comment) — these
            # slots are only ever reachable through an OPTIONAL sub-
            # sequence in the rule's own match tokens, so "bound" means
            # that optional continuation actually matched text.
            if any(s in slots for s in pred.unbound):
                return False
    return True


_TEMPLATE = re.compile(r"\{(\w+)(?:\.(\w+))?\}")
_SIGN = re.compile(r"sign\((\w+)\)")


def _naive_singular(word: str) -> str:
    """Naive English plural -> singular, for words the LEXICON CANNOT FOLD.
    Reached only through the opt-in `.singular` template attr, and there only
    for unknown-word folds — a lexicon word's plural already folds to its
    lemma. The rules that opt in are constructions whose GRAMMAR marks the
    position plural (a bare-plural generic subject, a span after plural-
    agreeing 'are'), so the fold is morphology licensed by the construction,
    never a loose match: keys are still materialized at emission and compared
    exactly. 'ss'/short words stay verbatim ('chess', 'gas')."""
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es") and word[-3] in "sxz":
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _canonical_phrase(units: tuple[Unit, ...], singularize_unknown: bool = False) -> str:
    """A span slot's value: per-token lemma normalization ONLY (plurals and
    known inflections fold to their lexicon lemma; unknown words stay
    verbatim), articles/punct dropped because they are already skippable
    senses. NO semantic loosening — 'opera singer' never becomes 'singer';
    a mismatch is a decline, never a guess (the phrase-key discipline,
    model.Atom docstring).

    A MERGED unit (condense.py's compound/attribute passes) renders as its
    full qualified phrase — fold words with the head canonicalized to the
    lemma — never the bare head lemma. The bare-lemma render silently
    re-opened the Fiedler trap the moment a modifier word entered the
    lexicon: with 'czech'/'choral' known, 'Czech choral conductor' condensed
    to ONE unit whose lemma is 'conductor', so "X is a Czech conductor"
    minted atom(x, 'conductor') and confidently answered "Is it true that X
    is a CHORAL conductor?" — the phrase-key discipline held only while the
    modifiers were UNKNOWN words (unmerged, verbatim in the span). Admitting
    a word must never loosen a phrase key."""
    parts = []
    for u in units:
        if u.sense() in SKIPPABLE_SENSES:
            continue
        words = (u.features.get("fold") or "").split()
        lemma = _lemma_of(u)
        rendered = qualified_render(words, lemma)
        if singularize_unknown and not u.senses():
            # only the SENSELESS unknown folds naively — a lexicon word's
            # plural already folded to its lemma above, and a name-sensed
            # unit mid-span ('Knicks players') keeps its surface key
            rendered = " ".join(_naive_singular(w) for w in rendered.split())
        parts.append(rendered)
    return " ".join(parts)


def intersective_split(
    words: list[str], head_lemma: str, reg: Registry
) -> tuple[list[str], list[str]]:
    """THE one definition of the intersectivity contract — learn.py's copular
    fold and the Atom variant emission below both call this, because a
    contract with two copies has already drifted (the _ACCOUNTED_VALUE_KINDS
    lesson).

    `words` is a merged nominal's fold words; returns (intersective, rest)
    where `intersective` are the modifier words in the opt-in
    `intersective_modifier` category (a structural NAME — the members live in
    packs; an empty category means nothing ever splits) and `rest` are the
    remaining modifiers. Dropping a modifier from a predicate, or asserting
    it alone, is sound ONLY for intersective ones: "Czech choral conductor"
    entails "a Czech", but "guard dog" does not entail "a guard" and "former
    president" does not entail "a president" — which is also why callers
    must never emit a bare-head variant unless every modifier was stripped
    as intersective."""
    mods = words[:-1]
    inter = [w for w in mods if reg.word_in_category(w, "intersective_modifier")]
    rest = [w for w in mods if w not in inter]
    return inter, rest


# Relative markers heading a restrictive relative clause inside a predicate
# span ('who'/'that'/'which'). Sense NAMES as kernel structure (the
# SKIPPABLE_SENSES pattern); the words live in the packs.
_RELATIVE_MARKER_SENSES = ("interrogative", "complementizer", "wh_which")


def _enumeration_segments(span: tuple) -> list[tuple]:
    """Split an enumeration span at its list separators — comma punct and
    conjunction-sensed units (', and' yields an empty middle segment, which
    drops). Structural only: senses and the comma, never words."""
    segs: list[tuple] = []
    cur: list = []
    for u in span:
        if u.sense() == "conjunction" or (
            u.sense() == "punct" and u.features.get("fold") == ","
        ):
            if cur:
                segs.append(tuple(cur))
                cur = []
        else:
            cur.append(u)
    if cur:
        segs.append(tuple(cur))
    return [
        s for s in segs
        if any(u.sense() not in SKIPPABLE_SENSES for u in s)
    ]


def _named_enumeration(span: tuple, reg: Registry) -> list[str] | None:
    """Require at least two coordinated names using the shared list grammar."""
    members = _category_enumeration(span, "name", reg)
    return list(members) if members and len(members) >= 2 else None


def _category_enumeration(span, category, reg):
    """An exact singleton or conjunctive list of category-compatible heads."""
    segments = _enumeration_segments(span)
    if not segments:
        return None
    names = []
    for segment in segments:
        content = [u for u in segment if u.sense() not in SKIPPABLE_SENSES]
        if len(content) != 1:
            return None
        unit = content[0]
        if unit.features.get("reference_qualifiers") or "value" in unit.features:
            return None
        if not (unit.sense() == category or reg.word_in_category(_lemma_of(unit), category)):
            return None
        names.append(_lemma_of(unit))
    conjunctions = [i for i, u in enumerate(span) if u.sense() == "conjunction"]
    if any(not reg.word_in_category(span[i].features.get("fold", ""), "holder_list_conjunction")
           for i in conjunctions):
        return None
    if any(u.sense() == "punct" and u.surface != "," for u in span):
        return None
    if len(names) > 1:
        heads = [i for i, u in enumerate(span) if u.sense() not in SKIPPABLE_SENSES and u.sense() != "conjunction"]
        if not conjunctions or not heads[-2] < conjunctions[-1] < heads[-1]:
            return None
    return tuple(names)


# Which fact kinds decompose, and on WHICH field. Only UPWARD-monotone
# positions may ever appear here: Atom.pred (a ground predicate),
# Quantified.pred and Conditional.then_pred (consequents). Quantified.cls and
# Conditional.cls/pred are ANTECEDENTS — downward-monotone; stripping there
# WIDENS the quantification and is unsound everywhere, forever.
_DECOMPOSABLE_FIELDS = {Atom: "pred", Quantified: "pred", Conditional: "then_pred"}


def atom_variants(fact: Fact, emit_fields: dict, slots: dict, reg: Registry) -> list[Fact]:
    """Decomposition of a rule-emitted fact's PREDICATE field —
    intersection-elimination at the predicate's TOP LEVEL only, for the
    upward-monotone positions in _DECOMPOSABLE_FIELDS (Stage 2.4 widened
    this from Atom.pred to Quantified.pred and Conditional.then_pred: "Every
    european is a czech conductor" also quantifies 'conductor' and 'czech',
    and synth-derived atoms inherit the decomposition transitively because
    every variant quantified/conditional instantiates separately).
    POSITIVE-polarity facts only — under negation the consequent position
    flips downward ("no dog is a czech mammal" says nothing about mammals).

    Two constructions decompose (each an entailment English licenses
    structurally):

    - INTERSECTIVE MODIFIERS on the leading nominal (Stage A, category-gated):
      "czech choral conductor who ..." additionally yields the span with the
      gated modifiers stripped, and each stripped modifier as its own
      single-word predicate ("czech" — no tail: the modifier predicates the
      subject directly). No bare-head variant unless every modifier stripped
      as intersective (the 'former president' safety).
    - A RESTRICTIVE RELATIVE CLAUSE immediately after the leading nominal
      (Stage 2.1, structural — no category): a predicate-position relative is
      a restriction, so "conductor who specialized in X" entails "conductor".
      The marker must sit ADJACENT to the lead (unambiguous attachment); a
      deeper marker decomposes nothing. The clause's INTERNAL content is
      irrelevant to the entailment ("who is not a smoker" still restricts),
      and negation cannot occur inside a span anyway (span_blocks).

    Everything else in the span is untouched: stripping inside an ARGUMENT
    position ("specialized in czech music" -> "specialized in music") is not
    structurally provable — predicate positions are not uniformly monotone.
    NEGATIVE atoms never decompose (neg(A and B) licenses neither neg(A) nor
    neg(B)), and quantified cls NEVER strips anywhere (a universal's
    antecedent is downward-monotone; widening it is unsound)."""
    field_name = _DECOMPOSABLE_FIELDS.get(type(fact))
    if field_name is None or getattr(fact, "polarity", None) is not True:
        return []
    raw = emit_fields.get(field_name)
    if not isinstance(raw, str):
        return []
    m = _TEMPLATE.fullmatch(raw.strip())
    # `.singular` is the ONE attr decomposition sees through: it renames the
    # same span's render (unknown plurals folded), so variants must fold the
    # same way or their keys drift from the primary's. Any other attr means
    # the field is not a plain span key — no decomposition.
    if not m or m.group(2) not in (None, "singular"):
        return []
    singularize = m.group(2) == "singular"
    span = slots.get(m.group(1))
    if not isinstance(span, tuple):
        return []
    units = [u for u in span if u.sense() not in SKIPPABLE_SENSES]
    # The lead must head a nominal: a KNOWN noun, or a SENSELESS unknown —
    # the decomposable fields are all copular predicate positions (pred /
    # then_pred), where the construction (copula + article + span) puts a
    # nominal at the lead whether or not the lexicon knows the word ("is an
    # AUTHOR who created X" ⊨ 'author'; the sense gate alone refused every
    # unknown-word lead, so the drop never fired on exactly the items whose
    # keys the lexicon cannot fold). A unit with a DIFFERENT sense (verb,
    # adjective, name) still refuses — only the lexicon's silence defers to
    # the construction's evidence.
    if not units or not (units[0].sense() == "noun" or not units[0].senses()):
        return []
    # Stage 9f: the lead nominal may be an UNMERGED run of noun/senseless
    # units — 'referee observer' stays two units when 'observer' is a word
    # the lexicon doesn't know, so condense never compounds them. The run
    # extends through contiguous noun-or-senseless units; the drop's tail
    # then starts at the first MARKED unit exactly as before. This only
    # ADDS variants: a second nominal unit can never satisfy any of the
    # tail_droppable arms below, so every previously-decomposing span had a
    # one-unit lead and is byte-identical through the single-unit branch.
    lead_end = 1
    while lead_end < len(units) and (
        units[lead_end].sense() == "noun" or not units[lead_end].senses()
    ):
        lead_end += 1
    lead = units[0]
    if lead_end == 1:
        words = (lead.features.get("fold") or "").split()
        lemma = _lemma_of(lead)
        lead_qualified = qualified_render(words, lemma)
        inter, rest = intersective_split(words, lemma, reg) if len(words) > 1 else ([], [])
        stripped_lead = " ".join(rest + [lemma]) if inter else None
    else:
        # a multi-unit run renders like the primary key does (canonical
        # phrase) and keeps NO modifier machinery — the intersective split
        # reads one merged unit's fold words, and an unmerged run has no
        # merged fold to split
        lead_qualified = _canonical_phrase(
            tuple(units[:lead_end]), singularize_unknown=singularize
        )
        inter, rest, stripped_lead = [], [], None
    tail_units = tuple(units[lead_end:])
    tail = _canonical_phrase(tail_units, singularize_unknown=singularize)
    tail_droppable = bool(tail_units) and (
        tail_units[0].sense() in _RELATIVE_MARKER_SENSES
        # Stage 2.2: a PP immediately after the lead nominal is a restrictive
        # modifier — "student at yale" entails "student" — UNLESS the PP
        # contains a QUANTIFIER: "a friend of no one" is not a friend-of
        # anyone ('no' flips the surface restriction into a denial; the
        # quantifier sense is the structural signal for every such flip).
        # Relative clauses need no such guard: "a man who knows every
        # senator" is still a man — the clause's finite verb scopes its own
        # quantifiers; a PP has no verb to scope them.
        or (
            tail_units[0].sense() == "preposition"
            and not any(u.sense() == "quantifier" for u in tail_units)
        )
        # Stage 9d: a REDUCED relative — a participial verb heading the tail
        # ("a van produced by Chevrolet", "a business run and owned by X") is
        # a restrictive postmodifier of the predicate nominal, so the head
        # entailment holds exactly as with an overt marker. Two guards, both
        # structural: (1) a 3sg-FINITE form ('serves') is never a
        # postmodifier — in this position it can only come from a garbled
        # sentence, so the single-s suffix refuses (the 9c fail-closed
        # precedent; real participles end in -ed/-en/-ing or are irregular
        # bare forms like 'run', none of which end in a single 's');
        # (2) the participle is NON-finite, so unlike a marked relative it
        # cannot scope a quantifier in its own clause — the PP quantifier
        # guard applies verbatim ("a van produced by no company").
        # An unknown (senseless) tail lead still refuses: only a lexicon
        # verb is evidence of the construction.
        or (
            tail_units[0].sense() == "verb"
            and not (
                (tail_units[0].features.get("fold") or "").endswith("s")
                and not (tail_units[0].features.get("fold") or "").endswith("ss")
            )
            and not any(u.sense() == "quantifier" for u in tail_units)
        )
    )

    preds: list[str] = []
    if inter:
        preds.append(f"{stripped_lead} {tail}".strip())
        preds.extend(inter)
    if tail_droppable:
        preds.append(lead_qualified)
        if inter:
            preds.append(stripped_lead)
    # Stage 2.3: a TOP-LEVEL conjunctive predicate — exactly [nominal,
    # conjunction, nominal] — asserts BOTH conjuncts ("a singer and an
    # actor" is a singer and is an actor), each with its own intersective
    # variants. Gated on the opt-in `conjunctive_marker` CATEGORY, not the
    # conjunction sense: 'or' ALSO carries the conjunction sense
    # (difg-mined), and a sense gate would split a DISJUNCTION into two
    # asserted disjuncts — a confident-wrong machine
    # (test_disjunction_asserts_neither_side caught it pre-ship). A
    # disjunction asserts NEITHER side; case analysis is Stage 3's
    # machinery, never a split. Longer spans stay whole — a deeper 'and'
    # has ambiguous scope.
    if (
        len(units) == 3
        and units[1].sense() == "conjunction"
        and reg.word_in_category(units[1].features.get("fold", ""), "conjunctive_marker")
        and units[2].sense() == "noun"
    ):
        for side in (units[0], units[2]):
            w = (side.features.get("fold") or "").split()
            lm = _lemma_of(side)
            preds.append(" ".join(w[:-1] + [lm]) if len(w) > 1 else lm)
            if len(w) > 1:
                s_inter, s_rest = intersective_split(w, lm, reg)
                if s_inter:
                    # may be the bare lemma — sound exactly then: every
                    # modifier was stripped as intersective
                    preds.append(" ".join(s_rest + [lm]))
                    preds.extend(s_inter)
    import dataclasses

    seen = {getattr(fact, field_name)}
    prov = Provenance(
        source=f"{fact.provenance.source}/intersective",
        sentence=fact.provenance.sentence,
        assumption=fact.provenance.assumption,
    )
    variants = []
    for p in preds:
        if p and p not in seen:
            seen.add(p)
            variants.append(
                dataclasses.replace(fact, provenance=prov, **{field_name: p})
            )
    return variants


def _slot_value(unit: Unit, attr: str | None) -> str:
    if attr == "uid":
        return str(unit.uid) if isinstance(unit, Unit) else ""
    if attr == "written":
        if isinstance(unit, tuple):
            return Unit(-1, tuple(word for part in unit for word in part.words)).written
        return unit.written
    if attr in ("span_start", "span_end"):
        units = unit if isinstance(unit, tuple) else (unit,)
        if not units:
            return ""
        index = 0 if attr == "span_start" else -1
        span_index = 0 if attr == "span_start" else -1
        return str(units[index].span[span_index])
    if isinstance(unit, tuple):
        # a span slot (MatchToken.span) binds a RUN of units; its rendering
        # is the canonical phrase — `.singular` additionally folds unknown-
        # word plurals (the plural-agreeing-construction attr, see
        # _naive_singular). A ONE-unit capitalized fallback-name span is the
        # same grammatical value as a one-unit slot and must follow that
        # slot's fold below: plural predicate nominals such as `Americans`
        # otherwise remain plural merely because the rule used `span: true`
        # to enforce whole-construction matching. Multi-unit name spans stay
        # untouched. Every other attr renders the plain phrase.
        rendered = _canonical_phrase(unit, singularize_unknown=(attr == "singular"))
        content = tuple(u for u in unit if u.sense() not in SKIPPABLE_SENSES)
        if (
            attr == "singular"
            and len(content) == 1
            and len(content[0].words) == 1
            and content[0].sense() == "name"
        ):
            rendered = " ".join(_naive_singular(w) for w in rendered.split())
        return rendered
    if attr == "singular":
        # a single-unit key in a construction whose grammar marks it PLURAL
        # (a bare-plural generic subject): the lemma render, then the naive
        # fold for a unit the lexicon cannot fold — the senseless unknown
        # and the sentence-initial capitalized unknown senses.py fell back
        # to naming (the universal-bare-plural-name rules' subject; a real
        # name cannot reach these slots — plural copular agreement). A
        # lexicon word keeps its untouched lemma path.
        rendered = _lemma_of(unit)
        if not unit.senses() or unit.sense() == "name":
            rendered = " ".join(_naive_singular(w) for w in rendered.split())
        return rendered
    if attr == "surface":
        return unit.surface
    if attr == "value":
        v = unit.features.get("value")
        return str(v) if v is not None else ""
    if attr == "components":
        # the comma-separated components of a `point`-typed slot (numbers.py
        # _TUPLE) — an ask's `p1: "{p1.components}"` template reads this and the
        # `coordinate` consumer splits it. A tuple has no scalar `value`, so
        # this is the only way to read one.
        return unit.features.get("components", "") or ""
    if attr == "owner_identity":
        owner = reference_from_unit(unit).owner
        return owner.head if owner and owner.resolved and not owner.described else ""
    if attr == "owner":
        # the possessive owner of a `possessed`-typed slot (condense.py
        # merge-possessive) — an ask's `entity_owner: "{who.owner}"`
        # template reads this to retry an owner-qualified entity key when
        # the bare one comes back empty (facts.py's collision-time split).
        return unit.features.get("owner", "") or ""
    if attr == "qualifier":
        # the attributive modifier of a `qualified`-typed slot (condense.py
        # merge-attribute / merge-compound) — an ask's `entity_qualifier:
        # "{who.qualifier}"` template reads this to retry a qualifier-
        # tagged entity key when the bare one comes back empty (facts.py's
        # collision-time split). Increment 34's mirror of `owner`.
        return unit.features.get("qualifier", "") or ""
    if attr == "label":
        # the trailing index label of a noun merged from NOUN + single-
        # capital-letter INDEX (condense.py merge-label) — mining
        # candidate labeled-entity-relations: a relation rule's
        # `subject_label: "{who.label}"` / `standard_label: "{std.label}"`
        # reads this so saturate.py's `_relations_synth` can resolve a
        # labeled standard against the SPECIFIC same-label Quantity
        # instead of an arbitrary same-lemma one. Mirrors `owner`/
        # `qualifier` above, one field over (increment 74's field).
        return unit.features.get("label", "") or ""
    if attr == "number":
        # grammatical number of a pronoun/noun slot ('singular'/'plural') — a
        # combined ask's `subject_number: "{who.number}"` reads this to tell a
        # SINGULAR subject ("how much does HE have total"; one holder IS the
        # answer) from a PLURAL one ("...do THEY have altogether"; one holder
        # means a missed second). A structural feature (senses.py), no lexicon.
        return unit.features.get("number", "") or ""
    if attr == "qualified":
        # the FULL qualified phrase of a (possibly compound) noun: its fold
        # words with the head canonicalized to the lemma ('chocolate dogs' ->
        # 'chocolate dog'); a bare noun falls through to its lemma unchanged.
        # ask/is-membership queries THIS instead of the bare head lemma, so a
        # qualified question can never be satisfied by a bare-head fact —
        # "Rex is a dog" must not answer "Is Rex a CHOCOLATE dog?" (the
        # default `_lemma_of` render collapsed the compound to 'dog' and
        # answered 'yes'; a compound keeps its head's lemma by design, so the
        # collapse is correct for entity gates and loose for membership).
        words = (unit.features.get("fold") or "").split()
        return qualified_render(words, _lemma_of(unit))
    return _lemma_of(unit)


def _polarity_of(unit: Unit, reg: Registry) -> int:
    """sign(<slot>): the polarity of the deepest polarity-carrying category
    containing this word; +1 when none carries one."""
    word = _lemma_of(unit)
    best_depth, best = -1, 1
    for w in (word, unit.features.get("fold", "")):
        for tag in reg.word_categories.get(w, ()):
            chain = reg.cat_ancestors(tag)
            for depth, cat in enumerate(reversed(chain)):
                if cat in reg.category_polarity and depth > best_depth:
                    best_depth, best = depth, reg.category_polarity[cat]
    return best


def _scoped_polarity_of(
    unit: Unit, scope: str, reg: Registry
) -> int | None:
    """Declared polarity below one category scope, or neutral when absent."""

    best_depth, best = -1, None
    for word in (_lemma_of(unit), unit.features.get("fold", "")):
        for tag in reg.word_categories.get(word, ()):
            chain = reg.cat_ancestors(tag)
            if scope not in chain:
                continue
            for depth, category in enumerate(reversed(chain)):
                if (
                    category in reg.category_polarity
                    and depth > best_depth
                ):
                    best_depth = depth
                    best = reg.category_polarity[category]
    return best


def _resolve_field(
    raw: str | float | bool,
    slots: dict[str, Unit],
    reg: Registry,
    numeric: bool,
    log: ArithmeticLog | None,
    rule_id: str,
) -> object:
    if not isinstance(raw, str):
        return raw
    # pure template? ("{who}", "{item.lemma}")
    m = _TEMPLATE.fullmatch(raw.strip())
    if m and not numeric:
        name, attr = m.group(1), m.group(2)
        if name not in slots:
            # An explicitly optional string emission may omit its phrase.
            # Ordinary templates remain strict, so misspelled bindings still
            # fail loudly. This never supplies a missing numeric operand.
            if attr == "optional":
                return ""
            raise EvaluationError(f"rule {rule_id}: emit references unbound slot {name!r}")
        if attr == "members":
            span = slots[name]
            return tuple(_lemma_of(next(u for u in segment if u.sense() not in SKIPPABLE_SENSES))
                         for segment in _enumeration_segments(span))
        return _slot_value(slots[name], attr)
    if not numeric:
        # Embedded placeholders obey the same explicit optionality contract
        # as a standalone placeholder; ordinary missing bindings stay errors.
        return _TEMPLATE.sub(
            lambda mm: str(_resolve_field(mm.group(0), slots, reg, False, log, rule_id)),
            raw,
        )
    # numeric expression: slot names are variables; sign(x) precomputed
    expr = _SIGN.sub(lambda mm: str(_polarity_of(slots[mm.group(1)], reg)), raw)
    expr = _TEMPLATE.sub(lambda mm: mm.group(1), expr)  # allow {n} in expressions too
    env = {
        name: float(u.features["value"])
        for name, u in slots.items()
        if isinstance(u, Unit) and "value" in u.features
    }
    return evaluate(expr, env, log, source=rule_id)


_NUMERIC_FIELDS = {
    "unit_price", "lot_quantity", "per_member", "content_count", "subtotal", "output_value", "population", "boundary_value",
    "group_size",
    "value", "year", "factor", "offset", "fraction", "numerator", "denominator",
    "elapsed",
    "first_fraction", "second_fraction",
    # mining candidate temporal-offset-age-recut: Relation's two new
    # signed-year offset fields (model.py) — a pattern rule emits them as
    # arithmetic expressions over bound slot values ("n", "-n"), the SAME
    # numeric-field discipline `offset` itself already gets, never a
    # template string.
    "subject_offset", "standard_offset",
    # mining candidate percent-change-values: PercentChange's own signed
    # direction, resolved via the SAME `sign(dir)` numeric-expression
    # mechanism the percent-comparative Relation rules already use for
    # `factor` — no rule anywhere else emits a field literally named
    # `sign`, so this addition changes zero existing rule's resolution.
    "sign",
}


def _template_reference(raw, slots):
    if not isinstance(raw, str):
        return None
    matched = _TEMPLATE.fullmatch(raw)
    if matched is None:
        return None
    unit = slots.get(matched.group(1))
    if not isinstance(unit, Unit):
        return None
    reference = reference_from_unit(unit)
    if matched.group(2) == "owner":
        return reference.owner
    return reference if matched.group(2) in (None, "optional") else None


def _build_fact(
    emit_fields: dict, fact_kind: str, slots: dict[str, Unit], reg: Registry,
    provenance: Provenance, log: ArithmeticLog | None, rule_id: str,
    reading=None, temporal_perspective: str | None = None,
) -> Fact:
    cls = _FACT_CLASSES[fact_kind]
    if temporal_perspective is not None:
        perspective = _resolve_field(
            temporal_perspective, slots, reg, False, log, rule_id
        )
        provenance = replace(
            provenance, temporal_perspective=str(perspective)
        )
    kwargs = {}
    for key, raw in emit_fields.items():
        # Quantity is numeric for a priced expenditure, but names a dimension
        # in other fact contracts (for example physics).
        numeric = key in _NUMERIC_FIELDS or (cls is Expenditure and key == "quantity")
        kwargs[key] = _resolve_field(raw, slots, reg, numeric, log, rule_id)
    if cls in (Expenditure, AccountEntry, BatchEvidence, SpecificationEvidence, PopulationEvidence, RegionEvidence):
        # Source positions are identifiers, not arithmetic operands.
        for key in ("position", "event", "lot_position", "quantity_position", "cost_factor_position"):
            if key in kwargs:
                kwargs[key] = int(kwargs[key])
    for item in fields(cls):
        role = item.metadata.get("reference_for")
        reference = _template_reference(emit_fields.get(role), slots) if role else None
        if reference is not None:
            kwargs[item.name] = reference
        qualifier_role = item.metadata.get("qualifier_for")
        if qualifier_role and emit_fields.get(item.name) is None:
            raw = emit_fields.get(qualifier_role)
            binding = _TEMPLATE.fullmatch(raw) if isinstance(raw, str) else None
            unit = slots.get(binding.group(1)) if binding and binding.group(2) is None else None
            if isinstance(unit, Unit) and unit.features.get("qualifier") is not None:
                kwargs[item.name] = unit.features["qualifier"]
    _indef_field = {Atom: "pred", VerbalRelation: "obj"}.get(cls)
    if _indef_field is not None and "indef_obj" not in kwargs:
        # composition-design.md Phase 0: record whether the pred/obj span
        # swallowed an INDEFINITE article (skippable, so it drops out of the
        # phrase key) — 'plays for a football club' must not later answer
        # "…plays for THE football club?", and an indefinite direct object
        # ("designed a tower") is never a particular referent
        # (model.Atom.indef_obj / model.VerbalRelation.indef_obj)
        pred_tpl = emit_fields.get(_indef_field)
        if isinstance(pred_tpl, str):
            kwargs["indef_obj"] = any(
                span_swallowed_indefinite(slots[mm.group(1)], reading, reg)
                for mm in _TEMPLATE.finditer(pred_tpl)
                if isinstance(slots.get(mm.group(1)), tuple)
            )
    if cls in (Quantity, FractionQuantity, RestQuantity) and "occurrence" not in kwargs:
        # a rule-emitted quantity is an event unless its verb is stative
        verb = kwargs.get("verb", "have")
        if not reg.word_in_category(verb, "state") and verb not in ("have", "be"):
            kwargs["occurrence"] = provenance.sentence
    elif cls in (
        PercentChange,
        SpatialPlacement,
        MeasuredContentChange,
        TotalityTransfer,
        TotalityEvent,
        BoundedActivityInquiry,
    ) and "occurrence" not in kwargs:
        # These are ALWAYS events (never states, unlike Quantity/
        # FractionQuantity/RestQuantity above, which branch on verb
        # category). Their occurrence is the narration coordinate that keeps
        # repeated changes distinct and lets consumers apply them in order.
        kwargs["occurrence"] = provenance.sentence
    return cls(provenance=provenance, **kwargs)


def rule_specificity(rule: PatternRule, reg: Registry) -> tuple[int, int, int]:
    """(required tokens, Σ category gate DEPTHS, where-count). Computed,
    never authored — a narrower category (pet ⊂ animal) scores strictly
    higher, which is what makes narrowing the conflict lever.

    A `lit` ALTERNATION counts as ONE required token and contributes ZERO gate
    depth — the same as the scalar literal it replaces. That is deliberate, not
    an oversight: it makes collapsing N sibling rules into one alternation
    rank-identical to whichever sibling would have fired, so the collapse is a
    provable no-op rather than a behaviour change wearing a refactor's clothes.
    Do not "fix" this without re-gating every collapsed family."""
    gate_depth = 0
    required = 0
    for seq in rule.match.values():
        flat = seq if seq and not isinstance(seq[0], list) else [t for s in seq for t in s]
        for tok in flat:
            if getattr(tok, "opt", None) is not None:
                continue
            required += 1
            cat = getattr(tok, "cat", None)
            if cat:
                gate_depth += len(reg.cat_ancestors(cat)) if cat in reg.category_parents else 1
    return (required, gate_depth, len(rule.where))


def specificity(match: Match, reg: Registry) -> tuple[int, int, int]:
    key = rule_specificity(match.rule, reg)
    return (len(match.consumed), key[1], key[2])


def subsumes(a: Match, b: Match, reg: Registry) -> bool:
    """a strictly subsumes b: a consumed a superset of b's units and is
    strictly more specific — the narrow rule silently wins."""
    if b.rule.overlapping:
        # An opt-in overlapping rule declares a LOCAL edge/window that must
        # coexist with an enclosing construction match. Dropping it because a
        # whole-clause rule consumed a superset would defeat the only purpose
        # of overlapping matching.
        return False
    return set(a.consumed) >= set(b.consumed) and specificity(a, reg) > specificity(b, reg)


def run_rules(
    reading: Reading,
    reg: Registry,
    phase: str,
    log: ArithmeticLog | None = None,
    is_question: bool = False,
) -> list[RuleMatchResult]:
    """Match ALL rules of the phase against the sentence; no short-circuit."""
    results: list[RuleMatchResult] = []
    sentence_folds = {u.features.get("fold") for u in reading.units}
    for rule in reg.rules:  # sorted by id at compile — deterministic
        if rule.phase != phase:
            continue
        key = "question" if is_question else "sentence"
        seq = rule.match.get(key) or rule.match.get("sentence")
        if seq is None or (seq and isinstance(seq[0], list)):
            continue  # multi-sentence rules handled at document level
        # Trigger prefilter: every literal token must be satisfiable, i.e. at
        # least ONE of its options is present. With alternations this stops
        # being a flat set-subset test and becomes a conjunction of
        # DISJUNCTIONS — getting it backwards drops rules silently (no error,
        # just declines), which is why it has its own test.
        if any(
            not (set(t.lit_options) & sentence_folds)
            for t in seq
            if t.lit is not None
        ):
            continue
        for m in match_all(reading, seq, reg, overlapping=rule.overlapping):
            m.rule = rule
            m.specificity = specificity(m, reg)
            effective_slots = project_references(rule.references, m.slots, reg)
            if effective_slots is None or not _check_where(rule, effective_slots, reading, reg):
                continue
            provenance = Provenance(
                source=rule.id,
                sentence=reading.sentence_index,
                assumption=reading.assumption,
            )
            facts = []
            for e in rule.emits:
                emit_provenance = replace(
                    provenance,
                    distributive=e.distributive,
                    container_count=e.container_count,
                )
                if e.options_from is not None:
                    # Stage 9h: whole-list emission (schemas.FactEmit
                    # .options_from) — ONE EnumeratedDisjunction over every
                    # enumeration segment, minted ONLY when the stated
                    # count equals the segment count: exhaustiveness is
                    # what the numeral licenses ("There are SIX types …:"
                    # + six listed = the list is the whole class), and a
                    # mismatched or countless enumeration emits nothing
                    # (fail closed — a partial list claims nothing).
                    # Options render exactly like the sibling per-item
                    # emit's {item.singular} so the keys join.
                    span = m.slots.get(e.options_from)
                    if not isinstance(span, tuple):
                        continue
                    options = tuple(
                        _canonical_phrase(seg, singularize_unknown=True)
                        for seg in _enumeration_segments(span)
                    )
                    count_raw = _resolve_field(
                        e.fields.get("count", ""), effective_slots, reg, False,
                        log, rule.id,
                    )
                    try:
                        count = int(float(count_raw))
                    except (TypeError, ValueError):
                        continue
                    if len(options) < 2 or count != len(options):
                        continue
                    cls_key = _resolve_field(
                        e.fields["cls"], effective_slots, reg, False, log, rule.id,
                    )
                    facts.append(EnumeratedDisjunction(
                        provenance=emit_provenance, cls=cls_key, options=options,
                    ))
                    continue
                if e.each is not None:
                    # Stage 9g: one fact per enumeration segment (see
                    # schemas.FactEmit.each). The segment binds as the
                    # reserved `item` slot, rendered like any span. An item
                    # whose NAME contains a conjunction ('Trinidad and
                    # Tobago') would split wrongly — enumeration rules must
                    # match constructions whose items are type names, where
                    # that cannot occur.
                    span = m.slots.get(e.each)
                    if not isinstance(span, tuple):
                        continue
                    for seg in _enumeration_segments(span):
                        sub_slots = dict(effective_slots)
                        sub_slots["item"] = seg
                        fact = _build_fact(
                            e.fields, e.fact, sub_slots, reg, emit_provenance,
                            log, rule.id, reading=reading,
                            temporal_perspective=e.temporal_perspective,
                        )
                        facts.append(fact)
                        facts.extend(atom_variants(fact, e.fields, sub_slots, reg))
                    continue
                fact = _build_fact(
                    e.fields, e.fact, effective_slots, reg, emit_provenance, log, rule.id,
                    reading=reading,
                    temporal_perspective=e.temporal_perspective,
                )
                facts.append(fact)
                # intersective decomposition (atom_variants): a no-op unless
                # the registry declares the opt-in category AND the emitted
                # fact is a positive span-pred Atom — no benchmark pack does
                # either, so every benchmark corpus is byte-identical
                facts.extend(atom_variants(fact, e.fields, effective_slots, reg))
            results.append(RuleMatchResult(match=m, facts=facts))
    return results


def match_ask(
    reading: Reading, reg: Registry, *, store: FactStore | None = None
) -> tuple[AskRule, dict[str, Any], Match] | None:
    """Match question shapes; the MOST SPECIFIC matching ask wins (max
    consumed units — a longer match read more of the question), then Σ CATEGORY
    GATE DEPTH, with id order as the deterministic tie-break. Re-landed alone
    from the reverted increment 8 per docs/negative-results.md.

    The gate-depth term is the same second key `rule_specificity` has always used
    for RULES, brought to asks: a category-gated slot read MORE than a bare typed
    one, so on an equal-length match it is the more specific reading. Without it
    the tie fell to ALPHABETICAL ID ORDER, which encodes nothing — "How many
    inches are in 3 feet?" went to ask/how-many-in-place (which reads "3 feet" as
    a PLACE and declines) purely because 'h' < 'u'. Ties are the only matches
    affected; any match that already won on length still wins.

    A supplied store filters consumers by their typed-evidence prerequisites
    before ranking. Without a store this remains a structural authoring match.
    """
    from .consumers import consumer_applicable

    class AskResolutionMismatch(Exception):
        pass

    def render(raw: str, match: Match) -> str:
        return _TEMPLATE.sub(
            lambda mm: _slot_value(match.slots[mm.group(1)], mm.group(2)), raw
        )

    def resolve_template(raw: str, match: Match) -> str | list[str]:
        whole = _TEMPLATE.fullmatch(raw)
        if whole is not None and whole.group(2) == "name_list":
            span = match.slots.get(whole.group(1))
            if not isinstance(span, tuple):
                raise AskResolutionMismatch
            names = _named_enumeration(span, reg)
            if names is None:
                raise AskResolutionMismatch
            return names
        if whole is not None and whole.group(2) == "group_members":
            unit = match.slots.get(whole.group(1))
            if not isinstance(unit, Unit):
                raise AskResolutionMismatch
            members = unit.features.get("referent_group")
            if (
                not isinstance(members, tuple)
                or not members
                or not all(isinstance(member, str) and member for member in members)
                or (
                    len(members) == 1
                    and not reg.word_in_category(members[0], "persongroup")
                )
            ):
                raise AskResolutionMismatch
            return list(members)
        return render(raw, match)

    def resolve(
        fields: dict[str, str | list[str]], match: Match
    ) -> dict[str, Any]:
        resolved_fields: dict[str, Any] = {}
        for key, raw in fields.items():
            try:
                if isinstance(raw, str):
                    resolved_fields[key] = resolve_template(raw, match)
                else:
                    values = [
                        resolve_template(template, match) for template in raw
                    ]
                    if not all(isinstance(value, str) for value in values):
                        raise AskResolutionMismatch
                    resolved_fields[key] = values
            except KeyError:
                # the template references an OPTIONAL slot that didn't bind
                # ("verb: {verb}" with the opt-group absent) — omit the key
                # and let the consumer's default apply
                continue
        if resolved_fields.get("consumer") in ("single-entity", "single-entity-elided-measure"):
            reference = _template_reference(fields.get("entity"), match.slots)
            if reference is not None:
                resolved_fields["evidence_entity_reference"] = reference.to_dict()
        if resolved_fields.get("consumer") == "mixture-component":
            for role in ("entity", "source"):
                reference = _template_reference(fields.get(role), match.slots)
                if reference is not None:
                    resolved_fields[role + "_reference"] = reference.to_dict()
        return resolved_fields

    best: tuple[AskRule, dict[str, Any], Match] | None = None
    for ask in reg.asks:  # sorted by id — deterministic tie-break
        seq = ask.match["question"]
        m = match_sequence(reading, seq, reg)
        if m is None:
            continue
        # Keep the winning ask attached to the ordinary Match just as premise
        # matching attaches its PatternRule.  Ask-level structural obligation
        # satisfaction uses this shared match contract after discourse binding.
        m.rule = ask  # type: ignore[assignment]
        if not _check_where(ask, m.slots, reading, reg):
            continue
        try:
            if ask.interpretations:
                resolved = {
                    "__clarification__": render(ask.clarification or "", m),
                    "__interpretations__": tuple(
                        {
                            "id": choice.id,
                            "label": render(choice.label, m),
                            "description": render(choice.description, m),
                            "kind": choice.kind,
                            "query": resolve(choice.resolves, m),
                        }
                        for choice in ask.interpretations
                    ),
                }
            else:
                resolved = resolve(ask.resolves, m)
        except AskResolutionMismatch:
            continue
        if store is not None and not consumer_applicable(resolved.get("consumer"), store):
            continue
        if best is None or _ask_rank(m, ask, reg) > _ask_rank(best[2], best[0], reg):
            best = (ask, resolved, m)
    return best


def _ask_rank(m: Match, ask: AskRule, reg: Registry) -> tuple[int, int]:
    """(consumed units, Σ category-gate depth) — see match_ask. Strictly `>`
    keeps id order as the final tie-break, exactly as before."""
    gate_depth = 0
    for tok in ask.match["question"]:
        if getattr(tok, "opt", None) is not None:
            continue
        cat = getattr(tok, "cat", None)
        if cat:
            gate_depth += len(reg.cat_ancestors(cat)) if cat in reg.category_parents else 1
    return (len(m.consumed), gate_depth)
