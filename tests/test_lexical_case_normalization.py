"""Case normalization must not turn unambiguous predicates into names."""

from rulekit.kernel.engine import analyze, solve


def test_title_cased_unambiguous_verb_keeps_lexical_sense(registry) -> None:
    reading = analyze("Aven Receives 10 apples.", registry)

    receives = next(
        unit for unit in reading.units
        if unit.features.get("fold") == "receives"
    )
    assert receives.sense() == "verb"
    assert receives.features["lemma"] == "receive"
    assert all(
        unit.features.get("fold") != "aven receives" for unit in reading.units
    )


def test_title_cased_premise_verb_preserves_combined_answer(registry) -> None:
    result = solve(
        "John receives 70 apples. "
        "Eron receives 20 apples more than Aven. "
        "Aven Receives 10 apples. "
        "How many apples do all of them receive combined?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 110


def test_capitalized_known_noun_remains_name_eligible(registry) -> None:
    reading = analyze("Sam met Rose yesterday.", registry)

    rose = next(
        unit for unit in reading.units
        if unit.features.get("fold") == "rose"
    )
    assert rose.sense() == "name"
