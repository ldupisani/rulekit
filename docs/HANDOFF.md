# rulekit handoff — semantic projection

**Updated:** 2026-07-23

**Active campaign:** COGS semantic projection

**Status:** Phase A complete; Phase B is next

**Last capability commit:** `0717f04` (`Add COGS semantic projection phase A`)

This is the short operational handoff. The complete Session 1–105 history is
preserved byte-for-byte in
[`HANDOFF-archive-2026-07-23.md`](HANDOFF-archive-2026-07-23.md). Do not extend
that archive; it is an immutable snapshot of the earlier arithmetic, FOLIO, and
semantic-projection work.

## Read before changing code

1. [`../CLAUDE.md`](../CLAUDE.md) — project constitution and standing gates.
2. [`semantic-projection-plan.md`](semantic-projection-plan.md) — campaign
   contract, phase definitions, and increment protocol.
3. [`methodology.md`](methodology.md) — DEV/TEST firewall and precision-first
   measurement.
4. [`architecture.md`](architecture.md) — runtime architecture.

The campaign plan is the detailed source of truth. This file says where work
currently stands and what to do next.

## Current objective

Extend the exact FOLIO-style reading layer with a compositional semantic view
that can represent entities, events, roles, modifiers, complements, identity,
and definiteness while retaining exact evidence and provenance.

The goal is not to print COGS logical-form strings or merely pass a benchmark.
It is to make increasingly complex questions answerable from a lossless,
inspectable semantic graph, and to decline or request clarification when the
text does not determine a safe reading.

Keep these layers distinct:

- exact surface facts — what the reader directly established;
- structured semantic projection — entities, events, roles, and attachments;
- lexical and ontology knowledge — declarative YAML data, not Python word
  lists;
- derived inference and proof — what follows from the established facts; and
- question interpretation — including explicit clarification when multiple
  precise readings remain.

Semantic projection is an additional typed view over evidence, not a replacement
fact store or a second inference engine.

## Phase A result

Phase A added:

- a reproducible COGS corpus builder pinned to corrected upstream revision
  `165a7b669eade971fa47bf568a2e51925360fed8`, with all four source SHA-256
  checks verified;
- project-level projection-corpus support;
- a COGS logical-form adapter that alpha-normalizes entity/event graphs;
- projection bench, snapshot, and harm-ordered diff support;
- graph tests for entities, definiteness, roles, modifiers, and complements;
  and
- a deliberately narrow runtime bridge from the pre-existing structured
  `VerbalRelation` fact.

All 51,155 scored source logical forms parse through the benchmark adapter.
The runtime bridge fails closed when it cannot license a verb or nominal
lemma. Flat `Atom` phrase keys are never split into guessed semantic edges.

### Honest baseline

| split | exact | safe partial | declined | incorrect | edge precision | edge recall |
|---|---:|---:|---:|---:|---:|---:|
| DEV-train | 247 | 41 | 11,768 | 0 | 100% | 1.5% |
| DEV-holdout | 213 | 47 | 11,839 | 0 | 100% | 1.3% |

The exact graphs currently come only from the pre-existing
`VerbalRelation` representation. Phase B must improve coverage without
weakening this precision boundary.

### Structural worklist

| DEV-train construction | items | exact | safe partial |
|---|---:|---:|---:|
| transitive | 3,221 | 247 | 41 |
| ditransitive | 2,661 | 0 | 0 |
| nominal modifier | 2,186 | 0 | 0 |
| intransitive theme | 1,301 | 0 | 0 |
| `ccomp` complement | 970 | 0 | 0 |
| intransitive agent | 699 | 0 | 0 |
| `xcomp` complement | 601 | 0 | 0 |
| nested modifier | 199 | 0 | 0 |
| nested complement | 142 | 0 | 0 |
| primitive exposure | 76 | 0 | 0 |

## Corpus firewall

| Rulekit slice | rows | Permitted use |
|---|---:|---|
| `dev-train` | 12,056 | inspect, mine, and tune |
| `dev-holdout` | 12,099 | aggregate/class diagnostics; no item tuning |
| `calibration` | 3,000 | inspectable, already contaminated by dataset selection |
| `test` | 3,000 | protected aggregate-only checkpoint |
| `generalization` | 20,984 | protected case aggregates after published-example exclusions |

No COGS TEST or generalization look has been spent.

The internal holdout detects local overfit, but COGS generalization is the
principal defense against grammar-template overfit. Do not inspect protected
failed rows. Do not copy COGS sentences into unit tests; use synthetic names,
nouns, verbs, and arrangements.

Materialized data and snapshots are gitignored. Rebuild with:

```bash
uv run --extra bench python projects/cogs/build_corpus.py
```

Phase A snapshot locations:

```text
projects/cogs/snapshots/phase-a-dev-train.json
projects/cogs/snapshots/phase-a-dev-holdout.json
```

## Phase B objective

Build first-class entity, event, and semantic-role projection breadth-first,
one construction class per increment:

1. named and indefinite entities;
2. intransitive events with verb-class-sensitive agent/theme roles;
3. active transitives;
4. passive transitives, including optional expressed agents;
5. ditransitives and recipient roles; and
6. definiteness without inventing uniqueness or world identity.

The locked exit conditions are:

- 100% projected-edge precision and zero incorrect graphs on both DEV
  partitions;
- exceed 247/213 exact graphs and 1.5%/1.3% edge recall;
- nonzero exact coverage on both DEV partitions for transitive, ditransitive,
  intransitive-agent, and intransitive-theme graphs;
- every served class has complete buyers in both DEV partitions; and
- all existing regression and cross-corpus gates remain neutral.

Adding vocabulary alone earns no credit. Verb-class membership belongs in YAML
packs; Python may consume a category but must not enumerate its members.

## Immediate next step

Use only inspectable `dev-train` data to subdivide the transitive pool by:

- missing graph structure;
- subject construction;
- object construction;
- active/passive voice; and
- named versus indefinite referents.

Select one frequent, clean class whose complete target requires a general
entity/event/role representation. Before implementation, record:

1. the construction class;
2. the complete graph it should buy;
3. representative synthetic positive examples;
4. negative neighbours and ambiguity cases;
5. the expected DEV-train and aggregate DEV-holdout buyers; and
6. which YAML categories, if any, license its role interpretation.

Do not begin by admitting frequent unknown COGS words. First design the
general representation and a complete construction buyer.

## Increment protocol

For every Phase B increment:

1. snapshot COGS DEV train/holdout and all standing regression corpora;
2. select one frequent clean blocker class from `dev-train`;
3. name the complete semantic graph and its provenance contract;
4. implement general machinery plus declarative YAML categories;
5. add synthetic positive, negative-neighbour, ambiguity, and overreach tests;
6. require zero new incorrect edges on DEV-train;
7. require zero new incorrect edges and no exact-to-partial regressions on
   DEV-holdout;
8. run curated twice and all standing regression/cross-corpus gates;
9. update the campaign plan or this handoff with buyers and graph deltas; and
10. do not spend COGS TEST/generalization looks before the phase checkpoint.

A partial graph is useful for inspection, but it is not a complete reading and
must not answer a query whose required subgraph is absent.

## Working commands

```bash
# Projection baselines
uv run rulekit --project projects/cogs bench --slice dev-train --jobs 8
uv run rulekit --project projects/cogs bench --slice dev-holdout --jobs 8

# Snapshot and compare an increment
uv run rulekit --project projects/cogs bench --slice dev-train \
  --snapshot /tmp/cogs-before.json
uv run rulekit --project projects/cogs diff \
  /tmp/cogs-before.json /tmp/cogs-after.json

# Synthetic and standing gates
uv run pytest
uv run rulekit --project projects/curated bench --slice suite
uv run rulekit --project projects/gsm8k bench --slice dev-train --jobs 8
uv run rulekit --project projects/gsm8k bench --slice dev-holdout --jobs 8
uv run rulekit --project projects/asdiv bench --slice dev --jobs 8
uv run rulekit --project projects/svamp bench --slice dev --jobs 8
uv run rulekit --project projects/mawps bench --slice dev --jobs 8
uv run rulekit --project projects/scibench bench --slice dev --jobs 8
uv run rulekit --project projects/folio bench --slice dev --jobs 8
uv run rulekit --project projects/gsm8k lint
```

Use the CLI's explicit TEST-spend option only at the phase checkpoint defined
in the campaign plan. Its existence is not authorization to spend a look.

## Current semantic/question UI

The designer already separates:

- **Reading** — tokens, decisions, exact facts, gaps, and deficiencies;
- **Deictic field** — discourse/reference state;
- **Semantic field** — projected semantic information and provenance; and
- **Proof/clarification** — answer evidence or candidate question readings.

Question ambiguity is first-class. For example, “an otter has a badge” may
mean an existential witness or a class-wide property. Without a selected
interpretation, the engine returns a structured clarification request and
commits to neither consumer. After selection, unsupported evidence returns
`undetermined`; this is distinct from “needs clarification.”

Preserve that distinction as semantic projection grows:

- **clarification**: multiple well-formed readings exist;
- **undetermined**: one selected reading lacks deciding evidence;
- **declined projection**: the sentence cannot yet be mapped safely; and
- **incorrect**: an unsupported semantic commitment was made.

## Relevant implementation files

- [`../projects/cogs/project.yaml`](../projects/cogs/project.yaml)
- [`../projects/cogs/build_corpus.py`](../projects/cogs/build_corpus.py)
- [`../projects/cogs/published_examples.txt`](../projects/cogs/published_examples.txt)
- [`../src/rulekit/harness/projection.py`](../src/rulekit/harness/projection.py)
- [`../src/rulekit/harness/snapshot.py`](../src/rulekit/harness/snapshot.py)
- [`../src/rulekit/data/schemas.py`](../src/rulekit/data/schemas.py)
- [`../src/rulekit/data/project.py`](../src/rulekit/data/project.py)
- [`../src/rulekit/cli.py`](../src/rulekit/cli.py)
- [`../tests/test_cogs_projection.py`](../tests/test_cogs_projection.py)

## Historical campaigns

- Full Session 1–105 record:
  [`HANDOFF-archive-2026-07-23.md`](HANDOFF-archive-2026-07-23.md)
- Earlier handoff archive:
  [`HANDOFF-archive-2026-07-16.md`](HANDOFF-archive-2026-07-16.md)
- Parked difg/SciBench physics work:
  [`parked-physics-campaign.md`](parked-physics-campaign.md)
- Completed FOLIO/Delphi campaign plan:
  [`delphi-learnings-plan.md`](delphi-learnings-plan.md)

The FOLIO work remains a standing safety and answer-level gate. Resume its
historical campaign only by deliberately choosing that direction; do not mix
FOLIO reader mining into the current COGS Phase B worklist.
