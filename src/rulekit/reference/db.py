"""The DuckDB resolver over the frozen reference tables (plan phase B2).

difg's `datasets.py` made DuckDB the universal read layer; this is that idea
re-homed under rulekit's determinism contract. The kernel stays I/O-free —
this module lives OUTSIDE `kernel/` and only the `reference-aggregate`
consumer calls it.

Determinism, the load-bearing property, is inherited rather than promised:

- The database is DERIVED, never authoritative: every row comes from
  `reg.reference` / `reg.reference_groups`, which are frozen mappings compiled
  from pack YAML in sorted order. Same packs -> same fingerprint -> same rows
  in the same order. There is no import path, no write path, no file.
- One connection per registry fingerprint, built lazily and cached; rows are
  inserted in the mappings' (sorted) iteration order.
- `SET threads TO 1`: DuckDB's parallel SUM may reorder float additions
  between runs, and a last-bit difference between two bench runs would read
  as nondeterminism in the gate. Single-threaded execution pins the order.
  These tables are tiny; parallelism buys nothing here.
- `duckdb` is an OPTIONAL dependency (`pip install rulekit[reference]`).
  Absence maps to the safe outcome: `aggregate` returns None and the
  consumer DECLINES — capability degrades to honesty, never to a guess.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from ..data.registry import Registry

_CONNECTIONS: dict[str, Any] = {}

# op word -> SQL aggregate. The ask shapes carry the op as a LITERAL
# ('total'/'average'), so an op outside this table cannot arrive from text;
# the consumer still checks membership rather than trusting that.
OPS = {"total": "SUM", "average": "AVG"}


def _connect(reg: Registry):
    try:
        import duckdb
    except ImportError:
        return None
    con = _CONNECTIONS.get(reg.fingerprint)
    if con is not None:
        return con
    con = duckdb.connect(":memory:")
    con.execute("SET threads TO 1")
    con.execute(
        "CREATE TABLE facts (entity VARCHAR, attr VARCHAR, year INTEGER, value DOUBLE)"
    )
    con.execute("CREATE TABLE groups (entity VARCHAR, attr VARCHAR, val VARCHAR)")
    for (entity, attr, year), value in reg.reference.items():
        con.execute("INSERT INTO facts VALUES (?, ?, ?, ?)", [entity, attr, year, value])
    for (entity, attr), val in reg.reference_groups.items():
        con.execute("INSERT INTO groups VALUES (?, ?, ?)", [entity, attr, val])
    _CONNECTIONS[reg.fingerprint] = con
    return con


def aggregate(
    reg: Registry,
    op: str,
    attribute: str,
    group_attr: str,
    group_value: str,
    year: int | None,
) -> float | None:
    """SUM/AVG of `attribute` over the entities whose `group_attr` is
    `group_value`, at `year` (None for point attributes). None means
    "cannot answer" — no duckdb, unknown op, or no matching facts — and the
    caller declines; this function never estimates."""
    sql_op = OPS.get(op)
    if sql_op is None:
        return None
    con = _connect(reg)
    if con is None:
        return None
    row = con.execute(
        f"SELECT {sql_op}(f.value) FROM facts f JOIN groups g USING (entity) "
        "WHERE g.attr = ? AND g.val = ? AND f.attr = ? "
        "AND f.year IS NOT DISTINCT FROM ?",
        [group_attr, group_value, attribute, year],
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0])
