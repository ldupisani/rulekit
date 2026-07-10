"""The bench: run a suite against a project, harm-ordered outcome taxonomy.

Outcomes (harm-ordered — the methodology's table):
  wrong    committed a confident wrong answer   WORST (precision failure)
  declined honest no-answer                     safe (coverage gap)
  errored  parse blow-up (counts as a decline)  safe
  correct  committed and right                  the win

Precision = correct / committed is THE metric. A precision drop reverts the
change, no matter how good other numbers look.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..data.registry import Registry
from ..kernel.engine import solve

TOL = 1e-6


@dataclass
class ItemResult:
    id: str
    outcome: str  # correct | wrong | declined | errored
    expected: object
    got: object
    reason: str = ""
    rules: list[str] = field(default_factory=list)
    collisions: int = 0


@dataclass
class BenchReport:
    results: list[ItemResult]
    fingerprint: str
    elapsed: float

    @property
    def counts(self) -> dict[str, int]:
        out = {"correct": 0, "wrong": 0, "declined": 0, "errored": 0}
        for r in self.results:
            out[r.outcome] += 1
        return out

    @property
    def committed(self) -> int:
        c = self.counts
        return c["correct"] + c["wrong"]

    @property
    def precision(self) -> float | None:
        return self.counts["correct"] / self.committed if self.committed else None

    @property
    def coverage(self) -> float:
        return self.committed / len(self.results) if self.results else 0.0

    def summary(self) -> str:
        c = self.counts
        precision = f"{self.precision:.1%}" if self.precision is not None else "n/a"
        lines = [
            f"items     {len(self.results)}",
            f"correct   {c['correct']}",
            f"wrong     {c['wrong']}   <- must trend to 0 (precision failures)",
            f"declined  {c['declined']}  (safe coverage gaps)",
            f"errored   {c['errored']}",
            f"precision {precision}  (correct/committed — THE safety metric)",
            f"coverage  {self.coverage:.1%}  (committed/total)",
            f"elapsed   {self.elapsed:.2f}s",
        ]
        wrongs = [r for r in self.results if r.outcome == "wrong"]
        if wrongs:
            lines.append("confident-wrongs (the worklist):")
            for r in wrongs:
                lines.append(f"  {r.id}: expected {r.expected!r}, got {r.got!r}")
        return "\n".join(lines)

    def to_snapshot(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "items": {
                r.id: {
                    "outcome": r.outcome,
                    "expected": r.expected,
                    "got": r.got,
                    "reason": r.reason,
                    "rules": r.rules,
                    "collisions": r.collisions,
                }
                for r in self.results
            },
        }


def _judge(expected: object, result) -> tuple[str, object]:
    answer = result.answer
    if answer.kind == "number":
        got = answer.value
        if isinstance(expected, (int, float)) and abs(got - float(expected)) < TOL:
            return "correct", got
        return "wrong", got
    if answer.kind == "verdict":
        got = answer.value
        if isinstance(expected, str) and got == expected:
            return "correct", got
        if expected == "decline" and got == "undetermined":
            return "correct", got
        # a verdict where a number was expected is a decline, not a commit
        if isinstance(expected, (int, float)):
            return "declined", got
        return "wrong", got
    # decline
    if expected == "decline":
        return "correct", None
    return "declined", None


def run_suite(items: list[dict], reg: Registry) -> BenchReport:
    started = time.monotonic()
    results: list[ItemResult] = []
    for item in items:
        item_id = str(item.get("id", len(results)))
        expected = item["expect"]
        try:
            result = solve(item["text"], reg)
            outcome, got = _judge(expected, result)
            rules = sorted(
                {
                    f.provenance.source
                    for f in result.store.facts
                    if f.provenance.source not in ("fold",)
                }
            )
            results.append(
                ItemResult(
                    item_id, outcome, expected, got,
                    reason=result.answer.reason,
                    rules=rules,
                    collisions=len(result.store.collisions),
                )
            )
        except Exception as exc:  # noqa: BLE001 — errored is a taxonomy bucket
            results.append(ItemResult(item_id, "errored", expected, None, reason=repr(exc)))
    return BenchReport(results, fingerprint=reg.fingerprint, elapsed=time.monotonic() - started)


def write_snapshot(report: BenchReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_snapshot(), indent=2, sort_keys=True))
