"""`reference-aggregate` — SUM/AVG of a reference attribute over a named group.

"What is the total population of Europe in 2020?" — the question a point
lookup structurally cannot answer: the answer is computed over the SET of
entities whose group column (continent) names Europe. The set membership and
the arithmetic run in DuckDB (rulekit.reference.db — plan phase B2), derived
from the same frozen tables the lookup consumer reads, so determinism is
inherited, not re-proven.

Decline map, all of it data-driven (no group, attribute or op is named here):
- group value found in NO group column      -> decline (Narnia)
- group value found in TWO group columns    -> decline (ambiguous set —
  choosing one would be a guess, the same rule as physics' two-values case)
- by-year attribute with no stated year     -> no rows match, decline
- duckdb not installed                      -> decline (the optional-extra
  contract: absence degrades to honesty, never to a guess)
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("reference-aggregate")
def reference_aggregate(ctx: ConsumerContext):
    from ...reference import db
    from ..answer import Answer

    op = ctx.query.get("op", "")
    attribute = ctx.query.get("attribute", "")
    group_value = str(ctx.query.get("group", "")).strip().lower()
    if op not in db.OPS or not attribute or not group_value:
        return Answer("decline", None, "an aggregate needs an op, an attribute and a group")
    year: int | None = None
    raw_year = ctx.query.get("year")
    if raw_year is not None:
        try:
            year = int(float(raw_year))
        except (TypeError, ValueError):
            return Answer("decline", None, f"cannot read {raw_year!r} as a year")

    # which group COLUMN holds this value ("europe" -> continent)? Resolved
    # from the frozen mapping; a value claimed by two columns is ambiguous
    # and ambiguity declines, exactly as physics declines two same-dimension
    # values rather than choosing.
    columns = sorted({a for (_e, a), v in ctx.reg.reference_groups.items() if v == group_value})
    if not columns:
        return Answer("decline", None, f"no reference group named {group_value!r}")
    if len(columns) > 1:
        return Answer(
            "decline", None,
            f"group {group_value!r} is ambiguous across {columns}",
        )

    result = db.aggregate(ctx.reg, op, attribute, columns[0], group_value, year)
    if result is None:
        when = f" in {year}" if year is not None else ""
        return Answer(
            "decline", None,
            f"cannot aggregate the {attribute!r} of {group_value!r}{when}",
        )
    when = f" in {year}" if year is not None else ""
    return Answer(
        "number", float(result),
        f"reference-aggregate: {op} {attribute} of {group_value}{when} = {result:g}",
    )
