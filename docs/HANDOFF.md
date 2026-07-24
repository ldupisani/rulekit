# rulekit handoff — semantic projection

**Updated:** 2026-07-24

**Active campaign:** COGS semantic projection

**Status:** PMB coverage increment 5 complete at 66 train exact / 327 correct
edges / 0 incorrect; recall coverage is next

**Current safe DEV baseline:** `964f09f`
(`Add COGS indefinite common subject projection`)

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

### Result

The default-off overlapping matcher preserves existing behavior while one
local nominal-link rule sees every adjacent attachment in a chain. Synthetic
depths 1 through 4 terminate deterministically with locally sourced edges.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,644 | 1,645 | +1 | 0 | 10.5% |
| holdout | 1,560 | 1,561 | +1 | 0 | 10.0% |

The rule additionally creates 584 train and 593 holdout safe partial graphs;
edge precision remains 100%. Both harm-ordered diffs have zero broken exact
graphs and zero safe-to-incorrect transitions. The complete gate is green:
165 focused COGS tests, 3,210 full-suite tests, zero lint errors, curated
twice, and neutral standing-corpus diffs.

## Phase C restart increment 5

This increment applies the reusable local-link machinery to a ccomp chain
terminating in subject-control xcomp.

### Recursive complement selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** depth 2 is exactly
   `Name V that Name V to V.`, using existing ccomp-matrix, xcomp-matrix, and
   xcomp-agent licences. Deeper synthetic forms repeat `Name V that` before
   the terminal control clause.
2. **Complete graph:** one named agent and event per finite clause, one
   terminal infinitival event, directed ccomp edges between adjacent finite
   events, and one terminal xcomp edge whose source and target agent roles
   share the final controller. All event refs remain distinct.
3. **Reusable mechanism:** a vocabulary-free complement-matrix supercategory,
   one overlapping local ccomp-link rule, and one terminal xcomp-link rule.
   No rule names or caps a depth.
4. **Synthetic positives and termination:** one through three successive
   ccomp links before xcomp must produce complete graphs with local
   provenance and deterministic fixpoint termination.
5. **Negative neighbours:** missing or replaced `that`/`to`; common or
   definite subjects; theme or transitive terminals; object-control;
   coordination; negation; modifiers; passives; and unlicensed forms.
6. **Known DEV buyers:** the earlier DEV-only implementation established
   five complete train and two aggregate holdout buyers. No vocabulary or
   quarantine change is required, no holdout rows are inspected, and the
   proper-object boundary is unchanged.

### Result

Two reusable local rules project each adjacent ccomp hop and the terminal
subject-control xcomp. Synthetic total complement depths 2 through 4 produce
complete graphs with distinct events, directed complement edges, explicit
controller sharing, local provenance, and deterministic termination.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,645 | 1,650 | +5 | 0 | 10.8% |
| holdout | 1,561 | 1,563 | +2 | 0 | 10.2% |

Both harm-ordered diffs have zero broken exact graphs and zero
safe-to-incorrect transitions. The complete gate is green: 179 focused COGS
tests, 3,224 full-suite tests, zero lint errors, curated twice, and neutral
GSM8K, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO diffs.

## Immediate next step

Preserve completed post-D DEV campaign 2 as the COGS DEV baseline. PMB
coverage increment 1 implemented the exact anchored `A/An N V-s.`
common-subject agentive-intransitive class and hit its locked delta: train is
1 exact / 6 partial / 9,058 declined / 0 incorrect at 100% edge precision;
development remains 0/0/990/0. Coverage increment 2 implemented the frozen
proper-name simple-past Agent class and hit its lock: train is now 34 exact /
0 partial / 9,031 declined / 0 incorrect with 135 correct edges and 0.3%
recall; development remains unchanged. Coverage increment 3
`Subject V-ed a/an N.` is complete at its quarantine-safe lock: 52 exact /
243 correct edges / 0 incorrect on train; development remains unchanged.
Coverage increment 4 `TypedSubject V-ed at/to TypedRecipient.` is complete at
62 train exact / 303 correct edges / 0 incorrect, adding explicit Recipient.
The expected aggregate development buyer did not materialize and development
stays at zero commitments. Coverage increment 5 adds the explicit SBN
noun-to-noun `Of` relation and hits its four-buyer train lock: 66 complete
graphs / 327 correct edges / zero incorrect. The full standing gate is green.
Profile the next train-only complete-graph class needed to cross 1% recall.

This clears the precision prerequisite for coverage, not the Phase E entry
gate: PMB has 66 complete train graphs and 327 correct edges, but only 0.6%
recall and no pristine development transfer. The attachment/complement bucket
is now satisfied. A development profiling diagnostic accidentally printed inspectable
rows despite the campaign's stricter aggregate-only choice; the observations
are quarantined and the deviation is recorded in the gate plan. No protected
PMB test look has been spent. Preserve the proper-object boundary and do not
rerun COGS TEST/generalization or PMB test.

## Phase C restart exit audit

The safe restart has reached the Phase D decision boundary:

| Target | DEV-train exact | DEV-holdout exact | Result |
| --- | ---: | ---: | --- |
| nominal PP modifier | 59 | 57 | pass |
| ccomp embedding | 26 | 17 | pass |
| xcomp control/sharing | 107 | 96 | pass |
| nested nominal modifier | 1 | 1 | pass |
| nested complement | 5 | 2 | pass |

The final DEV state is 1,650 exact / 653 safe partial / 0 incorrect on train
and 1,563 / 660 / 0 on holdout, with 100% projected-edge precision and
10.8%/10.2% edge recall. Active and passive constructions use the same
agent/theme role edge kinds, and the explicit-to dative uses those same
agent/theme edges plus the ordinary recipient edge. All standing gates are
neutral.

The original Phase C target also included the double-object/prepositional
dative alternation. That target is not counted as passed: the spent protected
generalization checkpoint proved its proper-object role transfer unsafe. The
post-checkpoint plan explicitly retires that half of the target, keeps
double-object and named-theme-plus-`to` surfaces declined, and retains only
the construction-specific explicit-to recipient graph.

Both protected ledgers still contain exactly one row. Phase D is therefore a
decision and handoff point, not authorization for another protected look.

## Phase D disposition

The rebuilt candidate is accepted as the safe post-checkpoint development
baseline and the restart campaign is closed. It is not described as having
passed a second protected checkpoint, because no second measurement exists.

The disposition rests on three bounded facts:

1. the permitted protected aggregates localized every one of the 58 failures
   to the two proper-object ditransitive cases, while every other disclosed
   case and structural class had zero incorrect graphs;
2. compared with failed batch `e657fc9`, the rebuilt runtime differs only by
   replacing the generic ditransitive category with
   `semantic_to_dative_verb` and deleting the double-object projection rule;
   the remaining semantic rules and general kernel machinery are unchanged;
3. the boundary is executable: direct proper objects remain themes,
   positional proper objects emit no recipient, double-object surfaces
   decline, and active/passive surfaces share one abstract role topology.

The final audit passes 180 focused COGS tests and all 3,225 unit/synthetic
tests. The latest complete increment gate also records 100% DEV edge
precision and neutral curated, GSM8K, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO
diffs.

This evidence supports freezing the repaired DEV baseline and removing the
known failure mechanism. It does not support a numerical claim about repaired
TEST or generalization precision.

## Post-D DEV campaign 1 — determiner-backed common subjects

This new DEV-only campaign extends already safe event frames from proper-name
subjects to explicitly determined common-noun subjects. It begins from frozen
baseline `2dd8a2a`; the Phase D evidence is not reused as a tuning set.

The locked campaign exit is:

- 100% projected-edge precision and zero incorrect graphs on both DEV
  partitions;
- nonzero complete buyers in both partitions for a definite common-noun
  agent in an active transitive frame;
- article-backed definiteness with no uniqueness or cross-mention identity;
- no widening of the proper-object or recipient-role boundary; and
- neutral synthetic, lint, regression, and cross-corpus gates.

### Increment 1 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `The N V a N.`, where the subject is an
   existing `semantic_nominal_entity_noun`, the event is a licensed
   `semantic_agent_theme_verb`, and the object is an existing
   `semantic_bare_theme_noun`. There is no proper object, recipient, passive,
   modifier, complement, coordination, negation, or trailing material.
2. **Complete graph:** two typed entity nodes, one normalized event node,
   agent and theme role edges, and exactly one `definite(subject)` edge
   licensed by the initial article. Definiteness records discourse status
   only.
3. **Synthetic positive:** the invented definite common subject
   `zephyrstone` appreciates an indefinite `zephyrstone`, proving that equal
   noun types retain distinct span-based entities and only the subject is
   definite.
4. **Negative neighbours:** indefinite, named, plural, modified, or
   coordinated subjects; definite or named objects; passive order;
   ditransitives; PP and complement tails; negation; unlicensed nouns or
   events; and missing punctuation.
5. **Expected buyers:** exact DEV-train profiling found 49 currently declined
   buyers. The same mechanical licence reports 58 aggregate DEV-holdout
   buyers without inspecting holdout rows.
6. **Licence and safety boundary:** the existing vocabulary-free nominal
   supercategory structurally joins already audited noun categories. No
   vocabulary, quarantine, Python mechanism, recipient rule, or ditransitive
   category changes.

### Result and exit audit

The rule emits two span-distinct typed entities, one event, ordinary
agent/theme roles, and one article-backed definite edge on the subject only.
It adds no vocabulary or runtime mechanism.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,650 | 1,699 | +49 | 0 | 11.2% |
| holdout | 1,563 | 1,621 | +58 | 0 | 10.6% |

The buyer counts exactly match the selection estimate. Both harm-ordered
diffs have zero broken exact graphs and zero safe-to-incorrect transitions.
Projected-edge precision remains 100%.

The complete gate is green: 192 focused COGS tests, 3,237 full-suite tests,
zero lint errors, curated 65/65 twice, and neutral GSM8K, ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO diffs. Every locked post-D campaign 1 condition is met,
so the one-increment campaign is complete.

## Post-D DEV campaign 2 — indefinite common subjects

This separate DEV-only campaign extends the same licensed active frame to an
explicitly indefinite common-noun subject. It begins from completed post-D
campaign 1; protected checkpoint evidence is not a tuning source.

The locked exit conditions are 100% projected-edge precision, zero incorrect
graphs, complete buyers in both DEV partitions, no definite edge without
`the`, no recipient-boundary widening, and neutral standing gates.

### Selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `A/An N V a/an N.`, with an existing
   `semantic_nominal_entity_noun` subject, licensed
   `semantic_agent_theme_verb`, and existing `semantic_bare_theme_noun`
   object. There is no proper object, recipient, passive, modifier,
   complement, coordination, negation, or tail.
2. **Complete graph:** two span-distinct typed entities, one normalized event,
   and ordinary agent/theme roles. Neither entity is definite.
3. **Synthetic positive:** an indefinite invented `zephyrstone` appreciates
   another indefinite `zephyrstone`, proving equal types retain different
   span identities without a definite edge.
4. **Negative neighbours:** definite, named, plural, modified, or coordinated
   subjects; definite or named objects; passive and ditransitive order; PP or
   complement tails; negation; unlicensed words; and missing punctuation.
5. **Expected buyers:** DEV-train profiling found 66 currently declined
   buyers. The same mechanical licence reports 71 aggregate DEV-holdout
   buyers without inspecting holdout rows.
6. **Licence and boundary:** no vocabulary, quarantine, category, Python,
   recipient, or ditransitive changes. The existing audited noun and event
   categories are reused exactly.

### Result and exit audit

The rule emits two span-distinct indefinite entities, one event, and ordinary
agent/theme roles. It emits no definite edge and changes no vocabulary or
runtime mechanism.

| DEV partition | Before exact | After exact | Gain | Incorrect | Edge recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1,699 | 1,765 | +66 | 0 | 11.6% |
| holdout | 1,621 | 1,692 | +71 | 0 | 11.1% |

Both buyer counts exactly match the selection estimate. The harm-ordered
diffs have zero broken exact graphs and zero safe-to-incorrect transitions;
projected-edge precision remains 100%.

The complete gate is green: 204 focused COGS tests, 3,249 full-suite tests,
zero lint errors, curated 65/65 twice, and neutral GSM8K, ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO diffs. Every locked post-D campaign 2 condition is met.

## Increment protocol

For every semantic-projection DEV increment:

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
