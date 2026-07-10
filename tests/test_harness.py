from rulekit.harness.snapshot import diff


def _snap(**outcomes):
    return {
        "fingerprint": "x",
        "items": {k: {"outcome": v, "got": None} for k, v in outcomes.items()},
    }


def test_ship_gate_blocks_broke():
    d = diff(_snap(a="correct", b="declined"), _snap(a="declined", b="correct"))
    assert d.broke == ["a"] and d.solved == ["b"]
    assert d.verdict() == "REVERT"


def test_ship_gate_blocks_decl_to_wrong():
    d = diff(_snap(a="declined"), _snap(a="wrong"))
    assert d.decl_to_wrong == ["a"]
    assert d.verdict() == "REVERT"


def test_neutral_for_pure_refactor():
    d = diff(_snap(a="correct", b="declined"), _snap(a="correct", b="declined"))
    assert d.verdict() == "NEUTRAL"


def test_ship_on_clean_gain():
    d = diff(_snap(a="correct", b="declined"), _snap(a="correct", b="correct"))
    assert d.verdict() == "SHIP"
