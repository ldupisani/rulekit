"""rulekit CLI: parse | solve | diagnose | bench | diff."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .data.project import load_project
from .harness.bench import run_suite, write_snapshot
from .harness.snapshot import diff as snapshot_diff, load_snapshot
from .kernel.engine import diagnose as run_diagnose, solve


def _registry(args):
    project = load_project(args.project)
    return project, project.registry


def cmd_solve(args) -> int:
    _project, reg = _registry(args)
    result = solve(args.text, reg, reference_year=args.reference_year)
    if args.json:
        print(json.dumps(run_diagnose(result), indent=2))
    else:
        a = result.answer
        print(f"{a.kind}: {a.value if a.value is not None else '(no result)'}")
        print(f"  reason: {a.reason}")
        for assumption in a.assumptions:
            print(f"  assumption: {assumption.description}")
        if args.trace:
            for event in result.trace():
                if event["kind"] == "question-assumption":
                    print(f"  [{event['sentence']}] question-assumption {event['text']}")
                    continue
                if event["kind"] == "agreement-ambiguity":
                    retained = event["retained"]
                    deduped = event["deduped"]
                    print(
                        "  [fact] agreement-ambiguity "
                        f"{retained['source']}@{retained['sentence']} == "
                        f"{deduped['source']}@{deduped['sentence']}"
                    )
                    continue
                print(
                    f"  [{event['sentence']}:{event['seq']:03d}] {event['kind']:<20} "
                    f"u{event['target']}  {event['reason']}"
                )
    return 0


def cmd_diagnose(args) -> int:
    _project, reg = _registry(args)
    result = solve(args.text, reg, reference_year=args.reference_year)
    print(json.dumps(run_diagnose(result), indent=2))
    return 0


def _dataset_items(project, slice_name: str):
    return project.dataset_items(slice_name)


def cmd_bench(args) -> int:
    from .harness.firewall import INSPECTABLE_SLICES, record_test_look

    project, reg = _registry(args)
    if project.doc.projection is not None:
        from .harness.projection import (
            run_projection_suite,
            write_projection_snapshot,
        )

        projection = project.doc.projection
        if not args.slice:
            print(
                "projection project: --slice "
                f"{'|'.join(sorted(projection.splits))} required",
                file=sys.stderr,
            )
            return 2
        split = projection.splits.get(args.slice)
        if split is None:
            print(
                f"unknown projection slice {args.slice!r}; choose one of "
                f"{', '.join(sorted(projection.splits))}",
                file=sys.stderr,
            )
            return 2
        inspectable = project.projection_slice_inspectable(args.slice)
        if not inspectable and not args.spend_test_look:
            print(
                f"{args.slice.upper()} is one-look and aggregate-only: add "
                "--spend-test-look to spend it (recorded in the ledger)",
                file=sys.stderr,
            )
            return 2
        if not inspectable and args.limit:
            print(
                "refusing --limit on an aggregate-only projection slice: "
                "a partial protected look is not a valid look",
                file=sys.stderr,
            )
            return 2
        items = project.projection_items(args.slice)
        if args.limit:
            print(
                f"⚠ PARTIAL FIREWALL: --limit {args.limit} — a prefix number is "
                "not the slice number; never ship on it"
            )
            items = items[: args.limit]
        report = run_projection_suite(
            items,
            reg,
            jobs=args.jobs,
            project_dir=args.project,
        )
        print(report.summary(items_visible=inspectable))
        if not inspectable:
            ledger = project.snapshots_dir / f"{args.slice}-ledger.jsonl"
            record_test_look(ledger, report.fingerprint, report.aggregates())
            print(f"{args.slice} look SPENT -> {ledger.relative_to(project.root)}")
            return 0
        if args.snapshot:
            path = project.snapshots_dir / args.snapshot
            write_projection_snapshot(report, path)
            print(f"snapshot -> {path}")
        if args.emit_snapshot:
            Path(args.emit_snapshot).write_text(
                json.dumps(report.to_snapshot(), sort_keys=True)
            )
        if args.twice:
            if args.jobs > 1:
                second = run_projection_suite(items, reg, jobs=1)
                if report.to_snapshot() != second.to_snapshot():
                    print(
                        f"DETERMINISM FAILURE: --jobs {args.jobs} "
                        "disagrees with serial",
                        file=sys.stderr,
                    )
                    return 3
                print(
                    f"determinism: --jobs {args.jobs} matches serial "
                    "(same process)"
                )
            fresh = _rerun_in_subprocess(args)
            if fresh is None:
                print(
                    "DETERMINISM FAILURE: the fresh-process re-run did not complete",
                    file=sys.stderr,
                )
                return 3
            if fresh != report.to_snapshot():
                print(
                    "DETERMINISM FAILURE: a fresh process disagrees with this one",
                    file=sys.stderr,
                )
                return 3
            print("determinism: a fresh process produces an identical snapshot")
        return 1 if report.counts["incorrect"] else 0

    if args.slice == "suite" or (not args.slice and not project.doc.datasets):
        items = project.suite_items()
        if not items:
            print("project has no suite", file=sys.stderr)
            return 2
    elif project.doc.datasets:
        if not args.slice:
            print(
                "dataset project: --slice suite|dev|dev-train|dev-holdout|test required",
                file=sys.stderr,
            )
            return 2
        if args.slice == "test" and not args.spend_test_look:
            print(
                "TEST is one-look and aggregate-only: add --spend-test-look to "
                "spend it (recorded in the ledger)",
                file=sys.stderr,
            )
            return 2
        items = _dataset_items(project, args.slice)
    else:
        items = project.suite_items()
        if not items:
            print("project has no suite or datasets", file=sys.stderr)
            return 2
    if args.limit:
        print(f"⚠ PARTIAL FIREWALL: --limit {args.limit} — a prefix number is "
              "not the slice number; never ship on it")
        items = items[: args.limit]

    report = run_suite(items, reg, jobs=args.jobs, project_dir=args.project)
    inspectable = (
        not project.doc.datasets
        or args.slice in INSPECTABLE_SLICES
        or args.slice == "suite"
    )
    print(report.summary(items_visible=inspectable))
    if project.doc.datasets and args.slice == "test":
        record_test_look(
            project.snapshots_dir / "test-ledger.jsonl", reg.fingerprint, report.aggregates()
        )
        print("test look SPENT -> snapshots/test-ledger.jsonl")
        return 0
    if args.snapshot:
        if not inspectable:
            print("refusing to snapshot an aggregate-only slice", file=sys.stderr)
            return 2
        path = project.snapshots_dir / args.snapshot
        write_snapshot(report, path)
        print(f"snapshot -> {path}")
    if args.emit_snapshot:
        Path(args.emit_snapshot).write_text(json.dumps(report.to_snapshot(), sort_keys=True))
    if args.twice and not inspectable:
        # a determinism check must never be a reason to touch TEST
        print("refusing --twice on an aggregate-only slice", file=sys.stderr)
        return 2
    if args.twice:
        # TWO INDEPENDENT CHECKS, because one process cannot make the other's
        # claim.
        #
        # (a) IN-PROCESS, and only when it says something. With `--jobs > 1` the
        #     re-run is deliberately SERIAL, making it a parallel-vs-serial
        #     equivalence proof. At `--jobs 1` — the DEFAULT — it would be the
        #     same code re-running under the same conditions in the same
        #     interpreter, which agrees with itself by construction, so it is
        #     skipped rather than printed as reassurance.
        if args.jobs > 1:
            second = run_suite(items, reg, jobs=1)
            if report.to_snapshot() != second.to_snapshot():
                print(
                    f"DETERMINISM FAILURE: --jobs {args.jobs} disagrees with serial",
                    file=sys.stderr,
                )
                return 3
            print(f"determinism: --jobs {args.jobs} matches serial (same process)")

        # (b) FRESH PROCESS. This is the check the flag always claimed to be
        #     making and never was: a second in-process run shares every module
        #     global, every cache and every import-order effect with the first,
        #     so it CANNOT see the failures that matter — state that leaks
        #     across runs, or a result that depends on anything established at
        #     import. `docs/architecture.md`'s determinism invariant is about
        #     fresh processes, so the re-run has to be one.
        fresh = _rerun_in_subprocess(args)
        if fresh is None:
            print("DETERMINISM FAILURE: the fresh-process re-run did not complete",
                  file=sys.stderr)
            return 3
        if fresh != report.to_snapshot():
            print("DETERMINISM FAILURE: a fresh process disagrees with this one",
                  file=sys.stderr)
            return 3
        print("determinism: a fresh process produces an identical snapshot")
    return 0 if report.counts["wrong"] == 0 else 1


def _rerun_in_subprocess(args) -> dict | None:
    """Re-run this bench in a FRESH interpreter and return its snapshot.

    Spawned with `-I` (isolated: no user site-packages, no inherited PYTHONPATH)
    so the second process is not merely a fork of this one's environment. The
    child writes a canonical snapshot to a temp file rather than to stdout,
    because stdout carries progress output that would have to be parsed — and a
    determinism check that depends on parsing is a determinism check with its
    own failure mode.

    Returns None if the child fails for any reason; the caller treats that as a
    FAILURE rather than a pass, because "could not verify" is not "verified".
    """
    import json
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "snapshot.json"
        cmd = [
            sys.executable, "-I", "-m", "rulekit.cli",
            "--project", str(args.project),
            "bench", "--slice", args.slice or "dev-train",
            "--jobs", "1",
            "--emit-snapshot", str(out),
        ]
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        try:
            proc = subprocess.run(cmd, capture_output=True, env=env, timeout=1800)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode not in (0, 1) or not out.exists():
            # 1 is "wrong answers present", which is orthogonal to determinism
            sys.stderr.write(proc.stderr.decode(errors="replace")[-2000:])
            return None
        return json.loads(out.read_text())


def cmd_stats(args) -> int:
    from collections import Counter

    from .harness.firewall import INSPECTABLE_SLICES

    project, reg = _registry(args)
    slice_name = args.slice or "dev-train"
    if project.doc.projection is not None:
        from .harness.projection import run_projection_suite

        if not project.projection_slice_inspectable(slice_name):
            print(
                "stats runs on inspectable projection slices only (the firewall)",
                file=sys.stderr,
            )
            return 2
        items = project.projection_items(slice_name)
        report = run_projection_suite(items, reg)
        unknown = Counter(
            word
            for result in report.results
            for word in result.unknown_words
        )
        print(report.summary())
        print("\nmost frequent unknown words (the vocabulary worklist):")
        for word, count in unknown.most_common(args.top):
            print(f"  {count:5d}  {word}")
        return 0
    if project.doc.datasets:
        if slice_name not in INSPECTABLE_SLICES:
            print("stats runs on inspectable slices only (the firewall)", file=sys.stderr)
            return 2
        items = _dataset_items(project, slice_name)
    else:
        items = project.suite_items()
    report = run_suite(items, reg)

    unknown = Counter()
    reasons = Counter()
    rules = Counter()
    for r in report.results:
        for w in r.unknown_words:
            unknown[w] += 1
        if r.outcome in ("declined", "errored"):
            reasons[r.reason.split("(")[0].split(" for ")[0].strip()[:60]] += 1
        if r.outcome == "correct":
            for rule in r.rules or ["fold-only"]:
                rules[rule] += 1
    print(report.summary())
    print("\nmost frequent unknown words (the vocabulary worklist):")
    for w, n in unknown.most_common(args.top):
        print(f"  {n:5d}  {w}")
    print("\ndecline reasons (the structure worklist):")
    for reason, n in reasons.most_common(args.top):
        print(f"  {n:5d}  {reason}")
    print("\nrule attribution (where correct answers come from):")
    for rule, n in rules.most_common():
        print(f"  {n:5d}  {rule}")
    return 0


def cmd_lint(args) -> int:
    from .lint.blast_radius import blast_radius
    from .lint.checks import lint_checks
    from .lint.overlap import lint_overlaps

    _project, reg = _registry(args)
    if args.category:
        if args.category not in reg.category_parents:
            print(f"unknown category {args.category!r}", file=sys.stderr)
            return 2
        print(blast_radius(reg, args.category).summary())
        return 0
    findings = lint_overlaps(reg) + lint_checks(reg)
    errors = 0
    for f in findings:
        if f.level == "info" and not args.verbose:
            continue
        print(f)
        errors += f.level == "error"
    print(f"lint: {sum(f.level == 'error' for f in findings)} errors, "
          f"{sum(f.level == 'warning' for f in findings)} warnings, "
          f"{sum(f.level == 'info' for f in findings)} info")
    return 1 if errors else 0


def cmd_serve(args) -> int:
    from pathlib import Path

    from .server.app import serve

    print(f"rulekit designer → http://{args.host}:{args.port}")
    serve(Path(args.project).resolve(), host=args.host, port=args.port)
    return 0


def cmd_diff(args) -> int:
    project, _reg = _registry(args)
    before = load_snapshot(project.snapshots_dir / args.before)
    after = load_snapshot(project.snapshots_dir / args.after)
    d = snapshot_diff(before, after)
    print(d.summary())
    return 0 if d.ship else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rulekit")
    parser.add_argument("--project", default=".", help="project directory")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("solve", help="parse + answer a text")
    p.add_argument("text")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--reference-year",
        type=int,
        help="absolute calendar year used to resolve deictic questions such as 'now'",
    )
    p.set_defaults(fn=cmd_solve)

    p = sub.add_parser("diagnose", help="the epistemic report for a text")
    p.add_argument("text")
    p.add_argument(
        "--reference-year",
        type=int,
        help="absolute calendar year used to resolve deictic questions such as 'now'",
    )
    p.set_defaults(fn=cmd_diagnose)

    p = sub.add_parser("bench", help="run the project suite or a dataset slice")
    p.add_argument(
        "--slice",
        help=(
            "suite|dev|dev-train|dev-holdout|calibration|test|generalization"
        ),
    )
    p.add_argument("--limit", type=int, help="prefix only — prints a PARTIAL FIREWALL warning")
    p.add_argument("--spend-test-look", action="store_true",
                   help="required for --slice test; the look is recorded in the ledger")
    p.add_argument("--snapshot", help="write snapshot JSON under snapshots/")
    p.add_argument("--twice", action="store_true", help="determinism self-check")
    p.add_argument(
        "--emit-snapshot", metavar="PATH",
        help="write the canonical snapshot to PATH (used by --twice's fresh-process re-run)",
    )
    p.add_argument("--jobs", type=int, default=1,
                   help="fan items out over N processes (default 1). Output is "
                        "byte-identical to a serial run. Choose this explicitly "
                        "to control CPU use alongside other development work.")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("stats", help="unknown-word worklist, decline taxonomy, rule attribution")
    p.add_argument("--slice", help="inspectable slice (default dev-train)")
    p.add_argument("--top", type=int, default=25)
    p.set_defaults(fn=cmd_stats)

    p = sub.add_parser("lint", help="static checks: overlaps, overrides, blast radius")
    p.add_argument("--category", help="print the blast-radius report for a category")
    p.add_argument("--verbose", action="store_true", help="include info findings")
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("diff", help="diff two snapshots (ship gate)")
    p.add_argument("before")
    p.add_argument("after")
    p.set_defaults(fn=cmd_diff)

    p = sub.add_parser("serve", help="the visual designer (local web UI)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8321)
    p.set_defaults(fn=cmd_serve)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
