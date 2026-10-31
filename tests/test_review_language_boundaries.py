"""Invented regressions for unit typing, local roles and construction boundaries."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import MatchToken
from rulekit.generation import generate_candidate
from rulekit.generation.sample import _strict_round_trip_result
from rulekit.kernel.document import run_document
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import BatchEvidence, SpecificationEvidence, Unit


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


def read(project, sentence):
    reading = analyze(sentence, project.registry)
    doc = run_document([reading], project.registry)
    return reading, doc, doc.rule_results.get(0, [])


@pytest.mark.parametrize("price,budget,expected", [
    ("50 cents", "2 dollars", 4),
    ("2 dollars", "100 cents", 0),
    ("25 cents", "125 cents", 5),
    ("3 dollars", "12 dollars", 4),
    ("3 dollars", "0 dollars", 0),
])
@pytest.mark.parametrize("item,plural", [("pen", "pens"), ("ticket", "tickets")])
def test_capacity_converts_concrete_money_units(project, price, budget, expected, item, plural):
    result = solve(f"A {item} costs {price}. How many {plural} can Dena buy with {budget}?", project.registry)
    assert result.answer.committed, result.answer
    assert result.value == expected
    assert not result.deficiencies()
    if "cents" in price or "cents" in budget:
        assert any(entry.source == "currency-conversion" for entry in result.log.entries)


@pytest.mark.parametrize("price,budget", [
    ("0 dollars", "3 dollars"),
    ("2 dollars", "10 costs"),
    ("2 dollars", "10 balances"),
    ("2 dollars", "10 earnings"),
    ("2 dollars", "10 pounds"),  # no exchange rate / homographic physical unit
])
def test_capacity_declines_nonunits_and_zero_prices(project, price, budget):
    result = solve(f"A pen costs {price}. How many pens can Dena buy with {budget}?", project.registry)
    assert not result.answer.committed


def test_unaware_price_consumers_cannot_use_unconverted_cents(project):
    result = solve("A pen costs 50 cents. How much does each pen cost?", project.registry)
    # This legacy ask has no requested denomination. It must convert or decline,
    # never reinterpret the quoted amount as canonical currency.
    assert not result.answer.committed or result.value == .5


@pytest.mark.parametrize("unit,accepted", [("dollars", True), ("cents", True), ("costs", False), ("earnings", False)])
def test_stored_resource_exceptions_require_actual_units(project, unit, accepted):
    _, doc, _ = read(project, f"The dog lost all money inside the wallet except for 7 {unit}.")
    rows = [f for f in doc.store.by_kind(BatchEvidence) if f.kind == "resource-store-loss"]
    assert bool(rows) == accepted


@pytest.mark.parametrize("subject", ["a plan", "the formula", "the procedure"])
@pytest.mark.parametrize("denominator,accepted", [("0", False), ("0.5", True), ("2", True)])
def test_ratio_denominator_is_strictly_positive_not_integral(project, subject, denominator, accepted):
    _, doc, _ = read(project, f"{subject.capitalize()} uses 3 liters of water per {denominator} kilograms of clay.")
    rows = [f for f in doc.store.by_kind(SpecificationEvidence) if f.kind == "reference"]
    assert bool(rows) == accepted


@pytest.mark.parametrize("subject,verb", [("Plan", "uses"), ("The plan", "use"), ("The plans", "uses")])
def test_ratio_requires_anchoring_and_finite_agreement(project, subject, verb):
    _, doc, _ = read(project, f"{subject} {verb} 3 liters of water per 2 kilograms of clay.")
    assert not [f for f in doc.store.by_kind(SpecificationEvidence) if f.kind == "reference"]


@pytest.mark.parametrize("head,verb", [("a book", "costs"), ("the bicycle", "costs"), ("Dena's books", "cost")])
def test_relative_clause_binds_anchored_uncounted_antecedent(project, head, verb):
    reading = analyze(f"Aven was buying {head} that {verb} 30 cents.", project.registry)
    pred = next(u for u in reading.units if u.surface == verb)
    subject = next(ob.target for ob in pred.obligations() if ob.need == "subject")
    assert isinstance(subject, Unit)
    assert any(word.surface.casefold() == "that" for u in reading.units for word in u.words)
    assert subject.span[1] < pred.span[0]
    assert not [d for d in reading.deficiencies() if f"'{verb}'" in d]


@pytest.mark.parametrize("prefix", [
    "There are 5 jars and each of the first four jars has 3 pickles.",
    "There are 5 jars and the first four jars each have 3 pickles.",
    "There are 5 jars and the first four jars have 3 pickles each.",
    "There were 5 jars and each of the first four jars had 3 pickles.",
])
def test_holder_distributives_bind_the_real_collection(project, prefix):
    reading, _, matches = read(project, prefix)
    match = next(m for m in matches if m.match.rule.id.startswith("arithmetic/holder-prefix-combined"))
    quantifier = match.match.slots["each"]
    obligation = next(ob for ob in quantifier.obligations() if ob.need == "collection")
    assert obligation.target is match.match.slots["holders"]
    assert not reading.deficiencies()
    result = solve(prefix + " There are a total of 17 pickles. How many pickles does the last jar have?", project.registry)
    assert result.answer.committed, result.answer
    assert result.value == 5


@pytest.mark.parametrize("prefix", [
    "There are 5 jars and the first four boxes have 3 pickles each.",
    "There are 5 jars and the four first jars have 3 pickles each.",
    "There are 5 jars and the first four jars has 3 pickles each.",
    "There are 5 jars and each of the first four jars have 3 pickles.",
    "There are 5 jars and first four jars have 3 pickles each.",
])
def test_holder_prefix_does_not_invent_identity_or_grammar(project, prefix):
    _, _, matches = read(project, prefix)
    assert not [m for m in matches if m.match.rule.id.startswith("arithmetic/holder-prefix-combined")]


@pytest.mark.parametrize("place,accepted", [
    ("aboard a bus", True), ("aboard the boat", True),
    ("in a cupboard", True), ("on the street", True),
    ("aboard a cupboard", False), ("aboard cupboard", False),
    ("in cupboard", False),
])
def test_location_frames_and_reference_anchoring(project, place, accepted):
    _, _, matches = read(project, f"There were 18 books {place} in total.")
    assert bool([m for m in matches if m.match.rule.id == "arithmetic/holder-content-total-located-trailing"]) == accepted


def test_pronoun_round_trip_uses_matched_slot_sense(project):
    sentence = "The gardener received 12 more cards but discarded half of those."
    reading, _, matches = read(project, sentence)
    result = next(m for m in matches if m.match.rule.id == "arithmetic/acquired-batch-more-discard")
    requested = {name: unit.surface for name, unit in result.match.slots.items() if isinstance(unit, Unit)}
    assert _strict_round_trip_result(result, requested, reading, project.registry)
    requested["item"] = "12 more books"
    assert not _strict_round_trip_result(result, requested, reading, project.registry)


@pytest.mark.parametrize("rule_id", [
    "arithmetic/specification-output-context-owned-scope",
    "arithmetic/explicit-proportion-adoption-owned-scope",
    "arithmetic/population-output-demand-owned-scope",
])
def test_owned_scope_generation_does_not_stack_independent_possessors(project, rule_id):
    candidate = generate_candidate(project, rule_id=rule_id, seed=231)
    assert candidate.target_status == "matched"
    assert "scope_determiner" not in candidate.requested_bindings


def test_positive_slot_schema_does_not_allow_a_non_numeric_role():
    with pytest.raises(ValidationError):
        MatchToken(slot="item", cat="noun", value_positive=True)
    assert MatchToken(slot="amount", cat="mass_measure", counted=True, value_positive=True)


@pytest.mark.parametrize("question", [
    "How much did Dena pay for 3 pens?",
    "Dena bought 3 pens. How much did Dena spend in total?",
])
@pytest.mark.parametrize("first,second", [("50 cents", "50 dollars"), ("50 dollars", "50 cents")])
def test_equal_numeric_quotes_in_different_denominations_conflict(project, question, first, second):
    result = solve(f"A pen costs {first}. Pens are {second} each. {question}", project.registry)
    assert not result.answer.committed


def test_optional_descriptor_boundaries_do_not_widen_other_spatial_meanings(project):
    reg = project.registry
    assert not reg.attribute_applies_to("near", "garden")
    assert reg.attribute_applies_to("near", "garden", when_declared=True)
    assert reg.attribute_applies_to("aboard", "bus", when_declared=True)
    assert not reg.attribute_applies_to("aboard", "cupboard", when_declared=True)


def test_an_invalid_budget_tail_cannot_be_replaced_by_a_prior_holding(project):
    result = solve("Dena has 10 dollars. A pen costs 2 dollars. "
                   "How many pens can Dena buy with 10 costs?", project.registry)
    assert not result.answer.committed


@pytest.mark.parametrize("purchase,expected", [("", None), ("Dena bought 1 pen. ", 1)])
def test_scaled_price_keeps_its_denomination(project, purchase, expected):
    from rulekit.kernel.model import Price
    text = ("A pen costs 50 cents. A pencil costs twice that price. " + purchase
            + "How many pencils can Dena buy with 2 dollars?")
    result = solve(text, project.registry)
    quote = next(p for p in result.store.by_kind(Price) if p.item == "pencil")
    assert quote.value == 100
    assert quote.measure == "cent"
    if expected is None:
        # The source quote has not been independently consumed by this ask.
        assert not result.answer.committed or result.value == 2
    else:
        assert result.answer.committed, result.answer
        assert result.value == expected


def test_partitive_distributive_cannot_be_an_ordinary_universal_determiner(project):
    _, _, matches = read(project, "There are 5 jars and every of the first four jars has 3 pickles.")
    assert not [m for m in matches if m.match.rule.id.startswith("arithmetic/holder-prefix-combined")]


@pytest.mark.parametrize("rule_id", [
    "arithmetic/holder-prefix-combined-0-bare", "arithmetic/holder-prefix-combined-0-located",
    "arithmetic/holder-prefix-0", "arithmetic/holder-prefix-combined-1-bare",
    "arithmetic/holder-prefix-combined-1-located", "arithmetic/holder-prefix-1",
    "arithmetic/holder-prefix-combined-2-bare", "arithmetic/holder-prefix-combined-2-located",
    "arithmetic/holder-prefix-2",
])
def test_all_holder_distributive_positions_generate_anchored_groups(project, rule_id):
    candidate = generate_candidate(project, rule_id=rule_id, seed=313)
    assert candidate.target_status == "matched", candidate
    assert "every of" not in candidate.sentence.lower()
    assert candidate.target_bindings["each"].casefold() == "each"
    assert not candidate.grammar_deficiencies


@pytest.mark.parametrize("measure,offset,per,accepted", [
    ("cent", 0, None, True), ("cent", 1, None, False),
    (None, 1, None, True), ("cent", 0, "pair", True),
])
def test_price_derivation_preserves_units_and_requires_offset_units(project, measure, offset, per, accepted):
    from rulekit.kernel.evaluate import ArithmeticLog
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.model import Price, Provenance, Relation
    from rulekit.kernel.saturate import _ANAPHOR_PRICE_STANDARD, _relations_synth
    anchor = Price(Provenance("invented", 0), item="pen", value=50, measure=measure, per=per)
    relation = Relation(Provenance("invented", 1), subject="pencil", standard=_ANAPHOR_PRICE_STANDARD,
                        measure="currency", factor=2, offset=offset, verb="cost")
    quotes = [p for p in _relations_synth(FactStore(facts=[anchor, relation]), project.registry,
                                         ArithmeticLog()) if isinstance(p, Price)]
    assert bool(quotes) == accepted
    if accepted:
        assert quotes[0].measure == measure
        assert quotes[0].per == per
        assert quotes[0].value == 100 + offset
