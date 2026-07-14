"""Mining increment 103: partitive-qualified measure
asks ("how many CUPS OF FLOUR / PAIRS OF SHOES / POUNDS OF X does WHO
have?"). No ask in this file could bind a postnominal "of SUBSTANCE" tail
at all outside the entity-less "there"/"left"/"combined" siblings the
earlier partitive-measure-ask-slot candidate wired up (mining candidate
partitive-measure-ask-slot, increment 84) — a NAMED-holder single/paired
question phrased through a partitive NP ("how many pairs of shoes does Ann
have?", "how many more pairs of shoes does Ann have than Bob?", "how many
cups of flour do they have altogether?") failed EVERY ask's match and
declined with "no ask shape recognizes this question" before any consumer
was ever consulted.

Mechanism (packs/arithmetic/rules/core.yaml, four NEW ask ids — no existing
ask is edited):

- ask/how-many-in-place-partitive (single-entity consumer, entity-less
  container/place reads)
- ask/how-many-combined-partitive / ask/how-many-combined-named-partitive
  (combined consumer, pronoun and named-pair totality reads)
- ask/how-many-more-partitive (difference consumer, named-pair comparison)

Each requires a REQUIRED (not optional) `{lit: of} {slot: qual, type:
noun}` tail right after `item` — a NEW ask id consuming 2 more units than
its bare sibling, never a widening of that sibling's own match, so a
partitive tail fails every bare sibling's match outright (no partial-match
tie in either direction: see each ask's own core.yaml comment for the
non-tie argument).

`qual` feeds two existing fields, never a new one:
- `measure_qualifier` (single-entity consumer only — increment 70's
  qualified-measure-keys): retries the exact "{measure}[{qual}]" key the
  premise-side SVO fold already writes for a partitive-NP quantity
  (learn.py's `_measure_substance`, mining candidate
  partitive-measure-ask-slot) before ever touching the bare-measure
  fallback.
- `measure_substance` (combined/difference consumers — the SAME
  decline-safety guard, `_measure_substance_guard`, ask/how-many-there-
  combined and ask/how-many-passive-combined already bind): declines
  rather than silently mixing a DIFFERENT substance under the same bare
  measure noun into the fold. The `difference` consumer had NO such guard
  before this candidate (answer.py) — a small, opt-in (query-gated) kernel
  addition mirroring the three pre-existing call sites exactly; every
  EXISTING (non-partitive) `difference` ask never binds `measure_substance`
  so the new guard call is a no-op for all of them.

SCOPED OUT at ship time (found during development, not forced): a
single-holder partitive sibling of ask/how-many-entity ("how many PAIRS OF
SHOES does Ann have?", `single-entity` consumer) was drafted and DROPPED —
the dev-train gate caught two confident wrongs the moment it started
matching questions this ask family had always declined (a unit-conversion
mismatch and a relation-derived quantity with no qualified key of its
own — see core.yaml's own comment at that scope point for the full
account). This candidate measures ZERO items solved on dev-train/holdout
by itself (infrastructure only, proven by the unchanged 79/32 correct
counts) — it is the enabler a follow-up candidate cashes in by pairing
these ask surfaces with additional standard-marker/relation machinery.

Synthetic only.
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


def test_partitive_combined_pronoun_resolves(full_registry):
    # ask/how-many-combined-partitive: two named holders of the SAME
    # partitive-qualified measure, totality marker required.
    r = solve(
        "Ravi has 5 pairs of shoes. Nita has 9 pairs of shoes. "
        "How many pairs of shoes do they have altogether?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 14


def test_partitive_combined_named_resolves(full_registry):
    # ask/how-many-combined-named-partitive: the named-pair sibling,
    # a/b bound directly instead of enumerated.
    r = solve(
        "Ravi has 5 pairs of shoes and Nita has 9 pairs of shoes. "
        "How many pairs of shoes do Ravi and Nita have combined?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 14


def test_partitive_difference_resolves(full_registry):
    # ask/how-many-more-partitive: the minimal pair this candidate's own
    # brief evidences ("Ann has 7 pairs of shoes. Bob has 5 pairs of
    # shoes...") — the identical text with the ask's qualifier dropped
    # ('how many more pairs...') already resolved via the bare `difference`
    # consumer; this ask reaches the SAME consumer over the partitive
    # phrasing of the question itself.
    r = solve(
        "Ann has 7 pairs of shoes. Bob has 5 pairs of shoes. "
        "How many more pairs of shoes does Ann have than Bob?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 2


def test_partitive_in_place_resolves(full_registry):
    # ask/how-many-in-place-partitive: an entity-less container read,
    # entity bound from the question's own "in PLACE" tail. Two SUBSTANCES
    # share the same place and bare measure noun ('cup') — the qualified
    # key ("cup[flour]") resolves the exact one asked about.
    r = solve(
        "The kitchen has 12 cups of flour. The kitchen has 9 cups of sugar. "
        "How many cups of flour are in the kitchen?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 12
    r2 = solve(
        "The kitchen has 12 cups of flour. The kitchen has 9 cups of sugar. "
        "How many cups of sugar are in the kitchen?",
        full_registry,
    )
    assert r2.answer.committed
    assert r2.answer.value == 9


def test_combined_pronoun_declines_on_mismatched_substance(full_registry):
    # THE decline-safety gate: two holders of the same bare measure
    # ('pair') but DIFFERENT substances ('shoe' vs 'boot') — without the
    # `measure_substance` guard, `_combined_holder_totals` would enumerate
    # BOTH holders and silently sum 5 + 9 = 14 regardless of which
    # substance was asked, a confident wrong. With it, this declines.
    r = solve(
        "Ravi has 5 pairs of shoes. Nita has 9 pairs of boots. "
        "How many pairs of shoes do they have altogether?",
        full_registry,
    )
    assert not r.answer.committed
    assert "more than one substance" in r.answer.reason


def test_combined_named_declines_on_mismatched_substance(full_registry):
    # the named-pair sibling gets the identical guard (it is bound in the
    # SAME query field the pronoun ask uses, and `_measure_substance_guard`
    # runs unconditionally before the a/b-vs-enumerate branch).
    r = solve(
        "Ravi has 5 pairs of shoes and Nita has 9 pairs of boots. "
        "How many pairs of shoes do Ravi and Nita have combined?",
        full_registry,
    )
    assert not r.answer.committed
    assert "more than one substance" in r.answer.reason


def test_difference_declines_on_mismatched_substance(full_registry):
    # this candidate's new guard call in the `difference` branch of
    # answer.py: Bob's own quantity is a DIFFERENT substance ('boot') under
    # the same bare measure ('pair') as what Ann's question asks about
    # ('shoe') — must decline, never silently answer from Bob's boot count.
    r = solve(
        "Ann has 7 pairs of shoes. Bob has 5 pairs of boots. "
        "How many more pairs of shoes does Ann have than Bob?",
        full_registry,
    )
    assert not r.answer.committed
    assert "more than one substance" in r.answer.reason


def test_single_holder_partitive_stays_out_of_scope(full_registry):
    # ask/how-many-entity deliberately did NOT get a partitive sibling
    # (see core.yaml's own comment at that scope point for the two
    # confident wrongs that ruled it out during development) — a
    # partitive-measure question in the "does WHO have" shape must still
    # decline exactly as before this candidate.
    r = solve(
        "Tom has 8 kilograms of rice. How many kilograms of rice does Tom have?",
        full_registry,
    )
    assert not r.answer.committed
    assert r.answer.reason == "no ask shape recognizes this question"


def test_bare_combined_ask_is_unaffected(full_registry):
    # no-regression: an ordinary bare-measure combined ask, no partitive
    # tail anywhere in the question, must resolve exactly as before this
    # candidate — the new partitive siblings simply fail to match it.
    r = solve(
        "Ravi has 5 shoes. Nita has 9 shoes. How many shoes do they have altogether?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 14


def test_bare_difference_ask_is_unaffected(full_registry):
    # no-regression: the new opt-in `measure_substance` guard in the
    # `difference` branch is never even called for a bare (non-partitive)
    # ask, since that ask never binds the field.
    r = solve(
        "Ann has 7 shoes. Bob has 5 shoes. How many more shoes does Ann have than Bob?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 2
