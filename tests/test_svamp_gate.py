"""The SVAMP cross-corpus gate: firewall soundness, no data leak.

SYNTHETIC ONLY (constitution rule 3). No SVAMP problem string appears here — the
split logic is exercised on invented strings, and the data-backed asserts skip
when the (gitignored) parquets have not been built. Sibling of test_asdiv_gate.py;
see that file for why a cross-corpus gate's reproducible split is load-bearing.
"""

import importlib.util
from pathlib import Path

import pytest

_BUILDER = Path("projects/svamp/build_corpus.py")


def _load_builder():
    spec = importlib.util.spec_from_file_location("svamp_build_corpus", _BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_split_is_deterministic():
    b = _load_builder()
    for s in ("a wolf ate 3 sheep", "there are 12 moons", "x bought y for z"):
        assert b.bucket(s) == b.bucket(s)


def test_split_partitions_both_ways():
    b = _load_builder()
    seen = {b.bucket(f"synthetic problem number {i}") for i in range(200)}
    assert seen == {"dev", "test"}


def test_gold_extraction_is_leading_number():
    b = _load_builder()
    assert b.gold_of("145") == 145.0
    assert b.gold_of("1,250") == 1250.0
    assert b.gold_of("no number here") is None


@pytest.mark.skipif(
    not (Path("projects/svamp/data/svamp_dev.parquet").exists()
         and Path("projects/svamp/data/svamp_test.parquet").exists()),
    reason="SVAMP corpus not built (uv run --with datasets python projects/svamp/build_corpus.py)",
)
def test_dev_and_test_do_not_leak():
    from rulekit.data.project import load_project

    proj = load_project(Path("projects/svamp"))
    dev_ids = {i["id"] for i in proj.dataset_items("dev")}
    test_ids = {i["id"] for i in proj.dataset_items("test")}
    assert dev_ids and test_ids, "a split side is empty"
    assert dev_ids.isdisjoint(test_ids), "DEV/TEST leak — held-out is not held out"
