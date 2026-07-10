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
        if "value" in unit.features:
            kind = unit.features["value_kind"]
            sense = {"count": "value", "multiplier": "multiplier", "fraction": "fraction"}[kind]
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
        if (
            entry is not None
            and surface[:1].isupper()
            and surface[1:].islower()
            and unit.words[0].index > 0
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
