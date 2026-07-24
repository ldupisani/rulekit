"""Sentence→semantic-graph evaluation.

Projection corpora measure the intermediate reading, not an answer.  They are
kept out of ``bench._judge`` on purpose: treating a logical form as text gold
would collapse a structured precision problem into string equality.

The normalized graph is intentionally small.  COGS variable spelling and
conjunct order disappear, while entity/event identity, semantic roles,
attachment, complement structure, definiteness, and lexical predicates remain.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..data.registry import Registry
from ..data.schemas import ProjectionSplitDef
from ..kernel.engine import solve
from ..kernel.model import SemanticGraphEdge, SemanticGraphNode, VerbalRelation

PROJECTION_SCHEMA = "rulekit/projection-graph@1"


@dataclass(frozen=True, order=True)
class ProjectionNode:
    """One discourse referent or eventuality.

    Evidence metadata does not participate in equality: it explains a runtime
    projection but cannot make a semantically different graph compare equal.
    """

    ref: str
    kind: str  # entity | event
    evidence_source: str = field(default="", compare=False)
    sentence: int | None = field(default=None, compare=False)
    span: tuple[int, int] | None = field(default=None, compare=False)

    def semantic_key(self) -> tuple[str, str]:
        return self.ref, self.kind

    def to_json(self) -> dict:
        out = {"ref": self.ref, "kind": self.kind}
        if self.evidence_source:
            out["evidence"] = {
                "source": self.evidence_source,
                "sentence": self.sentence,
                "span": list(self.span) if self.span is not None else None,
            }
        return out


@dataclass(frozen=True, order=True)
class ProjectionEdge:
    """One typed relation in the normalized graph."""

    kind: str  # type | event | definite | role | modifier | complement
    source: str
    target: str = ""
    label: str = ""
    evidence_source: str = field(default="", compare=False)
    sentence: int | None = field(default=None, compare=False)
    span: tuple[int, int] | None = field(default=None, compare=False)

    def semantic_key(self) -> tuple[str, str, str, str]:
        return self.kind, self.source, self.target, self.label

    def to_json(self) -> dict:
        out = {
            "kind": self.kind,
            "source": self.source,
            "target": self.target,
            "label": self.label,
        }
        if self.evidence_source:
            out["evidence"] = {
                "source": self.evidence_source,
                "sentence": self.sentence,
                "span": list(self.span) if self.span is not None else None,
            }
        return out


@dataclass(frozen=True)
class ProjectionGraph:
    nodes: tuple[ProjectionNode, ...] = ()
    edges: tuple[ProjectionEdge, ...] = ()

    @property
    def empty(self) -> bool:
        return not self.nodes and not self.edges

    def node_keys(self) -> frozenset[tuple[str, str]]:
        return frozenset(node.semantic_key() for node in self.nodes)

    def edge_keys(self) -> frozenset[tuple[str, str, str, str]]:
        return frozenset(edge.semantic_key() for edge in self.edges)

    def to_json(self) -> dict:
        return {
            "format": PROJECTION_SCHEMA,
            "nodes": [node.to_json() for node in self.nodes],
            "edges": [edge.to_json() for edge in self.edges],
        }


class _GraphBuilder:
    def __init__(self) -> None:
        self.nodes: dict[tuple[str, str], ProjectionNode] = {}
        self.edges: dict[tuple[str, str, str, str], ProjectionEdge] = {}

    def node(
        self,
        ref: str,
        kind: str,
        *,
        evidence_source: str = "",
        sentence: int | None = None,
        span: tuple[int, int] | None = None,
    ) -> None:
        node = ProjectionNode(ref, kind, evidence_source, sentence, span)
        self.nodes.setdefault(node.semantic_key(), node)

    def edge(
        self,
        kind: str,
        source: str,
        target: str = "",
        label: str = "",
        *,
        evidence_source: str = "",
        sentence: int | None = None,
        span: tuple[int, int] | None = None,
    ) -> None:
        edge = ProjectionEdge(
            kind,
            source,
            target,
            label,
            evidence_source,
            sentence,
            span,
        )
        self.edges.setdefault(edge.semantic_key(), edge)

    def build(self) -> ProjectionGraph:
        return ProjectionGraph(
            nodes=tuple(sorted(self.nodes.values())),
            edges=tuple(sorted(self.edges.values())),
        )


_LAMBDA = re.compile(r"^LAMBDA\s+([A-Za-z]\w*)\s*\.\s*")
_ATOM = re.compile(r"^(\*)?\s*(.+?)\s*\(\s*(.*?)\s*\)$")
_X_REF = re.compile(r"^x\s*_\s*(\d+)$")


def _normal_predicate(raw: str) -> str:
    return re.sub(r"\s*\.\s*", ".", raw.strip()).lower()


def _normal_ref(raw: str, bound: dict[str, str]) -> str:
    value = raw.strip()
    match = _X_REF.match(value)
    if match:
        return f"x{int(match.group(1))}"
    if value in bound:
        return bound[value]
    return f"const:{value.lower()}"


def parse_cogs_logical_form(logical_form: str) -> ProjectionGraph:
    """Parse one official COGS logical form into the normalized graph.

    The parser handles both instantiated sentence forms and the primitive
    lambda-exposure rows in the training set.  Target predicates and role names
    are schema values; no English vocabulary is enumerated here.
    """

    remaining = " ".join(str(logical_form).split())
    bound: dict[str, str] = {}
    while True:
        match = _LAMBDA.match(remaining)
        if match is None:
            break
        variable = match.group(1)
        bound[variable] = f"bound:{len(bound)}"
        remaining = remaining[match.end():]

    graph = _GraphBuilder()

    # Proper-name primitive exposure: ``Emma -> Emma``.
    if "(" not in remaining:
        if not remaining or " " in remaining:
            raise ValueError(f"unsupported COGS logical form {logical_form!r}")
        graph.node(_normal_ref(remaining, bound), "entity")
        return graph.build()

    atoms = re.split(r"\s*(?:;|\bAND\b)\s*", remaining)
    for raw_atom in atoms:
        atom = raw_atom.strip()
        if not atom:
            continue
        match = _ATOM.match(atom)
        if match is None:
            raise ValueError(f"unreadable COGS atom {atom!r} in {logical_form!r}")
        definite = bool(match.group(1))
        predicate = _normal_predicate(match.group(2))
        args = [part.strip() for part in match.group(3).split(",")]
        if len(args) not in (1, 2) or any(not part for part in args):
            raise ValueError(f"unsupported COGS arity in {atom!r}")
        refs = [_normal_ref(part, bound) for part in args]
        parts = predicate.split(".")

        if len(args) == 1:
            ref = refs[0]
            graph.node(ref, "entity")
            graph.edge("type", ref, label=parts[0])
            if definite:
                graph.edge("definite", ref)
            continue

        left, right = refs
        if len(parts) >= 3 and parts[1] == "nmod":
            graph.node(left, "entity")
            graph.node(right, "entity")
            graph.edge("modifier", left, right, parts[2])
            continue

        relation = parts[-1]
        lemma = parts[0]
        if relation in ("ccomp", "xcomp"):
            graph.node(left, "event")
            graph.node(right, "event")
            graph.edge("event", left, label=lemma)
            graph.edge("complement", left, right, relation)
            continue

        graph.node(left, "event")
        graph.node(right, "entity")
        graph.edge("event", left, label=lemma)
        graph.edge("role", left, right, relation)

    return graph.build()


_PMB_SYNSET = re.compile(r"^(.+)\.(n|v|a|r|x)\.(\d+)$")
_PMB_OFFSET = re.compile(r"^[+-]\d+$")
_PMB_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|\S+')
_PMB_ROLE_MAP = {
    "Agent": "agent",
    "Theme": "theme",
    "Recipient": "recipient",
}


def parse_pmb_sbn(sbn: str, *, document_id: str = "") -> ProjectionGraph:
    """Project explicit PMB SBN concepts and thematic roles.

    PMB sequence notation addresses concepts by signed offsets from the
    current synset.  The adapter deliberately maps only exact one-to-one
    Rulekit graph elements: nominal concepts, verbal events, adjectival
    ``AttributeOf`` properties, names, and the Agent/Theme/Recipient VerbNet
    roles.  Temporal operators, scope boxes, senses, and all other roles remain
    outside this projection view.
    """

    tokens = _PMB_TOKEN.findall(" ".join(str(sbn).split()))
    entries: list[tuple[str, str, list[str]]] = []
    index = 0
    while index < len(tokens):
        match = _PMB_SYNSET.match(tokens[index])
        if match is None:
            index += 1
            continue
        lemma, pos, _sense = match.groups()
        index += 1
        tail: list[str] = []
        while index < len(tokens) and _PMB_SYNSET.match(tokens[index]) is None:
            tail.append(tokens[index])
            index += 1
        entries.append((lemma.lower(), pos, tail))

    if not entries:
        raise ValueError(f"PMB SBN contains no synset: {sbn!r}")

    refs = [f"p{index}" for index in range(len(entries))]
    for current, (_lemma, pos, tail) in enumerate(entries):
        if pos != "n":
            continue
        for role_index in range(0, len(tail) - 1):
            if tail[role_index] == "Name":
                raw_name = tail[role_index + 1]
                if not (raw_name.startswith('"') and raw_name.endswith('"')):
                    continue
                name = " ".join(raw_name[1:-1].lower().split())
                if name and not _PMB_OFFSET.match(name):
                    refs[current] = f"const:{name}"
                break

    graph = _GraphBuilder()
    for current, (lemma, pos, tail) in enumerate(entries):
        ref = refs[current]
        source = (
            f"pmb:{document_id}:synset:{current}"
            if document_id
            else f"pmb:synset:{current}"
        )
        if pos == "v":
            graph.node(ref, "event", evidence_source=source)
            graph.edge("event", ref, label=lemma, evidence_source=source)
        elif pos == "n":
            graph.node(ref, "entity", evidence_source=source)
            graph.edge("type", ref, label=lemma, evidence_source=source)

        for role_index in range(0, len(tail) - 1):
            role = tail[role_index]
            target_token = tail[role_index + 1]
            if not _PMB_OFFSET.match(target_token):
                continue
            target_index = current + int(target_token)
            if not 0 <= target_index < len(entries):
                # PMB's reference parser treats an out-of-range signed token
                # as a numeric constant that merely resembles an offset.
                continue
            target_lemma, target_pos, _target_tail = entries[target_index]
            target_ref = refs[target_index]
            edge_source = f"{source}:role:{role_index}"
            if (
                pos == "v"
                and target_pos == "n"
                and role in _PMB_ROLE_MAP
            ):
                graph.node(
                    target_ref,
                    "entity",
                    evidence_source=(
                        f"pmb:{document_id}:synset:{target_index}"
                        if document_id
                        else f"pmb:synset:{target_index}"
                    ),
                )
                graph.edge(
                    "role",
                    ref,
                    target_ref,
                    _PMB_ROLE_MAP[role],
                    evidence_source=edge_source,
                )
            elif pos == "a" and target_pos == "n" and role == "AttributeOf":
                graph.node(
                    target_ref,
                    "entity",
                    evidence_source=(
                        f"pmb:{document_id}:synset:{target_index}"
                        if document_id
                        else f"pmb:synset:{target_index}"
                    ),
                )
                graph.edge(
                    "type",
                    target_ref,
                    label=lemma,
                    evidence_source=edge_source,
                )

    return graph.build()


@dataclass(frozen=True)
class ProjectionItem:
    id: str
    text: str
    gold: ProjectionGraph
    case: str
    construction: str
    adapter: str = "cogs"


def classify_projection_graph(graph: ProjectionGraph, case: str = "") -> str:
    """A vocabulary-free structural worklist label derived from the gold graph."""

    if case == "primitive" or any(
        node.ref.startswith("bound:") for node in graph.nodes
    ):
        return "primitive"
    complements = [
        edge.label for edge in graph.edges if edge.kind == "complement"
    ]
    if complements:
        if len(complements) > 1:
            return "nested-complement"
        return f"{complements[0]}-complement"
    modifiers = [edge for edge in graph.edges if edge.kind == "modifier"]
    if modifiers:
        return "nested-modifier" if len(modifiers) > 1 else "nominal-modifier"
    roles = [edge.label for edge in graph.edges if edge.kind == "role"]
    if "recipient" in roles:
        return "ditransitive"
    if "agent" in roles and "theme" in roles:
        return "transitive"
    if roles == ["agent"] or (roles and set(roles) == {"agent"}):
        return "intransitive-agent"
    if roles == ["theme"] or (roles and set(roles) == {"theme"}):
        return "intransitive-theme"
    if any(edge.kind == "type" for edge in graph.edges):
        return "nominal"
    return "other"


def load_projection_items(
    project_root: Path,
    split: ProjectionSplitDef,
    adapter: str,
) -> list[ProjectionItem]:
    import pyarrow.parquet as pq

    parsers = {
        "cogs": parse_cogs_logical_form,
        "pmb": parse_pmb_sbn,
    }
    parser = parsers.get(adapter)
    if parser is None:
        raise ValueError(f"unsupported projection adapter {adapter!r}")
    columns = [
        split.item_id,
        split.text,
        split.logical_form,
        split.case,
    ]
    if split.scored:
        columns.append(split.scored)
    table = pq.read_table(project_root / split.parquet, columns=columns)
    values = {name: table.column(name).to_pylist() for name in columns}
    items: list[ProjectionItem] = []
    for index in range(table.num_rows):
        if split.scored and not bool(values[split.scored][index]):
            continue
        logical_form = str(values[split.logical_form][index])
        item_id = str(values[split.item_id][index])
        gold_graph = (
            parse_pmb_sbn(logical_form, document_id=item_id)
            if adapter == "pmb"
            else parser(logical_form)
        )
        case = str(values[split.case][index])
        items.append(
            ProjectionItem(
                id=item_id,
                text=str(values[split.text][index]),
                gold=gold_graph,
                case=case,
                construction=classify_projection_graph(gold_graph, case),
                adapter=adapter,
            )
        )
    return items


def _align_projection_refs(
    got: ProjectionGraph,
    expected: ProjectionGraph,
) -> ProjectionGraph:
    """Rename runtime-local refs onto an independently named gold graph.

    PMB synset ordinals and Rulekit token anchors are both local identifiers,
    not semantics. Constants remain anchored by value. Non-constant nodes are
    injectively matched by kind and asserted unary labels, with edge agreement
    selecting among otherwise equivalent candidates.
    """

    expected_nodes = {node.ref: node for node in expected.nodes}
    got_nodes = {node.ref: node for node in got.nodes}

    def unary(graph: ProjectionGraph, ref: str) -> frozenset[tuple[str, str]]:
        return frozenset(
            (edge.kind, edge.label)
            for edge in graph.edges
            if edge.source == ref
            and not edge.target
            and edge.kind in {"type", "event", "definite"}
        )

    candidates: dict[str, tuple[str, ...]] = {}
    for ref, node in got_nodes.items():
        if ref.startswith("const:"):
            candidate = expected_nodes.get(ref)
            candidates[ref] = (
                (ref,)
                if candidate is not None and candidate.kind == node.kind
                else ()
            )
            continue
        asserted = unary(got, ref)
        candidates[ref] = tuple(
            expected_ref
            for expected_ref, expected_node in expected_nodes.items()
            if not expected_ref.startswith("const:")
            and expected_node.kind == node.kind
            and asserted <= unary(expected, expected_ref)
        )

    ordered = sorted(
        got_nodes,
        key=lambda ref: (len(candidates[ref]), ref),
    )
    expected_edge_keys = expected.edge_keys()
    best_mapping: dict[str, str] = {}
    best_score = -1

    def score(mapping: dict[str, str]) -> int:
        matched_nodes = len(mapping)
        matched_edges = sum(
            (
                edge.kind,
                mapping.get(edge.source, f"got:{edge.source}"),
                mapping.get(edge.target, f"got:{edge.target}") if edge.target else "",
                edge.label,
            )
            in expected_edge_keys
            for edge in got.edges
        )
        return matched_nodes + 2 * matched_edges

    def visit(position: int, mapping: dict[str, str], used: set[str]) -> None:
        nonlocal best_mapping, best_score
        if position == len(ordered):
            candidate_score = score(mapping)
            if candidate_score > best_score:
                best_score = candidate_score
                best_mapping = dict(mapping)
            return
        ref = ordered[position]
        choices = [value for value in candidates[ref] if value not in used]
        if not choices:
            visit(position + 1, mapping, used)
            return
        for value in choices:
            mapping[ref] = value
            used.add(value)
            visit(position + 1, mapping, used)
            used.remove(value)
            del mapping[ref]

    visit(0, {}, set())

    def mapped(ref: str) -> str:
        if not ref:
            return ""
        return best_mapping.get(ref, f"got:{ref}")

    return ProjectionGraph(
        nodes=tuple(sorted(
            ProjectionNode(
                mapped(node.ref),
                node.kind,
                node.evidence_source,
                node.sentence,
                node.span,
            )
            for node in got.nodes
        )),
        edges=tuple(sorted(
            ProjectionEdge(
                edge.kind,
                mapped(edge.source),
                mapped(edge.target),
                edge.label,
                edge.evidence_source,
                edge.sentence,
                edge.span,
            )
            for edge in got.edges
        )),
    )


def _unit_key(unit) -> str:
    value = unit.features.get("lemma") or unit.surface
    return " ".join(str(value).lower().split())


def _find_unit(reading, value: str, *, after: int = -1):
    key = " ".join(value.lower().split())
    candidates = [
        unit
        for unit in reading.units
        if unit.span[0] > after
        and (_unit_key(unit) == key or unit.surface.lower() == key)
    ]
    return min(candidates, key=lambda unit: unit.span[0]) if candidates else None


def _constant_ref(value: str) -> str:
    return f"const:{' '.join(value.lower().split())}"


def _semantic_ref(value: str) -> str:
    prefix, separator, payload = value.partition(":")
    if not separator or not payload:
        return ""
    if prefix == "name":
        return _constant_ref(payload)
    if prefix in ("entity", "event") and payload.isdigit():
        return f"x{int(payload)}"
    return ""


def _semantic_span(start: str, end: str) -> tuple[int, int] | None:
    if not start.isdigit() or not end.isdigit():
        return None
    return int(start), int(end)


def project_result(
    result,
    source_text: str,
    reg: Registry | None = None,
) -> ProjectionGraph:
    """Project only structures the current FactStore states exactly.

    Phase B's first-class semantic node/edge facts are the primary path.
    ``VerbalRelation`` remains the narrow Phase A compatibility bridge for
    forms no semantic pack owns. Flat ``Atom`` phrase keys are deliberately
    never split here.
    """

    graph = _GraphBuilder()
    readings = {reading.sentence_index: reading for reading in result.premises}
    words = source_text.split()
    for fact in result.store.facts:
        if isinstance(fact, SemanticGraphNode):
            ref = _semantic_ref(fact.ref)
            if ref:
                graph.node(
                    ref,
                    fact.kind,
                    evidence_source=fact.provenance.source,
                    sentence=fact.provenance.sentence,
                    span=_semantic_span(fact.span_start, fact.span_end),
                )
            continue
        if isinstance(fact, SemanticGraphEdge):
            source = _semantic_ref(fact.source)
            target = _semantic_ref(fact.target) if fact.target else ""
            if source and (not fact.target or target):
                graph.edge(
                    fact.kind,
                    source,
                    target,
                    fact.label,
                    evidence_source=fact.provenance.source,
                    sentence=fact.provenance.sentence,
                    span=_semantic_span(fact.span_start, fact.span_end),
                )
            continue
        if not isinstance(fact, VerbalRelation) or not fact.polarity or fact.prep:
            continue
        reading = readings.get(fact.provenance.sentence)
        if reading is None:
            continue
        subject = _find_unit(reading, fact.entity)
        verb = _find_unit(reading, fact.verb)
        obj = _find_unit(reading, fact.obj, after=verb.span[-1] if verb else -1)
        if subject is None or verb is None or obj is None:
            continue
        if reg is not None and (
            reg.word_in_category(
                verb.features.get("fold", ""),
                "semantic_projection_owned_verb",
            )
            or reg.word_in_category(
                verb.features.get("lemma", ""),
                "semantic_projection_owned_verb",
            )
        ):
            # A first-class semantic pack owns these newly admitted event
            # forms. The legacy bridge must not turn their vocabulary into
            # coverage for a neighbouring construction the semantic pack did
            # not buy. Nominal vocabulary is deliberately irrelevant here:
            # the legacy span rule already tolerated unknown object words.
            continue

        event_ref = f"x{verb.span[0]}"
        subject_ref = _constant_ref(fact.entity)
        object_is_name = obj.sense() == "name"
        object_ref = (
            _constant_ref(fact.obj)
            if object_is_name
            else f"x{obj.span[-1]}"
        )
        evidence = fact.provenance.source
        sentence = fact.provenance.sentence
        fact_span = (subject.span[0], obj.span[-1])

        graph.node(
            event_ref,
            "event",
            evidence_source=evidence,
            sentence=sentence,
            span=verb.span,
        )
        graph.node(
            subject_ref,
            "entity",
            evidence_source=evidence,
            sentence=sentence,
            span=subject.span,
        )
        graph.node(
            object_ref,
            "entity",
            evidence_source=evidence,
            sentence=sentence,
            span=obj.span,
        )
        # COGS predicates are lemmas.  A unit whose registered lemma is still
        # byte-identical to its inflected surface has supplied no evidence for
        # that normalization ("missed" registered as lemma "missed").  Keep
        # the correctly anchored event/roles as a safe partial graph, but do
        # not promote the surface spelling to an event predicate.
        if _unit_key(verb) != verb.surface.lower():
            graph.edge(
                "event",
                event_ref,
                label=fact.verb,
                evidence_source=evidence,
                sentence=sentence,
                span=verb.span,
            )
        graph.edge(
            "role",
            event_ref,
            subject_ref,
            "agent",
            evidence_source=evidence,
            sentence=sentence,
            span=fact_span,
        )
        graph.edge(
            "role",
            event_ref,
            object_ref,
            "theme",
            evidence_source=evidence,
            sentence=sentence,
            span=fact_span,
        )
        # Likewise, an ambiguous object unit can carry the verb reading's
        # lemma ("rose" -> "rise") even though the direct-object construction
        # proves a nominal role.  The role edge is sound; the class label is
        # not, so expose the missing type instead of asserting the wrong one.
        if (
            not object_is_name
            and not obj.features.get("ambiguous")
            and len(fact.obj.split()) == 1
            and fact.obj == obj.surface.lower()
        ):
            graph.edge(
                "type",
                object_ref,
                label=fact.obj,
                evidence_source=evidence,
                sentence=sentence,
                span=obj.span,
            )
        anchor = obj.span[0]
        if (
            not object_is_name
            and anchor > 0
            and anchor - 1 < len(words)
            and words[anchor - 1].lower() == "the"
        ):
            graph.edge(
                "definite",
                object_ref,
                evidence_source=evidence,
                sentence=sentence,
                span=obj.span,
            )
    return graph.build()


@dataclass
class ProjectionItemResult:
    id: str
    case: str
    construction: str
    outcome: str  # exact | partial | declined | incorrect | errored
    expected: ProjectionGraph
    got: ProjectionGraph
    missing_nodes: tuple[tuple[str, str], ...] = ()
    missing_edges: tuple[tuple[str, str, str, str], ...] = ()
    extra_nodes: tuple[tuple[str, str], ...] = ()
    extra_edges: tuple[tuple[str, str, str, str], ...] = ()
    unknown_words: tuple[str, ...] = ()
    reason: str = ""


@dataclass
class ProjectionReport:
    results: list[ProjectionItemResult]
    fingerprint: str
    elapsed: float

    @property
    def counts(self) -> dict[str, int]:
        out = {
            "exact": 0,
            "partial": 0,
            "declined": 0,
            "incorrect": 0,
            "errored": 0,
        }
        for result in self.results:
            out[result.outcome] += 1
        return out

    @property
    def edge_precision(self) -> float | None:
        predicted = sum(len(result.got.edge_keys()) for result in self.results)
        if predicted == 0:
            return None
        correct = sum(
            len(result.got.edge_keys() & result.expected.edge_keys())
            for result in self.results
        )
        return correct / predicted

    @property
    def edge_recall(self) -> float:
        expected = sum(len(result.expected.edge_keys()) for result in self.results)
        if expected == 0:
            return 0.0
        correct = sum(
            len(result.got.edge_keys() & result.expected.edge_keys())
            for result in self.results
        )
        return correct / expected

    def case_counts(self) -> dict[str, dict[str, int]]:
        cases: dict[str, dict[str, int]] = {}
        for result in self.results:
            counts = cases.setdefault(
                result.case,
                {
                    "items": 0,
                    "exact": 0,
                    "partial": 0,
                    "declined": 0,
                    "incorrect": 0,
                    "errored": 0,
                },
            )
            counts["items"] += 1
            counts[result.outcome] += 1
        return dict(sorted(cases.items()))

    def construction_counts(self) -> dict[str, dict[str, int]]:
        constructions: dict[str, dict[str, int]] = {}
        for result in self.results:
            counts = constructions.setdefault(
                result.construction,
                {
                    "items": 0,
                    "exact": 0,
                    "partial": 0,
                    "declined": 0,
                    "incorrect": 0,
                    "errored": 0,
                },
            )
            counts["items"] += 1
            counts[result.outcome] += 1
        return dict(sorted(constructions.items()))

    def aggregates(self) -> dict:
        precision = self.edge_precision
        return {
            "items": len(self.results),
            **self.counts,
            "edge_precision": precision,
            "edge_recall": self.edge_recall,
            "cases": self.case_counts(),
            "constructions": self.construction_counts(),
        }

    def summary(self, *, items_visible: bool = True) -> str:
        counts = self.counts
        precision = (
            f"{self.edge_precision:.1%}"
            if self.edge_precision is not None
            else "n/a"
        )
        blockers = Counter(
            edge[0]
            for result in self.results
            for edge in result.missing_edges
        )
        lines = [
            f"items          {len(self.results)}",
            f"exact          {counts['exact']}",
            f"partial        {counts['partial']}  (all projected elements correct)",
            f"declined       {counts['declined']}  (no semantic commitment)",
            f"incorrect      {counts['incorrect']}   <- must trend to 0",
            f"errored        {counts['errored']}",
            f"edge precision {precision}  (THE safety metric)",
            f"edge recall    {self.edge_recall:.1%}",
            f"elapsed        {self.elapsed:.2f}s",
        ]
        if blockers:
            lines.append("missing graph elements (the DEV worklist):")
            for kind, count in blockers.most_common():
                lines.append(f"  {count:6d}  {kind}")
        cases = self.case_counts()
        if len(cases) > 1 or next(iter(cases), "") != "in_distribution":
            lines.append("construction cases:")
            for case, case_count in cases.items():
                lines.append(
                    f"  {case}: exact {case_count['exact']}/{case_count['items']}, "
                    f"partial {case_count['partial']}, "
                    f"incorrect {case_count['incorrect']}"
                )
        lines.append("structural construction worklist:")
        for construction, construction_count in sorted(
            self.construction_counts().items(),
            key=lambda item: (-item[1]["items"], item[0]),
        ):
            lines.append(
                f"  {construction}: exact "
                f"{construction_count['exact']}/{construction_count['items']}, "
                f"partial {construction_count['partial']}, "
                f"incorrect {construction_count['incorrect']}"
            )
        incorrect = [r for r in self.results if r.outcome == "incorrect"]
        if incorrect and items_visible:
            lines.append("incorrect projections:")
            for result in incorrect[:25]:
                lines.append(
                    f"  {result.id}: +{len(result.extra_nodes)} nodes, "
                    f"+{len(result.extra_edges)} edges"
                )
        elif incorrect:
            lines.append(
                f"incorrect projections: {len(incorrect)} "
                "(aggregate-only slice — items withheld)"
            )
        return "\n".join(lines)

    def to_snapshot(self) -> dict:
        return {
            "kind": "projection",
            "schema": PROJECTION_SCHEMA,
            "fingerprint": self.fingerprint,
            "items": {
                result.id: {
                    "case": result.case,
                    "construction": result.construction,
                    "outcome": result.outcome,
                    "expected": result.expected.to_json(),
                    "got": result.got.to_json(),
                    "missing_nodes": [list(value) for value in result.missing_nodes],
                    "missing_edges": [list(value) for value in result.missing_edges],
                    "extra_nodes": [list(value) for value in result.extra_nodes],
                    "extra_edges": [list(value) for value in result.extra_edges],
                    "unknown_words": list(result.unknown_words),
                    "reason": result.reason,
                }
                for result in self.results
            },
        }


def _score_item(index: int, item: ProjectionItem, reg: Registry) -> ProjectionItemResult:
    try:
        result = solve(item.text, reg, tracing=False)
        got = project_result(result, item.text, reg)
        if item.adapter == "pmb":
            got = _align_projection_refs(got, item.gold)
        gold_nodes = item.gold.node_keys()
        gold_edges = item.gold.edge_keys()
        got_nodes = got.node_keys()
        got_edges = got.edge_keys()
        missing_nodes = tuple(sorted(gold_nodes - got_nodes))
        missing_edges = tuple(sorted(gold_edges - got_edges))
        extra_nodes = tuple(sorted(got_nodes - gold_nodes))
        extra_edges = tuple(sorted(got_edges - gold_edges))
        if extra_nodes or extra_edges:
            outcome = "incorrect"
        elif got.empty:
            outcome = "declined"
        elif missing_nodes or missing_edges:
            outcome = "partial"
        else:
            outcome = "exact"
        unknown = tuple(sorted({
            word.lower()
            for reading in result.premises
            for word in reading.unknown_words()
        }))
        return ProjectionItemResult(
            id=item.id or str(index),
            case=item.case,
            construction=item.construction,
            outcome=outcome,
            expected=item.gold,
            got=got,
            missing_nodes=missing_nodes,
            missing_edges=missing_edges,
            extra_nodes=extra_nodes,
            extra_edges=extra_edges,
            unknown_words=unknown,
            reason=result.answer.reason,
        )
    except Exception as exc:  # noqa: BLE001 — errored is an evaluation bucket
        return ProjectionItemResult(
            id=item.id or str(index),
            case=item.case,
            construction=item.construction,
            outcome="errored",
            expected=item.gold,
            got=ProjectionGraph(),
            reason=repr(exc),
        )


_WORKER_REG: Registry | None = None


def _worker_init(project_dir: str, expected_fingerprint: str) -> None:
    global _WORKER_REG
    from ..data.project import load_project

    registry = load_project(Path(project_dir)).registry
    if registry.fingerprint != expected_fingerprint:
        raise RuntimeError(
            f"worker registry fingerprint {registry.fingerprint!r} != parent "
            f"{expected_fingerprint!r}"
        )
    _WORKER_REG = registry


def _run_one(arg: tuple[int, ProjectionItem]) -> ProjectionItemResult:
    assert _WORKER_REG is not None
    return _score_item(arg[0], arg[1], _WORKER_REG)


def run_projection_suite(
    items: list[ProjectionItem],
    reg: Registry,
    *,
    jobs: int = 1,
    project_dir: Path | None = None,
) -> ProjectionReport:
    started = time.monotonic()
    if jobs > 1 and project_dir is not None and len(items) > 1:
        context = multiprocessing.get_context("spawn")
        with context.Pool(
            processes=jobs,
            initializer=_worker_init,
            initargs=(str(project_dir), reg.fingerprint),
        ) as pool:
            results = pool.map(
                _run_one,
                list(enumerate(items)),
                chunksize=32,
            )
    else:
        results = [
            _score_item(index, item, reg)
            for index, item in enumerate(items)
        ]
    adapters = ",".join(sorted({item.adapter for item in items}))
    fingerprint = hashlib.sha256(
        f"{reg.fingerprint}:{PROJECTION_SCHEMA}:{adapters}@1".encode()
    ).hexdigest()
    return ProjectionReport(
        results=results,
        fingerprint=fingerprint,
        elapsed=time.monotonic() - started,
    )


def write_projection_snapshot(report: ProjectionReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_snapshot(), indent=2, sort_keys=True))
