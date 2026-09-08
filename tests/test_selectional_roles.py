"""Category-owned verb roles keep lexical compatibility out of grammar rules."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.registry import CompileError
from rulekit.data.registry import Registry
from rulekit.data.schemas import VerbRolesCompatibilityPredicate
from rulekit.generation import GenerationError, generate_candidate
from rulekit.generation.sample import (
    _Filler, _SELECTIONAL_FRAME_CACHE, _selectional_assignment_compatible,
)
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
RULE_ID = "arithmetic/anchored-relation-conjoined-measures"


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


def _write_project(root: Path, *, invalid_child_target: bool = False) -> None:
    base = root / "base"
    extension = root / "extension"
    base.mkdir(parents=True)
    extension.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-selectional-roles
packs: [./base, ./extension]
"""
    )
    (root / "generation.yaml").write_text(
        """\
format: rulekit/generation@1
names: [Ava, Bea]
"""
    )
    (base / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: base\nversion: 0.1.0\n"
    )
    (extension / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: extension\nversion: 0.1.0\n"
    )
    (base / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  eat: {senses: [verb]}
  apple: {senses: [noun], plural: apples}
  stone: {senses: [noun], plural: stones}
"""
    )
    child_target = "stone_object" if invalid_child_target else "edible_object"
    (base / "categories.yaml").write_text(
        f"""\
format: rulekit/categories@1
categories:
  participant: {{parent: noun}}
  consumable_object: {{parent: noun}}
  edible_object: {{parent: consumable_object}}
  stone_object: {{parent: noun}}
  consumption_verb:
    parent: verb
    selectional_roles:
      actor: participant
      theme: consumable_object
  eating_verb:
    parent: consumption_verb
    selectional_roles:
      theme: {child_target}
members:
  eating_verb: [eat]
  edible_object: [apple]
  stone_object: [stone]
"""
    )
    (base / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/eating
    phase: read
    match:
      sentence:
        - {slot: who, type: proper_name}
        - {slot: verb, type: verb}
        - {slot: item, type: plural}
    where:
      - verb_roles_compatible:
          verb: verb
          roles:
            actor: [who]
            theme: [item]
          allow_proper_name: [who]
"""
    )
    (extension / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  devour: {senses: [verb]}
  devours: {senses: [verb], verb: {lemma: devour}}
  cake: {senses: [noun], plural: cakes}
"""
    )
    # The extension adds only vocabulary memberships. It neither redefines
    # the category contract nor edits the grammar rule.
    (extension / "categories.yaml").write_text(
        """\
format: rulekit/categories@1
members:
  eating_verb: [devour, devours]
  edible_object: [cake]
"""
    )


def test_generation_frame_cache_keeps_role_checks_and_revision_boundaries(tmp_path, monkeypatch):
    _write_project(tmp_path)
    reg = load_project(tmp_path).registry
    _SELECTIONAL_FRAME_CACHE.clear()
    calls = []
    original = Registry.selectional_frames

    def counted(self, word):
        calls.append((self.fingerprint, word))
        return original(self, word)

    monkeypatch.setattr(Registry, "selectional_frames", counted)
    requirement = VerbRolesCompatibilityPredicate(
        verb="verb", roles={"theme": ["item"]}, require_declared_frame=True,
    )
    verb = _Filler("eat", "eat")
    assert _selectional_assignment_compatible(verb, {"item": _Filler("apple", "apple")}, requirement, reg)
    assert not _selectional_assignment_compatible(verb, {"item": _Filler("stone", "stone")}, requirement, reg)
    assert len(calls) == 1
    restricted = requirement.model_copy(update={"frame_categories": ["stone_object"]})
    assert not _selectional_assignment_compatible(verb, {}, restricted, reg)
    assert not _selectional_assignment_compatible(verb, {}, restricted, reg)
    assert len(calls) == 2  # Empty frames are cached too, separately by restriction.

    # A normal project edit yields a fresh fingerprint, not stale role data.
    categories = tmp_path / "extension" / "categories.yaml"
    categories.write_text(categories.read_text().replace("[cake]", "[cake, stone]"))
    revised = load_project(tmp_path).registry
    assert revised.fingerprint != reg.fingerprint
    assert _selectional_assignment_compatible(verb, {"item": _Filler("stone", "stone")}, requirement, revised)
    assert len(calls) == 3


def test_curated_conjoined_rule_reads_category_owned_frames() -> None:
    registry = load_project(CURATED).registry
    rule = next(rule for rule in registry.rules if rule.id == RULE_ID)
    compatibility = next(
        predicate.verb_roles_compatible
        for predicate in rule.where
        if predicate.verb_roles_compatible is not None
    )

    assert compatibility.roles == {
        "actor": ["who", "std"],
        "theme": ["item", "item2"],
    }
    assert registry.selectional_frames("eat")[0][1] == {
        "actor": "quantity_event_participant",
        "theme": "edible_quantity_object",
    }
    assert registry.selectional_frames("win")[0][1] == {
        "actor": "animate",
        "theme": "winnable_quantity_object",
    }


@pytest.mark.parametrize(
    ("verb", "actor", "theme"),
    [
        ("travel", "motion_participant", "motion_comparison_measure"),
        ("finish", "quantity_event_participant", "finishable_quantity_object"),
        ("give", "quantity_event_participant", "transferable_quantity_object"),
        ("find", "quantity_event_participant", "findable_quantity_object"),
        ("enroll", "quantity_event_participant", "enrollment_quantity_object"),
        ("drops", "quantity_event_participant", "droppable_quantity_object"),
        ("begin", "initiation_quantity_participant", "initiable_quantity_object"),
        ("earn", "earning_quantity_participant", "earnable_quantity_object"),
        ("make", "production_quantity_participant", "producible_quantity_object"),
    ],
)
def test_bounded_quantity_verb_families_own_complete_frames(
    verb: str, actor: str, theme: str
) -> None:
    registry = load_project(CURATED).registry

    assert registry.selectional_frames(verb)[0][1] == {
        "actor": actor,
        "theme": theme,
    }


def test_generic_money_is_an_earnable_theme() -> None:
    registry = load_project(CURATED).registry

    assert registry.word_in_category("money", "earnable_quantity_object")


def test_extension_owned_shucking_family_uses_the_same_frame_contract() -> None:
    registry = load_project(GSM8K).registry

    assert registry.selectional_frames("shuck")[0][1] == {
        "actor": "quantity_event_participant",
        "theme": "shuckable_item",
    }


def test_teaching_family_owns_complete_frame() -> None:
    registry = load_project(CURATED).registry

    assert registry.selectional_frames("teach")[0][1] == {
        "actor": "animate",
        "theme": "teaching_quantity_object",
    }


def test_arithmetic_grammar_does_not_restate_teaching_frame() -> None:
    registry = load_project(CURATED).registry

    offenders = [
        rule.id
        for rule in (*registry.rules, *registry.asks)
        if any(
            predicate.verb_role_compatible is not None
            and predicate.verb_role_compatible.verb_cat
            == "teaching_quantity_verb"
            for predicate in rule.where
        )
    ]

    assert offenders == []


def test_cardinal_subject_ask_reads_teaching_roles_from_category() -> None:
    registry = load_project(CURATED).registry

    def ask_id(question: str) -> str | None:
        matched = match_ask(solve(question, registry).question, registry)
        return None if matched is None else matched[0].id

    target = "ask/how-many-plural-combined-cardinal-subject"
    assert ask_id("How many students do all 2 teachers teach?") == target
    assert ask_id("How many apples do all 2 teachers teach?") != target
    assert ask_id("How many students do all 2 birds teach?") != target

    ask = next(ask for ask in registry.asks if ask.id == target)
    structural = next(
        predicate.verb_roles_compatible
        for predicate in ask.where
        if predicate.verb_roles_compatible is not None
    )
    assert structural.roles == {"actor": ["who"], "theme": ["item"]}


def test_arithmetic_grammar_does_not_restate_category_owned_positive_frames() -> None:
    registry = load_project(CURATED).registry
    framed_categories = set(registry.selectional_roles)
    # These two constructions intentionally map the comparison standard to
    # the actor role for some verb families but not others. The generic frame
    # predicate cannot express that category-dependent slot mapping yet, so
    # their explicit clauses are the sound residue rather than duplication.
    construction_specific = {
        ("arithmetic/anchored-relation", "find_quantity_verb"),
        ("arithmetic/anchored-relation", "transfer_out"),
        ("arithmetic/anchored-relation", "task_completion_verb"),
        ("arithmetic/anchored-relation-postfix", "motion_comparison_verb"),
        ("arithmetic/anchored-relation-postfix", "shucking_verb"),
        ("arithmetic/anchored-relation-postfix", "transfer_out"),
        ("arithmetic/anchored-relation-postfix", "task_completion_verb"),
    }
    offenders: list[tuple[str, str]] = []

    for rule in (*registry.rules, *registry.asks):
        if not (
            rule.id.startswith("arithmetic/")
            or rule.id.startswith("ask/")
        ):
            continue
        for predicate in rule.where:
            compatibility = predicate.verb_role_compatible
            if (
                compatibility is not None
                and compatibility.role_cat is not None
                and compatibility.verb_cat in framed_categories
                and compatibility.role_cat
                in registry.selectional_roles[
                    compatibility.verb_cat
                ].values()
                and (rule.id, compatibility.verb_cat)
                not in construction_specific
            ):
                offenders.append((rule.id, compatibility.verb_cat))

    assert offenders == []


def test_duration_totality_ask_uses_the_category_owned_complete_frame() -> None:
    registry = load_project(CURATED).registry
    ask = next(
        ask
        for ask in registry.asks
        if ask.id == "ask/how-long-take-span-totality-item"
    )

    structural = [
        predicate.verb_roles_compatible
        for predicate in ask.where
        if predicate.verb_roles_compatible is not None
    ]
    assert len(structural) == 1
    assert structural[0].roles == {
        "actor": ["who"],
        "theme": ["item"],
    }
    assert structural[0].allow_proper_name == ["who"]


def test_affine_frame_uses_category_contract_without_relisting_eating() -> None:
    registry = load_project(CURATED).registry
    rule = next(
        rule
        for rule in registry.rules
        if rule.id == "arithmetic/affine-frame-relation"
    )

    structural = [
        predicate.verb_roles_compatible
        for predicate in rule.where
        if predicate.verb_roles_compatible is not None
    ]
    assert len(structural) == 1
    assert structural[0].roles == {
        "actor": ["who", "std"],
        "theme": ["item"],
    }
    assert "arithmetic/affine-frame-relation" in _matched_rules(
        "Arden ate 3 more than twice the number of apples that Briar ate.",
        registry,
    )
    assert "arithmetic/affine-frame-relation" not in _matched_rules(
        "Arden ate 3 more than twice the number of pencils that Briar ate.",
        registry,
    )


def test_eating_frame_accepts_edible_conjuncts_and_rejects_mixed_objects() -> None:
    registry = load_project(CURATED).registry

    assert RULE_ID in _matched_rules(
        "Arden ate 2 fewer apples and 3 more cookies than Briar.", registry
    )
    assert RULE_ID not in _matched_rules(
        "Arden ate 2 fewer pencils and 3 more cookies than Briar.", registry
    )


def test_extension_vocabulary_inherits_role_contract_without_rule_edits(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    project = load_project(tmp_path)

    assert project.registry.selectional_frames("devour")[0][1] == {
        "actor": "participant",
        "theme": "edible_object",
    }
    assert "invented/eating" in _matched_rules(
        "Ava devours cakes.", project.registry
    )
    assert "invented/eating" not in _matched_rules(
        "Ava devours stones.", project.registry
    )

    candidate = generate_candidate(
        project,
        rule_id="invented/eating",
        seed=7,
        locked_bindings={"who": "Ava", "verb": "devours", "item": "cakes"},
    )
    assert candidate.target_status == "matched"
    assert candidate.sentence == "Ava devours cakes."

    with pytest.raises(GenerationError, match="no filler"):
        generate_candidate(
            project,
            rule_id="invented/eating",
            seed=7,
            locked_bindings={
                "who": "Ava",
                "verb": "devours",
                "item": "stones",
            },
        )


def test_child_selectional_role_must_narrow_its_parent(tmp_path: Path) -> None:
    _write_project(tmp_path, invalid_child_target=True)

    with pytest.raises(CompileError, match="does not narrow inherited"):
        load_project(tmp_path)
