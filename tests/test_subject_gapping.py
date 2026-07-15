"""Subject gapping / conjunction reduction — the anaphoric subject of a bare
coordinated verb.

SYNTHETIC ONLY (constitution rule 3). Invented sentences; no benchmark string.

"Tom gave 3 apples to Sam and [] bought 5 apples" — the second coordinated verb's
ELIDED subject is a zero anaphor whose antecedent is the FIRST clause's subject
(Tom), NOT the nearest noun (the recipient 'Sam') that the SYNTAX adjacency metric
would otherwise pick. obligations._gapped_subject_antecedent resolves it; the
distance arbitration is left untouched for every non-gapped subject.

Two downstream guards this surfaced are pinned alongside, because the correct
attribution is what exposes them: a comparative difference must not fold to an
absolute (test_..._comparative), and a singular-subject aggregate sums the one
holder (test_..._singular_total)."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def _q(store, entity, verb):
    return [
        q for q in store.by_kind(Quantity) if q.entity == entity and q.verb == verb
    ]


def test_bare_conjoined_verb_inherits_the_first_subject(reg):
    """The core case. 'bought' inherits Tom (the sentence subject), never Sam
    (the recipient of 'gave')."""
    r = solve("Tom gave 3 apples to Sam and bought 5 apples. How many apples does Tom have?", reg, tracing=False)
    assert _q(r.store, "tom", "buy") and _q(r.store, "tom", "buy")[0].value == 5.0
    assert not _q(r.store, "sam", "buy"), "the bought must not attach to the recipient"


def test_explicit_second_subject_is_not_overridden(reg):
    """Tightness: an EXPLICIT second subject ('...and SAM ate 2') is not gapped —
    the anaphoric resolution must not steal it. Sam ate, not Tom."""
    r = solve("Tom gave 3 apples to Sam and Sam ate 2 apples. How many apples did Sam eat?", reg, tracing=False)
    assert _q(r.store, "sam", "eat"), "an explicit second subject keeps its own verb"
    assert not _q(r.store, "tom", "eat")


def test_comparative_difference_is_not_folded_to_absolute(reg):
    """A gapped comparative clause ('and is 7 years older than Jessica') must not
    mint an absolute year=7 — a difference is not a holding. Safe decline."""
    r = solve("James is a brother and is 7 years older than Jessica. How old is James?", reg, tracing=False)
    assert not r.answer.committed
    assert not [q for q in r.store.by_kind(Quantity) if q.entity == "james" and q.measure == "year"]


def test_general_comparative_still_folds(reg):
    """Tightness on the comparative guard: a NON-dimension comparative ('faster')
    is spurious and must leave the ordinary count fold intact."""
    r = solve("Noah has 5 apples faster than Mia. How many apples does Noah have?", reg, tracing=False)
    assert r.answer.value == 5.0


def test_singular_subject_aggregate_folds_the_one_holder(reg):
    """A singular subject with 'total' sums that one holder's own state+event
    holdings — surfaced when gapping stopped mis-attributing the event away."""
    r = solve("Priya had 54 dollars and got 2 dollars. How much money does she have total?", reg, tracing=False)
    assert r.answer.value == 56.0
