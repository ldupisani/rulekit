"""Engine behavior over synthetic strings (NEVER benchmark items)."""

from rulekit.kernel.engine import analyze, diagnose, solve
from rulekit.kernel.model import Quantity


def _value(text, registry):
    return solve(text, registry).answer.value


def test_simple_quantity(registry):
    assert _value("Tom has 3 apples. How many apples does Tom have?", registry) == 3


def test_word_number_and_plural(registry):
    assert _value("Tom has seven apples. How many apples does Tom have?", registry) == 7


def test_comma_number(registry):
    assert _value("Mary has 1,200 stickers. How many stickers does Mary have?", registry) == 1200


def test_signed_accumulation(registry):
    text = "Tom has 10 coins. Tom finds 3 coins. Tom lost 2 coins. How many coins does Tom have?"
    assert _value(text, registry) == 11


def test_relation_resolution(registry):
    text = "Tom has 3 apples. Mary has 2 more apples than Tom. How many apples does Mary have?"
    assert _value(text, registry) == 5


def test_relation_chain_saturates(registry):
    text = (
        "Tom has 2 cards. Mary has 3 more cards than Tom. "
        "Sue has twice as many cards as Mary. How many cards does Sue have?"
    )
    assert _value(text, registry) == 10


def test_negation_is_an_obligation_not_a_flag(registry):
    # the difg #26 lesson: "not" must BIND its verb, never a global flag
    r = solve("Bob is not a student. Is Bob a student?", registry)
    assert r.answer.value == "no"
    r = solve("Bob is a student. Is Bob a student?", registry)
    assert r.answer.value == "yes"


def test_unknown_word_declines_with_nonce(registry):
    # nonce word pins the unknown-word invariant as the lexicon grows
    r = solve("Tom has 3 wugs. How many wugs does Tom have?", registry)
    assert r.answer.kind == "decline"
    assert any("wugs" in d for d in r.deficiencies())


def test_sense_disambiguation_by_coverage(registry):
    reading = analyze("The rose wilted.", registry)
    rose = next(u for u in reading.units if "rose" in u.features.get("fold", ""))
    assert rose.senses() == ["noun"]


def test_name_vs_known_word(registry):
    # "Rose" without an article is a name; "the rose" is the flower
    reading = analyze("Is Rose a teacher?", registry)
    rose = next(u for u in reading.units if u.features.get("fold") == "rose")
    assert rose.senses() == ["name"]


def test_facts_carry_provenance(registry):
    r = solve("Tom has 3 apples. How many apples does Tom have?", registry)
    quantities = [f for f in r.store.facts if isinstance(f, Quantity)]
    assert quantities and quantities[0].provenance.source == "fold"


def test_pattern_rule_attribution(registry):
    r = solve(
        "Tom has 3 apples. Mary has 2 more apples than Tom. "
        "How many apples does Mary have?",
        registry,
    )
    sources = {f.provenance.source for f in r.store.facts}
    assert "arithmetic/anchored-relation" in sources


def test_trace_is_serializable(registry):
    import json

    r = solve("Tom has 3 apples. How many apples does Tom have?", registry)
    events = r.trace()
    assert events
    json.dumps(events)  # must not raise
    kinds = {e["kind"] for e in events}
    assert "annotate-number" in kinds and "bind" in kinds


def test_diagnose_unknown_word(registry):
    r = solve("Tom has 3 gribbles. How many gribbles does Tom have?", registry)
    d = diagnose(r)
    assert d["kind"] == "unknown-word"


def test_undo_restores_state(registry):
    reading = analyze("Tom has 3 apples.", registry)
    unit = reading.units[0]
    before = dict(unit.features)
    decision = reading.record("test", unit, {"senses": ["verb"]}, "test mutation")
    assert unit.features["senses"] == ["verb"]
    reading.undo(decision)
    assert unit.features == before
