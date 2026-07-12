"""Mining increment 72: group-total premises phrased as verb-subject totals
("A and B have N ITEM together", "In total, they VERB N ITEM", "N ITEM
total").

Mechanism: two new pattern rules in packs/arithmetic/rules/core.yaml, both
emitting the SAME existing GroupTotal fact kind (model.py untouched) that
increment 69's synth/sum-constraint plugin (saturate.py, unchanged) already
consumes:

- arithmetic/group-total-trailing: a stated quantity followed by a TRAILING
  totality marker ("... N ITEM together/altogether/total/combined", cat:
  aggregate, optionally preceded by 'all' or a preposition like 'in').
  Matches anywhere in the sentence, like the existing arithmetic/group-
  total-of's "a total of N ITEM" tail — the preceding subject/verb is never
  parsed.
- arithmetic/group-total-leading: the LEADING sibling, "In total, SUBJ VERB
  N ITEM" — requires the ordinary SUBJ VERB N ITEM skeleton right after the
  marker so the matched item is the sentence's own dobj.

Both rules consume the item's noun unit, which is the SAME unit the
sentence's own verb would otherwise bind as its dobj — this marks it
`pattern_consumed` and suppresses learn.py's ordinary per-entity fold for
that clause, so the stated number is read exactly once (as a group total),
never ALSO as an independent per-entity holding.

Synthetic only.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_trailing_together_with_compound_subject(full_registry):
    # arithmetic/group-total-trailing: "... N ITEM together" — the marker
    # never parses the preceding "Lena and Yusuf" compound subject at all;
    # only the item's noun+value and the trailing marker matter.
    # standard(Yusuf) = (42 - 8) / (1 + 1) = 17.
    r = solve(
        "Lena and Yusuf have 42 seashells together. "
        "Lena has 8 more seashells than Yusuf. "
        "How many seashells does Yusuf have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 17


def test_trailing_bare_total_no_of(full_registry):
    # arithmetic/group-total-trailing: bare "N ITEM total" — no "a total
    # of" framing at all (that's arithmetic/group-total-of, a disjoint
    # literal skeleton: "of" leads the item there, trails it here).
    # standard(Rohit) = 130 / (1 + 4) = 26.
    r = solve(
        "Priyanka picked four times as many mangoes as Rohit. "
        "They picked 130 mangoes total. "
        "How many mangoes did Rohit pick?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 26


def test_trailing_all_together(full_registry):
    # arithmetic/group-total-trailing: the two-word "all together" marker
    # ('all' optional quantifier + 'together' aggregate).
    # standard(Idris) = (90 - 10) / (1 + 1) = 40.
    r = solve(
        "Camille and Idris have 90 buttons all together. "
        "Camille has 10 more buttons than Idris. "
        "How many buttons does Idris have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 40


def test_leading_in_total_pronoun_subject(full_registry):
    # arithmetic/group-total-leading: "In total, they picked N ITEM" — the
    # plural pronoun subject is never resolved (deliberately excluded from
    # document-level pronoun binding); the rule never needs it resolved,
    # only consumes it to bridge to the verb+item.
    # standard(Priyanka) = (58 - 12) / (1 + 1) = 23.
    r = solve(
        "Rohan picked 12 more marbles than Priyanka. "
        "In total, they picked 58 marbles. "
        "How many marbles did Priyanka pick?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 23


def test_leading_in_total_named_subject(full_registry):
    # arithmetic/group-total-leading: a NAMED subject works identically —
    # the `who` slot's identity is never read in the emitted fact, only
    # consumed structurally, so it does not matter that 'Marco' also
    # happens to be one of the relation's own holders.
    # standard(Aisha) = (54 - 6) / (1 + 1) = 24.
    r = solve(
        "Marco sold 6 more kites than Aisha. "
        "In total, Marco sold 54 kites. "
        "How many kites did Aisha sell?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 24


def test_trailing_total_without_relation_declines_entity_ask(full_registry):
    # DECLINE-SAFETY: "N ITEM total" marks the item a GROUP total, not an
    # independent per-entity holding — learn.py's ordinary fold for this
    # clause is suppressed (pattern_consumed). With no Relation present to
    # pair against, synth/sum-constraint has nothing to solve, so a direct
    # entity-scoped ask must decline rather than fall back to answering
    # from the (suppressed) per-entity reading or the bare group total.
    r = solve(
        "Tom has 20 apples total. "
        "How many apples does Tom have?",
        full_registry,
    )
    assert r.answer.kind != "number"


def test_trailing_marker_absent_still_folds_ordinary_holding(full_registry):
    # Non-interference: the same "N ITEM" shape WITHOUT any aggregate
    # marker trailing it is completely unaffected — this is the ordinary
    # single-holder fold, still handled entirely by learn.py.
    r = solve(
        "Tom has 20 apples. "
        "How many apples does Tom have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 20
