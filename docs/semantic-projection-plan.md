# Semantic projection campaign — COGS → compositional meaning

**Status:** Phase D checkpoint 1 failed (2026-07-23), the batch was reverted,
and the repaired Phase B/C DEV baseline is now frozen. One TEST and one
generalization look are spent and ledgered; neither protected slice may be
rerun. The original Phase E is blocked pending sufficient independent PMB OOD
coverage; its inspectable precision repair is complete.

**Decision:** use **COGS** as the first development corpus. Use **FraCaS** later
as an external semantic-inference gate, not as the projection worklist.

**Current position:** the repaired baseline plus two explicitly post-D
DEV-only common-subject campaigns, plus a safe lexical normalization found by
PMB, reaches 1,772 exact / 646 safe partial / 0 incorrect on DEV-train and
1,696 / 656 / 0 on DEV-holdout, at 100%
projected-edge precision and 11.6%/11.1% edge recall. These extensions are not
Phase E and do not substitute DEV evidence for the failed OOD checkpoint.

---

## 1. Objective

Extend the FOLIO work from exact surface facts and query-time projections into a
compositional semantic layer that can represent:

- entities and events as distinct referents;
- predicate membership and definiteness;
- agent, theme, and recipient roles;
- nominal prepositional modifiers;
- active/passive and argument-structure alternations;
- open and controlled clausal complements;
- referent sharing across control constructions; and
- recursively embedded clauses and modifiers.

The end state is not “pass a semantic-parsing benchmark.” It is a reading engine
that can expose a lossless, inspectable semantic graph, use that graph to answer
more complex questions, and decline or ask for clarification when the text does
not determine one graph.

The FOLIO principles remain in force:

1. exact surface facts are evidence, not disposable parser intermediates;
2. semantic projection is an additional typed view, not a replacement fact
   store or a second inference engine;
3. lexical/POS knowledge, ontology knowledge, projected meaning, and derived
   inference remain separate layers;
4. missing structure causes a decline; it never licenses an approximate fact;
5. every projection edge must retain provenance to the reading decisions and
   source spans that bought it.

## 2. Why COGS is the first dataset

[COGS](https://github.com/najoungkim/COGS) is a sentence-to-logical-form
semantic parsing dataset. Its gold form directly names entities, events,
unary predicates, semantic roles, modifiers, and complement relations. That is
the supervision this campaign needs: it lets us evaluate the projection itself
instead of guessing projection quality from a final entailment label.

The official corpus contains:

- 24,155 training examples;
- 3,000 in-distribution development examples;
- 3,000 in-distribution test examples; and
- 21,000 generalization examples, 1,000 for each of 21 disclosed cases.

The generalization cases cover novel lexical/grammatical-role combinations,
modified phrases in new roles, deeper PP and clausal recursion, verb argument
alternations, and verb-class-sensitive roles. These are exactly the places
where a compositional rule system should generalize rather than acquire a
sentence-shaped patch. The source repository is MIT licensed and records a 2022
correction to 50 generalization examples, so the builder must pin a revision
containing that correction.

The design and counts come from the
[COGS paper](https://aclanthology.org/2020.emnlp-main.731/); the upstream split
and case metadata are documented in the
[official repository](https://github.com/najoungkim/COGS).

### What COGS buys

- A gold intermediate representation, not only a final answer.
- Exact semantic-role distinctions such as agent versus theme.
- A public, case-labelled compositional-generalization set.
- Sufficient scale to measure both edge-level precision and complete-graph
  coverage.
- A clear license and a reproducible upstream source.

### What COGS does not buy

- It is generated from a controlled grammar, not ordinary open-domain prose.
- Its logical form is deliberately simplified: it does not cover the full
  generalized-quantifier, temporal, anaphoric, plural, pragmatic, or ambiguity
  space exposed by FOLIO and FraCaS.
- Token-indexed variable names and serialized predicate order are dataset
  conventions, not semantics. Rulekit must compare normalized graphs, not learn
  to print a target string.
- It contains sentences but no user questions. It improves the semantic layer
  underneath question answering; it does not replace the buyer requirement for
  later end-to-end answer work.

These limitations make COGS a strong first projection corpus and a poor sole
claim of general language understanding.

## 3. Why not start with the alternatives

### FraCaS — second, as an inference gate

[FraCaS](https://aclanthology.org/2014.lilt-9.4.pdf) contains 346 diagnostic
problems spanning generalized quantifiers, plurals, anaphora, ellipsis,
adjectives, comparatives, temporal reference, verbs, and attitudes. Each
problem has premises, a question, and a Yes/No/Unknown-style judgement.

That breadth is valuable, but FraCaS does not provide a gold semantic projection
for each sentence. A wrong final verdict cannot tell us whether reading,
projection, inference, or answer consumption failed. We should add FraCaS after
COGS has bought the intermediate graph types, when it can answer the more useful
question: “do these projections support semantic inference beyond FOLIO?”

Before materializing FraCaS, verify the original data licence. Do not adopt the
random 80/20 split in the current Hugging Face mirror: the corpus is a small
diagnostic suite with related problem families, so row-level random splitting
would leak phenomena across the firewall. Preserve original ids and sections
and split by problem family.

### SICK — later, as a surface-transfer gate

[SICK](https://marcobaroni.org/composes/sick.html) has roughly 10,000
sentence pairs and three-way entailment labels. Its caption-derived sentences
are less controlled than COGS and therefore useful for transfer. It still lacks
gold projection graphs, contains systematic generated variations, and is
CC BY-NC-SA. It belongs after COGS and FraCaS, not at the start of this campaign.

## 4. Semantic-layer contract

COGS should not dictate kernel classes verbatim. It should first be normalized
into a small evaluation graph:

| Graph element | Meaning | Example |
|---|---|---|
| entity node | a named or existential referent | `entity:e1` |
| event node | an eventuality anchored to a predicate | `event:give1` |
| type edge | unary class/property membership | `type(e1, girl)` |
| role edge | event argument | `agent(give1, e1)` |
| modifier edge | a relation modifying a nominal | `nmod.in(box1, room1)` |
| complement edge | a relation between events/clauses | `ccomp(hope1, burn1)` |
| identity edge | two roles share one referent | control subject reuse |
| definiteness mark | discourse status asserted by the construction | `definite(e1)` |

The graph is a scoring and presentation interface. Kernel facts may remain more
specialized when that preserves stronger invariants.

Every projected node and edge must carry:

- source sentence and token/span anchors;
- the reading fact(s) and decision(s) that support it;
- epistemic role: observed, knowledge, or derived;
- representation role: exact or structured; and
- completeness state: partial, complete, ambiguous, or declined.

Exact FOLIO-style atoms stay in the store. Structured projections link to them
through provenance. A semantic edge must never silently rewrite or discard its
exact evidence phrase.

## 5. Evaluation contract

### Normalize before scoring

Build a COGS gold adapter that parses the target logical form into the
evaluation graph. It must:

- ignore serialized conjunct order;
- alpha-normalize variable names;
- preserve predicate lemmas, role labels, definiteness, and graph topology;
- preserve token anchors when they are semantically relevant; and
- compare graph structure, not raw target strings.

The adapter is benchmark infrastructure. It must not contain reading logic or
be imported by the runtime parser.

### Harm-ordered measurements

Report at least:

1. **incorrect projected edges** — worst; an asserted role/type/relation not in
   gold;
2. **exact complete graphs** — every required node and edge, no extras;
3. **safe partial graphs** — all asserted edges correct but some gold structure
   missing;
4. **declined graphs** — no unsupported semantic commitment;
5. edge precision/recall by graph-element type; and
6. exact-graph coverage by construction and generalization case.

The shipping bar follows the existing constitution:

- no baseline exact graph may become incorrect;
- no decline or safe partial graph may gain an incorrect edge;
- new capability may add only correct edges;
- a sentence counts as a buyer only when its whole target graph becomes exact,
  unless the increment was explicitly scoped as representation infrastructure;
  and
- representation infrastructure still needs a named imminent buyer and must
  remain outcome-neutral until that buyer lands.

Partial projection is useful in the designer, but it must not be confused with
a complete reading or used to answer a query whose required subgraph is
missing.

## 6. Firewall and corpus layout

Create `projects/cogs/` with a committed builder and gitignored materialized
data. Pin the corrected upstream revision and verify all four official row
counts and file checksums.

Dataset-selection research inspected a sample of upstream `dev.tsv`. Therefore
the official development file is already contaminated and must not be presented
as an untouched holdout. Record it as an inspectable calibration slice.

Use the splits as follows:

| Rulekit slice | Source | Access |
|---|---|---|
| `dev-train` | stable hash partition of official COGS train | fully inspectable; mine and tune |
| `dev-holdout` | complementary partition of official COGS train | aggregate/class diagnostics; no item tuning |
| `calibration` | official COGS dev | inspectable; never described as holdout |
| `test` | official COGS test | aggregate-only, ledgered, one look per checkpoint |
| `generalization` | official COGS gen | aggregate by disclosed case, ledgered, no item inspection |

The train partition must be computed before any campaign mining. Use a stable
salted hash of the complete source sentence, and include a duplicate audit.
Because the in-distribution data deliberately contains many structurally
similar sentences, the OOD generalization split—not the internal hash
holdout—is the principal defense against grammar-template overfit.

Paper/README examples are public task specifications. If an exact published
example appears in `test` or `generalization`, mark it in corpus metadata and
exclude it from the honest aggregate rather than pretending it was unseen.

Never copy COGS sentence strings into unit tests. Synthetic tests must use new
names, nouns, verbs, and arrangements.

## 7. Campaign phases

### Phase A — corpus, adapter, and honest baseline — DONE (2026-07-23)

1. Add the reproducible COGS builder and project configuration.
2. Parse every gold logical form into the normalized evaluation graph.
3. Add a projection bench and snapshot/diff support without changing runtime
   reading.
4. Baseline current exact and structured facts against COGS.
5. Produce blocker taxonomies by missing graph element and construction:
   entity, event, type, role, modifier, complement, identity, definiteness.
6. Lock numeric coverage objectives only after the baseline exists. Do not
   invent a percentage target before seeing the denominator and current
   precision.

**Exit:** reproducible counts/checksums, two identical fresh-process baselines,
zero evaluator self-test failures, and a DEV-only ranked worklist.

The exit gate is met. The official post-correction COGS revision is pinned at
`165a7b669eade971fa47bf568a2e51925360fed8`; all four source files are
SHA-256 checked. Materialization produces 12,056 DEV-train rows, 12,099
DEV-holdout rows, 3,000 calibration rows, 3,000 TEST rows, and 20,984 scored
generalization rows after excluding 16 published/exposed examples.

The untouched runtime baseline is:

| split | exact | safe partial | declined | incorrect | edge precision | edge recall |
|---|---:|---:|---:|---:|---:|---:|
| DEV-train | 247 | 41 | 11,768 | 0 | 100% | 1.5% |
| DEV-holdout | 213 | 47 | 11,839 | 0 | 100% | 1.3% |

The exact graphs come solely from the pre-existing FOLIO
`VerbalRelation` fact and a fail-closed evaluation projection. Flat `Atom`
phrase keys are never split. An unlicensed surface verb lemma or ambiguous
nominal lemma produces a safe partial graph, not an incorrect edge.

Ranked DEV-train structural worklist:

| construction | items | exact | safe partial |
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

Phase B objectives are now locked:

- keep projected-edge precision at 100% and incorrect graphs at zero on both
  DEV partitions;
- exceed 247/213 exact graphs and 1.5%/1.3% edge recall;
- establish nonzero exact coverage on both partitions for transitive,
  ditransitive, intransitive-agent, and intransitive-theme graphs; and
- credit no construction merely for adding COGS vocabulary.

Snapshots are gitignored at
`projects/cogs/snapshots/phase-a-dev-{train,holdout}.json`.

### Phase B — first-class events and roles

Work breadth-first by construction class, one class per increment:

1. named and indefinite entity projection;
2. intransitive events with verb-class-sensitive agent/theme roles;
3. active transitive events;
4. passive transitive events, with optional expressed agent;
5. ditransitives and recipient roles; and
6. definiteness without inventing uniqueness or world identity.

Prefer a small set of general graph facts over verb-specific fact classes.
Verb-class membership belongs in YAML packs. Python may consume a category but
must never enumerate the verbs in it.

**Exit:** each served class has complete buyers in both DEV partitions, no new
incorrect edge anywhere, and neutral existing regression/cross-corpus gates.

### Phase C — compositional attachment and sharing

Add the structures that require more than one flat predicate:

1. nominal PP modifiers and attachment provenance;
2. `ccomp` event/clause embedding;
3. `xcomp` control with explicit referent sharing;
4. active/passive and dative alternations through one role graph;
5. nested PP modifiers; and
6. nested sentential complements.

Depth must be handled by the document/rule machinery, not by adding separate
rules for depths 2, 3, and 4. A recursion increment is credited only if one
rule family handles multiple synthetic depths and the normal document-round
termination gate remains deterministic.

**Exit:** nonzero complete-graph coverage for every targeted composition class
on DEV holdout, with no graph-precision regression.

### Phase D — COGS checkpoint

When Phases B and C meet their locked DEV objectives:

1. spend one aggregate in-distribution TEST look;
2. if graph precision holds, spend one generalization look;
3. report the generalization aggregate and every disclosed case, separating
   lexical from structural cases;
4. do not inspect failed rows;
5. revert the checkpoint batch if committed graph precision drops; and
6. use only class-level aggregate results to choose the next DEV worklist.

#### Post-checkpoint restart amendment — 2026-07-23

Checkpoint 1 has been spent. TEST retained 100% precision, but the protected
generalization aggregate exposed 58 incorrect graphs, all localized to the
proper-object ditransitive cases `prim_to_obj_proper` and
`subj_to_obj_proper`. No protected row was inspected, and the complete batch
was reverted as required.

The restart therefore treats proper-object role transfer as a proved unsafe
boundary:

- recipient projection is licensed only by the explicit
  `Name V a N to Name` construction-specific category;
- direct proper objects remain themes;
- double-object and named-theme-plus-`to` surfaces remain declined; and
- the former double-object half of Phase C target 4 is retired rather than
  credited as complete.

This is an explicit checkpoint-driven scope correction, not a claim that the
original double-object target passed. Phase C restart readiness requires
nonzero complete holdout coverage for the remaining safe composition classes,
active/passive role invariance, the explicit-to recipient graph, 100%
projected-edge precision, and neutral standing gates. Both protected ledgers
contain one row; no second checkpoint look is authorized.

The completed disposition freezes the rebuilt state as a safe DEV baseline,
not as a second checkpoint pass. A runtime diff against failed batch
`e657fc9` confirms that the repaired candidate removes the double-object rule
and narrows its reusable verb category to the explicit-to construction while
leaving the remaining semantic rules and kernel machinery unchanged. Further
coverage work requires a new DEV-only campaign with a new locked objective.

Coverage on the official generalization split is the evidence that the
machinery composes. High in-distribution accuracy alone is not a campaign
success.

### Phase E — reconnect projection to questions and inference

**Gate status: BLOCKED — not started.** The prerequisite below was not met by
checkpoint 1, and the spent protected slices cannot be used again. Entering
this phase requires a separately preregistered, independent OOD projection
gate that demonstrates nonzero transfer without a precision failure.

The selected gate and frozen acceptance contract are recorded in
[`semantic-projection-ood-gate-plan.md`](semantic-projection-ood-gate-plan.md).
PMB 5.1.0 English gold is selected: its release materials licence annotations
under ODC-BY 1.0. Because raw texts retain the terms recorded in accompanying
`.met` files, the completed metadata-only audit freezes a Tatoeba-only subset
under the bundled CC BY 2.0 notice: 9,065 train, 990 development, and 923
protected standard-test documents. The local release and licence files are
hashed. The immutable builder, project schema, and conservative SBN gold
adapter now exist. The untouched-runtime train/development baseline had zero
exact graphs, 24/2 safe partials, and 113/19 incorrect graphs at 46.5%/38.4%
edge precision. The completed safety and coverage campaign froze at 117 train
exact / 531 correct edges / 0 incorrect and passed every inspectable entry
threshold. The single protected standard-test look has now been spent:
1 exact / 0 incorrect / 100% precision across 923 items. Its only exact class
was intransitive Agent, so the protected two-role and
direct-object-versus-recipient condition failed. No protected row, identifier,
sentence, meaning representation, or failure was inspected. The PMB gate
cannot be rerun, and Phase E remains blocked pending a newly preregistered
independent OOD gate.

After COGS demonstrates nonzero OOD transfer:

1. make question consumers request graph-shaped semantic queries rather than
   flattened phrase keys where the buyer needs roles or attachment;
2. extend the designer Semantic field with entity/event nodes, role edges,
   attachment, provenance, and completeness;
3. preserve the current Proof and clarification contracts;
4. add FraCaS as a family-grouped three-way semantic-inference project after
   its licence audit; and
5. use FOLIO and FraCaS as external answer-level gates while COGS remains the
   projection-level gate.

An ambiguous sentence or ask may expose multiple precise candidate graphs and
request confirmation. Clarification is allowed only when every option has a
well-formed projection. It must not disguise a malformed or unsupported parse.

## 8. Increment protocol

Every implementation increment follows this sequence:

1. Snapshot COGS DEV train/holdout and all standing regression corpora.
2. Select one frequent clean blocker class from `dev-train`.
3. State the general construction class and the complete graph it should buy.
4. Implement general machinery and YAML vocabulary/category data.
5. Add synthetic positive, negative-neighbour, ambiguity, and overreach tests.
6. Diff COGS `dev-train`: zero new incorrect edges.
7. Diff COGS `dev-holdout`: zero new incorrect edges and no exact→partial
   regressions.
8. Run curated twice and the standing GSM8K, ASDiv, SVAMP, MAWPS, SciBench,
   and FOLIO DEV gates.
9. Update the campaign ledger with buyers, graph delta, collisions, and dormant
   schema/rule joins.
10. Do not spend TEST/generalization looks until a phase checkpoint.

No increment receives credit merely for:

- recognizing more vocabulary;
- emitting a fact that does not join the gold graph;
- adding a schema with no end-to-end buyer;
- matching a raw COGS logical-form string;
- moving a parser category into the semantic field; or
- answering from a partial graph while a required edge is absent.

## 9. Next implementation step

The original A–E plan is at the Phase D/Phase E boundary: the repaired DEV
baseline is frozen, but Phase E remains blocked by the failed OOD checkpoint.
Do not rerun COGS TEST or generalization and do not describe the post-D
common-subject campaigns as plan phases.

Two valid next directions remain:

1. **Continue DEV coverage outside the original phase sequence:** profile a
   determined common-subject intransitive class, lock agent/theme role
   membership before implementation, and run the normal increment gate.
2. **Unblock original Phase E:** fabricate and seal the fit-for-purpose
   controlled-English corpus specified in
   [`synthetic-semantic-treebank-plan.md`](synthetic-semantic-treebank-plan.md).
   It uses a neutral schema, bundle-level compositional splits, plaintext
   train, separately encrypted aggregate-only development/test, and a CC0
   target. The fabrication context receives no Rulekit code, schemas, outputs,
   benchmark cases, or failures. Import begins only after the external release
   is sealed. The PMB campaign reached 117 train exact / 531 correct edges /
   0 incorrect and passed every inspectable threshold, but its single
   protected look produced only one intransitive-Agent exact graph. Precision
   stayed at 100%, while the protected two-role and
   direct-object-versus-recipient condition failed. The PMB look is spent and
   cannot be rerun or used for tuning.

Do not tune to DEV-holdout items. Do not start by admitting the frequent COGS
unknown words: vocabulary receives credit only as part of a complete
construction buyer.
