"""Inspectable language coverage for consumers requiring a complete source.

Only grammatical articles/punctuation, explicitly consumed rule units, and
the caller's exact evidence footprint are covered. Numeric accounting and
which facts/assumptions are admissible remain separate consumer policies.
"""


def uncovered_units(reading, covered=()):
    """Return the actual unread units, not just a yes/no completeness flag."""
    covered = frozenset(covered)
    return tuple(unit for unit in reading.units
                 if unit.uid not in covered
                 and not unit.features.get("pattern_consumed")
                 and unit.sense() not in {"article", "punct"})


def uncovered_document_units(premises, question, question_covered=()):
    """Keep sentence-local identities: ask coverage never covers a premise."""
    return tuple((reading.sentence_index, unit)
                 for reading in (*premises, question)
                 for unit in uncovered_units(
                     reading, question_covered if reading is question else ()))


def covered_temporal_annotation(fact, premises, entity, periods):
    """A read predicate's temporal projection is metadata for its declared period.

    This never excuses an additional event: the predicate itself must already
    be consumed by a complete rule, and its period must be preserved by that
    rule's evidence. Callers still audit every numeric operand separately.
    """
    from .model import VerbalRelation

    if (not isinstance(fact, VerbalRelation) or not fact.polarity
            or fact.role not in {'temporal-point', 'temporal-duration'}
            or fact.entity != entity or (fact.provenance.sentence, fact.obj) not in periods):
        return False
    reading = next((reading for reading in premises if reading.sentence_index == fact.provenance.sentence), None)
    return reading is not None and any(
        fact.event == f's{reading.sentence_index}:u{unit.uid}'
        and unit.features.get('pattern_consumed') for unit in reading.units)


def membership_source_units(reading, fact, reg):
    """Exact footprint of a bare positive copular membership already folded.

    Extra modifiers, owners, labels and adjuncts are deliberately outside this
    footprint. A consumer still decides whether the membership is relevant.
    """
    from .reference_identity import reference_from_unit

    units = [u for u in reading.units if u.sense() not in {"article", "punct"}]
    if (len(units) != 3 or not fact.polarity or fact.provenance.assumption
            or fact.provenance.sentence != reading.sentence_index):
        return ()
    subject, verb, predicate = units
    subject_ref = reference_from_unit(subject)
    predicate_ref = reference_from_unit(predicate)
    if (not subject_ref.resolved or subject_ref.described
            or predicate_ref.described
            or subject_ref.head != fact.member or predicate_ref.head != fact.collection
            or not reg.word_in_category(verb.features.get("fold", ""), "copula")):
        return ()
    return tuple(u.uid for u in units)


def quantity_source_units(reading, fact, reg):
    """The exact subject/verb/counted-object footprint of an ordinary fold.

    Already consumed clauses may follow a coordinating conjunction. Modifiers,
    competing transactions, or incomplete references remain uncovered.
    """
    from .reference_identity import reference_from_unit

    if fact.provenance.source != "fold" or fact.provenance.sentence != reading.sentence_index:
        return ()
    units = list(uncovered_units(reading))
    if (len(units) == 4 and reg.word_in_category(
            units[-1].features.get("lemma", ""), "holder_list_conjunction")):
        units.pop()
    if len(units) != 3:
        return ()
    subject, verb, amount = units
    ref = reference_from_unit(subject)
    amount_ref = reference_from_unit(amount)
    if (not ref.resolved or ref.described or amount_ref.described
            or ref.head != fact.entity or amount_ref.head != fact.measure
            or verb.features.get("lemma") != fact.verb
            or amount.features.get("value_kind") != "count"
            or amount.features.get("value") != fact.value):
        return ()
    return tuple(u.uid for u in uncovered_units(reading))


def price_source_units(reading, fact, reg):
    """Complete simple item-price clause for a Price already read by the fold."""
    from .reference_identity import reference_from_unit

    units = [u for u in reading.units if u.sense() not in {"article", "punct"}]
    if (
        fact.provenance.source != "fold"
        or fact.provenance.sentence != reading.sentence_index
        or len(units) not in (3, 4)
    ):
        return ()
    item, verb, amount = units[:3]
    ref = reference_from_unit(item)
    if (
        not ref.resolved
        or ref.owner
        or ref.label
        or ref.head != fact.item
        or (item.features.get("qualifier") or None) != fact.qualifier
        or not reg.word_in_category(verb.features.get("lemma", ""), "price_verb")
        or not reg.word_in_category(
            amount.features.get("lemma", ""), "currency_measure"
        )
        or amount.features.get("value") != fact.value
        or item.features.get("value_kind") is not None
        or len(units) == 4
        and not reg.word_in_category(
            units[3].features.get("lemma", ""), "postpositive_distributive_quantifier"
        )
    ):
        return ()
    return tuple(u.uid for u in units)


def partitive_quantity_source_units(reading, fact, reg):
    """Footprint of an ordinary folded quantity with explicit partitive roles.

    Join by reader-bound identities, then check the stated value. Repeated
    indistinguishable phrases decline instead of selecting one by its amount.
    A coordinated object may inherit the one clause predicate and subject.
    """
    from .reference_identity import reference_from_unit

    def bound(unit, need):
        return next((ob.target for ob in unit.obligations()
                     if ob.need == need and hasattr(ob.target, "features")), None)

    if (fact.provenance.source != "fold" or fact.provenance.sentence != reading.sentence_index
            or fact.measure_ref is None or fact.content_ref is None):
        return ()
    phrases = []
    for prep in reading.units:
        if not reg.word_in_category(prep.features.get("lemma", ""), "partitive"):
            continue
        anchor, content = bound(prep, "anchor"), bound(prep, "object")
        if (anchor is not None and content is not None
                and reference_from_unit(anchor) == fact.measure_ref
                and reference_from_unit(content) == fact.content_ref):
            phrases.append((anchor, prep, content))
    if len(phrases) != 1:
        return ()
    anchor, prep, content = phrases[0]
    if anchor.features.get("value_kind") != "count" or anchor.features.get("value") != fact.value:
        return ()
    verbs = [u for u in reading.units if u.sense() == "verb"
             and u.features.get("lemma") == fact.verb
             and (subject := bound(u, "subject")) is not None
             and reference_from_unit(subject) == fact.entity_ref]
    direct = [verb for verb in verbs if bound(verb, "dobj") is anchor]
    link = None
    if len(direct) == 1:
        verb = direct[0]
    elif fact.segment is not None and len(verbs) == 1:
        verb = verbs[0]
        before = [u for u in reading.units[:reading.units.index(anchor)]
                  if u.sense() not in {"article", "punct"}]
        if not before or not reg.word_in_category(
                before[-1].features.get("lemma", ""), "holder_list_conjunction"):
            return ()
        link = before[-1]
    else:
        return ()
    return tuple(u.uid for u in (bound(verb, "subject"), verb, anchor, prep, content, link)
                 if u is not None)


def quantity_ledger_source_units(reading, facts, reg):
    """Exact ordinary SVO count list, including coordinated partitive objects.

    Consumers retain the folded Quantity roles. This adapter validates the
    whole list rather than treating an arbitrary co-occurring number as use.
    """
    from .reference_identity import ReferenceIdentity, reference_from_unit
    units = list(uncovered_units(reading))
    if not units:
        return ()
    if len(units) < 3 or not facts:
        return ()
    subject, verb, *objects = units
    actor = reference_from_unit(subject)
    if (not actor.resolved or verb.sense() != 'verb'
            or any(f.provenance.source != 'fold' or f.entity_ref != actor
                   or f.verb != verb.features.get('lemma')
                   or f.provenance.sentence != reading.sentence_index for f in facts)):
        return ()
    pending = list(facts)
    times = {f.time for f in facts}
    if times != {None}:
        if (len(times) != 1 or not objects
                or objects[-1].surface.casefold() != next(iter(times)).casefold()):
            return ()
        objects = objects[:-1]
    index = 0
    while index < len(objects):
        amount = objects[index]
        index += 1
        if amount.features.get('value_kind') != 'count':
            return ()
        content = None
        if index < len(objects) and reg.word_in_category(
                objects[index].features.get('lemma', ''), 'partitive'):
            index += 1
            if index == len(objects):
                return ()
            content = reference_from_unit(objects[index])
            index += 1
        matches = [f for f in pending if f.value == amount.features.get('value')
                   and (f.measure_ref or ReferenceIdentity(
                       f.measure.split('[', 1)[0],
                       qualifiers=(f.measure_qualifier,) if f.measure_qualifier else ()))
                       == reference_from_unit(amount)
                   and f.content_ref == content]
        if len(matches) != 1:
            return ()
        pending.remove(matches[0])
        if index < len(objects):
            if not reg.word_in_category(objects[index].features.get('lemma', ''),
                                        'holder_list_conjunction'):
                return ()
            index += 1
            if index == len(objects):
                return ()
    return tuple(u.uid for u in units) if not pending else ()


def purchase_purpose_roles(reading, reg):
    """A fully read controlled infinitive supplies intent, not a purchase event."""
    from .learn import _bound
    from .reference_identity import reference_from_unit
    verbs = [u for u in reading.units if u.sense() == 'verb']
    movement = [u for u in verbs if reg.word_in_category(u.features.get('lemma', ''), 'outing_motion_verb')]
    purchases = [u for u in verbs if reg.word_in_category(u.features.get('lemma', ''), 'purchase')]
    if len(verbs) != 2 or len(movement) != 1 or len(purchases) != 1 or uncovered_units(reading):
        return None
    actor = _bound(movement[0], 'subject')
    buyer = _bound(purchases[0], 'subject')
    item = _bound(purchases[0], 'dobj')
    if actor is None or buyer is None or item is None:
        return None
    actor_ref, buyer_ref, item_ref = map(reference_from_unit, (actor, buyer, item))
    if not actor_ref.resolved or actor_ref != buyer_ref or not item_ref.resolved:
        return None
    return actor_ref, item_ref
