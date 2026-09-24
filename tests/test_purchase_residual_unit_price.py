"""Invented complete-purchase equations with one equal-price unknown lot."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import (
    Expenditure, LocationEvent, Membership, Predication, Price, PurchaseTotal,
    QuantityEventContext, ResourceAccountingIssue, VerbalRelation,
)


@pytest.fixture(scope="module", params=["curated", "gsm8k"])
def project(request):
    return load_project(Path("projects") / request.param)


def basket(*, total=90, count=6, buyer="Aven", equal=", all at the same price"):
    return (f"For ${total} {buyer} bought 3 pairs of socks for $8 each "
            f"and 2 pairs of shoes for $15 each. "
            f"{buyer} also bought {count} hats{equal}. ")


ASK = "How much did each hat cost?"


@pytest.mark.parametrize("opening", [
    "Aven got some bonus pay.", "Aven has some money.", "Aven is a shopper.",
    "Aven is out shopping.", "Aven is a person.", "Aven did some things.",
    "Aven is in town.", "We are observing Aven.", "Aven takes the following actions.",
])
def test_background_introductions_do_not_have_to_be_purchase_frames(project, opening):
    result = solve(opening + " " + basket(buyer="she") + ASK, project.registry)
    assert result.answer.value == 6, result.answer
    assert result.store.by_kind(PurchaseTotal)[0].entity == "aven"
    assert {e.entity for e in result.store.by_kind(Expenditure)} == {"aven"}
    if opening.startswith("We "):
        # The observer group is unresolved, but is not the buyer. Preserve
        # that gap rather than inventing a participant to make the UI green.
        assert any("refers" in gap for gap in result.deficiencies())
        assert not result.store.by_kind(Predication)
    else:
        assert not result.deficiencies()


@pytest.mark.parametrize("object_word,lemma", [("things", "thing"), ("stuff", "stuff")])
@pytest.mark.parametrize("copula", ["is", "was"])
def test_generic_progressive_activity_is_background_not_class_membership(project, object_word, lemma, copula):
    result = solve(f"Aven {copula} doing {object_word}. " + basket(buyer="she") + ASK,
                   project.registry)
    assert result.answer.value == 6, result.answer
    assert not result.deficiencies()
    assert result.store.by_kind(PurchaseTotal)[0].entity == "aven"
    background = [f for f in result.store.facts if f.provenance.sentence == 0]
    assert len(background) == 1
    predicate = background[0]
    assert isinstance(predicate, Predication)
    assert (predicate.subject, predicate.verb, predicate.dobj) == ("aven", "do", lemma)
    assert not result.store.by_kind(Membership)
    step = next(s for s in result.answer.proof.steps if s.rule == "purchase-background")
    assert predicate in step.evidence


@pytest.mark.parametrize("opening,kind", [
    ("Aven is a shopper.", Membership), ("Aven is in town.", VerbalRelation),
    ("Aven got some bonus pay.", Predication), ("Aven has some money.", Predication),
    ("Aven is out shopping.", Predication), ("Aven takes the following actions.", Predication),
])
def test_background_is_preserved_in_the_store_and_purchase_proof(project, opening, kind):
    result = solve(opening + " " + basket() + ASK, project.registry)
    assert result.answer.value == 6, result.answer
    background = [s for s in result.answer.proof.steps if s.rule == "purchase-background"]
    assert len(background) == 1
    assert any(isinstance(f, kind) for f in background[0].evidence)
    assert all(f in result.store.facts for f in background[0].evidence)
    assert all(f.provenance.sentence == 0 for f in background[0].evidence)


def test_location_is_not_class_membership(project):
    result = solve("Aven is in town. " + basket() + ASK, project.registry)
    assert not result.store.by_kind(Membership)
    relation, = result.store.by_kind(VerbalRelation)
    assert (relation.entity, relation.obj, relation.role) == ("aven", "town", "spatial-location")
    event, = result.store.by_kind(LocationEvent)
    assert (event.entity, event.place, event.effect) == ("aven", "town", "holds")


def test_nominal_income_does_not_become_a_payment(project):
    result = solve("Aven got some bonus pay. " + basket() + ASK, project.registry)
    predication, = result.store.by_kind(Predication)
    assert (predication.subject, predication.verb, predication.dobj) == ("aven", "get", "pay")
    assert not any(e.provenance.sentence == 0 for e in result.store.by_kind(Expenditure))
    issue, = result.store.by_kind(ResourceAccountingIssue)
    assert (issue.reason, issue.domain) == ("additional-change", "balance")


@pytest.mark.parametrize("ask", [
    "How much will Aven pay in all?", "How much did she pay for everything?",
])
def test_income_noun_does_not_steal_auxiliary_payment_predicates(project, ask):
    result = solve("Aven bought 3 toys that each cost $4. Aven gets a 25% discount. " + ask,
                   project.registry)
    assert result.answer.value == 9, result.answer
    assert next(u for u in result.question.units if u.surface == "pay").sense() == "verb"


@pytest.mark.parametrize("opening", [
    "Aven got a discount.", "Aven got a refund.", "Aven has a fee.", "Aven has a tax.",
    "Aven paid some money.", "Aven bought a book.", "Aven ordered a book.",
    "Aven has $100.", "Aven received $100.", "Aven has 3 books.",
    "Aven has a budget of $100.", "Aven might have some money.",
    "Aven has some xyzzynonsense.", "Aven and Bira are shoppers.",
    "We are observing Aven and Bira.",
])
def test_background_partition_does_not_hide_relevant_or_ambiguous_evidence(project, opening):
    result = solve(opening + " " + basket(buyer="she") + ASK, project.registry)
    assert not result.answer.committed, result.answer


def test_unquantified_cash_still_blocks_a_cash_balance_query(project):
    ledger = ("Aven has a budget of $90. Aven spent $30 on a book. "
              "Aven bought a hat. Aven has $20 left from her budget. "
              "How much did Aven pay for the hat?")
    assert solve(ledger, project.registry).answer.value == 40
    result = solve(ledger.replace("Aven spent", "Aven has some money. Aven spent"), project.registry)
    assert not result.answer.committed
    assert any(f.domain == "balance" for f in result.store.by_kind(ResourceAccountingIssue))


def test_background_after_the_transaction_is_not_implicitly_outside_its_scope(project):
    for continuation in ["Aven has some money.", "Aven is a shopper.", "Aven is in town."]:
        result = solve(basket() + continuation + " " + ASK, project.registry)
        assert not result.answer.committed, result.answer


@pytest.mark.parametrize("total,count,expected", [(90, 6, 6), (94, 8, 5), (64.5, 3, 3.5), (54, 6, 0)])
def test_residual_common_unit_price(project, total, count, expected):
    result = solve(basket(total=total, count=count) + ASK, project.registry)
    assert result.answer.value == expected, result.answer
    assert not result.deficiencies()
    assert {s.rule for s in result.answer.proof.steps} == {
        "transaction-envelope", "known-purchase-costs", "residual-equal-unit-price",
    }


def test_pair_prices_preserve_item_scope_and_source_operands(project):
    result = solve(basket() + ASK, project.registry)
    assert result.answer.value == 6, result.answer
    expenses = result.store.by_kind(Expenditure)
    assert [(e.item, e.quantity, e.unit_price, e.lot_measure) for e in expenses[:2]] == [
        ("sock", 3, 8, "pair"), ("shoe", 2, 15, "pair"),
    ]
    prices = result.store.by_kind(Price)
    assert {(p.item, p.value) for p in prices} == {("pair[sock]", 8), ("pair[shoe]", 15)}
    unknown = expenses[-1]
    assert unknown.uniform_price and unknown.lot_quantity == 6
    assert isinstance(unknown.lot_position, int) and isinstance(unknown.event, int)
    assert result.store.by_kind(PurchaseTotal)[0].entity == "aven"


@pytest.mark.parametrize("transform,ask,expected", [
    (lambda s: s.replace("pairs of socks", "books").replace("pairs of shoes", "balls"), ASK, 6),
    (lambda s: s.replace("For $90 Aven", "For $90, Aven"), ASK, 6),
    (lambda s: s.replace("pairs of socks", "pairs of shorts"), ASK, 6),
    (lambda s: s.replace("hats", "tops"), "How much did each top cost?", 6),
    (lambda s: s, "What is the cost of 2 hats?", 12),
    (lambda s: s.replace("also ", ""), ASK, 6),
])
def test_reuses_item_vocabulary_and_existing_asks(project, transform, ask, expected):
    result = solve(transform(basket()) + ask, project.registry)
    assert result.answer.value == expected, result.answer


@pytest.mark.parametrize("pronoun", ["she", "he"])
def test_preserved_named_possessor_can_supply_only_person_antecedent(project, pronoun):
    text = "Aven's favorite store was having a summer clearance. " + basket(buyer=pronoun)
    result = solve(text + ASK, project.registry)
    assert result.answer.value == 6, result.answer
    assert not result.deficiencies()
    assert result.store.by_kind(PurchaseTotal)[0].entity == "aven"


@pytest.mark.parametrize("text", [
    basket(equal="") + ASK,
    basket(count=0) + ASK,
    basket(count=1.5) + ASK,
    basket(total=40) + ASK,
    basket().replace("$15", "£15") + ASK,
    basket().replace("Aven also", "Bira also") + ASK,
    basket() + "Aven bought a book. " + ASK,
    basket() + "Aven also bought 2 balls, all at the same price. " + ASK,
    basket() + "Aven received $7. " + ASK,
    basket() + "Aven has 7 apples. " + ASK,
    basket() + "Aven has a budget of $100. " + ASK,
    basket().replace("and 2 pairs", "or 2 pairs") + ASK,
    basket().replace("Aven bought", "Aven can buy") + ASK,
    basket().replace("Aven also bought", "Aven did not buy") + ASK,
    basket().replace(", all at the same price", ", all at a different price") + ASK,
    basket() + "How much did each hat cost tomorrow?",
    basket() + "How much did each red hat cost?",
    basket() + "How much does Aven spend?",
    "Aven's store and Bira's store were having a clearance. " + basket(buyer="she") + ASK,
    "Aven's store was having a clearance. " + basket(buyer="it") + ASK,
    "The garden is near Aven's house. " + basket(buyer="she") + ASK,
])
def test_incomplete_ambiguous_or_unaccounted_evidence_declines(project, text):
    result = solve(text, project.registry)
    assert not result.answer.committed, result.answer


def test_animate_owned_head_still_precedes_hidden_owner(project):
    result = solve("Aven's teacher has a book. She buys 2 hats for $5 each. "
                   "How much does she spend?", project.registry)
    expense = result.store.by_kind(Expenditure)[0]
    assert expense.entity != "aven"


def test_equal_price_lot_is_generatable(project):
    for seed in range(3):
        candidate = generate_candidate(project, rule_id="arithmetic/uniform-price-purchase-lot", seed=seed)
        assert candidate.target_status == "matched"


@pytest.mark.parametrize("opening", [
    "Aven is buying clothes. ",
    "Aven was buying clothes. ",
    "Aven is purchasing clothes. ",
    "Aven was purchasing clothes. ",
])
def test_progressive_collection_introduces_the_same_purchase_lines(project, opening):
    result = solve(opening + basket(buyer="she") + ASK, project.registry)
    assert result.answer.value == 6, result.answer
    assert not result.deficiencies()
    contexts = result.store.by_kind(QuantityEventContext)
    assert len(contexts) == 1
    assert (contexts[0].entity, contexts[0].measure, contexts[0].place) == ("aven", "clothes", "")
    assert len(result.store.by_kind(Expenditure)) == 3
    assert contexts[0] in result.answer.proof.steps[0].evidence


@pytest.mark.parametrize("collection,lemma", [
    ("stuff", "stuff"), ("merchandise", "merchandise"), ("things", "thing"),
    ("items", "item"), ("goods", "goods"),
])
@pytest.mark.parametrize("activity", ["is buying", "was buying", "is purchasing", "was purchasing"])
def test_generic_shopping_collections_elaborate_later_purchases(project, collection, lemma, activity):
    result = solve(f"Aven {activity} {collection}. " + basket(buyer="she") + ASK, project.registry)
    assert result.answer.value == 6, result.answer
    assert not result.deficiencies()
    contexts = result.store.by_kind(QuantityEventContext)
    assert len(contexts) == 1 and contexts[0].measure == lemma
    assert len(result.store.by_kind(Expenditure)) == 3
    assert contexts[0] in result.answer.proof.steps[0].evidence


@pytest.mark.parametrize("opening", [
    "Aven is buying thing. ", "Aven is buying item. ", "Aven is buying ingredient. ",
    "Aven is buying a thing. ", "Aven is buying an item. ",
    "Aven is buying some stuff. ", "Aven is buying the stuff. ",
    "Aven is buying red stuff. ", "Aven is buying 3 items. ",
    "Aven is buying her stuff. ", "Aven is buying stuff for $8. ",
    "Aven is buying stuff and books. ", "Aven is buying stuff from Bira. ",
    "Aven bought stuff. ", "Aven is not buying stuff. ",
    "Bira is buying stuff. ", "Aven will be buying stuff. ",
])
def test_generic_collections_do_not_erase_amounts_restrictions_or_other_events(project, opening):
    result = solve(opening + basket() + ASK, project.registry)
    assert not result.answer.committed, result.answer


def test_generic_collection_cannot_hide_an_additional_unknown_purchase(project):
    result = solve("Aven is buying stuff. " + basket() + "Aven bought a book. " + ASK, project.registry)
    assert not result.answer.committed, result.answer


def test_another_activity_is_not_reclassified_as_a_purchase_introduction(project):
    result = solve("Aven is selling stuff. " + basket() + ASK, project.registry)
    assert not result.store.by_kind(QuantityEventContext)


def test_generic_scope_accepts_mixed_goods_without_widening_typed_collections(project):
    mixed = basket().replace("pairs of socks", "books")
    assert solve("Aven is buying things. " + mixed + ASK, project.registry).answer.value == 6
    assert not solve("Aven is buying clothes. " + mixed + ASK, project.registry).answer.committed
    # The broad collection is only a shopping licence, not global noun identity.
    assert not project.registry.category_terms_overlap("stuff", "book")


@pytest.mark.parametrize("opening", [
    "Aven bought clothes. ",           # a distinct completed purchase
    "Aven is buying shoes. ",          # a specific extra item, not a collection
    "Aven is buying 3 clothes. ",      # never erase a stated count
    "Aven is buying some clothes. ",   # explicitly indefinite amount
    "Aven is buying the clothes. ",    # a definite set, not a bare class
    "Aven is buying red clothes. ",
    "Aven is buying clothes for $8. ",
    "Aven is buying clothes and books. ",
    "Aven is not buying clothes. ",
    "Aven will be buying clothes. ",
    "Aven is buying ingredients. ",    # collection does not cover these items
    "Bira is buying clothes. ",        # a different participant's activity
])
def test_context_does_not_hide_separate_or_uncounted_costs(project, opening):
    result = solve(opening + basket() + ASK, project.registry)
    assert not result.answer.committed, result.answer


def test_context_must_precede_and_cover_the_whole_basket(project):
    for text in [
        basket() + "Aven is buying clothes. " + ASK,
        "Aven is buying clothes. " + basket().replace("pairs of socks", "books") + ASK,
        "Aven is buying clothes. Aven is buying ingredients. " + basket() + ASK,
    ]:
        assert not solve(text, project.registry).answer.committed


def test_existing_relative_price_account_reuses_collection_context(project):
    result = solve("Cato is buying ingredients. Cato buys 3 pounds of sugar for $16 "
                   "and a box of apples that costs half the price of the sugar. "
                   "How much does Cato spend on the ingredients?", project.registry)
    assert result.answer.value == 24, result.answer


@pytest.mark.parametrize("rule_id", ["arithmetic/purchase-collection-context",
                                    "arithmetic/purchase-mass-collection-context"])
@pytest.mark.parametrize("seed", [0, 3, 19])
def test_context_rule_is_generatable(project, rule_id, seed):
    candidate = generate_candidate(project, rule_id=rule_id, seed=seed)
    assert candidate.target_status == "matched"
    assert any(f["type"] == "QuantityEventContext" for f in candidate.facts)


@pytest.mark.parametrize("collection", ["stuff", "merchandise", "things", "items", "goods"])
def test_generic_collection_reuses_relative_purchase_totals_and_ask_scopes(project, collection):
    text = (f"Cato is purchasing {collection}. Cato buys 3 pounds of sugar for $16 "
            "and a box of apples that costs half the price of the sugar. ")
    result = solve(text + f"How much does Cato spend on the {collection}?", project.registry)
    assert result.answer.value == 24, result.answer
    assert len(result.store.by_kind(QuantityEventContext)) == 1
    assert not solve(text + "How much does Cato spend on the clothes?", project.registry).answer.committed


def test_generic_collection_membership_still_requires_ownable_items(project):
    from rulekit.kernel.resource_accounting import purchase_collection_contains

    assert purchase_collection_contains("stuff", "book", project.registry)
    assert purchase_collection_contains("thing", "shoe", project.registry)
    assert not purchase_collection_contains("stuff", "hour", project.registry)
    assert not purchase_collection_contains("stuff", "teacher", project.registry)
    assert not purchase_collection_contains("book", "book", project.registry)


@pytest.mark.parametrize("target", ["stuff", "things", "items", "goods", "books"])
def test_unread_purchase_activity_cannot_turn_subset_cost_into_total_spending(project, target):
    text = "Cato spent $60 on books and $80 on toys. "
    result = solve(text + f"How much did Cato spend on buying other {target}?", project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("target", ["stuff", "things", "items", "goods", "ingredients"])
def test_unread_collection_selector_cannot_be_discarded_by_relative_price_total(project, target):
    text = ("Cato buys 3 pounds of sugar for $16 and a box of apples "
            "that costs half the price of the sugar. ")
    for selector in ["other", "another", "these"]:
        result = solve(text + f"How much does Cato spend on {selector} {target}?", project.registry)
        assert not result.answer.committed, result.answer


def test_unrestricted_spending_asks_still_use_the_existing_total(project):
    text = "Cato buys 3 toys at $12 each. "
    for ask in ["How much does Cato spend?", "How much did Cato pay for everything?"]:
        assert solve(text + ask, project.registry).answer.value == 36
