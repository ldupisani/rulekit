"""Condensation: merge local structures into richer single units, to a
fixpoint. Merge is the structural move (adjective+noun = one restricted
concept, "mango trees" = one compound, "New York" = one name); binding is
the relational one — merge only when the result is genuinely one concept.

Order matters: NOMINAL merges run to a fixpoint first (so "mango trees" is
one compound before a count claims it), then the count+noun merge attaches
values to the completed nominals.
"""

from __future__ import annotations

from ..data.registry import Registry
from .learn import _has_event_polarity
from .model import Reading, Unit


def _merge(reading: Reading, i: int, head_features_from: Unit, kind: str, reason: str,
           extra: dict | None = None) -> Unit:
    units = reading.units
    a, b = units[i], units[i + 1]
    merged = reading.new_unit(a.words + b.words, dict(head_features_from.features))
    merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
    units[i : i + 2] = [merged]
    reading.record(kind, merged, extra or {}, reason)
    return merged


def _nominal_pass(reading: Reading, reg: Registry) -> bool:
    units = reading.units
    # perfect tense: have-lemma verb + verb -> ONE verb ("has read 32 books"
    # is a reading event, not a having plus a mystery participle)
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        if (
            a.sense() == "verb"
            and a.features.get("lemma") == "have"
            and b.sense() == "verb"
        ):
            merged = reading.new_unit(a.words + b.words, dict(b.features))
            merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
            units[i : i + 2] = [merged]
            reading.record(
                "merge-perfect", merged, {},
                f"perfect tense {merged.surface!r} — one verb, lemma "
                f"{b.features.get('lemma', b.features['fold'])!r}",
            )
            return True
    # polarity-tagged event verb + a following directional particle -> ONE
    # verb lexeme ("gives away", "takes away", "throws away") — otherwise
    # the particle reads as a free adverb, orphaning the fraction/count it
    # modifies and tripping value-accounting on an unaccounted number
    # (mining candidate particle-event-verbs). Gated on the base verb
    # ALREADY carrying a polarity tag (_has_event_polarity, the
    # increment-45 invariant): an untagged verb + particle ("looked up",
    # "knows off") stays exactly as today — decline-safe by construction,
    # never a blanket "every adverb after a verb" merge.
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        if (
            a.sense() == "verb"
            and reg.word_in_category(b.features.get("fold", ""), "verb_particle")
            and _has_event_polarity(a.features.get("lemma", a.features.get("fold", "")), reg)
        ):
            _merge(
                reading, i, a, "merge-particle-verb",
                f"{a.surface!r} + particle {b.surface!r} = one event verb "
                f"(polarity carried by {a.features.get('lemma', a.surface.lower())!r})",
            )
            return True
    # owner + 's + owned -> one owner-attributed noun ("Tom's apples")
    for i in range(len(units) - 2):
        a, b, c = units[i], units[i + 1], units[i + 2]
        if (
            a.sense() in ("name", "noun")
            and b.sense() == "possessive"
            and c.sense() == "noun"
        ):
            owner = a.features.get("lemma", a.features.get("fold", a.surface.lower()))
            merged = reading.new_unit(a.words + b.words + c.words, dict(c.features))
            merged.features["fold"] = f"{a.features['fold']} 's {c.features['fold']}"
            attrs = list(c.features.get("attributes", []))
            attrs.append(owner)
            units[i : i + 3] = [merged]
            reading.record(
                "merge-possessive", merged,
                # `owner` is the ENTITY-IDENTITY qualifier: "Kennedy's house"
                # and "Benedict's house" both fold to the bare noun lemma
                # 'house', so without it two possessed nouns of the same
                # kind collide as one fact-store entity (learn.py/patterns.py
                # both read this feature to build the qualified key).
                # `attributes` is separate pre-existing bookkeeping, unread
                # elsewhere today — left untouched.
                {"attributes": attrs, "owner": owner},
                f"{a.surface!r} owns {c.surface!r} — one owner-attributed noun",
            )
            return True
    # noun + trailing single-capital-letter INDEX -> one label-distinguished
    # noun ("Jar A", "Class B", "Machine C") — the same entity-identity
    # problem merge-possessive/merge-attribute already solve for possessive
    # owners and attributive modifiers (mining candidate
    # labeled-entity-identity), one label kind further: without this, "Jar
    # A has 28 marbles. Jar B has 15 marbles." both bare-fold to entity=
    # 'jar' and collide as one fact-store holding instead of two. The
    # label is PRODUCTIVE INDEX MORPHOLOGY (a single capital letter
    # standing in for "the Nth one"), never a lexicon fact — no vocabulary
    # is admitted here. Two structural forms reach this token, both gated
    # to exactly one uppercase LETTER (never a name, never a word):
    #   - unknown: senses.py never guesses "name" for a ONE-CHARACTER
    #     token (its capitalized-word branches require `surface[1:].
    #     islower()`, which is False for an empty remainder), so a bare
    #     single capital letter with no lexicon entry stays unknown ("Jar
    #     B" — 'b' has no entry).
    #   - article: the one single-letter word WITH a lexicon entry, "a" —
    #     "Jar A" downcases to the indefinite article's own fold. Gated on
    #     the SENSE name (structural), never the literal word: no other
    #     single-letter token in English carries the `article` sense, and
    #     the indefinite article never immediately FOLLOWS a noun in real
    #     text (articles precede the noun they introduce), so this can't
    #     be confused with an ordinary "a jar" — that "a" is lowercase and
    #     precedes, not follows, its noun.
    # Both forms additionally require the label be UPPERCASE — this is
    # what keeps "if I have" (I is the pronoun, its own sense, never
    # matches) and every ordinary lowercase "a" safely out, with no word
    # list at all. "Mr. B" and "A.T. Cross" are blocked structurally too:
    # a period is its own unit, so the title/initial and the letter are
    # never ADJACENT units the way this pass requires.
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        if (
            a.sense() == "noun"
            and len(b.words) == 1
            and len(b.surface) == 1
            and b.surface.isupper()
            and (
                b.sense() == "article"
                or (b.sense() is None and b.features.get("unknown"))
            )
        ):
            label = b.surface
            merged = _merge(
                reading, i, a, "merge-label",
                f"{a.surface!r} + index {b.surface!r} — one "
                f"label-distinguished noun (label {label!r})",
                {"label": label},
            )
            return True
    # timeperiod noun + trailing integer -> one period-identified noun ("the
    # year 1946", "week 3", "January 1946") — the numeric twin of the
    # single-letter label above. A number immediately FOLLOWING a timeperiod
    # noun is an IDENTIFIER, never a quantity of it ("year 1946" is not 1946
    # years — that construction is count+noun, handled by merge-count and
    # unreachable from here since nominal merges run first). Gated on the
    # CATEGORY name (structural; the members — 'year', months, weekdays —
    # live in packs), and on the number NOT being claimable as a count for a
    # noun that follows it: "Every year 500 people visit" must leave 500 to
    # quantify 'people', so a following noun blocks the merge outright —
    # the ambiguous "In the year 1946 books were sold" stays unmerged and
    # decline-safe (precision before coverage).
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        lemma = a.features.get("lemma", a.features.get("fold", ""))
        if (
            a.sense() == "noun"
            and a.features.get("number") != "plural"
            and reg.word_in_category(lemma, "timeperiod")
            and b.sense() == "value"
            and b.features.get("value_kind") == "count"
            and not b.features.get("pattern_consumed")
            and float(b.features["value"]).is_integer()
            and float(b.features["value"]) > 0
            and not (i + 2 < len(units) and units[i + 2].sense() == "noun")
        ):
            label = str(int(b.features["value"]))
            _merge(
                reading, i, a, "merge-period-index",
                f"{a.surface!r} + period index {b.surface!r} — one "
                f"period-identified noun (label {label!r})",
                {"label": label},
            )
            return True
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        # adjective + noun -> restricted noun ("red apple")
        if a.sense() == "adjective" and b.sense() == "noun":
            attrs = list(b.features.get("attributes", []))
            attrs.append(a.features.get("lemma", a.features["fold"]))
            # `qualifier` is the ENTITY-IDENTITY qualifier, mirroring
            # merge-possessive's `owner`: "coconut trees" and "mango trees"
            # both fold to the bare noun lemma 'tree', so without it two
            # same-noun holdings distinguished only by their modifier
            # collide as one fact-store entity (learn.py/facts.py both
            # read this feature to split a genuine value conflict).
            # Preference for an INNER qualifier (already tagged on `a` by
            # an earlier merge in this fixpoint) over the outer modifier's
            # own lemma — best-effort for nested chains, not required by
            # this candidate's target class. `attributes` is separate
            # pre-existing bookkeeping, unread elsewhere today.
            qualifier = a.features.get("qualifier") or a.features.get(
                "lemma", a.features["fold"]
            )
            _merge(reading, i, b, "merge-attribute",
                   f"adjective {a.surface!r} restricts {b.surface!r}",
                   {"attributes": attrs, "qualifier": qualifier})
            return True
        # adjective + elided measure-noun anaphor -> a qualified but
        # UNRESOLVED anaphoric noun ("12 yellow ONES", "twice as many
        # green ONES as yellow ones" — mining candidate measure-noun-
        # anaphor, infrastructure for the conjunct-comparative class). The
        # anaphor word itself never denotes the real measure — only its
        # qualifier is genuine — so this is NOT merge-attribute's ordinary
        # case (b stays sensed 'pronoun', never 'noun', up to this point;
        # see the measure_anaphor category's own notes in packs/core-
        # english/categories/core.yaml for why 'ones' is never given a
        # second, ambiguous 'noun' sense). Explicitly re-declares the
        # compound's own `senses` to `["noun"]` so every EXISTING generic
        # noun-consumption path (count-merge below, dobj/subject Quantity-
        # building in learn.py) picks it up unchanged, exactly like any
        # other restricted noun; `qualifier` stays LOCAL to this adjective
        # (never inherited from whatever the anaphor eventually resolves
        # to). `measure_anaphor: True` is the marker document.py's
        # `_bind_measure_anaphor` and learn.py's `_lemma` both read: zero
        # or two-or-more antecedent candidates leaves the compound
        # unresolved, and `_lemma` then returns a reserved sentinel no ask
        # can ever match — a silent, harmless decline, never a guess.
        #
        # Gated OUT whenever an article sits immediately left of the
        # adjective ("the yellow ones", "half of THE yellow ones"): that
        # DEFINITE shape names a subset of an already-established pool —
        # PartitionQuantity/FractionQuantity territory, whose synthesizers
        # (saturate.py) resolve a bare, UNQUALIFIED collection reference
        # against the unique prior pool and have no qualifier-matching
        # logic at all. Left admitted, "half of the yellow ones" would
        # satisfy fraction-of-pool's collection slot (now that this
        # compound presents as an ordinary noun) and resolve against the
        # WHOLE unqualified pool, silently dropping the 'yellow' qualifier
        # — a confident wrong the dev-holdout gate caught (item
        # 06dbd5d03f40: expected 84, got 336 — half of ALL balloons
        # instead of half of the yellow quarter). This candidate's own
        # target shapes are all INDEFINITE ("12 yellow ones", "twice as
        # many green ones as yellow ones", "as blue ones") — none carry a
        # preceding article — so excluding the definite form costs this
        # candidate nothing while closing that hole structurally.
        if (
            a.sense() == "adjective"
            and b.sense() == "pronoun"
            and reg.word_in_category(b.features.get("fold", ""), "measure_anaphor")
            and (i == 0 or units[i - 1].sense() != "article")
        ):
            attrs = list(b.features.get("attributes", []))
            attrs.append(a.features.get("lemma", a.features["fold"]))
            qualifier = a.features.get("qualifier") or a.features.get(
                "lemma", a.features["fold"]
            )
            _merge(
                reading, i, b, "merge-measure-anaphor",
                f"{a.surface!r} qualifies anaphoric head {b.surface!r} "
                f"(unresolved measure noun)",
                {
                    "attributes": attrs, "qualifier": qualifier,
                    "senses": ["noun"], "measure_anaphor": True,
                    # the compound is a NOUN now, not a pronoun — drop the
                    # inherited unmet 'refers' obligation (it would
                    # otherwise report a stale, misleading "needs a
                    # refers" deficiency; resolution is tracked purely via
                    # `antecedent_lemma`, never this obligation)
                    "obligations": [],
                },
            )
            return True
        # noun + noun -> compound, head = the RIGHT noun ("mango trees")
        if (
            a.sense() == "noun" and b.sense() == "noun"
            and "value" not in a.features
        ):
            attrs = list(b.features.get("attributes", []))
            attrs.append(a.features.get("lemma", a.features["fold"]))
            qualifier = a.features.get("qualifier") or a.features.get(
                "lemma", a.features["fold"]
            )
            _merge(reading, i, b, "merge-compound",
                   f"compound noun: {a.surface!r} modifies head {b.surface!r}",
                   {"attributes": attrs, "qualifier": qualifier})
            return True
        # CAPITALIZED known word + name -> one name ("Tall Tuna", "Cat Cafe
        # Meow"): the capitalization, not the part of speech, is the naming
        # signal — sentence-initial known nouns otherwise split the name
        # ('cafe meow' vs 'cat cafe paw') and relation chains never connect
        if (
            a.sense() in ("adjective", "noun")
            and len(a.words) == 1  # a MERGED unit ("Last year") is not a name part
            and a.surface[:1].isupper()
            and "value" not in a.features
            and b.sense() == "name"
        ):
            merged = _merge(reading, i, b, "merge-name",
                            f"capitalized {a.surface!r} is part of the name {b.surface!r}")
            merged.features["lemma"] = merged.features["fold"]
            return True
        # name + name -> one name ("New York")
        if a.sense() == "name" and b.sense() == "name":
            merged = _merge(reading, i, a, "merge-name",
                            f"consecutive names {a.surface!r} {b.surface!r} = one name")
            merged.features["lemma"] = merged.features["fold"]
            return True
    # NAME + partitive + NAME -> one TITULAR name ("Salmon of Doubt",
    # "University of Edinburgh", "House of Commons"): an English title
    # embeds its particle between capitalized parts, and pairwise merging
    # can never see across it — the single-unit name slots downstream then
    # fail on every titular subject and the sentence goes unread. Gated on
    # the `partitive` CATEGORY (the word lives in core-english's pack data;
    # the kernel references only the category name) and on BOTH neighbors
    # being NAME-sensed already — a noun/quantifier/number left of 'of'
    # never merges ("half of Boston", "the cost of Ann", "All of Emily's
    # friends" — 'All' is quantifier-sensed, 'cost' noun-sensed), so every
    # partitive arithmetic reading is byte-identical by construction.
    for i in range(len(units) - 2):
        a, b, c = units[i], units[i + 1], units[i + 2]
        if (
            (
                a.sense() == "name"
                # ... or a CAPITALIZED known word — the same signal the
                # pairwise "Tall Tuna" case reads: 'Salmon' in "The Salmon
                # of Doubt" is a lexicon fish, and a known word never falls
                # back to the name sense, so name-only left sides would
                # skip every title whose first word the lexicon knows
                or (
                    a.sense() in ("adjective", "noun")
                    and len(a.words) == 1
                    and a.surface[:1].isupper()
                    and a.words[0].index > 0  # sentence-initial caps are
                    # weak evidence ("Members of Pappy's have ..." is a
                    # plural description, not a title); mid-sentence
                    # capitalization is senses.py's own naming signal
                    and "value" not in a.features
                )
            )
            and reg.word_in_category(b.features.get("fold", ""), "partitive")
            and c.sense() == "name"
        ):
            # head features from the NAME side (the pairwise capitalized
            # case's own choice): the left word may be a known noun, and
            # inheriting its noun sense would leave the title unable to
            # bind any name slot
            merged = reading.new_unit(
                a.words + b.words + c.words, dict(c.features)
            )
            merged.features["fold"] = (
                f"{a.features['fold']} {b.features['fold']} {c.features['fold']}"
            )
            merged.features["lemma"] = merged.features["fold"]
            units[i : i + 3] = [merged]
            reading.record(
                "merge-name", merged, {},
                f"titular name {a.surface!r} {b.surface!r} {c.surface!r} = one name",
            )
            return True
    return False


def _count_pass(reading: Reading, reg: Registry) -> bool:
    units = reading.units
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        # count + noun -> one counted noun ("3 apples" is one concept);
        # multipliers/fractions stay separate (they scale a referent)
        if (
            a.features.get("value_kind") == "count"
            and a.sense() != "noun"
            and b.sense() == "noun"
            and not a.features.get("pattern_consumed")
        ):
            _merge(reading, i, b, "merge-count",
                   f"count {a.surface!r} quantifies {b.surface!r} — one concept",
                   {"value": a.features["value"], "value_kind": "count"})
            return True
    return False


def condense(reading: Reading, reg: Registry) -> Reading:
    # joint fixpoint with nominal priority: a count merge can expose a new
    # nominal merge ("Tom's [3 apples]"), so alternate until neither fires
    while True:
        if _nominal_pass(reading, reg):
            continue
        if _count_pass(reading, reg):
            continue
        return reading
