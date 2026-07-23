# rulekit handoff — semantic projection

**Updated:** 2026-07-23

**Active campaign:** COGS semantic projection

**Status:** Phase C restart increment 4 selected

**Previous safe capability commit:** `0717f04`
(`Add COGS semantic projection phase A`)

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

One Phase D COGS TEST look and one generalization look were spent on
2026-07-23. The gitignored ledgers are:

```text
projects/cogs/snapshots/test-ledger.jsonl
projects/cogs/snapshots/generalization-ledger.jsonl
```

Each ledger contains exactly one row. Do not rerun either protected slice.

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

## Phase D checkpoint 1 — failed and reverted

The completed Phase B/C batch at `e657fc9` met every locked DEV objective and
passed the in-distribution protected checkpoint:

| split | exact | safe partial | declined | incorrect | edge precision | edge recall |
|---|---:|---:|---:|---:|---:|---:|
| TEST | 427 | 160 | 2,413 | 0 | 100% | 10.9% |

The single protected generalization look then failed the precision boundary:

| split | exact | safe partial | declined | incorrect | edge precision | edge recall |
|---|---:|---:|---:|---:|---:|---:|
| generalization | 914 | 2,586 | 17,426 | 58 | 99.6% | 7.7% |

No protected row was inspected. The permitted aggregate diagnostics localize
all 58 incorrect graphs to the ditransitive construction: 29 in the disclosed
`prim_to_obj_proper` case and 29 in `subj_to_obj_proper`. Every other disclosed
case and structural construction had zero incorrect graphs.

Per the locked Phase D contract, the entire uncheckpointed Phase B/C commit
batch (`cac2a6e` through `e657fc9`) was reverted rather than selectively tuned
against protected failures. The restored Phase A state is again 247 exact / 41
safe partial / 0 incorrect on DEV-train and 213 / 47 / 0 on aggregate
DEV-holdout, both at 100% edge precision.

The restored state passes all 3,055 synthetic/unit tests, COGS lint with zero
errors, curated 65/65, GSM8K DEV-train 104 and DEV-holdout 40, ASDiv 44, SVAMP
30, MAWPS 9, SciBench 6, and FOLIO with zero commitments.

The next work must use inspectable DEV only. Treat proper-object role transfer
at the ditransitive boundary as the first safety worklist before reintroducing
recipient-role coverage. The generalization aggregate may select this class;
it may not supply examples or row-level tuning. The two protected looks are
spent and must not be rerun.

## Phase B restart safety increment 1

This increment reintroduces the already DEV-gated Phase B entity/event/role
foundation through the explicit prepositional-dative buyer, while tightening
the proper-object boundary exposed by the failed checkpoint.

### Proper-object/ditransitive boundary selection brief

Selected before implementation on 2026-07-23:

1. **Licensed construction:** exactly `Name V a N to Name.`, with sentence
   anchors, one declaratively licensed ditransitive event, an indefinite typed
   theme, and an overt `to` before the proper-name recipient. Only this overt
   prepositional skeleton licenses `recipient`.
2. **Proper-object boundary:** `Name V Name.` remains an ordinary transitive
   proper-object shape whose postverbal name is a theme. `Name V Name a N.`
   receives no recipient interpretation from position alone and remains
   declined, as do proper themes followed by a `to` recipient until that
   separate construction is licensed.
3. **DEV evidence:** inspectable DEV-train contains 37 exact double-object
   surfaces using the eight prior dative verb forms, but zero direct
   proper-object minimal pairs for those forms. DEV therefore does not justify
   transferring a bare postverbal proper name from theme to recipient.
4. **Complete graph and provenance:** the licensed `to` dative emits one event,
   named agent and recipient entities, one indefinite typed theme entity, and
   exact agent/theme/recipient edges. Every fact retains its emitting rule and
   source span.
5. **Synthetic positives and negatives:** an invented `Neris` gives an
   invented `zephyrstone` to `Mira`; direct proper-object, double-object,
   named-theme-plus-`to`, common-noun recipients, passives, embedding,
   coordination, negation, and PP-tailed variants must not emit a recipient
   edge.
6. **Expected buyers and licence:** the conservative explicit-`to` class buys
   30 DEV-train and 18 aggregate DEV-holdout complete graphs, with no
   double-object credit. The construction-specific project-local
   `semantic_to_dative_verb` category contains the same eight previously
   audited overt forms; there is intentionally no generic ditransitive
   category that a later double-object rule could reuse without a separate
   audit. No Python vocabulary and no quarantine change are permitted.

### Proper-object/ditransitive boundary result

The previously DEV-gated first-class entity/event/role foundation is restored
through the explicit prepositional-dative buyer. The construction-specific
`semantic_to_dative_verb` category is the only recipient-event licence: no
generic ditransitive category exists for a positional double-object rule to
reuse. Synthetic direct proper objects remain themes, while double-object and
named-theme-plus-`to` surfaces emit no recipient edge.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 247 | 1,235 | +988 | 0 | 1.5% → 5.6% |
| DEV-holdout | 213 | 1,198 | +985 | 0 | 1.3% → 5.4% |

The conservative `to`-dative class buys exactly 30/2,661 DEV-train and
18/2,687 aggregate DEV-holdout ditransitive graphs, matching the recorded
estimate. All 37 licensed DEV-train double-object surfaces remain declined.
Both harm-ordered diffs report zero broken exact graphs and zero
safe-to-incorrect transitions; projected-edge precision remains 100%.

Verification is green: all 3,165 synthetic/unit tests; all 120 focused COGS
projection tests; COGS lint with zero errors; curated 65/65 twice; GSM8K
DEV-train 104 and DEV-holdout 40; ASDiv 44; SVAMP 30; MAWPS 9; SciBench 6;
and FOLIO with zero commitments. Every standing non-COGS snapshot diff is
neutral.

The protected TEST and generalization ledgers remain at one row each. Neither
protected slice was rerun.

## Phase B restart safety increment 2

This increment restores article-backed definiteness as the exact minimal pair
of the already served agentless passive.

### Definite agentless-passive selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `The N was V-en.`, with an anchored
   definite article, one bare singular `semantic_bare_theme_noun`, `was`, and
   one licensed `semantic_passive_participle`. There is no expressed agent,
   recipient, modifier, coordination, negation, complement, or trailing
   material.
2. **Complete graph:** the existing passive theme entity/type,
   event/predicate, and `theme(event, entity)` role plus exactly
   `definite(entity)`. The definite edge records article-backed discourse
   status, not uniqueness or cross-mention identity.
3. **Synthetic positive and provenance:** `The zephyrstone was appreciated.`
   must emit the complete graph with the definite edge spanning the article
   and noun; every node and edge retains the emitting rule and exact source
   span.
4. **Negative neighbours:** indefinite and named themes; plurals; expressed
   `by` agents; recipients; modified or compound nouns; PP, coordination,
   negation, embedding, and active-order tails; and unsafe participles.
5. **Expected buyers:** the exact surface has 439 inspectable DEV-train and
   412 aggregate DEV-holdout rows. Existing noun and participle licences leave
   217 train and 192 holdout complete buyers, all currently declined.
6. **Licence and safety boundary:** no vocabulary or Python mechanism changes.
   The existing noun and passive categories license interpretation. The
   construction-specific `semantic_to_dative_verb` boundary remains
   unchanged, and double-object recipient projection stays withheld.

### Result

The selected rule now emits the existing agentless-passive graph plus one
article-backed `definite` edge. It does not assert uniqueness or identity,
and every emitted fact retains exact rule and source-span provenance.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,235 | 1,452 | +217 | 0 | 6.8% |
| holdout | 1,198 | 1,390 | +192 | 0 | 6.4% |

Both harm-ordered diffs have zero broken exact graphs and zero
safe-to-incorrect transitions. The complete gate is green: 16 focused
definite-passive cases, 104 focused COGS projection tests, 3,149 full-suite
tests, zero COGS lint errors, curated twice, and neutral GSM8K, ASDiv, SVAMP,
MAWPS, SciBench, and FOLIO diffs.

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

### Phase B restart exit audit

The restart satisfies every locked Phase B DEV condition:

- precision is 100% and incorrect graphs are zero on train and holdout;
- exact coverage is 1,452 train and 1,390 holdout, above the locked 247/213
  thresholds, with 6.8%/6.4% edge recall above 1.5%/1.3%;
- train/holdout exact coverage is respectively 630/611 transitive, 30/18
  ditransitive, 271/267 intransitive-agent, and 521/494
  intransitive-theme graphs;
- every served construction has complete buyers in both DEV partitions; and
- all regression and cross-corpus gates are neutral.

Recipient coverage is deliberately limited to explicit prepositional
`to`-datives. Double-object recipient projection and named themes followed by
`to` remain declined: the spent Phase D checkpoint localized all protected
errors to those two proper-object role boundaries, so they are not part of
the safe served set.

## Phase C restart increment 1

The first Phase C restart increment restores one depth-1 nominal PP class
hosted by the safe named-agent active-transitive graph. It is independent of
the withheld double-object constructions.

### Nominal PP modifier selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V a N P a N.`, where the event is a
   licensed `semantic_agent_theme_verb`, the direct object is an existing
   `semantic_bare_theme_noun`, and `P` is one of `beside`, `in`, or `on`.
   Both nominals are indefinite singulars. There is no definiteness, passive
   auxiliary, recipient, complement, coordination, second PP, negation, or
   trailing material.
2. **Complete graph:** the existing named-agent active graph plus one
   modifier-object entity/type and exactly
   `modifier(theme, object, preposition)`. The modifier edge spans the head
   through its PP object, recording both attachment site and evidence. It is
   the ordinary modifier edge, not a depth-specific fact.
3. **Synthetic positives:** a named agent acts on an invented
   `zephyrstone` beside, in, or on another invented `zephyrstone`, proving
   the preposition label is data-driven and repeated types retain distinct
   span-based identities.
4. **Negative neighbours:** subject-attached PPs, definite or named modifier
   objects, unsupported prepositions, omitted articles, second or nested PPs,
   coordination, passives, negation, embedding, and unlicensed or ambiguous
   events and nouns.
5. **Known DEV buyers:** the earlier DEV-only implementation established 59
   complete train buyers and 57 aggregate holdout buyers, all currently
   declined after the checkpoint revert. No holdout rows are inspected.
6. **Licence and safety boundary:** project-local preposition and
   modifier-object categories remain declarative. Ambiguous or quarantined
   nouns stay excluded. The `semantic_to_dative_verb` boundary is unchanged,
   and double-object recipient projection stays withheld.

### Result

The depth-1 nominal-PP rule emits the complete named-agent active graph plus
one modifier-object entity/type and one ordinary modifier edge. The captured
preposition supplies the label; the edge evidence spans the theme head
through the PP object, retaining the exact attachment decision without a
depth-specific fact class.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,452 | 1,511 | +59 | 0 | 7.2% |
| holdout | 1,390 | 1,447 | +57 | 0 | 6.8% |

The nominal-modifier bucket now has 59/2,186 exact train graphs and
57/2,121 exact aggregate holdout graphs. Both harm-ordered diffs have zero
broken exact graphs and zero safe-to-incorrect transitions.

The complete gate is green: 120 focused COGS projection tests, 3,165
full-suite tests, zero COGS lint errors, curated 65/65 twice, and neutral
GSM8K, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO diffs. The dative role
boundary is unchanged.

## Phase C restart increment 2

This increment begins sentential composition with one depth-1 `ccomp` class
joining two complete named-agent event subgraphs.

### Ccomp event selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V that Name V.`, with a licensed
   `semantic_ccomp_matrix_verb` and an existing
   `semantic_intransitive_agent_verb`. Both subjects are bare proper names.
   There is no object, passive, PP, recipient, control gap, coordination,
   negation, second complement, or trailing material.
2. **Complete graph:** two named entity nodes, two normalized event nodes,
   their respective agent roles, and exactly
   `complement(matrix_event, embedded_event, ccomp)`. The complement edge
   spans the matrix through embedded event, preserving overt `that`,
   attachment direction, and provenance.
3. **Synthetic positives:** distinct invented names plus a same-name variant,
   proving entity identity may be shared without collapsing the two event
   references.
4. **Negative neighbours:** omitted `that`; common-noun or definite subjects;
   theme-class, transitive, passive, or ditransitive embedded clauses;
   `xcomp` surfaces; coordination; negation; nesting; matrix objects; and
   unlicensed or ambiguous event forms.
5. **Known DEV buyers:** the earlier DEV-only implementation established 26
   complete train buyers and 17 aggregate holdout buyers, all currently
   declined after the checkpoint revert. No holdout rows are inspected.
6. **Licence and safety boundary:** matrix membership and missing ordinary
   verb lemmas remain project-local YAML data. Unsafe registry forms stay
   excluded. The `semantic_to_dative_verb` and proper-object boundaries are
   unchanged.

### Result

The depth-1 ccomp rule emits two independently span-addressed events, their
named agents, and one directed matrix-to-embedded complement edge backed by
the overt `that` span. Repeated names share an entity without collapsing the
event references.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,511 | 1,537 | +26 | 0 | 7.4% |
| holdout | 1,447 | 1,464 | +17 | 0 | 6.9% |

Both harm-ordered diffs have zero broken exact graphs and zero
safe-to-incorrect transitions. The complete gate is green: 136 focused COGS
tests, 3,181 full-suite tests, zero lint errors, curated twice, and neutral
GSM8K, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO diffs.

## Phase C restart increment 3

This increment adds subject-control `xcomp` composition with one explicitly
shared controller entity.

### Xcomp control selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V to V.`, with licensed
   `semantic_xcomp_matrix_verb` and `semantic_xcomp_agent_verb` forms. The
   subject is one bare proper name; there is no overt embedded subject,
   object, passive, PP, recipient, coordination, negation, nesting, or tail.
2. **Complete graph:** one named entity, two independently span-addressed
   events, `agent` edges from both events to the same controller, and exactly
   `complement(matrix_event, embedded_event, xcomp)`. Sharing is equal role
   targets, never event merging.
3. **Synthetic positive:** an invented name hopes to smirk, asserting the
   shared entity and distinct event references and predicates.
4. **Negative neighbours:** overt embedded subjects; object-control;
   transitive or theme-class infinitives; omitted `to`; ccomp; common-noun
   controllers; passive, coordination, negation, PP tails, nesting; and
   unlicensed or ambiguous forms.
5. **Known DEV buyers:** the earlier DEV-only implementation established 107
   complete train buyers and 96 aggregate holdout buyers, all currently
   declined after the checkpoint revert. No holdout rows are inspected.
6. **Licence and safety boundary:** matrix and embedded agentive membership
   remains declarative project-local YAML. Noun-only ambiguous infinitives
   stay excluded. The proper-object boundary is unchanged.

### Result

The subject-control rule emits one controller entity, two independently
span-addressed events, two agent edges targeting the same controller, and one
directed xcomp edge. Sharing is explicit in the role graph.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,537 | 1,644 | +107 | 0 | 8.1% |
| holdout | 1,464 | 1,560 | +96 | 0 | 7.6% |

Both harm-ordered diffs have zero broken exact graphs and zero
safe-to-incorrect transitions. The complete gate is green: 152 focused COGS
tests, 3,197 full-suite tests, zero lint errors, curated twice, and neutral
GSM8K, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO diffs.

## Phase C restart increment 4

This increment extends nominal PP attachment to arbitrary local chain depth
with one reusable overlapping-link rule.

### Recursive nominal modifier selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** a named-agent licensed active transitive with an
   indefinite theme followed by two or more adjacent indefinite nominal PPs
   using existing modifier licences. The depth-2 surface is
   `Name V a N P a N P a N.`; one mechanism must also serve synthetic depths
   1 through 4.
2. **Complete graph:** the active agent/theme frame plus one entity/type and
   one `modifier(previous_head, object, preposition)` edge per local PP. Each
   edge retains its own immediately preceding head and exact evidence span.
3. **Reusable mechanism:** a default-off `overlapping` pattern option lets
   one declarative `N P a N` rule see every adjacent link. Existing rules keep
   non-overlapping behavior; no rule encodes a depth.
4. **Synthetic positives and termination:** depths 1 through 4 must settle
   through the normal deterministic document fixpoint, with the exact number
   of local modifier edges and provenance records.
5. **Negative neighbours:** definite or named PP objects, unsupported
   prepositions, coordination, event attachment, passives, unlicensed heads,
   malformed articles, complement boundaries, and unsupported standalone
   link fragments.
6. **Known DEV buyers:** the earlier DEV-only implementation established one
   complete nested-modifier buyer in each partition and safe partial
   attachment subgraphs elsewhere. No holdout rows are inspected. No
   vocabulary or quarantine change is required, and the proper-object
   boundary is independent and unchanged.

## Immediate next step

Implement the recorded recursive nominal-modifier class and run its complete
increment gate. Preserve the proper-object boundary and do not rerun either
spent protected slice.

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
