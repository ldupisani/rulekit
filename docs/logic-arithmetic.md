# Logical classes and arithmetic

The opt-in logic layer preserves logical statements as typed evidence. The
narrow logic/arithmetic bridge uses exact membership and class constraints to
produce ordinary arithmetic facts. It shares the existing quantity consumers
and accounting machinery rather than introducing another numeric evaluator.

## Pack boundaries

[The logic pack](../packs/logic/pack.yaml) provides its declared logical
readers and synthesis. Supported facts include phrase-keyed atoms, quantified
statements, implications, disjunctions, and verbal relations. The accepted
fragment is defined by those rules; loading the pack does not enable general
first-order theorem proving.

[The logic/arithmetic pack](../packs/logic-arithmetic/pack.yaml) is a narrower
bridge loaded by curated. It depends on core English and arithmetic without
loading the broad logic reader surface. The ordinary FOLIO safety project
remains a separate arithmetic-only configuration.

## Exact class quantities

A `QuantifiedQuantity` states a quantity for members of a complete class key.
Positive `Membership` or an appropriate `Atom` can license materialization for
a particular participant. A related but nonidentical class, an existential
statement, or an unproved membership does not establish the universal quantity.

The materializer emits ordinary `Quantity` facts and preserves conflicting
explicit quantities rather than choosing the convenient one.

Implementation: [bridge readers](../packs/logic-arithmetic/rules/core.yaml),
[bridge synthesis](../packs/logic-arithmetic/synth.yaml), and
[kernel synthesis](../src/rulekit/kernel/saturate.py).

## Role derivation and refinement

Pack-declared verb/role mappings can derive a nominal role from an exact
verbal relation. The mapping must preserve the argument, preposition, and
restriction that licensed it. An arbitrary verb or preposition cannot create
a matching membership because its wording seems related.

`ClassRefinement` represents a declared subclass relationship. It differs
from an arithmetic subset and from intersective predicate decomposition.
Refinement retains the complete restricted superclass; dropping its location
or participant restriction would widen the claim.

Definitions: [role categories](../packs/logic-arithmetic/categories/roles.yaml)
and [fact model](../src/rulekit/kernel/model.py).

## Additive class adjustments

A class-scoped adjustment requires a unique compatible inherited baseline.
It is not an unanchored relation to an arbitrary class. Multiple compatible
baselines, missing memberships, undeclared refinements, and contradictory
explicit states must not produce a shortcut answer.

Question-local assumptions can supply a supported membership for that solve.
They do not persist to later questions or turn an assumed state into an actual
one. Explicitly named groups preserve their requested scope; per-holder asks
can return a labelled series instead of a sum.

Tests: [quantified quantities and bridge contracts](../tests/test_logic_quantified_quantity.py).

## Logical verdicts and uncertainty

Logical consumers use the appropriate phrase-keyed and polarity-bearing
facts. Full question coverage matters: reading only an unqualified head cannot
justify a verdict about a restricted phrase. Unsupported or conflicting
premises cannot be treated as a successful negative or uncertainty answer.

Implementation: [logic verdict](../src/rulekit/kernel/consumers/logic_verdict.py)
and [disjunction verdict](../src/rulekit/kernel/consumers/logic_disjunction_verdict.py).
Tests: [logical verdicts](../tests/test_logic_verdict.py),
[verbal logic](../tests/test_verbal_logic.py), and
[quantifiers](../tests/test_stage4_quantifiers.py).

See [the corpus reference](corpora.md) for the distinction between opt-in logic
capability and FOLIO's independent arithmetic safety role.
