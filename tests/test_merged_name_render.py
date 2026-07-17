"""A merged NAME renders ONCE in every qualified-phrase position.

merge-name (condense.py) sets the merged unit's lemma to its full fold
("Emmet Building" -> lemma 'emmet building'), but every qualified render
assumed the lemma replaces only the HEAD word (`words[:-1] + [lemma]`) — an
idiom that is correct for merged compounds (lemma = head: 'chocolate dogs'
-> 'chocolate dog') and duplicated names ('emmet building' -> 'emmet emmet
building'). Four call sites shared the idiom; `patterns.qualified_render` is
now the ONE definition (the _ACCOUNTED_VALUE_KINDS lesson: a contract with
two copies has already drifted).

The duplication was invisible to every verdict-level test because it is
SYMMETRIC — the same renderer produces the premise key and the query key, so
the echo still matches. Only a fact-key assertion can see it.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom, Membership
from rulekit.kernel.patterns import qualified_render

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            REPO / "packs/core-english",
            REPO / "packs/arithmetic",
            REPO / "packs/difg-mined",
            REPO / "projects/scratch/packs/logic",
        ])
    )


@pytest.fixture(scope="module")
def arithmetic_reg():
    return compile_registry(
        load_packs([
            REPO / "packs/core-english",
            REPO / "packs/arithmetic",
            REPO / "packs/difg-mined",
        ])
    )


# ---- the helper's contract ----------------------------------------------------

def test_qualified_render_contract():
    # bare noun: the lemma alone
    assert qualified_render(["dogs"], "dog") == "dog"
    # merged compound: lemma replaces the HEAD word only
    assert qualified_render(["chocolate", "dogs"], "dog") == "chocolate dog"
    # merged name: the lemma IS the whole phrase — never a head replacement
    assert qualified_render(["emmet", "building"], "emmet building") == "emmet building"


# ---- span capture (verbal + copular atom keys) --------------------------------

def test_verbal_span_renders_merged_name_once(logic_reg):
    r = solve("John works at the Emmet Building.", logic_reg, tracing=False)
    preds = {f.pred for f in r.store.by_kind(Atom) if f.entity == "john"}
    assert preds == {"work at emmet building"}


def test_copular_span_renders_merged_name_once(logic_reg):
    r = solve("Rex is a Great Dane.", logic_reg, tracing=False)
    preds = {f.pred for f in r.store.by_kind(Atom)}
    assert "great dane" in preds
    assert not any("great great" in p for p in preds)


# ---- the fold's Predication path (names bypass the Membership branch) ---------

def test_name_dobj_predication_carries_the_full_name(arithmetic_reg):
    # a NAME dobj takes the fold's Predication path, not Membership (that
    # branch is noun-gated), so the learn.py/{slot.qualified} call sites can
    # never see a merged name TODAY — they share `qualified_render` anyway so
    # the contract cannot drift apart if a future sense change widens them.
    r = solve("Rex is a Great Dane.", arithmetic_reg, tracing=False)
    from rulekit.kernel.model import Predication
    dobjs = {f.dobj for f in r.store.by_kind(Predication) if f.subject == "rex"}
    assert dobjs == {"great dane"}
