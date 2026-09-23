"""Invented cases for owned text, component evidence and original-length equations."""

from dataclasses import replace

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import Provenance, Quantity, Relation, TextPrefixSplit, TextValue
from rulekit.kernel.text_evidence import prefix_remainder, text_evidence


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def project(request):
    return load_project("projects/" + request.param)


COMPARISON = "Aven's last name has two fewer letters than Bira's last name. "
HYPOTHETICAL = (
    "If Bira took three letters off her last name, she would have a last name "
    "twice the length of Cato's. "
)
ANCHOR = "Cato's full name is Cato Reed. "
QUESTION = "How many letters are in Aven's last name?"


@pytest.mark.parametrize("apostrophe", ["'", "’"])
@pytest.mark.parametrize("order", [0, 1, 2])
def test_chained_original_text_lengths(project, apostrophe, order):
    sentences = [COMPARISON, HYPOTHETICAL, ANCHOR]
    premises = sentences[order:] + sentences[:order]
    result = solve(("".join(premises) + QUESTION).replace("'", apostrophe), project.registry)
    assert result.value == 9, result.answer
    assert not result.deficiencies()
    counts = {(q.entity_ref.head, q.owner): q.value
              for q in result.store.by_kind(Quantity)}
    assert counts[("last name", "cato")] == 4
    assert counts[("last name", "bira")] == 11
    assert counts[("last name", "aven")] == 9
    assert all(q.is_state for q in result.store.by_kind(Quantity))
    assert {type(f) for f in result.facts()} == {TextValue, TextPrefixSplit, Quantity, Relation}
    assert result.answer.proof
    assert any(s.rule == "explicit-prefix-split" for s in result.answer.proof.steps)


@pytest.mark.parametrize("attribute", ["last name", "first name", "surname", "nickname"])
@pytest.mark.parametrize("ending", ["Cato's", "Cato's {attribute}"])
def test_hypothetical_edit_reuses_any_owned_textual_attribute(project, attribute, ending):
    conditional = HYPOTHETICAL.replace("Cato's", ending).format(attribute=attribute)
    conditional = conditional.replace("last name", attribute)
    result = solve(
        conditional + f"Cato's {attribute} is Reed. "
        f"How many letters does Bira's {attribute} have?", project.registry,
    )
    assert result.value == 11, result.answer


@pytest.mark.parametrize("anchor,value", [
    ("Cato's last name is Abbott. ", 13),
    ("Cato's last name has 7 letters. ", 15),
])
def test_text_literal_or_stated_extent_can_anchor_the_same_relations(project, anchor, value):
    result = solve(COMPARISON + HYPOTHETICAL + anchor + QUESTION, project.registry)
    assert result.value == value, result.answer


@pytest.mark.parametrize("text", [
    COMPARISON + HYPOTHETICAL + QUESTION,
    COMPARISON + HYPOTHETICAL + "Dena's full name is Dena Reed. " + QUESTION,
    COMPARISON + HYPOTHETICAL + "Cato's full name is Dena Reed. " + QUESTION,
    COMPARISON + HYPOTHETICAL + "Cato's full name is Dena Reed. Cato's last name is Abbott. " + QUESTION,
    COMPARISON + HYPOTHETICAL + "Cato's full name is Cato. " + QUESTION,
    COMPARISON + HYPOTHETICAL + ANCHOR + "Cato's last name is Abbott. " + QUESTION,
    COMPARISON + HYPOTHETICAL + ANCHOR + "Bira's last name has 6 letters. " + QUESTION,
    COMPARISON.replace("two fewer", "twenty fewer") + HYPOTHETICAL + ANCHOR + QUESTION,
    COMPARISON.replace("two fewer", "0.5 fewer") + HYPOTHETICAL + ANCHOR + QUESTION,
    COMPARISON + HYPOTHETICAL.replace("her last name", "my last name") + ANCHOR + QUESTION,
    COMPARISON + HYPOTHETICAL.replace("her last name", "his last name") + ANCHOR + QUESTION,
    COMPARISON + HYPOTHETICAL.replace("have a last name", "have a nickname") + ANCHOR + QUESTION,
    COMPARISON + HYPOTHETICAL.replace("she would", "Dena would") + ANCHOR + QUESTION,
    COMPARISON + HYPOTHETICAL.replace("would have", "would not have") + ANCHOR + QUESTION,
    COMPARISON + HYPOTHETICAL.replace("three letters", "three words") + ANCHOR + QUESTION,
    COMPARISON + HYPOTHETICAL + ANCHOR + "Bira took 2 letters off her last name. " + QUESTION,
    COMPARISON + HYPOTHETICAL + ANCHOR + "Aven has 8 cards. " + QUESTION,
])
def test_unsupported_or_inconsistent_evidence_declines(project, text):
    result = solve(text, project.registry)
    assert not result.answer.committed, result.answer


def test_owner_and_attribute_both_scope_counts(project):
    premises = "Aven's surname is Abbott. Bira's surname is Reed. Aven's nickname is Bo. "
    for owner, attribute, expected in [("Aven", "surname", 6), ("Bira", "surname", 4),
                                        ("Aven", "nickname", 2), ("Cato", "surname", None),
                                        ("Bira", "nickname", None)]:
        result = solve(premises + f"How many letters are in {owner}'s {attribute}?", project.registry)
        assert result.value == expected, result.answer


def test_letter_count_normalizes_unicode_and_ignores_separators(project):
    fact = TextValue(Provenance("invented/literal", 0), "nickname", "Ame\u0301lie Jo", "letter", "aven")
    store = FactStore(facts=[fact])
    quantities = text_evidence(store, project.registry, ArithmeticLog())
    assert len(quantities) == 1
    assert quantities[0].value == 8
    assert quantities[0].entity_ref == fact.entity_ref
    unsupported = replace(fact, measure="page")
    assert not text_evidence(FactStore(facts=[unsupported]), project.registry, ArithmeticLog())


def test_contradictory_equal_length_spellings_still_collide(project):
    result = solve("Aven's surname is Reed. Aven's surname is Park. "
                   "How many letters are in Aven's surname?", project.registry)
    assert not result.answer.committed
    assert result.store.collisions


@pytest.mark.parametrize("rule_id", [
    "arithmetic/owned-text-value",
    "arithmetic/owned-text-count",
    "arithmetic/owned-text-count-comparison",
    "arithmetic/hypothetical-text-removal-ratio-elided",
    "arithmetic/hypothetical-text-removal-ratio-explicit",
])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_text_extent_rules_round_trip_in_the_designer(project, rule_id, seed):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
    assert candidate.target_status == "matched", candidate.sentence
    assert " 's" not in candidate.sentence
    result = solve(candidate.sentence, project.registry)
    assert not result.deficiencies(), (candidate.sentence, result.deficiencies())


def test_literal_two_part_definition_exposes_its_generation_boundary(project):
    from rulekit.generation import list_rule_availability
    row = next(row for row in list_rule_availability(project)
               if row.id == "arithmetic/two-part-personal-name")
    assert not row.supported
    assert row.generation == "reader-only"


@pytest.mark.parametrize("comparison", [
    "Aven's last name has two fewer letters than Bira's last name. ",
    "Aven's last name has two fewer letters than Bira's. ",
    "Aven's last name is two letters shorter than Bira's last name. ",
    "Aven's last name is two letters shorter than Bira's. ",
])
@pytest.mark.parametrize("poss,outcome", [("her", "she"), ("his", "he"), ("their", "they")])
def test_paraphrases_and_anaphoric_paradigms_compose(project, comparison, poss, outcome):
    text = (comparison + f"If Bira removed three letters from {poss} last name, "
            f"{outcome} would have twice as many letters as Cato's last name. "
            "Cato's last name contains four letters. "
            "What is the length of Aven's last name in letters?")
    result = solve(text, project.registry)
    assert result.value == 9, result.answer
    assert not result.deficiencies()
    from rulekit.kernel.reference_identity import reference_from_unit
    conditional = result.premises[1]
    forms = [u for u in conditional.units if u.surface.casefold() in {poss, outcome}]
    assert len(forms) == 2
    assert {reference_from_unit(u).head for u in forms} == {"bira"}
    assert all(reference_from_unit(u).resolved for u in forms)
    # Singular they retains its plural verb-agreement form, despite the
    # construction providing one singular antecedent.
    if outcome == "they":
        assert next(u for u in forms if u.surface == "they").features["number"] == "plural"


@pytest.mark.parametrize("operation", ["took three letters off", "removed three letters from"])
@pytest.mark.parametrize("result_phrase", [
    "a surname twice the length of Cato's surname",
    "twice as many letters as Cato's surname",
])
@pytest.mark.parametrize("question", [
    "How many letters are in Bira's surname?",
    "How many letters does Bira's surname contain?",
    "What is the length of Bira's surname in letters?",
])
def test_removal_and_result_and_ask_paraphrases(project, operation, result_phrase, question):
    result = solve(f"If Bira {operation} his surname, he would have {result_phrase}. "
                   "Cato's surname is Reed. " + question, project.registry)
    assert result.value == 11, result.answer
    assert not result.deficiencies()


def test_repeated_name_in_consequent_is_exact_not_just_compatible(project):
    for name, expected in [("Bira", 9), ("Dena", None)]:
        result = solve(COMPARISON + HYPOTHETICAL.replace("she would", name + " would")
                       + ANCHOR + QUESTION, project.registry)
        assert result.value == expected, result.answer


@pytest.mark.parametrize("comparison,expected", [
    ("Aven's nickname is three letters longer than Bira's nickname. ", 7),
    ("Aven's nickname is three letters longer than Bira's. ", 7),
    ("Aven's nickname contains three more letters than Bira's. ", 7),
    ("Aven's nickname is one letter shorter than Bira's. ", 3),
])
def test_signed_letter_differences_do_not_require_hypotheticals(project, comparison, expected):
    result = solve(comparison + "Bira's nickname is Reed. How many letters are in Aven's nickname?",
                   project.registry)
    assert result.value == expected, result.answer


@pytest.mark.parametrize("poss,outcome", [
    ("his", "she"), ("her", "he"), ("their", "he"), ("his", "they"),
    ("its", "it"), ("my", "she"), ("your", "they"),
])
def test_incompatible_or_unlicensed_reference_forms_decline(project, poss, outcome):
    text = (COMPARISON + f"If Bira removed three letters from {poss} last name, "
            f"{outcome} would have twice as many letters as Cato's last name. "
            + ANCHOR + QUESTION)
    result = solve(text, project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("conditional", [
    "If Bira removed three words from her last name, she would have twice as many letters as Cato's last name. ",
    "If Bira removed three letters from her last name, she would have twice as many words as Cato's last name. ",
    "If Bira removed three letters from Dena's last name, she would have twice as many letters as Cato's last name. ",
    "Bira removed three letters from her last name. ",
    "If Bira removed three letters from her last name, she would not have twice as many letters as Cato's last name. ",
])
def test_paraphrase_boundaries_remain_decline_safe(project, conditional):
    result = solve(COMPARISON + conditional + ANCHOR + QUESTION, project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("rule_id", [
    "arithmetic/owned-text-count-comparison-elided",
    "arithmetic/owned-text-length-comparison",
    "arithmetic/owned-text-length-comparison-elided",
    "arithmetic/hypothetical-text-remove-from-ratio-elided",
    "arithmetic/hypothetical-text-remove-from-ratio-explicit",
    "arithmetic/hypothetical-text-removal-as-many",
    "arithmetic/hypothetical-text-remove-from-as-many",
    "arithmetic/hypothetical-text-removal-named-outcome",
])
@pytest.mark.parametrize("seed", [0, 1])
def test_paraphrase_rules_round_trip(project, rule_id, seed):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
    assert candidate.target_status == "matched", candidate.sentence
    result = solve(candidate.sentence, project.registry)
    assert not result.deficiencies(), (candidate.sentence, result.deficiencies())


def test_length_in_letters_ask_is_generatable(project):
    from rulekit.generation.ask_generation import generate_ask_scenario
    candidate = generate_ask_scenario(project, ask_id="ask/owned-text-length-in-letters", seed=17)
    assert candidate.target_ask == "ask/owned-text-length-in-letters"
    assert candidate.query["consumer"] == "text-extent"


@pytest.mark.parametrize("comparison", [
    "Aven's surname has two more letters than Aven's. ",
    "Aven's surname is two letters longer than Aven's. ",
    "Aven's surname is two years longer than Bira's. ",
])
def test_comparative_scope_and_dimension_cannot_be_lost(project, comparison):
    result = solve(comparison + "Aven's surname is Reed. How many letters are in Aven's surname?",
                   project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("hyphen", ["-", "\u2010", "\u2011"])
@pytest.mark.parametrize("gap", [" ", "  ", "\t"])
def test_hyphenated_surname_preserves_spelling_and_anchors_original_lengths(project, hyphen, gap):
    surname = "Reed" + hyphen + "Park"
    anchor = f"Cato's full name is Cato{gap}{surname}. "
    result = solve(COMPARISON + HYPOTHETICAL + anchor + QUESTION, project.registry)
    assert result.value == 17, result.answer
    assert not result.deficiencies()
    values = {(v.entity, v.owner): v.text for v in result.store.by_kind(TextValue)}
    assert values[("full name", "cato")] == "Cato" + gap + surname
    assert values[("last name", "cato")] == surname
    counts = {(q.entity_ref.head, q.owner): q.value for q in result.store.by_kind(Quantity)}
    assert counts[("last name", "cato")] == 8
    assert counts[("last name", "bira")] == 19
    assert counts[("last name", "aven")] == 17
    assert any(surname in step.detail for step in result.answer.proof.steps)


@pytest.mark.parametrize("surname,expected", [
    ("Reed-Park", 8), ("Reed-Park-Abbott", 14), ("Léa-Park", 7),
])
def test_direct_written_surname_uses_the_same_letter_counter(project, surname, expected):
    result = solve(f"Aven's surname is {surname}. How many letters does Aven's surname contain?",
                   project.registry)
    assert result.value == expected, result.answer
    assert result.store.by_kind(TextValue)[0].text == surname


@pytest.mark.parametrize("surname", [
    "Reed- Park", "Reed -Park", "Reed - Park", "Reed--Park",
    "Reed-", "-Reed", "Reed-Park-", "Reed—Park", "Reed–Park", "Reed@Park",
    "Reed2-Park",
])
def test_full_name_split_does_not_repair_malformed_or_ambiguous_name_parts(project, surname):
    result = solve(f"Cato's full name is Cato {surname}. How many letters are in Cato's last name?",
                   project.registry)
    assert not result.answer.committed, result.answer


def test_hyphenated_and_space_separated_spellings_are_not_identical_evidence(project):
    result = solve("Aven's surname is Reed-Park. Aven's surname is Reed Park. "
                   "How many letters are in Aven's surname?", project.registry)
    assert not result.answer.committed
    assert result.store.collisions


@pytest.mark.parametrize("text,prefix,remainder", [
    ("Cato Reed-Park", "Cato", "Reed-Park"),
    ("Cato Reed\u2010Park", "cato", "Reed\u2010Park"),
    ("Cato Reed\u2011Park", "Cato", "Reed\u2011Park"),
    ("Cato Le\u0301a-Park", "Cato", "Léa-Park"),
    ("Cato\tReed-Park-Abbott", "Cato", "Reed-Park-Abbott"),
    ("Cato Reed--Park", "Cato", None),
    ("Cato -Reed", "Cato", None),
    ("Cato Reed-", "Cato", None),
    ("Cato Reed−Park", "Cato", None),
    ("Cato Reed—Park", "Cato", None),
    ("Cato Reed2-Park", "Cato", None),
    ("Cato Luis Reed-Park", "Cato", None),
    ("Dena Reed-Park", "Cato", None),
])
def test_component_split_treats_only_internal_hyphens_as_joiners(text, prefix, remainder):
    assert prefix_remainder(text, prefix) == remainder


@pytest.mark.parametrize("name,surname,count", [
    ("Cato Luis Reed", "Reed", 4),
    ("Cato Luis Evan Reed", "Reed", 4),
    ("Cato Reed Park", "Park", 4),
    ("Cato von Reed", "von Reed", 7),
    ("Cato van der Reed", "van der Reed", 10),
    ("Cato Luis de la Reed-Park", "de la Reed-Park", 12),
    ("Cato Élise van Reed", "van Reed", 7),
    ("Cato Luis Von Reed", "Reed", 4),
    ("Cato quor Reed", "quor Reed", 8),
    ("Cato\tLuis  van\tder  Reed\u2011Park", "van\tder  Reed\u2011Park", 14),
])
@pytest.mark.parametrize("anchor_first", [False, True])
def test_capitalization_convention_retains_prefixes_and_excludes_middle_names(project, name, surname, count, anchor_first):
    anchor = f"Cato's full name is {name}. "
    comparisons = COMPARISON + HYPOTHETICAL
    result = solve((anchor + comparisons if anchor_first else comparisons + anchor) + QUESTION,
                   project.registry)
    assert result.value == 2 * count + 1, result.answer
    assert not result.deficiencies()
    values = {(v.entity, v.owner): v.text for v in result.store.by_kind(TextValue)}
    assert values[("full name", "cato")] == name
    assert values[("last name", "cato")] == surname
    split = result.store.by_kind(TextPrefixSplit)[0]
    assert split.layout == "capitalized-tail"
    step = next(step for step in result.answer.proof.steps if step.rule == "explicit-prefix-split")
    assert "Capitalization convention" in step.detail
    assert repr(surname) in step.detail
    literal_units = [u for r in result.premises for u in r.units if u.features.get("literal_text")]
    assert literal_units
    assert all(u.sense() == "literal" and not u.obligations() for u in literal_units)


@pytest.mark.parametrize("name", [
    "Cato", "Cato von", "Cato von reed", "cato Luis Reed",
    "Cato von Luis Reed", "Cato de Luis van Reed", "Dena Luis Reed",
    "Cato Luis- Reed", "Cato Luis Reed-", "Cato 3 Reed",
    "Cato Luis, Reed", "Cato von Reed and Aven", "Cato von Reed with 3 apples",
])
def test_invalid_capitalization_layout_does_not_bind_or_license_unknown_words(project, name):
    result = solve(f"Cato's full name is {name}. How many letters are in Cato's last name?",
                   project.registry)
    assert not result.answer.committed, result.answer
    assert not result.store.by_kind(TextPrefixSplit)
    assert not any(u.features.get("literal_text") for r in result.premises for u in r.units)


def test_literal_prefix_does_not_expand_vocabulary_elsewhere(project):
    result = solve("Cato's full name is Cato quor Reed. Aven has 3 quor. "
                   "How many letters are in Cato's last name?", project.registry)
    assert not result.answer.committed
    assert not result.premises[0].unknown_words()
    assert "quor" in result.premises[1].unknown_words()
    assert not project.registry.word_in_category("quor", "name")


def test_equal_length_but_different_prefixed_surnames_still_conflict(project):
    result = solve("Cato's full name is Cato van Reed. Cato's last name is Van Reed. "
                   "How many letters are in Cato's last name?", project.registry)
    assert not result.answer.committed
    assert result.store.collisions


def test_abbreviated_middle_initial_cannot_discard_the_rest_of_the_name(project):
    # The existing sentence splitter treats the period as a boundary. The
    # unread following fragment must still prevent a partial-name answer.
    result = solve("Cato's full name is Cato L. Reed. How many letters are in Cato's last name?",
                   project.registry)
    assert not result.answer.committed


def test_default_component_layout_does_not_acquire_capitalization_semantics():
    assert prefix_remainder("Cato Luis Reed", "Cato") is None
    assert prefix_remainder("Cato Luis Reed", "Cato", "capitalized-tail") == "Reed"
    assert prefix_remainder("Cato von Reed", "Cato", "capitalized-tail") == "von Reed"
    assert prefix_remainder("Cato Reed", "Cato", "unregistered") is None


@pytest.mark.parametrize("spec", [
    {"text": "missing", "prefix": "owner"},
    {"text": "text", "prefix": "missing"},
    {"text": "text", "prefix": "text"},
    {"text": "text", "prefix": "owner", "prefix_attr": "owner"},
])
def test_text_split_predicate_rejects_invalid_slot_contracts(spec):
    from pathlib import Path
    from rulekit.data.packs import LoadedPack
    from rulekit.data.registry import CompileError, compile_registry
    from rulekit.data.schemas import PackDoc, RulesDoc

    rules = RulesDoc.model_validate({"format": "rulekit/rules@1", "rules": [{
        "id": "test/text-split", "match": {"sentence": [
            {"slot": "text", "span": True}, {"slot": "owner", "span": True},
        ]}, "where": [{"text_prefix_split": spec}],
    }]})
    pack = LoadedPack("test", Path("."), PackDoc(format="rulekit/pack@1", name="test"), rules=[rules])
    with pytest.raises(CompileError, match="text split"):
        compile_registry([pack])


def test_text_split_predicate_rejects_unknown_layout_at_schema_boundary():
    from pydantic import ValidationError
    from rulekit.data.schemas import WherePredicate

    with pytest.raises(ValidationError):
        WherePredicate(text_prefix_split={"text": "text", "prefix": "owner", "layout": "guess"})
