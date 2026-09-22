"""Invented regression cases for shared rate-query and evidence contracts."""

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.data.schemas import AskRule, VerbRolesCompatibilityPredicate, WherePredicate
from rulekit.generation.sample import _Filler, _selectional_assignment_compatible
from rulekit.generation.ask_generation import _ask_filler_satisfies_known_where


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def project(request):
    return load_project("projects/" + request.param)


CHAIN = (
    "Each bird eats 7 apricots per day. Each snake eats 2 birds per day. "
    "Each jaguar eats 4 snakes per day. There are 3 jaguars in a garden. "
)


@pytest.mark.parametrize("ask,value", [
    ("How many apricots does a bird eat in 2 days?", 14),
    ("How many apricots can a bird eat in 2 days?", 14),
    ("How many apricots do the birds eat in 2 days?", 336),
    ("How many apricots can the birds eat in 2 days?", 336),
])
def test_modal_and_ordinary_asks_keep_the_same_member_scope(project, ask, value):
    result = solve(CHAIN + ask, project.registry)
    assert result.value == value, result.answer


@pytest.mark.parametrize("ask", [
    "How many hours will it take Aven to {verb} 18 pages?",
    "How many hours will it take Aven to {verb} all of the pages?",
])
def test_inverse_asks_cannot_borrow_another_activity_rate(project, ask):
    premises = "Aven reads 6 pages per hour. "
    if "all of" in ask:
        premises += "Aven has 18 pages. "
    positive = solve(premises + ask.format(verb="read"), project.registry)
    assert positive.value == 3, positive.answer
    negative = solve(premises + ask.format(verb="write"), project.registry)
    assert negative.answer.kind == "decline", negative.answer


@pytest.mark.parametrize("item", ["18 pages", "all of the pages"])
def test_implicit_duration_unit_preserves_activity(item):
    # This project's lexicon includes the implicit-unit ask's adjective.
    registry = load_project("projects/gsm8k").registry
    premises = "Aven reads 6 pages per hour. "
    if item.startswith("all"):
        premises += "Aven has 18 pages. "
    assert solve(premises + f"How long will it take Aven to read {item}?", registry).value == 3
    assert solve(premises + f"How long will it take Aven to write {item}?", registry).answer.kind == "decline"


def test_every_legacy_rate_ask_declares_scope_and_activity(project):
    asks = [a for a in project.registry.asks
            if a.resolves.get("consumer") in {"rate-span", "rate-span-inverse"}]
    assert len(asks) == 10
    for ask in asks:
        for name in ("subject_number", "entity_owner", "entity_qualifier", "verb"):
            assert "evidence_" + name in ask.resolves, ask.id
        if ask.resolves.get("measure") == "{item}" or "item" in ask.resolves:
            for name in ("measure_owner", "measure_qualifier"):
                assert "evidence_" + name in ask.resolves, ask.id


def test_rate_activity_aliases_are_licensed_by_the_object_category(project):
    premises = "Aven earns 9 dollars per hour. Aven works 4 hours. "
    assert solve(premises + "How much does Aven make?", project.registry).value == 36
    assert solve(premises + "How much does Aven spend?", project.registry).answer.kind == "decline"
    nonmonetary = solve("Aven makes 9 toys per hour. How many toys does Aven earn in 4 hours?",
                        project.registry)
    assert nonmonetary.answer.kind == "decline", nonmonetary.answer


@pytest.mark.parametrize("ask", [
    "How many apricots can the birds eat in 2 days?",
    "How many apricots do the birds eat in 2 days?",
])
def test_missing_population_never_defaults_a_plural_ask_to_one(project, ask):
    result = solve("Each bird eats 7 apricots per day. " + ask, project.registry)
    assert result.answer.kind == "decline", result.answer


@pytest.mark.parametrize("ask", [
    "How many apricots does a bird eat in 2 days?",
    "How many apricots can a bird eat in 2 days?",
    "How many days will it take a bird to eat 14 apricots?",
])
def test_a_collective_rate_does_not_supply_an_individual_quota(project, ask):
    result = solve("Birds eat 7 apricots per day. " + ask, project.registry)
    assert result.answer.kind == "decline", result.answer


def test_inverse_collective_ask_needs_a_collective_rate(project):
    ask = "How many days will it take the birds to eat 21 apricots?"
    assert solve("Birds eat 7 apricots per day. " + ask, project.registry).value == 3
    assert solve("A bird eats 7 apricots per day. " + ask, project.registry).answer.kind == "decline"


def test_collective_rate_cannot_be_multiplied_as_if_it_were_per_member(project):
    result = solve("Birds eat 7 apricots per day. Aven has 3 birds. "
                   "How many apricots do the birds eat in 2 days?", project.registry)
    assert result.answer.kind == "decline", result.answer


def test_compound_rate_keeps_raw_operands_with_multiple_holders(project):
    result = solve(
        "A bird eats 7 apricots in 2 days. Aven has 3 birds. Bira has 5 birds. "
        "How many apricots do the birds eat in 4 days?", project.registry,
    )
    assert result.value == 112, result.answer
    assert result.log.uses_value(7)
    assert result.log.uses_value(2)


def test_compound_rate_cannot_hide_a_conflicting_population(project):
    result = solve(
        "A bird eats 7 apricots in 2 days. Aven has 3 birds. Bira has 5 birds. "
        "Aven has 11 birds. How many apricots do the birds eat in 4 days?",
        project.registry,
    )
    assert result.answer.kind == "decline", result.answer


def test_compound_active_period_bridge_uses_shared_rate_arithmetic(project):
    from rulekit.kernel.consumers import ConsumerContext
    from rulekit.kernel.consumers.rate_span import rate_span
    from rulekit.kernel.evaluate import ArithmeticLog
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.model import Provenance, Rate

    store = FactStore()
    store.admit(Rate(Provenance("invented/rate", 0), "aven", "page", "hour", 7, "read"))
    store.admit(Rate(Provenance("invented/active-periods", 1), "aven", "hour", "day",
                     1.5, "read", numerator=3, denominator=2))
    ctx = ConsumerContext(
        {"entity": "aven", "measure": "page", "verb": "read", "span_unit": "day", "span_value": "4"},
        None, store, project.registry, ArithmeticLog(), None, None,
    )
    answer = rate_span(ctx)
    assert answer.value == 42, answer
    assert ctx.log.uses_value(3)
    assert ctx.log.uses_value(2)


@pytest.mark.parametrize("surface,number,kind,permissions,expected", [
    ("bird", "singular", "noun", {}, False),
    ("birds", "plural", "noun", {}, True),
    ("they", "plural", "pronoun", {}, False),
    ("they", "plural", "pronoun", {"allow_plural_pronoun": ["item"]}, True),
    ("he", "singular", "pronoun", {"allow_plural_pronoun": ["item"]}, False),
    ("stones", "plural", "noun", {"allow_plural_pronoun": ["item"]}, False),
    ("stones", "plural", "noun", {"allow_plural_class": ["item"]}, True),
    ("Bira", "singular", "name", {"allow_proper_name": ["item"]}, False),
])
def test_ask_and_premise_generation_share_role_contract(
    project, surface, number, kind, permissions, expected,
):
    contract = VerbRolesCompatibilityPredicate(
        verb="verb", roles={"theme": ["item"]},
        frame_categories=["livestock_raising_quantity_verb"],
        require_declared_frame=True, **permissions,
    )
    ask = AskRule(id="invented/role-contract", match={"question": [
        {"slot": "verb", "type": "verb"}, {"slot": "item", "type": "entity"},
    ]}, where=[WherePredicate(verb_roles_compatible=contract)],
        resolves={"consumer": "unused"})
    verb = _Filler("raise", "raise", kind="verb")
    item = _Filler(surface, project.registry.plural_to_singular.get(surface, surface),
                   number=number, kind=kind)
    assert _selectional_assignment_compatible(verb, {"item": item}, contract, project.registry) is expected
    assert _ask_filler_satisfies_known_where(project, ask, "item", item, {"verb": verb}) is expected
    # Selecting the verb last must make the same decision.
    assert _ask_filler_satisfies_known_where(project, ask, "verb", verb, {"item": item}) is expected
    # An unchosen role is undecided, not rejected as missing.
    assert _ask_filler_satisfies_known_where(project, ask, "verb", verb, {})


def test_role_frame_cache_does_not_erase_surface_only_membership():
    from types import SimpleNamespace

    registry = SimpleNamespace(
        fingerprint="invented-surface-only-role-contract",
        selectional_frames=lambda word: (("frame", {"theme": "object"}),) if word == "gleams" else (),
        selectional_role_number=lambda category, role: None,
        word_in_category=lambda word, category: word == "stone" and category == "object",
    )
    contract = VerbRolesCompatibilityPredicate(
        verb="verb", roles={"theme": ["item"]}, require_declared_frame=True,
    )
    roles = {"item": _Filler("stone", "stone")}
    assert _selectional_assignment_compatible(_Filler("gleams", "gleam"), roles, contract, registry)
    assert not _selectional_assignment_compatible(_Filler("gleam", "gleam"), roles, contract, registry)
