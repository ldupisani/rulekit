"""Mining increment 75: collective-subject totality asks (prenominal
totality marker, quantified/cardinal collective subject).

Three new ask ids, all routing to the EXISTING `combined` consumer
(answer.py untouched, no new fact kind) — siblings of ask/how-many-plural-
combined (increment 67) left byte-identical:

- ask/how-many-plural-combined-prenominal-marker: "how many TOTAL-MARKER
  ITEM do/does/did (THE) PLURAL-COMMON-NOUN have?" — the aggregate marker
  sits PRENOMINALLY, right after "how many", instead of trailing the verb.
  `pre, cat: aggregate` is required.

- ask/how-many-plural-combined-quantified-subject: "how many ITEM do/does/
  did ALL/BOTH PLURAL-COMMON-NOUN have TOTAL-MARKER?" — the subject's
  leading word widens from a bare `the` to a `quantifier`-sense word
  ('all'/'both'), with the trailing aggregate marker still required (no
  cardinal to license the read on its own).

- ask/how-many-plural-combined-cardinal-subject: "how many ITEM do/does/
  did (DEMONSTRATIVE|ALL/BOTH) CARDINAL PLURAL-COMMON-NOUN have?" — the
  subject NP itself carries an explicit CARDINAL ("these three boys",
  "all three friends"), which alone licenses the totality read; no
  aggregate marker required anywhere. Gated on `who, type: counted` (a
  merged numeric value on the noun) so a bare "the boys"/"these boys"
  (no cardinal) still fails this ask's own match and still declines.

Synthetic only."""

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


def test_prenominal_marker_bare_plural_subject(full_registry):
    r = solve(
        "Nadia has 12 pebbles and Farrukh has 7 pebbles. "
        "How many total pebbles do the boys have?",
        full_registry,
    )
    assert r.answer.value == 19


def test_quantified_subject_all_with_trailing_marker(full_registry):
    r = solve(
        "Nadia scored 12 points. Farrukh scored 7 points. "
        "How many points did all boys score altogether?",
        full_registry,
    )
    assert r.answer.value == 19


def test_quantified_subject_both_with_trailing_marker(full_registry):
    r = solve(
        "Nadia has 12 pebbles and Farrukh has 7 pebbles. "
        "How many pebbles do both boys have combined?",
        full_registry,
    )
    assert r.answer.value == 19


def test_cardinal_subject_demonstrative_no_marker(full_registry):
    r = solve(
        "Nadia has 12 pebbles, Farrukh has 7 pebbles, and Oleander has 5 "
        "pebbles. How many pebbles do these three boys have?",
        full_registry,
    )
    assert r.answer.value == 24


def test_cardinal_subject_quantifier_no_marker(full_registry):
    r = solve(
        "Nadia scored 12 points. Farrukh scored 7 points. Oleander scored "
        "5 points. How many points did all three boys score?",
        full_registry,
    )
    assert r.answer.value == 24


def test_bare_plural_subject_no_marker_no_cardinal_declines(full_registry):
    # no aggregate marker anywhere and no cardinal on the subject: none of
    # the three new asks (nor the pre-existing plural-combined family) may
    # claim this question -- it must stay declined exactly as before.
    r = solve(
        "Nadia has 12 pebbles and Farrukh has 7 pebbles. "
        "How many pebbles do the boys have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_quantified_subject_without_marker_or_cardinal_declines(full_registry):
    # a bare quantifier ('both') with neither a trailing aggregate marker
    # nor an explicit cardinal on the subject must not license the
    # totality read -- this is the exact hazard the mining brief flagged.
    r = solve(
        "Nadia has 12 pebbles and Farrukh has 7 pebbles. "
        "How many pebbles do both boys have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_prenominal_marker_declines_with_one_holder(full_registry):
    # a collective subject still asserts plurality -- one holder in play
    # means decline, not a one-entity "sum", even with the marker present.
    r = solve(
        "Nadia has 12 pebbles. How many total pebbles does the boy have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
