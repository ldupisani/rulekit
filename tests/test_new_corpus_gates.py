"""Firewall soundness for the MAWPS and SciBench cross-corpus gates.

SYNTHETIC ONLY (constitution rule 3). No benchmark string appears here — the split
logic is exercised on invented strings, and the data-backed disjointness assert
skips when the (gitignored) parquets are unbuilt. Siblings of test_asdiv_gate.py /
test_svamp_gate.py; see those for why a reproducible split is load-bearing.
"""

import importlib.util
from pathlib import Path

import pytest

CORPORA = ["mawps", "scibench", "difg"]


def _load_builder(name):
    path = Path(f"projects/{name}/build_corpus.py")
    spec = importlib.util.spec_from_file_location(f"{name}_build_corpus", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("name", CORPORA)
def test_split_is_deterministic(name):
    b = _load_builder(name)
    for s in ("a wolf ate 3 sheep", "there are 12 moons", "x bought y for z"):
        assert b.bucket(s) == b.bucket(s)


@pytest.mark.parametrize("name", CORPORA)
def test_split_partitions_both_ways(name):
    b = _load_builder(name)
    seen = {b.bucket(f"synthetic problem number {i}") for i in range(200)}
    assert seen == {"dev", "test"}


@pytest.mark.parametrize("name", CORPORA)
def test_dev_and_test_do_not_leak(name):
    if not (Path(f"projects/{name}/data/{name}_dev.parquet").exists()
            and Path(f"projects/{name}/data/{name}_test.parquet").exists()):
        pytest.skip(f"{name} corpus not built")
    from rulekit.data.project import load_project

    proj = load_project(Path(f"projects/{name}"))
    dev_ids = {i["id"] for i in proj.dataset_items("dev")}
    test_ids = {i["id"] for i in proj.dataset_items("test")}
    assert dev_ids and test_ids, "a split side is empty"
    assert dev_ids.isdisjoint(test_ids), "DEV/TEST leak — held-out is not held out"
