"""Invented analogues for marginal prices, purchase budgets and nested allocations."""

import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def check(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.kind == "number", result.answer
    assert result.answer.value == pytest.approx(expected), result.answer
    assert not result.deficiencies(), result.deficiencies()


def ticket(count=9, threshold=6, discount="20%", ending="in all"):
    return (
        f"A ticket costs $25. Mira bought {count} tickets and received a {discount} "
        f"discount for every ticket bought that exceeds {threshold}. "
        f"How much did Mira pay {ending}?"
    )


@pytest.mark.parametrize("count,expected", [(3, 75), (6, 150), (9, 210), (0, 0)])
@pytest.mark.parametrize("ending", ["in all", "in total", ""])
def test_marginal_discount(reg, count, expected, ending):
    check(reg, ticket(count=count, ending=ending), expected)


@pytest.mark.parametrize(
    "edit",
    [
        lambda q: q.replace(
            "for every ticket bought that exceeds", "on each ticket above"
        ),
        lambda q: q.replace(
            "for every ticket bought that exceeds", "on each ticket beyond"
        ),
        lambda q: q.replace("ticket", "book"),
        lambda q: q.replace("costs $25", "costs $25 each"),
    ],
)
def test_marginal_price_paraphrases(reg, edit):
    check(reg, edit(ticket()), 210)


@pytest.mark.parametrize(
    "edit",
    [
        lambda q: q.replace("20%", "120%"),
        lambda q: q.replace("9 tickets", "9.5 tickets"),
        lambda q: q.replace("exceeds 6", "exceeds 6.5"),
        lambda q: q.replace("A ticket costs $25. ", ""),
        lambda q: q.replace("A ticket costs", "A book costs"),
        lambda q: q.replace("Mira pay", "Owen pay"),
        lambda q: q.replace("How much", "Mira paid $3 for food. How much"),
        lambda q: q.replace("every ticket", "every book"),
    ],
)
def test_marginal_price_boundaries(reg, edit):
    assert solve(edit(ticket()), reg).answer.kind == "decline"


def purchase():
    return (
        "Owen buys a pair of shoes which costs $30 and a dress which costs $90. "
        "How much should Mira budget to spend twice as much as Owen spent?"
    )


@pytest.mark.parametrize(
    "edit,expected",
    [
        (lambda q: q, 240),
        (lambda q: q.replace("which", "that"), 240),
        (lambda q: q.replace("twice", "triple"), 360),
        (lambda q: q.replace("a pair of shoes", "a book").replace("dress", "hat"), 240),
        (lambda q: q.replace(" and a dress", " . Owen buys a dress"), 240),
        (
            lambda q: q.replace(
                "Owen spent?", "Owen spent on the pair of shoes and dress?"
            ),
            240,
        ),
        (lambda q: q.replace("to spend twice", "if she wants to spend twice"), 240),
    ],
)
def test_relative_purchase_budget(reg, edit, expected):
    check(reg, edit(purchase()), expected)


@pytest.mark.parametrize(
    "edit",
    [
        lambda q: q.replace("Owen spent?", "Tess spent?"),
        lambda q: q.replace("Mira budget", "Owen budget"),
        lambda q: q.replace("Owen spent?", "Owen spent on the shoes and book?"),
        lambda q: q.replace("How much", "Owen lost $10. How much"),
        lambda q: q.replace("$90", "90 euros"),
    ],
)
def test_relative_budget_boundaries(reg, edit):
    assert solve(edit(purchase()), reg).answer.kind == "decline"


def nested():
    return (
        "8 children collected 7 boxes of apples. "
        "3 boxes had 4 bags, with each bag having 6 apples, while the remaining boxes "
        "had 2 bags, with each bag having 5 apples. "
        "How many apples would each child get if they divide the apples equally amongst themselves?"
    )


@pytest.mark.parametrize(
    "edit",
    [
        lambda q: q,
        lambda q: q.replace("amongst", "among"),
        lambda q: q.replace(" amongst themselves", ""),
        lambda q: q.replace("while the remaining boxes", "and 4 boxes"),
        lambda q: q.replace("while the remaining boxes", ". The remaining boxes"),
        lambda q: q.replace("apples", "cookies"),
        lambda q: q.replace("children", "monkeys").replace("child", "monkey"),
        lambda q: q.replace("would", "will"),
    ],
)
def test_nested_distribution(reg, edit):
    check(reg, edit(nested()), 14)


@pytest.mark.parametrize(
    "edit",
    [
        lambda q: q.replace("7 boxes", "2 boxes"),
        lambda q: q.replace("8 children", "0 children"),
        lambda q: q.replace("3 boxes", "3.5 boxes"),
        lambda q: q.replace("each bag having 5", "each box having 5"),
        lambda q: q.replace("remaining boxes", "last boxes"),
        lambda q: q.replace("remaining boxes", "remaining piles"),
        lambda q: q.replace("5 apples", "5 bananas"),
        lambda q: q.replace("How many", "They ate 3 apples. How many"),
    ],
)
def test_nested_distribution_boundaries(reg, edit):
    assert solve(edit(nested()), reg).answer.kind == "decline"


def sequence():
    return (
        "A storm caused 3 trees to collapse. Each following storm would have double "
        "the number of collapsing trees as the previous one. After 2 more storms, "
        "how many trees had collapsed including those from the first storm?"
    )


@pytest.mark.parametrize(
    "edit,expected",
    [
        (lambda q: q, 21),
        (lambda q: q.replace("double", "triple"), 39),
        (lambda q: q.replace("2 more", "0 more"), 3),
        (lambda q: q.replace("2 more", "1 more"), 9),
        (lambda q: q.replace("would have", "has"), 21),
        (lambda q: q.replace("trees", "houses"), 21),
        (
            lambda q: q.replace(
                "Each following", "Experts predicted that each following"
            ),
            21,
        ),
    ],
)
def test_event_progression(reg, edit, expected):
    check(reg, edit(sequence()), expected)


@pytest.mark.parametrize(
    "edit",
    [
        lambda q: q.replace("2 more", "2.5 more"),
        lambda q: q.replace("2 more", "1000 more"),
        lambda q: q.replace("3 trees", "3.5 trees"),
        lambda q: q.replace("following storm", "following earthquake"),
        lambda q: q.replace("first storm", "second storm"),
        lambda q: q.replace("previous one", "previous 2"),
        lambda q: q.replace("After 2", "There are 8 houses. After 2"),
        lambda q: q.replace("collapsing trees", "collapsing houses"),
    ],
)
def test_event_progression_boundaries(reg, edit):
    assert solve(edit(sequence()), reg).answer.kind == "decline"


def budget():
    return (
        "Mira has a budget of $800. Mira spends 25% on food, 10% on rent, "
        "and the rest on books. How much money does Mira spend on books?"
    )


@pytest.mark.parametrize(
    "edit,expected",
    [
        (lambda q: q, 520),
        (lambda q: q.replace("25%", "half"), 320),
        (lambda q: q.replace("10%", "0%"), 600),
        (lambda q: q.replace("How much money", "How much"), 520),
        (lambda q: q.replace("on books?", "on food?"), 200),
        (lambda q: q.replace("$800.", "$800 per month."), 520),
        (lambda q: q.replace("25%", "25% of her money"), 520),
        (
            lambda q: q.replace("Mira spends", "She spends").replace(
                "does Mira", "does she"
            ),
            520,
        ),
    ],
)
def test_budget_allocations(reg, edit, expected):
    check(reg, edit(budget()), expected)


@pytest.mark.parametrize(
    "edit",
    [
        lambda q: q.replace("25%", "95%"),
        lambda q: q.replace("10% on rent", "10% on food"),
        lambda q: q.replace("does Mira", "does Owen"),
        lambda q: q.replace("Mira spends", "Owen spends"),
        lambda q: q.replace("on books?", "on entertainment?"),
        lambda q: q.replace("How much", "Mira earned $10. How much"),
        lambda q: q.replace("25%", "25% of Owen's money"),
    ],
)
def test_budget_allocation_boundaries(reg, edit):
    assert solve(edit(budget()), reg).answer.kind == "decline"


def test_complete_contexts(reg):
    check(
        reg,
        "Mira and Owen want to attend a beauty and modelling contest. "
        "They want to buy pairs of shoes and dresses. " + purchase(),
        240,
    )
    check(
        reg,
        sequence()
        .replace("Each following", "Experts predicted that each following")
        .replace(
            "previous one.",
            "previous one, since each one would make the foundations less stable.",
        ),
        21,
    )
    check(
        reg,
        "Mira is a first-year student at a university in Chicago. "
        + budget()
        .replace("Mira spends", "She spends")
        .replace("does Mira", "does she"),
        520,
    )


def test_simple_single_allocation_and_single_basket(reg):
    check(reg, budget().replace("25% on food, 10% on rent,", "25% on food,"), 600)
    check(reg, purchase().replace(" and a dress which costs $90", ""), 60)
    check(
        reg,
        nested()
        .replace("7 boxes", "3 boxes")
        .replace(
            ", while the remaining boxes had 2 bags, with each bag having 5 apples", ""
        ),
        9,
    )


def test_fractional_equal_share_is_not_rounded(reg):
    check(reg, nested().replace("8 children", "3 children"), 112 / 3)


def test_ambiguous_person_reference_stays_ambiguous(reg):
    q = (
        "Mira has a budget of $800. Owen has a book. She spends 25% on food, "
        "10% on rent, and the rest on books. How much money does Mira spend on books?"
    )
    assert solve(q, reg).answer.kind == "decline"


def test_location_does_not_hide_a_competing_person(reg):
    q = (
        "Mira is a student at a university in Chicago. Owen has a book. "
        "She has a budget of $800. She spends 25% on food, 10% on rent, "
        "and the rest on books. How much money does she spend on books?"
    )
    assert solve(q, reg).answer.kind == "decline"


def test_result_attribute_does_not_change_unread(reg):
    assert (
        solve(sequence().replace("collapsing trees", "large trees"), reg).answer.kind
        == "decline"
    )


def test_plural_budget_subject_reference_is_not_singular(reg):
    q = purchase().replace("to spend twice", "if they want to spend twice")
    assert solve(q, reg).answer.kind == "decline"


def test_possessive_budget_reference_preserves_residual(reg):
    check(
        reg,
        "Mira has a budget of $120. Mira spent $25 on a book. "
        "Mira bought a hat. Mira has $30 left from her budget. "
        "How much did Mira pay for the hat?",
        65,
    )


def test_affiliation_context_preserves_class_membership(reg):
    result = solve("Mira is a student at the school. Is Mira a student?", reg)
    assert result.answer.value == "yes", result.answer


def test_a_location_named_as_an_actor_remains_a_reference_competitor(reg):
    text = (
        "Mira is a student at a university in Chicago. Chicago has a book. "
        "He has a budget of $800. He spends 25% on food, 10% on rent, "
        "and the rest on books. How much money does he spend on books?"
    )
    assert solve(text, reg).answer.kind == "decline"


def separate_discount(count=9, policy="a discount of 20%", item="book", order=(0, 1, 2)):
    clauses = [
        f"A {item} costs $25.",
        f"There is {policy} on additional {item}s if you buy more than 6.",
        f"Mira bought {count} {item}s.",
    ]
    return " ".join(clauses[i] for i in order) + " How much did Mira pay in all?"


@pytest.mark.parametrize("count,expected", [(0, 0), (3, 75), (6, 150), (9, 210)])
@pytest.mark.parametrize("policy", ["a discount of 20%", "a 20% discount"])
@pytest.mark.parametrize("order", [(0, 1, 2), (0, 2, 1), (1, 0, 2)])
def test_separate_marginal_policy(reg, count, expected, policy, order):
    check(reg, separate_discount(count, policy, order=order), expected)


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("book", "ticket"),
    lambda q: q.replace("in all", "in total"),
    lambda q: q.replace("in all", ""),
])
def test_separate_marginal_policy_paraphrases(reg, edit):
    check(reg, edit(separate_discount()), 210)


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("additional ", ""),
    lambda q: q.replace("more than", "less than"),
    lambda q: q.replace("20%", "120%"),
    lambda q: q.replace("9 books", "9.5 books"),
    lambda q: q.replace("than 6", "than 6.5"),
    lambda q: q.replace("additional books", "additional tickets"),
    lambda q: q.replace("Mira pay", "Owen pay"),
    lambda q: q.replace("Mira bought 9 books.", ""),
    lambda q: q.replace("How much", "Owen bought 2 books. How much"),
    lambda q: q.replace("if you buy", "if Owen buys"),
    lambda q: q.replace("There is", "There is not"),
])
@pytest.mark.parametrize("scope", ["additional", "all"])
def test_separate_marginal_policy_boundaries(reg, edit, scope):
    assert solve(edit(separate_discount()).replace("additional", scope), reg).answer.kind == "decline"


@pytest.mark.parametrize("count,expected", [(0, 0), (3, 75), (6, 150), (7, 140), (9, 180)])
@pytest.mark.parametrize("policy", ["a discount of 20%", "a 20% discount"])
@pytest.mark.parametrize("order", [(0, 1, 2), (0, 2, 1), (1, 0, 2)])
def test_whole_purchase_threshold_discount(reg, count, expected, policy, order):
    check(reg, separate_discount(count, policy, order=order).replace("additional", "all"), expected)


@pytest.mark.parametrize("item", ["book", "ticket"])
@pytest.mark.parametrize("ending", ["in all", "in total", ""])
def test_threshold_discount_scope_changes_the_total(reg, item, ending):
    text = separate_discount(item=item).replace("in all", ending)
    check(reg, text, 210)
    check(reg, text.replace("additional", "all"), 180)


def test_competing_discount_scopes_decline(reg):
    text = separate_discount().replace(
        "Mira bought", "There is a 20% discount on all books if you buy more than 6. Mira bought"
    )
    assert solve(text, reg).answer.kind == "decline"


@pytest.mark.parametrize("ending", ["per book", "for each book", "for every book", "per book on average", "on average per book"])
@pytest.mark.parametrize("count,expected", [(3, 25), (6, 25), (7, 20), (9, 20)])
@pytest.mark.parametrize("policy", ["a discount of 20%", "a 20% discount"])
def test_uniform_paid_unit_price(reg, ending, count, expected, policy):
    text = separate_discount(count, policy).replace("additional", "all")
    check(reg, text.replace("in all", ending), expected)


@pytest.mark.parametrize("ending", ["per book", "for each book", "for every book"])
def test_mixed_paid_unit_prices_need_explicit_average(reg, ending):
    assert solve(separate_discount().replace("in all", ending), reg).answer.kind == "decline"
    check(reg, separate_discount(6).replace("in all", ending), 25)


@pytest.mark.parametrize("ending", ["per {item} on average", "on average per {item}"])
def test_average_paid_price_reuses_purchase_total(reg, ending):
    check(reg, separate_discount().replace("in all", ending.format(item="book")), 210 / 9)
    check(reg, ticket().replace("in all", ending.format(item="ticket")), 210 / 9)


@pytest.mark.parametrize("scope", ["all", "additional"])
@pytest.mark.parametrize("ending", ["per book", "for each book", "per book on average", "on average per book"])
def test_no_paid_unit_price_without_purchased_units(reg, scope, ending):
    text = separate_discount(0).replace("additional", scope).replace("in all", ending)
    assert solve(text, reg).answer.kind == "decline"


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("per book", "per ticket"),
    lambda q: q.replace("Mira pay", "Owen pay"),
    lambda q: q.replace("per book", "per 2 books"),
    lambda q: q.replace("per book", "per red book"),
])
def test_paid_unit_price_reference_boundaries(reg, edit):
    text = separate_discount().replace("additional", "all").replace("in all", "per book")
    assert solve(edit(text), reg).answer.kind == "decline"


@pytest.mark.parametrize("edit", [
    lambda q: q.replace("per book", "per ticket"),
    lambda q: q.replace("Mira pay", "Owen pay"),
    lambda q: q.replace("on average", "on total"),
])
def test_average_before_unit_price_boundaries(reg, edit):
    text = separate_discount().replace("in all", "on average per book")
    assert solve(edit(text), reg).answer.kind == "decline"
