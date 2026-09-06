"""Item-targeted currency costs, including coordinated complements.

This supplements the generic fold and supplies its coordinated currency events.
Only a fully read amount + governed target is a cost. Vocabulary and additive
coordination permissions are owned by categories, not by this scan.
"""

from __future__ import annotations

from ..data.registry import Registry
from .model import Expenditure, Provenance, Reading


def _transaction_tail(reading, verb, index, reg, *, priced=False):
    """Read complete, category-licensed transaction complements in either order.

    The same routine handles an unpriced purchase and an explicit cost. No
    unrecognized PP is thrown away, including a unit-price or purpose tail.
    """
    from .learn import _bound, _lemma, _matching_adposition_roles
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
              and reg.word_in_category(_lemma(marker), "transaction_price_preposition")
              and obj.features.get("value_kind") == "count"
              and reg.word_in_category(_lemma(obj), "currency_measure")):
            if "value" in fields:
                return None
            fields.update(value=float(obj.features["value"]), measure=_lemma(obj), position=obj.uid)
        else:
            return None
        index = j + 1
    return index, fields


def learn_expenditures(reading: Reading, reg: Registry) -> list[Expenditure]:
    from .learn import _bound, _clause_negated, _lemma
    from .obligations import _crosses_clause_boundary

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
            while i < len(units):
                target = units[i]
                if target.sense() != "noun" or target.features.get("value_kind"):
                    break
                j = i + 1
                if reg.word_in_category(_lemma(target), "partitive_pair_measure"):
                    if j >= len(units) or not reg.word_in_category(_lemma(units[j]), "partitive"):
                        break
                    complement = _bound(units[j], "object")
                    if complement is None or not reg.partitive_applies_to(_lemma(target), _lemma(complement)):
                        break
                    target = complement
                    j = units.index(target) + 1
                tail = _transaction_tail(reading, verb, j, reg)
                if tail is None:
                    break
                j, fields = tail
                out.append(Expenditure(
                    provenance=Provenance(source="fold:purchase-target", sentence=reading.sentence_index,
                                          assumption=reading.assumption),
                    entity=_lemma(subject), item=_lemma(target), verb=_lemma(verb),
                    qualifier=target.features.get("qualifier") or "", event=verb.uid,
                    **({"position": target.uid} | fields),
                ))
                i = j
                if i < len(units) and units[i].surface == ",":
                    i += 1
                elif i >= len(units) or not reg.word_in_category(_lemma(units[i]), "holder_list_conjunction"):
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
