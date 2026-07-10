"""Increment 4: entity-less asks (unique-entity consumer) and if-leading
task sentences detected as questions. Synthetic strings only."""

from rulekit.kernel.engine import solve, split_question


def test_entityless_left_ask_unique_entity(registry):
    r = solve(
        "Tom has 10 marbles. Tom lost 3 marbles. How many marbles are left?", registry
    )
    assert r.answer.value == 7


def test_entityless_ask_declines_with_two_entities(registry):
    # two holders: "how many are left?" is genuinely ambiguous
    r = solve(
        "Tom has 10 marbles. Mary has 5 marbles. How many marbles are left?", registry
    )
    assert r.answer.kind == "decline"
    assert "exactly one" in r.answer.reason


def test_are_there_ask(registry):
    r = solve("Tom has 12 books. How many books are there?", registry)
    assert r.answer.value == 12


def test_if_leading_task_sentence_is_a_question(registry):
    premises, question = split_question(
        "Tom has 8 apples. If Tom ate 3 apples, compute the total.", registry
    )
    assert question is not None
    assert premises == ["Tom has 8 apples.", "Tom ate 3 apples."]
