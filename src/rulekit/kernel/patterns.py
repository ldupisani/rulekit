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
from dataclasses import dataclass, field

from ..data.registry import Registry
from ..data.schemas import AskRule, MatchToken, PatternRule
from .evaluate import ArithmeticLog, EvaluationError, evaluate
from .model import (
    Before,
    Discount,
    Fact,
    FractionQuantity,
    Goal,
    GroupTotal,
    Membership,
    PartitionQuantity,
    Predication,
    Provenance,
    Quantity,
    Rate,
    Reading,
    Relation,
    RestQuantity,
    Subset,
    Unit,
)

SKIPPABLE_SENSES = {"article", "punct"}

_FACT_CLASSES = {
    "quantity": Quantity,
    "relation": Relation,
    "membership": Membership,
    "subset": Subset,
    "predication": Predication,
    "before": Before,
    "fraction_quantity": FractionQuantity,
    "rest_quantity": RestQuantity,
    "partition_quantity": PartitionQuantity,
    "goal": Goal,
    "group_total": GroupTotal,
    "rate": Rate,
    "discount": Discount,
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


def _slot_ok(unit: Unit, token: MatchToken, reg: Registry) -> bool:
    if token.type is not None:
        t = token.type
        sense = unit.sense()
        kind = unit.features.get("value_kind")
        if t == "number":
            return kind == "count"
        if t == "fraction":
            return kind == "fraction"
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
            return sense == "noun" and unit.features.get("qualifier") is not None
        if t == "plural":
            return sense == "noun" and unit.features.get("number") == "plural"
        if t == "counted":
            return sense == "noun" and kind == "count"
        if t == "verb":
            return sense == "verb"
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


def _lemma_of(unit: Unit) -> str:
    # a pronoun whose `refers` bound cross-sentence speaks AS its antecedent
    if unit.sense() == "pronoun":
        for ob in unit.obligations():
            if ob.need == "refers" and ob.met and isinstance(ob.target, Unit):
                return ob.target.features.get(
                    "lemma", ob.target.features.get("fold", "")
                )
    return unit.features.get("lemma", unit.features.get("fold", unit.surface.lower()))


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
    for token in tokens:
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
            i += 1
        if i >= len(units):
            return None
        unit = units[i]
        if token.lit is not None:
            if unit.features.get("fold") != token.lit:
                return None
        else:
            if not _slot_ok(unit, token, reg):
                return None
            name = token.slot
            if name in slots and _lemma_of(slots[name]) != _lemma_of(unit):
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
    reading: Reading, tokens: list[MatchToken], reg: Registry, limit: int = 8
) -> list[Match]:
    """ALL non-overlapping leftmost matches — a compound sentence ("X picked
    12 more than Y, and Y picked 5 less than Z") yields one match per
    clause; taking only the first would leave the rest to the naive fold."""
    units = reading.units
    out: list[Match] = []
    start = 0
    while start < len(units) and len(out) < limit:
        matched_here = None
        for begin in range(start, len(units)):
            slots: dict[str, Unit] = {}
            consumed: list[int] = []
            end = _try_match_at(units, begin, tokens, reg, slots, consumed)
            if end is not None:
                matched_here = (Match(rule=None, slots=slots, consumed=tuple(consumed)), end)  # type: ignore[arg-type]
                break
        if matched_here is None:
            break
        out.append(matched_here[0])
        start = matched_here[1]
    return out


def _check_where(
    rule: PatternRule, slots: dict[str, Unit], reading: Reading, reg: Registry
) -> bool:
    for pred in rule.where:
        if pred.same_lemma is not None:
            lemmas = {_lemma_of(slots[s]) for s in pred.same_lemma if s in slots}
            if len(lemmas) > 1:
                return False
        if pred.distinct is not None:
            # (lemma, label) pairs, not bare lemma alone — mining candidate
            # labeled-entity-relations: "Jar B has 12 more marbles than jar
            # A" bare-folds who/std to the SAME lemma 'jar' (the label
            # lives in a separate feature, condense.py merge-label), so a
            # bare-lemma-only distinct check wrongly read this as the
            # self-referential "X compares to itself" case every `distinct:
            # [who, std]` guard exists to block, and silently declined
            # every labeled relation. Two unlabeled units (label=None on
            # both sides, the overwhelming common case) compare exactly as
            # before — (lemma, None) == (lemma, None) still collides, so
            # every existing distinct check's behavior is unchanged; this
            # only additionally distinguishes a pair that share a lemma AND
            # carry two DIFFERENT non-null labels.
            values = [
                (_lemma_of(slots[s]), slots[s].features.get("label"))
                for s in pred.distinct if s in slots
            ]
            if len(values) != len(set(values)):
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


def _slot_value(unit: Unit, attr: str | None) -> str:
    if attr == "surface":
        return unit.surface
    if attr == "value":
        v = unit.features.get("value")
        return str(v) if v is not None else ""
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
            raise EvaluationError(f"rule {rule_id}: emit references unbound slot {name!r}")
        return _slot_value(slots[name], attr)
    if not numeric:
        # a string with embedded templates
        return _TEMPLATE.sub(lambda mm: _slot_value(slots[mm.group(1)], mm.group(2)), raw)
    # numeric expression: slot names are variables; sign(x) precomputed
    expr = _SIGN.sub(lambda mm: str(_polarity_of(slots[mm.group(1)], reg)), raw)
    expr = _TEMPLATE.sub(lambda mm: mm.group(1), expr)  # allow {n} in expressions too
    env = {
        name: float(u.features["value"])
        for name, u in slots.items()
        if "value" in u.features
    }
    return evaluate(expr, env, log, source=rule_id)


_NUMERIC_FIELDS = {"value", "factor", "offset", "fraction", "numerator", "denominator"}


def _build_fact(
    emit_fields: dict, fact_kind: str, slots: dict[str, Unit], reg: Registry,
    provenance: Provenance, log: ArithmeticLog | None, rule_id: str,
) -> Fact:
    cls = _FACT_CLASSES[fact_kind]
    kwargs = {}
    for key, raw in emit_fields.items():
        kwargs[key] = _resolve_field(raw, slots, reg, key in _NUMERIC_FIELDS, log, rule_id)
    if cls in (Quantity, FractionQuantity, RestQuantity) and "occurrence" not in kwargs:
        # a rule-emitted quantity is an event unless its verb is stative
        verb = kwargs.get("verb", "have")
        if not reg.word_in_category(verb, "state") and verb not in ("have", "be"):
            kwargs["occurrence"] = provenance.sentence
    return cls(provenance=provenance, **kwargs)


def rule_specificity(rule: PatternRule, reg: Registry) -> tuple[int, int, int]:
    """(required tokens, Σ category gate DEPTHS, where-count). Computed,
    never authored — a narrower category (pet ⊂ animal) scores strictly
    higher, which is what makes narrowing the conflict lever."""
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
        # trigger prefilter: every literal must be present
        lits = {t.lit for t in seq if t.lit is not None}
        if not lits <= sentence_folds:
            continue
        for m in match_all(reading, seq, reg):
            m.rule = rule
            m.specificity = specificity(m, reg)
            if not _check_where(rule, m.slots, reading, reg):
                continue
            provenance = Provenance(source=rule.id, sentence=reading.sentence_index)
            facts = [
                _build_fact(e.fields, e.fact, m.slots, reg, provenance, log, rule.id)
                for e in rule.emits
            ]
            results.append(RuleMatchResult(match=m, facts=facts))
    return results


def match_ask(
    reading: Reading, reg: Registry
) -> tuple[AskRule, dict[str, str], Match] | None:
    """Match question shapes; the MOST SPECIFIC matching ask wins (max
    consumed units — a longer match read more of the question), with id
    order as the deterministic tie-break. Re-landed alone from the reverted
    increment 8 per docs/negative-results.md."""
    best: tuple[AskRule, dict[str, str], Match] | None = None
    for ask in reg.asks:  # sorted by id — deterministic tie-break
        seq = ask.match["question"]
        m = match_sequence(reading, seq, reg)
        if m is None:
            continue
        resolved = {}
        for key, raw in ask.resolves.items():
            try:
                resolved[key] = _TEMPLATE.sub(
                    lambda mm: _slot_value(m.slots[mm.group(1)], mm.group(2)), raw
                )
            except KeyError:
                # the template references an OPTIONAL slot that didn't bind
                # ("verb: {verb}" with the opt-group absent) — omit the key
                # and let the consumer's default apply
                continue
        if best is None or len(m.consumed) > len(best[2].consumed):
            best = (ask, resolved, m)
    return best
