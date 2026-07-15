"""Materialize the ASDiv cross-corpus gate into GSM8K-shaped parquet.

Run once to (re)create data/asdiv_dev.parquet + data/asdiv_test.parquet:

    uv run --with datasets python projects/asdiv/build_corpus.py

This is INFRASTRUCTURE, not a throwaway mining script (which the constitution
keeps out of the repo): the DEV/TEST split is defined by SALT below, and if that
salt lived only in a scratch file the TEST firewall would not be reproducible — a
fresh checkout would draw a different held-out set and silently spend a look. The
committed builder IS the definition of the firewall cut, exactly as firewall.py's
holdout_bucket() is for gsm8k.

SHAPE. Each row becomes {question: body+" "+question, answer: "#### <n>"}. The
"#### n" gold means the committed harness (firewall.parse_gold, load_dataset) and
the whole snapshot/diff ship gate read this corpus with ZERO new code. The gold
is the leading number of ASDiv's answer ("9 (apples)" -> 9.0); unit and set golds
are dropped to a float on purpose — this gate measures the SAME precision metric
that revealed the answer-accounting hole (a wrong number is wrong regardless of
unit). Typed golds (firewall.TypedGold) are a later tightening, tracked in
docs/difg-corpus-plan.md.

DETERMINISM. The split is md5(SALT + text) % 4 == 0 -> TEST (~25%), else DEV.
Continuous with the OOD probe that first measured this corpus, so the precision
numbers in docs/negative-results.md carry over. No Date/random: re-running is
byte-identical.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SALT = "asdiv-test@1"          # load-bearing: the firewall cut. NEVER change it.
_NUM = re.compile(r"-?[\d,]*\.?\d+")
HERE = Path(__file__).resolve().parent


def bucket(text: str) -> str:
    h = hashlib.md5((SALT + text).encode()).hexdigest()
    return "test" if int(h, 16) % 4 == 0 else "dev"


def gold_of(answer: str) -> float | None:
    m = _NUM.search(str(answer).replace(",", ""))
    return float(m.group()) if m else None


def main() -> None:
    from datasets import load_dataset  # only the fetch needs it; the split logic doesn't

    ds = load_dataset("EleutherAI/asdiv")["validation"]
    dev_q, dev_a, test_q, test_a = [], [], [], []
    dropped = 0
    for r in ds:
        text = f"{r['body'].strip()} {r['question'].strip()}"
        gold = gold_of(r["answer"])
        if gold is None:
            dropped += 1
            continue
        # store the float exactly as GSM8K stores its gold, so parse_gold reads it
        answer = f"#### {gold:g}"
        if bucket(text) == "test":
            test_q.append(text); test_a.append(answer)
        else:
            dev_q.append(text); dev_a.append(answer)

    (HERE / "data").mkdir(exist_ok=True)
    for name, qs, ans in (("asdiv_dev", dev_q, dev_a), ("asdiv_test", test_q, test_a)):
        table = pa.table({"question": qs, "answer": ans})
        out = HERE / "data" / f"{name}.parquet"
        pq.write_table(table, out)
        print(f"  {name:10} {len(qs):5d} items -> {out}")
    print(f"dropped {dropped} non-numeric-gold rows (typed golds; see docstring)")
    print(f"DEV is the standing gate; TEST ({len(test_q)}) is one-look-only.")


if __name__ == "__main__":
    main()
