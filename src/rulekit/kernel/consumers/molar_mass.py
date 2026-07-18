"""`molar-mass` — the chemistry consumer.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`log`
becoming `ctx.` lookups and the inline `import re` becoming a module-level
compiled pattern; every branch, message and computation is the original.

Behaviour is pinned from two directions across the move: the consumer golden
master asserts routing and outcome for this consumer's probes, and all eight
corpus slices are byte-neutral.
"""

from __future__ import annotations

import re

from ..evaluate import EvaluationError, evaluate
from . import ConsumerContext, consumer

_PART = re.compile(r"([A-Z][a-z]?)(\d*)")


@consumer("molar-mass")
def molar_mass(ctx: ConsumerContext):
    # Sum the atomic masses of a formula's symbols, each times its subscript.
    # Masses are DATA (`rulekit/elements@1`); no element is named here.
    # numbers.py has already validated every symbol against that same table, so
    # an unknown symbol cannot reach this consumer — but it is re-checked
    # rather than assumed, because the reader and the consumer are reached by
    # different paths and a table loaded without the other is a real
    # configuration.
    from ..answer import Answer

    raw = str(ctx.query.get("formula", ""))
    parts = _PART.findall(raw)
    if not raw or not parts:
        return Answer("decline", None, f"{raw!r} is not a readable formula")
    molar = 0.0
    for sym, count in parts:
        mass = ctx.reg.atomic_masses.get(sym)
        if mass is None:
            return Answer("decline", None, f"no atomic mass known for {sym!r}")
        molar += mass * (int(count) if count else 1)

    op = ctx.query.get("op", "mass")
    if op == "mass":
        return Answer("number", molar, f"molar-mass: {raw} = {molar}")

    try:
        amount = float(ctx.query.get("amount"))
    except (TypeError, ValueError):
        return Answer("decline", None, f"{op!r} needs a numeric amount")
    if molar <= 0:
        return Answer("decline", None, f"{raw!r} has no usable molar mass")

    if op == "moles_from_grams":
        return Answer("number", amount / molar,
                      f"molar-mass: {amount} g of {raw} = {amount / molar} mol")
    grams = amount * molar          # amount is in MOLES for the ops below
    if op == "cost_of_moles":
        try:
            rate = float(ctx.query.get("rate"))
        except (TypeError, ValueError):
            return Answer("decline", None, "a cost needs a numeric rate")
        return Answer("number", grams * rate,
                      f"molar-mass: {amount} mol of {raw} = {grams} g at {rate}")
    if op == "weight_of_moles":
        # NO CONSTANT HERE. The gram->kilogram factor is in the conversions
        # table and g lives inside `rulekit/formulas@1`'s `weight`
        # expression, exactly as it does for the physics consumer — so this
        # branch names neither a unit nor 9.8.
        factor = ctx.reg.conversions.get(("gram", "kilogram"))
        expr = ctx.reg.quantity_formulas.get("weight")
        if factor is None or expr is None:
            return Answer("decline", None,
                          "weight needs the gram->kilogram conversion and the "
                          "`weight` formula, and this project declares neither")
        try:
            value = evaluate(expr, {"mass": grams * factor}, ctx.log, source="molar-mass")
        except EvaluationError as exc:
            return Answer("decline", None, f"weight formula failed: {exc}")
        return Answer("number", value,
                      f"molar-mass: {amount} mol of {raw} = {grams} g -> {value}")
    return Answer("decline", None, f"unsupported molar-mass operation {op!r}")
