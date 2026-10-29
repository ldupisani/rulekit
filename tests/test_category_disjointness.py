"""Declared category separation is symmetric, inherited and checked at load."""

from pathlib import Path

import pytest

from rulekit.data.packs import LoadedPack
from rulekit.data.project import load_project
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.schemas import CategoriesDoc, LexiconEntry, PackDoc


def pack(name, categories=None, members=None, words=()):
    return LoadedPack(
        name=name, root=Path(name), manifest=PackDoc(format="rulekit/pack@1", name=name),
        lexicon={w: LexiconEntry(senses=["noun"], plural=w + "s") for w in words},
        categories=[CategoriesDoc(format="rulekit/categories@1",
                                  categories=categories or {}, members=members or {})],
        fingerprint=name,
    )


def taxonomy():
    return pack("families", {
        "living": {"parent": "noun", "disjoint_with": ["devices"]},
        "people": {"parent": "living"},
        "mentors": {"parent": "people"},
        "empty_living": {"parent": "living"},
        "devices": {"parent": "noun"},
        "printers": {"parent": "devices"},
        "empty_devices": {"parent": "devices"},
        "tools": {"parent": "noun"},
        "actors": {"parent": "noun", "includes": ["people", "devices"]},
    }, {"mentors": ["mentor"], "printers": ["printer"], "tools": ["hammer"]},
        ("mentor", "printer", "hammer"))


def test_separation_is_symmetric_and_reaches_members_subclasses_and_plurals():
    registry = compile_registry([taxonomy()])
    for left, right in [("living", "devices"), ("people", "printers"),
                        ("mentors", "devices"), ("mentor", "printer"),
                        ("mentors", "printers"), ("mentor", "printers"),
                        ("empty_living", "empty_devices")]:
        assert registry.category_terms_disjoint(left, right)
        assert registry.category_terms_disjoint(right, left)
    with pytest.raises(TypeError):
        registry.category_disjoint["living"] = ()


def test_absent_membership_siblings_and_partial_overlap_are_not_separation():
    registry = compile_registry([taxonomy()])
    for left, right in [("people", "tools"), ("mentor", "hammer"),
                        ("actors", "devices"), ("actors", "living"),
                        ("living", "living"), ("living", "mentor"),
                        ("missing", "devices")]:
        assert not registry.category_terms_disjoint(left, right)
        assert not registry.category_terms_disjoint(right, left)


def test_separation_reaches_included_families_without_closing_their_membership():
    base = taxonomy()
    extra = pack("extra", {
        "origins": {"parent": "noun", "includes": ["people"], "disjoint_with": ["tools"]},
    }, {"mentors": ["tutor"]}, ("tutor",))
    a = compile_registry([base, extra])
    b = compile_registry([extra, base])
    assert a.category_disjoint == b.category_disjoint
    assert a.category_terms_disjoint("tutor", "hammer")
    assert a.category_terms_disjoint("people", "tools")
    assert not a.category_terms_disjoint("devices", "tools")


@pytest.mark.parametrize("categories,error", [
    ({"a": {"parent": "noun", "disjoint_with": ["missing"]}}, "unknown category"),
    ({"a": {"parent": "noun", "disjoint_with": ["noun"]}}, "unknown category"),
    ({"a": {"parent": "noun", "disjoint_with": ["b"]},
      "b": {"parent": "verb"}}, "noun-rooted"),
    ({"a": {"parent": "verb", "disjoint_with": ["b"]},
      "b": {"parent": "noun"}}, "noun-rooted"),
    ({"a": {"parent": "noun", "disjoint_with": ["a"]}}, "overlapping families"),
    ({"a": {"parent": "noun", "disjoint_with": ["b"]},
      "b": {"parent": "a"}}, "overlapping families"),
    ({"a": {"parent": "noun", "includes": ["b"], "disjoint_with": ["b"]},
      "b": {"parent": "noun"}}, "overlapping families"),
    ({"a": {"parent": "noun", "includes": ["c"], "disjoint_with": ["b"]},
      "b": {"parent": "noun", "includes": ["c"]},
      "c": {"parent": "noun"}}, "overlapping families"),
])
def test_invalid_or_contradictory_category_declarations_fail(categories, error):
    with pytest.raises(CompileError, match=error):
        compile_registry([pack("invalid", categories)])


def test_later_members_cannot_contradict_declared_separation():
    extension = pack("conflict", members={"printers": ["mentor"]})
    with pytest.raises(CompileError, match="share members"):
        compile_registry([taxonomy(), extension])


def test_number_variants_cannot_hide_conflicting_memberships():
    extension = pack("plural-conflict", members={"printers": ["mentors"]})
    with pytest.raises(CompileError, match="share members"):
        compile_registry([taxonomy(), extension])


def test_lexical_category_labels_cannot_bridge_separated_families():
    base = pack("labels", {
        "a": {"parent": "noun", "disjoint_with": ["b"]},
        "b": {"parent": "noun"},
    }, {"b": ["a"]}, ("a",))
    with pytest.raises(CompileError, match="share members"):
        compile_registry([base])


def test_core_classification_does_not_admit_quarantined_vocabulary():
    registry = load_project(Path("projects/curated")).registry
    assert registry.word_in_category("apple", "fruit")
    assert registry.category_terms_disjoint("flower", "apple")
    assert registry.category_terms_disjoint("animal", "rose")
    assert "fruit" not in registry.lexicon
    assert "fruits" not in registry.lexicon
