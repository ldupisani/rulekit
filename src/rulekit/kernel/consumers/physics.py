"""`physics` — A named physical quantity from its formula table.

Moved out of `answer.py` UNCHANGED (the extraction increment). Every branch,
message and computation is the original; the only edits are `query`/`reg`/
`question`/`log` becoming `ctx.` lookups.

This tier always reads the question and may read the original premise readings
when the selected formula explicitly declares document scope. A document-scoped
formula owns every accounted value in those readings and declines if any stated
value cannot bind to an expression-referenced dimension.
"""

from __future__ import annotations

import re

from ..dimensions import bind_count_to_dimension
from ..evaluate import evaluate
from . import ConsumerContext, consumer


@consumer("physics")
def physics(ctx: ConsumerContext):
    # `_ACCOUNTED_VALUE_KINDS` is imported rather than copied: it is the ONE
    # definition of which value kinds must be accounted for, and this repo has
    # already paid for a second copy of that contract drifting.
    from ..answer import _ACCOUNTED_VALUE_KINDS, Answer

    # The difg `physics` domain: a NAMED physical quantity computed from the
    # parameters its formula scope admits — "the speed of an object that travels
    # 100 meters in 5 seconds". The formulas and the unit->dimension map are
    # DATA (packs/difg-mined/formulas.yaml); this branch is the generic
    # evaluator and names no quantity, no unit and no formula (rule 1). Same
    # shape as the `geometry` consumer above, minus the shape key.
    # Ask templates may preserve a compound quantity's modifier by rendering
    # "{q.qualifier} {q}".  A BARE quantity has no qualifier and therefore
    # renders with one harmless leading space; normalize the lookup key here so
    # every existing bare formula remains byte-compatible while qualified keys
    # ("maximum wavelength", "initial speed") stay exact.
    quantity = ctx.query.get("quantity", "").strip()
    expr = ctx.reg.quantity_formulas.get(quantity)
    if expr is None:
        return Answer("decline", None, f"no formula for the {quantity!r} of a thing")
    scope = ctx.reg.quantity_formula_scopes.get(quantity, "question")
    # The names the formula ACTUALLY references. "Read" means the expression
    # uses it — NOT merely that some dimension could be bound from it. Those
    # two sets differ, and the gap is a silent-ignore: "the weight of a 3 kg
    # object THAT TRAVELS 60 METERS IN 4 SECONDS" binds distance and time,
    # `mass * 9.8` never mentions them, and nothing would decline. Deriving
    # the set from the expr keeps this honest for formulas that do not exist
    # yet (the `_TOKEN` increment adds velocity/acceleration dimensions, which
    # is exactly when a bindable-but-unused value stops being harmless).
    read_names = set(re.findall(r"[a-z_][a-z_0-9]*", expr))

    # Bind each stated number by the DIMENSION OF ITS OWN UNIT, never by
    # position — "an object that took 5 seconds to travel 100 meters" must
    # read identically to the same facts in the other order. The unit is the
    # counted unit's LEMMA ("100 meters" -> 'meter'), or its QUALIFIER when
    # the noun itself is not a unit ("a 2 kg object" -> lemma 'object',
    # qualifier 'kilogram').
    env: dict[str, float] = {}
    readings = (*ctx.premises, ctx.question) if scope == "document" else (ctx.question,)
    for u in (
        unit
        for reading in readings
        for unit in reading.units
    ):
        kind = u.features.get("value_kind")
        # MIRROR guards.py's accounted kinds EXACTLY. This branch takes that
        # guard's exemption, so whatever it would have checked is now this
        # consumer's duty — and it accounts for count/multiplier/fraction,
        # not counts alone. A multiplier or a fraction is never a dimension
        # operand ("...in 4 seconds TWICE", "...and HALF of that"), so a
        # stated one is a quantity the formula provably did not read.
        if kind not in _ACCOUNTED_VALUE_KINDS:
            continue
        if kind != "count":
            return Answer(
                "decline", None,
                f"{quantity!r} cannot read the stated {u.surface!r}",
            )
        value = float(u.features["value"])
        # BIND BY THE DIMENSION OF THE UNIT'S OWN DIMENSION-ALGEBRA MODULE.
        # The resolution order (direct unit_dimension hit on lemma or
        # qualifier; scale-to-canonical through conversions@1 and the affine
        # table keyed on the merged LABEL; ambiguity or no-reach -> None) is
        # the shared `dimensions.bind_count_to_dimension` — one contract for
        # every consumer that binds a number by its own unit's dimension.
        # None here means unbound or ambiguous; the decline below is the
        # safe outcome, exactly as for an unknown unit.
        bound = bind_count_to_dimension(
            ctx.reg,
            value=value,
            lemma=u.features.get("lemma"),
            qualifier=u.features.get("qualifier"),
            label=u.features.get("label"),
            read_names=read_names,
        )
        if bound is None:
            # AN UNREAD COUNT IS A DECLINE. This branch takes the guards.py
            # value-accounting exemption (_WHOLE_LIST_CONSUMERS), so nothing
            # downstream will catch a number the formula silently ignored:
            # "travels 60 meters in 4 seconds AND 3 MINUTES" would commit 15
            # (the true answer is 0.33) because 'minute' denominates no
            # dimension here. Taking the exemption means OWNING the
            # accounting, so every stated count must be read or the whole
            # commit goes.
            return Answer(
                "decline", None,
                f"{quantity!r} cannot read the stated {u.surface!r}",
            )
        dim, value = bound
        if dim in env:
            # ANY second value for a dimension, not just a DIFFERENT one:
            # "60 meters then 60 meters" is as unreadable as "60 then 50"
            # (the true distance is 120), and comparing values would let the
            # equal case through — the same-value blind spot guards.py's own
            # Counter exists to close. The question states more than the
            # formula can consume; picking one is a guess either way.
            return Answer(
                "decline", None,
                f"two {dim!r} values stated — {quantity!r} cannot choose",
            )
        env[dim] = value
    # Register the operands so the arithmetic log shows what was read (the
    # `list-statistic` lesson); the sum is only the logging vehicle. `env`
    # holds ONLY expr-referenced dimensions, so what is logged is what the
    # answer actually READ — logging the merely-bindable would launder a
    # value the formula ignored into `log.uses_value()`, which other guards
    # consult as evidence. Every accounted value either reaches here or has
    # already declined, so this honours _WHOLE_LIST_CONSUMERS' contract.
    if env:
        evaluate(" + ".join(f"{v:g}" for v in env.values()), {}, ctx.log, source="physics")
    try:
        result = evaluate(expr, env, ctx.log, source="physics")
    except Exception:
        # A dimension the question never supplied leaves its name unbound and
        # `evaluate` raises — the definitive-or-decline path, and the ONLY
        # guard the shredded compound units need: "3 m/s^2" never yields an
        # 'acceleration', so `force` declines here rather than guessing from
        # whatever numbers happen to be lying around (including the exponent).
        return Answer(
            "decline", None,
            f"{quantity!r} needs parameters the question does not supply",
        )
    return Answer("number", float(result), f"physics: {quantity} = {expr} = {result}")
