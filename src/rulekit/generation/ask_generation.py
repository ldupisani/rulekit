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
    _leaf_tokens,
    _load_fixtures,
    _token_nodes,
    generate_candidate,
    list_rule_availability,
)

ASK_GENERATOR_VERSION = f"{GENERATOR_VERSION}+g7-asks"
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

    def realize(
        tokens: list[MatchToken],
        parent: tuple[int, ...] = (),
    ) -> None:
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

    realize(sequence)
    question = " ".join(surfaces)
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
    """Invert exact emit templates into premise slot locks.

    Only whole-slot templates can be inverted. Expressions and attributes
    stay unconstrained and the ordinary solver decides whether the resulting
    facts are sufficient.
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
            text, result = _solve_text(project, trial, question)
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
        not _solve_text(
            project,
            premises[:index] + premises[index + 1 :],
            question,
        )[1].answer.committed
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
        (score, rule.id, locks)
        for rule in project.registry.rules
        if rule.id in supported
        for score, locks in _emit_lock_variants(rule, query)
    ]
    plans.sort(key=lambda item: (-item[0], item[1], tuple(sorted(item[2].items()))))
    generated: list[dict[str, Any]] = []
    seen_sentences: set[str] = set()
    search_attempts = 0
    for _, rule_id, locks in plans:
        if search_attempts >= max_search_attempts:
            break
        search_attempts += 1
        try:
            candidate = generate_candidate(
                project,
                rule_id=rule_id,
                seed=rng.getrandbits(63),
                max_attempts=12,
                locked_bindings=locks,
            ).to_json()
        except GenerationError:
            continue
        if candidate["sentence"] in seen_sentences:
            continue
        seen_sentences.add(candidate["sentence"])
        generated.append(candidate)
        text, result = _solve_text(project, [candidate], question)
        if result.answer.committed:
            return [candidate], result, text, search_attempts

    # All-or-nothing series, combined totals, and other complete-group asks
    # may need several independently generated premises. Keep the search
    # bounded and deterministic; the ordinary solver remains the only oracle.
    pool = generated[:12]
    for size in (2, 3):
        for group in combinations(pool, size):
            search_attempts += 1
            text, result = _solve_text(project, list(group), question)
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
        ask = supported[rng.randrange(len(supported))]
    else:
        ask = asks.get(ask_id)
        if ask is None:
            raise GenerationError(f"unknown ask rule {ask_id!r}")
        item = availability[ask.id]
        if not item.supported:
            raise GenerationError(
                f"{ask.id} is blocked: {'; '.join(item.blockers)}"
            )

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
        premises, result, text, search_attempts = _search_answerable_scenario(
            project,
            question,
            query,
            rng=rng,
            max_search_attempts=max_search_attempts,
        )
        if not result.answer.committed:  # pragma: no cover - search enforces
            raise GenerationError("answerable scenario search returned no commitment")
    elif scenario_mode == "missing_evidence" and result.answer.committed:
        raise GenerationError(
            "the generated ask committed without premises, so it is not a "
            "missing-evidence scenario"
        )

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
