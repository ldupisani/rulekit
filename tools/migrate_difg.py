"""One-off migration: mine difg's runtime tables into the difg-mined pack.

Import, don't parse: difg's reading.py executes all its table mutations at
import time (8 LEXICON update sites, every _register_category/_tag_word/
_tag_attr), so importing and dumping the final dicts captures the true
merged state, duplicate-shadowing fixups included.

Usage: uv run python tools/migrate_difg.py [/path/to/difg]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "packs" / "difg-mined"

# difg sense name -> rulekit sense name
SENSE_MAP = {"negation": "negator", "aggregator": "aggregate"}

# polarity is semantic knowledge difg kept implicit in which set was
# enumerated; made explicit data here
POLARITY = {"acquire": 1, "lose": -1, "higher": 1, "lower": -1}

# difg parented higher/lower at 'adjective' but every member carries the
# 'comparative' sense — difg derived COMPARATIVE_SIGN from the tag table
# directly, bypassing its own sense-link. Re-root where the members live.
PARENT_REMAP = {"higher": "comparative", "lower": "comparative"}

_yaml = YAML(typ="rt")
_yaml.default_flow_style = False
_yaml.width = 100


def _dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        _yaml.dump(data, fh)


def _core_english_words() -> tuple[set[str], set[str], set[str]]:
    """Words, categories, and context-synonym concepts core-english already
    defines — the migration must not shadow them."""
    from rulekit.data.packs import load_pack

    pack = load_pack(REPO / "packs" / "core-english")
    words = set(pack.lexicon)
    cats: set[str] = set()
    concepts: set[str] = set()
    for doc in pack.categories:
        cats.update(doc.categories)
        concepts.update(doc.context_synonyms)
    return words, cats, concepts


def main(difg_root: str) -> int:
    sys.path.insert(0, difg_root)
    import reasoning.reading as r  # noqa: PLC0415 — the point of the script

    core_words, core_cats, core_concepts = _core_english_words()
    report: list[str] = []

    # ---- lexicon -----------------------------------------------------------
    singular_plurals: dict[str, list[str]] = defaultdict(list)
    for plural, singular in sorted(r.PLURALS.items()):
        singular_plurals[singular].append(plural)

    entries: dict[str, dict] = {}
    skipped_core: list[str] = []
    skipped_plural_forms: list[str] = []
    for word in sorted(r.LEXICON):
        if word in core_words:
            skipped_core.append(word)
            continue
        senses = [SENSE_MAP.get(s, s) for s in r.LEXICON[word]]
        # a plural-form entry that adds nothing over its singular is noise —
        # the singular's `plural:` field already admits the surface
        singular = r.PLURALS.get(word)
        if singular is not None and senses == ["noun"]:
            singular_senses = r.LEXICON.get(singular, [])
            if "noun" in singular_senses or singular in core_words:
                skipped_plural_forms.append(word)
                continue
        entry: dict = {"senses": senses}
        if "noun" in senses and word in singular_plurals:
            plurals = sorted(singular_plurals[word])
            entry["plural"] = plurals[0] if len(plurals) == 1 else plurals
        if "verb" in senses and word in r.VERB_LEMMA:
            entry["verb"] = {"lemma": r.VERB_LEMMA[word]}
        entries[word] = entry
    report.append(
        f"lexicon: {len(entries)} migrated, {len(skipped_core)} already in "
        f"core-english, {len(skipped_plural_forms)} redundant plural-form entries dropped"
    )

    orphan_plurals = sorted(
        p for p, s in r.PLURALS.items() if s not in r.LEXICON and s not in core_words
    )
    if orphan_plurals:
        report.append(f"plurals skipped (singular not in any lexicon): {orphan_plurals}")

    buckets: dict[str, dict] = {"a-f": {}, "g-m": {}, "n-s": {}, "t-z": {}}
    for word, entry in entries.items():
        c = word[0].lower()
        key = "a-f" if c <= "f" else "g-m" if c <= "m" else "n-s" if c <= "s" else "t-z"
        buckets[key][word] = entry
    for key, bucket in buckets.items():
        _dump(OUT / "lexicon" / f"{key}.yaml", {"format": "rulekit/lexicon@1", "entries": bucket})

    # ---- categories / members / quarantine ---------------------------------
    all_words = core_words | set(entries)
    categories: dict[str, dict] = {}
    for cat, parent in sorted(r.CATEGORY_PARENTS.items()):
        if cat == "plural":  # built-in: derived from lexicon plurals
            continue
        if cat in core_cats:
            continue
        cdef: dict = {"parent": PARENT_REMAP.get(cat, parent)}
        if cat in r.CATEGORY_ANTONYMS:
            cdef["antonym"] = r.CATEGORY_ANTONYMS[cat]
        if cat in POLARITY:
            cdef["polarity"] = POLARITY[cat]
        categories[cat] = cdef

    def _root(cat: str) -> str:
        while True:
            if cat in PARENT_REMAP:
                cat = PARENT_REMAP[cat]
            elif cat in r.CATEGORY_PARENTS:
                cat = r.CATEGORY_PARENTS[cat]
            else:
                return cat

    def _senses_of(head: str) -> list[str]:
        entry = r.LEXICON.get(head) or r.LEXICON.get(r.PLURALS.get(head, head))
        return [SENSE_MAP.get(s, s) for s in (entry or [])]

    members: dict[str, list[str]] = defaultdict(list)
    quarantined: dict[str, dict] = {}
    dead_tags: list[str] = []
    for word, tags in sorted(r.WORD_CATEGORIES.items()):
        head = word.split()[0]
        in_lexicon = (
            head in all_words
            or r.PLURALS.get(head, head) in all_words
        )
        if not in_lexicon:
            quarantined[word] = {
                "tags": sorted(tags),
                "reason": "difg mask-known: category-tagged but deliberately "
                "withheld from LEXICON (holdout-poison avoidance). "
                "Re-admit only through the firewall.",
            }
            continue
        for tag in sorted(set(tags)):
            if tag == "plural":
                continue
            # difg's sense-link made a tag whose root sense the word lacks
            # silently DEAD at runtime; drop it explicitly instead
            if _root(tag) not in _senses_of(head):
                dead_tags.append(f"{word}:{tag} (no {_root(tag)!r} sense — inert in difg too)")
                continue
            members[tag].append(word)
    if dead_tags:
        report.append(f"dead tags dropped ({len(dead_tags)}): {dead_tags}")
    report.append(
        f"categories: {len(categories)} new (+{len(core_cats)} in core), "
        f"members over {len(members)} categories, {len(quarantined)} quarantined"
    )

    context_synonyms = {}
    for concept, (gate, forms) in sorted(r.CONTEXT_SYNONYMS.items()):
        if concept in core_concepts:
            report.append(f"context synonym {concept!r} kept from core-english (difg's skipped)")
            continue
        context_synonyms[concept] = {"gate": gate, "forms": sorted(forms)}

    attrs = {w: dict(sorted(t.items())) for w, t in sorted(r.WORD_ATTRS.items())}
    part_counts = dict(sorted(getattr(r, "PART_COUNTS", {}).items()))

    _dump(
        OUT / "categories" / "semantic.yaml",
        {
            "format": "rulekit/categories@1",
            "categories": categories,
            "members": {k: sorted(v) for k, v in sorted(members.items())},
            "context_synonyms": context_synonyms,
            "attrs": attrs,
            "part_counts": part_counts,
        },
    )
    _dump(
        OUT / "quarantine.yaml",
        {"format": "rulekit/quarantine@1", "words": quarantined},
    )

    # ---- conversions (one direction; inverse derived at compile) -----------
    seen: set[frozenset] = set()
    conversions = []
    for (a, b), factor in sorted(r.CONVERSIONS.items()):
        pair = frozenset((a, b))
        if pair in seen:
            continue
        seen.add(pair)
        if factor < 1:  # store the >1 direction for readability
            a, b, factor = b, a, 1.0 / factor
        conversions.append({"from": a, "to": b, "factor": factor})
    _dump(
        OUT / "conversions.yaml",
        {"format": "rulekit/conversions@1", "conversions": conversions},
    )
    report.append(f"conversions: {len(conversions)} pairs")

    # ---- numbers (only keys core-english doesn't already define) ------------
    from rulekit.data.packs import load_pack

    core_numbers = load_pack(REPO / "packs" / "core-english").numbers[0]
    numbers_doc: dict = {"format": "rulekit/numbers@1"}

    def _new_only(name: str, difg_table: dict, core_table: dict) -> dict:
        out = {}
        for k, v in sorted(difg_table.items()):
            if k in core_table:
                if str(core_table[k]) != str(v) and float_eq(core_table[k], v) is False:
                    report.append(f"numbers.{name}[{k!r}]: core={core_table[k]} difg={v} — core kept")
                continue
            out[k] = v
        return out

    def float_eq(a, b) -> bool | None:
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return None

    numbers_doc["numbers"] = _new_only("numbers", dict(r.NUMBERS), core_numbers.numbers)
    numbers_doc["scales"] = _new_only("scales", dict(r.SCALES), core_numbers.scales)
    difg_mult = {k: v for k, v in r.MULTIPLIERS.items() if k != "half"}
    if "half" in r.MULTIPLIERS:
        report.append("multipliers['half'] skipped — classified as a fraction in core-english")
    numbers_doc["multipliers"] = _new_only("multipliers", difg_mult, core_numbers.multipliers)
    fractions = {
        name: num / den
        for name, (num, den) in sorted(getattr(r, "FRACTION_MULTIPLIERS", {}).items())
    }
    numbers_doc["fractions"] = _new_only("fractions", fractions, core_numbers.fractions)
    numbers_doc["operators"] = _new_only("operators", dict(getattr(r, "OPERATORS", {})), core_numbers.operators)
    _dump(OUT / "numbers.yaml", numbers_doc)

    _dump(
        OUT / "pack.yaml",
        {
            "format": "rulekit/pack@1",
            "name": "difg-mined",
            "version": "0.1.0",
            "requires": ["core-english"],
            "description": "Lexical data mined from difg's runtime tables by "
            "tools/migrate_difg.py. Edit freely — this is data, not a build artifact.",
        },
    )

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "/Users/louis/Development/experiments/difg"
    sys.exit(main(root))
