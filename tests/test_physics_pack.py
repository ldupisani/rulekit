"""The reusable physics pack and its DIFG extension boundary."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def curated():
    return load_project(ROOT / "projects" / "curated")


def test_curated_loads_physics_without_the_corpus_mined_pack(curated):
    names = [pack.name for pack in curated.packs]
    assert "physics" in names
    assert "difg-mined" not in names


@pytest.mark.parametrize(
    "question",
    [
        "What is the speed of an object that travels 60 meters in 4 seconds?",
        "What is the speed of an object that took 4 seconds to travel 60 meters?",
    ],
)
def test_speed_binds_operands_by_dimension_in_curated(curated, question):
    result = solve(question, curated.registry)
    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(15.0)


def test_weight_remains_a_second_base_physics_formula(curated):
    result = solve("What is the weight of a 3 kg object on Earth?", curated.registry)
    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(29.4)


def test_momentum_and_compound_velocity_are_reusable_in_curated(curated):
    result = solve(
        "What is the momentum of a 6 kg object moving at 7 m/s?",
        curated.registry,
    )
    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(42.0)


def test_momentum_declines_when_velocity_is_ambiguous(curated):
    result = solve(
        "What is the momentum of a 6 kg object moving at 7 m/s then 9 m/s?",
        curated.registry,
    )
    assert not result.answer.committed


def test_gravitational_potential_energy_is_reusable_in_curated(curated):
    result = solve(
        "What is the gravitational potential energy of a 7 kg object "
        "at a height of 3 meters?",
        curated.registry,
    )
    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(205.8)


def test_shorter_energy_ask_cannot_borrow_the_gravitational_formula(curated):
    result = solve(
        "What is the potential energy of a 7 kg object at a height of 3 meters?",
        curated.registry,
    )
    assert not result.answer.committed


def test_power_from_work_over_time_is_reusable_in_curated(curated):
    result = solve(
        "What is the power if 147 joules of work is done over 7 seconds?",
        curated.registry,
    )
    assert result.answer.committed, result.answer.reason
    assert result.answer.value == pytest.approx(21.0)


def test_difg_manifest_resolves_the_physics_dependency_transitively():
    packs = load_packs(
        [
            ROOT / "packs" / "core-english",
            ROOT / "packs" / "arithmetic",
            ROOT / "packs" / "difg-mined",
        ]
    )
    names = [pack.name for pack in packs]
    assert names == [
        "core-english",
        "arithmetic",
        "physics",
        "chemistry",
        "difg-mined",
    ]
