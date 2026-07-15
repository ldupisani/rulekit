"""Materialize the SciBench out-of-domain safety gate into GSM8K-shaped parquet.

    uv run --with datasets python projects/scibench/build_corpus.py

INFRASTRUCTURE (see projects/asdiv/build_corpus.py). SciBench is OUT OF DOMAIN
(college physics/chemistry), so this gate measures PRECISION on text the engine
cannot read: it should DECLINE, never commit a confident wrong. Each row ->
{question: problem_text, answer: "#### <n>"} where <n> is answer_number (a float;
unit dropped, exactly as the other float-gold corpora). SciBench ships a single
'train' split; we cut our own DEV/TEST by SALT.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SALT = "scibench-test@1"        # load-bearing: the firewall cut. NEVER change it.
_NUM = re.compile(r"[-+]?[\d,]*\.?\d+")
HERE = Path(__file__).resolve().parent


def bucket(text: str) -> str:
    h = hashlib.md5((SALT + text).encode()).hexdigest()
    return "test" if int(h, 16) % 4 == 0 else "dev"


def gold_of(answer: str) -> float | None:
    m = _NUM.search(str(answer).replace(",", ""))
    return float(m.group()) if m else None


def main() -> None:
    from datasets import concatenate_datasets, load_dataset

    ds = load_dataset("xw27/scibench")
    rows = concatenate_datasets([ds[s] for s in ds.keys()])
    dev_q, dev_a, test_q, test_a = [], [], [], []
    dropped = 0
    for r in rows:
        text = str(r["problem_text"]).strip()
        gold = gold_of(r["answer_number"])
        if gold is None or not text:
            dropped += 1
            continue
        answer = f"#### {gold:g}"
        if bucket(text) == "test":
            test_q.append(text); test_a.append(answer)
        else:
            dev_q.append(text); dev_a.append(answer)

    (HERE / "data").mkdir(exist_ok=True)
    for name, qs, ans in (("scibench_dev", dev_q, dev_a), ("scibench_test", test_q, test_a)):
        table = pa.table({"question": qs, "answer": ans})
        out = HERE / "data" / f"{name}.parquet"
        pq.write_table(table, out)
        print(f"  {name:13} {len(qs):5d} items -> {out}")
    print(f"dropped {dropped} non-numeric-gold rows")
    print(f"DEV is the standing gate; TEST ({len(test_q)}) is one-look-only.")


if __name__ == "__main__":
    main()
