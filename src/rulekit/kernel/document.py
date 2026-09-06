"""The document blackboard: multi-sentence texts, gap-driven re-parse rounds.

Round 0 parses every premise independently. Each later round supplies new
cross-sentence information (discourse referents now; providers and pack
activation later), re-derives facts for exactly the sentences whose gaps
that information can fill, rebuilds the store, and re-saturates. The loop
ends when a round changes nothing; a hard cap errors loudly.

Correctness choices: fact derivation per round is a pure recompute (the
store is rebuilt from scratch each round — no incremental patching to get
subtly wrong), and discourse binding is definitive-or-decline: ordinary
multi-name discourse remains ambiguous, while a question-local assumption
may establish one strictly nearer compatible antecedent; ties stay unmet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.registry import Registry
from .evaluate import ArithmeticLog
from .facts import FactStore
from .learn import learn
from . import deixis
from .model import (
    Before,
    EventTime,
    Fact,
    LocationConstraint,
    LocationConstraintViolation,
    LocationEvent,
    Obligation,
    PATTERN,
    Provenance,
    Reading,
    Unit,
)
from .patterns import RuleMatchResult, is_referential_entity, run_rules
from .saturate import saturate

MAX_ROUNDS = 6


@dataclass(frozen=True)
class Gap:
    sentence: int
    kind: str  # unknown-word | ambiguous-sense | unmet-obligation
    key: tuple

    def describe(self) -> str:
        if self.kind == "unknown-word":
            return f"sentence {self.sentence}: unknown word {self.key[0]!r}"
        if self.kind == "ambiguous-sense":
            return f"sentence {self.sentence}: {self.key[0]!r} is ambiguous"
        return f"sentence {self.sentence}: {self.key[0]!r} needs a {self.key[1]}"


@dataclass
class Document:
    readings: list[Reading]
    store: FactStore
    log: ArithmeticLog
    consumed_uids: dict[int, set[int]] = field(default_factory=dict)
    rounds: int = 0
    gaps: list[Gap] = field(default_factory=list)
    rule_results: dict[int, list[RuleMatchResult]] = field(default_factory=dict)


def _satisfy_pattern_obligations(
    reading: Reading, result: RuleMatchResult
) -> None:
    """Apply only the slot/need pairs explicitly owned by a matched rule."""

    for slot_name, needs in result.match.rule.satisfies.items():
        unit = result.match.slots.get(slot_name)
        if not isinstance(unit, Unit):
            continue  # compile validation rejects spans; fail closed at runtime
        obligations = unit.obligations()
        updated = list(obligations)
        changed = False
        for index, obligation in enumerate(obligations):
            if obligation.need not in needs or obligation.met:
                continue
            updated[index] = Obligation(
                obligation.role,
                obligation.need,
                target=PATTERN,
                optional=obligation.optional,
            )
            changed = True
        if changed:
            reading.record(
                "pattern-satisfy",
                unit,
                {"obligations": updated},
                f"{unit.surface!r} obligations satisfied structurally by "
                f"rule {result.match.rule.id}",
                rule_id=result.match.rule.id,
            )


def collect_gaps(readings: list[Reading]) -> list[Gap]:
    gaps: list[Gap] = []
    for reading in readings:
        for unit in reading.units:
            if unit.features.get("unknown"):
                gaps.append(Gap(reading.sentence_index, "unknown-word", (unit.surface,)))
            if unit.features.get("ambiguous"):
                gaps.append(Gap(reading.sentence_index, "ambiguous-sense", (unit.surface,)))
            for ob in unit.unmet():
                gaps.append(
                    Gap(reading.sentence_index, "unmet-obligation", (unit.surface, ob.need))
                )
    return gaps


def _discourse_candidates(
    readings: list[Reading], upto: int
) -> dict[str, tuple[int, Unit]]:
    """Name units introduced in sentences before `upto`, keyed by lemma.

    Carries each candidate's sentence index alongside the unit: a Unit knows its span
    but not which sentence it is in, and the PERSON axis needs both to be locatable.
    """
    out: dict[str, tuple[int, Unit]] = {}
    for reading in readings:
        if reading.sentence_index >= upto:
            continue
        for unit in reading.units:
            if unit.sense() == "name":
                lemma = unit.features.get("lemma", unit.features["fold"])
                out[lemma] = (reading.sentence_index, unit)
    return out


def _animate_candidates(
    readings: list[Reading], upto: int, reg: Registry
) -> dict[str, tuple[int, Unit]]:
    """`animate`-category common nouns before `upto` — the FALLBACK
    candidate set, consulted only when there is no name at all.

    "Baker made 157 cakes. He sold 158 cakes." has NO name unit: 'baker' is
    lexically a common noun, so the pronoun found no antecedent and the item
    declined — while the same story with 'Ana' reads, because an unknown
    word defaults to NAME. That asymmetry is an artifact of the lexicon, not
    of the English. Category membership is the ONLY admission test."""
    out: dict[str, tuple[int, Unit]] = {}
    for reading in readings:
        if reading.sentence_index >= upto:
            continue
        for unit in reading.units:
            if unit.sense() != "noun":
                continue
            lemma = unit.features.get("lemma", unit.features["fold"])
            if reg.word_in_category(lemma, "animate"):
                out[lemma] = (reading.sentence_index, unit)
    return out


def _prior_location_anaphor_candidates(
    readings: list[Reading], reading: Reading, unit: Unit, reg: Registry
) -> dict[tuple[int, int], tuple[int, Unit]] | None:
    """Prior locations for a pronoun governed by a location preposition.

    ``None`` means the pronoun is not in this grammatical position; an empty
    dictionary means that it is, but no compatible antecedent exists. Keeping
    those cases distinct prevents a location ``it`` from falling through to
    the ordinary proper-name candidate pool.
    """

    lemma = unit.features.get("lemma", unit.features.get("fold", ""))
    if not reg.word_in_category(lemma, "singular_location_anaphor"):
        return None
    governed = any(
        predicate.sense() == "preposition"
        and reg.word_in_category(
            predicate.features.get(
                "lemma", predicate.features.get("fold", "")
            ),
            "quantity_location_preposition",
        )
        and any(
            obligation.need == "object"
            and obligation.met
            and obligation.target is unit
            for obligation in predicate.obligations()
        )
        for predicate in reading.units
    )
    if not governed:
        return None
    return {
        (candidate_reading.sentence_index, candidate.uid): (
            candidate_reading.sentence_index,
            candidate,
        )
        for candidate_reading in readings
        if candidate_reading.sentence_index < reading.sentence_index
        for candidate in candidate_reading.units
        if candidate.sense() == "noun"
        and reg.word_in_category(
            candidate.features.get(
                "lemma", candidate.features.get("fold", "")
            ),
            "quantity_location",
        )
    }


def _local_possessive_subject_candidates(
    reading: Reading, determiner: Unit, reg: Registry
) -> dict[str, tuple[int, Unit]]:
    """The unique preceding subject available to a possessive determiner.

    A governed determiner has a strong clause-local reading in forms such as
    ``Maya has ... her sister`` and ``the teacher is ... her child``.  This
    path is deliberately narrower than general pronoun binding: the unit must
    actually govern an owned noun, the subject must already be obligation-
    bound, and exactly one distinct subject may precede the determiner.
    Objects and unrelated nearby animate nouns never enter the candidate set.
    """

    determiner_lemma = determiner.features.get(
        "lemma", determiner.features.get("fold", "")
    )
    if not reg.word_in_category(
        determiner_lemma, "clause_subject_possessive_determiner"
    ) or not any(
        unit.features.get("owner_ref_uid") == determiner.uid
        for unit in reading.units
    ):
        return {}
    candidates: dict[str, tuple[int, Unit]] = {}
    for predicate in reading.units:
        if predicate.sense() != "verb":
            continue
        for obligation in predicate.obligations():
            subject = obligation.target
            if (
                obligation.need != "subject"
                or not obligation.met
                or not isinstance(subject, Unit)
                or subject.span[0] >= determiner.span[0]
            ):
                continue
            target = subject
            seen: set[int] = set()
            while target.sense() == "pronoun" and id(target) not in seen:
                seen.add(id(target))
                referent = next(
                    (
                        item.target
                        for item in target.obligations()
                        if item.need == "refers"
                        and item.met
                        and isinstance(item.target, Unit)
                    ),
                    None,
                )
                if referent is None:
                    break
                target = referent
            lemma = target.features.get(
                "lemma", target.features.get("fold", "")
            )
            candidates[lemma] = (reading.sentence_index, target)
    return candidates if len(candidates) == 1 else {}


def _prior_possessive_owner_candidates(
    readings: list[Reading], reading: Reading, determiner: Unit
) -> dict[str, tuple[int, Unit]]:
    """Continue the nearest already-resolved owner of the same noun head."""

    owned_heads = {
        unit.features.get("lemma", unit.features.get("fold", ""))
        for unit in reading.units
        if unit.features.get("owner_ref_uid") == determiner.uid
    }
    if len(owned_heads) != 1:
        return {}
    head = next(iter(owned_heads))
    prior_owned: Unit | None = None
    prior_reading: Reading | None = None
    for candidate_reading in reversed(readings):
        if candidate_reading.sentence_index >= reading.sentence_index:
            continue
        for candidate in candidate_reading.units:
            if (
                candidate.sense() == "noun"
                and candidate.features.get(
                    "lemma", candidate.features.get("fold", "")
                )
                == head
            ):
                prior_owned = candidate
                prior_reading = candidate_reading
                break
        if prior_owned is not None:
            break
    if (
        prior_owned is None
        or prior_reading is None
        or not prior_owned.features.get("owner_resolved")
    ):
        return {}
    owner = prior_owned.features.get("owner")
    if not owner:
        return {}
    targets = [
        (candidate_reading.sentence_index, unit)
        for candidate_reading in readings
        if candidate_reading.sentence_index < reading.sentence_index
        for unit in candidate_reading.units
        if unit.features.get("lemma", unit.features.get("fold", ""))
        == owner
    ]
    if not targets:
        return {}
    target_sentence, target = max(
        targets, key=lambda item: (item[0], item[1].span)
    )
    return {owner: (target_sentence, target)}


def _subject_group(
    readings: list[Reading],
    upto: int,
    reg: Registry,
    group_entities: frozenset[str] = frozenset(),
    relation_sentences: frozenset[int] = frozenset(),
) -> tuple[tuple[str, ...], tuple[Unit, ...]] | None:
    """One conservative plural referent made from prior entity subjects.

    A member needs semantic participation in a committed entity-bearing fact.
    Thus ``Mary has twice as many as Tom ... they`` includes Tom, while the
    incidental object in ``Mary sees Zoe`` does not. A name left outside the
    fact set makes the group ambiguous, except inside a sentence whose
    committed quantitative Relation may itself have collapsed a coordinated
    standard (``Dilan and Ashley combined``) to one semantic group endpoint.
    Repeated appearances of one identity are deduplicated in first-mention order.
    A single declared person-group noun (``the crew ... they``) is also one
    valid collective referent even though its member list has one group entity.
    """

    prior = [
        reading
        for reading in readings
        if reading.sentence_index < upto and not reading.assumption
    ]
    def is_subject(reading: Reading, candidate: Unit) -> bool:
        return any(
            obligation.need == "subject"
            and obligation.met
            and obligation.target is candidate
            for verb in reading.units
            if verb.sense() == "verb"
            for obligation in verb.obligations()
        )

    members: list[str] = []
    targets: dict[str, Unit] = {}
    for reading in prior:
        for candidate in reading.units:
            lemma = candidate.features.get(
                "lemma", candidate.features.get("fold", "")
            )
            eligible = False
            if candidate.sense() == "name":
                eligible = lemma in group_entities
            elif candidate.sense() == "noun" and is_subject(reading, candidate):
                eligible = (
                    lemma in group_entities
                    and is_referential_entity(
                        reading,
                        candidate,
                        reg,
                        bare_reference_category="bare_entity_reference",
                    )
                )
            if not eligible:
                continue
            if lemma not in targets:
                members.append(lemma)
                targets[lemma] = candidate

    # Any named mention which is neither a subject nor a quantitative relation
    # participant is an unresolved rival discourse entity. Do not silently
    # omit it from "they".
    unresolved_names = {
        candidate.features.get(
            "lemma", candidate.features.get("fold", "")
        )
        for reading in prior
        for candidate in reading.units
        if candidate.sense() == "name"
        and candidate.features.get(
            "lemma", candidate.features.get("fold", "")
        ) not in targets
        and reading.sentence_index not in relation_sentences
    }
    if unresolved_names:
        return None
    if len(members) >= 2:
        return tuple(members), tuple(targets[name] for name in members)
    if len(members) == 1 and reg.word_in_category(members[0], "persongroup"):
        return tuple(members), (targets[members[0]],)
    return None


def _bind_discourse(
    readings: list[Reading],
    journal: deixis.Journal | None = None,
    reg: Registry | None = None,
    plural_group_sentence: int | None = None,
    group_entities: frozenset[str] = frozenset(),
    relation_sentences: frozenset[int] = frozenset(),
) -> set[int]:
    """Bind unmet pronoun `refers` obligations to a unique prior name, or —
    inside a question-local assumption context — to one strictly nearest name.
    When the text contains no name, singular reference applies the established
    `animate` fallback; question-local plural reference may instead construct
    one exact group from prior entity-bearing facts and their referential
    mentions. Returns the sentence indexes that gained a binding.

    `reg` is optional so the name-only path stays callable without a
    registry; the zero-name fallback simply does not run without one."""
    changed: set[int] = set()
    for reading in readings:
        for unit in reading.units:
            if unit.sense() != "pronoun":
                continue
            # Group reference is opt-in for the current question only. Subject
            # and object pronouns expose plural agreement directly; a plural
            # possessive determiner such as ``their`` agrees with its governed
            # noun instead, so its pack category carries the group signal.
            # Premise pronouns retain the established definitive-or-decline
            # behavior.
            lemma = unit.features.get("lemma", unit.features["fold"])
            # First-/second-person possessive determiners are anchored by the
            # speech situation, not by an earlier noun phrase.  Their governed
            # noun deliberately retains the surface owner (``my task``), while
            # the pronoun's ordinary ``refers`` obligation becomes optional so
            # a valid deictic phrase is not reported as a discourse defect.
            # It deliberately remains UNBOUND: ``my`` must not thereby become
            # a resolved entity slot and let a prefix rule ignore its noun.
            if (
                reg is not None
                and reg.word_in_category(
                    lemma, "externally_deictic_possessive_determiner"
                )
            ):
                obligations = unit.obligations()
                updated = list(obligations)
                deictic_changed = False
                for index, obligation in enumerate(obligations):
                    if (
                        obligation.need != "refers"
                        or obligation.met
                        or obligation.optional
                    ):
                        continue
                    updated[index] = Obligation(
                        obligation.role,
                        obligation.need,
                        target=None,
                        optional=True,
                    )
                    deictic_changed = True
                if deictic_changed:
                    reading.record(
                        "bind-deictic-possessive",
                        unit,
                        {"obligations": updated},
                        f"{unit.surface!r} is anchored by the speech situation",
                    )
                    changed.add(reading.sentence_index)
                continue
            group_reference = reg is not None and (
                (
                    unit.features.get("number") == "plural"
                    and reg.word_in_category(
                        lemma,
                        "discourse_referential_group_pronoun",
                    )
                )
                or reg.word_in_category(lemma, "plural_possessive_determiner")
            )
            if (
                group_reference
                and plural_group_sentence == reading.sentence_index
                and reg is not None
            ):
                group = _subject_group(
                    readings,
                    reading.sentence_index,
                    reg,
                    group_entities,
                    relation_sentences,
                )
                if group is not None:
                    members, targets = group
                    obligations = unit.obligations()
                    updated = list(obligations)
                    group_changed = False
                    for index, obligation in enumerate(obligations):
                        if obligation.need != "refers" or obligation.met:
                            continue
                        updated[index] = Obligation(
                            obligation.role,
                            obligation.need,
                            target=targets,
                            optional=obligation.optional,
                        )
                        group_changed = True
                    if group_changed:
                        reading.record(
                            "bind-discourse-group",
                            unit,
                            {
                                "obligations": updated,
                                "referent_group": members,
                            },
                            f"{unit.surface!r} -> {list(members)!r} "
                            "(unique prior fact-backed discourse group)",
                        )
                        changed.add(reading.sentence_index)
                    continue
            # A direct plural pronoun cannot fall back to one singular
            # antecedent. A possessive `their` has singular agreement on its
            # governed noun in the current representation, so when no group is
            # available it retains the established ordinary-owner path below.
            if unit.features.get("number") == "plural":
                continue
            obligations = unit.obligations()
            for i, ob in enumerate(obligations):
                if ob.need != "refers" or ob.met:
                    continue
                # Ordinary person discourse has no gender/person compatibility
                # model, so recency alone would make unsafe guesses ("Tom ... Mary
                # ... He ..."). Its field therefore stays flat. A candidate
                # re-mentioned by the current question's LOCAL ASSUMPTION supplies
                # the missing scope boundary: only then does sentence recency become
                # meaningful, and the shared strict-dominance rule still declines a
                # same-sentence tie.
                location_candidates = _prior_location_anaphor_candidates(
                    readings, reading, unit, reg
                )
                dimension = deixis.PERSON
                if location_candidates is not None:
                    candidates = location_candidates
                    dimension = deixis.PLACE
                else:
                    local_subjects = _local_possessive_subject_candidates(
                        reading, unit, reg
                    )
                    prior_owner = _prior_possessive_owner_candidates(
                        readings, reading, unit
                    )
                    candidates = (
                        local_subjects
                        or prior_owner
                        or _discourse_candidates(
                            readings, reading.sentence_index
                        )
                    )
                # THE ZERO-NAME FALLBACK. Common nouns are considered ONLY
                # when no name candidate exists, which is provably
                # byte-identical wherever any name is in play. That ordering
                # IS the safety argument: `deixis.resolve` under the constant
                # metric needs a UNIQUE winner, so adding candidates to a
                # non-empty set could silently UNBIND a working binding —
                # this shape never runs against a non-empty set.
                if not candidates and reg is not None and reg.word_in_category(
                    unit.features.get("lemma", unit.features["fold"]),
                    "animate_pronoun",
                ):
                    candidates = _animate_candidates(
                        readings, reading.sentence_index, reg
                    )
                # A possessive determiner cannot resolve to the head it
                # governs: in "her child", choosing an earlier `child` as
                # the owner would assert self-ownership and, worse, change a
                # repeated explicit owner from `her` to `child`.  The noun
                # attachment recorded by condense gives us this structural
                # exclusion without naming any determiner or kinship word.
                owned_heads = {
                    owned.features.get(
                        "lemma", owned.features.get("fold", "")
                    )
                    for owned in reading.units
                    if owned.features.get("owner_ref_uid") == unit.uid
                }
                if owned_heads:
                    candidates = {
                        lemma: candidate
                        for lemma, candidate in candidates.items()
                        if lemma not in owned_heads
                    }
                referents = [
                    deixis.Referent(
                        dimension=dimension,
                        key=lemma,
                        payload=target,
                        sentence=sentence,
                        span=target.span,
                    )
                    for lemma, (sentence, target) in candidates.items()
                ]
                assumption_sentences = {
                    candidate.sentence_index
                    for candidate in readings
                    if candidate.assumption
                }
                metric = (
                    deixis.sentence_distance
                    if any(
                        referent.sentence in assumption_sentences
                        for referent in referents
                    )
                    else deixis.constant
                )
                winner = deixis.resolve(
                    referents,
                    deixis.Origo(sentence=reading.sentence_index, span=unit.span),
                    metric,
                    dimension=dimension,
                    journal=journal,
                    source="bind-discourse",
                )
                if winner is not None:
                    target = winner.payload
                    lemma = target.features.get(
                        "lemma", target.features.get("fold", "")
                    )
                    new = list(obligations)
                    new[i] = Obligation(ob.role, ob.need, target=target, optional=ob.optional)
                    reading.record(
                        "bind-discourse", unit,
                        {"obligations": new},
                        f"{unit.surface!r} -> {lemma!r} "
                        "(strictly resolved antecedent in document)",
                    )
                    for owned in reading.units:
                        if owned.features.get("owner_ref_uid") != unit.uid:
                            continue
                        if owned.features.get("owner") == lemma:
                            continue
                        reading.record(
                            "bind-possessive-owner",
                            owned,
                            {"owner": lemma, "owner_resolved": True},
                            f"owner of {owned.surface!r} resolves through "
                            f"{unit.surface!r} to {lemma!r}",
                        )
                    changed.add(reading.sentence_index)
    return changed


def _measure_anaphor_candidate_lemma(unit: Unit) -> str | None:
    if unit.sense() != "noun" or unit.features.get("measure_anaphor"):
        return None
    if unit.features.get("number") != "plural":
        return None
    lemma = unit.features.get("lemma") or unit.features.get("fold")
    return lemma or None


def _bind_measure_anaphor(
    readings: list[Reading], journal: deixis.Journal | None = None
) -> set[int]:
    """Bind unresolved measure-noun anaphors (mining candidate measure-
    noun-anaphor: 'ones'-headed counted NPs, condense.py's merge-measure-
    anaphor) to the UNIQUE prior counted-noun lemma in the document — the
    measure-noun sibling of `_bind_discourse` above, resolving WHAT is
    being counted rather than WHO holds it. Candidates are PLURAL noun-
    sensed units only, drawn from every sentence up to and including this
    one (same-sentence mentions BEFORE the anaphor's own position count
    too — "6 blue balls, ... blue ONES" resolves within one sentence, no
    document round needed for that shape). Zero or two-or-more distinct
    candidate lemmas leaves it unresolved this round (learn.py's `_lemma`
    then returns a reserved sentinel no ask can ever match); a later round
    can still resolve it once a sibling sentence's own anaphor binding
    (rerun_rules) or an unrelated fact narrows the candidate set — the
    same reason `_bind_discourse` re-tries every round instead of once.
    Returns the sentence indexes that gained a binding this round."""
    changed: set[int] = set()
    for reading in readings:
        for unit in reading.units:
            if not unit.features.get("measure_anaphor"):
                continue
            if unit.features.get("antecedent_lemma") is not None:
                continue
            candidates: set[str] = set()
            for other in readings:
                if other.sentence_index > reading.sentence_index:
                    continue
                for cand in other.units:
                    if cand.uid == unit.uid:
                        continue
                    if (
                        other.sentence_index == reading.sentence_index
                        and cand.span[0] >= unit.span[0]
                    ):
                        continue
                    lemma = _measure_anaphor_candidate_lemma(cand)
                    if lemma is not None:
                        candidates.add(lemma)
            # Same primitive, DISCOURSE dimension: this resolves WHAT is counted, not
            # WHO holds it. Typing the candidates is the point — a person antecedent
            # can never be mistaken for a measure-noun antecedent, and vice versa.
            # Constant metric => byte-identical to the `len(candidates) == 1` it
            # replaces. Sorted for a deterministic candidate order (the set's
            # iteration order must never be able to decide a binding).
            winner = deixis.resolve(
                [
                    deixis.Referent(dimension=deixis.DISCOURSE, key=lemma)
                    for lemma in sorted(candidates)
                ],
                deixis.Origo(sentence=reading.sentence_index, span=unit.span),
                deixis.constant,
                dimension=deixis.DISCOURSE,
                journal=journal,
                source="bind-measure-anaphor",
            )
            if winner is not None:
                lemma = winner.key
                reading.record(
                    "bind-measure-anaphor", unit,
                    {"antecedent_lemma": lemma},
                    f"{unit.surface!r} -> {lemma!r} (unique prior counted-noun lemma)",
                )
                changed.add(reading.sentence_index)
    return changed


def run_document(
    premises: list[Reading], reg: Registry, journal: deixis.Journal | None = None
) -> Document:
    log = ArithmeticLog()
    # The journal rides on the log because the log is already threaded everywhere the
    # remaining resolution sites live (every SynthPlugin takes it as its third
    # argument). None whenever tracing is off — bench never builds one.
    log.journal = journal
    doc = Document(readings=premises, store=FactStore(), log=log)

    # round 0: pattern rules per sentence (their matches never change across
    # rounds — rules see one sentence; discourse changes only the fold)
    for reading in premises:
        results = run_rules(reading, reg, phase="read", log=log)
        doc.rule_results[reading.sentence_index] = results
        consumed = doc.consumed_uids.setdefault(reading.sentence_index, set())
        for r in results:
            _satisfy_pattern_obligations(reading, r)
            consumed.update(r.match.consumed)
            for uid in r.match.consumed:
                reading.record(
                    "pattern-consume", reading.unit(uid),
                    {"pattern_consumed": True},
                    f"consumed by rule {r.match.rule.id}",
                    rule_id=r.match.rule.id,
                )

    def rebuild_store() -> FactStore:
        store = FactStore()
        for reading in premises:
            store.admit_rule_results(doc.rule_results.get(reading.sentence_index, []), reg)
            for fact in learn(reading, reg):
                store.admit(fact)
        from .resource_accounting import compose_resource_accounts

        compose_resource_accounts(store, premises, reg)
        event_times = sorted(
            store.by_kind(EventTime),
            key=lambda fact: (fact.offset, fact.event),
        )
        for index, earlier in enumerate(event_times):
            for later in event_times[index + 1 :]:
                if earlier.offset >= later.offset:
                    continue
                store.admit(
                    Before(
                        provenance=Provenance(
                            source="inference/temporal-order",
                            sentence=later.provenance.sentence,
                        ),
                        earlier=earlier.event,
                        later=later.event,
                    )
                )
        for constraint in store.by_kind(LocationConstraint):
            if (
                constraint.modality != "impossible"
                or constraint.transition != "terminates"
            ):
                continue
            for event in store.by_kind(LocationEvent):
                if event.effect != "terminates" or event.place != constraint.place:
                    continue
                store.admit(
                    LocationConstraintViolation(
                        provenance=Provenance(
                            source="inference/location-constraint-conflict",
                            sentence=event.provenance.sentence,
                            assumption=constraint.provenance.assumption,
                        ),
                        event=event.event,
                        entity=event.entity,
                        place=event.place,
                        transition=event.effect,
                    )
                )
        saturate(store, reg, log)
        return store

    def rerun_rules(sentence_indexes: set[int]) -> None:
        """Discourse binding changed these sentences — their pattern rules
        get a fresh look (a resolved pronoun now satisfies name slots)."""
        for reading in premises:
            if reading.sentence_index not in sentence_indexes:
                continue
            results = run_rules(reading, reg, phase="read", log=log)
            doc.rule_results[reading.sentence_index] = results
            consumed = doc.consumed_uids.setdefault(reading.sentence_index, set())
            for r in results:
                _satisfy_pattern_obligations(reading, r)
                for uid in r.match.consumed:
                    if uid in consumed:
                        continue
                    consumed.add(uid)
                    reading.record(
                        "pattern-consume", reading.unit(uid),
                        {"pattern_consumed": True},
                        f"consumed by rule {r.match.rule.id}",
                        rule_id=r.match.rule.id,
                    )

    doc.store = rebuild_store()
    for round_no in range(1, MAX_ROUNDS + 1):
        doc.rounds = round_no
        if journal is not None:
            journal.round = round_no
        changed = _bind_discourse(premises, journal=journal, reg=reg)
        changed |= _bind_measure_anaphor(premises, journal=journal)
        if not changed:
            break
        rerun_rules(changed)
        doc.store = rebuild_store()
    else:
        raise RuntimeError(
            f"document loop did not settle in {MAX_ROUNDS} rounds — "
            "a synthesizer or discourse pass is oscillating"
        )

    doc.gaps = collect_gaps(premises)
    return doc
