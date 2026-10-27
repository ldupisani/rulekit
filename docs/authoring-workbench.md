# Designer and review workbench

The local Designer and generation services help inspect and author the same
packs used by the runtime. Generation and reviews supply debugging and
validation evidence; they do not become runtime premises or training labels.

## Inspect a reading

The Designer exposes reading decisions, obligations, matched rules and
bindings, emitted facts, collisions, deficiencies, query interpretation,
answers, and available proof or semantic views. Source indexes connect
compiled rules and template variants to their authored YAML.

Deictic and semantic views display supported evidence rather than infer missing
context for presentation. The views distinguish an unresolved reference from
one with a justified antecedent.

Implementation: [server API](../src/rulekit/server/api.py),
[Designer](../src/rulekit/server/static/app.js), and
[source indexing](../src/rulekit/data/sources.py).

## Edit YAML safely

The editor exposes existing YAML documents from loaded packs. Datasets,
snapshots, arbitrary paths, project configuration, and escaping symlinks are
outside that browser. Saving validates and recompiles; an invalid change is
rolled back. Source locations and the registry fingerprint identify the
knowledge used for a retest.

The editor links to the [YAML reference](yaml-reference.md),
[architecture](architecture.md), and schemas derived from the running models.
The schemas are read from code, not a hand-maintained copy.

Implementation: [documentation routes](../src/rulekit/server/help.py).
Tests: [authoring documentation](../tests/test_authoring_docs.py) and
[document firewall](../tests/test_server_doc_firewall.py).

## Generate premises

Premise generation realizes a declared rule with seeded vocabulary and
structural choices. Availability reports unsupported contracts explicitly.
Optional branches, contextual premises, categories, slot constraints, and
source-backed compatibility checks participate in the generated evidence.

Strict positives must round-trip to the intended rule. Controlled lexical or
structural boundary specimens preserve the operation under examination while
exposing its acceptance boundary. A failed bounded search is a reported
failure, not proof that no example exists.

Implementation: [generation](../src/rulekit/generation/sample.py),
[candidate model](../src/rulekit/generation/candidate.py), and
[exploration](../src/rulekit/generation/exploration.py).
Tests: [generation workbench](../tests/test_generation_workbench.py) and
[optional realization](../tests/test_generation_g5i.py).

## Generate asks and complete scenarios

Ask generation distinguishes independently realizable questions from questions
that require premise context. Supported modes include ask-only inspection,
bounded answerable scenarios, deliberate missing evidence, and scenarios built
from validated premises.

An answerable scenario must pass through ordinary `solve`, commit an answer,
and retain the intended ask. It is not accepted merely because an independent
arithmetic expression produces the desired value. Alignment declarations can
preserve identities, units, values, and derivation-only wording from reviewed
premises.

Implementation: [ask generation](../src/rulekit/generation/ask_generation.py).
Tests: [ask scenarios](../tests/test_ask_generation_g7.py) and
[review evidence](../tests/test_ask_review_evidence.py).

## Review and retest

Human judgments retain append-only edit, resolve, tombstone, and pinned-retest
history. Retesting a record uses its recorded text; it must not replace that
text with a newly generated sample. Previously accepted evidence can become
regressed without inventing a new human verdict.

Premise, reading-origin, targetless, fact-level, ask, and scenario evidence have
separate validity claims. A correct answer does not automatically validate
all premises. Fact snapshots preserve provenance and inspectable references.
Evidence exclusions and tombstones control reuse without erasing history.

The **Needs attention** view explains recorded deficiencies, collisions,
defects, judgments, and current replay regressions separately from the human
verdict. A `VALID` verdict can therefore still have an outstanding issue.

Use **Retest saved example** to replay its exact text and context. Compare the
recorded and current evidence, then choose fresh verdict, interpretation, and
result judgments before **Record updated evidence**. This appends a linked
record with the current fingerprint and snapshots; it does not replace the
original or close its issue. Changed readings and excluded or superseded source
records require a fresh retest. A valid update is blocked while current reader
or target checks fail for a premise review; invalid and unclear observations
can still be recorded. Ask reviews check their target, query, and result;
low-level reader observations remain inspectable and do not become judgments
that all the premises are valid.
Ask retests preserve the saved reference year. Prior premise validations and
minimality claims are not transferred to a new ask snapshot.
Retests list unresolved references separately, using the reader's unmet
reference obligations. A valid sentence can still require an antecedent in its
saved context. These observations remain in the original deficiency list and
still block premise validation; the display does not supply missing evidence.

Use **Mark resolved** with a note to close an issue independently. Resolution
retains the original verdict, defects, and evidence in **Evidence archive**.
It neither grants validated coverage to problematic evidence nor removes
coverage already supported by a clean reviewed example. Targetless sentence
reviews remain outside premise and ask coverage. **Exclude evidence** remains
the separate operation for removing a judgment from active evidence.

Coverage prefers examples that still replay correctly before using naturalness
and recency to choose an exemplar. The inbox checks each positive independently,
so a healthy example cannot conceal another regressed review in the same group.

Implementation: [reviews](../src/rulekit/generation/reviews.py).
Workflow: [saved review actions](../src/rulekit/generation/review_workflow.py).
Tests: [review boundaries](../tests/test_review_semantic_boundaries.py),
[reference reviews](../tests/test_reference_identity_reviews.py), and
[reviewed generation](../tests/test_reviewed_generation_boundaries.py).

## Historical campaign records

The mining campaign UI, CLI/API operations, isolated candidate runner, and
promotion workflow are retired. User-selected question implementation follows
[CLAUDE.md](../CLAUDE.md), with validation described in the
[testing methodology](methodology.md).

Existing records remain unchanged under `projects/*/generation/campaign/`:
candidate manifests in `candidates/`, human decisions in `reviews.jsonl`,
machine results in `gates.jsonl`, and integration records in `landings.jsonl`.
These JSON/JSONL files preserve their original formats, revision identifiers,
registry fingerprints, and history. They are an archive; the workbench no
longer reads or writes them.

Ordinary generation and review ledgers remain active in the parent
`generation/` directory. Reviews, pinned retests, provenance, and benchmark
snapshot comparisons do not depend on campaign records or approvals.
