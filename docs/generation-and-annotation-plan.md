# Rule generation and human review workbench

**Status:** implemented product contract; ongoing review-led refinement
**Accepted:** 2026-07-25
**Updated:** 2026-08-12
**Implementation:** G1–G7 and G6b are complete. Premise, Reading-origin,
targetless, fact-level, ask-only, answerable-scenario, and deliberate-decline
reviews share the append-only edit/resolve/tombstone lifecycle. Strict and
one-slot lexical-boundary generation, recursive realization, structural
coverage, category/fact/slot filters, source navigation, pinned edit/retest,
and generation-health diagnostics are implemented. G5v remains the name of
the ongoing human review loop; reconciliations are complete through batch 54.
Mining v2 now uses this workbench as its human promotion surface.

Point-in-time counts in the milestone sections below are historical results.
Only “Current checkpoint” and [`HANDOFF.md`](HANDOFF.md) describe the live
frontier.

## Current checkpoint

G1 shipped the first complete generate/review/next loop, G2 made its
mechanical result directly inspectable, G3 closed the edit/retest loop, and G4
added bounded hypothesis and minimal-pair exploration:

- all 125 ordinary curated premise targets are mechanically realizable; five
  fact-free safety interceptors remain active in reading but are deliberately
  excluded from premise generation and review;
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
- every non-question Reading sentence can also open a targetless sentence
  review, including when no premise rule matched; that review can preserve an
  intended interpretation and an optional missing-rule suggestion without
  claiming rule coverage;
- identified Reading premise rules, rule-backed decisions, emitted and
  semantic facts, and recognized ask rules can open their indexed YAML
  declarations directly in the existing editor;
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
- when one authored emit unambiguously explains a generated fact, its
  expression templates and resolved slot bindings are preserved and exposed
  under “How this fact was derived” without changing fact identity;
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
- failed fresh attempts append separately to a fixed failure ledger, so they
  advance exploration without being miscounted as generated specimens;
- rule and reachable-lexicon status distinguish blocked, untouched,
  attempted-but-unrealized, generated-but-unreviewed, and reviewed;
- generation support is deliberately mechanical rather than a human validity
  judgment: if every declared token and predicate has a realizer and a
  project-backed filler, the rule remains explorable even when the generated
  sentence exposes a defective premise;
- a `matched` or `shadowed` target status reports what the ordinary matcher
  accepted, never that the resulting English or emitted fact is correct;
- the current curated frontier contains 130 loaded reading rules, 125 ordinary
  premise-generation targets, five fact-free safety interceptors, and 305
  reachable generated-filler identities; live reviews and continuing
  exploration remain separate from mechanical availability; and
- fact-free safety consumers remain active in the internal matcher but are not
  premise-review targets or actual premise matches in the Designer; a
  surviving guard is shown separately as a safety interception, while a
  redundant guard subsumed by a valid ordinary premise stays hidden; and
- random Generate next chooses from the least-attempted compatible rule and
  filler frontier with seeded tie-breaking, while an explicit word probe links
  directly to its editable lexicon declaration;
- strict exploration can instead target the least-generated rule,
  least-reviewed rule, least-covered structural outcome, a live invalid or
  unclear review, or a seeded random rule within the selected filters;
- structural filters compose conjunctively across grammar phenomena, declared
  categories, slot types, and emitted fact types;
- coverage is atomic rather than a single rule counter: optional branches,
  literal alternatives, and emitted fact type/field shapes have stable
  signatures, and least-covered generation forces the selected optional or
  literal outcome instead of waiting for a random reroll to reach it;
- the exploration health panel reports structural coverage,
  current-fingerprint success/failure rates, and the five most frequent
  terminal generation blockers; failed requests also retain an aggregate of
  their most common deterministic-attempt causes;
- the mode selector separates strict positives from lexical-boundary probes:
  strict generation satisfies every slot requirement, while a boundary probe
  widens exactly one active lexical gate to its declared root sense and keeps
  every other structural constraint intact;
- lexical-boundary candidates retain the exact relaxation in reviews and
  pinned retests, but never count as strict rule or lexicon coverage;
- registry-fingerprint caches avoid rebuilding token domains, rule
  availability, and compatible-probe catalogs on every request, while the
  Designer receives a compact exploration payload; and
- the GSM8K project owns open proper-name generation fixtures, all 120
  ordinary premise targets are selectable, and its three fact-free safety
  interceptors remain outside premise generation and review;
- plural fraction forms are declared separately from their singular lemmas,
  require an explicit word count in both generation and premise matching, and
  retain complete numeric source evidence; and
- leading total constructions retain their exact normalized subject as an
  optional `GroupTotal.scope`, allowing independently reviewed blue/red totals
  over one measure to coexist without changing tail-only or synthesized totals;
  and
- fraction-valued comparisons and changes require a strictly positive
  magnitude, while pool and partition facts retain zero as a meaningful value.

The current gate is green: all 5,358 repository tests pass in four-worker
mode, curated remains deterministic at 71/71 and 100% precision, GSM8K
DEV-train is 108/0 and DEV-holdout is 42/0, every standing answer and
projection gate retains zero wrong or incorrect commitments, and lint has
zero errors with one known warning. The protected aggregate remains recorded
in the handoff and campaign ledgers; this documentation reconciliation spends
no protected look.
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

The same sentence also offers a sentence-meaning review. This targetless path
does not invent a rule id: it records `target_rule: null`, preserves ordinary
Reading evidence, and lets the reviewer describe the intended interpretation
or suggest a premise-rule shape that is missing. Such reviews do not increment
rule or lexicon coverage.

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
- target rule id and description, or an explicit targetless
  sentence-interpretation label;
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
- intended interpretation and optional missing-rule suggestion for a
  targetless Reading review;
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
Reading-origin request supplies the exact sentence and either an explicitly
chosen matched rule or no target. The server derives its stable seed and
replays it through the ordinary reader. A targetless response retains
incidental matches and facts for inspection but does not claim that any rule
was the review subject.

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
review kind: premise or sentence
target rule, or null for a sentence review
seed and slot bindings
registry fingerprint
human verdict
intended interpretation and optional missing-rule suggestion
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

Reading also exposes source controls without requiring promotion into Generate
mode. A matched premise selection, a rule-backed decision, an emitted or
semantic fact, and a recognized ask carry their authoring-only `SourceIndex`
reference when one exists. The control opens only paths already present in the
editable pack-document allowlist and jumps to the indexed line; derived or
kernel-only identifiers without a YAML declaration remain plain text.

### Targetless sentence-interpretation review entry — complete

Expose a separate `Review sentence meaning` action for every non-question
Reading sentence, including sentences with no premise-rule result. Promote the
unchanged text into a targetless, deterministic Reading candidate; retain
ordinary matches, facts, collisions, and deficiencies as inspectable evidence;
and record the review with an intended interpretation and optional missing-rule
suggestion.

The durable review uses `review_kind: sentence` and `target_rule: null`.
Append-only corrections can revise both human text fields. The exploration
fold excludes these rows from per-rule and per-lexicon reviewed counts while
still reporting them in the overall live-review total.

**Exit:** a user can preserve what an unmatched sentence means, or describe
the rule that ought to recognize it, without fabricating an existing premise
match or contaminating rule-coverage status.

The complete gate is green: 4,033 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

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

Failed fresh attempts use the separate fixed path
`projects/<project>/generation/failures.jsonl`. A bounded row records the
selected rule, seed, registry fingerprint, exact selected lexicon probe when
one exists, and the realization error. It does not claim a candidate or
increment generated coverage. Only failures matching the current registry
fingerprint affect selection, so an authored rule or lexicon change makes the
probe eligible for a fresh test while preserving the historical row.

Exploration status is a read-time fold over the current project, all
exploration rows, and the live folded reviews:

- every premise rule reports `blocked`, `never_generated`, `attempted_failed`,
  `generated_unreviewed`, or `reviewed`, plus successful, failed, attempted,
  and reviewed counts, verdict counts, timestamps, current
  availability/blockers, and its source declaration;
- the filler universe is exactly the lexicon identities reachable through at
  least one slot of a currently supported premise rule. Fixture names,
  literals, numbers, fractions, multipliers, and other non-lexicon surfaces do
  not masquerade as lexicon coverage;
- every reachable filler reports `never_generated`, `attempted_failed`,
  `generated_unreviewed`, or `reviewed`, its successful, failed, attempted,
  and reviewed counts, timestamps, declared source, admitted surfaces, and
  compatible rule/slot placements;
- a live Reading-origin or pre-G6 review can make its rule `reviewed` even
  without a matching exploration event. Filler review status is asserted only
  when the reviewed candidate has a recorded exploration event, because older
  review rows do not preserve normalized filler identities; and
- review corrections and tombstones affect reviewed status through the
  existing live-review fold. Exploration events themselves are observations,
  not judgments, and are never rewritten into review records.

Generate next uses the supplied seed against the current folded status. An
explicit rule and filler must be compatible. If the rule is omitted, choose
among compatible supported rules with the smallest attempt count; ties are
sorted by rule id and selected by the seeded RNG. If the filler is omitted,
choose among lexicon identities admitted by the chosen rule with the smallest
attempt count; ties are sorted by identity, token index, and slot and selected
by the same seeded RNG. If an identity admits multiple surfaces at that
placement, choose from the sorted surfaces with the seeded RNG. A supported
rule with no lexicon-backed slot still generates normally. The ordinary
realizer, constraints, and round-trip matcher remain the final authority and
fail without fallback if the selected probe cannot realize; that failure
advances the attempt frontier without fabricating a generation event.

The Designer exposes the rule and reachable-lexicon status totals, orders
untouched filler choices first, links the selected lexicon declaration through
the existing source index, and shows the exact probe chosen for each new
candidate. Status is navigational metadata only: the runtime registry, parser,
matcher, fact store, benchmark, retest comparison, and hypothesis derivation
never import or consult the exploration ledger.

**G6 exit:** fresh and reviewed coverage are visibly distinct, an untouched
reachable lexicon entry can be selected and generated through a compatible
rule, seeded least-explored choices replay against identical ledger state,
failed probes do not starve untouched alternatives, Reading/retest actions do
not fabricate sampling history, source links remain editable-document bounded,
and every standing runtime gate remains neutral.

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
- the generator version is `g6-reviewed-premise-boundaries`, and its explanations show
  counted-category and grammatical-number premises from the same declarations
  the matcher enforces.

Pinned retesting of all nine live reviews now yields `absent` for every invalid
target and `matched` for the one valid target. Synthetic tests cover each
positive surface, reviewed negative, agreement neighbour, emitted fact, and
16-seed generation round trip for every corrected supported rule. The full
gate is neutral: 3,514 tests pass; curated is 65/65; GSM8K DEV train and
holdout remain 104/0 and 40/0 with neutral diffs; ASDiv, SVAMP, MAWPS, SciBench,
and FOLIO retain zero wrong commitments; lint has zero errors.

#### G5g — core-owned age domain and owned-category boundary — complete

The post-G5f frontier was 23 supported and 70 blocked. The smallest
candidate class began as a pack-ownership correction:
`core-english` declares the generic noun category `age_noun`, but its only
lexicon entry and membership are owned by `difg-mined`. A project such as
curated that loads core language but not the mining pack therefore has no
project-backed filler for this otherwise supported noun-rooted category.

Complete occurrence profiling corrected the initial preregistration before it
could become an unsafe implementation contract. There are five `age_noun`
tokens across four rules, not only the two initially named rules. In
particular, `arithmetic/times-as-old-as-both-possessive` contains two age
slots and loses its last filler blocker at the same time. Merely moving the
word would also let the two comparative rules generate and match bare or
plural heads such as `Age is twice age.`, even though both emitted relations
read a possessive owner.

G5g therefore closes the complete structural class:

- generic `age/ages` and its `age_noun`, `dimension_noun`, and `time_measure`
  memberships move from `difg-mined` to `core-english` rather than being
  duplicated;
- a category slot may opt into `possessed: true`, composing the existing
  owned-noun unit structure with an exact noun category. Compilation rejects
  the qualifier on a category not rooted at `noun`;
- any scalar slot may declare `number: singular|plural`, and both matcher and
  generator require that exact project-declared grammatical feature;
- `distinct_owner` requires every named slot to carry a possessive owner and
  requires those owners to differ, without incorrectly comparing the shared
  noun lemma;
- the one-sided and two-sided age comparisons require singular possessed
  `age_noun` slots, copulas, and declared number agreement; the two-sided rule
  additionally refuses self-comparison; and
- generated premise explanations expose the category, owner, singular lemma,
  grammatical number, source declarations, and distinct-owner result.

**G5g result:** the corrected support delta is 23 → 26, unlocking
`arithmetic/group-total-of-age`,
`arithmetic/times-as-old-as-possessive-standard`, and
`arithmetic/times-as-old-as-both-possessive`.
`arithmetic/group-total-sum-of-age` remains blocked by its independent
optional group. Twenty-four seeded realizations of each comparative rule
round-trip through the ordinary matcher; invented `relic` vocabulary proves
the machinery is category-generic rather than age-specific. The cumulative
generator version is `g6-g5g`. All 3,589 repository tests pass; curated stays
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
diffs; ASDiv, SVAMP, MAWPS, SciBench, and FOLIO retain zero wrong commitments;
and lint remains at zero errors with the same two known warnings.

The post-G5g frontier is 26 supported and 67 blocked. The dominant remaining
blockers are unchanged in kind: 51 optional groups, 19 comparative-root
occurrences, and 14 `absent` predicates. Several otherwise-supported
core-declared categories also have project-empty slots whose members remain
mining-owned. Profile their complete ownership and occurrence sets before
preregistering G5h; do not infer that another isolated word move is safe.

While G5g was being gated, the Designer captured a new invalid review for
`10 of the years are large.` against
`arithmetic/partition-attribute-of-noun`. It attaches both
`premise_too_broad` and `semantically_implausible` to the adjective slot and
confirms the source-linked hypothesis. That evidence is preserved but is not
silently folded into G5g. Reconcile the complete adjective/noun compatibility
boundary before preregistering another coverage increment.

#### Review-led adjective/noun compatibility — complete

The complete curated occurrence set contains four `type: adjective` premise
slots: the cardinal, fractional, explicit-noun, and rest partition rules.
Only `arithmetic/partition-attribute-of-noun` binds the described noun in the
same rule. The two pronoun forms do not yet know their antecedent noun at
match time, and the rest form is independently blocked. The compatibility
premise therefore belongs only on the explicit-noun rule; adding it to the
other three would pretend an unresolved pronoun or remnant already supplied a
noun.

Before correction, the curated generator admits the unrestricted Cartesian
product of six adjectives and 31 declared plural noun lemmas: 186 pairs. The
new premise will admit a deliberately conservative 152-pair domain:

- `color_attribute` (`red`, `green`, `blue`) applies to 22 declared
  `colorable_noun` members;
- `size_attribute` (`small`, `large`) applies to both
  `physical_size_noun` and `magnitude_noun`, whose disjoint memberships total
  28 noun lemmas; and
- `remnant_adj` (`left`) applies to 30
  `remainder_collection_noun` members.

This is explicitly many-to-many. A category document declares
`attribute_compatibility` as an adjective-category key mapped to a list of
compatible noun categories. An adjective and noun may each belong to
multiple categories. Matching succeeds when any declared category pair
licenses the two lemmas, and the premise explanation names that exact pair.
Pack extensions may add adjective members, noun members, or another
compatible noun category without redefining either word or category.

The complete standing-corpus DEV sweep found nine current matches and these
eight unique pairs:

- GSM8K: `yellow/flower`, `red/flower`, `full/box`, `ripe/peach`, and
  `white/rose`;
- ASDiv: `good/carrot` and `red/ticket`; and
- MAWPS: `married/woman`.

SVAMP, SciBench, and FOLIO contain no current match for this rule. The
cross-pack declarations must preserve all eight pairs. In particular,
`size_attribute` will demonstrate more than one compatible noun category,
while a synthetic project must prove that either branch licenses a pair and
an unlisted third category is rejected.

The preregistered result is a precision narrowing with no availability
change: 26/93 rules remain selectable,
`arithmetic/partition-attribute-of-noun` remains supported, all eight
standing-corpus pairs remain matchable, and the reviewed `large/year` pair
becomes absent. No review or exploration row is rewritten. The cumulative
generator version becomes `g6-attribute-compatibility`.

**Result:** the implementation matches that preregistration. Categories
declare an adjective-category key with a list of noun-category targets;
memberships on either side remain independently extensible, and the matcher
accepts the existential union of every declared pair. `size_attribute`
explicitly targets both `physical_size_noun` and `magnitude_noun`, while a
generic invented project proves that either category licenses generation and
matching and an unlisted third category does not. Registry compilation rejects
unknown or wrongly rooted category targets and wrongly typed rule slots.

Generation filters both ordinary and locked/minimal-pair fillers through the
same registry predicate, and its `where` explanation names and source-links
the exact compatibility declaration, both category definitions, and both
memberships. Pack ownership remains local: reference-owned `population`
extends the generic noun categories from `reference`, while difg-owned
attributes and nouns extend the same boundary from `difg-mined`.

The reviewed `10 of the years are large.` is now absent without changing its
append-only review or exploration evidence. The generic core domain is exactly
152 pairs. Curated also loads reference-owned `population`, whose explicitly
declared size and remnant memberships add three licensed pairs, and G5g adds
incompatible `age`; the current complete curated domain is therefore 155/192
pairs. Support remains 26/93 at this historical checkpoint, and all eight
standing DEV pairs remain licensed. The full 3,654-test gate passes; curated
stays 65/65; GSM8K
DEV-train and DEV-holdout stay 104/0 and 40/0 with neutral diffs; ASDiv,
SVAMP, MAWPS, SciBench, and FOLIO retain zero wrong commitments; and lint
remains at zero errors with the same two known warnings.

#### Review-led leading GroupTotal subject boundary — complete

The sole remaining live review is invalid
`Altogether there drops 2 coins.` against
`arithmetic/group-total-leading-marker`. Before correction it bound existential
`there` through `who: type word`, bound unrestricted `drops` as the verb,
emitted `GroupTotal(scope="there", measure="coin", value=2, verb="drop")`, and
still reported that `drops` had no subject. The confirmed broad-verb
hypothesis identifies a symptom, but narrowing the verb slot itself would
remove valid aggregate actions.

A first sweep undercounted this occurrence class as 19. The completed,
post-change audit over both GSM8K DEV partitions and ASDiv DEV found 26
matches across the leading GroupTotal family: 25 genuine scoped/action totals
and one existential
surface. The valid action verbs include `sold`, `weigh`, `ran`, `earned`,
`watched`, `paid`, `picked`, `used`, `walked`, `spent`, `make`, `scored`, and
`planted`; they require the existing broad verb slot. The one existential
surface is `In total there are 96 flowers ...`. Before correction it emitted
the same incorrect `scope="there"` representation and declined downstream.

The implemented structural split is:

- both existing scoped leading rules add
  `slot_not_category: {slot: who, cat: existential}` while retaining their
  broad action-verb slots and scoped emissions;
- the generator realizes that generic negative category predicate by filtering
  the named slot's project-backed domain, including locked fillers;
- `arithmetic/group-total-leading-existential` owns
  `In total there COPULA COUNTED`, and
  `arithmetic/group-total-leading-marker-existential` owns
  `TOTALITY_MARKER there COPULA COUNTED`;
- both existential rules require declared copular number agreement, consume
  the counted item, and emit an unscoped GroupTotal with holding semantics;
  and
- no coverage is inferred for other existential verbs or inverted surfaces.

The availability delta is 26/93 → 28/95: the two existing rules stay
supported and the two explicit existential rules are added. All 18 scoped DEV
matches originally counted, plus the seven recovered by the complete audit,
retain action/state verbs and non-`there` scopes; the one existential DEV
match reroutes to an unscoped holding total. The marker-existential rule uses
the exact totality-marker alternation `altogether|combined|together|total`,
because the broader degenerate `aggregate` sense also contains `average` and
would generate the invalid surface “Average there …”.

The reviewed `drops` specimen now matches neither family and emits no
`GroupTotal`. `slot_not_category` is enforced during ordinary, locked, and
minimal-pair realization and explained as a source-backed `where` premise.
Static overlap analysis recognizes the subtraction, so it does not report the
scoped and existential siblings as overlapping. The append-only review and
exploration evidence remain unchanged. The cumulative generator version is
`g6-group-total-scope-boundary`.

The complete gate is green: 3,672 tests pass in four-worker mode; curated is
65/65; GSM8K DEV train and holdout remain 104/0 and 40/0 with neutral diffs;
ASDiv, SVAMP, MAWPS, SciBench, and FOLIO retain zero wrong commitments; and
lint has zero errors.

#### G5h core-owned exploratory category frontier — complete

The post-boundary curated frontier is 28 supported rules and 67 blocked rules.
Recursive profiling corrected the handoff's preliminary “five empty slots”
description. Seven noun/verb-rooted categories are empty in curated premise
rules because their generic-looking lexicon entries and memberships remain
owned by `difg-mined`. Optional nesting also exposes seven
`aggregate_noun` ask occurrences. Ask-only empty categories and
comparative/time/adverb roots remain outside G5 premise-generation scope and
stay visible for G7 or their own structured realizer.

| Empty category | Mining-owned entries | Premise occurrences | Ask occurrences | Standalone availability delta | Standing inspectable DEV matches |
| --- | --- | ---: | ---: | ---: | ---: |
| `duration_verb` | `take`, `takes`, `took` | 1 | 0 | +1 | 6 |
| `remnant` | `remainder`, `rest` | 4 | 0 | +2, plus two optional rules lose this blocker | 97 |
| `desire` | `want`, `wanted`, `wanting`, `wants` | 1 | 0 | +1 | 66 |
| `need_premise` | `need`, `needed`, `needs` | 1 | 0 | +1 | 58 |
| `aggregate_noun` | `amount`, `number` | 6 | 7 | +0 | 36 |
| `quantity_anaphor` | `amount`, `number` | 1 | 0 | +0 | 17 |
| `price_anaphor` | `cost`, `price` | 1 | 0 | +0 | 2 |

The 282 matches above cover both GSM8K DEV partitions plus ASDiv, SVAMP,
MAWPS, SciBench, and FOLIO DEV. SciBench and FOLIO have no matches in the
class. The remnant count includes all four rule occurrences: one
`fraction-of-remnant`, 20 `rest-of-pool`, 27 rest-attribute partitions, and
49 rest-membership partitions. Ninety-six are explicitly definite (“the
rest/remainder”); the sole bare occurrence is awkward ASDiv prose and already
declines. All 66 desire matches use finite `wants`/`wanted` and a bare
infinitive. All 58 need matches use finite `needs`/`needed`. All six duration
matches use `takes` and a bare infinitive; five spans are already declared
time measures, while one valid `seconds` surface exposes a separate
lexicon/morphology gap (`second` is adjective-sensed and `seconds` is an
unrelated bare noun entry).

In-memory pack relocation proved the ownership operation itself is
semantically neutral for projects that already load `difg-mined`: after
moving each lexicon group and every core-declared membership, every compiled
`Registry` field except the ownership-derived fingerprint is identical.
Each individual move and the four apparent coverage moves together also keep
the curated suite at 65/65. The four coverage moves would mechanically produce
the exact 28/95 → 33/95 support delta:

- `arithmetic/extraposed-duration-rate`;
- `arithmetic/fraction-of-remnant`;
- `arithmetic/rest-of-pool`;
- `arithmetic/goal-desire-quantity`; and
- `arithmetic/goal-need-quantity`.

Seeded temporary realization exposed premises that the ordinary matcher
accepts but ordinary English does not:

- the duration rule permits any counted noun as the elapsed span, any entity
  as the extraposed object, unrestricted `take/takes/took`, and any inflected
  verb after infinitival `to`;
- both newly selectable remnant rules omit the required definite article and
  retain an unrestricted finite verb;
- the desire rule admits bare `want` and participial `wanting` after a
  singular proper-name subject, plus non-bare verbs after `to`; and
- the need rule admits bare `need` after a singular proper-name subject.

Those defects are the evidence this workbench exists to reveal. Mechanical
support means that the generator can fill the declared structure and the
ordinary matcher accepts the result. It does not mean that a rule's premises
are grammatically or semantically adequate. Hiding the rule until its grammar
was already correct would invert the review loop and prevent the user from
observing the defect that should motivate the correction.

The relocation also widens already-selectable rules through generic type
domains. The four coverage groups together add nine filler positions across
five existing supported rules; verb-only groups each affect seven positions
across five rules, while remnant nouns affect four positions across four
rules. Moving `amount/number` unlocks no rule but changes 18 positions across
14 supported rules. Moving `cost/price` also unlocks no rule while changing
23 positions across 15 rules. That is intended exploratory reach, not runtime
approval: the reachable filler frontier should include all project-owned
vocabulary that satisfies the rule as currently authored.

**G5h result:** all seven generic domains and their 16 unique lexicon entries
move from `difg-mined` to the defining `core-english` pack without copying.
Mining-specific categories such as `accompany`, `need_ask_verb`,
`price_verb`, `dimension_noun`, and `currency_measure` continue to extend
those core-owned words. The combined GSM8K registry retains the same lexical
and category content apart from ownership-derived provenance, and curated
remains 65/65.

The exact frontier is now 33/95: the five rules listed above are selectable,
and all 125 lexicon identities reachable through supported slots can be
probed. The cumulative generator version is
`g6-g5h-core-category-frontier`. Generated missing definiteness, unsuitable
duration spans, non-bare infinitives, and subject/verb disagreement are
reviewable defects and hypotheses for later rule edits; they are not
availability blockers.

The complete gate remains green: 3,680 tests pass in four-worker mode;
curated is 65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0;
ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO
makes zero commitments; and lint has zero errors with the same two documented
warnings.

#### G5i recursive optional-branch realization — complete

The complete curated premise-rule profile contains 114 optional groups across
51 rules. Thirty-one groups are nested, the maximum nesting depth is three,
and the whole class reduces to 16 recursive structural shapes. The dominant
shapes are optional pronoun/noun qualification, a lone optional pronoun, and
an optional preposition containing a nested pronoun plus noun.

Support is deliberately branch-complete. An optional wrapper is realizable
only when every token in its include branch is itself realizable, recursively.
Omission cannot hide an unsupported child. This reveals the actual residual
blocker—such as comparative, adverb, complementizer, modal, quantifier, or
`where` predicate—on rules that previously reported only the generic optional
blocker.

The generator makes a seeded include/omit choice for every active group.
Nested groups under an omitted parent are recorded as `inactive`, distinct
from a group actively selected as `omitted`. Locked or excluded bindings
inside a group force every enclosing group to be included, so a minimal pair
cannot silently discard a binding it promises to preserve.

The premise inspector walks the same recursive tree in stable preorder:

- each group reports `included`, `omitted`, or `inactive`;
- active child tokens retain their ordinary bindings, category paths,
  morphology, and consumed-unit evidence;
- children of an omitted branch remain visible as `unverified`, rather than
  disappearing; and
- every top-level or nested row carries its exact YAML token path through the
  authoring-only source index.

Exploration and lexicon probing also walk optional descendants, while only
fillers actually selected into a successful candidate are recorded. This
preserves the separation between mechanical sampling and human judgment.

**G5i result:** 17 rules become newly selectable, moving the frontier from
33/95 to 50/95. Reachable lexicon identity remains 125 because the optional
branches reuse domains already reachable through other supported slots. The
cumulative generator version is `g6-g5i-optional-branches`.

The remaining 45 blocked rules no longer contain an optional-realizer
placeholder. Their leading explicit blockers are 19 `delta` comparative-root
occurrences, 14 `absent` predicates, eight `unbound` predicates, four
`distinct_measure` predicates, and four `future_modal` slots. Smaller
category-root gaps cover complementizers, quantifiers, adverbs, dimension and
age comparatives, count intensifiers, temporal markers, and one ordinary
modal slot.

The complete gate is green: 3,703 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with the same two documented curated
warnings.

#### G5j comparative-category realization — complete

The remaining category-root profile found 23 comparative-gated premise
positions across 22 rules:

- 20 `delta` positions across 19 rules;
- one `age_comparative`;
- one `dimension_comparative`; and
- one `count_intensifier`.

Curated has the complete three-member `delta` domain (`fewer`, `less`, `more`)
and the one-member `count_intensifier` domain (`more`). Its age- and
dimension-comparative categories remain empty because those mined forms are
not owned by the curated project. Supporting the root therefore does not
pretend those two slots are fillable: they now report an exact project-backed
filler gap.

Comparative realization uses the existing category-generic lexical domain,
the same implementation used by noun-, verb-, adjective-, preposition-, and
pronoun-rooted categories. No comparative words appear in Python. An invented
`zigher → invented_delta → comparative` project proves that arbitrary loaded
vocabulary generates, matches, and retains its lexicon, membership, category,
and rule-token sources.

**G5j result:** 12 rules become newly selectable, moving the frontier from
50/95 to 62/95. All 12 produce ordinary matcher-confirmed specimens, and each
core `delta` member can be deliberately locked and probed. No vocabulary is
added, no previously supported rule is widened, and the reachable lexicon
frontier remains 125. The cumulative generator version is
`g6-g5j-comparative-categories`.

Generated affine and comparative specimens are often awkward. They remain
reviewable evidence of the authored grammar; G5j asserts only that their
declared category premise can be realized.

The complete gate is green: 3,722 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with the same two documented curated
warnings.

The remaining frontier is 62 supported and 33 blocked. The leading explicit
blockers are 14 `absent` predicates, eight `unbound` predicates, four
`distinct_measure` predicates, and four `future_modal` slots. Two
complementizer and two quantifier roots remain, along with two empty
comparative-category domains and one each of adverb, ordinary modal, and
temporal-marker support.

G5k should profile `absent` first. It is the sole blocker on ten rules, but its
realizer must prove which declared slot or structure must be withheld rather
than treating the predicate as automatically true. Generated defects remain
review evidence, not a reason to hide a mechanically supported rule.

#### G5k sentence-wide absent-category realization — complete

The preregistered G5k profile contained 14 rules and 17 predicate occurrences:

- four `absent: {cat: aggregate}` predicates;
- four `absent: {cat: partitive}` predicates;
- three `absent: {cat: temporal_marker}` predicates;
- three `absent: {cat: relational_marker}` predicates; and
- three `absent: {cat: multiplier_marker}` predicates.

Later review increments reuse the same general machinery. The current profile
contains 19 rules and 24 occurrences: four aggregate, six partitive, three
temporal-marker, six relational-marker, three multiplier-marker, and two
conjunction exclusions. The newest relational exclusion enforces that an
anchorless comparative cannot consume the prefix of a `than` clause.

This predicate names no slot. The ordinary matcher scans every analyzed unit
in the sentence and rejects the match when a unit's lemma belongs to the
forbidden category. Generation now enforces that same whole-sentence boundary:
every literal and slot domain is filtered through the registry's
analyzed-lemma membership predicate before a filler can be selected.
Locked bindings cannot bypass the filter, and the exploration scheduler does
not advertise a forbidden lexicon identity as a compatible probe.

Availability remains conservative. It verifies that every declared leaf,
including descendants of optional groups, retains at least one project-backed
filler outside all of the rule's absent categories. If not, the rule reports
the exact leaf and categories instead of assuming that an optional omission
will hide the unsupported declaration. An invented two-noun project proves
that a broad noun slot selects only the safe member, a locked forbidden member
fails realization, exploration excludes that member, and an unavoidable
forbidden literal blocks the rule.

Every successful candidate retains one ordinary `where` premise row per
negative predicate. The explanation records that no analyzed unit belonged to
the named category and source-links the exact rule predicate plus the category
definition when the loaded project declares one.

**G5k result:** ten rules become newly selectable, moving the frontier from
62/95 to 72/95. Four rules carrying `absent` remain blocked only by independent
`future_modal` or `quantifier` gaps. All ten new rules produce ordinary
matcher-confirmed specimens. No vocabulary or runtime matcher changes, and
the reachable lexicon frontier remains 125. The cumulative generator version
is `g6-g5k-absent-categories`.

The complete gate is green: 3,736 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 72 supported and 23 blocked. The leading explicit
blockers are eight `unbound` predicates, four `distinct_measure` predicates,
and four `future_modal` slots. Two complementizer and two quantifier roots
remain, along with two empty comparative-category domains and one each of
adverb, ordinary modal, and temporal-marker support.

G5l should profile `unbound` next. It stands alone on eight rules. All nine
named sentinel occurrences are descendants of top-level optional groups, and
one rule names sentinels from two separate groups. The implementation must
prove genuine matcher-level non-binding and reconcile forced omission with
G5i's optional-branch exploration contract; deleting a requested binding
after realizing its surface would not satisfy the premise.

#### G5l matcher-confirmed unbound branch omission — complete

The complete profile contains eight rules and nine sentinel occurrences:
seven `std_seen` occurrences and two `item2_seen` occurrences. Seven rules
declare one top-level optional negative-lookahead branch. The eighth,
`arithmetic/times-as-many-conjunct-elided-item`, independently guards both an
explicit item branch and an explicit standard branch.

Every sentinel is a required leaf of its enclosing optional branch. If that
branch is included, the sentinel necessarily binds and the ordinary matcher's
`unbound` predicate rejects the target rule. The valid generation language
therefore omits the nearest enclosing branch. It does not erase a requested
binding after realization, and it does not force a wider ancestor branch out
when a nested valid prefix can still be included.

This is an intentional exception to random include/omit exploration, not a
retreat from G5i's complete declaration inspection. The omitted branch and all
of its descendants remain visible in the premise table. Its row explains that
it is the rule's negative-lookahead branch, each descendant remains
unverified, and the `where` row records every sentinel as `unbound` with a
matcher-confirmed explanation.

Locked and excluded bindings still force ordinary optional ancestors to be
included. If they require a branch that `unbound` makes invalid, realization
fails explicitly rather than silently ignoring the request. Exploration
similarly excludes lexicon placements reachable only through a forced-omitted
branch. An invented nested rule proves that a locked sibling can include the
outer branch while the nearest inner sentinel branch stays omitted; the
legitimate sibling remains probeable, the sentinel-only filler does not, and
locking the sentinel fails.

Availability also verifies that each named sentinel exists and is confined to
optional structure. A required sentinel remains honestly blocked because no
omission can make it unbound.

**G5l result:** eight rules become newly selectable, moving the frontier from
72/95 to 80/95. All eight produce ordinary matcher-confirmed elided specimens
on their first deterministic attempt. No vocabulary or runtime matcher
changes, and the reachable lexicon frontier remains 125. The cumulative
generator version is `g6-g5l-unbound-branches`.

The complete gate is green: 3,748 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 80 supported and 15 blocked. Four
`distinct_measure` rules and three otherwise-unblocked `future_modal` rules
form the leading complete classes. Two complementizer and two quantifier roots
remain, along with two empty comparative-category domains and one each of
adverb and ordinary modal support. The fourth `future_modal` rule also needs
the currently unsupported temporal-marker category.

G5m should profile `distinct_measure` next. It stands alone on four rules
through five slot-pair checks: `anchored-relation`, two checks in its
conjoined-measures sibling, its possessive-kinship sibling, and its postfix
sibling. The matcher compares `(lemma, label, qualifier)`, so the generator
must model that exact key even though current single-token fillers carry null
labels and qualifiers. Surface inequality alone is not the contract.

#### G5m exact distinct-measure-key realization — complete

The complete profile contains four rules and five pair checks:

- `arithmetic/anchored-relation`: `item` / `std`;
- `arithmetic/anchored-relation-conjoined-measures`: `item` / `std` and
  `item2` / `std`;
- `arithmetic/anchored-relation-possessive-kinship-standard`: `item` / `std`;
  and
- `arithmetic/anchored-relation-postfix`: `item` / `std`.

All named slots are required and each predicate is the rule's sole blocker.
Current plural, noun, and entity domains expose 36–42 canonical measure keys
per slot and 1,263–1,479 valid pair assignments. The counted postfix domain
contains 1,008 surfaces because every declared count combines with every noun,
but those surfaces collapse to 36 canonical noun keys. Availability therefore
cannot reason in surface space.

`_Filler` now carries the matcher's complete `(lemma, label, qualifier)` key.
The current single-token generators populate null label and qualifier fields,
but the machinery deliberately retains them: two fillers sharing a lemma are
validly distinct when either label or qualifier differs, matching the runtime
predicate that admits “green apples” versus “red apples”.

Availability solves all linked `distinct_measure` groups together and reports
an exact blocker when no project-backed assignment exists. Realization filters
against already chosen keys and metadata-resolved future locked bindings, so
slot order cannot admit a collision. Minimal-pair generation retains the
locked comparison slot and the excluded original surface while searching for
a genuinely different key.

Exploration applies the same satisfiability check per proposed slot/filler
placement. It does not advertise a filler in a position that would leave no
valid assignment for the remaining measure slots. An invented asymmetric
three-noun project proves this placement filtering, successful locked
generation, a forced third-key minimal pair, rejection of two locked identical
keys, and an honestly blocked one-key rule. A direct qualified-filler test
proves that qualifier and label differences independently satisfy the exact
key contract.

Each passed predicate explanation records the actual triples from the ordinary
matcher, not just the generated surfaces.

**G5m result:** four rules become newly selectable, moving the frontier from
80/95 to 84/95. All four produce ordinary matcher-confirmed specimens. No
vocabulary or runtime matcher changes, and the reachable lexicon frontier
remains 125. The cumulative generator version is
`g6-g5m-distinct-measures`.

The complete gate is green: 3,757 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 84 supported and 11 blocked. Two complementizer
rules and one quantifier-only rule have project-backed fillers and no other
blockers. Three `future_modal` rules are otherwise ready, but curated owns no
members of that category; a fourth also needs `temporal_marker`, whose members
are likewise absent. The two comparative filler gaps, one empty adverb
category, and the periodic rule's combined modal/quantifier blockers complete
the frontier.

G5n should profile the complementizer root next. It has two premise
occurrences—one mandatory and one optional—both backed by the core-owned word
`that`, and should reuse the existing category-generic realizer by admitting
the `complementizer` root. By contrast, admitting `future_modal` as a type
without first resolving vocabulary ownership would unlock nothing and should
only replace one honest blocker with another.

#### G5n direct complementizer-category realization — complete

The complete profile contains exactly two occurrences:

- `arithmetic/affine-frame-relation` has a mandatory `c` slot; and
- `arithmetic/fraction-frame-relation` places `c` inside an optional branch.

Both use the direct `complementizer` root-sense category. It is not a declared
category hierarchy in the current registry, and its sole curated filler is
the core-owned lexicon entry `that`. G5n therefore admits the root to the
existing category-generic generator without adding vocabulary, a literal word
branch, or runtime matcher behavior.

Both rules produce ordinary matcher-confirmed specimens. The fraction-frame
rule remains validly explorable with its complementizer branch included or
omitted, and the included premise reports `that → complementizer` with exact
rule-token and lexicon sources. Exploration exposes the `c` placement in both
rules. An invented project with a different complementizer-sensed word proves
the realizer follows loaded project vocabulary rather than the curated
surface.

**G5n result:** two rules become newly selectable, moving the frontier from
84/95 to 86/95. The reachable lexicon frontier remains 125 because `that` was
already reachable through broader supported word slots. The cumulative
generator version is `g6-g5n-complementizers`.

The complete gate is green: 3,764 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 86 supported and 9 blocked. `quantifier` is the next
smallest complete project-backed root: it occurs on two rules and has six
curated fillers (`all`, `each`, `every`, `much`, `no`, and `some`). Supporting
it should unlock the otherwise-ready
`arithmetic/existential-premise-distributive`; its periodic sibling will remain
honestly blocked by the independent empty `modal` slot. The adverb category
and both modal slot families have no curated fillers, two comparative
categories remain empty, and the fourth future rule also lacks a temporal
marker.

G5o should profile the full quantifier-root occurrence and filler maps, admit
only the existing category-generic root, prove all six project-backed fillers
through exploration, round-trip the newly available distributive rule, and
retain the periodic sibling's independent blocker.

#### G5o direct quantifier-category realization — complete

The complete profile contains exactly two direct root-sense occurrences:

- `arithmetic/existential-premise-distributive.q`; and
- `arithmetic/periodic-rate-every-span.freq`.

Curated owns six general quantifier fillers in `core-english`: `all`, `each`,
`every`, `much`, `no`, and `some`. G5o admits the root to the existing
category-generic generator without adding vocabulary, literal surfaces, or
runtime matcher behavior.

The current core inventory also owns `double` and `triple` as the two members
of `predeterminer_multiplier`. They were added later by G5v to distinguish
noun-phrase forms such as `double the amount` from reviewed adverbial
`as many/as much` frames; they do not widen the dedicated distributive or
frequency categories established after G5o.

The distributive rule becomes selectable and every loaded quantifier can be
locked into a matcher-confirmed specimen with exact token and lexicon sources.
Exploration exposes all six only on that supported `q` placement. The periodic
rule remains honestly blocked by its independent optional `type: modal`
descendant, so generation does not advertise an unusable `freq` placement.
An invented project with a different quantifier-sensed word proves the
realizer follows loaded project vocabulary.

The broad filler set is itself useful review evidence. The rule description
names `each` and `every`, while the declared `cat: quantifier` premise also
admits `all`, `much`, `no`, and `some`. G5o deliberately does not hide that
possible premise defect behind a narrower generation-only domain.

**G5o result:** one rule becomes newly selectable, moving the frontier from
86/95 to 87/95. The reachable lexicon frontier remains 125 because all six
quantifiers were already reachable through broader supported slots. The
cumulative generator version is `g6-g5o-quantifiers`.

The complete gate is green: 3,774 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 87 supported and 8 blocked, and every rule now
lacks project-backed vocabulary somewhere. One optional adverb slot has no
loaded adverb-sensed filler; two comparative categories are declared in core
but receive their members and lexicon entries from `difg-mined`; the periodic
rule's modal type has no loaded modal word; four future rules depend on
`future_modal` members `will`/`would` from `difg-mined`; and the fourth also
needs the `temporal_marker` members `today`/`now` from that pack.

G5p should profile every remaining repository member and ownership boundary,
separate generic-English relocation candidates from mined or overly broad
premises, measure each possible move's runtime and generation blast radius,
and preregister the smallest complete ownership increment. It must not enable
empty types or load `difg-mined` into curated merely to conceal the current
project boundary.

#### G5p remaining-blocker vocabulary ownership audit — complete

All eight remaining blocked rules lack curated vocabulary somewhere. The
repository-wide inventory is:

| Boundary | Repository inventory | Current owner | Immediate delta |
|---|---:|---|---:|
| direct `adverb` root | 45 words | `difg-mined` | unsafe to infer from the broad root |
| `age_comparative` | 2 words | `difg-mined` | +1 rule |
| `dimension_comparative` | 9 words | `difg-mined` | +1 rule |
| direct `modal` root | 8 words | `difg-mined` | needs a slot realizer |
| `future_modal` | 2 of those modal words | `difg-mined` | needs a slot realizer |
| `temporal_marker` | 2 of 5 time words | `difg-mined` | needs future-modal support first |

The inventory was measured through loaded registries, not filename guesses.
Every listed curated gap is empty; the same categories or senses become
populated in the GSM8K project because it explicitly loads `difg-mined`.

In-memory ownership overlays establish the decision boundary:

- moving `older` and `younger` plus their core-declared
  `age_comparative`/`more_dir`/`less_dir` memberships raises availability from
  87 to 88 and unlocks only
  `arithmetic/times-comparative-age-relation`;
- moving the nine dimension comparatives also buys one rule, at a larger
  vocabulary surface;
- moving `will`/`would` or `now`/`today` without new type support buys no
  rule; and
- simulating both ordinary/future modal realizers with `will`/`would` raises
  availability to 91, a four-rule jump that combines vocabulary, two slot
  contracts, and the periodic rule's broad-modal semantics.

The adverb occurrence is not a safe one-word ownership move. Its rule declares
the root `adverb`, which would admit all 45 repository adverbs, while its
comment motivates a much narrower optional trailing marker. It needs its own
premise-shape decision.

The age move is the smallest complete class and preserves extension behavior.
An in-memory relocation removed the two lexicon entries and three
core-declared memberships from `difg-mined`, added them to a core overlay, and
recompiled the GSM8K pack set. Every semantic registry field remained equal;
the mined-owned `higher`/`lower` memberships continued to extend the now
core-owned words.

G5q should implement exactly that two-word relocation, prove semantic registry
equivalence for the combined pack set, assert the 88/95 frontier, generate
matcher-confirmed specimens with both comparatives, and leave dimension,
modal, temporal, and adverb work separate.

#### G5q age-comparative core ownership — complete

The two generic age comparatives now live with the core grammar:

- `older` and `younger` moved from the mined lexicon to
  `core-english`;
- `age_comparative` now owns both words in core;
- `more_dir` owns `older` and `less_dir` owns `younger` in core; and
- the mined-only `higher`/`lower` memberships remain extension data in
  `difg-mined`.

This is an ownership move, not a duplicated vocabulary layer. Projects loading
both packs compile one lexicon declaration per word. An exhaustive test
reconstructs the legacy pack layout in memory and compares every semantic
registry field except its source fingerprint. The combined project remains
identical: `older` carries `age_comparative`/`higher`/`more_dir`, and
`younger` carries `age_comparative`/`less_dir`/`lower`.

Both words generate matcher-confirmed specimens for
`arithmetic/times-comparative-age-relation`, with their exact lexical,
membership, category, and rule-token sources. They also remain deliberately
probeable through the existing additive `delta` rules; moving ownership does
not suppress their previously declared `more_dir`/`less_dir` behavior.
Exploration exposes both identities on the newly available rule.

**G5q result:** one rule becomes newly selectable, moving the frontier from
87/95 to 88/95. Reachable lexicon identities increase from 125 to 127. The
cumulative generator version is `g6-g5q-age-comparatives`.

The complete gate is green: 3,782 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 88 supported and 7 blocked. The next isolated
ownership-only class is the nine dimension comparatives already inventoried
by G5p: six positive forms (`heavier`, `higher`, `larger`, `longer`, `taller`,
`wider`) and three negative forms (`lighter`, `shorter`, `smaller`). Moving
their `dimension_more`/`dimension_less` ownership should unlock exactly
`arithmetic/anchored-relation-postfix-dimension` and yield 89/95.

G5r should implement that class without modal, temporal, or adverb changes,
preserve every mined extension membership, prove combined-registry
equivalence, generate all nine forms, and measure the reachable-filler delta.

#### G5r dimension-comparative core ownership — complete

The complete signed dimension class now lives with the core grammar:

- `dimension_more`: `heavier`, `higher`, `larger`, `longer`, `taller`, and
  `wider`; and
- `dimension_less`: `lighter`, `shorter`, and `smaller`.

The nine lexicon entries moved from `difg-mined` to `core-english` together
with those two core-declared memberships. The mined pack retains its broader
`higher`/`lower` extensions. There is no duplicated vocabulary or
generation-only surface list.

Every form generates a matcher-confirmed specimen for
`arithmetic/anchored-relation-postfix-dimension`. Its premise reports the
exact signed category ancestry and source declarations, and exploration
exposes all nine identities on the new rule. The registry's declared polarity
remains `+1` for `dimension_more` and `-1` for `dimension_less`.

An exhaustive test reconstructs the legacy ownership layout in memory and
compares every semantic registry field except its source fingerprint.
Projects loading both packs remain identical: positive forms retain mined
`higher` where declared, negative forms retain `lower`, and `wider` remains
dimension-only.

**G5r result:** one rule becomes newly selectable, moving the frontier from
88/95 to 89/95. Reachable lexicon identities increase from 127 to 136. The
cumulative generator version is `g6-g5r-dimension-comparatives`.

The complete gate is green: 3,795 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 89 supported and 6 blocked. The next coherent class
is modal ownership plus realization. Eight generic modal words remain
mined-owned: six `capacity_modal` members (`can`, `could`, `may`, `might`,
`must`, `should`) and two `future_modal` members (`will`, `would`).

G5s should move those declarations and memberships to core, implement generic
`modal` and category-filtered `future_modal` filler domains, prove
combined-registry equivalence, and test the exact domains. It should unlock
the periodic rule and three future rules for a 93/95 frontier. The fourth
future rule must remain blocked solely by its empty `temporal_marker`.
Temporal and broad-adverb support remain separate.

#### G5s modal core ownership and realization — complete

All eight generic modal declarations now live with the core grammar:

- `capacity_modal`: `can`, `could`, `may`, `might`, `must`, and `should`;
- `future_modal`: `will` and `would`; and
- direct `type: modal`: the union selected from the loaded modal lexical
  sense.

The move does not duplicate vocabulary. `can` keeps both its modal and noun
senses and its declared plural `cans`; a project loading `difg-mined` also
retains that pack's `litter` membership. An exhaustive test reconstructs the
legacy ownership layout in memory and compares every compiled registry field
except the source fingerprint. Combined-pack semantics are identical.

Generation derives both domains from the registry. The periodic rule exposes
all eight loaded modals with exact lexical and subtype-category ancestry;
future-only slots expose only `will` and `would`. A capacity modal cannot be
forced through a future slot by a locked binding.

The first periodic samples also exposed a valid exploratory edge: a declared
zero count may become the denominator of its emitted rate. The ordinary
runtime raises an arithmetic error for that unusable sample. Generation now
records that attempt as rejected and deterministically tries the next
candidate; exhausting the attempt budget reports a `GenerationError` instead
of crashing or manufacturing a successful review item.

**G5s result:** four rules become newly selectable, moving the frontier from
89/95 to 93/95. Reachable lexicon identities increase from 136 to 144. The
cumulative generator version is `g6-g5s-modals`.

The complete gate is green: 3,814 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is 93 supported and 2 blocked. The next isolated
ownership class is the temporal marker: `now` and `today` are generic
time-sensed words currently owned by `difg-mined`, and both are members of
the core-declared `temporal_marker` category. G5t should move the declarations
and memberships to `core-english`, admit the loaded `time` root to
category-generic generation, preserve combined-pack semantics, and expose
both markers on
`arithmetic/temporal-offset-times-as-old-as-future-std-now`. The expected
frontier is exactly 94/95.

The final direct-adverb blocker stays separate. Its root would expose the full
45-word repository adverb inventory to a premise intended as a narrow
trailing anchor marker; that premise shape must be reviewed before broad
adverb realization is enabled.

#### G5t temporal-marker core ownership and realization — complete

The two generic deictic markers now live with the core grammar:

- `now` and `today` are core lexical entries carrying the `time` sense; and
- both are core members of the narrower `temporal_marker` category.

The category-generic generator now admits the loaded `time` root. It therefore
uses registry vocabulary and exact membership rather than a hidden list of
deictic words. Both markers generate matcher-confirmed specimens for
`arithmetic/temporal-offset-times-as-old-as-future-std-now`, with their
lexicon, membership, category ancestry, and rule token source-linked. An
invented time-rooted category and word follow the same path.

An exhaustive in-memory reconstruction returns the two declarations and their
membership to the mined pack and removes them from core. Every compiled
registry field except the source fingerprint remains identical, proving that
the move changes core-only availability rather than combined-project
semantics.

**G5t result:** one rule becomes newly selectable, moving the frontier from
93/95 to 94/95. Reachable lexicon identities increase from 144 to 146. The
cumulative generator version is `g6-g5t-temporal-markers`.

The complete gate is green: 3,821 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with three known warnings.

The remaining frontier is one rule:
`arithmetic/anchored-relation-conjoined-anchor`. Its optional
`trailing_adv` slot is authored against the direct `adverb` root. The combined
repository contains 45 single-token adverbs, while curated currently contains
none. The rule description's intended ordinary example uses `currently`, but
the premise deliberately does not say that.

G5u should move only generic `currently` into core, admit the direct loaded
`adverb` root, and expose the authored breadth rather than applying a
generation-only repair. Curated should reach 95/95 with `currently` plus the
already valid omitted-adverb form. A project loading `difg-mined` should see
all 45 loaded adverbs on that placement, allowing human review to determine
whether a narrower declarative category is warranted. Combined-registry
semantics must remain identical after the ownership move, and an invented
adverb must prove the realizer is registry-backed.

#### G5u direct-adverb visibility — complete

The final direct lexical root is now mechanically visible:

- generic `currently` moved from `difg-mined` to `core-english`;
- direct `adverb` category slots draw from the complete loaded adverb sense;
- the optional trailing branch generates both included and omitted forms; and
- the generator version at this checkpoint was `g6-g5u-adverbs`.

This remains a project-relative domain. Curated owns one adverb and therefore
offers `currently` on the final rule. The combined GSM8K project still owns 45
single-token adverbs in total, and all 45 remain visible on the broad authored
placement. Generation does not invent a narrower anchor category or discard a
surface because it sounds awkward. A resulting `absent` round trip is honest
review evidence about the rule, tokenizer, or realizer boundary.

An exhaustive in-memory reconstruction returns `currently` to the mined pack
and removes it from core. Every compiled registry field except the source
fingerprint remains identical. An invented adverb-sensed word also generates
normally, proving that no production surface list was introduced.

**G5u result:** the final rule becomes selectable, moving the premise frontier
from 94/95 to 95/95. Reachable lexicon identities increase from 146 to 147.

The complete gate is green: 3,900 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with two known warnings.

#### G5v review-led audit — active; reconciliations complete through batch 54

Mechanical completeness does not establish linguistic or semantic validity.
The twenty-fourth bounded run began with 406 exploration events, 189 review
rows, and 30 historical failure observations. Folding exactly those 189 rows
produced twelve live reviews; later concurrent rows are explicitly deferred
to the next scheduled reconciliation rather than being folded into a moving
implementation target.

G5v uses the existing Designer loop rather than adding a bulk validator:
Generate next selects a least-explored compatible rule/filler, the human
reviews one sentence, attaches exact premise or fact defects, explores a
source-backed hypothesis, edits declarative YAML when warranted, and retests
the pinned sentence. Every accepted change continues through the complete
test, benchmark, and lint gates. Reviews and exploration remain append-only.

The first batch reconciles five invalid generated/read surfaces as complete
grammar classes:

- subject/verb compatibility is explicit through `number_compatible`, while
  reviewed non-holder nouns and non-quantitative verbs are narrow
  pack-declared exclusions rather than exhaustive allowlists;
- `many_incompatible_noun` subtracts the known non-count readings from the
  open plural/count domain, preserving every established benchmark count noun;
- `mass_quantity_noun` gates `much`, and `quantity_delta` separates additive
  amount directions from age-specific comparatives;
- optional appositive standards require a possessive determiner and animate
  role, and `bound_requires_type` requires the following standard to be a
  proper name only when that prefix binds;
- optional PP objects opt into the `referential` boundary, with
  `bare_pp_object` as the declared bare-adjunct exception;
- demonstrative anaphoric conjuncts require overt `that` or `this`; and
- `standalone: true` separates an elided scalar from a condensed counted noun,
  preventing the elided and postfix relation rules from double-firing.

Generic `this` moved into `core-english` in that batch. Exploration applies
each rule's `slot_not_category` refusals before advertising lexical
compatibility; this removed the invalid historical `there`-as-holder
placement and left a 147-identity reachable frontier at that checkpoint. In
particular, `need`, `take`, and `want` can no longer starve
`arithmetic/affine-fraction-as-many` by remaining permanently least-explored
probes that the realizer must reject. All five pinned reviews from that batch
retest `absent`, all five target rules generate matcher-confirmed specimens
across the bounded seed test, and the existing valid neighbours remain
accepted.

Failed fresh attempts now append to `generation/failures.jsonl` rather than
vanishing. `generated_count` remains successful-realization coverage;
`failed_count` and `attempt_count` are separate, and least-explored selection
ranks by attempts. The Designer labels a failure-only target
`attempted_failed` and refreshes the frontier immediately after the 422
response. Failure scores are registry-fingerprint scoped, so saving a relevant
rule or lexicon change makes the target eligible for rapid retesting without
rewriting its historical attempt.

The second batch reconciles all six current invalid reviews:

- present and past age-comparison rules require the appropriate copula class
  and subject/verb agreement;
- duration rates require a counted `duration_measure`, a finite expletive
  duration verb, and a `bare_form` infinitive;
- descriptor/noun compatibility now covers adjective-, comparative-, and
  preposition-rooted categories, separating linear, mass, and duration
  measure pairings and constraining optional PP objects;
- the fraction-frame relation requires its complete determiner, aggregate
  noun, plural item, repeated verb, and paired optional destination
  preposition structure;
- `same_presence` declaratively couples paired optional slots, while
  `bound_requires_category` applies a category requirement only when its
  controlling slot is present; and
- conjoined aggregate anchors enforce agreement and refuse narrow
  non-quantity holders and verbs.

Generic `inch`, `pound`, and `travel` forms now live in `core-english`;
mined packs retain their corpus-specific category extensions. The current
generator version is `g6-reviewed-premise-boundaries`. All six current pinned
reviews retest `absent`, while direct and prepositional fraction frames,
present and past age comparisons, compatible dimension relations, valid
duration rates, and concrete aggregate anchors remain matcher-confirmed.
Curated remains 95/95 and the reachable frontier is now 150 identities.

The third batch reconciles all ten new live invalid reviews while preserving
the established count-frame benchmark class:

- temporal age-offset rules require declared `age_measure` units rather than
  arbitrary counted nouns; the intensified form also couples the offset
  number to singular/plural `year`;
- desire goals distinguish a `finite_form` matrix desire verb from the
  existing `bare_form` infinitival complement, rejecting participial matrix
  forms and inflected complements without a word list in Python;
- count-frame relations require an overt determiner, a declared
  `count_aggregate_noun`, plural item, additive count direction, and
  semantically viable holder and verb. Both established `amount of PLURAL`
  and `number of PLURAL` frames remain valid;
- an optional repeated item noun is number-compatible with its offset when
  present, while its absence remains neutral; this preserves valid
  `1 more gallon than ... gallons` and rejects plural disagreement;
- optional quantitative PP objects reuse declared preposition/noun
  compatibility, and animate appositive standards exclude the inanimate
  possessive determiner;
- explicit remainder membership uses separate declared collection and member
  noun classes, with generic `animal` owned by `core-english`; and
- `verb_role_compatible` conditionally requires animate/proper-name roles for
  agentive verbs such as the declared spending class while leaving other
  verbs and role domains open.

The generator uses the same constraints, including declared plural surfaces
for category slots participating in number agreement. Every reviewed target
still has matcher-confirmed candidates across the bounded seed gate; all ten
pinned invalid surfaces now retest `absent`. Curated remains 95/95 and the
reachable frontier is now 151 identities. The cumulative generator version
remains `g6-reviewed-premise-boundaries`.

The complete gate is green: 3,948 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 44/0, 30/0, 9/0, and 6/0; FOLIO makes zero
commitments; all before/after diffs are neutral; and lint has zero errors with
three known warnings.

The fourth batch reconciles both new live invalid reviews:

- periodic rates now use the dedicated `frequency_quantifier` category and
  require an explicitly counted `duration_measure`, so existential/amount
  quantifiers and unrelated counted nouns cannot masquerade as a frequency;
- the general `bound_requires_form` predicate makes an optional controller
  require a bare or finite target form only when the controller is present.
  The periodic rule uses its bare mode after a modal, preserving ordinary
  non-modal finite clauses;
- generic sales-verb ownership moves to `core-english` without changing the
  combined registry, and `verb_role_compatible` gains a mutually exclusive
  `excluded_role_cat` mode. The mass-relation rule therefore rejects a sales
  verb with a declared remnant object while leaving non-sales verbs and
  saleable mass nouns open; and
- the same rule's optional PP applies the existing declared
  preposition/noun compatibility relation.

The reviewed `Student should gets 12 hamsters some 6 apples.` and
`Bira sells triple as much rest in their animal as Dena.` surfaces both
retest `absent`. Valid modal and non-modal duration rates, saleable mass
objects, and non-sales remnant relations remain matcher-confirmed. Both
targets also remain generatable across the bounded seed gate.

The complete gate is green: 3,963 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; both
before/after diffs are neutral; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0,
30/0, 9/0, and 6/0; FOLIO makes zero commitments; and lint has zero errors
with three known warnings.

The fifth batch reconciles all twelve new live invalid reviews:

- the possessive-kinship anchored relation adopts ordinary agreement and the
  existing narrow holder, verb, count-noun, and quantitative-PP boundaries;
- `price_relation_verb` distinguishes copular/cost price relations from
  unrelated events without embedding a verb list in Python;
- the reviewed many and fraction comparison PPs reuse the declared
  preposition/noun compatibility relation. DEV snapshot witnesses complete
  the current quantitative-location class with `mall`, `wardrobe`, `wheel`,
  and `side`;
- every existential quantity-premise sibling requires an agreeing copula, and
  rest-of-pool applies agreement plus the narrow non-quantity-object refusal;
- affine appositive determiners must be animate possessives, the affine
  fraction-many form refuses the declared prepositional-frame verb class, and
  both reviewed affine PPs use descriptor/noun compatibility;
- `partition-rest-attribute` checks adjective/noun compatibility only when its
  optional explicit noun is bound, preserving discourse-backed bare rest
  clauses while rejecting incompatible explicit pairs; and
- `polarity_compatible` compares two or more slots inside independently
  declared category scopes. Percent-change events use it to reject an
  explicitly increasing verb paired with a decreasing direction while
  accepting a neutral verb with either direction.

The matcher, availability analysis, normal generation, locked probes, minimal
pairs, and premise explanations share these predicates. All twelve pinned
invalid surfaces retest `absent`; all twelve target rules continue to generate
matcher-confirmed candidates across the bounded seed gate, and valid
neighbors are pinned.

The initial DEV snapshot exposed three valid quantitative locations excluded
by the first boundary draft. Extending the general location category restored
all three commitments. The final DEV-train and DEV-holdout diffs are neutral.

The complete gate is green: 4,004 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; both
before/after diffs are neutral; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0,
30/0, 9/0, and 6/0; FOLIO makes zero commitments; and lint has zero errors
with three known warnings.

The sixth batch reconciles all five new live invalid reviews:

- a named category rooted at the existing `aggregate` sense separates
  `group_total_marker` from `average`, so a GroupTotal fact can only be
  licensed by a true sum marker. The existential and trailing rules retain
  every valid bare total marker and the declared `in total` construction;
- `group_total_preposition` and
  `prepositional_group_total_marker` express the two halves of that
  collocation. `bound_requires_category` activates the marker restriction
  only when the optional preposition binds, rejecting the reviewed
  `with combined`, `at average`, `with total`, and `to total` surfaces;
- count-frame bare and `that` relative clauses require a repeated predicate,
  `same_lemma` alignment with the matrix predicate, and independent
  subject/verb agreement. The same complete-clause premise applies to the
  plain, affine count-frame, and affine bare-item siblings; and
- an optional declared span-preposition plus counted `duration_measure`
  preserves complete duration-bearing relative clauses. The neutral
  DEV-holdout buyer also established the missing singular morphology of
  `drinks`, now declared in the mined lexicon.

The aggregate-root registry extension is structural: it enables pack-owned
subcategories without adding a new sense to any marker, so obligation
disambiguation remains unchanged. The matcher, availability analysis,
generation, locked probes, source evidence, and minimal pairs all see the
same category ancestry and conditional collocation premise.

All five pinned invalid surfaces retest `absent`; valid bare totals, `in
total`, complete relative clauses, paired prepositional frames, and counted
duration spans remain matcher-confirmed. Every corrected target generates
matched or shadowed candidates across the bounded seed gate. The first
holdout draft correctly exposed the undeclared `drinks` number and the
duration-bearing clause; after representing both premises, the final
DEV-train and DEV-holdout diffs are neutral.

The complete gate is green: 4,029 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; both
before/after diffs are neutral; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0,
30/0, 9/0, and 6/0; FOLIO makes zero commitments; and lint has zero errors
with two known warnings. No protected TEST look was spent.

The seventh batch reconciles five live reviews around possessive ratios and
elided mass relations:

- both affine and non-affine possessive ratios are split into explicit count
  and mass siblings. Count standards require a declared plural non-mass noun
  plus `count_quantity_delta`; mass standards require a declared singular
  `mass_quantity_noun` plus `mass_quantity_delta`;
- `possession_state` excludes copulas and unrelated event verbs from the
  possessive ratio frame. `nonunit_multiplier` excludes adverbial `once`
  structurally, without a multiplier word list in Python;
- `distinct_from_owner` compares the subject with the possessed noun's owner,
  closing the self-comparison that ordinary lemma-based `distinct` cannot
  see. Availability, ordinary generation, locked bindings, matcher premises,
  and explanations all share the new predicate;
- the standard-elided mass rule inherits the full rule's sale/remnant and
  preposition/object compatibility checks, while both refuse the declared
  prepositional-frame verb class on their unframed surfaces; and
- the common `WHO needs N fewer/more PLURAL than WHO` surface gets a dedicated
  comparative-need premise. It retains `need_premise` goal semantics and does
  not relax the generic quantitative-object verb boundary.

The first split produced one deliberate gate failure: requiring the affine
offset to be standalone dropped the established
`$50 more than twice Cecil's money` buyer. The harm-ordered snapshot identified
exactly `bacb0d512ef7`; retaining the original number slot's support for both
bare and explicitly measured offsets restored it through the mass sibling.
The final GSM8K train and holdout diffs are neutral.

All five live reviewed targets retest `absent`, while the corrected
comparative-need sentence and valid count/mass neighbours match. Curated now
contains 98/98 selectable premise rules. The fold contains 298 successful
generation events, five live reviews, and no failures under the current
fingerprint; rule coverage is 3 never-generated, 93
generated-but-unreviewed, and 2 reviewed.

The complete gate is green: 4,069 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0; both
before/after diffs are neutral; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0,
30/0, 9/0, and 6/0; FOLIO makes zero commitments; and lint has zero errors
with two known warnings. No protected TEST look was spent.

The eighth batch reconciles the four latest live reviews:

- the affine item-clause relation requires a counted currency offset, the
  complete definite frame, a `mass_currency_noun`, and a mass-compatible
  direction. Generic `money` moves to `core-english`; mined packs extend its
  category domains without owning the common word;
- fractional delta relations split into disjoint count and mass siblings.
  The count sibling requires a declared plural non-mass measure and count
  direction; the mass sibling requires a declared mass measure and mass
  direction. Both share agreement, quantitative-verb, distinct-standard, and
  optional PP compatibility premises;
- the anaphoric much/many siblings require overt `as`/`that`/`this` and use
  inspectable `unbound` continuations to refuse explicit comparison
  standards. The targetless reviewed sentence `Mary gets twice as many.`
  matches the intended anaphoric rule;
- implicit plural surfaces inherit the noun sense plus only non-noun senses
  licensed by a category declaration on that plural surface. This removes
  the fabricated verb reading from `cans` while preserving explicitly
  licensed readings such as price-relation `costs`; and
- fact cards retain an unambiguous authored emit expression and its resolved
  slot bindings. The Designer presents the template and substitutions under
  “How this fact was derived,” and review snapshots preserve that explanatory
  metadata without including it in fact identity.

The first benchmark pass found one semantic safety failure:
`arithmetic/anaphoric-multiplier-standard-many` correctly represented a
previously unaccounted `twice as many`, after which a base ask ignored the
question's trailing `originally` and returned a current qualified anchor.
A dedicated `originally` start-state ask now invokes the existing event
inversion. If same-holder, same-measure events carry a different explicit
qualifier, the consumer declines: the current scalar qualifier field cannot
prove whether those modifiers are nested or disjoint. This preserves the
valid anaphoric premise rather than narrowing it to benchmark sentence ends.

Both malformed reviewed surfaces retest `absent`; the targetless anaphoric
surface and comparative-need sentence now match their intended rules.
Curated contains 99/99 selectable premise rules and 152 reachable lexicon
identities. The live fold contains 314 successful generation events, four
reviews, and no failures under the current fingerprint; rule coverage is 1
never-generated, 95 generated-but-unreviewed, and 3 reviewed.

The complete gate is green: 4,103 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train remains 104/0 with a neutral diff and DEV-holdout moves
from 40/0 to 41/0 with one solve, no break, and no new wrong commitment.
ASDiv, SVAMP, MAWPS, and SciBench are 44/0, 30/0, 10/0, and 6/0; FOLIO makes
zero commitments; and lint has zero errors with two known warnings. No
protected TEST look was spent.

The ninth batch reconciles five live reviews through four reusable premises:

- an item-elided comparison conjunct either has no location contexts or has a
  compatible context on both conjuncts. `same_presence` exposes that pairing,
  and the unframed surface refuses the separately declared
  frame-prepositional verb class;
- a located existential requires a referential place compatible with its
  preposition. Article-bearing and possessive locations remain available to
  the matcher, while deterministic generation retains its grammatical
  definite and possessive forms;
- the full, item-elided, and affine fraction-`many` rules require explicit
  standards to be referential quantity holders. Common noun standards need
  definiteness, productive index labels such as `team A` provide structural
  definiteness, while `non_quantity_holder` excludes units such as `inch`;
  and
- the optional context in `fraction-as-much` uses the same authored
  preposition/noun compatibility relation as its quantitative siblings.

The exact five reviewed targets are absent, while context-free and paired
conjuncts, grammatical existentials, definite common-noun standards,
proper-name standards, and compatible mass contexts remain
matcher-confirmed. Every affected rule form generates only matched or
shadowed candidates over sixteen deterministic seeds. The resulting optional
shape is preregistered at 52 rules, 126 optional groups, 33 nested groups, and
maximum depth three.

The full synthetic and cross-corpus gates preserved three existing neighbours
by completing the same general contracts: the mined `quantity_location`
extension now includes the already-tested `office` and ASDiv's valid `school`,
while the referential matcher recognizes article-bearing noun phrases and
productive index labels on common-noun entities such as `team A` and `jar B`.
The label case uses parser structure already retained in relation identity
rather than a surface-specific exception.

The append-only fold now contains 338 successful generation events and 126
review rows folding to five live reviews. Rule coverage is 1 untouched, 93
generated-but-unreviewed, and 5 reviewed; filler coverage is 36 untouched, 96
generated-but-unreviewed, and 20 reviewed. There are no current-fingerprint
failures. Curated remains 65/65; GSM8K DEV-train and DEV-holdout remain 104/0
and 41/0 with neutral before/after diffs. No protected TEST look was spent.

The complete gate is green: 4,116 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

The tenth batch closes both open existential reviews through explicit
continuation ownership:

- the located rule had already rejected `There are 40 fish of rabbit.`, but
  the bare sibling still accepted the shorter `There are 40 fish` prefix.
  Optional preposition/conjunct sentinels plus `unbound` now make a failed
  longer continuation decline rather than produce a partial fact;
- a new `quantity_container` category preserves valid container-content
  partitives such as `30 boxes of apples` and `15 shelves of boxes`. The
  condition is activated only when the `of NOUN` tail binds, and arbitrary
  item heads such as `fish` cannot use it; and
- both items in the conjoined existential refuse `mass_measure`, so
  `There are 14 hamsters and 40 pounds.` cannot represent a weight amount as
  a second entity population. The bare sibling's conjunct sentinel also
  prevents a silent first-conjunct-only reading.

DEV witnesses completed `quantity_location` with `bowl`, `class`,
`classroom`, `farm`, and `party`; `class` alone receives the independently
declared bare-PP license needed by idiomatic `in class`. These pack-owned
members preserve valid located, ratio, and distributive classes without
admitting either reviewed surface.

Both current reviewed sentences now have no existential-rule match. Valid
bare, conjoined, located, distributive, and container-partitive neighbours
remain matcher-confirmed, and the changed rules generate only matched or
shadowed candidates over the bounded seed gate. The optional profile is now
53 rules, 129 groups, 33 nested groups, and maximum depth three.

The live append-only fold contains 351 successful generation events and 131
review rows folding to two reviews. Rule coverage is 1 untouched, 96
generated-but-unreviewed, and 2 reviewed; filler coverage is 33 untouched, 114
generated-but-unreviewed, and 5 reviewed. There are no current-fingerprint
failures.

The complete gate is green: 4,124 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

The eleventh batch reconciles the final live comparison review as a layered
declarative boundary:

- explicit comparative subjects and standards are complete references. Bare
  plurals remain valid measured classes, but a floating singular common noun
  does not become an entity merely by occupying the slot;
- `quantity_event_verb` groups the existing acquire/loss polarity families,
  and `quantity_event_participant` admits proper actors through pack-owned
  noun membership. Proper names and their resolved pronouns remain
  structurally valid without lexical enumeration;
- `verb_role_compatible.allow_plural_class` distinguishes an actor standard
  from an alternative measured class, preserving ordinary `nuts as bolts`
  comparisons without admitting singular `as pencil`;
- `in`, `on`, and `at` use separate compatible location subclasses, so a
  general locative label no longer makes every preposition/place pair valid;
  and
- the DEV gate identified two legitimate lexical neighbours. The mined
  `quarter` entry now owns its `quarters` morphology, and `Bill` uses a
  pack-declared `bare_entity_reference` through the referential matcher's
  existing category escape hatch. Neither repair introduces a surface branch
  in Python; and
- demonstrative anaphors and comparative anaphors have separate rules.
  `that many pounds` remains valid, while item-elided `as many`/`as much`
  rules use an immediate explicit-item sentinel and cannot claim the prefix
  of a longer comparison.

The exact reviewed sentence is absent from the complete-comparison and both
anaphoric rule families, while the participant, possession-state,
plural-class, resolved-pronoun, and location minimal pairs all pass.
The live fold contains 353 exploration events and 134 retained review rows.
The rule split changes the registry fingerprint, so no historical review is
current. Rule coverage is 2 untouched and 99 generated-but-unreviewed; filler
coverage is 33 untouched and 119 generated-but-unreviewed. The optional
profile is 55 rules, 131 groups, 33 nested groups, and maximum depth three.
There are no current-fingerprint failures.

All 4,134 tests pass in four-worker mode. Curated remains 65/65; GSM8K
DEV-train and DEV-holdout remain 104/0 and 41/0 with neutral diffs; ASDiv,
SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with two known warnings. No protected
TEST look was spent.

The twelfth batch reconciles the reviewed fractional mass comparison without
removing useful vocabulary:

- `rest` remains a mass quantity for compatible verbs, while the existing
  verb/role predicate requires spend-governed count and mass objects to be
  currency. This preserves `spends less money` and `spends fewer dollars` but
  rejects `spends less rest`;
- optional PPs on fractional delta comparisons retain declared location
  compatibility but exclude remnant prepositions. Remnant PPs remain
  available to their owning conjunct rules; and
- `proportional_delta_compatible` makes the mathematical premise inspectable:
  declared increases are unbounded, while decreases greater than 100% decline
  before a negative factor can be emitted. The compiler, matcher, generator,
  availability solver, probes, and premise cards share the same predicate.

`Cato spends nineteen tenths less rest with its remainder than your friend
Eron.` now has no target-rule match. Valid rest, currency, count, location,
and greater-than-100% increase neighbours remain matcher-confirmed. Across 32
seeds, generated mass-delta candidates remain matched and satisfy all three
new boundaries.

The live fold contains 354 exploration events and 136 review rows folding to
one live review. Rule coverage is 1 untouched, 99 generated-but-unreviewed,
and 1 reviewed; filler coverage is 33 untouched, 111
generated-but-unreviewed, and 8 reviewed. There are no current-fingerprint
failures.

All 4,149 tests pass in four-worker mode. Curated remains 65/65; GSM8K
DEV-train and DEV-holdout remain 104/0 and 41/0 with exact neutral diffs;
ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0, and 6/0; FOLIO
makes zero commitments; and lint has zero errors with two known warnings. No
protected TEST look was spent.

Batches thirteen through eighteen continued the same review-led method. They
separated trailing totals from prepositional aggregates, constrained postfix
comparisons, made extraposed-duration actors referential and role-compatible,
prevented category/member comparison overlap, narrowed distributive
quantifiers and mass-ratio remnants, split mass and plural currency change,
and separated explicit motion frequency (`as many times`) from distance
(`as far`). The detailed review IDs and individual gate records remain in
`docs/HANDOFF.md`; none of these batches changed the product loop or introduced
automatic rule mutation.

The nineteenth batch fixes the six-review snapshot that followed:

- `time` and `money` are declared non-holders for quantity subjects;
- plural remainder partitions require definite `the rest`, not bare `Rest`
  or singular `remainder`;
- temporal `times` is excluded locally from membership labels and from the
  second derived object in an elided-standard conjunct, while remaining valid
  in explicit motion-frequency comparisons;
- affine mass comparisons use `less`/`more`, never count-only `fewer`; and
- `double`/`triple` are declared predeterminers. Fourteen reviewed comparison
  rules exclude them from adverbial `as many/as much` positions while keeping
  `twice`, `thrice`, and explicit `N times`. The established affine-count
  compatibility remains accepted because removing it violated the 0-BROKE
  DEV ship gate.

The valid control `Cato buys thrice as much as my friend Aven.` remains
matched. The complete gate is 4,232 tests, curated 65/65, GSM8K DEV 104/0 and
41/0, ASDiv/SVAMP/MAWPS/SciBench 44/0, 30/0, 10/0, and 6/0, FOLIO at zero
commitments, and lint at zero errors with two known warnings. No protected
TEST look was spent.

The twentieth batch handles the six later rows in the same bounded snapshot:

- temporal `times` is a declared existential-incompatible noun but remains an
  explicit frequency measure;
- adverbial `as many/as much` rules require a non-unit multiplier, so the
  numeric value-one boundary rejects `once` generically;
- the sum-of-ages rule requires literal `the`, optional possessive-determiner
  ownership, plural `ages`, and a singular copula;
- periodic-rate subjects are referential rather than bare singular common
  nouns disguised by sentence-initial capitalization; and
- the destination-bearing fraction frame requires referential motion
  participants and a declared location measure. Mined `city` and `country`
  extend the existing location class beside the core `garden` witness.

All five invalid surfaces retest absent and the valid conjoined existential
control remains matched. The broader `amount of PLURAL` count-frame surface
is deliberately unchanged because it is an explicit existing synthetic and
DEV contract; narrowing it remains a product decision.

The complete gate is 4,242 tests, curated 65/65, GSM8K DEV 104/0 and 41/0
with exact neutral diffs, ASDiv/SVAMP/MAWPS/SciBench 44/0, 30/0, 10/0, and
6/0, FOLIO at zero commitments, and lint at zero errors with two known
warnings. No protected TEST look was spent.

The twenty-first batch folds the next 180-row bounded snapshot to three live
reviews. The valid dangling-comparative control remains matched with its
intended no-fact consumption and real missing-standard deficiency. Both
invalid specimens select `triple` through a verb slot even though the ordinary
reader deterministically commits that declared surface as a multiplier before
lexical sense selection.

The generator now treats structural numeric precedence as a generic filler
boundary: a declared number, fraction, or multiplier surface is omitted from
conflicting sense-specific lexical domains. It remains available to broad
`word` exploration and its explicit numeric domain. This removes the
unrealizable verb placement from both reviewed rules without a word-specific
Python branch, keeps ordinary verb neighbours matched, and leaves the current
106-rule / 156-identity frontier unchanged.

The complete gate is green: 4,249 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with exact neutral
diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0, and 6/0;
FOLIO makes zero commitments; and lint has zero errors with the same two known
warnings. No protected TEST or generalization look was spent.

The next 182-row scheduled snapshot adds one repeated `triple` review and one
new trailing-total review. The repeated verb placement is already excluded by
the twenty-first batch. The new `18 times in all.` specimen combines a clear
structural domain defect with an unresolved contextual-generation decision.

The clear boundary is implemented without vocabulary in the generator. When a
declared noun plural is also the declared multiplication operator marker, a
preceding count makes the ordinary number pass fold the complete surface into
a multiplier. Such a surface can never round-trip through `type: counted`, so
the counted domain now omits it. The number pass reads the multiplication
marker from the registry operator table rather than comparing a fixed English
word. Singular and ordinary-plural counted neighbours remain available, and
the 106-rule / 156-identity frontier does not change.

The same review also asks the single-sentence generator to supply a host clause
for a rule intentionally authored as a trailing tail matcher. That is not a
slot or matcher-premise correction: it requires choosing whether contextual
rules become honest blockers or whether generation gains generic multi-rule
host composition. Runtime narrowing would lose the arbitrary host clauses the
tail rule exists to cover. This plan leaves that product choice open rather
than encoding a one-rule wrapper or silently treating a matched fragment as a
full sentence.

The implemented structural boundary passes all 4,250 repository tests.
Curated remains 65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0
with exact neutral diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0,
10/0, and 6/0; FOLIO makes zero commitments; and lint retains zero errors with
the same two known warnings. No protected TEST or generalization look was
spent.

The twenty-second batch freezes the next 184-row snapshot and folds it to
seven live reviews. One addition is another already-fixed `triple` verb probe.
The other exact specimen is already blocked because its counted noun plural
is the multiplication marker, but it also reveals a separate agreement hole
that still reproduces with an ordinary counted noun.

`arithmetic/goal-need-quantity` now mirrors its comparative stated-need
sibling by declaring `number_compatible: [who, need]`. A singular proper name
therefore admits singular `needs` and the number-neutral past `needed`, but not
the plural/base form `need`. Matching, ordinary generation, locked probes, and
premise explanations share the existing generic predicate. No vocabulary,
kernel mechanism, rule availability, or reachable filler identity changes.

The exact reviewed sentence still leaves a generic learned `Predication` even
though its target premise is absent. Target-aware fold suppression would
couple runtime meaning to an authoring selection, while a global agreement
boundary on learned Predications is a separate kernel-wide product decision.
Neither is inferred from this one review.

The complete gate is green at 4,252 tests. Curated remains 65/65; GSM8K
DEV-train and DEV-holdout remain 104/0 and 41/0 with exact neutral diffs
against the prior gated snapshots; ASDiv, SVAMP, MAWPS, and SciBench remain
44/0, 30/0, 10/0, and 6/0; FOLIO makes zero commitments; and lint retains zero
errors with the same two known warnings. No protected TEST or generalization
look was spent.

The twenty-third batch freezes 186 rows and inspects the two additions,
`rev-29af767401ff4b62` and `rev-eb142f262bb84c65`. The latter is already
absent on its exact `triple` verb placement, but a normal finite verb proves
its independent magnitude defect: a part of one remainder could still bind
an improper fraction greater than one.

`fraction_within_whole: true` is now a generic opt-in qualifier on a
`type: fraction` slot. Matching and generation read the same numeric value and
admit only the closed interval from zero through one. The three
`FractionQuantity` rules that take a fraction of one finite whole—an explicit
pool, a pool pronoun, and a remainder—declare that qualifier and ordinary
subject/verb `number_compatible` premises. Improper fractions remain legal in
ratio and affine slots whose semantic domain is not one bounded whole.

The affine-frame review remains open. Same-lemma matrix/echo predicates do not
establish that the two clauses describe the same time, and English can
legitimately compare a past event against a habitual present rate. The
alternative referential/participant narrowing conflicts with a standing valid
bare-common-noun frame test. The plan therefore records rather than guesses
whether this family should model temporal alignment or retire its older common
noun widening. It also leaves the remnant article question open because the
broader pool rule has an established reviewed-valid bare-noun neighbor.

All 4,264 tests pass in four-worker mode. Curated remains 65/65; GSM8K
DEV-train and DEV-holdout remain 104/0 and 41/0 with exact neutral diffs;
ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0, and 6/0; FOLIO
makes zero commitments; and lint has zero errors with the same two known
warnings. No protected TEST or generalization look was spent.

The twenty-fourth batch freezes 189 review rows and inspects the three
additions: `rev-bfb4d8122bfd4d4f`, `rev-64e0fe60e538488b`, and
`rev-6cc6c869e71e4f49`.

The goal-desire and leading-existential targets are already absent. The
existing structural-numeric precedence boundary excludes a declared numeric
homograph from a sense-specific verb slot, while the multiplication-marker
boundary excludes `COUNT MARKER` from a composed counted-noun domain. Locked
generation verifies both mechanisms, so neither review justifies a duplicate
rule edit. The learned `Quantity` that survives the goal-desire sentence is a
separate kernel-wide decision: target-aware fold suppression would make
authoring state affect runtime semantics, while interpreting a multiplier
goal requires an explicit event representation.

The affine-fraction review also contains an independent, reproducible zero
magnitude. With an ordinary finite verb, `zero sixths` matched and emitted a
factor-zero Relation, making the comparison standard irrelevant. The new
`fraction_positive: true` token qualifier is shared by matcher, availability,
normal and locked generation, and premise explanations. Every fraction-valued
Relation rule and both percent-change rules declares it—fourteen rules in
total. Zero remains legal in `FractionQuantity` and partition facts, and the
qualifier has no upper bound, so positive improper ratios and affine
coefficients remain available.

The complete gate is green at 4,271 tests. Curated remains 65/65; GSM8K
DEV-train and DEV-holdout remain 104/0 and 41/0 with exact neutral diffs;
ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0, and 6/0; FOLIO
makes zero commitments; and lint retains zero errors with the same two known
warnings. No protected TEST or generalization look was spent. The affine-frame
tense policy, learned-fold suppression/representation, contextual total-host
composition, universal remnant definiteness, and `amount of PLURAL` remain
explicit product questions.

The twenty-fifth batch freezes 195 review rows / 155,416 bytes with SHA-256
`0ed974807ffe3070504d9537a13a03b16433e4d4c7ef4e5ddebc58e9bdc77969`
and folds them to eighteen live reviews. The prior sixteen preserve their
gated behavior. The two additions close two complete guard-coverage classes:

- all five anaphoric quantity-relation siblings now subtract the existing
  `non_quantity_holder` category from `who`. The reviewed
  `Time dropped thrice as much.` target is absent, and proper-name minimal
  pairs remain matched. The unrelated generic learned `Predication` still
  survives, so fold suppression remains an explicit kernel-wide product
  question rather than becoming target-aware authoring behavior; and
- all five adverbial age-ratio siblings subtract the existing
  `predeterminer_multiplier` category from `k`. `double`/`triple` remain
  available before noun phrases such as possessive ages, while `twice`,
  `thrice`, and explicit `N times` remain available in comparative/equative
  age frames. The separately documented affine-count compatibility exception
  is unchanged.

Both exact reviewed targets retest absent, both locked invalid probes fail at
filler selection, and every synthetic valid neighbour remains matched. The
106-rule / 156-identity mechanical frontier is unchanged.

The complete gate is green at 4,284 tests. Curated remains 65/65; GSM8K
DEV-train and DEV-holdout are 104/0 and 41/0; ASDiv, SVAMP, MAWPS, and
SciBench are 44/0, 30/0, 10/0, and 6/0; FOLIO makes zero commitments; and
lint has zero errors with the same two known warnings. All diffs have 0 BROKE
and 0 DECL-to-WRONG; the older R24 holdout and MAWPS baselines show only the
already-gated one-item solves. No protected TEST or generalization look was
spent.

#### Core exploration-vocabulary expansion — complete

The 106-rule premise frontier was mechanically complete but lexically narrow:
only four core animate common nouns, three mass-quantity nouns, three
quantitative locations, and three colour attributes were available. Core now
adds 25 ordinary, globally unclaimed exploration identities across six
explicit domains: countable objects and produce, one animal, people,
quantitative locations, mass materials, and colours. Count forms declare
their plurals in the lexicon; semantic suitability remains in YAML categories
such as `animate`, `quantity_event_participant`, `mass_quantity_noun`,
`non_quantity_holder`, `quantity_location`, `color_attribute`, and
`ripenable_noun`.

This is a vocabulary increment, not a generator exception. There is no word
list or preference in Python, and broad lexical senses do not bypass the
existing compatibility premises. Exact tests cover morphology, category
boundaries, count and mass comparisons, locative and colour surfaces, locked
generation, and the complete reachable identity set. The curated frontier is
now 106/106 supported rules and 181 reachable identities.

Candidate selection was precision-led. Quarantined or already owned words
were excluded. An initially considered `bead` entry made one GSM8K
DEV-holdout item commit to an incomplete initial quantity (40 instead of 10),
so it was removed rather than accepting coverage at the cost of precision.
With the final vocabulary the complete suite, inspectable arithmetic corpora,
FOLIO, and lint gates are green; no protected TEST or generalization look was
spent.

#### Twenty-sixth review reconciliation — complete

The bounded 218-row review snapshot folds to three live reviews. The valid
remainder-membership control stays matched, and the earlier same-measure
demonstrative-conjunct review remains an explicit product-semantics question.
The one new actionable review is
`rev-61f4aadb65cc4df4`, whose full conjunct comparison admitted a non-motion
common-noun subject and an incompatible optional PP.

The correction reuses two existing declarative predicates rather than adding
word memberships. Every conjunct quantity sibling applies
`verb_role_compatible` for `motion_comparison_verb` and
`motion_participant` to its common-noun subject; the full explicit-standard
rule applies the same boundary to its standard. The full rule also applies
the existing `attribute_compatible` predicate to its optional PP. The exact
review is now absent, while synthetic motion-participant and compatible-PP
minimal pairs remain matched. The anaphoric conjunct deliberately retains its
established broad temporal `by day`/`by night` adjunct contract.

Adding `book` globally to `non_quantity_holder` or `travel` globally to
`non_quantity_object_verb` would reject legitimate page holdings and distance
quantities. The separate question—whether motion comparisons that state an
item should require a declared distance/frequency measure—remains open until
that measure-role union is specified and audited as a product boundary.

The complete gate is 4,321 tests, curated 65/65, GSM8K DEV 104/0 and 41/0,
ASDiv/SVAMP/MAWPS/SciBench 45/0, 30/0, 11/0, and 6/0, FOLIO at zero
commitments, and lint at zero errors with two known warnings. All isolated
pre-change/current diffs are neutral. No protected TEST or generalization
look was spent.

#### Twenty-seventh review reconciliation — complete

The bounded 219-row / 169,703-byte review snapshot (SHA-256
`323869c3e9a3cdbec0c8cc732d0d8183d686c103854f30caef946da757e8554c`)
folds to four live reviews. The new valid future-age review confirms the
target rule and its subtraction semantics, but exposes repeated unknown-word
noise on required literal tokens. The same class was previously observed on
the past and temporal-ratio siblings.

The three affected generic English words—`ago`, `be`, and `old`—now live in
`core-english` beside the arithmetic grammar that requires them. This is a
declarative ownership move, not a generator or deficiency-reporter exception.
The existing `be ∈ non_event_verb` membership moves with the infinitive; the
mining pack retains `been` and `being` as its extension vocabulary. An
in-memory legacy reconstruction proves every combined GSM8K registry field
except the ownership-derived fingerprint is unchanged.

Curated gains exactly the three newly core-owned identities, moving the
frontier from 181 to 184 while keeping all 106 premise rules selectable.
Synthetic future, past, and temporal-ratio age frames match without unknown
deficiencies; a nonce-tail minimal pair remains unknown and does not match.
The complete gate is 4,327 tests, curated 65/65, GSM8K DEV 104/0 and 41/0,
ASDiv/SVAMP/MAWPS/SciBench 45/0, 30/0, 11/0, and 6/0, FOLIO at zero
commitments, and lint at zero errors with the current two warnings. All
isolated before/after diffs are neutral. No protected TEST or generalization
look was spent.

#### Twenty-eighth review reconciliation — complete

The bounded 222-row / 177,650-byte review snapshot (SHA-256
`d69f11c17f6c0d8720537f80d179a951be793805a3440639b852a8c57063fb49`)
folds to seven live reviews. Two new invalid surfaces expose complete existing
grammar boundaries:

- the demonstrative `that/this many|much` quantity pro-forms accept adverbial
  multipliers such as `twice`, `thrice`, and explicit `N times`, but subtract
  the declared noun-phrase `predeterminer_multiplier` class. The same premise
  applies to the standalone `many`, standalone `much`, and conjunct pro-form
  rules. `double`/`triple` remain available before actual noun heads such as
  `the amount` and `the number`; and
- the comparative stated-need rule uses a noun-rooted item slot with
  `same_number: [n, item]`. One rule now generates and matches both
  `1 fewer shopper` and `2 fewer shoppers`, while rejecting both mismatches.

The exact predeterminer and count-disagreement reviews now retest absent and
cannot be recreated through locked generation. The earlier exact
`double that many` conjunct also becomes absent for the same independent
surface boundary, while the `twice that many` minimal pair stays matched; its
same-measure addition semantics remain a product question.

The improper-fraction increase review stays matched. A standing synthetic
contract deliberately accepts positive improper fractions for unbounded
proportional increases, so choosing between a proper-fraction surface limit
and a different realization is an explicit product decision. Likewise, the
generic learned Predications left after the two target rules decline remain
the existing kernel-wide fold-policy question, not target-aware authoring
behavior.

All 4,334 tests pass in four-worker mode. Curated remains 65/65; GSM8K
DEV-train and DEV-holdout remain 104/0 and 41/0; ASDiv, SVAMP, MAWPS, and
SciBench remain 45/0, 30/0, 11/0, and 6/0; FOLIO makes zero commitments; all
before/after diffs are neutral; and lint has zero errors with two known
warnings. No protected TEST or generalization look was spent.

#### Additive elided comparison — complete

Two premise rules cover the ordinary state/ownership continuations
`Mary has 5 more apples` and `Mary has 5 more`. The first states the measure
and omits the comparison standard; the second omits both. They emit the
ordinary Relation fact with `$elided:standard$`, and the generic relation
synthesizer resolves the omission only when one earlier Quantity belongs to
a different holder. In the fully elided form that same fact supplies the
measure. Zero or multiple candidates, self-reference, and a derived negative
quantity produce no new Quantity rather than guessing.

Sentence-wide absence premises keep explicit `than` clauses and conjunctions
with their existing fuller rules. Both new rules require a
`possession_state` verb, excluding both event changes and copular generations
such as `Mary is 5 more apples`. This is the critical semantic boundary found
by cross-corpus profiling:
`Mary buys/gets/earns 5 more` changes Mary's own quantity and must not be read
as an omitted comparison with another holder. A broad verb draft produced
seven wrong ASDiv commitments and two wrong MAWPS commitments; the state-only
form removes all of them.

The final rule pair adds one clean GSM8K DEV-train solve: `Ellie has 8 pairs
of shoes. Riley has 3 fewer.` now supports the later total. The live
generation frontier is 111/111 rules with 189 reachable identities after the
logic-arithmetic bridge joined the curated project.
All 4,354 tests pass; curated is 65/65 twice; GSM8K DEV-train and DEV-holdout
are 105/0 and 41/0; ASDiv, SVAMP, MAWPS, and SciBench are 45/0, 30/0, 11/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with the same
two warnings. No protected TEST or generalization look was spent.

#### Variadic exact-name combined totals — complete

Ask resolutions can now preserve a list of templated scalar values. The first
consumer-facing use is `holders`: one variadic `how many ... together` ask
captures a coordinated span and resolves the exact names stated in the
question. Every segment must be one name; every conjunction must belong to
the pack-declared `holder_list_conjunction`; and the final two names must be
overtly conjoined. Comma-only lists, disjunctions, and arbitrary noun phrases
therefore stay outside the ask. The combined consumer validates at least two
non-empty unique names and sums precisely their independently resolved totals.
It never expands an explicit list by enumerating other same-measure holders.
Historical `a`/`b` named pairs remain supported, while pronoun totals retain
their intentionally different enumeration behavior.

The ordinary serial-comma and non-serial-comma forms share one ask because
punctuation is already a skippable reading unit. Synthetic tests
pin three-, four-, and five-holder lists, the extended relation-chain total,
exact scope in the presence of an unasked holder, decline on a missing holder,
decline on a repeated name, rejection of comma-only/disjunctive scope, and
unchanged two-name behavior. The supplied Seattle/London/Manchester/Brighton
question returns 111 after deriving 72, 24, 12, and 3.

GSM8K DEV-holdout gains two correct three-holder totals and no wrong
commitments; a third matching question remains declined because one named
holder is unresolved. All 4,363 tests pass; curated is 65/65 twice; GSM8K
DEV-train and DEV-holdout are 105/0 and 43/0; ASDiv, SVAMP, MAWPS, and
SciBench are 45/0, 30/0, 11/0, and 6/0; FOLIO makes zero commitments; and
lint has zero errors with the same two warnings. No protected TEST or
generalization look was spent.

#### Strict-positive and lexical-boundary generation modes — complete

The Designer now exposes two explicit experiments. `Strict positive` draws
every filler from the target rule's declared slot domain and only returns an
ordinary round trip that retains the target. `Lexical boundary probe` widens
exactly one active category-gated slot to that category's declared root sense,
or one narrow typed verb/modal slot to its declared parent type. It preserves
part of speech, counted and possessed structure, grammatical number,
referential form, optional branches, and every cross-slot predicate.

Each boundary candidate records the relaxed slot, selected surface and
identity, strict requirement, and broader domain. Its premise inspector marks
that row `relaxed`; an absent target is an expected observation rather than a
failed generation. Reviews, hypotheses, and pinned retests retain the mode and
relaxation. Minimal-pair and focused-lexicon controls remain strict-only, and
boundary probes never write success or failure exploration events, so the
coverage frontier continues to mean “generated under every declared premise.”

Generation latency is reduced without changing that contract. Bounded
in-memory catalogs cache structural filler domains, rule availability, and
compatible lexical placements by registry fingerprint plus project fixtures.
The compatible-placement search deduplicates exact measure keys before solving
`distinct_measure`, and the Designer status endpoint omits placement detail it
does not display. Any semantic YAML edit changes the fingerprint and therefore
uses fresh indexes.

The GSM8K project now declares its own open proper-name generation fixtures.
All 108 loaded premise rules are mechanically selectable and each has a
deterministic strict matcher-retained specimen. The flat-discount rule now
generates the currency surface it actually accepts, and structurally ambiguous
entity-before-counted surfaces are realized with project names so the reader
cannot condense the intended holder into the following noun phrase. The
cumulative generator version is `g6-strict-boundary-modes`.

Validation on 2026-08-06 passes all 4,379 repository tests. Curated remains
65/65; GSM8K DEV-train and DEV-holdout are 106/0 and 43/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 45/0, 30/0, 11/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with two known warnings. No protected
TEST or generalization look was spent. On the local GSM8K project, cold rule
availability builds in 1.587 seconds and repeats in 0.0008 seconds; a complete
strict round trip over all 108 rules takes 4.744 seconds.

#### Twenty-ninth review reconciliation — complete

The first GSM8K-project review ledger snapshot contains two rows / 2,022
bytes, SHA-256
`28a1b2ad883fe0a35aad414167e8ff8762a9bb24e62ccb114d2ca99608cba7b6`.
Both strict candidates were mechanically matched but semantically invalid:
one treated `millions` as a singular holder and mixed `libraries` with
`afternoons`; the other treated `joule` as an agent that could `afford`
`parents` and possess a `sister`.

This batch replaces the open-ended holder blacklist for the affected ratio
family with a positive role premise. `common_noun_cat` qualifies a
`type: entity` slot: names and resolved pronouns retain their ordinary path,
while a common noun must belong to the named category. The arithmetic rules
use the pack-declared `quantity_holder` category on their actual subject.
Their standard is intentionally not narrowed because it is polymorphic in the
existing model and may name a measure class (`buttons`, `crayons`, or
`angelfish`) rather than a holder. Existing evidence admits people, motion
participants, places, containers, name-homograph labels, books, stores,
person-groups, and vehicles. A new noun remains outside until a pack declares
its holder role.

The generator applies the same qualifier in availability, strict, locked,
minimal-pair, compatible-placement, and explanation paths. Boundary mode
widens it to the noun root as exactly one recorded lexical relaxation, so a
reviewer can still test the rejected `joule` class deliberately without
polluting strict coverage.

The new `same_category_membership` predicate requires several slots to agree
on whether they belong to one category. The conjunct quantity siblings use it
with `timeperiod`: `libraries/books` and `mornings/afternoons` pass, while
`libraries/afternoons` fails. Matcher, generator feasibility and
forward-checking, lexical probes, premise explanations, source evidence, and
registry validation share that declarative contract.

The remaining fixes are lexical data: `million/millions`, `measure/measures`,
and `afford/affords` now carry one lemma and explicit grammatical number;
`measure`, `measured`, `measures`, `afford`, and `affords` join the existing
`non_quantity_object_verb` boundary because those transitive readings do not
assert possession or acquisition of the object count.

The possessive appositive receives its own conditional role premise rather
than being inferred from the holder gate. When `appos_role` binds, `who` must
belong to `quantity_event_participant` or use the predicate's explicit
proper-name alternative. A store can still hold a quantity in the plain
ratio sentence, but cannot acquire `its sister Aven`; people, animals, and
proper names retain the appositive construction.

Both exact reviews retest absent. Synthetic controls preserve proper-name,
pronoun, declared common-holder, measure-class standard, ordinary-count
conjunct, temporal-conjunct, and name-homograph behavior. The final gate is
4,391 tests; curated 65/65; GSM8K DEV-train/holdout 106/0 and 43/0;
ASDiv/SVAMP/MAWPS/SciBench 45/0, 30/0, 11/0, and 6/0; FOLIO zero
commitments; lint zero errors and two known warnings. No protected TEST or
generalization look was spent.

#### Imperative single-dimension asks — complete

`ask/imperative-single-dimension` recognizes “Calculate the age of X” and the
same `compute`/`determine` cue family. A `dimension_noun` names what is being
measured; the single-entity consumer opts into declared dimension resolution
and then reuses its established holder fold. Resolution is scoped to the
explicit holder, so another entity's unrelated time, mass, length, or currency
unit cannot create ambiguity or supply an answer. Zero or multiple compatible
measures for that holder still decline.

The form is declaratively generic across age, height, weight, balance, and
other pack-owned dimension nouns. It remains distinct from the combined and
average imperative asks. A coordinated holder tail is captured and declined,
preventing a prefix match from answering only the first name.

Validation on 2026-08-06 passes all 4,431 tests and curated 65/65 twice.
GSM8K DEV-train improves from 107/0 to 108/0, solving one previously declined
item; DEV-holdout remains 43/0. ASDiv, SVAMP, MAWPS, SciBench, and FOLIO are
neutral with zero broken or decline-to-wrong transitions. Lint has zero errors
and the same two warnings. No protected TEST or generalization look was spent.

#### Thirty-first review reconciliation — complete

The batch froze eight active invalid reviews from the 36-row, 29,787-byte
GSM8K ledger, SHA-256
`ef6a1629ddcaee8e0c8555af767cba7eb928a74646a82b6642316fccb75104f0`.
Every exact target matched before the change. One possessive-standard sentence
also matched the shorter elided-standard fallback, so rejecting only the long
rule would have left the incorrect commitment alive.

The affected older rules now use the same positive common-noun roles as their
newer siblings. Conjoined count offsets require count directions and plausible
holders; anaphoric, percentage-change, elided-comparison, and periodic-rate
subjects require declared quantity holders; event-specific subject and object
roles use the existing generic verb-role predicate. The possessive kinship
standard is person-denoting, and the elided-standard continuation sentinel
also recognizes a possessive determiner followed by a noun.

`fraction-of-pool` now states its documented definite-pool grammar directly:
the article is required and consumed, the matrix verb is finite, and declared
encounter verbs require a plausible participant object. Pack data normalizes
the invariant unit symbol `ft` to `foot`, maps `drinking` to the lemma `drink`,
declares `machine` as a quantitative holder, and declares `quart` as a unit
rather than a holder. The existing strict round-trip check already rejected
the reviewed `merry-go-round` to `round` partial identity; the positive role
domain now prevents that filler from being selected for this rule in strict
generation.

All eight exact reviews now retest absent, and 11 focused boundary/minimal-pair
checks preserve valid neighbours. While validation ran, the live reviewer
appended one tombstone per row; the resulting append-only ledger is 44 rows /
30,891 bytes, SHA-256
`ffe79bdd98cda2247fec5344058a5030b562c253899d5b222feb1199f9cdb5c0`.

The complete synthetic gate passes all 4,450 tests. Curated is deterministic
at 65/65; GSM8K DEV-train and DEV-holdout remain 108/0 and 43/0; ASDiv,
SVAMP, MAWPS, and SciBench remain 45/0, 30/0, 11/0, and 6/0; FOLIO makes zero
commitments. Every before/after diff is neutral with zero breaks and zero
decline-to-wrong transitions. Lint has zero errors and one known warning. No
protected TEST or generalization look was spent.

#### Logic–arithmetic L2 coordinated roles — complete

The curated project now exposes all four narrow `logic-arithmetic` premise
rules in Generate mode. A binary coordinated named subject plus one finite
verbal PP emits a `VerbalRelation` for each conjunct. A pack-owned,
source-indexed table licenses exact verb/preposition-to-role derivations and
preserves the PP object; the generic synthesizer contains no project words.
The pattern explicitly satisfies the verb's group-subject obligation without
claiming that either conjunct is the sole grammatical subject.

The generated sentence `Aven and Mary teach at the university` round-trips to
its target rule. Disjunction, repeated names, singular agreement, coordinated
objects, and unlicensed role mappings remain negative controls. Combined with
the L1 exact quantified-quantity bridge, the three-sentence university-teacher
example answers 20 for Bob.

The complete gate is 4,459 tests and curated 67/67 with 112/112 premise rules
selectable. GSM8K DEV remains 108/0 and 43/0; ASDiv/SVAMP/MAWPS/SciBench are
45/0, 30/0, 11/0, and 6/0; DIFG is 75/0; and FOLIO makes zero commitments.
Every answer-level before/after diff is neutral. COGS and PMB inspectable
slices retain 100% projected-edge precision, lint has zero errors, and no
protected TEST or generalization look was spent.

#### Logic–arithmetic L3 declared class refinement — complete

`ClassRefinement` now gives the reasoning layer a first-class, inspectable
class edge. The pack-declared `refining_modifier` category licenses one exact
leading-modifier removal, preserving every remaining restriction:
`head teacher at university → teacher at university`. The same derivation may
materialize a positive superclass `Membership` or `Atom`, but never predicates
the modifier itself and never widens a subclass-wide numeric universal.

This edge is separate from both intersective predicate decomposition and the
ordinary right-headed noun-compound fold. `former teacher`, `fake teacher`,
undeclared compounds, and negative class facts expose no refinement edge. The
modifier declaration remains linked to its YAML source for Designer
inspection.

The complete gate is 4,465 tests and curated 67/67 with 112/112 premise rules
selectable. Every L2-to-L3 answer-level DEV diff is neutral; GSM8K remains
108/0 and 43/0, ASDiv/SVAMP/MAWPS/SciBench remain 45/0, 30/0, 11/0, and 6/0,
DIFG remains 75/0, and FOLIO makes zero commitments. COGS and PMB inspectable
slices retain 100% projected-edge precision, lint has zero errors, and no
protected TEST or generalization look was spent.

#### Logic–arithmetic L4 quantified additive refinements — complete

`QuantifiedAdjustment(cls, measure, offset, verb)` now represents an elided
class-wide comparison such as “All head teachers have 5 more students”. The
reader preserves the complete compound class and signed offset; it no longer
lets the older entity-relation rule reinterpret that sentence as an event.

Ordinary and adjusted universal inheritance share one monotone materializer.
For an exact refining-class member, it suppresses the inherited baseline and
emits one adjusted `Quantity` only when one compatible base universal survives
the class, scope, measure, and verb checks. The proof log names both premise
rules. No base, an undeclared refinement, multiple compatible bases, a negative
result, or a contradictory explicit state declines rather than selecting an
amount. Non-members retain their ordinary inherited base.

The non-hypothetical composition now answers 25 for Bob while Mary retains 20.
The new premise rule is available in Generate mode, bringing the curated
frontier to 113/113 rules with the same 189 reachable identities.

The complete gate is 4,476 tests and curated 68/68. Every L3-to-L4 answer-level
DEV diff is neutral; GSM8K remains 108/0 and 43/0, ASDiv/SVAMP/MAWPS/SciBench
remain 45/0, 30/0, 11/0, and 6/0, DIFG remains 75/0, and FOLIO makes zero
commitments. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision with zero incorrect graphs. Lint has zero errors. No
protected TEST or generalization look was spent.

#### Logic–arithmetic L5 local hypotheses and person deixis — complete

Conditional clauses promoted from the current question now retain a distinct
question-assumption scope. That scope is visible on the Reading, direct and
derived fact provenance, diagnosis, engine trace, and Designer trace. It is
owned by one fresh solve and cannot become a later solve's asserted knowledge.

Person deixis uses the existing typed strict-dominance resolver. Ordinary
multi-name discourse remains deliberately flat because RuleKit has no
gender/person compatibility model. In a question-local assumption context,
sentence distance is available: the re-mentioned Bob may strictly dominate an
older Mary mention, while two names in the same nearest assumption sentence
still tie and decline. This boundary avoids making unsafe recency guesses in
ordinary prose while completing the intended hypothetical composition.

The full motivating question now answers 25 and joins the curated suite. The
complete gate is 4,481 tests and curated 69/69 with the unchanged 113/113
premise-rule frontier and 189 reachable identities. Every L4-to-L5 answer-level
DEV diff is neutral; GSM8K remains 108/0 and 43/0, ASDiv/SVAMP/MAWPS/SciBench
remain 45/0, 30/0, 11/0, and 6/0, DIFG remains 75/0, and FOLIO makes zero
commitments. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision with zero incorrect graphs. Lint has zero errors. No
protected TEST or generalization look was spent. L6 generation and review is
the next logic–arithmetic increment.

The post-L5 marker-parity follow-up adds the valid two-token “all together”
tail to the variadic exact-name combined ask. It uses the existing declared
total quantifier/marker categories, preserves the exact holder list, and does
not admit `all total` or `alltogether`. The cumulative gate is 4,484 tests and
curated 70/70; all standing answer DEV diffs are neutral, COGS/PMB retain 100%
edge precision with zero incorrect graphs, lint has zero errors, and no
protected look was spent.

The next post-L5 ask follow-up adds exact distributive answers without
inventing positional meaning. “How many students do Bob and Mary each have?”
returns a `series` whose rows retain entity, canonical measure, and numeric
value. The `per-holder` consumer reuses the existing exact-list validation and
complete holder folds from `combined`, preserves source order, excludes
unasked holders, and declines rather than returning a partial series. A narrow
postpositive category accepts `each` but rejects the invalid `every` sibling.
The Designer renders labelled rows using the captured measure surface, the API
remains JSON-native, and the benchmark judge compares labels and values rather
than list position. The cumulative gate is 4,491 tests and curated 71/71; all
frozen answer DEV diffs are neutral, COGS/PMB inspectable slices retain 100%
edge precision with zero incorrect graphs, lint has zero errors and the known
single warning, and no protected look was spent.

The marker-position sibling adds “have each”, “have individually”, and
“individually have” without changing the result semantics. The two `each`
positions share the narrow distributive quantifier category. Core-English now
owns `individually` as an adverb, and only the new individualizing-adverb
category can fill its two positions; undeclared alternatives remain safe
declines. The reachable frontier is therefore 190 identities. The cumulative
gate is 4,493 tests and curated 71/71; all frozen answer DEV diffs are neutral,
COGS/PMB remain at 100% inspectable edge precision with zero incorrect graphs,
lint has zero errors and its known single warning, and no protected look was
spent.

The core-English adposition increment broadens the review frontier without
claiming that every recognized marker already has useful semantics. Broadly
useful single-word senses move to core, eight multiword prepositions condense
through one lexicon-driven analyzer pass, and the generator can realize those
phrases in preposition slots. A declarative `adposition_roles` table licenses
exact spatial, temporal, accompaniment, instrument, means, manner, cause, and
purpose `VerbalRelation` facts from compatible preposition, object, and
governing-verb categories. Unsupported or multiply licensed readings emit no
typed relation. Arithmetic-heavy homographs such as `as`, `less`, `per`, and
`up` retain their established sense until a governed construction can add the
preposition reading without changing existing parses. The reachable frontier
is 263 identities. The cumulative gate is 4,542 tests and curated 71/71; all
frozen answer DEV diffs are neutral, lint has zero errors and its known single
warning, and no protected look was spent.

The thirty-second review reconciliation closes the eight live rows exposed by
that broader frontier and the remaining older fraction row:

- bare `be` joins the direct quantitative-object exclusion, closing the
  agreement loophole without admitting an inflected copula into a possessive
  comparison frame;
- `motion_comparison_measure` limits explicit motion ratios to declared
  repetitions and distance units, while the short `times-the-number-of` frame
  accepts only a declared quantity particle and a non-unit multiplier;
- the logic-arithmetic membership PP rules require an explicit article and the
  declared `at the university` class restriction, while coordinated role
  derivation requires the declared `teach` surface; and
- `fraction-as-many` requires positive holder roles, a positive fraction no
  greater than one, and excludes a remnant PP from the middle of its comparison.

All eight pinned reviews retest `absent`; ordinary possession, quantity-event,
frequency, particle-ratio, institutional-role, and proper-fraction neighbours
remain matched. The cumulative gate is 4,552 tests and curated 71/71. GSM8K
DEV-train/holdout remain 108/0 and 43/0; ASDiv, SVAMP, MAWPS, and SciBench
remain 45/0, 30/0, 11/0, and 6/0; DIFG remains 75/0; FOLIO makes zero
commitments; and COGS/PMB retain 100% projected-edge precision with zero
incorrect graphs. Lint has zero errors and no protected look was spent.

The relative event-time follow-up makes day deixis inspectable without
pretending that every temporal surface shares one ordering. Core now owns
`yesterday` and `tomorrow` alongside `now` and `today`; a dedicated
`deictic_temporal_marker` category gives those four words signed offsets in
pack data. Exactly one marker attached to exactly one predicate with a bound
subject emits `EventTime`. The document derives `Before` for every pair whose
coordinates differ, while equal coordinates, competing markers, and competing
predicates add no direction. The narrower age-rule `temporal_marker` category
remains exactly `now`/`today`, preventing past or future words from entering a
slot whose semantics assumes a current-moment standard. The deictic field now
shows ordered event cards; `Quantity.time` calendar labels remain opaque and
asks still cannot select a reference moment.

The motivating travel reading preserves three spatial-goal relations, three
event times (`yesterday=-1`, `today=0`, `tomorrow=+1`), and all three supported
strict `Before` pairs, with no unknown-word gaps. The reachable identity
inventory is 265. The cumulative gate is 4,557 tests and curated 71/71.
GSM8K DEV-train/holdout remain 108/0 and 43/0; ASDiv, SVAMP, MAWPS, and
SciBench remain 45/0, 30/0, 11/0, and 6/0; FOLIO makes zero commitments.
COGS DEV-train/holdout and PMB train/development retain 100% projected-edge
precision with zero incorrect graphs. Lint has zero errors and its known
single warning. No protected TEST or generalization look was spent.

The arrival-frame follow-up moves `arrive`, `arrived`, and `arrives` into core
and normalizes both inflected forms to `arrive`. The declarative
`adposition_roles` schema now permits several category-gated frames to emit
one canonical role. `spatial-goal` retains its general motion-plus-destination
frame and adds an arrival-only `at` frame. Consequently “arrived at the
garden” is a goal, while “walked at the garden” retains only its earlier
location reading rather than becoming a goal.

The arrival variant of the motivating document now has no gaps and emits three
normalized `Predication` facts, three `spatial-goal` relations, three
`EventTime` facts, and the same complete three-pair `Before` order. The
reachable identity inventory is 266. The cumulative gate is 4,564 tests and
curated 71/71. GSM8K DEV-train/holdout remain 108/0 and 43/0; ASDiv, SVAMP,
MAWPS, and SciBench remain 45/0, 30/0, 11/0, and 6/0; FOLIO makes zero
commitments. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision with zero incorrect graphs. Lint has zero errors and
its known single warning. No protected TEST or generalization look was spent.

#### Finite-domain temporal location witnesses — complete

The first spatial-temporal query slice now treats arrivals and explicit
location observations as event-linked location evidence. A pack-declared
impossibility premise—“nobody can leave the garden”—is a question-scoped
`LocationConstraint`, not a global law. It may be written inside the question
or as the immediately preceding detached `If` sentence. Earlier or unrelated
conditionals do not acquire that scope. An observed departure that conflicts
with the assumption produces a visible violation and declines the answer.

“Which of them are at the garden today?” binds `them` only to a conservative
finite group of prior named subjects. The answer preserves discourse order and
returns a status per candidate. Direct same-day evidence and earlier arrival
under impossible departure are supported; a future arrival or missing history
is unknown rather than false. A direct same-day negative observation is
contradicted, while conflicting direct observations decline. The day category
deliberately excludes `now`, and prohibition modals such as `may` do not become
physical impossibility.

The new premise rule is strictly generatable. Modal-rooted categories are now
supported by the category-generic realizer; at that increment the curated
frontier reached 114/114 premise rules and 267 reachable identities. Designer traces serialize
the plural referent's grouped obligation target as a JSON-native name list.

The factual no-departure sibling is independently reviewable. “Nobody left
the garden” emits a narrative-through-reference transition-absence fact rather
than reusing physical impossibility. A past or same-day observed departure
conflicts; a future departure does not. Contextual sense arbitration preserves
the established adjective in terminal remainder frames while admitting the
same surface as a departure verb before a definite place. The new rule adds no
lexical identity, is a strict matcher-confirmed generation target, and advances
the live frontier to 115/115.

The complete gate is 4,587 tests and curated 71/71 twice. GSM8K DEV-train and
DEV-holdout remain 108/0 and 43/0; ASDiv, SVAMP, MAWPS, and SciBench remain
45/0, 30/0, 11/0, and 6/0; DIFG remains 75/0; and FOLIO makes zero
commitments. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision with zero incorrect graphs. Lint has zero errors and
its known single warning. No protected TEST or generalization look was spent.

G6b closes the generator-foundation prerequisite for G7. It does not generate
questions itself: it makes coverage measurable and selectable before ask
rules add a second kind of target.

#### G6b structural exploration and health — complete

Every supported premise rule now exposes a vocabulary-free profile assembled
from its authored token types, category ancestry, optional groups, literal
alternatives, `where` constraints, and emit declarations. The Designer turns
that profile into checkbox filters. All selected filters are required, and an
explicit rule or lexicon probe is rejected visibly if it is incompatible with
the filtered frontier.

Fresh strict observations retain the selected objective, filters, targeted
structural signature, observed signatures, and high-level phenomena. Existing
JSONL rows remain valid through schema defaults. Structural coverage is scoped
to the current registry fingerprint because a YAML edit may change the shape
named by an old signature; historical rule and lexicon exploration counts keep
their existing append-only behavior.

The initial signature inventory covers both outcomes of every optional group,
every member of a literal alternation, and every emitted fact type plus its
field-name shape. This is intentionally atomic rather than the cross-product
of every branch, word, and fact: the cross-product would grow exponentially
and make “complete” coverage meaningless. Later objectives can add another
atomic signature family without changing the event ledger contract.

The complete gate is 4,589 tests and curated 71/71 twice. GSM8K DEV-train and
DEV-holdout remain 108/0 and 43/0; ASDiv, SVAMP, MAWPS, and SciBench remain
45/0, 30/0, 11/0, and 6/0; DIFG remains 75/0; and FOLIO makes zero
commitments. COGS DEV-train/holdout and PMB train/development retain 100%
projected-edge precision with zero incorrect graphs. Lint has zero errors and
its known single warning. No protected TEST or generalization look was spent.

### Possessive ownership follow-up — complete

Generation exposed a missing reader distinction between definite common nouns
and possessive-determiner noun phrases in age comparisons. The correction is a
runtime identity feature, not a generator-only exception:

- condensation preserves the determiner as a unit and annotates only an
  uncounted governed noun with its owner;
- a pack-declared third-person determiner may use the unique preceding clause
  subject, following an already resolved subject pronoun to its antecedent;
- quantities and relations retain owner fields and saturation requires an
  exact owner-qualified anchor;
- different owners remain separate even when they state the same value;
- a dedicated generatable age premise accepts the complete determiner+noun
  standard, while the existing age rule retains definite, named, and
  apostrophe-s forms; and
- a possessed age ask uses the existing `single-entity` consumer with an
  explicit `entity_owner` query.

The object-pronoun/count boundary is explicit: `gives her 3 dollars` does not
annotate the counted dollars as possessed. The curated availability boundary
is 116 supported rules out of 118 loaded; the other two remain intentionally
reader-only/safety targets.

### Absolute-year age projection

`arithmetic/stated-age-at-year` makes the sentence class
“ENTITY was N years old in YEAR” directly reviewable. Its strict candidate
retains both numbers, emits one `AgeAtYear`, and round-trips through the
ordinary matcher. The matching ask “How old was ENTITY in YEAR?” routes to a
dedicated consumer. It projects only age, requires integral calendar
coordinates and one consistent non-negative result, and never exposes the
source as a timeless quantity. Arbitrary dated quantities therefore remain
non-projectable.

The distributive current-year sibling resolves subject-case `they` to one
conservative prior referential-subject group. Proper-name grouping retains its
existing ambiguity boundary; when no names occur, definite common-noun
subjects reuse the matcher's ordinary referential test. “How old are they
now/today?” projects every member or declines the whole series. The kernel
requires an explicit reference year rather than reading the wall clock; the
Designer supplies its current year and the CLI exposes `--reference-year`.
For reference year 2026, the reviewed teacher/child example returns labelled
ages 47 and 26. Object-case `them`, partial evidence, repeated holders, and
ambiguous owner/qualifier/label identities do not commit.

The explicit-year aggregate sibling resolves plural possessive `their` to the
same exact subject group. “What was their combined age in 2020?” projects each
member to 2020 before summing, so a teacher aged 20 in 1999 and a child aged 10
in 2010 answer 61. `total age` is the declared sibling surface. Prenominal
`together age`/`altogether age`, singular possessives, missing member evidence,
and unsupported aggregate operations decline rather than guessing.

The full synthetic gate is now 4,672 tests; all standing DEV and cross-corpus
gates retain zero wrong commitments or incorrect graphs, and no protected
TEST/generalization look was spent.

### G7 — Questions and derived rules — complete

Ask generation is implemented without weakening the premise workbench. It
exposes three explicit objectives:

1. **Ask surface** — realize and round-trip one ask rule by itself.
2. **Answerable scenario** — generate the smallest premise set that satisfies
   the ask's declared consumer requirements, then verify the ordinary engine
   returns the expected answer shape.
3. **Decline scenario** — deliberately omit or conflict one named requirement
   and verify the engine declines or asks for clarification rather than
   committing to an unsupported answer.

Ask coverage must remain separate from premise coverage, and generated
premises must continue to use the ordinary premise generator rather than a
question-specific text template.

The first follow-up brings ordinary ask review into the established Designer
loop. A review pins the exact question and complete scenario together with the
matched consumer/query, premise sentences and rule ids, answer and answer
shape, and removal-minimality result. Reviewers can mark the candidate Valid,
Invalid, or Unclear; identify missing consumers, incorrect bindings, irrelevant
evidence, incorrect answers/declines, or non-minimal scenarios; then use the
existing edit, resolve, tombstone, Reading, and source-navigation workflow.

General purchase, wage, price, spend-target, start-marker, and need-ask
vocabulary/categories now belong to `core-english`. Generated auxiliary,
modal, and infinitival ask slots require bare verb forms. This raises the
curated independent frontier from 93/104 to 104/107 loaded asks. The only
remaining blockers are three discourse-group asks that require generated
antecedent context; they remain explicit instead of receiving fabricated
referents.

Answerable-scenario inversion uses semantic identity locks rather than exact
surface locks. A normalized query measure such as `apple` can therefore
constrain a counted premise filler such as `11 apples` while leaving value and
agreement to the ordinary premise realizer. With a random target, the bounded
search deterministically advances past asks for which no scenario is found;
an explicitly selected ask retains an honest error. A pathological generated
combination that fails to saturate is treated as a failed search branch, not a
Designer crash. The full gate is 5,012 tests, all standing DEV snapshot diffs
are neutral, and no protected TEST/generalization look was spent.

#### Forty-sixth review reconciliation — complete

The latest fourteen live premise reviews reduce to four reusable grammar
boundaries rather than fourteen lexical exclusions:

- weekdays and months have governed temporal point prepositions, while
  duration/deadline prepositions retain their independent compatibility;
- every quantitative PP slot marks named calendar objects determinerless;
- direct quantitative initiation, earning, and production readings require
  declared actor/object roles, extended beside vocabulary ownership; and
- subject-owned singular third-person possessives require an animate local
  common-noun subject, while `that/this many` conjuncts require a non-unit
  multiplier.

The generator enforces the same category-scoped determinerless qualifier and
optional trigger-role boundary as the matcher. All reviewed surfaces retest
absent; valid governed calendar, event-role, possessive, and non-unit
multiplier neighbors both match and generate. The full gate is 5,049 tests,
curated remains 71/71, GSM8K DEV-train/holdout remain exactly neutral at
109/0 and 43/0, and all thirteen standing answer/projection DEV diffs are
neutral with zero wrong or incorrect commitments. No protected look was
spent.

#### Forty-seventh review reconciliation — complete

Six invalid generated-ask reviews now share explicit grammar contracts rather
than per-sentence exclusions:

- `how many` binds plural measure morphology; auxiliary-led verbs bind their
  bare form, including particle verbs whose head supplies agreement;
- combined totals admit declared sum markers only, and `how much` admits only
  declared mass-quantity nouns;
- projected-age questions require a future modal, an `in`/`after` temporal
  frame, and a counted age measure; and
- partitive questions use the generic pack-level
  `partitive_measure_compatibility` map between measure and substance
  categories.

The reader-side reconciliation is equally scoped. Arrival predicates cannot
turn a counted surface object into an arithmetic quantity, and the short
anchored relation has a negative lookahead only for a complete same-clause
anchor continuation. Independent coordinated relation clauses therefore keep
working. The matcher and generator share the same closed `AskRule.where`
predicates, and compilation rejects ask predicates that name missing slots or
categories.

All reviewed scenarios now decline; invented valid neighbours cover every
retained boundary. The full gate is 5,073 tests, curated is 71/71, GSM8K
DEV-train/holdout are exactly neutral at 109/0 and 43/0 with zero broken or
declined-to-wrong items, and every unprotected cross-corpus gate retains zero
wrong or incorrect commitments. No protected look was spent.

#### Forty-eighth review reconciliation — complete

Four generated-ask reviews now share declarative grammar and semantic-role
boundaries:

- passive totals require a plural count object, agreeing copula, declared
  passive quantity participle, compatible optional partitive, and a declared
  locative group scope;
- per-holder `how many` asks exclude mass nouns;
- in-place start-state asks require plural agreement, `in`, and an interior
  quantity location; and
- leading-unit dimension differences require concrete length or mass units,
  compatible comparatives, agreeing copulas, distinct plausible holders, and
  an animate common-noun standard after a possessive determiner.

Ask realization now applies any `where` predicate whose participating slots
are already bound before sampling the next filler. This is search pruning, not
a second matcher: the realized question must still pass ordinary analysis,
`match_ask`, specificity, and solving. It prevents tightened multi-slot Ask
contracts from spending all 64 attempts on combinations already known to be
invalid and also renders possessive common nouns without duplicate
definiteness.

All reviewed bindings are unrealisable and all neighboring positive forms
remain generatable. The full gate is 5,091 tests; curated is 71/71; GSM8K
DEV-train/holdout are exactly neutral at 109/0 and 43/0; ASDiv is 45/0, SVAMP
30/0, MAWPS 11/0, SciBench 6/0, and FOLIO retains zero commitments. COGS
DEV-train/holdout remain 1,771/1,693 exact with zero incorrect projections.
No protected look was spent.

#### Forty-ninth through fifty-first ask-review reconciliations — complete

The three latest ask-review batches replace permissive generated-question
slots with explicit grammar contracts for morphology, agreement, referential
holders, possessive ownership, semantic roles, partitives, total-duration
heads, and complete reference queries. Ask generation now supports
project-backed reference group/year domains, pack-declared unions of lexical
categories for one slot, and an answer-commitment requirement for questions
whose syntax alone does not prove a useful scenario. An uninverted
mass-quantity form is explicitly consume-only for standalone generation until
larger-clause generation exists.

The resulting curated frontier is 105/109 independently realizable ask
surfaces. The remaining four blockers are the three antecedent-dependent
discourse-group asks and that embedded-only uninverted form. The fifty-first
batch pins seventeen invalid reviews, preserves positive controls for every
affected family, and keeps established held label-comparison answers intact.
The complete gate is 5,227 tests; all thirteen unprotected benchmark diffs
have zero breaks and zero new wrong or incorrect commitments; lint has zero
errors and one pre-existing warning. No protected look was spent.

#### Fifty-second ask-review reconciliation — complete

The next twelve invalid generated questions exposed shared gaps rather than
twelve isolated strings. Their owning asks now require the appropriate count
or mass head, duration span, dimension unit/adjective pair, quantitative
predicate, participant role, locative scope, partitive compatibility,
membership class, or start-state possession frame. `tall` moves into core
English as a declared length-compatible adjective, and `kitchen` becomes an
explicit quantitative interior location.

Coordinated asks need a deliberate read/generate distinction. Standalone
generation now draws their auxiliary only from plural-compatible `do`/`did`,
so it cannot emit `does A and B`. The reader remains tolerant of that
non-standard agreement because two established GSM8K DEV questions use it
with otherwise unambiguous quantitative semantics. This tolerance is not a
generator loophole: batch tests exercise multiple seeds across all four
coordinated total/per-holder ask families.

All twelve reviewed surfaces are unrecognized, neighbouring valid forms still
match and generate, and the independent frontier remains 105/109. The full
gate is 5,266 tests. Curated remains 71/71; GSM8K DEV-train/holdout remain
108/0 and 43/0; ASDiv, SVAMP, MAWPS, SciBench, DIFG, and FOLIO retain zero
wrong commitments; COGS DEV-train/holdout remain 1,771/1,693 exact with zero
incorrect projections; and PMB train/development remain 117/4 exact with zero
incorrect projections. Every one of the thirteen unprotected before/after
diffs is neutral. Lint has zero errors and one pre-existing warning. No
protected look was spent.

#### Fifty-third ask-review reconciliation — complete

Fourteen new invalid asks exposed the remaining sibling variants of several
earlier boundaries. Named aggregate questions now reject duplicate holders
and generate plural-compatible do-support. Quantity predicates retain open
motion totals where the measure supports them, but reject the declared
non-quantity verb class and enforce the existing initiation, enrollment,
winning, and motion-object roles where those predicates trigger. This blocks
`begin grapes`, `enroll money`, `win rest`, and `travel pounds of sand`
without reducing a valid “miles did A and B run” question to a decline.

The same batch makes the nominal grammar explicit: `price`, `science`, and
`percentage` do not enter a `how many` count frame; membership collections
are singular; entity-less partitives require a compatible measure/substance
pair and a finite predicate; and start-state common nouns retain their exact
qualifier while calendar periods remain ineligible as holders. Duration
totality asks require plural duration units, plausible participants, and the
supported `all ITEM`, `all the ITEM`, or `all of the ITEM` surface. Imperative
dimension cardinals require “of the N”; an explicit negative-lookahead tail
prevents the floating matcher from accepting the shorter prefix of “of N”.

All fourteen reviewed surfaces are unrecognized, fourteen grammatical
neighbours still match, and every affected target remains strictly
generatable. The independent frontier remains 105/109. The full gate is 5,312
tests. Curated remains 71/71; GSM8K DEV-train/holdout remain 108/0 and 43/0;
ASDiv, SVAMP, MAWPS, SciBench, DIFG, and FOLIO retain zero wrong commitments;
COGS DEV-train/holdout remain 1,771/1,693 exact with zero incorrect
projections; and PMB train/development remain 117/4 exact with zero incorrect
projections. All thirteen unprotected before/after diffs are neutral. Lint
has zero errors and one pre-existing warning. No protected look was spent.

#### Fifty-fourth answerable-scenario reconciliation — complete

Four invalid answerable scenarios exposed defects at three different layers.
The premise planner now ranks equally relevant plans by fewer emissions and a
shorter declared rule shape, making the smallest found scenario easier to
inspect without bypassing ordinary generation or solving. Relation saturation
does not restate an existing same-holder anchor under a second verb and refuses
negative cardinal results. The reviewed conjoined comparison rules enforce
their declared verb/participant/object, count-head, age-word, and modifier
boundaries.

Ask grammar now requires an object-case plural discourse pronoun after “all
of”, while generation selects plural `do`/`did`; the reader keeps its existing
non-standard `does all of them` compatibility. Partitive membership asks carry
their collection into the query and require a project-declared exhaustive
complement label plus plural copular syntax. Curated has no such label
vocabulary, so this target becomes an explicit blocker rather than generating
unrelated nouns. Exact pronoun-group aggregate and per-holder asks are also
contextual rather than independently realizable: their question surfaces can
round-trip, but answering requires a prior subject group. The independent
curated frontier is therefore 104/114.

All four review records are pinned. The complete gate is 5,332 tests. Curated
is 71/71; GSM8K DEV-train/holdout are 108/0 and 42/0; ASDiv, SVAMP, MAWPS,
SciBench, DIFG, and FOLIO retain zero wrong commitments, with the explicit
group and qualified-measure path adding one SVAMP correct answer (31/0); COGS
DEV-train/holdout remain 1,771/1,693 exact with zero incorrect projections;
and PMB train/development remain 117/4 exact with zero incorrect projections.
Lint has zero errors and one pre-existing warning. No protected look was spent.

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
4. Mechanical generation support never implies linguistic validity. Known
   bad outputs remain explorable so the human can identify the faulty premise.
5. Reviews are lightweight debugging evidence, not training data.
6. Hypotheses are trace-backed suggestions, not learned or automatic edits.
7. The user intentionally edits YAML and explicitly saves it.
8. The pinned sentence is rerun immediately after a change.
9. The normal parser never reads reviews or generation configuration.
10. UI clarity and iteration speed take precedence over exhaustive validation
   machinery.
11. Question and bounded scenario generation are implemented as G7, but their
    availability and review evidence remain separate from premise coverage.

## Completion criterion

The product criterion has been met and remains the standard for further
refinement. A non-expert rule author can:

1. open the designer;
2. generate a concrete mechanically matched example for a selected or random
   rule, including examples that expose defective premises;
3. understand why the rule accepted it;
4. identify and record a questionable premise;
5. follow a hypothesis to the relevant YAML;
6. make an intentional edit;
7. retest the exact sentence;
8. understand the before/after result; and
9. continue exploring without leaving the workbench.

The ideal is to generate across every project rule and reachable lexicon
entry. Plausibility is an outcome for the reviewer to assess, not a condition
the generator must establish before exposing a specimen. The product is
useful before complete mechanical coverage, provided every unsupported area
is visible and honest.
