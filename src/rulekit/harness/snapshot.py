"""Snapshot diffing: the per-increment safety net.

Aggregate numbers HIDE confident-wrongs (an increment can post +1 net while
silently flipping previously-correct answers). The diff buckets every item
delta; the ship gate is: BROKE == 0 and DECL→WRONG == 0 and NET > 0
(diff-neutral for pure refactors: NET == 0 is the correct outcome there).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Diff:
    solved: list[str] = field(default_factory=list)  # not-correct -> correct
    broke: list[str] = field(default_factory=list)  # correct -> not-correct
    decl_to_wrong: list[str] = field(default_factory=list)  # safe -> WRONG
    wrong_to_decl: list[str] = field(default_factory=list)  # wrong -> safe
    changed_answer: list[str] = field(default_factory=list)

    @property
    def net(self) -> int:
        return len(self.solved) - len(self.broke)

    @property
    def ship(self) -> bool:
        return not self.broke and not self.decl_to_wrong and self.net >= 0

    def verdict(self) -> str:
        if self.broke or self.decl_to_wrong:
            return "REVERT"
        if self.net > 0:
            return "SHIP"
        return "NEUTRAL"

    def summary(self) -> str:
        lines = [
            f"SOLVED      {len(self.solved)}",
            f"BROKE       {len(self.broke)}   <- must be 0",
            f"DECL->WRONG {len(self.decl_to_wrong)}   <- must be 0",
            f"WRONG->DECL {len(self.wrong_to_decl)}",
            f"NET         {self.net:+d}",
            f"VERDICT: {self.verdict()}",
        ]
        for label, items in (
            ("BROKE", self.broke),
            ("DECL->WRONG", self.decl_to_wrong),
            ("SOLVED", self.solved),
        ):
            for item in items[:20]:
                lines.append(f"  {label}: {item}")
        return "\n".join(lines)


def load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text())


def diff(before: dict, after: dict) -> Diff:
    d = Diff()
    before_items = before["items"]
    after_items = after["items"]
    for item_id in sorted(set(before_items) | set(after_items)):
        b = before_items.get(item_id)
        a = after_items.get(item_id)
        if b is None or a is None:
            continue
        b_out, a_out = b["outcome"], a["outcome"]
        if b_out == a_out:
            if b_out == "correct" and b.get("got") != a.get("got"):
                d.changed_answer.append(item_id)
            continue
        if a_out == "correct":
            d.solved.append(item_id)
        elif b_out == "correct":
            d.broke.append(item_id)
        if b_out in ("declined", "errored") and a_out == "wrong":
            d.decl_to_wrong.append(item_id)
        if b_out == "wrong" and a_out in ("declined", "errored"):
            d.wrong_to_decl.append(item_id)
    return d
