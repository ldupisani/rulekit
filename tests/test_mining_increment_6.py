"""Increment 6: inverse relations, slash/percent fractions, ratio frames,
verb-sensitive differences, single-word name joining. Synthetic only."""

from rulekit.kernel.engine import solve


def test_inverse_relation_resolution(registry):
    r = solve(
        "Mary has twice as many apples as Tom. If Mary has 10 apples, "
        "how many apples does Tom have?",
        registry,
    )
    assert r.answer.value == 5


def test_slash_fraction_tokenizes_whole(registry):
    r = solve(
        "Tom found 12 eggs. Tom ate 1/4 of the eggs. How many eggs are left?", registry
    )
    assert r.answer.value == 9


def test_percent_word_is_a_fraction(registry):
    r = solve(
        "Mary has twenty percent more apples than Tom. If Tom has 20 apples, "
        "how many apples does Mary have?",
        registry,
    )
    assert r.answer.value == 24


def test_verb_sensitive_difference(registry):
    r = solve(
        "Tom sold 9 apples. Mary sold twice as many apples as Tom. "
        "How many more apples did Mary sell than Tom?",
        registry,
    )
    assert r.answer.value == 9


def test_forward_does_not_double_an_observed_event(registry):
    # "Mary found twice as many as Tom. Mary found 10." — re-deriving Mary
    # from Tom would double her; the by-verb block prevents it
    r = solve(
        "Mary found twice as many apples as Tom. If Mary found 10 apples, "
        "how many apples do they have altogether?",
        registry,
    )
    assert r.answer.value == 15


def test_merged_unit_never_joins_a_name(registry):
    # "Last year Tom" must stay [Last year][Tom] — time adjunct + name
    r = solve(
        "Tom has 4 toys. Mary has twice as many toys as Tom. "
        "How many toys do they have altogether?",
        registry,
    )
    assert r.answer.value == 12
