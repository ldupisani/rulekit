"""The ASDiv cross-corpus gate: firewall soundness, no data leak.

SYNTHETIC ONLY (constitution rule 3). No ASDiv problem string appears here — the
split logic is exercised on invented strings, and the data-backed asserts skip
when the (gitignored) parquets have not been built.

WHY IT EXISTS. The value of a cross-corpus gate is precision measured on text the
rules never saw. That value is destroyed by two silent failures: (1) a
non-reproducible split — a fresh checkout draws a different TEST set and spends a
look unknowingly; (2) a DEV/TEST leak — the same item in both, so a "held-out"
number is not held out. Both are pinned here so neither can regress unnoticed.
"""

import importlib.util
from pathlib import Path

import pytest

_BUILDER = Path("projects/asdiv/build_corpus.py")


def _load_builder():
    spec = importlib.util.spec_from_file_location("asdiv_build_corpus", _BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_split_is_deterministic():
    """The firewall cut must be a pure function of the text — re-deriving the
    bucket for the same string always agrees. A split that wanders is a spent
    TEST look every checkout."""
    b = _load_builder()
    for s in ("a wolf ate 3 sheep", "there are 12 moons", "x bought y for z"):
        assert b.bucket(s) == b.bucket(s)


def test_split_partitions_both_ways():
    """A salt that sent everything to one side would make TEST empty (or DEV
    empty) and the gate meaningless. On a synthetic spread both sides are hit."""
    b = _load_builder()
    seen = {b.bucket(f"synthetic problem number {i}") for i in range(200)}
    assert seen == {"dev", "test"}


def test_gold_extraction_is_leading_number():
    """The gold is ASDiv's leading answer number; unit/set tails drop to a float.
    Pinned so a builder edit can't silently start emitting units into a #### gold
    (which parse_gold would then misread)."""
    b = _load_builder()
    assert b.gold_of("9 (apples)") == 9.0
    assert b.gold_of("1,250 (dollars)") == 1250.0
    assert b.gold_of("no number here") is None


@pytest.mark.skipif(
    not (Path("projects/asdiv/data/asdiv_dev.parquet").exists()
         and Path("projects/asdiv/data/asdiv_test.parquet").exists()),
    reason="ASDiv corpus not built (uv run --with datasets python projects/asdiv/build_corpus.py)",
)
def test_dev_and_test_do_not_leak():
    """The firewall's one non-negotiable: no item is in both DEV and TEST."""
    from rulekit.data.project import load_project

    proj = load_project(Path("projects/asdiv"))
    dev_ids = {i["id"] for i in proj.dataset_items("dev")}
    test_ids = {i["id"] for i in proj.dataset_items("test")}
    assert dev_ids and test_ids, "a split side is empty"
    assert dev_ids.isdisjoint(test_ids), "DEV/TEST leak — held-out is not held out"
