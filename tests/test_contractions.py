"""Contractions are PACK DATA, not a dict in the kernel.

`_CONTRACTIONS` lived in `kernel/tokenize.py`, which made it the one place the
kernel enumerated WORDS — constitution rule 1 says every word-specific fact
lives in a pack, and "'re" -> "are" is a word-specific fact. The morphology
helpers beside it (`_naive_singular`, `_ORDINAL`) derive a form from a SHAPE
and are legitimately structural; this derives one WORD from another, and only
a table can say which.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_pack, load_packs
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.tokenize import tokenize

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reg():
    return load_project(ROOT / "projects" / "gsm8k").registry


@pytest.mark.parametrize(
    "text, expect",
    [
        ("Tom doesn't have apples", ["Tom", "does", "not", "have", "apples"]),
        ("they're here", ["they", "are", "here"]),
        ("she'll go", ["she", "will", "go"]),
        ("we've seen", ["we", "have", "seen"]),
        # the possessive/copular "'s" is kept as its OWN token rather than
        # expanded: the two readings share a surface and the choice belongs to
        # a later layer, not to tokenization
        ("Tom's apple", ["Tom", "'s", "apple"]),
    ],
)
def test_the_pack_table_splits_contractions(reg, text, expect):
    assert [u.surface for u in tokenize(text, contractions=reg.contractions).units] == expect


def test_the_engine_supplies_the_table(reg):
    # the end-to-end assertion: a rule matching `{lit: not}` must still see the
    # 'not' that a contraction produced
    units = [u.surface for u in solve("Tom doesn't have 5 apples.", reg).premises[0].units]
    assert "not" in units


def test_omitting_the_table_means_no_expansion(reg):
    # deliberate and visible in the call, rather than a silent difference: a
    # caller wanting raw tokenization says so by passing nothing
    assert [u.surface for u in tokenize("Tom doesn't have apples").units] == (
        ["Tom", "doesn't", "have", "apples"]
    )


def test_the_table_is_sorted_LONGEST_CLITIC_FIRST(reg):
    # matching is by suffix, so a shorter clitic could shadow a longer one
    # ("n't" vs a hypothetical "'t"). Sorting in compile_registry means a YAML
    # reordering can never change a reading.
    lengths = [len(clitic) for clitic, _ in reg.contractions]
    assert lengths == sorted(lengths, reverse=True)


def test_a_conflicting_redeclaration_fails_at_load(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    (root / "pack.yaml").write_text("format: rulekit/pack@1\nname: p\n")
    (root / "a.yaml").write_text("format: rulekit/contractions@1\nexpansions: {\"n't\": not}\n")
    (root / "b.yaml").write_text("format: rulekit/contractions@1\nexpansions: {\"n't\": never}\n")
    with pytest.raises(CompileError) as exc:
        compile_registry([load_pack(root)])
    assert "declared twice" in str(exc.value)


def test_an_uppercase_clitic_is_rejected(tmp_path):
    # matching runs on a lower-cased surface, so an upper-case key would sit in
    # the table matching nothing — the dead-entry failure mode this repo fails
    # loudly on rather than tolerating
    root = tmp_path / "p"
    root.mkdir()
    (root / "pack.yaml").write_text("format: rulekit/pack@1\nname: p\n")
    (root / "c.yaml").write_text("format: rulekit/contractions@1\nexpansions: {\"N'T\": not}\n")
    with pytest.raises(Exception) as exc:
        load_pack(root)
    assert "lower-case" in str(exc.value)


def test_the_kernel_no_longer_enumerates_the_words(reg):
    # constitution rule 1. If the table ever moves back into Python this is the
    # test that should start failing.
    import rulekit.kernel.tokenize as tok

    assert not hasattr(tok, "_CONTRACTIONS")
    assert reg.contractions, "the pack must supply them instead"
