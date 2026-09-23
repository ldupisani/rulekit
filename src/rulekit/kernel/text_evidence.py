"""Literal text and explicit component structure supply ordinary quantities."""

from unicodedata import normalize

from .evaluate import evaluate
from .model import Provenance, Quantity, TextPrefixSplit, TextValue
from .reference_identity import flat_reference


def _alphabetic_component(text: str) -> bool:
    """Letters joined by single ASCII, Unicode or nonbreaking hyphens.

    Hyphens join components, unlike clause dashes or arithmetic minus signs.
    Empty components reject leading, trailing and doubled separators.
    """
    parts = text.replace("\u2010", "-").replace("\u2011", "-").split("-")
    return all(part.isalpha() for part in parts)


def prefix_remainder(text: str, prefix: str, layout: str = "two-part") -> str | None:
    """Extract a declared component, without any name or prefix vocabulary.

    `capitalized-tail` licenses uppercase-initial intervening parts, then
    zero or more lowercase-initial parts attached to one uppercase-initial
    final part. It is an explicit orthographic convention, not a universal
    interpretation of personal names. Original internal spacing is retained.
    """
    text = normalize("NFC", text)
    words = text.split()
    prefix_words = normalize("NFC", prefix).split()
    if (len(words) < 2 or len(prefix_words) != 1
            or words[0].casefold() != prefix_words[0].casefold()
            or not all(_alphabetic_component(word) for word in words)):
        return None
    if layout == "two-part":
        return words[1] if len(words) == 2 else None
    if layout != "capitalized-tail":
        return None
    if not words[0][0].isupper() or not words[-1][0].isupper():
        return None
    start = len(words) - 1
    while start > 1 and words[start - 1][0].islower():
        start -= 1
    if not all(word[0].isupper() for word in words[1:start]):
        return None
    # Split only the discarded prefix, preserving spelling/separators in the
    # retained component (unlike joining whitespace-normalized tokens).
    return text.split(maxsplit=start)[-1].rstrip()


def text_evidence(store, reg, log):
    out = []
    values = store.by_kind(TextValue)
    if not values:
        return out
    for split in store.by_kind(TextPrefixSplit):
        whole_ref = flat_reference(split.whole, split.owner)
        candidates = [v for v in values if v.entity_ref == whole_ref
                      and v.measure == split.measure]
        if len(candidates) != 1:
            continue
        remainder = prefix_remainder(candidates[0].text, split.prefix, split.layout)
        if remainder is None:
            continue
        out.append(TextValue(
            Provenance("synth/text-prefix-split", split.provenance.sentence),
            split.part, remainder, split.measure, split.owner,
        ))
    for value in values:
        if (not value.entity_ref.resolved
                or not reg.word_in_category(value.measure, "text_letter_measure")):
            continue
        text = normalize("NFC", value.text)
        count = sum(character.isalpha() for character in text)
        if count == 0:
            continue
        out.append(Quantity(
            Provenance("synth/text-letter-count", value.provenance.sentence),
            value.entity, value.measure,
            evaluate("n", {"n": float(count)}, log, source="text-letter-count"),
            owner=value.owner, entity_ref=value.entity_ref,
        ))
    return out
