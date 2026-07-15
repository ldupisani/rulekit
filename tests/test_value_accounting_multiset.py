"""value-accounting multiplicity: a repeated stated value needs a fact per mention.

SYNTHETIC ONLY (constitution rule 3). No GSM8K or ASDiv string appears here.

WHY IT EXISTS. `value-accounting` vetoes a commit when a stated count reached no
fact. It kept a PER-SENTENCE *set* of fact values, so two mentions of the same
number were both satisfied by a single fact of that value — the same-value blind
spot. A different corpus (ASDiv) exposed it: "walked nine miles on Monday and nine
more on Tuesday" states 'nine' twice, the elided second mention forms no fact, yet
the lone 9-fact masked it and the engine committed 9 (gold 18). Its distinct-value
sibling ("...seven more...") already declined — the fix makes same-value behave the
same. A *Counter* (multiset) closes it: each mention CLAIMS one fact of its value.

The guard is DECLINE-ONLY — it can only turn a masked commit into a decline, never
create a wrong. It removes masked wrongs from more than one root cause (an elided
"N more", and a same-value conjunct dropped at fact-admit time).
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_repeated_value_elided_second_mention_declines(reg):
    """The core case. A second same-value mention ('four more') that forms no
    fact must not be masked by the first's fact — decline, don't commit a subset."""
    r = solve(
        "Mona ran four laps in the morning and four more in the evening. "
        "How many laps did Mona run?",
        reg, tracing=False,
    )
    assert not r.answer.committed, f"committed {r.answer.value!r} on a masked partial reading"
    assert "value-accounting" in (r.answer.reason or "")


def test_same_value_dropped_conjunct_declines(reg):
    """Same blind spot, a different root cause: a same-value second conjunct that
    never became a fact. Before the multiset fix this silently committed the lone
    fact (a confident wrong); now it declines."""
    r = solve(
        "Sam has three red pens and three blue pens. How many pens does Sam have?",
        reg, tracing=False,
    )
    assert not r.answer.committed, f"committed {r.answer.value!r} — a masked dropped conjunct"
    assert "value-accounting" in (r.answer.reason or "")


def test_distinct_values_both_resolved_still_commit(reg):
    """TIGHTNESS. Two conjuncts with DISTINCT values both form facts (supply meets
    demand) — the guard stays inert and the fold commits."""
    r = solve(
        "Sam has three red pens and four blue pens. How many pens does Sam have?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 7.0


def test_same_value_across_sentences_still_commits(reg):
    """TIGHTNESS, the load-bearing one for the multiset change: the supply is kept
    PER SENTENCE. Two sentences each stating 'three' with their own 3-fact must
    each claim their own slot — the sum commits, never falsely vetoed."""
    r = solve(
        "Sam has three pens. Amy has three pens. How many pens do they have together?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 6.0
