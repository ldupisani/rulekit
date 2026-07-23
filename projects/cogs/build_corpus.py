"""Materialize the pinned COGS semantic-projection corpus.

Run:

    uv run --extra bench python projects/cogs/build_corpus.py

COGS is fetched from the official MIT-licensed repository at one immutable
revision containing the 2022 correction to 50 generalization rows.  Every
download is SHA-256 verified before parsing.

FIREWALL
--------
The official train split is the inspectable development pool.  A stable hash of
the complete source sentence partitions it into ``dev-train`` and
``dev-holdout`` before campaign mining begins.  The official dev split was
sampled during dataset selection and is therefore named ``calibration`` rather
than falsely presented as untouched.  Official test and gen remain
aggregate-only, ledgered slices.

The builder processes held-out text mechanically but never prints it.  Exact
examples published in the COGS paper/README, duplicates of development text,
and explicitly recorded selection-research exposures remain in the parquet
with audit flags but ``scored=False`` on TEST/generalization.

Data is gitignored; this committed builder, pin, hashes, and salt are the
reproducible corpus contract.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REVISION = "165a7b669eade971fa47bf568a2e51925360fed8"
BASE_URL = (
    "https://raw.githubusercontent.com/najoungkim/COGS/"
    f"{REVISION}/data"
)
SALT = "cogs-dev-holdout@1"  # load-bearing; never change after baseline.

EXPECTED = {
    "train": (
        24_155,
        "220b3804b562c0156ee986eff1bdd15c27e52142549362a64f57baf86e304c78",
    ),
    "dev": (
        3_000,
        "ab66388a309c7ac1ad210c781a6a0ce12281a9ef24619a12422a752cef61bc21",
    ),
    "test": (
        3_000,
        "68f8e51e9f6d9cd22d64efe68dd21d7ea5ba327e9a2359481030161aea757035",
    ),
    "gen": (
        21_000,
        "d013d9eee0bafc153f8decc85f42814ac97260f84964d980e1e2b84577b82361",
    ),
}

# Rows printed while establishing the pin/checksum are explicitly quarantined
# from the honest generalization aggregate.  Store row identity, never sentence
# content, in Python.
SELECTION_EXPOSED = {"gen": frozenset({0, 1})}


@dataclass(frozen=True)
class SourceRow:
    source_split: str
    source_index: int
    text: str
    logical_form: str
    case: str

    @property
    def item_id(self) -> str:
        return f"{self.source_split}-{self.source_index:05d}"


def normalized_text(text: str) -> str:
    flat = " ".join(str(text).split())
    return re.sub(r"\s+([,.!?;:])", r"\1", flat)


def train_bucket(text: str) -> str:
    digest = hashlib.md5((SALT + normalized_text(text)).encode()).hexdigest()
    return "dev-train" if int(digest, 16) % 2 == 0 else "dev-holdout"


def _download(split: str) -> bytes:
    with urllib.request.urlopen(f"{BASE_URL}/{split}.tsv", timeout=60) as response:
        payload = response.read()
    expected_hash = EXPECTED[split][1]
    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"{split}.tsv checksum {actual_hash} != pinned {expected_hash}"
        )
    return payload


def parse_tsv(split: str, payload: bytes) -> list[SourceRow]:
    reader = csv.reader(io.StringIO(payload.decode("utf-8")), delimiter="\t")
    rows: list[SourceRow] = []
    for index, fields in enumerate(reader):
        if len(fields) != 3:
            raise ValueError(
                f"{split}.tsv row {index} has {len(fields)} columns, expected 3"
            )
        text, logical_form, case = fields
        if not text.strip() or not logical_form.strip() or not case.strip():
            raise ValueError(f"{split}.tsv row {index} contains an empty field")
        rows.append(
            SourceRow(
                source_split=split,
                source_index=index,
                text=normalized_text(text),
                logical_form=normalized_text(logical_form),
                case=case.strip(),
            )
        )
    expected_count = EXPECTED[split][0]
    if len(rows) != expected_count:
        raise RuntimeError(
            f"{split}.tsv has {len(rows)} rows, expected {expected_count}"
        )
    return rows


def _published_examples() -> frozenset[str]:
    path = HERE / "published_examples.txt"
    return frozenset(
        normalized_text(line)
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _table(
    rows: list[SourceRow],
    *,
    development_texts: frozenset[str],
    published: frozenset[str],
    held_out: bool,
) -> pa.Table:
    data = {
        "id": [],
        "text": [],
        "logical_form": [],
        "case": [],
        "source_split": [],
        "source_index": [],
        "public_spec": [],
        "duplicate_of_dev": [],
        "selection_exposed": [],
        "scored": [],
    }
    for row in rows:
        public_spec = row.text in published
        duplicate = held_out and row.text in development_texts
        exposed = row.source_index in SELECTION_EXPOSED.get(
            row.source_split, frozenset()
        )
        scored = not held_out or not (public_spec or duplicate or exposed)
        data["id"].append(row.item_id)
        data["text"].append(row.text)
        data["logical_form"].append(row.logical_form)
        data["case"].append(row.case)
        data["source_split"].append(row.source_split)
        data["source_index"].append(row.source_index)
        data["public_spec"].append(public_spec)
        data["duplicate_of_dev"].append(duplicate)
        data["selection_exposed"].append(exposed)
        data["scored"].append(scored)
    return pa.table(data)


def _write(name: str, table: pa.Table) -> None:
    output = HERE / "data" / f"cogs_{name}.parquet"
    pq.write_table(table, output)
    scored = sum(bool(value) for value in table.column("scored").to_pylist())
    print(f"  {name:14} {table.num_rows:6d} rows, {scored:6d} scored -> {output}")


def main() -> None:
    sources = {
        split: parse_tsv(split, _download(split))
        for split in ("train", "dev", "test", "gen")
    }
    published = _published_examples()
    development_texts = frozenset(
        row.text for row in sources["train"] + sources["dev"]
    )
    train_ids = [row.item_id for row in sources["train"]]
    if len(train_ids) != len(set(train_ids)):
        raise RuntimeError("duplicate COGS train item ids")

    dev_train = [
        row for row in sources["train"] if train_bucket(row.text) == "dev-train"
    ]
    dev_holdout = [
        row for row in sources["train"] if train_bucket(row.text) == "dev-holdout"
    ]
    if len(dev_train) + len(dev_holdout) != EXPECTED["train"][0]:
        raise RuntimeError("COGS train partition lost rows")

    (HERE / "data").mkdir(exist_ok=True)
    _write(
        "dev_train",
        _table(
            dev_train,
            development_texts=development_texts,
            published=published,
            held_out=False,
        ),
    )
    _write(
        "dev_holdout",
        _table(
            dev_holdout,
            development_texts=development_texts,
            published=published,
            held_out=False,
        ),
    )
    _write(
        "calibration",
        _table(
            sources["dev"],
            development_texts=development_texts,
            published=published,
            held_out=False,
        ),
    )
    _write(
        "test",
        _table(
            sources["test"],
            development_texts=development_texts,
            published=published,
            held_out=True,
        ),
    )
    _write(
        "generalization",
        _table(
            sources["gen"],
            development_texts=development_texts,
            published=published,
            held_out=True,
        ),
    )
    print(
        f"pin {REVISION}; all four source hashes verified; "
        "TEST/generalization remain unspent"
    )


if __name__ == "__main__":
    main()
