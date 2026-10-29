"""Core ownership for broadly useful English preposition senses.

The ownership move is deliberately semantic-neutral for projects that already
loaded ``difg-mined``.  It makes the same grammar vocabulary available to a
core-only project without assigning a spatial, temporal, or circumstantial
role to any word merely because it is a preposition.
"""

from dataclasses import fields, replace
from pathlib import Path

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import analyze


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"

MOVED_PREPOSITIONS = {
    "about",
    "above",
    "across",
    "after",
    "against",
    "along",
    "among",
    "amongst",
    "around",
    "before",
    "below",
    "between",
    "by",
    "during",
    "except",
    "for",
    "including",
    "inside",
    "into",
    "near",
    "onto",
    "over",
    "past",
    "through",
    "throughout",
    "towards",
    "under",
    "until",
    "versus",
    "via",
    "within",
    "without",
}
REQUESTED_SINGLE_FORMS = {
    "aboard", "about", "above", "absent", "across", "after", "against",
    "along", "alongside", "amid", "amidst", "among", "amongst", "around",
    "as", "at", "atop", "bar", "barring", "before", "behind", "below",
    "beneath", "beside", "besides", "between", "beyond", "but", "by",
    "circa", "concerning", "counting", "despite", "down", "during",
    "effective", "except", "excepting", "excluding", "failing", "following",
    "for", "from", "in", "including", "inside", "into", "less", "like",
    "minus", "near", "next", "notwithstanding", "of", "off", "on", "onto",
    "opposite", "out", "outside", "over", "past", "pending", "per", "plus",
    "regarding", "respecting", "short", "since", "than", "through",
    "throughout", "to", "toward", "towards", "under", "underneath", "unlike",
    "until", "up", "upon", "versus", "vs", "via", "wanting", "with",
    "within", "without", "worth",
}
MULTIWORD_PREPOSITIONS = {
    "according to", "apart from", "because of", "but for", "due to", "instead of",
    "next to", "out of", "short of",
}
DEFERRED_OVERLOADED_FORMS = {
    "absent", "as", "bar", "but", "counting", "excluding", "less", "minus",
    "next", "out", "per", "plus", "short", "than", "up", "wanting", "worth",
}
CORE_PREPOSITIONS = (
    REQUESTED_SINGLE_FORMS - DEFERRED_OVERLOADED_FORMS
) | MULTIWORD_PREPOSITIONS | {"de"}


def test_general_preposition_inventory_is_owned_by_core_english() -> None:
    project = load_project(CURATED)
    core = next(pack for pack in project.packs if pack.name == "core-english")
    source = (ROOT / "packs/core-english/lexicon/core.yaml").resolve()

    assert {
        word for word, entry in core.lexicon.items() if "preposition" in entry.senses
    } == CORE_PREPOSITIONS
    assert all(
        "preposition" in core.lexicon[word].senses
        for word in CORE_PREPOSITIONS
    )
    assert {
        project.source_index.lexicon[word].path.resolve()
        for word in CORE_PREPOSITIONS
    } == {source}


def test_overloaded_forms_keep_their_established_sense_until_governed() -> None:
    project = load_project(GSM8K)

    assert set(project.registry.lexicon) >= REQUESTED_SINGLE_FORMS
    assert all(
        "preposition" not in project.registry.lexicon[word].senses
        for word in DEFERRED_OVERLOADED_FORMS
    )


def test_multiword_prepositions_merge_before_role_binding() -> None:
    project = load_project(CURATED)

    for phrase in sorted(MULTIWORD_PREPOSITIONS):
        reading = analyze(f"Tom worked {phrase} Mary.", project.registry)
        merged = [unit for unit in reading.units if unit.features.get("fold") == phrase]

        assert len(merged) == 1
        assert merged[0].surface.lower() == phrase
        assert merged[0].sense() == "preposition"
        assert len(merged[0].obligations()) == 2


def test_combined_pack_semantics_are_identical_to_legacy_ownership() -> None:
    project = load_project(GSM8K)
    core, arithmetic, physics, chemistry, mined = project.packs
    legacy_core = replace(
        core,
        lexicon={
            word: entry
            for word, entry in core.lexicon.items()
            if word not in MOVED_PREPOSITIONS
        },
        lexicon_sources={
            word: path
            for word, path in core.lexicon_sources.items()
            if word not in MOVED_PREPOSITIONS
        },
    )
    legacy_mined = replace(
        mined,
        lexicon={
            **mined.lexicon,
            **{word: core.lexicon[word] for word in MOVED_PREPOSITIONS},
        },
        lexicon_sources={
            **mined.lexicon_sources,
            **{
                word: core.lexicon_sources[word]
                for word in MOVED_PREPOSITIONS
            },
        },
    )
    legacy = compile_registry(
        [legacy_core, arithmetic, physics, chemistry, legacy_mined]
    )
    compared_fields = {
        field.name
        for field in fields(project.registry)
        if field.name != "fingerprint"
    }

    assert {
        name
        for name in compared_fields
        if getattr(project.registry, name) != getattr(legacy, name)
    } == set()
