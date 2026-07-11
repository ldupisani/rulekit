"""The engine: analyze one sentence; solve a whole text.

solve() = premises + trailing question → parse each premise, run pattern
rules, learn facts, saturate, answer, guard. Every step auditable via the
decision trace; the result carries the full epistemic surface (answer OR
why-not + what IS known).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.registry import Registry
from .answer import Answer, answer as run_answer
from .condense import condense
from .document import Document, _bind_discourse, run_document
from .evaluate import ArithmeticLog
from .facts import FactStore
from .guards import GuardVeto, check as run_guards
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


def analyze(sentence: str, reg: Registry, sentence_index: int = 0) -> Reading:
    reading = tokenize(sentence, sentence_index)
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
    non-premise to a premise."""
    if not question.rstrip().endswith("?"):
        return None, question
    parts = question.split(",")
    if len(parts) < 2:
        return None, question
    split_at = None
    for i in range(len(parts) - 1):
        rest = ",".join(parts[i + 1 :]).strip()
        first = rest.split()[0].lower() if rest.split() else ""
        if first == "if":
            split_at = i  # keep the LAST such boundary
    if split_at is None:
        return None, question
    wh_part = ",".join(parts[: split_at + 1]).strip()
    clause_rest = ",".join(parts[split_at + 1 :]).strip()
    clause_body = clause_rest[2:].strip().rstrip("?").rstrip(".").strip()
    if not clause_body or not any(ch.isdigit() for ch in clause_body):
        return None, question
    if not wh_part.endswith("?"):
        wh_part = wh_part.rstrip(".") + "?"
    return clause_body + ".", wh_part


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
        if clause is not None:
            premises = premises + [clause]
    return premises, last


def solve(text: str, reg: Registry) -> Result:
    premise_texts, question_text = split_question(text, reg)
    premises = [
        analyze(sentence, reg, sentence_index=i)
        for i, sentence in enumerate(premise_texts)
    ]
    doc = run_document(premises, reg)

    if question_text is None:
        result = Result(
            Answer("decline", None, "no question found"),
            premises, None, doc.store, doc.log,
        )
        result.document = doc
        return result

    question = analyze(question_text, reg, sentence_index=len(premise_texts))
    # the question's own pronouns resolve against the document's discourse
    # exactly like premise pronouns: unique antecedent or stay unmet
    _bind_discourse(premises + [question])
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
            if slot_name in value_slots:
                question.record(
                    "ask-consume", unit, {"pattern_consumed": True},
                    f"value consumed by ask {matched_ask[0].id}",
                )
    proposed = run_answer(question, doc.store, reg, doc.log)
    veto = run_guards(
        premises, doc.consumed_uids, doc.log, reg, proposed, doc.store, question
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
