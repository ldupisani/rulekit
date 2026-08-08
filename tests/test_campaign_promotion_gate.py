"""M4 promotion evidence is exact, bounded, and append-only."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from rulekit.cli import main as cli_main
from rulekit.generation import (
    CampaignAnswerEvidence,
    CampaignCandidateManifest,
    CampaignClassEvidence,
    CampaignConstitutionEvidence,
    CampaignGenerationContract,
    CampaignImplementationContract,
    CampaignPromotionGate,
    CampaignSpecimen,
    CampaignSpecimenReplay,
    CampaignStandingGateResult,
    append_campaign_gate,
    campaign_gate_path,
    campaign_trace_diff,
    campaign_trace_evidence,
    latest_campaign_gate,
    read_campaign_gates,
)
from rulekit.server.candidate_runner import PromotionRuntime
from rulekit.server.promotion_gate import run_campaign_promotion_gate


def _trace_payload() -> dict:
    return {
        "error": None,
        "sentences": [
            {
                "index": 0,
                "machine_matches": [
                    {
                        "rule_id": "invented/holding",
                        "bindings": {"holder": "keeper"},
                        "consumed": [0, 1, 2],
                        "shadowed": False,
                    }
                ],
            }
        ],
        "facts": [
            {
                "type": "InventedQuantity",
                "fields": {"entity": "keeper", "value": 4},
                "source": "invented/holding",
                "sentence": 0,
                "source_ref": {"path": "/checkout/rules.yaml"},
                "derivation": {"checkout_specific": True},
            }
        ],
        "collisions": [],
        "deficiencies": [],
        "ask": {
            "id": "ask/invented-holder",
            "query": {"entity": "keeper"},
            "source_ref": {"path": "/checkout/asks.yaml"},
        },
        "answer": {
            "kind": "number",
            "value": 4,
            "reason": "one exact quantity",
            "committed": True,
            "clarification": None,
        },
        "semantic": {
            "proof": {
                "steps": [{"rule": "invented/holding"}],
                "source_ref": {"path": "/checkout/rules.yaml"},
            }
        },
    }


def test_trace_projection_covers_every_machine_promotion_surface() -> None:
    evidence = campaign_trace_evidence(_trace_payload())

    assert evidence.matches[0].rule_id == "invented/holding"
    assert evidence.facts[0].fields == {"entity": "keeper", "value": 4}
    assert evidence.facts[0].source_ref is None
    assert evidence.ask is not None and evidence.ask.id == "ask/invented-holder"
    assert evidence.answer.shape == "number"
    assert evidence.answer.committed is True
    assert evidence.proof == {"steps": [{"rule": "invented/holding"}]}


@pytest.mark.parametrize(
    ("section", "mutate"),
    [
        ("matches", lambda value: value.matches.clear()),
        ("facts", lambda value: value.facts.clear()),
        ("collisions", lambda value: value.collisions.append({"key": ["x"]})),
        ("deficiencies", lambda value: value.deficiencies.append("missing evidence")),
        ("ask", lambda value: setattr(value, "ask", None)),
        ("answer", lambda value: setattr(value.answer, "value", 5)),
        ("proof", lambda value: setattr(value, "proof", None)),
    ],
)
def test_trace_diff_names_each_changed_surface(section, mutate) -> None:
    expected = campaign_trace_evidence(_trace_payload())
    actual = expected.model_copy(deep=True)
    mutate(actual)

    changed = [name for name, item in campaign_trace_diff(expected, actual).items() if not item.same]

    assert changed == [section]


def _project(tmp_path: Path):
    return SimpleNamespace(
        root=tmp_path,
        doc=SimpleNamespace(name="invented-campaign"),
    )


def _gate(*, passed: bool = True) -> CampaignPromotionGate:
    return CampaignPromotionGate(
        candidate_id="holder-question",
        candidate_commit="abcdef1",
        registry_fingerprint="registry-abcdef0123456789",
        baseline_commit="1234567",
        passed=passed,
        specimens=[
            CampaignSpecimenReplay(
                specimen_id="strict-positive",
                passed=passed,
            )
        ],
        reviews=[],
        standing=[
            CampaignStandingGateResult(
                id="synthetic-full",
                kind="synthetic",
                passed=passed,
            )
        ],
    )


def test_gate_records_are_fixed_path_append_only_and_exact_revision_pinned(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    first = append_campaign_gate(project, _gate(passed=False))
    second = append_campaign_gate(project, _gate(passed=True))

    assert campaign_gate_path(project) == (
        tmp_path / "generation" / "campaign" / "gates.jsonl"
    )
    assert read_campaign_gates(project) == [first, second]
    assert latest_campaign_gate(
        project,
        "holder-question",
        "abcdef1",
        "registry-abcdef0123456789",
    ) == second
    assert latest_campaign_gate(
        project,
        "holder-question",
        "bcdefa2",
        "registry-abcdef0123456789",
    ) is None


def test_gate_cannot_claim_pass_when_a_component_failed() -> None:
    payload = _gate(passed=False).model_dump()
    payload["passed"] = True

    with pytest.raises(ValidationError, match="pass must match every component"):
        CampaignPromotionGate.model_validate(payload)


def test_campaign_trace_cli_reuses_the_designer_canonicalizer(capsys) -> None:
    exit_code = cli_main(
        [
            "--project",
            "projects/curated",
            "campaign-trace",
            "The keeper had 4 lanterns.",
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"answer"' in captured.out
    assert '"matches"' in captured.out


def test_promotion_gate_accepts_the_published_durable_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace = campaign_trace_evidence(_trace_payload())
    manifest = CampaignCandidateManifest(
        candidate_id="holder-question",
        class_name="Exact holder quantity questions",
        branch="mining/cand-holder-question",
        commit="abcdef1",
        registry_fingerprint="registry-abcdef0123456789",
        mechanism="One declared holding premise and exact-holder ask.",
        class_evidence=CampaignClassEvidence(
            pool_frequency=1,
            expected_solved=1,
            walked_item_ids=["dev-invented-1"],
            premise_mechanism="A holding premise emits one quantity.",
            ask_mechanism="An exact-holder ask selects that quantity.",
            structural_summary=["One invented item exercises the gate boundary."],
        ),
        generation_contract=CampaignGenerationContract(
            premise_rules=["invented/holding"],
            ask_rules=["ask/invented-holder"],
            required_specimen_kinds=["answerable"],
        ),
        implementation_contract=CampaignImplementationContract(
            files_expected=["packs/invented/rules.yaml"],
            synthetic_tests=["tests/test_invented_holder.py"],
            class_justification="The fixture exercises published evidence.",
        ),
        constitution_review=CampaignConstitutionEvidence(
            verdict="pass",
            notes="Read-only review passed.",
        ),
        specimens=[
            CampaignSpecimen(
                id="answerable",
                kind="answerable",
                title="Complete question",
                sentence="The keeper had 4 lanterns.",
                expectation="The existing trace remains exact.",
                actual_rule_ids=["invented/holding"],
                answer=CampaignAnswerEvidence(
                    kind="number",
                    value=4,
                    reason="one exact quantity",
                ),
                trace=trace,
            )
        ],
    )
    published = {
        **manifest.model_dump(),
        "project": "invented-campaign",
        "published_at": "2026-08-08T15:41:32+00:00",
    }
    runtime = PromotionRuntime(
        root=tmp_path,
        commit="abcdef1",
        python=tmp_path / "python",
        rulekit=tmp_path / "rulekit",
    )
    monkeypatch.setattr(
        "rulekit.server.promotion_gate.STANDING_SPECS",
        (),
    )
    monkeypatch.setattr(
        "rulekit.server.promotion_gate.relevant_campaign_reviews",
        lambda project, candidate: ([], []),
    )
    monkeypatch.setattr(
        "rulekit.server.promotion_gate._protected_digest",
        lambda roots: {},
    )
    monkeypatch.setattr(
        "rulekit.server.promotion_gate._run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "ok", ""),
    )

    gate = run_campaign_promotion_gate(
        _project(tmp_path),
        published,
        runtime,
        runtime,
        lambda text, interpretation, reference_year: _trace_payload(),
    )

    assert gate.passed is True
    assert gate.candidate_id == manifest.candidate_id
