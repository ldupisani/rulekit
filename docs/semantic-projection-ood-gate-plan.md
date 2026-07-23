# Semantic projection independent OOD gate preregistration

**Status:** candidate selected conditionally; no data downloaded and no
evaluation rows inspected

**Selected candidate:** Parallel Meaning Bank (PMB) 5.1.0, English gold
meaning representations

**Hard blocker:** confirm an explicit licence covering redistribution and
benchmark use of the PMB data archive. The official data page provides stable
downloads and citation instructions but does not state a dataset licence in
the visible release metadata. Do not download the archive or begin an adapter
until this is resolved from an authoritative source.

## Why this gate exists

COGS checkpoint 1 is spent and cannot be rerun. Its generalization aggregate
failed on proper-object ditransitives, so additional COGS DEV coverage cannot
unlock the original Phase E. The missing evidence is independent
out-of-distribution transfer of the repaired semantic graph at the existing
precision-first standard.

This gate is projection-level evidence only. It does not replace the later
FraCaS inference gate and does not authorize answer-level claims.

## Candidate decision

### Primary — PMB 5.1.0 English gold

Conditionally selected because:

- PMB supplies compositional Discourse Representation Structures with
  entities, predicates, thematic roles, discourse structure, and
  coreference—substantially closer to Rulekit's semantic graph than a
  database query language;
- the official release page reports 11,987 English gold instances in version
  5.1.0 and distinguishes fully human-corrected gold data from silver and
  bronze data;
- PMB5 defines a systematic split intended to reduce overlap and adds a
  dedicated compositional-generalization challenge set; and
- PMB is independently authored and represented, unlike an extension of the
  COGS grammar.

Primary sources:

- <https://pmb.let.rug.nl/data.php>
- <https://aclanthology.org/2024.dmr-1.17/>

### Rejected as the independent gate — SLOG

SLOG is a useful future diagnostic but not independent evidence: its paper
states that it extends COGS with 17 structural-generalization cases and
recommends the original COGS logical form. It inherits the grammar,
representation, and much of the vocabulary family whose transfer is in
question.

Source: <https://arxiv.org/abs/2310.15040>

### Rejected as the primary gate — CFQ

CFQ is openly distributable from Google Research (datasets are CC BY 4.0),
but its target is Freebase SPARQL for English questions. A conversion would
test knowledge-base query normalization more than sentence-level
entity/event/role projection. Retain it only as a possible later
question-consumer diagnostic.

Source: <https://github.com/google-research/google-research/tree/master/cfq>

## Frozen scope

If the licence blocker clears, pin before inspecting any evaluation item:

1. the exact PMB archive version, URL, SHA-256, and citation;
2. English **gold** meaning representations only—no silver or bronze data;
3. the release-provided systematic train/development partition for adapter
   development;
4. exactly one protected evaluation partition: the release-provided English
   compositional-generalization challenge set, if its membership and gold
   status are present in the pinned archive;
5. if that challenge set is absent or not gold, stop and revise this
   preregistration before inspecting another candidate partition.

Do not create a convenient random split. Do not inspect protected text, DRS
clauses, or failure rows before the one aggregate evaluation.

## Projection contract

The adapter may map only explicit PMB clauses with deterministic provenance:

- discourse referents to entity or event nodes;
- lexical predicates to type or event edges;
- explicit thematic-role clauses to ordinary role edges;
- explicit named-entity constants to constant entity nodes;
- explicit definiteness or discourse-status evidence to definite edges only
  when the PMB representation distinguishes it safely;
- explicit attachment or clausal relations to modifier/complement edges only
  through a documented one-to-one mapping.

Unsupported DRS operators, senses, roles, scope, discourse relations, or
coreference must remain absent and make the graph partial or declined. The
adapter must not infer a role from word order, convert every binary relation
into a generic role, or enumerate PMB vocabulary in Python.

Every emitted node and edge must retain the PMB document identifier, source
clause, and source span or token alignment when supplied.

## Development firewall

- **Train:** inspectable for mapping design and category work.
- **Development:** aggregate and item-level validation is permitted, but every
  rule change must be justified by a named construction class and synthetic
  tests.
- **Protected compositional challenge:** one aggregate look only.
- No protected failure row may be inspected after the look.
- A ledger records archive hash, git commit, timestamp, command, aggregate
  result, and disclosed challenge-family aggregates.

The COGS TEST and generalization ledgers remain unrelated and must stay at one
row each.

## Entry gate for original Phase E

All conditions are conjunctive:

1. zero incorrect graphs and 100% projected-edge precision;
2. at least 25 complete graphs;
3. at least 250 correct projected edges;
4. at least 1% recall over adapter-representable gold edges;
5. nonzero complete coverage in at least three preregistered buckets:
   entity/type/status, event/role, and attachment/complement;
6. zero broken exact graphs and zero decline-to-wrong transitions on every
   standing Rulekit gate; and
7. full synthetic/unit suite and lint remain green.

If any condition fails, original Phase E remains blocked. Revert the
uncheckpointed OOD adapter batch if precision falls below 100%. Coverage
shortfalls with perfect precision may return to inspectable PMB development
data only under a newly recorded increment; they do not permit another
protected look.

## Implementation sequence after licence approval

1. Record authoritative licence evidence in this file.
2. Download once, pin the archive hash, and materialize only declared splits.
3. Add the project schema, immutable builder, and snapshot ledger.
4. Implement the DRS-to-Rulekit gold adapter before adding reader coverage.
5. Establish an untouched-runtime baseline.
6. Mine only train/development, one construction class per increment.
7. Run all standing gates for every increment.
8. Freeze the candidate commit and spend the single protected challenge look.
9. Record pass/fail without inspecting failed rows.

