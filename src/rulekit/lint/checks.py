"""Assorted static checks: overrides hygiene, quarantine references,
unused categories."""

from __future__ import annotations

from ..data.registry import Registry
from .blast_radius import _rule_gates
from .overlap import Finding


def lint_checks(reg: Registry) -> list[Finding]:
    findings: list[Finding] = []
    rule_ids = {r.id for r in reg.rules}

    for rule in reg.rules:
        if rule.overrides:
            target = rule.overrides.get("rule")
            reason = rule.overrides.get("reason")
            if target not in rule_ids:
                findings.append(
                    Finding("error", "override-dangling",
                            f"{rule.id} overrides unknown rule {target!r}")
                )
            if not reason:
                findings.append(
                    Finding("error", "override-unreasoned",
                            f"{rule.id} overrides {target!r} without a reason")
                )
            else:
                findings.append(
                    Finding("info", "override",
                            f"{rule.id} overrides {target} — goal is zero of these")
                )

    used_gates: set[str] = set()
    for rule in list(reg.rules) + list(reg.asks):
        used_gates.update(_rule_gates(rule))
    for cat in sorted(reg.category_parents):
        in_hierarchy_of_used = any(
            cat in reg.cat_ancestors(g) or g in reg.cat_ancestors(cat)
            for g in used_gates
            if g in reg.category_parents
        )
        has_polarity = cat in reg.category_polarity
        has_ctx = any(gate == cat for gate, _ in reg.context_synonyms.values())
        if not in_hierarchy_of_used and not has_polarity and not has_ctx:
            findings.append(
                Finding("info", "category-unused",
                        f"category {cat!r} has no gating rule, polarity, or "
                        "context synonym yet")
            )
    return findings
