"""Lint must catch, statically, the conflicts difg could only find by
running the full benchmark diff."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_pack, load_packs
from rulekit.data.registry import compile_registry
from rulekit.lint.blast_radius import blast_radius
from rulekit.lint.overlap import lint_overlaps

REPO = Path(__file__).resolve().parent.parent

BASE_LEX = """format: rulekit/lexicon@1
entries:
  has: {senses: [verb], verb: {lemma: have}}
  than: {senses: [particle]}
  dog: {senses: [noun], plural: dogs}
  cat: {senses: [noun], plural: cats}
  apple: {senses: [noun], plural: apples}
"""

BASE_CATS = """format: rulekit/categories@1
categories:
  animal: {parent: noun}
  pet: {parent: animal}
members:
  animal: [dog, cat]
  pet: [dog]
"""

RULE_TMPL = """format: rulekit/rules@1
rules:
  - id: {rid}
    phase: read
    match:
      sentence:
        - {{slot: who, type: name}}
        - {{slot: verb, type: verb}}
        - {{slot: item, {gate}}}
    emits:
      - {{fact: quantity, entity: "{{who}}", measure: "{{item}}", value: 1.0}}
"""


def _mk(tmp_path, *docs):
    root = tmp_path / "p"
    root.mkdir()
    (root / "pack.yaml").write_text("format: rulekit/pack@1\nname: p\n")
    for i, doc in enumerate(docs):
        (root / f"doc{i}.yaml").write_text(doc)
    return compile_registry([load_pack(root)])


def test_equal_specificity_overlap_is_an_error(tmp_path):
    reg = _mk(
        tmp_path, BASE_LEX, BASE_CATS,
        RULE_TMPL.format(rid="r/a", gate="cat: animal"),
        RULE_TMPL.format(rid="r/b", gate="cat: animal"),
    )
    findings = lint_overlaps(reg)
    errors = [f for f in findings if f.level == "error"]
    assert errors and errors[0].code == "overlap-tie"
    assert "Witness" in errors[0].message


def test_narrower_gate_shadows_with_warning(tmp_path):
    reg = _mk(
        tmp_path, BASE_LEX, BASE_CATS,
        RULE_TMPL.format(rid="r/broad", gate="cat: animal"),
        RULE_TMPL.format(rid="r/narrow", gate="cat: pet"),
    )
    findings = lint_overlaps(reg)
    warnings = [f for f in findings if f.level == "warning"]
    # pet ⊂ animal: overlap exists but the narrow rule shadows — a warning,
    # never a silent ordering dependency
    assert warnings and "r/narrow" in warnings[0].message
    assert not [f for f in findings if f.level == "error"]


def test_disjoint_gates_do_not_overlap(tmp_path):
    reg = _mk(
        tmp_path, BASE_LEX, BASE_CATS,
        RULE_TMPL.format(rid="r/animal", gate="cat: animal"),
        RULE_TMPL.format(rid="r/number", gate="type: number"),
    )
    assert lint_overlaps(reg) == []


def test_pet_scenario_blast_radius(tmp_path):
    """The difg pet disaster, reproduced: registering a category must make
    every rule its members can newly reach ENUMERABLE before running."""
    reg = _mk(
        tmp_path, BASE_LEX, BASE_CATS,
        RULE_TMPL.format(rid="r/category-sum", gate="cat: animal"),
    )
    report = blast_radius(reg, "pet")
    # the pet member 'dog' satisfies the broader animal gate — the report
    # names the rule that a pet-membership change can newly activate
    assert "r/category-sum" in report.gating_rules
    assert report.member_words == ["dog"]
    report_animal = blast_radius(reg, "animal")
    assert "r/category-sum" in report_animal.gating_rules


def test_real_packs_lint_clean():
    packs = [REPO / "packs/core-english", REPO / "packs/arithmetic"]
    if (REPO / "packs/difg-mined").exists():
        packs.append(REPO / "packs/difg-mined")
    reg = compile_registry(load_packs(packs))
    errors = [f for f in lint_overlaps(reg) if f.level == "error"]
    assert errors == []
