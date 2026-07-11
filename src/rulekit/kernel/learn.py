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
    Price,
    Provenance,
    Quantity,
    Rate,
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


def _rate_unit(reading: Reading, counted: Unit) -> Unit | None:
    """For the article rate form 'N X a/an/per U', the unit noun U."""
    units = reading.units
    try:
        i = units.index(counted)
    except ValueError:
        return None
    j = i + 1
    while j < len(units) and units[j].sense() == "punct":
        j += 1
    if j >= len(units):
        return None
    if units[j].sense() == "rate" and j + 1 < len(units) and units[j + 1].sense() == "noun":
        return units[j + 1]
    if units[j].sense() == "article":
        k = j + 1
        if k < len(units) and units[k].sense() == "noun":
            return units[k]
    return None


def _price_each_value(
    reading: Reading, counted: Unit, reg: Registry, stop_at_list_boundary: bool = False
) -> float | None:
    """'N ITEM at/for $PRICE each' — the PER-UNIT price, when a
    currency-valued noun sits between the counted item and a trailing
    'each' quantifier. Returns None for the plain distributive form ('2
    notebooks for EACH of his children'), which stays a silent skip.

    stop_at_list_boundary additionally stops at a comma: in a purchase
    list ("A, B at $X each") an unpriced FIRST item must not borrow a
    LATER item's price. Off by default — a bare comma is not a clause
    boundary for every verb's rate-marker scan (widening it broke an
    unrelated 'contains 8 bags ..., and ... each bag' holding elsewhere;
    ask only the purchase-conjunction caller opts in)."""
    units = reading.units
    try:
        i = units.index(counted)
    except ValueError:
        return None
    price: Unit | None = None
    for unit in units[i + 1 :]:
        if unit.sense() == "complementizer" or unit.surface in (".", "?", "!"):
            break
        if stop_at_list_boundary and unit.surface == ",":
            break
        if unit.sense() == "quantifier":
            return float(price.features["value"]) if price is not None else None
        if (
            price is None
            and unit.sense() == "noun"
            and unit.features.get("value_kind") == "count"
            and reg.word_in_category(unit.features.get("lemma", ""), "currency")
        ):
            price = unit
    return None


def _conjoined_purchase_items(
    reading: Reading, reg: Registry, first_item: Unit
) -> list[tuple[Unit, float | None]]:
    """Additional purchased items conjoined to `first_item` in a list like
    'A at $X each, B, and C at $Z each' — the verb's dobj obligation only
    binds the FIRST item (a general, pre-existing limitation); this walks
    the tail, segmenting on top-level commas/conjunctions, and returns
    (item, price-or-None) for every SIBLING found (first_item excluded).
    A segment's price counts only when that segment has its OWN 'each' —
    a flat-priced item with no 'each' returns (item, None), same as an
    unpriced one, so the caller's all-or-decline total stays honest."""
    units = reading.units
    try:
        i = units.index(first_item)
    except ValueError:
        return []
    conjuncts: list[tuple[Unit, float | None]] = []
    segment: list[Unit] = []
    # the FIRST segment (up to the first delimiter) is first_item's OWN
    # trailing clause ("at $10 each") — already handled by the caller, not
    # a new conjunct. Only segments after the first delimiter count.
    seen_delimiter = False

    def _flush(seg: list[Unit]) -> None:
        item = next(
            (
                u for u in seg
                if u.sense() == "noun" and u.features.get("value_kind") == "count"
            ),
            None,
        )
        if item is None:
            return
        price: Unit | None = None
        has_each = any(u.sense() == "quantifier" for u in seg)
        if has_each:
            for u in seg:
                if (
                    u is not item
                    and u.sense() == "noun"
                    and u.features.get("value_kind") == "count"
                    and reg.word_in_category(u.features.get("lemma", ""), "currency")
                ):
                    price = u
        conjuncts.append((item, float(price.features["value"]) if price is not None else None))

    for unit in units[i + 1 :]:
        if unit.sense() == "complementizer" or unit.surface in (".", "?", "!"):
            break
        if unit.surface == "," or unit.sense() == "conjunction":
            if seen_delimiter and segment:
                _flush(segment)
            segment = []
            seen_delimiter = True
            continue
        if not seen_delimiter:
            continue  # still inside first_item's own trailing clause
        segment.append(unit)
    if segment:
        _flush(segment)
    return conjuncts


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
    # DISTRIBUTIVE: "2 notebooks for EACH of his children" — a quantifier
    # after the counted noun (within this clause) makes the count
    # per-recipient, i.e. a rate. Scan right until a clause boundary.
    for unit in units[j:]:
        if unit.sense() in ("complementizer",) or unit.surface in (".", "?", "!"):
            break
        if unit.sense() == "quantifier":
            return True
    return False


def _sentence_time(reading: Reading, reg: Registry) -> str | None:
    """A sentence-initial time adjunct ('Last year he made…', 'This year…')
    scopes every fact the sentence yields. The time words are the
    `timeperiod` category — data. Returns the adjunct's fold, or None."""
    for unit in reading.units:
        sense = unit.sense()
        if sense == "verb":
            return None  # reached the predicate: no leading adjunct
        if (
            sense == "noun"
            and "value" not in unit.features
            and reg.word_in_category(
                unit.features.get("lemma", unit.features.get("fold", "")), "timeperiod"
            )
        ):
            idx = reading.units.index(unit)
            words = [
                u.features.get("fold", "")
                for u in reading.units[max(0, idx - 1) : idx + 1]
                if u.sense() not in ("punct",)
            ]
            return " ".join(words)
    return None


def learn(reading: Reading, reg: Registry) -> list[Fact]:
    facts: list[Fact] = []
    prov = Provenance(source="fold", sentence=reading.sentence_index)
    time_label = _sentence_time(reading, reg)

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
        is_purchase_verb = reg.word_in_category(verb_lemma, "purchase")
        if dobj is not None and _is_rate(reading, dobj):
            unit_noun = _rate_unit(reading, dobj)
            if (
                unit_noun is not None
                and dobj.features.get("value_kind") == "count"
                and dobj.sense() == "noun"
            ):
                # the article/per form is a RATE FACT ("$18 an hour"); it
                # never folds into holdings, but the rate-span consumer can
                # multiply it.
                facts.append(
                    Rate(
                        provenance=prov,
                        entity=_lemma(subject),
                        measure=_lemma(dobj),
                        per=_lemma(unit_noun),
                        value=float(dobj.features["value"]),
                        verb=verb_lemma,
                        occurrence=occurrence,
                    )
                )
                continue  # never a holding — no plain quantity from a rate
            price_value = (
                _price_each_value(
                    reading, dobj, reg, stop_at_list_boundary=is_purchase_verb
                )
                if dobj.features.get("value_kind") == "count" and dobj.sense() == "noun"
                else None
            )
            if price_value is None:
                continue  # the for-each distributive ("for EACH of his
                # children") still just skips — no fact, value unaccounted
            # "N ITEM at/for $PRICE each" — the ITEM is a genuine purchased
            # COUNT (unlike the day-rate case), so it falls through to the
            # normal condensed-count Quantity emission below; the price is
            # its own fact, read only when the purchase-total consumer
            # actually multiplies it (guards._fact_values_by_sentence).
            facts.append(
                Price(
                    provenance=prov,
                    item=_lemma(dobj),
                    value=price_value,
                    verb=verb_lemma,
                    occurrence=occurrence,
                )
            )
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
                    time=time_label,
                )
            )
            if is_purchase_verb:
                # "buys A at $X each, B, and C at $Z each" — the dobj
                # obligation only bound A; recover the conjoined siblings
                # and fold each as its own purchase (Quantity + Price
                # when that sibling has its own 'each').
                for item, price_value in _conjoined_purchase_items(reading, reg, dobj):
                    facts.append(
                        Quantity(
                            provenance=prov,
                            entity=_lemma(subject),
                            measure=_lemma(item),
                            value=float(item.features["value"]),
                            verb=verb_lemma,
                            occurrence=occurrence,
                            time=time_label,
                        )
                    )
                    if price_value is not None:
                        facts.append(
                            Price(
                                provenance=prov,
                                item=_lemma(item),
                                value=price_value,
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
                    time=time_label,
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
