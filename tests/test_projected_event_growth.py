"""Source-audited proportional growth and fractional event projections."""
from fractions import Fraction

import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.predicate_compatibility import predicates_compatible


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def story(start=6, share="25%", extra=3, forecast="Experts predicted that ", modal="would ", event="storm", item="houses"):
    return (
        f"A {event} caused the destruction of {start} {item}. "
        f"{forecast}each following {event} {modal}cause {share} more {item} to collapse. "
        f"After {extra} more {event}s, how many {item} had been destroyed including those from the first {event}?"
    )


@pytest.mark.parametrize("event,item", [("storm", "houses"), ("tornado", "buildings")])
@pytest.mark.parametrize("share,rate", [("25%", Fraction(5, 4)), ("half", Fraction(3, 2)), ("150%", Fraction(5, 2)), ("0%", Fraction(1))])
@pytest.mark.parametrize("extra", [0, 1, 3])
def test_projected_growth_keeps_fractional_terms(reg, event, item, share, rate, extra):
    r = solve(story(share=share, extra=extra, event=event, item=item), reg)
    assert r.answer.value == pytest.approx(float(sum(6 * rate ** i for i in range(extra + 1)))), r.answer
    assert not r.deficiencies()
    assert "without rounding" in r.answer.reason


@pytest.mark.parametrize("forecast,modal", [("", "would "), ("Experts predicted that ", "")])
def test_either_explicit_forecast_or_modal_licenses_projection(reg, forecast, modal):
    q = story(forecast=forecast, modal=modal)
    if not modal:
        q = q.replace("storm cause ", "storm causes ")
    assert solve(q, reg).answer.value == pytest.approx(34.59375)


def test_actual_counts_still_require_whole_terms(reg):
    q = story(forecast="", modal="").replace("storm cause ", "storm causes ")
    assert not solve(q, reg).answer.committed
    q = story(start=16, extra=2, forecast="", modal="").replace("storm cause ", "storm causes ")
    assert solve(q, reg).answer.value == 61


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("3 more storms", "3.5 more storms"),
    lambda q: q.replace("3 more storms", "1000 more storms"),
    lambda q: q.replace("destruction of 6", "destruction of 6.5"),
    lambda q: q.replace("following storm", "following tornado"),
    lambda q: q.replace("more houses to collapse", "more buildings to collapse"),
    lambda q: q.replace("first storm", "second storm"),
    lambda q: q.replace("After 3", "There are 9 buildings. After 3"),
])
def test_projection_does_not_relax_scope_or_source_audit(reg, edit):
    assert not solve(edit(story()), reg).answer.committed


def test_structural_equivalence_is_object_scoped(reg):
    assert predicates_compatible("destruction", "collapse", "building", reg)
    assert not predicates_compatible("destruction", "collapse", "money", reg)
    assert not predicates_compatible("destruction", "repair", "building", reg)


def test_alternate_tornado_plural(reg):
    assert solve(story(event="tornado").replace("tornados", "tornadoes"), reg).answer.value == pytest.approx(34.59375)


@pytest.mark.parametrize("share", ["25 percent", "one quarter", "a quarter"])
def test_equivalent_fraction_surfaces(reg, share):
    assert solve(story(share=share), reg).answer.value == pytest.approx(34.59375)


@pytest.mark.parametrize("replacement", ["had destroyed", "had been destroy"])
def test_transitive_result_requires_a_passive_participle(reg, replacement):
    assert not solve(story().replace("had been destroyed", replacement), reg).answer.committed


def test_counted_group_ask_does_not_accept_mass_litter(reg):
    q = "Aven has 3 apples. Bira has 5 apples. How many litter do all of them have together?"
    assert not solve(q, reg).answer.committed
    assert solve(q.replace("litter", "apples"), reg).answer.value == 8


def test_fractional_count_comparison_requires_plural_objects(reg):
    assert not solve(story().replace("more houses", "more house"), reg).answer.committed
