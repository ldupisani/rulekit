"""Forward item-class anaphora in actual, comparison-connected clauses.

This is not universal noun coreference. A qualified comparison establishes an
item class for its participants and predicate. A later bare counted object
may refer to that class only when the prior context leaves one interpretation.
No amount, nearest-mention choice, future qualifier, or ask supplies identity.
"""

from dataclasses import replace

from . import deixis
from .model import ItemClassReference, Predication, Provenance, Quantity, Relation, Unit
from .reference_identity import ReferenceIdentity, reference_from_unit, reference_pool, resolve_reference
from .temporal import FUTURE, normalize_perspective


def _actual_clause(reading, predicate, reg):
    if reading is None or reading.assumption:
        return None
    verbs = [unit for unit in reading.units if unit.sense() == "verb"]
    if len(verbs) != 1 or verbs[0].features.get("lemma") != predicate:
        return None
    # The first supported class is an unscoped, single actual clause. These
    # structural exclusions also keep explicit whole totals out of anaphora.
    excluded = ("group_total_marker", "group_total_quantifier", "negation",
                "deictic_temporal_marker", "named_calendar_period", "time_measure")
    if any(unit.sense() in ("modal", "conjunction") or any(
        reg.word_in_category(unit.features.get("lemma", unit.features.get("fold", "")), category)
        for category in excluded) for unit in reading.units):
        return None
    return verbs[0]


def _bound(unit, need):
    return next((ob.target for ob in unit.obligations()
                 if ob.need == need and isinstance(ob.target, Unit)), None)


def _classes(store, quantity):
    """Current typed antecedent/rival inventory, shared by binding and use."""
    pool = reference_pool(store)
    actor = resolve_reference(quantity.entity_ref, pool)
    if actor is None:
        return {}
    candidates = {}
    for relation in store.by_kind(Relation):
        if (not relation.measure_qualifier or relation.measure != quantity.measure.split("[", 1)[0]
                or relation.standard_qualifier
                or relation.standard_ref.head == relation.measure
                or relation.verb != quantity.verb
                or relation.provenance.sentence >= quantity.provenance.sentence
                or relation.provenance.assumption or relation.provenance.distributive
                or relation.provenance.source.startswith("synth/")
                or relation.subject_offset or relation.standard_offset
                or relation.provenance.temporal_perspective != quantity.provenance.temporal_perspective):
            continue
        participants = {resolve_reference(ref, pool)
                        for ref in (relation.subject_ref, relation.standard_ref)}
        if None not in participants and actor in participants and len(participants) == 2:
            candidates.setdefault(relation.measure_qualifier, set()).add(relation.provenance)
    if not candidates:
        return {}
    for fact in [*store.by_kind(Quantity), *store.by_kind(Predication)]:
        reference = fact.entity_ref if isinstance(fact, Quantity) else fact.subject_ref
        measure = fact.measure if isinstance(fact, Quantity) else fact.dobj
        if (fact.provenance.sentence >= quantity.provenance.sentence
                or fact.provenance.assumption or fact.provenance.source.startswith("synth/")
                or fact.verb != quantity.verb or measure is None
                or measure.split("[", 1)[0] != quantity.measure.split("[", 1)[0]
                or resolve_reference(reference, pool) != actor):
            continue
        if isinstance(fact, Predication) and fact.polarity:
            # Its quantity/class is not fully represented. It may introduce
            # a rival; neither recency nor a matching head can erase it.
            return {}
        if isinstance(fact, Quantity) and fact.measure_qualifier:
            candidates.setdefault(fact.measure_qualifier, set()).add(fact.provenance)
    return candidates


def bind_item_classes(store, readings, reg, log):
    """Annotate direct quantities with inspectable links before saturation."""
    store.item_reference_clauses = frozenset()
    if not any(relation.measure_qualifier for relation in store.by_kind(Relation)):
        return
    by_sentence = {reading.sentence_index: reading for reading in readings}
    clauses = {}
    def actual(source, predicate):
        key = (source.sentence, predicate)
        if key not in clauses:
            clauses[key] = _actual_clause(by_sentence.get(source.sentence), predicate, reg)
        return clauses[key]

    store.item_reference_clauses = frozenset(
        fact.provenance for fact in store.facts if isinstance(fact, (Quantity, Relation))
        and actual(fact.provenance, fact.verb) is not None
        and normalize_perspective(fact.provenance.temporal_perspective, reg) != FUTURE)
    pool = reference_pool(store)
    quantities = store.by_kind(Quantity)
    for quantity in quantities:
        if (quantity.measure_qualifier or quantity.item_reference is not None
                or quantity.time is not None or quantity.provenance.assumption
                or quantity.provenance.distributive
                or quantity.provenance.source.startswith("synth/")):
            continue
        predicate = actual(quantity.provenance, quantity.verb)
        if predicate is None:
            continue
        subject, item = _bound(predicate, "subject"), _bound(predicate, "dobj")
        actor = resolve_reference(quantity.entity_ref, pool)
        if (subject is None or item is None or actor is None
                or resolve_reference(reference_from_unit(subject), pool) != actor
                or item.features.get("lemma") != quantity.measure
                or item.features.get("value") is None or item.features.get("qualifier")):
            continue
        perspective = normalize_perspective(quantity.provenance.temporal_perspective, reg)
        if perspective == FUTURE:
            continue
        candidates = _classes(store, quantity)
        if not candidates or any(source not in store.item_reference_clauses
                                 for sources in candidates.values() for source in sources):
            continue
        winner = deixis.resolve(
            [deixis.Referent(deixis.DISCOURSE, ReferenceIdentity(quantity.measure, qualifiers=(qualifier,)),
                             payload=tuple(sorted(set(sources), key=lambda p: (p.sentence, p.source))))
             for qualifier, sources in sorted(candidates.items())],
            deixis.Origo(sentence=quantity.provenance.sentence), deixis.constant,
            dimension=deixis.DISCOURSE, journal=log.journal, source="discourse/item-class-reference")
        if winner is None:
            continue
        link = ItemClassReference(winner.key, quantity.entity_ref, quantity.verb,
                                  quantity.provenance, winner.payload)
        store.facts[store.facts.index(quantity)] = replace(quantity, item_reference=link)


def project_item_reference(quantity, store):
    """Apply only a coherent recorded link to a nonmutating arithmetic view."""
    link = quantity.item_reference
    if link is None:
        return quantity
    classes = _classes(store, quantity)
    valid = (quantity in store.facts and isinstance(link, ItemClassReference)
             and _valid_reference(link.item) and _valid_reference(link.participant)
             and _valid_source(link.target)
             and isinstance(link.antecedents, tuple)
             and all(_valid_source(source) for source in link.antecedents)
             and link.item.resolved and link.item.head == quantity.measure.split("[", 1)[0]
             and len(link.item.qualifiers) == 1 and not link.item.owner and not link.item.label
             and link.participant == quantity.entity_ref and link.predicate == quantity.verb
             and link.target == quantity.provenance and not link.target.assumption
             and link.target in store.item_reference_clauses
             and set(link.antecedents) <= store.item_reference_clauses
             and quantity.time is None and not link.target.distributive
             and bool(link.antecedents) and all(
                 source.sentence < link.target.sentence and not source.assumption
                 for source in link.antecedents)
             and quantity.measure_qualifier in (None, link.item.qualifiers[0])
             and set(classes) == set(link.item.qualifiers)
             and classes[link.item.qualifiers[0]] == set(link.antecedents))
    if not valid:
        return replace(quantity, entity_ref=replace(quantity.entity_ref, resolved=False))
    # A validated view is already explicit. Removing the link from the view
    # prevents later narrower folds from needing antecedent facts they no
    # longer contain; the original store retains the full immutable link.
    return replace(quantity, measure_qualifier=link.item.qualifiers[0], item_reference=None)


def _valid_reference(reference):
    try:
        return (isinstance(reference, ReferenceIdentity) and reference.resolved
                and ReferenceIdentity.from_dict(reference.to_dict()) == reference)
    except (AttributeError, TypeError, ValueError, KeyError):
        return False


def _valid_source(source):
    return (isinstance(source, Provenance) and isinstance(source.source, str)
            and type(source.sentence) is int and source.sentence >= 0
            and (source.decision_seq is None or type(source.decision_seq) is int)
            and all(type(value) is bool for value in
                    (source.distributive, source.container_count, source.assumption))
            and (source.temporal_perspective is None or isinstance(source.temporal_perspective, str)))
