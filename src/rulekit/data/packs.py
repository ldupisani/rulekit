"""Pack discovery and loading.

A pack is a directory containing pack.yaml plus any number of rulekit YAML
documents (any nesting). Every document self-identifies via its `format:`
key; the loader validates each against its pydantic model and returns a
LoadedPack. Duplicate lexicon keys *within one pack* are a load error —
the difg duplicate-key-shadowing bug class is unrepresentable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from .schemas import (
    AffineConversionsDoc,
    CalendarDoc,
    ElementsDoc,
    KIND_MODELS,
    CategoriesDoc,
    ConversionsDoc,
    FormulasDoc,
    GeometryDoc,
    GuardsDoc,
    LexiconDoc,
    NumbersDoc,
    ObligationsDoc,
    PackDoc,
    QuarantineDoc,
    RequirementsDoc,
    RulesDoc,
    SynthDoc,
)

_yaml = YAML(typ="rt")  # round-trip: the designer writes comments back


class PackError(Exception):
    """A pack failed to load or validate. Message names file and cause."""


@dataclass
class LoadedPack:
    name: str
    root: Path
    manifest: PackDoc
    lexicon: dict[str, object] = field(default_factory=dict)  # word -> LexiconEntry
    lexicon_sources: dict[str, Path] = field(default_factory=dict)
    categories: list[CategoriesDoc] = field(default_factory=list)
    numbers: list[NumbersDoc] = field(default_factory=list)
    obligations: list[ObligationsDoc] = field(default_factory=list)
    rules: list[RulesDoc] = field(default_factory=list)
    synth: list[SynthDoc] = field(default_factory=list)
    requirements: list[RequirementsDoc] = field(default_factory=list)
    guards: list[GuardsDoc] = field(default_factory=list)
    conversions: list[ConversionsDoc] = field(default_factory=list)
    geometry: list[GeometryDoc] = field(default_factory=list)
    formulas: list[FormulasDoc] = field(default_factory=list)
    calendar: list[CalendarDoc] = field(default_factory=list)
    elements: list[ElementsDoc] = field(default_factory=list)
    affine: list[AffineConversionsDoc] = field(default_factory=list)
    quarantine: list[QuarantineDoc] = field(default_factory=list)
    fingerprint: str = ""


def _read_yaml(path: Path) -> dict:
    with path.open() as fh:
        data = _yaml.load(fh)
    if not isinstance(data, dict):
        raise PackError(f"{path}: not a mapping document")
    return data


def load_pack(root: Path) -> LoadedPack:
    root = root.resolve()
    manifest_path = root / "pack.yaml"
    if not manifest_path.exists():
        raise PackError(f"{root}: no pack.yaml")
    manifest = PackDoc.model_validate(_read_yaml(manifest_path))
    pack = LoadedPack(name=manifest.name, root=root, manifest=manifest)

    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*.yaml")):
        if path == manifest_path:
            hasher.update(path.read_bytes())
            continue
        raw = _read_yaml(path)
        fmt = raw.get("format")
        if fmt not in KIND_MODELS:
            raise PackError(f"{path}: unknown or missing format {fmt!r}")
        try:
            doc = KIND_MODELS[fmt].model_validate(raw)
        except Exception as exc:  # pydantic ValidationError carries the path
            raise PackError(f"{path}: {exc}") from exc
        hasher.update(path.read_bytes())

        if isinstance(doc, LexiconDoc):
            for word, entry in doc.entries.items():
                if word in pack.lexicon:
                    raise PackError(
                        f"{path}: duplicate lexicon entry {word!r} "
                        f"(also in {pack.lexicon_sources[word]})"
                    )
                pack.lexicon[word] = entry
                pack.lexicon_sources[word] = path
        elif isinstance(doc, CategoriesDoc):
            pack.categories.append(doc)
        elif isinstance(doc, NumbersDoc):
            pack.numbers.append(doc)
        elif isinstance(doc, ObligationsDoc):
            pack.obligations.append(doc)
        elif isinstance(doc, RulesDoc):
            pack.rules.append(doc)
        elif isinstance(doc, SynthDoc):
            pack.synth.append(doc)
        elif isinstance(doc, RequirementsDoc):
            pack.requirements.append(doc)
        elif isinstance(doc, GuardsDoc):
            pack.guards.append(doc)
        elif isinstance(doc, ConversionsDoc):
            pack.conversions.append(doc)
        elif isinstance(doc, GeometryDoc):
            pack.geometry.append(doc)
        elif isinstance(doc, FormulasDoc):
            pack.formulas.append(doc)
        elif isinstance(doc, CalendarDoc):
            pack.calendar.append(doc)
        elif isinstance(doc, ElementsDoc):
            pack.elements.append(doc)
        elif isinstance(doc, AffineConversionsDoc):
            pack.affine.append(doc)
        elif isinstance(doc, QuarantineDoc):
            pack.quarantine.append(doc)

    pack.fingerprint = hasher.hexdigest()
    return pack


def load_packs(roots: list[Path]) -> list[LoadedPack]:
    """Load several packs, checking requires-ordering."""
    packs = [load_pack(r) for r in roots]
    seen: set[str] = set()
    for p in packs:
        missing = [req for req in p.manifest.requires if req not in seen]
        if missing:
            raise PackError(f"pack {p.name!r} requires {missing} loaded before it")
        seen.add(p.name)
    return packs
