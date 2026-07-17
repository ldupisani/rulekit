"""Pattern-rule matching over the annotated unit sequence.

The successor to difg's 129 hand-ordered system solvers. Differences that
matter:
- Rules match UNITS, not raw text — "1,200" and "twelve hundred" present the
  same value feature, so the comma-regex bug class is gone.
- ALL triggered rules run; nothing short-circuits. Emitted facts go to the
  fact store, which adjudicates agreement/subsumption/collision (facts.py).
- Priority does not exist. Specificity is computed for subsumption only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..data.registry import Registry
from ..data.schemas import AskRule, MatchToken, PatternRule
from .evaluate import ArithmeticLog, EvaluationError, evaluate
from .model import (
    Before,
    Conditional,
    Discount,
    Fact,
    Atom,
    FractionQuantity,
    Goal,
    GroupTotal,
    Membership,
    PartitionQuantity,
    Quantified,
    PercentChange,
    Predication,
    Provenance,
    Quantity,
    Rate,
    Reading,
    Relation,
    RatioQuantity,
    RestQuantity,
    Subset,
    Unit,
)

SKIPPABLE_SENSES = {"article", "punct"}

_FACT_CLASSES = {
    "quantity": Quantity,
    "relation": Relation,
    "membership": Membership,
    "atom": Atom,
    "quantified": Quantified,
    "conditional": Conditional,
    "subset": Subset,
    "predication": Predication,
    "before": Before,
    "fraction_quantity": FractionQuantity,
    "rest_quantity": RestQuantity,
    "partition_quantity": PartitionQuantity,
    "ratio_quantity": RatioQuantity,
    "goal": Goal,
    "group_total": GroupTotal,
    "rate": Rate,
    "discount": Discount,
    "percent_change": PercentChange,
}


@dataclass
class Match:
    rule: PatternRule
    slots: dict[str, Unit]
    consumed: tuple[int, ...]  # uids of consumed units (the match span)
    specificity: tuple[int, int, int] = (0, 0, 0)


@dataclass
class RuleMatchResult:
    match: Match
    facts: list[Fact] = field(default_factory=list)


def _slot_ok(unit: Unit, token: MatchToken, reg: Registry) -> bool:
    if token.bare and (
        unit.features.get("qualifier") is not None or unit.features.get("owner") is not None
    ):
        # OPT-IN (schemas.MatchToken.bare, default False — every pre-existing
        # slot is byte-identical): a compound noun keeps its HEAD's lemma, so a
        # category gate cannot tell "the dot product" from "the product". An
        # operation-naming slot sets `bare: true` to demand the head itself.
        return False
    if token.type is not None:
        t = token.type
        sense = unit.sense()
        kind = unit.features.get("value_kind")
        if t == "number":
            return kind == "count"
        if t == "fraction":
            return kind == "fraction"
        if t == "percent":
            # mining candidate discounted-purchase-totals: the PERCENT
            # subset of fraction tokens only — numbers.py sets the
            # `percent` feature exclusively for "%"/"percent" surface
            # forms, never for word fractions ("half", "one third"), so
            # "half off" structurally cannot satisfy this slot the way
            # "50% off" does. Keeps the discount rules structurally
            # disjoint from every existing fraction-consuming rule (the
            # relation rules read plain `type: fraction` under a
            # completely different trailing literal — "more"/"fewer"/"as
            # many as", never "off"/"discount" — so there is no overlap
            # even before this narrower gate).
            return kind == "fraction" and bool(unit.features.get("percent"))
        if t == "multiplier":
            return kind == "multiplier"
        if t == "point":
            # a COORDINATE TUPLE ("(3,4)") — numbers.py's _TUPLE. Disjoint from
            # every scalar slot type by construction: a tuple unit carries no
            # `value`, and a valued unit is never value_kind "tuple".
            return kind == "tuple"
        if t == "name":
            # a RESOLVED pronoun satisfies a name slot (it denotes its
            # antecedent); an unresolved one never does (definitive-or-decline)
            if sense == "pronoun":
                return any(
                    ob.need == "refers" and ob.met for ob in unit.obligations()
                )
            return sense == "name"
        if t == "noun":
            return sense == "noun"
        if t == "entity":
            # anything that can HOLD a quantity: a name, a common noun
            # ("the factory"), or a resolved pronoun
            if sense == "pronoun":
                return any(ob.need == "refers" and ob.met for ob in unit.obligations())
            return sense in ("name", "noun")
        if t == "possessed":
            # a noun merged from "OWNER 's NOUN" (condense.py merge-
            # possessive tags it with an `owner` feature) — structural
            # possessive 's, never a bare common noun or a plain name
            return sense == "noun" and unit.features.get("owner") is not None
        if t == "qualified":
            # a noun merged from ADJECTIVE+NOUN or NOUN+NOUN (condense.py
            # merge-attribute / merge-compound tags it with a `qualifier`
            # feature) — "coconut trees", "red apples"; a bare noun with no
            # attributive modifier never matches (increment 34 mirror of
            # `possessed`)
            return sense == "noun" and unit.features.get("qualifier") is not None
        if t == "plural":
            return sense == "noun" and unit.features.get("number") == "plural"
        if t == "common_noun":
            # mining candidate conjunct-comparative-quantities: a BARE
            # common-noun holder — sense noun, no `owner` (never a
            # possessive-merged noun, `possessed`'s own tag), no
            # `qualifier` (never an attribute-merged noun, `qualified`'s
            # own tag), not plural (the plural-combined ask family's own
            # territory). Structurally disjoint from `possessed`/
            # `qualified`/`name` by construction — see SLOT_TYPES' comment.
            return (
                sense == "noun"
                and unit.features.get("owner") is None
                and unit.features.get("qualifier") is None
                and unit.features.get("number") != "plural"
            )
        if t == "counted":
            return sense == "noun" and kind == "count"
        if t == "verb":
            return sense == "verb"
        if t == "auxiliary":
            return sense == "auxiliary"
        if t == "modal":
            # increment 14 split 'modal' (can/could/will/would/should/may/
            # might/must) from 'auxiliary' precisely so factual asks
            # (auxiliary-gated) exclude it and a capacity ask (budget ÷
            # unit price) can claim the modal token structurally.
            return sense == "modal"
        if t == "future_modal":
            # mining candidate will-tense-asks: an ordinary factual ask's
            # aux slot ALSO accepts the future/conditional modal pair
            # (will/would, the `future_modal` category — packs/core-
            # english/categories/core.yaml) alongside the plain auxiliary
            # (do/does/did) it already matched. The other 6 modal-sense
            # words (can/could/should/may/might/must — capacity/
            # hypothetical modals) are NOT in `future_modal`, so they stay
            # excluded here exactly as before: the increment-14 kirsty
            # lesson (a wanted/hypothetical purchase is not a purchase)
            # cannot recur through this slot.
            if sense == "auxiliary":
                return True
            if sense == "modal":
                word = unit.features.get("lemma", unit.features.get("fold", ""))
                return reg.word_in_category(word, "future_modal")
            return False
        if t == "pronoun":
            return sense == "pronoun"
        if t == "word":
            return sense not in (None, "punct")
        if t == "adjective":
            return sense == "adjective"
        return False
    assert token.cat is not None
    word = unit.features.get("lemma", unit.features.get("fold", ""))
    return reg.word_in_category(word, token.cat) or reg.word_in_category(
        unit.features.get("fold", ""), token.cat
    )


_MEASURE_ANAPHOR_UNRESOLVED = "$anaphor:measure-unresolved$"


def _lemma_of(unit: Unit) -> str:
    # an elided measure-noun anaphor ("12 yellow ONES" — mining candidate
    # measure-noun-anaphor, condense.py's merge-measure-anaphor) speaks AS
    # the antecedent document.py's `_bind_measure_anaphor` resolved it to;
    # unresolved leaves the SAME reserved sentinel learn.py's own `_lemma`
    # falls back to — this compound's own fold ("yellow ones") is never a
    # real measure name, and its stale `lemma` feature (senses.py's
    # fallback assignment for every lexicon word, pronouns included) is
    # the anaphor's OWN word, not the antecedent — using either would be a
    # silent wrong, not a decline.
    if unit.features.get("measure_anaphor"):
        antecedent_lemma = unit.features.get("antecedent_lemma")
        return antecedent_lemma if antecedent_lemma is not None else _MEASURE_ANAPHOR_UNRESOLVED
    # a pronoun whose `refers` bound cross-sentence speaks AS its antecedent
    if unit.sense() == "pronoun":
        for ob in unit.obligations():
            if ob.need == "refers" and ob.met and isinstance(ob.target, Unit):
                return ob.target.features.get(
                    "lemma", ob.target.features.get("fold", "")
                )
    return unit.features.get("lemma", unit.features.get("fold", unit.surface.lower()))


def _try_match_at(
    units: list[Unit],
    start: int,
    tokens: list[MatchToken],
    reg: Registry,
    slots: dict[str, Unit],
    consumed: list[int],
) -> int | None:
    """Match tokens against units from `start`; returns the next unit index
    after the match, or None. Skippable units may sit between tokens."""
    i = start
    for k, token in enumerate(tokens):
        if token.opt is not None:
            sub_slots = dict(slots)
            sub_consumed = list(consumed)
            end = _try_match_at(units, i, token.opt, reg, sub_slots, sub_consumed)
            if end is not None:
                slots.update(sub_slots)
                consumed[:] = sub_consumed
                i = end
            continue
        while i < len(units) and units[i].sense() in SKIPPABLE_SENSES:
            i += 1
        if i >= len(units):
            return None
        if token.span:
            # OPT-IN phrase capture (schemas.MatchToken.span): bind a RUN of
            # units, GREEDY-LONGEST with backtracking — the longest capture
            # whose remainder still matches wins, so an inner copula stays
            # inside the phrase ("buildings that are tall" under a
            # `... {lit: are} ...` rule) unless the trailing tokens need it.
            # A FINAL span (nothing after it) must therefore run to the
            # sentence end: shorter captures only survive when the rest of
            # the sequence consumes what they leave, and an empty rest
            # consumes nothing — silently dropping a phrase TAIL would turn
            # exact-phrase matching into prefix matching, which is the
            # overclaim this flag exists to prevent.
            rest = tokens[k + 1:]
            for end in range(len(units), i, -1):
                captured = tuple(units[i:end])
                if not any(u.sense() not in SKIPPABLE_SENSES for u in captured):
                    continue  # a span must capture something meaningful
                if not rest and any(
                    u.sense() not in SKIPPABLE_SENSES for u in units[end:]
                ):
                    continue  # final span: nothing meaningful may trail it
                if token.span_blocks and any(
                    reg.word_in_category(_lemma_of(u), token.span_blocks)
                    for u in captured
                ):
                    # a blocked word (e.g. a negation) may NEVER be swallowed
                    # into a phrase — negation is read structurally by an
                    # explicit token or not at all. No shorter fallback that
                    # silently drops the tail: the guard above already keeps
                    # final spans full-length, and a non-final shorter capture
                    # still re-checks this condition on ITS OWN contents.
                    continue
                sub_slots = dict(slots)
                sub_consumed = list(consumed) + [u.uid for u in captured]
                tail = _try_match_at(units, end, rest, reg, sub_slots, sub_consumed)
                if tail is None:
                    continue
                sub_slots[token.slot] = captured  # type: ignore[assignment]
                slots.update(sub_slots)
                consumed[:] = sub_consumed
                return tail
            return None
        if token.at_start and any(
            u.sense() not in SKIPPABLE_SENSES for u in units[:i]
        ):
            # OPT-IN anchor (schemas.MatchToken.at_start): nothing MEANINGFUL may
            # precede. Skippables stay invisible here exactly as they are to the
            # loop above — an anchor that tripped on a leading article would be a
            # different rule than the one the author wrote.
            return None
        unit = units[i]
        if token.lit is not None:
            if unit.features.get("fold") != token.lit:
                return None
        else:
            if not _slot_ok(unit, token, reg):
                return None
            name = token.slot
            if name in slots and (
                isinstance(slots[name], tuple)  # a span slot never re-binds
                or _lemma_of(slots[name]) != _lemma_of(unit)
            ):
                return None  # repeated slot must bind the same lemma
            slots[name] = unit
        consumed.append(unit.uid)
        i += 1
    return i


def match_sequence(
    reading: Reading, tokens: list[MatchToken], reg: Registry
) -> Match | None:
    """First (leftmost) match of a token sequence anywhere in the sentence."""
    matches = match_all(reading, tokens, reg, limit=1)
    return matches[0] if matches else None


def match_all(
    reading: Reading, tokens: list[MatchToken], reg: Registry, limit: int = 8
) -> list[Match]:
    """ALL non-overlapping leftmost matches — a compound sentence ("X picked
    12 more than Y, and Y picked 5 less than Z") yields one match per
    clause; taking only the first would leave the rest to the naive fold."""
    units = reading.units
    out: list[Match] = []
    start = 0
    while start < len(units) and len(out) < limit:
        matched_here = None
        for begin in range(start, len(units)):
            slots: dict[str, Unit] = {}
            consumed: list[int] = []
            end = _try_match_at(units, begin, tokens, reg, slots, consumed)
            if end is not None:
                matched_here = (Match(rule=None, slots=slots, consumed=tuple(consumed)), end)  # type: ignore[arg-type]
                break
        if matched_here is None:
            break
        out.append(matched_here[0])
        start = matched_here[1]
    return out


def _check_where(
    rule: PatternRule, slots: dict[str, Unit], reading: Reading, reg: Registry
) -> bool:
    for pred in rule.where:
        if pred.same_lemma is not None:
            # span slots (tuple-valued) have no single lemma; they cannot
            # participate in where-predicates and are simply skipped
            lemmas = {
                _lemma_of(slots[s])
                for s in pred.same_lemma
                if s in slots and not isinstance(slots[s], tuple)
            }
            if len(lemmas) > 1:
                return False
        if pred.distinct is not None:
            # (lemma, label) pairs, not bare lemma alone — mining candidate
            # labeled-entity-relations: "Jar B has 12 more marbles than jar
            # A" bare-folds who/std to the SAME lemma 'jar' (the label
            # lives in a separate feature, condense.py merge-label), so a
            # bare-lemma-only distinct check wrongly read this as the
            # self-referential "X compares to itself" case every `distinct:
            # [who, std]` guard exists to block, and silently declined
            # every labeled relation. Two unlabeled units (label=None on
            # both sides, the overwhelming common case) compare exactly as
            # before — (lemma, None) == (lemma, None) still collides, so
            # every existing distinct check's behavior is unchanged; this
            # only additionally distinguishes a pair that share a lemma AND
            # carry two DIFFERENT non-null labels.
            values = [
                (_lemma_of(slots[s]), slots[s].features.get("label"))
                for s in pred.distinct if s in slots
            ]
            if len(values) != len(set(values)):
                return False
        if pred.distinct_measure is not None:
            # mining candidate qualified-measure-keys: the (lemma, label)
            # pair from `distinct` above, PLUS each slot's own `qualifier`
            # feature — "12 more green apples than red apples" shares
            # lemma 'apple' and label None on both sides but carries two
            # DIFFERENT non-null qualifiers ('green' vs 'red'), so this is
            # NOT the self-referential "compares a measure to itself" shape
            # (lemma, label, qualifier) all matching still blocks (a bare,
            # unqualified repeat, or two qualifiers that happen to agree,
            # is genuinely self-referential); only rules that opt into this
            # predicate (instead of plain `distinct`) get the widened
            # comparison — `distinct: [who, std]` elsewhere is untouched.
            values = [
                (
                    _lemma_of(slots[s]),
                    slots[s].features.get("label"),
                    slots[s].features.get("qualifier"),
                )
                for s in pred.distinct_measure if s in slots
            ]
            if len(values) != len(set(values)):
                return False
        if pred.absent is not None:
            cat = pred.absent["cat"]
            for u in reading.units:
                word = u.features.get("lemma", u.features.get("fold", ""))
                if reg.word_in_category(word, cat):
                    return False
        if pred.name_count is not None:
            exactly = pred.name_count.get("exactly")
            names = {u.features["fold"] for u in reading.units if u.sense() == "name"}
            if exactly is not None and len(names) != exactly:
                return False
        if pred.unbound is not None:
            # mining candidate elided-comparative-standards: a general
            # negative-lookahead mirror (schemas.py's own comment) — these
            # slots are only ever reachable through an OPTIONAL sub-
            # sequence in the rule's own match tokens, so "bound" means
            # that optional continuation actually matched text.
            if any(s in slots for s in pred.unbound):
                return False
    return True


_TEMPLATE = re.compile(r"\{(\w+)(?:\.(\w+))?\}")
_SIGN = re.compile(r"sign\((\w+)\)")


def _canonical_phrase(units: tuple[Unit, ...]) -> str:
    """A span slot's value: per-token lemma normalization ONLY (plurals and
    known inflections fold to their lexicon lemma; unknown words stay
    verbatim), articles/punct dropped because they are already skippable
    senses. NO semantic loosening — 'opera singer' never becomes 'singer';
    a mismatch is a decline, never a guess (the phrase-key discipline,
    model.Atom docstring).

    A MERGED unit (condense.py's compound/attribute passes) renders as its
    full qualified phrase — fold words with the head canonicalized to the
    lemma — never the bare head lemma. The bare-lemma render silently
    re-opened the Fiedler trap the moment a modifier word entered the
    lexicon: with 'czech'/'choral' known, 'Czech choral conductor' condensed
    to ONE unit whose lemma is 'conductor', so "X is a Czech conductor"
    minted atom(x, 'conductor') and confidently answered "Is it true that X
    is a CHORAL conductor?" — the phrase-key discipline held only while the
    modifiers were UNKNOWN words (unmerged, verbatim in the span). Admitting
    a word must never loosen a phrase key."""
    parts = []
    for u in units:
        if u.sense() in SKIPPABLE_SENSES:
            continue
        words = (u.features.get("fold") or "").split()
        lemma = _lemma_of(u)
        parts.append(" ".join(words[:-1] + [lemma]) if len(words) > 1 else lemma)
    return " ".join(parts)


def intersective_split(
    words: list[str], head_lemma: str, reg: Registry
) -> tuple[list[str], list[str]]:
    """THE one definition of the intersectivity contract — learn.py's copular
    fold and the Atom variant emission below both call this, because a
    contract with two copies has already drifted (the _ACCOUNTED_VALUE_KINDS
    lesson).

    `words` is a merged nominal's fold words; returns (intersective, rest)
    where `intersective` are the modifier words in the opt-in
    `intersective_modifier` category (a structural NAME — the members live in
    packs; an empty category means nothing ever splits) and `rest` are the
    remaining modifiers. Dropping a modifier from a predicate, or asserting
    it alone, is sound ONLY for intersective ones: "Czech choral conductor"
    entails "a Czech", but "guard dog" does not entail "a guard" and "former
    president" does not entail "a president" — which is also why callers
    must never emit a bare-head variant unless every modifier was stripped
    as intersective."""
    mods = words[:-1]
    inter = [w for w in mods if reg.word_in_category(w, "intersective_modifier")]
    rest = [w for w in mods if w not in inter]
    return inter, rest


def atom_variants(fact: Fact, emit_fields: dict, slots: dict, reg: Registry) -> list[Fact]:
    """Intersective decomposition of a rule-emitted Atom — intersection-
    elimination at the predicate's TOP LEVEL only.

    A positive atom whose pred span leads with a merged nominal ("czech
    choral conductor who specialized in X") additionally yields the entailed
    variants: the span with the leading nominal's intersective modifiers
    stripped ("choral conductor who specialized in x") and each stripped
    modifier as its own single-word predicate ("czech" — no tail: the
    modifier predicates the subject directly). Everything after the leading
    nominal is untouched: stripping inside an ARGUMENT position ("specialized
    in czech music" -> "specialized in music") is not structurally provable —
    predicate positions are not uniformly monotone — so only the top-level
    nominal decomposes. NEGATIVE atoms never decompose (neg(A and B) licenses
    neither neg(A) nor neg(B)), and quantified cls NEVER strips anywhere (a
    universal's antecedent is downward-monotone; widening it is unsound)."""
    if not isinstance(fact, Atom) or fact.polarity is not True:
        return []
    raw = emit_fields.get("pred")
    if not isinstance(raw, str):
        return []
    m = _TEMPLATE.fullmatch(raw.strip())
    if not m or m.group(2) is not None:
        return []
    span = slots.get(m.group(1))
    if not isinstance(span, tuple):
        return []
    units = [u for u in span if u.sense() not in SKIPPABLE_SENSES]
    if not units or units[0].sense() != "noun":
        return []
    lead = units[0]
    words = (lead.features.get("fold") or "").split()
    if len(words) < 2:
        return []
    inter, rest = intersective_split(words, _lemma_of(lead), reg)
    if not inter:
        return []
    tail = _canonical_phrase(tuple(units[1:]))
    stripped_lead = " ".join(rest + [_lemma_of(lead)])
    prov = Provenance(
        source=f"{fact.provenance.source}/intersective",
        sentence=fact.provenance.sentence,
    )
    variants = [
        Atom(provenance=prov, entity=fact.entity,
             pred=f"{stripped_lead} {tail}".strip(), polarity=True)
    ]
    for w in inter:
        variants.append(
            Atom(provenance=prov, entity=fact.entity, pred=w, polarity=True)
        )
    return variants


def _slot_value(unit: Unit, attr: str | None) -> str:
    if isinstance(unit, tuple):
        # a span slot (MatchToken.span) binds a RUN of units; its only
        # rendering is the canonical phrase, whatever attr the template asks
        return _canonical_phrase(unit)
    if attr == "surface":
        return unit.surface
    if attr == "value":
        v = unit.features.get("value")
        return str(v) if v is not None else ""
    if attr == "components":
        # the comma-separated components of a `point`-typed slot (numbers.py
        # _TUPLE) — an ask's `p1: "{p1.components}"` template reads this and the
        # `coordinate` consumer splits it. A tuple has no scalar `value`, so
        # this is the only way to read one.
        return unit.features.get("components", "") or ""
    if attr == "owner":
        # the possessive owner of a `possessed`-typed slot (condense.py
        # merge-possessive) — an ask's `entity_owner: "{who.owner}"`
        # template reads this to retry an owner-qualified entity key when
        # the bare one comes back empty (facts.py's collision-time split).
        return unit.features.get("owner", "") or ""
    if attr == "qualifier":
        # the attributive modifier of a `qualified`-typed slot (condense.py
        # merge-attribute / merge-compound) — an ask's `entity_qualifier:
        # "{who.qualifier}"` template reads this to retry a qualifier-
        # tagged entity key when the bare one comes back empty (facts.py's
        # collision-time split). Increment 34's mirror of `owner`.
        return unit.features.get("qualifier", "") or ""
    if attr == "label":
        # the trailing index label of a noun merged from NOUN + single-
        # capital-letter INDEX (condense.py merge-label) — mining
        # candidate labeled-entity-relations: a relation rule's
        # `subject_label: "{who.label}"` / `standard_label: "{std.label}"`
        # reads this so saturate.py's `_relations_synth` can resolve a
        # labeled standard against the SPECIFIC same-label Quantity
        # instead of an arbitrary same-lemma one. Mirrors `owner`/
        # `qualifier` above, one field over (increment 74's field).
        return unit.features.get("label", "") or ""
    if attr == "number":
        # grammatical number of a pronoun/noun slot ('singular'/'plural') — a
        # combined ask's `subject_number: "{who.number}"` reads this to tell a
        # SINGULAR subject ("how much does HE have total"; one holder IS the
        # answer) from a PLURAL one ("...do THEY have altogether"; one holder
        # means a missed second). A structural feature (senses.py), no lexicon.
        return unit.features.get("number", "") or ""
    if attr == "qualified":
        # the FULL qualified phrase of a (possibly compound) noun: its fold
        # words with the head canonicalized to the lemma ('chocolate dogs' ->
        # 'chocolate dog'); a bare noun falls through to its lemma unchanged.
        # ask/is-membership queries THIS instead of the bare head lemma, so a
        # qualified question can never be satisfied by a bare-head fact —
        # "Rex is a dog" must not answer "Is Rex a CHOCOLATE dog?" (the
        # default `_lemma_of` render collapsed the compound to 'dog' and
        # answered 'yes'; a compound keeps its head's lemma by design, so the
        # collapse is correct for entity gates and loose for membership).
        words = (unit.features.get("fold") or "").split()
        lemma = _lemma_of(unit)
        if len(words) > 1:
            return " ".join(words[:-1] + [lemma])
        return lemma
    return _lemma_of(unit)


def _polarity_of(unit: Unit, reg: Registry) -> int:
    """sign(<slot>): the polarity of the deepest polarity-carrying category
    containing this word; +1 when none carries one."""
    word = _lemma_of(unit)
    best_depth, best = -1, 1
    for w in (word, unit.features.get("fold", "")):
        for tag in reg.word_categories.get(w, ()):
            chain = reg.cat_ancestors(tag)
            for depth, cat in enumerate(reversed(chain)):
                if cat in reg.category_polarity and depth > best_depth:
                    best_depth, best = depth, reg.category_polarity[cat]
    return best


def _resolve_field(
    raw: str | float | bool,
    slots: dict[str, Unit],
    reg: Registry,
    numeric: bool,
    log: ArithmeticLog | None,
    rule_id: str,
) -> object:
    if not isinstance(raw, str):
        return raw
    # pure template? ("{who}", "{item.lemma}")
    m = _TEMPLATE.fullmatch(raw.strip())
    if m and not numeric:
        name, attr = m.group(1), m.group(2)
        if name not in slots:
            raise EvaluationError(f"rule {rule_id}: emit references unbound slot {name!r}")
        return _slot_value(slots[name], attr)
    if not numeric:
        # a string with embedded templates
        return _TEMPLATE.sub(lambda mm: _slot_value(slots[mm.group(1)], mm.group(2)), raw)
    # numeric expression: slot names are variables; sign(x) precomputed
    expr = _SIGN.sub(lambda mm: str(_polarity_of(slots[mm.group(1)], reg)), raw)
    expr = _TEMPLATE.sub(lambda mm: mm.group(1), expr)  # allow {n} in expressions too
    env = {
        name: float(u.features["value"])
        for name, u in slots.items()
        if "value" in u.features
    }
    return evaluate(expr, env, log, source=rule_id)


_NUMERIC_FIELDS = {
    "value", "factor", "offset", "fraction", "numerator", "denominator",
    # mining candidate temporal-offset-age-recut: Relation's two new
    # signed-year offset fields (model.py) — a pattern rule emits them as
    # arithmetic expressions over bound slot values ("n", "-n"), the SAME
    # numeric-field discipline `offset` itself already gets, never a
    # template string.
    "subject_offset", "standard_offset",
    # mining candidate percent-change-values: PercentChange's own signed
    # direction, resolved via the SAME `sign(dir)` numeric-expression
    # mechanism the percent-comparative Relation rules already use for
    # `factor` — no rule anywhere else emits a field literally named
    # `sign`, so this addition changes zero existing rule's resolution.
    "sign",
}


def _build_fact(
    emit_fields: dict, fact_kind: str, slots: dict[str, Unit], reg: Registry,
    provenance: Provenance, log: ArithmeticLog | None, rule_id: str,
) -> Fact:
    cls = _FACT_CLASSES[fact_kind]
    kwargs = {}
    for key, raw in emit_fields.items():
        kwargs[key] = _resolve_field(raw, slots, reg, key in _NUMERIC_FIELDS, log, rule_id)
    if cls in (Quantity, FractionQuantity, RestQuantity) and "occurrence" not in kwargs:
        # a rule-emitted quantity is an event unless its verb is stative
        verb = kwargs.get("verb", "have")
        if not reg.word_in_category(verb, "state") and verb not in ("have", "be"):
            kwargs["occurrence"] = provenance.sentence
    elif cls is PercentChange and "occurrence" not in kwargs:
        # mining candidate percent-change-values: a percent-change is
        # ALWAYS an event (never a state, unlike Quantity/FractionQuantity/
        # RestQuantity above, which branch on verb category) — this is
        # what lets two percent-change events on the SAME entity in two
        # DIFFERENT sentences key apart (PercentChange.key() includes
        # `occurrence`) so `_entity_total` (answer.py) can chain them in
        # ascending sentence order instead of colliding.
        kwargs["occurrence"] = provenance.sentence
    return cls(provenance=provenance, **kwargs)


def rule_specificity(rule: PatternRule, reg: Registry) -> tuple[int, int, int]:
    """(required tokens, Σ category gate DEPTHS, where-count). Computed,
    never authored — a narrower category (pet ⊂ animal) scores strictly
    higher, which is what makes narrowing the conflict lever."""
    gate_depth = 0
    required = 0
    for seq in rule.match.values():
        flat = seq if seq and not isinstance(seq[0], list) else [t for s in seq for t in s]
        for tok in flat:
            if getattr(tok, "opt", None) is not None:
                continue
            required += 1
            cat = getattr(tok, "cat", None)
            if cat:
                gate_depth += len(reg.cat_ancestors(cat)) if cat in reg.category_parents else 1
    return (required, gate_depth, len(rule.where))


def specificity(match: Match, reg: Registry) -> tuple[int, int, int]:
    key = rule_specificity(match.rule, reg)
    return (len(match.consumed), key[1], key[2])


def subsumes(a: Match, b: Match, reg: Registry) -> bool:
    """a strictly subsumes b: a consumed a superset of b's units and is
    strictly more specific — the narrow rule silently wins."""
    return set(a.consumed) >= set(b.consumed) and specificity(a, reg) > specificity(b, reg)


def run_rules(
    reading: Reading,
    reg: Registry,
    phase: str,
    log: ArithmeticLog | None = None,
    is_question: bool = False,
) -> list[RuleMatchResult]:
    """Match ALL rules of the phase against the sentence; no short-circuit."""
    results: list[RuleMatchResult] = []
    sentence_folds = {u.features.get("fold") for u in reading.units}
    for rule in reg.rules:  # sorted by id at compile — deterministic
        if rule.phase != phase:
            continue
        key = "question" if is_question else "sentence"
        seq = rule.match.get(key) or rule.match.get("sentence")
        if seq is None or (seq and isinstance(seq[0], list)):
            continue  # multi-sentence rules handled at document level
        # trigger prefilter: every literal must be present
        lits = {t.lit for t in seq if t.lit is not None}
        if not lits <= sentence_folds:
            continue
        for m in match_all(reading, seq, reg):
            m.rule = rule
            m.specificity = specificity(m, reg)
            if not _check_where(rule, m.slots, reading, reg):
                continue
            provenance = Provenance(source=rule.id, sentence=reading.sentence_index)
            facts = []
            for e in rule.emits:
                fact = _build_fact(e.fields, e.fact, m.slots, reg, provenance, log, rule.id)
                facts.append(fact)
                # intersective decomposition (atom_variants): a no-op unless
                # the registry declares the opt-in category AND the emitted
                # fact is a positive span-pred Atom — no benchmark pack does
                # either, so every benchmark corpus is byte-identical
                facts.extend(atom_variants(fact, e.fields, m.slots, reg))
            results.append(RuleMatchResult(match=m, facts=facts))
    return results


def match_ask(
    reading: Reading, reg: Registry
) -> tuple[AskRule, dict[str, str], Match] | None:
    """Match question shapes; the MOST SPECIFIC matching ask wins (max
    consumed units — a longer match read more of the question), then Σ CATEGORY
    GATE DEPTH, with id order as the deterministic tie-break. Re-landed alone
    from the reverted increment 8 per docs/negative-results.md.

    The gate-depth term is the same second key `rule_specificity` has always used
    for RULES, brought to asks: a category-gated slot read MORE than a bare typed
    one, so on an equal-length match it is the more specific reading. Without it
    the tie fell to ALPHABETICAL ID ORDER, which encodes nothing — "How many
    inches are in 3 feet?" went to ask/how-many-in-place (which reads "3 feet" as
    a PLACE and declines) purely because 'h' < 'u'. Ties are the only matches
    affected; any match that already won on length still wins.
    """
    best: tuple[AskRule, dict[str, str], Match] | None = None
    for ask in reg.asks:  # sorted by id — deterministic tie-break
        seq = ask.match["question"]
        m = match_sequence(reading, seq, reg)
        if m is None:
            continue
        resolved = {}
        for key, raw in ask.resolves.items():
            try:
                resolved[key] = _TEMPLATE.sub(
                    lambda mm: _slot_value(m.slots[mm.group(1)], mm.group(2)), raw
                )
            except KeyError:
                # the template references an OPTIONAL slot that didn't bind
                # ("verb: {verb}" with the opt-group absent) — omit the key
                # and let the consumer's default apply
                continue
        if best is None or _ask_rank(m, ask, reg) > _ask_rank(best[2], best[0], reg):
            best = (ask, resolved, m)
    return best


def _ask_rank(m: Match, ask: AskRule, reg: Registry) -> tuple[int, int]:
    """(consumed units, Σ category-gate depth) — see match_ask. Strictly `>`
    keeps id order as the final tie-break, exactly as before."""
    gate_depth = 0
    for tok in ask.match["question"]:
        if getattr(tok, "opt", None) is not None:
            continue
        cat = getattr(tok, "cat", None)
        if cat:
            gate_depth += len(reg.cat_ancestors(cat)) if cat in reg.category_parents else 1
    return (len(m.consumed), gate_depth)
