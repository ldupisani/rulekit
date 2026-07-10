"""Category blast radius: what a category change can touch, BEFORE running.

The difg `pet` disaster: one category tag silently activated an unrelated
fallback and turned a correct decline into a confident wrong. Here category
consumers are declared gates, so the impact of a change is enumerable."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.registry import Registry
from ..data.schemas import PatternRule


@dataclass
class BlastReport:
    category: str
    ancestors: list[str]
    member_words: list[str]
    gating_rules: list[str] = field(default_factory=list)  # rules whose gates admit these words
    context_synonyms: list[str] = field(default_factory=list)
    polarity: int | None = None
    antonym: str | None = None

    def summary(self) -> str:
        lines = [
            f"category {self.category!r}  (chain: {' -> '.join(self.ancestors)})",
            f"  members (deep): {len(self.member_words)} words"
            + (f" — {self.member_words[:12]}{'…' if len(self.member_words) > 12 else ''}" if self.member_words else ""),
        ]
        if self.polarity is not None:
            lines.append(f"  polarity: {self.polarity:+d} (antonym: {self.antonym})")
        if self.gating_rules:
            lines.append(
                f"  rules whose gates admit these words ({len(self.gating_rules)}):"
            )
            for r in self.gating_rules:
                lines.append(f"    - {r}")
            lines.append(
                "  ^ every one of these fires on member words — re-run the full"
                " suite diff after ANY membership change (a tag is global state)."
            )
        else:
            lines.append("  no pattern rules currently gate on this hierarchy")
        if self.context_synonyms:
            lines.append(f"  context synonyms gated here: {self.context_synonyms}")
        return "\n".join(lines)


def _rule_gates(rule: PatternRule) -> list[str]:
    gates = []
    for seq in rule.match.values():
        flat = seq if seq and not isinstance(seq[0], list) else [t for s in seq for t in s]
        for tok in flat:
            cat = getattr(tok, "cat", None)
            if cat:
                gates.append(cat)
            if getattr(tok, "opt", None):
                for sub in tok.opt:
                    if sub.cat:
                        gates.append(sub.cat)
    return gates


def blast_radius(reg: Registry, category: str) -> BlastReport:
    ancestors = reg.cat_ancestors(category)
    hierarchy = set(ancestors) | set(reg.cat_descendants(category))
    report = BlastReport(
        category=category,
        ancestors=ancestors,
        member_words=reg.cat_members_deep(category),
        polarity=reg.category_polarity.get(category),
        antonym=reg.category_antonyms.get(category),
    )
    for rule in list(reg.rules) + list(reg.asks):
        gates = _rule_gates(rule)
        # a gate on the category itself, any ancestor (member words satisfy
        # broader gates), or any descendant (narrower gates inside the subtree)
        if any(g in hierarchy for g in gates):
            report.gating_rules.append(rule.id)
    for concept, (gate, _forms) in sorted(reg.context_synonyms.items()):
        if gate in hierarchy:
            report.context_synonyms.append(concept)
    return report
