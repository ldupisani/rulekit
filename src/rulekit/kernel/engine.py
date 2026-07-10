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
ASK_CUE_SENSES = frozenset({"interrogative", "auxiliary", "imperative"})


def _has_ask_cue_sense(word: str, reg: Registry) -> bool:
    entry = reg.lexicon.get(word.lower().rstrip(",?"))
    return entry is not None and bool(set(entry.senses) & ASK_CUE_SENSES)


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
    if not is_question:
        return sentences, None
    premises = sentences[:-1]
    if reg is not None:
        clause, last = _split_leading_clause(last, reg)
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
