"""Item-targeted currency costs, including coordinated complements.

This supplements the generic fold and supplies its coordinated currency events.
Only a fully read amount + governed target is a cost. Vocabulary and additive
coordination permissions are owned by categories, not by this scan.
"""

from __future__ import annotations

from dataclasses import replace

from ..data.registry import Registry
from .model import Expenditure, Provenance, PurchaseTotal, Reading


def learn_purchase_totals(reading, reg):
    """A fronted currency complement scopes one actual purchase predicate.

    Only the complete initial marker + amount + subject + finite predicate
    frame licenses this total. A trailing item price or a proposed purchase
    cannot become a transaction-wide amount.
    """
    from .learn import _bound, _clause_negated, _lemma
    from .patterns import is_bare_referent, is_finite_verb_form

    units = [u for u in reading.units if u.sense() not in {"article", "punct"}]
    if len(units) < 5:
        return []
    prep, amount, subject, verb = units[:4]
    if (prep.sense() != "preposition"
            or not reg.word_in_category(_lemma(prep), "transaction_price_preposition")
            or amount.features.get("value_kind") != "count"
            or not reg.word_in_category(_lemma(amount), "currency_measure")
            or verb.sense() != "verb" or not reg.word_in_category(_lemma(verb), "purchase")
            or not is_finite_verb_form(verb.features.get("fold", ""), _lemma(verb), reg)
            or _bound(verb, "subject") is not subject
            or not is_bare_referent(subject) or _clause_negated(reading, verb, reg)
            or (subject.sense() == "pronoun" and _bound(subject, "refers") is None)
            or subject.sense() not in {"name", "pronoun"}):
        return []
    return [PurchaseTotal(
        Provenance("fold:fronted-purchase-total", reading.sentence_index,
                   assumption=reading.assumption),
        _lemma(subject), _lemma(amount), float(amount.features["value"]), amount.uid, verb.uid,
    )]


def _coordinated_finite_clause(reading, index, reg):
    """A new predicate closes the item list, not the surrounding document.

    Its own expenditure or resource-change checks still apply. An unpriced
    noun continuation is deliberately not a new finite clause.
    """
    from .learn import _lemma
    from .patterns import is_finite_verb_form

    units = reading.units
    while index < len(units) and units[index].surface == ",":
        index += 1
    if index >= len(units) or not any(reg.word_in_category(_lemma(units[index]), cat)
                                     for cat in ("holder_list_conjunction", "contrastive_conjunction")):
        return False
    index += 1
    if index < len(units) and units[index].sense() in {"name", "pronoun"}:
        index += 1
    return (index < len(units) and units[index].sense() == "verb"
            and is_finite_verb_form(units[index].features.get("fold", ""), _lemma(units[index]), reg))


def _relative_purchase_price(reading, index, reg):
    """A local relative price clause; never a unit-price declaration."""
    from .learn import _lemma
    from .patterns import is_finite_verb_form

    units = reading.units
    if index + 2 >= len(units) or units[index].sense() not in {"complementizer", "wh_which"}:
        return None
    verb, factor = units[index + 1:index + 3]
    if (verb.sense() != "verb" or not reg.word_in_category(_lemma(verb), "price_verb")
            or not is_finite_verb_form(verb.features.get("fold", ""), _lemma(verb), reg)
            or factor.features.get("value_kind") not in {"fraction", "multiplier"}
            or factor.features.get("requires_count")):
        return None
    index += 3
    while index < len(units) and units[index].sense() == "article":
        index += 1
    if index >= len(units) or not reg.word_in_category(_lemma(units[index]), "price_anaphor"):
        return None
    index += 1
    if index >= len(units) or not reg.word_in_category(_lemma(units[index]), "partitive"):
        return None
    index += 1
    while index < len(units) and units[index].sense() == "article":
        index += 1
    if index >= len(units):
        return None
    reference = units[index]
    if (reference.sense() != "noun" or reference.features.get("value_kind")
            or reference.features.get("owner")):
        return None
    return index + 1, dict(
        cost_reference=_lemma(reference),
        cost_reference_qualifier=reference.features.get("qualifier") or "",
        cost_factor=float(factor.features["value"]), cost_factor_position=factor.uid,
    )


def _transaction_tail(reading, verb, index, reg, *, priced=False, counted=None):
    """Read complete, category-licensed transaction complements in either order.

    The same routine handles an unpriced purchase and an explicit cost. No
    unrecognized PP is thrown away, including a unit-price or purpose tail.
    """
    from .learn import _bound, _lemma, _matching_adposition_roles, _price_each_value
    from .resource_accounting import account_complement

    units = reading.units
    fields = {}
    while index < len(units):
        marker = units[index]
        if reg.word_in_category(_lemma(marker), "transaction_channel"):
            if "channel" in fields:
                return None
            fields["channel"] = _lemma(marker)
            index += 1
            continue
        if marker.sense() in ("punct", "conjunction"):
            break
        if marker.sense() != "preposition":
            return None
        account = account_complement(reading, marker, reg)
        if account and reg.word_in_category(_lemma(marker), "transaction_account_preposition"):
            if "account" in fields:
                return None
            head, allocation_amount, owner, end = account
            if allocation_amount is not None and not (
                head.features.get("pattern_consumed") and allocation_amount.features.get("pattern_consumed")
            ):
                return None
            fields.update(account=_lemma(head), account_qualifier=head.features.get("qualifier") or "",
                          account_owner=owner, account_span=str(head.span[0]))
            index = end + 1
            continue
        obj = _bound(marker, "object")
        if obj is None:
            return None
        j = units.index(obj)
        if j <= index or any(u.sense() != "article" for u in units[index + 1:j]):
            return None
        roles = _matching_adposition_roles(_lemma(marker), obj, verb, reg)
        if roles == ["supplier"] and not obj.features.get("value_kind"):
            if "supplier" in fields:
                return None
            fields.update(supplier=_lemma(obj), supplier_qualifier=obj.features.get("qualifier") or "")
        elif (not priced and reg.word_in_category(_lemma(verb), "purchase")
              and (reg.word_in_category(_lemma(marker), "transaction_price_preposition")
                   or (counted is not None and reg.word_in_category(
                       _lemma(marker), "transaction_unit_price_preposition")))
              and obj.features.get("value_kind") == "count"
              and reg.word_in_category(_lemma(obj), "currency_measure")):
            if "value" in fields or "unit_price" in fields:
                return None
            if counted is not None:
                # Reuse the ordinary purchase reader's unit-price recognition,
                # but require its quantifier to close THIS price complement.
                price = _price_each_value(reading, counted, reg, stop_at_list_boundary=True)
                if (j + 1 < len(units) and units[j + 1].sense() == "quantifier"
                        and price == float(obj.features["value"])):
                    fields.update(unit_price=price, quantity=float(counted.features["value"]),
                                  quantity_position=counted.uid, measure=_lemma(obj), position=obj.uid)
                    quantifier = units[j + 1]
                    obligations = [replace(ob, target=counted) if ob.need == "collection" else ob
                                   for ob in quantifier.obligations()]
                    if obligations != quantifier.obligations():
                        reading.record("bind-price-unit", quantifier, {"obligations": obligations},
                                       "the explicit per-unit price quantifies this purchased lot")
                    j += 1
                elif reg.word_in_category(_lemma(marker), "transaction_price_preposition"):
                    fields.update(value=float(obj.features["value"]), measure=_lemma(obj), position=obj.uid,
                                  lot_quantity=float(counted.features["value"]), lot_position=counted.uid,
                                  lot_measure=_lemma(counted))
                else:
                    return None
            else:
                fields.update(value=float(obj.features["value"]), measure=_lemma(obj), position=obj.uid)
        else:
            return None
        index = j + 1
        # Numeric tokenization may retain a list comma on its amount token.
        if obj.surface.endswith(","):
            break
    return index, fields


def learn_expenditures(reading: Reading, reg: Registry) -> list[Expenditure]:
    from .learn import _bound, _clause_negated, _lemma
    from .obligations import _crosses_clause_boundary
    from .patterns import is_bare_referent

    units = reading.units
    out: list[Expenditure] = []
    for verb in units:
        event_start = len(out)
        if verb.sense() != "verb":
            continue
        if reg.word_in_category(_lemma(verb), "purchase_request"):
            # An older pack may also classify this lemma as acquisition.
            # That does not establish an actual transaction for this ledger.
            continue
        purchase = reg.word_in_category(_lemma(verb), "purchase")
        if not purchase and not reg.word_in_category(_lemma(verb), "spend_verb"):
            continue
        if purchase and verb.features.get("pattern_consumed"):
            continue
        subject = _bound(verb, "subject")
        amount = _bound(verb, "dobj")
        if subject is None or amount is None:
            continue
        if subject.sense() == "pronoun" and _bound(subject, "refers") is None:
            continue
        if _clause_negated(reading, verb, reg) or any(
            u.sense() == "modal" and not _crosses_clause_boundary(reading, u, verb)
            for u in units
        ):
            continue
        i = units.index(amount)
        if purchase:
            # Record the referent even without a stated cost. The ordinary
            # fold still owns its quantity/price semantics; this is only an
            # uncertainty record for a later closed-account calculation.
            complete = False
            while i < len(units):
                target = units[i]
                if target.sense() != "noun" or target.features.get("value_kind") not in (None, "count"):
                    break
                counted = target if target.features.get("value_kind") == "count" else None
                j = i + 1
                lot = {}
                if (reg.word_in_category(_lemma(target), "purchase_lot_measure")
                        and j < len(units) and reg.word_in_category(_lemma(units[j]), "partitive")):
                    head = target
                    complement = _bound(units[j], "object")
                    if (complement is None or complement.sense() != "noun"
                            or complement.features.get("value_kind") or complement.features.get("owner")):
                        break
                    target = complement
                    j = units.index(target) + 1
                    lot = dict(lot_measure=_lemma(head),
                               lot_quantity=float(head.features["value"]) if counted else None,
                               lot_position=head.uid if counted else -1)
                if reg.word_in_category(_lemma(target), "partitive_pair_measure"):
                    head = target
                    if j >= len(units) or not reg.word_in_category(_lemma(units[j]), "partitive"):
                        break
                    complement = _bound(units[j], "object")
                    if complement is None or not reg.partitive_applies_to(_lemma(target), _lemma(complement)):
                        break
                    target = complement
                    j = units.index(target) + 1
                    if counted is not None:
                        lot = dict(lot_measure=_lemma(head), lot_quantity=float(head.features["value"]),
                                   lot_position=head.uid)
                relative = _relative_purchase_price(reading, j, reg)
                if relative:
                    j, relative_fields = relative
                    tail = _transaction_tail(reading, verb, j, reg, priced=True)
                else:
                    relative_fields = {}
                    tail = _transaction_tail(reading, verb, j, reg, counted=counted)
                if tail is None:
                    break
                j, fields = tail
                fields.update(relative_fields)
                if counted is not None and not any(k in fields for k in ("unit_price", "value", "cost_factor")):
                    break  # do not lose the purchase count in an unpriced record
                if relative_fields and counted is not None and not lot:
                    lot = dict(lot_measure=_lemma(target), lot_quantity=float(counted.features["value"]),
                               lot_position=counted.uid)
                if lot and "unit_price" in fields:
                    lot = {"lot_measure": lot["lot_measure"]}
                if lot:
                    fields.update(lot)
                out.append(Expenditure(
                    provenance=Provenance(source="fold:purchase-target", sentence=reading.sentence_index,
                                          assumption=reading.assumption),
                    entity=_lemma(subject), item=_lemma(target), verb=_lemma(verb),
                    qualifier=target.features.get("qualifier") or "", event=verb.uid,
                    **({"position": target.uid} | fields),
                ))
                i = j
                if i >= len(units) or units[i].surface in (".", "!", "?"):
                    complete = True
                    break
                if _coordinated_finite_clause(reading, i, reg):
                    complete = True
                    break
                if i < len(units) and units[i].surface == ",":
                    i += 1
                elif i >= len(units) or not (
                    reg.word_in_category(_lemma(units[i]), "holder_list_conjunction")
                    or units[i - 1].surface.endswith(",")
                ):
                    break
                if i < len(units) and reg.word_in_category(_lemma(units[i]), "holder_list_conjunction"):
                    i += 1
                while i < len(units) and units[i].sense() == "article":
                    i += 1
                if i < len(units) and units[i].sense() == "name" and not (
                    i + 1 < len(units) and units[i + 1].sense() in ("verb", "auxiliary", "modal")
                ):
                    # A second coordinated supplier cannot silently disappear
                    # from the transaction's single-supplier representation.
                    del out[event_start:]
                    break
            if not complete or not is_bare_referent(subject):
                # This ledger keys buyers by their bare identity. Do not
                # merge differently owned/qualified buyers, even via pronouns.
                out[event_start:] = [replace(e, complete=False) for e in out[event_start:]]
            continue
        supplier = ""
        supplier_qualifier = ""
        # A payment may put the payee before its amount. A named supplier
        # and a categorized commercial noun share this argument position.
        if reg.word_in_category(_lemma(verb), "payment_verb") and (
            amount.sense() == "name" or reg.word_in_category(_lemma(amount), "transaction_supplier")
        ) and not amount.features.get("value_kind"):
            supplier = _lemma(amount)
            supplier_qualifier = amount.features.get("qualifier") or ""
            i += 1
        while i < len(units):
            amount = units[i]
            if not (amount.sense() == "noun"
                    and amount.features.get("value_kind") == "count"
                    and reg.word_in_category(_lemma(amount), "currency_measure")):
                break
            if i + 1 >= len(units):
                break
            prep = units[i + 1]
            if prep.sense() != "preposition" or not reg.word_in_category(_lemma(prep), "spend_target_prep"):
                break
            target = _bound(prep, "object")
            if target is None or target.sense() != "noun" or target.features.get("value_kind"):
                break
            j = units.index(target)
            if j <= i + 1 or any(u.sense() != "article" for u in units[i + 2:j]):
                break
            # A following complement changes the item or cost relation. It
            # must not be dropped while accepting just the prefix noun.
            tail = _transaction_tail(reading, verb, j + 1, reg, priced=True)
            if tail is None:
                break
            end, fields = tail
            out.append(Expenditure(
                provenance=Provenance(source="fold:expenditure", sentence=reading.sentence_index,
                                      assumption=reading.assumption),
                entity=_lemma(subject), item=_lemma(target), verb=_lemma(verb),
                qualifier=target.features.get("qualifier") or "",
                value=float(amount.features["value"]), measure=_lemma(amount), position=amount.uid, event=verb.uid,
                basis="payment", supplier=supplier, supplier_qualifier=supplier_qualifier, **fields,
            ))
            i = end
            separator = False
            while i < len(units) and units[i].surface == ",":
                separator = True
                i += 1
            if i < len(units) and reg.word_in_category(_lemma(units[i]), "holder_list_conjunction"):
                separator = True
                i += 1
            if not separator:
                break
            if i >= len(units) or (
                units[i].sense() in ("noun", "article", "punct")
                and not (
                    units[i].features.get("value_kind") == "count"
                    and reg.word_in_category(_lemma(units[i]), "currency_measure")
                )
            ):
                # An additive continuation with no priced line item is not
                # a complete cost event. Do not hide that missing cost behind
                # the valid prefix (even when it contains no extra number).
                del out[event_start:]
                break
    return out
