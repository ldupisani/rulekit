"""Exact class-wide quantities bridging the opt-in logic and arithmetic packs."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.generation import (
    generate_candidate,
    list_rule_availability,
    retest_candidate,
)
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.engine import diagnose, solve
from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import (
    PATTERN,
    Atom,
    ClassRefinement,
    Membership,
    Provenance,
    QuantifiedAdjustment,
    QuantifiedQuantity,
    Quantity,
    Relation,
    VerbalRelation,
)
from rulekit.kernel.saturate import saturate
from rulekit.server.api import ServerState, TraceBody, build_router


ROOT = Path(__file__).resolve().parents[1]


def _registry():
    return load_project(ROOT / "projects/curated").registry


def test_exact_class_quantity_instantiates_for_a_named_member():
    result = solve(
        "All teachers at the university have 20 students. "
        "Bob is a teacher at the university. "
        "How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert result.answer.committed
    assert result.answer.value == 20
    assert any(
        fact.cls == "teacher at university"
        and fact.measure == "student"
        and fact.value == 20
        for fact in result.store.by_kind(QuantifiedQuantity)
    )
    assert any(
        fact.entity == "bob" and fact.pred == "teacher at university"
        for fact in result.store.by_kind(Atom)
    )
    assert any(
        fact.entity == "bob"
        and fact.measure == "student"
        and fact.value == 20
        and fact.provenance.source == "synth/quantified-quantity-instantiation"
        for fact in result.store.by_kind(Quantity)
    )


def test_related_but_nonidentical_class_does_not_instantiate():
    result = solve(
        "All teachers at the university have 20 students. "
        "Bob is a teacher. How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert not result.answer.committed


def test_existential_and_coordinated_amounts_do_not_become_universals():
    for text in (
        "Some teachers have 20 students. Bob is a teacher. "
        "How many students does Bob have?",
        "All teachers have 20 students and 2 aides. Bob is a teacher. "
        "How many students does Bob have?",
    ):
        result = solve(text, _registry(), tracing=False)
        assert not result.answer.committed
        assert list(result.store.by_kind(QuantifiedQuantity)) == []


def test_conflicting_explicit_quantity_is_not_hidden():
    result = solve(
        "All teachers have 20 students. Bob is a teacher. "
        "Bob has 18 students. How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert not result.answer.committed
    assert "conflict" in result.answer.reason


def test_quantified_quantity_rules_are_available_to_human_review():
    project = load_project(ROOT / "projects/curated")
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    for rule_id in (
        "arithmetic/personal-role-at-definite-location",
        "logic-arithmetic/universal-all-have-quantity",
        "logic-arithmetic/universal-all-have-quantity-pp",
    ):
        assert availability[rule_id].supported
        candidate = generate_candidate(project, rule_id=rule_id, seed=0)
        assert candidate.target_status == "matched"
        assert rule_id in {
            match.rule_id for match in candidate.actual_matches
        }


def test_reviewed_logic_pp_surfaces_are_absent() -> None:
    project = load_project(ROOT / "projects/curated")
    reviewed = {
        "arithmetic/personal-role-at-definite-location": (
            "Fia is violinist on cookie."
        ),
        "logic-arithmetic/universal-all-have-quantity-pp": (
            "All violinists of puzzle have 80 grapes."
        ),
        "logic-arithmetic/coordinated-named-verbal-pp": (
            "Mary and Fia find of the guardian."
        ),
    }

    for rule_id, sentence in reviewed.items():
        candidate = retest_candidate(
            project,
            rule_id=rule_id,
            sentence=sentence,
            seed=0,
            origin="generated",
        )
        assert candidate.target_status == "absent"


def test_logic_pp_rules_keep_declared_spatial_role_surfaces() -> None:
    registry = _registry()
    expected = {
        "arithmetic/personal-role-at-definite-location": (
            "Fia is a violinist at the university."
        ),
        "logic-arithmetic/universal-all-have-quantity-pp": (
            "All violinists at the university have 80 grapes."
        ),
        "logic-arithmetic/coordinated-named-verbal-pp": (
            "Mary and Fia teach at the university."
        ),
    }

    for rule_id, sentence in expected.items():
        result = solve(sentence, registry, tracing=False)
        matched = {
            match.match.rule.id
            for matches in result.document.rule_results.values()
            for match in matches
        }
        assert rule_id in matched


def test_coordinated_teaching_derives_exact_roles_and_quantities():
    result = solve(
        "All teachers at the university have 20 students. "
        "Bob and Mary teach at the university. "
        "How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert result.answer.committed
    assert result.answer.value == 20
    teach = next(
        unit for unit in result.premises[1].units if unit.surface == "teach"
    )
    assert next(
        obligation
        for obligation in teach.obligations()
        if obligation.need == "subject"
    ).target is PATTERN
    assert not [gap for gap in result.deficiencies() if "'teach'" in gap]
    assert {
        (fact.entity, fact.verb, fact.prep, fact.obj)
        for fact in result.store.by_kind(VerbalRelation)
    } == {
        ("bob", "teach", "at", "university"),
        ("mary", "teach", "at", "university"),
    }
    assert {
        (fact.entity, fact.pred)
        for fact in result.store.by_kind(Atom)
        if fact.provenance.source == "synth/subject-role-derivation"
    } == {
        ("bob", "teacher at university"),
        ("mary", "teacher at university"),
    }
    assert {
        (fact.entity, fact.measure, fact.value)
        for fact in result.store.by_kind(Quantity)
        if fact.provenance.source
        == "synth/quantified-quantity-instantiation"
    } == {
        ("bob", "student", 20),
        ("mary", "student", 20),
    }


def test_subject_role_derivation_is_exactly_pack_licensed():
    controls = {
        "Bob or Mary teach at the university.": False,
        "Bob and Mary travel at the university.": False,
        "Bob and Mary teach in the university.": False,
        "Bob and Mary teach at the university and garden.": False,
        "Bob and Mary teaches at the university.": False,
        "Bob and Bob teach at the university.": False,
    }

    for text, relation_expected in controls.items():
        result = solve(text, _registry(), tracing=False)
        relations = list(result.store.by_kind(VerbalRelation))
        assert bool(relations) is relation_expected, text
        assert not [
            fact
            for fact in result.store.by_kind(Atom)
            if fact.provenance.source == "synth/subject-role-derivation"
        ], text


def test_subject_role_mapping_is_frozen_data_with_an_authoring_source():
    project = load_project(ROOT / "projects/curated")

    assert dict(project.registry.subject_role_derivations) == {
        ("teach", "at"): "teacher"
    }
    source = project.source_index.subject_role_derivations[("teach", "at")]
    assert source.path == (
        ROOT / "packs/logic-arithmetic/categories/roles.yaml"
    ).resolve()
    assert source.kind == "subject-role-derivation"


def test_coordinated_role_rule_is_generated_and_round_trips():
    project = load_project(ROOT / "projects/curated")
    rule_id = "logic-arithmetic/coordinated-named-verbal-pp"
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert availability[rule_id].supported
    candidate = generate_candidate(
        project,
        rule_id=rule_id,
        seed=0,
        locked_bindings={
            "left": "Aven",
            "conjunction": "and",
            "right": "Mary",
            "verb": "teach",
            "prep": "at",
            "restriction": "university",
        },
    )

    assert candidate.sentence == "Aven and Mary teach at the university."
    assert candidate.target_status == "matched"
    assert rule_id in {match.rule_id for match in candidate.actual_matches}


def _saturate_atom(pred: str, *, polarity: bool = True) -> FactStore:
    store = FactStore()
    store.admit(Atom(
        provenance=Provenance(source="synthetic", sentence=0),
        entity="bob",
        pred=pred,
        polarity=polarity,
    ))
    return saturate(store, _registry(), ArithmeticLog())


def test_declared_refining_modifier_derives_superclass_without_modifier():
    store = _saturate_atom("head teacher")

    assert {
        (fact.subclass, fact.superclass)
        for fact in store.by_kind(ClassRefinement)
    } == {("head teacher", "teacher")}
    assert any(
        fact.entity == "bob"
        and fact.pred == "teacher"
        and fact.provenance.source == "synth/declared-class-refinement"
        for fact in store.by_kind(Atom)
    )
    assert not any(
        fact.entity == "bob" and fact.pred == "head"
        for fact in store.by_kind(Atom)
    )


def test_declared_refinement_preserves_the_complete_superclass_restriction():
    store = _saturate_atom("head teacher at university")

    assert {
        (fact.subclass, fact.superclass)
        for fact in store.by_kind(ClassRefinement)
    } == {("head teacher at university", "teacher at university")}
    assert any(
        fact.entity == "bob" and fact.pred == "teacher at university"
        for fact in store.by_kind(Atom)
    )


def test_undeclared_and_negative_class_phrases_do_not_refine():
    for phrase in (
        "former teacher",
        "fake teacher",
        "lead teacher",
    ):
        store = _saturate_atom(phrase)
        assert list(store.by_kind(ClassRefinement)) == [], phrase
        assert {
            fact.pred for fact in store.by_kind(Atom)
        } == {phrase}, phrase

    negative = _saturate_atom("head teacher", polarity=False)
    assert list(negative.by_kind(ClassRefinement)) == []
    assert not any(
        fact.pred == "teacher" for fact in negative.by_kind(Atom)
    )


def test_refining_universal_records_ontology_without_widening_quantity():
    store = FactStore()
    store.admit(QuantifiedQuantity(
        provenance=Provenance(source="synthetic", sentence=0),
        cls="head teacher",
        measure="student",
        value=5,
    ))
    saturate(store, _registry(), ArithmeticLog())

    assert {
        (fact.subclass, fact.superclass)
        for fact in store.by_kind(ClassRefinement)
    } == {("head teacher", "teacher")}
    assert {
        (fact.cls, fact.measure, fact.value)
        for fact in store.by_kind(QuantifiedQuantity)
    } == {("head teacher", "student", 5)}


def test_copular_refining_membership_exposes_declared_class_edge():
    result = solve(
        "Bob is the head teacher.",
        _registry(),
        tracing=False,
    )

    assert any(
        fact.member == "bob" and fact.collection == "head teacher"
        for fact in result.store.by_kind(Membership)
    )
    assert {
        (fact.subclass, fact.superclass)
        for fact in result.store.by_kind(ClassRefinement)
    } == {("head teacher", "teacher")}
    assert not any(
        fact.member == "bob" and fact.collection == "head"
        for fact in result.store.by_kind(Membership)
    )


def test_refining_modifier_has_an_authoring_source():
    project = load_project(ROOT / "projects/curated")

    assert project.registry.word_in_category("head", "refining_modifier")
    source = project.source_index.category_members[(
        "refining_modifier",
        "head",
    )]
    assert source.path == (
        ROOT / "packs/logic-arithmetic/categories/roles.yaml"
    ).resolve()
    assert source.kind == "category-member"


def test_additive_universal_is_a_class_scoped_adjustment_not_a_relation():
    result = solve(
        "All head teachers have 5 more students.",
        _registry(),
        tracing=False,
    )

    assert {
        (fact.cls, fact.measure, fact.offset, fact.verb)
        for fact in result.store.by_kind(QuantifiedAdjustment)
    } == {("head teacher", "student", 5, "have")}
    assert list(result.store.by_kind(Relation)) == []
    assert not [gap for gap in result.deficiencies() if "'5'" in gap]


def test_unique_scoped_baseline_materializes_only_the_adjusted_quantity():
    result = solve(
        "All teachers at the university have 20 students. "
        "All head teachers have 5 more students. "
        "Bob and Mary teach at the university. "
        "Bob is the head teacher. "
        "How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert result.answer.committed
    assert result.answer.value == 25
    bob = [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "bob" and fact.measure == "student"
    ]
    assert len(bob) == 1
    assert bob[0].value == 25
    assert bob[0].provenance.source.startswith(
        "synth/quantified-adjustment-materialization"
    )
    assert "universal-all-have-quantity-pp" in bob[0].provenance.source
    assert "universal-all-have-adjustment" in bob[0].provenance.source
    assert any(
        fact.entity == "mary"
        and fact.measure == "student"
        and fact.value == 20
        for fact in result.store.by_kind(Quantity)
    )
    assert any(
        entry.source.startswith(
            "synth/quantified-adjustment-materialization"
        )
        and entry.env == {"base": 20, "adjustment": 5}
        and entry.result == 25
        for entry in result.log.entries
    )


def test_nonmember_keeps_the_unadjusted_class_quantity():
    result = solve(
        "All teachers have 20 students. "
        "All head teachers have 5 more students. "
        "Mary is a teacher. How many students does Mary have?",
        _registry(),
        tracing=False,
    )

    assert result.answer.committed
    assert result.answer.value == 20
    assert {
        (fact.entity, fact.value)
        for fact in result.store.by_kind(Quantity)
        if fact.measure == "student"
    } == {("mary", 20)}


def test_active_adjustment_without_a_class_baseline_vetoes_a_shortcut_answer():
    result = solve(
        "All head teachers have 5 more students. "
        "Bob is the head teacher. Bob has 7 students. "
        "How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert not result.answer.committed
    assert "never resolved against one compatible class-wide baseline" in (
        result.answer.reason
    )


def test_multiple_compatible_class_baselines_decline_without_choosing_one():
    result = solve(
        "All teachers have 20 students. "
        "All teachers at the university have 22 students. "
        "All head teachers have 5 more students. "
        "Bob and Mary teach at the university. "
        "Bob is the head teacher. "
        "How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert not result.answer.committed
    assert not [
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "bob" and fact.measure == "student"
    ]


def test_undeclared_compound_cannot_license_an_additive_baseline():
    result = solve(
        "All teachers have 20 students. "
        "All lead teachers have 5 more students. "
        "Bob is a lead teacher. How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert not result.answer.committed
    assert not any(
        fact.subclass == "lead teacher"
        for fact in result.store.by_kind(ClassRefinement)
    )


def test_additive_universal_preserves_signed_fewer_adjustment():
    result = solve(
        "All teachers have 20 students. "
        "All head teachers have 5 fewer students. "
        "Bob is the head teacher. How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert result.answer.committed
    assert result.answer.value == 15


def test_adjusted_quantity_conflicts_with_a_contradictory_explicit_state():
    result = solve(
        "All teachers have 20 students. "
        "All head teachers have 5 more students. "
        "Bob is the head teacher. Bob has 24 students. "
        "How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert not result.answer.committed
    assert "conflict" in result.answer.reason


def test_matching_explicit_state_agrees_with_the_adjusted_derivation():
    result = solve(
        "All teachers have 20 students. "
        "All head teachers have 5 more students. "
        "Bob is the head teacher. Bob has 25 students. "
        "How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert result.answer.committed
    assert result.answer.value == 25
    assert any(
        ambiguity.key[:4] == ("quantity", "bob", "student", "have")
        and ambiguity.deduped.source.startswith(
            "synth/quantified-adjustment-materialization"
        )
        for ambiguity in result.store.agreement_ambiguities
    )


def test_counted_class_is_not_misread_as_a_generic_adjustment():
    result = solve(
        "All 3 teachers have 5 more students.",
        _registry(),
        tracing=False,
    )

    assert list(result.store.by_kind(QuantifiedAdjustment)) == []


def test_additive_universal_rule_is_available_to_human_review():
    project = load_project(ROOT / "projects/curated")
    rule_id = "logic-arithmetic/universal-all-have-adjustment"
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert availability[rule_id].supported
    candidate = generate_candidate(project, rule_id=rule_id, seed=0)
    assert candidate.target_status == "matched"
    assert rule_id in {match.rule_id for match in candidate.actual_matches}


def test_question_local_head_teacher_assumption_completes_the_composition():
    result = solve(
        "All teachers at the university have 20 students. "
        "All head teachers have 5 more students. "
        "Bob and Mary teach at the university. "
        "If Bob is the head teacher, how many students does he have?",
        _registry(),
    )

    assert result.answer.committed
    assert result.answer.value == 25
    assert [(reading.sentence_index, reading.text) for reading in result.assumptions] == [
        (3, "Bob is the head teacher.")
    ]
    assert diagnose(result)["assumptions"] == [
        {"sentence": 3, "text": "Bob is the head teacher."}
    ]
    assert any(
        fact.member == "bob"
        and fact.collection == "head teacher"
        and fact.provenance.assumption
        for fact in result.store.by_kind(Membership)
    )
    adjusted = next(
        fact
        for fact in result.store.by_kind(Quantity)
        if fact.entity == "bob" and fact.value == 25
    )
    assert adjusted.provenance.assumption
    assert ";assumption=fold@3]" in adjusted.provenance.source
    assert {
        event["kind"]
        for event in result.trace()
        if event.get("sentence") == 3
    } >= {"question-assumption"}

    binding = next(
        observation
        for observation in result.log.journal.observations
        if observation.source == "bind-discourse"
    )
    assert binding.outcome == "bound"
    assert binding.winner == "bob"
    assert binding.arbitration == "dominant"
    assert {candidate.key: candidate.distance for candidate in binding.candidates} == {
        "bob": 1,
        "mary": 2,
    }


def test_question_assumption_does_not_escape_its_solve():
    registry = _registry()
    first = solve(
        "All teachers have 20 students. "
        "All head teachers have 5 more students. "
        "If Bob is the head teacher, how many students does Bob have?",
        registry,
        tracing=False,
    )
    second = solve(
        "All teachers have 20 students. "
        "All head teachers have 5 more students. "
        "Bob is a teacher. How many students does Bob have?",
        registry,
        tracing=False,
    )

    assert first.answer.value == 25
    assert second.answer.value == 20
    assert second.assumptions == []
    assert not any(fact.provenance.assumption for fact in second.store.facts)


def test_same_sentence_person_candidates_remain_tied():
    result = solve(
        "All teachers at the university have 20 students. "
        "If Bob and Mary are teachers at the university, "
        "how many students does he have?",
        _registry(),
    )

    assert not result.answer.committed
    binding = next(
        observation
        for observation in result.log.journal.observations
        if observation.source == "bind-discourse"
    )
    assert binding.outcome == "declined"
    assert binding.reason == "tie"
    assert {candidate.key: candidate.distance for candidate in binding.candidates} == {
        "bob": 1,
        "mary": 1,
    }


def test_asserted_head_teacher_premise_is_not_marked_as_an_assumption():
    result = solve(
        "All teachers have 20 students. "
        "All head teachers have 5 more students. "
        "Bob is the head teacher. How many students does Bob have?",
        _registry(),
        tracing=False,
    )

    assert result.answer.value == 25
    assert result.assumptions == []
    assert not any(fact.provenance.assumption for fact in result.store.facts)


def test_designer_trace_exposes_the_question_assumption_scope():
    router = build_router(ServerState(ROOT / "projects/curated"))
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/trace" and "POST" in route.methods
    )
    trace = endpoint(TraceBody(text=(
        "All teachers have 20 students. "
        "All head teachers have 5 more students. "
        "If Bob is the head teacher, how many students does Bob have?"
    )))

    assumption = next(
        sentence
        for sentence in trace["sentences"]
        if sentence.get("scope") == "question-assumption"
    )
    assert assumption["text"] == "Bob is the head teacher."
    assert any(
        fact.get("scope") == "question-assumption"
        and fact["type"] == "Membership"
        and fact["fields"].get("collection") == "head teacher"
        for fact in trace["facts"]
    )
    assert any(
        fact.get("scope") == "question-assumption"
        and fact["type"] == "Quantity"
        and fact["fields"].get("value") == 25
        for fact in trace["facts"]
    )


def test_question_local_hypothesis_returns_each_named_quantity():
    result = solve(
        "All teachers at the university have 20 students. "
        "All head teachers have 5 more students. "
        "Bob and Mary teach at the university. "
        "If Bob is the head teacher, "
        "how many students do Bob and Mary each have?",
        _registry(),
    )

    assert result.answer.kind == "series"
    assert result.answer.committed
    assert result.answer.value == [
        {"entity": "bob", "measure": "student", "value": 25},
        {"entity": "mary", "measure": "student", "value": 20},
    ]
    assert diagnose(result)["answer"] == result.answer.value


def test_designer_trace_exposes_a_json_native_series_answer():
    router = build_router(ServerState(ROOT / "projects/curated"))
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/api/trace" and "POST" in route.methods
    )
    trace = endpoint(TraceBody(text=(
        "All teachers at the university have 20 students. "
        "All head teachers have 5 more students. "
        "Bob and Mary teach at the university. "
        "If Bob is the head teacher, "
        "how many students do Bob and Mary each have?"
    )))

    assert trace["answer"] == {
        "kind": "series",
        "value": [
            {"entity": "bob", "measure": "student", "value": 25},
            {"entity": "mary", "measure": "student", "value": 20},
        ],
        "reason": "per-holder totals for ['bob', 'mary']",
        "assumptions": [],
        "committed": True,
        "clarification": None,
    }
    assert trace["ask"]["id"] == "ask/how-many-each-named-list"
    assert trace["ask"]["query"]["measure_surface"] == "students"
