# Logic–arithmetic integration plan

**Updated:** 2026-08-12
**Status:** L0 through L6 complete and gated; further work is review-led

## Goal

Let exact logical statements establish which arithmetic constraints apply to
which entities, then hand ordinary `Quantity` and relation facts to the existing
arithmetic consumers. Logic selects the applicable premises; it does not create
a second arithmetic evaluator.

The motivating question is:

> All teachers at the university have 20 students. All head teachers have 5
> more students. Bob and Mary teach at the university. If Bob is the head
> teacher, how many students does he have?

The intended answer is 25 only when all four links are established:

1. teaching at the university licenses the role *teacher at the university*;
2. *head teacher* is declared to refine *teacher*;
3. “5 more students” has exactly one compatible inherited baseline (20);
4. “he” resolves strictly to Bob in the local hypothetical context.

If any link is missing or ambiguous, RuleKit must decline or request
clarification. In particular, “5 more” must not pick an arbitrary comparison
class when two compatible baselines are in scope.

## Implemented foundation

### L0 — reusable pack boundary

The former `projects/scratch/packs/logic` implementation now lives at
top-level `packs/logic`. Scratch, COGS, and PMB reference it by pack name. The
ordinary FOLIO project remains logic-free and therefore remains the standing
0-commit safety gate.

The curated project now explicitly opts into the narrow
`packs/logic-arithmetic` bridge. It does not load the broad FOLIO reader
surface: that experiment changes unrelated arithmetic premise consumption.
This makes the exact class/quantity surface available in the Designer and
ordinary curated solves without changing the FOLIO safety contract or the
curated generator's compact vocabulary domain.

### L1 — exact quantified quantities

`QuantifiedQuantity(cls, measure, value, verb)` represents a class-wide numeric
holding. The reader now maps:

```text
All teachers at the university have 20 students.
```

to:

```text
QuantifiedQuantity(
  cls="teacher at university",
  measure="student",
  value=20,
  verb="have"
)
```

The shared universal-quantity materializer instantiates that constraint only
from an exact positive class-membership fact. Restricted phrases use `Atom`;
simple copular membership reuses the existing `Membership` fact. Both paths
join the complete class key. They emit a normal `Quantity`, so the established
arithmetic consumer and proof path answer the question. They do not match a related class, drop a PP
restriction, hide a contradictory explicit amount, or treat an
existential/coordinate amount as universal.

This supported form now answers 20:

```text
All teachers at the university have 20 students.
Bob is a teacher at the university.
How many students does Bob have?
```

All three bridge premise rules are deterministic Generate-mode targets. The
completed L1 gate passes 4,455 tests and curated 66/66. GSM8K DEV-train and
DEV-holdout remain 108/0 and 43/0; ASDiv, SVAMP, MAWPS, and SciBench remain
45/0, 30/0, 11/0, and 6/0; FOLIO makes zero commitments; and every snapshot
diff is neutral. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision. No protected TEST or generalization look was spent.

### L2 — structured coordinated role statements

`logic-arithmetic/coordinated-named-verbal-pp` reads
`Bob and Mary teach at the university` as one binary coordinated clause. It
emits one structured `VerbalRelation` per named conjunct rather than inventing
two surface parses. The matched rule explicitly discharges the verb's subject
obligation with the `PATTERN` sentinel: the subject is the complete
coordination, so neither Bob nor Mary is falsely selected as the sole
grammatical subject.

The pack-owned `subject_role_derivations` table licenses exact verb and
preposition pairs. Its current `teach + at → teacher` entry preserves the
complete PP object, and the generic synthesizer therefore emits
`teacher at university` for both Bob and Mary. The mapping and its source line
are inspectable. Python implements only the table join; it contains none of
the words in that mapping.

Disjunction, repeated conjuncts, singular verb agreement, coordinated PP
objects, and additional PP material do not match. An unlicensed verb or
preposition may still produce its literal verbal relation, but cannot derive a
nominal role. The reader and all four bridge rules are deterministic Generate
targets.

The completed composition now answers 20:

```text
All teachers at the university have 20 students.
Bob and Mary teach at the university.
How many students does Bob have?
```

The L2 gate passes 4,459 tests and curated 67/67 with all 112 premise rules
selectable. All answer-corpus DEV diffs are neutral: GSM8K remains 108/0 and
43/0; ASDiv, SVAMP, MAWPS, and SciBench remain 45/0, 30/0, 11/0, and 6/0;
DIFG remains 75/0; and FOLIO makes zero commitments. COGS DEV-train/holdout
and PMB train/development retain 100% projected-edge precision with zero
incorrect graphs. Lint has zero errors. No protected TEST or generalization
look was spent.

### L3 — declared class refinement

`ClassRefinement(subclass, superclass)` now records an explicit ontological
edge distinct from both arithmetic `Subset` and intersective predicate
decomposition. The pack-owned `refining_modifier` category currently declares
`head`. From any exact positive `Membership` or `Atom`, the generic synthesizer
therefore licenses:

```text
head teacher               → teacher
head teacher at university → teacher at university
```

It preserves the complete phrase after the single leading modifier and derives
the corresponding positive membership or atom. It never asserts that the
person is a `head`. A subclass-wide `QuantifiedQuantity` may expose the class
edge, but is not widened into a superclass-wide quantity.

This class ontology is separate from the established ordinary English
right-headed compound fold (`guard dog → dog`). Only a declared refining
modifier creates a `ClassRefinement` edge that later logic–arithmetic stages
may rely on. Exact `former teacher`, `fake teacher`, arbitrary undeclared
compounds, and negative `head teacher` facts create no such edge or derived
logic fact. The declaration is source-indexed for Designer inspection.

At the L3 boundary, the complete motivating diagnosis included
`ClassRefinement(head teacher, teacher)` while still declining: L4 had not yet
represented the class-scoped additive amount, and L5 had not yet made the
hypothesis/pronoun local and resolvable.

The L3 gate passes 4,465 tests and curated 67/67 with all 112 premise rules
selectable. Every L2-to-L3 answer-corpus DEV diff is neutral: GSM8K remains
108/0 and 43/0; ASDiv, SVAMP, MAWPS, and SciBench remain 45/0, 30/0, 11/0,
and 6/0; DIFG remains 75/0; and FOLIO makes zero commitments. COGS
DEV-train/holdout and PMB train/development retain 100% projected-edge
precision with zero incorrect graphs. Lint has zero errors. No protected TEST
or generalization look was spent.

### L4 — quantified additive refinements

`QuantifiedAdjustment(cls, measure, offset, verb)` now represents “All head
teachers have 5 more students” as a class-scoped numeric adjustment, not as the
existing entity-to-entity `Relation` and not as an opaque `Quantified`
predicate. The `generic_plural` slot accepts a complete compound generic while
still refusing a counted or possessive class, and `.qualified` preserves the
whole class key.

For one entity, the materializer may apply the adjustment only when:

- exact membership in the refining class is proven;
- a compatible base `QuantifiedQuantity` applies to that same entity;
- class refinement connects the adjustment to the base class; and
- exactly one base amount survives measure, verb, scope, and class checks.

The adjustment remains a first-class fact until the base is known. Ordinary
and adjusted quantified quantities share one materializer, so an applicable
adjustment suppresses its inherited baseline and emits one provenance-rich
derived value rather than competing 20 and 25 state quantities. Its arithmetic
log names both the base rule and the +5 adjustment rule.

When no baseline or multiple baselines survive, the active adjustment remains
unresolved and vetoes a numeric shortcut rather than being treated as an
acquisition event. An exact base class composes directly; a base with a
prepositional restriction may compose only when the same entity has exact
membership in that complete restricted class. Arbitrary shared prefixes do not
compose. Undeclared refinements, counted-class subjects, negative final values,
and explicit contradictions are fail-closed controls.

This non-hypothetical composition now answers 25 while leaving Mary at 20:

```text
All teachers at the university have 20 students.
All head teachers have 5 more students.
Bob and Mary teach at the university.
Bob is the head teacher.
How many students does Bob have?
```

The L4 gate passes 4,476 tests and curated 68/68 with all 113 premise rules
selectable and 189 reachable identities. Every L3-to-L4 answer-corpus DEV diff
is neutral: GSM8K remains 108/0 and 43/0; ASDiv, SVAMP, MAWPS, and SciBench
remain 45/0, 30/0, 11/0, and 6/0; DIFG remains 75/0; and FOLIO makes zero
commitments. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision with zero incorrect graphs. Lint has zero errors. No
protected TEST or generalization look was spent.

### L5 — local hypotheses and person deixis

The scoped question splitter now distinguishes an asserted premise from a
clause introduced by the current question's literal conditional frame.
`If Bob is the head teacher` becomes a `Reading` marked as a question
assumption. Direct fold and rule facts retain that provenance, the L4
materializer carries it into Bob's derived 25-student quantity, and diagnosis,
the engine trace, and the Designer API expose the scope explicitly. Every
`solve` constructs a new document; a second solve with the same registry sees
none of the first question's assumed facts.

Person resolution still uses the shared typed deictic resolver and its
strict-dominance rule. Ordinary multi-name discourse remains flat because the
kernel has no gender/person compatibility model: recency alone must not turn
`Tom ... Mary ... He ...` into a guess. A question-local assumption supplies
the narrower reference context. Within that context sentence distance is the
metric, so the assumption's Bob mention strictly dominates the older Mary
mention. Two compatible names in the same nearest assumption sentence remain
tied and unresolved.

The full motivating question now answers 25 and is the 69th curated item. The
L5 gate passes 4,481 tests and curated 69/69 with the unchanged 113/113 premise
generation frontier and 189 reachable identities. Every L4-to-L5 answer-corpus
DEV diff is neutral: GSM8K remains 108/0 and 43/0; ASDiv, SVAMP, MAWPS, and
SciBench remain 45/0, 30/0, 11/0, and 6/0; DIFG remains 75/0; and FOLIO makes
zero commitments. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision with zero incorrect graphs. Lint has zero errors. No
protected TEST or generalization look was spent.

A post-gate marker-parity follow-up adds the valid two-token “all together”
tail to the same variadic exact-name combined ask. It reuses the pack's narrow
`group_total_quantifier` and `quantified_group_total_marker` declarations, so
two or more named holders retain exact scope while `all total` and
`alltogether` remain rejected. The cumulative gate passes 4,484 tests and
curated 70/70. Every standing answer-corpus DEV diff is neutral, COGS/PMB
inspectable slices retain 100% edge precision with zero incorrect graphs, and
no protected look was spent.

A second post-L5 ask follow-up adds distributive multi-answer questions such
as “How many students do Bob and Mary each have?” The ask preserves the exact
coordinated name list and routes it through a new `per-holder` consumer. That
consumer reuses the same complete holder folds as `combined`, but returns an
ordered, JSON-native `series` of labelled entity/measure/value rows instead of
their sum. Missing or repeated holders decline the whole answer; an unrelated
same-measure holder remains outside the exact requested scope. A narrow
postpositive category licenses `each` but not the ungrammatical `every` form.
The API, Designer, diagnosis, and curated judge all carry the structured
answer without reducing it to `[25, 20]` or `[object Object]`. The motivating
question returns Bob 25 students and Mary 20 students.

The cumulative gate passes 4,491 tests and curated 71/71. All frozen standing
answer-corpus DEV diffs are neutral with zero breaks and zero
decline-to-wrong transitions. COGS DEV-train/holdout and PMB
train/development retain 100% projected-edge precision and zero incorrect
graphs. Lint has zero errors and the one known warning. No protected TEST or
generalization look was spent.

A marker-position follow-up routes three more accepted surfaces to that same
consumer: “have each”, “have individually”, and “individually have”. The
`each` siblings share the narrow quantifier category; `individually` is a
core-English adverb in its own individualizing category, so neither `every`
nor unrelated adverbs such as `separately` or `respectively` are admitted by
accident. No answer semantics, holder enumeration, or partial-result boundary
changes. The frontier is now 190 reachable identities. The cumulative gate is
4,493 tests and curated 71/71; every frozen answer-corpus DEV diff is neutral,
COGS/PMB inspectable slices retain 100% edge precision and zero incorrect
graphs, lint has zero errors and the known single warning, and no protected
look was spent.

## Final increment

### L6 — generation and review — complete

Expose every new reader and declarative mapping in Generate mode. Reviews must
be able to flag:

- an invalid universal scope;
- a bad verb-to-role derivation;
- an invalid class refinement;
- an ambiguous elided baseline;
- an incorrect hypothetical scope; or
- an incorrect pronoun antecedent.

Each derived fact and final arithmetic step should link back to the exact YAML
rule or mapping that licensed it.

The ordinary premise generator now covers every non-safety curated rule,
including all logic-arithmetic bridge rules. Source-indexed premise and fact
evidence enters the same append-only review, edit, resolve, tombstone, and
pinned-retest workflow as arithmetic rules. Fact snapshots retain the
emitting rule and, when unambiguous, its declarative template and bindings.
No logic-specific review store or runtime feedback path was introduced.

## Delivery gate

Each L increment is independently revertible and ships only with:

- synthetic positive, ambiguity, contradiction, and near-neighbour tests;
- curated suite coverage for the completed composition boundary;
- zero `BROKE` and zero `DECL→WRONG` across all standing DEV slices;
- unchanged FOLIO 0-commit safety behavior; and
- no protected TEST or generalization look unless the user explicitly spends
  one.

The full motivating question joins the curated suite only after L5 composes
with L4. Until then, the suite and focused contracts pin the exact L1
membership path, coordinated L2 role path, declared L3 class edge, and L4
non-hypothetical adjustment so later work cannot hide a broken foundation
behind the complete example.
