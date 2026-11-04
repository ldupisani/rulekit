"""Average the individually required rates over fully observed goal prefixes."""

from collections import Counter, defaultdict
from math import isfinite, isclose

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..model import BatchEvidence
from ..evaluate import evaluate
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_duration, convert_units
from ..reference_bindings import anaphoric_forms_agree, referenced_forms_agree
from ..reference_identity import reference_from_unit
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_document_units, covered_temporal_annotation


@consumer("mean-required-rate")
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    groups = [r for r in rows if r.kind == "completion-group"]
    goals = [r for r in rows if r.kind == "completion-target"]
    progress = [r for r in rows if r.kind in {"completion-rate", "completion-amount"}]
    if (
        len(groups) != 1
        or len(goals) != 1
        or not progress
        or len(rows) != 2 + len(progress)
        or ctx.store.collisions
        or ctx.store.quarantined
    ):
        return decline(
            "one named completion group, deadline and complete progress account are required"
        )
    group = groups[0]
    goal = goals[0]
    members = group.members
    if (
        len(members) < 2
        or len(set(members)) != len(members)
        or goal.verb != ctx.query["verb"]
        or any(r.provenance.assumption for r in rows)
        or (
            set(goal.members) != set(members)
            if goal.members
            else not anaphoric_forms_agree([goal.container], "plural", ctx.reg)
        )
        or not anaphoric_forms_agree(
            [ctx.match.slots[s].surface for s in ("poss", "group")], "plural", ctx.reg
        )
    ):
        return decline(
            "the plural goal and question must refer to the same complete group"
        )
    if not goal.attribute and not group.container:
        return decline(
            "a shared goal must explicitly apply to each participant outside a competition context"
        )
    elapsed = float(ctx.query["elapsed"])
    period = ctx.query["period"]
    deadline = convert_duration(
        goal.per_member,
        goal.marker,
        period,
        ctx.reg,
        ctx.log,
        source="completion-deadline-period",
    )
    if deadline is None or elapsed <= 0 or deadline <= elapsed:
        return decline(
            "the final interval must be a proper, compatible part of the deadline"
        )
    for qualifier in group.container_ref.qualifiers if group.container_ref else ():
        if ctx.reg.word_in_category(qualifier, "duration_measure"):
            span = convert_duration(
                1,
                qualifier,
                period,
                ctx.reg,
                ctx.log,
                source="competition-context-duration",
            )
            if span is None or not isclose(span, deadline):
                return decline("the competition length contradicts its deadline")
        elif not ctx.reg.word_in_category(qualifier, "duration_extent_descriptor"):
            return decline("the completion context has an unsupported restriction")
    expected = defaultdict(Counter)
    assumptions = []
    expected[goal.provenance.sentence][goal.value] += 1
    if goal.acquisition == "implicit-unit":
        if goal.per_member != 1:
            return decline("an indefinite singular deadline must denote one period")
    elif goal.acquisition:
        return decline("the deadline's quantity basis is unknown")
    else:
        expected[goal.provenance.sentence][goal.per_member] += 1
    if not goal.attribute:
        assumptions.append(AnswerAssumption(
            "individual-competition-goal",
            "The stated goal applies separately to each participant, rather than to their combined total.",
            (group.provenance.sentence, goal.provenance.sentence),
        ))
    expected[ctx.question.sentence_index][elapsed] += 1
    work = defaultdict(list)
    for row in progress:
        if (
            row.entity not in members
            or row.entity_ref is None
            or not row.entity_ref.resolved
            or not referenced_forms_agree(
                (*ctx.premises, ctx.question), row.entity_ref, ctx.reg
            )
            or not isfinite(row.value)
            or row.value < 0
        ):
            return decline(
                "each progress amount must identify one participant and compatible reference forms"
            )
        expected[row.provenance.sentence][row.value] += 1
        amount = convert_units(
            row.value,
            row.measure,
            goal.measure,
            ctx.reg,
            ctx.log,
            source="progress-quantity-unit",
        )
        if amount is None:
            return decline("progress must measure the same quantity as the goal")
        if row.kind == "completion-rate":
            if not row.attribute:
                assumptions.append(AnswerAssumption(
                    "prefix-average-per-period",
                    "An average over the initial interval is interpreted per stated period.",
                    (row.provenance.sentence,),
                ))
            expected[row.provenance.sentence][row.fraction] += 1
            end = convert_duration(
                row.fraction,
                row.marker,
                period,
                ctx.reg,
                ctx.log,
                source="observed-prefix-period",
            )
            base = convert_duration(
                row.fraction,
                row.marker,
                row.attribute or row.marker,
                ctx.reg,
                ctx.log,
                source="prefix-rate-periods",
            )
            if end is None or base is None:
                return decline("the averaged prefix has incompatible units")
            amount = evaluate(
                "rate * periods",
                {"rate": amount, "periods": base},
                ctx.log,
                source="prefix-average-total",
            )
            start = 0
        else:
            index = ctx.reg.attrs.get(row.acquisition, {}).get("ordinal_index")
            if index is None:
                try:
                    index = float(row.marker)
                except ValueError:
                    return decline(
                        "an indexed observation needs a declared numeric or ordinal period"
                    )
            if index < 1 or not float(index).is_integer() or row.verb != goal.verb:
                return decline(
                    "indexed observations require positive whole period indices and matching activity"
                )
            start = convert_duration(
                index - 1,
                row.attribute,
                period,
                ctx.reg,
                ctx.log,
                source="indexed-progress-start",
            )
            end = convert_duration(
                index,
                row.attribute,
                period,
                ctx.reg,
                ctx.log,
                source="indexed-progress-end",
            )
            if start is None or end is None:
                return decline("the indexed progress period is incompatible")
        if end <= start or end > deadline - elapsed:
            return decline("an observation lies outside the completed prefix")
        work[row.entity].append((start, end, amount))
    needed = []
    for member in members:
        end = 0
        amounts = []
        for start, stop, value in sorted(work[member]):
            if not isclose(start, end, abs_tol=1e-8):
                return decline(
                    "each observed prefix must be complete, disjoint and consecutive"
                )
            end = stop
            amounts.append(value)
        if not isclose(end, deadline - elapsed, abs_tol=1e-8):
            return decline(
                "all participants need progress through the same final interval"
            )
        remaining = resource_residual(
            [goal.value], amounts, ctx.log, source="individual-goal-remainder"
        )
        if remaining < 0:
            return decline("observed progress exceeds the stated completion goal")
        needed.append(
            evaluate(
                "remaining / periods",
                {"remaining": remaining, "periods": elapsed},
                ctx.log,
                source="required-individual-rate",
            )
        )
    annotations = [f for f in ctx.store.facts if not isinstance(f, BatchEvidence)]
    if any(
        not any(
            covered_temporal_annotation(
                f,
                ctx.premises,
                row.entity,
                {
                    (
                        row.provenance.sentence,
                        row.marker if row.kind == "completion-rate" else row.attribute,
                    )
                },
            )
            for row in progress
        )
        for f in annotations
    ):
        return decline("an additional event lies outside the completion account")
    if uncovered_document_units(
        ctx.premises, ctx.question, ctx.match.consumed
    ) or audit_numeric_mentions(
        (*ctx.premises, ctx.question),
        expected,
        missing="missing",
        duplicate="duplicate",
    ):
        return decline("every deadline, index, rate and progress amount must be read")
    total = evaluate(
        " + ".join(map(str, needed)), {}, ctx.log, source="required-rates-sum"
    )
    value = evaluate(
        "total / participants",
        {"total": total, "participants": len(members)},
        ctx.log,
        source="mean-required-rate",
    )
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    return Answer(
        "number",
        value,
        "mean of the individual required rates; each participant has the stated goal and an initial-period average is per stated period",
        assumptions=tuple(assumptions),
    )
