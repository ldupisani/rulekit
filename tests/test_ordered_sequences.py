"""Invented carrier/batch sequences and fail-closed semantic neighbours."""

from pathlib import Path
from dataclasses import replace
import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve, analyze
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.model import EventCadence, SequenceTotal, SequenceStep, Quantity
from rulekit.kernel.consumers.ordered_sequence import affine_terms_from_total
from rulekit.generation import generate_candidate
from rulekit.generation.sample import _lexical_fillers


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def reg(request):
    return load_project(Path("projects") / request.param).registry


def story(total=70, step="twice as many", index="first", carrier="box", verb="deliver", item="toys"):
    return (f"Mira {verb}s a {carrier} once every two days. "
            f"Over six days, Mira has {verb}ed {total} {item}. "
            f"Each new {carrier} has {step} {item} as the last {carrier}. "
            f"How many {item} were in the {index} {carrier}?")


@pytest.mark.parametrize("text,expected", [
    (story(), 10),
    (story(index="final"), 40),
    (story(index="last"), 40),
    (story(total=130, step="three times as many"), 10),
    (story(total=60, step="as many"), 20),
    (story(total=70, step="half as many"), 40),
    (story(total=70, step="half as many", index="final"), 10),
    (story(carrier="batch", item="apples"), 10),
    (story(carrier="basket", item="roses"), 10),
    (story().replace("last box", "previous box").replace("new box", "next box"), 10),
    (story().replace("Mira has delivered", "she has delivered"), 10),
    (story().replace("Mira has delivered", "Mira delivered"), 10),
    (story().replace("two days", "48 hours"), 10),
    (story().replace("six days", "144 hours"), 10),
    (story(total=60).replace("twice as many toys as", "five more toys than"), 15),
    (story(total=60).replace("twice as many toys as", "five fewer toys than"), 25),
    (story(total=60,index="final").replace("twice as many toys as", "five fewer toys than"), 15),
    (story().replace("in the first box?", "in the box Mira delivered in the first two days?"), 10),
])
def test_end_to_end_sequences(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.value == pytest.approx(expected), result.answer
    assert result.answer.proof
    assert len(result.store.by_kind(EventCadence)) == 1
    assert len(result.store.by_kind(SequenceTotal)) == 1
    assert len(result.store.by_kind(SequenceStep)) == 1
    assert not result.store.by_kind(Quantity)


def test_cadence_purpose_and_contextual_event_synonyms(reg):
    text = (
        "A deep-sea dragon returns from the sea once every fifty years to feast on a ship "
        "and sate its hunger. Over one hundred fifty years, it has consumed 63 people. "
        "Ships have been built larger over time, so each new ship has twice as many people "
        "as the last ship. How many people were on the ship the dragon ate in the first fifty years?"
    )
    result = solve(text, reg)
    assert result.answer.value == 9, result.answer
    assert "one whole ship" in result.answer.reason
    assert result.answer.proof.steps[0].rule == "bounded-carrier-interpretation"


@pytest.mark.parametrize("old,new", [
    ("once every", "twice every"),
    ("six days", "five days"),
    ("six days", "zero days"),
    ("two days", "zero days"),
    ("two days", "two years"),
    ("70 toys", "71 toys"),
    ("70 toys", "-70 toys"),
    ("last box", "last bag"),
    ("Mira has delivered", "Tova has delivered"),
    ("Mira has delivered", "Mira has received"),
    ("once every two days.", "once every two days except today."),
    ("a box once", "a large box once"),
    ("has twice", "has not twice"),
    ("has twice", "has about twice"),
    ("has twice", "has at least twice"),
    ("has delivered 70", "has delivered only half of 70"),
    ("70 toys.", "70 toys and 70 apples."),
    ("70 toys.", "70 toys. Mira delivers 70 toys."),
    ("70 toys.", "70 toys. Mira has 2 apples."),
    ("the first box?", "the first box today?"),
    ("the first box?", "the first box except two toys?"),
    ("twice as many", "zero times as many"),
    ("twice as many", "fifths as many"),
])
def test_incomplete_or_incompatible_series_declines(reg, old, new):
    result = solve(story().replace(old,new), reg)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("removed", [0,1,2])
def test_each_evidence_component_is_required(reg, removed):
    sentences = story().split(". ")
    del sentences[removed]
    result = solve(". ".join(sentences), reg)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("question", [
    "How many toys did Mira deliver?",
    "How many toys were in the box?",
    "How many toys does Mira have?",
])
def test_sequence_facts_cannot_disappear_into_old_folds(reg, question):
    result = solve(story().split("How many")[0] + question, reg)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("text,value", [("hundred years",100),("three hundred years",300),("dozen apples",12)])
def test_bare_and_explicit_scales_share_number_reader(reg, text, value):
    reading = analyze(text, reg)
    assert [u.features["value"] for u in reading.units if "value" in u.features] == [value]


def test_a_floating_quantifier_does_not_force_a_noun_reading(reg):
    result = solve("Mira buys 4 toys that each cost $5. How much did Mira pay for everything?", reg)
    assert result.answer.value == 20, result.answer


def test_perfect_predicate_keeps_its_auxiliary_agreement(reg):
    reading = analyze("Ships have been built.", reg)
    merged = next(u for u in reading.units if u.surface.lower() == "have been")
    assert merged.features["number"] == "plural"


def test_compound_verb_fillers_require_an_actual_reader_round_trip(reg):
    lexicon = dict(reg.lexicon)
    lexicon["red toy"] = reg.lexicon["have been"].model_copy()
    extended = replace(reg, lexicon=lexicon)
    forms = {f.surface for f in _lexical_fillers(extended, sense="verb")}
    assert {"has been", "have been", "had been"} <= forms
    assert "red toy" not in forms


@pytest.mark.parametrize("project_name", ["curated", "gsm8k"])
@pytest.mark.parametrize("rule", [
    "carrier-event-cadence", "purpose-carrier-event-cadence",
    "bounded-sequence-event-total", "bounded-sequence-anaphoric-total",
    "adjacent-carrier-multiplier", "adjacent-carrier-fraction", "adjacent-carrier-offset",
    "adjacent-carrier-equative",
])
def test_new_premises_are_generatable_and_round_trip(project_name, rule):
    project = load_project(Path("projects") / project_name)
    candidate = generate_candidate(project, rule_id=f"arithmetic/{rule}", seed=11)
    assert candidate.target_status == "matched"
    assert candidate.facts
    if rule == "bounded-sequence-anaphoric-total":
        assert candidate.context_before


@pytest.mark.parametrize("event", ["feast a ship", "feast in a ship", "deliver on a box"])
def test_event_preposition_is_part_of_its_declared_frame(reg, event):
    result = solve(
        f"Mira returns once every two days to {event}. "
        "Over six days, Mira has consumed 70 toys. "
        "Each new ship has twice as many toys as the last ship. "
        "How many toys were in the first ship?", reg,
    )
    assert not result.store.by_kind(EventCadence)
    assert not result.answer.committed


@pytest.mark.parametrize("step", ["once as many", "double as many", "triple as many"])
def test_frequency_and_predeterminers_do_not_replace_comparison_forms(reg, step):
    result = solve(story(step=step), reg)
    assert not result.store.by_kind(SequenceStep)
    assert not result.answer.committed


def test_predeterminers_cannot_state_an_event_frequency(reg):
    result = solve(story().replace("once every", "double every"), reg)
    assert not result.store.by_kind(EventCadence)
    assert not result.answer.committed


@pytest.mark.parametrize("total,count,factor,offset,expected", [
    (70,3,2,0,[10,20,40]),
    (70,3,.5,0,[40,20,10]),
    (60,3,1,5,[15,20,25]),
    (60,3,1,-5,[25,20,15]),
    (46,3,2,1,[6,13,27]),
    (15,1,3,8,[15]),
])
def test_affine_algebra_reuses_one_logged_path(total,count,factor,offset,expected):
    log=ArithmeticLog()
    assert affine_terms_from_total(total,count,factor,offset,log) == pytest.approx(expected)
    assert log.entries


@pytest.mark.parametrize("args", [(1,0,2,0),(1,1001,2,0),(1,3,-2,0),(-1,3,2,0),
                                 (1,3,1,10),(1,3,float("inf"),0),(1,1000,1e300,0)])
def test_invalid_or_explosive_algebra_declines(args):
    assert affine_terms_from_total(*args, ArithmeticLog()) is None
