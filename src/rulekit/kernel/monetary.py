"""Concrete monetary units and the legacy canonical unit-price contract.

Currency identities and conversions are pack data. Abstract financial labels
are dimensions, never denominations. Untyped legacy prices retain their
canonical denomination; new concrete denominations must be consumed explicitly.
"""
from __future__ import annotations

from dataclasses import replace
from math import isfinite

from .dimensions import conversion_factor
from .evaluate import evaluate


def canonical_currency(reg):
    units = reg.category_members.get("canonical_currency_unit", ())
    return units[0] if len(units) == 1 else None


def retain_price_currency(price, reading, reg):
    if price.measure:
        return price
    units = {
        reg.plural_to_singular.get(u.features.get("lemma", u.features.get("fold", "")),
                                  u.features.get("lemma", u.features.get("fold", "")))
        for u in reading.units
        if u.features.get("value_kind") == "count"
        and u.features.get("value") == price.value
        and reg.word_in_category(u.features.get("lemma", u.features.get("fold", "")), "currency_unit")
    }
    if len(units) == 1:
        unit = next(iter(units))
        # Preserve the established identity of canonical legacy prices.
        if unit != canonical_currency(reg):
            return replace(price, measure=unit)
    if len(units) > 1:
        return replace(price, measure="currency")
    return price


def convert_money(value, source, target, reg, log):
    factor = conversion_factor(reg, source, target, category="currency_unit")
    if factor is None or not isfinite(value):
        return None
    return evaluate(f"{value!r} * {factor!r}", {}, log, source="currency-conversion")


def canonical_price(price, reg, log):
    target = canonical_currency(reg)
    source = price.measure or target
    if target is None or source is None or price.per and price.per != price.item:
        return None
    value = convert_money(price.value, source, target, reg, log)
    if value is None or value <= 0:
        return None
    log.consumed_currency_price_keys.add(price.key())
    return value


def price_terms(price, reg):
    """A quote's amount, denomination and unit basis, independent of source."""
    return price.value, price.measure or canonical_currency(reg), price.per
