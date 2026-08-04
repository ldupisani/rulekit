"""The conjoined existential premise reader and its held-comparative ask.

SYNTHETIC ONLY (constitution rule 3) — invented scenarios, never a benchmark
string. The NOUNS must be lexicon words (an unknown word mints no fact at
all, so a test written with invented vocabulary passes or fails for reasons
that have nothing to do with the rule under test — this file's first draft
used 'widget'/'gadget' and failed on all four reading assertions).

WHY IT EXISTS. `arithmetic/existential-premise-bare` matched a single
`{slot: item, type: counted}`, so "There are 5 buttons and 9 ribbons."
minted button=5 and NO ribbon fact at all. That is not a decline but a
SILENT PARTIAL READING: every downstream consumer saw a store missing a
quantity the sentence plainly states, and the `label-difference` consumer
then declined for "no shared holder" — a decline whose stated reason was
false. The ordinary SVO fold ("The jar has 5 buttons and 9 ribbons") had
always read the conjunction correctly; only the existential surface had
the gap.

THE ASK'S WORD ORDER IS THE GATE, and it is load-bearing (see the
`ask/how-many-more-label-comparative-held` comment): `than MEASURE` must
precede the auxiliary. The aux-first family ("how many more X did he lose
than those he gave", "...than on tuesday", "...than Jill") is verb-,
time- and entity-comparison wearing a comparative surface, NOT a measure
pair, and a rule reaching those would commit an entity difference as a
measure difference. `test_aux_first_comparative_is_not_this_class` pins
that exclusion.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def _quantities(result):
    return {(q.entity, q.measure): q.value for q in result.store.by_kind(Quantity)}


def test_conjoined_existential_mints_both_conjuncts(reg):
    """The gap itself: the second conjunct used to be dropped silently."""
    q = _quantities(solve("There are 5 buttons and 9 ribbons.", reg))
    assert q.get(("world", "button")) == 5.0
    assert q.get(("world", "ribbon")) == 9.0


def test_single_item_existential_is_untouched(reg):
    """The bare sibling still owns the no-tail sentence — the conjoined rule
    is strictly longer, so it cannot fire here."""
    r = solve("There are 12 buttons.", reg)
    assert _quantities(r).get(("world", "button")) == 12.0
    sources = {f.provenance.source for f in r.store.by_kind(Quantity)}
    assert sources == {"arithmetic/existential-premise-bare"}


def test_container_partitive_keeps_only_its_valid_head_count(reg):
    r = solve("There are 30 boxes of apples.", reg)
    assert _quantities(r).get(("world", "box")) == 30.0
    sources = {f.provenance.source for f in r.store.by_kind(Quantity)}
    assert sources == {"arithmetic/existential-premise-bare"}


def test_noncontainer_partitive_cannot_fall_back_to_a_bare_prefix(reg):
    r = solve("There are 40 fish of rabbit.", reg)
    assert ("world", "fish") not in _quantities(r)


def test_aggregate_marker_still_routes_to_total(reg):
    """`absent: {cat: aggregate}` is inherited verbatim: a totality marker
    makes this a SUM CONSTRAINT, never two independent holdings."""
    q = _quantities(solve("There are 5 buttons and 9 ribbons altogether.", reg))
    assert ("world", "button") not in q or q[("world", "button")] != 5.0


def test_held_comparative_answers_from_the_conjoined_premise(reg):
    """The buyer: reader + ask together. Neither half answers this alone."""
    r = solve(
        "In a drawer there are 9 ribbons and 5 buttons. "
        "How many more ribbons than buttons does the drawer have?",
        reg,
    )
    assert r.value == 4.0


def test_held_comparative_reads_an_svo_conjunction_too(reg):
    """The ask is not existential-specific — the SVO fold already minted
    both conjuncts, and the ask consumes that store identically."""
    r = solve(
        "The jar has 9 ribbons and 5 buttons. "
        "How many more ribbons than buttons does the jar have?",
        reg,
    )
    assert r.value == 4.0


def test_aux_first_comparative_is_not_this_class(reg):
    """THE HAZARD. Same words, aux-first order, a NAME after 'than': this is
    an entity comparison over a measure FOLD ((9+5)-3=11), not a measure
    difference (9-5=4). The ask must not match it, and the engine must not
    commit 4."""
    r = solve(
        "Ana has 9 ribbons and 5 buttons. Bo has 3 ribbons. "
        "How many more ribbons does Ana have than Bo?",
        reg,
    )
    assert r.value != 4.0


def test_two_labels_on_different_holders_still_decline(reg):
    """The consumer's exactly-one-SHARED-holder discipline is untouched by
    the new ask: two unrelated holders must never be subtracted."""
    r = solve(
        "Ana has 9 ribbons. Bo has 5 buttons. "
        "How many more ribbons than buttons does Ana have?",
        reg,
    )
    assert r.value is None
