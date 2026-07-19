"""`calendar` — Date arithmetic over ISO and spelled dates.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`
becoming `ctx.` lookups. Pinned across the move by the consumer golden master
and by all eight corpus slices being byte-neutral.
"""

from __future__ import annotations

import datetime

from . import ConsumerContext, consumer


@consumer("calendar")
def calendar(ctx: ConsumerContext):
    from ..answer import Answer

    # Date arithmetic over ISO dates read as WHOLE tokens (tokenize.py's
    # date alternative + numbers.py `_ISO_DATE`). Two ops, both structural
    # opcodes; no unit word appears here -- the span divisor is looked up
    # in pack DATA (`rulekit/calendar@1`), keyed on the lemma the
    # `calendar_span_unit` category gate already matched.

    def _parse(raw):
        try:
            return datetime.date.fromisoformat(str(raw))
        except (TypeError, ValueError):
            # a malformed date declines rather than guessing a component
            return None

    op = ctx.query.get("op", "")
    d1 = _parse(ctx.query.get("d1"))
    if d1 is None:
        return Answer("decline", None, f"{ctx.query.get('d1')!r} is not a readable date")
    if op == "day_of_year":
        return Answer(
            "number", float(d1.timetuple().tm_yday),
            f"calendar: day of year for {d1.isoformat()}",
        )
    if op == "span":
        d2 = _parse(ctx.query.get("d2"))
        if d2 is None:
            return Answer("decline", None, f"{ctx.query.get('d2')!r} is not a readable date")
        unit = str(ctx.query.get("unit", ""))
        days_per = ctx.reg.calendar_span_days.get(unit)
        if days_per is None:
            # the category gate matched a word the DATA has no divisor for
            # -- decline, never fall back to a default of 1 day
            return Answer("decline", None, f"no calendar span divisor for {unit!r}")
        return Answer(
            "number", abs((d2 - d1).days) / days_per,
            f"calendar: span {d1.isoformat()}..{d2.isoformat()} in {unit}",
        )
    return Answer("decline", None, f"unsupported calendar operation {op!r}")
