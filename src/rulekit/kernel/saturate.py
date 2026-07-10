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
    out: list[Fact] = []
    # a relation anchors on ANY known quantity of the standard, but only an
    # existing STATE for the subject blocks resolution — the subject's own
    # EVENTS ("John lost 3") accumulate on top of the derived state
    quantities: dict[tuple[str, str], Quantity] = {}
    states: set[tuple[str, str]] = set()
    for q in store.by_kind(Quantity):
        quantities.setdefault((q.entity, q.measure), q)
        if q.is_state:
            states.add((q.entity, q.measure))
            quantities[(q.entity, q.measure)] = q
    for rel in store.by_kind(Relation):
        known = quantities.get((rel.standard, rel.measure))
        if known is None or (rel.subject, rel.measure) in states:
            continue
        value = evaluate(
            f"{rel.factor} * {known.value} + {rel.offset}", {}, log,
            source=f"relation:{rel.provenance.source}",
        )
        out.append(
            Quantity(
                provenance=Provenance(source="synth/relation", sentence=rel.provenance.sentence),
                entity=rel.subject, measure=rel.measure, value=value, verb=rel.verb,
            )
        )
    return out


PLUGINS: dict[str, Synthesizer] = {
    "synth/relation-to-quantity": _relations_synth,
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
