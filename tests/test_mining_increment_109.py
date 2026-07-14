"""Mining candidate combined-ask-holder-surfaces: combined/totality asks
whose HOLDER SET is a cardinal ("the three of them") or whose totality tail
is the unlexicalized "in all". Synthetic only.

Two new ask siblings (ask/how-many-combined-cardinal-pronoun, ask/how-much-
combined-cardinal-pronoun) match a bare cardinal holder set with an optional
literal "of them" tail ({slot: n, type: number} + opt[lit of, lit them] —
"them"/"us" carry no lexicon entry, so the tail is matched as grammatical-
skeleton LITERALS, never a `type: pronoun` slot) and route to the EXISTING
'combined' consumer, entity-less exactly like the pronoun-only ask/how-many-
combined: no a/b is bound, so every holder of the measure is enumerated.
The cardinal is threaded through as `holder_count: "{n.value}"`, which does
double duty: the `.value` template marks the cardinal consumed for value-
accounting (the same convention as `who_value` on ask/how-many-plural-
combined), and `answer.py`'s `combined` branch checks it against the number
of holders actually enumerated from the premises — declining rather than
silently summing a subset when the story under-reads a holder.

Also re-lands four "in all" totality-tail siblings (one per existing
'combined' ask: pronoun/named-pair x how-many/how-much) plus one partitive
sibling ("how many pairs of X do they have in all?"), each a literal
[in, all] tail scoped to its own ask id — 'all' keeps its `quantifier` sense
untouched; no lexicon or category change.

No new consumer; the only kernel touch is the `holder_count` check inside
`run_answer`'s existing `combined` branch (a no-op unless the key is bound).
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


# --- cardinal-pronoun holder set -------------------------------------------


def test_cardinal_pronoun_how_many_in_total(full_registry):
    r = solve(
        "Dara has 6 marbles. Tomas has 9 marbles. Vika has 3 marbles. "
        "How many marbles do the three of them have in total?",
        full_registry,
    )
    assert r.answer.value == 18


def test_cardinal_pronoun_how_much_altogether(full_registry):
    r = solve(
        "Dara has $6. Tomas has $9. Vika has $3. "
        "How much money do the three of them have altogether?",
        full_registry,
    )
    assert r.answer.value == 18


def test_cardinal_pronoun_no_of_them_tail(full_registry):
    # the "of them" tail is OPTIONAL: a bare cardinal before the verb must
    # resolve the same way ("how many marbles do the three have combined?").
    r = solve(
        "Dara has 6 marbles. Tomas has 9 marbles. Vika has 3 marbles. "
        "How many marbles do the three have combined?",
        full_registry,
    )
    assert r.answer.value == 18


def test_cardinal_pronoun_declines_on_holder_count_mismatch(full_registry):
    # decline-safety: the ask names THREE holders but only two are stated —
    # `holder_count` must veto rather than silently sum the pair.
    r = solve(
        "Dara has 6 marbles. Tomas has 9 marbles. "
        "How many marbles do the three of them have in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


# --- "in all" totality tail siblings ----------------------------------------


def test_pronoun_combined_in_all(full_registry):
    r = solve(
        "Priya has 6 kites. Omar has 4 kites. How many kites do they have in all?",
        full_registry,
    )
    assert r.answer.value == 10


def test_named_pair_combined_in_all(full_registry):
    r = solve(
        "Priya has 6 kites. Omar has 4 kites. "
        "How many kites do Priya and Omar have in all?",
        full_registry,
    )
    assert r.answer.value == 10


def test_how_much_combined_in_all_pronoun(full_registry):
    r = solve(
        "Priya has $6. Omar has $4. How much money do they have in all?",
        full_registry,
    )
    assert r.answer.value == 10


def test_how_much_combined_named_in_all(full_registry):
    r = solve(
        "Priya has $6. Omar has $4. How much money do Priya and Omar have in all?",
        full_registry,
    )
    assert r.answer.value == 10


def test_partitive_combined_in_all(full_registry):
    r = solve(
        "Mateo has 4 pairs of shoes. Elena has 7 pairs of shoes. "
        "How many pairs of shoes do they have in all?",
        full_registry,
    )
    assert r.answer.value == 11


def test_in_all_declines_on_unmatched_measure(full_registry):
    # decline-safety: the new tail must not let a combined ask fabricate a
    # total for a measure that was never stated.
    r = solve(
        "Priya has 6 kites. Omar has 4 kites. "
        "How many balloons do they have in all?",
        full_registry,
    )
    assert r.answer.kind == "decline"


# --- regression guard --------------------------------------------------


def test_cardinal_noun_subject_with_marker_still_resolves(full_registry):
    # Regression guard (synthetic, invented from scratch — every name,
    # number, and object changed from the mining-brief's evidence item):
    # a plural COMMON NOUN subject carrying its own cardinal ("the 3 kids")
    # plus a trailing aggregate marker was already answered correctly by
    # ask/how-many-plural-combined (which also binds `who_value` and
    # requires the marker). The new cardinal-pronoun ask's bare `n, type:
    # number` slot CAN also match a cardinal-merged noun (its value_kind is
    # "count" too), so on an id-order tie the new ask may win instead — but
    # both route to the identical 'combined' consumer's entity-less
    # enumeration, so the computed total must be unchanged either way, and
    # `holder_count` (which the true holder count of 3 satisfies) must
    # never turn this into a spurious decline.
    r = solve(
        "Mira, Toby, and Dan collected marbles. Mira had 12 more marbles "
        "than Toby. Toby had 4 less than Dan. Dan had 15 marbles. "
        "How many marbles did the 3 kids have in total?",
        full_registry,
    )
    dan = 15
    toby = dan - 4
    mira = toby + 12
    assert r.answer.value == mira + toby + dan
