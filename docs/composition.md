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
An entity-less whole question cannot use a lone distributive content amount
when no compatible population total has been established.

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

Initial-group evidence requires the same holder class as the stated population,
a definite ordinal-before-count phrase, and compatible finite agreement. Floating
distributives retain a real `collection` binding to that group. Located frames
require anchored location references and pack-declared preposition/object
compatibility; carrier locations and ordinary spatial locations have separate
category licences.

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

An original-stock fraction may name the definite resource, refer to it by
pronoun, or omit it when the single measured stock and its actor establish the
source. The nominal remainder forms select the current balance; an optional
resource name must identify that same stock. Quantity references do not also
license a collective plural-subject construction. Omitting a production goal does
not change these bases. After depletion, a later sentence with an unqualified
fraction cannot silently choose between the original amount and the current
balance. A list that switches to the remainder cannot silently revert to the
opening base either. Uses may produce different types of products when the
question asks only for the remaining resource. A stated variety count still
requires the named product type and distinct full product references to agree.
Final-balance frames use the end of the stated sequence; they cannot absorb an
unstated later event or date. Simple mass, volume and length unit questions
also accept a period terminator while retaining their explicit physical
measurement basis.

Invented paraphrases, nonfood analogues, and decline boundaries:
[fractional resource references](../tests/test_fractional_resource_references.py).

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
population descriptions, any repeated count, stated observer, attribute,
currency and periods must agree. Group sizes must be positive whole counts;
missing complements and overlapping unnamed shares decline. The reported
averages are per member, rather than a second aggregate amount. Inquiry and
source-attribution clauses add context without asserting additional receipts.
Total-amount and how-much questions share rate wording (per, each, every) and
single-interval wording (a/an, in a/an). Both use the same declared period
conversions and population checks; mixed or missing period frames decline.
A counted fraction-of-population clause can establish the whole directly.
Its complementary rates remain tied to that same whole and sentence; a
complete immediately adjacent conditional reuses question-scoped assumptions.
Later definite plural references can reuse the uniquely stated population
without repeating its number. Calculation and determination activities preserve
the same inquiry scope without asserting a computed result or another receipt.

Implementation: [population rate grammar](../packs/arithmetic/rules/population-rates.yaml)
and [weighted amounts](../src/rulekit/kernel/consumers/population_rate_total.py).

Invented examples, paraphrases and ambiguity boundaries for these compositions
live in [partitioned resource tests](../tests/test_partitioned_resource_questions.py).
Counted wholes, assessment context and population-reference boundaries are covered
in [population tests](../tests/test_population_partitive_rates.py).

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
A single indexed-period amount does not create this scope ambiguity. Block
totals do not establish a breakdown within the block. Examples and boundaries
live in
[partitioned resource tests](../tests/test_partitioned_resource_questions.py).

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

## Scoped rate accounts

Each activity context retains its complete description and owner alongside
its rate and elapsed extent. Relative rates and extents name their standard,
or require one immediately preceding compatible quote. Every context must
have both operands before their products can be added. Currency questions
require monetary outputs; counts, currencies and elapsed units remain distinct.
Explicit reporting periods must agree. Otherwise the question supplies the
reporting period for the stated schedule. Reference forms, additional events,
competing standards and partial accounts are checked before commitment.
Reporting cadence may follow the activity context or its relative extent.
Compatible conjuncts share one stated cadence; conflicting cadences decline.
An explicit projection span multiplies the complete reporting-period account.
Its work duration remains an ordinary `Quantity` for existing duration queries.

Implementation: [scoped rate grammar](../packs/arithmetic/rules/scoped-rates.yaml)
and [component totals](../src/rulekit/kernel/consumers/scoped_rate_total.py).

## Attendance across separate schedules

A counted participant group in explicitly different activity groups supports
an additive attendance schedule. Its distributive event count, preparation
duration per event, and event duration remain separate operands. A matched
plural reference is validated against that one participant group. The observer
must match the participants' stated owner. Missing distribution, shared groups,
conflicting event identities and additional overlap conditions decline.
An optional calendar context uses the generic `timeperiod` category: “this
week,” “this month,” “this year,” and “this semester” have the same role as
“this season.” The event count is a total within that period, not a recurring
rate to multiply by an unstated number of periods.
Coordinated statements and comma-separated trailing questions use complete
grammar proofs on both sides. Readers must declare `independent_clause` for
the new coordinate routing; this cannot promote an embedded statement merely
because it precedes a question. Total markers retain their permitted
prepositions, including “in total.”

Implementation: [event schedules](../packs/arithmetic/rules/event-schedules.yaml)
and [attendance duration](../src/rulekit/kernel/consumers/schedule_attendance.py).

## Measured residual holder shares

A measured resource whole and a counted holder population can be partitioned
by one subset with explicit per-holder contents. Asking for each remaining
holder supplies the common residual-share reading for that remainder. It does
not establish uniform contents across the original population. Mass-amount
and explicit-unit questions share the calculation and conversion checks.
Empty remainders, fractional holder counts, incompatible units, excess known
contents and unrelated holder descriptions decline.
An explicit average divides the residual by the remaining holder count without
asserting equal individual contents. Equal sizes are capacity descriptions;
unequal sizes leave individual fill unspecified when a nonzero remainder is
present. A zero residual fixes every remaining nonnegative amount at zero.
Material varieties and compatible mass or volume conversions stay in the account.

Implementation: [measured partitions](../packs/arithmetic/rules/measured-holder-partitions.yaml)
and [uniform distributions](../src/rulekit/kernel/consumers/uniform_content_distribution.py).

## Recurring minimums and carried shortfalls

Named-day observations establish a consecutive actual performance history.
A minimum applies to each day, and uncompleted work carries forward. Excess
performance can clear existing arrears; future daily minimums are not prepaid.
Make-up intentions record a future day without asserting completed work.
In a complete named-day make-up question an otherwise unqualified target is
interpreted as daily; the answer reports this interpretation. An explicit
unsupported recurrence, missing day, conflicting participant or output unit
declines. The named-day goal interpretation also supports an abbreviated
question without repeating the make-up request; its answer reports the daily
interpretation. Weekday order comes from shared calendar attributes.
An explicit weekly quota uses one cycle total, so completed work can meet or
exceed that quota. Cumulative progress “by” a named day is distinct from work
done “on” that day; overlapping cumulative and daily observations cannot be
added. The remaining quota is capped at zero when it is already met.

Implementation: [performance goals](../packs/arithmetic/rules/performance-goals.yaml)
and [carried shortfalls](../src/rulekit/kernel/consumers/recurring_goal_shortfall.py).

## Closed source contributions

A listed source inventory and a question about its one missing contribution
support a complete target partition. This reading treats the listed sources
as accounting for the full target, and the answer reports that interpretation.
An intended target remains goal evidence; an actual measured outcome remains
an ordinary `Quantity`, adapted only within this closed partition. Direct measurements, whole-target fractions,
multiples of earlier contributions and fractions of the unassigned remainder
share the same conservation ledger. Remainders follow reporting order; seasonal
context identifies the source roles. Incomplete inventories, repeated source
heads, unresolved standards, excess contributions and incompatible physical
or monetary quantities decline. Directly observed source amounts also support
source-specific totals without a target or an exhaustive source inventory;
compatible units are converted before adding them.
Category-validated source lists may retain explicit modifiers and arbitrary
list lengths. Nominal changes such as a weight gain preserve their physical
basis. A possessive quantity question must identify the same recipient and
dimension; malformed possessives do not supply that reference.

Implementation: [source contribution grammar](../packs/arithmetic/rules/source-contributions.yaml)
and [source conservation](../src/rulekit/kernel/consumers/source_contribution_remainder.py).

Invented examples, paraphrases, generation and ambiguity boundaries for these
families live in [scoped composition tests](../tests/test_scoped_schedule_compositions.py)
and [alternate ledger tests](../tests/test_alternate_ledger_phrasings.py).

## Weighted product accounts

Explicit per-object contents and service earnings share a source-local product
ledger. A quoted service price stays an `EarningRate`; ordinary completed work
counts remain `Quantity` facts for existing count questions. Distributed
supplemental receipts supply additional earned amounts. A quote for several
service objects retains its denominator. Component groups retain separate counts
and explicit per-object amounts, including a single exceptional object. A plural
group without an explicit per-member statement cannot silently supply one.

Implementation: [account grammar](../packs/arithmetic/rules/weighted-accounts.yaml)
and [weighted totals](../src/rulekit/kernel/consumers/weighted_account.py).

## Projected installment balances

A planned purchase supplies a quoted target, not an actual payment or cash
holding. One complete payment policy states the initial percentage and recurring
installment. The projected balance subtracts that initial amount, any explicitly
additional deposit, and complete payment periods. Conflicting buyers, extra
charges, incompatible currencies or periods, and overpayment decline.

Implementation: [installment grammar](../packs/arithmetic/rules/installment-accounts.yaml)
and [projected settlement](../src/rulekit/kernel/consumers/installment_balance.py).

## Named ratio shares and personal depletion

An ordered `AllocationRatio` and a joint pool determine each named holder's
share. Named joint totals remain `GroupTotal` facts for existing comparison
equations. Fractions of what a holder has then reduce that holder's own share, in
order. A follow-up remainder pronoun requires one immediately preceding depleted
holder and compatible reference forms. A ratio between qualified resources does
not license an unqualified pool. Discrete shares and balances must be whole counts.

Implementation: [share grammar](../packs/arithmetic/rules/named-share-balances.yaml)
and [personal balances](../src/rulekit/kernel/consumers/ratio_holder_remainder.py).

## Required rates over a final interval

Named participants can have one explicitly individual target and deadline.
A shared competition course also licenses an individual target; this reading is
reported with the answer. Prefix averages are per stated observation period.
Each participant's observed intervals must be disjoint, consecutive and complete
up to the final interval. The consumer computes each required rate before taking
their arithmetic mean. It does not infer unobserved progress or a shared group
target. Numeric period labels are readable; their direct generation remains
disabled until the generator can preserve their index. Rules that capture a
named participant enumeration also retain the generator's span-realization
boundary.

Implementation: [progress grammar](../packs/arithmetic/rules/completion-rates.yaml)
and [required-rate mean](../src/rulekit/kernel/consumers/mean_required_rate.py).
Paraphrases, other contexts and decline boundaries for these families live in
[composition tests](../tests/test_payment_progress_compositions.py).

## Related composition contracts

[Logic and arithmetic](logic-arithmetic.md) materialize applicable class
constraints before ordinary arithmetic runs. [Composed-family tests](../tests/test_composed_question_families.py)
and [composed costs and allocations](../tests/test_composed_costs_and_allocations.py)
exercise other complete questions and deliberate declines.

A generic operation is not permission to flatten every aggregate into a
`Quantity`, infer a missing rate, or discard an unused event. The distinction
between evidence and a coincidental arithmetic result is a
[project design constraint](negative-results.md).

## Monetary denominations

`currency_measure` includes monetary dimensions and financial labels.
`currency_unit` is its concrete denomination subset, required by counted
transaction inputs. Cent/dollar conversion is declared in the ordinary unit
conversion table; no foreign exchange is inferred. Legacy scalar `Price` facts
retain their canonical denomination, while other denominations retain their
explicit unit and must pass a consumed-conversion guard. Affordability converts
both budget and selected unit price before division and refuses nonpositive
prices or an incompatible package basis. Dimensionless price comparisons
preserve the source denomination and package basis; an additive offset without
its own unit evidence cannot bridge a noncanonical denomination.

Implementation: [monetary units](../packs/core-english/categories/core.yaml),
[conversion helpers](../src/rulekit/kernel/monetary.py),
[capacity consumer](../src/rulekit/kernel/consumers/capacity.py), and
[boundary regressions](../tests/test_review_language_boundaries.py).

Currency glyphs come from the pack's currency registry. Pounds sterling have
their own denomination identity, separate from pounds of mass. A named activity
can total the participants' counted items at matching item or serving prices;
that quote does not establish payment. A sales cash account instead combines
actual sales and supplemental receipts, then subtracts explicit deposits from
cash on hand. Those deposits remain owned assets, so the result is not net worth.

Implementation: [activity accounts](../src/rulekit/kernel/consumers/named_activity_cost.py)
and [cash transfers](../src/rulekit/kernel/consumers/cash_transaction_balance.py).

## Relative inventories and measured partitions

Cross-item comparisons retain their source and predicate. An omitted comparison
standard can refer to the preceding item only within the same inventory clause.
The consumer resolves those affine links before summing the requested declared
category. Excluded items require a declared disjoint classification; absent
membership is not evidence of exclusion. Cycles, unknown standards, negative
counts and unread events decline.
An ordinary inventory statement keeps its existing `Quantity` representation.
The comparison-standard particles remain grammatical alternations: the premise
generator cannot yet realize a particle category. All item and predicate
vocabulary still uses category gates.

A measured participant partition retains ordinal identities separately from
the unit being measured. Known and relatively stated members must exhaust the
initial ordinal prefix; an explicitly equal remaining group shares the residual.
Population counts, measurement units and the requested remaining group must agree.

Implementation: [relative inventories](../src/rulekit/kernel/consumers/relative_item_total.py)
and [participant outcomes](../src/rulekit/kernel/consumers/participant_outcome_remainder.py).

## Capacity, projections and counted distributions

Container contents can combine a geometric capacity with a fractional fill and
ordered `MeasuredContentChange` evidence. Every spill or scale applies to the
current contents. Capacity uses the shared shape formulas and unit conversions.
A complete length, width and height specification for an unqualified container
uses the rectangular-prism interpretation and reports it with the answer when
the shape is unstated. Other descriptors require an explicit rectangular model
or shape clarification. Incomplete or conflicting dimensions decline. Unspecified
overflow and competing content streams decline. A measurement forecast instead
applies an explicitly directed rate over the stated time to the same event,
reporting a projected outcome rather than asserting a future observation.

Counted distributions distinguish packages, wholes and their component units.
Whole-package coverage rounds up only after establishing the complete recipient
count and units per recipient. A piece remainder subtracts the explicit serving
roster, including an owner only when listed, and counts a named role once.
For a stated provision purpose and complete recipient roster, explicitly
individual packaged units use one unit per listed recipient. The answer reports
this roster and serving interpretation. An explicit serving quantity overrides
it. Other missing serving requirements request clarification; insufficient stock declines.

Implementation: [container state](../src/rulekit/kernel/consumers/container_content_state.py),
[measurement projection](../src/rulekit/kernel/consumers/projected_measured_state.py),
and [unit distribution](../src/rulekit/kernel/consumers/unit_distribution.py).
Paraphrases and ambiguity boundaries live in
[composition regressions](../tests/test_composed_quantity_accounts.py).

## Scoped affine comparison graphs

Comparison nodes retain participant identity and, when relevant, the item class
or ordinal observation period. Additive and multiplicative links use one shared
affine graph. An inverse link can recover the standard's quantity from the
subject. Conflicting paths decline. Unanchored components keep a symbolic
origin: a difference can be determined when that origin cancels, without
asserting either participant's absolute age.

Accumulated activity durations require the same activity and an identified
comparison standard. Indexed averages require one comparison for every position
in the declared range, a matching baseline and compatible count units. A
frequency expression can count performances in each period; it is not a
multiplier of an unstated stock. Ordinary unscoped comparison readers refuse
the indexed suffix rather than discard it. Calendar month counts convert between
declared month and year units without assigning a fixed day length to a month.

A construction may use an already resolved pronoun as its reference target
only through an explicit referential contract. The shared reference projector
still checks the real antecedent, number, form agreement and conflicting links.
An unresolved pronoun cannot establish another pronoun's identity.
Patterns requiring a previously resolved possessor are marked reader-only
for standalone generation until their antecedent context can be realized.

Implementation: [affine constraints](../src/rulekit/kernel/affine_graph.py),
[scoped comparisons](../src/rulekit/kernel/consumers/scoped_comparison.py),
and [reference projections](../src/rulekit/kernel/reference_bindings.py).

## Dependent stocks and reporting periods

An additional ratio acquisition contributes to the buyer's initial stock; it
does not replace that stock with a total-count comparison. Both container counts
and their contents must match. Qualified holdings can be compared independently,
then combined and shared only through an explicit pooling event with the same
complete holder set. Discrete stock and equal shares must remain whole counts.

A relative preceding-period amount retains its activity and period unit. An
adjacent-period total requires the complete two-period window, either explicitly
requested or covered by an aggregate over the entire account; it does not
repeat a relationship over additional unstated periods. Existing commercial
basket counts can supply the same observed event count through a checked local
view. Their original evidence and accounting identity remain intact.

Implementation: [dependent quantity totals](../src/rulekit/kernel/consumers/dependent_quantity_total.py)
and [source footprints](../src/rulekit/kernel/source_coverage.py).

## Included blocks, measured quotes and available capacity

A duration tariff can state a fixed included block and a separate rate for
excess usage in the same reporting period. The excess rate prices only usage
above that threshold. Usage below the block requires an explicit prorating
policy. This differs from a percentage premium on a continuing base rate.

A measured unit quote can recover a purchase quantity from the decrease in cash
on hand for the single stated shopping purpose. The purpose supplies intent,
not an asserted purchase event or an extra quantitative operand. A scaled mass
measurement can instead determine a change in an asset's quoted value. It
does not assert a sale or incoming cash. Measurements, product identity, owners
and denominations must agree. Numeric syntax admits leading decimal fractions
with or without a registered currency symbol.

Uniform grouped capacity excludes the unavailable groups before counting their
units. Ordinal exclusions must fall within the declared structure and preserve any
explicit site owner. Available assignments also require explicit vacancy evidence; identical units alone do
not establish vacancy. A request for a qualified subset needs its own evidence.

Implementation: [threshold blocks](../src/rulekit/kernel/consumers/threshold_block_total.py),
[measured values](../src/rulekit/kernel/consumers/measured_value_account.py),
and [grouped availability](../src/rulekit/kernel/consumers/grouped_availability.py).
Invented analogues, paraphrases and refusal boundaries live in
[scoped composition tests](../tests/test_scoped_quantity_compositions.py).

## Calendar schedules and staged quantity accounts

A weekly schedule applies an ordinary daily baseline to its inclusive opening
window, replacing explicitly identified weekdays with their relative rates.
An approximate exception yields an approximate total. Named-month schedules
sum pack-declared month lengths and distinct daily portions. An explicit year
selects common or leap-year lengths; an unstated year uses the reported
non-leap assumption. Joint annual savings uses the reported convention of 365
earning days for both explicitly named participants. These conventions remain
local interpretations rather than universal year/day or month/day conversions.

A unit earnings rate includes changes to both pay and work duration. Uniform
product extents first expand the requested output before inverting its stated
production rate. Measured-item quotes retain physical units, currency and
relative standards; quote totals do not assert payment. Explicit input/output
calibrations compose observed inputs and a matching output price. Weather
observations are one input grammar; named material processing reuses the same
calculation.

An equal-face-value coin exchange preserves the initial value before a stated
subset is revalued. Ordinary coins retain face value, and both the exchange and
subset must contain whole coins. A transfer reconstruction connects recipient
outcomes through the shared affine graph, then adds the closing remainder.
Sectioned stock reconstruction adds an observed section to a complementary
section recovered from its exhaustive remaining list. Container, item, section,
recipient and currency identities are checked before arithmetic; unrelated
holdings, overlapping identities, incompatible units and unread changes decline.

Implementation: [calendar resources](../src/rulekit/kernel/consumers/calendar_resource_total.py),
[adjusted rates](../src/rulekit/kernel/consumers/adjusted_unit_rate.py),
[output extents](../src/rulekit/kernel/consumers/composite_output_duration.py),
[measured quotes](../src/rulekit/kernel/consumers/measured_quote_total.py),
[calibrated resources](../src/rulekit/kernel/consumers/calibrated_resource_value.py),
[exchange valuation](../src/rulekit/kernel/consumers/exchange_valuation.py),
[recipient stock](../src/rulekit/kernel/consumers/recipient_stock_reconstruction.py),
and [section stock](../src/rulekit/kernel/consumers/section_stock_reconstruction.py).
Invented examples and refusal boundaries live in the
[quantity account tests](../tests/test_calendar_and_quantity_accounts.py).

## Shared composition operations and domain roles

Component requirements use role unions over material resources, production
outputs and culinary subcategories. Divisible food and material wholes inherit
the same component structure. Fractional component use is an explicit event;
eating retains its edible-object restriction, and food-specific remainder
wording cannot identify an inedible whole. A single-actor fractional use without
a per-whole component population can reuse the ordinary fractional-stock ledger
through a local view. Its prior pool must match the actor, resource and any
explicit qualifier; the original evidence and conflict metadata remain intact. Being an allocation recipient does
not imply being an intentional initiator or having personal-pronoun eligibility.

Closed compositions share source coverage and numeric operand auditing through
[composition evidence](../src/rulekit/kernel/composition_evidence.py).
Consumers still establish admissible facts, identities, assumptions and account
scope before calling those checks. Shared finalisation credits only the batch
facts that the consumer validated. Older share accounts reuse source adapters
and full question references rather than reconstructing a receipt's syntax.

The [affine graph](../src/rulekit/kernel/affine_graph.py) also provides a directed
dependency mode. Component requirements and joint shares use this mode to keep
their anchored, acyclic-definition contract; they do not gain inverse or cyclic
inference merely by sharing graph arithmetic. Nodes retain their account or
product scope and measurement identity. A zero multiplier still needs an
established standard. [Fractional allocations](../src/rulekit/kernel/resource_equations.py)
likewise require an explicit original-stock or current-remainder basis for each
step. Reference interpretation and permission to switch bases remain caller
policies. [Ratio application](../src/rulekit/kernel/rate_calculation.py) retains
both source operands for specifications and observed calibrations without
asserting that their resources or application conditions are interchangeable.

[Pricing](../src/rulekit/kernel/pricing.py) resolves agreeing unit-quote
restatements within one caller-established scope. Agreement requires the same
item, qualifier and pricing basis; denominations must have a declared monetary
conversion. Conflicting quotes and incompatible currencies decline. Measured
quote lines convert their physical denominator before using the existing
expenditure price resolver. A quotation still does not establish payment.

[Geometric costing](../src/rulekit/kernel/consumers/measure_cost.py) is available
through the arithmetic pack and evaluates declared shape properties using the
same inherited formula and unit contracts as geometry and container capacity.
In the rectangular width-by-height site construction, an unlabelled axis uses
the other stated axis's unit, or the explicit quoted unit when neither axis
labels its unit. Explicit physical-unit modifiers take priority over the site's
noun. Other shape constructions state their parameter roles explicitly. Area
and linear pricing bases stay distinct; extra dimensions, restrictions and
unread conditions cannot be discarded.

Cross-domain examples, equivalent and conflicting quotes, scoped dependencies,
fraction bases and dimensional boundaries are exercised by
[generalised composition tests](../tests/test_generalised_compositions.py).
