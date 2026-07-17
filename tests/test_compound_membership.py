"""Qualified-compound copular membership reads soundly — one class, three
faces (all synthetic; the two latent bugs were invisible to every benchmark
because verdicts never commit):

  1. LOOSE MATCH (consumer): "Rex is a dog. Is Rex a chocolate dog?" answered
     'yes' — the ask rendered the compound's head lemma, so the bare-head
     fact satisfied the qualified question. ask/is-membership now queries
     `{coll.qualified}` (full modifier+head phrase).
  2. NEGATED COMPOUND (emission): "Rex is not a chocolate dog" minted
     Membership(rex, 'dog', False) — ¬(A ∧ B) read as ¬B. Only the full
     phrase is denied now.
  3. INTERSECTIVE SPLIT (emission, opt-in): a positive compound asserts its
     full phrase + its head; a modifier splits out alone ONLY via the
     `intersective_modifier` category (a structural name — members live in
     packs; no registry in the repo's benchmark projects declares it, so
     their behavior is head + phrase only).
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Membership

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def _verdict(text, reg):
    r = solve(text, reg, tracing=False)
    return r.answer.value if r.answer.kind == "verdict" else r.answer.kind


# ---- faces 1 and 2: the default registry (no intersective category) ---------

def test_bare_head_fact_never_answers_a_qualified_question(full_registry):
    got = _verdict("Rex is a dog. Is Rex a chocolate dog?", full_registry)
    assert got == "undetermined"


def test_qualified_fact_answers_its_own_phrase(full_registry):
    got = _verdict("Rex is a chocolate dog. Is Rex a chocolate dog?", full_registry)
    assert got == "yes"


def test_compound_still_entails_its_head(full_registry):
    # the compound-keeps-head contract, now as an explicit fact
    got = _verdict("Rex is a chocolate dog. Is Rex a dog?", full_registry)
    assert got == "yes"


def test_negated_compound_denies_only_the_full_phrase(full_registry):
    assert _verdict(
        "Rex is not a chocolate dog. Is Rex a chocolate dog?", full_registry
    ) == "no"
    # ¬(chocolate ∧ dog) says NOTHING about dog alone
    assert _verdict(
        "Rex is not a chocolate dog. Is Rex a dog?", full_registry
    ) == "undetermined"


def test_bare_noun_membership_unchanged(full_registry):
    assert _verdict("Bob is a student. Is Bob a student?", full_registry) == "yes"
    assert _verdict("Bob is not a student. Is Bob a student?", full_registry) == "no"


def test_no_category_means_no_split(full_registry):
    # without `intersective_modifier` in the registry, a modifier never
    # becomes its own fact
    r = solve("Rex is a chocolate dog.", full_registry, tracing=False)
    collections = {f.collection for f in r.store.by_kind(Membership)}
    assert collections == {"dog", "chocolate dog"}


# ---- face 3: a registry that declares the intersective category -------------

@pytest.fixture(scope="module")
def intersective_registry(tmp_path_factory):
    root = tmp_path_factory.mktemp("intersective-pack")
    (root / "pack.yaml").write_text(
        "format: rulekit/pack@1\nname: intersective-test\nversion: 0.0.1\n"
        "description: synthetic intersective-modifier members\n"
    )
    (root / "categories").mkdir()
    (root / "categories" / "c.yaml").write_text(
        "format: rulekit/categories@1\n"
        "categories:\n"
        "    intersective_modifier: {parent: noun}\n"
        "    nationality_noun: {parent: intersective_modifier}\n"
        "members:\n"
        "    nationality_noun: [czech]\n"
    )
    (root / "lexicon").mkdir()
    (root / "lexicon" / "l.yaml").write_text(
        "format: rulekit/lexicon@1\n"
        "entries:\n"
        "    czech: {senses: [noun]}\n"
        "    conductor: {senses: [noun], plural: conductors}\n"
        "    choral: {senses: [adjective]}\n"
    )
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", root])
    )


def test_intersective_modifier_splits_out(intersective_registry):
    r = solve(
        "Miroslav was a Czech choral conductor.", intersective_registry,
        tracing=False,
    )
    collections = {f.collection for f in r.store.by_kind(Membership)}
    # full phrase + head + phrase-minus-intersective + the intersective alone
    assert collections == {
        "czech choral conductor", "conductor", "choral conductor", "czech",
    }
    assert all(f.polarity for f in r.store.by_kind(Membership))


def test_intersective_split_is_positive_only(intersective_registry):
    r = solve(
        "Miroslav was not a Czech choral conductor.", intersective_registry,
        tracing=False,
    )
    facts = list(r.store.by_kind(Membership))
    assert [(f.collection, f.polarity) for f in facts] == [
        ("czech choral conductor", False)
    ]


def test_non_intersective_modifier_never_splits(intersective_registry):
    # 'choral' is not in the category: it may not stand alone
    got = _verdict(
        "Miroslav was a Czech choral conductor. Is Miroslav a choral conductor?",
        intersective_registry,
    )
    assert got == "yes"
    got = _verdict(
        "Miroslav was a Czech choral conductor. Is Miroslav a Czech?",
        intersective_registry,
    )
    assert got == "yes"
