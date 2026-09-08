"""Expand local, data-only rule templates into ordinary validated rules.

Parameters replace complete YAML values. A list parameter in a list is
spliced, allowing optional grammatical components without string evaluation.
Source nodes are retained separately for the Designer; inference sees only
the expanded PatternRule or AskRule.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .schemas import RuleTemplate, TemplateVariant


def expand_rule_template(
    template: RuleTemplate, variant: TemplateVariant,
) -> tuple[dict[str, Any], dict[tuple[str | int, ...], Any]]:
    unknown = set(variant.arguments) - set(template.parameters)
    if unknown:
        raise ValueError(f"rule {variant.id!r}: unknown template parameters {sorted(unknown)}")
    arguments = {**template.parameters, **variant.arguments}
    origins = {}
    used = set()

    def parameter(node):
        if not isinstance(node, dict) or "parameter" not in node:
            return node
        if set(node) != {"parameter"} or not isinstance(node["parameter"], str):
            raise ValueError("a parameter reference must contain only one string `parameter`")
        parts = node["parameter"].split(".")
        if not all(parts):
            raise ValueError("parameter paths cannot have empty components")
        used.add(parts[0])
        value = arguments
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                raise ValueError(f"rule {variant.id!r}: unknown parameter path {node['parameter']!r}")
            value = value[part]
        return value

    def reject_nested_references(node):
        if isinstance(node, dict):
            if "parameter" in node:
                raise ValueError("template arguments must be literal YAML values, not parameter references")
            for value in node.values():
                reject_nested_references(value)
        elif isinstance(node, list):
            for value in node:
                reject_nested_references(value)

    for value in arguments.values():
        reject_nested_references(value)

    def expand(node, path=()):
        node = parameter(node)
        origins[path] = node
        if isinstance(node, dict):
            return {key: expand(value, (*path, key)) for key, value in node.items()}
        if isinstance(node, list):
            result = []
            for child in node:
                replacement = parameter(child)
                # Only a parameter can splice a sequence. Ordinary nested
                # lists retain their meaning (e.g. multi-sentence patterns).
                splice = (
                    isinstance(child, dict)
                    and "parameter" in child
                    and isinstance(replacement, list)
                )
                children = replacement if splice else [replacement]
                for value in children:
                    result.append(expand(value, (*path, len(result))))
            return result
        # Round-trip YAML scalars carry source metadata too. Preserve those
        # in origins, but give schema validation ordinary built-in values.
        if isinstance(node, bool):
            return bool(node)
        if isinstance(node, int):
            return int(node)
        if isinstance(node, float):
            return float(node)
        if isinstance(node, str):
            return str(node)
        return deepcopy(node)

    expanded = expand(template.rule)
    unused = set(template.parameters) - used
    if unused:
        raise ValueError(f"template has unused parameters {sorted(unused)}")
    if "id" in expanded:
        raise ValueError("a template cannot own a rule id; its variants own stable ids")
    expanded["id"] = variant.id
    description = getattr(variant, "description", None)
    if description is not None:
        expanded["description"] = description
    return expanded, origins
