"""The DEV/TEST firewall, made executable.

- DEV (= the train split) is inspectable: mine, tune, read items freely.
- dev-train / dev-holdout partition DEV by a stable md5 of the question —
  tune on dev-train ONLY, validate on dev-holdout as a delta gate.
- TEST is aggregate-only and each look is SPENT: it requires an explicit
  flag and is appended to an auditable ledger. Per-item TEST output does
  not exist in this codebase.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

INSPECTABLE_SLICES = ("dev", "dev-train", "dev-holdout")
ALL_SLICES = INSPECTABLE_SLICES + ("test",)

_GOLD = re.compile(r"####\s*([-+]?[\d,]*\.?\d+)")


@dataclass(frozen=True)
class TypedGold:
    """A gold that is not a bare float (docs/difg-corpus-plan.md, Phase 0).

    Only 44.5% of the difg corpus's answers are bare numbers; the rest are
    quantity+unit ("68.04 kg"), verdicts, money, percents, entities and sets. A
    float-only gold deletes physics, logic, clock_arithmetic and most of
    unit_conversion as SCORABLE domains — i.e. it abandons the goal.

    PURELY ADDITIVE, and that is the whole Phase 0 argument: GSM8K's loader emits
    a bare `float` exactly as it does today and `_judge` keeps its float path
    byte-for-byte. No GSM8K item can construct one of these, so no GSM8K item can
    take the typed branch. Byte-identity of the GSM8K snapshot is therefore a
    property of the SHAPE of this change, not a lucky outcome — which is exactly
    what Phase 0 exists to verify rather than assume."""

    kind: str            # number | quantity | verdict | money | percent | text | set
    value: object        # float | str | bool | tuple[str, ...]
    unit: str | None = None


@dataclass(frozen=True)
class BenchItem:
    id: str
    text: str
    expect: float | TypedGold


def item_id(question: str) -> str:
    return hashlib.md5(question.encode()).hexdigest()[:12]


def holdout_bucket(question: str) -> str:
    """Stable partition of DEV: never Python's per-process hash()."""
    digest = hashlib.md5(question.encode()).hexdigest()
    return "dev-train" if int(digest, 16) % 2 == 0 else "dev-holdout"


def parse_gold(answer: str) -> float | None:
    m = _GOLD.search(answer)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def load_dataset(parquet_path: Path, question_col: str, answer_col: str) -> list[BenchItem]:
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path, columns=[question_col, answer_col])
    items: list[BenchItem] = []
    for question, answer in zip(
        table.column(question_col).to_pylist(), table.column(answer_col).to_pylist()
    ):
        gold = parse_gold(answer)
        if gold is None:
            continue
        items.append(BenchItem(id=item_id(question), text=question, expect=gold))
    return items


def slice_items(
    train: list[BenchItem], test: list[BenchItem], slice_name: str
) -> list[BenchItem]:
    if slice_name == "dev":
        return train
    if slice_name in ("dev-train", "dev-holdout"):
        return [i for i in train if holdout_bucket(i.text) == slice_name]
    if slice_name == "test":
        return test
    raise ValueError(f"unknown slice {slice_name!r} (one of {ALL_SLICES})")


def record_test_look(ledger_path: Path, fingerprint: str, aggregates: dict) -> None:
    """Every TEST look is spent on the record."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "fingerprint": fingerprint,
        **aggregates,
    }
    with ledger_path.open("a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
