"""Conjoined full clauses — a premise sentence coordinating multiple FULL
clauses at the top level, each with its OWN NAME subject and finite state/
event verb ("Nadia has 17 stickers, Owen has 29 stickers and Farah has 8
stickers."), currently folds only the FIRST clause: the verb->dobj
obligation binds once per sentence, so every subsequent conjunct's own
subject/verb/number is silently dropped. This is the CLAUSE-conjunction
sibling of the NP-conjunction walkers (increments 11/35/45, which recover
extra sibling ITEMS for the SAME subject, "Nadia has 6 pens and 4 markers")
— distinct because here each conjunct introduces a NEW subject.

Mechanism: a structural pre-split in `engine.py`, ahead of any fold
machinery — every top-level ','/' and ' boundary in a premise is a
candidate clause boundary. A boundary only splits when (1) the
accumulated HEAD is ALREADY a complete clause with its own registered
state/event verb (`_has_finite_verb`) — this is what tells a genuine
clause boundary apart from a bare compound-subject fragment ("Callum" in
"Callum and Soraya paint 12 fences over the weekend") — and (2) the
candidate remainder opens with a NAME subject (a small compound, "Talon
and Yusuf", is tolerated) reaching a finite state/event verb with NOTHING
else between (`_clause_finite_verb`) and states its own digit.
Comparative/ratio clauses ("N more/fewer ITEM than Y", "N times as many X
as Y") are deliberately OUT OF SCOPE for this increment
(`_is_relational_clause`) — they feed the relation/ratio synthesizers, a
demonstrably riskier interaction deferred to the relation-family
increments. `than`/`times` are recognized as clause markers via the
`relational_marker`/`multiplier_marker` categories (packs/core-english,
packs/difg-mined) — never a Python word list, mirroring
`clause_marker`/`clause_marker_prep` (packs/difg-mined/categories/
clauses.yaml).

MUST NOT touch `_conjoined_purchase_items`/`_is_rate`/`_price_each_value`
(learn.py's existing NP-conjunction walkers) — this is a purely textual
pre-split that runs before any of that fold machinery ever sees the text.

Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve, split_question, _split_conjoined_clauses

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_three_conjoined_clauses_split_into_separate_premises(full_registry):
    premise_texts, _ = split_question(
        "Nadia has 17 stickers, Owen has 29 stickers and Farah has 8 stickers. "
        "How many stickers do they have in total?",
        full_registry,
    )
    assert len(premise_texts) == 1
    out = _split_conjoined_clauses(premise_texts[0], full_registry)
    assert out == [
        "Nadia has 17 stickers.",
        "Owen has 29 stickers.",
        "Farah has 8 stickers.",
    ]


def test_first_clause_holder_still_resolves(full_registry):
    r = solve(
        "Nadia has 17 stickers, Owen has 29 stickers and Farah has 8 stickers. "
        "How many stickers does Nadia have?",
        full_registry,
    )
    assert r.answer.value == 17


def test_third_clause_holder_now_resolves(full_registry):
    # before this increment ONLY the first conjunct's clause folded; the
    # third clause's own subject/verb/number was silently dropped.
    r = solve(
        "Nadia has 17 stickers, Owen has 29 stickers and Farah has 8 stickers. "
        "How many stickers does Farah have?",
        full_registry,
    )
    assert r.answer.value == 8


def test_two_conjoined_clauses_no_oxford_comma(full_registry):
    r = solve(
        "Milo has 14 shells and Petra has 22 shells. "
        "How many shells does Petra have?",
        full_registry,
    )
    assert r.answer.value == 22


def test_compound_subject_not_a_clause_boundary(full_registry):
    # 'Callum and Soraya' is a COMPOUND SUBJECT sharing one verb, not two
    # coordinated clauses — the head before the 'and' ('Callum') has no
    # verb of its own, so this must never split.
    out = _split_conjoined_clauses(
        "Callum and Soraya paint 12 fences over the weekend.", full_registry
    )
    assert out == ["Callum and Soraya paint 12 fences over the weekend."]


def test_compound_subject_on_both_sides_still_splits(full_registry):
    # a genuine clause boundary between two compound-subject clauses must
    # still be found, without severing the compound subject itself (a
    # naive 'next comma/and' lookahead window would truncate the second
    # clause's candidate check right after the dangling first name and
    # misread it as belonging to the first clause).
    out = _split_conjoined_clauses(
        "Idris and Wren collect 5 boxes of files and Talon and Yusuf "
        "collect 9 boxes of files.",
        full_registry,
    )
    assert out == [
        "Idris and Wren collect 5 boxes of files.",
        "Talon and Yusuf collect 9 boxes of files.",
    ]


def test_compound_object_tail_not_a_new_clause(full_registry):
    # 'Wren' is the tail of the compound OBJECT 'to Idris and Wren', not a
    # new clause subject — the real second clause's subject is the
    # pronoun 'he', two tokens later, which breaks the name+verb chain.
    out = _split_conjoined_clauses(
        "He handed 3 folders to Idris and Wren, and he handed 4 folders "
        "to Talon.",
        full_registry,
    )
    assert out == [
        "He handed 3 folders to Idris and Wren, and he handed 4 folders "
        "to Talon."
    ]


def test_relative_clause_declines(full_registry):
    # 'the shells Milo has' is a relative clause with no comma/'and'
    # boundary introducing a subject at all — never a candidate here.
    out = _split_conjoined_clauses("The shells Milo has are blue.", full_registry)
    assert out == ["The shells Milo has are blue."]


def test_complementizer_clause_never_double_folds(full_registry):
    # a complementizer-introduced clause ('that Talon has 9 folders') whose
    # OWN coordination introduces a new subject may legitimately split
    # (this is the SAME conjoined-clause gap, just wrapped in reported
    # speech) — the invariant this guards is that Talon's own fact is
    # never duplicated and Yusuf's fact is never merged into it.
    r = solve(
        "She mentioned that Talon has 9 folders and Yusuf has 11 folders. "
        "How many folders does Talon have?",
        full_registry,
    )
    assert r.answer.value == 9
    quantities = [f for f in r.facts() if getattr(f, "entity", None) == "talon"]
    assert len(quantities) == 1


def test_np_conjunction_same_subject_unaffected(full_registry):
    # 'Nadia has 6 pens and 4 markers' is a same-subject NP conjunction
    # (increment 35's job, not this candidate's) — no NEW subject after
    # 'and', so this must never split.
    out = _split_conjoined_clauses("Nadia has 6 pens and 4 markers.", full_registry)
    assert out == ["Nadia has 6 pens and 4 markers."]


def test_purchase_conjunction_unaffected(full_registry):
    # increment 11's own conjunct-recovery family (priced purchase lists)
    # must be completely untouched by this structural pre-split.
    r = solve(
        "Owen buys four ribbons at $3 each, two notebooks at $5 each, "
        "and six bracelets at $2 each. How much does Owen spend in all?",
        full_registry,
    )
    assert r.answer.value == 34


def test_comparative_relation_clause_declines_split(full_registry):
    # comparative/ratio clauses are out of scope for this increment (they
    # feed the relation/ratio synthesizers, a riskier interaction) — a
    # sentence made entirely of 'N more than Y' conjuncts must not split.
    out = _split_conjoined_clauses(
        "Petra won 7 more matches than Callum, and Callum won 2 more "
        "matches than Soraya.",
        full_registry,
    )
    assert out == [
        "Petra won 7 more matches than Callum, and Callum won 2 more "
        "matches than Soraya."
    ]


def test_multiplicative_relation_clause_declines_split(full_registry):
    # the 'times' marker (multiplier_marker category) also scopes a
    # clause out, without ANY comparative word present at all — the
    # `_is_relational_clause` check must catch this via 'times' alone.
    out = _split_conjoined_clauses(
        "Yusuf is 3 times older than Idris, and Wren is 15 years old.",
        full_registry,
    )
    assert out == [
        "Yusuf is 3 times older than Idris, and Wren is 15 years old."
    ]


def test_no_digit_conjunct_declines_split(full_registry):
    # a coordinated clause with no stated number of its own is not folded
    # as a premise — declining a non-quantity clause is safer than
    # promoting it.
    out = _split_conjoined_clauses(
        "Farah has 11 shells and Owen has a shell too.", full_registry
    )
    assert out == ["Farah has 11 shells and Owen has a shell too."]
