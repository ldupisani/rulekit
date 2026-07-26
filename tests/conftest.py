from functools import lru_cache
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

_load_packs = packs_module.load_packs
_compile_registry = registry_module.compile_registry
_load_project = project_module.load_project
_load_dataset = firewall_module.load_dataset
_registry_cache: dict[tuple[tuple[str, str], ...], Registry] = {}


def _inside_repo(path: Path) -> bool:
    path = path.resolve()
    return path == REPO or REPO in path.parents


@lru_cache(maxsize=None)
def _repo_packs(paths: tuple[str, ...]) -> tuple[LoadedPack, ...]:
    return tuple(_load_packs([Path(path) for path in paths]))


def _cached_load_packs(roots: list[Path]) -> list[LoadedPack]:
    """Share immutable repository packs for one pytest process.

    Temporary packs deliberately bypass the cache: tests which write a pack
    and reload it must continue to exercise the real loader on every call.
    Repository packs are never mutated by the suite, and their compiled
    Registry surface is frozen.
    """
    paths = tuple(str(Path(root).resolve()) for root in roots)
    if _CACHE_ENABLED and all(_inside_repo(Path(path)) for path in paths):
        return list(_repo_packs(paths))
    return _load_packs([Path(path) for path in paths])


def _cached_compile_registry(packs: list[LoadedPack]) -> Registry:
    """Compile each unchanged repository pack combination once per session."""
    pack_list = list(packs)
    if not _CACHE_ENABLED or not all(_inside_repo(pack.root) for pack in pack_list):
        return _compile_registry(pack_list)
    key = tuple(
        (str(pack.root.resolve()), pack.fingerprint)
        for pack in pack_list
    )
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
    if _CACHE_ENABLED and _inside_repo(resolved):
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
packs_module.load_packs = _cached_load_packs
project_module.load_packs = _cached_load_packs
registry_module.compile_registry = _cached_compile_registry
project_module.compile_registry = _cached_compile_registry
project_module.load_project = _cached_load_project
firewall_module.load_dataset = _cached_load_dataset


@pytest.fixture(scope="session")
def registry() -> Registry:
    return _cached_compile_registry(
        _cached_load_packs(
            [REPO / "packs/core-english", REPO / "packs/arithmetic"]
        )
    )
