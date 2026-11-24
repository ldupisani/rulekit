"""Uniform components, per-type requirements and nested allocations."""

from math import ceil
from .indexed_path import ordinal_index
from ..affine_graph import AffineError, AffineGraph
from ..dimensions import conversion_factor
from ..model import Quantity
from ..quantity_account import IncompleteAccount, quantity_account, require, whole_count
from ..rate_calculation import convert_exact_duration


@quantity_account("owned-area", "owned-area-comparison")
def owned_area(a, ctx):
    relations = a.select("owned-area-comparison", "value", "fraction")
    anchors = a.select("owned-area-anchor", "value")
    target = ctx.query_reference()
    unit = ctx.query["unit"]
    require(target and target.owner and anchors, "A measured owner and an area anchor are required.")

    def area(row):
        length = conversion_factor(ctx.reg, row.measure, unit, category="length_unit")
        require(length is not None, "The squared length units must be convertible.")
        return a.calculate("area * factor * factor", area=row.value, factor=length)

    related = {target}
    equations = []
    for r in relations:
        require(
            r.entity_ref
            and r.container_ref
            and r.entity_ref.owner
            and r.container_ref.owner
            and r.entity_ref != r.container_ref,
            "The two compared properties need distinct owners.",
        )
        equations.append((r.entity_ref, r.container_ref, r.fraction, area(r)))
    # Only measurements connected to this owner can qualify as operands.
    while True:
        reached = {
            node
            for left, right, _, _ in equations
            if left in related or right in related
            for node in (left, right)
        }
        if reached <= related:
            break
        related.update(reached)
    require(
        all(row.entity_ref in related for row in (*anchors, *relations)),
        "Every area statement must belong to the requested comparison.",
    )
    try:
        graph = AffineGraph([(r.entity_ref, area(r)) for r in anchors], equations, ctx.log)
        require(
            target in graph.forms and all(graph.value(node) >= 0 for node in graph.forms),
            "The area measurements must determine nonnegative areas.",
        )
        value = graph.value(target)
    except AffineError as exc:
        raise IncompleteAccount(str(exc)) from exc
    return a.finish(value, "Solve the stated scaled difference using the known area.")


@quantity_account("located-subgroup", "located-present-share")
def located_subgroup(a, ctx):
    absent = a.one("absent-share", "value")
    located = a.one("located-present-share", "value")
    rest = a.one("located-present-rest")
    populations = list(ctx.store.by_kind(Quantity))
    require(len(populations) == 1, "One complete population must be specified.")
    pool = populations[0]
    require(
        pool.is_state
        and not pool.measure_qualifier
        and not pool.time
        and pool.entity_ref.resolved
        and pool.measure == located.measure == ctx.query["measure"]
        and (not absent.measure or absent.measure == pool.measure)
        and pool.provenance.sentence < absent.provenance.sentence
        and absent.source_position < located.source_position < rest.source_position
        and located.container != rest.container
        and 0 <= absent.value <= 1
        and 0 <= located.value <= 1,
        "The shares must partition the same group between two distinct locations.",
    )
    a.include(pool, pool.value)
    present = a.calculate("population * (1 - absent)", population=pool.value, absent=absent.value)
    at_site = a.calculate("present * fraction", present=present, fraction=located.value)
    present = whole_count(present, "The number of participants present must be whole.")
    at_site = whole_count(at_site, "The number at the specified location must be whole.")
    target = ctx.query["place"]
    require(
        target in (located.container, rest.container),
        "The requested location must occur in the partition.",
    )
    value = (
        at_site
        if target == located.container
        else a.calculate("present - allocated", present=present, allocated=at_site)
    )
    return a.finish(
        value,
        "Allocate the stated share of those present and assign its remainder to the other location.",
    )


@quantity_account("graded-input-total", "graded-output-ratio")
def graded_input(a, ctx):
    context = a.one("modeled-production", optional=True)
    rates = a.select("graded-input", "value")
    ratio = a.one("graded-output-ratio", "value")
    used = a.one("graded-input-used", "value")
    materials = {r.marker for r in rates if r.marker}
    require(
        len(rates) == 2
        and {r.entity_ref for r in rates} == {ratio.container_ref, ratio.acquisition_ref}
        and ratio.container_ref != ratio.acquisition_ref
        and ratio.value > 0
        and used.container_ref in (ratio.container_ref, ratio.acquisition_ref)
        and ctx.query_reference() == used.entity_ref == ratio.entity_ref
        and used.entity_ref.resolved
        and all(r.value > 0 and r.measure == used.measure for r in rates)
        and used.measure == ctx.query["unit"]
        and materials == {used.marker} == {ctx.query["material"]}
        and (not ctx.query.get("product") or all(r.entity == ctx.query["product"] for r in rates))
        and (
            not context
            or context.entity_ref == used.entity_ref
            and context.measure == used.marker
            and all(r.entity == context.container for r in rates)
        ),
        "The material, product variants, maker and per-unit requirements must agree.",
    )
    per_unit = {r.entity_ref: r.value for r in rates}
    amount = a.calculate("used / rate", used=used.value, rate=per_unit[used.container_ref])
    graph = AffineGraph(
        [(used.container_ref, amount)],
        [(ratio.container_ref, ratio.acquisition_ref, ratio.value, 0)],
        ctx.log,
    )
    counts = [
        whole_count(graph.value(rate.entity_ref), "Material use must imply whole product counts.")
        for rate in rates
    ]
    total = sum(a.calculate("count * rate", count=v, rate=r.value) for v, r in zip(counts, rates))
    return a.finish(
        total,
        "Derive the product counts from the observed material use and apply each product’s input requirement.",
    )


@quantity_account("consumption-loads", "processing-capacity")
def consumption_loads(a, ctx):
    group = a.one("group-size", "value", "per_member", optional=True)
    if group:
        members, member_type = group.per_member, group.marker
    else:
        group = a.one("group-headcount", "value")
        per_group = a.one("members-per-user-group", "value")
        require(group.measure == per_group.measure, "The member count must name the group in the stay.")
        members, member_type = per_group.value, per_group.marker
    span = a.one("group-period", "value")
    use = a.one("per-person-consumption", "value")
    capacity = a.one("processing-capacity", "value")
    if use.attribute:
        require(use.subtotal == 1, "A replacement must be one new item.")
        a.extra_value(use, use.subtotal)
    require(
        group.measure == span.container
        and group.value.is_integer()
        and members.is_integer()
        and (not use.container or use.container == member_type)
        and capacity.acquisition_ref == use.acquisition_ref
        and capacity.marker == ctx.query["measure"]
        and capacity.value > 0
        and capacity.value.is_integer()
        and use.value.is_integer()
        and (not ctx.query.get("goods") or ctx.query_reference("goods") == use.acquisition_ref),
        "Group size, period, supply and batch capacity must refer to the same work.",
    )
    if ctx.query.get("activity"):
        frames = ctx.reg.selectional_frames(ctx.query["activity"], ("batch_processing_action",))
        require(
            any(
                ctx.reg.word_in_category(capacity.entity, roles["device"])
                and (
                    not ctx.query.get("collection")
                    or ctx.reg.word_in_category(ctx.query["collection"], roles["collection"])
                )
                for _, roles in frames
                if "device" in roles and "collection" in roles
            ),
            "The machine and work named in the question must be compatible.",
        )
    periods = convert_exact_duration(
        span.value, span.measure, use.marker, ctx.reg, ctx.log, source="supply-period"
    )
    require(
        periods is not None and periods.is_integer(), "The duration must cover whole supply periods."
    )
    loads = a.calculate(
        "groups * members * periods * supplies / capacity",
        groups=group.value,
        members=members,
        periods=periods,
        supplies=use.value,
        capacity=capacity.value,
    )
    return a.finish(ceil(loads), "Round the required batch count up so every used item fits.")


def section_extent_in(value, unit, target, ctx):
    if unit == target:
        return value
    require(
        all(ctx.reg.word_in_category(term, "playback_duration_unit") for term in (unit, target)),
        "The stated extent and requested unit must measure the same quantity.",
    )
    converted = convert_exact_duration(value, unit, target, ctx.reg, ctx.log, source="content-extent")
    require(converted is not None, "The section duration must convert to the requested unit.")
    return converted


@quantity_account("completed-section-extent", "completed-sections")
def completed_section_extent(a, ctx):
    full = a.one("completed-sections", "value")
    partial = a.one("partial-section", "value", optional=True)
    skip = a.one("skipped-section-remainder", "value", optional=True)
    further = a.one("additional-sections", "value", optional=True)
    size = a.one("uniform-section-size", "value")
    steps = [row for row in (full, partial, skip, further) if row is not None]
    require(
        steps == sorted(steps, key=lambda r: r.source_position)
        and all(s.entity_ref == ctx.query_reference() and s.entity_ref.resolved for s in steps)
        and (not ctx.query.get("work") or ctx.query["work"] == full.container)
        and full.measure == size.container
        and (not size.acquisition or size.acquisition_ref == full.container_ref)
        and (
            not further
            or further.container_ref == full.container_ref
            and further.measure == full.measure
            and ctx.reg.word_in_category(further.marker, "higher")
        ),
        "Each step must refer to the same participant, work and type of section.",
    )
    # One complete vocabulary frame must license the work, section, extent and
    # requested activity together. Sharing a unit alone does not link activities.
    target = ctx.query["measure"]
    roles = {"work": full.container, "section": full.measure, "extent": target}
    common_frames = None
    for verb in {ctx.query["activity"], *(s.verb for s in steps)}:
        frames = {
            category
            for category, frame in ctx.reg.selectional_frames(verb, ("content_consumption_action",))
            if all(
                role in frame and ctx.reg.word_in_category(term, frame[role])
                for role, term in roles.items()
            )
        }
        common_frames = frames if common_frames is None else common_frames & frames
    require(common_frames, "The stated and requested activities must share a compatible content frame.")
    whole_count(full.value, "The number of complete sections must be whole.")
    if further:
        whole_count(further.value, "The number of additional sections must be whole.")
    timed = ctx.reg.word_in_category(target, "playback_duration_unit")
    if not timed:
        whole_count(size.value, "A section size in countable units must be whole.")
    amount = section_extent_in(size.value, size.measure, target, ctx)
    require(amount > 0, "Each section must have a positive extent.")
    progress = 0
    if partial:
        index = ordinal_index(partial.marker, ctx.reg)
        progress = section_extent_in(partial.value, partial.measure, target, ctx)
        if not timed:
            whole_count(progress, "A partial extent in countable units must be whole.")
        require(
            full.container_ref == partial.container_ref
            and full.measure == partial.acquisition
            and index == full.value + 1
            and 0 < progress < amount,
            "Partial progress must be within the next section of the same work.",
        )
    if skip:
        require(
            partial
            and skip.value == index
            and skip.container == full.measure
            and skip.measure == partial.measure,
            "The skipped remainder must identify that partial section.",
        )
    times = set()
    for r, values in a.operands:
        if r in (full, partial, skip) and r.attribute:
            values.append(r.subtotal)
            times.add(r.subtotal)
    require(len(times) <= 1, "The clock references must identify the same boundary.")
    value = a.calculate(
        "(full + further) * size + partial",
        full=full.value,
        further=further.value if further else 0,
        size=amount,
        partial=progress,
    )
    return a.finish(
        value, "Add the extent of all completed sections and the measured portion of any unfinished section."
    )
