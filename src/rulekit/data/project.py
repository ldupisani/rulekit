"""Project loading: a project = packs + datasets/suite + config."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from .packs import LoadedPack, load_packs
from .registry import Registry, compile_registry
from .schemas import ProjectDoc

_yaml = YAML(typ="rt")


@dataclass
class Project:
    root: Path
    doc: ProjectDoc
    packs: list[LoadedPack]
    registry: Registry

    def suite_items(self) -> list[dict]:
        if not self.doc.suite:
            return []
        path = self.root / self.doc.suite
        with path.open() as fh:
            data = _yaml.load(fh)
        items = data["items"]
        seen: set[str] = set()
        for i, item in enumerate(items):
            item.setdefault("id", f"item-{i:03d}")
            if item["id"] in seen:
                raise ValueError(f"duplicate suite item id {item['id']!r}")
            seen.add(item["id"])
        return list(items)

    @property
    def snapshots_dir(self) -> Path:
        return self.root / "snapshots"

    def dataset_items(self, slice_name: str) -> list[dict]:
        """Bench items for a dataset slice (dev|dev-train|dev-holdout|test).
        The md5 split and slice semantics live in harness.firewall."""
        from ..harness.firewall import load_dataset, slice_items

        if not self.doc.datasets:
            raise ValueError("project has no datasets")
        _name, splits = next(iter(sorted(self.doc.datasets.items())))
        train = load_dataset(
            self.root / splits["train"].parquet,
            splits["train"].question, splits["train"].answer,
        )
        test = load_dataset(
            self.root / splits["test"].parquet,
            splits["test"].question, splits["test"].answer,
        )
        return [
            {"id": i.id, "text": i.text, "expect": i.expect}
            for i in slice_items(train, test, slice_name)
        ]


def _resolve_pack_path(name: str, project_root: Path) -> Path:
    if name.startswith("./") or name.startswith("../"):
        return (project_root / name).resolve()
    # search upward from the project for a repo-level packs/ directory
    for base in (project_root, *project_root.parents):
        candidate = base / "packs" / name
        if (candidate / "pack.yaml").exists():
            return candidate
    raise FileNotFoundError(f"pack {name!r} not found from {project_root}")


def load_project(root: Path | str) -> Project:
    root = Path(root).resolve()
    with (root / "project.yaml").open() as fh:
        doc = ProjectDoc.model_validate(_yaml.load(fh))
    pack_paths = [_resolve_pack_path(name, root) for name in doc.packs]
    packs = load_packs(pack_paths)
    return Project(root=root, doc=doc, packs=packs, registry=compile_registry(packs))
