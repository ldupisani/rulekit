"""`membership-verdict` — Is <name> a <collection>? — from Membership facts.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("membership-verdict", time_scoped=True)
def membership_verdict(ctx: ConsumerContext):
    from ..answer import Answer
    from ..model import Membership

    member, collection = ctx.query["member"], ctx.query["collection"]
    singular = ctx.reg.plural_to_singular.get(collection, collection)
    # AN UNREAD NAME IS A DECLINE — "BINDABLE is not READ", for names.
    #
    # Value-accounting already declines on an unread NUMBER. A dropped name
    # carries no digits, so no numeric guard can see it; this is that same
    # contract for the one kind of value this consumer binds. It fires when
    # the question STATES something the query never read — "Is Mary a student
    # AT YALE?" binds member='mary'/coll='student' and would otherwise answer
    # about Mary-as-student-generally, ignoring the restriction.
    #
    # It is NOT what keeps the member slot honest — `at_start` on the ask's
    # fronted auxiliary does that (see ask/is-membership). This guard was
    # written first, against the witness "Is it true that Jim is a Knicks
    # player?", and it was INCOMPLETE: keyed on an unread NAME, it sailed
    # straight past "...that THE PILOT is a Knicks player", which has no name
    # to be unread and still committed 'no' about the Knicks. The witness was
    # closed and the class left open, one value-kind over. The two now sit at
    # the right levels — the ask decides WHICH construction it may read, this
    # decides whether the reading used everything the question said.
    named = {u.features["fold"] for u in ctx.question.units if u.sense() == "name"}
    unread = named - {member}
    if unread:
        return Answer(
            "decline", None,
            f"question names {sorted(unread)!r} but the membership query is "
            f"about {member!r} — an unread name",
        )
    for f in ctx.store.by_kind(Membership):
        if f.member == member and f.collection == singular:
            return Answer("verdict", "yes" if f.polarity else "no", "membership fact")
    # packs/logic's ground rules CONSUME a copular premise, which
    # suppresses the fold's Membership fact for that sentence — the same
    # statement now lives as a phrase-keyed Atom instead. A single-noun
    # collection is a one-token phrase, so reading it here keeps the
    # exact-phrase discipline (a qualified atom like 'rovers player' can
    # never satisfy a bare 'player' query). Registries without
    # packs/logic have no Atom facts and skip this loop entirely.
    from ..model import Atom

    for f in ctx.store.by_kind(Atom):
        if f.entity == member and f.pred == singular:
            return Answer("verdict", "yes" if f.polarity else "no", "logic atom")
    return Answer("verdict", "undetermined", "no membership fact either way")
