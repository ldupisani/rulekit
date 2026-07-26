"""Scoped group totals.

Synthetic only.  These tests preregister the representation boundary exposed
by the Designer review of ``Total blue has 40 birds``: a total that names its
group must retain that identity, while genuinely unscoped total surfaces keep
their existing semantics.
"""

from rulekit.kernel.engine import solve
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import GroupTotal, Provenance, Quantity
from rulekit.kernel.totals import _qualified_variant_total


def _total(value: float, scope: str | None, source: str) -> GroupTotal:
    return GroupTotal(
        provenance=Provenance(source=source, sentence=0),
        measure="token",
        value=value,
        scope=scope,
    )


def test_same_measure_totals_for_distinct_scopes_coexist() -> None:
    store = FactStore()

    assert store.admit(_total(12, "amber", "reader/amber"))
    assert store.admit(_total(19, "cyan", "reader/cyan"))

    assert store.clean
    assert {
        (fact.scope, fact.value) for fact in store.by_kind(GroupTotal)
    } == {("amber", 12), ("cyan", 19)}


def test_same_scope_disagreement_remains_a_conflict() -> None:
    store = FactStore()

    assert store.admit(_total(12, "amber", "reader/first"))
    assert not store.admit(_total(19, "amber", "reader/second"))

    assert not store.clean
    assert store.by_kind(GroupTotal) == []
    assert store.collisions[0].key == ("group_total", "amber", "token")


def test_leading_group_total_retains_bound_scope(registry) -> None:
    result = solve(
        "Total blue has 40 birds. How many birds are there?",
        registry,
    )

    totals = result.store.by_kind(GroupTotal)
    assert len(totals) == 1
    assert totals[0].measure == "bird"
    assert totals[0].value == 40
    assert totals[0].scope == "blue"
    assert totals[0].provenance.source == "arithmetic/group-total-leading-marker"


def test_two_named_groups_over_one_measure_survive_together(registry) -> None:
    result = solve(
        "Total blue has 40 birds. Total red has 27 birds. "
        "How many birds are there?",
        registry,
    )

    assert result.store.clean
    assert {
        (total.scope, total.measure, total.value)
        for total in result.store.by_kind(GroupTotal)
    } == {
        ("blue", "bird", 40),
        ("red", "bird", 27),
    }


def test_tail_only_group_total_remains_unscoped(registry) -> None:
    result = solve(
        "There are 23 birds altogether. How many birds are there?",
        registry,
    )

    totals = result.store.by_kind(GroupTotal)
    assert len(totals) == 1
    assert totals[0].measure == "bird"
    assert totals[0].value == 23
    assert totals[0].scope is None


def test_trailing_marker_cannot_float_into_a_false_scoped_read(registry) -> None:
    result = solve(
        "Mira and Rovo buy birds together and have 30 birds total. "
        "How many birds are there?",
        registry,
    )

    totals = result.store.by_kind(GroupTotal)
    assert totals
    assert all(total.scope is None for total in totals)
    assert not any(
        match.match.rule.id == "arithmetic/group-total-leading-marker"
        for matches in result.document.rule_results.values()
        for match in matches
    )


def test_unrelated_scoped_total_does_not_block_named_variant_rollup(
    registry,
) -> None:
    store = FactStore()
    store.admit(
        Quantity(
            provenance=Provenance(source="reader/amber", sentence=0),
            entity="mira",
            measure="token[amber]",
            measure_qualifier="amber",
            value=7,
        )
    )
    store.admit(
        Quantity(
            provenance=Provenance(source="reader/cyan", sentence=1),
            entity="mira",
            measure="token[cyan]",
            measure_qualifier="cyan",
            value=11,
        )
    )
    store.admit(_total(50, "rovo", "reader/unrelated-total"))

    assert _qualified_variant_total(
        store, registry, "mira", "token", ArithmeticLog()
    ) == 18
