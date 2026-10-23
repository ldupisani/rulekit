"""Saturation: close the fact store under synthesizer rules, to a fixpoint.

Generality lives here (the #312 lesson): extraction stays tight, derivation
composes. Data synth rules are datalog-ish (unify fact shapes, emit a new
fact); algorithmic synthesizers (affine chains, partitions) are Python
plugins registered in PLUGINS with declared reads/emits.

Monotone by construction: a synthesizer only emits, never retracts, and an
`unless` clause blocks overwriting — so the fixpoint terminates (the store
dedupes; each round must add a fact or we stop). A hard cap backstops it.
"""

from __future__ import annotations
from .reference_identity import ReferenceIdentity, reference_pool, resolve_reference, scope_reference_store

import itertools
from dataclasses import dataclass, replace
from typing import Callable, Protocol

from ..data.registry import Registry
from ..data.schemas import SynthRule
from . import deixis
from .evaluate import ArithmeticLog, EvaluationError, evaluate
from .facts import FactStore
from .text_evidence import text_evidence
from .model import (
    Alias,
    AnchorQuantity,
    Atom,
    BoundedActivityInquiry,
    ClassRefinement,
    CollectionContext,
    Conditional,
    ContainerContent,
    Disjunction,
    EnumeratedDisjunction,
    Fact,
    Goal,
    GroupTotal,
    MeasuredContentChange,
    Membership,
    PartitionAggregateShare,
    PartitionQuantity,
    Predication,
    Price,
    Provenance,
    Quantity,
    Quantified,
    QuantifiedAdjustment,
    QuantifiedQuantity,
    Relation,
    TotalityTransfer,
    TotalityEvent,
    VerbalRelation,
)

# Direct top-level imports (session-4 refactor, step C): these five used to be
# DEFERRED function-local imports of `answer`, working around the import cycle
# that existed while the fold helpers lived inside answer.py. The folds now
# live in `totals` (which imports `answer` one-way, never back), so the
# workaround is gone with the cycle.
from .measures import _resolve_measure, _resolve_measure_against
from .temporal import normalize_perspective, perspectives_match
from .totals import _entity_total, _sign

MAX_ROUNDS = 50

_FIELD_ALIASES = {"entity", "measure", "value", "verb", "subject", "standard",
                  "subject_owner", "standard_owner",
                  "factor", "offset", "part", "whole", "fraction", "member",
                  "collection", "earlier", "later", "polarity", "dobj", "time",
                  "cls", "pred"}


class Synthesizer(Protocol):
    def __call__(self, store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]: ...


def _is_var(v: object) -> bool:
    return isinstance(v, str) and v[:1].isupper() and v.replace("_", "").isalnum()


def _unify_shape(shape_fields: dict, fact: Fact, env: dict) -> dict | None:
    out = dict(env)
    for key, pattern in shape_fields.items():
        if not hasattr(fact, key):
            return None
        actual = getattr(fact, key)
        if _is_var(pattern):
            if pattern in out and out[pattern] != actual:
                return None
            out[pattern] = actual
        elif pattern != actual:
            return None
    return out


def _apply_synth_rule(
    rule: SynthRule, store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    from .patterns import _FACT_CLASSES  # shared fact-kind table

    emitted: list[Fact] = []
    # kinds resolve through the SAME table the emit side uses — the previous
    # lowercased-class-name convention silently matched nothing for any
    # multi-word kind (QuantifiedDisjunction != 'quantified_disjunction'),
    # which read as a clean 0 SOLVED instead of an error
    kind_facts = {
        shape.fact: [
            f for f in store.facts if type(f) is _FACT_CLASSES.get(shape.fact)
        ]
        for shape in itertools.chain(rule.when, rule.unless)
    }
    # join the `when` clauses over all combinations (stores are small)
    envs: list[dict] = [{}]
    for shape in rule.when:
        nxt: list[dict] = []
        for env in envs:
            for fact in kind_facts[shape.fact]:
                unified = _unify_shape(shape.bindings(), fact, env)
                if unified is not None:
                    nxt.append(unified)
        envs = nxt
        if not envs:
            return []
    for env in envs:
        blocked = False
        for shape in rule.unless:
            for fact in kind_facts[shape.fact]:
                if _unify_shape(shape.bindings(), fact, env) is not None:
                    blocked = True
                    break
            if blocked:
                break
        if blocked:
            continue
        for shape in rule.emit:
            cls = _FACT_CLASSES[shape.fact]
            kwargs = {}
            ok = True
            for key, pattern in shape.bindings().items():
                if _is_var(pattern):
                    kwargs[key] = env.get(pattern)
                    if kwargs[key] is None:
                        ok = False
                elif isinstance(pattern, str) and any(op in pattern for op in "+-*/") :
                    # arithmetic over bound numeric variables
                    numeric_env = {k: v for k, v in env.items() if isinstance(v, (int, float))}
                    try:
                        kwargs[key] = evaluate(pattern, numeric_env, log, source=rule.id)
                    except EvaluationError:
                        ok = False
                else:
                    kwargs[key] = pattern
            if ok:
                emitted.append(cls(provenance=Provenance(source=rule.id, sentence=-1), **kwargs))
    return emitted


# -- algorithmic plugins ------------------------------------------------------

# mining candidate anaphoric-multiplier-standards: reserved `Relation.standard`
# sentinels for a DEMONSTRATIVE standard ("twice that much/many/amount/number",
# "3 times that price") — never a real entity lemma (both contain characters
# no tokenizer-produced lemma can), so they can never collide with a genuine
# document entity. Two, not one, so the quantity-anchored and price-anchored
# resolution paths in `_relations_synth` stay structurally disjoint.
_ANAPHOR_QUANTITY_STANDARD = "$anaphor:quantity$"
_ANAPHOR_PRICE_STANDARD = "$anaphor:price$"

# mining candidate elided-comparative-standards: a THIRD reserved sentinel,
# for a comparative whose standard is ELIDED ENTIRELY — no "as Y"/"than Y"
# clause at all ("Boy A holds 7 fish. Boy B has three times as many fish in
# his aquarium.") — never a real entity lemma either, same `$...$` shape as
# the two anaphor sentinels above, so it can never collide with one of them
# or with a genuine document entity. Deliberately its OWN sentinel, not one
# of the two anaphor ones: an anaphor sentinel's standard is a DEMONSTRATIVE
# ("that much") naming no entity AND no measure noun either (the pattern
# rule never states one), so it resolves against the unique prior fact of
# the right KIND document-wide. This sentinel normally carries a real,
# stated `measure` and resolves against the unique OTHER entity already
# holding that SAME measure. The fully elided additive sibling also leaves
# `measure` null; that narrower shape resolves both omissions from the
# unique prior Quantity belonging to another entity.
_ELIDED_STANDARD = "$elided:standard$"

# A goal-relative holding ("half the money she needs") names no independent
# comparison entity. The subject's unique compatible Goal is its standard.
_GOAL_STANDARD = "$goal:subject$"

_ACTIVE_MEASURED_CONTAINER = "$active:measured-container$"


def _measured_container_content_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Resolve elided measured updates into inspectable content events.

    The content amount is intentionally absent.  The source fact may state a
    resulting total or multiplier without stating that substance's own mass.
    An elided container resolves only when one prior aggregate anchor exists.
    """

    del reg, log
    changes = list(store.by_kind(MeasuredContentChange))
    anchors = [change for change in changes if change.operation == "set_total"]
    out: list[Fact] = []
    for change in changes:
        if change.occurrence is None:
            continue
        container = change.container
        if container == _ACTIVE_MEASURED_CONTAINER:
            prior = [
                anchor
                for anchor in anchors
                if anchor.occurrence is not None
                and anchor.occurrence < change.occurrence
            ]
            if len(prior) != 1:
                continue
            container = prior[0].container
        out.append(
            ContainerContent(
                provenance=Provenance(
                    source="synth/measured-container-content",
                    sentence=change.provenance.sentence,
                    assumption=change.provenance.assumption,
                ),
                container=container,
                content=change.content,
                operation=change.operation,
                occurrence=change.occurrence,
            )
        )
    return out


def _goal_relation_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Resolve goal-scoped comparisons against other stated goals.

    A relation headed by a declared ``goal_predicate`` describes target
    quantities, not actual holdings.  It therefore anchors only on the
    standard entity's unique compatible Goal and emits another Goal.  The
    ordinary affine synthesizer explicitly ignores the same relation so a
    current Quantity can never be mistaken for somebody else's target.
    """

    out: list[Fact] = []
    for relation in store.by_kind(Relation):
        if (
            relation.measure is None
            or relation.standard == _GOAL_STANDARD
            or not reg.word_in_category(relation.verb, "goal_predicate")
        ):
            continue
        goals = [
            goal
            for goal in store.by_kind(Goal)
            if goal.entity == relation.standard
            and _resolve_measure_against(
                relation.measure,
                {goal.measure},
                reg,
                journal=log.journal,
            )
            == goal.measure
        ]
        if len(goals) != 1:
            continue
        standard = goals[0]
        value = evaluate(
            f"{relation.factor} * {standard.value} + {relation.offset}",
            {},
            log,
            source=f"goal-relation:{relation.provenance.source}",
        )
        if value < 0:
            continue
        out.append(
            Goal(
                provenance=Provenance(
                    source="synth/goal-relation",
                    sentence=relation.provenance.sentence,
                ),
                entity=relation.subject,
                measure=standard.measure,
                value=value,
                verb=relation.verb,
                target=standard.target,
            )
        )
    return out


def _goal_progress_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Materialize current holdings stated as a fraction of a known goal."""

    out: list[Fact] = []
    for relation in store.by_kind(Relation):
        if relation.standard != _GOAL_STANDARD or relation.measure is None:
            continue
        goals = [
            goal
            for goal in store.by_kind(Goal)
            if goal.entity == relation.subject
            and _resolve_measure_against(
                relation.measure,
                {goal.measure},
                reg,
                journal=log.journal,
            )
            == goal.measure
        ]
        if len(goals) != 1:
            continue
        goal = goals[0]
        if any(
            quantity.entity == relation.subject
            and quantity.measure == goal.measure
            and quantity.is_state
            for quantity in store.by_kind(Quantity)
        ):
            continue
        value = evaluate(
            f"{relation.factor} * {goal.value} + {relation.offset}",
            {},
            log,
            source=f"goal-progress:{relation.provenance.source}",
        )
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/goal-progress",
                    sentence=relation.provenance.sentence,
                ),
                entity=relation.subject,
                measure=goal.measure,
                value=value,
                verb=relation.verb,
            )
        )
    return out


def _relations_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """Resolve Relation facts against known Quantities:
    subject = factor*standard + offset, hop by hop (raw factors visible)."""

    out: list[Fact] = []

    def relation_provenance(rel: Relation, anchor: Quantity) -> Provenance:
        return Provenance(
            source="synth/relation",
            sentence=rel.provenance.sentence,
            temporal_perspective=rel.provenance.temporal_perspective,
            assumption=rel.provenance.assumption or anchor.provenance.assumption,
        )

    def compatible_anchor(rel: Relation, known: Quantity) -> bool:
        required = normalize_perspective(
            rel.provenance.temporal_perspective, reg
        )
        if required is None:
            return True
        return perspectives_match(
            required, known.provenance.temporal_perspective, reg
        )
    # a relation anchors on ANY known quantity of the standard, but only an
    # existing STATE for the subject blocks resolution — the subject's own
    # EVENTS ("John lost 3") accumulate on top of the derived state
    def verb_key(verb: str) -> str:
        # ALL state verbs describe the same holding ("owns 15x as many" +
        # "has 300" must not derive two Loris) — they share one key
        if verb in ("have", "be") or reg.word_in_category(verb, "state"):
            return "have"
        return verb

    quantities: dict[tuple[str, str], Quantity] = {}
    by_verb: set[tuple[str, str, str]] = set()
    # Owner-qualified mirrors of the bare indexes. Quantity keeps its bare
    # entity lemma for compatibility, while `owner` records which possessed
    # instance it denotes. A relation carrying an owner must use this exact
    # index and may never borrow another owner's same-headed noun.
    owned_quantities: dict[tuple[str, str, str], Quantity] = {}
    by_verb_owned: set[tuple[str, str, str, str]] = set()
    # mining candidate labeled-entity-relations: a SECOND, label-keyed index
    # beside the bare-entity ones above — read ONLY when a relation's own
    # `subject_label`/`standard_label` is set (Relation, model.py), never
    # consulted for an ordinary unlabeled relation, so every existing
    # relation's resolution path below is untouched byte-for-byte. Keyed on
    # the entity's BARE lemma (stripped of any `[label]` suffix
    # facts.py's collision-time re-key may already have applied) so a
    # lookup succeeds whether or not the target quantity has collided with
    # a same-lemma sibling yet — `q.label` itself survives that re-key
    # unchanged (facts.py's `replace()` only ever touches `entity`).
    labeled_quantities: dict[tuple[str, str, str], Quantity] = {}
    by_verb_labeled: set[tuple[str, str, str, str]] = set()
    # mining candidate qualified-measure-keys: a THIRD, qualifier-keyed
    # index beside the bare-entity and label ones above — read ONLY when a
    # relation's own `measure_qualifier`/`standard_qualifier` is set, never
    # consulted for an ordinary unqualified relation, so every existing
    # relation's resolution path stays untouched byte-for-byte. Keyed on
    # the entity and the measure's BARE lemma (stripped of any
    # `[qualifier]` suffix facts.py's collision-time re-key may already
    # have applied — the SAME base-lemma stripping `labeled_quantities`
    # above uses for `entity`, one field over for `measure`), so a lookup
    # succeeds whether or not the target quantity has collided with a
    # same-lemma sibling yet.
    qualified_quantities: dict[tuple[str, str, str], Quantity] = {}
    by_verb_qualified: set[tuple[str, str, str, str]] = set()
    # mining candidate qualified-measure-keys: which (entity, base measure)
    # pairs ALREADY have a collision-split `measure[qualifier]` sibling in
    # the store, read by the same-holder subtype branches below to decide
    # whether a NEWLY derived sibling must be emitted PRE-bracketed. A 3+
    # way qualified chain ("12 pink pens" -> derive green -> derive blue")
    # only ever pairwise-collides ONCE: once pink/green have already split
    # to 'pen[pink]'/'pen[green]', a THIRD bare-'pen' fact for blue no
    # longer shares either sibling's key at all and would never collide
    # (and so never split) via facts.py's ordinary same-key admission path
    # — it would silently sit alongside them as an orphan bare-keyed
    # holding, and the fold would answer from ONE sibling instead of all
    # three. Emitting the THIRD-plus sibling already bracketed sidesteps
    # this: it lands with its own distinct key from the start, alongside
    # its already-split siblings, with nothing left to collide over.
    already_split_bases: set[tuple[str, str]] = set()
    for q in store.by_kind(Quantity):
        quantities.setdefault((q.entity, q.measure), q)
        by_verb.add((q.entity, q.measure, verb_key(q.verb)))
        if q.is_state:
            quantities[(q.entity, q.measure)] = q
        if q.owner:
            base_entity = q.entity.split("[", 1)[0]
            owned_quantities.setdefault(
                (base_entity, q.owner, q.measure), q
            )
            by_verb_owned.add(
                (base_entity, q.owner, q.measure, verb_key(q.verb))
            )
            if q.is_state:
                owned_quantities[
                    (base_entity, q.owner, q.measure)
                ] = q
        if q.label:
            base = q.entity.split("[", 1)[0]
            labeled_quantities.setdefault((base, q.measure, q.label), q)
            by_verb_labeled.add((base, q.measure, verb_key(q.verb), q.label))
            if q.is_state:
                labeled_quantities[(base, q.measure, q.label)] = q
        if q.measure_qualifier:
            base_measure = q.measure.split("[", 1)[0]
            qualified_quantities.setdefault((q.entity, base_measure, q.measure_qualifier), q)
            by_verb_qualified.add(
                (q.entity, base_measure, verb_key(q.verb), q.measure_qualifier)
            )
            if q.is_state:
                qualified_quantities[(q.entity, base_measure, q.measure_qualifier)] = q
        if "[" in q.measure:
            already_split_bases.add((q.entity, q.measure.split("[", 1)[0]))

    pool = reference_pool(store)

    def participant_quantities(reference):
        identity = resolve_reference(reference, pool)
        if identity is None:
            return []
        return [q for q in store.by_kind(Quantity)
                if resolve_reference(q.entity_ref, pool) == identity]

    def qualified_lookup(entity, measure, measure_qualifier):
        from .totals import _subtype_quantity
        return _subtype_quantity(store, reg, rel, measure, measure_qualifier, log)

    def anchor_measure(entity, measure, label=None, owner=None, *, reference):
        from .totals import _relation_item_evidence
        projection = _relation_item_evidence(store, rel, reference, measure, reg, log)
        if projection is None:
            return None
        scoped, candidates, resolved_measure = projection
        if len({q.time for q in candidates}) != 1:
            return None
        from .totals import _verb_total, _sign
        # A single explicit non-accumulating property remains the legacy
        # anchor (e.g. a stated physical measurement). Inventory events must
        # instead go through the signed holding fold below.
        if (verb_key(rel.verb) == "have" and len(candidates) == 1
                and not candidates[0].is_state
                and _sign(candidates[0].verb, reg, strict=True) is None):
            return resolved_measure, candidates[0]
        value = (_entity_total(scoped, reg, reference.head, resolved_measure, log)
                 if verb_key(rel.verb) == "have" else
                 _verb_total(scoped, reference.head, resolved_measure, rel.verb, log))
        if value is None:
            return None
        return resolved_measure, replace(candidates[0], value=value)

    def already_known(entity, measure, verb, *, label=None, owner=None, reference=None):
        reference = reference or rel.subject_ref
        return any(q.measure.split("[", 1)[0] == measure
                   and verb_key(q.verb) == verb_key(verb)
                   for q in participant_quantities(reference))

    # mining candidate cross-measure-relation-fixes: subjects that use each
    # STANDARD lemma across every relation in the store — the discriminator
    # the SAME-HOLDER SUBTYPE INVERSE branch (below) needs to tell "Rainwater
    # has 4x goats as cows and 2x goats as CHICKENS" (a subtype comparison —
    # 'chicken' is used as a standard by exactly ONE subject, 'rainwater')
    # apart from "Adam eats 3 more pies than BILL. Sierra eats 2x as many
    # pies as BILL." (an ordinary cross-entity comparison sharing a
    # standard — 'bill' is used as a standard by TWO DIFFERENT subjects,
    # 'adam' AND 'sierra': a genuine third-party holder others compare
    # themselves against is never a same-holder subtype of any ONE of them).
    standard_subjects: dict[str, set[ReferenceIdentity]] = {}
    for r in store.by_kind(Relation):
        standard_subjects.setdefault(r.standard, set()).add(r.subject_ref)

    def is_subtype_standard(rel: Relation) -> bool:
        """True only for a standard that structurally LOOKS like a same-
        holder subtype measure, never a separate (named or labeled)
        holder: lexiconed `noun` sense (a name is never in the lexicon at
        all — constitution rule 1, no word list, this reads the pre-
        existing sense data), carries no label (a labeled standard, "jar
        A", is always a genuine distinguishable holder — mining candidate
        labeled-entity-relations), and is used as a standard by exactly
        ONE subject anywhere in this document (the `standard_subjects`
        discriminator above). Descriptors come from typed references: the
        legacy flat projections may omit a correctly preserved owner/label."""
        return (
            reg.word_in_category(rel.standard, "noun")
            and not rel.subject_ref.label
            and not rel.standard_ref.label
            and not rel.standard_ref.owner
            and len(standard_subjects.get(rel.standard, ())) <= 1
        )

    for rel in store.by_kind(Relation):
        subject_identity = resolve_reference(rel.subject_ref, pool)
        if subject_identity is None:
            continue
        rel = replace(rel, subject_ref=subject_identity)
        # Goal predicates state target quantities. They are resolved only by
        # `_goal_relation_synth`; borrowing a current holding here would turn
        # "Fia needs 5 fewer than Cato" into an assertion about what Fia has.
        if reg.word_in_category(rel.verb, "goal_predicate"):
            continue
        # Goal-relative relations are resolved only by `_goal_progress_synth`.
        # Treating the reserved sentinel as an ordinary entity would let the
        # bidirectional affine solver materialize a fictitious holder named
        # "$goal:subject$" from the derived current quantity.
        if rel.standard == _GOAL_STANDARD:
            continue
        # mining candidate temporal-offset-age-recut: a genuinely SELF-
        # referential relation ("he will be 3 times as old as he was 11
        # years ago" — the SAME entity on both sides at two DIFFERENT time
        # offsets) needs a linear solve this synth does not do — decline
        # rather than guess. No existing rule can construct one (every
        # relation-emitting rule gates `distinct: [who, std]`, which —
        # mining candidate labeled-entity-relations — compares (lemma,
        # label) PAIRS, not bare lemma alone: "Jar B has 12 more than jar
        # A" bare-folds subject=standard='jar' but carries two DIFFERENT
        # labels, and is not self-referential at all). Mirroring that same
        # (lemma, label) comparison here, so this is pure defense-in-depth
        # for the genuine bare-lemma-AND-label match — it changes no
        # existing (labeled or unlabeled) relation's resolution.
        if rel.subject_ref == resolve_reference(rel.standard_ref, pool):
            continue
        if rel.standard in (_ANAPHOR_QUANTITY_STANDARD, _ANAPHOR_PRICE_STANDARD):
            # mining candidate anaphoric-multiplier-standards: "twice that
            # much"/"twice this many"/"3 times that price" — a DEMONSTRATIVE
            # standard names no entity at all (the pattern rule's own
            # `standard` is one of the two reserved sentinels above, never
            # a real lemma), so the entity-anchored `anchor_measure` above
            # can never apply. A SIBLING branch, deliberately never folded
            # into the `rel.measure is None` elided-measure branch below
            # (which recovers a measure from a NAMED standard entity's own
            # holdings — a different antecedent shape entirely): binds
            # instead to the UNIQUE fact of the right kind known from
            # EARLIER sentences document-wide — the same unique-in-play,
            # never-guess discipline every other branch here uses, just
            # scoped to the whole document instead of one entity because
            # there is no entity to scope by. Zero or two-or-more earlier
            # facts of that kind is ambiguous and declines this round: a
            # derived/aggregate antecedent ("twice that number" referring
            # to the SUM of two counts stated separately) leaves TWO prior
            # facts in play, not one, so it correctly declines rather than
            # guessing which one (or that their sum) is meant.
            #
            # deixis.resolve with the CONSTANT metric is exactly the rule these two
            # branches hand-wrote ("the unique prior fact, or decline"): no candidate
            # can strictly dominate another, so two-or-more always declines. 0-diff by
            # construction. The origo carries only a sentence — the store has no spans
            # — and the RECENCY metric this site obviously wants (the docstring above
            # says so: a two-candidate case is genuinely unresolved) is switched on
            # later as its own gated increment, never here.
            if rel.standard == _ANAPHOR_QUANTITY_STANDARD:
                def eligible_quantity_anaphor(q: Quantity) -> bool:
                    return (
                        (
                            rel.anaphor_measure_category is None
                            or reg.word_in_category(
                                q.measure,
                                rel.anaphor_measure_category,
                            )
                        )
                        and (
                            rel.anaphor_verb_category is None
                            or reg.word_in_category(
                                q.verb,
                                rel.anaphor_verb_category,
                            )
                        )
                    )

                anchor = deixis.resolve(
                    [
                        deixis.Referent(
                            dimension=deixis.DISCOURSE,
                            key=f"{q.entity}·{q.measure}",
                            payload=q,
                            sentence=q.provenance.sentence,
                        )
                        for q in store.by_kind(Quantity)
                        if q.provenance.sentence < rel.provenance.sentence
                        and eligible_quantity_anaphor(q)
                    ],
                    deixis.Origo(sentence=rel.provenance.sentence),
                    deixis.constant,
                    dimension=deixis.DISCOURSE,
                    journal=log.journal,
                    source="relation-anaphor-quantity",
                )
                if anchor is not None:
                    anchor_q = anchor.payload
                    if not already_known(
                        rel.subject,
                        anchor_q.measure,
                        rel.verb,
                        label=rel.subject_label,
                        owner=rel.subject_owner,
                    ):
                        value = evaluate(
                            f"{rel.factor} * {anchor_q.value} + {rel.offset}", {}, log,
                            source=f"relation-anaphor:{rel.provenance.source}",
                        )
                        out.append(
                            Quantity(
                                provenance=Provenance(
                                    source="synth/relation", sentence=rel.provenance.sentence
                                ),
                                entity=rel.subject, entity_ref=rel.subject_ref, measure=anchor_q.measure, value=value,
                                verb=rel.verb, label=rel.subject_label or None,
                                owner=rel.subject_owner or None,
                            )
                        )
            else:
                anchor = deixis.resolve(
                    [
                        deixis.Referent(
                            dimension=deixis.DISCOURSE,
                            key=str(p.item),
                            payload=p,
                            sentence=p.provenance.sentence,
                        )
                        for p in store.by_kind(Price)
                        if p.provenance.sentence < rel.provenance.sentence
                    ],
                    deixis.Origo(sentence=rel.provenance.sentence),
                    deixis.constant,
                    dimension=deixis.DISCOURSE,
                    journal=log.journal,
                    source="relation-anaphor-price",
                )
                if anchor is not None:
                    anchor_p = anchor.payload
                    already_priced = any(
                        p.item == rel.subject and p.verb == rel.verb
                        for p in store.by_kind(Price)
                    )
                    if not already_priced:
                        value = evaluate(
                            f"{rel.factor} * {anchor_p.value} + {rel.offset}", {}, log,
                            source=f"relation-anaphor:{rel.provenance.source}",
                        )
                        out.append(
                            Price(
                                provenance=Provenance(
                                    source="synth/relation", sentence=rel.provenance.sentence
                                ),
                                item=rel.subject, value=value, verb=rel.verb,
                            )
                        )
            continue
        if rel.standard == _ELIDED_STANDARD:
            # mining candidate elided-comparative-standards: "Boy A holds 7
            # fish. Boy B has three times as many fish in his aquarium." —
            # the pattern rule's own `standard` is the reserved sentinel
            # above (never a real lemma): the text names no comparison
            # entity at all, so `anchor_measure` can never apply (there is
            # no entity to anchor against). Recover the DISCOURSE
            # antecedent structurally instead: the UNIQUE OTHER entity
            # (never the relation's own subject — a repeated self-mention
            # without a demonstrative is not this shape; see
            # arithmetic/anaphoric-multiplier-standard-* for "twice that
            # many") already holding the SAME stated measure in an EARLIER
            # sentence — the same unique-pool-in-play, never-guess
            # discipline every other branch here uses. A stated measure
            # filters candidates to that same measure. The additive
            # fully-elided sibling carries `measure=None`; there the one
            # winning prior Quantity supplies BOTH its holder and measure.
            # Reuses the `quantities` index built above (state overrides
            # event per entity/measure, exactly like every entity-anchored
            # branch here). Zero or two-or-more candidates is ambiguous and
            # declines this round rather than guessing.
            #
            # "never the relation's own subject" is a PRECISION FILTER, not part of the
            # candidate set — so it is expressed as one. deixis.Filter may only SHRINK a
            # candidate set, so no filter can turn a decline into a commit; and stating
            # it this way is what lets the field view show WHICH candidate it removed
            # and why, instead of silently never mentioning it.
            def not_the_subject(referent, _origo, _subject=rel.subject):
                return referent.payload.entity != _subject

            anchor = deixis.resolve(
                [
                    deixis.Referent(
                        dimension=deixis.DISCOURSE,
                        key=f"{ent}·{meas}",
                        payload=q,
                        sentence=q.provenance.sentence,
                    )
                    for (ent, meas), q in quantities.items()
                    if (rel.measure is None or meas == rel.measure)
                    and q.provenance.sentence < rel.provenance.sentence
                ],
                deixis.Origo(sentence=rel.provenance.sentence),
                deixis.constant,
                filters=[not_the_subject],
                dimension=deixis.DISCOURSE,
                journal=log.journal,
                source="relation-elided-standard",
            )
            if anchor is not None:
                anchor_q = anchor.payload
                resolved_measure = rel.measure or anchor_q.measure
                already = already_known(
                    rel.subject,
                    resolved_measure,
                    rel.verb,
                    label=rel.subject_label,
                    owner=rel.subject_owner,
                )
                if not already:
                    value = evaluate(
                        f"{rel.factor} * {anchor_q.value} + {rel.offset}", {}, log,
                        source=f"relation-elided-standard:{rel.provenance.source}",
                    )
                    if value < 0:
                        continue
                    out.append(
                        Quantity(
                            provenance=Provenance(
                                source="synth/relation", sentence=rel.provenance.sentence
                            ),
                            entity=rel.subject, entity_ref=rel.subject_ref, measure=resolved_measure, value=value,
                            verb=rel.verb, label=rel.subject_label or None,
                            owner=rel.subject_owner or None,
                        )
                    )
            continue
        if rel.measure is None:
            from .totals import _resolve_relation
            recovered = _resolve_relation(store, rel, log)
            if recovered is None:
                continue
            rel = recovered
        # resolution is blocked when the target already has a quantity UNDER
        # THE RELATION'S OWN VERB — "Zig wrote 4× as many" plus "Zig wrote
        # 60" describe the SAME writing (re-deriving doubles it); a lose
        # event on top of a have-relation is a CHANGE and stays allowed
        resolved = anchor_measure(
            rel.standard,
            rel.measure,
            rel.standard_label,
            rel.standard_owner,
            reference=rel.standard_ref,
        )
        if resolved is not None and not compatible_anchor(rel, resolved[1]):
            resolved = None
        if resolved is not None:
            measure, known = resolved
            already = already_known(
                rel.subject,
                measure,
                rel.verb,
                label=rel.subject_label,
                owner=rel.subject_owner,
            )
            if not already:
                # mining candidate temporal-offset-age-recut: general form
                # age(subject)+subject_offset = factor*(age(standard)+
                # standard_offset)+offset, solved for the subject. Every
                # pre-existing relation defaults both offsets to 0.0, so
                # this reduces to EXACTLY the prior `factor*known+offset`
                # arithmetic (adding/subtracting a literal 0.0 changes no
                # float result) — byte-identical output for every relation
                # that predates this mechanism.
                value = evaluate(
                    f"{rel.factor} * ({known.value} + {rel.standard_offset}) "
                    f"+ {rel.offset} - {rel.subject_offset}", {}, log,
                    source=f"relation:{rel.provenance.source}",
                )
                # A resolved relation is still a cardinal Quantity.  A
                # negative result means the premises are inconsistent; it is
                # not a holding the rest of the engine may safely fold.
                if value < 0:
                    continue
                out.append(
                    Quantity(
                        provenance=relation_provenance(rel, known),
                        entity=rel.subject, entity_ref=rel.subject_ref, measure=measure, value=value, verb=rel.verb,
                        label=rel.subject_label or None,
                        owner=rel.subject_owner or None,
                        measure_qualifier=rel.measure_qualifier or None,
                    )
                )
                continue
        # SAME-HOLDER SUBTYPE anchor (mining candidate subtype-total-asks):
        # "Sandro has six times as many daughters as sons" — 'son' is NOT
        # another entity's own holding of 'daughter' (the ENTITY anchor
        # above correctly found nothing), it is a DIFFERENT measure the
        # RELATION'S OWN SUBJECT already holds. Strictly additive: reachable
        # only when the entity anchor above found nothing at all — i.e.
        # exactly the relations that decline today — so no existing
        # entity-anchored relation is ever intercepted here first. Guarded
        # by the SAME by-verb re-derivation block as the entity anchor, and
        # blocks re-deriving the SAME (subject, standard) pair once
        # resolved: the fixpoint driver (saturate()) reruns this synth every
        # round, so a chained standard ("son" -> "daughter" -> ... deriving
        # a third subtype from a second-round Quantity) resolves over
        # successive rounds with no extra loop here, and the by_verb guard
        # (rebuilt from the store each round, monotonically growing) makes a
        # cyclic pair decline rather than diverge: with no base-case
        # Quantity anywhere in the chain, neither side is ever found by
        # this lookup, so nothing is ever emitted for it.
        #
        # `qualified_lookup` (mining candidate qualified-measure-keys),
        # not the bare `quantities.get`, when `rel.standard_qualifier` is
        # set: "Sam has 16 red apples. Sam has 12 more green apples than
        # red apples" bare-folds subject/standard to the SAME lemma
        # 'apple' — the standard must resolve against the SPECIFIC
        # qualified sibling ('apple' tagged 'red'), never an arbitrary
        # same-lemma one. The re-derivation guard mirrors `by_verb_labeled`
        # one field over: a QUALIFIED relation checks the qualifier-keyed
        # index instead of the bare one, so deriving the 'green' sibling
        # is never blocked merely because the (unrelated) 'red' sibling
        # already occupies the same bare key under the same verb — every
        # UNQUALIFIED relation (the overwhelming existing case) keeps the
        # exact original `by_verb` check, byte-identical.
        subtype_known = (
            None
            if rel.subject_ref.owner or rel.standard_ref.owner
            else qualified_lookup(
                rel.subject,
                rel.standard,
                rel.standard_qualifier,
            )
        )
        already_derived = any(
            q.measure.split("[", 1)[0] == rel.measure
            and q.measure_qualifier == (rel.measure_qualifier or None)
            and verb_key(q.verb) == verb_key(rel.verb)
            for q in participant_quantities(rel.subject_ref)
        )
        if (
            subtype_known is not None
            and compatible_anchor(rel, subtype_known)
            and not already_derived
        ):
            # The shared lookup has already folded this exact standard:
            # state plus signed events for holdings, or all matching events
            # for an activity. It selects the item qualifier before folding,
            # so another class cannot inflate this anchor. Mixed-time or
            # unclassified evidence leaves the lookup unresolved.
            anchor_value = subtype_known.value
            value = evaluate(
                f"{rel.factor} * {anchor_value} + {rel.offset}", {}, log,
                source=f"relation-subtype:{rel.provenance.source}",
            )
            if value < 0:
                continue
            # a 3+-way qualified chain (mining candidate qualified-measure-
            # keys): once (subject, measure) already has a collision-split
            # sibling in the store, a bare-keyed emission here would never
            # collide with it (different key entirely) and so would never
            # get bracketed — pre-bracket it instead, landing it alongside
            # its siblings with nothing left to collide over. The first
            # sibling of a pair (no split yet) stays bare, letting facts.py's
            # ordinary same-key admission perform that FIRST split exactly
            # as before this candidate existed.
            derived_measure = (
                f"{rel.measure}[{rel.measure_qualifier}]"
                if rel.measure_qualifier and (rel.subject, rel.measure) in already_split_bases
                else rel.measure
            )
            out.append(
                Quantity(
                    provenance=relation_provenance(rel, subtype_known),
                    entity=rel.subject, entity_ref=rel.subject_ref, measure=derived_measure, value=value, verb=rel.verb,
                    measure_qualifier=rel.measure_qualifier or None,
                    owner=rel.subject_owner or None,
                )
            )
            continue
        if subtype_known is not None:
            # The standard-side quantity already exists.  Once the forward
            # relation has also been materialized, falling through to the
            # inverse branch would restate that same anchor under the
            # relation's verb and make state folds count it twice.
            continue
        # SAME-HOLDER SUBTYPE INVERSE (mining candidate cross-measure-
        # relation-fixes): the mirror of the forward branch just above —
        # "Mr. Rainwater has 9 cows. He has 4 times as many goats as cows
        # and 2 times as many goats as chickens. How many chickens does he
        # have?" The first relation's forward hop derives Rainwater's own
        # 'goat' quantity (36); the SECOND relation states that SAME 'goat'
        # measure again as ITS OWN subject-side quantity, with 'chicken' —
        # a subtype, not another holder — as the (still unknown) standard.
        # subject_known = the RELATION'S OWN measure, already resolved for
        # this SAME subject (by an earlier round's forward hop, or a
        # sibling relation) -> solve standard = (subject − offset) / factor,
        # entity-KEYED ON THE SAME SUBJECT (never a separate holder).
        # `is_subtype_standard` (defined above) is the load-bearing gate:
        # it is what tells this shape apart from an ORDINARY cross-entity
        # relation whose standard just happens to have no known quantity
        # YET either ("Jeff has twice as many marbles as Ann. Jeff has 10
        # marbles.") — there `rel.standard` is a NAME ('ann'), never
        # lexiconed with sense 'noun', so this branch never fires and the
        # EXISTING cross-entity INVERSE branch below (which correctly keys
        # the new Quantity on `rel.standard` as an ENTITY, not a measure)
        # is the only one that ever resolves it. The bare `noun`-sense
        # check ALONE is not enough — some names collide with common-noun
        # homonyms ("Bill" the person / 'bill' the lexiconed noun, "Jar A"
        # / "Jar B" both bare-lemma 'jar') — so `is_subtype_standard` ALSO
        # requires no label on either side (a labeled standard is always a
        # genuine distinguishable holder) and that the standard is used by
        # exactly one subject across every relation in the document (a
        # standard two different subjects both compare themselves against,
        # like 'bill', is a shared THIRD-PARTY holder, never a subtype of
        # either one). Without this gate, this branch would misfire on an
        # ordinary cross-entity relation whose subject-side measure is
        # already known, minting a nonsense Quantity(entity=Jeff,
        # measure='ann', ...) — a measure that is a person's name. Same
        # unique-in-play, never-guess discipline as every other branch
        # here: a zero factor, or a (subject, standard) pair already
        # resolved under this verb, skips rather than re-derives.
        #
        # `qualified_lookup`, not the bare `quantities.get` (mining
        # candidate qualified-measure-keys): when `rel.measure` and
        # `rel.standard` bare-fold to the SAME lemma with two DIFFERENT
        # qualifiers ("50 fewer BASEBALL cards than FOOTBALL cards" —
        # `is_subtype_standard` reads exactly true for this shape, same
        # lemma, no labels, single subject), the bare lookup would happily
        # grab ANY other same-lemma sibling holding this entity has (e.g.
        # an unrelated 'hockey' card count) and treat it as the subject's
        # OWN 'baseball' quantity — a genuine confident-wrong. The
        # qualifier-aware lookup correctly returns None instead (no
        # 'baseball' quantity is actually known), declining this hop
        # exactly like the unqualified branch already declines an
        # unresolvable one. Every UNQUALIFIED relation keeps the exact
        # original bare-lookup result, byte-identical.
        subject_known = qualified_lookup(rel.subject, rel.measure, rel.measure_qualifier)
        already_inverse_derived = any(
            q.measure.split("[", 1)[0] == rel.standard
            and q.measure_qualifier == (rel.standard_qualifier or None)
            and verb_key(q.verb) == verb_key(rel.verb)
            for q in participant_quantities(rel.subject_ref)
        )
        if (
            subject_known is not None
            and compatible_anchor(rel, subject_known)
            and rel.factor != 0
            and is_subtype_standard(rel)
            and not already_inverse_derived
        ):
            value = evaluate(
                f"({subject_known.value} - {rel.offset}) / {rel.factor}", {}, log,
                source=f"relation-subtype-inverse:{rel.provenance.source}",
            )
            derived_standard_measure = (
                f"{rel.standard}[{rel.standard_qualifier}]"
                if rel.standard_qualifier and (rel.subject, rel.standard) in already_split_bases
                else rel.standard
            )
            out.append(
                Quantity(
                    provenance=relation_provenance(rel, subject_known),
                    entity=rel.subject, entity_ref=rel.subject_ref, measure=derived_standard_measure, value=value, verb=rel.verb,
                    measure_qualifier=rel.standard_qualifier or None,
                )
            )
            continue
        # INVERSE: the subject is known, the standard is not — solve
        # standard = (subject − offset) / factor ("If Zig wrote 60, and Zig
        # wrote four times as many as Flo…"). `not is_subtype_standard(rel)`
        # (mining candidate cross-measure-relation-fixes): this branch's
        # own emit keys the new Quantity's ENTITY on `rel.standard` —
        # correct when `rel.standard` is a genuine second holder (a NAME
        # like 'flo', or a LABELED common noun like "Jar A"), but the
        # SAME-HOLDER SUBTYPE INVERSE branch just above is what must claim
        # an unlabeled, singly-referenced noun-sensed standard (e.g.
        # 'chicken') instead: those never reach here anyway once that
        # branch's own condition is satisfied (it `continue`s first), but
        # on a LATER fixpoint round — once its own by_verb guard blocks
        # re-deriving the (subject, standard) pair it already resolved —
        # this branch would otherwise still fire unguarded and mint a
        # second, nonsense Quantity(entity='chicken', measure='goat', ...)
        # (a measure noun standing in as an entity). Sharing the identical
        # `is_subtype_standard` predicate (rather than a separately-tuned
        # condition) is what keeps the two branches mutually exclusive.
        resolved = anchor_measure(
            rel.subject,
            rel.measure,
            rel.subject_label,
            rel.subject_owner,
            reference=rel.subject_ref,
        )
        if (
            resolved is not None
            and compatible_anchor(rel, resolved[1])
            and rel.factor != 0
            and not is_subtype_standard(rel)
        ):
            measure, known = resolved
            already = already_known(
                rel.standard,
                measure,
                rel.verb,
                label=rel.standard_label,
                owner=rel.standard_owner,
                reference=rel.standard_ref,
            )
            if not already:
                # mining candidate temporal-offset-age-recut: the same
                # general equation, solved for the standard — see the
                # forward branch's comment above for the byte-identical-
                # at-zero-offsets argument.
                value = evaluate(
                    f"(({known.value} + {rel.subject_offset}) - {rel.offset}) "
                    f"/ {rel.factor} - {rel.standard_offset}", {}, log,
                    source=f"relation-inverse:{rel.provenance.source}",
                )
                if value < 0:
                    continue
                out.append(
                    Quantity(
                        provenance=relation_provenance(rel, known),
                        entity=rel.standard, entity_ref=rel.standard_ref, measure=measure, value=value, verb=rel.verb,
                        label=rel.standard_label or None,
                        owner=rel.standard_owner or None,
                        measure_qualifier=rel.measure_qualifier or None,
                    )
                )
    return out


def _bare_age_anchor_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """"If Sherry is 25, how old is Randolph?" (mining candidate age-
    equative-recut) — the leading-'if' clause split turns the
    conditional's age statement into an ordinary premise, "Sherry is 25":
    a copula with a BARE stated number and NO measure noun ('years old'
    never appears). learn.py's generic SVO fold has nowhere to put a
    noun-less value, so it falls all the way to a valueless Predication
    (dobj holding the number's own surface/fold, e.g. '25') — an age
    relation chain (times-as-old-as, times-comparative-age-relation,
    anchored-relation-postfix, ...) needs a Quantity to anchor on, not a
    Predication, so this shape left the whole chain unanchored.

    GATED for decline-safety, not merely convenience: fires ONLY when the
    Predication's subject is already the subject or standard of an
    `age_measure`-category Relation ELSEWHERE in the document — a bare
    copula number in a non-age document (no such Relation exists) can
    never become an age, so this can never misfire on an unrelated "if X
    is 5" premise. The measure itself is read off that Relation (never a
    hardcoded 'year' literal — constitution rule 1; `reg.word_in_category`
    against the pack-declared `age_measure` category mirrors `currency`'s
    reference implementation in answer.py). Also declines (never guesses)
    when the dobj doesn't parse as a plain numeral — a word-form number
    ('twenty-five') is a separate, unbuilt reading. Emits the SAME
    Quantity shape arithmetic/stated-age's pattern rule does (an
    age-measure Quantity, no `occurrence` — a state), at the Predication's
    OWN sentence, so guards.py's value-accounting sees the stated number
    as read via the ordinary "a fact from this sentence carries the
    value" path — no accounting change needed."""
    out: list[Fact] = []
    age_relations = [
        r for r in store.by_kind(Relation)
        if reg.word_in_category(r.measure, "age_measure")
    ]
    if not age_relations:
        return out
    entity_measure: dict[str, str] = {}
    for r in age_relations:
        entity_measure.setdefault(r.subject, r.measure)
        entity_measure.setdefault(r.standard, r.measure)
    known = {(q.entity, q.measure) for q in store.by_kind(Quantity)}
    for p in store.by_kind(Predication):
        if p.verb != "be" or not p.polarity or p.dobj is None:
            continue
        measure = entity_measure.get(p.subject)
        if measure is None or (p.subject, measure) in known:
            continue
        try:
            value = float(p.dobj)
        except (TypeError, ValueError):
            continue
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/bare-age-anchor",
                    sentence=p.provenance.sentence,
                    temporal_perspective=p.provenance.temporal_perspective,
                ),
                entity=p.subject, measure=measure, value=value, verb=p.verb,
            )
        )
    return out


def _anchor_quantity_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """Resolve AnchorQuantity's bare-numeral placeholder (mining candidate
    elided-measure-anchors: "Quinn catches twice the amount of frogs as
    Alster WHO CAUGHT 2", "...if Kristen HAS 12?") against the UNIQUE
    measure already in play for that entity — a sibling Relation naming
    the entity as its subject or standard (the relation's OWN stated
    measure, e.g. "twice the amount of FROGS as Alster"), or the entity's
    own other stated Quantity measure. Zero or two-or-more candidates is
    ambiguous and declines this round — never a guess, the SAME
    unique-pool-in-play discipline `_relations_synth` (increment 85)
    already applies to elided-measure RELATIONS.

    A Relation whose OWN measure is itself still an unresolved elided
    sentinel (`rel.measure is None`, increment 85's shape) contributes NO
    candidate — it hasn't been recovered yet either, and guessing off an
    unresolved sibling would compound two guesses into one; it resolves
    on a LATER round with no extra loop here, exactly like
    `_relations_synth`'s own re-run-each-round design (`saturate()` is the
    fixpoint driver for both).

    A target entity that ALREADY holds a Quantity under the anchor's OWN
    verb blocks re-deriving (the same re-derivation guard `_relations_
    synth` applies) — re-deriving a known holding would double it."""
    out: list[Fact] = []
    resolved = {
        (q.entity, q.verb, q.occurrence, q.time)
        for q in store.by_kind(Quantity)
        if q.provenance.source == "synth/anchor-quantity"
    }
    measures_by_entity: dict[str, set[str]] = {}
    for q in store.by_kind(Quantity):
        measures_by_entity.setdefault(q.entity, set()).add(q.measure)
    for rel in store.by_kind(Relation):
        if rel.measure is None:
            continue
        measures_by_entity.setdefault(rel.subject, set()).add(rel.measure)
        measures_by_entity.setdefault(rel.standard, set()).add(rel.measure)
    known_by_verb = {(q.entity, q.measure, q.verb) for q in store.by_kind(Quantity)}
    for anchor in store.by_kind(AnchorQuantity):
        identity = (anchor.entity, anchor.verb, anchor.occurrence, anchor.time)
        if identity in resolved:
            continue
        # A REFERENTIAL origo (the entity), not a positional one, over bare measure
        # strings that carry no coordinates — sorted, so the set's iteration order can
        # never decide the binding. Constant metric => byte-identical to the
        # `len(candidates) != 1` it replaces.
        winner = deixis.resolve(
            [
                deixis.Referent(dimension=deixis.DISCOURSE, key=m)
                for m in sorted(measures_by_entity.get(anchor.entity, set()))
            ],
            deixis.Origo(sentence=anchor.provenance.sentence),
            deixis.constant,
            dimension=deixis.DISCOURSE,
            journal=log.journal,
            source="synth/anchor-quantity",
        )
        if winner is None:
            continue
        measure = winner.key
        if (anchor.entity, measure, anchor.verb) in known_by_verb:
            continue  # already has a quantity under this verb — would double it
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/anchor-quantity",
                    sentence=anchor.provenance.sentence,
                    temporal_perspective=anchor.provenance.temporal_perspective,
                ),
                entity=anchor.entity, measure=measure, value=anchor.value,
                verb=anchor.verb, occurrence=anchor.occurrence, time=anchor.time,
                owner=anchor.owner, qualifier=anchor.qualifier, label=anchor.label,
            )
        )
    return out


def _pool_before(
    store: FactStore, reg: Registry, sentence: int, measure: str,
    log: ArithmeticLog, source: str,
) -> float | None:
    """The definite pool ('the sandwiches') as of a sentence: the signed sum
    of the measure's quantities from EARLIER sentences — states anchor,
    events add/subtract by verb polarity, previously-derived fraction events
    included (so chains sequence). Rest-derived facts are excluded (they'd
    make the rest's own fixpoint unstable). None when nothing is known."""

    prior = [
        q for q in store.by_kind(Quantity)
        if q.measure == measure
        and q.provenance.sentence < sentence
        and q.provenance.source != "synth/rest"
    ]
    if not prior:
        return None
    if len({q.time for q in prior}) > 1:
        return None  # mixed times — time arithmetic is unbuilt
    expr = " ".join(
        f"{'+' if q.is_state or _sign(q.verb, reg) > 0 else '-'} {q.value}"
        for q in prior
    ).lstrip("+ ")
    if expr.startswith("- "):
        expr = "0 " + expr
    return evaluate(expr, {}, log, source=source)


def _fraction_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """'ate half of THE SANDWICHES' — the fraction becomes an event sized
    against the pool as of its sentence. An unknown or non-positive pool
    leaves it unresolved (the guard declines)."""
    from .model import FractionQuantity


    out: list[Fact] = []
    resolved = {
        (q.entity, q.verb, q.occurrence)
        for q in store.by_kind(Quantity)
        if q.provenance.source == "synth/fraction"
    }
    for fq in store.by_kind(FractionQuantity):
        # sequential chains: an earlier unresolved fraction still owes the
        # pool a depletion — resolving out of order would recompute next
        # round and collide with itself
        if any(
            other.provenance.sentence < fq.provenance.sentence
            and (other.entity, other.verb, other.occurrence) not in resolved
            for other in store.by_kind(FractionQuantity)
        ):
            continue
        # "40% of the MONEY" — the pool's measure resolves through the same
        # category machinery as the asks (money → the unique currency in play)
        measure = _resolve_measure(fq.measure, store, reg, journal=log.journal)
        if measure is None:
            continue
        if (not reg.word_in_category(fq.pool_qualifier, "remnant_adj")
                and any(other.provenance.sentence < fq.provenance.sentence
                        and _resolve_measure(other.measure, store, reg) == measure
                        for other in store.by_kind(FractionQuantity))):
            # Two unqualified fractions need not share a changing base.
            # Preserve the unresolved claim rather than silently choosing
            # the depleted pool over the original allocation.
            continue
        base = _pool_before(store, reg, fq.provenance.sentence, measure, log, "synth/fraction")
        if base is None:
            # "half OF IT": the measure word has no facts of its own — the
            # unique-measure principle resolves it when ONE pool is in play
            in_play = deixis.resolve(
                [
                    deixis.Referent(dimension=deixis.DISCOURSE, key=m)
                    for m in sorted({
                        q.measure for q in store.by_kind(Quantity)
                        if q.provenance.sentence < fq.provenance.sentence
                        and q.provenance.source != "synth/rest"
                    })
                ],
                deixis.Origo(sentence=fq.provenance.sentence),
                deixis.constant,
                dimension=deixis.DISCOURSE,
                journal=log.journal,
                source="synth/fraction",
            )
            if in_play is not None:
                measure = in_play.key
                base = _pool_before(
                    store, reg, fq.provenance.sentence, measure, log, "synth/fraction"
                )
        if base is None or base <= 0:
            continue
        value = evaluate(f"{fq.fraction} * {base}", {}, log, source="synth/fraction")
        out.append(
            Quantity(
                provenance=Provenance(source="synth/fraction", sentence=fq.provenance.sentence),
                entity=fq.entity, measure=measure, value=value,
                verb=fq.verb, occurrence=fq.occurrence, time=fq.time,
            )
        )
    return out


def _rest_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """'He picked THE REST' — the pool remainder as of its sentence. Only
    resolves once every earlier FractionQuantity has resolved (a premature
    rest would recompute next round and collide with itself), and only for
    a document with exactly ONE measure in play."""
    from .model import FractionQuantity, RestQuantity

    out: list[Fact] = []
    # THE MOST ORIGO-LESS SITE IN THE TREE, and it is worth naming as such: "the rest"
    # of WHAT is answered by "whatever the document's only measure is" — no sentence
    # filter, no ordering, no reference point whatsoever. Hence the empty Origo(): the
    # field view will show this resolution standing nowhere, which is the truth.
    #
    # Its decline is also the only GLOBAL one: a two-measure document turns _rest_synth
    # off for EVERY RestQuantity in it, not just this one. Preserved exactly.
    winner = deixis.resolve(
        [
            deixis.Referent(dimension=deixis.DISCOURSE, key=m)
            for m in sorted({
                q.measure for q in store.by_kind(Quantity)
                if q.provenance.source != "synth/rest"
            })
        ],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.DISCOURSE,
        journal=log.journal,
        source="synth/rest",
    )
    if winner is None:
        return out
    measure = winner.key
    resolved_fractions = {
        (q.entity, q.verb, q.occurrence)
        for q in store.by_kind(Quantity)
        if q.provenance.source == "synth/fraction"
    }
    for rq in store.by_kind(RestQuantity):
        pending = any(
            fq.provenance.sentence < rq.provenance.sentence
            and (fq.entity, fq.verb, fq.occurrence) not in resolved_fractions
            for fq in store.by_kind(FractionQuantity)
        )
        if pending:
            continue
        # "gave 6 roses to his mother, 9 to his grandmother, 4 to his
        # sister, and he kept the rest" — a coordinated EVENT clause and the
        # 'kept the rest' clause sharing ONE sentence (mining candidate
        # conjoined-event-conjuncts unmasked this: those give-events used to
        # fold-conflict and decline the item outright, hiding this separate
        # gap). `_pool_before` only ever sums STRICTLY EARLIER sentences
        # (the "pools = signed sum of prior-sentence facts" invariant) — it
        # cannot see an event in the REST's own sentence at all, so
        # resolving here would silently return the pool BEFORE the
        # depleting events (a confident wrong, not a remainder). Declining
        # keeps this shape exactly as safe as it already was: same-sentence
        # rest-of-events is a distinct, not-yet-built consumer, not this
        # candidate's job.
        same_sentence_event = any(
            q.provenance.sentence == rq.provenance.sentence
            and q.provenance.source != "synth/rest"
            and not q.is_state
            for q in store.by_kind(Quantity)
        )
        if same_sentence_event:
            continue
        value = _pool_before(store, reg, rq.provenance.sentence, measure, log, "synth/rest")
        if value is None or value < 0:
            continue
        out.append(
            Quantity(
                provenance=Provenance(source="synth/rest", sentence=rq.provenance.sentence),
                entity=rq.entity, measure=measure, value=value,
                verb=rq.verb, occurrence=rq.occurrence, time=rq.time,
            )
        )
    return out


def _partition_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """'Ten of THEM are yellow' — the plural pronoun denotes the unique
    prior collection; resolved by the same unique-pool-in-play principle
    fraction-of-pronoun uses (never document-level pronoun binding, which
    deliberately excludes plural pronouns). Ambiguous or absent context
    (zero or more than one distinct measure known before this sentence)
    leaves it unresolved — the guard declines rather than guess.

    A FRACTIONAL partition ('25% of THEM are red', `is_fraction=True`) is
    resolved the same way, then additionally sized against the resolved
    collection's own total-as-of-this-sentence — exactly the pool
    `synth/fraction-of-pool` uses — before being re-emitted as a real count
    (`is_fraction=False`). An unresolvable total (no or ambiguous prior
    quantity for the measure) leaves it unresolved this round, same as an
    unresolved collection.

    A REST partition ('THE REST are grey', `is_rest=True` — mining
    candidate rest-partitions) resolves its 'rest'/'remainder' placeholder
    collection the same unique-pool-in-play way, but sizing it needs every
    OTHER (non-rest) partition of that same collection to have ALREADY
    resolved to a real count first — otherwise it would under-subtract a
    sibling still owed its share, a confident wrong rather than a decline.
    A `pending` scan gates on that; once clear, the value becomes
    (the collection's own total as of this sentence, via `_pool_before`)
    minus the signed sum of those prior partitions, re-emitted as a real
    count with `is_rest` cleared, in the SAME step as the collection
    resolution (never a separate round) — a two-step resolution would
    re-key the intermediate fact identically to the final one (collection/
    attribute/verb, unchanged by sizing) and collide with it as a
    same-key-different-value conflict.

    Pre-existing bug fixed here (batch 26 free finding #2): once an
    earlier MEMBERSHIP partition resolves, its companion synth
    (`_partition_membership_synth`) emits a Quantity for the named subset
    noun itself ("5 of them are dogs" -> Quantity(measure='dog', ...)) so
    the general entity-less "how many dogs" ask can read it directly. That
    synthesized Quantity used to count as its own candidate collection
    measure here, so a LATER pronoun/remnant in the SAME document ("The
    rest are cats") saw two distinct measures in play (the real collection
    AND the subset noun) and permanently failed to resolve — an unrelated
    synthesized side-effect masquerading as a second collection. Excluded
    below by source, mirroring `_pool_before`'s existing exclusion of
    `synth/rest` for the identical reason: a derived fact must never count
    as evidence for what the document's own collection measure is."""
    out: list[Fact] = []
    known_measures = _known_collection_measures(store)

    def _candidate_measure(sentence: int) -> str | None:
        # "Ten of THEM" — a PLURAL pronoun, deliberately routed around _bind_discourse
        # (which refuses plurals, because group referents are unbuilt) and resolved by
        # unique-pool-in-play instead. This is precisely the site deixis.md phase 5 is
        # aimed at. The old `next(iter(candidates))` was safe ONLY because it was gated
        # on len == 1; deixis.resolve sorts first, so the set's iteration order can
        # never decide a binding even once a real metric lands.
        return _resolve_collection_measure(
            store,
            sentence,
            log,
            source="synth/partition",
        )

    for pq in store.by_kind(PartitionQuantity):
        if pq.collection in known_measures:
            continue  # already names a real measure — nothing to resolve
        measure = _candidate_measure(pq.provenance.sentence)
        if measure is None:
            continue
        if pq.is_rest:
            # A raw premise fact is never retracted, so an already-resolved
            # sibling's UNRESOLVED copy (collection still the placeholder)
            # lives on in the store forever alongside its resolved one —
            # checking "every fact has a resolved collection" would find
            # that stale copy and block forever. Identify siblings by
            # (attribute, verb, sentence) instead and ask whether EACH
            # identity has at least one resolved counterpart (collection
            # == measure), exactly the guard's own resolved-by-shape check.
            sibling_ids = {
                (sib.attribute, sib.verb, sib.provenance.sentence)
                for sib in store.by_kind(PartitionQuantity)
                if not sib.is_rest
                and sib.provenance.sentence < pq.provenance.sentence
                and _candidate_measure(sib.provenance.sentence) == measure
            }
            resolved_ids = {
                (p.attribute, p.verb, p.provenance.sentence)
                for p in store.by_kind(PartitionQuantity)
                if p.collection == measure and not p.is_rest
            }
            if not sibling_ids <= resolved_ids:
                continue
            prior_parts = [
                p for p in store.by_kind(PartitionQuantity)
                if p.collection == measure and not p.is_rest
                and p.provenance.sentence < pq.provenance.sentence
            ]
            if not prior_parts:
                # "the rest" names the EXACT COMPLEMENT of the STATED
                # subsets (the class definition itself) — with none stated,
                # committing the whole collection risks exactly the
                # confident wrong a hidden, non-partition subset (an
                # "equal men and women" algebra split, e.g.) would produce:
                # decline rather than assume "the rest" is everything.
                continue
            total = _pool_before(
                store, reg, pq.provenance.sentence, measure, log, "synth/partition"
            )
            if total is None:
                continue
            parts_expr = " ".join(
                f"{'+' if p.polarity else '-'} {p.value}" for p in prior_parts
            ) or "0"
            value = evaluate(
                f"{total} - ({parts_expr})", {}, log, source="synth/partition"
            )
            if value < 0:
                # an inconsistent premise (siblings sum past the collection
                # total) — same discipline as rest-of-pool: decline rather
                # than commit a nonsensical negative count.
                continue
            out.append(
                PartitionQuantity(
                    provenance=Provenance(
                        source="synth/partition", sentence=pq.provenance.sentence
                    ),
                    collection=measure, attribute=pq.attribute, value=value,
                    verb=pq.verb, polarity=pq.polarity, kind=pq.kind,
                    is_fraction=False, is_rest=False,
                )
            )
            continue
        value = pq.value
        if pq.is_fraction:
            total = _pool_before(
                store, reg, pq.provenance.sentence, measure, log, "synth/partition"
            )
            if total is None or total <= 0:
                continue
            value = evaluate(f"{pq.value} * {total}", {}, log, source="synth/partition")
        out.append(
            PartitionQuantity(
                provenance=Provenance(
                    source="synth/partition", sentence=pq.provenance.sentence
                ),
                collection=measure, attribute=pq.attribute, value=value,
                verb=pq.verb, polarity=pq.polarity, kind=pq.kind,
                is_fraction=False,
            )
        )
    return out


def _base_collection_measure(measure: str) -> str:
    """Return the collection head behind an attribute-qualified key."""

    return measure.split("[", 1)[0]


def _known_collection_measures(store: FactStore) -> set[str]:
    """All explicitly counted or discourse-introduced collection heads."""

    return {
        _base_collection_measure(quantity.measure)
        for quantity in store.by_kind(Quantity)
    } | {
        context.collection for context in store.by_kind(CollectionContext)
    }


def _resolve_collection_measure(
    store: FactStore,
    sentence: int,
    log: ArithmeticLog,
    *,
    source: str,
    declared: str | None = None,
) -> str | None:
    """Resolve one prior collection without inventing a cardinality.

    Existing quantity anchors retain their historical role. A
    :class:`CollectionContext` adds only a measure candidate, allowing a
    plural anaphor to resolve after prose such as ``a pantry with marbles``
    even though the total is not known yet. Zero or several candidates still
    decline through the same discourse-deixis boundary.
    """

    known = _known_collection_measures(store)
    if declared in known:
        return declared
    candidates = {
        _base_collection_measure(quantity.measure)
        for quantity in store.by_kind(Quantity)
        if quantity.provenance.sentence < sentence
        and quantity.provenance.source != "synth/partition-membership"
    } | {
        context.collection
        for context in store.by_kind(CollectionContext)
        if context.provenance.sentence < sentence
    }
    winner = deixis.resolve(
        [
            deixis.Referent(dimension=deixis.DISCOURSE, key=measure)
            for measure in sorted(candidates)
        ],
        deixis.Origo(sentence=sentence),
        deixis.constant,
        dimension=deixis.DISCOURSE,
        journal=log.journal,
        source=source,
    )
    return winner.key if winner is not None else None


def _unqualified_entity(entity: str, owner: str | None) -> str:
    if owner and entity.endswith(f"[{owner}]"):
        return entity[: -(len(owner) + 2)]
    return entity


def _resolve_collection_holder(
    store: FactStore,
    collection: str,
    sentence: int,
    log: ArithmeticLog,
    *,
    source: str,
) -> tuple[str, str | None] | None:
    """Resolve the unique holder/owner identity for one collection."""

    identities = {
        (
            _unqualified_entity(quantity.entity, quantity.owner),
            quantity.owner,
        )
        for quantity in store.by_kind(Quantity)
        if _base_collection_measure(quantity.measure) == collection
        and quantity.provenance.sentence <= sentence
    } | {
        (context.holder, context.holder_owner)
        for context in store.by_kind(CollectionContext)
        if context.collection == collection
        and context.provenance.sentence < sentence
    }
    keyed = {
        f"{holder}\N{UNIT SEPARATOR}{owner or ''}": (holder, owner)
        for holder, owner in identities
    }
    winner = deixis.resolve(
        [
            deixis.Referent(dimension=deixis.PERSON, key=key)
            for key in sorted(keyed)
        ],
        deixis.Origo(sentence=sentence),
        deixis.constant,
        dimension=deixis.PERSON,
        journal=log.journal,
        source=source,
    )
    return keyed[winner.key] if winner is not None else None


def _partition_aggregate_share_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Materialize ``target = fraction * (named sibling A + sibling B)``."""

    out: list[Fact] = []
    for share in store.by_kind(PartitionAggregateShare):
        attributes = {
            share.attribute,
            share.first_attribute,
            share.second_attribute,
        }
        if len(attributes) != 3:
            continue
        collection = _resolve_collection_measure(
            store,
            share.provenance.sentence,
            log,
            source="synth/partition-aggregate-share",
            declared=share.collection,
        )
        if collection is None:
            continue
        by_attribute: dict[str, list[PartitionQuantity]] = {}
        for partition in store.by_kind(PartitionQuantity):
            if (
                partition.collection != collection
                or partition.provenance.sentence >= share.provenance.sentence
                or partition.is_fraction
                or partition.is_rest
                or not partition.polarity
            ):
                continue
            by_attribute.setdefault(partition.attribute, []).append(partition)
        first = by_attribute.get(share.first_attribute, [])
        second = by_attribute.get(share.second_attribute, [])
        if len(first) != 1 or len(second) != 1:
            continue
        value = evaluate(
            "fraction * (first + second)",
            {
                "fraction": share.fraction,
                "first": first[0].value,
                "second": second[0].value,
            },
            log,
            source="synth/partition-aggregate-share",
        )
        if value < 0:
            continue
        out.append(
            PartitionQuantity(
                provenance=Provenance(
                    source="synth/partition-aggregate-share",
                    sentence=share.provenance.sentence,
                ),
                collection=collection,
                attribute=share.attribute,
                value=value,
                verb=share.verb,
            )
        )
    return out


def _partition_attribute_quantity_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Project contextual adjective partitions into qualified quantities.

    A counted collection already has a whole-measure quantity, so projecting
    each of its partitions beside that total would manufacture competing
    part/whole quantities.  This bridge is intentionally limited to the
    explicitly uncounted collections introduced by ``CollectionContext``.
    """

    out: list[Fact] = []
    known_collections = _known_collection_measures(store)
    contextual_collections = {
        context.collection for context in store.by_kind(CollectionContext)
    }
    collections_with_explicit_totals = {
        quantity.measure
        for quantity in store.by_kind(Quantity)
        if "[" not in quantity.measure and quantity.measure_qualifier is None
    }
    for partition in store.by_kind(PartitionQuantity):
        if (
            partition.kind != "adjective"
            or partition.is_fraction
            or partition.is_rest
            or not partition.polarity
            or partition.collection not in known_collections
            or partition.collection not in contextual_collections
            or partition.collection in collections_with_explicit_totals
            or not reg.word_in_category(partition.attribute, "adjective")
        ):
            continue
        identity = _resolve_collection_holder(
            store,
            partition.collection,
            partition.provenance.sentence,
            log,
            source="synth/partition-attribute-quantity",
        )
        if identity is None:
            continue
        holder, owner = identity
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/partition-attribute-quantity",
                    sentence=partition.provenance.sentence,
                ),
                entity=holder,
                owner=owner,
                measure=partition.collection,
                measure_qualifier=partition.attribute,
                value=partition.value,
                verb="have",
            )
        )
    return out


def _resolve_sequential_population(
    store: FactStore,
    reg: Registry,
    sentence: int,
    log: ArithmeticLog,
    source: str,
) -> tuple[str, float] | None:
    """Resolve one earlier collection measure, holder, and finite total."""
    prior = [
        quantity
        for quantity in store.by_kind(Quantity)
        if quantity.provenance.sentence < sentence
        and quantity.provenance.source != "synth/partition-membership"
    ]
    winner = deixis.resolve(
        [
            deixis.Referent(dimension=deixis.DISCOURSE, key=measure)
            for measure in sorted({quantity.measure for quantity in prior})
        ],
        deixis.Origo(sentence=sentence),
        deixis.constant,
        dimension=deixis.DISCOURSE,
        journal=log.journal,
        source=source,
    )
    if winner is None:
        return None
    measure = winner.key
    holders = {
        quantity.entity for quantity in prior if quantity.measure == measure
    }
    if len(holders) != 1:
        return None
    total = _pool_before(store, reg, sentence, measure, log, source)
    if total is None or total <= 0:
        return None
    return measure, total


def _sequential_partition_complement_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Resolve adjacent first-share/rest sentences as a two-way split."""
    from .model import (
        PartitionQuantity,
        SequentialPartitionInitialShare,
        SequentialPartitionRemainder,
    )

    out: list[Fact] = []
    initial_shares = store.by_kind(SequentialPartitionInitialShare)
    for remainder in store.by_kind(SequentialPartitionRemainder):
        candidates = [
            initial
            for initial in initial_shares
            if initial.provenance.sentence == remainder.provenance.sentence - 1
            and initial.verb == remainder.verb
            and initial.first_attribute != remainder.rest_attribute
        ]
        if len(candidates) != 1:
            continue
        initial = candidates[0]
        if not 0.0 <= initial.first_fraction <= 1.0:
            continue
        resolved = _resolve_sequential_population(
            store,
            reg,
            remainder.provenance.sentence,
            log,
            "synth/sequential-partition-complement",
        )
        if resolved is None:
            continue
        measure, total = resolved
        first = evaluate(
            "first_fraction * total",
            {"first_fraction": initial.first_fraction, "total": total},
            log,
            source="synth/sequential-partition-complement",
        )
        rest = evaluate(
            "total - first",
            {"total": total, "first": first},
            log,
            source="synth/sequential-partition-complement",
        )
        for attribute, value in (
            (initial.first_attribute, first),
            (remainder.rest_attribute, rest),
        ):
            out.append(
                PartitionQuantity(
                    provenance=Provenance(
                        source="synth/sequential-partition-complement",
                        sentence=remainder.provenance.sentence,
                        assumption=(
                            initial.provenance.assumption
                            or remainder.provenance.assumption
                        ),
                    ),
                    collection=measure,
                    attribute=attribute,
                    value=value,
                    verb=initial.verb,
                )
            )
    return out


def _sequential_partition_prefix_join_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Join adjacent first-share and remaining-share sentences."""
    from .model import (
        SequentialPartitionInitialShare,
        SequentialPartitionPrefix,
        SequentialPartitionRemainingShare,
    )

    out: list[Fact] = []
    initial_shares = store.by_kind(SequentialPartitionInitialShare)
    for remaining_share in store.by_kind(SequentialPartitionRemainingShare):
        candidates = [
            initial
            for initial in initial_shares
            if initial.provenance.sentence
            == remaining_share.provenance.sentence - 1
            and initial.verb == remaining_share.verb
            and initial.first_attribute != remaining_share.second_attribute
        ]
        if len(candidates) != 1:
            continue
        initial = candidates[0]
        out.append(
            SequentialPartitionPrefix(
                provenance=Provenance(
                    source="synth/sequential-partition-prefix-join",
                    sentence=remaining_share.provenance.sentence,
                    assumption=(
                        initial.provenance.assumption
                        or remaining_share.provenance.assumption
                    ),
                ),
                first_attribute=initial.first_attribute,
                first_fraction=initial.first_fraction,
                second_attribute=remaining_share.second_attribute,
                second_fraction=remaining_share.second_fraction,
                verb=initial.verb,
            )
        )
    return out


def _sequential_partition_join_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Join an allocation prefix to its immediately following rest clause.

    ``The rest`` is discourse-dependent, but this construction has a precise
    local antecedent: the two staged percentages in the previous sentence.
    Requiring exactly one compatible prefix in that sentence prevents an old
    or competing allocation from being selected by recency guesswork.
    """
    from .model import (
        SequentialPartition,
        SequentialPartitionPrefix,
        SequentialPartitionRemainder,
    )

    out: list[Fact] = []
    prefixes = store.by_kind(SequentialPartitionPrefix)
    for remainder in store.by_kind(SequentialPartitionRemainder):
        candidates = [
            prefix
            for prefix in prefixes
            if prefix.provenance.sentence == remainder.provenance.sentence - 1
            and prefix.verb == remainder.verb
            and remainder.rest_attribute
            not in {prefix.first_attribute, prefix.second_attribute}
        ]
        if len(candidates) != 1:
            continue
        prefix = candidates[0]
        out.append(
            SequentialPartition(
                provenance=Provenance(
                    source="synth/sequential-partition-join",
                    sentence=remainder.provenance.sentence,
                    assumption=(
                        prefix.provenance.assumption
                        or remainder.provenance.assumption
                    ),
                ),
                first_attribute=prefix.first_attribute,
                first_fraction=prefix.first_fraction,
                second_attribute=prefix.second_attribute,
                second_fraction=prefix.second_fraction,
                rest_attribute=remainder.rest_attribute,
                verb=prefix.verb,
            )
        )
    return out


def _sequential_partition_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Resolve a complete staged allocation against one prior collection.

    The allocation sentence omits its collection because the preceding
    discourse already stated it. Exactly one prior measure and one holder are
    required; any competing quantity leaves the allocation unresolved. The
    second fraction is sized against the remainder after the first, and the
    third partition receives the exact residual.
    """
    from .model import PartitionQuantity, SequentialPartition

    out: list[Fact] = []
    for allocation in store.by_kind(SequentialPartition):
        if not (
            0.0 <= allocation.first_fraction <= 1.0
            and 0.0 <= allocation.second_fraction <= 1.0
        ):
            continue
        resolved = _resolve_sequential_population(
            store,
            reg,
            allocation.provenance.sentence,
            log,
            "synth/sequential-partition",
        )
        if resolved is None:
            continue
        measure, total = resolved
        first = evaluate(
            "first_fraction * total",
            {
                "first_fraction": allocation.first_fraction,
                "total": total,
            },
            log,
            source="synth/sequential-partition",
        )
        second = evaluate(
            "second_fraction * (total - first)",
            {
                "second_fraction": allocation.second_fraction,
                "total": total,
                "first": first,
            },
            log,
            source="synth/sequential-partition",
        )
        rest = evaluate(
            "total - first - second",
            {"total": total, "first": first, "second": second},
            log,
            source="synth/sequential-partition",
        )
        if rest < 0:
            continue
        for attribute, value in (
            (allocation.first_attribute, first),
            (allocation.second_attribute, second),
            (allocation.rest_attribute, rest),
        ):
            out.append(
                PartitionQuantity(
                    provenance=Provenance(
                        source="synth/sequential-partition",
                        sentence=allocation.provenance.sentence,
                    ),
                    collection=measure,
                    attribute=attribute,
                    value=value,
                    verb=allocation.verb,
                )
            )
    return out


def _partition_membership_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """'8 of THEM are dogs' — once a MEMBERSHIP-kind partition's collection
    pronoun resolves (see `_partition_synth`), its `attribute` names a count
    of a plural common noun, not a modifier. Synthesize a Quantity for that
    noun so the general entity-less "how many NOUN are there" ask answers
    it, with no bespoke consumer. Fires only when the resolved collection's
    measure has EXACTLY one holding entity — an ambiguous holder (e.g. two
    entities both stated to have the collection) declines downstream
    exactly like partition-complement's whole-total check, never guesses.

    A collection counts as "resolved" either via synth/partition (the
    pronoun path) OR because the premise named the collection noun
    directly (the definite-NP partition surface, "8 of the animals are
    dogs"): both cases end with `collection` equal to a real known
    measure, so the gate checks that structural fact rather than the
    provenance tag, extending to the new surface without a per-rule
    special case."""
    from .model import PartitionQuantity

    out: list[Fact] = []
    known_measures = {q.measure for q in store.by_kind(Quantity)}
    for p in store.by_kind(PartitionQuantity):
        if p.kind != "membership" or p.collection not in known_measures:
            continue
        # The only saturate site whose candidates are HOLDERS — a PERSON-shaped question
        # ("who holds the collection?"), with a REFERENTIAL origo (the collection
        # measure). Typing it PERSON is not cosmetic: it is what stops a measure
        # referent ever competing to be a holder.
        winner = deixis.resolve(
            [
                deixis.Referent(dimension=deixis.PERSON, key=e)
                for e in sorted({
                    q.entity for q in store.by_kind(Quantity)
                    if q.measure == p.collection
                })
            ],
            deixis.Origo(sentence=p.provenance.sentence),
            deixis.constant,
            dimension=deixis.PERSON,
            journal=log.journal,
            source="synth/partition-membership",
        )
        if winner is None:
            continue
        holder = winner.key
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/partition-membership", sentence=p.provenance.sentence
                ),
                entity=holder, measure=p.attribute, value=p.value, verb="have",
            )
        )
    return out


def _complement_word(reg: Registry, word: str) -> str | None:
    """The pack-declared COMPLEMENT of a word ('girl' for 'boy'), mining
    candidate complement-labeled-subsets: two singleton categories linked
    by `antonym:` (packs/core-english/categories/core.yaml's structure,
    packs/difg-mined/categories/semantic.yaml's members) — the SAME
    antonym mechanism polarity pairs use (acquire/lose), reused here
    purely structurally (no `polarity` declared for this pair). A category
    with anything other than exactly one member on the antonym side is
    not a clean word-to-word pairing — decline (None) rather than guess
    which member is the intended complement."""
    for cat in reg.word_categories.get(word, ()):
        anto = reg.category_antonyms.get(cat)
        if anto is None:
            continue
        members = reg.category_members.get(anto, ())
        if len(members) == 1:
            return members[0]
    return None


def _partition_complement_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """Complement-labeled subset asks (mining candidate
    complement-labeled-subsets): "This bookshop has 40 books. 25% of them
    are graphic novels. How many are NOT graphic novels?" already answers
    via the `partition-complement` consumer's NEGATION path — but "How
    many TEXTBOOKS are in the bookshop?" (naming the complement by its OWN
    label, never by negating the stated one) has no fact to read, because
    the stated MEMBERSHIP partition only ever names the ONE subset it
    counts. This plugin closes that gap by EMITTING the missing measure
    directly, once a MEMBERSHIP partition ('boy') resolves its collection
    to a real measure with EXACTLY one holder and the asked label ('girl')
    is the PACK-DECLARED complement of the stated one (`_complement_word`
    above) — never an arbitrary unstated sibling noun, which increment
    16's own exhaustive-enumeration refusal still applies to. The declared
    pair is what makes exhaustiveness sound (a complementary pair
    partitions its collection BY DEFINITION), licensed by DATA instead of
    guessed.

    Declines (never fires) whenever: the partition is fractional/rest-
    kind/negative-polarity (only a plain stated MEMBERSHIP cardinal
    anchors a complement — those forms resolve to one here in a LATER
    round, same fixpoint discipline every other synth plugin uses); more
    than ONE membership partition is stated over the same collection (a
    3-way split is not a complement — a second stated subset makes the
    'exhaustive pair' assumption unsound); the collection's total has
    anything other than exactly one holder (never guess which entity the
    complement belongs to); the collection's own total is unresolvable as
    of the partition's sentence; the resulting count would be negative
    (an inconsistent premise); or the complement measure ALREADY has a
    Quantity of its own (never overwrite or double-emit — decline-safe by
    construction, mirrors every other synth plugin's `known_measures`
    guard)."""
    from .model import PartitionQuantity

    out: list[Fact] = []
    known_measures = {q.measure for q in store.by_kind(Quantity)}
    for p in store.by_kind(PartitionQuantity):
        if (
            p.kind != "membership" or p.is_fraction or p.is_rest
            or not p.polarity or p.collection not in known_measures
        ):
            continue
        complement = _complement_word(reg, p.attribute)
        if complement is None or complement in known_measures:
            continue
        siblings = [
            s for s in store.by_kind(PartitionQuantity)
            if s.collection == p.collection and s.kind == "membership"
            and not s.is_fraction and not s.is_rest
        ]
        if len(siblings) != 1:
            continue  # more than one stated subset — not a clean complement
        holders = {q.entity for q in store.by_kind(Quantity) if q.measure == p.collection}
        if len(holders) != 1:
            continue
        (holder,) = holders
        total = _pool_before(
            store, reg, p.provenance.sentence, p.collection, log,
            "synth/partition-complement",
        )
        if total is None:
            continue
        value = evaluate(
            f"{total} - {p.value}", {}, log, source="synth/partition-complement"
        )
        if value < 0:
            continue  # an inconsistent premise — never commit a negative count
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/partition-complement", sentence=p.provenance.sentence
                ),
                entity=holder, measure=complement, value=value, verb="have",
            )
        )
    return out


def _ratio_split_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """Resolves RatioQuantity facts (mining candidate ratio-split-
    premises): the collection anchor is the UNIQUE Quantity measure known
    as of the ratio fact's own sentence — INCLUSIVE of that same sentence
    (see RatioQuantity's own docstring, model.py, for why this differs
    from `_pool_before`'s strictly-prior convention; `_pool_before`/
    `_partition_synth` stay byte-for-byte untouched by this candidate).

    Two exclusions from the candidate set, both decline-safety, never a
    guess: (a) every measure this very synthesizer has already derived,
    so a SECOND, independent ratio statement later in the same document
    never treats the FIRST one's derived labels as a candidate
    collection (mirrors `_partition_synth`'s own exclusion of its
    `synth/partition-membership` derivations); (b) every label named by
    ANY RatioQuantity in the document — a ratio's own part is a SHARE,
    never the whole, so "There are 30 boys. The ratio of boys to girls is
    3:2." must not treat the already-known 'boy' count as the collection
    total and back out a wrong 'girl' share from it. Declining that shape
    is deliberate; it needs a different anchor (the part's own ratio
    number, not a collection total) that this candidate does not build.

    Fires only once the resolved collection measure has EXACTLY one
    holder (mirrors `_partition_membership_synth`'s own guard) and the
    label itself has no Quantity of its own yet (never overwrite or
    double-emit)."""
    from .model import RatioQuantity

    out: list[Fact] = []
    known_measures = {q.measure for q in store.by_kind(Quantity)}
    ratio_attributes = {rq.attribute for rq in store.by_kind(RatioQuantity)}
    derived = {
        q.measure for q in store.by_kind(Quantity)
        if q.provenance.source == "synth/ratio-split"
    }
    for rq in store.by_kind(RatioQuantity):
        if rq.attribute in known_measures:
            continue  # already has its own Quantity — never overwrite
        candidates = {
            q.measure for q in store.by_kind(Quantity)
            if q.provenance.sentence <= rq.provenance.sentence
            and q.measure not in derived
            and q.measure not in ratio_attributes
        }
        if len(candidates) != 1:
            continue
        (measure,) = candidates
        holders = {q.entity for q in store.by_kind(Quantity) if q.measure == measure}
        if len(holders) != 1:
            continue
        (holder,) = holders
        total = _entity_total(store, reg, holder, measure, log)
        if total is None or total <= 0:
            continue
        value = evaluate(f"{rq.fraction} * {total}", {}, log, source="synth/ratio-split")
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/ratio-split", sentence=rq.provenance.sentence
                ),
                entity=holder, measure=rq.attribute, value=value, verb="have",
            )
        )
    return out


def _sum_constraint_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """sum-constraint linear systems (mining candidate sum-constraint-
    relations): "Anais has 30 more toys than Kamari. There are 160 toys
    altogether." — a Relation (subject = factor*standard + offset) plus a
    GroupTotal over the SAME measure jointly commit to a unique 2x2 linear
    solve neither fact alone determines:

        standard = (T - offset) / (1 + factor)
        subject  = T - standard

    Fires ONLY when exactly one Relation and exactly one compatible GroupTotal
    share a measure.  An unscoped total is compatible, as is a total scoped by
    a plural discourse pronoun (``they``): both can denote the relation's two
    holders.  A named scope is local to that named holder/group and cannot be
    borrowed as the sum of two unrelated relation holders.  NEITHER the
    relation's subject nor its standard may already hold a Quantity of that
    measure (from anywhere — the ordinary
    relation-resolution path, an earlier round of this very plugin, or a
    stated holding): an existing holder means either the ordinary
    arithmetic/relation-to-quantity path already solved it, or a THIRD
    entity is also implicated and this plugin must never guess which
    entities the stated total actually spans. `factor == -1` is the
    degenerate case (the two terms cancel to a constant, not a sum) and
    also declines. A negative solution declines too — never commit a
    physically impossible split.

    Deliberately scoped to exactly TWO holders per total (a three-entity
    chain — two relations plus one total — is a named, separate increment,
    not this one)."""

    out: list[Fact] = []
    totals_by_measure: dict[str, list[GroupTotal]] = {}
    for gt in store.by_kind(GroupTotal):
        totals_by_measure.setdefault(gt.measure, []).append(gt)
    relations_by_measure: dict[str, list[Relation]] = {}
    all_relations = list(store.by_kind(Relation))
    for rel in all_relations:
        relations_by_measure.setdefault(rel.measure, []).append(rel)

    for measure, totals in totals_by_measure.items():
        if len(totals) != 1:
            continue  # more than one stated total for this measure — ambiguous
        (total,) = totals
        # mining candidate sum-constraint-premise-surfaces: an EXACT
        # measure-key match first (unchanged), plus a bridged match via the
        # pre-existing interchangeable-category machinery
        # (_resolve_measure_against, answer.py — the SAME 'money'->'dollar'
        # bridge a bare how-much ask already uses) for a relation whose own
        # measure word is a CURRENCY-CATEGORY generic ("three times as
        # much MONEY as") while the group total states a SPECIFIC bare '$N'
        # denomination ("a combined total of $150" resolves to the DATA
        # measure 'dollar' via senses.py's currency-amount noun reading).
        # Both are always unioned (never short-circuited on the exact
        # match alone) so a genuinely ambiguous pairing — an exact-measure
        # relation AND a separately bridged one both present — still
        # declines via the `len(rels) != 1` check below, exactly like two
        # exact-measure relations already do.
        exact_rels = relations_by_measure.get(measure, [])
        bridged_rels = [
            r for r in all_relations
            if r.measure != measure
            and _resolve_measure_against(r.measure, {measure}, reg, journal=log.journal) == measure
        ]
        rels = exact_rels + bridged_rels
        if len(rels) != 1:
            continue  # more than one relation over this measure — ambiguous
        (rel,) = rels
        # A leading total marker retains its grammatical subject as an exact
        # scope ("Combined John receives 70 apples" -> scope='john').  That
        # 70 is local to John; it is not evidence that Eron + Aven = 70 just
        # because their Relation happens to use the same measure.  Only a
        # genuinely unscoped total or a plural group anaphor can supply the
        # two-holder sum constraint.  Use the pack's existing discourse-group
        # category rather than hard-coding a pronoun list here.
        if total.scope is not None and not reg.word_in_category(
            total.scope, "discourse_referential_group_pronoun"
        ):
            continue
        if rel.subject == rel.standard or rel.factor == -1:
            continue  # self-referential or degenerate (terms cancel, not sum)
        holders = {q.entity for q in store.by_kind(Quantity) if q.measure == measure}
        if holders - {rel.subject, rel.standard}:
            continue  # a third entity holds this measure — never guess the span
        # mining candidate anaphoric-multiplier-standards: a THIRD relation
        # touching either of this relation's two entities is the SAME
        # three-entity-chain case the docstring already declines for
        # (Stacy=4xSteve, Steve=2xSkylar, 1100 total — a chain, not a
        # 2-holder split), but the `holders` check above alone cannot see
        # it: the other relation's OWN measure can still be unresolved
        # (e.g. an anaphoric-standard Relation, `measure is None`, that
        # hasn't recovered its measure yet) and so never lands in this
        # `measure`'s own bucket, leaving the chain invisible to
        # `relations_by_measure`. Checking every OTHER relation's subject/
        # standard directly (regardless of ITS OWN measure) closes that
        # gap without narrowing anything: an ordinary isolated 2-holder
        # relation (the overwhelming common case) has no other relation
        # naming either of its entities, so this adds zero new declines
        # there.
        if any(
            other is not rel and (rel.subject in (other.subject, other.standard)
                                   or rel.standard in (other.subject, other.standard))
            for other in store.by_kind(Relation)
        ):
            continue  # a third relation also implicates one of these two entities — a chain, not a 2-holder split
        if rel.subject in holders or rel.standard in holders:
            continue  # already resolved (or resolving) elsewhere — nothing to do
        standard_value = evaluate(
            f"({total.value} - {rel.offset}) / (1 + {rel.factor})", {}, log,
            source="synth/sum-constraint",
        )
        subject_value = evaluate(
            f"{total.value} - ({standard_value})", {}, log,
            source="synth/sum-constraint",
        )
        if standard_value < 0 or subject_value < 0:
            continue  # a physically impossible split — decline rather than commit
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/sum-constraint",
                    sentence=rel.provenance.sentence,
                    temporal_perspective=rel.provenance.temporal_perspective,
                ),
                entity=rel.standard, measure=measure, value=standard_value, verb=rel.verb,
                owner=rel.standard_owner or None,
            )
        )
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/sum-constraint",
                    sentence=rel.provenance.sentence,
                    temporal_perspective=rel.provenance.temporal_perspective,
                ),
                entity=rel.subject, measure=measure, value=subject_value, verb=rel.verb,
                owner=rel.subject_owner or None,
            )
        )
    return out


def _distributive_rate_source(q: Quantity) -> bool:
    """True when `q` genuinely STATES a per-container rate: the inherently
    distributive existential rule ('20 chairs IN EACH row'), or a plain
    fold whose subject carried a distributive determiner that learn.py
    tagged onto the provenance ('EACH box has 8 pens'). 'The second
    chapter is 36 pages' / 'bucket B has 30 seeds' fold to the identical
    (entity, measure) shape but state ONE instance's count — reading one
    as a rate is the garbage-total class this predicate exists to refuse.
    Shared by every rate-reading site (both container synths and the
    single-entity distributive-container branch) so the class has ONE
    definition, never a drifting mirror."""
    p = q.provenance
    if p.source == "arithmetic/existential-premise-distributive":
        return True
    return p.distributive


def _container_contents_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """container-content bridge (mining candidate container-content-bridge):
    'Mia bought 3 boxes of pencils. Each box has 10 pencils.' folds to two
    ORDINARY Quantity facts the kernel already gets right today — a
    per-container RATE (CR: entity='box', measure='pencil', value=10, from
    "each box has...") and a holder's CONTAINER COUNT (H: entity='mia',
    measure='box', value=3, from "bought 3 boxes of pencils") — but nothing
    bridges them into 'mia has 30 pencils' because a Quantity's ENTITY being
    ANOTHER Quantity's MEASURE is a pure STRUCTURAL relation, not a lexical
    one: no ask shape or ordinary fold connects the two independently-true
    facts. This plugin closes exactly that gap by composition: whenever a
    Quantity CR's entity equals the container noun C and its measure is the
    content noun I, and a DIFFERENT Quantity H's measure is that same C,
    emit Quantity(entity=H.entity, measure=I, value=H.value*CR.value,
    verb=H.verb) — the holder's derived content total.

    Restricted to direct premise facts — never another synth plugin's own
    output. Holder counts are either historical raw folds or grammar-rule
    quantities whose provenance explicitly marks them `container_count`; a
    per-container rate may likewise be emitted by a rule whose provenance
    marks it distributive. This admits inline qualified package counts and an
    indefinite class statement such as "a large crate has 80 beads" without
    treating arbitrary rule-emitted quantities or a definite individual crate
    as package evidence.

    Decline-safe gates, all measured against dev-train (0 BROKE, 0 new
    wrong on the full 3772-item dev-train + dev-holdout diff):
    - exactly ONE container-rate CR for a given (C, I) pair — two rival
      per-container rates for the same container/content pair is
      ambiguous, never averaged or summed;
    - the holder must not itself BE the container ('the box has 10
      pencils. it has 3 pencils' can't bridge to itself);
    - the holder must not ALREADY hold a Quantity of measure I — a
      genuinely stated total is never overwritten or double-counted;
    - CR and H must share the same `time` (mixed-time arithmetic is
      unbuilt elsewhere in this kernel and stays unbuilt here).

    USE-GATED, not existence-gated (docs/composition.md): emitted at
    `sentence=-1`, exactly the SynthRule datalog
    convention (see `_apply_synth_rule` above) — never a real premise
    sentence index. The derived VALUE (H.value*CR.value) is a NEW number
    that was never itself stated in the text (unlike relation-to-quantity's
    derived values, which anchor a stated relation to an existing holding
    at the relation's own sentence); tagging it to a real sentence would
    let `guards._fact_values_by_sentence` treat that sentence's unrelated
    stated numbers as 'read' whenever they coincidentally equal the
    product (e.g. '3 boxes of pencils and 30 crayons' — 3*10=30 must never
    launder the untouched '30 crayons' as accounted for). `sentence=-1`
    never matches any premise or question `reading.sentence_index`, so the
    derived value simply never enters that accounting — exactly how Rate/
    Price/Goal/GroupTotal's OWN values stay use-gated today. The two
    STATED numbers this synth actually reads (H's own count, CR's own
    per-container rate) remain accounted the ordinary way, via their own
    untouched raw facts at their own real sentences — no guards.py change
    needed.

    Infrastructure only: this plugin's emitted fact currently has no
    consumer (no ask shape reads a container-content total yet) — it
    SOLVES 0 dev-train items on its own. Its payoff (container-content
    totality asks) is a separate, later increment, built on this branch."""
    out: list[Fact] = []
    direct_quantities = [
        q for q in store.by_kind(Quantity)
        if not q.provenance.source.startswith("synth/")
    ]
    holder_quantities = [
        q
        for q in direct_quantities
        if (
            q.provenance.source == "fold"
            or q.provenance.container_count
        )
    ]
    known_measures_by_entity: dict[str, set[str]] = {}
    for q in store.by_kind(Quantity):
        known_measures_by_entity.setdefault(q.entity, set()).add(q.measure)

    # a CR must genuinely STATE a per-container rate (`_distributive_rate_
    # source`, the distributive-container-total synth's own gate): 'The
    # second chapter is 36 pages' folds to the identical (entity, measure)
    # shape as 'Each box has 10 pencils' but states ONE instance's count —
    # composing it minted a garbage bridged total (book page = 2 × 36)
    # beside the genuinely stated one. Filtered BEFORE the uniqueness
    # check, so a specific instance's fact never blocks a real rate either.
    rates_by_pair: dict[tuple[str, str], list[Quantity]] = {}
    for q in direct_quantities:
        if not _distributive_rate_source(q):
            continue
        rates_by_pair.setdefault((q.entity, q.measure), []).append(q)

    contributions: dict[
        tuple[str, str, str, int | None, str | None, str | None, str | None, str | None],
        tuple[Quantity, str, float],
    ] = {}
    for (container, content), rates in rates_by_pair.items():
        if len(rates) != 1:
            continue  # ambiguous per-container rate — decline rather than guess
        (rate,) = rates
        for holder in holder_quantities:
            if holder.measure != container or holder.entity == container:
                continue
            if content in known_measures_by_entity.get(holder.entity, ()):
                continue  # never overwrite an already-known/stated total
            if holder.time != rate.time:
                continue  # mixed times — time arithmetic is unbuilt
            value = evaluate(
                f"{holder.value} * {rate.value}", {}, log,
                source="synth/container-contents",
            )
            key = (
                holder.entity,
                content,
                holder.verb,
                holder.occurrence,
                holder.time,
                holder.owner,
                holder.qualifier,
                holder.label,
            )
            previous = contributions.get(key)
            if previous is not None:
                value = evaluate(
                    f"{previous[2]} + {value}", {}, log,
                    source="synth/container-contents-sum",
                )
            contributions[key] = (holder, content, value)
            # mining candidate distributive-holder-enum: `rate` (CR) just
            # got composed into `holder`'s own bridged total above — its
            # (entity, measure) key is a per-unit RATE, not an independent
            # holding, so a downstream holder-enumeration consumer must not
            # sum it ALONGSIDE the bridged total it was consumed to derive
            # (see ArithmeticLog.consumed_rate_keys's own docstring).
            log.consumed_rate_keys.add((rate.entity, rate.measure))
    for holder, content, value in contributions.values():
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/container-contents", sentence=-1
                ),
                entity=holder.entity,
                measure=content,
                value=value,
                verb=holder.verb,
                occurrence=holder.occurrence,
                time=holder.time,
                owner=holder.owner,
                qualifier=holder.qualifier,
                label=holder.label,
            )
        )
    return out


def _container_totality_transfer_synth(
    store: FactStore,
    reg: Registry,
    log: ArithmeticLog,
) -> list[Fact]:
    """Move one source's unambiguous complete quantity into a container.

    ``TotalityTransfer`` deliberately carries no measure: a surface such as
    "she puts them all in the bin" leaves that information anaphoric.  The
    transfer becomes quantitative only when the resolved source has exactly
    one non-container measure. Package counts are excluded because they name
    the means of carrying the contents, not additional contents to place in
    the destination. Multiple candidate content measures or multiple complete
    transfers from the same source decline rather than guessing.
    """
    out: list[Fact] = []
    transfers = list(store.by_kind(TotalityTransfer))
    for transfer in transfers:
        if sum(
            candidate.source == transfer.source
            for candidate in transfers
        ) != 1:
            continue

        if transfer.package_class_count is not None:
            package_classes = {
                quantity.measure
                for quantity in store.by_kind(Quantity)
                if quantity.entity == transfer.source
                and quantity.measure_qualifier is not None
                and (
                    transfer.package is None
                    or quantity.measure.split("[", 1)[0] == transfer.package
                )
                and reg.word_in_category(
                    quantity.measure.split("[", 1)[0],
                    "sized_quantity_container",
                )
            }
            if len(package_classes) != transfer.package_class_count:
                continue

        measures = {
            quantity.measure.split("[", 1)[0]
            for quantity in store.by_kind(Quantity)
            if quantity.entity == transfer.source
            and not _distributive_rate_source(quantity)
            and (
                transfer.content is None
                or quantity.measure.split("[", 1)[0] == transfer.content
            )
            and not reg.word_in_category(
                quantity.measure.split("[", 1)[0],
                "quantity_container",
            )
        }
        if len(measures) != 1:
            continue
        (measure,) = measures
        value = _entity_total(store, reg, transfer.source, measure, log)
        if value is None:
            continue

        provenance = Provenance(
            source="synth/container-totality-transfer",
            sentence=-1,
            assumption=transfer.provenance.assumption,
        )
        out.append(
            Quantity(
                provenance=provenance,
                entity=transfer.destination,
                measure=measure,
                value=value,
                verb="have",
            )
        )
        out.append(
            ContainerContent(
                provenance=provenance,
                container=transfer.destination,
                content=measure,
                operation="transfer_all",
                occurrence=transfer.occurrence,
            )
        )
    return out


def _totality_event_synth(
    store: FactStore,
    reg: Registry,
    log: ArithmeticLog,
) -> list[Fact]:
    """Materialize an explicitly complete activity from compatible holdings.

    A totality surface such as ``she eats it all`` states no number.  It may
    borrow an amount only from one earlier :class:`BoundedActivityInquiry`
    for the same participant and activity.  The inquiry's content head names
    the whole; distributive per-whole rates also expose compatible measured
    contents (for example pizzas -> slices).  This preserves both legitimate
    units without making ``piece`` and ``slice`` global synonyms.

    Existing events under the target verb make the remaining amount
    underdetermined, so the synth declines instead of treating "all" as an
    additional copy.  Derived facts are excluded from their own source store,
    keeping saturation monotone and idempotent.
    """

    out: list[Fact] = []
    inquiries = list(store.by_kind(BoundedActivityInquiry))
    derived_source = "synth/totality-event"
    source_store = FactStore(
        facts=[
            fact
            for fact in store.facts
            if not (
                isinstance(fact, Quantity)
                and fact.provenance.source == derived_source
            )
        ]
    )

    for event in store.by_kind(TotalityEvent):
        matching = [
            inquiry
            for inquiry in inquiries
            if inquiry.seeker == event.entity
            and inquiry.activity == event.verb
        ]
        if len(matching) != 1:
            continue
        (inquiry,) = matching
        root = inquiry.content.split("[", 1)[0]

        related_measures = {root}
        for rate in source_store.by_kind(Quantity):
            if not _distributive_rate_source(rate):
                continue
            if rate.entity.split("[", 1)[0] == root:
                related_measures.add(rate.measure.split("[", 1)[0])

        theme_categories = {
            frame["theme"]
            for _category, frame in reg.selectional_frames(event.verb)
            if "theme" in frame
        }
        eligible = sorted(
            measure
            for measure in related_measures
            if any(
                reg.word_in_category(measure, category)
                for category in theme_categories
            )
        )
        if not eligible:
            continue

        # A prior event under the same activity means "all" could denote the
        # original or the remaining pool. Remaining-state reasoning is a
        # different contract, so this route refuses the ambiguity.
        if any(
            quantity.entity == event.entity
            and quantity.verb == event.verb
            and quantity.measure.split("[", 1)[0] in eligible
            for quantity in source_store.by_kind(Quantity)
        ):
            continue

        totals: dict[str, float] = {}
        for measure in eligible:
            value = _entity_total(
                source_store, reg, event.entity, measure, log
            )
            if value is None or value < 0:
                totals = {}
                break
            totals[measure] = value
        if not totals:
            continue

        for quantity in source_store.by_kind(Quantity):
            if (
                quantity.entity == event.entity
                and quantity.measure.split("[", 1)[0] in totals
            ):
                log.consumed_totality_source_keys.add(
                    (
                        quantity.entity,
                        quantity.measure,
                        quantity.verb,
                        quantity.time,
                        quantity.occurrence,
                    )
                )

        for measure, value in totals.items():
            out.append(
                Quantity(
                    provenance=Provenance(
                        source=derived_source,
                        sentence=-1,
                        assumption=event.provenance.assumption,
                    ),
                    entity=event.entity,
                    measure=measure,
                    value=value,
                    verb=event.verb,
                    time=inquiry.unit,
                    occurrence=event.occurrence,
                )
            )
    return out


def _distributive_container_total_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """Distributive 'each' container totals (mining candidate distributive-
    each-totals): 'There are 40 rows of chairs. There are 20 chairs in each
    row.' / 'There are 5 boxes and each box has 8 pens.' — a per-container
    RATE (CR: entity=container noun, measure=content noun, e.g. entity=
    'row'/'box', measure='chair'/'pen' — from an ordinary SVO fold "each
    box HAS 8 pens" or from arithmetic/existential-premise-distributive's
    "20 chairs IN EACH row") composes with the container's own COUNT
    (H: any Quantity or GroupTotal whose MEASURE is that SAME container
    noun — '40 rows', '5 boxes', or a container total this very plugin
    derived on an earlier saturation round) into the group's total content:
    GroupTotal(measure=content, value=H.value * CR.value).

    Chained transitively for free by the ordinary saturation fixpoint,
    exactly like every other plugin here: a derived GroupTotal from one hop
    (measure=container) is itself a valid H for the NEXT hop — 'six chairs
    in each row; twenty rows' derives GroupTotal(chair)=120, then 'each
    chair holds five people' composes THAT total as the chair-count input
    into GroupTotal(person)=600, with no extra loop needed here (saturate()
    already reruns every plugin each round).

    UNIQUE AT EVERY HOP, never guessed:
    - CR must be a RAW premise fact (`provenance.source` not a `synth/`
      derivation, mirroring `_container_contents_synth`'s own raw-CR
      discipline) — the stated per-container rate itself, never a value
      some other synth already produced;
    - exactly one CR for the (container, content) pair — two rival stated
      rates is ambiguous, never averaged;
    - the container must not equal the content (no self-loop);
    - exactly one holder-count fact (Quantity OR GroupTotal, any source)
      for the container measure across the WHOLE store — zero is exactly
      today's decline (a per-container rate with no stated container
      count), several is a genuine ambiguity (e.g. two independent
      groups both counted in the same noun) and also declines rather than
      guess which one the rate belongs to;
    - never emits when a GroupTotal for the content measure already
      exists — a genuinely stated total (or an earlier-round derivation)
      wins; same-key disagreement is a real conflict per GroupTotal's own
      docstring, so this plugin refuses to even attempt a second value
      rather than let facts.py quarantine a spurious collision.

    THE PRECISION FIX THIS INCREMENT SHIPS (constitution rule 4): before
    this plugin existed, CR (entity=container) was the ONLY fact known for
    the content measure, so answer.py's unique-entity fold read it as if
    it were the group's total — a CONFIDENT WRONG ('20 chairs in each row'
    answered '20' for 'how many chairs are there?', gold 800). Emitting
    this GroupTotal does not, by itself, change that fold's reasoning —
    answer.py's unique-entity consumer additionally declines whenever a
    GroupTotal now exists for the measure it is about to fold a lone
    per-container entity over (see its own comment there), converting the
    latent wrong into a safe decline. The follow-up class (entity-less
    container-total asks that read this GroupTotal directly, remainder/
    fraction consumers that treat it as a pool) is a separate, later
    increment: this plugin SOLVES 0 dev-train items by design — it is
    infrastructure, not a payoff."""
    # a per-container RATE must come from a surface that actually STATES a
    # per-unit content — an ordinary SVO fold ("each box HAS 8 pens") or
    # this candidate's own distributive-existential rule ("20 chairs IN
    # EACH row"). A plain partitive existential ("40 ROWS of chairs",
    # arithmetic/existential-premise) states a TOTAL count, not a rate —
    # despite folding to the identical (entity, measure) shape by the
    # generic 'item PREP place' skeleton — so it must never be read as one
    # here: doing so would derive a spurious REVERSED total (mistaking
    # 'chairs' as the container of 'rows') and, via the unique-entity
    # guard below, wrongly decline the ordinary, already-correct "how many
    # rows are there?" reading of the very same two sentences.
    # A per-container RATE must come from a genuinely DISTRIBUTIVE surface, not
    # any container-entity fold. 'Each box has 8 pens' and 'bucket B has 30 seeds'
    # both fold to entity=container/measure=content with source='fold' — identical
    # shape, opposite meaning. Reading a specific instance's count as a per-unit
    # rate derived garbage totals (bucket seed=90, warehouse box=800) that then
    # made the GroupTotal-reading guards decline the surrounding item. The
    # existential-distributive rule ('20 chairs IN EACH row') is inherently
    # distributive; a plain fold qualifies only when learn.py tagged its subject's
    # distributive determiner ('EACH'/'every') onto the provenance.
    out: list[Fact] = []
    known_group_totals = {gt.measure for gt in store.by_kind(GroupTotal)}
    _is_rate_source = _distributive_rate_source

    rate_facts: set[int] = set()
    rates_by_pair: dict[tuple[str, str], list[Quantity]] = {}
    for q in store.by_kind(Quantity):
        if not _is_rate_source(q) or q.entity == q.measure:
            continue
        rates_by_pair.setdefault((q.entity, q.measure), []).append(q)
        rate_facts.add(id(q))

    # a CONTAINER COUNT must be the container's own stated/derived TOTAL,
    # never a fact that is itself playing the CR (per-unit rate) role for
    # some OTHER pair — a two-hop chain's middle noun ('chair' above) is
    # simultaneously the CONTENT of one rate ('row'/'chair') and the
    # CONTAINER of the next ('chair'/'person'); the first rate's own raw
    # fact happens to carry measure='chair' too, but its value (6, "per
    # row") is not a chair TOTAL and must never masquerade as one — that
    # would derive the next hop from a stale per-unit number instead of
    # the composed total, and (worse) lock in the wrong value permanently
    # once this plugin's own 'never overwrite an existing GroupTotal'
    # guard treats that wrong first answer as already resolved.
    counts_by_container: dict[str, list[float]] = {}
    for q in store.by_kind(Quantity):
        if id(q) in rate_facts:
            continue
        counts_by_container.setdefault(q.measure, []).append(q.value)
    for gt in store.by_kind(GroupTotal):
        counts_by_container.setdefault(gt.measure, []).append(gt.value)

    totals_by_content: dict[str, tuple[float, str]] = {}
    for (container, content), rates in rates_by_pair.items():
        if len(rates) != 1:
            continue  # ambiguous per-container rate — decline rather than guess
        (rate,) = rates
        if content in known_group_totals:
            continue  # a real (or earlier-round) total already wins
        counts = counts_by_container.get(container, [])
        if len(counts) != 1:
            continue  # zero or ambiguous container counts — decline
        (count,) = counts
        value = evaluate(
            f"{count} * {rate.value}", {}, log,
            source="synth/distributive-container-total",
        )
        previous = totals_by_content.get(content)
        if previous is not None:
            value = evaluate(
                f"{previous[0]} + {value}", {}, log,
                source="synth/distributive-container-total-sum",
            )
        totals_by_content[content] = (value, rate.verb)
        # NOTE (mining candidate distributive-holder-enum): deliberately
        # NOT marking `rate` in `log.consumed_rate_keys` here, unlike
        # synth/container-contents below. This synth's `container`
        # pairing is keyed by measure-NAME coincidence across the WHOLE
        # store (`counts_by_container`, built from every Quantity/
        # GroupTotal regardless of what noun the entity itself is), not
        # by an actual container-noun structural role — dev-train proved
        # this fires on unrelated collisions (e.g. a stated "Bill has 60
        # toys" got paired as a bogus per-'bill' rate whenever some other
        # fact's measure happened to read 'bill'), which is harmless today
        # only because nothing downstream reads `consumed_rate_keys` yet.
        # Marking it here demoted three genuinely independent holders
        # (BROKE on dev-train: 9a46ef7a9e2e, af2909139386, f325779c365e)
        # the moment `_combined_holder_totals` started consuming the set.
        # Left as a documented non-fix, not silently dropped.
    for content, (value, verb) in totals_by_content.items():
        out.append(
            GroupTotal(
                provenance=Provenance(
                    source="synth/distributive-container-total", sentence=-1
                ),
                measure=content, value=value, verb=verb,
            )
        )
    return out


def _enumeration_elimination_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Stage 9h: n-way disjunctive elimination over an exhaustive counted
    enumeration. EnumeratedDisjunction(cls, options) says every member of
    cls is SOME option (inclusive — patterns.py minted it only because the
    stated count matched the list). For a stated member of cls with all
    options but exactly one REFUTED by explicit negative atoms, the last
    option holds.

    Soundness guards, each load-bearing:
    - the entity must be a POSITIVE stated member of cls (no membership,
      no elimination — the Joey null control);
    - a member with any POSITIVE option atom is already decided — emit
      nothing (dedup would eat a duplicate anyway; a DIFFERENT positive
      option is consistent under the inclusive reading, so asserting the
      last undecided one from it would be unsound);
    - every non-final option must be refuted by an explicit negative atom
      — exactly one option may lack an atom entirely;
    - a QUARANTINED atom on (entity, option) means contradictory premises
      touched the disjunction: the pair vanishes from store.facts, so the
      option would otherwise read as merely "undecided" and the
      elimination would assert from a contradiction. Skip the entity.
    """
    enums = [f for f in store.facts if isinstance(f, EnumeratedDisjunction)]
    if not enums:
        return []
    out: list[Fact] = []
    polarity: dict[tuple[str, str], bool] = {}
    members: dict[str, list[str]] = {}
    for f in store.facts:
        if isinstance(f, Atom):
            polarity[(f.entity, f.pred)] = f.polarity
            if f.polarity:
                members.setdefault(f.pred, []).append(f.entity)
    tainted = {
        (f.entity, f.pred) for f in store.quarantined if isinstance(f, Atom)
    }
    for enum in enums:
        for entity in members.get(enum.cls, ()):
            if any((entity, o) in tainted for o in enum.options):
                continue
            decided = [polarity.get((entity, o)) for o in enum.options]
            if any(p is True for p in decided):
                continue  # already classified — nothing to eliminate toward
            open_opts = [
                o for o, p in zip(enum.options, decided) if p is None
            ]
            # exactly one open AND every other option explicitly refuted —
            # redundant given the positive-atom skip above, but the
            # conjunction is the statement of the inference and must
            # survive any future edit to that skip
            if len(open_opts) != 1:
                continue
            if sum(1 for p in decided if p is False) != len(enum.options) - 1:
                continue
            out.append(Atom(
                provenance=Provenance(
                    source="synth/enumeration-elimination", sentence=-1
                ),
                entity=entity, pred=open_opts[0], polarity=True,
                indef_obj=True,
            ))
    return out


def _name_prefix_alias_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Stage 9j: name-shortening identity — a story that says "Islip
    Speedway is …" and then "Islip is …" is using one name twice, and the
    9e alias-copy synths carry every ground atom across once the Alias
    exists. This is the INFERENCE the 9e reader deliberately excluded
    (model.Alias's docstring drew the boundary), built as its own gated
    mechanism:

    - both names must already be FACT SUBJECTS in the story (an entity
      mentioned only in the question never aliases — no premise uses the
      short form, so nothing licenses the identification);
    - the short name's words must be a strict word-PREFIX of the long
      name's;
    - the long extension must be UNIQUE for the short form: with 'John
      Smith' and 'John Jones' both present, 'John' identifies neither.
    """
    subjects = {
        f.entity
        for f in store.facts
        if isinstance(f, (Atom, Disjunction))
    }
    out: list[Fact] = []
    have = {(f.a, f.b) for f in store.facts if isinstance(f, Alias)}
    for short in subjects:
        sw = short.split()
        longs = [
            e for e in subjects
            if e != short and len(e.split()) > len(sw) and e.split()[: len(sw)] == sw
        ]
        if len(longs) == 1 and (short, longs[0]) not in have:
            out.append(Alias(
                provenance=Provenance(source="synth/name-prefix-alias", sentence=-1),
                a=short, b=longs[0],
            ))
    return out


def _name_head_sortal_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Stage 9j: the head-noun sortal — a multi-word proper name whose
    FINAL word names a class the story actively quantifies over carries
    that class as its sort: 'Islip Speedway' is a speedway exactly when
    some universal/conditional in the story ranges over 'speedway'.

    The join-driven gate is the soundness argument: a free-floating
    "every name asserts its head" rule is wrong ('The Salmon of Doubt'
    is not a salmon of anything), so the sortal minted here must (a)
    come from a ≥2-word entity, (b) contain no partitive word (the
    titular-name shapes stay out), and (c) have its head ALREADY be a
    quantified class in this story — the story itself must treat the
    head as a sort before a name is read as declaring it."""
    classes = {
        f.cls
        for f in store.facts
        if isinstance(f, (Quantified, Conditional))
    }
    if not classes:
        return []
    out: list[Fact] = []
    ents = {f.entity for f in store.facts if isinstance(f, Atom)}
    decided = {(f.entity, f.pred) for f in store.facts if isinstance(f, Atom)}
    for e in ents:
        words = e.split()
        if len(words) < 2:
            continue
        if any(reg.word_in_category(w, "partitive") for w in words):
            continue
        head = words[-1]
        if head in classes and (e, head) not in decided:
            out.append(Atom(
                provenance=Provenance(source="synth/name-head-sortal", sentence=-1),
                entity=e, pred=head, polarity=True,
            ))
    return out


def _subject_role_derivation_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Derive an exact nominal role from one declared verbal/PP relation.

    The registry table owns every lexical decision: verb lemma, role noun,
    and which preposition may survive in the role phrase. The kernel only
    joins that frozen mapping to a positive structured relation and preserves
    its complete PP object. No mapping means no inference.
    """

    out: list[Fact] = []
    for relation in store.by_kind(VerbalRelation):
        if not relation.polarity or not relation.prep or not relation.obj:
            continue
        role = reg.subject_role_derivations.get(
            (relation.verb, relation.prep)
        )
        if role is None:
            continue
        out.append(Atom(
            provenance=Provenance(
                source="synth/subject-role-derivation",
                sentence=-1,
                assumption=relation.provenance.assumption,
            ),
            entity=relation.entity,
            pred=f"{role} {relation.prep} {relation.obj}",
            polarity=True,
        ))
    return out


def _declared_refinement(phrase: str, reg: Registry) -> str | None:
    """Return the exact superclass licensed by one leading modifier.

    The category owns the lexical decision.  This helper only removes one
    canonical leading token and preserves the complete remainder, including
    PP restrictions.  Undeclared, multiword, or empty shapes fail closed.
    """

    modifier, separator, superclass = phrase.partition(" ")
    if (
        not separator
        or not superclass
        or not reg.word_in_category(modifier, "refining_modifier")
    ):
        return None
    return superclass


def _class_refinement_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Materialize declared class refinement without intersective leakage."""

    out: list[Fact] = []
    candidates: list[tuple[Fact, str]] = []
    candidates.extend(
        (fact, fact.collection)
        for fact in store.by_kind(Membership)
        if fact.polarity
    )
    candidates.extend(
        (fact, fact.pred)
        for fact in store.by_kind(Atom)
        if fact.polarity
    )
    candidates.extend(
        (fact, fact.cls)
        for fact in store.by_kind(QuantifiedQuantity)
    )
    candidates.extend(
        (fact, fact.cls)
        for fact in store.by_kind(QuantifiedAdjustment)
    )

    for fact, subclass in candidates:
        superclass = _declared_refinement(subclass, reg)
        if superclass is None:
            continue
        provenance = Provenance(
            source="synth/declared-class-refinement",
            sentence=fact.provenance.sentence,
            assumption=fact.provenance.assumption,
        )
        out.append(ClassRefinement(
            provenance=provenance,
            subclass=subclass,
            superclass=superclass,
        ))
        if isinstance(fact, Membership):
            out.append(Membership(
                provenance=provenance,
                member=fact.member,
                collection=superclass,
                polarity=True,
            ))
        elif isinstance(fact, Atom):
            out.append(Atom(
                provenance=provenance,
                entity=fact.entity,
                pred=superclass,
                polarity=True,
                indef_obj=fact.indef_obj,
            ))
        # A class-wide quantity over the subclass must never widen to the
        # superclass.  Its only output here is the explicit ontology edge.
    return out


def _class_scope_compatible(
    superclass: str, base_class: str, reg: Registry
) -> bool:
    """Whether one base class is a compatible scoped form of a superclass.

    Exact class keys always compose.  A base may additionally preserve a
    prepositional restriction (``teacher at university`` for superclass
    ``teacher``), but only when the first extra token is declared as a
    preposition.  This is phrase structure, not a word list, and it fails
    closed for arbitrary shared-prefix classes.
    """

    if base_class == superclass:
        return True
    prefix = f"{superclass} "
    if not base_class.startswith(prefix):
        return False
    first_extra = base_class[len(prefix):].partition(" ")[0]
    return bool(first_extra) and reg.word_in_category(
        first_extra, "preposition"
    )


def _quantified_quantity_materialization_synth(
    store: FactStore, reg: Registry, log: ArithmeticLog
) -> list[Fact]:
    """Materialize exact class quantities and unique additive refinements.

    The ordinary base and adjusted cases intentionally share this plugin. If
    separate monotone rules first emitted the inherited baseline and later
    emitted the adjusted value, the store would correctly quarantine them as
    contradictory state quantities. Here an applicable adjustment suppresses
    its compatible baseline and emits exactly one final value, while zero or
    multiple compatible baselines emit none and are caught by the unresolved
    derivation guard before any numeric answer can commit.
    """

    # One exact positive class-membership witness per (entity, class). Prefer
    # Atom when both representations exist so the old PP-instantiation
    # provenance remains stable; simple copular membership takes the sibling
    # source below.
    memberships: dict[tuple[str, str], Fact] = {}
    for fact in store.by_kind(Atom):
        if fact.polarity:
            memberships.setdefault((fact.entity, fact.pred), fact)
    for fact in store.by_kind(Membership):
        if fact.polarity:
            memberships.setdefault((fact.member, fact.collection), fact)

    bases = list(store.by_kind(QuantifiedQuantity))
    adjustments = list(store.by_kind(QuantifiedAdjustment))
    refinements: dict[str, list[ClassRefinement]] = {}
    for refinement in store.by_kind(ClassRefinement):
        refinements.setdefault(refinement.subclass, []).append(refinement)

    # Every exact (member, universal) pair is a potential ordinary base
    # materialization. A compatible active adjustment marks the pair as
    # suppressed even when the complete resolution later proves ambiguous.
    base_applications: list[tuple[str, QuantifiedQuantity, Fact]] = []
    entities = sorted({entity for entity, _class in memberships})
    for entity in entities:
        for base in bases:
            evidence = memberships.get((entity, base.cls))
            if evidence is not None:
                base_applications.append((entity, base, evidence))

    # Group active adjustments by the state quantity they would determine.
    # Multiple distinct adjustment classes for one entity/measure are not
    # ordered; the group stays unresolved.
    grouped: dict[
        tuple[str, str, str],
        list[
            tuple[
                QuantifiedAdjustment,
                Fact,
                tuple[QuantifiedQuantity, ...],
            ]
        ],
    ] = {}
    suppressed: set[tuple[str, QuantifiedQuantity]] = set()
    for entity in entities:
        for adjustment in adjustments:
            membership_evidence = memberships.get((entity, adjustment.cls))
            if membership_evidence is None:
                continue
            compatible: list[QuantifiedQuantity] = []
            for base in bases:
                if (
                    base.measure != adjustment.measure
                    or base.verb != adjustment.verb
                    or (entity, base.cls) not in memberships
                ):
                    continue
                if any(
                    _class_scope_compatible(
                        refinement.superclass, base.cls, reg
                    )
                    for refinement in refinements.get(adjustment.cls, ())
                ):
                    compatible.append(base)
                    suppressed.add((entity, base))
            grouped.setdefault(
                (entity, adjustment.measure, adjustment.verb), []
            ).append((adjustment, membership_evidence, tuple(compatible)))

    out: list[Fact] = []
    for entity, base, evidence in base_applications:
        if (entity, base) in suppressed:
            continue
        source = (
            "synth/quantified-quantity-instantiation"
            if isinstance(evidence, Atom)
            else "synth/quantified-quantity-membership-instantiation"
        )
        quantity = Quantity(
            provenance=Provenance(
                source=source,
                sentence=-1,
                assumption=(
                    base.provenance.assumption
                    or evidence.provenance.assumption
                ),
            ),
            entity=entity,
            measure=base.measure,
            value=base.value,
            verb=base.verb,
        )
        if quantity.key() not in {collision.key for collision in store.collisions}:
            out.append(quantity)

    existing_adjusted = {
        quantity.key()
        for quantity in store.by_kind(Quantity)
        if quantity.provenance.source.startswith(
            "synth/quantified-adjustment-materialization"
        )
    }
    existing_adjusted.update(
        ambiguity.key
        for ambiguity in store.agreement_ambiguities
        if ambiguity.retained.source.startswith(
            "synth/quantified-adjustment-materialization"
        )
        or ambiguity.deduped.source.startswith(
            "synth/quantified-adjustment-materialization"
        )
    )
    collision_keys = {collision.key for collision in store.collisions}
    for (entity, measure, verb), resolutions in sorted(grouped.items()):
        if len(resolutions) != 1:
            continue
        adjustment, membership_evidence, compatible = resolutions[0]
        if len(compatible) != 1:
            continue
        base = compatible[0]
        quantity_key = ("quantity", entity, measure, verb, None, None)
        if quantity_key in existing_adjusted or quantity_key in collision_keys:
            continue
        proof_source = (
            "synth/quantified-adjustment-materialization"
            f"[base={base.provenance.source};"
            f"adjustment={adjustment.provenance.source}"
            + (
                f";assumption={membership_evidence.provenance.source}"
                f"@{membership_evidence.provenance.sentence}"
                if membership_evidence.provenance.assumption
                else ""
            )
            + "]"
        )
        try:
            value = evaluate(
                "base + adjustment",
                {"base": base.value, "adjustment": adjustment.offset},
                log,
                source=proof_source,
            )
        except EvaluationError:
            continue
        if value < 0:
            continue
        out.append(Quantity(
            provenance=Provenance(
                source=proof_source,
                sentence=adjustment.provenance.sentence,
                assumption=(
                    base.provenance.assumption
                    or adjustment.provenance.assumption
                    or membership_evidence.provenance.assumption
                ),
            ),
            entity=entity,
            measure=measure,
            value=value,
            verb=verb,
        ))
    return out


PLUGINS: dict[str, Synthesizer] = {
    "synth/declared-class-refinement": _class_refinement_synth,
    "synth/enumeration-elimination": _enumeration_elimination_synth,
    "synth/name-prefix-alias": _name_prefix_alias_synth,
    "synth/name-head-sortal": _name_head_sortal_synth,
    "synth/measured-container-content": _measured_container_content_synth,
    "synth/subject-role-derivation": _subject_role_derivation_synth,
    "synth/goal-relation": _goal_relation_synth,
    "synth/goal-progress": _goal_progress_synth,
    # Runs after every membership-producing plugin (notably the declared
    # refinement and subject-role bridges). A monotone materializer cannot
    # retract a prematurely emitted 25 when a second compatible baseline
    # becomes visible later in the same fixpoint.
    "synth/universal-quantity-materialization": _quantified_quantity_materialization_synth,
    "synth/relation-to-quantity": _relations_synth,
    "synth/bare-age-anchor": _bare_age_anchor_synth,
    "synth/anchor-quantity": _anchor_quantity_synth,
    "synth/fraction-of-pool": _fraction_synth,
    "synth/rest-of-pool": _rest_synth,
    "synth/partition-of-collection": _partition_synth,
    "synth/partition-aggregate-share": _partition_aggregate_share_synth,
    "synth/partition-attribute-quantity": _partition_attribute_quantity_synth,
    "synth/sequential-partition-complement": _sequential_partition_complement_synth,
    "synth/sequential-partition-join": _sequential_partition_join_synth,
    "synth/sequential-partition-prefix-join": _sequential_partition_prefix_join_synth,
    "synth/sequential-partition": _sequential_partition_synth,
    "synth/partition-membership-quantity": _partition_membership_synth,
    "synth/partition-complement-quantity": _partition_complement_synth,
    "synth/ratio-split-quantity": _ratio_split_synth,
    "synth/sum-constraint": _sum_constraint_synth,
    "synth/container-contents": _container_contents_synth,
    "synth/container-totality-transfer": _container_totality_transfer_synth,
    "synth/totality-event": _totality_event_synth,
    "synth/distributive-container-total": _distributive_container_total_synth,
}


PLUGINS["synth/text-evidence"] = text_evidence


def saturate(store: FactStore, reg: Registry, log: ArithmeticLog) -> FactStore:
    for _round in range(MAX_ROUNDS):
        before = len(store.facts)
        for rule in reg.synth_rules:  # sorted by id — deterministic
            for fact in _apply_synth_rule(rule, store, reg, log):
                store.admit(fact)
        for name in sorted(PLUGINS):
            for fact in PLUGINS[name](store, reg, log):
                store.admit(fact)
        if len(store.facts) == before:
            return store
    raise RuntimeError(f"saturation did not reach a fixpoint in {MAX_ROUNDS} rounds")
