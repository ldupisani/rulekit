"""Opt-in, construction-local reference links with pack-owned form agreement.

Agreement does not discover an antecedent. A complete grammar declares that
link; this module validates it without guessing personal properties of names.
Candidate projections never mutate the reading while rules are being tried.
"""

from collections import defaultdict

from ..data.registry import Registry
from .model import Obligation, Unit
from .reference_identity import reference_from_unit


def anaphoric_forms_agree(surfaces: list[str], number: str | None, reg: Registry) -> bool:
    forms = [getattr(reg.lexicon.get(surface.casefold()), "anaphoric_form", None)
             for surface in surfaces]
    return bool(forms) and all(
        form is not None and number in form.referent_numbers for form in forms
    ) and len({form.paradigm for form in forms if form is not None}) == 1


def referenced_forms_agree(readings, identity, reg: Registry, number: str = 'singular') -> bool:
    """Check the explicit forms already linked to one identity, without guessing a name's gender."""
    forms = [unit.surface for reading in readings for unit in reading.units
             if unit.sense() == 'pronoun' and reference_from_unit(unit) == identity
             and getattr(reg.lexicon.get(unit.surface.casefold()), 'anaphoric_form', None)]
    return not forms or anaphoric_forms_agree(forms, number, reg)


def _referent_number(unit: Unit) -> str | None:
    seen = set()
    while unit.sense() == "pronoun":
        if id(unit) in seen:
            return None
        seen.add(id(unit))
        unit = next((ob.target for ob in unit.obligations()
                     if ob.need == "refers" and isinstance(ob.target, Unit)), None)
        if unit is None:
            return None
    return "singular" if unit.sense() == "name" else unit.features.get("number")


def project_references(bindings: dict[str, str], slots: dict, reg: Registry) -> dict | None:
    """Return validated copies, or None for absent, unknown or conflicting links."""
    if not bindings:
        return slots
    groups = defaultdict(list)
    for source, target in bindings.items():
        groups[target].append(source)
    projected = dict(slots)
    bound = {}
    for target_name, sources in groups.items():
        target = slots.get(target_name)
        if not isinstance(target, Unit):
            return None
        target_ref = reference_from_unit(target)
        if not target_ref.resolved:
            return None
        number = _referent_number(target)
        pronouns = [target.surface] if target.sense() == "pronoun" else []
        for source in sources:
            unit = slots.get(source)
            if not isinstance(unit, Unit):
                return None
            current_ref = reference_from_unit(unit)
            if current_ref.resolved and current_ref != target_ref:
                return None
            if unit.sense() != "pronoun":
                if not current_ref.resolved or current_ref != target_ref:
                    return None
                continue
            obligations = unit.obligations()
            if not any(ob.need == "refers" for ob in obligations):
                return None
            # Group bindings or unexplained structural satisfaction cannot be
            # silently overwritten by a singular construction-local identity.
            if any(ob.need == "refers" and ob.met and not isinstance(ob.target, Unit)
                   for ob in obligations):
                return None
            pronouns.append(unit.surface)
            updated = [Obligation(ob.role, ob.need, target=target, optional=ob.optional)
                       if ob.need == "refers" else ob for ob in obligations]
            projected[source] = Unit(unit.uid, unit.words, {**unit.features, "obligations": updated})
            bound[unit.uid] = target_ref
        if pronouns and not anaphoric_forms_agree(pronouns, number, reg):
            return None
    # Project the same identity onto nouns governed by a bound possessive.
    for name, unit in slots.items():
        if not isinstance(unit, Unit):
            continue
        owner = bound.get(unit.features.get("owner_ref_uid"))
        if owner is None:
            continue
        old = reference_from_unit(unit).owner
        if unit.features.get("owner_resolved") and old != owner:
            return None
        projected[name] = Unit(unit.uid, unit.words, {
            **unit.features, "owner": owner.head, "owner_resolved": True,
            "owner_reference": owner.to_dict(),
        })
    return projected
