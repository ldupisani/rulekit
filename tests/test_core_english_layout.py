"""Core vocabulary ownership follows language structure, not feature batches."""
from pathlib import Path

from ruamel.yaml import YAML

from rulekit.data.packs import load_pack
from rulekit.data.registry import compile_registry


ROOT = Path(__file__).resolve().parents[1] / "packs" / "core-english"


def test_shared_dictionary_has_one_alphabetized_owner():
    paths = sorted((ROOT / "lexicon").glob("*.yaml"))
    assert paths == [ROOT / "lexicon" / "core.yaml"]
    entries = YAML(typ="safe").load(paths[0].read_text())["entries"]
    assert list(entries) == sorted(entries)


def test_core_english_compiles_without_optional_domain_packs():
    compile_registry([load_pack(ROOT)])


def test_category_memberships_and_compatibility_live_with_definitions():
    documents = {p: YAML(typ="safe").load(p.read_text())
                 for p in (ROOT / "categories").glob("*.yaml")}
    owners = {}
    for path, document in documents.items():
        for category in document.get("categories", {}):
            assert category not in owners, category
            owners[category] = path
    for path, document in documents.items():
        for section in ("members", "attribute_compatibility", "modifier_host_compatibility",
                        "adverb_verb_compatibility", "measure_holder_compatibility",
                        "partitive_measure_compatibility"):
            for category in document.get(section, {}):
                expected = owners.get(category, ROOT / "categories" / "core.yaml")
                assert path == expected, (section, category, path, expected)
        if document.get("attrs"):
            if path != ROOT / "categories" / "attributes.yaml":
                classified = {word for words in document.get("members", {}).values() for word in words}
                assert set(document["attrs"]) <= classified, (path, set(document["attrs"]) - classified)


def test_noun_categories_do_not_repeat_a_lemma_and_its_declared_plural():
    registry = compile_registry([load_pack(ROOT)])
    for path in (ROOT / "categories").glob("*.yaml"):
        document = YAML(typ="safe").load(path.read_text())
        for category, words in document.get("members", {}).items():
            if registry.root_sense(category) != "noun":
                continue
            for word in words:
                lemma = registry.plural_to_singular.get(word, word)
                assert lemma == word or lemma not in words, (path, category, word, lemma)
