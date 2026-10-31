"""Invented inventories, process partitions, measured uses and period balances."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import analyze, solve


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.fixture(scope="module")
def registry(project):
    return project.registry


def number(text, registry, expected):
    result = solve(text, registry)
    assert result.answer.committed, result.answer.reason
    assert result.value == pytest.approx(expected)
    assert result.deficiencies() == []
    return result


def inventory():
    return ("There are 12 roses in a garden. There are 18 tulips. There are 30 daisies. "
            "What percentage of the flowers are not roses?")


@pytest.mark.parametrize("before,after,expected", [
    ("percentage", "percentage", 80), ("percentage", "percent", 80),
    ("are not roses", "are roses", 20),
    ("in a garden", "at a park", 80),
])
def test_document_local_category_inventory(registry, before, after, expected):
    number(inventory().replace(before, after), registry, expected)


def test_category_inventory_is_not_a_flower_solver(registry):
    number("There are 2 cats in a garden. There are 3 dogs. There are 5 birds. "
           "What percentage of animals are not cats?", registry, 80)


def test_explicit_category_total_does_not_require_all_subtypes(registry):
    number("There are 80 flowers in a garden. There are 20 roses. "
           "What percentage of the flowers are not roses?", registry, 75)


def test_category_inventory_reuses_folded_possession_states(registry):
    number("Fia has 12 roses. Fia has 18 tulips. Fia has 30 daisies. "
           "What percentage of the flowers are not roses?", registry, 80)


@pytest.mark.parametrize("before,after", [
    ("There are 18 tulips. There are 30 daisies. ", ""),
    ("There are 18 tulips.", "There are 18 tulips in a park."),
    ("18 tulips", "18 rocks"), ("18 tulips", "18 roses"),
    ("12 roses", "12 red roses"), ("12 roses", "12.5 roses"),
    ("There are 30 daisies.", "There are 30 daisies. Fia bought 2 roses."),
])
def test_inventory_does_not_merge_unstated_or_conflicting_populations(registry, before, after):
    assert not solve(inventory().replace(before, after), registry).answer.committed


def process():
    return ("Fia's project was divided into three parts. "
            "She finished the first part of her project in 20 minutes. "
            "It took her three times as long to finish the second part. "
            "If she was able to finish her project in 3 hours, "
            "how many minutes did Fia finish the third part of the project?")


@pytest.mark.parametrize("before,after", [
    ("project", "project"), ("project", "assignment"), ("project", "task"),
    ("finish the third", "spend on the third"),
    ("3 hours", "180 minutes"),
    ("was able to finish", "finished"),
])
def test_process_duration_partition_and_paraphrases(registry, before, after):
    number(process().replace(before, after), registry, 100)


@pytest.mark.parametrize("numeric_indices", [False, True])
@pytest.mark.parametrize("unit,expected", [("minutes", 100), ("seconds", 6000), ("hours", 5 / 3)])
def test_fronted_elapsed_duration_question_reuses_the_process_partition(registry, numeric_indices, unit, expected):
    text = process().replace("was able to finish", "finished").replace(
        "how many minutes", f"in how many {unit}")
    if numeric_indices:
        text = text.replace("first part", "1st part").replace("second part", "2nd part").replace("third part", "3rd part")
    result = number(text, registry, expected)
    assert [reading.text for reading in result.assumptions] == ["she finished her project in 3 hours."]


def test_fronted_elapsed_duration_question_supports_an_organization(registry):
    number("The company's task was divided into three parts. "
           "The company finished the first part in 15 minutes. "
           "The company finished the second part in 20 minutes. "
           "The company finished the task in 1 hour. "
           "In how many minutes did the company finish the third part?", registry, 25)


@pytest.mark.parametrize("before,after", [
    ("was able to finish", "could finish"),
    ("was able to finish", "can finish"),
    ("was able to finish", "might finish"),
    ("was able to finish", "could have finished"),
    ("was able to finish", "did not finish"),
    ("3 hours", "at most 3 hours"),
    ("3 hours", "at least 3 hours"),
    ("3 hours", "less than 3 hours"),
    ("in how many minutes", "in how many meters"),
    ("in how many minutes", "after how many minutes"),
    ("in how many minutes", "in how many minute"),
    ("in how many minutes did Fia finish", "in how many minutes did Fia spend on"),
])
def test_fronted_duration_query_does_not_invent_exact_elapsed_time(registry, before, after):
    text = process().replace("how many minutes", "in how many minutes").replace(before, after)
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize("opening", ["was divided into", "had", "has"])
@pytest.mark.parametrize("part", ["third", "3rd"])
@pytest.mark.parametrize("unit,expected,measure", [("", 100, "minute"),
    (" in seconds", 6000, "seconds"), (", in hours,", 5 / 3, "hour")])
def test_elapsed_time_question_with_optional_output_unit(registry, opening, part, unit, expected, measure):
    text = process().replace("was divided into", opening).replace("was able to finish", "finished").replace(
        "how many minutes did Fia finish the third", f"how long{unit} did Fia take to finish the {part}")
    result = number(text, registry, expected)
    assert dict(result.answer.proof.query.fields)["measure"] == measure


def test_owned_process_part_count_is_not_limited_to_schoolwork(registry):
    number("The company's task had three parts. "
           "The company finished the first part in 2 hours. "
           "The company finished the second part in 30 minutes. "
           "The company finished the task in 180 minutes. "
           "How long did the company take to finish the third part?", registry, 0.5)


@pytest.mark.parametrize("actor,possessor", [("Fia", "Fia's"), ("The company", "The company's")])
@pytest.mark.parametrize("part", ["first", "second", "third", "1st", "2nd", "3rd"])
def test_elapsed_time_can_ask_for_any_part_with_either_ordinal_form(registry, actor, possessor, part):
    indices = ["first", "second", "third"]
    index = indices.index(part) if part in indices else int(part[0]) - 1
    durations = [20, 60, 100]
    known = " ".join(f"{actor} finished the {word} part in {duration} minutes."
                     for i, (word, duration) in enumerate(zip(indices, durations)) if i != index)
    text = (f"{possessor} task had three parts. {known} "
            f"{actor} finished the task in 3 hours. "
            f"How long did {actor} take to finish the {part} part?")
    number(text, registry, durations[index])


def test_elapsed_duration_uses_declared_conversion_paths(registry):
    text = process().replace("20 minutes", "1 day").replace("3 hours", "1 week").replace(
        "how many minutes did Fia finish", "how long did Fia take to finish")
    number(text, registry, 3)
    assert not solve(text.replace("1 week", "1 month"), registry).answer.committed


def test_possessed_process_parts_are_generatable(project):
    candidate = generate_candidate(project, rule_id="arithmetic/process-parts-possession", seed=0)
    assert candidate.target_status == "matched"
    assert len(candidate.facts) == 1


@pytest.mark.parametrize("before,after", [
    ("had three parts", "could have three parts"),
    ("had three parts", "had at least three parts"),
    ("had three parts", "did not have three parts"),
    ("had three parts", "had three overlapping parts"),
    ("had three parts", "had three parts remaining"),
    ("had three parts", "had three tasks"),
    ("Fia's project had", "Cato's project had"),
    ("Fia's project had", "Fia's house had"),
    ("finished her project", "could finish her project"),
    ("the third part of the project", "the third part of the assignment"),
    ("how long did Fia take", "how far did Fia take"),
    ("how long did Fia take", "how long did Cato take"),
    ("how long", "how long in meters"),
    ("how long", "how long in minute"),
    ("how long did Fia", "how long do Fia"),
    ("take to finish", "took to finish"),
    ("take to finish", "take to finished"),
])
def test_elapsed_time_and_part_count_need_exact_compatible_evidence(registry, before, after):
    text = process().replace("was divided into", "had").replace("was able to finish", "finished").replace(
        "how many minutes did Fia finish", "how long did Fia take to finish")
    assert not solve(text.replace(before, after), registry).answer.committed


def test_four_part_process_and_duration_conversion(registry):
    text = process().replace("three parts", "four parts").replace(
        "If she was able", "She finished the third part in 30 minutes. If she was able").replace(
        "did Fia finish the third", "did Fia finish the fourth")
    number(text, registry, 70)


@pytest.mark.parametrize("ask", ["finish", "spend on"])
def test_numeric_and_word_ordinals_share_process_indices(registry, ask):
    text = process().replace("first", "1st").replace("second", "2nd").replace("third", "3rd")
    number(text.replace("did Fia finish", "did Fia " + ask), registry, 100)


def test_process_duration_partition_supports_an_organization(registry):
    number("The company's task was divided into three parts. "
           "The company finished the first part in 15 minutes. "
           "The company finished the second part in 20 minutes. "
           "The company finished the task in 1 hour. "
           "How many minutes did the company spend on the third part?", registry, 25)


def test_any_single_process_part_can_be_unknown(registry):
    number("Fia's task was divided into three parts. "
           "She finished the second part in 15 minutes. "
           "It took her twice as long to finish the third part. "
           "She finished her task in 1 hour. "
           "How many minutes did Fia spend on the first part?", registry, 15)


@pytest.mark.parametrize("before,after", [
    ("three parts", "four parts"), ("3 hours", "1 hour"),
    ("It took her", "It took him"),
    ("third part of the project?", "third part of the assignment?"),
    ("her project in 20", "her assignment in 20"),
    ("second part.", "first part."),
    ("She finished", "Cato finished"),
    ("the first part", "Cato's first part"),
])
def test_process_partition_requires_one_exhaustive_compatible_process(registry, before, after):
    assert not solve(process().replace(before, after), registry).answer.committed


def resource():
    return ("Dena bought 12 kilograms of clay to make models. "
            "She used one-half of it for red models, one-fourth of it for blue models, "
            "and one-third of the remaining clay for green models. "
            "How many kilograms of clay are left after making those three kinds of models?")


@pytest.mark.parametrize("before,after,expected", [
    ("clay", "clay", 2), ("bought", "received", 2),
    ("one-half", "1/2", 2),
    ("one-fourth of it", "one-fourth of the remaining clay", 3),
    ("after making those three kinds of models", "", 2),
    ("kilograms of clay are left", "grams of clay are left", 2000),
])
def test_fractional_resource_uses_keep_original_and_remaining_bases(registry, before, after, expected):
    number(resource().replace(before, after), registry, expected)


def test_fractional_use_can_describe_food_and_volume(registry):
    number(resource().replace("clay", "butter").replace("models", "cookies"), registry, 2)
    number(resource().replace("kilograms", "liters").replace("clay", "foam"), registry, 2)


@pytest.mark.parametrize("before,after", [
    ("one-fourth of it", "three-fourths of it"),
    ("remaining clay", "remaining butter"),
    ("three kinds", "four kinds"), ("green models", "blue models"),
    ("She used", "Cato used"),
    ("kilograms of clay are left", "meters of clay are left"),
])
def test_fractional_uses_require_consistent_resource_identity_and_budget(registry, before, after):
    assert not solve(resource().replace(before, after), registry).answer.committed


def population():
    return ("A teacher wants to find out the average daily allowance of the workers. "
            "According to her survey, half of the workers receive an average of $8 per day "
            "while the rest gets an average of $5 a day. "
            "If she surveyed 48 workers, what is the total amount of money those 48 workers get in a day?")


@pytest.mark.parametrize("before,after", [
    ("half", "half"), ("half", "1/2"), ("half", "50%"),
    ("workers", "students"), ("find out", "find"),
    ("while", "and"), (" a day.", " per day."),
])
def test_subgroup_average_rates_weight_by_member_counts(registry, before, after):
    number(population().replace(before, after), registry, 312)


def test_average_rates_do_not_need_an_inquiry_introduction(registry):
    number("Fia surveyed 48 workers. Half of the workers receive an average of $8 per day "
           "while the rest gets an average of $5 a day. "
           "What is the total amount of money those 48 workers get in a day?", registry, 312)


def test_population_rate_money_question_and_other_period(registry):
    text = population().replace("daily", "").replace("day", "hour")
    text = text.replace("what is the total amount of money those 48 workers get in a hour?",
                        "how much money do those 48 workers receive per hour?")
    number(text, registry, 312)


def test_reported_per_member_rates_support_device_recipients(registry):
    number("Fia surveyed 12 machines. Half of the machines receive an average of $8 per hour "
           "while the rest gets an average of $5 an hour. "
           "How much money do those 12 machines receive per hour?", registry, 78)


@pytest.mark.parametrize("before,after", [
    ("half", "2/5"), ("half", "120%"), ("half", "0%"), ("half", "100%"),
    ("those 48", "those 50"), ("48 workers,", "48 students,"),
    ("those 48 workers", "those 48 young workers"),
    ("her survey", "his survey"),
    ("while the rest gets an average of $5 a day", ""),
    ("daily", ""),
])
def test_population_partition_boundaries(registry, before, after):
    text = population().replace(before, after)
    if before == "daily":
        # Without an inquiry frequency this remains explicit in both reported rates.
        number(text, registry, 312)
    else:
        assert not solve(text, registry).answer.committed


def test_large_populations_still_require_whole_subgroups(registry):
    text = population().replace("48", "48000000000001").replace("half", "2/3")
    assert not solve(text, registry).answer.committed


def collections():
    return ("Every hour Fia has to collect the marbles out of the box inside the house. "
            "During the first hour, she collected 10 marbles. "
            "For the next two hours, she collected 20 marbles in total from the box. "
            "In the fourth hour, she collected 30 marbles from the box but she gave 5 of them "
            "to her coworker so she could buy a book. "
            "How many marbles did she have after the fourth hour?")


@pytest.mark.parametrize("before,after,expected", [
    ("marbles", "marbles", 55), ("marbles", "coins", 55),
    ("For the next", "Over the next", 55),
    ("20 marbles in total from", "20 marbles per hour from", 75),
    (" so she could buy a book", "", 55),
    (" but she gave 5 of them to her coworker so she could buy a book", "", 60),
])
def test_period_acquisition_blocks_and_actual_transfers(registry, before, after, expected):
    number(collections().replace(before, after), registry, expected)


def test_periodic_ledger_can_stand_without_a_duty_introduction(registry):
    text = collections().split(". ", 1)[1].replace("she", "Fia", 1)
    number(text, registry, 55)


def test_period_balances_reuse_information_acquisition_roles(registry):
    text = collections().split(". ", 1)[1].replace("she", "Fia", 1)
    text = text.replace("collected", "downloaded").replace(" from the box", "").replace(
        " so she could buy a book", "")
    number(text.replace("marbles", "files"), registry, 55)
    assert not solve(text, registry).answer.committed


def test_unscoped_multi_period_amount_requires_confirmation(registry):
    text = collections().replace("20 marbles in total", "20 marbles")
    result = solve(text, registry)
    assert not result.answer.committed
    assert result.deficiencies() == []
    assert result.answer.clarification is not None
    assert {o.id for o in result.answer.clarification.options} == {"block-total", "per-period"}
    for interpretation, expected in [("block-total", 55), ("per-period", 75)]:
        result = solve(text, registry, interpretation=interpretation)
        assert result.value == expected, result.answer
        assert result.deficiencies() == []
        assert result.answer.clarification.selected == interpretation
    assert not solve(text, registry, interpretation="unsupported").answer.committed


def test_confirmation_cannot_override_an_explicit_scope_or_invalid_evidence(registry):
    assert solve(collections(), registry, interpretation="per-period").value == 55
    text = collections().replace("20 marbles in total", "20 marbles").replace("5 of them", "35 of them")
    assert not solve(text, registry, interpretation="per-period").answer.committed


@pytest.mark.parametrize("before,after", [
    ("first hour", "second hour"), ("fourth hour", "fifth hour"),
    ("two hours", "1.5 hours"), ("5 of them", "35 of them"),
    ("30 marbles", "30 coins"), ("from the box", "from the fountain"),
    ("but she gave", "but Cato gave"),
    ("the first hour", "Cato's first hour"),
    ("so she could buy a book", "so she bought a book"),
])
def test_period_ledger_declines_gaps_unbound_transfers_and_unread_transactions(registry, before, after):
    assert not solve(collections().replace(before, after), registry).answer.committed


def test_declared_ordinals_do_not_turn_partitive_fractions_into_indices(registry):
    for text, ordinal in [("the third part", "third"), ("the fourth hour", "fourth")]:
        reading = analyze(text, registry)
        unit = next(u for u in reading.units if u.sense() == "noun")
        assert unit.features.get("qualifier") == ordinal
    reading = analyze("She used one-third of the butter.", registry)
    assert any(u.features.get("value_kind") == "fraction" and u.features.get("value") == pytest.approx(1/3)
               for u in reading.units)


@pytest.mark.parametrize("form", ["she", "her", "he", "his", "him"])
def test_common_noun_antecedents_respect_reference_number(registry, form):
    from rulekit.kernel.document import _animate_candidates
    readings = [analyze("A teacher surveyed 48 workers.", registry, 0)]
    pronoun = analyze(form, registry).units[0]
    candidates = _animate_candidates(readings, 1, registry, pronoun)
    assert {ref.head for ref in candidates} == {"teacher"}


def test_common_noun_antecedents_do_not_choose_between_two_singular_people(registry):
    from rulekit.kernel.document import _animate_candidates
    readings = [analyze("A teacher has a friend.", registry, 0)]
    pronoun = analyze("she", registry).units[0]
    assert len(_animate_candidates(readings, 1, registry, pronoun)) == 2


def test_counted_modifiers_keep_their_declared_position_and_numeric_binding(project, registry):
    from rulekit.data.schemas import MatchToken
    from rulekit.generation.sample import _counted_qualified_fillers, _domain, _load_fixtures
    temporal = _counted_qualified_fillers(registry, head_category="duration_measure",
                                        modifier_category="adjacent_interval_descriptor")
    assert temporal
    for filler in temporal:
        assert filler.surface.startswith("next ")
        reading = analyze(filler.surface, registry)
        units = [u for u in reading.units if u.features.get("value_kind") == "count"]
        assert len(units) == 1
        assert units[0].features.get("value") == filler.value
        assert units[0].features.get("qualifier") == filler.qualifier
    colored = _counted_qualified_fillers(registry, head_category="ownable_quantity_object",
                                       modifier_category="color_attribute")
    assert colored
    assert all(f.surface.split()[0].isdigit() for f in colored)
    referenced = _domain(MatchToken(slot="period", cat="duration_measure", counted=True,
                                   qualified=True, qualifier_cat="adjacent_interval_descriptor",
                                   referential=True, value_min=2), registry, _load_fixtures(project.root))
    assert referenced
    assert all(f.value is not None and f.value >= 2 for f in referenced)


@pytest.mark.parametrize("rule_id", [
    "arithmetic/fractional-resource-use", "arithmetic/fractional-resource-remainder-use",
    "arithmetic/process-relative-part-duration", "arithmetic/periodic-resource-successive-gain",
    "arithmetic/periodic-resource-successive-rate", "arithmetic/periodic-resource-successive-total",
])
def test_context_dependent_generation_round_trips_with_supporting_evidence(project, rule_id):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(project, rule_id=rule_id, seed=4500)
    assert candidate.target_status == "matched"
    assert candidate.context_before
    assert candidate.target_sentence_index == len(candidate.context_before)


def test_evidence_generation_preserves_an_explicit_task_reference(project):
    import random
    from rulekit.generation import generate_candidate
    from rulekit.generation.ask_generation import _emit_feature_surface_locks, _emit_lock_variants
    rule = next(r for r in project.registry.rules if r.id == "arithmetic/task-completion-duration")
    query = {"participant": "fia", "task": "puzzle", "verb": "finish", "unit": "minute"}
    _score, identities = _emit_lock_variants(rule, query)[0]
    surfaces = _emit_feature_surface_locks(project, rule, query, identities, random.Random(901))
    assert "task" in surfaces
    candidate = generate_candidate(project, rule_id=rule.id, seed=901,
                                   identity_bindings=identities, locked_bindings=surfaces)
    assert candidate.target_status == "matched"
    assert any(f["fields"].get("task") == "puzzle" for f in candidate.facts)


@pytest.mark.parametrize("front", [
    "What is the total amount of money those 48 workers get",
    "How much money do those 48 workers receive",
])
@pytest.mark.parametrize("period", ["per day", "each day", "every day", "a day", "in a day"])
def test_population_total_questions_share_period_wording(registry, front, period):
    premises = population().split("what is", 1)[0]
    number(premises + f"{front} {period}?", registry, 312)


def test_qualified_population_and_unattributed_rates_compose(registry):
    text = population().replace("of the workers", "of farm workers", 1)
    text = text.replace("According to her survey, half", "Half")
    text = text.replace("get in a day?", "get per day?")
    result = number(text, registry, 312)
    assert any(getattr(f, "kind", None) == "population-rate-inquiry"
               and f.container_ref.qualifiers == ("farm",) for f in result.facts())


@pytest.mark.parametrize("period,expected", [("per hour", 78), ("each hour", 78), ("every hour", 78),
                                            ("an hour", 78), ("in an hour", 78), ("per day", 1872)])
def test_other_recipients_and_converted_periods_use_the_same_total(registry, period, expected):
    text = ("Fia surveyed 12 machines. Half of the machines receive an average of $8 per hour "
            "while the rest gets an average of $5 an hour. "
            f"What is the total amount of money those 12 machines get {period}?")
    number(text, registry, expected)


def test_population_rate_total_can_request_a_larger_period(registry):
    number(population().replace("get in a day?", "get per week?"), registry, 2184)


@pytest.mark.parametrize("ending", [
    "in per day", "per a day", "per the day", "each a day", "in the a day",
    "per meter", "per two days", "per day and per hour", "per day at the end", "",
])
def test_population_period_questions_reject_incomplete_or_conflicting_bases(registry, ending):
    text = population().replace("get in a day?", f"get {ending}?")
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize("change", [
    ("those 48 workers", "those 50 workers"),
    ("those 48 workers", "those 48 students"),
    ("those 48 workers", "those 48 farm workers"),
    ("48 workers,", "48 students,"),
    ("half of the workers", "2/5 of the workers"),
    ("while the rest gets an average of $5 a day", ""),
])
def test_rate_wording_preserves_population_and_partition_boundaries(registry, change):
    text = population().replace("get in a day?", "get per day?").replace(*change)
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize("ask_id", [
    "ask/population-total-periodic-amount", "ask/population-total-periodic-amount-rate",
    "ask/population-total-periodic-money", "ask/population-total-periodic-money-interval",
])
def test_population_period_ask_variants_generate_and_round_trip(project, ask_id):
    from rulekit.generation import generate_ask_scenario
    candidate = generate_ask_scenario(project, ask_id=ask_id, seed=307)
    result = solve(candidate.question, project.registry)
    from rulekit.kernel.patterns import match_ask
    matched = match_ask(result.question, project.registry)
    assert matched is not None
    assert matched[0].id == ask_id
    assert matched[1]['consumer'] == 'population-rate-total'
    assert matched[1]['period']


@pytest.mark.parametrize("front", [
    "What is the total amount of money those 48 workers gets per day?",
    "What is the total amounts of money those 48 workers get per day?",
    "How much money does those 48 workers receive per day?",
])
def test_population_period_questions_require_number_agreement(registry, front):
    assert not solve(population().split('what is', 1)[0] + front, registry).answer.committed
