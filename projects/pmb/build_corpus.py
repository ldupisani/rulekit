"""Materialize the pinned, licence-filtered PMB 5.1.0 projection corpus.

Run:

    uv run --extra bench python projects/pmb/build_corpus.py

The default source is the extracted sibling directory
``/Users/louis/Development/pmb-5.1.0`` in the current campaign checkout. Use
``--source`` for another byte-identical extraction.

FIREWALL
--------
Only English gold records whose metadata says ``subcorpus: Tatoeba`` are
admitted. PMB annotations are ODC-BY 1.0 and the bundled Tatoeba notice is
CC BY 2.0. Train and development are inspectable. Standard test is
mechanically materialized but aggregate-only and one-look. This builder never
prints raw text, SBN, or protected identifiers.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parents[2] / "pmb-5.1.0"
ALLOWED_SUBCORPUS = "Tatoeba"

PINNED_FILES = {
    "licenses/PMB_LICENSE.txt": (
        "5e173568ea2d8dfe2a0a913e7ee8a924"
        "339a1680ebb469d4d10d3ca61a131abd"
    ),
    "licenses/ODC-BY.txt": (
        "597cb35ae00d3a9284fc748966b830393"
        "5625902ff615ab945d1c151eadc7e97"
    ),
    "licenses/Tatoeba_LICENSE.txt": (
        "da838337e44b466712ed708a637de5d6"
        "b8de1454283130c5de7af74a710b551e"
    ),
    "README": (
        "3a473fd7bdc947165d6b11ee154f746c"
        "86d72fa49991b419c10db8de32289c97"
    ),
    "split/en/train/gold.sbn": (
        "a93a9ef831935d4164959c4bfeb66e19"
        "317e8beb47b62394cbb2919a9aa0f893"
    ),
    "split/en/dev/standard.sbn": (
        "111167f3a42b5c61db3567205ed2c146"
        "3e01d93f4e06b8c2aae8c0c6217b1770"
    ),
    "split/en/test/standard.sbn": (
        "602183b2c06bd4d22130cafcc5eaa757"
        "2b8f95dc6ae0381b1eec9de82bdda546"
    ),
}

EXPECTED = {
    "train": (9_552, 9_065),
    "development": (1_194, 990),
    "test": (1_194, 923),
}


@dataclass(frozen=True)
class SplitRecord:
    item_id: str
    text: str
    sbn: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_release(source: Path) -> None:
    for relative, expected in PINNED_FILES.items():
        path = source / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned PMB file: {path}")
        actual = _sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"PMB checksum mismatch for {relative}: {actual} != {expected}"
            )


def parse_split(payload: str) -> list[SplitRecord]:
    lines = payload.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) % 4:
        raise ValueError("PMB split does not contain four-line records")
    records: list[SplitRecord] = []
    for offset in range(0, len(lines), 4):
        item_id, text, sbn, separator = lines[offset:offset + 4]
        if separator:
            raise ValueError("PMB split record lacks an empty separator line")
        if not item_id or not text.strip() or not sbn.strip():
            raise ValueError("PMB split record contains an empty required field")
        if not (
            len(item_id) == 9
            and item_id.startswith("p")
            and item_id[3:5] == "/d"
            and item_id[1:3].isdigit()
            and item_id[5:].isdigit()
        ):
            raise ValueError(f"invalid PMB document id {item_id!r}")
        records.append(SplitRecord(item_id, text.strip(), sbn.strip()))
    return records


def read_metadata(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"invalid PMB metadata line in {path}")
        values[key.strip()] = value.strip()
    return values


def eligible(source: Path, record: SplitRecord) -> bool:
    metadata = read_metadata(
        source / "data" / "en" / "gold" / record.item_id / "en.met"
    )
    return metadata.get("subcorpus") == ALLOWED_SUBCORPUS


def _table(records: list[SplitRecord]) -> pa.Table:
    return pa.table({
        "id": [record.item_id for record in records],
        "text": [record.text for record in records],
        "logical_form": [record.sbn for record in records],
        "case": [ALLOWED_SUBCORPUS for _record in records],
        "scored": [True for _record in records],
    })


def _write(name: str, records: list[SplitRecord]) -> None:
    output = HERE / "data" / f"pmb_{name}.parquet"
    pq.write_table(_table(records), output)
    print(f"  {name:12} {len(records):5d} eligible rows -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    verify_release(source)

    split_paths = {
        "train": source / "split/en/train/gold.sbn",
        "development": source / "split/en/dev/standard.sbn",
        "test": source / "split/en/test/standard.sbn",
    }
    selected: dict[str, list[SplitRecord]] = {}
    for name, path in split_paths.items():
        records = parse_split(path.read_text(encoding="utf-8"))
        expected_all, expected_eligible = EXPECTED[name]
        if len(records) != expected_all:
            raise RuntimeError(
                f"{name} has {len(records)} records, expected {expected_all}"
            )
        admitted = [record for record in records if eligible(source, record)]
        if len(admitted) != expected_eligible:
            raise RuntimeError(
                f"{name} has {len(admitted)} eligible records, "
                f"expected {expected_eligible}"
            )
        selected[name] = admitted

    (HERE / "data").mkdir(exist_ok=True)
    for name in ("train", "development", "test"):
        _write(name, selected[name])
    print(
        "PMB 5.1.0 pins verified; Tatoeba-only allowlist enforced; "
        "protected TEST remains unspent"
    )


if __name__ == "__main__":
    main()
