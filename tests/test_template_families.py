"""Shared rule families keep identities, semantic boundaries and editable sources."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_pack
from rulekit.data.project import load_project
from rulekit.generation import GenerationError, generate_ask_scenario, generate_candidate
from rulekit.kernel.engine import solve


PREMISES = [
    "transfer-ditransitive", "transfer-prepositional",
    "percent-change-event", "percent-change-event-count",
    "measured-content-resulting-total", "measured-content-resulting-total-preposed-goal",
    "measured-content-resulting-total-gapped", "measured-content-multiply-total",
    "measured-content-causative-multiply-total",
    "times-as-much", "fraction-as-much", "affine-times-as-much",
    "times-as-much-elided", "fraction-as-much-elided", "affine-times-as-much-elided",
    "times-as-much-elided-standard", "fraction-as-much-elided-standard",
    "times-as-much-possessive-standard", "affine-times-as-much-possessive-standard",
    "adjacent-carrier-multiplier", "adjacent-carrier-equative",
    "adjacent-carrier-offset", "adjacent-carrier-fraction",
]
ASKS = [
    "how-many-each-named-list", "how-many-each-named-list-postverbal",
    "how-many-individually-named-list", "how-many-individually-named-list-postverbal",
    "how-many-individually-discourse-group", "how-many-individually-discourse-group-postverbal",
]


@pytest.fixture(scope="module")
def project():
    return load_project("projects/curated")


@pytest.fixture(scope="module")
def rules(project):
    return {r.id.removeprefix("arithmetic/"): r for r in project.registry.rules}


def test_all_migrated_declarations_are_variants_not_duplicate_explicit_rules():
    pack = load_pack(Path("packs/arithmetic"))
    rule_variants = {v.id for doc in pack.rules for v in doc.variants}
    ask_variants = {v.id for doc in pack.rules for v in doc.ask_variants}
    assert {"arithmetic/" + name for name in PREMISES} <= rule_variants
    assert {"ask/" + name for name in ASKS} <= ask_variants
    assert not rule_variants.intersection(r.id for doc in pack.rules for r in doc.rules)
    assert not ask_variants.intersection(a.id for doc in pack.rules for a in doc.asks)


def test_transfer_order_cannot_change_roles_or_quantity_signing(rules):
    direct, prepositional = [rules["transfer-" + suffix] for suffix in ("ditransitive", "prepositional")]
    assert direct.where == prepositional.where
    assert direct.emits == prepositional.emits
    assert direct.consumes == prepositional.consumes == ["item"]
    assert [e.fields["entity"] for e in direct.emits] == ["{giver}", "{recipient}"]
    assert [e.fields["verb"] for e in direct.emits] == ["{verb}", "receive"]


def test_percent_change_count_mass_slots_are_coupled_but_safety_is_shared(rules):
    mass, count = rules["percent-change-event"], rules["percent-change-event-count"]
    assert mass.where == count.where
    assert mass.emits == count.emits
    assert mass.consumes == count.consumes == ["f"]
    for rule, direction, category, number in [
        (mass, "mass_quantity_delta", "mass_currency_noun", "singular"),
        (count, "count_quantity_delta", "currency", "plural"),
    ]:
        tokens = rule.match["sentence"]
        assert (tokens[3].cat, tokens[4].cat, tokens[4].number) == (direction, category, number)
        assert any(w.unbound == ["std_seen"] for w in rule.where)
        assert any(w.proportional_delta_compatible is not None for w in rule.where)


def test_measurement_templates_preserve_operation_and_context_boundaries(rules, project):
    direct = rules["measured-content-resulting-total"]
    preposed = rules["measured-content-resulting-total-preposed-goal"]
    gapped = rules["measured-content-resulting-total-gapped"]
    assert direct.emits == preposed.emits == gapped.emits
    assert direct.where == preposed.where
    assert gapped.generation == "reader-only"
    assert not gapped.where
    with pytest.raises(GenerationError, match="reader-only"):
        generate_candidate(project, rule_id=gapped.id, seed=17)
    scaling = rules["measured-content-multiply-total"]
    causative = rules["measured-content-causative-multiply-total"]
    addition = rules["measured-content-add-quantity"]
    assert scaling.emits[0].fact == causative.emits[0].fact
    assert scaling.emits[0].fields == causative.emits[0].fields
    assert scaling.emits[0].attribution.reason is None
    assert causative.emits[0].attribution.reason == ("actor", "content")
    assert scaling.where == causative.where
    assert scaling.generation_context == causative.generation_context == addition.generation_context
    assert [r.emits[0].fields["operation"] for r in (direct, scaling, addition)] == [
        "set_total", "multiply_total", "add_quantity",
    ]


def test_mass_endpoint_templates_do_not_turn_omissions_into_known_quantities(rules):
    for prefix in ("times", "fraction"):
        explicit = rules[prefix + "-as-much"].emits[0].fields
        omitted_measure = rules[prefix + "-as-much-elided"].emits[0].fields
        omitted_standard = rules[prefix + "-as-much-elided-standard"].emits[0].fields
        assert (explicit["measure"], explicit["standard"]) == ("{item}", "{std}")
        assert (omitted_measure["measure"], omitted_measure["standard"]) == (None, "{std}")
        assert (omitted_standard["measure"], omitted_standard["standard"]) == ("{item}", "$elided:standard$")
    for prefix in ("times", "affine-times"):
        possessed = rules[prefix + "-as-much-possessive-standard"]
        assert possessed.emits[0].fields["standard"] == "{std.owner}"
        assert any(w.distinct_from_owner is not None for w in possessed.where)


def test_sequence_variants_stay_occurrence_relations_not_holder_comparisons(rules):
    for suffix in ("equative", "multiplier", "fraction", "offset"):
        rule = rules["adjacent-carrier-" + suffix]
        emit, = rule.emits
        assert emit.fact == "sequence_step"
        assert (emit.fields["series"], emit.fields["measure"]) == ("{series}", "{item}")
        assert any(w.same_lemma == ["series", "previous"] for w in rule.where)
    assert rules["adjacent-carrier-offset"].emits[0].fields["offset"] == "amount * sign(dir)"


@pytest.mark.parametrize("target", ["arithmetic/" + r for r in PREMISES] + ["ask/" + a for a in ASKS])
def test_every_variant_and_expanded_token_retains_an_editable_source(project, target):
    is_ask = target.startswith("ask/")
    compiled = project.registry.asks if is_ask else project.registry.rules
    rule = next(r for r in compiled if r.id == target)
    index = project.source_index
    declaration = (index.asks if is_ask else index.rules)[target]
    lines = declaration.path.read_text().splitlines()
    assert target in lines[declaration.line - 1]
    sequence = rule.match["question" if is_ask else "sentence"]
    for number, _ in enumerate(sequence):
        source = index.rule_tokens[(target, number)]
        line = source.path.read_text().splitlines()[source.line - 1]
        assert source.line > 1
        assert "parameter:" not in line
    for number, _ in enumerate(rule.where):
        source = index.rule_where[(target, number)]
        assert source.line > 1
        assert "parameter:" not in source.path.read_text().splitlines()[source.line - 1]


@pytest.mark.parametrize("name", ASKS)
def test_templated_asks_round_trip_with_variant_links_and_labelled_answers(project, name):
    target = "ask/" + name
    contextual = "discourse-group" in name
    candidate = generate_ask_scenario(
        project, ask_id=target, seed=8242026,
        scenario_mode="answerable" if contextual else "ask_only",
        locked_bindings=None if contextual else {"item": "apples", "aux": "do", "verb": "have"},
        reference_year=2026, max_search_attempts=192,
    )
    assert candidate.target_ask == target
    assert candidate.target_source == project.source_index.asks[target].to_json()
    if contextual:
        assert candidate.answer["committed"]
        assert candidate.answer["kind"] == "series"
        assert candidate.premises
    else:
        # Named-list asks retain their old standalone generation contract.
        # Supply invented quantities rather than assuming a random ask has a
        # complete automatically generated evidence plan (a separate feature).
        prefix = " ".join(f"{holder.title()} has {i + 3} apples."
                          for i, holder in enumerate(candidate.query["holders"]))
        result = solve(prefix + " " + candidate.question, project.registry)
        assert result.answer.committed
        assert result.answer.kind == "series"


@pytest.mark.parametrize("name", ASKS[-2:])
def test_discourse_ask_templates_still_require_antecedent_evidence(project, name):
    with pytest.raises(GenerationError, match="requires generated premise evidence"):
        generate_ask_scenario(project, ask_id="ask/" + name, seed=17, scenario_mode="ask_only")
