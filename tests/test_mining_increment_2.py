"""Increment 2: money asks — currency amounts as counted nouns, measure
resolution against the facts, per-unit rates decline. Synthetic only."""

from rulekit.kernel.engine import solve


def test_currency_amount_is_a_counted_noun(registry):
    r = solve("Tom has $20. How many dollars does Tom have?", registry)
    assert r.answer.value == 20


def test_bare_how_much_resolves_the_category(registry):
    # `measure: currency` in the ask names the CATEGORY; the consumer
    # resolves it to the unique currency measure in the facts
    r = solve("Tom has $20. Tom spent $8. How much does Tom have?", registry)
    assert r.answer.value == 12


def test_how_much_event_ask(registry):
    r = solve("Tom spent $8. How much did Tom spend?", registry)
    assert r.answer.value == 8


def test_rate_expression_declines(registry):
    # "3 coins a day" is a RATE — no fact, unaccounted value, honest decline
    r = solve("Tom finds 3 coins a day. How many coins does Tom have?", registry)
    assert r.answer.kind == "decline"


def test_concrete_measure_never_collapses(registry):
    # apples stay apples even though a currency category exists
    r = solve("Tom has 3 apples. How many apples does Tom have?", registry)
    assert r.answer.value == 3
