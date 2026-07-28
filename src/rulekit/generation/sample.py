"""Deterministic sampling for supported premise-pattern rules."""

from __future__ import annotations

import hashlib
import random
import re
import secrets
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Literal

from ruamel.yaml import YAML

from ..data.project import Project
from ..data.registry import Registry
from ..data.schemas import (
    AttributeCompatibilityPredicate,
    MatchToken,
    PatternRule,
)
from ..data.sources import SourceRef
from ..kernel.document import run_document
from ..kernel.engine import analyze
from ..kernel.model import Unit, _jsonable
from ..kernel.patterns import (
    RuleMatchResult,
    is_bare_verb_form,
    is_finite_verb_form,
    subsumes,
)
from .candidate import (
    ConsumedUnitSummary,
    GenerationCandidate,
    MatchSummary,
    PremiseSummary,
    RuleAvailability,
)

GENERATOR_VERSION = "g6-reviewed-premise-boundaries"
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
        "counted",
        "possessed",
        "pronoun",
        "modal",
        "future_modal",
    }
)
_SUPPORTED_CATEGORY_ROOTS = frozenset(
    {
        "noun",
        "verb",
        "adjective",
        "preposition",
        "pronoun",
        "aggregate",
        "comparative",
        "complementizer",
        "quantifier",
        "time",
        "adverb",
    }
)
_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":"})
_yaml = YAML(typ="rt")


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


@dataclass(frozen=True)
class _Fixtures:
    names: tuple[str, ...]
    sources: dict[str, SourceRef]


def _load_fixtures(project_root: Path) -> _Fixtures:
    path = project_root / "generation.yaml"
    if not path.exists():
        return _Fixtures(names=(), sources={})
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
    return _Fixtures(names=tuple(names), sources=sources)


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
    if token.present_participle or token.past_participle:
        blockers.append("explicit verb morphology has no current realizer")
    if token.slot is not None and token.type is not None:
        if token.type not in _SUPPORTED_SLOT_TYPES:
            blockers.append(f"slot type {token.type!r} has no current realizer")
    if token.slot is not None and token.cat is not None:
        root = reg.root_sense(token.cat)
        if root not in _SUPPORTED_CATEGORY_ROOTS:
            blockers.append(
                f"category {token.cat!r} roots at unsupported sense {root!r}"
            )
    return blockers


def _where_blocker(rule: PatternRule) -> list[str]:
    blockers: list[str] = []
    for pred in rule.where:
        if (
            pred.distinct is not None
            or pred.distinct_owner is not None
            or pred.distinct_from_owner is not None
            or pred.same_lemma is not None
            or pred.same_number is not None
            or pred.number_compatible is not None
            or pred.bound_requires_type is not None
            or pred.bound_requires_category is not None
            or pred.bound_requires_form is not None
            or pred.polarity_compatible is not None
            or pred.same_presence is not None
            or pred.verb_role_compatible is not None
            or pred.attribute_compatible is not None
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


def _lexical_fillers(
    reg: Registry,
    *,
    sense: str | None = None,
    category: str | None = None,
    bare_form: bool = False,
    finite_form: bool = False,
) -> list[_Filler]:
    out: list[_Filler] = []
    for surface, entry in sorted(reg.lexicon.items()):
        if any(ch.isspace() for ch in surface) or not surface:
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
        )
        for value in values
    ]


def _fraction_fillers(reg: Registry) -> list[_Filler]:
    """Realize complete fraction phrases from declared number morphology."""

    direct = [
        _Filler(surface, reg.fraction_plurals.get(surface, surface))
        for surface in sorted(reg.fractions)
        if (
            surface not in reg.fraction_plurals
            and not any(ch.isspace() for ch in surface)
        )
    ]
    counted = [
        _Filler(f"{count_surface} {plural}", singular)
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
            and not any(ch.isspace() for ch in singular)
            and not any(ch.isspace() for ch in plural)
            and (entry := reg.lexicon.get(singular)) is not None
            and "noun" in entry.senses
        )
    ]
    return [
        _Filler(
            surface=f"{count} {singular if count == 1 else plural}",
            identity=singular,
            number="singular" if count == 1 else "plural",
        )
        for count in counts
        for singular, plural in noun_pairs
    ]


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
            or any(ch.isspace() for ch in singular)
            or set(entry.senses) != {"noun"}
            or reg.plural_to_singular.get(singular, singular) != singular
        ):
            continue
        heads[singular] = singular
        plural = reg.singular_to_plural.get(singular)
        if plural and not any(ch.isspace() for ch in plural):
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


def _raw_domain(
    token: MatchToken, reg: Registry, fixtures: _Fixtures
) -> list[_Filler]:
    if token.lit is not None:
        return [_Filler(option, option) for option in token.lit_options]
    if token.opt is not None or token.slot is None:
        return []
    if token.cat is not None:
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
        root = reg.root_sense(token.cat)
        if root == "noun" and token.number == "plural":
            return [
                _Filler(
                    surface=surface,
                    identity=singular,
                    number="plural",
                )
                for surface, singular in sorted(
                    reg.plural_to_singular.items()
                )
                if surface
                and not any(ch.isspace() for ch in surface)
                and reg.word_in_category(singular, token.cat)
            ]
        return _lexical_fillers(
            reg,
            sense=root,
            category=token.cat,
            bare_form=token.bare_form,
            finite_form=token.finite_form,
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
    if slot_type == "plural":
        return [
            _Filler(
                surface=surface,
                identity=singular,
                number="plural",
            )
            for surface, singular in sorted(reg.plural_to_singular.items())
            if surface and not any(ch.isspace() for ch in surface)
        ]
    if slot_type == "counted":
        return _counted_fillers(reg)
    if slot_type == "possessed":
        return _possessed_fillers(reg, fixtures)
    if slot_type == "pronoun":
        return _lexical_fillers(reg, sense="pronoun")
    if slot_type == "modal":
        return _lexical_fillers(reg, sense="modal")
    if slot_type == "future_modal":
        return _lexical_fillers(
            reg,
            sense="modal",
            category="future_modal",
        )
    if slot_type == "verb":
        return _lexical_fillers(
            reg,
            sense="verb",
            bare_form=token.bare_form,
            finite_form=token.finite_form,
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
        return _number_fillers(reg)
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
    return []


def _domain(
    token: MatchToken, reg: Registry, fixtures: _Fixtures
) -> list[_Filler]:
    fillers = _raw_domain(token, reg, fixtures)
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
    if token.number is None:
        return fillers
    return [
        filler for filler in fillers if filler.number == token.number
    ]


def _absent_categories(rule: PatternRule) -> tuple[str, ...]:
    """Return the sentence-wide category exclusions declared by one rule."""

    return tuple(
        dict.fromkeys(
            pred.absent["cat"]
            for pred in rule.where
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
    for pred in rule.where:
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
        for pred in rule.where
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
        for pred in rule.where
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


def _distinct_measure_groups(rule: PatternRule) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(pred.distinct_measure)
        for pred in rule.where
        if pred.distinct_measure is not None
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
    ordered = sorted(involved, key=lambda name: (len(key_domains[name]), name))
    chosen: dict[str, tuple[str, str | None, str | None]] = {}

    def assign(index: int) -> bool:
        if index == len(ordered):
            return True
        name = ordered[index]
        for key in key_domains[name]:
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
) -> dict[str, _Filler]:
    """Resolve locked surfaces to the same filler metadata realization uses."""

    resolved: dict[str, _Filler] = {}
    for slot_name, surface in locked_bindings.items():
        matches = [
            filler
            for _, token, _ in _leaf_tokens(tokens)
            if token.slot == slot_name
            for filler in _domain(token, reg, fixtures)
            if filler.surface.casefold() == surface.casefold()
        ]
        if not matches:
            continue
        keys = {_measure_key(filler) for filler in matches}
        if len(keys) != 1:
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

        def safe_domain(token: MatchToken) -> list[_Filler]:
            return [
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
        for pred in rule.where:
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
        for pred in rule.where:
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
        for pred in rule.where:
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
        for pred in rule.where:
            if pred.verb_role_compatible is None:
                continue
            compatibility = pred.verb_role_compatible
            verb_token = tokens_by_slot.get(compatibility.verb)
            role_tokens = [
                tokens_by_slot.get(role)
                for role in compatibility.roles
            ]

            def role_ok(verb: _Filler, role: _Filler) -> bool:
                if not reg.word_in_category(
                    verb.identity, compatibility.verb_cat
                ):
                    return True
                if compatibility.role_cat is not None:
                    return (
                        role.kind == "name"
                        or reg.word_in_category(
                            role.identity, compatibility.role_cat
                        )
                    )
                assert compatibility.excluded_role_cat is not None
                return not reg.word_in_category(
                    role.identity, compatibility.excluded_role_cat
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
        for pred in rule.where:
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
        for pred in rule.where:
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
    return tuple(dict.fromkeys(blockers))


def list_rule_availability(project: Project) -> list[RuleAvailability]:
    """List every premise rule, including every unsupported one."""

    fixtures = _load_fixtures(project.root)
    return [
        RuleAvailability(
            id=rule.id,
            description=rule.description,
            supported=not (blockers := _rule_blockers(rule, project.registry, fixtures)),
            blockers=blockers,
        )
        for rule in project.registry.rules
    ]


def _constraint_groups(
    rule: PatternRule,
) -> tuple[
    list[set[str]],
    list[set[str]],
    list[set[str]],
    list[tuple[tuple[str, str], ...]],
    list[set[str]],
    list[set[str]],
    list[tuple[str, str, str]],
    list[tuple[str, str, str]],
    list[tuple[str, str, str]],
    list[set[str]],
    tuple[tuple[str, ...], ...],
    list[tuple[str, str]],
    list[
        tuple[
            str,
            tuple[str, ...],
            str,
            str | None,
            str | None,
        ]
    ],
    list[tuple[str, str]],
    tuple[str, ...],
]:
    same: list[set[str]] = []
    same_number: list[set[str]] = []
    number_compatible: list[set[str]] = []
    polarity_compatible: list[tuple[tuple[str, str], ...]] = []
    distinct: list[set[str]] = []
    distinct_owner: list[set[str]] = []
    bound_type_requirements: list[tuple[str, str, str]] = []
    bound_category_requirements: list[tuple[str, str, str]] = []
    bound_form_requirements: list[tuple[str, str, str]] = []
    same_presence: list[set[str]] = []
    attribute_pairs: list[tuple[str, str]] = []
    verb_role_requirements: list[
        tuple[
            str,
            tuple[str, ...],
            str,
            str | None,
            str | None,
        ]
    ] = []
    slot_category_exclusions = list(_slot_category_exclusions(rule))
    for pred in rule.where:
        if pred.same_lemma is not None:
            same.append(set(pred.same_lemma))
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
        if pred.verb_role_compatible is not None:
            verb_role_requirements.append(
                (
                    pred.verb_role_compatible.verb,
                    tuple(pred.verb_role_compatible.roles),
                    pred.verb_role_compatible.verb_cat,
                    pred.verb_role_compatible.role_cat,
                    pred.verb_role_compatible.excluded_role_cat,
                )
            )
    return (
        same,
        same_number,
        number_compatible,
        polarity_compatible,
        distinct,
        distinct_owner,
        bound_type_requirements,
        bound_category_requirements,
        bound_form_requirements,
        same_presence,
        _distinct_measure_groups(rule),
        attribute_pairs,
        verb_role_requirements,
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
    locked_fillers: dict[str, _Filler],
    same_groups: list[set[str]],
    same_number_groups: list[set[str]],
    distinct_groups: list[set[str]],
    distinct_owner_groups: list[set[str]],
    distinct_measure_groups: tuple[tuple[str, ...], ...],
    attribute_pairs: list[tuple[str, str]],
    tokens_by_slot: dict[str, MatchToken],
    active_slots: set[str],
    slot_category_exclusions: list[tuple[str, str]],
    absent_categories: tuple[str, ...],
    number_compatible_groups: list[set[str]] | tuple[set[str], ...] = (),
    polarity_compatible_groups: (
        list[tuple[tuple[str, str], ...]]
        | tuple[tuple[tuple[str, str], ...], ...]
    ) = (),
    bound_type_requirements: (
        list[tuple[str, str, str]] | tuple[tuple[str, str, str], ...]
    ) = (),
    bound_category_requirements: (
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
            ]
        ]
        | tuple[
            tuple[
                str,
                tuple[str, ...],
                str,
                str | None,
                str | None,
            ],
            ...,
        ]
    ) = (),
    entity_owner_distinctions: tuple[tuple[str, str], ...] = (),
) -> list[_Filler]:
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
                for candidate in _domain(other, reg, fixtures)
                if _outside_categories(candidate, absent_categories, reg)
                and _outside_slot_categories(
                    candidate,
                    name,
                    slot_category_exclusions,
                    reg,
                )
            }

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
        for (
            verb_name,
            role_names,
            verb_category,
            role_category,
            excluded_role_category,
        ) in verb_role_requirements:
            def role_ok(verb: _Filler, role: _Filler) -> bool:
                if not reg.word_in_category(
                    verb.identity, verb_category
                ):
                    return True
                if role_category is not None:
                    return (
                        role.kind == "name"
                        or reg.word_in_category(
                            role.identity, role_category
                        )
                    )
                assert excluded_role_category is not None
                return not reg.word_in_category(
                    role.identity, excluded_role_category
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
                            for candidate in _domain(
                                tokens_by_slot[role_name], reg, fixtures
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
        return True

    def satisfies_conditional_categories(filler: _Filler) -> bool:
        def in_category(candidate: _Filler, category: str) -> bool:
            return (
                reg.word_in_category(candidate.surface.casefold(), category)
                or reg.word_in_category(candidate.identity, category)
            )

        for bound_slot, target_slot, category in bound_category_requirements:
            if (
                token.slot == target_slot
                and bound_slot in active_slots
                and not in_category(filler, category)
            ):
                return False
            if token.slot == bound_slot:
                target = chosen.get(target_slot) or locked_fillers.get(
                    target_slot
                )
                if target is not None and not in_category(target, category):
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
                        for candidate in _domain(
                            tokens_by_slot[target_slot], reg, fixtures
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
                    preceding_is_possessive
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
                and not preceding_is_possessive
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
    excluded_bindings: dict[str, str] | None = None,
) -> tuple[str, dict[str, str], dict[tuple[int, ...], bool]]:
    seq = _flat_sentence(rule)
    assert seq is not None
    locked_bindings = locked_bindings or {}
    excluded_bindings = excluded_bindings or {}
    (
        same_groups,
        same_number_groups,
        number_compatible_groups,
        polarity_compatible_groups,
        distinct_groups,
        distinct_owner_groups,
        bound_type_requirements,
        bound_category_requirements,
        bound_form_requirements,
        same_presence_groups,
        distinct_measure_groups,
        attribute_pairs,
        verb_role_requirements,
        slot_category_exclusions,
        absent_categories,
    ) = _constraint_groups(rule)
    unbound_optional_paths = _unbound_optional_paths(rule, seq)
    locked_fillers = _resolve_locked_fillers(
        seq, reg, fixtures, locked_bindings
    )
    entity_owner_distinctions = _entity_owner_distinctions(rule)
    chosen: dict[str, _Filler] = {}
    surfaces: list[str] = []
    optional_choices: dict[tuple[int, ...], bool] = {}
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
    forced_slots = set(locked_bindings) | set(excluded_bindings)
    forced_optional_paths = {
        ancestor
        for _, token, ancestors in _leaf_tokens(seq)
        if token.slot in forced_slots
        for ancestor in ancestors
    }
    forced_omitted_paths = set(unbound_optional_paths)
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
                _domain(token, reg, fixtures),
                chosen,
                reg,
                fixtures,
                locked_bindings,
                locked_fillers,
                same_groups,
                same_number_groups,
                distinct_groups,
                distinct_owner_groups,
                distinct_measure_groups,
                attribute_pairs,
                tokens_by_slot,
                active_slots,
                slot_category_exclusions,
                absent_categories,
                number_compatible_groups,
                polarity_compatible_groups,
                bound_type_requirements,
                bound_category_requirements,
                bound_form_requirements,
                verb_role_requirements,
                entity_owner_distinctions=entity_owner_distinctions,
            )
            if token.slot in locked_bindings:
                locked = locked_bindings[token.slot].casefold()
                domain = [
                    filler
                    for filler in domain
                    if filler.surface.casefold() == locked
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
            surfaces.append(filler.surface)

    realize_tokens(seq)

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
    )


def _fact_kind_type_name(kind: str) -> str:
    """Return the runtime dataclass spelling for a declarative fact kind."""

    return "".join(part.capitalize() for part in kind.split("_"))


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
    if slot_type == "counted" or token.counted:
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
    if token.counted:
        gates.append("counted")
    if token.possessed:
        gates.append("possessed")
    if token.bare_form:
        gates.append("bare form")
    if token.finite_form:
        gates.append("finite form")
    if token.number is not None:
        gates.append(f"number {token.number!r}")
    if token.standalone:
        gates.append("standalone")
    if token.referential:
        gates.append("referential")
    if token.bare_reference_category is not None:
        gates.append(
            f"bare category {token.bare_reference_category!r}"
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
        return (
            f"{surface!r} satisfied type 'fraction' through explicit count "
            f"{unit.features.get('fraction_count')!r} and declared plural "
            f"fraction lemma {unit.features.get('fraction_lemma')!r}"
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
    "same_number",
    "number_compatible",
    "bound_requires_type",
    "bound_requires_category",
    "bound_requires_form",
    "polarity_compatible",
    "same_presence",
    "verb_role_compatible",
    "same_phrase",
    "distinct",
    "distinct_owner",
    "distinct_from_owner",
    "attribute_compatible",
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
    elif kind == "attribute_compatible":
        names = (value.attribute, value.noun)
        rendered = (
            f"attribute={value.attribute!r}, noun={value.noun!r}"
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
            f"cat={value.cat!r}"
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
    elif kind == "verb_role_compatible":
        names = (value.verb, *value.roles)
        role_boundary = (
            f"role_cat={value.role_cat!r}"
            if value.role_cat is not None
            else f"excluded_role_cat={value.excluded_role_cat!r}"
        )
        rendered = (
            f"verb={value.verb!r}, roles={value.roles!r}, "
            f"verb_cat={value.verb_cat!r}, {role_boundary}"
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
    if pred.verb_role_compatible is not None:
        compatibility = pred.verb_role_compatible
        verb_units = _slot_units(slots.get(compatibility.verb))
        if not verb_units:
            return "the target match did not expose the governing verb"
        verb = _unit_lemma(verb_units[0], reg)
        if not reg.word_in_category(verb, compatibility.verb_cat):
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
        else:
            boundary = (
                f"excluded {compatibility.excluded_role_cat!r} roles"
            )
        return (
            f"{compatibility.verb}={verb!r} {boundary}: "
            + ", ".join(rendered_roles)
        )
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
            premises.append(
                PremiseSummary(
                    index=token_no,
                    kind="token",
                    expression=_token_expression(token),
                    binding=bound,
                    status="unverified",
                    reason=(
                        "target rule was absent; the matcher exposes no "
                        "partial premise result"
                    ),
                    slot=token.slot,
                    slot_type=token.type or token.cat,
                    sources=_dedupe_sources([source]),
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
        premises.append(
            PremiseSummary(
                index=token_no,
                kind="token",
                expression=_token_expression(token),
                binding=binding,
                status="passed" if units else "unverified",
                reason=(
                    _token_reason(token, units, category_path)
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
        if predicate.polarity_compatible is not None:
            where_sources.extend(
                project.source_index.categories.get(category)
                for category in predicate.polarity_compatible.categories
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
    optional_choices: dict[tuple[int, ...], bool] | None = None,
) -> GenerationCandidate:
    """Project one ordinary reader result into the authoring candidate record."""

    target_results = [
        result for result in results if result.match.rule.id == target_rule_id
    ]
    target_result = target_results[0] if target_results else None
    if target_result is None:
        status = "absent"
        target_bindings: dict[str, str] = {}
    else:
        target_shadowed = all(
            any(
                other is not result
                and subsumes(other.match, result.match, project.registry)
                for other in results
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
        )

    digest = hashlib.sha256(
        (
            f"{project.registry.fingerprint}\0{origin}\0{seed}\0{target_rule_id}\0"
            f"{sentence}"
        ).encode()
    ).hexdigest()[:20]
    return GenerationCandidate(
        id=f"gen-{digest}",
        project=project.doc.name,
        registry_fingerprint=project.registry.fingerprint,
        generator_version=GENERATOR_VERSION,
        origin=origin,
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
        actual_matches=_match_summaries(results, project, reading),
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
) -> GenerationCandidate:
    """Re-evaluate an identical pinned sentence against the current project."""

    if not sentence.strip():
        raise GenerationError("the pinned sentence must not be empty")
    fixtures = _load_fixtures(project.root)
    rule = next(
        (candidate for candidate in project.registry.rules if candidate.id == rule_id),
        None,
    )
    try:
        reading = analyze(sentence, project.registry, tracing=True)
        document = run_document([reading], project.registry)
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
        seed=seed,
        target_rule=None,
        target_description=(
            "No premise rule matched this sentence."
            if not results
            else "No premise rule was selected for this sentence-level review."
        ),
        sentence=sentence,
        requested_bindings={},
        target_bindings={},
        target_status="unmatched" if not results else "unassigned",
        target_specificity=None,
        target_source=None,
        premises=(),
        consumed_units=(),
        actual_matches=_match_summaries(results, project, reading),
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
    )


def generate_candidate(
    project: Project,
    *,
    rule_id: str | None = None,
    seed: int | None = None,
    max_attempts: int = 64,
    locked_bindings: dict[str, str] | None = None,
    excluded_bindings: dict[str, str] | None = None,
) -> GenerationCandidate:
    """Generate and round-trip one supported rule with a reproducible seed."""

    seed = secrets.randbits(63) if seed is None else seed
    rng = random.Random(seed)
    fixtures = _load_fixtures(project.root)
    rules = {rule.id: rule for rule in project.registry.rules}
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    if rule_id is None:
        supported = [
            rules[item.id] for item in availability.values() if item.supported
        ]
        if not supported:
            raise GenerationError("this project has no supported premise rules")
        rule = supported[rng.randrange(len(supported))]
    else:
        rule = rules.get(rule_id)
        if rule is None:
            raise GenerationError(f"unknown premise rule {rule_id!r}")
        item = availability[rule.id]
        if not item.supported:
            raise GenerationError(
                f"{rule.id} is blocked: {'; '.join(item.blockers)}"
            )

    last_sentence = ""
    last_bindings: dict[str, str] = {}
    last_results: list[RuleMatchResult] = []
    last_doc = None
    last_reading = None
    last_optional_choices: dict[tuple[int, ...], bool] = {}
    last_realization_error: GenerationError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            sentence, requested, optional_choices = _realize(
                rule,
                project.registry,
                fixtures,
                rng,
                locked_bindings=locked_bindings,
                excluded_bindings=excluded_bindings,
            )
        except GenerationError as exc:
            last_realization_error = exc
            continue
        reading = analyze(sentence, project.registry, tracing=True)
        try:
            doc = run_document([reading], project.registry)
        except ArithmeticError as exc:
            last_realization_error = GenerationError(
                "ordinary round trip rejected generated numeric values: "
                f"{type(exc).__name__}: {exc}"
            )
            continue
        results = doc.rule_results.get(reading.sentence_index, [])
        last_sentence = sentence
        last_bindings = requested
        last_results = results
        last_doc = doc
        last_reading = reading
        last_optional_choices = optional_choices
        if any(result.match.rule.id == rule.id for result in results):
            break
    if last_doc is None or last_reading is None:
        raise GenerationError(
            f"{rule.id} could not realize a sentence after {max_attempts} "
            f"deterministic attempts: {last_realization_error}"
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
        optional_choices=last_optional_choices,
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
