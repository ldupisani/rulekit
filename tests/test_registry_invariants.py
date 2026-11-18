"""Planted-failure tests: every compile invariant must fail LOUDLY."""

import pytest

from rulekit.data.packs import LoadedPack, PackError, load_pack
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.schemas import CategoriesDoc, LexiconDoc, PackDoc


def _pack(tmp_path, name="t", **docs):
    root = tmp_path / name
    root.mkdir()
    (root / "pack.yaml").write_text(f"format: rulekit/pack@1\nname: {name}\n")
    for fname, content in docs.items():
        (root / f"{fname}.yaml").write_text(content)
    return root


def test_duplicate_lexicon_within_pack(tmp_path):
    root = _pack(
        tmp_path,
        a="format: rulekit/lexicon@1\nentries:\n  dog: {senses: [noun]}\n",
        b="format: rulekit/lexicon@1\nentries:\n  dog: {senses: [verb]}\n",
    )
    with pytest.raises(PackError, match="duplicate lexicon entry 'dog'"):
        load_pack(root)


def test_duplicate_lexicon_across_packs(tmp_path):
    r1 = _pack(tmp_path, "p1", a="format: rulekit/lexicon@1\nentries:\n  dog: {senses: [noun]}\n")
    r2 = _pack(tmp_path, "p2", a="format: rulekit/lexicon@1\nentries:\n  dog: {senses: [noun]}\n")
    with pytest.raises(CompileError, match="defined in both pack"):
        compile_registry([load_pack(r1), load_pack(r2)])


def test_category_without_root_sense(tmp_path):
    root = _pack(
        tmp_path,
        cats="format: rulekit/categories@1\ncategories:\n  weird: {parent: nowhere}\n",
    )
    with pytest.raises(CompileError, match="does not resolve to a root sense"):
        compile_registry([load_pack(root)])


def test_category_cycle(tmp_path):
    root = _pack(
        tmp_path,
        cats=(
            "format: rulekit/categories@1\ncategories:\n"
            "  a: {parent: b}\n  b: {parent: a}\n"
        ),
    )
    with pytest.raises(CompileError, match="cycle"):
        compile_registry([load_pack(root)])


def test_antonym_overlap(tmp_path):
    root = _pack(
        tmp_path,
        lex=(
            "format: rulekit/lexicon@1\nentries:\n"
            "  grab: {senses: [verb]}\n"
        ),
        cats=(
            "format: rulekit/categories@1\ncategories:\n"
            "  gain: {parent: verb, antonym: shed}\n"
            "  shed: {parent: verb}\n"
            "members:\n  gain: [grab]\n  shed: [grab]\n"
        ),
    )
    with pytest.raises(CompileError, match="share members"):
        compile_registry([load_pack(root)])


def test_member_missing_from_lexicon(tmp_path):
    root = _pack(
        tmp_path,
        cats=(
            "format: rulekit/categories@1\ncategories:\n"
            "  gain: {parent: verb}\nmembers:\n  gain: [ghostword]\n"
        ),
    )
    with pytest.raises(CompileError, match="not in the lexicon"):
        compile_registry([load_pack(root)])


def test_member_lacks_root_sense(tmp_path):
    root = _pack(
        tmp_path,
        lex="format: rulekit/lexicon@1\nentries:\n  table: {senses: [noun]}\n",
        cats=(
            "format: rulekit/categories@1\ncategories:\n"
            "  gain: {parent: verb}\nmembers:\n  gain: [table]\n"
        ),
    )
    with pytest.raises(CompileError, match="lacks the root sense"):
        compile_registry([load_pack(root)])


def test_partitive_witnesses_preserve_both_partial_binding_domains(tmp_path):
    root = _pack(
        tmp_path,
        lex="""format: rulekit/lexicon@1
entries:
  bag: {senses: [noun], plural: bags}
  box: {senses: [noun]}
  nut: {senses: [noun], plural: nuts}
  seed: {senses: [noun]}
  drop: {senses: [noun]}
""",
        cats="""format: rulekit/categories@1
categories:
  container: {parent: noun}
  carrier: {parent: container}
  solid: {parent: noun}
  liquid: {parent: noun}
  vessel: {parent: noun}
members:
  carrier: [bag, box]
  solid: [nut, seed]
  liquid: [drop]
partitive_measure_compatibility:
  container: [solid]
  vessel: [liquid]
""",
    )
    reg = compile_registry([load_pack(root)])
    witnesses = reg.partitive_witnesses
    assert len(witnesses) < len(reg.lexicon)
    for term in [*reg.lexicon, "bags", "nuts", "unknown"]:
        assert any(reg.partitive_applies_to(term, w) for w in witnesses) == any(
            reg.partitive_applies_to(term, w) for w in reg.lexicon
        )
        assert any(reg.partitive_applies_to(w, term) for w in witnesses) == any(
            reg.partitive_applies_to(w, term) for w in reg.lexicon
        )
    assert reg.partitive_applies_to("bags", "nuts")
    assert not any(reg.partitive_applies_to(w, "drop") for w in witnesses)


def test_aggregate_sense_can_root_a_semantic_subset(tmp_path):
    root = _pack(
        tmp_path,
        lex=(
            "format: rulekit/lexicon@1\nentries:\n"
            "  sumwise: {senses: [aggregate]}\n"
            "  meanwise: {senses: [aggregate]}\n"
        ),
        cats=(
            "format: rulekit/categories@1\ncategories:\n"
            "  sum_marker: {parent: aggregate}\n"
            "members:\n  sum_marker: [sumwise]\n"
        ),
    )

    registry = compile_registry([load_pack(root)])

    assert registry.root_sense("sum_marker") == "aggregate"
    assert registry.cat_members_deep("sum_marker") == ["sumwise"]
    assert not registry.word_in_category("meanwise", "sum_marker")


def test_antonym_same_polarity(tmp_path):
    root = _pack(
        tmp_path,
        cats=(
            "format: rulekit/categories@1\ncategories:\n"
            "  up: {parent: verb, antonym: down, polarity: 1}\n"
            "  down: {parent: verb, polarity: 1}\n"
        ),
    )
    with pytest.raises(CompileError, match="share polarity"):
        compile_registry([load_pack(root)])


def test_fingerprint_deterministic(tmp_path):
    r = _pack(tmp_path, lex="format: rulekit/lexicon@1\nentries:\n  dog: {senses: [noun]}\n")
    f1 = compile_registry([load_pack(r)]).fingerprint
    f2 = compile_registry([load_pack(r)]).fingerprint
    assert f1 == f2
