"""Pre-tokenization reader for LaTeX math spans (the "reader stage").

Sits UPSTREAM of the pipeline: `solve()` hands raw text through
`normalize_math` before sentence splitting, so everything downstream —
tokenize, numbers, senses — still only annotates the surface it receives.
The tokenizer's "annotate, don't transform" invariant governs the pipeline;
this stage is a raw-text -> engine-text transcription, the same relation
`build_corpus.py` has to what text the engine sees.

Two rules make it safe:

1. IDENTITY FAST PATH. Text with no backslash-command (`\\` + letter) is
   returned as the SAME OBJECT — no grade-school corpus contains one, so
   GSM8K/ASDiv/SVAMP/MAWPS/FOLIO provably pass through untouched (the unit
   test asserts object identity, the ship gate asserts zero changed items).

2. WHOLE-SPAN CONSERVATISM. Only a `$...$` span in which EVERY construct is
   recognized is rewritten; one unknown command and the span stays verbatim,
   where the tokenizer shreds it into counts that value-accounting cannot
   consume and the item DECLINES exactly as it did before this module
   existed. Precision before coverage, made structural: the reader can only
   move an item declined -> {readable}, never silently misread it.

Recognized constructs (each a CLASS measured on scibench dev, none a
word-specific fact — unit MEANINGS live in packs, this strips markup only):
numbers; `\\times 10^{k}` scientific notation (folded into a plain decimal,
never e-notation, so numbers.py reads it unchanged); `\\mathrm{~X}` unit
symbols (markup stripped, symbol emitted bare); `^{\\circ}` -> "degrees";
numeric `\\frac{a}{b}` -> "a/b"; Greek commands -> the Unicode letter;
`\\mathrm` groups with numeric subscripts fused into a chemical formula
("C2H6"); LaTeX spacing. Deliberately ABSENT: unit exponents
(`\\mathrm{dm}^3`, `m/s^2`) — that is the `_TOKEN` compound-unit change
(formulas.yaml flags it), a separate bought increment.
"""

from __future__ import annotations

import re
from decimal import Decimal

# the identity fast path: no LaTeX signature, no work (and no new string).
# A backslash-command OR a braced superscript — "$10^{6}$" spans carry no
# backslash — and neither substring occurs in grade-school prose
_HAS_COMMAND = re.compile(r"\\[A-Za-z]|\^\{")

# a $...$ math span (single dollars; content never contains a dollar)
_SPAN = re.compile(r"\$([^$]+)\$")

_GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ",
    "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "chi": "χ",
    "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ",
    "Omega": "Ω",
}

# one construct per branch; _rewrite_span consumes the span with these and
# whitespace ONLY — any residue means the span is not fully recognized
_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")
_TIMES_POW10 = re.compile(r"\\times\s*10\^(?:\{([-+]?\d+)\}|([-+]?\d))")
_POW10 = re.compile(r"10\^(?:\{([-+]?\d+)\}|([-+]?\d))")
_MATHRM = re.compile(r"\\mathrm\{\s*~?\s*([A-Za-z]+)\s*\}")
_SUBSCRIPT = re.compile(r"_(?:\{(\d+)\}|(\d))")
_DEGREE = re.compile(r"\^\{\\circ\}")
_FRAC = re.compile(r"\\frac\{(\d+)\}\{(\d+)\}")
_GREEK_CMD = re.compile(r"\\([A-Za-z]+)")
_SPACING = re.compile(r"~|\\[,;!]|\\quad|\\ ")


def _pow10(number: str, exponent: str) -> str:
    """Fold `number * 10**exponent` into one plain decimal (never e-notation)."""
    value = Decimal(number) * (Decimal(10) ** int(exponent))
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _rewrite_span(span: str) -> str | None:
    """One `$...$` interior -> normalized text, or None if any construct is unknown."""
    out: list[str] = []
    pos = 0
    length = len(span)
    while pos < length:
        ch = span[pos]
        if ch.isspace():
            pos += 1
            continue
        if m := _SPACING.match(span, pos):
            pos = m.end()
            continue
        if m := _DEGREE.match(span, pos):
            out.append("degrees")
            pos = m.end()
            continue
        if m := _FRAC.match(span, pos):
            out.append(f"{m.group(1)}/{m.group(2)}")
            pos = m.end()
            continue
        if m := _MATHRM.match(span, pos):
            # fuse consecutive symbol+subscript groups into one chemical
            # formula token ("\mathrm{C}_2 \mathrm{H}_6" -> "C2H6"); a lone
            # group is just its bare symbol ("\mathrm{~mol}" -> "mol")
            piece = m.group(1)
            pos = m.end()
            fused = False
            while True:
                if s := _SUBSCRIPT.match(span, pos):
                    piece += s.group(1) or s.group(2)
                    pos = s.end()
                    fused = True
                    continue
                rest = span[pos:]
                stripped = rest.lstrip()
                if fused and (n := _MATHRM.match(stripped)):
                    piece += n.group(1)
                    pos += len(rest) - len(stripped) + n.end()
                    continue
                break
            # an exponent on the unit ("\mathrm{dm}^3") is the compound-unit
            # class this module deliberately does not read
            if span[pos : pos + 1] == "^":
                return None
            out.append(piece)
            continue
        # before the generic number branch: its `\d+` would otherwise take the
        # "10" of a bare power of ten and strand the caret
        if m := _POW10.match(span, pos):
            out.append(_pow10("1", m.group(1) or m.group(2)))
            pos = m.end()
            continue
        if m := _NUMBER.match(span, pos):
            number = m.group()
            pos = m.end()
            tail = span[pos:]
            stripped = tail.lstrip()
            if t := _TIMES_POW10.match(stripped):
                number = _pow10(number, t.group(1) or t.group(2))
                pos += len(tail) - len(stripped) + t.end()
            out.append(number)
            continue
        if m := _GREEK_CMD.match(span, pos):
            letter = _GREEK.get(m.group(1))
            if letter is None:
                return None
            out.append(letter)
            pos = m.end()
            continue
        return None
    return " ".join(out) if out else None


def normalize_math(text: str) -> str:
    """Rewrite fully-recognized `$...$` math spans; leave everything else alone."""
    if not _HAS_COMMAND.search(text):
        return text

    def replace(match: re.Match[str]) -> str:
        rewritten = _rewrite_span(match.group(1))
        return match.group(0) if rewritten is None else rewritten

    return _SPAN.sub(replace, text)
