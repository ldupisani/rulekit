# Semantic graph projection

Semantic projection exposes the meaning structures the reader actually emitted.
It is separate from numeric answering and from human review. A partial graph
must remain partial; a harness adapter or display cannot invent absent meaning.

## Runtime representation

`SemanticGraphNode` and `SemanticGraphEdge` represent supported nodes, types,
roles, and edges with provenance. Pack rules declare the language frames and
vocabulary. Unknown roles, unsupported attachment, and missing scope remain
missing rather than being guessed from word order or sentence plausibility.

Implementation: [fact model](../src/rulekit/kernel/model.py),
[projection reader pack](../projects/cogs/packs/semantic-projection/pack.yaml),
[reader rules](../projects/cogs/packs/semantic-projection/rules/semantic.yaml),
and [role boundaries](../projects/pmb/packs/role-boundary/pack.yaml).

The output is not a general-purpose semantic parser for arbitrary English.
A schema field or recognized noun does not establish support for the sentence's
argument, modifier, quantifier, or embedded-clause structure.

## Harness adapters

The COGS adapter normalizes its declared logical-form representation. The PMB
adapter maps only supported explicit SBN/DRS structure. These adapters are
benchmark-side expected-meaning and comparison machinery; they are not imported
into runtime reading to supply missing facts.

The COGS configuration permits its compatibility bridge from supported
`VerbalRelation` evidence. The independent PMB project sets `legacy_bridge:
false` and scores explicit semantic graph facts. This difference is part of the
measurement contract, not an interchangeable scoring convenience.

Implementation: [projection harness](../src/rulekit/harness/projection.py),
[COGS configuration](../projects/cogs/project.yaml), and
[PMB configuration](../projects/pmb/project.yaml).

## Graph outcomes

| Outcome | Meaning |
| --- | --- |
| Exact | The normalized predicted graph matches the supported gold graph |
| Partial | The prediction is sound but omits required structure |
| Declined | No usable projected structure was committed |
| Incorrect | The prediction introduces unsupported structure |

Node/edge normalization and role alignment belong to the declared adapter.
A correct lexical edge does not excuse an invented role or attachment.
Coverage and completeness must be reported separately from edge precision.
Unsupported gold structure is tracked by the adapter rather than treated as
permission to fabricate a runtime edge.

Tests: [COGS](../tests/test_cogs_projection.py),
[PMB](../tests/test_pmb_projection.py), and
[Designer projection](../tests/test_server_semantic_projection.py).

## Inspection and review

The Designer presents projected nodes, edges, source spans, and available
provenance. A graph view is diagnostic evidence, not a second inference
engine. Review records retain the facts actually emitted and cannot silently
upgrade an earlier review to a richer graph after code changes.

See [the workbench reference](authoring-workbench.md) and
[reference resolution](deixis.md) for adjacent evidence models.

## Evaluation and integration boundary

Projection corpus policies, calibration contamination, and licence filters are
specified in [the corpus reference](corpora.md) and committed builders.
Protected TEST/generalization access is aggregate-only, separately authorized,
and ledgered by [the projection firewall](../src/rulekit/cli.py).
Existing ledger entries do not authorize another look or item inspection.

Projection-to-question/inference integration remains parked. Available graph
output is not permission to use an unvalidated subgraph to answer a numeric
or logical query. The separate external semantic-generator candidate is not
an approved importer or source of runtime facts. Resuming that work, sealing
that candidate, or importing it requires explicit user direction under
[the project instructions](../CLAUDE.md).
