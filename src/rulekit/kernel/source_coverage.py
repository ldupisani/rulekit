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
