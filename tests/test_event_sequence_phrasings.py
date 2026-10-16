"""Nominal effects and participial results in bounded event progressions."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def question(event="storm", item="trees", seed="nominal", relation="cause", descriptor="collapsed", aggregate="amount", motive=False):
    first = f"the collapse of 3 {item}" if seed == "nominal" else f"3 {item} to collapse"
    explanation = ", since each one would make the foundations less stable" if motive else ""
    return (
        f"A {event} caused {first}. Experts predicted that each following {event} "
        f"would {relation} double the {aggregate} of {descriptor} {item} as the previous one{explanation}. "
        f"After 2 more {event}s, how many {item} had collapsed including those from the first {event}?"
    )


@pytest.mark.parametrize("event,item", [("storm", "trees"), ("earthquake", "houses")])
@pytest.mark.parametrize("seed", ["nominal", "infinitive"])
@pytest.mark.parametrize("relation,descriptor", [("cause", "collapsed"), ("have", "collapsed"), ("cause", "collapsing"), ("have", "collapsing")])
@pytest.mark.parametrize("aggregate", ["amount", "number"])
@pytest.mark.parametrize("motive", [False, True])
def test_equivalent_event_result_constructions(reg, event, item, seed, relation, descriptor, aggregate, motive):
    result = solve(question(event, item, seed, relation, descriptor, aggregate, motive), reg)
    assert result.answer.value == 21, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("collapse of 3", "collapse of 3.5"),
    lambda q: q.replace("collapsed trees as", "collapsed houses as"),
    lambda q: q.replace("following storm", "following earthquake"),
    lambda q: q.replace("previous one", "previous two"),
    lambda q: q.replace("first storm", "second storm"),
    lambda q: q.replace("After 2", "After 2.5"),
    lambda q: q.replace("After 2", "There are 5 houses. After 2"),
])
def test_nominal_effect_boundaries(reg, edit):
    assert not solve(edit(question()), reg).answer.committed
