"""Data-only rule families compile once, validate normally, and retain sources."""

from copy import deepcopy
from io import StringIO
from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from rulekit.data.rule_templates import expand_rule_template
from rulekit.data.packs import load_pack
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.schemas import AskRule, PatternRule, RulesDoc
from rulekit.data.sources import index_document


DOCUMENT = """\
format: rulekit/rules@1
templates:
  count:
    parameters:
      actor: {slot: who, type: name}
      extra: []
      guards: []
      amount: {value: n}
    rule:
      phase: read
      match:
        sentence:
          - {parameter: actor}
          - {parameter: extra}
          - {lit: has}
          - {slot: n, type: number}
          - {slot: item, type: noun}
      where: [{parameter: guards}]
      consumes: [n]
      emits:
        - fact: quantity
          entity: "{who}"
          measure: "{item}"
          value: {parameter: amount.value}
variants:
  - id: invented/plain
    template: count
  - id: invented/optional
    template: count
    description: One optional grammatical component.
    arguments:
      extra:
        - opt:
            - {slot: addition, cat: additive_discourse_adverb}
      guards:
        - distinct: [who, item]
"""


def document():
    return YAML().load(DOCUMENT)


def test_compiles_independent_normal_rules_without_mutating_authoring_data():
    raw = document()
    before = deepcopy(raw)
    doc = RulesDoc.model_validate(raw)
    plain, optional = doc.compiled_rules
    assert not doc.rules
    assert raw == before
    assert len(plain.match["sentence"]) == 4
    assert len(optional.match["sentence"]) == 5
    assert optional.match["sentence"][1].opt[0].slot == "addition"
    assert optional.description == "One optional grammatical component."
    assert plain.emits[0].fields["value"] == "n"
    assert optional.where[0].distinct == ["who", "item"]
    optional.match["sentence"][0].type = "entity"
    assert plain.match["sentence"][0].type == "name"
    assert doc.templates["count"].parameters["actor"]["type"] == "name"


def test_document_roundtrip_does_not_duplicate_expanded_rules():
    doc = RulesDoc.model_validate(document())
    restored = RulesDoc.model_validate_json(doc.model_dump_json())
    assert [r.model_dump() for r in restored.compiled_rules] == [
        r.model_dump() for r in doc.compiled_rules
    ]
    assert "_expanded_variants" not in doc.model_dump()
    assert {"rules", "asks", "templates", "variants"} <= RulesDoc.model_json_schema()["properties"].keys()


@pytest.mark.parametrize("change,message", [
    (lambda d: d["variants"][0].update(template="absent"), "unknown template"),
    (lambda d: d["variants"][0].update(arguments={"typo": []}), "unknown template parameters"),
    (lambda d: d["variants"][0].update(arguments={"actor": {"parameter": "actor"}}), "literal YAML"),
    (lambda d: d["variants"][1].update(id="invented/plain"), "defined twice"),
    (lambda d: d["templates"]["count"]["parameters"].update(unused=[]), "unused parameters"),
    (lambda d: d["templates"]["count"]["rule"].update(id="hidden/id"), "cannot own a rule id"),
    (lambda d: d["templates"]["count"]["rule"]["match"]["sentence"][0].update(parameter="missing"), "unknown parameter path"),
    (lambda d: d["templates"]["count"]["rule"]["match"]["sentence"][0].update(parameter="actor..slot"), "empty components"),
    (lambda d: d["templates"]["count"]["rule"]["match"]["sentence"][0].update(slot="other"), "only one string"),
    (lambda d: d["variants"][0].update(arguments={"actor": {"slot": "who", "type": "not-a-token-type"}}), "Input should be"),
    (lambda d: d["variants"][0].update(arguments={"guards": [{"made_up_predicate": []}]}), "Extra inputs"),
])
def test_bad_templates_fail_at_document_validation(change, message):
    raw = document()
    change(raw)
    with pytest.raises(ValidationError, match=message):
        RulesDoc.model_validate(raw)


def test_variant_ids_cannot_shadow_an_explicit_rule():
    raw = document()
    doc = RulesDoc.model_validate(raw)
    explicit, _ = expand_rule_template(doc.templates["count"], doc.variants[0])
    raw["rules"] = [explicit]
    with pytest.raises(ValidationError, match="defined twice"):
        RulesDoc.model_validate(raw)


def test_editor_sources_point_to_the_template_or_argument_that_owns_each_node():
    raw = document()
    index = index_document(Path("invented.yaml"), raw, RulesDoc.model_validate(raw))
    lines = DOCUMENT.splitlines()
    expected = [
        (index.rules["invented/optional"], "id: invented/optional"),
        (index.rule_tokens[("invented/optional", 0)], "actor: {slot: who"),
        (index.rule_tokens[("invented/optional", 1)], "opt:"),
        (index.rule_token_paths[("invented/optional", (1, 0))], "slot: addition"),
        (index.rule_tokens[("invented/optional", 2)], "lit: has"),
        (index.rule_where[("invented/optional", 0)], "distinct: [who, item]"),
    ]
    for ref, text in expected:
        assert ref.line > 1
        assert text in lines[ref.line - 1]


def test_expanded_numeric_values_are_plain_serializable_scalars():
    raw = document()
    raw["variants"][0]["arguments"] = {"amount": {"value": YAML().load("1.0")}}
    rule = RulesDoc.model_validate(raw).compiled_rules[0]
    assert type(rule.emits[0].fields["value"]) is float
    rule.model_dump_json(warnings="error")


def write_pack(root, raw):
    (root / "pack.yaml").write_text("format: rulekit/pack@1\nname: invented\n")
    stream = StringIO()
    YAML().dump(raw, stream)
    (root / "rules.yaml").write_text(stream.getvalue())


def test_expanded_rules_pass_through_normal_registry_validation(tmp_path):
    raw = document()
    raw["variants"] = raw["variants"][:1]
    raw["variants"][0]["arguments"] = {"actor": {"slot": "who", "cat": "missing_role"}}
    write_pack(tmp_path, raw)
    with pytest.raises(CompileError, match="missing_role"):
        compile_registry([load_pack(tmp_path)])


def test_editing_a_template_invalidates_the_registry_fingerprint(tmp_path):
    raw = document()
    raw["variants"] = raw["variants"][:1]
    write_pack(tmp_path, raw)
    before = compile_registry([load_pack(tmp_path)])
    raw["templates"]["count"]["parameters"]["amount"]["value"] = "n * 2"
    write_pack(tmp_path, raw)
    after = compile_registry([load_pack(tmp_path)])
    assert before.fingerprint != after.fingerprint
    assert before.rules[0].id == after.rules[0].id == "invented/plain"
    assert before.rules[0].emits[0].fields["value"] == "n"
    assert after.rules[0].emits[0].fields["value"] == "n * 2"


ASK_DOCUMENT = """\
format: rulekit/rules@1
templates:
  amount-question:
    parameters:
      actor: {slot: who, type: name}
      tail: []
      guards: []
      generation: {}
    rule:
      match:
        question:
          - {lit: how}
          - {lit: many}
          - {slot: item, type: plural}
          - {lit: does}
          - {parameter: actor}
          - {lit: have}
          - {parameter: tail}
      where: [{parameter: guards}]
      resolves:
        consumer: single-entity
        entity: "{who}"
        measure: "{item}"
      generation: {parameter: generation}
ask_variants:
  - id: ask/invented-amount
    template: amount-question
  - id: ask/invented-amount-marked
    template: amount-question
    arguments:
      tail:
        - opt:
            - {lit: altogether}
      guards:
        - distinct: [who, item]
"""


def ask_document():
    return YAML().load(ASK_DOCUMENT)


def test_ask_templates_compile_as_asks_and_survive_authoring_roundtrip():
    raw = document()
    ask_raw = ask_document()
    raw["templates"].update(ask_raw["templates"])
    raw["ask_variants"] = ask_raw["ask_variants"]
    before = deepcopy(raw)
    doc = RulesDoc.model_validate(raw)
    assert raw == before
    assert all(isinstance(r, PatternRule) for r in doc.compiled_rules)
    assert all(isinstance(a, AskRule) for a in doc.compiled_asks)
    assert len(doc.compiled_asks) == 2
    plain, marked = doc.compiled_asks
    assert len(plain.match["question"]) == 6
    assert len(marked.match["question"]) == 7
    assert marked.where[0].distinct == ["who", "item"]
    assert plain.resolves == marked.resolves
    restored = RulesDoc.model_validate_json(doc.model_dump_json())
    assert [a.model_dump() for a in restored.compiled_asks] == [
        a.model_dump() for a in doc.compiled_asks
    ]
    assert not restored.asks  # expanded asks are not copied into authored asks
    assert "_expanded_ask_variants" not in doc.model_dump()
    marked.match["question"][4].type = "entity"
    assert plain.match["question"][4].type == "name"
    assert doc.templates["amount-question"].parameters["actor"]["type"] == "name"


@pytest.mark.parametrize("change,message", [
    (lambda d: d["ask_variants"][0].update(template="absent"), "unknown template"),
    (lambda d: d["ask_variants"][0].update(arguments={"typo": []}), "unknown template parameters"),
    (lambda d: d["ask_variants"][1].update(id="ask/invented-amount"), "defined twice"),
    (lambda d: d["templates"]["amount-question"]["rule"].update(emits=[]), "Extra inputs"),
    (lambda d: d["templates"]["amount-question"]["rule"].update(resolves={}), "exactly one"),
    (lambda d: d["ask_variants"][0].update(arguments={"generation": {"slot_categories": {"missing": ["noun"]}}}), "unknown slots"),
    (lambda d: d["ask_variants"][0].update(arguments={"guards": [{"made_up_predicate": []}]}), "Extra inputs"),
    (lambda d: d["ask_variants"][0].update(arguments={"actor": {"parameter": "actor"}}), "literal YAML"),
    (lambda d: d["ask_variants"][0].update(description="Not an ask field"), "Extra inputs"),
])
def test_ask_variants_obey_template_and_normal_ask_validation(change, message):
    raw = ask_document()
    change(raw)
    with pytest.raises(ValidationError, match=message):
        RulesDoc.model_validate(raw)


def test_ask_variant_cannot_shadow_an_explicit_ask_or_premise_variant():
    raw = ask_document()
    doc = RulesDoc.model_validate(raw)
    raw["asks"] = [doc.compiled_asks[0].model_dump()]
    with pytest.raises(ValidationError, match="defined twice"):
        RulesDoc.model_validate(raw)
    del raw["asks"]
    premise = document()
    raw["templates"].update(premise["templates"])
    raw["variants"] = [{"id": "ask/invented-amount", "template": "count"}]
    with pytest.raises(ValidationError, match="defined twice"):
        RulesDoc.model_validate(raw)


def test_ask_template_editor_links_preserve_variant_and_shared_token_origins():
    raw = ask_document()
    index = index_document(Path("invented-asks.yaml"), raw, RulesDoc.model_validate(raw))
    lines = ASK_DOCUMENT.splitlines()
    target = "ask/invented-amount-marked"
    assert target not in index.rules
    for ref, expected in [
        (index.asks[target], "id: " + target),
        (index.rule_tokens[(target, 4)], "actor: {slot: who"),
        (index.rule_tokens[(target, 5)], "lit: have"),
        (index.rule_tokens[(target, 6)], "opt:"),
        (index.rule_token_paths[(target, (6, 0))], "lit: altogether"),
        (index.rule_where[(target, 0)], "distinct: [who, item]"),
    ]:
        assert ref.line > 1
        assert expected in lines[ref.line - 1]
        assert ref.kind.startswith("ask")


def test_compiled_asks_enter_registry_and_edits_change_fingerprint(tmp_path):
    raw = ask_document()
    write_pack(tmp_path, raw)
    before = compile_registry([load_pack(tmp_path)])
    assert len(before.asks) == 2
    assert not before.rules
    raw["templates"]["amount-question"]["rule"]["resolves"]["verb"] = "have"
    write_pack(tmp_path, raw)
    after = compile_registry([load_pack(tmp_path)])
    assert before.fingerprint != after.fingerprint
    assert [a.id for a in before.asks] == [a.id for a in after.asks]
    assert all(a.resolves["verb"] == "have" for a in after.asks)


def test_expanded_asks_use_normal_registry_category_and_duplicate_checks(tmp_path):
    raw = ask_document()
    raw["ask_variants"][0]["arguments"] = {
        "guards": [{"bound_requires_category": {
            "bound": "who", "slot": "who", "cat": "missing_role",
        }}],
    }
    write_pack(tmp_path, raw)
    with pytest.raises(CompileError, match="missing_role"):
        compile_registry([load_pack(tmp_path)])
    raw = ask_document()
    first = tmp_path / "first"
    first.mkdir()
    write_pack(first, raw)
    second = tmp_path / "second"
    second.mkdir()
    write_pack(second, raw)
    # Two independently loaded packs cannot silently reuse the public ask ID.
    with pytest.raises(CompileError, match="defined twice"):
        compile_registry([load_pack(first), load_pack(second)])
