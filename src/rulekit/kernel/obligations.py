"""Obligation attachment, sense disambiguation by coverage, and binding.

THE CORE PRINCIPLE: every word's role places a demand on the rest of the
sentence; parsing is the discharge of those demands. An obligation binds iff
exactly one candidate satisfies it (definitive-or-decline); what stays unmet
is the deficiency report. Sense ambiguity is resolved by trying each
assignment on a throwaway copy and keeping the unique best-covering one.
"""

from __future__ import annotations

import copy
import itertools

from ..data.registry import Registry
from . import deixis
from .model import Obligation, Reading, Unit

# Which sense classes can satisfy each need. Structural knowledge (what KIND
# of word fills a slot), deliberately small and fixed — the per-word facts
# live in the packs.
NEED_CANDIDATES: dict[str, frozenset[str]] = {
    "collection": frozenset({"noun", "pronoun"}),
    "subject": frozenset({"noun", "name", "pronoun"}),
    "dobj": frozenset({"noun", "name", "pronoun", "value"}),
    "object": frozenset({"noun", "name", "pronoun", "value"}),
    "anchor": frozenset({"noun", "name", "value", "verb"}),
    "quantifies": frozenset({"noun"}),
    "negates": frozenset({"verb"}),
    "standard": frozenset({"noun", "name", "value"}),
    "modifies": frozenset({"noun"}),
    "scales": frozenset({"noun", "value"}),
    # "refers" is deliberately ABSENT: a pronoun's antecedent is bound by the
    # DOCUMENT loop against prior sentences, never within its own sentence
    # (a same-sentence noun is an object, not an antecedent)
    "left": frozenset({"value"}),
    "right": frozenset({"value"}),
}

MAX_AMBIGUOUS_UNITS = 4  # cartesian-trial cap; beyond this, decline as ambiguous


def _unit_sense_class(unit: Unit) -> str | None:
    """The sense class a unit presents as a binding candidate."""
    sense = unit.sense()
    if sense in ("value", "multiplier", "fraction"):
        return "value"
    return sense


_SUBJECT_GAP_SKIP = frozenset({"adverb", "auxiliary", "modal", "punct"})


def _gapped_subject_antecedent(reading: Reading, verb: Unit) -> Unit | None:
    """Subject gapping / conjunction reduction: 'Tom gave 3 apples TO SAM and
    [] BOUGHT 5 apples' — the second coordinated verb has an ELIDED subject, a
    zero anaphor whose antecedent is the subject of the FIRST coordinated verb
    ('gave' -> Tom), never the nearest noun (the recipient 'Sam', which the
    SYNTAX adjacency metric would otherwise pick). This is an anaphoric
    resolution — the same kind the document loop runs for pronouns, scoped here
    to the intra-clausal gap — not a distance arbitration.

    Fires ONLY when `verb` is a BARE conjoined verb: the first non-function token
    to its left is a coordinator ('and' / comma), with NO subject noun of its
    own between them. An explicit second subject ('...and SAM ate') or any other
    shape returns None, so ordinary subject resolution is completely untouched.
    Returns the first verb's already-bound subject (the fixpoint discharges the
    earlier clause's subject first), or None."""
    units = reading.units
    try:
        i = units.index(verb)
    except ValueError:
        return None
    j = i - 1
    while j >= 0 and units[j].sense() in _SUBJECT_GAP_SKIP:
        j -= 1
    if j < 0 or not (units[j].sense() == "conjunction" or units[j].surface == ","):
        return None  # not a bare-conjoined verb — an explicit subject or no coordinator
    k = j - 1
    while k >= 0 and units[k].sense() != "verb":
        k -= 1
    if k < 0:
        return None
    for ob in units[k].obligations():
        if ob.need == "subject" and ob.met and isinstance(ob.target, Unit):
            return ob.target
    return None


def _conjoined_sibling(reading: Reading, unit: Unit) -> Unit | None:
    """Another name conjoined to `unit`: '<name> and <name>' or a comma
    list '<name>, <name>, and <name>' — a comma between names IS the list
    marker. Returns any one sibling (non-uniqueness is all the caller needs)."""
    units = reading.units
    try:
        i = units.index(unit)
    except ValueError:
        return None

    def _linked(j: int, step: int) -> Unit | None:
        k = j + step
        # one linker: a conjunction, or a comma directly between names
        if not (0 <= k < len(units)):
            return None
        linker = units[k]
        if linker.sense() == "conjunction" or linker.surface == ",":
            k += step
            if 0 <= k < len(units):
                nxt = units[k]
                # ", and Donna" — comma followed by conjunction
                if linker.surface == "," and nxt.sense() == "conjunction":
                    k += step
                    nxt = units[k] if 0 <= k < len(units) else None
                if nxt is not None and nxt.sense() == "name":
                    return nxt
        return None

    return _linked(i, +1) or _linked(i, -1)


def _crosses_clause_boundary(reading: Reading, a: Unit, b: Unit) -> bool:
    lo, hi = sorted((a.span[0], b.span[0]))
    return any(
        u.sense() == "complementizer" and lo < u.span[0] < hi
        for u in reading.units
    )


def _relative_clause_subject_antecedent(
    reading: Reading, candidate: Unit, holder: Unit, reg: Registry | None = None
) -> bool:
    """Bind a restrictive relative to its adjacent nominal antecedent.

    Counted, article-anchored, possessed and licensed bare mass phrases can
    supply the subject. The marker must immediately follow the antecedent;
    an intervening complementizer blocks access to a nested clause. Ordinary
    subordinate clauses never gain a nominal subject across that boundary.
    Count evidence may be condensed or still carried by a bound numeral.
    """
    if candidate.sense() != "noun":
        return False
    counted = candidate.features.get("value_kind") == "count" or any(
        ob.need == "quantifies" and ob.met and ob.target is candidate
        for unit in reading.units
        for ob in unit.obligations()
    )
    from .patterns import is_referential_entity
    if not counted and not (reg is not None and is_referential_entity(
            reading, candidate, reg, bare_reference_category="mass_quantity_noun")):
        return False
    units = reading.units
    try:
        idx = units.index(candidate)
    except ValueError:
        return False
    if idx + 1 >= len(units):
        return False
    marker = units[idx + 1]
    if marker.sense() != "complementizer":
        return False
    if holder.span[0] <= marker.span[0]:
        return False
    for u in units:
        if u.uid == marker.uid:
            continue
        if u.sense() == "complementizer" and marker.span[0] < u.span[0] < holder.span[0]:
            return False
    return True


def attach_obligations(reading: Reading, reg: Registry) -> Reading:
    for unit in reading.units:
        sense = unit.sense()
        if sense is None:
            continue
        role = reg.role_obligations.get(sense)
        if role is None:
            continue
        obligations = [
            Obligation(role=sense, need=need, optional=need in role.optional)
            for need in role.needs
        ]
        reading.record(
            "attach-obligations", unit,
            {"obligations": obligations},
            f"role {sense!r} demands {role.needs}",
        )
    return reading


def _candidates(reading: Reading, holder: Unit, ob: Obligation, reg: Registry) -> list[Unit]:
    wanted = NEED_CANDIDATES.get(ob.need, frozenset())
    role = reg.role_obligations.get(ob.role)
    direction = role.direction.get(ob.need, "either") if role else "either"

    # `quantifies` is strictly LOCAL: a count quantifies the noun it can
    # reach crossing only nominal material (articles, adjectives, punct-free
    # nouns). Any other sense in between ("5 LESS THAN half as many coconut
    # trees") means the value does NOT count that noun — leave it unmet and
    # let the deficiency/guard machinery decline, never mis-bind.
    if ob.need == "quantifies":
        idx = reading.units.index(holder)
        for unit in reading.units[idx + 1 :]:
            sense = unit.sense()
            if sense in ("article", "adjective"):
                continue
            if sense == "noun":
                return [unit]
            return []
        return []
    out = []
    for unit in reading.units:
        if unit.uid == holder.uid:
            continue
        if _unit_sense_class(unit) not in wanted:
            continue
        if direction == "left" and unit.span[0] > holder.span[0]:
            continue
        if direction == "right" and unit.span[0] < holder.span[0]:
            continue
        # arguments are CLAUSE-LOCAL: a complementizer ("found out THAT
        # 7 caps weigh…") is a boundary no subject/dobj binding may cross
        # — EXCEPT a restrictive 'that'-relative clause's verb may still
        # reach its own antecedent for its subject (see
        # _relative_clause_subject_antecedent; mining candidate
        # that-relative-clause-binding).
        if ob.need in ("subject", "dobj", "object") and _crosses_clause_boundary(
            reading, holder, unit
        ):
            if not (
                ob.need == "subject"
                and _relative_clause_subject_antecedent(reading, unit, holder, reg)
            ):
                continue
        out.append(unit)
    # A bare value competes for an argument slot only when nothing nominal
    # does ("Tom ate 3" is elliptical; "Tom ate 3 apples" condensed anyway).
    if ob.need in ("dobj", "object", "standard"):
        nominal = [u for u in out if _unit_sense_class(u) != "value"]
        if nominal:
            out = nominal
    # A counted noun is rarely an AGENT: "he made $100,000 and got a bonus"
    # must not give 'got' the subject '$100,000'. Prefer uncounted nominals.
    # This must run BEFORE the conjoined-sibling check below: a counted
    # noun sitting immediately before "and <Name>" ("...scored 4 goals AND
    # Michael scored...") is itself a (wrong) subject candidate for the
    # SECOND clause's verb, and if left in `out` its adjacency to the
    # coordinator makes the sibling check below misread the new clause's
    # subject as a conjunct of the counted noun — silently dropping the
    # second clause's subject entirely (mining candidate
    # coordinated-clause-conjuncts). Filtering counted nouns out of `out`
    # first ensures the sibling check only ever considers genuine nominal
    # subject candidates.
    if ob.need == "subject":
        uncounted = [u for u in out if u.features.get("value_kind") != "count"]
        if uncounted:
            out = uncounted
    # Subject gapping: a bare conjoined verb inherits the FIRST clause's subject
    # anaphorically, overriding the nearest-noun adjustment below (which would
    # mis-attribute it to the first clause's object). Tightly scoped — see
    # `_gapped_subject_antecedent` — so no ordinary subject is affected.
    if ob.need == "subject":
        antecedent = _gapped_subject_antecedent(reading, holder)
        if antecedent is not None:
            # Authoritative: the anaphoric antecedent OVERRIDES the distance
            # window that otherwise scoped `out` to the nearest clause (which is
            # exactly why the first clause's subject was out of reach). The
            # fixpoint in bind() discharges the earlier clause's subject before
            # this one, so the antecedent is already resolved when this fires.
            return [antecedent]
    # A conjoined name ("Frankie AND Carla played…") is not a lone subject —
    # the subject is the GROUP. Keep both conjuncts in play and FORBID
    # adjacency from arbitrating between them: the binding stays non-unique
    # (unmet) rather than attributing the fact to the nearer name.
    if ob.need == "subject":
        for candidate in list(out):
            sibling = _conjoined_sibling(reading, candidate)
            if sibling is not None:
                if sibling not in out:
                    out.append(sibling)
                return out
    if len(out) > 1:
        # Adjacency arbitration: the nearest candidate wins ONLY if strictly nearer than
        # all others; equal distance stays ambiguous.
        #
        # THE ONE SITE IN THE TREE THAT ALREADY RANKED. deixis.resolve was generalised
        # FROM this code, so migrating it uses the REAL metric (token_distance from the
        # holder's span) rather than `constant` — and is still 0-diff, because the
        # hand-written sort-then-strictly-dominate below is byte-for-byte what resolve
        # does. This is the only migration in phase 6 where the origo is a genuine
        # POSITION rather than an empty placeholder.
        #
        # journal is deliberately NOT threaded here. `_candidates` runs inside
        # `disambiguate`'s deepcopied TRIAL readings (up to |senses|^4 of them), and a
        # trial's candidate set reflects a sense assignment that was REJECTED —
        # recording it would render a discarded hypothesis as a real resolution. No log
        # reaches this far anyway, so `journal=None` falls out for free; journaling it
        # would need an explicit trial guard first.
        winner = deixis.resolve(
            [
                deixis.Referent(
                    dimension=deixis.SYNTAX,
                    key=unit.uid,
                    payload=unit,
                    sentence=reading.sentence_index,
                    span=unit.span,
                )
                for unit in out
            ],
            deixis.Origo(sentence=reading.sentence_index, span=holder.span),
            deixis.token_distance,
            dimension=deixis.SYNTAX,
        )
        if winner is not None:
            return [winner.payload]
    return out


def bind(reading: Reading, reg: Registry) -> Reading:
    """Discharge obligations where exactly one candidate fits. Iterates to a
    fixpoint: a binding can disambiguate a later one."""
    changed = True
    while changed:
        changed = False
        for unit in reading.units:
            obligations = unit.obligations()
            for i, ob in enumerate(obligations):
                if ob.met:
                    continue
                found = _candidates(reading, unit, ob, reg)
                if len(found) == 1:
                    new = list(obligations)
                    new[i] = Obligation(ob.role, ob.need, target=found[0], optional=ob.optional)
                    reading.record(
                        "bind", unit,
                        {"obligations": new},
                        f"{unit.surface!r}.{ob.need} -> {found[0].surface!r} (unique candidate)",
                    )
                    changed = True
    return reading


def _coverage_score(reading: Reading, reg: Registry) -> tuple[int, int]:
    """(unmet non-optional obligations, disconnected units) — lower is better.

    A unit is DISCONNECTED when it neither serves as any binding's target nor
    discharges an obligation of its own: it contributes nothing to the parse.
    Auxiliaries and modals are exempt — they are function words licensed by
    the verb complex / ask cues ('does Tom read', 'he CAN read'), not content
    words competing for argument slots; penalizing them made arbitration
    prefer a content sense ('can' the noun) that steals a verb's subject from
    the pronoun the sentence actually integrates."""
    trial = copy.deepcopy(reading)
    attach_obligations(trial, reg)
    bind(trial, reg)
    unmet = sum(len(u.unmet()) for u in trial.units)
    bound_targets = {
        ob.target.uid
        for u in trial.units
        for ob in u.obligations()
        if ob.met and isinstance(ob.target, Unit)
    }
    disconnected = sum(
        1
        for u in trial.units
        if u.sense() not in (None, "punct", "auxiliary", "modal")
        and u.uid not in bound_targets
        and not any(ob.met for ob in u.obligations())
    )
    return (unmet, disconnected)


def _relative_marker_licenses_finite_verb(reading: Reading, unit: Unit) -> bool:
    """An adjacent nominal relative antecedent supplies the finite subject.

    Do not prefer an inflected noun homograph in ``a coat that costs ...``.
    A subordinate clause with its own subject does not have this adjacency.
    """
    from .patterns import is_finite_verb_form

    index = reading.units.index(unit)
    if index < 2:
        return False
    marker, antecedent = reading.units[index - 1], reading.units[index - 2]
    return (marker.sense() == "complementizer" and antecedent.sense() == "noun"
            and is_finite_verb_form(unit.features.get("fold", ""),
                                    unit.features.get("lemma", "")))


def _article_licenses_noun(reading: Reading, unit: Unit, reg: Registry | None = None) -> bool:
    """An article to the left, across licensed modifiers, DETERMINES
    this unit: 'A can…'/'the can…' is a nominal, never an auxiliary or modal.
    Pure grammatical skeleton — articles introduce noun phrases; no auxiliary
    or modal can head one."""
    idx = reading.units.index(unit)
    crossed_modifier = False
    for prev in reversed(reading.units[:idx]):
        sense = prev.sense()
        nominal_modifier = (
            reg is not None and "noun" in prev.senses()
            and prev.features.get("number") != "plural"
            and reg.attribute_applies_to(
                reg.plural_to_singular.get(prev.features.get("fold", ""), prev.features.get("fold", "")),
                reg.plural_to_singular.get(unit.features.get("fold", ""), unit.features.get("fold", "")),
            )
        )
        if (reg is not None and prev.features.get("value_kind") == "count"
                and reg.word_in_category(prev.features.get("lemma", ""), "currency_measure")
                and reg.word_in_category(unit.features.get("lemma", ""), "monetary_amount_head")):
            # A declared monetary head can retain its amount modifier while
            # seeking the article/possessive that licenses this nominal use.
            crossed_modifier = True
            continue
        if sense in {"adjective", "ordinal"} or (
            reg is not None and "adjective" in prev.senses()
            and reg.attribute_applies_to(
                prev.features.get("lemma", prev.features.get("fold", "")),
                unit.features.get("lemma", unit.features.get("fold", "")),
            )
        ) or nominal_modifier:
            crossed_modifier = True
            continue
        # A bare quantifier can itself be a subject ("toys that each cost
        # ..."). Only its explicit adjective makes this a determined noun
        # phrase; do not turn the following finite predicate into a noun.
        # A possessive following an adposition heads its nominal object,
        # even when the head is also a verb ("from her budget"). This does
        # not force object-pronoun + verb complements such as "saw her dress".
        previous_index = reading.units.index(prev)
        if (reg is not None and previous_index > 0
                and reg.word_in_category(prev.features.get("fold", ""), "possessive_determiner")
                and reading.units[previous_index - 1].sense() == "preposition"):
            return True
        return sense == "article" or (
            reg is not None and sense == "quantifier" and crossed_modifier
        )
    return False


def _counted_compound_licenses_noun(reading: Reading, unit: Unit, reg: Registry) -> bool:
    """A counted nominal compound cannot use its modifier as a finite verb.

    Select only an existing noun sense, with an unambiguous following noun
    and an explicit count or comparison boundary on the left. This does not
    change ordinary subject/verb sequences or invent lexical senses.
    """
    index = reading.units.index(unit)
    if index == 0 or index + 1 >= len(reading.units):
        return False
    if reading.units[index + 1].senses() != ["noun"]:
        return False
    previous = reading.units[index - 1]
    if previous.sense() == "value":
        return True
    word = previous.features.get("fold", "")
    if reg.word_in_category(word, "relational_marker"):
        return True
    return (reg.word_in_category(word, "quantity_delta") and index >= 2
            and reading.units[index - 2].sense() == "value")


def _nominal_role_licenses_noun(reading: Reading, unit: Unit, reg: Registry) -> bool:
    """A nominal object frame or a motion endpoint selects an existing noun.

    Possessive-looking pronouns alone are not enough: they can also be the
    subject of a bare verbal complement. A declared nominal theme frame is
    required. Endpoint nouns likewise need a source preposition or an actual
    motion/vehicle predicate before the goal preposition.
    """
    i = reading.units.index(unit)
    word = unit.features.get("lemma", unit.features.get("fold", ""))
    previous = reading.units[:i]
    if not previous:
        return False
    prev = previous[-1]
    prev_word = prev.features.get("lemma", prev.features.get("fold", ""))
    if reg.word_in_category(word, "nominal_activity"):
        if (i + 1 < len(reading.units) and reg.word_in_category(
                reading.units[i + 1].features.get("lemma", ""), "settlement_event")):
            return True
        cursor = i - 1
        while cursor >= 0 and reg.word_in_category(
                reading.units[cursor].features.get("lemma", ""), "nominal_activity_modifier"):
            cursor -= 1
        if (cursor > 0 and reg.word_in_category(
                reading.units[cursor].features.get("fold", ""), "possessive_determiner")
                and reg.word_in_category(reading.units[cursor - 1].features.get("fold", ""),
                                         "nominal_activity_auxiliary")):
            return True
    if i >= 2 and reg.word_in_category(prev_word, "possessive_determiner"):
        verb = previous[-2]
        verb_word = verb.features.get("lemma", verb.features.get("fold", ""))
        if "verb" in verb.senses() and reg.word_in_category(verb_word, "nominal_object_verb"):
            return any("theme" in roles and reg.word_in_category(word, roles["theme"])
                       for _, roles in reg.selectional_frames(verb_word))
    if not reg.word_in_category(word, "nominal_location"):
        return False
    if (reg.word_in_category(prev_word, "possessive_determiner")
            and i + 1 < len(reading.units)
            and reg.word_in_category(reading.units[i + 1].features.get("fold", ""), "copula")):
        return True
    if reg.word_in_category(prev_word, "locative_source_preposition"):
        return True
    if not reg.word_in_category(prev_word, "locative_goal_preposition"):
        return False
    for candidate in reversed(previous[:-1]):
        lemma = candidate.features.get("lemma", candidate.features.get("fold", ""))
        if (reg.word_in_category(lemma, "journey_vehicle")
                or reg.word_in_category(lemma, "possessive_determiner")
                or reg.word_in_category(lemma, "return_direction_adverb")):
            continue
        return "verb" in candidate.senses() and (
            reg.word_in_category(lemma, "spatial_motion_verb")
            or reg.word_in_category(lemma, "journey_vehicle_verb"))
    return False


def _partitive_licenses_noun(reading: Reading, unit: Unit, reg: Registry) -> bool:
    """A noun governed by the pack's partitive preposition is nominal.

    In "joules of work", a noun/verb trial otherwise ties: the verb trial can
    spuriously borrow the measured quantity as its subject and a later duration
    as its object. The governing word is DATA (`partitive` currently contains
    English `of`), while this function states only the grammatical structure.
    Articles/adjectives and one possessive determiner may intervene inside
    the governed noun phrase; a finite predicate cannot follow that partitive.
    """
    idx = reading.units.index(unit)
    crossed_possessive = False
    for prev in reversed(reading.units[:idx]):
        sense = prev.sense()
        if sense in ("article", "adjective"):
            continue
        if (not crossed_possessive and reg.word_in_category(
                prev.features.get("fold", ""), "possessive_determiner")):
            crossed_possessive = True
            continue
        return sense == "preposition" and reg.word_in_category(
            prev.features.get("fold", ""), "partitive"
        )
    return False


def _finite_verb_licenses_nonbare_noun_object(
    reading: Reading, unit: Unit
) -> bool:
    """Select a noun reading after a complete finite predicate.

    English cannot place a second non-bare finite verb directly after a
    finite verb (``she planted plants``). When that second surface is a
    declared noun/verb homograph, its noun reading is therefore structural,
    not a lexical preference. Bare complements remain untouched because
    constructions such as ``help work`` can legitimately contain adjacent
    verbs.
    """

    from .patterns import is_bare_verb_form, is_finite_verb_form

    index = reading.units.index(unit)
    if index == 0:
        return False
    previous = reading.units[index - 1]
    if previous.senses() != ["verb"]:
        return False
    current_fold = unit.features.get("fold", "")
    current_lemma = unit.features.get("lemma", current_fold)
    if is_bare_verb_form(current_fold, current_lemma):
        return False
    previous_fold = previous.features.get("fold", "")
    previous_lemma = previous.features.get("lemma", previous_fold)
    return is_finite_verb_form(previous_fold, previous_lemma)


def _compatible_head_licenses_adjective(
    reading: Reading, unit: Unit, reg: Registry
) -> bool:
    """A declared compatible noun head selects an adjective reading.

    Some ordinary attributive words also have independent noun readings
    ("science courses", "business courses"). Obligation coverage alone
    cannot distinguish the two senses because neither carries an obligation.
    The project compatibility table is already the lexical authority for the
    modifier/head pair, so an immediately following noun head makes that
    declared adjective reading deterministic without a general part-of-speech
    preference.
    """

    index = reading.units.index(unit)
    if index + 1 >= len(reading.units):
        return False
    head = reading.units[index + 1]
    # The same nominal head may follow one explicit cardinal before count
    # condensation ("next 60 parcels"). Do not cross other modifiers,
    # punctuation or predicates to manufacture an adjective attachment.
    if head.features.get("value_kind") == "count" and head.sense() == "value":
        if index + 2 >= len(reading.units):
            return False
        head = reading.units[index + 2]
    if "noun" not in head.senses():
        return False
    modifier = unit.features.get("lemma", unit.features.get("fold", ""))
    head_word = head.features.get("lemma", head.features.get("fold", ""))
    return reg.attribute_applies_to(modifier, head_word)


def _compatible_predicate_licenses_adverb(reading: Reading, unit: Unit, reg: Registry) -> bool:
    """A declared adverb/verb relationship resolves a non-prenominal adjunct.

    This is the predicate-side counterpart of adjective/head compatibility.
    Multiple possible predicates or a following noun retain the ambiguity.
    """
    index = reading.units.index(unit)
    if index + 1 < len(reading.units) and "noun" in reading.units[index + 1].senses():
        return False
    predicates = [
        v for v in reading.units if v.sense() == "verb"
        and not _crosses_clause_boundary(reading, unit, v)
        and not any(u.sense() == "conjunction"
                    and min(unit.span[0], v.span[0]) < u.span[0] < max(unit.span[0], v.span[0])
                    # A coordinated object may elide the shared predicate.
                    # Only an explicit predicate opens a new verbal clause.
                    and any(p.sense() == "verb" and u.span[0] < p.span[0]
                            <= max(unit.span[0], v.span[0]) for p in reading.units)
                    for u in reading.units)
    ]
    return len(predicates) == 1 and reg.adverb_applies_to_verb(
        unit.features.get("lemma", unit.features.get("fold", "")),
        predicates[0].features.get("fold", ""),
    )


def _state_licenses_terminal_remnant_adjective(
    reading: Reading, unit: Unit, reg: Registry
) -> bool:
    """Preserve an explicitly declared terminal remnant adjective.

    Some past-tense verbs are adjective homographs. A pack member of
    ``remnant_adj`` following a declared state predicate, with no following
    nominal argument, retains the established adjective reading ("are left",
    "have money left"). Outside that frame ordinary obligation coverage may
    select the verb reading ("nobody left the garden").
    """

    fold = unit.features.get("fold", "")
    if not reg.word_in_category(fold, "remnant_adj"):
        return False
    index = reading.units.index(unit)
    if index == 0:
        return False
    if any(
        later.sense() in ("article", "noun", "name", "pronoun")
        for later in reading.units[index + 1 :]
        if later.sense() != "punct"
    ):
        return False
    return any(
        reg.word_in_category(
            previous.features.get("lemma", previous.features.get("fold", "")),
            "state",
        )
        or reg.word_in_category(previous.features.get("fold", ""), "state")
        for previous in reading.units[:index]
    )


def _nominal_subject_licenses_modal(reading: Reading, unit: Unit) -> bool:
    """Resolve a modal/noun homograph in ordinary subject-modal-verb order.

    The decision is purely grammatical: a nominal immediately to the left and
    a verb immediately to the right make this the modal position.  An article
    to the left ("the can fell") therefore retains the noun reading.
    """

    index = reading.units.index(unit)
    if index == 0 or index + 1 >= len(reading.units):
        return False
    left = reading.units[index - 1]
    right = reading.units[index + 1]
    return left.sense() in ("noun", "name", "pronoun") and "verb" in right.senses()


def _priced_subject_licenses_verb(reading: Reading, unit: Unit, reg: Registry) -> bool:
    """A nominal subject, price predicate, currency amount and infinitive.

    The adjective/article boundary still keeps nominal cost phrases nominal.
    This only selects an existing verb sense; vocabulary stays pack-owned.
    """
    index = reading.units.index(unit)
    if index == 0 or index + 3 >= len(reading.units):
        return False
    left, right = reading.units[index - 1], reading.units[index + 1]
    marker, activity = reading.units[index + 2:index + 4]
    from .patterns import is_bare_verb_form

    return (left.sense() in ("noun", "name", "pronoun")
            and reg.word_in_category(unit.features.get("lemma", ""), "price_verb")
            and reg.word_in_category(right.features.get("lemma", ""), "currency_measure")
            and "value" in right.features
            and reg.word_in_category(marker.features.get("lemma", ""), "infinitival_marker")
            and "verb" in activity.senses()
            and is_bare_verb_form(activity.features.get("fold", ""),
                                  activity.features.get("lemma", "")))


def _infinitive_licenses_count_homograph(reading: Reading, unit: Unit, reg: Registry) -> bool:
    """A bare infinitive is not an undetermined singular count-noun use."""
    from .patterns import is_bare_verb_form

    index = reading.units.index(unit)
    lemma = unit.features.get("lemma", "")
    licensed = reg.word_in_category(lemma, "determiner_required_noun") or (
        index > 1 and reg.word_in_category(
            reading.units[index - 2].features.get("lemma", ""), "infinitive_complement_predicate"))
    return (index > 0 and licensed
            and reg.word_in_category(reading.units[index - 1].features.get("lemma", ""),
                                     "infinitival_marker")
            and is_bare_verb_form(unit.features.get("fold", ""), lemma))


def _copular_progressive_licenses_verb(
    reading: Reading, unit: Unit, reg: Registry
) -> bool:
    """Resolve a noun/verb ``-ing`` homograph after a copular auxiliary."""

    fold = unit.features.get("fold", "")
    lemma = unit.features.get("lemma", fold)
    if not fold.endswith("ing") or fold == lemma:
        return False
    index = reading.units.index(unit)
    for previous in reversed(reading.units[:index]):
        if previous.sense() in ("adverb", "punct"):
            continue
        previous_fold = previous.features.get("fold", "")
        previous_lemma = previous.features.get("lemma", previous_fold)
        return reg.word_in_category(
            previous_fold, "copula"
        ) or reg.word_in_category(previous_lemma, "copula")
    return False


def _nominal_description_list(reading: Reading, reg: Registry) -> set[int]:
    """Declared noun modifiers coordinated before one shared attribute head.

    A finite possession predicate and two or more compatible, separated
    descriptors license noun senses throughout the list. Ordinary verbal
    uses of the same surfaces receive no new license.
    """
    licensed = set()
    units = reading.units
    for end, head in enumerate(units):
        noun = reg.plural_to_singular.get(head.features.get("fold", ""),
                                         head.features.get("fold", ""))
        if "noun" not in head.senses() or not reg.word_in_category(noun, "nominal_attribute_noun"):
            continue
        members = []
        need_member = True
        index = end - 1
        while index >= 0:
            unit = units[index]
            word = reg.plural_to_singular.get(unit.features.get("fold", ""),
                                             unit.features.get("fold", ""))
            if "noun" in unit.senses() and reg.attribute_applies_to(word, noun) and need_member:
                members.append(unit.uid)
                need_member = False
            elif ((unit.sense() == "punct" and unit.surface == ",")
                  or reg.word_in_category(word, "holder_list_conjunction")):
                need_member = True
            else:
                break
            index -= 1
        if (len(members) >= 2 and not need_member and index >= 0
                and reg.word_in_category(units[index].features.get("lemma", ""), "plain_have_state")):
            licensed.update(members)
            licensed.add(head.uid)
            by_uid = {u.uid: u for u in units}
            reading.record("nominal-description-list", head, {
                "nominal_description_qualifiers": tuple(
                    reg.plural_to_singular.get(by_uid[uid].features.get("fold", ""),
                                               by_uid[uid].features.get("fold", ""))
                    for uid in reversed(members)
                ),
            }, "coordinated descriptors retain every named attribute")
    return licensed


def _auxiliary_licenses_bare_verb(reading: Reading, unit: Unit, reg: Registry) -> bool:
    """An auxiliary selects a bare predicate, also across an inverted subject.

    Do not confuse a possessive determiner with that subject: this filter
    must not force its following noun into a verb. It chooses an existing sense,
    never guesses the predicate from its spelling or the question's topic.
    """
    fold = unit.features.get("fold", "")
    if fold != unit.features.get("lemma", fold):
        return False
    index = reading.units.index(unit) - 1
    while index >= 0 and reading.units[index].sense() in {"adverb", "negator"}:
        index -= 1
    if index < 0:
        return False
    previous = reading.units[index]
    if previous.sense() in {"auxiliary", "modal"}:
        # Direct adjacency is declarative only with an overt subject on the
        # left. In an inverted question the next noun may BE the subject.
        return index > 0 and reading.units[index - 1].sense() in {"name", "noun", "pronoun"}
    if (previous.sense() not in {"name", "noun", "pronoun"}
            or reg.word_in_category(previous.features.get("fold", ""), "possessive_determiner")):
        return False
    index -= 1
    while index >= 0 and reading.units[index].sense() in {"article", "adjective"}:
        index -= 1
    return index >= 0 and reading.units[index].sense() in {"auxiliary", "modal"}


def disambiguate(reading: Reading, reg: Registry) -> Reading:
    """Commit one sense per multi-sense unit: the assignment with the best
    obligation coverage wins, and only a unique winner commits."""
    nominal_list = _nominal_description_list(reading, reg)
    ambiguous = [u for u in reading.units if len(u.senses()) > 1]
    if not ambiguous:
        return reading
    options = []
    for u in ambiguous:
        senses = u.senses()
        index = reading.units.index(u)
        if ("adjective" in senses
                and reg.attrs.get(u.features.get("fold", ""), {}).get("ordinal_index") is not None
                and index + 1 < len(reading.units)
                and "noun" in reading.units[index + 1].senses()):
            # Ordinal position modifies the following noun, even when the
            # same spelling independently names a duration unit.
            options.append(["adjective"])
            continue
        if ("noun" in senses and index > 0
                and reading.units[index - 1].sense() == "rate"
                and reg.word_in_category(u.features.get("lemma", u.features.get("fold", "")), "duration_measure")
                and (index + 1 == len(reading.units)
                     or "noun" not in reading.units[index + 1].senses())):
            # A terminal denominator is a unit, whereas an ordinal before
            # another noun remains eligible to modify that noun.
            options.append(["noun"])
            continue
        if ("interrogative" in senses and "quantifier" in senses and index == 1
                and reading.units[0].sense() == "interrogative"
                and index + 1 < len(reading.units)
                and reading.units[index + 1].sense() in {"auxiliary", "modal"}):
            # An inverted quantity question has no nominal for the quantifier
            # here: the auxiliary introduces its subject and predicate.
            options.append(["interrogative"])
            continue
        if u.uid in nominal_list:
            options.append(["noun"])
            continue
        if "adverb" in senses and reg.word_in_category(
            u.features.get("lemma", u.features.get("fold", "")),
            "narration_sequence_adverb",
        ):
            index = reading.units.index(u)
            following = reading.units[index + 1:index + 2]
            preceding = reading.units[:index]
            if (
                "adjective" in senses and following
                and "noun" in following[0].senses()
            ):
                options.append(["adjective"])
                continue
            # An introductory sequencing adjunct, set off by punctuation,
            # is not a prenominal adjective. Leave nominal uses to the
            # ordinary adjective arbitration below.
            if (
                following and following[0].sense() == "punct"
                and all(p.sense() in ("conjunction", "adverb", "punct") for p in preceding)
            ):
                options.append(["adverb"])
                continue
            # A sequence marker between a subject and a verb is also an
            # adjunct. A leading marker can precede a pronominal/proper
            # subject, but never steals an adjective from a common noun.
            clause_leading = all(
                p.sense() in ("conjunction", "adverb", "punct") for p in preceding
            )
            if following and (
                (
                    following[0].sense() == "verb"
                    and preceding
                    and preceding[-1].sense() in ("name", "noun", "pronoun")
                )
                or (
                    clause_leading
                    and following[0].sense() in ("name", "pronoun")
                    and index + 2 < len(reading.units)
                    and reading.units[index + 2].sense() == "verb"
                )
            ):
                options.append(["adverb"])
                continue
        if "noun" in senses and "verb" in senses and _auxiliary_licenses_bare_verb(reading, u, reg):
            options.append(["verb"])
            continue
        if "noun" in senses and "verb" in senses and _relative_marker_licenses_finite_verb(reading, u):
            options.append(["verb"])
            continue
        if "noun" in senses and "verb" in senses and _priced_subject_licenses_verb(reading, u, reg):
            options.append(["verb"])
            continue
        if "noun" in senses and "verb" in senses and _infinitive_licenses_count_homograph(reading, u, reg):
            options.append(["verb"])
            continue
        if "verb" in senses and _copular_progressive_licenses_verb(
            reading, u, reg
        ):
            options.append(["verb"])
            continue
        if "noun" in senses and "verb" in senses and (
            _finite_verb_licenses_nonbare_noun_object(reading, u)
            or _article_licenses_noun(reading, u, reg)
            or _counted_compound_licenses_noun(reading, u, reg)
        ):
            options.append(["noun"])
            continue
        if "modal" in senses and _nominal_subject_licenses_modal(reading, u):
            options.append(["modal"])
            continue
        if "adjective" in senses and _compatible_head_licenses_adjective(
            reading, u, reg
        ):
            options.append(["adjective"])
            continue
        if "adverb" in senses and _compatible_predicate_licenses_adverb(reading, u, reg):
            options.append(["adverb"])
            continue
        if "adjective" in senses and _state_licenses_terminal_remnant_adjective(
            reading, u, reg
        ):
            options.append(["adjective"])
            continue
        if "noun" in senses and (_partitive_licenses_noun(reading, u, reg)
                                 or _nominal_role_licenses_noun(reading, u, reg)):
            # A partitive complement is a nominal position. Restrict an
            # EXISTING noun candidate; never invent one for a verb-only word.
            options.append(["noun"])
            continue
        options.append(
            [
                s
                for s in senses
                if not (
                    s in ("auxiliary", "modal")
                    and _article_licenses_noun(reading, u)
                )
            ]
            or senses
        )
    scored: list[tuple[tuple[int, int], tuple[str, ...]]] = []
    def selected_features(unit, sense):
        features = {"senses": [sense]}
        if sense == "noun" and "verb" in unit.senses():
            # A verbal inflection is not the noun's lexical identity.
            # Recover the declared noun head after choosing that sense.
            fold = unit.features.get("fold", "")
            features["lemma"] = reg.plural_to_singular.get(fold, fold)
            if fold in reg.plural_to_singular:
                features["number"] = "plural"
        elif sense == "verb" and "noun" in unit.senses():
            fold = unit.features.get("fold", "")
            features["lemma"] = reg.verb_lemmas.get(fold, fold)
            if fold in reg.plural_to_singular:
                entry = reg.lexicon.get(fold)
                features["number"] = entry.number if entry and entry.number else "singular"
        return features

    unresolved = sum(len(choices) > 1 for choices in options)
    if unresolved > MAX_AMBIGUOUS_UNITS:
        for u in ambiguous:
            reading.record(
                "ambiguity-overflow", u, {"ambiguous": True},
                f"{unresolved} unresolved ambiguous units exceeds trial cap",
            )
        return reading
    for assignment in itertools.product(*options):
        trial = copy.deepcopy(reading)
        for u, sense in zip(ambiguous, assignment):
            trial.unit(u.uid).features.update(selected_features(u, sense))
        scored.append((_coverage_score(trial, reg), assignment))
    scored.sort(key=lambda pair: (pair[0], pair[1]))

    best_score, best_assignment = scored[0]
    unique = len(scored) == 1 or scored[1][0] > best_score
    if unique:
        for u, sense in zip(ambiguous, best_assignment):
            reading.record(
                "assign-sense", u,
                selected_features(u, sense),
                f"coverage arbitration: {sense!r} leaves {best_score[0]} unmet",
            )
    else:
        for u in ambiguous:
            reading.record(
                "ambiguous", u, {"ambiguous": True},
                "no sense assignment covers strictly best — genuinely ambiguous",
            )
    return reading
