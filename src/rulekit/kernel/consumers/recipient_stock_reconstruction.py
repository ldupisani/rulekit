"""Recover an opening stock from recipient outcomes and a closing remainder."""

from math import isfinite
from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..answer import Answer
from ..model import BatchEvidence, Quantity
from ..reference_identity import ReferenceIdentity, constrains
from ..affine_graph import AffineGraph, AffineError
from ..resource_equations import resource_residual


@consumer(
    "recipient-stock-reconstruction",
    applicable=lambda s: any(
        r.kind == "transfer-opening" for r in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    quantities = list(ctx.store.by_kind(Quantity))
    facts = [*rows, *quantities]
    starts = [r for r in rows if r.kind == "transfer-opening"]
    ends = [r for r in rows if r.kind == "transfer-closing"]
    outcomes = [r for r in rows if r.kind in {"recipient-amount", "recipient-relation"}]
    if (
        len(starts) != 1
        or len(ends) != 1
        or not (outcomes or quantities)
        or len(rows) != 2 + len(outcomes)
    ):
        return Answer(
            "decline",
            None,
            "one opening population, complete recipient outcomes and closing remainder are required",
        )
    start, end = starts[0], ends[0]
    # The shared transfer reader already records both sides. Use one local
    # outcome view per matched pair; keep the original ledger intact.
    pending = list(quantities)
    while pending:
        senders = [
            q
            for q in pending
            if q.entity_ref == start.entity_ref
            and ctx.reg.word_in_category(q.verb, "transfer_out")
        ]
        if not senders:
            return Answer(
                "decline",
                None,
                "an additional holding lies outside the transfer account",
            )
        sender = senders[0]
        receivers = [
            q
            for q in pending
            if q is not sender
            and q.provenance == sender.provenance
            and q.occurrence == sender.occurrence
            and q.measure == sender.measure
            and q.value == sender.value
            and ctx.reg.word_in_category(q.verb, "allocation_receipt_verb")
        ]
        if (
            len(receivers) != 1
            or sender.measure != start.measure
            or any(
                q.owner
                or q.qualifier
                or q.measure_qualifier
                or q.label
                or q.time
                or q.provenance.distributive
                or q.provenance.assumption
                for q in (sender, *receivers)
            )
        ):
            return Answer(
                "decline",
                None,
                "each observed transfer needs one matching unqualified receipt",
            )
        receiver = receivers[0]
        if receiver.entity_ref == start.entity_ref or not receiver.entity_ref.resolved:
            return Answer(
                "decline",
                None,
                "the transferred stock needs a distinct resolved recipient",
            )
        outcomes.append(
            BatchEvidence(
                provenance=sender.provenance,
                kind="recipient-amount",
                entity=sender.entity,
                entity_ref=sender.entity_ref,
                measure=sender.measure,
                value=sender.value,
                position=0,
                container=receiver.entity,
                container_ref=receiver.entity_ref,
                verb=sender.verb,
            )
        )
        pending.remove(sender)
        pending.remove(receiver)
    asked = (
        ReferenceIdentity.from_dict(ctx.query["evidence_entity_reference"])
        if ctx.query.get("evidence_entity_reference")
        else ReferenceIdentity(ctx.query["entity"])
    )
    if (
        not constrains(asked, start.entity_ref)
        or start.measure != ctx.query["measure"]
        or end.measure != start.measure
        or any(r.entity_ref != start.entity_ref for r in rows)
        or any(r.provenance.assumption for r in rows if r is not end)
        or any(r.measure and r.measure != start.measure for r in outcomes)
        or len({r.container_ref for r in outcomes}) != len(outcomes)
    ):
        return Answer(
            "decline",
            None,
            "all outcomes must identify distinct recipients of the same opening stock",
        )
    key = lambda r: (r.provenance.sentence, r.position)
    if any(not (key(start) < key(r) < key(end)) for r in outcomes):
        return Answer(
            "decline", None, "the recipient transfers must precede the stated remainder"
        )
    if any(
        r.acquisition_ref not in {o.container_ref for o in outcomes}
        for r in outcomes
        if r.kind == "recipient-relation"
    ):
        return Answer(
            "decline",
            None,
            "every referenced recipient must belong to the complete transfer account",
        )
    anchors = []
    edges = []
    operands = [(start, []), (end, [end.value])]
    for r in outcomes:
        if r.kind == "recipient-amount":
            anchors.append((r.container_ref, r.value))
            operands.append((r, [r.value]))
        else:
            edges.append(
                (r.container_ref, r.acquisition_ref, r.fraction, r.value * r.sign)
            )
            operands.append((r, [r.fraction] + ([r.value] if r.sign else [])))
    try:
        graph = AffineGraph(anchors, edges, ctx.log)
        values = [graph.value(r.container_ref) for r in outcomes]
    except AffineError as e:
        return Answer("decline", None, str(e))
    if any(
        not isfinite(v) or v < 0 or not float(v).is_integer()
        for v in [end.value, *values]
    ) or not closed_evidence(ctx, facts, operands):
        return Answer(
            "decline",
            None,
            "all transfers must be read, connected and nonnegative whole counts",
        )
    total = resource_residual(
        [end.value, *values], [], ctx.log, source="reconstruct-opening-stock"
    )
    return finish_batch_answer(
        ctx,
        facts,
        total,
        "opening stock = all recipient transfers + the closing remainder",
    )
