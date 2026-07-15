"""Materialize the SVAMP cross-corpus gate into GSM8K-shaped parquet.

Run once to (re)create data/svamp_dev.parquet + data/svamp_test.parquet:

    uv run --with datasets python projects/svamp/build_corpus.py

INFRASTRUCTURE, not a throwaway mining script (sibling of projects/asdiv/
build_corpus.py — see its docstring for the full rationale): the DEV/TEST split is
salt-defined, and a scratch builder would make the TEST firewall non-reproducible.
The committed builder IS the definition of the firewall cut.

SHAPE. Each SVAMP row becomes {question: Body+" "+Question, answer: "#### <n>"} so
the committed harness (firewall.parse_gold, load_dataset) and the whole
snapshot/diff ship gate read it with ZERO new code — identical to the asdiv build.
SVAMP's own train/test split is IGNORED; we cut our own DEV/TEST by SALT so DEV is
a controlled inspectable pool and TEST is a real reserved held-out set.

DETERMINISM. md5(SALT + text) % 4 == 0 -> TEST (~25%), else DEV. No Date/random.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SALT = "svamp-test@1"          # load-bearing: the firewall cut. NEVER change it.
_NUM = re.compile(r"-?[\d,]*\.?\d+")
HERE = Path(__file__).resolve().parent


def bucket(text: str) -> str:
    h = hashlib.md5((SALT + text).encode()).hexdigest()
    return "test" if int(h, 16) % 4 == 0 else "dev"


def gold_of(answer: str) -> float | None:
    m = _NUM.search(str(answer).replace(",", ""))
    return float(m.group()) if m else None


def main() -> None:
    from datasets import concatenate_datasets, load_dataset  # only the fetch needs it

    ds = load_dataset("ChilleD/SVAMP")
    rows = concatenate_datasets([ds[s] for s in ds.keys()])  # our OWN split, not SVAMP's
    dev_q, dev_a, test_q, test_a = [], [], [], []
    dropped = 0
    for r in rows:
        text = f"{r['Body'].strip()} {r['Question'].strip()}"
        gold = gold_of(r["Answer"])
        if gold is None:
            dropped += 1
            continue
        answer = f"#### {gold:g}"
        if bucket(text) == "test":
            test_q.append(text); test_a.append(answer)
        else:
            dev_q.append(text); dev_a.append(answer)

    (HERE / "data").mkdir(exist_ok=True)
    for name, qs, ans in (("svamp_dev", dev_q, dev_a), ("svamp_test", test_q, test_a)):
        table = pa.table({"question": qs, "answer": ans})
        out = HERE / "data" / f"{name}.parquet"
        pq.write_table(table, out)
        print(f"  {name:10} {len(qs):5d} items -> {out}")
    print(f"dropped {dropped} non-numeric-gold rows")
    print(f"DEV is the standing gate; TEST ({len(test_q)}) is one-look-only.")


if __name__ == "__main__":
    main()
