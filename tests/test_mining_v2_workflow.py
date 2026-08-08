"""Mining v2 orchestration has one current protocol and a human gate."""

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLES = (
    "mining-scout",
    "mining-implementer",
    "constitution-reviewer",
    "mining-integrator",
)


def test_codex_and_claude_adapters_point_to_one_canonical_protocol_set() -> None:
    for role in ROLES:
        codex = tomllib.loads((ROOT / ".codex" / "agents" / f"{role}.toml").read_text())
        claude = (ROOT / ".claude" / "agents" / f"{role}.md").read_text()
        protocol = ROOT / ".agents" / "protocols" / f"{role}.md"

        assert protocol.is_file()
        assert f".agents/protocols/{role}.md" in codex["developer_instructions"]
        assert f".agents/protocols/{role}.md" in claude
        assert "difg domain campaign" not in codex["developer_instructions"]
        assert "difg domain campaign" not in claude


def test_mining_skill_pauses_for_human_review_and_exact_machine_gate() -> None:
    skill = (ROOT / ".agents" / "skills" / "mine" / "SKILL.md").read_text()

    assert "--integrate-approved" in skill
    assert "STOP for Designer review + exact machine gate" in skill
    assert "constitution pass + exact human approval" in skill
    assert "campaign-land" in skill
    assert "No historical suite/test count" in skill
    assert not (ROOT / ".claude" / "workflows" / "mine.js").exists()


def test_standing_protocol_names_every_inspectable_projection_gate() -> None:
    protocol = (ROOT / ".agents" / "protocols" / "standing-gate.md").read_text()

    assert "COGS `dev-train` and `dev-holdout`" in protocol
    assert "PMB `train` and `development`" in protocol
    assert "Never run `test`, `generalization`" in protocol
    assert "rulekit/campaign-review@2" in protocol
