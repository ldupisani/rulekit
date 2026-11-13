"""G5o: category-generic quantifier realization."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import (
    GenerationError,
    generate_candidate,
    list_rule_availability,
)
from rulekit.generation.exploration import exploration_status
from rulekit.generation.sample import _flat_sentence, _leaf_tokens


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"

EXPECTED_OCCURRENCES = {
    "arithmetic/classification-counts-with-shared-members": ((14,), "both"),
    "arithmetic/quoted-sale-price-each": ((6,), "each"),
    'arithmetic/counted-partition-price': ((7,), 'each'),
    'arithmetic/material-container-recipient-capacity': ((0,), 'each'),
    'arithmetic/material-container-service-capacity': ((0,), 'each'),
    'arithmetic/maximum-day-postposed-count': ((4,), 'most'),
    'arithmetic/nested-material-container-content': ((0,), 'each'),
    'arithmetic/nested-supply-exact-service-plan': ((8,), 'each'),
    'arithmetic/packaged-classified-content': ((0,), 'each'),
    'arithmetic/paired-day-count': ((9,), 'each'),
    'arithmetic/per-component-and-remaining-resource-requirement': ((7,), 'each'),
    'arithmetic/per-component-resource-requirement': ((7,), 'each'),
    'arithmetic/remaining-partition-relative-unit-price': ((2,), 'each'),
    "arithmetic/average-each-initial-period": ((3,), "each"),
    "arithmetic/partitive-distributed-supplemental-receipt": ((4,), "each"),
    "arithmetic/shared-completion-deadline-single-period": ((1, 0), "each"),
    "arithmetic/supplement-from-all-service-clients": ((4,), "each"),
    "arithmetic/supplement-per-completed-service": ((1,), "each"),
    "arithmetic/generic-unit-quote-collection": ((3,), "each"),
    'arithmetic/coin-subset-valuation': ((7,), 'each'),
    'arithmetic/periodic-rate-every-unit': ((4,), 'freq'),
    'arithmetic/relative-measured-item-quote': ((5,), 'much'),
    'arithmetic/returned-exchange-subset-valuation': ((16,), 'each'),
    'arithmetic/additional-ratio-acquisition': ((4,), 'every'),
    'arithmetic/distributive-object-unit-price': ((0,), 'each'),
    'arithmetic/fixed-block-with-excess-rate': ((15,), 'every'),
    'arithmetic/pooled-stock-shared-within-group': ((2,), 'all'),
    'arithmetic/uniform-grouped-capacity': ((6,), 'each'),
    'arithmetic/uniform-indexed-performance': ((4,), 'each'),
    'arithmetic/uniform-repetition-frequency': ((4,), 'each'),
    "arithmetic/declared-package-unit-quote": ((6, 0), "each"),
    "arithmetic/explicit-per-recipient-unit-count": ((0,), "each"),
    "arithmetic/partitioned-stock-served-to-mixed-roster": ((15,), "all"),
    "arithmetic/collected-components-each": ((5,), "each0"),
    "arithmetic/collected-components-each-each": ((10,), "each1"),
    "arithmetic/collected-components-each-single": ((5,), "each0"),
    "arithmetic/collected-components-single-each": ((9,), "each1"),
    "arithmetic/completed-service-with-supplement": ((6,), "each"),
    "arithmetic/distributed-supplemental-receipt": ((1,), "each"),
    "arithmetic/named-individual-completion-deadline": ((1,), "each"),
    "arithmetic/shared-completion-deadline": ((1, 0), "each"),
    "arithmetic/coordinated-relative-activity-extent": ((12,), "much"),
    "arithmetic/coordinated-relative-activity-extent-as-much": ((12,), "much"),
    "arithmetic/distributive-event-duration": ((0,), "each"),
    "arithmetic/distributive-scheduled-event-count": ((1,), "each"),
    "arithmetic/measured-holder-subset-finite": ((6,), "each"),
    "arithmetic/measured-holder-subset-progressive": ((7,), "each"),
    "arithmetic/per-event-preparation-duration": ((5,), "event_frequency"),
    "arithmetic/holder-prefix-0": ((0,), "each"),
    "arithmetic/holder-prefix-1": ((2,), "each"),
    "arithmetic/holder-prefix-2": ((4,), "each"),
    "arithmetic/holder-prefix-combined-0-bare": ((4,), "each"),
    "arithmetic/holder-prefix-combined-0-located": ((6,), "each"),
    "arithmetic/holder-prefix-combined-1-bare": ((6,), "each"),
    "arithmetic/holder-prefix-combined-1-located": ((8,), "each"),
    "arithmetic/holder-prefix-combined-2-bare": ((8,), "each"),
    "arithmetic/holder-prefix-combined-2-located": ((10,), "each"),
    "arithmetic/periodic-collection-duty": ((0,), "every"),
    "arithmetic/recipient-content-passive-each": ((4,), "each"),
    "arithmetic/recipient-content-singular-each": ((0,), "each"),
    "arithmetic/distributive-package-price-quote": ((1,), "each"),
    "arithmetic/recipient-content-each": ((4,), "each"),
    "arithmetic/uniform-container-stock": ((10,), "each"),
    "arithmetic/uniform-service-tariff": ((4,), "each"),
    "arithmetic/named-group-shopping-intention": ((1, 0), "both"),
    "arithmetic/named-group-item-shopping-intention": ((1, 0), "both"),
    "arithmetic/named-group-new-item-shopping-intention": ((1, 0), "both"),
    "arithmetic/named-group-collection-shopping-intention": ((1, 0), "both"),
    "arithmetic/named-group-new-collection-shopping-intention": ((1, 0), "both"),
    "arithmetic/conditional-all-units-discount-policy": ((6,), "totality"),
    "arithmetic/conditional-percent-all-units-discount-policy": ((5,), "totality"),
    "arithmetic/postpositive-unit-price": ((3,), "each"),
    "arithmetic/itemized-participial-price-serving-unit": ((7, 0), "each"),
    "arithmetic/itemized-participial-price-item-unit": ((5, 0), "each"),
    "arithmetic/itemized-marked-price-serving-unit": ((8, 0), "each"),
    "arithmetic/itemized-marked-price-item-unit": ((6, 0), "each"),
    "arithmetic/itemized-sale-offer-price-serving-unit": ((8, 0), "each"),
    "arithmetic/itemized-sale-offer-price-item-unit": ((6, 0), "each"),
    "arithmetic/itemized-relative-price-item-unit": ((6, 0), "each"),
    "arithmetic/itemized-relative-price-serving-unit": ((8, 0), "each"),
    "arithmetic/holder-prefix-subtotal-trailing": ((4, 0), "total_quantifier"),
    "arithmetic/collection-nominal-attribute": ((0,), "subset"),
    "arithmetic/collection-two-nominal-attributes": ((6,), "subset2"),
    "arithmetic/collection-three-nominal-attributes": ((9,), "subset3"),
    "arithmetic/container-all-available-fit-observation": ((0,), "totality"),
    "arithmetic/container-package-contents-totality-transfer": ((5,), "totality"),
    "arithmetic/container-package-groups-totality-transfer": ((2,), "totality"),
    "arithmetic/container-totality-transfer": ((3,), "totality"),
    "arithmetic/totality-activity-event": ((3,), "totality"),
    "arithmetic/existential-premise-distributive": ((4,), "q"),
    "arithmetic/group-total-trailing": ((1, 0), "q"),
    "arithmetic/group-total-trailing-in-all": ((2,), "q"),
    "arithmetic/discount-of-flat-per-unit": ((3,), "per_unit"),
    "arithmetic/periodic-output-per-unit": ((4,), "freq"),
    "arithmetic/periodic-rate-every-span": ((4,), "freq"),
    "arithmetic/per-member-period-rate": ((0,), "each"),
    "arithmetic/two-per-member-period-rates": ((7,), "each2"),
    "arithmetic/three-per-member-period-rates": ((14,), "each3"),
    "arithmetic/passive-per-member-period-rate": ((4,), "each"),
    "arithmetic/per-member-daily-rates": ((0,), "each"),
    "arithmetic/per-member-fronted-period-rates": ((2,), "each"),
    "arithmetic/postposed-member-period-rate": ((1,), "each"),
    "arithmetic/three-per-member-daily-rates": ((12,), "each3"),
    "arithmetic/three-per-member-fronted-period-rates": ((12,), "each3"),
    "arithmetic/three-per-member-shared-period-rates": ((10,), "each3"),
    "arithmetic/two-per-member-daily-rates": ((6,), "each2"),
    "arithmetic/two-per-member-fronted-period-rates": ((7,), "each2"),
    "arithmetic/two-per-member-shared-period-rates": ((5,), "each2"),
}
EXPECTED_FILLERS = {
    "most",
    "all",
    "both",
    "double",
    "each",
    "every",
    "much",
    "no",
    "some",
    "several",
    "triple",
}
EXPECTED_DISTRIBUTIVE_FILLERS = {"each", "every"}


def _write_invented_project(root: Path) -> None:
    pack = root / "pack"
    pack.mkdir()
    (root / "project.yaml").write_text(
        """\
format: rulekit/project@1
name: invented-quantifier-generation
packs: [./pack]
"""
    )
    (pack / "pack.yaml").write_text(
        """\
format: rulekit/pack@1
name: invented-quantifier
version: 0.1.0
"""
    )
    (pack / "lexicon.yaml").write_text(
        """\
format: rulekit/lexicon@1
entries:
  zorch: {senses: [quantifier]}
"""
    )
    (pack / "rules.yaml").write_text(
        """\
format: rulekit/rules@1
rules:
  - id: invented/quantifier
    phase: read
    match:
      sentence:
        - {lit: signal}
        - {slot: determiner, cat: quantifier}
    emits:
      - fact: atom
        entity: sample
        pred: "{determiner}"
"""
    )


def test_g5o_profiles_the_complete_quantifier_category_class() -> None:
    project = load_project(CURATED)
    occurrences = {
        rule.id: (path, token.slot)
        for rule in project.registry.rules
        for path, token, _ in _leaf_tokens(_flat_sentence(rule) or [])
        if (
            token.cat is not None
            and project.registry.root_sense(token.cat) == "quantifier"
        )
    }
    fillers = {
        surface
        for surface, entry in project.registry.lexicon.items()
        if (
            "quantifier" in entry.senses
            and project.registry.word_in_category(surface, "quantifier")
        )
    }

    assert occurrences == EXPECTED_OCCURRENCES
    assert project.registry.cat_ancestors("quantifier") == ["quantifier"]
    assert fillers == EXPECTED_FILLERS
    assert {
        project.source_index.lexicon[word].path.resolve()
        for word in fillers
    } == {(ROOT / "packs/core-english/lexicon/core.yaml").resolve()}


def test_g5o_unlocks_only_the_preregistered_rule() -> None:
    project = load_project(CURATED)
    availability = {
        item.id: item for item in list_rule_availability(project)
    }

    assert len(availability) == 957
    assert sum(item.supported for item in availability.values()) == 856
    assert sum(not item.supported for item in availability.values()) == 101
    assert availability[
        "arithmetic/existential-premise-distributive"
    ].supported
    assert availability["arithmetic/periodic-rate-every-span"].supported
    assert all(
        "unsupported sense 'quantifier'" not in blocker
        for item in availability.values()
        for blocker in item.blockers
    )
    assert len(exploration_status(project)["fillers"]) == 2652


@pytest.mark.parametrize("quantifier", sorted(EXPECTED_DISTRIBUTIVE_FILLERS))
def test_every_distributive_quantifier_is_exposed_for_human_review(
    quantifier: str,
) -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/existential-premise-distributive",
        seed=0,
        locked_bindings={"q": quantifier},
    )
    premise = next(row for row in candidate.premises if row.slot == "q")

    assert candidate.generator_version == "g6-strict-boundary-modes"
    assert candidate.target_status == "matched"
    assert premise.binding == quantifier
    assert premise.status == "passed"
    assert premise.category_path == (
        quantifier,
        "distributive_quantifier",
        "quantifier",
    )
    assert {"rule-token", "lexicon"} <= {
        source["kind"] for source in premise.sources
    }


@pytest.mark.parametrize(
    "quantifier", sorted(EXPECTED_FILLERS - EXPECTED_DISTRIBUTIVE_FILLERS)
)
def test_non_distributive_quantifiers_cannot_fill_the_container_slot(
    quantifier: str,
) -> None:
    with pytest.raises(GenerationError):
        generate_candidate(
            load_project(CURATED),
            rule_id="arithmetic/existential-premise-distributive",
            seed=0,
            locked_bindings={"q": quantifier},
        )


def test_exploration_exposes_quantifiers_only_on_compatible_rules() -> None:
    fillers = {
        item["identity"]: item
        for item in exploration_status(load_project(CURATED))["fillers"]
    }

    assert set(fillers) >= EXPECTED_FILLERS
    for quantifier in EXPECTED_FILLERS:
        placements = {
            (placement["rule_id"], placement["slot"])
            for placement in fillers[quantifier]["placements"]
            if placement["slot"] in {"q", "freq"}
        }
        expected = set()
        if quantifier in EXPECTED_DISTRIBUTIVE_FILLERS:
            expected.add(
                ("arithmetic/existential-premise-distributive", "q")
            )
            if quantifier == "every":
                expected.add(
                    ("arithmetic/periodic-rate-every-span", "freq")
                )
                expected.add(
                    ("arithmetic/periodic-rate-every-unit", "freq")
                )
                expected.add(
                    ("arithmetic/periodic-output-per-unit", "freq")
                )
        if quantifier == "all":
            expected.add(("arithmetic/group-total-trailing", "q"))
            expected.add(("arithmetic/group-total-trailing-in-all", "q"))
        assert placements == expected


def test_quantifier_realization_is_category_generic(tmp_path: Path) -> None:
    _write_invented_project(tmp_path)
    candidate = generate_candidate(
        load_project(tmp_path),
        rule_id="invented/quantifier",
        seed=0,
    )
    premise = next(
        row for row in candidate.premises if row.slot == "determiner"
    )

    assert candidate.sentence == "Signal zorch."
    assert candidate.target_status == "matched"
    assert premise.category_path == ("zorch", "quantifier")
    assert {"rule-token", "lexicon"} <= {
        source["kind"] for source in premise.sources
    }
