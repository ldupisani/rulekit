"""Stage 6 (projects/scratch/ROADMAP.md): the verbal frontier, re-landed from
the archived v1 with its three hazards designed out structurally:

  - 'be'-twin: the v slot is `nonstate_verb` (verb-sensed, not in `state`),
    so copular sentences stay the copular rules' territory;
  - the participle missplit: the verbal universal's pred span BLOCKS
    verb-sensed words, so "All students trained by Yale are smart" fails
    the verbal rule and falls to the copular rule (participial cls phrase);
  - the arithmetic clash: `span_blocks_counted` keeps merged counted nouns
    ('3 apples') out of verbal spans — the fold keeps its Quantities.

All synthetic."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified, Quantity

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


# ---- ground verbal + echo ------------------------------------------------------

def test_verbal_ground_echo(logic_reg):
    got = _verdict(
        "Rex eats apples. Is it true that Rex eats apples?", logic_reg)
    assert got == "yes"


def test_verbal_tense_collapses_via_lemma(logic_reg):
    # FOLIO's FOL is tenseless (the campaign's tense probe) — 'ate' and
    # 'eats' share the verb lemma, so the atom keys match
    got = _verdict(
        "Rex ate apples. Is it true that Rex eats apples?", logic_reg)
    assert got == "yes"


# ---- verbal universals ---------------------------------------------------------

def test_verbal_universal_instantiates(logic_reg):
    got = _verdict(
        "Every dog eats apples. Rex is a dog. "
        "Is it true that Rex eats apples?", logic_reg)
    assert got == "yes"


def test_participial_cls_falls_to_the_copular_rule(logic_reg):
    # the v1 missplit, with a LEXICONED participle so the verbal rule truly
    # competes: "All books sold by the school are cheap" must NOT bind
    # v='sold' — the verbal pred span blocks verb-sensed words ('are'), so
    # the verbal rule fails and the copular rule reads the participial cls
    # as one phrase key
    r = engine.solve("All books sold by the school are cheap.",
                     logic_reg, tracing=False)
    quants = [(f.cls, f.pred) for f in r.store.by_kind(Quantified)]
    # the participle lemma-folds inside the phrase key (sold -> sell),
    # the same per-token normalization that collapses tense - and the
    # conclusion side folds identically, so keys match
    assert ("book sell by school", "cheap") in quants
    assert not any("school are cheap" in p for _c, p in quants)


def test_copular_sentences_stay_copular(logic_reg):
    # 'is' is a state verb: the verbal rules must not twin the copular atoms
    r = engine.solve("Rex is a dog.", logic_reg, tracing=False)
    assert {f.pred for f in r.store.by_kind(Atom)} == {"dog"}


@pytest.mark.parametrize("verb", ["be", "been", "being"])
def test_additional_be_forms_stay_out_of_verbal_universals(logic_reg, verb):
    # These forms are lexically owned by difg-mined. They extend the event-
    # reader exclusion category, not the narrower arithmetic state category.
    r = engine.solve(f"Every dog {verb} friendly.", logic_reg, tracing=False)
    assert not list(r.store.by_kind(Quantified))
    assert logic_reg.word_in_category(verb, "non_event_verb")
    assert not logic_reg.word_in_category(verb, "state")


# ---- the arithmetic clash: counted nouns stay the fold's -----------------------

def test_counted_sentences_keep_their_quantities(logic_reg):
    r = engine.solve("Tom bought 3 apples. How many apples did Tom buy?",
                     logic_reg, tracing=False)
    assert r.answer.committed
    assert r.answer.value == 3
    assert not list(r.store.by_kind(Atom))


def test_bare_values_ride_in_verbal_spans(logic_reg):
    # a DATE is logic prose, not arithmetic — '1946' has no counted noun
    got = _verdict(
        "Miroslav sold a book in 1946. "
        "Is it true that Miroslav sold a book in 1946?", logic_reg)
    assert got == "yes"


# ---- the existential-verbal form (the user-example shape) ----------------------

def test_existential_verbal_witness(logic_reg):
    # "Is it true that A <cls> <verb> ...?" — ∃-introduction over a witness
    # holding both the class atom and the verbal atom
    got = _verdict(
        "Rex is a dog. Rex eats apples. "
        "Is it true that A dog eats apples?", logic_reg)
    assert got == "yes"


def test_existential_verbal_open_world(logic_reg):
    got = _verdict(
        "Rex is a dog. Is it true that A dog eats apples?", logic_reg)
    assert got in ("undetermined", "decline")


def test_verbal_null_control(logic_reg):
    got = _verdict(
        "Rex eats apples. Is it true that Ann eats apples?", logic_reg)
    assert got in ("undetermined", "decline")
