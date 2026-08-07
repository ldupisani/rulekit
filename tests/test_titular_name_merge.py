"""The titular name merge: NAME + partitive + NAME condenses to ONE name
("Salmon of Doubt", "University of Edinburgh", "House of Commons").

English titles embed 'of' (the `partitive` category's word — pack data;
condense.py references only the category) between capitalized parts, and
pairwise merging can never see across it — every single-unit name slot then
fails on a titular subject and the sentence goes unread (on logic prose,
straight into the fragment veto). The left part may be a NAME or a
mid-sentence CAPITALIZED known word (the pairwise "Tall Tuna" signal:
'Salmon' is a lexicon fish); the right part must be a name; head features
come from the name side. Sentence-initial capitalized known words never
merge — "Members of Pappy's have starred" is a plural description, not a
title.

All synthetic — never a corpus string.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            ROOT / "packs/difg-mined",
            ROOT / "packs/logic",
        ])
    )


def _verdict(text, reg):
    r = engine.solve(text, reg, tracing=False)
    return r.answer.value if r.answer.kind == "verdict" else r.answer.kind


def _atom_entities(text, reg):
    r = engine.solve(text, reg, tracing=False)
    return {f.entity for f in r.store.by_kind(Atom)}


def test_name_of_name_merges_and_echoes(logic_reg):
    assert _verdict(
        "Rex of Zar is a blicket. Is it true that Rex of Zar is a blicket?",
        logic_reg,
    ) == "yes"


def test_capitalized_known_noun_left_part_merges(logic_reg):
    # 'Dog' is a lexicon word — a known word never falls back to the name
    # sense, so a name-only gate would skip every title whose first word
    # the lexicon knows ("The Salmon of Doubt")
    assert "dog of zar" in _atom_entities(
        "The Dog of Zar is a blicket.", logic_reg
    )


def test_merged_title_binds_the_name_slot_not_its_noun_head(logic_reg):
    # head features come from the NAME side: were the left noun's sense
    # inherited, the title could bind no name slot and the sentence would
    # stay unread (measured live before the fix — the fragment veto held)
    assert _verdict(
        "The Dog of Zar is a blicket. Is it true that The Dog of Zar is a blicket?",
        logic_reg,
    ) == "yes"


def test_sentence_initial_known_noun_never_merges(logic_reg):
    # "Members of Zar are ..." is a plural description, not a title —
    # sentence-initial capitalization is weak evidence and stays unmerged
    assert "member of zar" not in _atom_entities(
        "Members of Zar are blickets.", logic_reg
    )
    assert "members of zar" not in _atom_entities(
        "Members of Zar are blickets.", logic_reg
    )


def test_quantifier_and_partitive_arithmetic_never_merge(logic_reg):
    # 'All of Emily', 'half of the apples' — the left unit is quantifier/
    # value/article-sensed, never a name or capitalized known noun; the
    # partitive reading is byte-identical by construction
    ents = _atom_entities("All of Emily is happy.", logic_reg)
    assert not any("of emily" in e for e in ents)


def test_titular_subject_lifts_the_fragment_veto_by_reading(logic_reg):
    # the composition buyer's shape: the titular sentence carries 'and',
    # and before the merge NO copular rule could read it — the item was
    # fragment-vetoed with the whole derivation already in the store
    assert _verdict(
        "Kelvin Ban is an author who created the collection called The Tome of Zar. "
        "The Tome of Zar is about gleebs and zorps. "
        "All authors are writers. "
        "Is it true that Kelvin Ban is a writer?",
        logic_reg,
    ) == "yes"


def test_titular_composition_null_control(logic_reg):
    got = _verdict(
        "Kelvin Ban is an author who created the collection called The Tome of Zar. "
        "The Tome of Zar is about gleebs and zorps. "
        "All authors are writers. "
        "Is it true that Kelvin Ban is a plumber?",
        logic_reg,
    )
    assert got in ("undetermined", "decline")
