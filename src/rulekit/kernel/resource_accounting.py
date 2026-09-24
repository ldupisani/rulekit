"""Compose account phrases and report incomplete resource events.

The reader owns attachment and event completeness. Arithmetic consumers see
account endpoints, line items, and explicit issues, never shopping syntax.
"""

from __future__ import annotations

from .model import (
    Expenditure, Provenance, ResourceAccountingIssue, ResourceAllocation,
    ResourceBalance, PurchaseTotal,
)


def _participant_account_owner(head, reading, reg):
    """Personal accounts cannot inherit a non-personal possessive binding.

    The wider discourse binder also serves objects and organizations. This
    consumer's person-held account class must retain its narrower boundary.
    """
    uid = head.features.get("owner_ref_uid")
    if uid is None:
        return True
    determiner = reading.unit(uid)
    return reg.word_in_category(determiner.features.get("fold", ""), "animate_possessive_determiner")


def account_complement(reading, marker, reg):
    """Read a governed account NP, including a separate possessive pronoun.

    Returns its head, optional amount, resolved owner and final unit index.
    No search crosses another phrase to find a convenient account noun.
    """
    from .learn import _bound, _lemma

    units = reading.units
    index = units.index(marker) + 1
    while index < len(units) and units[index].sense() == "article":
        index += 1
    if index >= len(units):
        return None
    first = units[index]
    owner = ""
    if reg.word_in_category(first.features.get("fold", ""), "possessive_determiner"):
        if first.sense() == "pronoun" and _bound(first, "refers") is None:
            return None
        owner = _lemma(first)
        index += 1
    if index >= len(units):
        return None
    amount = None
    if (units[index].features.get("value_kind") == "count"
            and reg.word_in_category(_lemma(units[index]), "currency_measure")):
        amount = units[index]
        index += 1
    if index >= len(units):
        return None
    head = units[index]
    if (head.sense() != "noun" or head.features.get("value_kind")
            or not reg.word_in_category(_lemma(head), "resource_budget_noun")
            or _bound(marker, "object") not in (first, head)):
        return None
    owners = {v for v in (head.features.get("owner"), owner,
                         amount.features.get("owner") if amount else "") if v}
    if len(owners) > 1 or not _participant_account_owner(head, reading, reg) or (
        amount is not None and not _participant_account_owner(amount, reading, reg)
    ):
        return None
    owner = next(iter(owners), "")
    if amount is None and index + 2 < len(units):
        prep, possible = units[index + 1:index + 3]
        if (prep.sense() == "preposition" and reg.word_in_category(_lemma(prep), "partitive")
                and _bound(prep, "object") is possible
                and possible.features.get("value_kind") == "count"
                and reg.word_in_category(_lemma(possible), "currency_measure")):
            amount = possible
            index += 2
    return head, amount, owner, index


def allocation_attachments(reading, allocations, reg, expenses=()):
    """Yield (phrase, predicate, participant, owner) only for a unique attachment.

    Direct-object possession and category-licensed adjuncts share the account
    phrase. A noun anchor is accepted only through an already bound predicate
    object; no nearest-person or nearest-location fallback is permitted.
    """
    from .learn import (
        _bound, _clause_negated, _lemma, _matching_adposition_roles,
        _temporal_governing_verb, _temporal_relation_subject,
    )
    from .obligations import _crosses_clause_boundary

    for phrase in allocations:
        head = next((u for u in reading.units if str(u.span[0]) == phrase.head_span), None)
        amount = next((u for u in reading.units if str(u.span[0]) == phrase.amount_span), None)
        if head is None or amount is None or not _participant_account_owner(head, reading, reg) or not _participant_account_owner(amount, reading, reg):
            continue
        owners = {v for v in (phrase.owner, phrase.amount_owner) if v}
        if len(owners) > 1:
            continue
        owner = next(iter(owners), "")
        candidates = []
        for verb in reading.units:
            if (verb.sense() == "verb" and _bound(verb, "dobj") in (head, amount)
                    and reg.word_in_category(_lemma(verb), "possession_state")):
                candidates.append((verb, _bound(verb, "subject"), None))
        for marker in reading.units:
            if marker.sense() != "preposition":
                continue
            complement = account_complement(reading, marker, reg)
            if complement is None or complement[0] is not head or complement[1] is not amount:
                continue
            # The marker must introduce the entire NP, not be its internal
            # amount complement. Source spans work for both amount orders.
            if marker.span[0] >= min(head.span[0], amount.span[0]):
                continue
            verb = _temporal_governing_verb(reading, marker)
            if verb is None:
                # A complete transaction can already have read intervening
                # price/supplier complements. Join its explicit account link
                # rather than guessing a verb across those noun anchors.
                event_ids = {e.event for e in expenses
                             if e.account == phrase.account and e.account_qualifier == phrase.qualifier
                             and e.account_owner == owner and e.account_span == phrase.head_span}
                if len(event_ids) == 1:
                    verb = reading.unit(next(iter(event_ids)))
            if verb is None:
                continue
            roles = _matching_adposition_roles(_lemma(marker), head, verb, reg)
            if roles != ["allocation-context"]:
                continue
            candidates.append((verb, _temporal_relation_subject(reading, marker, verb), marker))
        if len(candidates) != 1:
            continue
        verb, subject, marker = candidates[0]
        if subject is None or (
            subject.sense() == "pronoun" and _bound(subject, "refers") is None
        ):
            continue
        if subject.sense() not in ("name", "pronoun") and not reg.word_in_category(
            _lemma(subject), "animate"
        ):
            continue
        if _clause_negated(reading, verb, reg) or any(
            u.sense() == "modal" and not _crosses_clause_boundary(reading, u, verb)
            for u in reading.units
        ):
            continue
        # Explicit ownership beats an adjunct's subject, including when it
        # contradicts that subject. Retain the conflict for the scope gate.
        yield phrase, verb, subject, owner


def purchase_collection_contains(collection, item, reg):
    """Typed collections constrain their items; generic ones still need goods.

    This licence belongs to a shopping scope, not to noun identity globally.
    An arbitrary uncounted noun must not become an ignorable introduction.
    """
    if not reg.word_in_category(collection, "purchase_collection_noun"):
        return False
    category = ("ownable_quantity_object"
                if reg.word_in_category(collection, "generic_purchase_collection_noun")
                else collection)
    return reg.word_in_category(item, category)


def purchase_context_error(contexts, expenses, reg):
    """A leading collective activity may summarize one buyer's later ledger.

    This is a category-backed elaboration link, not permission to ignore an
    unknown purchase. The complete progressive grammar supplies the context;
    every line must be a later actual purchase within its declared collection.
    """
    if not contexts:
        return None
    if len(contexts) != 1 or not expenses:
        return "a purchase collection needs one introduction and a subsequent ledger"
    context = contexts[0]
    if (context.place or context.provenance.assumption
            or not reg.word_in_category(context.verb, "purchase")
            or not reg.word_in_category(context.measure, "purchase_collection_noun")
            or context.entity_ref.owner or context.entity_ref.qualifiers
            or context.entity_ref.label or not context.entity_ref.resolved
            or any(e.entity != context.entity or e.basis != "purchase"
                   or e.provenance.sentence <= context.provenance.sentence
                   or e.provenance.assumption
                   or not purchase_collection_contains(context.measure, e.item, reg)
                   for e in expenses)):
        return "purchase lines do not elaborate the same buyer's introductory collection"
    return None


def compose_resource_accounts(store, premises, reg):
    """Build balances, then materialize shared completeness diagnostics."""
    from .learn import _bound, _lemma
    from .model import Price, QuantityEventContext

    allocations = list(store.by_kind(ResourceAllocation))
    expenses = list(store.by_kind(Expenditure))
    closed_account = bool(allocations or store.by_kind(ResourceBalance) or store.by_kind(PurchaseTotal))
    if not closed_account and not any(e.cost_reference for e in expenses):
        return
    for reading in premises:
        phrases = [a for a in allocations if a.provenance.sentence == reading.sentence_index]
        sentence_expenses = [e for e in expenses if e.provenance.sentence == reading.sentence_index]
        for phrase, verb, subject, owner in allocation_attachments(reading, phrases, reg, sentence_expenses):
            store.admit(ResourceBalance(
                provenance=Provenance(source="inference/allocation-attachment",
                                      sentence=reading.sentence_index,
                                      assumption=reading.assumption),
                entity=_lemma(subject), account=phrase.account, owner=owner,
                qualifier=phrase.qualifier, stage="opening", measure=phrase.measure,
                value=phrase.value, allocation_span=phrase.head_span, event=verb.uid,
            ))

    balances = list(store.by_kind(ResourceBalance))
    events = {(e.provenance.sentence, e.event) for e in expenses}
    contexts = [c for c in store.by_kind(QuantityEventContext)
                if not c.place and reg.word_in_category(c.verb, "purchase")]
    context_error = purchase_context_error(contexts, expenses, reg)
    for reading in premises:
        transaction_sentence = closed_account or any(
            e.provenance.sentence == reading.sentence_index for e in expenses
        )
        def issue(unit, reason, *, domain="resource"):
            store.admit(ResourceAccountingIssue(
                provenance=Provenance(source="inference/resource-completeness",
                                      sentence=reading.sentence_index),
                position=unit.uid, reason=reason, domain=domain,
            ))

        for unit in reading.units:
            lemma = _lemma(unit)
            if transaction_sentence and reg.word_in_category(lemma, "transaction_adjustment_noun"):
                issue(unit, "unscoped-price-adjustment")
            if reg.word_in_category(lemma, "resource_budget_noun") and not _participant_account_owner(unit, reading, reg):
                issue(unit, "owner-reference")
            if transaction_sentence and (unit.sense() in ("negator", "modal") or reg.word_in_category(lemma, "negation")):
                issue(unit, "nonactual")
            if transaction_sentence and unit.sense() == "conjunction" and not any(
                reg.word_in_category(lemma, cat)
                for cat in ("holder_list_conjunction", "contrastive_conjunction")
            ):
                issue(unit, "alternative")
            if unit.sense() != "verb":
                continue
            if reg.word_in_category(lemma, "purchase_request"):
                issue(unit, "unsettled-request")
            event = reg.word_in_category(lemma, "purchase") or reg.word_in_category(lemma, "spend_verb")
            subject, obj = _bound(unit, "subject"), _bound(unit, "dobj")
            contextual = not context_error and unit.features.get("pattern_consumed") and any(
                c.provenance.sentence == reading.sentence_index and c.verb == lemma
                and subject is not None and c.entity == _lemma(subject)
                and obj is not None and c.measure == _lemma(obj) for c in contexts
            )
            if event and not contextual and (reading.sentence_index, unit.uid) not in events:
                issue(unit, "unread-event")
            balance_verb = obj is not None and any(
                b.stage == "closing" and b.provenance.sentence == reading.sentence_index
                and reg.word_in_category(lemma, "remaining_balance_state")
                and _lemma(obj) == b.measure and obj.features.get("value") == b.value
                for b in balances
            )
            allocation_verb = obj is not None and any(
                b.stage == "opening" and b.provenance.sentence == reading.sentence_index
                and b.event == unit.uid
                and a.head_span == b.allocation_span
                and str(obj.span[0]) in (a.head_span, a.amount_span)
                for b in balances for a in allocations
                if a.provenance.sentence == reading.sentence_index
            )
            balance_background = (
                not event and obj is not None and not obj.features.get("value_kind")
                and any(reg.word_in_category(lemma, category)
                        for category in ("possession_state", "periodic_income_verb"))
                and any(reg.word_in_category(_lemma(obj), category)
                        for category in ("currency", "income_resource_noun"))
            )
            if reg.word_in_category(lemma, "divide") or (
                not event and obj is not None
                and (reg.word_in_category(_lemma(obj), "currency") or balance_background)
                and not balance_verb and not allocation_verb
                and not (reg.word_in_category(lemma, "price_verb") and any(
                    p.provenance.sentence == reading.sentence_index for p in store.by_kind(Price)
                ))
            ):
                issue(unit, "additional-change", domain="balance" if balance_background else "resource")


def purchase_background_facts(store, total):
    """Partition non-quantitative context before an explicit transaction.

    This is deliberately narrower than a general relevance engine. Identity,
    location, ordinary predicates and incomplete cash holdings stay in the
    store but are not operands of a fixed purchase-cost equation. Expenditures,
    price conditions and facts inside/after that transaction are never hidden.
    Numeric completeness remains the caller's responsibility.
    """
    from .model import LocationEvent, Membership, Predication, VerbalRelation

    background = []
    for fact in store.facts:
        if fact.provenance.sentence >= total.provenance.sentence or fact.provenance.assumption:
            continue
        if (isinstance(fact, (Membership, Predication))
                or isinstance(fact, VerbalRelation) and fact.role == "spatial-location"
                or isinstance(fact, LocationEvent) and fact.effect in {"holds", "not-holds"}
                or isinstance(fact, ResourceAccountingIssue) and fact.domain == "balance"):
            background.append(fact)
    return tuple(background)
