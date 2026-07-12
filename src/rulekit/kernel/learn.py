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
from .obligations import _crosses_clause_boundary


def _bound(unit: Unit, need: str) -> Unit | None:
    for ob in unit.obligations():
        if ob.need == need and ob.met and isinstance(ob.target, Unit):
            return ob.target
    return None


def _has_distributive_determiner(reading: Reading, noun: Unit) -> bool:
    """'Each pen costs $3' — a quantifier ('each'/'every'/...) whose own
    `collection` obligation resolves to THIS noun is a distributive
    determiner scoped over it, structurally identical to the trailing
    '$3 each' shape _is_rate already recognizes (same sense gate, opposite
    side of the noun). Reverse lookup mirrors `_negated`'s pattern: scan
    every unit's obligations for one bound TO this target, since the
    quantifier -> collection edge only runs quantifier-to-noun, never
    noun-to-quantifier."""
    for unit in reading.units:
        if _bound(unit, "collection") is noun:
            return True
    return False


def _is_measure_unit(noun: Unit, reg: Registry) -> bool:
    """A noun naming a KNOWN physical measure unit — one side of a
    `reg.conversions` pair (pound, gallon, ounce, ...; both directions are
    stored, so membership on either side is enough). Data-driven — never a
    Python word list; a made-up container noun ('box', 'bag') is never a
    member and stays out of scope for `_measure_partitive_anchor`."""
    lemma = _lemma(noun)
    return any(lemma in pair for pair in reg.conversions)


def _measure_partitive_anchor(reading: Reading, subject: Unit, reg: Registry) -> Unit | None:
    """'A pound of coffee beans costs $2.50' / '4 pounds of coffee beans
    cost $10 each' — a price_verb's subject binds (via the existing 'of'
    preposition's object obligation) to the ITEM noun, the same convenient
    resolution any partitive 'of' phrase already produces. But the price is
    stated PER the MEASURE noun the 'of' phrase anchors to ('pound'), not
    per item — the Price fact must be keyed on that measure so
    `_purchase_total`'s item-noun match (which already keys the purchase
    Quantity by the SAME measure noun — 'Jasmine bought 4 pounds of coffee
    beans' folds to measure='pound', unwidened since increment 10) finds
    it. Returns the anchor noun when a `partitive`-category preposition's
    object is exactly `subject` and its anchor names a known measure unit
    (`_is_measure_unit`) — never a made-up container noun, which stays a
    separate, ambiguous class out of scope here."""
    for unit in reading.units:
        if not reg.word_in_category(_lemma(unit), "partitive"):
            continue
        if _bound(unit, "object") is not subject:
            continue
        anchor = _bound(unit, "anchor")
        if anchor is not None and anchor.sense() == "noun" and _is_measure_unit(anchor, reg):
            return anchor
    return None


def _negated(reading: Reading, verb: Unit) -> bool:
    for unit in reading.units:
        for ob in unit.obligations():
            if ob.need == "negates" and ob.met and ob.target is verb:
                return True
    return False


def _clause_negated(reading: Reading, verb: Unit, reg: Registry) -> bool:
    """A negation-category token ('not', 'never', ...) in the SAME CLAUSE as
    `verb` means the verb's event/holding did not happen as the sentence's
    surface count states it — the Quantity fold declines this verb's
    contribution rather than fold a negated number as a real holding
    ("Tom does NOT have 5 apples" must not commit 5.0; the `negates`
    obligation above only covers the copula shape 'is not', not 'does not
    VERB', so this is a SEPARATE, clause-scoped check reusing the existing
    complementizer clause-boundary — never the whole sentence, so an
    unrelated negation in a different clause doesn't blank an otherwise
    fine fold on this verb).

    Decline-only: this never computes negated semantics, it only withholds
    the ordinary (positive) fold's contribution."""
    for unit in reading.units:
        lemma = unit.features.get("lemma", unit.features.get("fold", ""))
        if reg.word_in_category(lemma, "negation") and not _crosses_clause_boundary(
            reading, unit, verb
        ):
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


def _qualifier(unit: Unit) -> str | None:
    """The attributive modifier of a noun merged from ADJECTIVE+NOUN or
    NOUN+NOUN (condense.py's merge-attribute / merge-compound: "coconut
    trees", "mango trees"), if any — carried on Quantity facts SEPARATELY
    from `entity` (the bare lemma stays the identity everywhere it already
    worked, e.g. "the tree ... it ..." keeps folding into one entity
    exactly as before). Only facts.py's collision handling reads this, and
    only to split a genuine same-key VALUE conflict ("coconut tree" vs
    "mango tree") into two entities — never to change identity when there
    is no conflict. A second, independent qualifier field beside `owner`
    (increment 25's mirror) — a subject can carry both when nested
    ("Tom's red car"), each read only by its own ask/collision path."""
    if unit.sense() == "pronoun":
        antecedent = _bound(unit, "refers")
        if antecedent is not None:
            return antecedent.features.get("qualifier")
        return None
    return unit.features.get("qualifier")


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


def _compound_rate_span(reading: Reading, counted: Unit, reg: Registry) -> Unit | None:
    """'reads 8 pages in 20 minutes' — a COMPOUND rate stated as two
    numbers (an amount and an elapsed span) rather than the simple 'N ITEM
    a/an/per U' article form `_rate_unit` recognizes. Scans forward from
    the counted item, within the same clause, for a preposition in the
    pack-declared `span_preposition` category (structure, not a literal
    string — the 'per'->'rate' sense is the precedent: a word-specific
    fact belongs in the pack, never compared against in Python) that
    itself introduces a counted noun (the span); an intervening
    prepositional frame outside that category ("of a book") is simply not
    a match and the scan continues past it — a LATER, unrelated member
    (e.g. a location, "in the library") that fails the counted-noun test
    still returns None rather than searching further, the same definitive-
    or-decline caution as the rest of this module. A verb or clause
    boundary reached first means no compound span is stated here at all."""
    units = reading.units
    try:
        i = units.index(counted)
    except ValueError:
        return None
    for idx in range(i + 1, len(units)):
        unit = units[idx]
        if unit.sense() == "complementizer" or unit.surface in (".", "?", "!"):
            return None
        if unit.sense() == "verb":
            return None  # a second clause starts here
        if unit.sense() == "preposition" and reg.word_in_category(
            _lemma(unit), "span_preposition"
        ):
            j = idx + 1
            while j < len(units) and units[j].sense() == "article":
                j += 1
            if (
                j < len(units)
                and units[j].sense() == "noun"
                and units[j].features.get("value_kind") == "count"
            ):
                return units[j]
            return None
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
        if unit.sense() == "verb":
            # a second finite clause starts here (its own subject/verb, not
            # a sibling noun phrase in first_item's list) — stop WITHOUT
            # flushing the in-progress segment. Purchase-item lists almost
            # never coordinate a whole second clause before the period, but
            # state-verb sentences commonly do ("Sam has 3 apples, and
            # Kendall has 6 dimes"); walking into the second clause would
            # read ITS subject/dobj as a sibling of first_item, and
            # flushing an in-progress segment here would misattribute that
            # clause's own subject noun phrase ("...and her 6 dimes are on
            # the table") to first_item's entity instead of declining.
            segment = []
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


def _conjoined_bare_number_events(
    reading: Reading, reg: Registry, first_item: Unit
) -> list[float]:
    """'Vera ... sold 5 last week and 7 this week' — a further sibling of
    `_conjoined_purchase_items` for an EVENT verb whose sibling conjunct
    states no item noun of its own AT ALL: a bare, unmerged count VALUE
    (never condensed into a counted noun, unlike `first_item` itself),
    optionally trailing a bare temporal modifier ('this week', 'last
    month' — the `timeperiod` category, structure only, never a literal).
    Such a conjunct names no item because none IS stated — the only
    coherent reading is that it counts ANOTHER occurrence of the SAME item
    the verb's bound dobj (`first_item`) already counts, so the walker
    hands back its bare value for the caller to fold as another event
    Quantity under the head's own entity/measure/verb — inheriting, never
    inventing, a measure.

    Structural gate, no lexicon: a segment matches only when it holds
    EXACTLY one count-value unit whose own sense is 'value' (a genuinely
    NAMED item, however sparse-looking, is `_conjoined_purchase_items`'s
    job, not this one — this walker never fires where that one already
    would) and every noun-sense unit in the segment is a `timeperiod`
    category member (a bare temporal adjunct never disqualifies the
    conjunct; ANY other noun means a real item WAS stated and this walker
    declines that segment entirely, leaving it to the noun-bearing path).
    Zero or multiple bare values in a segment is an ambiguous shape and
    silently declines, same discipline as `_conjoined_purchase_items`."""
    units = reading.units
    try:
        i = units.index(first_item)
    except ValueError:
        return []
    values: list[float] = []
    segment: list[Unit] = []
    seen_delimiter = False

    def _flush(seg: list[Unit]) -> None:
        bare_values = [
            u
            for u in seg
            if u.sense() == "value" and u.features.get("value_kind") == "count"
        ]
        if len(bare_values) != 1:
            return
        other_nouns = [
            u
            for u in seg
            if u.sense() == "noun"
            and not reg.word_in_category(
                u.features.get("lemma", u.features.get("fold", "")), "timeperiod"
            )
        ]
        if other_nouns:
            return  # a real item WAS stated here — not this walker's class
        values.append(float(bare_values[0].features["value"]))

    for unit in units[i + 1 :]:
        if unit.sense() == "complementizer" or unit.surface in (".", "?", "!"):
            break
        if unit.sense() == "verb":
            # a second finite clause starts here — same caution as
            # `_conjoined_purchase_items`: never misattribute its subject.
            segment = []
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
    return values


def _has_event_polarity(verb_lemma: str, reg: Registry) -> bool:
    """True when `verb_lemma` carries a polarity-tagged category (acquire/
    lose and their subcategories: purchase, produce, receive, sell, ...) —
    the SAME strict-mode test answer.py's `_sign(strict=True)` applies
    downstream to decide whether an event Quantity can ever be signed.
    Mirrored here rather than imported (answer.py is the consumer layer,
    learn.py the fold) so the conjunct walker's gate can ask the identical
    question the fold will ask later: an UNTAGGED verb ('want', 'need' —
    deliberately unsignable per packs/core-english/categories/core.yaml)
    must keep declining exactly as it already does. Recovering conjunct
    siblings for a verb the fold can never sign would manufacture Quantity
    facts that only ever sit inert — harmless by construction, but exactly
    the kind of scope creep the polarity invariant exists to forbid, so the
    gate withholds them at the source instead."""
    for tag in reg.word_categories.get(verb_lemma, ()):
        for cat in reg.cat_ancestors(tag):
            if cat in reg.category_polarity:
                return True
    return False


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
        negated_clause = _clause_negated(reading, verb, reg)
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
            # different semantics, left alone). "Each ITEM costs $PRICE" —
            # the SAME distributive quantifier, but scoped over the subject
            # noun itself rather than trailing the price — is structurally
            # equivalent (_has_distributive_determiner) and gets the
            # identical Price fact. Either way 'cost' + a currency dobj is
            # NEVER a holding: a price statement always skips the generic
            # Quantity fallback below, priced or not.
            #
            # "A pound of coffee beans costs $2.50" / "4 pounds of coffee
            # beans cost $10 each" (mining candidate
            # modal-spend-measure-price): 'of' binds the subject to the
            # ITEM (coffee beans), never the MEASURE the price is actually
            # PER (pound) — `_measure_partitive_anchor` finds that measure
            # noun structurally. A BARE (uncounted) measure anchor is
            # itself the per-unit signal ("a pound", the indefinite
            # singular reading — no trailing 'each' exists to detect in
            # this shape at all); a COUNTED anchor ("4 pounds") still needs
            # the ordinary 'each'/distributive trigger above. Either way
            # the emitted Price is keyed on the MEASURE noun, not the item,
            # so it lines up with the purchase premise's own
            # Quantity.measure (unwidened, increment 10).
            measure_anchor = _measure_partitive_anchor(reading, subject, reg)
            is_bare_measure_price = (
                measure_anchor is not None
                and measure_anchor.features.get("value_kind") != "count"
            )
            if (
                (_is_rate(reading, dobj) and _rate_unit(reading, dobj) is None)
                or _has_distributive_determiner(reading, subject)
                or is_bare_measure_price
            ):
                price_item = (
                    _lemma(measure_anchor) if measure_anchor is not None else _lemma(subject)
                )
                price_item_qualifier = (
                    _qualifier(measure_anchor)
                    if measure_anchor is not None
                    else _qualifier(subject)
                )
                facts.append(
                    Price(
                        provenance=prov,
                        item=price_item,
                        qualifier=price_item_qualifier,
                        value=float(dobj.features["value"]),
                        verb=verb_lemma,
                        occurrence=occurrence,
                    )
                )
            continue
        is_copular_price = (
            verb_lemma == "be"
            and dobj_is_currency
            and subject.sense() == "noun"
            and subject.features.get("number") == "plural"
        )
        if (
            is_copular_price
            and _is_rate(reading, dobj)
            and _rate_unit(reading, dobj) is None
        ):
            # "ITEM(s) are $PRICE each" — the copular twin of the price_verb
            # branch above: 'be' (the state category) with a PLURAL common
            # noun subject and a currency dobj, followed by the same
            # distributive 'each' structure (_is_rate/_rate_unit UNWIDENED,
            # _rate_unit None ruling out a 'per NOUN' rate reading instead).
            # Emit the Price fact keyed on the subject and skip the fold
            # entirely for THIS shape only. Any 'be'+currency-dobj sentence
            # missing a piece of this gate (no 'each', singular subject, a
            # 'per NOUN' rate marker) is untouched — it falls through to the
            # existing state-verb Quantity/Membership/Predication path below,
            # exactly as before this change.
            facts.append(
                Price(
                    provenance=prov,
                    item=_lemma(subject),
                    qualifier=_qualifier(subject),
                    value=float(dobj.features["value"]),
                    verb=verb_lemma,
                    occurrence=occurrence,
                )
            )
            continue
        dobj_is_rate = dobj is not None and _is_rate(
            reading, dobj, stop_at_list_boundary=is_purchase_verb
        )
        dobj_is_counted_noun = (
            dobj is not None
            and dobj.features.get("value_kind") == "count"
            and dobj.sense() == "noun"
        )
        if not dobj_is_rate and dobj_is_counted_noun:
            compound_span = _compound_rate_span(reading, dobj, reg)
            if compound_span is not None and float(compound_span.features["value"]) != 0:
                # "reads 8 pages in 20 minutes" — a COMPOUND rate (an
                # amount over an elapsed span), rather than the simple
                # per-unit article form below. Same Rate fact kind, same
                # USE-GATED value-accounting discipline (guards.py's
                # rate_values + log.uses_value gate, not mere existence —
                # neither this branch nor the article one marks its units
                # `pattern_consumed`): the forward rate-span consumer
                # reads it going forward (value/per x span), the inverse
                # consumer (rate-span-inverse) reads it going backward
                # (a question-stated target ÷ value). Never a holding —
                # a compound rate is not a balance.
                numerator = float(dobj.features["value"])
                denominator = float(compound_span.features["value"])
                facts.append(
                    Rate(
                        provenance=prov,
                        entity=_lemma(subject),
                        measure=_lemma(dobj),
                        per=_lemma(compound_span),
                        value=numerator / denominator,
                        verb=verb_lemma,
                        occurrence=occurrence,
                        numerator=numerator,
                        denominator=denominator,
                    )
                )
                continue  # never a holding — no plain quantity from a compound rate
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
                    qualifier=_qualifier(dobj),
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
            # condensed counted noun ("3 apples") — a negated clause ("Tom
            # does NOT have 5 apples") declines this contribution entirely
            # rather than fold the stated count as a real holding.
            if not negated_clause:
                facts.append(
                    Quantity(
                        provenance=prov,
                        entity=_lemma(subject),
                        owner=_owner(subject),
                        qualifier=_qualifier(subject),
                        measure=_lemma(dobj),
                        measure_qualifier=_qualifier(dobj),
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
                            qualifier=_qualifier(dobj),
                            value=flat_price_value,
                            verb=verb_lemma,
                            occurrence=occurrence,
                        )
                    )
                if (
                    is_purchase_verb
                    or is_state
                    or (not is_state and _has_event_polarity(verb_lemma, reg))
                ):
                    # "buys A at $X each, B, and C at $Z each" (purchase
                    # verbs), "has A and B" / "owns X, Y, and Z" (state
                    # verbs), or "found 7 apples and 6 oranges" / "lost 3
                    # pens, 2 pencils, and a ruler" (any OTHER polarity-
                    # tagged event verb, acquire/lose and their
                    # subcategories) — the dobj obligation only bound the
                    # FIRST item; recover the conjoined siblings via the
                    # SAME segmentation increment 11 built for purchase
                    # lists and fold each as its own Quantity, signed
                    # downstream by the verb's own category polarity
                    # exactly like the first item already is. An event verb
                    # with NO polarity category ('want'/'need' — see
                    # _has_event_polarity) still declines: only a
                    # purchase verb's siblings ever emit a Price.
                    for item, item_qty, price_value in _conjoined_purchase_items(reading, reg, dobj):
                        facts.append(
                            Quantity(
                                provenance=prov,
                                entity=_lemma(subject),
                                owner=_owner(subject),
                                qualifier=_qualifier(subject),
                                measure=_lemma(item),
                                measure_qualifier=_qualifier(item),
                                value=item_qty,
                                verb=verb_lemma,
                                occurrence=occurrence,
                                time=time_label,
                            )
                        )
                        if is_purchase_verb and price_value is not None:
                            facts.append(
                                Price(
                                    provenance=prov,
                                    item=_lemma(item),
                                    qualifier=_qualifier(item),
                                    value=price_value,
                                    verb=verb_lemma,
                                    occurrence=occurrence,
                                )
                            )
                    if not is_state and _has_event_polarity(verb_lemma, reg):
                        # "sold 5 last week and 7 this week" — mining
                        # candidate event-goal-progress-inheritance: a
                        # sibling conjunct stating NO item noun of its own
                        # (bare number, optional bare temporal modifier)
                        # inherits `dobj`'s own measure — same entity/verb,
                        # signed downstream by the SAME category polarity as
                        # the first occurrence. Never fires where
                        # `_conjoined_purchase_items` already emitted a fact
                        # for the segment — see `_conjoined_bare_number_
                        # events`'s docstring for the mutual-exclusion gate.
                        for bare_value in _conjoined_bare_number_events(reading, reg, dobj):
                            facts.append(
                                Quantity(
                                    provenance=prov,
                                    entity=_lemma(subject),
                                    owner=_owner(subject),
                                    qualifier=_qualifier(subject),
                                    measure=_lemma(dobj),
                                    measure_qualifier=_qualifier(dobj),
                                    value=bare_value,
                                    verb=verb_lemma,
                                    occurrence=occurrence,
                                    time=time_label,
                                )
                            )
        elif flat_price_value is not None:
            # "a hat for $10" — a FLAT-priced purchase item with no
            # explicit count and no distributive 'each': a single unit at
            # the stated total price, so the purchase-total consumer's
            # sum-over-priced-quantities (qty=1 × price) covers it
            # unchanged. Order-independent: recover any conjoined siblings
            # exactly as the counted-dobj branch above does. A negated
            # clause declines this contribution, same as the counted case.
            if not negated_clause:
                facts.append(
                    Quantity(
                        provenance=prov,
                        entity=_lemma(subject),
                        owner=_owner(subject),
                        qualifier=_qualifier(subject),
                        measure=_lemma(dobj),
                        measure_qualifier=_qualifier(dobj),
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
                        qualifier=_qualifier(dobj),
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
                            qualifier=_qualifier(subject),
                            measure=_lemma(item),
                            measure_qualifier=_qualifier(item),
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
                                qualifier=_qualifier(item),
                                value=price_value,
                                verb=verb_lemma,
                                occurrence=occurrence,
                            )
                        )
        elif dobj is not None and dobj.uid in quantifies:
            # a value bound to dobj via a separate value unit ("has 5 of
            # them") — same negated-clause decline as the two branches above.
            if not negated_clause:
                value_unit = quantifies[dobj.uid]
                facts.append(
                    Quantity(
                        provenance=prov,
                        entity=_lemma(subject),
                        owner=_owner(subject),
                        qualifier=_qualifier(subject),
                        measure=_lemma(dobj),
                        measure_qualifier=_qualifier(dobj),
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
