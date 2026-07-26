"""Source locations retained from round-trip YAML for authoring tools.

This metadata never enters Registry compilation or inference. Pack loading
already uses ruamel's round-trip nodes, so indexing their line/column data here
keeps the YAML document as the one source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schemas import (
    CategoriesDoc,
    ContractionsDoc,
    LexiconDoc,
    NumbersDoc,
    RulesDoc,
)


@dataclass(frozen=True)
class SourceRef:
    """One editable declaration, using 1-based editor coordinates."""

    path: Path
    line: int
    column: int
    kind: str
    label: str

    def to_json(self) -> dict[str, str | int]:
        return {
            "path": str(self.path),
            "line": self.line,
            "column": self.column,
            "kind": self.kind,
            "label": self.label,
        }


@dataclass
class SourceIndex:
    """Authoring lookup tables merged across a project's loaded packs."""

    rules: dict[str, SourceRef] = field(default_factory=dict)
    asks: dict[str, SourceRef] = field(default_factory=dict)
    rule_tokens: dict[tuple[str, int], SourceRef] = field(default_factory=dict)
    rule_where: dict[tuple[str, int], SourceRef] = field(default_factory=dict)
    lexicon: dict[str, SourceRef] = field(default_factory=dict)
    morphology: dict[tuple[str, str], SourceRef] = field(default_factory=dict)
    contractions: dict[str, SourceRef] = field(default_factory=dict)
    categories: dict[str, SourceRef] = field(default_factory=dict)
    category_members: dict[tuple[str, str], SourceRef] = field(default_factory=dict)
    numeric: dict[tuple[str, str], SourceRef] = field(default_factory=dict)

    def merge(self, other: "SourceIndex") -> None:
        """Merge one pack, preserving the first declaration for duplicate data."""

        for name in (
            "rules",
            "asks",
            "rule_tokens",
            "rule_where",
            "lexicon",
            "morphology",
            "contractions",
            "categories",
            "category_members",
            "numeric",
        ):
            target = getattr(self, name)
            for key, ref in getattr(other, name).items():
                target.setdefault(key, ref)


def _position(node: Any, *, key: Any = None, item: int | None = None) -> tuple[int, int]:
    """Read a ruamel coordinate and convert it to an editor coordinate."""

    try:
        if key is not None:
            line, column = node.lc.key(key)
        elif item is not None:
            line, column = node.lc.item(item)
        else:
            line, column = node.lc.line, node.lc.col
    except (AttributeError, KeyError, TypeError):
        line, column = 0, 0
    return line + 1, column + 1


def _ref(
    path: Path,
    node: Any,
    *,
    kind: str,
    label: str,
    key: Any = None,
    item: int | None = None,
) -> SourceRef:
    line, column = _position(node, key=key, item=item)
    return SourceRef(
        path=path.resolve(),
        line=line,
        column=column,
        kind=kind,
        label=label,
    )


def _index_rules(index: SourceIndex, path: Path, raw: Any, doc: RulesDoc) -> None:
    raw_rules = raw.get("rules", [])
    for rule_no, rule in enumerate(doc.rules):
        if rule_no >= len(raw_rules):
            continue
        raw_rule = raw_rules[rule_no]
        index.rules[rule.id] = _ref(
            path, raw_rules, kind="rule", label=rule.id, item=rule_no
        )
        raw_sentence = raw_rule.get("match", {}).get("sentence")
        if isinstance(raw_sentence, list):
            for token_no in range(len(raw_sentence)):
                index.rule_tokens[(rule.id, token_no)] = _ref(
                    path,
                    raw_sentence,
                    kind="rule-token",
                    label=f"{rule.id} token {token_no + 1}",
                    item=token_no,
                )
        raw_where = raw_rule.get("where", [])
        if isinstance(raw_where, list):
            for where_no in range(len(raw_where)):
                index.rule_where[(rule.id, where_no)] = _ref(
                    path,
                    raw_where,
                    kind="rule-where",
                    label=f"{rule.id} where {where_no + 1}",
                    item=where_no,
                )

    raw_asks = raw.get("asks", [])
    for ask_no, ask in enumerate(doc.asks):
        if ask_no >= len(raw_asks):
            continue
        index.asks[ask.id] = _ref(
            path, raw_asks, kind="ask", label=ask.id, item=ask_no
        )


def _index_lexicon(
    index: SourceIndex, path: Path, raw: Any, doc: LexiconDoc
) -> None:
    raw_entries = raw.get("entries", {})
    for surface in doc.entries:
        if surface not in raw_entries:
            continue
        index.lexicon[surface] = _ref(
            path,
            raw_entries,
            kind="lexicon",
            label=surface,
            key=surface,
        )
        raw_entry = raw_entries[surface]
        for field_name in ("plural", "number", "verb"):
            if field_name in raw_entry:
                index.morphology[(surface, field_name)] = _ref(
                    path,
                    raw_entry,
                    kind="morphology",
                    label=f"{surface}.{field_name}",
                    key=field_name,
                )
        raw_verb = raw_entry.get("verb")
        if isinstance(raw_verb, dict) and "lemma" in raw_verb:
            index.morphology[(surface, "verb.lemma")] = _ref(
                path,
                raw_verb,
                kind="morphology",
                label=f"{surface}.verb.lemma",
                key="lemma",
            )


def _index_categories(
    index: SourceIndex, path: Path, raw: Any, doc: CategoriesDoc
) -> None:
    raw_categories = raw.get("categories", {})
    for category in doc.categories:
        if category in raw_categories:
            index.categories[category] = _ref(
                path,
                raw_categories,
                kind="category",
                label=category,
                key=category,
            )

    raw_members = raw.get("members", {})
    for category, members in doc.members.items():
        raw_values = raw_members.get(category, [])
        for member_no, member in enumerate(members):
            if member_no >= len(raw_values):
                continue
            index.category_members[(category, member)] = _ref(
                path,
                raw_values,
                kind="category-member",
                label=f"{member} ∈ {category}",
                item=member_no,
            )


def _index_numbers(
    index: SourceIndex, path: Path, raw: Any, doc: NumbersDoc
) -> None:
    for family in (
        "numbers",
        "scales",
        "multipliers",
        "fractions",
        "fraction_plurals",
        "operators",
        "currencies",
        "percents",
    ):
        raw_values = raw.get(family, {})
        values = getattr(doc, family)
        for surface in values:
            if surface in raw_values:
                index.numeric[(family, surface)] = _ref(
                    path,
                    raw_values,
                    kind=f"number-{family}",
                    label=surface,
                    key=surface,
                )


def _index_contractions(
    index: SourceIndex, path: Path, raw: Any, doc: ContractionsDoc
) -> None:
    raw_expansions = raw.get("expansions", {})
    for clitic in doc.expansions:
        if clitic in raw_expansions:
            index.contractions[clitic] = _ref(
                path,
                raw_expansions,
                kind="contraction",
                label=clitic,
                key=clitic,
            )


def index_document(path: Path, raw: Any, doc: Any) -> SourceIndex:
    """Build source metadata for the document families G2 links into."""

    index = SourceIndex()
    if isinstance(doc, RulesDoc):
        _index_rules(index, path, raw, doc)
    elif isinstance(doc, LexiconDoc):
        _index_lexicon(index, path, raw, doc)
    elif isinstance(doc, CategoriesDoc):
        _index_categories(index, path, raw, doc)
    elif isinstance(doc, NumbersDoc):
        _index_numbers(index, path, raw, doc)
    elif isinstance(doc, ContractionsDoc):
        _index_contractions(index, path, raw, doc)
    return index


def merge_pack_sources(packs: list[Any]) -> SourceIndex:
    """Build one project index in declared pack order."""

    merged = SourceIndex()
    for pack in packs:
        merged.merge(pack.source_index)
    return merged
