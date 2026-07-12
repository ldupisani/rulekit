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
from .model import Fact, GroupTotal, Predication, Provenance, Quantity, Relation

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
    out: list[Fact] = []
    totals_by_measure: dict[str, list[GroupTotal]] = {}
    for gt in store.by_kind(GroupTotal):
        totals_by_measure.setdefault(gt.measure, []).append(gt)
    relations_by_measure: dict[str, list[Relation]] = {}
    for rel in store.by_kind(Relation):
        relations_by_measure.setdefault(rel.measure, []).append(rel)

    for measure, totals in totals_by_measure.items():
        if len(totals) != 1:
            continue  # more than one stated total for this measure — ambiguous
        (total,) = totals
        rels = relations_by_measure.get(measure, [])
        if len(rels) != 1:
            continue  # more than one relation over this measure — ambiguous
        (rel,) = rels
        if rel.subject == rel.standard or rel.factor == -1:
            continue  # self-referential or degenerate (terms cancel, not sum)
        holders = {q.entity for q in store.by_kind(Quantity) if q.measure == measure}
        if holders - {rel.subject, rel.standard}:
            continue  # a third entity holds this measure — never guess the span
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


PLUGINS: dict[str, Synthesizer] = {
    "synth/relation-to-quantity": _relations_synth,
    "synth/bare-age-anchor": _bare_age_anchor_synth,
    "synth/fraction-of-pool": _fraction_synth,
    "synth/rest-of-pool": _rest_synth,
    "synth/partition-of-collection": _partition_synth,
    "synth/partition-membership-quantity": _partition_membership_synth,
    "synth/partition-complement-quantity": _partition_complement_synth,
    "synth/sum-constraint": _sum_constraint_synth,
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
