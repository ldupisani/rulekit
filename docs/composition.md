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
| `RegionEvidence` | Resource scope, named geometric axes, and directly measured opening/removal amounts |

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

## Recurring costs and complementary saving windows

A periodic expense, active-period duration, saving intention, and uniform
task tariff establish an average over the complementary saving window.
Offered activities are `ServiceScope` evidence, not completed work or income.
The enclosing cycle is declared in pack data: the supported annual-season
convention uses one year and names that assumption in the answer. Calendar
month/year conversion uses cadence conversions, not a fixed day count.
The calculation requires a positive saving window, one participant and
purpose, matching periods, and complete source and numeric accounting.
The duration may be declared after the saving plan or tariff. A named activity
does not by itself limit an unrelated recurring expense to that activity's
season. Saving-for and affordability questions share the same goal contract.
An expense can explicitly name its owned active period in a leading or
trailing temporal phrase. Its duration may be stated separately, as a measured
modifier of the period, or as a counted duration of that period. This links
otherwise unrelated goods to the expense window without interpreting the
goods as activity names. Period owners, activity modifiers, and measurements
must agree; extra periods, negation, outside-period costs, and incomplete
duration evidence still decline.

Implementation: [cyclic budgets](../packs/arithmetic/rules/cyclic-budgets.yaml)
and [saving average](../src/rulekit/kernel/consumers/cyclic_saving_average.py).
Executable paraphrases and boundaries:
[scoped periodic expenses](../tests/test_scoped_periodic_expenses.py).

## Measured resource remainders

Material identity, stock form, geometric shape, and requested measurement
are separate evidence. `RegionEvidence` preserves one named operand and its
unit per source region. Rectangular areas and cuboid volumes use the shared
YAML formula registry; directly stated lengths, masses, and volumes use the
same resource balance without inventing geometry or density. Every geometric
axis is converted before evaluating its formula, so area and volume conversions
apply the unit factor to each axis.

An active cut with omitted material needs an earlier fabrication scope for
the same actor. Passive descriptions can refer to the sole stated stock;
coordinated omissions inherit a unique same-sentence anchor. Direct usage
must identify the stock's owner. Multiple stocks, incompatible bases, unread
conditions, oversized individual cuts, and negative remainders decline.
Geometric subtraction accounts for area or volume; it does not construct a
cutting or packing layout.

Separate ask constructions normalize “how much”, “how many units”, and
“what area/volume/length/mass” to the same resource, quantity basis, and output
unit. Both standalone and attached square/cubic modifiers preserve the power.
A question may omit its physical basis only when all measured operands and
declared shape formulas establish one common basis. Omitted output units still
require one uniquely stated unit. Conversions follow declared unit paths and
apply the factor to every geometric axis. Material modifiers such as an uncut
remainder retain the same identity and measurement checks.
Predicative length questions and dimension-noun questions with a remnant
modifier on the material use the same contract. Physical-length wording is
gated to measured materials; it does not widen duration asks or infer a
remaining side length from area or volume. Explicit length units permit
conversion; omitted units still require a unique stated unit.

Implementation: [region rules](../packs/arithmetic/rules/material-regions.yaml),
[shared shape properties](../packs/core-english/categories/geometry.yaml), and
[resource remainder](../src/rulekit/kernel/consumers/material_region_remainder.py).

Shape properties use the same inheritance and typed evaluation contract as
other category properties. The resource consumer converts axes, then calls the
shared property evaluator, including declared equal-side constraints and formula
dependencies. An omitted spatial basis selects the shape's spatial measure:
adding a perimeter, diagonal, or surface-area formula cannot make an existing
area or volume balance ambiguous. Scalar spatial dimension and the physical
dimension of a derived result remain separate.

Implementation and boundaries: [property evaluator](../src/rulekit/kernel/properties.py),
[property contracts](../tests/test_category_properties.py).

A measured acquisition can also establish stock for ordered fractional uses.
Each use preserves whether its fraction applies to the opening stock or the
current remainder. Coordinated omissions inherit one same-sentence actor;
material identity, compatible units, source coverage and nonnegative balances
remain required. A production-variety count checks distinct full product
references, rather than multiplying the usage again. This extends the same
measured-remainder asks to food ingredients and fabrication materials.

Implementation: [fractional use grammar](../packs/arithmetic/rules/fractional-resource-use.yaml)
and [fractional resource composition](../src/rulekit/kernel/consumers/fractional_resource_remainder.py).

## Category inventory percentages

A category-percentage question can use an explicit category total or a
document-local enumeration of distinct subtypes. The denominator includes only
counts belonging to the requested category and one compatible inventory scope.
Other state counts can be excluded only when YAML category declarations prove
their separation from that category. They remain in the fact store and retain
full source and numeric accounting. Unknown membership, overlapping descriptions,
duplicate counts, extra events and mixed relevant locations decline. A single subtype alone
does not establish the category total. Negation selects the complement before
division. This does not close the category's taxonomy or enable general
superordinate totals from incidental mentions.

Coordinated counted lists retain every member, including lists longer than
three items. A shared location may follow the first item or the entire list.
An introductory `with` can supply a stated inventory, with an optional shared
location after the list. This frame consumes the complete inventory fragment;
it does not reinterpret accompaniment, absence, or instruments as holdings.
The same inventory can be supplied as the current question's conditional
antecedent, including an immediately preceding detached conditional sentence;
its facts retain assumption provenance and never persist beyond that solve.
Disjunctions, missing counts, and additional item-specific locations do not
become a shared inventory.

Implementation: [inventory asks](../packs/arithmetic/rules/category-populations.yaml),
[coordinated inventory grammar](../packs/arithmetic/rules/counted-inventories.yaml)
and [percentage consumers](../src/rulekit/kernel/consumers/partition_percentage.py).
Executable analogues and boundaries: [inventory tests](../tests/test_existential_inventories.py).
Category filtering and separation contracts: [scoped inventories](../tests/test_scoped_inventory_percentages.py)
and [category declarations](../tests/test_category_disjointness.py).

The shared vocabulary classifies [flowers and fruit](../packs/core-english/categories/plants.yaml),
[birds and insects](../packs/core-english/categories/animals.yaml), and
[people](../packs/core-english/categories/agents.yaml). Birds and insects inherit
animal membership. Botanical families are separate from living agents; birds
and insects are separate from each other and from people. These declarations
do not separate all animals from people or infer separation from an unclassified
noun. Lexical plurals reuse the same membership and separation evidence.
Vocabulary ownership and role boundaries are checked by the
[core taxonomy tests](../tests/test_core_inventory_taxonomy.py).

## Partitioned process durations

An explicitly partitioned process can have one unknown part duration. Every
other indexed part must have a duration, with compatible units and matching
participant and process references. A relative duration uses the immediately
preceding part and a compatible actor reference. Word and numeric ordinals
share the existing ordinal-index machinery. The total may be asserted or an
adjacent question-local condition; subtraction cannot produce a negative
duration. No unspecified gaps, overlaps or concurrent work are inferred.
The partition may be introduced by possession or explicit division. Duration
questions accept a fronted unit phrase or an elapsed-time construction.
When an elapsed-time question omits its output unit, the answer uses the first
directly measured part's unit and records that unit in its proof. An explicit
output unit takes precedence; all stated durations are converted before
subtraction. Capability, negation and duration bounds do not establish an
exact completed total.

Implementation: [process grammar](../packs/arithmetic/rules/process-parts.yaml)
and [duration remainder](../src/rulekit/kernel/consumers/process_part_remainder.py).

An explicit unchanged-pace continuation supports a separate duration
projection from a timed first component. The partition must state equal
component sizes; a component count alone does not establish that equality.
Without it, the decline records the missing equality in its reason and proof,
separately from vocabulary or grammar deficiencies. The supported scope is
the whole or its remaining components, with compatible elapsed-time units
and matching participant, activity and whole references. This applies to
divisible objects and partitioned work. The rate is constructed only after
these conditions hold and is never stored as an observed general rate or
completed whole duration.

Implementation: [projection grammar](../packs/arithmetic/rules/uniform-processes.yaml)
and [equal-part projection](../src/rulekit/kernel/consumers/uniform_partition_duration.py).
Paraphrases, generated surfaces and ambiguity boundaries are covered in
[projection tests](../tests/test_uniform_partition_duration.py).

## Population-weighted periodic amounts

A reported per-member average and its population share establish a subgroup
total. An explicit complementary group completes the binary partition. The
observer, population descriptions, repeated population count, attribute,
currency and periods must agree. Group sizes must be positive whole counts;
missing complements and overlapping unnamed shares decline. The reported
averages are per member, rather than a second aggregate amount. Inquiry and
source-attribution clauses add context without asserting additional receipts.

Implementation: [population rate grammar](../packs/arithmetic/rules/population-rates.yaml)
and [weighted amounts](../src/rulekit/kernel/consumers/population_rate_total.py).

Invented examples, paraphrases and ambiguity boundaries for these compositions
live in [partitioned resource tests](../tests/test_partitioned_resource_questions.py).

## Indexed acquisition balances

Indexed acquisitions and successive multi-period blocks form a contiguous
sequence. Explicit block totals and per-period rates retain different scopes;
actual partitive transfers subtract from the identified acquisition. A purpose
clause with a modal purchase does not assert another completed transaction.
Participant, resource, period, collection source and transfer references must
agree, and the question must identify the observed sequence's endpoint.

A multi-period amount without an explicit total or rate requests clarification.
The ordinary caller interpretation selects a block-total or per-period reading;
it cannot override explicit evidence or bypass identity and coverage checks.
Multiple independently ambiguous blocks require explicit wording. A recurring
duty supplies context without silently making the observed amounts uniform.

Implementation: [period grammar](../packs/arithmetic/rules/periodic-resource-balances.yaml)
and [acquisition balance](../src/rulekit/kernel/consumers/periodic_resource_balance.py).

## Reconstructing equal container contents

An explicit equal-content stock can be reconstructed from a retained count
and the entire remainder shared among a stated number of recipients with
known individual shares. The container count, retained amount, recipients,
and share remain separate operands. Their identities and event order must
agree; discrete contents must divide into whole counts. Equal contents are
required evidence and are never inferred merely from identical containers.

Implementation: [distribution rules](../packs/arithmetic/rules/equal-content-distribution.yaml)
and [uniform contents](../src/rulekit/kernel/consumers/uniform_content_distribution.py).

## Allocation roles and equal shares

Allocation recipients include living agents, organizations, devices, physical
stores, and financial accounts. Receipt eligibility does not grant intention,
personal-pronoun eligibility, or the ability to collect and divide resources;
nested collection grammar retains its separate actor role.

Actual active transfers and passive distributions preserve the source pool,
resource, units, and counted recipient class. The uniform-distribution consumer
also computes forward shares: subtract any explicit retention and divide by
the recipient count. Ordinary monetary holdings remain `Quantity` facts and
are adapted locally when an actual allocation identifies their use. Requirements,
capacity, hypothetical transfers, missing equality, conflicting recipient
descriptions, and indivisible discrete shares decline.

An opted-in impersonal subject can continue a unique prior nonliving resource
actor in a usage, retention, or allocation clause. This uses the ordinary
reference arbiter, admits prior grammatical subjects, and leaves competing
actors unresolved.

Implementation: [recipient categories](../packs/core-english/categories/distribution.yaml),
[allocation grammar](../packs/arithmetic/rules/resource-distribution.yaml), and
[uniform distribution](../src/rulekit/kernel/consumers/uniform_content_distribution.py).
Executable examples and boundaries: [measured resources and allocations](../tests/test_measured_resources_and_allocations.py).

## Package quotes and expenditure comparisons

A completed purchase can retain its package count before a separate quote
supplies the price. Ordinary `Quantity` facts retain typed measure and content
references from the reader's partitive bindings. The comparison adapts them
locally into expenditure operands, preserving existing container-content
derivations. `Price.per` and `Price.measure` retain the quoted package and
currency. The existing expenditure-price evaluator computes the two item
subtotals, which are subtracted in the requested direction. Each quote
must match the contents and package; all purchases and quotes must belong to
one complete ledger. A scoped quote cannot be counted as an ordinary item
price by another consumer without explicit accounting.
Both distributive package-first and content-first per-package quotes preserve
that denominator; a price per package cannot become an unqualified item price.

Implementation: [quote rules](../packs/arithmetic/rules/quoted-purchases.yaml)
and [item expenditure comparison](../src/rulekit/kernel/consumers/item_expenditure_comparison.py).

## Successive allocations and a stored loss

A received monetary pool may remain an ordinary `Quantity` until a local
consumer composes it with ordered fractional allocations. A fraction of the
opening pool and a fraction of its remainder have distinct markers. Transfers
retain the destination's owner and modifiers; they are not spending. The
remaining balance must be explicitly located before a loss can use that
store. Losing everything except a survivor subtracts the survivor from that
balance. Missing locations, overlapping store descriptions, incompatible
owners, extra events, and excessive survivor amounts decline.
Work context need not name a location. Allocation destinations may be explicit
without a possessive, but an account and a reserve description cannot silently
be treated as different stores. Destruction, consumption, and theft all support
owner-relative loss when they identify the same stored pool. A definite store
can refer to the unique earlier location; an indefinite store cannot establish
that reference. An exception separated from the loss by another event is not
silently assigned back to the loss.

Implementation: [resource remainder rules](../packs/arithmetic/rules/resource-remainders.yaml)
and [stored resource loss](../src/rulekit/kernel/consumers/stored_resource_loss.py).
Executable analogues, paraphrases, and decline boundaries for these families:
[resource composition tests](../tests/test_resource_composition_families.py) and
[alternate phrasings](../tests/test_resource_alternate_phrasings.py).

## Related composition contracts

[Logic and arithmetic](logic-arithmetic.md) materialize applicable class
constraints before ordinary arithmetic runs. [Composed-family tests](../tests/test_composed_question_families.py)
and [composed costs and allocations](../tests/test_composed_costs_and_allocations.py)
exercise other complete questions and deliberate declines.

A generic operation is not permission to flatten every aggregate into a
`Quantity`, infer a missing rate, or discard an unused event. The distinction
between evidence and a coincidental arithmetic result is a
[project design constraint](negative-results.md).
