"""A stated change can answer a total and a separate attribution question."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence, MeasuredContentChange


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


TANK = (
    "Nora fills her tank halfway. {loss} "
    "Nora triples the amount of water in the tank. "
    "The tank is 2 feet long, 3 feet wide, and 4 feet high."
)


@pytest.mark.parametrize(("loss", "actor", "cause"), [
    ("Half the water in the tank spilled.", None, None),
    ("Her cat spilled half the water in the tank.", "Her cat", None),
    ("Her cat knocked the tank over, spilling half the water in it.", "Her cat",
     "Her cat knocked the tank over"),
    ("Her cat knocked the tank over, spilling half its water.", "Her cat",
     "Her cat knocked the tank over"),
    ("Her cat dropped the tank, spilling half its water.", "Her cat",
     "Her cat dropped the tank"),
    ("Half the water in the tank spilled because her cat knocked the tank over.", None,
     "her cat knocked the tank over"),
    ("While she's gone, her cat knocks the tank over and spills half the water in it.",
     "her cat", None),
])
def test_same_content_stream_answers_effect_and_attribution(registry, loss, actor, cause):
    story = TANK.format(loss=loss)
    result = solve(story + " How many cubic feet of water are in the tank?", registry)
    assert result.answer.value == pytest.approx(18)
    event, = [f for f in result.store.by_kind(MeasuredContentChange) if f.operation == "remove_fraction"]
    evidence = event.provenance.attribution
    assert evidence.predicate == "spill"
    assert (evidence.reason_span is not None) == (cause is not None)
    assert (evidence.actor is not None) == (actor is not None)
    for question, value in (
        ("Which animal spilled the water?", actor),
        ("What caused the water to spill?", cause),
        ("Who tripled the amount of water?", "Nora"),
    ):
        answer = solve(story + " " + question, registry).answer
        if value is None:
            assert not answer.committed
        else:
            assert answer.kind == "text"
            assert answer.value.casefold() == value.casefold()
            assert answer.proof.steps[0].evidence


@pytest.mark.parametrize("loss", [
    "The cat knocked the tank over.",
    "Half the water in the bucket spilled because the cat knocked the tank over.",
    "Half the water in the tank spilled after the cat knocked the tank over.",
    "Her cat might have spilled half the water in the tank.",
    "Her cat did not spill half the water in the tank.",
])
def test_missing_amount_or_attachment_never_supplies_causal_evidence(registry, loss):
    assert not solve(TANK.format(loss=loss) + " What caused the water to spill?", registry).answer.committed


def test_fractional_loss_amount_is_evaluated_before_scaling(registry):
    text = TANK.format(loss="Her cat spilled half the water in the tank.")
    answer = solve(text + " How many cubic feet of water did the cat spill?", registry).answer
    assert answer.value == pytest.approx(6)
    assert not solve(text + " How many cubic feet of water did the dog spill?", registry).answer.committed


def test_measured_loss_and_cause_are_separate_queries(registry):
    story = (
        "The tank held 20 liters of water. "
        "A valve caused 4 liters of water from the tank to leak out. "
        "Heat caused 3 liters of water from the tank to evaporate. "
    )
    assert solve(story + "How many liters of water remain in the tank?", registry).answer.value == 13
    assert solve(story + "How many liters were lost through the valve?", registry).answer.value == 4
    assert solve(story + "What caused the water to evaporate?", registry).answer.value == "Heat"
    assert not solve(story + "How many liters were lost through the pipe?", registry).answer.committed


def test_repeated_losses_and_restoration_use_distinct_occurrences(registry):
    story = (
        "The tank held 20 liters of water. The cat spilled 4 liters of water from the tank. "
        "The dog spilled 3 liters of water from the tank. The cat spilled 2 liters of water from the tank. "
    )
    assert solve(story + "How many liters remain in the tank?", registry).answer.value == 11
    assert solve(story + "How many liters did the cat spill?", registry).answer.value == 6
    replenished = story + "Nora poured 3 liters of water back into the tank. "
    assert solve(replenished + "How many liters remain in the tank?", registry).answer.value == 14
    assert solve(replenished + "Who poured the water into the tank?", registry).answer.value == "Nora"


def test_actor_loss_question_selects_the_requested_action(registry):
    story = (
        "The tank held 20 liters of water. The cat spilled 4 liters of water from the tank. "
        "A valve caused 3 liters of water from the tank to leak out. "
    )
    assert solve(story + "How many liters did the cat spill?", registry).answer.value == 4


@pytest.mark.parametrize("marker", ["Because of", "Due to"])
def test_room_exclusion_reuses_the_same_fact_for_cause_and_capacity(registry, marker):
    story = (
        "Oren booked a room in a hotel. The hotel has 6 floors with 5 identical rooms on each floor. "
        f"{marker} a leak, the last floor is unavailable for the guests. "
    )
    result = solve(story + "Considering there are no other guests, in how many different rooms could Oren be checked in?", registry)
    assert result.answer.value == 25
    exclusion, = [f for f in result.store.by_kind(BatchEvidence) if f.kind == "available-capacity-exclusion"]
    assert [r.head for r in exclusion.provenance.attribution.reason_entities] == ["leak"]
    assert solve(story + "Why is the last floor unavailable?", registry).answer.value == "a leak"
    assert solve(story + "How many rooms are unavailable because of the leak?", registry).answer.value == 5
    assert not solve(story + "How many rooms are unavailable because of rain?", registry).answer.committed


def test_classification_reason_is_retained_for_an_independent_ask(registry):
    story = "Nora downloaded 300 files and deleted 60% of them because they were irrelevant. "
    assert solve(story + "How many useful files remain?", registry).answer.value == 120
    assert solve(story + "Why did Nora delete the files?", registry).answer.value == "they were irrelevant"
    assert not solve(story.replace(" because they were irrelevant", "") + "Why did Nora delete the files?", registry).answer.committed


@pytest.mark.parametrize(("story", "question", "expected"), [
    ("The hotel has 6 floors with 5 identical rooms on each floor. "
     "Because of both a leak and an electrical fault, the last floor is closed.",
     "How many rooms are unavailable?", 5),
    ("A file of 90 megabytes downloads at the rate of 5 megabytes per second for its first "
     "60 megabytes, and then 10 megabytes per second thereafter. A router reboot paused the transfer for 4 seconds.",
     "How many seconds does it take to download entirely?", 19),
    ("A file of 90 megabytes downloads at the rate of 5 megabytes per second for its first "
     "60 megabytes, and then 10 megabytes per second thereafter. A router reboot paused the transfer for 4 seconds.",
     "How many seconds were spent actively downloading?", 15),
    ("A file of 90 megabytes downloads at the rate of 5 megabytes per second for its first "
     "60 megabytes, and then 10 megabytes per second thereafter. A router reboot paused the transfer for 4 seconds.",
     "How many seconds did the reboot delay the transfer?", 4),
    ("A storm caused 3 trees to collapse. Each following storm would have double the number of "
     "collapsing trees as the previous one.",
     "How many trees would the second storm cause to collapse?", 6),
    ("The conveyor dropped 5 parcels. The robot dropped 3 parcels. The conveyor dropped 2 parcels.",
     "How many parcels did the conveyor drop?", 7),
    ("The conveyor dropped 5 parcels. The robot dropped 3 parcels. The conveyor dropped 2 parcels.",
     "How many parcels were dropped?", 10),
    ("Shawna's daily goal is 30 situps. On Monday, Shawna did 12 situps because she felt ill. "
     "On Tuesday, Shawna did 19 situps.",
     "How many of the missed situps were from the day she felt ill?", 18),
    ("Shawna's daily goal is 30 situps. On Monday, Shawna did 12 situps because she felt ill. "
     "On Tuesday, Shawna did 19 situps.",
     "How many situps would Shawna have to do on Wednesday to meet her goal?", 59),
    ("Nora had 20 meters of wire. Nora cut 5 meters of wire for a repair. Nora discarded 2 meters of wire because of damage.",
     "How long is the remaining wire?", 13),
    ("Nora had 20 meters of wire. Nora cut 5 meters of wire for a repair. Nora discarded 2 meters of wire because of damage.",
     "How much was discarded because of damage?", 2),
    ("Nora collects 2 liters of seawater. The seawater is 20% salt by volume. "
     "Sunlight evaporated all the water from the seawater, leaving all the salt.",
     "How many milliliters of salt were retained?", 400),
    ("Nora collects 2 liters of seawater. The seawater is 20% salt by volume. "
     "Sunlight evaporated all the water from the seawater, leaving all the salt.",
     "What caused the water to evaporate?", "Sunlight"),
    ("Nora downloaded 300 files and deleted 60% of them because they were irrelevant. "
     "She downloaded 200 more files but again realized that 3/4 of them were irrelevant.",
     "How many files were deleted from the first batch for that reason?", 180),
    ("The boat makes 4 trips per day. The boat can take 12 people per trip. Wind canceled one trip on the second day.",
     "How many people can the boat transport in 3 days?", 132),
    ("The boat makes 4 trips per day. The boat can take 12 people per trip. Wind cancelled one trip on the second day.",
     "How much capacity was lost because of wind?", 12),
    ("Lee charges $33 to mow one lawn. Lee mowed 16 lawns. Three customers each gave Lee a $10 tip because of the extra work.",
     "How much did Lee earn mowing lawns?", 558),
    ("Lee charges $33 to mow one lawn. Lee mowed 16 lawns. Three customers each gave Lee a $10 tip because of the extra work.",
     "How much did Lee receive in tips because of the extra work?", 30),
    ("An inspector discards every part that is scratched or bent. Of 100 parts, 10 are scratched, 6 are bent, and 4 are both.",
     "How many parts remain?", 88),
    ("An inspector discards every part that is scratched or bent. Of 100 parts, 10 are scratched, 6 are bent, and 4 are both.",
     "How many were discarded for either defect?", 12),
    ("A repair costs £120. The shop adds a £30 callout fee because of a failure.",
     "How much is the bill?", 150),
    ("A repair costs £120. The shop adds a £30 callout fee because of a failure.",
     "How much of the bill is attributable to the callout?", 30),
    ("A repair costs £120. The shop adds a £30 callout fee because of a failure.",
     "Why did the shop add the fee?", "a failure"),
    ("The container weighs 3 kilograms. Adding clay caused the weight to double.",
     "How much does the container weigh now?", 6),
    ("The container weighs 3 kilograms. Adding clay caused the weight to double.",
     "How much weight did adding clay contribute?", 3),
])
def test_attribution_and_quantity_examples(registry, story, question, expected):
    answer = solve(f"{story} {question}", registry).answer
    assert answer.committed, answer
    assert answer.value == (pytest.approx(expected) if isinstance(expected, int) else expected)


@pytest.mark.parametrize(("story", "question"), [
    ("The tank held 20 liters of water. A cat spilled 4 liters of water from the tank. "
     "A cat spilled 2 liters of water from the tank.",
     "How many liters did the cat spill?"),
    ("The tank held 20 liters of water. The cat spilled 4 liters of water from the tank. "
     "Nora poured 10 liters of water back into the tank.",
     "How many liters remain in the tank?"),
    ("The boat makes 4 trips per day. The boat can take 12 people per trip. Wind canceled one trip on the fourth day.",
     "How many people can the boat transport in 3 days?"),
    ("An inspector discards every part that is scratched or bent. Of 100 parts, 10 are scratched, 6 are bent, and 7 are both.",
     "How many parts remain?"),
    ("Nora collects 2 liters of seawater. The seawater is 20% salt by volume.",
     "How many milliliters of salt were retained?"),
    ("A repair costs £120. The shop adds a £30 callout fee.",
     "How much of the bill is attributable to the delivery?"),
    ("A file of 90 megabytes downloads at the rate of 5 megabytes per second for its first "
     "60 megabytes, and then 10 megabytes per second thereafter. "
     "A router reboot paused the transfer for 4 seconds. A failure paused the transfer for 4 seconds.",
     "How many seconds does it take to download entirely?"),
    ("The jar weighs 3 kilograms. The box weighs 4 kilograms. Adding clay caused the weight to double.",
     "How much weight did adding clay contribute?"),
])
def test_attribution_and_quantity_boundaries(registry, story, question):
    assert not solve(f"{story} {question}", registry).answer.committed


def test_temporal_order_and_unrelated_disturbance_keep_the_same_volume(registry):
    for clause in (
        "Half the water in the tank spilled after her cat knocked the tank over.",
        "The cat knocked over an empty bucket. The cat spilled half the water in the tank.",
    ):
        story = TANK.format(loss=clause)
        assert solve(story + " How many cubic feet of water are in the tank?", registry).answer.value == pytest.approx(18)
        assert not solve(story + " What caused the water to spill?", registry).answer.committed


def test_result_clause_attaches_the_disturbance_without_inventing_a_spill_actor(registry):
    story = TANK.format(loss="Her cat knocked the tank over, so half the water spilled.")
    assert solve(story + " How many cubic feet of water are in the tank?", registry).answer.value == pytest.approx(18)
    assert solve(story + " What caused the water to spill?", registry).answer.value == "Her cat knocked the tank over"
    assert not solve(story + " Which animal spilled the water?", registry).answer.committed


def test_actor_question_distinguishes_an_inflow_destination_from_a_loss(registry):
    story = "The tank held 20 liters of water. The cat spilled 4 liters of water from the tank."
    assert not solve(story + " Who spilled the water into the tank?", registry).answer.committed


def test_repeated_event_count_is_separate_from_amount(registry):
    story = (
        "The tank held 20 liters of water. The cat spilled 4 liters of water from the tank. "
        "The dog spilled 3 liters of water from the tank. The cat spilled 2 liters of water from the tank."
    )
    assert solve(story + " How many times did the cat spill water?", registry).answer.value == 2
