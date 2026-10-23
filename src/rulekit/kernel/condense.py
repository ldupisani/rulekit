"""Condensation: merge local structures into richer single units, to a
fixpoint. Merge is the structural move (adjective+noun = one restricted
concept, "mango trees" = one compound, "New York" = one name); binding is
the relational one — merge only when the result is genuinely one concept.

Order matters: NOMINAL merges run to a fixpoint first (so "mango trees" is
one compound before a count claims it), then the count+noun merge attaches
values to the completed nominals.
"""

from __future__ import annotations
from .reference_identity import reference_from_unit

import datetime
import re

from ..data.registry import Registry
from .learn import _has_event_polarity
from .model import Reading, Unit


def condense_lexical_phrases(reading: Reading, reg: Registry) -> Reading:
    """Merge declared atomic phrases before role disambiguation.

    Phrase vocabulary lives in the lexicon, exactly like single-token
    vocabulary.  This pass supplies only the generic structural operation:
    longest matching phrase wins. Prepositions retain their existing contract;
    other entries must explicitly opt in, including their declared plurals.
    Fresh features ensure an idiomatic phrase cannot inherit a component's
    numeric value, unknown status, or obligations.
    """
    phrases = []
    for phrase, entry in reg.lexicon.items():
        if entry.lexical_phrase and "'" in phrase:
            from .tokenize import tokenize
            words = tuple(u.features["fold"] for u in tokenize(phrase, contractions=reg.contractions).units)
            if len(words) > 1:
                phrases.append((words, phrase, phrase, entry.number or "singular", entry))
        # A declared hyphenated lexeme is one dictionary word. Tokenization
        # keeps hyphen boundaries for productive measured compounds; merge
        # only this exact declared spelling, never its space-separated form.
        if "-" in phrase and " " not in phrase and not any(c.isdigit() for c in phrase):
            words = tuple(phrase.split("-"))
            if all(words):
                phrases.append((words, phrase, phrase, entry.number or "singular", entry))
        if " " not in phrase or not (
            "preposition" in entry.senses or entry.lexical_phrase
        ):
            continue
        phrases.append(
            (tuple(phrase.split()), phrase, phrase, entry.number or "singular", entry)
        )
        if entry.lexical_phrase:
            phrases.extend(
                (tuple(plural.split()), plural, phrase, "plural", entry)
                for plural in entry.plurals()
                if " " in plural
            )
    phrases.sort(key=lambda item: (-len(item[0]), item[1]))
    if not phrases:
        return reading

    i = 0
    while i < len(reading.units):
        matched = False
        for words, phrase, lemma, number, entry in phrases:
            end = i + len(words)
            if end > len(reading.units):
                continue
            span = reading.units[i:end]
            if tuple(unit.features.get("fold", "") for unit in span) != words:
                continue
            hyphenated = "-" in phrase and " " not in phrase
            if hyphenated != all(u.features.get("joined_left_by_hyphen") for u in span[1:]):
                continue
            merged = reading.new_unit(
                tuple(word for unit in span for word in unit.words),
                {},
            )
            reading.units[i:end] = [merged]
            changes: dict[str, object] = {
                "fold": phrase,
                "lemma": lemma,
                "senses": list(entry.senses),
                "number": number,
            }
            reading.record(
                "merge-multiword-preposition" if "preposition" in entry.senses
                else "merge-lexical-phrase",
                merged,
                changes,
                f"declared lexical phrase {phrase!r} has identity {lemma!r}",
            )
            matched = True
            break
        if not matched:
            i += 1
    return reading


def _merge(reading: Reading, i: int, head_features_from: Unit, kind: str, reason: str,
           extra: dict | None = None) -> Unit:
    units = reading.units
    a, b = units[i], units[i + 1]
    merged = reading.new_unit(a.words + b.words, dict(head_features_from.features))
    merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
    units[i : i + 2] = [merged]
    reading.record(kind, merged, extra or {}, reason)
    return merged


def _is_relative_period(unit: Unit, reg: Registry) -> bool:
    """Whether UNIT is a declared discourse-relative period.

    ``last month`` first reaches this pass as the ordinary qualified noun
    produced by ``merge-attribute``.  Its qualifier and head categories are
    the semantic evidence that it is an adjunct boundary; the kernel does not
    need to know either surface word.
    """

    if unit.sense() != "noun" or "value" in unit.features:
        return False
    qualifier = unit.features.get("qualifier")
    head = unit.features.get("lemma", unit.features.get("fold", ""))
    return (
        isinstance(qualifier, str)
        and reg.word_in_category(qualifier, "relative_period_attribute")
        and (
            reg.word_in_category(head, "duration_measure")
            or reg.word_in_category(head, "timeperiod")
        )
    )


def _nominal_attribute_postmodifier(reading: Reading, reg: Registry) -> bool:
    """Project a declared nominal-attribute PP onto its host's item identity.

    The pack supplies the preposition, attribute heads and compatibility.
    Counts and owners remain on the host; the attribute is not a new item.
    """
    units = reading.units
    for i, host in enumerate(units[:-2]):
        if host.sense() != "noun" or host.features.get("qualifier"):
            continue
        prep = units[i + 1]
        if not reg.word_in_category(prep.features.get("fold", ""), "nominal_attribute_preposition"):
            continue
        j = i + 2
        while j < len(units) and units[j].sense() == "article":
            j += 1
        if j == len(units):
            continue
        attribute = units[j]
        qualifier = attribute.features.get("qualifier")
        head = attribute.features.get("lemma", "")
        if (attribute.sense() != "noun" or not qualifier
                or not reg.word_in_category(head, "nominal_attribute_noun")
                or any(attribute.features.get(k) is not None for k in ("owner", "label", "value"))
                or not reg.attribute_applies_to(qualifier, head)
                or not reg.attribute_applies_to(qualifier, host.features.get("lemma", ""))):
            continue
        span = units[i:j + 1]
        merged = reading.new_unit(tuple(w for u in span for w in u.words), dict(host.features))
        units[i:j + 1] = [merged]
        reading.record("merge-nominal-attribute-pp", merged, {
            "fold": " ".join(u.features["fold"] for u in span),
            "qualifier": qualifier,
            "nominal_attribute": head,
            "attributes": list(host.features.get("attributes", [])) + [qualifier],
            "reference_qualifiers": tuple(sorted(set(reference_from_unit(host).qualifiers + (qualifier,)))),
        }, "declared nominal attribute restricts the host item")
        return True
    return False


def _nominal_pass(reading: Reading, reg: Registry) -> bool:
    units = reading.units
    # Declared abbreviated personal titles remain attached to their name.
    for i in range(len(units) - 2):
        title, period, name = units[i:i + 3]
        if (reg.word_in_category(title.features.get("fold", ""), "person_title")
                and period.surface == "." and name.sense() == "name"
                and len(name.features.get("lemma", "")) > 1):
            merged = reading.new_unit(title.words + period.words + name.words, dict(name.features))
            units[i:i + 3] = [merged]
            identity = title.features["fold"] + ". " + name.features["lemma"]
            reading.record("merge-personal-title", merged, {"fold": identity, "lemma": identity},
                           "a declared personal title qualifies this name")
            return True
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
                "merge-perfect", merged, {"number": a.features.get("number")},
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
                {"attributes": attrs, "owner": owner,
                 "owner_antecedent": a,
                 "owner_reference": reference_from_unit(a).to_dict()},
                f"{a.surface!r} owns {c.surface!r} — one owner-attributed noun",
            )
            return True
    # Explicit class indices precede member nouns: "level 4 students".
    # Unlike calendar years, the following noun does not claim this number.
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        if (a.sense() == "noun" and a.features.get("number") != "plural"
                and reg.word_in_category(a.features.get("lemma", ""), "numeric_index_head")
                and b.sense() == "value" and b.features.get("value_kind") == "count"
                and b.features["value"] > 0 and float(b.features["value"]).is_integer()):
            _merge(reading, i, a, "merge-class-index", "a trailing class index identifies rather than counts",
                   {"label": str(int(b.features["value"]))})
            return True
    # An uppercase letter after an ordered assessment and boundary marker is
    # a scale label, just as a letter after a container is an instance label.
    # Its ordering is NOT inferred; consumers can only compare equal bounds.
    for i in range(2, len(units)):
        head, prep, label = units[i-2:i+1]
        if (reg.word_in_category(head.features.get("lemma", ""), "ordered_assessment")
                and prep.sense() == "preposition"
                and len(label.surface) == 1 and label.surface.isupper()
                and label.surface.isalpha() and label.features.get("value_kind") != "scale_label"):
            reading.record("recognize-scale-label", label,
                           {"senses": ["noun"], "lemma": label.surface, "unknown": False,
                            "value_kind": "scale_label", "label": label.surface},
                           "uppercase index in an explicit ordered assessment")
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
                   {"attributes": attrs, "qualifier": qualifier,
                    "reference_qualifiers": tuple(sorted(set(
                        reference_from_unit(b).qualifiers + (qualifier,))))})
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
            and a.features.get("label") is None
            and not (a.features.get("owner") and b.features.get("owner"))
            # A qualified relative period is a temporal adjunct, not the
            # lexical head of the preceding object: ``toy cars last month``
            # must remain [toy cars] [last month], never one quantity of
            # months.  The two category declarations are pack-owned, so new
            # relative attributes and period nouns inherit the boundary.
            and not _is_relative_period(b, reg)
            # A quantity determiner starts a new NP, even after it has
            # merged with its head. Do not absorb the preceding PP object
            # into that phrase (destination NP + quantified content NP).
            and not any(
                reg.word_in_category(attribute, "quantity_determiner_attribute")
                for attribute in b.features.get("attributes", ())
            )
        ):
            attrs = list(b.features.get("attributes", []))
            attrs.append(a.features.get("lemma", a.features["fold"]))
            qualifier = a.features.get("qualifier") or a.features.get(
                "lemma", a.features["fold"]
            )
            _merge(reading, i, b, "merge-compound",
                   f"compound noun: {a.surface!r} modifies head {b.surface!r}",
                   {
                       # A possessive may have merged with the modifier
                       # first. Its scope is the complete compound; do not
                       # erase that identity when adopting the right head.
                       **{key: a.features[key] for key in
                          ("owner", "owner_reference", "owner_ref_uid", "owner_antecedent")
                          if key in a.features},
                       "attributes": attrs,
                       "qualifier": qualifier,
                       "reference_qualifiers": tuple(sorted(set(
                           reference_from_unit(b).qualifiers
                           + reference_from_unit(a).qualifiers
                           + (a.features.get("lemma", a.features["fold"]),)))),
                       # A source hyphen immediately before the nominal
                       # modifier is retained through this merge.  If a count
                       # sits to the left, the count pass can then represent
                       # "100-page book" as a book with a 100-page extent,
                       # rather than the false quantity "100 books".
                       "qualifier_joined_left_by_hyphen": bool(
                           a.features.get("joined_left_by_hyphen")
                       ),
                   })
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
    # possessive determiner + owned noun -> retain the ordinary two-unit
    # surface while attaching an owner identity to the noun. Unlike the
    # apostrophe-s merge above, these units must stay separate: declarative
    # rules legitimately inspect the determiner itself (her/his/their is a
    # grammatical premise), and collapsing it would silently break those
    # rule shapes. Category membership owns the word list; the kernel only
    # supplies the general governor-to-noun attachment.
    for i in range(len(units) - 1):
        determiner, owned = units[i], units[i + 1]
        determiner_word = determiner.features.get(
            "lemma", determiner.features.get("fold", "")
        )
        if (
            determiner.sense() == "pronoun"
            and reg.word_in_category(
                determiner_word, "possessive_determiner"
            )
            and owned.sense() == "noun"
            # "gives her 3 dollars" contains an object pronoun followed by
            # a counted NP, not a determiner+noun phrase. Condensation has
            # already merged the number and noun, so the count feature is a
            # vocabulary-free structural boundary between the two shapes.
            and owned.features.get("value_kind") != "count"
            and owned.features.get("owner_ref_uid") is None
            # A noun phrase with an apostrophe-s owner is already complete.
            # A preceding possessive determiner cannot replace that owner
            # ("their Mary's teacher"). Leave both structures visible so a
            # declarative phrase rule can reject the doubled ownership.
            and owned.features.get("owner") is None
        ):
            reading.record(
                "attach-possessive-determiner",
                owned,
                {
                    "owner": determiner_word,
                    "owner_ref_uid": determiner.uid,
                },
                f"{determiner.surface!r} owns {owned.surface!r} — "
                "the noun retains an explicit possessor",
            )
            return True
    return _nominal_attribute_postmodifier(reading, reg)


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
            if (
                b.features.get("qualifier") is not None
                and b.features.get("qualifier_joined_left_by_hyphen")
            ):
                _merge(
                    reading,
                    i,
                    b,
                    "merge-attributive-count",
                    f"count {a.surface!r} measures hyphenated modifier "
                    f"{b.features['qualifier']!r} on {b.surface!r}",
                    {
                        "value": a.features["value"],
                        "value_kind": "attributive_count",
                        "attributive_value": a.features["value"],
                        # The one hyphen boundary has now been consumed.  A
                        # further count to the left ("16 three-minute songs")
                        # quantifies the completed head instead of replacing
                        # its inner three-minute extent.
                        "qualifier_joined_left_by_hyphen": False,
                    },
                )
            else:
                _merge(reading, i, b, "merge-count",
                       f"count {a.surface!r} quantifies {b.surface!r} — one concept",
                       {"value": a.features["value"], "value_kind": "count"})
            return True
    return False


def _date_pass(reading: Reading, reg: Registry) -> bool:
    """Merge a SPELLED date -- "1 Jan 2024" -- into ONE unit carrying the same
    `date` value-kind that numbers.py gives an ISO date.

    A date is one thing; its surface form is the READER's problem, not the
    ask's. Without this the spelled form reached asks as three loose units, so
    every date-consuming ask needed a second shape and every date-consuming
    consumer a second branch -- date parsing duplicated into two layers that
    have no business knowing about calendars.

    Data-gated, never a word list: the month must be in `reg.month_numbers`
    (pack data), which also means a project whose packs declare no months
    cannot reach this pass at all.

    Structural gates, each load-bearing:
      - the month's SENSE must be a name or a noun. 'May' is a MODAL in the
        lexicon, and "you may 2024 ..." must never look like a date; excluding
        it costs the May-dated form and is the honest half of the trade.
      - the year must be written with FOUR digits, so "1 Jan 5" is not a date.
      - an IMPOSSIBLE date (31 Feb) does not merge, leaving the sentence
        unread rather than rolling over into March -- monotone-safe.
    """
    if not reg.month_numbers:
        return False
    units = reading.units
    for i in range(len(units) - 2):
        day, mon, year = units[i], units[i + 1], units[i + 2]
        if day.features.get("value_kind") != "count":
            continue
        if year.features.get("value_kind") != "count":
            continue
        if len(year.features.get("fold", "")) != 4:
            continue
        number = reg.month_numbers.get(mon.features.get("fold", ""))
        if number is None or mon.sense() not in ("name", "noun"):
            continue
        try:
            stamp = datetime.date(
                int(year.features["value"]), number, int(day.features["value"])
            )
        except (TypeError, ValueError):
            continue
        merged = reading.new_unit(day.words + mon.words + year.words, {})
        units[i : i + 3] = [merged]
        reading.record(
            "merge-date", merged,
            {
                "fold": f"{day.features['fold']} {mon.features['fold']} {year.features['fold']}",
                "senses": ["date"],
                "value_kind": "date",
                "components": stamp.isoformat(),
            },
            f"spelled date {stamp.isoformat()!r} is one unit",
        )
        return True
    return False


_FORMULA = re.compile(r"^(?:[A-Z][a-z]?\d*)+$")
_FORMULA_PART = re.compile(r"([A-Z][a-z]?)(\d*)")


def _formula_pass(reading: Reading, reg: Registry) -> bool:
    """Fuse a shredded chemical formula — "H2O" as H,2,O — back into ONE unit.

    THE TOKENIZER CANNOT DO THIS, and that is the whole reason the pass lives
    here. "CO2" and "MP3" are structurally identical: capitals then a digit.
    Only the ELEMENT TABLE separates a compound from an MP3 player, and the
    tokenizer has no registry. A tokenizer-level pattern was tried and it
    fused 'MP3', costing two GSM8K items.

    So the run is reassembled from the SURFACES and validated as a whole:
    every symbol must be a key in `reg.atomic_masses` (pack data), and at least
    two element groups must be present. A project declaring no elements cannot
    reach this pass at all.

    Only SENSELESS letter units join a run, which is what keeps element symbols
    that are also English words out of it: 'He', 'I', 'In', 'As', 'At', 'No'
    and 'Be' are all real symbols AND lexicon words, and the lexicon wins.

    The merged unit carries NO `value` — a formula is not a scalar, the same
    contract as a date or a coordinate tuple.
    """
    if not reg.atomic_masses:
        return False
    units = reading.units

    def is_digit(u) -> bool:
        return u.surface.isdigit() and u.features.get("value_kind") == "count"

    def eligible(u) -> bool:
        return is_digit(u) or u.surface.isalpha()

    for i in range(len(units)):
        if not eligible(units[i]) or is_digit(units[i]):
            continue  # a formula starts with a symbol, never a subscript
        for j in range(len(units), i, -1):        # longest run first
            run = units[i:j]
            if not all(eligible(u) for u in run):
                continue
            # THE LEXICON WINS, but only where there is nothing else to go on.
            # A LONE unit must be senseless, so 'He'/'I'/'As'/'At'/'No' stay
            # the English words they are. A MULTI-unit run must instead carry a
            # SUBSCRIPT — that digit is the structural evidence a formula is
            # meant, and it is what lets 'SO' in "H2SO4" be sulfur+oxygen even
            # though 'so' is a conjunction.
            if len(run) == 1:
                if run[0].senses():
                    continue
            elif not any(is_digit(u) for u in run):
                continue
            text = "".join(u.surface for u in run)
            if not _FORMULA.match(text):
                continue
            parts = _FORMULA_PART.findall(text)
            if len(parts) < 2 or not all(sym in reg.atomic_masses for sym, _ in parts):
                continue
            if len(run) == 1 and units[i].features.get("value_kind") == "formula":
                continue  # already merged
            merged = reading.new_unit(tuple(w for u in run for w in u.words), {})
            units[i:j] = [merged]
            reading.record(
                "merge-formula", merged,
                {
                    "fold": text.lower(),
                    "senses": ["formula"],
                    "value_kind": "formula",
                    "components": text,
                },
                f"chemical formula {text!r} is one unit",
            )
            return True
    return False


def condense(reading: Reading, reg: Registry) -> Reading:
    # joint fixpoint with nominal priority: a count merge can expose a new
    # nominal merge ("Tom's [3 apples]"), so alternate until neither fires
    while True:
        # dates FIRST: the count merge would otherwise attach the day to the
        # month noun ("1 March" -> one counted nominal) and the date would
        # never be seen
        if _date_pass(reading, reg):
            continue
        # formulas before the count merge, for the same reason as dates: the
        # count merge would otherwise claim the subscript ("2 O" -> one counted
        # nominal) and the formula would never be seen
        if _formula_pass(reading, reg):
            continue
        if _nominal_pass(reading, reg):
            continue
        if _count_pass(reading, reg):
            continue
        return reading
