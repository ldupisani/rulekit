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


def test_slot_category_exclusion_makes_literal_sibling_disjoint(tmp_path):
    lexicon = BASE_LEX + "  there: {senses: [existential]}\n"
    broad = """format: rulekit/rules@1
rules:
  - id: r/scoped
    phase: read
    match:
      sentence:
        - {slot: subject, type: word}
        - {slot: verb, type: verb}
    where:
      - slot_not_category: {slot: subject, cat: existential}
    emits:
      - {fact: atom, entity: "{subject}", pred: "{verb}"}
"""
    existential = """format: rulekit/rules@1
rules:
  - id: r/existential
    phase: read
    match:
      sentence:
        - {lit: there}
        - {slot: verb, type: verb}
    emits:
      - {fact: atom, entity: world, pred: "{verb}"}
"""
    reg = _mk(tmp_path, lexicon, broad, existential)

    assert lint_overlaps(reg) == []


def test_counted_qualifier_requires_a_noun_rooted_category(tmp_path):
    from rulekit.data.registry import CompileError

    categories = """format: rulekit/categories@1
categories:
  action: {parent: verb}
members:
  action: [has]
"""
    rule = """format: rulekit/rules@1
rules:
  - id: r/impossible-counted-verb
    phase: read
    match:
      sentence:
        - {slot: action, cat: action, counted: true}
    emits:
      - {fact: atom, entity: sample, pred: "{action}"}
"""

    with pytest.raises(CompileError, match="non-noun category 'action'"):
        _mk(tmp_path, BASE_LEX, categories, rule)


def test_counted_category_cannot_overlap_a_single_word_literal(tmp_path):
    counted = """format: rulekit/rules@1
rules:
  - id: r/counted-animal
    phase: read
    match:
      sentence:
        - {slot: item, cat: animal, counted: true}
    emits:
      - {fact: atom, entity: sample, pred: "{item}"}
"""
    literal = """format: rulekit/rules@1
rules:
  - id: r/literal-dog
    phase: read
    match:
      sentence:
        - {lit: dog}
    emits:
      - {fact: atom, entity: sample, pred: dog}
"""
    reg = _mk(tmp_path, BASE_LEX, BASE_CATS, counted, literal)

    assert lint_overlaps(reg) == []


@pytest.mark.parametrize('first, second, overlaps', [
    ('cat: animal, counted: true', 'cat: animal, uncounted: true', False),
    ('type: counted', 'cat: animal, uncounted: true', False),
    ('cat: animal, qualified: true, attributive_counted: true', 'cat: animal, uncounted: true', False),
    ('cat: animal, counted: true', 'cat: animal, qualified: true, attributive_counted: true', False),
    ('type: counted', 'cat: animal, qualified: true, attributive_counted: true', False),
    ('cat: animal, counted: true', 'cat: animal', True),
    ('cat: animal, uncounted: true', 'cat: animal', True),
    ('cat: animal, qualified: true, attributive_counted: true', 'cat: animal', True),
    ('cat: animal, counted: true', 'cat: animal, counted: true', True),
    ('cat: animal, qualified: true, attributive_counted: true', 'cat: animal, qualified: true, attributive_counted: true', True),
])
def test_numeric_nominal_structures_keep_their_runtime_disjointness(tmp_path, first, second, overlaps):
    reg = _mk(tmp_path, BASE_LEX, BASE_CATS,
              RULE_TMPL.format(rid='r/first', gate=first),
              RULE_TMPL.format(rid='r/second', gate=second))
    assert bool(lint_overlaps(reg)) == overlaps


def test_possessed_qualifier_requires_a_noun_rooted_category(tmp_path):
    from rulekit.data.registry import CompileError

    categories = """format: rulekit/categories@1
categories:
  action: {parent: verb}
members:
  action: [has]
"""
    rule = """format: rulekit/rules@1
rules:
  - id: r/impossible-possessed-verb
    phase: read
    match:
      sentence:
        - {slot: action, cat: action, possessed: true}
    emits:
      - {fact: atom, entity: sample, pred: "{action}"}
"""

    with pytest.raises(CompileError, match="non-noun category 'action'"):
        _mk(tmp_path, BASE_LEX, categories, rule)


def test_possessed_category_cannot_overlap_a_single_word_literal(tmp_path):
    possessed = """format: rulekit/rules@1
rules:
  - id: r/possessed-animal
    phase: read
    match:
      sentence:
        - {slot: item, cat: animal, possessed: true}
    emits:
      - {fact: atom, entity: sample, pred: "{item.owner}"}
"""
    literal = """format: rulekit/rules@1
rules:
  - id: r/literal-dog
    phase: read
    match:
      sentence:
        - {lit: dog}
    emits:
      - {fact: atom, entity: sample, pred: dog}
"""
    reg = _mk(tmp_path, BASE_LEX, BASE_CATS, possessed, literal)

    assert lint_overlaps(reg) == []


def test_opposed_number_qualifiers_are_statically_disjoint(tmp_path):
    singular = """format: rulekit/rules@1
rules:
  - id: r/singular-owned-animal
    phase: read
    match:
      sentence:
        - {slot: item, cat: animal, possessed: true, number: singular}
    emits:
      - {fact: atom, entity: sample, pred: "{item.owner}"}
"""
    plural = """format: rulekit/rules@1
rules:
  - id: r/plural-owned-animal
    phase: read
    match:
      sentence:
        - {slot: item, cat: animal, possessed: true, number: plural}
    emits:
      - {fact: atom, entity: sample, pred: "{item.owner}"}
"""
    reg = _mk(tmp_path, BASE_LEX, BASE_CATS, singular, plural)

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


# --- the nonstate_verb blind spot ------------------------------------------
# `_TYPE_SENSES` had no `nonstate_verb` entry, so the type fell through to
# None = "matches anything" and every copular `{lit: is}` rule was reported
# as colliding with a `nonstate_verb` slot — a collision patterns._slot_ok
# makes impossible ('is' is state-category on its fold, 'be' on its lemma).
# All 8 projects/scratch lint errors were this one false positive.

NSV_LEX = """format: rulekit/lexicon@1
entries:
  is: {senses: [verb], verb: {lemma: be}}
  was: {senses: [verb], verb: {lemma: be}}
  be: {senses: [verb]}
  eats: {senses: [verb], verb: {lemma: eat}}
  dog: {senses: [noun], plural: dogs}
  cat: {senses: [noun], plural: cats}
"""

NSV_CATS = """format: rulekit/categories@1
categories:
  animal: {parent: noun}
  state: {parent: verb}
members:
  animal: [dog, cat]
  state: [be, was]
"""

NSV_RULE_TMPL = """format: rulekit/rules@1
rules:
  - id: {rid}
    phase: read
    match:
      sentence:
        - {{slot: who, type: name}}
        - {mid}
        - {{slot: item, cat: animal}}
    emits:
      - {{fact: quantity, entity: "{{who}}", measure: "{{item}}", value: 1.0}}
"""


def _nsv_overlaps(tmp_path, lit_mid):
    reg = _mk(
        tmp_path, NSV_LEX, NSV_CATS,
        NSV_RULE_TMPL.format(rid="r/verbal", mid="{slot: v, type: nonstate_verb}"),
        NSV_RULE_TMPL.format(rid="r/literal", mid=lit_mid),
    )
    return lint_overlaps(reg)


def test_a_copular_lit_cannot_collide_with_a_nonstate_verb_slot(tmp_path):
    # the lemma path: 'is' is not a state MEMBER (only 'be' is) — the check
    # must look the lemma up, exactly as patterns._slot_ok does
    assert _nsv_overlaps(tmp_path, "{lit: is}") == []


def test_a_state_surface_lit_cannot_collide_either(tmp_path):
    # the fold path: 'was' is a state member directly
    assert _nsv_overlaps(tmp_path, "{lit: was}") == []


def test_an_event_verb_lit_still_collides(tmp_path):
    # BOTH directions, or the fix could clear the errors by never reporting
    # nonstate_verb at all: 'eats' really can fill the slot, so the overlap
    # is real and must survive
    findings = _nsv_overlaps(tmp_path, "{lit: eats}")
    assert findings, "the real overlap disappeared with the false one"
    assert any("r/verbal" in f.message and "r/literal" in f.message for f in findings)


# --- the bare_plural blind spot (same class, next type over) -----------------
# Found the day Stage 9d added a bare_plural rule: `{lit: all}` was reported
# as colliding with a slot only a plural NOUN can bind.

BP_LEX = """format: rulekit/lexicon@1
entries:
  all: {senses: [quantifier]}
  are: {senses: [verb], verb: {lemma: be}}
  dog: {senses: [noun], plural: dogs}
  dogs: {senses: [noun]}
  pet: {senses: [noun], plural: pets}
"""

BP_RULE_TMPL = """format: rulekit/rules@1
rules:
  - id: {rid}
    phase: read
    match:
      sentence:
        - {mid}
        - {{lit: are}}
        - {{slot: pred, type: noun}}
    emits:
      - {{fact: quantity, entity: "x", measure: "{{pred}}", value: 1.0}}
"""


def _bp_overlaps(tmp_path, lit_mid):
    reg = _mk(
        tmp_path, BP_LEX,
        BP_RULE_TMPL.format(rid="r/generic", mid="{slot: cls, type: bare_plural}"),
        BP_RULE_TMPL.format(rid="r/literal", mid=lit_mid),
    )
    return lint_overlaps(reg)


def test_a_quantifier_lit_cannot_collide_with_a_bare_plural_slot(tmp_path):
    assert _bp_overlaps(tmp_path, "{lit: all}") == []


def test_a_plural_noun_lit_still_collides_with_a_bare_plural_slot(tmp_path):
    findings = _bp_overlaps(tmp_path, "{lit: dogs}")
    assert findings, "the real overlap disappeared with the false one"


@pytest.mark.parametrize("gate", ["qualified: true", "possessed: true", "type: qualified", "type: possessed"])
def test_bare_and_described_slots_are_disjoint(tmp_path, gate):
    reg = _mk(tmp_path, BASE_LEX, BASE_CATS,
              RULE_TMPL.format(rid="r/bare", gate="cat: animal, bare: true"),
              RULE_TMPL.format(rid="r/described", gate=(gate if gate.startswith("type:") else "cat: animal, " + gate)))
    assert lint_overlaps(reg) == []


@pytest.mark.parametrize("other,overlaps", [
    ("size", False), ("hue", True), ("dark_hue", True), ("warm_hue", True),
])
def test_qualified_slots_intersect_only_with_compatible_modifiers(tmp_path, other, overlaps):
    lexicon = BASE_LEX + "  red: {senses: [adjective]}\n  big: {senses: [adjective]}\n"
    categories = """format: rulekit/categories@1
categories:
  animal: {parent: noun}
  hue: {parent: adjective}
  dark_hue: {parent: hue}
  warm_hue: {parent: adjective}
  size: {parent: adjective}
members:
  animal: [dog, cat]
  dark_hue: [red]
  warm_hue: [red]
  size: [big]
"""
    reg = _mk(tmp_path, lexicon, categories,
              RULE_TMPL.format(rid="r/first", gate="cat: animal, counted: true, qualified: true, qualifier_cat: hue"),
              RULE_TMPL.format(rid="r/second", gate=f"cat: animal, counted: true, qualified: true, qualifier_cat: {other}"))
    assert bool(lint_overlaps(reg)) == overlaps
