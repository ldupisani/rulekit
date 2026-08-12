"""Exact discourse groups for aggregate and per-holder asks."""

from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask


PREFIX = (
    "John receives 70 apples. "
    "Eron receives 20 apples more than Aven. "
    "Aven receives 10 apples. "
)


def test_repeated_object_then_subject_can_join_discourse_group(registry) -> None:
    result = solve(PREFIX + "How many apples do they receive combined?", registry)

    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == "ask/how-many-combined-discourse-group"
    assert ask[1]["holders"] == ["john", "eron", "aven"]
    assert result.answer.kind == "number"
    assert result.answer.value == 110


def test_discourse_group_individually_returns_labelled_series(registry) -> None:
    result = solve(
        PREFIX + "How many apples do they receive individually?", registry
    )

    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == (
        "ask/how-many-individually-discourse-group-postverbal"
    )
    assert ask[1]["holders"] == ["john", "eron", "aven"]
    assert result.answer.kind == "series"
    assert result.answer.value == [
        {"entity": "john", "measure": "apple", "value": 70},
        {"entity": "eron", "measure": "apple", "value": 30},
        {"entity": "aven", "measure": "apple", "value": 10},
    ]


def test_discourse_group_individually_supports_preverbal_marker(registry) -> None:
    result = solve(
        PREFIX + "How many apples do they individually receive?", registry
    )

    assert result.answer.kind == "series"
    assert result.answer.value == [
        {"entity": "john", "measure": "apple", "value": 70},
        {"entity": "eron", "measure": "apple", "value": 30},
        {"entity": "aven", "measure": "apple", "value": 10},
    ]


def test_all_of_them_projects_the_same_exact_discourse_group(registry) -> None:
    result = solve(
        PREFIX + "How many apples do all of them receive combined?", registry
    )

    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == "ask/how-many-all-combined-discourse-group"
    assert ask[1]["holders"] == ["john", "eron", "aven"]
    assert result.answer.kind == "number"
    assert result.answer.value == 110


def test_object_only_name_prevents_discourse_group_guess(registry) -> None:
    result = solve(
        "John receives 70 apples. John sees Zoe. "
        "How many apples do they receive individually?",
        registry,
    )

    assert result.answer.kind == "decline"
    assert match_ask(result.question, registry) is None


def test_unresolved_they_cannot_fall_back_to_fact_store_enumeration(
    registry,
) -> None:
    result = solve(
        "John has 3 apples. Bira has 5 apples. John sees Zoe. "
        "How many apples do they have combined?",
        registry,
    )

    ask = match_ask(result.question, registry)
    assert ask is not None
    assert ask[0].id == "ask/how-many-combined"
    assert ask[1]["require_discourse_group"] == "they"
    assert result.answer.kind == "decline"
    assert "antecedent group" in result.answer.reason
