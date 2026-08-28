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

from .sources import SourceIndex, index_document
from .schemas import (
    AffineConversionsDoc,
    CalendarDoc,
    ContractionsDoc,
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
    ReferenceDoc,
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
    contractions: list[ContractionsDoc] = field(default_factory=list)
    affine: list[AffineConversionsDoc] = field(default_factory=list)
    quarantine: list[QuarantineDoc] = field(default_factory=list)
    reference: list[ReferenceDoc] = field(default_factory=list)
    source_index: SourceIndex = field(default_factory=SourceIndex)
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
        pack.source_index.merge(index_document(path, raw, doc))

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
        elif isinstance(doc, ContractionsDoc):
            pack.contractions.append(doc)
        elif isinstance(doc, AffineConversionsDoc):
            pack.affine.append(doc)
        elif isinstance(doc, QuarantineDoc):
            pack.quarantine.append(doc)
        elif isinstance(doc, ReferenceDoc):
            pack.reference.append(doc)

    pack.fingerprint = hasher.hexdigest()
    return pack


def load_packs(roots: list[Path]) -> list[LoadedPack]:
    """Load explicit packs and their sibling-declared dependencies.

    A manifest names dependencies by pack name. Repository packs live as
    sibling directories, so callers should not have to reproduce the complete
    transitive order in every project and test fixture. Explicit roots still
    win when a dependency is supplied from another location (for example a
    project-local pack); unresolved names are looked up beside the requiring
    pack. Cycles, missing packs, and two roots claiming one name fail closed.
    """

    explicit = [load_pack(root) for root in roots]
    available: dict[str, LoadedPack] = {}
    for pack in explicit:
        prior = available.get(pack.name)
        if prior is not None and prior.root != pack.root:
            raise PackError(
                f"pack name {pack.name!r} resolves to both {prior.root} "
                f"and {pack.root}"
            )
        available[pack.name] = pack

    ordered: list[LoadedPack] = []
    loaded: dict[str, LoadedPack] = {}
    visiting: list[str] = []

    def visit(pack: LoadedPack) -> None:
        prior = loaded.get(pack.name)
        if prior is not None:
            if prior.root != pack.root:
                raise PackError(
                    f"pack name {pack.name!r} resolves to both {prior.root} "
                    f"and {pack.root}"
                )
            return
        if pack.name in visiting:
            cycle = " -> ".join((*visiting, pack.name))
            raise PackError(f"pack dependency cycle: {cycle}")

        visiting.append(pack.name)
        for required_name in pack.manifest.requires:
            required = available.get(required_name)
            if required is None:
                required_root = pack.root.parent / required_name
                if not (required_root / "pack.yaml").exists():
                    raise PackError(
                        f"pack {pack.name!r} requires {required_name!r}, "
                        f"but {required_root} is not a pack"
                    )
                required = load_pack(required_root)
                if required.name != required_name:
                    raise PackError(
                        f"pack {pack.name!r} requires {required_name!r}, but "
                        f"{required_root} declares name {required.name!r}"
                    )
                available[required_name] = required
            visit(required)
        visiting.pop()
        loaded[pack.name] = pack
        ordered.append(pack)

    for pack in explicit:
        visit(pack)
    return ordered
