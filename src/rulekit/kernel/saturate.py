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

import itertools
from dataclasses import dataclass, replace
from typing import Callable, Protocol

from ..data.registry import Registry
from ..data.schemas import SynthRule
from .evaluate import ArithmeticLog, EvaluationError, evaluate
from .facts import FactStore
from .model import (
    AnchorQuantity,
    Fact,
    GroupTotal,
    Predication,
    Price,
    Provenance,
    Quantity,
    Relation,
)

MAX_ROUNDS = 50

_FIELD_ALIASES = {"entity", "measure", "value", "verb", "subject", "standard",
                  "factor", "offset", "part", "whole", "fraction", "member",
                  "collection", "earlier", "later", "polarity", "dobj", "time"}


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
    kind_facts = {
        shape.fact: [f for f in store.facts if type(f).__name__.lower() == shape.fact]
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


def _relations_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """Resolve Relation facts against known Quantities:
    subject = factor*standard + offset, hop by hop (raw factors visible)."""
    from .answer import _resolve_measure_against

    out: list[Fact] = []
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
    measures_by_entity: dict[str, set[str]] = {}
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
    for q in store.by_kind(Quantity):
        quantities.setdefault((q.entity, q.measure), q)
        by_verb.add((q.entity, q.measure, verb_key(q.verb)))
        measures_by_entity.setdefault(q.entity, set()).add(q.measure)
        if q.is_state:
            quantities[(q.entity, q.measure)] = q
        if q.label:
            base = q.entity.split("[", 1)[0]
            labeled_quantities.setdefault((base, q.measure, q.label), q)
            by_verb_labeled.add((base, q.measure, verb_key(q.verb), q.label))
            if q.is_state:
                labeled_quantities[(base, q.measure, q.label)] = q

    def anchor_measure(
        entity: str, measure: str, label: str | None = None
    ) -> tuple[str, Quantity] | None:
        """The relation's stated measure resolved against ONE entity's own
        holdings — an EXACT match first, else (only for `interchangeable`
        categories, e.g. currency) the entity's unique same-category
        measure ('money' resolves to the anchor's own stated 'dollar').
        Ambiguous (two different currencies on the same entity) or
        unresolvable declines this relation, never guesses.

        `label`, when given (mining candidate labeled-entity-relations):
        the relation's own text named a SPECIFIC labeled standard ("jar
        A") — resolve against exactly that labeled Quantity or decline;
        never fall back to a same-lemma sibling under a DIFFERENT label,
        and never widen via the interchangeable-category path either (a
        stated label is already maximally specific, so borrowing a
        sibling measure on top of it would compound two guesses into
        one)."""
        if label:
            known = labeled_quantities.get((entity, measure, label))
            return (measure, known) if known is not None else None
        exact = quantities.get((entity, measure))
        if exact is not None:
            return measure, exact
        candidate = _resolve_measure_against(measure, measures_by_entity.get(entity, set()), reg)
        if candidate is None or candidate == measure:
            return None
        candidate_known = quantities.get((entity, candidate))
        if candidate_known is None:
            return None
        return candidate, candidate_known

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
    standard_subjects: dict[str, set[str]] = {}
    for r in store.by_kind(Relation):
        standard_subjects.setdefault(r.standard, set()).add(r.subject)

    def is_subtype_standard(rel: Relation) -> bool:
        """True only for a standard that structurally LOOKS like a same-
        holder subtype measure, never a separate (named or labeled)
        holder: lexiconed `noun` sense (a name is never in the lexicon at
        all — constitution rule 1, no word list, this reads the pre-
        existing sense data), carries no label (a labeled standard, "jar
        A", is always a genuine distinguishable holder — mining candidate
        labeled-entity-relations), and is used as a standard by exactly
        ONE subject anywhere in this document (the `standard_subjects`
        discriminator above)."""
        return (
            reg.word_in_category(rel.standard, "noun")
            and not rel.subject_label
            and not rel.standard_label
            and len(standard_subjects.get(rel.standard, ())) <= 1
        )

    for rel in store.by_kind(Relation):
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
            if rel.standard == _ANAPHOR_QUANTITY_STANDARD:
                prior_q = [
                    q for q in store.by_kind(Quantity)
                    if q.provenance.sentence < rel.provenance.sentence
                ]
                if len(prior_q) == 1:
                    (anchor_q,) = prior_q
                    if (rel.subject, anchor_q.measure, verb_key(rel.verb)) not in by_verb:
                        value = evaluate(
                            f"{rel.factor} * {anchor_q.value} + {rel.offset}", {}, log,
                            source=f"relation-anaphor:{rel.provenance.source}",
                        )
                        out.append(
                            Quantity(
                                provenance=Provenance(
                                    source="synth/relation", sentence=rel.provenance.sentence
                                ),
                                entity=rel.subject, measure=anchor_q.measure, value=value,
                                verb=rel.verb, label=rel.subject_label or None,
                            )
                        )
            else:
                prior_p = [
                    p for p in store.by_kind(Price)
                    if p.provenance.sentence < rel.provenance.sentence
                ]
                if len(prior_p) == 1:
                    (anchor_p,) = prior_p
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
        if rel.measure is None:
            # mining candidate elided-measure-relations: the pattern rule
            # stated no measure noun at all ("Ben has twice as many as
            # Ann") — recover it from the STANDARD's own unique in-play
            # quantity, the same unique-pool-in-play discipline
            # synth/fraction-of-pool and synth/partition-of-collection
            # already use. Exactly one measure known for the standard
            # resolves; zero or two-or-more (ambiguous) declines this
            # relation for the round — never guesses. A standard whose
            # own measure is itself only DERIVED by an earlier round (a
            # chained elided relation) resolves on a LATER round with no
            # extra loop here: saturate() reruns this whole function every
            # round from the fixpoint driver, rebuilding `measures_by_entity`
            # from the then-current store each time.
            std_candidates = measures_by_entity.get(rel.standard, set())
            if len(std_candidates) != 1:
                continue
            (recovered,) = std_candidates
            rel = replace(rel, measure=recovered)
        # resolution is blocked when the target already has a quantity UNDER
        # THE RELATION'S OWN VERB — "Zig wrote 4× as many" plus "Zig wrote
        # 60" describe the SAME writing (re-deriving doubles it); a lose
        # event on top of a have-relation is a CHANGE and stays allowed
        resolved = anchor_measure(rel.standard, rel.measure, rel.standard_label)
        if resolved is not None:
            measure, known = resolved
            already = (
                (rel.subject, measure, verb_key(rel.verb), rel.subject_label) in by_verb_labeled
                if rel.subject_label
                else (rel.subject, measure, verb_key(rel.verb)) in by_verb
            )
            if not already:
                value = evaluate(
                    f"{rel.factor} * {known.value} + {rel.offset}", {}, log,
                    source=f"relation:{rel.provenance.source}",
                )
                out.append(
                    Quantity(
                        provenance=Provenance(source="synth/relation", sentence=rel.provenance.sentence),
                        entity=rel.subject, measure=measure, value=value, verb=rel.verb,
                        label=rel.subject_label or None,
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
        subtype_known = quantities.get((rel.subject, rel.standard))
        if (
            subtype_known is not None
            and (rel.subject, rel.measure, verb_key(rel.verb)) not in by_verb
        ):
            value = evaluate(
                f"{rel.factor} * {subtype_known.value} + {rel.offset}", {}, log,
                source=f"relation-subtype:{rel.provenance.source}",
            )
            out.append(
                Quantity(
                    provenance=Provenance(source="synth/relation", sentence=rel.provenance.sentence),
                    entity=rel.subject, measure=rel.measure, value=value, verb=rel.verb,
                )
            )
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
        subject_known = quantities.get((rel.subject, rel.measure))
        if (
            subject_known is not None
            and rel.factor != 0
            and is_subtype_standard(rel)
            and (rel.subject, rel.standard, verb_key(rel.verb)) not in by_verb
        ):
            value = evaluate(
                f"({subject_known.value} - {rel.offset}) / {rel.factor}", {}, log,
                source=f"relation-subtype-inverse:{rel.provenance.source}",
            )
            out.append(
                Quantity(
                    provenance=Provenance(source="synth/relation", sentence=rel.provenance.sentence),
                    entity=rel.subject, measure=rel.standard, value=value, verb=rel.verb,
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
        resolved = anchor_measure(rel.subject, rel.measure, rel.subject_label)
        if (
            resolved is not None
            and rel.factor != 0
            and not is_subtype_standard(rel)
        ):
            measure, known = resolved
            already = (
                (rel.standard, measure, verb_key(rel.verb), rel.standard_label) in by_verb_labeled
                if rel.standard_label
                else (rel.standard, measure, verb_key(rel.verb)) in by_verb
            )
            if not already:
                value = evaluate(
                    f"({known.value} - {rel.offset}) / {rel.factor}", {}, log,
                    source=f"relation-inverse:{rel.provenance.source}",
                )
                out.append(
                    Quantity(
                        provenance=Provenance(source="synth/relation", sentence=rel.provenance.sentence),
                        entity=rel.standard, measure=measure, value=value, verb=rel.verb,
                        label=rel.standard_label or None,
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
                    source="synth/bare-age-anchor", sentence=p.provenance.sentence
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
        candidates = measures_by_entity.get(anchor.entity, set())
        if len(candidates) != 1:
            continue
        (measure,) = candidates
        if (anchor.entity, measure, anchor.verb) in known_by_verb:
            continue  # already has a quantity under this verb — would double it
        out.append(
            Quantity(
                provenance=Provenance(
                    source="synth/anchor-quantity", sentence=anchor.provenance.sentence
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
    from ..kernel.answer import _sign

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

    from .answer import _resolve_measure

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
        measure = _resolve_measure(fq.measure, store, reg)
        if measure is None:
            continue
        base = _pool_before(store, reg, fq.provenance.sentence, measure, log, "synth/fraction")
        if base is None:
            # "half OF IT": the measure word has no facts of its own — the
            # unique-measure principle resolves it when ONE pool is in play
            in_play = {
                q.measure for q in store.by_kind(Quantity)
                if q.provenance.sentence < fq.provenance.sentence
                and q.provenance.source != "synth/rest"
            }
            if len(in_play) == 1:
                (measure,) = in_play
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
    measures = {
        q.measure for q in store.by_kind(Quantity)
        if q.provenance.source != "synth/rest"
    }
    if len(measures) != 1:
        return out
    (measure,) = measures
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
    from .model import PartitionQuantity

    out: list[Fact] = []
    known_measures = {q.measure for q in store.by_kind(Quantity)}

    def _candidate_measure(sentence: int) -> str | None:
        candidates = {
            q.measure for q in store.by_kind(Quantity)
            if q.provenance.sentence < sentence
            and q.provenance.source != "synth/partition-membership"
        }
        return next(iter(candidates)) if len(candidates) == 1 else None

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
        holders = {q.entity for q in store.by_kind(Quantity) if q.measure == p.collection}
        if len(holders) != 1:
            continue
        (holder,) = holders
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


def _sum_constraint_synth(store: FactStore, reg: Registry, log: ArithmeticLog) -> list[Fact]:
    """sum-constraint linear systems (mining candidate sum-constraint-
    relations): "Anais has 30 more toys than Kamari. There are 160 toys
    altogether." — a Relation (subject = factor*standard + offset) plus a
    GroupTotal over the SAME measure jointly commit to a unique 2x2 linear
    solve neither fact alone determines:

        standard = (T - offset) / (1 + factor)
        subject  = T - standard

    Fires ONLY when exactly one Relation and exactly one GroupTotal share a
    measure, and NEITHER the relation's subject nor its standard already
    holds a Quantity of that measure (from anywhere — the ordinary
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
    from .answer import _resolve_measure_against

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
            and _resolve_measure_against(r.measure, {measure}, reg) == measure
        ]
        rels = exact_rels + bridged_rels
        if len(rels) != 1:
            continue  # more than one relation over this measure — ambiguous
        (rel,) = rels
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
                provenance=Provenance(source="synth/sum-constraint", sentence=rel.provenance.sentence),
                entity=rel.standard, measure=measure, value=standard_value, verb=rel.verb,
            )
        )
        out.append(
            Quantity(
                provenance=Provenance(source="synth/sum-constraint", sentence=rel.provenance.sentence),
                entity=rel.subject, measure=measure, value=subject_value, verb=rel.verb,
            )
        )
    return out


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

    Restricted to RAW-FOLD facts only (`provenance.source == "fold"`) for
    both CR and H — never another synth plugin's own output — so this stays
    a single-hop composition over the two facts the kernel already folds
    correctly, with a trivially stable fixpoint (raw fold facts never
    change across rounds; the 'already known' gate below stops the second
    round from re-deriving the same fact and colliding with it).

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

    USE-GATED, not existence-gated (the look #4-#7 invariant, docs/
    HANDOFF.md): emitted at `sentence=-1`, exactly the SynthRule datalog
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
    fold_quantities = [
        q for q in store.by_kind(Quantity) if q.provenance.source == "fold"
    ]
    known_measures_by_entity: dict[str, set[str]] = {}
    for q in store.by_kind(Quantity):
        known_measures_by_entity.setdefault(q.entity, set()).add(q.measure)

    rates_by_pair: dict[tuple[str, str], list[Quantity]] = {}
    for q in fold_quantities:
        rates_by_pair.setdefault((q.entity, q.measure), []).append(q)

    for (container, content), rates in rates_by_pair.items():
        if len(rates) != 1:
            continue  # ambiguous per-container rate — decline rather than guess
        (rate,) = rates
        for holder in fold_quantities:
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
            out.append(
                Quantity(
                    provenance=Provenance(source="synth/container-contents", sentence=-1),
                    entity=holder.entity, measure=content, value=value,
                    verb=holder.verb, occurrence=holder.occurrence, time=holder.time,
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
    _RATE_SOURCES = {"fold", "arithmetic/existential-premise-distributive"}
    out: list[Fact] = []
    known_group_totals = {gt.measure for gt in store.by_kind(GroupTotal)}

    rate_facts: set[int] = set()
    rates_by_pair: dict[tuple[str, str], list[Quantity]] = {}
    for q in store.by_kind(Quantity):
        if q.provenance.source not in _RATE_SOURCES or q.entity == q.measure:
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
        out.append(
            GroupTotal(
                provenance=Provenance(
                    source="synth/distributive-container-total", sentence=-1
                ),
                measure=content, value=value, verb=rate.verb,
            )
        )
    return out


PLUGINS: dict[str, Synthesizer] = {
    "synth/relation-to-quantity": _relations_synth,
    "synth/bare-age-anchor": _bare_age_anchor_synth,
    "synth/anchor-quantity": _anchor_quantity_synth,
    "synth/fraction-of-pool": _fraction_synth,
    "synth/rest-of-pool": _rest_synth,
    "synth/partition-of-collection": _partition_synth,
    "synth/partition-membership-quantity": _partition_membership_synth,
    "synth/partition-complement-quantity": _partition_complement_synth,
    "synth/sum-constraint": _sum_constraint_synth,
    "synth/container-contents": _container_contents_synth,
    "synth/distributive-container-total": _distributive_container_total_synth,
}


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
