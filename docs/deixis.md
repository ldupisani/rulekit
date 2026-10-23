# Reference resolution, time, and location

A deictic expression is interpreted relative to a reference point, or *origo*.
RuleKit shares a conservative arbitration mechanism across supported reference
constructions. Eligibility comes from typed evidence; proximity alone does
not establish a compatible participant or item.

## Arbitration

[The deictic resolver](../src/rulekit/kernel/deixis.py) represents candidates
with a dimension, identity, payload, and available position information. An
origo supplies the reference point. Caller-provided distances and filters
express the construction's evidence.

The winning candidate must be strictly nearer than every surviving rival.
Ties remain unresolved. With constant distance, this becomes exactly
“one compatible candidate or decline.” Filters only shrink a candidate pool;
they cannot supply an antecedent that was absent from the evidence.
The journal records candidates, exclusions, distances, and the result.

This primitive is shared machinery, not a universal nearest-mention rule.
A changed distance function changes interpretation and requires its own
regression evidence. See [resolver tests](../tests/test_mining_increment_116.py).

## Participant identity

[Reference identities](../src/rulekit/kernel/reference_identity.py) preserve
heads, owners, labels, qualifiers, and resolution status. Equal values do not
collapse distinct participants. A bare head may resolve to a unique compatible
identity, but competing owners or descriptions remain ambiguous.

[The document loop](../src/rulekit/kernel/document.py) binds supported personal
pronouns and possessors, then rematches changed readings. Plural subject groups
come from explicit discourse evidence; they are not assembled from every
holder with a matching quantity unit.

Tests: [identity](../tests/test_reference_identity.py),
[reference bindings](../tests/test_reference_bindings.py), and
[personal coreference](../tests/test_animate_coreference.py).

## Item-class references

A qualified comparison can establish an item class for its participants and
activity. A later bare counted object may inherit that class only when the
prior evidence leaves one interpretation. The literal count remains unchanged;
an inspectable `ItemClassReference` records the link used by an arithmetic view.

The link requires compatible participant, predicate, item, and temporal scope.
It cannot come from the ask alone, a future mention, an unrelated participant,
or a convenient number. Rival classes and explicit whole-total wording block
an unsupported subset interpretation.

A question-local hypothetical count may use an actual comparison's item
context. Its assumption flag remains attached to the stated count and derived
quantities. A hypothetical antecedent cannot establish an actual item context.

Implementation: [item references](../src/rulekit/kernel/item_references.py).
Tests: [item-reference contracts](../tests/test_item_references.py) and
[comparison chains](../tests/test_composed_question_families.py).

## Temporal evidence

Opaque calendar labels support equality selection, not arbitrary temporal
ordering. Explicitly timed same-activity events may be summed in supported
unscoped questions; mixed timed/untimed evidence and unrelated activities
cannot silently become one history.

`Provenance.temporal_perspective` retains supported finite-surface distinctions
that a verb lemma cannot express. Pack-declared relative markers can emit
`EventTime`; distinct supported offsets can derive `Before` between events.
Question interpretation supplies a temporal origo where the declared ask
supports it. Duration conversion does not establish an event's calendar time.

Implementation: [temporal normalization](../src/rulekit/kernel/temporal.py),
[reading](../src/rulekit/kernel/learn.py), and
[question interpretation](../src/rulekit/kernel/answer.py).
Tests: [temporal asks](../tests/test_temporal_ask_evidence.py) and
[deictic events](../tests/test_temporal_deictic_events.py).

## Location evidence

Declared preposition/object/verb frames preserve location, source, goal, and
path roles. Supported `LocationEvent` facts share event identity with temporal
evidence. A finite-domain witness query can distinguish supported, contradicted,
unknown, and conflicting location evidence.

An explicit impossible transition and an explicit absence of departure are
different facts. Neither means that every unmentioned transition is impossible.
There is no general containment geometry, route planner, or distance inference
in this reference mechanism.

Implementation: [location witnesses](../src/rulekit/kernel/consumers/location_witnesses.py).
Tests: [spatial prepositions](../tests/test_spatial_prepositions.py) and
[temporal location witnesses](../tests/test_temporal_location_witnesses.py).

The Designer exposes this evidence through its deictic field and semantic
views. See [the workbench reference](authoring-workbench.md).
