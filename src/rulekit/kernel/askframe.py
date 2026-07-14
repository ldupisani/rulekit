"""The compositional ask frame — a SUM where match_ask() is a PRODUCT.

WHY THIS EXISTS (docs/negative-results.md, "The ask layer is a PRODUCT"):

`match_ask` matches a question against ~79 flat token TEMPLATES. Each spells out a
whole question — wh-word, auxiliary, entity, measure, aggregation — so the
templates enumerate the CELLS of a product:

    {how many, how much, ...}          wh-operator
  x {bare, named, common-noun, ...}    entity form
  x {simple, combined, average, ...}   aggregation
  x {do/does/did, will, has+Ven, ...}  tense / aspect / voice

The matcher has NO ALTERNATION PRIMITIVE — ask/how-many-combined-in-all says so in
its own comment ("the matcher cannot express as an alternative WITHIN that ask") —
so every variant of every coordinate becomes another whole-question template. 79 of
them, and 496 dev-train questions still match none. They are MULTIPLY blocked, so
widening any ONE coordinate converts ZERO (measured: the future_modal buy-test,
0 SOLVED / 1 DECL->WRONG).

This module reads the question BY ROLE: it finds the wh-operator, the measure, the
entity and the aggregation cue wherever they sit, and maps them onto the SAME
consumers answer.py already implements. Coordinates are declared once each, not
enumerated as their product. Tense/aspect/voice are simply NOT ASKED FOR — they are
properties of the question, not of what it asks, exactly as deixis.py established
for the temporal origo ("one scan; every consumer, every ask shape, for free").

THE THREE INVARIANTS. All load-bearing; the third was bought with a wrong.

1. FALLBACK ONLY. answer() calls this ONLY when match_ask() returned None, so every
   question the 79 templates already answer takes its identical path. 0 BROKE by
   construction.

2. DECLINE UNLESS UNAMBIGUOUS. This layer COMMITS, and every TEST kill in this
   campaign came from a committer firing on unseen structure. Two candidate
   entities, two candidate verbs => None. A decline is free; a wrong is not.

3. THE QUESTION MUST BE READ IN FULL — question accounting.
   ------------------------------------------------------------------------
   A template that does not match simply declines: its RIGIDITY IS ITS SAFETY.
   A role-based frame is permissive by nature, so it must pay for that
   flexibility with a stricter refusal rule, or every operator it fails to model
   becomes a CONFIDENT WRONG.

   Bought the hard way. v1 of this file had invariants 1 and 2 and still shipped:

       Q:     "how many ounces of milk does James have LEFT?"    gold 371
       frame: {consumer: single-entity, entity: james, measure: ounce}
       got:   -13.0

   The frame silently DROPPED `left` — an operator selecting a remainder reading —
   and confidently answered a question nobody asked. A blacklist of known-bad
   operators would only re-enumerate the product from the other side and still miss
   whatever it had not thought of.

   So: EVERY content-bearing unit in the question must be consumed by a role. One
   unconsumed content word means the frame did not read the question => decline.
   This is exactly the value-accounting invariant the premise side already runs (a
   stated number that reaches no fact declines the item) — applied to the question.
   Unmodelled operators (`left`, `more ... than`, `each`) fail SAFE, and a future
   operator nobody has thought of fails safe too, which a blacklist cannot promise.

NO LEXICON HERE (constitution rule 1). This module names SENSES and CATEGORY NAMES
as structure ('aggregate', 'mean_cue', 'noun'); every WORD lives in the packs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Reading, Unit
from .patterns import Match
from ..data.registry import Registry
from ..data.schemas import AskRule

# Senses that carry no propositional content — they need no role to be "read".
#
# `modal` is NOT here, and that is the single most important line in this file.
#
# The tempting premise — "TAM is orthogonal to what a question asks, so strip it"
# — is FALSE, and it cost two guard tests (test_mining_increment_66, _96):
#
#     'will' / 'would'  (future)    factually transparent: same facts, later time
#     'can' / 'could' / 'must' ...  CHANGE THE QUESTION
#
# "how many CAN he buy" is not "how many DOES he buy" — the first asks a CAPACITY
# (budget / unit price), the second a fact. v4 listed `modal` as inert, so the
# frame answered hypothetical questions as factual ones and committed numbers on
# items the engine had DELIBERATELY declined (the increment-14 kirsty lesson: a
# wanted purchase is not a purchase). The dev diff called it NEUTRAL — 3,772 items
# saw nothing. Two synthetic unit tests caught it. A clean DEV gate is necessary
# and NEVER sufficient.
#
# So the auxiliary sense (do/does/did) is inert, and `future_modal` is admitted by
# the ask templates that want it — but a bare `modal` is an UNREAD CONTENT WORD and
# invariant 3 declines the question. Exactly the behaviour the 79 templates already
# have, preserved rather than flattened.
_INERT_SENSES = {"article", "punct", "preposition", "auxiliary", "interrogative"}

# The wh-quantifier heading a QUANTITY question: "how MANY", "how MUCH".
# Anchored on the literal pair — bare 'how' also heads MANNER questions ("how did
# he do it") which name no measure and which this frame must never claim.
_HOW = "how"
_WH_QUANTIFIER = ("many", "much")

# The aggregation categories this frame MODELS, and the consumer each selects.
# Category NAMES as structure (rule 1); the words are pack-owned. Anything else
# operator-like in the question is, by invariant 3, simply an unconsumed content
# word — so it declines without this module needing to name it.
_MEAN_CUE = "mean_cue"       # 'average', 'mean'  -> the `average` consumer
_SUM_CUE = "aggregate"       # 'total', 'altogether', 'combined' -> `combined`


@dataclass(frozen=True)
class AskFrame:
    wh: str
    measure: Unit
    entity: Unit | None
    verb: Unit
    aggregation: Unit | None
    consumer: str


def _fold(unit: Unit) -> str:
    return unit.features.get("fold", unit.surface.lower())


def _lemma(unit: Unit) -> str:
    return unit.features.get("lemma", _fold(unit))


def _resolved_entity(unit: Unit) -> str | None:
    """The lemma this subject SPEAKS AS, following discourse binding.

    A pronoun subject ("how many does HE have?") is not ambiguous once the
    document loop has bound it: `_bind_discourse` records a met `refers`
    obligation pointing at the antecedent. Reading through it is the same move
    patterns._lemma_of already makes for every template ask — reusing the
    resolution rather than re-deriving it. An UNBOUND pronoun (a bare plural
    'they' with no antecedent) resolves to nothing and the caller declines.
    """
    if unit.sense() == "pronoun":
        for ob in unit.obligations():
            if ob.need == "refers" and ob.met and isinstance(ob.target, Unit):
                return _lemma(ob.target)
        return None
    if unit.sense() == "name":
        return _lemma(unit)
    return None


def compose(
    question: Reading, reg: Registry
) -> tuple[AskRule, dict[str, str], Match] | None:
    """Read `question` by role. None on ambiguity, or on ANY unread content."""
    units = question.units

    # --- the WH-OPERATOR: 'how many' / 'how much' --------------------------
    wh = None
    for i in range(len(units) - 1):
        if _fold(units[i]) == _HOW and _fold(units[i + 1]) in _WH_QUANTIFIER:
            wh = i + 1
            break
    if wh is None:
        return None

    read: set[int] = {units[wh - 1].uid, units[wh].uid}

    # --- the MEASURE: the nominal the wh-quantifier scopes over -------------
    # An ELIDED measure ("how many did he add?") is a different consumer with its
    # own resolution rules; this frame does not claim it.
    measure = next((u for u in units[wh + 1:] if u.sense() in ("noun", "name")), None)
    if measure is None:
        return None
    read.add(measure.uid)

    # The measure's nominal complement ("how many pounds OF VEGETABLES") is NOT
    # marked read here, and that is deliberate — it falls to invariant 3 and
    # declines the question.
    #
    # v3 DID mark it read, and shipped a wrong:
    #
    #     Q:     "How many pounds of vegetables did he use?"          gold 6
    #     frame: {consumer: single-entity, measure: 'pound', entity: 'john'}
    #     got:   1.0                    <- the "all but 1 pound" of BEEF
    #
    # The complement RESTRICTS the measure — pounds-of-vegetables is not
    # pounds-of-beef — but the `single-entity` consumer keys on the bare measure
    # lemma, so the frame had nowhere to put it and silently dropped it. Marking
    # it read satisfied invariant 3 VACUOUSLY: touched, never used.
    #
    # THE INVARIANT, TIGHTENED: a content word counts as read only when it is
    # USED in `resolves`. A safety check that can be satisfied vacuously launders
    # a guess as a checked answer — strictly worse than no check at all. Keying
    # the complement into the measure is the right fix and needs consumer support
    # (the template asks carry pp/qualifier slots for exactly this); until then it
    # declines, which is free.
    tail_start = units.index(measure) + 1

    # --- the AGGREGATION cue, wherever it sits ------------------------------
    aggregation = None
    consumer = None
    for u in units:
        if reg.word_in_category(_fold(u), _MEAN_CUE):
            aggregation, consumer = u, "average"
            break
        if reg.word_in_category(_fold(u), _SUM_CUE):
            aggregation, consumer = u, "combined"
            break
    if aggregation is not None:
        read.add(aggregation.uid)

    # --- the ENTITY and the VERB -------------------------------------------
    predicate = units[tail_start:]
    entities = [u for u in predicate if u.sense() in ("name", "pronoun")]
    verbs = [u for u in predicate if u.sense() == "verb"]

    # INVARIANT 2 — decline unless unambiguous.
    if len(entities) > 1 or len(verbs) != 1:
        return None
    verb = verbs[0]
    entity = entities[0] if entities else None
    read.add(verb.uid)
    if entity is not None:
        read.add(entity.uid)

    # --- CONSUMER SELECTION: a SUM over coordinates, not a product of cells --
    entity_lemma = _resolved_entity(entity) if entity is not None else None
    if consumer is None:
        # A subject with no aggregation cue is the single-holder reading — but
        # ONLY once the subject actually denotes someone. A pronoun reads through
        # its bound antecedent (_resolved_entity); an UNBOUND one ("how many do
        # THEY have?" with no antecedent) denotes nothing and is genuinely
        # ambiguous between the single-holder and combined readings => decline.
        if entity_lemma is None:
            return None
        consumer = "single-entity"

    # --- INVARIANT 3 — QUESTION ACCOUNTING: every content word must be read --
    # The frame's licence to be permissive. One unread content unit means an
    # operator (or anything else) went unmodelled -> the question was not read.
    for u in units:
        if u.uid in read or u.sense() in _INERT_SENSES:
            continue
        return None

    resolves: dict[str, str] = {
        "consumer": consumer,
        "measure": _lemma(measure),
        "verb": _lemma(verb),
    }
    if consumer == "single-entity":
        resolves["entity"] = entity_lemma  # type: ignore[arg-type]

    rule = AskRule(id=f"ask/frame-{consumer}", match={"question": []},
                   resolves=dict(resolves))
    consumed = tuple(sorted(read))
    return rule, resolves, Match(rule=rule, slots={}, consumed=consumed)
