"""Phase B reader 52: appositive role identity with a relative event."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/appositive-role-member-relative-event"


def _facts(text: str) -> list[Atom]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


def test_emits_role_class_and_complete_relative_event() -> None:
    facts = _facts(
        "The son of Ada Lovelace, Byron King, is a football player "
        "who plays for North City."
    )
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [
        ("byron king", "son of ada lovelace", True),
        ("byron king", "football player", True),
        ("byron king", "play for north city", True),
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "A son of Ada Lovelace, Byron King, is a football player who plays for North City.",
        "The son of her, Byron King, is a football player who plays for North City.",
        "The son of Ada Lovelace Byron King is a football player who plays for North City.",
        "The son of Ada Lovelace, he, is a football player who plays for North City.",
        "The son of Ada Lovelace, Byron King, is not a football player who plays for North City.",
        "The son of Ada Lovelace, Byron King, is football player who plays for North City.",
        "The son of Ada Lovelace, Byron King, is a football player.",
        "The son of Ada Lovelace, Byron King, is a football player who does not play for North City.",
        "The son of Ada Lovelace, Byron King, is a football player who plays for North City and South Town.",
        "The son of Ada Lovelace, Byron King, is a football player who plays for North City",
    ],
)
def test_adjacent_constructions_stay_unread(surface: str) -> None:
    assert _facts(surface) == []
