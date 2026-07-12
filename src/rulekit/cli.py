"""rulekit CLI: parse | solve | diagnose | bench | diff."""

from __future__ import annotations

import argparse
import json
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
    result = solve(args.text, reg)
    if args.json:
        print(json.dumps(run_diagnose(result), indent=2))
    else:
        a = result.answer
        print(f"{a.kind}: {a.value if a.value is not None else '(no result)'}")
        print(f"  reason: {a.reason}")
        if args.trace:
            for event in result.trace():
                print(
                    f"  [{event['sentence']}:{event['seq']:03d}] {event['kind']:<20} "
                    f"u{event['target']}  {event['reason']}"
                )
    return 0


def cmd_diagnose(args) -> int:
    _project, reg = _registry(args)
    result = solve(args.text, reg)
    print(json.dumps(run_diagnose(result), indent=2))
    return 0


def _dataset_items(project, slice_name: str):
    return project.dataset_items(slice_name)


def cmd_bench(args) -> int:
    from .harness.firewall import INSPECTABLE_SLICES, record_test_look

    project, reg = _registry(args)
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
    if args.twice:
        # With --jobs > 1 the re-run is deliberately SERIAL: that makes --twice a
        # parallel-vs-serial equivalence proof, which is strictly stronger than
        # repeating the same parallel run and finding it agrees with itself.
        second = run_suite(items, reg, jobs=1)
        if report.to_snapshot() != second.to_snapshot():
            print(
                "DETERMINISM FAILURE: two runs disagree"
                + (f" (--jobs {args.jobs} vs serial)" if args.jobs > 1 else ""),
                file=sys.stderr,
            )
            return 3
        print("determinism: two in-process runs identical")
    return 0 if report.counts["wrong"] == 0 else 1


def cmd_stats(args) -> int:
    from collections import Counter

    from .harness.firewall import INSPECTABLE_SLICES

    project, reg = _registry(args)
    slice_name = args.slice or "dev-train"
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
    p.set_defaults(fn=cmd_solve)

    p = sub.add_parser("diagnose", help="the epistemic report for a text")
    p.add_argument("text")
    p.set_defaults(fn=cmd_diagnose)

    p = sub.add_parser("bench", help="run the project suite or a dataset slice")
    p.add_argument("--slice", help="dev|dev-train|dev-holdout|test (dataset projects)")
    p.add_argument("--limit", type=int, help="prefix only — prints a PARTIAL FIREWALL warning")
    p.add_argument("--spend-test-look", action="store_true",
                   help="required for --slice test; the look is recorded in the ledger")
    p.add_argument("--snapshot", help="write snapshot JSON under snapshots/")
    p.add_argument("--twice", action="store_true", help="determinism self-check")
    p.add_argument("--jobs", type=int, default=1,
                   help="fan items out over N processes (default 1). Output is "
                        "byte-identical to a serial run. Serial BY DEFAULT: a "
                        "mining batch already runs its implementers in parallel, "
                        "so spend this only where the pipeline is serial.")
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
