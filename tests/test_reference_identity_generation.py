"""Existing generation targets keep the same lossless reader/query contract."""
import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.ask_generation import generate_ask_scenario
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", params=("curated", "gsm8k"))
def project(request):
    return load_project(ROOT / "projects" / request.param)


@pytest.mark.parametrize("rule", (
    "arithmetic/anchored-relation", "arithmetic/stated-possessed-location-content",
))
def test_premise_round_trip(project, rule):
    candidate = generate_candidate(project, rule_id=rule, seed=17)
    assert candidate.target_status == "matched"
    assert rule in {match.rule_id for match in candidate.actual_matches}
    assert candidate.facts
    for fact in candidate.facts:
        for role in ("entity_ref", "subject_ref", "standard_ref"):
            if role in fact["fields"]:
                assert isinstance(fact["fields"][role], dict)
    json.dumps(candidate.to_json())


@pytest.mark.parametrize("ask", (
    "ask/how-many-entity", "ask/how-many-entity-common-noun",
    "ask/how-many-entity-qualified", "ask/how-many-entity-possessed",
    "ask/how-many-container-content-state", "ask/how-many-in-owned-place",
))
def test_ask_round_trip_preserves_structured_reference(project, ask):
    candidate = generate_ask_scenario(project, ask_id=ask, seed=17)
    result = solve(candidate.text, project.registry)
    matched = match_ask(result.question, project.registry)
    assert matched is not None and matched[0].id == ask
    reference = matched[1]["evidence_entity_reference"]
    assert reference["head"] and reference["resolved"]
    assert candidate.query["evidence_entity_reference"] == reference
    json.dumps(candidate.to_json())
