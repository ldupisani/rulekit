# rulekit handoff — semantic projection

**Updated:** 2026-07-23

**Active campaign:** COGS semantic projection

**Status:** Phase B underway; increments 1–5 complete

**Previous capability commit:** `0034a58`
(`Add COGS agentless passive projection`)

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

## Phase B increment 1

The first Phase B increment used only inspectable `dev-train` data to
subdivide the transitive pool by:

- missing graph structure;
- subject construction;
- object construction;
- active/passive voice; and
- named versus indefinite referents.

It selected one frequent, clean class whose complete target requires a general
entity/event/role representation and recorded:

1. the construction class;
2. the complete graph it should buy;
3. representative synthetic positive examples;
4. negative neighbours and ambiguity cases;
5. the expected DEV-train and aggregate DEV-holdout buyers; and
6. which YAML categories, if any, license its role interpretation.

### Phase B increment 1 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** a sentence-initial proper name followed by one
   licensed active transitive event and one bare indefinite singular
   direct-object noun, with no PP, coordination, second object, or trailing
   material beyond punctuation.
2. **Complete graph:** one named entity node, one existential entity node,
   one event node, the event predicate, the object's type, and exact
   `agent(event, name)` and `theme(event, object)` edges. Every node and edge
   must retain the emitting rule provenance and source span.
3. **Synthetic positives:** forms such as “Neris polished a lantern” and
   additional invented regular/irregular event lemmas with an invented common
   noun theme.
4. **Negative neighbours:** definite or named objects, common-noun subjects,
   passives, ditransitives, PP-tailed objects, coordination, negation, and
   lexically unlicensed or sense-ambiguous event heads. These must remain for
   their own construction increment or decline safely.
5. **Expected buyers:** 279 inspectable DEV-train graphs and 228 aggregate
   DEV-holdout graphs have the broad structure. The conservative lexical
   licence excludes unsafe/self-lemma event forms, ambiguous nominal forms,
   and the `difg-mined` quarantine entries. The final licensed class contains
   243 DEV-train buyers (96 exact, 2 safe-partial, 145 declined) and 158
   aggregate DEV-holdout buyers (57 exact, 101 declined). Holdout item text
   remains uninspected.
6. **Declarative licence:** a project-local `semantic_agent_theme_verb`
   category names verbs for which this active direct-object construction
   licenses agent/theme roles. Surface-to-lemma mappings and nominal type
   facts live in the same COGS-local YAML pack; the Python kernel contains no
   member list.

The representation is first-class semantic node/edge facts in the ordinary
fact store. The COGS adapter consumes that typed view; it does not split flat
`Atom` or `VerbalRelation` strings to guess structure.

### Phase B increment 1 result

The licensed active named-agent/indefinite-theme rule produces complete
entity/event/type/role graphs with exact rule and span provenance. A
declarative ownership subcategory prevents newly admitted event vocabulary
from widening the legacy `VerbalRelation` bridge into unserved definite,
passive, PP-tailed, or coordinated neighbours.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 247 | 390 | +143 | 0 | 1.5% → 2.3% |
| DEV-holdout | 213 | 312 | +99 | 0 | 1.3% → 1.8% |

Within the final licensed class, DEV-train moved from 96 exact / 2 partial /
145 declined to 239 exact / 0 partial / 4 declined. Aggregate DEV-holdout
moved from 57 exact / 0 partial / 101 declined to 156 exact / 0 partial / 2
declined. Both harm-ordered diffs report zero broken exact graphs and zero
safe-to-incorrect transitions.

Verification is green: 3,064 synthetic/unit tests; curated twice; GSM8K
DEV-train and DEV-holdout; ASDiv, SVAMP, MAWPS, SciBench, and FOLIO DEV; and
COGS lint with zero errors. Every standing non-COGS snapshot diff is neutral.
No COGS TEST or generalization look was spent.

## Phase B increment 2

The second Phase B increment began the intransitive-role work. It used only
inspectable `dev-train` data to subdivide the 699 intransitive-agent and 1,301
intransitive-theme graphs by:

- named, indefinite, and definite subject construction;
- overt verb form and ambiguity/lemma quality;
- the YAML verb class needed to license agent versus theme; and
- complete-graph blockers beyond the event, type, and single role.

It selected one frequent clean class with complete buyers in both DEV
partitions and recorded its positive graph, negative agent/theme minimal
pairs, ambiguity and overreach cases, expected buyers, and declarative
verb-class licence before implementation.

### Phase B increment 2 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** a sentence-initial bare proper name followed by one
   licensed finite intransitive agent verb and terminal punctuation, with no
   article, complement, object, PP, coordination, negation, auxiliary, or
   trailing material.
2. **Complete graph:** one named entity node, one event node, the normalized
   event predicate, and `agent(event, name)`. Every node and edge retains the
   emitting rule provenance and its exact source span.
3. **Synthetic positives:** forms such as “Neris smiled” and “Mira slept,”
   using invented names and arrangements.
4. **Negative neighbours:** the identical proper-name frame with a
   theme-class verb (“Neris collapsed”); indefinite and definite common-noun
   subjects; transitive, PP-tailed, coordinated, negated, passive, and
   auxiliary constructions; the quarantined `cooked` form; and the unsafe
   self-lemma `called` form. Each remains for its own construction or declines
   safely.
5. **Expected buyers:** the broad named-agent pool contains 305 DEV-train
   rows. Correct existing lemmas plus quarantine-safe new form mappings leave
   277 inspectable DEV-train buyers and 271 aggregate DEV-holdout buyers. All
   548 licensed graphs are declined at the increment-1 baseline. Holdout item
   text remains uninspected.
6. **Declarative licence:** a project-local
   `semantic_intransitive_agent_verb` category states which overt forms
   license an agent role in this construction. Newly admitted forms also join
   the generic semantic-projection ownership category so vocabulary cannot
   widen the legacy `VerbalRelation` bridge into unserved neighbours. Python
   consumes category structure and enumerates no verbs.

### Phase B increment 2 result

The bare-name intransitive-agent rule emits a named entity node, event node,
normalized event predicate, and exact agent role with source-span provenance.
The agent/theme decision is licensed only by
`semantic_intransitive_agent_verb`; the same surface frame with a theme-class
verb emits nothing.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 390 | 661 | +271 | 0 | 2.3% → 3.0% |
| DEV-holdout | 312 | 579 | +267 | 0 | 1.8% → 2.6% |

The intransitive-agent construction now has 271/699 exact DEV-train graphs
and 267/665 exact aggregate DEV-holdout graphs. Both harm-ordered diffs report
zero broken exact graphs and zero safe-to-incorrect transitions.

The pre-implementation estimate was high by six DEV-train and four aggregate
DEV-holdout rows. The six inspectable train misses are capitalized
name/common-noun homographs: `Jack` and `Mason` retain their existing noun
senses and therefore do not satisfy the exact `proper_name` slot. That is a
separate entity-disambiguation construction, not permission to widen the
intransitive rule. The four holdout rows remain aggregate-only and
uninspected.

Verification is green: 3,073 synthetic/unit tests; COGS lint with zero errors;
curated twice; GSM8K DEV-train and DEV-holdout; and ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO DEV. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase B increment 3

The third Phase B increment built the named intransitive-theme minimal pair.
It used only inspectable `dev-train` data to subdivide all 96 named-theme
graphs and found that every row has the bare `Name V.` surface.

### Phase B increment 3 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** a sentence-initial bare proper name followed by one
   licensed finite intransitive theme verb and terminal punctuation, with no
   article, complement, object, PP, coordination, negation, auxiliary, or
   trailing material.
2. **Complete graph:** one named entity node, one event node, the normalized
   event predicate, and `theme(event, name)`. Every node and edge retains the
   emitting rule provenance and its exact source span.
3. **Synthetic positives:** forms such as “Neris reddened” and “Mira
   collapsed,” using invented names and arrangements.
4. **Negative neighbours:** the identical proper-name frame with an
   agent-class verb (“Neris smiled”); indefinite and definite common-noun
   subjects; transitive, PP-tailed, coordinated, negated, passive, and
   auxiliary constructions; and the unsafe self-lemma `broke` and `doubled`
   forms. Each remains for its own construction or declines safely.
5. **Expected buyers:** the broad pool contains 96 DEV-train and 99 aggregate
   DEV-holdout rows. The disjoint, correctly lemmatized theme licence plus
   exact proper-name recognition leaves 90 inspectable DEV-train and 92
   aggregate DEV-holdout buyers, all currently declined. Two train rows are
   name/common-noun homographs; four more train rows and seven aggregate
   holdout rows use excluded self-lemma event forms. Holdout item text remains
   uninspected.
6. **Declarative licence:** a project-local
   `semantic_intransitive_theme_verb` category is disjoint from
   `semantic_intransitive_agent_verb` and states which overt forms license the
   theme role. The quarantine audit found no candidate theme form, and newly
   admitted forms join the generic projection-ownership category. Python
   consumes category structure and enumerates no verbs.

### Phase B increment 3 result

The bare-name intransitive-theme rule emits a named entity node, event node,
normalized event predicate, and exact theme role with source-span provenance.
The agent/theme decision is licensed only by
`semantic_intransitive_theme_verb`; the same surface frame with an agent-class
verb emits nothing.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 661 | 751 | +90 | 0 | 3.0% → 3.3% |
| DEV-holdout | 579 | 671 | +92 | 0 | 2.6% → 2.8% |

The intransitive-theme construction now has 90/1,301 exact DEV-train graphs
and 92/1,282 exact aggregate DEV-holdout graphs. Both harm-ordered diffs
report zero broken exact graphs and zero safe-to-incorrect transitions. The
observed buyer counts exactly match the pre-implementation estimate.

Verification is green: 3,083 synthetic/unit tests; COGS lint with zero errors;
curated twice; GSM8K DEV-train and DEV-holdout; and ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO DEV. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase B increment 4

The fourth Phase B increment begins passive transitives with the largest
simple class that does not require definiteness or an expressed-agent entity:
an indefinite common-noun theme, passive auxiliary and licensed participle,
and no `by` phrase.

### Phase B increment 4 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `A N was V-en.`, where the article is an
   indefinite article, the singular noun is licensed by
   `semantic_bare_theme_noun`, `was` is the passive auxiliary, and the final
   participle is licensed by a new project-local passive category. There is no
   expressed agent, recipient, complement, modifier, coordination, negation,
   or trailing material.
2. **Complete graph:** one indefinite entity node and type edge, one event
   node and normalized event-predicate edge, and
   `theme(event, entity)`. No agent edge is invented when the passive omits
   its agent. Every node and edge retains the emitting rule provenance and
   exact source span.
3. **Synthetic positive:** an invented common noun in the selected passive
   frame, paired with active and expressed-agent neighbours that must remain
   outside this rule.
4. **Negative neighbours:** a definite or named theme; an expressed `by`
   agent; an active clause; an intransitive use; plural agreement; a
   recipient, PP, complement, coordination, or negation tail; quarantined
   `cooked`; and the missing or unsafe participle lemmas `frozen`, `seen`,
   `thrown`, `drawn`, `grown`, `discovered`, `doubled`, `broken`, `missed`,
   `called`, and `known`.
5. **Expected buyers:** the exact surface/graph pool contains 427 inspectable
   DEV-train rows and 432 aggregate DEV-holdout rows. Reusing the existing
   noun licence and admitting only 45 quarantine-safe participles whose
   current registry lemma exactly matches the gold event leaves 214
   DEV-train and 210 aggregate DEV-holdout buyers. Every selected graph is
   currently declined. Holdout item text remains uninspected.
6. **Declarative licence:** a project-local
   `semantic_passive_participle` category states which overt forms license
   this passive construction. It does not infer participial morphology or
   enumerate verbs in Python. The exact sentence pattern, disjoint rule
   identity, and reuse of already-registered event lemmas keep the new
   category from widening active, expressed-agent, definite, ditransitive, or
   embedded neighbours.

### Phase B increment 4 result

The anchored indefinite passive rule emits the common-noun entity and type,
event and normalized predicate, and theme role. It emits no agent edge when
the sentence contains no expressed agent. The rule accepts irregular
participles only through the explicit category and an already-correct
registry lemma.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 751 | 965 | +214 | 0 | 3.3% → 4.1% |
| DEV-holdout | 671 | 881 | +210 | 0 | 2.8% → 3.6% |

All 214 selected DEV-train and 210 aggregate DEV-holdout buyers became exact,
matching the pre-implementation estimate. Both harm-ordered diffs report zero
broken exact graphs and zero safe-to-incorrect transitions. Because the
construction taxonomy is graph-structural, an omitted-agent passive has the
same event/theme-only graph shape as an intransitive-theme sentence and is
reported in that structural bucket; the exact anchored surface and rule
provenance preserve the passive reading.

Verification is green: 3,097 synthetic/unit tests; COGS lint with zero errors;
curated twice; GSM8K DEV-train and DEV-holdout; and ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO DEV. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase B increment 5

The fifth Phase B increment adds the expressed-agent minimal pair of
increment 4: the same indefinite common-noun passive theme and licensed
participle, followed by `by` and an exact proper name.

### Phase B increment 5 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `A N was V-en by Name.`, retaining
   increment 4's indefinite article, bare singular theme noun, `was`
   auxiliary, and `semantic_passive_participle` licence. The terminal agent is
   licensed by the overt `by` phrase and the existing exact `proper_name`
   slot. There is no recipient, modifier, complement, coordination, negation,
   or trailing material.
2. **Complete graph:** increment 4's indefinite entity/type, event/predicate,
   and theme-role graph plus one named entity node and exactly
   `agent(event, name)`. Surface subject order does not determine the semantic
   role. Every node and edge retains the emitting rule provenance and exact
   source span.
3. **Synthetic positive:** the invented `zephyrstone` theme with invented
   name `Neris`, paired with the identical omitted-agent passive and an active
   clause to pin the role alternation.
4. **Negative neighbours:** omitted agents remain increment 4's class;
   common-noun `by` agents, definite or named themes, active order, plural
   agreement, recipients, PP/modifier tails, coordination, negation,
   embedding, and malformed auxiliaries remain outside this rule. The
   increment-4 participle quarantine and unsafe-lemma exclusions remain
   unchanged.
5. **Expected buyers:** the exact surface/graph pool contains 427 inspectable
   DEV-train rows and 466 aggregate DEV-holdout rows. Reusing increment 4's
   noun and 45-participle licences plus exact proper-name recognition leaves
   236 DEV-train and 294 aggregate DEV-holdout buyers, all currently
   declined. On DEV-train, 116 rows use nouns outside the existing semantic
   licence, 71 use excluded participles, and four otherwise eligible rows use
   the `Jack`/`Mason` noun homographs. Holdout item text remains uninspected.
6. **Declarative licence:** no new corpus vocabulary or Python mechanism is
   needed. The existing noun and passive-participle categories license the
   lexical interpretation; the explicit auxiliary, `by` skeleton, sentence
   anchors, and `proper_name` type license the expressed-agent structure.

### Phase B increment 5 result

The expressed-agent passive rule reuses increment 4's entity/type,
event/predicate, and theme projection, then emits the named agent entity and
`agent(event, name)` only when the exact terminal `by Name` skeleton is
present. The omitted-agent and expressed-agent rules remain disjoint.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 965 | 1,205 | +240 | 0 | 4.1% → 5.4% |
| DEV-holdout | 881 | 1,180 | +299 | 0 | 3.6% → 5.2% |

Both harm-ordered diffs report zero broken exact graphs and zero
safe-to-incorrect transitions. The conservative pre-implementation estimate
was low by four DEV-train and five aggregate DEV-holdout rows. On the
inspectable train slice, the four additional buyers use `Jack` or `Mason`:
although those forms retain common-noun senses, the overt `by` context
resolves them as proper-name agents. The five holdout additions remain
aggregate-only and uninspected.

The structural transitive bucket now has 630/3,221 exact DEV-train graphs and
611/3,299 exact aggregate DEV-holdout graphs. Verification is green: 3,113
synthetic/unit tests; COGS lint with zero errors; curated twice; GSM8K
DEV-train and DEV-holdout; and ASDiv, SVAMP, MAWPS, SciBench, and FOLIO DEV.
Every standing non-COGS snapshot diff is neutral. No COGS TEST or
generalization look was spent.

## Immediate next step

Begin ditransitives and recipient roles. Use only inspectable `dev-train` data
to:

- subdivide all 2,661 structural ditransitives by active versus passive
  surface, prepositional versus double-object dative, and named/indefinite/
  definite agent, theme, and recipient;
- choose one frequent, structurally simple active subclass that can reuse the
  existing entity, event, agent, and theme licences while adding exactly one
  recipient entity and `recipient(event, entity)` edge;
- record the complete graph, exact buyers, alternation and attachment
  exclusions, quarantine audit, and aggregate holdout count before
  implementation;
- test prepositional/double-object minimal pairs plus transitive, passive,
  omitted-recipient, PP/modifier, coordination, negation, and embedded
  neighbours; and
- require nonzero exact ditransitive coverage on both DEV partitions with no
  change to the active or passive transitive graphs.

Do not inspect holdout rows or spend COGS TEST/generalization looks.

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
