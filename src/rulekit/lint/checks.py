"""Assorted static checks: overrides hygiene, quarantine references,
unused categories, and literal-token hygiene."""

from __future__ import annotations

from ..data.registry import Registry
from ..kernel.patterns import SKIPPABLE_SENSES
from .blast_radius import _rule_gates
from .overlap import Finding


def _all_tokens(rule) -> list:
    """Every match token, INCLUDING inside `opt:` groups.

    The recursion is the point, and it is FULLY recursive rather than one level
    deep: every dead literal found in this repo lived in an `opt:` group, where
    the no-op is invisible (the group simply never fires and the rule still
    matches without it) — and two of them are nested an `opt:` inside an `opt:`,
    which a single-level walk silently misses.
    """
    out: list = []

    def walk(tokens):
        for tok in tokens:
            out.append(tok)
            walk(getattr(tok, "opt", None) or ())

    for seq in rule.match.values():
        flat = seq if seq and not isinstance(seq[0], list) else [t for s in seq for t in s]
        walk(flat)
    return out


def _literal_checks(reg: Registry) -> list[Finding]:
    """Hygiene for `lit` tokens and `lit` ALTERNATIONS.

    Three findings, and the split matters:

    - `dead-literal`: EVERY option is a skippable-sense word (article/punct)
      and `consume_skipped` is not set, so the token can never match. The
      auto-skip loop walks straight past it. An `opt:` group containing one is
      a silent no-op; a REQUIRED one makes the whole rule unmatchable, which a
      dev gate reports as a clean 0 SOLVED.
    - `partially-dead-alternation`: SOME but not all options are dead. The
      token still fires, silently narrowed to its live options — a mistake the
      alternation primitive newly makes possible.
    - `alternation-should-be-category`: every option shares a root sense, so a
      CATEGORY would have fitted. Warning, never error: a category name is
      addressable by `span_blocks` and visible to blast-radius analysis, so it
      is the better tool when available — but there are legitimate exceptions
      (an alternation whose members need per-member payloads a category cannot
      carry). The check forces the author to state which case they are in.
    """
    findings: list[Finding] = []
    for rule in list(reg.rules) + list(reg.asks):
        for tok in _all_tokens(rule):
            opts = tok.lit_options
            if not opts or tok.consume_skipped:
                continue
            entries = {o: reg.lexicon.get(o) for o in opts}
            # a word the lexicon does not know is not dead — it simply has no
            # sense to be skippable, and packs may rely on unlexicalised forms
            dead = {
                o for o, e in entries.items()
                if e is not None and set(e.senses) <= SKIPPABLE_SENSES
            }
            if dead == set(opts):
                findings.append(
                    Finding("error", "dead-literal",
                            f"{rule.id} matches {list(opts)} but every option is a "
                            "SKIPPABLE sense (article/punct) — the skip loop walks "
                            "past it, so this token can never match. Add "
                            "`consume_skipped: true` or delete it")
                )
                continue
            if dead:
                findings.append(
                    Finding("warning", "partially-dead-alternation",
                            f"{rule.id} alternation {list(opts)} has skippable-only "
                            f"option(s) {sorted(dead)} that can never match — the "
                            "token is silently narrowed to the rest")
                )
            if len(opts) > 1:
                roots = []
                for o, e in entries.items():
                    roots.append(set(e.senses) if e is not None else set())
                shared = set.intersection(*roots) if roots else set()
                # articles/punct are pure skeleton — 'a'/'an' sharing the
                # `article` sense is allomorphy, not a class worth naming
                shared -= SKIPPABLE_SENSES
                if shared:
                    findings.append(
                        Finding("warning", "alternation-should-be-category",
                                f"{rule.id} alternation {list(opts)} shares the sense "
                                f"{sorted(shared)!r} — a CATEGORY would fit, and unlike "
                                "an alternation a category is refusable by `span_blocks` "
                                "and visible to blast-radius. Say why if not")
                    )
    return findings


def lint_checks(reg: Registry) -> list[Finding]:
    findings: list[Finding] = _literal_checks(reg)
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
