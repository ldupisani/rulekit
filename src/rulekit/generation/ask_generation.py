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
from ..kernel.patterns import match_ask
from .candidate import (
    AskAvailability,
    AskScenarioCandidate,
    AskScenarioMode,
)
from .sample import (
    GENERATOR_VERSION,
    GenerationError,
    _Filler,
    _domain,
    _filler_in_category,
    _leaf_tokens,
    _load_fixtures,
    _token_nodes,
    generate_candidate,
    list_rule_availability,
)

ASK_GENERATOR_VERSION = f"{GENERATOR_VERSION}+g7-asks-data-domains"
_MAX_RANDOM_ANSWERABLE_ASKS = 8
_SCENARIO_PREMISE_ATTEMPTS = 4
_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":"})
_WHOLE_TEMPLATE = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)(?:\.([^}]+))?\}$")
_NON_IDENTITY_QUERY_FIELDS = frozenset(
    {
        "consumer",
        "measure_surface",
        "dimension_measure",
        "sum_measure_variants",
        "reference_time",
        "op",
        "polarity",
    }
)


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
        domain = [
            filler
            for declared in categories
            for filler in _domain(
                token.model_copy(update={"type": None, "cat": declared}),
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
        blockers.append(
            "ask requires embedding context; standalone realization is disabled"
        )
    contracts = _span_contracts(ask)
    if "group_members" in contracts.values():
        blockers.append(
            "ask requires an antecedent discourse group; generate it as a "
            "contextual scenario"
        )
    for _, token, _ in _leaf_tokens(ask.match["question"]):
        label = token.slot or repr(token.lit)
        if token.present_participle or token.past_participle:
            blockers.append(
                f"{label} requires explicit verb morphology with no ask realizer"
            )
            continue
        if token.span and contracts.get(token.slot or "") != "name_list":
            blockers.append(
                f"span {label} has no bounded declared ask realizer"
            )
            continue
        if not _ask_token_domain(project, ask, token):
            blockers.append(f"no project-backed ask filler exists for {label}")
    return tuple(dict.fromkeys(blockers))


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
                frames = reg.selectional_frames(verb.identity)
                if frames:
                    accepted = False
                    for _category, frame in frames:
                        if not set(roles_compatibility.roles) <= set(frame):
                            continue
                        frame_ok = True
                        for semantic_role, role_names in (
                            roles_compatibility.roles.items()
                        ):
                            role_category = frame[semantic_role]
                            for role_name in role_names:
                                role = value(role_name)
                                if role is None:
                                    continue
                                if (
                                    role_name
                                    in roles_compatibility.allow_proper_name
                                    and role.kind == "name"
                                ):
                                    continue
                                if (
                                    role_name
                                    in roles_compatibility.allow_plural_class
                                    and role.number == "plural"
                                ):
                                    continue
                                if not _filler_in_category(
                                    role, role_category, reg
                                ):
                                    frame_ok = False
                                    break
                            if not frame_ok:
                                break
                        if frame_ok:
                            accepted = True
                            break
                    if not accepted:
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

    return [
        AskAvailability(
            id=ask.id,
            consumer=(
                str(ask.resolves.get("consumer"))
                if ask.resolves.get("consumer") is not None
                else None
            ),
            supported=not (blockers := _ask_blockers(project, ask)),
            blockers=blockers,
        )
        for ask in project.registry.asks
    ]


def _optional_choices(
    tokens: list[MatchToken],
    rng: random.Random,
    forced_slots: set[str],
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
            include = bool(nested_slots & forced_slots) or bool(rng.randrange(2))
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
    optionals = _optional_choices(sequence, rng, set(locked_bindings))
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


def _generate_ask_surface(
    project: Project,
    ask: AskRule,
    *,
    seed: int,
    locked_bindings: dict[str, str],
    max_attempts: int,
) -> tuple[str, dict[str, str], dict[str, str], dict[str, Any], int]:
    blockers = _ask_blockers(project, ask)
    if blockers:
        raise GenerationError(f"{ask.id} is blocked: {'; '.join(blockers)}")
    rng = random.Random(seed)
    last_error: str | None = None
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
        reading = analyze(question, project.registry, tracing=True)
        matched = match_ask(reading, project.registry)
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
        return (
            question,
            requested,
            _match_bindings(match),
            _json_value(query),
            attempt,
        )
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
        options: list[list[tuple[str, str] | None]] = []
        score = 0
        for field, raw in emit.fields.items():
            expected = query_values.get(field)
            if expected is None:
                continue
            if isinstance(raw, str) and (match := _WHOLE_TEMPLATE.fullmatch(raw)):
                if match.group(2) is None:
                    options.append(
                        [(match.group(1), value) for value in expected]
                    )
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


def _solve_text(project: Project, premises: list[dict[str, Any]], question: str):
    text = " ".join(
        [*(premise["sentence"] for premise in premises), question]
    )
    return text, solve(text, project.registry)


def _try_solve_text(
    project: Project,
    premises: list[dict[str, Any]],
    question: str,
):
    """Treat a pathological generated combination as a failed search branch."""

    try:
        return _solve_text(project, premises, question)
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
) -> tuple[list[dict[str, Any]], Any, str]:
    selected = list(premises)
    changed = True
    while changed and len(selected) > 1:
        changed = False
        for index in range(len(selected)):
            trial = selected[:index] + selected[index + 1 :]
            solved = _try_solve_text(project, trial, question)
            if solved is None:
                continue
            text, result = solved
            if result.answer.committed:
                selected = trial
                changed = True
                break
    text, result = _solve_text(project, selected, question)
    return selected, result, text


def _premise_set_is_minimal(
    project: Project,
    premises: list[dict[str, Any]],
    question: str,
) -> bool:
    """Prove no generated premise can be removed while retaining an answer."""

    return all(
        (solved := _try_solve_text(
            project, premises[:index] + premises[index + 1 :], question
        )) is None
        or not solved[1].answer.committed
        for index in range(len(premises))
    )


def _search_answerable_scenario(
    project: Project,
    question: str,
    query: dict[str, Any],
    *,
    rng: random.Random,
    max_search_attempts: int,
) -> tuple[list[dict[str, Any]], Any, str, int]:
    ask_only = solve(question, project.registry)
    if ask_only.answer.committed:
        return [], ask_only, question, 0
    supported = {
        item.id
        for item in list_rule_availability(project)
        if item.supported
    }
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
    generated: list[dict[str, Any]] = []
    seen_sentences: set[str] = set()
    search_attempts = 0
    for _, _, _, rule_id, identity_locks in plans:
        if search_attempts >= max_search_attempts:
            break
        search_attempts += 1
        try:
            candidate = generate_candidate(
                project,
                rule_id=rule_id,
                seed=rng.getrandbits(63),
                max_attempts=_SCENARIO_PREMISE_ATTEMPTS,
                identity_bindings=identity_locks,
            ).to_json()
        except GenerationError:
            continue
        if candidate["sentence"] in seen_sentences:
            continue
        seen_sentences.add(candidate["sentence"])
        generated.append(candidate)
        solved = _try_solve_text(project, [candidate], question)
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
            solved = _try_solve_text(project, list(group), question)
            if solved is None:
                continue
            text, result = solved
            if not result.answer.committed:
                continue
            minimal, result, text = _minimal_committed_premises(
                project,
                list(group),
                question,
            )
            return minimal, result, text, search_attempts
    raise GenerationError(
        "no complete one-to-three-premise scenario was found from supported "
        f"generated rules after {search_attempts} deterministic checks"
    )


def generate_ask_scenario(
    project: Project,
    *,
    ask_id: str | None = None,
    seed: int | None = None,
    scenario_mode: AskScenarioMode = "ask_only",
    locked_bindings: dict[str, str] | None = None,
    max_attempts: int = 64,
    max_search_attempts: int = 48,
) -> AskScenarioCandidate:
    """Generate one exact ask and optionally its smallest found evidence set."""

    if scenario_mode not in {"ask_only", "answerable", "missing_evidence"}:
        raise GenerationError(f"unknown ask scenario mode {scenario_mode!r}")
    seed = secrets.randbits(63) if seed is None else seed
    rng = random.Random(seed)
    asks = {ask.id: ask for ask in project.registry.asks}
    availability = {
        item.id: item for item in list_ask_availability(project)
    }
    if ask_id is None:
        supported = [
            asks[item.id] for item in availability.values() if item.supported
        ]
        if not supported:
            raise GenerationError("this project has no supported ask surfaces")
        start = rng.randrange(len(supported))
        ordered = supported[start:] + supported[:start]
        ask_candidates = (
            ordered[:_MAX_RANDOM_ANSWERABLE_ASKS]
            if scenario_mode == "answerable"
            else ordered[:1]
        )
    else:
        ask = asks.get(ask_id)
        if ask is None:
            raise GenerationError(f"unknown ask rule {ask_id!r}")
        item = availability[ask.id]
        if not item.supported:
            raise GenerationError(
                f"{ask.id} is blocked: {'; '.join(item.blockers)}"
            )
        ask_candidates = [ask]

    last_error: Exception | None = None
    for ask in ask_candidates:
        try:
            question, requested, actual, query, attempts = _generate_ask_surface(
                project,
                ask,
                seed=seed,
                locked_bindings=dict(locked_bindings or {}),
                max_attempts=max_attempts,
            )
            ask_only = solve(question, project.registry)
            premises: list[dict[str, Any]] = []
            result = ask_only
            text = question
            search_attempts = 0
            if scenario_mode == "answerable":
                premises, result, text, search_attempts = (
                    _search_answerable_scenario(
                        project,
                        question,
                        query,
                        rng=rng,
                        max_search_attempts=max_search_attempts,
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
        except (GenerationError, ArithmeticError) as exc:
            last_error = exc
            if ask_id is not None or scenario_mode != "answerable":
                if isinstance(exc, GenerationError):
                    raise
                raise GenerationError(str(exc)) from exc
            continue

        answer, answer_shape = _answer_json(result.answer)
        digest = hashlib.sha256(
            (
                f"{project.registry.fingerprint}\0{scenario_mode}\0{seed}\0"
                f"{ask.id}\0{text}"
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
            minimal=_premise_set_is_minimal(project, premises, question),
            attempts=attempts,
            search_attempts=search_attempts,
        )

    raise GenerationError(
        "no answerable scenario was found for the first "
        f"{len(ask_candidates)} deterministic supported asks: "
        f"{last_error or 'no viable scenario'}"
    )
