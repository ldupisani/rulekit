"""The reference-lookup tier (rulekit/reference@1 -> reg.reference -> consumer).

Synthetic only: the fixture pack is built in tmp_path with INVENTED entities —
no geography row, no benchmark string. What the real pack ships is data; what
these tests pin is the MACHINERY: compile invariants (loud, named errors),
determinism, and the decline honesty the docstrings promise.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import CompileError, compile_registry

REPO = Path(__file__).resolve().parent.parent

PACK_YAML = """\
format: rulekit/pack@1
name: testref
version: "0.0"
requires: [core-english]
description: synthetic reference fixture
"""

LEXICON_YAML = """\
format: rulekit/lexicon@1
entries:
  wingspan:
    senses:
    - noun
"""

CATEGORIES_YAML = """\
format: rulekit/categories@1
categories:
  reference_attribute: {parent: noun}
members:
  reference_attribute: [wingspan]
"""

ASKS_YAML = """\
format: rulekit/rules@1
rules: []
asks:
  - id: ask/testref-attribute
    match:
      question:
        - {lit: what}
        - {lit: is}
        - {slot: a, cat: reference_attribute}
        - {lit: of}
        - {slot: e, type: name}
    resolves:
      consumer: reference-lookup
      attribute: "{a}"
      entity: "{e}"
"""

REFERENCE_YAML = """\
format: rulekit/reference@1
tables:
  - name: dragons
    key: dragon
    attributes:
      wingspan: {}
    rows:
      - {dragon: Zamfir, wingspan: 12}
"""


def _write_pack(root: Path, reference_yaml: str = REFERENCE_YAML) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pack.yaml").write_text(PACK_YAML)
    (root / "lexicon.yaml").write_text(LEXICON_YAML)
    (root / "categories.yaml").write_text(CATEGORIES_YAML)
    (root / "asks.yaml").write_text(ASKS_YAML)
    (root / "reference.yaml").write_text(reference_yaml)
    return root


def _registry(tmp_path: Path, reference_yaml: str = REFERENCE_YAML):
    pack = _write_pack(tmp_path / "testref", reference_yaml)
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", pack])
    )


class TestCompile:
    def test_rows_flatten_to_frozen_mapping(self, tmp_path):
        reg = _registry(tmp_path)
        assert reg.reference[("zamfir", "wingspan", None)] == 12.0

    def test_two_compiles_are_identical(self, tmp_path):
        a = _registry(tmp_path / "a")
        b = _registry(tmp_path / "b")
        assert dict(a.reference) == dict(b.reference)
        assert list(a.reference) == list(b.reference)  # iteration order too

    def test_undeclared_attribute_errors_by_name(self, tmp_path):
        bad = REFERENCE_YAML.replace("wingspan: 12", "wingspan: 12, mood: grumpy")
        with pytest.raises(CompileError, match="undeclared attribute 'mood'"):
            _registry(tmp_path, bad)

    def test_missing_key_field_errors(self, tmp_path):
        bad = REFERENCE_YAML.replace("dragon: Zamfir, ", "")
        with pytest.raises(CompileError, match="lacks its key field"):
            _registry(tmp_path, bad)

    def test_bare_value_on_by_year_attribute_errors(self, tmp_path):
        bad = REFERENCE_YAML.replace("wingspan: {}", "wingspan: {by: year}")
        with pytest.raises(CompileError, match="by-year"):
            _registry(tmp_path, bad)


class TestLookup:
    def test_hit_commits_the_fact(self, tmp_path):
        from rulekit.kernel.engine import solve

        reg = _registry(tmp_path)
        r = solve("What is the wingspan of Zamfir?", reg, tracing=False)
        assert r.answer.kind == "number"
        assert r.answer.value == 12.0

    def test_unknown_entity_declines(self, tmp_path):
        from rulekit.kernel.engine import solve

        reg = _registry(tmp_path)
        r = solve("What is the wingspan of Borblat?", reg, tracing=False)
        assert r.answer.kind == "decline"
        assert "no reference fact" in r.answer.reason

    def test_empty_table_declines_everything(self, tmp_path):
        # the null control: same asks, same category, ZERO rows — nothing may
        # commit, proving commits come from the data and only the data
        from rulekit.kernel.engine import solve

        empty = REFERENCE_YAML.replace(
            "    rows:\n      - {dragon: Zamfir, wingspan: 12}", "    rows: []"
        )
        reg = _registry(tmp_path, empty)
        r = solve("What is the wingspan of Zamfir?", reg, tracing=False)
        assert r.answer.kind == "decline"
