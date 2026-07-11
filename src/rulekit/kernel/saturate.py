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
from dataclasses import dataclass
from typing import Callable, Protocol

from ..data.registry import Registry
from ..data.schemas import SynthRule
from .evaluate import ArithmeticLog, EvaluationError, evaluate
from .facts import FactStore
from .model import Fact, Provenance, Quantity, Relation

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
    for q in store.by_kind(Quantity):
        quantities.setdefault((q.entity, q.measure), q)
        by_verb.add((q.entity, q.measure, verb_key(q.verb)))
        measures_by_entity.setdefault(q.entity, set()).add(q.measure)
        if q.is_state:
            quantities[(q.entity, q.measure)] = q

    def anchor_measure(entity: str, measure: str) -> tuple[str, Quantity] | None:
        """The relation's stated measure resolved against ONE entity's own
        holdings — an EXACT match first, else (only for `interchangeable`
        categories, e.g. currency) the entity's unique same-category
        measure ('money' resolves to the anchor's own stated 'dollar').
        Ambiguous (two different currencies on the same entity) or
        unresolvable declines this relation, never guesses."""
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

    for rel in store.by_kind(Relation):
        # resolution is blocked when the target already has a quantity UNDER
        # THE RELATION'S OWN VERB — "Zig wrote 4× as many" plus "Zig wrote
        # 60" describe the SAME writing (re-deriving doubles it); a lose
        # event on top of a have-relation is a CHANGE and stays allowed
        resolved = anchor_measure(rel.standard, rel.measure)
        if resolved is not None:
            measure, known = resolved
            if (rel.subject, measure, verb_key(rel.verb)) not in by_verb:
                value = evaluate(
                    f"{rel.factor} * {known.value} + {rel.offset}", {}, log,
                    source=f"relation:{rel.provenance.source}",
                )
                out.append(
                    Quantity(
                        provenance=Provenance(source="synth/relation", sentence=rel.provenance.sentence),
                        entity=rel.subject, measure=measure, value=value, verb=rel.verb,
                    )
                )
                continue
        # INVERSE: the subject is known, the standard is not — solve
        # standard = (subject − offset) / factor ("If Zig wrote 60, and Zig
        # wrote four times as many as Flo…")
        resolved = anchor_measure(rel.subject, rel.measure)
        if (
            resolved is not None
            and rel.factor != 0
        ):
            measure, known = resolved
            if (rel.standard, measure, verb_key(rel.verb)) not in by_verb:
                value = evaluate(
                    f"({known.value} - {rel.offset}) / {rel.factor}", {}, log,
                    source=f"relation-inverse:{rel.provenance.source}",
                )
                out.append(
                    Quantity(
                        provenance=Provenance(source="synth/relation", sentence=rel.provenance.sentence),
                        entity=rel.standard, measure=measure, value=value, verb=rel.verb,
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
    unresolved collection."""
    from .model import PartitionQuantity

    out: list[Fact] = []
    known_measures = {q.measure for q in store.by_kind(Quantity)}
    for pq in store.by_kind(PartitionQuantity):
        if pq.collection in known_measures:
            continue  # already names a real measure — nothing to resolve
        candidates = {
            q.measure for q in store.by_kind(Quantity)
            if q.provenance.sentence < pq.provenance.sentence
        }
        if len(candidates) != 1:
            continue
        (measure,) = candidates
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


PLUGINS: dict[str, Synthesizer] = {
    "synth/relation-to-quantity": _relations_synth,
    "synth/fraction-of-pool": _fraction_synth,
    "synth/rest-of-pool": _rest_synth,
    "synth/partition-of-collection": _partition_synth,
    "synth/partition-membership-quantity": _partition_membership_synth,
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
