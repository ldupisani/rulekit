# Synthetic semantic treebank fabrication and firewall plan

**Status:** design accepted; fabrication has not started

**Purpose:** create a fit-for-purpose, independently fabricated semantic
treebank for precise ordinary English, then import it through a one-way
firewall so Rulekit can tune on train data without seeing protected test
content.

**Licence target:** CC0 1.0 dedication for the generated corpus, its neutral
schema, lexicons, grammars, and metadata. Tooling may use a permissive
software licence separately.

## Decision

Build the complete data model now, including statements, questions,
clarification cases, safe declines, alternations, attachment, coordination,
negation, and embedding. Every phenomenon must be independently selectable.
The first gate uses only a conservative `projection-core` profile; later
profiles reuse the same sealed corpus.

Positive cases prioritize grammatical, generally accepted contemporary
English with one determinate reading. The corpus is not a challenge set for
garden paths, literary ellipsis, slang, hostile spelling, or deliberately
obtuse language. Naturally ambiguous language belongs in the `clarify`
partition, and language outside the declared contract belongs in `decline`.

The corpus is synthetic evidence of controlled compositional transfer. It
does **not** demonstrate performance on the uncontrolled distribution of
human-authored text and must never be described as such. Its legitimacy as a
Phase E gate comes from the application's controlled-language contract, the
independent fabrication context, compositional held-outs, and the sealed
one-look protocol.

## Independence threat model

The fabrication agent receives only the standalone assignment in this
document. It must not receive or inspect:

- the Rulekit repository, runtime code, YAML packs, tests, or schemas;
- COGS, PMB, FrameNet, UDS, or any other benchmark sentence or annotation;
- Rulekit benchmark outputs, protected aggregates, failure classes, or
  campaign history;
- current Rulekit vocabulary or parser capabilities; or
- any generated corpus from a previous fabrication attempt.

The assignment necessarily names the public semantic contract to test:
entities, events, roles, attachment, scope, questions, and dispositions. That
is specification knowledge, not implementation knowledge.

The fabrication workspace must be a new repository outside Rulekit. Do not
mount Rulekit into that context. Do not use retrieval, web search, external
corpora, example banks, or an LLM API to source sentences. The fabrication
agent may author declarative grammars and lexicons, then use deterministic
programs to generate the corpus.

The importer receives plaintext train, separately encrypted development and
test bundles, and their public manifests. Development evaluation is
repeatable but aggregate-only. The importer does not receive the
protected-test key. The protected evaluator receives that key only when the
user deliberately spends the single test look.

## Units of data

The primary split unit is a **bundle**, not a sentence. A bundle owns one or
more semantic scenes and all utterances derived from or relating those
scenes. A bundle is assigned wholly to one split.

A **scene** has a globally unique `scene_id` and exactly one neutral graph.
A scene may support several cases, so its ID intentionally repeats in case
records. A normal project/question case names one scene. An ambiguous case
names two or more alternative scenes in the same bundle. Its clarification
question and each resolving response also remain in that bundle.

An utterance is one of:

- `statement`: a declarative realization of the scene;
- `wh_question`: asks for an Agent, Theme, Recipient, type, identity, or
  attachment;
- `yes_no_question`: asks whether one explicit graph relation holds; or
- `clarification_response`: an unambiguous response that selects one of the
  alternatives recorded by a clarification case.

Every scored case has one expected disposition:

- `project`: exactly one supported interpretation with exact neutral gold;
- `clarify`: two or more plausible supported graphs plus a focused
  clarification contract; or
- `decline`: unsupported language or insufficient information, with no gold
  graph that the system is expected to guess.

Target release size is approximately 3,200 scored utterances:

| Split | Utterances | Permitted use |
| --- | ---: | --- |
| train | 2,000 | inspect, profile, and tune |
| development | 400 | encrypted, repeatable aggregate feature-cell validation |
| protected test | 800 | encrypted, aggregate-only, one look |

Target disposition balance is 75% `project`, 12.5% `clarify`, and 12.5%
`decline`. Exact totals may move only before sealing and must be recorded in
the release manifest.

## Neutral interchange schema

Use versioned JSON Lines validated by a committed JSON Schema. Do not use
Rulekit class names, token references, pack categories, or internal
provenance shapes.

Use separate scene and case streams. The abbreviated case shape is:

```json
{
  "schema_version": "1.0",
  "case_id": "case-...",
  "bundle_id": "bundle-...",
  "scene_id": "scene-...|null",
  "alternative_scene_ids": [],
  "split": "train|development|test",
  "profile_tags": ["projection-core"],
  "features": {
    "utterance_kind": "statement",
    "disposition": "project",
    "valency": "ditransitive",
    "realization": "prepositional-dative",
    "voice": "active",
    "subject_form": "proper-name",
    "theme_form": "indefinite-common",
    "recipient_form": "proper-name",
    "attachment": "none",
    "coordination": false,
    "negation": false,
    "embedding": false,
    "relative_clause": false
  },
  "utterance": "...",
  "gold_query": null,
  "clarification": null,
  "provenance": {
    "generator_version": "...",
    "seed": "...",
    "scene_rule": "...",
    "realization_rule": "...",
    "lexicon_revision": "..."
  }
}
```

The normative release must provide JSON Schemas for scenes, cases,
predictions, queries, clarifications, manifests, aggregate results, and
encrypted-bundle envelopes. The case schema uses disposition-specific
`oneOf` branches:

- `project`: exactly one `scene_id`; optional `gold_query`; no alternatives;
- `clarify`: null `scene_id`; at least two `alternative_scene_ids`; required
  clarification contract; and
- `decline`: null `scene_id`; no alternatives, query, or expected graph.

Scene records contain `scene_id`, `bundle_id`, one graph, semantic signature,
and provenance. Case records contain language and point to scenes; they do
not duplicate graphs.

### Nodes

The minimum node vocabulary is:

- `entity`: stable identity, optional proper-name value, semantic type,
  number, definiteness, and quantificational status;
- `event`: predicate lemma and polarity;
- `proposition`: required for clausal complements, negation scope, and
  embedded questions; and
- `set`: required for plural coordination without inventing multiple
  duplicated role edges.

Node identifiers are opaque and local to a scene. They must not encode token
positions or surface order.

### Edges

The minimum edge vocabulary is:

- thematic: `agent`, `theme`, `recipient`, and `beneficiary`;
- nominal: `type`, `identity`, `attribute`, `possessor`, `part_of`;
- structural: `modifier`, `complement`, `member`, `corefers`;
- scope: `negates`, `embeds`; and
- query: query targets are represented in `gold_query`, not as ordinary
  semantic facts.

Every edge must identify its source and target node. Surface spans are
optional alignment metadata and never define the semantic role.

The schemas constrain permitted source/target kinds and cardinalities. In
particular, thematic edges originate at events and terminate at entities or
sets; type/identity/attribute edges originate at entities; membership
originates at a set and terminates at an entity; and scope edges connect
propositions/events according to
their declared type. The semantic validator enforces required roles from the
predicate lexicon, prohibits duplicate labeled edges, rejects unreachable
nodes, and rejects undeclared node/edge attributes.

### Canonical graph scoring

Opaque node IDs are not scored literally. Two graphs are equal when a
label-preserving graph isomorphism exists over:

- node kind and all semantically scored node attributes;
- directed edge label and all semantically scored edge attributes; and
- bound constants such as proper-name values and query answers.

The fabrication toolkit must own the reference scorer used by both corpus
tests and protected evaluation. It must expose exact graph equality,
intersection edges, extra edges, missing edges, and projected-edge precision.
Graphs are small enough for exact labeled isomorphism; a heuristic match is
not permitted.

### Questions

`gold_query` records:

- the requested answer kind;
- the target relation or node property;
- any bound nodes supplied by the question;
- the expected answer node/value for a `project` case; and
- whether a proof should depend on an explicit or derived relation.

The same scene graph may support several questions, but bundle-level
splitting prevents paraphrases, alternatives, or related questions from
crossing the firewall.

### Clarification

A `clarify` case contains:

- at least two complete alternative graphs;
- one machine-readable ambiguity dimension, such as
  `attachment-target`, `pronoun-antecedent`, or `coordination-scope`;
- a short, ordinary clarification question whose possible answers select
  exactly one alternative; and
- unambiguous response realizations for those answers.

Do not label mere parser difficulty as ambiguity. If competent speakers would
normally agree on one reading, the case is `project`, not `clarify`.

## Feature taxonomy and selectable profiles

All features are explicit fields rather than inferred later from text.
`corpusctl select` must support inclusion and exclusion by any field or tag.

### Construction dimensions

- valency: agentive intransitive, theme-subject intransitive, transitive,
  ditransitive;
- dative realization: double-object, `to` prepositional, `for`
  prepositional where semantically licensed;
- voice: active and passive;
- reference: proper name, pronoun, common noun, definite, indefinite,
  singular, plural;
- nominal structure: possessive, PP attachment, adjective attachment,
  part-whole;
- clause structure: coordination, relative clause, negation, finite
  complement, nonfinite complement, and embedded question; and
- utterance kind: statement, wh-question, yes/no question, clarification
  response.

### Release profiles

- `projection-core`: unambiguous statements covering entities, types,
  Agent/Theme/Recipient, active/passive, both dative realizations, reference
  forms, and conservative safe declines;
- `projection-attachment`: possessives, nominal PP attachment, modifiers,
  part-whole, and matched attachment ambiguities;
- `projection-composition`: coordination, relative clauses, negation, and
  clausal embedding;
- `query-core`: direct Agent/Theme/Recipient, identity, type, and yes/no
  questions over `projection-core` scenes;
- `clarification`: genuine attachment, antecedent, and scope ambiguities with
  resolution turns; and
- `full`: every released feature.

Profiles are views over one immutable release. Selecting a profile must never
regenerate or resplit data.

## Fabrication architecture

Generate semantics first and language second:

1. Define typed lexicons for names, entity types, attributes, and predicates.
   Predicate entries declare allowed valency, thematic roles, alternations,
   voice, and selectional constraints.
2. Enumerate valid neutral scenes from construction specifications.
3. Assign whole bundles to splits using the frozen split design below.
4. Realize each scene through several grammar rules without changing its
   graph.
5. Generate matched questions from the graph, not by transforming arbitrary
   strings.
6. Generate `clarify` cases from an explicit pair of graphs that share one
   surface realization.
7. Generate `decline` cases by violating a declared language-contract
   boundary, never by corrupting random characters.
8. Validate all artifacts before the protected bundle is sealed.

The generator must be deterministic from the committed specification,
lexicons, tool versions, and root seed. Regeneration must reproduce every
byte of every plaintext split before encryption.

### Language policy

Positive utterances must:

- be grammatical ordinary English;
- use common productive constructions;
- avoid copied quotations and corpus-derived wording;
- avoid obscure senses, idioms, coercions, and world-knowledge traps;
- make semantic type constraints plausible without requiring encyclopedic
  knowledge; and
- remain understandable without knowledge of the generator.

Lexical diversity matters, but semantic coverage controls the split.
Paraphrases may vary determiners, auxiliaries, voice, dative realization, and
ordinary lexical choice. They must not introduce unrecorded semantic changes.

Declines should exercise meaningful boundaries: unsupported ellipsis,
unresolved reference, missing required participant, genuinely vague
quantification, or a construction explicitly outside the selected profile.
Typographical noise is out of scope for release 1.

## Split and compositional hold-out design

Do not randomly split individual utterances.

1. Group by `bundle_id`; related scenes, alternatives, statements, questions,
   paraphrases, and clarification responses are indivisible.
2. Define a bundle signature from the union of its scene roles, valency,
   polarity, attachment, scope, reference forms, utterance kinds, and question
   targets.
3. Freeze a coverage matrix before generating surface text.
4. Put every individual phenomenon in train.
5. Hold out lexical pairings and realization combinations in development.
6. Reserve protected test cells that combine individually seen phenomena in
   unseen ways, for example:
   - passive + prepositional dative + pronoun recipient;
   - double-object + definite Theme + proper Recipient;
   - question + passive + Recipient target;
   - attachment + coordinated entity;
   - negation + clausal complement.
7. Ensure protected test contains no wholly novel semantic label or grammar
   contract. It tests composition, not surprise requirements.
8. Prevent lexical leakage by grouping inflections, derivations, and
   paraphrase families before assigning split-specific hold-outs.

The manifest records the full cell matrix and counts without exposing test
utterances or gold graphs.

`coverage-matrix.yaml` is normative, not descriptive. It declares minimum
scene and case counts by split for every atomic feature, every
`projection-core` role/realization cell, every disposition, and every
protected compositional hold-out. The generator fails rather than silently
underfilling a cell. As a starting constraint, each released atomic feature
must have at least 20 train, 8 development, and 12 test cases where that
feature is eligible; stricter core-role minima are chosen to make the
protected entry contract arithmetically possible.

Profile selection syntax is repeated predicates:

```text
corpusctl select --profile projection-core \
  --include voice=passive \
  --exclude recipient_form=pronoun
```

Selection is a pure stable filter over an immutable release. Output ordering
is by UTF-8 byte order of `case_id`; the selected output records its selector
and source-release fingerprint.

## Toolchain for the fabrication repository

Use Python 3.12 managed by `uv`, with all dependencies and tool versions
locked. Recommended dependencies:

- `pydantic` or `jsonschema` for the interchange contract;
- `PyYAML` for declarative grammars and lexicons;
- `pytest` and `hypothesis` for generator invariants;
- `ruff` for formatting and lint;
- `cryptography` for authenticated protected-bundle encryption; and
- the Python standard library for deterministic JSONL, hashing, and archive
  construction.

Expose one command-line tool:

```text
corpusctl generate   # build all scenes and realizations deterministically
corpusctl validate   # schema, graph, alignment, language, and leakage gates
corpusctl profile    # aggregate counts and coverage cells only
corpusctl select     # immutable filtered views by profile/features
corpusctl seal       # encrypt development/test; write manifests/checksums
corpusctl verify     # reproduce plaintext hashes and verify sealed artifacts
corpusctl evaluate   # stream cases to a runner, score, emit aggregates
```

`evaluate` uses a generic JSON Lines runner protocol and therefore has no
Rulekit dependency. It decrypts one independently authenticated bundle frame
at a time in memory, then writes each case's opaque handle, utterance,
requested profile, and schema version to the runner's standard input, and
reads a disposition plus neutral predicted graph from standard output. The
runner receives no gold, feature cell, source case ID, or key. Invalid output,
timeout, process failure, or extra stdout is scored as an error/decline
according to the frozen evaluator contract. The fabrication repository
includes prediction/result schemas and a deterministic reference runner used
by evaluator tests.

For import, the runner is a frozen OCI image containing the candidate
application and neutral-output adapter. The evaluator launches it with no
network, a read-only filesystem, a bounded tmpfs, fixed CPU/memory/time
limits, and discarded stderr. Only schema-valid predictions reach the
scorer. This boundary is designed to prevent accidental disclosure, logs, and
state retention; it does not claim to defeat a deliberately malicious runner
using timing or resource side channels.

`evaluate` never prints a development/test case, identifier, sentence, graph,
or per-case result. Development evaluation prints only frozen aggregate cells
and is repeatable. Test evaluation prints only preregistered aggregates,
atomically appends a ledger record keyed by release and candidate
fingerprints, and refuses another run while that ledger exists. The one-look
rule remains a procedural scientific commitment: encryption cannot prevent a
key holder from copying state or deliberately evaluating twice.

Aggregate cells are frozen in the public manifest before import. No ad hoc
test selector or post-result cross-tab is accepted. Every reported cell has
at least ten cases; smaller cells are merged into a preregistered parent or
suppressed. Development exposes the same fixed taxonomy so repeated
differencing cannot be used to isolate a row.

Development and test use independent random 256-bit keys and a framed
AES-256-GCM bundle format. Each bundle is canonicalized independently and
encrypted as one frame with a unique random 96-bit nonce. Format version,
release fingerprint, split, frame ordinal, and bundle ID are authenticated
additional data. Nonces may never repeat under one key. The outer envelope
contains the ordered frames and no plaintext case metadata. This permits
authenticate-before-use processing one bundle at a time without materializing
the split.

Keys are delivered separately from artifacts. Key material is supplied to
`evaluate` through an inherited file descriptor or interactive prompt, never
through an argument, environment variable, repository file, log, or
manifest. The development key may be installed outside the workspace for
repeatable evaluation. The user retains the test key outside the workspace
until the candidate and acceptance contract are frozen.

## Fabrication validation gates

The release cannot be sealed until all gates pass.

### Schema and graph integrity

- 100% JSON Schema validity;
- globally unique case IDs and globally unique scene definitions;
- every case references scenes in its own bundle and split;
- node IDs unique within each graph;
- every edge endpoint exists;
- exactly one expected disposition;
- `project` references exactly one complete scene graph;
- `clarify` references at least two distinct valid scene graphs and one
  resolving question;
- `decline` references no scene graph;
- all questions resolve against their scene graph; and
- no forbidden Rulekit-specific field or identifier occurs.

### Linguistic and semantic consistency

- every surface predicate is licensed by its neutral lexicon entry;
- realized argument count and roles match the scene;
- active/passive and dative alternations preserve the intended graph;
- pronouns agree in number and declared reference;
- negation and embedding attach to the intended proposition;
- clarification alternatives differ only on the recorded ambiguity
  dimension; and
- every decline violates a named contract boundary.

These rules require executable validators. Prose review alone is not a gate.

### Split integrity

- no bundle or scene crosses splits;
- no exact utterance crosses splits;
- no normalized paraphrase family crosses a forbidden boundary;
- no held-out semantic cell leaks through another profile;
- train contains every atomic phenomenon used compositionally in test; and
- all split counts and signature distributions match the frozen matrix.

### Quality review

Before sealing, the fabrication context performs a blinded review of a
stratified sample from every feature cell, including protected cells. This is
allowed because the fabrication context owns the gold and is permanently
separate from Rulekit. Review decisions and corrections are completed before
the release hash is frozen.

A second fresh context should reader-test the specification, run the complete
validator suite, and audit aggregate coverage without receiving Rulekit.

The review rubric records grammaticality, ordinary-language acceptability,
semantic agreement with the graph, disposition correctness, ambiguity
genuineness, and clarification usefulness. Review all `clarify` and `decline`
cases, every protected matched direct-object/recipient case, and at least ten
cases or 20% (whichever is larger) from every other populated feature cell.
Two independent judgments are required for ambiguous cases; disagreement is
adjudicated or the case is removed before sealing. Review records contain
case IDs and decisions but remain only in the fabrication repository.

### Deterministic serialization

All plaintext artifacts use UTF-8, Unicode NFC, LF newlines, lexicographically
sorted object keys, no insignificant whitespace, and exactly one trailing
newline. JSONL records are sorted by UTF-8 byte order of their primary ID.
Numeric fields prohibit NaN and infinity. Generation fixes locale to `C`,
timezone to UTC, and timestamps to manifest-supplied values rather than wall
clock time. Plaintext hashes cover these canonical bytes. Encryption is
intentionally nondeterministic; verification decrypts and compares the
canonical plaintext hash.

## Release artifacts

The independent repository delivers:

```text
LICENSE-CC0.txt
README.md
schema/scene.schema.json
schema/case.schema.json
schema/query.schema.json
schema/clarification.schema.json
schema/prediction.schema.json
schema/manifest.schema.json
schema/evaluation-result.schema.json
schema/envelope.schema.json
spec/features.yaml
spec/profiles.yaml
spec/coverage-matrix.yaml
lexicon/*.yaml
grammar/*.yaml
src/corpusctl/**
tests/**
dist/scenes-train.jsonl
dist/train.jsonl
dist/development.bundle.enc
dist/development.public-manifest.json
dist/test.bundle.enc
dist/test.public-manifest.json
dist/release-manifest.json
dist/SHA256SUMS
```

`release-manifest.json` records repository commit, schema version, root seed,
dependency-lock hash, generator version, row and scene counts, disposition
counts, aggregate feature cells, plaintext train hash, development/test
plaintext hashes, encrypted-bundle hashes, licence, and required
attribution/dedication notices.

The development/test plaintext hashes permit later verification, but neither
plaintext artifact is delivered to the Rulekit workspace.

The user records the release commit and manifest hash through the trusted
handoff between contexts. Hashes establish integrity only after that trusted
pin; they are not presented as proof of publisher identity. The release tag
may additionally be signed, but import must not depend on an unverifiable
self-supplied public key.

## Rulekit import firewall

Import is a separate campaign and a separate commit series.

1. Verify the CC0 dedication, release commit, manifests, and every supplied
   hash before reading train text.
2. Store only the public fabrication specification, manifest, schema,
   builder, and attribution notice in Rulekit. Materialized train data,
   predictions, snapshots, ledgers, keys, and encrypted development/test
   bundles remain gitignored.
3. Write a deterministic project builder that validates the neutral schema
   and materializes immutable profile views.
4. Write a narrow neutral-graph adapter independently of Rulekit's runtime
   output. The adapter may map only declared neutral nodes and edges.
5. Take an untouched-runtime baseline on inspectable train and encrypted,
   aggregate-only development through the generic runner.
6. Tune only on train. Development may report preregistered aggregate feature
   cells but no sentences, IDs, graphs, or failure rows.
7. Every implementation increment follows the standing Rulekit gate:
   synthetic unit tests, zero broken exact graphs, zero
   decline-to-incorrect transitions, COGS/PMB preservation, all other project
   gates, and lint.
8. Freeze the candidate and acceptance contract before obtaining the
   protected key.
9. Spend exactly one protected evaluation through `corpusctl evaluate`.
10. Record pass or fail without inspecting protected cases. Never rerun,
    regenerate, or replace the release after the look.

The fabricator must not perform the Rulekit import. The importer must not
modify the fabrication release.

## Proposed protected entry contract

The exact contract must be committed before the protected key is made
available. The recommended minimum for the `projection-core` profile is:

1. zero incorrect projected graphs and 100% projected-edge precision;
2. no graph commitment on a protected `decline` case;
3. at least 100 complete protected `project` graphs;
4. at least 25 exact protected graphs containing each of Agent, Theme, and
   Recipient;
5. nonzero exact protected coverage for agentive intransitive, theme-subject
   intransitive, transitive, double-object ditransitive, prepositional dative,
   active, and passive cells;
6. at least ten exact protected direct-object cases and ten exact protected
   recipient cases in matched role-boundary cells;
7. zero broken exact graphs and zero decline-to-wrong transitions on every
   standing Rulekit gate; and
8. the complete synthetic/unit suite and lint remain green.

Questions and `clarify` cases are present in the release but are not required
to unblock the projection-only boundary. They receive separate preregistered
contracts when their profiles become active. This avoids making Phase E
question and clarification machinery a prerequisite for beginning Phase E.

If precision fails, revert the uncheckpointed adapter/coverage batch. If
coverage fails at perfect precision, the protected look is still spent:
continue only with a new independently fabricated release and a new
preregistration, never by tuning to protected aggregates.

## Standalone fabrication-agent assignment

Give the following instruction and this document—but no Rulekit files or
conversation history—to the fabrication agent:

> Build the synthetic semantic treebank specified in this document in a new,
> standalone repository. You have no access to the consuming application and
> must not request it. Implement the neutral schema, declarative lexicons and
> grammars, deterministic semantics-first generator, feature selectors,
> validators, split matrix, protected encryption/evaluator, tests, licence,
> and release manifests. Do not use external corpora, web text, benchmark
> examples, retrieval, or an LLM API as sentence sources. Generate ordinary,
> precise English from the committed grammar. Keep all realizations of a
> scene in one split. Test every invariant executable in code. Review and
> correct all feature cells before sealing, then deliver plaintext
> train, separately encrypted development and test bundles, public manifests,
> hashes, and the tools needed to reproduce and evaluate the release through
> a generic streaming runner. Do not inspect or import the consuming project.

The fabrication agent should work in milestones:

1. schema and feature contract;
2. semantic scene generator;
3. surface realizer and question generator;
4. ambiguity and decline generator;
5. split optimizer and leakage checks;
6. profile/select tooling;
7. sealing and aggregate-only evaluator;
8. full validation, independent reader test, and release.

Each milestone ends with tests, aggregate profiles, and a commit. Do not seal
until every milestone and release gate is green.
