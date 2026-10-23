# Composition of typed evidence

RuleKit composes facts through synthesis and query-specific consumers. The
operation must be licensed by the facts' meaning, identity, units, and scope.
It does not search arbitrary arithmetic expressions for a plausible number.

## Representations have different roles

| Evidence | Role in a calculation |
| --- | --- |
| `Quantity` | A participant's measured state or event amount |
| `Relation` | An affine or proportional constraint between scoped quantities |
| `Rate` | A measured amount per another unit, activity, or period |
| `Price` | A price attached to an item and its supported pricing scope |
| `GroupTotal` | An aggregate with its own scope and provenance |
| `BatchEvidence` | Operands belonging to a specific ordered or grouped structure |
| `MixtureEvidence` | Sample measurements, component shares, and process evidence |

A per-container content amount is not automatically a stock holding. A total
is not automatically a new independent occurrence. Different consumers may
use these facts, but they must preserve the distinctions in the model.

Implementation: [fact model](../src/rulekit/kernel/model.py),
[fact store](../src/rulekit/kernel/facts.py), and
[quantity folds](../src/rulekit/kernel/totals.py).

## Synthesis and local arithmetic

[Saturation](../src/rulekit/kernel/saturate.py) applies declarative joins and
registered synthesizers to a fixpoint. Ordinary relation synthesis can resolve
forward and inverse constraints and then compose further relation steps.
Derived quantities retain the relevant predicate, participant identity, item
qualifier, and hypothetical provenance.

Consumers also compose typed operands locally. This keeps a query-specific
interpretation from becoming an unqualified global fact. Supported examples
include rate chains, scheduled durations, successive process rates, resource
balances, ordered batches, and mixture ledgers.

Implementation: [rate calculations](../src/rulekit/kernel/rate_calculation.py),
[duration consumers](../src/rulekit/kernel/consumers/composed_duration.py),
[resource accounting](../src/rulekit/kernel/resource_accounting.py), and
[consumer registry](../src/rulekit/kernel/consumers/__init__.py).

## Accounting and completeness

The arithmetic log records expressions and the evidence actually consumed.
Commitment guards check operative numeric values and facts. A present rate or
price is not treated as used merely because its value occurs in an expression.
Likewise, an input used to form a total must not be counted again as stock.

Remainders and averages require an established population. A sequence that
leaves two unknown holders does not identify either holder's contents.
Fractions of separate batches remain separate fractions. Mixture processes
preserve sample identity and basis rather than merging same-named materials.

Implementation: [evaluation log](../src/rulekit/kernel/evaluate.py),
[numeric evidence](../src/rulekit/kernel/numeric_evidence.py), and
[guards](../src/rulekit/kernel/guards.py).

## Ordered batches and acquisitions

`BatchEvidence` retains operands and ordering for one batch. A fraction applies
only to that batch, not to the accumulated stock. Repeated equal counts remain
distinct occurrences. The consumer shares fraction evaluation, resource-balance
arithmetic, numeric accounting, and source-coverage checks with other models.

Two population contracts are supported:

- **Ordered outcomes:** first/next batches must be disjoint and exhaust an
  explicitly stated opening population. Positive and complement asks reuse
  the same event counts.
- **Independent acquisitions:** acquired batches add to stock without having
  to partition an opening population. Disposal and quality classification
  remain local to the identified acquisition. Ordinary acquisitions can stay
  `Quantity` facts until a batch-specific operation needs their scope.

Classification does not remove objects. A quality-specific retained or disposed
count needs classification evidence for every relevant batch; an unclassified
batch still contributes its full amount to an unqualified inventory. Declared
binary classifications do not imply a general synonym or complement rule.

The model requires compatible participants, objects, events, and round identity,
fractions within one whole, and integral discrete outcomes. Overlapping or
incomplete opening partitions, ambiguous/nonadjacent references, nonexistent
rounds, incompatible acquisition/disposal events, and additional unread events
decline. Intentions and attempts are not successful outcomes. A fraction of all
accumulated stock cannot silently become a fraction of the latest acquisition.

Implementation: [outcome rules](../packs/arithmetic/rules/batch-outcomes.yaml),
[acquisition rules](../packs/arithmetic/rules/acquired-batches.yaml), and
[batch consumer](../src/rulekit/kernel/consumers/batch_outcomes.py).
Executable examples and boundaries: [ordered outcomes](../tests/test_batch_outcomes.py)
and [acquisitions](../tests/test_acquired_batches.py).

## One remaining holder

This model identifies the contents of the sole remaining holder in an exhaustive
population. A known prefix records either an equal amount per holder or one
collective subtotal. Those are separate evidence fields: a collective subtotal
is subtracted once and is never multiplied by the prefix size.

The population and prefix must leave exactly one holder. The remainder is the
stated content total minus either the prefix count times its per-holder amount,
or the explicit collective subtotal. The consumer checks whole counts,
nonnegative results, compatible holder/content identities and locations, and
complete numeric and source coverage before returning a partition proof.

Ordinary `Quantity` facts can establish a standalone population; `BatchEvidence`
records the prefix and any combined population, and `GroupTotal` records the
content total. Ordinal and terminal qualifiers identify holders even when their
contents happen to be equal. A question-local conditional total retains its
hypothetical scope.

Two unknown holders, a different queried ordinal, conflicting locations/totals,
fractional object counts, and additional unread events decline. An acquisition
or loss of holders does not itself establish this static population. The model
does not assume equal contents for unknown holders. Ask applicability requires
typed prefix evidence, so ordinary indexed holdings keep their existing route.

Implementation: [holder rules](../packs/arithmetic/rules/holder-remainder.yaml)
and [holder consumer](../src/rulekit/kernel/consumers/holder_remainder.py).
Executable examples, including collective versus per-holder totals:
[holder-remainder tests](../tests/test_holder_remainder.py).

## Mixture ledgers

`MixtureEvidence` preserves sample identity, component share, measurement basis,
and ordered process evidence. Sample references retain holder descriptions and
labels instead of merging every occurrence of the same material noun. A uniquely
associated composition may precede its sample measurement. A solvent alias
requires an earlier, uniquely identified sample.

Mass/weight, volume, mole amount, and count are distinct bases. Explicit basis
information must agree with the sample and requested dimension. Compatible unit
conversions reuse the registry; density, molar mass, and mass-to-count conversions
are not inferred. Count-based samples and processes preserve whole counts.

An unspecified basis retains an empty basis and uses the elementary
same-dimension convention named in the answer explanation. In particular,
recovering a solid from an aqueous sample under this volume convention is not a
scientific determination of the solid's physical volume or a laboratory
concentration model.

Supported processes have separate evidence requirements:

| Process | Required evidence and effect |
| --- | --- |
| Blend distinct samples | Compatible basis and uniquely identified sources; combine component amounts and sample totals |
| Add a component | Explicit purity; update component and total amounts |
| Withdraw part of a mixture | Explicit homogeneity or uniformity; withdraw proportionally |
| Remove a solvent selectively | Identified solvent and explicit component retention |
| Complete solvent recovery | Preserve the retained component amount; the total residue can remain unknown |

Mass and mole amounts are additive in supported ledgers. Combining or diluting
volumes requires an explicit volume-additivity premise. Blending does not invent
a destination container or establish uniformity. An addition or combination
clears uniformity until it is stated again.

Initial sample and composition evidence must associate unambiguously. Processes
then run in sentence order; interleaved remeasurement is unsupported. Declared
aqueous evaporation can carry its scoped retention assumption, but nonaqueous
removal does not inherit it. A later residue percentage still needs a known
residue total.

Current support tracks one component per sample. Multiple stated component
shares, conflicting or ambiguous samples, incompatible bases, unaccounted
narration, negative/excessive withdrawals, unspecified recovery, and negated or
ongoing removal decline. Material names do not imply homogeneity, reactions,
complementary compositions, arbitrary compound synonyms, or gas laws. Laboratory
concentration units such as mass per volume are outside these rules.

Implementation: [mixture rules](../packs/arithmetic/rules/mixtures.yaml) and
[mixture consumer](../src/rulekit/kernel/consumers/mixture_component.py).
Executable examples and boundaries: [general mixtures](../tests/test_general_mixtures.py),
[component amounts](../tests/test_mixture_component.py), and
[paraphrases](../tests/test_mixture_paraphrases.py).

## Related composition contracts

[Logic and arithmetic](logic-arithmetic.md) materialize applicable class
constraints before ordinary arithmetic runs. [Composed-family tests](../tests/test_composed_question_families.py)
and [composed costs and allocations](../tests/test_composed_costs_and_allocations.py)
exercise other complete questions and deliberate declines.

A generic operation is not permission to flatten every aggregate into a
`Quantity`, infer a missing rate, or discard an unused event. The distinction
between evidence and a coincidental arithmetic result is a
[project design constraint](negative-results.md).
