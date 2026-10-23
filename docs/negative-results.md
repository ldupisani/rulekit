# Design constraints and failure modes

These principles explain the project's architecture and testing discipline.
The binding constitution and implementation workflow live in
[CLAUDE.md](../CLAUDE.md); this document supplies rationale and implementation
references rather than a second copy of those instructions.

## Evidence must determine the operation

Reaching a target number by some arithmetic expression is not evidence that
the text states that expression. Typed quantities, roles, units, and scope
must license each operation. Test reachability diagnostics against shuffled
or unrelated targets before treating their apparent success as useful signal.

[Typed composition](composition.md), [rates](../src/rulekit/kernel/rate_calculation.py),
and [numeric evidence](../src/rulekit/kernel/numeric_evidence.py) implement
parts of this discipline.

## Identity precedes numeric disagreement

Equal amounts do not make two labeled containers or two owners the same
participant. Preserve nominal heads, owners, labels, and qualifiers before
folding values. A matching noun or a shared string is insufficient evidence
of reference identity.

Implementation and boundaries: [reference identity](../src/rulekit/kernel/reference_identity.py),
[identity tests](../tests/test_reference_identity.py), and
[reference resolution](deixis.md).

## A whole is not one of its parts

A bare total cannot automatically become a count of red items, one owner's
items, or a particular sample. A later omitted modifier may inherit a class
only through a validated, unique discourse reference. Explicit rival classes,
whole-total language, and unrelated events must remain visible.

Implementation: [item references](../src/rulekit/kernel/item_references.py),
[quantity projections](../src/rulekit/kernel/totals.py),
[item-reference tests](../tests/test_item_references.py), and
[mixture ledgers](composition.md#mixture-ledgers).

## Use is different from existence

A rate or price being present does not show that an answer used it. Conversely,
a fact consumed as a per-unit rate must not also be added as an ordinary stock
quantity. Record actual use at the operation that consumes evidence, and keep
original facts and their provenance inspectable.

Implementation: [arithmetic log](../src/rulekit/kernel/evaluate.py),
[accounting guards](../src/rulekit/kernel/guards.py), and
[composition](composition.md).

## Taxonomy does not establish an exhaustive population

Knowing that two types belong to a category does not establish that they are
all the category's members in a question. Named conjunctions, declared
partitions, and explicit totality evidence can establish a closed scope;
category membership alone cannot. An unknown third class cannot silently
vanish from a remainder or aggregate.

Implementation: [totals](../src/rulekit/kernel/totals.py),
[partition synthesis](../src/rulekit/kernel/saturate.py), and
[qualified comparison tests](../tests/test_qualified_comparison_chain.py).

## Unknown, negative, and declined are distinct

Silence does not establish negation. Failure to read a sentence is not an
inference that its conclusion is uncertain. Missing location evidence is not
proof that a person is elsewhere. Unknown and contradicted witnesses remain
different outcomes, and contradictory evidence cannot be resolved by picking
the most convenient branch.

Implementation: [logical verdicts](../src/rulekit/kernel/consumers/logic_verdict.py),
[location witnesses](../src/rulekit/kernel/consumers/location_witnesses.py),
[typed gold tests](../tests/test_typed_gold.py), and
[location tests](../tests/test_temporal_location_witnesses.py).

## Time and hypothetical scope cannot be reconstructed from a lemma

Lemmatizing a predicate does not preserve all tense or event information.
Explicit temporal labels support exact selection; arbitrary ordering needs
additional evidence. A goal is not a completed event, and a question assumption
is not an actual holding. Derived values must preserve relevant provenance.

Implementation: [temporal evidence](../src/rulekit/kernel/temporal.py),
[clause scope](complementizers.md), [synthesis](../src/rulekit/kernel/saturate.py),
and [temporal ask tests](../tests/test_temporal_ask_evidence.py).

## More coverage exposes latent errors

A vocabulary addition, new ask, or broader reader can activate unsafe paths
that previously declined for unrelated reasons. Test shared mechanisms across
their callers and negative boundaries. An unchanged correct-answer count does
not show that no new wrong answer was introduced.

[Testing methodology](methodology.md) describes outcome diffs, the full
synthetic gate, relevant independent corpora, and the protected evaluation
boundary. [Guards](../src/rulekit/kernel/guards.py) enforce the final commitment
contract; documentation alone cannot enforce an invariant.

## The logic-corpus search

A corpus assembled from a predecessor's demonstrations measures coverage of
those examples. It does not establish independent generalization. A corpus
with only affirmative labels cannot distinguish inference from an always-yes
engine. A templated generator's breadth also requires independent evaluation.

FOLIO supplies a distinct logical safety role: its `Uncertain` label remains
a positive logical claim, not a successful decline. The arithmetic-only
project and the opt-in logic readers are separate configurations. See the
[corpus reference](corpora.md) and [logic reference](logic-arithmetic.md).

## Reviews do not become runtime knowledge

Human acceptance, generated examples, recorded solver output, and benchmark
gold have different roles. Reviews are authoring evidence with append-only
history. They do not supply missing runtime premises or justify a broader
inference by themselves.

The [authoring workbench](authoring-workbench.md) documents those boundaries.
