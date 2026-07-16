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
    # holdout-grouping key (schemas.DatasetDef.group): items sharing it land on
    # the same side of the dev-train/dev-holdout cut. None => bucket on text.
    group: str | None = None


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


# TYPED-GOLD payload shapes, classified STRUCTURALLY — by punctuation and digit
# morphology, never by a unit word list. A harness that enumerated units would be
# smuggling a lexicon into Python (constitution rule 1) AND would silently drop
# any gold whose unit it had not been taught. "$5" is money because of the '$';
# "50%" is a percent because of the '%'; "68.04 kg" is a quantity because a
# number is followed by a non-numeric run — whatever that run says.
_MONEY = re.compile(r"^\$\s*([-+]?[\d,]*\.?\d+)$")
_PERCENT = re.compile(r"^([-+]?[\d,]*\.?\d+)\s*%$")
_QUANTITY = re.compile(r"^([-+]?[\d,]*\.?\d+)\s*([^\d\s].*)$")
_NUMBER = re.compile(r"^([-+]?[\d,]*\.?\d+)$")


def parse_typed_gold(answer: str) -> TypedGold | None:
    """Classify a `#### <payload>` gold into a TypedGold, or None if unreadable.

    Only a `gold: typed` dataset reaches this (schemas.DatasetDef.gold); every
    other project keeps `parse_gold`'s float path byte-for-byte.

    An UNREADABLE payload returns None and the row is dropped, exactly as a
    malformed float row is today — a gold we cannot classify is not a gold we
    are willing to score against.
    """
    payload = answer.split("####", 1)[-1].strip() if "####" in answer else answer.strip()
    if not payload:
        return None
    flat = payload.replace(",", "")
    m = _NUMBER.match(flat)
    if m:
        return TypedGold(kind="number", value=float(m.group(1)))
    m = _MONEY.match(flat)
    if m:
        return TypedGold(kind="money", value=float(m.group(1)))
    m = _PERCENT.match(flat)
    if m:
        return TypedGold(kind="percent", value=float(m.group(1)))
    if flat.strip().lower() in ("true", "false", "yes", "no"):
        return TypedGold(kind="verdict", value=flat.strip().lower())
    m = _QUANTITY.match(flat)
    if m:
        return TypedGold(kind="quantity", value=float(m.group(1)), unit=m.group(2).strip())
    # text / entity / set — a bare non-numeric payload. Kept as text; the set
    # shape is not split here because a comma is not reliably a set separator
    # (it is also a thousands mark and a clause break), and guessing would
    # manufacture golds rather than read them.
    return TypedGold(kind="text", value=payload)


def load_dataset(
    parquet_path: Path,
    question_col: str,
    answer_col: str,
    gold: str | None = None,
    group_col: str | None = None,
) -> list[BenchItem]:
    import pyarrow.parquet as pq

    columns = [question_col, answer_col] + ([group_col] if group_col else [])
    table = pq.read_table(parquet_path, columns=columns)
    groups = table.column(group_col).to_pylist() if group_col else None
    items: list[BenchItem] = []
    for row, (question, answer) in enumerate(
        zip(table.column(question_col).to_pylist(), table.column(answer_col).to_pylist())
    ):
        # `gold is None` is the DEFAULT and the pre-existing path, unchanged.
        expect = parse_typed_gold(answer) if gold == "typed" else parse_gold(answer)
        if expect is None:
            continue
        items.append(
            BenchItem(
                id=item_id(question),
                text=question,
                expect=expect,
                group=groups[row] if groups else None,
            )
        )
    return items


def slice_items(
    train: list[BenchItem], test: list[BenchItem], slice_name: str
) -> list[BenchItem]:
    if slice_name == "dev":
        return train
    if slice_name in ("dev-train", "dev-holdout"):
        # bucket on the grouping key when the dataset declares one, so items
        # sharing a premise block never straddle the internal cut; item id and
        # text are untouched — only WHICH side an item lands on can differ.
        return [i for i in train if holdout_bucket(i.group or i.text) == slice_name]
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
