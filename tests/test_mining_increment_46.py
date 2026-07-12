"""Mining candidate affine-relations-recut: affine relation offsets
("N more/fewer than K times as many X as Y").

Two new YAML-only pattern rules in packs/arithmetic/rules/core.yaml:
`arithmetic/affine-times-as-many` and `arithmetic/affine-fraction-as-many`.
Both extend the existing times-as-many / fraction-as-many ratio family
(the bare "as many ITEM as STD" frame) with the anchored-relation offset
prefix ("N more/fewer than"), mirroring how `affine-frame-relation` already
prefixes the "the number of" frame -- this is the same offset+ratio
combination for the "as many"/"as much" bare frame instead: subject =
ratio*standard + n*sign(dir). No kernel changes: the Relation fact's
`offset` field and saturate.py's forward/inverse relation resolution
(subject = factor*standard + offset; standard = (subject - offset)/factor)
already existed and are reused unchanged. Offset sign comes from the
existing more_dir/less_dir polarity categories (core-english lexicon:
'more' -> more_dir, 'fewer'/'less' -> less_dir), never a Python word list.

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


def test_affine_times_as_many_more(full_registry):
    # subject = 2*standard + 5: Priyanka has 5 MORE than twice as many
    # stickers as Duncan
    r = solve(
        "Duncan has 9 stickers. Priyanka has 5 more than twice as many "
        "stickers as Duncan. How many stickers does Priyanka have?",
        full_registry,
    )
    assert r.answer.value == 23


def test_affine_times_as_many_fewer(full_registry):
    # subject = 3*standard - 4: Odalys has 4 FEWER than three times as
    # many marbles as Beckett
    r = solve(
        "Beckett has 6 marbles. Odalys has 4 fewer than three times as "
        "many marbles as Beckett. How many marbles does Odalys have?",
        full_registry,
    )
    assert r.answer.value == 14


def test_affine_fraction_as_many_less(full_registry):
    # subject = 0.5*standard - 3: Marisol has 3 less than half as many
    # marbles as Tobias
    r = solve(
        "Tobias has 30 marbles. Marisol has 3 less than half as many "
        "marbles as Tobias. How many marbles does Marisol have?",
        full_registry,
    )
    assert r.answer.value == 12


def test_affine_fraction_as_many_more(full_registry):
    # subject = (1/3)*standard + 2: Fenwick has 2 more than a third as
    # many kites as Rosalind
    r = solve(
        "Rosalind has 21 kites. Fenwick has 2 more than a third as many "
        "kites as Rosalind. How many kites does Fenwick have?",
        full_registry,
    )
    assert r.answer.value == 9


def test_affine_inverse_resolves_standard(full_registry):
    # standard = (subject - offset) / factor, resolved via the inverse
    # direction when the STANDARD's own value is unstated but the SUBJECT's
    # is: Odalys has 4 fewer than three times as many marbles as Beckett,
    # and Odalys's own count is given -- Beckett's must resolve backward.
    r = solve(
        "Odalys has 14 marbles. Odalys has 4 fewer than three times as "
        "many marbles as Beckett. How many marbles does Beckett have?",
        full_registry,
    )
    assert r.answer.value == 6


def test_affine_combined_total(full_registry):
    # a downstream combined-total ask over an affine relation's resolved
    # subject, exercising the general how-much-combined consumer
    r = solve(
        "Duncan has 9 stickers. Priyanka has 5 more than twice as many "
        "stickers as Duncan. How many stickers do they have in total?",
        full_registry,
    )
    assert r.answer.value == 32


def test_affine_as_many_without_resolvable_standard_declines(full_registry):
    # decline-safety: the standard entity never states its own quantity
    # anywhere in the text -- nothing to resolve the ratio against, so the
    # relation must decline rather than guess.
    r = solve(
        "Priyanka has 5 more than twice as many stickers as Duncan. "
        "How many stickers does Priyanka have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
