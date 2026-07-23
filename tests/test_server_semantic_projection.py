"""The designer exposes typed semantic roles and consumer-owned proof steps."""

from pathlib import Path

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask
from rulekit.server.api import _semantic_json


REGISTRY = load_project(Path("projects/scratch")).registry


def test_semantic_projection_cross_links_witness_evidence() -> None:
    result = solve(
        "Nadia is an otter. Every otter is an animal. Nadia has a badge. "
        "Is it true that Some animal has a badge?",
        REGISTRY,
        tracing=False,
    )
    assert result.answer.value == "yes"
    assert result.question is not None
    ask = match_ask(result.question, REGISTRY)
    assert ask is not None

    semantic = _semantic_json(result, ask)
    assert semantic["query"] == {
        "kind": "Existential",
        "fields": {
            "cls": "animal",
            "pred": "have badge",
            "polarity": True,
        },
    }

    facts = semantic["facts"]
    assert any(
        fact["role"] == "observed"
        and fact["representation"] == "exact"
        and fact["fields"].get("pred") == "have badge"
        for fact in facts
    )
    assert any(
        fact["role"] == "observed"
        and fact["representation"] == "structured"
        and fact["type"] == "Quantified"
        for fact in facts
    )
    assert any(
        fact["role"] == "derived"
        and fact["fields"].get("pred") == "animal"
        for fact in facts
    )

    proof = semantic["proof"]
    assert proof is not None
    assert proof["status"] == "proved"
    assert [step["rule"] for step in proof["steps"]] == [
        "existential-introduction",
    ]
    evidence_ids = [fact["id"] for fact in proof["steps"][0]["evidence"]]
    assert len(evidence_ids) == 2
    assert all(evidence_id is not None for evidence_id in evidence_ids)
    assert set(evidence_ids) <= {fact["id"] for fact in facts}


def test_designer_contains_semantic_and_proof_views() -> None:
    root = Path("src/rulekit/server/static")
    html = (root / "index.html").read_text()
    js = (root / "app.js").read_text()
    assert 'id="view-semantic"' in html
    assert 'id="view-proof"' in html
    assert 'id="semantic"' in html
    assert 'id="proof"' in html
    assert "renderSemantic(t)" in js
    assert "renderProof(t)" in js
