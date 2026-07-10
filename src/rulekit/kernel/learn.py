"""Learn: read facts off the saturated obligation graph of one sentence.

This is the general fold's extraction side — no patterns, no vocabulary:
purely the bindings. A declarative sentence whose verb found its subject
(and object, and whose values found what they quantify) yields facts; what
didn't bind yields nothing (definitive-or-decline, localized).
"""

from __future__ import annotations

from ..data.registry import Registry
from .model import (
    Fact,
    Membership,
    Predication,
    Provenance,
    Quantity,
    Reading,
    Unit,
)


def _bound(unit: Unit, need: str) -> Unit | None:
    for ob in unit.obligations():
        if ob.need == need and ob.met and isinstance(ob.target, Unit):
            return ob.target
    return None


def _negated(reading: Reading, verb: Unit) -> bool:
    for unit in reading.units:
        for ob in unit.obligations():
            if ob.need == "negates" and ob.met and ob.target is verb:
                return True
    return False


def _lemma(unit: Unit) -> str:
    # a pronoun whose `refers` obligation bound cross-sentence speaks AS its
    # antecedent — the document loop's whole point
    if unit.sense() == "pronoun":
        antecedent = _bound(unit, "refers")
        if antecedent is not None:
            return antecedent.features.get("lemma", antecedent.features.get("fold", ""))
    return unit.features.get("lemma", unit.features.get("fold", unit.surface.lower()))


def _is_rate(reading: Reading, counted: Unit) -> bool:
    """'$10 an hour' / '20 hours a month' / '$2 per pound' — a counted noun
    followed by a rate marker (the `rate` sense) or by article+noun is a
    PER-UNIT RATE, not a holding. Rate machinery is unbuilt: emitting a
    plain quantity here is how a wage becomes a balance. Skip the fact and
    let value accounting decline."""
    units = reading.units
    try:
        i = units.index(counted)
    except ValueError:
        return False
    j = i + 1
    while j < len(units) and units[j].sense() == "punct":
        j += 1
    if j >= len(units):
        return False
    if units[j].sense() == "rate":
        return True
    if units[j].sense() == "article":
        k = j + 1
        if k < len(units) and units[k].sense() == "noun":
            return True
    return False


def learn(reading: Reading, reg: Registry) -> list[Fact]:
    facts: list[Fact] = []
    prov = Provenance(source="fold", sentence=reading.sentence_index)

    # value units that found what they quantify: value -> noun. Units a
    # pattern rule consumed are masked (their facts were already emitted with
    # the rule's own semantics — re-extracting duplicates them, the
    # SystemResult double-count bug).
    quantifies: dict[int, Unit] = {}  # noun uid -> value unit
    for unit in reading.units:
        if unit.features.get("pattern_consumed"):
            continue
        if unit.features.get("value_kind") == "count" and unit.sense() != "noun":
            target = _bound(unit, "quantifies")
            if target is not None:
                quantifies[target.uid] = unit

    for verb in reading.units:
        if verb.sense() != "verb":
            continue
        subject = _bound(verb, "subject")
        dobj = _bound(verb, "dobj")
        if subject is None:
            continue
        # an UNRESOLVED pronoun subject must not become a fact entity —
        # Quantity(entity='he') would silently poison combined sums; the
        # unmet refers obligation stays a reportable gap instead
        if subject.sense() == "pronoun" and _bound(subject, "refers") is None:
            continue
        polarity = not _negated(reading, verb)
        verb_lemma = _lemma(verb)

        consumed = verb.features.get("pattern_consumed") or (
            dobj is not None and dobj.features.get("pattern_consumed")
        )
        if consumed:
            continue
        is_state = reg.word_in_category(verb.features.get("fold", ""), "state")
        occurrence = None if is_state else reading.sentence_index
        if dobj is not None and _is_rate(reading, dobj):
            continue  # a rate, not a holding — no fact, value stays unaccounted
        if dobj is not None and dobj.features.get("value_kind") == "count" and dobj.sense() == "noun":
            # condensed counted noun ("3 apples")
            facts.append(
                Quantity(
                    provenance=prov,
                    entity=_lemma(subject),
                    measure=_lemma(dobj),
                    value=float(dobj.features["value"]),
                    verb=verb_lemma,
                    occurrence=occurrence,
                )
            )
        elif dobj is not None and dobj.uid in quantifies:
            value_unit = quantifies[dobj.uid]
            facts.append(
                Quantity(
                    provenance=prov,
                    entity=_lemma(subject),
                    measure=_lemma(dobj),
                    value=float(value_unit.features["value"]),
                    verb=verb_lemma,
                    occurrence=occurrence,
                )
            )
        elif verb_lemma == "be" and dobj is not None and dobj.sense() == "noun":
            facts.append(
                Membership(
                    provenance=prov,
                    member=_lemma(subject),
                    collection=_lemma(dobj),
                    polarity=polarity,
                )
            )
        elif dobj is not None:
            facts.append(
                Predication(
                    provenance=prov,
                    subject=_lemma(subject),
                    verb=verb_lemma,
                    dobj=_lemma(dobj),
                    polarity=polarity,
                )
            )
        else:
            facts.append(
                Predication(
                    provenance=prov,
                    subject=_lemma(subject),
                    verb=verb_lemma,
                    polarity=polarity,
                )
            )
    return facts
