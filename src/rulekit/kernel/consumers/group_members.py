"""Reconcile stated subgroup sizes and member measurements within one roster."""

from dataclasses import replace
from math import isclose

from .indexed_path import ordinal_index
from ..dimensions import conversion_factor
from ..rate_calculation import convert_exact_duration
from ..quantity_account import quantity_account, require, whole_count


def measurement_key(reg, descriptor, unit):
    """Keep the property axis distinct from the unit family used to convert it."""
    families = {
        family
        for category, family in reg.attribute_compatibility_pairs(descriptor, unit)
        if "measured_property_descriptor" in reg.cat_ancestors(category)
    }
    axis = reg.attribute_value(descriptor, "projection_axis")
    require(axis is not None and len(families) == 1, "The measured property needs a compatible unit.")
    return axis, families.pop()


def read_group_members(account):
    groups = account.select("group-members")
    require(
        groups and len({g.provenance.sentence for g in groups}) == 1,
        "The members must belong to one identified group.",
    )
    sizes = {}
    for group in groups:
        require(
            group.entity_ref and group.entity_ref.resolved and group.entity_ref not in sizes,
            "Each subgroup needs a distinct identity.",
        )
        sizes[group.entity_ref] = whole_count(group.value, "Each subgroup needs a whole headcount.")
        if group.marker == "explicit":
            account.extra_value(group, group.value)

    members = {}
    for row in account.select("group-member-measurement", "value"):
        owner = row.entity_ref
        if row.marker and owner and owner.qualifiers == (row.marker,):
            owner = replace(owner, qualifiers=())
        require(owner in sizes, "The measurements must belong to a stated subgroup.")
        axis, family = measurement_key(account.ctx.reg, row.attribute, row.measure)
        if row.acquisition:
            require(
                account.ctx.reg.attribute_value(row.acquisition, "projection_axis") == axis,
                "The named property and the measured property must agree.",
            )
        members.setdefault((owner, axis, family), []).append(row)
    for (owner, _, _), rows in members.items():
        require(
            len(rows) == sizes[owner],
            "Each listed subgroup must have one measurement of this property per member.",
        )
        if any(row.marker for row in rows):
            indices = {ordinal_index(row.marker, account.ctx.reg) for row in rows}
            require(
                indices == set(range(1, len(rows) + 1)),
                "The indexed measurements must identify distinct members.",
            )
        else:
            require(
                len({row.provenance.sentence for row in rows}) == 1,
                "Separate unindexed measurement lists cannot identify distinct members.",
            )
    return groups, sizes, members


def eligible_member_count(account, discount, sizes, observations):
    group = discount.container_ref
    require(group in sizes, "The offer must identify a subgroup in the purchase.")
    if discount.boundary_value is None:
        return sizes[group]

    ctx = account.ctx
    axis, family = measurement_key(ctx.reg, discount.attribute, discount.boundary_unit)
    rows = observations.get((group, axis, family))
    require(rows, "Eligibility needs this property for each member of the named subgroup.")
    direction = ctx.reg.attribute_value(discount.operator, "threshold_direction")
    require(direction in (-1, 1), "The policy needs a stated comparison direction.")
    count = 0
    for row in rows:
        if ctx.reg.word_in_category(row.measure, "duration_measure"):
            boundary = convert_exact_duration(
                discount.boundary_value,
                discount.boundary_unit,
                row.measure,
                ctx.reg,
                ctx.log,
                source="eligibility-boundary",
            )
        else:
            factor = conversion_factor(ctx.reg, discount.boundary_unit, row.measure, category=family)
            boundary = (
                None
                if factor is None
                else account.calculate(
                    "boundary * factor", boundary=discount.boundary_value, factor=factor
                )
            )
        require(boundary is not None, "Member measurements must convert exactly to the policy unit.")
        # Treat only floating point conversion noise as equality.
        at_boundary = isclose(row.value, boundary, rel_tol=1e-14, abs_tol=0)
        count += (
            bool(discount.inclusive_marker) if at_boundary else direction * (row.value - boundary) > 0
        )
    return count


@quantity_account("group-headcount", "group-members")
def group_headcount(account, ctx):
    _, sizes, _ = read_group_members(account)
    return account.finish(sum(sizes.values()), "Add the stated sizes of the participating groups.")
