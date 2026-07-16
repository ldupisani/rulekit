"""Materialize the difg multi-domain coverage corpus into GSM8K-shaped parquet.

    uv run python projects/difg/build_corpus.py

Reads difg's CASES from a LOCAL checkout (DIFG_SRC below) — the difg source is a
read-only dependency, not on HuggingFace. INFRASTRUCTURE (committed, salt-defined
firewall), like the other build_corpus.py scripts.

HONESTY SCAFFOLDING (docs/difg-corpus-plan.md, Phase 2 — none optional):
  - TYPED GOLD IS NOW KEPT. The gold payload is written through VERBATIM as difg
    wrote it ("68.04 kg", "$215.14", "50%", "134 days"), and the harness loader
    classifies it structurally (firewall.parse_typed_gold) because project.yaml
    declares `gold: typed`. Previously 252 of 454 items were DROPPED here for
    having a non-numeric gold, which is what left physics / logic /
    unit_conversion with no mining signal at all.
  - This changes NO existing item's split. The bucket is md5(SALT + question), a
    per-question function — admitting new items cannot move an old one across the
    firewall, and the numeric items keep the identical `#### <n>` payload they
    already had.
  - EXCLUDE `expression` (5 raw calculator strings — not natural language).
  - The metric this corpus reports is COVERAGE, not precision (the set is 79.3%
    difg's own example_queries — see project.yaml). We do not draw a
    precision claim from it.
  - Salted DEV/TEST split (reproducible, like every other corpus here), so the
    split is NOT a one-way door; the point of no return is MINING the DEV items,
    not cutting them. TEST stays reserved.

Each item -> {question: the difg query, answer: "#### <n>"} so the existing
harness reads it with no new code. The domain (orchestrator id) is dropped from
the parquet for now (the harness reads question/answer only); a `--domain` stats
facet is a later refinement (plan, mining-readiness gap 4).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SALT = "difg-test@1"           # load-bearing: the firewall cut. NEVER change it.
DIFG_SRC = Path.home() / "Development/experiments/difg/reasoning/tests/test_orchestrators.py"
HERE = Path(__file__).resolve().parent

_BARE = re.compile(r"^[-+]?[\d,]*\.?\d+$")
EXCLUDE_DOMAINS = {"expression"}  # raw calculator strings, not natural language


def bucket(text: str) -> str:
    h = hashlib.md5((SALT + text).encode()).hexdigest()
    return "test" if int(h, 16) % 4 == 0 else "dev"


def _read_cases():
    text = DIFG_SRC.read_text()
    m = re.search(r"^CASES = \[(.*?)^\]", text, re.S | re.M)
    if not m:
        raise SystemExit(f"could not find CASES in {DIFG_SRC}")
    return eval("[" + m.group(1) + "]", {"__builtins__": {}}, {})


def main() -> None:
    cases = _read_cases()
    dev_q, dev_a, test_q, test_a = [], [], [], []
    kept = dropped = 0
    for query, answer, orch in cases:
        if orch in EXCLUDE_DOMAINS:
            dropped += 1
            continue
        g = str(answer).strip().replace(",", "")
        q = str(query).strip()
        if _BARE.match(g):
            # A bare-number gold keeps its EXACT pre-existing payload, so every
            # item already in the corpus is byte-identical and no snapshot moves.
            row_a = f"#### {float(g):g}"
        else:
            # A typed gold goes through VERBATIM; firewall.parse_typed_gold
            # classifies it. Written from the raw `answer`, not the
            # comma-stripped `g`, so nothing about difg's own formatting is lost.
            payload = str(answer).strip()
            if not payload:
                dropped += 1
                continue
            row_a = f"#### {payload}"
        kept += 1
        if bucket(q) == "test":
            test_q.append(q); test_a.append(row_a)
        else:
            dev_q.append(q); dev_a.append(row_a)

    (HERE / "data").mkdir(exist_ok=True)
    for name, qs, ans in (("difg_dev", dev_q, dev_a), ("difg_test", test_q, test_a)):
        table = pa.table({"question": qs, "answer": ans})
        out = HERE / "data" / f"{name}.parquet"
        pq.write_table(table, out)
        print(f"  {name:10} {len(qs):5d} items -> {out}")
    print(f"kept {kept} items (numeric + typed), dropped {dropped} (excluded domains)")
    print(f"COVERAGE corpus; DEV is the mining worklist, TEST ({len(test_q)}) reserved.")


if __name__ == "__main__":
    main()
