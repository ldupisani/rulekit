"""The document loop: gap-driven cross-sentence resolution,
definitive-or-decline discourse, loud termination."""

from rulekit.kernel.engine import solve


def test_unique_antecedent_resolves_in_round_two(registry):
    r = solve("Tom has 10 apples. He ate 4 apples. How many apples does Tom have?", registry)
    assert r.answer.value == 6
    assert r.document.rounds == 2  # round 1 bound the pronoun, round 2 settled
    assert r.document.gaps == []


def test_pronoun_facts_attribute_to_antecedent(registry):
    from rulekit.kernel.model import Quantity

    r = solve("Mary has 5 books. She finds 2 books. How many books does Mary have?", registry)
    assert r.answer.value == 7
    entities = {f.entity for f in r.store.facts if isinstance(f, Quantity)}
    assert entities == {"mary"}  # never a Quantity(entity='she')


def test_ambiguous_pronoun_declines(registry):
    """Two candidate antecedents: binding would be a guess. The unresolved
    value must also block the partial answer (a confident 3 ignoring a
    possible depletion is the exact wrong this engine exists to prevent)."""
    r = solve(
        "Tom has 3 apples. Mary has 4 apples. He ate 2 apples. "
        "How many apples does Tom have?",
        registry,
    )
    assert r.answer.kind == "decline"
    assert "value-accounting" in r.answer.reason
    assert any(g.kind == "unmet-obligation" and g.key[0] == "He" for g in r.document.gaps)


def test_unrelated_known_value_does_not_veto(registry):
    # Mary's 4 reached a FACT (fully read, just not asked about) — accounted
    r = solve(
        "Tom has 3 apples. Mary has 4 apples. How many apples does Tom have?",
        registry,
    )
    assert r.answer.value == 3


def test_rounds_terminate(registry):
    # a document with no cross-sentence work settles in one round
    r = solve("Tom has 3 apples. How many apples does Tom have?", registry)
    assert r.document.rounds == 1
