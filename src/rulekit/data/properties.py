"""Compile scalar and derived properties through declared category ancestry.

This module validates symbolic dimensions, conflicts and dependencies. Runtime
arithmetic stays in kernel.evaluate; no formula or vocabulary is implemented here.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from .schemas import DerivedAttributeDef, DimensionSpec

Dimension = tuple[tuple[str, float], ...]


class PropertyError(ValueError):
    pass


def dimension(spec: DimensionSpec) -> Dimension:
    values = {spec: 1} if isinstance(spec, str) else spec
    return tuple(sorted((k, float(v)) for k, v in values.items() if v))


def combine(a: Dimension, b: Dimension, sign: int = 1) -> Dimension:
    values = dict(a)
    for key, power in b:
        values[key] = values.get(key, 0) + sign * power
    return tuple(sorted((k, v) for k, v in values.items() if v))


@dataclass(frozen=True, order=True)
class PropertyOrigin:
    kind: str
    owner: str
    pack: str


@dataclass(frozen=True)
class DerivedAttribute:
    expr: str
    inputs: Mapping[str, Dimension]
    result_dimension: Dimension
    constants: Mapping[str, float]


def compile_formula(definition: DerivedAttributeDef, global_constants=None) -> DerivedAttribute:
    inputs = {k: dimension(v) for k, v in definition.inputs.items()}
    constants = definition.constants
    if isinstance(constants, list):
        if len(constants) != len(set(constants)) or set(constants) - (global_constants or {}).keys():
            raise PropertyError("formula references an unknown or duplicate named constant")
        constants = {key: global_constants[key] for key in constants}
    try:
        tree = ast.parse(definition.expr, mode="eval")
    except SyntaxError as exc:
        raise PropertyError("invalid formula expression") from exc
    used: set[str] = set()

    def infer(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and isfinite(node.value):
            return ()
        if isinstance(node, ast.Name):
            if node.id not in inputs and node.id not in constants:
                raise PropertyError(f"undeclared formula input {node.id!r}")
            used.add(node.id)
            return inputs.get(node.id, ())
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return infer(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = infer(node.left), infer(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if left != right:
                    raise PropertyError("formula addition requires compatible dimensions")
                return left
            if isinstance(node.op, ast.Mult):
                return combine(left, right)
            if isinstance(node.op, ast.Div):
                return combine(left, right, -1)
            if isinstance(node.op, ast.Pow):
                if right or not isinstance(node.right, ast.Constant) or type(node.right.value) not in (int, float):
                    raise PropertyError("formula powers require a constant dimensionless exponent")
                return tuple((key, power * node.right.value) for key, power in left if power * node.right.value)
        raise PropertyError("unsupported formula syntax")

    result = infer(tree.body)
    if used != inputs.keys() | constants.keys():
        raise PropertyError("formula declarations contain unused inputs or constants")
    expected = dimension(definition.result_dimension)
    if result != expected:
        raise PropertyError(f"formula result dimension {result!r} differs from {expected!r}")
    return DerivedAttribute(definition.expr, MappingProxyType(inputs), expected,
                            MappingProxyType(dict(constants)))


def compile_properties(*, lexicon, plurals, parents, word_categories, category_defs,
                       word_attrs, word_formulas, word_bindings, word_origins, constants=None):
    """Return effective values/formulas/sources/bindings for classes and words.

    Parent edges carry definitions downward. Includes unions contribute members
    only; they never copy a child's properties onto the union or its siblings.
    """
    declarations = {}
    binding_declarations = {}
    for word in word_attrs.keys() & word_formulas.keys():
        if word_attrs[word].keys() & word_formulas[word].keys():
            raise PropertyError(f"a word property cannot be both scalar and derived: {word!r}")
    for category, (definition, pack) in category_defs.items():
        declarations[category] = {
            **definition.attrs,
            **{key: compile_formula(value, constants) for key, value in definition.formulas.items()},
        }
        binding_declarations[category] = dict(definition.parameter_bindings)

    def ancestors(category):
        chain = [category]
        while chain[-1] in parents:
            chain.append(parents[chain[-1]])
        return chain

    def root(category):
        return ancestors(category)[-1]

    attrs, formulas, sources, bindings = {}, {}, {}, {}
    subjects = set(lexicon) | set(parents) | set(plurals) | set(word_attrs) | set(word_formulas) | set(word_bindings)
    for subject in sorted(subjects):
        lemma = plurals.get(subject, subject)
        tags = set(word_categories.get(subject, ()))
        if lemma != subject:
            tags.update(cat for cat in word_categories.get(lemma, ()) if root(cat) == "noun")
        if subject in parents:
            tags.add(subject)
        categories = {cat for tag in tags for cat in ancestors(tag) if cat in parents}
        properties = {key for cat in categories for key in declarations[cat]}
        binding_keys = {key for cat in categories for key in binding_declarations[cat]}
        # Legacy word-level grammatical metadata is not noun morphology.
        # A mixed-sense lemma's ordinal/verb attributes must not leak to a noun plural.
        lexical = lemma if lemma == subject or lexicon.get(lemma) and lexicon[lemma].senses == ["noun"] else subject
        direct = dict(word_attrs.get(lexical, {}))
        direct.update(word_formulas.get(lexical, {}))
        properties.update(direct)
        binding_keys.update(word_bindings.get(lexical, {}))

        def select(key, tables):
            candidates = [cat for cat in categories if key in tables[cat]]
            specific = [cat for cat in candidates if not any(
                cat != other and cat in ancestors(other)[1:] for other in candidates)]
            if not specific:
                return None, ()
            values = [tables[cat][key] for cat in sorted(specific)]
            if any(value != values[0] for value in values[1:]):
                raise PropertyError(f"conflicting property {key!r} for {subject!r}: {sorted(specific)}")
            origins = tuple(PropertyOrigin("category", cat, category_defs[cat][1]) for cat in sorted(specific))
            return values[0], origins

        for key in sorted(properties):
            if key in direct:
                value = direct[key]
                if isinstance(value, DerivedAttributeDef):
                    value = compile_formula(value, constants)
                origins = (PropertyOrigin("word", lexical, word_origins.get((lexical, key), "")),)
            else:
                value, origins = select(key, declarations)
            if isinstance(value, DerivedAttribute):
                formulas.setdefault(subject, {})[key] = value
            elif value is not None:
                if not isfinite(value):
                    raise PropertyError(f"non-finite attribute {key!r} for {subject!r}")
                attrs.setdefault(subject, {})[key] = float(value)
            sources[(subject, key)] = origins
        selected_bindings = {}
        for key in sorted(binding_keys):
            if key in word_bindings.get(lexical, {}):
                value = word_bindings[lexical][key]
                origins = (PropertyOrigin("word", lexical, word_origins.get((lexical, "binding:" + key), "")),)
            else:
                value, origins = select(key, binding_declarations)
            selected_bindings[key] = value
            sources[(subject, "binding:" + key)] = origins
        if selected_bindings:
            bindings[subject] = selected_bindings
        validate_dependencies(subject, formulas.get(subject, {}), attrs.get(subject, {}), selected_bindings)
    return attrs, formulas, sources, bindings


def validate_dependencies(subject, formulas, attrs, bindings):
    if any(not name.isidentifier() for pair in bindings.items() for name in pair):
        raise PropertyError(f"parameter bindings must name identifiers for {subject!r}")
    declared = {key for formula in formulas.values() for key in formula.inputs}
    if set(bindings) - declared - set(bindings.values()):
        raise PropertyError(f"unused parameter binding for {subject!r}")
    def canonical(name, seen=()):
        if name in seen:
            raise PropertyError(f"parameter binding cycle for {subject!r}")
        target = bindings.get(name)
        return canonical(target, (*seen, name)) if target else name

    for name in bindings:
        canonical(name)
    dimensions = {}
    for formula in formulas.values():
        for name, dim in formula.inputs.items():
            name = canonical(name)
            if name in dimensions and dimensions[name] != dim:
                raise PropertyError(f"incompatible parameter dimensions for {subject!r}: {name!r}")
            dimensions[name] = dim
    seen, visiting = set(), set()

    def visit(key):
        if key in visiting:
            raise PropertyError(f"formula dependency cycle for {subject!r}: {key!r}")
        if key in seen:
            return
        visiting.add(key)
        for name, expected in formulas[key].inputs.items():
            name = canonical(name)
            if name in formulas:
                if formulas[name].result_dimension != expected:
                    raise PropertyError(f"incompatible derived input dimension for {subject!r}: {name!r}")
                visit(name)
        visiting.remove(key)
        seen.add(key)
    for key in formulas:
        visit(key)
