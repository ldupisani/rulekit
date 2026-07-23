# rulekit handoff — semantic projection

**Updated:** 2026-07-23

**Active campaign:** COGS semantic projection

**Status:** Phase C underway; increment 6 complete, exit audit next

**Previous capability commit:** pending commit
(`Add recursive COGS complement projection`)

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

## Phase B increment 6

The sixth Phase B increment begins ditransitives with the simple active
prepositional-dative class: named agent, licensed event, indefinite
common-noun theme, `to`, and named recipient.

### Phase B increment 6 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V a N to Name.`, with sentence
   anchors, exact proper-name agent and recipient, one bare singular
   `semantic_bare_theme_noun`, and a new declarative ditransitive-event
   category. There is no definiteness, modifier, second PP, coordination,
   negation, complement, passive auxiliary, or trailing material.
2. **Complete graph:** named agent entity, event and normalized predicate,
   indefinite theme entity/type, named recipient entity, and the three roles
   `agent(event, agent)`, `theme(event, theme)`, and
   `recipient(event, recipient)`. Every node and edge retains the emitting
   rule provenance and exact source span.
3. **Synthetic positive:** `Neris` transfers an invented `zephyrstone` to
   invented recipient `Mira`, paired with the corresponding double-object,
   ordinary transitive, and passive surfaces.
4. **Negative neighbours:** double-object order, omitted recipient,
   indefinite or definite common-noun recipients, non-name agents, definite
   or named themes, passive datives, modifier/PP tails, coordination,
   negation, embedding, and malformed event forms. Each remains for its own
   construction or declines safely.
5. **Expected buyers:** the exact class contains 51 inspectable DEV-train and
   38 aggregate DEV-holdout rows. Reusing the existing theme-noun licence and
   exact name recognition, while admitting only eight overt forms with
   already-correct registry lemmas, leaves 30 DEV-train and 18 aggregate
   DEV-holdout buyers, all currently declined. Fourteen train rows use themes
   outside the existing semantic licence and seven use missing or incorrect
   event lemmas. Holdout item text remains uninspected.
6. **Declarative licence:** a project-local `semantic_ditransitive_verb`
   category contains `brought`, `fed`, `gave`, `offered`, `passed`, `rented`,
   `sent`, and `sold`. The quarantine audit found none of these forms. Python
   consumes the category and enumerates no vocabulary.

### Phase B increment 6 result

The active prepositional-dative rule emits one event and the same
agent/theme/recipient role graph regardless of the surface position of those
arguments. The `to` skeleton licenses recipient; the double-object
alternation remains safely declined for Phase C's cross-alternation work.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,205 | 1,235 | +30 | 0 | 5.4% → 5.6% |
| DEV-holdout | 1,180 | 1,198 | +18 | 0 | 5.2% → 5.4% |

The structural ditransitive bucket now has 30/2,661 exact DEV-train graphs
and 18/2,687 exact aggregate DEV-holdout graphs. The observed buyers exactly
match the pre-implementation estimate. Both harm-ordered diffs report zero
broken exact graphs and zero safe-to-incorrect transitions.

Verification is green: 3,128 synthetic/unit tests; COGS lint with zero errors;
curated twice; GSM8K DEV-train and DEV-holdout; and ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO DEV. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase B increment 7

The seventh Phase B increment adds definiteness as the exact minimal pair of
increment 4: a definite common-noun theme in an agentless passive.

### Phase B increment 7 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `The N was V-en.`, with an anchored
   definite article, one bare singular `semantic_bare_theme_noun`, the `was`
   auxiliary, and one licensed `semantic_passive_participle`. There is no
   expressed agent, recipient, modifier, coordination, negation, complement,
   or trailing material.
2. **Complete graph:** increment 4's theme entity/type, event/predicate, and
   `theme(event, entity)` role plus exactly `definite(entity)`. The definite
   edge records the article-backed discourse status; it does not assert a
   unique real-world object or identity with any other mention. Every node and
   edge retains the emitting rule provenance and exact source span.
3. **Synthetic positive:** `The zephyrstone was appreciated.`, paired with
   increment 4's indefinite form and increment 5's expressed-agent passive.
4. **Negative neighbours:** indefinite and named themes; plural agreement;
   expressed `by` agents; recipients; definite noun modifiers or compounds;
   PP, coordination, negation, and embedded tails; active order; and all
   increment-4 quarantine or unsafe-participle exclusions.
5. **Expected buyers:** the exact class contains 439 inspectable DEV-train and
   412 aggregate DEV-holdout rows. Reusing the existing noun and
   passive-participle licences leaves 217 DEV-train and 192 aggregate
   DEV-holdout buyers, all currently declined. On train, 159 rows use themes
   outside the noun licence and 63 use participles outside the existing
   passive licence. Holdout item text remains uninspected.
6. **Declarative licence:** no new vocabulary or Python mechanism is needed.
   The existing categories license noun and event interpretation; the exact
   definite article and passive skeleton license the new graph edge.

### Phase B increment 7 result

The definite agentless-passive rule emits increment 4's complete
entity/type, event/predicate, and theme-role graph plus one definite edge
whose evidence spans the article and noun. It emits no uniqueness or
cross-mention identity claim.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,235 | 1,452 | +217 | 0 | 5.6% → 6.8% |
| DEV-holdout | 1,198 | 1,390 | +192 | 0 | 5.4% → 6.4% |

The observed buyer counts exactly match the pre-implementation estimate.
Both harm-ordered diffs report zero broken exact graphs and zero
safe-to-incorrect transitions.

Verification is green: 3,144 synthetic/unit tests; COGS lint with zero errors;
curated twice; GSM8K DEV-train and DEV-holdout; and ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO DEV. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase B exit audit

Phase B meets its locked exit gate:

- edge precision is 100% and incorrect graphs are zero on both DEV
  partitions;
- total exact coverage is 1,452/12,056 on DEV-train and 1,390/12,099 on
  aggregate DEV-holdout, above the 247/213 Phase A baseline;
- every required structural class has nonzero exact buyers on both
  partitions: transitive 630/611, ditransitive 30/18, intransitive-agent
  271/267, and intransitive-theme 521/494;
- named and indefinite entities, verb-class-sensitive intransitives, active
  and passive transitives with omitted or expressed agents, recipient roles,
  and article-backed definiteness all have complete buyers;
- every shipped class has exact source-span and rule provenance, with no
  unsupported uniqueness or identity claim; and
- every increment retained zero new incorrect edges and neutral standing
  regression/cross-corpus gates.

The protected COGS TEST/generalization checkpoint is Phase D, after both
Phases B and C meet their DEV objectives. It remains unspent.

## Phase C increment 1

The first Phase C increment begins compositional attachment with one depth-1
nominal PP class hosted by the already served active-transitive role graph.

### Phase C increment 1 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V a N P a N.`, where the event is a
   licensed `semantic_agent_theme_verb`, the direct object is an existing
   `semantic_bare_theme_noun`, and `P` is one of the declaratively licensed
   nominal modifiers `beside`, `in`, or `on`. Both nominals are indefinite
   singulars. There is no definiteness, passive auxiliary, recipient,
   complement, coordination, second PP, negation, or trailing material.
2. **Complete graph:** the existing named-agent active graph—agent entity,
   event/predicate, theme entity/type, and exact agent/theme roles—plus one
   modifier-object entity/type and exactly
   `modifier(theme, object, preposition)`. The modifier edge spans the head
   through its PP object, so its provenance records both the attachment site
   and attachment evidence. It uses the ordinary `modifier` graph edge, not a
   depth-specific fact, and can therefore be reused by the later nested-PP
   increment.
3. **Synthetic positives:** a named agent admires an invented
   `zephyrstone` beside, in, or on another invented `zephyrstone`, proving
   that the preposition label is data-driven while node identity remains
   span-based even when both type predicates are equal.
4. **Negative neighbours:** subject-attached PPs, definite or named modifier
   objects, unsupported prepositions, omitted articles, second or nested PPs,
   coordination, passives, negation, embedding, and lexically unlicensed or
   ambiguous events and nouns. Each must remain for its own construction or
   decline safely.
5. **Expected buyers:** the exact class has 122 inspectable DEV-train rows.
   Existing event and theme licences plus a modifier-object category
   containing only already known unambiguous noun entries leave 59
   DEV-train buyers: 20 `beside`, 22 `in`, and 17 `on`. The same licence has
   59 aggregate DEV-holdout buyers. All 118 buyers are currently declined;
   holdout item text remains uninspected.
6. **Declarative licence and audit:** new project-local preposition and
   modifier-object categories contain no Python vocabulary. The object
   category contains 23 corpus-relevant existing noun-only entries plus the
   synthetic-only `zephyrstone`. Missing noun vocabulary remains excluded, as
   do ambiguous `log` and quarantined `tiger`; none of the selected words or
   prepositions is quarantined.

### Phase C increment 1 result

The depth-1 nominal-PP rule emits the complete named-agent active graph plus
one modifier-object entity/type and one ordinary modifier edge. The captured
preposition supplies the edge label; the edge's evidence spans the theme head
through the PP object, retaining an exact, inspectable attachment decision.
The same edge type can represent later nested attachments without a
depth-specific schema or fact class.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,452 | 1,511 | +59 | 0 | 6.8% → 7.2% |
| DEV-holdout | 1,390 | 1,447 | +57 | 0 | 6.4% → 6.8% |

The nominal-modifier bucket now has 59/2,186 exact DEV-train graphs and
57/2,121 exact aggregate DEV-holdout graphs. Train exactly matches the
pre-implementation buyer estimate. Two of the 59 mechanically predicted
holdout buyers remained safely declined; their rows were not inspected and
the dormant join is retained as an aggregate-only observation. Both
harm-ordered diffs report zero broken exact graphs and zero safe-to-incorrect
transitions.

Verification is green: 3,160 synthetic/unit tests; 115 focused COGS
projection tests; COGS lint with zero errors; curated 65/65 twice; GSM8K
DEV-train 104 and DEV-holdout 40; ASDiv 44; SVAMP 30; MAWPS 9; SciBench 6;
and FOLIO 0 committed. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase C increment 2

The second Phase C increment begins sentential composition with one depth-1
`ccomp` class joining two complete named-agent event subgraphs.

### Phase C increment 2 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V that Name V.`, where the matrix
   form is a declaratively licensed `semantic_ccomp_matrix_verb` and the
   embedded form is an existing `semantic_intransitive_agent_verb`. Both
   subjects are bare proper names. There is no object, definiteness, passive,
   PP, recipient, control gap, coordination, negation, second complement, or
   trailing material.
2. **Complete graph:** two named entity nodes and two event nodes; normalized
   event predicates; `agent(matrix_event, matrix_name)` and
   `agent(embedded_event, embedded_name)`; and exactly
   `complement(matrix_event, embedded_event, ccomp)`. The complement edge
   spans the matrix event through the embedded event, preserving the overt
   `that`-licensed attachment and direction. Repeated surface names may share
   one constant node without sharing the two distinct event refs.
3. **Synthetic positive:** invented name `Neris` hopes that invented name
   `Mira` smiles, paired with a same-name variant to prove entity identity
   and event identity remain distinct.
4. **Negative neighbours:** omitted `that`; common-noun or definite subjects;
   theme-class embedded verbs; transitive, passive, or ditransitive embedded
   clauses; `xcomp`/control surfaces; coordination; negation; nested
   complements; matrix objects; and lexically unlicensed or ambiguous event
   forms. Each remains for its own construction or declines safely.
5. **Expected buyers:** the exact graph/surface class contains 34 inspectable
   DEV-train rows. Conservative matrix and embedded licences leave 26
   DEV-train buyers and 18 aggregate DEV-holdout buyers, all currently
   declined. Holdout item text remains uninspected.
6. **Declarative licence and audit:** the matrix category contains
   `admired`, `believed`, `confessed`, `dreamed`, `hoped`, `imagined`,
   `liked`, `noticed`, and `respected`. Five missing forms receive ordinary
   project-local verb/lemma entries and join the existing projection-owned
   guard category. No selected form is quarantined. Existing `said` and
   `thought` forms lack safe registry lemmas and remain excluded rather than
   widening a shared pack.

### Phase C increment 2 result

The depth-1 `ccomp` rule emits two independently span-addressed events, their
named agents, and one directed matrix-to-embedded complement edge backed by
the overt `that` span. Repeated names share one constant entity while the
events remain distinct, preserving identity without collapsing eventualities.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,511 | 1,537 | +26 | 0 | 7.2% → 7.4% |
| DEV-holdout | 1,447 | 1,464 | +17 | 0 | 6.8% → 6.9% |

The `ccomp` bucket now has 26/970 exact DEV-train graphs and 17/1,028 exact
aggregate DEV-holdout graphs. Train exactly matches the pre-implementation
estimate. One of the 18 mechanically predicted holdout buyers remained safely
declined; its row was not inspected. Both harm-ordered diffs report zero
broken exact graphs and zero safe-to-incorrect transitions.

Verification is green: 3,176 synthetic/unit tests; 131 focused COGS
projection tests; COGS lint with zero errors; curated 65/65 twice; GSM8K
DEV-train 104 and DEV-holdout 40; ASDiv 44; SVAMP 30; MAWPS 9; SciBench 6;
and FOLIO 0 committed. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase C increment 3

The third Phase C increment adds subject-control `xcomp` composition with one
explicitly shared controller entity.

### Phase C increment 3 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V to V.`, where the matrix event is
   a licensed `semantic_xcomp_matrix_verb` and the infinitival event is a
   licensed `semantic_xcomp_agent_verb`. The subject is one bare proper name.
   There is no overt embedded subject, object, definiteness, passive, PP,
   recipient, coordination, negation, second complement, or trailing
   material.
2. **Complete graph:** one named entity node and two independently
   span-addressed event nodes; normalized matrix and embedded predicates;
   `agent(matrix_event, controller)` and
   `agent(embedded_event, controller)` targeting the same entity ref; and
   exactly `complement(matrix_event, embedded_event, xcomp)`. The overt `to`
   and exact construction license subject control; sharing is represented by
   equal role targets, not by copying or merging the two events.
3. **Synthetic positive:** invented `Neris` hopes to smirk, with assertions
   that both event-agent edges share `Neris` while the event refs and
   predicates remain distinct.
4. **Negative neighbours:** overt embedded subjects; object-control and
   transitive infinitives; theme-class infinitives; omitted `to`; `ccomp`
   surfaces; common-noun or definite controllers; passive, coordination,
   negation, PP tails, and nested complements; and lexically unlicensed or
   ambiguous matrix/embedded forms.
5. **Expected buyers:** the exact named subject-control surface has 282
   inspectable DEV-train rows. Correct existing lemma mappings leave 123
   structural candidates; excluding noun-only ambiguous infinitives leaves
   109 DEV-train and 96 aggregate DEV-holdout buyers, all currently declined.
   Holdout item text remains uninspected.
6. **Declarative licence and audit:** the matrix category contains `dreamed`,
   `hoped`, `liked`, `loved`, `needed`, and `wanted`. The embedded category
   contains 17 agentive infinitives; seven missing forms receive project-local
   verb entries and join the projection-owned guard. Existing noun-only
   `dance`, `hunt`, and `nap` remain excluded rather than widening shared
   lexicon senses. No selected form is quarantined; quarantined `cooked` does
   not license or block the distinct selected infinitive `cook`.

### Phase C increment 3 result

The subject-control rule emits one controller entity, two independently
span-addressed events, two agent edges targeting the same controller ref, and
one directed `xcomp` edge. Referent sharing is therefore explicit in the role
graph rather than inferred from duplicate names or represented by merging the
two events.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,537 | 1,644 | +107 | 0 | 7.4% → 8.1% |
| DEV-holdout | 1,464 | 1,560 | +96 | 0 | 6.9% → 7.6% |

The `xcomp` bucket now has 107/601 exact DEV-train graphs and 96/605 exact
aggregate DEV-holdout graphs. Holdout exactly matches the pre-implementation
estimate; two of the 109 mechanically predicted train buyers remained safely
declined. Both harm-ordered diffs report zero broken exact graphs and zero
safe-to-incorrect transitions.

Verification is green: 3,192 synthetic/unit tests; 147 focused COGS
projection tests; COGS lint with zero errors; curated 65/65 twice; GSM8K
DEV-train 104 and DEV-holdout 40; ASDiv 44; SVAMP 30; MAWPS 9; SciBench 6;
and FOLIO 0 committed. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase C increment 4

The fourth Phase C increment demonstrates role-graph invariance across the
double-object and prepositional-dative surface alternation.

### Phase C increment 4 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** exactly `Name V Name a N.`, where the event is an
   existing `semantic_ditransitive_verb`, the first post-verbal name is the
   recipient, and the final common noun is an existing
   `semantic_bare_theme_noun`. There is no `to`, definiteness, passive, PP,
   modifier, coordination, negation, complement, or trailing material.
2. **Complete graph:** the identical four-node, five-edge semantic graph
   emitted for Phase B's `Name V a N to Name.` prepositional dative: named
   agent and recipient entities, one indefinite typed theme entity, one event
   predicate, and `agent`, `theme`, and `recipient` role edges. Surface
   position changes no role kind or edge direction.
3. **Synthetic alternation pair:** `Neris` gives invented recipient `Mira` an
   invented `zephyrstone`, paired with `Neris` giving the same
   `zephyrstone` to `Mira`; both must have equal labeled role topology after
   abstracting only the deliberately different token-indexed runtime refs.
4. **Negative neighbours:** omitted recipients or themes; prepositional
   datives handled by the existing rule; indefinite or definite common-noun
   recipients; definite or named themes; passive datives; modifiers,
   coordination, negation, embedding, malformed order, and unlicensed event
   forms.
5. **Expected buyers:** the exact graph/surface class contains 53 inspectable
   DEV-train rows. Reusing the existing event and theme licences leaves 33
   DEV-train and 31 aggregate DEV-holdout buyers, all currently declined.
   Holdout item text remains uninspected.
6. **Declarative licence and audit:** no new vocabulary or Python mechanism
   is needed. Seven existing ditransitive forms have observed train buyers;
   all selected forms and themes passed the earlier quarantine audit. The
   rule emits the same role edge kinds used by the prepositional alternant.

### Phase C increment 4 result

The double-object rule emits the same event, entity/type, and
agent/theme/recipient role topology as the existing prepositional dative.
Only token-indexed runtime refs differ with surface order; no
surface-order-specific role or semantic fact type was introduced.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,644 | 1,677 | +33 | 0 | 8.1% → 8.4% |
| DEV-holdout | 1,560 | 1,591 | +31 | 0 | 7.6% → 7.8% |

The ditransitive bucket now has 63/2,661 exact DEV-train graphs and 49/2,687
exact aggregate DEV-holdout graphs. Both observed buyer counts exactly match
the pre-implementation estimate. Both harm-ordered diffs report zero broken
exact graphs and zero safe-to-incorrect transitions.

Verification is green: 3,207 synthetic/unit tests; 162 focused COGS
projection tests; COGS lint with zero errors; curated 65/65 twice; GSM8K
DEV-train 104 and DEV-holdout 40; ASDiv 44; SVAMP 30; MAWPS 9; SciBench 6;
and FOLIO 0 committed. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase C increment 5

The fifth Phase C increment extends nominal PP attachment to arbitrary local
chain depth with one reusable overlapping-link rule.

### Phase C increment 5 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** a named-agent licensed active transitive with an
   indefinite theme followed by two or more adjacent indefinite nominal PPs,
   where every preposition and noun is in the existing modifier licences.
   The inspectable depth-2 corpus surface is exactly
   `Name V a N P a N P a N.`; the same mechanism must accept synthetic
   depths 1, 2, 3, and 4 without depth-specific rules.
2. **Complete graph:** the existing active agent/theme event graph plus one
   entity/type node and one directed
   `modifier(previous_head, object, preposition)` edge for every local PP.
   Each link's source is the immediately preceding nominal ref, not the root
   theme for all depths, and each edge retains its own head-through-object
   evidence span.
3. **Reusable mechanism:** add a default-off `overlapping` pattern-rule
   option. When enabled, the generic matcher advances one unit after a match
   start rather than after the whole match, so one declarative `N P a N`
   link rule sees every adjacent, intentionally overlapping pair in a chain.
   Existing rules retain non-overlapping behavior. A separate prefix root rule
   emits the already licensed event frame once; neither rule encodes a depth.
4. **Synthetic positives and termination:** invented `Neris`/`zephyrstone`
   chains at depths 1 through 4 must produce the complete graph. The depth-4
   case must settle through the normal document fixpoint in one round and
   produce exactly four modifier edges with local provenance.
5. **Negative neighbours:** definite or named PP objects, unsupported
   prepositions, coordination, event-attached PPs, passives, unlicensed event
   or noun heads, malformed articles, and complement boundaries. Root-frame
   overreach and standalone link fragments must not create an unsupported
   complete graph.
6. **Expected buyers and licence:** the exact all-indefinite depth-2 surface
   has three inspectable DEV-train rows. Existing event/theme/preposition and
   modifier-object licences leave one DEV-train and one aggregate
   DEV-holdout buyer, both currently declined. A new noun supercategory
   structurally unites the existing theme and modifier-object subcategories
   without copying either member list. No vocabulary or quarantine change is
   needed; holdout item text remains uninspected.

### Phase C increment 5 result

The default-off overlapping matcher preserves all existing rule behavior while
letting one local nominal-link rule see every adjacent edge in an attachment
chain. Synthetic depths 1 through 4 produce complete graphs; the depth-4 case
settles in one normal document round with four locally sourced modifier edges.
The corpus depth-2 class gains complete buyers in both DEV partitions.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,677 | 1,678 | +1 | 0 | 8.4% → 10.8% |
| DEV-holdout | 1,591 | 1,592 | +1 | 0 | 7.8% → 10.2% |

The nested-modifier bucket now has 1/199 exact DEV-train and 1/210 exact
aggregate DEV-holdout graph, exactly matching the pre-implementation
estimate. The reusable local rule additionally moved 584 train and 593
holdout graphs from declined to safe partial by emitting only gold-consistent
attachment/type subgraphs; edge precision remains 100%. Both harm-ordered
diffs report zero broken exact graphs and zero safe-to-incorrect transitions.

Verification is green: 3,220 synthetic/unit tests; 175 focused COGS
projection tests; COGS lint with zero errors; curated 65/65 twice; GSM8K
DEV-train 104 and DEV-holdout 40; ASDiv 44; SVAMP 30; MAWPS 9; SciBench 6;
and FOLIO 0 committed. Every standing non-COGS snapshot diff is neutral. No
COGS TEST or generalization look was spent.

## Phase C increment 6

The sixth Phase C increment applies the reusable local-link machinery to
nested sentential composition: a `ccomp` chain terminating in subject-control
`xcomp`.

### Phase C increment 6 selection brief

Selected before implementation on 2026-07-23:

1. **Construction class:** the inspectable depth-2 surface is exactly
   `Name V that Name V to V.`, where the first matrix form is an existing
   `semantic_ccomp_matrix_verb`, the controller event is an existing
   `semantic_xcomp_matrix_verb`, and the infinitive is an existing
   `semantic_xcomp_agent_verb`. Synthetic deeper forms repeat
   `Name V that` before the terminal control clause.
2. **Complete graph:** one named agent and one event/predicate per overt
   finite clause; one terminal infinitival event; directed `ccomp` edges for
   every matrix-to-embedded finite event; and one terminal `xcomp` edge whose
   source and target agent roles share the final controller entity. Event refs
   remain distinct at every depth.
3. **Reusable mechanism:** make the existing ccomp- and xcomp-matrix
   categories children of one vocabulary-free semantic complement-matrix
   supercategory. One overlapping local ccomp-link rule emits every adjacent
   finite-clause hop; one local terminal xcomp-link rule emits explicit
   controller sharing. Neither rule names or caps a depth.
4. **Synthetic positives and termination:** chains with one, two, and three
   successive `ccomp` links before the terminal `xcomp` must produce complete
   graphs (total complement depths 2–4), retain local direction/provenance,
   and settle deterministically through the normal document fixpoint.
5. **Negative neighbours:** missing or replaced `that`/`to`; common-noun or
   definite subjects; theme-class or transitive terminal events;
   object-control; coordination; negation; PP/modifier tails; passive
   embedded clauses; and unlicensed matrix, controller, or infinitive forms.
6. **Expected buyers and licence:** the exact depth-2 all-name surface has 13
   inspectable DEV-train rows. Existing lemma and category licences leave five
   DEV-train and two aggregate DEV-holdout buyers, all currently declined.
   No vocabulary or quarantine change is required, and holdout item text
   remains uninspected.

### Phase C increment 6 result

Two reusable overlapping local rules project every adjacent finite `ccomp`
hop and the terminal subject-control `xcomp`. Synthetic total complement
depths 2 through 4 produce complete graphs in one deterministic document
round, with distinct events, directed complement edges, explicit shared
controller roles, and local rule provenance. The corpus depth-2 class gains
exactly the complete buyers predicted in both DEV partitions.

| split | before exact | after exact | new exact | incorrect | edge recall |
|---|---:|---:|---:|---:|---:|
| DEV-train | 1,678 | 1,683 | +5 | 0 | 10.8% → 11.0% |
| DEV-holdout | 1,592 | 1,594 | +2 | 0 | 10.2% → 10.4% |

The nested-complement bucket now has 5/142 exact and 24 safe-partial
DEV-train graphs, plus 2/135 exact and 25 safe-partial aggregate DEV-holdout
graphs. The local rules additionally move 30 train and 20 holdout graphs from
declined to safe partial; edge precision remains 100%. Both harm-ordered
diffs report zero broken exact graphs and zero safe-to-incorrect transitions.

Verification is green: 3,234 synthetic/unit tests; 189 focused COGS
projection tests, including 14 recursive-complement cases; COGS lint with zero
errors; curated 65/65 twice; GSM8K DEV-train 104 and DEV-holdout 40; ASDiv 44;
SVAMP 30; MAWPS 9; SciBench 6; and FOLIO 0 committed. Every standing
non-COGS snapshot diff is neutral. No COGS TEST or generalization look was
spent.

## Immediate next step

Run the locked Phase C exit audit: confirm nonzero complete-graph
DEV-holdout coverage for nominal PP modifiers, `ccomp`, `xcomp`, alternation,
nested modifiers, and nested complements; confirm 100% projected-edge
precision and neutral standing gates. If all conditions hold, record Phase C
complete and hand off to the protected Phase D aggregate TEST checkpoint.

Do not inspect holdout rows or spend COGS TEST/generalization looks before the
Phase D checkpoint.

## Increment protocol

For every semantic-projection increment:

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
