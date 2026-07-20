"""The conjoined-measure anchored relation, and `label-difference`'s holder hint.

SYNTHETIC ONLY (constitution rule 3) — invented scenarios, never a benchmark
string. NOUNS must be lexicon words (see test_conjoined_existential.py's
header for why an invented noun makes a reading test meaningless).

WHY IT EXISTS, part 1 (the reader). `arithmetic/anchored-relation` requires
`than` after a SINGLE item, so "Ana has 6 fewer buttons and 8 more ribbons
than Bo" failed its match outright and minted NO relation at all — not one
relation with a dropped conjunct, but nothing. Both conjuncts share the one
trailing standard, so the conjoined rule emits two Relations differing only
in measure and offset. This is the SAME per-construction conjunction
asymmetry the conjoined existential closed.

WHY IT EXISTS, part 2 (the holder hint). Reading that relation DERIVES the
subject's quantities — which is what made the reader useless on its own:
'button' then has two holders, and `label-difference`'s exactly-one-SHARED-
holder discipline (correctly, on its own terms) refused. The held ask names
the holder, so the consumer now uses it WHEN that entity holds both
measures.

THE FALLBACK IS THE LOAD-BEARING PART. The hint is ignored, never a
decline, when it does not resolve — `who` binds the question's surface
holder, which legitimately fails to match a fact key when the SCENE holds
the quantities ("In a drawer there are..." puts both facts on `world`
while the ask says "does the drawer have"). A decline there would break
the existential reading the ask was built for. `test_holder_hint_falls_
back_to_the_scene_holder` pins exactly that.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Relation


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def _rels(result):
    return {(f.subject, f.standard, f.measure): f.offset
            for f in result.store.by_kind(Relation)}


def _qty(result):
    return {(q.entity, q.measure): q.value for q in result.store.by_kind(Quantity)}


def test_conjoined_relation_mints_both_conjuncts(reg):
    """The gap itself: this sentence minted NOTHING before."""
    r = solve("Ana has 6 fewer buttons and 8 more ribbons than Bo.", reg)
    assert _rels(r) == {
        ("ana", "bo", "button"): -6.0,
        ("ana", "bo", "ribbon"): 8.0,
    }


def test_conjoined_relation_resolves_against_the_standard(reg):
    """Both conjuncts share the ONE trailing standard, and saturate derives
    the subject's quantities from it."""
    q = _qty(solve(
        "Ana has 6 fewer buttons and 8 more ribbons than Bo. "
        "Bo has 17 buttons and 16 ribbons.", reg))
    assert q[("ana", "button")] == 11.0
    assert q[("ana", "ribbon")] == 24.0


def test_single_conjunct_relation_is_untouched(reg):
    """The conjoined rule is strictly longer, so the one-measure sentence
    still routes to arithmetic/anchored-relation."""
    r = solve("Ana has 6 fewer buttons than Bo.", reg)
    assert _rels(r) == {("ana", "bo", "button"): -6.0}


def test_holder_hint_scopes_past_a_second_holder(reg):
    """THE BUYER, both halves together. The derived 'ana' button quantity
    gives 'button' two holders, so the uniqueness discipline alone refuses;
    the question names Bo, who holds both measures."""
    r = solve(
        "Ana has 6 fewer buttons than Bo. Bo has 17 buttons and 16 ribbons. "
        "How many more buttons than ribbons does Bo have?",
        reg,
    )
    assert r.value == 1.0


def test_holder_hint_falls_back_to_the_scene_holder(reg):
    """THE FALLBACK. 'drawer' never matches a fact key — both quantities sit
    on the `world` scene-holder — so the hint must be IGNORED, not declined,
    or the existential reading this ask was built for breaks."""
    r = solve(
        "In a drawer there are 9 ribbons and 5 buttons. "
        "How many more ribbons than buttons does the drawer have?",
        reg,
    )
    assert r.value == 4.0


def test_two_unrelated_holders_still_decline(reg):
    """The discipline is intact where the hint cannot rescue it: the named
    holder holds only ONE measure, and no single entity holds both."""
    r = solve(
        "Ana has 9 ribbons. Bo has 5 buttons. "
        "How many more ribbons than buttons does Ana have?",
        reg,
    )
    assert r.value is None


def test_self_referential_conjunct_is_refused(reg):
    """`distinct_measure` is checked on BOTH conjuncts: an elliptical
    measure comparison ('fewer X than Y' where Y is a MEASURE, not a
    holder) must not mint a relation whose standard is the measure being
    counted — and it can appear in either conjunct independently."""
    r = solve("Ana has 2 fewer buttons and 3 more ribbons than buttons.", reg)
    assert _rels(r) == {}
