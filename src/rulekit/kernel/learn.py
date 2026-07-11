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


def _owner(unit: Unit) -> str | None:
    """The possessive owner of a noun merged from "OWNER 's NOUN" (condense
    .py's merge-possessive), if any — carried on Quantity facts SEPARATELY
    from `entity` (the bare lemma stays the identity everywhere it already
    worked, e.g. "Tom's dog ... the dog ..." keeps folding into one entity
    exactly as before). Only facts.py's collision handling reads this, and
    only to split a genuine same-key VALUE conflict ("Kennedy's house" vs
    "Benedict's house") into two entities — never to change identity when
    there is no conflict."""
    if unit.sense() == "pronoun":
        antecedent = _bound(unit, "refers")
        if antecedent is not None:
            return antecedent.features.get("owner")
        return None
    return unit.features.get("owner")


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
) -> list[tuple[Unit, float, float | None]]:
    """Additional purchased items conjoined to `first_item` in a list like
    'A at $X each, B, and C at $Z each' — the verb's dobj obligation only
    binds the FIRST item (a general, pre-existing limitation); this walks
    the tail, segmenting on top-level commas/conjunctions, and returns
    (item, quantity, price-or-None) for every SIBLING found (first_item
    excluded). A segment's price counts only when that segment has its
    OWN 'each' — a flat-priced COUNTED item with no 'each' and a
    quantity other than exactly 1 returns (item, qty, None), same as an
    unpriced one, so the caller's all-or-decline total stays honest (a
    flat 'for $N' on a qty > 1 item is genuinely ambiguous — total or
    each? — and stays unbuilt). A SINGULAR item — quantity exactly 1,
    whether spelled with an explicit '1' or an indefinite article that
    merged no count at all ("1 computer game for $90" / "a hat for
    $10") — has no such ambiguity: 'for $N' can only mean the one unit's
    own price, so it returns (item, 1.0, price) whenever a currency noun
    is present with no distributive 'each' — the flat-priced-singleton
    class, same mechanism as the top-level dobj case in `learn()`."""
    units = reading.units
    try:
        i = units.index(first_item)
    except ValueError:
        return []
    conjuncts: list[tuple[Unit, float, float | None]] = []
    segment: list[Unit] = []
    # the FIRST segment (up to the first delimiter) is first_item's OWN
    # trailing clause ("at $10 each") — already handled by the caller, not
    # a new conjunct. Only segments after the first delimiter count.
    seen_delimiter = False

    def _flush(seg: list[Unit]) -> None:
        has_each = any(u.sense() == "quantifier" for u in seg)
        item = next(
            (
                u for u in seg
                if u.sense() == "noun"
                and u.features.get("value_kind") == "count"
                and not reg.word_in_category(u.features.get("lemma", ""), "currency")
            ),
            None,
        )
        if item is not None:
            qty = float(item.features["value"])
            price: Unit | None = None
            if has_each:
                for u in seg:
                    if (
                        u is not item
                        and u.sense() == "noun"
                        and u.features.get("value_kind") == "count"
                        and reg.word_in_category(u.features.get("lemma", ""), "currency")
                    ):
                        price = u
            elif qty == 1.0:
                # a SINGULAR counted item ("1 computer game for $90") with
                # no 'each' — flat total is unambiguous at quantity 1.
                price = next(
                    (
                        u for u in seg
                        if u is not item
                        and u.sense() == "noun"
                        and u.features.get("value_kind") == "count"
                        and reg.word_in_category(u.features.get("lemma", ""), "currency")
                    ),
                    None,
                )
            conjuncts.append((
                item,
                qty,
                float(price.features["value"]) if price is not None else None,
            ))
            return
        if has_each:
            return  # a per-unit shape with no explicit count is unbuilt — skip
        # no explicitly-counted item: a bare singular noun ("a hat") plus
        # a flat currency price with no 'each' is a single flat-priced
        # unit — quantity 1, price the flat total.
        bare_item = next(
            (
                u for u in seg
                if u.sense() == "noun"
                and u.features.get("value_kind") != "count"
                and not reg.word_in_category(u.features.get("lemma", ""), "currency")
            ),
            None,
        )
        if bare_item is None:
            return
        price = next(
            (
                u for u in seg
                if u.sense() == "noun"
                and u.features.get("value_kind") == "count"
                and reg.word_in_category(u.features.get("lemma", ""), "currency")
            ),
            None,
        )
        if price is None:
            return
        conjuncts.append((bare_item, 1.0, float(price.features["value"])))

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


def _is_rate(
    reading: Reading, counted: Unit, stop_at_list_boundary: bool = False
) -> bool:
    """'$10 an hour' / '20 hours a month' / '$2 per pound' — a counted noun
    followed by a rate marker (the `rate` sense) or by article+noun is a
    PER-UNIT RATE, not a holding. Rate machinery is unbuilt: emitting a
    plain quantity here is how a wage becomes a balance. Skip the fact and
    let value accounting decline.

    stop_at_list_boundary additionally stops the DISTRIBUTIVE scan at a
    bare comma or conjunction: in a purchase list ("a hat for $10 and 3
    shirts at $5 each") the second item's trailing 'each' must never leak
    backward and misclassify the FIRST, flat-priced item as a rate. Off by
    default — mirrors _price_each_value's own flag (increment 11 lesson:
    a shared clause-boundary scan must never be widened globally; only the
    purchase-conjunction caller opts in)."""
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
        if stop_at_list_boundary and (
            unit.surface == "," or unit.sense() == "conjunction"
        ):
            break
        if unit.sense() == "quantifier":
            return True
    return False


def _flat_purchase_price(reading: Reading, item: Unit, reg: Registry) -> float | None:
    """'a hat for $10' — a FLAT TOTAL price for a purchased item that
    carries no explicit count (a bare singular noun, quantity 1 by the
    article's own reading), stated via a preposition anchored to the item
    itself. Anchoring on the preposition's resolved 'anchor' obligation
    (structural binding, not position) is what keeps a beneficiary/
    duration/exchange 'for' ("bought it for his brother", "worked for 3
    hours") from misfiring: those anchor to something else, or their
    object isn't a currency noun — either way this returns None and the
    item declines exactly as it did before this fact existed. A
    'each' immediately trailing the price is the PER-UNIT shape
    (_price_each_value/_is_rate's job already) and is left alone here to
    avoid double-counting."""
    for prep in reading.units:
        if prep.sense() != "preposition":
            continue
        if _bound(prep, "anchor") is not item:
            continue
        obj = _bound(prep, "object")
        if (
            obj is None
            or obj.sense() != "noun"
            or obj.features.get("value_kind") != "count"
            or not reg.word_in_category(obj.features.get("lemma", ""), "currency")
        ):
            continue
        units = reading.units
        try:
            k = units.index(obj) + 1
        except ValueError:
            k = len(units)
        while k < len(units) and units[k].sense() == "punct":
            k += 1
        if k < len(units) and units[k].sense() == "quantifier":
            continue  # "$10 each" anchored here — a per-unit price, not flat
        return float(obj.features["value"])
    return None


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
        is_price_verb = reg.word_in_category(verb_lemma, "price_verb")
        dobj_is_currency = (
            dobj is not None
            and dobj.features.get("value_kind") == "count"
            and dobj.sense() == "noun"
            and reg.word_in_category(_lemma(dobj), "currency")
        )
        if is_price_verb and dobj_is_currency:
            # "ITEM cost(s) $PRICE each" — the ITEM is the SUBJECT (not the
            # object of buy, increment 10's shape) and 'cost' carries the
            # price itself as its dobj. The trailing distributive 'each'
            # (_is_rate's existing quantifier scan) is what makes this a
            # PER-UNIT price rather than an unbuilt lump-sum/rate reading
            # (_rate_unit not None means a 'per NOUN' marker instead —
            # different semantics, left alone). Either way 'cost' + a
            # currency dobj is NEVER a holding: a price statement always
            # skips the generic Quantity fallback below, priced or not.
            if _is_rate(reading, dobj) and _rate_unit(reading, dobj) is None:
                facts.append(
                    Price(
                        provenance=prov,
                        item=_lemma(subject),
                        value=float(dobj.features["value"]),
                        verb=verb_lemma,
                        occurrence=occurrence,
                    )
                )
            continue
        dobj_is_rate = dobj is not None and _is_rate(
            reading, dobj, stop_at_list_boundary=is_purchase_verb
        )
        if dobj_is_rate:
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
        dobj_is_count = (
            dobj is not None
            and dobj.features.get("value_kind") == "count"
            and dobj.sense() == "noun"
        )
        flat_price_value = None
        if (
            is_purchase_verb
            and not dobj_is_rate
            and dobj is not None
            and dobj.sense() == "noun"
            and (not dobj_is_count or float(dobj.features["value"]) == 1.0)
        ):
            # a SINGULAR purchased item — no explicit count at all ("a
            # hat") or an explicit quantity of exactly 1 ("1 computer
            # game") — makes a flat 'for $N' unambiguous (qty 1, so
            # total == each); qty > 1 stays unbuilt (total-vs-each is
            # genuinely ambiguous there).
            flat_price_value = _flat_purchase_price(reading, dobj, reg)
        if dobj_is_count:
            # condensed counted noun ("3 apples")
            facts.append(
                Quantity(
                    provenance=prov,
                    entity=_lemma(subject),
                    owner=_owner(subject),
                    measure=_lemma(dobj),
                    value=float(dobj.features["value"]),
                    verb=verb_lemma,
                    occurrence=occurrence,
                    time=time_label,
                )
            )
            if flat_price_value is not None:
                facts.append(
                    Price(
                        provenance=prov,
                        item=_lemma(dobj),
                        value=flat_price_value,
                        verb=verb_lemma,
                        occurrence=occurrence,
                    )
                )
            if is_purchase_verb:
                # "buys A at $X each, B, and C at $Z each" — the dobj
                # obligation only bound A; recover the conjoined siblings
                # and fold each as its own purchase (Quantity + Price
                # when that sibling has its own 'each', or a flat 'for
                # $N' price on a bare singular sibling).
                for item, item_qty, price_value in _conjoined_purchase_items(reading, reg, dobj):
                    facts.append(
                        Quantity(
                            provenance=prov,
                            entity=_lemma(subject),
                            owner=_owner(subject),
                            measure=_lemma(item),
                            value=item_qty,
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
        elif flat_price_value is not None:
            # "a hat for $10" — a FLAT-priced purchase item with no
            # explicit count and no distributive 'each': a single unit at
            # the stated total price, so the purchase-total consumer's
            # sum-over-priced-quantities (qty=1 × price) covers it
            # unchanged. Order-independent: recover any conjoined siblings
            # exactly as the counted-dobj branch above does.
            facts.append(
                Quantity(
                    provenance=prov,
                    entity=_lemma(subject),
                    owner=_owner(subject),
                    measure=_lemma(dobj),
                    value=1.0,
                    verb=verb_lemma,
                    occurrence=occurrence,
                    time=time_label,
                )
            )
            facts.append(
                Price(
                    provenance=prov,
                    item=_lemma(dobj),
                    value=flat_price_value,
                    verb=verb_lemma,
                    occurrence=occurrence,
                )
            )
            for item, item_qty, price_value in _conjoined_purchase_items(reading, reg, dobj):
                facts.append(
                    Quantity(
                        provenance=prov,
                        entity=_lemma(subject),
                        owner=_owner(subject),
                        measure=_lemma(item),
                        value=item_qty,
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
                    owner=_owner(subject),
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
