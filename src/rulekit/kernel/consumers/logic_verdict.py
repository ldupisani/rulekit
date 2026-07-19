"""`logic-verdict` — The FOLIO embedded-declarative verdict, from phrase-keyed atoms.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("logic-verdict", time_scoped=True)
def logic_verdict(ctx: ConsumerContext):
    from ..answer import Answer

    # The FOLIO-style embedded-declarative verdict: "Is it true that
    # <subject> <predicate phrase>?" — answered ONLY from phrase-keyed
    # logic facts (model.Atom, emitted by packs/logic extraction rules and
    # the packs/logic synth chain), never from the generic SVO fold, whose
    # head-lemma facts drop qualifiers ("opera singer" -> 'singer') and
    # would make this consumer a confident-wrong machine (Phase 0a).
    #
    # FULL READ IS VERIFIED, NOT ASSUMED: the ask's final span runs to the
    # sentence end by construction, but the wrapper tokens and subject sit
    # outside it — every meaningful question unit must be in the match's
    # consumed set, the b1db917/b5655ca lesson generalized from names to
    # ALL value kinds ("Is Mary a student AT YALE?" declines).
    from ..model import Atom
    from ..patterns import SKIPPABLE_SENSES

    unread = [
        u.surface
        for u in ctx.question.units
        if u.sense() not in SKIPPABLE_SENSES and u.uid not in ctx.match.consumed
    ]
    if unread:
        return Answer(
            "decline", None,
            f"question states {unread!r} but the logic query never read it",
        )
    entity = ctx.query["entity"]
    pred = ctx.query["pred"]
    pol = ctx.query.get("polarity", "true") == "true"
    # Phase 0 (composition-design.md): a definite-DESCRIPTION question
    # ('…the football club?') is never satisfied by an indefinite
    # premise ('…a football club') — the shared flat key hides the
    # article, so the bit rides on the atom and the ask field
    from ..patterns import field_definite_common

    q_defcom = field_definite_common(ctx.ask, "pred", ctx.match, ctx.question, ctx.reg)
    for f in ctx.store.by_kind(Atom):
        if q_defcom and f.indef_obj:
            continue
        if f.entity == entity and f.pred == pred:
            # open-world, polarity-aware: a stored negative answers 'no'
            # to the positive question and 'yes' to the negated one; the
            # ABSENCE of a fact is never falsity — that is 'undetermined'
            return Answer(
                "verdict",
                "yes" if f.polarity == pol else "no",
                f"logic atom {f.entity!r} {f.pred!r} "
                f"({'+' if f.polarity else '-'}) via {f.provenance.source}",
            )
    return Answer("verdict", "undetermined", "no logic fact decides it")
