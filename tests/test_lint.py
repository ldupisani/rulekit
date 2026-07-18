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


# --- literal-token hygiene -------------------------------------------------
# Synthetic packs only. These checks exist because a token that can never match
# is invisible: the dev gate reports a clean 0 SOLVED (the same argument
# AskRule._anchor_is_first makes for failing at load).

LIT_LEX = """format: rulekit/lexicon@1
entries:
  the: {senses: [article]}
  a: {senses: [article]}
  an: {senses: [article]}
  sine: {senses: [noun]}
  sin: {senses: [noun]}
  some: {senses: [quantifier]}
  dog: {senses: [noun], plural: dogs}
"""


def _lit_ask(tokens):
    return (
        "format: rulekit/rules@1\nasks:\n"
        "  - id: ask/probe\n    match:\n      question:\n" + tokens +
        "    resolves: {consumer: c}\n"
    )


def _codes(reg):
    from rulekit.lint.checks import lint_checks
    return {f.code for f in lint_checks(reg)}


def test_a_bare_skippable_literal_cannot_even_be_LOADED(tmp_path):
    # see test_a_dead_literal_fails_at_LOAD below — the registry refuses it, so
    # there is no lint finding to make and no registry for lint to run on
    from rulekit.data.registry import CompileError

    with pytest.raises(CompileError):
        _mk(tmp_path, LIT_LEX, _lit_ask("        - {lit: the}\n"))


def test_consume_skipped_makes_it_live(tmp_path):
    reg = _mk(tmp_path, LIT_LEX,
              _lit_ask("        - {lit: the, consume_skipped: true}\n"))
    assert "dead-literal" not in _codes(reg)


def test_an_unlexicalised_word_is_not_dead(tmp_path):
    # a pack may legitimately match a surface form the lexicon does not know;
    # it simply has no sense to BE skippable
    reg = _mk(tmp_path, LIT_LEX, _lit_ask("        - {lit: blicket}\n"))
    assert "dead-literal" not in _codes(reg)





def test_a_partly_dead_alternation_loads_but_warns(tmp_path):
    # 'some' keeps the token live, so the registry builds — but 'the' can never
    # fire, silently narrowing the alternation. That is the case only lint can
    # catch, which is why this finding survives the load-time promotion.
    live = _mk(tmp_path, LIT_LEX, _lit_ask("        - {lit: [the, some]}\n"))
    assert "partially-dead-alternation" in _codes(live)


def test_an_alternation_with_EVERY_option_dead_is_refused_at_load(tmp_path):
    from rulekit.data.registry import CompileError

    with pytest.raises(CompileError):
        _mk(tmp_path, LIT_LEX, _lit_ask("        - {lit: [the, a]}\n"))


def test_a_same_sense_alternation_suggests_a_category(tmp_path):
    # 'sine'/'sin' are both nouns, so a category WOULD fit — the warning makes
    # the author state why it does not (here: `op` is per-word, and a category
    # cannot carry a per-member payload)
    reg = _mk(tmp_path, LIT_LEX, _lit_ask("        - {lit: [sine, sin]}\n"))
    assert "alternation-should-be-category" in _codes(reg)


def test_an_article_alternation_is_skeleton_not_a_missing_category(tmp_path):
    # a/an share the `article` sense, but that is ALLOMORPHY, not a class worth
    # naming — skippable senses are exempt or every a/an merge would nag
    reg = _mk(tmp_path, LIT_LEX,
              _lit_ask("        - {lit: [a, an], consume_skipped: true}\n"))
    assert "alternation-should-be-category" not in _codes(reg)


def test_a_dead_literal_fails_at_LOAD(tmp_path):
    # The lint check reports it; the registry REFUSES it. Same argument as
    # AskRule._anchor_is_first: a token that can never match makes a dead rule,
    # and a dev gate reports a dead rule as a clean 0 SOLVED — so the failure
    # has to happen where it cannot be read past.
    from rulekit.data.registry import CompileError

    with pytest.raises(CompileError) as exc:
        _mk(tmp_path, LIT_LEX, _lit_ask("        - {lit: the}\n"))
    assert "can never match" in str(exc.value)


def test_load_time_refusal_recurses_into_opt(tmp_path):
    from rulekit.data.registry import CompileError

    with pytest.raises(CompileError):
        _mk(tmp_path, LIT_LEX, _lit_ask(
            "        - opt:\n"
            "            - opt:\n"
            "                - {lit: the}\n"
            "        - {lit: dog}\n"))


def test_load_time_refusal_spares_a_live_or_claimed_literal(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    # consume_skipped makes it live...
    _mk(tmp_path / "a", LIT_LEX,
        _lit_ask("        - {lit: the, consume_skipped: true}\n"))
    # ...and an alternation is only dead if EVERY option is
    _mk(tmp_path / "b", LIT_LEX, _lit_ask("        - {lit: [the, some]}\n"))
