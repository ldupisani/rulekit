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
import re
from math import isfinite
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .packs import LoadedPack, PackError
from .properties import DerivedAttribute, PropertyOrigin, PropertyError, compile_properties
from .schemas import (
    AskRule,
    LexiconEntry,
    MatchToken,
    PatternRule,
    RequirementShape,
    RoleObligation,
    SynthRule,
)

# A generic group-label slot may be narrowed by a lexical role contract.
# The same structural permission applies to premise and ask slots.
_SELECTIONAL_ROLE_SLOT_ROOTS = frozenset({
    "noun", "entity", "name", "proper_name", "word",
})

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
# 'auxiliary' follows the same rule for agreement-sensitive do-support
# subsets used by generated questions. It was already a known lexicon sense;
# this only permits a category to name the plural-compatible forms and adds
# no new ambiguity to any word. 'imperative' was added the same way again
# (mining candidate dimension-
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
    "interrogative",
    "operator",
    "noun", "verb", "adjective", "quantifier", "preposition", "comparative",
    "negator", "conjunction", "modal", "particle", "adverb", "time",
    "article", "pronoun", "auxiliary", "imperative", "aggregate", "possessive", "title",
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
    category_includes: Mapping[str, tuple[str, ...]]
    category_members: Mapping[str, tuple[str, ...]]  # explicit + included members
    word_categories: Mapping[str, tuple[str, ...]]
    category_antonyms: Mapping[str, str]
    category_polarity: Mapping[str, int]
    # Effective inherited role contracts by verb category. Each inner mapping
    # is semantic role -> noun category.
    selectional_roles: Mapping[str, Mapping[str, str]]
    # Optional inherited grammatical-number requirements for the same roles.
    selectional_role_numbers: Mapping[str, Mapping[str, str]]
    interchangeable_categories: frozenset[str]
    superordinate_categories: frozenset[str]
    coordinated_superordinate_categories: frozenset[str]
    dimension_categories: frozenset[str]
    attribute_compatibility: Mapping[str, tuple[str, ...]]
    modifier_host_compatibility: Mapping[str, tuple[str, ...]]
    adverb_verb_compatibility: Mapping[str, tuple[str, ...]]
    modifier_attachment_compatibility: tuple[tuple[str, str, str], ...]
    measure_holder_compatibility: Mapping[str, tuple[str, ...]]
    partitive_measure_compatibility: Mapping[str, tuple[str, ...]]
    subject_role_derivations: Mapping[tuple[str, str], str]
    adposition_roles: Mapping[
        str, tuple[tuple[str, str, str, bool], ...]
    ]
    temporal_offsets: Mapping[str, float]
    context_synonyms: Mapping[str, tuple[str, tuple[str, ...]]]  # concept -> (gate, forms)
    attrs: Mapping[str, Mapping[str, float]]
    part_counts: Mapping[str, str]
    conversions: Mapping[tuple[str, str], float]
    substance_conversions: Mapping[tuple[str, str, str], float]
    cadence_conversions: Mapping[tuple[str, str], float]
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
    category_disjoint: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    property_formulas: Mapping[str, Mapping[str, DerivedAttribute]] = field(default_factory=lambda: MappingProxyType({}))
    property_sources: Mapping[tuple[str, str], tuple[PropertyOrigin, ...]] = field(default_factory=lambda: MappingProxyType({}))
    parameter_bindings: Mapping[str, Mapping[str, str]] = field(default_factory=lambda: MappingProxyType({}))
    formula_units: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    formula_unit_categories: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    property_aliases: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    formula_constants: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))

    def attribute_value(self, term: str, attribute: str) -> float | None:
        return self.attrs.get(term.casefold(), {}).get(self.property_aliases.get(attribute, attribute))

    def derived_attribute(self, term: str, attribute: str) -> DerivedAttribute | None:
        return self.property_formulas.get(term.casefold(), {}).get(self.property_aliases.get(attribute, attribute))

    def attribute_sources(self, term: str, attribute: str) -> tuple[PropertyOrigin, ...]:
        return self.property_sources.get((term.casefold(), self.property_aliases.get(attribute, attribute)), ())

    def spatial_quantities(self, shape: str) -> set[str]:
        """Quantities matching the shape's declared spatial measure, not its boundary."""
        quantities = {quantity for term, quantity in self.geometry_formulas if term == shape}
        spatial = self.attribute_value(shape, "spatial_dimension")
        if spatial is None:
            return quantities
        # Untyped legacy formulas remain ambiguity candidates: a missing
        # dimension contract is not evidence that their basis is different.
        return {quantity for quantity in quantities
                if (definition := self.derived_attribute(shape, quantity)) is None
                or (len(definition.result_dimension) == 1
                and definition.result_dimension[0][1] == spatial
                and self.word_in_category(self.formula_units.get(definition.result_dimension[0][0], ""), "length_unit"))}

    def property_inputs(self, term: str, attribute: str) -> tuple[str, ...]:
        """Leaf roles after declared equalities, scalar defaults and dependencies."""
        table = self.property_formulas.get(term, {})
        scalars = self.attrs.get(term, {})
        bindings = self.parameter_bindings.get(term, {})
        leaves = set()
        def walk(key):
            while key in bindings:
                key = bindings[key]
            if key in scalars:
                return
            if key in table:
                for parameter in table[key].inputs:
                    walk(parameter)
            else:
                leaves.add(key)
        walk(self.property_aliases.get(attribute, attribute))
        return tuple(sorted(leaves))

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
        """Member surfaces, including declared noun plurals, sorted.

        Authored membership stays on the noun lemma. Enumeration must expose
        the same inflections accepted by ``word_in_category``; noun morphology
        must never expand a verb or other grammatical category.
        """
        words: set[str] = set()
        for c in self.cat_descendants(category):
            words.update(self.category_members.get(c, ()))
        if self.root_sense(category) == "noun":
            for word in tuple(words):
                entry = self.lexicon.get(word)
                if entry is not None:
                    words.update(entry.plurals())
        return sorted(words)

    def category_membership_path(self, word: str, category: str) -> tuple[str, ...]:
        """A deterministic lexical/ancestry/inclusion route for source links."""
        if not self.word_in_category(word, category):
            return ()
        lemma = (
            self.plural_to_singular.get(word, word)
            if self.root_sense(category) == "noun" else word
        )
        if lemma != word and not self.word_in_category(lemma, category):
            # A surface-only grammatical marker must link to its own authored
            # membership, rather than an unclassified singular.
            lemma = word
        for source in self.category_includes.get(category, ()):
            path = self.category_membership_path(lemma, source)
            if path:
                return (*path, category)
        for child, parent in sorted(self.category_parents.items()):
            if parent == category:
                path = self.category_membership_path(lemma, child)
                if path:
                    return (*path, category)
        return (lemma, category)

    def word_in_category(self, word: str, category: str) -> bool:
        """Membership through ancestry and sense-scoped noun morphology."""
        lemma = (
            self.plural_to_singular.get(word, word)
            if self.root_sense(category) == "noun" else word
        )
        forms = (word,) if lemma == word else (word, lemma)
        for w in forms:
            for tag in self.word_categories.get(w, ()):
                if category in self.cat_ancestors(tag):
                    return True
        # base categories derived from lexicon senses: any sense name acts as
        # a degenerate category (noun, verb, aggregate, particle, ...)
        for w in forms:
            entry = self.lexicon.get(w)
            if entry is not None and category in entry.senses:
                return True
        if category == "plural":
            return word in self.plural_to_singular
        return False

    def selectional_frames(
        self, word: str
    ) -> tuple[tuple[str, Mapping[str, str]], ...]:
        """Most-specific complete role frames applicable to one verb.

        A word may carry sibling verb categories for distinct senses. Those
        remain alternatives. An ancestor frame is suppressed when a more
        specific applicable category exists, preventing a broad parent from
        bypassing a child's narrowed role target.
        """

        word = word.casefold()
        lemma = self.verb_lemmas.get(word, word)
        applicable = {
            category
            for category in self.selectional_roles
            if self.word_in_category(word, category)
            or self.word_in_category(lemma, category)
        }
        most_specific = sorted(
            category
            for category in applicable
            if not any(
                category != other
                and category in self.cat_ancestors(other)[1:]
                for other in applicable
            )
        )
        return tuple(
            (category, self.selectional_roles[category])
            for category in most_specific
        )

    def selectional_role_number(
        self, category: str, role: str
    ) -> str | None:
        """Return one category frame's inherited role-number requirement."""

        return self.selectional_role_numbers.get(category, {}).get(role)

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
        return self.category_term_contains(
            left, right
        ) or self.category_term_contains(right, left)

    def category_term_contains(self, collection: str, member: str) -> bool:
        """Whether COLLECTION names a declared noun category containing MEMBER."""

        collection = self.plural_to_singular.get(collection, collection)
        member = self.plural_to_singular.get(member, member)
        return (
            (collection in self.category_parents or collection in self.category_members)
            and self.root_sense(collection) == "noun"
            and self.word_in_category(member, collection)
        )

    def category_terms_disjoint(self, left: str, right: str) -> bool:
        """Prove separation from declarations, never from absent membership."""
        left = self.plural_to_singular.get(left, left)
        right = self.plural_to_singular.get(right, right)

        def within(term: str, category: str) -> bool:
            if term in self.category_parents:
                return category in self.cat_ancestors(term)
            return self.word_in_category(term, category)

        return any(
            within(left, category) and any(within(right, other) for other in others)
            for category, others in self.category_disjoint.items()
        )

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

    def attribute_applies_to(self, attribute: str, noun: str, *, when_declared: bool = False) -> bool:
        if when_declared and not any(
            self.word_in_category(attribute, category)
            for category in self.attribute_compatibility
        ):
            return True
        return bool(self.attribute_compatibility_pairs(attribute, noun))

    def modifier_host_compatibility_pairs(
        self, modifier: str, host: str
    ) -> tuple[tuple[str, str], ...]:
        """Every declared preposition-category/host-category licence."""

        pairs: set[tuple[str, str]] = set()
        for direct in self.word_categories.get(modifier, ()):
            for modifier_category in self.cat_ancestors(direct):
                for host_category in self.modifier_host_compatibility.get(
                    modifier_category, ()
                ):
                    if self.word_in_category(host, host_category):
                        pairs.add((modifier_category, host_category))
        return tuple(sorted(pairs))

    def adverb_verb_compatibility_pairs(
        self, adverb: str, verb: str
    ) -> tuple[tuple[str, str], ...]:
        """Every declared adverb-category/verb-category licence."""

        pairs: set[tuple[str, str]] = set()
        for direct in self.word_categories.get(adverb, ()):
            for adverb_category in self.cat_ancestors(direct):
                for verb_category in self.adverb_verb_compatibility.get(
                    adverb_category, ()
                ):
                    if self.word_in_category(verb, verb_category):
                        pairs.add((adverb_category, verb_category))
        return tuple(sorted(pairs))

    def adverb_applies_to_verb(self, adverb: str, verb: str) -> bool:
        return bool(self.adverb_verb_compatibility_pairs(adverb, verb))

    def modifier_has_host_boundary(self, modifier: str) -> bool:
        return any(
            category in self.modifier_host_compatibility
            for direct in self.word_categories.get(modifier, ())
            for category in self.cat_ancestors(direct)
        )

    def modifier_applies_to_host(self, modifier: str, host: str) -> bool:
        return bool(self.modifier_host_compatibility_pairs(modifier, host))

    def adposition_object_frames(self, marker: str, verb: str) -> tuple[tuple[str, str, bool], ...]:
        """Role/object-category alternatives licensed by this marker and verb."""
        return tuple(
            (role, object_category, allow_name)
            for role, frames in self.adposition_roles.items()
            for prep, object_category, host, allow_name in frames
            if self.word_in_category(marker, prep) and self.word_in_category(verb, host)
        )

    def matching_adposition_roles(self, marker: str, object_: str, verb: str,
                                  *, name_object: bool = False) -> tuple[str, ...]:
        """Shared lexical PP licences for learning, matching and generation."""
        return tuple(dict.fromkeys(
            role for role, object_category, allow_name in self.adposition_object_frames(marker, verb)
            if (allow_name if name_object else self.word_in_category(object_, object_category))
        ))

    def modifier_frame_compatible(self, modifier: str, host: str, object_: str | None,
                                  *, host_type: str = "noun", name_object: bool = False,
                                  nominal_host: str | None = None) -> bool:
        if host_type == "verb":
            return object_ is not None and (
                bool(self.matching_adposition_roles(modifier, object_, host, name_object=name_object))
                or (nominal_host is not None
                    and self.modifier_has_host_boundary(modifier)
                    and self.modifier_frame_compatible(modifier, nominal_host, object_))
            )
        return ((not self.modifier_has_host_boundary(modifier)
                 or self.modifier_applies_to_host(modifier, host))
                and (object_ is None or self.modifier_attaches_to(modifier, object_, host)))

    def modifier_attachment_frames(
        self, modifier: str, object_: str
    ) -> tuple[tuple[str, str, str], ...]:
        """Frames activated by this exact modifier/object pair."""

        return tuple(
            frame
            for frame in self.modifier_attachment_compatibility
            if self.word_in_category(modifier, frame[0])
            and self.word_in_category(object_, frame[1])
        )

    def modifier_attaches_to(
        self, modifier: str, object_: str, host: str
    ) -> bool:
        frames = self.modifier_attachment_frames(modifier, object_)
        return not frames or any(
            self.word_in_category(host, host_category)
            for _, _, host_category in frames
        )

    def category_routes_overlap(self, left: str, right: str) -> bool:
        """Whether two declared categories are on one inheritance route."""

        return (
            left in self.cat_ancestors(right)
            or right in self.cat_ancestors(left)
        )

    def measure_holder_compatibility_pairs(
        self, measure: str, holder: str, attribute: str | None = None
    ) -> tuple[tuple[str, str], ...]:
        """Every declared measure-category/holder-category licence.

        An optional descriptor keeps a polysemous measure on the noun-category
        route selected by ``attribute_compatibility``.  The registry still
        owns every lexical fact; this merely composes two declarations.
        """

        pairs: set[tuple[str, str]] = set()
        measure = self.plural_to_singular.get(measure, measure)
        holder = self.plural_to_singular.get(holder, holder)
        route_categories = (
            {
                noun_category
                for _, noun_category in self.attribute_compatibility_pairs(
                    attribute, measure
                )
            }
            if attribute is not None
            else set()
        )
        if attribute is not None and not route_categories:
            return ()
        for direct in self.word_categories.get(measure, ()):
            for measure_category in self.cat_ancestors(direct):
                if route_categories and not any(
                    self.category_routes_overlap(
                        measure_category, route_category
                    )
                    for route_category in route_categories
                ):
                    continue
                for holder_category in self.measure_holder_compatibility.get(
                    measure_category, ()
                ):
                    if self.word_in_category(holder, holder_category):
                        pairs.add((measure_category, holder_category))
        return tuple(sorted(pairs))

    def measure_has_holder_boundary(self, measure: str) -> bool:
        """Whether MEASURE activates any declared holder relationship."""

        measure = self.plural_to_singular.get(measure, measure)
        return any(
            measure_category in self.measure_holder_compatibility
            for direct in self.word_categories.get(measure, ())
            for measure_category in self.cat_ancestors(direct)
        )

    def measure_applies_to_holder(
        self, measure: str, holder: str, attribute: str | None = None
    ) -> bool:
        return bool(
            self.measure_holder_compatibility_pairs(
                measure, holder, attribute
            )
        )

    def partitive_compatibility_pairs(
        self, measure: str, substance: str
    ) -> tuple[tuple[str, str], ...]:
        """Every declared measure-category/substance-category licence."""

        pairs: set[tuple[str, str]] = set()
        measure = self.plural_to_singular.get(measure, measure)
        substance = self.plural_to_singular.get(substance, substance)
        for direct in self.word_categories.get(measure, ()):
            for measure_category in self.cat_ancestors(direct):
                for substance_category in self.partitive_measure_compatibility.get(
                    measure_category, ()
                ):
                    if self.word_in_category(substance, substance_category):
                        pairs.add((measure_category, substance_category))
        return tuple(sorted(pairs))

    def partitive_applies_to(self, measure: str, substance: str) -> bool:
        return bool(self.partitive_compatibility_pairs(measure, substance))


def _freeze(d: dict) -> Mapping:
    return MappingProxyType(dict(sorted(d.items())))


def _validate_text_prefix_split(predicate, slots, rule_id: str) -> None:
    spec = predicate.text_prefix_split
    if spec is None:
        return
    for slot in (spec.text, spec.prefix):
        if slot not in slots:
            raise CompileError(f"rule {rule_id!r} text split names unknown slot {slot!r}")
    if spec.text == spec.prefix:
        raise CompileError(f"rule {rule_id!r} text split needs an independent prefix slot")
    if spec.prefix_attr == "owner" and slots[spec.prefix].span:
        raise CompileError(f"rule {rule_id!r} text split owner cannot come from a span")


def compile_registry(packs: list[LoadedPack]) -> Registry:
    lexicon: dict[str, LexiconEntry] = {}
    lexicon_pack: dict[str, str] = {}
    for pack in packs:
        for word in sorted(pack.lexicon):
            if pack.lexicon[word].lexical_phrase and (
                (len(word.split()) < 2 and "'" not in word) or word != " ".join(word.split())
            ):
                raise CompileError("a lexical phrase needs a normalized multiword or apostrophized key")
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
    category_includes: dict[str, tuple[str, ...]] = {}
    declared_disjoint: dict[str, tuple[str, ...]] = {}
    category_antonyms: dict[str, str] = {}
    category_polarity: dict[str, int] = {}
    declared_selectional_roles: dict[str, dict[str, str]] = {}
    declared_selectional_role_numbers: dict[str, dict[str, str]] = {}
    interchangeable_categories: set[str] = set()
    superordinate_categories: set[str] = set()
    coordinated_superordinate_categories: set[str] = set()
    dimension_categories: set[str] = set()
    attribute_compatibility: dict[str, list[str]] = {}
    modifier_host_compatibility: dict[str, list[str]] = {}
    adverb_verb_compatibility: dict[str, list[str]] = {}
    modifier_attachment_compatibility: list[tuple[str, str, str]] = []
    measure_holder_compatibility: dict[str, list[str]] = {}
    partitive_measure_compatibility: dict[str, list[str]] = {}
    subject_role_derivations: dict[tuple[str, str], str] = {}
    subject_role_verbs: set[str] = set()
    adposition_roles: dict[
        str, tuple[tuple[str, str, str, bool], ...]
    ] = {}
    temporal_offsets: dict[str, float] = {}
    category_members: dict[str, list[str]] = {}
    context_synonyms: dict[str, tuple[str, tuple[str, ...]]] = {}
    attrs: dict[str, dict[str, float]] = {}
    category_defs = {}
    word_formulas = {}
    word_bindings = {}
    property_word_origins = {}
    formula_units = {}
    formula_unit_categories = {}
    property_aliases = {}
    formula_constants = {}
    part_counts: dict[str, str] = {}
    for pack in packs:
        for doc in pack.categories:
            for name, cdef in doc.categories.items():
                if name in category_parents:
                    raise CompileError(f"category {name!r} defined twice")
                category_parents[name] = cdef.parent
                category_defs[name] = (cdef, pack.name)
                if cdef.includes:
                    category_includes[name] = tuple(sorted(set(cdef.includes)))
                if cdef.disjoint_with:
                    declared_disjoint[name] = tuple(sorted(set(cdef.disjoint_with)))
                if cdef.antonym:
                    category_antonyms[name] = cdef.antonym
                if cdef.polarity is not None:
                    category_polarity[name] = cdef.polarity
                if cdef.selectional_roles:
                    declared_selectional_roles[name] = dict(
                        cdef.selectional_roles
                    )
                if cdef.selectional_role_numbers:
                    declared_selectional_role_numbers[name] = dict(
                        cdef.selectional_role_numbers
                    )
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
            for modifier, hosts in doc.modifier_host_compatibility.items():
                modifier_host_compatibility.setdefault(modifier, []).extend(hosts)
            for adverb, verbs in doc.adverb_verb_compatibility.items():
                adverb_verb_compatibility.setdefault(adverb, []).extend(verbs)
            modifier_attachment_compatibility.extend(
                (
                    frame.preposition_category,
                    frame.object_category,
                    frame.host_category,
                )
                for frame in doc.modifier_attachment_compatibility
            )
            for measure, holders in doc.measure_holder_compatibility.items():
                measure_holder_compatibility.setdefault(measure, []).extend(
                    holders
                )
            for measure, substances in doc.partitive_measure_compatibility.items():
                partitive_measure_compatibility.setdefault(measure, []).extend(
                    substances
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
                for key, value in table.items():
                    prior = attrs.setdefault(word, {}).get(key)
                    if prior is not None and prior != value:
                        raise CompileError(f"word attribute {(word, key)!r} has conflicting values")
                    attrs[word][key] = value
                    property_word_origins[(word, key)] = pack.name
            for word, table in doc.formulas.items():
                for key, value in table.items():
                    prior = word_formulas.setdefault(word, {}).get(key)
                    if prior is not None and prior != value:
                        raise CompileError(f"word formula {(word, key)!r} has conflicting definitions")
                    word_formulas[word][key] = value
                    property_word_origins[(word, key)] = pack.name
            for word, table in doc.parameter_bindings.items():
                for key, value in table.items():
                    prior = word_bindings.setdefault(word, {}).get(key)
                    if prior is not None and prior != value:
                        raise CompileError(f"word binding {(word, key)!r} has conflicting definitions")
                    word_bindings[word][key] = value
                    property_word_origins[(word, "binding:" + key)] = pack.name
            for basis, contract in doc.formula_units.items():
                unit = contract if isinstance(contract, str) else contract.unit
                category = None if isinstance(contract, str) else contract.category
                if basis in formula_units and (
                    formula_units[basis] != unit or formula_unit_categories.get(basis) != category
                ):
                    raise CompileError(f"formula dimension {basis!r} has conflicting unit contracts")
                formula_units[basis] = unit
                if category is not None:
                    formula_unit_categories[basis] = category
            for surface, key in doc.property_aliases.items():
                if surface in property_aliases and property_aliases[surface] != key:
                    raise CompileError(f"property alias {surface!r} has conflicting targets")
                property_aliases[surface] = key
            for name, value in doc.formula_constants.items():
                if name in formula_constants and formula_constants[name] != value:
                    raise CompileError(f"formula constant {name!r} has conflicting values")
                if not name.isidentifier() or not isfinite(value):
                    raise CompileError("formula constants need identifier names and finite values")
                formula_constants[name] = value
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

    # Selectional roles belong only to verb categories and always target noun
    # categories. Resolve inheritance once at compile time. A child contract
    # may narrow an inherited role but may never replace it with an unrelated
    # or broader target: doing so would make the category hierarchy lie about
    # the lexical boundary it is meant to carry.
    selectional_roles: dict[str, dict[str, str]] = {}
    selectional_role_numbers: dict[str, dict[str, str]] = {}
    selectional_contracts: dict[
        str, tuple[dict[str, str], dict[str, str]]
    ] = {}

    def _category_root(category: str) -> str:
        root = category
        while root in category_parents:
            root = category_parents[root]
        return root

    # Resolve nominal role unions after ALL packs have contributed members.
    # Inclusion is membership only: it must not import verb frames, polarity,
    # coreference eligibility, or superclass aggregation flags in reverse.
    children: dict[str, list[str]] = {}
    for child, parent in category_parents.items():
        children.setdefault(parent, []).append(child)
    for target, sources in category_includes.items():
        if _category_root(target) != "noun":
            raise CompileError(f"category includes requires a noun-rooted target: {target!r}")
        for source in sources:
            if source not in category_parents:
                raise CompileError(f"category {target!r} includes unknown category {source!r}")
            if _category_root(source) != "noun":
                raise CompileError(f"category {target!r} includes non-noun category {source!r}")
    explicit_members = {c: set(words) for c, words in category_members.items()}
    deep_members: dict[str, set[str]] = {}
    resolving: set[str] = set()

    def _included_members(category: str) -> set[str]:
        if category in resolving:
            raise CompileError(f"category inclusion cycle at {category!r}")
        if category in deep_members:
            return deep_members[category]
        resolving.add(category)
        included: set[str] = set()
        for source in category_includes.get(category, ()):
            included.update(_included_members(source))
        if included:
            category_members[category] = sorted(explicit_members.get(category, set()) | included)
        result = explicit_members.get(category, set()) | included
        for child in children.get(category, ()):
            result = result | _included_members(child)
        resolving.remove(category)
        deep_members[category] = result
        return result

    for category in sorted(category_parents):
        _included_members(category)

    # A disjoint family excludes its descendants and included families too.
    # Validate both structural overlap and lexical overlap after extensions
    # have contributed their members, including currently empty subclasses.
    regions: dict[str, frozenset[str]] = {}

    def _category_region(category: str) -> frozenset[str]:
        if category not in regions:
            descendants = {category}
            for child in (*children.get(category, ()), *category_includes.get(category, ())):
                descendants.update(_category_region(child))
            regions[category] = frozenset(descendants)
        return regions[category]

    category_disjoint: dict[str, set[str]] = {}
    for left, others in sorted(declared_disjoint.items()):
        for right in others:
            if right not in category_parents:
                raise CompileError(f"category {left!r} declares disjointness with unknown category {right!r}")
            if _category_root(left) != "noun" or _category_root(right) != "noun":
                raise CompileError("category disjointness requires noun-rooted categories")
            left_region, right_region = _category_region(left), _category_region(right)
            if left_region & right_region:
                raise CompileError(f"disjoint categories {left!r}/{right!r} have overlapping families")
            left_members = {plural_to_singular.get(word, word) for word in deep_members[left]}
            right_members = {plural_to_singular.get(word, word) for word in deep_members[right]}
            overlap = (left_members & right_members
                       | left_region & right_members
                       | right_region & left_members)
            if overlap:
                raise CompileError(f"disjoint categories {left!r}/{right!r} share members {sorted(overlap)}")
            for a in left_region:
                for b in right_region:
                    category_disjoint.setdefault(a, set()).add(b)
                    category_disjoint.setdefault(b, set()).add(a)

    def _effective_selectional_contract(
        category: str,
    ) -> tuple[dict[str, str], dict[str, str]]:
        cached = selectional_contracts.get(category)
        if cached is not None:
            return cached
        parent = category_parents[category]
        inherited_roles, inherited_numbers = (
            _effective_selectional_contract(parent)
            if parent in category_parents
            else ({}, {})
        )
        effective = dict(inherited_roles)
        effective_numbers = dict(inherited_numbers)
        for role, target in declared_selectional_roles.get(category, {}).items():
            inherited = effective.get(role)
            target_chain = [target]
            while target_chain[-1] in category_parents:
                target_chain.append(category_parents[target_chain[-1]])
            if inherited is not None and inherited not in target_chain:
                raise CompileError(
                    f"category {category!r} selectional role {role!r} "
                    f"target {target!r} does not narrow inherited "
                    f"category {inherited!r}"
                )
            effective[role] = target
        for role, number in declared_selectional_role_numbers.get(
            category, {}
        ).items():
            if role not in effective:
                raise CompileError(
                    f"category {category!r} selectional role number names "
                    f"undeclared role {role!r}"
                )
            inherited = effective_numbers.get(role)
            if inherited is not None and inherited != number:
                raise CompileError(
                    f"category {category!r} selectional role {role!r} "
                    f"number {number!r} conflicts with inherited "
                    f"number {inherited!r}"
                )
            effective_numbers[role] = number
        if effective:
            selectional_roles[category] = effective
        if effective_numbers:
            selectional_role_numbers[category] = effective_numbers
        contract = (effective, effective_numbers)
        selectional_contracts[category] = contract
        return contract

    for category in sorted(
        set(declared_selectional_roles)
        | set(declared_selectional_role_numbers)
    ):
        if _category_root(category) != "verb":
            raise CompileError(
                f"category {category!r} declares a selectional contract but "
                "is not verb-rooted"
            )
        roles = declared_selectional_roles.get(category, {})
        for role, target in sorted(roles.items()):
            if target not in category_parents and target != "noun":
                raise CompileError(
                    f"category {category!r} selectional role {role!r} names "
                    f"unknown noun category {target!r}"
                )
            if _category_root(target) != "noun":
                raise CompileError(
                    f"category {category!r} selectional role {role!r} "
                    f"target {target!r} is not noun-rooted"
                )

    for category in sorted(category_parents):
        if _category_root(category) == "verb":
            _effective_selectional_contract(category)
    selectional_role_names = frozenset(
        role for frame in selectional_roles.values() for role in frame
    )

    for attribute, nouns in sorted(attribute_compatibility.items()):
        if attribute not in category_parents:
            raise CompileError(
                f"attribute compatibility names unknown category {attribute!r}"
            )
        root = attribute
        while root in category_parents:
            root = category_parents[root]
        if root not in {"adjective", "comparative", "preposition", "noun"}:
            raise CompileError(
                f"attribute compatibility key {attribute!r} is not "
                "descriptor-rooted (adjective/comparative/preposition/noun)"
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

    for measure, substances in sorted(partitive_measure_compatibility.items()):
        for category, role in ((measure, "measure"), *(
            (substance, "substance") for substance in substances
        )):
            if category not in category_parents:
                raise CompileError(
                    f"partitive compatibility names unknown {role} category "
                    f"{category!r}"
                )
            root = category
            while root in category_parents:
                root = category_parents[root]
            if root != "noun":
                raise CompileError(
                    f"partitive compatibility {role} category "
                    f"{category!r} is not noun-rooted"
                )

    for modifier, hosts in sorted(modifier_host_compatibility.items()):
        if modifier not in category_parents:
            raise CompileError(
                f"modifier-host compatibility names unknown category {modifier!r}"
            )
        root = modifier
        while root in category_parents:
            root = category_parents[root]
        if root != "preposition":
            raise CompileError(
                f"modifier-host compatibility key {modifier!r} is not "
                "preposition-rooted"
            )
        for host in hosts:
            if host not in category_parents:
                raise CompileError(
                    f"modifier-host compatibility {modifier!r} names unknown "
                    f"host category {host!r}"
                )
            root = host
            while root in category_parents:
                root = category_parents[root]
            if root != "noun":
                raise CompileError(
                    f"modifier-host compatibility target {host!r} is not "
                    "noun-rooted"
                )

    for adverb, verbs in sorted(adverb_verb_compatibility.items()):
        if adverb not in category_parents:
            raise CompileError(
                f"adverb-verb compatibility names unknown category {adverb!r}"
            )
        if _category_root(adverb) != "adverb":
            raise CompileError(
                f"adverb-verb compatibility key {adverb!r} is not "
                "adverb-rooted"
            )
        for verb in verbs:
            if verb not in category_parents:
                raise CompileError(
                    f"adverb-verb compatibility {adverb!r} names unknown "
                    f"verb category {verb!r}"
                )
            if _category_root(verb) != "verb":
                raise CompileError(
                    f"adverb-verb compatibility target {verb!r} is not "
                    "verb-rooted"
                )

    for preposition, object_, host in modifier_attachment_compatibility:
        for category, role, expected_root in (
            (preposition, "preposition", "preposition"),
            (object_, "object", "noun"),
            (host, "host", "noun"),
        ):
            if category not in category_parents:
                raise CompileError(
                    "modifier attachment compatibility names unknown "
                    f"{role} category {category!r}"
                )
            root = category
            while root in category_parents:
                root = category_parents[root]
            if root != expected_root:
                raise CompileError(
                    f"modifier attachment {role} category {category!r} is "
                    f"not {expected_root}-rooted"
                )

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

    try:
        attrs, property_formulas, property_sources, parameter_bindings = compile_properties(
            lexicon=lexicon, plurals=plural_to_singular, parents=category_parents,
            word_categories=word_categories, category_defs=category_defs,
            word_attrs=attrs, word_formulas=word_formulas, word_bindings=word_bindings,
            word_origins=property_word_origins, constants=formula_constants)
    except PropertyError as exc:
        raise CompileError(str(exc)) from exc
    for basis, unit in formula_units.items():
        if not basis.isidentifier() or unit not in lexicon or "noun" not in lexicon[unit].senses:
            raise CompileError(f"formula dimension {basis!r} needs a declared canonical noun unit")
        category = formula_unit_categories.get(basis)
        if category is not None and (
            category not in category_parents or _category_root(category) != "noun"
            or not any(tag in _category_region(category) for tag in word_categories.get(unit, ()))
        ):
            raise CompileError(f"formula dimension {basis!r} needs a noun unit family containing {unit!r}")
    for alias in property_aliases:
        chain = set()
        target = alias
        while target in property_aliases:
            if target in chain:
                raise CompileError("property alias cycle")
            chain.add(target)
            target = property_aliases[target]
        property_aliases[alias] = target

    # invariant: context-synonym gates are real categories
    for concept, (gate, _forms) in sorted(context_synonyms.items()):
        if gate not in category_parents:
            raise CompileError(f"context synonym {concept!r} gates on unknown category {gate!r}")

    # conversions: store both directions; conflicting factors error. Cadence-
    # scoped pairs are separate so conventional word-problem annualization
    # cannot leak into exact elapsed-time comparisons.
    conversions: dict[tuple[str, str], float] = {}
    substance_conversions: dict[tuple[str, str, str], float] = {}
    cadence_conversions: dict[tuple[str, str], float] = {}
    for pack in packs:
        for doc in pack.conversions:
            for c in doc.conversions:
                if c.factor == 0:
                    raise CompileError(
                        f"conversion {c.from_!r}->{c.to!r} has a zero factor"
                    )
                if c.substance is not None:
                    if c.scope != "general":
                        raise CompileError(
                            "substance-scoped conversions cannot use cadence scope"
                        )
                    for pair, factor in (
                        ((c.substance, c.from_, c.to), c.factor),
                        ((c.substance, c.to, c.from_), 1.0 / c.factor),
                    ):
                        if (
                            pair in substance_conversions
                            and abs(substance_conversions[pair] - factor) > 1e-9
                        ):
                            raise CompileError(
                                f"substance conversion {pair} declared twice with "
                                "different factors"
                            )
                        substance_conversions[pair] = factor
                    continue
                target = (
                    cadence_conversions if c.scope == "cadence" else conversions
                )
                for pair, factor in (
                    ((c.from_, c.to), c.factor),
                    ((c.to, c.from_), 1.0 / c.factor),
                ):
                    if pair in target and abs(target[pair] - factor) > 1e-9:
                        raise CompileError(
                            f"{c.scope} conversion {pair} declared twice with "
                            "different factors"
                        )
                    target[pair] = factor

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

    # Compatibility view for existing geometry consumers. Definitions and
    # inheritance are compiled once by the general property machinery.
    shape_scope = _category_region("geometry_shape") if "geometry_shape" in category_parents else frozenset()
    for term, table in property_formulas.items():
        tags = list(word_categories.get(term, ()))
        shape = term in shape_scope or any(tag in shape_scope for tag in tags)
        if shape or term in word_formulas:
            for quantity, definition in table.items():
                key = (term, quantity)
                if key in geometry_formulas and geometry_formulas[key] != definition.expr:
                    raise CompileError(f"geometry formula {key!r} conflicts with a derived attribute")
                geometry_formulas[key] = definition.expr

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
            for rule in doc.compiled_rules:
                if rule.id in rule_ids:
                    raise CompileError(f"rule id {rule.id!r} defined twice")
                rule_ids.add(rule.id)
                rules.append(rule)
            for ask in doc.compiled_asks:
                if ask.id in rule_ids:
                    raise CompileError(f"ask id {ask.id!r} defined twice")
                rule_ids.add(ask.id)
                asks.append(ask)
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
            "qualified",
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

    def _validate_preceding_verb(predicate, slots, rule_id):
        spec = predicate.preceding_verb_category
        if spec is None:
            return
        if set(spec) != {"slot", "cat"} or spec.get("slot") not in slots:
            raise CompileError(f"rule {rule_id!r}: preceding verb gate needs a declared slot and category")
        if spec["cat"] not in valid_gates or _category_chain(spec["cat"])[-1] != "verb":
            raise CompileError(f"rule {rule_id!r}: preceding verb gate needs a verb category")

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
                        raise CompileError(
                            f"rule {rule.id!r} gates on unknown category {cat!r}"
                        )
                    if tok.enumeration_cat and tok.enumeration_cat not in valid_gates:
                        raise CompileError(
                            f"rule {rule.id!r} enumeration gates on unknown category {tok.enumeration_cat!r}"
                        )
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
                    qualifier_cat = getattr(tok, "qualifier_cat", None)
                    if qualifier_cat and qualifier_cat not in valid_gates:
                        raise CompileError(
                            f"rule {rule.id!r} qualifier gates on unknown "
                            f"category {qualifier_cat!r}"
                        )
                    determinerless_category = getattr(
                        tok, "determinerless_category", None
                    )
                    if determinerless_category is not None:
                        if determinerless_category not in valid_gates:
                            raise CompileError(
                                f"rule {rule.id!r} determinerless slot names "
                                f"unknown category {determinerless_category!r}"
                            )
                        root = determinerless_category
                        while root in category_parents:
                            root = category_parents[root]
                        if root != "noun":
                            raise CompileError(
                                f"rule {rule.id!r} determinerless category "
                                f"{determinerless_category!r} is not noun-rooted"
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
        for emit in rule.emits:
            for raw in emit.fields.values():
                members = re.fullmatch(r"\{(\w+)\.members\}", raw) if isinstance(raw, str) else None
                if members is not None:
                    token = slots.get(members.group(1))
                    if token is None or not token.enumeration_cat:
                        raise CompileError(f"rule {rule.id!r}: members emission needs an enumeration-gated span")
                optional = re.fullmatch(r"\{(\w+)\.optional\}", raw) if isinstance(raw, str) else None
                if optional is not None and optional.group(1) not in slots:
                    raise CompileError(f"rule {rule.id!r}: optional emission needs a declared slot")
            if emit.fact != "relation":
                continue
            for field_name, expected_root in (
                ("anaphor_measure_category", "noun"),
                ("anaphor_verb_category", "verb"),
            ):
                category = emit.fields.get(field_name)
                if category is None:
                    continue
                if not isinstance(category, str) or "{" in category:
                    raise CompileError(
                        f"rule {rule.id!r} relation {field_name} must be a "
                        "literal category"
                    )
                if category not in valid_gates:
                    raise CompileError(
                        f"rule {rule.id!r} relation {field_name} names "
                        f"unknown category {category!r}"
                    )
                root = category
                while root in category_parents:
                    root = category_parents[root]
                if root != expected_root:
                    raise CompileError(
                        f"rule {rule.id!r} relation {field_name} category "
                        f"{category!r} is {root!r}-rooted, not "
                        f"{expected_root!r}-rooted"
                    )
        for predicate in (*rule.where, *rule.generation_where):
            _validate_text_prefix_split(predicate, slots, rule.id)
            _validate_preceding_verb(predicate, slots, rule.id)
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
                    "noun",
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
            modifier_compatibility = predicate.modifier_host_compatible
            if modifier_compatibility is not None:
                modifier = slots.get(modifier_compatibility.modifier)
                host = slots.get(modifier_compatibility.host)
                if modifier is None or host is None:
                    missing = (
                        modifier_compatibility.modifier
                        if modifier is None
                        else modifier_compatibility.host
                    )
                    raise CompileError(
                        f"rule {rule.id!r} modifier-host compatibility names "
                        f"unknown slot {missing!r}"
                    )
                if _slot_root(modifier) != "preposition":
                    raise CompileError(
                        f"rule {rule.id!r} modifier-host modifier slot "
                        f"{modifier_compatibility.modifier!r} is not "
                        "preposition-rooted"
                    )
                if _slot_root(host) != modifier_compatibility.host_type:
                    raise CompileError(
                        f"rule {rule.id!r} modifier-host host slot "
                        f"{modifier_compatibility.host!r} is not {modifier_compatibility.host_type}-rooted"
                    )
                if modifier_compatibility.nominal_host is not None:
                    nominal = slots.get(modifier_compatibility.nominal_host)
                    if nominal is None or _slot_root(nominal) != "noun":
                        raise CompileError(f"rule {rule.id!r} nominal alternative must name a noun-rooted slot")
                if modifier_compatibility.object is not None:
                    object_ = slots.get(modifier_compatibility.object)
                    if object_ is None:
                        raise CompileError(
                            f"rule {rule.id!r} modifier-host compatibility "
                            "names unknown object slot "
                            f"{modifier_compatibility.object!r}"
                        )
                    if _slot_root(object_) != "noun":
                        raise CompileError(
                            f"rule {rule.id!r} modifier-host object slot "
                            f"{modifier_compatibility.object!r} is not noun-rooted"
                        )
            adverb_compatibility = predicate.adverb_verb_compatible
            if adverb_compatibility is not None:
                adverb = slots.get(adverb_compatibility.adverb)
                verb = slots.get(adverb_compatibility.verb)
                if adverb is None or verb is None:
                    missing = (
                        adverb_compatibility.adverb
                        if adverb is None
                        else adverb_compatibility.verb
                    )
                    raise CompileError(
                        f"rule {rule.id!r} adverb-verb compatibility names "
                        f"unknown slot {missing!r}"
                    )
                if _slot_root(adverb) != "adverb":
                    raise CompileError(
                        f"rule {rule.id!r} adverb-verb compatibility adverb "
                        f"slot {adverb_compatibility.adverb!r} is not "
                        "adverb-rooted"
                    )
                if _slot_root(verb) != "verb":
                    raise CompileError(
                        f"rule {rule.id!r} adverb-verb compatibility verb "
                        f"slot {adverb_compatibility.verb!r} is not verb-rooted"
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
                if conditional.bound_cat is not None and conditional.bound_cat not in valid_gates:
                    raise CompileError(f"rule {rule.id!r} conditional trigger names unknown category {conditional.bound_cat!r}")
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
            if predicate.mutually_exclusive is not None:
                if len(predicate.mutually_exclusive) < 2:
                    raise CompileError(
                        f"rule {rule.id!r} mutually_exclusive needs at least "
                        "two slots"
                    )
                for slot_name in predicate.mutually_exclusive:
                    if slot_name not in slots:
                        raise CompileError(
                            f"rule {rule.id!r} mutually_exclusive names "
                            f"unknown slot {slot_name!r}"
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
                trigger_root = _slot_root(slots[role_compatibility.verb])
                role_category = (
                    role_compatibility.role_cat
                    or role_compatibility.excluded_role_cat
                )
                assert role_category is not None
                for category, expected_root in (
                    (role_compatibility.verb_cat, trigger_root),
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
                            f"rule {rule.id!r} trigger-role compatibility "
                            f"category {category!r} is not "
                            f"{expected_root}-rooted"
                        )
            roles_compatibility = predicate.verb_roles_compatible
            if roles_compatibility is not None:
                trigger = slots.get(roles_compatibility.verb)
                if trigger is None:
                    raise CompileError(
                        f"rule {rule.id!r} verb roles compatibility names "
                        f"unknown slot {roles_compatibility.verb!r}"
                    )
                if _slot_root(trigger) != "verb":
                    raise CompileError(
                        f"rule {rule.id!r} verb roles trigger "
                        f"{roles_compatibility.verb!r} is not verb-rooted"
                    )
                for category in roles_compatibility.frame_categories:
                    if category not in valid_gates:
                        raise CompileError(
                            f"rule {rule.id!r} verb roles compatibility names "
                            f"unknown frame category {category!r}"
                        )
                    root = category
                    while root in category_parents:
                        root = category_parents[root]
                    if root != "verb":
                        raise CompileError(
                            f"rule {rule.id!r} verb roles frame category "
                            f"{category!r} is not verb-rooted"
                        )
                for semantic_role, slot_names in (
                    roles_compatibility.roles.items()
                ):
                    if semantic_role not in selectional_role_names:
                        raise CompileError(
                            f"rule {rule.id!r} verb roles compatibility names "
                            f"undeclared semantic role {semantic_role!r}"
                        )
                    for slot_name in slot_names:
                        token = slots.get(slot_name)
                        if token is None:
                            raise CompileError(
                                f"rule {rule.id!r} verb roles compatibility "
                                f"names unknown slot {slot_name!r}"
                            )
                        if _slot_root(token) not in _SELECTIONAL_ROLE_SLOT_ROOTS:
                            raise CompileError(
                                f"rule {rule.id!r} verb role slot "
                                f"{slot_name!r} is not noun/entity-rooted"
                            )
            measure_compatibility = predicate.measure_holder_compatible
            if measure_compatibility is not None:
                for slot_name in (
                    measure_compatibility.measure,
                    *(
                        (measure_compatibility.attribute,)
                        if measure_compatibility.attribute is not None
                        else ()
                    ),
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
                if (
                    measure_compatibility.attribute is not None
                    and _slot_root(
                        slots[measure_compatibility.attribute]
                    ) not in {"adjective", "comparative", "preposition"}
                ):
                    raise CompileError(
                        f"rule {rule.id!r} measure-holder compatibility "
                        f"attribute {measure_compatibility.attribute!r} is not "
                        "descriptor-rooted"
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
            partitive_compatibility = predicate.partitive_compatible
            if partitive_compatibility is not None:
                for slot_name in (
                    partitive_compatibility.measure,
                    partitive_compatibility.substance,
                ):
                    token = slots.get(slot_name)
                    if token is None:
                        raise CompileError(
                            f"rule {rule.id!r} partitive compatibility names "
                            f"unknown slot {slot_name!r}"
                        )
                    if _slot_root(token) != "noun":
                        raise CompileError(
                            f"rule {rule.id!r} partitive compatibility slot "
                            f"{slot_name!r} is not noun-rooted"
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
            category_contains = predicate.category_contains
            if category_contains is not None:
                for slot_name in (
                    category_contains.collection,
                    *category_contains.members,
                ):
                    token = slots.get(slot_name)
                    if token is None:
                        raise CompileError(
                            f"rule {rule.id!r} category containment names "
                            f"unknown slot {slot_name!r}"
                        )
                    if not (
                        token.type in {"entity", "name", "proper_name"}
                        or _slot_root(token) == "noun"
                    ):
                        raise CompileError(
                            f"rule {rule.id!r} category containment slot "
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
        for source, needs in rule.bindings.items():
            token = slots.get(source)
            root = _slot_root(token) if token is not None else None
            role = role_obligations.get(root)
            for need, target in needs.items():
                if (token is None or token.span or target == source
                        or target not in slots or slots[target].span
                        or role is None or need not in role.needs
                        or (need == "collection" and _slot_root(slots[target]) not in {"noun", "pronoun"})):
                    raise CompileError(f"rule {rule.id!r}: invalid unit obligation binding {source}.{need} -> {target}")
                if need in rule.satisfies.get(source, ()):
                    raise CompileError(f"rule {rule.id!r}: a bound need cannot also use pattern satisfaction")
        for source, target in rule.references.items():
            for slot_name in (source, target):
                token = slots.get(slot_name)
                if token is None or token.span:
                    raise CompileError(
                        f"rule {rule.id!r} reference binding needs a single-unit "
                        f"slot {slot_name!r}"
                    )
            if _slot_root(slots[source]) not in {"pronoun", "name", "proper_name", "entity"}:
                raise CompileError(f"rule {rule.id!r} reference source {source!r} is not referential")
            target_root = _slot_root(slots[target])
            resolved_pronoun = target_root == "pronoun" and slots[target].referential
            if target_root not in {"noun", "name", "proper_name", "entity"} and not resolved_pronoun:
                raise CompileError(f"rule {rule.id!r} reference target {target!r} is not nominal")
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

    # Ask rules use the same closed where-predicate model as premise rules.
    # Validate the cross-slot predicate introduced for partitive questions at
    # compile time so an authoring typo cannot become a silently dead ask.
    for ask in asks:
        for token in _walk_match_tokens(ask.match["question"]):
            if token.enumeration_cat and token.enumeration_cat not in valid_gates:
                raise CompileError(
                    f"ask {ask.id!r} enumeration gates on unknown category {token.enumeration_cat!r}"
                )
        ask_slots = {
            token.slot: token
            for token in _walk_match_tokens(ask.match["question"])
            if token.slot is not None
        }
        for slot_name in ask.satisfies:
            token = ask_slots.get(slot_name)
            if token is None:
                raise CompileError(
                    f"ask {ask.id!r} pattern satisfaction names unknown "
                    f"slot {slot_name!r}"
                )
            if token.span:
                raise CompileError(
                    f"ask {ask.id!r} pattern satisfaction slot "
                    f"{slot_name!r} is a span, not one obligation-bearing unit"
                )
        for predicate in ask.where:
            _validate_text_prefix_split(predicate, ask_slots, ask.id)
            _validate_preceding_verb(predicate, ask_slots, ask.id)
            if predicate.number_compatible is not None:
                for slot_name in predicate.number_compatible:
                    if slot_name not in ask_slots:
                        raise CompileError(
                            f"ask {ask.id!r} number compatibility names "
                            f"unknown slot {slot_name!r}"
                        )
            conditional = predicate.bound_requires_category
            if conditional is not None:
                for slot_name in (conditional.bound, conditional.slot):
                    if slot_name not in ask_slots:
                        raise CompileError(
                            f"ask {ask.id!r} conditional category names "
                            f"unknown slot {slot_name!r}"
                        )
                if conditional.cat not in valid_gates:
                    raise CompileError(
                        f"ask {ask.id!r} conditional category names "
                        f"unknown category {conditional.cat!r}"
                    )
                if conditional.bound_cat is not None and conditional.bound_cat not in valid_gates:
                    raise CompileError(f"ask {ask.id!r} conditional trigger names unknown category {conditional.bound_cat!r}")
            conditional_type = predicate.bound_requires_type
            if conditional_type is not None:
                for slot_name in (
                    conditional_type.bound,
                    conditional_type.slot,
                ):
                    if slot_name not in ask_slots:
                        raise CompileError(
                            f"ask {ask.id!r} conditional type names "
                            f"unknown slot {slot_name!r}"
                        )
            exclusion = predicate.slot_not_category
            if exclusion is not None:
                slot_name = exclusion.get("slot")
                if slot_name not in ask_slots:
                    raise CompileError(
                        f"ask {ask.id!r} slot exclusion names unknown slot "
                        f"{slot_name!r}"
                    )
            ask_attribute_compatibility = predicate.attribute_compatible
            if ask_attribute_compatibility is not None:
                attribute = ask_slots.get(ask_attribute_compatibility.attribute)
                noun = ask_slots.get(ask_attribute_compatibility.noun)
                if attribute is None or noun is None:
                    missing = (
                        ask_attribute_compatibility.attribute
                        if attribute is None
                        else ask_attribute_compatibility.noun
                    )
                    raise CompileError(
                        f"ask {ask.id!r} compatibility names unknown slot "
                        f"{missing!r}"
                    )
                if _slot_root(attribute) not in {
                    "adjective",
                    "comparative",
                    "preposition",
                    "noun",
                }:
                    raise CompileError(
                        f"ask {ask.id!r} compatibility attribute slot "
                        f"{ask_attribute_compatibility.attribute!r} is not "
                        "descriptor-rooted"
                    )
                if _slot_root(noun) != "noun":
                    raise CompileError(
                        f"ask {ask.id!r} compatibility noun slot "
                        f"{ask_attribute_compatibility.noun!r} is not noun-rooted"
                    )
            ask_adverb_compatibility = predicate.adverb_verb_compatible
            if ask_adverb_compatibility is not None:
                adverb = ask_slots.get(ask_adverb_compatibility.adverb)
                verb = ask_slots.get(ask_adverb_compatibility.verb)
                if adverb is None or verb is None:
                    missing = (
                        ask_adverb_compatibility.adverb
                        if adverb is None
                        else ask_adverb_compatibility.verb
                    )
                    raise CompileError(
                        f"ask {ask.id!r} adverb-verb compatibility names "
                        f"unknown slot {missing!r}"
                    )
                if _slot_root(adverb) != "adverb":
                    raise CompileError(
                        f"ask {ask.id!r} adverb-verb compatibility adverb "
                        f"slot {ask_adverb_compatibility.adverb!r} is not "
                        "adverb-rooted"
                    )
                if _slot_root(verb) != "verb":
                    raise CompileError(
                        f"ask {ask.id!r} adverb-verb compatibility verb "
                        f"slot {ask_adverb_compatibility.verb!r} is not "
                        "verb-rooted"
                    )
            role_compatibility = predicate.verb_role_compatible
            if role_compatibility is not None:
                for slot_name in (
                    role_compatibility.verb,
                    *role_compatibility.roles,
                ):
                    if slot_name not in ask_slots:
                        raise CompileError(
                            f"ask {ask.id!r} verb-role compatibility names "
                            f"unknown slot {slot_name!r}"
                        )
                trigger_root = _slot_root(
                    ask_slots[role_compatibility.verb]
                )
                role_category = (
                    role_compatibility.role_cat
                    or role_compatibility.excluded_role_cat
                )
                assert role_category is not None
                for category, expected_root in (
                    (role_compatibility.verb_cat, trigger_root),
                    (role_category, "noun"),
                ):
                    if category not in valid_gates:
                        raise CompileError(
                            f"ask {ask.id!r} verb-role compatibility names "
                            f"unknown category {category!r}"
                        )
                    root = category
                    while root in category_parents:
                        root = category_parents[root]
                    if root != expected_root:
                        raise CompileError(
                            f"ask {ask.id!r} verb-role compatibility category "
                            f"{category!r} is not {expected_root}-rooted"
                        )
            roles_compatibility = predicate.verb_roles_compatible
            if roles_compatibility is not None:
                trigger = ask_slots.get(roles_compatibility.verb)
                if trigger is None:
                    raise CompileError(
                        f"ask {ask.id!r} verb roles compatibility names "
                        f"unknown slot {roles_compatibility.verb!r}"
                    )
                if _slot_root(trigger) != "verb":
                    raise CompileError(
                        f"ask {ask.id!r} verb roles trigger "
                        f"{roles_compatibility.verb!r} is not verb-rooted"
                    )
                for category in roles_compatibility.frame_categories:
                    if category not in valid_gates:
                        raise CompileError(
                            f"ask {ask.id!r} verb roles compatibility names "
                            f"unknown frame category {category!r}"
                        )
                    root = category
                    while root in category_parents:
                        root = category_parents[root]
                    if root != "verb":
                        raise CompileError(
                            f"ask {ask.id!r} verb roles frame category "
                            f"{category!r} is not verb-rooted"
                        )
                for semantic_role, slot_names in (
                    roles_compatibility.roles.items()
                ):
                    if semantic_role not in selectional_role_names:
                        raise CompileError(
                            f"ask {ask.id!r} verb roles compatibility names "
                            f"undeclared semantic role {semantic_role!r}"
                        )
                    for slot_name in slot_names:
                        token = ask_slots.get(slot_name)
                        if token is None:
                            raise CompileError(
                                f"ask {ask.id!r} verb roles compatibility "
                                f"names unknown slot {slot_name!r}"
                            )
                        if _slot_root(token) not in _SELECTIONAL_ROLE_SLOT_ROOTS:
                            raise CompileError(
                                f"ask {ask.id!r} verb role slot "
                                f"{slot_name!r} is not noun/entity-rooted"
                            )
            measure_compatibility = predicate.measure_holder_compatible
            if measure_compatibility is not None:
                for slot_name in (
                    measure_compatibility.measure,
                    *(
                        (measure_compatibility.attribute,)
                        if measure_compatibility.attribute is not None
                        else ()
                    ),
                    *measure_compatibility.holders,
                ):
                    if slot_name not in ask_slots:
                        raise CompileError(
                            f"ask {ask.id!r} measure-holder compatibility "
                            f"names unknown slot {slot_name!r}"
                        )
                if _slot_root(
                    ask_slots[measure_compatibility.measure]
                ) != "noun":
                    raise CompileError(
                        f"ask {ask.id!r} measure-holder compatibility measure "
                        f"{measure_compatibility.measure!r} is not noun-rooted"
                    )
                if (
                    measure_compatibility.attribute is not None
                    and _slot_root(
                        ask_slots[measure_compatibility.attribute]
                    ) not in {"adjective", "comparative", "preposition"}
                ):
                    raise CompileError(
                        f"ask {ask.id!r} measure-holder compatibility "
                        f"attribute {measure_compatibility.attribute!r} is not "
                        "descriptor-rooted"
                    )
                for holder_name in measure_compatibility.holders:
                    holder = ask_slots[holder_name]
                    if not (
                        holder.type in {"entity", "name", "proper_name"}
                        or _slot_root(holder) == "noun"
                    ):
                        raise CompileError(
                            f"ask {ask.id!r} measure-holder compatibility "
                            f"holder {holder_name!r} is not entity/noun-rooted"
                        )
            compatibility = predicate.partitive_compatible
            if compatibility is None:
                continue
            for slot_name in (
                compatibility.measure,
                compatibility.substance,
            ):
                token = ask_slots.get(slot_name)
                if token is None:
                    raise CompileError(
                        f"ask {ask.id!r} partitive compatibility names "
                        f"unknown slot {slot_name!r}"
                    )
                if _slot_root(token) != "noun":
                    raise CompileError(
                        f"ask {ask.id!r} partitive compatibility slot "
                        f"{slot_name!r} is not noun-rooted"
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
            qualifier_cat = getattr(tok, "qualifier_cat", None)
            if qualifier_cat and qualifier_cat not in valid_gates:
                raise CompileError(
                    f"{rule.id!r} qualifier gates on unknown category "
                    f"{qualifier_cat!r}"
                )
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
        category_includes=_freeze(category_includes),
        category_disjoint=_freeze({k: tuple(sorted(v)) for k, v in category_disjoint.items()}),
        category_members=_freeze({k: tuple(sorted(set(v))) for k, v in category_members.items()}),
        word_categories=_freeze({k: tuple(sorted(set(v))) for k, v in word_categories.items()}),
        category_antonyms=_freeze(category_antonyms),
        category_polarity=_freeze(category_polarity),
        selectional_roles=_freeze(
            {
                category: _freeze(roles)
                for category, roles in selectional_roles.items()
            }
        ),
        selectional_role_numbers=_freeze(
            {
                category: _freeze(numbers)
                for category, numbers in selectional_role_numbers.items()
            }
        ),
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
        modifier_host_compatibility=_freeze(
            {
                key: tuple(sorted(set(values)))
                for key, values in modifier_host_compatibility.items()
            }
        ),
        adverb_verb_compatibility=_freeze(
            {
                key: tuple(sorted(set(values)))
                for key, values in adverb_verb_compatibility.items()
            }
        ),
        modifier_attachment_compatibility=tuple(
            sorted(set(modifier_attachment_compatibility))
        ),
        measure_holder_compatibility=_freeze(
            {
                key: tuple(sorted(set(values)))
                for key, values in measure_holder_compatibility.items()
            }
        ),
        partitive_measure_compatibility=_freeze(
            {
                key: tuple(sorted(set(values)))
                for key, values in partitive_measure_compatibility.items()
            }
        ),
        subject_role_derivations=_freeze(subject_role_derivations),
        adposition_roles=_freeze(adposition_roles),
        temporal_offsets=_freeze(temporal_offsets),
        context_synonyms=_freeze(context_synonyms),
        attrs=_freeze({k: _freeze(v) for k, v in attrs.items()}),
        property_formulas=_freeze({k: _freeze(v) for k, v in property_formulas.items()}),
        property_sources=_freeze(property_sources),
        parameter_bindings=_freeze({k: _freeze(v) for k, v in parameter_bindings.items()}),
        formula_units=_freeze(formula_units),
        formula_unit_categories=_freeze(formula_unit_categories),
        property_aliases=_freeze(property_aliases),
        formula_constants=_freeze(formula_constants),
        part_counts=_freeze(part_counts),
        conversions=_freeze(conversions),
        substance_conversions=_freeze(substance_conversions),
        cadence_conversions=_freeze(cadence_conversions),
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
