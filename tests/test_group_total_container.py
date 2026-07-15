"""The distributive-container consumer on the `single-entity` path.

SYNTHETIC ONLY (constitution rule 3). No GSM8K or ASDiv string appears here — the
mechanism is exercised on invented containers (tables/plates, boxes/pens), never
the benchmark item that surfaced it.

WHY IT EXISTS. A cross-corpus (ASDiv) confident-wrong: "There were 150 shelves.
Each shelf had 15 books. How many books were on the shelves?" The engine
synthesizes the correct group total (2250) AND folds the resolved container's own
per-container rate (15) — and committed the RATE. GSM8K could not reveal it (its
ask shapes happen not to resolve a counted container as the fold entity).

TWO STAGES, both pinned here. First this shipped as a DECLINE (a counted container
+ a group total is ambiguous: "the shelves" all -> 2250 vs "a shelf" one -> 15).
Then saturate's synth was tightened so a SPECIFIC instance's count ("bucket B has
30", "the first warehouse has 400") no longer masquerades as a per-container rate
(learn.py provenance.distributive gate) — with the garbage totals gone, the
surviving group total is trustworthy and IS the answer, so the consumer now COMMITS
it. The distinct-value test below proves the specific-instance garbage is gone.

THE TIGHTNESS INVARIANT (the named-holder test) is load-bearing: the consumer must
NOT fire for a NAMED holder whose own fold is correct and merely coexists with an
unrelated document total — else it would break every legitimate named fold. The
container signature (the entity is itself a counted thing) is what keeps it tight.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import GroupTotal


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_counted_container_commits_the_group_total(reg):
    """The core case. A counted container ('20 tables') holds a per-container
    rate ('each table had 6 plates') and saturate synthesizes the trustworthy
    whole (GroupTotal plate=120). The ask ('how many plates were on the tables')
    wants that whole — the consumer commits 120, not the per-container 6."""
    r = solve(
        "There were 20 tables. Each table had 6 plates. How many plates were on the tables?",
        reg, tracing=False,
    )
    assert any(g.measure == "plate" and g.value == 120.0 for g in r.store.by_kind(GroupTotal))
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 120.0
    assert "group total" in (r.answer.reason or "")


def test_specific_instance_count_is_not_a_rate(reg):
    """The synth-tightening invariant. A SPECIFIC instance's count ('crate 2 had
    9 apples') is NOT a per-container rate, so no group total is derived from it —
    the garbage that this whole line of work removed. With no trustworthy whole,
    the consumer does not fire and the item declines rather than commit a bogus
    N x N total."""
    r = solve(
        "There were 5 crates. Crate 2 had 9 apples. How many apples were on the crates?",
        reg, tracing=False,
    )
    assert not any(g.measure == "apple" for g in r.store.by_kind(GroupTotal)), \
        "a specific instance's count must not derive a distributive group total"


def test_named_holder_with_unrelated_total_still_commits(reg):
    """THE TIGHTNESS INVARIANT. A GroupTotal for the asked measure coexists, but
    the named holder is NOT a counted container — its own fold is correct and must
    survive. If this ever declines, the guard has gone as broad as the entity-less
    one and would break legitimate named folds."""
    r = solve(
        "There are 90 apples altogether. Rina has 5 apples. How many apples does Rina have?",
        reg, tracing=False,
    )
    assert any(g.measure == "apple" for g in r.store.by_kind(GroupTotal)), \
        "precondition: a group total for the asked measure must exist"
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 5.0


def test_plain_single_entity_unaffected(reg):
    """Regression floor: with no group total in play the guard is inert."""
    r = solve("Rina has 5 apples. How many apples does Rina have?", reg, tracing=False)
    assert r.answer.committed
    assert r.answer.value == 5.0
