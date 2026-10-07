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
    "nonunit_multiplier": "twice",
    "name": "Alex",
    "noun": "apple",
    "plural": "apples",
    "counted": "3 apples",
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
    # noun-sensed AND in the plural map, like `plural` — the generic-subject
    # slot ("Mushrooms are fungi"). Without the entry it fell through to
    # "matches anything" and `{lit: all}` was reported as colliding with a
    # slot no quantifier can ever bind (the nonstate_verb blind spot, next
    # type over).
    "bare_plural": frozenset({"noun"}),
    "counted": frozenset({"noun"}),
    "verb": frozenset({"verb"}),
    # verb-sensed MINUS the `state` category — the subtraction is applied in
    # `_ok` below (a sense set alone cannot express it). Without this entry
    # the type fell through to None = "matches anything", and every copular
    # `{lit: is}` rule was reported as colliding with a `nonstate_verb` slot
    # it can never share a match with: patterns._slot_ok refuses 'is' there
    # ('is' is state-category on its fold; 'be' on its lemma).
    "nonstate_verb": frozenset({"verb"}),
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
    # A `lit` may be an ALTERNATION (schemas.MatchToken), so every test below
    # is "do ANY of the options intersect" rather than a scalar comparison.
    # Equality on `.lit` would read False for two overlapping alternations and
    # silently under-report real overlaps.
    # A bare reference cannot also carry a qualifier or possessive owner.
    # These gates constrain the condensed unit independently of its noun category.
    if ((a.bare and (b.qualified or b.possessed or b.qualifier_cat or b.type in {"qualified", "possessed"}))
            or (b.bare and (a.qualified or a.possessed or a.qualifier_cat or a.type in {"qualified", "possessed"}))):
        return False
    if a.number is not None and b.number is not None and a.number != b.number:
        return False
    if a.lit is not None and b.lit is not None:
        return bool(set(a.lit_options) & set(b.lit_options))
    if a.lit is not None or b.lit is not None:
        lits, slot = (a.lit_options, b) if a.lit is not None else (b.lit_options, a)
        if slot.counted or slot.possessed:
            # A category-qualified counted/possessed slot binds one condensed
            # multiword noun unit; a fixed one-word literal can never be it.
            return False
        if slot.type is not None:
            if slot.type == "word":
                return True
            if slot.type in {
                "number",
                "fraction",
                "multiplier",
                "nonunit_multiplier",
            }:
                return False  # a fixed literal is never a value slot
            senses = _TYPE_SENSES.get(slot.type)
            if senses is None:
                return True
            def _ok(lit: str) -> bool:
                entry = reg.lexicon.get(lit)
                hit = entry is not None and bool(set(entry.senses) & senses)
                if slot.type in ("plural", "bare_plural"):
                    hit = hit and lit in reg.plural_to_singular
                if slot.type == "nonstate_verb":
                    # mirror patterns._slot_ok exactly: the state category
                    # lists SURFACE forms, so BOTH the word and its verb
                    # lemma are checked — a surface-only test would wave
                    # 'is' (lemma 'be') through, the very blind spot the
                    # matcher's own comment records.
                    lemma = reg.verb_lemmas.get(lit, lit)
                    hit = hit and not (
                        reg.word_in_category(lit, "state")
                        or reg.word_in_category(lemma, "state")
                    )
                return hit
            return any(_ok(lit) for lit in lits)
        return any(reg.word_in_category(lit, slot.cat) for lit in lits)
    # slot vs slot
    ta = a.type or _type_of_cat(a.cat, reg)
    tb = b.type or _type_of_cat(b.cat, reg)
    base = {
        "plural": "noun",
        "nonunit_multiplier": "multiplier",
    }
    if a.cat and b.cat:
        if a.cat in reg.cat_ancestors(b.cat) or b.cat in reg.cat_ancestors(a.cat):
            return True
        return bool(set(reg.cat_members_deep(a.cat)) & set(reg.cat_members_deep(b.cat)))
    if ta == "word" or tb == "word":
        return True
    return base.get(ta, ta) == base.get(tb, tb)


def _witness_word(token: MatchToken, reg: Registry) -> str:
    if token.lit is not None:
        # the FIRST authored option — deterministic, so a witness string does
        # not depend on set ordering
        return token.lit_options[0]
    if token.cat is not None:
        members = reg.cat_members_deep(token.cat)
        if not members:
            return f"<{token.cat}>"
        member = members[0]
        if token.counted:
            return f"3 {reg.singular_to_plural.get(member, member)}"
        if token.possessed:
            if token.number == "plural":
                member = reg.singular_to_plural.get(member, member)
            return f"Alex's {member}"
        if token.number == "plural":
            return reg.singular_to_plural.get(member, member)
        return member
    return _TYPE_EXAMPLES.get(token.type, "<?>")


def _sentence_seq(rule: PatternRule) -> list[MatchToken] | None:
    seq = rule.match.get("sentence")
    if seq and not isinstance(seq[0], list):
        return seq
    return None


def _slot_excludes_token(
    rule: PatternRule,
    slot: MatchToken,
    other: MatchToken,
    reg: Registry,
) -> bool:
    """Whether one slot predicate makes the aligned token disjoint.

    ``slot_not_category`` is a semantic subtraction from an otherwise broad
    slot. Treating the slot as unconstrained invents overlap witnesses that the
    runtime matcher necessarily rejects.
    """

    if slot.slot is None:
        return False
    exclusions = {
        predicate.slot_not_category.get("cat")
        for predicate in rule.where
        if predicate.slot_not_category is not None
        and predicate.slot_not_category.get("slot") == slot.slot
    }
    exclusions.discard(None)
    for category in exclusions:
        assert category is not None
        if other.lit is not None and all(
            reg.word_in_category(literal, category)
            for literal in other.lit_options
        ):
            return True
        if other.cat is not None and (
            category == other.cat
            or category in reg.cat_ancestors(other.cat)
        ):
            return True
        other_root = (
            _type_of_cat(other.cat, reg)
            if other.cat is not None
            else other.type
        )
        if other_root == category:
            return True
    return False


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
        if _slot_excludes_token(a, ta, tb, reg) or _slot_excludes_token(
            b, tb, ta, reg
        ):
            return None
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
