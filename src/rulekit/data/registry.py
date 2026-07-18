"""Compile loaded packs into the immutable Registry the kernel consumes.

All compile invariants live here and fail loudly:
- cross-pack duplicate lexicon entries (no silent shadowing)
- every category resolves through parents to exactly one root sense
- antonym pairs are symmetric with disjoint memberships
- every category member exists in the lexicon with the root sense
- context-synonym gates name real categories

The Registry is frozen after compile; every mapping is a plain dict built in
sorted order, so iteration is deterministic across processes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .packs import LoadedPack, PackError
from .schemas import (
    AskRule,
    LexiconEntry,
    PatternRule,
    RequirementShape,
    RoleObligation,
    SynthRule,
)

# Senses that can root a category hierarchy. 'conjunction' was added so a
# clause-marker category (packs/difg-mined/categories/clauses.yaml) can name
# specific subordinators like 'when' -- purely additive: 'conjunction' was
# already a known sense (and thus already a valid pattern-rule gate via the
# "a sense name is a valid degenerate category" rule below), so this only
# permits NEW categories to root here; it changes no existing category or
# word behavior. 'modal' was added the same way (mining candidate
# will-tense-asks) so a `future_modal` category can name the will/would
# subset of the 8 modal-sense words without disturbing the increment-14
# modal/auxiliary split. 'particle' was added the same way again (mining
# candidate conjoined-clause-holdings) so a `relational_marker` category
# can name 'than' -- the comparative/ratio clause-boundary word already
# sensed 'particle' in the core-english lexicon -- without adding a second
# sense to it (which would make every 'than'-bearing sentence in the
# corpus newly ambiguous under obligations.disambiguate()). 'adverb' was
# added the same way again (mining candidate particle-event-verbs) so a
# `verb_particle` category can name the closed set of directional
# particles (away/out/off/up) that fuse to a polarity-tagged event verb in
# condense.py -- purely additive: 'adverb' was already a known lexicon
# sense, so this only permits a NEW category to root here; it changes no
# existing word's sense or any other adverb-sensed word's behavior. 'time'
# was added the same way again (mining candidate age-equative-recut) so a
# `temporal_marker` category can name the closed set of deictic time words
# ('today', ...) that mark a clause's stated age as relative to a separate
# temporal anchor elsewhere in the document -- purely additive: 'time' was
# already a known lexicon sense (months, weekdays, 'now', 'today', ...), so
# this only permits a NEW category to root here; it changes no existing
# word's sense or any other time-sensed word's behavior. 'article' was added
# the same way again (mining candidate generic-unit-price-premises) so an
# `indefinite_article` category can name the 'a'/'an' subset of articles,
# distinct from 'the' -- purely additive: 'article' was already a known
# lexicon sense (a/an/the), so this only permits a NEW category to root
# here; it changes no existing word's sense or any other article-sensed
# word's behavior. 'pronoun' was added the same way again (mining candidate
# measure-noun-anaphor) so a `measure_anaphor` category can name the closed
# set of elided measure-noun anaphor heads ('ones', "12 yellow ONES") --
# purely additive: 'pronoun' was already a known lexicon sense ('ones' has
# carried it unaccompanied since it entered the lexicon), so this only
# permits a NEW category to root here; it changes no existing word's sense
# (no second sense is added to 'ones' or anything else) or any other
# pronoun-sensed word's behavior. Deliberately NOT rooted at 'noun': giving
# 'ones' a second, genuinely ambiguous 'noun' sense would make it always
# win obligations.disambiguate()'s coverage race (a pronoun's mandatory,
# never-locally-bindable 'refers' obligation is strictly worse-covering
# than a noun's none), silently reinterpreting EVERY 'ones' in the corpus
# -- including the unrelated relative-clause/definite forms ("the ones she
# didn't do") -- as a noun from round 0 on. Rooting at 'pronoun' instead
# keeps 'ones' single-sensed and behavior-identical everywhere except the
# one condense.py merge (adjective + measure_anaphor pronoun) that opts in
# by category membership, narrowly, exactly as the invariant demands.
# 'imperative' was added the same way again (mining candidate dimension-
# aggregate-asks) so a `compute_verb` category can name the closed set of
# imperative task-cue verbs ('compute'/'calculate'/'determine') that gate
# the new imperative-headed aggregate asks -- purely additive: 'imperative'
# was already a known lexicon sense (packs/core-english/lexicon/core.yaml's
# 'compute' entry, difg-mined's 'calculate'/'determine' entries, used today
# only by engine.py's ASK_CUE_SENSES to detect a task sentence with no
# question mark), so this only permits a NEW category to root here; it
# changes no existing word's sense or any other imperative-sensed word's
# behavior.
ROOT_SENSES = (
    "noun", "verb", "adjective", "quantifier", "preposition", "comparative",
    "negator", "conjunction", "modal", "particle", "adverb", "time",
    "article", "pronoun", "imperative",
)


class CompileError(Exception):
    pass


@dataclass(frozen=True)
class Registry:
    lexicon: Mapping[str, LexiconEntry]
    plural_to_singular: Mapping[str, str]
    singular_to_plural: Mapping[str, str]
    verb_lemmas: Mapping[str, str]
    numbers: Mapping[str, float]
    scales: Mapping[str, float]
    multipliers: Mapping[str, float]
    fractions: Mapping[str, float]
    operators: Mapping[str, str]
    currencies: Mapping[str, str]
    percents: Mapping[str, float]
    role_obligations: Mapping[str, RoleObligation]
    category_parents: Mapping[str, str]
    category_members: Mapping[str, tuple[str, ...]]  # direct members, sorted
    word_categories: Mapping[str, tuple[str, ...]]
    category_antonyms: Mapping[str, str]
    category_polarity: Mapping[str, int]
    interchangeable_categories: frozenset[str]
    superordinate_categories: frozenset[str]
    dimension_categories: frozenset[str]
    context_synonyms: Mapping[str, tuple[str, tuple[str, ...]]]  # concept -> (gate, forms)
    attrs: Mapping[str, Mapping[str, float]]
    part_counts: Mapping[str, str]
    conversions: Mapping[tuple[str, str], float]
    geometry_formulas: Mapping[tuple[str, str], str]  # (shape, quantity) -> expr
    quantity_formulas: Mapping[str, str]  # quantity -> expr over dimension names
    unit_dimension: Mapping[str, str]  # unit lemma -> dimension name
    calendar_span_days: Mapping[str, float]  # span unit lemma -> days per unit
    month_numbers: Mapping[str, int]  # month name/abbreviation -> 1..12
    atomic_masses: Mapping[str, float]  # element symbol -> g/mol
    affine_scales: Mapping[tuple[str, str], tuple[float, float]]  # (from,to) -> (offset,factor)
    quarantine: Mapping[str, str]  # word -> reason (never vocabulary)
    rules: tuple[PatternRule, ...]
    asks: tuple[AskRule, ...]
    synth_rules: tuple[SynthRule, ...]
    requirement_shapes: tuple[RequirementShape, ...]
    guard_config: Mapping[str, Mapping[str, object]]
    fingerprint: str
    pack_names: tuple[str, ...] = field(default=())

    # -- category helpers (the _cat machinery) -------------------------------

    def cat_ancestors(self, category: str) -> list[str]:
        out = [category]
        while out[-1] in self.category_parents:
            out.append(self.category_parents[out[-1]])
        return out

    def root_sense(self, category: str) -> str:
        chain = self.cat_ancestors(category)
        return chain[-1]

    def cat_descendants(self, category: str) -> list[str]:
        return sorted(
            c for c in set(self.category_parents) | set(self.category_members)
            if category in self.cat_ancestors(c)
        )

    def cat_members_deep(self, category: str) -> list[str]:
        """All member words of a category and its subcategories, sorted."""
        words: set[str] = set()
        for c in self.cat_descendants(category):
            words.update(self.category_members.get(c, ()))
        return sorted(words)

    def word_in_category(self, word: str, category: str) -> bool:
        """difg's _cat: word satisfies category directly, via a subcategory,
        via its singular form, or (for root senses) via its lexicon senses."""
        lemma = self.plural_to_singular.get(word, word)
        for w in (word, lemma):
            for tag in self.word_categories.get(w, ()):
                if category in self.cat_ancestors(tag):
                    return True
        # base categories derived from lexicon senses: any sense name acts as
        # a degenerate category (noun, verb, aggregate, particle, ...)
        entry = self.lexicon.get(word) or self.lexicon.get(lemma)
        if entry is not None and category in entry.senses:
            return True
        if category == "plural":
            return word in self.plural_to_singular
        return False


def _freeze(d: dict) -> Mapping:
    return MappingProxyType(dict(sorted(d.items())))


def compile_registry(packs: list[LoadedPack]) -> Registry:
    lexicon: dict[str, LexiconEntry] = {}
    lexicon_pack: dict[str, str] = {}
    for pack in packs:
        for word in sorted(pack.lexicon):
            if word in lexicon:
                raise CompileError(
                    f"lexicon entry {word!r} defined in both pack "
                    f"{lexicon_pack[word]!r} and {pack.name!r} — packs may not "
                    "silently shadow; remove one"
                )
            lexicon[word] = pack.lexicon[word]
            lexicon_pack[word] = pack.name

    plural_to_singular: dict[str, str] = {}
    verb_lemmas: dict[str, str] = {}
    for word, entry in sorted(lexicon.items()):
        for plural in entry.plurals():
            if plural in plural_to_singular and plural_to_singular[plural] != word:
                raise CompileError(f"plural {plural!r} claimed by two singulars")
            plural_to_singular[plural] = word
        if entry.verb and entry.verb.lemma:
            verb_lemmas[word] = entry.verb.lemma

    numbers: dict[str, float] = {}
    scales: dict[str, float] = {}
    multipliers: dict[str, float] = {}
    fractions: dict[str, float] = {}
    operators: dict[str, str] = {}
    currencies: dict[str, str] = {}
    percents: dict[str, float] = {}
    for pack in packs:
        for doc in pack.numbers:
            numbers.update(doc.numbers)
            scales.update(doc.scales)
            multipliers.update(doc.multipliers)
            fractions.update(doc.fractions)
            operators.update(doc.operators)
            currencies.update(doc.currencies)
            percents.update(doc.percents)

    role_obligations: dict[str, RoleObligation] = {}
    for pack in packs:
        for doc in pack.obligations:
            for role, ob in doc.roles.items():
                if role in role_obligations:
                    raise CompileError(f"role {role!r} obligations defined twice")
                role_obligations[role] = ob

    # -- categories ----------------------------------------------------------
    category_parents: dict[str, str] = {}
    category_antonyms: dict[str, str] = {}
    category_polarity: dict[str, int] = {}
    interchangeable_categories: set[str] = set()
    superordinate_categories: set[str] = set()
    dimension_categories: set[str] = set()
    category_members: dict[str, list[str]] = {}
    context_synonyms: dict[str, tuple[str, tuple[str, ...]]] = {}
    attrs: dict[str, dict[str, float]] = {}
    part_counts: dict[str, str] = {}
    for pack in packs:
        for doc in pack.categories:
            for name, cdef in doc.categories.items():
                if name in category_parents:
                    raise CompileError(f"category {name!r} defined twice")
                category_parents[name] = cdef.parent
                if cdef.antonym:
                    category_antonyms[name] = cdef.antonym
                if cdef.polarity is not None:
                    category_polarity[name] = cdef.polarity
                if cdef.interchangeable:
                    interchangeable_categories.add(name)
                if cdef.superordinate:
                    superordinate_categories.add(name)
                if cdef.dimension:
                    dimension_categories.add(name)
            for cat, words in doc.members.items():
                category_members.setdefault(cat, []).extend(words)
            for concept, syn in doc.context_synonyms.items():
                context_synonyms[concept] = (syn.gate, tuple(syn.forms))
            for word, table in doc.attrs.items():
                attrs.setdefault(word, {}).update(table)
            part_counts.update(doc.part_counts)

    # invariant: every category chain terminates in a root sense
    for cat in category_parents:
        chain, seen = [cat], {cat}
        while chain[-1] in category_parents:
            nxt = category_parents[chain[-1]]
            if nxt in seen:
                raise CompileError(f"category cycle at {cat!r}: {chain + [nxt]}")
            chain.append(nxt)
            seen.add(nxt)
        if chain[-1] not in ROOT_SENSES:
            raise CompileError(
                f"category {cat!r} does not resolve to a root sense "
                f"(chain ends at {chain[-1]!r}; roots are {ROOT_SENSES})"
            )

    # invariant: antonyms symmetric + memberships disjoint
    for a, b in sorted(category_antonyms.items()):
        if category_antonyms.get(b) not in (None, a):
            raise CompileError(f"antonym asymmetry: {a}->{b} but {b}->{category_antonyms.get(b)}")
        category_antonyms.setdefault(b, a)
        overlap = set(category_members.get(a, ())) & set(category_members.get(b, ()))
        if overlap:
            raise CompileError(f"antonym categories {a!r}/{b!r} share members {sorted(overlap)}")
        if a in category_polarity and b in category_polarity:
            if category_polarity[a] == category_polarity[b]:
                raise CompileError(f"antonym categories {a!r}/{b!r} share polarity")

    # invariant: members exist in the lexicon with the root sense
    word_categories: dict[str, list[str]] = {}
    for cat in sorted(category_members):
        if cat not in category_parents:
            raise CompileError(f"members listed for unregistered category {cat!r}")
        root = cat
        while root in category_parents:
            root = category_parents[root]
        for word in category_members[cat]:
            head = word.split()[0]  # multi-word members ("give away") check the head
            entry = lexicon.get(head) or lexicon.get(plural_to_singular.get(head, head))
            if entry is None:
                raise CompileError(
                    f"category {cat!r} member {word!r} is not in the lexicon"
                )
            if root not in entry.senses:
                raise CompileError(
                    f"category {cat!r} member {word!r} lacks the root sense {root!r}"
                )
            word_categories.setdefault(word, []).append(cat)

    # invariant: context-synonym gates are real categories
    for concept, (gate, _forms) in sorted(context_synonyms.items()):
        if gate not in category_parents:
            raise CompileError(f"context synonym {concept!r} gates on unknown category {gate!r}")

    # conversions: store both directions; conflicting factors error
    conversions: dict[tuple[str, str], float] = {}
    for pack in packs:
        for doc in pack.conversions:
            for c in doc.conversions:
                for pair, factor in (
                    ((c.from_, c.to), c.factor),
                    ((c.to, c.from_), 1.0 / c.factor),
                ):
                    if pair in conversions and abs(conversions[pair] - factor) > 1e-9:
                        raise CompileError(
                            f"conversion {pair} declared twice with different factors"
                        )
                    conversions[pair] = factor

    # geometry formulas: (shape, quantity) -> expression over named dimensions
    geometry_formulas: dict[tuple[str, str], str] = {}
    for pack in packs:
        for doc in pack.geometry:
            for f in doc.formulas:
                key = (f.shape, f.quantity)
                if key in geometry_formulas and geometry_formulas[key] != f.expr:
                    raise CompileError(
                        f"geometry formula {key} declared twice with different expressions"
                    )
                geometry_formulas[key] = f.expr

    # affine scale pairs, stored in BOTH directions like `conversions` above:
    # forward is (x + offset) * factor, so the inverse is x / factor - offset,
    # which is itself affine with offset' = -offset*factor and factor' = 1/factor.
    affine_scales: dict[tuple[str, str], tuple[float, float]] = {}
    for pack in packs:
        for doc in pack.affine:
            for sc in doc.scales:
                if sc.factor == 0:
                    raise CompileError(f"affine scale {sc.from_!r}->{sc.to!r} has a zero factor")
                fwd, rev = (sc.from_, sc.to), (sc.to, sc.from_)
                pair = (sc.offset, sc.factor)
                if fwd in affine_scales and affine_scales[fwd] != pair:
                    raise CompileError(
                        f"affine scale {sc.from_!r}->{sc.to!r} declared twice differently"
                    )
                affine_scales[fwd] = pair
                affine_scales[rev] = (-sc.offset * sc.factor, 1.0 / sc.factor)

    # atomic masses: element symbol -> g/mol. Same conflict discipline as the
    # tables above — a redeclaration with a different mass ERRORS.
    atomic_masses: dict[str, float] = {}
    for pack in packs:
        for doc in pack.elements:
            for sym, mass in doc.masses.items():
                if atomic_masses.get(sym, mass) != mass:
                    raise CompileError(
                        f"element {sym!r} declared twice with different masses"
                    )
                atomic_masses[sym] = mass

    # calendar spans: span unit lemma -> days per unit. Same conflict
    # discipline as the tables above -- a redeclaration with a different
    # divisor ERRORS rather than letting one silently win.
    calendar_span_days: dict[str, float] = {}
    month_numbers: dict[str, int] = {}
    for pack in packs:
        for doc in pack.calendar:
            for name, number in doc.months.items():
                if not 1 <= number <= 12:
                    raise CompileError(f"month {name!r} has out-of-range number {number}")
                if month_numbers.get(name, number) != number:
                    raise CompileError(f"month {name!r} declared twice with different numbers")
                month_numbers[name] = number
            for unit, days in doc.span_units.items():
                if unit in calendar_span_days and calendar_span_days[unit] != days:
                    raise CompileError(
                        f"calendar span unit {unit!r} declared twice with different divisors"
                    )
                calendar_span_days[unit] = days

    # quantity formulas: quantity -> expression over DIMENSION names, plus the
    # unit -> dimension map that binds them. Same conflict discipline as the
    # geometry table above: a redeclaration with a different expression ERRORS
    # rather than letting one silently win.
    quantity_formulas: dict[str, str] = {}
    unit_dimension: dict[str, str] = {}
    for pack in packs:
        for doc in pack.formulas:
            for f in doc.formulas:
                if f.quantity in quantity_formulas and quantity_formulas[f.quantity] != f.expr:
                    raise CompileError(
                        f"quantity formula {f.quantity!r} declared twice with different expressions"
                    )
                quantity_formulas[f.quantity] = f.expr
            for dim, units in doc.dimensions.items():
                for unit in units:
                    if unit in unit_dimension and unit_dimension[unit] != dim:
                        # One unit cannot denominate two dimensions: that would
                        # make binding order-dependent again, which is the exact
                        # thing the map exists to prevent.
                        raise CompileError(
                            f"unit {unit!r} mapped to two dimensions: "
                            f"{unit_dimension[unit]!r} and {dim!r}"
                        )
                    unit_dimension[unit] = dim

    # quarantine: documentation only, and it must not contradict the lexicon
    quarantine: dict[str, str] = {}
    for pack in packs:
        for doc in pack.quarantine:
            for word, q in doc.words.items():
                if word in lexicon:
                    raise CompileError(
                        f"quarantined word {word!r} is also in the lexicon — "
                        "re-admission must remove it from quarantine"
                    )
                quarantine[word] = q.reason

    rules: list[PatternRule] = []
    asks: list[AskRule] = []
    synth_rules: list[SynthRule] = []
    requirement_shapes: list[RequirementShape] = []
    guard_config: dict[str, dict[str, object]] = {}
    rule_ids: set[str] = set()
    for pack in packs:
        for doc in pack.rules:
            for rule in doc.rules:
                if rule.id in rule_ids:
                    raise CompileError(f"rule id {rule.id!r} defined twice")
                rule_ids.add(rule.id)
                rules.append(rule)
            asks.extend(doc.asks)
        for doc in pack.synth:
            synth_rules.extend(doc.rules)
        for doc in pack.requirements:
            requirement_shapes.extend(doc.shapes)
        for doc in pack.guards:
            for name, setting in doc.guards.items():
                guard_config[name] = {"enabled": setting.enabled, **(setting.model_extra or {})}

    # rules referencing unknown categories fail at compile; a sense name is a
    # valid degenerate category
    known_senses = {s for entry in lexicon.values() for s in entry.senses}
    valid_gates = set(category_parents) | set(ROOT_SENSES) | known_senses
    for rule in rules:
        for seq in rule.match.values():
            tokens = seq if seq and isinstance(seq[0], list) else [seq]
            for sub in tokens:
                for tok in sub:
                    cat = getattr(tok, "cat", None)
                    if cat and cat not in valid_gates:
                        raise CompileError(f"rule {rule.id!r} gates on unknown category {cat!r}")

    # A LITERAL THAT CAN NEVER MATCH is an authoring mistake, and it fails at
    # LOAD for the same reason AskRule._anchor_is_first does: the auto-skip
    # loop walks past a skippable-sense word, so the token matches nothing and
    # a dev gate reports a clean 0 SOLVED. Inside an `opt:` group that is a
    # silent no-op; on a required token it makes the whole rule unmatchable.
    # Twelve of these had accumulated before the check existed.
    #
    # This lives here rather than on the MatchToken schema because it needs
    # SENSES, which only the compiled lexicon has. The import is deferred: this
    # module is imported BY kernel.patterns, so a module-level import would be
    # circular. One definition, borrowed — not a second copy.
    from ..kernel.patterns import SKIPPABLE_SENSES

    def _every_token(rule):
        out: list = []

        def walk(tokens):
            for tok in tokens:
                out.append(tok)
                walk(getattr(tok, "opt", None) or ())

        for seq in rule.match.values():
            flat = seq if seq and not isinstance(seq[0], list) else [t for s in seq for t in s]
            walk(flat)
        return out

    for rule in list(rules) + list(asks):
        for tok in _every_token(rule):
            opts = tok.lit_options
            if not opts or tok.consume_skipped:
                continue
            entries = [lexicon.get(o) for o in opts]
            # a word the lexicon does not know has no sense to BE skippable
            if all(e is not None and set(e.senses) <= SKIPPABLE_SENSES for e in entries):
                raise CompileError(
                    f"{rule.id!r} matches {list(opts)} but every option is a SKIPPABLE "
                    f"sense — the skip loop walks past it, so this token can never "
                    f"match. Add `consume_skipped: true` or delete it"
                )

    fingerprint = hashlib.sha256(
        "|".join(p.fingerprint for p in packs).encode()
    ).hexdigest()

    return Registry(
        lexicon=_freeze(lexicon),
        plural_to_singular=_freeze(plural_to_singular),
        singular_to_plural=_freeze({v: k for k, v in plural_to_singular.items()}),
        verb_lemmas=_freeze(verb_lemmas),
        numbers=_freeze(numbers),
        scales=_freeze(scales),
        multipliers=_freeze(multipliers),
        fractions=_freeze(fractions),
        operators=_freeze(operators),
        currencies=_freeze(currencies),
        percents=_freeze(percents),
        role_obligations=_freeze(role_obligations),
        category_parents=_freeze(category_parents),
        category_members=_freeze({k: tuple(sorted(set(v))) for k, v in category_members.items()}),
        word_categories=_freeze({k: tuple(sorted(set(v))) for k, v in word_categories.items()}),
        category_antonyms=_freeze(category_antonyms),
        category_polarity=_freeze(category_polarity),
        interchangeable_categories=frozenset(interchangeable_categories),
        superordinate_categories=frozenset(superordinate_categories),
        dimension_categories=frozenset(dimension_categories),
        context_synonyms=_freeze(context_synonyms),
        attrs=_freeze({k: _freeze(v) for k, v in attrs.items()}),
        part_counts=_freeze(part_counts),
        conversions=_freeze(conversions),
        calendar_span_days=_freeze(calendar_span_days),
        month_numbers=_freeze(month_numbers),
        atomic_masses=_freeze(atomic_masses),
        affine_scales=_freeze(affine_scales),
        geometry_formulas=_freeze(geometry_formulas),
        quantity_formulas=_freeze(quantity_formulas),
        unit_dimension=_freeze(unit_dimension),
        quarantine=_freeze(quarantine),
        rules=tuple(sorted(rules, key=lambda r: r.id)),
        asks=tuple(sorted(asks, key=lambda a: a.id)),
        synth_rules=tuple(sorted(synth_rules, key=lambda s: s.id)),
        requirement_shapes=tuple(sorted(requirement_shapes, key=lambda s: s.id)),
        guard_config=_freeze(guard_config),
        fingerprint=fingerprint,
        pack_names=tuple(p.name for p in packs),
    )
