"""The engine: analyze one sentence; solve a whole text.

solve() = premises + trailing question → parse each premise, run pattern
rules, learn facts, saturate, answer, guard. Every step auditable via the
decision trace; the result carries the full epistemic surface (answer OR
why-not + what IS known).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..data.registry import Registry
from . import deixis
from .answer import Answer, answer as run_answer
from .condense import condense
from .document import Document, _bind_discourse, run_document
from .evaluate import ArithmeticLog
from .facts import FactStore
from .guards import GuardVeto, check as run_guards
from .learn import _has_event_polarity
from .mathtext import normalize_math
from .model import Fact, Reading
from .numbers import annotate_numbers
from .obligations import attach_obligations, bind, disambiguate
from .senses import annotate_senses
from .tokenize import split_sentences, tokenize

# senses that mark a sentence as a question/task when they LEAD it, and that
# mark the wh-part inside an "If <clause>, <wh…>" sentence. Sense names are
# structure; the WORDS carrying them live in the packs (the constitution).
ASK_CUE_SENSES = frozenset({"interrogative", "auxiliary", "modal", "imperative"})


def _has_ask_cue_sense(word: str, reg: Registry) -> bool:
    entry = reg.lexicon.get(word.lower().rstrip(",?"))
    return entry is not None and bool(set(entry.senses) & ASK_CUE_SENSES)


# categories (packs/difg-mined/categories/clauses.yaml — the member words
# are only lexically defined in that pack) naming subordinators that can
# open a leading temporal dependent clause ("When X, ..." / "After X, ...").
# Category NAMES are structure, never the words themselves — 'if' stays a
# literal per its own pre-existing skeleton precedent (the check right
# below), but new markers are admitted purely by adding a pack member.
CLAUSE_MARKER_CATEGORIES = ("clause_marker", "clause_marker_prep")


def _leading_temporal_marker(question: str, reg: Registry) -> str | None:
    """The sentence's first word, if it is a registered leading temporal
    clause-marker (category membership only — never a Python word list);
    else None."""
    words = question.split()
    if not words:
        return None
    first = words[0].lower().rstrip(",")
    if any(reg.word_in_category(first, cat) for cat in CLAUSE_MARKER_CATEGORIES):
        return first
    return None


def analyze(
    sentence: str, reg: Registry, sentence_index: int = 0, tracing: bool = True
) -> Reading:
    reading = tokenize(sentence, sentence_index, tracing=tracing,
                       contractions=reg.contractions)
    annotate_numbers(reading, reg)
    annotate_senses(reading, reg)
    disambiguate(reading, reg)
    attach_obligations(reading, reg)
    condense(reading, reg)
    bind(reading, reg)
    return reading


@dataclass
class Result:
    answer: Answer
    premises: list[Reading] = field(default_factory=list)
    question: Reading | None = None
    store: FactStore = field(default_factory=FactStore)
    log: ArithmeticLog = field(default_factory=ArithmeticLog)
    veto: GuardVeto | None = None
    document: Document | None = None

    @property
    def value(self) -> float | str | None:
        return self.answer.value

    def facts(self) -> list[Fact]:
        return list(self.store.facts)

    def deficiencies(self) -> list[str]:
        out: list[str] = []
        for reading in self.premises + ([self.question] if self.question else []):
            out.extend(reading.deficiencies())
        if self.veto is not None:
            out.append(f"[{self.veto.guard}] {self.veto.reason}")
        return out

    def trace(self) -> list[dict]:
        events: list[dict] = []
        for reading in self.premises + ([self.question] if self.question else []):
            for d in reading.decisions:
                events.append({"sentence": reading.sentence_index, **d.to_json()})
        events.extend(event.to_trace_event() for event in self.store.agreement_ambiguities)
        return events


def _split_leading_clause(question: str, reg: Registry) -> tuple[str | None, str]:
    """'If <clause>, <wh…>?' → the clause is a PREMISE, the wh-part the
    question. Split at the first comma whose next word carries an ask-cue
    sense. 'If'/',' are grammatical skeleton; the cues are lexicon data."""
    lowered = question.lower()
    if not lowered.startswith("if "):
        return None, question
    parts = question.split(",")
    for i in range(len(parts) - 1):
        rest = ",".join(parts[i + 1 :]).strip()
        first = rest.split()[0] if rest.split() else ""
        if _has_ask_cue_sense(first, reg):
            clause = ",".join(parts[: i + 1])[2:].strip().lstrip()
            return clause.rstrip(".") + ".", rest
    return _split_leading_clause_commaless(question, reg)


def _split_leading_clause_commaless(
    question: str, reg: Registry
) -> tuple[str | None, str]:
    """Comma-less sibling of `_split_leading_clause` — the LEADING mirror of
    increment 53's `_split_trailing_clause_commaless`, reached only when the
    comma path found no split.

    "If he sold 158 cakes and 147 pastries How many more cakes than pastries
    did baker sell?" — SVAMP writes the fused conditional with no comma, so
    the whole clause stays on the QUESTION side and its counts reach no fact.

    THE CAPITAL DOES THE COMMA'S JOB: the cue is a MID-SENTENCE CAPITALIZED
    ask-cue token. `_has_ask_cue_sense` lowercases internally, so the
    capitalisation test is separate and load-bearing — a lowercase embedded
    cue must never split.

    THE FIRST QUALIFYING BOUNDARY WINS, deliberately NOT the trailing form's
    LAST: the errors are ASYMMETRIC. An early split leaves junk on the
    question side and DECLINES (safe); a late split folds question words
    into a PREMISE and mints facts from unasserted material.

    The promoted clause must carry a digit — which also neutralises a
    capitalised modal-sensed name ('Will', 'May') opening the sentence, since
    the clause before it is empty and hence digit-free."""
    if not question.lower().startswith("if "):
        return None, question
    tokens = question.split()
    for i in range(1, len(tokens)):
        token = tokens[i]
        if not token[:1].isupper():
            continue
        if not _has_ask_cue_sense(token, reg):
            continue
        clause = " ".join(tokens[1:i]).strip().rstrip(",").rstrip(".").strip()
        rest = " ".join(tokens[i:]).strip()
        if not clause or not rest or not any(ch.isdigit() for ch in clause):
            return None, question
        return clause + ".", rest
    return None, question


def _split_leading_temporal_clause(question: str, reg: Registry) -> tuple[str | None, str]:
    """'When/After <clause>, <wh…>?' -> the clause is a PREMISE, the wh-part
    stays the question. Sibling of `_split_leading_clause`'s 'if' form: same
    comma / ask-cue-sense split, but the marker is a pack-registered
    clause_marker/clause_marker_prep category member (never a Python word
    list) rather than a literal, and — mirroring `_split_trailing_clause`'s
    (increment 12) safety property — only a clause that carries a digit is
    promoted to a premise; a bare narrative marker with no stated quantity
    ("When she got home, ...") is left alone rather than risk folding a
    non-premise clause into the fold."""
    marker = _leading_temporal_marker(question, reg)
    if marker is None:
        return None, question
    parts = question.split(",")
    for i in range(len(parts) - 1):
        rest = ",".join(parts[i + 1 :]).strip()
        first = rest.split()[0] if rest.split() else ""
        if _has_ask_cue_sense(first, reg):
            clause = ",".join(parts[: i + 1])[len(marker) :].strip().lstrip()
            clause = clause.rstrip(".").strip()
            if not clause or not any(ch.isdigit() for ch in clause):
                return None, question
            return clause + ".", rest
    return None, question


def _split_trailing_clause(question: str, reg: Registry) -> tuple[str | None, str]:
    """'<wh…>, if <clause>?' -> the clause is a PREMISE, the wh-part stays
    the question. Mirror of `_split_leading_clause` for the trailing form:
    split at the LAST top-level comma whose following text starts with the
    conditional marker 'if' (already pack lexicon; the literal here is
    grammatical skeleton exactly like the leading form's "if " check), strip
    the trailing '?', and only split when the clause carries a number (a
    bare appositive or 'in total, ...' tail never does) — declining a
    coincidental ", if ..." tail with no number is safer than promoting a
    non-premise to a premise.

    Increment 53: when no top-level comma+'if' split exists at all (a
    comma-less trailing conditional — "How old is Ironman if Thor is 1456
    years old?", no comma anywhere), fall back to `_split_trailing_clause_
    commaless`, which finds the same shape at the LAST ' if ' token
    boundary instead of a comma. The comma path above is untouched byte-
    for-byte; the fallback only runs when it found no split at all."""
    if not question.rstrip().endswith("?"):
        return None, question
    parts = question.split(",")
    split_at = None
    if len(parts) >= 2:
        for i in range(len(parts) - 1):
            rest = ",".join(parts[i + 1 :]).strip()
            first = rest.split()[0].lower() if rest.split() else ""
            if first == "if":
                split_at = i  # keep the LAST such boundary
    if split_at is not None:
        wh_part = ",".join(parts[: split_at + 1]).strip()
        clause_rest = ",".join(parts[split_at + 1 :]).strip()
        clause_body = clause_rest[2:].strip().rstrip("?").rstrip(".").strip()
        if not clause_body or not any(ch.isdigit() for ch in clause_body):
            return None, question
        if not wh_part.endswith("?"):
            wh_part = wh_part.rstrip(".") + "?"
        return clause_body + ".", wh_part
    return _split_trailing_clause_commaless(question)


def _split_trailing_clause_commaless(question: str) -> tuple[str | None, str]:
    """Comma-less sibling of `_split_trailing_clause` (increment 53): only
    reached when the question has no top-level comma+'if' split at all.
    Splits at the LAST ' if ' token boundary of the sentence instead of a
    comma — 'if' stays grammatical skeleton, the identical literal used by
    the comma'd form above and by `_split_leading_clause`. Same safety
    property: the promoted clause must carry a digit, so a bare narrative
    tail ('...to see if that works?', '...wondering if she'll come?') is
    left alone rather than risk folding a non-premise clause into the
    fold. The ' if ' spacing anchors on a whole word, not a substring
    (so 'gift'/'differently' never match), and taking the LAST occurrence
    mirrors the comma'd form's 'keep the LAST such boundary' rule when a
    sentence happens to contain more than one 'if'."""
    stripped = question.rstrip()
    if not stripped.endswith("?"):
        return None, question
    body = stripped[:-1]
    idx = body.lower().rfind(" if ")
    if idx == -1:
        return None, question
    wh_part = body[:idx].rstrip()
    clause_body = body[idx + len(" if ") :].strip().rstrip(".").strip()
    if not wh_part or not clause_body or not any(ch.isdigit() for ch in clause_body):
        return None, question
    return clause_body + ".", wh_part + "?"


_CLAUSE_BOUNDARY = re.compile(r",\s+|(?P<word>[A-Za-z]+)\s+")


def _is_conjunction_word(word: str, reg: Registry) -> bool:
    """Same structural sense check `_has_ask_cue_sense` already uses for
    ask-cue words: true when `word` carries the pack-registered
    `conjunction` sense (packs/core-english's 'and' — the ONLY member
    today, but zero words are enumerated here; constitution rule 1).
    `_CLAUSE_BOUNDARY` matches every plain word so this can filter which
    ones are genuine coordinators; `_clause_finite_verb`'s compound-
    subject chain walk uses the same check for the identical reason."""
    entry = reg.lexicon.get(word.lower().rstrip(",.;:"))
    return entry is not None and "conjunction" in entry.senses


def _is_name_token(word: str) -> bool:
    """The SAME structural exception senses.py itself uses: a capitalized,
    not-all-caps word reads as a name — never a Python name list."""
    w = word.rstrip(",.;:")
    return bool(w) and w[:1].isupper() and w[1:].islower()


def _clause_finite_verb(words: list[str], reg: Registry) -> str | None:
    """Walks `words` as SUBJECT (NAME (`and` NAME)*) VERB — a single name,
    or a chain of names joined by 'and' with no other token between them
    ('Ann and Cate'), immediately followed by a registered state/event-
    polarity verb. Returns the verb's lemma, or None if the chain breaks
    on anything else (a pronoun, a comma, a non-name, an unregistered
    word) before a verb is reached — this is what stops a dangling
    compound-OBJECT tail ('..., and she gave more to Idris') from being
    mistaken for a new clause: the tail name passes as a name, but the
    token chain breaks at the pronoun before ever finding a verb reachable
    from that name itself."""
    if not words or not _is_name_token(words[0]):
        return None
    i = 1
    while (
        i + 1 < len(words)
        and _is_conjunction_word(words[i], reg)
        and _is_name_token(words[i + 1])
    ):
        i += 2
    if i >= len(words):
        return None
    fold = words[i].lower().rstrip(",.;:")
    entry = reg.lexicon.get(fold)
    if entry is None or "verb" not in entry.senses:
        return None
    lemma = reg.verb_lemmas.get(fold, fold)
    if reg.word_in_category(lemma, "state") or _has_event_polarity(lemma, reg):
        return lemma
    return None


def _is_relational_clause(text: str, reg: Registry) -> bool:
    """True when `text` carries a comparative/ratio marker: a word rooted
    in the `comparative` category (more/fewer/less/older/younger — the
    SAME category `arithmetic/anchored-relation` and its age/ratio
    siblings gate on), the `multiplier` sense (twice/half — the ratio
    rules' `k` slot), or the `relational_marker`/`multiplier_marker`
    categories (packs/core-english's 'than', packs/difg-mined's 'times' —
    the clause-boundary words those same rules match on as grammatical
    skeleton). Tests category membership only, exactly like
    `clause_marker`/`clause_marker_prep` (packs/difg-mined/categories/
    clauses.yaml) — never a Python word list. These clauses feed the
    relation/ratio synthesizers, which resolve one person's stated
    quantity against ANOTHER named person's — exactly the interaction our
    split newly makes reachable for pairs of people who previously never
    both got a fact at all (the train-diff wrong that first exposed this:
    two comparative clauses about the SAME two people, split, mis-resolved
    through arithmetic/anchored-relation + synth/relation). Scoping this
    increment to PLAIN quantity clauses only — deferring comparative
    conjuncts to the relation-family increments named in the brief's
    'overlaps_with' — keeps the blast radius to the class actually
    described (two or more plain "NAME has N ITEM" clauses)."""
    for word in text.split():
        fold = word.lower().rstrip(",.;:")
        for category in (
            "comparative",
            "multiplier",
            "relational_marker",
            "multiplier_marker",
        ):
            if reg.word_in_category(fold, category):
                return True
    return False


def _has_finite_verb(text: str, reg: Registry) -> bool:
    """Does `text` contain its OWN registered state/event-polarity verb
    anywhere? Confirms a candidate HEAD (the text before a boundary) is
    already a complete clause in its own right — not a bare compound-
    subject fragment ('Callum' in 'Callum and Soraya paint 12 fences over
    the weekend', where the verb belongs to BOTH names and there is no
    clause boundary there at all, only a conjoined SUBJECT). Scans every
    word (not just a leading window) because the head can be arbitrarily
    long by the time later boundaries are considered."""
    for word in text.split():
        fold = word.lower().rstrip(",.;:")
        entry = reg.lexicon.get(fold)
        if entry is None or "verb" not in entry.senses:
            continue
        lemma = reg.verb_lemmas.get(fold, fold)
        if reg.word_in_category(lemma, "state") or _has_event_polarity(lemma, reg):
            return True
    return False


_NEW_CLAUSE_WINDOW = 8  # words scanned after a boundary — enough for a
# subject (possibly a small compound: 'Ann and Cate'), its verb, and its
# own number, without reaching into a wholly separate later clause.


def _looks_like_new_clause(clause_text: str, reg: Registry) -> bool:
    """Structural gate for `_split_conjoined_clauses`: does `clause_text`
    (a fixed-size word window starting right after a candidate boundary,
    deliberately NOT truncated at the next comma/'and' — see the docstring
    below) open with a NAME subject (possibly a small compound, 'Ann and
    Cate') reaching a finite state/event verb with NOTHING else between
    (`_clause_finite_verb`), and state its own digit? Only then is this a
    genuinely conjoined FULL CLAUSE (own subject) rather than a same-
    subject NP conjunction ('Tom has 3 apples and 5 pears' — no new
    subject here, already the increment 11/35/45 walker's job), a
    subordinate/relative clause (no comma/'and'-introduced subject to
    find in the first place), or a dangling compound-OBJECT tail."""
    words = clause_text.split()
    if len(words) < 3:
        return False
    if _clause_finite_verb(words, reg) is None:
        return False
    return any(ch.isdigit() for ch in clause_text)


def _split_conjoined_clauses(sentence: str, reg: Registry) -> list[str]:
    """'Nadia has 17 stickers, Owen has 29 stickers and Farah has 8
    stickers.' — a premise sentence coordinating multiple FULL clauses at
    the top level, each with its own NAME subject, currently folds only
    the FIRST clause (the verb->dobj obligation binds once per sentence).
    Sibling of `_split_leading_clause`/`_split_trailing_clause` above:
    same 'find the boundary, promote what follows' shape, but scanning
    every top-level comma/coordinator boundary in a PREMISE and testing
    each candidate remainder with `_looks_like_new_clause` instead of an
    ask-cue sense. `_CLAUSE_BOUNDARY` matches every plain word so the
    loop can test candidates by SENSE (`_is_conjunction_word`, mirroring
    `_has_ask_cue_sense`) rather than hardcoding the literal 'and' —
    constitution rule 1, zero words enumerated in this module. Declines
    (returns `[sentence]` unchanged) wherever no
    boundary's remainder carries its own subject+verb+digit — protecting
    relative clauses, complementizer clauses, and same-subject NP
    conjunctions (learn.py's own conjunct walkers, increments 11/35/45)
    from ever being double-split here. MUST NOT touch
    `_conjoined_purchase_items`/`_is_rate` — this is a purely textual
    pre-split that runs before any of that fold machinery sees the text.

    Critically, a boundary only splits when the HEAD accumulated so far
    (`_has_finite_verb`) is ALREADY a complete clause on its own — this is
    what tells 'Nadia has 17 stickers, Owen has 29 stickers' (head 'Nadia
    has 17 stickers' — a complete clause; split) apart from 'Callum and
    Soraya paint 12 fences over the weekend' (head 'Callum' — a bare
    name, no verb of its own; the 'and' here conjoins a compound SUBJECT,
    not two clauses, so it must not split).

    The candidate remainder is checked over a fixed word WINDOW
    (`_NEW_CLAUSE_WINDOW`), never truncated at the very next boundary —
    'Idris and Wren pack 50% of their boxes and Talon and Yusuf pack 75%
    of the boxes' has a boundary right after 'Talon', but 'Talon' alone is
    not a clause (it is half of the compound subject 'Talon and Yusuf');
    reading only up to that next boundary would hide the verb 'pack' that
    makes 'Talon and Yusuf pack 75%...' a genuine new clause, and the
    boundary scan would then wrongly keep extending the FIRST clause's
    head to swallow the dangling name.

    Neither side of an accepted boundary may be a comparative/ratio
    clause (`_is_relational_clause`) — see that function's docstring for
    why this fold is scoped to plain quantity statements only."""
    body = sentence.strip()
    if not body:
        return [sentence]
    trailing = ""
    if body.endswith("."):
        body, trailing = body[:-1], "."
    matches = list(_CLAUSE_BOUNDARY.finditer(body))
    if not matches:
        return [sentence]
    clauses: list[str] = []
    cursor = 0
    for m in matches:
        word = m.group("word")
        if word is not None and not _is_conjunction_word(word, reg):
            continue  # a plain word, not a coordinator — not a boundary
        boundary_start = m.start()
        clause_start = m.end()
        head = body[cursor:boundary_start].strip()
        if not head or not _has_finite_verb(head, reg):
            continue  # head isn't a standalone clause yet — e.g. a bare
            # compound-subject fragment; keep accumulating, don't split
        if _is_relational_clause(head, reg):
            continue
        window = " ".join(body[clause_start:].split()[:_NEW_CLAUSE_WINDOW])
        if not _looks_like_new_clause(window, reg) or _is_relational_clause(
            window, reg
        ):
            continue
        clauses.append(head)
        cursor = clause_start
    tail = body[cursor:].strip()
    if tail and clauses:
        clauses.append(tail)
    if len(clauses) < 2:
        return [sentence]
    return [c + trailing for c in clauses]


def _split_fused_premise_question(
    fused: str, reg: Registry
) -> tuple[str | None, str]:
    """Recover a missing terminal boundary between one premise and its ask.

    Some sources concatenate ``<premise> <Question?>`` without punctuation
    after the premise. Capitalization only proposes a boundary; it never
    licenses one. The left side must be wholly consumed by one fact-emitting
    read rule, and the right side wholly consumed by one ask rule. This
    two-sided grammar proof prevents an ask that merely floats to a later
    substring—or a premise rule that reads only a fragment—from manufacturing
    a document boundary.

    The rule and ask vocabularies remain pack-owned. This function compares
    only structural match coverage and therefore introduces no word list in
    the kernel.
    """
    if not fused.rstrip().endswith("?"):
        return None, fused
    first = fused.split()[0] if fused.split() else ""
    first_entry = reg.lexicon.get(first.lower().rstrip(",?"))
    if _has_ask_cue_sense(first, reg) or (
        first_entry is not None and "verb" in first_entry.senses
    ):
        # Ordinary questions overwhelmingly declare themselves at token 0.
        # A registered leading verb covers inverted questions such as
        # copular "Is ...?", whose `is` sense is structural `verb` rather
        # than one of ASK_CUE_SENSES. Fused inputs instead begin with their
        # premise subject/quantifier, so they proceed to the two-sided proof.
        return None, fused

    # Local import avoids making the tokenizer/document entry point depend on
    # the pattern module during engine import. The same functions are imported
    # lazily by solve() for ordinary ask matching below.
    from .patterns import SKIPPABLE_SENSES, match_ask, run_rules

    def meaningful_uids(reading: Reading) -> set[int]:
        return {
            unit.uid
            for unit in reading.units
            if unit.sense() not in SKIPPABLE_SENSES
        }

    # A question already consumed end-to-end has no missing boundary. Besides
    # preserving its interpretation, this fast path avoids probing capitalized
    # names inside the overwhelmingly common correctly punctuated question.
    whole = analyze(fused, reg, tracing=False)
    whole_ask = match_ask(whole, reg)
    if whole_ask is not None and meaningful_uids(whole).issubset(
        whole_ask[2].consumed
    ):
        return None, fused

    # The capital is the only surface evidence that punctuation was omitted.
    # The grammar proofs below carry the semantic load.
    for boundary in list(re.finditer(r"\S+", fused))[1:]:
        token = boundary.group()
        if not token[:1].isupper():
            continue
        head = fused[: boundary.start()].strip()
        tail = fused[boundary.start() :].strip()
        if len(head.split()) < 3 or len(tail.split()) < 3:
            continue

        question = analyze(tail, reg, tracing=False)
        ask = match_ask(question, reg)
        if ask is None or not meaningful_uids(question).issubset(ask[2].consumed):
            continue

        premise = analyze(head, reg, tracing=False)
        content = meaningful_uids(premise)
        exact_fact_rule = any(
            result.facts and content.issubset(result.match.consumed)
            for result in run_rules(premise, reg, "read")
        )
        if not exact_fact_rule:
            continue

        promoted = head.rstrip(",;:").rstrip().rstrip(".") + "."
        return promoted, tail
    return None, fused


def split_question(text: str, reg: Registry | None = None) -> tuple[list[str], str | None]:
    sentences = split_sentences(text)
    if not sentences:
        return [], None
    last = sentences[-1]
    words = last.split()
    first_word = words[0] if words else ""
    is_question = last.endswith("?") or (
        reg is not None and _has_ask_cue_sense(first_word, reg)
    )
    # "If she worked 50 hours, calculate her total income." — no question
    # mark, no leading cue, but the post-comma part leads with one
    if not is_question and reg is not None and last.lower().startswith("if "):
        clause, rest = _split_leading_clause(last, reg)
        is_question = clause is not None
    # same shape, for a pack-registered temporal marker ("When she finds 4
    # shells, calculate her total.") instead of the literal 'if'
    if not is_question and reg is not None and _leading_temporal_marker(last, reg):
        clause, rest = _split_leading_temporal_clause(last, reg)
        is_question = clause is not None
    if not is_question:
        return sentences, None
    premises = sentences[:-1]
    if reg is not None:
        clause, last = _split_leading_clause(last, reg)
        if clause is None:
            clause, last = _split_leading_temporal_clause(last, reg)
        if clause is None:
            clause, last = _split_trailing_clause(last, reg)
        if clause is None:
            clause, last = _split_fused_premise_question(last, reg)
        if clause is not None:
            premises = premises + [clause]
    return premises, last


def solve(text: str, reg: Registry, tracing: bool = True) -> Result:
    """Read `text` and answer it.

    `tracing=False` skips snapshotting the reversible feature diffs in every
    Decision. Only the designer (`engine.trace`) and `Reading.undo` read those;
    a bench run does not, and the snapshotting is 61% of its wall-clock.

    It also skips the deictic journal, for the same reason and with the same effect:
    `deixis.resolve` takes the silent path when handed None, so bench pays nothing.
    """
    # the reader stage: LaTeX math spans transcribed to plain text BEFORE any
    # splitting/tokenization; non-LaTeX text passes through as the same object
    # (mathtext.py — whole-span conservatism, unrecognized spans stay verbatim)
    text = normalize_math(text)
    premise_texts, question_text = split_question(text, reg)
    expanded_premise_texts: list[str] = []
    for premise_text in premise_texts:
        expanded_premise_texts.extend(_split_conjoined_clauses(premise_text, reg))
    premises = [
        analyze(sentence, reg, sentence_index=i, tracing=tracing)
        for i, sentence in enumerate(expanded_premise_texts)
    ]
    journal = deixis.Journal() if tracing else None
    doc = run_document(premises, reg, journal=journal)

    if question_text is None:
        result = Result(
            Answer("decline", None, "no question found"),
            premises, None, doc.store, doc.log,
        )
        result.document = doc
        return result

    question = analyze(
        question_text, reg, sentence_index=len(expanded_premise_texts), tracing=tracing
    )
    # the question's own pronouns resolve against the document's discourse
    # exactly like premise pronouns: unique antecedent or stay unmet
    _bind_discourse(premises + [question], journal=journal, reg=reg)
    # only slots whose VALUE the consumer uses ({slot.value} templates)
    # count as read — matching "four-minute songs" as an item does NOT read
    # the four, and value accounting must still decline it
    from .patterns import match_ask as _match_ask

    matched_ask = _match_ask(question, reg)
    if matched_ask is not None:
        import re as _re

        value_slots = {
            m.group(1)
            for raw in matched_ask[0].resolves.values()
            for m in _re.finditer(r"\{(\w+)\.value\}", raw)
        }
        for slot_name, unit in matched_ask[2].slots.items():
            if isinstance(unit, tuple):
                continue  # a span slot carries no scalar value to consume
            if slot_name in value_slots:
                question.record(
                    "ask-consume", unit, {"pattern_consumed": True},
                    f"value consumed by ask {matched_ask[0].id}",
                )
    proposed = run_answer(question, doc.store, reg, doc.log, premises=premises)
    veto = run_guards(
        premises, doc.consumed_uids, doc.log, reg, proposed, doc.store, question,
        # the clause pre-split erases its boundary word from the readings, so
        # the verdict fragment guard must be told it happened (guards.py
        # _check_verdict — a promoted disjunct reads as an asserted fact)
        clause_split=len(expanded_premise_texts) != len(premise_texts),
    )
    if veto is not None:
        proposed = Answer("decline", None, f"[{veto.guard}] {veto.reason}")
    result = Result(proposed, premises, question, doc.store, doc.log, veto)
    result.document = doc
    return result


def diagnose(result: Result) -> dict:
    """The epistemic surface: why declined, what IS known, what would help."""
    kind = "answered"
    if not result.answer.committed and result.answer.kind != "verdict":
        unknown = [w for r in result.premises for w in r.unknown_words()]
        if result.question is not None:
            unknown += result.question.unknown_words()
        if unknown:
            kind = "unknown-word"
        elif any(u.features.get("ambiguous") for r in result.premises for u in r.units):
            kind = "ambiguous"
        elif result.store.collisions:
            kind = "conflict"
        else:
            kind = "insufficient"
    return {
        "answer": result.answer.value if result.answer.committed or result.answer.kind == "verdict" else None,
        "kind": kind,
        "reason": result.answer.reason,
        "known": [repr(f) for f in result.store.facts],
        "deficiencies": result.deficiencies(),
    }
