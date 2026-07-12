"""Parallel bench must be byte-identical to serial.

Every gate in the campaign is a snapshot comparison, so if fanning items out
over processes perturbed ordering or content by one byte, every baseline in
flight would be silently invalidated. The bar is not "it's faster" — it is
"the snapshot is the same".

The items are synthetic (NEVER benchmark items). A real project dir is needed
only because a worker cannot be handed a Registry (unpicklable) and must build
its own from the project — and it must build the SAME one the parent has, which
is exactly what the fingerprint guard enforces.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.harness.bench import _worker_init, run_suite

REPO = Path(__file__).resolve().parent.parent
PROJECT_DIR = REPO / "projects/gsm8k"

ITEMS = [
    {"id": "a", "text": "Tom has 3 apples. How many apples does Tom have?", "expect": 3},
    {"id": "b", "text": "Mary has 12 pens. How many pens does Mary have?", "expect": 12},
    {"id": "c", "text": "Tom has 5 marbles. How many rocks does Tom have?", "expect": "decline"},
    {"id": "d", "text": "Ann has 10 coins. Ann lost 4 coins. How many coins does Ann have?",
     "expect": 6},
    {"id": "e", "text": "Bob has 7 hats. How many hats does Bob have?", "expect": 7},
]


@pytest.fixture(scope="module")
def project_reg():
    """The project's own registry — the one a worker will rebuild for itself."""
    return load_project(PROJECT_DIR).registry


def test_parallel_snapshot_is_identical_to_serial(project_reg):
    serial = run_suite(ITEMS, project_reg, jobs=1).to_snapshot()
    parallel = run_suite(ITEMS, project_reg, jobs=2, project_dir=PROJECT_DIR).to_snapshot()
    assert parallel == serial


def test_parallel_preserves_input_order(project_reg):
    """Pool.map preserves order; scheduling must not reshuffle the items.

    `items` is a dict keyed by id, and it is serialised with sort_keys=True — so
    a reshuffle would not move a byte in the snapshot. Pin the order anyway: the
    id fallback for an item WITHOUT an explicit id is its index, and a reshuffle
    there would silently mislabel every such item.
    """
    parallel = run_suite(ITEMS, project_reg, jobs=2, project_dir=PROJECT_DIR).to_snapshot()
    assert list(parallel["items"]) == ["a", "b", "c", "d", "e"]

    anon = [{"text": i["text"], "expect": i["expect"]} for i in ITEMS]
    serial_anon = run_suite(anon, project_reg, jobs=1).to_snapshot()
    parallel_anon = run_suite(anon, project_reg, jobs=2, project_dir=PROJECT_DIR).to_snapshot()
    assert list(parallel_anon["items"]) == ["0", "1", "2", "3", "4"]
    assert parallel_anon == serial_anon


def test_jobs_without_project_dir_falls_back_to_serial(project_reg):
    """A worker needs the project path to rebuild the Registry. Without one,
    run serially rather than crash."""
    report = run_suite(ITEMS, project_reg, jobs=4, project_dir=None)
    assert report.to_snapshot() == run_suite(ITEMS, project_reg, jobs=1).to_snapshot()


def test_worker_refuses_a_mismatched_pack_state():
    """The safety net: a worker that would bench a different pack state than the
    parent reports in its snapshot must die loudly, not bench a mixture."""
    with pytest.raises(RuntimeError, match="refusing to bench a mixed pack state"):
        _worker_init(str(PROJECT_DIR), "not-the-real-fingerprint")


def test_worker_accepts_the_matching_pack_state(project_reg):
    _worker_init(str(PROJECT_DIR), project_reg.fingerprint)  # must not raise
