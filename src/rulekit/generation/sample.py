"""Deterministic sampling for supported premise-pattern rules."""

from __future__ import annotations

import hashlib
import random
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ruamel.yaml import YAML

from ..data.project import Project
from ..data.registry import Registry
from ..data.schemas import MatchToken, PatternRule
from ..data.sources import SourceRef
from ..kernel.document import run_document
from ..kernel.engine import analyze
from ..kernel.model import Unit, _jsonable
from ..kernel.patterns import RuleMatchResult, subsumes
from .candidate import (
    ConsumedUnitSummary,
    GenerationCandidate,
    MatchSummary,
    PremiseSummary,
    RuleAvailability,
)

GENERATOR_VERSION = "g6-review-boundaries"
_SUPPORTED_SLOT_TYPES = frozenset(
    {
        "number",
        "fraction",
        "multiplier",
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
    }
)
_SUPPORTED_CATEGORY_ROOTS = frozenset(
    {"noun", "verb", "adjective", "preposition", "pronoun", "aggregate"}
)
_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":"})
_yaml = YAML(typ="rt")


class GenerationError(ValueError):
    """A selected rule cannot produce a generation candidate."""


@dataclass(frozen=True)
class _Filler:
    surface: str
    identity: str


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


def _token_blockers(token: MatchToken, reg: Registry) -> list[str]:
    blockers: list[str] = []
    if token.opt is not None:
        blockers.append("optional groups have no current realizer")
        return blockers
    if token.span:
        blockers.append("span capture has no current realizer")
    if token.present_participle or token.past_participle or token.bare_form:
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
            or pred.same_lemma is not None
            or pred.same_number is not None
        ):
            continue
        kind = next(
            name
            for name in (
                "same_phrase",
                "distinct_measure",
                "name_count",
                "absent",
                "slot_not_category",
                "unbound",
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
        if bare_form and identity != surface:
            continue
        out.append(_Filler(surface=surface, identity=identity))
    return out


def _number_fillers(reg: Registry) -> list[_Filler]:
    values = sorted(
        {
            int(value)
            for value in reg.numbers.values()
            if float(value).is_integer() and value >= 0
        }
    )
    return [_Filler(str(value), str(value)) for value in values]


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
        _Filler(surface=f"{owner}'s {head}", identity=singular)
        for owner in fixtures.names
        for head, singular in sorted(heads.items())
    ]


def _domain(token: MatchToken, reg: Registry, fixtures: _Fixtures) -> list[_Filler]:
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
        root = reg.root_sense(token.cat)
        return _lexical_fillers(
            reg,
            sense=root,
            category=token.cat,
            bare_form=token.bare_form,
        )

    slot_type = token.type
    if slot_type in {"name", "proper_name"}:
        return [_Filler(name, name.casefold()) for name in fixtures.names]
    if slot_type == "entity":
        return [
            *[_Filler(name, name.casefold()) for name in fixtures.names],
            *_lexical_fillers(reg, sense="noun"),
        ]
    if slot_type in {"noun", "common_noun"}:
        return _lexical_fillers(reg, sense="noun")
    if slot_type == "plural":
        return [
            _Filler(surface=surface, identity=singular)
            for surface, singular in sorted(reg.plural_to_singular.items())
            if surface and not any(ch.isspace() for ch in surface)
        ]
    if slot_type == "counted":
        return _counted_fillers(reg)
    if slot_type == "possessed":
        return _possessed_fillers(reg, fixtures)
    if slot_type == "pronoun":
        return _lexical_fillers(reg, sense="pronoun")
    if slot_type == "verb":
        return _lexical_fillers(reg, sense="verb", bare_form=token.bare_form)
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
    if slot_type == "percent":
        return [
            _Filler(f"{filler.surface}%", f"{filler.identity}%")
            for filler in _number_fillers(reg)
        ]
    return []


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
        for token in seq:
            blockers.extend(_token_blockers(token, reg))
            if not _token_blockers(token, reg) and not _domain(token, reg, fixtures):
                label = token.slot or repr(token.lit)
                blockers.append(f"no project-backed filler exists for {label}")
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


def _constraint_groups(rule: PatternRule) -> tuple[list[set[str]], list[set[str]]]:
    same: list[set[str]] = []
    distinct: list[set[str]] = []
    for pred in rule.where:
        if pred.same_lemma is not None:
            same.append(set(pred.same_lemma))
        if pred.distinct is not None:
            distinct.append(set(pred.distinct))
    return same, distinct


def _allowed_fillers(
    token: MatchToken,
    domain: list[_Filler],
    chosen: dict[str, _Filler],
    same_groups: list[set[str]],
    distinct_groups: list[set[str]],
) -> list[_Filler]:
    if token.slot is None:
        return domain
    if token.slot in chosen:
        return [chosen[token.slot]]

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
    return [
        filler
        for filler in domain
        if (
            not required_identities
            or filler.identity in required_identities
        )
        and filler.identity not in forbidden_identities
    ]


def _realize(
    rule: PatternRule,
    reg: Registry,
    fixtures: _Fixtures,
    rng: random.Random,
    *,
    locked_bindings: dict[str, str] | None = None,
    excluded_bindings: dict[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    seq = _flat_sentence(rule)
    assert seq is not None
    locked_bindings = locked_bindings or {}
    excluded_bindings = excluded_bindings or {}
    same_groups, distinct_groups = _constraint_groups(rule)
    chosen: dict[str, _Filler] = {}
    surfaces: list[str] = []
    for token in seq:
        domain = _allowed_fillers(
            token,
            _domain(token, reg, fixtures),
            chosen,
            same_groups,
            distinct_groups,
        )
        if token.slot in locked_bindings:
            locked = locked_bindings[token.slot].casefold()
            domain = [
                filler for filler in domain if filler.surface.casefold() == locked
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
            raise GenerationError(f"constraints left no filler for {label}")
        filler = domain[rng.randrange(len(domain))]
        if token.slot is not None:
            chosen[token.slot] = filler
        surfaces.append(filler.surface)

    sentence = " ".join(surfaces)
    sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
    if sentence and sentence[-1] not in _PUNCTUATION:
        sentence += "."
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
    return sentence, {name: filler.surface for name, filler in chosen.items()}


def _fact_json(fact: Any, project: Project | None = None) -> dict[str, Any]:
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
                _fact_json(fact, project) for fact in result.facts
            ),
        )
        for result in results
    )


def _source_json(ref: SourceRef | None) -> dict[str, Any] | None:
    return None if ref is None else ref.to_json()


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

    if token.cat is None:
        return (), []
    reg = project.registry
    index = project.source_index
    fold = unit.surface.casefold()
    lemma = _unit_lemma(unit, reg)
    for word in dict.fromkeys((fold, lemma)):
        for category in reg.word_categories.get(word, ()):
            ancestry = reg.cat_ancestors(category)
            if token.cat not in ancestry:
                continue
            refs: list[SourceRef | None] = [
                index.category_members.get((category, word)),
                index.category_members.get((category, lemma)),
            ]
            refs.extend(index.categories.get(name) for name in ancestry)
            return (word, *ancestry), refs

    # Root-sense categories are also satisfied directly by lexicon senses.
    entry = reg.lexicon.get(fold) or reg.lexicon.get(lemma)
    if entry is not None and token.cat in entry.senses:
        return (lemma, token.cat), [index.categories.get(token.cat)]
    return (lemma, token.cat), [index.categories.get(token.cat)]


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
    if slot_type == "multiplier":
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
    if token.lit is not None:
        return "literal " + " | ".join(repr(value) for value in token.lit_options)
    gates = []
    if token.type is not None:
        gates.append(f"type {token.type!r}")
    if token.cat is not None:
        gates.append(f"category {token.cat!r}")
    if token.counted:
        gates.append("counted")
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
    "same_phrase",
    "distinct",
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
    names = pred.distinct or pred.same_lemma or pred.same_number
    if names is None:
        expression, _ = _where_expression(rule, index)
        return f"the target match confirms {expression} passed"
    if pred.same_number is not None:
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
        else "shared grammatical number"
        if pred.same_number is not None
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

    for token_no, token in enumerate(seq or []):
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
                    sources=_dedupe_sources(
                        [project.source_index.rule_tokens.get((rule.id, token_no))]
                    ),
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
            project.source_index.rule_tokens.get((rule.id, token_no))
        ]
        for unit in units:
            sources.extend(
                _counted_lexical_sources(project, unit)
                if token.type == "counted" or token.counted
                else _possessed_sources(project, fixtures, unit)
                if token.type == "possessed"
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
        premises.append(
            PremiseSummary(
                index=where_no,
                kind="where",
                expression=expression,
                binding=", ".join(
                    f"{name}={actual_bindings.get(name, requested.get(name, ''))}"
                    for name in names
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
                sources=_dedupe_sources(
                    [project.source_index.rule_where.get((rule.id, where_no))]
                ),
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
            _fact_json(fact, project) for fact in document.store.facts
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
    last_realization_error: GenerationError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            sentence, requested = _realize(
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
        doc = run_document([reading], project.registry)
        results = doc.rule_results.get(reading.sentence_index, [])
        last_sentence = sentence
        last_bindings = requested
        last_results = results
        last_doc = doc
        last_reading = reading
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
    slots = {token.slot for token in seq if token.slot is not None}
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
    slot_tokens = [token for token in seq if token.slot == reroll_slot]
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
