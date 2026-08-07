"""Exact named-holder lists for combined-total questions.

Synthetic only: invented names and ordinary core vocabulary exercise the
question contract without copying a benchmark item.
"""

from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask


TEXT = (
    "Aven has twice as many apples as Bira. "
    "Bira has 4 times as many apples as Cato. "
)


def test_three_named_holders_sum_a_resolved_relation_chain(registry) -> None:
    result = solve(
        TEXT
        + "How many apples does Aven, Bira, and Cato have together "
        "if Bira has 12 apples?",
        registry,
    )

    assert result.answer.value == 39
    assert len(result.premises) == 3
    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == "ask/how-many-combined-named-list"
    assert ask[1]["holders"] == ["aven", "bira", "cato"]


def test_three_named_holders_accept_the_non_serial_comma_surface(registry) -> None:
    result = solve(
        TEXT
        + "Bira has 12 apples. "
        "How many apples do Aven, Bira and Cato have together?",
        registry,
    )

    assert result.answer.value == 39


def test_four_named_holders_extend_the_same_relation_chain(registry) -> None:
    result = solve(
        "Dena has 3 times as many apples as Aven. "
        + TEXT
        + "How many apples do Dena, Aven, Bira, and Cato have together "
        "if Bira has 12 apples?",
        registry,
    )

    assert result.answer.value == 111
    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == "ask/how-many-combined-named-list"
    assert ask[1]["holders"] == ["dena", "aven", "bira", "cato"]


def test_named_holder_list_has_no_authored_arity_limit(registry) -> None:
    result = solve(
        "Aven has 1 apple. Bira has 2 apples. Cato has 3 apples. "
        "Dena has 4 apples. Eron has 5 apples. "
        "How many apples do Aven, Bira, Cato, Dena, and Eron have together?",
        registry,
    )

    assert result.answer.value == 15


def test_named_holder_list_accepts_all_together(registry) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. Cato has 3 apples. "
        "How many apples do Aven, Bira, and Cato have all together?",
        registry,
    )

    assert result.answer.value == 39
    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == "ask/how-many-combined-named-list-all-together"
    assert ask[1]["holders"] == ["aven", "bira", "cato"]


def test_named_pair_accepts_all_together_without_expanding_scope(registry) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. Cato has 100 apples. "
        "How many apples do Aven and Bira have all together?",
        registry,
    )

    assert result.answer.value == 36


def test_each_named_holder_list_returns_labelled_values_in_surface_order(
    registry,
) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. Cato has 3 apples. "
        "Dena has 100 apples. "
        "How many apples do Aven, Bira, and Cato each have?",
        registry,
    )

    assert result.answer.kind == "series"
    assert result.answer.value == [
        {"entity": "aven", "measure": "apple", "value": 24},
        {"entity": "bira", "measure": "apple", "value": 12},
        {"entity": "cato", "measure": "apple", "value": 3},
    ]
    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == "ask/how-many-each-named-list"
    assert ask[1]["holders"] == ["aven", "bira", "cato"]
    assert ask[1]["measure_surface"] == "apples"


def test_per_holder_marker_positions_share_the_same_labelled_answer(
    registry,
) -> None:
    prefix = "Aven has 24 apples. Bira has 12 apples. "
    questions = {
        "How many apples do Aven and Bira have each?":
            "ask/how-many-each-named-list-postverbal",
        "How many apples do Aven and Bira have individually?":
            "ask/how-many-individually-named-list-postverbal",
        "How many apples do Aven and Bira individually have?":
            "ask/how-many-individually-named-list",
    }

    for question, ask_id in questions.items():
        result = solve(prefix + question, registry)
        assert result.answer.kind == "series", question
        assert result.answer.value == [
            {"entity": "aven", "measure": "apple", "value": 24},
            {"entity": "bira", "measure": "apple", "value": 12},
        ], question
        ask = match_ask(result.question, registry)
        assert ask is not None
        assert ask[0].id == ask_id


def test_per_holder_asks_do_not_admit_undeclared_marker_substitutions(
    registry,
) -> None:
    prefix = "Aven has 24 apples. Bira has 12 apples. "
    for question in (
        "How many apples do Aven and Bira have every?",
        "How many apples do Aven and Bira separately have?",
        "How many apples do Aven and Bira have respectively?",
    ):
        result = solve(prefix + question, registry)
        assert result.answer.kind == "decline", question
        assert match_ask(result.question, registry) is None, question


def test_each_named_holder_list_declines_instead_of_returning_a_partial_series(
    registry,
) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. "
        "How many apples do Aven, Bira, and Cato each have?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert result.answer.value is None
    assert "cato" in result.answer.reason


def test_each_named_holder_list_rejects_invalid_postpositive_quantifiers(
    registry,
) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. "
        "How many apples do Aven and Bira every have?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert match_ask(result.question, registry) is None


def test_named_holder_list_rejects_invalid_total_marker_forms(registry) -> None:
    prefix = "Aven has 24 apples. Bira has 12 apples. "
    misspelled = solve(
        prefix + "How many apples do Aven and Bira have alltogether?",
        registry,
    )
    invalid_pairing = solve(
        prefix + "How many apples do Aven and Bira have all total?",
        registry,
    )

    assert misspelled.answer.kind == "decline"
    assert match_ask(misspelled.question, registry) is None
    assert invalid_pairing.answer.kind == "decline"
    assert match_ask(invalid_pairing.question, registry) is None


def test_exact_named_holder_list_ignores_an_unasked_fourth_holder(registry) -> None:
    result = solve(
        TEXT
        + "Bira has 12 apples. Dena has 100 apples. "
        "How many apples do Aven, Bira, and Cato have together?",
        registry,
    )

    assert result.answer.value == 39


def test_exact_named_holder_list_declines_when_one_holder_is_unresolved(
    registry,
) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. "
        "How many apples do Aven, Bira, and Cato have together?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert "cato" in result.answer.reason


def test_exact_named_holder_list_declines_a_repeated_name(registry) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. "
        "How many apples do Aven, Bira, and Aven have together?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert "repeats a named holder" in result.answer.reason


def test_named_holder_list_rejects_disjunction_and_comma_only_scope(
    registry,
) -> None:
    disjunction = solve(
        "Aven has 1 apple. Bira has 2 apples. Cato has 3 apples. "
        "How many apples do Aven, Bira, or Cato have together?",
        registry,
    )
    comma_only = solve(
        "Aven has 1 apple. Bira has 2 apples. Cato has 3 apples. "
        "How many apples do Aven, Bira, Cato have together?",
        registry,
    )

    assert disjunction.answer.kind == "decline"
    assert comma_only.answer.kind == "decline"
    assert match_ask(disjunction.question, registry) is None
    assert match_ask(comma_only.question, registry) is None


def test_existing_named_pair_still_sums_exactly_two_holders(registry) -> None:
    result = solve(
        "Aven has 24 apples. Bira has 12 apples. Cato has 3 apples. "
        "How many apples do Aven and Bira have together?",
        registry,
    )

    assert result.answer.value == 36
