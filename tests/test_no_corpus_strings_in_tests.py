"""Constitution rule 3: never a benchmark string in `tests/`.

WHY IT MATTERS. A test written from a corpus item passes for the same reason
the corpus item passes, so it stops being an independent SPECIFICATION and
becomes a second copy of the bench. This repo's own record is blunt about the
consequence — "the corpora are a SAMPLE; the tests are the SPECIFICATION", and
twice a change passed all six corpora and was still wrong, caught only by a
unit test encoding a contract no corpus phrases. A test that borrows corpus
prose cannot be that test.

The check needs the gitignored data, so it SKIPS in CI and runs locally where
the corpora exist — the same shape as the existing data-backed gate tests.

⚠ THE ALLOWLIST IS A DEBT LEDGER, NOT AN EXEMPTION. It records sentences that
were already in `tests/` when this check landed, so the check starts GREEN and
catches NEW ones (a check that starts red is not a check). Most are incidental
collisions on generic question shapes — "How many apples does he have?" is
what any synthetic test of that ask would write — but some are real borrowings
and should be replaced when their file is next touched. Do not add to it.
"""

import re
from pathlib import Path

import pytest

from rulekit.data.project import load_project

ROOT = Path(__file__).resolve().parents[1]

# Sentences already present when this check landed. Shrink this, never grow it.
_PRE_EXISTING = {
    # generic question shapes — any synthetic test of the same ask writes these
    "How many apples does he have?",
    "How many apples does Bob have?",
    "How much money does he have left?",
    "How much money does she have left?",
    "How much money do they have altogether?",
    "How much money do the three of them have altogether?",
    "How many marbles are there altogether?",
    "How many pens are there in all?",
    "How many books were on the shelves?",
    "How many models can she buy now?",
    "How many total toys does he buy?",
    "How many points did they score in total?",
    "How many stickers does Victor have in total?",
    "How many pairs of shoes do they have in all?",
    "How much did she pay for everything?",
    "How much will each of them earn if they divided their total earning?",
    "How many pieces of litter did they pick up altogether?",
    "How many more marbles did John have than Ben then?",
    # real borrowings, pre-dating this check — replace when the file is touched
    "Thor is 13 times older than Captain America.",
    "Ben had 18 marbles and John had 17 marbles.",
    "Ben gave half of his marbles to John.",
    "Jar B has 12 more marbles than jar A.",
    "Jar C has twice as many marbles as jar B.",
    "John works at the Emmet Building.",
    "Is it true that Jim is a Knicks player?",
    "Is it true that No plants are mushrooms?",
    "Is it true that Oxford Circus is designed by a British architect?",
    "Sūduva Marijampolė is a soccer team.",
    "What is the force on a mass of 10 kg accelerating at 3 m/s^2?",
    "What is 2 to the power of 10?",
    "Convert 100 centimeters to inches",
}

_PROJECTS = ("gsm8k", "asdiv", "svamp", "mawps", "scibench", "difg", "folio")
_SLICES = ("dev", "test")


def _corpus_sentences():
    # One sentence can occur in several firewall slices or corpora. The guard
    # only needs to test its text once; retain the first deterministic source
    # solely for the failure report.
    out = {}
    for proj in _PROJECTS:
        for sl in _SLICES:
            try:
                items = load_project(ROOT / "projects" / proj).dataset_items(sl)
            except Exception:
                continue
            for it in items:
                for sent in re.split(r"(?<=[.?])\s+", it["text"]):
                    sent = sent.strip()
                    # short fragments collide by chance; a long sentence does not
                    if len(sent) > 28:
                        out.setdefault(sent, (proj, sl))
    return [
        (proj, sl, sent)
        for sent, (proj, sl) in out.items()
    ]


def test_no_new_corpus_sentence_appears_in_tests():
    corpus = _corpus_sentences()
    if not corpus:
        pytest.skip("benchmark data absent (gitignored) — runs locally, not in CI")

    sources = {p: p.read_text() for p in ROOT.joinpath("tests").glob("*.py")
               if p.name != Path(__file__).name}
    # Searching every corpus sentence through every source file made this
    # single guard one third of the suite. Keep the exact substring contract,
    # but use three necessary fixed-width anchors to discard nearly every
    # impossible match first. A real match necessarily contains every anchor,
    # so this cannot hide a corpus borrowing; the final check below is still
    # the original exact substring test.
    anchor_width = 16
    candidates = [
        (proj, sl, sent)
        for proj, sl, sent in corpus
        if sent not in _PRE_EXISTING
    ]

    def anchors(sentence):
        middle = (len(sentence) - anchor_width) // 2
        return {
            sentence[:anchor_width],
            sentence[middle:middle + anchor_width],
            sentence[-anchor_width:],
        }

    needed = {
        anchor
        for _proj, _sl, sentence in candidates
        for anchor in anchors(sentence)
    }
    present = set()
    for source in sources.values():
        for offset in range(len(source) - anchor_width + 1):
            anchor = source[offset:offset + anchor_width]
            if anchor in needed:
                present.add(anchor)

    found = {}
    for proj, sl, sent in candidates:
        if not anchors(sent) <= present:
            continue
        for path, source in sources.items():
            if sent in source:
                found.setdefault(sent, (path.name, proj, sl))
                break

    assert not found, "corpus strings in tests/ (constitution rule 3):\n" + "\n".join(
        f"  {where[0]} <- [{where[1]}/{where[2]}] {sent!r}" for sent, where in sorted(found.items())
    )


def test_the_allowlist_has_no_dead_entries():
    # an allowlist entry whose sentence no longer appears is debt already paid;
    # leaving it in would quietly re-permit the string later
    sources = "\n".join(p.read_text() for p in ROOT.joinpath("tests").glob("*.py")
                        if p.name != Path(__file__).name)
    stale = sorted(s for s in _PRE_EXISTING if s not in sources)
    assert not stale, f"allowlist entries no longer present — delete them: {stale}"
