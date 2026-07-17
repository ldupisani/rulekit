"""Sense annotation: lexicon lookup, plural inheritance, name detection.

Definitive dictionaries, never heuristics: a word absent from the lexicon is
marked unknown (a reportable deficiency), never guessed — with two safe
exceptions that are structural, not lexical: capitalized non-initial tokens
read as names, and value-carrying tokens already annotated by numbers.py.
"""

from __future__ import annotations

from ..data.registry import Registry
from .model import Reading

PUNCT = {".", ",", "!", "?", ";", ":"}


def _previous_word_unit(reading: Reading, unit) -> object | None:
    prev = None
    for u in reading.units:
        if u is unit:
            return prev
        if u.surface not in PUNCT:
            prev = u
    return prev


def annotate_senses(reading: Reading, reg: Registry) -> Reading:
    for unit in reading.units:
        fold = unit.features.get("fold", "")
        surface = unit.surface

        if surface in PUNCT:
            reading.record("annotate-sense", unit, {"senses": ["punct"]}, "punctuation")
            continue
        # The `or` is ADDITIVE, not a widening of the shared gate: every other
        # number annotation sets `value` and `value_kind` together, so this
        # cannot pull any pre-existing unit down a new path. A coordinate tuple
        # is the one annotation with a kind but no scalar (numbers.py _TUPLE).
        if "value" in unit.features or unit.features.get("value_kind") == "tuple":
            # a currency amount IS a counted noun ("$5" ≡ "5 dollars"); its
            # measure word comes from the currencies map (data, not code)
            if unit.features.get("currency") and "$" in reg.currencies:
                reading.record(
                    "annotate-sense", unit,
                    {
                        "senses": ["noun"],
                        "lemma": reg.currencies["$"],
                        "number": "plural",
                    },
                    f"currency amount {unit.surface!r} reads as a counted "
                    f"{reg.currencies['$']!r} noun",
                )
                continue
            kind = unit.features["value_kind"]
            sense = {
                "count": "value", "multiplier": "multiplier", "fraction": "fraction",
                "ordinal": "ordinal",
                # a coordinate tuple ("(3,4)" -> numbers.py's _TUPLE): its own
                # sense, so it is never an unknown word and never a `value` (it
                # carries no scalar and demands no `quantifies` obligation).
                "tuple": "tuple",
            }[kind]
            reading.record("annotate-sense", unit, {"senses": [sense]}, f"value token ({kind})")
            continue

        # A noun's number-forms share ONE identity (difg's _noun_lemma): the
        # plural mapping canonicalizes the lemma even when the plural surface
        # has its own lexicon entry.
        entry = reg.lexicon.get(fold)
        number = "singular"
        singular = fold
        if fold in reg.plural_to_singular:
            singular = reg.plural_to_singular[fold]
            number = "plural"
            if entry is None:
                entry = reg.lexicon.get(singular)

        # A capitalized mid-sentence word WITHOUT a preceding article is a
        # name even when the lowercase word is known ("Is Rose a teacher?"
        # vs "the rose wilted") — proper nouns don't take articles.
        # EXCEPT a `timeperiod` category word (mining candidate time-
        # period-qualified-events: 'Monday', 'Tuesday', ... — always
        # capitalized by English convention, and never a person's name in
        # this corpus, unlike genuinely name-ambiguous words such as
        # 'Rose'). Without this exemption every weekday adjunct sentence
        # ("On Monday, Sam sold...") misread its weekday as a second bare
        # NAME, which then polluted `_discourse_candidates` (document.py)
        # with a spurious second antecedent and broke cross-sentence
        # pronoun binding for the following sentence's "he"/"she" — not
        # merely a wrong sense for the weekday word itself. Structural
        # (category membership), never a literal word list.
        if (
            entry is not None
            and surface[:1].isupper()
            and surface[1:].islower()
            and unit.words[0].index > 0
            and not reg.word_in_category(fold, "timeperiod")
            # a QUANTIFIER's capital is never a naming signal: an embedded
            # clause keeps its sentence-initial capital ("Is it true that No
            # plants are mushrooms?" — the FOLIO wrapper construction), and a
            # name-annotated 'No' binds ground-ask subject slots while the
            # quantifier meaning vanishes. Same structural shape as the
            # timeperiod exemption above; sense reference, never a word list.
            # Measured trade: quantifier-headed REAL names are one item across
            # all seven DEV corpora ('All Goods Available store', declines
            # before and after) vs 78 wrapper-capitalized quantifier
            # conclusions in folio dev-train alone.
            and "quantifier" not in entry.senses
        ):
            prev = _previous_word_unit(reading, unit)
            prev_fold = prev.features.get("fold") if prev is not None else None
            if reg.lexicon.get(prev_fold) is None or "article" not in reg.lexicon[prev_fold].senses:
                reading.record(
                    "annotate-sense", unit,
                    {"senses": ["name"], "lemma": fold, "number": "singular"},
                    "capitalized mid-sentence without article → name",
                )
                continue

        if entry is not None:
            if entry.number is not None:
                number = entry.number
            changes: dict = {"senses": list(entry.senses), "number": number}
            if singular != fold and "noun" in entry.senses:
                changes["lemma"] = singular
            elif "verb" in entry.senses:
                changes["lemma"] = reg.verb_lemmas.get(fold, fold)
            else:
                changes["lemma"] = singular if singular != fold else fold
            reading.record("annotate-sense", unit, changes, f"lexicon entry {fold!r}")
            continue

        # A capitalized word that is not sentence-initial reads as a name.
        # Sentence-initial capitals are names only if also absent as a common
        # word — which they are here (no lexicon entry), so treat as name too,
        # but keep the ambiguity note for the trace.
        if surface[:1].isupper() and surface[1:].islower():
            reason = (
                "capitalized mid-sentence → name"
                if unit.words[0].index > 0
                else "sentence-initial capital, not in lexicon → name"
            )
            reading.record(
                "annotate-sense", unit,
                {"senses": ["name"], "lemma": fold, "number": "singular"},
                reason,
            )
            continue

        reading.record("annotate-sense", unit, {"unknown": True, "senses": []},
                       f"{surface!r} is not in the lexicon")
    return reading
