# Rule generation and human review workbench

**Status:** active project plan  
**Accepted:** 2026-07-25  
**Implementation:** G1 complete; G2 is next

## Current checkpoint

G1 shipped the first complete generate/review/next loop:

- all 93 curated premise rules are listed, with 8 currently G1-realizable and
  exact blockers for the other 85;
- seeded candidates are identical across fresh project loads;
- failed target round trips remain inspectable as `absent`;
- the ordinary analyzer and document matcher supply actual matches, surviving
  facts, collisions, and deficiencies;
- the Designer has a Generate mode, review controls, Generate next, and a
  handoff to the full Reading trace;
- proper names come from `projects/curated/generation.yaml`; and
- reviews append only to `projects/curated/generation/reviews.jsonl`.

The G1 gate is green: 3,417 unit tests pass, curated remains 65/65 at 100%
precision, and curated lint has zero errors. G2 now adds premise explanations
and source navigation without widening the realization boundary.

## Decision

Invert RuleKit's authoring workflow.

Given the rules, categories, and lexicon loaded by a project, the designer
will generate one candidate sentence at a time. A human will decide whether
the rule's premises were justified in accepting that sentence, identify any
defective premise, form a hypothesis about the responsible rule or lexical
data, edit the relevant YAML, and immediately rerun the same sentence.

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
random seed
target rule id
generated sentence
slot bindings
optional branches selected
premise explanations
actual matching rule ids
emitted facts
collisions and deficiencies
human review, if any
```

The sentence and seed make the experiment reproducible. The registry
fingerprint says exactly which pack state produced and evaluated it.

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

Review remains editable. It records the user's current judgment; it is not a
gold label frozen for model training.

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
POST /api/generation/review
POST /api/generation/hypotheses
POST /api/generation/retest
GET  /api/generation/history
```

Candidate requests may identify a rule or request a random target. They may
also provide a seed, locked bindings, optional-branch choices, or a manually
edited sentence.

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

### G2 — Premise inspector and source index — next

Add premise rows, category paths, predicate results, rule specificity, source
file/line links, and editor navigation.

**Exit:** a reviewer can explain every accepted premise without consulting the
raw trace and can open its source declaration directly.

### G3 — Edit and retest

Pin the sentence while editing. Add Save + retest and the compact before/after
behavior diff.

**Exit:** a user can change a pack document, compile it, and see the effect on
the identical sentence without reconstructing the experiment.

### G4 — Trace-backed hypotheses

Add defect-to-hypothesis rules, premise attachment, hypothesis cards and
statuses, and single-slot minimal-pair generation.

**Exit:** an invalid or unclear review produces at least one relevant,
source-linked hypothesis when the selected evidence supports one; unsupported
cases say that no mechanical hypothesis is available.

### G5 — Structured realizers

Add counted, plural, possessed, qualified, participial, optional, and bounded
span realization in small independently tested groups.

**Exit:** the supported-rule count grows without weakening the mechanical
round-trip check or hiding unsupported rules.

### G6 — Exploration status and lexicon probes

Add review-history navigation, never-sampled lexicon entries, selected-word
probing, and least-explored random selection.

**Exit:** the user can deliberately work through untouched rule and lexical
areas without turning history into a training corpus.

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
