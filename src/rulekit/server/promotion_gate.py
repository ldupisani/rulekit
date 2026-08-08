"""Execute the fixed, serialized M4 candidate promotion gate.

Only inspectable DEV slices are named here.  Snapshot files are written to a
temporary directory outside both checkouts, and protected artifacts are never
parsed: their byte digests merely prove that the gate did not mutate them.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from ..data.project import Project
from ..generation.campaign_gates import (
    CampaignPromotionGate,
    CampaignReviewReplay,
    CampaignSpecimenReplay,
    CampaignStandingGateResult,
    campaign_trace_diff,
    campaign_trace_evidence,
)
from ..generation.campaign_reviews import (
    CampaignCandidateManifest,
    DurableCampaignCandidateManifest,
)
from ..generation.reviews import read_reviews
from ..harness.snapshot import Diff, ProjectionDiff, diff as snapshot_diff
from .candidate_runner import PromotionRuntime


@dataclass(frozen=True)
class StandingSpec:
    id: str
    project: str
    slice: str
    kind: str = "answer"


STANDING_SPECS = (
    StandingSpec("curated-suite", "curated", "suite"),
    StandingSpec("gsm8k-dev-train", "gsm8k", "dev-train"),
    StandingSpec("gsm8k-dev-holdout", "gsm8k", "dev-holdout"),
    StandingSpec("asdiv-dev", "asdiv", "dev"),
    StandingSpec("svamp-dev", "svamp", "dev"),
    StandingSpec("mawps-dev", "mawps", "dev"),
    StandingSpec("scibench-dev", "scibench", "dev"),
    StandingSpec("difg-dev", "difg", "dev"),
    StandingSpec("folio-dev", "folio", "dev"),
    StandingSpec("cogs-dev-train", "cogs", "dev-train", "projection"),
    StandingSpec("cogs-dev-holdout", "cogs", "dev-holdout", "projection"),
    StandingSpec("pmb-train", "pmb", "train", "projection"),
    StandingSpec("pmb-development", "pmb", "development", "projection"),
)


def relevant_campaign_reviews(
    project: Project,
    manifest: CampaignCandidateManifest,
) -> tuple[list[tuple[dict[str, Any], str]], list[str]]:
    """Return live, mechanically relevant reviews and missing explicit ids."""

    live = read_reviews(project, limit=100_000)
    by_id = {row["id"]: row for row in live}
    rule_ids = {
        rule_id
        for specimen in manifest.specimens
        for rule_id in (
            [specimen.target_rule] if specimen.target_rule else []
        )
        + specimen.actual_rule_ids
        + (
            [match.rule_id for match in specimen.trace.matches]
            if specimen.trace is not None
            else []
        )
    }
    selected = {
        row["id"]: (row, "target_rule")
        for row in live
        if row.get("target_rule") in rule_ids
    }
    missing = []
    for review_id in manifest.review_ids:
        row = by_id.get(review_id)
        if row is None:
            missing.append(review_id)
        else:
            selected[review_id] = (row, "explicit")
    return sorted(selected.values(), key=lambda item: item[0]["id"]), missing


def _counts(snapshot: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {"items": len(snapshot["items"])}
    for item in snapshot["items"].values():
        outcome = str(item["outcome"])
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def _numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, tuple)):
        return any(_numeric(item) for item in value)
    if isinstance(value, dict):
        return any(_numeric(item) for item in value.values())
    return False


def _diff_json(value: Diff | ProjectionDiff) -> dict[str, Any]:
    if isinstance(value, ProjectionDiff):
        return {
            "exact": value.exact,
            "broke": value.broke,
            "safe_to_incorrect": value.safe_to_incorrect,
            "incorrect_to_safe": value.incorrect_to_safe,
            "changed_graph": value.changed_graph,
            "net": value.net,
            "verdict": value.verdict(),
        }
    return {
        "solved": value.solved,
        "broke": value.broke,
        "decl_to_wrong": value.decl_to_wrong,
        "wrong_to_decl": value.wrong_to_decl,
        "changed_answer": value.changed_answer,
        "net": value.net,
        "verdict": value.verdict(),
    }


def _run(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = 1800,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode()
            if isinstance(exc.stdout, bytes)
            else exc.stdout
        )
        stderr = (
            exc.stderr.decode()
            if isinstance(exc.stderr, bytes)
            else exc.stderr
        )
        return subprocess.CompletedProcess(
            args,
            124,
            stdout=stdout or "",
            stderr=(stderr or "") + f"\ncommand timed out after {timeout}s",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args,
            127,
            stdout="",
            stderr=f"could not execute command: {exc}",
        )


def _bench_snapshot(
    runtime: PromotionRuntime,
    spec: StandingSpec,
    output: Path,
) -> tuple[dict[str, Any] | None, str]:
    project = runtime.root / "projects" / spec.project
    result = _run(
        [
            str(runtime.rulekit),
            "--project",
            str(project),
            "bench",
            "--slice",
            spec.slice,
            "--jobs",
            "8",
            "--emit-snapshot",
            str(output),
        ],
        cwd=runtime.root,
    )
    detail = (result.stdout + "\n" + result.stderr).strip()[-8000:]
    if result.returncode not in (0, 1) or not output.is_file():
        return None, detail or f"bench exited {result.returncode}"
    try:
        return json.loads(output.read_text(encoding="utf-8")), detail
    except (OSError, ValueError) as exc:
        return None, f"invalid emitted snapshot: {exc}"


def _standing_result(
    spec: StandingSpec,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    detail: str,
) -> CampaignStandingGateResult:
    before_ids = set(baseline["items"])
    after_ids = set(candidate["items"])
    delta = snapshot_diff(baseline, candidate)
    baseline_counts = _counts(baseline)
    candidate_counts = _counts(candidate)
    passed = before_ids == after_ids and delta.ship
    notes = []
    if before_ids != after_ids:
        notes.append("baseline and candidate item identities differ")
    if spec.kind == "projection":
        passed = passed and candidate_counts.get("incorrect", 0) == 0
    else:
        passed = passed and candidate_counts.get("wrong", 0) == 0
    if spec.id == "curated-suite":
        passed = passed and candidate_counts.get("correct", 0) == candidate_counts["items"]
    if spec.id == "folio-dev":
        numeric = sum(
            1 for item in candidate["items"].values() if _numeric(item.get("got"))
        )
        candidate_counts["numeric_commitments"] = numeric
        passed = passed and numeric == 0
    return CampaignStandingGateResult(
        id=spec.id,
        kind=spec.kind,
        passed=passed,
        baseline_fingerprint=baseline.get("fingerprint"),
        candidate_fingerprint=candidate.get("fingerprint"),
        item_ids_digest=hashlib.sha256(
            "\n".join(sorted(after_ids)).encode("utf-8")
        ).hexdigest(),
        baseline=baseline_counts,
        candidate=candidate_counts,
        diff=_diff_json(delta),
        detail="; ".join(notes) or detail[-2000:],
    )


def _protected_digest(roots: Iterable[Path]) -> dict[str, str]:
    patterns = (
        "projects/*/snapshots/*ledger*.jsonl",
        "projects/*/data/*test*.parquet",
        "projects/*/data/*generalization*.parquet",
    )
    digests: dict[str, str] = {}
    for root in roots:
        for pattern in patterns:
            for path in sorted(root.glob(pattern)):
                if not path.is_file():
                    continue
                resolved = path.resolve()
                key = str(resolved)
                if key in digests:
                    continue
                hasher = hashlib.sha256()
                with resolved.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        hasher.update(chunk)
                digests[key] = hasher.hexdigest()
    return digests


def run_campaign_promotion_gate(
    project: Project,
    manifest_data: dict[str, Any],
    baseline_runtime: PromotionRuntime,
    candidate_runtime: PromotionRuntime,
    trace: Callable[[str, str | None, int | None], dict[str, Any]],
) -> CampaignPromotionGate:
    """Run all replay and fixed standing checks for one exact candidate."""

    # Promotion gates only run after central publication.  The queue therefore
    # supplies the durable record, including the project and publication time,
    # rather than the pre-publication candidate payload.
    manifest = DurableCampaignCandidateManifest.model_validate(manifest_data)
    specimens: list[CampaignSpecimenReplay] = []
    for specimen in manifest.specimens:
        if specimen.trace is None:
            specimens.append(
                CampaignSpecimenReplay(
                    specimen_id=specimen.id,
                    passed=False,
                    error="manifest lacks canonical trace evidence",
                )
            )
            continue
        try:
            actual = campaign_trace_evidence(
                trace(
                    specimen.sentence,
                    specimen.interpretation,
                    specimen.reference_year,
                )
            )
            sections = campaign_trace_diff(specimen.trace, actual)
            changed = [name for name, value in sections.items() if not value.same]
            specimens.append(
                CampaignSpecimenReplay(
                    specimen_id=specimen.id,
                    passed=not changed,
                    changed_sections=changed,
                    actual=actual,
                    diff=sections,
                )
            )
        except Exception as exc:  # noqa: BLE001 - durable gate failure evidence
            specimens.append(
                CampaignSpecimenReplay(
                    specimen_id=specimen.id,
                    passed=False,
                    error=f"{type(exc).__name__}: {exc}"[:4000],
                )
            )

    reviews: list[CampaignReviewReplay] = []
    relevant, missing = relevant_campaign_reviews(project, manifest)
    for review_id in missing:
        reviews.append(
            CampaignReviewReplay(
                review_id=review_id,
                scope="explicit",
                verdict="missing",
                replayed=False,
                error="explicit review id is absent or tombstoned",
            )
        )
    for review, scope in relevant:
        try:
            actual = campaign_trace_evidence(
                trace(
                    review["sentence"],
                    review.get("interpretation") or None,
                    None,
                )
            )
            target = review.get("target_rule")
            reviews.append(
                CampaignReviewReplay(
                    review_id=review["id"],
                    scope=scope,
                    verdict=review["verdict"],
                    target_rule=target,
                    target_present=(
                        None
                        if target is None
                        else any(match.rule_id == target for match in actual.matches)
                    ),
                    replayed=True,
                    actual=actual,
                )
            )
        except Exception as exc:  # noqa: BLE001 - durable gate failure evidence
            reviews.append(
                CampaignReviewReplay(
                    review_id=review["id"],
                    scope=scope,
                    verdict=review["verdict"],
                    target_rule=review.get("target_rule"),
                    replayed=False,
                    error=f"{type(exc).__name__}: {exc}"[:4000],
                )
            )

    protected_before = _protected_digest((baseline_runtime.root, candidate_runtime.root))
    standing: list[CampaignStandingGateResult] = []
    with tempfile.TemporaryDirectory(prefix="rulekit-campaign-gate-") as raw_tmp:
        tmp = Path(raw_tmp)
        for index, spec in enumerate(STANDING_SPECS):
            before, before_detail = _bench_snapshot(
                baseline_runtime, spec, tmp / f"{index}-before.json"
            )
            after, after_detail = _bench_snapshot(
                candidate_runtime, spec, tmp / f"{index}-after.json"
            )
            if before is None or after is None:
                standing.append(
                    CampaignStandingGateResult(
                        id=spec.id,
                        kind=spec.kind,
                        passed=False,
                        detail=(before_detail + "\n" + after_detail)[-8000:],
                    )
                )
            else:
                standing.append(
                    _standing_result(spec, before, after, after_detail)
                )

        tests = _run(
            [
                str(candidate_runtime.python),
                "-m",
                "pytest",
                "-q",
                "-n",
                "4",
                "--dist=worksteal",
            ],
            cwd=candidate_runtime.root,
        )
        standing.append(
            CampaignStandingGateResult(
                id="synthetic-full",
                kind="synthetic",
                passed=tests.returncode == 0,
                detail=(tests.stdout + "\n" + tests.stderr).strip()[-8000:],
            )
        )
        lint = _run(
            [
                str(candidate_runtime.rulekit),
                "--project",
                str(candidate_runtime.root / "projects" / "curated"),
                "lint",
            ],
            cwd=candidate_runtime.root,
        )
        standing.append(
            CampaignStandingGateResult(
                id="lint-curated",
                kind="lint",
                passed=lint.returncode == 0,
                detail=(lint.stdout + "\n" + lint.stderr).strip()[-8000:],
            )
        )

    protected_after = _protected_digest((baseline_runtime.root, candidate_runtime.root))
    standing.append(
        CampaignStandingGateResult(
            id="protected-firewall",
            kind="firewall",
            passed=protected_before == protected_after,
            baseline={"files": len(protected_before)},
            candidate={"files": len(protected_after)},
            detail=(
                "protected ledger and TEST/generalization bytes unchanged"
                if protected_before == protected_after
                else "protected artifact digest changed during the gate"
            ),
        )
    )
    passed = (
        all(item.passed for item in specimens)
        and all(item.replayed for item in reviews)
        and all(item.passed for item in standing)
    )
    return CampaignPromotionGate(
        candidate_id=manifest.candidate_id,
        candidate_commit=candidate_runtime.commit,
        registry_fingerprint=manifest.registry_fingerprint,
        baseline_commit=baseline_runtime.commit,
        passed=passed,
        specimens=specimens,
        reviews=reviews,
        standing=standing,
    )
