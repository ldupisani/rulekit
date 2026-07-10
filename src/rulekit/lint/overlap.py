"""Static pattern-overlap analysis.

Two rules OVERLAP when some sentence can satisfy both of their match
sequences. Overlap + same emitted fact kind + no strict subsumption means a
potential runtime collision — reported at lint time with a synthesized
witness, before anything runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.registry import Registry
from ..data.schemas import MatchToken, PatternRule

# canonical example words for witness synthesis
_TYPE_EXAMPLES = {
    "number": "7",
    "fraction": "half",
    "multiplier": "twice",
    "name": "Alex",
    "noun": "apple",
    "plural": "apples",
    "verb": "has",
    "auxiliary": "does",
    "pronoun": "they",
    "word": "thing",
}

# which lexicon senses each slot type admits (for lit-vs-slot checks)
_TYPE_SENSES = {
    "name": frozenset(),  # structural, no lexicon sense
    "noun": frozenset({"noun"}),
    "plural": frozenset({"noun"}),
    "verb": frozenset({"verb"}),
    "auxiliary": frozenset({"auxiliary"}),
    "pronoun": frozenset({"pronoun"}),
    "word": None,  # anything
}


@dataclass
class Finding:
    level: str  # "error" | "warning" | "info"
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.code}: {self.message}"


def _required(tokens: list[MatchToken]) -> list[MatchToken]:
    return [t for t in tokens if t.opt is None]


def _type_of_cat(cat: str, reg: Registry) -> str:
    root = reg.root_sense(cat) if cat in reg.category_parents else cat
    return root


def _tokens_intersect(a: MatchToken, b: MatchToken, reg: Registry) -> bool:
    if a.lit is not None and b.lit is not None:
        return a.lit == b.lit
    if a.lit is not None or b.lit is not None:
        lit, slot = (a.lit, b) if a.lit is not None else (b.lit, a)
        if slot.type is not None:
            if slot.type == "word":
                return True
            senses = _TYPE_SENSES.get(slot.type)
            if senses is None:
                return True
            if slot.type in ("number", "fraction", "multiplier"):
                return False  # a fixed literal is never a value slot
            entry = reg.lexicon.get(lit)
            ok = entry is not None and bool(set(entry.senses) & senses)
            if slot.type == "plural":
                ok = ok and lit in reg.plural_to_singular
            return ok
        return reg.word_in_category(lit, slot.cat)
    # slot vs slot
    ta = a.type or _type_of_cat(a.cat, reg)
    tb = b.type or _type_of_cat(b.cat, reg)
    base = {"plural": "noun"}
    if a.cat and b.cat:
        if a.cat in reg.cat_ancestors(b.cat) or b.cat in reg.cat_ancestors(a.cat):
            return True
        return bool(set(reg.cat_members_deep(a.cat)) & set(reg.cat_members_deep(b.cat)))
    if ta == "word" or tb == "word":
        return True
    return base.get(ta, ta) == base.get(tb, tb)


def _witness_word(token: MatchToken, reg: Registry) -> str:
    if token.lit is not None:
        return token.lit
    if token.cat is not None:
        members = reg.cat_members_deep(token.cat)
        return members[0] if members else f"<{token.cat}>"
    return _TYPE_EXAMPLES.get(token.type, "<?>")


def _sentence_seq(rule: PatternRule) -> list[MatchToken] | None:
    seq = rule.match.get("sentence")
    if seq and not isinstance(seq[0], list):
        return seq
    return None


def rules_overlap(a: PatternRule, b: PatternRule, reg: Registry) -> str | None:
    """A witness sentence both rules can match, or None."""
    sa, sb = _sentence_seq(a), _sentence_seq(b)
    if sa is None or sb is None:
        return None
    ra, rb = _required(sa), _required(sb)
    if len(ra) != len(rb):
        return None  # conservative: only equal-arity shapes compared (v1)
    words = []
    for ta, tb in zip(ra, rb):
        if not _tokens_intersect(ta, tb, reg):
            return None
        # the witness uses the MORE specific side (lit > cat > type)
        pick = ta if (ta.lit is not None or (ta.cat and not tb.lit)) else tb
        words.append(_witness_word(pick, reg))
    return " ".join(words)


def _specificity_key(rule: PatternRule, reg: Registry) -> tuple[int, int, int]:
    from ..kernel.patterns import rule_specificity  # single source of truth

    return rule_specificity(rule, reg)


def lint_overlaps(reg: Registry) -> list[Finding]:
    findings: list[Finding] = []
    rules = [r for r in reg.rules if _sentence_seq(r) is not None]
    for i, a in enumerate(rules):
        for b in rules[i + 1 :]:
            if a.phase != b.phase:
                continue
            emit_kinds_a = {e.fact for e in a.emits}
            emit_kinds_b = {e.fact for e in b.emits}
            if not emit_kinds_a & emit_kinds_b:
                continue
            witness = rules_overlap(a, b, reg)
            if witness is None:
                continue
            ka, kb = _specificity_key(a, reg), _specificity_key(b, reg)
            overridden = (
                (a.overrides and a.overrides.get("rule") == b.id)
                or (b.overrides and b.overrides.get("rule") == a.id)
            )
            if ka == kb and not overridden:
                findings.append(
                    Finding(
                        "error", "overlap-tie",
                        f"{a.id} and {b.id} overlap with EQUAL specificity — "
                        f"neither can shadow; both would fire and may collide. "
                        f'Witness: "{witness}". Narrow a category gate or add overrides.',
                    )
                )
            else:
                narrow, broad = (a, b) if ka > kb else (b, a)
                findings.append(
                    Finding(
                        "warning", "overlap",
                        f"{narrow.id} (more specific) overlaps {broad.id}; the "
                        f"narrow rule shadows on shared matches. "
                        f'Witness: "{witness}".',
                    )
                )
    return findings
