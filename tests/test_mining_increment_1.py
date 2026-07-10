"""Increment 1 of the GSM8K campaign — synthetic pins for the general
machinery it added (the firewall: no benchmark strings in tests)."""

from rulekit.kernel.engine import solve, split_question


def test_question_pronoun_resolves(registry):
    r = solve("Tom has 10 apples. Tom ate 4 apples. How many apples does he have?", registry)
    assert r.answer.value == 6


def test_question_pronoun_ambiguous_declines(registry):
    r = solve(
        "Tom has 3 apples. Mary has 4 apples. How many apples does he have?", registry
    )
    assert r.answer.kind == "decline"


def test_if_clause_splits_into_premise(registry):
    premises, question = split_question(
        "Tom has 8 apples. If Tom ate 3 apples, how many apples does he have?", registry
    )
    assert premises == ["Tom has 8 apples.", "Tom ate 3 apples."]
    assert question == "how many apples does he have?"
    r = solve("Tom has 8 apples. If Tom ate 3 apples, how many apples does he have?", registry)
    assert r.answer.value == 5


def test_if_clause_with_commas_in_question_part(registry):
    _, question = split_question(
        "If Tom has 4 coins, how many coins, in total, does Tom have?", registry
    )
    assert question.startswith("how many coins")


def test_postfix_comparative(registry):
    # "N ITEM more than Y" — the count condenses into the noun first
    r = solve(
        "Mary found 4 marbles more than Tom. If Tom found 2 marbles, "
        "how many marbles does Mary have?",
        registry,
    )
    assert r.answer.value == 6


def test_compound_sentence_matches_both_clauses(registry):
    r = solve(
        "Mary found 4 marbles more than Tom, and Sue found 1 marble fewer than Mary. "
        "If Tom found 2 marbles, how many marbles does Sue have?",
        registry,
    )
    assert r.answer.value == 5


def test_word_number_cascade(registry):
    r = solve(
        "Tom has one hundred forty five coins. How many coins does Tom have?", registry
    )
    assert r.answer.value == 145


def test_capitalized_adjective_joins_name(registry):
    r = solve("Small Tom has 3 apples. How many apples does Small Tom have?", registry)
    assert r.answer.value == 3


def test_comma_list_conjunction_declines(registry):
    # the group's number must never be attributed to the nearest name
    r = solve(
        "Tom, Mary, and Sue have 12 apples. How many apples does Sue have?", registry
    )
    assert r.answer.kind == "decline"


def test_event_does_not_block_relation_resolution(registry):
    r = solve(
        "Mary has 3 more apples than Tom. Mary ate 1 apple. "
        "If Tom has 5 apples, how many apples does Mary have?",
        registry,
    )
    assert r.answer.value == 7  # (5+3) state, then the eat event
