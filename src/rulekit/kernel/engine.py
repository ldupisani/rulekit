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
from .document import Document, run_document
from .evaluate import ArithmeticLog
from .facts import FactStore
from .guards import GuardVeto, check as run_guards
from .model import Fact, Reading
from .numbers import annotate_numbers
from .obligations import attach_obligations, bind, disambiguate
from .senses import annotate_senses
from .tokenize import split_sentences, tokenize

QUESTION_WORDS = {"how", "what", "who", "which", "is", "are", "does", "do", "did"}


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


def split_question(text: str) -> tuple[list[str], str | None]:
    sentences = split_sentences(text)
    if not sentences:
        return [], None
    last = sentences[-1]
    first_word = last.split()[0].lower().rstrip(",") if last.split() else ""
    if last.endswith("?") or first_word in QUESTION_WORDS:
        return sentences[:-1], last
    return sentences, None


def solve(text: str, reg: Registry) -> Result:
    premise_texts, question_text = split_question(text)
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
    proposed = run_answer(question, doc.store, reg, doc.log)
    veto = run_guards(premises, doc.consumed_uids, doc.log, reg, proposed, doc.store)
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
