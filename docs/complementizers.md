# Clause scope and question assumptions

Clause markers affect what a sentence asserts. A comparative standard,
conditional premise, goal infinitive, relative clause, and reported statement
cannot all be treated as independent factual sentences.

RuleKit supports explicit constructions through grammar and conservative
clause routing. It does not provide a general-purpose English clause tree or
a general theory of factive predicates.

## Question-local assumptions

[Question routing](../src/rulekit/kernel/engine.py) recognizes supported leading
and trailing conditional frames. Grammar can also own a complete question,
preventing a convenient text split from changing its meaning. Declared
question-assumption permission governs supported promotions.

Pack-defined `question_assumption_introducer` markers also support a leading
participial assumption followed by a comma and a question. Promotion requires
one complete read rule with `question_assumption: true`; an arbitrary embedded
clause does not qualify. The unchanged-pace projection grammar uses this for
`assuming`, alongside a conditional or a standalone ability statement. The
continuation licenses a projection rather than asserting completed work.

An accepted conditional premise is read with `Reading.assumption`; emitted
facts carry `Provenance.assumption`. These facts belong to that solve. They
do not establish an actual holding or persist as learned knowledge for the
next question. Ordinary relation derivations retain a hypothetical anchor's
assumption flag.

Examples and isolation tests are in
[logic/quantity tests](../tests/test_logic_quantified_quantity.py),
[item-reference tests](../tests/test_item_references.py), and
[composed questions](../tests/test_composed_question_families.py).

## Grammatical boundaries

[Obligation binding](../src/rulekit/kernel/obligations.py) checks supported
clause boundaries when assigning arguments. Specific relative-clause and
complementizer constructions carry their own licensing conditions. A token's
lexical sense does not imply that every subordinating construction is supported.

Supported independent conjoined clauses are split conservatively. Shared
subjects, relative clauses, comparisons, and noun-phrase conjunctions must
retain their construction-specific interpretation. A conjunction category is
not permission to assert both sides of every conditional or disjunction.

Implementation: [engine routing](../src/rulekit/kernel/engine.py),
[obligations](../src/rulekit/kernel/obligations.py), and
[structural learning](../src/rulekit/kernel/learn.py).
Tests: [conjoined relations](../tests/test_conjoined_relation.py) and
[conjoined existentials](../tests/test_conjoined_existential.py).

## Comparison clauses

A repeated standard predicate must agree with the main activity where the
comparison grammar requires that agreement. Supported do-support and omitted
standard predicates inherit that same activity; an explicitly different
activity is not silently discarded.

Content-qualified comparisons preserve the stated item context. Any later
omission of that qualifier is resolved through the separate
[item-reference mechanism](deixis.md), rather than by deleting the qualifier
from the original comparison.

Implementation: [predicate comparisons](../packs/arithmetic/rules/predicate-comparisons.yaml).
Tests: [comparison paraphrases and boundaries](../tests/test_composed_question_families.py).

## Goals, reports, and limits

A goal or intended event is represented separately from a completed event.
Understanding an infinitive does not establish that it happened. Similarly,
the presence of an embedded clause does not by itself establish its truth.
Unsupported embeddings require a suitable meaning-preserving reader; splitting
at a marker is not a substitute for an assertion contract.

Tests for supported goal constructions are in
[generic goal predicates](../tests/test_generic_goal_predicates.py).
Broader logical implication and negation belong to the opt-in
[logic model](logic-arithmetic.md), not unconditional quantity learning.
