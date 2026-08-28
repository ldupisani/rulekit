"""Manifest dependency resolution for reusable pack boundaries."""

from pathlib import Path

import pytest

from rulekit.data.packs import PackError, load_packs


def _pack(root: Path, name: str, *requires: str) -> Path:
    root.mkdir(parents=True)
    requires_yaml = f"\nrequires: [{', '.join(requires)}]" if requires else ""
    (root / "pack.yaml").write_text(
        f"format: rulekit/pack@1\nname: {name}{requires_yaml}\n"
    )
    return root


def test_transitive_sibling_dependencies_load_before_the_explicit_pack(tmp_path):
    packs = tmp_path / "packs"
    _pack(packs / "base", "base")
    _pack(packs / "middle", "middle", "base")
    leaf = _pack(packs / "leaf", "leaf", "middle")

    loaded = load_packs([leaf])

    assert [pack.name for pack in loaded] == ["base", "middle", "leaf"]


def test_missing_dependency_fails_closed(tmp_path):
    leaf = _pack(tmp_path / "packs" / "leaf", "leaf", "absent")

    with pytest.raises(PackError, match="requires 'absent'"):
        load_packs([leaf])


def test_dependency_cycle_fails_closed(tmp_path):
    packs = tmp_path / "packs"
    first = _pack(packs / "first", "first", "second")
    _pack(packs / "second", "second", "first")

    with pytest.raises(PackError, match="first -> second -> first"):
        load_packs([first])
