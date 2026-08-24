"""Increments 122-125 — the temporal origo, and the month fix it unblocks.

docs/deixis.md §4 ran the month fix, gated it, and REVERTED it (`DECL->WRONG 1`). Its
lesson: *do not make a deictic dimension readable before the ask can name a point along
it — doing so converts declines into WRONGS.*

The fix was never the retag. The retag only EXPOSED two independent defects:

  1. `_verb_total` computed its time-set AFTER filtering by verb, so cross-verb time
     evidence was structurally invisible. "In January Benny adds $19 ... by the end of
     March he has $46. How many did he add in March?" -> the $46 is verb='have' and was
     filtered out before the guard ran -> no refusal -> COMMITS 19 (gold 8).
  2. Nothing could carry "March". No ask could name a point in time, so no consumer
     could ever have compared the question's month to a fact's month.

These tests pin both, plus the normalisation that makes a time comparable at all.

Synthetic only (NEVER benchmark items).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import deixis
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.learn import _sentence_time

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def reg():
    return compile_registry(
        load_packs([
            REPO / "packs/core-english",
            REPO / "packs/arithmetic",
            REPO / "packs/difg-mined",
        ])
    )


# ---------------------------------------------------------------------------
# 122 — the label is comparable at all
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sentence,expected",
    [
        ("On Monday, Sam sold 3 apples.", "monday"),
        ("By Monday, Sam sold 3 apples.", "monday"),
        ("Monday, Sam sold 3 apples.", "monday"),
    ],
)
def test_a_preposition_marks_the_adjunct_and_is_not_part_of_the_moment(
    sentence, expected, reg
):
    """"on Monday", "by Monday" and a bare "Monday" are ONE moment.

    They used to be three labels — and since `time` is part of Quantity.key(), three
    different FACT IDENTITIES. Two facts about one Monday could neither dedupe nor be
    seen as same-time.
    """
    assert _sentence_time(analyze(sentence, reg), reg) == expected


def test_a_determiner_IS_part_of_the_moment_and_must_survive(reg):
    """The obvious normalisation (key on the lemma) would collapse these to 'year'.

    That is a PRECISION REGRESSION, not a simplification: it would stop the mixed-time
    refusals firing and turn a decline into a wrong. "last year" and "this year" are
    different moments that happen to share a timeperiod noun.
    """
    last = _sentence_time(analyze("Last year he made 5 dollars.", reg), reg)
    this = _sentence_time(analyze("This year he made 7 dollars.", reg), reg)
    assert last == "last year"
    assert this == "this year"
    assert last != this


# ---------------------------------------------------------------------------
# 123 — the cross-verb hole: THE §4 confident-wrong
# ---------------------------------------------------------------------------


def test_the_deixis_md_section_4_confident_wrong_is_dead(reg):
    """THE REGRESSION TEST FOR THE WHOLE EXERCISE.

    Before: committed 19 — the JANUARY amount, for a question about MARCH.
    Now: declines. The gold is 8, which needs temporal arithmetic we have not built —
    so a decline is the correct outcome, and a commit of any value is a failure.
    """
    result = solve(
        "Benny added 19 dollars in January. By the end of March, he has 46 dollars. "
        "How many dollars did he add in March?",
        reg,
    )
    assert result.answer.kind == "decline", (
        f"committed {result.answer.value!r} for a March question; "
        "this is the §4 confident-wrong resurrected"
    )
    assert result.answer.value != 19


def test_a_state_at_another_moment_blocks_a_single_verb_fold(reg):
    """The guard must see CROSS-VERB time evidence.

    A document that speaks about more than one moment cannot be folded under one verb
    without knowing which moment is asked about.
    """
    result = solve(
        "On Monday, Sam sold 4 apples. On Tuesday, Sam had 9 apples. "
        "How many apples did Sam sell?",
        reg,
    )
    assert result.answer.kind == "decline"


# ---------------------------------------------------------------------------
# 124 — the ask can finally name a point in time
# ---------------------------------------------------------------------------


def test_the_question_names_a_moment_and_it_scopes_the_facts(reg):
    """The reference time is resolved on the TIME dimension, and it FILTERS.

    A fact stamped with a different moment is not evidence about this one.
    """
    result = solve(
        "On Monday, Sam sold 4 apples. On Tuesday, Sam sold 6 apples. "
        "How many apples did Sam sell on Tuesday?",
        reg,
    )
    refs = [
        o for o in result.log.journal.observations if o.source == "ask/reference-time"
    ]
    assert refs, "the question named a time; the ask must journal its temporal origo"
    obs = refs[0]
    assert obs.dimension == deixis.TIME
    assert obs.outcome == "bound"
    assert obs.winner == "tuesday"


def test_a_bare_timeperiod_noun_is_subject_matter_not_an_origo(reg):
    """"How many MONTHS..." — `month` is what is COUNTED, not when.

    Only a PREPOSITION-governed timeperiod noun is an adjunct. Without that test, an
    ask whose own measure happens to be a period word would scope the facts to itself
    and answer nothing.
    """
    result = solve("Sam waited 3 months. How many months did Sam wait?", reg)
    refs = [
        o for o in result.log.journal.observations if o.source == "ask/reference-time"
    ]
    assert not refs, "a counted period noun must never be read as a reference time"


def test_two_named_moments_decline_because_time_has_no_order(reg):
    """Arbitrating between two moments needs an ORDER, and `time` is an opaque label
    with none. Ties decline — the strict-dominance rule, on the TIME dimension."""
    origo = deixis.Origo(sentence=0)
    candidates = [
        deixis.Referent(dimension=deixis.TIME, key="march"),
        deixis.Referent(dimension=deixis.TIME, key="april"),
    ]
    assert deixis.resolve(candidates, origo, dimension=deixis.TIME) is None


# ---------------------------------------------------------------------------
# 125 — the retag: months stop polluting the PERSON pool
# ---------------------------------------------------------------------------


def test_a_month_is_no_longer_a_rival_person(reg):
    """docs/deixis.md §4's thesis in miniature, now closed.

    senses.py's capitalisation override read a mid-sentence "March" as a proper NAME,
    putting it in the PERSON antecedent pool as a rival to the actual person — so the
    next sentence's pronoun could not bind uniquely. Exactly the bug increment 88 fixed
    by hand for weekdays.
    """
    result = solve(
        "In March, Sam had 12 apples. He found 5 more apples. "
        "How many apples does Sam have?",
        reg,
    )
    binds = [
        o for o in result.log.journal.observations if o.source == "bind-discourse"
    ]
    assert binds, "the pronoun must attempt a binding"
    obs = binds[0]
    assert "march" not in {c.key for c in obs.candidates}, (
        "a month is back in the PERSON antecedent pool"
    )
    assert obs.outcome == "bound"
    assert obs.winner == "sam"


def test_may_selects_modal_or_month_from_licensed_context(reg):
    """The ambiguous surface keeps both lexical uses, while the surrounding
    grammar commits exactly one: auxiliary syntax selects the modal and an
    explicit temporal ``in`` phrase selects the calendar noun."""
    assert reg.word_in_category("may", "timeperiod")
    assert set(reg.lexicon["may"].senses) == {"modal", "noun"}

    modal = analyze("Mira may sell stickers.", reg)
    month = analyze("Mira sold 4 stickers in May.", reg)

    assert next(unit for unit in modal.units if unit.surface == "may").sense() == "modal"
    assert next(unit for unit in month.units if unit.surface == "May").sense() == "noun"


def test_every_other_month_joined_the_category(reg):
    for month in (
        "january", "february", "march", "april", "june", "july",
        "august", "september", "october", "november", "december",
    ):
        assert reg.word_in_category(month, "timeperiod"), month
