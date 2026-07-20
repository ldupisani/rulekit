"""The LaTeX reader stage (kernel/mathtext.py). Synthetic strings only.

The two properties that make the reader safe are the ones under test:
identity (non-LaTeX text is returned as the SAME OBJECT — the five
non-scibench corpora provably pass through untouched) and whole-span
conservatism (one unrecognized construct leaves the span verbatim, where
it declines exactly as before the reader existed).
"""

import pytest

from rulekit.kernel.mathtext import normalize_math


class TestIdentityFastPath:
    # representative grade-school shapes: currency, percent, ISO date,
    # thousands commas, curly apostrophe, hyphen range — every one must come
    # back as the same object, not merely an equal string
    @pytest.mark.parametrize(
        "text",
        [
            "Tom has $5 and buys 3 apples for $1.50 each.",
            "She scored 50% on 2024-01-01, up from 1,234 points.",
            "Gould’s 21st try covered 5-10 miles in 3/4 of an hour.",
            "A plain sentence with no numbers at all.",
            "",
        ],
    )
    def test_plain_text_is_same_object(self, text):
        assert normalize_math(text) is text

    def test_dollar_amounts_without_commands_untouched(self):
        # `$27$` has no backslash-command, so even a dollar-wrapped number
        # takes the fast path
        text = "The prize is $27$ dollars, split between $3 and $24."
        assert normalize_math(text) is text


class TestRecognizedConstructs:
    def test_scientific_notation_folds_to_plain_decimal(self):
        got = normalize_math(r"It stores $3.5 \times 10^{6} \mathrm{~J}$ of heat.")
        assert got == "It stores 3500000 J of heat."

    def test_negative_exponent_never_e_notation(self):
        got = normalize_math(r"A charge of $1.6 \times 10^{-4} \mathrm{~g}$ remains.")
        assert got == "A charge of 0.00016 g remains."
        assert "e" not in got.split()[3].lower()

    def test_mathrm_unit_symbol_stripped(self):
        got = normalize_math(r"Add $10.0 \mathrm{~mol}$ of gas.")
        assert got == "Add 10.0 mol of gas."

    def test_degree_celsius(self):
        got = normalize_math(r"Heated to $27^{\circ} \mathrm{C}$ overnight.")
        assert got == "Heated to 27 degrees C overnight."

    def test_numeric_frac(self):
        got = normalize_math(r"Only $\frac{1}{4}$ of the tank is full.")
        assert got == "Only 1/4 of the tank is full."

    def test_greek_letter(self):
        got = normalize_math(r"The wavelength $\lambda$ is measured.")
        assert got == "The wavelength λ is measured."

    def test_chemical_formula_fuses(self):
        got = normalize_math(r"A tank of $\mathrm{C}_2 \mathrm{H}_6$ leaks.")
        assert got == "A tank of C2H6 leaks."

    def test_standalone_power_of_ten(self):
        got = normalize_math(r"About $10^{3}$ students attended.")
        assert got == "About 1000 students attended."

    def test_spacing_commands_collapse(self):
        got = normalize_math(r"A mass of $12\,\mathrm{kg}$ was weighed.")
        assert got == "A mass of 12 kg was weighed."


class TestWholeSpanConservatism:
    def test_unknown_command_leaves_span_verbatim(self):
        text = r"The rate is $\int_0^t k\,dt$ overall."
        assert normalize_math(text) == text

    def test_mixed_known_and_unknown_leaves_span_verbatim(self):
        # \mathrm is recognized, \left( is not -> the WHOLE span stays
        text = r"Given $5 \mathrm{~kg} \left(\right)$ of ore."
        assert normalize_math(text) == text

    def test_unit_exponent_is_the_compound_unit_class_not_read(self):
        # formulas.yaml's deliberately-absent class: exponent on the unit
        text = r"Confined to $4.86 \mathrm{dm}^3$ at noon."
        assert normalize_math(text) == text

    def test_equation_leaves_span_verbatim(self):
        text = r"Use $\frac{1}{R}=\frac{1}{R_1}$ here."
        assert normalize_math(text) == text

    def test_only_recognized_spans_rewrite_others_stay(self):
        text = r"Take $2.0 \mathrm{~g}$ from $4.86 \mathrm{dm}^3$ of stock."
        got = normalize_math(text)
        assert got == r"Take 2.0 g from $4.86 \mathrm{dm}^3$ of stock."

    def test_unpaired_dollar_untouched(self):
        text = r"A stray \mathrm{g} outside any span."
        assert normalize_math(text) == text


class TestEndToEnd:
    def test_latex_word_problem_reads_through_solve(self):
        # a synthetic problem whose LaTeX normalizes to text the arithmetic
        # machinery already reads — the reader is the only new link in the chain
        from pathlib import Path

        from rulekit.data.project import load_project
        from rulekit.kernel.engine import solve

        reg = load_project(Path("projects/gsm8k")).registry
        text = r"Ann has $3 \times 10^{1}$ hats. How many hats does Ann have?"
        result = solve(text, reg, tracing=False)
        assert result.answer.kind == "number"
        assert result.answer.value == 30
