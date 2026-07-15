"""Materialize the MAWPS cross-corpus gate into GSM8K-shaped parquet.

    uv run --with datasets python projects/mawps/build_corpus.py

INFRASTRUCTURE (see projects/asdiv/build_corpus.py for the full rationale): the
salt-defined DEV/TEST split must be reproducible, so the builder is committed.
Each row -> {question, answer: "#### <n>"}; the existing harness reads it with no
new code. MAWPS's own splits are ignored; we cut our own by SALT.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SALT = "mawps-test@1"          # load-bearing: the firewall cut. NEVER change it.
HERE = Path(__file__).resolve().parent


def bucket(text: str) -> str:
    h = hashlib.md5((SALT + text).encode()).hexdigest()
    return "test" if int(h, 16) % 4 == 0 else "dev"


def gold_of(row) -> float | None:
    v = row.get("result_float")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> None:
    from datasets import concatenate_datasets, load_dataset

    ds = load_dataset("MU-NLPC/Calc-mawps")
    rows = concatenate_datasets([ds[s] for s in ds.keys()])
    dev_q, dev_a, test_q, test_a = [], [], [], []
    dropped = 0
    seen: set[str] = set()
    for r in rows:
        text = r["question"].strip()
        if text in seen:  # MAWPS has near-duplicates across splits; keep one
            continue
        seen.add(text)
        gold = gold_of(r)
        if gold is None:
            dropped += 1
            continue
        answer = f"#### {gold:g}"
        if bucket(text) == "test":
            test_q.append(text); test_a.append(answer)
        else:
            dev_q.append(text); dev_a.append(answer)

    (HERE / "data").mkdir(exist_ok=True)
    for name, qs, ans in (("mawps_dev", dev_q, dev_a), ("mawps_test", test_q, test_a)):
        table = pa.table({"question": qs, "answer": ans})
        out = HERE / "data" / f"{name}.parquet"
        pq.write_table(table, out)
        print(f"  {name:11} {len(qs):5d} items -> {out}")
    print(f"dropped {dropped} non-numeric-gold rows")
    print(f"DEV is the standing gate; TEST ({len(test_q)}) is one-look-only.")


if __name__ == "__main__":
    main()
