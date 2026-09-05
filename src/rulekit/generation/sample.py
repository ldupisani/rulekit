"""Deterministic sampling for supported premise-pattern rules."""

from __future__ import annotations

import hashlib
import random
import re
import secrets
from collections import Counter, OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Literal

from ruamel.yaml import YAML

from ..data.project import Project
from ..data.registry import Registry
from ..data.schemas import (
    AdverbVerbCompatibilityPredicate,
    AttributeCompatibilityPredicate,
    MatchToken,
    PatternRule,
    VerbRolesCompatibilityPredicate,
    WherePredicate,
)
from ..data.sources import SourceRef
from ..kernel.document import run_document
from ..kernel.engine import analyze
from ..kernel.model import Unit, _jsonable
from ..kernel.patterns import (
    RuleMatchResult,
    SKIPPABLE_SENSES,
    _role_is_proper_name,
    is_bare_verb_form,
    is_finite_verb_form,
    proportional_delta_is_compatible,
    subsumes,
)
from .candidate import (
    ConsumedUnitSummary,
    GenerationCandidate,
    GenerationMode,
    LexicalRelaxation,
    MatchSummary,
    PremiseSummary,
    RuleAvailability,
)

GENERATOR_VERSION = "g6-strict-boundary-modes"
_SUPPORTED_SLOT_TYPES = frozenset(
    {
        "number",
        "fraction",
        "multiplier",
        "nonunit_multiplier",
        "name",
        "noun",
        "entity",
        "verb",
        "word",
        "adjective",
        "percent",
        "nonstate_verb",
        "proper_name",
        "preposition",
        "common_noun",
        "plural",
        "bare_plural",
        "generic_plural",
        "counted",
        "qualified",
        "possessed",
        "pronoun",
        "modal",
        "future_modal",
        "date",
        "point",
        "formula",
    }
)
_SUPPORTED_CATEGORY_ROOTS = frozenset(
    {
        "noun",
        "verb",
        "adjective",
        "preposition",
        "pronoun",
        "modal",
        "aggregate",
        "comparative",
        "complementizer",
        "quantifier",
        "conjunction",
        "time",
        "adverb",
        "auxiliary",
    }
)
_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":"})
_yaml = YAML(typ="rt")
_CACHE_LOCK = RLock()
_StructuralValues = tuple[tuple[str, tuple[str, ...]], ...]
_FixtureCacheKey = tuple[tuple[str, ...], _StructuralValues]
_DOMAIN_CACHE: OrderedDict[
    tuple[str, _FixtureCacheKey, str], list["_Filler"]
] = OrderedDict()
_BOUNDARY_DOMAIN_CACHE: OrderedDict[
    tuple[str, _FixtureCacheKey, str],
    tuple[list["_Filler"], str, str] | None,
] = OrderedDict()
_AVAILABILITY_CACHE: OrderedDict[
    tuple[str, _FixtureCacheKey], tuple[RuleAvailability, ...]
] = OrderedDict()
_MAX_DOMAIN_CACHE_ENTRIES = 4096
_MAX_AVAILABILITY_CACHE_ENTRIES = 32


class GenerationError(ValueError):
    """A selected rule cannot produce a generation candidate."""


@dataclass(frozen=True)
class _Filler:
    surface: str
    identity: str
    owner: str | None = None
    number: Literal["singular", "plural"] | None = None
    label: str | None = None
    qualifier: str | None = None
    reference_form: Literal["bare", "definite"] | None = None
    kind: str | None = None
    value: float | None = None


def _filler_in_category(
    filler: _Filler, category: str, reg: Registry
) -> bool:
    """Mirror scalar matching: category membership may use surface or lemma."""

    return reg.word_in_category(
        filler.identity, category
    ) or reg.word_in_category(filler.surface.casefold(), category)


def _filler_satisfies_selectional_role(
    filler: _Filler,
    category: str,
    number: str | None,
    slot: str,
    compatibility: VerbRolesCompatibilityPredicate,
    reg: Registry,
) -> bool:
    if number is not None and filler.number != number:
        return False
    return (
        slot in compatibility.allow_proper_name and filler.kind == "name"
    ) or (
        slot in compatibility.allow_plural_class
        and filler.number == "plural"
    ) or _filler_in_category(filler, category, reg)


def _selectional_assignment_compatible(
    verb: _Filler,
    assignments: dict[str, _Filler],
    compatibility: VerbRolesCompatibilityPredicate,
    reg: Registry,
) -> bool:
    """Whether one complete lexical frame accepts all currently known roles."""

    frames = reg.selectional_frames(verb.identity)
    if compatibility.frame_categories:
        frames = tuple(
            (category, frame)
            for category, frame in frames
            if any(
                trigger in reg.cat_ancestors(category)
                for trigger in compatibility.frame_categories
            )
        )
    if not frames:
        return not compatibility.require_declared_frame
    for frame_category, frame in frames:
        if not set(compatibility.roles) <= set(frame):
            continue
        if all(
            _filler_satisfies_selectional_role(
                assignments[slot],
                frame[semantic_role],
                reg.selectional_role_number(frame_category, semantic_role),
                slot,
                compatibility,
                reg,
            )
            for semantic_role, slots in compatibility.roles.items()
            for slot in slots
            if slot in assignments
        ):
            return True
    return False


def _filler_categories_overlap(
    left: _Filler, right: _Filler, reg: Registry
) -> bool:
    """Whether generated noun roles have unresolved category containment."""

    if left.kind != "noun" or right.kind != "noun":
        return False
    if left.label and right.label and left.label != right.label:
        return False
    if left.owner and right.owner and left.owner != right.owner:
        return False
    return reg.category_terms_overlap(left.identity, right.identity)


def _filler_category_term_contains(
    collection: _Filler, member: _Filler, reg: Registry
) -> bool:
    """Whether a generated collection term contains a generated member.

    Plural and category-gated noun domains do not need the ``kind='noun'``
    marker used by open entity domains. Positive membership nevertheless
    needs the same registry taxonomy check, while independently labelled or
    owned referents must remain distinct.
    """

    if collection.label and member.label and collection.label != member.label:
        return False
    if collection.owner and member.owner and collection.owner != member.owner:
        return False
    return reg.category_term_contains(collection.identity, member.identity)


@dataclass(frozen=True)
class _Fixtures:
    names: tuple[str, ...]
    sources: dict[str, SourceRef]
    structural_values: _StructuralValues = ()

    def values_for(self, slot_type: str | None) -> tuple[str, ...]:
        if slot_type is None:
            return ()
        return dict(self.structural_values).get(slot_type, ())

    @property
    def cache_key(self) -> _FixtureCacheKey:
        return self.names, self.structural_values


def _load_fixtures(project_root: Path) -> _Fixtures:
    """Load generation fixtures once per exact on-disk revision.

    Ask realization consults the fixture domains for several tokens on every
    deterministic attempt.  Reparsing the same YAML at each lookup made a
    bounded scenario search behave like an unbounded request.  The file
    revision remains part of the key so Designer edits become visible without
    restarting the server.
    """

    path = project_root / "generation.yaml"
    try:
        stat = path.stat()
    except FileNotFoundError:
        return _Fixtures(names=(), sources={}, structural_values=())
    return _load_fixtures_revision(path, stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=32)
def _load_fixtures_revision(
    path: Path,
    _mtime_ns: int,
    _size: int,
) -> _Fixtures:
    """Parse one immutable fixture-file revision."""

    raw = _yaml.load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("format") != "rulekit/generation@1":
        raise GenerationError(
            f"{path}: expected a rulekit/generation@1 mapping"
        )
    names = raw.get("names")
    if not isinstance(names, list) or not names:
        raise GenerationError(f"{path}: names must be a non-empty list")
    if any(
        not isinstance(name, str)
        or not name
        or name.strip() != name
        or any(ch.isspace() for ch in name)
        for name in names
    ):
        raise GenerationError(
            f"{path}: generation names must be non-empty, single-token strings"
        )
    if len(set(names)) != len(names):
        raise GenerationError(f"{path}: names must be unique")
    raw_structural_values = raw.get("structural_values", {})
    if not isinstance(raw_structural_values, dict):
        raise GenerationError(f"{path}: structural_values must be a mapping")
    supported_structural_types = {"date", "point", "formula"}
    unknown_structural_types = (
        set(raw_structural_values) - supported_structural_types
    )
    if unknown_structural_types:
        raise GenerationError(
            f"{path}: unsupported structural value types: "
            + ", ".join(sorted(unknown_structural_types))
        )
    structural_values: list[tuple[str, tuple[str, ...]]] = []
    for slot_type, values in sorted(raw_structural_values.items()):
        if (
            not isinstance(values, list)
            or not values
            or any(
                not isinstance(value, str)
                or not value
                or value.strip() != value
                or any(ch.isspace() for ch in value)
                for value in values
            )
        ):
            raise GenerationError(
                f"{path}: structural_values.{slot_type} must be a non-empty "
                "list of single-token strings"
            )
        if len(set(values)) != len(values):
            raise GenerationError(
                f"{path}: structural_values.{slot_type} must be unique"
            )
        structural_values.append((slot_type, tuple(values)))
    sources: dict[str, SourceRef] = {}
    for index, name in enumerate(names):
        try:
            line, column = names.lc.item(index)
        except (AttributeError, KeyError, TypeError):
            line, column = 0, 0
        sources[name.casefold()] = SourceRef(
            path=path.resolve(),
            line=line + 1,
            column=column + 1,
            kind="generation-fixture",
            label=name,
        )
    return _Fixtures(
        names=tuple(names),
        sources=sources,
        structural_values=tuple(structural_values),
    )


def _flat_sentence(rule: PatternRule) -> list[MatchToken] | None:
    seq = rule.match.get("sentence")
    if seq is None or (seq and isinstance(seq[0], list)):
        return None
    return seq  # type: ignore[return-value]


def _token_nodes(
    tokens: list[MatchToken],
    *,
    parent_path: tuple[int, ...] = (),
    optional_ancestors: tuple[tuple[int, ...], ...] = (),
):
    """Yield every token recursively with its stable YAML path."""

    for token_no, token in enumerate(tokens):
        path = (*parent_path, token_no)
        yield path, token, optional_ancestors
        if token.opt is not None:
            yield from _token_nodes(
                token.opt,
                parent_path=path,
                optional_ancestors=(*optional_ancestors, path),
            )


def _leaf_tokens(tokens: list[MatchToken]):
    """Yield realizable tokens inside arbitrarily nested optional groups."""

    for path, token, optional_ancestors in _token_nodes(tokens):
        if token.opt is None:
            yield path, token, optional_ancestors


def _token_blockers(token: MatchToken, reg: Registry) -> list[str]:
    blockers: list[str] = []
    if token.opt is not None:
        for child in token.opt:
            blockers.extend(_token_blockers(child, reg))
        return blockers
    if token.span:
        blockers.append("span capture has no current realizer")
    if token.slot is not None and token.type is not None:
        if token.type not in _SUPPORTED_SLOT_TYPES:
            blockers.append(f"slot type {token.type!r} has no current realizer")
    if token.slot is not None and token.cat is not None:
        root = reg.root_sense(token.cat)
        if root not in _SUPPORTED_CATEGORY_ROOTS:
            blockers.append(
                f"category {token.cat!r} roots at unsupported sense {root!r}"
            )
    if token.common_noun_cat is not None:
        root = reg.root_sense(token.common_noun_cat)
        if root != "noun":
            blockers.append(
                f"common-noun category {token.common_noun_cat!r} roots at "
                f"unsupported sense {root!r}"
            )
    return blockers


def _generation_predicates(rule: PatternRule) -> tuple[WherePredicate, ...]:
    """Reader predicates plus generator-only surface-quality constraints."""

    return (*rule.where, *rule.generation_where)


def _where_blocker(rule: PatternRule) -> list[str]:
    blockers: list[str] = []
    for pred in _generation_predicates(rule):
        if (
            pred.distinct is not None
            or pred.category_nonoverlap is not None
            or pred.category_contains is not None
            or pred.distinct_owner is not None
            or pred.distinct_from_owner is not None
            or pred.same_lemma is not None
            or pred.same_surface is not None
            or pred.same_number is not None
            or pred.same_category_membership is not None
            or pred.number_compatible is not None
            or pred.bound_requires_type is not None
            or pred.bound_requires_category is not None
            or pred.bound_rejects_category is not None
            or pred.category_requires_bound is not None
            or pred.bound_requires_form is not None
            or pred.polarity_compatible is not None
            or pred.proportional_delta_compatible is not None
            or pred.same_presence is not None
            or pred.mutually_exclusive is not None
            or pred.verb_role_compatible is not None
            or pred.verb_roles_compatible is not None
            or pred.measure_holder_compatible is not None
            or pred.partitive_compatible is not None
            or pred.attribute_compatible is not None
            or pred.modifier_host_compatible is not None
            or pred.adverb_verb_compatible is not None
            or pred.slot_not_category is not None
            or pred.absent is not None
            or pred.unbound is not None
            or pred.distinct_measure is not None
        ):
            continue
        kind = next(
            name
            for name in (
                "same_phrase",
                "name_count",
            )
            if getattr(pred, name) is not None
        )
        blockers.append(f"where predicate {kind!r} has no current realizer")
    return blockers


def _is_atomic_noun_surface(surface: str, reg: Registry) -> bool:
    """Single words or noun phrases explicitly supported by the reader."""
    if not surface:
        return False
    if not any(ch.isspace() for ch in surface):
        return True
    lemma = reg.plural_to_singular.get(surface, surface)
    entry = reg.lexicon.get(lemma)
    return bool(entry and entry.lexical_phrase and entry.senses == ["noun"])


def _lexical_fillers(
    reg: Registry,
    *,
    sense: str | None = None,
    category: str | None = None,
    bare_form: bool = False,
    finite_form: bool = False,
    present_participle: bool = False,
    past_participle: bool = False,
) -> list[_Filler]:
    out: list[_Filler] = []
    for surface, entry in sorted(reg.lexicon.items()):
        if not surface:
            continue
        if any(ch.isspace() for ch in surface) and not (
            (sense == "preposition" and "preposition" in entry.senses)
            or entry.lexical_phrase
        ):
            # Only declared atomic phrases have a reader round-trip contract.
            continue
        if sense is not None and (
            surface in reg.numbers
            or surface in reg.fractions
            or surface in reg.multipliers
        ):
            # The ordinary analyzer commits declared numeric surfaces before
            # lexical sense selection.  A homograph such as an authored
            # multiplier/verb can therefore never round-trip through a
            # sense-specific lexical slot as that verb.  Keep it available to
            # broad `word` exploration, but do not advertise an unreachable
            # lexical reading that every generated candidate must reject.
            continue
        if category is not None and not reg.word_in_category(surface, category):
            continue
        if sense is not None and sense not in entry.senses:
            continue
        if sense == "noun" and surface in reg.plural_to_singular:
            continue
        identity = reg.plural_to_singular.get(
            surface, reg.verb_lemmas.get(surface, surface)
        )
        if bare_form and not is_bare_verb_form(surface, identity):
            continue
        if finite_form and not is_finite_verb_form(surface, identity):
            continue
        # Mirror patterns._slot_ok's opt-in morphology exactly. These are
        # structural surface checks over pack-declared lemmas, not an English
        # word list, so newly added participles become generatable without a
        # second authoring mechanism.
        if present_participle and not (
            surface.endswith("ing") and surface != identity
        ):
            continue
        if past_participle and not (
            surface.endswith(("ed", "en")) and surface != identity
        ):
            continue
        number = entry.number
        if sense == "noun" and surface not in reg.plural_to_singular:
            number = number or "singular"
        out.append(
            _Filler(
                surface=surface,
                identity=identity,
                number=number,
                kind=sense,
            )
        )
    return out


def _number_fillers(reg: Registry) -> list[_Filler]:
    values = sorted(
        {
            int(value)
            for value in reg.numbers.values()
            if float(value).is_integer() and value >= 0
        }
    )
    return [
        _Filler(
            str(value),
            str(value),
            number="singular" if value == 1 else "plural",
            value=float(value),
        )
        for value in values
    ]


def _fraction_fillers(reg: Registry) -> list[_Filler]:
    """Realize complete fraction phrases from declared number morphology."""

    direct = [
        _Filler(
            surface,
            reg.fraction_plurals.get(surface, surface),
            number="singular",
            value=float(reg.fractions[surface]),
        )
        for surface in sorted(reg.fractions)
        if (
            surface not in reg.fraction_plurals
            and not any(ch.isspace() for ch in surface)
        )
    ]
    counted = [
        _Filler(
            f"{count_surface} {plural}",
            singular,
            number="plural",
            value=float(value) * float(reg.fractions[plural]),
        )
        for count_surface, value in sorted(reg.numbers.items())
        for plural, singular in sorted(reg.fraction_plurals.items())
        if (
            count_surface
            and not any(ch.isspace() for ch in count_surface)
            and float(value).is_integer()
            and value >= 0
            and value != 1
            and plural
            and not any(ch.isspace() for ch in plural)
        )
    ]
    return direct + counted


def _counted_fillers(reg: Registry) -> list[_Filler]:
    """Compose declared integer counts with declared noun morphology."""

    counts = [
        int(filler.surface)
        for filler in _number_fillers(reg)
    ]
    noun_pairs = [
        (singular, plural)
        for singular, plural in sorted(reg.singular_to_plural.items())
        if (
            singular
            and plural
            and _is_atomic_noun_surface(singular, reg)
            and _is_atomic_noun_surface(plural, reg)
            and (entry := reg.lexicon.get(singular)) is not None
            and "noun" in entry.senses
        )
    ]
    out: list[_Filler] = []
    for count in counts:
        for singular, plural in noun_pairs:
            noun_surface = singular if count == 1 else plural
            if reg.operators.get(noun_surface) == "*":
                # The ordinary number pass structurally folds
                # "COUNT MULTIPLICATION-MARKER" into one multiplier unit.
                # It can therefore never round-trip through a counted slot,
                # even when the marker is also a declared noun plural.
                continue
            out.append(
                _Filler(
                    surface=f"{count} {noun_surface}",
                    identity=singular,
                    number="singular" if count == 1 else "plural",
                    value=float(count),
                )
            )
        for symbol, singular in sorted(reg.currencies.items()):
            if (
                not symbol
                or any(ch.isspace() for ch in symbol)
                or (entry := reg.lexicon.get(singular)) is None
                or "noun" not in entry.senses
            ):
                continue
            out.append(
                _Filler(
                    surface=f"{symbol}{count}",
                    identity=singular,
                    number="singular" if count == 1 else "plural",
                    value=float(count),
                )
            )
    return out


def _possessed_fillers(reg: Registry, fixtures: _Fixtures) -> list[_Filler]:
    """Compose declared proper-name owners with declared noun surfaces."""

    possessive = reg.lexicon.get("'s")
    contractions = dict(reg.contractions)
    if (
        possessive is None
        or "possessive" not in possessive.senses
        or contractions.get("'s") != "'s"
    ):
        return []
    heads: dict[str, str] = {}
    for singular, entry in sorted(reg.lexicon.items()):
        if (
            not singular
            or not _is_atomic_noun_surface(singular, reg)
            or set(entry.senses) != {"noun"}
            or reg.plural_to_singular.get(singular, singular) != singular
        ):
            continue
        heads[singular] = singular
        plural = reg.singular_to_plural.get(singular)
        if plural and _is_atomic_noun_surface(plural, reg):
            heads[plural] = singular
    return [
        _Filler(
            surface=f"{owner}'s {head}",
            identity=singular,
            owner=owner.casefold(),
            number="singular" if head == singular else "plural",
        )
        for owner in fixtures.names
        for head, singular in sorted(heads.items())
    ]


def _qualified_fillers(reg: Registry) -> list[_Filler]:
    """Compose declared compatible modifiers with noun heads.

    ``type: qualified`` is structural: the ordinary analyzer must merge the
    phrase and retain its qualifier. The compatibility table is the bounded
    project declaration that licenses generated adjective/noun and noun/noun
    combinations; this function never invents an open-ended compound.
    """

    modifiers = [
        *_lexical_fillers(reg, sense="adjective"),
        *_lexical_fillers(reg, sense="noun"),
    ]
    heads = [
        *_lexical_fillers(reg, sense="noun"),
        *[
            _Filler(
                surface=surface,
                identity=singular,
                number="plural",
                kind="noun",
            )
            for surface, singular in sorted(reg.plural_to_singular.items())
            if _is_atomic_noun_surface(surface, reg)
        ],
    ]
    return [
        _Filler(
            surface=f"{modifier.surface} {head.surface}",
            identity=head.identity,
            qualifier=modifier.identity,
            number=head.number,
            kind="noun",
        )
        for modifier in modifiers
        for head in heads
        if modifier.identity != head.identity
        and reg.attribute_applies_to(modifier.identity, head.identity)
    ]


def _counted_qualified_fillers(reg: Registry) -> list[_Filler]:
    """Compose a positive count with one declared qualified noun class."""

    counts = [
        int(filler.value)
        for filler in _number_fillers(reg)
        if isinstance(filler.value, (int, float)) and filler.value > 0
    ]
    classes = sorted(
        {
            (filler.qualifier, filler.identity)
            for filler in _qualified_fillers(reg)
            if filler.qualifier is not None
        }
    )
    out: list[_Filler] = []
    for count in counts:
        for qualifier, identity in classes:
            surface = (
                identity
                if count == 1
                else reg.singular_to_plural.get(identity)
            )
            if not surface or not _is_atomic_noun_surface(surface, reg):
                continue
            out.append(
                _Filler(
                    surface=f"{count} {qualifier} {surface}",
                    identity=identity,
                    qualifier=qualifier,
                    number="singular" if count == 1 else "plural",
                    kind="noun",
                    value=float(count),
                )
            )
    return out


def _attributive_counted_fillers(reg: Registry) -> list[_Filler]:
    """Compose numeric hyphen modifiers from declared measure/holder pairs."""

    counts = [
        int(filler.value)
        for filler in _number_fillers(reg)
        if isinstance(filler.value, (int, float)) and filler.value > 0
    ]
    nouns = _lexical_fillers(reg, sense="noun")
    return [
        _Filler(
            surface=f"{count}-{measure.surface} {holder.surface}",
            identity=holder.identity,
            qualifier=measure.identity,
            number=holder.number,
            kind="noun",
            value=float(count),
        )
        for count in counts
        for measure in nouns
        for holder in nouns
        if measure.identity != holder.identity
        and reg.measure_applies_to_holder(measure.identity, holder.identity)
    ]


def _raw_domain(
    token: MatchToken, reg: Registry, fixtures: _Fixtures
) -> list[_Filler]:
    if token.lit is not None:
        return [_Filler(option, option) for option in token.lit_options]
    if token.opt is not None or token.slot is None:
        return []
    if token.cat is not None:
        if token.attributive_counted:
            return [
                filler
                for filler in _attributive_counted_fillers(reg)
                if reg.word_in_category(filler.identity, token.cat)
            ]
        if token.counted and token.qualified:
            return [
                filler
                for filler in _counted_qualified_fillers(reg)
                if reg.word_in_category(filler.identity, token.cat)
            ]
        if token.counted:
            return [
                filler
                for filler in _counted_fillers(reg)
                if reg.word_in_category(filler.identity, token.cat)
            ]
        if token.possessed:
            return [
                filler
                for filler in _possessed_fillers(reg, fixtures)
                if reg.word_in_category(filler.identity, token.cat)
            ]
        if token.qualified:
            return [
                filler
                for filler in _qualified_fillers(reg)
                if reg.word_in_category(filler.identity, token.cat)
            ]
        root = reg.root_sense(token.cat)
        if root == "noun" and (
            token.number == "plural" or token.generation_all_numbers
        ):
            plural_fillers = [
                _Filler(
                    surface=surface,
                    identity=singular,
                    number="plural",
                )
                for surface, singular in sorted(
                    reg.plural_to_singular.items()
                )
                if surface
                and _is_atomic_noun_surface(surface, reg)
                and reg.word_in_category(singular, token.cat)
            ]
            if token.generation_all_numbers:
                return [
                    *_lexical_fillers(
                        reg,
                        sense=root,
                        category=token.cat,
                        bare_form=token.bare_form,
                        finite_form=token.finite_form,
                        present_participle=token.present_participle,
                        past_participle=token.past_participle,
                    ),
                    *plural_fillers,
                ]
            return plural_fillers
        return _lexical_fillers(
            reg,
            sense=root,
            category=token.cat,
            bare_form=token.bare_form,
            finite_form=token.finite_form,
            present_participle=token.present_participle,
            past_participle=token.past_participle,
        )

    slot_type = token.type
    if slot_type in {"name", "proper_name"}:
        return [
            _Filler(
                name, name.casefold(), number="singular", kind="name"
            )
            for name in fixtures.names
        ]
    if slot_type == "entity":
        return [
            *[
                _Filler(
                    name, name.casefold(), number="singular", kind="name"
                )
                for name in fixtures.names
            ],
            *_lexical_fillers(reg, sense="noun"),
        ]
    if slot_type in {"noun", "common_noun"}:
        return _lexical_fillers(reg, sense="noun")
    if slot_type in {"plural", "bare_plural", "generic_plural"}:
        return [
            _Filler(
                surface=surface,
                identity=singular,
                number="plural",
            )
            for surface, singular in sorted(reg.plural_to_singular.items())
            if _is_atomic_noun_surface(surface, reg)
        ]
    if slot_type == "counted":
        return _counted_fillers(reg)
    if slot_type == "possessed":
        return _possessed_fillers(reg, fixtures)
    if slot_type == "qualified":
        return (
            _attributive_counted_fillers(reg)
            if token.attributive_counted
            else _qualified_fillers(reg)
        )
    if slot_type == "auxiliary":
        return _lexical_fillers(reg, sense="auxiliary")
    if slot_type == "pronoun":
        return _lexical_fillers(reg, sense="pronoun")
    if slot_type == "modal":
        return _lexical_fillers(reg, sense="modal")
    if slot_type == "future_modal":
        # The matcher contract is the union of ordinary factual auxiliaries
        # and the pack-declared future/conditional modal subset. Keeping the
        # realizer on the same union prevents generation from silently
        # exercising only will/would questions.
        return [
            *_lexical_fillers(reg, sense="auxiliary"),
            *_lexical_fillers(
                reg,
                sense="modal",
                category="future_modal",
            ),
        ]
    if slot_type == "verb":
        return _lexical_fillers(
            reg,
            sense="verb",
            bare_form=token.bare_form,
            finite_form=token.finite_form,
            present_participle=token.present_participle,
            past_participle=token.past_participle,
        )
    if slot_type == "nonstate_verb":
        return [
            filler
            for filler in _lexical_fillers(reg, sense="verb")
            if not reg.word_in_category(filler.surface, "non_event_verb")
            and not reg.word_in_category(filler.identity, "non_event_verb")
        ]
    if slot_type == "adjective":
        return _lexical_fillers(reg, sense="adjective")
    if slot_type == "preposition":
        return _lexical_fillers(reg, sense="preposition")
    if slot_type == "word":
        return _lexical_fillers(reg)
    if slot_type == "number":
        fillers = _number_fillers(reg)
        # A bounded numeric slot may sit wholly outside the small lexical
        # number inventory (calendar years are the first example). Include
        # its authored endpoints as deterministic generation witnesses; the
        # ordinary qualifier below still enforces the complete interval.
        endpoints = {
            value
            for value in (token.value_min, token.value_max)
            if value is not None
            and (not token.integer or float(value).is_integer())
        }
        for value in sorted(endpoints):
            rendered = (
                str(int(value)) if float(value).is_integer() else str(value)
            )
            fillers.append(
                _Filler(
                    rendered,
                    rendered,
                    number="singular" if float(value) == 1.0 else "plural",
                    value=float(value),
                )
            )
        return fillers
    if slot_type == "fraction":
        return _fraction_fillers(reg)
    if slot_type == "multiplier":
        return [
            _Filler(surface, surface)
            for surface in sorted(reg.multipliers)
            if not any(ch.isspace() for ch in surface)
        ]
    if slot_type == "nonunit_multiplier":
        return [
            _Filler(surface, surface)
            for surface, value in sorted(reg.multipliers.items())
            if not any(ch.isspace() for ch in surface)
            and float(value) != 1.0
        ]
    if slot_type == "percent":
        return [
            _Filler(f"{filler.surface}%", f"{filler.identity}%")
            for filler in _number_fillers(reg)
        ]
    expected_value_kind = {
        "date": "date",
        "point": "tuple",
        "formula": "formula",
    }.get(slot_type)
    if expected_value_kind is not None:
        fillers: list[_Filler] = []
        for surface in fixtures.values_for(slot_type):
            reading = analyze(surface, reg, tracing=False)
            if len(reading.units) != 1:
                continue
            unit = reading.units[0]
            if unit.features.get("value_kind") != expected_value_kind:
                continue
            fillers.append(
                _Filler(
                    surface=surface,
                    identity=str(
                        unit.features.get("components")
                        or unit.features.get("fold")
                        or surface.casefold()
                    ),
                    kind=slot_type,
                )
            )
        return fillers
    return []


def _expected_indefinite_article(
    following: _Filler,
    reg: Registry,
) -> str | None:
    """Choose the English indefinite allomorph for one generated surface.

    The ordinary spelling heuristic is grammar, while pronunciation exceptions
    remain pack data.  Returning ``None`` leaves non-alphabetic surfaces alone
    rather than pretending their spoken form is known.
    """

    if _filler_in_category(following, "indefinite_an_exception", reg):
        return "an"
    if _filler_in_category(following, "indefinite_a_exception", reg):
        return "a"
    initial = next(
        (char.casefold() for char in following.surface if char.isalpha()),
        None,
    )
    if initial is None:
        return None
    return "an" if initial in "aeiou" else "a"


def _qualify_domain(
    token: MatchToken,
    fillers: list[_Filler],
    reg: Registry,
    *,
    enforce_common_noun_cat: bool = True,
) -> list[_Filler]:
    """Apply structural token qualifiers to an already selected word domain."""

    if enforce_common_noun_cat and token.common_noun_cat is not None:
        fillers = [
            filler
            for filler in fillers
            if filler.kind != "noun"
            or _filler_in_category(filler, token.common_noun_cat, reg)
        ]
    if token.qualifier_cat is not None:
        fillers = [
            filler
            for filler in fillers
            if filler.qualifier is not None
            and reg.word_in_category(filler.qualifier, token.qualifier_cat)
        ]
    if token.single_word:
        fillers = [
            filler
            for filler in fillers
            if not any(ch.isspace() for ch in filler.surface)
        ]
    if token.fraction_within_whole:
        fillers = [
            filler
            for filler in fillers
            if isinstance(filler.value, (int, float))
            and 0.0 <= float(filler.value) <= 1.0
        ]
    if token.word_fraction_within_whole:
        # `_fraction_fillers` realizes word fractions, never percentages.
        # Percentage input remains matcher-valid above one, but generated
        # word-fraction comparisons use a natural magnitude.
        fillers = [
            filler
            for filler in fillers
            if isinstance(filler.value, (int, float))
            and 0.0 <= float(filler.value) <= 1.0
        ]
    if token.fraction_positive:
        fillers = [
            filler
            for filler in fillers
            if isinstance(filler.value, (int, float))
            and float(filler.value) > 0.0
        ]
    if token.value_min is not None:
        fillers = [
            filler
            for filler in fillers
            if isinstance(filler.value, (int, float))
            and float(filler.value) >= token.value_min
        ]
    if token.value_max is not None:
        fillers = [
            filler
            for filler in fillers
            if isinstance(filler.value, (int, float))
            and float(filler.value) <= token.value_max
        ]
    if token.generation_explicit_unit_fraction:
        unit_surface = min(
            surface
            for surface, value in reg.numbers.items()
            if float(value) == 1.0 and not any(ch.isspace() for ch in surface)
        )
        fillers = [
            (
                _Filler(
                    surface=f"{unit_surface} {filler.surface}",
                    identity=filler.identity,
                    number=filler.number,
                    value=filler.value,
                )
                if filler.number == "singular"
                else filler
            )
            for filler in fillers
        ]
    if token.referential:
        articles = [
            filler.surface
            for filler in _lexical_fillers(
                reg, sense="article", category="definite_article"
            )
        ]
        referential: list[_Filler] = []
        for filler in fillers:
            entry = reg.lexicon.get(filler.identity)
            is_noun = entry is not None and "noun" in entry.senses
            if not is_noun or filler.owner is not None:
                referential.append(filler)
                continue
            # A possessive determiner may license the bare head. The
            # constraint filter keeps this variant only when the immediately
            # preceding chosen filler is such a determiner.
            referential.append(
                _Filler(
                    surface=filler.surface,
                    identity=filler.identity,
                    owner=filler.owner,
                    number=filler.number,
                    label=filler.label,
                    qualifier=filler.qualifier,
                    reference_form="bare",
                    kind=filler.kind,
                )
            )
            referential.extend(
                _Filler(
                    surface=f"{article} {filler.surface}",
                    identity=filler.identity,
                    owner=filler.owner,
                    number=filler.number,
                    label=filler.label,
                    qualifier=filler.qualifier,
                    reference_form="definite",
                    kind=filler.kind,
                )
                for article in articles
            )
        fillers = referential
    if token.determinerless_category is not None:
        fillers = [
            filler
            for filler in fillers
            if not _filler_in_category(
                filler, token.determinerless_category, reg
            )
            or filler.reference_form in {None, "bare"}
        ]
    if token.number is None:
        return fillers
    return [
        filler for filler in fillers if filler.number == token.number
    ]


def _domain(
    token: MatchToken, reg: Registry, fixtures: _Fixtures
) -> list[_Filler]:
    key = (
        reg.fingerprint,
        fixtures.cache_key,
        token.model_dump_json(exclude_none=True),
    )
    with _CACHE_LOCK:
        cached = _DOMAIN_CACHE.get(key)
        if cached is not None:
            _DOMAIN_CACHE.move_to_end(key)
            return cached
    domain = _qualify_domain(token, _raw_domain(token, reg, fixtures), reg)
    with _CACHE_LOCK:
        _DOMAIN_CACHE[key] = domain
        _DOMAIN_CACHE.move_to_end(key)
        while len(_DOMAIN_CACHE) > _MAX_DOMAIN_CACHE_ENTRIES:
            _DOMAIN_CACHE.popitem(last=False)
    return domain


def _broader_lexical_domain(
    token: MatchToken,
    reg: Registry,
    fixtures: _Fixtures,
) -> tuple[list[_Filler], str, str] | None:
    """Return a structurally compatible domain beyond one lexical gate.

    Boundary generation widens category-gated slots only to the category's
    declared root sense. It never crosses part of speech, invents vocabulary,
    or discards counted/possessed/number/referential morphology. Two narrow
    typed subsets have equally explicit parents: ``nonstate_verb`` widens to
    ``verb`` and ``future_modal`` widens to ``modal``.
    """

    key = (
        reg.fingerprint,
        fixtures.cache_key,
        token.model_dump_json(exclude_none=True),
    )
    with _CACHE_LOCK:
        if key in _BOUNDARY_DOMAIN_CACHE:
            cached = _BOUNDARY_DOMAIN_CACHE[key]
            _BOUNDARY_DOMAIN_CACHE.move_to_end(key)
            return cached

    requirement: str
    broader_domain: str
    fillers: list[_Filler]
    if token.common_noun_cat is not None:
        requirement = f"common-noun category {token.common_noun_cat!r}"
        broader_domain = "root sense 'noun'"
        fillers = _lexical_fillers(reg, sense="noun")
    elif token.cat is not None:
        root = reg.root_sense(token.cat)
        requirement = f"category {token.cat!r}"
        broader_domain = f"root sense {root!r}"
        if token.attributive_counted:
            fillers = _attributive_counted_fillers(reg)
        elif token.counted and token.qualified:
            fillers = _counted_qualified_fillers(reg)
        elif token.counted:
            fillers = _counted_fillers(reg)
        elif token.possessed:
            fillers = _possessed_fillers(reg, fixtures)
        elif token.qualified:
            fillers = _qualified_fillers(reg)
        elif root == "noun" and token.number == "plural":
            fillers = [
                _Filler(
                    surface=surface,
                    identity=singular,
                    number="plural",
                )
                for surface, singular in sorted(
                    reg.plural_to_singular.items()
                )
                if _is_atomic_noun_surface(surface, reg)
            ]
        else:
            fillers = _lexical_fillers(
                reg,
                sense=root,
                bare_form=token.bare_form,
                finite_form=token.finite_form,
                present_participle=token.present_participle,
                past_participle=token.past_participle,
            )
    elif token.type == "nonstate_verb":
        requirement = "type 'nonstate_verb'"
        broader_domain = "type 'verb'"
        fillers = _lexical_fillers(reg, sense="verb")
    elif token.type == "future_modal":
        requirement = "type 'future_modal'"
        broader_domain = "type 'modal'"
        fillers = _lexical_fillers(reg, sense="modal")
    else:
        result = None
        with _CACHE_LOCK:
            _BOUNDARY_DOMAIN_CACHE[key] = result
            _BOUNDARY_DOMAIN_CACHE.move_to_end(key)
            while len(_BOUNDARY_DOMAIN_CACHE) > _MAX_DOMAIN_CACHE_ENTRIES:
                _BOUNDARY_DOMAIN_CACHE.popitem(last=False)
        return result

    strict = set(_domain(token, reg, fixtures))
    outside = [
        filler
        for filler in _qualify_domain(
            token,
            fillers,
            reg,
            enforce_common_noun_cat=False,
        )
        if filler not in strict
    ]
    result = (
        (outside, requirement, broader_domain)
        if outside
        else None
    )
    with _CACHE_LOCK:
        _BOUNDARY_DOMAIN_CACHE[key] = result
        _BOUNDARY_DOMAIN_CACHE.move_to_end(key)
        while len(_BOUNDARY_DOMAIN_CACHE) > _MAX_DOMAIN_CACHE_ENTRIES:
            _BOUNDARY_DOMAIN_CACHE.popitem(last=False)
    return result


def _absent_categories(rule: PatternRule) -> tuple[str, ...]:
    """Return the sentence-wide category exclusions declared by one rule."""

    return tuple(
        dict.fromkeys(
            pred.absent["cat"]
            for pred in _generation_predicates(rule)
            if pred.absent is not None
        )
    )


def _outside_categories(
    filler: _Filler,
    categories: tuple[str, ...],
    reg: Registry,
) -> bool:
    """Mirror the matcher's analyzed-lemma category test for one filler."""

    return all(
        not reg.word_in_category(filler.identity, category)
        for category in categories
    )


def _slot_category_exclusions(
    rule: PatternRule,
) -> tuple[tuple[str, str], ...]:
    """Return the per-slot category refusals declared by one rule."""

    exclusions: list[tuple[str, str]] = []
    for pred in _generation_predicates(rule):
        if pred.slot_not_category is None:
            continue
        slot = pred.slot_not_category.get("slot")
        category = pred.slot_not_category.get("cat")
        if slot is not None and category is not None:
            exclusions.append((slot, category))
    return tuple(exclusions)


def _entity_owner_distinctions(
    rule: PatternRule,
) -> tuple[tuple[str, str], ...]:
    """Return ordinary-entity/possessed-owner inequality constraints."""

    return tuple(
        (
            pred.distinct_from_owner.entity,
            pred.distinct_from_owner.possessed,
        )
        for pred in _generation_predicates(rule)
        if pred.distinct_from_owner is not None
    )


def _outside_slot_categories(
    filler: _Filler,
    slot: str | None,
    exclusions: tuple[tuple[str, str], ...] | list[tuple[str, str]],
    reg: Registry,
) -> bool:
    """Apply the matcher's slot-local category refusals to one filler."""

    return all(
        slot != excluded_slot
        or (
            not reg.word_in_category(filler.surface.casefold(), category)
            and not reg.word_in_category(filler.identity, category)
        )
        for excluded_slot, category in exclusions
    )


def _unbound_optional_paths(
    rule: PatternRule,
    tokens: list[MatchToken],
) -> dict[tuple[int, ...], tuple[str, ...]]:
    """Map each forced-omitted optional branch to its sentinel slots."""

    names = {
        name
        for pred in _generation_predicates(rule)
        for name in (pred.unbound or ())
    }
    grouped: dict[tuple[int, ...], list[str]] = {}
    for _, token, optional_ancestors in _leaf_tokens(tokens):
        if token.slot not in names or not optional_ancestors:
            continue
        nearest = optional_ancestors[-1]
        grouped.setdefault(nearest, []).append(token.slot)
    return {
        path: tuple(dict.fromkeys(path_names))
        for path, path_names in grouped.items()
    }


def _measure_key(
    filler: _Filler,
) -> tuple[str, str | None, str | None]:
    """Return the matcher's exact distinct-measure comparison key."""

    return filler.identity, filler.label, filler.qualifier


def _proper_name_measure_allowed(
    measure: _Filler,
    *,
    attribute: _Filler | None = None,
    allow_proper_name: bool,
    measure_categories: tuple[str, ...],
    reg: Registry,
) -> bool:
    """Whether a declared measure permits the proper-name holder shortcut."""

    if not allow_proper_name or not measure_categories:
        return allow_proper_name
    if attribute is None:
        return any(
            _filler_in_category(measure, category, reg)
            for category in measure_categories
        )
    route_categories = {
        noun_category
        for _, noun_category in reg.attribute_compatibility_pairs(
            attribute.identity, measure.identity
        )
    }
    return any(
        reg.category_routes_overlap(route_category, permitted_category)
        for route_category in route_categories
        for permitted_category in measure_categories
    )


def _scoped_filler_polarity(
    filler: _Filler, scope: str, reg: Registry
) -> int | None:
    """Declared filler polarity below one category scope, if any."""

    best_depth, best = -1, None
    for word in {filler.identity, filler.surface.casefold()}:
        for tag in reg.word_categories.get(word, ()):
            chain = reg.cat_ancestors(tag)
            if scope not in chain:
                continue
            for depth, category in enumerate(reversed(chain)):
                if (
                    category in reg.category_polarity
                    and depth > best_depth
                ):
                    best_depth = depth
                    best = reg.category_polarity[category]
    return best


def _proportional_delta_requirements(
    rule: PatternRule,
) -> tuple[tuple[str, str, str], ...]:
    """Return fraction/direction/category triples declared by one rule."""

    return tuple(
        (
            pred.proportional_delta_compatible.fraction,
            pred.proportional_delta_compatible.direction,
            pred.proportional_delta_compatible.direction_cat,
        )
        for pred in _generation_predicates(rule)
        if pred.proportional_delta_compatible is not None
    )


def _distinct_measure_groups(rule: PatternRule) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(pred.distinct_measure)
        for pred in _generation_predicates(rule)
        if pred.distinct_measure is not None
    )


def _category_membership_requirements(
    rule: PatternRule,
) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Return slot groups that must agree on one category membership."""

    return tuple(
        (tuple(pred.same_category_membership.slots),
         pred.same_category_membership.cat)
        for pred in _generation_predicates(rule)
        if pred.same_category_membership is not None
    )


def _category_membership_assignment_exists(
    requirements: tuple[tuple[tuple[str, ...], str], ...],
    domains: dict[str, list[_Filler]],
    reg: Registry,
) -> bool:
    """Whether each agreement group has at least one shared truth value."""

    return all(
        bool(
            set.intersection(
                *(
                    {
                        _filler_in_category(filler, category, reg)
                        for filler in domains.get(slot_name, ())
                    }
                    for slot_name in slots
                )
            )
        )
        for slots, category in requirements
    )


def _measure_assignment_exists(
    groups: tuple[tuple[str, ...], ...],
    domains: dict[str, list[_Filler]],
    fixed: dict[str, _Filler] | None = None,
) -> bool:
    """Find one assignment whose measure keys differ within every group."""

    fixed = fixed or {}
    involved = {
        name for group in groups for name in group
    }
    if any(len(group) != len(set(group)) for group in groups):
        return False
    key_domains = {
        name: (
            (_measure_key(fixed[name]),)
            if name in fixed
            else tuple(
                dict.fromkeys(
                    _measure_key(filler) for filler in domains[name]
                )
            )
        )
        for name in involved
        if name in domains
    }
    if set(key_domains) != involved or any(
        not values for values in key_domains.values()
    ):
        return False
    return _measure_key_assignment_exists(
        groups,
        key_domains,
        {name: _measure_key(filler) for name, filler in fixed.items()},
    )


def _measure_key_assignment_exists(
    groups: tuple[tuple[str, ...], ...],
    key_domains: dict[
        str, tuple[tuple[str, str | None, str | None], ...]
    ],
    fixed: dict[str, tuple[str, str | None, str | None]] | None = None,
) -> bool:
    """Check distinct-measure feasibility over already deduplicated keys."""

    fixed = fixed or {}
    effective_domains = {
        name: (fixed[name],) if name in fixed else values
        for name, values in key_domains.items()
    }
    ordered = sorted(
        effective_domains,
        key=lambda name: (len(effective_domains[name]), name),
    )
    chosen: dict[str, tuple[str, str | None, str | None]] = {}

    def assign(index: int) -> bool:
        if index == len(ordered):
            return True
        name = ordered[index]
        for key in effective_domains[name]:
            if any(
                key in {
                    chosen[other]
                    for other in group
                    if other != name and other in chosen
                }
                for group in groups
                if name in group
            ):
                continue
            chosen[name] = key
            if assign(index + 1):
                return True
            chosen.pop(name)
        return False

    return assign(0)


def _resolve_locked_fillers(
    tokens: list[MatchToken],
    reg: Registry,
    fixtures: _Fixtures,
    locked_bindings: dict[str, str],
    identity_bindings: dict[str, str],
) -> dict[str, _Filler]:
    """Resolve surface/identity locks to realization filler metadata."""

    resolved: dict[str, _Filler] = {}
    for slot_name in locked_bindings.keys() | identity_bindings.keys():
        surface = locked_bindings.get(slot_name)
        identity = identity_bindings.get(slot_name)
        matches = [
            filler
            for _, token, _ in _leaf_tokens(tokens)
            if token.slot == slot_name
            for filler in _domain(token, reg, fixtures)
            if (
                surface is None
                or filler.surface.casefold() == surface.casefold()
            )
            if (
                identity is None
                or filler.identity.casefold() == identity.casefold()
            )
        ]
        if not matches:
            continue
        keys = {_measure_key(filler) for filler in matches}
        if len(keys) != 1:
            # An identity-only link may intentionally leave count, qualifier,
            # owner, or label open for this realization. The ordinary domain
            # filter below will still enforce the identity when the slot is
            # chosen; it simply cannot be treated as one pre-resolved filler.
            if surface is None and identity is not None:
                continue
            raise GenerationError(
                f"locked binding {slot_name!r}={surface!r} has ambiguous "
                "measure metadata"
            )
        resolved[slot_name] = matches[0]
    return resolved


def _rule_blockers(
    rule: PatternRule, reg: Registry, fixtures: _Fixtures
) -> tuple[str, ...]:
    blockers: list[str] = []
    if rule.generation == "safety":
        blockers.append("declared non-generative safety consumer")
    elif rule.generation == "reader-only":
        blockers.append("declared non-generative reader-only rule")
    if rule.phase != "read":
        blockers.append("only phase: read rules are currently supported")
    seq = _flat_sentence(rule)
    if seq is None:
        blockers.append(
            "only flat single-sentence premise patterns are currently supported"
        )
    else:
        absent_categories = _absent_categories(rule)
        slot_category_exclusions = _slot_category_exclusions(rule)
        safe_domains: dict[str, list[_Filler]] = {}

        def safe_domain(token: MatchToken) -> list[_Filler]:
            key = token.model_dump_json(exclude_none=True)
            if key not in safe_domains:
                safe_domains[key] = [
                    filler
                    for filler in _domain(token, reg, fixtures)
                    if _outside_categories(filler, absent_categories, reg)
                    and _outside_slot_categories(
                        filler,
                        token.slot,
                        slot_category_exclusions,
                        reg,
                    )
                ]
            return safe_domains[key]

        for _, token, _ in _leaf_tokens(seq):
            token_blockers = _token_blockers(token, reg)
            blockers.extend(token_blockers)
            domain = _domain(token, reg, fixtures)
            if not token_blockers and not domain:
                label = token.slot or repr(token.lit)
                blockers.append(f"no project-backed filler exists for {label}")
            elif (
                not token_blockers
                and absent_categories
                and not safe_domain(token)
            ):
                label = token.slot or repr(token.lit)
                rendered = ", ".join(repr(cat) for cat in absent_categories)
                blockers.append(
                    f"no project-backed filler remains for {label} outside "
                    f"absent categories {rendered}"
                )
        tokens_by_slot = {
            token.slot: token
            for _, token, _ in _leaf_tokens(seq)
            if token.slot is not None
        }
        slot_occurrences: dict[
            str,
            list[tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]],
        ] = {}
        for path, token, optional_ancestors in _leaf_tokens(seq):
            if token.slot is not None:
                slot_occurrences.setdefault(token.slot, []).append(
                    (path, optional_ancestors)
                )
        for pred in _generation_predicates(rule):
            if pred.unbound is None:
                continue
            for slot_name in pred.unbound:
                occurrences = slot_occurrences.get(slot_name, ())
                if not occurrences:
                    blockers.append(
                        f"unbound slot {slot_name!r} is not declared by the pattern"
                    )
                elif any(not ancestors for _, ancestors in occurrences):
                    blockers.append(
                        f"unbound slot {slot_name!r} is not confined to "
                        "optional structure"
                    )
        distinct_measure_groups = _distinct_measure_groups(rule)
        if distinct_measure_groups:
            measure_slots = {
                name for group in distinct_measure_groups for name in group
            }
            missing = sorted(measure_slots - set(tokens_by_slot))
            if missing:
                blockers.append(
                    "distinct_measure slots are not declared by the pattern: "
                    + ", ".join(repr(name) for name in missing)
                )
            elif not _measure_assignment_exists(
                distinct_measure_groups,
                {
                    name: safe_domain(tokens_by_slot[name])
                    for name in measure_slots
                },
            ):
                rendered = "; ".join(
                    "/".join(group) for group in distinct_measure_groups
                )
                blockers.append(
                    "no project-backed distinct measure assignment exists "
                    f"for {rendered}"
                )
        category_membership_requirements = (
            _category_membership_requirements(rule)
        )
        if category_membership_requirements:
            membership_slots = {
                name
                for group, _ in category_membership_requirements
                for name in group
            }
            missing = sorted(membership_slots - set(tokens_by_slot))
            if missing:
                blockers.append(
                    "category-membership agreement slots are not declared "
                    "by the pattern: "
                    + ", ".join(repr(name) for name in missing)
                )
            elif not _category_membership_assignment_exists(
                category_membership_requirements,
                {
                    name: safe_domain(tokens_by_slot[name])
                    for name in membership_slots
                },
                reg,
            ):
                rendered = "; ".join(
                    f"{'/'.join(group)} in {category!r}"
                    for group, category in category_membership_requirements
                )
                blockers.append(
                    "no project-backed category-membership assignment "
                    f"exists for {rendered}"
                )
        for pred in _generation_predicates(rule):
            if pred.category_contains is None:
                continue
            containment = pred.category_contains
            role_names = (containment.collection, *containment.members)
            role_tokens = [tokens_by_slot.get(name) for name in role_names]
            if any(token is None for token in role_tokens):
                blockers.append(
                    "category-containment slots are not declared by the pattern: "
                    + ", ".join(repr(name) for name in role_names)
                )
                continue
            role_domains = [
                safe_domain(token)
                for token in role_tokens
                if token is not None
            ]
            if not any(
                all(
                    _filler_category_term_contains(
                        assignment[0], member, reg
                    )
                    for member in assignment[1:]
                )
                for assignment in product(*role_domains)
            ):
                blockers.append(
                    "no project-backed category/member assignment exists "
                    f"for {'/'.join(role_names)}"
                )
        for pred in _generation_predicates(rule):
            if pred.attribute_compatible is None:
                continue
            attribute_name = pred.attribute_compatible.attribute
            noun_name = pred.attribute_compatible.noun
            attribute_token = tokens_by_slot.get(attribute_name)
            noun_token = tokens_by_slot.get(noun_name)
            if (
                attribute_token is None
                or noun_token is None
                or not any(
                    reg.attribute_applies_to(attribute.identity, noun.identity)
                    for attribute in safe_domain(attribute_token)
                    for noun in safe_domain(noun_token)
                )
            ):
                blockers.append(
                    "no project-backed adjective/noun compatibility exists "
                    f"for {attribute_name}/{noun_name}"
                )
        for pred in _generation_predicates(rule):
            if pred.modifier_host_compatible is None:
                continue
            modifier_name = pred.modifier_host_compatible.modifier
            host_name = pred.modifier_host_compatible.host
            object_name = pred.modifier_host_compatible.object
            modifier_token = tokens_by_slot.get(modifier_name)
            host_token = tokens_by_slot.get(host_name)
            object_token = (
                tokens_by_slot.get(object_name)
                if object_name is not None
                else None
            )
            if (
                modifier_token is None
                or host_token is None
                or (object_name is not None and object_token is None)
            ):
                blockers.append(
                    "modifier-host compatibility names undeclared pattern "
                    f"slots {modifier_name}/{host_name}"
                    + (f"/{object_name}" if object_name is not None else "")
                )
                continue
            modifier_domain = safe_domain(modifier_token)
            host_domain = safe_domain(host_token)
            object_domain = (
                safe_domain(object_token) if object_token is not None else [None]
            )
            if not any(
                (
                    not reg.modifier_has_host_boundary(modifier.identity)
                    or reg.modifier_applies_to_host(
                        modifier.identity, host.identity
                    )
                )
                and (
                    object_ is None
                    or reg.modifier_attaches_to(
                        modifier.identity, object_.identity, host.identity
                    )
                )
                for modifier in modifier_domain
                for host in host_domain
                for object_ in object_domain
            ):
                blockers.append(
                    "no project-backed modifier/host compatibility exists "
                    f"for {modifier_name}/{host_name}"
                )
        for pred in _generation_predicates(rule):
            if pred.adverb_verb_compatible is None:
                continue
            adverb_name = pred.adverb_verb_compatible.adverb
            verb_name = pred.adverb_verb_compatible.verb
            adverb_token = tokens_by_slot.get(adverb_name)
            verb_token = tokens_by_slot.get(verb_name)
            if (
                adverb_token is None
                or verb_token is None
                or not any(
                    reg.adverb_applies_to_verb(
                        adverb.surface.casefold(), verb.surface.casefold()
                    )
                    for adverb in safe_domain(adverb_token)
                    for verb in safe_domain(verb_token)
                )
            ):
                blockers.append(
                    "no project-backed adverb/verb compatibility exists "
                    f"for {adverb_name}/{verb_name}"
                )
        for pred in _generation_predicates(rule):
            if pred.polarity_compatible is None:
                continue
            pairs = tuple(
                zip(
                    pred.polarity_compatible.slots,
                    pred.polarity_compatible.categories,
                    strict=True,
                )
            )
            pair_tokens = [
                tokens_by_slot.get(slot_name)
                for slot_name, _ in pairs
            ]
            has_omittable_slot = any(
                all(ancestors for _, ancestors in slot_occurrences[slot_name])
                for slot_name, _ in pairs
            )
            if (
                any(token is None for token in pair_tokens)
                or (
                    not has_omittable_slot
                    and not any(
                        len(
                            {
                                polarity
                                for filler, (_, category) in zip(
                                    fillers, pairs, strict=True
                                )
                                if (
                                    polarity := _scoped_filler_polarity(
                                        filler, category, reg
                                    )
                                )
                                is not None
                            }
                        )
                        <= 1
                        for fillers in product(
                            *(
                                safe_domain(token)
                                for token in pair_tokens
                                if token is not None
                            )
                        )
                    )
                )
            ):
                blockers.append(
                    "no project-backed scoped polarity assignment exists "
                    f"for {'/'.join(slot for slot, _ in pairs)}"
                )
        for pred in _generation_predicates(rule):
            if pred.proportional_delta_compatible is None:
                continue
            compatibility = pred.proportional_delta_compatible
            fraction_token = tokens_by_slot.get(compatibility.fraction)
            direction_token = tokens_by_slot.get(compatibility.direction)

            def delta_ok(fraction: _Filler, direction: _Filler) -> bool:
                polarity = _scoped_filler_polarity(
                    direction, compatibility.direction_cat, reg
                )
                return proportional_delta_is_compatible(
                    fraction.value, polarity
                )

            if (
                fraction_token is None
                or direction_token is None
                or not any(
                    delta_ok(fraction, direction)
                    for fraction in safe_domain(fraction_token)
                    for direction in safe_domain(direction_token)
                )
            ):
                blockers.append(
                    "no project-backed proportional delta assignment exists "
                    f"for {compatibility.fraction}/"
                    f"{compatibility.direction}"
                )
        for pred in _generation_predicates(rule):
            if pred.verb_role_compatible is None:
                continue
            compatibility = pred.verb_role_compatible
            verb_token = tokens_by_slot.get(compatibility.verb)
            role_tokens = [
                tokens_by_slot.get(role)
                for role in compatibility.roles
            ]

            def role_ok(verb: _Filler, role: _Filler) -> bool:
                if not _filler_in_category(
                    verb, compatibility.verb_cat, reg
                ):
                    return True
                if compatibility.role_cat is not None:
                    return (
                        role.kind == "name"
                        or (
                            compatibility.allow_plural_class
                            and role.number == "plural"
                        )
                        or _filler_in_category(
                            role, compatibility.role_cat, reg
                        )
                    )
                assert compatibility.excluded_role_cat is not None
                return not _filler_in_category(
                    role, compatibility.excluded_role_cat, reg
                )

            if (
                verb_token is None
                or any(token is None for token in role_tokens)
                or not any(
                    all(
                        any(
                            role_ok(verb, role)
                            for role in safe_domain(role_token)
                        )
                        for role_token in role_tokens
                        if role_token is not None
                    )
                    for verb in safe_domain(verb_token)
                )
            ):
                blockers.append(
                    "no project-backed verb/role compatibility exists for "
                    f"{compatibility.verb}/"
                    f"{'/'.join(compatibility.roles)}"
                )
        for pred in _generation_predicates(rule):
            if pred.verb_roles_compatible is None:
                continue
            compatibility = pred.verb_roles_compatible
            verb_token = tokens_by_slot.get(compatibility.verb)
            role_tokens = {
                slot: tokens_by_slot.get(slot)
                for slots in compatibility.roles.values()
                for slot in slots
            }

            def verb_has_possible_frame(verb: _Filler) -> bool:
                frames = reg.selectional_frames(verb.identity)
                if compatibility.frame_categories:
                    frames = tuple(
                        (category, frame)
                        for category, frame in frames
                        if any(
                            trigger in reg.cat_ancestors(category)
                            for trigger in compatibility.frame_categories
                        )
                    )
                if not frames:
                    return not compatibility.require_declared_frame
                for frame_category, frame in frames:
                    if not set(compatibility.roles) <= set(frame):
                        continue
                    if all(
                        token is not None
                        and any(
                            _filler_satisfies_selectional_role(
                                role,
                                frame[semantic_role],
                                reg.selectional_role_number(
                                    frame_category, semantic_role
                                ),
                                slot,
                                compatibility,
                                reg,
                            )
                            for role in safe_domain(token)
                        )
                        for semantic_role, slots in compatibility.roles.items()
                        for slot in slots
                        for token in (role_tokens[slot],)
                    ):
                        return True
                return False

            if (
                verb_token is None
                or any(token is None for token in role_tokens.values())
                or not any(
                    verb_has_possible_frame(verb)
                    for verb in safe_domain(verb_token)
                )
            ):
                blockers.append(
                    "no project-backed category-owned verb role frame exists "
                    f"for {compatibility.verb}/"
                    f"{'/'.join(role_tokens)}"
                )
        for pred in _generation_predicates(rule):
            if pred.measure_holder_compatible is None:
                continue
            compatibility = pred.measure_holder_compatible
            measure_token = tokens_by_slot.get(compatibility.measure)
            attribute_token = (
                tokens_by_slot.get(compatibility.attribute)
                if compatibility.attribute is not None
                else None
            )
            holder_tokens = [
                tokens_by_slot.get(holder)
                for holder in compatibility.holders
            ]

            def holder_ok(
                measure: _Filler,
                holder: _Filler,
                attribute: _Filler | None,
            ) -> bool:
                if (
                    compatibility.when_declared
                    and not reg.measure_has_holder_boundary(measure.identity)
                ):
                    return True
                return (
                    holder.kind == "name"
                    and _proper_name_measure_allowed(
                        measure,
                        attribute=attribute,
                        allow_proper_name=compatibility.allow_proper_name,
                        measure_categories=tuple(
                            compatibility.proper_name_measure_categories
                        ),
                        reg=reg,
                    )
                ) or reg.measure_applies_to_holder(
                    measure.identity,
                    holder.identity,
                    attribute.identity if attribute is not None else None,
                )

            if (
                measure_token is None
                or (
                    compatibility.attribute is not None
                    and attribute_token is None
                )
                or any(token is None for token in holder_tokens)
                or not any(
                    all(
                        any(
                            holder_ok(measure, holder, attribute)
                            for holder in safe_domain(holder_token)
                        )
                        for holder_token in holder_tokens
                        if holder_token is not None
                    )
                    for measure in safe_domain(measure_token)
                    for attribute in (
                        safe_domain(attribute_token)
                        if attribute_token is not None
                        else [None]
                    )
                )
            ):
                blockers.append(
                    "no project-backed measure/holder compatibility exists "
                    f"for {compatibility.measure}/"
                    f"{'/'.join(compatibility.holders)}"
                )
        for pred in _generation_predicates(rule):
            if pred.distinct_from_owner is None:
                continue
            entity_name = pred.distinct_from_owner.entity
            possessed_name = pred.distinct_from_owner.possessed
            entity_token = tokens_by_slot.get(entity_name)
            possessed_token = tokens_by_slot.get(possessed_name)
            if (
                entity_token is None
                or possessed_token is None
                or not any(
                    entity.identity != possessed.owner
                    for entity in safe_domain(entity_token)
                    for possessed in safe_domain(possessed_token)
                )
            ):
                blockers.append(
                    "no project-backed distinct entity/owner assignment "
                    f"exists for {entity_name}/{possessed_name}"
                )
        for pred in _generation_predicates(rule):
            if pred.slot_not_category is None:
                continue
            slot_name = pred.slot_not_category.get("slot")
            category = pred.slot_not_category.get("cat")
            token = tokens_by_slot.get(slot_name or "")
            if (
                token is None
                or category is None
                or not any(
                    not reg.word_in_category(filler.surface.casefold(), category)
                    and not reg.word_in_category(filler.identity, category)
                    for filler in safe_domain(token)
                )
            ):
                blockers.append(
                    "no project-backed filler remains for "
                    f"{slot_name!r} outside category {category!r}"
                )
    blockers.extend(_where_blocker(rule))
    if rule.generation_context is not None:
        for position, contexts in (
            ("before", rule.generation_context.before),
            ("after", rule.generation_context.after),
        ):
            for index, context in enumerate(contexts):
                contextual_rule = PatternRule(
                    id=f"{rule.id}#context-{position}-{index}",
                    match={"sentence": context.sentence},
                    where=context.where,
                )
                blockers.extend(
                    f"context {position} {index}: {blocker}"
                    for blocker in _rule_blockers(
                        contextual_rule, reg, fixtures
                    )
                )
    return tuple(dict.fromkeys(blockers))


def list_rule_availability(project: Project) -> list[RuleAvailability]:
    """List every premise rule, including every unsupported one."""

    fixtures = _load_fixtures(project.root)
    key = (project.registry.fingerprint, fixtures.cache_key)
    with _CACHE_LOCK:
        cached = _AVAILABILITY_CACHE.get(key)
        if cached is not None:
            _AVAILABILITY_CACHE.move_to_end(key)
            return list(cached)
    availability = tuple(
        RuleAvailability(
            id=rule.id,
            description=rule.description,
            supported=not (blockers := _rule_blockers(rule, project.registry, fixtures)),
            blockers=blockers,
            generation=rule.generation,
        )
        for rule in project.registry.rules
    )
    with _CACHE_LOCK:
        _AVAILABILITY_CACHE[key] = availability
        _AVAILABILITY_CACHE.move_to_end(key)
        while len(_AVAILABILITY_CACHE) > _MAX_AVAILABILITY_CACHE_ENTRIES:
            _AVAILABILITY_CACHE.popitem(last=False)
    return list(availability)


def _constraint_groups(
    rule: PatternRule,
) -> tuple[
    list[set[str]],
    list[set[str]],
    list[set[str]],
    list[set[str]],
    list[tuple[tuple[str, str], ...]],
    list[set[str]],
    list[set[str]],
    list[tuple[str, str, str]],
    list[tuple[str, str, str, bool]],
    list[tuple[str, str, str]],
    list[set[str]],
    tuple[tuple[str, ...], ...],
    list[tuple[str, str, str | None]],
    list[tuple[str, str]],
    list[
        tuple[
            str,
            tuple[str, ...],
            str,
            str | None,
            str | None,
            bool,
            bool,
        ]
    ],
    list[VerbRolesCompatibilityPredicate],
    list[tuple[str, tuple[str, ...], bool, tuple[str, ...], bool]],
    list[tuple[str, str]],
    tuple[str, ...],
]:
    same: list[set[str]] = []
    same_surface: list[set[str]] = []
    same_number: list[set[str]] = []
    number_compatible: list[set[str]] = []
    polarity_compatible: list[tuple[tuple[str, str], ...]] = []
    distinct: list[set[str]] = []
    category_nonoverlap: list[set[str]] = []
    category_containment: list[tuple[str, tuple[str, ...]]] = []
    distinct_owner: list[set[str]] = []
    bound_type_requirements: list[tuple[str, str, str]] = []
    bound_category_requirements: list[tuple[str, str, str, bool]] = []
    bound_category_exclusions: list[tuple[str, str, str]] = []
    category_bound_requirements: list[tuple[str, str, str]] = []
    bound_form_requirements: list[tuple[str, str, str]] = []
    same_presence: list[set[str]] = []
    attribute_pairs: list[tuple[str, str]] = []
    adverb_verb_pairs: list[tuple[str, str]] = []
    modifier_host_pairs: list[tuple[str, str, str | None]] = []
    verb_role_requirements: list[
        tuple[
            str,
            tuple[str, ...],
            str,
            str | None,
            str | None,
            bool,
            bool,
        ]
    ] = []
    verb_selectional_requirements: list[
        VerbRolesCompatibilityPredicate
    ] = []
    measure_holder_requirements: list[
        tuple[
            str | None,
            str,
            tuple[str, ...],
            bool,
            tuple[str, ...],
            bool,
        ]
    ] = []
    slot_category_exclusions = list(_slot_category_exclusions(rule))
    for pred in _generation_predicates(rule):
        if pred.same_lemma is not None:
            same.append(set(pred.same_lemma))
        if pred.same_surface is not None:
            same_surface.append(set(pred.same_surface))
        if pred.same_number is not None:
            same_number.append(set(pred.same_number))
        if pred.number_compatible is not None:
            number_compatible.append(set(pred.number_compatible))
        if pred.polarity_compatible is not None:
            polarity_compatible.append(
                tuple(
                    zip(
                        pred.polarity_compatible.slots,
                        pred.polarity_compatible.categories,
                        strict=True,
                    )
                )
            )
        if pred.distinct is not None:
            distinct.append(set(pred.distinct))
        if pred.category_nonoverlap is not None:
            category_nonoverlap.append(set(pred.category_nonoverlap))
        if pred.category_contains is not None:
            category_containment.append(
                (
                    pred.category_contains.collection,
                    tuple(pred.category_contains.members),
                )
            )
        if pred.distinct_owner is not None:
            distinct_owner.append(set(pred.distinct_owner))
        if pred.bound_requires_type is not None:
            bound_type_requirements.append(
                (
                    pred.bound_requires_type.bound,
                    pred.bound_requires_type.slot,
                    pred.bound_requires_type.type,
                )
            )
        if pred.bound_requires_category is not None:
            bound_category_requirements.append(
                (
                    pred.bound_requires_category.bound,
                    pred.bound_requires_category.slot,
                    pred.bound_requires_category.cat,
                    pred.bound_requires_category.allow_proper_name,
                )
            )
        if pred.category_requires_bound is not None:
            category_bound_requirements.append(
                (
                    pred.category_requires_bound.slot,
                    pred.category_requires_bound.cat,
                    pred.category_requires_bound.bound,
                )
            )
        if pred.bound_rejects_category is not None:
            bound_category_exclusions.append(
                (
                    pred.bound_rejects_category.bound,
                    pred.bound_rejects_category.slot,
                    pred.bound_rejects_category.cat,
                )
            )
        if pred.bound_requires_form is not None:
            bound_form_requirements.append(
                (
                    pred.bound_requires_form.bound,
                    pred.bound_requires_form.slot,
                    pred.bound_requires_form.form,
                )
            )
        if pred.same_presence is not None:
            same_presence.append(set(pred.same_presence))
        if pred.attribute_compatible is not None:
            attribute_pairs.append(
                (
                    pred.attribute_compatible.attribute,
                    pred.attribute_compatible.noun,
                )
            )
        if pred.adverb_verb_compatible is not None:
            adverb_verb_pairs.append(
                (
                    pred.adverb_verb_compatible.adverb,
                    pred.adverb_verb_compatible.verb,
                )
            )
        if pred.modifier_host_compatible is not None:
            modifier_host_pairs.append(
                (
                    pred.modifier_host_compatible.modifier,
                    pred.modifier_host_compatible.host,
                    pred.modifier_host_compatible.object,
                )
            )
        if pred.verb_role_compatible is not None:
            verb_role_requirements.append(
                (
                    pred.verb_role_compatible.verb,
                    tuple(pred.verb_role_compatible.roles),
                    pred.verb_role_compatible.verb_cat,
                    pred.verb_role_compatible.role_cat,
                    pred.verb_role_compatible.excluded_role_cat,
                    pred.verb_role_compatible.allow_plural_class,
                    pred.verb_role_compatible.allow_unbound_trigger,
                )
            )
        if pred.verb_roles_compatible is not None:
            verb_selectional_requirements.append(
                pred.verb_roles_compatible
            )
        if pred.measure_holder_compatible is not None:
            measure_holder_requirements.append(
                (
                    pred.measure_holder_compatible.attribute,
                    pred.measure_holder_compatible.measure,
                    tuple(pred.measure_holder_compatible.holders),
                    pred.measure_holder_compatible.allow_proper_name,
                    tuple(
                        pred.measure_holder_compatible.proper_name_measure_categories
                    ),
                    pred.measure_holder_compatible.when_declared,
                )
            )
    return (
        same,
        same_surface,
        same_number,
        number_compatible,
        polarity_compatible,
        distinct,
        category_nonoverlap,
        category_containment,
        distinct_owner,
        bound_type_requirements,
        bound_category_requirements,
        bound_category_exclusions,
        category_bound_requirements,
        bound_form_requirements,
        same_presence,
        _distinct_measure_groups(rule),
        attribute_pairs,
        adverb_verb_pairs,
        modifier_host_pairs,
        verb_role_requirements,
        verb_selectional_requirements,
        measure_holder_requirements,
        slot_category_exclusions,
        _absent_categories(rule),
    )


def _allowed_fillers(
    token: MatchToken,
    domain: list[_Filler],
    chosen: dict[str, _Filler],
    reg: Registry,
    fixtures: _Fixtures,
    locked_bindings: dict[str, str],
    identity_bindings: dict[str, str],
    locked_fillers: dict[str, _Filler],
    same_groups: list[set[str]],
    same_number_groups: list[set[str]],
    distinct_groups: list[set[str]],
    category_nonoverlap_groups: list[set[str]],
    distinct_owner_groups: list[set[str]],
    distinct_measure_groups: tuple[tuple[str, ...], ...],
    attribute_pairs: list[tuple[str, str]],
    adverb_verb_pairs: list[tuple[str, str]],
    tokens_by_slot: dict[str, MatchToken],
    active_slots: set[str],
    slot_category_exclusions: list[tuple[str, str]],
    absent_categories: tuple[str, ...],
    modifier_host_pairs: (
        list[tuple[str, str, str | None]]
        | tuple[tuple[str, str, str | None], ...]
    ) = (),
    proportional_delta_requirements: tuple[tuple[str, str, str], ...] = (),
    number_compatible_groups: list[set[str]] | tuple[set[str], ...] = (),
    polarity_compatible_groups: (
        list[tuple[tuple[str, str], ...]]
        | tuple[tuple[tuple[str, str], ...], ...]
    ) = (),
    bound_type_requirements: (
        list[tuple[str, str, str]] | tuple[tuple[str, str, str], ...]
    ) = (),
    bound_category_requirements: (
        list[tuple[str, str, str, bool]]
        | tuple[tuple[str, str, str, bool], ...]
    ) = (),
    bound_category_exclusions: (
        list[tuple[str, str, str]] | tuple[tuple[str, str, str], ...]
    ) = (),
    category_bound_requirements: (
        list[tuple[str, str, str]] | tuple[tuple[str, str, str], ...]
    ) = (),
    bound_form_requirements: (
        list[tuple[str, str, str]] | tuple[tuple[str, str, str], ...]
    ) = (),
    verb_role_requirements: (
        list[
            tuple[
                str,
                tuple[str, ...],
                str,
                str | None,
                str | None,
                bool,
                bool,
            ]
        ]
        | tuple[
            tuple[
                str,
                tuple[str, ...],
                str,
                str | None,
                str | None,
                bool,
                bool,
            ],
            ...,
        ]
    ) = (),
    verb_selectional_requirements: (
        list[VerbRolesCompatibilityPredicate]
        | tuple[VerbRolesCompatibilityPredicate, ...]
    ) = (),
    measure_holder_requirements: (
        list[
            tuple[
                str | None,
                str,
                tuple[str, ...],
                bool,
                tuple[str, ...],
                bool,
            ]
        ]
        | tuple[
            tuple[
                str | None,
                str,
                tuple[str, ...],
                bool,
                tuple[str, ...],
                bool,
            ],
            ...,
        ]
    ) = (),
    category_membership_requirements: (
        tuple[tuple[tuple[str, ...], str], ...]
        | list[tuple[tuple[str, ...], str]]
    ) = (),
    entity_owner_distinctions: tuple[tuple[str, str], ...] = (),
    domain_for: Callable[[MatchToken], list[_Filler]] | None = None,
    same_surface_groups: (
        list[set[str]] | tuple[set[str], ...]
    ) = (),
    category_containment_requirements: (
        list[tuple[str, tuple[str, ...]]]
        | tuple[tuple[str, tuple[str, ...]], ...]
    ) = (),
) -> list[_Filler]:
    candidate_domain = domain_for or (
        lambda candidate: _domain(candidate, reg, fixtures)
    )
    domain = [
        filler
        for filler in domain
        if _outside_categories(filler, absent_categories, reg)
    ]
    if token.slot is None:
        return domain
    if token.slot in chosen:
        return [chosen[token.slot]]
    if (
        token.cat is not None
        and reg.root_sense(token.cat) == "noun"
        and any(token.slot in group for group in same_number_groups)
    ):
        existing = {(filler.surface, filler.identity) for filler in domain}
        domain = [
            *domain,
            *[
                _Filler(
                    surface=plural,
                    identity=filler.identity,
                    number="plural",
                    kind=filler.kind,
                )
                for filler in domain
                if (plural := reg.singular_to_plural.get(filler.identity))
                is not None
                and (plural, filler.identity) not in existing
            ],
        ]

    required_identities = {
        chosen[name].identity
        for group in same_groups
        if token.slot in group
        for name in group
        if name in chosen
    }
    required_surfaces = {
        chosen[name].surface.casefold()
        for group in same_surface_groups
        if token.slot in group
        for name in group
        if name in chosen
    }
    forbidden_identities = {
        chosen[name].identity
        for group in distinct_groups
        if token.slot in group
        for name in group
        if name in chosen
    }
    required_numbers = {
        chosen[name].number
        for group in same_number_groups
        if token.slot in group
        for name in group
        if name in chosen and chosen[name].number is not None
    }
    needs_number = any(
        token.slot in group for group in same_number_groups
    )
    compatible_numbers = {
        chosen[name].number
        for group in number_compatible_groups
        if token.slot in group
        for name in group
        if name in chosen and chosen[name].number is not None
    }
    preceding_is_possessive = bool(chosen) and reg.word_in_category(
        next(reversed(chosen.values())).surface.casefold(),
        "possessive_determiner",
    )
    forbidden_owners = {
        chosen[name].owner
        for group in distinct_owner_groups
        if token.slot in group
        for name in group
        if name in chosen
    }
    forbidden_measure_keys = {
        _measure_key(known)
        for group in distinct_measure_groups
        if token.slot in group
        for name in group
        if name != token.slot
        if (known := chosen.get(name) or locked_fillers.get(name)) is not None
    }

    def satisfies_required_type(
        filler: _Filler, required_type: str
    ) -> bool:
        if required_type in {"name", "proper_name"}:
            return filler.kind == "name"
        if required_type in {"noun", "common_noun"}:
            return filler.kind == "noun"
        return True

    required_types = {
        required_type
        for bound_slot, target_slot, required_type
        in bound_type_requirements
        if token.slot == target_slot and bound_slot in chosen
    }

    def compatible(filler: _Filler) -> bool:
        def known_filler(name: str) -> _Filler | None:
            return chosen.get(name) or locked_fillers.get(name)

        def known_identity(name: str) -> str | None:
            known = known_filler(name)
            if known is not None:
                return known.identity
            identity = identity_bindings.get(name)
            if identity is not None:
                return identity.casefold()
            surface = locked_bindings.get(name)
            if surface is None:
                return None
            fold = surface.casefold()
            return reg.plural_to_singular.get(
                fold, reg.verb_lemmas.get(fold, fold)
            )

        def possible_identities(name: str) -> set[str]:
            known = known_identity(name)
            if known is not None:
                return {known}
            other = tokens_by_slot.get(name)
            if other is None or name not in active_slots:
                return set()
            return {
                candidate.identity
                for candidate in candidate_domain(other)
                if _outside_categories(candidate, absent_categories, reg)
                and _outside_slot_categories(
                    candidate,
                    name,
                    slot_category_exclusions,
                    reg,
                )
            }

        # Surface agreement must be feasible in every still-unfilled sibling
        # domain, not merely checked after an earlier random choice. Without
        # this forward check, a possessive slot could repeatedly select a form
        # that has no corresponding object-pronoun surface and waste the whole
        # deterministic attempt.
        for group in same_surface_groups:
            if token.slot not in group:
                continue
            desired = filler.surface.casefold()
            for other_name in group - {token.slot}:
                other = known_filler(other_name)
                if other is not None:
                    if other.surface.casefold() != desired:
                        return False
                    continue
                other_token = tokens_by_slot.get(other_name)
                if other_name not in active_slots or other_token is None:
                    return False
                if not any(
                    candidate.surface.casefold() == desired
                    for candidate in candidate_domain(other_token)
                    if _outside_categories(
                        candidate, absent_categories, reg
                    )
                    and _outside_slot_categories(
                        candidate,
                        other_name,
                        slot_category_exclusions,
                        reg,
                    )
                ):
                    return False

        for entity_name, possessed_name in entity_owner_distinctions:
            if token.slot == entity_name:
                possessed = known_filler(possessed_name)
                if (
                    possessed is not None
                    and possessed.owner == filler.identity
                ):
                    return False
            if token.slot == possessed_name:
                entity = known_filler(entity_name)
                if (
                    entity is not None
                    and filler.owner == entity.identity
                ):
                    return False

        for source_slot, category, required_slot in (
            category_bound_requirements
        ):
            if (
                token.slot == source_slot
                and required_slot not in active_slots
                and _filler_in_category(filler, category, reg)
            ):
                return False

        for group in category_nonoverlap_groups:
            if token.slot not in group:
                continue
            for other_name in group - {token.slot}:
                other = known_filler(other_name)
                if (
                    other is not None
                    and _filler_categories_overlap(filler, other, reg)
                ):
                    return False

        for collection_name, member_names in category_containment_requirements:
            if token.slot not in {collection_name, *member_names}:
                continue
            if token.slot == collection_name:
                for member_name in member_names:
                    member = known_filler(member_name)
                    if member is not None:
                        if not _filler_category_term_contains(
                            filler, member, reg
                        ):
                            return False
                        continue
                    if member_name not in active_slots:
                        return False
                    member_token = tokens_by_slot.get(member_name)
                    if member_token is None or not any(
                        _filler_category_term_contains(filler, candidate, reg)
                        for candidate in candidate_domain(member_token)
                        if _outside_categories(
                            candidate, absent_categories, reg
                        )
                        and _outside_slot_categories(
                            candidate,
                            member_name,
                            slot_category_exclusions,
                            reg,
                        )
                    ):
                        return False
                continue
            collection = known_filler(collection_name)
            if collection is not None:
                if not _filler_category_term_contains(collection, filler, reg):
                    return False
                continue
            if collection_name not in active_slots:
                return False
            collection_token = tokens_by_slot.get(collection_name)
            if collection_token is None or not any(
                _filler_category_term_contains(candidate, filler, reg)
                for candidate in candidate_domain(collection_token)
                if _outside_categories(candidate, absent_categories, reg)
                and _outside_slot_categories(
                    candidate,
                    collection_name,
                    slot_category_exclusions,
                    reg,
                )
            ):
                return False

        for group, category in category_membership_requirements:
            if token.slot not in group:
                continue
            desired = _filler_in_category(filler, category, reg)
            for other_name in group:
                if other_name == token.slot:
                    continue
                other = known_filler(other_name)
                if other is not None:
                    if _filler_in_category(other, category, reg) != desired:
                        return False
                    continue
                if other_name not in active_slots:
                    return False
                other_token = tokens_by_slot.get(other_name)
                if other_token is None or not any(
                    _filler_in_category(candidate, category, reg) == desired
                    for candidate in candidate_domain(other_token)
                    if _outside_categories(
                        candidate, absent_categories, reg
                    )
                    and _outside_slot_categories(
                        candidate,
                        other_name,
                        slot_category_exclusions,
                        reg,
                    )
                ):
                    return False

        for attribute_name, noun_name in attribute_pairs:
            noun = known_identity(noun_name)
            attribute = known_identity(attribute_name)
            if token.slot == attribute_name and noun is not None:
                if not reg.attribute_applies_to(
                    filler.identity, noun
                ):
                    return False
            if (
                token.slot == attribute_name
                and noun is None
                and noun_name in active_slots
                and not any(
                    reg.attribute_applies_to(filler.identity, candidate)
                    for candidate in possible_identities(noun_name)
                )
            ):
                return False
            if token.slot == noun_name and attribute is not None:
                if not reg.attribute_applies_to(
                    attribute, filler.identity
                ):
                    return False
            if (
                token.slot == noun_name
                and attribute is None
                and attribute_name in active_slots
                and not any(
                    reg.attribute_applies_to(candidate, filler.identity)
                    for candidate in possible_identities(attribute_name)
                )
            ):
                return False
        for adverb_name, verb_name in adverb_verb_pairs:
            adverb = known_filler(adverb_name)
            verb = known_filler(verb_name)
            if token.slot == adverb_name and verb is not None:
                if not reg.adverb_applies_to_verb(
                    filler.surface.casefold(), verb.surface.casefold()
                ):
                    return False
            if (
                token.slot == adverb_name
                and verb is None
                and verb_name in active_slots
                and not any(
                    reg.adverb_applies_to_verb(
                        filler.surface.casefold(), candidate.surface.casefold()
                    )
                    for candidate in candidate_domain(tokens_by_slot[verb_name])
                )
            ):
                return False
            if token.slot == verb_name and adverb is not None:
                if not reg.adverb_applies_to_verb(
                    adverb.surface.casefold(), filler.surface.casefold()
                ):
                    return False
            if (
                token.slot == verb_name
                and adverb is None
                and adverb_name in active_slots
                and not any(
                    reg.adverb_applies_to_verb(
                        candidate.surface.casefold(), filler.surface.casefold()
                    )
                    for candidate in candidate_domain(tokens_by_slot[adverb_name])
                )
            ):
                return False
        for modifier_name, host_name, object_name in modifier_host_pairs:
            modifier = known_identity(modifier_name)
            host = known_identity(host_name)
            object_ = known_identity(object_name) if object_name is not None else None

            def modifier_host_ok(
                modifier_identity: str,
                host_identity: str,
                object_identity: str | None,
            ) -> bool:
                return (
                    (
                        not reg.modifier_has_host_boundary(modifier_identity)
                        or reg.modifier_applies_to_host(
                            modifier_identity, host_identity
                        )
                    )
                    and (
                        object_identity is None
                        or reg.modifier_attaches_to(
                            modifier_identity, object_identity, host_identity
                        )
                    )
                )

            if (
                token.slot == modifier_name
                and host is not None
                and (object_name is None or object_ is not None)
            ):
                if not modifier_host_ok(filler.identity, host, object_):
                    return False
            if (
                token.slot == modifier_name
                and host is None
                and host_name in active_slots
                and not any(
                    modifier_host_ok(filler.identity, candidate, object_)
                    for candidate in possible_identities(host_name)
                )
            ):
                return False
            if (
                token.slot == host_name
                and modifier is not None
                and (object_name is None or object_ is not None)
            ):
                if not modifier_host_ok(modifier, filler.identity, object_):
                    return False
            if (
                token.slot == host_name
                and modifier is None
                and modifier_name in active_slots
                and not any(
                    modifier_host_ok(candidate, filler.identity, object_)
                    for candidate in possible_identities(modifier_name)
                )
            ):
                return False
            if (
                object_name is not None
                and token.slot == object_name
                and modifier is not None
                and host is not None
                and not modifier_host_ok(modifier, host, filler.identity)
            ):
                return False
        for fraction_name, direction_name, direction_category in (
            proportional_delta_requirements
        ):
            def delta_ok(
                fraction: _Filler, direction: _Filler
            ) -> bool:
                polarity = _scoped_filler_polarity(
                    direction, direction_category, reg
                )
                return proportional_delta_is_compatible(
                    fraction.value, polarity
                )

            if token.slot == fraction_name:
                direction = known_filler(direction_name)
                if direction is not None and not delta_ok(filler, direction):
                    return False
                if (
                    direction is None
                    and direction_name in active_slots
                    and not any(
                        delta_ok(filler, candidate)
                        for candidate in candidate_domain(
                            tokens_by_slot[direction_name]
                        )
                        if _outside_categories(
                            candidate, absent_categories, reg
                        )
                        and _outside_slot_categories(
                            candidate,
                            direction_name,
                            slot_category_exclusions,
                            reg,
                        )
                    )
                ):
                    return False
            if token.slot == direction_name:
                fraction = known_filler(fraction_name)
                if fraction is not None and not delta_ok(fraction, filler):
                    return False
        for (
            verb_name,
            role_names,
            verb_category,
            role_category,
            excluded_role_category,
            allow_plural_class,
            _allow_unbound_trigger,
        ) in verb_role_requirements:
            def role_ok(verb: _Filler, role: _Filler) -> bool:
                if not _filler_in_category(verb, verb_category, reg):
                    return True
                if role_category is not None:
                    return (
                        role.kind == "name"
                        or (
                            allow_plural_class
                            and role.number == "plural"
                        )
                        or _filler_in_category(
                            role, role_category, reg
                        )
                    )
                assert excluded_role_category is not None
                return not _filler_in_category(
                    role, excluded_role_category, reg
                )

            if token.slot == verb_name:
                for role_name in role_names:
                    role = known_filler(role_name)
                    if role is not None and not role_ok(filler, role):
                        return False
                    if (
                        role is None
                        and role_name in active_slots
                        and not any(
                            role_ok(filler, candidate)
                            for candidate in candidate_domain(
                                tokens_by_slot[role_name]
                            )
                            if _outside_categories(
                                candidate, absent_categories, reg
                            )
                            and _outside_slot_categories(
                                candidate,
                                role_name,
                                slot_category_exclusions,
                                reg,
                            )
                        )
                    ):
                        return False
            if token.slot in role_names:
                verb = known_filler(verb_name)
                if verb is not None and not role_ok(verb, filler):
                    return False
        for compatibility in verb_selectional_requirements:
            mapped_slots = {
                slot
                for slots in compatibility.roles.values()
                for slot in slots
            }
            if token.slot != compatibility.verb and token.slot not in mapped_slots:
                continue
            assignments = {
                role_slot: known
                for role_slot in mapped_slots
                if (
                    known := (
                        filler
                        if token.slot == role_slot
                        else known_filler(role_slot)
                    )
                )
                is not None
            }
            if token.slot == compatibility.verb:
                if not _selectional_assignment_compatible(
                    filler, assignments, compatibility, reg
                ):
                    return False
                continue
            verb = known_filler(compatibility.verb)
            if verb is not None:
                if not _selectional_assignment_compatible(
                    verb, assignments, compatibility, reg
                ):
                    return False
                continue
            verb_token = tokens_by_slot.get(compatibility.verb)
            if verb_token is None or not any(
                _selectional_assignment_compatible(
                    candidate, assignments, compatibility, reg
                )
                for candidate in candidate_domain(verb_token)
                if _outside_categories(candidate, absent_categories, reg)
                and _outside_slot_categories(
                    candidate,
                    compatibility.verb,
                    slot_category_exclusions,
                    reg,
                )
            ):
                return False
        for (
            attribute_name,
            measure_name,
            holder_names,
            allow_proper_name,
            proper_name_measure_categories,
            when_declared,
        ) in measure_holder_requirements:
            def holder_ok(
                measure: _Filler,
                holder: _Filler,
                attribute: _Filler | None,
            ) -> bool:
                if (
                    when_declared
                    and not reg.measure_has_holder_boundary(measure.identity)
                ):
                    return True
                return (
                    holder.kind == "name"
                    and _proper_name_measure_allowed(
                        measure,
                        attribute=attribute,
                        allow_proper_name=allow_proper_name,
                        measure_categories=proper_name_measure_categories,
                        reg=reg,
                    )
                ) or reg.measure_applies_to_holder(
                    measure.identity,
                    holder.identity,
                    attribute.identity if attribute is not None else None,
                )

            def possible_attributes(
                current: _Filler | None = None,
            ) -> list[_Filler | None]:
                if attribute_name is None:
                    return [None]
                if token.slot == attribute_name and current is not None:
                    return [current]
                known = known_filler(attribute_name)
                if known is not None:
                    return [known]
                if attribute_name not in active_slots:
                    return []
                return [
                    candidate
                    for candidate in candidate_domain(
                        tokens_by_slot[attribute_name]
                    )
                    if _outside_categories(
                        candidate, absent_categories, reg
                    )
                    and _outside_slot_categories(
                        candidate,
                        attribute_name,
                        slot_category_exclusions,
                        reg,
                    )
                ]

            def compatible_with_any_attribute(
                measure: _Filler,
                holder: _Filler,
                current: _Filler | None = None,
            ) -> bool:
                return any(
                    holder_ok(measure, holder, attribute)
                    for attribute in possible_attributes(current)
                )

            if token.slot == measure_name:
                for holder_name in holder_names:
                    holder = known_filler(holder_name)
                    if holder is not None and not compatible_with_any_attribute(
                        filler, holder
                    ):
                        return False
                    if (
                        holder is None
                        and holder_name in active_slots
                        and not any(
                            compatible_with_any_attribute(filler, candidate)
                            for candidate in candidate_domain(
                                tokens_by_slot[holder_name]
                            )
                            if _outside_categories(
                                candidate, absent_categories, reg
                            )
                            and _outside_slot_categories(
                                candidate,
                                holder_name,
                                slot_category_exclusions,
                                reg,
                            )
                        )
                    ):
                        return False
            if token.slot in holder_names:
                measure = known_filler(measure_name)
                if measure is not None and not compatible_with_any_attribute(
                    measure, filler
                ):
                    return False
                if (
                    measure is None
                    and measure_name in active_slots
                    and not any(
                        compatible_with_any_attribute(candidate, filler)
                        for candidate in candidate_domain(
                            tokens_by_slot[measure_name]
                        )
                        if _outside_categories(
                            candidate, absent_categories, reg
                        )
                        and _outside_slot_categories(
                            candidate,
                            measure_name,
                            slot_category_exclusions,
                            reg,
                        )
                    )
                ):
                    return False
            if token.slot == attribute_name:
                measures = (
                    [known_filler(measure_name)]
                    if known_filler(measure_name) is not None
                    else [
                        candidate
                        for candidate in candidate_domain(
                            tokens_by_slot[measure_name]
                        )
                        if _outside_categories(
                            candidate, absent_categories, reg
                        )
                        and _outside_slot_categories(
                            candidate,
                            measure_name,
                            slot_category_exclusions,
                            reg,
                        )
                    ]
                )
                for holder_name in holder_names:
                    holder = known_filler(holder_name)
                    holders = (
                        [holder]
                        if holder is not None
                        else [
                            candidate
                            for candidate in candidate_domain(
                                tokens_by_slot[holder_name]
                            )
                            if _outside_categories(
                                candidate, absent_categories, reg
                            )
                            and _outside_slot_categories(
                                candidate,
                                holder_name,
                                slot_category_exclusions,
                                reg,
                            )
                        ]
                    )
                    if not any(
                        holder_ok(measure, holder, filler)
                        for measure in measures
                        if measure is not None
                        for holder in holders
                    ):
                        return False
        return True

    def satisfies_conditional_categories(filler: _Filler) -> bool:
        def in_category(
            candidate: _Filler,
            category: str,
            allow_proper_name: bool,
        ) -> bool:
            return (allow_proper_name and candidate.kind == "name") or (
                reg.word_in_category(candidate.surface.casefold(), category)
                or reg.word_in_category(candidate.identity, category)
            )

        for (
            bound_slot,
            target_slot,
            category,
            allow_proper_name,
        ) in bound_category_requirements:
            if (
                token.slot == target_slot
                and bound_slot in active_slots
                and not in_category(
                    filler, category, allow_proper_name
                )
            ):
                return False
            if token.slot == bound_slot:
                target = chosen.get(target_slot) or locked_fillers.get(
                    target_slot
                )
                if target is not None and not in_category(
                    target, category, allow_proper_name
                ):
                    return False
        for bound_slot, target_slot, category in bound_category_exclusions:
            if (
                token.slot == target_slot
                and bound_slot in active_slots
                and in_category(filler, category, False)
            ):
                return False
            if token.slot == bound_slot:
                target = chosen.get(target_slot) or locked_fillers.get(
                    target_slot
                )
                if target is not None and in_category(
                    target, category, False
                ):
                    return False
        return True

    def satisfies_conditional_forms(filler: _Filler) -> bool:
        def has_form(candidate: _Filler, form: str) -> bool:
            if form == "bare":
                return is_bare_verb_form(
                    candidate.surface.casefold(), candidate.identity
                )
            return is_finite_verb_form(
                candidate.surface.casefold(), candidate.identity
            )

        for bound_slot, target_slot, form in bound_form_requirements:
            if (
                token.slot == target_slot
                and bound_slot in active_slots
                and not has_form(filler, form)
            ):
                return False
            if token.slot == bound_slot:
                target = chosen.get(target_slot) or locked_fillers.get(
                    target_slot
                )
                if target is not None and not has_form(target, form):
                    return False
                if (
                    target is None
                    and target_slot in active_slots
                    and not any(
                        has_form(candidate, form)
                        for candidate in candidate_domain(
                            tokens_by_slot[target_slot]
                        )
                        if _outside_categories(
                            candidate, absent_categories, reg
                        )
                        and _outside_slot_categories(
                            candidate,
                            target_slot,
                            slot_category_exclusions,
                            reg,
                        )
                    )
                ):
                    return False
        return True

    def satisfies_scoped_polarity(filler: _Filler) -> bool:
        for requirement in polarity_compatible_groups:
            scopes = dict(requirement)
            if token.slot not in scopes:
                continue
            polarities = {
                polarity
                for slot_name, category in requirement
                if (
                    candidate := (
                        filler
                        if slot_name == token.slot
                        else chosen.get(slot_name)
                        or locked_fillers.get(slot_name)
                    )
                )
                is not None
                if (
                    polarity := _scoped_filler_polarity(
                        candidate, category, reg
                    )
                )
                is not None
            }
            if len(polarities) > 1:
                return False
        return True

    return [
        filler
        for filler in domain
        if (
            not required_identities
            or filler.identity in required_identities
        )
        and (
            not required_surfaces
            or filler.surface.casefold() in required_surfaces
        )
        and filler.identity not in forbidden_identities
        and (not needs_number or filler.number is not None)
        and (not required_numbers or filler.number in required_numbers)
        and (
            filler.number is None
            or not compatible_numbers
            or filler.number in compatible_numbers
        )
        and (
            filler.reference_form is None
            or (
                filler.reference_form == "bare"
                and (
                    token.generation_bare_reference
                    or preceding_is_possessive
                    or (
                        token.bare_reference_category is not None
                        and reg.word_in_category(
                            filler.identity,
                            token.bare_reference_category,
                        )
                    )
                )
            )
            or (
                filler.reference_form == "definite"
                and not token.generation_bare_reference
                and not preceding_is_possessive
            )
        )
        and not (
            preceding_is_possessive
            and token.determinerless_category is not None
            and _filler_in_category(
                filler, token.determinerless_category, reg
            )
        )
        and filler.owner not in forbidden_owners
        and _measure_key(filler) not in forbidden_measure_keys
        and all(
            satisfies_required_type(filler, required_type)
            for required_type in required_types
        )
        and compatible(filler)
        and satisfies_conditional_categories(filler)
        and satisfies_conditional_forms(filler)
        and satisfies_scoped_polarity(filler)
        and _outside_slot_categories(
            filler,
            token.slot,
            slot_category_exclusions,
            reg,
        )
    ]


def _realize(
    rule: PatternRule,
    reg: Registry,
    fixtures: _Fixtures,
    rng: random.Random,
    *,
    locked_bindings: dict[str, str] | None = None,
    identity_bindings: dict[str, str] | None = None,
    excluded_bindings: dict[str, str] | None = None,
    generation_mode: GenerationMode = "strict",
    structural_target: str | None = None,
) -> tuple[
    str,
    dict[str, str],
    dict[tuple[int, ...], bool],
    tuple[LexicalRelaxation, ...],
]:
    seq = _flat_sentence(rule)
    assert seq is not None
    locked_bindings = locked_bindings or {}
    identity_bindings = identity_bindings or {}
    excluded_bindings = excluded_bindings or {}
    (
        same_groups,
        same_surface_groups,
        same_number_groups,
        number_compatible_groups,
        polarity_compatible_groups,
        distinct_groups,
        category_nonoverlap_groups,
        category_containment_requirements,
        distinct_owner_groups,
        bound_type_requirements,
        bound_category_requirements,
        bound_category_exclusions,
        category_bound_requirements,
        bound_form_requirements,
        same_presence_groups,
        distinct_measure_groups,
        attribute_pairs,
        adverb_verb_pairs,
        modifier_host_pairs,
        verb_role_requirements,
        verb_selectional_requirements,
        measure_holder_requirements,
        slot_category_exclusions,
        absent_categories,
    ) = _constraint_groups(rule)
    unbound_optional_paths = _unbound_optional_paths(rule, seq)
    proportional_delta_requirements = _proportional_delta_requirements(rule)
    category_membership_requirements = (
        _category_membership_requirements(rule)
    )
    locked_fillers = _resolve_locked_fillers(
        seq, reg, fixtures, locked_bindings, identity_bindings
    )
    entity_owner_distinctions = _entity_owner_distinctions(rule)
    chosen: dict[str, _Filler] = {}
    surfaces: list[str] = []
    realized: list[tuple[MatchToken, _Filler]] = []
    optional_choices: dict[tuple[int, ...], bool] = {}
    token_nodes = list(_token_nodes(seq))
    structural_optional_path: tuple[int, ...] | None = None
    structural_optional_value: bool | None = None
    structural_literal_path: tuple[int, ...] | None = None
    structural_literal_surface: str | None = None
    forced_structural_ancestors: set[tuple[int, ...]] = set()
    if structural_target is not None:
        parts = structural_target.split(":", 2)
        if parts[0] in {"optional", "literal"}:
            if len(parts) != 3 or not parts[1].isdigit():
                raise GenerationError(
                    f"invalid structural target {structural_target!r}"
                )
            token_no = int(parts[1])
            if token_no >= len(token_nodes):
                raise GenerationError(
                    f"structural target {structural_target!r} names no token"
                )
            path, target_token, target_ancestors = token_nodes[token_no]
            if parts[0] == "optional":
                if target_token.opt is None or parts[2] not in {
                    "included",
                    "omitted",
                }:
                    raise GenerationError(
                        f"structural target {structural_target!r} is not an "
                        "optional-branch outcome"
                    )
                structural_optional_path = path
                structural_optional_value = parts[2] == "included"
                forced_structural_ancestors = set(target_ancestors)
            else:
                if (
                    len(target_token.lit_options) < 2
                    or parts[2].casefold()
                    not in {
                        option.casefold() for option in target_token.lit_options
                    }
                ):
                    raise GenerationError(
                        f"structural target {structural_target!r} is not a "
                        "declared literal alternative"
                    )
                structural_literal_path = path
                structural_literal_surface = parts[2].casefold()
                forced_structural_ancestors = set(target_ancestors)
        elif parts[0] not in {"fact", "surface"}:
            raise GenerationError(
                f"unknown structural target {structural_target!r}"
            )
    tokens_by_slot = {
        token.slot: token
        for _, token, _ in _leaf_tokens(seq)
        if token.slot is not None
    }
    optional_path_by_slot = {
        token.slot: (ancestors[-1] if ancestors else None)
        for _, token, ancestors in _leaf_tokens(seq)
        if token.slot is not None
    }
    presence_path_groups = [
        {
            path
            for slot in group
            if (path := optional_path_by_slot.get(slot)) is not None
        }
        for group in same_presence_groups
    ]
    forced_slots = (
        set(locked_bindings) | set(identity_bindings) | set(excluded_bindings)
    )
    forced_optional_paths = {
        ancestor
        for _, token, ancestors in _leaf_tokens(seq)
        if token.slot in forced_slots
        for ancestor in ancestors
    } | forced_structural_ancestors
    forced_omitted_paths = set(unbound_optional_paths)
    if structural_optional_path is not None:
        if structural_optional_value:
            forced_optional_paths.add(structural_optional_path)
        else:
            forced_omitted_paths.add(structural_optional_path)
    for paths in presence_path_groups:
        if paths & forced_optional_paths:
            forced_optional_paths.update(paths)
        if paths & forced_omitted_paths:
            forced_omitted_paths.update(paths)
    conflicting_paths = forced_optional_paths & forced_omitted_paths
    if conflicting_paths:
        path = min(conflicting_paths)
        names = ", ".join(repr(name) for name in unbound_optional_paths[path])
        raise GenerationError(
            f"requested binding requires optional branch {path}, but "
            f"where requires {names} to remain unbound"
        )

    path_presence_group = {
        path: group_no
        for group_no, paths in enumerate(presence_path_groups)
        for path in paths
    }
    presence_choices: dict[int, bool] = {}

    def decide_optionals(
        tokens: list[MatchToken],
        parent_path: tuple[int, ...] = (),
    ) -> None:
        for token_no, token in enumerate(tokens):
            path = (*parent_path, token_no)
            if token.opt is None:
                continue
            group_no = path_presence_group.get(path)
            if path in forced_omitted_paths:
                include = False
            elif path in forced_optional_paths:
                include = True
            elif group_no is not None and group_no in presence_choices:
                include = presence_choices[group_no]
            else:
                include = bool(rng.randrange(2))
            if group_no is not None:
                presence_choices[group_no] = include
            optional_choices[path] = include
            if include:
                decide_optionals(token.opt, path)

    decide_optionals(seq)
    active_slots = {
        token.slot
        for _, token, ancestors in _leaf_tokens(seq)
        if token.slot is not None
        and all(optional_choices.get(path, False) for path in ancestors)
    }
    active_leaf_tokens = [
        token
        for _, token, ancestors in _leaf_tokens(seq)
        if all(optional_choices.get(path, False) for path in ancestors)
    ]
    name_required_before_count = {
        current.slot
        for current, following in zip(
            active_leaf_tokens,
            active_leaf_tokens[1:],
            strict=False,
        )
        if current.slot is not None
        and current.type == "entity"
        and (following.type == "counted" or following.counted)
    }

    boundary_domains: dict[
        str, tuple[list[_Filler], str, str]
    ] = {}
    if generation_mode == "lexical_boundary":
        active_tokens_by_slot: dict[str, list[MatchToken]] = {}
        for _, token, ancestors in _leaf_tokens(seq):
            if (
                token.slot is not None
                and token.slot in active_slots
                and all(optional_choices.get(path, False) for path in ancestors)
            ):
                active_tokens_by_slot.setdefault(token.slot, []).append(token)
        for slot_name, slot_tokens in active_tokens_by_slot.items():
            widened = [
                _broader_lexical_domain(token, reg, fixtures)
                for token in slot_tokens
            ]
            if any(domain is None for domain in widened):
                continue
            complete = [domain for domain in widened if domain is not None]
            shared = set(complete[0][0])
            for domain, _, _ in complete[1:]:
                shared.intersection_update(domain)
            if shared:
                boundary_domains[slot_name] = (
                    [filler for filler in complete[0][0] if filler in shared],
                    complete[0][1],
                    complete[0][2],
                )
    boundary_slot = (
        sorted(boundary_domains)[rng.randrange(len(boundary_domains))]
        if boundary_domains
        else None
    )
    relaxations: dict[str, LexicalRelaxation] = {}

    def domain_for(token: MatchToken) -> list[_Filler]:
        if boundary_slot is not None and token.slot == boundary_slot:
            domain = boundary_domains[boundary_slot][0]
        else:
            domain = _domain(token, reg, fixtures)
        # Exact numeric locks are structural values, not lexicon entries. Add
        # the requested scalar to the ordinary bounded domain and let the same
        # token qualifier enforce integer/range/fraction constraints. This is
        # needed for replaying a caller-supplied calendar reference year; it
        # does not widen unlocked random generation beyond declared values.
        locked_number = locked_bindings.get(token.slot or "")
        if token.type == "number" and locked_number is not None:
            try:
                value = float(locked_number)
            except ValueError:
                pass
            else:
                rendered = (
                    str(int(value)) if value.is_integer() else str(value)
                )
                domain = [
                    *domain,
                    *_qualify_domain(
                        token,
                        [
                            _Filler(
                                rendered,
                                rendered,
                                number=(
                                    "singular" if value == 1.0 else "plural"
                                ),
                                value=value,
                            )
                        ],
                        reg,
                    ),
                ]
        if token.slot in name_required_before_count:
            return [filler for filler in domain if filler.kind == "name"]
        return domain

    def realize_tokens(
        tokens: list[MatchToken],
        parent_path: tuple[int, ...] = (),
    ) -> None:
        for token_no, token in enumerate(tokens):
            path = (*parent_path, token_no)
            if token.opt is not None:
                if optional_choices.get(path, False):
                    realize_tokens(token.opt, path)
                continue

            domain = _allowed_fillers(
                token,
                domain_for(token),
                chosen,
                reg,
                fixtures,
                locked_bindings,
                identity_bindings,
                locked_fillers,
                same_groups,
                same_number_groups,
                distinct_groups,
                category_nonoverlap_groups,
                distinct_owner_groups,
                distinct_measure_groups,
                attribute_pairs,
                adverb_verb_pairs,
                tokens_by_slot,
                active_slots,
                slot_category_exclusions,
                absent_categories,
                modifier_host_pairs,
                proportional_delta_requirements,
                number_compatible_groups,
                polarity_compatible_groups,
                bound_type_requirements,
                bound_category_requirements,
                bound_category_exclusions,
                category_bound_requirements,
                bound_form_requirements,
                verb_role_requirements,
                verb_selectional_requirements,
                measure_holder_requirements,
                category_containment_requirements=(
                    category_containment_requirements
                ),
                category_membership_requirements=(
                    category_membership_requirements
                ),
                entity_owner_distinctions=entity_owner_distinctions,
                domain_for=domain_for,
                same_surface_groups=same_surface_groups,
            )
            if path == structural_literal_path:
                domain = [
                    filler
                    for filler in domain
                    if filler.surface.casefold() == structural_literal_surface
                ]
            if token.slot in locked_bindings:
                locked = locked_bindings[token.slot].casefold()
                domain = [
                    filler
                    for filler in domain
                    if filler.surface.casefold() == locked
                ]
            if token.slot in identity_bindings:
                identity = identity_bindings[token.slot].casefold()
                domain = [
                    filler
                    for filler in domain
                    if filler.identity.casefold() == identity
                ]
            if token.slot in excluded_bindings:
                excluded = excluded_bindings[token.slot].casefold()
                domain = [
                    filler
                    for filler in domain
                    if filler.surface.casefold() != excluded
                ]
            if not domain:
                label = token.slot or repr(token.lit)
                raise GenerationError(
                    f"constraints left no filler for {label}"
                )
            filler = domain[rng.randrange(len(domain))]
            if token.slot is not None:
                chosen[token.slot] = filler
                if boundary_slot is not None and token.slot == boundary_slot:
                    _, requirement, broader_domain = boundary_domains[
                        boundary_slot
                    ]
                    relaxations[token.slot] = LexicalRelaxation(
                        slot=token.slot,
                        surface=filler.surface,
                        identity=filler.identity,
                        requirement=requirement,
                        broader_domain=broader_domain,
                    )
            surfaces.append(filler.surface)
            realized.append((token, filler))

    realize_tokens(seq)

    for (token, article), (_, following) in zip(
        realized,
        realized[1:],
        strict=False,
    ):
        if {
            option.casefold() for option in token.lit_options
        } != {"a", "an"}:
            continue
        expected = _expected_indefinite_article(following, reg)
        if expected is not None and article.surface.casefold() != expected:
            raise GenerationError(
                f"indefinite article {article.surface!r} is incompatible "
                f"with following surface {following.surface!r}"
            )

    sentence = " ".join(surfaces)
    sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
    if sentence and sentence[-1] not in _PUNCTUATION:
        sentence += "."
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
    return (
        sentence,
        {name: filler.surface for name, filler in chosen.items()},
        optional_choices,
        tuple(relaxations[name] for name in sorted(relaxations)),
    )


def _fact_kind_type_name(kind: str) -> str:
    """Return the runtime dataclass spelling for a declarative fact kind."""

    return "".join(part.capitalize() for part in kind.split("_"))


def _realize_context(
    rule: PatternRule,
    reg: Registry,
    fixtures: _Fixtures,
    rng: random.Random,
    *,
    locked_bindings: dict[str, str] | None = None,
    identity_bindings: dict[str, str] | None = None,
    target_bindings: dict[str, str] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Realize pack-declared adjacent discourse without linguistic literals."""

    context = rule.generation_context
    if context is None:
        return (), ()

    contextual_identities = dict(identity_bindings or {})
    target_bindings = target_bindings or {}
    for context_slot, target_slot in context.target_identity_links.items():
        surface = target_bindings.get(target_slot)
        if surface is None:
            raise GenerationError(
                f"context identity link {context_slot!r} needs target slot "
                f"{target_slot!r}"
            )
        key = _binding_key(surface, reg)
        if not key:
            raise GenerationError(
                f"context identity link could not resolve {surface!r}"
            )
        identity = key[-1]
        existing = contextual_identities.get(context_slot)
        if existing is not None and existing.casefold() != identity:
            raise GenerationError(
                f"context identity link for {context_slot!r} conflicts with "
                f"requested identity {existing!r}"
            )
        contextual_identities[context_slot] = identity

    def realize_all(position: str, sentences: list[Any]) -> tuple[str, ...]:
        realized: list[str] = []
        for index, sentence in enumerate(sentences):
            contextual_rule = PatternRule(
                id=f"{rule.id}#context-{position}-{index}",
                match={"sentence": sentence.sentence},
                where=sentence.where,
            )
            surface, _, _, _ = _realize(
                contextual_rule,
                reg,
                fixtures,
                rng,
                locked_bindings=locked_bindings,
                identity_bindings=contextual_identities,
            )
            realized.append(surface)
        return tuple(realized)

    return (
        realize_all("before", context.before),
        realize_all("after", context.after),
    )


def _format_contextual_target(
    rule: PatternRule,
    sentence: str,
    requested: dict[str, str],
) -> str:
    """Render readable clause boundaries omitted from matcher skeletons."""

    if rule.generation_context is None:
        return sentence
    for slot in rule.generation_context.target_commas_after:
        surface = requested.get(slot)
        if not surface:
            continue
        sentence = sentence.replace(
            surface,
            f"{surface},",
            1,
        )
    return sentence


def _fact_derivation(
    fact: Any,
    project: Project,
    bindings: dict[str, str] | None,
) -> dict[str, Any] | None:
    """Expose the declarative emit template behind one matched fact.

    Runtime facts intentionally retain only their resolved fields and compact
    provenance. The Designer has the loaded registry and exact match bindings,
    so it can reconstruct the authoring explanation without changing kernel
    fact identity or serialization.
    """

    rule = next(
        (
            candidate
            for candidate in project.registry.rules
            if candidate.id == fact.provenance.source
        ),
        None,
    )
    if rule is None:
        return None
    emits = [
        emit
        for emit in rule.emits
        if _fact_kind_type_name(emit.fact) == type(fact).__name__
    ]
    if len(emits) != 1:
        # Several same-kind emits need per-emission provenance before they can
        # be explained honestly. Do not guess which template produced a fact.
        return None
    return {
        "templates": {
            key: _jsonable(value)
            for key, value in sorted(emits[0].fields.items())
        },
        "bindings": dict(sorted((bindings or {}).items())),
    }


def _fact_json(
    fact: Any,
    project: Project | None = None,
    *,
    bindings: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = {
        "type": type(fact).__name__,
        "fields": {
            key: _jsonable(value)
            for key, value in fact.__dict__.items()
            if key != "provenance" and value is not None
        },
        "source": fact.provenance.source,
        "sentence": fact.provenance.sentence,
    }
    if project is not None:
        source = project.source_index.rules.get(fact.provenance.source)
        if source is not None:
            payload["source_ref"] = source.to_json()
        derivation = _fact_derivation(fact, project, bindings)
        if derivation is not None:
            payload["derivation"] = derivation
    return payload


def _bindings(result: RuleMatchResult) -> dict[str, str]:
    return {
        name: (
            " ".join(unit.surface for unit in value)
            if isinstance(value, tuple)
            else value.surface
        )
        for name, value in sorted(result.match.slots.items())
    }


def _binding_key(surface: str, reg: Registry) -> tuple[str, ...]:
    """Canonical content units for one requested or matched slot surface.

    Generated fillers may include an article that the ordinary matcher skips,
    sentence-initial capitalization, possessive spacing, or a hyphenated
    fraction that normalization condenses. Re-analyzing the isolated surface
    compares those ordinary structural forms without letting a partial head
    match stand in for a longer requested filler.
    """

    reading = analyze(surface, reg, tracing=False)
    return tuple(
        _unit_lemma(unit, reg).casefold()
        for unit in reading.units
        if unit.sense() not in SKIPPABLE_SENSES
    )


def _strict_round_trip_result(
    result: RuleMatchResult,
    requested_bindings: dict[str, str],
    reading: Any,
    reg: Registry,
) -> bool:
    """Whether TARGET preserved every generated role and all content units."""

    actual = _bindings(result)
    if any(
        slot not in actual
        or _binding_key(surface, reg) != _binding_key(actual[slot], reg)
        for slot, surface in requested_bindings.items()
    ):
        return False
    meaningful = {
        unit.uid
        for unit in reading.units
        if unit.sense() not in SKIPPABLE_SENSES
    }
    return meaningful.issubset(result.match.consumed)


def _match_summaries(
    results: list[RuleMatchResult], project: Project, reading: Any
) -> tuple[MatchSummary, ...]:
    reg = project.registry
    units = {unit.uid: unit for unit in reading.units}
    return tuple(
        MatchSummary(
            rule_id=result.match.rule.id,
            bindings=_bindings(result),
            consumed=result.match.consumed,
            consumed_surfaces=tuple(
                units[uid].surface for uid in result.match.consumed if uid in units
            ),
            shadowed=any(
                other is not result
                and subsumes(other.match, result.match, reg)
                for other in results
            ),
            emitted_facts=tuple(
                _fact_json(
                    fact,
                    project,
                    bindings=_bindings(result),
                )
                for fact in result.facts
            ),
        )
        for result in results
    )


def _premise_match_results(
    results: list[RuleMatchResult],
) -> list[RuleMatchResult]:
    """Ordinary reviewable matches, excluding defensive safety consumers."""

    return [
        result
        for result in results
        if result.match.rule.generation != "safety"
    ]


def _safety_interception_results(
    results: list[RuleMatchResult], reg: Registry
) -> list[RuleMatchResult]:
    """Safety consumers that remain necessary after ordinary subsumption.

    A broad fact-free guard often co-fires with the valid premise that already
    consumes the same units. That redundant guard is implementation detail,
    not a safety event worth presenting to the reviewer. It becomes an
    interception only when no ordinary, more-specific match subsumes it.
    """

    ordinary = _premise_match_results(results)
    return [
        result
        for result in results
        if result.match.rule.generation == "safety"
        and not any(
            subsumes(other.match, result.match, reg)
            for other in ordinary
        )
    ]


def _matched_fact_bindings(
    fact: Any,
    results: list[RuleMatchResult],
) -> dict[str, str] | None:
    """Return bindings only when one ordinary match owns FACT unambiguously."""

    owners = [
        _bindings(result)
        for result in results
        if any(
            emitted is fact or emitted == fact
            for emitted in result.facts
        )
    ]
    if not owners:
        return None
    first = owners[0]
    return first if all(owner == first for owner in owners[1:]) else None


def _source_json(ref: SourceRef | None) -> dict[str, Any] | None:
    return None if ref is None else ref.to_json()


def _rule_token_source(
    project: Project,
    rule_id: str,
    path: tuple[int, ...],
) -> SourceRef | None:
    """Return the exact source row for a top-level or nested rule token."""

    return (
        project.source_index.rule_token_paths.get((rule_id, path))
        or (
            project.source_index.rule_tokens.get((rule_id, path[0]))
            if len(path) == 1
            else None
        )
    )


def _dedupe_sources(refs: list[SourceRef | None]) -> tuple[dict[str, Any], ...]:
    seen: set[tuple[str, int, str]] = set()
    out: list[dict[str, Any]] = []
    for ref in refs:
        if ref is None:
            continue
        key = (str(ref.path), ref.line, ref.kind)
        if key not in seen:
            seen.add(key)
            out.append(ref.to_json())
    return tuple(out)


def _slot_units(value: Unit | tuple[Unit, ...] | None) -> tuple[Unit, ...]:
    if value is None:
        return ()
    return value if isinstance(value, tuple) else (value,)


def _unit_lemma(unit: Unit, reg: Registry) -> str:
    fold = unit.surface.casefold()
    feature = unit.features.get("lemma")
    if isinstance(feature, str):
        return feature.casefold()
    return reg.plural_to_singular.get(
        fold, reg.verb_lemmas.get(fold, fold)
    )


def _lexical_sources(
    project: Project, unit: Unit
) -> list[SourceRef | None]:
    """Locate the declaration and any morphology that produced this surface."""

    reg = project.registry
    index = project.source_index
    fold = unit.surface.casefold()
    lemma = _unit_lemma(unit, reg)
    refs: list[SourceRef | None] = [
        index.lexicon.get(fold),
        index.lexicon.get(lemma),
    ]
    if fold != lemma:
        refs.extend(
            (
                index.morphology.get((lemma, "plural")),
                index.morphology.get((fold, "verb.lemma")),
                index.morphology.get((lemma, "verb")),
            )
        )
    return refs


def _counted_lexical_sources(
    project: Project, unit: Unit
) -> list[SourceRef | None]:
    """Locate the declared noun pair used by one condensed counted unit."""

    reg = project.registry
    index = project.source_index
    lemma = _unit_lemma(unit, reg)
    refs: list[SourceRef | None] = [index.lexicon.get(lemma)]
    value = unit.features.get("value")
    if (
        isinstance(value, (int, float))
        and float(value) != 1
        and reg.singular_to_plural.get(lemma)
        == unit.words[-1].surface.casefold()
    ):
        refs.append(index.morphology.get((lemma, "plural")))
    return refs


def _possessed_sources(
    project: Project, fixtures: _Fixtures, unit: Unit
) -> list[SourceRef | None]:
    """Locate every declaration used by one possessive-merged noun."""

    reg = project.registry
    index = project.source_index
    lemma = _unit_lemma(unit, reg)
    owner_surface = unit.words[0].surface.casefold() if unit.words else ""
    head_surface = unit.words[-1].surface.casefold() if unit.words else ""
    refs: list[SourceRef | None] = [
        fixtures.sources.get(owner_surface),
        index.contractions.get("'s"),
        index.lexicon.get("'s"),
        index.lexicon.get(lemma),
    ]
    if (
        unit.features.get("number") == "plural"
        and reg.singular_to_plural.get(lemma) == head_surface
    ):
        refs.append(index.morphology.get((lemma, "plural")))
    return refs


def _category_evidence(
    project: Project, token: MatchToken, unit: Unit
) -> tuple[tuple[str, ...], list[SourceRef | None]]:
    """Explain the word/category ancestry accepted by the ordinary matcher."""

    category_gate = token.cat
    if token.common_noun_cat is not None and unit.sense() == "noun":
        category_gate = token.common_noun_cat
    if category_gate is None and token.type in {"modal", "future_modal"}:
        category_gate = token.type
    if category_gate is None:
        return (), []
    reg = project.registry
    index = project.source_index
    fold = unit.surface.casefold()
    lemma = _unit_lemma(unit, reg)
    for word in dict.fromkeys((fold, lemma)):
        for category in reg.word_categories.get(word, ()):
            ancestry = reg.cat_ancestors(category)
            if category_gate not in ancestry:
                continue
            refs: list[SourceRef | None] = [
                index.category_members.get((category, word)),
                index.category_members.get((category, lemma)),
            ]
            refs.extend(index.categories.get(name) for name in ancestry)
            return (word, *ancestry), refs

    # Root-sense categories are also satisfied directly by lexicon senses.
    entry = reg.lexicon.get(fold) or reg.lexicon.get(lemma)
    if entry is not None and category_gate in entry.senses:
        return (lemma, category_gate), [
            index.categories.get(category_gate)
        ]
    return (lemma, category_gate), [index.categories.get(category_gate)]


def _attribute_compatibility_evidence(
    project: Project,
    predicate: AttributeCompatibilityPredicate,
    slots: dict[str, Unit | tuple[Unit, ...]],
) -> list[SourceRef | None]:
    """Locate the exact category-pair and memberships that licensed a match."""

    attribute_units = _slot_units(slots.get(predicate.attribute))
    noun_units = _slot_units(slots.get(predicate.noun))
    if not attribute_units or not noun_units:
        return []
    reg = project.registry
    index = project.source_index
    attribute = _unit_lemma(attribute_units[0], reg)
    noun = _unit_lemma(noun_units[0], reg)
    refs: list[SourceRef | None] = []
    for attribute_category, noun_category in reg.attribute_compatibility_pairs(
        attribute, noun
    ):
        refs.extend(
            (
                index.attribute_compatibility.get(
                    (attribute_category, noun_category)
                ),
                index.categories.get(attribute_category),
                index.categories.get(noun_category),
            )
        )
        for direct in reg.word_categories.get(attribute, ()):
            if attribute_category in reg.cat_ancestors(direct):
                refs.append(index.category_members.get((direct, attribute)))
        for direct in reg.word_categories.get(noun, ()):
            if noun_category in reg.cat_ancestors(direct):
                refs.append(index.category_members.get((direct, noun)))
    return refs


def _adverb_verb_compatibility_evidence(
    project: Project,
    predicate: AdverbVerbCompatibilityPredicate,
    slots: dict[str, Unit | tuple[Unit, ...]],
) -> list[SourceRef | None]:
    """Locate the category pair and memberships licensing an adverb/verb."""

    adverb_units = _slot_units(slots.get(predicate.adverb))
    verb_units = _slot_units(slots.get(predicate.verb))
    if not adverb_units or not verb_units:
        return []
    reg = project.registry
    index = project.source_index
    adverb = adverb_units[0].surface.casefold()
    verb = verb_units[0].surface.casefold()
    refs: list[SourceRef | None] = []
    for adverb_category, verb_category in (
        reg.adverb_verb_compatibility_pairs(adverb, verb)
    ):
        refs.extend(
            (
                index.adverb_verb_compatibility.get(
                    (adverb_category, verb_category)
                ),
                index.categories.get(adverb_category),
                index.categories.get(verb_category),
            )
        )
        for direct in reg.word_categories.get(adverb, ()):
            if adverb_category in reg.cat_ancestors(direct):
                refs.append(index.category_members.get((direct, adverb)))
        for direct in reg.word_categories.get(verb, ()):
            if verb_category in reg.cat_ancestors(direct):
                refs.append(index.category_members.get((direct, verb)))
    return refs


def _measure_holder_compatibility_evidence(
    project: Project,
    attribute_slot: str | None,
    measure_slot: str,
    holder_slots: tuple[str, ...],
    slots: dict[str, Unit | tuple[Unit, ...]],
) -> list[SourceRef | None]:
    """Locate every pack declaration that licensed measure/holder roles."""

    measure_units = _slot_units(slots.get(measure_slot))
    if not measure_units:
        return []
    reg = project.registry
    index = project.source_index
    measure = _unit_lemma(measure_units[0], reg)
    attribute_units = (
        _slot_units(slots.get(attribute_slot))
        if attribute_slot is not None
        else ()
    )
    attribute = (
        _unit_lemma(attribute_units[0], reg) if attribute_units else None
    )
    refs: list[SourceRef | None] = []
    for holder_slot in holder_slots:
        holder_units = _slot_units(slots.get(holder_slot))
        if not holder_units or _role_is_proper_name(holder_units[0], reg):
            continue
        holder = _unit_lemma(holder_units[0], reg)
        for measure_category, holder_category in (
            reg.measure_holder_compatibility_pairs(
                measure, holder, attribute
            )
        ):
            refs.extend(
                (
                    index.measure_holder_compatibility.get(
                        (measure_category, holder_category)
                    ),
                    index.categories.get(measure_category),
                    index.categories.get(holder_category),
                )
            )
            for direct in reg.word_categories.get(measure, ()):
                if measure_category in reg.cat_ancestors(direct):
                    refs.append(
                        index.category_members.get((direct, measure))
                    )
            for direct in reg.word_categories.get(holder, ()):
                if holder_category in reg.cat_ancestors(direct):
                    refs.append(index.category_members.get((direct, holder)))
    return refs


def _numeric_sources(
    project: Project, token: MatchToken, unit: Unit
) -> list[SourceRef | None]:
    slot_type = token.type
    fold = unit.surface.casefold()
    index = project.source_index
    reg = project.registry
    if slot_type == "fraction":
        if unit.features.get("fraction_count") is not None and unit.words:
            count_surface = unit.words[0].surface.casefold()
            plural = unit.words[-1].surface.casefold()
            return [
                index.numeric.get(("numbers", count_surface)),
                index.numeric.get(("fractions", plural)),
                index.numeric.get(("fraction_plurals", plural)),
            ]
        return [index.numeric.get(("fractions", fold))]
    if slot_type in {"multiplier", "nonunit_multiplier"}:
        return [index.numeric.get(("multipliers", fold))]
    if slot_type == "counted" or token.counted or token.attributive_counted:
        value = unit.features.get("value")
        if not isinstance(value, (int, float)):
            return []
    elif slot_type in {"number", "percent"}:
        value_text = fold.removesuffix("%")
        try:
            value = float(value_text)
        except ValueError:
            return [index.numeric.get(("numbers", value_text))]
    else:
        return []
    for surface, declared in sorted(reg.numbers.items()):
        if float(declared) == value:
            return [index.numeric.get(("numbers", surface))]
    return []


def _token_expression(token: MatchToken) -> str:
    if token.opt is not None:
        return f"optional group ({len(token.opt)} token(s))"
    if token.lit is not None:
        return "literal " + " | ".join(repr(value) for value in token.lit_options)
    gates = []
    if token.type is not None:
        gates.append(f"type {token.type!r}")
    if token.cat is not None:
        gates.append(f"category {token.cat!r}")
    if token.common_noun_cat is not None:
        gates.append(
            f"common nouns in category {token.common_noun_cat!r}"
        )
    if token.counted:
        gates.append("counted")
    if token.attributive_counted:
        gates.append("numeric hyphen modifier")
    if token.qualifier_cat is not None:
        gates.append(f"qualifier category {token.qualifier_cat!r}")
    if token.possessed:
        gates.append("possessed")
    if token.bare_form:
        gates.append("bare form")
    if token.finite_form:
        gates.append("finite form")
    if token.present_participle:
        gates.append("present participle")
    if token.past_participle:
        gates.append("past participle")
    if token.number is not None:
        gates.append(f"number {token.number!r}")
    if token.standalone:
        gates.append("standalone")
    if token.integer:
        gates.append("integer")
    if token.value_min is not None:
        gates.append(f"value >= {token.value_min:g}")
    if token.value_max is not None:
        gates.append(f"value <= {token.value_max:g}")
    if token.fraction_within_whole:
        gates.append("within one whole")
    if token.word_fraction_within_whole:
        gates.append("word fraction within one whole")
    if token.fraction_positive:
        gates.append("positive")
    if token.referential:
        gates.append("referential")
    if token.bare_reference_category is not None:
        gates.append(
            f"bare category {token.bare_reference_category!r}"
        )
    if token.determinerless_category is not None:
        gates.append(
            f"determinerless category {token.determinerless_category!r}"
        )
    return f"{token.slot}: " + ", ".join(gates or ["word"])


def _token_reason(
    token: MatchToken,
    units: tuple[Unit, ...],
    category_path: tuple[str, ...],
) -> str:
    surface = " ".join(unit.surface for unit in units)
    if token.lit is not None:
        return f"{surface!r} satisfied the required literal"
    if token.cat is not None:
        chain = " → ".join(category_path)
        if token.counted and len(units) == 1:
            unit = units[0]
            value = unit.features.get("value")
            agreement = (
                "singular"
                if isinstance(value, (int, float)) and float(value) == 1
                else "declared plural"
            )
            return (
                f"{surface!r} satisfied counted category {token.cat!r} via "
                f"{chain}, count {value!r}, and {agreement} agreement"
            )
        if token.possessed and len(units) == 1:
            unit = units[0]
            return (
                f"{surface!r} satisfied possessed category {token.cat!r} via "
                f"{chain}, owner {unit.features.get('owner')!r}, and noun "
                f"lemma {unit.features.get('lemma')!r}"
            )
        return f"{surface!r} satisfied category {token.cat!r} via {chain}"
    if token.common_noun_cat is not None and len(units) == 1:
        unit = units[0]
        if unit.sense() == "noun":
            chain = " → ".join(category_path)
            return (
                f"{surface!r} satisfied entity type as a common noun in "
                f"category {token.common_noun_cat!r} via {chain}"
            )
        return (
            f"{surface!r} satisfied entity type independently as a "
            f"{unit.sense() or 'referential'} expression; the common-noun "
            "category gate did not apply"
        )
    if token.type == "counted" and len(units) == 1:
        unit = units[0]
        value = unit.features.get("value")
        agreement = (
            "singular" if isinstance(value, (int, float)) and value == 1
            else "declared plural"
        )
        return (
            f"{surface!r} satisfied type 'counted' through count "
            f"{value!r}, noun lemma {unit.features.get('lemma')!r}, and "
            f"{agreement} agreement"
        )
    if token.type == "possessed" and len(units) == 1:
        unit = units[0]
        number = (
            "declared plural"
            if unit.features.get("number") == "plural"
            else "singular"
        )
        return (
            f"{surface!r} satisfied type 'possessed' through owner "
            f"{unit.features.get('owner')!r}, noun lemma "
            f"{unit.features.get('lemma')!r}, and {number} head morphology"
        )
    if (
        token.type == "fraction"
        and len(units) == 1
        and units[0].features.get("fraction_count") is not None
    ):
        unit = units[0]
        boundaries = []
        if token.fraction_positive:
            boundaries.append("strictly positive")
        if token.fraction_within_whole:
            boundaries.append("within the declared whole")
        if token.word_fraction_within_whole:
            boundaries.append("word fraction within one whole")
        boundary = f", {' and '.join(boundaries)}" if boundaries else ""
        return (
            f"{surface!r} satisfied type 'fraction' through explicit count "
            f"{unit.features.get('fraction_count')!r} and declared plural "
            f"fraction lemma {unit.features.get('fraction_lemma')!r}"
            f"{boundary}"
        )
    if token.type == "fraction" and (
        token.fraction_within_whole
        or token.word_fraction_within_whole
        or token.fraction_positive
    ):
        value = units[0].features.get("value") if len(units) == 1 else None
        boundaries = []
        if token.fraction_positive:
            boundaries.append("strictly positive")
        if token.fraction_within_whole:
            boundaries.append("within the declared whole")
        if token.word_fraction_within_whole:
            boundaries.append("word fraction within one whole")
        return (
            f"{surface!r} satisfied type 'fraction' with value {value!r} "
            f"that is {' and '.join(boundaries)}"
        )
    senses = sorted({unit.sense() for unit in units if unit.sense()})
    value_kinds = sorted(
        {
            str(unit.features["value_kind"])
            for unit in units
            if unit.features.get("value_kind") is not None
        }
    )
    evidence = (
        f"value kind {', '.join(value_kinds)!r}"
        if value_kinds
        else f"committed sense {', '.join(senses)!r}"
        if senses
        else "the matcher's structural and lexical gates"
    )
    return f"{surface!r} satisfied type {token.type!r} through {evidence}"


_WHERE_FIELDS = (
    "same_lemma",
    "same_surface",
    "same_number",
    "same_category_membership",
    "number_compatible",
    "bound_requires_type",
    "bound_requires_category",
    "bound_rejects_category",
    "category_requires_bound",
    "bound_requires_form",
    "polarity_compatible",
    "proportional_delta_compatible",
    "same_presence",
    "mutually_exclusive",
    "verb_role_compatible",
    "verb_roles_compatible",
    "measure_holder_compatible",
    "partitive_compatible",
    "same_phrase",
    "distinct",
    "category_nonoverlap",
    "category_contains",
    "distinct_owner",
    "distinct_from_owner",
    "attribute_compatible",
    "modifier_host_compatible",
    "adverb_verb_compatible",
    "distinct_measure",
    "name_count",
    "absent",
    "slot_not_category",
    "unbound",
)


def _where_expression(rule: PatternRule, index: int) -> tuple[str, tuple[str, ...]]:
    pred = rule.where[index]
    kind = next(
        name for name in _WHERE_FIELDS if getattr(pred, name) is not None
    )
    value = getattr(pred, kind)
    if isinstance(value, list):
        names = tuple(value)
        rendered = ", ".join(value)
    elif kind == "same_category_membership":
        names = tuple(value.slots)
        rendered = f"slots={value.slots!r}, cat={value.cat!r}"
    elif kind == "attribute_compatible":
        names = (value.attribute, value.noun)
        rendered = (
            f"attribute={value.attribute!r}, noun={value.noun!r}"
        )
    elif kind == "modifier_host_compatible":
        names = tuple(
            name
            for name in (value.modifier, value.host, value.object)
            if name is not None
        )
        rendered = f"modifier={value.modifier!r}, host={value.host!r}"
        if value.object is not None:
            rendered += f", object={value.object!r}"
    elif kind == "adverb_verb_compatible":
        names = (value.adverb, value.verb)
        rendered = f"adverb={value.adverb!r}, verb={value.verb!r}"
    elif kind == "partitive_compatible":
        names = (value.measure, value.substance)
        rendered = (
            f"measure={value.measure!r}, substance={value.substance!r}"
        )
    elif kind == "bound_requires_type":
        names = (value.bound, value.slot)
        rendered = (
            f"bound={value.bound!r}, slot={value.slot!r}, "
            f"type={value.type!r}"
        )
    elif kind == "bound_requires_category":
        names = (value.bound, value.slot)
        rendered = (
            f"bound={value.bound!r}, slot={value.slot!r}, "
            f"cat={value.cat!r}, "
            f"allow_proper_name={value.allow_proper_name!r}"
        )
    elif kind == "bound_rejects_category":
        names = (value.bound, value.slot)
        rendered = (
            f"bound={value.bound!r}, slot={value.slot!r}, "
            f"cat={value.cat!r}"
        )
    elif kind == "category_requires_bound":
        names = (value.slot, value.bound)
        rendered = (
            f"slot={value.slot!r}, cat={value.cat!r}, "
            f"bound={value.bound!r}"
        )
    elif kind == "bound_requires_form":
        names = (value.bound, value.slot)
        rendered = (
            f"bound={value.bound!r}, slot={value.slot!r}, "
            f"form={value.form!r}"
        )
    elif kind == "polarity_compatible":
        names = tuple(value.slots)
        rendered = ", ".join(
            f"{slot} within {category!r}"
            for slot, category in zip(
                value.slots, value.categories, strict=True
            )
        )
    elif kind == "proportional_delta_compatible":
        names = (value.fraction, value.direction)
        rendered = (
            f"fraction={value.fraction!r}, "
            f"direction={value.direction!r}, "
            f"direction_cat={value.direction_cat!r}"
        )
    elif kind == "verb_role_compatible":
        names = (value.verb, *value.roles)
        role_boundary = (
            f"role_cat={value.role_cat!r}"
            if value.role_cat is not None
            else f"excluded_role_cat={value.excluded_role_cat!r}"
        )
        rendered = (
            f"verb={value.verb!r}, roles={value.roles!r}, "
            f"verb_cat={value.verb_cat!r}, {role_boundary}, "
            f"allow_plural_class={value.allow_plural_class!r}"
        )
    elif kind == "verb_roles_compatible":
        names = (
            value.verb,
            *(
                slot
                for slots in value.roles.values()
                for slot in slots
            ),
        )
        rendered = (
            f"verb={value.verb!r}, roles={value.roles!r}, "
            f"allow_proper_name={value.allow_proper_name!r}, "
            f"allow_plural_class={value.allow_plural_class!r}"
        )
    elif kind == "measure_holder_compatible":
        names = (value.measure, *value.holders)
        rendered = (
            f"measure={value.measure!r}, holders={value.holders!r}, "
            f"allow_proper_name={value.allow_proper_name!r}, "
            "proper_name_measure_categories="
            f"{value.proper_name_measure_categories!r}, "
            f"when_declared={value.when_declared!r}"
        )
    elif kind == "distinct_from_owner":
        names = (value.entity, value.possessed)
        rendered = (
            f"entity={value.entity!r}, possessed={value.possessed!r}"
        )
    elif isinstance(value, dict):
        slot = value.get("slot")
        names = (slot,) if isinstance(slot, str) else ()
        rendered = ", ".join(f"{key}={item!r}" for key, item in value.items())
    else:  # pragma: no cover - schema keeps the predicate set closed
        names = ()
        rendered = repr(value)
    return f"{kind}({rendered})", names


def _where_reason(
    rule: PatternRule,
    index: int,
    slots: dict[str, Unit | tuple[Unit, ...]],
    reg: Registry,
) -> str:
    pred = rule.where[index]
    if pred.same_presence is not None:
        present = [name for name in pred.same_presence if name in slots]
        if present:
            return "all paired slots were present: " + ", ".join(present)
        return "all paired slots were absent"
    if pred.same_category_membership is not None:
        agreement = pred.same_category_membership
        rendered = []
        for slot_name in agreement.slots:
            units = _slot_units(slots.get(slot_name))
            if not units:
                return f"the target match did not expose slot {slot_name!r}"
            identity = _unit_lemma(units[0], reg)
            membership = _filler_in_category(
                _Filler(surface=units[0].surface, identity=identity),
                agreement.cat,
                reg,
            )
            rendered.append(
                f"{slot_name}={identity!r} was "
                + ("inside" if membership else "outside")
                + f" {agreement.cat!r}"
            )
        return "; ".join(rendered) + "; memberships agreed"
    if pred.bound_requires_category is not None:
        requirement = pred.bound_requires_category
        if requirement.bound not in slots:
            return (
                f"{requirement.bound!r} was unbound, so no category "
                f"restriction applied to {requirement.slot!r}"
            )
        units = _slot_units(slots.get(requirement.slot))
        if not units:
            return (
                f"{requirement.bound!r} was bound but "
                f"{requirement.slot!r} was not exposed"
            )
        identity = _unit_lemma(units[0], reg)
        return (
            f"{requirement.bound!r} was bound, so "
            f"{requirement.slot}={identity!r} satisfied category "
            f"{requirement.cat!r}"
            + (
                " or the proper-name alternative"
                if requirement.allow_proper_name
                else ""
            )
        )
    if pred.category_requires_bound is not None:
        requirement = pred.category_requires_bound
        units = _slot_units(slots.get(requirement.slot))
        if not units:
            return f"the target match did not expose slot {requirement.slot!r}"
        identity = _unit_lemma(units[0], reg)
        return (
            f"{requirement.slot}={identity!r} satisfied category "
            f"{requirement.cat!r}, so {requirement.bound!r} was bound"
        )
    if pred.bound_rejects_category is not None:
        requirement = pred.bound_rejects_category
        if requirement.bound not in slots:
            return (
                f"{requirement.bound!r} was unbound, so no category "
                f"exclusion applied to {requirement.slot!r}"
            )
        units = _slot_units(slots.get(requirement.slot))
        if not units:
            return (
                f"{requirement.bound!r} was bound but "
                f"{requirement.slot!r} was not exposed"
            )
        identity = _unit_lemma(units[0], reg)
        return (
            f"{requirement.bound!r} was bound, so "
            f"{requirement.slot}={identity!r} remained outside "
            f"category {requirement.cat!r}"
        )
    if pred.bound_requires_form is not None:
        requirement = pred.bound_requires_form
        if requirement.bound not in slots:
            return (
                f"{requirement.bound!r} was unbound, so no morphology "
                f"restriction applied to {requirement.slot!r}"
            )
        units = _slot_units(slots.get(requirement.slot))
        if not units:
            return (
                f"{requirement.bound!r} was bound but "
                f"{requirement.slot!r} was not exposed"
            )
        return (
            f"{requirement.bound!r} was bound, so "
            f"{requirement.slot}={units[0].surface!r} satisfied "
            f"{requirement.form!r} verb form"
        )
    if pred.polarity_compatible is not None:
        rendered = []
        for slot_name, category in zip(
            pred.polarity_compatible.slots,
            pred.polarity_compatible.categories,
            strict=True,
        ):
            units = _slot_units(slots.get(slot_name))
            if not units:
                rendered.append(f"{slot_name}=unbound")
                continue
            polarity = _scoped_filler_polarity(
                _Filler(
                    surface=units[0].surface,
                    identity=_unit_lemma(units[0], reg),
                ),
                category,
                reg,
            )
            rendered.append(
                f"{slot_name}={units[0].surface!r}"
                + (
                    " was neutral"
                    if polarity is None
                    else f" declared polarity {polarity:+d}"
                )
                + f" within {category!r}"
            )
        return "; ".join(rendered)
    if pred.proportional_delta_compatible is not None:
        compatibility = pred.proportional_delta_compatible
        fraction_units = _slot_units(slots.get(compatibility.fraction))
        direction_units = _slot_units(slots.get(compatibility.direction))
        if not fraction_units or not direction_units:
            return "the target match did not expose both proportional roles"
        value = fraction_units[0].features.get("value")
        direction = direction_units[0]
        polarity = _scoped_filler_polarity(
            _Filler(
                surface=direction.surface,
                identity=_unit_lemma(direction, reg),
            ),
            compatibility.direction_cat,
            reg,
        )
        boundary = "unbounded increase" if polarity == 1 else "at most 1"
        return (
            f"{compatibility.fraction}={value!r}, "
            f"{compatibility.direction}={direction.surface!r} had declared "
            f"polarity {polarity!r}; allowed magnitude was {boundary}"
        )
    if pred.category_nonoverlap is not None:
        rendered = []
        for role_name in pred.category_nonoverlap:
            units = _slot_units(slots.get(role_name))
            if not units:
                rendered.append(f"{role_name}=unbound")
                continue
            rendered.append(
                f"{role_name}={_unit_lemma(units[0], reg)!r}"
            )
        return (
            ", ".join(rendered)
            + " had no unresolved declared category/member containment"
        )
    if pred.category_contains is not None:
        containment = pred.category_contains
        rendered = []
        for role_name in (containment.collection, *containment.members):
            units = _slot_units(slots.get(role_name))
            if not units:
                rendered.append(f"{role_name}=unbound")
                continue
            rendered.append(
                f"{role_name}={_unit_lemma(units[0], reg)!r}"
            )
        return (
            ", ".join(rendered)
            + " had directional declared category/member containment"
        )
    if pred.verb_role_compatible is not None:
        compatibility = pred.verb_role_compatible
        verb_units = _slot_units(slots.get(compatibility.verb))
        if not verb_units:
            return "the target match did not expose the governing verb"
        verb_unit = verb_units[0]
        verb = _unit_lemma(verb_unit, reg)
        if not _filler_in_category(
            _Filler(surface=verb_unit.surface, identity=verb),
            compatibility.verb_cat,
            reg,
        ):
            return (
                f"{compatibility.verb}={verb!r} was outside triggering "
                f"category {compatibility.verb_cat!r}"
            )
        rendered_roles = []
        for role_name in compatibility.roles:
            units = _slot_units(slots.get(role_name))
            if units:
                rendered_roles.append(
                    f"{role_name}={_unit_lemma(units[0], reg)!r}"
                )
        if compatibility.role_cat is not None:
            boundary = (
                f"required {compatibility.role_cat!r} or proper-name roles"
            )
            if compatibility.allow_plural_class:
                boundary += " or a plural comparison class"
        else:
            boundary = (
                f"excluded {compatibility.excluded_role_cat!r} roles"
            )
        return (
            f"{compatibility.verb}={verb!r} {boundary}: "
            + ", ".join(rendered_roles)
        )
    if pred.verb_roles_compatible is not None:
        compatibility = pred.verb_roles_compatible
        verb_units = _slot_units(slots.get(compatibility.verb))
        if not verb_units:
            return "the target match did not expose the governing verb"
        verb = _unit_lemma(verb_units[0], reg)
        frames = reg.selectional_frames(verb)
        if not frames:
            if compatibility.require_declared_frame:
                return (
                    f"{compatibility.verb}={verb!r} required a declared "
                    "role frame"
                )
            return (
                f"{compatibility.verb}={verb!r} had no declared role frame; "
                "the compatibility boundary remained open"
            )
        rendered_roles = []
        for semantic_role, role_names in compatibility.roles.items():
            values = []
            for role_name in role_names:
                units = _slot_units(slots.get(role_name))
                if units:
                    values.append(
                        f"{role_name}={_unit_lemma(units[0], reg)!r}"
                    )
            rendered_roles.append(
                f"{semantic_role}({', '.join(values)})"
            )
        frame_names = ", ".join(category for category, _ in frames)
        return (
            f"{compatibility.verb}={verb!r} satisfied category-owned frame "
            f"{frame_names}: " + "; ".join(rendered_roles)
        )
    if pred.measure_holder_compatible is not None:
        compatibility = pred.measure_holder_compatible
        measure_units = _slot_units(slots.get(compatibility.measure))
        if not measure_units:
            return "the target match did not expose the governing measure"
        measure = _unit_lemma(measure_units[0], reg)
        attribute_units = (
            _slot_units(slots.get(compatibility.attribute))
            if compatibility.attribute is not None
            else ()
        )
        attribute = (
            _unit_lemma(attribute_units[0], reg)
            if attribute_units
            else None
        )
        if (
            compatibility.when_declared
            and not reg.measure_has_holder_boundary(measure)
        ):
            return (
                f"{compatibility.measure}={measure!r} had no declared "
                "holder boundary, so the conditional relation was neutral"
            )
        rendered = []
        for holder_name in compatibility.holders:
            holder_units = _slot_units(slots.get(holder_name))
            if not holder_units:
                rendered.append(f"{holder_name}=unbound")
                continue
            holder = holder_units[0]
            holder_lemma = _unit_lemma(holder, reg)
            if (
                compatibility.allow_proper_name
                and _role_is_proper_name(holder, reg)
            ):
                categories = tuple(
                    compatibility.proper_name_measure_categories
                )
                permitted = not categories or any(
                    (
                        attribute is None
                        and reg.word_in_category(measure, category)
                    )
                    or (
                        attribute is not None
                        and any(
                            reg.category_routes_overlap(
                                route_category, category
                            )
                            for _, route_category in (
                                reg.attribute_compatibility_pairs(
                                    attribute, measure
                                )
                            )
                        )
                    )
                    for category in categories
                )
                rendered.append(
                    f"{holder_name}={holder_lemma!r} (proper name; "
                    + ("permitted" if permitted else "not permitted")
                    + ")"
                )
                continue
            pairs = reg.measure_holder_compatibility_pairs(
                measure, holder_lemma, attribute
            )
            licences = ", ".join(
                f"{measure_category} → {holder_category}"
                for measure_category, holder_category in pairs
            )
            rendered.append(
                f"{holder_name}={holder_lemma!r} via {licences}"
            )
        return f"{compatibility.measure}={measure!r}: " + "; ".join(rendered)
    if pred.attribute_compatible is not None:
        attribute_name = pred.attribute_compatible.attribute
        noun_name = pred.attribute_compatible.noun
        attribute_units = _slot_units(slots.get(attribute_name))
        noun_units = _slot_units(slots.get(noun_name))
        if not attribute_units and not noun_units:
            return "both optional compatibility slots were absent"
        if not attribute_units or not noun_units:
            return "the target match did not expose both compatibility slots"
        attribute = _unit_lemma(attribute_units[0], reg)
        noun = _unit_lemma(noun_units[0], reg)
        pairs = reg.attribute_compatibility_pairs(attribute, noun)
        rendered = ", ".join(
            f"{attribute_category} → {noun_category}"
            for attribute_category, noun_category in pairs
        )
        return (
            f"{attribute_name}={attribute!r}, {noun_name}={noun!r} matched "
            f"{rendered}"
        )
    if pred.adverb_verb_compatible is not None:
        adverb_name = pred.adverb_verb_compatible.adverb
        verb_name = pred.adverb_verb_compatible.verb
        adverb_units = _slot_units(slots.get(adverb_name))
        verb_units = _slot_units(slots.get(verb_name))
        if not adverb_units:
            return "the optional adverb was absent"
        if not verb_units:
            return "the target match did not expose the modified verb"
        adverb = adverb_units[0].surface.casefold()
        verb = verb_units[0].surface.casefold()
        pairs = reg.adverb_verb_compatibility_pairs(adverb, verb)
        rendered = ", ".join(
            f"{adverb_category} → {verb_category}"
            for adverb_category, verb_category in pairs
        )
        return (
            f"{adverb_name}={adverb!r}, {verb_name}={verb!r} matched "
            f"{rendered}"
        )
    if pred.modifier_host_compatible is not None:
        modifier_name = pred.modifier_host_compatible.modifier
        host_name = pred.modifier_host_compatible.host
        object_name = pred.modifier_host_compatible.object
        modifier_units = _slot_units(slots.get(modifier_name))
        host_units = _slot_units(slots.get(host_name))
        object_units = _slot_units(slots.get(object_name)) if object_name else []
        if not modifier_units:
            return "the optional modifier was absent"
        if not host_units:
            return "the target match did not expose the modifier host"
        modifier = _unit_lemma(modifier_units[0], reg)
        host = _unit_lemma(host_units[0], reg)
        pairs = reg.modifier_host_compatibility_pairs(modifier, host)
        rendered = ", ".join(
            f"{modifier_category} → {host_category}"
            for modifier_category, host_category in pairs
        )
        reason = (
            f"{modifier_name}={modifier!r}, {host_name}={host!r} "
            + (f"matched {rendered}" if rendered else "used an open modifier")
        )
        if object_name is not None:
            if not object_units:
                return "the target match did not expose the modifier object"
            object_ = _unit_lemma(object_units[0], reg)
            frames = reg.modifier_attachment_frames(modifier, object_)
            if frames:
                rendered_frames = ", ".join(
                    f"{prep} + {obj} → {host_cat}"
                    for prep, obj, host_cat in frames
                )
                reason += f"; {object_name}={object_!r} activated {rendered_frames}"
        return reason
    if pred.distinct_from_owner is not None:
        entity_name = pred.distinct_from_owner.entity
        possessed_name = pred.distinct_from_owner.possessed
        entity_units = _slot_units(slots.get(entity_name))
        possessed_units = _slot_units(slots.get(possessed_name))
        if not entity_units or not possessed_units:
            return "the target match did not expose both owner roles"
        entity = _unit_lemma(entity_units[0], reg)
        owner = possessed_units[0].features.get("owner")
        return (
            f"{entity_name}={entity!r} differed from "
            f"{possessed_name}.owner={owner!r}"
        )
    if pred.slot_not_category is not None:
        slot_name = pred.slot_not_category.get("slot", "")
        category = pred.slot_not_category.get("cat", "")
        units = _slot_units(slots.get(slot_name))
        if not units:
            return f"the target match did not expose slot {slot_name!r}"
        identity = _unit_lemma(units[0], reg)
        return (
            f"{slot_name}={identity!r} was not in category {category!r}"
        )
    if pred.absent is not None:
        category = pred.absent["cat"]
        return f"no analyzed unit belonged to category {category!r}"
    if pred.unbound is not None:
        rendered = ", ".join(repr(name) for name in pred.unbound)
        noun = "slot" if len(pred.unbound) == 1 else "slots"
        return f"{noun} {rendered} remained unbound"
    if pred.distinct_measure is not None:
        rendered: list[str] = []
        for name in pred.distinct_measure:
            units = _slot_units(slots.get(name))
            if not units:
                return f"the target match did not expose slot {name!r}"
            unit = units[0]
            key = (
                _unit_lemma(unit, reg),
                unit.features.get("label"),
                unit.features.get("qualifier"),
            )
            rendered.append(f"{name}={key!r}")
        return ", ".join(rendered) + " were distinct measure keys"
    if pred.bound_requires_type is not None:
        requirement = pred.bound_requires_type
        if requirement.bound not in slots:
            return (
                f"{requirement.bound!r} remained unbound, so "
                f"{requirement.slot!r} retained its declared type"
            )
        units = _slot_units(slots.get(requirement.slot))
        binding = " ".join(unit.surface for unit in units)
        return (
            f"{requirement.bound!r} was bound, so "
            f"{requirement.slot}={binding!r} satisfied type "
            f"{requirement.type!r}"
        )
    names = (
        pred.distinct
        or pred.distinct_owner
        or pred.same_lemma
        or pred.same_surface
        or pred.same_number
        or pred.number_compatible
    )
    if names is None:
        expression, _ = _where_expression(rule, index)
        return f"the target match confirms {expression} passed"
    if (
        pred.same_number is not None
        or pred.number_compatible is not None
    ):
        values = {}
        for name in names:
            units = _slot_units(slots.get(name))
            if not units:
                values[name] = ""
                continue
            unit = units[0]
            number = unit.features.get("number")
            if unit.features.get("value_kind") == "count":
                value = unit.features.get("value")
                if isinstance(value, (int, float)):
                    number = "singular" if float(value) == 1 else "plural"
            values[name] = str(number or "")
    elif pred.distinct_owner is not None:
        values = {
            name: "/".join(
                str(unit.features.get("owner") or "")
                for unit in _slot_units(slots.get(name))
            )
            for name in names
        }
    elif pred.same_surface is not None:
        values = {
            name: "/".join(
                unit.surface.casefold()
                for unit in _slot_units(slots.get(name))
            )
            for name in names
        }
    else:
        values = {
            name: "/".join(
                _unit_lemma(unit, reg) for unit in _slot_units(slots.get(name))
            )
            for name in names
        }
    relation = (
        "were distinct"
        if pred.distinct is not None
        else "had distinct owners"
        if pred.distinct_owner is not None
        else "shared grammatical number"
        if pred.same_number is not None
        else "had compatible grammatical number"
        if pred.number_compatible is not None
        else "shared a surface form"
        if pred.same_surface is not None
        else "shared a lemma"
    )
    rendered = ", ".join(f"{name}={value!r}" for name, value in values.items())
    return f"{rendered} {relation}"


def _explain_candidate(
    project: Project,
    rule: PatternRule,
    fixtures: _Fixtures,
    reading: Any,
    target: RuleMatchResult | None,
    requested: dict[str, str],
    optional_choices: dict[tuple[int, ...], bool] | None = None,
    lexical_relaxations: tuple[LexicalRelaxation, ...] = (),
) -> tuple[tuple[PremiseSummary, ...], tuple[ConsumedUnitSummary, ...]]:
    seq = _flat_sentence(rule)
    unit_by_uid = {unit.uid: unit for unit in reading.units}
    slots = target.match.slots if target is not None else {}
    target_uids = target.match.consumed if target is not None else ()
    claimed = {
        unit.uid
        for value in slots.values()
        for unit in _slot_units(value)
    }
    remaining_literals = [
        unit_by_uid[uid]
        for uid in target_uids
        if uid in unit_by_uid and uid not in claimed
    ]
    premises: list[PremiseSummary] = []
    relaxations_by_slot = {
        relaxation.slot: relaxation for relaxation in lexical_relaxations
    }

    def relaxation_reason(relaxation: LexicalRelaxation) -> str:
        outcome = (
            "the ordinary matcher nevertheless retained the target rule"
            if target is not None
            else "the ordinary matcher was allowed to reject the target rule"
        )
        return (
            "lexical boundary mode deliberately sampled "
            f"{relaxation.surface!r} from {relaxation.broader_domain}, "
            f"outside the strict {relaxation.requirement}; {outcome}"
        )

    if seq is None:
        premises.append(
            PremiseSummary(
                index=0,
                kind="rule",
                expression="nested or multi-sentence premise pattern",
                binding=None,
                status="passed" if target is not None else "unverified",
                reason=(
                    "the reloaded target matched, but its edited pattern is "
                    "outside the flat token inspector"
                    if target is not None
                    else (
                        "the reloaded target was absent and its edited pattern "
                        "is outside the flat token inspector"
                    )
                ),
                sources=_dedupe_sources(
                    [project.source_index.rules.get(rule.id)]
                ),
            )
        )

    resolved_optional_choices: dict[tuple[int, ...], bool] = {}
    requested_optional_choices = optional_choices or {}
    unbound_optional_paths = _unbound_optional_paths(rule, seq or [])

    def optional_group_has_match_evidence(token: MatchToken) -> bool:
        assert token.opt is not None
        for _, child, _ in _leaf_tokens(token.opt):
            if child.slot is not None and child.slot in slots:
                return True
            if child.lit is not None and any(
                unit.surface.casefold()
                in {option.casefold() for option in child.lit_options}
                for unit in remaining_literals
            ):
                return True
        return False

    for token_no, (path, token, optional_ancestors) in enumerate(
        _token_nodes(seq or [])
    ):
        source = _rule_token_source(project, rule.id, path)
        parent_active = all(
            resolved_optional_choices.get(ancestor, False)
            for ancestor in optional_ancestors
        )
        if token.opt is not None:
            if not parent_active:
                state = "inactive"
                included = False
                reason = "an enclosing optional branch was omitted"
            else:
                included = requested_optional_choices.get(
                    path,
                    optional_group_has_match_evidence(token),
                )
                state = "included" if included else "omitted"
                if path in unbound_optional_paths:
                    sentinels = ", ".join(
                        repr(name) for name in unbound_optional_paths[path]
                    )
                    reason = (
                        "this negative-lookahead branch was omitted because "
                        f"where requires {sentinels} to remain unbound"
                    )
                elif path in requested_optional_choices:
                    reason = (
                        "the generator included this declared optional branch"
                        if included
                        else "the generator omitted this declared optional branch"
                    )
                else:
                    reason = (
                        "the matcher consumed evidence from this optional branch"
                        if included
                        else "the matcher exposed no consumed evidence from "
                        "this optional branch"
                    )
            resolved_optional_choices[path] = included
            premises.append(
                PremiseSummary(
                    index=token_no,
                    kind="token",
                    expression=_token_expression(token),
                    binding=state,
                    status="passed",
                    reason=reason,
                    slot_type="optional",
                    sources=_dedupe_sources([source]),
                )
            )
            continue

        if not parent_active:
            premises.append(
                PremiseSummary(
                    index=token_no,
                    kind="token",
                    expression=_token_expression(token),
                    binding=None,
                    status="unverified",
                    reason="this token belongs to an omitted optional branch",
                    slot=token.slot,
                    slot_type=token.type or token.cat,
                    sources=_dedupe_sources([source]),
                )
            )
            continue

        if target is None:
            bound = requested.get(token.slot) if token.slot is not None else (
                token.lit_options[0] if token.lit_options else None
            )
            relaxation = (
                relaxations_by_slot.get(token.slot)
                if token.slot is not None
                else None
            )
            absent_sources: list[SourceRef | None] = [source]
            if token.cat is not None:
                absent_sources.append(
                    project.source_index.categories.get(token.cat)
                )
            if relaxation is not None:
                absent_sources.append(
                    project.source_index.lexicon.get(relaxation.identity)
                )
            premises.append(
                PremiseSummary(
                    index=token_no,
                    kind="token",
                    expression=_token_expression(token),
                    binding=bound,
                    status="relaxed" if relaxation is not None else "unverified",
                    reason=(
                        relaxation_reason(relaxation)
                        if relaxation is not None
                        else (
                            "target rule was absent; the matcher exposes no "
                            "partial premise result"
                        )
                    ),
                    slot=token.slot,
                    slot_type=token.type or token.cat,
                    sources=_dedupe_sources(absent_sources),
                )
            )
            continue

        if token.slot is not None:
            units = _slot_units(slots.get(token.slot))
        else:
            options = {option.casefold() for option in token.lit_options}
            literal_no = next(
                (
                    index
                    for index, unit in enumerate(remaining_literals)
                    if unit.surface.casefold() in options
                ),
                None,
            )
            units = (
                (remaining_literals.pop(literal_no),)
                if literal_no is not None
                else ()
            )
        category_path, category_refs = (
            _category_evidence(project, token, units[0])
            if units
            else ((), [])
        )
        sources: list[SourceRef | None] = [
            source
        ]
        for unit in units:
            sources.extend(
                _counted_lexical_sources(project, unit)
                if token.type == "counted" or token.counted
                else _possessed_sources(project, fixtures, unit)
                if token.type == "possessed" or token.possessed
                else _lexical_sources(project, unit)
            )
            sources.extend(_numeric_sources(project, token, unit))
            fixture = fixtures.sources.get(unit.surface.casefold())
            sources.append(fixture)
        sources.extend(category_refs)
        binding = " ".join(unit.surface for unit in units) or None
        relaxation = (
            relaxations_by_slot.get(token.slot)
            if token.slot is not None
            else None
        )
        premises.append(
            PremiseSummary(
                index=token_no,
                kind="token",
                expression=_token_expression(token),
                binding=binding,
                status=(
                    "relaxed"
                    if relaxation is not None
                    else "passed"
                    if units
                    else "unverified"
                ),
                reason=(
                    relaxation_reason(relaxation)
                    if relaxation is not None
                    else _token_reason(token, units, category_path)
                    if units
                    else "the matcher reported no consumable unit for this token"
                ),
                slot=token.slot,
                slot_type=token.type or token.cat,
                category_path=category_path,
                consumed=tuple(unit.uid for unit in units),
                sources=_dedupe_sources(sources),
            )
        )

    actual_bindings = _bindings(target) if target is not None else {}
    for where_no in range(len(rule.where)):
        expression, names = _where_expression(rule, where_no)
        predicate = rule.where[where_no]
        where_sources: list[SourceRef | None] = [
            project.source_index.rule_where.get((rule.id, where_no))
        ]
        if target is not None and predicate.attribute_compatible is not None:
            where_sources.extend(
                _attribute_compatibility_evidence(
                    project, predicate.attribute_compatible, slots
                )
            )
        if (
            target is not None
            and predicate.adverb_verb_compatible is not None
        ):
            where_sources.extend(
                _adverb_verb_compatibility_evidence(
                    project, predicate.adverb_verb_compatible, slots
                )
            )
        if (
            target is not None
            and predicate.modifier_host_compatible is not None
        ):
            modifier_units = _slot_units(
                slots.get(predicate.modifier_host_compatible.modifier)
            )
            host_units = _slot_units(
                slots.get(predicate.modifier_host_compatible.host)
            )
            object_name = predicate.modifier_host_compatible.object
            object_units = (
                _slot_units(slots.get(object_name))
                if object_name is not None
                else ()
            )
            if modifier_units and host_units:
                modifier = _unit_lemma(modifier_units[0], project.registry)
                host = _unit_lemma(host_units[0], project.registry)
                for pair in project.registry.modifier_host_compatibility_pairs(
                    modifier, host
                ):
                    where_sources.append(
                        project.source_index.modifier_host_compatibility.get(pair)
                    )
                if object_units:
                    object_ = _unit_lemma(object_units[0], project.registry)
                    for frame in project.registry.modifier_attachment_frames(
                        modifier, object_
                    ):
                        where_sources.append(
                            project.source_index.modifier_attachment_compatibility.get(
                                frame
                            )
                        )
        if (
            target is not None
            and predicate.measure_holder_compatible is not None
        ):
            where_sources.extend(
                _measure_holder_compatibility_evidence(
                    project,
                    predicate.measure_holder_compatible.attribute,
                    predicate.measure_holder_compatible.measure,
                    tuple(predicate.measure_holder_compatible.holders),
                    slots,
                )
            )
        if predicate.absent is not None:
            where_sources.append(
                project.source_index.categories.get(predicate.absent["cat"])
            )
        if predicate.bound_requires_category is not None:
            where_sources.append(
                project.source_index.categories.get(
                    predicate.bound_requires_category.cat
                )
            )
        if predicate.bound_rejects_category is not None:
            where_sources.append(
                project.source_index.categories.get(
                    predicate.bound_rejects_category.cat
                )
            )
        if predicate.category_requires_bound is not None:
            where_sources.append(
                project.source_index.categories.get(
                    predicate.category_requires_bound.cat
                )
            )
        if predicate.same_category_membership is not None:
            where_sources.append(
                project.source_index.categories.get(
                    predicate.same_category_membership.cat
                )
            )
        if predicate.polarity_compatible is not None:
            where_sources.extend(
                project.source_index.categories.get(category)
                for category in predicate.polarity_compatible.categories
            )
        if predicate.proportional_delta_compatible is not None:
            where_sources.append(
                project.source_index.categories.get(
                    predicate.proportional_delta_compatible.direction_cat
                )
            )
        if predicate.category_nonoverlap is not None and target is not None:
            for role_name in predicate.category_nonoverlap:
                role_units = _slot_units(slots.get(role_name))
                if role_units:
                    where_sources.append(
                        project.source_index.categories.get(
                            _unit_lemma(role_units[0], project.registry)
                        )
                    )
        if predicate.category_contains is not None and target is not None:
            containment = predicate.category_contains
            for role_name in (containment.collection, *containment.members):
                role_units = _slot_units(slots.get(role_name))
                if role_units:
                    where_sources.append(
                        project.source_index.categories.get(
                            _unit_lemma(role_units[0], project.registry)
                        )
                    )
        if predicate.verb_role_compatible is not None:
            role_category = (
                predicate.verb_role_compatible.role_cat
                or predicate.verb_role_compatible.excluded_role_cat
            )
            where_sources.extend(
                (
                    project.source_index.categories.get(
                        predicate.verb_role_compatible.verb_cat
                    ),
                    project.source_index.categories.get(
                        role_category
                    ),
                )
            )
        if predicate.verb_roles_compatible is not None and target is not None:
            verb_units = _slot_units(
                slots.get(predicate.verb_roles_compatible.verb)
            )
            if verb_units:
                for category, frame in project.registry.selectional_frames(
                    _unit_lemma(verb_units[0], project.registry)
                ):
                    where_sources.append(
                        project.source_index.categories.get(category)
                    )
                    where_sources.extend(
                        project.source_index.categories.get(target_category)
                        for target_category in frame.values()
                    )
        premises.append(
            PremiseSummary(
                index=where_no,
                kind="where",
                expression=expression,
                binding=(
                    ", ".join(f"{name}=unbound" for name in names)
                    if predicate.unbound is not None
                    else ", ".join(
                        f"{name}="
                        f"{actual_bindings.get(name, requested.get(name, ''))}"
                        for name in names
                    )
                ),
                status="passed" if target is not None else "unverified",
                reason=(
                    _where_reason(rule, where_no, slots, project.registry)
                    if target is not None
                    else (
                        "target rule was absent; the matcher exposes no "
                        "partial predicate result"
                    )
                ),
                sources=_dedupe_sources(where_sources),
            )
        )

    consumed = tuple(
        ConsumedUnitSummary(
            uid=uid,
            surface=unit_by_uid[uid].surface,
            sense=unit_by_uid[uid].sense(),
            lemma=_unit_lemma(unit_by_uid[uid], project.registry),
        )
        for uid in target_uids
        if uid in unit_by_uid
    )
    return tuple(premises), consumed


def _collision_json(collision: Any) -> dict[str, Any]:
    return {
        "key": _jsonable(collision.key),
        "a_source": collision.a_source,
        "b_source": collision.b_source,
        "a_value": _jsonable(collision.a_value),
        "b_value": _jsonable(collision.b_value),
    }


def _candidate_from_reading(
    project: Project,
    *,
    rule: PatternRule | None,
    target_rule_id: str,
    sentence: str,
    seed: int,
    requested_bindings: dict[str, str],
    attempts: int,
    fixtures: _Fixtures,
    reading: Any,
    document: Any,
    results: list[RuleMatchResult],
    origin: Literal["generated", "reading"] = "generated",
    generation_mode: GenerationMode = "strict",
    optional_choices: dict[tuple[int, ...], bool] | None = None,
    lexical_relaxations: tuple[LexicalRelaxation, ...] = (),
    context_before: tuple[str, ...] = (),
    context_after: tuple[str, ...] = (),
) -> GenerationCandidate:
    """Project one ordinary reader result into the authoring candidate record."""

    premise_results = _premise_match_results(results)
    safety_results = _safety_interception_results(
        results, project.registry
    )
    target_pool = (
        safety_results
        if generation_mode == "safety_boundary"
        else premise_results
    )
    target_results = [
        result
        for result in target_pool
        if result.match.rule.id == target_rule_id
    ]
    if origin == "generated" and generation_mode in {
        "strict",
        "safety_boundary",
    }:
        target_results = [
            result
            for result in target_results
            if _strict_round_trip_result(
                result, requested_bindings, reading, project.registry
            )
        ]
    target_result = target_results[0] if target_results else None
    if target_result is None:
        status = "absent"
        target_bindings: dict[str, str] = {}
    else:
        target_shadowed = generation_mode != "safety_boundary" and all(
            any(
                other is not result
                and subsumes(other.match, result.match, project.registry)
                for other in premise_results
            )
            for result in target_results
        )
        status = "shadowed" if target_shadowed else "matched"
        target_bindings = _bindings(target_result)
    effective_bindings = (
        target_bindings
        if origin == "reading" and target_result is not None
        else requested_bindings
    )

    if rule is None:
        premises = (
            PremiseSummary(
                index=0,
                kind="rule",
                expression=target_rule_id,
                binding=None,
                status="unverified",
                reason="the target rule is no longer declared in the reloaded project",
            ),
        )
        consumed_units: tuple[ConsumedUnitSummary, ...] = ()
    else:
        premises, consumed_units = _explain_candidate(
            project,
            rule,
            fixtures,
            reading,
            target_result,
            effective_bindings,
            optional_choices,
            lexical_relaxations,
        )

    digest = hashlib.sha256(
        (
            f"{project.registry.fingerprint}\0{origin}\0{generation_mode}\0"
            f"{seed}\0{target_rule_id}\0"
            f"{' '.join((*context_before, sentence, *context_after))}"
        ).encode()
    ).hexdigest()[:20]
    return GenerationCandidate(
        id=f"gen-{digest}",
        project=project.doc.name,
        registry_fingerprint=project.registry.fingerprint,
        generator_version=GENERATOR_VERSION,
        origin=origin,
        generation_mode=generation_mode,
        seed=seed,
        target_rule=target_rule_id,
        target_description=rule.description if rule is not None else None,
        sentence=sentence,
        requested_bindings=effective_bindings,
        target_bindings=target_bindings,
        target_status=status,
        target_specificity=(
            target_result.match.specificity if target_result is not None else None
        ),
        target_source=(
            _source_json(project.source_index.rules.get(rule.id))
            if rule is not None
            else None
        ),
        premises=premises,
        consumed_units=consumed_units,
        actual_matches=_match_summaries(
            premise_results, project, reading
        ),
        safety_interceptions=_match_summaries(
            safety_results, project, reading
        ),
        facts=tuple(
            _fact_json(
                fact,
                project,
                bindings=_matched_fact_bindings(fact, results),
            )
            for fact in document.store.facts
        ),
        collisions=tuple(
            _collision_json(collision)
            for collision in document.store.collisions
        ),
        deficiencies=tuple(reading.deficiencies()),
        attempts=attempts,
        lexical_relaxations=lexical_relaxations,
        context_before=context_before,
        context_after=context_after,
        target_sentence_index=len(context_before),
    )


def retest_candidate(
    project: Project,
    *,
    rule_id: str,
    sentence: str,
    seed: int,
    requested_bindings: dict[str, str] | None = None,
    attempts: int = 1,
    origin: Literal["generated", "reading"] = "generated",
    generation_mode: GenerationMode = "strict",
    lexical_relaxations: tuple[LexicalRelaxation, ...] = (),
    context_before: tuple[str, ...] = (),
    context_after: tuple[str, ...] = (),
) -> GenerationCandidate:
    """Re-evaluate an identical pinned sentence against the current project."""

    if not sentence.strip():
        raise GenerationError("the pinned sentence must not be empty")
    fixtures = _load_fixtures(project.root)
    rule = next(
        (candidate for candidate in project.registry.rules if candidate.id == rule_id),
        None,
    )
    if (
        rule is not None
        and rule.generation == "safety"
        and generation_mode != "safety_boundary"
    ):
        raise GenerationError(
            "a safety consumer is not a premise review target; "
            "review the sentence meaning instead"
        )
    try:
        readings = [
            analyze(
                surface,
                project.registry,
                sentence_index=index,
                tracing=True,
            )
            for index, surface in enumerate(
                (*context_before, sentence, *context_after)
            )
        ]
        reading = readings[len(context_before)]
        document = run_document(readings, project.registry)
    except Exception as exc:  # noqa: BLE001 - authoring API surfaces the defect
        raise GenerationError(
            f"could not retest the pinned sentence: {type(exc).__name__}: {exc}"
        ) from exc
    results = document.rule_results.get(reading.sentence_index, [])
    return _candidate_from_reading(
        project,
        rule=rule,
        target_rule_id=rule_id,
        sentence=sentence,
        seed=seed,
        requested_bindings=dict(requested_bindings or {}),
        attempts=attempts,
        fixtures=fixtures,
        reading=reading,
        document=document,
        results=results,
        origin=origin,
        generation_mode=generation_mode,
        lexical_relaxations=lexical_relaxations,
        context_before=context_before,
        context_after=context_after,
    )


def promote_reading_candidate(
    project: Project,
    *,
    rule_id: str,
    sentence: str,
) -> GenerationCandidate:
    """Promote one Reading sentence into the ordinary review workbench.

    The sentence is never realized or rewritten. Its stable seed exists only
    to keep candidate identity and later pinned retests reproducible.
    """

    if not sentence.strip():
        raise GenerationError("the Reading sentence must not be empty")
    seed = int.from_bytes(
        hashlib.sha256(
            (
                f"reading\0{project.registry.fingerprint}\0{rule_id}\0"
                f"{sentence}"
            ).encode()
        ).digest()[:8],
        "big",
    ) & ((1 << 53) - 1)
    return retest_candidate(
        project,
        rule_id=rule_id,
        sentence=sentence,
        seed=seed,
        origin="reading",
    )


def promote_sentence_review_candidate(
    project: Project,
    *,
    sentence: str,
) -> GenerationCandidate:
    """Promote Reading evidence without claiming that a rule consumed it.

    This is the sentence-interpretation sibling of
    :func:`promote_reading_candidate`. It runs the ordinary analyzer and
    document matcher, preserves any incidental matches and facts for
    inspection, but deliberately leaves the target rule unset. The review can
    therefore describe an intended meaning or missing rule without polluting
    premise-rule coverage.
    """

    if not sentence.strip():
        raise GenerationError("the Reading sentence must not be empty")
    seed = int.from_bytes(
        hashlib.sha256(
            (
                f"sentence-review\0{project.registry.fingerprint}\0"
                f"{sentence}"
            ).encode()
        ).digest()[:8],
        "big",
    ) & ((1 << 53) - 1)
    try:
        reading = analyze(sentence, project.registry, tracing=True)
        document = run_document([reading], project.registry)
    except Exception as exc:  # noqa: BLE001 - authoring API surfaces the defect
        raise GenerationError(
            "could not inspect the Reading sentence: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    results = document.rule_results.get(reading.sentence_index, [])
    premise_results = _premise_match_results(results)
    safety_results = _safety_interception_results(
        results, project.registry
    )
    digest = hashlib.sha256(
        (
            f"{project.registry.fingerprint}\0reading\0{seed}\0"
            f"sentence-review\0{sentence}"
        ).encode()
    ).hexdigest()[:20]
    return GenerationCandidate(
        id=f"gen-{digest}",
        project=project.doc.name,
        registry_fingerprint=project.registry.fingerprint,
        generator_version=GENERATOR_VERSION,
        origin="reading",
        generation_mode="strict",
        seed=seed,
        target_rule=None,
        target_description=(
            "No premise rule matched this sentence."
            if not premise_results
            else "No premise rule was selected for this sentence-level review."
        ),
        sentence=sentence,
        requested_bindings={},
        target_bindings={},
        target_status=(
            "unmatched" if not premise_results else "unassigned"
        ),
        target_specificity=None,
        target_source=None,
        premises=(),
        consumed_units=(),
        actual_matches=_match_summaries(
            premise_results, project, reading
        ),
        safety_interceptions=_match_summaries(
            safety_results, project, reading
        ),
        facts=tuple(
            _fact_json(
                fact,
                project,
                bindings=_matched_fact_bindings(fact, results),
            )
            for fact in document.store.facts
        ),
        collisions=tuple(
            _collision_json(collision)
            for collision in document.store.collisions
        ),
        deficiencies=tuple(reading.deficiencies()),
        attempts=1,
        lexical_relaxations=(),
    )


def generate_candidate(
    project: Project,
    *,
    rule_id: str | None = None,
    seed: int | None = None,
    max_attempts: int = 64,
    locked_bindings: dict[str, str] | None = None,
    identity_bindings: dict[str, str] | None = None,
    excluded_bindings: dict[str, str] | None = None,
    generation_mode: GenerationMode = "strict",
    structural_target: str | None = None,
) -> GenerationCandidate:
    """Generate and round-trip one supported rule with a reproducible seed."""

    if generation_mode not in {
        "strict",
        "lexical_boundary",
        "safety_boundary",
    }:
        raise GenerationError(f"unknown generation mode {generation_mode!r}")
    seed = secrets.randbits(63) if seed is None else seed
    rng = random.Random(seed)
    fixtures = _load_fixtures(project.root)
    rules = {rule.id: rule for rule in project.registry.rules}
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    if rule_id is None:
        supported = [
            rules[item.id]
            for item in availability.values()
            if (
                item.generation == "safety"
                if generation_mode == "safety_boundary"
                else item.supported
            )
        ]
        if not supported:
            raise GenerationError("this project has no supported premise rules")
        rule = supported[rng.randrange(len(supported))]
    else:
        rule = rules.get(rule_id)
        if rule is None:
            raise GenerationError(f"unknown premise rule {rule_id!r}")
        item = availability[rule.id]
        if not item.supported and not (
            generation_mode == "safety_boundary"
            and rule.generation == "safety"
        ):
            raise GenerationError(
                f"{rule.id} is blocked: {'; '.join(item.blockers)}"
            )

    last_sentence = ""
    last_bindings: dict[str, str] = {}
    last_results: list[RuleMatchResult] = []
    last_doc = None
    last_reading = None
    last_optional_choices: dict[tuple[int, ...], bool] = {}
    last_lexical_relaxations: tuple[LexicalRelaxation, ...] = ()
    last_context_before: tuple[str, ...] = ()
    last_context_after: tuple[str, ...] = ()
    last_realization_error: GenerationError | None = None
    failure_causes: Counter[str] = Counter()
    for attempt in range(1, max_attempts + 1):
        try:
            (
                sentence,
                requested,
                optional_choices,
                lexical_relaxations,
            ) = _realize(
                rule,
                project.registry,
                fixtures,
                rng,
                locked_bindings=locked_bindings,
                identity_bindings=identity_bindings,
                excluded_bindings=excluded_bindings,
                generation_mode=generation_mode,
                structural_target=structural_target,
            )
        except GenerationError as exc:
            last_realization_error = exc
            failure_causes[str(exc)] += 1
            continue
        sentence = _format_contextual_target(rule, sentence, requested)
        try:
            context_before, context_after = _realize_context(
                rule,
                project.registry,
                fixtures,
                rng,
                locked_bindings=locked_bindings,
                identity_bindings=identity_bindings,
                target_bindings=requested,
            )
        except GenerationError as exc:
            last_realization_error = exc
            failure_causes[str(exc)] += 1
            continue
        readings = [
            analyze(
                surface,
                project.registry,
                sentence_index=index,
                tracing=True,
            )
            for index, surface in enumerate(
                (*context_before, sentence, *context_after)
            )
        ]
        reading = readings[len(context_before)]
        try:
            doc = run_document(readings, project.registry)
        except ArithmeticError as exc:
            last_realization_error = GenerationError(
                "ordinary round trip rejected generated numeric values: "
                f"{type(exc).__name__}: {exc}"
            )
            failure_causes[str(last_realization_error)] += 1
            continue
        if rule.generation_context is not None:
            actual_fact_counts = Counter(
                "".join(
                    ("_" + char.lower()) if char.isupper() else char
                    for char in type(fact).__name__
                ).lstrip("_")
                for fact in doc.store.facts
            )
            missing_context = {
                kind: required - actual_fact_counts[kind]
                for kind, required in (
                    rule.generation_context.required_fact_counts.items()
                )
                if actual_fact_counts[kind] < required
            }
            if missing_context:
                last_realization_error = GenerationError(
                    "context did not realize required facts: "
                    + ", ".join(
                        f"{kind} missing {count}"
                        for kind, count in sorted(missing_context.items())
                    )
                )
                failure_causes[str(last_realization_error)] += 1
                continue
        results = doc.rule_results.get(reading.sentence_index, [])
        last_sentence = sentence
        last_bindings = requested
        last_results = results
        last_doc = doc
        last_reading = reading
        last_optional_choices = optional_choices
        last_lexical_relaxations = lexical_relaxations
        last_context_before = context_before
        last_context_after = context_after
        target_results = [
            result for result in results if result.match.rule.id == rule.id
        ]
        safety_boundary_is_clean = (
            generation_mode != "safety_boundary"
            or not _premise_match_results(results)
        )
        if not safety_boundary_is_clean:
            last_realization_error = GenerationError(
                "safety boundary also matched a fact-emitting premise rule"
            )
            failure_causes[str(last_realization_error)] += 1
        target_structure_realized = True
        if structural_target is not None:
            kind, _, value = structural_target.partition(":")
            if kind == "fact":
                fact_kind = value.split("(", 1)[0]
                target_structure_realized = any(
                    type(fact).__name__ == _fact_kind_type_name(fact_kind)
                    for result in target_results
                    for fact in result.facts
                )
            elif kind == "surface":
                target_structure_realized = bool(target_results)
        if safety_boundary_is_clean and target_structure_realized and (
            generation_mode == "lexical_boundary" or any(
                result.match.rule.id == rule.id
                and _strict_round_trip_result(
                    result, requested, reading, project.registry
                )
                for result in results
            )
        ):
            break
    if last_doc is None or last_reading is None:
        profile = "; ".join(
            f"{count}× {cause}"
            for cause, count in sorted(
                failure_causes.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        )
        raise GenerationError(
            f"{rule.id} could not realize a sentence after {max_attempts} "
            f"deterministic attempts: {last_realization_error}"
            + (f"; failure profile: {profile}" if profile else "")
        )
    return _candidate_from_reading(
        project,
        rule=rule,
        target_rule_id=rule.id,
        sentence=last_sentence,
        seed=seed,
        requested_bindings=last_bindings,
        attempts=attempt,
        fixtures=fixtures,
        reading=last_reading,
        document=last_doc,
        results=last_results,
        generation_mode=generation_mode,
        optional_choices=last_optional_choices,
        lexical_relaxations=last_lexical_relaxations,
        context_before=last_context_before,
        context_after=last_context_after,
    )


def generate_minimal_pair(
    project: Project,
    *,
    rule_id: str,
    base_seed: int,
    original_bindings: dict[str, str],
    reroll_slot: str,
    max_attempts: int = 64,
) -> GenerationCandidate:
    """Reroll one slot while locking every other realized binding."""

    rule = next(
        (candidate for candidate in project.registry.rules if candidate.id == rule_id),
        None,
    )
    if rule is None:
        raise GenerationError(f"unknown premise rule {rule_id!r}")
    seq = _flat_sentence(rule)
    if seq is None:
        raise GenerationError(
            f"{rule_id} has no flat sentence pattern for a single-slot reroll"
        )
    slots = {
        token.slot
        for _, token, _ in _leaf_tokens(seq)
        if token.slot is not None
    }
    if reroll_slot not in slots:
        raise GenerationError(
            f"{reroll_slot!r} is not a realizable slot in {rule_id}"
        )
    original = original_bindings.get(reroll_slot)
    if original is None:
        raise GenerationError(
            f"the pinned candidate has no binding for slot {reroll_slot!r}"
        )

    fixtures = _load_fixtures(project.root)
    slot_tokens = [
        token
        for _, token, _ in _leaf_tokens(seq)
        if token.slot == reroll_slot
    ]
    if not any(
        filler.surface.casefold() != original.casefold()
        for token in slot_tokens
        for filler in _domain(token, project.registry, fixtures)
    ):
        raise GenerationError(
            f"slot {reroll_slot!r} has no project-backed alternative to {original!r}"
        )

    locked = {
        slot: surface
        for slot, surface in original_bindings.items()
        if slot in slots and slot != reroll_slot
    }
    seed_material = "\0".join(
        (
            project.registry.fingerprint,
            str(base_seed),
            rule_id,
            reroll_slot,
            repr(sorted(original_bindings.items())),
        )
    )
    pair_seed = int.from_bytes(
        hashlib.sha256(seed_material.encode()).digest()[:8], "big"
    ) & ((1 << 63) - 1)
    return generate_candidate(
        project,
        rule_id=rule_id,
        seed=pair_seed,
        max_attempts=max_attempts,
        locked_bindings=locked,
        excluded_bindings={reroll_slot: original},
    )
