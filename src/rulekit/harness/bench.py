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
import multiprocessing
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
    unknown_words: list[str] = field(default_factory=list)

    @property
    def fully_read(self) -> bool:
        return not self.unknown_words


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
        # an expected-decline item answered honestly is correct but committed
        # NOTHING — only actual answers count toward coverage/precision
        return sum(
            1 for r in self.results
            if r.outcome == "wrong" or (r.outcome == "correct" and r.got is not None)
        )

    @property
    def precision(self) -> float | None:
        if not self.committed:
            return None
        committed_correct = sum(
            1 for r in self.results if r.outcome == "correct" and r.got is not None
        )
        return committed_correct / self.committed

    @property
    def coverage(self) -> float:
        return self.committed / len(self.results) if self.results else 0.0

    @property
    def fully_read_count(self) -> int:
        return sum(1 for r in self.results if r.fully_read)

    def aggregates(self) -> dict:
        c = self.counts
        return {
            "items": len(self.results),
            **c,
            "precision": self.precision,
            "coverage": self.coverage,
            "fully_read": self.fully_read_count,
        }

    def summary(self, items_visible: bool = True) -> str:
        c = self.counts
        precision = f"{self.precision:.1%}" if self.precision is not None else "n/a"
        n = len(self.results)
        ceiling = self.fully_read_count / n if n else 0.0
        hit_rate = self.committed / self.fully_read_count if self.fully_read_count else 0.0
        lines = [
            f"items      {n}",
            f"correct    {c['correct']}",
            f"wrong      {c['wrong']}   <- must trend to 0 (precision failures)",
            f"declined   {c['declined']}  (safe coverage gaps)",
            f"errored    {c['errored']}",
            f"precision  {precision}  (correct/committed — THE safety metric)",
            f"coverage   {self.coverage:.1%}  (committed/total)",
            f"fully-read {ceiling:.1%}  × hit-rate {hit_rate:.1%}  (coverage factorization)",
            f"elapsed    {self.elapsed:.2f}s",
        ]
        wrongs = [r for r in self.results if r.outcome == "wrong"]
        if wrongs and items_visible:
            lines.append("confident-wrongs (the worklist):")
            for r in wrongs[:25]:
                lines.append(f"  {r.id}: expected {r.expected!r}, got {r.got!r}")
        elif wrongs:
            lines.append(f"confident-wrongs: {len(wrongs)} (aggregate-only slice — items withheld)")
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


def _solve_item(index: int, item: dict, reg: Registry) -> ItemResult:
    """Bench exactly one item. The single code path for serial AND parallel runs.

    `index` is the item's position in the slice — it is the id fallback, so a
    worker never needs to know how many items came before it.
    """
    item_id = str(item.get("id", index))
    expected = item["expect"]
    try:
        # tracing=False: a bench reads facts and the answer, never the
        # per-decision feature diffs. Snapshotting them was 61% of wall.
        result = solve(item["text"], reg, tracing=False)
        outcome, got = _judge(expected, result)
        rules = sorted(
            {
                f.provenance.source
                for f in result.store.facts
                if f.provenance.source not in ("fold",)
            }
        )
        unknown = sorted(
            {w.lower() for r in result.premises for w in r.unknown_words()}
            | {w.lower() for w in (result.question.unknown_words() if result.question else [])}
        )
        return ItemResult(
            item_id, outcome, expected, got,
            reason=result.answer.reason,
            rules=rules,
            collisions=len(result.store.collisions),
            unknown_words=unknown,
        )
    except Exception as exc:  # noqa: BLE001 — errored is a taxonomy bucket
        return ItemResult(item_id, "errored", expected, None, reason=repr(exc))


_WORKER_REG: Registry | None = None


def _worker_init(project_dir: str, expected_fingerprint: str) -> None:
    """Build this worker's own Registry.

    A Registry cannot be pickled (mappingproxy), so it cannot be shipped to a
    worker; each one loads the project itself. The fingerprint check is the
    safety net: if a worker somehow reads a different pack state than the parent
    reports in the snapshot, the run dies loudly instead of quietly benching a
    mixture of two states.
    """
    global _WORKER_REG
    from ..data.project import load_project

    reg = load_project(Path(project_dir)).registry
    if reg.fingerprint != expected_fingerprint:
        raise RuntimeError(
            f"worker registry fingerprint {reg.fingerprint!r} != parent "
            f"{expected_fingerprint!r} — refusing to bench a mixed pack state"
        )
    _WORKER_REG = reg


def _run_one(arg: tuple[int, dict]) -> ItemResult:
    index, item = arg
    assert _WORKER_REG is not None, "worker used before _worker_init"
    return _solve_item(index, item, _WORKER_REG)


def run_suite(
    items: list[dict],
    reg: Registry,
    jobs: int = 1,
    project_dir: Path | None = None,
) -> BenchReport:
    """Bench a slice.

    `jobs > 1` fans the items out over a process pool. Items are independent and
    the kernel is deterministic, and `Pool.map` preserves input order, so the
    report — and therefore the snapshot — is byte-identical to a serial run.

    Default is serial ON PURPOSE. A mining batch already runs its implementers
    concurrently; a bench that silently grabbed every core would oversubscribe
    the box and make that phase slower. Spend `jobs` where the pipeline is
    actually serial — the integration tail.
    """
    started = time.monotonic()
    if jobs > 1 and project_dir is not None and len(items) > 1:
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(
            processes=jobs,
            initializer=_worker_init,
            initargs=(str(project_dir), reg.fingerprint),
        ) as pool:
            results = pool.map(_run_one, list(enumerate(items)), chunksize=32)
    else:
        results = [_solve_item(i, item, reg) for i, item in enumerate(items)]
    return BenchReport(results, fingerprint=reg.fingerprint, elapsed=time.monotonic() - started)


def write_snapshot(report: BenchReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_snapshot(), indent=2, sort_keys=True))
