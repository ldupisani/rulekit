"""Perfect tense, affine/fraction frame relations,
fraction-as-many, unique-verb combined fallback. Synthetic only."""

from rulekit.kernel.engine import solve


def test_perfect_tense_is_one_verb(registry):
    r = solve("Tom has found 5 coins. How many coins did Tom find?", registry)
    assert r.answer.value == 5


def test_affine_frame_relation(full_registry):
    r = solve(
        "Mary has found 10 coins. Tom has found 3 more than twice the number "
        "of coins that Mary has found. How many coins did Tom find?",
        full_registry,
    )
    assert r.answer.value == 23


def test_fraction_frame_relation(full_registry):
    r = solve(
        "Mary has found 12 coins. Tom has found 1/4 the number of coins that "
        "Mary has found. How many coins did Tom find?",
        full_registry,
    )
    assert r.answer.value == 3


def test_fraction_as_many(registry):
    r = solve(
        "Mary found 12 coins. Tom found half as many coins as Mary. "
        "How many coins did Tom find?",
        registry,
    )
    assert r.answer.value == 6


def test_unique_verb_combined_fallback(registry):
    r = solve(
        "Mary found 12 coins. Tom found half as many coins as Mary. "
        "How many coins altogether did Mary and Tom find?",
        registry,
    )
    assert r.answer.value == 18
