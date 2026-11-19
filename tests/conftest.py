from functools import lru_cache
import json
import os
from pathlib import Path

import pytest

from rulekit.data import packs as packs_module
from rulekit.data import project as project_module
from rulekit.data import registry as registry_module
from rulekit.data.packs import LoadedPack
from rulekit.data.project import Project
from rulekit.data.registry import Registry
from rulekit.harness import firewall as firewall_module
from rulekit.harness.firewall import BenchItem

REPO = Path(__file__).resolve().parent.parent
_CACHE_ENABLED = os.environ.get("RULEKIT_TEST_CACHE", "1") != "0"

_load_pack = packs_module.load_pack
_compile_registry = registry_module.compile_registry
_load_project = project_module.load_project
_load_dataset = firewall_module.load_dataset
_PACK_ROOTS = {manifest.parent for manifest in (REPO / "packs").glob("*/pack.yaml")}
_PROJECT_ROOTS = {manifest.parent for manifest in (REPO / "projects").glob("*/project.yaml")}
_shared_packs: dict[Path, LoadedPack] = {}
_registry_cache: dict[tuple[Path, ...], Registry] = {}


def _inside_repo(path: Path) -> bool:
    path = path.resolve()
    return path == REPO or REPO in path.parents


def _cached_load_pack(root: Path) -> LoadedPack:
    """Parse each shared vocabulary/rule pack once, including transitive dependencies."""
    root = root.resolve()
    if not _CACHE_ENABLED or root not in _PACK_ROOTS:
        return _load_pack(root)
    if root not in _shared_packs:
        _shared_packs[root] = _load_pack(root)
    return _shared_packs[root]


def _cached_compile_registry(packs: list[LoadedPack]) -> Registry:
    """Only the original shared packs can reuse a compiled registry.

    Tests may replace pack contents in memory while retaining the on-disk fingerprint.
    """
    pack_list = list(packs)
    if not pack_list or any(
        _shared_packs.get(pack.root) is not pack for pack in pack_list
    ):
        return _compile_registry(pack_list)
    key = tuple(pack.root for pack in pack_list)
    registry = _registry_cache.get(key)
    if registry is None:
        registry = _compile_registry(pack_list)
        _registry_cache[key] = registry
    return registry


@lru_cache(maxsize=None)
def _repo_project(root: str) -> Project:
    return _load_project(Path(root))


def _cached_load_project(root: Path | str) -> Project:
    """Share repository projects; keep writable temporary projects fresh."""
    resolved = Path(root).resolve()
    if _CACHE_ENABLED and resolved in _PROJECT_ROOTS:
        return _repo_project(str(resolved))
    return _load_project(resolved)


@lru_cache(maxsize=None)
def _repo_dataset(
    path: str,
    question_col: str,
    answer_col: str,
    gold: str | None,
    group_col: str | None,
    mtime_ns: int,
    size: int,
) -> tuple[BenchItem, ...]:
    # mtime and size are deliberately part of the key. They make the test
    # cache observe a repository dataset replaced during a long pytest process
    # without paying to hash a potentially large parquet on every access.
    del mtime_ns, size
    return tuple(
        _load_dataset(
            Path(path),
            question_col,
            answer_col,
            gold=gold,
            group_col=group_col,
        )
    )


def _cached_load_dataset(
    parquet_path: Path,
    question_col: str,
    answer_col: str,
    gold: str | None = None,
    group_col: str | None = None,
) -> list[BenchItem]:
    """Read each unchanged repository parquet once per pytest process."""
    resolved = Path(parquet_path).resolve()
    if not _CACHE_ENABLED or not _inside_repo(resolved):
        return _load_dataset(
            resolved,
            question_col,
            answer_col,
            gold=gold,
            group_col=group_col,
        )
    stat = resolved.stat()
    # Return a fresh container so a test cannot mutate the cached list. Its
    # BenchItem members are frozen dataclasses.
    return list(
        _repo_dataset(
            str(resolved),
            question_col,
            answer_col,
            gold,
            group_col,
            stat.st_mtime_ns,
            stat.st_size,
        )
    )


# Test modules import these functions during collection, after conftest itself
# has loaded. Patch only the test process; production imports and benchmark
# worker processes remain unchanged. project.py imported its collaborators by
# name, so update those bindings as well as their defining modules.
packs_module.load_pack = _cached_load_pack
registry_module.compile_registry = _cached_compile_registry
project_module.compile_registry = _cached_compile_registry
project_module.load_project = _cached_load_project
firewall_module.load_dataset = _cached_load_dataset


@pytest.fixture(scope="session")
def registry() -> Registry:
    return _cached_compile_registry(
        packs_module.load_packs(
            [REPO / "packs/core-english", REPO / "packs/arithmetic"]
        )
    )


@pytest.fixture(scope="session")
def full_registry() -> Registry:
    """Arithmetic with the extended difg vocabulary."""
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return _cached_compile_registry(
        packs_module.load_packs(
            [REPO / "packs/core-english", REPO / "packs/arithmetic", mined]
        )
    )


@pytest.fixture(scope="session")
def curated_availability():
    from rulekit.generation import list_rule_availability

    project = _cached_load_project(REPO / "projects/curated")
    return {rule.id: rule for rule in list_rule_availability(project)}


@pytest.fixture(scope="session")
def curated_fillers():
    from rulekit.generation.exploration import exploration_status

    project = _cached_load_project(REPO / "projects/curated")
    rows = exploration_status(project)["fillers"]
    by_identity = {row["identity"]: row for row in rows}
    assert len(by_identity) == len(rows)
    return by_identity


@pytest.fixture(scope="session")
def curated_review_rows():
    """Index the checked-in raw ledger, including superseded and resolved reviews."""
    from rulekit.generation.reviews import review_path

    path = review_path(_cached_load_project(REPO / "projects/curated"))
    with path.open(encoding="utf-8") as stream:
        rows = (json.loads(line) for line in stream if line.strip())
        return {row["id"]: row for row in rows}
