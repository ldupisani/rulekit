"""A capitalized QUANTIFIER is never a name (structural sense exemption).

FOLIO's wrapper embeds its conclusion mid-question ("Is it true that
<Conclusion>?"), so the conclusion keeps its sentence-initial capital and
'No plants are mushrooms' arrived as name('No') + verb('plants') + 'be
mushrooms' — three stacked misreadings, saved from a confident-wrong only
by the open-world 'undetermined'. The capitalization-naming branch
(senses.py) already exempts timeperiod words for the same reason (weekday
adjuncts); quantifier-sensed words get the identical structural exemption.

Trade measured before shipping: quantifier words heading REAL names are
one item across all seven DEV corpora ("at All Goods Available store",
gsm8k dev-holdout, declines before and after); FOLIO's wrapper capitalizes
a quantifier in 78 dev-train conclusions.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import analyze

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


def _senses(reading, surface):
    return [
        u.features.get("senses")
        for u in reading.units
        if u.surface == surface
    ]


def test_mid_sentence_capitalized_quantifier_keeps_its_sense(reg):
    r = analyze("Is it true that No plants are mushrooms?", reg, sentence_index=0)
    assert _senses(r, "No") == [["quantifier"]]


def test_capitalized_quantifier_never_merges_into_a_name(reg):
    # 'All' + capitalized 'CD' must NOT merge-name into 'all cd' — the
    # quantifier stays a quantifier and the class phrase stays its own unit
    r = analyze("Is it true that All CD players are broken?", reg, sentence_index=0)
    surfaces = [u.surface for u in r.units]
    assert "All" in surfaces  # not swallowed by a merge
    assert _senses(r, "All") == [["quantifier"]]


def test_article_guarded_capitalized_word_is_unchanged(reg):
    # "a No response": the article check already kept 'No' un-named before
    # this exemption; pin that the path still holds
    r = analyze("9% of the guests RSVP with a No response.", reg, sentence_index=0)
    assert _senses(r, "No") == [["quantifier"]]


def test_non_quantifier_known_words_still_name(reg):
    # 'Rose' is a known common word; capitalization mid-sentence still names
    # it — the exemption is quantifier-sensed words only
    r = analyze("Sam met Rose yesterday.", reg, sentence_index=0)
    assert _senses(r, "Rose") == [["name"]]
