"""Superordinate subtype-total through the COMBINED / aggregate ask.

SYNTHETIC ONLY (constitution rule 3). Invented sentences; no benchmark string.

"picked up 10 bottles and 8 cans... how many pieces of litter altogether?" -> 18.
No entity holds the asked measure ('piece', or 'litter' itself) directly, but the
measure or its partitive substance is a pack-declared SUPERORDINATE (litter) whose
subtypes (bottle, can) ARE held. `_superordinate_total` already summed subtypes for
the SINGLE-entity consumer ("how many children does he have"); this pins the new
path that reaches it through the aggregate marker's `combined` consumer, including
the generic-counter partitive ('pieces of').
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


PREMISE = "The crew picked up 10 bottles and 8 cans. "


def test_partitive_superordinate_over_subtypes(reg):
    """The core case: 'how many PIECES OF litter altogether' — the partitive
    substance 'litter' is the superordinate; sum its held subtypes."""
    r = solve(PREMISE + "How many pieces of litter did they pick up altogether?", reg, tracing=False)
    assert r.answer.value == 18.0


def test_bare_superordinate_over_subtypes(reg):
    """Same, asked with the bare superordinate ('how many litter altogether')."""
    r = solve(PREMISE + "How many litter did they pick up altogether?", reg, tracing=False)
    assert r.answer.value == 18.0


def test_single_subtype_is_not_a_superordinate_total(reg):
    """TIGHTNESS (the _superordinate_total guard): only ONE subtype held is not
    'every subtype' — a lone 'bottle' must not answer a 'litter' total, so this
    stays a decline rather than read a partial as the whole."""
    r = solve("The crew picked up 10 bottles. How many litter did they pick up altogether?", reg, tracing=False)
    assert not r.answer.committed
