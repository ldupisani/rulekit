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


def cmd_bench(args) -> int:
    project, reg = _registry(args)
    items = project.suite_items()
    if not items:
        print("project has no suite", file=sys.stderr)
        return 2
    report = run_suite(items, reg)
    print(report.summary())
    if args.snapshot:
        path = project.snapshots_dir / args.snapshot
        write_snapshot(report, path)
        print(f"snapshot -> {path}")
    if args.twice:
        second = run_suite(items, reg)
        if report.to_snapshot() != second.to_snapshot():
            print("DETERMINISM FAILURE: two runs disagree", file=sys.stderr)
            return 3
        print("determinism: two in-process runs identical")
    return 0 if report.counts["wrong"] == 0 else 1


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

    p = sub.add_parser("bench", help="run the project suite")
    p.add_argument("--snapshot", help="write snapshot JSON under snapshots/")
    p.add_argument("--twice", action="store_true", help="determinism self-check")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("diff", help="diff two snapshots (ship gate)")
    p.add_argument("before")
    p.add_argument("after")
    p.set_defaults(fn=cmd_diff)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
