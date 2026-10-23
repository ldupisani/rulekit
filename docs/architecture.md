# RuleKit architecture

RuleKit reads controlled English, records explicit meaning, and answers only
when the evidence supports a commitment. It is deterministic: a small Python
kernel executes declarative language and domain knowledge from YAML packs.
There is no LLM in the runtime path.

This document describes the application, its boundaries, and where extensions
belong. For file formats, rule syntax, category relationships, and generation
contracts, use the [YAML reference](yaml-reference.md). The
[reference index](README.md) links to implemented features and design
principles. Development policy lives in [CLAUDE.md](../CLAUDE.md), with
validation described in [methodology.md](methodology.md).

## System map

```text
project.yaml + YAML packs
          |
          v
 schema validation -> compilation -> immutable Registry + fingerprint
                                          |
                    +---------------------+----------------------+
                    |                     |                      |
                    v                     v                      v
              CLI / solve          Designer authoring       benchmark harness
                    |              generate / edit /        same runtime,
                    |              review / replay          separate golds
                    v                     |
       analyze -> document facts <--------+ ordinary round trip
                    |
       saturation + discourse resolution
                    |
        ask -> normalized query -> consumer -> guards
                    |
          answer / clarification / decline
```

| Layer | Responsibility | Source |
| --- | --- | --- |
| Data | Strict schemas, pack loading, compilation, source locations | `src/rulekit/data/` |
| Kernel | Reading, identities, facts, inference, answering, guards | `src/rulekit/kernel/` |
| Consumers | Named, reusable operations over queries and evidence | `src/rulekit/kernel/consumers/` |
| Generation | Seeded realization, round trips, reviews and evidence replay | `src/rulekit/generation/` |
| Harness | Dataset adapters, judges, snapshots and protected split controls | `src/rulekit/harness/` |
| Designer | Local FastAPI service and vanilla JavaScript UI | `src/rulekit/server/` |
| Reference | Optional DuckDB-backed lookup and aggregation | `src/rulekit/reference/` |

## Architectural boundaries

Language knowledge belongs in packs: vocabulary, inflections, categories,
semantic roles, conversions, constants, and sentence constructions. Python
implements reusable operations on that data, not lists of words or branches
for individual questions.

Authoring is separate from inference. A generated sentence or a human judgment
cannot become a runtime fact by itself. Generation
uses the ordinary reader and solver to observe behavior; review records never
train a probabilistic model or silently modify a pack.

Evaluation is separate from reading. Runtime code cannot consult benchmark
answers or gold semantic graphs. A project chooses packs and evaluation data,
but a corpus adapter is not another parser.

Precision takes precedence over coverage. Unsupported language, ambiguous
references, contradictory evidence, incomplete accounting, or an unsupported
query should produce a visible decline or clarification, not a guessed answer.

## Configuration and compilation

A project chooses packs and optionally a curated suite, answer datasets, or
semantic-projection splits. Packs may depend on other packs. Each YAML
document identifies its own format; filenames and directory grouping are for
authors rather than dispatch rules.

Loading validates documents against Pydantic models, expands local rule
templates, resolves dependencies and category relationships, and compiles an
immutable registry. Compilation rejects invalid references, category cycles,
incompatible senses, and other structural errors before a reading begins.
The registry fingerprint identifies the loaded pack bytes. Source indexes
retain original file and line locations, including template variants and
category-inclusion routes.

One category hierarchy describes taxonomy. Nominal inclusion unions compose
reusable member families without multiple inheritance. Category-owned verb
frames and measure/holder relationships describe admissible roles; grammar
rules map their slots to those roles. All are shared by matching, generation,
and source-backed explanations. Their syntax and distinctions are documented
in the [category reference](yaml-reference.md#categories-and-relationships).

## Runtime reading pipeline

The main internal entry point is `rulekit.kernel.engine.solve`. The CLI and
Designer load a project and call the same runtime.

### 1. Normalize and analyze

Recognized math notation is conservatively normalized, then the text is split
into premises and a question. Explicitly licensed conditional-question
constructions retain their scope; there is no general prose repair service.

For each sentence, the reader tokenizes, annotates numeric structures and
candidate senses, disambiguates, attaches grammatical obligations, condenses
licensed phrases, and binds their roles. Tracing records reversible decisions;
benchmark execution omits expensive snapshots without changing semantics.

### 2. Build and saturate the premise store

Read-phase pattern rules match analyzed units and emit typed facts. General
structural learning contributes facts independently. Provenance records the
sentence, rule, and relevant evidence.

The store is saturated with declarative joins and registered algorithmic
synthesizers. Facts are deduplicated, and inference stops when no new facts
are added. A bounded round limit makes non-termination an error. This is
additive inference, not a general truth-maintenance or retraction system.

### 3. Resolve document context

A bounded document loop resolves supported personal references, possessors,
measure anaphora, and exact plural subject groups. Changed readings are
rematched and the store rebuilt and saturated. Resolution uses explicit
compatibility and deictic arbitration; ties stay unresolved.

Participant identity preserves nominal heads, owners, qualifiers and labels.
A bare reference can select a uniquely compatible identity, but cannot erase
competing owners or qualifiers. Subject groups come from discourse evidence,
not from collecting every quantity with the requested unit. An incidental
object is not automatically a member of “they.”

### 4. Interpret and answer

The question is analyzed against the document. Ask selection ranks consumed
units, category specificity, then stable rule id. The selected ask produces a
normalized query for a named consumer. An ask with explicit alternatives can
request clarification instead of choosing an interpretation invisibly.

Consumers use the query, facts, registry and reading evidence. They may return
a scalar, a labelled numeric series, witness statuses, a logical verdict, a
proof, or a decline. They do not parse problem-specific prose.

### 5. Guard the commitment

A proposed answer passes structural and evidence-accounting guards. Numeric
answers require supported vocabulary and properly used operative values;
witness and logical answers have their own supported-fragment checks. A veto
turns the commitment into a decline with an explanation. A dirty fact store
cannot commit.

## Core representations

| Representation | Purpose |
| --- | --- |
| `Registry` | Compiled language/domain knowledge and fingerprint |
| `Reading`, `Unit`, `Obligation` | Sentence structure and grammatical needs |
| `Decision` | Inspectable reading mutation |
| `ReferenceIdentity` | Structured participant identity, including ownership |
| `Fact`, `Provenance` | Typed evidence and its origin |
| `FactStore` | Lookup, deduplication, agreement and collision quarantine |
| `Document` | Readings, store, context resolution, logs and gaps |
| `Answer`, `Result` | Outcome plus evidence, clarification or veto |

Facts are not flattened into generic triples. Quantities, relations, rates,
goals, account entries, events, logical statements, and semantic graph edges
have different identity and value contracts. Equal keys and equal values
record agreement; equal keys and incompatible values quarantine the conflict.

All matching read rules run. A structurally more specific match can shadow a
less specific match only under the kernel's consumed-unit and specificity
contract. There is no author-assigned priority to hide a conflict.

## Reusable reasoning components

These are cooperating evidence models, not independent question solvers:

- Quantities and affine/proportional relations share participant identity,
  measure resolution, derivations and value accounting.
- Rates, duration, cadence, and threshold policies compose only when their
  actor, activity, unit and scope evidence agrees.
- Resource allocations, balances, purchases, expenditure and repayments
  retain account, owner and event scope. A budget, credit limit, actual use,
  and remaining liability are not interchangeable facts.
- Containers, content changes, physical measurements and unit conversions
  preserve the distinction between intrinsic container mass, total readings,
  individual contents, and capacity. Substance-specific conversions are not
  global unit equivalences.
- Partitions, ordered batch shares, inventory changes, and totality claims
  require a complete compatible population before computing a remainder.
- Goals and hypothetical changes remain distinct from actual holdings or
  completed events. Temporal queries require the relevant temporal evidence.
- Dimensional algebra underlies compatible conversions and declarative
  physical/chemical formulas; packs supply constants and quantity knowledge.
- Opt-in logic packs represent quantified statements and finite evidence.
  The logic/arithmetic bridge derives quantities only from supported
  membership and refinement evidence.

Extending one of these models should reuse its identity, scope, and accounting
contracts. Recognizing a new sentence is not permission to discard a fact's
time, holder, purpose, unit, or completeness conditions.

## Designer and authoring workflow

The local Designer exposes reading traces, facts, gaps, semantic/deictic/proof
views, YAML editing, generation, and reviews.
The [YAML reference](yaml-reference.md) is available from its editor, together
with live JSON schemas for the running code.

The editor permits only existing YAML documents in loaded packs. It excludes
datasets, snapshots, project files, arbitrary paths, and escaping symlinks.
Saving validates and recompiles, or rolls back. Retesting a pinned example
compares the same text, not a newly generated replacement.

Premise generation realizes one rule with seeded lexical choices and optional
context. Ask generation supports independent asks, bounded answerable
scenarios, intentional missing evidence, and questions based on validated
premises. Every returned candidate round-trips through the ordinary runtime;
an answerable scenario must commit through the solver and retain the intended
ask. Bounded searches report failures rather than claim exhaustive coverage.

Human judgments are append-only authoring evidence. Valid examples can be
folded into structural coverage and replayed against current code. Regressed
means previously accepted evidence no longer meets its recorded contract;
it is not a new human verdict. Tombstones and evidence exclusions control
which records participate without rewriting history. Generation support,
reader matching, a solver commitment, and human validity are different claims.

The [workbench reference](authoring-workbench.md) describes implemented
generation, review, coverage, and the location of historical campaign records.
Automated mining and its candidate promotion workflow are retired.
User-selected questions use the same runtime and regression harness directly.

## Evaluation, snapshots, and firewall

The harness runs the ordinary engine. Answer projects use answer judging;
semantic-projection projects normalize emitted graph facts and compare them
with gold graphs in the harness only. Unsupported projected structure is
incorrect even when some required structure is present; incomplete but sound
graphs are partial, not exact.

DEV slices are inspectable under the methodology. Protected TEST and
generalization looks require explicit authorization, return aggregates, and
are ledgered. Projection split policies additionally reject partial protected
looks. The Designer's document browser must never expose corpus data.

Snapshots retain registry fingerprints and stable outcomes. Diff gates detect
lost correct answers and newly wrong commitments. Isolated and parallel
execution checks test determinism against the same registry. Tests use
invented analogues and boundary cases, not copied benchmark prose.

## Where extensions belong

| Change | Location |
| --- | --- |
| Vocabulary, taxonomy, role compatibility, constants | YAML packs |
| New construction emitting existing meaning | A premise rule and synthetic tests |
| Repeated grammatical skeleton | Local rule/ask template variants |
| Join of existing facts | Declarative synthesis |
| General algorithmic derivation | Registered kernel synthesizer |
| New question surface | An ask producing an existing normalized query |
| New query operation | A focused consumer with evidence guards |
| New fact kind | Model, emission, store/identity, accounting and serialization |
| New corpus/gold format | Project builder and harness adapter |
| New authoring operation | Generation or Designer, not runtime inference |

`packs/core-english/` owns base language; `arithmetic/`, `physics/`,
`chemistry/`, `logic/`, `logic-arithmetic/` and `reference/` add reusable
domains. `difg-mined/` supplies migrated knowledge, with its quarantine
boundary intact. Projects may also load local packs.

## Declared but not implemented

Do not infer runtime support from schema acceptance alone:

- Pack `activation` is declared, but project packs load eagerly.
- Requirement shapes compile, but no provider loop consumes them.
- `post-saturation` pattern rules and multi-sentence pattern sequences are
  accepted by the schema but are not scheduled as executable read patterns.
- There is no general event-indexed provider or provenance-retraction loop.
- Synthesizers and consumers are in-process registries, not external plugins.
- Internal Python entry points are not a promised stable public library API.

These limitations are also called out in the authoring reference, where a
schema-valid but inactive construct would otherwise be misleading.
