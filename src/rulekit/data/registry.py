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
    MatchToken,
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
# behavior. 'aggregate' follows the same rule: total and average markers
# already carry that single sense and are already valid direct pattern gates;
# rooting a category here only permits pack-owned semantic subsets such as
# sum markers without adding a second ambiguous sense to any word.
ROOT_SENSES = (
    "noun", "verb", "adjective", "quantifier", "preposition", "comparative",
    "negator", "conjunction", "modal", "particle", "adverb", "time",
    "article", "pronoun", "imperative", "aggregate",
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
    fraction_plurals: Mapping[str, str]
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
    coordinated_superordinate_categories: frozenset[str]
    dimension_categories: frozenset[str]
    attribute_compatibility: Mapping[str, tuple[str, ...]]
    measure_holder_compatibility: Mapping[str, tuple[str, ...]]
    subject_role_derivations: Mapping[tuple[str, str], str]
    adposition_roles: Mapping[
        str, tuple[tuple[str, str, str, bool], ...]
    ]
    temporal_offsets: Mapping[str, float]
    context_synonyms: Mapping[str, tuple[str, tuple[str, ...]]]  # concept -> (gate, forms)
    attrs: Mapping[str, Mapping[str, float]]
    part_counts: Mapping[str, str]
    conversions: Mapping[tuple[str, str], float]
    geometry_formulas: Mapping[tuple[str, str], str]  # (shape, quantity) -> expr
    quantity_formulas: Mapping[str, str]  # quantity -> expr over dimension names
    quantity_formula_scopes: Mapping[str, str]  # quantity -> question|document
    unit_dimension: Mapping[str, str]  # unit lemma -> dimension name
    calendar_span_days: Mapping[str, float]  # span unit lemma -> days per unit
    month_numbers: Mapping[str, int]  # month name/abbreviation -> 1..12
    atomic_masses: Mapping[str, float]  # element symbol -> g/mol
    # clitic -> expansion, LONGEST CLITIC FIRST (see compile_registry)
    contractions: tuple[tuple[str, str], ...]
    affine_scales: Mapping[tuple[str, str], tuple[float, float]]  # (from,to) -> (offset,factor)
    # curated reference facts: (entity fold, attribute, year|None) -> value.
    # Frozen like every other table — the dict-not-DuckDB tier (schemas.ReferenceDoc)
    reference: Mapping[tuple[str, str, int | None], float]
    # (entity fold, group attribute) -> folded group value ("continent" ->
    # "europe"). The sets aggregates run over; reference/db.py derives its
    # DuckDB tables from THIS and `reference` alone, so the resolver inherits
    # the frozen registry's determinism instead of owning any data
    reference_groups: Mapping[tuple[str, str], str]
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

    def category_terms_overlap(self, left: str, right: str) -> bool:
        """Whether two noun terms are identical or one subsumes the other.

        A pack may use a noun-category name as the lexical supertype itself:
        ``animal`` contains ``hamster``, ``fish`` contains ``goldfish``, and
        so on.  This helper reads only that declared category structure.  It
        does not infer disjointness between siblings or treat arbitrary shared
        memberships as identity evidence.
        """

        left = self.plural_to_singular.get(left, left)
        right = self.plural_to_singular.get(right, right)
        if left == right:
            return True

        categories = set(self.category_parents) | set(self.category_members)

        def contains(category_term: str, member_term: str) -> bool:
            return (
                category_term in categories
                and self.root_sense(category_term) == "noun"
                and self.word_in_category(member_term, category_term)
            )

        return contains(left, right) or contains(right, left)

    def attribute_compatibility_pairs(
        self, attribute: str, noun: str
    ) -> tuple[tuple[str, str], ...]:
        """Every declared category pair that licenses ATTRIBUTE for NOUN."""

        pairs: set[tuple[str, str]] = set()
        for direct in self.word_categories.get(attribute, ()):
            for attribute_category in self.cat_ancestors(direct):
                for noun_category in self.attribute_compatibility.get(
                    attribute_category, ()
                ):
                    if self.word_in_category(noun, noun_category):
                        pairs.add((attribute_category, noun_category))
        return tuple(sorted(pairs))

    def attribute_applies_to(self, attribute: str, noun: str) -> bool:
        return bool(self.attribute_compatibility_pairs(attribute, noun))

    def measure_holder_compatibility_pairs(
        self, measure: str, holder: str
    ) -> tuple[tuple[str, str], ...]:
        """Every declared measure-category/holder-category licence."""

        pairs: set[tuple[str, str]] = set()
        measure = self.plural_to_singular.get(measure, measure)
        holder = self.plural_to_singular.get(holder, holder)
        for direct in self.word_categories.get(measure, ()):
            for measure_category in self.cat_ancestors(direct):
                for holder_category in self.measure_holder_compatibility.get(
                    measure_category, ()
                ):
                    if self.word_in_category(holder, holder_category):
                        pairs.add((measure_category, holder_category))
        return tuple(sorted(pairs))

    def measure_applies_to_holder(self, measure: str, holder: str) -> bool:
        return bool(self.measure_holder_compatibility_pairs(measure, holder))


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
    fraction_plurals: dict[str, str] = {}
    operators: dict[str, str] = {}
    currencies: dict[str, str] = {}
    percents: dict[str, float] = {}
    for pack in packs:
        for doc in pack.numbers:
            numbers.update(doc.numbers)
            scales.update(doc.scales)
            multipliers.update(doc.multipliers)
            fractions.update(doc.fractions)
            for plural, singular in doc.fraction_plurals.items():
                prior = fraction_plurals.get(plural)
                if prior is not None and prior != singular:
                    raise CompileError(
                        f"fraction plural {plural!r} maps to both "
                        f"{prior!r} and {singular!r}"
                    )
                fraction_plurals[plural] = singular
            operators.update(doc.operators)
            currencies.update(doc.currencies)
            percents.update(doc.percents)
    for plural, singular in sorted(fraction_plurals.items()):
        if not plural or not singular or plural == singular:
            raise CompileError(
                f"fraction plural mapping {plural!r} -> {singular!r} "
                "must name two distinct non-empty surfaces"
            )
        if plural not in fractions:
            raise CompileError(
                f"fraction plural {plural!r} has no declared fraction value"
            )
        if singular not in fractions:
            raise CompileError(
                f"fraction plural {plural!r} names undeclared singular "
                f"{singular!r}"
            )
        if fractions[plural] != fractions[singular]:
            raise CompileError(
                f"fraction plural {plural!r} and singular {singular!r} "
                "must have the same declared value"
            )

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
    coordinated_superordinate_categories: set[str] = set()
    dimension_categories: set[str] = set()
    attribute_compatibility: dict[str, list[str]] = {}
    measure_holder_compatibility: dict[str, list[str]] = {}
    subject_role_derivations: dict[tuple[str, str], str] = {}
    subject_role_verbs: set[str] = set()
    adposition_roles: dict[
        str, tuple[tuple[str, str, str, bool], ...]
    ] = {}
    temporal_offsets: dict[str, float] = {}
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
                if cdef.coordinated_superordinate:
                    coordinated_superordinate_categories.add(name)
                if cdef.dimension:
                    dimension_categories.add(name)
            for cat, words in doc.members.items():
                category_members.setdefault(cat, []).extend(words)
            for attribute, nouns in doc.attribute_compatibility.items():
                attribute_compatibility.setdefault(attribute, []).extend(nouns)
            for measure, holders in doc.measure_holder_compatibility.items():
                measure_holder_compatibility.setdefault(measure, []).extend(
                    holders
                )
            for verb, derivation in doc.subject_role_derivations.items():
                if verb in subject_role_verbs:
                    raise CompileError(
                        f"subject-role derivation for {verb!r} defined twice"
                    )
                subject_role_verbs.add(verb)
                verb_entry = lexicon.get(verb)
                if verb_entry is None or "verb" not in verb_entry.senses:
                    raise CompileError(
                        f"subject-role derivation verb {verb!r} is not a "
                        "declared verb"
                    )
                if verb_lemmas.get(verb, verb) != verb:
                    raise CompileError(
                        f"subject-role derivation verb {verb!r} is not its "
                        "canonical lemma"
                    )
                role_entry = lexicon.get(derivation.role)
                if role_entry is None or "noun" not in role_entry.senses:
                    raise CompileError(
                        f"subject-role derivation role {derivation.role!r} "
                        "is not a declared noun"
                    )
                if plural_to_singular.get(
                    derivation.role, derivation.role
                ) != derivation.role:
                    raise CompileError(
                        f"subject-role derivation role {derivation.role!r} "
                        "must be singular"
                    )
                for prep in derivation.preserve_prepositions:
                    prep_entry = lexicon.get(prep)
                    if prep_entry is None or "preposition" not in prep_entry.senses:
                        raise CompileError(
                            f"subject-role derivation preposition {prep!r} "
                            "is not declared"
                        )
                    subject_role_derivations[(verb, prep)] = derivation.role
            for role, declared in doc.adposition_roles.items():
                if role in adposition_roles:
                    raise CompileError(f"adposition role {role!r} defined twice")
                definitions = (
                    declared if isinstance(declared, list) else [declared]
                )
                adposition_roles[role] = tuple(
                    (
                        definition.preposition_category,
                        definition.object_category,
                        definition.verb_category,
                        definition.allow_name_object,
                    )
                    for definition in definitions
                )
            for marker, offset in doc.temporal_offsets.items():
                if (
                    marker in temporal_offsets
                    and temporal_offsets[marker] != offset
                ):
                    raise CompileError(
                        f"temporal offset {marker!r} declared twice with "
                        "different values"
                    )
                temporal_offsets[marker] = offset
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

    for attribute, nouns in sorted(attribute_compatibility.items()):
        if attribute not in category_parents:
            raise CompileError(
                f"attribute compatibility names unknown category {attribute!r}"
            )
        root = attribute
        while root in category_parents:
            root = category_parents[root]
        if root not in {"adjective", "comparative", "preposition"}:
            raise CompileError(
                f"attribute compatibility key {attribute!r} is not "
                "descriptor-rooted (adjective/comparative/preposition)"
            )
        for noun in nouns:
            if noun not in category_parents:
                raise CompileError(
                    f"attribute compatibility {attribute!r} names unknown "
                    f"noun category {noun!r}"
                )
            root = noun
            while root in category_parents:
                root = category_parents[root]
            if root != "noun":
                raise CompileError(
                    f"attribute compatibility target {noun!r} is not noun-rooted"
                )

    for measure, holders in sorted(measure_holder_compatibility.items()):
        for category, role in ((measure, "measure"), *(
            (holder, "holder") for holder in holders
        )):
            if category not in category_parents:
                raise CompileError(
                    f"measure-holder compatibility names unknown {role} "
                    f"category {category!r}"
                )
            root = category
            while root in category_parents:
                root = category_parents[root]
            if root != "noun":
                raise CompileError(
                    f"measure-holder compatibility {role} category "
                    f"{category!r} is not noun-rooted"
                )

    def _category_root(category: str) -> str:
        root = category
        while root in category_parents:
            root = category_parents[root]
        return root

    for role, frames in sorted(adposition_roles.items()):
        for frame_no, (prep, obj, verb, _) in enumerate(frames, start=1):
            for category, expected, field_name in (
                (prep, "preposition", "preposition"),
                (obj, "noun", "object"),
                (verb, "verb", "verb"),
            ):
                if category not in category_parents and category not in ROOT_SENSES:
                    raise CompileError(
                        f"adposition role {role!r} frame {frame_no} names "
                        f"unknown {field_name} category {category!r}"
                    )
                root = _category_root(category)
                if root != expected:
                    raise CompileError(
                        f"adposition role {role!r} frame {frame_no} "
                        f"{field_name} category {category!r} is {root!r}-rooted, "
                        f"not {expected!r}-rooted"
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
            # A declared multiword lexeme ("next to") owns its sense as a
            # whole.  Legacy compositional members such as "give away" still
            # validate through their head when no whole-phrase entry exists.
            # This keeps phrase recognition declarative without requiring the
            # first token ("next") to acquire a misleading standalone
            # preposition sense.
            head = word.split()[0]
            entry = (
                lexicon.get(word)
                or lexicon.get(head)
                or lexicon.get(plural_to_singular.get(head, head))
            )
            if entry is None:
                raise CompileError(
                    f"category {cat!r} member {word!r} is not in the lexicon"
                )
            if root not in entry.senses:
                raise CompileError(
                    f"category {cat!r} member {word!r} lacks the root sense {root!r}"
                )
            word_categories.setdefault(word, []).append(cat)

    for marker in sorted(temporal_offsets):
        entry = lexicon.get(marker)
        if entry is None or "time" not in entry.senses:
            raise CompileError(
                f"temporal offset {marker!r} needs a time-sensed lexicon entry"
            )
        if "deictic_temporal_marker" not in word_categories.get(marker, ()):
            raise CompileError(
                f"temporal offset {marker!r} needs "
                "deictic_temporal_marker membership"
            )

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

    # reference tables: rows flattened to (entity fold, attribute, year|None)
    # -> float. Validation happens HERE, not in the schema, so an error names
    # the table, row and attribute. A `by: year` attribute stores one key per
    # year and NO year-less key — the lookup consumer declines a year-less ask
    # against a time series rather than silently choosing a year.
    reference: dict[tuple[str, str, int | None], float] = {}
    reference_groups: dict[tuple[str, str], str] = {}
    for pack in packs:
        for doc in pack.reference:
            for table in doc.tables:
                for row in table.rows:
                    if table.key not in row:
                        raise CompileError(
                            f"reference table {table.name!r}: a row lacks its "
                            f"key field {table.key!r}"
                        )
                    entity = str(row[table.key]).strip().lower()
                    for attr, value in sorted(row.items()):
                        if attr == table.key:
                            continue
                        spec = table.attributes.get(attr)
                        if spec is None:
                            raise CompileError(
                                f"reference table {table.name!r} row {entity!r}: "
                                f"undeclared attribute {attr!r}"
                            )
                        if spec.group:
                            gkey = (entity, attr)
                            gval = str(value).strip().lower()
                            if gkey in reference_groups and reference_groups[gkey] != gval:
                                raise CompileError(
                                    f"reference group {gkey} declared twice with "
                                    f"different values"
                                )
                            reference_groups[gkey] = gval
                            continue
                        if spec.by == "year":
                            if not isinstance(value, dict):
                                raise CompileError(
                                    f"reference {table.name!r}.{attr!r} is by-year "
                                    f"but row {entity!r} gives a bare value"
                                )
                            points = [(int(y), float(v)) for y, v in value.items()]
                        elif isinstance(value, dict):
                            raise CompileError(
                                f"reference {table.name!r}.{attr!r} is not by-year "
                                f"but row {entity!r} gives a mapping"
                            )
                        else:
                            points = [(None, float(value))]
                        for year, v in sorted(points, key=lambda p: (p[0] is not None, p[0])):
                            key = (entity, attr, year)
                            if key in reference and reference[key] != v:
                                raise CompileError(
                                    f"reference fact {key} declared twice with "
                                    f"different values"
                                )
                            reference[key] = v

    # contractions: clitic -> expansion. Stored as an ordered TUPLE sorted by
    # DESCENDING clitic length, because matching is longest-suffix-first: "n't"
    # and a hypothetical "'t" both match "doesn't" and only the longer is
    # right. Sorting here means a YAML reordering can never change a reading.
    contraction_map: dict[str, str] = {}
    for pack in packs:
        for doc in pack.contractions:
            for clitic, expansion in doc.expansions.items():
                if contraction_map.get(clitic, expansion) != expansion:
                    raise CompileError(
                        f"contraction {clitic!r} declared twice with different expansions"
                    )
                contraction_map[clitic] = expansion
    contractions = tuple(
        sorted(contraction_map.items(), key=lambda kv: (-len(kv[0]), kv[0]))
    )

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
    quantity_formula_scopes: dict[str, str] = {}
    unit_dimension: dict[str, str] = {}
    for pack in packs:
        for doc in pack.formulas:
            for f in doc.formulas:
                if f.quantity in quantity_formulas and (
                    quantity_formulas[f.quantity] != f.expr
                    or quantity_formula_scopes[f.quantity] != f.scope
                ):
                    raise CompileError(
                        f"quantity formula {f.quantity!r} declared twice with different definitions"
                    )
                quantity_formulas[f.quantity] = f.expr
                quantity_formula_scopes[f.quantity] = f.scope
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

    def _slot_root(token: MatchToken) -> str | None:
        if token.cat is not None:
            root = token.cat
            while root in category_parents:
                root = category_parents[root]
            return root
        if token.type in {
            "noun",
            "plural",
            "bare_plural",
            "common_noun",
            "counted",
            "possessed",
        }:
            return "noun"
        if token.type == "nonunit_multiplier":
            return "multiplier"
        return token.type

    def _category_chain(category: str) -> tuple[str, ...]:
        chain = [category]
        while chain[-1] in category_parents:
            chain.append(category_parents[chain[-1]])
        return tuple(chain)

    def _walk_match_tokens(tokens: list[MatchToken]):
        for token in tokens:
            yield token
            if token.opt is not None:
                yield from _walk_match_tokens(token.opt)

    for rule in rules:
        slots: dict[str, MatchToken] = {}
        for seq in rule.match.values():
            tokens = seq if seq and isinstance(seq[0], list) else [seq]
            for sub in tokens:
                for tok in _walk_match_tokens(sub):
                    if tok.slot is not None:
                        slots.setdefault(tok.slot, tok)
                    cat = getattr(tok, "cat", None)
                    if cat and cat not in valid_gates:
                        raise CompileError(f"rule {rule.id!r} gates on unknown category {cat!r}")
                    common_noun_cat = getattr(tok, "common_noun_cat", None)
                    if common_noun_cat:
                        if common_noun_cat not in valid_gates:
                            raise CompileError(
                                f"rule {rule.id!r} common-noun role gates on "
                                f"unknown category {common_noun_cat!r}"
                            )
                        root = common_noun_cat
                        while root in category_parents:
                            root = category_parents[root]
                        if root != "noun":
                            raise CompileError(
                                f"rule {rule.id!r} uses `common_noun_cat` "
                                f"with non-noun category {common_noun_cat!r}"
                            )
                    if cat and (
                        getattr(tok, "counted", False)
                        or getattr(tok, "possessed", False)
                    ):
                        root = cat
                        while root in category_parents:
                            root = category_parents[root]
                        if root != "noun":
                            qualifier = (
                                "counted"
                                if getattr(tok, "counted", False)
                                else "possessed"
                            )
                            raise CompileError(
                                f"rule {rule.id!r} uses `{qualifier}: true` on "
                                f"non-noun category {cat!r}"
                            )
                    if getattr(tok, "finite_form", False) and _slot_root(tok) != "verb":
                        raise CompileError(
                            f"rule {rule.id!r} uses `finite_form: true` on "
                            f"non-verb slot {tok.slot!r}"
                        )
        for predicate in rule.where:
            membership = predicate.same_category_membership
            if membership is not None:
                # Like the long-standing slot_not_category predicate, this
                # agreement may name a category supplied by an optional
                # extension pack. Without that pack every slot is simply
                # outside the category, so agreement remains a sound no-op.
                if membership.cat in valid_gates:
                    category_root = membership.cat
                    while category_root in category_parents:
                        category_root = category_parents[category_root]
                    if category_root != "noun":
                        raise CompileError(
                            f"rule {rule.id!r} category agreement uses "
                            f"non-noun category {membership.cat!r}"
                        )
                for slot_name in membership.slots:
                    token = slots.get(slot_name)
                    if token is None:
                        raise CompileError(
                            f"rule {rule.id!r} category agreement names "
                            f"unknown slot {slot_name!r}"
                        )
                    if _slot_root(token) not in {"noun", "entity"}:
                        raise CompileError(
                            f"rule {rule.id!r} category agreement slot "
                            f"{slot_name!r} is not noun/entity-rooted"
                        )
            compatibility = predicate.attribute_compatible
            if compatibility is not None:
                attribute = slots.get(compatibility.attribute)
                noun = slots.get(compatibility.noun)
                if attribute is None or noun is None:
                    missing = (
                        compatibility.attribute if attribute is None
                        else compatibility.noun
                    )
                    raise CompileError(
                        f"rule {rule.id!r} compatibility names unknown slot "
                        f"{missing!r}"
                    )
                if _slot_root(attribute) not in {
                    "adjective",
                    "comparative",
                    "preposition",
                }:
                    raise CompileError(
                        f"rule {rule.id!r} compatibility attribute slot "
                        f"{compatibility.attribute!r} is not "
                        "descriptor-rooted"
                    )
                if _slot_root(noun) != "noun":
                    raise CompileError(
                        f"rule {rule.id!r} compatibility noun slot "
                        f"{compatibility.noun!r} is not noun-rooted"
                    )
            conditional = predicate.bound_requires_category
            if conditional is not None:
                for slot_name in (conditional.bound, conditional.slot):
                    if slot_name not in slots:
                        raise CompileError(
                            f"rule {rule.id!r} conditional category names "
                            f"unknown slot {slot_name!r}"
                        )
                if conditional.cat not in valid_gates:
                    raise CompileError(
                        f"rule {rule.id!r} conditional category names "
                        f"unknown category {conditional.cat!r}"
                    )
            conditional_form = predicate.bound_requires_form
            if conditional_form is not None:
                for slot_name in (
                    conditional_form.bound,
                    conditional_form.slot,
                ):
                    if slot_name not in slots:
                        raise CompileError(
                            f"rule {rule.id!r} conditional form names "
                            f"unknown slot {slot_name!r}"
                        )
                if _slot_root(slots[conditional_form.slot]) != "verb":
                    raise CompileError(
                        f"rule {rule.id!r} conditional form target "
                        f"{conditional_form.slot!r} is not verb-rooted"
                    )
            polarity_compatibility = predicate.polarity_compatible
            if polarity_compatibility is not None:
                for slot_name, category in zip(
                    polarity_compatibility.slots,
                    polarity_compatibility.categories,
                    strict=True,
                ):
                    token = slots.get(slot_name)
                    if token is None:
                        raise CompileError(
                            f"rule {rule.id!r} polarity compatibility names "
                            f"unknown slot {slot_name!r}"
                        )
                    if category not in valid_gates:
                        raise CompileError(
                            f"rule {rule.id!r} polarity compatibility names "
                            f"unknown category {category!r}"
                        )
                    category_root = category
                    while category_root in category_parents:
                        category_root = category_parents[category_root]
                    if _slot_root(token) != category_root:
                        raise CompileError(
                            f"rule {rule.id!r} polarity compatibility pairs "
                            f"{slot_name!r} with incompatible category "
                            f"{category!r}"
                        )
                    scoped_polarities = {
                        polarity
                        for candidate, polarity in category_polarity.items()
                        if category
                        in _category_chain(candidate)
                    }
                    if not scoped_polarities:
                        raise CompileError(
                            f"rule {rule.id!r} polarity compatibility category "
                            f"{category!r} has no polarity-bearing descendants"
                        )
            proportional_delta = predicate.proportional_delta_compatible
            if proportional_delta is not None:
                fraction = slots.get(proportional_delta.fraction)
                direction = slots.get(proportional_delta.direction)
                if fraction is None or direction is None:
                    missing = (
                        proportional_delta.fraction
                        if fraction is None
                        else proportional_delta.direction
                    )
                    raise CompileError(
                        f"rule {rule.id!r} proportional delta names unknown "
                        f"slot {missing!r}"
                    )
                if fraction.type != "fraction":
                    raise CompileError(
                        f"rule {rule.id!r} proportional delta magnitude "
                        f"{proportional_delta.fraction!r} is not a fraction slot"
                    )
                category = proportional_delta.direction_cat
                if category not in valid_gates:
                    raise CompileError(
                        f"rule {rule.id!r} proportional delta names unknown "
                        f"direction category {category!r}"
                    )
                category_root = category
                while category_root in category_parents:
                    category_root = category_parents[category_root]
                if (
                    _slot_root(direction) != "comparative"
                    or category_root != "comparative"
                ):
                    raise CompileError(
                        f"rule {rule.id!r} proportional delta direction "
                        f"{proportional_delta.direction!r}/{category!r} is not "
                        "comparative-rooted"
                    )
                if not any(
                    category in _category_chain(candidate)
                    for candidate in category_polarity
                ):
                    raise CompileError(
                        f"rule {rule.id!r} proportional delta direction "
                        f"category {category!r} has no declared polarity"
                    )
            if predicate.same_presence is not None:
                if len(predicate.same_presence) < 2:
                    raise CompileError(
                        f"rule {rule.id!r} same_presence needs at least two slots"
                    )
                for slot_name in predicate.same_presence:
                    if slot_name not in slots:
                        raise CompileError(
                            f"rule {rule.id!r} same_presence names unknown "
                            f"slot {slot_name!r}"
                        )
            role_compatibility = predicate.verb_role_compatible
            if role_compatibility is not None:
                for slot_name in (
                    role_compatibility.verb,
                    *role_compatibility.roles,
                ):
                    if slot_name not in slots:
                        raise CompileError(
                            f"rule {rule.id!r} verb-role compatibility names "
                            f"unknown slot {slot_name!r}"
                        )
                if _slot_root(slots[role_compatibility.verb]) != "verb":
                    raise CompileError(
                        f"rule {rule.id!r} verb-role compatibility governor "
                        f"{role_compatibility.verb!r} is not verb-rooted"
                    )
                role_category = (
                    role_compatibility.role_cat
                    or role_compatibility.excluded_role_cat
                )
                assert role_category is not None
                for category, expected_root in (
                    (role_compatibility.verb_cat, "verb"),
                    (role_category, "noun"),
                ):
                    if category not in valid_gates:
                        raise CompileError(
                            f"rule {rule.id!r} verb-role compatibility names "
                            f"unknown category {category!r}"
                        )
                    root = category
                    while root in category_parents:
                        root = category_parents[root]
                    if root != expected_root:
                        raise CompileError(
                            f"rule {rule.id!r} verb-role compatibility "
                            f"category {category!r} is not "
                            f"{expected_root}-rooted"
                        )
            measure_compatibility = predicate.measure_holder_compatible
            if measure_compatibility is not None:
                for slot_name in (
                    measure_compatibility.measure,
                    *measure_compatibility.holders,
                ):
                    if slot_name not in slots:
                        raise CompileError(
                            f"rule {rule.id!r} measure-holder compatibility "
                            f"names unknown slot {slot_name!r}"
                        )
                if _slot_root(slots[measure_compatibility.measure]) != "noun":
                    raise CompileError(
                        f"rule {rule.id!r} measure-holder compatibility measure "
                        f"{measure_compatibility.measure!r} is not noun-rooted"
                    )
                for holder_name in measure_compatibility.holders:
                    holder = slots[holder_name]
                    if not (
                        holder.type in {"entity", "name", "proper_name"}
                        or _slot_root(holder) == "noun"
                    ):
                        raise CompileError(
                            f"rule {rule.id!r} measure-holder compatibility "
                            f"holder {holder_name!r} is not entity/noun-rooted"
                        )
            category_nonoverlap = predicate.category_nonoverlap
            if category_nonoverlap is not None:
                for slot_name in category_nonoverlap:
                    token = slots.get(slot_name)
                    if token is None:
                        raise CompileError(
                            f"rule {rule.id!r} category nonoverlap names "
                            f"unknown slot {slot_name!r}"
                        )
                    if not (
                        token.type in {"entity", "name", "proper_name"}
                        or _slot_root(token) == "noun"
                    ):
                        raise CompileError(
                            f"rule {rule.id!r} category nonoverlap slot "
                            f"{slot_name!r} is not entity/noun-rooted"
                        )
            owner_distinction = predicate.distinct_from_owner
            if owner_distinction is not None:
                for slot_name in (
                    owner_distinction.entity,
                    owner_distinction.possessed,
                ):
                    if slot_name not in slots:
                        raise CompileError(
                            f"rule {rule.id!r} entity/owner distinction names "
                            f"unknown slot {slot_name!r}"
                        )
                possessed_token = slots[owner_distinction.possessed]
                if not (
                    possessed_token.type == "possessed"
                    or possessed_token.possessed
                ):
                    raise CompileError(
                        f"rule {rule.id!r} entity/owner distinction target "
                        f"{owner_distinction.possessed!r} is not possessed"
                    )
            exclusion = predicate.slot_not_category
            if exclusion is not None:
                slot_name = exclusion.get("slot")
                if slot_name not in slots:
                    raise CompileError(
                        f"rule {rule.id!r} slot exclusion names unknown slot "
                        f"{slot_name!r}"
                    )
        for slot_name in rule.satisfies:
            token = slots.get(slot_name)
            if token is None:
                raise CompileError(
                    f"rule {rule.id!r} pattern satisfaction names unknown "
                    f"slot {slot_name!r}"
                )
            if token.span:
                raise CompileError(
                    f"rule {rule.id!r} pattern satisfaction slot "
                    f"{slot_name!r} is a span, not one obligation-bearing unit"
                )

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
        fraction_plurals=_freeze(fraction_plurals),
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
        coordinated_superordinate_categories=frozenset(
            coordinated_superordinate_categories
        ),
        dimension_categories=frozenset(dimension_categories),
        attribute_compatibility=_freeze(
            {
                key: tuple(sorted(set(values)))
                for key, values in attribute_compatibility.items()
            }
        ),
        measure_holder_compatibility=_freeze(
            {
                key: tuple(sorted(set(values)))
                for key, values in measure_holder_compatibility.items()
            }
        ),
        subject_role_derivations=_freeze(subject_role_derivations),
        adposition_roles=_freeze(adposition_roles),
        temporal_offsets=_freeze(temporal_offsets),
        context_synonyms=_freeze(context_synonyms),
        attrs=_freeze({k: _freeze(v) for k, v in attrs.items()}),
        part_counts=_freeze(part_counts),
        conversions=_freeze(conversions),
        calendar_span_days=_freeze(calendar_span_days),
        month_numbers=_freeze(month_numbers),
        atomic_masses=_freeze(atomic_masses),
        contractions=contractions,
        affine_scales=_freeze(affine_scales),
        reference=_freeze(reference),
        reference_groups=_freeze(reference_groups),
        geometry_formulas=_freeze(geometry_formulas),
        quantity_formulas=_freeze(quantity_formulas),
        quantity_formula_scopes=_freeze(quantity_formula_scopes),
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
