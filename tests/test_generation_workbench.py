"""Generation is deterministic, honest about blockers, and firewalled."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.generation import (
    AskScenarioReviewEvidence,
    ExplorationEvent,
    ExplorationFailure,
    ExplorationSelection,
    FactEvidence,
    GenerationError,
    LexicalRelaxation,
    PremiseAttachment,
    ReviewRecord,
    ReviewDefect,
    append_exploration,
    append_review,
    choose_exploration_target,
    delete_review,
    derive_hypotheses,
    exploration_status,
    exploration_failure_path,
    generate_candidate,
    generate_minimal_pair,
    list_rule_availability,
    promote_reading_candidate,
    promote_sentence_review_candidate,
    read_review_history,
    read_reviews,
    read_exploration_events,
    read_exploration_failures,
    retest_candidate,
    resolve_review,
    update_review,
)
from rulekit.generation.exploration import exploration_path
from rulekit.generation.reviews import _raw_reviews, review_path
from rulekit.kernel.engine import analyze
from rulekit.server.api import (
    DocBody,
    GenerationCandidateBody,
    GenerationHypothesisBody,
    GenerationMinimalPairBody,
    GenerationReadingBody,
    GenerationRetestBody,
    ServerState,
    TraceBody,
    build_router,
)


def _write_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir(parents=True)
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-generation
packs: [./pack]
"""
    )
    (root / "generation.yaml").write_text(
        """\
format: rulekit/generation@1
names: [Luma, Navo, Pera]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  "'s": {senses: [possessive]}
  dax: {senses: [verb]}
  jel: {senses: [adjective]}
  miv: {senses: [noun], plural: mivs}
  siv: {senses: [aggregate]}
  tev: {senses: [aggregate]}
  vem: {senses: [pronoun]}
  zor: {senses: [noun], plural: zors}
"""
    )
    (pack / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
categories:
  invented_action: {parent: verb}
  invented_pool: {parent: pronoun}
members:
  invented_action: [dax]
  invented_pool: [vem]
"""
    )
    (pack / "contractions.yaml").write_text(
        """\
format: rulekit/contractions@1
expansions:
  "'s": "'s"
"""
    )
    (pack / "numbers.yaml").write_text(
        """\
format: rulekit/numbers@1
numbers:
  nil: 0
  un: 1
  du: 2
fractions:
  tal: 0.5
  tals: 0.5
fraction_plurals:
  tals: tal
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/simple
    phase: read
    description: a flat invented premise
    match:
      sentence:
        - {slot: who, type: name}
        - {slot: verb, cat: invented_action}
        - {slot: item, type: noun}
    where:
      - distinct: [who, item]
    emits:
      - fact: predication
        subject: "{who}"
        verb: "{verb}"
        dobj: "{item}"

  - id: invented/condensed
    phase: read
    match:
      sentence:
        - {slot: quality, type: adjective}
        - {slot: item, type: noun}
    emits:
      - fact: predication
        subject: "{item}"
        verb: quality
        dobj: "{quality}"

  - id: invented/two_roles
    phase: read
    match:
      sentence:
        - {slot: left, type: noun}
        - {slot: right, type: noun}
    emits:
      - fact: predication
        subject: "{left}"
        verb: relates
        dobj: "{right}"

  - id: invented/plural
    phase: read
    match:
      sentence:
        - {slot: group, type: plural}
        - {lit: gather}
    emits:
      - fact: atom
        entity: "{group}"
        pred: gather

  - id: invented/plural_distinct
    phase: read
    match:
      sentence:
        - {slot: group, type: plural}
        - {slot: item, type: noun}
    where:
      - distinct: [group, item]
    emits:
      - fact: atom
        entity: "{group}"
        pred: "{item}"

  - id: invented/counted
    phase: read
    match:
      sentence:
        - {slot: item, type: counted}
    emits:
      - fact: atom
        entity: "{item}"
        pred: counted

  - id: invented/counted_distinct
    phase: read
    match:
      sentence:
        - {slot: group, type: counted}
        - {lit: near}
        - {slot: item, type: noun}
    where:
      - distinct: [group, item]
    emits:
      - fact: atom
        entity: "{group}"
        pred: "{item}"

  - id: invented/fraction
    phase: read
    match:
      sentence:
        - {slot: share, type: fraction}
    emits:
      - fact: atom
        entity: sample
        pred: "{share}"

  - id: invented/possessed
    phase: read
    match:
      sentence:
        - {slot: who, type: name}
        - {slot: verb, cat: invented_action}
        - {slot: asset, type: possessed}
    where:
      - distinct: [who, asset]
    emits:
      - fact: predication
        subject: "{who}"
        verb: "{verb}"
        dobj: "{asset}"

  - id: invented/pronoun
    phase: read
    match:
      sentence:
        - {slot: ref, type: pronoun}
    emits:
      - fact: atom
        entity: "{ref}"
        pred: declared

  - id: invented/pronoun_category
    phase: read
    match:
      sentence:
        - {slot: ref, cat: invented_pool}
    emits:
      - fact: atom
        entity: "{ref}"
        pred: categorized

  - id: invented/aggregate
    phase: read
    match:
      sentence:
        - {slot: marker, cat: aggregate}
    emits:
      - fact: atom
        entity: sample
        pred: "{marker}"

  - id: invented/span
    phase: read
    match:
      sentence:
        - {lit: vek}
        - {slot: phrase, span: true}
    emits:
      - fact: atom
        entity: sample
        pred: example
"""
    )


def test_same_seed_is_identical_across_fresh_project_loads(tmp_path: Path) -> None:
    _write_project(tmp_path)

    first = generate_candidate(
        load_project(tmp_path), rule_id="invented/simple", seed=8128
    )
    second = generate_candidate(
        load_project(tmp_path), rule_id="invented/simple", seed=8128
    )

    assert first.to_json() == second.to_json()
    assert first.target_status == "matched"
    assert first.target_rule in {
        match.rule_id for match in first.actual_matches
    }
    assert first.sentence.endswith(".")
    assert first.facts


def test_strict_round_trip_rejects_a_partial_requested_binding(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text().replace(
            "  jel: {senses: [adjective]}\n",
            (
                "  jel: {senses: [adjective]}\n"
                "  hand: {senses: [noun]}\n"
                "  hand-written: {senses: [noun]}\n"
            ),
        )
    )
    project = load_project(tmp_path)

    partial = generate_candidate(
        project,
        rule_id="invented/simple",
        seed=8128,
        max_attempts=1,
        locked_bindings={
            "who": "Luma",
            "verb": "dax",
            "item": "hand-written",
        },
    )
    complete = generate_candidate(
        project,
        rule_id="invented/simple",
        seed=8128,
        max_attempts=1,
        locked_bindings={
            "who": "Luma",
            "verb": "dax",
            "item": "hand",
        },
    )

    assert partial.target_status == "absent"
    assert partial.requested_bindings["item"] == "hand-written"
    assert any(
        match.rule_id == "invented/simple"
        for match in partial.actual_matches
    )
    assert "written" in " ".join(partial.deficiencies)
    assert complete.target_status == "matched"


def test_lexical_boundary_mode_widens_one_gate_without_claiming_a_match(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text().replace(
            "  dax: {senses: [verb]}\n",
            "  dax: {senses: [verb]}\n  nax: {senses: [verb]}\n",
        )
    )
    project = load_project(tmp_path)

    strict = generate_candidate(
        project,
        rule_id="invented/simple",
        seed=8128,
        generation_mode="strict",
    )
    boundary = generate_candidate(
        project,
        rule_id="invented/simple",
        seed=8128,
        generation_mode="lexical_boundary",
    )
    replay = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/simple",
        seed=8128,
        generation_mode="lexical_boundary",
    )

    assert strict.target_status == "matched"
    assert strict.requested_bindings["verb"] == "dax"
    assert strict.lexical_relaxations == ()
    assert boundary.to_json() == replay.to_json()
    assert boundary.generation_mode == "lexical_boundary"
    assert boundary.requested_bindings["verb"] == "nax"
    assert boundary.target_status == "absent"
    assert [item.slot for item in boundary.lexical_relaxations] == ["verb"]
    assert boundary.lexical_relaxations[0].requirement == (
        "category 'invented_action'"
    )
    relaxed = next(
        premise
        for premise in boundary.premises
        if premise.slot == "verb"
    )
    assert relaxed.status == "relaxed"
    assert "outside the strict category 'invented_action'" in relaxed.reason
    assert all(
        premise.status == "unverified"
        for premise in boundary.premises
        if premise.kind == "where"
    )


def test_boundary_mode_survives_retest_and_review_without_counting_coverage(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text().replace(
            "  dax: {senses: [verb]}\n",
            "  dax: {senses: [verb]}\n  nax: {senses: [verb]}\n",
        )
    )
    project = load_project(tmp_path)
    state = ServerState(tmp_path)
    router = build_router(state)
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/generation/candidate"
        and "POST" in route.methods
    )

    payload = endpoint(
        GenerationCandidateBody(
            rule_id="invented/simple",
            seed=8128,
            generation_mode="lexical_boundary",
        )
    )

    assert payload["target_status"] == "absent"
    assert payload["exploration_event_id"] is None
    assert payload["exploration_probe"] is None
    assert read_exploration_events(project) == []

    exploration_endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/generation/exploration"
        and "GET" in route.methods
    )
    compact_status = exploration_endpoint()
    assert compact_status["fillers"]
    assert all(
        "surfaces" not in filler and "placements" not in filler
        for filler in compact_status["fillers"]
    )

    relaxation = tuple(
        LexicalRelaxation(**item) for item in payload["lexical_relaxations"]
    )
    replay = retest_candidate(
        project,
        rule_id=payload["target_rule"],
        sentence=payload["sentence"],
        seed=payload["seed"],
        requested_bindings=payload["requested_bindings"],
        attempts=payload["attempts"],
        generation_mode="lexical_boundary",
        lexical_relaxations=relaxation,
    )
    assert replay.generation_mode == "lexical_boundary"
    assert replay.lexical_relaxations == relaxation
    review = append_review(
        project,
        ReviewRecord(
            candidate_id=replay.id,
            generation_mode=replay.generation_mode,
            lexical_relaxations=list(replay.lexical_relaxations),
            sentence=replay.sentence,
            target_rule=replay.target_rule,
            seed=replay.seed,
            registry_fingerprint=replay.registry_fingerprint,
            requested_bindings=replay.requested_bindings,
            verdict="unclear",
        ),
    )
    assert review["generation_mode"] == "lexical_boundary"
    assert review["lexical_relaxations"][0]["slot"] == "verb"


def test_gsm8k_generation_fixtures_make_every_premise_rule_available() -> None:
    availability = list_rule_availability(load_project(Path("projects/gsm8k")))

    assert len(availability) == 136
    blocked = {
        rule.id: rule for rule in availability if not rule.supported
    }
    assert set(blocked) == {
        "arithmetic/capacity-progress-anaphoric-multiplier-safety",
        "arithmetic/dangling-comparative-safety",
        "arithmetic/partition-membership-of-mass-measure-safety",
        "arithmetic/realized-progress-anaphoric-multiplier-safety",
        "arithmetic/realized-progress-deictic-anaphoric-multiplier-safety",
        "arithmetic/ratio-split-of-to-possession-safety",
    }
    assert blocked["arithmetic/dangling-comparative-safety"].blockers == (
        "declared non-generative safety consumer",
    )
    for rule_id in {
        "arithmetic/capacity-progress-anaphoric-multiplier-safety",
        "arithmetic/partition-membership-of-mass-measure-safety",
        "arithmetic/realized-progress-anaphoric-multiplier-safety",
        "arithmetic/realized-progress-deictic-anaphoric-multiplier-safety",
        "arithmetic/ratio-split-of-to-possession-safety",
    }:
        assert blocked[rule_id].blockers == (
            "declared non-generative safety consumer",
        )


def test_every_gsm8k_premise_rule_has_a_strict_round_trip() -> None:
    project = load_project(Path("projects/gsm8k"))
    availability = list_rule_availability(project)

    for index, rule in enumerate(
        item for item in availability if item.supported
    ):
        candidate = generate_candidate(
            project,
            rule_id=rule.id,
            seed=1000 + index,
        )
        assert candidate.target_status in {"matched", "shadowed"}, rule.id


def test_flat_currency_discount_realizes_as_one_symbolic_count() -> None:
    candidate = generate_candidate(
        load_project(Path("projects/curated")),
        rule_id="arithmetic/discount-flat-noun",
        seed=0,
    )

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings["amt"].startswith("$")
    assert " " not in candidate.requested_bindings["amt"]


def test_every_rule_is_listed_and_unsupported_rules_name_the_blocker(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    availability = {
        rule.id: rule
        for rule in list_rule_availability(load_project(tmp_path))
    }

    assert set(availability) == {
        "invented/simple",
        "invented/condensed",
        "invented/two_roles",
        "invented/plural",
        "invented/plural_distinct",
        "invented/counted",
        "invented/counted_distinct",
        "invented/fraction",
        "invented/possessed",
        "invented/pronoun",
        "invented/pronoun_category",
        "invented/aggregate",
        "invented/span",
    }
    assert availability["invented/simple"].supported
    assert availability["invented/condensed"].supported
    assert availability["invented/plural"].supported
    assert availability["invented/counted"].supported
    assert availability["invented/fraction"].supported
    assert availability["invented/possessed"].supported
    assert availability["invented/pronoun"].supported
    assert availability["invented/pronoun_category"].supported
    assert availability["invented/aggregate"].supported
    assert not availability["invented/span"].supported
    assert "span capture has no current realizer" in availability[
        "invented/span"
    ].blockers


def test_declared_plural_slots_are_reproducible_and_source_linked(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)

    first = generate_candidate(
        load_project(tmp_path), rule_id="invented/plural", seed=144
    )
    second = generate_candidate(
        load_project(tmp_path), rule_id="invented/plural", seed=144
    )

    assert first.to_json() == second.to_json()
    assert first.generator_version == "g6-strict-boundary-modes"
    assert first.target_status == "matched"
    assert first.requested_bindings["group"] in {"mivs", "zors"}
    premise = first.premises[0]
    assert premise.slot_type == "plural"
    assert {"lexicon", "morphology"} <= {
        source["kind"] for source in premise.sources
    }


def test_plural_support_does_not_widen_plain_noun_slots(tmp_path: Path) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    observed = {
        generate_candidate(
            project, rule_id="invented/two_roles", seed=seed
        ).requested_bindings["left"]
        for seed in range(16)
    }

    assert observed <= {"miv", "zor"}
    assert observed

    constrained = generate_candidate(
        project, rule_id="invented/plural_distinct", seed=31
    )
    plural = constrained.requested_bindings["group"]
    singular = constrained.requested_bindings["item"]
    assert project.registry.plural_to_singular[plural] != singular


def test_declared_counted_slots_compose_exact_number_noun_agreement(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    candidates = [
        generate_candidate(
            project, rule_id="invented/counted", seed=seed
        )
        for seed in range(64)
    ]

    assert {candidate.target_status for candidate in candidates} == {"matched"}
    assert {
        candidate.requested_bindings["item"] for candidate in candidates
    } <= {
        "0 mivs",
        "0 zors",
        "1 miv",
        "1 zor",
        "2 mivs",
        "2 zors",
    }
    zero = next(
        candidate
        for candidate in candidates
        if candidate.requested_bindings["item"].startswith("0 ")
    )
    singular = next(
        candidate
        for candidate in candidates
        if candidate.requested_bindings["item"].startswith("1 ")
    )
    plural = next(
        candidate
        for candidate in candidates
        if candidate.requested_bindings["item"].startswith("2 ")
    )
    singular_sources = {
        source["kind"] for source in singular.premises[0].sources
    }
    plural_sources = {
        source["kind"] for source in plural.premises[0].sources
    }
    assert {"rule-token", "number-numbers", "lexicon"} <= singular_sources
    assert "morphology" not in singular_sources
    assert "morphology" in plural_sources
    assert "morphology" in {
        source["kind"] for source in zero.premises[0].sources
    }
    assert "noun lemma" in plural.premises[0].reason


def test_counted_filler_identity_is_the_singular_noun_lemma(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    for seed in range(16):
        candidate = generate_candidate(
            project, rule_id="invented/counted_distinct", seed=seed
        )
        counted_head = candidate.requested_bindings["group"].split()[-1]
        counted_lemma = project.registry.plural_to_singular.get(
            counted_head, counted_head
        )
        assert counted_lemma != candidate.requested_bindings["item"]
        assert candidate.target_status == "matched"


def test_counted_domain_refuses_nouns_without_declared_plural_morphology(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text()
        .replace(", plural: mivs", "")
        .replace(", plural: zors", "")
    )

    availability = {
        rule.id: rule for rule in list_rule_availability(load_project(tmp_path))
    }
    assert not availability["invented/counted"].supported
    assert availability["invented/counted"].blockers == (
        "no project-backed filler exists for item",
    )


def test_counted_domain_refuses_declared_multiplication_marker_homographs(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    numbers = tmp_path / "pack" / "numbers.yaml"
    numbers.write_text(numbers.read_text() + 'operators:\n  zors: "*"\n')
    project = load_project(tmp_path)

    reading = analyze("2 zors", project.registry)
    assert len(reading.units) == 1
    assert reading.units[0].features["value_kind"] == "multiplier"

    with pytest.raises(
        GenerationError, match="constraints left no filler for item"
    ):
        generate_candidate(
            project,
            rule_id="invented/counted",
            seed=0,
            locked_bindings={"item": "2 zors"},
        )

    singular = generate_candidate(
        project,
        rule_id="invented/counted",
        seed=0,
        locked_bindings={"item": "1 zor"},
    )
    ordinary_plural = generate_candidate(
        project,
        rule_id="invented/counted",
        seed=0,
        locked_bindings={"item": "2 mivs"},
    )
    assert singular.target_status == "matched"
    assert ordinary_plural.target_status == "matched"


def test_fraction_slots_require_counts_for_declared_plural_forms(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    candidates = [
        generate_candidate(project, rule_id="invented/fraction", seed=seed)
        for seed in range(32)
    ]
    observed = {
        candidate.requested_bindings["share"] for candidate in candidates
    }

    assert observed == {"tal", "nil tals", "du tals"}
    assert "tals" not in observed
    assert "un tals" not in observed
    assert {candidate.target_status for candidate in candidates} == {"matched"}

    counted = generate_candidate(
        project,
        rule_id="invented/fraction",
        seed=41,
        locked_bindings={"share": "du tals"},
    )
    premise = counted.premises[0]
    assert "explicit count 2" in premise.reason
    assert "fraction lemma 'tal'" in premise.reason
    assert {
        "rule-token",
        "number-numbers",
        "number-fractions",
        "number-fraction_plurals",
    } <= {source["kind"] for source in premise.sources}

    with pytest.raises(
        GenerationError, match="constraints left no filler for share"
    ):
        generate_candidate(
            project,
            rule_id="invented/fraction",
            seed=41,
            locked_bindings={"share": "tals"},
        )


def test_fraction_plural_requirement_is_declarative(tmp_path: Path) -> None:
    _write_project(tmp_path)
    numbers = tmp_path / "pack" / "numbers.yaml"
    numbers.write_text(
        numbers.read_text().replace(
            "fraction_plurals:\n  tals: tal\n",
            "",
        )
    )

    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/fraction",
        seed=3,
        locked_bindings={"share": "tals"},
    )

    assert candidate.target_status == "matched"
    assert candidate.requested_bindings == {"share": "tals"}


def test_possessed_slots_compose_declared_owner_and_noun_sources(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidates = [
        generate_candidate(
            project, rule_id="invented/possessed", seed=seed
        )
        for seed in range(64)
    ]
    singular = next(
        candidate
        for candidate in candidates
        if candidate.requested_bindings["asset"].endswith(" miv")
    )
    plural = next(
        candidate
        for candidate in candidates
        if candidate.requested_bindings["asset"].endswith(" mivs")
    )
    replay = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/possessed",
        seed=singular.seed,
    )

    assert singular.to_json() == replay.to_json()
    assert singular.generator_version == "g6-strict-boundary-modes"
    assert singular.target_status == "matched"
    assert plural.target_status == "matched"
    singular_premise = next(
        premise
        for premise in singular.premises
        if premise.slot_type == "possessed"
    )
    plural_premise = next(
        premise
        for premise in plural.premises
        if premise.slot_type == "possessed"
    )
    assert {"generation-fixture", "contraction", "lexicon"} <= {
        source["kind"] for source in singular_premise.sources
    }
    assert "morphology" not in {
        source["kind"] for source in singular_premise.sources
    }
    assert "morphology" in {
        source["kind"] for source in plural_premise.sources
    }
    assert {"'s", "miv"} <= {
        source["label"] for source in singular_premise.sources
    }
    assert "owner" in singular_premise.reason
    assert "noun lemma 'miv'" in singular_premise.reason
    event = append_exploration(project, singular)
    possessed_filler = next(
        filler for filler in event["fillers"] if filler["slot"] == "asset"
    )
    assert possessed_filler["identity"] == "miv"
    assert possessed_filler["surface"] == singular.requested_bindings["asset"]
    assert all(
        filler["identity"].casefold() not in {"luma", "navo", "pera"}
        for filler in event["fillers"]
    )


def test_possessed_domain_requires_the_declared_possessive_token(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text().replace(
            '  "\'s": {senses: [possessive]}\n',
            "",
        )
    )

    availability = {
        rule.id: rule for rule in list_rule_availability(load_project(tmp_path))
    }
    assert not availability["invented/possessed"].supported
    assert availability["invented/possessed"].blockers == (
        "no project-backed filler exists for asset",
    )


def test_possessed_domain_requires_the_declared_contraction_split(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    contractions = tmp_path / "pack" / "contractions.yaml"
    contractions.write_text(
        contractions.read_text().replace(
            'expansions:\n  "\'s": "\'s"\n',
            "expansions: {}\n",
        )
    )

    availability = {
        rule.id: rule for rule in list_rule_availability(load_project(tmp_path))
    }
    assert not availability["invented/possessed"].supported
    assert availability["invented/possessed"].blockers == (
        "no project-backed filler exists for asset",
    )


def test_possessed_domain_round_trips_declared_invariant_plural(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text() + "  nul: {senses: [noun], plural: nul}\n"
    )
    project = load_project(tmp_path)

    candidate = generate_candidate(
        project,
        rule_id="invented/possessed",
        seed=610,
        locked_bindings={"asset": "Luma's nul"},
    )

    assert candidate.target_status == "matched"
    premise = next(
        item for item in candidate.premises if item.slot_type == "possessed"
    )
    assert "declared plural head morphology" in premise.reason
    assert "morphology" in {
        source["kind"] for source in premise.sources
    }
    event = append_exploration(project, candidate)
    filler = next(
        item for item in event["fillers"] if item["slot"] == "asset"
    )
    assert filler["identity"] == "nul"


def test_pronoun_slots_use_the_complete_declared_domain_and_sources(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    candidate = generate_candidate(
        project,
        rule_id="invented/pronoun",
        seed=747,
        locked_bindings={"ref": "vem"},
    )
    replay = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/pronoun",
        seed=747,
        locked_bindings={"ref": "vem"},
    )

    assert candidate.to_json() == replay.to_json()
    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status in {"matched", "shadowed"}
    assert candidate.requested_bindings == {"ref": "vem"}
    premise = candidate.premises[0]
    assert premise.slot_type == "pronoun"
    assert "committed sense 'pronoun'" in premise.reason
    assert {"rule-token", "lexicon"} <= {
        source["kind"] for source in premise.sources
    }
    assert "vem" in {source["label"] for source in premise.sources}
    event = append_exploration(project, candidate)
    assert event["fillers"] == [
        {
            "identity": "vem",
            "slot": "ref",
            "source": premise.sources[1],
            "surface": "vem",
            "token_index": 0,
        }
    ]


def test_pronoun_slots_block_when_the_project_declares_no_pronouns(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text().replace("  vem: {senses: [pronoun]}\n", "")
    )
    categories = tmp_path / "pack" / "categories.yaml"
    categories.write_text(
        categories.read_text().replace("  invented_pool: [vem]\n", "")
    )

    availability = {
        rule.id: rule for rule in list_rule_availability(load_project(tmp_path))
    }
    assert not availability["invented/pronoun"].supported
    assert availability["invented/pronoun"].blockers == (
        "no project-backed filler exists for ref",
    )


def test_pronoun_category_slots_use_membership_and_ancestry_sources(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    candidate = generate_candidate(
        project,
        rule_id="invented/pronoun_category",
        seed=991,
        locked_bindings={"ref": "vem"},
    )
    replay = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/pronoun_category",
        seed=991,
        locked_bindings={"ref": "vem"},
    )

    assert candidate.to_json() == replay.to_json()
    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    premise = candidate.premises[0]
    assert premise.slot_type == "invented_pool"
    assert premise.category_path == ("vem", "invented_pool", "pronoun")
    assert {"rule-token", "lexicon", "category-member", "category"} <= {
        source["kind"] for source in premise.sources
    }
    event = append_exploration(project, candidate)
    filler = next(item for item in event["fillers"] if item["slot"] == "ref")
    assert filler["identity"] == "vem"
    assert filler["surface"] == "vem"


def test_pronoun_category_slots_block_when_membership_is_empty(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    categories = tmp_path / "pack" / "categories.yaml"
    categories.write_text(
        categories.read_text().replace("  invented_pool: [vem]\n", "")
    )

    availability = {
        rule.id: rule for rule in list_rule_availability(load_project(tmp_path))
    }
    assert availability["invented/pronoun"].supported
    assert not availability["invented/pronoun_category"].supported
    assert availability["invented/pronoun_category"].blockers == (
        "no project-backed filler exists for ref",
    )


def test_aggregate_root_slots_use_the_complete_declared_domain_and_sources(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    for surface in ("siv", "tev"):
        candidate = generate_candidate(
            project,
            rule_id="invented/aggregate",
            seed=319,
            locked_bindings={"marker": surface},
        )
        replay = generate_candidate(
            load_project(tmp_path),
            rule_id="invented/aggregate",
            seed=319,
            locked_bindings={"marker": surface},
        )

        assert candidate.to_json() == replay.to_json()
        assert candidate.generator_version == "g6-strict-boundary-modes"
        assert candidate.target_status == "matched"
        assert candidate.requested_bindings == {"marker": surface}
        premise = candidate.premises[0]
        assert premise.slot_type == "aggregate"
        assert premise.category_path == (surface, "aggregate")
        assert {"rule-token", "lexicon"} <= {
            source["kind"] for source in premise.sources
        }
        assert "category-member" not in {
            source["kind"] for source in premise.sources
        }
        event = append_exploration(project, candidate)
        filler = next(
            item for item in event["fillers"] if item["slot"] == "marker"
        )
        assert filler["identity"] == surface
        assert filler["surface"] == surface


def test_aggregate_root_slots_block_when_the_lexicon_domain_is_empty(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    lexicon = tmp_path / "pack" / "lexicon.yaml"
    lexicon.write_text(
        lexicon.read_text()
        .replace("  siv: {senses: [aggregate]}\n", "")
        .replace("  tev: {senses: [aggregate]}\n", "")
        + '  "siv tev": {senses: [aggregate]}\n'
    )

    availability = {
        rule.id: rule for rule in list_rule_availability(load_project(tmp_path))
    }
    assert not availability["invented/aggregate"].supported
    assert availability["invented/aggregate"].blockers == (
        "no project-backed filler exists for marker",
    )


def test_g5b_unlocks_exactly_the_five_preregistered_curated_rules() -> None:
    availability = {
        rule.id: rule
        for rule in list_rule_availability(
            load_project(Path("projects/curated"))
        )
    }
    unlocked = {
        "arithmetic/group-total-leading",
        "arithmetic/group-total-of",
        "arithmetic/stated-age",
        "arithmetic/transfer-ditransitive",
        "arithmetic/transfer-prepositional",
    }

    assert all(availability[rule_id].supported for rule_id in unlocked)
    for rule_id in unlocked:
        candidate = generate_candidate(
            load_project(Path("projects/curated")),
            rule_id=rule_id,
            seed=8317,
        )
        assert candidate.target_status in {"matched", "shadowed"}
        counted = next(
            premise
            for premise in candidate.premises
            if premise.slot_type
            == (
                "age_measure"
                if rule_id == "arithmetic/stated-age"
                else "counted"
            )
        )
        assert {"rule-token", "number-numbers", "lexicon"} <= {
            source["kind"] for source in counted.sources
        }
        if rule_id == "arithmetic/stated-age":
            assert {"category-member", "category"} <= {
                source["kind"] for source in counted.sources
            }


def test_g5c_possessed_rules_remain_supported_after_g5j() -> None:
    project = load_project(Path("projects/curated"))
    availability = {
        rule.id: rule for rule in list_rule_availability(project)
    }

    assert availability[
        "arithmetic/times-as-many-possessive-standard"
    ].supported
    assert availability[
        "arithmetic/affine-times-as-many-possessive-standard"
    ].supported

    candidate = generate_candidate(
        project,
        rule_id="arithmetic/times-as-many-possessive-standard",
        seed=4181,
    )
    assert candidate.target_status in {"matched", "shadowed"}
    possessed = next(
        premise
        for premise in candidate.premises
        if premise.slot == "std"
    )
    assert {
        "rule-token",
        "generation-fixture",
        "contraction",
        "lexicon",
    } <= {
        source["kind"] for source in possessed.sources
    }


def test_g5d_unlocks_only_the_four_preregistered_partition_rules() -> None:
    project = load_project(Path("projects/curated"))
    availability = {
        rule.id: rule for rule in list_rule_availability(project)
    }
    migrated_pronouns = {
        "anything",
        "either",
        "everyone",
        "everything",
        "her",
        "herself",
        "him",
        "himself",
        "his",
        "its",
        "my",
        "ones",
        "their",
        "theirs",
        "them",
        "themselves",
        "you",
        "your",
    }
    unlocked = {
        "arithmetic/partition-attribute",
        "arithmetic/partition-attribute-fraction",
        "arithmetic/partition-membership",
        "arithmetic/partition-membership-fraction",
    }

    assert all(availability[rule_id].supported for rule_id in unlocked)
    assert availability[
        "arithmetic/times-as-many-possessive-kinship-standard"
    ].supported
    assert all(
        project.source_index.lexicon[surface].path
        == Path("packs/core-english/lexicon/core.yaml").resolve()
        for surface in migrated_pronouns
    )
    assert project.source_index.category_members[
        ("pool_pronoun", "them")
    ].path == Path("packs/core-english/categories/core.yaml").resolve()
    assert project.source_index.category_members[
        ("plural_object_pronoun", "them")
    ].path == Path("packs/core-english/categories/core.yaml").resolve()

    for rule_id in sorted(unlocked):
        candidate = generate_candidate(
            project,
            rule_id=rule_id,
            seed=901,
            locked_bindings={"coll": "them"},
        )
        assert candidate.target_status in {"matched", "shadowed"}
        assert candidate.requested_bindings["coll"] == "them"
        pronoun = next(
            premise
            for premise in candidate.premises
            if premise.slot_type == "plural_object_pronoun"
        )
        assert {"rule-token", "lexicon", "category-member", "category"} <= {
            source["kind"] for source in pronoun.sources
        }
        assert "them" in {source["label"] for source in pronoun.sources}
        assert any(
            source["path"].endswith(
                "packs/core-english/lexicon/core.yaml"
            )
            for source in pronoun.sources
            if source["label"] == "them"
        )


def test_g5e_unlocks_only_the_preregistered_pool_pronoun_rule() -> None:
    project = load_project(Path("projects/curated"))
    availability = {
        rule.id: rule for rule in list_rule_availability(project)
    }

    assert availability["arithmetic/fraction-of-pronoun"].supported

    for surface in ("it", "them"):
        candidate = generate_candidate(
            project,
            rule_id="arithmetic/fraction-of-pronoun",
            seed=173,
            locked_bindings={"ref": surface},
        )
        assert candidate.target_status in {"matched", "shadowed"}
        assert candidate.requested_bindings["ref"] == surface
        premise = next(
            item
            for item in candidate.premises
            if item.slot_type == "pool_pronoun"
        )
        assert premise.category_path == (
            surface,
            "pool_pronoun",
            "pronoun",
        )
        assert {
            "rule-token",
            "lexicon",
            "category-member",
            "category",
        } <= {source["kind"] for source in premise.sources}
        assert all(
            "packs/core-english/" in source["path"]
            for source in premise.sources
            if source["kind"] in {"lexicon", "category-member", "category"}
        )


def test_g5f_aggregate_boundary_remains_narrow_after_later_increments() -> None:
    project = load_project(Path("projects/curated"))
    availability = {
        rule.id: rule for rule in list_rule_availability(project)
    }

    assert availability["arithmetic/group-total-leading-marker"].supported
    assert availability["arithmetic/existential-premise-total"].supported
    assert availability["arithmetic/group-total-of-age"].supported
    assert availability["arithmetic/group-total-trailing"].supported

    members = {"altogether", "combined", "together", "total"}
    for surface in sorted(members):
        candidate = generate_candidate(
            project,
            rule_id="arithmetic/group-total-leading-marker",
            seed=517,
            locked_bindings={"agg": surface},
        )
        assert candidate.target_status in {"matched", "shadowed"}
        assert candidate.requested_bindings["agg"] == surface
        premise = next(
            item for item in candidate.premises
            if item.slot == "agg"
        )
        assert premise.slot_type == "group_total_marker"
        assert premise.category_path == (
            surface,
            "group_total_marker",
            "aggregate",
        )
        assert {"rule-token", "lexicon", "category-member", "category"} <= {
            source["kind"] for source in premise.sources
        }
        assert surface in {
            source["label"] for source in premise.sources
        }

    with pytest.raises(GenerationError, match="no filler for agg"):
        generate_candidate(
            project,
            rule_id="arithmetic/group-total-leading-marker",
            seed=517,
            locked_bindings={"agg": "average"},
        )

    meaningful = generate_candidate(
        project,
        rule_id="arithmetic/group-total-leading-marker",
        seed=517,
        locked_bindings={
            "agg": "together",
            "who": "they",
            "verb": "have",
            "item": "2 apples",
        },
    )
    assert meaningful.sentence == "Together they have 2 apples."
    assert meaningful.target_status in {"matched", "shadowed"}


def test_reviewed_bare_fraction_plural_is_absent_but_counted_form_matches() -> None:
    project = load_project(Path("projects/curated"))
    rule_id = "arithmetic/fraction-of-pool"

    invalid = retest_candidate(
        project,
        rule_id=rule_id,
        sentence="Dena had eighths of the plum.",
        seed=2814696225159466,
        requested_bindings={
            "f": "eighths",
            "item": "plum",
            "verb": "had",
            "who": "Dena",
        },
    )
    valid = retest_candidate(
        project,
        rule_id=rule_id,
        sentence="Dena had two eighths of the plum.",
        seed=2814696225159466,
    )

    assert invalid.target_status == "absent"
    assert valid.target_status in {"matched", "shadowed"}
    assert valid.target_bindings["f"] == "two eighths"
    premise = next(
        item for item in valid.premises if item.slot_type == "fraction"
    )
    assert "explicit count 2" in premise.reason
    assert {
        "number-numbers",
        "number-fractions",
        "number-fraction_plurals",
    } <= {source["kind"] for source in premise.sources}


def test_failed_round_trip_remains_an_inspectable_candidate(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)

    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/condensed",
        seed=3,
        max_attempts=2,
    )

    assert candidate.sentence == "Jel zor."
    assert candidate.target_status == "absent"
    assert candidate.target_bindings == {}
    assert candidate.attempts == 2
    assert candidate.target_specificity is None
    assert candidate.premises
    assert {premise.status for premise in candidate.premises} == {"unverified"}


def test_source_index_retains_exact_pack_declaration_locations(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    source = project.source_index

    refs = (
        source.rules["invented/simple"],
        source.rule_tokens[("invented/simple", 1)],
        source.rule_where[("invented/simple", 0)],
        source.lexicon["dax"],
        source.morphology[("miv", "plural")],
        source.contractions["'s"],
        source.categories["invented_action"],
        source.category_members[("invented_action", "dax")],
        source.numeric[("numbers", "un")],
    )
    for ref in refs:
        line = ref.path.read_text().splitlines()[ref.line - 1]
        assert line.strip()
        assert ref.column >= 1

    assert "invented/simple" in refs[0].path.read_text().splitlines()[
        refs[0].line - 1
    ]
    assert "slot: verb" in refs[1].path.read_text().splitlines()[
        refs[1].line - 1
    ]
    assert "distinct:" in refs[2].path.read_text().splitlines()[
        refs[2].line - 1
    ]


def test_matched_candidate_explains_each_premise_with_sources(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path), rule_id="invented/simple", seed=8128
    )

    assert candidate.target_specificity is not None
    assert candidate.target_source
    assert candidate.target_source["kind"] == "rule"
    assert len(candidate.premises) == 4
    assert {premise.status for premise in candidate.premises} == {"passed"}
    assert candidate.premises[-1].expression == "distinct(who, item)"
    assert candidate.premises[-1].kind == "where"
    assert candidate.premises[-1].sources[0]["kind"] == "rule-where"

    category = candidate.premises[1]
    assert category.category_path == ("dax", "invented_action", "verb")
    assert {"rule-token", "lexicon", "category-member", "category"} <= {
        source["kind"] for source in category.sources
    }
    assert any(
        source["kind"] == "generation-fixture"
        for source in candidate.premises[0].sources
    )
    assert {unit.uid for unit in candidate.consumed_units} == set(
        candidate.actual_matches[0].consumed
    )
    assert candidate.actual_matches[0].consumed_surfaces


def test_retest_replays_the_identical_candidate_without_resampling(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    before = generate_candidate(
        project, rule_id="invented/simple", seed=8128
    )

    after = retest_candidate(
        load_project(tmp_path),
        rule_id=before.target_rule,
        sentence=before.sentence,
        seed=before.seed,
        requested_bindings=before.requested_bindings,
        attempts=before.attempts,
    )

    assert after.to_json() == before.to_json()


def test_reading_sentence_is_promoted_without_realization_or_rewriting(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    sentence = "Luma dax miv."

    first = promote_reading_candidate(
        load_project(tmp_path),
        rule_id="invented/simple",
        sentence=sentence,
    )
    second = promote_reading_candidate(
        load_project(tmp_path),
        rule_id="invented/simple",
        sentence=sentence,
    )

    assert first.to_json() == second.to_json()
    assert first.origin == "reading"
    assert first.sentence == sentence
    assert first.target_status == "matched"
    assert first.requested_bindings == first.target_bindings
    assert first.attempts == 1
    assert 0 <= first.seed <= (1 << 53) - 1


def test_unmatched_reading_sentence_becomes_a_targetless_interpretation_review(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    sentence = "Miv."

    first = promote_sentence_review_candidate(project, sentence=sentence)
    second = promote_sentence_review_candidate(
        load_project(tmp_path), sentence=sentence
    )

    assert first.to_json() == second.to_json()
    assert first.origin == "reading"
    assert first.sentence == sentence
    assert first.target_rule is None
    assert first.target_status == "unmatched"
    assert first.actual_matches == ()
    assert first.premises == ()

    review = append_review(
        project,
        ReviewRecord(
            candidate_id=first.id,
            origin="reading",
            review_kind="sentence",
            sentence=first.sentence,
            target_rule=None,
            seed=first.seed,
            registry_fingerprint=first.registry_fingerprint,
            verdict="valid",
            interpretation="A single entity is being named.",
            suggested_rule="Recognize a bare nominal utterance.",
        ),
    )
    assert review["target_rule"] is None
    assert review["interpretation"] == "A single entity is being named."
    assert review["suggested_rule"] == "Recognize a bare nominal utterance."

    status = exploration_status(project)
    assert status["summary"]["live_reviews"] == 1
    assert all(item["reviewed_count"] == 0 for item in status["rules"])


def test_sentence_review_cannot_claim_a_target_or_generated_origin() -> None:
    common = {
        "candidate_id": "gen-targetless",
        "review_kind": "sentence",
        "sentence": "A sentence.",
        "seed": 1,
        "registry_fingerprint": "abcdef0123456789",
        "verdict": "unclear",
    }
    with pytest.raises(ValidationError):
        ReviewRecord.model_validate(
            {**common, "origin": "reading", "target_rule": "invented/simple"}
        )
    with pytest.raises(ValidationError):
        ReviewRecord.model_validate(
            {**common, "origin": "generated", "target_rule": None}
        )


def test_minimal_pair_rerolls_one_slot_and_locks_every_other_binding(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    before = generate_candidate(
        project, rule_id="invented/simple", seed=8128
    )

    first = generate_minimal_pair(
        project,
        rule_id=before.target_rule,
        base_seed=before.seed,
        original_bindings=before.requested_bindings,
        reroll_slot="who",
    )
    replay = generate_minimal_pair(
        load_project(tmp_path),
        rule_id=before.target_rule,
        base_seed=before.seed,
        original_bindings=before.requested_bindings,
        reroll_slot="who",
    )

    assert first.to_json() == replay.to_json()
    assert first.sentence != before.sentence
    assert first.requested_bindings["who"] != before.requested_bindings["who"]
    assert {
        slot: surface
        for slot, surface in first.requested_bindings.items()
        if slot != "who"
    } == {
        slot: surface
        for slot, surface in before.requested_bindings.items()
        if slot != "who"
    }


def test_minimal_pair_fails_honestly_when_a_slot_has_no_alternative(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    before = generate_candidate(
        project, rule_id="invented/simple", seed=8128
    )

    with pytest.raises(
        ValueError, match="slot 'verb' has no project-backed alternative"
    ):
        generate_minimal_pair(
            project,
            rule_id=before.target_rule,
            base_seed=before.seed,
            original_bindings=before.requested_bindings,
            reroll_slot="verb",
        )


def test_category_defect_produces_a_deterministic_source_linked_hypothesis(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path), rule_id="invented/simple", seed=8128
    )
    defect = ReviewDefect(
        kind="wrong_category_membership",
        attachment=PremiseAttachment(kind="token", index=1),
    )

    first = derive_hypotheses(
        candidate, verdict="invalid", defects=[defect]
    )
    second = derive_hypotheses(
        candidate, verdict="invalid", defects=[defect]
    )

    assert first == second
    assert [hypothesis.kind for hypothesis in first] == [
        "category_gate_too_broad"
    ]
    assert first[0].premise == defect.attachment
    assert {"rule-token", "lexicon", "category-member", "category"} <= {
        source.kind for source in first[0].sources
    }


def test_fact_defect_keeps_the_exact_snapshot_and_forms_a_rule_hypothesis(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project, rule_id="invented/simple", seed=8128
    )
    fact = FactEvidence.model_validate(candidate.facts[0])
    defect = ReviewDefect(
        kind="missing_fact_context",
        attachment=PremiseAttachment(kind="fact", index=0),
        fact=fact,
    )

    hypotheses = derive_hypotheses(
        candidate, verdict="invalid", defects=[defect]
    )
    durable = append_review(
        project,
        ReviewRecord(
            candidate_id=candidate.id,
            sentence=candidate.sentence,
            target_rule=candidate.target_rule,
            seed=candidate.seed,
            registry_fingerprint=candidate.registry_fingerprint,
            verdict="invalid",
            defects=[defect],
            hypotheses=list(hypotheses),
        ),
    )

    assert fact.source_ref is not None
    assert fact.source_ref.kind == "rule"
    assert [hypothesis.kind for hypothesis in hypotheses] == [
        "fact_context_boundary"
    ]
    assert hypotheses[0].premise == defect.attachment
    assert hypotheses[0].sources[0] == fact.source_ref
    assert "identity, qualifier, role, time" in hypotheses[0].claim
    assert durable["defects"][0]["attachment"] == {
        "kind": "fact",
        "index": 0,
    }
    assert durable["defects"][0]["fact"] == fact.model_dump()


def test_fact_defects_require_an_exact_fact_attachment() -> None:
    with pytest.raises(
        ValidationError, match="fact defect must be attached to an emitted fact"
    ):
        ReviewDefect(
            kind="missing_fact_context",
            attachment=PremiseAttachment(kind="sentence"),
        )

    with pytest.raises(
        ValidationError, match="fact attachment requires the emitted fact snapshot"
    ):
        ReviewDefect(
            kind="other",
            attachment=PremiseAttachment(kind="fact", index=0),
        )


def test_missing_constraint_hypothesis_requires_duplicate_slot_evidence(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = next(
        generated
        for seed in range(32)
        if len(
            set(
                (
                    generated := generate_candidate(
                        project,
                        rule_id="invented/two_roles",
                        seed=seed,
                    )
                ).requested_bindings.values()
            )
        )
        == 1
    )
    defect = ReviewDefect(
        kind="missing_cross_slot_constraint",
        attachment=PremiseAttachment(kind="rule", index=0),
    )

    hypotheses = derive_hypotheses(
        candidate, verdict="invalid", defects=[defect]
    )

    assert [hypothesis.kind for hypothesis in hypotheses] == [
        "missing_distinct_predicate"
    ]
    assert "left, right" in hypotheses[0].claim


def test_unsupported_defect_says_no_mechanical_hypothesis(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path), rule_id="invented/simple", seed=8128
    )

    assert derive_hypotheses(
        candidate,
        verdict="invalid",
        defects=[
            ReviewDefect(
                kind="sentence_ungrammatical",
                attachment=PremiseAttachment(kind="sentence"),
            )
        ],
    ) == ()


def test_save_then_retest_reports_the_changed_behavior_on_the_same_sentence(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    state = ServerState(tmp_path)
    router = build_router(state)

    def endpoint(path: str, method: str):
        return next(
            route.endpoint
            for route in router.routes
            if route.path == path and method in route.methods
        )

    before = endpoint("/api/generation/candidate", "POST")(
        GenerationCandidateBody(rule_id="invented/simple", seed=8128)
    )
    assert before["target_status"] == "matched"

    rule_doc = tmp_path / "pack" / "rules.yaml"
    content = rule_doc.read_text()
    changed = content.replace(
        "{slot: verb, cat: invented_action}",
        "{slot: verb, type: adjective}",
        1,
    )
    saved = endpoint("/api/doc", "PUT")(
        DocBody(path=str(rule_doc), content=changed)
    )
    assert saved["ok"]

    after = endpoint("/api/generation/retest", "POST")(
        GenerationRetestBody(
            rule_id=before["target_rule"],
            sentence=before["sentence"],
            seed=before["seed"],
            requested_bindings=before["requested_bindings"],
            attempts=before["attempts"],
        )
    )
    assert after["sentence"] == before["sentence"]
    assert after["seed"] == before["seed"]
    assert after["registry_fingerprint"] != before["registry_fingerprint"]
    assert after["target_status"] == "absent"
    assert {premise["status"] for premise in after["premises"]} == {
        "unverified"
    }

    with pytest.raises(ValidationError):
        GenerationRetestBody.model_validate(
            {
                "rule_id": before["target_rule"],
                "sentence": before["sentence"],
                "seed": before["seed"],
                "path": str(tmp_path / "not-authorized.yaml"),
            }
        )


def test_trace_exposes_explicit_targets_and_promotes_the_selected_rule(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    router = build_router(ServerState(tmp_path))

    def endpoint(path: str, method: str):
        return next(
            route.endpoint
            for route in router.routes
            if route.path == path and method in route.methods
        )

    sentence = "Luma dax miv."
    trace = endpoint("/api/trace", "POST")(TraceBody(text=sentence))
    targets = trace["sentences"][0]["review_targets"]
    assert [
        {
            key: value
            for key, value in target.items()
            if key != "source_ref"
        }
        for target in targets
    ] == [
        {
            "rule_id": "invented/simple",
            "description": "a flat invented premise",
            "status": "matched",
        }
    ]
    rule_path = (tmp_path / "pack" / "rules.yaml").resolve()
    assert targets[0]["source_ref"]["path"] == str(rule_path)
    assert targets[0]["source_ref"]["kind"] == "rule"
    fact = next(
        fact for fact in trace["facts"] if fact["source"] == "invented/simple"
    )
    assert fact["source_ref"] == targets[0]["source_ref"]
    decision = next(
        decision
        for decision in trace["sentences"][0]["decisions"]
        if decision.get("rule_id") == "invented/simple"
    )
    assert decision["source_ref"] == targets[0]["source_ref"]
    semantic_fact = next(
        fact
        for fact in trace["semantic"]["facts"]
        if fact["source"] == "invented/simple"
    )
    assert semantic_fact["source_ref"] == targets[0]["source_ref"]

    candidate = endpoint("/api/generation/from-reading", "POST")(
        GenerationReadingBody(
            rule_id=targets[0]["rule_id"],
            sentence=sentence,
        )
    )
    assert candidate["origin"] == "reading"
    assert candidate["sentence"] == sentence
    assert candidate["target_rule"] == targets[0]["rule_id"]
    assert candidate["requested_bindings"] == candidate["target_bindings"]
    assert candidate["target_source"] == targets[0]["source_ref"]


def test_trace_can_promote_a_sentence_without_selecting_a_rule(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    router = build_router(ServerState(tmp_path))

    def endpoint(path: str, method: str):
        return next(
            route.endpoint
            for route in router.routes
            if route.path == path and method in route.methods
        )

    sentence = "Miv."
    trace = endpoint("/api/trace", "POST")(TraceBody(text=sentence))
    assert trace["sentences"][0]["review_targets"] == []

    candidate = endpoint("/api/generation/from-reading", "POST")(
        GenerationReadingBody(sentence=sentence)
    )
    assert candidate["origin"] == "reading"
    assert candidate["sentence"] == sentence
    assert candidate["target_rule"] is None
    assert candidate["target_status"] == "unmatched"
    assert candidate["actual_rule_ids"] == []


def test_trace_exposes_the_identified_ask_source() -> None:
    router = build_router(ServerState(Path("projects/curated")))
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/trace" and "POST" in route.methods
    )

    trace = endpoint(
        TraceBody(
            text=(
                "Aven has 2 apples. "
                "How many apples does Aven have?"
            )
        )
    )

    assert trace["ask"]["id"] == "ask/how-many-entity"
    assert trace["ask"]["source_ref"]["kind"] == "ask"
    assert trace["ask"]["source_ref"]["label"] == "ask/how-many-entity"
    assert trace["ask"]["source_ref"]["path"].endswith(
        "/packs/arithmetic/rules/core.yaml"
    )


def test_hypothesis_and_minimal_pair_routes_recompute_project_evidence(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    state = ServerState(tmp_path)
    router = build_router(state)

    def endpoint(path: str, method: str):
        return next(
            route.endpoint
            for route in router.routes
            if route.path == path and method in route.methods
        )

    before = endpoint("/api/generation/candidate", "POST")(
        GenerationCandidateBody(rule_id="invented/simple", seed=8128)
    )
    defect = ReviewDefect(
        kind="wrong_category_membership",
        attachment=PremiseAttachment(kind="token", index=1),
    )
    proposed = endpoint("/api/generation/hypotheses", "POST")(
        GenerationHypothesisBody(
            rule_id=before["target_rule"],
            sentence=before["sentence"],
            seed=before["seed"],
            requested_bindings=before["requested_bindings"],
            attempts=before["attempts"],
            verdict="invalid",
            defects=[defect],
        )
    )
    unsupported = endpoint("/api/generation/hypotheses", "POST")(
        GenerationHypothesisBody(
            rule_id=before["target_rule"],
            sentence=before["sentence"],
            seed=before["seed"],
            requested_bindings=before["requested_bindings"],
            attempts=before["attempts"],
            verdict="invalid",
            defects=[
                ReviewDefect(
                    kind="sentence_ungrammatical",
                    attachment=PremiseAttachment(kind="sentence"),
                )
            ],
        )
    )
    paired = endpoint("/api/generation/minimal-pair", "POST")(
        GenerationMinimalPairBody(
            rule_id=before["target_rule"],
            base_seed=before["seed"],
            original_bindings=before["requested_bindings"],
            reroll_slot="who",
        )
    )

    assert proposed["candidate"]["sentence"] == before["sentence"]
    assert proposed["hypotheses"][0]["kind"] == "category_gate_too_broad"
    assert proposed["detail"] is None
    assert unsupported["hypotheses"] == []
    assert unsupported["detail"].startswith(
        "No mechanical hypothesis is available"
    )
    assert paired["reroll_slot"] == "who"
    assert paired["candidate"]["requested_bindings"]["who"] != (
        before["requested_bindings"]["who"]
    )
    assert paired["locked_bindings"] == {
        slot: surface
        for slot, surface in before["requested_bindings"].items()
        if slot != "who"
    }


def test_seeded_random_rule_selection_is_reproducible(tmp_path: Path) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    assert generate_candidate(project, seed=21).to_json() == generate_candidate(
        load_project(tmp_path), seed=21
    ).to_json()


def test_exploration_status_distinguishes_generation_from_human_review(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    selection = choose_exploration_target(
        project,
        rule_id="invented/simple",
        filler_identity="miv",
        seed=31,
    )
    candidate = generate_candidate(
        project,
        rule_id=selection.rule_id,
        seed=31,
        locked_bindings=selection.locked_bindings,
    )

    event = append_exploration(project, candidate)
    generated = exploration_status(project)
    rule = next(
        item for item in generated["rules"] if item["id"] == "invented/simple"
    )
    filler = next(
        item for item in generated["fillers"] if item["identity"] == "miv"
    )

    assert event["candidate_id"] == candidate.id
    assert candidate.requested_bindings["item"] == "miv"
    assert rule["status"] == "generated_unreviewed"
    assert rule["generated_count"] == 1
    assert rule["reviewed_count"] == 0
    assert filler["status"] == "generated_unreviewed"
    assert filler["generated_count"] == 1
    assert filler["reviewed_count"] == 0
    assert filler["source"]["kind"] == "lexicon"
    assert "invented/simple" in filler["compatible_rules"]

    review = append_review(project, _review(candidate, "valid"))
    reviewed = exploration_status(project)
    rule = next(
        item for item in reviewed["rules"] if item["id"] == "invented/simple"
    )
    filler = next(
        item for item in reviewed["fillers"] if item["identity"] == "miv"
    )

    assert rule["status"] == "reviewed"
    assert rule["verdict_counts"] == {
        "valid": 1,
        "invalid": 0,
        "unclear": 0,
    }
    assert filler["status"] == "reviewed"
    assert filler["reviewed_count"] == 1

    corrected = update_review(
        project, review["id"], "unclear", "needs another look"
    )
    corrected_status = exploration_status(project)
    corrected_rule = next(
        item
        for item in corrected_status["rules"]
        if item["id"] == "invented/simple"
    )
    assert corrected_rule["reviewed_count"] == 1
    assert corrected_rule["verdict_counts"]["valid"] == 0
    assert corrected_rule["verdict_counts"]["unclear"] == 1

    delete_review(project, corrected["id"])
    deleted_status = exploration_status(project)
    deleted_rule = next(
        item
        for item in deleted_status["rules"]
        if item["id"] == "invented/simple"
    )
    deleted_filler = next(
        item
        for item in deleted_status["fillers"]
        if item["identity"] == "miv"
    )
    assert deleted_rule["status"] == "generated_unreviewed"
    assert deleted_filler["status"] == "generated_unreviewed"


def test_pre_g6_review_does_not_invent_filler_history(tmp_path: Path) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project, rule_id="invented/simple", seed=5
    )
    append_review(project, _review(candidate, "valid"))

    status = exploration_status(project)
    rule = next(
        item for item in status["rules"] if item["id"] == "invented/simple"
    )

    assert rule["status"] == "reviewed"
    assert rule["generated_count"] == 0
    assert all(item["reviewed_count"] == 0 for item in status["fillers"])
    assert not exploration_path(project).exists()


def test_least_explored_selection_is_seeded_and_probe_compatible(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    first = choose_exploration_target(project, seed=144)
    replay = choose_exploration_target(
        load_project(tmp_path), seed=144
    )
    assert first == replay
    assert first.probe is not None

    selected = choose_exploration_target(
        project,
        rule_id="invented/simple",
        filler_identity="miv",
        seed=55,
    )
    assert selected.rule_id == "invented/simple"
    assert selected.probe["identity"] == "miv"
    assert selected.locked_bindings == {"item": "miv"}

    with pytest.raises(
        ValueError,
        match="cannot fill a supported slot in invented/condensed",
    ):
        choose_exploration_target(
            project,
            rule_id="invented/condensed",
            filler_identity="dax",
            seed=55,
        )

    curated = load_project(Path("projects/curated"))
    curated_fillers = {
        item["identity"]: item
        for item in exploration_status(curated)["fillers"]
    }
    excluded_rule = "arithmetic/affine-fraction-as-many"
    for identity in ("need", "take", "want"):
        assert excluded_rule not in curated_fillers[identity]["compatible_rules"]
        assert all(
            placement["rule_id"] != excluded_rule
            for placement in curated_fillers[identity]["placements"]
        )
        with pytest.raises(
            ValueError,
            match=f"cannot fill a supported slot in {excluded_rule}",
        ):
            choose_exploration_target(
                curated,
                rule_id=excluded_rule,
                filler_identity=identity,
                seed=55,
            )


def test_structural_coverage_targets_filters_and_health_are_explicit(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    rules_path = tmp_path / "pack" / "rules.yaml"
    rules_path.write_text(
        rules_path.read_text()
        + """\

  - id: invented/structural
    phase: read
    match:
      sentence:
        - {slot: who, type: name}
        - {lit: [dax, vax]}
        - {slot: item, type: noun}
        - opt:
            - {slot: extra, type: noun}
    emits:
      - fact: atom
        entity: "{who}"
        pred: "{item}"
"""
    )
    project = load_project(tmp_path)

    status = exploration_status(project)
    profile = next(
        item for item in status["rules"] if item["id"] == "invented/structural"
    )
    assert profile["profile"]["phenomena"] == [
        "literal_alternatives",
        "optional_branches",
    ]
    assert profile["profile"]["fact_types"] == ["atom"]
    assert profile["structural_total"] == 5
    assert profile["structural_covered"] == 0
    assert "optional_branches" in status["filter_options"]["phenomena"]

    selection = choose_exploration_target(
        project,
        seed=41,
        objective="least_covered_structure",
        filters=("phenomenon:optional_branches", "fact:atom"),
    )
    assert selection.rule_id == "invented/structural"
    assert selection.target_signature in profile["uncovered_signatures"]
    assert selection.filters == (
        "fact:atom",
        "phenomenon:optional_branches",
    )

    included = generate_candidate(
        project,
        rule_id="invented/structural",
        seed=42,
        structural_target="optional:3:included",
    )
    event = append_exploration(
        project,
        included,
        ExplorationSelection(
            rule_id="invented/structural",
            locked_bindings={},
            probe=None,
            objective="least_covered_structure",
            filters=("phenomenon:optional_branches",),
            target_signature="optional:3:included",
        ),
    )
    assert "optional:3:included" in event["structural_signatures"]
    assert "fact:atom(entity,pred)" in event["structural_signatures"]
    assert event["objective"] == "least_covered_structure"

    omitted = generate_candidate(
        project,
        rule_id="invented/structural",
        seed=43,
        structural_target="optional:3:omitted",
    )
    omitted_event = append_exploration(project, omitted)
    assert "optional:3:omitted" in omitted_event["structural_signatures"]

    alternative = generate_candidate(
        project,
        rule_id="invented/structural",
        seed=44,
        structural_target="literal:1:vax",
    )
    alternative_event = append_exploration(project, alternative)
    assert "literal:1:vax" in alternative_event["structural_signatures"]

    revised = exploration_status(load_project(tmp_path))
    revised_rule = next(
        item for item in revised["rules"] if item["id"] == "invented/structural"
    )
    assert revised_rule["structural_covered"] == 5
    assert revised["health"]["structural_covered"] >= 5
    assert revised["health"]["current_structural_events"] == 3

    with pytest.raises(GenerationError, match="unknown or currently unreachable"):
        choose_exploration_target(
            project,
            seed=45,
            filters=("phenomenon:not_declared",),
        )


def test_review_attention_objective_selects_a_live_problem_rule(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project, rule_id="invented/simple", seed=52
    )
    append_review(project, _review(candidate, "invalid"))

    selection = choose_exploration_target(
        project,
        seed=53,
        objective="review_attention",
    )
    assert selection.rule_id == "invented/simple"
    assert selection.objective == "review_attention"


def test_generation_api_records_only_fresh_realizations(tmp_path: Path) -> None:
    _write_project(tmp_path)
    rules_path = tmp_path / "pack" / "rules.yaml"
    rules_path.write_text(
        rules_path.read_text()
        + """\

  - id: invented/impossible-same
    phase: read
    match:
      sentence:
        - {slot: verb, cat: invented_action}
        - {slot: item, type: noun}
    where:
      - same_lemma: [verb, item]
    emits:
      - fact: atom
        entity: "{item}"
        pred: "{verb}"
"""
    )
    router = build_router(ServerState(tmp_path))

    def endpoint(path: str, method: str):
        return next(
            route.endpoint
            for route in router.routes
            if route.path == path and method in route.methods
        )

    project = load_project(tmp_path)
    first_selection = choose_exploration_target(
        project,
        rule_id="invented/impossible-same",
        seed=8128,
    )
    with pytest.raises(HTTPException, match="could not realize"):
        endpoint("/api/generation/candidate", "POST")(
            GenerationCandidateBody(
                rule_id="invented/impossible-same",
                seed=8128,
            )
        )

    failures = read_exploration_failures(load_project(tmp_path))
    assert len(failures) == 1
    assert failures[0]["id"].startswith("fail-")
    assert failures[0]["rule_id"] == "invented/impossible-same"
    assert failures[0]["probe"]["identity"] == first_selection.probe["identity"]
    assert exploration_failure_path(project).exists()
    assert not exploration_path(project).exists()

    attempted = exploration_status(load_project(tmp_path))
    attempted_rule = next(
        item
        for item in attempted["rules"]
        if item["id"] == "invented/impossible-same"
    )
    attempted_filler = next(
        item
        for item in attempted["fillers"]
        if item["identity"] == first_selection.probe["identity"]
    )
    assert attempted_rule["status"] == "attempted_failed"
    assert attempted_rule["generated_count"] == 0
    assert attempted_rule["failed_count"] == 1
    assert attempted_rule["attempt_count"] == 1
    assert attempted_filler["status"] == "attempted_failed"
    assert attempted_filler["generated_count"] == 0
    assert attempted_filler["failed_count"] == 1
    assert attempted_filler["attempt_count"] == 1
    assert attempted["health"]["failed_attempts"] == 1
    assert attempted["health"]["top_failures"][0]["count"] == 1
    assert "constraints left no filler" in (
        attempted["health"]["top_failures"][0]["cause"]
    )

    second_selection = choose_exploration_target(
        load_project(tmp_path),
        rule_id="invented/impossible-same",
        seed=8129,
    )
    assert second_selection.probe["identity"] != first_selection.probe["identity"]
    assert (
        choose_exploration_target(load_project(tmp_path), seed=8130).rule_id
        != "invented/impossible-same"
    )

    generated = endpoint("/api/generation/candidate", "POST")(
        GenerationCandidateBody(
            rule_id="invented/simple",
            filler_identity="miv",
            seed=8128,
        )
    )
    assert generated["exploration_probe"]["identity"] == "miv"
    assert generated["exploration_event_id"].startswith("exp-")
    assert generated["exploration_objective"] == "least_attempted_rule"
    assert generated["exploration_filters"] == []
    assert any(
        signature.startswith("fact:predication(")
        for signature in generated["structural_signatures"]
    )
    assert len(read_exploration_events(load_project(tmp_path))) == 1

    endpoint("/api/generation/retest", "POST")(
        GenerationRetestBody(
            rule_id=generated["target_rule"],
            sentence=generated["sentence"],
            seed=generated["seed"],
            requested_bindings=generated["requested_bindings"],
            attempts=generated["attempts"],
        )
    )
    endpoint("/api/generation/from-reading", "POST")(
        GenerationReadingBody(
            rule_id="invented/simple",
            sentence="Luma dax miv.",
        )
    )
    assert len(read_exploration_events(load_project(tmp_path))) == 1

    paired = endpoint("/api/generation/minimal-pair", "POST")(
        GenerationMinimalPairBody(
            rule_id=generated["target_rule"],
            base_seed=generated["seed"],
            original_bindings=generated["requested_bindings"],
            reroll_slot="who",
        )
    )
    assert paired["exploration_event_id"].startswith("exp-")
    assert len(read_exploration_events(load_project(tmp_path))) == 2

    lexicon_path = tmp_path / "pack" / "lexicon.yaml"
    lexicon_path.write_text(
        lexicon_path.read_text() + "  nova: {senses: [noun], plural: novas}\n"
    )
    revised = exploration_status(load_project(tmp_path))
    revised_rule = next(
        item
        for item in revised["rules"]
        if item["id"] == "invented/impossible-same"
    )
    assert revised_rule["status"] == "never_generated"
    assert revised_rule["failed_count"] == 0
    assert revised_rule["attempt_count"] == 0
    assert len(read_exploration_failures(load_project(tmp_path))) == 1

    with pytest.raises(ValidationError):
        GenerationCandidateBody.model_validate(
            {
                "rule_id": "invented/simple",
                "seed": 1,
                "path": str(tmp_path / "elsewhere.jsonl"),
            }
        )


def test_exploration_event_schema_rejects_unbounded_or_extra_data() -> None:
    with pytest.raises(ValidationError):
        ExplorationEvent.model_validate(
            {
                "candidate_id": "gen-example",
                "rule_id": "invented/simple",
                "seed": 1,
                "registry_fingerprint": "abcdef0123456789",
                "fillers": [],
                "note": "exploration rows do not accept free text",
            }
        )

    with pytest.raises(ValidationError):
        ExplorationFailure.model_validate(
            {
                "rule_id": "invented/simple",
                "seed": 1,
                "registry_fingerprint": "abcdef0123456789",
                "error": "could not realize",
                "path": "/tmp/not-allowed.jsonl",
            }
        )


def test_reviews_can_only_use_the_fixed_project_path(tmp_path: Path) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project, rule_id="invented/simple", seed=5
    )
    review = ReviewRecord(
        candidate_id=candidate.id,
        sentence=candidate.sentence,
        target_rule=candidate.target_rule,
        seed=candidate.seed,
        registry_fingerprint=candidate.registry_fingerprint,
        verdict="invalid",
        note="The premise is deliberately under review.",
    )

    durable = append_review(project, review)

    path = tmp_path / "generation" / "reviews.jsonl"
    assert path.exists()
    assert read_reviews(project) == [durable]
    with pytest.raises(ValidationError):
        ReviewRecord.model_validate(
            {
                **review.model_dump(),
                "path": str(tmp_path / "elsewhere.jsonl"),
            }
        )
    assert not (tmp_path / "elsewhere.jsonl").exists()


def test_structured_defects_and_hypothesis_statuses_survive_corrections(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(
        project, rule_id="invented/simple", seed=8128
    )
    defect = ReviewDefect(
        kind="wrong_category_membership",
        attachment=PremiseAttachment(kind="token", index=1),
    )
    hypothesis = derive_hypotheses(
        candidate, verdict="invalid", defects=[defect]
    )[0]
    first = append_review(
        project,
        ReviewRecord(
            candidate_id=candidate.id,
            sentence=candidate.sentence,
            target_rule=candidate.target_rule,
            seed=candidate.seed,
            registry_fingerprint=candidate.registry_fingerprint,
            requested_bindings=candidate.requested_bindings,
            verdict="invalid",
            defects=[defect],
            hypotheses=[hypothesis],
        ),
    )

    corrected = update_review(
        project,
        first["id"],
        "invalid",
        "tested in the editor",
        [hypothesis.model_copy(update={"status": "confirmed"})],
    )

    assert corrected["requested_bindings"] == candidate.requested_bindings
    assert corrected["defects"][0]["attachment"] == {
        "kind": "token",
        "index": 1,
    }
    assert corrected["hypotheses"][0]["status"] == "confirmed"
    assert len(_raw_reviews(project)) == 2


def _review(candidate, verdict: str = "unclear", note: str = "") -> ReviewRecord:
    return ReviewRecord(
        candidate_id=candidate.id,
        sentence=candidate.sentence,
        target_rule=candidate.target_rule,
        seed=candidate.seed,
        registry_fingerprint=candidate.registry_fingerprint,
        verdict=verdict,
        note=note,
    )


def _seeded(tmp_path: Path):
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = generate_candidate(project, rule_id="invented/simple", seed=5)
    return project, candidate


def test_editing_a_review_supersedes_without_destroying_the_original(
    tmp_path: Path,
) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "unclear", "unsure"))

    corrected = update_review(project, first["id"], "invalid", "decided")

    live = read_reviews(project)
    assert [r["id"] for r in live] == [corrected["id"]]
    assert live[0]["verdict"] == "invalid"
    assert live[0]["note"] == "decided"
    assert corrected["supersedes"] == first["id"]
    # the ledger keeps both rows: the correction is an APPEND, not a rewrite
    raw = _raw_reviews(project)
    assert [r["id"] for r in raw] == [first["id"], corrected["id"]]
    assert raw[0]["verdict"] == "unclear"


def test_ask_review_pins_the_complete_generated_scenario(tmp_path: Path) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    evidence = AskScenarioReviewEvidence(
        target_ask="ask/invented-total",
        scenario_mode="answerable",
        question="How many mivs does Luma have?",
        text="Luma dax 3 mivs. How many mivs does Luma have?",
        consumer="single-entity",
        query={"consumer": "single-entity", "entity": "luma", "measure": "miv"},
        premises=["Luma dax 3 mivs."],
        premise_rules=["invented/simple"],
        answer={"kind": "number", "value": 3, "committed": True},
        answer_shape="number",
        minimal=True,
    )

    durable = append_review(
        project,
        ReviewRecord(
            candidate_id="askgen-invented",
            review_kind="ask",
            sentence=evidence.question,
            context_before=evidence.premises,
            target_rule=None,
            ask_scenario=evidence,
            seed=44,
            registry_fingerprint=project.registry.fingerprint,
            verdict="invalid",
            defects=[
                ReviewDefect(
                    kind="incorrect_query_binding",
                    attachment=PremiseAttachment(kind="sentence"),
                )
            ],
            note="the measure binding needs inspection",
        ),
    )

    assert read_reviews(project) == [durable]
    assert durable["review_kind"] == "ask"
    assert durable["ask_scenario"]["text"] == evidence.text
    assert durable["ask_scenario"]["query"] == evidence.query
    assert durable["ask_scenario"]["answer"]["value"] == 3


def test_ask_review_requires_exact_generated_scenario_evidence() -> None:
    with pytest.raises(ValidationError):
        ReviewRecord(
            candidate_id="askgen-missing",
            review_kind="ask",
            sentence="How many mivs?",
            target_rule=None,
            seed=1,
            registry_fingerprint="abcdef0123456789",
            verdict="unclear",
        )


def test_editing_preserves_what_was_actually_reviewed(tmp_path: Path) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "valid"))

    corrected = update_review(project, first["id"], "invalid", "")

    # only the human judgment may move; the reviewed artefact stays pinned
    for field in ("candidate_id", "sentence", "target_rule", "seed",
                  "registry_fingerprint"):
        assert corrected[field] == first[field]


def test_sentence_interpretation_and_rule_suggestion_are_append_only_edits(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)
    candidate = promote_sentence_review_candidate(project, sentence="Miv.")
    first = append_review(
        project,
        ReviewRecord(
            candidate_id=candidate.id,
            origin="reading",
            review_kind="sentence",
            sentence=candidate.sentence,
            target_rule=None,
            seed=candidate.seed,
            registry_fingerprint=candidate.registry_fingerprint,
            verdict="unclear",
            interpretation="An entity is mentioned.",
            suggested_rule="Consider a nominal utterance rule.",
        ),
    )

    corrected = update_review(
        project,
        first["id"],
        "valid",
        "ordinary elliptical language",
        interpretation="The named entity is the topic.",
        suggested_rule="Add a deliberately scoped nominal-utterance rule.",
    )

    assert corrected["supersedes"] == first["id"]
    assert corrected["target_rule"] is None
    assert corrected["interpretation"] == "The named entity is the topic."
    assert (
        corrected["suggested_rule"]
        == "Add a deliberately scoped nominal-utterance rule."
    )
    assert _raw_reviews(project)[0]["interpretation"] == "An entity is mentioned."


def test_deleting_a_review_appends_a_tombstone(tmp_path: Path) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "valid"))

    delete_review(project, first["id"])

    assert read_reviews(project) == []
    raw = _raw_reviews(project)
    assert len(raw) == 2
    assert raw[0]["verdict"] == "valid"  # original untouched on disk
    assert raw[1]["tombstones"] == first["id"]


def test_resolved_review_stays_in_history_but_leaves_open_gate(
    tmp_path: Path,
) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "invalid"))

    marker = resolve_review(project, first["id"], "fixed by a role boundary")

    assert read_reviews(project) == []
    history = read_review_history(project)
    assert len(history) == 1
    assert history[0]["sentence"] == first["sentence"]
    assert history[0]["verdict"] == "invalid"
    assert history[0]["review_status"] == "resolved"
    assert history[0]["resolves"] == first["id"]
    assert history[0]["resolution_note"] == "fixed by a role boundary"
    assert marker["timestamp"] == first["timestamp"]


def test_accidental_tombstone_can_be_recovered_as_visible_resolution(
    tmp_path: Path,
) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "invalid"))
    delete_review(project, first["id"])

    resolve_review(project, first["id"], "reconciled")

    assert read_reviews(project) == []
    assert read_review_history(project)[0]["review_status"] == "resolved"


def test_human_can_tombstone_a_resolved_review_after_verification(
    tmp_path: Path,
) -> None:
    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "invalid"))
    resolved = resolve_review(project, first["id"], "fixed")

    tombstone = delete_review(project, resolved["id"])

    assert tombstone["tombstones"] == resolved["id"]
    assert read_reviews(project) == []
    assert read_review_history(project) == []


def test_an_edited_review_can_still_be_deleted(tmp_path: Path) -> None:
    """The tombstone must target the live row, not the spent original."""

    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "unclear"))
    corrected = update_review(project, first["id"], "valid", "")

    delete_review(project, corrected["id"])

    assert read_reviews(project) == []
    assert len(_raw_reviews(project)) == 3


def test_a_superseded_review_cannot_be_edited_or_deleted(tmp_path: Path) -> None:
    """Otherwise a stale designer tab would resurrect a spent verdict."""

    project, candidate = _seeded(tmp_path)
    first = append_review(project, _review(candidate, "unclear"))
    update_review(project, first["id"], "valid", "")

    with pytest.raises(KeyError):
        update_review(project, first["id"], "invalid", "")
    with pytest.raises(KeyError):
        delete_review(project, first["id"])
    with pytest.raises(KeyError):
        delete_review(project, "rev-does-not-exist")


def test_rows_written_before_ids_existed_stay_addressable(tmp_path: Path) -> None:
    """Legacy history predates the id field; folding must not orphan it."""

    _write_project(tmp_path)
    project = load_project(tmp_path)
    path = review_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"candidate_id": "gen-legacy", "note": "", "project": "p", "seed": 1,'
        ' "registry_fingerprint": "abcdef0123456789",'
        ' "sentence": "A synthetic legacy row.", "target_rule": "probe/rule",'
        ' "timestamp": "2026-01-01T00:00:00+00:00", "verdict": "unclear"}\n',
        encoding="utf-8",
    )

    live = read_reviews(project)
    assert len(live) == 1
    legacy_id = live[0]["id"]
    # the derived id must be stable across reads, or edits would miss it
    assert read_reviews(project)[0]["id"] == legacy_id

    update_review(project, legacy_id, "valid", "triaged")
    assert [r["verdict"] for r in read_reviews(project)] == ["valid"]


def test_history_limit_counts_live_reviews_not_spent_corrections(
    tmp_path: Path,
) -> None:
    project, candidate = _seeded(tmp_path)
    kept = append_review(project, _review(candidate, "valid"))
    noisy = append_review(project, _review(candidate, "unclear"))
    for _ in range(5):
        noisy = update_review(project, noisy["id"], "unclear", "again")

    live = read_reviews(project, limit=2)
    assert {r["id"] for r in live} == {kept["id"], noisy["id"]}


def test_designer_exposes_the_generation_review_loop() -> None:
    root = Path("src/rulekit/server/static")
    html = (root / "index.html").read_text()
    js = (root / "app.js").read_text()
    css = (root / "style.css").read_text()

    assert 'id="view-generate"' in html
    assert 'id="generation-rule"' in html
    assert 'id="generation-mode"' in html
    assert 'value="lexical_boundary"' in html
    assert 'id="generation-filler"' in html
    assert 'id="generation-exploration-selection"' in html
    assert 'id="generation-probe"' in html
    assert 'id="generation-mode-note"' in html
    assert 'data-verdict="valid"' in html
    assert 'data-verdict="invalid"' in html
    assert 'data-verdict="unclear"' in html
    assert 'id="generation-premise-list"' in html
    assert 'id="generation-objective"' in html
    assert 'id="generation-filter-groups"' in html
    assert 'id="generation-health"' in html
    assert 'id="generation-minimal-pair"' in html
    assert 'id="generation-defects"' in html
    assert 'id="generation-attachment"' in html
    assert 'id="generation-hypotheses"' in html
    assert 'id="generation-interpretation"' in html
    assert 'id="generation-rule-suggestion"' in html
    assert 'id="generation-review-title"' in html
    assert 'id="save-retest-btn"' in html
    assert 'id="generation-retest-diff"' in html
    assert "/api/generation/candidate" in js
    assert "/api/generation/exploration" in js
    assert "/api/generation/from-reading" in js
    assert "/api/generation/retest" in js
    assert "/api/generation/minimal-pair" in js
    assert "/api/generation/hypotheses" in js
    assert '"fact generation-fact"' in js
    assert '"generation-fact-header"' in js
    assert '"generation-fact-fields"' in js
    assert '"generation-fact-derivation"' in js
    assert "How this fact was derived" in js
    assert "displayedFact.source_ref" in js
    assert ".generation-fact-derivation" in css
    assert "/api/generation/review" in js
    assert "openGenerationSource" in js
    assert "RulekitEditor?.gotoLine" in js
    assert "renderGenerationRetest" in js
    assert "renderGenerationHypotheses" in js
    assert "Open in editor" in js
    assert "reviewRecorded" in js
    assert "promoteReadingSentence" in js
    assert "Review premise" in js
    assert "Review sentence meaning" in js
    assert "target_rule: candidate.target_rule" in js
    assert "source_ref: candidate.target_source" in js
    assert 'review_kind: candidate.target_rule ? "premise" : "sentence"' in js
    assert 'candidate.target_rule || "Sentence-level interpretation review"' in js
    assert '"Sentence meaning review"' in js
    assert 'r.target_rule || r.ask_scenario?.target_ask || "No target rule"' in js
    assert "suggested_rule" in js
    assert "Open rule YAML" in js
    assert "Open ask YAML" in js
    assert "function reviewSource(r)" in js
    assert "state.campaignRunner.project?.sources?.[target] || r.source_ref" in js
    assert "if (source) await openGenerationSource(source)" in js
    assert "reading-fact-head" in js
    assert "d.source_ref" in js
    assert "f.source_ref" in js
    assert "loadGenerationExploration" in js
    assert "selectedGenerationMode" in js
    assert "selectedGenerationObjective" in js
    assert "selectedGenerationFilters" in js
    assert "generationRuleMatchesFilters" in js
    assert "Structural target" in js
    assert "Most frequent generation blockers" in js
    assert 'generation_mode: generationMode' in js
    assert "objective: generationMode" in js
    assert "filters: generationMode" in js
    assert "boundary probes do not count as strict rule or lexicon coverage" in js
    assert "attempted_failed" in js
    assert "rule frontier: ${objective}, with seeded tie-breaking" in js
    assert "use Review history → Edit for corrections" in js
    assert "control.title = help" in js
    assert "Fact omits needed context" in js
    assert "fact drops an identity, qualifier, role, time" in js
    assert 'option.value = `fact:${index}`' in js
    assert "fact ? { fact }" in js
    generate_next = js[js.index("async function generateNext()"):]
    assert "await loadGenerationExploration();" in generate_next
    seed_consumed = generate_next.index("state.lastGenerationSeed = seed")
    candidate_request = generate_next.index(
        'await api("POST", "/api/generation/candidate"'
    )
    assert seed_consumed < candidate_request
    assert 'prior === state.lastGenerationSeed ? 1 : 0' in generate_next
    assert '$("generation-seed").addEventListener("input"' in js
    assert "seed ${seed}: ${candidate.detail}" in generate_next
    assert "minmax(22ch, 260px)" in css
    assert ".generation-structure-controls" in css
    assert ".generation-filter-options" in css
