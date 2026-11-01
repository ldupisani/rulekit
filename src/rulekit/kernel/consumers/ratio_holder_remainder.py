"""Determine a named share of a joint pool, then apply its own withdrawal."""

from collections import Counter, defaultdict
from math import isfinite, isclose

from . import consumer
from ..answer import Answer
from ..model import AllocationRatio, BatchEvidence, GroupTotal
from ..evaluate import evaluate
from ..numeric_evidence import audit_numeric_mentions
from ..reference_bindings import anaphoric_forms_agree, referenced_forms_agree
from ..reference_identity import reference_from_unit
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units


@consumer("ratio-holder-remainder")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    ratios = list(ctx.store.by_kind(AllocationRatio))
    rows = list(ctx.store.by_kind(BatchEvidence))
    pools = [r for r in rows if r.kind == "ratio-pool"]
    totals = list(ctx.store.by_kind(GroupTotal))
    for total in totals:
        reading = next(
            (r for r in ctx.premises if r.sentence_index == total.provenance.sentence),
            None,
        )
        names = (
            [reference_from_unit(u).head for u in reading.units if u.sense() == "name"]
            if reading
            else []
        )
        if len(names) != 2 or total.scope:
            return decline(
                "a joint total must identify exactly the ordered ratio holders"
            )
        pools.append(
            BatchEvidence(
                provenance=total.provenance,
                kind="ratio-pool",
                entity=names[0],
                measure=total.measure,
                value=total.value,
                position=0,
                container=names[1],
                marker="named",
            )
        )
    withdrawals = [r for r in rows if r.kind == "ratio-withdrawal"]
    if (
        len(ratios) != 1
        or len(pools) != 1
        or not withdrawals
        or len(rows) + len(totals) != 1 + len(withdrawals)
        or len(ctx.store.facts) != 1 + len(rows) + len(totals)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one ordered ratio, joint pool and complete personal withdrawal account are required"
        )
    ratio = ratios[0]
    pool = pools[0]
    who = reference_from_unit(ctx.match.slots["who"])
    if not who.resolved and ctx.match.slots["who"].sense() == "pronoun":
        latest = max((r.sentence_index for r in ctx.premises), default=-1)
        owners = {r.entity_ref for r in withdrawals if r.provenance.sentence == latest}
        if len(owners) != 1 or None in owners:
            return decline(
                "the follow-up has no unique immediately preceding depleted holder"
            )
        who = next(iter(owners))
        forms = [
            u.surface
            for reading in ctx.premises
            for u in reading.units
            if u.sense() == "pronoun"
            and reference_from_unit(u) == who
            and getattr(
                ctx.reg.lexicon.get(u.surface.casefold()), "anaphoric_form", None
            )
        ]
        if not anaphoric_forms_agree(
            [*forms, ctx.match.slots["who"].surface], "singular", ctx.reg
        ):
            return decline(
                "the follow-up pronoun conflicts with the depleted holder reference"
            )
    members = (ratio.first, ratio.second)
    described = [
        u
        for reading in ctx.premises
        for u in reading.units
        if u.sense() == "noun"
        and u.features.get("lemma") == ratio.resource
        and reference_from_unit(u).qualifiers
    ]
    if described:
        return decline("a qualified resource needs an equally qualified ratio pool")
    if (
        who.head not in members
        or members[0] == members[1]
        or ratio.group_size != 2
        or pool.measure != ratio.resource
        or ctx.query["measure"] not in ("", ratio.resource)
        or ratio.provenance.assumption
        or pool.provenance.sentence < ratio.provenance.sentence
        or any(
            not isfinite(v) or v < 0
            for v in (ratio.numerator, ratio.denominator, pool.value)
        )
        or ratio.numerator + ratio.denominator <= 0
        or not float(pool.value).is_integer()
        or not referenced_forms_agree((*ctx.premises, ctx.question), who, ctx.reg)
    ):
        return decline(
            "the ordered holders, nonnegative ratio parts and discrete pool must agree"
        )
    if pool.marker == "named":
        if {pool.entity, pool.container} != set(members):
            return decline("the total names a different holder group")
    elif pool.members:
        if set(pool.members) != set(members):
            return decline("the total names a different holder group")
    elif not anaphoric_forms_agree([pool.container], "plural", ctx.reg):
        return decline("the total must refer to the complete ratio group")
    parts = (ratio.numerator, ratio.denominator)
    opening = evaluate(
        "total * share / parts",
        {
            "total": pool.value,
            "share": parts[members.index(who.head)],
            "parts": sum(parts),
        },
        ctx.log,
        source="ordered-holder-share",
    )
    if not isclose(opening, round(opening), abs_tol=1e-8):
        return decline("the ratio does not produce whole item shares")
    expected = defaultdict(Counter)
    expected[ratio.provenance.sentence].update(parts)
    expected[pool.provenance.sentence][pool.value] += 1
    balance = opening
    for row in sorted(withdrawals, key=lambda r: (r.provenance.sentence, r.position)):
        if (
            row.entity_ref != who
            or row.provenance.sentence < pool.provenance.sentence
            or not 0 <= row.value <= 1
        ):
            return decline(
                "a withdrawal must refer to the requested holder after the joint total"
            )
        expected[row.provenance.sentence][row.value] += 1
        used = evaluate(
            "balance * fraction",
            {"balance": balance, "fraction": row.value},
            ctx.log,
            source="personal-share-withdrawal",
        )
        balance = resource_residual(
            [balance], [used], ctx.log, source="personal-share-balance"
        )
        if not isclose(balance, round(balance), abs_tol=1e-8):
            return decline("discrete remainders must be whole counts")
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline(
            "every ratio part, total, personal fraction and condition must be read"
        )
    ctx.log.consumed_allocation_ratio_keys.add(ratio.key())
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        balance,
        "allocate the ordered ratio share, then subtract only that holder’s stated fractional spending",
    )
