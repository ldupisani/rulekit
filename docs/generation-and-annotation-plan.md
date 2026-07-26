# Rule generation and human review workbench

**Status:** active project plan  
**Accepted:** 2026-07-25  
**Implementation:** G1–G6, G5c–G5f, Reading-origin and fact-level review, the
fraction-plural morphology correction, scoped `GroupTotal`, and the first
review-led grammar-boundary reconciliation complete; G5g `age_noun` ownership
profiling is next

## Current checkpoint

G1 shipped the first complete generate/review/next loop, G2 made its
mechanical result directly inspectable, G3 closed the edit/retest loop, and G4
added bounded hypothesis and minimal-pair exploration:

- all 93 curated premise rules are listed, with 23 currently realizable and
  exact blockers for the other 70;
- seeded candidates are identical across fresh project loads;
- failed target round trips remain inspectable as `absent`;
- the ordinary analyzer and document matcher supply actual matches, surviving
  facts, collisions, and deficiencies;
- the Designer has a Generate mode, review controls, Generate next, and a
  handoff to the full Reading trace;
- each non-question sentence in Reading exposes its matched and shadowed
  premise rules, requires an explicit target selection when more than one
  fired, and can open the exact sentence in the same review workbench without
  a realization pass;
- proper names come from `projects/curated/generation.yaml`;
- reviews append only to `projects/curated/generation/reviews.jsonl`;
- loaded projects retain exact source positions for rules, asks, premise
  tokens, predicates, lexicon entries, category definitions/memberships,
  morphology, and numbers without changing the runtime registry;
- candidates report every supported flat token and `where` premise, selected binding,
  type/category reason, category path, consumed units, and target
  specificity; and
- each editable source link opens the existing allowlisted pack editor at the
  exact declaration line;
- the current sentence remains pinned while a pack document is edited;
- Save + retest uses the existing compile-and-rollback save boundary, reloads
  the project, and evaluates that identical sentence without resampling; and
- a seven-row diff compares registry fingerprint, target status and
  specificity, premises, co-firing rules, facts, collisions, and
  deficiencies;
- reviews can carry the declared structured defects, each attached to the
  whole sentence, one exact premise row, or one exact surviving fact;
- every defect choice explains its intended evidence on hover, while facts
  are numbered and indexed emitting rules are source-linked in the candidate;
- fact attachments preserve an immutable type/fields/provenance/source
  snapshot, and distinguish unjustified facts, incorrect fields, and missing
  downstream context;
- hypothesis formation first replays the pinned sentence, then returns only
  deterministic suggestions supported by the selected defect and matcher
  evidence;
- every suggestion shows its observations, implicated premise, existing
  source declarations, note, and human-controlled status, while unsupported
  combinations explicitly report that no mechanical hypothesis is available;
- review corrections preserve the immutable candidate evidence while
  append-only updates can change a hypothesis status;
- a captured candidate review locks its verdict, defects, attachments, notes,
  and hypothesis statuses; subsequent changes go through Review History →
  Edit and therefore append a durable correction; and
- a single-slot minimal pair excludes the original filler, locks every other
  slot binding, preserves normal cross-slot constraints, and shows the two
  sentences and premise tables side by side;
- successful fresh realizations append schema-bounded observations to the
  separate fixed exploration ledger, while Reading promotion and pinned
  retests do not fabricate sampling history;
- rule status distinguishes blocked, untouched, generated-but-unreviewed, and
  reviewed, while reachable lexicon entries distinguish untouched,
  generated-but-unreviewed, and reviewed;
- the current curated frontier contains 23 supported rules and 114 reachable
  lexicon identities; nine live reviews cover seven rules, while exploration
  remains separate from human judgment; and
- random Generate next chooses from the least-generated compatible rule and
  filler frontier with seeded tie-breaking, while an explicit word probe links
  directly to its editable lexicon declaration;
- plural fraction forms are declared separately from their singular lemmas,
  require an explicit word count in both generation and premise matching, and
  retain complete numeric source evidence; and
- leading total constructions retain their exact normalized subject as an
  optional `GroupTotal.scope`, allowing independently reviewed blue/red totals
  over one measure to coexist without changing tail-only or synthesized totals.

The current gate is green: the 3,514-test full repository run passes, the final
scoped boundary file passes 7/7, curated remains deterministic at 65/65 and
100% precision, both GSM8K development diffs are neutral, every standing
cross-corpus gate retains zero wrong answers, and lint has zero errors.
G6 live validation selected untouched `rabbit`, opened its declaration, and
generated matched `Eron gives 18 rabbits to Aven.` for
`arithmetic/transfer-prepositional`. The rule moved from untouched to
generated-but-unreviewed, both sampled lexicon identities were counted, the
browser console remained clean, and the temporary probe event was removed
without recording a human review.
G5c live validation generated matched
`Bira has double Cato's plum.` for
`arithmetic/times-as-many-possessive-standard`, reported generator
`g6-g5c`, and linked the proper-name fixture, contraction, possessive
declaration, noun declaration, and rule token. The probe event was removed
without recording a review or altering concurrent user-authored ledger rows,
and the browser console remained clean.
G5d live validation selected core-owned `them` and generated matched
`70 of them are blue.` for `arithmetic/partition-attribute`. The Designer
reported generator `g6-g5d`, linked the exact pronoun declaration, preserved
the rule's unresolved-context deficiencies, and produced no browser
diagnostics. The probe event was removed without recording a review or
altering user-authored ledger rows.
G5e live validation selected core-owned `it` and generated matched
`Eron has half of it.` for `arithmetic/fraction-of-pronoun`. The Designer
reported generator `g6-g5e`, displayed the lexicon declaration, exact
`it ∈ pool_pronoun` membership and ancestry, and preserved the unresolved
reference deficiency. The probe event was removed without recording a review
or altering user-authored ledger rows; the browser console remained clean.
The fraction correction live validation generated matched
`Cato received nine fifths of it.` for the same rule, reported generator
`g6-g5e-fractions`, explained the explicit count and singular `fifth` lemma,
and linked the count, fraction value, and fraction-plural declarations. Its
temporary exploration event was removed without changing human review data,
and the browser console remained clean.
G5f live validation generated matched
`Together they bought 9 books.` for
`arithmetic/group-total-leading-marker`, reported generator `g6-g5f`,
displayed the exact `together → aggregate` path with rule-token and lexicon
sources, and emitted `GroupTotal`. The probe left no review or browser
diagnostic, and its temporary exploration events were removed without
altering user-authored rows.
Fact-level live validation then attached `missing_fact_context` to the
numbered `GroupTotal`, preserved its exact source-linked snapshot, and formed
the advisory hypothesis that an identity, qualifier, role, time, or other
downstream discriminator may be absent. No review was recorded and the
temporary generation event was removed.
The resulting scoped-`GroupTotal` increment now preserves that discriminator:
the reviewed `Total blue has 40 birds.` shape emits `scope = blue`; distinct
blue/red totals coexist, same-scope disagreement still conflicts, and
unscoped producers remain unchanged. The two leading rules are anchored to
the sentence start so a trailing aggregate marker cannot manufacture a scope.
Live validation showed the scope in both the surviving-fact card and its
defect-attachment option. This creates the evidence needed by a future
comparison consumer; it does not add or guess that comparison itself.

## Decision

Invert RuleKit's authoring workflow.

Given the rules, categories, and lexicon loaded by a project, the designer
will generate one candidate sentence at a time. A human will decide whether
the rule's premises were justified in accepting that sentence, identify any
defective premise or emitted fact, form a hypothesis about the responsible
rule or lexical data, edit the relevant YAML, and immediately rerun the same
sentence.

This is an interactive rule-debugging and grammar-exploration tool. It is not
a dataset-fabrication campaign, a training loop, or a probabilistic language
generator.

The target workflow is:

```text
select or randomly choose a rule
        ↓
randomly realize one sentence from its premises
        ↓
show why each premise passed
        ↓
human: valid / invalid / unclear
        ↓
attach defects to the suspicious premises
        ↓
form trace-backed hypotheses
        ↓
open the implicated YAML in the designer
        ↓
edit, save, compile, and rerun the same sentence
        ↓
compare before and after
        ↓
generate the next sentence
```

## Product objective

Make rule and lexicon authoring fast enough to feel exploratory:

- generate a sentence with one action;
- understand the rule's acceptance without reading a raw trace;
- identify the exact rule token, category membership, or lexicon entry that
  admitted a word;
- alter the source YAML without leaving the experiment;
- retest the same sentence immediately;
- see whether the intended behavior changed and whether another rule took
  over; and
- continue with a new random specimen.

The human review answers one question:

> Is this sentence a legitimate example of the language that this rule's
> premises claim to recognize?

RuleKit's round trip can establish that a rule matched. Only the human can
establish that the match was linguistically and semantically justified.

## Non-goals

The first implementation will not:

- train a model from annotations;
- optimize a probabilistic generator;
- fabricate or seal a benchmark corpus;
- build train/development/test partitions;
- infer rule changes from aggregate labels;
- mutate rules or lexicon entries automatically;
- attempt exhaustive Cartesian coverage of every word in every slot;
- generate multi-sentence reasoning problems;
- generate premises that make every ask consumer answerable; or
- claim that parser acceptance proves natural-language validity.

The existing semantic-projection campaign remains parked and is independent
of this work.

## The unit of work

The workbench handles one `GenerationCandidate` at a time.

A candidate contains:

```text
candidate id
project name
registry fingerprint
generator version
origin: generated or reading
random seed
target rule id
candidate sentence
slot bindings
optional branches selected
premise explanations
actual matching rule ids
emitted facts
collisions and deficiencies
human review, if any
```

The sentence, seed, and origin make the experiment reproducible. Generated
candidates use their sampling seed. Reading-origin candidates preserve the
user's exact sentence and derive a stable identity seed without sampling or
rewriting it. The registry fingerprint says exactly which pack state
evaluated it.

A candidate is not a corpus row. It is a transient experiment that may be
recorded in the project's lightweight review history.

## What “valid” means

The UI keeps two judgments separate.

### Mechanical result

The generator reports what RuleKit did:

- the intended rule matched;
- another rule shadowed it;
- no rule matched;
- additional rules also matched;
- facts were emitted;
- a collision occurred; or
- the reading retained deficiencies.

This result is computed automatically by the existing reader.

### Human result

The reviewer chooses:

- **Valid** — the sentence is a legitimate example of the target rule;
- **Invalid** — one or more premises admitted a sentence they should not
  admit; or
- **Unclear** — the sentence or rule boundary needs further exploration.

The human result is the signal that drives investigation. Mechanical success
does not imply human validity.

## Generation architecture

Generation is authoring tooling outside the runtime kernel:

```text
src/rulekit/generation/
    candidate.py       candidate and review records
    domains.py         possible fillers for a match token
    realize.py         raw-text realization
    sample.py          deterministic random selection and constraint solving
    explain.py         premise explanations and source references
    hypotheses.py      trace-backed debugging suggestions
```

The dependency is one-way:

```text
generation tooling → existing RuleKit kernel
existing RuleKit kernel ↛ generation tooling
```

The generator may call tokenization, analysis, matching, fact admission, and
tracing as its validation oracle. The ordinary `solve()` path and benchmark
harnesses must not import generation code or human annotations.

### Sampling a rule

The user may:

- select a particular rule;
- choose a pack and select a random rule within it;
- choose a random rule from the whole project; or
- ask for the next rule with little or no review history.

Rules outside the generator's currently supported realization subset remain
visible and carry a precise blocker. They are never silently removed from the
rule list.

### Filling premises

For each match token, the generator constructs a domain:

- a literal supplies its declared surface form;
- a typed slot draws from compatible registry entries or structured values;
- a category-gated slot draws from the category and its descendants;
- numeric slots draw from small safe structural values;
- open proper-name slots use project generation fixtures when the runtime
  lexicon intentionally does not enumerate names; and
- `where` predicates constrain combinations of slot bindings.

All word-specific candidates come from project or pack data. Python may
implement generic realization for a slot type, but it may not contain a
hidden English word list.

Random choice is seeded. The user can reroll the whole sentence or one slot
while locking the remaining bindings.

### Realizing raw text

Parser rules match post-condensation `Unit` objects rather than raw words.
Generation therefore needs generic inverse realizers.

The first realization subset covers:

- literals and punctuation;
- names and proper names;
- singular nouns;
- simple verbs;
- adjectives;
- prepositions;
- plain words;
- numbers, fractions, multipliers, and percents; and
- simple category-gated forms of those types.

Later realizers cover:

- counted nouns;
- plurals and bare plurals;
- possessives;
- qualified and compound nouns;
- participles and other explicitly represented morphology;
- optional groups;
- dates, tuples, and formulas; and
- bounded span constructions.

Morphology must use attested registry relationships—plural declarations,
surface entries, and verb lemmas—rather than guessing unseen English forms.

### Round-trip check

Every generated sentence is sent through the ordinary reader. The workbench
records:

- whether the target rule produced a match;
- the slots it actually bound;
- whether computed specificity shadowed it;
- every co-firing rule;
- the surviving facts after store adjudication;
- agreement or disagreement collisions; and
- reading gaps or unmet obligations.

A failed round trip remains inspectable as a generator or rule-boundary
problem. It is not presented as proof that the sentence itself is invalid.

## Premise inspector

The premise inspector is the central product surface. It translates a match
trace into a compact table:

| Premise | Binding | Why it passed | Source |
| --- | --- | --- | --- |
| `type: name` | `Mira` | name-sensed generated fixture | generation config |
| `lit: has` | `has` | literal matched | rule YAML |
| `type: number` | `4` | numeric count unit | structural value |
| `cat: pet` | `lizards` | `lizard → pet → animal → noun` | categories YAML |
| `distinct: [who, std]` | pass | different bound identities | rule YAML |

The inspector must show:

- required and optional match tokens in sentence order;
- selected and omitted optional branches;
- slot type;
- category gate and the complete membership/ancestor path;
- relevant morphology or lexicon sense;
- every `where` predicate and its result;
- consumed units;
- target-rule specificity;
- shadowing or co-firing rules; and
- emitted facts.

The normal raw decision trace remains available as a deeper view, but a user
should not need it for the ordinary generate-review-edit loop.

## Source index

Rapid editing requires every premise explanation to point back to editable
source.

Pack loading will build a source index for:

```text
rule id                         → file and line
ask id                          → file and line
lexicon surface                → file and line
category definition            → file and line
category membership pair       → file and line
number/morphology declaration  → file and line
```

`ruamel.yaml` already retains source positions during round-trip loading. The
source index is authoring metadata owned by the loaded `Project`; it is not a
new inference input.

Selecting a source reference opens the existing pack editor, scrolls to the
relevant line, and highlights the declaration.

## Human review

The primary control is deliberately small:

```text
Valid    Invalid    Unclear
```

An invalid or unclear review may attach one or more defects:

- premise is too broad;
- premise is too narrow;
- wrong category membership;
- wrong lexical sense;
- wrong morphology or agreement;
- inappropriate optional branch;
- missing cross-slot constraint;
- sentence is ungrammatical;
- sentence is grammatical but semantically implausible;
- intended rule did not fire;
- another rule interfered;
- generator realization defect; or
- other, with a note.

A defect can be attached to the whole sentence or to one premise row. Premise
attachment is preferred because it produces a more precise hypothesis.

After capture, the candidate controls lock. A reviewer can correct the current
judgment through Review History → Edit, which appends a superseding record
rather than rewriting the captured evidence. It is not a gold label frozen
for model training.

## Hypotheses

A hypothesis is an inspectable debugging suggestion. It is never an automatic
change.

Initial hypotheses are deterministic consequences of the mechanical result
and human-selected defects:

| Observation | Possible hypothesis |
| --- | --- |
| invalid sentence and category-gated slot selected | category membership or gate is too broad |
| valid sentence but intended rule did not match | slot type, category gate, literal, or `where` predicate is too narrow |
| same filler selected for two roles | a `distinct` predicate may be missing |
| intended rule was shadowed | specificity or overlap boundary needs inspection |
| optional tail made the sentence invalid | optional group should be removed, narrowed, or split into another rule |
| morphology is wrong | plural/lemma declaration or slot realizer is defective |
| co-firing rule emitted incompatible facts | the two rule premises overlap without a sound specificity boundary |

Each hypothesis card contains:

- a concise claim;
- the observations that motivated it;
- the implicated premise;
- links to the relevant source declarations;
- an **Open in editor** action;
- an optional note from the user; and
- status: `open`, `confirmed`, `rejected`, or `inconclusive`.

The first implementation does not synthesize YAML patches. The user makes the
change intentionally in the editor. A later increment may offer a small draft
patch, but it must remain a preview that requires explicit user action.

### Minimal-pair exploration

For an unclear boundary, the user can lock every slot except one and reroll
that slot. This produces a controlled minimal pair without building a corpus.

Examples:

- keep the rule and syntax, replace only the category member;
- keep every word, include or omit one optional branch;
- keep the nouns, replace only the verb category member; or
- keep the sentence, alter one manually edited surface.

The two premise tables and mechanical results appear side by side.

## Rapid editor loop

The generated sentence remains pinned while the user edits YAML.

After **Save + retest**, the designer:

1. saves through the existing editable-document allowlist;
2. recompiles the project, rolling the file back on failure;
3. re-analyzes the identical pinned sentence;
4. recomputes the premise explanation;
5. shows the old and new registry fingerprints; and
6. presents a compact behavior diff.

The diff includes:

| Surface | Before | After |
| --- | --- | --- |
| target rule | matched, shadowed, or absent | matched, shadowed, or absent |
| premise results | previous pass/fail reasons | new pass/fail reasons |
| co-firing rules | ids | ids |
| emitted facts | normalized facts | normalized facts |
| collisions | count and sources | count and sources |
| deficiencies | list | list |

The user then marks the hypothesis confirmed, rejected, or inconclusive and
chooses whether to generate another sentence.

The workbench may also rerun the small set of specimens reviewed during the
current session for the same rule. This is a local probe set, not a benchmark
or training split.

## Designer interaction

Add a new top-level **Generate** mode beside the existing reading views.

Reading is also an entry point to the same workbench. Each premise sentence
lists the ordinary matcher's premise-rule results. When several rules fired,
the reviewer chooses the intended target explicitly, then opens that exact
sentence in Generate mode. Questions are excluded because this loop reviews
premise rules, not ask rules.

### Generation controls

- project and loaded-pack summary;
- random project rule;
- random rule within a selected pack;
- selected rule;
- generated seed;
- Generate next;
- Reroll sentence;
- Reroll selected slot;
- lock/unlock slot;
- include/omit optional branch;
- select a particular lexicon entry to probe; and
- prefer rules or words with little review history.

### Main candidate panel

- large, editable generated sentence;
- target rule id and description;
- mechanical result badge;
- premise inspector;
- actual rule matches;
- emitted facts and collisions; and
- link to the full reading trace.

### Review and hypothesis panel

- Valid / Invalid / Unclear;
- defect choices;
- premise attachment;
- note;
- hypothesis cards;
- hypothesis status; and
- Next sentence.

### Editor

- existing pack document tree;
- automatic opening and line highlighting from a premise source;
- Save + validate;
- Save + retest pinned sentence; and
- before/after comparison.

The UI should keep the candidate, review, hypotheses, and editor visible
together on a desktop viewport. The common loop must not require navigating
between separate pages.

## API surface

The initial designer API will add:

```text
GET  /api/generation/rules
POST /api/generation/candidate
POST /api/generation/from-reading
POST /api/generation/review
POST /api/generation/hypotheses
POST /api/generation/retest
GET  /api/generation/history
```

Candidate requests may identify a rule or request a random target. A
Reading-origin request supplies only the exact sentence and explicitly chosen
matched rule; the server derives its stable seed and replays it through the
ordinary reader.

The server retains the currently pinned candidate and before-state only as UI
session state. Durable reviews are written through one fixed project-local
path; the API never accepts an arbitrary output path.

Generation uses a lock separate from the benchmark impact lock. Saving still
uses the existing compile-and-rollback behavior.

## Lightweight review history

Reviews are a debugging log, not a dataset.

Use an append-only JSON Lines file at a fixed project-owned location, with
records containing:

```text
candidate id and sentence
origin: generated or reading
target rule
seed and slot bindings
registry fingerprint
human verdict
defects and attached premises
note
hypotheses and their statuses
retest fingerprint and compact behavior diff
timestamp
```

The designer may archive or clear history through an explicit operation.
Nothing reads this file during ordinary parsing, solving, or benchmarking.

When a prior review is opened after the project changes, the UI reruns its
sentence and displays the new behavior. It does not need a corpus-style stale
label or migration protocol.

## Exploration status

A compact status view helps users choose where to explore:

- never generated;
- generated but not reviewed;
- at least one valid review;
- at least one invalid review;
- unresolved unclear reviews;
- open hypotheses;
- rules the generator cannot yet realize; and
- lexicon entries never sampled.

These are navigation aids, not quality scores. A rule with one valid specimen
is not proven universally correct.

The long-term ideal is that:

- every active premise rule can generate at least one plausible sentence;
- every relevant lexicon entry can be sampled through a compatible slot; and
- every intentional exclusion is visible with a reason.

This is an exploration target, not an exhaustive proof obligation.

## Delivery increments

### G1 — Thin designer vertical slice — complete

Implement the smallest complete loop in `projects/curated`:

1. select or randomly choose a supported premise rule;
2. generate one sentence from literals and simple slots;
3. run it through the existing reader;
4. show target match, actual matches, and emitted facts;
5. accept Valid / Invalid / Unclear with a note; and
6. generate the next sentence.

Supported G1 slot families:

- literal;
- name/proper-name fixture;
- noun and common noun;
- verb and nonstate verb without special morphology;
- adjective;
- preposition;
- word;
- number, fraction, multiplier, and percent; and
- category gates over those types.

G1 may support the simple `distinct` and `same_lemma` predicates. Rules with
span capture, compound unit types, participial constraints, nested optionals,
or unsupported predicates remain listed with blockers.

**Exit:** a user can complete the one-sentence generate/review/next loop in the
designer, and the same seed produces the same candidate in a fresh process.

### G2 — Premise inspector and source index — complete

Add premise rows, category paths, predicate results, rule specificity, source
file/line links, and editor navigation.

**Exit:** a reviewer can explain every accepted premise without consulting the
raw trace and can open its source declaration directly.

### G3 — Edit and retest — complete

Pin the sentence while editing. Add Save + retest and the compact before/after
behavior diff.

**Exit:** a user can change a pack document, compile it, and see the effect on
the identical sentence without reconstructing the experiment.

### G4 — Trace-backed hypotheses — complete

Add defect-to-hypothesis rules, premise attachment, hypothesis cards and
statuses, and single-slot minimal-pair generation.

**Exit:** an invalid or unclear review produces at least one relevant,
source-linked hypothesis when the selected evidence supports one; unsupported
cases say that no mechanical hypothesis is available.

### Reading-origin review entry — complete

Expose the ordinary matcher's deduplicated premise-rule results beside each
non-question Reading sentence. Require explicit target selection, promote the
unchanged sentence into `GenerationCandidate`, retain `reading` provenance,
and reuse premise inspection, defects, hypotheses, pinned retest, and the
append-only review ledger.

**Exit:** a user can read a sentence, choose one of its actual premise-rule
matches, and complete the same human-review loop without asking the generator
to fabricate or alter the text.

### G5 — Structured realizers — in progress

Add counted, plural, possessed, qualified, participial, optional, and bounded
span realization in small independently tested groups.

**Exit:** the supported-rule count grows without weakening the mechanical
round-trip check or hiding unsupported rules.

#### G5a — declared plural slots — complete

The 2026-07-25 blocker profile found:

| Candidate family | Blocker occurrences | Rules unlocked alone |
| --- | ---: | ---: |
| optional group | 51 | 6 superficially |
| counted slot | 30 | 5 |
| plural slot | 16 | 3 |
| possessed slot | 2 | 1 |
| bounded span | 0 | 0 |
| explicit participial morphology | 0 | 0 |

The six superficially optional-only rules all contain an include branch with
an unsupported pronoun slot. Treating them as supported by always omitting
that branch would hide an unavailable choice, so optional realization is not
the smallest complete increment. Counted slots require project-backed
number–noun composition and agreement. Declared plurals require only the
existing singular-to-plural registry mapping.

G5a therefore adds exactly this boundary:

- realize `type: plural` from single-token plural surfaces explicitly declared
  by loaded lexicon entries;
- retain the singular lemma as filler identity so `distinct` and
  `same_lemma` keep their current meaning;
- do not invent productive plurals or accept an undeclared surface;
- do not widen noun, counted, possessed, qualified, pronoun, optional, or span
  realization; and
- expect the curated supported count to move from 8 to 11 by unlocking only
  `arithmetic/partition-attribute-of-noun`,
  `arithmetic/partition-membership-of-noun`, and
  `arithmetic/ratio-split-of-to`.

**G5a exit:** the three preregistered rules become honestly selectable,
same-seed plural candidates are identical across fresh project loads, their
plural premise rows link to the declaration and morphology source, and every
standing runtime gate remains neutral.

**G5a result:** met exactly. The supported count is 11/93; no fourth rule was
enabled, `generator_version` is `g5a`, counted and span fixtures remain
blocked, plain noun domains remain singular, and plural identities obey
`distinct`.

#### G5b — declared counted composition — complete

The five rules whose only remaining blocker is `type: counted` are:

- `arithmetic/group-total-leading`;
- `arithmetic/group-total-of`;
- `arithmetic/stated-age`;
- `arithmetic/transfer-ditransitive`; and
- `arithmetic/transfer-prepositional`.

Their other literals, slots, categories, and `distinct` predicates already
have complete current domains. G5b therefore adds one composition contract:

- the count domain is exactly the non-negative integer values already exposed
  by the loaded registry's `numbers` declarations, using the existing
  canonical digit surface; scales, fractions, multipliers, currency, and
  undeclared values are excluded;
- the noun domain is exactly single-token singular entries with an explicit
  single-token plural surface in the loaded registry;
- count `1` selects the declared singular surface; every other admitted count,
  including `0`, selects the declared plural surface;
- filler identity is the singular noun lemma, so cross-slot `distinct` and
  `same_lemma` compare what is counted rather than the number or inflected
  surface;
- premise evidence links the rule token, number declaration, singular lexicon
  entry, and—only when the plural surface is selected—the explicit plural
  morphology declaration;
- the realizer inserts no article, does not inflect a verb, does not infer
  productive noun morphology, and does not repair or conceal a rule premise
  whose other slots admit an ungrammatical combination;
- a project with no admitted count or no declared noun pair reports an empty
  counted domain and keeps the rule blocked; constraint exhaustion remains an
  explicit generation error with no fallback surface; and
- the expected curated boundary is exactly 11 → 16 supported rules, unlocking
  only the five ids above. Counted support must not enable any rule that still
  carries an optional, pronoun, category-root, predicate, future-modal, or
  other independent blocker.

**G5b exit:** the five preregistered rules become honestly selectable,
same-seed candidates are identical across fresh project loads, `1` and
non-`1` counts round-trip with exact declared agreement and source evidence,
the filler identity is the singular noun lemma, no sixth rule is unlocked,
and all standing runtime gates remain neutral.

**G5b result:** met exactly. The supported count is 16/93, only the five
preregistered rules were unlocked, `generator_version` is `g5b`, zero and
non-one values select declared plural surfaces while one selects the singular,
counted identities obey `distinct`, missing plural declarations leave the
domain blocked, and every standing runtime gate remains green.

### G6 — Exploration status and lexicon probes — complete

The folded review ledger currently contains one live generated-origin review
covering one rule. It can answer what a human reviewed, but it cannot answer
what the Designer merely generated: candidates that were not reviewed were
session-only through G5b. Treating absence from `reviews.jsonl` as "never
sampled" would therefore invent history.

G6 adds a second, fixed-path Designer ledger at
`projects/<project>/generation/exploration.jsonl`. A row is appended only after
a fresh realization succeeds through Generate next or a single-slot minimal
pair. Reading promotion and pinned retest do not append because neither samples
a new realization. Each schema-bounded row records the candidate id, target
rule, seed, registry fingerprint, and the lexicon-backed filler identities,
surfaces, slots, and declaration sources actually used. It contains no verdict,
defect, hypothesis, benchmark result, or free text. Human reviews remain in
their existing ledger and retain their existing meaning.

Exploration status is a read-time fold over the current project, all
exploration rows, and the live folded reviews:

- every premise rule reports `blocked`, `never_generated`,
  `generated_unreviewed`, or `reviewed`, plus generated count, reviewed count,
  verdict counts, last-generated time, last-reviewed time, current
  availability/blockers, and its source declaration;
- the filler universe is exactly the lexicon identities reachable through at
  least one slot of a currently supported premise rule. Fixture names,
  literals, numbers, fractions, multipliers, and other non-lexicon surfaces do
  not masquerade as lexicon coverage;
- every reachable filler reports `never_generated`, `generated_unreviewed`, or
  `reviewed`, its generated/reviewed counts, last timestamps, declared source,
  admitted surfaces, and compatible rule/slot placements;
- a live Reading-origin or pre-G6 review can make its rule `reviewed` even
  without a matching exploration event. Filler review status is asserted only
  when the reviewed candidate has a recorded exploration event, because older
  review rows do not preserve normalized filler identities; and
- review corrections and tombstones affect reviewed status through the
  existing live-review fold. Exploration events themselves are observations,
  not judgments, and are never rewritten into review records.

Generate next uses the supplied seed against the current folded status. An
explicit rule and filler must be compatible. If the rule is omitted, choose
among compatible supported rules with the smallest generated count; ties are
sorted by rule id and selected by the seeded RNG. If the filler is omitted,
choose among lexicon identities admitted by the chosen rule with the smallest
generated count; ties are sorted by identity, token index, and slot and selected
by the same seeded RNG. If an identity admits multiple surfaces at that
placement, choose from the sorted surfaces with the seeded RNG. A supported
rule with no lexicon-backed slot still generates normally. The ordinary
realizer, constraints, and round-trip matcher remain the final authority and
fail without fallback if the selected probe cannot realize.

The Designer exposes the rule and reachable-lexicon status totals, orders
untouched filler choices first, links the selected lexicon declaration through
the existing source index, and shows the exact probe chosen for each new
candidate. Status is navigational metadata only: the runtime registry, parser,
matcher, fact store, benchmark, retest comparison, and hypothesis derivation
never import or consult the exploration ledger.

**G6 exit:** fresh and reviewed coverage are visibly distinct, an untouched
reachable lexicon entry can be selected and generated through a compatible
rule, seeded least-explored choices replay against identical ledger state,
Reading/retest actions do not fabricate sampling history, source links remain
editable-document bounded, and every standing runtime gate remains neutral.

**G6 result:** met exactly. The initial curated fold reports 77 blocked rules,
15 untouched supported rules, one reviewed rule with zero fabricated
generation events, 95 reachable lexicon identities, and no fabricated filler
reviews. Fresh candidates and minimal pairs append observations; Reading
promotion and pinned retest do not. Explicit compatible probes, incompatible
probe failures, least-explored replay, source navigation, review joining,
correction/tombstone folding, schema/path bounds, and runtime neutrality are
covered by focused and full gates. `generator_version` is `g6`.

The next increment returns to the still-open structured-realizer work as G5c.
Before implementation, profile and preregister the smallest complete remaining
coverage class. The current blocker frontier is led by optional groups (51
occurrences), comparative category roots (19), `absent` predicates (14),
pronoun slots (6), and possessed slots (2). The single-blocker counts alone do
not authorize a shortcut: the selected class must define its whole domain,
constraints, source evidence, identity, and exact expected support delta.

#### G5c — declared proper-name possessive composition — complete

The smallest complete remaining slot class is `type: possessed`. It occurs in
exactly two curated rules:

- `arithmetic/times-as-many-possessive-standard`, whose only blocker is the
  possessed slot; and
- `arithmetic/affine-times-as-many-possessive-standard`, which remains blocked
  independently by its unsupported comparative `delta` category.

The ordinary matcher defines `possessed` structurally as a noun unit carrying
the `owner` feature produced by the existing `OWNER 's NOUN` condensation.
G5c adds exactly one bounded composition contract:

- the owner domain is the project generation fixture's declared, single-token
  proper names;
- the head domain is a loaded, single-token canonical lexicon entry whose sole
  declared sense is `noun`. An explicit single-token plural declaration adds
  that plural surface; invariant plurals such as `fish` remain one surface;
- realization is exactly `OWNER's HEAD`, and is admitted only when the loaded
  contraction table preserves the `'s` clitic and the lexicon declares its
  possessive sense. It adds no article, nested genitive, common-noun owner,
  pronoun owner, qualified head, productive morphology, or agreement repair;
- filler identity is the singular head lemma, matching the ordinary matcher's
  default value and `distinct`/`same_lemma` behavior. The owner is separately
  visible through the matched unit's `owner` feature and must not silently
  replace that identity;
- premise evidence links the rule token, proper-name fixture, contraction
  declaration, possessive lexicon declaration, singular head lexicon
  declaration, and—when the realized head is the declared plural—the
  morphology declaration;
- a missing fixture owner or admitted noun head leaves the domain empty and
  the rule blocked. Constraint exhaustion remains an explicit generation
  error with no fallback; and
- the curated boundary is exactly 16 → 17 supported premise rules, unlocking
  only `arithmetic/times-as-many-possessive-standard`. Its affine sibling and
  every optional, pronoun, comparative, predicate, qualified, and span class
  remain blocked.

The current curated fixture has six owners and 28 admitted unambiguous noun
lemmas, yielding 54 distinct declared head surfaces and 324 possible
possessive surfaces before rule-level cross-slot constraints. This profile is
evidence for the boundary, not vocabulary embedded in Python.

**G5c exit:** the one preregistered rule becomes honestly selectable;
singular, ordinary plural, and invariant-plural heads round-trip through the
existing possessive condensation with correct owner/head evidence; same-seed
candidates replay across fresh project loads; selected filler identity remains
the noun lemma; no second rule unlocks; exploration metadata records the head
lexicon identity without treating fixture names as lexicon coverage; and all
standing runtime gates remain neutral. The cumulative generator version is
`g6-g5c`.

**G5c result:** met exactly. The supported count is 17/93 and only
`arithmetic/times-as-many-possessive-standard` was unlocked. The comparative
`affine-times-as-many-possessive-standard` sibling remains blocked solely on
its unsupported `delta` category. The curated domain contains six fixture
owners, 28 unambiguous noun lemmas, 54 declared head surfaces, and 324
owner/head surfaces before cross-slot constraints. Missing contraction or
possessive declarations leave the slot blocked; singular, declared plural,
and invariant-plural heads preserve noun-lemma identity; exploration records
the noun rather than the fixture owner; source evidence is complete; and all
standing gates remain green.

#### G5d — declared generic pronoun realization — complete

The post-G5c frontier is 17 supported and 76 blocked. It includes 51
optional-group blockers, 19 unsupported comparative-category roots, 14
unsupported `absent` predicates, and 6 direct `type: pronoun` blockers.
Four partition rules have no independent blocker. Their ordinary object-case
surface `them` was previously stored in `difg-mined`, even though generic
pronouns are core English. That is a data-location defect, not a reason for
Python vocabulary or a hidden generator preference.

G5d therefore adds one complete declared-domain contract:

- every single-token lexicon entry whose declarations include sense `pronoun`
  is a direct `type: pronoun` filler; identity is its exact case-folded
  surface;
- all pronoun-only entries currently stored in `difg-mined` move unchanged to
  `core-english`. Projects that already load both packs retain the same
  declarations, while a core-only project gains the generic vocabulary in its
  proper home. `them` also moves with its `pool_pronoun` membership;
- realization does not infer or silently filter case, person, number,
  definiteness, reference resolution, or possessive use. The current matcher
  does not express those constraints on `type: pronoun`; if a rule admits an
  unsuitable declared pronoun, the generated specimen must expose that broad
  premise for human review;
- evidence links the exact rule token and pronoun lexicon declaration.
  Category evidence remains separate: `cat: pool_pronoun` is not enabled by
  direct slot support because pronoun-rooted category realization is a
  distinct future boundary;
- an empty declared pronoun domain keeps the rule blocked, and constraint or
  round-trip failure remains explicit with no fallback; and
- the curated boundary is exactly 17 → 21 supported premise rules, unlocking
  only `arithmetic/partition-attribute`,
  `arithmetic/partition-attribute-fraction`,
  `arithmetic/partition-membership`, and
  `arithmetic/partition-membership-fraction`. The two other direct-pronoun
  rules retain independent blockers, and `arithmetic/fraction-of-pronoun`
  remains blocked at its `pool_pronoun` category root.

**G5d exit:** the four preregistered partition rules become honestly
selectable; an explicitly selected `them` specimen round-trips and links to
the core declaration; all declared pronoun surfaces remain available rather
than hidden by generator grammar repair; same-seed candidates replay across
fresh project loads; exploration records the pronoun identity; no fifth rule
unlocks; and all standing runtime gates remain neutral. The cumulative
generator version is `g6-g5d`.

**G5d result:** met exactly. The supported count is 21/93 and only the four
preregistered partition rules were unlocked. All 18 pronoun-only declarations
formerly in `difg-mined` now live in `core-english`; projects loading both
packs retain the same 27-entry compiled pronoun inventory, while the
core-only curated project gains the generic data in its proper home. `them`'s
`pool_pronoun` membership moved with it. Declared surfaces retain exact
identity, source evidence points into the core pack, an empty project
pronoun domain blocks explicitly, same-seed candidates replay, exploration
records the lexicon identity, and every standing gate remains green.

#### G5e — declared pronoun-rooted category realization — complete

The post-G5d frontier is 21 supported and 72 blocked. The smallest apparent
independent category class is `cat: pool_pronoun`, used by
`arithmetic/fraction-of-pronoun` as its sole blocker. Its core declaration has
the measured pool-denoting members `it` and `them`. No other currently
blocked rule reports a pronoun-rooted category.

G5e adds the same generic declared-category rule already used for supported
noun-, verb-, adjective-, and preposition-rooted categories:

- a slot gated by a category whose root sense is `pronoun` draws exactly the
  loaded, single-token lexicon surfaces that both carry the root `pronoun`
  sense and belong to that declared category;
- filler identity is the exact case-folded surface, matching direct pronoun
  identity. No category name, reference target, or inferred grammatical
  feature replaces it;
- evidence links the rule token, lexicon declaration, exact category
  membership, and category ancestry;
- the generator does not infer pool reference or admit other generic
  pronouns. An empty category domain leaves the rule blocked, and
  constraint/round-trip failure remains explicit;
- the current complete occurrence set is one token in one rule:
  `arithmetic/fraction-of-pronoun` slot `ref`, category `pool_pronoun`;
- the curated support delta is exactly 21 → 22, unlocking only that rule; and
- direct pronoun, optional, comparative, predicate, qualified, and span
  boundaries remain unchanged.

**G5e exit:** both declared members `it` and `them` round-trip through the
ordinary matcher, show complete lexical/category evidence, replay across
fresh project loads, and enter exploration under their surface identity; an
invented pronoun subcategory proves the mechanism is generic rather than
hard-coded to `pool_pronoun`; no second rule unlocks; and all standing gates
remain neutral. The cumulative generator version is `g6-g5e`.

**G5e result:** met exactly. The supported count is 22/93 and only
`arithmetic/fraction-of-pronoun` was unlocked. `it` and `them` both
round-trip with surface identity and complete rule-token, lexicon,
category-membership, and ancestry evidence; an invented pronoun subcategory
proves the root mechanism is generic; an empty membership keeps the rule
blocked; direct pronoun availability is unchanged; exploration records the
lexicon identity; and every standing gate remains green.

#### Fraction-plural morphology correction — complete

The reviewed generated sentence `Dena had eighths of plum.` exposed a
language-data boundary rather than a probabilistic generation failure. A
plural fraction surface denotes a fraction part, but it is not a complete
fraction phrase without an explicit count. The singular surface may stand
alone and imply one part.

The correction is declarative and general:

- `rulekit/numbers@1` accepts `fraction_plurals`, mapping each
  count-requiring plural surface to its declared singular fraction lemma;
- compilation requires both surfaces to exist in `fractions` with the same
  value;
- number annotation marks a bare declared plural as requiring a count, and
  the ordinary `type: fraction` gate rejects that incomplete form;
- the existing word-count-plus-fraction merge clears the requirement, so
  `two eighths` remains one valid fraction unit without widening the
  deliberately excluded digit-merge boundary;
- the generator excludes bare plural forms, retains direct singular and
  already-complete fraction surfaces, and composes declared non-negative
  word counts other than one with declared plural forms;
- filler identity is the singular fraction lemma, and premise evidence links
  the rule token, word-count declaration, fraction value, and plural mapping;
  and
- the original review remains append-only evidence. Its exact pinned sentence
  now retests as `absent`; `Dena had two eighths of plum.` matches
  `arithmetic/fraction-of-pool`.

**Correction result:** the support frontier remains 22/93 because this narrows
an invalid filler rather than unlocking a rule. The cumulative generator
version is `g6-g5e-fractions`. All 3,462 unit tests, the 65/65 curated suite,
and curated lint (0 errors, one known overlap warning) are green.

#### G5f — aggregate-rooted category realization — complete

The post-correction frontier was 22 supported and 71 blocked. The smallest
remaining rooted-category class that could independently unlock a rule was
`aggregate`. It occurs four times, always as `cat: aggregate`, over the five
loaded single-token lexicon-sense members `altogether`, `average`, `combined`,
`together`, and `total`. This is a degenerate root category supplied directly
by lexicon senses rather than a separately named category declaration.

G5f admits that root through the existing generic category mechanism:

- the filler domain is exactly the loaded, single-token lexicon entries whose
  senses include `aggregate`; `average` remains visible and no semantic
  suitability filter or silent grammar repair is applied;
- filler identity is the exact case-folded surface and the reason path is
  `surface → aggregate`;
- evidence links the rule token and lexicon declaration. It does not fabricate
  a category definition or category-member source for the degenerate root;
- a project with the root sense known but no single-token aggregate entry
  receives an exact no-project-backed-filler blocker;
- the complete occurrence set is
  `arithmetic/existential-premise-total`,
  `arithmetic/group-total-leading-marker`,
  `arithmetic/group-total-of-age`, and
  `arithmetic/group-total-trailing`; and
- the exact support delta is 22 → 23, unlocking only
  `arithmetic/group-total-leading-marker`. The other three retain,
  respectively, optional-group, missing-`age_noun`, and optional-group
  blockers.

**G5f result:** met exactly. All five surfaces round-trip through the ordinary
matcher with exact identity and source evidence; an invented two-member
aggregate domain proves the mechanism is generic and deterministic across
fresh loads; an empty single-token domain stays blocked; the cumulative
generator version is `g6-g5f`; and all standing gates remain green. The live
Designer specimen was `Together they bought 9 books.`, which matched the
target rule and emitted `GroupTotal`.

#### Scoped `GroupTotal` fact boundary — complete

The fact-level review of `Total blue has 40 birds.` correctly identified that
the rule bound `who = blue` but discarded it from the emitted fact. The
runtime boundary now records an optional exact `scope` and keys group totals by
`(scope, measure)`. Only the two leading rules emit their mechanically bound
subject; existential, tail-only, age, and synthesized totals remain unscoped.
Named consumers filter for unscoped or exact-scope-compatible totals, while an
entity-less ask cannot widen a named group to the whole scene.

Anchoring both leading rules at the sentence start was required by the DEV
gate: without it, a trailing `together` in a longer clause could float into
the leading-marker matcher and record a conjunction as scope. The anchored
version restores a neutral GSM8K DEV-train diff and removes the former overlap
warning. Synthetic tests cover distinct-scope coexistence, same-scope
quarantine, exact rule emission, unchanged unscoped emission, the floating
trailing-marker neighbour, unrelated-consumer isolation, and two named groups
over one measure.

#### Review-led grammar boundaries — complete

The next eight invalid live reviews exposed four shared premise boundaries,
not eight isolated sentence repairs. The correction keeps the append-only
ledger unchanged and expresses each boundary in reusable pack data or schema:

- partition rules use a declared `plural_object_pronoun` collection, copula
  categories, explicit definite articles for noun collections, plural
  membership predicates, and `same_number` agreement for cardinal forms;
- transfer rules use `transfer_out ⊂ lose`, so recipient-bearing `gave`/`sold`
  constructions remain available while consumption, generic loss, dropping,
  and spending cannot manufacture a recipient;
- `arithmetic/stated-age` requires a copula and a counted `age_measure`, with
  generic `year/years` and its age/time memberships owned by `core-english`;
  and
- the generator version is `g6-review-boundaries`, and its explanations show
  counted-category and grammatical-number premises from the same declarations
  the matcher enforces.

Pinned retesting of all nine live reviews now yields `absent` for every invalid
target and `matched` for the one valid target. Synthetic tests cover each
positive surface, reviewed negative, agreement neighbour, emitted fact, and
16-seed generation round trip for every corrected supported rule. The full
gate is neutral: 3,514 tests pass; curated is 65/65; GSM8K DEV train and
holdout remain 104/0 and 40/0 with neutral diffs; ASDiv, SVAMP, MAWPS, SciBench,
and FOLIO retain zero wrong commitments; lint has zero errors.

#### G5g — core-owned `age_noun` domain — profiling

The post-G5f frontier is 23 supported and 70 blocked. The next smallest
complete class is a pack-ownership correction, not a new realizer:
`core-english` declares the generic noun category `age_noun`, but its only
lexicon entry and membership are owned by `difg-mined`. A project such as
curated that loads core language but not the mining pack therefore has no
project-backed filler for this otherwise supported noun-rooted category.

Before relocation, prove the complete declaration, membership, lexicon, and
rule occurrence set. Preregister a 23 → 25 support delta that unlocks only
`arithmetic/group-total-of-age` and
`arithmetic/times-as-old-as-possessive-standard`; the related
`arithmetic/group-total-sum-of-age` must retain its independent optional-group
blocker. Move the generic `age` datum rather than copying it, preserve the
combined inventory and source evidence, and round-trip both newly generated
surface classes through the ordinary matcher.

### G7 — Questions and derived rules, if still useful

Only after premise-rule exploration is mature, assess separate generation
paths for ask rules, synthesizer premise sets, and answer consumers.

This is deferred. It is not required for the single-sentence workbench.

## G1 implementation brief

The first implementation must be a vertical product slice, not a backend
framework with no usable designer surface.

### Backend

- add `rulekit.generation` without imports from the kernel back into it;
- enumerate supported `phase: read` sentence rules;
- build deterministic filler domains from the loaded registry;
- load a small project-local generation fixture file for proper names;
- solve supported slot/category and simple cross-slot constraints;
- realize one sentence;
- call the ordinary analyzer and rule matcher;
- return actual rule results, normalized facts, and blockers; and
- add focused synthetic tests with invented vocabulary.

### Server

- list supported and blocked rules;
- request a selected or seeded-random candidate;
- expose the target and mechanical result;
- accept a lightweight review; and
- keep review output on a fixed allowlisted project path.

### Designer

- add a Generate mode;
- show rule selection, seed, sentence, target/actual match status, facts, and
  the three review controls;
- allow Generate next; and
- keep the existing Reading view available for the generated sentence.

### G1 gates

- full unit suite remains green;
- curated bench and lint are neutral;
- generator determinism holds across fresh project loads;
- no runtime result changes when generation is unused;
- no word-specific generation vocabulary appears in Python;
- unsupported rules are reported, never silently skipped; and
- malformed review requests cannot write outside the fixed review path.

## Locked product decisions

1. Generation is deterministic random exploration, one sentence at a time.
2. Premise pattern rules are the first and primary target.
3. The human judges whether the rule premises licensed a valid sentence.
4. Reviews are lightweight debugging evidence, not training data.
5. Hypotheses are trace-backed suggestions, not learned or automatic edits.
6. The user intentionally edits YAML and explicitly saves it.
7. The pinned sentence is rerun immediately after a change.
8. The normal parser never reads reviews or generation configuration.
9. UI clarity and iteration speed take precedence over exhaustive validation
   machinery.
10. Questions, multi-sentence documents, synth rules, and consumers are
    deferred until the premise-rule workbench proves useful.

## Completion criterion

The active plan succeeds when a non-expert rule author can:

1. open the designer;
2. generate a plausible example for a selected or random rule;
3. understand why the rule accepted it;
4. identify and record a questionable premise;
5. follow a hypothesis to the relevant YAML;
6. make an intentional edit;
7. retest the exact sentence;
8. understand the before/after result; and
9. continue exploring without leaving the workbench.

The ideal of generating plausible examples across every project rule and
lexicon remains the direction of travel. The product is useful before that
ideal is complete, provided every unsupported area is visible and honest.
