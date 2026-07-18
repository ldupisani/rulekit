"""Date arithmetic (difg): ISO dates as whole tokens, spans, day-of-year.

SYNTHETIC ONLY (constitution rule 3): invented dates, not difg CASES.

The enabling piece is a READER, not a rule -- an ISO date is one token
(tokenize.py) with value_kind "date" (numbers.py `_ISO_DATE`) and its own
sense, the `point`/_TUPLE precedent one value-kind over. Before it,
"2024-01-01" reached the asks as three free-standing counts.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.tokenize import tokenize


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


# --- the READER, and the incidental behaviours it must not disturb ---------
# A pattern's incidental behaviours are its contract: tightening _DIGIT for
# coordinates once dropped its accidental trailing-comma tolerance and broke
# three unrelated items. The date alternative LEADS the alternation, so pin
# what the neighbouring branches still do.


def test_an_iso_date_is_one_token():
    folds = [u.surface for u in tokenize("Due 2024-01-01 sharp.").units]
    assert "2024-01-01" in folds


@pytest.mark.parametrize(
    "text, expect",
    [
        ("She ran 5-10 miles", "5"),        # hyphenated RANGE still splits
        ("It cost 1,234 dollars", "1,234"),  # thousands grouping intact
        ("He came 3rd overall", "3rd"),      # fused ordinal intact
        ("Half is 1/4 more", "1/4"),         # slash fraction intact
    ],
)
def test_neighbouring_number_forms_are_untouched(text, expect):
    assert expect in [u.surface for u in tokenize(text).units]


def test_a_longer_digit_run_is_not_a_date():
    # the pattern is fully anchored (4-2-2 + a negative lookahead), so a
    # digit run that merely CONTAINS the shape must not be claimed
    assert "2024-01-011" not in [u.surface for u in tokenize("code 2024-01-011 here").units]


def test_a_date_carries_no_scalar(reg):
    # like a tuple, a date is not a quantity -- value-accounting must never
    # demand it be consumed as one
    units = [u for u in solve("What is the day of the year for 2019-07-04?", reg).question.units]
    date = next(u for u in units if u.features.get("value_kind") == "date")
    assert "value" not in date.features


# --- the spans -------------------------------------------------------------


@pytest.mark.parametrize(
    "question, want",
    [
        ("How many days are between 2020-01-01 and 2020-01-31?", 30.0),
        ("How many weeks are between 2020-01-01 and 2020-01-29?", 4.0),
        ("How many years are between 1990-06-01 and 2020-06-01?", pytest.approx(30.0, rel=0.01)),
    ],
)
def test_calendar_spans(reg, question, want):
    assert solve(question, reg).answer.value == want


def test_a_span_is_absolute(reg):
    # the later date first must not report a negative span
    a = solve("How many days are between 2020-01-01 and 2020-01-31?", reg).answer.value
    b = solve("How many days are between 2020-01-31 and 2020-01-01?", reg).answer.value
    assert a == b == 30.0


def test_leap_day_is_counted(reg):
    # a real calendar difference, not a 30-day-month approximation
    assert solve(
        "How many days are between 2020-02-28 and 2020-03-01?", reg
    ).answer.value == 2.0


def test_day_of_year_respects_leap_years(reg):
    # 2020-03-01 is day 61 (Feb has 29); 2021-03-01 is day 60
    assert solve("What is the day of the year for 2020-03-01?", reg).answer.value == 61.0
    assert solve("What is the day of the year for 2021-03-01?", reg).answer.value == 60.0


def test_an_impossible_date_declines(reg):
    # the reader's SHAPE gate is 4-2-2 digits, which "2024-13-45" satisfies --
    # only the consumer can know it is not a date, and it must decline rather
    # than clamp or guess a month
    assert solve(
        "What is the day of the year for 2024-13-45?", reg
    ).answer.kind == "decline"


def test_the_span_divisors_are_pack_data_not_python(reg):
    # constitution rule 1: a divisor keyed on a unit WORD is a word-specific
    # fact. If this table ever moved into the consumer, this test is the one
    # that should start failing.
    assert reg.calendar_span_days == {
        "day": 1.0, "week": 7.0, "month": 30.4375, "year": 365.25
    }


# --- the SPELLED date form: three slots, month looked up in pack data -------


def test_a_spelled_date_span(reg):
    assert solve(
        "How many days are between 3 Jan 2019 and 13 Feb 2019?", reg
    ).answer.value == 41.0


def test_spelled_and_iso_forms_agree(reg):
    a = solve("How many days are between 1 Jan 2024 and 31 Jan 2024?", reg).answer.value
    b = solve("How many days are between 2024-01-01 and 2024-01-31?", reg).answer.value
    assert a == b == 30.0


def test_an_unknown_month_declines(reg):
    assert solve(
        "How many days are between 1 Smorg 2024 and 10 Feb 2024?", reg
    ).answer.kind == "decline"


def test_an_impossible_spelled_date_declines(reg):
    # 31 February -- the slots are all well-formed, so only building the date
    # can catch it, and it must decline rather than roll over into March
    assert solve(
        "How many days are between 31 Feb 2024 and 10 Mar 2024?", reg
    ).answer.kind == "decline"


def test_a_full_month_name_reads_too(reg):
    # this was a documented GAP while the spelled form was read by its own ASK
    # (whose month slots took names, and 'January' is a `timeperiod` noun).
    # Moving the reading into condense closed it for free -- the merge gates on
    # the SENSE being a name or a noun, so both spellings arrive as one date.
    assert solve(
        "How many days are between 1 January 2024 and 31 January 2024?", reg
    ).answer.value == 30.0


def test_the_spelled_form_reaches_EVERY_date_ask(reg):
    # the point of reading in condense rather than in an ask: `day of year`
    # never grew a spelled variant and accepts one anyway, because it asks for
    # a `date` slot and a date is now a date whatever its surface form
    assert solve("What is the day of the year for 1 Mar 2024?", reg).answer.value == 61.0


def test_a_lowercase_modal_month_is_not_a_date(reg):
    # 'may' is a MODAL in the lexicon. Capitalised after a number it reads as
    # a name (so "1 May 2024" IS a date), but the bare modal must never look
    # like one.
    from rulekit.kernel.condense import condense
    from rulekit.kernel.numbers import annotate_numbers
    from rulekit.kernel.senses import annotate_senses
    from rulekit.kernel.tokenize import tokenize

    r = tokenize("you may 2024 things")
    annotate_numbers(r, reg)
    annotate_senses(r, reg)
    condense(r, reg)
    assert not any(u.features.get("value_kind") == "date" for u in r.units)


def test_a_capitalised_may_after_a_day_is_a_date(reg):
    assert solve(
        "How many days are between 1 May 2024 and 11 May 2024?", reg
    ).answer.value == 10.0


@pytest.mark.parametrize(
    "text",
    [
        "He bought 5 March tickets",   # no year follows
        "Tom has 12 May flowers",      # ditto, and 'May' is capitalised
        "On 5 Mar 99 he left",         # a year needs FOUR digits
        "I saw 31 Feb 2024 written",   # an impossible date stays unread
    ],
)
def test_the_merge_leaves_non_dates_alone(reg, text):
    # a merge pass runs on EVERY corpus, so its refusals are as much a
    # contract as its merges
    from rulekit.kernel.condense import condense
    from rulekit.kernel.numbers import annotate_numbers
    from rulekit.kernel.senses import annotate_senses
    from rulekit.kernel.tokenize import tokenize

    r = tokenize(text)
    annotate_numbers(r, reg)
    annotate_senses(r, reg)
    condense(r, reg)
    assert not any(u.features.get("value_kind") == "date" for u in r.units)


def test_a_spelled_date_carries_no_scalar(reg):
    # the same invariant as an ISO date: not a quantity, so value-accounting
    # must never demand it be consumed as one
    from rulekit.kernel.condense import condense
    from rulekit.kernel.numbers import annotate_numbers
    from rulekit.kernel.senses import annotate_senses
    from rulekit.kernel.tokenize import tokenize

    r = tokenize("The 1 Jan 2024 report")
    annotate_numbers(r, reg)
    annotate_senses(r, reg)
    condense(r, reg)
    date = next(u for u in r.units if u.features.get("value_kind") == "date")
    assert "value" not in date.features
    assert date.features["components"] == "2024-01-01"


def test_the_month_table_is_pack_data(reg):
    # constitution rule 1 -- no month is named in the consumer
    assert reg.month_numbers["jan"] == 1
    assert reg.month_numbers["december"] == 12
