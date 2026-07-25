"""Deterministic G1 sampling for flat premise-pattern rules."""

from __future__ import annotations

import hashlib
import random
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from ..data.project import Project
from ..data.registry import Registry
from ..data.schemas import MatchToken, PatternRule
from ..kernel.document import run_document
from ..kernel.engine import analyze
from ..kernel.model import Unit, _jsonable
from ..kernel.patterns import RuleMatchResult, subsumes
from .candidate import GenerationCandidate, MatchSummary, RuleAvailability

GENERATOR_VERSION = "g1"
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
    }
)
_SUPPORTED_CATEGORY_ROOTS = frozenset({"noun", "verb", "adjective", "preposition"})
_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":"})
_yaml = YAML(typ="safe")


class GenerationError(ValueError):
    """A selected rule cannot produce a G1 candidate."""


@dataclass(frozen=True)
class _Filler:
    surface: str
    identity: str


@dataclass(frozen=True)
class _Fixtures:
    names: tuple[str, ...]


def _load_fixtures(project_root: Path) -> _Fixtures:
    path = project_root / "generation.yaml"
    if not path.exists():
        return _Fixtures(names=())
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
            f"{path}: G1 names must be non-empty, single-token strings"
        )
    if len(set(names)) != len(names):
        raise GenerationError(f"{path}: names must be unique")
    return _Fixtures(names=tuple(names))


def _flat_sentence(rule: PatternRule) -> list[MatchToken] | None:
    seq = rule.match.get("sentence")
    if seq is None or (seq and isinstance(seq[0], list)):
        return None
    return seq  # type: ignore[return-value]


def _token_blockers(token: MatchToken, reg: Registry) -> list[str]:
    blockers: list[str] = []
    if token.opt is not None:
        blockers.append("optional groups are deferred beyond G1")
        return blockers
    if token.span:
        blockers.append("span capture is deferred beyond G1")
    if token.present_participle or token.past_participle or token.bare_form:
        blockers.append("explicit verb morphology is deferred beyond G1")
    if token.slot is not None and token.type is not None:
        if token.type not in _SUPPORTED_SLOT_TYPES:
            blockers.append(f"slot type {token.type!r} has no G1 realizer")
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
        if pred.distinct is not None or pred.same_lemma is not None:
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
        blockers.append(f"where predicate {kind!r} is deferred beyond G1")
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


def _domain(token: MatchToken, reg: Registry, fixtures: _Fixtures) -> list[_Filler]:
    if token.lit is not None:
        return [_Filler(option, option) for option in token.lit_options]
    if token.opt is not None or token.slot is None:
        return []
    if token.cat is not None:
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
        return [
            _Filler(surface, surface)
            for surface in sorted(reg.fractions)
            if not any(ch.isspace() for ch in surface)
        ]
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
        blockers.append("only phase: read rules are supported in G1")
    seq = _flat_sentence(rule)
    if seq is None:
        blockers.append("only flat single-sentence premise patterns are supported in G1")
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
    rule: PatternRule, reg: Registry, fixtures: _Fixtures, rng: random.Random
) -> tuple[str, dict[str, str]]:
    seq = _flat_sentence(rule)
    assert seq is not None
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


def _fact_json(fact: Any) -> dict[str, Any]:
    return {
        "type": type(fact).__name__,
        "fields": {
            key: _jsonable(value)
            for key, value in fact.__dict__.items()
            if key != "provenance" and value is not None
        },
        "source": fact.provenance.source,
        "sentence": fact.provenance.sentence,
    }


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
    results: list[RuleMatchResult], reg: Registry
) -> tuple[MatchSummary, ...]:
    return tuple(
        MatchSummary(
            rule_id=result.match.rule.id,
            bindings=_bindings(result),
            consumed=result.match.consumed,
            shadowed=any(
                other is not result
                and subsumes(other.match, result.match, reg)
                for other in results
            ),
            emitted_facts=tuple(_fact_json(fact) for fact in result.facts),
        )
        for result in results
    )


def _collision_json(collision: Any) -> dict[str, Any]:
    return {
        "key": _jsonable(collision.key),
        "a_source": collision.a_source,
        "b_source": collision.b_source,
        "a_value": _jsonable(collision.a_value),
        "b_value": _jsonable(collision.b_value),
    }


def generate_candidate(
    project: Project,
    *,
    rule_id: str | None = None,
    seed: int | None = None,
    max_attempts: int = 64,
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
            raise GenerationError("this project has no G1-supported premise rules")
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
                rule, project.registry, fixtures, rng
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

    target_results = [
        result for result in last_results if result.match.rule.id == rule.id
    ]
    if not target_results:
        status = "absent"
        target_bindings = {}
    else:
        target_shadowed = all(
            any(
                other is not result
                and subsumes(other.match, result.match, project.registry)
                for other in last_results
            )
            for result in target_results
        )
        status = "shadowed" if target_shadowed else "matched"
        target_bindings = _bindings(target_results[0])
    digest = hashlib.sha256(
        (
            f"{project.registry.fingerprint}\0{seed}\0{rule.id}\0"
            f"{last_sentence}"
        ).encode()
    ).hexdigest()[:20]
    return GenerationCandidate(
        id=f"gen-{digest}",
        project=project.doc.name,
        registry_fingerprint=project.registry.fingerprint,
        generator_version=GENERATOR_VERSION,
        seed=seed,
        target_rule=rule.id,
        target_description=rule.description,
        sentence=last_sentence,
        requested_bindings=last_bindings,
        target_bindings=target_bindings,
        target_status=status,
        actual_matches=_match_summaries(last_results, project.registry),
        facts=tuple(_fact_json(fact) for fact in last_doc.store.facts),
        collisions=tuple(
            _collision_json(collision)
            for collision in last_doc.store.collisions
        ),
        deficiencies=tuple(last_reading.deficiencies()),
        attempts=attempt,
    )
