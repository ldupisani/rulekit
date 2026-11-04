"""Synthetic excess-tier policies and repeated schedules; no corpus prose."""

from pathlib import Path
from dataclasses import replace

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, list_rule_availability
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import Rate, RateThreshold, RatePremium, RepeatedActivityDuration, Quantity
from rulekit.kernel.tokenize import tokenize
from rulekit.kernel.facts import FactStore


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def project(request):
    return load_project(Path("projects") / request.param)


def story(*, rate=20, threshold=6, elapsed=9, repeats=4, premium="1/4", period="day"):
    return (
        f"Mira earns ${rate} an hour. "
        f"If she works more than {threshold} hours per shift, she is eligible "
        f"for overtime, which is paid by your hourly wage + {premium} your hourly wage. "
        f"If she works {elapsed} hours every {period} for {repeats} {period}s, "
        "how much money does she earn?"
    )


@pytest.mark.parametrize("elapsed,repeats,premium,expected", [
    (9, 4, "1/4", 780),
    (6, 4, "1/4", 480),
    (3, 4, "1/4", 240),
    (9, 2, "1/2", 420),
    (9, 4, "one third of", 800),
    (7.5, 2, "1/2", 330),
    (0, 4, "1/4", 0),
])
def test_threshold_resets_before_each_repetition(project, elapsed, repeats, premium, expected):
    result = solve(story(elapsed=elapsed, repeats=repeats, premium=premium), project.registry)
    assert (result.answer.kind, result.answer.value) == ("number", expected), result.answer
    assert "one shift" in result.answer.reason
    assert [a.id for a in result.answer.assumptions] == ["one-session-per-scheduled-period"]
    assert len(result.store.by_kind(RateThreshold)) == 1
    assert len(result.store.by_kind(RatePremium)) == 1
    assert len(result.store.by_kind(RepeatedActivityDuration)) == 1
    assert not result.store.by_kind(Quantity)  # a policy is not performed time
    assert not result.deficiencies()


@pytest.mark.parametrize("old,new", [
    ("+ 1/4", "plus 1/4"),
    ("paid by", "paid at"),
    ("$20", "20 dollars"),
    ("Mira", "Tova"),
    ("earns", "makes"),
    ("9 hours", "540 minutes"),
    ("6 hours", "360 minutes"),
    ("how much money", "how much"),
])
def test_equivalent_surfaces_keep_the_same_arithmetic(project, old, new):
    text = story().replace(old, new)
    if old == "earns":
        text = text.replace("she earn?", "she make?")
    result = solve(text, project.registry)
    assert result.answer.value == 780, result.answer


def test_explicit_shift_repetition_needs_no_daily_assumption(project):
    result = solve(story(period="shift"), project.registry)
    assert result.answer.value == 780, result.answer
    assert "treating" not in result.answer.reason
    assert not result.answer.assumptions


def test_schedule_without_a_tier_uses_only_stated_base_rate(project):
    result = solve(
        "Tova earns $16 an hour. Tova works 3 hours every day for 4 days. "
        "How much money does Tova earn?", project.registry,
    )
    assert result.answer.value == 192, result.answer


@pytest.mark.parametrize("old,new", [
    ("+", "-"), ("+", "×"), ("+", "/"), ("+", ""),
    ("more than", "less than"),
    ("more than", "at least"),
    ("per shift", "per week"),
    ("every day", "every week"),
    ("4 days", "4 weeks"),
    ("4 days", "2.5 days"),
    ("9 hours", "9 apples"),
    ("9 hours", "-9 hours"),
    ("$20", "-$20"),
    ("6 hours", "6 apples"),
    ("an hour.", "a day."),
    ("your hourly wage.", "your wage."),
    ("your hourly wage.", "my hourly wage."),
    ("she is eligible", "Tova is eligible"),
    ("she is eligible", "she is not eligible"),
    ("which is paid", "which is not paid"),
    ("which is paid", "which may be paid"),
    ("she works 9", "Tova works 9"),
    ("she works 9", "she can work 9"),
    ("she works 9", "she never works 9"),
    ("she earn?", "Tova earn?"),
    ("she earn?", "she spend?"),
    ("she earn?", "she earn in 3 days?"),
    ("how much money", "how much money in pounds"),
    ("20 an hour", "20 an hour for tutoring"),
    ("20 an hour.", "20 an hour without overtime."),
    ("20 an hour.", "20 an hour with a bonus."),
    ("she earn?", "she earn without overtime?"),
])
def test_unsupported_or_conflicting_policy_neighbours_decline(project, old, new):
    result = solve(story().replace(old, new), project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("extra", [
    "Mira earned $20.",
    "Mira works 9 hours.",
    "Mira earns $20 a day.",
    "Mira earns $30 an hour.",
    "Mira works 9 hours every day for 4 days.",
    "Tova works 9 hours every day for 4 days.",
])
def test_an_extra_equal_or_distinct_given_is_not_silently_ignored(project, extra):
    text = story().replace("If she works 9", extra + " If she works 9")
    result = solve(text, project.registry)
    assert not result.answer.committed, result.answer


def test_eligibility_without_rate_definition_does_not_guess_time_and_a_half(project):
    text = story().replace(
        ", which is paid by your hourly wage + 1/4 your hourly wage", ""
    )
    result = solve(text, project.registry)
    assert not result.answer.committed
    assert "both be stated" in result.answer.reason


def test_unrelated_flat_total_cannot_ignore_a_policy(project):
    text = story().replace("how much money does she earn?", "how many hours does she work?")
    assert not solve(text, project.registry).answer.committed


def test_new_core_vocabulary_keeps_existing_wage_and_physics_paths(project):
    assert solve("Mira earns $20 an hour. How much does Mira earn in 3 hours?", project.registry).answer.value == 60
    assert solve("Mira earned $20. How much money did Mira earn?", project.registry).answer.value == 20
    assert solve("What is the power if 120 joules of work is done over 6 seconds?", project.registry).answer.value == 20


def test_symbol_boundaries_survive_tokenization():
    for operator in ("+", "-", "×", "−", "=", "*"):
        reading = tokenize(f"wage {operator} 1/4 wage")
        assert operator in [u.surface for u in reading.units]
    reading = tokenize("a 120-page book and a button-up shirt")
    assert "-" not in [u.surface for u in reading.units]


@pytest.mark.parametrize("surface,value", [("-90", -90), ("-$20.50", -20.5), ("-12%", -0.12)])
def test_adjacent_sign_belongs_to_the_numeric_token(project, surface, value):
    reading = analyze(surface, project.registry)
    assert len(reading.units) == 1
    assert reading.units[0].features["value"] == value


@pytest.mark.parametrize("kind,field,value", [
    (RateThreshold, "value", 12.0),
    (RatePremium, "fraction", 0.5),
    (RepeatedActivityDuration, "elapsed", 3.0),
])
def test_conflicting_structured_fact_values_are_quarantined(project, kind, field, value):
    fact = solve(story(), project.registry).store.by_kind(kind)[0]
    store = FactStore()
    store.admit(fact)
    store.admit(replace(fact, **{field: value}))
    assert store.collisions


def test_new_activity_tier_and_rate_noun_extend_through_pack_data(tmp_path):
    root = Path(__file__).resolve().parents[1]
    extension = tmp_path / "extension"
    extension.mkdir()
    (extension / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: invented-rate-policy\nversion: 0.1.0\n"
    )
    (extension / "lexicon.yaml").write_text("""\
format: rulekit/lexicon@1
entries:
  labor: {senses: [verb]}
  labors: {senses: [verb], number: singular, verb: {lemma: labor}}
  uplift: {senses: [noun]}
  stipend: {senses: [noun]}
""")
    (extension / "categories.yaml").write_text("""\
format: rulekit/categories@1
members:
  scheduled_activity_verb: [labor, labors]
  rate_tier_noun: [uplift]
  rate_basis_noun: [stipend]
""")
    (tmp_path / "project.yaml").write_text(
        "format: rulekit/project@1\nname: invented-rate-policy\npacks:\n"
        f"  - {root / 'packs/core-english'}\n  - {root / 'packs/arithmetic'}\n"
        "  - ./extension\n"
    )
    text = story().replace("works", "labors").replace("overtime", "uplift").replace("wage", "stipend")
    result = solve(text, load_project(tmp_path).registry)
    assert result.answer.value == 780, result.answer


@pytest.mark.parametrize("rule_id", [
    "arithmetic/activity-threshold-eligibility",
    "arithmetic/relative-additive-rate-premium",
    "arithmetic/repeated-activity-duration",
])
def test_policy_components_generate_and_round_trip(project, rule_id):
    available = {a.id: a for a in list_rule_availability(project)}
    assert available[rule_id].supported, available[rule_id]
    for seed in (3101, 3102):
        candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
        assert candidate.target_status in {"matched", "shadowed"}
