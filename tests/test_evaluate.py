import pytest

from rulekit.kernel.evaluate import (
    ArithmeticLog,
    EvaluationError,
    evaluate,
    run_program,
)


def test_basic_arithmetic():
    assert evaluate("2 + 3 * 4", {}) == 14
    assert evaluate("(10 - 4) / 3", {}) == 2
    assert evaluate("-5 + abs(-2)", {}) == -3


def test_variables():
    assert evaluate("n * sign", {"n": 3, "sign": -1}) == -3


def test_unbound_variable_errors():
    with pytest.raises(EvaluationError):
        evaluate("x + 1", {})


def test_no_eval_escape():
    for evil in [
        "__import__('os').system('true')",
        "().__class__",
        "[1][0]",
        "'a' + 'b'",
        "lambda: 1",
    ]:
        with pytest.raises(EvaluationError):
            evaluate(evil, {})


def test_program():
    assert run_program("a = 3\nb = a * 4\nanswer = b - 2") == 10


def test_log_uses_value():
    log = ArithmeticLog()
    evaluate("3 + 4", {}, log, source="test")
    assert log.uses_value(3)
    assert log.uses_value(4)
    assert not log.uses_value(5)
    evaluate("x * 2", {"x": 7}, log, source="test")
    assert log.uses_value(7)
