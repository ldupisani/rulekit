"""Deterministic ask surfaces and minimal generated evidence scenarios.

Ask realization reuses the same project-backed token domains as premise
generation. Answerable scenarios search only declarative premise rules and
their emitted field templates; they never read a benchmark item, maintain a
question template, or bypass the ordinary ``solve`` pipeline.
"""

from __future__ import annotations

import hashlib
import random
import re
import secrets
from dataclasses import replace
from itertools import combinations, product
from typing import Any, Iterable

from ..data.project import Project
from ..data.schemas import AskRule, MatchToken, PatternRule
from ..kernel.engine import analyze, solve
from ..kernel.model import Unit, _jsonable
from ..kernel.patterns import _check_where, match_ask, match_sequence
from .candidate import (
    AskAvailability,
    AskScenarioCandidate,
    AskScenarioMode,
)
from .reviews import (
    ask_review_consumer_counts,
    ask_review_surface_counts,
    ask_review_surface_signature,
    ask_review_target_counts,
    validated_premise_candidates,
    validated_premise_rule_usage_counts,
)
from .sample import (
    GENERATOR_VERSION,
    GenerationError,
    _Filler,
    _domain,
    _filler_category_term_contains,
    _filler_in_category,
    _leaf_tokens,
    _load_fixtures,
    _selectional_assignment_compatible,
    _token_nodes,
    generate_candidate,
    list_rule_availability,
)

ASK_GENERATOR_VERSION = (
    f"{GENERATOR_VERSION}+g7-validated-evidence-frontier-source-alignment"
)
_MAX_RANDOM_ANSWERABLE_ASKS = 8
_MAX_RANDOM_VALIDATED_ASKS = 32
_MAX_RANDOM_VALIDATED_SEARCH_ATTEMPTS = 8
_MAX_VALIDATED_PREMISE_POOL = 16
_MAX_VALIDATED_SURFACE_ATTEMPTS = 16
_SCENARIO_PREMISE_ATTEMPTS = 4
_ASK_SCENARIO_MODES: tuple[AskScenarioMode, ...] = (
    "ask_only",
    "answerable",
    "validated_premises",
    "missing_evidence",
)
_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":"})
_WHOLE_TEMPLATE = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)(?:\.([^}]+))?\}$")
_NON_IDENTITY_QUERY_FIELDS = frozenset(
    {
        "consumer",
        "measure_surface",
        "dimension_measure",
        "sum_measure_variants",
        "reference_time",
        "evidence_reference_time_required",
        "require_entity_owner_evidence",
        "op",
        "polarity",
    }
)


def _query_field_value(query: dict[str, Any], path: str) -> Any:
    """Resolve a declared scalar query path such as ``holders.1``."""

    value: Any = query
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            index = int(part)
            value = value[index] if index < len(value) else None
        else:
            return None
    return value


def _iter_resolution_values(ask: AskRule) -> Iterable[str]:
    mappings = [ask.resolves] if ask.resolves else [
        interpretation.resolves for interpretation in ask.interpretations
    ]
    for mapping in mappings:
        for raw in mapping.values():
            if isinstance(raw, str):
                yield raw
            else:
                yield from raw


def _span_contracts(ask: AskRule) -> dict[str, str]:
    contracts: dict[str, str] = {}
    for raw in _iter_resolution_values(ask):
        match = _WHOLE_TEMPLATE.fullmatch(raw)
        if match is not None and match.group(2) in {
            "name_list",
            "group_members",
        }:
            contracts[match.group(1)] = match.group(2)
    return contracts


def _context_required_blocker(ask: AskRule) -> str:
    if ask.generation.context_strategy == "evidence":
        return "ask requires generated premise evidence; standalone realization is disabled"
    return "ask requires embedding context; standalone realization is disabled"


def _name_list_fillers(project: Project) -> list[_Filler]:
    fixtures = _load_fixtures(project.root)
    if len(fixtures.names) < 2:
        return []
    conjunctions = _domain(
        MatchToken(slot="conjunction", cat="holder_list_conjunction"),
        project.registry,
        fixtures,
    )
    if not conjunctions:
        return []
    fillers: list[_Filler] = []
    maximum = min(4, len(fixtures.names))
    for count in range(2, maximum + 1):
        for names in combinations(fixtures.names, count):
            for conjunction in conjunctions:
                if count == 2:
                    surface = f"{names[0]} {conjunction.surface} {names[1]}"
                else:
                    surface = (
                        ", ".join(names[:-1])
                        + f", {conjunction.surface} {names[-1]}"
                    )
                fillers.append(
                    _Filler(
                        surface=surface,
                        identity="|".join(name.casefold() for name in names),
                        kind="name-list",
                    )
                )
    return fillers


def _ask_token_domain(
    project: Project,
    ask: AskRule,
    token: MatchToken,
) -> list[_Filler]:
    source = ask.generation.slot_sources.get(token.slot or "")
    if source == "reference_group":
        return [
            _Filler(
                surface=value.title(),
                identity=value,
                number="singular",
                kind="name",
            )
            for value in sorted(set(project.registry.reference_groups.values()))
        ]
    if source == "reference_year":
        return [
            _Filler(
                surface=str(year),
                identity=str(year),
                number="plural" if year != 1 else "singular",
                kind="number",
                value=float(year),
            )
            for year in sorted(
                {
                    year
                    for _, _, year in project.registry.reference
                    if year is not None
                }
            )
        ]
    category = ask.generation.slot_categories.get(token.slot or "")
    if category is not None:
        categories = category if isinstance(category, list) else [category]
        fixtures = _load_fixtures(project.root)
        structural_updates: dict[str, Any] = {"type": None}
        # A generation-only lexical category narrows vocabulary; it must not
        # erase morphology encoded by the reader's broad slot type. Category
        # domains express those same structures as explicit qualifiers.
        if token.type in {"plural", "bare_plural", "generic_plural"}:
            structural_updates["number"] = "plural"
        elif token.type == "counted":
            structural_updates["counted"] = True
        elif token.type == "possessed":
            structural_updates["possessed"] = True
        elif token.type == "qualified":
            structural_updates["qualified"] = True
        domain = [
            filler
            for declared in categories
            for filler in _domain(
                token.model_copy(
                    update={**structural_updates, "cat": declared}
                ),
                project.registry,
                fixtures,
            )
        ]
        return list(
            {
                (filler.surface, filler.identity, filler.number): filler
                for filler in domain
            }.values()
        )
    if token.span:
        contract = _span_contracts(ask).get(token.slot or "")
        return _name_list_fillers(project) if contract == "name_list" else []
    fixtures = _load_fixtures(project.root)
    domain = _domain(token, project.registry, fixtures)
    if token.type == "noun" and token.number is None:
        # A matcher noun is identity-based and therefore accepts declared
        # singular or plural surfaces. Premise realization often needs the
        # singular default, but asks such as ``how many NOUN`` expose the
        # missing number constraint unless both declared forms are visible.
        plural_token = token.model_copy(update={"type": "plural"})
        domain = [*domain, *_domain(plural_token, project.registry, fixtures)]
    return list(
        {
            (filler.surface, filler.identity, filler.number): filler
            for filler in domain
        }.values()
    )


def _ask_blockers(project: Project, ask: AskRule) -> tuple[str, ...]:
    blockers: list[str] = []
    if ask.generation.context_required:
        blockers.append(_context_required_blocker(ask))
    contracts = _span_contracts(ask)
    if "group_members" in contracts.values():
        blockers.append(
            "ask requires an antecedent discourse group; generate it as a "
            "contextual scenario"
        )
    for _, token, _ in _leaf_tokens(ask.match["question"]):
        label = token.slot or repr(token.lit)
        if token.span and contracts.get(token.slot or "") != "name_list":
            blockers.append(
                f"span {label} has no bounded declared ask realizer"
            )
            continue
        if not _ask_token_domain(project, ask, token):
            blockers.append(f"no project-backed ask filler exists for {label}")
    if ask.generation.evidence_rules:
        rule_availability = {
            item.id: item for item in list_rule_availability(project)
        }
        blockers.extend(
            f"declared evidence rule {step.rule!r} is not generatable"
            for step in ask.generation.evidence_rules
            if step.rule not in rule_availability
            or not rule_availability[step.rule].supported
        )
    return tuple(dict.fromkeys(blockers))


def _ask_mode_blockers(
    project: Project,
    ask: AskRule,
    scenario_mode: AskScenarioMode,
) -> tuple[str, ...]:
    """Return only blockers that apply to one requested scenario mode.

    Independent support remains deliberately stricter than contextual
    support. A generated document may establish a discourse antecedent or
    premise evidence, but ask-only generation must not fabricate either by
    mutating a standalone reading.
    """

    blockers = list(_ask_blockers(project, ask))
    contracts = _span_contracts(ask)
    group_blocker = (
        "ask requires an antecedent discourse group; generate it as a "
        "contextual scenario"
    )
    context_blocker = _context_required_blocker(ask)
    if (
        "group_members" in contracts.values()
        and scenario_mode in {"answerable", "validated_premises"}
    ):
        blockers = [blocker for blocker in blockers if blocker != group_blocker]
    strategy = ask.generation.context_strategy
    allowed_context_modes = {
        "evidence": {"answerable", "validated_premises", "missing_evidence"},
        "conditional": {"answerable", "validated_premises"},
    }
    if strategy is not None and scenario_mode in allowed_context_modes[strategy]:
        blockers = [blocker for blocker in blockers if blocker != context_blocker]
    return tuple(blockers)


def _ask_filler_satisfies_known_where(
    project: Project,
    ask: AskRule,
    slot: str | None,
    filler: _Filler,
    chosen: dict[str, _Filler],
) -> bool:
    """Prune a filler when an Ask ``where`` predicate is already decidable.

    Ask realization remains ordinary declarative matching: this only avoids
    spending the bounded retry budget on combinations the matcher must reject
    later. Predicates whose other slots are not yet chosen stay undecided.
    """

    if slot is None:
        return True
    reg = project.registry

    def value(name: str) -> _Filler | None:
        return filler if name == slot else chosen.get(name)

    for predicate in ask.where:
        exclusion = predicate.slot_not_category
        if (
            exclusion is not None
            and exclusion.get("slot") == slot
            and _filler_in_category(filler, exclusion["cat"], reg)
        ):
            return False

        if (
            predicate.number_compatible is not None
            and slot in predicate.number_compatible
        ):
            numbers = {
                known.number
                for name in predicate.number_compatible
                if (known := value(name)) is not None
                and known.number in {"singular", "plural"}
            }
            if len(numbers) > 1:
                return False

        owner_match = predicate.owner_matches
        if owner_match is not None:
            owner = value(owner_match.owner)
            possessed = value(owner_match.possessed)
            if (
                owner is not None
                and possessed is not None
                and possessed.owner != owner.identity
            ):
                return False

        if predicate.distinct is not None and slot in predicate.distinct:
            if any(
                other != slot
                and (known := value(other)) is not None
                and known.identity == filler.identity
                for other in predicate.distinct
            ):
                return False

        containment = predicate.category_contains
        if containment is not None:
            collection = value(containment.collection)
            members = [value(name) for name in containment.members]
            if collection is not None and any(
                member is not None
                and not _filler_category_term_contains(
                    collection, member, reg
                )
                for member in members
            ):
                return False

        if (
            predicate.mutually_exclusive is not None
            and slot in predicate.mutually_exclusive
            and any(
                other != slot and value(other) is not None
                for other in predicate.mutually_exclusive
            )
        ):
            return False

        conditional = predicate.bound_requires_category
        if conditional is not None:
            bound = value(conditional.bound)
            target = value(conditional.slot)
            if (
                bound is not None
                and target is not None
                and not (
                    conditional.allow_proper_name and target.kind == "name"
                )
                and not _filler_in_category(target, conditional.cat, reg)
            ):
                return False

        compatibility = predicate.attribute_compatible
        if compatibility is not None:
            attribute = value(compatibility.attribute)
            noun = value(compatibility.noun)
            if (
                attribute is not None
                and noun is not None
                and not reg.attribute_applies_to(
                    attribute.identity, noun.identity
                )
            ):
                return False

        measure_compatibility = predicate.measure_holder_compatible
        if measure_compatibility is not None:
            measure = value(measure_compatibility.measure)
            if (
                measure is not None
                and not (
                    measure_compatibility.when_declared
                    and not reg.measure_has_holder_boundary(measure.identity)
                )
            ):
                for holder_name in measure_compatibility.holders:
                    holder = value(holder_name)
                    if holder is None:
                        continue
                    proper_categories = (
                        measure_compatibility.proper_name_measure_categories
                    )
                    proper_allowed = (
                        holder.kind == "name"
                        and measure_compatibility.allow_proper_name
                        and (
                            not proper_categories
                            or any(
                                _filler_in_category(measure, category, reg)
                                for category in proper_categories
                            )
                        )
                    )
                    if not proper_allowed and not reg.measure_applies_to_holder(
                        measure.identity, holder.identity
                    ):
                        return False

        role_compatibility = predicate.verb_role_compatible
        if role_compatibility is not None:
            verb = value(role_compatibility.verb)
            if verb is not None and _filler_in_category(
                verb, role_compatibility.verb_cat, reg
            ):
                role_category = (
                    role_compatibility.role_cat
                    or role_compatibility.excluded_role_cat
                )
                assert role_category is not None
                for role_name in role_compatibility.roles:
                    role = value(role_name)
                    if role is None:
                        continue
                    in_category = _filler_in_category(role, role_category, reg)
                    if role_compatibility.role_cat is not None and not in_category:
                        return False
                    if (
                        role_compatibility.excluded_role_cat is not None
                        and in_category
                    ):
                        return False

        roles_compatibility = predicate.verb_roles_compatible
        if roles_compatibility is not None:
            verb = value(roles_compatibility.verb)
            if verb is not None:
                assignments = {**chosen, slot: filler}
                if not _selectional_assignment_compatible(
                    verb, assignments, roles_compatibility, reg
                ):
                    return False

        partitive = predicate.partitive_compatible
        if partitive is not None:
            measure = value(partitive.measure)
            substance = value(partitive.substance)
            if measure is not None and substance is None:
                if not any(
                    reg.partitive_applies_to(measure.identity, word)
                    for word in reg.lexicon
                ):
                    return False
                continue
            if substance is not None and measure is None:
                if not any(
                    reg.partitive_applies_to(word, substance.identity)
                    for word in reg.lexicon
                ):
                    return False
                continue
            if (
                measure is not None
                and substance is not None
                and not reg.partitive_applies_to(
                    measure.identity, substance.identity
                )
            ):
                return False

    return True


def list_ask_availability(project: Project) -> list[AskAvailability]:
    """Report ask-surface support without executing a generated question."""

    availability: list[AskAvailability] = []
    for ask in project.registry.asks:
        blockers = _ask_blockers(project, ask)
        supported_modes = tuple(
            mode
            for mode in _ASK_SCENARIO_MODES
            if not _ask_mode_blockers(project, ask, mode)
        )
        availability.append(
            AskAvailability(
                id=ask.id,
                consumer=(
                    str(ask.resolves.get("consumer"))
                    if ask.resolves.get("consumer") is not None
                    else None
                ),
                supported="ask_only" in supported_modes,
                blockers=blockers,
                supported_modes=supported_modes,
            )
        )
    return availability


def _optional_choices(
    tokens: list[MatchToken],
    rng: random.Random,
    forced_slots: set[str],
    omitted_slots: set[str],
) -> dict[tuple[int, ...], bool]:
    choices: dict[tuple[int, ...], bool] = {}

    def choose(
        branch: list[MatchToken],
        parent: tuple[int, ...] = (),
    ) -> None:
        for token_no, token in enumerate(branch):
            path = (*parent, token_no)
            if token.opt is None:
                continue
            nested_slots = {
                child.slot
                for _, child, _ in _leaf_tokens(token.opt)
                if child.slot is not None
            }
            if nested_slots & omitted_slots:
                include = False
            else:
                include = bool(nested_slots & forced_slots) or bool(
                    rng.randrange(2)
                )
            choices[path] = include
            if include:
                choose(token.opt, path)

    choose(tokens)
    return choices


def _realize_ask(
    project: Project,
    ask: AskRule,
    rng: random.Random,
    locked_bindings: dict[str, str],
) -> tuple[str, dict[str, str]]:
    sequence = ask.match["question"]
    declared_slots = {
        token.slot
        for _, token, _ in _leaf_tokens(sequence)
        if token.slot is not None
    }
    unknown = set(locked_bindings) - declared_slots
    if unknown:
        raise GenerationError(
            "ask bindings name unknown slots: " + ", ".join(sorted(unknown))
        )
    omitted_slots = set(ask.generation.omit_slots)
    locked_omitted = set(locked_bindings) & omitted_slots
    if locked_omitted:
        raise GenerationError(
            "ask bindings lock generation-omitted slots: "
            + ", ".join(sorted(locked_omitted))
        )
    optionals = _optional_choices(
        sequence,
        rng,
        set(locked_bindings),
        omitted_slots,
    )
    chosen: dict[str, _Filler] = {}
    surfaces: list[str] = []
    previous_filler: _Filler | None = None

    def realize(
        tokens: list[MatchToken],
        parent: tuple[int, ...] = (),
    ) -> None:
        nonlocal previous_filler
        for token_no, token in enumerate(tokens):
            path = (*parent, token_no)
            if token.opt is not None:
                if optionals.get(path, False):
                    realize(token.opt, path)
                continue
            if token.slot is not None and token.slot in chosen:
                domain = [chosen[token.slot]]
            else:
                domain = _ask_token_domain(project, ask, token)
            if (
                token.possessed
                and previous_filler is not None
                and project.registry.word_in_category(
                    previous_filler.identity, "possessive_determiner"
                )
            ):
                bare_token = token.model_copy(update={"possessed": False})
                domain = [
                    replace(
                        candidate,
                        owner=previous_filler.identity,
                        reference_form="bare",
                    )
                    for candidate in _ask_token_domain(project, ask, bare_token)
                    if candidate.kind == "noun"
                ]
            if token.generation_bare_reference:
                domain = [
                    candidate
                    for candidate in domain
                    if candidate.reference_form in {None, "bare"}
                ]
            # A generated possessive determiner supplies the following noun's
            # definiteness itself. Keep only the bare common-noun rendering;
            # otherwise an optional branch can realize "his the book". Names
            # are also excluded here because a possessive + proper-name shape
            # needs an appositive contract rather than this ordinary NP slot.
            if (
                token.referential
                and previous_filler is not None
                and project.registry.word_in_category(
                    previous_filler.identity, "possessive_determiner"
                )
            ):
                domain = [
                    filler
                    for filler in domain
                    if filler.reference_form == "bare"
                ]
            elif token.referential and not token.generation_bare_reference:
                # `_domain` exposes a bare common-noun alternative because a
                # preceding possessive may license it.  Once the surrounding
                # branch is known not to contain that determiner, keep only a
                # definite rendering (or an independently declared bare
                # reference).  Besides avoiding wasted retries, this lets a
                # semantic identity lock such as `guardian` realize as `the
                # guardian` instead of forcing an invalid bare surface.
                domain = [
                    filler
                    for filler in domain
                    if filler.reference_form != "bare"
                    or (
                        token.bare_reference_category is not None
                        and _filler_in_category(
                            filler,
                            token.bare_reference_category,
                            project.registry,
                        )
                    )
                ]
            domain = [
                candidate
                for candidate in domain
                if _ask_filler_satisfies_known_where(
                    project,
                    ask,
                    token.slot,
                    candidate,
                    chosen,
                )
            ]
            locked = locked_bindings.get(token.slot or "")
            if locked is not None:
                folded = locked.casefold()
                surface_matches = [
                    filler
                    for filler in domain
                    if filler.surface.casefold() == folded
                ]
                domain = surface_matches or [
                    filler
                    for filler in domain
                    if filler.identity.casefold() == folded
                ]
            if not domain:
                raise GenerationError(
                    f"ask constraints left no filler for {token.slot or token.lit!r}"
                )
            filler = domain[rng.randrange(len(domain))]
            if token.slot is not None:
                chosen[token.slot] = filler
            surfaces.append(filler.surface)
            previous_filler = filler

    realize(sequence)
    question = " ".join(surfaces)
    # English clitics attach to the preceding word. The analyzer keeps them
    # as independent units for matching, but generated surface text should
    # still render the contraction rather than exposing tokenizer spacing.
    question = re.sub(r"\s+('s)\b", r"\1", question)
    question = re.sub(r"\s+([,.;:!?])", r"\1", question)
    if question and question[-1] not in _PUNCTUATION:
        question += "?"
    if question:
        question = question[0].upper() + question[1:]
    return question, {
        name: filler.surface for name, filler in sorted(chosen.items())
    }


def _match_bindings(match) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for name, value in sorted(match.slots.items()):
        if isinstance(value, Unit):
            bindings[name] = value.surface
        else:
            bindings[name] = " ".join(unit.surface for unit in value)
    return bindings


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return _jsonable(value)


def _answer_json(answer) -> tuple[dict[str, Any], str]:
    clarification = answer.clarification
    clarification_json = None
    shape = answer.kind
    if clarification is not None:
        shape = "clarification"
        clarification_json = {
            "prompt": clarification.prompt,
            "selected": clarification.selected,
            "options": [
                {
                    "id": option.id,
                    "label": option.label,
                    "description": option.description,
                }
                for option in clarification.options
            ],
        }
    return (
        {
            "kind": answer.kind,
            "value": _json_value(answer.value),
            "reason": answer.reason,
            "committed": answer.committed,
            "clarification": clarification_json,
        },
        shape,
    )


def _match_generated_ask(
    project: Project,
    ask: AskRule,
    question: str,
    *,
    scenario_mode: AskScenarioMode,
):
    """Match a realized ask, provisionally seeding only group discovery.

    A discourse-group ask cannot resolve its ``{slot.group_members}``
    template until it appears after real premises. For search planning only,
    bind two project-declared fixture names to that exact matched group slot.
    The returned scenario is still accepted solely after ``solve`` rebuilds
    the group from its generated document and the target ask wins normally.
    """

    reading = analyze(question, project.registry, tracing=True)
    matched = match_ask(reading, project.registry)
    contracts = _span_contracts(ask)
    if (
        (matched is not None and matched[0].id == ask.id)
        or "group_members" not in contracts.values()
        or scenario_mode not in {"answerable", "validated_premises"}
    ):
        return matched
    provisional = match_sequence(
        reading,
        ask.match["question"],
        project.registry,
    )
    if provisional is None or not _check_where(
        ask,
        provisional.slots,
        reading,
        project.registry,
    ):
        return None
    fixtures = _load_fixtures(project.root)
    if len(fixtures.names) < 2:
        return None
    members = tuple(name.casefold() for name in fixtures.names[:2])
    for slot, contract in contracts.items():
        if contract != "group_members":
            continue
        unit = provisional.slots.get(slot)
        if not isinstance(unit, Unit):
            return None
        reading.record(
            "generation-provisional-group",
            unit,
            {"referent_group": members},
            "seed an exact group only to plan generated antecedent evidence",
        )
    return match_ask(reading, project.registry)


def _generate_ask_surface(
    project: Project,
    ask: AskRule,
    *,
    seed: int,
    locked_bindings: dict[str, str],
    max_attempts: int,
    scenario_mode: AskScenarioMode,
    reviewed_surfaces: dict[str, int],
) -> tuple[str, dict[str, str], dict[str, str], dict[str, Any], int]:
    blockers = _ask_mode_blockers(project, ask, scenario_mode)
    if blockers:
        raise GenerationError(f"{ask.id} is blocked: {'; '.join(blockers)}")
    rng = random.Random(seed)
    last_error: str | None = None
    best: (
        tuple[str, dict[str, str], dict[str, str], dict[str, Any], int]
        | None
    ) = None
    best_count: int | None = None
    has_reviewed_surfaces = bool(reviewed_surfaces)
    for attempt in range(1, max_attempts + 1):
        try:
            question, requested = _realize_ask(
                project,
                ask,
                rng,
                locked_bindings,
            )
        except GenerationError as exc:
            last_error = str(exc)
            continue
        matched = _match_generated_ask(
            project,
            ask,
            question,
            scenario_mode=scenario_mode,
        )
        if matched is None:
            last_error = "no declared ask matched the realized surface"
            continue
        actual_ask, query, match = matched
        if actual_ask.id != ask.id:
            last_error = f"{actual_ask.id} won the ask specificity tie"
            continue
        if (
            ask.generation.requires_committed_answer
            and not solve(question, project.registry).answer.committed
        ):
            last_error = "generated data-backed ask has no supported answer"
            continue
        candidate = (
            question,
            requested,
            _match_bindings(match),
            _json_value(query),
            attempt,
        )
        if not has_reviewed_surfaces:
            return candidate
        signature = ask_review_surface_signature(
            target_ask=ask.id,
            scenario_mode=scenario_mode,
            consumer=(
                str(query["consumer"])
                if query.get("consumer") is not None
                else None
            ),
            query_fields=list(query.keys()),
            binding_fields=list(requested.keys()),
        )
        count = reviewed_surfaces.get(signature, 0)
        if best_count is None or count < best_count:
            best, best_count = candidate, count
        if count == 0:
            return candidate
        if attempt >= 4 and best is not None:
            return best
    if best is not None:
        return best
    raise GenerationError(
        f"{ask.id} could not realize an exact ask after {max_attempts} "
        f"deterministic attempts: {last_error or 'no viable surface'}"
    )


def _query_identity_values(query: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    values: dict[str, tuple[str, ...]] = {}
    for field, raw in query.items():
        if field in _NON_IDENTITY_QUERY_FIELDS:
            continue
        if isinstance(raw, (str, int, float)):
            values[field] = (str(raw),)
        elif isinstance(raw, list) and all(
            isinstance(item, (str, int, float)) for item in raw
        ):
            values[field] = tuple(str(item) for item in raw)
    entity_values = tuple(
        dict.fromkeys(
            item
            for field in ("entities", "holders", "candidates")
            for item in values.get(field, ())
        )
    )
    if entity_values:
        values.setdefault("entity", entity_values)
    return values


def _emit_lock_variants(
    rule: PatternRule,
    query: dict[str, Any],
) -> list[tuple[int, dict[str, str]]]:
    """Invert exact emit templates into premise slot identity locks.

    Only whole-slot templates can be inverted. Expressions and attributes
    stay unconstrained. Identity locks let a normalized query measure such as
    ``pencil`` select any compatible counted surface such as ``3 pencils``;
    the premise realizer still owns number, morphology, and value selection.
    The ordinary solver decides whether the resulting facts are sufficient.
    """

    query_values = _query_identity_values(query)
    variants: list[tuple[int, dict[str, str]]] = []
    for emit in rule.emits:
        emit_values = dict(query_values)
        if emit.fact == "quantity":
            for attribute in ("owner", "qualifier"):
                if query_values.get(f"entity_{attribute}"):
                    emit_values[attribute] = query_values[f"entity_{attribute}"]
        options: list[list[tuple[str, str] | None]] = []
        score = 0
        for field, raw in emit.fields.items():
            expected = emit_values.get(field)
            if expected is None:
                continue
            if isinstance(raw, str) and (match := _WHOLE_TEMPLATE.fullmatch(raw)):
                if match.group(2) is None:
                    options.append(
                        [(match.group(1), value) for value in expected]
                    )
                    score += 1
                elif match.group(2) in {"owner", "qualifier", "label"}:
                    # Exact feature constraints are realized from ordinary
                    # filler metadata below, not guessed from a head lemma.
                    score += 1
                continue
            if isinstance(raw, (str, int, float, bool)) and any(
                str(raw).casefold() == value.casefold() for value in expected
            ):
                options.append([None])
                score += 1
        if not options:
            variants.append((score, {}))
            continue
        for combination in product(*options):
            locks: dict[str, str] = {}
            consistent = True
            for item in combination:
                if item is None:
                    continue
                slot, value = item
                previous = locks.get(slot)
                if previous is not None and previous.casefold() != value.casefold():
                    consistent = False
                    break
                locks[slot] = value
            if consistent:
                variants.append((score, locks))
    if not rule.emits:
        variants.append((0, {}))
    unique: dict[tuple[tuple[str, str], ...], int] = {}
    for score, locks in variants:
        key = tuple(sorted(locks.items()))
        unique[key] = max(score, unique.get(key, -1))
    return sorted(
        ((score, dict(key)) for key, score in unique.items()),
        key=lambda item: (-item[0], tuple(sorted(item[1].items()))),
    )


def _emit_feature_surface_locks(
    project: Project,
    rule: PatternRule,
    query: dict[str, Any],
    identities: dict[str, str],
    rng: random.Random,
) -> dict[str, str]:
    """Invert declared quantity scope attributes into ordinary surface locks.

    An entity identity alone deliberately leaves its owner/qualifier open.
    Where the ask and emission both name those attributes, constrain them
    together before realization rather than hoping a random owner matches.
    """
    requirements: dict[str, dict[str, str]] = {}
    for emit in rule.emits:
        if emit.fact != "quantity":
            continue
        entity_template = emit.fields.get("entity")
        entity_match = (
            _WHOLE_TEMPLATE.fullmatch(entity_template)
            if isinstance(entity_template, str) else None
        )
        if entity_match is None or entity_match.group(2) is not None:
            continue
        slot = entity_match.group(1)
        for attribute in ("owner", "qualifier"):
            expected = query.get(f"entity_{attribute}")
            if expected and emit.fields.get(attribute) == f"{{{slot}.{attribute}}}":
                requirements.setdefault(slot, {})[attribute] = str(expected).casefold()
    locked: dict[str, str] = {}
    fixtures = _load_fixtures(project.root)
    for slot, attributes in requirements.items():
        token = next(
            token for _, token, _ in _leaf_tokens(rule.match["sentence"])
            if token.slot == slot
        )
        domain = [
            filler for filler in _domain(token, project.registry, fixtures)
            if (slot not in identities or filler.identity == identities[slot])
            and all(
                getattr(filler, attr, None) == value
                for attr, value in attributes.items()
            )
        ]
        if not domain:
            raise GenerationError(
                f"no premise filler preserves the requested scope of {slot!r}"
            )
        locked[slot] = rng.choice(domain).surface
    return locked


def _compose_scenario_text(
    premises: list[dict[str, Any]],
    question: str,
    *,
    conditional_embedding: bool = False,
) -> str:
    premise_texts = [
        str(premise.get("text") or premise["sentence"]).strip()
        for premise in premises
    ]
    if not conditional_embedding or not premise_texts:
        return " ".join([*premise_texts, question])
    # The embedded order belongs after a subordinate introducer. Use the last
    # ordinary generated premise as that clause and leave any earlier evidence
    # as ordinary sentences. Contextual multi-sentence premise candidates are
    # intentionally ineligible here: embedding only their final surface would
    # detach the context that made them valid.
    embedded = premises[-1]
    if embedded.get("context_before") or embedded.get("context_after"):
        raise GenerationError(
            "conditional ask embedding needs an independent premise candidate"
        )
    clause = str(embedded["sentence"]).strip().rstrip(".?!")
    for article in ("The ", "A ", "An "):
        if clause.startswith(article):
            clause = article.lower() + clause[len(article) :]
            break
    tail = question[0].lower() + question[1:] if question else question
    return " ".join([*premise_texts[:-1], f"If {clause}, {tail}"])


def _solve_text(
    project: Project,
    premises: list[dict[str, Any]],
    question: str,
    *,
    conditional_embedding: bool = False,
    reference_year: int | None = None,
):
    text = _compose_scenario_text(
        premises,
        question,
        conditional_embedding=conditional_embedding,
    )
    return text, solve(
        text,
        project.registry,
        reference_year=reference_year,
    )


def _try_solve_text(
    project: Project,
    premises: list[dict[str, Any]],
    question: str,
    *,
    conditional_embedding: bool = False,
    reference_year: int | None = None,
):
    """Treat a pathological generated combination as a failed search branch."""

    try:
        return _solve_text(
            project,
            premises,
            question,
            conditional_embedding=conditional_embedding,
            reference_year=reference_year,
        )
    except ArithmeticError:
        return None
    except RuntimeError as exc:
        if not str(exc).startswith("saturation did not reach a fixpoint"):
            raise
        return None


def _minimal_committed_premises(
    project: Project,
    premises: list[dict[str, Any]],
    question: str,
    *,
    conditional_embedding: bool = False,
    reference_year: int | None = None,
) -> tuple[list[dict[str, Any]], Any, str]:
    selected = list(premises)
    changed = True
    while changed and len(selected) > 1:
        changed = False
        for index in range(len(selected)):
            trial = selected[:index] + selected[index + 1 :]
            solved = _try_solve_text(
                project,
                trial,
                question,
                conditional_embedding=conditional_embedding,
                reference_year=reference_year,
            )
            if solved is None:
                continue
            text, result = solved
            if result.answer.committed:
                selected = trial
                changed = True
                break
    text, result = _solve_text(
        project,
        selected,
        question,
        conditional_embedding=conditional_embedding,
        reference_year=reference_year,
    )
    return selected, result, text


def _premise_set_is_minimal(
    project: Project,
    premises: list[dict[str, Any]],
    question: str,
    *,
    conditional_embedding: bool = False,
    reference_year: int | None = None,
) -> bool:
    """Prove no generated premise can be removed while retaining an answer."""

    return all(
        (solved := _try_solve_text(
            project,
            premises[:index] + premises[index + 1 :],
            question,
            conditional_embedding=conditional_embedding,
            reference_year=reference_year,
        )) is None
        or not solved[1].answer.committed
        for index in range(len(premises))
    )


def _search_answerable_scenario(
    project: Project,
    ask: AskRule,
    question: str,
    query: dict[str, Any],
    *,
    rng: random.Random,
    max_search_attempts: int,
    reference_year: int | None = None,
) -> tuple[list[dict[str, Any]], Any, str, int]:
    conditional_embedding = ask.generation.context_strategy == "conditional"
    evidence_query = dict(query)
    if reference_year is not None:
        evidence_query["reference_year"] = reference_year
    ask_only = solve(
        question,
        project.registry,
        reference_year=reference_year,
    )
    if ask_only.answer.committed:
        return [], ask_only, question, 0
    supported = {
        item.id
        for item in list_rule_availability(project)
        if item.supported
    }
    premise_rules = {rule.id: rule for rule in project.registry.rules}
    generated: list[dict[str, Any]] = []
    seen_sentences: set[str] = set()
    search_attempts = 0

    # Some consumers need a complete fact family rather than one arbitrary
    # quantity. The owning ask can preregister ordinary premise rules and map
    # their slots to query fields. This is still grammar-driven generation:
    # no sentence template or expected answer appears here, and ``solve`` is
    # the sole oracle for whether the realized evidence actually suffices.
    for _plan_attempt in range(12 if ask.generation.evidence_rules else 0):
        planned: list[dict[str, Any]] = []
        for step in ask.generation.evidence_rules:
            if step.rule not in supported:
                raise GenerationError(
                    f"ask evidence rule {step.rule!r} is not generatable"
                )
            identity_bindings: dict[str, str] = {}
            surface_bindings: dict[str, str] = {}
            rule = premise_rules[step.rule]
            tokens_by_slot = {
                token.slot: token
                for _, token, _ in _leaf_tokens(rule.match["sentence"])
                if token.slot is not None
            }
            for slot, field in step.bindings.items():
                value = _query_field_value(evidence_query, field)
                if not isinstance(value, (str, int, float)):
                    raise GenerationError(
                        f"ask evidence binding {slot!r} needs scalar query field "
                        f"{field!r}"
                    )
                token = tokens_by_slot.get(slot)
                if token is not None and token.type == "number":
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError) as exc:
                        raise GenerationError(
                            f"ask evidence binding {slot!r} needs numeric query "
                            f"field {field!r}"
                        ) from exc
                    if numeric.is_integer():
                        surface_bindings[slot] = str(int(numeric))
                    else:
                        surface_bindings[slot] = str(numeric)
                else:
                    identity_bindings[slot] = str(value)
            search_attempts += 1
            candidate = generate_candidate(
                project,
                rule_id=step.rule,
                seed=rng.getrandbits(63),
                max_attempts=max(16, _SCENARIO_PREMISE_ATTEMPTS),
                locked_bindings=surface_bindings,
                identity_bindings=identity_bindings,
            ).to_json()
            planned.append(candidate)
            if candidate["sentence"] not in seen_sentences:
                seen_sentences.add(candidate["sentence"])
                generated.append(candidate)
        solved = _try_solve_text(
            project,
            planned,
            question,
            conditional_embedding=conditional_embedding,
            reference_year=reference_year,
        )
        if solved is not None and solved[1].answer.committed:
            minimal, result, text = _minimal_committed_premises(
                project,
                planned,
                question,
                conditional_embedding=conditional_embedding,
                reference_year=reference_year,
            )
            return minimal, result, text, search_attempts

    plans = [
        (
            score,
            len(rule.emits),
            sum(1 for _ in _leaf_tokens(rule.match["sentence"])),
            rule.id,
            locks,
        )
        for rule in project.registry.rules
        if rule.id in supported
        for score, locks in _emit_lock_variants(rule, query)
    ]
    plans.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[2],
            item[3],
            tuple(sorted(item[4].items())),
        )
    )
    for _, _, _, rule_id, identity_locks in plans:
        if search_attempts >= max_search_attempts:
            break
        search_attempts += 1
        try:
            surface_locks = _emit_feature_surface_locks(
                project, premise_rules[rule_id], query, identity_locks, rng,
            )
            candidate = generate_candidate(
                project,
                rule_id=rule_id,
                seed=rng.getrandbits(63),
                max_attempts=_SCENARIO_PREMISE_ATTEMPTS,
                identity_bindings=identity_locks,
                locked_bindings=surface_locks,
            ).to_json()
        except GenerationError:
            continue
        if candidate["sentence"] in seen_sentences:
            continue
        seen_sentences.add(candidate["sentence"])
        generated.append(candidate)
        solved = _try_solve_text(
            project,
            [candidate],
            question,
            conditional_embedding=conditional_embedding,
            reference_year=reference_year,
        )
        if solved is None:
            continue
        text, result = solved
        if result.answer.committed:
            return [candidate], result, text, search_attempts

    # All-or-nothing series, combined totals, and other complete-group asks
    # may need several independently generated premises. Keep the search
    # bounded and deterministic; the ordinary solver remains the only oracle.
    pool = generated[:12]
    for size in (2, 3):
        for group in combinations(pool, size):
            search_attempts += 1
            solved = _try_solve_text(
                project,
                list(group),
                question,
                conditional_embedding=conditional_embedding,
                reference_year=reference_year,
            )
            if solved is None:
                continue
            text, result = solved
            if not result.answer.committed:
                continue
            minimal, result, text = _minimal_committed_premises(
                project,
                list(group),
                question,
                conditional_embedding=conditional_embedding,
                reference_year=reference_year,
            )
            return minimal, result, text, search_attempts
    raise GenerationError(
        "no complete one-to-three-premise scenario was found from supported "
        f"generated rules after {search_attempts} deterministic checks"
    )


def _validated_ask_lock_variants(
    project: Project,
    ask: AskRule,
    premises: tuple[dict[str, Any], ...],
) -> list[tuple[int, dict[str, str]]]:
    """Invert shared fact/query fields into ranked ask identity locks.

    A literal resolve value is evidence-bearing too.  For example,
    ``ask/how-old-is`` fixes ``measure: year`` rather than exposing a measure
    slot.  Counting that exact literal match, with a small specificity bonus,
    keeps a dimension-specific ask ahead of a generic ask that merely happens
    to expose more vocabulary slots.
    """

    facts = [fact for premise in premises for fact in premise.get("facts", [])]
    tokens = {
        token.slot: token
        for _, token, _parent in _leaf_tokens(ask.match["question"])
        if token.slot is not None
    }
    source_locks: dict[str, str] = {}
    source_bindings_compatible = True
    for ask_slot, premise_slot in ask.generation.validated_source_bindings.items():
        source_surfaces = {
            str(fact["derivation"]["bindings"][premise_slot])
            for fact in facts
            if isinstance(fact.get("derivation"), dict)
            and isinstance(fact["derivation"].get("bindings"), dict)
            and fact["derivation"]["bindings"].get(premise_slot)
        }
        if not source_surfaces:
            continue
        if len(source_surfaces) != 1:
            source_bindings_compatible = False
            break
        source_surface = next(iter(source_surfaces))
        compatible_surfaces = {
            filler.surface
            for filler in _ask_token_domain(project, ask, tokens[ask_slot])
            if filler.surface.casefold() == source_surface.casefold()
        }
        if len(compatible_surfaces) != 1:
            source_bindings_compatible = False
            break
        source_locks[ask_slot] = next(iter(compatible_surfaces))
    if not source_bindings_compatible:
        return []
    mappings = [ask.resolves, *(choice.resolves for choice in ask.interpretations)]
    variants: list[tuple[int, dict[str, str]]] = []
    for mapping in mappings:
        locks: dict[str, str] = dict(source_locks)
        literal_matches = 0
        for field, raw in mapping.items():
            if not isinstance(raw, str):
                continue
            values = {
                str(fact["fields"][field])
                for fact in facts
                if isinstance(fact.get("fields"), dict)
                and isinstance(fact["fields"].get(field), str)
                and fact["fields"][field]
            }
            match = _WHOLE_TEMPLATE.fullmatch(raw)
            if match is None:
                if raw.casefold() in {value.casefold() for value in values}:
                    literal_matches += 1
                continue
            if field.startswith("evidence_") and match.group(2) == "surface":
                # Provenance policy may depend on the exact inflected surface
                # even when the semantic fact field stores its lemma (``was``
                # -> verb ``be``). Generated premise evidence already records
                # the matcher bindings in its derivation, so preserve that
                # surface when fabricating an ask from validated evidence.
                # This is generic over every evidence field and slot; no tense
                # word or vocabulary item is named in Python.
                bound_values = {
                    str(fact["derivation"]["bindings"][match.group(1)])
                    for fact in facts
                    if isinstance(fact.get("derivation"), dict)
                    and isinstance(fact["derivation"].get("bindings"), dict)
                    and fact["derivation"]["bindings"].get(match.group(1))
                }
                if len(bound_values) == 1:
                    locks[match.group(1)] = next(iter(bound_values))
                continue
            if len(values) == 1:
                locks[match.group(1)] = next(iter(values))
        for slot, binding in ask.generation.validated_slot_bindings.items():
            token = tokens[slot]
            surfaces: set[str] = set()
            for fact in facts:
                fields = fact.get("fields")
                if not isinstance(fields, dict):
                    continue
                identity = fields.get(binding.identity_field)
                requested_value = (
                    fields.get(binding.value_field)
                    if binding.value_field is not None
                    else None
                )
                if not isinstance(identity, str) or not identity:
                    continue
                for filler in _ask_token_domain(project, ask, token):
                    if filler.identity.casefold() != identity.casefold():
                        continue
                    if binding.value_field is not None:
                        if not isinstance(
                            filler.value, (int, float)
                        ) or not isinstance(requested_value, (int, float)):
                            continue
                        if float(filler.value) != float(requested_value):
                            continue
                    surfaces.add(filler.surface)
            if len(surfaces) == 1:
                locks[slot] = next(iter(surfaces))
        matched_fields = len(locks) + literal_matches
        variants.append((2 * matched_fields + literal_matches, locks))
    unique: dict[tuple[tuple[str, str], ...], int] = {}
    for score, locks in variants:
        key = tuple(sorted(locks.items()))
        unique[key] = max(score, unique.get(key, -1))
    return sorted(
        ((score, dict(key)) for key, score in unique.items()),
        key=lambda item: (-item[0], tuple(sorted(item[1].items()))),
    )


def _validated_query_aligns_with_premises(
    ask: AskRule,
    query: dict[str, Any],
    premises: list[dict[str, Any]],
) -> bool:
    """Require generated query identities to cohere in retained evidence.

    Only direct ``{slot}`` resolve fields are checked: those are the lexical
    identities actually asserted by the generated question.  Constant and
    derived query controls remain the ask/consumer contract.  At least one
    retained fact must jointly support every comparable direct field, so an
    entity from one premise and an unrelated verb from another cannot be
    spliced into a superficially answerable ask.
    """

    facts = [fact for premise in premises for fact in premise.get("facts", [])]
    mappings = [ask.resolves, *(choice.resolves for choice in ask.interpretations)]
    for mapping in mappings:
        comparable: dict[str, str] = {}
        for field, raw in mapping.items():
            if not isinstance(raw, str) or _WHOLE_TEMPLATE.fullmatch(raw) is None:
                continue
            query_value = query.get(field)
            if not isinstance(query_value, str) or not query_value:
                continue
            if any(
                isinstance(fact.get("fields"), dict)
                and isinstance(fact["fields"].get(field), str)
                and fact["fields"][field]
                for fact in facts
            ):
                comparable[field] = query_value.casefold()
        if not comparable:
            return True
        if any(
            isinstance(fact.get("fields"), dict)
            and all(
                isinstance(fact["fields"].get(field), str)
                and fact["fields"][field].casefold() == expected
                for field, expected in comparable.items()
            )
            for fact in facts
        ):
            return True
    return False


def _search_validated_premise_scenario(
    project: Project,
    ask: AskRule,
    *,
    seed: int,
    locked_bindings: dict[str, str],
    max_attempts: int,
    max_search_attempts: int,
    reviewed_surfaces: dict[str, int],
    premise_pool: list[dict[str, Any]],
    reference_year: int | None = None,
) -> tuple[
    str,
    dict[str, str],
    dict[str, str],
    dict[str, Any],
    int,
    list[dict[str, Any]],
    Any,
    str,
    int,
]:
    """Generate an ask whose only evidence is replay-valid human review."""

    if not premise_pool:
        raise GenerationError("this project has no replay-valid premise reviews")
    # Reviews are grouped in rule-id order, which has no bearing on whether a
    # premise can support this ask.  Rank the complete pool for the selected
    # ask before bounding combination search.  The old ``pool[:24]`` silently
    # excluded useful later evidence and then spent the whole budget replaying
    # irrelevant early reviews.
    ranked_pool: list[tuple[int, int, dict[str, Any]]] = []
    for index, premise in enumerate(premise_pool):
        score = max(
            (
                variant_score
                for variant_score, _locks in _validated_ask_lock_variants(
                    project, ask, (premise,)
                )
            ),
            default=0,
        )
        ranked_pool.append((score, index, premise))
    ranked_pool.sort(key=lambda item: (-item[0], item[1]))
    plans: list[tuple[int, int, tuple[str, ...], tuple[dict[str, Any], ...], dict[str, str]]] = []
    bounded_pool = [
        premise
        for _score, _index, premise in ranked_pool[:_MAX_VALIDATED_PREMISE_POOL]
    ]
    for size in (1, 2, 3):
        for group in combinations(bounded_pool, size):
            ids = tuple(str(item.get("validated_review_id") or "") for item in group)
            for score, locks in _validated_ask_lock_variants(
                project, ask, group
            ):
                plans.append((score, size, ids, group, locks))
    plans.sort(key=lambda item: (-item[0], item[1], item[2]))
    rng = random.Random(seed)
    search_attempts = 0
    last_error: Exception | None = None
    for _score, _size, _ids, group, derived_locks in plans:
        if search_attempts >= max_search_attempts:
            break
        search_attempts += 1
        locks = {**derived_locks, **locked_bindings}
        try:
            question, requested, actual, query, attempts = _generate_ask_surface(
                project,
                ask,
                seed=rng.getrandbits(63),
                locked_bindings=locks,
                max_attempts=min(
                    max_attempts,
                    _MAX_VALIDATED_SURFACE_ATTEMPTS,
                ),
                scenario_mode="validated_premises",
                reviewed_surfaces=reviewed_surfaces,
            )
        except GenerationError as exc:
            last_error = exc
            continue
        if solve(
            question,
            project.registry,
            tracing=False,
            reference_year=reference_year,
        ).answer.committed:
            continue
        conditional_embedding = (
            ask.generation.context_strategy == "conditional"
        )
        solved = _try_solve_text(
            project,
            list(group),
            question,
            conditional_embedding=conditional_embedding,
            reference_year=reference_year,
        )
        if solved is None or not solved[1].answer.committed:
            continue
        minimal, result, text = _minimal_committed_premises(
            project,
            list(group),
            question,
            conditional_embedding=conditional_embedding,
            reference_year=reference_year,
        )
        # Minimization can remove the premise that licensed a generated slot.
        # Recheck against the evidence that will actually be shown and saved;
        # a committed number is insufficient when the retained facts say
        # ``verb: be`` but the question asks with an unrelated ``verb: own``.
        if not _validated_query_aligns_with_premises(ask, query, minimal):
            last_error = GenerationError(
                "generated ask identities are unsupported by retained evidence"
            )
            continue
        return (
            question,
            requested,
            actual,
            query,
            attempts,
            minimal,
            result,
            text,
            search_attempts,
        )
    raise GenerationError(
        "no answerable scenario was found from replay-valid reviewed premises "
        f"after {search_attempts} deterministic checks"
        + (f": {last_error}" if last_error else "")
    )


def _validated_ask_frontier(
    project: Project,
    asks: list[AskRule],
    premise_pool: list[dict[str, Any]],
    *,
    target_counts: dict[str, int],
    consumer_counts: dict[str, int],
    premise_rule_usage: dict[str, int],
) -> list[AskRule]:
    """Order asks by unexplored evidence, consumer/target novelty, then coherence.

    Field overlap is useful for locating possible evidence, but it is not a
    semantic proof: a ``Rate`` and a ``Quantity`` can expose the same entity,
    measure, and verb fields while supporting different consumers.  The old
    compatibility-first sort consequently kept returning age surfaces and
    hid every candidate below an eight-ask cutoff.  Human-confirmed use of a
    premise rule is the stronger authoring signal.  We therefore advance the
    least-used evidence family first, then the least-reviewed semantic
    consumer and ask target, and use overlap only to rank otherwise equal
    possibilities. Ordinary ``solve`` remains the sole acceptance oracle.
    """

    ranked: list[tuple[int, int, int, int, int, AskRule]] = []
    for position, ask in enumerate(asks):
        possibilities: list[tuple[int, int, int]] = []
        for premise_position, premise in enumerate(premise_pool):
            score = max(
                (
                    variant_score
                    for variant_score, _locks in _validated_ask_lock_variants(
                        project, ask, (premise,)
                    )
                ),
                default=0,
            )
            if score <= 0:
                continue
            rule_id = str(premise.get("target_rule") or "")
            possibilities.append(
                (
                    premise_rule_usage.get(rule_id, 0),
                    -score,
                    premise_position,
                )
            )
        best = min(possibilities, default=(10**9, 0, 10**9))
        mappings = [
            ask.resolves,
            *(choice.resolves for choice in ask.interpretations),
        ]
        consumers = {
            mapping.get("consumer")
            for mapping in mappings
            if isinstance(mapping.get("consumer"), str)
            and not str(mapping["consumer"]).startswith("{")
        }
        consumer_count = min(
            (consumer_counts.get(str(consumer), 0) for consumer in consumers),
            default=10**9,
        )
        ranked.append(
            (
                best[0],
                consumer_count,
                target_counts.get(ask.id, 0),
                best[1],
                position,
                ask,
            )
        )
    ranked.sort(key=lambda item: item[:4])
    return [item[-1] for item in ranked]


def generate_ask_scenario(
    project: Project,
    *,
    ask_id: str | None = None,
    seed: int | None = None,
    scenario_mode: AskScenarioMode = "ask_only",
    reference_year: int | None = None,
    locked_bindings: dict[str, str] | None = None,
    max_attempts: int = 64,
    max_search_attempts: int = 48,
) -> AskScenarioCandidate:
    """Generate one exact ask and optionally its smallest found evidence set."""

    if scenario_mode not in {
        "ask_only", "answerable", "validated_premises", "missing_evidence"
    }:
        raise GenerationError(f"unknown ask scenario mode {scenario_mode!r}")
    seed = secrets.randbits(63) if seed is None else seed
    rng = random.Random(seed)
    asks = {ask.id: ask for ask in project.registry.asks}
    availability = {
        item.id: item for item in list_ask_availability(project)
    }
    reviewed_surfaces = ask_review_surface_counts(project)
    validated_pool = (
        validated_premise_candidates(project)
        if scenario_mode == "validated_premises"
        else []
    )
    if scenario_mode == "validated_premises" and not validated_pool:
        raise GenerationError("this project has no replay-valid premise reviews")
    if ask_id is None:
        supported = [
            asks[item.id]
            for item in availability.values()
            if item.supports(scenario_mode)
        ]
        if not supported:
            raise GenerationError("this project has no supported ask surfaces")
        review_counts = (
            ask_review_target_counts(
                project,
                scenario_mode="validated_premises",
            )
            if scenario_mode == "validated_premises"
            else ask_review_target_counts(project)
        )
        # Human-confirmed asks stay available, but random generation advances
        # the least validated target frontier first. Seeded rotation only
        # breaks ties, retaining exact reproducibility without allowing the
        # ledger to become a runtime input.
        start = rng.randrange(len(supported))
        rotated = supported[start:] + supported[:start]
        ordered = sorted(rotated, key=lambda ask: review_counts.get(ask.id, 0))
        if scenario_mode == "validated_premises" and validated_pool:
            ordered = _validated_ask_frontier(
                project,
                ordered,
                validated_pool,
                target_counts=review_counts,
                consumer_counts=ask_review_consumer_counts(
                    project,
                    scenario_mode="validated_premises",
                ),
                premise_rule_usage=validated_premise_rule_usage_counts(project),
            )
        ask_candidates = (
            ordered[
                :(
                    _MAX_RANDOM_VALIDATED_ASKS
                    if scenario_mode == "validated_premises"
                    else _MAX_RANDOM_ANSWERABLE_ASKS
                )
            ]
            if scenario_mode in {"answerable", "validated_premises"}
            else ordered[:1]
        )
    else:
        ask = asks.get(ask_id)
        if ask is None:
            raise GenerationError(f"unknown ask rule {ask_id!r}")
        item = availability[ask.id]
        if not item.supports(scenario_mode):
            mode_blockers = _ask_mode_blockers(project, ask, scenario_mode)
            raise GenerationError(
                f"{ask.id} is blocked in {scenario_mode}: "
                f"{'; '.join(mode_blockers or item.blockers)}"
            )
        ask_candidates = [ask]

    last_error: Exception | None = None
    for ask in ask_candidates:
        try:
            if scenario_mode == "validated_premises":
                (
                    question,
                    requested,
                    actual,
                    query,
                    attempts,
                    premises,
                    result,
                    text,
                    search_attempts,
                ) = _search_validated_premise_scenario(
                    project,
                    ask,
                    seed=seed,
                    locked_bindings=dict(locked_bindings or {}),
                    max_attempts=max_attempts,
                    max_search_attempts=(
                        max_search_attempts
                        if ask_id is not None
                        else min(
                            max_search_attempts,
                            _MAX_RANDOM_VALIDATED_SEARCH_ATTEMPTS,
                        )
                    ),
                    reviewed_surfaces=reviewed_surfaces,
                    premise_pool=validated_pool,
                    reference_year=reference_year,
                )
                ask_only = solve(
                    question,
                    project.registry,
                    reference_year=reference_year,
                )
            else:
                question, requested, actual, query, attempts = _generate_ask_surface(
                    project,
                    ask,
                    seed=seed,
                    locked_bindings=dict(locked_bindings or {}),
                    max_attempts=max_attempts,
                    scenario_mode=scenario_mode,
                    reviewed_surfaces=reviewed_surfaces,
                )
                ask_only = solve(
                    question,
                    project.registry,
                    reference_year=reference_year,
                )
                premises = []
                result = ask_only
                text = question
                search_attempts = 0
            if scenario_mode == "answerable":
                premises, result, text, search_attempts = (
                    _search_answerable_scenario(
                        project,
                        ask,
                        question,
                        query,
                        rng=rng,
                        max_search_attempts=max_search_attempts,
                        reference_year=reference_year,
                    )
                )
                if not result.answer.committed:  # pragma: no cover
                    raise GenerationError(
                        "answerable scenario search returned no commitment"
                    )
            elif scenario_mode == "missing_evidence" and result.answer.committed:
                raise GenerationError(
                    "the generated ask committed without premises, so it is not a "
                    "missing-evidence scenario"
                )
            if scenario_mode in {"answerable", "validated_premises"}:
                if result.question is None:
                    raise GenerationError(
                        "generated contextual scenario lost its question"
                    )
                final_match = match_ask(result.question, project.registry, store=result.store)
                if final_match is None or final_match[0].id != ask.id:
                    winner = None if final_match is None else final_match[0].id
                    raise GenerationError(
                        f"generated context did not activate {ask.id}; "
                        f"winner was {winner or 'none'}"
                    )
                _actual_ask, final_query, final_binding = final_match
                query = _json_value(final_query)
                actual = _match_bindings(final_binding)
        except (GenerationError, ArithmeticError) as exc:
            last_error = exc
            if ask_id is not None or scenario_mode not in {
                "answerable", "validated_premises"
            }:
                if isinstance(exc, GenerationError):
                    raise
                raise GenerationError(str(exc)) from exc
            continue

        answer, answer_shape = _answer_json(result.answer)
        digest = hashlib.sha256(
            (
                f"{project.registry.fingerprint}\0{scenario_mode}\0{seed}\0"
                f"{reference_year}\0{ask.id}\0{text}"
            ).encode()
        ).hexdigest()[:20]
        source = project.source_index.asks.get(ask.id)
        return AskScenarioCandidate(
            id=f"askgen-{digest}",
            project=project.doc.name,
            registry_fingerprint=project.registry.fingerprint,
            generator_version=ASK_GENERATOR_VERSION,
            scenario_mode=scenario_mode,
            seed=seed,
            reference_year=reference_year,
            target_ask=ask.id,
            consumer=(
                str(query.get("consumer"))
                if query.get("consumer") is not None
                else None
            ),
            question=question,
            text=text,
            requested_bindings=requested,
            target_bindings=actual,
            query=query,
            target_source=source.to_json() if source is not None else None,
            premises=tuple(premises),
            answer=answer,
            answer_shape=answer_shape,
            minimal=_premise_set_is_minimal(
                project,
                premises,
                question,
                conditional_embedding=(
                    ask.generation.context_strategy == "conditional"
                ),
                reference_year=reference_year,
            ),
            attempts=attempts,
            search_attempts=search_attempts,
        )

    raise GenerationError(
        "no answerable scenario was found for the first "
        f"{len(ask_candidates)} deterministic supported asks: "
        f"{last_error or 'no viable scenario'}"
    )
